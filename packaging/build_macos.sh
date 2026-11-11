#!/bin/bash
# Dependencies must already be installed in a dedicated native Python environment.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT/.venv-macos/bin/python}"
BUILD_ROOT="${1:-$ROOT/build/macos-arm64}"
"$PYTHON" -c 'import platform,sys; assert sys.platform == "darwin" and platform.machine() == "arm64", "Native macOS ARM64 Python required"; assert sys.prefix != sys.base_prefix, "Use a dedicated virtual environment"'
BUILD_ROOT="$("$PYTHON" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).expanduser().resolve())' "$BUILD_ROOT")"
if [ -e "$BUILD_ROOT" ]; then
    echo "Refusing to overwrite build directory: $BUILD_ROOT" >&2
    exit 1
fi
mkdir -p "$BUILD_ROOT"
cd "$ROOT"
"$PYTHON" -m pip freeze --exclude-editable > "$BUILD_ROOT/dependencies.txt"
"$PYTHON" -m PyInstaller --noconfirm --distpath "$BUILD_ROOT/dist" --workpath "$BUILD_ROOT/work" packaging/emcd_macos.spec
"$PYTHON" packaging/check_macos_bundle.py "$BUILD_ROOT/dist/EMCD-Sim.app"
/usr/bin/file "$BUILD_ROOT/dist/EMCD-Sim.app/Contents/MacOS/EMCD-Sim"
echo "Local candidate: $BUILD_ROOT/dist/EMCD-Sim.app"
