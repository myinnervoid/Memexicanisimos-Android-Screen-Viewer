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

    sep = ';' if plat == 'win32' else ':'
    if os.path.exists(bin_path) and os.listdir(bin_path):
        add_data = f"--add-data={bin_path}{sep}bin"
        args.insert(args.index(main_script), add_data)
        safe_print("[MASV] Carpeta 'bin/' detectada. Se incluirá en el ejecutable portátil.")
    else:
        safe_print("[MASV] Carpeta 'bin/' vacía o no encontrada. El ejecutable dependerá del PATH del sistema.")

    assets_path = os.path.join(base_dir, "assets")
    if os.path.exists(assets_path) and os.listdir(assets_path):
        args.insert(args.index(main_script), f"--add-data={assets_path}{sep}assets")
        safe_print("[MASV] Carpeta 'assets/' detectada e incluida en el ejecutable.")

    # Solución específica para Linux: incluir libpython.so explícitamente para evitar error PyInstaller PYI-21058 (dlopen)
    if plat == "linux":
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        candidates = (
            glob.glob(f"/lib/*/libpython{py_ver}*.so*") +
            glob.glob(f"/usr/lib/*/libpython{py_ver}*.so*") +
            glob.glob(f"{sys.base_prefix}/lib/libpython{py_ver}*.so*") +
            glob.glob(f"{sys.base_prefix}/lib/*/libpython{py_ver}*.so*")
        )
        for so_file in candidates:
            if os.path.exists(so_file) and not os.path.islink(so_file):
                # Incluir el archivo binario real y su versión simbólica
                args.insert(args.index(main_script), f"--add-binary={so_file}:.")
                safe_print(f"[MASV] Agregada librería dinámica compartida: {so_file}")

    try:
        PyInstaller.__main__.run(args)
        dist_dir = os.path.join(base_dir, "dist")
        
        if plat == "win32":
            bin_file = os.path.join(dist_dir, "MASV.exe")
            if not os.path.exists(bin_file):
                alt = os.path.join(dist_dir, "MASV")
                if os.path.exists(alt):
                    bin_file = alt
            if not os.path.exists(bin_file):
                raise FileNotFoundError(f"No se encontró el ejecutable Windows en {dist_dir}")

            import zipfile
            zip_path = os.path.join(dist_dir, "MASV-Windows.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(bin_file, arcname="MASV.exe")
                if os.path.isdir(bin_path) and os.listdir(bin_path):
                    for root, _, files in os.walk(bin_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            rel = os.path.relpath(file_path, bin_path)
                            arcname = "bin/" + rel.replace(os.path.sep, '/')
                            zipf.write(file_path, arcname)
                else:
                    safe_print(f"[MASV] No se encontró 'bin/' en {bin_path}; se omite del ZIP.")
            safe_print(f"[MASV] Paquete Windows generado en: {zip_path}")

        elif plat == "darwin":
            import shutil
            app_bundle = os.path.join(dist_dir, "MASV.app")
            bin_file = os.path.join(dist_dir, "MASV")
            if os.path.exists(app_bundle):
                safe_print(f"[MASV] Bundle macOS detectado: {app_bundle}")
                inner_bin = os.path.join(app_bundle, "Contents", "MacOS", "MASV")
                if os.path.exists(inner_bin) and not os.path.exists(bin_file):
                    shutil.copy2(inner_bin, bin_file)
            elif not os.path.exists(bin_file):
                raise FileNotFoundError(f"No se encontró ni MASV.app ni binario MASV en {dist_dir}")
            safe_print("[MASV] Ejecutable macOS listo en dist/.")

        else:
            bin_file = os.path.join(dist_dir, "MASV")
            if not os.path.exists(bin_file):
                raise FileNotFoundError(f"No se encontró el binario Linux en {dist_dir}")
            tar_path = os.path.join(dist_dir, "MASV-Linux.tar.gz")
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(bin_file, arcname="MASV")
                install_sh = os.path.join(base_dir, "install.sh")
                if os.path.exists(install_sh):
                    tar.add(install_sh, arcname="install.sh")
                uninstall_sh = os.path.join(base_dir, "uninstall.sh")
                if os.path.exists(uninstall_sh):
                    tar.add(uninstall_sh, arcname="uninstall.sh")
                if os.path.isdir(assets_path) and os.listdir(assets_path):
                    tar.add(assets_path, arcname="assets")
                if os.path.isdir(bin_path) and os.listdir(bin_path):
                    tar.add(bin_path, arcname="bin")
            safe_print(f"[MASV] Paquete Linux generado en: {tar_path}")

        safe_print("[MASV] Empaquetado finalizado con éxito en 'dist/'.")
    except Exception as e:
        safe_print(f"❌ Error durante el empaquetado: {e}")
        raise

if __name__ == "__main__":
    build()
