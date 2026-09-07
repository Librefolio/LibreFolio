"""
Disnat Broker Report Import Plugin.

Parses comma-delimited CSV exports from Disnat (Desjardins, Canada).
"""

from __future__ import annotations

import csv
import unicodedata
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

COL_TRADE_DATE = "Date de transaction"
COL_SETTLEMENT_DATE = "Date de règlement"
COL_TYPE = "Type de transaction"
COL_SYMBOL = "Symbole"
COL_DESCRIPTION = "Description"
COL_QUANTITY = "Quantité"
COL_AMOUNT = "Montant de l'opération"
COL_CURRENCY = "Devise du compte"

CURRENCY_ALIASES = {"CAN": "CAD"}


def _clean_cell(value: Optional[str]) -> str:
    value = (value or "").strip()
    return "" if value == "-" else value


def _normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.strip().lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def _parse_disnat_date(value: str) -> Optional[date_type]:
    value = _clean_cell(value)
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_disnat_number(value: str) -> Optional[Decimal]:
    value = _clean_cell(value).replace(" ", "")
    if not value:
        return None
    try:
        return Decimal(value.replace(",", "."))
    except InvalidOperation:
        return None


def _map_transaction_type(value: str) -> Optional[TransactionType]:
    normalized = _normalize_text(value)
    if normalized.startswith("achat"):
        return TransactionType.BUY
    if normalized.startswith("vente"):
        return TransactionType.SELL
    if normalized.startswith("dividende"):
        return TransactionType.DIVIDEND
    if normalized.startswith("taxe") or normalized.startswith("retenue"):
        return TransactionType.TAX
    if normalized.startswith("depot"):
        return TransactionType.DEPOSIT
    if normalized.startswith("retrait"):
        return TransactionType.WITHDRAWAL
    if normalized.startswith("frais") or normalized.startswith("commission"):
        return TransactionType.FEE
    if normalized.startswith("interet"):
        return TransactionType.INTEREST
    return None


def _normalize_cash_sign(tx_type: TransactionType, amount: Optional[Decimal]) -> Optional[Decimal]:
    if amount is None or amount == 0:
        return amount
    if tx_type in (TransactionType.BUY, TransactionType.WITHDRAWAL, TransactionType.FEE, TransactionType.TAX):
        return -abs(amount)
    if tx_type in (TransactionType.SELL, TransactionType.DIVIDEND, TransactionType.INTEREST, TransactionType.DEPOSIT):
        return abs(amount)
    return amount


def _normalize_currency(value: str) -> str:
    code = _clean_cell(value).upper() or "CAD"
    return CURRENCY_ALIASES.get(code, code)


def _requires_asset(tx_type: TransactionType) -> bool:
    return tx_type in (TransactionType.BUY, TransactionType.SELL, TransactionType.DIVIDEND)


def _may_link_asset(tx_type: TransactionType) -> bool:
    return tx_type in (TransactionType.INTEREST, TransactionType.FEE, TransactionType.TAX)


@register_provider(BRIMProviderRegistry)
class DisnatBrokerProvider(BRIMProvider):
    """Disnat CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_disnat"

    @property
    def provider_name(self) -> str:
        return "Disnat"

    @property
    def description(self) -> str:
        return "Import transactions from Disnat CSV export. Supports trades, dividends, taxes, cash movements, fees, and interest."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://disnat.com/favicon.ico"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/disnat/"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Disnat format by checking distinctive French/Canadian CSV headers."""
        if file_path.suffix.lower() != ".csv":
            return False
        try:
            content = self._read_file_head(file_path, num_lines=2)
            first_line = content.split("\n")[0].lower() if content else ""
            required = [
                "date de transaction",
                "date de règlement",
                "type de transaction",
                "classe d'actif",
                "montant de l'opération",
                "devise du compte",
            ]
            return all(col in first_line for col in required)
        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:  # noqa: C901 — flat row loop: validation guards and per-type field mapping, no nested logic
        """Parse Disnat CSV export file."""
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

                    tx_type_raw = _clean_cell(row.get(COL_TYPE))
                    if not tx_type_raw:
                        warnings.append(f"Row {row_num}: empty transaction type, skipping")
                        continue

                    tx_type = _map_transaction_type(tx_type_raw)
                    if tx_type is None:
                        warnings.append(f"Row {row_num}: unknown type '{tx_type_raw}', skipping")
                        continue

                    tx_date = _parse_disnat_date(row.get(COL_TRADE_DATE) or "") or _parse_disnat_date(row.get(COL_SETTLEMENT_DATE) or "")
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date, skipping")
                        continue

                    amount = _normalize_cash_sign(tx_type, _parse_disnat_number(row.get(COL_AMOUNT) or ""))
                    if amount is None or amount == 0:
                        warnings.append(f"Row {row_num}: missing cash amount for '{tx_type_raw}', skipping")
                        continue

                    quantity = _parse_disnat_number(row.get(COL_QUANTITY) or "") or Decimal("0")
                    if tx_type == TransactionType.SELL and quantity > 0:
                        quantity = -quantity
                    if tx_type not in (TransactionType.BUY, TransactionType.SELL):
                        if tx_type in (TransactionType.DIVIDEND, TransactionType.INTEREST) and quantity != 0:
                            warnings.append(f"Row {row_num}: discarded quantity for {tx_type.value}")
                        quantity = Decimal("0")

                    currency = _normalize_currency(row.get(COL_CURRENCY) or "")
                    symbol = _clean_cell(row.get(COL_SYMBOL))
                    description_text = _clean_cell(row.get(COL_DESCRIPTION))

                    asset_id = None
                    if _requires_asset(tx_type) or (_may_link_asset(tx_type) and symbol):
                        if not symbol:
                            warnings.append(f"Row {row_num}: {tx_type.value} requires asset symbol, skipping")
                            continue
                        if symbol in asset_to_fake_id:
                            asset_id = asset_to_fake_id[symbol]
                        else:
                            asset_id = next_fake_id
                            asset_to_fake_id[symbol] = asset_id
                            extracted_assets_raw[asset_id] = {
                                "extracted_symbol": symbol,
                                "extracted_isin": None,
                                "extracted_name": description_text if description_text else None,
                            }
                            next_fake_id -= 1

                    description = f"{tx_type_raw}: {description_text}" if description_text else tx_type_raw
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
                        tags=["import", "disnat"],
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

        logger.info("Disnat file parsed", transaction_count=len(transactions), warning_count=len(warnings), asset_count=len(extracted_assets))
        return BRIMParseOutput(transactions=transactions, warnings=warnings, validation_issues=validation_issues, extracted_assets=extracted_assets)

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "disnat"
