"""Ayuda: centro de documentación y los 19 acordeones FAQ."""
from __future__ import annotations

import tkinter as tk

from ...i18n import _
from ...utils import C, FONT_UI, FONT_UI_B, FONT_SM, FONT_LG
from ...ui_widgets import _cmd_chip, AccordionItem, bind_mousewheel

from .common import clear, scrollable


def build(parent, tab) -> None:
    p = parent
    clear(parent)

    tab.faq_items.clear()
    root_ref = tab.ctx.root

    hdr = tk.Frame(p, bg=C["card"], pady=10, padx=16,
                   highlightbackground=C["card_border"], highlightthickness=1)
    hdr.pack(fill="x", padx=12, pady=(8, 4))
    
    tk.Label(hdr, text=_("❓  Centro de Ayuda, Documentación y FAQ"),
             bg=C["card"], fg=C["indigo"], font=FONT_LG).pack(side="left")
    tk.Label(hdr, text=_("Atajo rápido: Ctrl+H"),
             bg=C["card"], fg=C["muted"], font=FONT_SM).pack(side="right")

    inner, canvas = scrollable(p)

    def _add(title, build_fn):
        item = AccordionItem(inner, _(title), build_fn, canvas_ref=canvas)
        item.pack(fill="x", padx=12, pady=3)
        tab.faq_items.append(item)

    # ── 1. Inicio rápido ─────────────────────────────────────────
    def _faq_quickstart(f):
        steps = [
            _("1. Conecta tu teléfono Android a tu computadora con un cable USB de datos de buena calidad."),
            _("2. Activa la Depuración USB en tu Android (ver sección 2 abajo)."),
            _("3. En la pantalla del teléfono, acepta la ventana emergente '¿Permitir depuración USB?'."),
            _("4. Ve a la sección 📱 Dispositivos y pulsa  🔄 Buscar dispositivos."),
            _("5. Selecciona tu teléfono de la lista detectada."),
            _("6. Ve a 🚀 Quick Cast (o Acciones) y pulsa  ▶ INICIAR TRANSMISIÓN.")
        ]
        for s in steps:
            tk.Label(f, text=s, bg=C["bg"], fg=C["text2"], font=FONT_UI,
                     anchor="w", justify="left", wraplength=680).pack(fill="x", padx=16, pady=2)

    _add("🚀  1. Inicio rápido — Primeros pasos con MASV", _faq_quickstart)

    # ── 2. Depuración USB ─────────────────────────────────────────
    def _faq_usb_debug(f):
        tk.Label(f, text=_("Paso 1 — Activa las Opciones de desarrollador:"),
                 bg=C["bg"], fg=C["indigo"], font=FONT_UI_B, anchor="w").pack(fill="x", padx=16, pady=(4, 2))
        for line in [
            _("   a. Abre Ajustes en tu teléfono."),
            _("   b. Ve a 'Acerca del teléfono' → 'Información de software'."),
            _("   c. Toca 7 veces seguidas sobre 'Número de compilación' (Build number)."),
            _("   d. Aparecerá el mensaje: ¡Ahora eres desarrollador!")
        ]:
            tk.Label(f, text=line, bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w").pack(fill="x", padx=16, pady=1)

        tk.Label(f, text=_("Paso 2 — Activa la Depuración USB:"),
                 bg=C["bg"], fg=C["indigo"], font=FONT_UI_B, anchor="w").pack(fill="x", padx=16, pady=(8, 2))
        for line in [
            _("   a. Regresa a Ajustes → Sistema → Opciones para desarrolladores."),
            _("   b. Activa el interruptor 'Depuración USB'."),
            _("   c. Conecta el cable USB a tu PC y marca 'Permitir siempre desde esta computadora'.")
        ]:
            tk.Label(f, text=line, bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w").pack(fill="x", padx=16, pady=1)

    _add("🔌  2. Cómo habilitar la Depuración USB en Android", _faq_usb_debug)

    # ── 3. Dispositivo no detectado ───────────────────────────────
    def _faq_not_found(f):
        tk.Label(f, text=_("Si tu dispositivo no aparece o indica 'unauthorized':"),
                 bg=C["bg"], fg=C["text2"], font=FONT_UI_B).pack(anchor="w", padx=16, pady=4)
        _cmd_chip(f, "adb kill-server", root_ref)
        _cmd_chip(f, "adb start-server", root_ref)
        _cmd_chip(f, "adb devices", root_ref)
        tk.Label(f, text=_("• En Linux: Si no tienes permisos de acceso USB, añade tu usuario al grupo 'plugdev' o instala udev rules."),
                 bg=C["bg"], fg=C["muted"], font=FONT_SM, wraplength=680, justify="left").pack(anchor="w", padx=16, pady=4)

    _add("⚠️  3. El dispositivo no aparece o dice 'no autorizado'", _faq_not_found)

    # ── 4. Dependencias ───────────────────────────────────────────
    def _faq_deps(f):
        for os_name, cmds in [
            (_("🐧 Linux (Debian / Ubuntu / Mint):"), ["sudo apt update", "sudo apt install adb scrcpy"]),
            (_("🐧 Linux (Arch / Manjaro):"), ["sudo pacman -S scrcpy android-tools"]),
            (_("🪟 Windows (winget):"), ["winget install Genymobile.scrcpy"]),
            (_("🍎 macOS (Homebrew):"), ["brew install scrcpy android-platform-tools"]),
        ]:
            tk.Label(f, text=os_name, bg=C["bg"], fg=C["indigo"], font=FONT_UI_B).pack(anchor="w", padx=16, pady=(6, 2))
            for c in cmds: _cmd_chip(f, c, root_ref)

    _add("📦  4. Dependencias necesarias (Instalación de adb y scrcpy)", _faq_deps)

    # ── 5. WiFi TCP/IP ────────────────────────────────────────────
    def _faq_wifi(f):
        steps = [
            _("1. Conecta el teléfono por USB una primera vez para autorizar la huella ADB."),
            _("2. Asegúrate de que el teléfono y la PC estén conectados a la MISMA red Wi-Fi local."),
            _("3. En la sección 📱 Dispositivos → pulsa 'Habilitar TCP/IP (USB→WiFi)'."),
            _("4. Pulsa '📡 Obtener IP' y a continuación pulsa 'Conectar'."),
            _("5. ¡Ya puedes desconectar el cable USB y transmitir de forma inalámbrica!"),
            _("6. Importante: Al iniciar sesión por primera vez, pulsa '🛡️ Confiar y Recordar' para guardarlo en la Bóveda de Confianza y evitar que vuelva a aparecer la advertencia de seguridad en cada inicio.")
        ]
        for s in steps:
            tk.Label(f, text=s, bg=C["bg"], fg=C["text2"], font=FONT_UI,
                     anchor="w", justify="left", wraplength=680).pack(fill="x", padx=16, pady=2)

    _add("📡  5. Conexión inalámbrica por Wi-Fi TCP/IP (sin cables)", _faq_wifi)

    # ── 6. Emparejamiento Seguro Android 11+ ──────────────────────
    def _faq_pair(f):
        steps = [
            _("En Android 11 y versiones superiores no necesitas conectar ningún cable para iniciar Wi-Fi:"),
            _("1. En el teléfono: Ajustes → Opciones de desarrollador → 'Depuración inalámbrica' (activar)."),
            _("2. Toca sobre 'Vincular dispositivo con código de vinculación'."),
            _("3. El teléfono mostrará una IP con un puerto efímero (ej. 192.168.1.50:38291) y un código PIN de 6 dígitos."),
            _("4. En MASV, ingresa esa IP:Puerto y el código de 6 dígitos en la sección 'Emparejamiento Seguro'."),
            _("5. Pulsa '🔒 Emparejar (`adb pair`)' y la conexión quedará autenticada con cifrado TLS.")
        ]
        for s in steps:
            tk.Label(f, text=s, bg=C["bg"], fg=C["text2"], font=FONT_UI,
                     anchor="w", justify="left", wraplength=680).pack(fill="x", padx=16, pady=2)

    _add("🔒  6. Emparejamiento Seguro en Android 11+ (adb pair)", _faq_pair)

    # ── 7. Webcam en OBS ──────────────────────────────────────────
    def _faq_obs(f):
        steps = [
            _("1. En MASV, selecciona el perfil preestablecido 'Webcam HD' o 'Cámara Trasera'."),
            _("2. En Linux: pulsa 'Cargar módulo' en la sección Webcam Virtual para activar v4l2loopback."),
            _("3. Pulsa 'Enrutar cámara → /dev/video9'."),
            _("4. Abre OBS Studio → Fuentes → Añadir '+' → 'Dispositivo de captura de video (V4L2)'."),
            _("5. Selecciona el dispositivo '/dev/video9' y disfruta de tu cámara de celular en 1080p con cero latencia.")
        ]
        for s in steps:
            tk.Label(f, text=s, bg=C["bg"], fg=C["text2"], font=FONT_UI,
                     anchor="w", justify="left", wraplength=680).pack(fill="x", padx=16, pady=2)

    _add("📷  7. Cómo usar la cámara como Webcam en OBS Studio", _faq_obs)

    # ── 8. Pantalla apagada ───────────────────────────────────────
    def _faq_screen_off(f):
        steps = [
            _("• scrcpy permite transmitir la pantalla manteniendo el display físico del teléfono totalmente apagado:"),
            _("  - Ahorra hasta un 80% de batería en sesiones largas de streaming."),
            _("  - Evita que el dispositivo se caliente."),
            _("• Puedes activar esta opción creando o editando un perfil en ⚙️ Perfiles marcando 'Apagar pantalla del dispositivo (--turn-screen-off)'."),
            _("• Para teléfonos Huawei / Honor / EMUI donde scrcpy no apaga la pantalla directamente, activa la casilla de compatibilidad EMUI (Keyevent 26).")
        ]
        for s in steps:
            tk.Label(f, text=s, bg=C["bg"], fg=C["text2"], font=FONT_UI,
                     anchor="w", justify="left", wraplength=680).pack(fill="x", padx=16, pady=2)

    _add("⚡  8. Pantalla apagada mientras transmites (Ahorro de batería)", _faq_screen_off)

    # ── 9. Atajos de teclado ──────────────────────────────────────
    def _faq_shortcuts(f):
        tk.Label(f, text=_("Atajos en la ventana de scrcpy:"), bg=C["bg"], fg=C["indigo"], font=FONT_UI_B).pack(anchor="w", padx=16, pady=(4, 2))
        shortcuts_scrcpy = [
            ("Alt + f", _("Pantalla completa")),
            ("Alt + g", _("Ajustar ventana al tamaño original (1:1)")),
            ("Alt + h", _("Botón Inicio (Home)")),
            ("Alt + b", _("Botón Atrás (Back)")),
            ("Alt + s", _("Selector de aplicaciones recientes")),
            ("Alt + p", _("Encender / Apagar pantalla del dispositivo")),
            ("Alt + r", _("Rotar orientación de pantalla")),
            ("Alt + ↑ / ↓", _("Subir / Bajar volumen")),
        ]
        for sc, desc in shortcuts_scrcpy:
            row = tk.Frame(f, bg=C["bg"])
            row.pack(fill="x", padx=16, pady=1)
            tk.Label(row, text=f"• {sc}:", bg=C["bg"], fg=C["text"], font=FONT_UI_B, width=14, anchor="w").pack(side="left")
            tk.Label(row, text=desc, bg=C["bg"], fg=C["text2"], font=FONT_UI).pack(side="left")

        tk.Label(f, text=_("Atajos en MASV:"), bg=C["bg"], fg=C["indigo"], font=FONT_UI_B).pack(anchor="w", padx=16, pady=(8, 2))
        shortcuts_masv = [
            ("Ctrl + I", _("Iniciar o alternar transmisión de pantalla")),
            ("Ctrl + R", _("Refrescar y escanear dispositivos")),
            ("Ctrl + H", _("Abrir este Centro de Ayuda")),
            ("Ctrl + B", _("Colapsar / Expandir barra lateral (Dashboard)")),
            ("Ctrl + M", _("Alternar Modo Compacto y Avanzado")),
            ("Ctrl + Q", _("Salir con blindaje automático")),
        ]
        for sc, desc in shortcuts_masv:
            row = tk.Frame(f, bg=C["bg"])
            row.pack(fill="x", padx=16, pady=1)
            tk.Label(row, text=f"• {sc}:", bg=C["bg"], fg=C["text"], font=FONT_UI_B, width=14, anchor="w").pack(side="left")
            tk.Label(row, text=desc, bg=C["bg"], fg=C["text2"], font=FONT_UI).pack(side="left")

    _add("⌨  9. Atajos de teclado en MASV y scrcpy", _faq_shortcuts)

    # ── 10. Solución de problemas ─────────────────────────────────
    def _faq_troubleshooting(f):
        tips = [
            (_("Pantalla en negro o scrcpy se cierra de inmediato:"),
             _("Prueba cambiar el códec de video en ⚙️ Perfiles a H.264 o baja la resolución a 1080p o 720p.")),
            (_("Audio no se escucha en PC:"),
             _("La transmisión nativa de audio de scrcpy requiere Android 11 o superior. En Android 10 o inferior selecciona 'mic' como fuente de audio.")),
            (_("Lag o retraso en Wi-Fi:"),
             _("Conecta tu PC por cable Ethernet al router y usa la banda Wi-Fi de 5 GHz en el teléfono con bitrate a 8M.")),
            (_("El puerto 5555 sigue abierto en el teléfono:"),
             _("Pulsa el botón '🛡️ Blindar TCP/IP' o '🔒 Blindar Red' en MASV para ejecutar `adb usb` y cerrar el puerto inmediatamente."))
        ]
        for title, desc in tips:
            tk.Label(f, text=f"• {title}", bg=C["bg"], fg=C["orange"], font=FONT_UI_B, anchor="w").pack(fill="x", padx=16, pady=(4, 1))
            tk.Label(f, text=f"  {desc}", bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w", wraplength=680, justify="left").pack(fill="x", padx=16, pady=(0, 4))

    _add("🛠  10. Solución de problemas comunes y optimización", _faq_troubleshooting)

    # ── 11. Dispositivo en estado Offline ─────────────────────────
    def _faq_offline(f):
        tips = [
            _("El teléfono perdió comunicación con el socket ADB debido a desconexión o suspensión de energía USB."),
            _("Solución: reconecta el cable, asegúrate de que el puerto USB no suspenda la energía y haz clic en 'Reiniciar ADB' en MASV.")
        ]
        for desc in tips:
            tk.Label(f, text=f"• {desc}", bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w", wraplength=680, justify="left").pack(fill="x", padx=16, pady=2)

    _add("🔴  11. Dispositivo en estado Offline", _faq_offline)

    # ── 12. Huawei Y9 y Android 10 ───────────────────────────────
    def _faq_huawei(f):
        tips = [
            _("Android 10 no soporta captura nativa de audio interno en scrcpy (requiere Android 11+), por lo que MASV fuerza automáticamente --no-audio."),
            _("Recomendación: para el chipset Kirin 710, usa el códec H.264 a 8Mbps para obtener mejor rendimiento.")
        ]
        for desc in tips:
            tk.Label(f, text=f"• {desc}", bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w", wraplength=680, justify="left").pack(fill="x", padx=16, pady=2)

    _add("📱  12. Huawei Y9 y Android 10 (Restricciones y Optimización)", _faq_huawei)

    # ── 13. Bóveda y Modo Seguro ─────────────────────────────────
    def _faq_vault(f):
        tips = [
            (_("¿Por qué aparece la advertencia de seguridad al iniciar sesión?"),
             _("En redes Wi-Fi locales o públicas compartidas, cualquier dispositivo podría escanear puertos e intentar conectarse al puerto ADB 5555 abierto de tu teléfono. El Modo Seguro de MASV verifica la huella y serial del dispositivo antes de iniciar la transmisión para garantizar que solo tú tengas acceso a tu teléfono.")),
            (_("¿Cómo desaparecer la advertencia de forma definitiva?"),
             _("Al iniciar la sesión, cuando aparezca el diálogo de seguridad, pulsa '🛡️ Confiar y Recordar'. MASV guardará la identidad del dispositivo en tu Bóveda local (~/.config/masv/config.json). Una vez registrado como Confiable, MASV iniciará todas las transmisiones futuras de forma instantánea sin mostrar advertencias ni ventanas emergentes.")),
            (_("Gestión y Administración de la Bóveda:"),
             _("Puedes abrir en cualquier momento el menú superior 'Dispositivo' → '🛡️ Bóveda de Dispositivos Confiables' para inspeccionar tus teléfonos autorizados, asignarles alias amigables (ej. 'Mi Celular Personal') o revocar la confianza a dispositivos antiguos.")),
            (_("Blindaje de Red (Cierre de Puertos):"),
             _("Usa el blindaje de red (Modo Seguro) para revocar el puerto 5555 ejecutando `adb usb`, cerrando de inmediato el acceso remoto inalámbrico al teléfono."))
        ]
        for title, desc in tips:
            tk.Label(f, text=f"• {title}", bg=C["bg"], fg=C["indigo"], font=FONT_UI_B, anchor="w").pack(fill="x", padx=16, pady=(4, 1))
            tk.Label(f, text=f"  {desc}", bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w", wraplength=680, justify="left").pack(fill="x", padx=16, pady=(0, 4))

    _add("🛡️  13. Importancia de la Bóveda de Dispositivos Confiables y Modo Seguro", _faq_vault)

    # ── 14. Modo Estudio Fotográfico ─────────────────────────────
    def _faq_studio(f):
        tips = [
            _("Puedes usar el feed limpio de la cámara trasera de tu Android en OBS Studio."),
            _("Con la opción Webcam Virtual en Linux, MASV monta la cámara nativamente usando el módulo v4l2loopback para cero latencia.")
        ]
        for desc in tips:
            tk.Label(f, text=f"• {desc}", bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w", wraplength=680, justify="left").pack(fill="x", padx=16, pady=2)

    _add("📷  14. Modo Estudio Fotográfico & Clean Camera Feed", _faq_studio)

    # ── 15. Cierre Limpio vs Bandeja ─────────────────────────────
    def _faq_exit(f):
        tips = [
            _("El botón Salir (o Ctrl+Q) termina por completo la aplicación y el rastreador de dispositivos (Device Tracker)."),
            _("Esto libera de forma limpia los puertos de red y bloqueos, algo útil si otras herramientas necesitan acceder a ADB.")
        ]
        for desc in tips:
            tk.Label(f, text=f"• {desc}", bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w", wraplength=680, justify="left").pack(fill="x", padx=16, pady=2)

    _add("🚪  15. Cierre Limpio vs. Minimizar a la Bandeja", _faq_exit)

    # ── 16. Multidispositivo ──────────────────────────────────────
    def _faq_multidev(f):
        tips = [
            (_("¿Cuántos dispositivos soporta MASV simultáneamente?"),
             _("MASV cuenta con un gestor dinámico de puertos (PortPoolAllocator) en el rango 27183 a 27199, lo que permite conectar y transmitir hasta 16 teléfonos Android al mismo tiempo en ventanas totalmente independientes.")),
            (_("¿Cómo se distribuyen las ventanas?"),
             _("Cada dispositivo corre en su propia ventana individual de scrcpy con título identificador (ej: 'MASV: vivo V2314'), permitiéndote organizarlas libremente en tu monitor, acomodarlas en mosaico o enviarlas a monitores secundarios.")),
            (_("Rendimiento recomendado:"),
             _("En equipos de escritorio con procesadores como el Intel Core i7-8700T, se recomienda mantener de 2 a 4 dispositivos en paralelo a 1080p60 fps para garantizar cero latencia y evitar sobrecalentamiento del procesador."))
        ]
        for title, desc in tips:
            tk.Label(f, text=f"• {title}", bg=C["bg"], fg=C["indigo"], font=FONT_UI_B, anchor="w").pack(fill="x", padx=16, pady=(4, 1))
            tk.Label(f, text=f"  {desc}", bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w", wraplength=680, justify="left").pack(fill="x", padx=16, pady=(0, 4))

    _add("📱  16. Soporte Multidispositivo: ¿Cuántos teléfonos puedo conectar a la vez?", _faq_multidev)

    # ── 17. Modo OTG ──────────────────────────────────────────────
    def _faq_otg(f):
        tips = [
            (_("¿Qué es el Modo OTG?"),
             _("El Modo OTG (On-The-Go) aprovecha la capacidad HID de scrcpy (--otg) para conectar el teclado y ratón de tu PC directamente como periféricos físicos de hardware en tu teléfono Android.")),
            (_("¿Abre ventana de video en la pantalla de la PC?"),
             _("NO. En Modo OTG no se abre ninguna ventana de video en tu computadora. La pantalla del teléfono permanece visible para ti físicamente y respondiendo directamente a tus teclas y clics, con un consumo de CPU prácticamente del 0% en la computadora.")),
            (_("¿Cuándo es útil el Modo OTG?"),
             _("Es ideal para responder mensajes largos de WhatsApp, redactar documentos o jugar con teclado físico mientras tienes tu celular colocado en un soporte sobre tu escritorio."))
        ]
        for title, desc in tips:
            tk.Label(f, text=f"• {title}", bg=C["bg"], fg=C["indigo"], font=FONT_UI_B, anchor="w").pack(fill="x", padx=16, pady=(4, 1))
            tk.Label(f, text=f"  {desc}", bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w", wraplength=680, justify="left").pack(fill="x", padx=16, pady=(0, 4))

    _add("⌨️  17. Modo OTG (Control por Teclado y Ratón sin Pantalla)", _faq_otg)

    # ── 18. Reverse Tethering ─────────────────────────────────────
    def _faq_tether(f):
        tips = [
            (_("¿Qué es el Reverse Tethering (Compartir Internet)?"),
             _("Permite que tu teléfono Android navegue por internet utilizando la conexión cableada o Wi-Fi de tu computadora a través del cable USB mediante la herramienta `gnirehtet`.")),
            (_("¿Cuándo es necesario?"),
             _("Si tu teléfono no tiene SIM de datos, está fuera de alcance Wi-Fi o se encuentra en una zona con mala cobertura, este modo le provee conectividad de alta velocidad al instante a través del cable.")),
            (_("¿Cómo se activa en MASV?"),
             _("Conecta el teléfono por USB y haz clic en el botón '🌐 Compartir Internet (USB)' dentro de la pestaña Dispositivo o en el menú superior Dispositivo. Si ya está activo, al pulsar el botón nuevamente se detiene el túnel."))
        ]
        for title, desc in tips:
            tk.Label(f, text=f"• {title}", bg=C["bg"], fg=C["indigo"], font=FONT_UI_B, anchor="w").pack(fill="x", padx=16, pady=(4, 1))
            tk.Label(f, text=f"  {desc}", bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w", wraplength=680, justify="left").pack(fill="x", padx=16, pady=(0, 4))

    _add("🌐  18. Compartir Internet de PC a Teléfono (Reverse Tethering)", _faq_tether)

    # ── 19. Temas Visuales y Contraste ────────────────────────────
    def _faq_themes(f):
        tips = [
            (_("Paletas disponibles:"),
             _("• Warm Stone (Por defecto): Tonos neutros orgánicos y cálidos inspirados en piedra de cantera.\n• Cyber Obsidian: Modo oscuro profundo de alto contraste.\n• Nordic Slate: Estilo nórdico frío y minimalista.")),
            (_("Cómo cambiar el tema:"),
             _("Ve al menú superior 'Ver' → 'Tema Visual' y selecciona el de tu agrado. MASV te ofrecerá reiniciar o refrescar la interfaz para que todos los bordes, botones y textos mantengan un contraste impecable."))
        ]
        for title, desc in tips:
            tk.Label(f, text=f"• {title}", bg=C["bg"], fg=C["indigo"], font=FONT_UI_B, anchor="w").pack(fill="x", padx=16, pady=(4, 1))
            tk.Label(f, text=f"  {desc}", bg=C["bg"], fg=C["text2"], font=FONT_UI, anchor="w", wraplength=680, justify="left").pack(fill="x", padx=16, pady=(0, 4))

    _add("🎨  19. Temas Visuales y Contraste de Interfaz", _faq_themes)

    # Enlazar scroll a todos los elementos creados y actualizar scrollregion
    canvas.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))
    bind_mousewheel(canvas, canvas)
