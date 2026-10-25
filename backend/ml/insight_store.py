import json

from app.schemas import InsightCard, TraceStep
from ml import config

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