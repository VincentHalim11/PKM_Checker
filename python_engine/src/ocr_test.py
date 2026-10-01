import pymupdf
import pytesseract
import re
from PIL import Image
from pathlib import Path

PDF_PATH = Path(r"D:\PDF_PKM\PROPOSALPKM_GFT.pdf")
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

doc = pymupdf.open(PDF_PATH)

# Halaman 16 secara fisik = index 15 karena Python mulai dari 0
START_PAGE = 10
END_PAGE = min(20, len(doc))

for physical_page in range(START_PAGE, END_PAGE + 1):
    print(f"\n{'=' * 60}")
    print(f"OCR HALAMAN FISIK {physical_page}")
    print(f"{'=' * 60}")

    page = doc[physical_page - 1]

    pix = page.get_pixmap(
        matrix=pymupdf.Matrix(2, 2),
        alpha=False
    )

    img = Image.frombytes(
        "RGB",
        [pix.width, pix.height],
        pix.samples
    )

    text = pytesseract.image_to_string(img, lang="eng")

    print(text[:1000])

    lines = [
        re.sub(r"\s+", " ", line).strip().upper()
        for line in text.splitlines()
    ]

    has_bare_lampiran = any(
        line == "LAMPIRAN"
        for line in lines
    )

    has_lampiran_1 = any(
        re.match(r"^LAMPIRAN\s*1\s*[:.]?", line)
        for line in lines
    )

    if has_bare_lampiran or has_lampiran_1:
        print("✅ DETEKSI: AWAL LAMPIRAN")
    else:
        print("❌ Bukan awal Lampiran")