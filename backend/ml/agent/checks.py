import re

PARTS = ("summary", "why_it_matters", "risks", "opportunities", "actions", "bank_view")

NUMBER_RE = re.compile(r"\d+\.\d+|\d{2,}")

MONEY_RE = re.compile(r"\d[\d\s,.]*\s*(тыс\.?|млн|млрд|трлн)?\s*(руб|₽)", re.IGNORECASE)

FORBIDDEN = [
    (re.compile(r"экспортир|импортир", re.IGNORECASE), "fts_flag",
     "по сведениям ФТС нельзя утверждать, что компания экспортирует или импортирует"),
    (re.compile(r"расходы\s+(уже\s+)?(вырос|увелич)", re.IGNORECASE), "has_loa",
     "по флагу кредита нельзя утверждать, что расходы уже выросли"),
    (re.compile(r"ненад[её]жн", re.IGNORECASE), None,
     "нельзя делать вывод о надёжности контрагента"),
]


def _has_prefix(refs: list[str], prefix: str) -> bool:
    return any(ref.startswith(prefix) for ref in refs)


def _report_text(state: dict, refs: list[str]) -> str:
    """Тексты, даты и названия отчётов банка, на которые ссылается утверждение."""
    parts = []
    for call in state["results"]:
        for item in call["result"].get("items", []):
            if item.get("ref") in refs:
                parts.append(f"{item.get('title', '')} {item.get('date', '')} {item.get('text', '')}")
    return " ".join(parts).replace(",", ".")


def claim_problems(claim, state: dict) -> list[str]:
    """Что не так с одним утверждением (пустой список, если всё в порядке)."""
    known = state["refs"]
    company_flags = {ref[len("client:"):] for ref in known if ref.startswith("client:")}
    problems = []

    fake = [ref for ref in claim.refs if ref not in known]
    if fake:
        problems.append(f"метки не из результатов инструментов: {', '.join(fake)}")

    if claim.type == "fact" and not _has_prefix(claim.refs, "news:"):
        problems.append("факт без ссылки на новость")
    if claim.type == "bank_view":
        if not _has_prefix(claim.refs, "alfa:"):
            problems.append("позиция банка без ссылки на отчёт")
        if any(not ref.startswith("alfa:") for ref in claim.refs):
            problems.append("у позиции банка допустимы только метки alfa:")
        # числа из позиции банка должны быть в самом отчёте, иначе банку приписана чужая цифра
        report = _report_text(state, claim.refs)
        missing = [n for n in NUMBER_RE.findall(claim.text.replace(",", ".")) if n not in report]
        if report and missing:
            problems.append(f"числа {', '.join(missing)} не найдены в отчёте банка")
    if claim.type == "ai_inference" and not _has_prefix(claim.refs, "client:"):
        problems.append("вывод не опирается на признак компании")
    if claim.type == "ad" and not _has_prefix(claim.refs, "product:"):
        problems.append("продукт не из списка банка")

    if claim.type in ("ai_inference", "ad"):
        if MONEY_RE.search(claim.text):
            problems.append("сумма в рублях без данных пользователя")
        for pattern, flag, message in FORBIDDEN:
            if (flag is None or flag in company_flags) and pattern.search(claim.text):
                problems.append(message)
    return problems


def rule_check(draft, state: dict) -> list[str]:
    issues = []
    for part in PARTS:
        for number, claim in enumerate(getattr(draft, part), start=1):
            issues += [f"{part}[{number}]: {problem}" for problem in claim_problems(claim, state)]
    if not draft.uncertainty:
        issues.append("uncertainty: не указано, чего не хватает для точного вывода")
    return issues


if __name__ == "__main__":
    from types import SimpleNamespace

    state = {"refs": {"news:a1", "alfa:x.pdf#1", "client:has_loa", "client:fts_flag", "product:deposit"}}

    def claim(text, type_, refs):
        return SimpleNamespace(text=text, type=type_, refs=refs)

    draft = SimpleNamespace(
        summary=[claim("ЦБ сохранил ставку; Россия импортирует топливо на 10 млрд руб.", "fact", ["news:a1"]),
                 claim("Инфляция выросла", "fact", [])],
        why_it_matters=[claim("Компания экспортирует в Китай", "ai_inference", ["client:fts_flag"])],
        risks=[claim("Расходы вырастут на 50 млн руб.", "ai_inference", ["client:has_loa"])],
        opportunities=[],
        actions=[claim("Рассмотреть депозит", "ad", ["product:deposit"])],
        bank_view=[claim("Банк ждёт 13,5%", "bank_view", ["news:a1", "alfa:y.pdf#2"])],
        uncertainty="",
    )
    for issue in rule_check(draft, state):
        print(issue)