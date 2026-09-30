"""
section_analyzer.py - ANALYZER segmentasi bagian (BELUM memberi PASS/FAIL).

Menebak batas bagian proposal dari PENANDA TEKS, lalu melaporkan buktinya:
  sebelum Daftar Isi | Daftar Isi/awal | inti (Bab 1 - Daftar Pustaka) | lampiran

Yang RESMI (Panduan PKM 2026, bagian proposal):
  - Daftar Isi bernomor Romawi (mulai i), lalu inti bernomor Arab (mulai 1
    di Bab 1 Pendahuluan), lalu lampiran.
  - Inti = Bab 1 Pendahuluan sampai Daftar Pustaka, maksimum 10 halaman.
  - Tidak ada halaman sampul dan pengesahan pada berkas.
Yang HEURISTIK (parameter teknis saya, bukan panduan):
  - penanda = baris yang persis "DAFTAR ISI", "BAB 1/I [PENDAHULUAN]",
    "DAFTAR PUSTAKA", atau "LAMPIRAN [n]." di awal blok teks
  - halaman Daftar Isi dikenali dari baris bertitik pengarah (>= 3 baris)
  - halaman "tanpa teks terbaca" = <= 50 karakter selain nomor halaman

Akhir bagian inti dilaporkan sebagai RENTANG (minimum-maksimum), bukan satu
angka, karena halaman scan tidak punya teks yang bisa dibaca.

Pakai: python section_analyzer.py "path.pdf"
"""
import re
import sys

import pymupdf

from page_number_analyzer import find_candidates

LOW_TEXT_CHARS = 50     # HEURISTIK
TOC_DOT_LINES = 3       # HEURISTIK
MAX_HEADING_LEN = 100   # HEURISTIK
IMAGE_PAGE_RATIO = 0.4  # HEURISTIK: gambar >= 50% luas halaman + hampir tanpa teks = halaman scan

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


def _finish_structure(pages, found, core_start, di, scheme):
    """Bagian bersama GFT dan AI: Daftar Pustaka, Lampiran, rentang inti, jenis halaman."""
    n = len(pages)

    dp = lamp = None
    lamp_txt = None
    if core_start:
        dp, _ = _first_page(pages, core_start,
                            lambda up, first: bool(RE_DAFTAR_PUSTAKA.match(up)))
        lamp, lamp_txt = _first_page(pages, (dp if dp else core_start + 1),
                                     is_lampiran_heading)
    found["daftar_pustaka"] = dp
    found["lampiran"] = lamp
    found["lampiran_text"] = lamp_txt
    found["core_start"] = core_start

    low_pages = [p["no"] for p in pages if p["low_text"]]
    found["low_text_pages"] = low_pages

    lo = hi = None
    note = None
    if core_start and dp:
        if lamp and lamp > dp:
            upper = lamp - 1
        elif lamp == dp:
            upper = dp
            note = "Lampiran mulai di halaman yang sama dengan Daftar Pustaka"
        else:
            upper = n
        first_low = next((q for q in low_pages if q > dp), None)
        lower = (first_low - 1) if first_low else n
        hi = upper
        lo = max(dp, min(lower, upper))

        # Halaman scan (gambar penuh, nyaris tanpa teks) tepat setelah halaman bertulis
        # bukan lanjutan Daftar Pustaka (yang berupa teks) -> inti paling jauh berakhir
        # sebelum halaman scan pertama. Ini mempersempit rentang, sering menjadi pasti.
        first_scan = next(
            (p["no"] for p in pages if p["no"] > dp and p["scan_like"]), None
        )
        if first_scan is not None:
            hi = max(dp, min(hi, first_scan - 1))
            lo = min(lo, hi)
            if note is None and hi != upper:
                note = f"Halaman scan mulai di hal. {first_scan}; dianggap lampiran"
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
            elif scheme != "AI" and not p["toc_like"] and RE_BAB1.match(up):
                marks.append(raw)
            elif not p["toc_like"] and RE_DAFTAR_PUSTAKA.match(up):
                marks.append("DAFTAR PUSTAKA")
            elif not p["toc_like"] and is_lampiran_heading(up, first):
                marks.append(raw[:40])
        if p["low_text"]:
            marks.append("TANPA TEKS")
        p["marks"] = marks
    return found


def _find_daftar_isi(pages):
    for p in pages:
        if any(RE_DAFTAR_ISI.match(up) for up, _, _ in p["lines"]):
            return p["no"]
    return None


def _analyze_gft(pages):
    found = {}
    di = _find_daftar_isi(pages)
    found["daftar_isi"] = di

    core_start, bab_txt = _first_page(pages, (di + 1) if di else 1,
                                      lambda up, first: bool(RE_BAB1.match(up)))
    found["bab1"] = core_start
    found["bab1_text"] = bab_txt
    return _finish_structure(pages, found, core_start, di, "GFT")


def _analyze_ai(pages):
    """PKM-AI: tanpa Daftar Isi; bagian inti dimulai dari halaman judul (hal. 1)."""
    found = {}
    # Dicatat apa adanya: untuk AI, Daftar Isi TIDAK BOLEH ada (dinilai di validator).
    found["daftar_isi"] = _find_daftar_isi(pages)
    found["bab1"] = None
    found["bab1_text"] = None
    return _finish_structure(pages, found, 1, None, "AI")


def analyze_structure(pages, scheme="GFT"):
    if str(scheme).upper() == "AI":
        return _analyze_ai(pages)
    return _analyze_gft(pages)


def report(pdf_path, scheme="GFT"):
    pages = scan_pages(pdf_path)
    f = analyze_structure(pages, scheme)
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
    print(f"Lampiran pertama             : {'hal ' + str(f['lampiran']) + '  (' + f['lampiran_text'] + ')' if f['lampiran'] else 'tidak ditemukan'}")
    if f["core_start"] and f["core_lo"]:
        a, lo, hi = f["core_start"], f["core_lo"], f["core_hi"]
        if lo == hi:
            print(f"Bagian inti                  : hal {a}-{hi} = {hi - a + 1} halaman  (panduan: maksimum 10)")
        else:
            print(f"Bagian inti                  : berakhir di hal {lo}-{hi} "
                  f"-> {lo - a + 1} sampai {hi - a + 1} halaman  (panduan: maksimum 10)")
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