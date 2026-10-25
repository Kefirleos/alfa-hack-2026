import sys

from app.main import DEMO_IDS
from app.scoring import get_feed_items, load_events
from ml import insight_store, service
from ml.agent.loop import run_insight
from ml.service import make_insight_id, parse_insight_id

LIMIT = 6
CHAT_LIMIT = 2

CHAT_QUESTIONS = [
    "Что это значит для нас?",
    "Что проверить в первую очередь?",
    "Что по этому поводу думает банк?",
]


DEMO_STORY = ("U_9250", "cfo", "сохранил ключевую ставку")
DEMO_QUESTIONS = [
    "Что банк ждёт по ставке до конца года?",
    "Что нам проверить по кредитам?",
    "Почему банк поменял прогноз?",
]


def warm_insight(insight_id: str, company_id: str, role: str, relevance: float) -> bool:
    if insight_store.get(insight_id):
        print("уже есть ", insight_id)
        return True
    _, event_id, _ = parse_insight_id(insight_id)
    try:
        card, trace, context = run_insight(company_id, event_id, role, relevance)
    except Exception as error:
        print("Error", insight_id, error)
        return False
    insight_store.save(insight_id, card, trace, context, demo=True)
    print("Готово", insight_id)
    return True


def warm_chat(insight_id: str, questions: list[str]) -> None:
    for question in questions:
        if insight_store.get_chat(insight_id, question):
            print("ответ: ", question)
            continue
        try:
            service.answer_question(insight_id, question, demo=True)
            print("ответ готов: ", question)
        except Exception as error:
            print("ошибка ответа: ", question, error)

def main(roles: list[str]) -> None:
    for company_id in DEMO_IDS:
        for role in roles:
            items = get_feed_items(company_id, role, LIMIT)
            for number, item in enumerate(items):
                ok = warm_insight(item.insight_id, company_id, role, item.relevance)
                if ok and number < CHAT_LIMIT:
                    warm_chat(item.insight_id, CHAT_QUESTIONS)

    company_id, role, title_part = DEMO_STORY
    event = next((e for e in load_events() if title_part in e["title"]), None)
    if event is None:
        print("демо-история не найдена")
        return
    insight_id = make_insight_id(company_id, event["event_id"], role)
    if warm_insight(insight_id, company_id, role, relevance=0.0):
        warm_chat(insight_id, CHAT_QUESTIONS + DEMO_QUESTIONS)

if __name__ == "__main__":
    main(sys.argv[1:] or ["cfo"])