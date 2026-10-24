"""Точка входа для uvicorn: бэкенд репозитория + недостающие ручки.

Запускается лаунчером как ``uvicorn ext.app_ext:app --app-dir <frontend>``,
рабочая папка - папка бэкенда (там лежат ``app``, ``data`` и ``.env``).

Приложение команды импортируется как есть; сверху добавляются только
те ручки, которых в нём нет, и заголовки CORS на адрес фронтенда.
Ни один файл в репозитории не изменяется.
"""

from __future__ import annotations

import sys
from pathlib import Path

EXT_DIR = Path(__file__).resolve().parent
FRONTEND = EXT_DIR.parent
ROOT = FRONTEND.parent

from .backend_locator import find_backend
from .routes_ext import router as ext_router

BACKEND = find_backend(FRONTEND)
if BACKEND is None:
    raise RuntimeError(
        "Не нашёл папку бэкенда рядом с frontend. "
        "Положи папку frontend в корень репозитория (там, где лежит backend/app/main.py) "
        "или укажи путь в переменной ALFA_BACKEND."
    )

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.main import app  # noqa: E402  (приложение команды)

from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from starlette.middleware import Middleware  # noqa: E402

ALLOWED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]

# У приложения из репозитория свой список источников (без 127.0.0.1),
# поэтому его middleware заменяется на такой же, но с адресом фронтенда.
app.user_middleware = [
    item for item in app.user_middleware if item.cls is not CORSMiddleware
]
app.user_middleware.insert(
    0,
    Middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    ),
)

app.include_router(ext_router)

__all__ = ["app", "BACKEND"]
