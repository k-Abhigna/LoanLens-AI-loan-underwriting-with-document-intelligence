"""Render the three loan documents as PDFs with reportlab."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

W, H = LETTER


def money(x: float) -> str:
    return f"-${abs(x):,.2f}" if x < 0 else f"${x:,.2f}"


def _header(c: canvas.Canvas, title: str, subtitle: str) -> float:
    c.setFillColor(colors.HexColor("#1f3a5f"))
    c.rect(0, H - 80, W, 80, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, H - 45, title)
    c.setFont("Helvetica", 10)
    c.drawString(40, H - 63, subtitle)
    c.setFillColor(colors.black)
    return H - 110


def _rows(c: canvas.Canvas, y: float, rows: list[tuple[str, str]], x=40, gap=18) -> float:
    for label, value in rows:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, y, f"{label}:")
        c.setFont("Helvetica", 10)
        c.drawString(x + 170, y, value)
        y -= gap
    return y


def render_application(case: dict, path: Path, template: str = "A") -> None:
    a = case["application"]
    c = canvas.Canvas(str(path), pagesize=LETTER)
    y = _header(c, f"{case['bank_name']}", "Personal Loan Application Form")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Section A - Applicant")
    y = _rows(c, y - 22, [
        ("Applicant Name", a["applicant_name"]),
        ("State of Residence", a["state"]),
        ("Home Ownership", a["home_ownership"]),
        ("Application Date", a["date"]),
    ])
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y - 10, "Section B - Employment & Income")
    y = _rows(c, y - 32, [
        ("Employer", a["employer"]),
        ("Job Title", a["job_title"]),
        ("Years Employed", str(a["years_employed"])),
        ("Annual Income", money(a["stated_annual_income"])),
        ("Monthly Debt Payments", money(a["monthly_debt_payments"])),
    ])
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y - 10, "Section C - Loan Request")
    y = _rows(c, y - 32, [
        ("Loan Amount", money(a["loan_amount"])),
        ("Term", f"{a['term_months']} months"),
        ("Monthly Installment", money(a["monthly_installment"])),
        ("Purpose", a["purpose"]),
    ])
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(40, y - 30, "I certify that the information provided is true and complete.")
    c.drawString(40, y - 60, f"Signature: {a['applicant_name']}")
    c.save()


def render_payslip(case: dict, path: Path, template: str = "A") -> None:
    if template == "B":
        return _render_payslip_b(case, path)
    p = case["payslip"]
    c = canvas.Canvas(str(path), pagesize=LETTER)
    y = _header(c, p["employer"], "Employee Earnings Statement")
    y = _rows(c, y, [
        ("Employee Name", p["employee_name"]),
        ("Job Title", p["job_title"]),
        ("Pay Period", p["pay_period"]),
    ])
    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Earnings")
    c.drawString(330, y, "Amount")
    c.line(40, y - 4, 450, y - 4)
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(40, y, "Regular Salary")
    c.drawString(330, y, money(p["gross_pay"]))
    y -= 30
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Deductions")
    c.line(40, y - 4, 450, y - 4)
    y -= 20
    c.setFont("Helvetica", 10)
    for name, amount in p["deductions"].items():
        c.drawString(40, y, name)
        c.drawString(330, y, money(amount))
        y -= 16
    y -= 14
    y = _rows(c, y, [
        ("Gross Pay", money(p["gross_pay"])),
        ("Total Deductions", money(p["total_deductions"])),
        ("Net Pay", money(p["net_pay"])),
        ("YTD Gross", money(p["ytd_gross"])),
    ])
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(40, 40, "This statement is computer generated. Retain for your records.")
    c.save()


def render_bank_statement(case: dict, path: Path, template: str = "A") -> None:
    if template == "B":
        return _render_bank_statement_b(case, path)
    b = case["bank_statement"]
    c = canvas.Canvas(str(path), pagesize=LETTER)
    y = _header(c, case["bank_name"], "Checking Account Statement")
    y = _rows(c, y, [
        ("Account Holder", b["account_holder"]),
        ("Account Number", b["account_number"]),
        ("Statement Period", b["period"]),
        ("Opening Balance", money(b["opening_balance"])),
        ("Closing Balance", money(b["closing_balance"])),
    ])
    y -= 10
    c.setFont("Helvetica-Bold", 10)
    for x, label in [(40, "Date"), (120, "Description"), (390, "Amount"), (480, "Balance")]:
        c.drawString(x, y, label)
    c.line(40, y - 4, 560, y - 4)
    y -= 18
    c.setFont("Helvetica", 9)
    for t in b["transactions"]:
        if y < 50:
            c.showPage()
            y = H - 50
            c.setFont("Helvetica", 9)
        c.drawString(40, y, t["date"])
        c.drawString(120, y, t["description"])
        c.drawRightString(450, y, money(t["amount"]))
        c.drawRightString(550, y, money(t["balance"]))
        y -= 15
    c.save()


# ---------- Layout B: a different employer's payroll system / a different bank ----------

def _render_payslip_b(case: dict, path: Path) -> None:
    p = case["payslip"]
    c = canvas.Canvas(str(path), pagesize=LETTER)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(W / 2, H - 50, "PAY SLIP")
    c.setFont("Helvetica", 11)
    c.drawCentredString(W / 2, H - 70, p["employer"])
    c.line(40, H - 82, W - 40, H - 82)

    y = H - 110
    for left, right in [(("Staff Name", p["employee_name"]), ("Designation", p["job_title"])),
                        (("Period Covered", p["pay_period"]), ("Currency", "USD"))]:
        for x, (label, value) in zip((40, 330), (left, right)):
            c.setFont("Helvetica", 8)
            c.drawString(x, y + 12, label.upper())
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x, y, value)
        y -= 40

    c.setFillColor(colors.HexColor("#e8eef5"))
    c.rect(40, y - 6, W - 80, 18, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(45, y, "Component")
    c.drawRightString(W - 45, y, "USD")
    y -= 22
    c.setFont("Helvetica", 10)
    items = [("Basic Salary", p["gross_pay"])] + [(n, -v) for n, v in p["deductions"].items()]
    for name, amount in items:
        c.drawString(45, y, name)
        c.drawRightString(W - 45, y, f"{amount:,.2f}")
        y -= 16
    y -= 10
    c.line(40, y + 8, W - 40, y + 8)
    for label, amount in [("Gross Earnings", p["gross_pay"]),
                          ("Less Deductions", p["total_deductions"]),
                          ("Net Amount Payable", p["net_pay"]),
                          ("Earnings Year To Date", p["ytd_gross"])]:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(45, y - 6, label)
        c.drawRightString(W - 45, y - 6, f"{amount:,.2f}")
        y -= 18
    c.save()


def _render_bank_statement_b(case: dict, path: Path) -> None:
    b = case["bank_statement"]
    c = canvas.Canvas(str(path), pagesize=LETTER)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, H - 50, "Coastal Union Bank")
    c.setFont("Helvetica", 10)
    c.drawRightString(W - 40, H - 50, "ACCOUNT SUMMARY")
    y = _rows(c, H - 90, [
        ("Customer Name", b["account_holder"]),
        ("Account No.", b["account_number"]),
        ("Period", b["period"]),
        ("Beginning Balance", f"{b['opening_balance']:,.2f}"),
        ("Ending Balance", f"{b['closing_balance']:,.2f}"),
    ])
    y -= 10
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y, "Date")
    c.drawString(110, y, "Details")
    c.drawRightString(420, y, "Withdrawals")
    c.drawRightString(500, y, "Deposits")
    c.drawRightString(570, y, "Balance")
    c.line(40, y - 4, W - 40, y - 4)
    y -= 16
    c.setFont("Helvetica", 9)
    for t in b["transactions"]:
        c.drawString(40, y, t["date"])
        c.drawString(110, y, t["description"])
        col = 500 if t["amount"] > 0 else 420
        c.drawRightString(col, y, f"{abs(t['amount']):,.2f}")
        c.drawRightString(570, y, f"{t['balance']:,.2f}")
        y -= 14
    c.save()


RENDERERS = {
    "application": render_application,
    "payslip": render_payslip,
    "bank_statement": render_bank_statement,
}
