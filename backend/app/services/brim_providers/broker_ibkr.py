"""
Interactive Brokers (IBKR) Report Import Plugin.

This plugin parses CSV exports from Interactive Brokers.

**File Format Characteristics:**
- First line: column headers (quoted)
- All values are quoted
- Separator: comma
- Date format: YYYYMMDD
- Multi-currency support

**Supported Transaction Types:**
- BUY → BUY
- SELL → SELL
- Commission tracked in IBCommission column → FEE

**Columns:**
- Buy/Sell: Transaction direction
- TradeDate: Date (YYYYMMDD)
- ISIN: Asset ISIN
- Quantity: Number of shares (negative for sell)
- TradeMoney: Total trade value
- CurrencyPrimary: Currency
- IBCommission: Broker commission
- IBCommissionCurrency: Commission currency
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

COL_DIRECTION = "Buy/Sell"
COL_DATE = "TradeDate"
COL_ISIN = "ISIN"
COL_QUANTITY = "Quantity"
COL_TRADE_MONEY = "TradeMoney"
COL_CURRENCY = "CurrencyPrimary"
COL_COMMISSION = "IBCommission"
COL_COMMISSION_CURRENCY = "IBCommissionCurrency"


def _parse_ibkr_date(value: str) -> Optional[date_type]:
    """Parse IBKR date format (YYYYMMDD)."""
    value = value.strip().replace('"', '')
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def _parse_ibkr_number(value: str) -> Optional[Decimal]:
    """Parse IBKR number (quoted, US format)."""
    value = value.strip().replace('"', '')
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
class IBKRBrokerProvider(BRIMProvider):
    """
    Interactive Brokers (IBKR) CSV export import plugin.
    """

    @property
    def provider_code(self) -> str:
        return "broker_ibkr"

    @property
    def provider_name(self) -> str:
        return "Interactive Brokers"

    @property
    def description(self) -> str:
        return (
            "Import trades from Interactive Brokers CSV export. "
            "Supports stocks, ETFs, and FX trades with commissions."
        )

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> str:
        """Interactive Brokers logo."""
        return "https://www.interactivebrokers.com/favicon.ico"

    def can_parse(self, file_path: Path) -> bool:
        """Detect IBKR format by checking for distinctive quoted headers."""
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=3)
            first_line = content.split('\n')[0].lower() if content else ""

            # IBKR specific: quoted headers
            required = ['"buy/sell"', '"tradedate"', '"isin"', '"ibcommission"']
            return all(col in first_line for col in required)

        except Exception:
            return False

    def parse(
        self,
        file_path: Path,
        broker_id: int
    ) -> Tuple[List[TXCreateItem], List[str], Dict[int, BRIMExtractedAssetInfo]]:
        """Parse IBKR CSV export file."""
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

                    direction = row.get(COL_DIRECTION, "").strip().upper().replace('"', '')
                    if not direction:
                        continue

                    # Map direction to type
                    if direction == "BUY":
                        tx_type = TransactionType.BUY
                    elif direction == "SELL":
                        tx_type = TransactionType.SELL
                    else:
                        warnings.append(f"Row {row_num}: unknown direction '{direction}', skipping")
                        continue

                    # Parse date
                    tx_date = _parse_ibkr_date(row.get(COL_DATE, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date, skipping")
                        continue

                    # Get ISIN
                    isin = row.get(COL_ISIN, "").strip().replace('"', '')

                    # Handle FX trades (no ISIN, negative large quantity)
                    quantity = _parse_ibkr_number(row.get(COL_QUANTITY, ""))
                    if quantity is None:
                        quantity = Decimal("0")

                    if not isin:
                        # This might be an FX trade - skip for now
                        warnings.append(f"Row {row_num}: no ISIN (likely FX trade), skipping")
                        continue

                    # Get or create fake asset ID
                    if isin in asset_to_fake_id:
                        asset_id = asset_to_fake_id[isin]
                    else:
                        asset_id = next_fake_id
                        asset_to_fake_id[isin] = asset_id

                        extracted_assets[asset_id] = {
                            "extracted_symbol": None,
                            "extracted_isin": isin,
                            "extracted_name": None,
                            }

                        next_fake_id -= 1

                    # Parse amount
                    trade_money = _parse_ibkr_number(row.get(COL_TRADE_MONEY, ""))
                    currency = row.get(COL_CURRENCY, "USD").strip().upper().replace('"', '')
                    if not currency:
                        currency = "USD"

                    # Adjust signs
                    if tx_type == TransactionType.SELL and quantity > 0:
                        quantity = -quantity
                    if tx_type == TransactionType.BUY and trade_money and trade_money > 0:
                        trade_money = -trade_money

                    # Create main transaction
                    try:
                        tx = TXCreateItem(
                            broker_id=broker_id,
                            asset_id=asset_id,
                            type=tx_type,
                            date=tx_date,
                            quantity=quantity,
                            cash=Currency(code=currency, amount=trade_money) if trade_money else None,
                            description=f"IBKR {direction}: {isin}",
                            tags=["import", "ibkr"],
                            )
                        transactions.append(tx)

                    except Exception as e:
                        warnings.append(f"Row {row_num}: error creating transaction: {e}")
                        continue

                    # Handle commission as separate FEE transaction
                    commission = _parse_ibkr_number(row.get(COL_COMMISSION, ""))
                    if commission and commission != 0:
                        comm_currency = row.get(COL_COMMISSION_CURRENCY, currency).strip().upper().replace('"', '')
                        if not comm_currency:
                            comm_currency = currency

                        try:
                            fee_tx = TXCreateItem(
                                broker_id=broker_id,
                                asset_id=asset_id,
                                type=TransactionType.FEE,
                                date=tx_date,
                                quantity=Decimal("0"),
                                cash=Currency(code=comm_currency, amount=commission),
                                description=f"IBKR commission: {isin}",
                                tags=["import", "ibkr", "commission"],
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
            "IBKR file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets_typed)
            )

        return transactions, warnings, extracted_assets_typed

    @property
    def test_file_pattern(self) -> Optional[str]:
        """Filename pattern for auto-detection tests."""
        return "ibkr"
