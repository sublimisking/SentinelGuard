"""USB bildirimlerini Tk mesaj dongusunden ayri bir thread uzerinde dinler."""

import queue
import threading

import win32con
import win32gui
import win32gui_struct


class USBEventListener:

    USB_DEVICE_GUID = (
        "{A5DCBF10-6530-11D2-901F-00C04FB951ED}"
    )

    def __init__(self, callback):
        self.callback = callback
        self.hwnd = None
        self.notification_handle = None

        self.class_name = (
            f"SentinelGuardUSBListener_{id(self)}"
        )
        self.class_registered = False
        self._events = queue.Queue()
        self._thread = None
        self._stop_event = threading.Event()
        self._ready = threading.Event()
        self._error = None

    def on_device_change(self, hwnd, msg, event, lparam):

        if event not in (
            win32con.DBT_DEVICEARRIVAL,
            win32con.DBT_DEVICEREMOVECOMPLETE
        ):
            return 1

        if not lparam:
            return 1

        try:
            info = win32gui_struct.UnpackDEV_BROADCAST(
                lparam
            )

            if info is None:
                return 1

            if info.devicetype != (
                win32con.DBT_DEVTYP_DEVICEINTERFACE
            ):
                return 1

            device_path = getattr(info, "name", None)

            if not device_path:
                print("USB bildirimi: Cihaz yolu okunamadi.")
                return 1

            if event == win32con.DBT_DEVICEARRIVAL:
                event_type = "USB_CONNECTED"
            else:
                event_type = "USB_DISCONNECTED"

            # Windows callback'i icinde alarm veya arayuz kodu calistirma.
            if not self._stop_event.is_set():
                self._events.put((event_type, str(device_path)))

        except Exception as error:
            print(f"USB bildirim hatasi: {error}")

        return 1

    def start(self):
        """Ana uygulama thread'inden cagrilir; kayit bitmeden donmez."""
        if self._thread is not None and self._thread.is_alive():
            if self._stop_event.is_set():
                raise RuntimeError("USB dinleyicisi henuz durmadi.")
            return

        self._clear_events()
        self._stop_event.clear()
        self._ready.clear()
        self._error = None
        self._thread = threading.Thread(
            target=self._run,
            name="SentinelGuardUSBListener",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(5.0):
            self._stop_event.set()
            raise RuntimeError("USB dinleyicisi zamaninda baslatilamadi.")
        if self._error is not None:
            self._thread.join(timeout=5.0)
            raise RuntimeError("USB dinleyicisi baslatilamadi.") from self._error
        print("USB olay dinleyicisi baslatildi.")

    def _run(self):
        try:
            self._create_window()
            self._ready.set()
            while not self._stop_event.is_set():
                # Yalnizca bu thread'in mesajlari islenir; Tk'ye dokunulmaz.
                if win32gui.PumpWaitingMessages():
                    if not self._stop_event.is_set():
                        raise RuntimeError("USB mesaj dongusu beklenmedik sekilde kapandi.")
                    break
                self._stop_event.wait(0.01)
        except Exception as error:
            self._error = error
        finally:
            try:
                self._destroy_window()
            except Exception as error:
                if self._error is None:
                    self._error = error
            self._ready.set()

    def _create_window(self):
        window_class = win32gui.WNDCLASS()
        window_class.lpszClassName = self.class_name

        window_class.lpfnWndProc = {
            win32con.WM_DEVICECHANGE:
                self.on_device_change
        }

        win32gui.RegisterClass(window_class)
        self.class_registered = True

        try:
            self.hwnd = win32gui.CreateWindow(
                self.class_name,
                "SentinelGuard USB Listener",
                win32con.WS_CAPTION,
                0, 0, 0, 0,
                0, 0, 0, None
            )

            device_filter = (
                win32gui_struct.PackDEV_BROADCAST_DEVICEINTERFACE(
                    self.USB_DEVICE_GUID
                )
            )

            self.notification_handle = (
                win32gui.RegisterDeviceNotification(
                    self.hwnd,
                    device_filter,
                    win32con.DEVICE_NOTIFY_WINDOW_HANDLE
                )
            )

        except Exception:
            # _run finally blogu kaynaklari ayni thread uzerinde temizler.
            raise

    def process_events(self):
        """Mevcut uygulama dongusunden cagrilir; sadece kuyrugu bosaltir."""
        if self._stop_event.is_set():
            return
        if self._error is not None:
            raise RuntimeError("USB olay dinleyicisi calismiyor.") from self._error
        # Bir USB olay firtinasinda arayuzun kilitlenmesini onle.
        for _ in range(100):
            if self._stop_event.is_set():
                break
            try:
                event_type, device_path = self._events.get_nowait()
            except queue.Empty:
                break
            self.callback(event_type, device_path)

    def _clear_events(self):
        while True:
            try:
                self._events.get_nowait()
            except queue.Empty:
                return

    def stop(self):
        """Pencereyi olusturan thread'in kaynaklari kapatmasini bekle."""
        self._stop_event.set()
        thread = self._thread
        if thread is not None:
            if thread is threading.current_thread():
                return
            thread.join(timeout=5.0)
            if thread.is_alive():
                raise RuntimeError("USB dinleyicisi zamaninda durmadi.")
            self._thread = None
        self._clear_events()

    def _destroy_window(self):
        if self.notification_handle is not None:
            win32gui.UnregisterDeviceNotification(
                self.notification_handle
            )
            self.notification_handle = None

        if self.hwnd is not None:
            win32gui.DestroyWindow(self.hwnd)
            self.hwnd = None

        if self.class_registered:
            win32gui.UnregisterClass(
                self.class_name,
                None
            )
            self.class_registered = False
