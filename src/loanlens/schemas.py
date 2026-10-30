"""Data models for every stage of the pipeline.

Pydantic checks types for us, so a bad LLM answer (e.g. a total written as text)
fails loudly instead of silently breaking a decision later.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

DocType = Literal["application", "payslip", "bank_statement", "unknown"]


class ApplicationFields(BaseModel):
    applicant_name: Optional[str] = None
    employer: Optional[str] = None
    job_title: Optional[str] = None
    years_employed: Optional[int] = None
    stated_annual_income: Optional[float] = None
    monthly_debt_payments: Optional[float] = None
    loan_amount: Optional[float] = None
    term_months: Optional[int] = None
    monthly_installment: Optional[float] = None
    purpose: Optional[str] = None
    home_ownership: Optional[str] = None


class PayslipFields(BaseModel):
    employee_name: Optional[str] = None
    employer: Optional[str] = None
    pay_period: Optional[str] = None
    gross_pay: Optional[float] = None
    total_deductions: Optional[float] = None
    net_pay: Optional[float] = None
    ytd_gross: Optional[float] = None


class BankStatementFields(BaseModel):
    account_holder: Optional[str] = None
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    salary_credits: list[float] = Field(default_factory=list)
    salary_payer: Optional[str] = None


class Check(BaseModel):
    name: str
    status: Literal["pass", "warn", "fail"]
    detail: str


class Decision(BaseModel):
    decision: Literal["APPROVE", "REVIEW", "REJECT"]
    reasons: list[str]
    risk_score: float  # 0 (safe) .. 100 (risky)
    confidence: Literal["high", "medium", "low"]
    metrics: dict
