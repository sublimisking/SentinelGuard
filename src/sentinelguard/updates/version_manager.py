import re
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version

from sentinelguard.updates.update_checker import (
    ReleaseInfo,
    UpdateChecker
)


# Paket metadata yoksa (or. PyInstaller exe) bu kullanilir.
FALLBACK_VERSION = "0.1.1"

_PATTERN = re.compile(
    r"^v?(\d+)\.(\d+)\.(\d+)"
    r"(?:-(alpha|beta|rc)(?:\.(\d+))?)?$",
    re.IGNORECASE
)

_STAGE_ORDER = {"alpha": 0, "beta": 1, "rc": 2}
_STABLE = 3


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int
    stage: int
    number: int

    @classmethod
    def parse(cls, text: str) -> "Version":
        match = _PATTERN.match(text.strip())

        if not match:
            raise ValueError(f"Gecersiz surum: {text}")

        major, minor, patch, stage, number = match.groups()

        return cls(
            int(major),
            int(minor),
            int(patch),
            _STAGE_ORDER[stage.lower()] if stage else _STABLE,
            int(number or 0)
        )

    @property
    def is_prerelease(self) -> bool:
        return self.stage != _STABLE


def get_current_version() -> Version:
    """Calisan uygulamanin surumunu dondurur."""

    try:
        text = version("sentinelguard")
    except PackageNotFoundError:
        text = FALLBACK_VERSION

    return Version.parse(text)


class VersionManager:

    def __init__(
        self,
        checker: UpdateChecker,
        current: Version | None = None,
        include_prerelease: bool = False
    ):
        self.checker = checker
        self.current = current or get_current_version()
        self.include_prerelease = include_prerelease

    def find_update(self) -> ReleaseInfo | None:
        """GitHub'a bakar. Daha yeni surum varsa dondurur, yoksa None.

        UpdateCheckError disari firlatilir; arayan karar verir.
        """

        best: tuple[Version, ReleaseInfo] | None = None

        for release in self.checker.fetch_releases():

            try:
                candidate = Version.parse(release.tag)
            except ValueError:
                continue

            if (
                (release.is_prerelease or candidate.is_prerelease)
                and not self.include_prerelease
            ):
                continue

            if candidate <= self.current:
                continue

            if best is None or candidate > best[0]:
                best = (candidate, release)

        return best[1] if best else None
