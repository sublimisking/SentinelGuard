import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from sentinelguard.updates.update_downloader import DEFAULT_UPDATE_DIR


class UpdateInstallError(RuntimeError):
    """Kurulum baslatilamadi."""


class UpdateInstaller:
    """Inno Setup kurulumunu sessiz modda baslatir.

    Kurulum ayri surecte calisir. Uygulama hemen kapanmali ki
    kurulum dosyalari degistirebilsin. Kurulum bitince .iss
    icindeki [Run] satiri uygulamayi tekrar acar.
    """

    def __init__(
        self,
        allowed_dir: Path | None = None,
        popen: Callable[..., object] = subprocess.Popen
    ):
        self.allowed_dir = Path(allowed_dir or DEFAULT_UPDATE_DIR)
        self._popen = popen

    def build_command(self, installer: Path) -> list[str]:
        log_path = installer.with_suffix(".log")

        return [
            str(installer),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/CLOSEAPPLICATIONS",
            f"/LOG={log_path}"
        ]

    def launch(
        self,
        installer: Path,
        shutdown: Callable[[], None]
    ) -> None:
        """Kurulumu baslatir, sonra shutdown() ile uygulamayi kapatir."""

        if sys.platform != "win32":
            raise UpdateInstallError(
                "Otomatik kurulum sadece Windows'ta calisir."
            )

        path = self._validate(installer)

        flags = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )

        try:
            self._popen(
                self.build_command(path),
                creationflags=flags,
                close_fds=True,
                cwd=str(path.parent)
            )
        except OSError as error:
            raise UpdateInstallError(
                "Kurulum baslatilamadi."
            ) from error

        shutdown()

    def _validate(self, installer: Path) -> Path:

        try:
            path = Path(installer).resolve(strict=True)
            allowed = self.allowed_dir.resolve(strict=True)
        except OSError as error:
            raise UpdateInstallError(
                "Kurulum dosyasi bulunamadi."
            ) from error

        if not path.is_file() or path.suffix.lower() != ".exe":
            raise UpdateInstallError(
                "Kurulum dosyasi gecersiz."
            )

        if path.parent != allowed:
            raise UpdateInstallError(
                "Kurulum dosyasi guvenilir klasorde degil."
            )

        if os.path.getsize(path) == 0:
            raise UpdateInstallError("Kurulum dosyasi bos.")

        return path
