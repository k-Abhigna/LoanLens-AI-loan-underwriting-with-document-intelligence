"""Evidence highlighting: show where on the page each extracted value was found.

A loan officer should never have to trust a number blindly. For every extracted field we
search the document for that value and draw a coloured box around it.
"""

import re
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont

from loanlens.extract.rules import MONEY, parse_money
from loanlens.extract.text import IMAGE_EXTS, ocr_boxes

# Fields worth pointing at, per document type (numbers like years/term are too ambiguous)
FIELDS = {
    "application": ["applicant_name", "employer", "stated_annual_income",
                    "monthly_debt_payments", "loan_amount", "monthly_installment"],
    "payslip": ["employee_name", "employer", "pay_period", "gross_pay", "total_deductions",
                "net_pay", "ytd_gross"],
    "bank_statement": ["account_holder", "opening_balance", "closing_balance",
                       "salary_credits"],
}
PALETTE = ["#22d3ee", "#a78bfa", "#f472b6", "#facc15", "#4ade80", "#fb923c", "#60a5fa"]
RENDER_SCALE = 2


def _norm(text: str) -> str:
    return re.sub(r"[^0-9a-z]", "", text.lower())


def _values(value) -> list:
    """A field's value(s) as a list; salary_credits is already a list."""
    if value is None or isinstance(value, bool):
        return []
    values = value if isinstance(value, list) else [value]
    return [v for v in values if isinstance(v, float) or (isinstance(v, str) and len(v) >= 3)]


def _render(path: Path) -> Image.Image:
    if path.suffix.lower() in IMAGE_EXTS:
        return Image.open(path).convert("RGB")
    pdf = pdfium.PdfDocument(str(path))
    image = pdf[0].render(scale=RENDER_SCALE).to_pil().convert("RGB")
    pdf.close()
    return image


def _find_in_pdf(path: Path, value) -> list[tuple]:
    pattern = re.escape(f"{abs(value):,.2f}") if isinstance(value, float) else re.escape(value)
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[0]
        return [(m["x0"] * RENDER_SCALE, m["top"] * RENDER_SCALE,
                 m["x1"] * RENDER_SCALE, m["bottom"] * RENDER_SCALE)
                for m in page.search(pattern, regex=True, case=False)]


def _find_in_scan(path: Path, value) -> list[tuple]:
    hits = []
    for box in ocr_boxes(str(path)):
        if isinstance(value, float):
            # Compare as numbers: OCR may read "1,103.26" as "1;103.26"
            found = any(abs((parse_money(m) or -1) - abs(value)) < 0.005
                        for m in re.findall(MONEY, box["text"]))
        else:
            found = _norm(value) in _norm(box["text"])
        if found:
            hits.append((box["x0"], box["y0"], box["x1"], box["y1"]))
    return hits


def _rgba(hex_color: str, alpha: int) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def highlight(path: Path, doc_type: str, fields: dict) -> tuple[Image.Image, list[dict]]:
    """Return the page image with numbered boxes drawn, and one legend row per field.

    Boxes are translucent and labelled with a number badge (not text) so they never hide
    the neighbouring lines; the field names go in the legend next to the image.
    """
    image = _render(path).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    radius = max(10, image.width // 90)
    font = ImageFont.load_default(size=int(radius * 1.3))
    find = _find_in_scan if path.suffix.lower() in IMAGE_EXTS else _find_in_pdf

    legend = []
    for i, field in enumerate(FIELDS.get(doc_type, [])):
        number, color = i + 1, PALETTE[i % len(PALETTE)]
        values = _values(fields.get(field))
        boxes = [b for v in values for b in find(path, v)]
        for x0, y0, x1, y1 in boxes:
            pad = 3
            draw.rectangle((x0 - pad, y0 - pad, x1 + pad, y1 + pad),
                           fill=_rgba(color, 60), outline=_rgba(color, 255), width=3)
            # Number badge just left of the box
            cx, cy = x0 - pad - radius - 4, (y0 + y1) / 2
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                         fill=_rgba(color, 255))
            draw.text((cx, cy), str(number), fill="#0b1220", font=font, anchor="mm")
        legend.append({"number": number, "field": field, "value": fields.get(field),
                       "color": color, "found": bool(boxes), "extracted": bool(values)})
    return Image.alpha_composite(image, overlay).convert("RGB"), legend
