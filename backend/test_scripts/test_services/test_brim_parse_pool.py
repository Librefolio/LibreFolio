"""
The parse off-loading path (P3 / import performance).

``parse_file`` used to run inline in an ``async def`` endpoint: it blocked the event loop
for the whole parse, and firing several parses in parallel from the browser changed
nothing because the server could only ever run one. It now runs in a process pool.

Crossing a process boundary is the part that can fail silently, so these tests pin exactly
that: the result must survive pickling **with its contents intact**, and every failure mode
must degrade to a thread instead of losing the import. What must *not* happen is a parser
error being mistaken for a broken pool — an "unsupported layout" message is the only useful
thing the user gets when a file will not parse, and swallowing it into a silent retry would
leave them staring at a spinner.

W-B53 (J-30): the first parse after the server starts paid for starting the pool — a forkserver
started from nothing, then a worker importing ``brim_provider`` as it unpickled ``parse_file``
and discovering every plugin at the parse: about 4 s at load 31, 31–49 s under heavy load, then
1 ms. The cure, pinned here:

1. the forkserver the pool forks its workers from preloads ``brim_parse_preload``, which imports
   ``brim_provider`` and runs the registry's discovery: a worker starts with the BRIM module, a
   plugin module and the discovery done. Observed by ``_brim_pool_probe.worker_report``, run in
   the pool of a fresh interpreter: the forkserver is one per process, and this one may have
   started it without the preload in an earlier test;
2. ``prewarm()`` starts that forkserver before any parse — the first worker of the pool built
   afterwards is forked by a process ``prewarm()`` started, and is born as in (1) — and leaves
   the pool itself lazy (``_pool`` still ``None``). The forkserver stays single-threaded once
   preloaded: a thread started by anything the preload imports would make every worker a fork
   of a multi-threaded process, which the pool's own docstring rules out;
3. ``prewarm()`` never raises: a forkserver that cannot start is logged, and the pool stays
   lazy and usable as before (``_pool_disabled`` False); with the pool disabled, or ``spawn``
   alone, it starts nothing; a parse after it still goes through the pool, contents intact;
4. importing ``brim_parse_preload`` never raises, even when the discovery does — the forkserver
   must never die of it — and leaves ``brim_provider`` imported and the discovery to the
   worker's first parse, which reports the failure as before;
5. importing ``brim_parse_pool`` stays light: it names the preload for the forkserver, never
   imports it, so the import runs no discovery and starts no process.

Red before the cure: (1) because the worker starts with none of it; (2) and (3) because
``prewarm`` does not exist, (4) because ``brim_parse_preload`` does not — reached when the test
runs, never at collection. (5) is green before the cure and must stay so. A fresh interpreter
runs in a session of its own, killed with its process group (forkserver and workers) if it
outlives its deadline. No assertion depends on a duration.

W-B59 (R13-SEC2, E's review of 17/10, note 12): ``_get_pool()`` sets the forkserver preload whatever the prewarm
(``LIBREFOLIO_BRIM_PREWARM``, ``config/brim.py``, off by default: decision N56) says. On Python 3.13 the first
``run_in_executor`` waits, on the event-loop thread, for the new worker's pid, which a preloading forkserver sends only
once BRIM and its 33 plugins are imported: the loop stalls ~4 s idle, 30–50 s under load (E measured, with a module that
sleeps 3 s at import: a stall of 3.14 s with the preload, 0.18 s without). The contract:

6. ``_get_pool()`` sets the preload only when ``brim_prewarm_enabled()`` is true, a ``BrimConfigError`` counting as off:
   with ``LIBREFOLIO_BRIM_PREWARM=0`` or ``=bogus`` the pool's first worker is born WITHOUT the BRIM module, the plugin
   module and the discovery (red today: it is born with them), the pool built and not disabled;
7. with ``LIBREFOLIO_BRIM_PREWARM=1``, (1) and (2) hold as before: the two W-B53 tests now set it explicitly, so the
   environment of the run (``LIBREFOLIO_TEST_MODE``, which a blank value follows) never decides for them — guards,
   green today and after.

The event-loop stall itself is not measured here: under the load of a shared test machine (100 and more) no margin
tells a preload from a busy scheduler, and the worker's birth is the cause the stall follows from.
"""

from __future__ import annotations

import asyncio
import contextlib
import errno
import json
import multiprocessing
import multiprocessing.forkserver
import os
import pickle
import signal
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from structlog.testing import capture_logs

from backend.app.schemas.brim import BRIMParseOutput
from backend.app.services.brim import brim_parse_pool, brim_provider
from backend.app.services.brim.brim_provider import BRIMParseError, delete_file, get_file_path, save_uploaded_file
from backend.app.services.plugin_settings import runtime as settings_runtime
from backend.test_scripts.test_services._brim_pool_probe import BRIM_MODULE, PLUGIN_MODULE, PRELOAD_MODULE

SAMPLE = Path(__file__).resolve().parents[2] / "app" / "services" / "brim_providers" / "sample_reports" / "schwab-export.csv"
REPO_ROOT = Path(__file__).resolve().parents[3]

#: Printed before the JSON of what a fresh interpreter saw: the only line of its output the test reads.
PROBE_MARK = "WB53-PROBE "
#: Deadlines that turn a hang into a red, never a measure. The first worker of a pool waits for its forkserver to start and
#: to import its preload: about 4 s at load 31 and 31–49 s under heavy load, for the first parse W-B53 measured.
RESULT_SECONDS = 180.0
PROCESS_SECONDS = 240.0
REAP_SECONDS = 10.0
LOG_CANARY = "brim-parse-pool test: canary through the pool's logger"

FORKSERVER_ONLY = pytest.mark.skipif(
    "forkserver" not in multiprocessing.get_all_start_methods(),
    reason="only spawn here: the pool spawns every worker from a fresh interpreter, so there is no forkserver to preload or to start early, and prewarm() does nothing",
)

#: What a worker must hold as it starts, by the keys of ``_brim_pool_probe.loaded_report``.
BORN_WITH = {
    "brim_module_loaded": f"the BRIM module ({BRIM_MODULE})",
    "plugin_module_loaded": f"a plugin module ({PLUGIN_MODULE})",
    "registry_discovery_done": "the registry's discovery done",
}

#: Run as ``python -c`` with ``PROBE_MARK``, the scenario (``import``, ``pool`` or ``prewarm``) and ``RESULT_SECONDS``.
#: Under ``-c`` the main module has neither file nor spec, so the workers import nothing of it: what a worker holds as it
#: starts comes from the forkserver it was forked from, plus the probe module it unpickles. The forkserver is a new
#: interpreter, never a fork of this one: what this interpreter imports or discovers never reaches a worker. The barriers:
#: the probe alone finds nothing; at the end, once this interpreter has run the discovery itself, it finds it all. The
#: children of this interpreter, read with psutil, are the processes it started; the threads of the worker's parent, read
#: once the worker answered, are those of its forkserver with the preload done.
FRESH_POOL_SCRIPT = """
import json
import sys

import psutil

from backend.test_scripts.test_services import _brim_pool_probe as probe

mark, scenario, result_seconds = sys.argv[1], sys.argv[2], float(sys.argv[3])
me = psutil.Process()
children = {child.pid for child in me.children()}
seen = {"interpreter_pid": me.pid, "probe_alone": probe.loaded_report()}

from backend.app.services.brim import brim_parse_pool

seen["after_pool_import"] = probe.loaded_report()
seen["started_by_import"] = sorted({child.pid for child in me.children()} - children)
seen["pool_after_import"] = repr(brim_parse_pool._pool)
try:
    if scenario == "prewarm":
        children = {child.pid for child in me.children()}
        seen["prewarm_returned"] = repr(brim_parse_pool.prewarm())
        seen["pool_after_prewarm"] = repr(brim_parse_pool._pool)
        seen["disabled_after_prewarm"] = brim_parse_pool._pool_disabled
        seen["started_by_prewarm"] = sorted({child.pid for child in me.children()} - children)
    if scenario != "import":
        pool = brim_parse_pool._get_pool()
        seen["pool"] = type(pool).__name__
        if pool is not None:
            seen["worker"] = pool.submit(probe.worker_report).result(timeout=result_seconds)
            seen["interpreter_children"] = sorted(child.pid for child in me.children())
            try:
                seen["forkserver_threads"] = psutil.Process(seen["worker"]["ppid"]).num_threads()
            except psutil.Error as exc:
                seen["forkserver_threads"] = repr(exc)
finally:
    brim_parse_pool.shutdown_pool(wait=True)

from backend.app.services.brim.registry import BRIMProviderRegistry

BRIMProviderRegistry.auto_discover()
seen["after_discovery_here"] = probe.loaded_report()
print(mark + json.dumps(seen), flush=True)
"""

#: Run as ``python -c`` with ``PROBE_MARK``: the registry's discovery made to fail — ``_discover_modules`` raises, counting
#: its calls — before ``brim_parse_preload`` is imported, as the forkserver imports it; then the discovery asked for once
#: more, as the worker's first parse asks for it. The registry is imported first: it does not import the BRIM module.
PRELOAD_FAILURE_SCRIPT = """
import json
import sys

from backend.test_scripts.test_services import _brim_pool_probe as probe
from backend.app.services.brim.registry import BRIMProviderRegistry

mark = sys.argv[1]
seen = {"before_import": probe.loaded_report()}
attempts = []


def failing_discovery(cls):
    attempts.append(cls.__name__)
    raise RuntimeError("provoked: the discovery failed")


BRIMProviderRegistry._discover_modules = classmethod(failing_discovery)
try:
    import backend.app.services.brim.brim_parse_preload
except Exception as exc:
    seen["import_raised"] = repr(exc)
else:
    seen["import_raised"] = None
seen["attempts_at_import"] = len(attempts)
seen["after_import"] = probe.loaded_report()
try:
    BRIMProviderRegistry.auto_discover()
except Exception as exc:
    seen["next_discovery_raised"] = repr(exc)
else:
    seen["next_discovery_raised"] = None
seen["attempts_after_next"] = len(attempts)
print(mark + json.dumps(seen), flush=True)
"""


@pytest.fixture
def uploaded_sample():
    """A real upload of a sample report, through the real code path, cleaned up after."""
    info = save_uploaded_file(SAMPLE.read_bytes(), SAMPLE.name)
    yield info.file_id
    delete_file(info.file_id)


@pytest.fixture
def reset_pool():
    """Each test starts from a pristine pool and leaves no workers behind."""
    brim_parse_pool.shutdown_pool()
    brim_parse_pool._pool_disabled = False
    yield
    brim_parse_pool.shutdown_pool()
    brim_parse_pool._pool_disabled = False


def test_upload_area_resolves(uploaded_sample):
    """Guard the fixture itself: a wrong path would make every test below vacuous."""
    assert get_file_path(uploaded_sample) is not None


@pytest.mark.asyncio
async def test_offloaded_parse_matches_inline_parse(uploaded_sample, reset_pool):
    """A parse through the pool returns what the inline one returns — contents included."""
    inline = brim_provider.parse_file(uploaded_sample, "broker_schwab", 1)
    offloaded = await brim_parse_pool.parse_file_offloaded(uploaded_sample, "broker_schwab", 1)

    assert isinstance(offloaded, BRIMParseOutput)
    assert offloaded.model_dump(mode="json") == inline.model_dump(mode="json")
    assert len(offloaded.transactions) > 0


def test_parse_output_survives_pickling(uploaded_sample):
    """The return trip is a pickle: a field that does not round-trip is data silently lost."""
    output = brim_provider.parse_file(uploaded_sample, "broker_schwab", 1)
    restored = pickle.loads(pickle.dumps(output))
    assert restored.model_dump(mode="json") == output.model_dump(mode="json")


def test_parse_error_survives_pickling():
    """A parser error must arrive readable on the other side, ``details`` included."""
    original = BRIMParseError("unsupported layout", {"row": 12})
    restored = pickle.loads(pickle.dumps(original))
    assert str(restored) == "unsupported layout"
    assert restored.details == {"row": 12}


@pytest.mark.asyncio
async def test_parser_errors_are_not_mistaken_for_a_broken_pool(uploaded_sample, reset_pool):
    """A plugin that cannot read the file raises through — and the pool stays alive."""
    with pytest.raises(ValueError):
        await brim_parse_pool.parse_file_offloaded(uploaded_sample, "broker_nonexistent_plugin", 1)
    assert brim_parse_pool._pool_disabled is False


@pytest.mark.asyncio
async def test_missing_file_still_raises_filenotfound(reset_pool):
    """FileNotFoundError is an OSError: it must not be read as pool trouble."""
    with pytest.raises(FileNotFoundError):
        await brim_parse_pool.parse_file_offloaded(str(uuid.uuid4()), "broker_schwab", 1)
    assert brim_parse_pool._pool_disabled is False


@pytest.mark.asyncio
async def test_falls_back_to_a_thread_when_the_pool_cannot_start(uploaded_sample, reset_pool, monkeypatch):
    """No workers available is a slow import, never a failed one."""
    monkeypatch.setattr(brim_parse_pool, "_pool_disabled", True)
    output = await brim_parse_pool.parse_file_offloaded(uploaded_sample, "broker_schwab", 1)
    assert len(output.transactions) > 0


@pytest.mark.asyncio
@pytest.mark.parametrize("pool", [pytest.param(True, id="process-pool"), pytest.param(False, id="thread-fallback")])
async def test_naming_the_user_changes_nothing_for_a_plugin_without_settings(pool: bool, uploaded_sample, reset_pool, monkeypatch):
    """W-BS: ``parse_file_offloaded(..., user_id=…)`` is the settings hook; a plugin that declares no field (schwab, like
    every real one) is parsed exactly as before — the same output, through the pool and through the thread — and the
    database of the settings is never reached (the engine of the settings runtime raises when it is)."""

    def no_database():
        raise AssertionError("the settings database was reached: schwab declares no field")

    monkeypatch.setattr(settings_runtime, "get_async_engine", no_database)
    monkeypatch.setattr(brim_parse_pool, "_pool_disabled", not pool)
    inline = brim_provider.parse_file(uploaded_sample, "broker_schwab", 1)

    offloaded = await brim_parse_pool.parse_file_offloaded(uploaded_sample, "broker_schwab", 1, user_id=1)

    assert offloaded.model_dump(mode="json") == inline.model_dump(mode="json") and len(offloaded.transactions) > 0
    assert (brim_parse_pool._pool is not None) is pool, "the pool carried the parse, or the thread did, as asked"


def test_worker_count_is_bounded():
    """Never more workers than cores, never more than the cap, never zero."""
    assert 1 <= brim_parse_pool._worker_count() <= brim_parse_pool.MAX_WORKERS


# ---------------------------------------------------------------------------
# W-B53: workers forked from a preloaded forkserver, started before any parse
# ---------------------------------------------------------------------------


def _tail(text: str, lines: int = 80) -> str:
    return "\n".join(text.splitlines()[-lines:])


def _fresh_interpreter_env(overrides: dict[str, str] | None = None) -> dict[str, str]:
    """This process's environment, with the project root first on ``PYTHONPATH``, as the server has it, and ``overrides``
    on top (W-B59: ``LIBREFOLIO_BRIM_PREWARM`` set by the test, never inherited by chance).

    The root matters beyond the script's own imports: ``multiprocessing.forkserver.main`` swallows the ``ImportError`` of a
    preload module in silence, so a forkserver whose ``sys.path`` missed it would start "preloaded" with nothing — the first
    W-B53 measure fell into that. The rest is kept: the lane's data directory and, in a measured run, the coverage start-up
    every child of the runner gets (``COVERAGE_PROCESS_START``, and its directory on ``PYTHONPATH``).
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT), *(part for part in os.environ.get("PYTHONPATH", "").split(os.pathsep) if part)])
    env.update(overrides or {})
    return env


def _in_a_fresh_interpreter(tmp_path: Path, label: str, script: str, *args: str, env: dict[str, str] | None = None) -> dict[str, Any]:
    """What ``script`` saw in a new interpreter, started in a session of its own with ``args`` and the variables ``env`` on
    top of this process's: the JSON after ``PROBE_MARK``.

    Its output goes to a file in ``tmp_path`` — never to a pipe its forkserver could keep open — and is shown when it fails.
    Past ``PROCESS_SECONDS`` it is killed with its whole process group, forkserver and workers included, and reaped.
    """
    log_path = tmp_path / f"fresh-interpreter-{label}.log"
    command = [sys.executable, "-c", script, *args]
    with log_path.open("wb") as log:
        process = subprocess.Popen(command, cwd=REPO_ROOT, env=_fresh_interpreter_env(env), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=PROCESS_SECONDS)
        hung = process.poll() is None
    finally:
        if process.poll() is None:
            # Not reaped yet, so its pid — the id of the group its session started — names nobody else.
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(process.pid, signal.SIGKILL)
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=REAP_SECONDS)
    output = log_path.read_text(encoding="utf-8", errors="replace")
    assert not hung, f"the fresh interpreter ({label}) still ran {PROCESS_SECONDS} s later: killed with its process group:\n{_tail(output)}"
    lines = [line for line in output.splitlines() if line.startswith(PROBE_MARK)]
    assert process.returncode == 0 and len(lines) == 1, f"the fresh interpreter ({label}) ended with status {process.returncode}:\n{_tail(output)}"
    return json.loads(lines[0][len(PROBE_MARK) :])


def _in_a_fresh_pool_interpreter(tmp_path: Path, scenario: str, *, env: dict[str, str] | None = None) -> dict[str, Any]:
    """``FRESH_POOL_SCRIPT`` run for ``scenario``, with the variables ``env`` set, and the barriers on its probe passed: it
    finds nothing alone, and it finds all a worker must be born with once the interpreter itself has run the discovery.
    Without them, what the probe answers proves nothing either way."""
    seen = _in_a_fresh_interpreter(tmp_path, scenario, FRESH_POOL_SCRIPT, PROBE_MARK, scenario, str(RESULT_SECONDS), env=env)
    assert not any(seen["probe_alone"].values()), f"barrier: _brim_pool_probe alone finds the BRIM modules or the discovery in a fresh interpreter, so a worker answering True would prove nothing: {seen}"
    assert not _lacking(seen["after_discovery_here"]), f"barrier: once the interpreter has run the discovery itself, the probe still misses {_lacking(seen['after_discovery_here'])}: it looks for the wrong names, or the discovery fails here, and then it fails in a forkserver too: {seen}"
    return seen


def _lacking(report: dict[str, Any]) -> list[str]:
    """What a ``_brim_pool_probe.loaded_report`` misses of ``BORN_WITH``."""
    return [what for key, what in BORN_WITH.items() if report.get(key) is not True]


def _worker_of_a_forkserver(seen: dict[str, Any]) -> dict[str, Any]:
    """The worker's report, once it is shown to come from a worker forked by a forkserver this interpreter started."""
    assert seen["pool"] == "ProcessPoolExecutor", f"barrier: _get_pool() gave no process pool in a fresh interpreter: {seen}"
    worker = seen["worker"]
    assert worker["ppid"] != seen["interpreter_pid"] and worker["ppid"] in seen["interpreter_children"], f"barrier: the worker was not forked by a forkserver this interpreter started — the pool no longer forks from one here: {seen}"
    return worker


@contextlib.contextmanager
def _pool_log() -> Iterator[list[dict[str, Any]]]:
    """What ``brim_parse_pool`` logs inside the block, behind a barrier: a canary through its own logger must arrive first."""
    with capture_logs() as events:
        brim_parse_pool.logger.warning(LOG_CANARY)
        assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: brim_parse_pool's logger does not reach capture_logs, so what this test reads of the log proves nothing: {events}"
        yield events


def _spawn_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """This platform as one with ``spawn`` alone, whichever way it is asked: the start methods listed, or the context."""
    real_get_context = multiprocessing.get_context

    def get_context(method: str | None = None) -> Any:
        if method == "forkserver":
            raise ValueError("cannot find context for 'forkserver'")
        return real_get_context(method)

    monkeypatch.setattr(multiprocessing, "get_all_start_methods", lambda: ["spawn"])
    monkeypatch.setattr(multiprocessing, "get_context", get_context)


#: The variable of the BRIM prewarm (``config/brim.py``), set explicitly in every fresh interpreter that builds the pool.
PREWARM_VARIABLE = "LIBREFOLIO_BRIM_PREWARM"
PREWARM_ON = {PREWARM_VARIABLE: "1"}


@FORKSERVER_ONLY
def test_with_the_prewarm_on_a_worker_of_the_pool_starts_with_the_brim_module_and_its_plugins_already_loaded(tmp_path):
    """W-B53, now a guard: green today and after. With the prewarm on (``LIBREFOLIO_BRIM_PREWARM=1``, set here, never
    inherited), the forkserver ``_get_pool()`` forks its workers from has preloaded the BRIM module, its plugins and the
    registry's discovery (``brim_parse_preload``).

    In a fresh interpreter, where no forkserver has started yet, ``_get_pool()`` builds the pool and its first worker runs
    ``_brim_pool_probe.worker_report``. Before W-B53 it found none of it: the forkserver started with the default preload,
    and each worker imported the BRIM module when its first parse unpickled ``parse_file``, then discovered every plugin in
    that parse. W-B59 keeps this with the prewarm on, and drops the preload with it off (the tests below).
    """
    seen = _in_a_fresh_pool_interpreter(tmp_path, "pool", env=PREWARM_ON)

    worker = _worker_of_a_forkserver(seen)
    lacking = _lacking(worker)
    assert not lacking, f"W-B53: with the prewarm on, worker {worker['pid']} started without {'; '.join(lacking)}: its forkserver (pid {worker['ppid']}) did not preload them ({PRELOAD_MODULE} loaded there: {worker['preload_module_loaded']}): {seen}"


@FORKSERVER_ONLY
@pytest.mark.parametrize(
    ("value", "reading"),
    [
        pytest.param("0", "off", id="prewarm-0"),
        pytest.param("bogus", "neither on nor off, so BrimConfigError, which counts as off", id="prewarm-bogus"),
    ],
)
def test_with_the_prewarm_off_the_first_worker_is_born_without_the_brim_module_its_plugins_or_the_discovery(tmp_path, value, reading):
    """W-B59 (R13-SEC2). Red today: ``_get_pool()`` sets the forkserver preload whatever ``LIBREFOLIO_BRIM_PREWARM``
    says, so the first worker is born with the BRIM module, a plugin module and the discovery. On Python 3.13 the first
    ``run_in_executor`` waits on the event-loop thread for that worker's pid, which a preloading forkserver sends only
    once BRIM and its 33 plugins are imported: the server stalls ~4 s idle, 30–50 s under load — with the prewarm off,
    against decision N56.

    Contract: ``_get_pool()`` sets the preload only when ``brim_prewarm_enabled()`` is true; a ``BrimConfigError`` counts
    as off. In a fresh interpreter with ``LIBREFOLIO_BRIM_PREWARM`` at ``0`` (off) or at ``bogus`` (neither on nor off:
    ``BrimConfigError``), the pool is built — not disabled, nothing raised (the barrier of ``_worker_of_a_forkserver``)
    — and its first worker, forked by a lazy forkserver without preload, lacks all three of ``BORN_WITH``: it imports
    them at its first parse, outside the event loop, as before W-B53. The ``bogus`` case guards the error path: green
    after the cure only if the configuration error is read as off, never raised out of ``_get_pool()`` (which would
    disable the pool and fail the barrier).
    """
    seen = _in_a_fresh_pool_interpreter(tmp_path, f"pool-prewarm-{value}", env={PREWARM_VARIABLE: value})

    worker = _worker_of_a_forkserver(seen)
    loaded = [what for key, what in BORN_WITH.items() if worker.get(key) is True]
    assert not loaded, f"W-B59: with LIBREFOLIO_BRIM_PREWARM={value} ({reading}), worker {worker['pid']} was born with {'; '.join(loaded)}: its forkserver (pid {worker['ppid']}) preloaded them, and the loop waited for it: {seen}"


@FORKSERVER_ONLY
def test_prewarm_starts_the_preloaded_forkserver_before_any_parse_and_leaves_the_pool_lazy(tmp_path):
    """W-B53, now a guard: green today and after. With the prewarm on (``LIBREFOLIO_BRIM_PREWARM=1``, set here, never
    inherited), ``prewarm()`` starts the forkserver now, preloaded.

    In a fresh interpreter: ``prewarm()`` returns None, the pool still unbuilt and not disabled, and the processes it started
    are new children of the interpreter. The pool built afterwards forks its first worker from one of them — the forkserver
    ``prewarm()`` started, not one started at the first parse — and the worker is born with the BRIM module, a plugin module
    and the discovery done: the preload was set before the forkserver started, and its import succeeded (``multiprocessing``
    swallows a failed one in silence). With that barrier passed, the forkserver — preload done — runs one thread: the
    single-thread guard, green as long as nothing the preload imports starts a thread at import.
    """
    assert callable(brim_parse_pool.prewarm), "brim_parse_pool.prewarm must be a function"

    seen = _in_a_fresh_pool_interpreter(tmp_path, "prewarm", env=PREWARM_ON)

    assert seen["prewarm_returned"] == "None", f"prewarm() returned {seen['prewarm_returned']}, not None: {seen}"
    assert seen["pool_after_prewarm"] == "None", f"prewarm() built the pool: the pool stays lazy, built by the first parse: {seen}"
    assert seen["disabled_after_prewarm"] is False, f"prewarm() disabled the pool: {seen}"
    assert seen["started_by_prewarm"], f"prewarm() started no process: the forkserver will start at the first parse, which pays for it: {seen}"
    worker = _worker_of_a_forkserver(seen)
    assert worker["ppid"] in seen["started_by_prewarm"], f"the first worker of the pool was forked by pid {worker['ppid']}, not by the forkserver prewarm() started ({seen['started_by_prewarm']}): {seen}"
    lacking = _lacking(worker)
    assert not lacking, f"the forkserver prewarm() started gave its worker no {'; '.join(lacking)}: the preload was set after ensure_running(), its import failed in silence, or it ran no discovery ({PRELOAD_MODULE} loaded in the worker: {worker['preload_module_loaded']}): {seen}"
    threads = seen["forkserver_threads"]
    assert isinstance(threads, int), f"barrier: the threads of the forkserver (pid {worker['ppid']}) could not be read: {threads}"
    assert threads == 1, f"the forkserver (pid {worker['ppid']}) runs {threads} threads once preloaded: an import of {PRELOAD_MODULE} starts one. Fork from a single-threaded forkserver: forking a process that runs threads 'is how you get deadlocks' (brim_parse_pool's docstring): {seen}"


def test_importing_the_preload_never_raises_when_the_discovery_fails_and_leaves_the_failure_to_the_first_parse(tmp_path):
    """W-B53 guard, red before the cure only because ``brim_parse_preload`` does not exist (``ModuleNotFoundError``).

    The forkserver imports the preload module, and an exception other than ``ImportError`` there kills it — and with it every
    worker the pool would fork. In a fresh interpreter whose registry discovery raises, importing the module must not raise;
    it leaves ``brim_provider`` imported, and the discovery not done: the worker's first parse asks for it again and gets the
    failure, as before the cure, instead of a catalogue without plugins.
    """
    seen = _in_a_fresh_interpreter(tmp_path, "preload-failure", PRELOAD_FAILURE_SCRIPT, PROBE_MARK)

    assert seen["before_import"]["brim_module_loaded"] is False and seen["before_import"]["registry_discovery_done"] is False, f"barrier: the BRIM module or the discovery is already there before {PRELOAD_MODULE} is imported, so what it leaves proves nothing: {seen}"
    assert seen["import_raised"] is None, f"importing {PRELOAD_MODULE} raised {seen['import_raised']}: in the forkserver, anything but an ImportError kills it, and the pool's workers with it: {seen}"
    assert seen["attempts_at_import"] >= 1, f"barrier: importing {PRELOAD_MODULE} never ran the registry's discovery, so its failure was never provoked — and the forkserver would preload no plugin: {seen}"
    assert seen["after_import"]["brim_module_loaded"] is True, f"importing {PRELOAD_MODULE} left {BRIM_MODULE} out when the discovery failed: the workers would import it at their first parse again: {seen}"
    assert seen["after_import"]["registry_discovery_done"] is False, f"importing {PRELOAD_MODULE} marked the failed discovery done: the worker's first parse would find a catalogue without plugins instead of reporting the failure: {seen}"
    assert seen["attempts_after_next"] == seen["attempts_at_import"] + 1 and "provoked" in (seen["next_discovery_raised"] or ""), f"after the failed preload, the next discovery — the worker's first parse — must run it again and raise its failure, as before the cure: {seen}"


def test_importing_the_pool_stays_light_no_discovery_no_preload_no_process(tmp_path):
    """W-B53 guard, green before the cure and after it: the pool names the preload module for the forkserver, never imports it.

    In a fresh interpreter, importing ``brim_parse_pool`` imports the BRIM module (it submits ``parse_file``) but no plugin
    module, runs no discovery, imports no preload module, builds no pool and starts no process — an import never forks.
    """
    seen = _in_a_fresh_pool_interpreter(tmp_path, "import")

    after = seen["after_pool_import"]
    assert after["preload_module_loaded"] is False, f"importing brim_parse_pool imported {PRELOAD_MODULE}: the pool names it for the forkserver, and importing the pool must stay light: {seen}"
    assert after["plugin_module_loaded"] is False and after["registry_discovery_done"] is False, f"importing brim_parse_pool ran the BRIM plugin discovery: every process that imports the app pays for it: {seen}"
    assert seen["started_by_import"] == [], f"importing brim_parse_pool started processes {seen['started_by_import']}: an import never forks — the forkserver starts at the first parse, or at prewarm(): {seen}"
    assert seen["pool_after_import"] == "None", f"importing brim_parse_pool built the pool: it is built lazily, by the first parse: {seen}"


@FORKSERVER_ONLY
@pytest.mark.parametrize("failure", [OSError(errno.EAGAIN, "provoked: no process can be started"), RuntimeError("provoked: the forkserver failed")], ids=["oserror", "runtimeerror"])
def test_prewarm_never_raises_when_the_forkserver_cannot_start_and_the_pool_stays_lazy_and_usable(failure, reset_pool, monkeypatch):
    """W-B53 guard, red before the cure only because ``prewarm`` does not exist.

    ``multiprocessing.forkserver.ensure_running`` raises: ``prewarm()`` returns None, logs the failure at warning or above,
    and leaves the pool as it was, lazy and usable — neither built nor disabled: the first parse builds it and pays the
    start, as before the cure. The preload goes to a recorder, so this process's forkserver configuration stays as it was.
    """
    prewarm = brim_parse_pool.prewarm
    attempts: list[str] = []

    def failing_ensure_running() -> None:
        attempts.append("ensure_running")
        raise failure

    monkeypatch.setattr(multiprocessing.forkserver, "ensure_running", failing_ensure_running)
    monkeypatch.setattr(multiprocessing.forkserver, "set_forkserver_preload", lambda modules: attempts.append("set_forkserver_preload"))

    with _pool_log() as events:
        returned = prewarm()

    assert "ensure_running" in attempts, f"barrier: prewarm() never reached multiprocessing.forkserver.ensure_running as the module holds it when it runs, so its failure was never provoked: {attempts}"
    assert returned is None
    assert brim_parse_pool._pool is None, "prewarm() built the pool"
    assert brim_parse_pool._pool_disabled is False, "a forkserver that could not start in prewarm() disabled the pool: the first parse must still try it, lazily, as before the cure"
    reported = [event for event in events if event.get("event") != LOG_CANARY and event.get("log_level") in ("warning", "error", "critical")]
    assert reported, f"prewarm() swallowed {failure!r} without logging it at warning or above: {events}"


@pytest.mark.parametrize("why", ["pool-disabled", "spawn-only"])
def test_prewarm_starts_nothing_when_the_pool_would_not_fork_from_a_forkserver(why, reset_pool, monkeypatch):
    """W-B53 guard, red before the cure only because ``prewarm`` does not exist.

    The pool disabled for the process lifetime, or ``spawn`` alone on the platform (whichever way it is asked): ``prewarm()``
    returns None, sets no preload and starts no forkserver — one the pool would never fork from.
    """
    prewarm = brim_parse_pool.prewarm
    attempts: list[str] = []
    monkeypatch.setattr(multiprocessing.forkserver, "ensure_running", lambda: attempts.append("ensure_running"))
    monkeypatch.setattr(multiprocessing.forkserver, "set_forkserver_preload", lambda modules: attempts.append("set_forkserver_preload"))
    if why == "pool-disabled":
        monkeypatch.setattr(brim_parse_pool, "_pool_disabled", True)
    else:
        _spawn_only(monkeypatch)

    assert prewarm() is None
    assert attempts == [], f"prewarm() acted although the pool would not fork from a forkserver ({why}): {attempts}"
    assert brim_parse_pool._pool is None, "prewarm() built the pool"


@pytest.mark.asyncio
async def test_a_parse_after_prewarm_goes_through_the_pool_and_matches_the_inline_parse(uploaded_sample, reset_pool):
    """W-B53 guard, red before the cure only because ``prewarm`` does not exist.

    ``prewarm()``, run as the startup step runs it (``asyncio.to_thread``), then a parse: it goes through the pool — built,
    not disabled — and returns what the inline parse returns, contents included. This process's forkserver may already run,
    started by an earlier test with or without the preload: the parse must work either way.
    """
    prewarm = brim_parse_pool.prewarm
    assert await asyncio.to_thread(prewarm) is None

    inline = brim_provider.parse_file(uploaded_sample, "broker_schwab", 1)
    offloaded = await brim_parse_pool.parse_file_offloaded(uploaded_sample, "broker_schwab", 1)

    assert isinstance(offloaded, BRIMParseOutput)
    assert offloaded.model_dump(mode="json") == inline.model_dump(mode="json")
    assert len(offloaded.transactions) > 0
    assert brim_parse_pool._pool is not None and brim_parse_pool._pool_disabled is False, "the parse fell back to a thread: the pool did not serve it"
