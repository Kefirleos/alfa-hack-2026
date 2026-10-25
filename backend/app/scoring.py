import json
from datetime import date
from functools import lru_cache

import yaml

from app.company_profile import get_company_profile
from app.schemas import FeedItem, ItemKind
from ml import config

# коэффициенты: насколько событие данного статуса важно
STATUS_FACTOR = {"decided": 1.0, "proposed": 0.85, "other": 0.7, "data": 0.55}
MAX_PER_TOPIC = 2  # не больше двух событий одной темы в ленте, чтобы лента была разнообразной


def _load_yaml(name: str):
    with open(config.REFERENCE_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def _rules() -> dict:
    return {
        "fields": _load_yaml("field_rules.yaml"),
        "roles": _load_yaml("roles.yaml"),
        "okved": _load_yaml("okved_exposure.yaml"),
    }


@lru_cache(maxsize=1)
def load_events() -> list[dict]:
    """События с темами из events.jsonl (без тем в ленту не попадают)."""
    path = config.PROCESSED_DIR / "events.jsonl"
    with open(path, encoding="utf-8") as f:
        events = [json.loads(line) for line in f if line.strip()]
    return [e for e in events if e["topics"] and e.get("published") and "состоится" not in e["title"].lower()]

def _published_date(event: dict) -> date:
    return date.fromisoformat(event["published"][:10])


def company_signals(profile: dict) -> dict:
    """Что в профиле компании связывает её с темами: тема -> список вкладов (вес, вид, причина)."""
    rules = _rules()
    fields, okved = rules["fields"], rules["okved"]
    signals: dict[str, list[dict]] = {}

    def add(topic: str, weight: float, kind: str | None, reason: str):
        signals.setdefault(topic, []).append({"weight": weight, "kind": kind, "reason": reason})

    # продукты банка
    for flag in profile["bank_products"]:
        rule = fields["fields"].get(flag)
        if rule:
            for topic, spec in rule["topics"].items():
                add(topic, spec["weight"], spec["kind"], rule["reason"])

    # внешняя торговля, правила флага и страны
    trade = profile["foreign_trade"]
    if trade["fts_flag"]:
        rule = fields["fields"]["fts_flag"]
        for topic, spec in rule["topics"].items():
            add(topic, spec["weight"], spec["kind"], rule["reason"])
        by_country: dict[str, float] = {}
        names = []
        for country in trade["countries"]:
            name = country.capitalize()
            names.append(name)
            table = fields["countries"].get(name, fields["countries"]["default"])
            for topic, weight in table.items():
                by_country[topic] = max(by_country.get(topic, 0.0), weight)
        if names:
            for topic, weight in by_country.items():
                add(topic, weight, None, "внешняя торговля со странами: " + ", ".join(names))

    # отрасль
    # точный код ОКВЭД важнее раздела: у оптовиков топливом свои темы
    section = okved.get("codes", {}).get(profile["industry"]["okved_code"]) or okved["sections"].get(profile["industry"]["okved_div"], okved["default"])
    for topic, weight in section["topics"].items():
        add(topic, weight, None, f"отрасль: {section['name'].lower()}")

    # зависимость от одного плательщика или получателя
    pay = profile["payments"]
    for key, share in (("top_payer_share", pay["top_payer_share"]), ("top_payee_share", pay["top_payee_share"])):
        rule = fields["payments"][key]
        if share is not None and share >= rule["threshold"]:
            for topic, weight in rule["topics"].items():
                add(topic, weight, None, rule["reason"])
    return signals


def _topic_weight(contributions: list[dict]) -> float:
    """Несколько независимых причин усиливают друг друга (но не больше 0.97)."""
    rest = 1.0
    for c in contributions:
        rest *= 1.0 - c["weight"]
    return min(0.97, 1.0 - rest)


def score_event(profile: dict, signals: dict, role: str, event: dict, ref_date: date) -> dict | None:
    roles = _rules()["roles"]
    role_rule = roles[role]
    best = None
    for topic in event["topics"]:
        contributions = signals.get(topic)
        if not contributions:
            continue
        topic_score = _topic_weight(contributions) * role_rule["weights"].get(topic, role_rule["default_weight"])
        if best is None or topic_score > best[0]:
            best = (topic_score, topic, contributions)
    if best is None:
        return None
    topic_score, topic, contributions = best

    age = max(0, (ref_date - _published_date(event)).days)
    freshness = max(0.35, 0.5 ** (age / 14))
    status = STATUS_FACTOR.get(event.get("status"), 0.7)
    source = 0.75 + 0.25 * event.get("source_weight", 0.5)
    industries = event.get("industries") or []
    if industries:
        industry = 1.25 if profile["industry"]["okved_div"] in industries else 0.7
    else:
        industry = 1.0
    # новость называет страны, с которыми торгует клиент: она ближе к нему
    own_countries = {c.capitalize() for c in profile["foreign_trade"]["countries"]}
    country = 1.3 if own_countries & set(event.get("countries") or []) else 1.0
    score = min(1.0, topic_score * freshness * status * source * industry * country)

    # вид события: направление берём из разметки новости (риск/возможность для заёмщика),
    # а если оно нейтральное, то из самого сильного правила для клиента
    with_kind = [c for c in contributions if c["kind"]]
    rule_kind = max(with_kind, key=lambda c: c["weight"])["kind"] if with_kind else None
    event_kind = event.get("kind", "neutral")
    kind = event_kind if event_kind != "neutral" else (rule_kind or "neutral")

    reasons = []
    for c in sorted(contributions, key=lambda c: c["weight"], reverse=True):
        if c["reason"] not in reasons:
            reasons.append(c["reason"])
        if len(reasons) == 2:
            break
    return {"event": event, "topic": topic, "score": score, "kind": kind, "reasons": reasons}


def rank_events(profile: dict, role: str, limit: int = 10) -> list[dict]:
    events = load_events()
    ref_date = max(_published_date(e) for e in events)  # «сегодня» = дата самой свежей новости
    signals = company_signals(profile)
    scored = [s for e in events if (s := score_event(profile, signals, role, e, ref_date))]
    scored.sort(key=lambda s: (-round(s["score"], 3), s["event"]["published"]))
    result, per_topic, seen_titles = [], {}, set()
    for s in scored:
        title_key = s["event"]["title"].split("//")[-1].strip().lower()[:40] # один сюжет в разных заголовках не повтоярется
        if title_key in seen_titles or per_topic.get(s["topic"], 0) >= MAX_PER_TOPIC:
            continue
        seen_titles.add(title_key)
        per_topic[s["topic"]] = per_topic.get(s["topic"], 0) + 1
        result.append(s)
        if len(result) >= limit:
            break
    return result


def make_insight_id(company_id: str, event_id: str, role: str) -> str:
    return f"{company_id}__{event_id}__{role}"


def get_feed_items(company_id: str, role: str = "ceo", limit: int = 10) -> list[FeedItem] | None:
    profile = get_company_profile(company_id)
    if profile is None:
        return None
    return [
        FeedItem(
            insight_id=make_insight_id(company_id, s["event"]["event_id"], role),
            title=s["event"]["title"],
            date=s["event"]["published"][:10],
            relevance=round(s["score"], 3),
            kind=ItemKind(s["kind"]),
            why_for_you=s["reasons"],
            source=s["event"]["source_name"],
        )
        for s in rank_events(profile, role, limit)
    ]