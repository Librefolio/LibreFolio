"""
Saxo Broker Report Import Plugin.

This plugin parses Saxo CSV exports with comma-separated columns.

**File Format Characteristics:**
- First line: column headers
- Separator: comma
- Date format: DD-Mon-YYYY (e.g. 02-Apr-2025)
- Amounts may use comma or dot decimals
- Saxo ticker suffixes such as ``:xams`` are kept as exported

**Supported Transaction Types:**
- Trade rows with Event ``Buy <qty> @ <price> <currency>`` → BUY
- Trade rows with Event ``Sell <qty> @ <price> <currency>`` → SELL
  (localized verbs are supported, e.g. Dutch ``Koop``/``Verkoop``)
- Corporate action rows with Event ``Dividend`` → DIVIDEND
- Cash Transfer rows with Event ``Deposit`` → DEPOSIT
- Cash Transfer rows with Event ``Withdrawal`` → WITHDRAWAL
- Cash amount rows (e.g. ``Custody Fee``) → FEE

**Limitations:**
- Localized trade verbs beyond the mapped set and unknown type/event
  combinations are skipped with warnings instead of emitting schema-invalid
  transactions.
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
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMExtractedAssetInfo, BRIMParseOutput, BRIMValidationIssue
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.provider_registry import BRIMProviderRegistry, register_provider

logger = structlog.get_logger(__name__)


COL_CLIENT_ID = "Client ID"
COL_TRADE_DATE = "Trade Date"
COL_VALUE_DATE = "Value Date"
COL_TYPE = "Type"
COL_INSTRUMENT = "Instrument"
COL_ISIN = "Instrument ISIN"
COL_CURRENCY = "Instrument currency"
COL_EXCHANGE = "Exchange Description"
COL_SYMBOL = "Instrument Symbol"
COL_EVENT = "Event"
COL_AMOUNT = "Amount"
COL_ORDER_ID = "Order ID"
COL_CONVERSION_RATE = "Conversion Rate"

SAXO_HEADER = [
    COL_CLIENT_ID,
    COL_TRADE_DATE,
    COL_VALUE_DATE,
    COL_TYPE,
    COL_INSTRUMENT,
    COL_ISIN,
    COL_CURRENCY,
    COL_EXCHANGE,
    COL_SYMBOL,
    COL_EVENT,
    COL_AMOUNT,
    COL_ORDER_ID,
    COL_CONVERSION_RATE,
]


def _parse_saxo_date(value: str) -> Optional[date_type]:
    """Parse Saxo DD-Mon-YYYY dates."""
    value = value.strip()
    if not value:
        return None

    for fmt in ("%d-%b-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def _parse_saxo_number(value: str) -> Optional[Decimal]:
    """Parse Saxo decimal values with comma or dot decimal separators."""
    value = value.strip().replace('"', "")
    if not value:
        return None

    value = value.replace(" ", "")
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        value = value.replace(",", ".")

    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _parse_trade_event(event: str) -> Optional[tuple[TransactionType, Decimal, Decimal, str]]:
    """Parse Event values like 'Sell 3 @ 139.74 USD' (localized verbs supported)."""
    parts = event.strip().split()
    if len(parts) != 5 or parts[2] != "@":
        return None

    verb = parts[0].lower()
    # English + localized buy/sell verbs (e.g. Dutch Koop/Verkoop)
    buy_verbs = {"buy", "koop", "kaufen", "achat", "acquisto", "compra"}
    sell_verbs = {"sell", "verkoop", "verkauf", "vente", "vendita", "venta"}
    if verb in buy_verbs:
        tx_type = TransactionType.BUY
    elif verb in sell_verbs:
        tx_type = TransactionType.SELL
    else:
        return None

    quantity = _parse_saxo_number(parts[1])
    price = _parse_saxo_number(parts[3])
    currency = parts[4].upper().strip()
    if quantity is None or price is None or quantity <= 0 or not currency:
        return None

    return tx_type, quantity, price, currency


@register_provider(BRIMProviderRegistry)
class SaxoBrokerProvider(BRIMProvider):
    """Saxo CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_saxo"

    @property
    def provider_name(self) -> str:
        return "Saxo"

    @property
    def description(self) -> str:
        return "Import Saxo CSV exports: equity trades, dividends, cash deposits/withdrawals and custody fees."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://home.saxo/favicon.ico"

    @property
    def plugin_version(self) -> str:
        return "1.1.0"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Saxo format by checking the exact distinctive header."""
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=3)
            first_line = content.split("\n")[0].strip()
            header = next(csv.reader([first_line], delimiter=","))
            return header == SAXO_HEADER
        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """Parse Saxo CSV export file."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets_raw: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        detected_delim = self.detect_csv_delimiter(file_path)

        try:
            with open(file_path, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f, delimiter=detected_delim)
                if reader.fieldnames != SAXO_HEADER:
                    raise BRIMParseError("Unexpected Saxo CSV header")

                row_num = 1
                for row in reader:
                    row_num += 1
                    row_type = row.get(COL_TYPE, "").strip()
                    event = row.get(COL_EVENT, "").strip()
                    context = f"{row_type}: {event}" if event else row_type

                    tx_date = _parse_saxo_date(row.get(COL_TRADE_DATE, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid trade date '{row.get(COL_TRADE_DATE, '')}', skipping")
                        continue

                    amount = _parse_saxo_number(row.get(COL_AMOUNT, ""))
                    if amount is None or amount == 0:
                        warnings.append(f"Row {row_num}: missing or zero amount for '{context}', skipping")
                        continue

                    currency = row.get(COL_CURRENCY, "").strip().upper()
                    if not currency:
                        warnings.append(f"Row {row_num}: missing instrument currency for '{context}', skipping")
                        continue

                    tx_type: Optional[TransactionType] = None
                    quantity = Decimal("0")
                    price: Optional[Decimal] = None
                    asset_required = False

                    if row_type in ("Trade", "Transactie"):
                        trade = _parse_trade_event(event)
                        if trade is None:
                            warnings.append(f"Row {row_num}: unsupported Saxo trade event '{event}', skipping")
                            continue
                        tx_type, quantity, price, event_currency = trade
                        asset_required = True
                        if event_currency != currency:
                            warnings.append(f"Row {row_num}: event currency '{event_currency}' differs from instrument currency '{currency}', using '{currency}'")
                        if tx_type == TransactionType.BUY:
                            quantity = abs(quantity)
                            amount = -abs(amount)
                        else:
                            quantity = -abs(quantity)
                            amount = abs(amount)
                    elif row_type == "Corporate action" and event.lower() == "dividend":
                        tx_type = TransactionType.DIVIDEND
                        asset_required = True
                        amount = abs(amount)
                    elif row_type == "Cash Transfer":
                        event_lower = event.lower()
                        if event_lower == "deposit":
                            tx_type = TransactionType.DEPOSIT
                            amount = abs(amount)
                        elif event_lower == "withdrawal":
                            tx_type = TransactionType.WITHDRAWAL
                            amount = -abs(amount)
                        else:
                            warnings.append(f"Row {row_num}: unsupported Saxo cash transfer event '{event}', skipping")
                            continue
                    elif row_type == "Cash amount":
                        # Cash-account charges such as 'Custody Fee' (always a debit).
                        tx_type = TransactionType.FEE
                        amount = -abs(amount)
                    else:
                        warnings.append(f"Row {row_num}: unsupported Saxo type/event '{context}', skipping")
                        continue

                    asset_id: Optional[int] = None
                    if asset_required:
                        ticker = row.get(COL_SYMBOL, "").strip()
                        isin = row.get(COL_ISIN, "").strip()
                        name = row.get(COL_INSTRUMENT, "").strip()
                        asset_key = isin or ticker
                        if not asset_key:
                            warnings.append(f"Row {row_num}: {tx_type.value} requires ISIN or ticker, skipping")
                            continue

                        if asset_key in asset_to_fake_id:
                            asset_id = asset_to_fake_id[asset_key]
                        else:
                            asset_id = next_fake_id
                            asset_to_fake_id[asset_key] = asset_id
                            extracted_assets_raw[asset_id] = {
                                "extracted_symbol": ticker if ticker else None,
                                "extracted_isin": isin if isin else None,
                                "extracted_name": name if name else None,
                            }
                            next_fake_id -= 1

                    description = context
                    if price is not None:
                        description = f"{context}; price {currency} {price}"

                    self._create_transaction(
                        row_num=row_num,
                        transactions=transactions,
                        validation_issues=validation_issues,
                        context=context,
                        broker_id=broker_id,
                        asset_id=asset_id,
                        type=tx_type,
                        date=tx_date,
                        quantity=quantity,
                        cash=Currency(code=currency, amount=amount),
                        description=description,
                        tags=["import", "saxo"],
                    )

        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}") from None
        except BRIMParseError:
            raise
        except Exception as e:
            raise BRIMParseError(f"Error parsing file: {e}") from e

        if not transactions:
            warnings.append("No valid transactions found in file")

        extracted_assets_typed: Dict[int, BRIMExtractedAssetInfo] = {
            fake_id: BRIMExtractedAssetInfo(
                extracted_symbol=info.get("extracted_symbol"),
                extracted_isin=info.get("extracted_isin"),
                extracted_name=info.get("extracted_name"),
            )
            for fake_id, info in extracted_assets_raw.items()
        }

        logger.info(
            "Saxo file parsed",
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
        return "/mkdocs/user/transactions/import/saxo/"

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "saxo"
