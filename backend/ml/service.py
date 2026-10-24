from datetime import date

from app.company_profile import get_company_profile
from app.schemas import ChatAnswer, Claim, ClaimType, InsightCard, TraceStep, UserRole
from app.scoring import company_signals, load_events, score_event
from ml import insight_store
from ml.agent.loop import find_event, run_insight


class CompanyNotFound(LookupError):
    ""

def make_insight_id(company_id: str, event_id: str, role: UserRole | str) -> str:
    role_value = role.value if isinstance(role, UserRole) else role
    return f"{company_id}__{event_id}__{role_value}"

def parse_insight_id(insight_id:str) -> tuple[str, str, UserRole]:
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
    scored = score_event(profile, company_signals(profile), role, event, ref_date)
    return round(scored["score"], 3) if scored else 0.0
 
def _insight_with_trace(insight_id: str) -> tuple[InsightCard, list[TraceStep]]:
    cached = insight_store.get(insight_id)
    if cached:
        return cached
 
    company_id, event_id, role = parse_insight_id(insight_id)
    profile = _check_company(company_id)
    event = find_event(event_id)
    if event is None:
        raise ValueError(f"Событие {event_id} не найдено")      
 
    card, trace = run_insight(company_id, event_id, role.value, relevance=_relevance(profile, event, role.value))
    insight_store.save(insight_id, card, trace)
    return card, trace
 
 
def get_insight(insight_id: str) -> InsightCard:
    card, _ = _insight_with_trace(insight_id)
    return card
 
 
def get_trace(insight_id: str) -> list[TraceStep]:
    _, trace = _insight_with_trace(insight_id)
    return trace
 
def answer_question(insight_id: str, message: str) -> ChatAnswer:
    company_id, _, _ = parse_insight_id(insight_id)
    _check_company(company_id)
    return ChatAnswer(answer=[
        Claim(text=f"Вопрос: «{message[:100]}». Ответ по разбору будет добавлен.",
              type=ClaimType.ai_inference), 
    ])
 
 
def custom_insight(company_id: str, role: UserRole, text: str | None = None, url: str | None = None) -> InsightCard:
    if not text and not url:
        raise ValueError("Нужен text или url")
    _check_company(company_id)
    raise NotImplementedError("A breakdown of your news will be added.")