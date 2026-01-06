"""
Charles Schwab Broker Report Import Plugin.

This plugin parses CSV exports from Charles Schwab.

**File Format Characteristics:**
- First line: column headers
- Separator: comma
- US date format (MM/DD/YYYY)
- USD currency with $ symbol
- Amounts may have thousands separator (comma)

**Supported Transaction Types:**
- Buy / Reinvest Shares → BUY
- Sell → SELL
- Dividend / Reinvest Dividend / Qualified Dividend → DIVIDEND
- Credit Interest → INTEREST
- Wire Funds / MoneyLink Transfer → DEPOSIT/WITHDRAWAL

**Columns:**
- Date: MM/DD/YYYY
- Action: Transaction type
- Symbol: Asset ticker
- Description: Asset name
- Quantity: Number of shares
- Amount: Total value (with $)
- Fees & Comm: Commission
"""
from __future__ import annotations

import csv
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

COL_DATE = "Date"
COL_ACTION = "Action"
COL_SYMBOL = "Symbol"
COL_DESCRIPTION = "Description"
COL_QUANTITY = "Quantity"
COL_AMOUNT = "Amount"
COL_FEES = "Fees & Comm"

# Type mapping
TYPE_MAPPINGS: Dict[str, TransactionType] = {
    "buy": TransactionType.BUY,
    "reinvest shares": TransactionType.BUY,
    "sell": TransactionType.SELL,
    "dividend": TransactionType.DIVIDEND,
    "reinvest dividend": TransactionType.DIVIDEND,
    "qualified dividend": TransactionType.DIVIDEND,
    "credit interest": TransactionType.INTEREST,
    "wire funds": TransactionType.DEPOSIT,
    "moneylink transfer": TransactionType.DEPOSIT,
    }


def _parse_schwab_date(value: str) -> Optional[date_type]:
    """Parse Schwab US date format (MM/DD/YYYY)."""
    value = value.strip()
    if not value:
        return None

    try:
        return datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError:
        return None


def _parse_schwab_amount(value: str) -> Optional[Decimal]:
    """Parse Schwab amount ($1,234.56 format)."""
    value = value.strip()
    if not value:
        return None

    # Remove $ and quotes
    value = value.replace("$", "").replace('"', '')

    # Remove thousands separator (but keep decimal point)
    value = value.replace(",", "")

    try:
        return Decimal(value)
    except InvalidOperation:
        return None


# =============================================================================
# PLUGIN IMPLEMENTATION
# =============================================================================

@register_provider(BRIMProviderRegistry)
class SchwabBrokerProvider(BRIMProvider):
    """Charles Schwab CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_schwab"

    @property
    def provider_name(self) -> str:
        return "Charles Schwab"

    @property
    def description(self) -> str:
        return (
            "Import transactions from Charles Schwab CSV export. "
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
        return "https://www.schwab.com/favicon.ico"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Schwab format by checking for distinctive headers."""
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=3)
            first_line = content.split('\n')[0].lower() if content else ""

            # Schwab specific columns
            required = ["date", "action", "symbol", "description", "quantity", "fees & comm", "amount"]
            return all(col in first_line for col in required)

        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> Tuple[List[TXCreateItem], List[str], Dict[int, Dict]]:
        """Parse Schwab CSV export file."""
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

                    action = row.get(COL_ACTION, "").strip().lower()
                    if not action:
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
                    tx_date = _parse_schwab_date(row.get(COL_DATE, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date, skipping")
                        continue

                    # Get symbol and description
                    symbol = row.get(COL_SYMBOL, "").strip()
                    description = row.get(COL_DESCRIPTION, "").strip()

                    # Asset required for some types
                    asset_id = None
                    asset_required = tx_type in [
                        TransactionType.BUY,
                        TransactionType.SELL,
                        TransactionType.DIVIDEND,
                        ]

                    if asset_required:
                        if not symbol:
                            warnings.append(f"Row {row_num}: {tx_type.value} requires asset, skipping")
                            continue

                        if symbol in asset_to_fake_id:
                            asset_id = asset_to_fake_id[symbol]
                        else:
                            asset_id = next_fake_id
                            asset_to_fake_id[symbol] = asset_id

                            extracted_assets[asset_id] = {
                                "extracted_symbol": symbol,
                                "extracted_isin": None,
                                "extracted_name": description if description else None,
                                }

                            next_fake_id -= 1

                    # Parse amount
                    amount = _parse_schwab_amount(row.get(COL_AMOUNT, ""))

                    # Parse quantity
                    quantity = _parse_schwab_amount(row.get(COL_QUANTITY, ""))
                    if quantity is None:
                        quantity = Decimal("0")

                    # Adjust signs (Schwab already has correct signs in Amount)
                    if tx_type == TransactionType.SELL and quantity > 0:
                        quantity = -quantity

                    # Create transaction
                    try:
                        tx = TXCreateItem(
                            broker_id=broker_id,
                            asset_id=asset_id,
                            type=tx_type,
                            date=tx_date,
                            quantity=quantity,
                            cash=Currency(code="USD", amount=amount) if amount else None,
                            description=f"{action}: {description}" if description else action,
                            tags=["import", "schwab"],
                            )
                        transactions.append(tx)

                    except Exception as e:
                        warnings.append(f"Row {row_num}: error creating transaction: {e}")
                        continue

                    # Handle fees as separate transaction
                    fees = _parse_schwab_amount(row.get(COL_FEES, ""))
                    if fees and fees != 0:
                        try:
                            fee_tx = TXCreateItem(
                                broker_id=broker_id,
                                asset_id=asset_id,
                                type=TransactionType.FEE,
                                date=tx_date,
                                quantity=Decimal("0"),
                                cash=Currency(code="USD", amount=-abs(fees)),
                                description=f"Commission: {symbol}" if symbol else "Commission",
                                tags=["import", "schwab", "commission"],
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
            "Schwab file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets)
            )

        return transactions, warnings, extracted_assets
