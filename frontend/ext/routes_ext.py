"""Недостающие ручки витрины: счета, платежи, кредиты, аналитика, курсы.

Подключаются поверх приложения из репозитория, ничего в нём не меняя:
если команда позже сама добавит такую ручку, её версия останется
главной, а эта просто не будет использоваться.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from . import analytics_ext, demo_data
from .schemas_ext import (
    Account,
    AnalyticsSummary,
    CreditOffer,
    Payment,
)

router = APIRouter()


def _require_company(company_id: str) -> dict:
    item = demo_data.company(company_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Клиент %s не найден" % company_id)
    return item


def _insight_ids(company_id: str) -> list:
    """Id инсайтов из ленты бэкенда, чтобы аналитика ссылалась на них же."""
    try:
        from app.main import get_feed

        return [item.insight_id for item in get_feed(company_id)]
    except Exception:
        return []


@router.get("/companies/{company_id}")
def get_company(company_id: str):
    item = _require_company(company_id)
    return {
        "id": item["id"],
        "name": item["name"],
        "industry": item["industry"],
        "region": item["region"],
    }


@router.get("/companies/{company_id}/accounts", response_model=list[Account])
def get_accounts(company_id: str):
    _require_company(company_id)
    return [Account(**row) for row in demo_data.accounts(company_id)]


@router.get("/companies/{company_id}/payments", response_model=list[Payment])
def get_payments(company_id: str):
    _require_company(company_id)
    return [Payment(**row) for row in demo_data.payments(company_id)]


@router.get("/companies/{company_id}/credits", response_model=list[CreditOffer])
def get_credits(company_id: str):
    _require_company(company_id)
    return [CreditOffer(**row) for row in demo_data.credits(company_id)]


@router.get("/companies/{company_id}/analytics", response_model=AnalyticsSummary)
def get_analytics(company_id: str):
    _require_company(company_id)
    return analytics_ext.build_summary(company_id, _insight_ids(company_id))


@router.get("/fx")
def get_fx_rates():
    return {"base": demo_data.BASE_CURRENCY, "rates": dict(demo_data.FX_RATES)}
