import json 
import re
import yaml
from rank_bm25 import BM25Okapi
import snowballstemmer
from ml import config
from app.schemas import Source

PAGES_FILE = config.PROCESSED_DIR / "alfa_pages.jsonl"
REPORTS_FILE = config.REFERENCE_DIR / "alfa_reports.yaml"
CHUNK_CHARS = 800
CHUNK_OVERLAP = 150
MIN_CONFIDENCE = 50
MIN_COVERAGE = 0.5
_INDEX = None
STOPWORDS = {"и", "в", "во", "на", "по", "с", "со", "к", "о", 
                 "об", "от", "до", "за", "из", "у", "не", "что", "как", 
                 "это", "для", "при", "или", "но", "а", "же", "его", "их", 
                 "мы", "вы", "г", "гг", "т", "др","стал", "стала", "стало",
                 "станет", "будет", "был", "была", "было", "были"
            }
STEMMER = snowballstemmer.stemmer("russian")
STEMMER_EN = snowballstemmer.stemmer("english")


def _tokenize(text) -> list[str]:
    text = text.lower().replace("ё", "е")
    words = re.findall(r"[а-яa-z0-9]+", text)
    tokens = []
    for w in words:
        if w in STOPWORDS:
            continue
        if len(w) < 2:
            continue
        if w.isdigit() and len(w) > 4:
            continue
        if re.search(r"\d", w) and re.search(r"[а-яa-z]", w): 
            continue
        if re.search(r"[а-я]", w):
            tokens.append(STEMMER.stemWord(w))
        else:
            tokens.append(STEMMER_EN.stemWord(w))
    return tokens

def _split(text) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= CHUNK_CHARS:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        chunk = text[start:start + CHUNK_CHARS]
        if len(chunk) > 100:
            chunks.append(chunk)
        start += CHUNK_CHARS - CHUNK_OVERLAP
    return chunks

def _load_reports() -> dict:
    if not REPORTS_FILE.exists():
        return {}
    with open(REPORTS_FILE, encoding="utf-8") as f:
        items = yaml.safe_load(f) or []
    return {item["file"]: item for item in items}

def _build_index():
    if not PAGES_FILE.exists():
        raise FileNotFoundError("not pages_file")
   
    reports = _load_reports()
    chunks = []
    with open(PAGES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            page = json.loads(line)
            if page["confidence"] < MIN_CONFIDENCE:
                continue
            meta = reports.get(page["file"], {})
            for text in _split(page["text"]):
                chunks.append({
                    "file": page["file"],
                    "page": page["page"],
                    "text": text,
                    "title": meta.get("title", page["file"]),
                    "date": str(meta.get("date", "")),
                    "outdated": meta.get("outdated", False),
                    "topics": meta.get("topics", [])
                })
    if not chunks:
        raise ValueError("In alfa_pages.jsonl not pages with normal recognition")

    tokenized = [_tokenize(chunk["text"]) for chunk in chunks]
    for chunk, chunk_tokens in zip(chunks, tokenized):
        chunk["tokens"] = set(chunk_tokens)
    bm25 = BM25Okapi(tokenized)
    return bm25, chunks      

def _get_index():
    global _INDEX
    if _INDEX is None:
        _INDEX = _build_index()
    return _INDEX 

def search(query: str, top_k: int = 5, topics: list[str] | None = None,
           include_outdated: bool = False) -> list[dict]:
    
    bm25, chunks = _get_index()
    tokens = _tokenize(query)
    if not tokens:
        return []
    query_set = set(tokens)

    scores = bm25.get_scores(tokens)
    order = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)

    results = []
    per_page = {}  
    for i in order:
        if scores[i] <= 0:
            break  
        chunk = chunks[i]
        covered = len(query_set & chunk["tokens"]) / len(query_set)
        if covered < MIN_COVERAGE:
            continue
        if chunk["outdated"] and not include_outdated:
            continue
        if topics and not set(topics) & set(chunk["topics"]):
            continue
        page_key = (chunk["file"], chunk["page"])
        if per_page.get(page_key, 0) >= 2:
            continue
        per_page[page_key] = per_page.get(page_key, 0) + 1

        hit = {key: value for key, value in chunk.items() if key != "tokens"}
        hit["score"] = round(float(scores[i]), 2)
        hit["ref"] = f"alfa:{chunk['file']}#{chunk['page']}"
        results.append(hit)
        if len(results) >= top_k:
            break
    return results


def to_source(hit: dict) -> Source:
    return Source(title=hit["title"], doc=hit["file"], page=hit["page"])


if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) or "ключевая ставка"
    for hit in search(query):
        print(hit["score"], hit["ref"], hit["date"])
        print("   ", hit["text"][:150])