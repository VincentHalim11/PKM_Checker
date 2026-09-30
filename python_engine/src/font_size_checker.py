import sys
from collections import Counter

import pymupdf

from filters import is_symbol_only, is_page_number_text, is_caption_text


# ============================================================
# FONT SIZE RULE
# ============================================================

EXPECTED_FONT_SIZE = 12.0
TOLERANCE = 0.1


# ============================================================
# CHECK SIZE
# ============================================================

def is_expected_size(size: float) -> bool:
    """
    Mengecek apakah ukuran font sesuai dengan aturan.
    """
    return abs(size - EXPECTED_FONT_SIZE) <= TOLERANCE


# ============================================================
# EXTRACT FONT SIZES
# ============================================================

def extract_font_sizes_detailed(pdf_path: str):
    """
    Return (main_counter, caption_counter).

    - main_counter    : ukuran font teks biasa (yang dinilai ketat).
    - caption_counter : ukuran font caption Tabel/Gambar (hanya jadi peringatan).

    Dilewati: span simbol saja dan baris nomor halaman
    (nomor halaman dinilai oleh page_number_analyzer).
    """

    main_counter = Counter()
    caption_counter = Counter()

    doc = pymupdf.open(pdf_path)

    try:
        for page in doc:

            text_data = page.get_text("dict")

            for block in text_data.get("blocks", []):

                if "lines" not in block:
                    continue

                for line in block["lines"]:

                    line_text = "".join(
                        span.get("text", "")
                        for span in line.get("spans", [])
                    ).strip()

                    if not line_text:
                        continue

                    if is_page_number_text(line_text):
                        continue

                    target = (
                        caption_counter
                        if is_caption_text(line_text)
                        else main_counter
                    )

                    for span in line.get("spans", []):

                        text = span.get("text", "").strip()

                        if not text:
                            continue

                        if is_symbol_only(text):
                            continue

                        size = round(float(span.get("size", 0)), 2)

                        target[size] += 1

    finally:
        doc.close()

    return main_counter, caption_counter


def extract_font_sizes(pdf_path: str) -> Counter:
    """Kompatibel dengan kode lama: hanya ukuran font teks biasa."""
    main_counter, _ = extract_font_sizes_detailed(pdf_path)
    return main_counter


# ============================================================
# DISPLAY FONT SIZE CHECK
# ============================================================

def check_font_sizes(pdf_path: str) -> None:

    print("=" * 60)
    print("                 FONT SIZE CHECKER")
    print("=" * 60)

    print(f"File               : {pdf_path}")
    print(
        f"Expected Font Size : "
        f"{EXPECTED_FONT_SIZE:.2f} pt"
    )

    try:
        sizes = extract_font_sizes(pdf_path)

    except Exception as error:
        print(f"\nERROR: {error}")
        return

    print("\n" + "=" * 60)
    print("UKURAN FONT YANG DITEMUKAN")
    print("=" * 60)

    if not sizes:
        print("Tidak ditemukan text layer pada PDF.")
        print("Ukuran font tidak dapat diverifikasi.")
        return

    for size, count in sorted(sizes.items()):

        status = (
            "PASS"
            if is_expected_size(size)
            else "CHECK"
        )

        print(
            f"{size:>7.2f} pt"
            f"{count:>8} kali   "
            f"[{status}]"
        )

    print("\n" + "=" * 60)
    print("HASIL PEMERIKSAAN")
    print("=" * 60)

    invalid_sizes = [
        size
        for size in sizes
        if not is_expected_size(size)
    ]

    if not invalid_sizes:

        print("✅ PASS")
        print(
            "Semua ukuran font yang ditemukan "
            "adalah 12 pt."
        )

    else:

        print("⚠ CHECK")
        print(
            "Ditemukan ukuran font selain 12 pt:"
        )

        for size in invalid_sizes:

            print(
                f"  - {size:.2f} pt "
                f"({sizes[size]} kali)"
            )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            'Cara penggunaan:\n'
            'python font_size_checker.py '
            '"D:\\Folder\\nama_file.pdf"'
        )

        sys.exit(1)

    pdf_path = sys.argv[1]

    check_font_sizes(pdf_path)


# ============================================================
# EVALUASI UKURAN FONT BERBASIS KONTEKS (PKM-PM dan PKM-AI)
# ============================================================

import re

RE_ABSTRACT_HEADING = re.compile(r"^(ABSTRAK|ABSTRACT)\.?$")
RE_INTRO_HEADING = re.compile(r"^(1\s*[.)]?\s*)?PENDAHULUAN\.?$")
RE_SOURCE_LINE = re.compile(r"^(SUMBER|SOURCE)\s*:", re.IGNORECASE)

ABSTRACT_MAX_PAGE = 3   # HEURISTIK: judul + abstrak hanya dicari di 3 halaman pertama


def _norm(text):
    text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    return re.sub(r"\s+", " ", text).strip()


def _scheme_rules(scheme):
    """Kumpulan ukuran yang diizinkan per jenis teks."""
    try:
        from rules import SCHEMES
        cfg = SCHEMES.get(scheme, {})
    except Exception:
        cfg = {}

    body = {EXPECTED_FONT_SIZE}

    if scheme == "AI":
        special = cfg.get("first_page_special", {})
        author = special.get("author_font_size", 10.0)
        abstract = special.get("abstract_font_size", 11.0)
        caption = cfg.get("caption_font_size", 11.0)
        unspecified = set(cfg.get("unspecified_font_sizes", [11.0, 12.0]))
        return {
            "body": body,
            "title": {author, EXPECTED_FONT_SIZE},
            "abstract": {abstract},
            "abstract_heading": {abstract, EXPECTED_FONT_SIZE},
            "caption": {caption},
            "source": unspecified,
            "table": unspecified,
        }

    caption = cfg.get("caption_font_size", EXPECTED_FONT_SIZE)
    return {
        "body": body,
        "caption": {caption},
        "title": body,
        "abstract": body,
        "abstract_heading": body,
        "source": body,
        "table": body,
    }


def _in_any(bbox, rects):
    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    return any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in rects)


def collect_font_spans(pdf_path: str, scheme: str = "GFT"):
    """
    Kumpulkan semua span teks beserta JENIS-nya:
      body | title | abstract | abstract_heading | caption | source | table
    Jenis 'title/abstract' hanya dikenali pada skema AI.
    """
    doc = pymupdf.open(pdf_path)
    out = []

    # status lintas halaman (khusus AI)
    region = "title" if scheme == "AI" else "body"
    abstract_started = False

    try:
        for page in doc:
            pno = page.number + 1

            last_cap = None   # (ukuran, bawah) baris caption/lanjutannya terakhir di halaman ini

            table_rects = []
            try:
                for t in page.find_tables().tables:
                    table_rects.append(tuple(t.bbox))
            except Exception:
                table_rects = []

            for block in page.get_text("dict").get("blocks", []):
                if block.get("type") != 0:
                    continue

                caption_block = False
                caption_size = None

                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    line_text = _norm("".join(s.get("text", "") for s in spans))
                    if not line_text:
                        continue

                    upper = line_text.upper()

                    # nomor halaman dinilai oleh page_number_analyzer
                    if is_page_number_text(line_text):
                        continue

                    # ---- tentukan jenis baris ----
                    kind = None

                    if scheme == "AI" and pno <= ABSTRACT_MAX_PAGE:
                        if RE_ABSTRACT_HEADING.match(upper):
                            abstract_started = True
                            region = "abstract"
                            kind = "abstract_heading"
                        elif region == "abstract" and RE_INTRO_HEADING.match(upper):
                            region = "body"

                    first_size = (
                        round(float(spans[0].get("size", 0)), 2) if spans else 0
                    )

                    if kind is None:
                        if is_caption_text(line_text):
                            kind = "caption"
                            caption_block = True
                            caption_size = first_size
                        elif RE_SOURCE_LINE.match(line_text):
                            kind = "source"
                            caption_block = False
                        elif (
                            caption_block
                            and caption_size is not None
                            and abs(first_size - caption_size) <= TOLERANCE
                        ):
                            kind = "caption"        # lanjutan caption yang turun baris
                        elif (
                            last_cap is not None
                            and abs(first_size - last_cap[0]) <= TOLERANCE
                            and -1.0 <= line["bbox"][1] - last_cap[1] <= 0.6 * last_cap[0]
                        ):
                            # lanjutan caption yang terpisah blok (tepat di bawah baris caption,
                            # ukuran sama) - sering terjadi pada caption rata tengah
                            kind = "caption"
                        elif _in_any(line["bbox"], table_rects):
                            kind = "table"
                        elif scheme == "AI" and region == "abstract" and pno <= ABSTRACT_MAX_PAGE:
                            kind = "abstract"
                        elif scheme == "AI" and region == "title" and pno <= ABSTRACT_MAX_PAGE:
                            kind = "title"
                        else:
                            kind = "body"

                    if kind == "caption":
                        last_cap = (first_size, line["bbox"][3])
                    else:
                        last_cap = None

                    for span in spans:
                        text = span.get("text", "").strip()
                        if not text or is_symbol_only(text):
                            continue
                        if span.get("flags", 0) & 1:      # superscript (mis. "1)" pada nama penulis)
                            continue
                        out.append({
                            "page": pno,
                            "size": round(float(span.get("size", 0)), 2),
                            "text": line_text,
                            "kind": kind,
                        })

            # halaman pertama tanpa heading Abstrak: jangan biarkan region 'title'
            # meluas ke halaman berikutnya
            if scheme == "AI" and pno >= ABSTRACT_MAX_PAGE and not abstract_started:
                region = "body"
    finally:
        doc.close()

    # Jika judul ternyata tidak diikuti heading Abstrak sama sekali,
    # anggap tidak ada area judul/abstrak khusus (ketat: 12 pt).
    if scheme == "AI" and not abstract_started:
        for sp in out:
            if sp["kind"] in ("title", "abstract"):
                sp["kind"] = "body"

    return out


def evaluate_font_sizes(pdf_path: str, scheme: str = "GFT"):
    """
    Return dict:
      invalid          : list ukuran salah pada teks biasa/judul/abstrak/tabel
      caption_invalid  : list ukuran salah pada caption
    Tiap item: {"size", "count", "pages", "samples", "kind"}.
    """
    allowed = _scheme_rules(scheme)
    spans = collect_font_spans(pdf_path, scheme)

    def ok(sp):
        return any(abs(sp["size"] - a) <= TOLERANCE for a in allowed[sp["kind"]])

    def group(items):
        bucket = {}
        for sp in items:
            key = (sp["size"], sp["kind"])
            b = bucket.setdefault(key, {"size": sp["size"], "kind": sp["kind"],
                                        "count": 0, "pages": set(), "samples": []})
            b["count"] += 1
            b["pages"].add(sp["page"])
            if len(b["samples"]) < 3 and sp["text"][:60] not in b["samples"]:
                b["samples"].append(sp["text"][:60])
        res = []
        for b in bucket.values():
            b["pages"] = sorted(b["pages"])
            res.append(b)
        return sorted(res, key=lambda d: (d["size"], d["kind"]))

    bad = [sp for sp in spans if not ok(sp)]
    return {
        "invalid": group([sp for sp in bad if sp["kind"] != "caption"]),
        "caption_invalid": group([sp for sp in bad if sp["kind"] == "caption"]),
        "allowed": allowed,
    }