import re
import sys
import pymupdf
from statistics import median

from font_checker import extract_fonts, normalize_font_name
from font_size_checker import extract_font_sizes_detailed, is_expected_size
from filters import is_page_number_text
from line_spacing_checker import evaluate as evaluate_line_spacing
from page_number_analyzer import evaluate as evaluate_page_number
from section_analyzer import scan_pages, analyze_structure

from rules import (
    PAGE,
    MARGIN,
    FONT,
    PAGE_NUMBER,
)


# ============================================================
# CONSTANT
# ============================================================

PT_PER_CM = 72 / 2.54


# ============================================================
# HELPER
# ============================================================

def cm_to_pt(cm):
    return cm * PT_PER_CM


def points_to_cm(pt):
    return pt / PT_PER_CM

# ============================================================
# DOCUMENT STRUCTURE
# ============================================================

def analyze_document_structure(pdf_path):
    """Mendapatkan struktur dokumen berdasarkan section_analyzer."""
    pages = scan_pages(pdf_path)
    structure = analyze_structure(pages)
    return pages, structure


# ============================================================
# PAGE SIZE
# ============================================================

def check_page_size(pdf_path):
    doc = pymupdf.open(pdf_path)

    expected_width = cm_to_pt(PAGE["width_cm"])
    expected_height = cm_to_pt(PAGE["height_cm"])

    tolerance = 2.0

    invalid_pages = []

    for page_number, page in enumerate(doc, start=1):
        width = page.rect.width
        height = page.rect.height

        width_ok = abs(width - expected_width) <= tolerance
        height_ok = abs(height - expected_height) <= tolerance

        if not (width_ok and height_ok):
            invalid_pages.append({
                "page": page_number,
                "width": width,
                "height": height,
            })

    doc.close()

    if invalid_pages:
        return {
            "status": "FAIL",
            "message": "Ditemukan halaman dengan ukuran selain A4.",
            "details": invalid_pages
        }

    return {
        "status": "PASS",
        "message": "Semua halaman berukuran A4.",
        "details": []
    }


# ============================================================
# FONT
# ============================================================

def check_font(pdf_path):
    fonts = extract_fonts(pdf_path)

    invalid_fonts = []

    for font_name in fonts:
        normalized = normalize_font_name(font_name)

        if normalized != FONT["family"]:
            invalid_fonts.append({
                "font": font_name,
                "count": fonts[font_name]
            })

    if invalid_fonts:
        return {
            "status": "FAIL",
            "message": "Ditemukan font yang tidak sesuai.",
            "details": invalid_fonts
        }

    return {
        "status": "PASS",
        "message": f"Semua font yang ditemukan sesuai {FONT['family']}.",
        "details": []
    }


# ============================================================
# FONT SIZE
# ============================================================

def check_font_size(pdf_path):
    sizes, caption_sizes = extract_font_sizes_detailed(pdf_path)

    invalid_sizes = [
        {"size": size, "count": count}
        for size, count in sizes.items()
        if not is_expected_size(size)
    ]

    invalid_captions = [
        {"size": size, "count": count}
        for size, count in caption_sizes.items()
        if not is_expected_size(size)
    ]

    # Aturan (konfirmasi staff): caption Tabel/Gambar juga WAJIB 12 pt.
    if invalid_sizes or invalid_captions:
        return {
            "status": "FAIL",
            "message": (
                f"Ditemukan ukuran font selain "
                f"{FONT['size_pt']:.2f} pt."
            ),
            "details": invalid_sizes,
            "caption_details": invalid_captions,
        }

    return {
        "status": "PASS",
        "message": (
            f"Semua ukuran font sesuai "
            f"{FONT['size_pt']:.2f} pt."
        ),
        "details": [],
        "caption_details": [],
    }


# ============================================================
# LINE SPACING
# ============================================================

def check_line_spacing(pdf_path, core_range=None):
    """
    Adapter: mengubah hasil evaluate() dari line_spacing_checker
    menjadi format standar validator: status / message / details.
    """
    r = evaluate_line_spacing(pdf_path, core_range)

    details = {
        "expected": r.get("expected"),
        "n_single": r.get("n_single"),
        "n_skipped_gaps": r.get("n_skipped_gaps"),
        "share_ok": r.get("share_ok"),
        "dominant_ratio": r.get("dominant_ratio"),
        "off_pages": r.get("off_pages", []),
        "warning": r.get("warning"),
    }

    return {
        "status": r["status"],
        "message": r["reason"],
        "details": details,
    }


# ============================================================
# PAGE NUMBER
# ============================================================

def check_page_number(pdf_path):
    """
    evaluate() dari page_number_analyzer sudah berformat standar
    (status / message / details), jadi cukup diteruskan.
    Return: {"font": {...}, "position": {...}}
    """
    return evaluate_page_number(pdf_path)


# ============================================================
# TEXT LINE EXTRACTION
# ============================================================

def extract_body_like_lines(page):
    """
    Mengambil baris teks yang kemungkinan besar merupakan
    baris isi/body proposal.

    Kita sengaja tidak menggunakan semua objek teks karena:
    - judul bisa mengganggu
    - nomor halaman bisa mengganggu
    - tabel bisa mengganggu
    - teks pendek bisa mengganggu
    """

    page_dict = page.get_text("dict")

    lines = []

    for block in page_dict.get("blocks", []):

        # Hanya block teks
        if block.get("type") != 0:
            continue

        for line in block.get("lines", []):

            spans = line.get("spans", [])

            if not spans:
                continue

            text = "".join(
                span.get("text", "")
                for span in spans
            ).strip()

            if not text:
                continue

            # Abaikan nomor halaman sederhana
            if re.fullmatch(r"\d+", text):
                continue

            # Hilangkan whitespace untuk menghitung karakter
            compact_text = re.sub(r"\s+", "", text)

            # Baris terlalu pendek biasanya bukan body
            if len(compact_text) < 20:
                continue

            x0 = min(span["bbox"][0] for span in spans)
            y0 = min(span["bbox"][1] for span in spans)
            x1 = max(span["bbox"][2] for span in spans)
            y1 = max(span["bbox"][3] for span in spans)

            width = x1 - x0

            # Baris yang terlalu pendek cenderung:
            # heading, nomor, caption, dll.
            if width < 150:
                continue

            lines.append({
                "text": text,
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1,
                "width": width,
            })

    return lines


# ============================================================
# MARGIN
# ============================================================

def check_margins(pdf_path):
    """
    Margin checker v2.

    Pemeriksaan dilakukan berdasarkan apakah ada konten teks
    yang masuk ke area margin minimum yang ditentukan.

    Catatan:
    PDF tidak selalu menyimpan nilai margin Word secara langsung,
    sehingga metode ini memeriksa pelanggaran batas margin,
    bukan membuktikan setting margin Word secara absolut.
    """

    doc = pymupdf.open(pdf_path)

    expected_left = cm_to_pt(MARGIN["left_cm"])
    expected_right = cm_to_pt(MARGIN["right_cm"])
    expected_top = cm_to_pt(MARGIN["top_cm"])
    expected_bottom = cm_to_pt(MARGIN["bottom_cm"])

    tolerance = cm_to_pt(MARGIN["tolerance_cm"])

    violations = []

    for page_number, page in enumerate(doc, start=1):

        page_width = page.rect.width
        page_height = page.rect.height

        left_boundary = expected_left - tolerance
        right_boundary = page_width - expected_right + tolerance
        top_boundary = expected_top - tolerance
        bottom_boundary = page_height - expected_bottom + tolerance

        page_violations = []

        page_dict = page.get_text("dict")

        for block in page_dict.get("blocks", []):

            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):

                spans = line.get("spans", [])

                if not spans:
                    continue

                text = "".join(
                    span.get("text", "")
                    for span in spans
                ).strip()

                if not text:
                    continue

                # Abaikan nomor halaman (Arab maupun Romawi)
                if is_page_number_text(text):
                    continue

                x0 = min(
                    span["bbox"][0]
                    for span in spans
                )

                y0 = min(
                    span["bbox"][1]
                    for span in spans
                )

                x1 = max(
                    span["bbox"][2]
                    for span in spans
                )

                y1 = max(
                    span["bbox"][3]
                    for span in spans
                )

                # --------------------------------------------
                # LEFT
                # --------------------------------------------

                if x0 < left_boundary:

                    page_violations.append({
                        "type": "LEFT",
                        "text": text,
                        "position_cm": points_to_cm(x0),
                        "expected_cm": MARGIN["left_cm"]
                    })

                # --------------------------------------------
                # RIGHT
                # --------------------------------------------

                if x1 > right_boundary:

                    actual_margin = points_to_cm(
                        page_width - x1
                    )

                    page_violations.append({
                        "type": "RIGHT",
                        "text": text,
                        "position_cm": actual_margin,
                        "expected_cm": MARGIN["right_cm"]
                    })

                # --------------------------------------------
                # TOP
                # --------------------------------------------

                if y0 < top_boundary:

                    page_violations.append({
                        "type": "TOP",
                        "text": text,
                        "position_cm": points_to_cm(y0),
                        "expected_cm": MARGIN["top_cm"]
                    })

                # --------------------------------------------
                # BOTTOM
                # --------------------------------------------

                if y1 > bottom_boundary:

                    actual_margin = points_to_cm(
                        page_height - y1
                    )

                    page_violations.append({
                        "type": "BOTTOM",
                        "text": text,
                        "position_cm": actual_margin,
                        "expected_cm": MARGIN["bottom_cm"]
                    })

        violations.extend(
            [
                {
                    "page": page_number,
                    **violation
                }
                for violation in page_violations
            ]
        )

    doc.close()

    # ========================================================
    # RESULT
    # ========================================================

    if violations:

        return {
            "status": "FAIL",
            "message": "Ditemukan konten yang memasuki area margin.",
            "details": violations
        }

    return {
        "status": "PASS",
        "message": "Tidak ditemukan konten yang melanggar batas margin.",
        "details": []
    }

# ============================================================
# STRUKTUR: HALAMAN AWAL, BAGIAN INTI, NOMOR HALAMAN
# ============================================================

MAX_CORE_PAGES = 10

RE_FORBIDDEN_FRONT = re.compile(
    r"^(ABSTRAK|RINGKASAN|HALAMAN PENGESAHAN|LEMBAR PENGESAHAN)\.?$"
)


def check_front_matter(pages, structure):
    """Proposal tidak boleh punya sampul, pengesahan, ringkasan, atau abstrak."""
    di = structure.get("daftar_isi")
    bab1 = structure.get("bab1")

    if not di:
        return {
            "status": "REVIEW",
            "message": "Daftar Isi tidak ditemukan; halaman awal tidak dapat dinilai.",
            "details": [],
        }

    problems = []

    if di > 1:
        problems.append(
            f"{di - 1} halaman sebelum Daftar Isi (sampul/pengesahan?): "
            f"halaman {list(range(1, di))}"
        )

    limit = bab1 if bab1 else di
    for p in pages:
        if p["no"] >= limit:
            continue
        for up, _first, raw in p["lines"]:
            if RE_FORBIDDEN_FRONT.match(up):
                problems.append(f"halaman {p['no']} memuat judul \"{raw}\"")

    if problems:
        return {
            "status": "FAIL",
            "message": "; ".join(problems),
            "details": problems,
        }

    return {
        "status": "PASS",
        "message": "Tidak ada sampul, pengesahan, ringkasan, atau abstrak.",
        "details": [],
    }


def check_core_pages(structure):
    """Bagian inti (Bab 1 sampai Daftar Pustaka) maksimum 10 halaman."""
    bab1 = structure.get("bab1")
    lo = structure.get("core_lo")
    hi = structure.get("core_hi")

    if not bab1 or not lo or not hi:
        return {
            "status": "REVIEW",
            "message": (
                "Bagian inti tidak dapat ditentukan "
                "(Bab 1 atau Daftar Pustaka tidak ditemukan)."
            ),
            "details": {},
        }

    n_min = lo - bab1 + 1
    n_max = hi - bab1 + 1
    details = {"min_pages": n_min, "max_pages": n_max}

    if n_min > MAX_CORE_PAGES:
        return {
            "status": "FAIL",
            "message": (
                f"Bagian inti {n_min} halaman (hal. fisik {bab1}-{lo}), "
                f"melebihi maksimum {MAX_CORE_PAGES}."
            ),
            "details": details,
        }

    if n_max > MAX_CORE_PAGES:
        return {
            "status": "REVIEW",
            "message": (
                f"Bagian inti {n_min}-{n_max} halaman; batas akhir belum pasti "
                f"(maksimum {MAX_CORE_PAGES})."
            ),
            "details": details,
        }

    return {
        "status": "PASS",
        "message": f"Bagian inti {n_max} halaman (maksimum {MAX_CORE_PAGES}).",
        "details": details,
    }


def check_page_number_coverage(page_number_result, structure):
    """Setiap halaman sampai akhir bagian inti wajib bernomor.
    Halaman lampiran tanpa nomor cukup REVIEW."""
    details = page_number_result["position"].get("details", {})
    missing = details.get("pages_without_number", []) if isinstance(details, dict) else []

    if not missing:
        return {
            "status": "PASS",
            "message": "Semua halaman memiliki nomor halaman.",
            "details": [],
        }

    limit = structure.get("core_hi")

    if limit:
        must = [p for p in missing if p <= limit]
        rest = [p for p in missing if p > limit]
    else:
        must, rest = [], list(missing)

    if must:
        return {
            "status": "FAIL",
            "message": f"Halaman tanpa nomor (sampai akhir bagian inti): {must}",
            "details": missing,
        }

    return {
        "status": "REVIEW",
        "message": f"Halaman tanpa nomor: {rest}; periksa apakah termasuk lampiran.",
        "details": missing,
    }


# ============================================================
# PRINT DOCUMENT STRUCTURE
# ============================================================

def print_document_structure(structure):
    
    pages, structure = analyze_document_structure(pdf_path)

    print()
    print("-" * 70)
    print("DOCUMENT STRUCTURE")
    print("-" * 70)

    if structure["daftar_isi"]:
        print(
            f"Daftar Isi        : halaman "
            f"{structure['daftar_isi']}"
        )
    else:
        print("Daftar Isi        : tidak ditemukan")

    if structure["bab1"]:
        print(
            f"Bab 1             : halaman "
            f"{structure['bab1']}"
        )
    else:
        print("Bab 1             : tidak ditemukan")

    if structure["daftar_pustaka"]:
        print(
            f"Daftar Pustaka    : halaman "
            f"{structure['daftar_pustaka']}"
        )
    else:
        print("Daftar Pustaka    : tidak ditemukan")

    if structure["lampiran"]:
        print(
            f"Lampiran          : halaman "
            f"{structure['lampiran']}"
        )
    else:
        print("Lampiran          : tidak ditemukan")

    if (
        structure["core_lo"] is not None
        and structure["core_hi"] is not None
    ):
        print(
            f"Bagian inti       : halaman "
            f"{structure['core_lo']}-"
            f"{structure['core_hi']}"
        )

# ============================================================
# PRINT MARGIN RESULT
# ============================================================

def print_margin_result(result):

    print()
    print("-" * 70)
    print("MARGIN")
    print("-" * 70)

    if result["status"] == "PASS":

        print(
            "✅ Left   : Tidak ada konten "
            "melewati batas 4 cm"
        )

        print(
            "✅ Right  : Tidak ada konten "
            "melewati batas 3 cm"
        )

        print(
            "✅ Top    : Tidak ada konten "
            "melewati batas 3 cm"
        )

        print(
            "✅ Bottom : Tidak ada konten "
            "melewati batas 3 cm"
        )

    else:

        print(
            f"⚠️ {result['message']}"
        )

        if result["details"]:

            print()

            for item in result["details"]:

                print(
                    f"❌ Page {item['page']} | "
                    f"{item['type']} | "
                    f"{item['text'][:60]}"
                )

    print()

    print(
        f"Margin Status : "
        f"{result['status']}"
    )
# ============================================================
# MAIN VALIDATOR
# ============================================================

def validate_pdf(pdf_path):

    doc = pymupdf.open(pdf_path)

    print("=" * 70)
    print("                     PKM 2026 VALIDATOR")
    print("=" * 70)

    print(f"File           : {pdf_path}")
    print(f"Jumlah halaman : {len(doc)}")

    doc.close()  
      
    # --------------------------------------------------------
    # DOCUMENT STRUCTURE
    # --------------------------------------------------------

    pages, structure = analyze_document_structure(pdf_path)

    # --------------------------------------------------------
    # PAGE SIZE
    # --------------------------------------------------------

    page_result = check_page_size(pdf_path)

    # --------------------------------------------------------
    # FONT
    # --------------------------------------------------------

    font_result = check_font(pdf_path)

    # --------------------------------------------------------
    # FONT SIZE
    # --------------------------------------------------------

    font_size_result = check_font_size(pdf_path)

    # --------------------------------------------------------
    # MARGIN
    # --------------------------------------------------------

    margin_result = check_margins(pdf_path)

    # --------------------------------------------------------
    # LINE SPACING
    # --------------------------------------------------------

    core_range = None
    if structure.get("bab1") and structure.get("core_hi"):
        core_range = (structure["bab1"], structure["core_hi"])

    line_spacing_result = check_line_spacing(pdf_path, core_range)

    # --------------------------------------------------------
    # PAGE NUMBER
    # --------------------------------------------------------

    page_number_result = check_page_number(pdf_path)

    front_result = check_front_matter(pages, structure)
    core_result = check_core_pages(structure)
    coverage_result = check_page_number_coverage(page_number_result, structure)

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("=" * 70)
    print("                    HASIL PEMERIKSAAN")
    print("=" * 70)

    # Page
    if page_result["status"] == "PASS":
        print("✅ Page Size       : A4")
    else:
        print("❌ Page Size       : Bukan A4")

    # Font
    if font_result["status"] == "PASS":
        print(
            f"✅ Font            : "
            f"{FONT['family']}"
        )
    else:
        print(
            "❌ Font            : "
            "Ditemukan font tidak sesuai"
        )

    # Font size
    if font_size_result["status"] == "PASS":
        print(
            f"✅ Font Size       : "
            f"{FONT['size_pt']:.2f} pt"
        )
    elif font_size_result["status"] == "REVIEW":
        print(
            f"⚠️ Font Size       : "
            f"{font_size_result['message']}"
        )
    else:
        print(
            f"❌ Font Size       : "
            f"Ditemukan ukuran selain "
            f"{FONT['size_pt']:.2f} pt"
        )

    # Margin
    print_margin_result(margin_result)

    # Line spacing
    ls = line_spacing_result
    icon = {"PASS": "✅", "FAIL": "❌", "REVIEW": "⚠️"}[ls["status"]]
    print()
    print(f"{icon} Line Spacing    : {ls['message']}")
    if ls["details"]["warning"]:
        print(f"   ⚠️ {ls['details']['warning']}")
    if ls["status"] != "PASS" and ls["details"]["off_pages"]:
        print(f"   Halaman menyimpang: {ls['details']['off_pages']}")

    # Page number
    pn_font = page_number_result["font"]
    pn_pos = page_number_result["position"]
    icons = {"PASS": "✅", "FAIL": "❌", "REVIEW": "⚠️"}
    print()
    if pn_font["message"] == pn_pos["message"]:
        print(f"{icons[pn_font['status']]} Nomor Halaman   : {pn_font['message']}")
    else:
        print(f"{icons[pn_font['status']]} Nomor Hal. Font  : {pn_font['message']}")
        print(f"{icons[pn_pos['status']]} Nomor Hal. Posisi: {pn_pos['message']}")

    print()
    print(f"{icons[coverage_result['status']]} Cakupan Nomor  : {coverage_result['message']}")
    print(f"{icons[front_result['status']]} Halaman Awal    : {front_result['message']}")
    print(f"{icons[core_result['status']]} Bagian Inti     : {core_result['message']}")

    # ========================================================
    # DETAILS FONT SIZE
    # ========================================================

    if font_size_result["details"]:

        print()
        print("-" * 70)
        print("UKURAN FONT TIDAK SESUAI")
        print("-" * 70)

        for item in font_size_result["details"]:
            print(
                f"- {item['size']:.2f} pt "
                f"({item['count']} kali)"
            )

    if font_size_result.get("caption_details"):

        print()
        print("-" * 70)
        print("UKURAN FONT CAPTION TABEL/GAMBAR TIDAK SESUAI")
        print("-" * 70)

        for item in font_size_result["caption_details"]:
            print(
                f"- {item['size']:.2f} pt "
                f"({item['count']} kali)"
            )

    # ========================================================
    # DETAILS FONT
    # ========================================================

    if font_result["details"]:

        print()
        print("-" * 70)
        print("FONT TIDAK SESUAI")
        print("-" * 70)

        for item in font_result["details"]:
            print(
                f"- {item['font']} "
                f"({item['count']} kali)"
            )

    # ========================================================
    # FINAL STATUS
    # ========================================================

    results = [
        page_result["status"],
        font_result["status"],
        font_size_result["status"],
        margin_result["status"],
        line_spacing_result["status"],
        page_number_result["font"]["status"],
        page_number_result["position"]["status"],
        front_result["status"],
        core_result["status"],
        coverage_result["status"],
    ]

    if "FAIL" in results:
        final_status = "FAIL"

    elif "REVIEW" in results:
        final_status = "REVIEW"

    else:
        final_status = "PASS"

    print()
    print("=" * 70)
    print("                      STATUS")
    print("=" * 70)

    if final_status == "PASS":
        print("✅ PASS")

    elif final_status == "FAIL":
        print("❌ FAIL")

    else:
        print("⚠️ REVIEW")

    print("=" * 70)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]

    else:
        pdf_path = input(
            "\nMasukkan path PDF: "
        ).strip()

    pdf_path = pdf_path.strip('"')

    validate_pdf(pdf_path)