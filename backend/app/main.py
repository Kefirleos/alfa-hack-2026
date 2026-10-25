from fastapi import FastAPI, HTTPException
from app.schemas import ClaimType, Source, Claim, Event, InsightCard, ItemKind, CompanyShort, FeedItem, UserRole, LoginRequest, LoginResponse, TraceStep, ChatRequest, ChatAnswer, CustomNewsRequest, CompareResult, FeedBackRequest
from app.company_profile import get_company_profile
from app.scoring import get_feed_items
from fastapi.middleware.cors import CORSMiddleware
from ml import insight_store, service
from ml.llm_client import LLMError

app = FastAPI(title="GenAlpha News Insights API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/health")
def health():
    return {"status": "ok"}

def _call_service(func, *args):
    """Вызов сервиса разбора с переводом его ошибок в коды HTTP."""
    try:
        return func(*args)
    except service.NotFound as error:
        raise HTTPException(status_code=404, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail=str(error))
    except LLMError as error:
        raise HTTPException(status_code=503, detail=f"Модель недоступна: {error}")


@app.get("/insights/{insight_id}", response_model=InsightCard)
def get_insight(insight_id: str):
    return _call_service(service.get_insight, insight_id)

@app.get("/insights/{insight_id}/trace", response_model=list[TraceStep])
def get_trace(insight_id: str):
    return _call_service(service.get_trace, insight_id)

@app.post("/insights/{insight_id}/chat", response_model=ChatAnswer)
def chat(insight_id: str, data: ChatRequest):
    return _call_service(service.answer_question, insight_id, data.message)


DEMO_IDS = ["U_57706", "U_9250", "U_88715"]  # демо-клиенты из demo_companies.yaml


@app.get("/companies/demo", response_model=list[CompanyShort])
def get_demo_companies():
    result = []
    for number, company_id in enumerate(DEMO_IDS, start=1):
        profile = get_company_profile(company_id)
        result.append(CompanyShort(
            id=company_id,
            name=f"Клиент {number}",
            industry=profile["industry"]["okved_name"],
            region=profile["region"]["region"],
        ))
    return result


@app.get("/companies/{company_id}/feed", response_model=list[FeedItem])
def get_feed(company_id: str, role: UserRole = UserRole.ceo, limit: int = 10):
    items = get_feed_items(company_id, role.value, limit)
    if items is None:
        raise HTTPException(status_code=404, detail=f"Клиент {company_id} не найден")
    return items


@app.post("/auth/login", response_model=LoginResponse)
def login(data: LoginRequest): # пока что любой логин и пароль
    return LoginResponse(
        token="demo-token",
        user_name="Тестовый пользователь",
        role=UserRole.cfo,
        company_id="U_57706"
    )


@app.post("/insights/custom", response_model=InsightCard)
def custom_insight(data: CustomNewsRequest):
    return _call_service(service.custom_insight, data.company_id, data.role, data.text, data.url)


@app.get("/compare", response_model=CompareResult)
def compare(company_a: str, company_b: str, role: UserRole = UserRole.ceo):
    companies = {c.id: c for c in get_demo_companies()}
    for company_id in (company_a, company_b):
        if company_id not in companies:
            raise HTTPException(status_code=404, detail=f"Клиент {company_id} не найден")
    return CompareResult(
        company_a=companies[company_a],
        company_b=companies[company_b],
        feed_a=get_feed(company_a, role),
        feed_b=get_feed(company_b, role)
    )


@app.post("/feedback")
def feedback(data: FeedBackRequest):
    try:
        service.parse_insight_id(data.insight_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    insight_store.save_feedback(data.insight_id, data.useful, data.reason)
    return {"status": "ok"}


@app.get("/companies/{company_id}/profile")
def get_profile(company_id: str):
    profile = get_company_profile(company_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Клиент {company_id} не найден")
    return profile