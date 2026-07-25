import os
import sys
import subprocess
import shutil

# ── Configuración del build ────────────────────────────────────────────────
APP_NAME  = "MASV"
ENTRY     = "run.py"
ICON_FILE = None  # Pon aquí la ruta a un .ico/.icns si tienes uno

bin_dir  = os.path.join(os.path.dirname(__file__), "bin")
add_data = []
if os.path.isdir(bin_dir):
    for fname in os.listdir(bin_dir):
        fpath = os.path.join(bin_dir, fname)
        if os.path.isfile(fpath):
            sep = ";" if sys.platform == "win32" else ":"
            add_data.append(f"--add-binary={fpath}{sep}bin")

args = [
    ENTRY,
    "--onefile",
    "--name", APP_NAME,
    "--noconsole",
    "--clean",
]
if ICON_FILE and os.path.exists(ICON_FILE):
    args += ["--icon", ICON_FILE]
args += add_data

print(f"[MASV Build] Generando ejecutable con PyInstaller...")
print(f"  Nombre   : {APP_NAME}")
print(f"  Entrada  : {ENTRY}")
print(f"  Binarios extras: {len(add_data)}")

import PyInstaller.__main__
PyInstaller.__main__.run(args)

# ── Post-build: empaquetar .tar.gz en Linux ────────────────────────────────
if sys.platform == "linux":
    dist_file = os.path.join("dist", APP_NAME)
    tar_name  = f"{APP_NAME}-Linux.tar.gz"
    if os.path.exists(dist_file):
        import tarfile
        with tarfile.open(tar_name, "w:gz") as tar:
            tar.add(dist_file, arcname=APP_NAME)
        print(f"[MASV Build] Paquete Linux generado: {tar_name}")
    else:
        print(f"[MASV Build] AVISO: No se encontró {dist_file} para empaquetar.")

print(f"\n[MASV Build] ¡Listo! Ejecutable en dist/{APP_NAME}")
