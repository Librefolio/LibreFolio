"""Parsing a file that moves underfoot.

A successful parse transitions the file uploaded → parsed, and that transition is
a physical rename. Two clients parsing the same file at once therefore race: the
second resolved its path before the rename and reads it after, so it fails on a
path that no longer exists — with a message about the file's *contents*, which is
the wrong story entirely.

Observed in the E2E suite at five Playwright workers: one import-wizard test out
of sixty-five failed with "Error reading CSV file: [Errno 2] No such file or
directory", timestamped to the millisecond of a neighbour's "Moved file" log line.

``can_parse`` is the injection point because it is the real seam: the runtime
calls it after resolving the path and before handing that path to ``parse``.
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
