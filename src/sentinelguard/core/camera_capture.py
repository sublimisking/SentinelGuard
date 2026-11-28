"""Alarm aninda kameradan tek fotograf ceken, hata vermeyen modul.

Fotograflar yalnizca bu bilgisayarda saklanir ve hicbir yere gonderilmez.
Kamera yoksa, baska uygulama tutuyorsa veya Windows izin vermiyorsa
koruma kesintisiz devam eder; sonuc yalnizca callback ile bildirilir.
"""

from __future__ import annotations

import base64
from datetime import datetime
import json
import os
from pathlib import Path
import threading
import time

MAX_PHOTOS = 5
CAPTURE_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2.0
WARMUP_FRAMES = 8
JPEG_QUALITY = 85

PRIVACY_HINT = (
    "Kamera açılamadı. Windows Ayarlar > Gizlilik > Kamera bölümünde "
    "masaüstü uygulamalarına izin verildiğini kontrol edin."
)


def _local_base() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base is None:
        return Path.home() / "AppData" / "Local" / "SentinelGuard"
    return Path(base) / "SentinelGuard"


def default_captures_dir() -> Path:
    return _local_base() / "captures"


def default_settings_path() -> Path:
    return _local_base() / "settings.json"


# --- Ayar: settings.json icindeki "camera.enabled" (varsayilan: acik) ---


def _read_settings(settings_path: Path) -> dict:
    try:
        with open(settings_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, UnicodeError):
        return {}


def load_camera_enabled(settings_path: str | Path | None = None) -> bool:
    path = Path(settings_path) if settings_path else default_settings_path()
    camera = _read_settings(path).get("camera")
    if isinstance(camera, dict) and isinstance(camera.get("enabled"), bool):
        return camera["enabled"]
    return True


def save_camera_enabled(
    enabled: bool, settings_path: str | Path | None = None
) -> None:
    path = Path(settings_path) if settings_path else default_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    settings = _read_settings(path)
    if not isinstance(settings.get("camera"), dict):
        settings["camera"] = {}
    settings["camera"]["enabled"] = bool(enabled)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(settings, file, indent=4)


# --- Onizleme: Pillow olmadan, cv2 ile PNG uretip Tk PhotoImage'a verir ---


def make_png_base64(photo_path: str | Path, max_size: int) -> str | None:
    """Fotografi max_size kutusuna sigdirip base64 PNG dondurur."""
    try:
        import cv2

        image = cv2.imread(str(photo_path))
        if image is None:
            return None

        height, width = image.shape[:2]
        scale = min(max_size / width, max_size / height, 1.0)
        if scale < 1.0:
            image = cv2.resize(
                image,
                (max(1, int(width * scale)), max(1, int(height * scale))),
                interpolation=cv2.INTER_AREA,
            )

        ok, buffer = cv2.imencode(".png", image)
        if not ok:
            return None
        return base64.b64encode(buffer.tobytes()).decode("ascii")
    except Exception as error:
        print(f"Önizleme oluşturulamadı: {error}")
        return None


class CameraCapture:
    """Tek kare ceker; en fazla max_photos fotografi diskte tutar."""

    def __init__(
        self,
        captures_dir: str | Path | None = None,
        max_photos: int = MAX_PHOTOS,
        attempts: int = CAPTURE_ATTEMPTS,
        retry_delay: float = RETRY_DELAY_SECONDS,
        warmup_frames: int = WARMUP_FRAMES,
    ):
        self.captures_dir = (
            Path(captures_dir) if captures_dir else default_captures_dir()
        )
        self.max_photos = max(1, max_photos)
        self.attempts = max(1, attempts)
        self.retry_delay = retry_delay
        self.warmup_frames = warmup_frames
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    # --- Disariya acik ---

    def capture_async(self, on_done) -> bool:
        """Arka planda ceker. on_done(path | None, hata_metni | None).

        on_done, capture thread'inden cagrilir; UI'ye dokunmamalidir.
        Onceki cekim suruyorsa yenisi baslatilmaz.
        """
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False
            self._thread = threading.Thread(
                target=self._run,
                args=(on_done,),
                daemon=True,
                name="SentinelGuardCamera",
            )
            self._thread.start()
        return True

    def capture_with_retries(self) -> Path:
        """Birkac kez dener; basarisizsa RuntimeError firlatir."""
        last_error = PRIVACY_HINT
        for attempt in range(self.attempts):
            try:
                return self.capture_once()
            except Exception as error:
                last_error = str(error) or PRIVACY_HINT
                print(f"Kamera denemesi {attempt + 1} başarısız: {last_error}")
                if attempt < self.attempts - 1:
                    time.sleep(self.retry_delay)
        raise RuntimeError(last_error)

    def capture_once(self) -> Path:
        import cv2

        camera = self._open_camera(cv2)
        try:
            frame = None
            # Ilk kareler karanlik/bos olabilir; poz oturana kadar at.
            for _ in range(self.warmup_frames):
                ok, candidate = camera.read()
                if ok and candidate is not None:
                    frame = candidate
            if frame is None:
                ok, frame = camera.read()
                if not ok or frame is None:
                    raise RuntimeError("Kameradan görüntü alınamadı.")
        finally:
            camera.release()

        self.captures_dir.mkdir(parents=True, exist_ok=True)
        path = self._new_photo_path()
        ok = cv2.imwrite(
            str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
        )
        if not ok or not path.is_file():
            raise RuntimeError("Fotoğraf diske yazılamadı.")

        self.prune()
        return path

    def list_photos(self) -> list[Path]:
        """Kayitli fotograflar, en yeni en basta."""
        try:
            return sorted(self.captures_dir.glob("*.jpg"), reverse=True)
        except OSError:
            return []

    def delete_photo(self, path: str | Path) -> bool:
        """Yalnizca captures klasorundeki .jpg dosyalarini siler.

        Baska klasorlerdeki yollar reddedilir (ValueError). Dosya zaten
        yoksa False doner.
        """
        target = Path(path)
        try:
            inside = (
                target.suffix.lower() == ".jpg"
                and target.resolve().parent == self.captures_dir.resolve()
            )
        except OSError:
            inside = False
        if not inside:
            raise ValueError("Yalnızca alarm fotoğrafları silinebilir.")

        try:
            target.unlink()
        except FileNotFoundError:
            return False
        return True

    def prune(self) -> None:
        """En yeni max_photos dosya kalir, eskiler silinir."""
        try:
            photos = sorted(self.captures_dir.glob("*.jpg"))
        except OSError:
            return
        for old in photos[: max(0, len(photos) - self.max_photos)]:
            try:
                old.unlink()
            except OSError as error:
                print(f"Eski fotoğraf silinemedi: {error}")

    # --- Ic ayrintilar ---

    def _run(self, on_done) -> None:
        try:
            path = self.capture_with_retries()
            result = (path, None)
        except Exception as error:
            result = (None, str(error) or PRIVACY_HINT)
        try:
            on_done(*result)
        except Exception as error:
            print(f"Kamera sonucu iletilemedi: {error}")

    def _open_camera(self, cv2):
        backends = [getattr(cv2, "CAP_DSHOW", None), None]
        for backend in backends:
            camera = (
                cv2.VideoCapture(0)
                if backend is None
                else cv2.VideoCapture(0, backend)
            )
            if camera is not None and camera.isOpened():
                return camera
            if camera is not None:
                camera.release()
        raise RuntimeError(PRIVACY_HINT)

    def _new_photo_path(self) -> Path:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = self.captures_dir / f"{stamp}.jpg"
        counter = 1
        while path.exists():
            path = self.captures_dir / f"{stamp}_{counter}.jpg"
            counter += 1
        return path
