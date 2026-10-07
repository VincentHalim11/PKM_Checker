# Membuat paket rilis Windows: aplikasi Flutter + engine Python terbungkus.
#
# Syarat: build_engine.ps1 sudah dijalankan (folder dist\pkm_engine ada).
#
#   powershell -ExecutionPolicy Bypass -File .\package_release.ps1 -FlutterDir "D:\...\folder_project_flutter"
#
# Hasil: PKM_Checker_release.zip (ekstrak lalu jalankan .exe aplikasi).

param(
    [Parameter(Mandatory = $true)]
    [string]$FlutterDir
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$engine = Join-Path $root "dist\pkm_engine"

if (-not (Test-Path (Join-Path $engine "pkm_engine.exe"))) {
    throw "Engine belum dibangun. Jalankan build_engine.ps1 terlebih dahulu."
}

Push-Location $FlutterDir
try {
    Write-Host "== flutter build windows --release ..."
    flutter build windows --release
    if ($LASTEXITCODE -ne 0) { throw "flutter build gagal." }
}
finally {
    Pop-Location
}

$release = Join-Path $FlutterDir "build\windows\x64\runner\Release"

if (-not (Test-Path $release)) {
    throw "Folder rilis tidak ditemukan: $release"
}

# Aplikasi mencari engine di: <folder .exe>\engine\pkm_engine.exe
$dest = Join-Path $release "engine"

if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }

Copy-Item $engine $dest -Recurse

$zip = Join-Path $root "PKM_Checker_release.zip"

if (Test-Path $zip) { Remove-Item $zip -Force }

Compress-Archive -Path (Join-Path $release "*") -DestinationPath $zip

Write-Host ""
Write-Host "Paket rilis: $zip"
