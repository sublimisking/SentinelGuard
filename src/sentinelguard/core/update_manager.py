"""GitHub Releases uzerinden guncelleme kontrolu ve kurulumu.

Akis:
1. ``check_for_update`` GitHub API'den yayinlari okur, mevcut surumden
   yeni olan en yuksek surumu ve onun ``*-Setup.exe`` dosyasini bulur.
2. ``download_update`` kurulum dosyasini indirir ve SHA-256 ozetini
   dogrular. Ozet yoksa veya uyusmazsa dosya silinir, kurulum yapilmaz.
3. ``launch_installer`` Inno Setup kurulumunu sessiz modda baslatir.
   Kurulum bittiginde uygulama yeniden acilir.

Bu modul Windows'a ozel hicbir sey import etmez; testler her yerde calisir.
Koruma aktifken guncelleme kurulmamasi kararini app.py verir.
"""

import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from sentinelguard.version import GITHUB_REPOSITORY, __version__

API_URL = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases"
USER_AGENT = f"SentinelGuard/{__version__}"
INSTALLER_PATTERN = re.compile(r"^SentinelGuard-.+-Setup\.exe$", re.IGNORECASE)
TIMEOUT_SECONDS = 15
MAX_INSTALLER_BYTES = 300 * 1024 * 1024

_VERSION_RE = re.compile(
    r"^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$"
)


class UpdateError(RuntimeError):
    """Guncelleme kontrolu, indirme veya dogrulama basarisiz."""


def parse_version(text):
    """'v1.2.3-beta.1' -> karsilastirilabilir anahtar.

    SemVer kurali: on surum (beta) ayni numarali son surumden kucuktur.
    """
    match = _VERSION_RE.match(str(text).strip())
    if match is None:
        raise ValueError(f"Gecersiz surum: {text!r}")

    major, minor, patch, pre = match.groups()
    core = (int(major), int(minor), int(patch))
    if pre is None:
        # Son surum her on surumden buyuk olsun.
        return core + ((1,),)

    parts = []
    for part in pre.split("."):
        if part.isdigit():
            parts.append((0, int(part), ""))
        else:
            parts.append((1, 0, part.lower()))
    return core + ((0, tuple(parts)),)


def is_newer(candidate, current=__version__):
    return parse_version(candidate) > parse_version(current)


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    tag: str
    name: str
    notes: str
    page_url: str
    asset_name: str
    download_url: str
    size: int
    sha256: str | None
    checksum_url: str | None


def _http_get(url, accept="application/vnd.github+json"):
    if not url.startswith("https://"):
        raise UpdateError("Yalnizca HTTPS baglantilarina izin verilir.")
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": accept}
    )
    return urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS)


def _read_json(url):
    try:
        with _http_get(url) as response:
            return json.loads(response.read().decode("utf-8"))
    except UpdateError:
        raise
    except Exception as error:
        raise UpdateError(f"Guncelleme sunucusuna ulasilamadi: {error}") from error


def select_update(releases, current=__version__, include_prereleases=True):
    """Yayin listesinden kurulabilir en yeni guncellemeyi sec."""
    best = None
    best_key = parse_version(current)

    for release in releases:
        if release.get("draft"):
            continue
        if release.get("prerelease") and not include_prereleases:
            continue

        tag = release.get("tag_name") or ""
        try:
            key = parse_version(tag)
        except ValueError:
            continue
        if key <= best_key:
            continue

        assets = release.get("assets") or []
        installer = next(
            (a for a in assets if INSTALLER_PATTERN.match(a.get("name", ""))),
            None,
        )
        if installer is None:
            continue

        checksum_asset = next(
            (
                a for a in assets
                if a.get("name", "").lower()
                == installer["name"].lower() + ".sha256"
            ),
            None,
        )

        sha256 = None
        digest = installer.get("digest") or ""
        if digest.lower().startswith("sha256:"):
            sha256 = digest.split(":", 1)[1].lower()

        best_key = key
        best = UpdateInfo(
            version=tag.lstrip("vV"),
            tag=tag,
            name=release.get("name") or tag,
            notes=release.get("body") or "",
            page_url=release.get("html_url") or "",
            asset_name=installer["name"],
            download_url=installer["browser_download_url"],
            size=int(installer.get("size") or 0),
            sha256=sha256,
            checksum_url=(
                checksum_asset["browser_download_url"]
                if checksum_asset else None
            ),
        )

    return best


def check_for_update(current=__version__, fetch_json=_read_json):
    """Yeni surum varsa UpdateInfo, yoksa None dondurur."""
    releases = fetch_json(f"{API_URL}?per_page=20")
    if not isinstance(releases, list):
        raise UpdateError("GitHub beklenmeyen bir yanit dondurdu.")
    return select_update(releases, current=current)


def _expected_sha256(info, opener=_http_get):
    if info.sha256:
        return info.sha256
    if not info.checksum_url:
        raise UpdateError(
            "Bu surum icin SHA-256 ozeti yok. Guvenlik icin kurulmayacak."
        )
    try:
        with opener(info.checksum_url, accept="application/octet-stream") as response:
            text = response.read(4096).decode("utf-8", "replace")
    except Exception as error:
        raise UpdateError(f"SHA-256 ozeti indirilemedi: {error}") from error

    match = re.search(r"\b([0-9a-fA-F]{64})\b", text)
    if match is None:
        raise UpdateError("SHA-256 ozet dosyasi gecersiz.")
    return match.group(1).lower()


def download_update(info, target_dir=None, opener=_http_get, progress=None):
    """Kurulumu indir, ozetini dogrula ve dosya yolunu dondur."""
    expected = _expected_sha256(info, opener=opener)

    if target_dir is None:
        target_dir = Path(tempfile.gettempdir()) / "SentinelGuardUpdate"
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    final_path = target_dir / Path(info.asset_name).name
    partial_path = final_path.with_suffix(final_path.suffix + ".part")
    digest = hashlib.sha256()
    received = 0

    try:
        with opener(info.download_url, accept="application/octet-stream") as response, \
                open(partial_path, "wb") as output:
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                received += len(chunk)
                if received > MAX_INSTALLER_BYTES:
                    raise UpdateError("Kurulum dosyasi beklenenden buyuk.")
                digest.update(chunk)
                output.write(chunk)
                if progress is not None:
                    progress(received, info.size)
    except UpdateError:
        partial_path.unlink(missing_ok=True)
        raise
    except Exception as error:
        partial_path.unlink(missing_ok=True)
        raise UpdateError(f"Guncelleme indirilemedi: {error}") from error

    if digest.hexdigest() != expected:
        partial_path.unlink(missing_ok=True)
        raise UpdateError(
            "Indirilen dosyanin SHA-256 ozeti uyusmuyor. Kurulum iptal edildi."
        )

    os.replace(partial_path, final_path)
    return final_path


def launch_installer(installer_path, popen=subprocess.Popen):
    """Inno Setup kurulumunu sessiz modda ayri bir surec olarak baslat.

    Cagiran taraf hemen ardindan uygulamayi kapatmalidir. Kurulum,
    Restart Manager ile kalan dosyalari kapatir ve bitince uygulamayi
    yeniden acar (bkz. installer/SentinelGuard.iss).
    """
    args = [
        str(installer_path),
        "/SILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/CLOSEAPPLICATIONS",
    ]
    flags = 0
    if os.name == "nt":
        flags = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
    return popen(args, close_fds=True, creationflags=flags)
