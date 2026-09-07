"""
Archiving of test artefacts (logs, coverage databases, test DB snapshots).

One convention, used by everything that needs to keep an older copy of
something around:

    <target>/00_archive/<YYYYMMDD_HHMM>.<ext>

Compression is done with the standard library only. LibreFolio runs on macOS
today and on Linux or Windows tomorrow, so shelling out to ``tar``/``xz``/``zstd``
would make the behaviour depend on whatever happens to be installed. ``lzma``
and ``bz2`` are *optional* CPython modules (a build without ``liblzma`` simply
does not expose them, which happens on minimal Linux images), hence the probe
below degrades one step at a time and ends on ``gzip``, which is always there.

Measured on the project's own artefacts — ``lzma`` at preset 1 is the sweet
spot, beating an external ``zstd -3`` on both size and time:

    4.3 MB run log  →  0.16 MB (27x) in 0.04 s
    1.4 MB test DB  →  0.25 MB (5.5x) in 0.04 s

SQLite files compress well despite being binary: their pages are mostly text
and slack.
"""

import re
import shutil
import tarfile
from datetime import datetime
from pathlib import Path

from ._common import Colors

ARCHIVE_DIR_NAME = "00_archive"

#: preset 1 keeps ~90% of the ratio of preset 6 for a twelfth of the cost.
_LZMA_PRESET = 1


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _unique(path: Path) -> Path:
    """
    Never overwrite an existing archive.

    Timestamps have second granularity, so two archives created in the same
    second would collide and the older one would vanish without a word — which
    is the opposite of what archiving is for.
    """
    if not path.exists():
        return path
    stem = path.name
    # Keep the full multi-part suffix (".tar.xz"), not just the last one.
    for ext in (".tar.xz", ".tar.bz2", ".tar.gz", ".tar"):
        if stem.endswith(ext):
            base, suffix = stem[: -len(ext)], ext
            break
    else:
        base, suffix = path.stem, path.suffix
    n = 2
    while (candidate := path.with_name(f"{base}_{n}{suffix}")).exists():
        n += 1
    return candidate


def best_tar_mode() -> tuple[str, str]:
    """
    Pick the best tar compression this interpreter can actually perform.

    Returns:
        tuple[str, str]: (tarfile mode, file extension), degrading
        ``xz`` → ``bz2`` → ``gz`` → uncompressed. Never raises: the last step
        needs only ``zlib``, which is always available.
    """
    try:
        import lzma  # noqa: F401,PLC0415 — probing availability, not using it here

        return "w:xz", ".tar.xz"
    except ImportError:
        pass
    try:
        import bz2  # noqa: F401,PLC0415 — probing availability, not using it here

        return "w:bz2", ".tar.bz2"
    except ImportError:
        pass
    try:
        import zlib  # noqa: F401,PLC0415 — probing availability, not using it here

        return "w:gz", ".tar.gz"
    except ImportError:
        return "w", ".tar"


def _add_to_tar(tar: tarfile.TarFile, path: Path, arcname: str) -> None:
    tar.add(str(path), arcname=arcname)


def archive_path(source: Path, target_dir: Path | None = None, label: str | None = None, *, move: bool = False, quiet: bool = False) -> Path | None:
    """
    Archive a file or directory into ``<target_dir>/00_archive/``, compressed.

    Args:
        source: file or directory to archive. Missing/empty → no-op.
        target_dir: where ``00_archive/`` lives. Defaults to the source's parent.
        label: name stem for the archive. Defaults to the source's name.
        move: remove the source once archived (used when the source is about to
            be rewritten anyway).
        quiet: suppress the confirmation line.

    Returns:
        Path | None: the archive written, or None when there was nothing to do.
    """
    source = Path(source)
    if not source.exists():
        return None
    if source.is_dir() and not any(source.iterdir()):
        return None

    target_dir = Path(target_dir) if target_dir else source.parent
    archive_dir = target_dir / ARCHIVE_DIR_NAME
    archive_dir.mkdir(parents=True, exist_ok=True)

    stem = label or source.name
    mode, ext = best_tar_mode()
    dest = _unique(archive_dir / f"{stem}_{_timestamp()}{ext}")

    kwargs = {"preset": _LZMA_PRESET} if mode == "w:xz" else {}
    try:
        with tarfile.open(dest, mode, **kwargs) as tar:  # type: ignore[call-overload]
            _add_to_tar(tar, source, arcname=stem)
    except Exception as exc:  # pragma: no cover — archiving must never break a run
        print(f"   {Colors.YELLOW}⚠️  Could not archive {source.name}: {exc}{Colors.NC}")
        return None

    if move:
        if source.is_dir():
            shutil.rmtree(source, ignore_errors=True)
        else:
            source.unlink(missing_ok=True)

    if not quiet:
        size_mb = dest.stat().st_size / 1_048_576
        print(f"   {Colors.GREEN}📦 Archived {stem} → {ARCHIVE_DIR_NAME}/{dest.name} ({size_mb:.2f} MB){Colors.NC}")
    return dest


def prepare_log_dir(log_dir: Path) -> Path:
    """
    Make ``log_dir`` ready to receive this run's logs.

    Existing logs are not deleted: they are moved into
    ``log_dir/00_archive/<timestamp>.tar.xz`` so a previous run stays available
    for comparison while costing almost nothing on disk.
    """
    log_dir = Path(log_dir).expanduser().resolve()
    log_dir.mkdir(parents=True, exist_ok=True)

    previous = [p for p in log_dir.iterdir() if p.name != ARCHIVE_DIR_NAME]
    if previous:
        archive_dir = log_dir / ARCHIVE_DIR_NAME
        archive_dir.mkdir(exist_ok=True)
        mode, ext = best_tar_mode()
        dest = _unique(archive_dir / f"logs_{_timestamp()}{ext}")
        kwargs = {"preset": _LZMA_PRESET} if mode == "w:xz" else {}
        try:
            with tarfile.open(dest, mode, **kwargs) as tar:  # type: ignore[call-overload]
                for item in previous:
                    _add_to_tar(tar, item, arcname=item.name)
            for item in previous:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
            size_mb = dest.stat().st_size / 1_048_576
            print(f"   {Colors.GREEN}📦 Archived {len(previous)} previous log(s) → {ARCHIVE_DIR_NAME}/{dest.name} ({size_mb:.2f} MB){Colors.NC}")
        except Exception as exc:  # pragma: no cover — never block a run over old logs
            print(f"   {Colors.YELLOW}⚠️  Could not archive previous logs: {exc}{Colors.NC}")

    return log_dir


def snapshot_test_db(log_dir: Path, label: str = "test-db") -> Path | None:
    """
    Keep a compressed copy of the test DB next to the run's logs.

    A red is only reproducible with the data that produced it. SQLite files
    compress well despite being binary (1.4 MB → 0.25 MB measured here), so the
    snapshot costs almost nothing and removes the usual "it failed but the DB has
    moved on since" dead end.
    """
    try:
        from backend.test_scripts.test_db_config import TEST_DB_PATH

        db = Path(TEST_DB_PATH)
        if not db.exists():
            return None
        return archive_path(db, target_dir=Path(log_dir), label=label, quiet=True)
    except Exception:
        return None



_SLUG_RE = re.compile(r"[^A-Za-z0-9._-]+")


def log_file_for(log_dir: Path, category: str, unit: str) -> Path:
    """
    Build the log path for one test unit.

    The name carries category and unit so a failure can be located by eye:
    ``front-transaction__tx-wac-mode.log``. Descriptions come from the runner and
    contain spaces, colons and parentheses, so they are slugified; if two units
    share a description the second gets a numeric suffix rather than silently
    overwriting the first.
    """
    def _slug(value: str) -> str:
        return _SLUG_RE.sub("-", (value or "unit").strip()).strip("-_.")[:80] or "unit"

    base = f"{_slug(category)}__{_slug(unit)}"
    path = log_dir / f"{base}.log"
    n = 2
    while path.exists():
        path = log_dir / f"{base}_{n}.log"
        n += 1
    return path
