"""
The unified batch of ``POST /transactions/validate`` and ``/commit``: the operations and statuses of a batch item,
the request body, the per-item results and the response, the validation codes with their metadata, the validation
issue, and the split and promote items the pipeline parses.
"""

from __future__ import annotations

from datetime import date as date_type
from enum import StrEnum
from typing import Any, Dict, List, Literal, Optional

from pydantic import Field, field_validator, model_validator

from backend.app.schemas.common import (
    BaseBulkResponse,
    BaseDeleteResult,
    Currency,
    StrictModel,
)
from backend.app.schemas.wac import WACPreviewResultItem

# Per-item diagnostic status for atomic bulk operations.
# - "success":       item applied cleanly — and, when a commit was requested,
#                    the whole batch committed. On a dry-run (`/validate`,
#                    commit=False) it means "this item would apply cleanly":
#                    the caller never asked to persist, so there is nothing to
#                    be misled about.
# - "simulated":     a commit WAS requested, the item applied in-session, but
#                    the batch was rolled back (another item failed or balance
#                    validation triggered). The `ids` are the ids the rows
#                    would have had — they do not exist.
# - "failed":        the item itself raised the error that caused the rollback.
# - "not_attempted": processing stopped before this item was considered.
#
# A caller that wants "do my rows exist?" must read `committed`. `status` alone
# answers "was this item acceptable?".
TXItemStatus = Literal["success", "simulated", "failed", "not_attempted"]

# Batch operation types — single source of truth for all operation Literals.
TXBatchOperation = Literal["create", "update", "delete", "split", "promote"]


class TXDeleteResult(BaseDeleteResult):
    """
    Result for a single transaction deletion attempt.

    Extends BaseDeleteResult with transaction-specific identifier and the
    atomic diagnostic status.
    """

    id: int = Field(..., description="Transaction ID")
    status: TXItemStatus = Field(default="not_attempted", description="Atomic diagnostic status")


# =============================================================================
# UNIFIED BATCH (Unified Batch Pipeline — replaces POST/PATCH/DELETE /bulk)
# =============================================================================


class TXMixedBatch(StrictModel):
    """Unified batch body for /validate and /commit.

    `creates` and `updates` are List[dict] (not List[TXCreateItem]) so that
    FastAPI does NOT pre-validate individual rows. The service does per-row
    model_validate() in try/except, collecting schema errors alongside
    business-rule and balance violations in one response.
    """

    creates: List[dict] = Field(default_factory=list)
    updates: List[dict] = Field(default_factory=list)
    deletes: List[int] = Field(default_factory=list)
    splits: List[dict] = Field(default_factory=list, max_length=100)
    promotes: List[dict] = Field(default_factory=list, max_length=100)


class TXBatchResultItem(StrictModel):
    """Per-item result for committed rows."""

    operation: TXBatchOperation
    index: int
    ids: List[int] = Field(default_factory=list, description="IDs of affected transactions. Split/promote return both IDs.")
    link_uuid: Optional[str] = None
    status: TXItemStatus


class TXBatchResponse(BaseBulkResponse[TXBatchResultItem]):
    """Unified response for /validate and /commit.

    Extends BaseBulkResponse with transaction-specific fields:
    - committed: whether the batch was committed to DB
    - issues: rich validation issue objects (superset of errors)
    - wac_results: WAC computation results for auto items
    """

    committed: bool = Field(..., description="Whether the batch was committed to DB")
    issues: List[TXValidationIssue] = Field(default_factory=list, description="Rich validation issues")
    wac_results: Optional[List[WACPreviewResultItem]] = Field(None, description="WAC results for auto items")


# =============================================================================
# VALIDATION CODES (F13 — centralized enum)
# =============================================================================


class TXValidationCode(StrEnum):
    """Centralized validation error codes for transaction operations.

    Frontend maps these to i18n keys via `transactions.errors.{code}`.
    Exposed in GET /transactions/types → validation_codes.
    """

    BALANCE_ASSET_NEGATIVE = "balanceAssetNegative"
    BALANCE_CASH_NEGATIVE = "balanceCashNegative"
    TX_NOT_FOUND = "txNotFound"
    TYPE_CANNOT_SPLIT = "typeCannotSplit"
    SPLIT_IDS_MISMATCH = "splitIdsMismatch"
    PROMOTE_REF_NOT_FOUND = "promoteRefNotFound"
    ALREADY_PAIRED = "alreadyPaired"
    NO_PROMOTE_RULE = "noPromoteRule"
    ACCESS_DENIED = "accessDenied"
    LINK_UUID_PAIR_COUNT = "linkUuidPairCount"
    WAC_FX_UNAVAILABLE = "wacFxUnavailable"
    COST_BASIS_REQUIRED = "costBasisRequired"
    # C-97: a value over its column's limit, params {max}; the values of db/precision.decimal_limit_issue.
    DECIMAL_PLACES_EXCEEDED = "decimalPlacesExceeded"
    SIGNIFICANT_DIGITS_EXCEEDED = "significantDigitsExceeded"
    INTEGER_DIGITS_EXCEEDED = "integerDigitsExceeded"
    # N74 (R13-SEC7-3): a date outside 1900-01-01 … today + 1 year, params {min, max} (ISO dates).
    DATE_OUT_OF_RANGE = "dateOutOfRange"
    # W-B69: an Auto cost over a pool holding rows that cannot be read, params {count}.
    AUTO_COST_UNREADABLE = "autoCostUnreadable"


class TXValidationCodeInfo(StrictModel):
    """Metadata for a validation code — exposed in GET /transactions/types."""

    code: str = Field(..., description="Validation code identifier")
    description: str = Field(..., description="Human-readable description")
    severity: Literal["error", "warning"] = Field("error", description="Issue severity")


# Precomputed list of all validation codes for the types endpoint.
VALIDATION_CODE_METADATA: list[TXValidationCodeInfo] = [TXValidationCodeInfo(code=c.value, description=c.name.replace("_", " ").title(), severity="error") for c in TXValidationCode]


# =============================================================================
# VALIDATION ISSUE
# =============================================================================


class TXValidationIssue(StrictModel):
    """Single issue produced by validate_batch."""

    operation: TXBatchOperation
    index: int = Field(..., ge=-1, description="Index within the corresponding list (-1 = broker-level, not row-specific)")
    ref_id: Optional[int] = Field(default=None, description="Transaction ID for update/delete, None for create")
    error: str
    code: Optional[str] = Field(default=None, description="i18n error code from the catalog (e.g. 'assetRequired')")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Structured params for frontend i18n resolver (IDs, dates, amounts)")
    field: Optional[str] = Field(default=None, description="Draft field that caused the error (e.g. 'asset_id', 'quantity')")


# =============================================================================
# BATCH SPLIT / PROMOTE ITEMS (pipeline-only, no standalone endpoints)
# =============================================================================


class TXSplitBatchItem(StrictModel):
    """Single split within a batch. Both IDs of the pair must be provided."""

    id_a: int = Field(..., gt=0, description="ID of one half of the pair")
    id_b: int = Field(..., gt=0, description="ID of the other half of the pair")

    @model_validator(mode="after")
    def ids_must_differ(self) -> TXSplitBatchItem:
        if self.id_a == self.id_b:
            raise ValueError("id_a and id_b must be different transactions")
        return self


class TXPromoteResolvedFields(StrictModel):
    """The merged values a promotion writes (PromoteMergeModal), typed like a create's fields (H-41).

    A key left out leaves both rows as they are; an explicit null clears the description, the tags or the cost basis.
    The description, the tags and the date go on both rows, the cost basis on the receiving leg only (decision 47).
    Applied by ``batch_creates._apply_promote_resolved_fields``. A value refused here is an issue of the promote at the
    batch's parse, named by the field itself (``transaction_batch_stages._loc_to_field``). Before, the dict was applied
    as it came: a description of any type or length reached the Text column, an unknown key was ignored, and a malformed
    date, tags or cost basis raised out of the batch.
    """

    description: Optional[str] = Field(default=None, max_length=500, description="Merged notes, on both rows; null clears them")
    tags: Optional[List[str]] = Field(default=None, description="Merged tags, on both rows; null clears them")
    date: Optional[date_type] = Field(default=None, description="Merged settlement date, on both rows; never null")
    cost_basis_override: Optional[Currency] = Field(default=None, description="Merged per-unit cost basis, on the receiving leg; null clears it")

    @field_validator("tags", mode="before")
    @classmethod
    def _validate_tags(cls, v: Any) -> Optional[List[str]]:
        # transactions.py imports type_metadata, which imports this module: imported here, when a promote is parsed.
        from backend.app.schemas.transactions.transactions import validate_tags_list  # noqa: PLC0415 — avoid circular import

        return validate_tags_list(v)

    @field_validator("date", mode="before")
    @classmethod
    def _date_not_null(cls, v: Any) -> Any:
        """An explicit null date is refused: no row is without one. Leave the key out to keep the rows' dates."""
        if v is None:
            raise ValueError("date cannot be null: leave it out to keep the rows' dates")
        return v


class TXPromoteBatchItem(StrictModel):
    """Single promote within a batch. Supports saved+saved, new+new, saved+new."""

    id_a: Optional[int] = Field(None, gt=0, description="Real ID for saved TX A")
    id_b: Optional[int] = Field(None, gt=0, description="Real ID for saved TX B")
    link_uuid_a: Optional[str] = Field(None, max_length=36, description="link_uuid to resolve TX A from creates in same batch")
    link_uuid_b: Optional[str] = Field(None, max_length=36, description="link_uuid to resolve TX B from creates in same batch")
    resolved_fields: Optional[TXPromoteResolvedFields] = Field(None, description="Merged field values from PromoteMergeModal: description, tags, date, cost_basis_override")

    @model_validator(mode="after")
    def _validate_refs(self) -> TXPromoteBatchItem:
        """At least one of id_a/link_uuid_a and id_b/link_uuid_b must be set."""
        if self.id_a is None and self.link_uuid_a is None:
            raise ValueError("Either id_a or link_uuid_a must be provided for TX A")
        if self.id_b is None and self.link_uuid_b is None:
            raise ValueError("Either id_b or link_uuid_b must be provided for TX B")
        if self.id_a is not None and self.link_uuid_a is not None:
            raise ValueError("Provide either id_a or link_uuid_a for TX A, not both")
        if self.id_b is not None and self.link_uuid_b is not None:
            raise ValueError("Provide either id_b or link_uuid_b for TX B, not both")
        return self
