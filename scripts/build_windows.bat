@echo off
setlocal

REM Build a Windows EXE with PyInstaller.
REM Run this from the repository root on Windows.

if not exist main.py (
  echo ERROR: Run this script from the repository root.
  exit /b 1
)

set "ICON_ARG="
if exist assets\app.ico (
  set "ICON_ARG=--icon assets\app.ico"
)

py -3 -m pip install --upgrade pip
if errorlevel 1 exit /b 1

py -3 -m pip install -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1

py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name MDES-ROM-Editor --version-file scripts\windows_version_info.txt %ICON_ARG% main.py
if errorlevel 1 exit /b 1

echo.
echo Build complete: dist\MDES-ROM-Editor.exe
exit /b 0
