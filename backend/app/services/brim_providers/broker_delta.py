"""
Delta Broker Report Import Plugin.

Parses Delta CSV exports on a best-effort basis.

Supported mappings:
- BUY/SELL with fiat quote currency → BUY/SELL with cash
- BUY/SELL with crypto quote currency → ADJUSTMENT on the base asset so the
  position still updates; quote leg is only recorded in the description
- WITHDRAW/DEPOSIT crypto → ADJUSTMENT quantity +/-; fiat → WITHDRAWAL/DEPOSIT
- TRANSFER rows are skipped
- DIVIDEND rows are supported when the sample contains stock + fiat proceeds

Known limits:
- Crypto-to-crypto trades cannot be represented as complete two-leg trades in
  LibreFolio BRIM, so only the base asset quantity is imported.
- Crypto-denominated fees are modeled as cashless negative ADJUSTMENT rows when
  possible; ambiguous fees are skipped with a warning.
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
from backend.app.schemas.common import Currency, is_fiat_currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.provider_registry import BRIMProviderRegistry, register_provider

logger = structlog.get_logger(__name__)

COL_DATE = "Date"
COL_WAY = "Way"
COL_BASE_AMOUNT = "Base amount"
COL_BASE_CURRENCY = "Base currency (name)"
COL_BASE_TYPE = "Base type"
COL_QUOTE_AMOUNT = "Quote amount"
COL_QUOTE_CURRENCY = "Quote currency"
COL_EXCHANGE = "Exchange"
COL_FEE_AMOUNT = "Fee amount"
COL_FEE_CURRENCY = "Fee currency (name)"
COL_BROKER = "Broker"
COL_NOTES = "Notes"

REQUIRED_COLUMNS = [
    COL_DATE,
    COL_WAY,
    COL_BASE_AMOUNT,
    COL_BASE_CURRENCY,
    COL_BASE_TYPE,
    COL_QUOTE_AMOUNT,
    COL_QUOTE_CURRENCY,
    COL_FEE_AMOUNT,
    COL_FEE_CURRENCY,
    COL_NOTES,
]


def _parse_delta_date(value: str) -> Optional[date_type]:
    """Parse Delta ISO date/time, including timezone offsets."""
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_delta_number(value: str) -> Optional[Decimal]:
    """Parse Delta decimal numbers."""
    value = value.strip()
    if not value:
        return None
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None


def _parse_delta_asset(value: str) -> Dict[str, Optional[str]]:
    """Extract symbol and optional name from strings like 'SOL (Solana)'."""
    value = value.strip()
    if not value:
        return {"symbol": None, "name": None}
    if " (" in value and value.endswith(")"):
        symbol, name = value.split(" (", 1)
        return {"symbol": symbol.strip().upper() or None, "name": name[:-1].strip() or None}
    return {"symbol": value.upper(), "name": None}


@register_provider(BRIMProviderRegistry)
class DeltaBrokerProvider(BRIMProvider):
    """Delta CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_delta"

    @property
    def provider_name(self) -> str:
        return "Delta"

    @property
    def description(self) -> str:
        return "Import transactions from Delta CSV exports. Best-effort support for fiat-backed trades, crypto transfers, dividends, and crypto-to-crypto adjustments."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://www.google.com/s2/favicons?domain=delta.app&sz=64"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/delta/"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "delta"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Delta format by its distinctive first-line header."""
        if file_path.suffix.lower() != ".csv":
            return False
        try:
            content = self._read_file_head(file_path, num_lines=2)
            first_line = content.splitlines()[0] if content else ""
            header = next(csv.reader([first_line]))
            return all(col in header for col in REQUIRED_COLUMNS)
        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:  # noqa: C901 — flat row-variant dispatch (if/elif over ways), no nested decisions
        """Parse Delta CSV export file."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets_raw: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE
        skipped_transfer_rows = 0
        skipped_unknown_rows = 0
        skipped_invalid_rows = 0
        crypto_trade_adjustments = 0

        def get_asset_id(symbol: str, name: Optional[str] = None, asset_type: Optional[str] = None) -> int:
            nonlocal next_fake_id
            symbol = symbol.strip().upper()
            if symbol in asset_to_fake_id:
                return asset_to_fake_id[symbol]
            asset_id = next_fake_id
            asset_to_fake_id[symbol] = asset_id
            extracted_assets_raw[asset_id] = {
                "extracted_symbol": symbol,
                "extracted_isin": None,
                "extracted_name": name or (f"{symbol} (Crypto)" if asset_type == "CRYPTO" else symbol),
            }
            next_fake_id -= 1
            return asset_id

        def create_fee(row_num: int, tx_date: date_type, fee: Optional[Decimal], fee_currency_raw: str, asset_id: Optional[int], context: str) -> None:
            if fee is None or fee <= 0 or not fee_currency_raw.strip():
                return
            fee_asset = _parse_delta_asset(fee_currency_raw)
            fee_symbol = fee_asset["symbol"]
            if not fee_symbol:
                return
            if is_fiat_currency(fee_symbol):
                self._create_transaction(
                    row_num=row_num,
                    transactions=transactions,
                    validation_issues=validation_issues,
                    context=f"Fee: {context}",
                    broker_id=broker_id,
                    asset_id=asset_id,
                    type=TransactionType.FEE,
                    date=tx_date,
                    quantity=Decimal("0"),
                    cash=Currency(code=fee_symbol, amount=-abs(fee)),
                    description=f"Delta fee: {context}",
                    tags=["import", "delta", "fee"],
                )
                return
            fee_asset_id = get_asset_id(fee_symbol, fee_asset["name"], "CRYPTO")
            warnings.append(f"Row {row_num}: crypto-denominated fee {fee} {fee_symbol} modeled as ADJUSTMENT")
            self._create_transaction(
                row_num=row_num,
                transactions=transactions,
                validation_issues=validation_issues,
                context=f"Crypto fee: {context}",
                broker_id=broker_id,
                asset_id=fee_asset_id,
                type=TransactionType.ADJUSTMENT,
                date=tx_date,
                quantity=-abs(fee),
                cash=None,
                description=f"Delta crypto fee: {context}",
                tags=["import", "delta", "fee"],
            )

        detected_delim = self.detect_csv_delimiter(file_path)

        try:
            with open(file_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=detected_delim)
                if not reader.fieldnames or not all(col in reader.fieldnames for col in REQUIRED_COLUMNS):
                    raise BRIMParseError("Unexpected Delta header")

                row_num = 1
                for row in reader:
                    row_num += 1
                    way = (row.get(COL_WAY) or "").strip().upper()
                    tx_date = _parse_delta_date(row.get(COL_DATE, ""))
                    if not tx_date:
                        skipped_invalid_rows += 1
                        warnings.append(f"Row {row_num}: invalid date '{row.get(COL_DATE, '')}', skipping")
                        continue

                    base_amount = _parse_delta_number(row.get(COL_BASE_AMOUNT, ""))
                    quote_amount = _parse_delta_number(row.get(COL_QUOTE_AMOUNT, ""))
                    fee_amount = _parse_delta_number(row.get(COL_FEE_AMOUNT, ""))
                    base_asset = _parse_delta_asset(row.get(COL_BASE_CURRENCY, ""))
                    quote_asset = _parse_delta_asset(row.get(COL_QUOTE_CURRENCY, ""))
                    base_symbol = base_asset["symbol"]
                    quote_symbol = quote_asset["symbol"]
                    base_type = (row.get(COL_BASE_TYPE) or "").strip().upper()
                    notes = (row.get(COL_NOTES) or "").strip()
                    exchange = (row.get(COL_EXCHANGE) or row.get(COL_BROKER) or "").strip()
                    context = f"{way}: {base_symbol or ''}".strip()
                    if exchange:
                        context = f"{context} on {exchange}"

                    if way == "TRANSFER":
                        skipped_transfer_rows += 1
                        warnings.append(f"Row {row_num}: TRANSFER rows are not imported, skipping")
                        continue

                    if way in ("BUY", "SELL"):
                        if base_amount is None or base_amount <= 0 or not base_symbol:
                            skipped_invalid_rows += 1
                            warnings.append(f"Row {row_num}: invalid {way} base asset/amount, skipping")
                            continue
                        asset_id = get_asset_id(base_symbol, base_asset["name"], base_type)
                        if quote_symbol and is_fiat_currency(quote_symbol) and quote_amount is not None and quote_amount > 0:
                            tx_type = TransactionType.BUY if way == "BUY" else TransactionType.SELL
                            quantity = abs(base_amount) if way == "BUY" else -abs(base_amount)
                            cash_amount = -abs(quote_amount) if way == "BUY" else abs(quote_amount)
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=context,
                                broker_id=broker_id,
                                asset_id=asset_id,
                                type=tx_type,
                                date=tx_date,
                                quantity=quantity,
                                cash=Currency(code=quote_symbol, amount=cash_amount),
                                description=notes or f"Delta {way.lower()} {base_symbol}",
                                tags=["import", "delta"],
                            )
                        else:
                            crypto_trade_adjustments += 1
                            quantity = abs(base_amount) if way == "BUY" else -abs(base_amount)
                            quote_text = f" for {quote_amount} {quote_symbol}" if quote_amount and quote_symbol else ""
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=context,
                                broker_id=broker_id,
                                asset_id=asset_id,
                                type=TransactionType.ADJUSTMENT,
                                date=tx_date,
                                quantity=quantity,
                                cash=None,
                                description=notes or f"Delta crypto-to-crypto {way.lower()} {base_symbol}{quote_text}; quote leg not imported",
                                tags=["import", "delta"],
                            )
                        create_fee(row_num, tx_date, fee_amount, row.get(COL_FEE_CURRENCY, ""), asset_id, context)

                    elif way in ("WITHDRAW", "DEPOSIT"):
                        if base_amount is None or base_amount <= 0 or not base_symbol:
                            skipped_invalid_rows += 1
                            warnings.append(f"Row {row_num}: invalid {way} base asset/amount, skipping")
                            continue
                        if base_type == "FIAT" or is_fiat_currency(base_symbol):
                            tx_type = TransactionType.DEPOSIT if way == "DEPOSIT" else TransactionType.WITHDRAWAL
                            cash_amount = abs(base_amount) if way == "DEPOSIT" else -abs(base_amount)
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=context,
                                broker_id=broker_id,
                                asset_id=None,
                                type=tx_type,
                                date=tx_date,
                                quantity=Decimal("0"),
                                cash=Currency(code=base_symbol, amount=cash_amount),
                                description=notes or f"Delta fiat {way.lower()} {base_symbol}",
                                tags=["import", "delta"],
                            )
                            create_fee(row_num, tx_date, fee_amount, row.get(COL_FEE_CURRENCY, ""), None, context)
                        else:
                            asset_id = get_asset_id(base_symbol, base_asset["name"], base_type)
                            quantity = abs(base_amount) if way == "DEPOSIT" else -abs(base_amount)
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=context,
                                broker_id=broker_id,
                                asset_id=asset_id,
                                type=TransactionType.ADJUSTMENT,
                                date=tx_date,
                                quantity=quantity,
                                cash=None,
                                description=notes or f"Delta crypto {way.lower()} {base_symbol}",
                                tags=["import", "delta"],
                            )
                            create_fee(row_num, tx_date, fee_amount, row.get(COL_FEE_CURRENCY, ""), asset_id, context)

                    elif way == "DIVIDEND":
                        if not base_symbol or quote_amount is None or quote_amount <= 0 or not quote_symbol or not is_fiat_currency(quote_symbol):
                            skipped_invalid_rows += 1
                            warnings.append(f"Row {row_num}: invalid dividend, skipping")
                            continue
                        asset_id = get_asset_id(base_symbol, base_asset["name"], base_type)
                        self._create_transaction(
                            row_num=row_num,
                            transactions=transactions,
                            validation_issues=validation_issues,
                            context=context,
                            broker_id=broker_id,
                            asset_id=asset_id,
                            type=TransactionType.DIVIDEND,
                            date=tx_date,
                            quantity=Decimal("0"),
                            cash=Currency(code=quote_symbol, amount=abs(quote_amount)),
                            description=notes or f"Delta dividend {base_symbol}",
                            tags=["import", "delta"],
                        )
                        create_fee(row_num, tx_date, fee_amount, row.get(COL_FEE_CURRENCY, ""), asset_id, context)

                    else:
                        skipped_unknown_rows += 1
                        warnings.append(f"Row {row_num}: unknown way '{way}', skipping")

        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}") from None
        except BRIMParseError:
            raise
        except Exception as e:
            raise BRIMParseError(f"Error parsing file: {e}") from e

        if crypto_trade_adjustments:
            warnings.append(f"Summary: modeled {crypto_trade_adjustments} crypto-to-crypto BUY/SELL rows as ADJUSTMENT")
        if skipped_transfer_rows:
            warnings.append(f"Summary: skipped {skipped_transfer_rows} TRANSFER rows")
        if skipped_unknown_rows:
            warnings.append(f"Summary: skipped {skipped_unknown_rows} unknown way rows")
        if skipped_invalid_rows:
            warnings.append(f"Summary: skipped {skipped_invalid_rows} invalid rows")
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
            "Delta file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets_typed),
        )

        return BRIMParseOutput(transactions=transactions, warnings=warnings, validation_issues=validation_issues, extracted_assets=extracted_assets_typed)
