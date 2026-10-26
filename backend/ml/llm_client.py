import os
import json
import hashlib
import time
import re
from pathlib import Path
from urllib.request import Request, urlopen

from pydantic import BaseModel, ValidationError
from openai import OpenAI, BadRequestError

from ml import config

ROLES = ("fast", "writer", "critic", "research", "fallback", "vision")

class LLMError(RuntimeError):
    """Базовая ошибка при работе с LLM-шлюзом."""


class LLMOfflineError(LLMError):
    """Запрос к модели заблокирован, потому что включён OFFLINE_MODE и ответа нет в кэше."""
    

def model_for(role: str) -> str:
    if role not in ROLES:
        raise ValueError("ROLES: fast, writer, critic, research, fallback, vision")
    name_model = "LLM_MODEL_" + role.upper()
    name = os.getenv(name_model)

    if not name:
        raise ValueError("in .env not variable")
    return name

_client = None

def _get_client():
    global _client
    if _client is None:
        if not config.LLM_API_KEY:
            raise LLMError("LLM_API_KEY is not set")

        _client = OpenAI(
            api_key = config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
            timeout=float(config.LLM_TIMEOUT),
            max_retries=2
        )
    return _client


def _call(model: str, messages: list[dict], params: dict) -> dict:
    client = _get_client()

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages, 
            **params
        )
    except BadRequestError:
        if "response_format" not in params:
            raise  
        params = {k: v for k, v in params.items() if k != "response_format"}
        resp = client.chat.completions.create(
            model=model, 
            messages=messages, 
            **params
        )

    msg = resp.choices[0].message
    return {
        "content": msg.content,
        "tool_calls": [tc.model_dump() for tc in msg.tool_calls] if msg.tool_calls else None,
        "model": resp.model or model,
        "usage": resp.usage.model_dump() if resp.usage else None,
    }

def _cache_path(payload:dict) -> Path:
    raw = json.dumps(payload,
               sort_keys=True,
               ensure_ascii=False,
               default=str      
             )

    key = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    return config.LLM_CACHE_DIR/key[:2]/f"{key}.json"


def _log_usage(role: str, model: str, usage: dict | None, seconds: float, cached: bool) -> None:
    config.LLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    rec = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "role": role,
        "model": model,
        "cached": cached,
        "seconds": round(seconds, 2),
        "prompt_tokens": (usage or {}).get("prompt_tokens"),
        "completion_tokens": (usage or {}).get("completion_tokens"),
    }

    with open(config.LLM_CACHE_DIR / "usage.jsonl", mode= "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def chat(
    role: str,
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    json_mode: bool = False,
    temperature: float = 0.2,
    max_tokens: int | None = 2000,
    use_cache: bool = True) -> dict:

    model = model_for(role)

    params: dict = {"temperature": temperature}
    if max_tokens:
        params["max_tokens"] = max_tokens
    if tools:
        params["tools"] = tools
    if json_mode:
        params["response_format"] = {"type": "json_object"}

    # 1. кэш
    path = _cache_path({"model": model, "messages": messages, **params})
    if use_cache and path.exists():
        out = json.loads(path.read_text(encoding="utf-8"))
        out["cached"] = True
        _log_usage(role, out["model"], None, 0.0, cached=True)
        return out

    # 2. офлайн мод
    if config.OFFLINE_MODE:
        raise LLMOfflineError(f"OFFLINE_MODE: no response in the cache for the role {role}")

    # 3. запасная модель
    started = time.time()
    try:
        out = _call(model, messages, params)
    except Exception as first_error:
        fallback = model_for("fallback")
        if fallback == model:
            raise LLMError(f"{model}: {first_error}") from first_error
        try:
            out = _call(fallback, messages, params)
        except Exception as second_error:
            raise LLMError(f"{model}: {first_error}; spare {fallback}: {second_error}") from second_error

    # 4. журнал
    _log_usage(role, out["model"], out["usage"], time.time() - started, cached=False)
    if use_cache:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    out["cached"] = False
    return out

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


def _extract_json(text: str) -> str:
    text = _THINK.sub("", text or "").strip()
    text = _FENCE.sub("", text).strip()
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end > start else text


def chat_json(role: str, messages: list[dict], schema: type[BaseModel], *, retries: int = 1, **kw):
    schema_txt = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    msgs = [
        {
            "role": "system",
            "content": "Answer ONLY with a JSON object, without explanations or markdown., "
            f"strictly according to this JSON Schema:\n{schema_txt}",
        },
        *messages,
    ]
    last_error = ""
    for attempt in range(retries + 1):
        out = chat(role, msgs, json_mode=True, use_cache=(attempt == 0), **kw)
        raw = _extract_json(out["content"] or "")
        try:
            return schema.model_validate_json(raw)
        except ValidationError as e:
            last_error = str(e)[:1500]
            msgs = msgs + [
                {"role": "assistant", "content": out["content"] or ""},
                {"role": "user", "content": f"The response failed the schema validation:\n{last_error}\nFix it and send the JSON again."},
            ]
    raise LLMError(f"{role}: The answer does not match the schema. {schema.__name__}: {last_error}")


def key_info() -> dict:
    root = config.LLM_BASE_URL.rstrip("/").removesuffix("/v1")
    req = Request(f"{root}/key/info", headers={"Authorization": f"Bearer {config.LLM_API_KEY}"})
    with urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))