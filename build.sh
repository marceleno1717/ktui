#!/usr/bin/env bash
# build.sh — Build the ktui binary with PyInstaller and stage it into the npm package.
# Run from repo root: ./build.sh [--skip-pyinstaller]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PLATFORM="$(python3 -c "
import sys, platform
p = sys.platform
a = platform.machine()
os = 'darwin' if p == 'darwin' else 'win32' if p == 'win32' else 'linux'
arch = 'arm64' if a == 'arm64' else 'x64'
print(f'{os}-{arch}')
")"

BINARY_NAME="ktui"
[[ "$PLATFORM" == win32* ]] && BINARY_NAME="ktui.exe"

NPM_PKG_DIR="$ROOT/npm-package/npm/ktui-${PLATFORM}/bin"
DIST_BIN="$ROOT/dist/${BINARY_NAME}"

echo "▶  Building for platform: $PLATFORM"
mkdir -p "$NPM_PKG_DIR"

if [[ "${1:-}" != "--skip-pyinstaller" ]]; then
    echo "▶  Running PyInstaller…"
    cd "$ROOT"
    pyinstaller ktui.spec --distpath dist --workpath build/pyinstaller --clean -y
    echo "✓  PyInstaller done: $DIST_BIN"
fi

echo "▶  Staging binary → $NPM_PKG_DIR/$BINARY_NAME"
cp "$DIST_BIN" "$NPM_PKG_DIR/$BINARY_NAME"
chmod +x "$NPM_PKG_DIR/$BINARY_NAME" 2>/dev/null || true

echo "✓  Binary staged at npm-package/npm/ktui-${PLATFORM}/bin/$BINARY_NAME"
echo ""
echo "Next steps:"
echo "  cd npm-package/npm/ktui-${PLATFORM} && npm publish --access public"
echo "  cd npm-package && npm publish --access public"
