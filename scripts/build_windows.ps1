$ErrorActionPreference = "Stop"

# Build a Windows EXE with PyInstaller.
# Run this script from the repository root on Windows.

if (-not (Test-Path "main.py")) {
    throw "Run this script from the repository root."
}

$iconArgs = @()
if (Test-Path "assets/app.ico") {
    $iconArgs = @("--icon", "assets/app.ico")
}

py -3 -m pip install --upgrade pip
py -3 -m pip install -r requirements.txt pyinstaller
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name MDES-ROM-Editor --version-file scripts/windows_version_info.txt @iconArgs main.py

Write-Host "Build complete: dist\MDES-ROM-Editor.exe"
