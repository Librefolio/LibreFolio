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
- Dividend → DIVIDEND
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
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional

import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMExtractedAssetInfo, BRIMParseOutput, BRIMPreviewColumn, BRIMValidationIssue
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.provider_registry import BRIMProviderRegistry, register_provider

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
    "dividend": TransactionType.DIVIDEND,
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
        return "Import transactions from Finpension CSV export. " "Supports Swiss pension fund investments."

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
            first_line = content.split("\n")[0].lower() if content else ""

            # Finpension uses semicolon and has specific columns
            if ";" not in first_line:
                return False

            required = ["date", "category", "asset name", "isin", "number of shares", "cash flow"]
            return all(col in first_line for col in required)

        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """Parse Finpension CSV export file."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        detected_delim = self.detect_csv_delimiter(file_path)

        try:
            with open(file_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=detected_delim)
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
                        TransactionType.DIVIDEND,
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
                    self._create_transaction(
                        row_num=row_num,
                        transactions=transactions,
                        validation_issues=validation_issues,
                        context=f"{category}: {asset_name}" if asset_name else category,
                        broker_id=broker_id,
                        asset_id=asset_id,
                        type=tx_type,
                        date=tx_date,
                        quantity=quantity,
                        cash=Currency(code="CHF", amount=amount) if amount else None,
                        description=f"{category}: {asset_name}" if asset_name else category,
                        tags=["import", "finpension"],
                    )

        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}") from None
        except Exception as e:
            raise BRIMParseError(f"Error parsing file: {e}") from e

        if not transactions:
            warnings.append("No valid transactions found in file")

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
            "Finpension file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets_typed),
        )

        return BRIMParseOutput(
            transactions=transactions,
            warnings=warnings,
            validation_issues=validation_issues,
            extracted_assets=extracted_assets_typed,
        )

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/finpension/"

    def preview_columns(self) -> List[BRIMPreviewColumn]:
        return [
            BRIMPreviewColumn(key="date", label="brim.preview.date", type="date", width="110px", align="left"),
            BRIMPreviewColumn(key="type", label="brim.preview.type", type="enum", width="110px", align="left"),
            BRIMPreviewColumn(key="quantity", label="brim.preview.quantity", type="number", width="110px", align="right"),
            BRIMPreviewColumn(key="asset", label="brim.preview.asset", type="text", align="left"),
            BRIMPreviewColumn(key="cash_amount", label="brim.preview.cash_amount", type="number", width="120px", align="right"),
            BRIMPreviewColumn(key="cash_currency", label="brim.preview.cash_currency", type="text", width="70px", align="center"),
        ]

    @property
    def test_file_pattern(self) -> Optional[str]:
        """Filename pattern for auto-detection tests."""
        return "finpension"
