"""
Avanza Broker Report Import Plugin.

Parses semicolon-delimited CSV exports from Avanza (Sweden).
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

COL_DATE = "Datum"
COL_TYPE = "Typ av transaktion"
COL_NAME = "Värdepapper/beskrivning"
COL_QUANTITY = "Antal"
COL_AMOUNT = "Belopp"
COL_CURRENCY = "Transaktionsvaluta"
COL_ISIN = "ISIN"

TYPE_MAPPINGS: Dict[str, TransactionType] = {
    "köp": TransactionType.BUY,
    "sälj": TransactionType.SELL,
    "insättning": TransactionType.DEPOSIT,
    "uttag": TransactionType.WITHDRAWAL,
    "utdelning": TransactionType.DIVIDEND,
    "ränta": TransactionType.INTEREST,
    "källskatt": TransactionType.TAX,
    "skatt": TransactionType.TAX,
    "courtage": TransactionType.FEE,
    "avgift": TransactionType.FEE,
}


def _parse_avanza_date(value: str) -> Optional[date_type]:
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_avanza_number(value: str) -> Optional[Decimal]:
    value = value.strip().replace(" ", "")
    if not value:
        return None
    try:
        return Decimal(value.replace(",", "."))
    except InvalidOperation:
        return None


def _map_transaction_type(value: str) -> Optional[TransactionType]:
    value_lower = value.strip().lower()
    for pattern, tx_type in TYPE_MAPPINGS.items():
        if pattern in value_lower:
            return tx_type
    return None


def _normalize_cash_sign(tx_type: TransactionType, amount: Optional[Decimal]) -> Optional[Decimal]:
    if amount is None or amount == 0:
        return amount
    if tx_type in (TransactionType.BUY, TransactionType.WITHDRAWAL, TransactionType.FEE, TransactionType.TAX):
        return -abs(amount)
    if tx_type in (TransactionType.SELL, TransactionType.DIVIDEND, TransactionType.INTEREST, TransactionType.DEPOSIT):
        return abs(amount)
    return amount


def _requires_asset(tx_type: TransactionType) -> bool:
    return tx_type in (TransactionType.BUY, TransactionType.SELL, TransactionType.DIVIDEND)


def _may_link_asset(tx_type: TransactionType) -> bool:
    return tx_type in (TransactionType.INTEREST, TransactionType.FEE, TransactionType.TAX)


@register_provider(BRIMProviderRegistry)
class AvanzaBrokerProvider(BRIMProvider):
    """Avanza CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_avanza"

    @property
    def provider_name(self) -> str:
        return "Avanza"

    @property
    def description(self) -> str:
        return "Import transactions from Avanza CSV export. Supports trades, cash movements, dividends, interest, taxes, and fees."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://avanza.se/favicon.ico"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/avanza/"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Avanza format by checking distinctive Swedish CSV headers."""
        if file_path.suffix.lower() != ".csv":
            return False
        try:
            content = self._read_file_head(file_path, num_lines=2)
            first_line = content.split("\n")[0].lower() if content else ""
            required = [
                "datum",
                "typ av transaktion",
                "värdepapper/beskrivning",
                "transaktionsvaluta",
                "courtage (sek)",
                "isin",
            ]
            return all(col in first_line for col in required)
        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """Parse Avanza CSV export file."""
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
                row_num = 1
                for row in reader:
                    row_num += 1

                    tx_type_raw = (row.get(COL_TYPE) or "").strip()
                    if not tx_type_raw:
                        warnings.append(f"Row {row_num}: empty transaction type, skipping")
                        continue

                    tx_type = _map_transaction_type(tx_type_raw)
                    if tx_type is None:
                        warnings.append(f"Row {row_num}: unknown type '{tx_type_raw}', skipping")
                        continue

                    tx_date = _parse_avanza_date(row.get(COL_DATE) or "")
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date '{row.get(COL_DATE, '')}', skipping")
                        continue

                    amount = _normalize_cash_sign(tx_type, _parse_avanza_number(row.get(COL_AMOUNT) or ""))
                    if amount is None or amount == 0:
                        warnings.append(f"Row {row_num}: missing cash amount for '{tx_type_raw}', skipping")
                        continue

                    quantity = _parse_avanza_number(row.get(COL_QUANTITY) or "") or Decimal("0")
                    if tx_type == TransactionType.SELL and quantity > 0:
                        quantity = -quantity
                    if tx_type not in (TransactionType.BUY, TransactionType.SELL):
                        if tx_type in (TransactionType.DIVIDEND, TransactionType.INTEREST) and quantity != 0:
                            warnings.append(f"Row {row_num}: discarded quantity for {tx_type.value}")
                        quantity = Decimal("0")

                    currency = (row.get(COL_CURRENCY) or "SEK").strip().upper() or "SEK"
                    isin = (row.get(COL_ISIN) or "").strip()
                    name = (row.get(COL_NAME) or "").strip()

                    asset_id = None
                    if _requires_asset(tx_type) or (_may_link_asset(tx_type) and isin):
                        if not isin:
                            warnings.append(f"Row {row_num}: {tx_type.value} requires asset identifier, skipping")
                            continue
                        if isin in asset_to_fake_id:
                            asset_id = asset_to_fake_id[isin]
                        else:
                            asset_id = next_fake_id
                            asset_to_fake_id[isin] = asset_id
                            extracted_assets_raw[asset_id] = {
                                "extracted_symbol": None,
                                "extracted_isin": isin,
                                "extracted_name": name if name else None,
                            }
                            next_fake_id -= 1

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
                        tags=["import", "avanza"],
                    )
        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}") from None
        except Exception as e:
            raise BRIMParseError(f"Error parsing file: {e}") from e

        if not transactions:
            warnings.append("No valid transactions found in file")

        extracted_assets = {
            fake_id: BRIMExtractedAssetInfo(
                extracted_symbol=info.get("extracted_symbol"),
                extracted_isin=info.get("extracted_isin"),
                extracted_name=info.get("extracted_name"),
            )
            for fake_id, info in extracted_assets_raw.items()
        }

        logger.info("Avanza file parsed", transaction_count=len(transactions), warning_count=len(warnings), asset_count=len(extracted_assets))
        return BRIMParseOutput(transactions=transactions, warnings=warnings, validation_issues=validation_issues, extracted_assets=extracted_assets)

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "avanza"
