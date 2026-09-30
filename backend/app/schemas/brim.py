"""
Broker Report Import Manager (BRIM) schemas.

DTOs for broker report file upload, parsing, and import operations.

**Naming Convention:**
- BRIM prefix: Broker Report Import Manager schemas
- File-related: BRIMFileInfo, BRIMFileStatus
- Plugin-related: BRIMPluginInfo
- Parse/Import: BRIMParseRequest, BRIMParseResponse, BRIMImportRequest
- Asset Mapping: BRIMAssetCandidate, BRIMAssetMapping, BRIMMatchConfidence
- Duplicate Detection: BRIMDuplicateMatch, BRIMTXDuplicateCandidate, BRIMDuplicateReport

**Design Notes:**
- File IDs are UUIDs (never expose filesystem paths)
- Fake Asset IDs start from MAX_INT and decrement to avoid collision
- Parsing returns transactions with fake asset IDs for user review
- User maps fake IDs to real assets before import
- Duplicate detection flags possible/certain duplicates
- Import accepts (potentially modified) List[TXCreateItem]
- Final import uses TransactionService.create_bulk() - same as manual
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.app.db.models import TransactionType
from backend.app.schemas.common import Currency, DateRangeModel, SafeDecimal, StrictModel
from backend.app.schemas.transactions import TXCreateItem
from backend.app.utils.datetime_utils import UTCDateTime

# =============================================================================
# CONSTANTS
# =============================================================================

# Fake IDs start from MAX_INT and decrement to avoid collision with real IDs
FAKE_ASSET_ID_BASE = 2**31 - 1  # 2147483647


def is_fake_asset_id(asset_id: Optional[int]) -> bool:
    """Check if an asset_id is a fake ID (used during import preview)."""
    if asset_id is None:
        return False
    return asset_id >= FAKE_ASSET_ID_BASE - 10000  # Allow 10000 fake assets per import


# Columns every combined report-set table must carry (see BRIMCombinedTable).
COMBINED_REQUIRED_HEADERS = ("lf_row_kind", "lf_source")


# =============================================================================
# EXTRACTED ASSET INFO (from plugin parsing)
# =============================================================================


# =============================================================================
# ENUMS
# =============================================================================


class BRIMFileStatus(StrEnum):
    """Status of an uploaded broker report file.

    Flow: UPLOADED → PARSED (success) or FAILED (error)
    After parsing, the file stays in PARSED. The actual transaction import
    uses POST /transactions and doesn't change file status.
    """

    UPLOADED = "uploaded"  # File uploaded, awaiting processing
    PARSED = "parsed"  # Successfully parsed, ready for review/import
    FAILED = "failed"  # Processing failed with error


class BRIMMatchConfidence(StrEnum):
    """Confidence level for asset candidate matching.

    Criteria:
    - EXACT: ISIN match (ISIN is globally unique identifier)
    - HIGH: Symbol exact match + same asset type
    - MEDIUM: Symbol exact match only (no type verification)
    - LOW: Partial name match or fuzzy symbol match
    """

    EXACT = "exact"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BRIMDuplicateLevel(StrEnum):
    """Confidence level for duplicate detection (ascending order).

    Levels (from lowest to highest confidence):
    1. POSSIBLE: type + date + quantity + cash match, but asset not resolved
    2. POSSIBLE_WITH_ASSET: POSSIBLE + asset auto-resolved (1 candidate)
    3. LIKELY: POSSIBLE + identical non-empty description, but asset not resolved
    4. LIKELY_WITH_ASSET: LIKELY + asset auto-resolved (practically certain duplicate)

    The WITH_ASSET variants are more reliable because the asset was automatically
    matched to a single candidate in the database.
    """

    POSSIBLE = "possible"
    POSSIBLE_WITH_ASSET = "possible_with_asset"
    LIKELY = "likely"
    LIKELY_WITH_ASSET = "likely_with_asset"


# =============================================================================
# FILE MANAGEMENT SCHEMAS
# =============================================================================


class BRIMDerivedRef(StrictModel):
    """One original file a combined report-set file was built from."""

    file_id: str = Field(..., description="UUID of the original file")
    role: Optional[str] = Field(default=None, description="Role of the file in the set (e.g. 'custody', 'cash')")
    filename: str = Field(..., description="Original filename, as uploaded")
    deleted: bool = Field(default=False, description="True once the original has been deleted; the combined file stays usable")


class BRIMFileInfo(StrictModel):
    """
    Information about an uploaded broker report file.

    Attributes:
        file_id: UUID identifier (NOT filesystem path)
        filename: Original filename from upload
        size_bytes: File size in bytes
        status: Current processing status
        uploaded_at: UTC timestamp when file was uploaded
        processed_at: UTC timestamp when file was processed (if applicable)
        compatible_plugins: List of plugin codes that can parse this file
        error_message: Error description if status is FAILED
        uploaded_by_user_id: ID of user who uploaded the file
        target_broker_id: ID of broker this file belongs to
        last_parse_result: Cached result from last successful parse
        parsed_plugin_code: Plugin code used at last successful parse
        parsed_plugin_version: Plugin version at last successful parse
        parse_is_stale: Computed flag. True iff status==PARSED and
            parsed_plugin_version differs from the plugin's current
            version (i.e., the plugin code has been updated since the
            cached parse was produced). The UI can use this to surface a
            "Re-parse available" hint without introducing a new
            persisted status.
    """

    file_id: str = Field(..., description="UUID identifier for the file")
    filename: str = Field(..., description="Original filename from upload")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")
    status: BRIMFileStatus = Field(..., description="Current processing status")
    uploaded_at: UTCDateTime = Field(..., description="UTC timestamp when uploaded")
    processed_at: Optional[UTCDateTime] = Field(default=None, description="UTC timestamp when processed")
    compatible_plugins: List[str] = Field(default_factory=list, description="Plugin codes that can parse this file")
    error_message: Optional[str] = Field(default=None, description="Error description if processing failed")
    # Multi-user support fields
    uploaded_by_user_id: Optional[int] = Field(default=None, description="ID of user who uploaded the file")
    target_broker_id: Optional[int] = Field(default=None, description="ID of broker this file belongs to")
    last_parse_result: Optional[dict] = Field(default=None, description="Cached result from last successful parse")
    # Plugin versioning (for cache invalidation)
    parsed_plugin_code: Optional[str] = Field(default=None, description="Plugin code used at last successful parse")
    parsed_plugin_version: Optional[str] = Field(default=None, description="Plugin version at last successful parse")
    parse_is_stale: bool = Field(default=False, description="True if cached parse was produced by an older plugin version and a re-parse is recommended")
    # Report sets: files uploaded together, and the combined file derived from them
    batch_id: Optional[str] = Field(default=None, description="Upload batch the file belongs to; files uploaded together form a report set")
    kind: Literal["original", "combined"] = Field(default="original", description="original = uploaded by the user; combined = derived by a report-set plugin")
    derived_from: List[BRIMDerivedRef] = Field(default_factory=list, description="For a combined file: the originals it was built from")
    combined_into: List[str] = Field(default_factory=list, description="For an original file: the combined files built from it")
    combine_is_stale: bool = Field(default=False, description="True if a combined file was built by an older plugin version")


# =============================================================================
# PLUGIN SCHEMAS
# =============================================================================


class BRIMAssetNotice(BaseModel):
    """
    A per-asset advisory notice raised by a plugin while parsing a broker report.

    Plugins attach notices to a ``BRIMExtractedAssetInfo`` when the transactions for that
    asset suggest something the user should know before creating/mapping it — e.g. a
    redemption/maturity movement implying the security is delisted and won't be found by the
    online search. The frontend groups notices by ``kind`` (category label from app i18n) and
    lists each ``reason`` bullet (authored by the plugin in the report's language). Notices are
    advisory only: they never change import behaviour (the user decides, e.g. via the active toggle).

    Attributes:
        kind: Category key driving banner grouping/label (e.g. "maturity_suspected"). Extensible —
            the frontend falls back to a generic label for unknown kinds.
        reason: Human-readable, plugin-localized motivation shown as a bullet under the banner.
        transaction_indexes: Positions (in the parse output's transactions list) of the transactions
            that triggered this notice. Currently unused by the UI; reserved for a future preview.
    """

    kind: str = Field(..., description="Notice category key driving banner grouping (e.g. 'maturity_suspected')")
    reason: str = Field(..., description="Plugin-localized motivation shown as a bullet under the banner")
    transaction_indexes: List[int] = Field(default_factory=list, description="Indexes of triggering transactions in the parse output (reserved for future preview)")


class BRIMExtractedAssetInfo(StrictModel):
    """
    Extracted asset information from a broker report row.

    Used by plugins to classify and identify assets found in imported files.
    All fields are optional as not all reports contain all identifiers.

    Attributes:
        extracted_symbol: Ticker/symbol extracted from report (e.g., "AAPL", "VWCE")
        extracted_isin: ISIN code extracted from report (e.g., "US0378331005")
        extracted_name: Asset name/description extracted from report
        notices: Advisory notices for this asset (e.g. suspected maturity/redemption). Empty by default.
    """

    extracted_symbol: Optional[str] = Field(default=None, description="Ticker/symbol from report")
    extracted_isin: Optional[str] = Field(default=None, description="ISIN code from report")
    extracted_name: Optional[str] = Field(default=None, description="Asset name/description from report")
    notices: List[BRIMAssetNotice] = Field(default_factory=list, description="Advisory notices for this asset (e.g. suspected maturity/redemption); empty by default")


class BRIMReportRole(StrictModel):
    """One kind of export a report-set plugin reads (e.g. custody transactions, cash statement)."""

    code: str = Field(..., min_length=1, description="Role code, unique within the plugin (e.g. 'custody', 'cash')")
    required: bool = Field(default=True, description="The set cannot be combined without at least one file of this role")
    multiple: bool = Field(default=False, description="Several files of this role are allowed in one set")
    extensions: List[str] = Field(..., min_length=1, description="Accepted file extensions (e.g. ['.csv'])")
    description: str = Field(..., description="English description of the export (UI fallback)")
    max_history: Optional[str] = Field(default=None, description="How far back the bank exports this role, as an ISO 8601 duration (e.g. 'P1Y')")
    must_cover: Optional[str] = Field(default=None, description="Role whose period this role must cover (e.g. the cash statement must cover the custody period)")


class BRIMCoverage(StrictModel):
    """The period a report-set member covers on one date axis."""

    axis: Literal["trade", "value"] = Field(..., description="trade = operation date; value = settlement (value) date")
    start: date = Field(..., description="First date covered (inclusive)")
    end: date = Field(..., description="Last date covered (inclusive)")

    @model_validator(mode="after")
    def _check_order(self) -> BRIMCoverage:
        if self.start > self.end:
            raise ValueError("coverage start must not be after its end")
        return self


class BRIMMemberSummary(StrictModel):
    """What a report-set plugin reads from one member without combining: role, size and coverage."""

    role: Optional[str] = Field(default=None, description="Role recognised in the file, or None")
    rows: int = Field(..., ge=0, description="Number of data rows")
    coverage: List[BRIMCoverage] = Field(default_factory=list, description="Covered period per date axis")
    account_fingerprint: Optional[str] = Field(default=None, exclude=True, description="Opaque account key compared in memory only; never serialised")


class BRIMPluginInfo(StrictModel):
    """
    Information about an available import plugin.

    Attributes:
        code: Unique plugin identifier (e.g., 'broker_generic_csv')
        name: Human-readable name (e.g., 'Generic CSV')
        description: Plugin description for UI
        supported_extensions: List of supported file extensions
        icon_url: URL to the broker's icon/logo (optional)
        docs_url: URL to plugin documentation (optional)
        plugin_version: Semver of the parsing logic. Bumped when the output
            for the same file would change. The frontend compares this
            with ``BRIMFileInfo.parsed_plugin_version`` to decide whether a
            cached parse is stale.
        detection_priority: Priority for auto-detection (higher = checked first).
            100+ for broker-specific, 50-99 for semi-generic, 0-49 for fallbacks.
    """

    code: str = Field(..., description="Unique plugin identifier")
    name: str = Field(..., description="Human-readable plugin name")
    description: str = Field(..., description="Plugin description for UI")
    supported_extensions: List[str] = Field(default_factory=list, description="Supported file extensions (e.g., ['.csv', '.xlsx'])")
    icon_url: Optional[str] = Field(None, description="URL to broker icon/logo (absolute URL or relative path)")
    docs_url: Optional[str] = Field(None, description="URL to the plugin documentation page")
    plugin_version: str = Field(..., description="Semver of the parsing logic; bumped when plugin output would change for the same input")
    detection_priority: int = Field(100, description="Priority for auto-detection (higher = checked first). 100+ broker-specific, 50-99 semi-generic, 0-49 fallbacks")
    report_roles: List[BRIMReportRole] = Field(default_factory=list, description="Export roles of a report-set plugin; empty for single-file plugins")


# =============================================================================
# ASSET MAPPING SCHEMAS (Fake ID → Real Asset)
# =============================================================================


class BRIMAssetCandidate(BaseModel):
    """
    A potential real asset match for a fake asset ID.

    Found by searching the database using extracted info from the import file.
    """

    asset_id: int = Field(..., description="Real asset ID from database")
    symbol: Optional[str] = Field(None, description="Asset symbol/ticker")
    isin: Optional[str] = Field(None, description="Asset ISIN")
    name: str = Field(..., description="Asset display name")
    match_confidence: BRIMMatchConfidence = Field(..., description="How confident we are this is the right asset")


class BRIMAssetMapping(BaseModel):
    """
    Mapping from a fake asset ID to extracted info and candidate matches.

    The parser assigns fake IDs to assets it finds in the import file.
    This mapping tells the user what was extracted and suggests real assets.

    Note: selected_asset_id is auto-populated if exactly 1 candidate found.
    Frontend can override or must set if candidates is empty or multiple.
    """

    fake_asset_id: int = Field(..., description="Fake ID used in parsed transactions")
    extracted_symbol: Optional[str] = Field(None, description="Symbol extracted from file")
    extracted_isin: Optional[str] = Field(None, description="ISIN extracted from file")
    extracted_name: Optional[str] = Field(None, description="Name extracted from file")
    candidates: List[BRIMAssetCandidate] = Field(default_factory=list, description="Possible asset matches from database (empty = not found)")
    selected_asset_id: Optional[int] = Field(None, description="Auto-set if 1 candidate, else None (user must choose)")
    notices: List[BRIMAssetNotice] = Field(default_factory=list, description="Advisory notices propagated from the extracted asset (grouped/rendered by the frontend)")


# =============================================================================
# DUPLICATE DETECTION SCHEMAS
# =============================================================================


class BRIMDuplicateMatch(BaseModel):
    """
    An existing transaction in the database that may be a duplicate.
    """

    existing_tx_id: int = Field(..., description="ID of existing transaction in DB")
    tx_date: date = Field(..., description="Transaction date")
    tx_type: TransactionType = Field(..., description="Transaction type")
    tx_quantity: SafeDecimal = Field(..., description="Transaction quantity")
    tx_cash_amount: Optional[SafeDecimal] = Field(None, description="Cash amount if applicable")
    tx_cash_currency: Optional[str] = Field(None, description="Cash currency if applicable")
    tx_description: Optional[str] = Field(None, description="Transaction description")
    match_level: BRIMDuplicateLevel = Field(..., description="Duplicate confidence level")


class BRIMTXDuplicateCandidate(BaseModel):
    """
    A parsed transaction that may be a duplicate of existing transactions.
    """

    tx_row_index: int = Field(..., description="Row index in parsed transactions list")
    tx_parsed: TXCreateItem = Field(..., description="The parsed transaction")
    tx_existing_matches: List[BRIMDuplicateMatch] = Field(default_factory=list, description="Existing transactions that match")


class BRIMDuplicateReport(BaseModel):
    """
    Report of duplicate detection results for all parsed transactions.

    Transactions are categorized into:
    - tx_unique_indices: Definitely new (no matches found)
    - tx_possible_duplicates: Might be duplicates (key fields match, no description match)
    - tx_likely_duplicates: Very likely duplicates (key fields + description match)
    """

    tx_unique_indices: List[int] = Field(default_factory=list, description="Row indices of unique (non-duplicate) transactions")
    tx_possible_duplicates: List[BRIMTXDuplicateCandidate] = Field(default_factory=list, description="Transactions that might be duplicates (POSSIBLE level)")
    tx_likely_duplicates: List[BRIMTXDuplicateCandidate] = Field(default_factory=list, description="Transactions very likely to be duplicates (LIKELY level)")


# =============================================================================
# PARSE SCHEMAS (Preview)
# =============================================================================


class BRIMParseRequest(BaseModel):
    """
    Request to parse an uploaded file (preview mode).

    The parsed transactions are returned for user review before import.
    User can modify the transactions before sending to /import endpoint.

    Attributes:
        plugin_code: Plugin to use for parsing. Use 'auto' or omit for auto-detection.
        broker_id: Target broker ID for the transactions
    """

    plugin_code: str = Field(
        default="auto",
        description="Plugin code to use for parsing. Use 'auto' for automatic detection.",
    )
    broker_id: int = Field(..., gt=0, description="Target broker ID")


class BRIMDuplicateCheckRequest(BaseModel):
    """
    Request to re-run duplicate detection on transactions the user has already worked on.

    ``POST /files/{id}/parse`` returns a duplicate report computed on the transactions
    *as the plugin produced them*. That verdict is stale the moment the user changes
    anything: a row the plugin could only book as a cash withdrawal because it could not
    read the instrument is compared against cash movements, not against the purchase it
    actually is. Correcting it afterwards does not re-open the question.

    This request carries the transactions in their current state — after asset
    unification and after manual corrections — so the comparison runs on the data that
    will really be imported.

    Attributes:
        broker_id: Target broker the transactions will be imported into
        transactions: Transactions in their current, possibly user-edited state
        asset_mappings: Fake-id → real-asset resolutions, so the check is asset-aware
    """

    broker_id: int = Field(..., gt=0, description="Target broker ID")
    transactions: List[TXCreateItem] = Field(..., description="Transactions in their current state (post-correction)")
    asset_mappings: List[BRIMAssetMapping] = Field(default_factory=list, description="Fake asset id resolutions, used for asset-aware matching")


# =============================================================================
# VALIDATION ISSUE (structured parse error)
# =============================================================================


class BRIMValidationIssue(BaseModel):
    """Structured validation error from TXCreateItem construction during BRIM parse.

    Produced by ``BRIMProvider._create_transaction()`` when Pydantic validation
    fails (e.g. wrong sign on cash, missing required field).  The ``code`` and
    ``params`` fields are designed to be consumed by the frontend's
    ``resolveIssueMessage()`` — the same resolver used by the BulkModal — so
    the user sees a localized, human-friendly message instead of a raw traceback.

    Free-text plugin messages (unknown type, skipped row, invalid date, etc.)
    are NOT validation issues: they stay in ``warnings: List[str]``.
    """

    row: int = Field(..., description="Source file row number (1-based)")
    code: str = Field(..., description="Pydantic error type code (e.g. 'cashSignPositive', 'cashRequired')")
    message: str = Field(..., description="Human-readable error message (English fallback)")
    field: Optional[str] = Field(default=None, description="Field path that caused the error (e.g. 'cash.amount')")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Structured params for frontend i18n resolver (e.g. {type: 'DIVIDEND'})")
    context: Optional[str] = Field(default=None, description="Extra context from plugin (e.g. row description)")


# =============================================================================
# EVIDENCE + NOTICE (how a plugin explains what it did not understand)
# =============================================================================


class BRIMEvidence(StrictModel):
    """A navigable table of source data plus a human comment on what does not add up.

    A plugin message is a pair *data + interpretation*: the number that does not
    reconcile stays verifiable next to the sentence explaining it, so the reader
    does not have to take the plugin's word for it. Rendered by the frontend with
    the shared ``DataTable`` component (sorting/filters/pagination for free).

    Typical use: the source file row that could not be classified, the coupon row
    that supplied a bond nominal, or a computed comparison between the two.
    """

    title: str = Field(..., description="Short table caption (e.g. 'Riga di origine', 'Cedola corrispondente')")
    headers: List[str] = Field(default_factory=list, description="Column headers, in display order")
    rows: List[List[str]] = Field(default_factory=list, description="Row values as strings, aligned with headers")
    row_numbers: List[int] = Field(default_factory=list, description="Optional 1-based source-file line number per row (same length as rows, or empty)")
    comment: Optional[str] = Field(default=None, description="Human-readable comment explaining what does not add up")


class BRIMNotice(StrictModel):
    """A parser notice: severity, stable code, human message and optional evidence.

    Replaces the previous bare ``str`` warning. A ``field_validator`` in
    ``mode="before"`` coerces a plain string into ``BRIMNotice(severity="warning",
    ...)``, so every existing ``warnings.append("...")`` call across all plugins
    keeps working unchanged.

    Severity drives presentation only — both levels surface the confirmation modal
    when the user advances:
    - ``info``    — the plugin did something correct and non-obvious; explain it (blue)
    - ``warning`` — the plugin had to fall back or guess; look at it (amber)
    """

    severity: Literal["info", "warning"] = Field(default="warning", description="info = explanatory (blue); warning = needs attention (amber)")
    code: str = Field(default="generic", description="Machine-readable, i18n-stable notice code")
    message: str = Field(..., description="Human-readable message (plugin language)")
    evidence: List[BRIMEvidence] = Field(default_factory=list, description="Supporting source-data tables with comments")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Extra params for i18n interpolation")

    @field_validator("evidence", mode="before")
    @classmethod
    def _default_evidence(cls, value: Any) -> Any:
        return [] if value is None else value

    @classmethod
    def coerce(cls, value: Any) -> Any:
        """Accept a bare string as a legacy warning so existing plugins keep working."""
        if isinstance(value, str):
            return cls(severity="warning", code="legacy", message=value)
        return value


def _coerce_notices(value: Any) -> Any:
    """Normalise a ``List[str] | List[BRIMNotice]`` mix into notices (validator helper)."""
    if isinstance(value, list):
        return [BRIMNotice.coerce(item) for item in value]
    return value


# =============================================================================
# REPORT SETS (multi-file imports)
# =============================================================================


class BRIMSetShape(StrictModel):
    """What a report-set plugin can tell about its members without combining them.

    Used by the set preview: the segments covered by the files that define the
    window (e.g. the custody exports), the gaps between them that the other files
    prove, and plugin notices with stable codes.
    """

    segments: List[DateRangeModel] = Field(default_factory=list, description="Covered segments, in date order")
    gaps: List[DateRangeModel] = Field(default_factory=list, description="Proven gaps between segments")
    notices: List[BRIMNotice] = Field(default_factory=list, description="Plugin notices about the set")


class BRIMCombinedTable(BaseModel):
    """The combined table a report-set plugin builds from its members.

    Internal plugin-to-core object: the core writes it as the combined CSV
    (``write_combined_csv``), so the file format is the same for every plugin.
    Each row carries the verbatim source values plus the ``lf_*`` columns that
    explain it (kind, zone, reason, source).
    """

    headers: List[str] = Field(..., description="Column headers; must include lf_row_kind and lf_source")
    rows: List[List[str]] = Field(default_factory=list, description="Row values as strings, aligned with headers")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Combine summary, persisted in the combined file's sidecar")

    @model_validator(mode="after")
    def _check_shape(self) -> BRIMCombinedTable:
        if len(set(self.headers)) != len(self.headers):
            raise ValueError("combined table headers must be unique")
        missing = [header for header in COMBINED_REQUIRED_HEADERS if header not in self.headers]
        if missing:
            raise ValueError(f"combined table is missing required headers: {', '.join(missing)}")
        width = len(self.headers)
        for index, row in enumerate(self.rows):
            if len(row) != width:
                raise ValueError(f"combined table row {index} has {len(row)} values, expected {width}")
        return self


class BRIMTruthCash(StrictModel):
    """A cash balance the bank states, in one currency."""

    currency: str = Field(..., description="ISO 4217 currency code")
    amount: SafeDecimal = Field(..., description="Balance amount (can be negative)")

    @field_validator("currency", mode="before")
    @classmethod
    def _validate_currency(cls, value: Any) -> str:
        return Currency.validate_code(value)


class BRIMTruthPosition(StrictModel):
    """A position the bank's files prove: an exact quantity, or a minimum."""

    asset_id: int = Field(..., description="Fake asset ID from the parse (the wizard resolves it to a real asset)")
    quantity: SafeDecimal = Field(..., description="Quantity held (exact) or minimum quantity held (at_least)")
    exactness: Literal["exact", "at_least"] = Field(..., description="exact = the bank states the quantity; at_least = a lower bound the files prove")
    unit_cost: Optional[Currency] = Field(default=None, description="Per-unit cost, when the files prove it")


class BRIMAbsorbedRow(StrictModel):
    """One cash row a checkpoint summarises (value date, currency, amount), used to explain a difference."""

    as_of: date = Field(..., description="Value date of the row")
    currency: str = Field(..., description="ISO 4217 currency code")
    amount: SafeDecimal = Field(..., description="Signed cash amount of the row")
    label: Optional[str] = Field(default=None, description="Short description from the export")

    @field_validator("currency", mode="before")
    @classmethod
    def _validate_currency(cls, value: Any) -> str:
        return Currency.validate_code(value)


class BRIMAbsorbed(StrictModel):
    """Rows a checkpoint summarises instead of importing them one by one."""

    count: int = Field(default=0, ge=0, description="Number of summarised rows")
    cash: List[BRIMTruthCash] = Field(default_factory=list, description="Net cash of the summarised rows, per currency")
    rows: List[BRIMAbsorbedRow] = Field(default_factory=list, description="The summarised cash rows, to tell which ones LibreFolio already has")
    opening_cash: List[BRIMTruthCash] = Field(default_factory=list, description="Balance before the first summarised row (the start of the export)")


class BRIMCheckpoint(StrictModel):
    """What the bank states on the eve of a segment.

    The core compares it with what LibreFolio will know at that date and proposes
    the gap-fix corrections that close the difference.
    """

    as_of: date = Field(..., description="End of the day the truth refers to (the eve of the segment)")
    kind: Literal["opening", "gap"] = Field(..., description="opening = first checkpoint of the history; gap = closes a proven gap")
    cash: List[BRIMTruthCash] = Field(default_factory=list, description="Cash balances stated by the bank")
    positions: List[BRIMTruthPosition] = Field(default_factory=list, description="Positions proven by the files")
    absorbed: BRIMAbsorbed = Field(default_factory=BRIMAbsorbed, description="Rows this checkpoint summarises")
    evidence: List[BRIMEvidence] = Field(default_factory=list, description="Source rows backing the checkpoint")


class BRIMVerification(StrictModel):
    """A truth point that is only compared, never corrected (e.g. the end of the last segment)."""

    as_of: date = Field(..., description="End of the day the truth refers to")
    cash: List[BRIMTruthCash] = Field(default_factory=list, description="Cash balances stated by the bank")
    evidence: List[BRIMEvidence] = Field(default_factory=list, description="Source rows backing the verification")


class BRIMSetRequest(StrictModel):
    """Identifies one report set: the files uploaded together for a broker and recognised by a plugin."""

    broker_id: int = Field(..., gt=0, description="Target broker ID")
    plugin_code: str = Field(..., description="Report-set plugin code")
    batch_id: str = Field(..., description="Upload batch shared by the set's files")


class BRIMSetMemberInfo(StrictModel):
    """One file of a report set, as the preview sees it."""

    file_id: str = Field(..., description="UUID of the file")
    filename: str = Field(..., description="Original filename")
    role: Optional[str] = Field(default=None, description="Role recognised by the plugin, or None")
    rows: int = Field(default=0, ge=0, description="Number of data rows")
    coverage: List[BRIMCoverage] = Field(default_factory=list, description="Covered period per date axis")


class BRIMSetRoleStatus(StrictModel):
    """Whether a plugin role is covered by the set's files."""

    code: str = Field(..., description="Role code")
    required: bool = Field(..., description="The set needs this role")
    multiple: bool = Field(..., description="Several files of this role are allowed")
    status: Literal["present", "missing", "excess"] = Field(..., description="present, missing, or too many files for a single-file role")
    file_ids: List[str] = Field(default_factory=list, description="Files recognised with this role")


class BRIMSetMissing(StrictModel):
    """A required role the set lacks, with the period its file must cover when it can be computed."""

    role: str = Field(..., description="Missing role code")
    start: Optional[date] = Field(default=None, description="First day the missing export must cover")
    end: Optional[date] = Field(default=None, description="Last day the missing export must cover")


class BRIMSetPreview(StrictModel):
    """What a report set contains and whether it can be combined. Read-only."""

    broker_id: int = Field(..., description="Target broker ID")
    plugin_code: str = Field(..., description="Report-set plugin code")
    batch_id: str = Field(..., description="Upload batch of the set")
    members: List[BRIMSetMemberInfo] = Field(default_factory=list, description="Files of the set")
    roles: List[BRIMSetRoleStatus] = Field(default_factory=list, description="One entry per plugin role")
    missing: List[BRIMSetMissing] = Field(default_factory=list, description="Required roles without a file")
    segments: List[DateRangeModel] = Field(default_factory=list, description="Covered segments, in date order")
    gaps: List[DateRangeModel] = Field(default_factory=list, description="Proven gaps between segments")
    history_start: Optional[date] = Field(default=None, description="First day of the broker history already in LibreFolio")
    warnings: List[BRIMNotice] = Field(default_factory=list, description="Notices with stable codes for the UI")
    complete: bool = Field(default=False, description="True when the set can be combined")


class BRIMSetCombineResponse(StrictModel):
    """The combined file of a report set."""

    combined: BRIMFileInfo = Field(..., description="The combined file, parseable like any other file")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Combine summary (counts, window, checkpoints)")
    reused: bool = Field(default=False, description="True when an identical combined file already existed")


# =============================================================================
# FIELD_TODO (intentionally incomplete field in accepted TX)
# =============================================================================


class BRIMFieldTodo(StrictModel):
    """A field in an accepted transaction that the plugin left intentionally incomplete.

    Three output channels from a BRIM parse:
    - ``warnings: List[str]``                      — free-text: skipped rows, unknown types
    - ``validation_issues: List[BRIMValidationIssue]`` — TX rejected by Pydantic validation
    - ``field_todos: List[BRIMFieldTodo]``          — TX accepted, but field needs manual input

    Used for cases where the plugin cannot determine the correct value automatically
    (e.g. corporate actions where cost_basis_override requires user input).
    Severity ``blocker`` means Step 4 cannot proceed without resolution.
    """

    tx_index: int = Field(..., description="Index into transactions[] (0-based)")
    field: str = Field(..., description="TXCreateItem field name that needs input (e.g. 'cost_basis_override')")
    severity: Literal["blocker", "warning"] = Field(..., description="blocker = Step 4 gated; warning = informational")
    reason_code: str = Field(..., description="Machine-readable reason (e.g. 'stock_merger', 'spin_off', 'corporate_action')")
    message: str = Field(..., description="Human-readable fallback message (English)")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Extra params for i18n (e.g. {old_ticker, new_ticker})")
    evidence: List[BRIMEvidence] = Field(default_factory=list, description="Source-data tables backing this todo (e.g. the originating file row)")


# =============================================================================
# GAP-FIX (align LibreFolio with the bank's truth points)
# =============================================================================


class BRIMGapFixRequest(StrictModel):
    """What the wizard is about to import, and what the bank states: the gap-fix compares them."""

    broker_id: int = Field(..., gt=0, description="Target broker ID")
    plugin_code: str = Field(..., description="Plugin that produced the truth points")
    checkpoints: List[BRIMCheckpoint] = Field(default_factory=list, description="Truth points with real asset IDs")
    verifications: List[BRIMVerification] = Field(default_factory=list, description="Truth points that are only compared")
    selection: List[TXCreateItem] = Field(default_factory=list, description="Transactions the wizard is about to hand to the editor")
    pending_creates: List[TXCreateItem] = Field(default_factory=list, description="Unsaved rows already in the bulk editor")
    pending_delete_tx_ids: List[int] = Field(default_factory=list, description="Saved transactions the bulk editor is about to delete")


class BRIMGapFixCashRow(StrictModel):
    """Bank vs LibreFolio cash in one currency at a truth point."""

    currency: str = Field(..., description="ISO 4217 currency code")
    bank: SafeDecimal = Field(..., description="Balance stated by the bank")
    librefolio: SafeDecimal = Field(..., description="Balance LibreFolio will have")
    difference: SafeDecimal = Field(..., description="bank - librefolio")


class BRIMGapFixPositionRow(StrictModel):
    """Bank vs LibreFolio quantity of one asset at a checkpoint."""

    asset_id: int = Field(..., description="Real asset ID")
    exactness: Literal["exact", "at_least"] = Field(..., description="exact quantity or lower bound")
    bank: SafeDecimal = Field(..., description="Quantity stated or proven by the bank")
    librefolio: SafeDecimal = Field(..., description="Quantity LibreFolio will have")
    difference: SafeDecimal = Field(..., description="Quantity proposed (bank - librefolio; never negative for at_least)")


class BRIMGapFixExplanation(StrictModel):
    """Where a checkpoint difference comes from."""

    absorbed_count: int = Field(default=0, ge=0, description="Rows the checkpoint summarises")
    absorbed_missing_count: int = Field(default=0, ge=0, description="Summarised rows LibreFolio does not have")
    absorbed_missing_cash: List[BRIMTruthCash] = Field(default_factory=list, description="Net cash of the missing summarised rows")
    opening_cash: List[BRIMTruthCash] = Field(default_factory=list, description="Balance before the export (opening checkpoint only)")
    unexplained_cash: List[BRIMTruthCash] = Field(default_factory=list, description="Difference not explained by the rows above")
    notes: List[BRIMNotice] = Field(default_factory=list, description="Notices (e.g. an asset still unresolved)")


class BRIMGapFixCheckpointResult(StrictModel):
    """One checkpoint: the comparison and the gap-fix corrections that close it."""

    as_of: date = Field(..., description="End of the day of the checkpoint")
    kind: Literal["opening", "gap"] = Field(..., description="opening or gap")
    cash: List[BRIMGapFixCashRow] = Field(default_factory=list, description="Cash comparison per currency")
    positions: List[BRIMGapFixPositionRow] = Field(default_factory=list, description="Position comparison per asset")
    proposals: List[TXCreateItem] = Field(default_factory=list, description="Gap-fix corrections, tagged gap_fix")
    todos: List[BRIMFieldTodo] = Field(default_factory=list, description="Fields to complete on the proposals (tx_index into proposals)")
    explanation: BRIMGapFixExplanation = Field(default_factory=BRIMGapFixExplanation, description="Where the difference comes from")


class BRIMGapFixVerificationResult(StrictModel):
    """A truth point that is only compared."""

    as_of: date = Field(..., description="End of the day of the verification")
    ok: bool = Field(..., description="True when every currency matches within 0.01")
    cash: List[BRIMGapFixCashRow] = Field(default_factory=list, description="Cash comparison per currency")


class BRIMGapFixResponse(StrictModel):
    """The gap-fix of one broker: checkpoints in date order, then verifications."""

    checkpoints: List[BRIMGapFixCheckpointResult] = Field(default_factory=list, description="Checkpoint results, in date order")
    verifications: List[BRIMGapFixVerificationResult] = Field(default_factory=list, description="Verification results, in date order")


class BRIMParseResponse(StrictModel):
    """
    Response from parsing a broker report file.

    Contains:
    - Parsed transactions with fake asset IDs where applicable
    - Asset mappings: fake ID → candidate real assets from DB
    - Duplicate report: which transactions might already exist
    - Warnings: skipped rows, ambiguous data, etc.

    Frontend workflow:
    1. Show transactions with asset mappings for user to resolve
    2. Show duplicate report for user to decide what to import
    3. User edits, selects assets, unchecks duplicates
    4. Frontend replaces fake IDs with selected real IDs
    5. Frontend sends final transaction list to /import endpoint
    """

    file_id: str = Field(..., description="UUID of the parsed file")
    plugin_code: str = Field(..., description="Plugin used for parsing")
    broker_id: int = Field(..., gt=0, description="Target broker ID")
    transactions: List[TXCreateItem] = Field(default_factory=list, description="Parsed transactions (may have fake asset IDs)")
    asset_mappings: List[BRIMAssetMapping] = Field(default_factory=list, description="Fake asset ID → candidate real assets mapping")
    duplicates: Optional[BRIMDuplicateReport] = Field(default=None, description="Duplicate detection results")
    warnings: List[BRIMNotice] = Field(default_factory=list, description="Parser notices (info/warning) with optional source-data evidence")
    validation_issues: List[BRIMValidationIssue] = Field(default_factory=list, description="Structured validation errors from TXCreateItem construction")
    field_todos: List[BRIMFieldTodo] = Field(default_factory=list, description="Fields in accepted transactions that require manual user input")
    checkpoints: List[BRIMCheckpoint] = Field(default_factory=list, description="Report sets: truth points to compare with LibreFolio (gap-fix)")
    verifications: List[BRIMVerification] = Field(default_factory=list, description="Report sets: truth points that are only compared")
    history_start: Optional[date] = Field(default=None, description="Report sets: first day of the broker history already in LibreFolio; earlier rows are already represented")

    @field_validator("warnings", mode="before")
    @classmethod
    def _coerce_warnings(cls, value: Any) -> Any:
        return _coerce_notices(value)


# =============================================================================
# PARSE OUTPUT (plugin return value)
# =============================================================================


class BRIMParseOutput(BaseModel):
    """Return type of ``BRIMProvider.parse()``.

    Plugins must populate ``transactions`` and ``extracted_assets``.
    ``warnings`` is optional (default empty list).

    The plugin is a pure parser: it does NOT emit asset-level events.
    Dividends as cash movements become ``TXCreateItem`` of type DIVIDEND;
    dividends as asset metadata (per-share, market-wide) are populated by
    the asset source providers (yfinance/JustETF/...) or manually by the
    user from the asset UI, not by BRIM plugins.
    """

    transactions: List[TXCreateItem] = Field(default_factory=list)
    warnings: List[BRIMNotice] = Field(default_factory=list)
    validation_issues: List[BRIMValidationIssue] = Field(default_factory=list)
    field_todos: List[BRIMFieldTodo] = Field(default_factory=list)
    extracted_assets: Dict[int, BRIMExtractedAssetInfo] = Field(default_factory=dict)
    checkpoints: List[BRIMCheckpoint] = Field(default_factory=list)
    verifications: List[BRIMVerification] = Field(default_factory=list)

    @field_validator("warnings", mode="before")
    @classmethod
    def _coerce_warnings(cls, value: Any) -> Any:
        return _coerce_notices(value)


# NOTE: No atomic commit schema / endpoint.
# After parsing, the client should:
# 1. Resolve fake asset IDs to real asset IDs (Staging Modal)
# 2. Submit transactions to POST /transactions/validate and /transactions/commit
#    (TransactionService.execute_batch, the standard batch endpoints).
# 3. The BRIM file status auto-transitions to PARSED/FAILED right after
#    the /parse call; no additional state change is needed after commit.


class BRIMAssetCandidatesRequest(BaseModel):
    """Request body for POST /brokers/import/asset-candidates."""

    extracted_symbol: Optional[str] = None
    extracted_isin: Optional[str] = None
    extracted_name: Optional[str] = None
