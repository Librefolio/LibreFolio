#!/usr/bin/env python3
"""Check that no live price reached the backend while a gallery snapshot was captured (LibreFolio visual review).

The gallery is offline: its guard (frontend/e2e/fixtures/galleryReportSets.ts, `guardGalleryOffline`) answers the
pages' live-price poll, `POST /api/v1/assets/prices/current`, from fixtures. A poll that reaches the backend anyway
asks the asset's provider and writes today's candle into the lane's database (the endpoint's documented side
effect), and every later shot that depends on that asset changes. On 14/10/2026 one such tick, sent while the
guard was already removed at the end of a test, rewrote Apple's candle from Yahoo halfway through a run and voided
a noise measure. Any capture used for a comparison — noise run, reference, candidate — must therefore be clean.

The backend's log (`<data dir>/logs/librefolio.log`, JSON lines at DEBUG level in the test server) records every
step of that path. This script reads, from each snapshot's meta.json, when the capture started, how long it took
and which lane data directory it used, and counts the live-price lines the log holds for that time window.

Run from the repository root with the project venv, like the other visual review tools (standard library only):
    pipenv run python -m scripts.visual_review.live_price_check <work>/snapshots/<label> [<work>/snapshots/<label2> ...]
        [--log <data dir>/logs/librefolio.log]   # default: the data_dir written in each meta.json
        [--show 20]                              # matching lines to print per snapshot

Exit status: 0 every snapshot is clean; 1 a live price reached the backend during a capture — that capture is
void, capture it again; 2 a snapshot could not be verified (no meta.json, no log, a log that does not cover the
capture, or a log without DEBUG lines, where the markers are never written).
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# The live-price path logs these, and nothing else does (backend/app/services/assets/price_query.py and the
# Yahoo Finance plugin). One line is enough to void a capture.
MARKERS: tuple[tuple[str, str], ...] = (
    ("current_value for", "a provider answered a live quote (Yahoo Finance)"),
    ("[Intra-day price extend]", "today's candle updated in the database"),
    ("[F.2 bootstrap]", "today's candle created in the database"),
    ("Current-price persist", "the live-price path persisted, or skipped, fresh quotes"),
    ("Current-price cache HIT", "a live-price request reached the backend (answered from its cache)"),
    ("Provider current-price failed", "a live-price request reached a provider, which failed"),
    ("Current-price OHLC persist failed", "the live-price path failed to write today's candle"),
)
# The backend's clock and the runner's agree (same machine): a little slack, for the last lines of a server stopping.
AFTER_END = timedelta(seconds=30)
TIMESTAMP = re.compile(r'"timestamp": "([^"]+)"')
EVENT = re.compile(r'"event": "((?:[^"\\]|\\.)*)"')
LOGGER = re.compile(r'"logger": "([^"]+)"')


def parse_time(text: str) -> datetime:
    """An ISO 8601 instant with an offset, as meta.json (`+0200`) and the backend's log (`Z`) write it."""
    text = text.strip().replace("Z", "+00:00")
    for pattern in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    raise ValueError(f"not an ISO 8601 instant with an offset: {text!r}")


def read_meta(snapshot: Path) -> dict:
    """meta.json, read leniently: a snapshot whose extra arguments held a backslash was written as invalid JSON."""
    path = snapshot / "meta.json"
    raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        meta: dict = {}
        for key in ("label", "started", "data_dir"):
            found = re.search(rf'"{key}":\s*"([^"]*)"', raw)
            if found:
                meta[key] = found.group(1)
        found = re.search(r'"duration_s":\s*(\d+)', raw)
        if found:
            meta["duration_s"] = int(found.group(1))
        return meta


class Capture:
    """One snapshot: its time window, the log it is checked against, and what that log holds for the window."""

    def __init__(self, snapshot: Path, log_override: Path | None):
        self.snapshot = snapshot
        self.label = snapshot.name
        self.problem: str | None = None
        self.lines_in_window = 0
        self.debug_in_window = 0
        self.hits: dict[str, list[str]] = {marker: [] for marker, _ in MARKERS}
        self.log: Path | None = None
        self.start = self.end = None
        if not (snapshot / "meta.json").is_file():
            self.problem = f"no meta.json in {snapshot}"
            return
        meta = read_meta(snapshot)
        self.label = meta.get("label") or snapshot.name
        if "started" not in meta or "duration_s" not in meta:
            self.problem = "meta.json has no started/duration_s: the capture did not finish"
            return
        self.start = parse_time(meta["started"])
        self.end = self.start + timedelta(seconds=int(meta["duration_s"])) + AFTER_END
        if log_override:
            self.log = log_override
        elif meta.get("data_dir"):
            self.log = Path(meta["data_dir"]) / "logs" / "librefolio.log"
        else:
            self.problem = "meta.json names no data_dir: pass --log"

    def covers(self, instant: datetime) -> bool:
        return self.start is not None and self.start <= instant <= self.end


def log_files(main: Path, since: datetime) -> list[Path]:
    """The lane's log and any rotated copy written since `since` (the backend rotates weekly, and gzips the old file)."""
    files = [path for path in sorted(main.parent.glob(main.name + ".*")) if datetime.fromtimestamp(path.stat().st_mtime, tz=UTC) >= since]
    return files + ([main] if main.is_file() else [])


def open_text(path: Path):
    return gzip.open(path, "rt", encoding="utf-8", errors="replace") if path.suffix == ".gz" else path.open(encoding="utf-8", errors="replace")


def scan(log: Path, captures: list[Capture]) -> None:
    """One pass over the log (and its rotated copies) for every capture checked against it."""
    since = min(capture.start for capture in captures)
    for path in log_files(log, since):
        with open_text(path) as lines:
            for line in lines:
                found = TIMESTAMP.search(line)
                if not found:
                    continue
                try:
                    instant = parse_time(found.group(1))
                except ValueError:
                    continue
                for capture in captures:
                    if not capture.covers(instant):
                        continue
                    capture.lines_in_window += 1
                    if '"level": "DEBUG"' in line:
                        capture.debug_in_window += 1
                    for marker, _ in MARKERS:
                        if marker in line:
                            capture.hits[marker].append(line)


def describe(line: str) -> str:
    when = TIMESTAMP.search(line)
    event = EVENT.search(line)
    logger = LOGGER.search(line)
    return f"{when.group(1) if when else '?'}  {event.group(1) if event else line.strip()[:160]}  [{logger.group(1) if logger else '?'}]"


def load(snapshots: list[Path], log_override: Path | None) -> list[Capture]:
    """The captures, each scanned against its log — one pass per log, however many captures share it."""
    captures = [Capture(snapshot, log_override) for snapshot in snapshots]
    by_log: dict[Path, list[Capture]] = {}
    for capture in captures:
        if capture.problem:
            continue
        if not capture.log.is_file():
            capture.problem = f"no backend log at {capture.log}: pass --log"
            continue
        by_log.setdefault(capture.log, []).append(capture)
    for log, group in by_log.items():
        scan(log, group)
    return captures


def unverifiable(capture: Capture) -> str | None:
    """Why the log cannot vouch for the capture, if it cannot: a clean answer from the wrong file would be a false one."""
    if capture.problem:
        return capture.problem
    if capture.lines_in_window == 0:
        return f"{capture.log} holds no line between the capture's start and end: wrong log or data dir?"
    if capture.debug_in_window == 0:
        return f"{capture.log} holds no DEBUG line for the capture: the live-price markers are written at DEBUG only"
    return None


def report(capture: Capture, show: int) -> int:
    """Print the verdict on one capture; return its exit status (0 clean, 1 void, 2 cannot verify)."""
    problem = unverifiable(capture)
    if problem:
        print(f"❔ {capture.label}: cannot verify — {problem}")
        return 2
    window = f"{capture.start.astimezone():%Y-%m-%d %H:%M:%S} → {capture.end.astimezone():%H:%M:%S}"
    total = sum(len(lines) for lines in capture.hits.values())
    print(f"{'✅' if total == 0 else '❌'} {capture.label}: {window}, {capture.lines_in_window} log lines in the window ({capture.log})")
    if total == 0:
        print("   no live-price line: no live price reached the backend during the capture")
        return 0
    for marker, meaning in MARKERS:
        if capture.hits[marker]:
            print(f"   {len(capture.hits[marker]):>4} × «{marker}» — {meaning}")
    for line in sorted({line for lines in capture.hits.values() for line in lines}, key=lambda line: (TIMESTAMP.search(line) or EVENT.search(line)).group(1))[:show]:
        print(f"     {describe(line)}")
    print(f"   VOID: a live price reached the backend during {capture.label} — capture it again")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("snapshots", nargs="+", type=Path, help="snapshot directories written by gallery_snapshot.sh")
    parser.add_argument("--log", type=Path, help="the lane's backend log (default: <data_dir of meta.json>/logs/librefolio.log)")
    parser.add_argument("--show", type=int, default=20, help="matching lines to print per snapshot (default 20)")
    args = parser.parse_args()
    return max(report(capture, args.show) for capture in load(args.snapshots, args.log))


if __name__ == "__main__":
    sys.exit(main())
