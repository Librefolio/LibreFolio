"""
Freetrade Broker Report Import Plugin.

This plugin parses CSV exports from Freetrade (UK broker).

**File Format Characteristics:**
- First line: column headers
- Separator: comma
- ISO datetime format
- GBP as primary currency
- ISIN provided

**Supported Transaction Types:**
- ORDER (Buy/Sell) → BUY/SELL
- DIVIDEND → DIVIDEND
- TOP_UP → DEPOSIT
- WITHDRAWAL → WITHDRAWAL
- INTEREST_FROM_CASH → INTEREST
- FREESHARE_ORDER → BUY

**Columns:**
- Title: Asset name
- Type: Transaction type
- Timestamp: ISO datetime
- Account Currency: Currency code
- Total Amount: Transaction value
- Buy / Sell: Direction for orders
- Ticker: Asset symbol
- ISIN: Asset ISIN
- Quantity: Number of shares
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

COL_TITLE = "Title"
COL_TYPE = "Type"
COL_TIMESTAMP = "Timestamp"
COL_CURRENCY = "Account Currency"
COL_AMOUNT = "Total Amount"
COL_DIRECTION = "Buy / Sell"
COL_TICKER = "Ticker"
COL_ISIN = "ISIN"
COL_QUANTITY = "Quantity"

# Type mapping
TYPE_MAPPINGS: Dict[str, TransactionType] = {
    "order": None,  # Determined by Buy/Sell column
    "freeshare_order": TransactionType.BUY,
    "dividend": TransactionType.DIVIDEND,
    "top_up": TransactionType.DEPOSIT,
    "withdrawal": TransactionType.WITHDRAWAL,
    "interest_from_cash": TransactionType.INTEREST,
    }

# Types to skip
SKIP_TYPES = [
    "monthly_statement",
    "property",  # Stock property changes
    ]


def _parse_freetrade_datetime(value: str) -> Optional[date_type]:
    """Parse Freetrade ISO datetime format."""
    value = value.strip().replace("Z", "")
    if not value:
        return None

    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        ]

    for fmt in formats:
        try:
            return datetime.strptime(value[:26], fmt).date()
        except ValueError:
            continue

    return None


def _parse_freetrade_number(value: str) -> Optional[Decimal]:
    """Parse Freetrade number."""
    value = value.strip()
    if not value:
        return None

    try:
        return Decimal(value)
    except InvalidOperation:
        return None


# =============================================================================
# PLUGIN IMPLEMENTATION
# =============================================================================

@register_provider(BRIMProviderRegistry)
class FreetradeBrokerProvider(BRIMProvider):
    """Freetrade (UK broker) CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_freetrade"

    @property
    def provider_name(self) -> str:
        return "Freetrade"

    @property
    def description(self) -> str:
        return (
            "Import transactions from Freetrade CSV export. "
            "Supports UK stocks, ETFs, dividends, and interest."
        )

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> str:
        return "https://freetrade.io/favicon.ico"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Freetrade format by checking for distinctive headers."""
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=3)
            first_line = content.split('\n')[0].lower() if content else ""

            # Freetrade specific columns - must have ALL of these
            required = ["title", "type", "timestamp", "account currency", "buy / sell", "isin", "stamp duty"]
            return all(col in first_line for col in required)

        except Exception:
            return False

    def parse(
        self,
        file_path: Path,
        broker_id: int
    ) -> Tuple[List[TXCreateItem], List[str], Dict[int, BRIMExtractedAssetInfo]]:
        """Parse Freetrade CSV export file."""
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
                    tx_type = TYPE_MAPPINGS.get(tx_type_raw)

                    # For ORDER type, determine from Buy/Sell column
                    if tx_type_raw == "order":
                        direction = row.get(COL_DIRECTION, "").strip().upper()
                        if direction == "BUY":
                            tx_type = TransactionType.BUY
                        elif direction == "SELL":
                            tx_type = TransactionType.SELL
                        else:
                            warnings.append(f"Row {row_num}: unknown order direction '{direction}', skipping")
                            continue

                    if tx_type is None:
                        warnings.append(f"Row {row_num}: unknown type '{tx_type_raw}', skipping")
                        continue

                    # Parse date
                    tx_date = _parse_freetrade_datetime(row.get(COL_TIMESTAMP, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date, skipping")
                        continue

                    # Get asset info
                    ticker = row.get(COL_TICKER, "").strip()
                    isin = row.get(COL_ISIN, "").strip()
                    title = row.get(COL_TITLE, "").strip()

                    # Asset required for some types
                    asset_id = None
                    asset_required = tx_type in [
                        TransactionType.BUY,
                        TransactionType.SELL,
                        TransactionType.DIVIDEND,
                        ]

                    if asset_required:
                        if not isin and not ticker:
                            warnings.append(f"Row {row_num}: {tx_type.value} requires asset, skipping")
                            continue

                        asset_key = isin if isin else ticker

                        if asset_key in asset_to_fake_id:
                            asset_id = asset_to_fake_id[asset_key]
                        else:
                            asset_id = next_fake_id
                            asset_to_fake_id[asset_key] = asset_id

                            extracted_assets[asset_id] = {
                                "extracted_symbol": ticker if ticker else None,
                                "extracted_isin": isin if isin else None,
                                "extracted_name": title if title else None,
                                }

                            next_fake_id -= 1

                    # Parse amount
                    amount = _parse_freetrade_number(row.get(COL_AMOUNT, ""))
                    currency = row.get(COL_CURRENCY, "GBP").strip().upper() or "GBP"

                    # Parse quantity
                    quantity = _parse_freetrade_number(row.get(COL_QUANTITY, ""))
                    if quantity is None:
                        quantity = Decimal("0")

                    # Adjust signs
                    if tx_type == TransactionType.SELL and quantity > 0:
                        quantity = -quantity
                    if tx_type == TransactionType.BUY and amount and amount > 0:
                        amount = -amount
                    if tx_type == TransactionType.WITHDRAWAL and amount and amount > 0:
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
                            description=f"{tx_type_raw}: {title}" if title else tx_type_raw,
                            tags=["import", "freetrade"],
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
            "Freetrade file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets_typed)
            )

        return transactions, warnings, extracted_assets_typed

    @property
    def test_file_pattern(self) -> Optional[str]:
        """Filename pattern for auto-detection tests."""
        return "freetrade"
