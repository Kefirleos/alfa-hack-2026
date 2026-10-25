import json
import re

from pydantic import BaseModel, Field
from app.schemas import ChatAnswer, Claim, ClaimType, InsightCard
from ml import llm_client
from ml.agent.checks import check_claims
from ml.agent.loop import AGENT_ROLE, DraftClaim, _prompt, claim_converter, fill
from ml.agent.tools import _load_yaml, run_tool

MAX_QUESTION = 1000
BANK_WORDS = re.compile(r"банк|прогноз|ставк|курс|инфляц|рубл", re.IGNORECASE)


class ChatDraft(BaseModel):
    answer: list[DraftClaim] = Field(min_length=1)
    uncertainty: str = ""


def _extra_bank_search(message: str, state: dict) -> None:
    if not BANK_WORDS.search(message):
        return
    args = {"query": message}
    result = run_tool("search_alfa_analytics", args)
    state["results"].append({"tool": "search_alfa_analytics", "args": args, "result": result})
    state["refs"].update(result.get("refs", []))


def _generate(message: str, card: InsightCard, state: dict, role: str,
              feedback: str | None = None) -> ChatDraft:
    role_rule = _load_yaml("roles.yaml")[role]
    tool_results = json.dumps(
        [{"tool": call["tool"], "result": call["result"]} for call in state["results"]],
        ensure_ascii=False,
    )
    user = fill(_prompt("chat.txt"), {
        "role_name": role_rule["name"],
        "role_style": role_rule["answer_style"],
        "question": message,
        "insight": card.model_dump_json(exclude={"id", "company_id", "relevance"}),
        "tool_results": tool_results,
    })
    messages = [
        {"role": "system", "content": _prompt("system.txt")},
        {"role": "user", "content": user},
    ]
    if feedback:
        messages.append({"role": "user", "content": "Исправь ответ с учётом замечаний:\n" + feedback})
    return llm_client.chat_json(AGENT_ROLE, messages, ChatDraft, max_tokens=2000, temperature=0.2)


def answer(card: InsightCard, context: dict, event: dict, role: str, message: str) -> ChatAnswer:
    message = message.strip()[:MAX_QUESTION]
    state = {"results": list(context["results"]), "refs": set(context["refs"])}
    _extra_bank_search(message, state)

    draft = _generate(message, card, state, role)
    issues = check_claims(draft.answer, "answer", state)
    if issues:
        draft = _generate(message, card, state, role, feedback="\n".join(issues))

    checked = [claim for claim in draft.answer if not check_claims([claim], "answer", state)]

    to_claim = claim_converter(state, event)
    claims = [to_claim(claim) for claim in checked]
    if not claims:
        claims = [Claim(text="По данным разбора ответить на этот вопрос не получается.",
                        type=ClaimType.ai_inference, confidence="low")]
    if draft.uncertainty:
        claims.append(Claim(text=f"Чего не хватает: {draft.uncertainty}",
                            type=ClaimType.ai_inference, confidence="low"))
    return ChatAnswer(answer=claims)