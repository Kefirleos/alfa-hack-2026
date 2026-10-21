from fastapi import FastAPI
from app.schemas import ClaimType, Source, Claim, Event, InsightCard, ItemKind, CompanyShort, FeedItem, UserRole, LoginRequest, LoginResponse, TraceStep, ChatRequest, ChatAnswer
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


@app.get("/companies/demo", response_model=list[CompanyShort])
def get_demo_companies():
    # тоже демка, позже здесь будут лежать данные клиентов
    return [
        CompanyShort(id="U_demo1", name="Клиент 1", industry="Название отрасли", region="Название региона"),
        CompanyShort(id="U_demo2", name="Клиент 2", industry="Название отрасли", region="Название региона")
    ]


@app.get("/companies/{company_id}/feed", response_model=list[FeedItem])
def get_feed(company_id: str):
    # временная мера тк лента не персонализирована еще (у всех клиентов она одинакова)
    return [
        FeedItem(
            insight_id="ins_001",
            title="Заголовок события 1",
            date="2026-10-20",
            relevance=0.9,
            kind=ItemKind.risk,
            why_for_you=["признак компании 1", "признак компании 2"],
            source="Название источника"
        ),
        FeedItem(
            insight_id="ins_002",
            title="Заголовок события 2",
            date="2026-10-19",
            relevance=0.3,
            kind=ItemKind.opportunity,
            why_for_you=["признак компании 1"],
            source="Название источника"
        )
    ]


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