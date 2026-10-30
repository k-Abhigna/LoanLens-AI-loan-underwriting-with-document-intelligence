"""Paths and credit-policy settings in one place, so they are easy to find and change."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW_DIR = DATA / "raw"
PROCESSED_DIR = DATA / "processed"
GENERATED_DIR = DATA / "generated"
DEMO_DIR = DATA / "demo"
AUDIT_LOG = DATA / "audit_log.jsonl"
RESULTS_DIR = ROOT / "evals" / "results"

# ---- Credit policy (what a bank's credit team would write down) ----
POLICY = {
    # Debt-to-income AFTER adding the new loan EMI, in percent of gross monthly income
    "dti_reject_above": 45.0,
    "dti_review_above": 35.0,
    # Loan amount as a share of annual income
    "loan_to_income_review_above": 0.50,
    # Employment shorter than this (years) goes to a human
    "min_employment_years": 1,
    # Cross-document tolerances
    "income_tolerance": 0.10,       # payslip vs application vs bank statement
    "income_reject_mismatch": 0.25,  # beyond this the income is treated as not verified
    "employer_match_threshold": 0.80,
}
