# Evaluation results - `rules` extractor

Applications evaluated: **300**

| Metric | Value |
|---|---|
| Document classification accuracy | 100.0% |
| Field extraction accuracy (all fields) | 85.3% |
| Field accuracy, layout A (seen) | 99.6% |
| Field accuracy, layout B (unseen) | 0.0% |
| Fraud detection precision | 60.7% |
| Fraud detection recall | 78.3% |
| False fraud alarms on clean applications | 35 |
| Risk score AUC vs real defaults | 0.547 |
| Avg seconds per application | 4.65 |

## Extraction accuracy by document

| Document | Layout | Read with | Accuracy |
|---|---|---|---|
| application | A | pdf_text | 100.0% |
| bank_statement | A | pdf_text | 100.0% |
| bank_statement | B | pdf_text | 0.0% |
| payslip | A | ocr | 94.7% |
| payslip | A | pdf_text | 100.0% |
| payslip | B | ocr | 0.0% |
| payslip | B | pdf_text | 0.0% |

## Fraud recall by type

| Fraud type | Caught |
|---|---|
| employer_mismatch | 55.0% |
| inflated_income | 84.6% |
| payslip_math | 91.3% |

## Decisions vs real loan outcomes (untampered applications)

Default rate if every application were approved: **0.524**

| Decision | Applications | Real default rate |
|---|---|---|
| APPROVE | 90 | 45.6% |
| REJECT | 41 | 51.2% |
| REVIEW | 100 | 59.0% |

## Weakest fields

| Document | Layout | Read with | Field | Accuracy |
|---|---|---|---|---|
| bank_statement | B | pdf_text | opening_balance | 0.0% |
| bank_statement | B | pdf_text | closing_balance | 0.0% |
| bank_statement | B | pdf_text | salary_credits | 0.0% |
| bank_statement | B | pdf_text | salary_payer | 0.0% |
| bank_statement | B | pdf_text | account_holder | 0.0% |
