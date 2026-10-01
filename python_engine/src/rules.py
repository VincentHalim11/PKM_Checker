from copy import deepcopy


# ============================================================
# PKM 2026 - FORMAT RULES
# ============================================================
#
# Struktur aturan:
# - Aturan umum disimpan sebagai default.
# - Setiap skema tetap memiliki profil sendiri.
# - Skema yang memiliki format dasar sama memakai base profile
#   lalu dapat dioverride secara individual.
#
# ============================================================

# ------------------------------------------------------------
# PAGE
# ------------------------------------------------------------

PAGE = {
    "size": "A4",
    "width_cm": 21.0,
    "height_cm": 29.7,
    "columns": 1,
}


# ------------------------------------------------------------
# MARGIN
# ------------------------------------------------------------

MARGIN = {
    "left_cm": 4.0,
    "right_cm": 3.0,
    "top_cm": 3.0,
    "bottom_cm": 3.0,

    # Toleransi deteksi otomatis.
    # Ini bukan aturan PKM, tetapi toleransi teknis.
    "tolerance_cm": 0.45,
}


# ------------------------------------------------------------
# FONT
# ------------------------------------------------------------

FONT = {
    "family": "Times New Roman",
    "size_pt": 12.0,
}


# ------------------------------------------------------------
# PARAGRAPH
# ------------------------------------------------------------

PARAGRAPH = {
    "line_spacing": 1.15,
    "alignment": "justify",
}


# ------------------------------------------------------------
# PAGE NUMBER
# ------------------------------------------------------------

PAGE_NUMBER = {
    "font_family": "Times New Roman",
    "font_size_pt": 12.0,

    # Daftar isi / bagian awal untuk skema yang memiliki Daftar Isi.
    "preliminary_style": "roman",
    "preliminary_position": "bottom_right",

    # Bagian inti dan lampiran.
    "main_style": "arabic",
    "main_position": "top_right",
}


# ------------------------------------------------------------
# MAIN SECTION
# ------------------------------------------------------------
# Default maksimum untuk proposal pendanaan.
# Tetap dipertahankan untuk kompatibilitas dengan kode lama.

MAIN_SECTION = {
    "maximum_core_pages": 10,
    "starts_from": "BAB I PENDAHULUAN",
    "ends_at": "DAFTAR PUSTAKA",
}


# ============================================================
# BASE SCHEME PROFILES
# ============================================================

# Semua skema proposal pendanaan memiliki aturan FORMAT DASAR
# yang sama pada Panduan PKM 2026.
# Masing-masing skema tetap dibuat sebagai profil terpisah
# sehingga nanti dapat memiliki override sendiri.

PROPOSAL_BASE = {
    "structure": "toc_core_attachment",

    "preliminary": {
        "has_toc": True,
        "numbering": "roman",
        "position": "bottom_right",
    },

    "core": {
        "start": "BAB 1",
        "end": "DAFTAR PUSTAKA",
        # 0 = tidak ada minimum yang ditetapkan secara eksplisit.
        # Maksimum proposal pendanaan = 10.
        "min_pages": 0,
        "max_pages": 10,
        "numbering": "arabic",
        "position": "top_right",
    },

    "attachment": {
        "start": "LAMPIRAN",
        "numbering": "arabic",
        "position": "top_right",
    },

    "paragraph": {
        "line_spacing": 1.15,
        "alignment": "justify",
    },

    # Untuk proposal, panduan tidak memberi aturan caption khusus.
    # Nilai 12 pt mengikuti aturan font umum proposal.
    "caption_font_size": 12.0,
}


# ============================================================
# SCHEME PROFILES
# ============================================================

SCHEMES = {

    # --------------------------------------------------------
    # GENERAL
    # --------------------------------------------------------
    # Profil kompatibilitas / default untuk proposal pendanaan.
    "GENERAL": deepcopy(PROPOSAL_BASE),

    # --------------------------------------------------------
    # PKM-GFT
    # --------------------------------------------------------
    "GFT": {
        **deepcopy(PROPOSAL_BASE),
        "core": {
            **PROPOSAL_BASE["core"],
            "min_pages": 8,
            "max_pages": 15,
        },
    },

    # --------------------------------------------------------
    # PKM-AI
    # --------------------------------------------------------
    "AI": {
        "structure": "article_core_attachment",

        "preliminary": {
            "has_toc": False,
            # Tidak ada Daftar Isi pada PKM-AI, jadi tidak ada penomoran romawi.
            "numbering": None,
            "position": None,
        },

        "core": {
            "start": "TITLE",
            "end": "DAFTAR PUSTAKA",
            "min_pages": 8,
            "max_pages": 15,
            "numbering": "arabic",
            "position": "top_right",
        },

        "attachment": {
            "start": "LAMPIRAN",
            "numbering": "arabic",
            "position": "top_right",
        },

        "paragraph": {
            "line_spacing": 1.15,
            "alignment": "justify",
        },

        # Aturan khusus gambar/tabel pada PKM-AI.
        "caption_font_size": 11.0,

        "first_page_special": {
            "title_font_size": 12.0,
            "author_font_size": 10.0,
            "abstract_font_size": 11.0,
            "abstract_heading_font_size": 11.0,
            "line_spacing": 1.0,
        },
        
        "unspecified_font_sizes": [11.0, 12.0],
    },
}


# ============================================================
# FUNDING SCHEMES
# ============================================================
# Delapan skema berikut memakai PROPOSAL_BASE sebagai default.
# Masing-masing tetap memiliki entry sendiri di SCHEMES sehingga
# dapat dioverride secara independen kapan saja.

FUNDING_SCHEMES = (
    "K",
    "KC",
    "KI",
    "PI",
    "PM",
    "RE",
    "RSH",
    "VGK",
)

for _scheme_name in FUNDING_SCHEMES:
    SCHEMES[_scheme_name] = deepcopy(PROPOSAL_BASE)


del _scheme_name


# ============================================================
# HELPER AKSES SKEMA
# ============================================================
# Semua file lain sebaiknya memakai fungsi di bawah ini, bukan
# membandingkan nama skema secara langsung (mis. scheme == "AI").

def get_scheme(name):
    """Profil skema; nama tidak dikenal -> profil GENERAL."""
    return SCHEMES.get(str(name).upper(), SCHEMES["GENERAL"])


def is_article_scheme(name):
    """True bila skema berbentuk artikel (tanpa sampul, tanpa Daftar Isi)."""
    return get_scheme(name).get("structure") == "article_core_attachment"
