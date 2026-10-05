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
step G.5): see the last section of this file.
"""

from pathlib import Path

import pytest

from backend.app.schemas.brim import BRIMFileStatus, BRIMParseOutput
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
