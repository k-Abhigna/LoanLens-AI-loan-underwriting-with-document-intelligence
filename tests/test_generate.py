import pytest

from loanlens.generate.profile import FRAUD_TYPES, build_case


def test_same_borrower_gives_same_documents(row):
    assert build_case(row) == build_case(row)


def test_clean_payslip_adds_up_and_matches_bank(row):
    case = build_case(row)
    p, b = case["payslip"], case["bank_statement"]
    assert p["gross_pay"] == pytest.approx(72000 / 12, abs=0.01)
    assert p["gross_pay"] - p["total_deductions"] == pytest.approx(p["net_pay"], abs=0.01)
    assert b["salary_credits"] == [p["net_pay"]] * 3


def test_existing_debt_comes_from_real_dti(row):
    case = build_case(row)
    assert case["application"]["monthly_debt_payments"] == pytest.approx(6000 * 0.142, abs=0.01)


@pytest.mark.parametrize("fraud", FRAUD_TYPES)
def test_fraud_never_touches_bank_statement(row, fraud):
    assert build_case(row, fraud)["bank_statement"] == build_case(row)["bank_statement"]
    assert build_case(row, fraud)["labels"]["fraud_type"] == fraud


def test_inflated_income_raises_payslip_above_bank(row):
    case = build_case(row, "inflated_income")
    assert case["payslip"]["net_pay"] > case["bank_statement"]["salary_credits"][0] * 1.3
