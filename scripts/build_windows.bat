@echo off
setlocal

REM Build a Windows EXE with PyInstaller.
REM Run this script from the repository root on Windows.

if not exist main.py (
  echo ERROR: Run this script from the repository root.
  exit /b 1
)

if not exist MDES-ROM-Editor.spec (
  echo ERROR: MDES-ROM-Editor.spec not found. Make sure you are in the repo root.
  exit /b 1
)

py -3 -m pip install --upgrade pip
if errorlevel 1 exit /b 1

py -3 -m pip install -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1

py -3 -m PyInstaller --noconfirm --clean MDES-ROM-Editor.spec
if errorlevel 1 exit /b 1

echo.
echo Build complete: dist\MDES-ROM-Editor.exe
exit /b 0
