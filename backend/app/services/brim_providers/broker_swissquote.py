"""
Swissquote Broker Report Import Plugin.

This plugin parses Swissquote semicolon-separated CSV exports.

**File Format Characteristics:**
- First line: column headers
- Separator: semicolon
- Date format: DD-MM-YYYY HH:MM:SS
- Dot decimal numbers

**Supported Transaction Types:**
- Buy → BUY
- Sell → SELL
- Dividend → DIVIDEND
- Custody fee / fee → FEE
- Debit → WITHDRAWAL
- Credit → DEPOSIT
- Interest / Interests → INTEREST
- Tax / Withholding → TAX

**Limitations:**
- Forex credit/debit legs are skipped with warnings. LibreFolio requires paired
  FX_CONVERSION transactions with non-zero cash and link_uuid; standalone
  Swissquote forex legs have no ISIN/Symbol and are not imported by this plugin.
- Costs and accrued interest are folded into the transaction description rather
  than emitted as separate transactions to avoid double-counting Net Amount.
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


COL_DATE = "Date"
COL_ORDER = "Order #"
COL_TRANSACTION = "Transaction"
COL_SYMBOL = "Symbol"
COL_NAME = "Name"
COL_ISIN = "ISIN"
COL_QUANTITY = "Quantity"
COL_UNIT_PRICE = "Unit price"
COL_COSTS = "Costs"
COL_ACCRUED_INTEREST = "Accrued Interest"
COL_NET_AMOUNT = "Net Amount"
COL_BALANCE = "Balance"
COL_CURRENCY = "Currency"

SWISSQUOTE_HEADER = [
    COL_DATE,
    COL_ORDER,
    COL_TRANSACTION,
    COL_SYMBOL,
    COL_NAME,
    COL_ISIN,
    COL_QUANTITY,
    COL_UNIT_PRICE,
    COL_COSTS,
    COL_ACCRUED_INTEREST,
    COL_NET_AMOUNT,
    COL_BALANCE,
    COL_CURRENCY,
]


def _parse_swissquote_date(value: str) -> Optional[date_type]:
    """Parse Swissquote DD-MM-YYYY HH:MM:SS dates."""
    value = value.strip()
    if not value:
        return None

    for fmt in ("%d-%m-%Y %H:%M:%S", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def _parse_swissquote_number(value: str) -> Optional[Decimal]:
    """Parse Swissquote dot-decimal numbers."""
    value = value.strip().replace('"', "")
    if not value:
        return None

    value = value.replace("'", "").replace(" ", "")
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _map_swissquote_transaction(value: str) -> Optional[TransactionType]:
    """Map Swissquote transaction labels to TransactionType."""
    tx = value.strip().lower()
    if not tx:
        return None
    if tx in {"buy", "sell", "dividend", "debit", "credit"}:
        return {
            "buy": TransactionType.BUY,
            "sell": TransactionType.SELL,
            "dividend": TransactionType.DIVIDEND,
            "debit": TransactionType.WITHDRAWAL,
            "credit": TransactionType.DEPOSIT,
        }[tx]
    if "interest" in tx:
        return TransactionType.INTEREST
    if "withholding" in tx or "tax" in tx:
        return TransactionType.TAX
    if "fee" in tx:
        return TransactionType.FEE
    return None


@register_provider(BRIMProviderRegistry)
class SwissquoteBrokerProvider(BRIMProvider):
    """Swissquote CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_swissquote"

    @property
    def provider_name(self) -> str:
        return "Swissquote"

    @property
    def description(self) -> str:
        return "Import Swissquote CSV exports for trades, dividends, cash movements, fees, taxes, and interest. Forex legs are skipped."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://www.swissquote.com/favicon.ico"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Swissquote format by checking the exact distinctive header."""
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=3)
            first_line = content.split("\n")[0].strip()
            header = next(csv.reader([first_line], delimiter=";"))
            return header == SWISSQUOTE_HEADER
        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:  # noqa: C901 — flat row loop: validation guards and per-type sign dispatch, no nested logic
        """Parse Swissquote CSV export file."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets_raw: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        detected_delim = self.detect_csv_delimiter(file_path)

        try:
            with open(file_path, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f, delimiter=detected_delim)
                if reader.fieldnames != SWISSQUOTE_HEADER:
                    raise BRIMParseError("Unexpected Swissquote CSV header")

                row_num = 1
                for row in reader:
                    row_num += 1
                    raw_tx = row.get(COL_TRANSACTION, "").strip()
                    tx_label = raw_tx.lower()
                    if tx_label in {"forex credit", "forex debit"}:
                        warnings.append(f"Row {row_num}: Swissquote forex leg '{raw_tx}' skipped")
                        continue

                    tx_type = _map_swissquote_transaction(raw_tx)
                    if tx_type is None:
                        warnings.append(f"Row {row_num}: unknown Swissquote transaction '{raw_tx}', skipping")
                        continue

                    tx_date = _parse_swissquote_date(row.get(COL_DATE, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date '{row.get(COL_DATE, '')}', skipping")
                        continue

                    amount = _parse_swissquote_number(row.get(COL_NET_AMOUNT, ""))
                    if amount is None or amount == 0:
                        warnings.append(f"Row {row_num}: missing or zero net amount for '{raw_tx}', skipping")
                        continue

                    currency = row.get(COL_CURRENCY, "").strip().upper()
                    if not currency:
                        warnings.append(f"Row {row_num}: missing currency for '{raw_tx}', skipping")
                        continue

                    quantity = _parse_swissquote_number(row.get(COL_QUANTITY, ""))
                    if quantity is None:
                        quantity = Decimal("0")

                    symbol = row.get(COL_SYMBOL, "").strip()
                    isin = row.get(COL_ISIN, "").strip()
                    name = row.get(COL_NAME, "").strip()
                    asset_id: Optional[int] = None

                    asset_required = tx_type in [TransactionType.BUY, TransactionType.SELL, TransactionType.DIVIDEND]
                    if asset_required:
                        asset_key = isin or symbol
                        if not asset_key:
                            warnings.append(f"Row {row_num}: {tx_type.value} requires ISIN or symbol, skipping")
                            continue
                        if asset_key in asset_to_fake_id:
                            asset_id = asset_to_fake_id[asset_key]
                        else:
                            asset_id = next_fake_id
                            asset_to_fake_id[asset_key] = asset_id
                            extracted_assets_raw[asset_id] = {
                                "extracted_symbol": symbol if symbol else None,
                                "extracted_isin": isin if isin else None,
                                "extracted_name": name if name else None,
                            }
                            next_fake_id -= 1

                    if tx_type == TransactionType.BUY:
                        if quantity <= 0:
                            warnings.append(f"Row {row_num}: BUY has non-positive quantity, skipping")
                            continue
                        quantity = abs(quantity)
                        amount = -abs(amount)
                    elif tx_type == TransactionType.SELL:
                        if quantity <= 0:
                            warnings.append(f"Row {row_num}: SELL has non-positive quantity, skipping")
                            continue
                        quantity = -abs(quantity)
                        amount = abs(amount)
                    elif tx_type == TransactionType.DIVIDEND:
                        if quantity != 0:
                            warnings.append(f"Row {row_num}: DIVIDEND source quantity '{quantity}' discarded")
                        quantity = Decimal("0")
                        amount = abs(amount)
                    elif tx_type in (TransactionType.INTEREST, TransactionType.DEPOSIT):
                        quantity = Decimal("0")
                        amount = abs(amount)
                    else:
                        quantity = Decimal("0")
                        amount = -abs(amount)

                    description_parts = [raw_tx]
                    if name:
                        description_parts.append(name)
                    costs = _parse_swissquote_number(row.get(COL_COSTS, ""))
                    if costs and costs != 0:
                        description_parts.append(f"costs {currency} {costs}")
                    accrued_interest = _parse_swissquote_number(row.get(COL_ACCRUED_INTEREST, ""))
                    if accrued_interest and accrued_interest != 0:
                        description_parts.append(f"accrued interest {currency} {accrued_interest}")
                    description = "; ".join(description_parts)

                    self._create_transaction(
                        row_num=row_num,
                        transactions=transactions,
                        validation_issues=validation_issues,
                        context=raw_tx,
                        broker_id=broker_id,
                        asset_id=asset_id,
                        type=tx_type,
                        date=tx_date,
                        quantity=quantity,
                        cash=Currency(code=currency, amount=amount),
                        description=description,
                        tags=["import", "swissquote"],
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
            "Swissquote file parsed",
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
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/swissquote/"

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "swissquote"
