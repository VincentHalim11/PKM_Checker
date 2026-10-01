import re
import shutil
import sys

import pymupdf

from page_number_analyzer import find_candidates
from rules import MAIN_SECTION, get_scheme, is_article_scheme

# OCR dipakai hanya sebagai fallback untuk halaman kandidat yang scan-like.
# Prioritaskan Tesseract dari PATH; pada Windows tanpa PATH, gunakan lokasi installer UB Mannheim.
TESSERACT_PATH = shutil.which("tesseract") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
OCR_SCALE = 2

LOW_TEXT_CHARS = 50     # HEURISTIK
TOC_DOT_LINES = 3       # HEURISTIK
MAX_HEADING_LEN = 100   # HEURISTIK
IMAGE_PAGE_RATIO = 0.4  # HEURISTIK: gambar >= 40% luas halaman + hampir tanpa teks = kandidat scan

DOT_LEADER = re.compile(r"(\.\s*){5,}")
NUM_ONLY = re.compile(r"\d{1,3}|[ivxIVX]{1,6}")
RE_DAFTAR_ISI = re.compile(r"^DAFTAR ISI\.?$")
RE_BAB1 = re.compile(r"^BAB\s*(1|I)\s*\.?(\s*PENDAHULUAN)?$")
RE_DAFTAR_PUSTAKA = re.compile(r"^(?:\d+\s*[\.\)]\s*)?DAFTAR PUSTAKA\.?$")
RE_LAMPIRAN_NUM = re.compile(r"^LAMPIRAN\s*\d+\s*[.:]")      # "Lampiran 3. Biodata ..."
RE_LAMPIRAN_BARE = re.compile(r"^LAMPIRAN\s*$")            # "LAMPIRAN" saja (wajib awal blok)


def normalize_text(text):
    """
    Membersihkan karakter tak terlihat / zero-width
    dan merapikan whitespace.
    """

    # Zero-width space
    text = text.replace("\u200b", "")
    # Zero-width non-joiner
    text = text.replace("\u200c", "")
    # Zero-width joiner
    text = text.replace("\u200d", "")
    # BOM
    text = text.replace("\ufeff", "")
    # Whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def scan_pages(pdf_path):
    """Satu lintasan: kumpulkan fakta per halaman."""
    doc = pymupdf.open(pdf_path)
    pages = []
    for pno, page in enumerate(doc, start=1):
        lines, chars, dots = [], 0, 0
        big_image = False
        page_area = float(page.rect.width * page.rect.height) or 1.0
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") == 1:
                bb = block.get("bbox", (0, 0, 0, 0))
                if (bb[2] - bb[0]) * (bb[3] - bb[1]) >= IMAGE_PAGE_RATIO * page_area:
                    big_image = True
                continue
            if block.get("type") != 0:
                continue
            first = True
            for line in block["lines"]:
                text = "".join(s["text"] for s in line["spans"])
                norm = normalize_text(text)
                if not norm:
                    continue
                if DOT_LEADER.search(norm):
                    dots += 1
                if not NUM_ONLY.fullmatch(norm):
                    chars += len(norm)
                lines.append((norm.upper(), first, norm))
                first = False
        cands = find_candidates(page)
        pages.append({
            "no": pno,
            "lines": lines,
            "chars": chars,
            "toc_like": dots >= TOC_DOT_LINES,
            "low_text": chars <= LOW_TEXT_CHARS,
            "scan_like": big_image and chars <= LOW_TEXT_CHARS,
            "label": cands[0]["text"] if cands else None,
        })
    doc.close()
    return pages


def is_lampiran_heading(up, first):
    return bool(RE_LAMPIRAN_NUM.match(up) or (first and RE_LAMPIRAN_BARE.match(up)))


def is_first_lampiran_heading(up, first):
    """Penanda khusus AWAL Lampiran: LAMPIRAN atau Lampiran 1, bukan Lampiran 2+."""
    return bool((first and RE_LAMPIRAN_BARE.match(up)) or re.match(r"^LAMPIRAN\s*1\s*[.:]?", up))


def _ocr_page_text(pdf_path, page_no):
    """OCR satu halaman fisik. Dipanggil hanya untuk kandidat scan-like."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return "", "pytesseract/Pillow tidak tersedia"

    try:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
        doc = pymupdf.open(pdf_path)
        try:
            page = doc[page_no - 1]
            pix = page.get_pixmap(
                matrix=pymupdf.Matrix(OCR_SCALE, OCR_SCALE),
                alpha=False,
            )
            img = Image.frombytes(
                "RGB",
                [pix.width, pix.height],
                pix.samples,
            )
            text = pytesseract.image_to_string(img, lang="eng")
            return text, None
        finally:
            doc.close()
    except Exception as exc:
        return "", f"OCR gagal di hal. {page_no}: {exc}"


def _ocr_is_lampiran_start(text):
    """Deteksi awal Lampiran dari hasil OCR tanpa menganggap Lampiran 2/3/4 sebagai awal."""
    lines = [
        re.sub(r"\s+", " ", line).strip().upper()
        for line in text.splitlines()
        if line.strip()
    ]

    has_bare_lampiran = any(line == "LAMPIRAN" for line in lines)
    has_lampiran_1 = any(
        re.match(r"^LAMPIRAN\s*1\s*[:.]?", line)
        for line in lines
    )

    return has_bare_lampiran or has_lampiran_1


def _first_page(pages, start, matcher):
    """(halaman, teks) pertama >= start yang punya baris judul cocok
    dan bukan halaman Daftar Isi (titik pengarah)."""
    for p in pages:
        if p["no"] < start or p["toc_like"]:
            continue
        for up, first, raw in p["lines"]:
            if len(raw) > MAX_HEADING_LEN:
                continue
            if matcher(up, first):
                return p["no"], raw
    return None, None


def _finish_structure(pages, found, core_start, di, scheme, pdf_path=None):
    """Bagian bersama GFT dan AI: Daftar Pustaka, Lampiran, rentang inti, jenis halaman."""
    n = len(pages)

    dp = lamp = None
    lamp_txt = None
    lamp_source = None
    ocr_checked_pages = []
    ocr_errors = []

    if core_start:
        dp, _ = _first_page(
            pages,
            core_start,
            lambda up, first: bool(RE_DAFTAR_PUSTAKA.match(up)),
        )

        # Prioritas 1: penanda teks biasa. Ini cepat dan tidak membutuhkan OCR.
        lamp, lamp_txt = _first_page(
            pages,
            (dp if dp else core_start + 1),
            is_first_lampiran_heading,
        )
        if lamp is not None:
            lamp_source = "teks"

        # Prioritas 2: OCR hanya untuk halaman scan-like setelah Daftar Pustaka.
        # Jangan gunakan scan-like sebagai bukti Lampiran; scan-like hanya pemicu OCR.
        if lamp is None and pdf_path and dp:
            for p in pages:
                if p["no"] <= dp or p["toc_like"] or not p["scan_like"]:
                    continue

                ocr_checked_pages.append(p["no"])
                p["ocr_checked"] = True
                ocr_text, ocr_error = _ocr_page_text(pdf_path, p["no"])
                if ocr_error:
                    ocr_errors.append(ocr_error)
                    continue

                if _ocr_is_lampiran_start(ocr_text):
                    lamp = p["no"]
                    lamp_txt = "LAMPIRAN (OCR)"
                    lamp_source = "OCR"
                    p["ocr_lampiran"] = True
                    p["ocr_marker"] = "LAMPIRAN / Lampiran 1"
                    break
                p["ocr_lampiran"] = False

    found["daftar_pustaka"] = dp
    found["lampiran"] = lamp
    found["lampiran_text"] = lamp_txt
    found["lampiran_source"] = lamp_source
    found["ocr_checked_pages"] = ocr_checked_pages
    found["ocr_errors"] = ocr_errors
    found["core_start"] = core_start

    low_pages = [p["no"] for p in pages if p["low_text"]]
    found["low_text_pages"] = low_pages

    lo = hi = None
    note = None
    if core_start and dp:
        if lamp and lamp > dp:
            # Ini batas yang kita inginkan: halaman tepat sebelum Lampiran adalah
            # halaman terakhir Bagian Inti. Tidak lagi memakai first_scan sebagai cut-off.
            upper = lamp - 1
            lo = hi = upper
        elif lamp == dp:
            upper = dp
            lo = hi = dp
            note = "Lampiran mulai di halaman yang sama dengan Daftar Pustaka"
        else:
            # Daftar Pustaka ditemukan, tetapi awal Lampiran belum dapat dipastikan.
            # Laporkan rentang agar validator tidak mengarang angka pasti.
            lo = dp
            hi = n
            note = "Awal Lampiran tidak ditemukan; akhir Bagian Inti belum dapat dipastikan"
    elif core_start and not dp:
        note = "Daftar Pustaka tidak ditemukan; akhir inti tidak dapat ditentukan"
    found["core_lo"], found["core_hi"], found["note"] = lo, hi, note
    found["span_to_lampiran"] = ((lamp - 1) if lamp else n) if core_start else None

    def kind(no):
        if core_start is None:
            return "?"
        if no < core_start:
            if di is None:
                return "sebelum inti"
            return "sebelum Daftar Isi" if no < di else "Daftar Isi/awal"
        if dp:
            if no <= lo:
                return "inti"
            if no <= hi:
                return "inti atau lampiran (belum pasti)"
            return "lampiran"
        if no <= found["span_to_lampiran"]:
            return "inti? (tanpa Daftar Pustaka)"
        return "lampiran"

    for p in pages:
        p["kind"] = kind(p["no"])
        marks = []
        if p["toc_like"]:
            marks.append("[titik pengarah]")
        for up, first, raw in p["lines"]:
            if len(raw) > MAX_HEADING_LEN:
                continue
            if RE_DAFTAR_ISI.match(up):
                marks.append("DAFTAR ISI")
            elif not is_article_scheme(scheme) and not p["toc_like"] and RE_BAB1.match(up):
                marks.append(raw)
            elif not p["toc_like"] and RE_DAFTAR_PUSTAKA.match(up):
                marks.append("DAFTAR PUSTAKA")
            elif not p["toc_like"] and is_lampiran_heading(up, first):
                marks.append(raw[:40])
        if p.get("ocr_lampiran"):
            marks.append("LAMPIRAN (OCR)")
        if p.get("ocr_checked"):
            marks.append("OCR diperiksa")
        if p["low_text"]:
            marks.append("TANPA TEKS")
        p["marks"] = marks
    return found


def _find_daftar_isi(pages):
    for p in pages:
        if any(RE_DAFTAR_ISI.match(up) for up, _, _ in p["lines"]):
            return p["no"]
    return None


def _analyze_gft(pages, pdf_path=None):
    found = {}
    di = _find_daftar_isi(pages)
    found["daftar_isi"] = di

    core_start, bab_txt = _first_page(pages, (di + 1) if di else 1,
                                      lambda up, first: bool(RE_BAB1.match(up)))
    found["bab1"] = core_start
    found["bab1_text"] = bab_txt
    return _finish_structure(pages, found, core_start, di, "GFT", pdf_path)


def _analyze_ai(pages, pdf_path=None):
    """PKM-AI: tanpa Daftar Isi; bagian inti dimulai dari halaman judul (hal. 1)."""
    found = {}
    # Dicatat apa adanya: untuk AI, Daftar Isi TIDAK BOLEH ada (dinilai di validator).
    found["daftar_isi"] = _find_daftar_isi(pages)
    found["bab1"] = None
    found["bab1_text"] = None
    return _finish_structure(pages, found, 1, None, "AI", pdf_path)


def analyze_structure(pages, scheme="GFT", pdf_path=None):
    if is_article_scheme(scheme):
        return _analyze_ai(pages, pdf_path)
    return _analyze_gft(pages, pdf_path)


def report(pdf_path, scheme="GFT"):
    scheme_key = str(scheme).upper()
    core_max = get_scheme(scheme_key).get("core", {}).get("max_pages")
    if core_max is None:
        core_max = MAIN_SECTION["maximum_core_pages"]
    pages = scan_pages(pdf_path)
    f = analyze_structure(pages, scheme, pdf_path)
    n = len(pages)
    print("=" * 84)
    print(f"File : {pdf_path}   ({n} halaman)")
    print("=" * 84)
    print(f"{'Hal':>3} | {'Jenis (dugaan)':<32} | {'Nomor':<6} | {'Teks':>5} | Penanda")
    print("-" * 84)
    for p in pages:
        print(f"{p['no']:>3} | {p['kind']:<32} | {str(p['label'] or '-'):<6} | "
              f"{p['chars']:>5} | {'; '.join(p['marks']) or '-'}")

    print("\n--- Ringkasan (dugaan dari penanda teks) ---")
    pre = [p["no"] for p in pages if p["kind"] in ("sebelum Daftar Isi", "sebelum Bab 1")]
    print(f"Halaman sebelum Daftar Isi   : {pre if pre else '-'}   "
          "(panduan: berkas tidak memuat sampul/pengesahan)")
    print(f"Daftar Isi                   : {'hal ' + str(f['daftar_isi']) if f['daftar_isi'] else 'tidak ditemukan'}")
    print(f"Bab 1 Pendahuluan            : {'hal ' + str(f['bab1']) + '  (' + f['bab1_text'] + ')' if f['bab1'] else 'tidak ditemukan'}")
    print(f"Daftar Pustaka               : {'hal ' + str(f['daftar_pustaka']) if f['daftar_pustaka'] else 'tidak ditemukan'}")
    print(f"Lampiran pertama             : {'hal ' + str(f['lampiran']) + '  (' + str(f['lampiran_text']) + ')' if f['lampiran'] else 'tidak ditemukan'}" + (f"  [sumber: {f['lampiran_source']}]" if f.get("lampiran_source") else ""))
    if f["core_start"] and f["core_lo"]:
        a, lo, hi = f["core_start"], f["core_lo"], f["core_hi"]
        if lo == hi:
            print(f"Bagian inti                  : hal {a}-{hi} = {hi - a + 1} halaman  (scheme {scheme_key}: maksimum {core_max})")
        else:
            print(f"Bagian inti                  : berakhir di hal {lo}-{hi} "
                  f"-> {lo - a + 1} sampai {hi - a + 1} halaman  (scheme {scheme_key}: maksimum {core_max})")
    elif f["core_start"]:
        s = f["span_to_lampiran"]
        print(f"Bagian inti                  : TIDAK DAPAT DITENTUKAN ({f['note']})")
        rng = pages[f['core_start'] - 1:s]
        unread = [p['no'] for p in rng if p['low_text']]
        print(f"   Awal inti sampai sebelum Lampiran pertama/akhir berkas: hal {f['core_start']}-{s} "
              f"= {s - f['core_start'] + 1} halaman, {len(unread)} di antaranya tanpa teks terbaca {unread if unread else ''}")
    else:
        print("Bagian inti                  : TIDAK DAPAT DITENTUKAN (Bab 1 tidak ditemukan)")
    if f["note"] and f["core_lo"]:
        print(f"Catatan                      : {f['note']}")
    if f.get("ocr_checked_pages"):
        print("Halaman kandidat yang di-OCR : " + str(f["ocr_checked_pages"]))
    if f.get("ocr_errors"):
        print("Peringatan OCR               : " + str(f["ocr_errors"]))
    low = f["low_text_pages"]
    print(f"Halaman tanpa teks terbaca   : {low if low else '-'}")
    for kind_name in ("sebelum Daftar Isi", "Daftar Isi/awal"):
        sel = [q for q in low if pages[q - 1]["kind"] == kind_name]
        if sel:
            print(f"   - di '{kind_name}': {sel}")
    core_low = [q for q in low if pages[q - 1]["kind"].startswith("inti")]
    if core_low:
        print(f"   - di/dekat inti  : {core_low}")
    print("\n(Analyzer: tidak ada PASS/FAIL. Periksa kolom Penanda untuk menilai apakah dugaan masuk akal.)")
    return pages, f


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Pemakaian: python section_analyzer.py "path.pdf"')
        sys.exit(1)
    report(sys.argv[1], sys.argv[2].upper() if len(sys.argv) > 2 else "GFT")