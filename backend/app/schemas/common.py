"""
Common schemas shared across subsystems.

This module contains Pydantic models and TypedDicts used by multiple services
(e.g., both FX and Asset pricing systems).
"""
from pydantic import BaseModel, Field


class BackwardFillInfo(BaseModel):
    """
    Backward-fill information when requested date has no data.

    Used by both FX (fx.py) and Asset pricing (asset_source.py) systems
    to indicate when historical data was used instead of exact date match.

    Attributes:
        actual_rate_date: ISO date string of the actual data used (YYYY-MM-DD)
        days_back: Number of days back from requested date

    Examples:
        # Exact match - backward_fill_info is None
        {
            "date": "2025-11-05",
            "value": 1.234,
            "backward_fill_info": None
        }

        # Backfilled - used data from 3 days earlier
        {
            "date": "2025-11-05",
            "value": 1.234,
            "backward_fill_info": {
                "actual_rate_date": "2025-11-02",
                "days_back": 3
            }
        }
    """
    actual_rate_date: str = Field(..., description="ISO date of actual data used (YYYY-MM-DD)")
    days_back: int = Field(..., description="Number of days back from requested date")
