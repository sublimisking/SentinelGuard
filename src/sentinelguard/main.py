import time

from sentinelguard.core.audio_manager import AudioManager
from sentinelguard.core.alarm_manager import AlarmManager
from sentinelguard.core.security_manager import SecurityManager

from sentinelguard.monitors.power_monitor import PowerMonitor
from sentinelguard.monitors.usb_monitor import USBMonitor


def main():

    # 1. Ses sistemi
    audio_manager = AudioManager()
    alarm_manager = AlarmManager(audio_manager)

    # 2. Guvenlik sistemi
    security_manager = SecurityManager(alarm_manager)

    # 3. Sensorler
    power_monitor = PowerMonitor(security_manager)
    usb_monitor = USBMonitor(security_manager)

    print("SentinelGuard baslatildi.")

    try:
        input(
            "Korumayi etkinlestirmek icin Enter'a bas..."
        )

        security_manager.arm()

        power_monitor.start_session()
        usb_monitor.start_session()

        print("\nSentinelGuard koruma modu aktif!")
        print("Sarj ve USB olaylari izleniyor.")
        print("Cikmak icin Ctrl+C.")

        next_power_check = time.monotonic()

        while True:

            # USB olaylarini Windows'tan al.
            usb_monitor.process_events()

            # Sarj durumunu 0.5 saniyede bir kontrol et.
            now = time.monotonic()

            if now >= next_power_check:
                power_monitor.check_power()

                next_power_check = (
                    time.monotonic() + 0.5
                )

            # Mesaj dongusunun CPU'yu mesgul
            # etmesini engelle.
            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nSentinelGuard kapatiliyor...")

    finally:

        usb_monitor.stop_session()
        power_monitor.stop_session()
        security_manager.disarm()

        print("SentinelGuard kapatildi.")


if __name__ == "__main__":
    main()
