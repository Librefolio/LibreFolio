"""
Common schemas shared across subsystems.

This module contains Pydantic models used by multiple services
(e.g., both FX and Asset pricing systems).

**Domain Coverage**:
- BackwardFillInfo: Shared by FA and FX for gap-filling logic
- DateRangeModel: Reusable date range representation
- BaseBulkResponse: Standardized base class for bulk operation responses

**Design Notes**:
- No backward compatibility maintained during refactoring
- Models designed for maximum reusability across FA/FX systems
- Future: Consider adding validation (end >= start) via Pydantic validator
"""
# Postpones evaluation of type hints to improve imports and performance. Also avoid circular import issues.
from __future__ import annotations

from datetime import date as date_type
from typing import Optional, List, TypeVar, Generic

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from backend.app.utils.datetime_utils import parse_ISO_date
from backend.app.utils.validation_utils import validate_date_range_order

# Generic type for result items in bulk responses
TResult = TypeVar('TResult', bound=BaseModel)


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


class BaseBulkResponse(BaseModel, Generic[TResult]):
    """
    Standardized base class for all bulk operation responses.

    Provides consistent structure across FA and FX systems for bulk operations.
    Subclasses should specify the concrete result type.

    Standard fields:
    - results: List of per-item operation results
    - success_count: Number of successful operations
    - failed_count: Number of failed operations (derived from len(results) - success_count)
    - errors: Optional list of error messages (operation-level errors, not per-item)

    Design Notes:
    - Generic class parameterized by TResult (the result item type)
    - Subclasses inherit this structure and specify their result type
    - failed_count is NOT stored, computed from results length
    - errors field is for operation-level errors (e.g., "timeout", "provider unavailable")
    - Per-item errors should be in the result items themselves

    Examples:
        ```python
        class FABulkAssetCreateResponse(BaseBulkResponse[FAAssetCreateResult]):
            # Inherits: results, success_count, errors
            # failed_count is computed property
            pass

        class FXBulkUpsertResponse(BaseBulkResponse[FXUpsertResult]):
            # Can add specific fields if needed
            inserted_count: int
            updated_count: int
        ```
    """
    model_config = ConfigDict(extra="forbid")

    results: List[TResult] = Field(..., description="Per-item operation results")
    success_count: int = Field(..., ge=0, description="Number of successful operations")
    errors: List[str] = Field(default_factory=list, description="Operation-level errors (not per-item)")

    @property
    def failed_count(self) -> int:
        """Computed property: number of failed operations."""
        return len(self.results) - self.success_count

    @property
    def total_count(self) -> int:
        """Computed property: total number of items processed."""
        return len(self.results)


class BaseDeleteResult(BaseModel):
    """
    Standardized base class for all delete/removal operation results.

    Provides consistent structure across FA and FX systems for deletion operations.
    All delete/removal result classes should inherit from this base.

    Standard fields:
    - success: bool - Whether the deletion operation succeeded
    - deleted_count: int - Number of items actually deleted (always >= 0)
    - message: Optional[str] - Info/warning/error message

    Identifier fields:
    - Subclasses add their own identifier fields (asset_id, base/quote, etc.)

    Design Notes:
    - Simple inheritance model (no Generic complexity)
    - Consistent naming: always use 'deleted_count' (not 'deleted')
    - message is optional (None if operation successful with no warnings)
    - Subclasses can add operation-specific fields (existing_count, etc.)

    Examples:
        ```python
        class FAAssetDeleteResult(BaseDeleteResult):
            asset_id: int
            # Inherits: success, deleted_count, message

        class FXDeleteResult(BaseDeleteResult):
            base: str
            quote: str
            date_range: DateRangeModel
            existing_count: int  # Operation-specific field
            # Inherits: success, deleted_count, message
        ```

    Benefits:
    - Consistent API across all deletion operations
    - Guaranteed validation (deleted_count >= 0)
    - Single source of truth for deletion result structure
    - Easy to extend with operation-specific fields
    """
    model_config = ConfigDict(extra="forbid")

    success: bool = Field(..., description="Whether the deletion succeeded")
    deleted_count: int = Field(..., ge=0, description="Number of items deleted")
    message: Optional[str] = Field(None, description="Info/warning/error message")


class BaseBulkDeleteResponse(BaseBulkResponse[TResult]):
    """
    Specialized base class for bulk delete/removal operations.
    
    Combines BaseBulkResponse structure with delete-specific aggregate field.
    Inherits list of results and success tracking from BaseBulkResponse,
    adds total deletion count across all items.
    
    Standard fields (from BaseBulkResponse):
    - results: List[TResult] - Per-item deletion results
    - success_count: int - Number of successful deletions
    - errors: List[str] - Operation-level errors
    
    Delete-specific field:
    - total_deleted: int - Total number of records deleted across all items
    
    Computed properties (from BaseBulkResponse):
    - failed_count: int - Number of failed deletions
    - total_count: int - Total number of items processed
    
    Design Notes:
    - Extends BaseBulkResponse with delete-specific aggregate
    - total_deleted is the sum of all deleted_count from individual results
    - Generic class parameterized by TResult (the result item type)
    - Use when bulk operation deletes multiple records per item
    
    Examples:
        ```python
        # For price deletion (deletes multiple price records per asset)
        class FABulkDeleteResponse(BaseBulkDeleteResponse[FAPriceDeleteResult]):
            pass
        
        # For FX rate deletion (deletes multiple rates per pair)
        class FXBulkDeleteResponse(BaseBulkDeleteResponse[FXDeleteResult]):
            pass
        ```
    
    Benefits:
    - Consistent pattern for bulk deletion operations
    - Clear separation: success_count (items) vs total_deleted (records)
    - Inherits all BaseBulkResponse benefits
    - Delete-specific semantics explicit in class name
    """
    # Delete-specific aggregate field
    total_deleted: int = Field(..., ge=0, description="Total number of records deleted across all items")
