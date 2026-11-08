import ctypes
from ctypes import wintypes
import math
import time


class MouseMovementFilter:
    """Küçük işaretçi oynamalarını filtreler; ekran pikseli kullanır."""

    def __init__(self, threshold_pixels=40, window_seconds=1.5):
        if threshold_pixels <= 0 or window_seconds <= 0:
            raise ValueError("Fare eşikleri sıfırdan büyük olmalıdır.")
        self.threshold_pixels = threshold_pixels
        self.window_seconds = window_seconds
        self._start_pos = None
        self._last_pos = None
        self._start_time = None

    def reset(self, cursor, now):
        self._start_pos = tuple(cursor)
        self._last_pos = tuple(cursor)
        self._start_time = now

    def check(self, cursor, now):
        cursor = tuple(cursor)
        if self._start_pos is None:
            self.reset(cursor, now)
            return False

        # Uzun süre boyunca birikmiş titreşimi harekete dönüştürme.
        if now - self._start_time > self.window_seconds:
            self._start_pos = self._last_pos
            self._start_time = now

        self._last_pos = cursor
        dx = cursor[0] - self._start_pos[0]
        dy = cursor[1] - self._start_pos[1]
        return math.hypot(dx, dy) >= self.threshold_pixels


class WindowsInputBackend:
    """Yalnızca Windows user32 API'si; ek kütüphane gerektirmez."""

    # 0x01-0x06: sol/sağ/orta/ek fare düğmeleri
    # 0x08-0xFE: Windows sanal klavye tuşları
    TRACKED_KEYS = (1, 2, 4, 5, 6, *range(0x08, 0xFF))

    def __init__(self):
        if not hasattr(ctypes, "WinDLL"):
            raise OSError("InputMonitor yalnızca Windows üzerinde çalışır.")
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.user32.GetCursorPos.argtypes = (ctypes.POINTER(wintypes.POINT),)
        self.user32.GetCursorPos.restype = wintypes.BOOL
        self.user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
        self.user32.GetAsyncKeyState.restype = ctypes.c_short

    def cursor_position(self):
        point = wintypes.POINT()
        if not self.user32.GetCursorPos(ctypes.byref(point)):
            raise ctypes.WinError(ctypes.get_last_error())
        return point.x, point.y

    def pressed_keys(self):
        # Yüksek bit: tuş şu anda basılı. Düşük bit kullanılmıyor.
        return frozenset(
            key for key in self.TRACKED_KEYS
            if self.user32.GetAsyncKeyState(key) & 0x8000
        )


class InputMonitor:
    """Mevcut app.py ile aynı arayüz: start/check/stop_session."""

    MOUSE_THRESHOLD_PIXELS = 40
    MOUSE_WINDOW_SECONDS = 1.5

    def __init__(self, event_router, backend=None, clock=None):
        self.event_router = event_router
        self.backend = backend if backend is not None else WindowsInputBackend()
        self.clock = clock if clock is not None else time.monotonic
        self.mouse_filter = MouseMovementFilter(
            threshold_pixels=self.MOUSE_THRESHOLD_PIXELS,
            window_seconds=self.MOUSE_WINDOW_SECONDS,
        )
        self.is_monitoring = False
        self.input_detected = False
        self._previous_pressed = frozenset()

    def start_session(self):
        self._previous_pressed = self.backend.pressed_keys()
        self.mouse_filter.reset(self.backend.cursor_position(), self.clock())
        self.input_detected = False
        self.is_monitoring = True
        print("InputMonitor: İzleme başlatıldı (40 px / 1.5 sn).")

    def check_input(self):
        if not self.is_monitoring or self.input_detected:
            return False

        now = self.clock()
        pressed = self.backend.pressed_keys()
        newly_pressed = pressed - self._previous_pressed
        self._previous_pressed = pressed

        moved_enough = self.mouse_filter.check(self.backend.cursor_position(), now)

        if not newly_pressed and not moved_enough:
            return False

        self.input_detected = True
        self.event_router.handle_event("INPUT_DETECTED")
        return True

    def stop_session(self):
        self.is_monitoring = False
        self.input_detected = False
        self._previous_pressed = frozenset()
