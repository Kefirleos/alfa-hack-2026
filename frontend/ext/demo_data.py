"""Demo dataset for the Alfa-Business prototype.

The upstream repository ships a stub backend: the endpoints answer with
hardcoded sample objects. This module keeps the same demo character but
gives every tab real rows to work with, so the frontend can be exercised
end to end without a data pipeline.

The data is clearly synthetic: company names, counterparties and figures
are placeholders, exactly like the objects already in ``app.main``.
"""

from __future__ import annotations

from typing import Dict, List

# --------------------------------------------------------------------------
# Companies
# --------------------------------------------------------------------------
COMPANIES: Dict[str, Dict[str, str]] = {
    "U_demo1": {
        "id": "U_demo1",
        "name": "Клиент 1",
        "industry": "Производство",
        "region": "Центральный ФО",
    },
    "U_demo2": {
        "id": "U_demo2",
        "name": "Клиент 2",
        "industry": "Логистика",
        "region": "Северо-Западный ФО",
    },
}

# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------
ACCOUNTS: List[Dict] = [
    {
        "id": "acc_001",
        "company_id": "U_demo1",
        "name": "Расчётный счёт №40702810",
        "type": "Расчётный",
        "currency": "RUB",
        "balance": 4_820_500.0,
        "turnover_month": 12_450_000.0,
        "status": "Активен",
        "opened_at": "2021-03-11",
    },
    {
        "id": "acc_002",
        "company_id": "U_demo1",
        "name": "Валютный счёт №40702811",
        "type": "Валютный",
        "currency": "USD",
        "balance": 318_400.0,
        "turnover_month": 1_120_000.0,
        "status": "Активен",
        "opened_at": "2022-09-02",
    },
    {
        "id": "acc_003",
        "company_id": "U_demo1",
        "name": "Накопительный счёт №40702812",
        "type": "Накопительный",
        "currency": "RUB",
        "balance": 26_900_000.0,
        "turnover_month": 0.0,
        "status": "Активен",
        "opened_at": "2023-01-19",
    },
    {
        "id": "acc_004",
        "company_id": "U_demo1",
        "name": "Зарплатный счёт №40702813",
        "type": "Зарплатный",
        "currency": "RUB",
        "balance": 1_240_800.0,
        "turnover_month": 8_960_000.0,
        "status": "Активен",
        "opened_at": "2020-06-30",
    },
    {
        "id": "acc_005",
        "company_id": "U_demo2",
        "name": "Расчётный счёт №40702820",
        "type": "Расчётный",
        "currency": "RUB",
        "balance": 1_960_300.0,
        "turnover_month": 6_310_000.0,
        "status": "Активен",
        "opened_at": "2020-11-05",
    },
    {
        "id": "acc_006",
        "company_id": "U_demo2",
        "name": "Валютный счёт №40702821",
        "type": "Валютный",
        "currency": "EUR",
        "balance": 92_150.0,
        "turnover_month": 410_000.0,
        "status": "Активен",
        "opened_at": "2023-05-22",
    },
    {
        "id": "acc_007",
        "company_id": "U_demo2",
        "name": "Резервный счёт №40702822",
        "type": "Резервный",
        "currency": "RUB",
        "balance": 740_000.0,
        "turnover_month": 0.0,
        "status": "Активен",
        "opened_at": "2024-02-14",
    },
]

# --------------------------------------------------------------------------
# Payments
# --------------------------------------------------------------------------
PAYMENTS: List[Dict] = [
    {
        "id": "pay_001",
        "company_id": "U_demo1",
        "date": "2026-10-20",
        "counterparty": "Поставщик «Северный Металл»",
        "account_id": "acc_001",
        "amount": 1_845_000.0,
        "currency": "RUB",
        "direction": "outgoing",
        "category": "Закупка сырья",
        "status": "Проведён",
        "comment": "Партия металлопроката, № 44-118",
    },
    {
        "id": "pay_002",
        "company_id": "U_demo1",
        "date": "2026-10-20",
        "counterparty": "Покупатель ООО «Альянс Трейд»",
        "account_id": "acc_001",
        "amount": 3100000.0,
        "currency": "RUB",
        "direction": "incoming",
        "category": "Выручка",
        "status": "Проведён",
        "comment": "Оплата по договору поставки",
    },
    {
        "id": "pay_003",
        "company_id": "U_demo1",
        "date": "2026-10-19",
        "counterparty": "ФНС",
        "account_id": "acc_001",
        "amount": 940_500.0,
        "currency": "RUB",
        "direction": "outgoing",
        "category": "Налоги",
        "status": "Проведён",
        "comment": "Авансовый платёж по НДС",
    },
    {
        "id": "pay_004",
        "company_id": "U_demo1",
        "date": "2026-10-19",
        "counterparty": "Покупатель ООО «Вектор Групп»",
        "account_id": "acc_001",
        "amount": 2100000.0,
        "currency": "RUB",
        "direction": "incoming",
        "category": "Выручка",
        "status": "Проведён",
        "comment": "Отгрузка по договору № 18/26",
    },
    {
        "id": "pay_005",
        "company_id": "U_demo1",
        "date": "2026-10-18",
        "counterparty": "Подрядчик «СтройИнвест»",
        "account_id": "acc_001",
        "amount": 720_300.0,
        "currency": "RUB",
        "direction": "outgoing",
        "category": "Подряд",
        "status": "В обработке",
        "comment": "Строительно-монтажные работы",
    },
    {
        "id": "pay_006",
        "company_id": "U_demo1",
        "date": "2026-10-18",
        "counterparty": "Поставщик «Логистик Плюс»",
        "account_id": "acc_001",
        "amount": 388_000.0,
        "currency": "RUB",
        "direction": "outgoing",
        "category": "Логистика",
        "status": "Проведён",
        "comment": "Доставка по маршруту 12",
    },
    {
        "id": "pay_007",
        "company_id": "U_demo1",
        "date": "2026-10-17",
        "counterparty": "Контрагент «Euro Parts GmbH»",
        "account_id": "acc_002",
        "amount": 48000.0,
        "currency": "USD",
        "direction": "outgoing",
        "category": "Закупка сырья",
        "status": "Проведён",
        "comment": "Комплектующие, инвойс EP-2026-441",
    },
    {
        "id": "pay_008",
        "company_id": "U_demo1",
        "date": "2026-10-16",
        "counterparty": "Фонд социального страхования",
        "account_id": "acc_004",
        "amount": 1_180_000.0,
        "currency": "RUB",
        "direction": "outgoing",
        "category": "Зарплата",
        "status": "Проведён",
        "comment": "Страховые взносы за сентябрь",
    },
    {
        "id": "pay_009",
        "company_id": "U_demo1",
        "date": "2026-10-15",
        "counterparty": "Покупатель ООО «Альянс Трейд»",
        "account_id": "acc_001",
        "amount": 2600000.0,
        "currency": "RUB",
        "direction": "incoming",
        "category": "Выручка",
        "status": "Проведён",
        "comment": "Повторная оплата по договору",
    },
    {
        "id": "pay_010",
        "company_id": "U_demo1",
        "date": "2026-10-14",
        "counterparty": "Банк «Альфа-Банк»",
        "account_id": "acc_003",
        "amount": 4_000_000.0,
        "currency": "RUB",
        "direction": "outgoing",
        "category": "Перевод между счетами",
        "status": "Проведён",
        "comment": "Размещение средств на накопительном счёте",
    },
    {
        "id": "pay_011",
        "company_id": "U_demo1",
        "date": "2026-10-13",
        "counterparty": "Поставщик «Северный Металл»",
        "account_id": "acc_001",
        "amount": 1_220_000.0,
        "currency": "RUB",
        "direction": "outgoing",
        "category": "Закупка сырья",
        "status": "Проведён",
        "comment": "Партия металлопроката, № 44-117",
    },
    {
        "id": "pay_012",
        "company_id": "U_demo1",
        "date": "2026-10-12",
        "counterparty": "Покупатель ООО «Вектор Групп»",
        "account_id": "acc_001",
        "amount": 2350000.0,
        "currency": "RUB",
        "direction": "incoming",
        "category": "Выручка",
        "status": "Проведён",
        "comment": "Отгрузка по договору № 17/26",
    },
    {
        "id": "pay_013",
        "company_id": "U_demo2",
        "date": "2026-10-20",
        "counterparty": "Заказчик ООО «ТрансЛайн»",
        "account_id": "acc_005",
        "amount": 1_480_000.0,
        "currency": "RUB",
        "direction": "incoming",
        "category": "Выручка",
        "status": "Проведён",
        "comment": "Перевозка партии, маршрут 44",
    },
    {
        "id": "pay_014",
        "company_id": "U_demo2",
        "date": "2026-10-19",
        "counterparty": "Поставщик «Топливная Компания»",
        "account_id": "acc_005",
        "amount": 640_000.0,
        "currency": "RUB",
        "direction": "outgoing",
        "category": "Топливо",
        "status": "Проведён",
        "comment": "Аванс за горюче-смазочные материалы",
    },
    {
        "id": "pay_015",
        "company_id": "U_demo2",
        "date": "2026-10-18",
        "counterparty": "Контрагент «Rhein Cargo GmbH»",
        "account_id": "acc_006",
        "amount": 41_000.0,
        "currency": "EUR",
        "direction": "incoming",
        "category": "Выручка",
        "status": "Проведён",
        "comment": "Международный рейс",
    },
    {
        "id": "pay_016",
        "company_id": "U_demo2",
        "date": "2026-10-17",
        "counterparty": "Страховая компания «Щит»",
        "account_id": "acc_005",
        "amount": 215_000.0,
        "currency": "RUB",
        "direction": "outgoing",
        "category": "Страхование",
        "status": "Проведён",
        "comment": "Страхование автопарка",
    },
    {
        "id": "pay_017",
        "company_id": "U_demo2",
        "date": "2026-10-16",
        "counterparty": "ФНС",
        "account_id": "acc_005",
        "amount": 310_000.0,
        "currency": "RUB",
        "direction": "outgoing",
        "category": "Налоги",
        "status": "Проведён",
        "comment": "Налог на прибыль",
    },
    {
        "id": "pay_018",
        "company_id": "U_demo2",
        "date": "2026-10-15",
        "counterparty": "Поставщик «Топливная Компания»",
        "account_id": "acc_005",
        "amount": 588_000.0,
        "currency": "RUB",
        "direction": "outgoing",
        "category": "Топливо",
        "status": "В обработке",
        "comment": "Оплата по договору поставки",
    },
    {
        "id": "pay_019",
        "company_id": "U_demo1",
        "date": "2026-09-28",
        "counterparty": "Покупатель ООО «Вектор Групп»",
        "account_id": "acc_001",
        "amount": 2150000.0,
        "currency": "RUB",
        "direction": "incoming",
        "category": "Выручка",
        "status": "Проведён",
        "comment": "Отгрузка по договору № 16/26",
    },
    {
        "id": "pay_020",
        "company_id": "U_demo1",
        "date": "2026-09-24",
        "counterparty": "Поставщик «Северный Металл»",
        "account_id": "acc_001",
        "amount": 1_640_000.0,
        "currency": "RUB",
        "direction": "outgoing",
        "category": "Закупка сырья",
        "status": "Проведён",
        "comment": "Партия металлопроката, № 44-109",
    },
    {
        "id": "pay_021",
        "company_id": "U_demo1",
        "date": "2026-09-18",
        "counterparty": "Подрядчик «СтройИнвест»",
        "account_id": "acc_001",
        "amount": 640_000.0,
        "currency": "RUB",
        "direction": "outgoing",
        "category": "Подряд",
        "status": "Проведён",
        "comment": "Ремонт производственной линии",
    },
    {
        "id": "pay_022",
        "company_id": "U_demo1",
        "date": "2026-09-11",
        "counterparty": "Покупатель ООО «Альянс Трейд»",
        "account_id": "acc_001",
        "amount": 2400000.0,
        "currency": "RUB",
        "direction": "incoming",
        "category": "Выручка",
        "status": "Проведён",
        "comment": "Оплата по договору поставки",
    },
    {
        "id": "pay_023",
        "company_id": "U_demo2",
        "date": "2026-09-29",
        "counterparty": "Заказчик ООО «ТрансЛайн»",
        "account_id": "acc_005",
        "amount": 1_290_000.0,
        "currency": "RUB",
        "direction": "incoming",
        "category": "Выручка",
        "status": "Проведён",
        "comment": "Перевозка партии, маршрут 38",
    },
    {
        "id": "pay_024",
        "company_id": "U_demo2",
        "date": "2026-09-21",
        "counterparty": "Поставщик «Топливная Компания»",
        "account_id": "acc_005",
        "amount": 705_000.0,
        "currency": "RUB",
        "direction": "outgoing",
        "category": "Топливо",
        "status": "Проведён",
        "comment": "Оплата по договору поставки",
    },
    {
        "id": "pay_025",
        "company_id": "U_demo2",
        "date": "2026-09-12",
        "counterparty": "Заказчик ООО «ТрансЛайн»",
        "account_id": "acc_005",
        "amount": 1_150_000.0,
        "currency": "RUB",
        "direction": "incoming",
        "category": "Выручка",
        "status": "Проведён",
        "comment": "Перевозка партии, маршрут 31",
    },
]

# --------------------------------------------------------------------------
# Курсы для пересчёта в базовую валюту (демонстрационные)
# --------------------------------------------------------------------------
BASE_CURRENCY = "RUB"
FX_RATES = {"RUB": 1.0, "USD": 95.0, "EUR": 103.0}

# --------------------------------------------------------------------------
# Credits
# --------------------------------------------------------------------------
CREDITS: List[Dict] = [
    {
        "id": "cr_001",
        "company_id": "U_demo1",
        "product": "Оборотный кредит",
        "limit": 12000000.0,
        "currency": "RUB",
        "rate": 0.1485,
        "term_months": 12,
        "used": 11500000.0,
        "status": "Активен",
        "recommendation": "Рекомендуется",
        "reason": "Оборотные средства покрывают закупку сырья с запасом 1.5 месяца",
    },
    {
        "id": "cr_002",
        "company_id": "U_demo1",
        "product": "Кредитная линия",
        "limit": 8_000_000.0,
        "currency": "RUB",
        "rate": 0.1610,
        "term_months": 24,
        "used": 0.0,
        "status": "Доступен",
        "recommendation": "Рекомендуется",
        "reason": "Финансирование под залог оборудования, свободный лимит 8 млн ₽",
    },
    {
        "id": "cr_003",
        "company_id": "U_demo1",
        "product": "Валютный кредит",
        "limit": 200000.0,
        "currency": "USD",
        "rate": 0.0920,
        "term_months": 12,
        "used": 48000.0,
        "status": "Активен",
        "recommendation": "На рассмотрении",
        "reason": "Валютная выручка покрывает обслуживание, но растёт долларовая экспозиция",
    },
    {
        "id": "cr_004",
        "company_id": "U_demo2",
        "product": "Оборотный кредит",
        "limit": 10_000_000.0,
        "currency": "RUB",
        "rate": 0.1540,
        "term_months": 12,
        "used": 3_100_000.0,
        "status": "Активен",
        "recommendation": "Рекомендуется",
        "reason": "Стабильный денежный поток от транспортных заказов",
    },
    {
        "id": "cr_005",
        "company_id": "U_demo2",
        "product": "Линия под залог автопарка",
        "limit": 6_000_000.0,
        "currency": "RUB",
        "rate": 0.1690,
        "term_months": 36,
        "used": 0.0,
        "status": "Доступен",
        "recommendation": "На рассмотрении",
        "reason": "Обновление парка: свободный лимит 6 млн ₽ под залог техники",
    },
]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def companies() -> List[Dict]:
    return [dict(item) for item in COMPANIES.values()]


def company(company_id: str) -> Dict | None:
    item = COMPANIES.get(company_id)
    return dict(item) if item else None


def accounts(company_id: str) -> List[Dict]:
    return [dict(item) for item in ACCOUNTS if item["company_id"] == company_id]


def payments(company_id: str) -> List[Dict]:
    rows = [dict(item) for item in PAYMENTS if item["company_id"] == company_id]
    rows.sort(key=lambda row: row["date"], reverse=True)
    return rows


def credits(company_id: str) -> List[Dict]:
    return [dict(item) for item in CREDITS if item["company_id"] == company_id]


def fx_rate(currency: str) -> float:
    return FX_RATES.get(currency, 1.0)


def to_base(amount: float, currency: str) -> float:
    """Convert a payment amount into the base currency using demo rates."""
    return round(amount * fx_rate(currency), 2)
