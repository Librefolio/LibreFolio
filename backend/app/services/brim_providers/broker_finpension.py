"""
Finpension Broker Report Import Plugin.

This plugin parses CSV exports from Finpension (Swiss pension platform).

**File Format Characteristics:**
- First line: column headers
- Separator: semicolon (;)
- Swiss format
- CHF as primary currency
- ISIN provided

**Supported Transaction Types:**
- Buy → BUY
- Sell → SELL
- Interests → INTEREST
- Flat-rate administrative fee → FEE
- Deposit → DEPOSIT

**Columns:**
- Date: YYYY-MM-DD
- Category: Transaction type
- Asset Name: Full asset name
- ISIN: Asset ISIN
- Number of Shares: Quantity
- Cash Flow: Amount
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
COL_CATEGORY = "Category"
COL_ASSET_NAME = "Asset Name"
COL_ISIN = "ISIN"
COL_SHARES = "Number of Shares"
COL_CASH_FLOW = "Cash Flow"

# Type mapping
TYPE_MAPPINGS: Dict[str, TransactionType] = {
    "buy": TransactionType.BUY,
    "sell": TransactionType.SELL,
    "interests": TransactionType.INTEREST,
    "flat-rate administrative fee": TransactionType.FEE,
    "deposit": TransactionType.DEPOSIT,
    "withdrawal": TransactionType.WITHDRAWAL,
    }


def _parse_finpension_date(value: str) -> Optional[date_type]:
    """Parse Finpension date format (YYYY-MM-DD)."""
    value = value.strip()
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_finpension_number(value: str) -> Optional[Decimal]:
    """Parse Finpension number."""
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
class FinpensionBrokerProvider(BRIMProvider):
    """Finpension (Swiss pension) CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_finpension"

    @property
    def provider_name(self) -> str:
        return "Finpension"

    @property
    def description(self) -> str:
        return (
            "Import transactions from Finpension CSV export. "
            "Supports Swiss pension fund investments."
        )

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> str:
        return "https://www.finpension.ch/favicon.ico"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Finpension format by checking for distinctive headers."""
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=3)
            first_line = content.split('\n')[0].lower() if content else ""

            # Finpension uses semicolon and has specific columns
            if ";" not in first_line:
                return False

            required = ["date", "category", "asset name", "isin", "number of shares", "cash flow"]
            return all(col in first_line for col in required)

        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> Tuple[List[TXCreateItem], List[str], Dict[int, Dict]]:
        """Parse Finpension CSV export file."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        extracted_assets: Dict[int, Dict] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=";")
                row_num = 1

                for row in reader:
                    row_num += 1

                    category = row.get(COL_CATEGORY, "").strip().lower()
                    if not category:
                        continue

                    # Map transaction type
                    tx_type = TYPE_MAPPINGS.get(category)

                    if tx_type is None:
                        warnings.append(f"Row {row_num}: unknown category '{category}', skipping")
                        continue

                    # Parse date
                    tx_date = _parse_finpension_date(row.get(COL_DATE, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date, skipping")
                        continue

                    # Get asset info
                    asset_name = row.get(COL_ASSET_NAME, "").strip()
                    isin = row.get(COL_ISIN, "").strip()

                    # Asset required for some types
                    asset_id = None
                    asset_required = tx_type in [
                        TransactionType.BUY,
                        TransactionType.SELL,
                        ]

                    if asset_required:
                        if not isin and not asset_name:
                            warnings.append(f"Row {row_num}: {tx_type.value} requires asset, skipping")
                            continue

                        asset_key = isin if isin else asset_name

                        if asset_key in asset_to_fake_id:
                            asset_id = asset_to_fake_id[asset_key]
                        else:
                            asset_id = next_fake_id
                            asset_to_fake_id[asset_key] = asset_id

                            extracted_assets[asset_id] = {
                                "extracted_symbol": None,
                                "extracted_isin": isin if isin else None,
                                "extracted_name": asset_name if asset_name else None,
                                }

                            next_fake_id -= 1

                    # Parse amount
                    amount = _parse_finpension_number(row.get(COL_CASH_FLOW, ""))

                    # Parse quantity
                    quantity = _parse_finpension_number(row.get(COL_SHARES, ""))
                    if quantity is None:
                        quantity = Decimal("0")

                    # Finpension already has correct signs

                    # Create transaction
                    try:
                        tx = TXCreateItem(
                            broker_id=broker_id,
                            asset_id=asset_id,
                            type=tx_type,
                            date=tx_date,
                            quantity=quantity,
                            cash=Currency(code="CHF", amount=amount) if amount else None,
                            description=f"{category}: {asset_name}" if asset_name else category,
                            tags=["import", "finpension"],
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

        logger.info(
            "Finpension file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets)
            )

        return transactions, warnings, extracted_assets
