"""Turn one real Lending Club borrower row into the facts printed on their documents.

Lending Club gives us the real numbers (income, debt-to-income, loan, outcome).
It does NOT give names or employer names (privacy), so those are fictional.
"""

import random
import re
from datetime import date, timedelta

FIRST_NAMES = ["James", "Maria", "Robert", "Linda", "Michael", "Patricia", "David", "Jennifer",
               "Daniel", "Elizabeth", "Kevin", "Susan", "Brian", "Karen", "Jason", "Nancy",
               "Anthony", "Lisa", "Mark", "Angela", "Steven", "Michelle", "Paul", "Laura"]
LAST_NAMES = ["Carter", "Nguyen", "Patel", "Brooks", "Ramirez", "Coleman", "Foster", "Hughes",
              "Jenkins", "Kim", "Lopez", "Morgan", "Perry", "Reed", "Sanders", "Turner",
              "Ward", "Bennett", "Diaz", "Howard", "Price", "Russell", "Stone", "Wells"]
EMPLOYERS = ["Northwind Logistics Inc", "Bluepeak Health Systems", "Granite State Builders LLC",
             "Silverline Retail Group", "Harborview Medical Center", "Crestline Software Corp",
             "Evergreen School District", "Summit Financial Services", "Redwood Manufacturing Co",
             "Lakeside Hospitality LLC", "Ironbridge Engineering", "Pioneer Transport Co",
             "Brightwave Telecom", "Maple Grove Insurance", "Cobalt Energy Partners"]
BANK_NAME = "First Meridian Bank"
# Layout "A" is what the regex rules were written for; "B" is an unseen layout from another
# employer / bank, used to test how extractors generalise.
TEMPLATES = ["A", "B"]
PAYER_PREFIX = {"A": "PAYROLL DEP", "B": "DIRECT DEPOSIT SALARY"}

FRAUD_TYPES = ["inflated_income", "employer_mismatch", "payslip_math"]


def _parse_years(emp_length) -> int:
    """'10+ years' -> 10, '< 1 year' -> 0, '3 years' -> 3."""
    text = str(emp_length)
    if "<" in text:
        return 0
    match = re.search(r"\d+", text)
    return int(match.group()) if match else 0


def _parse_term(term) -> int:
    match = re.search(r"\d+", str(term))
    return int(match.group()) if match else 36


def _parse_issue_date(issue_d) -> date:
    """'Dec-2015' -> 2015-12-01. Falls back to a fixed date if unreadable."""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    try:
        mon, year = str(issue_d).split("-")
        return date(int(year), months.index(mon[:3].title()) + 1, 1)
    except (ValueError, IndexError):
        return date(2016, 1, 1)


def _r2(x: float) -> float:
    return round(float(x), 2)


def build_case(row: dict, fraud_type: str | None = None, templates: dict | None = None) -> dict:
    """Everything needed to render the 3 documents for one application, plus the truth labels."""
    templates = templates or {"payslip": "A", "bank_statement": "A"}
    rng = random.Random(str(row["id"]))  # same borrower -> same documents every run

    name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
    employer = rng.choice(EMPLOYERS)
    job_title = str(row["emp_title"]).strip().title()[:40]
    annual_income = float(row["annual_inc"])
    monthly_gross = annual_income / 12
    issue = _parse_issue_date(row["issue_d"])
    pay_month_end = issue - timedelta(days=1)  # last month before the loan application

    # US-style payroll deductions (approximate rates)
    deductions = {
        "Federal Income Tax": monthly_gross * rng.uniform(0.09, 0.15),
        "State Income Tax": monthly_gross * rng.uniform(0.02, 0.05),
        "Social Security": monthly_gross * 0.062,
        "Medicare": monthly_gross * 0.0145,
        "401(k) Contribution": monthly_gross * rng.choice([0, 0.03, 0.05]),
    }
    deductions = {k: _r2(v) for k, v in deductions.items() if v > 0}
    gross = _r2(monthly_gross)
    total_ded = _r2(sum(deductions.values()))
    net = _r2(gross - total_ded)

    # Real debt-to-income from Lending Club -> existing monthly debt payments
    monthly_debt = _r2(float(row["dti"]) / 100 * monthly_gross)

    case = {
        "application_id": str(row["id"]),
        "bank_name": BANK_NAME,
        "templates": templates,
        "application": {
            "applicant_name": name,
            "employer": employer,
            "job_title": job_title,
            "years_employed": _parse_years(row["emp_length"]),
            "stated_annual_income": _r2(annual_income),
            "monthly_debt_payments": monthly_debt,
            "loan_amount": _r2(row["loan_amnt"]),
            "term_months": _parse_term(row["term"]),
            "monthly_installment": _r2(row["installment"]),
            "purpose": str(row["purpose"]).replace("_", " ").title(),
            "home_ownership": str(row["home_ownership"]).title(),
            "state": str(row.get("addr_state", "")),
            "date": issue.isoformat(),
        },
        "payslip": {
            "employee_name": name,
            "employer": employer,
            "job_title": job_title,
            "pay_period": f"{pay_month_end.replace(day=1).isoformat()} to {pay_month_end.isoformat()}",
            "gross_pay": gross,
            "deductions": deductions,
            "total_deductions": total_ded,
            "net_pay": net,
            "ytd_gross": _r2(gross * pay_month_end.month),
        },
        "bank_statement": _bank_statement(rng, name, employer, net, monthly_debt,
                                          float(row["installment"]), pay_month_end,
                                          str(row["home_ownership"]),
                                          PAYER_PREFIX[templates["bank_statement"]]),
        "labels": {
            "fraud_type": fraud_type,
            "loan_status": str(row["loan_status"]),
            "defaulted": str(row["loan_status"]) == "Charged Off",
            "grade": str(row.get("grade", "")),
        },
    }
    if fraud_type:
        _tamper(case, fraud_type, rng)
    return case


def _bank_statement(rng, name, employer, net_pay, monthly_debt, installment, period_end, home,
                    payer_prefix):
    """3 months of transactions. Salary credits show the TRUE net pay."""
    months = []
    d = period_end.replace(day=1)
    for _ in range(3):
        months.insert(0, d)
        d = (d - timedelta(days=1)).replace(day=1)

    balance = _r2(rng.uniform(300, 6000))
    opening = balance
    rent = _r2(net_pay * rng.uniform(0.20, 0.35)) if home.upper() in ("RENT", "MORTGAGE") else 0
    txns = []
    payer = f"{payer_prefix} {employer.upper()[:22].strip()}"
    for m in months:
        rows = [
            (m.replace(day=1), payer, net_pay),
            (m.replace(day=3), "RENT PAYMENT" if home.upper() == "RENT" else "MORTGAGE PMT", -rent),
            (m.replace(day=8), "CREDIT CARD / LOAN PAYMENTS", -monthly_debt),
            (m.replace(day=12), "GROCERY STORE", -_r2(rng.uniform(150, 600))),
            (m.replace(day=18), "UTILITIES", -_r2(rng.uniform(80, 250))),
            (m.replace(day=24), "CARD PURCHASES", -_r2(rng.uniform(100, 700))),
        ]
        for when, desc, amount in rows:
            if amount == 0:
                continue
            balance = _r2(balance + amount)
            txns.append({"date": when.isoformat(), "description": desc, "amount": _r2(amount),
                         "balance": balance})
    return {
        "account_holder": name,
        "account_number": f"XXXX{rng.randint(1000, 9999)}",
        "period": f"{months[0].isoformat()} to {period_end.isoformat()}",
        "opening_balance": opening,
        "closing_balance": balance,
        "transactions": txns,
        "salary_credits": [net_pay] * 3,
        "salary_payer": payer,
    }


def _tamper(case: dict, fraud_type: str, rng: random.Random) -> None:
    """Simulate common loan-document fraud. The bank statement is left untouched."""
    p, app = case["payslip"], case["application"]
    if fraud_type == "inflated_income":
        # Forger scales the whole payslip and the stated income consistently
        k = rng.uniform(1.4, 1.8)
        p["deductions"] = {n: _r2(v * k) for n, v in p["deductions"].items()}
        p["gross_pay"] = _r2(p["gross_pay"] * k)
        p["total_deductions"] = _r2(sum(p["deductions"].values()))
        p["net_pay"] = _r2(p["gross_pay"] - p["total_deductions"])
        p["ytd_gross"] = _r2(p["ytd_gross"] * k)
        app["stated_annual_income"] = _r2(p["gross_pay"] * 12)
    elif fraud_type == "employer_mismatch":
        # Payslip made from another company's template
        p["employer"] = rng.choice([e for e in EMPLOYERS if e != p["employer"]])
    elif fraud_type == "payslip_math":
        # Only the gross figure was edited, so the arithmetic no longer adds up
        p["gross_pay"] = _r2(p["gross_pay"] * rng.uniform(1.3, 1.6))
        app["stated_annual_income"] = _r2(p["gross_pay"] * 12)
    else:
        raise ValueError(f"Unknown fraud type: {fraud_type}")
