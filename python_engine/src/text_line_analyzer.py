import sys
import pymupdf


def classify_line(spans, page_width):
    """
    Mengklasifikasikan satu baris teks:
    HEADING / SUBHEADING / BODY
    """

    if not spans:
        return "EMPTY"

    text = " ".join(
        span.get("text", "").strip()
        for span in spans
        if span.get("text", "").strip()
    ).strip()

    if not text:
        return "EMPTY"

    sizes = [
        float(span.get("size", 0))
        for span in spans
    ]

    fonts = [
        span.get("font", "").lower()
        for span in spans
    ]

    # Semua span dianggap bold jika semuanya bold
    all_bold = all("bold" in font for font in fonts)

    # Gunakan ukuran font terbesar pada baris
    max_size = max(sizes)

    # Gabungkan bounding box semua span
    x0 = min(span["bbox"][0] for span in spans)
    y0 = min(span["bbox"][1] for span in spans)
    x1 = max(span["bbox"][2] for span in spans)
    y1 = max(span["bbox"][3] for span in spans)

    line_center = (x0 + x1) / 2
    page_center = page_width / 2

    center_distance = abs(line_center - page_center)

    # ========================================================
    # HEADING
    # ========================================================

    if (
        max_size > 12
        and all_bold
        and len(text) <= 60
        and center_distance <= 80
    ):
        return "HEADING"

    # ========================================================
    # SUBHEADING
    # ========================================================

    if (
        all_bold
        and len(text) <= 100
    ):
        return "SUBHEADING"

    # ========================================================
    # BODY
    # ========================================================

    return "BODY"


def analyze_pdf(pdf_path):
    try:
        doc = pymupdf.open(pdf_path)

    except Exception as error:
        print(f"ERROR membuka PDF: {error}")
        return

    print("=" * 70)
    print("                  TEXT LINE ANALYZER")
    print("=" * 70)

    print(f"File           : {pdf_path}")
    print(f"Jumlah halaman : {len(doc)}")

    total_lines = 0
    total_body = 0
    total_subheading = 0
    total_heading = 0

    try:

        for page_number, page in enumerate(doc, start=1):

            page_width = page.rect.width

            # ====================================================
            # KUMPULKAN SEMUA TEXT SPAN
            # ====================================================

            raw_lines = []

            text_data = page.get_text("dict")

            for block in text_data.get("blocks", []):

                if "lines" not in block:
                    continue

                for line in block["lines"]:

                    spans = [
                        span
                        for span in line.get("spans", [])
                        if span.get("text", "").strip()
                    ]

                    if not spans:
                        continue

                    x0 = min(span["bbox"][0] for span in spans)
                    y0 = min(span["bbox"][1] for span in spans)
                    x1 = max(span["bbox"][2] for span in spans)
                    y1 = max(span["bbox"][3] for span in spans)

                    text = " ".join(
                        span.get("text", "").strip()
                        for span in spans
                    ).strip()

                    if not text:
                        continue

                    raw_lines.append({
                        "text": text,
                        "spans": spans,
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1
                    })

            # ====================================================
            # GABUNGKAN BAGIAN YANG SEBENARNYA SATU BARIS
            # ====================================================

            merged_lines = []

            for current in raw_lines:

                merged = False

                for previous in reversed(merged_lines):

                    vertical_distance = abs(
                        current["y0"] - previous["y0"]
                    )

                    horizontal_gap = (
                        current["x0"] - previous["x1"]
                    )

                    # Kalau berada pada baris yang sama
                    # dan jaraknya dekat, gabungkan.
                    if (
                        vertical_distance <= 3
                        and 0 <= horizontal_gap <= 30
                    ):

                        previous["text"] = (
                            previous["text"]
                            + " "
                            + current["text"]
                        ).strip()

                        previous["spans"].extend(
                            current["spans"]
                        )

                        previous["x1"] = current["x1"]
                        previous["y1"] = max(
                            previous["y1"],
                            current["y1"]
                        )

                        merged = True
                        break

                if not merged:
                    merged_lines.append(current)

            # ====================================================
            # CLASSIFY
            # ====================================================

            for line in merged_lines:

                total_lines += 1

                classification = classify_line(
                    line["spans"],
                    page_width
                )

                if classification == "BODY":
                    total_body += 1

                elif classification == "SUBHEADING":

                    total_subheading += 1

                    print(
                        f"[SUBHEADING] "
                        f"Halaman {page_number}: "
                        f"{line['text']}"
                    )

                elif classification == "HEADING":

                    total_heading += 1

                    print(
                        f"[HEADING] "
                        f"Halaman {page_number}: "
                        f"{line['text']}"
                    )

        # ====================================================
        # SUMMARY
        # ====================================================

        print("\n" + "=" * 70)
        print("RINGKASAN")
        print("=" * 70)

        print(f"Total line       : {total_lines}")
        print(f"Body             : {total_body}")
        print(f"Subheading       : {total_subheading}")
        print(f"Heading          : {total_heading}")

        print("\n" + "=" * 70)
        print("ANALISIS SELESAI")
        print("=" * 70)

    finally:
        doc.close()


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            'Cara penggunaan:\n'
            'python text_line_analyzer.py '
            '"D:\\Folder\\nama_file.pdf"'
        )

        sys.exit(1)

    pdf_path = sys.argv[1]

    analyze_pdf(pdf_path)