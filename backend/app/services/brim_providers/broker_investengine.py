"""
InvestEngine Broker Report Import Plugin.

Parses CSV exports from InvestEngine (UK broker).
"""

from __future__ import annotations

import csv
import re
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

COL_SECURITY = "Security / ISIN"
COL_TYPE = "Transaction Type"
COL_QUANTITY = "Quantity"
COL_SHARE_PRICE = "Share Price"
COL_TOTAL_VALUE = "Total Trade Value"
COL_TRADE_DATE = "Trade Date/Time"
COL_SETTLEMENT_DATE = "Settlement Date"
COL_BROKER = "Broker"

EXPECTED_HEADER = [
    COL_SECURITY,
    COL_TYPE,
    COL_QUANTITY,
    COL_SHARE_PRICE,
    COL_TOTAL_VALUE,
    COL_TRADE_DATE,
    COL_SETTLEMENT_DATE,
    COL_BROKER,
]

TYPE_MAPPINGS: Dict[str, TransactionType] = {
    "buy": TransactionType.BUY,
    "sell": TransactionType.SELL,
    "dividend": TransactionType.DIVIDEND,
}


def _parse_investengine_date(value: str) -> Optional[date_type]:
    """Parse InvestEngine date/time (DD/MM/YY HH:MM:SS)."""
    value = value.strip()
    if not value:
        return None
    for fmt in ("%d/%m/%y %H:%M:%S", "%d/%m/%y", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_investengine_number(value: str) -> Optional[Decimal]:
    """Parse InvestEngine GBP amount/quantity."""
    value = re.sub(r"[£€$]", "", value.strip()).replace(",", "")
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _parse_security(value: str) -> tuple[str, str]:
    """Split 'Name / ISIN IE...' into (name, isin)."""
    parts = value.strip().split(" / ISIN ", 1)
    if len(parts) != 2:
        return value.strip(), ""
    return parts[0].strip(), parts[1].strip()


@register_provider(BRIMProviderRegistry)
class InvestEngineBrokerProvider(BRIMProvider):
    """InvestEngine CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_investengine"

    @property
    def provider_name(self) -> str:
        return "InvestEngine"

    @property
    def description(self) -> str:
        return "Import transactions from InvestEngine CSV export. Supports buys, sells, and dividends in GBP."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> str:
        return "https://www.investengine.com/favicon.ico"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/investengine/"

    def can_parse(self, file_path: Path) -> bool:
        """Detect InvestEngine export via exact header."""
        if file_path.suffix.lower() != ".csv":
            return False
        try:
            with open(file_path, encoding="utf-8-sig", newline="") as f:
                header = next(csv.reader(f, delimiter=","), [])
            return header == EXPECTED_HEADER
        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:  # noqa: C901 — flat row loop: validation guards and per-type sign rules, no nested logic
        """Parse InvestEngine CSV export file."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        try:
            with open(file_path, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f, delimiter=",")
                row_num = 1

                if reader.fieldnames != EXPECTED_HEADER:
                    raise BRIMParseError("Unexpected InvestEngine CSV header")

                for row in reader:
                    row_num += 1
                    tx_type_raw = row.get(COL_TYPE, "").strip()
                    tx_type = TYPE_MAPPINGS.get(tx_type_raw.lower())
                    if not tx_type:
                        warnings.append(f"Row {row_num}: unknown type '{tx_type_raw}', skipping")
                        continue

                    tx_date = _parse_investengine_date(row.get(COL_TRADE_DATE, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date, skipping")
                        continue

                    name, isin = _parse_security(row.get(COL_SECURITY, ""))
                    if not isin:
                        warnings.append(f"Row {row_num}: missing ISIN, skipping")
                        continue

                    asset_key = isin
                    if asset_key in asset_to_fake_id:
                        asset_id = asset_to_fake_id[asset_key]
                    else:
                        asset_id = next_fake_id
                        asset_to_fake_id[asset_key] = asset_id
                        extracted_assets[asset_id] = {
                            "extracted_symbol": None,
                            "extracted_isin": isin,
                            "extracted_name": name if name else None,
                        }
                        next_fake_id -= 1

                    amount = _parse_investengine_number(row.get(COL_TOTAL_VALUE, ""))
                    if amount is None:
                        warnings.append(f"Row {row_num}: invalid amount, skipping")
                        continue

                    quantity = _parse_investengine_number(row.get(COL_QUANTITY, ""))
                    if quantity is None:
                        quantity = Decimal("0")

                    if tx_type == TransactionType.BUY and amount > 0:
                        amount = -amount
                    if tx_type == TransactionType.SELL and quantity > 0:
                        quantity = -quantity
                    if tx_type == TransactionType.DIVIDEND:
                        quantity = Decimal("0")
                        if amount < 0:
                            amount = -amount

                    description = f"{tx_type_raw}: {name}" if name else tx_type_raw
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
                        cash=Currency(code="GBP", amount=amount),
                        description=description,
                        tags=["import", "investengine"],
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
            for fake_id, info in extracted_assets.items()
        }

        logger.info(
            "InvestEngine file parsed",
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
    def test_file_pattern(self) -> Optional[str]:
        return "investengine"
