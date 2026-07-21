"""
Bitvavo Broker Report Import Plugin.

This plugin parses CSV exports from Bitvavo (crypto exchange).

**Supported Transaction Types:**
- buy → BUY
- sell → SELL
- deposit/withdrawal of fiat → DEPOSIT/WITHDRAWAL
- deposit/withdrawal of crypto → ADJUSTMENT
- staking → ADJUSTMENT

Only ``Status=Completed`` rows are imported. Rows with other statuses are
reported as warnings and skipped.
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

COL_DATE = "Date"
COL_TIME = "Time"
COL_TYPE = "Type"
COL_CURRENCY = "Currency"
COL_AMOUNT = "Amount"
COL_QUOTE_CURRENCY = "Quote Currency"
COL_PAID_CURRENCY = "Received / Paid Currency"
COL_PAID_AMOUNT = "Received / Paid Amount"
COL_FEE_CURRENCY = "Fee currency"
COL_FEE_AMOUNT = "Fee amount"
COL_STATUS = "Status"
COL_TX_ID = "Transaction ID"


def _parse_bitvavo_datetime(date_value: str, time_value: str) -> Optional[date_type]:
    """Parse Bitvavo date + time columns."""
    date_value = date_value.strip()
    time_value = time_value.strip()
    if not date_value:
        return None

    combined = f"{date_value} {time_value}" if time_value else date_value
    formats = [
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(combined, fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(value: str) -> Optional[Decimal]:
    """Parse CSV decimal with light currency/thousands cleanup."""
    value = value.strip()
    if not value:
        return None
    value = re.sub(r"[€$£\s]", "", value)
    if "," in value and "." not in value:
        value = value.replace(",", ".")
    else:
        value = value.replace(",", "")
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _is_fiat_currency(code: str) -> bool:
    """Return True when code can be represented by Currency (ISO 4217)."""
    code = code.strip().upper()
    if not code:
        return False
    try:
        Currency(code=code, amount=Decimal("0"))
        return True
    except Exception:
        return False


@register_provider(BRIMProviderRegistry)
class BitvavoBrokerProvider(BRIMProvider):
    """Bitvavo crypto exchange CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_bitvavo"

    @property
    def provider_name(self) -> str:
        return "Bitvavo"

    @property
    def description(self) -> str:
        return "Import transactions from Bitvavo CSV export. Supports crypto buys, sells, staking rewards, cash deposits/withdrawals, and crypto balance adjustments."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://bitvavo.com/favicon-32x32.png?v=7ba51b544a17c10de8defa086df79917"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/bitvavo/"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Bitvavo format by distinctive headers."""
        if file_path.suffix.lower() != ".csv":
            return False
        try:
            content = self._read_file_head(file_path, num_lines=3)
            first_line = content.split("\n")[0].lower() if content else ""
            required = [
                "timezone",
                "date",
                "time",
                "type",
                "currency",
                "amount",
                "quote currency",
                "received / paid amount",
            ]
            return all(col in first_line for col in required)
        except Exception:
            return False

    @staticmethod
    def _get_asset_id(symbol: str, asset_to_fake_id: Dict[str, int], extracted_assets: Dict[int, BRIMExtractedAssetInfo], next_fake_id: int) -> tuple[int, int]:
        if symbol in asset_to_fake_id:
            return asset_to_fake_id[symbol], next_fake_id
        asset_id = next_fake_id
        asset_to_fake_id[symbol] = asset_id
        extracted_assets[asset_id] = BRIMExtractedAssetInfo(extracted_symbol=symbol, extracted_isin=None, extracted_name=f"{symbol} (Crypto)")
        return asset_id, next_fake_id - 1

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """Parse Bitvavo CSV export file."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets: Dict[int, BRIMExtractedAssetInfo] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        detected_delim = self.detect_csv_delimiter(file_path)

        try:
            with open(file_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=detected_delim)
                row_num = 1

                for row in reader:
                    row_num += 1
                    status = row.get(COL_STATUS, "").strip()
                    tx_type_raw = row.get(COL_TYPE, "").strip().lower()
                    if not tx_type_raw:
                        continue
                    if status.lower() != "completed":
                        warnings.append(f"Row {row_num}: status '{status}' is not Completed, skipping")
                        continue

                    tx_date = _parse_bitvavo_datetime(row.get(COL_DATE, ""), row.get(COL_TIME, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date/time, skipping")
                        continue

                    symbol = row.get(COL_CURRENCY, "").strip().upper()
                    quantity = _parse_decimal(row.get(COL_AMOUNT, "")) or Decimal("0")
                    cash_currency = row.get(COL_PAID_CURRENCY, "").strip().upper() or row.get(COL_QUOTE_CURRENCY, "").strip().upper()
                    cash_amount = _parse_decimal(row.get(COL_PAID_AMOUNT, ""))
                    tx_id = row.get(COL_TX_ID, "").strip()
                    desc_suffix = f" ({tx_id})" if tx_id else ""

                    if tx_type_raw in ("buy", "sell"):
                        if not symbol:
                            warnings.append(f"Row {row_num}: {tx_type_raw} missing crypto currency, skipping")
                            continue
                        if not cash_currency or cash_amount is None or cash_amount == 0:
                            warnings.append(f"Row {row_num}: {tx_type_raw} missing fiat cash amount, skipping")
                            continue
                        asset_id, next_fake_id = self._get_asset_id(symbol, asset_to_fake_id, extracted_assets, next_fake_id)
                        tx_type = TransactionType.BUY if tx_type_raw == "buy" else TransactionType.SELL
                        quantity = abs(quantity) if tx_type == TransactionType.BUY else -abs(quantity)
                        cash_amount = -abs(cash_amount) if tx_type == TransactionType.BUY else abs(cash_amount)
                        self._create_transaction(
                            row_num=row_num,
                            transactions=transactions,
                            validation_issues=validation_issues,
                            context=f"{tx_type_raw}: {symbol}",
                            broker_id=broker_id,
                            asset_id=asset_id,
                            type=tx_type,
                            date=tx_date,
                            quantity=quantity,
                            cash=Currency(code=cash_currency, amount=cash_amount),
                            description=f"{tx_type_raw}: {symbol}{desc_suffix}",
                            tags=["import", "bitvavo", "crypto"],
                        )

                    elif tx_type_raw in ("deposit", "withdrawal"):
                        if not symbol:
                            warnings.append(f"Row {row_num}: {tx_type_raw} missing currency, skipping")
                            continue
                        if _is_fiat_currency(symbol):
                            tx_type = TransactionType.DEPOSIT if tx_type_raw == "deposit" else TransactionType.WITHDRAWAL
                            cash_amount_for_type = abs(quantity) if tx_type == TransactionType.DEPOSIT else -abs(quantity)
                            if cash_amount_for_type == 0:
                                warnings.append(f"Row {row_num}: zero cash {tx_type_raw}, skipping")
                                continue
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=f"{tx_type_raw}: {symbol}",
                                broker_id=broker_id,
                                asset_id=None,
                                type=tx_type,
                                date=tx_date,
                                quantity=Decimal("0"),
                                cash=Currency(code=symbol, amount=cash_amount_for_type),
                                description=f"{tx_type_raw}: {symbol}{desc_suffix}",
                                tags=["import", "bitvavo", "cash"],
                            )
                        else:
                            asset_id, next_fake_id = self._get_asset_id(symbol, asset_to_fake_id, extracted_assets, next_fake_id)
                            quantity = abs(quantity) if tx_type_raw == "deposit" else -abs(quantity)
                            if quantity == 0:
                                warnings.append(f"Row {row_num}: zero crypto {tx_type_raw}, skipping")
                                continue
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=f"{tx_type_raw}: {symbol}",
                                broker_id=broker_id,
                                asset_id=asset_id,
                                type=TransactionType.ADJUSTMENT,
                                date=tx_date,
                                quantity=quantity,
                                cash=None,
                                description=f"{tx_type_raw}: {symbol}{desc_suffix}",
                                tags=["import", "bitvavo", "crypto"],
                            )

                    elif tx_type_raw == "staking":
                        if not symbol:
                            warnings.append(f"Row {row_num}: staking missing crypto currency, skipping")
                            continue
                        if quantity == 0:
                            warnings.append(f"Row {row_num}: zero staking quantity, skipping")
                            continue
                        asset_id, next_fake_id = self._get_asset_id(symbol, asset_to_fake_id, extracted_assets, next_fake_id)
                        self._create_transaction(
                            row_num=row_num,
                            transactions=transactions,
                            validation_issues=validation_issues,
                            context=f"staking: {symbol}",
                            broker_id=broker_id,
                            asset_id=asset_id,
                            type=TransactionType.ADJUSTMENT,
                            date=tx_date,
                            quantity=quantity,
                            cash=None,
                            description=f"staking: {symbol}{desc_suffix}",
                            tags=["import", "bitvavo", "staking", "crypto"],
                        )
                    else:
                        warnings.append(f"Row {row_num}: unknown type '{tx_type_raw}', skipping")
                        continue

                    fee_amount = _parse_decimal(row.get(COL_FEE_AMOUNT, ""))
                    fee_currency = row.get(COL_FEE_CURRENCY, "").strip().upper()
                    if fee_amount and fee_amount > 0 and fee_currency:
                        if _is_fiat_currency(fee_currency):
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=f"Fee: {fee_currency}",
                                broker_id=broker_id,
                                asset_id=None,
                                type=TransactionType.FEE,
                                date=tx_date,
                                quantity=Decimal("0"),
                                cash=Currency(code=fee_currency, amount=-abs(fee_amount)),
                                description=f"Fee: {fee_currency}{desc_suffix}",
                                tags=["import", "bitvavo", "fee"],
                            )
                        else:
                            fee_asset_id, next_fake_id = self._get_asset_id(fee_currency, asset_to_fake_id, extracted_assets, next_fake_id)
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=f"Crypto fee: {fee_currency}",
                                broker_id=broker_id,
                                asset_id=fee_asset_id,
                                type=TransactionType.ADJUSTMENT,
                                date=tx_date,
                                quantity=-abs(fee_amount),
                                cash=None,
                                description=f"Crypto fee: {fee_currency}{desc_suffix}",
                                tags=["import", "bitvavo", "fee", "crypto"],
                            )

        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}") from None
        except Exception as e:
            raise BRIMParseError(f"Error parsing file: {e}") from e

        if not transactions:
            warnings.append("No valid transactions found in file")

        logger.info("Bitvavo file parsed", transaction_count=len(transactions), warning_count=len(warnings), asset_count=len(extracted_assets))

        return BRIMParseOutput(transactions=transactions, warnings=warnings, validation_issues=validation_issues, extracted_assets=extracted_assets)

    @property
    def test_file_pattern(self) -> Optional[str]:
        """Filename pattern for auto-detection tests."""
        return "bitvavo"
