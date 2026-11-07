import time

from sentinelguard.core.audio_manager import AudioManager
from sentinelguard.core.alarm_manager import AlarmManager
from sentinelguard.core.security_manager import SecurityManager

from sentinelguard.monitors.power_monitor import PowerMonitor
from sentinelguard.monitors.usb_monitor import USBMonitor


def ensure_alarm_speaker(audio_manager):
    """
    Kayıtlı alarm hoparlörünü kontrol eder.
    Geçerli bir seçim yoksa kullanıcıya hoparlör seçtirir.
    """

    # 1. Kayıtlı hoparlör var mı?
    saved_id = audio_manager.load_speaker_selection()

    if saved_id is not None:
        print("Alarm hoparloru hazir.")
        return

    # 2. Kayıt yoksa veya cihaz bulunamıyorsa
    print("\nAlarm hoparloru ayarlanmamis.")
    print("Lutfen alarm icin kullanilacak hoparloru sec.")

    devices = audio_manager.list_audio_outputs()

    if not devices:
        raise RuntimeError(
            "Kullanilabilir ses cikisi bulunamadi. "
            "Koruma baslatilamiyor."
        )

    # 3. Geçerli seçim yapılana kadar sor
    while True:
        choice = input(
            "Hoparlor numarasini gir (q: iptal): "
        ).strip()

        if choice.lower() == "q":
            raise RuntimeError(
                "Hoparlor secimi iptal edildi. "
                "Koruma baslatilmadi."
            )

        try:
            index = int(choice) - 1
        except ValueError:
            print("Lutfen bir numara gir.")
            continue

        if not 0 <= index < len(devices):
            print("Gecersiz hoparlor numarasi.")
            continue

        selected_device = devices[index]

        # 4. Seçimi settings.json dosyasına kaydet
        audio_manager.save_speaker_selection(
            selected_device.id
        )

        print(
            f"Alarm hoparloru secildi: "
            f"{selected_device.FriendlyName}"
        )

        return


def main():

    # Ses sistemi
    audio_manager = AudioManager()
    alarm_manager = AlarmManager(audio_manager)

    # Güvenlik sistemi
    security_manager = SecurityManager(alarm_manager)

    # Sensörler
    power_monitor = PowerMonitor(security_manager)
    usb_monitor = USBMonitor(security_manager)

    power_started = False
    usb_started = False

    print("SentinelGuard baslatildi.")

    try:
        # ONEMLI: Koruma acilmadan once hoparloru kontrol et.
        ensure_alarm_speaker(audio_manager)

        input(
            "\nKorumayi etkinlestirmek icin Enter'a bas..."
        )

        # Koruma modunu etkinleştir
        security_manager.arm()

        power_monitor.start_session()
        power_started = True

        usb_monitor.start_session()
        usb_started = True

        print("\nSentinelGuard koruma modu aktif!")
        print("Sarj ve USB olaylari izleniyor.")
        print("Cikmak icin Ctrl+C.")

        next_power_check = time.monotonic()

        while True:

            # USB olaylarini Windows'tan al
            usb_monitor.process_events()

            # Sarj durumunu kontrol et
            now = time.monotonic()

            if now >= next_power_check:
                power_monitor.check_power()
                next_power_check = (
                    time.monotonic() + 0.5
                )

            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nSentinelGuard kapatiliyor...")

    except EOFError:
        print("\nKullanici girdisi alinamadi.")

    except (OSError, RuntimeError, ValueError) as error:
        print(f"SentinelGuard hatasi: {error}")

    finally:
        if usb_started:
            usb_monitor.stop_session()

        if power_started:
            power_monitor.stop_session()

        security_manager.disarm()

        print("SentinelGuard kapatildi.")


if __name__ == "__main__":
    main()
