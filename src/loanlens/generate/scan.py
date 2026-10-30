"""Make a PDF look like a phone photo / scan: image, slight tilt, blur, noise."""

import random
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageFilter


def pdf_to_scan(pdf_path: Path, out_path: Path, seed: int = 0) -> None:
    rng = random.Random(seed)
    pdf = pdfium.PdfDocument(str(pdf_path))
    page = pdf[0].render(scale=2).to_pil().convert("L")  # ~144 dpi, grayscale
    pdf.close()

    page = page.rotate(rng.uniform(-1.5, 1.5), expand=True, fillcolor=255)
    page = page.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 0.8)))

    # Salt-and-pepper style speckles
    pixels = page.load()
    w, h = page.size
    for _ in range(w * h // 400):
        pixels[rng.randrange(w), rng.randrange(h)] = rng.choice([0, 255])

    Image.Image.save(page, out_path, quality=80)
