# LoanLens — Scope & Assumptions

## 1. Who is the user and what problem are they having?
**User:** Loan officer / credit analyst at a retail lender (bank or NBFC).

**Problem:** For every personal-loan application the officer manually reads the application
form, payslip and bank statement, cross-checks income and employer, calculates debt-to-income
and looks for tampered documents. This takes 30–60 minutes per application, is error-prone,
and income fraud slips through.

## 2. What outcome are we trying to improve?
- Time to decision per application (target: seconds of machine time + a short human review)
- Fraud catch rate on tampered documents, with few false alarms
- Decision quality: lower default rate among approved loans
- Consistency: same documents → same decision, with written reasons and an audit trail

## 3. Which part of the problem should AI handle?
| Step | Handled by |
|---|---|
| Read the document (PDF text layer or OCR for scans) | OCR / PDF parser |
| Classify document type | Keyword classifier |
| Extract fields into a fixed schema | LLM (Gemini free tier); regex rules as offline baseline and fallback |
| Cross-check documents against each other | Deterministic rules |
| Compute verified income, DTI, loan-to-income | Deterministic rules |
| Recommend APPROVE / REVIEW / REJECT with reasons | Policy rules |
| Final decision | **Human loan officer** |

AI is used only where the input is unstructured (reading documents). Everything that decides
money is plain, auditable code, because a regulator or credit committee must be able to read it.

## 4. How much agency should the system have?
**Recommend, with escalation. Never act alone.**
- REJECT is recommended only for objective failures: missing documents, documents that
  contradict each other (fraud signals), or DTI above policy.
- A missing or unreadable value is "could not verify" → REVIEW by a human, **never** "fraud".
- Every recommendation and every human override is written to an audit log.
  Overriding the AI requires a written reason.

## Data & assumptions
- Borrower numbers (income, existing debt via DTI, loan amount, term, EMI) and repayment
  outcomes are **real**, from the public Lending Club dataset (2007–2018).
- Documents are generated from those real records, because real payslips and bank statements
  are private by law. Names and employer names are fictional.
- 20% of applications contain injected fraud (inflated income, wrong employer, edited gross pay).
- 25% of payslips are scanned images (blur, tilt, noise) to exercise OCR.
- 30% of payslips/bank statements use an **unseen layout** to test generalisation.
- Out of scope (v1): credit bureau pulls, ID verification APIs, live bank integrations,
  non-US document formats.
