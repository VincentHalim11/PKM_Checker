import os
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).parent
TEST_CASE_DIR = BASE_DIR / "test_cases"


TEST_CASES = [
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
    },
]


def run_test(test_case):
    pdf_path = TEST_CASE_DIR / test_case["file"]

    command = [
        sys.executable,
        "-X",
        "utf8",
        str(BASE_DIR.parent / "src" / "validator.py"),
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

    output = result.stdout + result.stderr

    expected = test_case["expected"]

    if expected in output and "❌" in output:
        print(f"[PASS] {test_case['file']}")
    else:
        print(f"[FAIL] {test_case['file']}")
        print("Expected:", expected)
        print(output)


if __name__ == "__main__":
    print("=" * 60)
    print("             PKM VALIDATOR TEST")
    print("=" * 60)

    for test_case in TEST_CASES:
        run_test(test_case)