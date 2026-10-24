from app.db import get_connection


def top_counterparties(company_id: str, direction: str = "out", limit: int = 5) -> dict:
    """Главные контрагенты компании по платежам.

    direction="out": кому платит компания; direction="in": кто платит ей.
    """
    if direction == "out":
        me, other = "payer", "receiver"
    elif direction == "in":
        me, other = "receiver", "payer"
    else:
        raise ValueError("direction должен быть 'out' или 'in'")

    with get_connection() as conn:
        # сумма всех платежей компании в этом направлении (без самоплатежей)
        total = conn.execute(
            f"SELECT COALESCE(SUM(amount), 0) FROM payment_edges WHERE {me} = ?",
            (company_id,),
        ).fetchone()[0]

        # сумма платежей тем контрагентам, которые есть в нашей таблице компаний
        known = conn.execute(
            f"""SELECT COALESCE(SUM(e.amount), 0) FROM payment_edges e
                JOIN companies c ON c.id = e.{other}
                WHERE e.{me} = ?""",
            (company_id,),
        ).fetchone()[0]

        rows = conn.execute(
            f"""SELECT e.{other} AS id, e.amount, c.okved_div, c.okved_name, c.region
                FROM payment_edges e LEFT JOIN companies c ON c.id = e.{other}
                WHERE e.{me} = ?
                ORDER BY e.amount DESC LIMIT ?""",
            (company_id, limit),
        ).fetchall()

    return {
        "total": total,
        "known_share": known / total if total else None,  # доля контрагентов с известной отраслью
        "items": [
            {
                "id": r["id"],
                "amount": r["amount"],
                "share": r["amount"] / total if total else None,
                "okved_div": r["okved_div"],
                "okved_name": r["okved_name"],
                "region": r["region"],
            }
            for r in rows
        ],
    }