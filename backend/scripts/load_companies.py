import csv
from pathlib import Path
from app.db import get_connection, init_db


RAW_CSV = Path(__file__).resolve().parents[1] / "data" / "raw" / "df_Uid_data_hack.csv"


BAD_IDS = {"U_428697"} # этот ID встречается у 12 разных компаний: считаем это ошибкой в данных и пропускаем


def to_int(value: str):
    # в данных флаги равны 0.0 и 1.0, потому float
    return int(float(value)) if value.strip() else None


def to_text(value: str):
    # пустая строка = Null
    value = value.strip()
    return value if value else None


def main() -> None:
    init_db()
    rows = []
    skipped = 0
    with open(RAW_CSV, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["SYNTHETIC_U"] in BAD_IDS:
                skipped += 1
                continue
            revenue = float(r["REVENUE_COMPANY"])
            code = r["MAINOKVED_CODE"].strip()
            rows.append((
                r["SYNTHETIC_U"],
                code,
                code.split(".")[0], # в okved_div первые цифры до точки
                to_text(r["MAINOKVED_NAME"]),
                to_text(r["OKFS_NAME"]),
                to_text(r["COMPANY_AGE_YEARS_GRADATION"]),
                to_text(r["ECO_MARK_LABEL"]),
                to_int(r["NEGATIVEMARK"]),
                to_text(r["AMOUNT_WORKERS_FNS_GRADATION"]),
                to_text(r["CL_TYPE"]),
                to_int(r["CL_PRODUCT_RKO_MARK"]),
                to_int(r["CL_PRODUCT_GAR_MARK"]),
                to_int(r["CL_PRODUCT_LOA_MARK"]),
                to_int(r["CL_PRODUCT_LEA_MARK"]),
                to_int(r["CL_PRODUCT_DEP_MARK"]),
                to_int(r["CL_PRODUCT_ZPP_MARK"]),
                to_int(r["FACTORING_MARK"]),
                to_int(r["FTS_FLAG"]),
                to_text(r["FTS_COUNTRY_NAME"]),
                revenue,
                1 if revenue == 1000 else 0, # revenue_is_stub
                to_text(r["GROUP_ID"]),
                to_text(r["CITY"]),
                to_text(r["REGION"])
            ))

    with get_connection() as conn:
        conn.execute("DELETE FROM companies") # чтоб повторный запуск не повторялся
        conn.executemany("INSERT INTO companies VALUES (" + ",".join("?" * 24) + ")", rows)
        print(f"Загружено компаний: {len(rows)}, пропущено строк: {skipped}")


if __name__ == "__main__":
    main()