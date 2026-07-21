"""
XTB Broker Report Import Plugin.

This plugin parses semicolon-delimited CSV exports from XTB.
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

XTB_HEADER = "ID;Type;Time;Symbol;Comment;Amount"

COL_ID = "ID"
COL_TYPE = "Type"
COL_TIME = "Time"
COL_SYMBOL = "Symbol"
COL_COMMENT = "Comment"
COL_AMOUNT = "Amount"

TYPE_MAPPINGS: Dict[str, TransactionType] = {
    "stocks/etf purchase": TransactionType.BUY,
    "ações/etf compra": TransactionType.BUY,
    "stocks/etf sale": TransactionType.SELL,
    "ações/etf vende": TransactionType.SELL,
    "deposit": TransactionType.DEPOSIT,
    "withdrawal": TransactionType.WITHDRAWAL,
    "dividend": TransactionType.DIVIDEND,
    "withholding tax": TransactionType.TAX,
    "commission": TransactionType.FEE,
    "fee": TransactionType.FEE,
    "free funds interests tax": TransactionType.TAX,
    "free-funds interest tax": TransactionType.TAX,
    "free funds interests": TransactionType.INTEREST,
    "free-funds interest": TransactionType.INTEREST,
    "interest": TransactionType.INTEREST,
}

KNOWN_CURRENCIES = {
    "AUD",
    "CAD",
    "CHF",
    "EUR",
    "GBP",
    "JPY",
    "NOK",
    "PLN",
    "SEK",
    "USD",
}


def _parse_xtb_date(value: str) -> Optional[date_type]:
    """Parse XTB datetime format (DD.MM.YYYY HH:MM:SS)."""
    value = value.strip()
    if not value:
        return None

    date_part, _, time_part = value.partition(" ")
    parts = date_part.split(".")
    if len(parts) == 3 and len(parts[0]) == 3 and parts[0].startswith("0"):
        value = ".".join([parts[0][1:], parts[1], parts[2]]) + (f" {time_part}" if time_part else "")

    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_xtb_number(value: str) -> Optional[Decimal]:
    """Parse XTB decimal number."""
    value = value.strip().replace(",", ".")
    if not value or value in {"-", "-."}:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _map_xtb_type(value: str) -> Optional[TransactionType]:
    value_lower = value.strip().lower()
    if value_lower in TYPE_MAPPINGS:
        return TYPE_MAPPINGS[value_lower]
    for key, tx_type in TYPE_MAPPINGS.items():
        if key in value_lower:
            return tx_type
    return None


def _is_decimal_token(value: str) -> bool:
    return _parse_xtb_number(value) is not None


def _parse_xtb_comment_quantity_price(comment: str) -> tuple[Decimal, Optional[Decimal]]:
    """Extract quantity and price from comments like ``OPEN BUY 34/42.5658 @ 11.7480``."""
    tokens = comment.replace("/", " / ").replace("@", " @ ").split()
    quantity = Decimal("0")
    price: Optional[Decimal] = None

    for index, token in enumerate(tokens):
        if token == "@" and index + 1 < len(tokens):
            price = _parse_xtb_number(tokens[index + 1])
            break

    action_index = next((i for i, token in enumerate(tokens) if token.upper() in {"BUY", "SELL"}), None)
    search_tokens = tokens[action_index + 1 :] if action_index is not None else tokens
    for token in search_tokens:
        if _is_decimal_token(token):
            quantity = _parse_xtb_number(token) or Decimal("0")
            break

    return quantity, price


def _infer_xtb_currency(comment: str) -> Optional[str]:
    comment_tokens = comment.replace("/", " ").replace("@", " ").replace(",", " ").split()
    for token in comment_tokens:
        cleaned = token.strip("()[]{}.,;:")
        if cleaned in KNOWN_CURRENCIES:
            return cleaned

    return None


@register_provider(BRIMProviderRegistry)
class XTBBrokerProvider(BRIMProvider):
    """XTB CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_xtb"

    @property
    def provider_name(self) -> str:
        return "XTB"

    @property
    def description(self) -> str:
        return "Import transactions from XTB CSV export. Supports stocks, ETFs, dividends, cash movements, taxes, fees, and interest."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://www.xtb.com/favicon.ico"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/xtb/"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "xtb"

    def can_parse(self, file_path: Path) -> bool:
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=1)
            first_line = content.splitlines()[0].strip() if content else ""
            return first_line == XTB_HEADER
        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets_raw: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE
        warned_default_currency = False

        detected_delim = self.detect_csv_delimiter(file_path)

        try:
            with open(file_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=detected_delim)
                if reader.fieldnames != XTB_HEADER.split(";"):
                    raise BRIMParseError("XTB CSV header mismatch")

                row_num = 1
                for row in reader:
                    row_num += 1

                    type_raw = row.get(COL_TYPE, "").strip()
                    if not type_raw:
                        continue

                    tx_type = _map_xtb_type(type_raw)
                    if tx_type is None:
                        warnings.append(f"Row {row_num}: unknown XTB type '{type_raw}', skipping")
                        continue

                    tx_date = _parse_xtb_date(row.get(COL_TIME, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date '{row.get(COL_TIME, '')}', skipping")
                        continue

                    amount = _parse_xtb_number(row.get(COL_AMOUNT, ""))
                    if amount is None:
                        warnings.append(f"Row {row_num}: invalid amount '{row.get(COL_AMOUNT, '')}', skipping")
                        continue

                    symbol = row.get(COL_SYMBOL, "").strip()
                    comment = row.get(COL_COMMENT, "").strip()
                    quantity, price = _parse_xtb_comment_quantity_price(comment)

                    if tx_type == TransactionType.BUY:
                        quantity = abs(quantity)
                        amount = -abs(amount)
                    elif tx_type == TransactionType.SELL:
                        quantity = -abs(quantity)
                        amount = abs(amount)
                    elif tx_type in (TransactionType.DIVIDEND, TransactionType.INTEREST, TransactionType.DEPOSIT):
                        quantity = Decimal("0")
                        amount = abs(amount)
                    elif tx_type in (TransactionType.WITHDRAWAL, TransactionType.FEE, TransactionType.TAX):
                        quantity = Decimal("0")
                        amount = -abs(amount)

                    asset_id = None
                    asset_required = tx_type in (TransactionType.BUY, TransactionType.SELL, TransactionType.DIVIDEND)
                    asset_optional = tx_type in (TransactionType.INTEREST, TransactionType.FEE, TransactionType.TAX)

                    if asset_required and not symbol:
                        warnings.append(f"Row {row_num}: {tx_type.value} requires symbol, skipping")
                        continue

                    if asset_required or (asset_optional and symbol):
                        asset_key = symbol
                        if asset_key in asset_to_fake_id:
                            asset_id = asset_to_fake_id[asset_key]
                        else:
                            asset_id = next_fake_id
                            asset_to_fake_id[asset_key] = asset_id
                            extracted_assets_raw[asset_id] = {
                                "extracted_symbol": symbol,
                                "extracted_isin": None,
                                "extracted_name": symbol,
                            }
                            next_fake_id -= 1

                    currency = _infer_xtb_currency(comment)
                    if currency is None:
                        currency = "EUR"
                        if not warned_default_currency:
                            warnings.append("Currency not explicit in some XTB rows; defaulted ambiguous cash rows to EUR.")
                            warned_default_currency = True

                    description_parts = [type_raw]
                    if symbol:
                        description_parts.append(symbol)
                    if comment:
                        description_parts.append(comment)
                    if price is not None:
                        description_parts.append(f"price={price}")
                    description = " | ".join(description_parts)

                    self._create_transaction(
                        row_num=row_num,
                        transactions=transactions,
                        validation_issues=validation_issues,
                        context=description,
                        broker_id=broker_id,
                        asset_id=asset_id,
                        type=tx_type,
                        date=tx_date,
                        quantity=quantity,
                        cash=Currency(code=currency, amount=amount),
                        description=description,
                        tags=["import", "xtb"],
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
            "XTB file parsed",
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
