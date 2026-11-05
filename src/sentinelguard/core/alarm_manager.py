from pathlib import Path
import threading
import winsound

import comtypes
from pycaw.pycaw import AudioUtilities


class AlarmManager:
    def __init__(self, audio_manager):
        self.audio_manager = audio_manager
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
        sound_path = (
            Path(__file__).resolve().parents[3]
            / "assets"
            / "alarm.wav"
        )

        volume = None
        old_volume = None
        old_mute = None
        com_initialized = False

        try:
            # Windows ses sistemini bu thread icin baslat.
            comtypes.CoInitialize()
            com_initialized = True

            if not sound_path.is_file():
                raise FileNotFoundError(
                    f"Alarm dosyasi bulunamadi: {sound_path}"
                )

            # 1. Eski ses cikisini kaydet ve
            # kullanicinin sectigi hoparlore gec.
            self.audio_manager.switch_to_selected_speaker()

            print("Alarm hoparlorune gecildi.")

            # Ses aygitinin degismesine kisa bir sure tanı.
            if stop_event.wait(0.2):
                return

            # 2. Yeni varsayilan hoparloru al.
            speakers = AudioUtilities.GetSpeakers()
            volume = speakers.EndpointVolume

            # 3. Hoparlorun onceki ses ayarlarini kaydet.
            old_volume = volume.GetMasterVolumeLevelScalar()
            old_mute = volume.GetMute()

            print(f"Eski hoparlor sesi: %{old_volume * 100:.0f}")

            # 4. Sesi yukselt ve sessiz modu kapat.
            volume.SetMute(0, None)
            volume.SetMasterVolumeLevelScalar(0.003, None)

            if stop_event.is_set():
                return

            # 5. Sireni baslat.
            winsound.PlaySound(
                str(sound_path),
                winsound.SND_FILENAME
                | winsound.SND_ASYNC
                | winsound.SND_LOOP
                | winsound.SND_NODEFAULT
            )

            print("SentinelGuard: Siren caliyor!")

            # 6. Alarm aktifken sesi kontrol et.
            while not stop_event.wait(0.2):

                current_volume = (
                    volume.GetMasterVolumeLevelScalar()
                )

                current_mute = volume.GetMute()

                if current_mute:
                    volume.SetMute(0, None)

                if current_volume < 0.99:
                    volume.SetMasterVolumeLevelScalar(
                        1.0, None
                    )

        except Exception as error:
            print(f"Alarm sistemi hatasi: {error}")

        finally:
            # 7. Sireni durdur.
            try:
                winsound.PlaySound(None, 0)
            except RuntimeError as error:
                print(f"Siren durdurulamadi: {error}")

            # 8. Hoparlorun eski ses seviyesini geri yukle.
            if volume is not None:
                try:
                    if old_volume is not None:
                        volume.SetMasterVolumeLevelScalar(
                            old_volume, None
                        )

                    if old_mute is not None:
                        volume.SetMute(old_mute, None)

                    print("Eski ses seviyesi geri yuklendi.")

                except Exception as error:
                    print(f"Ses geri yuklenemedi: {error}")

            # 9. Eski ses cikisina geri don.
            try:
                self.audio_manager.restore_previous_output()
            except Exception as error:
                print(f"Ses cikisi geri yuklenemedi: {error}")

            volume = None

            if com_initialized:
                comtypes.CoUninitialize()

            # 10. Alarm durumunu sifirla.
            with self._lock:
                if self.stop_event is stop_event:
                    self.alarm_active = False

            print("SentinelGuard: Alarm islemi tamamlandi.")

    def stop_alarm(self):
        with self._lock:
            thread = self.alarm_thread

            if thread is None:
                return

            self.stop_event.set()

        if thread is not threading.current_thread():
            thread.join()

        print("SentinelGuard: Alarm durduruldu!")

