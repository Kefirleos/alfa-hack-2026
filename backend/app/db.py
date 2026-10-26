import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "app.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # читаем строки по имени колонки
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY, -- SYNTHETIC_U
    okved_code TEXT, -- MAINOKVED_CODE из данных
    okved_div TEXT, -- раздел ОКВЭД: цифры кода до первой точки
    okved_name TEXT,
    ownership TEXT, -- OKFS_NAME
    age_group TEXT,
    stage TEXT, -- ECO_MARK_LABEL
    negative_mark INTEGER, -- NEGATIVEMARK, признак ключевого собственника, в выводах не используется
    workers_fns TEXT,
    cl_type TEXT, -- CLIENT / PROSPECT / CLOSE_CLIENT
    has_rko INTEGER,
    has_gar INTEGER,
    has_loa INTEGER,
    has_lea INTEGER,
    has_dep INTEGER,
    has_zpp INTEGER,
    has_factoring INTEGER,
    fts_flag INTEGER,
    fts_countries TEXT, -- страны подаются через запятую
    revenue REAL,
    revenue_is_stub INTEGER, -- 1, если выручка ровно 1000 (заглушка в данных)
    group_id TEXT,
    city TEXT,
    region TEXT
);
CREATE TABLE IF NOT EXISTS payment_edges (
    payer TEXT NOT NULL,        -- PAYER: кто платит
    receiver TEXT NOT NULL,     -- BENEFICIARY: кому платят
    amount REAL NOT NULL,       -- PAY_AMT, сумма всех платежей этой пары
    cnt INTEGER NOT NULL,       -- PAY_CNT, число платежей
    PRIMARY KEY (payer, receiver)
);
CREATE INDEX IF NOT EXISTS idx_edges_payer ON payment_edges(payer);
CREATE INDEX IF NOT EXISTS idx_edges_receiver ON payment_edges(receiver);
"""


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)