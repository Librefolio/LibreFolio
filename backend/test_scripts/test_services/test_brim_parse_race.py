"""Parsing a file that moves underfoot.

A successful parse transitions the file uploaded → parsed, and that transition is
a physical rename. Two clients parsing the same file at once therefore race: the
second resolved its path before the rename and reads it after, so it fails on a
path that no longer exists — with a message about the file's *contents*, which is
the wrong story entirely.

Observed in the E2E suite at five Playwright workers: one import-wizard test out
of sixty-five failed with "Error reading CSV file: [Errno 2] No such file or
directory", timestamped to the millisecond of a neighbour's "Moved file" log line.

``can_parse`` is where the story starts and where it was half-cured: the runtime
calls it after resolving the path and before handing that path to ``parse``. The
retry was fitted to ``parse`` alone, so the guard two lines above kept answering
"this plugin cannot read your file" about files it reads fine.

When the guard does refuse, it says why if the plugin can tell (workstream L,
step G.5): see the section «THE REFUSAL SAYS WHY».

A move also races the detection of a file's plugins, which step 5 of workstream L
(item 8) runs again on read when the plugin catalogue changed, and every metadata
write of a broker now takes that broker's lock: see the last section of this file.
"""

import json
import subprocess
import sys
import threading
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pytest

from backend.app.config import get_version
from backend.app.schemas.brim import BRIMCombinedTable, BRIMDerivedRef, BRIMFileInfo, BRIMFileStatus, BRIMParseOutput
from backend.app.services import brim_provider


class _MovingPlugin:
    """A plugin that reads the path it is given, after the file has moved away."""

    plugin_version = "1.0.0"

    def __init__(self, file_id: str, move: bool = True):
        self.file_id = file_id
        self.move = move
        self.paths_read: list[Path] = []

    def can_parse(self, file_path: Path) -> bool:
        if self.move:
            brim_provider.move_to_parsed(self.file_id)
            self.move = False  # only the first caller wins the transition
        return True

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        self.paths_read.append(file_path)
        file_path.read_text()  # the real failure surface: ENOENT if it moved
        return BRIMParseOutput(transactions=[], extracted_assets={})


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(brim_provider, "get_broker_reports_dir", lambda: tmp_path)
    return tmp_path


def _upload(content: bytes = b"date,amount\n2026-01-01,10\n"):
    return brim_provider.save_uploaded_file(content, "generic_simple.csv", user_id=1, broker_id=1)


def test_parse_survives_the_file_moving_between_resolution_and_read(store, monkeypatch):
    info = _upload()
    plugin = _MovingPlugin(info.file_id)
    monkeypatch.setattr(brim_provider.BRIMProviderRegistry, "get_provider_instance", lambda code: plugin)

    output = brim_provider.parse_file(info.file_id, "broker_generic_csv", broker_id=1)

    assert output.transactions == []
    assert len(plugin.paths_read) == 2, "expected one failed read at the old path and one retry"
    assert plugin.paths_read[0].parent.name == "broker_1"
    assert plugin.paths_read[0].parent.parent.name == BRIMFileStatus.UPLOADED.value
    assert plugin.paths_read[1].parent.parent.name == BRIMFileStatus.PARSED.value


def test_a_read_error_on_a_file_that_did_not_move_is_not_retried(store, monkeypatch):
    """The retry must not launder a genuine failure into a second attempt."""
    info = _upload()
    plugin = _MovingPlugin(info.file_id, move=False)

    def exploding_parse(file_path, broker_id):
        plugin.paths_read.append(file_path)
        raise ValueError("genuinely malformed")

    plugin.parse = exploding_parse
    monkeypatch.setattr(brim_provider.BRIMProviderRegistry, "get_provider_instance", lambda code: plugin)

    with pytest.raises(ValueError, match="genuinely malformed"):
        brim_provider.parse_file(info.file_id, "broker_generic_csv", broker_id=1)
    assert len(plugin.paths_read) == 1


def test_get_file_path_finds_a_file_whose_metadata_still_says_uploaded(store):
    """_move_file renames the data first and rewrites the sidecar after.

    A reader arriving inside that window computes the folder from a status that
    is already stale. Deriving the address from the status is a shortcut; the
    file itself is the fact, so the lookup falls back to a scan.
    """
    info = _upload()
    ext = ".csv"
    uploaded = store / BRIMFileStatus.UPLOADED.value / "broker_1"
    parsed = store / BRIMFileStatus.PARSED.value / "broker_1"
    parsed.mkdir(parents=True, exist_ok=True)
    (uploaded / f"{info.file_id}{ext}").rename(parsed / f"{info.file_id}{ext}")
    # sidecar deliberately left behind, still saying "uploaded"

    found = brim_provider.get_file_path(info.file_id)

    assert found is not None
    assert found == parsed / f"{info.file_id}{ext}"


class _HonestPlugin:
    """A plugin whose ``can_parse`` answers about the file it is actually given.

    Every shipped plugin reads the file to decide, so a path that moved makes the
    guard answer ``False`` — not because the plugin cannot read this format, but
    because there is nothing at that address any more.
    """

    plugin_version = "1.0.0"

    def __init__(self, mover: str | None = None):
        self.mover = mover
        self.checked: list[Path] = []
        self.paths_read: list[Path] = []

    def can_parse(self, file_path: Path) -> bool:
        self.checked.append(file_path)
        if self.mover:
            brim_provider.move_to_parsed(self.mover)
            self.mover = None  # only the first caller wins the transition
        return file_path.exists()

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        self.paths_read.append(file_path)
        file_path.read_text()
        return BRIMParseOutput(transactions=[], extracted_assets={})


def test_can_parse_guard_survives_the_file_moving_before_the_check(store, monkeypatch):
    """The guard loses the same race as the parse, and needs the same cure.

    A neighbour's parse renames the file between our path resolution and our
    ``can_parse`` call. The guard then answers ``False`` about a stale address and
    the user is told "this plugin cannot parse your file" — about a file the plugin
    parses perfectly well two lines later.
    """
    info = _upload()
    plugin = _HonestPlugin(mover=info.file_id)
    monkeypatch.setattr(brim_provider.BRIMProviderRegistry, "get_provider_instance", lambda code: plugin)

    output = brim_provider.parse_file(info.file_id, "broker_generic_csv", broker_id=1)

    assert output.transactions == []
    assert len(plugin.checked) == 2, "expected one check at the stale path and one at the new one"
    assert plugin.checked[0].parent.parent.name == BRIMFileStatus.UPLOADED.value
    assert plugin.checked[1].parent.parent.name == BRIMFileStatus.PARSED.value
    # and the parse must be handed the relocated path, not the stale one it was resolved with
    assert plugin.paths_read == [plugin.checked[1]]


def test_a_plugin_that_genuinely_cannot_read_the_format_still_fails(store, monkeypatch):
    """The retry must not turn "wrong format" into a silent success either."""
    info = _upload()
    plugin = _HonestPlugin()
    plugin.can_parse = lambda file_path: False  # the file is there; the plugin just says no
    monkeypatch.setattr(brim_provider.BRIMProviderRegistry, "get_provider_instance", lambda code: plugin)

    with pytest.raises(ValueError, match="cannot parse file"):
        brim_provider.parse_file(info.file_id, "broker_generic_csv", broker_id=1)
    assert plugin.paths_read == []


def test_relocated_path_reports_none_when_the_file_never_moved(store):
    """``None`` is the signal that the caller's failure was genuine."""
    info = _upload()
    path = brim_provider.get_file_path(info.file_id)
    assert path is not None

    assert brim_provider._relocated_path(info.file_id, path) is None

    brim_provider.move_to_parsed(info.file_id)
    moved = brim_provider._relocated_path(info.file_id, path)
    assert moved is not None
    assert moved.parent.parent.name == BRIMFileStatus.PARSED.value

    assert brim_provider._relocated_path("does-not-exist", path) is None


# =============================================================================
# THE REFUSAL SAYS WHY (workstream L, step G.5)
# =============================================================================
#
# The developer's decision, verbatim: «Correggi dentro G con il metodo opzionale (Consigliato)».
# When the guard refuses a file, its message is ``Plugin '{code}' cannot parse file '{name}'``,
# followed by ``: {reason}`` when the plugin says why: ``BRIMProvider.cannot_parse_reason``, an
# optional method that the guard reads with ``getattr`` and asks only after ``can_parse`` answered
# False, about the path it checked last (the relocated one when the file moved). ``None`` or an
# empty sentence adds nothing, not even the colon. A duck-typed plugin without the method, or a
# method that raises, leaves the plain message: always this ``ValueError``, never another exception.
# ``{name}`` is the stored file's name, ``{file_id}{ext}``, which G.5 does not change.

GENERIC_CSV_CODE = "broker_generic_csv"


def _plain_refusal(stored: Path) -> str:
    """The guard's message when the plugin has nothing to add, about the stored file ``stored``."""
    return f"Plugin '{GENERIC_CSV_CODE}' cannot parse file '{stored.name}'"


class _RefusingPlugin:
    """A plugin that refuses every file, and answers ``cannot_parse_reason`` with ``reason``.

    ``reason`` is a sentence or ``None``, a callable of the path, or an exception to raise. The
    paths the guard checks and the paths it asks the reason about are recorded, so a test can tell
    whether the guard asked, and where. ``mover`` as in ``_HonestPlugin``: the first check moves
    that file uploaded → parsed, the way a neighbour's parse would.
    """

    plugin_version = "1.0.0"

    def __init__(self, reason=None, mover: str | None = None):
        self.reason = reason
        self.mover = mover
        self.checked: list[Path] = []
        self.reasons_asked: list[Path] = []
        self.paths_read: list[Path] = []

    def can_parse(self, file_path: Path) -> bool:
        self.checked.append(file_path)
        if self.mover:
            brim_provider.move_to_parsed(self.mover)
            self.mover = None  # only the first caller wins the transition
        return False

    def cannot_parse_reason(self, file_path: Path):
        self.reasons_asked.append(file_path)
        if isinstance(self.reason, BaseException):
            raise self.reason
        return self.reason(file_path) if callable(self.reason) else self.reason

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        self.paths_read.append(file_path)
        return BRIMParseOutput(transactions=[], extracted_assets={})


def _refusal(file_id: str, plugin, monkeypatch) -> ValueError:
    """Parse ``file_id`` with ``plugin`` standing in for the generic CSV; the ``ValueError`` the guard must raise."""
    monkeypatch.setattr(brim_provider.BRIMProviderRegistry, "get_provider_instance", lambda code: plugin)
    with pytest.raises(ValueError) as refusal:
        brim_provider.parse_file(file_id, GENERIC_CSV_CODE, broker_id=1)
    return refusal.value


def test_the_refusal_says_why_when_the_plugin_knows(store, monkeypatch):
    info = _upload()
    stored = brim_provider.get_file_path(info.file_id)
    plugin = _RefusingPlugin(reason="some reason")

    refusal = _refusal(info.file_id, plugin, monkeypatch)

    assert str(refusal) == f"{_plain_refusal(stored)}: some reason"
    assert plugin.reasons_asked == [stored], "the reason is asked once, about the file the guard checked"
    assert plugin.paths_read == []


@pytest.mark.parametrize("reason", [None, ""], ids=["none", "empty-sentence"])
def test_the_refusal_stays_plain_when_the_plugin_has_nothing_to_add(store, monkeypatch, reason):
    """No colon, nothing appended, so a stray ``": "`` fails — and the guard did ask."""
    info = _upload()
    stored = brim_provider.get_file_path(info.file_id)
    plugin = _RefusingPlugin(reason=reason)

    refusal = _refusal(info.file_id, plugin, monkeypatch)

    assert str(refusal) == _plain_refusal(stored)
    assert plugin.reasons_asked == [stored], "the guard never asked the plugin why it refuses the file"


def test_a_plugin_without_the_method_keeps_the_plain_refusal(store, monkeypatch):
    """A guard, green before G.5 too: the method is read with ``getattr``, never an ``AttributeError``.

    ``test_a_plugin_that_genuinely_cannot_read_the_format_still_fails`` matches a fragment of the
    message; this pins all of it, so a stray suffix for a plugin without the method fails.
    """
    info = _upload()
    stored = brim_provider.get_file_path(info.file_id)
    plugin = _HonestPlugin()
    plugin.can_parse = lambda file_path: False
    assert not hasattr(plugin, "cannot_parse_reason"), "premise: this double predates G.5"

    refusal = _refusal(info.file_id, plugin, monkeypatch)

    assert str(refusal) == _plain_refusal(stored)


@pytest.mark.parametrize(
    "failure",
    [RuntimeError("the reason itself failed"), ValueError("the reason itself failed")],
    ids=["runtime-error", "value-error"],
)
def test_a_reason_that_raises_leaves_the_plain_refusal(store, monkeypatch, failure):
    """The guard logs the failure and ignores it: the plain ``ValueError``, never the method's exception — not even its own ``ValueError``."""
    info = _upload()
    stored = brim_provider.get_file_path(info.file_id)
    plugin = _RefusingPlugin(reason=failure)

    refusal = _refusal(info.file_id, plugin, monkeypatch)

    assert str(refusal) == _plain_refusal(stored)
    assert plugin.reasons_asked == [stored], "the guard never asked the plugin why it refuses the file"


def test_the_reason_is_asked_where_the_guard_looked_last(store, monkeypatch):
    """The file moves uploaded → parsed under the check, and the plugin refuses it at both addresses: the reason comes from the relocated one."""
    info = _upload()
    stored = brim_provider.get_file_path(info.file_id)
    plugin = _RefusingPlugin(reason=lambda file_path: f"refused in {file_path.parent.parent.name}", mover=info.file_id)

    refusal = _refusal(info.file_id, plugin, monkeypatch)

    assert len(plugin.checked) == 2, "premise: the guard checked the stale path, then the relocated one"
    stale, relocated = plugin.checked
    assert (stale.parent.parent.name, relocated.parent.parent.name) == (BRIMFileStatus.UPLOADED.value, BRIMFileStatus.PARSED.value), "premise: the file moved uploaded → parsed under the check"
    assert str(refusal) == f"{_plain_refusal(stored)}: refused in {BRIMFileStatus.PARSED.value}"
    assert plugin.reasons_asked == [relocated]


def test_the_generic_csv_names_the_required_columns_a_file_misses(store):
    """The real plugin through the guard: an uploaded CSV whose header is ``amount,description`` names neither ``date`` nor ``type``."""
    info = _upload(b"amount,description\n10,first\n20,second\n")
    assert GENERIC_CSV_CODE not in info.compatible_plugins, f"premise: the generic CSV does not offer itself for this file: {info.compatible_plugins}"

    with pytest.raises(ValueError) as refusal:
        brim_provider.parse_file(info.file_id, GENERIC_CSV_CODE, broker_id=1)

    message = str(refusal.value)
    assert message.startswith(f"Plugin '{GENERIC_CSV_CODE}' cannot parse file '"), message
    assert message.endswith("': required columns 'date' and 'type' not found in the CSV header"), f"the refusal does not say which columns are missing: {message!r}"


# =============================================================================
# RE-DETECTION AND THE BROKER LOCK (workstream L, step 5, item 8)
# =============================================================================
#
# Plan: plan-phase00BrimDanskeBankStep5PluginRedetection.prompt.md, §0, §2 and §4. The developer's choice, verbatim:
# «A — rilevare di nuovo quando i plugin cambiano (Consigliata)», then «Approvo le raccomandazioni (Consigliato)»: the
# detection is saved (D1, A-persist), its signature is the app version (D2), its one-off cost is accepted (D3). Until
# now ``compatible_plugins`` was computed once, at upload, and trusted for ever: a file uploaded before a plugin that
# reads it was added or changed kept the list of the catalogue it was uploaded with (``[]`` for a Danske export that
# catalogue did not read) and was never offered that plugin. The sidecars here model a file detected before item 8: no
# ``plugins_signature`` and no plugin, every other key as today's upload writes it. They are not 1.1.0's: 1.1.0 recorded
# no ``batch_id`` either, so its uploads are detected again but join no set (guarded in test_brim_report_sets.py,
# ``TestDanskePairUploadedWith1_1_0``). The contract pinned here:
#
# - ``detection_signature()`` is the signature of the plugin catalogue, the app version; the module looks it up at call
#   time, so a test pins it with ``monkeypatch``;
# - the upload records it in the sidecar, ``plugins_signature``, next to ``compatible_plugins``;
# - a read (``get_file_info``, ``list_files``) of an original whose sidecar has no signature, or another one, detects
#   again with ``BRIMProviderRegistry.get_compatible_plugins(<data file>)``, returns the new list and saves it with the
#   current signature: under the broker lock, only if the sidecar is still where it was read and still old, and
#   changing those two fields only. A combined file is never detected again; a missing data file keeps the stored list
#   and writes nothing; under the current signature nothing is detected;
# - ``_broker_metadata_lock(broker_id)``: per broker, re-entrant on its thread, exclusive across processes through
#   ``fcntl.flock`` on ``<broker reports>/.locks/broker_<id>.lock`` (``broker_none.lock`` without a broker), released
#   on exceptions, and taken by every metadata write of the broker.
#
# The tests that need the signature pin it with ``raising=False``: each fails on the behaviour it pins, not on the
# missing name, which ``test_the_detection_signature_is_the_app_version`` pins alone. Every wait is bounded: a
# regression fails here, it never hangs the suite.

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "app" / "services" / "brim_providers" / "sample_reports"
DANSKE_CODE = "broker_danske_bank"
DANSKE_CASH = "danske_bank-cash.csv"
CURRENT_SIGNATURE = "plugins-signature-current"
OLD_SIGNATURE = "plugins-signature-of-an-older-version"
READS = ("get_file_info", "list_files")
# Read by no plugin of today's catalogue: since step G the generic CSV wants a date and a type column.
UNREADABLE_CSV = b"Amount;Description\n10;first\n20;second\n"
COMBINED_TABLE = BRIMCombinedTable(headers=["lf_row_kind", "lf_source", "amount"], rows=[["standalone", "cash:2", "-115"]], summary={"rows": 1})

# Every wait for something that must happen is bounded by this.
_WAIT_SECONDS = 30.0
# How long a write is given to show that it does NOT wait for a broker lock another thread holds. It only bounds the
# chance the defect gets to show itself (an unguarded write of a small sidecar takes milliseconds); behind a correct
# lock the write is parked, the grace runs out and the lock is released whatever the value. Paid on the green path only.
_BLOCKED_GRACE_SECONDS = 1.0
# How long a concurrent write is given while the detection is parked: it returns at once when the detection computes
# outside the lock, as the plan says; an implementation computing under the lock makes it wait for the release instead.
_WRITER_GRACE_SECONDS = 2.0

# Run in ANOTHER PROCESS: can it take the lock file now, without waiting? Exit 0 free, 3 held, 4 no such file.
_PROBE_FLOCK = """
import fcntl, sys
try:
    handle = open(sys.argv[1], "rb")
except FileNotFoundError:
    sys.exit(4)
with handle:
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit(3)
    fcntl.flock(handle, fcntl.LOCK_UN)
"""
_PROBE_ANSWERS = {0: "free", 3: "held", 4: "no lock file"}


def _pin_signature(monkeypatch, signature: str = CURRENT_SIGNATURE) -> None:
    """The signature of today's catalogue, for this test (``raising=False``: see the section header)."""
    monkeypatch.setattr(brim_provider, "detection_signature", lambda: signature, raising=False)


def _upload_danske_cash() -> BRIMFileInfo:
    """The synthetic Danske cash statement, uploaded on broker 1 through the real ``save_uploaded_file``."""
    return brim_provider.save_uploaded_file((SAMPLE_DIR / DANSKE_CASH).read_bytes(), DANSKE_CASH, user_id=1, broker_id=1)


def _sidecar_path(store: Path, file_id: str, status: BRIMFileStatus = BRIMFileStatus.UPLOADED) -> Path:
    return store / status.value / "broker_1" / f"{file_id}.json"


def _stored(store: Path, file_id: str, status: BRIMFileStatus = BRIMFileStatus.UPLOADED) -> Dict[str, Any]:
    """The raw sidecar of broker 1's file, as it is on disk now."""
    return json.loads(_sidecar_path(store, file_id, status).read_text())


def _rewrite_sidecar(path: Path, *, drop: tuple = (), **changes: Any) -> None:
    """Rewrite a sidecar on disk the way an older version, or another writer, left it."""
    metadata = json.loads(path.read_text())
    for key in drop:
        metadata.pop(key, None)
    metadata.update(changes)
    path.write_text(json.dumps(metadata, indent=2))


def _as_detected_before_item_8(path: Path) -> None:
    """The sidecar of a Danske export as a build before item 8 left it, its catalogue not reading the export: no ``plugins_signature``, and no plugin.

    Every other key stays as today's upload wrote it: not 1.1.0's sidecar (see the section header).
    """
    _rewrite_sidecar(path, drop=("plugins_signature",), compatible_plugins=[])


def _sidecars(store: Path, file_id: str) -> List[Path]:
    """Every sidecar of ``file_id``, in every status folder and every broker subfolder."""
    return [path for status in BRIMFileStatus for path in sorted((store / status.value).glob(f"**/{file_id}.json"))]


def _data_files(store: Path, file_id: str) -> List[Path]:
    """Every data file of the synthetic cash statement ``file_id``, wherever it lies."""
    return [path for status in BRIMFileStatus for path in sorted((store / status.value).glob(f"**/{file_id}.csv"))]


def _resolved(paths: List[Path]) -> List[Path]:
    return [Path(path).resolve() for path in paths]


def _read(how: str, file_id: str) -> BRIMFileInfo:
    """Broker 1's file as ``get_file_info`` or ``list_files`` reads it."""
    if how == "get_file_info":
        info = brim_provider.get_file_info(file_id)
        assert info is not None, f"get_file_info({file_id!r}) is None"
        return info
    listed = [info for info in brim_provider.list_files(broker_ids=[1]) if info.file_id == file_id]
    assert len(listed) == 1, f"{file_id} listed {len(listed)} times"
    return listed[0]


def _save_combined(member: BRIMFileInfo) -> BRIMFileInfo:
    """A combined file built from ``member`` by the Danske plugin, stored by the real ``save_combined_file``."""
    ref = BRIMDerivedRef(file_id=member.file_id, role="cash", filename=member.filename)
    return brim_provider.save_combined_file(broker_id=1, plugin_code=DANSKE_CODE, plugin_version="1.0.0", members=[ref], table=COMBINED_TABLE, filename="Danske Bank — combined")


class _DetectionGate:
    """Parks one thread inside the detection, after it computed and before it saves: the window a concurrent write races."""

    def __init__(self) -> None:
        self.parked: Optional[threading.Thread] = None
        self.inside = threading.Event()
        self.progress = threading.Event()  # the parked thread is inside the detection, or its read returned
        self.release = threading.Event()


class _DetectionSpy:
    """Stands in for ``BRIMProviderRegistry.get_compatible_plugins``: records every path it is asked about and answers with the real catalogue."""

    def __init__(self, real: Callable[[Path], List[str]], gate: Optional[_DetectionGate] = None) -> None:
        self._real = real
        self._gate = gate
        self._lock = threading.Lock()
        self.paths: List[Path] = []

    def __call__(self, file_path: Path) -> List[str]:
        with self._lock:
            self.paths.append(Path(file_path))
        compatible = self._real(file_path)
        gate = self._gate
        if gate is not None and threading.current_thread() is gate.parked:
            gate.inside.set()
            gate.progress.set()
            gate.release.wait(timeout=_WAIT_SECONDS)
        return compatible


def _spy_on_detection(monkeypatch, gate: Optional[_DetectionGate] = None) -> _DetectionSpy:
    """Install the spy after the test's own uploads (which detect too); ``monkeypatch`` puts the classmethod back."""
    spy = _DetectionSpy(brim_provider.BRIMProviderRegistry.get_compatible_plugins, gate)
    monkeypatch.setattr(brim_provider.BRIMProviderRegistry, "get_compatible_plugins", staticmethod(spy))
    return spy


class _Threaded:
    """One call on its own daemon thread, keeping what it returned or raised (as the V1 race tests do)."""

    def __init__(self, name: str, call: Callable[[], Any], on_exit: Optional[threading.Event] = None) -> None:
        self._call = call
        self._on_exit = on_exit
        self.result: Any = None
        self.error: Optional[Exception] = None
        self.trace = ""
        self.thread = threading.Thread(target=self._run, name=name, daemon=True)

    def _run(self) -> None:
        try:
            self.result = self._call()
        except Exception as exc:  # what the call raised is exactly what the test asserts on
            self.error = exc
            self.trace = traceback.format_exc()
        finally:
            if self._on_exit is not None:
                self._on_exit.set()

    def finish(self, hung: str) -> None:
        """Join with a bound: a stuck call fails the test instead of hanging the suite (the thread is a daemon)."""
        self.thread.join(timeout=_WAIT_SECONDS)
        assert not self.thread.is_alive(), f"{self.thread.name} still running after {_WAIT_SECONDS}s: {hung}"

    @property
    def outcome(self) -> tuple:
        if self.error is not None:
            return ("raised", f"{type(self.error).__name__}: {self.error}")
        return ("returned", self.result)


def _lock_file(store: Path, broker_id: Optional[int]) -> Path:
    """The contract's lock file of a broker: ``<broker reports>/.locks/broker_<id>.lock``."""
    return store / ".locks" / f"broker_{'none' if broker_id is None else broker_id}.lock"


def _probe(lock_file: Path) -> str:
    """Whether ANOTHER PROCESS can take ``lock_file`` right now, without waiting: "free", "held" or "no lock file"."""
    probe = subprocess.run([sys.executable, "-I", "-c", _PROBE_FLOCK, str(lock_file)], capture_output=True, text=True, timeout=_WAIT_SECONDS)
    assert probe.returncode in _PROBE_ANSWERS, f"the probe process failed ({probe.returncode}): {probe.stderr}"
    return _PROBE_ANSWERS[probe.returncode]


def _take_and_release(broker_id: Optional[int]) -> bool:
    with brim_provider._broker_metadata_lock(broker_id):
        return True


# ----------------------------------------------------------------------------- the signature and the detection


def test_the_detection_signature_is_the_app_version():
    """D2: the signature of the plugin catalogue is the app version, so every release (and every nightly commit) detects again."""
    signature = brim_provider.detection_signature()

    assert isinstance(signature, str) and signature, f"the signature is not a non-empty string: {signature!r}"
    assert signature == get_version()


def test_the_upload_records_the_signature_it_detected_with(store, monkeypatch):
    """The sidecar carries ``plugins_signature`` next to ``compatible_plugins``, and the next read trusts the upload's detection."""
    _pin_signature(monkeypatch)
    info = _upload_danske_cash()

    stored = _stored(store, info.file_id)

    assert stored["compatible_plugins"] == [DANSKE_CODE], f"premise: today's catalogue reads the sample as Danske only: {stored['compatible_plugins']}"
    assert stored.get("plugins_signature") == CURRENT_SIGNATURE, f"the upload does not record the signature of the catalogue it detected with: {sorted(stored)}"
    spy = _spy_on_detection(monkeypatch)
    assert brim_provider.get_file_info(info.file_id).compatible_plugins == [DANSKE_CODE]
    assert spy.paths == [], "a read right after the upload detected the plugins again"


@pytest.mark.parametrize("how", READS)
def test_a_sidecar_without_the_detection_signature_is_detected_again_and_saved(store, monkeypatch, how):
    """A Danske export detected before item 8 (no signature, no plugin): the read gives Danske, and the sidecar keeps it with today's signature."""
    _pin_signature(monkeypatch)
    info = _upload_danske_cash()
    _as_detected_before_item_8(_sidecar_path(store, info.file_id))

    read = _read(how, info.file_id)

    assert read.compatible_plugins == [DANSKE_CODE], f"{how} still gives the plugins stored before item 8: {read.compatible_plugins}"
    stored = _stored(store, info.file_id)
    assert (stored["compatible_plugins"], stored.get("plugins_signature")) == ([DANSKE_CODE], CURRENT_SIGNATURE), "the detection is not saved with the current signature"


@pytest.mark.parametrize("status", [BRIMFileStatus.PARSED, BRIMFileStatus.FAILED], ids=lambda status: status.value)
def test_a_parsed_or_failed_file_is_detected_again_where_it_lies(store, monkeypatch, status):
    """Every original is detected again, a failed one too (plan §2.3: so it can be retried), on the data file beside its sidecar."""
    _pin_signature(monkeypatch)
    info = _upload_danske_cash()
    moved = brim_provider.move_to_parsed(info.file_id) if status == BRIMFileStatus.PARSED else brim_provider.move_to_failed(info.file_id, "synthetic failure")
    assert moved, f"premise: the file moved to {status.value}"
    sidecar = _sidecar_path(store, info.file_id, status)
    _as_detected_before_item_8(sidecar)
    spy = _spy_on_detection(monkeypatch)

    read = brim_provider.get_file_info(info.file_id)

    assert read is not None and read.status == status, f"premise: the file reads as {status.value}: {read}"
    assert read.compatible_plugins == [DANSKE_CODE], f"a {status.value} file still gives the plugins stored before item 8: {read.compatible_plugins}"
    assert _resolved(spy.paths) == _resolved([sidecar.with_suffix(".csv")]), f"the detection did not read the data file beside its sidecar: {spy.paths}"
    stored = _stored(store, info.file_id, status)
    assert (stored["compatible_plugins"], stored.get("plugins_signature"), stored["status"]) == ([DANSKE_CODE], CURRENT_SIGNATURE, status.value), f"the detection is not saved, with the current signature, beside the {status.value} file"


@pytest.mark.parametrize("how", READS)
def test_an_old_signature_drops_the_plugins_that_no_longer_read_the_file(store, monkeypatch, how):
    """What an older catalogue offered and today's does not (since step G the generic CSV wants a date and a type): the list empties."""
    _pin_signature(monkeypatch)
    info = brim_provider.save_uploaded_file(UNREADABLE_CSV, "amounts.csv", user_id=1, broker_id=1)
    sidecar = _sidecar_path(store, info.file_id)
    assert brim_provider.BRIMProviderRegistry.get_compatible_plugins(sidecar.with_suffix(".csv")) == [], "premise: no plugin of today's catalogue reads this CSV"
    _rewrite_sidecar(sidecar, plugins_signature=OLD_SIGNATURE, compatible_plugins=["broker_directa", "broker_generic_csv"])

    read = _read(how, info.file_id)

    assert read.compatible_plugins == [], f"{how} still offers what the old catalogue detected: {read.compatible_plugins}"
    stored = _stored(store, info.file_id)
    assert (stored["compatible_plugins"], stored.get("plugins_signature")) == ([], CURRENT_SIGNATURE), "the detection is not saved with the current signature"


def test_under_the_current_signature_nothing_is_detected_again(store, monkeypatch):
    """Guard: the stored list is trusted as it is, through both reads, and the sidecar is not touched.

    The stored list is deliberately wrong, so a detection would show in the result as well as in the spy.
    """
    _pin_signature(monkeypatch)
    info = _upload_danske_cash()
    sidecar = _sidecar_path(store, info.file_id)
    _rewrite_sidecar(sidecar, plugins_signature=CURRENT_SIGNATURE, compatible_plugins=["broker_directa"])
    before = sidecar.read_text()
    spy = _spy_on_detection(monkeypatch)

    reads = {how: _read(how, info.file_id).compatible_plugins for how in READS}

    assert reads == {how: ["broker_directa"] for how in READS}, f"the stored list was replaced under the current signature: {reads}"
    assert spy.paths == [], f"detected again under the current signature: {spy.paths}"
    assert sidecar.read_text() == before


@pytest.mark.parametrize("signature", [None, OLD_SIGNATURE], ids=["no-signature", "old-signature"])
def test_a_combined_file_is_never_detected_again(store, monkeypatch, signature):
    """Guard: a combined file is read by the plugin that built it, whatever its sidecar's signature."""
    _pin_signature(monkeypatch)
    combined = _save_combined(_upload_danske_cash())
    sidecar = _sidecar_path(store, combined.file_id)
    if signature is None:
        _rewrite_sidecar(sidecar, drop=("plugins_signature",))
    else:
        _rewrite_sidecar(sidecar, plugins_signature=signature)
    before = sidecar.read_text()
    spy = _spy_on_detection(monkeypatch)

    reads = {how: _read(how, combined.file_id).compatible_plugins for how in READS}

    assert reads == {how: [DANSKE_CODE] for how in READS}, f"a combined file was detected again: {reads}"
    assert spy.paths == [], f"a detection ran for a combined file or its member: {spy.paths}"
    assert sidecar.read_text() == before


def test_a_missing_data_file_keeps_the_stored_list_and_writes_nothing(store, monkeypatch):
    """Guard: with nothing to read, the stored list stays, the sidecar is not rewritten and the read does not fail."""
    _pin_signature(monkeypatch)
    info = _upload_danske_cash()
    sidecar = _sidecar_path(store, info.file_id)
    _rewrite_sidecar(sidecar, drop=("plugins_signature",), compatible_plugins=["broker_directa"])
    sidecar.with_suffix(".csv").unlink()
    before = sidecar.read_text()

    reads = {how: _read(how, info.file_id).compatible_plugins for how in READS}

    assert reads == {how: ["broker_directa"] for how in READS}, f"the stored list was replaced although the data file is gone: {reads}"
    assert sidecar.read_text() == before, "the sidecar was rewritten although its data file is gone"


def test_a_saved_detection_is_trusted_by_the_next_reads(store, monkeypatch):
    """Once per version (D1): the first read detects on the data file and saves; the next ones, through both reads, detect nothing."""
    _pin_signature(monkeypatch)
    info = _upload_danske_cash()
    sidecar = _sidecar_path(store, info.file_id)
    _as_detected_before_item_8(sidecar)
    data = sidecar.with_suffix(".csv")
    spy = _spy_on_detection(monkeypatch)

    first = brim_provider.get_file_info(info.file_id)
    detected = list(spy.paths)
    again = {how: _read(how, info.file_id).compatible_plugins for how in READS}

    assert _resolved(detected) == _resolved([data]), f"the first read did not detect the plugins again, once, on the data file: {detected}"
    assert _resolved(spy.paths) == _resolved([data]), f"a read after the detection detected again (it was not saved with the current signature): {spy.paths}"
    assert (first.compatible_plugins, again) == ([DANSKE_CODE], {how: [DANSKE_CODE] for how in READS})


# ----------------------------------------------------------------------------- a write while the detection computes


def _move_to_parsed(file_id: str) -> bool:
    return brim_provider._move_file(file_id, BRIMFileStatus.PARSED)


def _update_another_field(file_id: str) -> bool:
    return brim_provider._update_metadata(file_id, lambda metadata: metadata.update(lock_probe="kept"))


def _detect_meanwhile(file_id: str) -> bool:
    """Another worker saved its own detection first: the current signature, with a list told apart from the parked one."""
    return brim_provider._update_metadata(file_id, lambda metadata: metadata.update(plugins_signature=CURRENT_SIGNATURE, compatible_plugins=["broker_directa"]))


def _settled_after_the_move(store: Path, file_id: str) -> None:
    parsed = _sidecar_path(store, file_id, BRIMFileStatus.PARSED)
    sidecars = _sidecars(store, file_id)
    assert sidecars == [parsed], f"the detection saved its result where the file no longer is: {[str(path.relative_to(store)) for path in sidecars]}"
    assert _stored(store, file_id, BRIMFileStatus.PARSED)["status"] == BRIMFileStatus.PARSED.value
    assert _data_files(store, file_id) == [parsed.with_suffix(".csv")]


def _settled_after_the_update(store: Path, file_id: str) -> None:
    stored = _stored(store, file_id)
    assert stored.get("lock_probe") == "kept", "the detection saved the sidecar it had read, undoing a write made meanwhile: only its two fields may change"
    assert (stored["compatible_plugins"], stored.get("plugins_signature")) == ([DANSKE_CODE], CURRENT_SIGNATURE), "the detection is not saved over a write made meanwhile, though the signature was still old"


def _settled_after_the_other_detection(store: Path, file_id: str) -> None:
    stored = _stored(store, file_id)
    assert (stored["compatible_plugins"], stored.get("plugins_signature")) == (["broker_directa"], CURRENT_SIGNATURE), "the detection overwrote a sidecar that already carried the current signature"


CONCURRENT_WRITES = {
    "move-to-parsed": (_move_to_parsed, _settled_after_the_move),
    "update-another-field": (_update_another_field, _settled_after_the_update),
    "detected-meanwhile": (_detect_meanwhile, _settled_after_the_other_detection),
}


@pytest.mark.parametrize("write", list(CONCURRENT_WRITES))
def test_a_write_while_the_detection_computes_is_never_undone(store, monkeypatch, write):
    """The detection has read the sidecar and computes (outside the lock, the slow part) when a concurrent write lands.

    Saving, it re-reads under the broker lock: a sidecar that moved is not written back at its old address (no
    ``uploaded/`` copy resurrected beside the ``parsed/`` one), a field written meanwhile stays (only the list and the
    signature change), and a sidecar that already carries the current signature is left alone.
    """
    concurrent, settled = CONCURRENT_WRITES[write]
    _pin_signature(monkeypatch)
    info = _upload_danske_cash()
    _as_detected_before_item_8(_sidecar_path(store, info.file_id))
    gate = _DetectionGate()
    _spy_on_detection(monkeypatch, gate)
    reader = _Threaded("detection-reader", lambda: brim_provider.get_file_info(info.file_id), on_exit=gate.progress)
    writer = _Threaded(f"concurrent-{write}", lambda: concurrent(info.file_id))
    gate.parked = reader.thread
    reader.thread.start()
    try:
        assert gate.progress.wait(_WAIT_SECONDS), "the read neither detected the plugins again nor returned"
        if gate.inside.is_set():
            writer.thread.start()
            writer.thread.join(timeout=_WRITER_GRACE_SECONDS)
    finally:
        gate.release.set()
    reader.finish("the read hung after the detection was released")

    assert gate.inside.is_set(), "the read returned without detecting the plugins again: a sidecar without plugins_signature is still trusted as it is"
    writer.finish(f"the concurrent {write} hung")
    assert writer.outcome == ("returned", True), f"the concurrent {write} failed: {writer.outcome} {writer.trace}"
    assert reader.error is None, f"the detection failed after the concurrent {write}: {reader.trace}"
    settled(store, info.file_id)


# ----------------------------------------------------------------------------- the broker lock


def test_the_broker_lock_excludes_another_process_until_it_is_released(store):
    """The coordinator's requirement: with several workers, a parse moving a file in one process while another rewrites its old sidecar would resurrect it."""
    broker_lock = brim_provider._broker_metadata_lock
    lock_file = _lock_file(store, 1)

    with broker_lock(1):
        exists = lock_file.is_file()
        while_held = _probe(lock_file)
    after = _probe(lock_file)

    assert exists, f"no lock file at {lock_file.relative_to(store)}, the contract's path"
    assert while_held == "held", f"another process could take broker 1's lock while this one held it: {while_held}"
    assert after == "free", f"another process still cannot take broker 1's lock after the block: {after}"


def test_the_broker_lock_is_per_broker(store):
    """Holding broker 1's lock, another thread takes broker 2's at once, and so does another process."""
    broker_lock = brim_provider._broker_metadata_lock
    with broker_lock(2):
        assert _lock_file(store, 2).is_file(), "premise: broker 2's lock file exists once its lock was taken"
    other = _Threaded("broker-2-while-broker-1-is-held", lambda: _take_and_release(2))

    with broker_lock(1):
        other.thread.start()
        other.thread.join(timeout=_WAIT_SECONDS)
        took_it_while_held = not other.thread.is_alive()
        probes = {"broker_1": _probe(_lock_file(store, 1)), "broker_2": _probe(_lock_file(store, 2))}

    other.finish("taking broker 2's lock hung even after broker 1's was released")
    assert took_it_while_held, f"another thread waited {_WAIT_SECONDS}s for broker 2's lock while broker 1's was held, and took it only after the release: the lock is not per broker"
    assert other.outcome == ("returned", True), f"taking broker 2's lock failed: {other.outcome} {other.trace}"
    assert probes == {"broker_1": "held", "broker_2": "free"}, f"another process sees the brokers' locks as {probes}"


def test_an_exception_inside_the_broker_lock_releases_it(store):
    """The lock is released when the block raises: for another process and for another thread of this one."""
    broker_lock = brim_provider._broker_metadata_lock
    with pytest.raises(RuntimeError, match="raised inside the broker lock"):
        with broker_lock(1):
            while_held = _probe(_lock_file(store, 1))
            raise RuntimeError("raised inside the broker lock")
    after = _probe(_lock_file(store, 1))
    other = _Threaded("broker-1-after-the-exception", lambda: _take_and_release(1))
    other.thread.start()
    other.finish("another thread still waits for broker 1's lock after an exception left the block")

    assert while_held == "held", f"premise: another process could take broker 1's lock while it was held: {while_held}"
    assert after == "free", f"another process still cannot take broker 1's lock after an exception left the block: {after}"
    assert other.outcome == ("returned", True)


def test_the_broker_lock_is_reentrant_and_held_until_the_outer_block_ends(store):
    """A write that calls another write takes the lock again on the same thread: no deadlock, and the file lock stays held until the outer block ends.

    Plan §7: ``flock`` is taken once per nesting level, with a per-thread counter. Releasing it when the inner block
    ends would leave the rest of the outer one unprotected against another process.
    """
    broker_lock = brim_provider._broker_metadata_lock
    lock_file = _lock_file(store, 1)

    def nested() -> tuple:
        with broker_lock(1):
            with broker_lock(1):
                inside_both = _probe(lock_file)
            after_the_inner = _probe(lock_file)
        return inside_both, after_the_inner, _probe(lock_file)

    call = _Threaded("nested-broker-lock", nested)
    call.thread.start()
    call.finish("taking broker 1's lock again on the thread that holds it deadlocked")

    assert call.outcome == ("returned", ("held", "held", "free")), f"another process's view (inside both blocks, after the inner one, after the outer one): {call.outcome}"


def test_files_without_a_broker_share_the_broker_none_lock(store):
    """``_broker_metadata_lock(None)`` locks ``broker_none.lock``, the files uploaded without a broker."""
    broker_lock = brim_provider._broker_metadata_lock
    lock_file = _lock_file(store, None)

    with broker_lock(None):
        while_held = _probe(lock_file)
    after = _probe(lock_file)

    assert (while_held, after) == ("held", "free"), f"another process's view of {lock_file.relative_to(store)} (while held, after): {(while_held, after)}"


# ----------------------------------------------------------------------------- every metadata write takes the lock


def _writes_upload(store: Path):
    _upload_danske_cash()  # the broker's folders exist and already hold a file

    def landed(result: BRIMFileInfo) -> None:
        assert _sidecar_path(store, result.file_id).is_file()

    return (lambda: brim_provider.save_uploaded_file(UNREADABLE_CSV, "probe.csv", user_id=1, broker_id=1)), landed


def _writes_update(store: Path):
    info = _upload_danske_cash()

    def landed(result: bool) -> None:
        assert result is True
        assert _stored(store, info.file_id).get("lock_probe") == "written"

    return (lambda: brim_provider._update_metadata(info.file_id, lambda metadata: metadata.update(lock_probe="written"))), landed


def _writes_combined(store: Path):
    member = _upload_danske_cash()

    def landed(result: BRIMFileInfo) -> None:
        assert _sidecar_path(store, result.file_id).is_file()
        assert result.file_id in _stored(store, member.file_id).get("combined_into", [])

    return (lambda: _save_combined(member)), landed


def _writes_parse_result(store: Path):
    info = _upload_danske_cash()
    cached = {"transactions": [], "lock_probe": "written"}

    def landed(result: bool) -> None:
        assert result is True
        assert _stored(store, info.file_id)["last_parse_result"] == cached

    return (lambda: brim_provider.save_parse_result(info.file_id, cached)), landed


def _writes_move(store: Path):
    info = _upload_danske_cash()

    def landed(result: bool) -> None:
        assert result is True
        assert _sidecars(store, info.file_id) == [_sidecar_path(store, info.file_id, BRIMFileStatus.PARSED)]

    return (lambda: brim_provider._move_file(info.file_id, BRIMFileStatus.PARSED)), landed


def _writes_delete(store: Path):
    info = _upload_danske_cash()

    def landed(result: bool) -> None:
        assert result is True
        assert _sidecars(store, info.file_id) == []

    return (lambda: brim_provider.delete_file(info.file_id)), landed


def _writes_detection(store: Path):
    info = _upload_danske_cash()
    _as_detected_before_item_8(_sidecar_path(store, info.file_id))

    def landed(result: Optional[BRIMFileInfo]) -> None:
        assert result is not None and result.compatible_plugins == [DANSKE_CODE], f"the read does not give the detected plugins: {result}"
        stored = _stored(store, info.file_id)
        assert (stored["compatible_plugins"], stored.get("plugins_signature")) == ([DANSKE_CODE], CURRENT_SIGNATURE), "the detection is not saved once the lock was released"

    return (lambda: brim_provider.get_file_info(info.file_id)), landed


# The writers of plan §2.7, each with a check that its write landed once the lock was released.
LOCKED_WRITES = {
    "save_uploaded_file": _writes_upload,
    "_update_metadata": _writes_update,
    "save_combined_file": _writes_combined,
    "save_parse_result": _writes_parse_result,
    "_move_file": _writes_move,
    "delete_file": _writes_delete,
    "the-detection-save": _writes_detection,
}


def _broker_sidecars(store: Path, broker_id: int) -> Dict[str, Optional[str]]:
    """Every sidecar of the broker with its content; ``None`` for one removed between the listing and the read."""
    snapshot: Dict[str, Optional[str]] = {}
    for path in sorted(store.glob(f"*/broker_{broker_id}/*.json")):
        try:
            snapshot[str(path.relative_to(store))] = path.read_text()
        except FileNotFoundError:  # removed by a write in flight: that write is the evidence
            snapshot[str(path.relative_to(store))] = None
    return snapshot


@pytest.mark.parametrize("write", list(LOCKED_WRITES))
def test_a_metadata_write_waits_for_the_broker_lock(store, monkeypatch, write):
    """While another thread holds broker 1's lock, the write neither returns nor changes a sidecar of broker 1; released, it lands."""
    _pin_signature(monkeypatch)
    act, landed = LOCKED_WRITES[write](store)
    broker_lock = brim_provider._broker_metadata_lock
    call = _Threaded(f"{write}-while-the-lock-is-held", act)
    before = _broker_sidecars(store, 1)

    with broker_lock(1):
        call.thread.start()
        call.thread.join(timeout=_BLOCKED_GRACE_SECONDS)
        returned_while_held = not call.thread.is_alive()
        changed_while_held = _broker_sidecars(store, 1) != before
    call.finish(f"{write} never completed once broker 1's lock was released")

    assert not (returned_while_held or changed_while_held), f"{write} did not wait for broker 1's lock, held by another thread (returned: {returned_while_held}, sidecars changed: {changed_while_held})"
    assert call.error is None, f"{write} failed once the lock was released: {call.trace}"
    landed(call.result)
