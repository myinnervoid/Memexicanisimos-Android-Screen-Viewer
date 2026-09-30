"""Autómata Finito de Interfaz para MASV.

Estándar de 5 Vectores — Vector 4 (Superficie de Interfaz & Mapeo de Estados) y Ley Global 6.
Gestiona de manera formal los 5 estados canónicos: [IDLE], [PENDING], [SUCCESS], [EMPTY], [FAULT].
"""

from enum import Enum
from typing import Callable, List, Optional, Dict, Any
from .errors import ErrorCode

class UIState(str, Enum):
    IDLE = "IDLE"          # Sin transmisión activa, interfaz lista para operar
    PENDING = "PENDING"    # Operación en curso (escaneo, emparejamiento, arranque scrcpy)
    SUCCESS = "SUCCESS"    # Transmisión en vivo o acción completada con éxito
    EMPTY = "EMPTY"        # Sin dispositivos conectados o sin perfiles disponibles
    FAULT = "FAULT"        # Error en ADB, scrcpy, red o permisos


class UIStateMachine:
    """Máquina de estados finita determinista para la interfaz de usuario."""

    def __init__(self, initial_state: UIState = UIState.IDLE):
        self._state: UIState = initial_state
        self._previous_state: Optional[UIState] = None
        self._message: str = ""
        self._error_code: Optional[ErrorCode] = None
        self._listeners: List[Callable[[UIState, str, Optional[ErrorCode]], None]] = []

    @property
    def current_state(self) -> UIState:
        return self._state

    @property
    def previous_state(self) -> Optional[UIState]:
        return self._previous_state

    @property
    def message(self) -> str:
        return self._message

    @property
    def error_code(self) -> Optional[ErrorCode]:
        return self._error_code

    def subscribe(self, listener: Callable[[UIState, str, Optional[ErrorCode]], None]):
        """Registra un observador que reacciona a los cambios de estado."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener: Callable[[UIState, str, Optional[ErrorCode]], None]):
        if listener in self._listeners:
            self._listeners.remove(listener)

    def transition_to(
        self,
        new_state: UIState,
        message: str = "",
        error_code: Optional[ErrorCode] = None
    ) -> bool:
        """Aplica una transición de estado si es válida y notifica a los observadores."""
        self._previous_state = self._state
        self._state = new_state
        self._message = message
        self._error_code = error_code if new_state == UIState.FAULT else None

        self._notify_listeners()
        return True

    def set_idle(self, message: str = "Listo"):
        self.transition_to(UIState.IDLE, message=message)

    def set_pending(self, message: str = "Procesando..."):
        self.transition_to(UIState.PENDING, message=message)

    def set_success(self, message: str = "Operación completada"):
        self.transition_to(UIState.SUCCESS, message=message)

    def set_empty(self, message: str = "No hay dispositivos conectados"):
        self.transition_to(UIState.EMPTY, message=message)

    def set_fault(self, message: str, error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR):
        self.transition_to(UIState.FAULT, message=message, error_code=error_code)

    def _notify_listeners(self):
        for listener in self._listeners:
            try:
                listener(self._state, self._message, self._error_code)
            except Exception as e:
                print(f"[UIStateMachine] Error en listener: {e}")

    def get_status_info(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "message": self._message,
            "error_code": self._error_code.value if self._error_code else None,
            "is_busy": self._state == UIState.PENDING,
            "is_streaming": self._state == UIState.SUCCESS,
            "has_error": self._state == UIState.FAULT,
        }
