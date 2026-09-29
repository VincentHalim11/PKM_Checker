"""
diagnostic.py - alat bantu (BUKAN validator, tidak memberi PASS/FAIL).
Menjawab dua pertanyaan pada PDF nyata:
  1. Font/ukuran "tidak sesuai" itu ada di halaman mana dan teks apa?
  2. Celah baris yang menyimpang dari 1,15 itu terletak di mana?

Pakai: python diagnostic.py "path.pdf"
Tidak mengubah file lain; hanya mengimpor konstanta dari line_spacing_checker.
"""
import sys
from collections import Counter, defaultdict

import pymupdf

from line_spacing_checker import (
    BODY_SIZE_MIN, BODY_SIZE_MAX, DIST_MIN, DIST_MAX,
    TNR_LINE_HEIGHT_FACTOR, RULE_RATIO, RATIO_TOL, is_times,
    extract_rows, merge_rows,
)

MAX_GAP_LINES = 60   # batas baris keluaran untuk daftar celah


def font_by_page(pdf_path):
    doc = pymupdf.open(pdf_path)
    print("=" * 70)
    print("FONT / UKURAN PER HALAMAN (selain Times New Roman 12 pt)")
    print("=" * 70)
    for pno, page in enumerate(doc, start=1):
        combos = defaultdict(lambda: [0, []])
        ok = 0
        for b in page.get_text("dict")["blocks"]:
            if b.get("type") != 0:
                continue
            for l in b["lines"]:
                for s in l["spans"]:
                    t = s["text"].strip()
                    if not t:
                        continue
                    fam = "TNR" if is_times(s["font"]) else s["font"]
                    size = round(s["size"], 2)
                    if fam == "TNR" and abs(size - 12.0) <= 0.1:
                        ok += 1
                        continue
                    c = combos[(fam, size)]
                    c[0] += 1
                    if len(c[1]) < 2:
                        c[1].append(t[:28])
        print(f"\nHalaman {pno}: {ok} span TNR 12 pt sesuai")
        for (fam, size), (n, samples) in sorted(combos.items(), key=lambda kv: -kv[1][0]):
            print(f"   {fam} {size:.2f} pt x{n}   contoh: {samples}")
    doc.close()


def off_gaps(pdf_path):
    doc = pymupdf.open(pdf_path)
    print("\n" + "=" * 70)
    print(f"CELAH BARIS YANG MENYIMPANG DARI {RULE_RATIO} (toleransi {RATIO_TOL})")
    print("(hanya pasangan dua baris body murni di luar tabel; sama dengan checker)")
    print("=" * 70)
    printed = 0
    total_off = 0
    hist = Counter()
    excluded = Counter()
    for pno, page in enumerate(doc, start=1):
        rows = extract_rows(page)
        for r in rows:
            if not r[2]:
                excluded[r[3]] += 1
        merged = merge_rows(rows)
        for (y1, s1, b1, t1), (y2, s2, b2, t2) in zip(merged, merged[1:]):
            if not (b1 and b2):
                continue
            d = y2 - y1
            if not (DIST_MIN <= d <= DIST_MAX):
                continue
            r = d / (((s1 + s2) / 2) * TNR_LINE_HEIGHT_FACTOR)
            if abs(r - RULE_RATIO) <= RATIO_TOL:
                continue
            total_off += 1
            hist[round(d, 1)] += 1
            skipped = abs(r - 2 * RULE_RATIO) <= 2 * RATIO_TOL
            if printed < MAX_GAP_LINES:
                printed += 1
                tag = " (dilewati evaluate)" if skipped else ""
                print(f"hal {pno:>2} | gap {d:5.1f} pt | rasio {r:.2f}{tag}")
                print(f"      atas : {t1[:55]!r}")
                print(f"      bawah: {t2[:55]!r}")
    print(f"\nTotal celah menyimpang: {total_off} (ditampilkan {printed})")
    print("Distribusi jarak menyimpang (pt):")
    for dist, cnt in hist.most_common(8):
        print(f"   {dist:5.1f} pt : {cnt} kali")
    print("\nBaris yang TIDAK dipakai sebagai bukti:")
    for reason, cnt in excluded.most_common():
        print(f"   {reason}: {cnt} baris")
    doc.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Pemakaian: python diagnostic.py "path.pdf"')
        sys.exit(1)
    font_by_page(sys.argv[1])
    off_gaps(sys.argv[1])