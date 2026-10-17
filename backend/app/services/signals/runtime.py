"""Fail-fast validation for the production technical-analysis stack."""

from __future__ import annotations

import importlib
from dataclasses import dataclass


class SignalRuntimeUnavailable(RuntimeError):
    """Raised when the locked technical-analysis stack is incomplete."""


@dataclass(frozen=True)
class SignalRuntimeInfo:
    pandas_ta_classic_version: str
    talib_version: str


def validate_signal_runtime() -> SignalRuntimeInfo:
    """Import both libraries and reject pandas-ta-classic silent fallback."""
    try:
        pandas_ta = importlib.import_module("pandas_ta_classic")
    except Exception as exc:
        raise SignalRuntimeUnavailable(f"pandas-ta-classic cannot be loaded: {type(exc).__name__}: {exc}") from exc

    try:
        talib = importlib.import_module("talib")
    except Exception as exc:
        raise SignalRuntimeUnavailable(f"TA-Lib cannot be loaded: {type(exc).__name__}: {exc}") from exc

    imports = getattr(pandas_ta, "Imports", None)
    if not isinstance(imports, dict) or imports.get("talib") is not True:
        raise SignalRuntimeUnavailable("pandas-ta-classic cannot detect TA-Lib; delegated plugins would silently use native implementations")

    return SignalRuntimeInfo(
        pandas_ta_classic_version=str(pandas_ta.version),
        talib_version=str(talib.__version__),
    )


__all__ = [
    "SignalRuntimeInfo",
    "SignalRuntimeUnavailable",
    "validate_signal_runtime",
]
