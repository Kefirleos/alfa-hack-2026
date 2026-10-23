import argparse
import contextlib
import hashlib
import html
import json
import re
from datetime import datetime, timezone
import calendar
import httpx
import feedparser
import yaml

from ml import config

SOURCES_FILE = config.REFERENCE_DIR / "sources.yaml"
OUT_FILE = config.PROCESSED_DIR / "news_raw.jsonl"
TIMEOUT = 60
HEADERS = {"User-Agent": "Mozilla/5.0 (alfa-hack-2026 news reader)"}
MAX_TEXT = 4000

def load_sources() -> list[dict]:
    with open(SOURCES_FILE, encoding="utf-8") as f:
        sources = yaml.safe_load(f) or []
    return [source for source in sources
            if source.get("enabled") and source.get("type") == "rss"]


def _clean_html(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

def _published_iso(entry) -> str | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime.fromtimestamp(calendar.timegm(parsed), tz= timezone.utc).isoformat()

def _make_id(url: str, title: str) -> str:
    return hashlib.sha256((url or title).encode("utf-8")).hexdigest()[:12]

def _entry_to_record(entry, source: dict) -> dict | None:
    title = _clean_html(entry.get("title"))
    url = entry.get("link", "")
    if not title and not url:
        return None
    text = _clean_html(entry.get("summary") or entry.get("description"))[:MAX_TEXT]
    categories = [tag.get("term", "").strip() for tag in entry.get("tags", []) if tag.get("term")]
    return {
        "event_id": _make_id(url, title),
        "source_id": source["id"],
        "source_name": source["name"],
        "source_weight": source.get("weight", 0.5),
        "title": title,
        "url": url,
        "text": text,
        "categories": categories,
        "published": _published_iso(entry),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "content_hash": hashlib.sha256((title + text).encode("utf-8")).hexdigest()[:16]      
    }

def fetch_feed(source: dict) -> list[dict]:
    resp = httpx.get(source["url"], headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"no RSS {feed.bozo_exception}")
    skipped = 0
    records = []
    exclude = [word.lower().replace("ё", "е") for word in source.get("exclude", [])]
    include = {c.lower().replace("ё", "е") for c in source.get("include_categories", [])}
    for entry in feed.entries:
        record = _entry_to_record(entry, source)
        if record is None:
            continue
        record_categories = {c.lower().replace("ё", "е") for c in record["categories"]}
        if include and not include & record_categories:
            skipped += 1
            continue
        title_lower = record["title"].lower().replace("ё", "е")
        if any(word in title_lower for word in exclude):
            skipped += 1
            continue
        records.append(record)
    if skipped:
        print(f"{source['id']}: filtered out the official ones {skipped}")
    return records

def load_seen() -> tuple[set, set]:
    seen_ids, seen_hashes = set(), set()
    if not OUT_FILE.exists():
        return seen_ids, seen_hashes
    with open(OUT_FILE, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            seen_ids.add(record["event_id"])
            seen_hashes.add(record.get("content_hash"))
    return seen_ids, seen_hashes

def main():
    parser = argparse.ArgumentParser(description="gathering news from RSS")
    parser.add_argument("--only", help = "id of one source from sources.yaml")
    parser.add_argument("--dry-run", action="store_true", help = "to show, but not to write down")
    args = parser.parse_args()

    sources = load_sources()
    if args.only:
        sources = [source for source in sources
                   if source["id"] == args.only]
    if not sources:
        print("no included rss")
        return

    seen_ids, seen_hashes = load_seen()
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    total_new = 0
 
    output = contextlib.nullcontext() if args.dry_run else open(OUT_FILE, "a", encoding="utf-8")
    with output as out:
        for source in sources:
            try:
                records = fetch_feed(source)
            except Exception as error:
                print(f"{source['id']}: error {error}")
                continue
 
            new_count = 0
            for record in records:
                if record["event_id"] in seen_ids or record["content_hash"] in seen_hashes:
                    continue
                seen_ids.add(record["event_id"])
                seen_hashes.add(record["content_hash"])
                new_count += 1
                if args.dry_run:
                    print(f"   {record['published']}  {record['title'][:100]}")
                else:
                    out.write(json.dumps(record, ensure_ascii=False) + "\n")
            total_new += new_count
            print(f"{source['id']}: in the feed {len(records)}, new {new_count}")
 
    if args.dry_run:
        print(f"\nTrial run: there would be {total_new} new ones, the file has not been modified.")
    else:
        print(f"\nNew items in total: {total_new}; in {OUT_FILE.name} now {len(seen_ids)} news items.")
 
 
if __name__ == "__main__":
    main()
                     