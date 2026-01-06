"""
Coinbase Broker Report Import Plugin.

This plugin parses CSV exports from Coinbase (crypto exchange).

**File Format Characteristics:**
- First line: column headers
- Separator: comma
- ISO datetime format with timezone
- EUR as primary currency (with € symbol in some columns)
- Crypto assets (BTC, ETH, etc.)

**Supported Transaction Types:**
- Buy → BUY
- Sell → SELL
- Staking Income / Rewards Income → INTEREST
- Convert → BUY (of target asset)
- Send → WITHDRAWAL (of crypto)
- Receive → DEPOSIT (of crypto)

**Columns:**
- Timestamp: ISO datetime with UTC
- Transaction Type: Type of transaction
- Asset: Crypto symbol
- Quantity Transacted: Amount
- Price Currency: Currency code
- Total (inclusive of fees and/or spread): Net amount
- Fees and/or Spread: Transaction fees
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
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMProvider, BRIMParseError
from backend.app.services.provider_registry import register_provider, BRIMProviderRegistry

logger = structlog.get_logger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

COL_TIMESTAMP = "Timestamp"
COL_TYPE = "Transaction Type"
COL_ASSET = "Asset"
COL_QUANTITY = "Quantity Transacted"
COL_CURRENCY = "Price Currency"
COL_TOTAL = "Total (inclusive of fees and/or spread)"
COL_FEES = "Fees and/or Spread"

# Type mapping
TYPE_MAPPINGS: Dict[str, TransactionType] = {
    "buy": TransactionType.BUY,
    "sell": TransactionType.SELL,
    "staking income": TransactionType.INTEREST,
    "rewards income": TransactionType.INTEREST,
    "learning reward": TransactionType.INTEREST,
    "convert": TransactionType.BUY,  # Treat as buy of target
    }

# Types to skip
SKIP_TYPES = [
    "send",  # Internal crypto transfers
    "receive",  # Internal crypto transfers
    ]


def _parse_coinbase_datetime(value: str) -> Optional[date_type]:
    """Parse Coinbase datetime format (YYYY-MM-DD HH:MM:SS UTC)."""
    value = value.strip().replace(" UTC", "")
    if not value:
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def _parse_coinbase_amount(value: str) -> Optional[Decimal]:
    """Parse Coinbase amount (may have € symbol)."""
    value = value.strip()
    if not value:
        return None

    # Remove currency symbols
    value = re.sub(r'[€$£]', '', value).strip()

    # Handle comma as thousands separator
    value = value.replace(",", "")

    try:
        return Decimal(value)
    except InvalidOperation:
        return None


# =============================================================================
# PLUGIN IMPLEMENTATION
# =============================================================================

@register_provider(BRIMProviderRegistry)
class CoinbaseBrokerProvider(BRIMProvider):
    """Coinbase crypto exchange CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_coinbase"

    @property
    def provider_name(self) -> str:
        return "Coinbase"

    @property
    def description(self) -> str:
        return (
            "Import transactions from Coinbase CSV export. "
            "Supports crypto buys, sells, and staking rewards."
        )

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> str:
        return "https://www.coinbase.com/favicon.ico"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Coinbase format by checking for distinctive headers."""
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=3)
            first_line = content.split('\n')[0].lower() if content else ""

            # Coinbase specific columns
            required = ["timestamp", "transaction type", "asset", "quantity transacted", "price currency"]
            return all(col in first_line for col in required)

        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> Tuple[List[TXCreateItem], List[str], Dict[int, Dict]]:
        """Parse Coinbase CSV export file."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        extracted_assets: Dict[int, Dict] = {}
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
                    tx_date = _parse_coinbase_datetime(row.get(COL_TIMESTAMP, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date, skipping")
                        continue

                    # Get asset
                    asset = row.get(COL_ASSET, "").strip().upper()

                    # Get or create fake asset ID
                    asset_id = None
                    if asset:
                        if asset in asset_to_fake_id:
                            asset_id = asset_to_fake_id[asset]
                        else:
                            asset_id = next_fake_id
                            asset_to_fake_id[asset] = asset_id

                            extracted_assets[asset_id] = {
                                "extracted_symbol": asset,
                                "extracted_isin": None,
                                "extracted_name": f"{asset} (Crypto)",
                                }

                            next_fake_id -= 1

                    # Parse amount
                    amount = _parse_coinbase_amount(row.get(COL_TOTAL, ""))
                    currency = row.get(COL_CURRENCY, "EUR").strip().upper() or "EUR"

                    # Parse quantity
                    quantity = _parse_coinbase_amount(row.get(COL_QUANTITY, ""))
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
                            description=f"{tx_type_raw}: {asset}",
                            tags=["import", "coinbase", "crypto"],
                            )
                        transactions.append(tx)

                    except Exception as e:
                        warnings.append(f"Row {row_num}: error creating transaction: {e}")
                        continue

                    # Handle fees as separate transaction
                    fees = _parse_coinbase_amount(row.get(COL_FEES, ""))
                    if fees and fees > 0:
                        try:
                            fee_tx = TXCreateItem(
                                broker_id=broker_id,
                                asset_id=asset_id,
                                type=TransactionType.FEE,
                                date=tx_date,
                                quantity=Decimal("0"),
                                cash=Currency(code=currency, amount=-fees),
                                description=f"Fee: {asset}",
                                tags=["import", "coinbase", "fee"],
                                )
                            transactions.append(fee_tx)
                        except Exception as e:
                            warnings.append(f"Row {row_num}: error creating fee transaction: {e}")

        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}")
        except Exception as e:
            raise BRIMParseError(f"Error parsing file: {e}")

        if not transactions:
            raise BRIMParseError("No valid transactions found in file")

        logger.info(
            "Coinbase file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets)
            )

        return transactions, warnings, extracted_assets
