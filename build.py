import os
import sys
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
        # Fallback sin emojis para consolas Windows restringidas a cp1252
        clean_msg = msg.encode('ascii', errors='ignore').decode('ascii')
        print(clean_msg)

def build():
    safe_print("[MASV] Iniciando empaquetado con PyInstaller...")
    
    plat = sys.platform
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bin_path = os.path.join(base_dir, "bin")
    
    if os.path.exists(bin_path) and os.listdir(bin_path):
        sep = ';' if plat == 'win32' else ':'
        add_data = f"--add-data={bin_path}{sep}bin"
        safe_print("[MASV] Carpeta 'bin/' detectada. Se incluirá en el ejecutable portátil.")
    else:
        add_data = ""
        safe_print("[MASV] Carpeta 'bin/' vacía o no encontrada. El ejecutable dependerá del PATH del sistema.")
        
    main_script = os.path.join(base_dir, "run.py")

    args = [
        '--onefile',
        '--windowed',
        '--name=MASV',
        '--collect-all=pystray',
        '--collect-all=PIL',
        main_script
    ]

    if add_data:
        args.insert(args.index(main_script), add_data)

    try:
        PyInstaller.__main__.run(args)
        dist_dir = os.path.join(base_dir, "dist")
        bin_file = os.path.join(dist_dir, "MASV" + (".exe" if plat == "win32" else ""))
        
        if os.path.exists(bin_file):
            if plat != "win32":
                tar_path = os.path.join(dist_dir, "MASV-Linux.tar.gz")
                with tarfile.open(tar_path, "w:gz") as tar:
                    tar.add(bin_file, arcname="MASV")
                    if os.path.exists(bin_path) and os.listdir(bin_path):
                        tar.add(bin_path, arcname="bin")
                safe_print(f"[MASV] Paquete comprimido generado en: {tar_path}")
            else:
                import zipfile
                zip_path = os.path.join(dist_dir, "MASV-Windows.zip")
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(bin_file, arcname="MASV.exe")
                    if os.path.exists(bin_path) and os.listdir(bin_path):
                        for root, _, files in os.walk(bin_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, base_dir)
                                zipf.write(file_path, arcname)
                safe_print(f"[MASV] Paquete comprimido generado en: {zip_path}")
            
        safe_print("[MASV] Empaquetado finalizado con éxito en 'dist/'.")
    except Exception as e:
        safe_print(f"[MASV] Error durante el empaquetado: {e}")

if __name__ == "__main__":
    build()
