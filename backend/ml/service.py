from app.schemas import (
    ChatAnswer,
    Claim,
    ClaimType,
    CompanyShort,
    Event,
    FeedItem,
    InsightCard,
    ItemKind,
    Source,
    TraceStep,
    UserRole,
)

STUB = True

class CompanyNotFound(LookupError):
    ""

def make_insight_id(company_id: str, event_id:str, role: UserRole) -> str:
    return f"{company_id}__{event_id}__{role.value}"

def parse_insight_id(insight_id:str) -> tuple[str, str, UserRole]:
    parts = insight_id.split("__")
    if len(parts) != 3:
        raise ValueError("insight_id should be in the format company__event__role")
    company_id, event_id, role_value = parts
    try:
        role = UserRole(role_value)
    except ValueError:
        raise ValueError("Unknown role")
    return company_id, event_id, role

_COMPANIES = {
    "U_demo1": CompanyShort(id="U_demo1", name="Клиент 1",
                            industry="Производство металлоконструкций", region="Свердловская область"),
    "U_demo2": CompanyShort(id="U_demo2", name="Клиент 2",
                            industry="Оптовая торговля продуктами питания", region="Москва"),
}
 
_PROFILES = {
    "U_demo1": {
        "scale": "крупный бизнес",
        "products": ["РКО", "кредит", "лизинг"],
        "foreign_trade_countries": [],
        "topics": ["ключевая ставка", "цены на металл", "строительство"],
        "top_counterparty_industries": ["металлургия", "строительство"],
        "data_gaps": [],
    },
    "U_demo2": {
        "scale": "крупный бизнес",
        "products": ["РКО", "депозит", "ВЭД"],
        "foreign_trade_countries": ["Китай", "Турция"],
        "topics": ["курс CNY", "пошлины на импорт", "потребительский спрос"],
        "top_counterparty_industries": ["пищевое производство", "розничная торговля"],
        "data_gaps": ["выручка (в данных заглушка 1000)"],
    },
}
 
# у каждой компании своя ленты
_FEEDS = {
    "U_demo1": [
        ("E_rate", "Банк России сохранил ключевую ставку", "2026-10-20", 0.91, ItemKind.risk,
         ["у вас кредит и лизинг", "капиталоёмкая отрасль"], "cbr.ru"),
        ("E_steel", "Цены на арматуру снизились третью неделю подряд", "2026-10-19", 0.72, ItemKind.opportunity,
         ["ваши контрагенты — металлургия", "отрасль: металлоконструкции"], "minpromtorg.gov.ru"),
        ("E_tax", "Минфин уточнил порядок уплаты НДС", "2026-10-15", 0.30, ItemKind.neutral,
         ["затрагивает всех плательщиков НДС"], "minfin.gov.ru"),
    ],
    "U_demo2": [
        ("E_cny", "Курс юаня опустился до минимума за три месяца", "2026-10-18", 0.88, ItemKind.opportunity,
         ["ВЭД с Китаем", "импорт в юанях"], "cbr.ru"),
        ("E_duty", "Правительство повышает пошлины на часть импортных продуктов", "2026-10-17", 0.81, ItemKind.risk,
         ["вы импортируете продукты", "страны-партнёры: Китай, Турция"], "government.ru"),
        ("E_rate", "Банк России сохранил ключевую ставку", "2026-10-20", 0.45, ItemKind.opportunity,
         ["у вас депозит: доходность сохранится"], "cbr.ru"),
    ],
}

def _company(company_id:str) -> CompanyShort:
    if company_id not in _COMPANIES:
        raise CompanyNotFound("The client was not found")
    return _COMPANIES[company_id]

def list_companies(query:str | None = None, limit: int = 50) -> list[CompanyShort]:
    companies = list(_COMPANIES.values())
    if query:
        query_lower = query.lower()
        companies = [
            company for company in companies
            if query_lower in company.name.lower() or query_lower in company.industry.lower()
        ]
    return companies[:limit]

def get_company(company_id:str) -> dict:
    company = _company(company_id)
    return {**company.model_dump(), **_PROFILES[company_id]}

def get_feed(company_id:str, role: UserRole = UserRole.ceo, days: int = 30, limit: int = 20) -> list[FeedItem]:
    _company(company_id)
    items = [
        FeedItem(
            insight_id=make_insight_id(company_id, event_id, role),
            title= title,
            date=date, 
            relevance=relevance,
            kind=kind,
            why_for_you=why,
            source = source
        )
        for event_id, title, date, relevance, kind, why, source in _FEEDS[company_id]
    ]
    items.sort(key=lambda item: item.relevance, reverse=True)
    return items[:limit]

def get_insight(insight_id:str) -> InsightCard:
    company_id, event_id, role = parse_insight_id(insight_id)
    _company(company_id)

    news = Source(title="Банк России: решение по ключевой ставке", url="https://cbr.ru/press/keypr/")
    bank_doc = Source(title="Macro Insights: ключевая ставка", doc="ALFA-Macro_Insights-Policy_Rate_11Sep.pdf", page=3)

    return InsightCard(
        id=insight_id,
        company_id=company_id,
        relevance=0.91,
        event=Event(
            title="Банк России сохранил ключевую ставку",
            date="2026-10-20",
            summary=[
                Claim(text="Совет директоров Банка России сохранил ключевую ставку.",
                      type=ClaimType.fact, sources=[news], confidence="high"),
            ],
        ),
        why_it_matters=[
            Claim(text="У компании есть кредит и лизинг: стоимость обслуживания долга останется высокой.",
                  type=ClaimType.ai_inference, features=["has_loa", "has_lea"]),
        ],
        risks=[
            Claim(text="Рефинансирование в ближайший квартал будет дороже, чем ожидалось.",
                  type=ClaimType.ai_inference, features=["has_loa"]),
        ],
        opportunities=[
            Claim(text="Свободные остатки можно разместить на депозите под высокую ставку.",
                  type=ClaimType.ai_inference, features=["has_rko"]),
        ],
        actions=[
            Claim(text="Обсудить с казначеем график погашения и фиксацию ставки.",
                  type=ClaimType.ai_inference, features=["has_loa"]),
            Claim(text="Депозиты Альфа-Банка для бизнеса — для размещения свободных остатков.",
                  type=ClaimType.ad),
        ],
        bank_view=[
            Claim(text="Аналитики банка ожидают начала снижения ставки не раньше следующего года.",
                  type=ClaimType.bank_view, sources=[bank_doc]),
        ],
        uncertainty="Заглушка: данные демонстрационные.",
    )
 
def get_trace(insgiht_id: str) -> list[TraceStep]:
    company_id, event_id, role = parse_insight_id(insgiht_id)
    _company(company_id)
    return [
        TraceStep(step=1, name="Профиль компании", tool="get_company_profile",
                  result="Отрасль, продукты банка (кредит, лизинг), контрагенты"),
        TraceStep(step=2, name="Поиск аналитики банка", tool="search_alfa_analytics",
                  result="Найден фрагмент о прогнозе ключевой ставки",
                  sources=[Source(title="Macro Insights: ключевая ставка",
                                  doc="ALFA-Macro_Insights-Policy_Rate_11Sep.pdf", page=3)]),
        TraceStep(step=3, name="Похожие события", tool="search_related_news",
                  result="2 похожих решения по ставке за последние полгода"),
        TraceStep(step=4, name="Самопроверка", tool=None,
                  result="У каждого факта и позиции банка есть источник, выводы опираются на признаки компании"),
    ]

def answer_question(insgiht_id: str, message: str) -> ChatAnswer:
    company_id, event_id, role = parse_insight_id(insgiht_id)
    _company(company_id)
    return ChatAnswer(answer=[
        Claim(text=f"Вопрос: «{message[:100]}». Здесь будет ответ по разбору с учётом данных компании.",
        type=ClaimType.ai_inference, features=["has_loa"]),
    ])

def custom_insight(company_id: str, role: UserRole, text: str | None = None, url: str | None = None) -> InsightCard:
    if not text and not url:
        raise ValueError("Need text or url")
    _company(company_id)
    card = get_insight(make_insight_id(company_id, "E_custom", role))
    card.event.title = (text or url)[:120]
    return card
