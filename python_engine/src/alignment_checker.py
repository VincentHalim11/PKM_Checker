"""
Pemeriksa alignment paragraf (rata kiri-kanan / justify) pada bagian inti.

Prinsip: pada teks justify, setiap baris paragraf KECUALI baris terakhirnya
berakhir tepat di tepi kanan yang sama. Pada teks rata kiri, tepi kanan
bergerigi. Jadi yang diukur hanya "baris lanjutan paragraf" (baris yang masih
diikuti baris berikutnya dalam paragraf yang sama), lalu dihitung berapa
persen yang berakhir di tepi kanan yang sama.

Aturan alignment berasal dari rules.py (paragraph.alignment).
Angka ambang di bawah adalah PARAMETER TEKNIS, bukan aturan PKM.
"""
import sys
import collections

import pymupdf

from rules import MARGIN, FONT, PARAGRAPH, get_scheme

PT_PER_CM = 72 / 2.54

# ---------- Parameter teknis (BUKAN aturan resmi PKM) ----------
MIN_LINES = 15          # minimal baris lanjutan agar penilaian bermakna
FAIL_SHARE = 0.50       # di bawah ini -> FAIL (bukan justify)
PASS_SHARE = 0.70       # di atas ini  -> PASS
EDGE_TOL_PT = 2.0       # selisih x1 yang masih dianggap "tepi kanan sama"
MIN_PAGE_LINES = 5      # minimal baris agar sebuah halaman ikut ditandai
MIN_REACH = 0.5         # baris dihitung bila x1 melewati 50% lebar teks
                        # (membuang sel tabel sempit, daftar pendek, dsb.)
BODY_LO = FONT["size_pt"] - 1.5
BODY_HI = FONT["size_pt"] + 0.5


def expected_alignment(scheme):
    cfg = get_scheme(scheme).get("paragraph", PARAGRAPH)
    return cfg.get("alignment", PARAGRAPH["alignment"])


def continuation_right_edges(page):
    """x1 dari baris lanjutan paragraf pada satu halaman (area isi saja)."""
    w, h = page.rect.width, page.rect.height
    left = MARGIN["left_cm"] * PT_PER_CM
    right = w - MARGIN["right_cm"] * PT_PER_CM
    reach = left + MIN_REACH * (right - left)
    top = MARGIN["top_cm"] * PT_PER_CM
    bottom = h - MARGIN["bottom_cm"] * PT_PER_CM

    rows = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            x0, y0, x1, y1 = line["bbox"]
            if y0 < top or y1 > bottom:
                continue                      # header/footer/nomor halaman
            size = max(s["size"] for s in spans)
            pure = all(BODY_LO <= s["size"] <= BODY_HI for s in spans)
            text = "".join(s["text"] for s in spans).strip()
            rows.append((y0, x0, x1, size, pure, len(text)))
    rows.sort()

    edges = []
    for cur, nxt in zip(rows, rows[1:]):
        y0, x0, x1, size, pure, n = cur
        ny0, nx0, _nx1, _nsize, npure, nn = nxt
        dy = ny0 - y0
        continues = (
            pure and npure
            and 0 < dy <= 1.8 * size       # baris berikutnya rapat di bawahnya
            and nx0 <= x0 + 2              # mulai di margin kiri (bukan baris menjorok)
            and n >= 25 and nn >= 8
            and x1 >= reach
        )
        if continues:
            edges.append(x1)
    return edges


def _share_at_mode(xs):
    counts = collections.Counter(round(x) for x in xs)
    mode = max(counts, key=counts.get)
    share = sum(1 for x in xs if abs(x - mode) <= EDGE_TOL_PT) / len(xs)
    return mode, share


def evaluate(pdf_path, core_range=None, scheme="GFT"):
    """Return {status, message, details} (format standar validator)."""
    want = expected_alignment(scheme)
    if want != "justify":
        return {"status": "REVIEW",
                "message": f"Pemeriksaan alignment baru mendukung 'justify' "
                           f"(aturan skema: {want}).",
                "details": {}}

    doc = pymupdf.open(pdf_path)
    lo, hi = core_range if core_range else (1, len(doc))
    per_page, xs = {}, []
    for pno, page in enumerate(doc, start=1):
        if not (lo <= pno <= hi):
            continue
        e = continuation_right_edges(page)
        per_page[pno] = e
        xs += e
    doc.close()

    scope = f"hal. {lo}-{hi}"
    if len(xs) < MIN_LINES:
        return {"status": "REVIEW",
                "message": f"Baris paragraf terlalu sedikit ({len(xs)}) pada {scope} "
                           f"untuk menilai alignment.",
                "details": {"n_lines": len(xs)}}

    mode, share = _share_at_mode(xs)
    off_pages = []
    for pno, e in per_page.items():
        if len(e) >= MIN_PAGE_LINES:
            ok = sum(1 for x in e if abs(x - mode) <= EDGE_TOL_PT) / len(e)
            if ok < FAIL_SHARE:
                off_pages.append(pno)

    details = {"share": round(share, 3), "n_lines": len(xs),
               "edge_pt": mode, "off_pages": off_pages}
    base = f"{share:.0%} dari {len(xs)} baris lanjutan paragraf ({scope}) berakhir di tepi kanan yang sama"
    if share >= PASS_SHARE:
        return {"status": "PASS",
                "message": f"Paragraf rata kiri-kanan (justify): {base}.",
                "details": details}
    if share < FAIL_SHARE:
        return {"status": "FAIL",
                "message": f"Paragraf tidak rata kiri-kanan (justify): hanya {base}; "
                           f"tepi kanan bergerigi (kemungkinan rata kiri/kanan atau tengah).",
                "details": details}
    return {"status": "REVIEW",
            "message": f"Alignment tidak meyakinkan: {base}; periksa halaman yang ditandai.",
            "details": details}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Pemakaian: python alignment_checker.py "path.pdf" [skema]')
        sys.exit(1)
    sch = sys.argv[2].upper() if len(sys.argv) > 2 else "GFT"
    r = evaluate(sys.argv[1], None, sch)
    print(r["status"], "-", r["message"])
    if r["details"].get("off_pages"):
        print("Halaman menyimpang:", r["details"]["off_pages"])
