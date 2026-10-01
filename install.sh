#!/bin/bash
set -e

# Detectar directorio si se ejecuta como archivo local o tubería (pipe)
if [ -n "$BASH_SOURCE" ] && [ -f "$BASH_SOURCE" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    SCRIPT_DIR="$(pwd)"
fi

BIN_PATH=""
CLEANUP_TMP=false

# 1. Caso A: Paquete descomprimido (MASV en la misma carpeta)
if [ -f "$SCRIPT_DIR/MASV" ]; then
    BIN_PATH="$SCRIPT_DIR/MASV"
# 2. Caso B: Ya compilado en carpeta dist/
elif [ -f "$SCRIPT_DIR/dist/MASV" ]; then
    BIN_PATH="$SCRIPT_DIR/dist/MASV"
# 3. Caso C: Git clone (código fuente presente)
elif [ -f "$SCRIPT_DIR/build.py" ] && command -v python3 >/dev/null 2>&1; then
    echo "🔨 Detectado entorno de código fuente (git clone). Compilando binario..."
    python3 "$SCRIPT_DIR/build.py"
    BIN_PATH="$SCRIPT_DIR/dist/MASV"
# 4. Caso D: 1-Liner curl/wget directo desde internet (sin clonar el repo)
else
    echo "🌐 Descargando la versión más reciente de MASV desde GitHub..."
    TMP_DIR=$(mktemp -d)
    TAR_URL="https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-Linux.tar.gz"
    
    if command -v curl >/dev/null 2>&1; then
        curl -sSL "$TAR_URL" -o "$TMP_DIR/MASV-Linux.tar.gz"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "$TMP_DIR/MASV-Linux.tar.gz" "$TAR_URL"
    else
        echo "❌ Error: Se requiere 'curl' o 'wget' para descargar MASV."
        exit 1
    fi
    
    tar -xzf "$TMP_DIR/MASV-Linux.tar.gz" -C "$TMP_DIR"
    BIN_PATH="$TMP_DIR/MASV"
    CLEANUP_TMP=true
fi

if [ ! -f "$BIN_PATH" ]; then
    echo "❌ Error: No se pudo resolver o generar el ejecutable 'MASV'."
    exit 1
fi

chmod +x "$BIN_PATH"
echo "📦 Instalando MASV (Memexicanisimos Android Screen Viewer)..."
"$BIN_PATH" --install

if [ "$CLEANUP_TMP" = true ] && [ -d "$TMP_DIR" ]; then
    rm -rf "$TMP_DIR"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo "=========================================================="
echo "🎉 ¡Instalación exitosa!"
echo "   • Acceso en el Menú: Utilidades / Desarrollo -> MASV"
echo "   • Comando directo en Terminal: MASV"
echo "   • El binario se copió de forma persistente en ~/.MASV/bin/"
echo "=========================================================="
