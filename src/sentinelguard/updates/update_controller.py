"""Guncelleme akisini arayuze baglar.

Ag isleri arka planda calisir. Sonuclar kuyruga girer ve Tk
ana dongusunde islenir; Tk nesnelerine baska thread dokunmaz.
"""

import queue
import threading
from collections.abc import Callable

from sentinelguard.updates.update_checker import (
    ReleaseInfo,
    UpdateCheckError,
    UpdateChecker
)
from sentinelguard.updates.update_downloader import (
    UpdateDownloader,
    UpdateDownloadError,
    select_installer
)
from sentinelguard.updates.update_installer import (
    UpdateInstaller,
    UpdateInstallError
)
from sentinelguard.updates.version_manager import VersionManager


GITHUB_OWNER = "sublimisking"
GITHUB_REPO = "SentinelGuard"

# Uygulama su an beta; beta kullanicilari beta guncellemeleri alir.
INCLUDE_PRERELEASE = True

POLL_MS = 100


def _start_thread(target: Callable[[], None]) -> None:
    threading.Thread(target=target, daemon=True).start()


class UpdateController:

    def __init__(
        self,
        root,
        version_manager: VersionManager,
        downloader: UpdateDownloader,
        installer: UpdateInstaller,
        start_thread: Callable[[Callable[[], None]], None] = _start_thread
    ):
        self.root = root
        self.version_manager = version_manager
        self.downloader = downloader
        self.installer = installer
        self._start_thread = start_thread
        self._queue: queue.Queue = queue.Queue()

        self.release: ReleaseInfo | None = None
        self.busy = False

        self._on_status: Callable[[str], None] = lambda text: None
        self._on_available: Callable[[ReleaseInfo | None], None] = (
            lambda release: None
        )
        self._can_launch: Callable[[], bool] = lambda: True
        self._shutdown: Callable[[], None] = lambda: None

    @classmethod
    def create_default(cls, root) -> "UpdateController":
        checker = UpdateChecker(GITHUB_OWNER, GITHUB_REPO)
        return cls(
            root,
            VersionManager(checker, include_prerelease=INCLUDE_PRERELEASE),
            UpdateDownloader(),
            UpdateInstaller()
        )

    def bind(
        self,
        on_status: Callable[[str], None],
        on_available: Callable[[ReleaseInfo | None], None]
    ) -> None:
        self._on_status = on_status
        self._on_available = on_available

    # --- Guncelleme kontrolu ---

    def check(self) -> None:
        if self.busy:
            return

        self.busy = True
        self._on_status("Güncellemeler kontrol ediliyor...")

        def work():
            try:
                self._queue.put(("checked", self.version_manager.find_update()))
            except UpdateCheckError as error:
                self._queue.put(("error", f"Kontrol başarısız: {error}"))

        self._start_thread(work)
        self._schedule_poll()

    # --- Indirme ve kurulum ---

    def install(
        self,
        can_launch: Callable[[], bool],
        shutdown: Callable[[], None]
    ) -> None:
        if self.busy or self.release is None:
            return

        asset = select_installer(self.release)

        if asset is None:
            self._on_status("Bu sürümde Windows kurulum dosyası yok.")
            return

        self._can_launch = can_launch
        self._shutdown = shutdown
        self.busy = True
        self._on_status("Güncelleme indiriliyor...")

        def progress(received, total):
            self._queue.put(("progress", received, total))

        def work():
            try:
                path = self.downloader.download(asset, progress=progress)
                self._queue.put(("downloaded", path))
            except UpdateDownloadError as error:
                self._queue.put(("error", f"İndirme başarısız: {error}"))

        self._start_thread(work)
        self._schedule_poll()

    # --- Kuyruk ---

    def _schedule_poll(self) -> None:
        self.root.after(POLL_MS, self._poll)

    def _poll(self) -> None:
        self.drain()

        if self.busy:
            self._schedule_poll()

    def drain(self) -> None:
        while True:
            try:
                message = self._queue.get_nowait()
            except queue.Empty:
                return

            self._handle(message)

    def _handle(self, message) -> None:
        kind = message[0]

        if kind == "progress":
            received, total = message[1], message[2]
            if total:
                percent = min(100, received * 100 // total)
                self._on_status(f"Güncelleme indiriliyor... %{percent}")
            return

        self.busy = False

        if kind == "error":
            self._on_status(message[1])

        elif kind == "checked":
            self.release = message[1]
            if self.release is None:
                self._on_status("SentinelGuard güncel.")
            else:
                self._on_status(f"Yeni sürüm var: {self.release.tag}")
            self._on_available(self.release)

        elif kind == "downloaded":
            self._launch(message[1])

    def _launch(self, path) -> None:
        # Indirme surerken koruma acilmis olabilir; tekrar bak.
        if not self._can_launch():
            self._on_status(
                "Koruma açık. Kurulum için korumayı kapatıp tekrar deneyin."
            )
            return

        try:
            self._on_status("Kurulum başlatılıyor...")
            self.installer.launch(path, self._shutdown)
        except UpdateInstallError as error:
            self._on_status(f"Kurulum başarısız: {error}")
