"""Поиск папки бэкенда рядом с фронтендом.

Папку ``frontend`` копируют в корень своего репозитория, поэтому путь
к бэкенду нельзя прописать жёстко: он ищется по наличию ``app/main.py``
с объектом FastAPI. Порядок: переменная окружения, известные варианты
рядом, затем поиск на пару уровней вглубь.
"""

from __future__ import annotations

import os
from pathlib import Path


def _looks_like_backend(path: Path) -> bool:
    return (path / "app" / "main.py").exists()


def find_backend(frontend: Path) -> Path | None:
    """Return the directory that contains ``app/main.py``, or None."""
    env = os.environ.get("ALFA_BACKEND", "").strip()
    if env:
        candidate = Path(env).expanduser()
        if _looks_like_backend(candidate):
            return candidate.resolve()

    root = frontend.resolve().parent
    for candidate in (
        root / "backend",
        root / "repo" / "backend",
        frontend / "backend",
        root / "back",
        root / "server",
    ):
        if _looks_like_backend(candidate):
            return candidate.resolve()

    for pattern in ("*/app/main.py", "*/*/app/main.py", "*/*/*/app/main.py"):
        for hit in sorted(root.glob(pattern)):
            if "site-packages" in str(hit) or ".venv" in str(hit):
                continue
            try:
                text = hit.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "FastAPI(" in text:
                return hit.parent.parent.resolve()
    return None
