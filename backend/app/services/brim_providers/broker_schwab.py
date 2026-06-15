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
- Buy / Reinvest Shares / Long Term Cap Gain Reinvest / Prior Year Reinvest → BUY
- Sell → SELL
- Dividend / Reinvest Dividend / Qualified Dividend / Cash Dividend /
  Non-Qualified Div / Special Non-Qual Div / Prior Year Cash Div → DIVIDEND
- Credit Interest → INTEREST
- Wire Funds / MoneyLink Transfer → DEPOSIT/WITHDRAWAL (sign determines direction)
- Wire Sent → WITHDRAWAL
- Advisor Fee / ADR Mgmt Fee → FEE
- Foreign Tax Paid → TAX

**Skipped (no equivalent in project model):**
- Stock Split / Reverse Split / Stock Merger / Name Change / Spin-Off
- Journaled Shares / Conversion / Internal Transfer / Stock Div Dist

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
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional

import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import (
    FAKE_ASSET_ID_BASE,
    BRIMExtractedAssetInfo,
    BRIMParseOutput,
    BRIMPreviewColumn,
    BRIMValidationIssue,
)
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.provider_registry import BRIMProviderRegistry, register_provider

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

# Type mapping (exact lowercase match via `pattern in action`)
TYPE_MAPPINGS: Dict[str, TransactionType] = {
    # BUY
    "buy": TransactionType.BUY,
    "reinvest shares": TransactionType.BUY,       # shares purchased with reinvested dividend
    # SELL
    "sell": TransactionType.SELL,
    # DIVIDEND — Schwab splits reinvestment into two rows:
    #   "reinvest dividend" (cash received) + "reinvest shares" (shares bought)
    "dividend": TransactionType.DIVIDEND,
    "qualified dividend": TransactionType.DIVIDEND,
    "cash dividend": TransactionType.DIVIDEND,
    "reinvest dividend": TransactionType.DIVIDEND, # cash portion of reinvested dividend
    "qual div reinvest": TransactionType.DIVIDEND,
    "non-qualified div": TransactionType.DIVIDEND,
    "special non qual div": TransactionType.DIVIDEND,
    "pr yr cash div": TransactionType.DIVIDEND,
    "pr yr div reinvest": TransactionType.DIVIDEND, # prior year dividend cash portion
    "long term cap gain reinvest": TransactionType.DIVIDEND,  # cap gains distribution
    # INTEREST
    "credit interest": TransactionType.INTEREST,
    # DEPOSIT / WITHDRAWAL (sign of Amount determines direction)
    "wire funds": TransactionType.DEPOSIT,
    "moneylink transfer": TransactionType.DEPOSIT,
    "wire sent": TransactionType.WITHDRAWAL,        # outgoing wire always withdrawal
    "internal transfer": TransactionType.DEPOSIT,   # cash transfer between accounts (sign-corrected below)
    # FEE
    "advisor fee": TransactionType.FEE,
    "adr mgmt fee": TransactionType.FEE,
    # TAX
    "foreign tax paid": TransactionType.TAX,
}

# Corporate actions mapped to ADJUSTMENT
# Note: stock splits and reverse splits are mapped to ADJUSTMENT.
# It is expected that the price provider adjusts the asset historical prices accordingly starting from the action date.
CORPORATE_ACTIONS: frozenset[str] = frozenset({
    "stock split",
    "reverse split",
    "stock merger",
    "name change",
    "spin-off",
    "journaled shares",
    "conversion",
    "stock div dist",   # stock dividend (shares, not cash)
})


def _parse_schwab_date(value: str) -> Optional[date_type]:
    """Parse Schwab US date format (MM/DD/YYYY).

    Also handles the "MM/DD/YYYY as of MM/DD/YYYY" notation Schwab uses
    for corporate actions (trade date as of settlement date) — the trade
    date (first date) is used.
    """
    value = value.strip()
    if not value:
        return None

    # Strip " as of MM/DD/YYYY" suffix if present (corporate action settlement date)
    if " as of " in value:
        value = value.split(" as of ")[0].strip()

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
    value = value.replace("$", "").replace('"', "")

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
        return "Import transactions from Charles Schwab CSV export. " "Supports stocks, ETFs, dividends, and interest."

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
            first_line = content.split("\n")[0].lower() if content else ""

            # Schwab specific columns
            required = [
                "date",
                "action",
                "symbol",
                "description",
                "quantity",
                "fees & comm",
                "amount",
            ]
            return all(col in first_line for col in required)

        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """Parse Charles Schwab CSV export file."""
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

                    action = row.get(COL_ACTION, "").strip().lower()
                    if not action:
                        continue

                    # Map transaction type
                    tx_type = None
                    for pattern, mapped_type in TYPE_MAPPINGS.items():
                        if pattern in action:
                            tx_type = mapped_type
                            break

                    is_corporate = False
                    if tx_type is None:
                        # Check if it's a known corporate action
                        is_corporate = any(ca in action for ca in CORPORATE_ACTIONS)
                        if is_corporate:
                            tx_type = TransactionType.ADJUSTMENT
                        else:
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
                        TransactionType.ADJUSTMENT,
                    ]

                    if asset_required:
                        if not symbol:
                            if tx_type == TransactionType.DIVIDEND:
                                # Dividend from a cash fund (e.g. money-market) with no ticker
                                # → treat as INTEREST (cash yield, no asset needed)
                                warnings.append(
                                    f"Row {row_num}: DIVIDEND '{description}' has no ticker"
                                    f" — reclassified as INTEREST"
                                )
                                tx_type = TransactionType.INTEREST
                            else:
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

                    # If it's a corporate action ADJUSTMENT, it must have a non-zero quantity
                    if tx_type == TransactionType.ADJUSTMENT and quantity == Decimal("0"):
                        warnings.append(
                            f"Row {row_num}: corporate action '{action}' has quantity = 0, skipping"
                        )
                        continue

                    # Adjust signs (Schwab already has correct signs in Amount)
                    if tx_type == TransactionType.SELL and quantity > 0:
                        quantity = -quantity

                    # For cash movements (DEPOSIT/WITHDRAWAL), Schwab uses the Amount sign
                    # to indicate direction. MoneyLink Transfer with -$X is a withdrawal,
                    # with +$X is a deposit. Flip the type to match the actual cash flow.
                    if tx_type == TransactionType.DEPOSIT and amount is not None and amount < 0:
                        tx_type = TransactionType.WITHDRAWAL
                    elif tx_type == TransactionType.WITHDRAWAL and amount is not None and amount > 0:
                        tx_type = TransactionType.DEPOSIT

                    # Create transaction
                    tx_tags = ["import", "schwab"]
                    if is_corporate:
                        tx_tags.append("corporate-action")

                    self._create_transaction(
                        row_num=row_num,
                        transactions=transactions,
                        validation_issues=validation_issues,
                        context=f"{action}: {description}" if description else action,
                        broker_id=broker_id,
                        asset_id=asset_id,
                        type=tx_type,
                        date=tx_date,
                        quantity=quantity,
                        cash=Currency(code="USD", amount=amount) if amount else None,
                        description=f"{action}: {description}" if description else action,
                        tags=tx_tags,
                    )

                    # Handle fees as separate transaction
                    fees = _parse_schwab_amount(row.get(COL_FEES, ""))
                    if fees and fees != 0:
                        self._create_transaction(
                            row_num=row_num,
                            transactions=transactions,
                            validation_issues=validation_issues,
                            context=f"Commission: {symbol}" if symbol else "Commission",
                            broker_id=broker_id,
                            asset_id=asset_id,
                            type=TransactionType.FEE,
                            date=tx_date,
                            quantity=Decimal("0"),
                            cash=Currency(code="USD", amount=-abs(fees)),
                            description=f"Commission: {symbol}" if symbol else "Commission",
                            tags=["import", "schwab", "commission"],
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
            "Schwab file parsed",
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
        return "/mkdocs/user/brokers/schwab/"

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
        return "schwab"
