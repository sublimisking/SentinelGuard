import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen


MAX_RESPONSE_BYTES = 4 * 1024 * 1024


class UpdateCheckError(RuntimeError):
    """GitHub surum bilgisi alinamadiginda olusur."""


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    download_url: str
    size: int | None
    digest: str | None


@dataclass(frozen=True)
class ReleaseInfo:
    tag: str
    title: str
    is_prerelease: bool
    notes: str
    page_url: str
    assets: tuple[ReleaseAsset, ...]


class UpdateChecker:

    def __init__(
        self,
        owner: str,
        repo: str,
        timeout: float = 8.0
    ):
        if (
            not owner
            or not repo
            or "/" in owner
            or "/" in repo
        ):
            raise ValueError(
                "GitHub kullanici adi veya depo adi gecersiz."
            )

        if timeout <= 0:
            raise ValueError(
                "Zaman asimi pozitif olmali."
            )

        self.owner = owner
        self.repo = repo
        self.timeout = timeout

        self.url = (
            "https://api.github.com/repos/"
            f"{quote(owner, safe='')}/"
            f"{quote(repo, safe='')}/releases?per_page=30"
        )

    def fetch_releases(self) -> list[ReleaseInfo]:
        """GitHub'daki yayimlanmis surumleri getirir."""

        request = Request(
            self.url,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "SentinelGuard-UpdateChecker"
            }
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout
            ) as response:
                raw = response.read(
                    MAX_RESPONSE_BYTES + 1
                )

        except HTTPError as error:
            raise UpdateCheckError(
                f"GitHub API HTTP hatasi: {error.code}"
            ) from error

        except (URLError, TimeoutError, OSError) as error:
            raise UpdateCheckError(
                "GitHub'a baglanilamadi."
            ) from error

        if len(raw) > MAX_RESPONSE_BYTES:
            raise UpdateCheckError(
                "Surum verisi beklenenden buyuk."
            )

        try:
            payload = json.loads(
                raw.decode("utf-8")
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError
        ) as error:
            raise UpdateCheckError(
                "GitHub gecersiz JSON cevabi gonderdi."
            ) from error

        if not isinstance(payload, list):
            raise UpdateCheckError(
                "GitHub surum listesi gecersiz."
            )

        releases = []

        for item in payload:

            if not isinstance(item, dict):
                continue

            if item.get("draft") is True:
                continue

            tag = item.get("tag_name")

            if not isinstance(tag, str) or not tag.strip():
                continue

            assets = []
            asset_list = item.get("assets")

            if isinstance(asset_list, list):

                for asset in asset_list:

                    if not isinstance(asset, dict):
                        continue

                    name = asset.get("name")
                    link = asset.get("browser_download_url")

                    if (
                        not isinstance(name, str)
                        or not isinstance(link, str)
                    ):
                        continue

                    parts = urlsplit(link)

                    expected_prefix = (
                        f"/{self.owner}/{self.repo}"
                        "/releases/download/"
                    )

                    if (
                        parts.scheme != "https"
                        or parts.hostname != "github.com"
                        or parts.username is not None
                        or parts.password is not None
                        or parts.port not in (None, 443)
                        or not parts.path.lower().startswith(
                            expected_prefix.lower()
                        )
                    ):
                        continue

                    size = asset.get("size")
                    digest = asset.get("digest")

                    assets.append(
                        ReleaseAsset(
                            name=name,
                            download_url=link,
                            size=(
                                size
                                if isinstance(size, int)
                                and size >= 0
                                else None
                            ),
                            digest=(
                                digest
                                if isinstance(digest, str)
                                else None
                            )
                        )
                    )

            title = item.get("name")
            notes = item.get("body")
            page_url = item.get("html_url")

            releases.append(
                ReleaseInfo(
                    tag=tag,
                    title=(
                        title
                        if isinstance(title, str) and title
                        else tag
                    ),
                    is_prerelease=(
                        item.get("prerelease") is True
                    ),
                    notes=(
                        notes if isinstance(notes, str) else ""
                    ),
                    page_url=(
                        page_url
                        if isinstance(page_url, str)
                        else ""
                    ),
                    assets=tuple(assets)
                )
            )

        return releases
