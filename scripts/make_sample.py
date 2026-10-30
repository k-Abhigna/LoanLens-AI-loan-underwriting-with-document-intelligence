"""Make a balanced sample of REAL borrowers from the Lending Club dataset.

1. Download "Lending Club" by wordsforthewise from Kaggle.
2. Put accepted_2007_to_2018Q4.csv.gz (or .csv) in data/raw/
3. python scripts/make_sample.py
"""

from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")
OUT = Path("data/processed/borrowers.csv")
PER_CLASS = 1000

COLUMNS = [
    "id", "loan_amnt", "term", "int_rate", "installment", "grade",
    "emp_title", "emp_length", "home_ownership", "annual_inc",
    "verification_status", "issue_d", "loan_status", "purpose", "dti", "addr_state",
]


def find_raw_file() -> Path:
    for name in ["accepted_2007_to_2018Q4.csv.gz", "accepted_2007_to_2018Q4.csv"]:
        if (RAW_DIR / name).exists():
            return RAW_DIR / name
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raise FileNotFoundError(f"Put accepted_2007_to_2018Q4.csv(.gz) from Kaggle in {RAW_DIR}/")


def main():
    raw = find_raw_file()
    print(f"Reading {raw} ... (1-3 minutes)")
    df = pd.read_csv(raw, usecols=COLUMNS, low_memory=False)
    print("Total loans:", len(df))

    # Only finished loans: we know for sure whether they were repaid
    df = df[df["loan_status"].isin(["Fully Paid", "Charged Off"])]
    df = df.dropna(subset=["emp_title", "annual_inc", "dti", "emp_length", "installment"])
    df = df[(df["annual_inc"] >= 10_000) & (df["annual_inc"] <= 500_000)]
    df = df[(df["dti"] >= 0) & (df["dti"] <= 60)]

    # 50/50 repaid vs defaulted, so "approve everyone" can't look good
    paid = df[df["loan_status"] == "Fully Paid"].sample(PER_CLASS, random_state=42)
    bad = df[df["loan_status"] == "Charged Off"].sample(PER_CLASS, random_state=42)
    sample = pd.concat([paid, bad]).sample(frac=1, random_state=42)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(OUT, index=False)
    print(f"Saved {len(sample)} borrowers to {OUT}")
    print(sample["loan_status"].value_counts().to_string())


if __name__ == "__main__":
    main()
