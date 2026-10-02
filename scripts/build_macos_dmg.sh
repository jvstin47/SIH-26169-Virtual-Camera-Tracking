#!/usr/bin/env bash
# =============================================================================
# Phoenix-X: Automated macOS DMG Build Script
# Creates an optimized, standalone Phoenix-X.app and wraps it in a DMG
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo "================================================================="
echo "  PHOENIX-X: BUILDING OPTIMIZED MACOS DMG INSTALLER"
echo "================================================================="

# 1. Ensure Dependencies
echo "[1/4] Checking build dependencies..."
python3 -m pip install --quiet pyinstaller pillow

# 2. Generate Application Icons
echo "[2/4] Generating high-resolution App Icons..."
python3 scripts/create_icons.py

# 3. PyInstaller Build
echo "[3/4] Compiling standalone application bundle with PyInstaller..."
python3 -m PyInstaller PhoenixX.spec --clean --noconfirm

# 4. DMG Package Creation
echo "[4/4] Generating disk image (DMG)..."
rm -rf dmg_staging Phoenix-X-macOS.dmg
mkdir -p dmg_staging
cp -R dist/Phoenix-X.app dmg_staging/
ln -s /Applications dmg_staging/Applications

hdiutil create -volname "Phoenix-X Optical Tracker" \
               -srcfolder dmg_staging \
               -ov -format UDZO Phoenix-X-macOS.dmg

rm -rf dmg_staging

echo ""
echo "================================================================="
echo "[+] SUCCESS: Built Phoenix-X-macOS.dmg ($(du -h Phoenix-X-macOS.dmg | cut -f1))"
echo "    Mount and drag Phoenix-X.app into Applications!"
echo "================================================================="
