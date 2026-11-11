"""
Trade Republic Broker Report Import Plugin.

Two layouts, told apart by the header:

- **The Transaction export** (Profile → Account statements → Transaction export), Trade Republic's own CSV since April 2026,
  as written or re-saved by Excel: read by ``_transactions_export.py`` (since 1.2.0).
- **The Dutch 8-column CSV** (``Datum;Transactietype;Waarde (netto);…``): read below, unchanged.
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
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.brim_providers import _brim_io as io
from backend.app.services.brim_providers.broker_traderepublic import _transactions_export as transactions_export
from backend.app.services.provider_registry import register_provider

logger = structlog.get_logger(__name__)

# =============================================================================
# THE DUTCH 8-COLUMN CSV
# =============================================================================
# Built on an export found online, not reliable: no real export of this layout has ever been checked (the developer, 11/11/2026).
# The sample (sample_reports/traderepublic-export.csv) is the one of the Export-To-Ghostfolio project, byte for byte, and that file
# was written by the community tool pytr (`pytr export_transactions` in Dutch), not by Trade Republic, which had no CSV export then.
# Today's pytr writes 10 columns (ISIN2, Aantal2), which this exact header does not accept.

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
        return "Import Trade Republic's Transaction export (CSV, also when re-saved by Excel): buys and sells of funds, stocks and crypto with their fee and tax, interest with its withholding tax, stamp duty, dividends and cash transfers."

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
    def plugin_version(self) -> str:
        # 1.2.0 — the Transaction export (23 columns, also re-saved by Excel): each amount, fee and tax column is its own transaction (lane 73 TR).
        # 1.1.0 — the rows left out, and the fee and tax columns not imported, are listed in shared notices with the link to open an issue (W-B87).
        return "1.2.0"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/traderepublic/"

    def can_parse(self, file_path: Path) -> bool:
        """Detect the Transaction export by its required columns, or the Dutch CSV by its exact semicolon header."""
        if file_path.suffix.lower() != ".csv":
            return False
        try:
            return self._is_dutch_csv(file_path) or transactions_export.is_transactions_export(self, file_path)
        except Exception:  # a probe: a file it cannot read is not a Trade Republic export
            return False

    def _is_dutch_csv(self, file_path: Path) -> bool:
        with self._open_text(file_path, newline="") as f:
            header = next(csv.reader(f, delimiter=";"), [])
        return header == EXPECTED_HEADER

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """Parse a Trade Republic CSV: the Transaction export, or the Dutch CSV."""
        try:
            is_dutch = self._is_dutch_csv(file_path)
        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}", details={"code": "file_not_found", "context": {"file": file_path.name}}) from None
        if is_dutch:
            return self._parse_dutch_csv(file_path, broker_id)
        if not transactions_export.is_transactions_export(self, file_path):
            raise BRIMParseError("Unexpected Trade Republic CSV header", details={"code": "header_mismatch"})
        try:
            return transactions_export.parse(self, file_path, broker_id)
        except Exception as e:
            raise BRIMParseError(f"Error parsing file: {e}", details={"code": "file_unreadable", "context": {"error": str(e)}}) from e

    def _parse_dutch_csv(self, file_path: Path, broker_id: int) -> BRIMParseOutput:  # noqa: C901 — flat row loop: validation guards and per-type sign rules, no nested logic
        """Parse the Dutch 8-column CSV."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE
        skips = io.RowSkips()

        try:
            with self._open_text(file_path, newline="") as f:
                reader = csv.DictReader(f, delimiter=";")
                skips.set_headers(reader.fieldnames)
                row_num = 1

                if reader.fieldnames != EXPECTED_HEADER:
                    raise BRIMParseError("Unexpected Trade Republic CSV header", details={"code": "header_mismatch"})

                for row in reader:
                    row_num += 1
                    tx_type_raw = row.get(COL_TYPE, "").strip()
                    tx_type = TYPE_MAPPINGS.get(tx_type_raw.lower())
                    if not tx_type:
                        skips.unknown(row_num, row, f"unknown type: '{tx_type_raw}'")
                        continue

                    tx_date = _parse_traderepublic_date(row.get(COL_DATE, ""))
                    if not tx_date:
                        skips.unreadable(row_num, row, "invalid date")
                        continue

                    amount = _parse_traderepublic_number(row.get(COL_AMOUNT, ""))
                    if amount is None:
                        skips.unreadable(row_num, row, "invalid amount")
                        continue

                    note = row.get(COL_NOTE, "").strip()
                    isin = row.get(COL_ISIN, "").strip()
                    quantity = _parse_traderepublic_number(row.get(COL_QUANTITY, "")) or Decimal("0")

                    asset_id = None
                    if tx_type in (TransactionType.BUY, TransactionType.SELL, TransactionType.DIVIDEND):
                        if not isin:
                            skips.unreadable(row_num, row, f"{tx_type.value} without an ISIN")
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
                        # The row is imported, its fee and tax are not (W-B87): listed, so the user adds them by hand.
                        skips.unknown(row_num, row, "fee/tax columns (Kosten/Belasting) not imported")

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
            raise BRIMParseError(f"File not found: {file_path}", details={"code": "file_not_found", "context": {"file": file_path.name}}) from None
        except BRIMParseError:
            raise
        except Exception as e:
            raise BRIMParseError(f"Error parsing file: {e}", details={"code": "file_unreadable", "context": {"error": str(e)}}) from e

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
            warnings=[*warnings, *skips.notices()],
            validation_issues=validation_issues,
            extracted_assets=extracted_assets_typed,
        )

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "traderepublic"

    @property
    def test_file_patterns(self) -> List[str]:
        return ["traderepublic-export", "traderepublic-transactions"]
