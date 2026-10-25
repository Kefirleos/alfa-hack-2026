"""Данные витрины для реальных клиентов: счета, платежи, кредиты.

В банковских данных нет остатков, операций и лимитов, поэтому они
моделируются по настоящему профилю клиента: масштаб берётся из выручки,
доли крупнейших покупателей и поставщиков из таблицы платежей, наличие
кредитных продуктов из отметок банка. Результат детерминирован: для одного
клиента всегда одни и те же строки.
"""

from __future__ import annotations

import random
from datetime import date
from functools import lru_cache
from typing import Dict, List

from app.company_profile import get_company_profile

TODAY = date(2026, 10, 23)  # дата самой свежей новости в снимке
MONTHS = 3
STUB_MONTHLY_PER_WORKER = 400_000.0  # если выручка неизвестна, оцениваем по числу сотрудников
WORKERS = {"1-15": 10, "16-100": 50, "101-250": 150, "Более 251": 400}

# продукт банка -> (название, ставка, срок в месяцах, множитель месячной выручки для лимита)
CREDIT_PRODUCTS = {
    "has_loa": ("Кредит на пополнение оборотных средств", 0.165, 12, 1.5),
    "has_lea": ("Лизинг", 0.18, 36, 1.0),
    "has_factoring": ("Факторинг", 0.17, 6, 0.8),
    "has_gar": ("Банковская гарантия", 0.04, 12, 0.5),
}
NOTE = "Смоделировано по профилю клиента"


def _day(back: int, rng: random.Random) -> date:
    """Случайный день внутри календарного месяца, отстоящего на back месяцев от текущего."""
    month = TODAY.month - back
    last = TODAY.day if back == 0 else 28
    return date(TODAY.year, month, rng.randint(1, last))


def _monthly_revenue(profile: dict) -> float:
    revenue = profile["scale"]["revenue"]
    if revenue:
        return revenue / 12
    workers = WORKERS.get(profile["scale"]["workers_fns"], 10)
    return workers * STUB_MONTHLY_PER_WORKER


@lru_cache(maxsize=None)
def _build(company_id: str) -> dict | None:
    profile = get_company_profile(company_id)
    if profile is None:
        return None
    rng = random.Random(company_id)
    month_revenue = _monthly_revenue(profile)
    products = profile["bank_products"]

    accounts: List[Dict] = []
    if "has_rko" in products:
        accounts.append({
            "id": f"{company_id}_rub", "company_id": company_id, "name": "Расчётный счёт",
            "type": "Расчётный", "currency": "RUB", "balance": round(month_revenue * 0.9, 2),
            "turnover_month": round(month_revenue * 1.8, 2), "status": "Активен", "opened_at": "",
        })
    if profile["foreign_trade"]["fts_flag"] and accounts:
        accounts.append({
            "id": f"{company_id}_usd", "company_id": company_id, "name": "Валютный счёт",
            "type": "Валютный", "currency": "USD", "balance": round(month_revenue * 0.04 / 95, 2),
            "turnover_month": round(month_revenue * 0.2 / 95, 2), "status": "Активен", "opened_at": "",
        })
    account_id = accounts[0]["id"] if accounts else ""

    pay = profile["payments"]
    payments: List[Dict] = []

    def add(day: date, counterparty: str, amount: float, direction: str, category: str, comment: str):
        payments.append({
            "id": f"{company_id}_p{len(payments) + 1}", "company_id": company_id,
            "date": day.isoformat(), "counterparty": counterparty, "account_id": account_id,
            "amount": round(amount, 2), "currency": "RUB", "direction": direction,
            "category": category, "status": "Проведён", "comment": comment,
        })

    for m in range(MONTHS):
        # поступления: крупные покупатели по их долям в платежах, остальное одной строкой
        income = month_revenue * rng.uniform(0.9, 1.1)
        rest = 1.0
        for i, item in enumerate(pay["top_payers"], start=1):
            share = min(item["share"], rest)
            rest -= share
            day = _day(m, rng)
            add(day, f"Покупатель {i}", income * share, "incoming", "Выручка", NOTE)
        if rest > 0.01:
            add(_day(m, rng), "Прочие покупатели", income * rest, "incoming", "Выручка", NOTE)

        # списания: крупные поставщики, налоги и зарплата
        cost = month_revenue * 0.8 * rng.uniform(0.9, 1.1)
        rest = 1.0
        for i, item in enumerate(pay["top_payees"], start=1):
            share = min(item["share"], rest)
            rest -= share
            day = _day(m, rng)
            category = item["okved_name"] or "Закупки"
            add(day, f"Поставщик {i}", cost * share, "outgoing", category[:40], NOTE)
        if rest > 0.01:
            add(_day(m, rng), "Прочие поставщики", cost * rest, "outgoing", "Закупки", NOTE)
        add(_day(m, rng), "ФНС", month_revenue * 0.03, "outgoing", "Налоги", NOTE)
        workers = WORKERS.get(profile["scale"]["workers_fns"], 10)
        add(_day(m, rng), "Сотрудники", min(workers * 80_000.0, month_revenue * 0.1), "outgoing", "Зарплата", NOTE)

    # последние операции ещё в обработке
    payments.sort(key=lambda row: row["date"], reverse=True)
    for row in payments[:2]:
        row["status"] = "В обработке"

    credits: List[Dict] = []
    for flag, (product, rate, term, factor) in CREDIT_PRODUCTS.items():
        if flag not in products:
            continue
        limit = round(month_revenue * factor, 2)
        credits.append({
            "id": f"{company_id}_{flag}", "company_id": company_id, "product": product,
            "limit": limit, "currency": "RUB", "rate": rate, "term_months": term,
            "used": round(limit * rng.uniform(0.3, 0.7), 2), "status": "Активен",
            "recommendation": "Действует",
            "reason": "Продукт подключён у клиента (отметка банка); лимит и ставка смоделированы",
        })

    return {
        "profile": profile, "accounts": accounts, "payments": payments, "credits": credits,
    }


def company(company_id: str) -> Dict | None:
    data = _build(company_id)
    if data is None:
        return None
    from app.main import DEMO_IDS  # импорт здесь, чтобы не было круговой зависимости

    profile = data["profile"]
    number = DEMO_IDS.index(company_id) + 1 if company_id in DEMO_IDS else None
    return {
        "id": company_id, "name": f"Клиент {number}" if number else company_id,
        "industry": profile["industry"]["okved_name"], "region": profile["region"]["region"],
    }


def accounts(company_id: str) -> List[Dict]:
    data = _build(company_id)
    return [dict(row) for row in data["accounts"]] if data else []


def payments(company_id: str) -> List[Dict]:
    data = _build(company_id)
    return [dict(row) for row in data["payments"]] if data else []


def credits(company_id: str) -> List[Dict]:
    data = _build(company_id)
    return [dict(row) for row in data["credits"]] if data else []