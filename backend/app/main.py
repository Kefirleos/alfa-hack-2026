from fastapi import FastAPI, HTTPException
from app.schemas import ClaimType, Source, Claim, Event, InsightCard, ItemKind, CompanyShort, FeedItem, UserRole, LoginRequest, LoginResponse, TraceStep, ChatRequest, ChatAnswer, CustomNewsRequest, CompareResult, FeedBackRequest
from app.company_profile import get_company_profile
from app.scoring import get_feed_items
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="GenAlpha News Insights API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"], # надо заменить на реальный порт
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/insights/{insight_id}", response_model=InsightCard)
def get_insight(insight_id: str):
    # тексты в кавычках чисто символические, считайте что это демо-версия
    return InsightCard(
        id=insight_id,
        company_id="U_demo",
        relevance=0.5,
        event=Event(
            title="Заголовок события",
            date="2026-10-20",
            summary=[
                Claim(
                    text="Здесь будет описание того, что произошло",
                    type=ClaimType.fact,
                    sources=[Source(title="Название источника")]
                )
            ]
        ),
        why_it_matters=[
            Claim(
                text="Здесь будет объяснение того, почему это важно для компании",
                type=ClaimType.ai_inference,
                features=["какой-то признак компании"]
            )
        ],
        risks=[
            Claim(
                text="Здесь будет описание риска для компании",
                type=ClaimType.ai_inference,
                features=["признак компании"]
            )
        ],
        opportunities=[
            Claim(
                text="здесь будет описание возможности для компании",
                type=ClaimType.ai_inference,
                features=["признак компании"]
            )
        ],
        actions=[
            Claim(
                text="здесь будет предложение конкретного действия",
                type=ClaimType.ai_inference,
                features=["признак компании"]
            )
        ],
        bank_view=[
            Claim(
                text="Здесь будет позиция Альфа банка",
                type=ClaimType.bank_view,
                sources=[Source(title="Название документа", doc="файл_аналитики.pdf")]
            )
        ],
        uncertainty="На будущее для проверки формата"
    )


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
        company_id="U_demo1"
    )


@app.get("/insights/{insight_id}/trace", response_model=list[TraceStep])
def get_trace(insight_id: str): # здесь будут шаги агента
    return [
        TraceStep(step=1, name="Планирование", result="Определили, какие данные нужны"),
        TraceStep(step=2, name="Поиск новостей", tool="search_news", result="Нашли n новостей", sources=[Source(title="Название источника")]),
        TraceStep(step=3, name="Самопроверка", result="Проверрили, что у каждого вывода есть источник")
    ]


@app.post("/insights/{insight_id}/chat", response_model=ChatAnswer)
def chat(insight_id: str, data: ChatRequest): # ответ пока не зависит от вопроса
    return ChatAnswer(
        answer=[Claim(text="здесь будет ответ на вопрос пользователя", type=ClaimType.ai_inference)]
    )


@app.post("/insights/custom", response_model=InsightCard)
def custom_insight(data: CustomNewsRequest): # возвращаем ту же демку карточки
    return get_insight("ins_custom")


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
def feedback(data: FeedBackRequest): # пока ниче не сохраняется
    return {"status": "ok"}


@app.get("/companies/{company_id}/profile")
def get_profile(company_id: str):
    profile = get_company_profile(company_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Клиент {company_id} не найден")
    return profile