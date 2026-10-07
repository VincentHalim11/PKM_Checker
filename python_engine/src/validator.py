import os
import re
import sys
import pymupdf
import json
import io
from contextlib import redirect_stdout, redirect_stderr
from statistics import median

from font_checker import extract_fonts, normalize_font_name
from font_size_checker import evaluate_font_sizes
from filters import is_page_number_text
from line_spacing_checker import evaluate as evaluate_line_spacing
from page_number_analyzer import evaluate as evaluate_page_number
from page_number_analyzer import evaluate_sequence as evaluate_page_number_sequence
from alignment_checker import evaluate as evaluate_alignment
from section_analyzer import scan_pages, analyze_structure

from rules import (
    PAGE,
    MARGIN,
    FONT,
    PAGE_NUMBER,
    SCHEMES,
    is_article_scheme,
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

def analyze_document_structure(pdf_path, scheme="GFT"):
    pages = scan_pages(pdf_path)
    structure = analyze_structure(pages,scheme,pdf_path)
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

def _describe_allowed(allowed):
    """Ringkasan aturan ukuran font untuk pesan."""
    def fmt(sizes):
        return "/".join(f"{x:g}" for x in sorted(sizes))
    parts = [f"isi {fmt(allowed['body'])} pt"]
    if allowed["title"] != allowed["body"]:
        parts.append(f"judul/penulis {fmt(allowed['title'])} pt")
    if allowed["abstract"] != allowed["body"]:
        parts.append(f"abstrak {fmt(allowed['abstract'])} pt")
    parts.append(f"caption {fmt(allowed['caption'])} pt")
    return ", ".join(parts)


def check_font_size(pdf_path, scheme="GFT"):
    r = evaluate_font_sizes(pdf_path, scheme)
    rule_text = _describe_allowed(r["allowed"])

    if r["invalid"] or r["caption_invalid"]:
        return {
            "status": "FAIL",
            "message": f"Ukuran font tidak sesuai aturan ({rule_text}).",
            "details": r["invalid"],
            "caption_details": r["caption_invalid"],
        }

    return {
        "status": "PASS",
        "message": f"Ukuran font sesuai aturan ({rule_text}).",
        "details": [],
        "caption_details": [],
    }


def _print_size_items(items):
    kind_label = {
        "body": "teks isi", "title": "judul/penulis", "abstract": "abstrak",
        "abstract_heading": "judul abstrak", "caption": "caption",
        "source": "baris Sumber", "table": "isi tabel",
    }
    for item in items:
        pages = item.get("pages", [])
        pages_txt = ", ".join(str(p) for p in pages[:12]) + (" ..." if len(pages) > 12 else "")
        print(
            f"- {item['size']:.2f} pt "
            f"({item['count']} kali, {kind_label.get(item.get('kind'), item.get('kind'))}) "
            f"hal. {pages_txt}"
        )
        for sample in item.get("samples", []):
            print(f"    contoh: \"{sample}\"")


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

# MAX_CORE_PAGES = 10

RE_FORBIDDEN_FRONT = re.compile(
    r"^(ABSTRAK|RINGKASAN|HALAMAN PENGESAHAN|LEMBAR PENGESAHAN)\.?$"
)


def check_front_matter_ai(pages, structure):
    """PKM-AI: tanpa sampul/pengesahan/Daftar Isi; halaman judul memuat Abstrak dan Abstract."""
    problems = []

    if structure.get("daftar_isi"):
        problems.append(
            f"Naskah PKM-AI tidak boleh memuat Daftar Isi (ditemukan di hal. {structure['daftar_isi']})"
        )

    limit = structure.get("daftar_pustaka") or len(pages) + 1
    for p in pages:
        if p["no"] >= limit:
            continue
        for up, _first, raw in p["lines"]:
            if re.match(r"^(HALAMAN|LEMBAR) PENGESAHAN\.?$", up):
                problems.append(f"halaman {p['no']} memuat judul \"{raw}\"")

    if problems:
        return {"status": "FAIL", "message": "; ".join(problems), "details": problems}

    head = [p for p in pages if p["no"] <= 3]
    has_id = any(up == "ABSTRAK" for p in head for up, _f, _r in p["lines"])
    has_en = any(up == "ABSTRACT" for p in head for up, _f, _r in p["lines"])

    if not (has_id and has_en):
        missing = [n for n, ok in (("ABSTRAK", has_id), ("ABSTRACT", has_en)) if not ok]
        return {
            "status": "REVIEW",
            "message": f"Judul {' dan '.join(missing)} tidak ditemukan di 3 halaman pertama.",
            "details": missing,
        }

    return {
        "status": "PASS",
        "message": "Tanpa sampul/pengesahan/Daftar Isi; Abstrak dan Abstract ditemukan.",
        "details": [],
    }


def check_front_matter(pages, structure, scheme="GFT"):
    """Proposal tidak boleh punya sampul, pengesahan, ringkasan, atau abstrak."""
    if is_article_scheme(scheme):
        return check_front_matter_ai(pages, structure)

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


def check_core_pages(structure, scheme):
    """
    Memeriksa jumlah halaman bagian inti berdasarkan skema PKM.
    """

    if scheme not in SCHEMES:
        return {
            "status": "REVIEW",
            "message": f"Skema PKM '{scheme}' tidak dikenali.",
            "details": {},
        }

    core_rules = SCHEMES[scheme]["core"]

    min_core_pages = core_rules["min_pages"]
    max_core_pages = core_rules["max_pages"]

    start = structure.get("core_start") or structure.get("bab1")
    lo = structure.get("core_lo")
    hi = structure.get("core_hi")

    if not start or not lo or not hi:
        return {
            "status": "REVIEW",
            "message": (
                "Bagian inti tidak dapat ditentukan "
                "(awal atau akhir bagian inti tidak ditemukan)."
            ),
            "details": {},
        }

    n_min = lo - start + 1     # kemungkinan paling sedikit
    n_max = hi - start + 1     # kemungkinan paling banyak

    details = {
        "min_pages": n_min,
        "max_pages": n_max,
        "rule_min": min_core_pages,
        "rule_max": max_core_pages,
        "physical_start": start,
        "scheme": scheme,
    }

    if n_min > max_core_pages:
        return {
            "status": "FAIL",
            "message": (
                f"Bagian inti {n_min} halaman (hal. fisik {start}-{lo}), "
                f"melebihi maksimum {max_core_pages}."
            ),
            "details": details,
        }

    if n_max < min_core_pages:
        return {
            "status": "FAIL",
            "message": (
                f"Bagian inti {n_max} halaman (hal. fisik {start}-{hi}), "
                f"kurang dari minimum {min_core_pages}."
            ),
            "details": details,
        }

    if n_min >= min_core_pages and n_max <= max_core_pages:
        shown = f"{n_max}" if n_min == n_max else f"{n_min}-{n_max}"
        return {
            "status": "PASS",
            "message": (
                f"Bagian inti {shown} halaman, sesuai batas "
                f"{min_core_pages}-{max_core_pages}."
            ),
            "details": details,
        }

    return {
        "status": "REVIEW",
        "message": (
            f"Bagian inti {n_min}-{n_max} halaman; akhirnya belum pasti "
            f"(batas {min_core_pages}-{max_core_pages})."
        ),
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

def validate_pdf(pdf_path, scheme):

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

    pages, structure = analyze_document_structure(pdf_path,scheme)

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

    font_size_result = check_font_size(pdf_path, scheme)

    # --------------------------------------------------------
    # MARGIN
    # --------------------------------------------------------

    margin_result = check_margins(pdf_path)

    # --------------------------------------------------------
    # LINE SPACING
    # --------------------------------------------------------

    core_range = None
    core_start = structure.get("core_start") or structure.get("bab1")
    if core_start and structure.get("core_hi"):
        core_range = (core_start, structure["core_hi"])

    line_spacing_result = check_line_spacing(pdf_path, core_range)

    # --------------------------------------------------------
    # ALIGNMENT (rata kiri-kanan)
    # --------------------------------------------------------

    alignment_result = evaluate_alignment(pdf_path, core_range, scheme)

    # --------------------------------------------------------
    # PAGE NUMBER
    # --------------------------------------------------------

    page_number_result = check_page_number(pdf_path)
    sequence_result = evaluate_page_number_sequence(pdf_path, structure)

    front_result = check_front_matter(pages, structure, scheme)
    core_result = check_core_pages(structure, scheme)
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
            f"{font_size_result['message']}"
        )
    elif font_size_result["status"] == "REVIEW":
        print(
            f"⚠️ Font Size       : "
            f"{font_size_result['message']}"
        )
    else:
        print(
            f"❌ Font Size       : "
            f"{font_size_result['message']}"
        )

    # Margin
    print_margin_result(margin_result)

    # Line spacing
    ls = line_spacing_result
    icon_map = {"PASS": "✅", "FAIL": "❌", "REVIEW": "⚠️"}
    icon = icon_map[ls["status"]]
    print()
    print(f"{icon} Line Spacing    : {ls['message']}")
    if ls["details"]["warning"]:
        print(f"   ⚠️ {ls['details']['warning']}")
    if ls["status"] != "PASS" and ls["details"]["off_pages"]:
        print(f"   Halaman menyimpang: {ls['details']['off_pages']}")

    # Alignment
    al = alignment_result
    print()
    print(f"{icon_map[al['status']]} Alignment       : {al['message']}")
    if al["status"] != "PASS" and al["details"].get("off_pages"):
        print(f"   Halaman menyimpang: {al['details']['off_pages']}")

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
    print(f"{icons[sequence_result['status']]} Nomor Hal. Urutan: {sequence_result['message']}")

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

        _print_size_items(font_size_result["details"])

    if font_size_result.get("caption_details"):

        print()
        print("-" * 70)
        print("UKURAN FONT CAPTION TABEL/GAMBAR TIDAK SESUAI")
        print("-" * 70)

        _print_size_items(font_size_result["caption_details"])

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
        alignment_result["status"],
        sequence_result["status"],
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

# ========================================================
# RETURN STRUCTURED RESULT
# ========================================================


    return {
    "status": final_status,
    "checks": {
        "page_size": page_result,
        "font": font_result,
        "font_size": font_size_result,
        "margin": margin_result,
        "line_spacing": line_spacing_result,
        "alignment": alignment_result,
        "page_number_font": page_number_result["font"],
        "page_number_position": page_number_result["position"],
        "page_number_sequence": sequence_result,
        "page_number_coverage": coverage_result,
        "front_matter": front_result,
        "core_pages": core_result,
    }
}


# ============================================================
# ERROR DALAM MODE --json
# ============================================================

def emit_json_error(message):
    """Mode --json selalu menghasilkan JSON di stdout, termasuk saat error.
    Format: {"status": "ERROR", "error": "...", "checks": {}}; kode keluar 2."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print(json.dumps(
        {"status": "ERROR", "error": message, "checks": {}},
        ensure_ascii=False,
        indent=2,
    ))
    sys.exit(2)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) < 2:
        pdf_path = input(
            "\nMasukkan path PDF: "
        ).strip()

        scheme = input(
            "Masukkan skema PKM (GFT/AI): "
        ).strip().upper()

    else:
        pdf_path = sys.argv[1]

        scheme = "GFT"

        if "--scheme" in sys.argv:
            index = sys.argv.index("--scheme")

            if index + 1 < len(sys.argv):
                scheme = sys.argv[index + 1].upper()

        # Dukung juga penulisan posisional: validator.py file.pdf AI
        elif len(sys.argv) >= 3 and not sys.argv[2].startswith("--"):
            scheme = sys.argv[2].upper()

    pdf_path = pdf_path.strip('"')
    json_mode = "--json" in sys.argv

    if scheme not in SCHEMES:
        message = (
            f"Skema PKM '{scheme}' tidak tersedia. "
            f"Skema tersedia: {', '.join(SCHEMES.keys())}"
        )

        if json_mode:
            emit_json_error(message)

        print()
        print(f"❌ {message.split('. Skema tersedia')[0]}.")
        print(
            f"Skema tersedia: {', '.join(SCHEMES.keys())}"
        )
        sys.exit(1)

    if json_mode and not os.path.isfile(pdf_path):
        emit_json_error(f"File PDF tidak ditemukan: {pdf_path}")

    if json_mode:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

        buffer = io.StringIO()

        try:
            with redirect_stdout(buffer), redirect_stderr(buffer):
                result = validate_pdf(pdf_path, scheme)
        except Exception as e:
            emit_json_error(
                f"Gagal memeriksa PDF ({type(e).__name__}): {e}"
            )

        # default=str: nilai yang tidak bisa diserialisasi (mis. set)
        # diubah menjadi teks, bukan membuat program crash.
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    else:
        validate_pdf(pdf_path, scheme)