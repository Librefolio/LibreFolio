"""
Financial utilities — pure math, no I/O.

Exports the core WAC and ROI functions.
"""

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

__all__ = [
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
