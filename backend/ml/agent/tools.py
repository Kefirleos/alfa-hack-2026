import json
from functools import lru_cache
import yaml

from app.company_profile import get_company_profile as _db_profile
from app.graph import top_counterparties
from app.scoring import company_signals, load_events
from ml import alfa_rag, config

PRODUCT_NAMES = {
    "has_rko": "расчётный счёт", "has_gar": "банковская гарантия", "has_loa": "кредит",
    "has_lea": "лизинг", "has_dep": "депозит", "has_zpp": "зарплатный проект",
    "has_factoring": "факторинг",
}
DIRECTION_NOTES = {"in": "кто платит компании", "out": "кому платит компания"}

COUNTERPARTY_NOTE = (
    "Назначение платежей неизвестно: не называть контрагентов поставщиками или покупателями. "
    "Высокая доля — повод уточнить график поступлений, а не вывод о надёжности. "
    "Если industry = null, контрагента нет в данных банка: его отрасль неизвестна."
)
TOPIC_LIST = {"type": "array", "items": {"type": "string"}, "description": "id тем из справочника, например key_rate"}



@lru_cache(maxsize=None)
def _load_yaml(name: str):
    with open(config.REFERENCE_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)

def _round(value, digits=2):
    return round(value, digits) if value is not None else None

def get_company_profile(company_id: str) -> dict:
    profile = _db_profile(company_id)
    if profile is None:
        return {"error": f"company {company_id} not found","refs": []}

    signals = company_signals(profile)
    topics = []
    for topic, contributions in signals.items():
        weight = max(c["weight"] for c in contributions)
        reasons = list(dict.fromkeys(c["reason"] for c in contributions))
        topics.append({"topic": topic, "weight": round(weight, 2), "reasons": reasons})
    topics.sort(key=lambda t: t["weight"], reverse=True)
    topics = topics[:8]

    rules = _load_yaml("field_rules.yaml")["fields"]
    flags = list(profile["bank_products"])
    if profile["foreign_trade"]["fts_flag"]:
        flags.append("fts_flag")
    limits = [rules[flag]["limits"] for flag in flags if flag in rules and rules[flag].get("limits")]

    refs = ["client:okved", "client:region"] + [f"client:{flag}" for flag in flags]
    if profile["payments"]["top_payer_share"] is not None:
        refs.append("client:payments")

    gaps = list(profile["data_gaps"])
    if "has_loa" in flags or "has_lea" in flags:
        gaps.append("сумма долга, тип ставки и даты пересмотра неизвестны")
    if "fts_flag" in flags:
        gaps.append("направление ВЭД, товары и валюта контрактов неизвестны")
    payments = profile["payments"]
    return {
        "company_id": company_id,
        "industry": profile["industry"]["okved_name"],
        "okved": profile["industry"]["okved_code"],
        "region": profile["region"]["region"],
        "revenue_rub": profile["scale"]["revenue"],
        "bank_products": [PRODUCT_NAMES.get(flag, flag) for flag in profile["bank_products"]],
        "foreign_trade": {"fts_flag": profile["foreign_trade"]["fts_flag"],
        "countries": [c.capitalize() for c in profile["foreign_trade"]["countries"]]
        },
        "data_gaps": gaps,
        "top_payer_share": _round(payments["top_payer_share"]),
        "top_payee_share": _round(payments["top_payee_share"]),
        "topics": topics,
        "limits": limits,
        "refs": refs
    }


def get_counterparties(company_id:str, direction: str = "in", limit: int = 5) -> dict:
    if direction not in ("in", "out"):
        return {"error": "direction: in или out", "refs": []}
    data = top_counterparties(company_id, direction, limit)
    items = [{
        "id": item["id"],
        "share": _round(item["share"]),
        "industry": item["okved_name"],   
        "region": item["region"]
    } for item in data["items"]]

    return {
        "company_id": company_id,
        "direction": direction,
        "direction_note": DIRECTION_NOTES[direction],
        "items": items,
        "known_share": _round(data["known_share"]),
        "note": COUNTERPARTY_NOTE,
        "refs": ["client:counterparties"],
    }


def search_alfa_analytics(query: str, topics: list[str] | None = None, top_k: int = 4) -> dict:
    hits = alfa_rag.search(query, top_k, topics)
    if not hits:
        return {"query": query, "items": [], "note": "Подходящая позиция Альфа-Банка не найдена", "refs": []}

    items = [{"ref": hit["ref"], "title": hit["title"], "date": hit["date"],
        "page": hit["page"], "outdated": hit["outdated"], "text": hit["text"][:600]
        } for hit in hits]
    items.sort(key = lambda item: item["date"], reverse=True)
    return {"query": query, "items": items, "refs": list(dict.fromkeys(item["ref"] for item in items))}

def search_related_news(topics: list[str], industries: list[str] | None = None, exclude_event_id: str | None = None, limit: int = 5) -> dict:
    events = load_events()
    wanted = set(topics)
    wanted_industries = set(industries or [])
    scored = []
    for event in events:
        if event["event_id"] == exclude_event_id:
            continue
        common = wanted & set(event["topics"])
        if not common:
            continue
        score = len(common) + (0.5 if wanted_industries & set(event.get("industries") or []) else 0)
        scored.append((score, event["published"], event))

    scored.sort(key = lambda x: (x[0], x[1]), reverse=True)
    items = []
    for score, published, event in scored[:limit]:
        items.append({
            "ref": f"news:{event['event_id']}",
            "title": event["title"],
            "date": event["published"][:10],
            "source": event["source_name"],
            "summary": event.get("summary", ""),
            "topics": event["topics"],
        })

    return {"topics": topics, "items": items, "refs": [item["ref"] for item in items]}

def get_bank_products(company_id:str, topics: list[str]) -> dict:
    profile = _db_profile(company_id)
    if profile is None:
        return {"error": f"company {company_id} not found", "refs": []}
    owned = set(profile["bank_products"])
    products = _load_yaml("products.yaml")
    wanted = set(topics)
    items = []
    for product in products:
        if not wanted & set(product["topics"]):
            continue                     
        if product["field"] and product["field"] in owned:
            continue                      
        items.append({
            "ref": f"product:{product['id']}",
            "name": product["name"],
            "when": product["when"],
            "not_for": product["not_for"],
            "check_if_connected": product["field"] is None,
        })
    return {"company_id": company_id, "items": items[:3], "note": "Ставки и условия не называть - предложить обсудить с менеджером.", "refs": [item["ref"] for item in items[:3]]}

def _spec(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {
        "name": name,
        "description": description,
        "parameters": {"type": "object", "properties": properties, "required": required},
    }}

TOOL_SPECS = [
    _spec("get_company_profile",
          "Профиль компании: отрасль, продукты банка, ВЭД, доли платежей, темы с причинами, "
          "ограничения (что нельзя утверждать) и пробелы данных.",
          {"company_id": {"type": "string"}}, ["company_id"]),
    _spec("get_counterparties",
          "Крупнейшие контрагенты компании по платежам: доли и отрасли. in — кто платит компании, out — кому платит она.",
          {"company_id": {"type": "string"},
           "direction": {"type": "string", "enum": ["in", "out"]},
           "limit": {"type": "integer"}},
          ["company_id"]),
    _spec("search_alfa_analytics",
          "Поиск по отчётам аналитиков Альфа-Банка. Единственный источник позиции банка. "
          "Запрос — несколько ключевых слов по-русски.",
          {"query": {"type": "string"}, "topics": TOPIC_LIST, "top_k": {"type": "integer"}},
          ["query"]),
    _spec("search_related_news",
          "Похожие события из ленты новостей по темам и отраслям.",
          {"topics": TOPIC_LIST,
           "industries": {"type": "array", "items": {"type": "string"}, "description": "разделы ОКВЭД, например 42"},
           "exclude_event_id": {"type": "string"},
           "limit": {"type": "integer"}},
          ["topics"]),
    _spec("get_bank_products",
          "Продукты Альфа-Банка, подходящие к темам события, кроме уже подключённых у компании.",
          {"company_id": {"type": "string"}, "topics": TOPIC_LIST},
          ["company_id", "topics"]),
]
TOOLS = {
    "get_company_profile": get_company_profile,
    "get_counterparties": get_counterparties,
    "search_alfa_analytics": search_alfa_analytics,
    "search_related_news": search_related_news,
    "get_bank_products": get_bank_products,
}

def run_tool(name:str, args) ->dict:
    if name not in TOOLS:
        return {"error": f"there is no tool {name}", "refs": []}
    try:
        return TOOLS[name](**args)
    except TypeError as error:
        return {"error": f"incorrect arguments {name}: {error}", "refs": []}
    except Exception as error:
        return {"error": f"{name}: {error}", "refs": []}


if __name__ == "__main__":
    print(len(TOOL_SPECS), [spec["function"]["name"] for spec in TOOL_SPECS])
    print(run_tool("get_counterparties", {"company_id": "U_9250", "direction": "out", "limit": 2}))
    print(run_tool("get_counterparties", {"company": "U_9250"}))
    print(run_tool("unknown_tool", {}))