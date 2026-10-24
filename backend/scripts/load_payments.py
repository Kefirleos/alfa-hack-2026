import csv
from pathlib import Path
from app.db import get_connection, init_db


RAW_CSV = Path(__file__).resolve().parents[1] / "data" / "raw" / "df_Uid_payment_hack.csv"


def main() -> None:
    init_db()
    with get_connection() as conn:
        company_ids = {row["id"] for row in conn.execute("SELECT id FROM companies")}
    if not company_ids:
        print("Таблица companies пуста: сначала запустите scripts.load_companies")
        return

    edges = {}  # (плательщик, получатель) - [сумма, количество платежей]
    total = self_pay = outside = 0
    with open(RAW_CSV, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            total += 1
            payer, receiver = r["PAYER"], r["BENEFICIARY"]
            if payer == receiver:
                self_pay += 1  # перевод самому себе, для графа бесполезен
                continue
            if payer not in company_ids and receiver not in company_ids:
                outside += 1  # обе стороны вне нашей таблицы компаний
                continue
            edge = edges.setdefault((payer, receiver), [0.0, 0])
            edge[0] += float(r["PAY_AMT"])
            edge[1] += int(float(r["PAY_CNT"]))

    rows = [(p, b, amount, cnt) for (p, b), (amount, cnt) in edges.items()]
    with get_connection() as conn:
        conn.execute("DELETE FROM payment_edges")  # чтобы повторный запуск не дублировал
        conn.executemany("INSERT INTO payment_edges VALUES (?, ?, ?, ?)", rows)
    print(f"Прочитано платежей: {total}")
    print(f"  самоплатежей пропущено: {self_pay}")
    print(f"  без наших компаний пропущено: {outside}")
    print(f"Загружено связей: {len(rows)}")


if __name__ == "__main__":
    main()