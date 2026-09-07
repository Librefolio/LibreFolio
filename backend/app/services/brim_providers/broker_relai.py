"""
Relai Broker Report Import Plugin.

This plugin parses CSV exports from Relai. Relai reports Bitcoin-only buys and
sells with fiat cash and a separate fee column.
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
COL_TYPE = "Transaction Type"
COL_BTC_AMOUNT = "BTC Amount"
COL_CURRENCY_PAIR = "Currency Pair"
COL_FIAT_AMOUNT = "Fiat Amount (excl. fees)"
COL_FIAT_CURRENCY = "Fiat Currency"
COL_FEE = "Fee"
COL_FEE_CURRENCY = "Fee Currency"
COL_OPERATION_ID = "Operation ID"


def _parse_relai_datetime(value: str) -> Optional[date_type]:
    """Parse Relai ISO-Z datetime."""
    value = value.strip()
    if not value:
        return None
    value = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _parse_decimal(value: str) -> Optional[Decimal]:
    """Parse Relai decimal."""
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


@register_provider(BRIMProviderRegistry)
class RelaiBrokerProvider(BRIMProvider):
    """Relai Bitcoin CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_relai"

    @property
    def provider_name(self) -> str:
        return "Relai"

    @property
    def description(self) -> str:
        return "Import Bitcoin buys and sells from Relai CSV export, including separate fee transactions."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://relai.app/app/uploads/2023/06/cropped-App-icon-32x32.png"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/relai/"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Relai format by distinctive headers."""
        if file_path.suffix.lower() != ".csv":
            return False
        try:
            content = self._read_file_head(file_path, num_lines=3)
            first_line = content.split("\n")[0].lower() if content else ""
            required = [
                "transaction type",
                "btc amount",
                "currency pair",
                "fiat amount (excl. fees)",
                "fiat currency",
            ]
            return all(col in first_line for col in required)
        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:  # noqa: C901 — flat row loop: validation guards and fee handling, no nested logic
        """Parse Relai CSV export file."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets: Dict[int, BRIMExtractedAssetInfo] = {FAKE_ASSET_ID_BASE: BRIMExtractedAssetInfo(extracted_symbol="BTC", extracted_isin=None, extracted_name="BTC (Crypto)")}

        detected_delim = self.detect_csv_delimiter(file_path)

        try:
            with open(file_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=detected_delim)
                row_num = 1

                for row in reader:
                    row_num += 1
                    tx_type_raw = row.get(COL_TYPE, "").strip().lower()
                    if not tx_type_raw:
                        continue
                    if tx_type_raw not in ("buy", "sell"):
                        warnings.append(f"Row {row_num}: unsupported Relai type '{tx_type_raw}', skipping")
                        continue

                    tx_date = _parse_relai_datetime(row.get(COL_DATE, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date, skipping")
                        continue

                    btc_amount = _parse_decimal(row.get(COL_BTC_AMOUNT, ""))
                    fiat_amount = _parse_decimal(row.get(COL_FIAT_AMOUNT, ""))
                    fiat_currency = row.get(COL_FIAT_CURRENCY, "").strip().upper()
                    if btc_amount is None or btc_amount == 0:
                        warnings.append(f"Row {row_num}: missing BTC amount, skipping")
                        continue
                    if fiat_amount is None or fiat_amount == 0 or not fiat_currency:
                        warnings.append(f"Row {row_num}: missing fiat amount/currency, skipping")
                        continue

                    operation_id = row.get(COL_OPERATION_ID, "").strip()
                    desc_suffix = f" ({operation_id})" if operation_id else ""
                    tx_type = TransactionType.BUY if tx_type_raw == "buy" else TransactionType.SELL
                    quantity = abs(btc_amount) if tx_type == TransactionType.BUY else -abs(btc_amount)
                    cash_amount = -abs(fiat_amount) if tx_type == TransactionType.BUY else abs(fiat_amount)
                    self._create_transaction(
                        row_num=row_num,
                        transactions=transactions,
                        validation_issues=validation_issues,
                        context=f"{tx_type_raw}: BTC",
                        broker_id=broker_id,
                        asset_id=FAKE_ASSET_ID_BASE,
                        type=tx_type,
                        date=tx_date,
                        quantity=quantity,
                        cash=Currency(code=fiat_currency, amount=cash_amount),
                        description=f"{tx_type_raw}: BTC{desc_suffix}",
                        tags=["import", "relai", "crypto"],
                    )

                    fee_amount = _parse_decimal(row.get(COL_FEE, ""))
                    fee_currency = row.get(COL_FEE_CURRENCY, "").strip().upper() or fiat_currency
                    if fee_amount and fee_amount > 0:
                        self._create_transaction(
                            row_num=row_num,
                            transactions=transactions,
                            validation_issues=validation_issues,
                            context="Fee: BTC",
                            broker_id=broker_id,
                            asset_id=FAKE_ASSET_ID_BASE,
                            type=TransactionType.FEE,
                            date=tx_date,
                            quantity=Decimal("0"),
                            cash=Currency(code=fee_currency, amount=-abs(fee_amount)),
                            description=f"Fee: BTC{desc_suffix}",
                            tags=["import", "relai", "fee"],
                        )

        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}") from None
        except Exception as e:
            raise BRIMParseError(f"Error parsing file: {e}") from e

        if not transactions:
            warnings.append("No valid transactions found in file")

        logger.info("Relai file parsed", transaction_count=len(transactions), warning_count=len(warnings), asset_count=len(extracted_assets))

        return BRIMParseOutput(transactions=transactions, warnings=warnings, validation_issues=validation_issues, extracted_assets=extracted_assets)

    @property
    def test_file_pattern(self) -> Optional[str]:
        """Filename pattern for auto-detection tests."""
        return "relai"
