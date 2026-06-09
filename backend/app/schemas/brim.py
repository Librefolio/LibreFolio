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

from pydantic import BaseModel, ConfigDict, Field

from backend.app.db.models import TransactionType
from backend.app.schemas.common import SafeDecimal
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


class BRIMFileInfo(BaseModel):
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


# =============================================================================
# PLUGIN SCHEMAS
# =============================================================================


class BRIMExtractedAssetInfo(BaseModel):
    """
    Extracted asset information from a broker report row.

    Used by plugins to classify and identify assets found in imported files.
    All fields are optional as not all reports contain all identifiers.

    Attributes:
        extracted_symbol: Ticker/symbol extracted from report (e.g., "AAPL", "VWCE")
        extracted_isin: ISIN code extracted from report (e.g., "US0378331005")
        extracted_name: Asset name/description extracted from report
    """

    model_config = ConfigDict(extra="forbid")

    extracted_symbol: Optional[str] = Field(default=None, description="Ticker/symbol from report")
    extracted_isin: Optional[str] = Field(default=None, description="ISIN code from report")
    extracted_name: Optional[str] = Field(default=None, description="Asset name/description from report")


# =============================================================================
# PLUGIN PREVIEW METADATA
# =============================================================================


class BRIMPreviewColumn(BaseModel):
    """Column metadata for the Staging Modal preview table.

    The frontend uses this to render a dynamic table per plugin with
    appropriate widths/alignments and i18n labels.
    """

    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., description="Field key in the TX / event row")
    label: str = Field(..., description="Column label (frontend passes through i18n)")
    type: Literal["text", "number", "date", "currency", "enum", "boolean"] = Field(..., description="Data type of the column")
    width: Optional[str] = Field(None, description="CSS width (e.g., '120px', '10%')")
    align: Optional[Literal["left", "center", "right"]] = Field(None, description="Text alignment")


class BRIMPluginInfo(BaseModel):
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
        preview_columns: Columns metadata for the Staging Modal preview
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
    preview_columns: List[BRIMPreviewColumn] = Field(default_factory=list, description="Columns metadata for the Staging Modal preview table")
    detection_priority: int = Field(100, description="Priority for auto-detection (higher = checked first). 100+ broker-specific, 50-99 semi-generic, 0-49 fallbacks")


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

    model_config = ConfigDict(extra="forbid")

    row: int = Field(..., description="Source file row number (1-based)")
    code: str = Field(..., description="Pydantic error type code (e.g. 'cashSignPositive', 'cashRequired')")
    message: str = Field(..., description="Human-readable error message (English fallback)")
    field: Optional[str] = Field(default=None, description="Field path that caused the error (e.g. 'cash.amount')")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Structured params for frontend i18n resolver (e.g. {type: 'DIVIDEND'})")
    context: Optional[str] = Field(default=None, description="Extra context from plugin (e.g. row description)")


class BRIMParseResponse(BaseModel):
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
    warnings: List[str] = Field(default_factory=list, description="Parser warnings (skipped rows, ambiguous data, etc.)")
    validation_issues: List[BRIMValidationIssue] = Field(default_factory=list, description="Structured validation errors from TXCreateItem construction")


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

    model_config = ConfigDict(extra="forbid")

    transactions: List[TXCreateItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validation_issues: List[BRIMValidationIssue] = Field(default_factory=list)
    extracted_assets: Dict[int, BRIMExtractedAssetInfo] = Field(default_factory=dict)


# NOTE: No atomic commit schema / endpoint.
# After parsing, the client should:
# 1. Resolve fake asset IDs to real asset IDs (Staging Modal)
# 2. Submit transactions to POST /brokers/{broker_id}/transactions/bulk
#    (standard endpoint, atomic per-broker — see Phase 7 Part 3).
# 3. The BRIM file status auto-transitions to PARSED/FAILED right after
#    the /parse call; no additional state change is needed after commit.
