import sys
from collections import Counter

import pymupdf

from filters import is_symbol_only, is_page_number_text, is_caption_text


# ============================================================
# FONT SIZE RULE
# ============================================================

EXPECTED_FONT_SIZE = 12.0
TOLERANCE = 0.1


# ============================================================
# CHECK SIZE
# ============================================================

def is_expected_size(size: float) -> bool:
    """
    Mengecek apakah ukuran font sesuai dengan aturan.
    """
    return abs(size - EXPECTED_FONT_SIZE) <= TOLERANCE


# ============================================================
# EXTRACT FONT SIZES
# ============================================================

def extract_font_sizes_detailed(pdf_path: str):
    """
    Return (main_counter, caption_counter).

    - main_counter    : ukuran font teks biasa (yang dinilai ketat).
    - caption_counter : ukuran font caption Tabel/Gambar (hanya jadi peringatan).

    Dilewati: span simbol saja dan baris nomor halaman
    (nomor halaman dinilai oleh page_number_analyzer).
    """

    main_counter = Counter()
    caption_counter = Counter()

    doc = pymupdf.open(pdf_path)

    try:
        for page in doc:

            text_data = page.get_text("dict")

            for block in text_data.get("blocks", []):

                if "lines" not in block:
                    continue

                for line in block["lines"]:

                    line_text = "".join(
                        span.get("text", "")
                        for span in line.get("spans", [])
                    ).strip()

                    if not line_text:
                        continue

                    if is_page_number_text(line_text):
                        continue

                    target = (
                        caption_counter
                        if is_caption_text(line_text)
                        else main_counter
                    )

                    for span in line.get("spans", []):

                        text = span.get("text", "").strip()

                        if not text:
                            continue

                        if is_symbol_only(text):
                            continue

                        size = round(float(span.get("size", 0)), 2)

                        target[size] += 1

    finally:
        doc.close()

    return main_counter, caption_counter


def extract_font_sizes(pdf_path: str) -> Counter:
    """Kompatibel dengan kode lama: hanya ukuran font teks biasa."""
    main_counter, _ = extract_font_sizes_detailed(pdf_path)
    return main_counter


# ============================================================
# DISPLAY FONT SIZE CHECK
# ============================================================

def check_font_sizes(pdf_path: str) -> None:

    print("=" * 60)
    print("                 FONT SIZE CHECKER")
    print("=" * 60)

    print(f"File               : {pdf_path}")
    print(
        f"Expected Font Size : "
        f"{EXPECTED_FONT_SIZE:.2f} pt"
    )

    try:
        sizes = extract_font_sizes(pdf_path)

    except Exception as error:
        print(f"\nERROR: {error}")
        return

    print("\n" + "=" * 60)
    print("UKURAN FONT YANG DITEMUKAN")
    print("=" * 60)

    if not sizes:
        print("Tidak ditemukan text layer pada PDF.")
        print("Ukuran font tidak dapat diverifikasi.")
        return

    for size, count in sorted(sizes.items()):

        status = (
            "PASS"
            if is_expected_size(size)
            else "CHECK"
        )

        print(
            f"{size:>7.2f} pt"
            f"{count:>8} kali   "
            f"[{status}]"
        )

    print("\n" + "=" * 60)
    print("HASIL PEMERIKSAAN")
    print("=" * 60)

    invalid_sizes = [
        size
        for size in sizes
        if not is_expected_size(size)
    ]

    if not invalid_sizes:

        print("✅ PASS")
        print(
            "Semua ukuran font yang ditemukan "
            "adalah 12 pt."
        )

    else:

        print("⚠ CHECK")
        print(
            "Ditemukan ukuran font selain 12 pt:"
        )

        for size in invalid_sizes:

            print(
                f"  - {size:.2f} pt "
                f"({sizes[size]} kali)"
            )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            'Cara penggunaan:\n'
            'python font_size_checker.py '
            '"D:\\Folder\\nama_file.pdf"'
        )

        sys.exit(1)

    pdf_path = sys.argv[1]

    check_font_sizes(pdf_path)