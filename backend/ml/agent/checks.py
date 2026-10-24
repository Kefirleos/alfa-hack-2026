import re

PARTS = ("summary", "why_it_matters", "risks", "opportunities", "actions", "bank_view")

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


def rule_check(draft, state: dict) -> list[str]:
    known = state["refs"]
    company_flags = {ref[len("client:"):] for ref in known if ref.startswith("client:")}
    issues = []

    for part in PARTS:
        for number, claim in enumerate(getattr(draft, part), start=1):
            where = f"{part}[{number}]"

            fake = [ref for ref in claim.refs if ref not in known]
            if fake:
                issues.append(f"{where}: метки не из результатов инструментов: {', '.join(fake)}")

            if claim.type == "fact" and not _has_prefix(claim.refs, "news:"):
                issues.append(f"{where}: факт без ссылки на новость")
            if claim.type == "bank_view":
                if not _has_prefix(claim.refs, "alfa:"):
                    issues.append(f"{where}: позиция банка без ссылки на отчёт")
                if any(not ref.startswith("alfa:") for ref in claim.refs):
                    issues.append(f"{where}: у позиции банка допустимы только метки alfa:")
            if claim.type == "ai_inference" and not _has_prefix(claim.refs, "client:"):
                issues.append(f"{where}: вывод не опирается на признак компании")
            if claim.type == "ad" and not _has_prefix(claim.refs, "product:"):
                issues.append(f"{where}: продукт не из списка банка")

            if claim.type not in ("ai_inference", "ad"):
                continue
            if MONEY_RE.search(claim.text):
                issues.append(f"{where}: сумма в рублях без данных пользователя")
            for pattern, flag, message in FORBIDDEN:
                if (flag is None or flag in company_flags) and pattern.search(claim.text):
                    issues.append(f"{where}: {message}")

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