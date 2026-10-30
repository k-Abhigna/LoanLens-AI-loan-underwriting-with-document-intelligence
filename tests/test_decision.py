import pytest

from loanlens.checks import run_checks
from loanlens.decide import decide
from loanlens.generate.profile import FRAUD_TYPES
from loanlens.pipeline import process_folder
from loanlens.schemas import ApplicationFields, BankStatementFields, PayslipFields

EXPECTED_FAILED_CHECK = {
    "inflated_income": "income_vs_bank",
    "employer_mismatch": "employer_match",
    "payslip_math": "payslip_arithmetic",
}


def status(result, name):
    return next(c["status"] for c in result["checks"] if c["name"] == name)


def test_clean_application_passes_every_check(make_docs):
    _, folder = make_docs()
    result = process_folder(folder)
    assert all(c["status"] == "pass" for c in result["checks"])
    assert result["decision"]["decision"] == "APPROVE"


@pytest.mark.parametrize("fraud", FRAUD_TYPES)
def test_each_fraud_type_is_caught_and_rejected(make_docs, fraud):
    _, folder = make_docs(fraud=fraud)
    result = process_folder(folder)
    assert status(result, EXPECTED_FAILED_CHECK[fraud]) == "fail"
    assert result["decision"]["decision"] == "REJECT"


def test_true_income_is_recovered_from_bank_when_payslip_is_inflated(make_docs):
    case, folder = make_docs(fraud="inflated_income")
    income = process_folder(folder)["decision"]["metrics"]["verified_monthly_income"]
    assert income == pytest.approx(72000 / 12, rel=0.01)


def test_high_dti_is_rejected(make_docs):
    _, folder = make_docs(row_overrides={"dti": 40, "installment": 900})
    result = process_folder(folder)["decision"]
    assert result["decision"] == "REJECT"
    assert result["metrics"]["dti_after_loan_pct"] > 45


def test_missing_values_go_to_human_not_fraud():
    app = ApplicationFields(applicant_name="A B", employer="X Corp", stated_annual_income=60000,
                            monthly_debt_payments=500, monthly_installment=300, loan_amount=9000,
                            years_employed=5)
    checks, derived = run_checks(app, PayslipFields(), BankStatementFields())
    assert not [c for c in checks if c.status == "fail"]
    assert decide(app, checks, derived).decision == "REVIEW"


def test_missing_document_is_rejected():
    checks, derived = run_checks(ApplicationFields(), None, BankStatementFields())
    assert decide(ApplicationFields(), checks, derived).decision == "REJECT"
