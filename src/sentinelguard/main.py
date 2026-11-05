import time

from sentinelguard.core.alarm_manager import AlarmManager
from sentinelguard.core.security_manager import SecurityManager
from sentinelguard.monitors.power_monitor import PowerMonitor
from sentinelguard.core.audio_manager import AudioManager

def main():

    audio_manager = AudioManager()
    alarm_manager = AlarmManager(audio_manager)
    security_manager = SecurityManager(alarm_manager)
    power_monitor = PowerMonitor(security_manager)

    print("SentinelGuard baslatiliyor...")

    try:
        input("Enter'a basarak koruma modunu aktiflestirin...")

        security_manager.arm()
        power_monitor.start_session()

        print("Izleme baslatildi. Cikis yapmak icin Ctrl+C tuslarina basin.")

        while True:
            power_monitor.check_power()
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nCikis yapiliyor...")

    finally:

        power_monitor.stop_session()
        security_manager.disarm()

if __name__ == "__main__":
    main()