from fastapi import FastAPI
from app.schemas import ClaimType, Source, Claim, Event, InsightCard

app = FastAPI(title="GenAlpha News Insights API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/insights/{insight_id}", response_model=InsightCard)
def get_insight(insight_id: str):
    # тексты в кавычках чисто симолические, считайте что это демо-версия
    return InsightCard(
        id=insight_id,
        company_id="U_demo",
        relevance=0.5,
        event = Event(
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
                type=ClaimType.ai_reference,
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
                text="здесь будет предложение конкретнорго действия",
                type=ClaimType.ai_inference,
                features=["признак компании"]
            )
        ],
        bank_view=[
            Claim(
                text="Здесь будет позиция Альфа банка",
                type=ClaimType.bank_view,
                sources=[Source(doc="файл_аеалитики.pdf")]
            )
        ],
        uncertainty="На будущее для проверки формата"
    )