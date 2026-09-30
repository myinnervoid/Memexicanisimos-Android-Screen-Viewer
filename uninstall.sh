#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_PATH="$SCRIPT_DIR/MASV"

echo "🗑️ Desinstalando MASV..."
if [ -f "$BIN_PATH" ]; then
    "$BIN_PATH" --uninstall "$@"
elif [ -f "$HOME/.local/bin/MASV" ]; then
    "$HOME/.local/bin/MASV" --uninstall "$@"
else
    rm -f "$HOME/.local/bin/MASV" "$HOME/.local/bin/masv" "$HOME/.local/share/applications/MASV.desktop"
    echo "✅ Enlaces y accesos directos de MASV eliminados correctamente."
fi
