# Build trên Windows:  powershell -ExecutionPolicy Bypass -File build.ps1 0.1.0
param([string]$Version = "0.1.0")
$ErrorActionPreference = "Stop"

uv sync --locked --all-groups
uv run pytest -q

# Tải Chromium vào trong gói playwright để PyInstaller mang theo; máy dùng không cần cài trình duyệt.
$env:PLAYWRIGHT_BROWSERS_PATH = "0"
uv run playwright install chromium

# --onedir: khởi động nhanh, ít bị antivirus báo nhầm.
# --collect-all playwright: kèm driver Node và Chromium vừa tải.
uv run pyinstaller --noconfirm --clean --onedir --windowed `
  --name NhapPhieuMPLIS `
  --paths src `
  --add-data "config;config" `
  --collect-all playwright `
  --collect-submodules keyring.backends `
  run_app.py

iscc /DAppVersion=$Version installer\setup.iss
Write-Host "Xong: installer\Output\NhapPhieuMPLIS-Setup-$Version.exe"
