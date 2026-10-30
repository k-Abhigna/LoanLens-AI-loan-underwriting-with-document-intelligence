import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loanlens.generate.pdfs import RENDERERS  # noqa: E402
from loanlens.generate.profile import build_case  # noqa: E402

# A made-up borrower in Lending Club format (test fixture, not real data)
ROW = {
    "id": "TEST001", "loan_amnt": 12000, "term": " 36 months", "int_rate": 11.5,
    "installment": 395.71, "grade": "B", "emp_title": "registered nurse",
    "emp_length": "6 years", "home_ownership": "RENT", "annual_inc": 72000,
    "verification_status": "Verified", "issue_d": "Mar-2016", "loan_status": "Fully Paid",
    "purpose": "debt_consolidation", "dti": 14.2, "addr_state": "TX",
}


@pytest.fixture
def row():
    return dict(ROW)


def write_docs(case: dict, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for doc_type, render in RENDERERS.items():
        render(case, folder / f"{doc_type}.pdf", case["templates"].get(doc_type, "A"))
    return folder


@pytest.fixture
def make_docs(tmp_path):
    def _make(fraud=None, templates=None, row_overrides=None):
        case = build_case({**ROW, **(row_overrides or {})}, fraud, templates)
        return case, write_docs(case, tmp_path / (fraud or "clean"))
    return _make
