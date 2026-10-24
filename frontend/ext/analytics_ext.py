"""Analytics over the demo dataset.

Everything here is computed from :mod:`demo_data` - no hardcoded
totals - so the numbers on the "Аналитика" tab always match the rows
shown on the "Платежи" and "Счета" tabs.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List

from . import demo_data
from .schemas_ext import (
    AnalyticsSummary,
    CategoryStat,
    CounterpartyStat,
    MonthStat,
)

# Внутрибанковский перевод не является ни доходом, ни расходом компании.
INTERNAL_CATEGORY = "Перевод между счетами"

# Категория, по которой считаем распределение операций (все, кроме переводов).
FLOW_CATEGORIES_EXCLUDE = {INTERNAL_CATEGORY}


def _base(row: Dict) -> float:
    return demo_data.to_base(row["amount"], row["currency"])


def _is_internal(row: Dict) -> bool:
    return row.get("category") in FLOW_CATEGORIES_EXCLUDE


def build_summary(company_id: str, insight_ids: Iterable[str] = ()) -> AnalyticsSummary:
    accounts = demo_data.accounts(company_id)
    payments = demo_data.payments(company_id)
    credits = demo_data.credits(company_id)

    income = 0.0
    expense = 0.0
    volume = 0.0
    by_category: Dict[str, float] = defaultdict(float)
    by_month: Dict[str, Dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    by_counterparty: Dict[str, float] = defaultdict(float)

    for row in payments:
        if _is_internal(row):
            # перевод между своими счетами не меняет поток компании
            continue
        amount = _base(row)
        month = row["date"][:7]
        if row["direction"] == "incoming":
            income += amount
            by_month[month]["income"] += amount
        else:
            expense += amount
            by_month[month]["expense"] += amount

        volume += abs(amount)
        by_category[row["category"]] += amount if row["direction"] == "incoming" else -amount
        by_counterparty[row["counterparty"]] += amount

    net = round(income - expense, 2)

    category_stats = []
    for name, amount in sorted(by_category.items(), key=lambda kv: abs(kv[1]), reverse=True):
        share = round(abs(amount) / volume, 4) if volume else 0.0
        category_stats.append(CategoryStat(category=name, amount=round(amount, 2), share=share))

    month_stats = [
        MonthStat(
            month=month,
            income=round(values["income"], 2),
            expense=round(values["expense"], 2),
        )
        for month, values in sorted(by_month.items())
    ]

    counterparty_stats = [
        CounterpartyStat(name=name, amount=round(amount, 2), share=round(abs(amount) / volume, 4) if volume else 0.0)
        for name, amount in sorted(by_counterparty.items(), key=lambda kv: abs(kv[1]), reverse=True)[:6]
    ]

    total_balance = round(sum(demo_data.to_base(a["balance"], a["currency"]) for a in accounts), 2)

    credit_limit_total = 0.0
    credit_used_total = 0.0
    for credit in credits:
        limit = demo_data.to_base(credit["limit"], credit["currency"])
        used = demo_data.to_base(credit["used"], credit["currency"])
        credit_limit_total += limit
        credit_used_total += used

    credit_available_total = round(credit_limit_total - credit_used_total, 2)
    utilisation = credit_used_total / credit_limit_total if credit_limit_total else 0.0

    critical: List[str] = []
    notes: List[str] = []

    if net < 0:
        text = "Отрицательный чистый денежный поток за период: расходы превышают поступления."
        critical.append(text)
        notes.append(text)

    if credit_limit_total and utilisation > 0.8:
        text = "Задействовано более 80%% кредитного лимита: свободная линия практически исчерпана."
        critical.append(text)
        notes.append(text)

    for stat in category_stats:
        if stat.share > 0.3 and stat.amount < 0:
            notes.append(
                "Доля категории «%s» в операциях превышает 30%% — высокая зависимость от одного направления."
                % stat.category
            )

    pending = [row for row in payments if row.get("status") != "Проведён"]
    if pending:
        notes.append("Операций в обработке: %d. Они ещё не отражены в фактическом остатке." % len(pending))

    monthly_expense = sum(stat.expense for stat in month_stats) / max(len(month_stats), 1)
    if total_balance and monthly_expense and total_balance < monthly_expense:
        text = "Совокупный остаток меньше среднего месячного расхода — стоит проверить ликвидность."
        critical.append(text)
        notes.append(text)

    if not notes:
        notes.append("Критичных отклонений не выявлено: поток положительный, лимит не исчерпан.")

    if len(critical) >= 2:
        risk_level = "Высокий"
    elif len(critical) == 1:
        risk_level = "Средний"
    elif notes and notes[0] != "Критичных отклонений не выявлено: поток положительный, лимит не исчерпан.":
        risk_level = "Умеренный"
    else:
        risk_level = "Низкий"

    return AnalyticsSummary(
        company_id=company_id,
        currency=demo_data.BASE_CURRENCY,
        accounts_count=len(accounts),
        payments_count=len(payments),
        total_income=round(income, 2),
        total_expense=round(expense, 2),
        net=net,
        total_balance=total_balance,
        credit_limit_total=round(credit_limit_total, 2),
        credit_used_total=round(credit_used_total, 2),
        credit_available_total=credit_available_total,
        by_category=category_stats,
        by_month=month_stats,
        top_counterparties=counterparty_stats,
        risk_level=risk_level,
        risk_notes=notes,
        insight_ids=list(insight_ids),
    )
