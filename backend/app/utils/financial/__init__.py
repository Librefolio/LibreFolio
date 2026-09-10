"""
Financial utilities — pure math, no I/O.

Exports the core WAC and ROI functions.
"""

from importlib import import_module as _import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.utils.financial.roi_utils import (
        CashFlowInput,
        MWRRPoint,
        NAVSnapshot,
        ROIResult,
        SimpleROIPoint,
        TWRRPoint,
        calculate_mwrr,
        calculate_mwrr_series,
        calculate_simple_roi,
        calculate_simple_roi_series,
        calculate_twrr,
        calculate_twrr_series,
    )
    from backend.app.utils.financial.wac_utils import (
        WACCalcResult,
        WACInputTX,
        compute_wac_from_txlist,
        determine_target_currency,
    )

_EXPORT_GROUPS = {
    "roi_utils": (
        "CashFlowInput",
        "MWRRPoint",
        "NAVSnapshot",
        "ROIResult",
        "SimpleROIPoint",
        "TWRRPoint",
        "calculate_mwrr",
        "calculate_mwrr_series",
        "calculate_simple_roi",
        "calculate_simple_roi_series",
        "calculate_twrr",
        "calculate_twrr_series",
    ),
    "wac_utils": ("WACCalcResult", "WACInputTX", "compute_wac_from_txlist", "determine_target_currency"),
}
_EXPORTS = {name: f"{__name__}.{module}" for module, names in _EXPORT_GROUPS.items() for name in names}

__all__ = [  # noqa: RUF022 — grouped by domain with section comments; sorting would scatter related names
    # WAC
    "WACInputTX",
    "WACCalcResult",
    "compute_wac_from_txlist",
    "determine_target_currency",
    # ROI types
    "CashFlowInput",
    "NAVSnapshot",
    "ROIResult",
    "SimpleROIPoint",
    "TWRRPoint",
    "MWRRPoint",
    # ROI functions
    "calculate_simple_roi",
    "calculate_simple_roi_series",
    "calculate_twrr",
    "calculate_twrr_series",
    "calculate_mwrr",
    "calculate_mwrr_series",
]


def __getattr__(name: str) -> object:
    if name in _EXPORTS:
        value = getattr(_import_module(_EXPORTS[name]), name)
    elif name in _EXPORT_GROUPS:
        value = _import_module(f"{__name__}.{name}")
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_EXPORTS) | set(_EXPORT_GROUPS))
