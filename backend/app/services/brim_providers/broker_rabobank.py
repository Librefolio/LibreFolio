"""
Rabobank Broker Report Import Plugin.

Parses semicolon-separated Dutch CSV exports from Rabobank.
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

COL_PORTFOLIO = "Portefeuille"
COL_NAME = "Naam"
COL_DATE = "Datum"
COL_TYPE = "Type mutatie"
COL_MUTATION_CURRENCY = "Valuta mutatie"
COL_VOLUME = "Volume"
COL_PRICE = "Koers"
COL_PRICE_CURRENCY = "Valuta koers"
COL_COSTS = "Valuta kosten €"
COL_VALUE = "Waarde"
COL_AMOUNT = "Bedrag"
COL_ISIN = "Isin code"
COL_TIME = "Tijd"
COL_EXCHANGE = "Beurs"

EXPECTED_HEADER = [
    COL_PORTFOLIO,
    COL_NAME,
    COL_DATE,
    COL_TYPE,
    COL_MUTATION_CURRENCY,
    COL_VOLUME,
    COL_PRICE,
    COL_PRICE_CURRENCY,
    COL_COSTS,
    COL_VALUE,
    COL_AMOUNT,
    COL_ISIN,
    COL_TIME,
    COL_EXCHANGE,
]


def _parse_rabobank_date(value: str) -> Optional[date_type]:
    """Parse Rabobank date (DD-MM-YYYY)."""
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d-%m-%Y").date()
    except ValueError:
        return None


def _parse_rabobank_number(value: str) -> Optional[Decimal]:
    """Parse Rabobank Dutch decimal format."""
    value = re.sub(r"[€\s]", "", value.strip())
    if not value:
        return None
    value = value.replace(".", "").replace(",", ".")
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _map_rabobank_type(value: str, amount: Decimal) -> Optional[TransactionType]:
    """Map Rabobank Dutch transaction type."""
    value_lower = value.lower().strip()
    if "verkoop fondsen" in value_lower or value_lower == "verkoop":
        return TransactionType.SELL
    if "koop fondsen" in value_lower or value_lower == "koop":
        return TransactionType.BUY
    if "dividend" in value_lower:
        return TransactionType.DIVIDEND
    if "storting" in value_lower and "opname" in value_lower:
        return TransactionType.DEPOSIT if amount >= Decimal("0") else TransactionType.WITHDRAWAL
    if "storting" in value_lower:
        return TransactionType.DEPOSIT
    if "opname" in value_lower:
        return TransactionType.WITHDRAWAL
    if "kosten" in value_lower or "tarieven" in value_lower or "services" in value_lower:
        return TransactionType.FEE
    if "rente" in value_lower:
        return TransactionType.INTEREST
    return None


@register_provider(BRIMProviderRegistry)
class RabobankBrokerProvider(BRIMProvider):
    """Rabobank CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_rabobank"

    @property
    def provider_name(self) -> str:
        return "Rabobank"

    @property
    def description(self) -> str:
        return "Import transactions from Rabobank Dutch CSV export. Supports funds, dividends, deposits, withdrawals, fees, and interest."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://www.rabobank.com/static/msp/global-sites/rds/favicons/favicon-svg.svg"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/rabobank/"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Rabobank export via exact semicolon header."""
        if file_path.suffix.lower() != ".csv":
            return False
        try:
            with open(file_path, encoding="utf-8-sig", newline="") as f:
                header = next(csv.reader(f, delimiter=";"), [])
            return header == EXPECTED_HEADER
        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """Parse Rabobank CSV export file."""
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
                    raise BRIMParseError("Unexpected Rabobank CSV header")

                for row in reader:
                    row_num += 1

                    amount = _parse_rabobank_number(row.get(COL_AMOUNT, ""))
                    if amount is None:
                        warnings.append(f"Row {row_num}: invalid amount, skipping")
                        continue

                    tx_type_raw = row.get(COL_TYPE, "").strip()
                    tx_type = _map_rabobank_type(tx_type_raw, amount)
                    if not tx_type:
                        warnings.append(f"Row {row_num}: unknown type '{tx_type_raw}', skipping")
                        continue

                    tx_date = _parse_rabobank_date(row.get(COL_DATE, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date, skipping")
                        continue

                    name = row.get(COL_NAME, "").strip()
                    isin = row.get(COL_ISIN, "").strip()
                    quantity = _parse_rabobank_number(row.get(COL_VOLUME, "")) or Decimal("0")
                    currency = row.get(COL_MUTATION_CURRENCY, "EUR").strip().upper() or "EUR"

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
                                "extracted_name": name if name else None,
                            }
                            next_fake_id -= 1

                    if tx_type == TransactionType.BUY and amount > 0:
                        amount = -amount
                    if tx_type == TransactionType.SELL:
                        if quantity > 0:
                            quantity = -quantity
                        if amount < 0:
                            amount = -amount
                    if tx_type == TransactionType.DIVIDEND:
                        quantity = Decimal("0")
                        if amount < 0:
                            amount = -amount
                    if tx_type in (TransactionType.DEPOSIT, TransactionType.WITHDRAWAL, TransactionType.FEE, TransactionType.INTEREST):
                        quantity = Decimal("0")
                    if tx_type == TransactionType.WITHDRAWAL and amount > 0:
                        amount = -amount
                    if tx_type == TransactionType.FEE and amount > 0:
                        amount = -amount
                    if tx_type == TransactionType.INTEREST and amount < 0:
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
                        cash=Currency(code=currency, amount=amount),
                        description=description,
                        tags=["import", "rabobank"],
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
            "Rabobank file parsed",
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
        return "rabobank"
