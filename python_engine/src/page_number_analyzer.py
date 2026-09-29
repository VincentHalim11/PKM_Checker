"""
page_number_analyzer.py - ANALYZER, belum memberi PASS/FAIL.

Mencari nomor halaman (angka Arab atau Romawi) di zona atas/bawah halaman,
lalu melaporkan: teks, gaya, posisi, font, dan ukurannya.

Yang RESMI (panduan PKM 2026, dari rules.py PAGE_NUMBER):
  - font Times New Roman 12 pt
  - bagian awal/daftar isi: Romawi, kanan bawah
  - bagian inti/lampiran: Arab, kanan atas
Yang HEURISTIK (parameter teknis saya, bukan panduan):
  - "zona nomor halaman" = 3 cm teratas / 3 cm terbawah halaman
  - kolom kiri/tengah/kanan = sepertiga lebar halaman
  - teks dianggap nomor halaman jika HANYA angka Arab (1-3 digit) atau Romawi

Pakai: python page_number_analyzer.py "path.pdf"
Berdiri sendiri: hanya butuh pymupdf.
"""
import re
import sys
from collections import Counter

import pymupdf

ZONE_CM = 3.0                       # HEURISTIK
PT_PER_CM = 72 / 2.54
ARABIC = re.compile(r"^\d{1,3}$")
ROMAN = re.compile(r"^(?=[ivxlcdm]+$)m{0,3}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$",
                   re.IGNORECASE)


def style_of(text):
    if ARABIC.match(text):
        return "arabic"
    if ROMAN.match(text):
        return "roman"
    return None


def is_times(font):
    return "times" in font.lower().replace(" ", "")


def find_candidates(page):
    """Semua baris yang hanya berisi angka Arab/Romawi di zona atas/bawah."""
    w, h = page.rect.width, page.rect.height
    zone = ZONE_CM * PT_PER_CM
    found = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            text = "".join(s["text"] for s in spans).strip()
            st = style_of(text)
            if st is None:
                continue
            x0, y0, x1, y1 = line["bbox"]
            yc = (y0 + y1) / 2
            if yc < zone:
                vpos = "atas"
            elif yc > h - zone:
                vpos = "bawah"
            else:
                continue
            xc = (x0 + x1) / 2
            hpos = "kiri" if xc < w / 3 else ("kanan" if xc > 2 * w / 3 else "tengah")
            s0 = spans[0]
            found.append({
                "text": text, "style": st, "vpos": vpos, "hpos": hpos,
                "font": s0["font"], "size": round(s0["size"], 2),
                "right_gap_cm": round((w - x1) / PT_PER_CM, 2),
                "v_gap_cm": round((y0 if vpos == "atas" else h - y1) / PT_PER_CM, 2),
            })
    return found


def analyze(pdf_path):
    doc = pymupdf.open(pdf_path)
    print("=" * 74)
    print(f"File : {pdf_path}   ({len(doc)} halaman)")
    print(f"Zona : {ZONE_CM} cm teratas / terbawah (heuristik)")
    print("=" * 74)
    print(f"{'Hal':>3} | {'Nomor':<6} | {'Gaya':<6} | {'Posisi':<12} | "
          f"{'Font':<22} | {'Ukuran':>6} | jarak tepi")
    print("-" * 74)

    rows, missing, multi = [], [], []
    for pno, page in enumerate(doc, start=1):
        c = find_candidates(page)
        if not c:
            missing.append(pno)
            continue
        if len(c) > 1:
            multi.append(pno)
        for x in c:
            rows.append((pno, x))
            print(f"{pno:>3} | {x['text']:<6} | {x['style']:<6} | "
                  f"{x['vpos']+' '+x['hpos']:<12} | {x['font'][:22]:<22} | "
                  f"{x['size']:>6.2f} | kanan {x['right_gap_cm']} cm, "
                  f"{x['vpos']} {x['v_gap_cm']} cm")

    print("\n--- Ringkasan ---")
    print(f"Halaman dengan kandidat nomor : {len({p for p, _ in rows})} dari {len(doc)}")
    print(f"Halaman TANPA kandidat        : {missing if missing else '-'}")
    print("  (tidak ditemukan != tidak ada: cover memang bisa tanpa nomor,")
    print("   dan nomor yang berupa gambar tidak terbaca)")
    if multi:
        print(f"Halaman dengan >1 kandidat    : {multi}  (perlu dilihat manual)")
    print("\nGaya x posisi:")
    for (st, pos), n in Counter((x['style'], x['vpos'] + ' ' + x['hpos']) for _, x in rows).most_common():
        print(f"   {st:<7} {pos:<13}: {n} halaman")
    print("Font x ukuran:")
    for (f, s), n in Counter((x['font'], x['size']) for _, x in rows).most_common():
        tag = "TNR" if is_times(f) else "bukan TNR"
        print(f"   {f} {s:.2f} pt [{tag}]: {n} halaman")
    doc.close()


# ---------- Verdict (aturan dari rules.py; zona/kolom = heuristik) ----------
from rules import PAGE_NUMBER

SIZE_TOL = 0.1   # toleransi teknis untuk ukuran font
_POS = {"bottom_right": ("bawah", "kanan"), "top_right": ("atas", "kanan")}
EXPECTED_POS = {
    PAGE_NUMBER["preliminary_style"]: _POS[PAGE_NUMBER["preliminary_position"]],
    PAGE_NUMBER["main_style"]: _POS[PAGE_NUMBER["main_position"]],
}


def zone_other(page):
    """Teks non-nomor dan gambar di zona atas/bawah (untuk membedakan
    'tidak ada apa pun' dari 'ada sesuatu yang tidak dikenali')."""
    w, h = page.rect.width, page.rect.height
    zone = ZONE_CM * PT_PER_CM
    other = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            text = "".join(s["text"] for s in line["spans"]).strip()
            if not text or style_of(text):
                continue
            yc = (line["bbox"][1] + line["bbox"][3]) / 2
            if yc < zone or yc > h - zone:
                other.append(text[:30])
    images = 0
    try:
        for im in page.get_image_info():
            b = im["bbox"]
            if b[3] < zone or b[1] > h - zone:
                images += 1
    except Exception:
        pass
    return other, images


def evaluate(pdf_path):
    """Return {"font": {...}, "position": {...}}; tiap isi = status/message/details
    (format yang sama dengan checker lain di validator.py)."""
    doc = pymupdf.open(pdf_path)
    found, no_num, other_all, imgs = [], [], [], 0
    for pno, page in enumerate(doc, start=1):
        c = find_candidates(page)
        if c:
            found += [(pno, x) for x in c]
        else:
            no_num.append(pno)
            o, i = zone_other(page)
            other_all += o
            imgs += i
    n_pages = len(doc)
    doc.close()

    if not found:
        if other_all or imgs:
            msg = ("Tidak ada nomor halaman yang dikenali, tetapi ada "
                   f"{len(other_all)} teks dan {imgs} gambar di zona atas/bawah "
                   f"(contoh: {other_all[:3]}). Format nomor mungkin tidak umum.")
            st = "REVIEW"
        else:
            msg = ("Tidak ditemukan nomor halaman: zona atas/bawah kosong "
                   "(tanpa teks maupun gambar) di semua halaman.")
            st = "FAIL"
        r = {"status": st, "message": msg, "details": {"pages_without_number": no_num}}
        return {"font": r, "position": r}

    scope = (f"{len(found)} nomor terdeteksi; halaman tanpa nomor tidak dinilai: "
             f"{no_num if no_num else '-'}")

    # --- font ---
    want = PAGE_NUMBER["font_size_pt"]
    bad_font = [(p, x["font"], x["size"]) for p, x in found
                if not (is_times(x["font"]) and abs(x["size"] - want) <= SIZE_TOL)]
    if bad_font:
        combos = Counter((f, s) for _, f, s in bad_font).most_common()
        font_r = {"status": "FAIL",
                  "message": f"{len(bad_font)} dari {len(found)} nomor bukan "
                             f"{PAGE_NUMBER['font_family']} {want:.0f} pt: {combos}",
                  "details": {"bad": bad_font, "pages_without_number": no_num}}
    else:
        font_r = {"status": "PASS",
                  "message": f"Semua nomor terdeteksi {PAGE_NUMBER['font_family']} "
                             f"{want:.0f} pt. ({scope})",
                  "details": {"pages_without_number": no_num}}

    # --- posisi (gaya -> posisi yang diwajibkan) ---
    bad_pos = [(p, x["text"], x["style"], f"{x['vpos']} {x['hpos']}")
               for p, x in found
               if (x["vpos"], x["hpos"]) != EXPECTED_POS[x["style"]]]
    if bad_pos:
        combos = Counter((st, pos) for _, _, st, pos in bad_pos).most_common()
        pos_r = {"status": "FAIL",
                 "message": f"{len(bad_pos)} dari {len(found)} nomor di posisi yang "
                            f"salah untuk gayanya: {combos}",
                 "details": {"bad": bad_pos, "pages_without_number": no_num}}
    else:
        pos_r = {"status": "PASS",
                 "message": f"Semua nomor sesuai aturan posisi gaya masing-masing. ({scope})",
                 "details": {"pages_without_number": no_num}}
    return {"font": font_r, "position": pos_r}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Pemakaian: python page_number_analyzer.py "path.pdf"')
        sys.exit(1)
    analyze(sys.argv[1])
    res = evaluate(sys.argv[1])
    print("\n--- VERDICT ---")
    for k, v in res.items():
        print(f"[{k}] {v['status']}: {v['message']}")