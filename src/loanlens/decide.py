"""Credit decision: APPROVE / REVIEW / REJECT with reasons a loan officer can read."""

from loanlens.config import POLICY
from loanlens.schemas import ApplicationFields, Check, Decision


def _risk_score(dti_after: float, lti: float, years: int, n_warn: int, n_fail: int) -> float:
    """0 = very safe, 100 = very risky. Used to rank applications, not to decide alone."""
    score = min(dti_after / 60, 1) * 50
    score += min(lti / 0.6, 1) * 20
    score += 10 if years < 1 else 5 if years < 3 else 0
    score += 10 * n_warn + 30 * n_fail
    return round(min(score, 100), 1)


def decide(app: ApplicationFields | None, checks: list[Check], derived: dict,
           used_ocr: bool = False) -> Decision:
    fails = [c for c in checks if c.status == "fail"]
    warns = [c for c in checks if c.status == "warn"]

    if app is None or not derived:
        return Decision(decision="REJECT", reasons=[c.detail for c in fails] or ["Incomplete"],
                        risk_score=100, confidence="high", metrics={})

    income = derived.get("verified_monthly_income")
    debt = app.monthly_debt_payments or 0
    emi = app.monthly_installment or 0
    if not income:
        reasons = ([f"Document verification failed - {c.name}: {c.detail}" for c in fails]
                   + ["Income could not be verified"]
                   + [f"{c.name}: {c.detail}" for c in warns])
        return Decision(decision="REJECT" if fails else "REVIEW", reasons=reasons,
                        risk_score=100 if fails else 80, confidence="low", metrics={})

    dti_after = (debt + emi) / income * 100
    lti = (app.loan_amount or 0) / (income * 12)
    years = app.years_employed if app.years_employed is not None else 0
    metrics = {
        "verified_monthly_income": round(income, 2),
        "income_source": derived["income_source"],
        "existing_monthly_debt": round(debt, 2),
        "new_emi": round(emi, 2),
        "dti_after_loan_pct": round(dti_after, 1),
        "loan_to_income": round(lti, 2),
        "years_employed": years,
    }

    reasons, decision = [], "APPROVE"
    # Hard stops
    for c in fails:
        reasons.append(f"Document verification failed - {c.name}: {c.detail}")
    if dti_after > POLICY["dti_reject_above"]:
        reasons.append(f"DTI after loan {dti_after:.1f}% exceeds {POLICY['dti_reject_above']}%")
    if reasons:
        decision = "REJECT"
    else:
        # Soft flags -> a human looks at it
        for c in warns:
            reasons.append(f"Check needs attention - {c.name}: {c.detail}")
        if dti_after > POLICY["dti_review_above"]:
            reasons.append(f"DTI after loan {dti_after:.1f}% is above "
                           f"{POLICY['dti_review_above']}%")
        if lti > POLICY["loan_to_income_review_above"]:
            reasons.append(f"Loan is {lti:.0%} of annual income")
        if years < POLICY["min_employment_years"]:
            reasons.append(f"Employed less than {POLICY['min_employment_years']} year")
        if reasons:
            decision = "REVIEW"
        else:
            reasons.append(f"Income verified, DTI after loan {dti_after:.1f}%, all checks passed")

    confidence = "high"
    if warns or used_ocr:
        confidence = "medium"
    if len(warns) >= 2:
        confidence = "low"

    return Decision(decision=decision, reasons=reasons, confidence=confidence, metrics=metrics,
                    risk_score=_risk_score(dti_after, lti, years, len(warns), len(fails)))
