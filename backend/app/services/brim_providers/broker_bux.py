"""
BUX Broker Report Import Plugin.

Parses comma-delimited CSV exports from BUX.
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

COL_TIME = "Transaction Time (CET)"
COL_CATEGORY = "Transaction Category"
COL_TYPE = "Transaction Type"
COL_AMOUNT = "Transaction Amount"
COL_CURRENCY = "Transaction Currency"
COL_CASH_BALANCE = "Cash Balance Amount"
COL_ASSET_ID = "Asset Id"
COL_ASSET_NAME = "Asset Name"
COL_QUANTITY = "Asset Quantity"
COL_DIVIDEND_CURRENCY = "Dividend Currency"
COL_DIVIDEND_NET = "Dividend Net Amount"
COL_DESCRIPTION = "Transaction Description"


def _parse_bux_datetime(value: str) -> Optional[date_type]:
    value = value.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:26], fmt).date()
        except ValueError:
            continue
    return None


def _parse_bux_number(value: str) -> Optional[Decimal]:
    value = value.strip().replace(",", "")
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _is_currency_code(value: str) -> bool:
    value = value.strip()
    return len(value) == 3 and value.isalpha()


def _map_transaction_type(tx_type: str, category: str) -> Optional[TransactionType]:
    text = f"{tx_type} {category}".lower()
    if "buy trade" in text:
        return TransactionType.BUY
    if "sell trade" in text:
        return TransactionType.SELL
    if "sepa deposit" in text or "deposit" in text:
        return TransactionType.DEPOSIT
    if "withdrawal" in text:
        return TransactionType.WITHDRAWAL
    if "dividend" in text:
        return TransactionType.DIVIDEND
    if "fee" in text:
        return TransactionType.FEE
    return None


def _row_amount_currency(row: Dict[str, str], tx_type: TransactionType):
    if tx_type == TransactionType.DIVIDEND:
        amount = _parse_bux_number(row.get(COL_DIVIDEND_NET, ""))
        currency = (row.get(COL_DIVIDEND_CURRENCY) or "").strip().upper()
        if amount is not None and currency:
            return amount, currency

    amount = _parse_bux_number(row.get(COL_AMOUNT, ""))
    currency = (row.get(COL_CURRENCY) or "").strip().upper()

    if amount is None and not _is_currency_code(currency):
        shifted_amount = _parse_bux_number(currency)
        shifted_currency = (row.get(COL_CASH_BALANCE) or "").strip().upper()
        if shifted_amount is not None and _is_currency_code(shifted_currency):
            return shifted_amount, shifted_currency

    return amount, currency if _is_currency_code(currency) else "EUR"


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
class BUXBrokerProvider(BRIMProvider):
    """BUX CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_bux"

    @property
    def provider_name(self) -> str:
        return "BUX"

    @property
    def description(self) -> str:
        return "Import transactions from BUX CSV export. Supports trades, SEPA deposits/withdrawals, dividends, and fees."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://bux.com/it/wp-content/themes/vo-theme/assets/images/favicon/favicon-32x32.png"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/bux/"

    def can_parse(self, file_path: Path) -> bool:
        """Detect BUX format by checking distinctive CSV headers."""
        if file_path.suffix.lower() != ".csv":
            return False
        try:
            content = self._read_file_head(file_path, num_lines=2)
            first_line = content.split("\n")[0].lower() if content else ""
            required = [
                "transaction time (cet)",
                "transaction category",
                "transaction type",
                "asset id",
                "asset quantity",
                "dividend net amount",
            ]
            return all(col in first_line for col in required)
        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """Parse BUX CSV export file."""
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
                    category = (row.get(COL_CATEGORY) or "").strip()
                    if not tx_type_raw:
                        warnings.append(f"Row {row_num}: empty transaction type, skipping")
                        continue

                    tx_type = _map_transaction_type(tx_type_raw, category)
                    if tx_type is None:
                        warnings.append(f"Row {row_num}: unknown type '{tx_type_raw}', skipping")
                        continue

                    tx_date = _parse_bux_datetime(row.get(COL_TIME) or "")
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date '{row.get(COL_TIME, '')}', skipping")
                        continue

                    amount, currency = _row_amount_currency(row, tx_type)
                    amount = _normalize_cash_sign(tx_type, amount)
                    if amount is None or amount == 0:
                        warnings.append(f"Row {row_num}: missing cash amount for '{tx_type_raw}', skipping")
                        continue

                    quantity = _parse_bux_number(row.get(COL_QUANTITY) or "") or Decimal("0")
                    if tx_type == TransactionType.SELL and quantity > 0:
                        quantity = -quantity
                    if tx_type not in (TransactionType.BUY, TransactionType.SELL):
                        if tx_type == TransactionType.DIVIDEND and quantity != 0:
                            warnings.append(f"Row {row_num}: discarded quantity for {tx_type.value}")
                        quantity = Decimal("0")

                    isin = (row.get(COL_ASSET_ID) or "").strip()
                    name = (row.get(COL_ASSET_NAME) or "").strip()

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

                    description_parts = [tx_type_raw]
                    if name:
                        description_parts.append(name)
                    extra_desc = (row.get(COL_DESCRIPTION) or "").strip()
                    if extra_desc:
                        description_parts.append(extra_desc)
                    description = ": ".join(description_parts)

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
                        tags=["import", "bux"],
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

        logger.info("BUX file parsed", transaction_count=len(transactions), warning_count=len(warnings), asset_count=len(extracted_assets))
        return BRIMParseOutput(transactions=transactions, warnings=warnings, validation_issues=validation_issues, extracted_assets=extracted_assets)

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "bux"
