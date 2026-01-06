"""
Generic CSV Broker Report Import Plugin.

This plugin provides a flexible CSV importer with auto-detection of columns.
It uses header mapping to identify columns regardless of language or naming convention.

**Features:**
- Auto-detection of column mappings via header matching
- Support for common date formats (ISO, DD/MM/YYYY, MM/DD/YYYY, etc.)
- Mapping of transaction type keywords to TransactionType enum
- Warnings for skipped or problematic rows
- Graceful handling of missing optional columns

**Supported Columns (auto-detected via header mapping):**
- date: Transaction date (required)
- type: Transaction type (required)
- quantity: Asset quantity (optional, default 0)
- amount: Cash amount (optional)
- currency: Currency code (optional, default EUR)
- description: Transaction notes (optional)
- asset: Asset identifier (optional, for asset transactions)

**Usage:**
    plugin = BRIMProviderRegistry.get_provider_instance('broker_generic_csv')
    transactions, warnings = plugin.parse(file_path, broker_id=1)
"""
from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Tuple, Dict, Optional

import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMProvider, BRIMParseError
from backend.app.services.provider_registry import register_provider, BRIMProviderRegistry

logger = structlog.get_logger(__name__)

# =============================================================================
# COLUMN MAPPINGS
# =============================================================================

# Maps normalized header names to standard column names
# Each list contains possible header variations (lowercase)
HEADER_MAPPINGS: Dict[str, List[str]] = {
    "date": [
        "date", "data", "settlement_date", "value_date", "trade_date",
        "fecha", "datum", "transaction_date", "exec_date"
        ],
    "type": [
        "type", "tipo", "transaction_type", "operation", "operazione",
        "action", "azione", "trans_type", "op_type"
        ],
    "quantity": [
        "quantity", "quantità", "qty", "shares", "azioni", "units",
        "unità", "amount_shares", "num_shares"
        ],
    "amount": [
        "amount", "importo", "value", "cash", "cash_amount", "total",
        "totale", "net_amount", "gross_amount", "price"
        ],
    "currency": [
        "currency", "valuta", "ccy", "curr", "currency_code",
        "divisa", "währung"
        ],
    "description": [
        "description", "descrizione", "notes", "memo", "note",
        "details", "dettagli", "comment", "commento"
        ],
    "asset": [
        "asset", "symbol", "ticker", "isin", "asset_id", "instrument",
        "strumento", "security", "titolo", "name", "nome"
        ],
    }

# =============================================================================
# TYPE MAPPINGS
# =============================================================================

# Maps lowercase keywords to TransactionType enum
TYPE_MAPPINGS: Dict[str, TransactionType] = {
    # BUY
    "buy": TransactionType.BUY,
    "acquisto": TransactionType.BUY,
    "purchase": TransactionType.BUY,
    "compra": TransactionType.BUY,
    "bought": TransactionType.BUY,
    "b": TransactionType.BUY,

    # SELL
    "sell": TransactionType.SELL,
    "vendita": TransactionType.SELL,
    "sale": TransactionType.SELL,
    "vendi": TransactionType.SELL,
    "sold": TransactionType.SELL,
    "s": TransactionType.SELL,

    # DIVIDEND
    "dividend": TransactionType.DIVIDEND,
    "dividendo": TransactionType.DIVIDEND,
    "div": TransactionType.DIVIDEND,
    "dividends": TransactionType.DIVIDEND,

    # INTEREST
    "interest": TransactionType.INTEREST,
    "interesse": TransactionType.INTEREST,
    "interessi": TransactionType.INTEREST,
    "int": TransactionType.INTEREST,

    # DEPOSIT
    "deposit": TransactionType.DEPOSIT,
    "deposito": TransactionType.DEPOSIT,
    "versamento": TransactionType.DEPOSIT,
    "dep": TransactionType.DEPOSIT,
    "cash_in": TransactionType.DEPOSIT,

    # WITHDRAWAL
    "withdrawal": TransactionType.WITHDRAWAL,
    "prelievo": TransactionType.WITHDRAWAL,
    "ritiro": TransactionType.WITHDRAWAL,
    "withdraw": TransactionType.WITHDRAWAL,
    "cash_out": TransactionType.WITHDRAWAL,

    # FEE
    "fee": TransactionType.FEE,
    "commissione": TransactionType.FEE,
    "fees": TransactionType.FEE,
    "commissioni": TransactionType.FEE,
    "charge": TransactionType.FEE,

    # TAX
    "tax": TransactionType.TAX,
    "tassa": TransactionType.TAX,
    "imposta": TransactionType.TAX,
    "taxes": TransactionType.TAX,
    "withholding": TransactionType.TAX,

    # TRANSFER (requires link_uuid - rarely from CSV)
    "transfer": TransactionType.TRANSFER,
    "trasferimento": TransactionType.TRANSFER,
    "transfer_in": TransactionType.TRANSFER,
    "transfer_out": TransactionType.TRANSFER,

    # ADJUSTMENT
    "adjustment": TransactionType.ADJUSTMENT,
    "rettifica": TransactionType.ADJUSTMENT,
    "aggiustamento": TransactionType.ADJUSTMENT,
    "correction": TransactionType.ADJUSTMENT,
    }

# =============================================================================
# DATE PARSING
# =============================================================================

# Date formats to try, in order of preference
DATE_FORMATS = [
    "%Y-%m-%d",  # ISO: 2025-01-03
    "%d/%m/%Y",  # European: 03/01/2025
    "%m/%d/%Y",  # US: 01/03/2025
    "%d-%m-%Y",  # European dash: 03-01-2025
    "%Y/%m/%d",  # ISO slash: 2025/01/03
    "%d.%m.%Y",  # German: 03.01.2025
    "%Y%m%d",  # Compact: 20250103
    "%d %b %Y",  # Text: 03 Jan 2025
    "%d %B %Y",  # Full text: 03 January 2025
    ]


def parse_date(value: str) -> Optional[date]:
    """
    Parse a date string using multiple format patterns.

    Args:
        value: Date string to parse

    Returns:
        date object or None if parsing fails
    """
    value = value.strip()
    if not value:
        return None

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


# =============================================================================
# NUMBER PARSING
# =============================================================================

def parse_decimal(value: str) -> Optional[Decimal]:
    """
    Parse a decimal number from various formats.

    Handles:
    - Standard decimal: 123.45
    - European decimal: 123,45
    - Thousands separator: 1,234.56 or 1.234,56
    - Negative: -123.45 or (123.45)
    - Currency symbols: $123.45, €123.45

    Args:
        value: String to parse

    Returns:
        Decimal or None if parsing fails
    """
    if not value:
        return None

    # Remove whitespace and common non-numeric chars
    value = value.strip()
    value = value.replace("$", "").replace("€", "").replace("£", "")
    value = value.replace(" ", "").replace("\u00a0", "")  # Regular and non-breaking space

    # Handle parentheses as negative: (123.45) -> -123.45
    if value.startswith("(") and value.endswith(")"):
        value = "-" + value[1:-1]

    # Determine decimal separator
    # If both . and , present, the last one is likely the decimal separator
    has_comma = "," in value
    has_dot = "." in value

    if has_comma and has_dot:
        # Both present: determine which is decimal separator
        comma_pos = value.rfind(",")
        dot_pos = value.rfind(".")

        if comma_pos > dot_pos:
            # Comma is decimal separator (European): 1.234,56
            value = value.replace(".", "").replace(",", ".")
        else:
            # Dot is decimal separator (US): 1,234.56
            value = value.replace(",", "")
    elif has_comma:
        # Only comma: might be decimal or thousands
        # If exactly 3 digits after comma, likely thousands (Italian/European)
        # Otherwise, treat as decimal separator
        parts = value.split(",")
        if len(parts) == 2 and len(parts[1]) == 3 and parts[1].isdigit():
            # Likely thousands separator: 1,234
            value = value.replace(",", "")
        else:
            # Likely decimal separator: 123,45
            value = value.replace(",", ".")

    try:
        return Decimal(value)
    except InvalidOperation:
        return None


# =============================================================================
# PLUGIN IMPLEMENTATION
# =============================================================================

@register_provider(BRIMProviderRegistry)
class GenericCSVBrokerProvider(BRIMProvider):
    """
    Generic CSV import plugin with auto-detection of columns.

    This plugin can parse most simple CSV files exported from brokers.
    It auto-detects columns based on header names and handles common
    variations in date formats, number formats, and transaction types.

    Detection priority is 0 (lowest) - used as fallback when no broker-specific
    plugin matches the file.
    """

    @property
    def provider_code(self) -> str:
        return "broker_generic_csv"

    @property
    def provider_name(self) -> str:
        return "Generic CSV"

    @property
    def description(self) -> str:
        return (
            "Import transactions from a generic CSV file. "
            "Auto-detects columns based on header names. "
            "Supports various date and number formats."
        )

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        """Lowest priority - used as fallback when no specific plugin matches."""
        return 0

    def can_parse(self, file_path: Path) -> bool:
        """
        Check if this plugin can parse the file.

        Returns True for .csv files that have a readable header row.
        """
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                return header is not None and len(header) > 0
        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> Tuple[List[TXCreateItem], List[str], Dict[int, Dict]]:
        """
        Parse CSV file and return transactions with warnings.

        Process:
        1. Read CSV and detect column mappings from header
        2. Validate required columns (date, type) are present
        3. Parse each row into TXCreateItem
        4. Assign fake asset IDs for asset-based transactions
        5. Collect warnings for skipped/problematic rows
        6. Return (transactions, warnings, extracted_assets)

        Asset Handling:
        - Extracts asset identifier from 'asset' column (symbol, ISIN, or name)
        - Groups transactions by asset identifier
        - Assigns consistent fake IDs (same asset = same fake ID)
        """
        from backend.app.schemas.brim import FAKE_ASSET_ID_BASE

        transactions: List[TXCreateItem] = []
        warnings: List[str] = []

        # Track asset identifiers to assign consistent fake IDs
        # Maps extracted identifier -> fake_asset_id
        self._asset_id_map: Dict[str, int] = {}
        self._next_fake_id = FAKE_ASSET_ID_BASE

        # Track extracted asset info for later use
        self._extracted_assets: Dict[int, Dict[str, Optional[str]]] = {}

        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)

                # Map header columns to standard names
                column_map = self._detect_columns(reader.fieldnames or [])

                # Validate required columns
                if "date" not in column_map:
                    raise BRIMParseError(
                        "Required column 'date' not found in CSV header",
                        details={"headers": reader.fieldnames}
                        )
                if "type" not in column_map:
                    raise BRIMParseError(
                        "Required column 'type' not found in CSV header",
                        details={"headers": reader.fieldnames}
                        )

                # Parse rows
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                    try:
                        tx = self._parse_row(row, column_map, broker_id, row_num)
                        if tx:
                            transactions.append(tx)
                    except Exception as e:
                        warnings.append(f"Row {row_num}: {str(e)}")

        except BRIMParseError:
            raise
        except Exception as e:
            raise BRIMParseError(
                f"Error reading CSV file: {str(e)}",
                details={"file": file_path.name}
                )

        if not transactions:
            warnings.append("No valid transactions found in file")

        return transactions, warnings, self._extracted_assets

    def _detect_columns(self, fieldnames: List[str]) -> Dict[str, str]:
        """
        Detect which CSV columns map to standard fields.

        Args:
            fieldnames: List of CSV header column names

        Returns:
            Dict mapping standard field names to CSV column names
        """
        column_map: Dict[str, str] = {}

        for csv_col in fieldnames:
            csv_col_lower = csv_col.lower().strip()

            for std_name, variations in HEADER_MAPPINGS.items():
                if std_name in column_map:
                    continue  # Already mapped

                if csv_col_lower in variations:
                    column_map[std_name] = csv_col
                    break

        return column_map

    def _parse_row(
        self,
        row: Dict[str, str],
        column_map: Dict[str, str],
        broker_id: int,
        row_num: int
        ) -> Optional[TXCreateItem]:
        """
        Parse a single CSV row into a TXCreateItem.

        Args:
            row: Dict of column name -> value
            column_map: Mapping of standard names to CSV column names
            broker_id: Target broker ID
            row_num: Row number for error messages

        Returns:
            TXCreateItem or None if row should be skipped

        Raises:
            Exception with descriptive message if row is invalid
        """

        # Helper to get value from row using mapping
        def get_val(std_name: str, default: str = "") -> str:
            csv_col = column_map.get(std_name)
            if csv_col:
                return row.get(csv_col, default).strip()
            return default

        # Parse date (required)
        date_str = get_val("date")
        if not date_str:
            raise ValueError("Empty date value")

        tx_date = parse_date(date_str)
        if not tx_date:
            raise ValueError(f"Invalid date format: '{date_str}'")

        # Parse type (required)
        type_str = get_val("type")
        if not type_str:
            raise ValueError("Empty type value")

        tx_type = TYPE_MAPPINGS.get(type_str.lower())
        if not tx_type:
            raise ValueError(f"Unknown transaction type: '{type_str}'")

        # Parse quantity (optional, default 0)
        quantity = Decimal("0")
        quantity_str = get_val("quantity")
        if quantity_str:
            parsed_qty = parse_decimal(quantity_str)
            if parsed_qty is not None:
                quantity = parsed_qty

        # Parse amount and currency (optional)
        cash: Optional[Currency] = None
        amount_str = get_val("amount")
        if amount_str:
            amount = parse_decimal(amount_str)
            if amount is not None:
                currency_code = get_val("currency", "EUR")
                cash = Currency(code=currency_code.upper(), amount=amount)

        # Parse description (optional)
        description = get_val("description") or None

        # Parse asset identifier (optional)
        # This could be a symbol, ISIN, or name
        asset_identifier = get_val("asset")

        # Determine if this transaction type requires an asset
        asset_required_types = {
            TransactionType.BUY,
            TransactionType.SELL,
            TransactionType.DIVIDEND,
            TransactionType.TRANSFER,
            TransactionType.ADJUSTMENT,
            }

        # Assign fake asset ID if asset info is present OR if type requires asset
        asset_id: Optional[int] = None

        # If no asset identifier but type requires asset, use row-based placeholder
        # This allows user to manually map the asset in the UI
        if not asset_identifier and tx_type in asset_required_types:
            asset_identifier = f"UNKNOWN_ROW_{row_num}"

        if asset_identifier:
            # Check if we've seen this asset before
            if asset_identifier in self._asset_id_map:
                asset_id = self._asset_id_map[asset_identifier]
            else:
                # Assign new fake ID
                asset_id = self._next_fake_id
                self._asset_id_map[asset_identifier] = asset_id
                self._next_fake_id -= 1

                # Store extracted asset info for later candidate search
                extracted_info = self._classify_asset_identifier(asset_identifier)
                self._extracted_assets[asset_id] = extracted_info

        # Handle TRANSFER type - needs link_uuid
        # For generic CSV, we can't auto-generate paired transfers
        # Just warn and skip TRANSFER types
        if tx_type == TransactionType.TRANSFER:
            raise ValueError(
                "TRANSFER type requires paired transactions with link_uuid. "
                "Please use manual entry or broker-specific plugin."
                )

        # Handle FX_CONVERSION type - needs link_uuid
        if tx_type == TransactionType.FX_CONVERSION:
            raise ValueError(
                "FX_CONVERSION type requires paired transactions with link_uuid. "
                "Please use manual entry or broker-specific plugin."
                )

        # Build TXCreateItem - validation will pass because:
        # - Asset-required types now always have a fake_id assigned
        # - TRANSFER/FX_CONVERSION are rejected above (require link_uuid)
        return TXCreateItem(
            broker_id=broker_id,
            asset_id=asset_id,
            type=tx_type,
            date=tx_date,
            quantity=quantity,
            cash=cash,
            link_uuid=None,
            description=description,
            tags=["import", "csv"]
            )

    # TODO: capire se invece del dizionario si riesce a ritornare direttamente l'oggetto
    def _classify_asset_identifier(self, identifier: str) -> Dict[str, Optional[str]]:
        """
        Try to classify what type of identifier we have.

        ISIN format: 2 letters + 9 alphanumeric + 1 check digit (12 chars total)
        Symbol: Usually 1-5 uppercase letters
        Otherwise: Treat as name

        Returns dict with extracted_symbol, extracted_isin, extracted_name
        """
        identifier = identifier.strip()

        # Check if it looks like an ISIN
        if len(identifier) == 12 and identifier[:2].isalpha() and identifier[2:].isalnum():
            return {
                "extracted_symbol": None,
                "extracted_isin": identifier.upper(),
                "extracted_name": None
                }

        # Check if it looks like a ticker symbol (1-6 chars, alphanumeric with dots/dashes)
        if 1 <= len(identifier) <= 6 and identifier.replace(".", "").replace("-", "").isalnum():
            return {
                "extracted_symbol": identifier.upper(),
                "extracted_isin": None,
                "extracted_name": None
                }

        # Otherwise treat as name
        return {
            "extracted_symbol": None,
            "extracted_isin": None,
            "extracted_name": identifier
            }

    def get_extracted_assets(self) -> Dict[int, Dict[str, Optional[str]]]:
        """
        Get the mapping of fake asset IDs to extracted info.

        Call this after parse() to get asset info for candidate search.

        Returns:
            Dict mapping fake_asset_id -> {extracted_symbol, extracted_isin, extracted_name}
        """
        return getattr(self, '_extracted_assets', {})
