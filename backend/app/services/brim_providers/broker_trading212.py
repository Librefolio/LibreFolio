"""
Trading212 Broker Report Import Plugin.

This plugin parses CSV exports from Trading212 (UK/EU broker).

**File Format Characteristics:**
- First line: column headers
- Separator: comma
- English column names
- ISO datetime format with timezone (YYYY-MM-DD HH:MM:SS.mmm)
- Multi-currency support

**Supported Transaction Types:**
- Market buy → BUY
- Market sell → SELL
- Dividend (Dividend) → DIVIDEND
- Deposit → DEPOSIT
- Withdrawal → WITHDRAWAL
- Interest on cash → INTEREST
- Withholding tax (in separate column) → TAX

**Columns:**
- Action: Transaction type
- Time: Timestamp (ISO format)
- ISIN: Asset ISIN
- Ticker: Asset symbol
- Name: Asset name
- No. of shares: Quantity
- Total: Total amount
- Currency (Total): Currency code
- Withholding tax: Tax withheld
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

# Column names
COL_ACTION = "Action"
COL_TIME = "Time"
COL_ISIN = "ISIN"
COL_TICKER = "Ticker"
COL_NAME = "Name"
COL_SHARES = "No. of shares"
COL_TOTAL = "Total"
COL_CURRENCY = "Currency (Total)"
COL_TAX = "Withholding tax"
COL_TAX_CURRENCY = "Currency (Withholding tax)"

# Type mapping (lowercase)
TYPE_MAPPINGS: Dict[str, TransactionType] = {
    "market buy": TransactionType.BUY,
    "limit buy": TransactionType.BUY,
    "stop buy": TransactionType.BUY,
    "market sell": TransactionType.SELL,
    "limit sell": TransactionType.SELL,
    "stop sell": TransactionType.SELL,
    "deposit": TransactionType.DEPOSIT,
    "withdrawal": TransactionType.WITHDRAWAL,
    "dividend": TransactionType.DIVIDEND,
    "interest on cash": TransactionType.INTEREST,
    }

# Types to skip
SKIP_TYPES = [
    "stock split",
    "stock distribution",
    "transfer",
    "currency conversion",
    ]


def _parse_trading212_datetime(value: str) -> Optional[date_type]:
    """Parse Trading212 datetime format."""
    value = value.strip()
    if not value:
        return None

    # Try multiple formats
    formats = [
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        ]

    for fmt in formats:
        try:
            return datetime.strptime(value[:26], fmt).date()  # Limit to 26 chars for microseconds
        except ValueError:
            continue

    return None


def _parse_trading212_number(value: str) -> Optional[Decimal]:
    """Parse Trading212 number."""
    value = value.strip()
    if not value:
        return None

    # Remove currency symbols and quotes
    value = re.sub(r'[€$£""]', '', value).strip()

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
class Trading212BrokerProvider(BRIMProvider):
    """
    Trading212 (UK/EU broker) CSV export import plugin.
    """

    @property
    def provider_code(self) -> str:
        return "broker_trading212"

    @property
    def provider_name(self) -> str:
        return "Trading212"

    @property
    def description(self) -> str:
        return (
            "Import transactions from Trading212 CSV export. "
            "Supports stocks, ETFs, dividends, and interest."
        )

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> str:
        """Trading212 logo."""
        return "https://www.trading212.com/favicon.ico"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Trading212 format by checking for distinctive headers."""
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=3)
            first_line = content.split('\n')[0].lower() if content else ""

            # Trading212 specific columns
            required = ["action", "time", "isin", "ticker", "no. of shares"]
            return all(col in first_line for col in required)

        except Exception:
            return False

    def parse(
        self,
        file_path: Path,
        broker_id: int
    ) -> Tuple[List[TXCreateItem], List[str], Dict[int, BRIMExtractedAssetInfo]]:
        """Parse Trading212 CSV export file."""
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

                    action = row.get(COL_ACTION, "").strip().lower()
                    if not action:
                        continue

                    # Skip certain types
                    if any(skip in action for skip in SKIP_TYPES):
                        continue

                    # Map transaction type
                    tx_type = None
                    for pattern, mapped_type in TYPE_MAPPINGS.items():
                        if pattern in action:
                            tx_type = mapped_type
                            break

                    if tx_type is None:
                        warnings.append(f"Row {row_num}: unknown action '{action}', skipping")
                        continue

                    # Parse date
                    tx_date = _parse_trading212_datetime(row.get(COL_TIME, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date, skipping")
                        continue

                    # Get asset info
                    isin = row.get(COL_ISIN, "").strip()
                    ticker = row.get(COL_TICKER, "").strip()
                    name = row.get(COL_NAME, "").strip()

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
                                "extracted_name": name if name else None,
                                }

                            next_fake_id -= 1

                    # Parse amount
                    amount = _parse_trading212_number(row.get(COL_TOTAL, ""))
                    currency = row.get(COL_CURRENCY, "EUR").strip().upper()
                    if not currency:
                        currency = "EUR"

                    # Parse quantity
                    quantity = _parse_trading212_number(row.get(COL_SHARES, ""))
                    if quantity is None:
                        quantity = Decimal("0")

                    # Adjust signs
                    if tx_type == TransactionType.SELL and quantity > 0:
                        quantity = -quantity
                    if tx_type == TransactionType.BUY and amount and amount > 0:
                        amount = -amount

                    # Create main transaction
                    try:
                        tx = TXCreateItem(
                            broker_id=broker_id,
                            asset_id=asset_id,
                            type=tx_type,
                            date=tx_date,
                            quantity=quantity,
                            cash=Currency(code=currency, amount=amount) if amount else None,
                            description=f"{action}: {name}" if name else action,
                            tags=["import", "trading212"],
                            )
                        transactions.append(tx)

                    except Exception as e:
                        warnings.append(f"Row {row_num}: error creating transaction: {e}")
                        continue

                    # Handle withholding tax as separate transaction
                    tax_amount = _parse_trading212_number(row.get(COL_TAX, ""))
                    if tax_amount and tax_amount != 0:
                        tax_currency = row.get(COL_TAX_CURRENCY, currency).strip().upper()
                        if not tax_currency:
                            tax_currency = currency

                        # Tax is usually positive in the file, make it negative
                        if tax_amount > 0:
                            tax_amount = -tax_amount

                        try:
                            tax_tx = TXCreateItem(
                                broker_id=broker_id,
                                asset_id=asset_id,
                                type=TransactionType.TAX,
                                date=tx_date,
                                quantity=Decimal("0"),
                                cash=Currency(code=tax_currency, amount=tax_amount),
                                description=f"Withholding tax: {name}" if name else "Withholding tax",
                                tags=["import", "trading212", "tax"],
                                )
                            transactions.append(tax_tx)
                        except Exception as e:
                            warnings.append(f"Row {row_num}: error creating tax transaction: {e}")

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
            "Trading212 file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets_typed)
            )

        return transactions, warnings, extracted_assets_typed

    @property
    def test_file_pattern(self) -> Optional[str]:
        """Filename pattern for auto-detection tests."""
        return "trading212"
