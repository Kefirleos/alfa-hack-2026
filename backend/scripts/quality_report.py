"""Считает метрики качества по готовым разборам, журналу вызовов модели и отзывам.

Запуск из папки backend: python -m scripts.quality_report
Модель не вызывается, ключ не нужен.
"""
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import date

from app.main import DEMO_IDS
from app.scoring import _published_date, get_feed_items, load_events
from ml import config, insight_store

ROLES = ("cfo", "ceo")
FEED_SIZE = 5

# цена за 1 млн токенов, рубли (вход, выход)
PRICES = {
    "google/gemma-4-26b-a4b-it": (4.48, 23),
    "z-ai/glm-5.3-flash": (5.10, 17),
    "qwen/qwen3.6-35b-a3b": (5.33, 74),
    "deepseek/deepseek-v4.1-flash": (10, 21),
    "qwen/qwen3-vl-30b-a3b-instruct": (14.30, 57.10),
    "moonshotai/kimi-k2.6": (51, 270),
}


def load_cards() -> list[dict]:
    cards = []
    for folder in (insight_store.INSIGHTS_DIR, insight_store.DEMO_DIR):
        if folder.exists():
            for path in folder.glob("*.json"):
                cards.append(json.loads(path.read_text(encoding="utf-8")))
    return cards


def card_metrics(cards: list[dict]) -> None:
    claims = Counter()
    without_source = Counter()
    with_bank = 0
    with_dropped = 0
    seconds = []
    for data in cards:
        card = data["card"]
        parts = [card["event"]["summary"], card["why_it_matters"], card["risks"],
                 card["opportunities"], card["actions"], card["bank_view"]]
        for part in parts:
            for claim in part:
                claims[claim["type"]] += 1
                if claim["type"] in ("fact", "bank_view") and not claim["sources"]:
                    without_source[claim["type"]] += 1
        if card["bank_view"]:
            with_bank += 1
        for step in data["trace"]:
            if step["name"].startswith("Снятие"):
                with_dropped += 1
            found = re.search(r"([\d.]+) с$", step["result"]) if step["name"] == "Готово" else None
            if found:
                seconds.append(float(found.group(1)))

    checked = claims["fact"] + claims["bank_view"]
    print(f"Карточек: {len(cards)}, утверждений: {sum(claims.values())} {dict(claims)}")
    print(f"Покрытие источниками: {checked - sum(without_source.values())} из {checked} "
          f"фактов и позиций банка с источником")
    print(f"Карточек, где самопроверка сняла утверждения: {with_dropped} из {len(cards)}")
    print(f"Карточек с заполненной позицией банка: {with_bank} из {len(cards)} ({with_bank / max(len(cards), 1):.0%})")
    if seconds:
        print(f"Время разбора: медиана {statistics.median(seconds):.0f} с, максимум {max(seconds):.0f} с")


def usage_metrics() -> None:
    path = config.LLM_CACHE_DIR / "usage.jsonl"
    if not path.exists():
        print("Журнал вызовов модели не найден")
        return
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    cached = sum(1 for row in rows if row.get("cached"))
    paid = [row for row in rows if not row.get("cached")]
    cost = 0.0
    by_role = defaultdict(float)
    for row in paid:
        price_in, price_out = PRICES.get(row["model"], (0, 0))
        spent = ((row.get("prompt_tokens") or 0) * price_in + (row.get("completion_tokens") or 0) * price_out) / 1_000_000
        cost += spent
        by_role[row["role"]] += spent
    research = [row for row in paid if row["role"] == "research"]
    print(f"Вызовов модели: {len(rows)}, из кэша: {cached} ({cached / max(len(rows), 1):.0%})")
    print(f"Потрачено: {cost:.1f} ₽ ({', '.join(f'{role} {value:.1f}' for role, value in by_role.items())})")
    if research:
        print(f"Стоимость вызова основной модели в среднем: {by_role['research'] / len(research):.2f} ₽ "
              f"(разбор обычно 1–2 вызова)")


def feed_metrics() -> None:
    events = load_events()
    ref_date = max(_published_date(event) for event in events)
    ages = []
    duplicates = shown = 0
    for company_id in DEMO_IDS:
        for role in ROLES:
            items = get_feed_items(company_id, role, FEED_SIZE) or []
            by_id = {event["event_id"]: event for event in events}
            keys = []
            for item in items:
                event = by_id[item.insight_id.split("__")[1]]
                ages.append((ref_date - _published_date(event)).days)
                keys.append((tuple(event["topics"][:1]), _published_date(event)))
            counts = Counter(keys)
            duplicates += sum(count for count in counts.values() if count > 1)
            shown += len(items)
    print(f"Свежесть топ-{FEED_SIZE}: медианный возраст {statistics.median(ages):.0f} дн., максимум {max(ages)} дн.")
    print(f"Дубликаты (одна тема и один день) в топ-{FEED_SIZE}: {duplicates} из {shown} ({duplicates / max(shown, 1):.0%})")


def feedback_metrics() -> None:
    path = insight_store.INSIGHTS_DIR / "feedback.jsonl"
    if not path.exists():
        print("Отзывов пока нет")
        return
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    useful = sum(1 for row in rows if row["useful"])
    print(f"Отзывов: {len(rows)}, «Полезно»: {useful} ({useful / len(rows):.0%})")


def main() -> None:
    print("Метрики качества на", date.today().isoformat())
    print("\nРазборы")
    card_metrics(load_cards())
    print("\nМодель и бюджет")
    usage_metrics()
    print("\nЛента")
    feed_metrics()
    print("\nОтзывы пользователей")
    feedback_metrics()


if __name__ == "__main__":
    main()
