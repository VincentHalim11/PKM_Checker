# Membangun engine Python menjadi folder mandiri (pengguna TIDAK perlu memasang Python).
#
# Jalankan dari folder python_engine:
#   powershell -ExecutionPolicy Bypass -File .\build_engine.ps1
#   powershell -ExecutionPolicy Bypass -File .\build_engine.ps1 -TestPdf "D:\PDF_PKM\PKM_AI.pdf" -Scheme AI
#
# Hasil: dist\pkm_engine\pkm_engine.exe (+ file pendukung di folder yang sama).
# Seluruh folder dist\pkm_engine harus ikut dibagikan, bukan hanya .exe-nya.

param(
    [string]$TestPdf = "",
    [string]$Scheme = "GENERAL"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    throw "Python virtual environment tidak ditemukan: $py"
}

Write-Host "== Memasang PyInstaller ..."
& $py -m pip install --upgrade pyinstaller
if ($LASTEXITCODE -ne 0) { throw "Gagal memasang PyInstaller." }

Write-Host "== Membangun engine (onedir) ..."
& $py -m PyInstaller --noconfirm --clean --onedir --name pkm_engine `
    --paths (Join-Path $root "src") `
    --collect-all pymupdf `
    --hidden-import pytesseract `
    --distpath (Join-Path $root "dist") `
    --workpath (Join-Path $root "build") `
    --specpath (Join-Path $root "build") `
    (Join-Path $root "src\validator.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller gagal." }

$exe = Join-Path $root "dist\pkm_engine\pkm_engine.exe"

if (-not (Test-Path $exe)) { throw "pkm_engine.exe tidak terbentuk." }

Write-Host ""
Write-Host "== Uji 1: skema salah harus menghasilkan JSON status ERROR"
& $exe "x.pdf" --scheme XYZ --json

if ($TestPdf -ne "") {
    Write-Host ""
    Write-Host "== Uji 2: memeriksa $TestPdf (skema $Scheme)"
    $json = & $exe $TestPdf --scheme $Scheme --json | Out-String
    $result = $json | ConvertFrom-Json
    Write-Host ("Status akhir: " + $result.status)
    foreach ($p in $result.checks.PSObject.Properties) {
        Write-Host ("  {0,-22} {1}" -f $p.Name, $p.Value.status)
    }
}

Write-Host ""
Write-Host "Engine selesai: $exe"
