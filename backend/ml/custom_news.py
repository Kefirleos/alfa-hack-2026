import hashlib
import json
import re
import httpx
from datetime import datetime, timezone

from ml import config, llm_client
from ml.news_ingest import HEADERS, _clean_html
from ml.news_tagging import build_system_prompt, keyword_tags, llm_tags, load_topics

CUSTOM_FILE = config. PROCESSED_DIR.parent / "insights" / "custom_events.jsonl"
MAX_TEXT = 5000
MIN_TEXT = 50
FETCH_TIMEOUT = 20


def _fetch_page(url: str) -> tuple[str, str]:
    if not url.startswith(("http://", "https://")):
        raise ValueError("Ccылка должна начинаться с http:// или https://")
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as error:
        raise ValueError(f"Не удалось открыть ссылку: {error}") from None

    page = resp.text
    title_match = re.search(r"<title[^>]*>(.*?)</title>", page, re.IGNORECASE | re.DOTALL)
    title = _clean_html(title_match.group(1)) if title_match else ""
    page = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", page, flags=re.IGNORECASE | re.DOTALL)
    paragraphs = [_clean_html(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", page, re.IGNORECASE | re.DOTALL)]
    text = " ".join(p for p in paragraphs if len(p) > 40)
    return title, text or _clean_html(page)


def _split_text(text: str) -> tuple[str, str]:
    text = text.strip()
    title = text.partition("\n")[0].strip()[:200]
    return title, text


def find(event_id: str) -> dict | None:
    if not CUSTOM_FILE.exists():
        return None
    with open(CUSTOM_FILE, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                event = json.loads(line)
                if event["event_id"] == event_id:
                    return event
    return None


def make_event(text: str | None = None, url: str | None = None) -> dict:
    if text and text.strip():
        title, body = _split_text(text)
    else:
        title, body = _fetch_page(url.strip())
    body = body[:MAX_TEXT]
    if len(body) < MIN_TEXT:
        raise ValueError("Слишком короткий текст новости")

    event_id = "custom_" + hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
    saved = find(event_id)
    if saved:
        return saved

    now = datetime.now(timezone.utc).isoformat()
    record = {
        "event_id": event_id,
        "source_id": "custom",
        "source_name": "Новость пользователя",
        "source_weight": 0.5,
        "title": title or body[:100],
        "url": url,
        "text": body,
        "categories": [],
        "published": now,
        "fetched_at": now,
    }

    topics = load_topics()
    topic_ids = {topic["id"] for topic in topics}
    try:
        tags = llm_tags([record], build_system_prompt(topics), topics, topic_ids)[event_id]
        tagged_by = "llm"
    except llm_client.LLMError:
        tags = keyword_tags(record, topics)
        tagged_by = "keywords"
    if not tags.topics:
        raise ValueError("Новость не связана с темами, которые влияют на бизнес клиентов")

    event = {**record, **tags.model_dump(), "tagged_by": tagged_by}
    CUSTOM_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CUSTOM_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event

