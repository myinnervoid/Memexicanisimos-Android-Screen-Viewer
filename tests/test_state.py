import unittest
from scrcpy_dock.state import UIStateMachine, UIState
from scrcpy_dock.errors import ErrorCode

class TestUIStateMachine(unittest.TestCase):
    def setUp(self):
        self.sm = UIStateMachine(UIState.IDLE)

    def test_initial_state(self):
        self.assertEqual(self.sm.current_state, UIState.IDLE)
        self.assertIsNone(self.sm.previous_state)
        self.assertFalse(self.sm.get_status_info()["is_busy"])

    def test_transitions_lifecycle(self):
        # Transición a PENDING
        self.sm.set_pending("Escaneando dispositivos...")
        self.assertEqual(self.sm.current_state, UIState.PENDING)
        self.assertEqual(self.sm.previous_state, UIState.IDLE)
        self.assertTrue(self.sm.get_status_info()["is_busy"])

        # Transición a SUCCESS
        self.sm.set_success("Transmisión activa")
        self.assertEqual(self.sm.current_state, UIState.SUCCESS)
        self.assertEqual(self.sm.previous_state, UIState.PENDING)
        self.assertTrue(self.sm.get_status_info()["is_streaming"])

        # Transición a EMPTY
        self.sm.set_empty("Sin dispositivos")
        self.assertEqual(self.sm.current_state, UIState.EMPTY)
        self.assertEqual(self.sm.previous_state, UIState.SUCCESS)

        # Transición a FAULT
        self.sm.set_fault("Error al iniciar scrcpy", ErrorCode.PROCESS_CRASH)
        self.assertEqual(self.sm.current_state, UIState.FAULT)
        self.assertEqual(self.sm.error_code, ErrorCode.PROCESS_CRASH)
        self.assertTrue(self.sm.get_status_info()["has_error"])

        # Retorno a IDLE
        self.sm.set_idle("Listo")
        self.assertEqual(self.sm.current_state, UIState.IDLE)
        self.assertIsNone(self.sm.error_code)

    def test_observer_notifications(self):
        events_received = []

        def listener(state, message, error_code):
            events_received.append((state, message, error_code))

        self.sm.subscribe(listener)
        self.sm.set_pending("Conectando Wi-Fi...")
        self.sm.set_fault("Conexión rechazada", ErrorCode.CONNECTION_REFUSED)

        self.assertEqual(len(events_received), 2)
        self.assertEqual(events_received[0], (UIState.PENDING, "Conectando Wi-Fi...", None))
        self.assertEqual(events_received[1], (UIState.FAULT, "Conexión rechazada", ErrorCode.CONNECTION_REFUSED))

        # Unsubscribe
        self.sm.unsubscribe(listener)
        self.sm.set_idle("Listo")
        self.assertEqual(len(events_received), 2)

if __name__ == "__main__":
    unittest.main()
