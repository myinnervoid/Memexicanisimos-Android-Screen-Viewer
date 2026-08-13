import os
import sys
import glob
import tarfile

# Configurar encoding seguro para consolas de Windows (evita UnicodeEncodeError cp1252)
if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
if hasattr(sys.stderr, 'reconfigure'):
    try: sys.stderr.reconfigure(encoding='utf-8')
    except Exception: pass

import PyInstaller.__main__

def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        clean_msg = msg.encode('ascii', errors='ignore').decode('ascii')
        print(clean_msg)

def build():
    safe_print("[MASV] Iniciando empaquetado con PyInstaller...")
    
    plat = sys.platform
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bin_path = os.path.join(base_dir, "bin")
    
    main_script = os.path.join(base_dir, "run.py")

    args = [
        '--onefile',
        '--windowed',
        '--name=MASV',
        '--collect-all=pystray',
        '--collect-all=PIL',
        main_script
    ]

    if os.path.exists(bin_path) and os.listdir(bin_path):
        sep = ';' if plat == 'win32' else ':'
        add_data = f"--add-data={bin_path}{sep}bin"
        args.insert(args.index(main_script), add_data)
        safe_print("[MASV] Carpeta 'bin/' detectada. Se incluirá en el ejecutable portátil.")
    else:
        safe_print("[MASV] Carpeta 'bin/' vacía o no encontrada. El ejecutable dependerá del PATH del sistema.")

    # Solución específica para Linux: incluir libpython.so explícitamente para evitar error PyInstaller PYI-21058 (dlopen)
    if plat == "linux":
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        candidates = glob.glob(f"/lib/*/libpython{py_ver}*.so*") + glob.glob(f"/usr/lib/*/libpython{py_ver}*.so*")
        for so_file in candidates:
            if os.path.exists(so_file) and not os.path.islink(so_file):
                # Incluir el archivo binario real y su versión simbólica
                args.insert(args.index(main_script), f"--add-binary={so_file}:.")
                safe_print(f"[MASV] Agregada librería dinámica compartida: {so_file}")

    try:
        PyInstaller.__main__.run(args)
        dist_dir = os.path.join(base_dir, "dist")
        bin_file = os.path.join(dist_dir, "MASV" + (".exe" if plat == "win32" else ""))
        
        if os.path.exists(bin_file):
            if plat != "win32":
                tar_path = os.path.join(dist_dir, "MASV-Linux.tar.gz")
                with tarfile.open(tar_path, "w:gz") as tar:
                    tar.add(bin_file, arcname="MASV")
                safe_print(f"[MASV] Paquete comprimido generado en: {tar_path}")
            safe_print("[MASV] Empaquetado finalizado con éxito en 'dist/'.")
        else:
            safe_print("❌ No se encontró el binario generado en dist/")
    except Exception as e:
        safe_print(f"❌ Error durante el empaquetado: {e}")

if __name__ == "__main__":
    build()
