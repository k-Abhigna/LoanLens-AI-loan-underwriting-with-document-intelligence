# LoanLens — Scope & Assumptions

## 1. Who is the user and what problem are they having?
**User:** Loan officer / credit analyst at a retail lender (bank or NBFC).
**Problem:** For every personal-loan application, the officer manually reads payslips,
bank statements and the application form, cross-checks income and employer, calculates
debt-to-income, and looks for tampered documents. This takes 30–60 minutes per
application, is error-prone, and fraud (inflated income) slips through.

## 2. What outcome are we trying to improve?
- Time to decision per application (target: minutes, not hours)
- Fraud catch rate on tampered documents
- Decision quality: fewer approvals of borrowers who later default
- Consistency: same documents → same decision, with written reasons

## 3. Which part of the problem should AI handle?
| Step | Handled by |
|---|---|
| Classify document type (payslip / bank statement / application) | AI |
| Extract fields (name, employer, gross/net salary, credits, EMIs) | AI |
| Cross-check documents against each other | Rules (deterministic code) |
| Compute DTI, income stability, affordability | Rules |
| Flag suspicious / tampered documents | AI + rules |
| Final approve / reject on borderline cases | Human loan officer |

## 4. How much agency should the system have?
**Recommend + act with escalation:**
- AUTO-REJECT only for objective failures (missing documents, income mismatch beyond tolerance).
- RECOMMEND approve/reject with reasons and confidence for everything else.
- A human approves every loan. Low-confidence or flagged cases go to a review queue.
- Every decision is logged with evidence (audit trail).

## Data & assumptions
- Borrower values and repayment outcomes: real, from the public Lending Club dataset (2007–2018).
- Documents: generated from those real records, because real payslips and bank
  statements are private by law. Some documents are deliberately tampered with to test fraud detection.
- Out of scope (v1): real credit bureau checks, Aadhaar/PAN verification APIs, live bank integrations.
