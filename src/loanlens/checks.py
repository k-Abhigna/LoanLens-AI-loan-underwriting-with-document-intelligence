"""Cross-document verification: do the documents agree with each other?

This is plain code, not AI: rules a credit team can read, audit and change.
"""

from difflib import SequenceMatcher
from statistics import mean

from loanlens.config import POLICY
from loanlens.schemas import ApplicationFields, BankStatementFields, Check, PayslipFields

TYPICAL_TAKE_HOME = 0.75  # net/gross, used only when the payslip itself is unreliable


def similar(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.upper().strip(), b.upper().strip()).ratio()


def _payer_name(description: str | None) -> str:
    """'PAYROLL DEP ACME CORP' / 'DIRECT DEPOSIT SALARY ACME CORP' -> 'ACME CORP'."""
    words = (description or "").upper().replace("-", " ").split()
    noise = {"PAYROLL", "DEP", "DIRECT", "DEPOSIT", "SALARY", "ACH", "CREDIT", "PPD"}
    return " ".join(w for w in words if w not in noise)


def _pct_diff(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1e-9)


def _income_check(name: str, claimed: float | None, observed: float | None, what: str) -> Check:
    if claimed is None or observed is None:
        return Check(name=name, status="warn", detail=f"Could not compare {what}: value missing")
    diff = _pct_diff(claimed, observed)
    detail = f"{what}: ${claimed:,.2f} vs ${observed:,.2f} ({diff:.0%} apart)"
    if diff > POLICY["income_reject_mismatch"]:
        return Check(name=name, status="fail", detail=detail)
    if diff > POLICY["income_tolerance"]:
        return Check(name=name, status="warn", detail=detail)
    return Check(name=name, status="pass", detail=detail)


def run_checks(app: ApplicationFields | None, slip: PayslipFields | None,
               bank: BankStatementFields | None) -> tuple[list[Check], dict]:
    """Return the list of checks plus derived numbers (verified income etc.)."""
    checks: list[Check] = []
    missing = [n for n, d in [("application", app), ("payslip", slip), ("bank statement", bank)]
               if d is None]
    if missing:
        checks.append(Check(name="documents_present", status="fail",
                            detail=f"Missing: {', '.join(missing)}"))
        return checks, {}
    checks.append(Check(name="documents_present", status="pass", detail="All 3 documents found"))

    # 1. Same person on all documents
    # A missing value means "could not verify" (warn -> human), never "fraud" (fail)
    names = [app.applicant_name, slip.employee_name, bank.account_holder]
    score = min(similar(names[0], names[1]), similar(names[0], names[2]))
    status = "warn" if None in names else "pass" if score >= 0.85 else "fail"
    checks.append(Check(name="name_match", status=status,
                        detail=f"Application / payslip / bank: {' / '.join(map(str, names))}"))

    # 2. Payslip arithmetic: gross - deductions = net
    math_ok = None not in (slip.gross_pay, slip.total_deductions, slip.net_pay)
    if math_ok:
        gap = slip.gross_pay - slip.total_deductions - slip.net_pay
        math_ok = abs(gap) <= 1.0
        checks.append(Check(name="payslip_arithmetic", status="pass" if math_ok else "fail",
                            detail=f"Gross - deductions - net = ${gap:,.2f}"))
    else:
        checks.append(Check(name="payslip_arithmetic", status="warn",
                            detail="Gross, deductions or net pay missing"))

    # 3. Employer: application vs payslip letterhead vs payroll deposit description
    emp_score = similar(app.employer, slip.employer)
    payer = _payer_name(bank.salary_payer)
    bank_score = similar(payer, (app.employer or "").upper()[:len(payer)]) if payer else 0.0
    ok = min(emp_score, bank_score) >= POLICY["employer_match_threshold"]
    status = "warn" if not (app.employer and slip.employer and payer) else "pass" if ok else "fail"
    checks.append(Check(name="employer_match", status=status,
                        detail=f"Application: {app.employer} | Payslip: {slip.employer} | "
                               f"Bank payroll: {payer or 'not found'}"))

    # 4. Income: payslip vs what the applicant stated
    slip_annual = slip.gross_pay * 12 if slip.gross_pay else None
    checks.append(_income_check("income_vs_application", slip_annual, app.stated_annual_income,
                                "Payslip gross x12 vs stated annual income"))

    # 5. Income: payslip net pay vs salary actually received in the bank (key fraud signal)
    avg_credit = mean(bank.salary_credits) if bank.salary_credits else None
    bank_check = _income_check("income_vs_bank", slip.net_pay, avg_credit,
                               "Payslip net pay vs average payroll deposit")
    checks.append(bank_check)

    # Verified income: trust the payslip only when the bank confirms it
    if bank_check.status == "pass" and slip.gross_pay:
        monthly_income, source = slip.gross_pay, "payslip (confirmed by bank deposits)"
    elif avg_credit:
        ratio = (slip.gross_pay / slip.net_pay
                 if math_ok and slip.gross_pay and slip.net_pay else 1 / TYPICAL_TAKE_HOME)
        monthly_income, source = avg_credit * ratio, "estimated from bank deposits"
    else:
        monthly_income, source = None, "not verifiable"

    return checks, {"verified_monthly_income": monthly_income, "income_source": source,
                    "avg_salary_credit": avg_credit}
