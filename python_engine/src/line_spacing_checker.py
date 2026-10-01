import sys
import statistics
from collections import Counter

import pymupdf

from rules import FONT, PARAGRAPH

# ---------- Parameter (BUKAN aturan resmi PKM) ----------
BODY_SIZE_MIN = FONT["size_pt"] - 0.5   # kandidat body text: ukuran font isi (rules.py) -0.5
BODY_SIZE_MAX = FONT["size_pt"] + 0.5
DIST_MIN = 5.0                # filter jarak baseline antar baris (pt)
DIST_MAX = 40.0
TNR_LINE_HEIGHT_FACTOR = 1.149  # HEURISTIK: tinggi baris alami TNR / ukuran font
CANDIDATE_RATIOS = [1.0, 1.15, 1.5, 2.0]  # hanya untuk label pembanding


def is_times(font_name: str) -> bool:
    n = font_name.lower()
    return "times" in n or "timesnewroman" in n.replace(" ", "")


def get_table_bboxes(page):
    """Kotak tabel BERGARIS yang dikenali PyMuPDF (find_tables, strategi 'lines').
    Tabel tanpa garis tidak terdeteksi. Bila gagal, kembalikan daftar kosong."""
    try:
        return [pymupdf.Rect(t.bbox) for t in page.find_tables().tables]
    except Exception:
        return []


def extract_rows(page):
    """
    Ambil semua baris teks pada satu halaman.
    Return list of (y, size, is_body, reason, text, asc_desc).

    Sebuah baris dihitung body HANYA bila:
      - SEMUA span-nya Times New Roman berukuran 11.5-12.5 pt
        (baris dengan nomor 14 pt, bullet Symbol, dsb. tidak murni), dan
      - pusat baris tidak berada di dalam tabel bergaris.
    Alasannya: tinggi baris Word mengikuti glyph terbesar pada baris itu,
    jadi baris tidak murni menggeser jarak dan bukan bukti spasi 1,15.
    """
    tables = get_table_bboxes(page)
    rows = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            main = max(spans, key=lambda s: len(s["text"].strip()))
            x0, y0, x1, y1 = line["bbox"]
            center = pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2)

            if any(center in r for r in tables):
                is_body, reason = False, "tabel"
            elif all(BODY_SIZE_MIN <= s["size"] <= BODY_SIZE_MAX
                     and is_times(s["font"]) for s in spans):
                is_body, reason = True, "body"
            else:
                is_body, reason = False, "font/ukuran campuran atau lain"

            ad = None
            if is_body and "ascender" in main and "descender" in main:
                ad = main["ascender"] - main["descender"]
            text = "".join(s["text"] for s in spans).strip()
            rows.append((main["origin"][1], main["size"], is_body, reason, text, ad))
    rows.sort(key=lambda r: r[0])
    return rows


def merge_rows(rows):
    """Gabungkan fragmen di baris visual yang sama (selisih y < 1 pt).
    Return list of (y, size, is_body, text). Dianggap body hanya bila semua fragmen body."""
    merged = []
    for y, size, is_body, _reason, text, _ad in rows:
        if merged and abs(y - merged[-1][0]) < 1.0:
            py, ps, pb, pt = merged[-1]
            merged[-1] = (py, ps, pb and is_body, pt + " " + text)
        else:
            merged.append((y, size, is_body, text))
    return merged


def collect_observations(pdf_path: str, page_range=None):
    """page_range = (halaman_awal, halaman_akhir) 1-based, inklusif. None = semua halaman."""
    doc = pymupdf.open(pdf_path)
    total_lines = 0
    body_candidates = 0
    observations = []      # (page_no, distance_pt, font_size)
    asc_desc = []

    for page_index, page in enumerate(doc, start=1):
        if page_range and not (page_range[0] <= page_index <= page_range[1]):
            continue
        rows = extract_rows(page)
        total_lines += len(rows)
        for _y, _s, is_body, _r, _t, ad in rows:
            if is_body:
                body_candidates += 1
                if ad is not None:
                    asc_desc.append(ad)

        merged = merge_rows(rows)
        # jarak hanya dihitung jika DUA baris berurutan sama-sama body
        for (y1, s1, b1, _), (y2, s2, b2, _) in zip(merged, merged[1:]):
            if b1 and b2:
                d = y2 - y1
                if DIST_MIN <= d <= DIST_MAX:
                    observations.append((page_index, d, (s1 + s2) / 2))

    doc.close()
    return total_lines, body_candidates, observations, asc_desc


def nearest_ratio_label(ratio: float) -> str:
    best = min(CANDIDATE_RATIOS, key=lambda r: abs(r - ratio))
    return f"paling dekat ke {best:.2f} (selisih {abs(best - ratio):.3f})"


def analyze(pdf_path: str):
    total, body, obs, asc_desc = collect_observations(pdf_path)

    print("=" * 60)
    print(f"File                : {pdf_path}")
    print(f"Total text lines    : {total}")
    print(f"Body candidates     : {body}   (TNR, {BODY_SIZE_MIN}-{BODY_SIZE_MAX} pt)")
    print(f"Observations        : {len(obs)}   (jarak {DIST_MIN}-{DIST_MAX} pt)")

    if not obs:
        print("\nTidak ada observasi. Analyzer tidak bisa menyimpulkan apa pun.")
        return

    distances = [d for _, d, _ in obs]
    sizes = [s for _, _, s in obs]
    avg_size = statistics.mean(sizes)

    hist = Counter(round(d, 1) for d in distances)
    dominant, dom_count = hist.most_common(1)[0]
    median_d = statistics.median(distances)

    print("\n--- Distribusi jarak baseline (pt) ---")
    for dist, cnt in hist.most_common(8):
        print(f"  {dist:6.1f} pt : {cnt} kali ({cnt / len(distances) * 100:.1f}%)")

    print(f"\nDominan (modus)     : {dominant:.1f} pt")
    print(f"Median              : {median_d:.2f} pt")
    print(f"Rata-rata font size : {avg_size:.2f} pt")

    print("\n--- Estimasi rasio (HEURISTIK, bukan aturan resmi) ---")
    r_naive = dominant / avg_size
    r_tnr = dominant / (avg_size * TNR_LINE_HEIGHT_FACTOR)
    print(f"jarak / font size                  = {r_naive:.3f}  (naif, hanya info)")
    print(f"jarak / (font size x {TNR_LINE_HEIGHT_FACTOR})     = {r_tnr:.3f}  -> {nearest_ratio_label(r_tnr)}")

    if asc_desc:
        m = statistics.mean(asc_desc)
        print(f"\nMetrik font dari PDF: (ascender - descender) rata-rata = {m:.3f} em")
        print("  (catatan: ini biasanya belum termasuk line gap, jadi bisa lebih kecil dari 1.149)")

    print("\n--- Nilai jarak yang DIHARAPKAN untuk font %.1f pt (heuristik) ---" % avg_size)
    for r in CANDIDATE_RATIOS:
        print(f"  spasi {r:.2f} -> {avg_size * TNR_LINE_HEIGHT_FACTOR * r:.2f} pt")

    print("\n--- Median jarak per halaman (celah tunggal; celah ~2x dihitung terpisah) ---")
    pages = sorted({p for p, _, _ in obs})
    for p in pages:
        dp = [(d, sz) for pp, d, sz in obs if pp == p]
        single = [d for d, sz in dp
                  if abs(d / (sz * TNR_LINE_HEIGHT_FACTOR) - 2 * RULE_RATIO) > 2 * RATIO_TOL]
        dbl = len(dp) - len(single)
        med = f"{statistics.median(single):.2f} pt" if single else "-"
        print(f"  Halaman {p:>3}: median {med}  ({len(single)} tunggal, {dbl} celah ~2x)")


# ---------- Verdict (parameter teknis, BUKAN aturan panduan) ----------
RULE_RATIO = PARAGRAPH["line_spacing"]   # ATURAN RESMI PKM (dari rules.py)
RATIO_TOL = 0.05       # toleransi teknis
PASS_SHARE = 0.90      # minimal porsi celah yang sesuai
MIN_OBS = 15           # minimal bukti
SKIP_WARN_SHARE = 0.10 # peringatan bila celah "2x" melebihi porsi ini


DOMINANT_BUCKET = 0.05   # lebar kelompok untuk mencari rasio dominan
PAR_GAP_MARGIN = 0.15    # celah > dominan + margin = jarak antar paragraf / heading (bukan spasi baris)


def judge_ratios(ratios) -> dict:
    """
    Fungsi murni (mudah dites). ratios = list of (halaman, rasio).

    Logika:
      1. Cari rasio DOMINAN (modus) di halaman yang dinilai.
      2. Dominan jauh dari 1,15 (mis. 1,0 / 1,5 / 2,0)  -> FAIL.
      3. Dominan ~1,15 -> buang celah besar (antar paragraf/heading),
         lalu hitung porsi celah dalam-paragraf yang sesuai 1,15.
         >= 90% PASS, selain itu REVIEW (bukan FAIL, karena bisa jadi
         tabel/rumus/campuran font yang lolos filter).
    """
    result = {
        "rule": "line_spacing",
        "expected": RULE_RATIO,
        "n_single": 0,
        "n_skipped_gaps": 0,
        "share_ok": None,
        "dominant_ratio": None,
        "off_pages": [],
        "warning": None,
    }

    if len(ratios) < MIN_OBS:
        result.update(status="REVIEW",
                      reason=f"Bukti tidak cukup ({len(ratios)} < {MIN_OBS} celah baris)")
        return result

    def bucket(r):
        return round(round(r / DOMINANT_BUCKET) * DOMINANT_BUCKET, 2)

    dominant = Counter(bucket(r) for _, r in ratios).most_common(1)[0][0]
    result["dominant_ratio"] = dominant

    in_par = [(p, r) for p, r in ratios if r <= dominant + PAR_GAP_MARGIN]
    result["n_single"] = len(in_par)
    result["n_skipped_gaps"] = len(ratios) - len(in_par)

    if abs(dominant - RULE_RATIO) > RATIO_TOL + 1e-9:
        bad_pages = sorted({p for p, r in in_par if abs(r - RULE_RATIO) > RATIO_TOL})
        result.update(status="FAIL", off_pages=bad_pages,
                      reason=f"Spasi baris dominan {dominant:.2f}, seharusnya {RULE_RATIO}")
        return result

    ok = [(p, r) for p, r in in_par if abs(r - RULE_RATIO) <= RATIO_TOL]
    bad = [(p, r) for p, r in in_par if abs(r - RULE_RATIO) > RATIO_TOL]
    share = len(ok) / len(in_par)
    result.update(share_ok=share, off_pages=sorted({p for p, _ in bad}))

    if share >= PASS_SHARE:
        result.update(status="PASS",
                      reason=f"{share:.0%} celah baris dalam paragraf sesuai 1,15 (±{RATIO_TOL})")
    else:
        result.update(status="REVIEW",
                      reason=(f"Spasi dominan 1,15 tetapi hanya {share:.0%} celah baris "
                              "sesuai; periksa halaman yang ditandai"))
    return result


def evaluate(pdf_path: str, page_range=None) -> dict:
    """page_range = (awal, akhir) halaman fisik 1-based. Sebaiknya bagian inti saja
    (Bab 1 sampai Daftar Pustaka), karena daftar isi/tabel/lampiran bukan teks paragraf."""
    _, _, obs, _ = collect_observations(pdf_path, page_range)
    ratios = [(p, d / (s * TNR_LINE_HEIGHT_FACTOR)) for p, d, s in obs]
    return judge_ratios(ratios)


def show_double_gaps(pdf_path: str):
    """Diagnostik: pasangan baris body murni (di luar tabel) dengan jarak ~2x
    spasi aturan. Kriterianya sama dengan evaluate(), jadi jumlahnya harus
    sama dengan n_skipped_gaps."""
    doc = pymupdf.open(pdf_path)
    found = 0
    for pno, page in enumerate(doc, start=1):
        merged = merge_rows(extract_rows(page))
        for (y1, s1, b1, t1), (y2, s2, b2, t2) in zip(merged, merged[1:]):
            if not (b1 and b2):
                continue
            d = y2 - y1
            if not (DIST_MIN <= d <= DIST_MAX):
                continue
            r = d / (((s1 + s2) / 2) * TNR_LINE_HEIGHT_FACTOR)
            if abs(r - 2 * RULE_RATIO) <= 2 * RATIO_TOL:
                found += 1
                print(f"hal {pno}: gap {d:.1f} pt")
                print(f"   atas : {t1[:60]!r}")
                print(f"   bawah: {t2[:60]!r}")
    print(f"Total celah ~2x: {found}" if found else "(tidak ada celah ~2x ditemukan)")
    doc.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Pemakaian: python line_spacing_checker.py "path.pdf"')
        sys.exit(1)
    analyze(sys.argv[1])
    print("\n--- VERDICT ---")
    print(evaluate(sys.argv[1]))
    print("\n--- CELAH ~2x (diagnostik) ---")
    show_double_gaps(sys.argv[1])