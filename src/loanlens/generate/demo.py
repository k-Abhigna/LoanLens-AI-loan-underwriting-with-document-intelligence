"""Create FAKE demo borrowers in the Lending Club format.

Use this only to try the project before downloading the real Kaggle data.
Numbers here are random, so evaluation results on demo data mean nothing.
"""

import random
import pandas as pd

from loanlens.config import DEMO_DIR

OUT = DEMO_DIR / "demo_borrowers.csv"
TITLES = ["Teacher", "Registered Nurse", "Sales Manager", "Truck Driver", "Software Engineer",
          "Accountant", "Store Manager", "Electrician", "Office Assistant", "Project Manager"]
PURPOSES = ["debt_consolidation", "credit_card", "home_improvement", "car", "medical"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def installment(amount: float, annual_rate: float, months: int) -> float:
    r = annual_rate / 100 / 12
    return round(amount * r / (1 - (1 + r) ** -months), 2)


def main(n: int = 40, seed: int = 7) -> None:
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        income = rng.randrange(28_000, 160_000, 500)
        amount = rng.randrange(3_000, 35_000, 250)
        term = rng.choice([36, 60])
        rate = round(rng.uniform(6, 26), 2)
        rows.append({
            "id": f"DEMO{i + 1:04d}",
            "loan_amnt": amount,
            "term": f" {term} months",
            "int_rate": rate,
            "installment": installment(amount, rate, term),
            "grade": rng.choice("ABCDEF"),
            "emp_title": rng.choice(TITLES),
            "emp_length": rng.choice(["< 1 year", "1 year", "3 years", "6 years", "10+ years"]),
            "home_ownership": rng.choice(["RENT", "MORTGAGE", "OWN"]),
            "annual_inc": income,
            "verification_status": "Not Verified",
            "issue_d": f"{rng.choice(MONTHS)}-{rng.randint(2014, 2018)}",
            "loan_status": rng.choice(["Fully Paid", "Charged Off"]),
            "purpose": rng.choice(PURPOSES),
            "dti": round(rng.uniform(2, 38), 2),
            "addr_state": rng.choice(["CA", "TX", "NY", "FL", "IL", "WA"]),
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"Saved {n} FAKE demo borrowers to {OUT}")


if __name__ == "__main__":
    main()
