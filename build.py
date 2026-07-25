import os
import sys
import tarfile
import PyInstaller.__main__

def build():
    print("🚀 Iniciando empaquetado de MASV con PyInstaller...")
    
    plat = sys.platform
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bin_path = os.path.join(base_dir, "bin")
    
    if os.path.exists(bin_path) and os.listdir(bin_path):
        sep = ';' if plat == 'win32' else ':'
        add_data = f"--add-data={bin_path}{sep}bin"
        print(f"📦 Carpeta 'bin/' detectada. Se incluirá en el ejecutable portátil.")
    else:
        add_data = ""
        print(f"⚠ Carpeta 'bin/' vacía o no encontrada. El ejecutable dependerá del PATH del sistema.")
        
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
        
        if plat != "win32" and os.path.exists(bin_file):
            tar_path = os.path.join(dist_dir, "MASV-Linux.tar.gz")
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(bin_file, arcname="MASV")
            print(f"📦 Paquete comprimido generado en: {tar_path}")
            
        print("✅ Empaquetado de MASV finalizado con éxito en 'dist/'.")
    except Exception as e:
        print(f"❌ Error durante el empaquetado: {e}")

if __name__ == "__main__":
    build()
