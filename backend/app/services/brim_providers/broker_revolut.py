"""
Revolut Broker Report Import Plugin.

This plugin parses CSV exports from Revolut Trading.

**File Format Characteristics:**
- First line: column headers
- Separator: comma
- ISO datetime format with timezone (YYYY-MM-DDTHH:MM:SS.ffffffZ)
- Multi-currency support (USD, EUR, GBP)
- Amount includes currency symbol ($, €, £)

**Supported Transaction Types:**
- BUY - MARKET / BUY - LIMIT → BUY
- SELL - MARKET / SELL - LIMIT → SELL
- DIVIDEND → DIVIDEND
- CASH TOP-UP → DEPOSIT
- CASH WITHDRAWAL → WITHDRAWAL
- CUSTODY FEE → FEE

**Columns:**
- Date: ISO timestamp
- Ticker: Asset symbol
- Type: Transaction type
- Quantity: Number of shares
- Price per share: Unit price
- Total Amount: Total value (with currency symbol)
- Currency: Currency code
"""
from __future__ import annotations

import csv
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
COL_TICKER = "Ticker"
COL_TYPE = "Type"
COL_QUANTITY = "Quantity"
COL_TOTAL = "Total Amount"
COL_CURRENCY = "Currency"

# Type mapping
TYPE_MAPPINGS: Dict[str, TransactionType] = {
    "buy - market": TransactionType.BUY,
    "buy - limit": TransactionType.BUY,
    "sell - market": TransactionType.SELL,
    "sell - limit": TransactionType.SELL,
    "dividend": TransactionType.DIVIDEND,
    "cash top-up": TransactionType.DEPOSIT,
    "cash withdrawal": TransactionType.WITHDRAWAL,
    "custody fee": TransactionType.FEE,
    }

# Types to skip
SKIP_TYPES = [
    "transfer",
    "stock split",
    ]


def _parse_revolut_datetime(value: str) -> Optional[date_type]:
    """Parse Revolut ISO datetime format."""
    value = value.strip()
    if not value:
        return None

    # Remove timezone Z and truncate microseconds
    value = value.replace("Z", "")
    if "." in value:
        value = value[:26]  # Keep up to 6 decimal places

    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def _parse_revolut_amount(value: str) -> Tuple[Optional[Decimal], str]:
    """
    Parse Revolut amount with currency symbol.

    Returns: (amount, currency_code)
    """
    value = value.strip()
    if not value:
        return None, "USD"

    # Detect currency from symbol
    currency = "USD"
    if value.startswith("$"):
        currency = "USD"
        value = value[1:]
    elif value.startswith("€"):
        currency = "EUR"
        value = value[1:]
    elif value.startswith("£"):
        currency = "GBP"
        value = value[1:]

    # Handle European format (comma as decimal)
    value = value.replace(",", ".")

    try:
        return Decimal(value), currency
    except InvalidOperation:
        return None, currency


def _parse_revolut_quantity(value: str) -> Optional[Decimal]:
    """Parse Revolut quantity (may use comma as decimal)."""
    value = value.strip()
    if not value:
        return None

    # Handle European format
    value = value.replace(",", ".")

    try:
        return Decimal(value)
    except InvalidOperation:
        return None


# =============================================================================
# PLUGIN IMPLEMENTATION
# =============================================================================

@register_provider(BRIMProviderRegistry)
class RevolutBrokerProvider(BRIMProvider):
    """Revolut Trading CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_revolut"

    @property
    def provider_name(self) -> str:
        return "Revolut"

    @property
    def description(self) -> str:
        return (
            "Import transactions from Revolut Trading CSV export. "
            "Supports stocks, dividends, and cash movements."
        )

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> str:
        return "https://www.revolut.com/favicon.ico"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Revolut format by checking for distinctive headers."""
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=3)
            first_line = content.split('\n')[0].lower() if content else ""

            # Revolut specific columns - must NOT have Freetrade-specific columns
            if "stamp duty" in first_line or "title" in first_line:
                return False

            # Revolut specific columns
            required = ["date", "ticker", "type", "quantity", "price per share", "total amount", "fx rate"]
            return all(col in first_line for col in required)

        except Exception:
            return False

    def parse(
        self,
        file_path: Path,
        broker_id: int
        ) -> Tuple[List[TXCreateItem], List[str], Dict[int, BRIMExtractedAssetInfo]]:
        """Parse Revolut Trading CSV export file."""
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
                    tx_date = _parse_revolut_datetime(row.get(COL_DATE, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date, skipping")
                        continue

                    # Get ticker
                    ticker = row.get(COL_TICKER, "").strip()

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
                    amount, amount_currency = _parse_revolut_amount(row.get(COL_TOTAL, ""))
                    currency = row.get(COL_CURRENCY, "").strip().upper() or amount_currency

                    # Parse quantity
                    quantity = _parse_revolut_quantity(row.get(COL_QUANTITY, ""))
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
                            description=f"{tx_type_raw}: {ticker}" if ticker else tx_type_raw,
                            tags=["import", "revolut"],
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
            "Revolut file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets_typed)
            )

        return transactions, warnings, extracted_assets_typed

    @property
    def test_file_pattern(self) -> Optional[str]:
        """Filename pattern for auto-detection tests."""
        return "revolut"
