"""
Common schemas shared across subsystems.

This module contains Pydantic models used by multiple services
(e.g., both FX and Asset pricing systems).

**Domain Coverage**:
- BackwardFillInfo: Shared by FA and FX for gap-filling logic
- DateRangeModel: Reusable date range representation

**Design Notes**:
- No backward compatibility maintained during refactoring
- Models designed for maximum reusability across FA/FX systems
- Future: Consider adding validation (end >= start) via Pydantic validator
"""
# Postpones evaluation of type hints to improve imports and performance. Also avoid circular import issues.
from __future__ import annotations

from datetime import date as date_type
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from backend.app.utils.datetime_utils import parse_ISO_date
from backend.app.utils.validation_utils import validate_date_range_order


class BackwardFillInfo(BaseModel):
    """
    Backward-fill information when requested date has no data.

    Used by both FX (fx.py) and Asset pricing (asset_source.py) systems
    to indicate when historical data was used instead of exact date match.

    Attributes:
        actual_rate_date: stored as a `date` (accepts ISO string, `date` or `datetime` on input)
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
    model_config = ConfigDict()

    actual_rate_date: date_type = Field(..., description="ISO date of actual data used (YYYY-MM-DD)")
    days_back: int = Field(..., description="Number of days back from requested date")

    @field_validator("actual_rate_date", mode="before")
    @classmethod
    def _parse_actual_rate_date(cls, v):
        return parse_ISO_date(v)

    def actual_rate_date_str(self) -> str:
        """Restituisce la data in formato ISO string (YYYY-MM-DD)."""
        return self.actual_rate_date.isoformat()


class DateRangeModel(BaseModel):
    """
    Reusable date range model for FA and FX operations.

    Used across multiple operations: price deletion, FX rate queries, etc.
    Represents an inclusive date range [start, end].

    Attributes:
        start: Start date (inclusive, required)
        end: End date (inclusive, optional - defaults to start for single day)

    Design Notes:
        - If end is None, represents a single day (start only)
        - If end is provided, represents a range [start, end] inclusive
        - Validator ensures end >= start when provided

    Examples:
        # Single day
        {"start": "2025-11-05", "end": null}  # Just 2025-11-05

        # Range
        {"start": "2025-11-01", "end": "2025-11-30"}  # Entire November
    """
    model_config = ConfigDict(extra="forbid")

    start: date_type = Field(..., description="Start date (inclusive)")
    end: Optional[date_type] = Field(None, description="End date (inclusive, optional = single day)")

    @model_validator(mode='after')
    def validate_end_after_start(self) -> 'DateRangeModel':
        """Ensure end >= start when end is provided."""
        validate_date_range_order(self.start, self.end)
        return self
