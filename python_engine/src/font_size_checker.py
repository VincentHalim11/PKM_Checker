import sys
from collections import Counter

import pymupdf


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

def extract_font_sizes(pdf_path: str) -> Counter:
    """
    Mengambil semua ukuran font dari text layer PDF.
    Menghasilkan Counter berisi ukuran font dan jumlah kemunculannya.
    """

    size_counter = Counter()

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

                        size = round(
                            float(span.get("size", 0)),
                            2
                        )

                        size_counter[size] += 1

    finally:
        doc.close()

    return size_counter


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