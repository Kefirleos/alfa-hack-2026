"""Данные витрины: курсы валют и доступ к данным клиента.

Счета, платежи и кредиты строятся в real_data.py по профилю настоящего
клиента, а здесь остаются курсы (демонстрационные) и тонкие обёртки,
чтобы остальной код ext/ не менялся.
"""

from __future__ import annotations

from typing import Dict, List

from . import real_data

BASE_CURRENCY = "RUB"
FX_RATES = {"RUB": 1.0, "USD": 95.0, "EUR": 103.0}


def company(company_id: str) -> Dict | None:
    return real_data.company(company_id)


def accounts(company_id: str) -> List[Dict]:
    return real_data.accounts(company_id)


def payments(company_id: str) -> List[Dict]:
    return real_data.payments(company_id)


def credits(company_id: str) -> List[Dict]:
    return real_data.credits(company_id)


def fx_rate(currency: str) -> float:
    return FX_RATES.get(currency, 1.0)


def to_base(amount: float, currency: str) -> float:
    """Пересчёт суммы в базовую валюту по демонстрационным курсам."""
    return round(amount * fx_rate(currency), 2)