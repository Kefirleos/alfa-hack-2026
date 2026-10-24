"""Модели ответов, которых нет в бэкенде команды.

Бэкенд отдаёт только витрину и ленту. Вкладкам «Счета», «Платежи»,
«Кредиты» и «Аналитика» нужны свои структуры, поэтому они объявлены
здесь и не зависят от версии ``app.schemas`` в репозитории.
"""

from pydantic import BaseModel


class Account(BaseModel):
    id: str
    company_id: str
    name: str
    type: str
    currency: str
    balance: float
    turnover_month: float
    status: str
    opened_at: str


class Payment(BaseModel):
    id: str
    company_id: str
    date: str
    counterparty: str
    account_id: str
    amount: float
    currency: str
    direction: str
    category: str
    status: str
    comment: str


class CreditOffer(BaseModel):
    id: str
    company_id: str
    product: str
    limit: float
    currency: str
    rate: float
    term_months: int
    used: float
    status: str
    recommendation: str
    reason: str


class CategoryStat(BaseModel):
    category: str
    amount: float
    share: float


class MonthStat(BaseModel):
    month: str
    income: float
    expense: float


class CounterpartyStat(BaseModel):
    name: str
    amount: float
    share: float


class AnalyticsSummary(BaseModel):
    company_id: str
    currency: str
    accounts_count: int
    payments_count: int
    total_income: float
    total_expense: float
    net: float
    total_balance: float
    credit_limit_total: float
    credit_used_total: float
    credit_available_total: float
    by_category: list[CategoryStat]
    by_month: list[MonthStat]
    top_counterparties: list[CounterpartyStat]
    risk_level: str
    risk_notes: list[str]
    insight_ids: list[str]
