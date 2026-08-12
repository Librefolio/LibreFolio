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
"""

from __future__ import annotations

import pickle
import uuid
from pathlib import Path

import pytest

from backend.app.schemas.brim import BRIMParseOutput
from backend.app.services import brim_parse_pool, brim_provider
from backend.app.services.brim_provider import BRIMParseError, delete_file, get_file_path, save_uploaded_file

SAMPLE = Path(__file__).resolve().parents[2] / "app" / "services" / "brim_providers" / "sample_reports" / "schwab-export.csv"


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


def test_worker_count_is_bounded():
    """Never more workers than cores, never more than the cap, never zero."""
    assert 1 <= brim_parse_pool._worker_count() <= brim_parse_pool.MAX_WORKERS
