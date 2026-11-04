# Build trên Windows:  powershell -ExecutionPolicy Bypass -File build.ps1 0.1.0
param([string]$Version = "0.1.0")
$ErrorActionPreference = "Stop"

uv sync --locked --all-groups
uv run pytest -q

# --onedir: khởi động nhanh, ít bị antivirus báo nhầm.
# --collect-all playwright: kèm driver Node của Playwright (KHÔNG kèm Chromium vì dùng Edge).
uv run pyinstaller --noconfirm --clean --onedir --windowed `
  --name NhapPhieuMPLIS `
  --paths src `
  --add-data "config;config" `
  --collect-all playwright `
  --collect-submodules keyring.backends `
  run_app.py

iscc /DAppVersion=$Version installer\setup.iss
Write-Host "Xong: installer\Output\NhapPhieuMPLIS-Setup-$Version.exe"
