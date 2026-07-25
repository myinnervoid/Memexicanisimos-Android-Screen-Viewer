import os
import sys
import PyInstaller.__main__

def build():
    print("🚀 Iniciando empaquetado con PyInstaller...")
    
    # Detecta el sistema operativo para añadir los binarios correctos
    plat = sys.platform
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bin_path = os.path.join(base_dir, "bin")
    
    # Si la carpeta bin existe, la añade al ejecutable como datos
    if os.path.exists(bin_path) and os.listdir(bin_path):
        # En Windows el separador de paths es ';', en Linux/Mac es ':'
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
        '--name=ScrcpyDock',
        '--collect-all=pystray',
        '--collect-all=PIL',
        main_script
    ]

    if add_data:
        args.insert(args.index(main_script), add_data)

    try:
        PyInstaller.__main__.run(args)
        print("✅ Empaquetado finalizado con éxito. Revisa la carpeta 'dist/'.")
    except Exception as e:
        print(f"❌ Error durante el empaquetado: {e}")

if __name__ == "__main__":
    build()
