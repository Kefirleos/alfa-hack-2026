import hashlib
import json
import re

from app.schemas import ChatAnswer, InsightCard, TraceStep
from ml import config
from datetime import datetime, timezone

INSIGHTS_DIR = config.PROCESSED_DIR.parent / "insights"
DEMO_DIR = config.PROCESSED_DIR.parents[1] / "demo_cache"


def _path(folder, insight_id: str):
    return folder / f"{insight_id}.json"


def _load(insight_id: str) -> dict | None:
    for folder in (INSIGHTS_DIR, DEMO_DIR):
        path = _path(folder, insight_id)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def get(insight_id: str) -> tuple[InsightCard, list[TraceStep]] | None:
    data = _load(insight_id)
    if data is None:
        return None
    card = InsightCard.model_validate(data["card"])
    trace = [TraceStep.model_validate(step) for step in data["trace"]]
    return card, trace


def get_context(insight_id: str) -> dict | None:
    data = _load(insight_id)
    return data.get("context") if data else None


def save(insight_id: str, card: InsightCard, trace: list[TraceStep], context: dict | None = None, demo: bool = False) -> None:
    folder = DEMO_DIR if demo else INSIGHTS_DIR
    folder.mkdir(parents=True, exist_ok= True)
    data = {
        "card": card.model_dump(),
        "trace": [step.model_dump() for step in trace],
        "context": context
    }

    _path(folder, insight_id).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _question_key(insight_id: str, message: str) -> str:
    normalized = re.sub(r"\s+", " ", message.lower().replace("ё", "е")).strip(" ?!.")
    return f"{insight_id}__{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]}"


def get_chat(insight_id: str, message: str) -> ChatAnswer | None:
    key = _question_key(insight_id, message)
    for folder in (INSIGHTS_DIR / "chat", DEMO_DIR / "chat"):
        path = _path(folder, key)
        if path.exists():
            return ChatAnswer.model_validate(json.loads(path.read_text(encoding="utf-8"))["answer"])
    return None


def save_chat(insight_id: str, message: str, answer: ChatAnswer, demo: bool = False) -> None:
    folder = (DEMO_DIR if demo else INSIGHTS_DIR) / "chat"
    folder.mkdir(parents=True, exist_ok=True)
    data = {"insight_id": insight_id, "question": message, "answer": answer.model_dump()}
    _path(folder, _question_key(insight_id, message)).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def save_feedback(insight_id: str, useful: bool, reason: str | None = None) -> None:
    INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    row = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "insight_id": insight_id, "useful": useful, "reason": (reason or "")[:500] or None}
    with open(INSIGHTS_DIR / "feedback.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")