import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = ROOT / "src" / "validator.py"
TEST_CASES = ROOT / "test" / "test_cases"


# ============================================================
# TEST CASES
# ============================================================

TESTS = [
    # --------------------------------------------------------
    # INVALID FILES
    # --------------------------------------------------------

    {
        "file": "SALAH_01_font_bukan_TNR_PKM-K.pdf",
        "scheme": "K",
        "expected_status": "FAIL",
    },
    {
        "file": "SALAH_02_ukuran_huruf_11_PKM-KC.pdf",
        "scheme": "KC",
        "expected_status": "FAIL",
    },
    {
        "file": "SALAH_03_spasi_1_5_PKM-KI.pdf",
        "scheme": "KI",
        "expected_status": "FAIL",
    },
    {
        "file": "SALAH_04_rata_kiri_saja_PKM-PI.pdf",
        "scheme": "PI",
        "expected_status": "FAIL",
    },
    {
        "file": "SALAH_05_margin_kiri_3cm_PKM-PM.pdf",
        "scheme": "PM",
        "expected_status": "FAIL",
    },
    {
        "file": "SALAH_06_kertas_Letter_PKM-RE.pdf",
        "scheme": "RE",
        "expected_status": "FAIL",
    },
    {
        "file": "SALAH_07_bagian_inti_lebih_10_hal_PKM-RSH.pdf",
        "scheme": "RSH",
        "expected_status": "FAIL",
    },
    {
        "file": "SALAH_08_ada_halaman_sampul_PKM-VGK.pdf",
        "scheme": "VGK",
        "expected_status": "FAIL",
    },
    {
        "file": "SALAH_09_ada_abstrak_di_GFT_PKM-GFT.pdf",
        "scheme": "GFT",
        "expected_status": "FAIL",
    },
    {
        "file": "SALAH_10_daftar_isi_angka_arab_PKM-K.pdf",
        "scheme": "K",
        "expected_status": "FAIL",
    },
    {
        "file": "SALAH_11_penomoran_inti_mulai_5_PKM-PI.pdf",
        "scheme": "PI",
        "expected_status": "FAIL",
    },
    {
        "file": "SALAH_12_ukuran_nomor_halaman_10_PKM-KI.pdf",
        "scheme": "KI",
        "expected_status": "FAIL",
    },
    {
        "file": "SALAH_13_nomor_halaman_kiri_atas_PKM-PM.pdf",
        "scheme": "PM",
        "expected_status": "FAIL",
    },
    {
        "file": "SALAH_14_bagian_inti_kurang_8_hal_GFT_PKM-GFT.pdf",
        "scheme": "GFT",
        "expected_status": "FAIL",
    },
    {
        "file": "SALAH_15_banyak_kesalahan_PKM-K.pdf",
        "scheme": "K",
        "expected_status": "FAIL",
    },
    {
        "file": "SALAH_PKMUC(revisifont).pdf",
        "scheme": "GENERAL",
        "expected_status": "FAIL",
    },

    # --------------------------------------------------------
    # VALID FILES
    # --------------------------------------------------------

    {
        "file": "BENAR_PKM_AI.pdf",
        "scheme": "AI",
        "expected_status": "PASS",
    },
    {
        "file": "BENAR_PKM_PM_UC.pdf",
        "scheme": "GENERAL",
        "expected_status": "PASS",
    },
    {
        "file": "BENAR_PROPOSALPROGRAMKREATIVITASMAHASISWAPKM_GFT.pdf",
        "scheme": "GFT",
        "expected_status": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-GFT.pdf",
        "scheme": "GFT",
        "expected_status": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-K.pdf",
        "scheme": "K",
        "expected_status": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-KC.pdf",
        "scheme": "KC",
        "expected_status": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-KI.pdf",
        "scheme": "KI",
        "expected_status": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-PI.pdf",
        "scheme": "PI",
        "expected_status": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-PM.pdf",
        "scheme": "PM",
        "expected_status": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-RE.pdf",
        "scheme": "RE",
        "expected_status": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-RSH.pdf",
        "scheme": "RSH",
        "expected_status": "PASS",
    },
    {
        "file": "BENAR_Proposal_Dummy_PKM-VGK.pdf",
        "scheme": "VGK",
        "expected_status": "PASS",
    },
]


# ============================================================
# KONTRAK JSON (dipakai UI Flutter - home_screen.dart)
# ============================================================
# Kunci di bawah harus sama dengan 'definitions' di _buildValidationResults().
# Jika sebuah kunci hilang, Flutter diam-diam menyembunyikan kartunya.

REQUIRED_CHECKS = [
    "page_size",
    "font",
    "font_size",
    "margin",
    "line_spacing",
    "alignment",
    "page_number_font",
    "page_number_position",
    "page_number_sequence",
    "page_number_coverage",
    "front_matter",
    "core_pages",
]

VALID_STATUS = {"PASS", "FAIL", "REVIEW"}


def check_contract(filename, data):
    """Return daftar masalah kontrak (kosong bila semua benar)."""
    problems = []
    checks = data["checks"]

    missing = [k for k in REQUIRED_CHECKS if k not in checks]
    if missing:
        problems.append(f"kunci checks hilang: {missing}")

    for key in REQUIRED_CHECKS:
        item = checks.get(key)
        if item is None:
            continue
        if not isinstance(item, dict):
            problems.append(f"checks.{key} bukan object")
            continue
        if item.get("status") not in VALID_STATUS:
            problems.append(f"checks.{key}.status tidak valid: {item.get('status')!r}")
        if not isinstance(item.get("message"), str):
            problems.append(f"checks.{key}.message bukan string")
        if "details" not in item:
            problems.append(f"checks.{key} tidak punya 'details'")

    return problems


# ============================================================
# ERROR HANDLING (mode --json harus tetap menghasilkan JSON)
# ============================================================

ERROR_TESTS = [
    {
        "name": "skema tidak dikenal",
        "file": "SALAH_01_font_bukan_TNR_PKM-K.pdf",
        "scheme": "XYZ",
    },
    {
        "name": "file PDF tidak ada",
        "file": "TIDAK_ADA.pdf",
        "scheme": "K",
    },
]


def run_error_test(test_case):
    name = test_case["name"]

    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            str(TEST_CASES / test_case["file"]),
            "--scheme",
            test_case["scheme"],
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"[FAIL] error: {name} - stdout bukan JSON")
        print(result.stdout)
        return False

    if data.get("status") != "ERROR" or not data.get("error"):
        print(f"[FAIL] error: {name} - harus status=ERROR dengan pesan 'error'")
        return False

    if result.returncode == 0:
        print(f"[FAIL] error: {name} - kode keluar seharusnya bukan 0")
        return False

    print(f"[PASS] error: {name}")
    return True


# ============================================================
# RUN ONE TEST
# ============================================================

def run_json_test(test_case):
    filename = test_case["file"]
    scheme = test_case["scheme"]
    expected_status = test_case["expected_status"]

    pdf_path = TEST_CASES / filename

    if not pdf_path.exists():
        print(f"[FAIL] {filename} - file tidak ditemukan")
        return False

    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            str(pdf_path),
            "--scheme",
            scheme,
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # PROCESS ERROR
    # --------------------------------------------------------

    if result.returncode != 0:
        print(f"[FAIL] {filename} - validator error")

        if result.stderr:
            print(result.stderr)

        return False

    # --------------------------------------------------------
    # JSON PARSE
    # --------------------------------------------------------

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"[FAIL] {filename} - output bukan JSON valid")
        print(f"Error: {e}")
        print()
        print("Output yang diterima:")
        print(result.stdout)

        return False

    # --------------------------------------------------------
    # CHECK ROOT STATUS
    # --------------------------------------------------------

    actual_status = data.get("status")

    if actual_status != expected_status:
        print(
            f"[FAIL] {filename} - "
            f"status = {actual_status}, "
            f"expected = {expected_status}"
        )

        return False

    # --------------------------------------------------------
    # CHECK 'checks'
    # --------------------------------------------------------

    if "checks" not in data:
        print(f"[FAIL] {filename} - key 'checks' tidak ditemukan")
        return False

    if not isinstance(data["checks"], dict):
        print(f"[FAIL] {filename} - 'checks' bukan object/dict")
        return False

    # --------------------------------------------------------
    # KONTRAK 12 KUNCI (agar UI tidak diam-diam menyembunyikan kartu)
    # --------------------------------------------------------

    problems = check_contract(filename, data)

    if problems:
        print(f"[FAIL] {filename} - kontrak JSON tidak terpenuhi")
        for p in problems:
            print(f"    - {p}")
        return False

    # --------------------------------------------------------
    # PASS
    # --------------------------------------------------------

    print(f"[PASS] {filename}")
    return True


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("               PKM JSON TEST")
    print("=" * 60)

    passed = 0

    for test_case in TESTS:
        if run_json_test(test_case):
            passed += 1

    for test_case in ERROR_TESTS:
        if run_error_test(test_case):
            passed += 1

    total = len(TESTS) + len(ERROR_TESTS)

    print("=" * 60)
    print(f"{passed}/{total} JSON test lulus")
    print("=" * 60)

    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()