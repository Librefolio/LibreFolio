"""
Investimental Broker Report Import Plugin.

Parses Investimental CSV order-update logs on a best-effort basis.

This is an ORDER-UPDATE log, not a clean execution ledger.  The parser groups
rows by ``Order ID`` and emits at most one transaction per order.  It selects
the latest update per order that is not a deleted/rejected request, requires an
execution marker (``Update Type`` = ``Fil`` or a non-zero ``Last Trade ID``), and
skips orders whose final state is cancelled/rejected/expired or never executed.

Known limits:
- Partial fills are collapsed into one best-effort transaction, so very complex
  order histories may need manual review.
- The file contains tickers only, no ISIN.
- If the final fill row carries zero ``Value``, cash is estimated as
  ``Price * Volume`` to avoid schema-invalid rows.
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

COL_ORDER_ID = "Order ID"
COL_SIDE = "Side"
COL_EXCHANGE = "Exchange"
COL_SYMBOL = "Symbol"
COL_PRICE = "Price"
COL_VOLUME = "Volume"
COL_VALUE = "Value"
COL_FEE = "Fee"
COL_ACCOUNT_NAME = "Account Name"
COL_LAST_TRADE_ID = "Last Trade ID"
COL_STATUS = "Status"
COL_UPDATE_TYPE = "Update Type"
COL_UPDATE_TIME = "Update Time"
COL_REQUEST_STATUS = "Request Status"

REQUIRED_COLUMNS = [
    COL_ORDER_ID,
    "Order Number",
    COL_SIDE,
    COL_EXCHANGE,
    COL_SYMBOL,
    "Market",
    COL_PRICE,
    COL_VOLUME,
    COL_VALUE,
    COL_FEE,
    COL_ACCOUNT_NAME,
    COL_LAST_TRADE_ID,
    COL_STATUS,
    COL_UPDATE_TYPE,
    COL_UPDATE_TIME,
    COL_REQUEST_STATUS,
]


def _parse_investimental_date(value: str) -> Optional[date_type]:
    """Parse Investimental update date/time."""
    value = value.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_investimental_datetime(value: str) -> Optional[datetime]:
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _parse_investimental_number(value: str) -> Optional[Decimal]:
    """Parse Investimental decimal numbers."""
    value = value.strip()
    if not value:
        return None
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None


def _extract_currency_from_account(value: str) -> Optional[str]:
    """Extract currency code from account name like 'JOHN DOE [RON]'."""
    value = value.strip()
    if "[" not in value or "]" not in value:
        return None
    code = value.rsplit("[", 1)[1].split("]", 1)[0].strip().upper()
    if not code:
        return None
    try:
        return Currency.validate_code(code)
    except ValueError:
        return None


def _row_is_deleted_or_rejected(row: Dict[str, str]) -> bool:
    request_status = (row.get(COL_REQUEST_STATUS) or "").strip().lower()
    return request_status in {"deleted", "rejected"}


def _row_has_execution_marker(row: Dict[str, str]) -> bool:
    update_type = (row.get(COL_UPDATE_TYPE) or "").strip().lower()
    last_trade_id = (row.get(COL_LAST_TRADE_ID) or "").strip()
    return update_type == "fil" or last_trade_id not in {"", "0"}


@register_provider(BRIMProviderRegistry)
class InvestimentalBrokerProvider(BRIMProvider):
    """Investimental order-update CSV import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_investimental"

    @property
    def provider_name(self) -> str:
        return "Investimental"

    @property
    def description(self) -> str:
        return "Import final executed transactions from Investimental CSV order-update logs. Cancellations, rejected requests, and unexecuted orders are skipped."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/investimental/"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "investimental"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Investimental format by distinctive order-log headers."""
        if file_path.suffix.lower() != ".csv":
            return False
        try:
            content = self._read_file_head(file_path, num_lines=2)
            first_line = content.splitlines()[0] if content else ""
            header = next(csv.reader([first_line]))
            return all(col in header for col in REQUIRED_COLUMNS)
        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """Parse Investimental CSV export file."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets_raw: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE
        orders: Dict[str, List[Dict[str, str]]] = {}
        row_numbers: Dict[str, List[int]] = {}
        skipped_cancelled = 0
        skipped_unexecuted = 0
        skipped_invalid = 0

        def get_asset_id(symbol: str) -> int:
            nonlocal next_fake_id
            symbol = symbol.strip().upper()
            if symbol in asset_to_fake_id:
                return asset_to_fake_id[symbol]
            asset_id = next_fake_id
            asset_to_fake_id[symbol] = asset_id
            extracted_assets_raw[asset_id] = {
                "extracted_symbol": symbol,
                "extracted_isin": None,
                "extracted_name": symbol,
            }
            next_fake_id -= 1
            return asset_id

        detected_delim = self.detect_csv_delimiter(file_path)

        try:
            with open(file_path, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f, delimiter=detected_delim)
                if not reader.fieldnames or not all(col in reader.fieldnames for col in REQUIRED_COLUMNS):
                    raise BRIMParseError("Unexpected Investimental header")

                row_num = 1
                for row in reader:
                    row_num += 1
                    order_id = (row.get(COL_ORDER_ID) or "").strip()
                    if not order_id:
                        skipped_invalid += 1
                        warnings.append(f"Row {row_num}: missing Order ID, skipping")
                        continue
                    orders.setdefault(order_id, []).append(row)
                    row_numbers.setdefault(order_id, []).append(row_num)

            for order_id, rows in orders.items():
                sorted_rows = sorted(rows, key=lambda r: _parse_investimental_datetime(r.get(COL_UPDATE_TIME, "")) or datetime.min)
                final_row = sorted_rows[-1]
                candidate_rows = [row for row in sorted_rows if not _row_is_deleted_or_rejected(row)]

                if not candidate_rows:
                    skipped_cancelled += 1
                    warnings.append(f"Order {order_id}: final state deleted/rejected, skipping")
                    continue

                has_execution = any(_row_has_execution_marker(row) for row in sorted_rows)
                final_request_status = (final_row.get(COL_REQUEST_STATUS) or "").strip().lower()
                final_update_type = (final_row.get(COL_UPDATE_TYPE) or "").strip().lower()
                if final_request_status in {"deleted", "rejected"} and not has_execution:
                    skipped_cancelled += 1
                    warnings.append(f"Order {order_id}: final state {final_request_status}, skipping")
                    continue
                if final_update_type in {"oot", "exp", "can"} and not has_execution:
                    skipped_cancelled += 1
                    warnings.append(f"Order {order_id}: final state {final_update_type}, skipping")
                    continue
                if not has_execution:
                    skipped_unexecuted += 1
                    warnings.append(f"Order {order_id}: no executed fill marker, skipping")
                    continue

                selected = candidate_rows[-1]
                selected_row_num = row_numbers[order_id][rows.index(selected)]
                tx_date = _parse_investimental_date(selected.get(COL_UPDATE_TIME, ""))
                side = (selected.get(COL_SIDE) or "").strip().lower()
                symbol = (selected.get(COL_SYMBOL) or "").strip().upper()
                currency = _extract_currency_from_account(selected.get(COL_ACCOUNT_NAME, ""))
                price = _parse_investimental_number(selected.get(COL_PRICE, ""))
                volume = _parse_investimental_number(selected.get(COL_VOLUME, ""))
                value = _parse_investimental_number(selected.get(COL_VALUE, ""))
                fee = _parse_investimental_number(selected.get(COL_FEE, ""))

                if not tx_date or side not in {"buy", "sell"} or not symbol or not currency or volume is None or volume <= 0:
                    skipped_invalid += 1
                    warnings.append(f"Order {order_id}: missing date/side/symbol/currency/volume, skipping")
                    continue
                if value is None or value == 0:
                    if price is not None and price > 0:
                        value = price * volume
                        warnings.append(f"Order {order_id}: zero Value on final fill; estimated cash as Price * Volume")
                    else:
                        skipped_invalid += 1
                        warnings.append(f"Order {order_id}: zero Value and no valid price, skipping")
                        continue

                asset_id = get_asset_id(symbol)
                tx_type = TransactionType.BUY if side == "buy" else TransactionType.SELL
                quantity = abs(volume) if tx_type == TransactionType.BUY else -abs(volume)
                cash_amount = -abs(value) if tx_type == TransactionType.BUY else abs(value)
                exchange = (selected.get(COL_EXCHANGE) or "").strip()
                description = f"Investimental {side} {symbol}"
                if exchange:
                    description = f"{description} on {exchange}"

                self._create_transaction(
                    row_num=selected_row_num,
                    transactions=transactions,
                    validation_issues=validation_issues,
                    context=description,
                    broker_id=broker_id,
                    asset_id=asset_id,
                    type=tx_type,
                    date=tx_date,
                    quantity=quantity,
                    cash=Currency(code=currency, amount=cash_amount),
                    description=description,
                    tags=["import", "investimental"],
                )

                if fee is not None and fee > 0:
                    self._create_transaction(
                        row_num=selected_row_num,
                        transactions=transactions,
                        validation_issues=validation_issues,
                        context=f"Fee: {description}",
                        broker_id=broker_id,
                        asset_id=asset_id,
                        type=TransactionType.FEE,
                        date=tx_date,
                        quantity=Decimal("0"),
                        cash=Currency(code=currency, amount=-abs(fee)),
                        description=f"Investimental fee: {symbol}",
                        tags=["import", "investimental", "fee"],
                    )

        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}") from None
        except BRIMParseError:
            raise
        except Exception as e:
            raise BRIMParseError(f"Error parsing file: {e}") from e

        if skipped_cancelled:
            warnings.append(f"Summary: skipped {skipped_cancelled} cancelled/rejected/expired orders")
        if skipped_unexecuted:
            warnings.append(f"Summary: skipped {skipped_unexecuted} orders without executed fills")
        if skipped_invalid:
            warnings.append(f"Summary: skipped {skipped_invalid} invalid rows/orders")
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
            "Investimental file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets_typed),
        )

        return BRIMParseOutput(transactions=transactions, warnings=warnings, validation_issues=validation_issues, extracted_assets=extracted_assets_typed)
