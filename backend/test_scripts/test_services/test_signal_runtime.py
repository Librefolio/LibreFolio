"""Tests for signal-stack fail-fast validation and startup integration."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.app import main
from backend.app.services import signal_runtime
from backend.app.services.signal_runtime import SignalRuntimeUnavailable, validate_signal_runtime


def test_validate_signal_runtime_accepts_locked_stack():
    info = validate_signal_runtime()

    assert info.pandas_ta_classic_version == "0.6.52"
    assert info.talib_version == "0.7.1"


def test_validate_signal_runtime_rejects_missing_pandas_ta(monkeypatch):
    def missing_pandas_ta(name: str):
        if name == "pandas_ta_classic":
            raise ImportError("missing")
        raise AssertionError(f"unexpected import: {name}")

    monkeypatch.setattr(signal_runtime.importlib, "import_module", missing_pandas_ta)

    with pytest.raises(SignalRuntimeUnavailable, match="pandas-ta-classic cannot be loaded"):
        validate_signal_runtime()


def test_validate_signal_runtime_rejects_missing_talib(monkeypatch):
    pandas_ta = SimpleNamespace(version="0.6.52", Imports={"talib": True})

    def missing_talib(name: str):
        if name == "pandas_ta_classic":
            return pandas_ta
        if name == "talib":
            raise ImportError("missing")
        raise AssertionError(f"unexpected import: {name}")

    monkeypatch.setattr(signal_runtime.importlib, "import_module", missing_talib)

    with pytest.raises(SignalRuntimeUnavailable, match="TA-Lib cannot be loaded"):
        validate_signal_runtime()


def test_validate_signal_runtime_wraps_native_loader_failures(monkeypatch):
    pandas_ta = SimpleNamespace(version="0.6.52", Imports={"talib": True})

    def broken_native_library(name: str):
        if name == "pandas_ta_classic":
            return pandas_ta
        if name == "talib":
            raise OSError("missing shared library")
        raise AssertionError(f"unexpected import: {name}")

    monkeypatch.setattr(signal_runtime.importlib, "import_module", broken_native_library)

    with pytest.raises(SignalRuntimeUnavailable, match="OSError: missing shared library"):
        validate_signal_runtime()


def test_validate_signal_runtime_rejects_silent_fallback(monkeypatch):
    modules = {
        "pandas_ta_classic": SimpleNamespace(version="0.6.52", Imports={"talib": False}),
        "talib": SimpleNamespace(__version__="0.7.1"),
    }
    monkeypatch.setattr(signal_runtime.importlib, "import_module", modules.__getitem__)

    with pytest.raises(SignalRuntimeUnavailable, match="silently use native"):
        validate_signal_runtime()


@pytest.mark.asyncio
async def test_lifespan_fails_before_database_startup_when_signal_runtime_is_missing(monkeypatch):
    def fail_runtime():
        raise SignalRuntimeUnavailable("stack unavailable")

    ensure_dirs_called = False

    def track_ensure_dirs():
        nonlocal ensure_dirs_called
        ensure_dirs_called = True

    monkeypatch.setattr(main, "validate_signal_runtime", fail_runtime)
    monkeypatch.setattr(main, "ensure_data_dirs", track_ensure_dirs)

    with pytest.raises(SignalRuntimeUnavailable, match="stack unavailable"):
        async with main.lifespan(main.app):
            pass

    assert ensure_dirs_called is False
