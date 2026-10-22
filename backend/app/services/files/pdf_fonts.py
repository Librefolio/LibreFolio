"""The PDF viewer's Chinese, Japanese and Korean fonts, fetched once and served by the instance (lot H-55, decision (c)).

Owner: workstream H (platform). The viewer (``frontend/src/lib/utils/files/pdfViewerAssets.ts``) asks for a CJK font only
when a PDF needs it, and asks the instance: the Content-Security-Policy keeps ``connect-src 'self'``, so the browser never
reaches a third party. These fonts are tens of megabytes each, too heavy for the image: the instance fetches a file once
from jsDelivr, at the version the lock installed, and keeps it only if its sha256 is the one the list holds
(``pdf_font_hashes.json``, written by ``frontend/scripts/pdf-font-hashes.mjs`` from the copies in ``node_modules`` and
kept equal to them by a test). A file is kept in ``DATA_DIR/cache/pdf-fonts/<package>/<file>``: written under a temporary
name, renamed once complete, never before its hash was checked. Only the files of the list are ever fetched, from one
fixed host: no name of a request reaches the network.

Everything here is blocking (file and network I/O): the route calls it through ``asyncio.to_thread``.
"""

import hashlib
import json
import os
import tempfile
import threading
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import httpx

from backend.app.config import get_data_dir
from backend.app.logging_config import get_logger

logger = get_logger(__name__)

#: The only host the fonts are fetched from: the CDN the viewer used before, now the instance's own source.
PDF_FONT_SOURCE = "https://cdn.jsdelivr.net/npm/@embedpdf"
#: The list of the fonts the instance may fetch, with their sizes and sha256.
FONT_LIST_FILE = Path(__file__).with_name("pdf_font_hashes.json")
#: How long a fetch may take before the source counts as unreachable.
FETCH_TIMEOUT_SECONDS = 60.0


class PdfFontUnknown(LookupError):
    """No font of the list has this package and file name."""


class PdfFontUnavailable(RuntimeError):
    """The source of the fonts cannot give the file now: the PDF is shown without those glyphs."""


class PdfFontMismatch(RuntimeError):
    """The file the source gave is not the one the list expects: it is thrown away."""


@dataclass(frozen=True)
class FontEntry:
    """A font of the list: its package, its file name, its size and its sha256."""

    package: str
    file: str
    size: int
    sha256: str


@cache
def font_list() -> dict:
    """The list of the fonts the instance may fetch, as ``pdf_font_hashes.json`` holds it: ``version`` and ``files``."""
    return json.loads(FONT_LIST_FILE.read_text(encoding="utf-8"))


def font_entry(package: str, file: str) -> FontEntry | None:
    """The font of the list named exactly ``package``/``file``; None for any other name."""
    for item in font_list()["files"]:
        if item["package"] == package and item["file"] == file:
            return FontEntry(item["package"], item["file"], int(item["size"]), item["sha256"])
    return None


def source_url(entry: FontEntry | dict, version: str) -> str:
    """Where the source keeps ``entry`` (a ``FontEntry``, or an item of the list) at ``version``."""
    package, file = (entry["package"], entry["file"]) if isinstance(entry, dict) else (entry.package, entry.file)
    return f"{PDF_FONT_SOURCE}/{package}@{version}/fonts/{file}"


def fetch_font_bytes(url: str, max_bytes: int) -> bytes:
    """The bytes the source answers at ``url``, at most ``max_bytes``; ``PdfFontUnavailable`` otherwise."""
    try:
        with httpx.Client(timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=False) as client, client.stream("GET", url) as response:
            if response.status_code != 200:
                raise PdfFontUnavailable(f"the font source answered {response.status_code}")
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise PdfFontUnavailable("the font source sent more than the expected size")
            return bytes(body)
    except httpx.HTTPError as exc:
        raise PdfFontUnavailable(f"the font source cannot be reached: {type(exc).__name__}") from exc


def cache_dir() -> Path:
    """Where the fonts are kept, in the data directory of the moment."""
    return get_data_dir() / "cache" / "pdf-fonts"


_locks: dict[tuple[str, str], threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(key: tuple[str, str]) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def _usable(path: Path, entry: FontEntry) -> bool:
    try:
        return path.is_file() and path.stat().st_size == entry.size
    except OSError:
        return False


def cached_font(package: str, file: str) -> Path:
    """The file of the font ``package``/``file``, fetched and checked the first time; blocking.

    Raises ``PdfFontUnknown`` for a name outside the list, ``PdfFontUnavailable`` when the source cannot give it,
    ``PdfFontMismatch`` when what it gives is not the expected file (nothing is kept).
    """
    entry = font_entry(package, file)
    if entry is None:
        raise PdfFontUnknown(f"{package}/{file}")
    path = cache_dir() / entry.package / entry.file
    if _usable(path, entry):
        return path
    with _lock_for((entry.package, entry.file)):
        # Another request may have fetched it while this one waited for the lock
        if _usable(path, entry):
            return path
        body = fetch_font_bytes(source_url(entry, font_list()["version"]), entry.size)
        if len(body) != entry.size or hashlib.sha256(body).hexdigest() != entry.sha256:
            logger.warning("A PDF font from the source is not the expected file: thrown away", package=entry.package, file=entry.file, size=len(body))
            raise PdfFontMismatch(f"{entry.package}/{entry.file}")
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{entry.file}.", suffix=".part")
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(body)
            os.replace(temporary, path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
        logger.info("A PDF font was fetched and kept", package=entry.package, file=entry.file, size=entry.size)
        return path
