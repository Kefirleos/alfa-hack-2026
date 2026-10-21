from enum import Enum

from pydantic import BaseModel


class ClaimType(str, Enum):
    fact = "fact" # какой-то подтвержденный факт из источника
    bank_view = "bank_view" # позиция Альфа-Банка
    ai_inference = "ai_inference" # что выводит модель
    ad = "ad" # реклама продукта банка


class Source(BaseModel):
    title: str
    url: str | None = None
    doc: str | None = None # файл аналитики от банка
    page: int | None = None


class Claim(BaseModel):
    text: str
    type: ClaimType
    sources: list[Source] = []
    features: list[str] = [] # некая информация о компании от которой зависел ответ
    confidence: str = "medium" # low/medium/high на выбор


class Event(BaseModel):
    title: str
    date: str
    summary: list[Claim]


class InsightCard(BaseModel):
    id: str
    company_id: str
    relevance: float
    event: Event
    why_it_matters: list[Claim]
    risks: list[Claim]
    opportunities: list[Claim]
    actions: list[Claim]
    bank_view: list[Claim]
    uncertainty: str | None = None


class ItemKind(str, Enum):
    risk = "risk" # событие несет риск
    opportunity = "opportunity" # событие дает возможность
    neutral = "neutral" # нейтральное, к сведению


class CompanyShort(BaseModel):
    id: str
    name: str # условное название (в данных названий компаний нету)
    industry: str # отрасль
    region: str


class FeedItem(BaseModel): # короткая версия карточки для ленты, insight_id совпадает со значением запроса /insights/{insight_id}
    insight_id: str # по нему откроется полная карточка
    title: str
    date: str
    relevance: float # от 0 до 1. Чем больше, тем значимее, и, соответственно, выше в ленте
    kind: ItemKind
    why_for_you: list[str] # пара коротких признаков компании
    source: str