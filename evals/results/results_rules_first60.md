# Evaluation results - `rules` extractor

Applications evaluated: **60**

| Metric | Value |
|---|---|
| Document classification accuracy | 100.0% |
| Field extraction accuracy (all fields) | 81.7% |
| Field accuracy, layout A (seen) | 99.5% |
| Field accuracy, layout B (unseen) | 0.0% |
| Fraud detection precision | 55.6% |
| Fraud detection recall | 88.2% |
| False fraud alarms on clean applications | 12 |
| Risk score AUC vs real defaults | 0.522 |
| Avg seconds per application | 1.6 |

## Extraction accuracy by document

| Document | Layout | Read with | Accuracy |
|---|---|---|---|
| application | A | pdf_text | 100.0% |
| bank_statement | A | pdf_text | 100.0% |
| bank_statement | B | pdf_text | 0.0% |
| payslip | A | ocr | 94.6% |
| payslip | A | pdf_text | 100.0% |
| payslip | B | ocr | 0.0% |
| payslip | B | pdf_text | 0.0% |

## Fraud recall by type

| Fraud type | Caught |
|---|---|
| employer_mismatch | 66.7% |
| inflated_income | 83.3% |
| payslip_math | 100.0% |

## Decisions vs real loan outcomes (untampered applications)

Default rate if every application were approved: **0.488**

| Decision | Applications | Real default rate |
|---|---|---|
| APPROVE | 13 | 30.8% |
| REJECT | 13 | 38.5% |
| REVIEW | 17 | 70.6% |

## Weakest fields

| Document | Layout | Read with | Field | Accuracy |
|---|---|---|---|---|
| bank_statement | B | pdf_text | opening_balance | 0.0% |
| bank_statement | B | pdf_text | closing_balance | 0.0% |
| bank_statement | B | pdf_text | salary_credits | 0.0% |
| bank_statement | B | pdf_text | salary_payer | 0.0% |
| bank_statement | B | pdf_text | account_holder | 0.0% |
