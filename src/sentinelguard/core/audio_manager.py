import json
import os
from pathlib import Path

from pycaw.pycaw import AudioUtilities
from pycaw.constants import EDataFlow, DEVICE_STATE, ERole


class AudioManager:

    AUDIO_ROLES = (
        ERole.eConsole,
        ERole.eMultimedia,
        ERole.eCommunications
    )

    def __init__(self):
        self.settings_path = (
            Path(os.environ["LOCALAPPDATA"])
            / "SentinelGuard"
            / "settings.json"
        )

        # Alarmdan onceki ses cikislarini saklayacak.
        self.previous_outputs = None

    # ------------------------------------
    # SES CIHAZLARINI LISTELEME
    # ------------------------------------

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

    # ------------------------------------
    # AYAR DOSYASINI OKUMA
    # ------------------------------------

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

    # ------------------------------------
    # HOPARLOR SECIMINI KAYDETME
    # ------------------------------------

    def save_speaker_selection(self, device_id):
        devices = self.get_audio_outputs()

        if not any(device.id == device_id for device in devices):
            raise ValueError("Secilen ses cihazi bulunamadi.")

        self.settings_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        settings = self._read_settings()

        if not isinstance(settings.get("audio"), dict):
            settings["audio"] = {}

        settings["audio"]["speaker_device_id"] = device_id

        with open(
            self.settings_path, "w", encoding="utf-8"
        ) as file:
            json.dump(settings, file, indent=4)

        print("Hoparlor secimi basariyla kaydedildi.")

    # ------------------------------------
    # KAYITLI HOPARLORU YUKLEME
    # ------------------------------------

    def load_speaker_selection(self):
        settings = self._read_settings()
        audio_settings = settings.get("audio", {})

        if not isinstance(audio_settings, dict):
            return None

        device_id = audio_settings.get("speaker_device_id")

        if not device_id:
            return None

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

    # ------------------------------------
    # SECILEN HOPARLORE GECIS
    # ------------------------------------

    def switch_to_selected_speaker(self):
        if self.previous_outputs is not None:
            return

        speaker_id = self.load_speaker_selection()

        if speaker_id is None:
            raise RuntimeError(
                "Kayitli hoparlor bulunamadi."
            )

        enumerator = AudioUtilities.GetDeviceEnumerator()

        # Eski cikislari once gecici olarak kaydet.
        previous_outputs = {}

        for role in self.AUDIO_ROLES:
            current_device = enumerator.GetDefaultAudioEndpoint(
                EDataFlow.eRender.value,
                role.value
            )

            previous_outputs[role] = current_device.GetId()

        self.previous_outputs = previous_outputs

        try:
            # Windows'un varsayilan ses cikisini degistir.
            AudioUtilities.SetDefaultDevice(
                speaker_id,
                roles=self.AUDIO_ROLES
            )

            print("Ses cikisi secilen hoparlore degistirildi.")

        except Exception:
            # Gecis basarisizsa eski cikislara don.
            try:
                self.restore_previous_output()
            except Exception as restore_error:
                print(
                    f"Ses cikisi kurtarma hatasi: {restore_error}"
                )
            raise

    # ------------------------------------
    # ESKI SES CIKISINA GERI DONUS
    # ------------------------------------

    def restore_previous_output(self):
        if self.previous_outputs is None:
            return

        errors = []
        remaining_outputs = {}

        for role, device_id in self.previous_outputs.items():
            try:
                AudioUtilities.SetDefaultDevice(
                    device_id,
                    roles=[role]
                )

            except Exception as error:
                errors.append(f"{role.name}: {error}")
                remaining_outputs[role] = device_id

        # Basarisiz donusleri tekrar deneyebilmek icin sakla.
        self.previous_outputs = remaining_outputs or None

        if errors:
            raise RuntimeError(
                "Bazi ses cikislari geri yuklenemedi: "
                + "; ".join(errors)
            )

        print("Eski ses cikislari geri yuklendi.")
