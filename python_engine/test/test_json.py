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

    print("=" * 60)
    print(f"{passed}/{len(TESTS)} JSON test lulus")
    print("=" * 60)

    if passed != len(TESTS):
        sys.exit(1)


if __name__ == "__main__":
    main()