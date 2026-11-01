# Evaluation results - `gemini` extractor

Applications evaluated: **60**

| Metric | Value |
|---|---|
| Document classification accuracy | 100.0% |
| Field extraction accuracy (all fields) | 97.2% |
| Field accuracy, layout A (seen) | 97.3% |
| Field accuracy, layout B (unseen) | 97.2% |
| Fraud detection precision | 100.0% |
| Fraud detection recall | 100.0% |
| False fraud alarms on clean applications | 0 |
| Risk score AUC vs real defaults | 0.629 |
| Avg seconds per application | 12.1 |

## Extraction accuracy by document

| Document | Layout | Read with | Accuracy |
|---|---|---|---|
| application | A | pdf_text | 100.0% |
| bank_statement | A | pdf_text | 99.1% |
| bank_statement | B | pdf_text | 100.0% |
| payslip | A | ocr | 74.1% |
| payslip | A | pdf_text | 100.0% |
| payslip | B | ocr | 75.0% |
| payslip | B | pdf_text | 100.0% |

## Fraud recall by type

| Fraud type | Caught |
|---|---|
| employer_mismatch | 100.0% |
| inflated_income | 100.0% |
| payslip_math | 100.0% |

## Decisions vs real loan outcomes (untampered applications)

Default rate if every application were approved: **0.488**

| Decision | Applications | Real default rate |
|---|---|---|
| APPROVE | 28 | 39.3% |
| REJECT | 5 | 60.0% |
| REVIEW | 10 | 70.0% |

## Weakest fields

| Document | Layout | Read with | Field | Accuracy |
|---|---|---|---|---|
| payslip | A | ocr | pay_period | 18.8% |
| payslip | B | ocr | pay_period | 25.0% |
| payslip | A | ocr | employer | 37.5% |
| payslip | B | ocr | employee_name | 50.0% |
| payslip | B | ocr | employer | 50.0% |
