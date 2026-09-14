"""InstallerService · Layout ~/.MASV/ y resolución de binarios.

Contrato v1 congelado — ver ADR-018, ADR-019.
NO cambiar firmas sin reabrir el ADR correspondiente.
"""
from __future__ import annotations

import logging
import os
import shutil
import stat
import textwrap
from pathlib import Path
from typing import Callable, Optional

from scrcpy_dock.contracts import OperationResult
from scrcpy_dock.errors import ErrorCode


log = logging.getLogger(__name__)


_MASV_DIRNAME = ".MASV"
_SUBDIRS = ("bin", "assets", "config", "logs")
_DESKTOP_FILENAME = "MASV.desktop"
_BIN_SYMLINK_NAME = "MASV"


class InstallerService:
    """Gestión del layout ~/.MASV/ y resolución de binarios.

    Responsabilidades:
      - resolve_binary(name) con prioridad ~/.MASV/bin/ > $PATH.
      - ensure_layout(): crear ~/.MASV/{bin,assets,config,logs}.
      - write_desktop_entry(): crear ~/.local/bin/MASV + .desktop.
      - uninstall(purge=False): eliminar enlaces XDG; purga opcional.

    NO responsabilidades:
      - Descargar binarios (fuera de scope v1).
      - Compilar v4l2loopback (fuera de scope v1).
      - Tocar la UI.
    """

    def __init__(
        self,
        home: Path | None = None,
        xdg_data_home: Path | None = None,
        which_fn: Callable[[str], Optional[str]] = shutil.which,
    ) -> None:
        self._home = Path(home) if home else Path.home()
        self._xdg_data_home = (
            Path(xdg_data_home)
            if xdg_data_home
            else Path(os.environ.get(
                "XDG_DATA_HOME", self._home / ".local" / "share",
            ))
        )
        self._which = which_fn

    # ────────────────────────────────────────────────────────────────────
    # Propiedades y helpers internos
    # ────────────────────────────────────────────────────────────────────

    @property
    def masv_root(self) -> Path:
        return self._home / _MASV_DIRNAME

    @property
    def bin_dir(self) -> Path:
        return self.masv_root / "bin"

    @property
    def assets_dir(self) -> Path:
        return self.masv_root / "assets"

    @property
    def config_dir(self) -> Path:
        return self.masv_root / "config"

    @property
    def logs_dir(self) -> Path:
        return self.masv_root / "logs"

    @property
    def desktop_entry_path(self) -> Path:
        return self._xdg_data_home / "applications" / _DESKTOP_FILENAME

    @property
    def bin_symlink_path(self) -> Path:
        return self._home / ".local" / "bin" / _BIN_SYMLINK_NAME

    @staticmethod
    def _is_executable(path: Path) -> bool:
        return path.is_file() and os.access(path, os.X_OK)

    def _render_desktop_entry(self, exec_path: Path, icon_path: Path) -> str:
        """Plantilla del .desktop (XDG Desktop Entry spec)."""
        return textwrap.dedent(f"""\
            [Desktop Entry]
            Type=Application
            Name=MASV
            GenericName=Android Screen Viewer
            Comment=Mirror and control Android devices
            Exec={exec_path}
            Icon={icon_path}
            Terminal=false
            Categories=Utility;Development;
            StartupNotify=true
        """)

    # ────────────────────────────────────────────────────────────────────
    # API pública · contratos congelados
    # ────────────────────────────────────────────────────────────────────

    # ─── TODO-I1 · resolve_binary ────────────────────────────────────
    def resolve_binary(self, name: str) -> OperationResult[Path]:
        """Resuelve el path absoluto de un binario.

        Contrato de búsqueda:
          1. ~/.MASV/bin/<name> si existe Y es ejecutable.
          2. shutil.which(<name>) sobre $PATH.
          3. Fail(BINARY_NOT_FOUND) si ninguna coincide.

        Contrato de forma:
          - name vacío o con '/' → fail(INVALID_INPUT).
          - Path devuelto siempre absoluto.
          - No lanza excepción en ningún caso.
        """
        if not name or "/" in name:
            return OperationResult.fail(
                ErrorCode.INVALID_INPUT, f"nombre de binario inválido: {name!r}",
            )

        # 1. ~/.MASV/bin/
        local = self.bin_dir / name
        if self._is_executable(local):
            return OperationResult.ok(local.absolute(), f"local: {local}")

        # 2. $PATH
        found = self._which(name)
        if found:
            return OperationResult.ok(Path(found).absolute(), f"PATH: {found}")

        # 3. No encontrado
        return OperationResult.fail(
            ErrorCode.BINARY_NOT_FOUND, f"binario {name!r} no encontrado",
        )

    # ─── TODO-I2 · ensure_layout ─────────────────────────────────────
    def ensure_layout(self) -> OperationResult[None]:
        """Crea ~/.MASV/{bin,assets,config,logs} si no existen.

        Contrato:
          - Idempotente: llamar dos veces no falla.
          - Directorios creados con permisos por defecto del umask.
          - Falla con DEPENDENCY_INSTALL_FAILED si no se puede crear.
        """
        try:
            for sub in _SUBDIRS:
                (self.masv_root / sub).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return OperationResult.fail(
                ErrorCode.DEPENDENCY_INSTALL_FAILED, f"Error creando layout ~/.MASV/: {e}",
            )
        return OperationResult.ok(None, f"layout creado en {self.masv_root}")

    # ─── TODO-I3 · write_desktop_entry ───────────────────────────────
    def write_desktop_entry(
        self,
        exec_path: Path,
        icon_path: Path,
    ) -> OperationResult[None]:
        """Crea el .desktop y el symlink en ~/.local/bin.

        Contrato:
          - Crea ~/.local/share/applications/ y ~/.local/bin/ si faltan.
          - Escribe MASV.desktop con Exec e Icon absolutos.
          - Crea symlink ~/.local/bin/MASV → exec_path.
          - Sobreescribe versiones previas sin fallar.
          - Idempotente.
        """
        try:
            self.desktop_entry_path.parent.mkdir(parents=True, exist_ok=True)
            self.bin_symlink_path.parent.mkdir(parents=True, exist_ok=True)

            # Escribir archivo .desktop
            self.desktop_entry_path.write_text(
                self._render_desktop_entry(exec_path.resolve(), icon_path.resolve()),
                encoding="utf-8",
            )

            # Symlink a ejecutable (idempotente: remover si existe enlace o archivo previo)
            if self.bin_symlink_path.is_symlink() or self.bin_symlink_path.exists():
                self.bin_symlink_path.unlink()
            self.bin_symlink_path.symlink_to(exec_path.resolve())

        except OSError as e:
            return OperationResult.fail(
                ErrorCode.DEPENDENCY_INSTALL_FAILED, f"Error escribiendo desktop entry: {e}",
            )
        return OperationResult.ok(None, "desktop entry y symlink creados exitosamente")

    # ─── TODO-I4 · uninstall ─────────────────────────────────────────
    def uninstall(self, purge: bool = False) -> OperationResult[None]:
        """Elimina enlaces XDG. Purga ~/.MASV/ solo si purge=True.

        Contrato:
          - Elimina .desktop y symlink si existen (idempotente).
          - purge=False: conserva ~/.MASV/ intacto.
          - purge=True: elimina ~/.MASV/ completo con shutil.rmtree.
          - Fail con DEPENDENCY_INSTALL_FAILED si rmtree falla.
        """
        errors = []
        for p in (self.desktop_entry_path, self.bin_symlink_path):
            try:
                if p.is_symlink() or p.exists():
                    p.unlink()
            except OSError as e:
                errors.append(f"{p}: {e}")

        if purge:
            try:
                if self.masv_root.exists():
                    shutil.rmtree(self.masv_root)
            except OSError as e:
                errors.append(f"{self.masv_root}: {e}")

        if errors:
            return OperationResult.fail(
                ErrorCode.DEPENDENCY_INSTALL_FAILED, "; ".join(errors),
            )
        return OperationResult.ok(None, "desinstalación completada con éxito")
