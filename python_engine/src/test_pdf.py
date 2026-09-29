import sys
from collections import Counter
import pymupdf


def points_to_cm(points: float) -> float:
    """Convert PDF points to centimeters."""
    return points * 2.54 / 72


def get_text_spans(page):
    """Get all non-empty text spans from a PDF page."""
    spans = []

    text_data = page.get_text("dict")

    for block in text_data.get("blocks", []):
        if "lines" not in block:
            continue

        for line in block["lines"]:
            for span in line.get("spans", []):
                text = span.get("text", "").strip()

                # Ignore completely empty text
                if not text:
                    continue

                spans.append(span)

    return spans


def analyze_pdf(pdf_path: str) -> None:
    try:
        doc = pymupdf.open(pdf_path)

        print("=" * 70)
        print("                  PKM PDF ANALYZER")
        print("=" * 70)

        print(f"File           : {pdf_path}")
        print(f"Jumlah halaman : {len(doc)}")

        # Store overall information
        all_fonts = Counter()
        all_font_sizes = Counter()
        page_sizes = Counter()

        print("\n" + "=" * 70)
        print("UKURAN HALAMAN")
        print("=" * 70)

        for page_number, page in enumerate(doc, start=1):
            width = page.rect.width
            height = page.rect.height

            width_cm = points_to_cm(width)
            height_cm = points_to_cm(height)

            page_size = (round(width, 2), round(height, 2))
            page_sizes[page_size] += 1

            print(
                f"Halaman {page_number:>2}: "
                f"{width:.2f} × {height:.2f} pt "
                f"({width_cm:.2f} × {height_cm:.2f} cm)"
            )

        print("\n" + "=" * 70)
        print("FONT YANG DITEMUKAN")
        print("=" * 70)

        # Analyze every page
        for page_number, page in enumerate(doc, start=1):
            spans = get_text_spans(page)

            for span in spans:
                font = span.get("font", "Unknown")
                size = span.get("size", 0)

                all_fonts[font] += 1
                all_font_sizes[round(size, 2)] += 1

        for font, count in all_fonts.most_common():
            print(f"{font:<30} {count:>6} kali")

        print("\n" + "=" * 70)
        print("UKURAN FONT YANG DITEMUKAN")
        print("=" * 70)

        for size, count in sorted(all_font_sizes.items()):
            print(f"{size:>7.2f} pt     {count:>6} kali")

        print("\n" + "=" * 70)
        print("RINGKASAN UKURAN HALAMAN")
        print("=" * 70)

        for (width, height), count in page_sizes.items():
            print(
                f"{width:.2f} × {height:.2f} pt "
                f"→ {count} halaman"
            )

        print("\n" + "=" * 70)
        print("ESTIMASI MARGIN")
        print("=" * 70)

        for page_number, page in enumerate(doc, start=1):
            spans = get_text_spans(page)

            if not spans:
                print(f"Halaman {page_number}: tidak ada teks")
                continue

            # Find the outermost text positions
            left = min(span["bbox"][0] for span in spans)
            top = min(span["bbox"][1] for span in spans)
            right = max(span["bbox"][2] for span in spans)
            bottom = max(span["bbox"][3] for span in spans)

            page_width = page.rect.width
            page_height = page.rect.height

            margin_left = left
            margin_top = top
            margin_right = page_width - right
            margin_bottom = page_height - bottom

            print(f"\nHalaman {page_number}")

            print(
                f"  Kiri  : {points_to_cm(margin_left):.2f} cm"
            )
            print(
                f"  Atas  : {points_to_cm(margin_top):.2f} cm"
            )
            print(
                f"  Kanan : {points_to_cm(margin_right):.2f} cm"
            )
            print(
                f"  Bawah : {points_to_cm(margin_bottom):.2f} cm"
            )

        doc.close()

        print("\n" + "=" * 70)
        print("ANALISIS SELESAI")
        print("=" * 70)

    except FileNotFoundError:
        print(f"\nERROR: File tidak ditemukan:")
        print(pdf_path)

    except Exception as error:
        print(f"\nERROR: {error}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Cara penggunaan:")
        print(
            'python test_pdf.py "D:\\Folder\\nama_file.pdf"'
        )
        sys.exit(1)

    analyze_pdf(sys.argv[1])