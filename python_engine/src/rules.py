# ============================================================
# PKM 2026 - FORMAT RULES
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

    # Toleransi deteksi otomatis
    # Ini bukan aturan PKM, tetapi toleransi teknis
    # agar posisi teks PDF tidak terlalu sensitif.
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

    # Daftar isi dan bagian awal:
    "preliminary_style": "roman",
    "preliminary_position": "bottom_right",

    # Bagian inti dan lampiran:
    "main_style": "arabic",
    "main_position": "top_right",
}


# ------------------------------------------------------------
# MAIN SECTION
# ------------------------------------------------------------

MAIN_SECTION = {
    "maximum_core_pages": 10,
    "starts_from": "BAB I PENDAHULUAN",
    "ends_at": "DAFTAR PUSTAKA",
}