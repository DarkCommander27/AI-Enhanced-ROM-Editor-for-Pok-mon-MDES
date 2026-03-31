$ErrorActionPreference = "Stop"

# Build a Windows EXE with PyInstaller.
# Run this script from the repository root on Windows.

if (-not (Test-Path "main.py")) {
    throw "Run this script from the repository root."
}

if (-not (Test-Path "MDES-ROM-Editor.spec")) {
    throw "MDES-ROM-Editor.spec not found. Make sure you are in the repo root."
}

py -3 -m pip install --upgrade pip
py -3 -m pip install -r requirements.txt pyinstaller
py -3 -m PyInstaller --noconfirm --clean MDES-ROM-Editor.spec

Write-Host "Build complete: dist\MDES-ROM-Editor.exe"
