"""
Broker Report Import Manager (BRIM) - Provider base class, registry, and service.

This module provides:
- BRIMProvider: Abstract base class for broker report import plugins
- BRIMProviderRegistry: Registry for auto-discovery of plugins
- File storage functions for uploaded broker reports
- Service functions for parsing coordination

**Architecture:**
- Plugins are auto-discovered from `brim_providers/` folder
- File storage uses UUID-based naming for security (no original paths exposed)
- Parsing returns TXCreateItem DTOs for user review
- Final import uses POST /transactions (standard endpoint)

**File Storage Structure:**
    backend/data/broker_reports/
    ├── uploaded/          # Files awaiting processing
    │   ├── {uuid}.csv     # Data file with original extension
    │   └── {uuid}.json    # Metadata sidecar
    ├── parsed/            # Successfully parsed files (ready for review/import)
    └── failed/            # Failed files with error details

**Flow:**
    UPLOADED → parse → PARSED (success) or FAILED (error)
    After parsing, the user reviews and imports via POST /transactions.
"""
from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

import structlog
from sqlalchemy import select, and_

from backend.app.config import PROJECT_ROOT
from backend.app.db.models import Transaction
from backend.app.schemas.assets import FAAinfoFiltersRequest
from backend.app.schemas.brim import BRIMAssetCandidate, BRIMMatchConfidence
from backend.app.schemas.brim import (
    BRIMDuplicateReport, BRIMDuplicateMatch, BRIMDuplicateLevel,
    BRIMTXDuplicateCandidate, is_fake_asset_id
    )
from backend.app.schemas.brim import (
    BRIMFileInfo,
    BRIMFileStatus,
    BRIMPluginInfo,
    BRIMAssetMapping,
    BRIMExtractedAssetInfo,
    )
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.asset_source import AssetCRUDService
from backend.app.services.provider_registry import BRIMProviderRegistry
from backend.app.utils.datetime_utils import utcnow

logger = structlog.get_logger(__name__)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class BRIMParseError(Exception):
    """Raised when a file cannot be parsed by a plugin."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


# =============================================================================
# ABSTRACT BASE CLASS
# =============================================================================

class BRIMProvider(ABC):
    """
    Abstract base class for broker report import plugins.

    Each plugin is responsible for parsing a specific broker's file format
    and converting it to a list of TXCreateItem DTOs.

    Plugins are auto-discovered from `brim_providers/` folder when the
    registry is first accessed.

    **Plugin Responsibilities:**
    - Parse broker-specific file formats (CSV, XLSX, PDF, etc.)
    - Convert parsed data to standard TXCreateItem DTOs
    - Return warnings for skipped/ambiguous rows
    - Handle date format variations
    - Map broker-specific transaction types to TransactionType enum

    **Core Responsibilities (not in plugin):**
    - File storage and management
    - Final import via TransactionService.create_bulk()
    - Database persistence

    Example:
        @register_provider(BRIMProviderRegistry)
        class DirectaCSVProvider(BRIMProvider):
            @property
            def provider_code(self) -> str:
                return "directa_csv"
            # ... implement other methods
    """

    @property
    @abstractmethod
    def provider_code(self) -> str:
        """
        Unique plugin identifier.

        Used in database, API, and for plugin selection.
        Must be lowercase alphanumeric with underscores.

        Examples: 'broker_generic_csv', 'directa_csv', 'degiro_xlsx'
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Human-readable plugin name for UI display.

        Examples: 'Generic CSV', 'Directa CSV Export', 'Degiro XLSX'
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Plugin description for UI display.

        Should explain what file formats are supported and any limitations.
        """
        pass

    @property
    def supported_extensions(self) -> List[str]:
        """
        List of supported file extensions (lowercase, with dot).

        Default: ['.csv']
        Override if plugin supports other formats.

        Examples: ['.csv'], ['.csv', '.xlsx'], ['.pdf']
        """
        return ['.csv']

    @property
    def detection_priority(self) -> int:
        """
        Priority for auto-detection (higher = checked first).

        Used when iterating plugins to find one that can parse a file.
        Higher priority plugins are checked before lower priority ones.

        Suggested ranges:
        - 100+: Broker-specific plugins with unique headers
        - 50-99: Semi-generic plugins
        - 0-49: Generic fallback plugins (e.g., broker_generic_csv)

        Default: 100 (broker-specific plugins)
        """
        return 100

    @staticmethod
    def _read_file_head(file_path: Path, num_lines: int = 15) -> str:
        """
        Read the first N lines of a file with encoding fallback.

        Tries multiple encodings to handle different file formats:
        - utf-8-sig (UTF-8 with BOM, common in Windows exports)
        - utf-8
        - latin-1 (ISO-8859-1)
        - cp1252 (Windows Western European)

        Args:
            file_path: Path to the file
            num_lines: Number of lines to read (default 15)

        Returns:
            String containing the first N lines, empty string on error
        """
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    lines = []
                    for _ in range(num_lines):
                        line = f.readline()
                        if not line:
                            break
                        lines.append(line)
                    return ''.join(lines)
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception:
                return ''

        return ''

    @staticmethod
    def _detect_separator(content: str) -> str:
        """
        Auto-detect CSV separator from file content.

        Checks for common separators: semicolon, comma, tab.
        Returns the most likely separator based on frequency in first line.

        Args:
            content: File content (first few lines)

        Returns:
            Detected separator character (default: ',')
        """
        if not content:
            return ','

        first_line = content.split('\n')[0] if '\n' in content else content

        # Count occurrences of each separator
        separators = {
            ';': first_line.count(';'),
            ',': first_line.count(','),
            '\t': first_line.count('\t'),
            }

        # Return the one with most occurrences (minimum 1)
        best = max(separators, key=separators.get)
        return best if separators[best] > 0 else ','

    @property
    def icon_url(self) -> Optional[str]:
        """
        URL to the broker's icon/logo.

        Override in subclass to provide broker-specific icon.
        Can be:
        - Absolute URL (https://...)
        - Relative path served by backend (e.g., /static/icons/broker_xxx.png)
        - None if no icon available

        Default: None
        """
        return None

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """
        Check if this plugin can parse the given file.

        Should perform a quick check (e.g., extension, header row)
        without full parsing. Used to determine compatible plugins
        for a file.

        Args:
            file_path: Path to the file to check

        Returns:
            True if this plugin can likely parse the file
        """
        pass

    @abstractmethod
    def parse(
        self,
        file_path: Path,
        broker_id: int
        ) -> Tuple[List[TXCreateItem], List[str], Dict[int, "BRIMExtractedAssetInfo"]]:
        """
        Parse file and return transactions, warnings, and extracted asset info.

        **Plugin Responsibility:**
        - Read the broker-specific file format
        - Create TXCreateItem DTOs with fake_asset_ids for asset-linked transactions
        - Extract asset identifiers (symbol, ISIN, name) from the file
        - Group same-asset transactions under the same fake_asset_id
        - Collect warnings for skipped/problematic rows

        **Core Responsibility (NOT plugin):**
        - Search DB for asset candidates using extracted info
        - Map fake_asset_ids to real asset_ids
        - Detect duplicate transactions

        Args:
            file_path: Path to the file to parse
            broker_id: Target broker ID for all transactions

        Returns:
            Tuple of (transactions, warnings, extracted_assets)
            - transactions: List of TXCreateItem DTOs (with fake asset IDs)
            - warnings: List of warning messages (skipped rows, etc.)
            - extracted_assets: Dict mapping fake_asset_id -> BRIMExtractedAssetInfo

        Raises:
            BRIMParseError: If file cannot be parsed
        """
        pass

    @property
    def test_file_pattern(self) -> Optional[str]:
        """
        Filename contain pattern for auto-detection tests.
        Using for test with backend/app/services/brim_providers/sample_reports/* files

        Override this to specify what filename substring should auto-detect
        to this plugin. Used only for testing purposes.

        Example: "directa" for broker_directa plugin
        Returns None if no test pattern (e.g., generic fallback plugin).
        """
        return None

    def to_plugin_info(self) -> BRIMPluginInfo:
        """Convert provider to BRIMPluginInfo DTO."""
        return BRIMPluginInfo(
            code=self.provider_code,
            name=self.provider_name,
            description=self.description,
            supported_extensions=self.supported_extensions,
            icon_url=self.icon_url
            )


# =============================================================================
# FILE STORAGE
# =============================================================================

# Storage directory: backend/data/broker_reports/
BROKER_REPORTS_DIR = PROJECT_ROOT / "backend" / "data" / "broker_reports"


def _ensure_dirs() -> None:
    """Create storage directories if they don't exist."""
    for status in BRIMFileStatus:
        (BROKER_REPORTS_DIR / status.value).mkdir(parents=True, exist_ok=True)


def _get_folder_for_status(status: BRIMFileStatus) -> Path:
    """Get the folder path for a given status."""
    return BROKER_REPORTS_DIR / status.value


def save_uploaded_file(content: bytes, original_filename: str) -> BRIMFileInfo:
    """
    Save an uploaded file to the 'uploaded' folder.

    Process:
    1. Generate a UUID for the file (security: never expose original filename in path)
    2. Determine file extension from original filename
    3. Write file content to: uploaded/{uuid}.{ext}
    4. Query BRIMProviderRegistry.get_compatible_plugins() to detect which plugins can parse
    5. Create metadata JSON sidecar: uploaded/{uuid}.json
    6. Return BRIMFileInfo with all metadata

    Args:
        content: Raw file bytes from upload
        original_filename: Original filename (e.g., "report_2025.csv")

    Returns:
        BRIMFileInfo with file_id, compatible plugins, etc.
    """
    _ensure_dirs()

    # Generate UUID and determine extension
    file_id = str(uuid.uuid4())
    ext = Path(original_filename).suffix.lower() or ".dat"

    # Write file to uploaded folder
    uploaded_dir = BROKER_REPORTS_DIR / "uploaded"
    file_path = uploaded_dir / f"{file_id}{ext}"
    file_path.write_bytes(content)

    # Detect compatible plugins
    compatible_plugins = BRIMProviderRegistry.get_compatible_plugins(file_path)

    # Create metadata
    now = utcnow()
    metadata = {
        "file_id": file_id,
        "filename": original_filename,
        "extension": ext,
        "size_bytes": len(content),
        "status": BRIMFileStatus.UPLOADED.value,
        "uploaded_at": now.isoformat(),
        "processed_at": None,
        "compatible_plugins": compatible_plugins,
        "error_message": None
        }

    # Write metadata JSON
    meta_path = uploaded_dir / f"{file_id}.json"
    meta_path.write_text(json.dumps(metadata, indent=2))

    logger.info(
        "Saved uploaded file",
        file_id=file_id,
        original_filename=original_filename,
        size_bytes=len(content),
        compatible_plugins=compatible_plugins
        )

    return BRIMFileInfo(
        file_id=file_id,
        filename=original_filename,
        size_bytes=len(content),
        status=BRIMFileStatus.UPLOADED,
        uploaded_at=now,
        compatible_plugins=compatible_plugins
        )


def list_files(status: Optional[BRIMFileStatus] = None) -> List[BRIMFileInfo]:
    """
    List all files, optionally filtered by status.

    Process:
    1. Determine which folders to scan (one folder per status, or all if status=None)
    2. For each folder, glob all *.json metadata files
    3. Parse each JSON into BRIMFileInfo
    4. Return sorted list (most recent first by uploaded_at)

    Args:
        status: Optional filter (UPLOADED, IMPORTED, FAILED)

    Returns:
        List of BRIMFileInfo objects, sorted by uploaded_at (newest first)
    """
    _ensure_dirs()

    # Determine folders to scan
    if status:
        folders = [BROKER_REPORTS_DIR / status.value]
    else:
        folders = [
            BROKER_REPORTS_DIR / s.value
            for s in BRIMFileStatus
            ]

    files = []
    for folder in folders:
        if not folder.exists():
            continue
        for meta_path in folder.glob("*.json"):
            try:
                metadata = json.loads(meta_path.read_text())
                files.append(BRIMFileInfo(
                    file_id=metadata["file_id"],
                    filename=metadata["filename"],
                    size_bytes=metadata["size_bytes"],
                    status=BRIMFileStatus(metadata["status"]),
                    uploaded_at=datetime.fromisoformat(metadata["uploaded_at"]),
                    processed_at=(
                        datetime.fromisoformat(metadata["processed_at"])
                        if metadata.get("processed_at")
                        else None
                    ),
                    compatible_plugins=metadata.get("compatible_plugins", []),
                    error_message=metadata.get("error_message")
                    ))
            except Exception as e:
                logger.warning(
                    "Error reading file metadata",
                    meta_path=str(meta_path),
                    error=str(e)
                    )

    # Sort by uploaded_at, newest first
    files.sort(key=lambda f: f.uploaded_at, reverse=True)
    return files


def get_file_info(file_id: str) -> Optional[BRIMFileInfo]:
    """
    Get metadata for a specific file by its UUID.

    Process:
    1. Search for {file_id}.json in all three folders (uploaded, imported, failed)
    2. Return first match, or None if not found

    Args:
        file_id: UUID of the file

    Returns:
        BRIMFileInfo or None if not found
    """
    _ensure_dirs()

    for status in BRIMFileStatus:
        meta_path = BROKER_REPORTS_DIR / status.value / f"{file_id}.json"
        if meta_path.exists():
            try:
                metadata = json.loads(meta_path.read_text())
                return BRIMFileInfo(
                    file_id=metadata["file_id"],
                    filename=metadata["filename"],
                    size_bytes=metadata["size_bytes"],
                    status=BRIMFileStatus(metadata["status"]),
                    uploaded_at=datetime.fromisoformat(metadata["uploaded_at"]),
                    processed_at=(
                        datetime.fromisoformat(metadata["processed_at"])
                        if metadata.get("processed_at")
                        else None
                    ),
                    compatible_plugins=metadata.get("compatible_plugins", []),
                    error_message=metadata.get("error_message")
                    )
            except Exception as e:
                logger.warning(
                    "Error reading file metadata",
                    file_id=file_id,
                    error=str(e)
                    )
                return None
    return None


def get_file_path(file_id: str) -> Optional[Path]:
    """
    Get the actual filesystem path to a file for parsing.

    Process:
    1. Call get_file_info() to find the file and its current status
    2. Extract original extension from the stored metadata
    3. Construct path: {status_folder}/{file_id}.{ext}
    4. Verify file exists, return Path or None

    Args:
        file_id: UUID of the file

    Returns:
        Path object or None if file not found
    """
    file_info = get_file_info(file_id)
    if not file_info:
        return None

    # Get extension from filename
    ext = Path(file_info.filename).suffix.lower() or ".dat"

    # Construct path
    folder = BROKER_REPORTS_DIR / file_info.status.value
    file_path = folder / f"{file_id}{ext}"

    if file_path.exists():
        return file_path
    return None


def delete_file(file_id: str) -> bool:
    """
    Delete a file and its metadata.

    Process:
    1. Find file location via get_file_info()
    2. Delete both the data file and .json metadata
    3. Return True if deleted, False if not found

    Args:
        file_id: UUID of the file

    Returns:
        True if deleted, False if not found
    """
    file_info = get_file_info(file_id)
    if not file_info:
        return False

    # Get extension and folder
    ext = Path(file_info.filename).suffix.lower() or ".dat"
    folder = BROKER_REPORTS_DIR / file_info.status.value

    # Delete data file
    file_path = folder / f"{file_id}{ext}"
    if file_path.exists():
        file_path.unlink()

    # Delete metadata
    meta_path = folder / f"{file_id}.json"
    if meta_path.exists():
        meta_path.unlink()

    logger.info("Deleted file", file_id=file_id)
    return True


def move_to_parsed(file_id: str) -> bool:
    """
    Move a successfully parsed file from 'uploaded' to 'parsed'.

    Process:
    1. Get current file info and verify status is UPLOADED
    2. Move data file: uploaded/{id}.ext → parsed/{id}.ext
    3. Update metadata: status=PARSED, processed_at=now()
    4. Write updated metadata to parsed/{id}.json
    5. Delete old metadata from uploaded/

    Args:
        file_id: UUID of the file

    Returns:
        True if moved, False if not found or wrong status
    """
    return _move_file(file_id, BRIMFileStatus.PARSED)


def move_to_failed(file_id: str, error_message: str) -> bool:
    """
    Move a failed file from 'uploaded' to 'failed' with error details.

    Process:
    1. Get current file info and verify status is UPLOADED
    2. Move data file: uploaded/{id}.ext → failed/{id}.ext
    3. Update metadata: status=FAILED, processed_at=now(), error_message=error
    4. Write updated metadata to failed/{id}.json
    5. Delete old metadata from uploaded/

    Args:
        file_id: UUID of the file
        error_message: Error description to store

    Returns:
        True if moved, False if not found or wrong status
    """
    return _move_file(file_id, BRIMFileStatus.FAILED, error_message)


def _move_file(
    file_id: str,
    target_status: BRIMFileStatus,
    error_message: Optional[str] = None
    ) -> bool:
    """
    Internal helper to move a file to a different status folder.

    Args:
        file_id: UUID of the file
        target_status: Target status (IMPORTED or FAILED)
        error_message: Error message (only for FAILED status)

    Returns:
        True if moved, False if not found or wrong status
    """
    _ensure_dirs()

    # Get current file info
    file_info = get_file_info(file_id)
    if not file_info:
        return False

    # Only move from UPLOADED status
    if file_info.status != BRIMFileStatus.UPLOADED:
        logger.warning(
            "Cannot move file: not in UPLOADED status",
            file_id=file_id,
            current_status=file_info.status.value
            )
        return False

    # Get extension
    ext = Path(file_info.filename).suffix.lower() or ".dat"

    # Source paths
    src_folder = BROKER_REPORTS_DIR / BRIMFileStatus.UPLOADED.value
    src_file = src_folder / f"{file_id}{ext}"
    src_meta = src_folder / f"{file_id}.json"

    # Target paths
    dst_folder = BROKER_REPORTS_DIR / target_status.value
    dst_file = dst_folder / f"{file_id}{ext}"
    dst_meta = dst_folder / f"{file_id}.json"

    # Move data file
    if src_file.exists():
        src_file.rename(dst_file)

    # Update and move metadata
    if src_meta.exists():
        metadata = json.loads(src_meta.read_text())
        metadata["status"] = target_status.value
        metadata["processed_at"] = utcnow().isoformat()
        if error_message:
            metadata["error_message"] = error_message
        dst_meta.write_text(json.dumps(metadata, indent=2))
        src_meta.unlink()

    logger.info(
        "Moved file",
        file_id=file_id,
        from_status=BRIMFileStatus.UPLOADED.value,
        to_status=target_status.value
        )
    return True


# =============================================================================
# SERVICE FUNCTIONS
# =============================================================================

def parse_file(
    file_id: str,
    plugin_code: str,
    broker_id: int
    ) -> Tuple[List[TXCreateItem], List[str], Dict[int, BRIMExtractedAssetInfo]]:
    """
    Parse a file using the specified plugin (preview only, no DB persistence).

    Process:
    1. Call get_file_path(file_id) to get actual file location
       - Raise FileNotFoundError if file doesn't exist
    2. Call BRIMProviderRegistry.get_provider_instance(plugin_code)
       - Raise ValueError if plugin not found
    3. Call plugin.can_parse(file_path)
       - Raise ValueError if plugin cannot parse this file type
    4. Call plugin.parse(file_path, broker_id)
       - Returns Tuple[List[TXCreateItem], List[str], Dict[int, BRIMExtractedAssetInfo]]
       - Transactions are standard DTOs ready for TransactionService
       - Warnings include skipped rows, ambiguous data, etc.
       - Extracted assets is the mapping fake_id -> BRIMExtractedAssetInfo
    5. Return (transactions, warnings, extracted_assets)

    IMPORTANT: This function does NOT persist anything to DB.
    It's used for preview so user can review/edit before confirming.

    Args:
        file_id: UUID of the uploaded file
        plugin_code: Provider code (e.g., "broker_generic_csv")
        broker_id: Target broker ID for the transactions

    Returns:
        Tuple of (transactions, warnings, extracted_assets)
        - transactions: List[TXCreateItem] with fake asset IDs where applicable
        - warnings: List[str] parser warnings
        - extracted_assets: Dict[fake_id -> {extracted_symbol, extracted_isin, extracted_name}]

    Raises:
        FileNotFoundError: File not found
        ValueError: Plugin not found or cannot parse file
        BRIMParseError: Plugin-specific parsing error
    """
    # Get file path
    file_path = get_file_path(file_id)
    if not file_path:
        raise FileNotFoundError(f"File not found: {file_id}")

    # Get plugin instance
    plugin = BRIMProviderRegistry.get_provider_instance(plugin_code)
    if not plugin:
        raise ValueError(f"Plugin not found: {plugin_code}")

    # Verify plugin can parse this file
    if not plugin.can_parse(file_path):
        raise ValueError(
            f"Plugin '{plugin_code}' cannot parse file '{file_path.name}'"
            )

    # Parse file
    logger.info(
        "Parsing file with plugin",
        file_id=file_id,
        plugin_code=plugin_code,
        broker_id=broker_id
        )

    # Plugin returns (transactions, warnings, extracted_assets)
    transactions, warnings, extracted_assets = plugin.parse(file_path, broker_id)

    logger.info(
        "File parsed successfully",
        file_id=file_id,
        plugin_code=plugin_code,
        transaction_count=len(transactions),
        warning_count=len(warnings),
        extracted_asset_count=len(extracted_assets)
        )

    return transactions, warnings, extracted_assets


# =============================================================================
# ASSET CANDIDATE SEARCH
# =============================================================================

async def search_asset_candidates(
    session,
    extracted_symbol: Optional[str],
    extracted_isin: Optional[str],
    extracted_name: Optional[str]
    ) -> Tuple[List, Optional[int]]:
    """
    Search for asset candidates in the database.

    Uses FAAinfoFiltersRequest to search directly on Asset identifier columns.
    Returns candidates with confidence levels and auto-selects if exactly 1 match.

    Priority:
    1. ISIN exact match → EXACT confidence (Asset.identifier_isin)
    2. Symbol exact match → MEDIUM confidence (Asset.identifier_ticker)
    3. Name partial match → LOW confidence (display_name search)

    Args:
        session: AsyncSession for database queries
        extracted_symbol: Symbol/ticker from import file
        extracted_isin: ISIN from import file
        extracted_name: Asset name from import file

    Returns:
        Tuple of (candidates list, auto_selected_id)
        - If exactly 1 candidate: auto_selected_id = that asset's ID
        - Otherwise: auto_selected_id = None
    """
    candidates = []

    # Priority 1: ISIN exact match (EXACT confidence)
    if extracted_isin:
        results = await AssetCRUDService.list_assets(
            filters=FAAinfoFiltersRequest(isin=extracted_isin),
            session=session
            )
        for asset in results:
            candidates.append(BRIMAssetCandidate(
                asset_id=asset.id,
                symbol=asset.identifier_ticker,
                isin=asset.identifier_isin,
                name=asset.display_name,
                match_confidence=BRIMMatchConfidence.EXACT
                ))

    # Priority 2: Symbol exact match (MEDIUM confidence)
    if extracted_symbol and not candidates:
        results = await AssetCRUDService.list_assets(
            filters=FAAinfoFiltersRequest(ticker=extracted_symbol),
            session=session
            )
        for asset in results:
            candidates.append(BRIMAssetCandidate(
                asset_id=asset.id,
                symbol=asset.identifier_ticker,
                isin=asset.identifier_isin,
                name=asset.display_name,
                match_confidence=BRIMMatchConfidence.MEDIUM
                ))

    # Priority 3: Name partial match (LOW confidence)
    if extracted_name and not candidates:
        # Try identifier partial match first
        results = await AssetCRUDService.list_assets(
            filters=FAAinfoFiltersRequest(identifier_contains=extracted_name),
            session=session
            )
        if not results:
            # Fall back to display_name search
            results = await AssetCRUDService.list_assets(
                filters=FAAinfoFiltersRequest(search=extracted_name),
                session=session
                )
        for asset in results:
            candidates.append(BRIMAssetCandidate(
                asset_id=asset.id,
                symbol=asset.identifier_ticker,
                isin=asset.identifier_isin,
                name=asset.display_name,
                match_confidence=BRIMMatchConfidence.LOW
                ))

    # Auto-select if exactly 1 candidate found
    auto_selected = candidates[0].asset_id if len(candidates) == 1 else None

    return candidates, auto_selected


# =============================================================================
# DUPLICATE DETECTION
# =============================================================================

async def detect_tx_duplicates(
    transactions: List[TXCreateItem],
    broker_id: int,
    session,
    asset_mappings: Optional[List[BRIMAssetMapping]] = None
    ) -> "BRIMDuplicateReport":
    """
    Detect potential duplicate transactions in the database.

    For each parsed transaction, queries the DB for existing transactions with:
    - Same broker_id (scoped to broker)
    - Same type
    - Same date
    - Same quantity (within tolerance for decimals)
    - Same cash amount and currency (if present)
    - Same asset_id (only if asset was auto-resolved with 1 candidate)

    Match levels (ascending confidence):
    - POSSIBLE: key fields match, asset not resolved
    - POSSIBLE_WITH_ASSET: key fields match, asset auto-resolved and matches
    - LIKELY: key fields + description match, asset not resolved
    - LIKELY_WITH_ASSET: key fields + description match, asset auto-resolved

    Args:
        transactions: List of parsed TXCreateItem
        broker_id: Target broker ID
        session: AsyncSession for database queries
        asset_mappings: Optional list of BRIMAssetMapping for asset resolution

    Returns:
        BRIMDuplicateReport with categorized transactions
    """
    tx_unique_indices = []
    tx_possible_duplicates = []
    tx_likely_duplicates = []

    # Tolerance for decimal comparison
    QUANTITY_TOLERANCE = Decimal("0.0001")
    AMOUNT_TOLERANCE = Decimal("0.01")

    # Build fake_id -> real_asset_id mapping from asset_mappings
    # Only includes mappings where exactly 1 candidate was found (auto-resolved)
    resolved_assets: Dict[int, int] = {}
    if asset_mappings:
        for mapping in asset_mappings:
            if mapping.selected_asset_id is not None:
                resolved_assets[mapping.fake_asset_id] = mapping.selected_asset_id

    for idx, tx in enumerate(transactions):
        # Determine if this transaction has a resolved asset
        real_asset_id: Optional[int] = None
        asset_is_resolved = False

        if tx.asset_id is not None:
            if is_fake_asset_id(tx.asset_id):
                # Check if this fake ID was resolved to a real asset
                if tx.asset_id in resolved_assets:
                    real_asset_id = resolved_assets[tx.asset_id]
                    asset_is_resolved = True
            else:
                # Already a real asset ID
                real_asset_id = tx.asset_id
                asset_is_resolved = True

        # Build query conditions
        conditions = [
            Transaction.broker_id == broker_id,
            Transaction.type == tx.type,
            Transaction.date == tx.date
            ]

        # If asset is resolved, filter by asset_id for more precise matching
        if asset_is_resolved and real_asset_id is not None:
            conditions.append(Transaction.asset_id == real_asset_id)

        stmt = select(Transaction).where(and_(*conditions))
        result = await session.execute(stmt)
        existing_txs = result.scalars().all()

        matches = []
        for existing in existing_txs:
            # Check quantity match (with tolerance)
            qty_match = abs(existing.quantity - tx.quantity) <= QUANTITY_TOLERANCE
            if not qty_match:
                continue

            # Check cash match (if applicable)
            cash_match = True
            if tx.cash:
                if existing.amount is None or existing.currency is None:
                    cash_match = False
                elif existing.currency != tx.cash.code:
                    cash_match = False
                elif abs(existing.amount - tx.cash.amount) > AMOUNT_TOLERANCE:
                    cash_match = False

            if not cash_match:
                continue

            # Determine match level based on:
            # 1. Whether asset is resolved (more confident)
            # 2. Whether description matches (even more confident)
            tx_desc = tx.description or ""
            existing_desc = existing.description or ""
            desc_matches = tx_desc and existing_desc and tx_desc.strip() == existing_desc.strip()

            if asset_is_resolved:
                # Asset resolved - use WITH_ASSET levels
                if desc_matches:
                    match_level = BRIMDuplicateLevel.LIKELY_WITH_ASSET
                else:
                    match_level = BRIMDuplicateLevel.POSSIBLE_WITH_ASSET
            else:
                # Asset not resolved - use base levels
                if desc_matches:
                    match_level = BRIMDuplicateLevel.LIKELY
                else:
                    match_level = BRIMDuplicateLevel.POSSIBLE

            matches.append(BRIMDuplicateMatch(
                existing_tx_id=existing.id,
                tx_date=existing.date,
                tx_type=existing.type,
                tx_quantity=existing.quantity,
                tx_cash_amount=existing.amount,
                tx_cash_currency=existing.currency,
                tx_description=existing.description,
                match_level=match_level
                ))

        if not matches:
            tx_unique_indices.append(idx)
        else:
            # Categorize by highest match level found
            # Priority: LIKELY_WITH_ASSET > LIKELY > POSSIBLE_WITH_ASSET > POSSIBLE
            likely_with_asset = [m for m in matches if m.match_level == BRIMDuplicateLevel.LIKELY_WITH_ASSET]
            likely = [m for m in matches if m.match_level == BRIMDuplicateLevel.LIKELY]

            candidate = BRIMTXDuplicateCandidate(
                tx_row_index=idx,
                tx_parsed=tx,
                tx_existing_matches=matches
                )

            # If any LIKELY level match, put in likely_duplicates
            if likely_with_asset or likely:
                tx_likely_duplicates.append(candidate)
            else:
                tx_possible_duplicates.append(candidate)

    return BRIMDuplicateReport(
        tx_unique_indices=tx_unique_indices,
        tx_possible_duplicates=tx_possible_duplicates,
        tx_likely_duplicates=tx_likely_duplicates
        )
