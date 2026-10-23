"""The 400 of a failed BRIM parse carries an object the import wizard translates, not an English sentence (lot W5-5, backlog C-70b).

Module under test: the parse endpoint of ``api/v1/brokers.py`` (``parse_file``), with ``services/brim/brim_parse_pool.py``
(``parse_file_offloaded``) and the guard of ``services/brim/brim_provider.py`` (``parse_file``) behind it. The contract:

1. **A plugin raised ``BRIMParseError(message, details={"code": …, "context": …})``**: HTTP 400, ``detail`` is
   ``{"code": "parse_failed", "message": "Parse error: <message>", "plugin_code", "plugin_name", "reason": {"code", "message", "context"}}``.
   ``plugin_name`` is the plugin's ``provider_name``, the code when the plugin is not registered. ``reason.code`` and
   ``reason.context`` come from ``details`` and are ``None`` and ``{}`` when the plugin gave none; ``reason.message`` is the
   error's own message.
2. **The parse guard refuses** (``can_parse`` is false): the same object, ``message`` is the guard's English sentence
   (``Plugin '<name>' cannot parse file '<file>'`` and the plugin's reason after a colon, when it has one), ``reason`` is the
   plugin's ``cannot_parse_detail`` (a ``BRIMRefusal``: code, message, context) — or no code, no message and no context when
   the plugin has nothing to say.
3. **Any other ``ValueError``** (an unknown plugin) keeps a plain string ``detail`` (400); ``FileNotFoundError`` stays 404.
4. **The file goes to ``failed`` with the English text as its stored ``error_message``** (the diagnostic, as before): the
   error's own message for a parse error, the guard's whole sentence for a refusal.

The real server runs in another process, so a plugin of the tests cannot be registered in it: these tests call the endpoint
function itself, with the plugin registered in this process (``_brim_settings_lab`` registers it for the length of a test) and
the pool given up (the thread fallback runs the same parent code and the same call). What a real plugin and a real HTTP round
trip answer is in ``test_api/test_brim_api.py`` (RS-G05, RS-C70-02, RS-C70-03). The access checks and the report-set guard are
put aside: they are not the subject.

Pure: the uploaded file lives under ``tmp_path`` (the reports directory is redirected); the plugins are registered for the
length of a test and taken out again; no database is reached (a plugin that declares no setting reads none).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar, Optional

import pytest
from fastapi import HTTPException

from backend.app.api.v1 import brokers as brokers_api
from backend.app.schemas.brim import BRIMParseOutput, BRIMParseRequest, BRIMRefusal
from backend.app.services.brim import brim_parse_pool, brim_provider
from backend.app.services.brim.brim_provider import BRIMParseError
from backend.test_scripts.test_services import _brim_settings_lab as brim_lab
from backend.test_scripts.test_utils import print_section, print_success

BROKER_ID = 5
UPLOADED_NAME = "generic_simple.csv"
DETAIL_KEYS = {"code", "message", "plugin_code", "plugin_name", "reason"}


# =============================================================================
# THE PLUGINS OF THE TESTS
# =============================================================================


class _Plugin(brim_lab.SettingsBrimPlugin):
    """A BRIM plugin of the tests that declares no setting; what it does is set by the class attributes of its subclasses."""

    settings_fields = ()
    code: ClassVar[str] = "test_brim_failure_detail"
    name: ClassVar[str] = "Failure detail plugin (TESTING ONLY)"
    accepts: ClassVar[bool] = True
    raises: ClassVar[Optional[BRIMParseError]] = None
    refusal: ClassVar[Optional[BRIMRefusal]] = None

    @property
    def provider_code(self) -> str:
        return self.code

    @property
    def provider_name(self) -> str:
        return self.name

    def can_parse(self, file_path: Path) -> bool:
        return self.accepts

    def cannot_parse_reason(self, file_path: Path) -> Optional[str]:
        return self.refusal.message if self.refusal else None

    def cannot_parse_detail(self, file_path: Path) -> Optional[BRIMRefusal]:
        return self.refusal

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        if self.raises is not None:
            raise self.raises
        return BRIMParseOutput(transactions=[], warnings=[], extracted_assets={})


class _CodedError(_Plugin):
    code = "test_failure_coded"
    name = "Coded Failure Plugin"
    raises = BRIMParseError("boom", details={"code": "test_code", "context": {"n": 2}})


class _UncodedError(_Plugin):
    code = "test_failure_uncoded"
    name = "Uncoded Failure Plugin"
    raises = BRIMParseError("it broke", details={"file": "x.csv", "line": 7})


class _CodedRefusal(_Plugin):
    code = "test_refusal_coded"
    name = "Coded Refusal Plugin"
    accepts = False
    refusal = BRIMRefusal(code="test_refusal", message="the test says no", context={"n": 3})


class _SilentRefusal(_Plugin):
    code = "test_refusal_silent"
    name = "Silent Refusal Plugin"
    accepts = False


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test mode (the plugins are ``test_only``), a data directory of this test, no settings database."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(brim_parse_pool, "_pool_disabled", True)


@pytest.fixture
def uploaded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """A file uploaded under ``tmp_path`` (the reports directory is redirected) as ``generic_simple.csv``: its id."""
    reports = tmp_path / "broker_reports"
    reports.mkdir()
    monkeypatch.setattr(brim_provider, "get_broker_reports_dir", lambda: reports)
    return brim_provider.save_uploaded_file(b"date,amount\n2026-01-01,10\n", UPLOADED_NAME, user_id=1, broker_id=BROKER_ID).file_id


@pytest.fixture(autouse=True)
def access_put_aside(monkeypatch: pytest.MonkeyPatch) -> None:
    """The access checks and the report-set guard answer yes: the parse is the subject."""

    async def access(*_args: Any, **_kwargs: Any) -> object:
        return object()

    async def editor(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(brokers_api, "_get_brim_file_with_access", access)
    monkeypatch.setattr(brokers_api, "_require_broker_editor", editor)
    monkeypatch.setattr(brokers_api, "_refuse_report_set_member", lambda _code, _info: None)


async def _parse(file_id: str, plugin_code: str) -> HTTPException:
    """Call the parse endpoint and return the ``HTTPException`` it raises; fail when it answers."""
    with pytest.raises(HTTPException) as raised:
        await brokers_api.parse_file(file_id, BRIMParseRequest(plugin_code=plugin_code, broker_id=BROKER_ID), SimpleNamespace(id=1), None)
    return raised.value


def _stored(file_id: str) -> tuple:
    """``(status, error_message)`` the file keeps."""
    info = brim_provider.get_file_info(file_id)
    assert info is not None, "premise: the file is still there"
    return str(getattr(info.status, "value", info.status)), info.error_message


# =============================================================================
# 1. A PLUGIN RAISED A BRIMParseError
# =============================================================================


@pytest.mark.asyncio
async def test_a_parse_error_with_a_code_and_a_context_gives_the_reason_the_wizard_translates(uploaded: str):
    """1: ``BRIMParseError("boom", details={"code": "test_code", "context": {"n": 2}})`` — 400, the object whole, and the file
    ``failed`` with ``boom`` (the error's own message: what the failed file has always kept)."""
    print_section("1: a parse error with a code")
    with brim_lab.registered_settings_brim(_CodedError):
        error = await _parse(uploaded, _CodedError.code)

    assert error.status_code == 400
    assert isinstance(error.detail, dict), f"the detail of a failed parse is an object, not an English sentence (C-70b): {error.detail!r}"
    assert error.detail == {
        "code": "parse_failed",
        "message": "Parse error: boom",
        "plugin_code": _CodedError.code,
        "plugin_name": _CodedError.name,
        "reason": {"code": "test_code", "message": "boom", "context": {"n": 2}},
    }
    assert _stored(uploaded) == ("failed", "boom")
    print_success("the coded parse error reaches the client as parse_failed with its reason")


@pytest.mark.asyncio
async def test_a_parse_error_without_a_code_gives_a_reason_with_no_code_and_no_context(uploaded: str):
    """1: details with no ``code`` and no ``context`` (a plugin's free keys): ``reason`` is ``{code: None, message: <the error's
    message>, context: {}}``; the free keys do not leak into the context."""
    print_section("1: a parse error without a code")
    with brim_lab.registered_settings_brim(_UncodedError):
        error = await _parse(uploaded, _UncodedError.code)

    assert error.status_code == 400
    assert isinstance(error.detail, dict), f"the detail of a failed parse is an object (C-70b): {error.detail!r}"
    assert set(error.detail) == DETAIL_KEYS, error.detail
    assert (error.detail["code"], error.detail["message"], error.detail["plugin_name"]) == ("parse_failed", "Parse error: it broke", _UncodedError.name)
    assert error.detail["reason"] == {"code": None, "message": "it broke", "context": {}}
    assert _stored(uploaded) == ("failed", "it broke")


@pytest.mark.asyncio
async def test_a_plugin_that_is_not_registered_is_named_by_its_code(uploaded: str, monkeypatch: pytest.MonkeyPatch):
    """1: when no registered plugin answers to the code the error came from, ``plugin_name`` is the code (the sentence the user
    reads still names something). The parse itself is replaced by an error: the registry has nothing under that code."""
    ghost = "broker_ghost_of_the_tests"

    async def offloaded(*_args: Any, **_kwargs: Any) -> BRIMParseOutput:
        raise BRIMParseError("ghost failure", details={"code": "ghost_code"})

    monkeypatch.setattr(brokers_api, "parse_file_offloaded", offloaded)

    error = await _parse(uploaded, ghost)

    assert error.status_code == 400
    assert isinstance(error.detail, dict), f"the detail of a failed parse is an object (C-70b): {error.detail!r}"
    assert (error.detail["plugin_code"], error.detail["plugin_name"]) == (ghost, ghost), error.detail
    assert error.detail["reason"] == {"code": "ghost_code", "message": "ghost failure", "context": {}}


# =============================================================================
# 2. THE PARSE GUARD REFUSES
# =============================================================================


@pytest.mark.asyncio
async def test_the_guard_refusal_carries_the_plugins_coded_reason(uploaded: str):
    """2: ``can_parse`` false, the plugin gives a ``BRIMRefusal``: ``message`` is the guard's whole English sentence (plugin by its
    name, file by the name it was uploaded with, the reason after a colon), ``reason`` is the refusal, and the file is ``failed``
    with the same sentence."""
    print_section("2: the guard refuses with a coded reason")
    with brim_lab.registered_settings_brim(_CodedRefusal):
        error = await _parse(uploaded, _CodedRefusal.code)

    english = f"Plugin '{_CodedRefusal.name}' cannot parse file '{UPLOADED_NAME}': the test says no"
    assert error.status_code == 400
    assert isinstance(error.detail, dict), f"the detail of a refused parse is an object, not an English sentence (C-70b): {error.detail!r}"
    assert error.detail == {
        "code": "parse_failed",
        "message": english,
        "plugin_code": _CodedRefusal.code,
        "plugin_name": _CodedRefusal.name,
        "reason": {"code": "test_refusal", "message": "the test says no", "context": {"n": 3}},
    }
    assert _stored(uploaded) == ("failed", english)
    print_success("the refusal reaches the client with the plugin's code and context")


@pytest.mark.asyncio
async def test_the_guard_refusal_of_a_plugin_with_nothing_to_say_has_an_empty_reason(uploaded: str):
    """2: ``can_parse`` false and no reason: ``message`` is the bare guard sentence, ``reason`` has no code, no message and no
    context (``null`` or an empty string for the message; the frontend then shows its own «no reason» text)."""
    print_section("2: the guard refuses without a reason")
    with brim_lab.registered_settings_brim(_SilentRefusal):
        error = await _parse(uploaded, _SilentRefusal.code)

    english = f"Plugin '{_SilentRefusal.name}' cannot parse file '{UPLOADED_NAME}'"
    assert error.status_code == 400
    assert isinstance(error.detail, dict), f"the detail of a refused parse is an object (C-70b): {error.detail!r}"
    assert set(error.detail) == DETAIL_KEYS, error.detail
    assert (error.detail["code"], error.detail["message"], error.detail["plugin_code"], error.detail["plugin_name"]) == ("parse_failed", english, _SilentRefusal.code, _SilentRefusal.name)
    reason = error.detail["reason"]
    assert reason["code"] is None and not reason["message"] and reason["context"] == {}, reason
    assert _stored(uploaded) == ("failed", english)


# =============================================================================
# 3. THE OTHER ERRORS ARE UNCHANGED
# =============================================================================


@pytest.mark.asyncio
async def test_an_unknown_plugin_keeps_a_plain_string_detail(uploaded: str):
    """3: a plugin code nobody registered is not a parse failure of a plugin: 400 with the sentence as a plain string, as before."""
    error = await _parse(uploaded, "broker_does_not_exist_anywhere")

    assert error.status_code == 400
    assert isinstance(error.detail, str), f"an unknown plugin keeps a string detail: {error.detail!r}"
    assert "broker_does_not_exist_anywhere" in error.detail


@pytest.mark.asyncio
async def test_a_file_nobody_uploaded_is_still_404():
    """3: ``FileNotFoundError`` stays 404 "File not found"."""
    error = await _parse("00000000-0000-0000-0000-000000000000", "broker_generic_csv")

    assert error.status_code == 404
    assert error.detail == "File not found"
