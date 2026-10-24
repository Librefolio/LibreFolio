"""
Swissquote Broker Report Import Plugin.

This plugin parses Swissquote semicolon-separated CSV exports.

**File Format Characteristics:**
- First line: column headers
- Separator: semicolon
- Date format: DD-MM-YYYY HH:MM:SS
- Dot decimal numbers

**Supported Transaction Types:**
- Buy → BUY
- Sell → SELL
- Dividend → DIVIDEND
- Custody fee / fee → FEE
- Debit → WITHDRAWAL
- Credit → DEPOSIT
- Interest / Interests → INTEREST
- Tax / Withholding → TAX

**Limitations:**
- Forex credit/debit legs with the same ``Order #`` become one linked FX_CONVERSION pair (a
  credit and a debit, in two currencies, no costs). A leg without its partner, an order with
  more than two legs, a leg that carries costs, or two legs in one currency are not imported:
  they are listed with the link to open an issue.
- Costs and accrued interest are folded into the transaction description rather
  than emitted as separate transactions to avoid double-counting Net Amount.
"""

from __future__ import annotations

import csv
import uuid
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMExtractedAssetInfo, BRIMParseOutput, BRIMValidationIssue
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.brim_providers import _brim_io as io
from backend.app.services.provider_registry import register_provider

logger = structlog.get_logger(__name__)


COL_DATE = "Date"
COL_ORDER = "Order #"
COL_TRANSACTION = "Transaction"
COL_SYMBOL = "Symbol"
COL_NAME = "Name"
COL_ISIN = "ISIN"
COL_QUANTITY = "Quantity"
COL_UNIT_PRICE = "Unit price"
COL_COSTS = "Costs"
COL_ACCRUED_INTEREST = "Accrued Interest"
COL_NET_AMOUNT = "Net Amount"
COL_BALANCE = "Balance"
COL_CURRENCY = "Currency"

SWISSQUOTE_HEADER = [
    COL_DATE,
    COL_ORDER,
    COL_TRANSACTION,
    COL_SYMBOL,
    COL_NAME,
    COL_ISIN,
    COL_QUANTITY,
    COL_UNIT_PRICE,
    COL_COSTS,
    COL_ACCRUED_INTEREST,
    COL_NET_AMOUNT,
    COL_BALANCE,
    COL_CURRENCY,
]


def _parse_swissquote_date(value: str) -> Optional[date_type]:
    """Parse Swissquote DD-MM-YYYY HH:MM:SS dates."""
    value = value.strip()
    if not value:
        return None

    for fmt in ("%d-%m-%Y %H:%M:%S", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def _parse_swissquote_number(value: str) -> Optional[Decimal]:
    """Parse Swissquote dot-decimal numbers."""
    value = value.strip().replace('"', "")
    if not value:
        return None

    value = value.replace("'", "").replace(" ", "")
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


# Namespace of the link ids of the forex pairs: the same file always gives the same ids.
_LINK_NAMESPACE = uuid.UUID("5d2a0c0e-6f43-4c53-9a35-3b6a8c1e2f10")


def _forex_pair(order: str, legs: List[Tuple[int, Dict[str, str]]]) -> Optional[List[Tuple[Tuple[int, Dict[str, str]], Tuple[date_type, str, Decimal]]]]:
    """The two legs of a currency conversion, each with its (date, currency, signed Net Amount); ``None`` when they are not a clean pair.

    A clean pair is an order number that names exactly two legs: one ``Forex credit`` (money in, positive) and one ``Forex debit``
    (money out, negative), in two different currencies, each with a date, an amount and no costs: a cost on a leg would be
    inside or outside its Net Amount, which the file does not say.
    """
    if not order or len(legs) != 2:
        return None
    parsed = []
    for leg in legs:
        row = leg[1]
        tx_date = _parse_swissquote_date(row.get(COL_DATE, ""))
        amount = _parse_swissquote_number(row.get(COL_NET_AMOUNT, ""))
        currency = row.get(COL_CURRENCY, "").strip().upper()
        costs = _parse_swissquote_number(row.get(COL_COSTS, ""))
        if tx_date is None or amount is None or amount == 0 or not currency or (costs is not None and costs != 0):
            return None
        is_credit = row.get(COL_TRANSACTION, "").strip().lower() == "forex credit"
        if (amount > 0) != is_credit:
            return None
        parsed.append((leg, (tx_date, currency, amount)))
    first, second = parsed[0][1], parsed[1][1]
    if first[1] == second[1] or (first[2] > 0) == (second[2] > 0):
        return None  # one currency, or two credits / two debits
    return parsed


def _map_swissquote_transaction(value: str) -> Optional[TransactionType]:
    """Map Swissquote transaction labels to TransactionType."""
    tx = value.strip().lower()
    if not tx:
        return None
    if tx in {"buy", "sell", "dividend", "debit", "credit"}:
        return {
            "buy": TransactionType.BUY,
            "sell": TransactionType.SELL,
            "dividend": TransactionType.DIVIDEND,
            "debit": TransactionType.WITHDRAWAL,
            "credit": TransactionType.DEPOSIT,
        }[tx]
    if "interest" in tx:
        return TransactionType.INTEREST
    if "withholding" in tx or "tax" in tx:
        return TransactionType.TAX
    if "fee" in tx:
        return TransactionType.FEE
    return None


@register_provider(BRIMProviderRegistry)
class SwissquoteBrokerProvider(BRIMProvider):
    """Swissquote CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_swissquote"

    @property
    def provider_name(self) -> str:
        return "Swissquote"

    @property
    def description(self) -> str:
        return "Import Swissquote CSV exports for trades, dividends, cash movements, fees, taxes, interest and currency exchanges."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://www.swissquote.com/favicon.ico"

    @property
    def plugin_version(self) -> str:
        # 1.2.0 — the two forex legs of an order are imported as one linked FX_CONVERSION pair (W-B87).
        # 1.1.0 — the rows left out (forex legs, unknown or unreadable rows) are listed in shared notices with the link to open an issue (W-B87).
        return "1.2.0"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Swissquote format by checking the exact distinctive header."""
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=3)
            first_line = content.split("\n")[0].strip()
            header = next(csv.reader([first_line], delimiter=";"))
            return header == SWISSQUOTE_HEADER
        except Exception:
            return False

    def _pair_forex_legs(
        self,
        forex_legs: Dict[str, List[Tuple[int, Dict[str, str]]]],
        broker_id: int,
        transactions: List[TXCreateItem],
        validation_issues: List[BRIMValidationIssue],
        skips: io.RowSkips,
    ) -> None:
        """One linked FX_CONVERSION pair per order of exactly two legs, a credit and a debit; every other leg is listed (W-B87)."""
        for order, legs in forex_legs.items():
            pair = _forex_pair(order, legs)
            if pair is None:
                for row_num, row in legs:
                    skips.unknown(row_num, row, f"forex leg not imported: '{row.get(COL_TRANSACTION, '').strip()}'")
                continue
            link_uuid = str(uuid.uuid5(_LINK_NAMESPACE, f"swissquote:{order}:{legs[0][1].get(COL_DATE, '').strip()}"))
            for (row_num, row), (tx_date, currency, amount) in pair:
                self._create_transaction(
                    row_num=row_num,
                    transactions=transactions,
                    validation_issues=validation_issues,
                    context=row.get(COL_TRANSACTION, "").strip(),
                    broker_id=broker_id,
                    asset_id=None,
                    type=TransactionType.FX_CONVERSION,
                    date=tx_date,
                    quantity=Decimal("0"),
                    cash=Currency(code=currency, amount=amount),
                    description=f"Forex order {order}",
                    link_uuid=link_uuid,
                    tags=["import", "swissquote"],
                )

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:  # noqa: C901 — flat row loop: validation guards and per-type sign dispatch, no nested logic
        """Parse Swissquote CSV export file."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets_raw: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE
        skips = io.RowSkips()
        forex_legs: Dict[str, List[Tuple[int, Dict[str, str]]]] = {}

        detected_delim = self.detect_csv_delimiter(file_path)

        try:
            with self._open_text(file_path, newline="") as f:
                reader = csv.DictReader(f, delimiter=detected_delim)
                if reader.fieldnames != SWISSQUOTE_HEADER:
                    raise BRIMParseError("Unexpected Swissquote CSV header")
                skips.set_headers(reader.fieldnames)

                row_num = 1
                for row in reader:
                    row_num += 1
                    raw_tx = row.get(COL_TRANSACTION, "").strip()
                    tx_label = raw_tx.lower()
                    if tx_label in {"forex credit", "forex debit"}:
                        # A currency conversion is two rows: it is paired after the loop (W-B87).
                        forex_legs.setdefault(row.get(COL_ORDER, "").strip(), []).append((row_num, row))
                        continue

                    tx_type = _map_swissquote_transaction(raw_tx)
                    if tx_type is None:
                        skips.unknown(row_num, row, f"unknown transaction: '{raw_tx}'")
                        continue

                    tx_date = _parse_swissquote_date(row.get(COL_DATE, ""))
                    if not tx_date:
                        skips.unreadable(row_num, row, f"invalid date: '{row.get(COL_DATE, '')}'")
                        continue

                    amount = _parse_swissquote_number(row.get(COL_NET_AMOUNT, ""))
                    if amount is None or amount == 0:
                        skips.unreadable(row_num, row, "missing or zero net amount")
                        continue

                    currency = row.get(COL_CURRENCY, "").strip().upper()
                    if not currency:
                        skips.unreadable(row_num, row, "missing currency")
                        continue

                    quantity = _parse_swissquote_number(row.get(COL_QUANTITY, ""))
                    if quantity is None:
                        quantity = Decimal("0")

                    symbol = row.get(COL_SYMBOL, "").strip()
                    isin = row.get(COL_ISIN, "").strip()
                    name = row.get(COL_NAME, "").strip()
                    asset_id: Optional[int] = None

                    asset_required = tx_type in [TransactionType.BUY, TransactionType.SELL, TransactionType.DIVIDEND]
                    if asset_required:
                        asset_key = isin or symbol
                        if not asset_key:
                            skips.unreadable(row_num, row, f"{tx_type.value} without an ISIN or a symbol")
                            continue
                        if asset_key in asset_to_fake_id:
                            asset_id = asset_to_fake_id[asset_key]
                        else:
                            asset_id = next_fake_id
                            asset_to_fake_id[asset_key] = asset_id
                            extracted_assets_raw[asset_id] = {
                                "extracted_symbol": symbol if symbol else None,
                                "extracted_isin": isin if isin else None,
                                "extracted_name": name if name else None,
                            }
                            next_fake_id -= 1

                    if tx_type == TransactionType.BUY:
                        if quantity <= 0:
                            skips.unreadable(row_num, row, "BUY without a positive quantity")
                            continue
                        quantity = abs(quantity)
                        amount = -abs(amount)
                    elif tx_type == TransactionType.SELL:
                        if quantity <= 0:
                            skips.unreadable(row_num, row, "SELL without a positive quantity")
                            continue
                        quantity = -abs(quantity)
                        amount = abs(amount)
                    elif tx_type == TransactionType.DIVIDEND:
                        if quantity != 0:
                            warnings.append(f"Row {row_num}: DIVIDEND source quantity '{quantity}' discarded")
                        quantity = Decimal("0")
                        amount = abs(amount)
                    elif tx_type in (TransactionType.INTEREST, TransactionType.DEPOSIT):
                        quantity = Decimal("0")
                        amount = abs(amount)
                    else:
                        quantity = Decimal("0")
                        amount = -abs(amount)

                    description_parts = [raw_tx]
                    if name:
                        description_parts.append(name)
                    costs = _parse_swissquote_number(row.get(COL_COSTS, ""))
                    if costs and costs != 0:
                        description_parts.append(f"costs {currency} {costs}")
                    accrued_interest = _parse_swissquote_number(row.get(COL_ACCRUED_INTEREST, ""))
                    if accrued_interest and accrued_interest != 0:
                        description_parts.append(f"accrued interest {currency} {accrued_interest}")
                    description = "; ".join(description_parts)

                    self._create_transaction(
                        row_num=row_num,
                        transactions=transactions,
                        validation_issues=validation_issues,
                        context=raw_tx,
                        broker_id=broker_id,
                        asset_id=asset_id,
                        type=tx_type,
                        date=tx_date,
                        quantity=quantity,
                        cash=Currency(code=currency, amount=amount),
                        description=description,
                        tags=["import", "swissquote"],
                    )

            self._pair_forex_legs(forex_legs, broker_id, transactions, validation_issues, skips)

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
            "Swissquote file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets_typed),
        )

        return BRIMParseOutput(
            transactions=transactions,
            warnings=[*warnings, *skips.notices()],
            validation_issues=validation_issues,
            extracted_assets=extracted_assets_typed,
        )

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/swissquote/"

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "swissquote"
