"""Заранее строит разборы для демо-клиентов и кладёт их в backend/demo_cache.

Запуск из папки backend: python -m scripts.warm_cache [роль ...]
Нужен ключ в .env. Уже готовые разборы пропускаются, поэтому скрипт можно
запускать повторно. Папку demo_cache коммитим: с ней демо работает без модели.
"""
import sys

from app.main import DEMO_IDS
from app.scoring import get_feed_items
from ml import insight_store
from ml.agent.loop import run_insight
from ml.service import parse_insight_id

LIMIT = 6  # сколько событий из ленты прогреваем у каждого клиента


def main(roles: list[str]) -> None:
    for company_id in DEMO_IDS:
        for role in roles:
            for item in get_feed_items(company_id, role, LIMIT):
                if insight_store.get(item.insight_id):
                    print("уже есть", item.insight_id)
                    continue
                _, event_id, _ = parse_insight_id(item.insight_id)
                try:
                    card, trace, context = run_insight(company_id, event_id, role, relevance=item.relevance)
                except Exception as error:
                    print("ошибка", item.insight_id, error)
                    continue
                insight_store.save(item.insight_id, card, trace, context=context, demo=True)
                print("готово", item.insight_id)


if __name__ == "__main__":
    main(sys.argv[1:] or ["cfo"])