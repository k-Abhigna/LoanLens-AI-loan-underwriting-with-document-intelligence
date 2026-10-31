"""Baseline extractor: regular expressions. Free, fast, offline - and brittle.

The LLM extractor (llm.py) is compared against this baseline in the evaluation.
"""

import re

from loanlens.schemas import ApplicationFields, BankStatementFields, PayslipFields

# Amounts always have 2 decimals. OCR may read ',' as ';' or ':' so accept any separator.
MONEY = r"-?\$?\s?-?\d[\d,;:.]*[.,:;]\d{2}(?!\d)"


def parse_money(text: str | None) -> float | None:
    """'$1,103.26' / '$1;103.26' / '-$468.70' -> number."""
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    value = int(digits) / 100
    return -value if "-" in text else value


def _fix_ocr_words(value: str | None) -> str | None:
    """'Angela.Morgan' / 'BrightwaveTelecom' -> 'Angela Morgan' / 'Brightwave Telecom'."""
    if not value:
        return value
    value = re.sub(r"[.'`]", " ", value)
    value = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    return " ".join(value.split())


SEP = r"[\s:.,;]*"  # OCR often adds stray ':' or '.' between label and value


def _label(label: str) -> str:
    """'Gross Pay' -> regex that also matches 'GrossPay' (OCR drops spaces)."""
    return r"[\s.]*".join(map(re.escape, label.split()))


def _find(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).strip(" .:;,") if match else None


def _text_after(label: str, text: str) -> str | None:
    return _find(rf"{_label(label)}{SEP}(.+)", text)


def _money_after(label: str, text: str) -> float | None:
    return parse_money(_find(rf"{_label(label)}{SEP}({MONEY})", text))


def _int_after(label: str, text: str) -> int | None:
    value = _find(rf"{_label(label)}{SEP}(\d+)", text)
    return int(value) if value else None


def extract_application(text: str) -> ApplicationFields:
    return ApplicationFields(
        applicant_name=_text_after("Applicant Name", text),
        employer=_text_after("Employer", text),
        job_title=_text_after("Job Title", text),
        years_employed=_int_after("Years Employed", text),
        stated_annual_income=_money_after("Annual Income", text),
        monthly_debt_payments=_money_after("Monthly Debt Payments", text),
        loan_amount=_money_after("Loan Amount", text),
        term_months=_int_after("Term", text),
        monthly_installment=_money_after("Monthly Installment", text),
        purpose=_text_after("Purpose", text),
        home_ownership=_text_after("Home Ownership", text),
    )


def _clean_period(value: str | None) -> str | None:
    """'20.18-06-01to2018-06-30' -> '2018-06-01 to 2018-06-30'."""
    if not value:
        return None
    value = re.sub(r"(?<=\d)[.:,](?=\d)", "", value)
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", value)
    return " to ".join(dates[:2]) if len(dates) >= 2 else value


def extract_payslip(text: str) -> PayslipFields:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return PayslipFields(
        employee_name=_fix_ocr_words(_text_after("Employee Name", text)),
        employer=_fix_ocr_words(lines[0]) if lines else None,  # letterhead
        pay_period=_clean_period(_text_after("Pay Period", text)),
        gross_pay=_money_after("Gross Pay", text),
        total_deductions=_money_after("Total Deductions", text),
        net_pay=_money_after("Net Pay", text),
        ytd_gross=_money_after("YTD Gross", text),
    )


def clean_ocr_payslip(slip: PayslipFields) -> PayslipFields:
    """Undo OCR damage in text fields, whichever extractor read them."""
    return slip.model_copy(update={
        "employee_name": _fix_ocr_words(slip.employee_name),
        "employer": _fix_ocr_words(slip.employer),
        "pay_period": _clean_period(slip.pay_period),
    })


def extract_bank_statement(text: str) -> BankStatementFields:
    credits, payer = [], None
    for line in text.splitlines():
        if "PAYROLL" in line.upper():
            match = re.search(rf"(PAYROLL.*?)\s+({MONEY})", line, flags=re.IGNORECASE)
            if match:
                payer = payer or match.group(1).strip()
                credits.append(parse_money(match.group(2)))
    return BankStatementFields(
        account_holder=_text_after("Account Holder", text),
        opening_balance=_money_after("Opening Balance", text),
        closing_balance=_money_after("Closing Balance", text),
        salary_credits=credits,
        salary_payer=payer,
    )


EXTRACTORS = {
    "application": extract_application,
    "payslip": extract_payslip,
    "bank_statement": extract_bank_statement,
}


def extract(doc_type: str, text: str):
    return EXTRACTORS[doc_type](text)
