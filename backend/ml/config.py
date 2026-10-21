import os
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1] 
REPO_DIR = BACKEND_DIR.parent                       

for env_file in (REPO_DIR / ".env", BACKEND_DIR / ".env"):
    if env_file.exists():
        load_dotenv(env_file, override=False)

def _path(var: str, default: str) -> Path:
    p = Path(os.getenv(var, default))
    if p.is_absolute():
        return p
    return (BACKEND_DIR / p).resolve()


REFERENCE_DIR = _path("REFERENCE_DIR", "./data/reference")
LLM_CACHE_DIR = _path("LLM_CACHE_DIR", "./llm_cache")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_TIMEOUT = os.getenv("LLM_TIMEOUT", "90")
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "0") == "1"

RAW_DIR       = _path("RAW_DATA_DIR",  "./data/raw")
PROCESSED_DIR = _path("PROCESSED_DIR", "./data/processed")

DATA_FILE = RAW_DIR / "df_Uid_data_hack.csv"
PAYMENTS_FILE = RAW_DIR / "df_Uid_payment_hack.csv"
LINKS_FILE = RAW_DIR / "df_Fid_Uid_link_hack.csv"
