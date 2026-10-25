import json
import time
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field

from app.schemas import Claim, ClaimType, Event, InsightCard, Source, TraceStep
from app.scoring import load_events
from ml import llm_client, custom_news
from ml.agent.tools import PRODUCT_NAMES, run_tool, _load_yaml
from ml.agent.checks import rule_check

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
MAX_TOOL_CALLS = 8
MAX_GENERATIONS = 3
TIME_LIMIT = 60
PARTS = ("summary", "why_it_matters", "risks", "opportunities", "actions", "bank_view")
AGENT_ROLE = "research"


class DraftClaim(BaseModel):
    text: str
    type: Literal["fact", "bank_view", "ai_inference", "ad"]
    refs: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"


class InsightDraft(BaseModel):
    summary: list[DraftClaim] = Field(min_length=1)
    why_it_matters: list[DraftClaim] = Field(min_length=1)
    risks: list[DraftClaim] = Field(default_factory=list)
    opportunities: list[DraftClaim] = Field(default_factory=list)
    actions: list[DraftClaim] = Field(min_length=1)
    bank_view: list[DraftClaim] = Field(default_factory=list)
    uncertainty: str = ""


def _prompt(name:str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def find_event(event_id) -> dict | None:
    for event in load_events():
        if event["event_id"] == event_id:
            return event
    return custom_news.find(event_id)


def fill(template: str, values: dict) -> str:
    for key, value in values.items():
        template = template.replace("{" + key + "}", str(value))
    return template


def _new_state() -> dict:
    return {
        "started": time.time(),
        "calls": 0,
        "results": [],
        "refs": set(),
        "trace": [],
    }


def _add_step(state: dict, name: str, result: str, tool: str | None = None) -> None:
    state["trace"].append(TraceStep(step=len(state["trace"]) + 1, name=name, tool=tool, result=result))


def _call(state: dict, step_name: str, tool: str, args) -> dict:
    if state["calls"] >= MAX_TOOL_CALLS or TIME_LIMIT < (time.time() - state["started"]):
        return {"error": "лимит агента исчерпан", "refs": []}
    result = run_tool(tool, args)
    state["calls"] += 1
    state["results"].append({"tool": tool, "args": args, "result": result})
    state["refs"].update(result.get("refs", []))

    if "error" in result:
        summary = f"ошибка: {result['error']}"
    elif "items" in result:
        summary = f"найдено: {len(result['items'])}"
    else:
        summary = "получено"

    _add_step(state, step_name, summary, tool)
    return result


def _topic_names(topic_ids: list[str]) -> str:
    names = {topic["id"]: topic["name"] for topic in _load_yaml("topics.yaml")}
    return " ".join(names.get(topic_id, topic_id) for topic_id in topic_ids)


def gather(company_id:str, event: dict, role: str) -> dict:
    state = _new_state()
    topics = event["topics"]
    _add_step(state, "План",
             f"Компания {company_id}, роль {role}, темы события: {', '.join(topics)}. "
             "Нужны: профиль компании, позиция банка, похожие события, продукты банка.")
    state["refs"].add(f"news:{event['event_id']}")
    profile = _call(state, "Профиль компании", "get_company_profile", {"company_id": company_id})
    okved_div = (profile.get("okved") or "")[:2]

    query = f"{event['title']} {_topic_names(topics)}"
    bank = _call(state, "Поиск позиции банка", "search_alfa_analytics", {"query": query, "topics": topics})
    if not bank.get("items"):
        bank = _call(state, "Повторный поиск позиции банка", "search_alfa_analytics", {"query": _topic_names(topics)})

    if "key_rate" in topics:
        _call(state, "Поиск прогноза банка по ставке", "search_alfa_analytics",
              {"query": "прогноз ключевой ставки на конец года"})

    _call(state, "Похожие события", "search_related_news",
        {"topics": topics, "industries": [okved_div] if okved_div else [],
        "exclude_event_id": event["event_id"], "limit": 4})

    _call(state, "Продукты банка", "get_bank_products", {"company_id": company_id, "topics": topics})

    return state


def generate(state: dict, company_id: str, event: dict, role: str, feedback: str | None = None) -> InsightDraft:
    role_rule = _load_yaml("roles.yaml")[role]

    event_info = {
        "ref": f"news:{event['event_id']}",
        "title": event["title"],
        "date": event["published"][:10],
        "source": event["source_name"],
        "summary": event.get("summary", ""),
        "text": event.get("text", "")[:800],
    }
    tool_results = json.dumps(
        [{"tool": call["tool"], "result": call["result"]} for call in state["results"]],
        ensure_ascii=False,
    )
    user = fill(_prompt("insight.txt"), {
        "company_id": company_id,
        "role_name": role_rule["name"],
        "role_focus": role_rule["focus"],
        "role_style": role_rule["answer_style"],
        "event": json.dumps(event_info, ensure_ascii=False),
        "tool_results": tool_results,
    })
    messages = [
        {"role": "system", "content": _prompt("system.txt")},
        {"role": "user", "content": user},
    ]
    if feedback:
        messages.append({"role": "user", "content": "Исправь разбор с учётом замечаний:\n" + feedback})

    draft = llm_client.chat_json(AGENT_ROLE, messages, InsightDraft, max_tokens=4000, temperature=0.2)
    state["generations"] = state.get("generations", 0) + 1
    total = sum(len(getattr(draft, part)) for part in PARTS)
    _add_step(state, "Генерация разбора", f"утверждений: {total}")
    return draft


def claim_converter(state: dict, event: dict):
    sources = {}
    for call in state["results"]:
        for item in call["result"].get("items", []):
            ref = item.get("ref", "")
            if ref.startswith("alfa:"):
                file_name = ref[len("alfa:"):].split("#")[0]
                sources[ref] = Source(title=f"{item['title']} ({item['date']})", doc=file_name, page=item["page"])
            elif ref.startswith("news:"):
                found = find_event(ref[len("news:"):])
                sources[ref] = Source(title=item["title"], url=found.get("url") if found else None)
    sources[f"news:{event['event_id']}"] = Source(title=event["title"], url=event.get("url"))

    product_names = {f"product:{p['id']}": p["name"] for p in _load_yaml("products.yaml")}
    field_names = {"okved": "отрасль", "region": "регион", "payments": "структура платежей",
                   "counterparties": "контрагенты", "fts_flag": "сведения ФТС", **PRODUCT_NAMES}


    def to_claim(draft_claim: DraftClaim) -> Claim:
        claim_sources, features = [], []
        for ref in draft_claim.refs:
            if ref in sources:
                claim_sources.append(sources[ref])
            elif ref.startswith("client:"):
                features.append(field_names.get(ref[len("client:"):], ref))
            elif ref in product_names:
                features.append(product_names[ref])
        return Claim(text=draft_claim.text, type=ClaimType(draft_claim.type),
                     sources=claim_sources, features=features, confidence=draft_claim.confidence)

    return to_claim


def resolve(draft: InsightDraft, state: dict, company_id: str, insight_id: str,
            event: dict, relevance: float) -> InsightCard:
    to_claim = claim_converter(state, event)
    return InsightCard(
        id=insight_id,
        company_id=company_id,
        relevance=relevance,
        event=Event(title=event["title"], date=event["published"][:10],
                    summary=[to_claim(c) for c in draft.summary]),
        why_it_matters=[to_claim(c) for c in draft.why_it_matters],
        risks=[to_claim(c) for c in draft.risks],
        opportunities=[to_claim(c) for c in draft.opportunities],
        actions=[to_claim(c) for c in draft.actions],
        bank_view=[to_claim(c) for c in draft.bank_view],
        uncertainty=draft.uncertainty or None,
    )


def _drop_invalid(draft: InsightDraft, state: dict) -> int:
    known = state["refs"]
    required = {"fact": "news:", "bank_view": "alfa:", "ad": "product:"}
    dropped = 0
    for part in PARTS:
        kept = []
        for claim in getattr(draft, part):
            claim.refs = [ref for ref in claim.refs if ref in known]
            prefix = required.get(claim.type)
            if prefix and not any(ref.startswith(prefix) for ref in claim.refs):
                dropped += 1
                continue
            kept.append(claim)
        setattr(draft, part, kept)
    return dropped


def run_insight(company_id: str, event_id: str, role: str,
                relevance: float = 0.0) -> tuple[InsightCard, list[TraceStep], dict]:
    event = find_event(event_id)
    if event is None:
        raise ValueError(f"событие {event_id} не найдено")

    state = gather(company_id, event, role)
    draft = generate(state, company_id, event, role)

    issues = rule_check(draft, state)
    _add_step(state, "Самопроверка", "замечаний нет" if not issues else f"замечаний: {len(issues)}")

    time_left = time.time() - state["started"] < TIME_LIMIT
    if issues and state["generations"] < MAX_GENERATIONS and time_left:
        draft = generate(state, company_id, event, role, feedback="\n".join(issues))
        issues = rule_check(draft, state)
        _add_step(state, "Повторная самопроверка", "замечаний нет" if not issues else f"замечаний: {len(issues)}")

    if issues:
        dropped = _drop_invalid(draft, state)
        if dropped:
            draft.uncertainty = (draft.uncertainty + f" Снято утверждений без подтверждения: {dropped}.").strip()
            _add_step(state, "Снятие неподтверждённого", f"снято: {dropped}")

    card = resolve(draft, state, company_id, f"{company_id}__{event_id}__{role}", event, relevance)
    seconds = round(time.time() - state["started"], 1)
    _add_step(state, "Готово", f"инструментов: {state['calls']}, генераций: {state['generations']}, {seconds} с")

    context = {"results": state["results"], "refs": sorted(state["refs"])}
    return card, state["trace"], context


if __name__ == "__main__":
    import sys
    company = sys.argv[1] if len(sys.argv) > 1 else "U_9250"
    role = sys.argv[2] if len(sys.argv) > 2 else "cfo"
    event = next(e for e in load_events() if "сохранил ключевую ставку" in e["title"])
    card, trace, context = run_insight(company, event["event_id"], role, relevance=0.8)
    print(card.model_dump_json(indent=2))
    for step in trace:
        print(step.step, step.name, step.tool or "", "—", step.result)
    print("context:", len(context["results"]), "вызовов,", len(context["refs"]), "меток")