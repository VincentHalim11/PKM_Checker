import os
import re
import sys
import pymupdf
import json
import io
import tempfile
from contextlib import redirect_stdout, redirect_stderr
from statistics import median

from font_checker import extract_fonts, normalize_font_name
from font_size_checker import evaluate_font_sizes
from filters import is_page_number_text, is_symbol_only
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
    """
    Memeriksa jenis font dan mengembalikan koordinat setiap span
    yang menggunakan font selain FONT["family"].

    Format lokasi kompatibel dengan overlay PDF Viewer:
    page, bbox, text, font.
    """
    fonts = extract_fonts(pdf_path)

    invalid_fonts = []

    for font_name, count in fonts.items():
        normalized = normalize_font_name(font_name)

        if normalized != FONT["family"]:
            invalid_fonts.append({
                "font": normalized,
                "count": count,
            })

    # Nama font yang benar-benar dinyatakan tidak sesuai oleh checker.
    invalid_font_names = {
        item["font"] for item in invalid_fonts
    }

    locations = []

    if invalid_font_names:
        doc = pymupdf.open(pdf_path)

        try:
            for page_number, page in enumerate(doc, start=1):
                page_dict = page.get_text("dict")

                for block in page_dict.get("blocks", []):
                    if block.get("type") != 0:
                        continue

                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if not text or is_symbol_only(text):
                                continue

                            raw_font = span.get("font", "Unknown")
                            normalized = normalize_font_name(raw_font)

                            # Gunakan aturan normalisasi yang sama dengan
                            # check_font() dan extract_fonts().
                            if normalized not in invalid_font_names:
                                continue

                            bbox = span.get("bbox")
                            if not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
                                continue

                            try:
                                coordinates = [
                                    round(float(value), 2)
                                    for value in bbox[:4]
                                ]
                            except (TypeError, ValueError):
                                continue

                            x0, y0, x1, y1 = coordinates
                            if x1 <= x0 or y1 <= y0:
                                continue

                            locations.append({
                                "page": page_number,
                                "bbox": coordinates,
                                "text": text,
                                "font": normalized,
                            })
        finally:
            doc.close()

    if invalid_fonts:
        return {
            "status": "FAIL",
            "message": "Ditemukan font yang tidak sesuai.",
            "details": invalid_fonts,
            "locations": locations,
        }

    return {
        "status": "PASS",
        "message": f"Semua font yang ditemukan sesuai {FONT['family']}.",
        "details": [],
        "locations": [],
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
        # --------------------------------------------
        # Periksa margin tabel
        # --------------------------------------------

        try:
            detected_tables = page.find_tables().tables
        except Exception as exc:
            # Jika deteksi tabel gagal, pemeriksaan margin
            # teks dan gambar tetap dilanjutkan.
            print(
                f"⚠️ Deteksi tabel gagal pada halaman "
                f"{page_number}: {exc}"
            )
            detected_tables = []

        for table in detected_tables:

            raw_bbox = table.bbox

            if not isinstance(raw_bbox, (list, tuple)) or len(raw_bbox) < 4:
                continue

            try:
                tx0, ty0, tx1, ty1 = [
                    float(value) for value in raw_bbox[:4]
                ]
            except (TypeError, ValueError):
                continue

            if tx1 <= tx0 or ty1 <= ty0:
                continue

            table_bbox = [
                round(tx0, 2),
                round(ty0, 2),
                round(tx1, 2),
                round(ty1, 2),
            ]

            table_boundaries = [
                (
                    "LEFT",
                    tx0 < left_boundary,
                    points_to_cm(tx0),
                    MARGIN["left_cm"],
                ),
                (
                    "RIGHT",
                    tx1 > right_boundary,
                    points_to_cm(page_width - tx1),
                    MARGIN["right_cm"],
                ),
                (
                    "TOP",
                    ty0 < top_boundary,
                    points_to_cm(ty0),
                    MARGIN["top_cm"],
                ),
                (
                    "BOTTOM",
                    ty1 > bottom_boundary,
                    points_to_cm(page_height - ty1),
                    MARGIN["bottom_cm"],
                ),
            ]

            for side, violated, position_cm, expected_cm in table_boundaries:

                if violated:
                    page_violations.append({
                        "type": side,
                        "object_type": "TABLE",
                        "text": "[Tabel]",
                        "bbox": table_bbox,
                        "position_cm": position_cm,
                        "expected_cm": expected_cm,
                    })

        page_dict = page.get_text("dict")

        # Hitung teks agar halaman scan bisa dibedakan.
        page_text = re.sub(r"\s+", "", page.get_text("text"))
        page_text_length = len(page_text)

        for block in page_dict.get("blocks", []):

            # Periksa blok gambar.
            if block.get("type") == 1:
                raw_bbox = block.get("bbox")

                if not isinstance(raw_bbox, (list, tuple)) or len(raw_bbox) < 4:
                    continue

                try:
                    ix0, iy0, ix1, iy1 = [
                        float(value) for value in raw_bbox[:4]
                    ]
                except (TypeError, ValueError):
                    continue

                if ix1 <= ix0 or iy1 <= iy0:
                    continue

                image_area = (ix1 - ix0) * (iy1 - iy0)
                page_area = float(page_width * page_height) or 1.0
                image_ratio = image_area / page_area

                # Hindari menandai halaman scan sebagai gambar biasa.
                if image_ratio >= 0.35 and page_text_length <= 50:
                    continue

                image_bbox = [
                    round(ix0, 2),
                    round(iy0, 2),
                    round(ix1, 2),
                    round(iy1, 2),
                ]
                # Abaikan potongan gambar yang hampir seluruhnya
                # berada di luar batas halaman PDF.
                try:
                    block_rect = pymupdf.Rect(
                        ix0, iy0, ix1, iy1
                    )

                    max_visible_ratio = None

                    for image_info in page.get_images(full=True):
                        xref = image_info[0]

                        for placement in page.get_image_rects(xref):
                            original_rect = pymupdf.Rect(placement)
                            clipped_rect = original_rect & page.rect

                            if (
                                clipped_rect.is_empty
                                or clipped_rect.get_area() <= 0
                            ):
                                continue

                            # Cocokkan posisi asli dengan bbox
                            # gambar yang sedang diperiksa.
                            same_bbox = all(
                                abs(a - b) <= 1.5
                                for a, b in zip(
                                    clipped_rect, block_rect
                                )
                            )

                            if not same_bbox:
                                continue

                            original_area = original_rect.get_area()

                            if original_area <= 0:
                                continue

                            visible_ratio = (
                                clipped_rect.get_area()
                                / original_area
                            )

                            if (
                                max_visible_ratio is None
                                or visible_ratio > max_visible_ratio
                            ):
                                max_visible_ratio = visible_ratio

                    # Abaikan gambar jika kurang dari 5% area
                    # penempatan aslinya terlihat pada halaman.
                    if (
                        max_visible_ratio is not None
                        and max_visible_ratio < 0.05
                    ):
                        continue

                except Exception:
                    # Jika pemeriksaan tambahan gagal, lanjutkan
                    # validasi gambar dengan logika sebelumnya.
                    pass

                boundaries = [
                    ("LEFT", ix0 < left_boundary, points_to_cm(ix0),
                    MARGIN["left_cm"]),
                    ("RIGHT", ix1 > right_boundary,
                    points_to_cm(page_width - ix1), MARGIN["right_cm"]),
                    ("TOP", iy0 < top_boundary, points_to_cm(iy0),
                    MARGIN["top_cm"]),
                    ("BOTTOM", iy1 > bottom_boundary,
                    points_to_cm(page_height - iy1), MARGIN["bottom_cm"]),
                ]

                for side, violated, position_cm, expected_cm in boundaries:
                    if violated:
                        page_violations.append({
                            "type": side,
                            "object_type": "IMAGE",
                            "text": "[Gambar]",
                            "bbox": image_bbox,
                            "position_cm": position_cm,
                            "expected_cm": expected_cm,
                        })

                continue

            # Bagian setelah ini tetap memeriksa blok teks.
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

                x0 = min(span["bbox"][0]for span in spans)
                y0 = min(span["bbox"][1]for span in spans)
                x1 = max(span["bbox"][2]for span in spans)
                y1 = max(span["bbox"][3]for span in spans)

                bbox = [
                    round(float(x0), 2),
                    round(float(y0), 2),
                    round(float(x1), 2),
                    round(float(y1), 2),
                ]

                # --------------------------------------------
                # LEFT
                # --------------------------------------------

                if x0 < left_boundary:

                    page_violations.append({
                        "type": "LEFT",
                        "text": text,
                        "bbox": bbox,
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


def export_highlighted_pdf(pdf_path, output_path, locations_json_path):
    """
    Membuat salinan PDF dengan highlight permanen dan satu halaman legenda.

    locations_json_path berisi:
    {
        "font_size": [...],
        "font": [...],
        "margin": [...]
    }
    """

    source_path = os.path.normcase(os.path.abspath(pdf_path))
    destination_path = os.path.normcase(os.path.abspath(output_path))

    if source_path == destination_path:
        raise ValueError("PDF hasil ekspor tidak boleh menimpa PDF asli.")

    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF sumber tidak ditemukan: {pdf_path}")

    with open(locations_json_path, "r", encoding="utf-8") as file:
        locations_data = json.load(file)

    if not isinstance(locations_data, dict):
        raise ValueError("Data lokasi highlight harus berbentuk JSON object.")

    # Warna RGB disamakan dengan warna di Flutter:
    # merah = Colors.red, biru = Colors.blue,
    # ungu = Colors.deepPurple.
    categories = [
        (
            "font_size",
            "Ukuran font",
            "Teks yang ukuran font-nya terdeteksi tidak sesuai aturan.",
            (244 / 255, 67 / 255, 54 / 255),
        ),
        (
            "font",
            "Jenis font",
            "Teks yang jenis font-nya terdeteksi tidak sesuai aturan.",
            (33 / 255, 150 / 255, 243 / 255),
        ),
        (
            "margin",
            "Margin",
            "Pelanggaran margin pada teks, gambar, atau tabel.",
            (103 / 255, 58 / 255, 183 / 255),
        ),
    ]

    doc = pymupdf.open(pdf_path)
    temp_output_path = None

    try:
        original_page_count = len(doc)
        counts = {}

        for category_index, (category, _title, _description, color) in enumerate(categories):
            locations = locations_data.get(category, [])

            if not isinstance(locations, list):
                locations = []

            # Hindari menggambar kotak yang identik berulang kali.
            seen = set()

            for location in locations:
                if not isinstance(location, dict):
                    continue

                try:
                    page_number = int(location["page"])
                    bbox = location["bbox"]

                    if not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
                        continue

                    coordinates = [float(value) for value in bbox[:4]]

                except (KeyError, TypeError, ValueError):
                    continue

                if page_number < 1 or page_number > original_page_count:
                    continue

                x0, y0, x1, y1 = coordinates

                if x1 <= x0 or y1 <= y0:
                    continue

                page = doc[page_number - 1]

                # Batasi highlight pada area halaman PDF.
                rect = pymupdf.Rect(x0, y0, x1, y1) & page.rect

                if rect.is_empty or rect.get_area() <= 0:
                    continue

                rect_key = (
                    page_number,
                    *(round(value, 2) for value in rect),
                )

                if rect_key in seen:
                    continue

                seen.add(rect_key)

                # Outline saja, tanpa isian transparan, agar warna kategori
                # tidak bercampur ketika dua error menandai area yang sama.
                # Jika bbox bertumpuk, setiap kategori memakai garis terpisah:
                # merah di luar, biru di tengah, dan ungu pada bbox asli.
                ring_offset = (len(categories) - 1 - category_index) * 1.5
                outline_rect = pymupdf.Rect(
                    rect.x0 - ring_offset,
                    rect.y0 - ring_offset,
                    rect.x1 + ring_offset,
                    rect.y1 + ring_offset,
                ) & page.rect

                if outline_rect.is_empty or outline_rect.get_area() <= 0:
                    continue

                page.draw_rect(
                    outline_rect,
                    color=color,
                    width=1.1,
                    stroke_opacity=1.0,
                    overlay=True,
                )

            counts[category] = len(seen)

        # ----------------------------------------------------
        # Tambahkan halaman legenda di akhir dokumen.
        # ----------------------------------------------------

        legend_page = doc.new_page(pno=0,width=595,height=842,)

        dark = (0.12, 0.12, 0.16)
        muted = (0.38, 0.38, 0.42)
        light_line = (0.82, 0.82, 0.85)

        legend_page.insert_text(
            (50, 58),
            "PKM 2026 CHECKER",
            fontname="hebo",
            fontsize=12,
            color=muted,
        )

        legend_page.draw_line(
            (50, 78),
            (545, 78),
            color=light_line,
            width=1,
        )

        legend_page.insert_text(
            (50, 123),
            "LEGENDA HASIL PEMERIKSAAN",
            fontname="hebo",
            fontsize=20,
            color=dark,
        )

        legend_page.insert_text(
            (50, 154),
            "Arti warna highlight pada halaman proposal berikutnya:",
            fontname="helv",
            fontsize=11,
            color=muted,
        )

        legend_page.insert_text(
            (50, 775),
            "PDF ini merupakan salinan hasil pemeriksaan. "
            "Dokumen sumber tidak diubah.",
            fontname="helv",
            fontsize=9,
            color=muted,
        )

        y_positions = [225, 325, 425]

        for (category, title, description, color), y in zip(
            categories, y_positions
        ):
            # Contoh di legenda mengikuti highlight: garis tepi tanpa isian.
            legend_page.draw_rect(
                pymupdf.Rect(55, y - 18, 83, y + 10),
                color=color,
                width=1.2,
                stroke_opacity=1.0,
                overlay=True,
            )

            legend_page.insert_text(
                (100, y - 2),
                title,
                fontname="hebo",
                fontsize=13,
                color=dark,
            )

            legend_page.insert_text(
                (100, y + 22),
                description,
                fontname="helv",
                fontsize=10,
                color=muted,
            )

            legend_page.insert_text(
                (100, y + 43),
                f"Jumlah lokasi highlight: {counts[category]}",
                fontname="helv",
                fontsize=9,
                color=muted,
            )

        legend_page.draw_line(
            (50, 750),
            (545, 750),
            color=light_line,
            width=1,
        )

        legend_page.insert_text(
            (50, 775),
            "PDF ini merupakan salinan hasil pemeriksaan. "
            "Dokumen sumber tidak diubah.",
            fontname="helv",
            fontsize=9,
            color=muted,
        )

        # Simpan ke file sementara terlebih dahulu, kemudian pindahkan
        # ke tujuan akhir setelah penyimpanan PDF berhasil.
        destination_directory = os.path.dirname(
            os.path.abspath(output_path)
        )
        os.makedirs(destination_directory, exist_ok=True)

        fd, temp_output_path = tempfile.mkstemp(
            prefix="pkm_highlight_",
            suffix=".pdf",
            dir=destination_directory,
        )
        os.close(fd)
        os.remove(temp_output_path)

        total_pages = len(doc)

        doc.save(
            temp_output_path,
            garbage=4,
            deflate=True,
        )

        doc.close()
        os.replace(temp_output_path, output_path)
        temp_output_path = None

        return {
            "status": "PASS",
            "output_path": os.path.abspath(output_path),
            "original_pages": original_page_count,
            "total_pages": total_pages,
            "legend_added": True,
            "highlights": counts,
        }

    finally:
        try:
            doc.close()
        except Exception:
            pass

        if temp_output_path and os.path.exists(temp_output_path):
            os.remove(temp_output_path)


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

    
    # Mode ekspor PDF dengan highlight dan halaman legenda.
    if "--export-highlight" in sys.argv:
        try:
            if len(sys.argv) < 2:
                raise ValueError("Path PDF sumber belum diberikan.")

            pdf_path = sys.argv[1].strip('"')

            def get_argument(flag):
                if flag not in sys.argv:
                    raise ValueError(f"Argumen {flag} wajib diberikan.")

                index = sys.argv.index(flag)

                if index + 1 >= len(sys.argv):
                    raise ValueError(f"Nilai untuk {flag} belum diberikan.")

                return sys.argv[index + 1].strip('"')

            result = export_highlighted_pdf(
                pdf_path=pdf_path,
                output_path=get_argument("--output"),
                locations_json_path=get_argument("--locations-json"),
            )

            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(0)

        except Exception as exc:
            print(json.dumps({
                "status": "ERROR",
                "error": str(exc),
            }, ensure_ascii=False))
            sys.exit(2)


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