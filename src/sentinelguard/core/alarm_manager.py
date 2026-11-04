from pathlib import Path
import threading
import winsound

import comtypes
from pycaw.pycaw import AudioUtilities


class AlarmManager:
    def __init__(self):
        self.alarm_active = False
        self.stop_event = threading.Event()
        self.alarm_thread = None
        self._lock = threading.Lock()

    def start_alarm(self):
        with self._lock:
            if self.alarm_thread and self.alarm_thread.is_alive():
                return

            self.stop_event = threading.Event()
            self.alarm_active = True

            self.alarm_thread = threading.Thread(
                target=self._play_alarm,
                args=(self.stop_event,),
                daemon=False,
                name="SentinelGuardAlarm"
            )

            self.alarm_thread.start()

        print("SentinelGuard: Alarm baslatildi!")

    def _play_alarm(self, stop_event):
        speakers = None
        volume = None
        old_volume = None
        old_mute = None
        com_initialized = False

        sound_path = (
            Path(__file__).resolve().parents[3]
            / "assets"
            / "alarm.wav"
        )

        try:
            if not sound_path.is_file():
                raise FileNotFoundError(
                    f"Alarm dosyasi bulunamadi: {sound_path}"
                )

            try:
                comtypes.CoInitialize()
                com_initialized = True

                speakers = AudioUtilities.GetSpeakers()
                volume = speakers.EndpointVolume

                # Baslangictaki ses ayarlarini kaydet.
                old_volume = volume.GetMasterVolumeLevelScalar()
                old_mute = volume.GetMute()

                print(f"Eski ses seviyesi: %{old_volume * 100:.0f}")

                if not stop_event.is_set():
                    volume.SetMute(0, None)
                    volume.SetMasterVolumeLevelScalar(1.0, None)

            except Exception as error:
                print(f"Ses ayarlari degistirilemedi: {error}")

            if not stop_event.is_set():
                winsound.PlaySound(
                    str(sound_path),
                    winsound.SND_FILENAME
                    | winsound.SND_ASYNC
                    | winsound.SND_LOOP
                    | winsound.SND_NODEFAULT
                )

                # Alarm aktifken ses seviyesini koru.
                while not stop_event.wait(0.2):
                    if volume is None:
                        continue

                    try:
                        current_volume = (
                            volume.GetMasterVolumeLevelScalar()
                        )
                        current_mute = volume.GetMute()

                        # Sessize alindiysa sessiz modu kapat.
                        if current_mute:
                            volume.SetMute(0, None)

                        # Ses dusurulduyse tekrar %100 yap.
                        if current_volume < 0.99:
                            volume.SetMasterVolumeLevelScalar(
                                1.0, None
                            )

                    except Exception as error:
                        print(f"Ses kontrol hatasi: {error}")
                        # Siren devam etsin, denetim yapilamasin.
                        stop_event.wait()
                        break

        except (RuntimeError, OSError) as error:
            print(f"Alarm sesi oynatilamadi: {error}")

        finally:
            # Once alarm sesini durdur.
            try:
                winsound.PlaySound(None, 0)
            except RuntimeError as error:
                print(f"Alarm durdurulamadi: {error}")

            # Eski ses ayarlarini geri yukle.
            if volume is not None:
                if old_volume is not None:
                    try:
                        volume.SetMasterVolumeLevelScalar(
                            old_volume, None
                        )
                    except Exception as error:
                        print(f"Ses geri yuklenemedi: {error}")

                if old_mute is not None:
                    try:
                        volume.SetMute(old_mute, None)
                    except Exception as error:
                        print(f"Sessiz mod geri yuklenemedi: {error}")

            volume = None
            speakers = None

            if com_initialized:
                comtypes.CoUninitialize()

            with self._lock:
                if self.stop_event is stop_event:
                    self.alarm_active = False

            print("Alarm islemi tamamlandi.")

    def stop_alarm(self):
        with self._lock:
            thread = self.alarm_thread

            if thread is None:
                return

            self.stop_event.set()

        if thread is not threading.current_thread():
            thread.join()

        print("SentinelGuard: Alarm durduruldu!")

