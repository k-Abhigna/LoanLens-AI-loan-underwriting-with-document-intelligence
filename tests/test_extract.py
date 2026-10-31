import json

import pytest

from loanlens.extract import llm, rules
from loanlens.extract.classify import classify
from loanlens.extract.text import get_text


@pytest.mark.parametrize("text, expected", [
    ("$1,103.26", 1103.26),
    ("-$468.70", -468.70),
    ("$10;208.33", 10208.33),   # OCR read ',' as ';'
    ("$37,916:70", 37916.70),   # OCR read '.' as ':'
    ("", None),
])
def test_parse_money(text, expected):
    assert rules.parse_money(text) == expected


@pytest.mark.parametrize("doc_type", ["application", "payslip", "bank_statement"])
def test_classify_both_layouts(make_docs, doc_type):
    for layout in "AB":
        _, folder = make_docs(templates={"payslip": layout, "bank_statement": layout})
        text, _ = get_text(folder / f"{doc_type}.pdf")
        assert classify(text)[0] == doc_type


def test_rules_extract_layout_a_exactly(make_docs):
    case, folder = make_docs()
    for doc_type in ["application", "payslip", "bank_statement"]:
        text, _ = get_text(folder / f"{doc_type}.pdf")
        fields = rules.extract(doc_type, text).model_dump()
        for name, value in fields.items():
            assert value == case[doc_type][name], f"{doc_type}.{name}"


def test_ocr_noise_cleanup():
    text = "Redwood ManufacturingCo\nEmployee.Name: Angela.Morgan\nPay.Period: 20.18-06-01to2018-06-30"
    slip = rules.extract_payslip(text)
    assert slip.employee_name == "Angela Morgan"
    assert slip.employer == "Redwood Manufacturing Co"
    assert slip.pay_period == "2018-06-01 to 2018-06-30"


def test_ocr_cleanup_applies_to_any_extractor():
    from loanlens.schemas import PayslipFields
    slip = PayslipFields(employee_name="Kevin'Wells", employer="BrightwaveTelecom",
                         pay_period="2018-10-01to2018-10-31", gross_pay=5000.0)
    clean = rules.clean_ocr_payslip(slip)
    assert (clean.employee_name, clean.employer, clean.pay_period) == (
        "Kevin Wells", "Brightwave Telecom", "2018-10-01 to 2018-10-31")
    assert clean.gross_pay == 5000.0


def test_llm_retries_once_on_invalid_json(monkeypatch):
    answers = iter(['{"gross_pay": "lots"}', json.dumps({"gross_pay": 5000.0, "net_pay": 3900.0})])
    calls = []
    monkeypatch.setitem(llm.PROVIDERS, "fake", lambda prompt: calls.append(prompt) or next(answers))
    slip = llm.extract("payslip", "Gross Pay: $5,000.00", provider="fake")
    assert slip.gross_pay == 5000.0 and len(calls) == 2
    assert "previous answer was invalid" in calls[1]
