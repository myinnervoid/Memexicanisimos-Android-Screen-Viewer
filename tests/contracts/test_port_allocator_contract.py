"""Contratos congelados de PortAllocator. NO modificar sin reabrir ADR-029."""
from __future__ import annotations
import socket
import unittest

from scrcpy_dock.core.port_allocator import PortAllocator
from scrcpy_dock.contracts import ErrorCode


class PortAllocatorContract(unittest.TestCase):

    def test_first_acquire_returns_base(self):
        alloc = PortAllocator(base=27183)
        result = alloc.acquire()
        self.assertTrue(result.success)
        self.assertEqual(result.data, 27183)

    def test_second_acquire_increments(self):
        alloc = PortAllocator(base=27183)
        first = alloc.acquire().data
        second = alloc.acquire().data
        self.assertEqual((first, second), (27183, 27184))

    def test_release_frees_port_for_reuse(self):
        alloc = PortAllocator(base=27183)
        p = alloc.acquire().data
        alloc.release(p)
        self.assertEqual(alloc.acquire().data, p)

    def test_release_is_idempotent(self):
        alloc = PortAllocator(base=27183)
        alloc.release(99999)   # no reservado → no-op
        alloc.release(99999)

    def test_skips_port_already_in_use_by_external_process(self):
        # Ocupar 27183 con un socket real en loopback
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.bind(("127.0.0.1", 27183))
        blocker.listen(1)
        try:
            alloc = PortAllocator(base=27183)
            result = alloc.acquire()
            self.assertTrue(result.success)
            self.assertNotEqual(result.data, 27183)
        finally:
            blocker.close()

    def test_exhaustion_returns_error(self):
        alloc = PortAllocator(base=27183, max_offset=2)
        alloc.acquire()
        alloc.acquire()
        alloc.acquire()
        result = alloc.acquire()
        self.assertFalse(result.success)
        self.assertEqual(result.error, ErrorCode.PORT_POOL_EXHAUSTED)

    def test_reserved_snapshot_is_immutable_view(self):
        alloc = PortAllocator(base=27183)
        p = alloc.acquire().data
        snap = alloc.reserved()
        self.assertIn(p, snap)
        alloc.release(p)
        self.assertNotIn(p, alloc.reserved())

    def test_acquire_is_thread_safe_for_two_devices(self):
        """Simula el setup de 2 teléfonos concurrente."""
        import threading
        alloc = PortAllocator(base=27183)
        results: list[int] = []
        lock = threading.Lock()

        def worker():
            r = alloc.acquire()
            with lock:
                results.append(r.data)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(set(results)), 2)   # puertos distintos


if __name__ == "__main__":
    unittest.main()
