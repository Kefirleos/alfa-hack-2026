from ml import config, llm_client

import time
from datetime import datetime, timedelta, timezone

ROLES = ("fast", "writer", "critic", "research", "fallback")
MSK = timezone(timedelta(hours=3))


def print_limit() -> bool:
    try:
        data = llm_client.key_info()
    except Exception as e:
        print(f"Limit: error — {e}")
        return False

    info = data.get("info", data) 
    spend = info.get("spend")
    budget = info.get("max_budget")
    reset = info.get("budget_reset_at")
    if reset:
        reset_msk = datetime.fromisoformat(reset).astimezone(MSK).strftime("%d.%m %H:%M МСК")
        reset = f"{reset} ({reset_msk})"
    print(f"Limit: spent {spend} from {budget}, reset {reset}")
    return True


def check_model(role: str) -> None:
    try:
        model = llm_client.model_for(role)
    except llm_client.LLMError as e:
        print(f"{role:9} пропуск: {e}")
        return

    messages = [{"role": "user", "content": "Answer in one word: what is the capital of Russia?"}]
    started = time.time()
    try:
        out = llm_client._call(model, messages, {"temperature": 0, "max_tokens": 100})
    except Exception as e:
        print(f"{role:9} {model:40} ERROR  {str(e)[:150]}")
        return

    seconds = time.time() - started
    answer = (out["content"] or "").strip().replace("\n", " ")[:60]
    tokens = (out["usage"] or {}).get("completion_tokens")
    print(f"{role:9} {model:40} OK  {seconds:5.1f} c tokens {tokens}  «{answer}»")


def main() -> None:
    print(f"Gateway: {config.LLM_BASE_URL}")
    if not config.LLM_API_KEY:
        print("The key is not set: enter LLM_API_KEY in .env")
        return
    print("Key: set")

    if not print_limit():
        return

    print()
    for role in ROLES:
        check_model(role)

    print(f"\nDone. Expense journal: {config.LLM_CACHE_DIR / 'usage.jsonl'}")


if __name__ == "__main__":
    main()