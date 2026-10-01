import re
import sys
from collections import Counter

import pymupdf

from filters import is_symbol_only
from rules import FONT


# ============================================================
# FONT RULE
# ============================================================

EXPECTED_FONT = FONT["family"]   # sumber: rules.py


# ============================================================
# FONT NORMALIZATION
# ============================================================

def normalize_font_name(font_name: str) -> str:
    """
    Mengubah nama font PDF menjadi nama font yang lebih mudah dibaca.
    """

    name = font_name.strip()

    # Buang prefiks subset PDF, mis. "ABCDEF+TimesNewRomanPSMT"
    name = re.sub(r"^[A-Z]{6}\+", "", name)

    # Times New Roman variants
    if (
        name.startswith("TimesNewRoman")
        or name.startswith("Times New Roman")
    ):
        return "Times New Roman"

    # Calibri variants
    if name.startswith("Calibri"):
        return "Calibri"

    # Arial variants
    if name.startswith("Arial"):
        return "Arial"

    # Symbol
    if name.startswith("Symbol"):
        return "Symbol"

    return name


# ============================================================
# EXTRACT FONTS
# ============================================================

def extract_fonts(pdf_path: str) -> Counter:
    """
    Mengambil semua font yang digunakan pada text layer PDF.
    """

    font_counter = Counter()

    doc = pymupdf.open(pdf_path)

    try:
        for page in doc:
            text_data = page.get_text("dict")

            for block in text_data.get("blocks", []):
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()

                        if not text:
                            continue

                        # Abaikan span yang hanya berisi simbol (subscript, centang, bullet)
                        if is_symbol_only(text):
                            continue

                        font_name = span.get("font", "Unknown")

                        normalized = normalize_font_name(font_name)

                        font_counter[normalized] += 1

    finally:
        doc.close()

    return font_counter


# ============================================================
# CHECK FONT
# ============================================================

def check_fonts(pdf_path: str) -> None:

    print("=" * 60)
    print("                   FONT CHECKER")
    print("=" * 60)

    print(f"File           : {pdf_path}")
    print(f"Expected Font  : {EXPECTED_FONT}")

    try:
        fonts = extract_fonts(pdf_path)

    except Exception as error:
        print(f"\nERROR: {error}")
        return

    print("\n" + "=" * 60)
    print("FONT YANG DITEMUKAN")
    print("=" * 60)

    if not fonts:
        print("Tidak ditemukan text layer pada PDF.")
        print("Font tidak dapat diverifikasi secara otomatis.")
        return

    for font, count in fonts.most_common():
        status = "PASS" if font == EXPECTED_FONT else "FAIL"

        print(
            f"{font:<25}"
            f"{count:>6} kali   "
            f"[{status}]"
        )

    # --------------------------------------------------------
    # Overall result
    # --------------------------------------------------------

    invalid_fonts = [
        font
        for font in fonts
        if font != EXPECTED_FONT
    ]

    print("\n" + "=" * 60)
    print("HASIL PEMERIKSAAN")
    print("=" * 60)

    if not invalid_fonts:
        print("✅ PASS")
        print("Semua font yang ditemukan sesuai aturan.")

    else:
        print("❌ FAIL")
        print("Ditemukan font selain Times New Roman:")

        for font in invalid_fonts:
            print(f"  - {font}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print(
            'Penggunaan:\n'
            'python font_checker.py "D:\\Folder\\nama_file.pdf"'
        )
        sys.exit(1)

    pdf_path = sys.argv[1]

    check_fonts(pdf_path)