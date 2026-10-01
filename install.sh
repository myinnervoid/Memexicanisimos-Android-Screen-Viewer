#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_PATH="$SCRIPT_DIR/MASV"

if [ ! -f "$BIN_PATH" ]; then
    echo "❌ Error: No se encontró el ejecutable 'MASV' en: $SCRIPT_DIR"
    exit 1
fi

chmod +x "$BIN_PATH"
echo "📦 Instalando MASV (Memexicanisimos Android Screen Viewer)..."
"$BIN_PATH" --install

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo "=========================================================="
echo "🎉 ¡Instalación exitosa!"
echo "   • Acceso en el Menú: Utilidades / Desarrollo -> MASV"
echo "   • Comando directo en Terminal: MASV"
echo "   • El binario se copió de forma persistente en ~/.MASV/bin/"
echo "   • Ya puedes mover, guardar o borrar esta carpeta temporal."
echo "=========================================================="
