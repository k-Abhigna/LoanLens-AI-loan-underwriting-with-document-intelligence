"""Get plain text out of a document: PDF text layer, or OCR for scans/photos."""

from functools import lru_cache
from pathlib import Path

import pdfplumber

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


@lru_cache(maxsize=1)
def _ocr_engine():
    from rapidocr_onnxruntime import RapidOCR  # imported lazily: it is slow to load
    return RapidOCR()


def ocr_image(path: Path) -> str:
    """Run OCR and rebuild reading order: group word boxes into lines by their height."""
    result, _ = _ocr_engine()(str(path))
    if not result:
        return ""
    boxes = []
    for points, text, _score in result:
        ys = [p[1] for p in points]
        boxes.append({"x": min(p[0] for p in points), "y": sum(ys) / 4,
                      "h": max(ys) - min(ys), "text": text})
    boxes.sort(key=lambda b: b["y"])

    lines, current = [], [boxes[0]]
    for box in boxes[1:]:
        if abs(box["y"] - current[-1]["y"]) < max(box["h"], current[-1]["h"]) * 0.6:
            current.append(box)
        else:
            lines.append(current)
            current = [box]
    lines.append(current)
    return "\n".join(" ".join(b["text"] for b in sorted(line, key=lambda b: b["x"]))
                     for line in lines)


def get_text(path: str | Path) -> tuple[str, str]:
    """Return (text, method) where method is 'pdf_text' or 'ocr'."""
    path = Path(path)
    if path.suffix.lower() in IMAGE_EXTS:
        return ocr_image(path), "ocr"
    with pdfplumber.open(path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return text, "pdf_text"
