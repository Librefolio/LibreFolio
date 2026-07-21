"""
Trade Republic Broker Report Import Plugin.

Parses semicolon-separated Dutch CSV exports from Trade Republic.
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

COL_DATE = "Datum"
COL_TYPE = "Transactietype"
COL_AMOUNT = "Waarde (netto)"
COL_NOTE = "Opmerking"
COL_ISIN = "ISIN"
COL_QUANTITY = "Aantal"
COL_FEE = "Kosten"
COL_TAX = "Belasting"

EXPECTED_HEADER = [
    COL_DATE,
    COL_TYPE,
    COL_AMOUNT,
    COL_NOTE,
    COL_ISIN,
    COL_QUANTITY,
    COL_FEE,
    COL_TAX,
]

TYPE_MAPPINGS: Dict[str, TransactionType] = {
    "aankoop": TransactionType.BUY,
    "buy": TransactionType.BUY,
    "verkoop": TransactionType.SELL,
    "sell": TransactionType.SELL,
    "storting": TransactionType.DEPOSIT,
    "onttrekking": TransactionType.WITHDRAWAL,
    "dividend": TransactionType.DIVIDEND,
    "rente": TransactionType.INTEREST,
    "kosten": TransactionType.FEE,
    "belasting": TransactionType.TAX,
}


def _parse_traderepublic_date(value: str) -> Optional[date_type]:
    """Parse Trade Republic ISO date/datetime."""
    value = value.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value[:19], fmt).date()
        except ValueError:
            continue
    return None


def _parse_traderepublic_number(value: str) -> Optional[Decimal]:
    """Parse Trade Republic decimal, accepting comma or dot decimals."""
    value = re.sub(r"[€\s]", "", value.strip())
    if not value:
        return None
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


@register_provider(BRIMProviderRegistry)
class TradeRepublicBrokerProvider(BRIMProvider):
    """Trade Republic CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_traderepublic"

    @property
    def provider_name(self) -> str:
        return "Trade Republic"

    @property
    def description(self) -> str:
        return "Import transactions from Trade Republic CSV export. Supports trades, dividends, interest, cash movements, fees, and taxes in EUR."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> str:
        return "https://traderepublic.com/favicon.ico"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/traderepublic/"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Trade Republic export via exact semicolon header."""
        if file_path.suffix.lower() != ".csv":
            return False
        try:
            with open(file_path, encoding="utf-8-sig", newline="") as f:
                header = next(csv.reader(f, delimiter=";"), [])
            return header == EXPECTED_HEADER
        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """Parse Trade Republic CSV export file."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        try:
            with open(file_path, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f, delimiter=";")
                row_num = 1

                if reader.fieldnames != EXPECTED_HEADER:
                    raise BRIMParseError("Unexpected Trade Republic CSV header")

                for row in reader:
                    row_num += 1
                    tx_type_raw = row.get(COL_TYPE, "").strip()
                    tx_type = TYPE_MAPPINGS.get(tx_type_raw.lower())
                    if not tx_type:
                        warnings.append(f"Row {row_num}: unknown type '{tx_type_raw}', skipping")
                        continue

                    tx_date = _parse_traderepublic_date(row.get(COL_DATE, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date, skipping")
                        continue

                    amount = _parse_traderepublic_number(row.get(COL_AMOUNT, ""))
                    if amount is None:
                        warnings.append(f"Row {row_num}: invalid amount, skipping")
                        continue

                    note = row.get(COL_NOTE, "").strip()
                    isin = row.get(COL_ISIN, "").strip()
                    quantity = _parse_traderepublic_number(row.get(COL_QUANTITY, "")) or Decimal("0")

                    asset_id = None
                    if tx_type in (TransactionType.BUY, TransactionType.SELL, TransactionType.DIVIDEND):
                        if not isin:
                            warnings.append(f"Row {row_num}: {tx_type.value} requires ISIN, skipping")
                            continue
                        if isin in asset_to_fake_id:
                            asset_id = asset_to_fake_id[isin]
                        else:
                            asset_id = next_fake_id
                            asset_to_fake_id[isin] = asset_id
                            extracted_assets[asset_id] = {
                                "extracted_symbol": None,
                                "extracted_isin": isin,
                                "extracted_name": note if note else None,
                            }
                            next_fake_id -= 1

                    if tx_type == TransactionType.BUY and amount > 0:
                        amount = -amount
                    if tx_type == TransactionType.SELL:
                        if quantity > 0:
                            quantity = -quantity
                        if amount < 0:
                            amount = -amount
                    if tx_type in (TransactionType.DIVIDEND, TransactionType.INTEREST, TransactionType.DEPOSIT, TransactionType.WITHDRAWAL, TransactionType.FEE, TransactionType.TAX):
                        quantity = Decimal("0")
                    if tx_type in (TransactionType.DIVIDEND, TransactionType.INTEREST, TransactionType.DEPOSIT) and amount < 0:
                        amount = -amount
                    if tx_type in (TransactionType.WITHDRAWAL, TransactionType.FEE, TransactionType.TAX) and amount > 0:
                        amount = -amount

                    fee = _parse_traderepublic_number(row.get(COL_FEE, "")) or Decimal("0")
                    tax = _parse_traderepublic_number(row.get(COL_TAX, "")) or Decimal("0")
                    if fee != Decimal("0") or tax != Decimal("0"):
                        warnings.append(f"Row {row_num}: Kosten/Belasting columns present; additional fee/tax transactions skipped")

                    description = f"{tx_type_raw}: {note}" if note else tx_type_raw
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
                        cash=Currency(code="EUR", amount=amount),
                        description=description,
                        tags=["import", "traderepublic"],
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
            "Trade Republic file parsed",
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
        return "traderepublic"
