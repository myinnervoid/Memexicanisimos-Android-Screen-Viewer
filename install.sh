#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_PATH="$SCRIPT_DIR/MASV"

if [ ! -f "$BIN_PATH" ]; then
    echo "❌ No se encontró el binario 'MASV' en $SCRIPT_DIR"
    exit 1
fi

chmod +x "$BIN_PATH"
echo "📦 Instalando MASV en tu sistema..."
"$BIN_PATH" --install
echo "🎉 ¡Instalación completa! Ahora puedes abrir MASV desde el menú de aplicaciones o escribiendo 'MASV' en tu terminal."
