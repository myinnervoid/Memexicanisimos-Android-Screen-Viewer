"""AdbEngine · Adaptador de bajo nivel para ADB.

Contrato v1 congelado — ver ADR-006, ADR-007, ADR-008, ADR-009.
NO cambiar firmas sin reabrir el ADR.

Estado del módulo:
  ✅ __init__, _env_with_socket, _try_start_server, _is_bind_failure
  ✅ start_daemon (Sesión A)
  ✅ stop_tracker (Idempotente)
  🟡 list_devices (TODO-2)
  🟡 get_properties (TODO-3)
  🟡 tcpip / revert / wifi / tracker (TODO-4)
"""
from __future__ import annotations

import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional

from scrcpy_dock.contracts import OperationResult
from scrcpy_dock.errors import ErrorCode
from scrcpy_dock.domain.models import (
    ConnectionType,
    Device,
    DeviceState,
)
from scrcpy_dock.domain.protocols import TrackerHandle

log = logging.getLogger(__name__)

# Orden exacto requerido por tests/contracts/helpers.py GETPROPS_HUAWEI_Y9_FIXTURE.
_PROPS: tuple[str, ...] = (
    "ro.build.version.sdk",
    "ro.build.version.release",
    "ro.product.manufacturer",
    "ro.product.model",
    "ro.board.platform",
)

# Propiedades adicionales que se consultan en el MISMO shell pero
# NO forman parte del dict de salida. Solo alimentan fallbacks internos.
_PROPS_INTERNAL_FALLBACK: tuple[str, ...] = ("ro.hardware",)

_BIND_FAILURE_MARKERS = ("cannot bind", "address already in use")

_DEVICE_STATE_MAP: dict[str, DeviceState] = {
    "device": DeviceState.DEVICE,
    "unauthorized": DeviceState.UNAUTHORIZED,
    "offline": DeviceState.OFFLINE,
}


class AdbEngine:
    """Wrapper robusto sobre el binario oficial `adb` de Platform-Tools."""

    def __init__(
        self,
        adb_binary: Path,
        preferred_socket_port: int = 5037,
        fallback_socket_port: int = 5038,
    ) -> None:
        self._adb_binary = Path(adb_binary)
        self._preferred_socket_port = preferred_socket_port
        self._fallback_socket_port = fallback_socket_port

        # Estado del daemon (ADR-006)
        self._effective_port: int = 0
        self._daemon_started: bool = False

        # Estado de tcpip (ADR-009)
        self._activated_by_masv: set[str] = set()

        # Tracker (ADR-008)
        self._tracker: Optional[TrackerHandle] = None

    # ────────────────────────────────────────────────────────────────────
    # Helpers internos
    # ────────────────────────────────────────────────────────────────────

    def _env_with_socket(self, port: int | None = None) -> dict[str, str]:
        """Devuelve env con ADB_SERVER_SOCKET apuntando al puerto efectivo.

        Prioridad: port explícito → _effective_port → _preferred_socket_port.
        """
        chosen = port or self._effective_port or self._preferred_socket_port
        return {**os.environ, "ADB_SERVER_SOCKET": f"tcp:localhost:{chosen}"}

    def _try_start_server(self, port: int) -> OperationResult[None]:
        """Un único intento de `adb start-server` en un puerto dado."""
        try:
            proc = subprocess.run(
                [str(self._adb_binary), "start-server"],
                capture_output=True,
                text=True,
                timeout=10,
                env=self._env_with_socket(port),
            )
        except FileNotFoundError as e:
            return OperationResult.fail(ErrorCode.ADB_NOT_FOUND, str(e))
        except subprocess.TimeoutExpired as e:
            return OperationResult.fail(
                ErrorCode.ADB_SERVER_FAILED, f"timeout: {e}",
            )
        except OSError as e:
            return OperationResult.fail(ErrorCode.ADB_SERVER_FAILED, str(e))

        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "start-server falló").strip()
            return OperationResult.fail(ErrorCode.ADB_SERVER_FAILED, msg)
        return OperationResult.ok(None, f"daemon listo en {port}")

    @staticmethod
    def _is_bind_failure(message: str | None) -> bool:
        if not message:
            return False
        low = message.lower()
        return any(marker in low for marker in _BIND_FAILURE_MARKERS)

    # ────────────────────────────────────────────────────────────────────
    # API pública · contratos congelados
    # ────────────────────────────────────────────────────────────────────

    @property
    def effective_socket_port(self) -> int:
        return self._effective_port

    # ─── Sesión A · start_daemon (ADR-006) ──────────────────────────────
    def start_daemon(self) -> OperationResult[int]:
        """Arranca/verifica el daemon ADB.

        Contrato:
          - Idempotente: segunda llamada NO invoca subprocess.
          - 2 fallos consecutivos con 'cannot bind' en 5037 → saltar a 5038.
          - Si 5038 también falla → ErrorCode.ADB_DAEMON_DEAD.
          - Errores que NO son bind → propagar sin reintentar.
        """
        if self._daemon_started:
            return OperationResult.ok(self._effective_port, "ya activo")

        for port in (self._preferred_socket_port, self._fallback_socket_port):
            failures = 0
            for attempt in range(2):
                res = self._try_start_server(port)
                if res.success:
                    self._effective_port = port
                    self._daemon_started = True
                    return OperationResult.ok(port, f"daemon en {port}")

                if not self._is_bind_failure(res.message):
                    # Si no es un error de bind (ej. ADB_NOT_FOUND), no reintentar
                    return OperationResult.fail(
                        res.error_code or ErrorCode.ADB_SERVER_FAILED,
                        res.message,
                    )

                failures += 1
                if failures >= 2:
                    break

        return OperationResult.fail(
            ErrorCode.ADB_DAEMON_DEAD,
            "5037 y 5038 no disponibles",
        )

    # ─── Sesión B · list_devices ───────────────────────────────────────
    def list_devices(self) -> OperationResult[list[Device]]:
        """Ejecuta `adb devices -l` y devuelve lista tipada.

        Contrato:
          - Ignorar cabecera 'List of devices attached' y líneas vacías.
          - Mapear: 'device'→DEVICE, 'unauthorized'→UNAUTHORIZED,
                    'offline'→OFFLINE. Otros estados → log.warning + skip.
          - Extraer model desde token 'model:XXX' si existe; si no, usar serial.
          - android_sdk=0 como placeholder (se resuelve lazy vía get_properties).

        Tests:
          test_parses_all_three_states
          test_empty_output_returns_empty_list_not_error   ← debe dar [], no None
        """
        try:
            proc = subprocess.run(
                [str(self._adb_binary), "devices", "-l"],
                capture_output=True,
                text=True,
                timeout=10,
                env=self._env_with_socket(),
            )
        except FileNotFoundError as e:
            return OperationResult.fail(ErrorCode.ADB_NOT_FOUND, str(e))
        except subprocess.TimeoutExpired as e:
            return OperationResult.fail(
                ErrorCode.ADB_SERVER_FAILED, f"timeout: {e}",
            )

        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "devices -l falló").strip()
            return OperationResult.fail(ErrorCode.ADB_SERVER_FAILED, msg)

        devices: list[Device] = []
        for raw_line in proc.stdout.splitlines():
            device = self._parse_device_line(raw_line)
            if device is not None:
                devices.append(device)
            elif raw_line.strip() and not raw_line.startswith("List of devices"):
                # Línea con contenido pero estado desconocido → avisar
                log.warning("Línea ADB no reconocida: %r", raw_line)

        return OperationResult.ok(devices, f"{len(devices)} dispositivo(s)")

    @staticmethod
    def _parse_device_line(line: str) -> Optional[Device]:
        """Parser puro · reutilizado por list_devices y _TrackerThread.

        Devuelve None si la línea es cabecera, vacía, o tiene estado desconocido.
        NO loggea; el caller decide qué hacer con el None.

        Formato esperado (adb devices -l):
          <serial> <state> [key:value ...]
        """
        stripped = line.strip()
        if not stripped:
            return None
        if stripped.startswith("List of devices"):
            return None

        parts = stripped.split()
        if len(parts) < 2:
            return None

        serial = parts[0]
        raw_state = parts[1]

        state = _DEVICE_STATE_MAP.get(raw_state)
        if state is None:
            return None

        # Buscar model:XXX entre los tokens opcionales
        model = serial
        for token in parts[2:]:
            if token.startswith("model:"):
                model = token[len("model:"):]
                break

        return Device(
            serial=serial,
            model=model,
            android_sdk=0,                      # placeholder lazy
            state=state,
            connection_type=ConnectionType.USB, # adb devices -l no distingue aquí
        )

    # ─── Sesión C · get_properties ─────────────────────────────────────
    def get_properties(self, serial: str) -> OperationResult[dict[str, str]]:
        """Lee en UNA sola invocación ADB las props necesarias.

        Contrato duro: EXACTAMENTE 1 llamada a subprocess.run.
        """
        all_props = _PROPS + _PROPS_INTERNAL_FALLBACK
        shell_cmd = "; ".join(f"getprop {p}" for p in all_props)

        try:
            proc = subprocess.run(
                [str(self._adb_binary), "-s", serial, "shell", shell_cmd],
                capture_output=True,
                text=True,
                timeout=10,
                env=self._env_with_socket(),
            )
        except FileNotFoundError as e:
            return OperationResult.fail(ErrorCode.ADB_NOT_FOUND, str(e))
        except subprocess.TimeoutExpired as e:
            return OperationResult.fail(
                ErrorCode.ADB_SERVER_FAILED, f"timeout: {e}",
            )

        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "getprop falló").strip()
            # El dispositivo puede no existir o estar offline
            return OperationResult.fail(ErrorCode.DEVICE_NOT_FOUND, msg)

        # Parseo: cada getprop emite exactamente 1 línea (posiblemente vacía).
        # zip tolera que el mock devuelva MENOS líneas de las consultadas.
        lines = proc.stdout.splitlines()
        raw: dict[str, str] = {}
        for key, line in zip(all_props, lines):
            raw[key] = line.strip()
        for key in all_props:
            raw.setdefault(key, "")

        # Fallback: ro.board.platform → ro.hardware
        platform = raw.get("ro.board.platform") or raw.get("ro.hardware", "")

        # Dict de salida · SOLO las 5 props canónicas del contrato
        props: dict[str, str] = {
            "ro.build.version.sdk":     raw.get("ro.build.version.sdk", ""),
            "ro.build.version.release": raw.get("ro.build.version.release", ""),
            "ro.product.manufacturer":  raw.get("ro.product.manufacturer", ""),
            "ro.product.model":         raw.get("ro.product.model", ""),
            "ro.board.platform":        platform,
        }

        return OperationResult.ok(
            props,
            f"props leídas para {serial}",
        )

    # ─── Sesión D · start_tcpip (ADR-009) ──────────────────────────────
    def start_tcpip(
        self, serial: str, port: int = 5555,
    ) -> OperationResult[None]:
        """`adb -s <serial> tcpip <port>`.

        Contrato:
          - Marcar self._activated_by_masv.add(serial) SOLO tras éxito.
          - Un fallo NO marca el serial → revert_tcpip posterior será no-op.
        """
        try:
            proc = subprocess.run(
                [str(self._adb_binary), "-s", serial, "tcpip", str(port)],
                capture_output=True,
                text=True,
                timeout=10,
                env=self._env_with_socket(),
            )
        except FileNotFoundError as e:
            return OperationResult.fail(ErrorCode.ADB_NOT_FOUND, str(e))
        except subprocess.TimeoutExpired as e:
            return OperationResult.fail(
                ErrorCode.ADB_SERVER_FAILED, f"timeout: {e}",
            )

        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "tcpip falló").strip()
            return OperationResult.fail(ErrorCode.ADB_SERVER_FAILED, msg)

        self._activated_by_masv.add(serial)
        return OperationResult.ok(None, f"{serial} en tcpip:{port}")

    # ─── Sesión D · revert_tcpip (ADR-009) ──────────────────────────────
    def revert_tcpip(self, serial: str) -> OperationResult[None]:
        """Revierte tcpip a USB SOLO si MASV lo activó.

        Contrato CRÍTICO:
          - Early-return ANTES de cualquier subprocess.run si
            serial NOT IN self._activated_by_masv.
          - El test verifica que 'usb' NO aparece en ningún call.args.

        Tests:
          test_revert_skips_when_not_activated_by_masv
          test_revert_runs_when_activated_by_masv
        """
        if serial not in self._activated_by_masv:
            return OperationResult.ok(
                None, f"{serial} no fue activado por MASV · no-op",
            )

        try:
            proc = subprocess.run(
                [str(self._adb_binary), "-s", serial, "usb"],
                capture_output=True,
                text=True,
                timeout=10,
                env=self._env_with_socket(),
            )
        except FileNotFoundError as e:
            return OperationResult.fail(ErrorCode.ADB_NOT_FOUND, str(e))
        except subprocess.TimeoutExpired as e:
            return OperationResult.fail(
                ErrorCode.LOCKDOWN_FAILED, f"timeout: {e}",
            )

        # Pase lo que pase, ya no consideramos el serial bajo control de MASV.
        self._activated_by_masv.discard(serial)

        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "usb revert falló").strip()
            # ADR-009 · Falso negativo conocido:
            # `adb usb` cierra el socket TCP durante la transición a USB.
            # EMUI/Android 10 devuelve 'error: closed' con el efecto deseado.
            # Tratamos estos patrones como éxito funcional.
            _TRANSPORT_TRANSITION_MARKERS = (
                "error: closed",
                "connection reset by peer",
                "device not found",
            )
            is_transition = any(m in msg.lower() for m in _TRANSPORT_TRANSITION_MARKERS) or (
                "device" in msg.lower() and "not found" in msg.lower()
            )
            if is_transition:
                log.info(
                    "revert_tcpip(%s): transición de transporte (esperado) · %s",
                    serial,
                    msg,
                )
                return OperationResult.ok(
                    None, f"{serial} revertido a USB (transición)",
                )

            return OperationResult.fail(ErrorCode.LOCKDOWN_FAILED, msg)

        return OperationResult.ok(None, f"{serial} revertido a USB")

    # ─── Sesión D · connect_wifi / disconnect_wifi ──────────────────────
    def connect_wifi(
        self, host: str, port: int = 5555,
    ) -> OperationResult[str]:
        """`adb connect host:port`. Devuelve el serial resultante."""
        endpoint = f"{host}:{port}"
        try:
            proc = subprocess.run(
                [str(self._adb_binary), "connect", endpoint],
                capture_output=True,
                text=True,
                timeout=15,
                env=self._env_with_socket(),
            )
        except FileNotFoundError as e:
            return OperationResult.fail(ErrorCode.ADB_NOT_FOUND, str(e))
        except subprocess.TimeoutExpired as e:
            return OperationResult.fail(
                ErrorCode.CONNECTION_REFUSED, f"timeout: {e}",
            )

        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "connect falló").strip()
            return OperationResult.fail(ErrorCode.CONNECTION_REFUSED, msg)

        # `adb connect` a veces retorna 0 con "unable to connect" en stdout.
        out = (proc.stdout or "").strip()
        if "unable to connect" in out.lower() or "failed" in out.lower():
            return OperationResult.fail(ErrorCode.CONNECTION_REFUSED, out)

        return OperationResult.ok(endpoint, out or f"conectado a {endpoint}")

    def disconnect_wifi(self, serial: str) -> OperationResult[None]:
        """`adb disconnect <serial>`. No-op silencioso si no existe."""
        try:
            proc = subprocess.run(
                [str(self._adb_binary), "disconnect", serial],
                capture_output=True,
                text=True,
                timeout=10,
                env=self._env_with_socket(),
            )
        except FileNotFoundError as e:
            return OperationResult.fail(ErrorCode.ADB_NOT_FOUND, str(e))
        except subprocess.TimeoutExpired as e:
            return OperationResult.fail(
                ErrorCode.CONNECTION_REFUSED, f"timeout: {e}",
            )

        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "disconnect falló").strip()
            return OperationResult.fail(ErrorCode.CONNECTION_REFUSED, msg)

        return OperationResult.ok(None, f"{serial} desconectado")

    # ─── TODO-4d · tracker reactivo (ADR-008) ──────────────────────────
    def track_devices_async(
        self,
        on_change: Callable[[list[Device]], None],
        on_daemon_dead: Callable[[ErrorCode], None],
        max_reconnect_attempts: int = 5,
    ) -> OperationResult[TrackerHandle]:
        """Hilo centinela con `adb track-devices` + reconexión backoff.

        Contrato:
          - on_change(list[Device]) en cada evento.
          - Si el daemon muere → reintento con backoff [1,2,4,8,16]s.
          - Agotados los intentos → on_daemon_dead(ADB_DAEMON_DEAD).

        NO cubierto por tests unitarios → validar con smoke manual (5 pasos).
        """
        if self._tracker is not None and self._tracker.is_alive():
            return OperationResult.fail(
                ErrorCode.DEVICE_BUSY, "tracker ya activo",
            )

        tracker = _TrackerThread(
            adb_binary=self._adb_binary,
            port=self._effective_port or self._preferred_socket_port,
            on_change=on_change,
            on_daemon_dead=on_daemon_dead,
            max_attempts=max_reconnect_attempts,
            parse_line=self._parse_device_line,  # reutiliza parser de TODO-2
        )
        tracker.start()
        self._tracker = tracker
        return OperationResult.ok(tracker, "tracker iniciado")

    def stop_tracker(self) -> None:
        """Detiene tracker si está vivo. Idempotente."""
        if self._tracker is not None:
            self._tracker.stop(timeout=2.0)
            self._tracker = None


# ────────────────────────────────────────────────────────────────────
# TODO-4e · _TrackerThread (implementación del hilo centinela)
# ────────────────────────────────────────────────────────────────────

class _TrackerThread(threading.Thread):
    """Hilo daemon que corre `adb track-devices` y notifica vía callback.

    Protocolo `adb track-devices`: cada evento emite un bloque:
      <4 hex dígitos: longitud>\n
      <payload de N bytes>

    El payload replica el formato de `adb devices` sin cabecera:
      serial\tstate\n[serial\tstate\n...]

    Nota: el protocolo NO incluye `model:` (eso es exclusivo de `-l`).
    El parser recibe líneas con 2 campos y devuelve Device con model=serial.
    """

    def __init__(
        self,
        adb_binary: Path,
        port: int,
        on_change: Callable[[list[Device]], None],
        on_daemon_dead: Callable[[ErrorCode], None],
        max_attempts: int = 5,
        parse_line: Callable[[str], Optional[Device]] | None = None,
    ) -> None:
        super().__init__(daemon=True, name="adb-track-devices")
        self._adb_binary = Path(adb_binary)
        self._port = port
        self._on_change = on_change
        self._on_daemon_dead = on_daemon_dead
        self._max_attempts = max_attempts
        self._parse_line = parse_line or self._default_parse_line
        self._stop_event = threading.Event()
        self._env = {
            **os.environ,
            "ADB_SERVER_SOCKET": f"tcp:localhost:{port}",
        }

    @staticmethod
    def _default_parse_line(line: str) -> Optional[Device]:
        """Fallback por si no se inyecta el parser del engine."""
        stripped = line.strip()
        if not stripped:
            return None
        parts = stripped.split()
        if len(parts) < 2:
            return None
        serial, raw_state = parts[0], parts[1]
        state = _DEVICE_STATE_MAP.get(raw_state)
        if state is None:
            return None
        return Device(
            serial=serial,
            model=serial,
            android_sdk=0,
            state=state,
            connection_type=ConnectionType.USB,
        )

    def run(self) -> None:
        attempts = 0
        while not self._stop_event.is_set() and attempts < self._max_attempts:
            exited_normally = self._run_once()
            if self._stop_event.is_set():
                return
            if exited_normally and attempts == 0:
                # track-devices salió tras una operación normal → daemon sano
                # pero stream cerrado. Reintentar sin penalización de backoff.
                attempts = max(0, attempts - 1)

            attempts += 1
            if attempts >= self._max_attempts:
                break

            backoff = 2 ** (attempts - 1)  # 1, 2, 4, 8, 16
            log.warning(
                "track-devices reintento %d/%d en %ds",
                attempts,
                self._max_attempts,
                backoff,
            )
            # Espera interrumpible
            if self._stop_event.wait(timeout=backoff):
                return

        if attempts >= self._max_attempts:
            log.error("track-devices agotó reintentos · daemon muerto")
            try:
                self._on_daemon_dead(ErrorCode.ADB_DAEMON_DEAD)
            except Exception:
                log.exception("on_daemon_dead lanzó excepción")

    def _run_once(self) -> bool:
        """Una sesión de `track-devices`. Devuelve True si salió por EOF limpio."""
        proc: subprocess.Popen | None = None
        try:
            proc = subprocess.Popen(
                [str(self._adb_binary), "track-devices"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self._env,
                bufsize=1,  # line-buffered
            )
        except (FileNotFoundError, OSError) as e:
            log.error("track-devices no se pudo lanzar: %s", e)
            return False

        try:
            while not self._stop_event.is_set():
                # Leer cabecera de longitud: exactamente 4 dígitos hex (sin \n intermedio)
                header = proc.stdout.read(4)
                if not header:
                    # EOF · adb track-devices murió
                    break
                if len(header) < 4:
                    log.warning("track-devices: cabecera incompleta %r", header)
                    break

                try:
                    payload_len = int(header, 16)
                except ValueError:
                    log.warning("track-devices: cabecera inválida %r", header)
                    continue

                if payload_len <= 0:
                    # Evento "sin dispositivos" o vacío
                    self._on_change([])
                    continue

                payload = proc.stdout.read(payload_len)
                if not payload:
                    break

                devices: list[Device] = []
                for raw in payload.splitlines():
                    dev = self._parse_line(raw)
                    if dev is not None:
                        devices.append(dev)

                try:
                    self._on_change(devices)
                except Exception:
                    log.exception("on_change lanzó excepción")
        finally:
            # Asegurar limpieza del subprocess
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
            return proc.returncode == 0

    def stop(self, timeout: float = 2.0) -> None:
        """Detiene el hilo. Idempotente."""
        self._stop_event.set()
        if self.is_alive():
            self.join(timeout=timeout)
