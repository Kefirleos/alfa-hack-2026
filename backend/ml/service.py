from datetime import date

from app.company_profile import get_company_profile
from app.schemas import ChatAnswer, InsightCard, TraceStep, UserRole
from app.scoring import company_signals, load_events, score_event
from ml import custom_news, insight_store
from ml.agent import chat
from ml.agent.loop import find_event, run_insight


class NotFound(LookupError):
    ""


class CompanyNotFound(NotFound):
    ""


class EventNotFound(NotFound):
    ""

def make_insight_id(company_id: str, event_id: str, role: UserRole | str) -> str:
    role_value = role.value if isinstance(role, UserRole) else role
    return f"{company_id}__{event_id}__{role_value}"


def parse_insight_id(insight_id: str) -> tuple[str, str, UserRole]:
    parts = insight_id.split("__")
    if len(parts) != 3:
        raise ValueError("insight_id должен иметь вид company__event__role")
    company_id, event_id, role_value = parts
    try:
        role = UserRole(role_value)
    except ValueError:
        raise ValueError(f"Неизвестная роль {role_value!r}") from None
    return company_id, event_id, role


def _check_company(company_id: str) -> dict:
    profile = get_company_profile(company_id)
    if profile is None:
        raise CompanyNotFound(f"Клиент {company_id} не найден")
    return profile


def _relevance(profile: dict, event: dict, role: str) -> float:
    events = load_events()
    ref_date = max(date.fromisoformat(e["published"][:10]) for e in events)
    ref_date = max(ref_date, date.fromisoformat(event["published"][:10]))
    scored = score_event(profile, company_signals(profile), role, event, ref_date)
    return round(scored["score"], 3) if scored else 0.0


def _insight_with_trace(insight_id: str) -> tuple[InsightCard, list[TraceStep]]:
    company_id, event_id, role = parse_insight_id(insight_id)
    profile = _check_company(company_id)
    event = find_event(event_id)
    if event is None:
        raise EventNotFound(f"Событие {event_id} не найдено")

    cached = insight_store.get(insight_id)
    if cached:
        return cached

    card, trace, context = run_insight(company_id, event_id, role.value,
                                       relevance=_relevance(profile, event, role.value))
    insight_store.save(insight_id, card, trace, context=context)
    return card, trace


def get_insight(insight_id: str) -> InsightCard:
    card, _ = _insight_with_trace(insight_id)
    return card


def get_trace(insight_id: str) -> list[TraceStep]:
    _, trace = _insight_with_trace(insight_id)
    return trace

  
def answer_question(insight_id: str, message: str, demo: bool = False) -> ChatAnswer:
    if not message or not message.strip():
        raise ValueError("Пустой вопрос")
    card, _ = _insight_with_trace(insight_id) 
    cached = insight_store.get_chat(insight_id, message)
    if cached and not demo:
        return cached

    context = insight_store.get_context(insight_id)
    if context is None:
        raise ValueError("Разбор сохранён без данных для чата: удалите его файл в data/insights и откройте заново")
    _, event_id, role = parse_insight_id(insight_id)
    answer = chat.answer(card, context, find_event(event_id), role.value, message)
    insight_store.save_chat(insight_id, message, answer, demo=demo)
    return answer
  

def custom_insight(company_id: str, role: UserRole | str, text: str | None = None,
                   url: str | None = None) -> InsightCard:
    """Своя новость: текст или ссылка -> событие с разметкой -> обычный разбор."""
    if not (text and text.strip()) and not (url and url.strip()):
        raise ValueError("Нужен text или url")
    _check_company(company_id)
    event = custom_news.make_event(text=text, url=url)
    return get_insight(make_insight_id(company_id, event["event_id"], role))