@echo off
REM ================================================================
REM  Videcook — Portable Windows Build Script
REM
REM  Builds a portable dist/Videcook/ folder using PyInstaller.
REM  Requires Python 3.11+ and pyinstaller (pip install pyinstaller).
REM
REM  The resulting dist/Videcook/ folder can be copied anywhere
REM  and run by double-clicking Videcook.exe.
REM
REM  IMPORTANT: Binaries (yt-dlp.exe, ffmpeg.exe, ffprobe.exe)
REM  must be placed in bin/ BEFORE running this script, or the
REM  resulting .exe will work but cannot download videos.
REM ================================================================
setlocal enabledelayedexpansion

echo ================================================================
echo  Videcook Portable Build
echo ================================================================

REM --- Check prerequisites ---
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not on PATH. Install Python 3.11+ first.
    exit /b 1
)

python -c "import PyInstaller" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Installing pyinstaller...
    python -m pip install pyinstaller>=6.0
    if %ERRORLEVEL% NEQ 0 exit /b 1
)

REM --- Warn if bin/ is empty ---
set "BIN_COUNT=0"
for %%f in (bin\*.exe) do set /a BIN_COUNT+=1
if %BIN_COUNT% EQU 0 (
    echo.
    echo [WARNING] bin/ contains no .exe files!
    echo           Videcook.exe will be built, but real downloads will fail.
    echo           Place yt-dlp.exe, ffmpeg.exe, ffprobe.exe in bin/,
    echo           or run: python scripts/download_binaries.py --all
    echo           Then re-run this build script.
    echo.
    choice /c YN /m "Continue without binaries"
    if !ERRORLEVEL! EQU 2 exit /b 0
)

REM --- Clean previous build ---
echo.
echo [INFO] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM --- Run PyInstaller ---
echo [INFO] Building with PyInstaller...
python -m PyInstaller --clean --noconfirm Videcook.spec
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyInstaller build failed.
    exit /b 1
)

REM --- Verify output ---
if not exist "dist\Videcook\Videcook.exe" (
    echo [ERROR] Build output not found.
    exit /b 1
)

echo.
echo ================================================================
echo  Build complete!
echo  Output: dist\Videcook\
echo  Launch: dist\Videcook\Videcook.exe
echo ================================================================
exit /b 0
