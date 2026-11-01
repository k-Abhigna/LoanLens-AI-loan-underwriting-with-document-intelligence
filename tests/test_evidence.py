from loanlens.evidence import highlight


def test_every_extracted_value_is_located_on_the_page(make_docs):
    case, folder = make_docs()
    for doc_type in ["application", "payslip", "bank_statement"]:
        fields = {k: case[doc_type].get(k) for k in case[doc_type]}
        image, legend = highlight(folder / f"{doc_type}.pdf", doc_type, fields)
        assert image.size[0] > 0
        assert all(item["found"] for item in legend if item["extracted"]), doc_type


def test_missing_value_is_reported_not_located(make_docs):
    _, folder = make_docs()
    _, legend = highlight(folder / "payslip.pdf", "payslip", {"net_pay": None, "gross_pay": 1.23})
    rows = {item["field"]: item for item in legend}
    assert not rows["net_pay"]["extracted"]
    assert rows["gross_pay"]["extracted"] and not rows["gross_pay"]["found"]
