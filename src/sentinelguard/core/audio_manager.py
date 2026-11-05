import json
import os
from pathlib import Path

from pycaw.pycaw import AudioUtilities
from pycaw.constants import EDataFlow, DEVICE_STATE


class AudioManager:
    def __init__(self):
        self.settings_path = (
            Path(os.environ["LOCALAPPDATA"])
            / "SentinelGuard"
            / "settings.json"
        )

    def get_audio_outputs(self):
        return AudioUtilities.GetAllDevices(
            data_flow=EDataFlow.eRender.value,
            device_state=DEVICE_STATE.ACTIVE.value
        )

    def list_audio_outputs(self):
        devices = self.get_audio_outputs()

        if not devices:
            print("Kullanilabilir ses cikisi bulunamadi.")
            return devices

        print("\nKullanilabilir ses cikislari:\n")

        for index, device in enumerate(devices, start=1):
            print(f"{index}. {device.FriendlyName}")
            print(f"   Device ID: {device.id}\n")

        return devices

    def _read_settings(self):
        if not self.settings_path.exists():
            return {}

        try:
            with open(
                self.settings_path, "r", encoding="utf-8"
            ) as file:
                settings = json.load(file)

            if not isinstance(settings, dict):
                raise ValueError("Gecersiz ayar dosyasi.")

            return settings

        except (OSError, ValueError, UnicodeError) as error:
            print(f"Ayar dosyasi okunamadi: {error}")
            return {}

    def save_speaker_selection(self, device_id):
        devices = self.get_audio_outputs()

        # Secilen cihaz gercekten mevcut mu?
        if not any(device.id == device_id for device in devices):
            raise ValueError("Secilen ses cihazi bulunamadi.")

        # Ayar klasorunu olustur.
        self.settings_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        # Mevcut ayarlari koru.
        settings = self._read_settings()

        if not isinstance(settings.get("audio"), dict):
            settings["audio"] = {}

        settings["audio"]["speaker_device_id"] = device_id

        # Ayarlari dosyaya kaydet.
        with open(
            self.settings_path, "w", encoding="utf-8"
        ) as file:
            json.dump(settings, file, indent=4)

        print("Hoparlor secimi basariyla kaydedildi.")

    def load_speaker_selection(self):
        settings = self._read_settings()

        audio_settings = settings.get("audio", {})

        if not isinstance(audio_settings, dict):
            return None

        device_id = audio_settings.get("speaker_device_id")

        if not device_id:
            return None

        # Kaydedilen cihaz hala mevcut mu?
        devices = self.get_audio_outputs()

        for device in devices:
            if device.id == device_id:
                print(
                    f"Kayitli hoparlor bulundu: "
                    f"{device.FriendlyName}"
                )
                return device_id

        print("Kaydedilen hoparlor artik bulunamiyor.")
        return None


if __name__ == "__main__":
    audio_manager = AudioManager()

    try:
        saved_id = audio_manager.load_speaker_selection()

        if saved_id is None:
            devices = audio_manager.list_audio_outputs()

            if devices:
                try:
                    choice = int(
                        input("Hoparlor numarasini sec: ")
                    )

                    if 1 <= choice <= len(devices):
                        selected_device = devices[choice - 1]

                        audio_manager.save_speaker_selection(
                            selected_device.id
                        )
                    else:
                        print("Gecersiz secim.")

                except ValueError:
                    print("Lutfen gecerli bir numara gir.")

        else:
            print("Hoparlor secimi zaten yapilmis.")

    except KeyboardInterrupt:
        print("\nIslem kullanici tarafindan iptal edildi.")

    except (OSError, ValueError, RuntimeError) as error:
        print(f"AudioManager hatasi: {error}")
