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

            # Olayi USBMonitor'a ilet.
            self.callback(event_type, str(device_path))

        except Exception as error:
            print(f"USB bildirim hatasi: {error}")

        return 1

    def start(self):
        if self.hwnd is not None:
            return

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

            print("USB olay dinleyicisi baslatildi.")

        except Exception:
            self.stop()
            raise

    def process_events(self):
        if self.hwnd is not None:
            win32gui.PumpWaitingMessages()

    def stop(self):

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
