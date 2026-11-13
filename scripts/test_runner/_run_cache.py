"""
Test Run Cache - resume interrupted test suites.

Persists pass/fail state for test suites so that --resume can skip
already-passed tests and restart from the last failure point.

Cache file: scripts/test_runner/.run_cache.json (gitignored)

A second, independent file tracks the *campaign*: the sequence of invocations
that a ``--fresh-run`` opens and the following ``--resume`` runs continue. It is
deliberately not part of the run cache, because ``clear_all()`` wipes that file
and the campaign is precisely what has to survive the wipe that starts it.

Campaign file: scripts/test_runner/.campaign.json (gitignored)

A third record is the run's durations (project 71, step 3.10): what each spec, test, Vitest file and pytest unit took, read
from the reports the consolidated passes already parse for their verdicts. They are kept for one run in
``.coverage_data/durations.json``, which the invocation's campaign record names. ``.coverage_data/unit_durations.json``
(``_scheduler.py``) stays what it is: the history the parallel pass balances its workers on.
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

_CACHE_FILE = Path(__file__).parent / ".run_cache.json"
_CAMPAIGN_FILE = Path(__file__).parent / ".campaign.json"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
#: One run's durations, beside the coverage reports.
DURATIONS_FILE = _PROJECT_ROOT / ".coverage_data" / "durations.json"
#: The stopwatch lines of the E2E coverage collection (``LF_COV_TIMING=1``), summarised into the durations when present.
TIMING_DIR = _PROJECT_ROOT / "frontend" / "coverage-js" / "timing"
_TIMING_PROBE = _PROJECT_ROOT / "frontend" / "scripts" / "js-coverage-probe.mjs"


def _load_all() -> dict:
    """Load the entire cache file."""
    if not _CACHE_FILE.exists():
        return {}
    try:
        return json.loads(_CACHE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_all(data: dict) -> None:
    """Write the entire cache file."""
    _CACHE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def load_cache(suite_key: str) -> dict:
    """Load cache entry for a specific suite."""
    all_data = _load_all()
    return all_data.get(suite_key, {"passed": [], "failed": None, "timestamp": None})


def mark_passed(suite_key: str, test_name: str) -> None:
    """Mark a test as passed within a suite."""
    all_data = _load_all()
    entry = all_data.setdefault(suite_key, {"passed": [], "failed": None, "timestamp": None})
    if test_name not in entry["passed"]:
        entry["passed"].append(test_name)
    if entry["failed"] == test_name:
        entry["failed"] = None
    entry["timestamp"] = datetime.now().isoformat(timespec="seconds")
    _save_all(all_data)


def mark_failed(suite_key: str, test_name: str) -> None:
    """Mark a test as failed (stopping point for resume)."""
    all_data = _load_all()
    entry = all_data.setdefault(suite_key, {"passed": [], "failed": None, "timestamp": None})
    entry["failed"] = test_name
    entry["timestamp"] = datetime.now().isoformat(timespec="seconds")
    _save_all(all_data)


def is_passed(suite_key: str, test_name: str) -> bool:
    """Check if a test was already passed in the current run."""
    entry = load_cache(suite_key)
    return test_name in entry["passed"]


def clear_suite(suite_key: str) -> None:
    """Clear cache for a specific suite (full pass completed)."""
    all_data = _load_all()
    if suite_key in all_data:
        del all_data[suite_key]
        _save_all(all_data)


def clear_all() -> None:
    """Clear all cached run state (fresh start)."""
    if _CACHE_FILE.exists():
        _CACHE_FILE.unlink()


def show_status() -> str:
    """Return a formatted status string of the current cache."""
    all_data = _load_all()
    if not all_data:
        return "No active test run cache. All suites start fresh."

    lines = []
    for suite_key, entry in all_data.items():
        passed = entry.get("passed", [])
        failed = entry.get("failed")
        ts = entry.get("timestamp", "?")
        lines.append("")
        lines.append(f"  \U0001f4cb {suite_key} (last update: {ts})")
        lines.append(f"     \u2705 Passed: {len(passed)} test(s)")
        if passed:
            for t in passed:
                lines.append(f"        \u2022 {t}")
        if failed:
            lines.append(f"     \u274c Stopped at: {failed}")
        else:
            lines.append(f"     \u23f3 Next: resume will continue from test #{len(passed) + 1}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Campaign timing
#
# One campaign = one --fresh-run plus every --resume that follows it. Two
# durations are worth reporting and they answer different questions:
#
#   machine time — the sum of the invocations: how long the suite costs to run
#   wall time    — from the fresh-run to now: machine time plus the gaps in
#                  between, which is where fixes were written
#
# Reporting only the first hides that a "40-minute suite" took an afternoon;
# reporting only the second blames the runner for the time spent editing.
# ---------------------------------------------------------------------------


def _load_campaign() -> dict:
    """Load the campaign file, tolerating absence and corruption."""
    if not _CAMPAIGN_FILE.exists():
        return {}
    try:
        return json.loads(_CAMPAIGN_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def campaign_begin(reset: bool) -> None:
    """Open a campaign, or join the one already running.

    ``reset`` is the --fresh-run flag: it starts the clock over. Without it an
    existing campaign is continued, so a --resume adds to the same total
    instead of pretending the earlier invocations never happened.
    """
    data = _load_campaign()
    if reset or not data.get("started_at"):
        data = {"started_at": datetime.now().isoformat(timespec="seconds"), "runs": []}
    data["current_started_monotonic"] = time.monotonic()
    data["current_started_at"] = datetime.now().isoformat(timespec="seconds")
    try:
        _CAMPAIGN_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    except OSError:
        pass


def campaign_end(success: bool, label: str, fresh: bool, resumed: bool, durations: str | None = None) -> None:
    """Close the current invocation and record it in the campaign, with the path of its durations file when it wrote one."""
    data = _load_campaign()
    started = data.get("current_started_monotonic")
    if started is None:
        return
    run = {
        "label": label,
        "kind": "fresh" if fresh else ("resume" if resumed else "plain"),
        "started_at": data.get("current_started_at"),
        "ended_at": datetime.now().isoformat(timespec="seconds"),
        "seconds": round(max(0.0, time.monotonic() - started), 1),
        "success": bool(success),
    }
    if durations:
        run["durations"] = durations
    data.setdefault("runs", []).append(run)
    data.pop("current_started_monotonic", None)
    data.pop("current_started_at", None)
    try:
        _CAMPAIGN_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    except OSError:
        pass


def format_duration(seconds: float) -> str:
    """Render a duration the way a person reads a stopwatch."""
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def campaign_summary() -> str:
    """Return the closing note: how long this took, and how long it has taken."""
    data = _load_campaign()
    runs = data.get("runs") or []
    if not runs:
        return ""

    last = runs[-1]
    machine = sum(float(r.get("seconds") or 0) for r in runs)
    started_at = data.get("started_at")

    lines = [f"   \u23f1\ufe0f  This invocation: {format_duration(float(last.get('seconds') or 0))}"]

    if len(runs) > 1:
        kinds: dict[str, int] = {}
        for r in runs:
            kinds[r.get("kind", "plain")] = kinds.get(r.get("kind", "plain"), 0) + 1
        breakdown = ", ".join(f"{n} {k}" for k, n in kinds.items())
        lines.append(f"   \U0001f501 Invocations:    {len(runs)} ({breakdown})")
        lines.append(f"   \u2699\ufe0f  Machine time:   {format_duration(machine)}  (sum of every invocation)")

    if started_at:
        try:
            wall = (datetime.now() - datetime.fromisoformat(started_at)).total_seconds()
        except ValueError:
            wall = None
        if wall is not None and wall >= 0:
            since = started_at.replace("T", " ")
            suffix = "  (includes the time between runs)" if len(runs) > 1 else ""
            lines.append(f"   \U0001f4c5 Since fresh-run: {format_duration(wall)}  \u2014 opened {since}{suffix}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Run durations (project 71, step 3.10)
# ---------------------------------------------------------------------------


class RunDurations:
    """The seconds a run spent, by category: per Playwright spec (with its tests), per Vitest file, per pytest unit.

    Fed by the consolidated passes from the reports they read anyway (``_consolidate.py``, ``_consolidate_backend.py``);
    emptied when an invocation starts (``_timed_run``) and written when it ends (``write_durations``).
    """

    def __init__(self) -> None:
        self.categories: dict[str, dict] = {}

    def reset(self) -> None:
        self.categories = {}

    def empty(self) -> bool:
        return not self.categories

    def add(self, category: str, kind: str, unit: str, seconds: float, tests: dict[str, float] | None = None) -> None:
        """Add ``seconds`` to ``unit`` of ``kind`` (``playwright``, ``vitest``, ``pytest``) in ``category``; a Playwright spec
        also carries its tests' seconds."""
        entry = self.categories.setdefault(category, {"seconds": 0.0})
        bucket = entry.setdefault(kind, {})
        if kind == "playwright":
            spec = bucket.setdefault(unit, {"seconds": 0.0, "tests": {}})
            spec["seconds"] += seconds
            for title, test_seconds in (tests or {}).items():
                spec["tests"][title] = spec["tests"].get(title, 0.0) + test_seconds
        else:
            bucket[unit] = bucket.get(unit, 0.0) + seconds
        entry["seconds"] += seconds


#: The durations of this process's run.
DURATIONS = RunDurations()


def _rounded(value):
    """Milliseconds are the reports' resolution: three decimals of a second, no float noise."""
    if isinstance(value, float):
        return round(value, 3)
    if isinstance(value, dict):
        return {key: _rounded(item) for key, item in value.items()}
    return value


def _coverage_timing() -> dict | None:
    """The summary of the E2E coverage stopwatches (``js-coverage-probe.mjs timing --json``), or ``None`` without them."""
    if not TIMING_DIR.is_dir() or not any(TIMING_DIR.glob("*.jsonl")):
        return None
    try:
        result = subprocess.run(["node", str(_TIMING_PROBE), "timing", str(TIMING_DIR), "--json"], capture_output=True, text=True, timeout=120)
        return json.loads(result.stdout) if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def write_durations(with_coverage_timing: bool = False) -> Path | None:
    """Write ``DURATIONS`` to ``DURATIONS_FILE`` (schema ``lf-durations/1``) and return its path; ``None``, and nothing
    written, when the run recorded no duration. ``with_coverage_timing`` only for a run under JS coverage: such a run wipes
    ``coverage-js/`` when it starts, so its stopwatch lines are its own; any other run would summarise a previous run's."""
    if DURATIONS.empty():
        return None
    timing = _coverage_timing() if with_coverage_timing else None
    data = {"schema": "lf-durations/1", "written_at": datetime.now().isoformat(timespec="seconds"), "categories": _rounded(DURATIONS.categories), "coverage_timing": timing}
    DURATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DURATIONS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return DURATIONS_FILE
