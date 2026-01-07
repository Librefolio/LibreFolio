"""
eToro Broker Report Import Plugin.

This plugin parses CSV exports from eToro (social trading platform).

**File Format Characteristics:**
- First line: column headers
- Separator: comma
- Date format: DD/MM/YYYY HH:MM:SS
- Details column contains ticker (e.g., NKE/USD)
- Multi-currency inferred from ticker

**Supported Transaction Types:**
- Open Position → BUY
- Position closed → SELL
- Dividend → DIVIDEND
- Interest Payment → INTEREST
- Withdraw Request → WITHDRAWAL
- Deposit → DEPOSIT
- Withdraw Fee / Conversion Fee → FEE

**Columns:**
- Date: Transaction date
- Type: Transaction type
- Details: Contains ticker (SYMBOL/CURRENCY)
- Amount: Cash amount
- Units: Quantity
"""
from __future__ import annotations

import csv
import re
from datetime import date as date_type, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Tuple, Dict, Optional

import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMExtractedAssetInfo
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMProvider, BRIMParseError
from backend.app.services.provider_registry import register_provider, BRIMProviderRegistry

logger = structlog.get_logger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

COL_DATE = "Date"
COL_TYPE = "Type"
COL_DETAILS = "Details"
COL_AMOUNT = "Amount"
COL_UNITS = "Units"

# Type mapping
TYPE_MAPPINGS: Dict[str, TransactionType] = {
    "open position": TransactionType.BUY,
    "position closed": TransactionType.SELL,
    "dividend": TransactionType.DIVIDEND,
    "interest payment": TransactionType.INTEREST,
    "withdraw request": TransactionType.WITHDRAWAL,
    "deposit": TransactionType.DEPOSIT,
    }

# Types to skip
SKIP_TYPES = [
    "overnight fee",
    "overnight refund",
    "withdraw fee",
    "conversion fee",
    "sdrt",  # UK stamp duty
    ]


def _parse_etoro_date(value: str) -> Optional[date_type]:
    """Parse eToro date format (DD/MM/YYYY HH:MM:SS)."""
    value = value.strip()
    if not value:
        return None

    formats = [
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def _parse_etoro_number(value: str) -> Optional[Decimal]:
    """Parse eToro number (may have parentheses for negative, spaces, commas)."""
    value = value.strip()
    if not value or value == "-":
        return None

    # Handle parentheses for negative
    is_negative = False
    if value.startswith("(") and value.endswith(")"):
        is_negative = True
        value = value[1:-1]

    # Remove spaces and currency symbols
    value = re.sub(r'[\s€$£]', '', value)

    # Handle European format (1.234,56) vs US format (1,234.56)
    if '.' in value and ',' in value:
        if value.rfind(',') > value.rfind('.'):
            # European: 1.234,56
            value = value.replace('.', '').replace(',', '.')
        else:
            # US: 1,234.56
            value = value.replace(',', '')
    elif ',' in value:
        # Could be decimal or thousands
        parts = value.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            value = value.replace(',', '.')
        else:
            value = value.replace(',', '')

    try:
        result = Decimal(value)
        return -result if is_negative else result
    except InvalidOperation:
        return None


def _parse_ticker_from_details(details: str) -> Tuple[Optional[str], str]:
    """
    Extract ticker and currency from eToro details field.

    Format: SYMBOL/CURRENCY (e.g., NKE/USD, KER/EUR)

    Returns:
        Tuple of (ticker, currency)
    """
    if not details or details == "-":
        return None, "USD"

    match = re.match(r'^([A-Z0-9]+)/([A-Z]{3})$', details.strip())
    if match:
        return match.group(1), match.group(2)

    return details.strip(), "USD"


# =============================================================================
# PLUGIN IMPLEMENTATION
# =============================================================================

@register_provider(BRIMProviderRegistry)
class EtoroBrokerProvider(BRIMProvider):
    """
    eToro (social trading platform) CSV export import plugin.
    """

    @property
    def provider_code(self) -> str:
        return "broker_etoro"

    @property
    def provider_name(self) -> str:
        return "eToro"

    @property
    def description(self) -> str:
        return (
            "Import transactions from eToro CSV export. "
            "Supports stocks, CFDs, dividends, and interest."
        )

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> str:
        """eToro logo."""
        return "https://www.etoro.com/favicon.ico"

    def can_parse(self, file_path: Path) -> bool:
        """Detect eToro format by checking for distinctive headers."""
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=3)
            first_line = content.split('\n')[0].lower() if content else ""

            # eToro specific columns
            required = ["date", "type", "details", "amount", "units", "realized equity"]
            return all(col in first_line for col in required)

        except Exception:
            return False

    def parse(
        self,
        file_path: Path,
        broker_id: int
        ) -> Tuple[List[TXCreateItem], List[str], Dict[int, BRIMExtractedAssetInfo]]:
        """Parse eToro CSV export file."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        extracted_assets: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                row_num = 1

                for row in reader:
                    row_num += 1

                    tx_type_raw = row.get(COL_TYPE, "").strip().lower()
                    if not tx_type_raw:
                        continue

                    # Skip certain types
                    if any(skip in tx_type_raw for skip in SKIP_TYPES):
                        continue

                    # Map transaction type
                    tx_type = None
                    for pattern, mapped_type in TYPE_MAPPINGS.items():
                        if pattern in tx_type_raw:
                            tx_type = mapped_type
                            break

                    if tx_type is None:
                        warnings.append(f"Row {row_num}: unknown type '{tx_type_raw}', skipping")
                        continue

                    # Parse date
                    tx_date = _parse_etoro_date(row.get(COL_DATE, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date, skipping")
                        continue

                    # Get ticker and currency from details
                    details = row.get(COL_DETAILS, "")
                    ticker, currency = _parse_ticker_from_details(details)

                    # Asset required for some types
                    asset_id = None
                    asset_required = tx_type in [
                        TransactionType.BUY,
                        TransactionType.SELL,
                        TransactionType.DIVIDEND,
                        ]

                    if asset_required:
                        if not ticker:
                            warnings.append(f"Row {row_num}: {tx_type.value} requires asset, skipping")
                            continue

                        if ticker in asset_to_fake_id:
                            asset_id = asset_to_fake_id[ticker]
                        else:
                            asset_id = next_fake_id
                            asset_to_fake_id[ticker] = asset_id

                            extracted_assets[asset_id] = {
                                "extracted_symbol": ticker,
                                "extracted_isin": None,
                                "extracted_name": None,
                                }

                            next_fake_id -= 1

                    # Parse amount
                    amount = _parse_etoro_number(row.get(COL_AMOUNT, ""))

                    # Parse quantity
                    quantity = _parse_etoro_number(row.get(COL_UNITS, ""))
                    if quantity is None:
                        quantity = Decimal("0")

                    # Adjust signs
                    if tx_type == TransactionType.SELL and quantity > 0:
                        quantity = -quantity
                    if tx_type == TransactionType.BUY and amount and amount > 0:
                        amount = -amount

                    # Create transaction
                    try:
                        tx = TXCreateItem(
                            broker_id=broker_id,
                            asset_id=asset_id,
                            type=tx_type,
                            date=tx_date,
                            quantity=quantity,
                            cash=Currency(code=currency, amount=amount) if amount else None,
                            description=f"{tx_type_raw}: {details}" if details else tx_type_raw,
                            tags=["import", "etoro"],
                            )
                        transactions.append(tx)

                    except Exception as e:
                        warnings.append(f"Row {row_num}: error creating transaction: {e}")
                        continue

        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}")
        except Exception as e:
            raise BRIMParseError(f"Error parsing file: {e}")

        if not transactions:
            raise BRIMParseError("No valid transactions found in file")

        # Convert raw dict to BRIMExtractedAssetInfo
        extracted_assets_typed: Dict[int, BRIMExtractedAssetInfo] = {
            fake_id: BRIMExtractedAssetInfo(
                extracted_symbol=info.get("extracted_symbol"),
                extracted_isin=info.get("extracted_isin"),
                extracted_name=info.get("extracted_name"),
                )
            for fake_id, info in extracted_assets.items()
            }

        logger.info(
            "eToro file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets_typed)
            )

        return transactions, warnings, extracted_assets_typed

    @property
    def test_file_pattern(self) -> Optional[str]:
        """Filename pattern for auto-detection tests."""
        return "etoro"
