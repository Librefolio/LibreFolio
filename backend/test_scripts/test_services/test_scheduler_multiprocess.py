"""``backend.app.services.platform.scheduler.scheduler`` across processes: two workers run the due jobs at the same moment
(plan phase01SleepWake, item Z-11, night decision N71).

Each uvicorn worker has a scheduler loop and an ``asyncio.Lock`` of its own, so two workers may reach
``run_due_jobs`` together: two ticks, or a wake-up served by one worker while the other ticks. With ``fcntl`` they meet
at one lock file, ``.scheduler.lock`` in the data directory, held from the state's load to the last save; the leader
election is the fallback of a platform without ``fcntl`` only. The contract pinned here:

(a) Two processes, past a common barrier, each call ``run_due_jobs("wake")`` on one data directory with both jobs due:
    each job runs once across the two. The process that takes the lock first runs both jobs and reports them "ok"; the
    other waits for the lock, then loads the state the first saved and reports both "not_due". Neither reports
    "not_leader", and neither asks ``am_i_leader``.
(b) The state file holds each job's ``last_run_at`` as the process that ran it wrote it, once; the other process read
    those very values when it loaded the state, inside the lock; and the lock file the two met at is the data
    directory's ``.scheduler.lock``.

Pure: no database, no server, no lane port, no network. The two processes are real: one script written under
``tmp_path`` and run twice by ``sys.executable``, the project root on ``sys.path``, with ``LIBREFOLIO_DATA_DIR`` a
folder of ``tmp_path``, ``LIBREFOLIO_TEST_MODE`` "0", and neither ``LIBREFOLIO_NO_SCHEDULER``, ``LIBREFOLIO_BLOCKED``
nor the coverage variables: the state file and the lock file are the real ones, both under ``tmp_path``. Each process
imports the scheduler, then patches it in its own memory: the settings enabled, without the database; the two jobs'
due functions "never ran" (``last_run_at`` None) and their bodies fakes that write a line to a record file shared by the
two, last ``JOB_SECONDS``, so that two runs left unserialised would overlap, and set ``last_run_at``; ``load_state``
the real one, its result written to the record too; ``CLOCK_SETTLE_SECONDS`` 0; ``am_i_leader`` a recorder that answers
yes, so that nothing but the lock across processes may keep the two runs apart. Each process says it is ready, waits for
a ``go`` file written once both are, runs, and writes its report as JSON. The processes run once for the module
(``scenario``), and both tests read that one run. Every wait is the polling of a file or of a process against a
generous deadline, the machine may be loaded far past its cores; no assertion depends on a duration. Both processes are
killed and reaped in a ``finally``.

Red until Z-11 exists: both processes ask ``am_i_leader`` and, told yes, run both jobs: a job runs twice, the state is
written twice, no process finds the jobs done, and no ``.scheduler.lock`` is in the data directory.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from backend.test_scripts.test_utils import print_section, print_success

REPO_ROOT = Path(__file__).resolve().parents[3]

#: The literals of the contract, never read from the module under test.
JOBS = ("current_price", "history_sync")
LOCK_FILE_NAME = ".scheduler.lock"
STATE_FILE_NAME = "scheduler_state.json"
RAN_BOTH = [["current_price", "ok"], ["history_sync", "ok"]]
FOUND_BOTH_DONE = [["current_price", "not_due"], ["history_sync", "not_due"]]

WORKERS = ("first", "second")
#: How long each fake job lasts: two runs left unserialised overlap.
JOB_SECONDS = 0.5
#: The longest a worker may take to be ready (its interpreter and the scheduler's imports), then to run and report.
START_SECONDS = 180.0
RUN_SECONDS = 180.0
#: How long a worker may take to exit after its report, and a killed one to be reaped.
REAP_SECONDS = 30.0
#: How often a file or a process is polled.
POLL_STEP = 0.02
#: The variables a worker must not inherit: the test lane's data directory, and the switches that would stop its run.
NOT_INHERITED = ("LIBREFOLIO_TEST_MODE", "LIBREFOLIO_TEST_DATA_DIR", "LIBREFOLIO_DATA_DIR", "LIBREFOLIO_NO_SCHEDULER", "LIBREFOLIO_BLOCKED")

#: One worker: ``<root> <folder> <name> <start seconds> <run seconds> <job seconds>``. Its lines in ``record.log`` all start
#: with its pid: ``am_i_leader``; ``start <job>``; ``end <job> <last_run_at>``; ``load <current_price> <history_sync>``,
#: the ``last_run_at`` it loaded or ``-``. Its files: ``ready-<name>``, then ``report-<name>.json``, or ``error-<name>``.
WORKER = """
import asyncio
import json
import os
import sys
import time
import traceback
from pathlib import Path

root, folder, name = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
start_seconds, run_seconds, job_seconds = (float(value) for value in sys.argv[4:7])
sys.path.insert(0, root)

from backend.app.services.platform.scheduler import scheduler
from backend.app.services.platform.scheduler.settings import SchedulerSettings
from backend.app.services.platform.scheduler.state import JobState

RECORD = folder / "record.log"
SETTINGS = SchedulerSettings(
    scheduler_enabled=True,
    current_price_frequency_minutes=10,
    history_sync_times=[],
    history_sync_days=["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
    history_sync_horizon_days=14,
    scheduler_timezone="UTC",
)


def record(*words):
    line = " ".join([str(os.getpid()), *[str(word) for word in words]]) + "\\n"
    fd = os.open(RECORD, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, line.encode())
    finally:
        os.close(fd)


def say(file_name, text):
    part = folder / (file_name + ".part")
    part.write_text(text)
    os.replace(part, folder / file_name)


async def enabled_settings():
    return SETTINGS


def the_leader():
    record("am_i_leader")
    return True


def never_ran(job):
    def due(now, settings, state):
        return getattr(state, job).last_run_at is None

    return due


async def run_job(job, state):
    record("start", job)
    await asyncio.sleep(job_seconds)
    stamp = scheduler.utc_now().isoformat()
    setattr(state, job, JobState(last_run_at=stamp, last_duration_s=job_seconds, last_status="ok", last_items_ok=1))
    record("end", job, stamp)


async def current_price(state):
    await run_job("current_price", state)


async def history_sync(state, horizon_days=None):
    await run_job("history_sync", state)


real_load_state = scheduler.load_state


def recorded_load_state():
    state = real_load_state()
    record("load", state.current_price.last_run_at or "-", state.history_sync.last_run_at or "-")
    return state


scheduler.CLOCK_SETTLE_SECONDS = 0.0
scheduler.am_i_leader = the_leader
scheduler.load_scheduler_settings = enabled_settings
scheduler.load_state = recorded_load_state
scheduler.due_current_price = never_ran("current_price")
scheduler.due_history_sync = never_ran("history_sync")
scheduler.run_current_price_refresh = current_price
scheduler.run_history_sync = history_sync


async def main():
    say("ready-" + name, str(os.getpid()))
    deadline = time.monotonic() + start_seconds
    while not (folder / "go").exists():
        if time.monotonic() > deadline:
            raise TimeoutError("no go within the start deadline")
        await asyncio.sleep(0.005)
    report = await asyncio.wait_for(scheduler.run_due_jobs("wake"), run_seconds)
    jobs = [[outcome.name, outcome.status] for outcome in report.jobs]
    say("report-" + name + ".json", json.dumps({"pid": os.getpid(), "status": report.status, "jobs": jobs}))


try:
    asyncio.run(main())
except BaseException:
    say("error-" + name, traceback.format_exc())
    raise
"""


def _tail(log: Path, lines: int = 40) -> str:
    try:
        text = log.read_text(errors="replace")
    except FileNotFoundError:
        return "(no output)"
    return "\n".join(text.splitlines()[-lines:]) or "(no output)"


def _worker_environment(data_dir: Path) -> dict[str, str]:
    """This process's environment without the lane's data directory, the switches and the coverage variables; the data
    directory a folder of the test, outside the test mode."""
    environment = {name: value for name, value in os.environ.items() if name not in NOT_INHERITED and not name.startswith("COVERAGE_")}
    environment.update(LIBREFOLIO_TEST_MODE="0", LIBREFOLIO_DATA_DIR=str(data_dir))
    return environment


def _await_each(folder: Path, marker: str, workers: dict[str, subprocess.Popen[bytes]], seconds: float) -> None:
    """Until every worker has written ``marker`` (``{name}`` in it is the worker's); a red at once for a worker that ended
    without it, or after ``seconds``."""
    deadline = time.monotonic() + seconds
    while True:
        missing = [name for name in workers if not (folder / marker.format(name=name)).exists()]
        if not missing:
            return
        for name in missing:
            if workers[name].poll() is not None and not (folder / marker.format(name=name)).exists():
                pytest.fail(f"worker {name} ended ({workers[name].returncode}) before {marker.format(name=name)}: {_tail(folder / f'{name}.log')}")
        if time.monotonic() > deadline:
            pytest.fail(f"{', '.join(missing)}: no {marker} within {seconds:.0f} s: " + " | ".join(_tail(folder / f"{name}.log") for name in missing))
        with contextlib.suppress(subprocess.TimeoutExpired):
            workers[missing[0]].wait(timeout=POLL_STEP)


def _stop(workers: dict[str, subprocess.Popen[bytes]]) -> None:
    for process in workers.values():
        if process.poll() is None:
            process.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=REAP_SECONDS)


@dataclass(frozen=True)
class Scenario:
    """What the two workers left: their reports by name, the record's lines split in words (the pid first), the state file
    as JSON (None if missing), what is at the data directory's lock path, and their output."""

    folder: Path
    data_dir: Path
    reports: dict[str, dict[str, Any]]
    record: list[tuple[str, ...]]
    state: dict[str, Any] | None
    lock_file: str
    logs: str

    def lines(self, word: str) -> list[tuple[str, ...]]:
        """The record's lines of ``word``: the pid, then what follows the word."""
        return [(line[0], *line[2:]) for line in self.record if len(line) > 1 and line[1] == word]

    def pid(self, outcomes: list[list[str]]) -> str | None:
        """The pid of the worker whose report has these outcomes, if one has."""
        return next((str(report["pid"]) for report in self.reports.values() if report["jobs"] == outcomes), None)

    def describe(self) -> str:
        return f"reports {self.reports}; record {self.record}"


def _lock_file(path: Path) -> str:
    if path.is_symlink():
        return "a symbolic link"
    if path.is_file():
        return "a regular file"
    return "nothing" if not path.exists() else "something else"


def _read(folder: Path, data_dir: Path) -> Scenario:
    reports = {name: json.loads((folder / f"report-{name}.json").read_text()) for name in WORKERS}
    record_file = folder / "record.log"
    record = [tuple(line.split()) for line in record_file.read_text().splitlines()] if record_file.exists() else []
    state_file = data_dir / STATE_FILE_NAME
    state = json.loads(state_file.read_text()) if state_file.exists() else None
    logs = " | ".join(f"{name}: {_tail(folder / f'{name}.log', 15)}" for name in WORKERS)
    return Scenario(folder, data_dir, reports, record, state, _lock_file(data_dir / LOCK_FILE_NAME), logs)


@pytest.fixture(scope="module")
def scenario(tmp_path_factory: pytest.TempPathFactory) -> Scenario:
    """The two workers, run once for the module: started, both ready, ``go``, both reported, both exited."""
    folder = tmp_path_factory.mktemp("scheduler-two-workers")
    data_dir = folder / "data"
    data_dir.mkdir()
    script = folder / "worker.py"
    script.write_text(WORKER)
    workers: dict[str, subprocess.Popen[bytes]] = {}
    try:
        for name in WORKERS:
            with (folder / f"{name}.log").open("wb") as log:
                arguments = [str(REPO_ROOT), str(folder), name, str(START_SECONDS), str(RUN_SECONDS), str(JOB_SECONDS)]
                workers[name] = subprocess.Popen([sys.executable, "-u", str(script), *arguments], cwd=folder, env=_worker_environment(data_dir), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        _await_each(folder, "ready-{name}", workers, START_SECONDS)
        (folder / "go").write_text("go")
        _await_each(folder, "report-{name}.json", workers, RUN_SECONDS)
        for name, process in workers.items():
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=REAP_SECONDS)
            assert process.returncode == 0, f"worker {name} ended {process.returncode} after its report: {_tail(folder / f'{name}.log')}"
        return _read(folder, data_dir)
    finally:
        _stop(workers)


def test_two_processes_run_each_due_job_once_and_the_second_finds_both_done(scenario: Scenario) -> None:
    """MP-001 — contract (a): across the two processes each job started once, both in the same process, which reports both
    "ok"; the other reports both "not_due"; both runs are "ok" — no "not_leader" —, and ``am_i_leader`` was never asked:
    with ``fcntl`` the lock across processes decides, not the leader."""
    print_section("MP-001: two workers, each job once")
    assert importlib.util.find_spec("fcntl") is not None, "Precondition: fcntl is there, as on every POSIX system"
    starts = scenario.lines("start")
    ran = Counter(job for _, job in starts)
    outcomes = sorted(report["jobs"] for report in scenario.reports.values())
    statuses = sorted(report["status"] for report in scenario.reports.values())
    asked = scenario.lines("am_i_leader")

    assert ran == Counter(JOBS), f"each due job runs once across the two processes, behind the lock across processes (the data directory's {LOCK_FILE_NAME}, N71); started {dict(ran)} times: {starts}; {scenario.describe()}"
    assert outcomes == sorted([RAN_BOTH, FOUND_BOTH_DONE]), f"the process that took the cross-process lock first runs both jobs, the other finds both not due once it gets the lock: {scenario.describe()}"
    assert len({pid for pid, _ in starts}) == 1 and scenario.pid(RAN_BOTH) == starts[0][0], f"both jobs ran in the process reporting them ok: {scenario.describe()}"
    assert statuses == ["ok", "ok"], f"both runs end ok, neither not_leader: with the cross-process lock there is no leader to wait for: {statuses}"
    assert asked == [], f"with fcntl available am_i_leader is never asked: the cross-process lock decides (Z-11, N71); asked by {asked}"
    print_success(f"each job once, in {starts[0][0]}; the other found both done; no leader asked")


def test_the_state_holds_each_job_written_once_and_the_second_process_read_it_inside_the_lock(scenario: Scenario) -> None:
    """MP-002 — contract (b): each job's ``last_run_at`` was written once, by the process that ran both jobs, and the state
    file holds those values; the first load, there, saw no job run, and the other process's one load saw both values —
    it read the state inside the lock, after the first process's last save; the data directory's ``.scheduler.lock`` is
    a regular file."""
    print_section("MP-002: the state written once, read inside the lock")
    ends = scenario.lines("end")
    written = Counter(job for _, job, _ in ends)

    assert written == Counter(JOBS) and len({pid for pid, _, _ in ends}) == 1, f"each job's last_run_at is written once, both by the process holding the cross-process lock (N71); written {dict(written)} times: {ends}; {scenario.describe()}"
    writer = ends[0][0]
    stamps = {job: stamp for _, job, stamp in ends}
    assert scenario.state is not None, f"the state file is in the data directory {scenario.data_dir}: {scenario.logs}"
    assert {job: scenario.state.get(job, {}).get("last_run_at") for job in JOBS} == stamps, f"the state file holds what the run wrote: {scenario.state}"
    loads = {pid: [(current, history) for loader, current, history in scenario.lines("load") if loader == pid] for pid in {loader for loader, _, _ in scenario.lines("load")}}
    others = [pid for pid in loads if pid != writer]
    assert loads.get(writer) == [("-", "-")], f"the process that ran the jobs loaded a state where none had run: {loads}"
    assert len(others) == 1 and loads[others[0]] == [(stamps["current_price"], stamps["history_sync"])], f"the other process loaded the state once, inside the cross-process lock, after the first one's last save: loads {loads}, written {stamps}"
    assert scenario.lock_file == "a regular file", f"the two processes met at {scenario.data_dir / LOCK_FILE_NAME}, the data directory's lock file (run_lock_path()): there is {scenario.lock_file}"
    print_success("written once; the second load saw it; the lock file in the data directory")
