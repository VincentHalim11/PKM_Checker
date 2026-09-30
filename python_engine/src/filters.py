"""
filters.py - fungsi bantu bersama untuk membuang "noise" yang bukan pelanggaran format.
"""
import re

# nomor halaman: angka (1, 12) atau romawi (i, ii, iv, xii)
PAGE_NUM_RE = re.compile(r"^(\d{1,3}|[ivxlcdm]{1,7})$", re.IGNORECASE)

# caption tabel / gambar, mis. "Tabel 1. Indikator ..." atau "Gambar 1. Bagan ..."
CAPTION_RE = re.compile(r"^(Tabel|Gambar)\s*\d+\s*[.:]", re.IGNORECASE)


def is_page_number_text(text: str) -> bool:
    """True bila teks hanya berisi nomor halaman (Arab atau Romawi)."""
    return bool(PAGE_NUM_RE.fullmatch(text.strip()))


def is_symbol_only(text: str) -> bool:
    """True bila teks tidak punya huruf/angka sama sekali (mis. subscript, centang, bullet).
    Font cadangan seperti MS-PMincho sering muncul di sini dan bukan kesalahan penulis."""
    return not re.search(r"[A-Za-z0-9]", text)


def is_caption_text(text: str) -> bool:
    """True bila baris adalah caption tabel/gambar."""
    return bool(CAPTION_RE.match(text.strip()))