"""
Parqet Broker Report Import Plugin.

This plugin parses semicolon-delimited CSV exports from Parqet.
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

COL_DATETIME = "datetime"
COL_PRICE = "price"
COL_SHARES = "shares"
COL_AMOUNT = "amount"
COL_TAX = "tax"
COL_FEE = "fee"
COL_TYPE = "type"
COL_BROKER = "broker"
COL_ASSETTYPE = "assettype"
COL_IDENTIFIER = "identifier"
COL_WKN = "wkn"
COL_CURRENCY = "currency"
COL_HOLDINGNAME = "holdingname"

TYPE_MAPPINGS: Dict[str, TransactionType] = {
    "buy": TransactionType.BUY,
    "sell": TransactionType.SELL,
    "dividend": TransactionType.DIVIDEND,
    "transferin": TransactionType.DEPOSIT,
    "deposit": TransactionType.DEPOSIT,
    "transferout": TransactionType.WITHDRAWAL,
    "interest": TransactionType.INTEREST,
}


def _parse_parqet_date(value: str) -> Optional[date_type]:
    """Parse Parqet ISO datetime."""
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _parse_parqet_number(value: str) -> Optional[Decimal]:
    """Parse Parqet comma-decimal number."""
    value = value.strip().replace(".", "").replace(",", ".")
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _normalize_parqet_header(value: Optional[str]) -> str:
    return (value or "").strip().strip('"').strip()


def _normalize_parqet_row(row: Dict[Optional[str], Optional[str]]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for key, value in row.items():
        normalized_key = _normalize_parqet_header(key)
        if normalized_key:
            normalized[normalized_key] = (value or "").strip()
    return normalized


@register_provider(BRIMProviderRegistry)
class ParqetBrokerProvider(BRIMProvider):
    """Parqet CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_parqet"

    @property
    def provider_name(self) -> str:
        return "Parqet"

    @property
    def description(self) -> str:
        return "Import transactions from Parqet CSV export. Parqet is an aggregator; underlying broker names are kept in transaction descriptions."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://parqet.com/favicon.ico"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/parqet/"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "parqet"

    def can_parse(self, file_path: Path) -> bool:
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=1)
            header = content.splitlines()[0].lower() if content else ""
            return all(marker in header for marker in ['"identifier"', '"holdingname"', '"assettype"'])
        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:  # noqa: C901 — flat row loop: validation guards and per-type sign dispatch, no nested logic
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets_raw: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        detected_delim = self.detect_csv_delimiter(file_path)

        try:
            with open(file_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=detected_delim)
                normalized_headers = {_normalize_parqet_header(header) for header in reader.fieldnames or []}
                required_headers = {COL_IDENTIFIER, COL_HOLDINGNAME, COL_ASSETTYPE}
                if not required_headers.issubset(normalized_headers):
                    raise BRIMParseError("Parqet CSV header mismatch")

                row_num = 1
                for raw_row in reader:
                    row_num += 1
                    row = _normalize_parqet_row(raw_row)

                    type_raw = row.get(COL_TYPE, "").strip()
                    tx_type = TYPE_MAPPINGS.get(type_raw.lower())
                    if tx_type is None:
                        warnings.append(f"Row {row_num}: unsupported Parqet type '{type_raw}', skipping")
                        continue

                    tx_date = _parse_parqet_date(row.get(COL_DATETIME, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid datetime '{row.get(COL_DATETIME, '')}', skipping")
                        continue

                    amount = _parse_parqet_number(row.get(COL_AMOUNT, ""))
                    if amount is None:
                        warnings.append(f"Row {row_num}: invalid amount '{row.get(COL_AMOUNT, '')}', skipping")
                        continue

                    shares = _parse_parqet_number(row.get(COL_SHARES, "")) or Decimal("0")
                    price = _parse_parqet_number(row.get(COL_PRICE, ""))
                    tax = _parse_parqet_number(row.get(COL_TAX, "")) or Decimal("0")
                    fee = _parse_parqet_number(row.get(COL_FEE, "")) or Decimal("0")
                    currency = row.get(COL_CURRENCY, "").strip().upper() or "EUR"
                    identifier = row.get(COL_IDENTIFIER, "").strip()
                    wkn = row.get(COL_WKN, "").strip()
                    holding_name = row.get(COL_HOLDINGNAME, "").strip()
                    broker_name = row.get(COL_BROKER, "").strip()

                    asset_id = None
                    asset_required = tx_type in (TransactionType.BUY, TransactionType.SELL, TransactionType.DIVIDEND)
                    asset_optional = tx_type == TransactionType.INTEREST

                    if asset_required and not identifier:
                        warnings.append(f"Row {row_num}: {tx_type.value} requires identifier/ISIN, skipping")
                        continue

                    if asset_required or (asset_optional and identifier):
                        asset_key = identifier
                        if asset_key in asset_to_fake_id:
                            asset_id = asset_to_fake_id[asset_key]
                        else:
                            asset_id = next_fake_id
                            asset_to_fake_id[asset_key] = asset_id
                            extracted_name = f"{holding_name} (WKN {wkn})" if holding_name and wkn else holding_name or None
                            extracted_assets_raw[asset_id] = {
                                "extracted_symbol": None,
                                "extracted_isin": identifier,
                                "extracted_name": extracted_name,
                            }
                            next_fake_id -= 1

                    if tx_type == TransactionType.BUY:
                        quantity = abs(shares)
                        amount = -abs(amount)
                    elif tx_type == TransactionType.SELL:
                        quantity = -abs(shares)
                        amount = abs(amount)
                    elif tx_type in (TransactionType.DIVIDEND, TransactionType.INTEREST, TransactionType.DEPOSIT):
                        quantity = Decimal("0")
                        amount = abs(amount)
                    else:
                        quantity = Decimal("0")
                        amount = -abs(amount)

                    description_parts = [f"Parqet {type_raw}"]
                    if broker_name:
                        description_parts.append(f"underlying broker: {broker_name}")
                    if holding_name:
                        description_parts.append(holding_name)
                    if wkn:
                        description_parts.append(f"WKN {wkn}")
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
                        tags=["import", "parqet"],
                    )

                    if tax != Decimal("0"):
                        self._create_transaction(
                            row_num=row_num,
                            transactions=transactions,
                            validation_issues=validation_issues,
                            context=f"Parqet tax: {description}",
                            broker_id=broker_id,
                            asset_id=asset_id,
                            type=TransactionType.TAX,
                            date=tx_date,
                            quantity=Decimal("0"),
                            cash=Currency(code=currency, amount=-abs(tax)),
                            description=f"Parqet tax: {description}",
                            tags=["import", "parqet", "tax"],
                        )

                    if fee != Decimal("0"):
                        self._create_transaction(
                            row_num=row_num,
                            transactions=transactions,
                            validation_issues=validation_issues,
                            context=f"Parqet fee: {description}",
                            broker_id=broker_id,
                            asset_id=asset_id,
                            type=TransactionType.FEE,
                            date=tx_date,
                            quantity=Decimal("0"),
                            cash=Currency(code=currency, amount=-abs(fee)),
                            description=f"Parqet fee: {description}",
                            tags=["import", "parqet", "fee"],
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
            "Parqet file parsed",
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
