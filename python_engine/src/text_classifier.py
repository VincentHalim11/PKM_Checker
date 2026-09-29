import sys
from collections import Counter

import pymupdf


def classify_text(span, page_width):
    text = span.get("text", "").strip()
    font = span.get("font", "").lower()
    size = float(span.get("size", 0))
    bbox = span.get("bbox")

    if not text or not bbox:
        return "EMPTY"

    x0, y0, x1, y1 = bbox

    is_bold = "bold" in font
    text_length = len(text)

    text_center = (x0 + x1) / 2
    page_center = page_width / 2

    center_distance = abs(text_center - page_center)

    # Heading utama
    if (
        size > 12
        and is_bold
        and text_length <= 50
        and center_distance <= 80
    ):
        return "HEADING"

    # Subheading
    if is_bold and text_length <= 100:
        return "SUBHEADING"

    # Body
    return "BODY"


def analyze_pdf(pdf_path):
    try:
        doc = pymupdf.open(pdf_path)
    except Exception as error:
        print(f"ERROR membuka PDF: {error}")
        return

    print("=" * 70)
    print("                    TEXT CLASSIFIER")
    print("=" * 70)

    print(f"File           : {pdf_path}")
    print(f"Jumlah halaman : {len(doc)}")

    classification_counter = Counter()
    headings = []
    subheadings = []

    try:
        for page_number, page in enumerate(doc, start=1):

            page_width = page.rect.width
            text_data = page.get_text("dict")

            for block in text_data.get("blocks", []):

                if "lines" not in block:
                    continue

                for line in block["lines"]:

                    for span in line.get("spans", []):

                        text = span.get("text", "").strip()

                        if not text:
                            continue

                        classification = classify_text(
                            span,
                            page_width
                        )

                        classification_counter[classification] += 1

                        # Simpan heading
                        if classification == "HEADING":
                            headings.append({
                                "page": page_number,
                                "text": text,
                                "font": span.get("font"),
                                "size": span.get("size")
                            })

                        # Simpan subheading
                        elif classification == "SUBHEADING":
                            subheadings.append({
                                "page": page_number,
                                "text": text,
                                "font": span.get("font"),
                                "size": span.get("size")
                            })

        # ====================================================
        # SUMMARY
        # ====================================================

        print("\n" + "=" * 70)
        print("RINGKASAN KLASIFIKASI")
        print("=" * 70)

        print(
            f"BODY        : "
            f"{classification_counter['BODY']} text span"
        )

        print(
            f"SUBHEADING  : "
            f"{classification_counter['SUBHEADING']} text span"
        )

        print(
            f"HEADING     : "
            f"{classification_counter['HEADING']} text span"
        )

        # ====================================================
        # HEADINGS
        # ====================================================

        print("\n" + "=" * 70)
        print("HEADING TERDETEKSI")
        print("=" * 70)

        if headings:
            for item in headings:
                print(
                    f"[Halaman {item['page']}] "
                    f"{item['text']} "
                    f"({item['size']:.2f} pt)"
                )
        else:
            print("Tidak ada heading yang terdeteksi.")

        # ====================================================
        # SUBHEADINGS
        # ====================================================

        print("\n" + "=" * 70)
        print("SUBHEADING TERDETEKSI")
        print("=" * 70)

        if subheadings:
            for item in subheadings:
                print(
                    f"[Halaman {item['page']}] "
                    f"{item['text']} "
                    f"({item['size']:.2f} pt)"
                )
        else:
            print("Tidak ada subheading yang terdeteksi.")

        print("\n" + "=" * 70)
        print("ANALISIS SELESAI")
        print("=" * 70)

    finally:
        doc.close()


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print(
            'Cara penggunaan:\n'
            'python text_classifier.py '
            '"D:\\Folder\\nama_file.pdf"'
        )
        sys.exit(1)

    analyze_pdf(sys.argv[1])