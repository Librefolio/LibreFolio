"""
H-61 checkpoint 2 · the registry of used ticket ids (``jti``) of the hosting panel's signed tickets (LibreFolio 1.3,
workstream H, platform). The contract is H-61 CP2's: §2 «The registry», and §6 for this file.

Under test: ``backend/app/services/platform/hosting_panel/ticket_registry.py`` (new) and, in HPR-008 only, the access in
front of it (``panel_access``, ``hosting_panel/access.py``, §3). ``record(jti, expires_at, now) -> bool`` answers ``True``
for a ``jti`` it has never recorded, and records it, and ``False`` for one already there: the access then refuses with
``panel_ticket_replayed``. The registry is a small SQLite file, ``<data dir>/panel_tickets.sqlite3``, with a table
``(jti TEXT PRIMARY KEY, expires_at INTEGER)``:

- the check and the record are one transaction: of several threads, or worker processes sharing the file, exactly one
  gets ``True`` for a ``jti``, and none gets an error instead of an answer;
- at each record the rows with ``expires_at < now − PRUNE_MARGIN_SECONDS`` are deleted, the margin being fixed:
  ``PANEL_CLOCK_SKEW_MAX_SECONDS + TICKET_MAX_LIFETIME_SECONDS`` = 300 + 300 = 600 s, whatever
  ``LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS`` says (the registry no longer reads the tolerance; ``record`` takes none). Pruning
  at the verification's own edge (``now − skew``) would let a clock that steps back (NTP, a VM resumed after sleep), or a
  tolerance raised at a restart, make a pruned ticket valid again, and it would pass twice; the margin keeps every row
  whose ticket any tolerance, at any clock the instance may see next, still accepts. A deleted ``jti`` is new again, since
  ``verify_ticket`` refuses its expired ticket first;
- the file outlives the process: a server started again still refuses what was recorded before it;
- the file is created on first use, never at import, with mode ``0600``, in the data directory ``get_data_dir()`` gives
  at each call, outside every entry an archive carries and every folder a restore swaps (``instance_backup/paths.py``);
- a file that cannot be used (a folder in its place, a file that is not SQLite, a data directory that cannot be written)
  raises the error the access turns into the scope's 503 ``…_unavailable``: the request gets its answer, the route never
  runs, and what stands in the file's place is left as it was. A symbolic link at the file's path is such a file, even
  one to a valid SQLite file or to nothing: the registry looks at the path itself (``os.lstat``) before it connects,
  anything but a regular file raises, the link stays as it was, and a dangling link's target is never created.

The tests, with the item of the brief they cover:

- HPR-001 (1): a ``jti`` recorded once is refused the second time, in one process.
- HPR-002 (2): the module imported anew, a fresh module state on the same file, still refuses it.
- HPR-003 (2): a new process on the same file, a server started again, still refuses it.
- HPR-004 (3): four threads record one ``jti`` together, released by a barrier, round after round: one ``True`` a round.
- HPR-005 (3): two spawned processes, likewise; their first round also creates the file together.
- HPR-006 (4): pruning at the fixed margin of 600 s, the tolerance unset (60), 0 and 300 changing nothing; a pruned
  ``jti`` is new again.
- HPR-007 (5): an unusable file (a folder, not SQLite, a data directory that cannot be written, a dangling symbolic link,
  a symbolic link to a SQLite file) raises ``TicketRegistryError``, the registry's own class, which the access turns into
  the scope's 503 (any other error is a 500), twice, and is left as it was, a link's target too (a dangling one never
  created); taken away, the same record is accepted.
- HPR-008 (5): through ``panel_access``, each scope: an unusable file gives the scope's 503 and the route never runs;
  taken away, a ticket is accepted (``credential="ticket"``, its ``kid`` and ``jti``) and its ``jti`` recorded.
- HPR-009 (6): the file is created on first use, never at import, with mode ``0600`` under the umask 022.
- HPR-010 (6): the file is SQLite with the contract's table, outside every archived entry and swapped folder.
- HPR-011 (6): the file is the one of the data directory read at each call.
- HPR-012 (4): a ticket recorded and pruned by the old edge, then the clock steps back, or the tolerance is raised: its
  replay is still refused.

How. Pure: no server, no lane database, no network, no file outside ``tmp_path``. Each test has a data directory of its
own (``LIBREFOLIO_TEST_MODE``, ``LIBREFOLIO_TEST_DATA_DIR``), made empty with mode ``0700``, and the tolerance's variable
unset unless the test sets it. The clock is injected: every record is given a fixed ``now``. Threads and processes are
released together by barriers, and nothing sleeps; a process is spawned (``multiprocessing.get_context("spawn")``),
imports this module and points itself at the test's data directory. The table is read with ``sqlite3`` and found by its
columns, its name being the module's choice. HPR-008 sends, in this process through ``httpx.ASGITransport``, tickets
PyJWT signs with an Ed25519 key from a fixed seed (a test key, never for production); the access reads its own clock, so
they are issued at the real time and live 120 seconds, far from either edge of the tolerance. This file does not use
``from __future__ import annotations``: a test route's ``Annotated[..., Depends(...)]`` is built from a local dependency.

Red today (against the first cut, which prunes at ``now − tolerance`` and follows a symbolic link at the file's path):
HPR-006 in its three cases fails on its ``rows == expected`` assertion, the rows at ``now − 600`` and within it having
been deleted by the pruning at ``now − 0``, ``now − 60`` or ``now − 300``; HPR-012 in both cases fails on its first
assertion, the first row gone after the pruning record; HPR-007 and HPR-008 with the two links fail where the link is
followed, ``record`` answering ``True`` (HPR-007: «record() raises» on the first attempt; HPR-008: a 200 where the
scope's 503 is). The links' targets are in a subfolder of the data directory, not beside it: the test-mode guard of
``get_data_dir()`` would otherwise refuse a link leaving the data directory with a ``ValueError`` before the registry
runs, which HPR-007 would take for a refusal and HPR-008 would see as a 500. The file collects.
"""

import asyncio
import base64
import contextlib
import functools
import hashlib
import importlib
import multiprocessing
import os
import queue
import sqlite3
import stat
import sys
import threading
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from multiprocessing.context import BaseContext
from multiprocessing.process import BaseProcess
from pathlib import Path
from types import ModuleType
from typing import Annotated, Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import Depends, FastAPI, Request

from backend.app.config import get_data_dir
from backend.app.services.platform import client_address as client_address_module
from backend.app.services.platform.instance_backup import paths as backup_paths
from backend.test_scripts.test_utils import print_section, print_success

# =============================================================================
# THE CONTRACT, SPELLED OUT
# =============================================================================

#: The modules of H-61 CP2 this file needs, imported when a test needs them, and their files for the red message.
REGISTRY_MODULE = "backend.app.services.platform.hosting_panel.ticket_registry"
ACCESS_MODULE = "backend.app.services.platform.hosting_panel.access"
_SOURCES = {
    REGISTRY_MODULE: "backend/app/services/platform/hosting_panel/ticket_registry.py",
    ACCESS_MODULE: "backend/app/services/platform/hosting_panel/access.py",
}

#: The registry's file in the data directory, and the columns of its table: name → (declared type, place in the primary
#: key, 0 when outside it).
REGISTRY_FILE = "panel_tickets.sqlite3"
TABLE_COLUMNS = {"jti": ("TEXT", 1), "expires_at": ("INTEGER", 0)}

#: The tolerance of the clock: its variable, and its value when the variable is unset.
SKEW_VARIABLE = "LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS"
DEFAULT_SKEW = 60

#: The registry's fixed pruning margin: a record deletes the rows with ``expires_at < now − PRUNE_MARGIN_SECONDS``. Pinned
#: here, once, as a literal built from its two parts: the largest tolerance (``PANEL_CLOCK_SKEW_MAX_SECONDS``) and the
#: longest a ticket lives (``TICKET_MAX_LIFETIME_SECONDS``). It is the registry's ``PRUNE_MARGIN_SECONDS`` too (HPR-006).
PRUNE_MARGIN_SECONDS = 300 + 300

#: The clock of the records: a fixed instant (2027-01-15 08:00:00 UTC), which the tests move themselves.
NOW = 1_800_000_000
#: The longest a ticket lives (``exp − iat ≤ 300``): how far past their ``now`` the records' ``expires_at`` usually is.
LIFETIME = 300

#: What may stand where the registry's file goes, as the tests put it there.
FOLDER = "folder"
NOT_SQLITE_FILE = "not-sqlite"
READ_ONLY = "read-only-data-directory"
DANGLING_LINK = "dangling-symlink"
LINK_TO_SQLITE = "symlink-to-a-sqlite-file"
#: Where the two links point: a subfolder of the data directory itself. Not outside it: in test mode ``get_data_dir()``
#: resolves the registry's path (``validate_test_data_dir``, ``managed_paths``) and raises «Test data path escapes its
#: configured root» for a link leaving the data directory, before the registry runs; with the targets inside, the guard
#: passes and the refusal under test is the registry's own. The name is none of the guard's managed paths.
LINK_TARGET_FOLDER = "link-targets"
LINK_TARGET_FILE = "target.sqlite3"
#: The table of a registry file as a valid one holds it, for the link whose target is a real SQLite file (the registry
#: finds its table by the columns, so the name is the module's choice; this is the target's own).
VALID_REGISTRY_DDL = "CREATE TABLE used_ticket (jti TEXT PRIMARY KEY, expires_at INTEGER NOT NULL)"
#: A file in the registry's place that is not SQLite: more than a page of text, which SQLite reads as «file is not a
#: database».
NOT_SQLITE = b"LibreFolio H-61 test: not a SQLite database, and nothing may replace it.\n" * 64

POSIX = os.name != "nt"
AS_ROOT = POSIX and os.geteuid() == 0
needs_posix_modes = pytest.mark.skipif(not POSIX, reason="file modes are POSIX only")
needs_permission_checks = pytest.mark.skipif(not POSIX or AS_ROOT, reason="needs POSIX permissions, which root bypasses")
needs_symlinks = pytest.mark.skipif(not POSIX, reason="symbolic links are POSIX only here")

OBSTACLES = [
    pytest.param(FOLDER, id="a-folder-in-its-place"),
    pytest.param(NOT_SQLITE_FILE, id="a-file-that-is-not-sqlite"),
    pytest.param(READ_ONLY, id="a-data-directory-that-cannot-be-written", marks=needs_permission_checks),
    pytest.param(DANGLING_LINK, id="a-dangling-symlink", marks=needs_symlinks),
    pytest.param(LINK_TO_SQLITE, id="a-symlink-to-a-sqlite-file", marks=needs_symlinks),
]

#: The races: racers released together by a barrier for each ``jti``, and how many ``jti`` they race on.
THREAD_RACERS = 4
THREAD_ROUNDS = 20
PROCESS_RACERS = 2
PROCESS_ROUNDS = 10
#: Generous: a spawned process imports the application first, and a loaded parallel run is slow. A hang still ends.
RACE_TIMEOUT_SECONDS = 120

#: HPR-008: the three scopes of the panel, as ``PanelScope``'s values, and the code of each one's 503.
BACKUP, WAKE, STATUS = "backup", "wake", "status"
SCOPES = (BACKUP, WAKE, STATUS)
UNAVAILABLE_CODES = {BACKUP: "backup_panel_unavailable", WAKE: "wake_unavailable", STATUS: "panel_status_unavailable"}
#: The variables of the three scopes' tokens and their ``_FILE``s: none is set, so tickets are the only way in.
TOKEN_VARIABLES = tuple(name for variable in ("LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN", "LIBREFOLIO_WAKE_TOKEN", "LIBREFOLIO_PANEL_STATUS_TOKEN") for name in (variable, f"{variable}_FILE"))
KEYS_VARIABLE = "LIBREFOLIO_PANEL_PUBLIC_KEYS"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
#: The instance's public address, already an origin in its canonical form: the audience of its tickets, as written.
AUDIENCE = "https://registry.h61.example"
TICKET_TYPE = "lf-panel+jwt"
KID = "h61-registry-test"
#: The seed of the tests' signing key: fixed and published here, a test key, never for production.
SEED = hashlib.sha256(b"LibreFolio H-61 CP2 test_hosting_panel_registry: a test key, never for production").digest()
#: How long the tickets of HPR-008 live: well inside the 300 seconds a ticket may live, far from either edge.
TICKET_SECONDS = 120
#: The test routes, one per scope: method and path.
ROUTES = {BACKUP: ("POST", "/hpr-test/backup"), WAKE: ("POST", "/hpr-test/wake"), STATUS: ("GET", "/hpr-test/status")}
#: The peer of the requests (``httpx.ASGITransport``'s ``client``): a public address.
PEER = ("203.0.113.70", 50000)
BASE_URL = "http://hpr.test"
#: Every in-process call ends within this, or the test fails instead of hanging.
CALL_SECONDS = 10.0


def a_jti(label: str) -> str:
    """A ``jti`` as the signer makes them, 16 bytes in base64url (22 characters of ``[A-Za-z0-9_-]``), fixed by ``label``."""
    return base64.urlsafe_b64encode(hashlib.sha256(label.encode("utf-8")).digest()[:16]).rstrip(b"=").decode("ascii")


# =============================================================================
# THE MODULES OF H-61 CP2, IMPORTED WHEN A TEST RUNS
# =============================================================================


def _module(name: str) -> ModuleType:
    """The module ``name``, imported when a test needs it: before H-61 CP2 the registry does not exist, and the rest of
    this file must still be collected."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        # The module itself missing is the red; a module it imports missing is a finding, raised as it is.
        if error.name != name:
            raise
    pytest.fail(f"H-61 CP2: {_SOURCES[name]} is missing")


def _given(module: ModuleType, name: str) -> Any:
    """``module.name``, the test failing when the module does not give it."""
    value = getattr(module, name, None)
    if value is None:
        pytest.fail(f"H-61 CP2: {module.__name__} gives no {name}")
    return value


def _record(registry: ModuleType, jti: str, expires_at: int, now: int) -> object:
    """``record(jti, expires_at, now)``, the call of the contract, written in this one place."""
    return registry.record(jti, expires_at=expires_at, now=now)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """A data directory of this test only, in test mode, made as a server makes one (``0700``) and empty: whatever the
    registry creates there is visible. The tolerance is the default, its variable unset, unless the test sets it."""
    for variable in ("LIBREFOLIO_DATA_DIR", SKEW_VARIABLE):
        monkeypatch.delenv(variable, raising=False)
    folder = tmp_path / "data"
    folder.mkdir(mode=0o700)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(folder))
    data = folder.resolve()
    assert get_data_dir() == data, f"Precondition: the data directory of this test is its own, under tmp_path, not {get_data_dir()}"
    return data


@pytest.fixture
def registry(data_dir: Path) -> ModuleType:
    """The registry module, imported once this test's data directory is in place. Before H-61 CP2 the test fails here."""
    module = _module(REGISTRY_MODULE)
    _given(module, "record")
    return module


@pytest.fixture
def permissive_umask() -> Iterator[None]:
    """The umask 022 many servers run with, for the test, put back after it: a file made with the default mode would be
    0644 under it, so a 0600 file is one the registry asked for."""
    previous = os.umask(0o022)
    try:
        yield
    finally:
        os.umask(previous)


@dataclass(frozen=True)
class Obstacle:
    """What a test put where the registry's file goes (``kind``, at ``path``), and how to take it away."""

    kind: str
    path: Path
    remove: Callable[[], None]
    #: Where a link points (the two link kinds), else None: a test reads that the registry left it as it was.
    target: Path | None = None


def _link_target(data_dir: Path) -> Path:
    """The file the links of the two link kinds point to: in a subfolder of ``data_dir`` (see ``LINK_TARGET_FOLDER``)."""
    return data_dir / LINK_TARGET_FOLDER / LINK_TARGET_FILE


def _place(kind: str, data_dir: Path) -> Callable[[], None]:
    """Put ``kind`` in the way of the registry's file in ``data_dir``; give back what takes it away."""
    path = data_dir / REGISTRY_FILE
    if kind == FOLDER:
        path.mkdir(mode=0o700)
        return path.rmdir
    if kind == NOT_SQLITE_FILE:
        path.write_bytes(NOT_SQLITE)
        path.chmod(0o600)
        return path.unlink
    if kind == READ_ONLY:
        data_dir.chmod(0o500)
        return functools.partial(data_dir.chmod, 0o700)
    if kind in (DANGLING_LINK, LINK_TO_SQLITE):
        target = _link_target(data_dir)
        target.parent.mkdir(mode=0o700)
        if kind == LINK_TO_SQLITE:
            with contextlib.closing(sqlite3.connect(target)) as connection, connection:
                connection.execute(VALID_REGISTRY_DDL)
            target.chmod(0o600)
        path.symlink_to(target)
        return path.unlink
    raise ValueError(f"no such obstacle: {kind!r}")


@pytest.fixture
def obstacle(request: pytest.FixtureRequest, data_dir: Path) -> Iterator[Obstacle]:
    """The obstacle of the test's parameter (``OBSTACLES``) in place. After the test the data directory is writable
    again, whatever happened, so that ``tmp_path`` can be removed."""
    try:
        target = _link_target(data_dir) if request.param in (DANGLING_LINK, LINK_TO_SQLITE) else None
        yield Obstacle(request.param, data_dir / REGISTRY_FILE, _place(request.param, data_dir), target)
    finally:
        data_dir.chmod(0o700)


# =============================================================================
# THE FILE, ITS TABLE, A FRESH MODULE STATE
# =============================================================================


def _entries(folder: Path) -> list[str]:
    return sorted(entry.name for entry in folder.iterdir())


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _state(path: Path) -> tuple[object, ...]:
    """What stands at ``path``: a link and its target, a folder and its entries, a file and its bytes, or nothing."""
    if path.is_symlink():
        return ("link", os.readlink(path))
    if path.is_dir():
        return ("folder", _entries(path))
    if path.is_file():
        return ("file", path.read_bytes())
    return ("nothing",)


def _summary(state: tuple[object, ...]) -> str:
    """``_state`` in a few words: the bytes of a file are counted, never written out."""
    if state[0] == "file":
        return f"a file of {len(state[1])} bytes"
    return " ".join(str(part) for part in state)


@contextlib.contextmanager
def _connected(path: Path) -> Iterator[sqlite3.Connection]:
    """A connection of the test to the registry's file, which must exist (``mode=rw`` never creates one), closed after
    the block; it only reads. Its busy timeout is the app's, 30 seconds."""
    assert path.is_file(), f"{path.name} is not a file in the data directory, whose entries are {_entries(path.parent)}"
    connection = sqlite3.connect(f"{path.as_uri()}?mode=rw", uri=True, timeout=30.0)
    try:
        yield connection
    finally:
        connection.close()


def _quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _columns(connection: sqlite3.Connection, table: str) -> dict[str, tuple[str, int]]:
    """The columns of ``table``: name → (declared type in upper case, place in the primary key, 0 when outside it)."""
    return {row[1]: (str(row[2]).upper(), row[5]) for row in connection.execute(f"PRAGMA table_info({_quoted(table)})")}


def _registry_table(connection: sqlite3.Connection) -> str:
    """The one table of the file with a ``jti`` and an ``expires_at`` column: its name is the module's choice."""
    tables = [name for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
    matching = [name for name in tables if {"jti", "expires_at"} <= set(_columns(connection, name))]
    assert len(matching) == 1, f"the registry's file holds one table (jti TEXT PRIMARY KEY, expires_at INTEGER): its tables are {tables}"
    return matching[0]


def _rows(data_dir: Path) -> dict[str, int]:
    """What the registry's file of ``data_dir`` holds: ``jti`` → ``expires_at``."""
    with _connected(data_dir / REGISTRY_FILE) as connection:
        table = _registry_table(connection)
        return dict(connection.execute(f"SELECT jti, expires_at FROM {_quoted(table)}").fetchall())


def _fresh_import(monkeypatch: pytest.MonkeyPatch, name: str) -> ModuleType:
    """The module ``name`` imported anew, with none of the state of the copy already imported: a restarted server's.

    ``sys.modules`` and the package's attribute are put back after the test, so every later import gets the original
    copy again.
    """
    original = sys.modules.get(name)
    assert original is not None, f"Precondition: {name} is imported before it is imported anew"
    package_name, _, attribute = name.rpartition(".")
    monkeypatch.setattr(importlib.import_module(package_name), attribute, original)
    monkeypatch.delitem(sys.modules, name)
    return importlib.import_module(name)


# =============================================================================
# THE RACES: THREADS AND SPAWNED PROCESSES RELEASED TOGETHER
# =============================================================================


def _one_answer(registry: ModuleType, jti: str) -> object:
    """What a racer gets for ``jti``: ``record``'s answer, or the text of what it raised instead."""
    try:
        return _record(registry, jti, NOW + LIFETIME, NOW)
    except Exception as exc:  # reported by the test, which asks every racer for an answer
        return f"{type(exc).__name__}: {exc}"


def _assert_one_true_per_round(jtis: Sequence[str], answers: Sequence[Sequence[object]]) -> None:
    """Every racer answered every round with a bool, and of each round's answers exactly one is ``True``."""
    failures = [answer for racer in answers for answer in racer if not isinstance(answer, bool)]
    assert not failures, f"a racer got an error instead of an answer, or its barrier broke: {failures[:5]}. Workers recording at once all get an answer: a check then a write in one deferred transaction fails at once under WAL (SQLITE_BUSY_SNAPSHOT), which busy_timeout does not wait for"
    assert all(len(racer) == len(jtis) for racer in answers), f"every racer answers every round: {[len(racer) for racer in answers]} answers for {len(jtis)} rounds"
    accepted = {jti: sum(racer[index] is True for racer in answers) for index, jti in enumerate(jtis)}
    wrong = {jti: count for jti, count in accepted.items() if count != 1}
    assert not wrong, f"of {len(answers)} racers recording one jti together exactly one gets True, the others False: {len(wrong)} of {len(jtis)} rounds had another count of True ({sorted(wrong.values())}). Two True would let one ticket count twice"


def _race_in_threads(registry: ModuleType, jtis: Sequence[str]) -> list[list[object]]:
    """``THREAD_RACERS`` threads recording each of ``jtis`` together, released by a barrier for each: their answers, one
    list per thread, in the order of ``jtis``. A thread still running at the deadline fails the test."""
    barrier = threading.Barrier(THREAD_RACERS)
    answers: list[list[object]] = [[] for _ in range(THREAD_RACERS)]

    def race(racer: int) -> None:
        try:
            for jti in jtis:
                barrier.wait(timeout=RACE_TIMEOUT_SECONDS)
                answers[racer].append(_one_answer(registry, jti))
        except threading.BrokenBarrierError:
            answers[racer].append("the barrier broke: another racer hung")

    threads = [threading.Thread(target=race, args=(racer,), name=f"hpr-racer-{racer}", daemon=True) for racer in range(THREAD_RACERS)]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + RACE_TIMEOUT_SECONDS
    for thread in threads:
        thread.join(timeout=max(0.0, deadline - time.monotonic()))
    stuck = [thread.name for thread in threads if thread.is_alive()]
    if stuck:
        barrier.abort()
        pytest.fail(f"racing threads still running after {RACE_TIMEOUT_SECONDS} s: {stuck}")
    return answers


def _point_at(data_dir: str) -> None:
    """In a spawned process: the test's data directory, in test mode, whatever environment it inherited."""
    os.environ["LIBREFOLIO_TEST_MODE"] = "1"
    os.environ["LIBREFOLIO_TEST_DATA_DIR"] = data_dir


def _records_in_a_new_process(data_dir: str, records: list[tuple[str, int, int]], results: Any) -> None:
    """Runs in a spawned process, a server started again on the test's data directory: records each ``(jti, expires_at,
    now)`` in order and sends back the answers.

    Module level, so that the spawned interpreter imports it by name. What fails is sent back as text: the test reports it
    instead of waiting for an answer that never comes.
    """
    answers: list[object] = []
    try:
        _point_at(data_dir)
        registry = importlib.import_module(REGISTRY_MODULE)
        answers.extend(_record(registry, jti, expires_at, now) for jti, expires_at, now in records)
    except Exception as exc:  # sent back: the test reports it
        answers.append(f"failed: {type(exc).__name__}: {exc}")
    results.put(answers)


def _races_in_a_process(data_dir: str, jtis: list[str], barrier: Any, results: Any) -> None:
    """Runs in a spawned process, a worker of a server sharing the test's data directory: for each of ``jtis``, waits at
    the barrier for every racer, then records it at the same moment as the others, and sends back the answers.

    Module level, so that the spawned interpreter imports it by name. A racer that cannot go on breaks the barrier, so the
    others stop waiting for it, and sends back what failed.
    """
    answers: list[object] = []
    try:
        _point_at(data_dir)
        registry = importlib.import_module(REGISTRY_MODULE)
        for jti in jtis:
            barrier.wait(timeout=RACE_TIMEOUT_SECONDS)
            answers.append(_one_answer(registry, jti))
    except Exception as exc:  # sent back, the barrier broken: the test reports it
        barrier.abort()
        answers.append(f"failed: {type(exc).__name__}: {exc}")
    results.put(answers)


@contextlib.contextmanager
def _spawned(context: BaseContext, target: Callable[..., None], arguments: Sequence[tuple[Any, ...]]) -> Iterator[list[BaseProcess]]:
    """Spawned processes running ``target``, one per tuple of ``arguments``, started now; after the block each is waited
    for, and killed if it hangs."""
    processes = [context.Process(target=target, args=args, name=f"hpr-process-{index}", daemon=True) for index, args in enumerate(arguments)]
    for process in processes:
        process.start()
    try:
        yield processes
    finally:
        for process in processes:
            process.join(timeout=RACE_TIMEOUT_SECONDS)
            if process.is_alive():
                process.kill()
                process.join(timeout=10)


def _answers(results: Any, processes: Sequence[BaseProcess]) -> list[Any]:
    """One message per process, polled with a deadline: a process that dies or hangs fails the test instead of blocking it."""
    received: list[Any] = []
    deadline = time.monotonic() + RACE_TIMEOUT_SECONDS
    while len(received) < len(processes):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            pytest.fail(f"only {len(received)} of {len(processes)} spawned processes answered within {RACE_TIMEOUT_SECONDS} s: {received}")
        try:
            received.append(results.get(timeout=min(remaining, 1.0)))
        except queue.Empty:
            if not any(process.is_alive() for process in processes) and results.empty():
                pytest.fail(f"the spawned processes exited without answering (exit codes {[process.exitcode for process in processes]}): {received}")
    return received


# =============================================================================
# HPR-008: SIGNED TICKETS, THE TEST ROUTES, ONE REQUEST
# =============================================================================


def _signing_key() -> Ed25519PrivateKey:
    """The tests' signer: an Ed25519 private key from the fixed ``SEED``."""
    return Ed25519PrivateKey.from_private_bytes(SEED)


def _public_key_text() -> str:
    """The signer's public key as ``LIBREFOLIO_PANEL_PUBLIC_KEYS`` takes one: the raw 32 bytes in base64url without
    padding, 43 characters."""
    raw = _signing_key().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _ticket(scope: str, jti: str) -> str:
    """A valid ticket of ``scope``, ``jti`` its id, issued now on the real clock (the access reads its own) for
    ``TICKET_SECONDS``: EdDSA, ``typ`` ``lf-panel+jwt``, ``kid`` ``KID``, ``aud`` the instance's origin."""
    issued_at = int(time.time())
    claims = {"aud": AUDIENCE, "scope": scope, "iat": issued_at, "exp": issued_at + TICKET_SECONDS, "jti": jti}
    return jwt.encode(claims, _signing_key(), algorithm="EdDSA", headers={"typ": TICKET_TYPE, "kid": KID})


def _keys_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """L2 alone on every scope: the test key under ``KID``, the public address the audience comes from, the default
    tolerance, no token of any scope, the self-hosted profile. ``LIBREFOLIO_CLIENT_IP_HEADER`` is read as unset whatever
    the lane sets (``_configured_header`` replaced, its per-process cache never filled)."""
    for name in (*TOKEN_VARIABLES, SKEW_VARIABLE, "LIBREFOLIO_PROFILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(KEYS_VARIABLE, f"{KID}:{_public_key_text()}")
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, AUDIENCE)
    monkeypatch.setattr(client_address_module, "_configured_header", lambda: None)


#: The test routes' endpoints, built once per process from the access module (``panel_access`` gives the same object for
#: the same scope) and kept: FastAPI caches the context of an endpoint by its ``id()``, which a freed one could lend.
_ENDPOINTS: dict[str, Callable[..., Any]] = {}


def _endpoint(access: ModuleType, scope: str) -> Callable[..., Any]:
    """The test route of ``scope``: its caller is ``Depends(panel_access(PanelScope(scope)))``; it records the caller it
    gets, so a test sees whether the route ran."""
    if scope not in _ENDPOINTS:
        dependency = access.panel_access(access.PanelScope(scope))

        async def route(request: Request, caller: Annotated[Any, Depends(dependency)]) -> dict[str, str]:
            request.app.state.served.append((scope, caller))
            return {"served": scope}

        route.__name__ = route.__qualname__ = f"hpr_test_{scope}_route"
        _ENDPOINTS[scope] = route
    return _ENDPOINTS[scope]


def _panel_app(access: ModuleType) -> FastAPI:
    """A fresh app holding the three test routes and nothing else."""
    app = FastAPI()
    app.state.served = []
    for scope in SCOPES:
        method, path = ROUTES[scope]
        app.add_api_route(path, _endpoint(access, scope), methods=[method])
    return app


async def _call(app: FastAPI, scope: str, ticket: str) -> httpx.Response:
    """The request of ``scope``'s test route with ``ticket`` as its bearer credential, in this process from ``PEER``,
    within ``CALL_SECONDS``: an exception the app does not handle comes back as its 500, never raised here."""
    method, path = ROUTES[scope]
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False, client=PEER)
    try:
        async with asyncio.timeout(CALL_SECONDS):
            async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as http:
                return await http.request(method, path, headers={"Authorization": f"Bearer {ticket}"})
    except TimeoutError:
        pytest.fail(f"{method} {path}: no answer within {CALL_SECONDS} s")


def _answer(response: httpx.Response) -> tuple[int, object]:
    """Status and body: the JSON of a JSON answer, the first bytes of any other, so a red always reads."""
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.status_code, response.json()
    return response.status_code, response.content[:200]


def _covers(entry: Path, relative: Path) -> bool:
    """Whether the archive entry or folder ``entry`` is ``relative`` or holds it, both relative to the data directory."""
    return entry == relative or entry in relative.parents


# =============================================================================
# HPR-001..003 (§2, brief 1–2): a jti counts once, in one process and after a restart
# =============================================================================


def test_a_jti_recorded_once_is_refused_the_second_time(registry: ModuleType, data_dir: Path) -> None:
    """HPR-001 (§2, brief 1): ``record`` answers ``True`` for a ``jti`` never seen, ``False`` for the same one again, and
    keeps refusing it. Another ``jti`` is still new: the refusal is about that ``jti``, not a registry that refuses
    everything after its first record."""
    print_section("H-61 CP2 §2 registry: a jti recorded once is refused the second time")
    ticket, other = a_jti("HPR-001 a ticket"), a_jti("HPR-001 another ticket")
    expires_at = NOW + LIFETIME

    assert _record(registry, ticket, expires_at, NOW) is True, "a jti never recorded is new: record() answers True, a bool"
    assert _record(registry, ticket, expires_at, NOW + 1) is False, "the same jti again is a replay: record() answers False, a bool, and the access refuses with panel_ticket_replayed"
    assert _record(registry, other, expires_at, NOW + 1) is True, "canary: another jti is still new, so the refusal above is about that jti alone"
    assert _record(registry, ticket, expires_at, NOW + 2) is False, "a replayed jti stays refused: a refusal never frees it"
    assert _record(registry, other, expires_at, NOW + 2) is False, "the other jti, once recorded, is refused in its turn"
    print_success("True, then False for the same jti; another jti True, then False")


def test_a_fresh_module_state_on_the_same_file_still_refuses_a_recorded_jti(registry: ModuleType, data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """HPR-002 (§2, brief 2): the module imported anew has none of the state of the first copy, as after a restart; on
    the same file it still refuses a ``jti`` the first copy recorded, records a new one, and the first copy refuses that
    one: the two share the file, and nothing that matters lives in the process."""
    print_section("H-61 CP2 §2 registry: a fresh module state on the same file")
    before, after = a_jti("HPR-002 before the restart"), a_jti("HPR-002 after the restart")
    assert _record(registry, before, NOW + LIFETIME, NOW) is True, "Precondition: a jti never seen is recorded"

    restarted = _fresh_import(monkeypatch, REGISTRY_MODULE)

    assert restarted is not registry, "Precondition: the module imported anew is another module state"
    assert _record(restarted, before, NOW + LIFETIME, NOW + 1) is False, "after a restart the file still holds the jti: a ticket within its lifetime never counts twice"
    assert _record(restarted, after, NOW + LIFETIME, NOW + 1) is True, "canary: the fresh module state records a new jti in that file, so its refusal above came from the file"
    assert _record(registry, after, NOW + LIFETIME, NOW + 2) is False, "both module states share the one file: what the fresh one recorded, the first refuses"
    print_success("the fresh module state refuses the jti recorded before it, and shares the file")


def test_a_new_process_on_the_same_file_still_refuses_a_recorded_jti(registry: ModuleType, data_dir: Path) -> None:
    """HPR-003 (§2, brief 2): a server started again is a new process: spawned on the same data directory, it refuses
    the ``jti`` this process recorded and records a new one, which this process then refuses."""
    print_section("H-61 CP2 §2 registry: a new process on the same file")
    before, after = a_jti("HPR-003 before the restart"), a_jti("HPR-003 after the restart")
    assert _record(registry, before, NOW + LIFETIME, NOW) is True, "Precondition: a jti never seen is recorded"
    context = multiprocessing.get_context("spawn")
    results = context.Queue()
    records = [(before, NOW + LIFETIME, NOW + 1), (after, NOW + LIFETIME, NOW + 1)]

    with _spawned(context, _records_in_a_new_process, [(str(data_dir), records, results)]) as processes:
        [answers] = _answers(results, processes)

    assert answers == [False, True], f"a new process on the same file refuses the jti recorded before it started (False) and records a new one (True): it answered {answers}"
    assert [process.exitcode for process in processes] == [0], f"the new process ends cleanly: exit code {[process.exitcode for process in processes]}"
    assert _record(registry, after, NOW + LIFETIME, NOW + 2) is False, "this process sees what the new one recorded: one file for both"
    print_success("a new process refuses the old jti, records a new one, and this process refuses that one")


# =============================================================================
# HPR-004..005 (§2, brief 3): recording together, exactly one True
# =============================================================================


def test_threads_recording_one_jti_together_accept_it_exactly_once(registry: ModuleType, data_dir: Path) -> None:
    """HPR-004 (§2, brief 3): the access runs in the server's threads, so several may record one ``jti`` together.
    ``THREAD_RACERS`` threads, released by a barrier for each of ``THREAD_ROUNDS`` new ``jti``: each round, exactly one
    gets ``True``, the others ``False``, and none an error. The first round also makes the file, all at once."""
    print_section(f"H-61 CP2 §2 registry: {THREAD_RACERS} threads recording together, {THREAD_ROUNDS} rounds")
    jtis = [a_jti(f"HPR-004 round {round_number}") for round_number in range(THREAD_ROUNDS)]

    answers = _race_in_threads(registry, jtis)

    _assert_one_true_per_round(jtis, answers)
    assert set(_rows(data_dir)) == set(jtis), "every jti raced on is recorded once in the one file, and nothing else"
    print_success(f"{THREAD_ROUNDS} rounds, one True each")


def test_processes_recording_one_jti_together_accept_it_exactly_once(registry: ModuleType, data_dir: Path) -> None:
    """HPR-005 (§2, brief 3): the workers of a server share the file and its lock. ``PROCESS_RACERS`` spawned processes,
    released by a barrier for each of ``PROCESS_ROUNDS`` new ``jti``: each round, exactly one gets ``True``, the others
    ``False``, and none an error. Their first round also makes the file, as workers starting together would. This
    process then refuses every one of those ``jti``: the file is shared."""
    print_section(f"H-61 CP2 §2 registry: {PROCESS_RACERS} spawned processes recording together, {PROCESS_ROUNDS} rounds")
    jtis = [a_jti(f"HPR-005 round {round_number}") for round_number in range(PROCESS_ROUNDS)]
    context = multiprocessing.get_context("spawn")
    barrier, results = context.Barrier(PROCESS_RACERS), context.Queue()

    with _spawned(context, _races_in_a_process, [(str(data_dir), jtis, barrier, results)] * PROCESS_RACERS) as processes:
        answers = _answers(results, processes)

    _assert_one_true_per_round(jtis, answers)
    assert [process.exitcode for process in processes] == [0] * PROCESS_RACERS, f"every racing process ends cleanly: exit codes {[process.exitcode for process in processes]}"
    assert set(_rows(data_dir)) == set(jtis), "every jti raced on is recorded once in the one file, and nothing else"
    accepted_here = [jti for jti in jtis if _record(registry, jti, NOW + LIFETIME, NOW + 1) is not False]
    assert not accepted_here, f"this process shares the file: every jti the processes recorded is refused here too, {len(accepted_here)} were not"
    assert _record(registry, a_jti("HPR-005 canary"), NOW + LIFETIME, NOW + 1) is True, "canary: this process still records a new jti, so its refusals above came from the file"
    print_success(f"{PROCESS_ROUNDS} rounds across processes, one True each, all refused afterwards")


# =============================================================================
# HPR-006 (§2, brief 4): pruning
# =============================================================================


SKEWS = [
    pytest.param(None, DEFAULT_SKEW, id="tolerance-unset-is-60"),
    pytest.param("0", 0, id="tolerance-0"),
    pytest.param("300", 300, id="tolerance-300"),
]


@pytest.mark.parametrize(("configured", "skew"), SKEWS)
def test_a_record_deletes_the_rows_expired_beyond_the_fixed_margin_whatever_the_tolerance_and_a_deleted_jti_is_new_again(registry: ModuleType, data_dir: Path, monkeypatch: pytest.MonkeyPatch, configured: str | None, skew: int) -> None:
    """HPR-006 (§2, brief 4): three rows expiring one second apart; then, at ``now`` = the middle one's ``expires_at`` +
    ``PRUNE_MARGIN_SECONDS`` (600), a new record. The first row (``expires_at < now − 600``) is gone; the middle one, at
    ``now − 600`` exactly, stays (only ``<`` is deleted); the last one, within the margin, stays. The margin is fixed: the
    tolerance (unset, 0 or 300, ``skew``) is set for the whole test and changes nothing, so a row whose ticket a clock
    that stepped back, or a tolerance raised at a restart, would accept again is never deleted. The deleted ``jti`` is new
    again (its ticket is expired, and ``verify_ticket`` refuses it first); the others are still refused. The registry
    gives the margin it prunes by, ``PRUNE_MARGIN_SECONDS``, and it is the 600 pinned here."""
    print_section(f"H-61 CP2 §2 registry: pruning at the fixed margin of {PRUNE_MARGIN_SECONDS} s, tolerance {skew} s")
    if configured is not None:
        monkeypatch.setenv(SKEW_VARIABLE, configured)
    beyond, edge, within, trigger = (a_jti(f"HPR-006 {skew} {name}") for name in ("beyond", "edge", "within", "trigger"))
    expiries = {beyond: NOW + 100, edge: NOW + 101, within: NOW + 102}
    for jti, expires_at in expiries.items():
        assert _record(registry, jti, expires_at, NOW) is True, "Precondition: three jtis never seen are recorded"
    assert _rows(data_dir) == expiries, "Precondition: at NOW none is past its expiry, so the three rows are there, each with its expires_at"

    later = expiries[edge] + PRUNE_MARGIN_SECONDS  # later − margin is the edge row's expires_at exactly
    assert _record(registry, trigger, later + LIFETIME, later) is True, "Precondition: a new jti, recorded later, which prunes"
    rows = _rows(data_dir)

    assert beyond not in rows, f"at a record at now={later}, the row with expires_at {expiries[beyond]} < now − margin ({later - PRUNE_MARGIN_SECONDS}) is deleted: its ticket is long expired"
    expected = {edge: expiries[edge], within: expiries[within], trigger: later + LIFETIME}
    assert rows == expected, f"now={later}, tolerance {skew} s: the margin is {PRUNE_MARGIN_SECONDS} s whatever the tolerance, so the row at now − margin exactly stays (only expires_at < now − margin is deleted), the row within it stays, the new row is there: {rows}"
    assert _record(registry, beyond, expiries[beyond], later) is True, "a deleted jti is new again: its ticket is expired anyway, and verify_ticket refuses it before the registry"
    assert _record(registry, edge, expiries[edge], later) is False, "the row at now − margin exactly is still there: its jti is still refused"
    assert _record(registry, within, expiries[within], later) is False, "the row within the margin is still there: its jti is still refused"
    assert _given(registry, "PRUNE_MARGIN_SECONDS") == PRUNE_MARGIN_SECONDS, f"the registry's margin is the {PRUNE_MARGIN_SECONDS} s of the contract (300 + 300), the one this test pruned by"
    print_success(f"tolerance {skew} s changes nothing: the row beyond the {PRUNE_MARGIN_SECONDS} s margin deleted and new again, the edge and the one within kept")


#: HPR-012: the ticket's own life, in seconds from ``NOW``: recorded at ``NOW``, its ``expires_at`` is ``NOW + EXPIRES_IN``.
EXPIRES_IN = 120
#: HPR-012's two ways to make a pruned ticket valid again: (the tolerance at the pruning record, the tolerance at the
#: replay, the pruning record's ``now``, the replay's ``now``), the clocks as offsets from ``NOW``. The pruning record is
#: one second past the old edge (``expires_at + tolerance``) for a tolerance of 60; the replay is a moment the
#: verification accepts the ticket at (``expires_at > now − tolerance``), which the test checks.
REPLAYS = [
    pytest.param(60, 60, EXPIRES_IN + 60 + 1, 130, id="the-clock-steps-back"),
    pytest.param(60, 300, EXPIRES_IN + 60 + 1, EXPIRES_IN + 200, id="the-tolerance-is-raised"),
]


@pytest.mark.parametrize(("prune_skew", "replay_skew", "prune_at", "replay_at"), REPLAYS)
def test_a_ticket_the_old_pruning_edge_would_have_forgotten_is_still_refused_after_the_clock_or_the_tolerance_moves(registry: ModuleType, data_dir: Path, monkeypatch: pytest.MonkeyPatch, prune_skew: int, replay_skew: int, prune_at: int, replay_at: int) -> None:
    """HPR-012 (§2, brief 4): a jti recorded at ``NOW`` with ``expires_at = NOW + 120``, accepted. A record of another jti
    one second past the verification's edge for a tolerance of 60 (``NOW + 181``: the row would be pruned at
    ``now − tolerance``). Then either the clock steps back to ``NOW + 130`` (NTP, a VM resumed after sleep), or the
    tolerance is raised from 60 to 300 and the clock is at ``NOW + 320``: in both the ticket would pass the verification
    (``expires_at > now − tolerance``), so the first jti recorded again must be refused. It is, because the registry
    prunes at a fixed margin of 600 s and the row is still there; pruning at the verification's own edge would have
    deleted it, and the ticket would have passed twice."""
    print_section(f"H-61 CP2 §2 registry: tolerance {prune_skew} s then {replay_skew} s, pruning at +{prune_at}, replay at +{replay_at}")
    jti, trigger = a_jti(f"HPR-012 {prune_at} {replay_at} ticket"), a_jti(f"HPR-012 {prune_at} {replay_at} trigger")
    expires_at = NOW + EXPIRES_IN
    assert prune_at + NOW - prune_skew > expires_at, "Precondition: at the pruning record the verification's own edge is past the ticket's expiry: a registry pruning there deletes the row"
    assert expires_at > NOW + replay_at - replay_skew, "Precondition: at the replay the verification accepts the ticket again (exp > now − tolerance): only the registry stops it"
    monkeypatch.setenv(SKEW_VARIABLE, str(prune_skew))
    assert _record(registry, jti, expires_at, NOW) is True, "Precondition: the ticket's jti is new and recorded"

    assert _record(registry, trigger, NOW + prune_at + LIFETIME, NOW + prune_at) is True, "Precondition: a new jti, recorded one second past the old pruning edge, which prunes"

    assert _rows(data_dir).get(jti) == expires_at, f"the pruning record at now={NOW + prune_at} keeps the row of the ticket (expires_at {expires_at}): the margin is {PRUNE_MARGIN_SECONDS} s, not the tolerance of {prune_skew} s"
    monkeypatch.setenv(SKEW_VARIABLE, str(replay_skew))
    assert _record(registry, jti, expires_at, NOW + replay_at) is False, f"the ticket recorded again at now={NOW + replay_at} (tolerance {replay_skew} s) is a replay, the verification accepting it: refused"
    assert _record(registry, a_jti(f"HPR-012 {prune_at} {replay_at} canary"), expires_at, NOW + replay_at) is True, "canary: another jti is still new, so the refusal above is about that jti alone"
    print_success(f"tolerance {prune_skew} s then {replay_skew} s: the ticket still refused at +{replay_at}")


# =============================================================================
# HPR-007..008 (§2–§3, brief 5): a file that cannot be used
# =============================================================================


def _attempt(registry: ModuleType, jti: str) -> tuple[str, object]:
    """``("answered", answer)`` or ``("raised", error)`` for one record of ``jti``."""
    try:
        return "answered", _record(registry, jti, NOW + LIFETIME, NOW)
    except Exception as exc:  # any error is reported by the test, which then checks it is the registry's own class
        return "raised", exc


def _target_view(obstacle: Obstacle) -> tuple[object, ...] | None:
    """What stands where a link points, and the entries of its folder (a journal or a new file would show there); None
    for an obstacle that is no link."""
    if obstacle.target is None:
        return None
    return _state(obstacle.target), _entries(obstacle.target.parent)


def _summarised(view: tuple[object, ...] | None) -> str:
    """``_target_view`` in a few words: the state of the target, as ``_summary`` says it, and its folder's entries."""
    return "no link" if view is None else f"{_summary(view[0])} among {view[1]}"  # type: ignore[arg-type]


@pytest.mark.parametrize("obstacle", OBSTACLES, indirect=True)
def test_an_unusable_registry_file_raises_and_is_left_as_it_was(registry: ModuleType, data_dir: Path, obstacle: Obstacle) -> None:
    """HPR-007 (§2, brief 5): with a folder where the file goes, a file that is not SQLite, a data directory that
    cannot be written, a dangling symbolic link or a symbolic link to a valid SQLite file, ``record`` raises the
    registry's own ``TicketRegistryError`` (the access turns only that into the scope's 503, HPR-008; any other error is
    a 500), twice, and leaves what stands there as it was: never replaced nor removed.
    A link is refused as a link, before any connection: anything but a regular file at the path raises, so the target is
    left as it was too, a dangling one never created (nothing appears in its folder), a valid one never written. The
    targets are in a subfolder of the data directory: in test mode ``get_data_dir()`` refuses a link that leaves it
    before the registry runs, and that would be the error raised, not the registry's. Once the
    obstacle is taken away, the same record is accepted: the error was the obstacle's alone, and recorded nothing."""
    print_section(f"H-61 CP2 §2 registry: an unusable file, {obstacle.kind}")
    jti = a_jti(f"HPR-007 {obstacle.kind}")
    before = _state(obstacle.path)
    target_before = _target_view(obstacle)
    error_class = _given(registry, "TicketRegistryError")

    for attempt in (1, 2):
        outcome, detail = _attempt(registry, jti)
        assert outcome == "raised", f"attempt {attempt}: with {obstacle.kind} in the registry's way, record() raises the error the access turns into a 503, never answers: it answered {detail!r}"
        assert isinstance(detail, error_class), f"attempt {attempt}: with {obstacle.kind} in the registry's way, record() raises {error_class.__name__}, the one error the access turns into the scope's 503, anything else being a 500: it raised {type(detail).__name__}: {detail}"
        after = _state(obstacle.path)
        assert after == before, f"attempt {attempt}: what stands where {REGISTRY_FILE} goes is left as it was, never replaced nor removed: it was {_summary(before)}, it is {_summary(after)}"
        assert _target_view(obstacle) == target_before, f"attempt {attempt}: where the link points is left as it was, a dangling target never created, a valid one never written: it was {_summarised(target_before)}, it is {_summarised(_target_view(obstacle))}"

    obstacle.remove()
    assert _record(registry, jti, NOW + LIFETIME, NOW) is True, "canary: the obstacle taken away, the same record is accepted, so the error above was the obstacle's alone"
    assert obstacle.path.is_file() and not obstacle.path.is_symlink(), f"the obstacle taken away, the registry's file is made, a regular file: {_entries(data_dir)}"
    print_success(f"{obstacle.kind}: raised twice, left as it was; taken away, recorded")


@pytest.mark.asyncio
@pytest.mark.parametrize("obstacle", OBSTACLES, indirect=True)
@pytest.mark.parametrize("scope", SCOPES)
async def test_an_unusable_registry_file_gives_the_scopes_503_and_the_route_never_runs(registry: ModuleType, data_dir: Path, obstacle: Obstacle, scope: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """HPR-008 (§2–§3, brief 5): L2 alone, a valid ticket of ``scope``, the registry's file unusable: the answer is the
    scope's 503, ``{"detail": {"code": "<scope>_unavailable", "message": …}}``, not a 500, the ticket nowhere in it, and
    the route never runs: the registry is written before the route works. The obstacle taken away, another ticket of the
    same scope is accepted, through the ticket (``credential="ticket"``, its ``kid`` and ``jti``), and its ``jti`` is the
    one the file holds: the 503 was the registry's alone, and recorded nothing."""
    print_section(f"H-61 CP2 §2–§3: {obstacle.kind}, a ticket of {scope} gets the scope's 503")
    access = _module(ACCESS_MODULE)
    for name in ("PanelScope", "panel_access"):
        _given(access, name)
    _keys_only(monkeypatch)
    app = _panel_app(access)
    refused_jti, accepted_jti = a_jti(f"HPR-008 {scope} {obstacle.kind} refused"), a_jti(f"HPR-008 {scope} {obstacle.kind} accepted")
    refused_ticket = _ticket(scope, refused_jti)

    response = await _call(app, scope, refused_ticket)

    status, body = _answer(response)
    detail = body.get("detail") if isinstance(body, dict) else None
    assert status == 503, f"{scope}, {obstacle.kind}: a registry that cannot record the ticket gives the scope's 503, never a 500 nor an acceptance: {status} {body!r}"
    assert isinstance(body, dict) and sorted(body) == ["detail"] and isinstance(detail, dict) and sorted(detail) == ["code", "message"], f"the body is {{'detail': {{'code', 'message'}}}}: {body!r}"
    assert detail["code"] == UNAVAILABLE_CODES[scope], f"the code is the scope's own: {detail['code']!r}, not {UNAVAILABLE_CODES[scope]!r}"
    assert isinstance(detail["message"], str) and detail["message"].strip(), f"the message says something: {detail['message']!r}"
    assert refused_ticket not in response.text and not any(refused_ticket in value for value in response.headers.values()), "the ticket never shows in an answer"
    assert app.state.served == [], f"the route never runs when the registry cannot record its ticket: it ran for {app.state.served}"

    obstacle.remove()
    accepted_ticket = _ticket(scope, accepted_jti)
    response = await _call(app, scope, accepted_ticket)

    assert _answer(response) == (200, {"served": scope}), f"canary: the obstacle taken away, a ticket of {scope} is accepted, so the 503 was the registry's alone: {_answer(response)}"
    callers = [(served, getattr(caller, "credential", None), getattr(caller, "kid", None), getattr(caller, "jti", None)) for served, caller in app.state.served]
    assert callers == [(scope, "ticket", KID, accepted_jti)], f"the route ran once, for a caller that came in by its ticket: {callers}"
    assert set(_rows(data_dir)) == {accepted_jti}, "the accepted ticket's jti is the one the registry holds; the one refused with 503 was never recorded"
    print_success(f"{scope}, {obstacle.kind}: 503 {UNAVAILABLE_CODES[scope]}, the route not run; taken away, accepted")


# =============================================================================
# HPR-009..011 (§2, brief 6): the file
# =============================================================================


@needs_posix_modes
def test_the_file_is_created_on_first_use_in_the_data_directory_with_mode_600(registry: ModuleType, data_dir: Path, monkeypatch: pytest.MonkeyPatch, permissive_umask: None) -> None:
    """HPR-009 (§2, brief 6): importing the registry (anew, so this test sees it) creates nothing; the first record makes
    ``panel_tickets.sqlite3`` in the data directory, a plain file with mode ``0600`` even under the umask 022."""
    print_section("H-61 CP2 §2 registry: the file is created on first use, mode 0600")
    fresh = _fresh_import(monkeypatch, REGISTRY_MODULE)
    path = data_dir / REGISTRY_FILE
    assert _entries(data_dir) == [], f"importing the registry creates nothing in the data directory: the file is made on first use: {_entries(data_dir)}"

    assert _record(fresh, a_jti("HPR-009 the first ticket"), NOW + LIFETIME, NOW) is True, "Precondition: the first jti is new"

    assert path.is_file() and not path.is_symlink(), f"the first record makes {REGISTRY_FILE}, a plain file, in the data directory: {_entries(data_dir)}"
    assert _mode(path) == 0o600, f"{REGISTRY_FILE} has mode 0600, even under the umask 022 a server often has: {_mode(path):04o}"
    print_success(f"{REGISTRY_FILE} made by the first record, mode 0600")


def test_the_file_is_sqlite_with_the_contracts_table_and_outside_every_archive(registry: ModuleType, data_dir: Path) -> None:
    """HPR-010 (§2, brief 6): the file is SQLite and holds the table ``(jti TEXT PRIMARY KEY, expires_at INTEGER)``, the
    record being the ``jti`` with its ``expires_at`` as given. It is ``panel_tickets.sqlite3`` at the top of the data
    directory: neither an entry an archive carries (``DATABASE_ENTRY``, ``MANIFEST_ENTRY``, ``INSTANCE_KEY_ENTRY``) nor in
    one of the folders it carries whole (``ARCHIVED_FOLDERS``), nor in one a restore swaps (``SWAPPED_FOLDERS``): out of
    the backups, and never touched by a restore."""
    print_section("H-61 CP2 §2 registry: SQLite, the contract's table, outside the backups")
    jti = a_jti("HPR-010 a ticket")
    assert _record(registry, jti, NOW + LIFETIME, NOW) is True, "Precondition: a jti never seen is recorded"
    path = data_dir / REGISTRY_FILE

    with _connected(path) as connection:
        table = _registry_table(connection)
        columns = _columns(connection, table)
    assert columns == TABLE_COLUMNS, f"the table is (jti TEXT PRIMARY KEY, expires_at INTEGER): its columns are {columns} (name: declared type, place in the primary key)"
    assert _rows(data_dir) == {jti: NOW + LIFETIME}, "the record is the jti with its expires_at, as given"

    relative = path.relative_to(data_dir)
    carried = (backup_paths.DATABASE_ENTRY, backup_paths.MANIFEST_ENTRY, backup_paths.INSTANCE_KEY_ENTRY, *backup_paths.ARCHIVED_FOLDERS)
    inside = [entry for entry in (*carried, *backup_paths.SWAPPED_FOLDERS) if _covers(Path(entry), relative)]
    assert relative == Path(REGISTRY_FILE), f"the registry's file is at the top of the data directory: {relative}"
    assert not inside, f"{relative} is among what an archive carries or a restore swaps: {inside}. The registry stays out of the backups, and a restore never touches it"
    print_success(f"{REGISTRY_FILE}: SQLite, (jti TEXT PRIMARY KEY, expires_at INTEGER), outside {carried} and {backup_paths.SWAPPED_FOLDERS}")


def test_the_file_is_the_one_of_the_data_directory_read_at_each_call(registry: ModuleType, data_dir: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """HPR-011 (§2, brief 6): the file is ``get_data_dir() / panel_tickets.sqlite3``, the data directory read at each
    call, as ``instance_key_path()`` reads it: another data directory is another registry, where the same ``jti`` is new;
    back on the first one, its file still refuses it."""
    print_section("H-61 CP2 §2 registry: the data directory read at each call")
    jti = a_jti("HPR-011 a ticket")
    assert _record(registry, jti, NOW + LIFETIME, NOW) is True, "Precondition: a jti never seen is recorded"
    other = tmp_path / "another-installation"
    other.mkdir(mode=0o700)
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(other))
    assert get_data_dir() == other.resolve(), f"Precondition: the data directory is now the other one, not {get_data_dir()}"

    assert _record(registry, jti, NOW + LIFETIME, NOW) is True, "another data directory is another registry, where the jti is new: the file is get_data_dir()'s, read at each call"
    assert (other / REGISTRY_FILE).is_file(), f"the record made {REGISTRY_FILE} in the data directory of the call: {_entries(other)}"
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(data_dir))
    assert _record(registry, jti, NOW + LIFETIME, NOW + 1) is False, "back on the first data directory, its file still refuses the jti"
    print_success("one registry per data directory, read at each call")
