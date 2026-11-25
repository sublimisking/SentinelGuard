import hashlib
import os
import re
import tempfile
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sentinelguard.updates.update_checker import (
    ReleaseAsset,
    ReleaseInfo
)


MAX_DOWNLOAD_BYTES = 500 * 1024 * 1024
CHUNK_SIZE = 64 * 1024

DEFAULT_UPDATE_DIR = Path(tempfile.gettempdir()) / "SentinelGuard-Updates"

_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
_DIGEST = re.compile(r"^sha256:([0-9a-fA-F]{64})$")


class UpdateDownloadError(RuntimeError):
    """Guncelleme dosyasi indirilemedi veya dogrulanamadi."""


def select_installer(release: ReleaseInfo) -> ReleaseAsset | None:
    """Surumdeki Windows kurulum dosyasini secer."""

    for asset in release.assets:
        name = asset.name.lower()

        if name.endswith(".exe") and "setup" in name:
            return asset

    return None


class UpdateDownloader:

    def __init__(
        self,
        target_dir: Path | None = None,
        timeout: float = 30.0,
        require_digest: bool = True
    ):
        if timeout <= 0:
            raise ValueError("Zaman asimi pozitif olmali.")

        self.target_dir = Path(target_dir or DEFAULT_UPDATE_DIR)
        self.timeout = timeout
        self.require_digest = require_digest

    def download(
        self,
        asset: ReleaseAsset,
        progress: Callable[[int, int | None], None] | None = None
    ) -> Path:
        """Dosyayi indirir, sha256 dogrular, yolunu dondurur."""

        if not _SAFE_NAME.match(asset.name):
            raise UpdateDownloadError(
                f"Gecersiz dosya adi: {asset.name}"
            )

        expected_hash = self._expected_hash(asset)

        if asset.size is not None and asset.size > MAX_DOWNLOAD_BYTES:
            raise UpdateDownloadError("Dosya cok buyuk.")

        self.target_dir.mkdir(parents=True, exist_ok=True)

        final_path = self.target_dir / asset.name
        part_path = final_path.with_name(final_path.name + ".part")

        request = Request(
            asset.download_url,
            headers={
                "Accept": "application/octet-stream",
                "User-Agent": "SentinelGuard-UpdateDownloader"
            }
        )

        hasher = hashlib.sha256()
        received = 0

        try:
            with urlopen(request, timeout=self.timeout) as response, \
                    open(part_path, "wb") as out:

                while True:
                    chunk = response.read(CHUNK_SIZE)

                    if not chunk:
                        break

                    received += len(chunk)

                    if received > MAX_DOWNLOAD_BYTES:
                        raise UpdateDownloadError("Dosya cok buyuk.")

                    hasher.update(chunk)
                    out.write(chunk)

                    if progress:
                        progress(received, asset.size)

        except UpdateDownloadError:
            self._remove(part_path)
            raise

        except HTTPError as error:
            self._remove(part_path)
            raise UpdateDownloadError(
                f"Indirme HTTP hatasi: {error.code}"
            ) from error

        except (URLError, TimeoutError, OSError) as error:
            self._remove(part_path)
            raise UpdateDownloadError(
                "Guncelleme indirilemedi."
            ) from error

        if asset.size is not None and received != asset.size:
            self._remove(part_path)
            raise UpdateDownloadError("Dosya boyutu tutmuyor.")

        if expected_hash and hasher.hexdigest() != expected_hash:
            self._remove(part_path)
            raise UpdateDownloadError("SHA256 dogrulamasi basarisiz.")

        os.replace(part_path, final_path)

        return final_path

    def _expected_hash(self, asset: ReleaseAsset) -> str | None:

        if asset.digest is None:
            if self.require_digest:
                raise UpdateDownloadError(
                    "Dosyanin SHA256 ozeti yok, kurulum guvenli degil."
                )
            return None

        match = _DIGEST.match(asset.digest)

        if not match:
            raise UpdateDownloadError(
                f"Desteklenmeyen ozet: {asset.digest}"
            )

        return match.group(1).lower()

    @staticmethod
    def _remove(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
