from app.db import get_connection
from app.graph import top_counterparties

# отметки продуктов банка из таблицы companies (названия как в field_rules.yaml)
PRODUCT_FLAGS = ["has_rko", "has_gar", "has_loa", "has_lea", "has_dep", "has_zpp", "has_factoring"]


def get_company_profile(company_id: str) -> dict | None:
    """Профиль компании для скоринга и промптов. Если компании нет, вернёт None."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
        if row is None:
            return None
        group_size = None
        if row["group_id"]:
            group_size = conn.execute(
                "SELECT COUNT(*) FROM companies WHERE group_id = ?", (row["group_id"],)
            ).fetchone()[0]

    countries = [c.strip() for c in row["fts_countries"].split(",")] if row["fts_countries"] else []
    paying = top_counterparties(company_id, "out", 3)   # кому платит компания
    paid_by = top_counterparties(company_id, "in", 3)   # кто платит ей

    # пробелы в данных: чего мы НЕ знаем, чтобы выводы не были слишком смелыми
    gaps = []
    if row["revenue_is_stub"]:
        gaps.append("revenue_is_stub")
    if not row["stage"]:
        gaps.append("stage_unknown")
    if row["fts_flag"] and not countries:
        gaps.append("fts_countries_missing")
    if not paying["total"] and not paid_by["total"]:
        gaps.append("no_payments_data")

    return {
        "company_id": row["id"],
        "label": f"{row['okved_name']}, {row['region']}",
        "industry": {
            "okved_code": row["okved_code"],
            "okved_div": row["okved_div"],
            "okved_name": row["okved_name"],
        },
        "scale": {
            "revenue": None if row["revenue_is_stub"] else row["revenue"],
            "workers_fns": row["workers_fns"],
            "age_group": row["age_group"],
            "stage": row["stage"],
        },
        "region": {"city": row["city"], "region": row["region"]},
        "client_type": row["cl_type"],
        "bank_products": [flag for flag in PRODUCT_FLAGS if row[flag]],
        "foreign_trade": {"fts_flag": bool(row["fts_flag"]), "countries": countries},
        "group": {"group_id": row["group_id"], "size": group_size},
        "payments": {
            # доли считаем только по наблюдаемым платежам (это выборка, не весь оборот)
            "top_payer_share": paid_by["items"][0]["share"] if paid_by["items"] else None,
            "top_payee_share": paying["items"][0]["share"] if paying["items"] else None,
            "top_payers": paid_by["items"],
            "top_payees": paying["items"],
            "known_share_out": paying["known_share"],
            "known_share_in": paid_by["known_share"],
        },
        "data_gaps": gaps,
    }