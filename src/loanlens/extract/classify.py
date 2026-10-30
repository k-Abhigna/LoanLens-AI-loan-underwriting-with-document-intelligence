"""Decide what kind of document this is, from keywords in its text."""

from loanlens.schemas import DocType

KEYWORDS: dict[str, list[str]] = {
    "application": ["loan application", "applicant name", "loan amount", "purpose",
                    "monthly installment", "i certify"],
    "payslip": ["earnings statement", "pay slip", "gross pay", "gross earnings", "net pay",
                "net amount", "deductions", "year to date", "employee name", "staff name",
                "pay period", "period covered"],
    "bank_statement": ["account statement", "account summary", "account holder",
                       "customer name", "opening balance", "beginning balance",
                       "closing balance", "ending balance", "deposit", "withdrawals"],
}


def classify(text: str) -> tuple[DocType, float]:
    """Return (doc_type, confidence 0-1). 'unknown' if nothing matches well."""
    squashed = "".join(text.lower().split())  # OCR may drop spaces between words
    scores = {doc: sum("".join(k.split()) in squashed for k in words) / len(words)
              for doc, words in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    if scores[best] < 0.3:
        return "unknown", scores[best]
    return best, round(scores[best], 2)
