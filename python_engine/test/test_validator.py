import os
import re
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).parent
TEST_CASE_DIR = BASE_DIR / "test_cases"
VALIDATOR = BASE_DIR.parent / "src" / "validator.py"


# ============================================================
# CARA MENAMBAH TEST CASE BARU
# ------------------------------------------------------------
# 1. Letakkan PDF di folder test_cases/.
# 2. Tambahkan satu dict di TEST_CASES:
#      "file"     : nama berkas PDF
#      "scheme"   : "GENERAL", "GFT", atau "AI"
#      "expected" : - "PASS"           -> dokumen BENAR, status akhir harus PASS
#                   - "Font Size", dst -> dokumen SALAH, baris dengan label itu
#                                         harus berawalan ❌
#                   - [..., ...]       -> cukup salah satu label yang ditandai ❌
#      "min_flags": (opsional) minimal jumlah label berbeda yang ditandai ❌,
#                   dipakai untuk dokumen "banyak kesalahan"
# 3. Jalankan:  python test\test_validator.py
#    Berkas PDF yang belum didaftarkan akan diperingatkan di akhir.
#
# Label yang dikenali (sama dengan teks di sebelah kiri tanda ":" pada keluaran):
#   Page Size, Font, Font Size, Margin, Line Spacing, Alignment,
#   Nomor Hal. Font, Nomor Hal. Posisi, Nomor Awal, Cakupan Nomor,
#   Halaman Awal, Bagian Inti
# "Nomor" berarti salah satu label yang diawali "Nomor".
# ============================================================

TEST_CASES = [
    # ---------------- dokumen SALAH ----------------
    {
        "file": "SALAH_01_font_bukan_TNR_PKM-K.pdf",
        "scheme": "GENERAL",
        "expected": "Font",
    },
    {
        "file": "SALAH_02_ukuran_huruf_11_PKM-KC.pdf",
        "scheme": "GENERAL",
        "expected": "Font Size",
    },
    {
        "file": "SALAH_03_spasi_1_5_PKM-KI.pdf",
        "scheme": "GENERAL",
        "expected": "Line Spacing",
    },
    {
        "file": "SALAH_04_rata_kiri_saja_PKM-PI.pdf",
        "scheme": "GENERAL",
        "expected": "Alignment",
    },
    {
        "file": "SALAH_05_margin_kiri_3cm_PKM-PM.pdf",
        "scheme": "GENERAL",
        "expected": "Margin",
    },
    {
        "file": "SALAH_06_kertas_Letter_PKM-RE.pdf",
        "scheme": "GENERAL",
        "expected": "Page Size",
    },
    {
        "file": "SALAH_07_bagian_inti_lebih_10_hal_PKM-RSH.pdf",
        "scheme": "GENERAL",
        "expected": "Bagian Inti",
    },
    {
        "file": "SALAH_08_ada_halaman_sampul_PKM-VGK.pdf",
        "scheme": "GENERAL",
        "expected": "Halaman Awal",
    },
    {
        "file": "SALAH_09_ada_abstrak_di_GFT_PKM-GFT.pdf",
        "scheme": "GFT",
        "expected": "Halaman Awal",
    },
    {
        "file": "SALAH_10_daftar_isi_angka_arab_PKM-K.pdf",
        "scheme": "GENERAL",
        "expected": "Nomor",
    },
    {
        "file": "SALAH_11_penomoran_inti_mulai_5_PKM-PI.pdf",
        "scheme": "GENERAL",
        "expected": "Nomor",
    },
    {
        "file": "SALAH_12_ukuran_nomor_halaman_10_PKM-KI.pdf",
        "scheme": "GENERAL",
        "expected": "Nomor Hal. Font",
    },
    {
        "file": "SALAH_13_nomor_halaman_kiri_atas_PKM-PM.pdf",
        "scheme": "GENERAL",
        "expected": "Nomor Hal. Posisi",
    },
    {
        "file": "SALAH_14_bagian_inti_kurang_8_hal_GFT_PKM-GFT.pdf",
        "scheme": "GFT",
        "expected": "Bagian Inti",
    },
    {
        "file": "SALAH_15_banyak_kesalahan_PKM-K.pdf",
        "scheme": "GENERAL",
        "expected": "Font",
        "min_flags": 3,
    },
    {
        # Semua teks sudah 12 pt dan TNR; yang tersisa: Daftar Pustaka meluber
        # ke halaman 15 sehingga bagian inti 11 halaman. KONFIRMASI: apakah ini
        # kesalahan yang Anda maksud pada berkas ini?
        "file": "SALAH_PKMUC(revisifont).pdf",
        "scheme": "GENERAL",
        "expected": "Bagian Inti",
    },

    # ---------------- dokumen BENAR (status akhir harus PASS) ----------------
    {
        "file": "BENAR_PKM_AI.pdf",
        "scheme": "AI",
        "expected": "PASS",
    },
    {
        "file": "BENAR_PKM_PM_UC.pdf",
        "scheme": "GENERAL",
        "expected": "PASS",
    },
    {
        # Saat ini GAGAL: judul "DAFTAR PUSTAKA" dan "LAMPIRAN" 14 pt,
        # "BAB 3 / KESIMPULAN" 11 pt, dan isi daftar isi 11 pt. Menurut aturan
        # (TNR 12 tanpa pengecualian) berkas ini belum patuh.
        "file": "BENAR_PROPOSALPROGRAMKREATIVITASMAHASISWAPKM_GFT.pdf",
        "scheme": "GFT",
        "expected": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-GFT.pdf",
        "scheme": "GFT",
        "expected": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-K.pdf",
        "scheme": "GENERAL",
        "expected": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-KC.pdf",
        "scheme": "GENERAL",
        "expected": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-KI.pdf",
        "scheme": "GENERAL",
        "expected": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-PI.pdf",
        "scheme": "GENERAL",
        "expected": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-PM.pdf",
        "scheme": "GENERAL",
        "expected": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-RE.pdf",
        "scheme": "GENERAL",
        "expected": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-RSH.pdf",
        "scheme": "GENERAL",
        "expected": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-VGK.pdf",
        "scheme": "GENERAL",
        "expected": "PASS",
    },
]


# ------------------------------------------------------------
# Membaca keluaran validator
# ------------------------------------------------------------

LABEL_LINE = re.compile(r"^\s*❌\s*(.+?)\s*:")
FINAL_LINE = re.compile(r"^\s*(?:✅|❌|⚠️)\s*(PASS|FAIL|REVIEW)\s*$")
MARGIN_FAIL = re.compile(r"^\s*Margin Status\s*:\s*FAIL")


def flagged_labels(output):
    """Label pemeriksaan yang ditandai ❌ (berawalan ❌ pada barisnya)."""
    labels = []
    for line in output.splitlines():
        m = LABEL_LINE.match(line)
        if m:
            labels.append(m.group(1).strip())
        if MARGIN_FAIL.match(line):
            labels.append("Margin")
    return labels


def final_status(output):
    status = None
    for line in output.splitlines():
        m = FINAL_LINE.match(line)
        if m:
            status = m.group(1)
    return status


def label_matches(expected, label):
    if label == expected:
        return True
    return expected == "Nomor" and label.startswith("Nomor")


def run_validator(test_case):
    pdf_path = TEST_CASE_DIR / test_case["file"]

    command = [
        sys.executable,
        "-X",
        "utf8",
        str(VALIDATOR),
        str(pdf_path),
        "--scheme",
        test_case["scheme"],
    ]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )

    return result.stdout + result.stderr


def run_test(test_case):
    if not (TEST_CASE_DIR / test_case["file"]).exists():
        print(f"[SKIP] {test_case['file']}  (berkas tidak ditemukan)")
        return None

    output = run_validator(test_case)
    expected = test_case["expected"]
    labels = flagged_labels(output)
    status = final_status(output)

    if expected == "PASS":
        passed = status == "PASS"
        reason = f"status akhir {status}, label ❌: {labels}"
    else:
        wanted = expected if isinstance(expected, list) else [expected]
        hit = any(label_matches(w, l) for w in wanted for l in labels)
        enough = len(set(labels)) >= test_case.get("min_flags", 1)
        passed = hit and enough
        reason = f"diharapkan {wanted}, terdeteksi {labels}"

    if passed:
        print(f"[PASS] {test_case['file']}")
    else:
        print(f"[FAIL] {test_case['file']}")
        print("   ", reason)
        print(output)

    return passed


def warn_unregistered():
    registered = {t["file"] for t in TEST_CASES}
    extra = sorted(
        p.name for p in TEST_CASE_DIR.glob("*.pdf") if p.name not in registered
    )
    if extra:
        print()
        print("PERINGATAN: PDF berikut ada di test_cases/ tetapi belum didaftarkan:")
        for name in extra:
            print("  -", name)


if __name__ == "__main__":
    print("=" * 60)
    print("             PKM VALIDATOR TEST")
    print("=" * 60)

    outcomes = [run_test(t) for t in TEST_CASES]
    ran = [o for o in outcomes if o is not None]

    print("=" * 60)
    print(f"{sum(ran)}/{len(ran)} test lulus")
    warn_unregistered()

    sys.exit(0 if all(ran) else 1)