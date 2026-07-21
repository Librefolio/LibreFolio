"""
CoinTracking Broker Report Import Plugin.

Parses CoinTracking CSV exports with duplicate ``Cur.`` columns.  Columns are
read by index, not by ``DictReader``.

Supported mappings:
- Trade crypto bought with fiat → BUY; crypto sold for fiat → SELL
- Crypto deposits/withdrawals → ADJUSTMENT quantity +/- (cashless)
- Fiat deposits/withdrawals → DEPOSIT / WITHDRAWAL
- Staking rewards → ADJUSTMENT quantity + (cashless)
- Fiat fees → separate FEE transaction

Known limits:
- Crypto-to-crypto trades are skipped with a warning because LibreFolio cannot
  express both crypto legs as one valid cash-backed BUY/SELL transaction.
- Crypto-denominated fees are modeled as cashless negative ADJUSTMENT rows when
  possible; invalid/ambiguous fees are skipped with a warning.
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

COL_TYPE = 0
COL_BUY_AMOUNT = 1
COL_BUY_CUR = 2
COL_SELL_AMOUNT = 3
COL_SELL_CUR = 4
COL_FEE_AMOUNT = 5
COL_FEE_CUR = 6
COL_EXCHANGE = 7
COL_GROUP = 8
COL_COMMENT = 9
COL_DATE = 10
COL_TX_ID = 11

EXPECTED_HEADER = ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"]


def _parse_cointracking_date(value: str) -> Optional[date_type]:
    """Parse CoinTracking dates in dd.mm.yyyy and ISO datetime formats."""
    value = value.strip()
    if not value:
        return None

    for fmt in ("%d.%m.%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_cointracking_number(value: str) -> Optional[Decimal]:
    """Parse CoinTracking decimal numbers."""
    value = value.strip()
    if not value:
        return None
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None


def _normalise_symbol(value: str) -> str:
    return value.strip().upper()


def _is_fiat_currency(value: str) -> bool:
    try:
        Currency.validate_code(value)
    except ValueError:
        return False
    return True


@register_provider(BRIMProviderRegistry)
class CoinTrackingBrokerProvider(BRIMProvider):
    """CoinTracking CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_cointracking"

    @property
    def provider_name(self) -> str:
        return "CoinTracking"

    @property
    def description(self) -> str:
        return "Import transactions from CoinTracking CSV exports. Supports fiat-backed crypto trades, transfers, staking rewards, and fiat fees."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://cointracking.info/favicon.ico"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/cointracking/"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "cointracking"

    def can_parse(self, file_path: Path) -> bool:
        """Detect CoinTracking format by its exact duplicate-column header."""
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=2)
            first_line = content.splitlines()[0] if content else ""
            header = next(csv.reader([first_line]))
            return header == EXPECTED_HEADER
        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """Parse CoinTracking CSV export file."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets_raw: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE
        skipped_crypto_trades = 0
        skipped_unknown_types = 0
        skipped_invalid_rows = 0

        def get_asset_id(symbol: str) -> int:
            nonlocal next_fake_id
            symbol = _normalise_symbol(symbol)
            if symbol in asset_to_fake_id:
                return asset_to_fake_id[symbol]
            asset_id = next_fake_id
            asset_to_fake_id[symbol] = asset_id
            extracted_assets_raw[asset_id] = {
                "extracted_symbol": symbol,
                "extracted_isin": None,
                "extracted_name": f"{symbol} (Crypto)",
            }
            next_fake_id -= 1
            return asset_id

        def create_fee(row_num: int, tx_date: date_type, fee: Optional[Decimal], fee_cur: str, asset_id: Optional[int], context: str) -> None:
            if fee is None or fee <= 0 or not fee_cur:
                return
            if _is_fiat_currency(fee_cur):
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
                    cash=Currency(code=fee_cur, amount=-fee),
                    description=f"CoinTracking fee: {context}",
                    tags=["import", "cointracking", "fee"],
                )
                return
            fee_asset_id = get_asset_id(fee_cur)
            warnings.append(f"Row {row_num}: crypto-denominated fee {fee} {fee_cur} modeled as ADJUSTMENT")
            self._create_transaction(
                row_num=row_num,
                transactions=transactions,
                validation_issues=validation_issues,
                context=f"Crypto fee: {context}",
                broker_id=broker_id,
                asset_id=fee_asset_id,
                type=TransactionType.ADJUSTMENT,
                date=tx_date,
                quantity=-fee,
                cash=None,
                description=f"CoinTracking crypto fee: {context}",
                tags=["import", "cointracking", "fee"],
            )

        detected_delim = self.detect_csv_delimiter(file_path)

        try:
            with open(file_path, encoding="utf-8-sig") as f:
                reader = csv.reader(f, delimiter=detected_delim)
                header = next(reader, None)
                if header != EXPECTED_HEADER:
                    raise BRIMParseError("Unexpected CoinTracking header")

                row_num = 1
                for row in reader:
                    row_num += 1
                    if not row or all(not cell.strip() for cell in row):
                        continue
                    if len(row) <= COL_TX_ID:
                        skipped_invalid_rows += 1
                        warnings.append(f"Row {row_num}: insufficient columns, skipping")
                        continue

                    tx_date = _parse_cointracking_date(row[COL_DATE])
                    if not tx_date:
                        skipped_invalid_rows += 1
                        warnings.append(f"Row {row_num}: invalid date '{row[COL_DATE]}', skipping")
                        continue

                    tx_type_raw = row[COL_TYPE].strip()
                    buy_amount = _parse_cointracking_number(row[COL_BUY_AMOUNT])
                    buy_cur = _normalise_symbol(row[COL_BUY_CUR])
                    sell_amount = _parse_cointracking_number(row[COL_SELL_AMOUNT])
                    sell_cur = _normalise_symbol(row[COL_SELL_CUR])
                    fee_amount = _parse_cointracking_number(row[COL_FEE_AMOUNT])
                    fee_cur = _normalise_symbol(row[COL_FEE_CUR])
                    exchange = row[COL_EXCHANGE].strip()
                    comment = row[COL_COMMENT].strip()
                    context = f"{tx_type_raw}: {exchange}" if exchange else tx_type_raw
                    if comment:
                        context = f"{context} — {comment}"

                    tx_type_lower = tx_type_raw.lower()
                    asset_id = None

                    if tx_type_lower == "trade":
                        if buy_amount is None or sell_amount is None or not buy_cur or not sell_cur:
                            skipped_invalid_rows += 1
                            warnings.append(f"Row {row_num}: incomplete trade, skipping")
                            continue

                        buy_is_fiat = _is_fiat_currency(buy_cur)
                        sell_is_fiat = _is_fiat_currency(sell_cur)
                        if not buy_is_fiat and sell_is_fiat:
                            asset_id = get_asset_id(buy_cur)
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=context,
                                broker_id=broker_id,
                                asset_id=asset_id,
                                type=TransactionType.BUY,
                                date=tx_date,
                                quantity=abs(buy_amount),
                                cash=Currency(code=sell_cur, amount=-abs(sell_amount)),
                                description=f"CoinTracking trade buy {buy_cur} on {exchange}" if exchange else f"CoinTracking trade buy {buy_cur}",
                                tags=["import", "cointracking"],
                            )
                        elif buy_is_fiat and not sell_is_fiat:
                            asset_id = get_asset_id(sell_cur)
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=context,
                                broker_id=broker_id,
                                asset_id=asset_id,
                                type=TransactionType.SELL,
                                date=tx_date,
                                quantity=-abs(sell_amount),
                                cash=Currency(code=buy_cur, amount=abs(buy_amount)),
                                description=f"CoinTracking trade sell {sell_cur} on {exchange}" if exchange else f"CoinTracking trade sell {sell_cur}",
                                tags=["import", "cointracking"],
                            )
                        else:
                            skipped_crypto_trades += 1
                            warnings.append(f"Row {row_num}: crypto-to-crypto or fiat-to-fiat trade ({buy_cur}/{sell_cur}) not supported, skipping")
                            continue

                    elif tx_type_lower == "deposit":
                        if buy_amount is None or buy_amount <= 0 or not buy_cur:
                            skipped_invalid_rows += 1
                            warnings.append(f"Row {row_num}: invalid deposit, skipping")
                            continue
                        if _is_fiat_currency(buy_cur):
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=context,
                                broker_id=broker_id,
                                asset_id=None,
                                type=TransactionType.DEPOSIT,
                                date=tx_date,
                                quantity=Decimal("0"),
                                cash=Currency(code=buy_cur, amount=abs(buy_amount)),
                                description=f"CoinTracking fiat deposit {buy_cur}",
                                tags=["import", "cointracking"],
                            )
                        else:
                            asset_id = get_asset_id(buy_cur)
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=context,
                                broker_id=broker_id,
                                asset_id=asset_id,
                                type=TransactionType.ADJUSTMENT,
                                date=tx_date,
                                quantity=abs(buy_amount),
                                cash=None,
                                description=f"CoinTracking crypto deposit {buy_cur}",
                                tags=["import", "cointracking"],
                            )

                    elif tx_type_lower == "withdrawal":
                        if sell_amount is None or sell_amount <= 0 or not sell_cur:
                            skipped_invalid_rows += 1
                            warnings.append(f"Row {row_num}: invalid withdrawal, skipping")
                            continue
                        if _is_fiat_currency(sell_cur):
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=context,
                                broker_id=broker_id,
                                asset_id=None,
                                type=TransactionType.WITHDRAWAL,
                                date=tx_date,
                                quantity=Decimal("0"),
                                cash=Currency(code=sell_cur, amount=-abs(sell_amount)),
                                description=f"CoinTracking fiat withdrawal {sell_cur}",
                                tags=["import", "cointracking"],
                            )
                        else:
                            asset_id = get_asset_id(sell_cur)
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=context,
                                broker_id=broker_id,
                                asset_id=asset_id,
                                type=TransactionType.ADJUSTMENT,
                                date=tx_date,
                                quantity=-abs(sell_amount),
                                cash=None,
                                description=f"CoinTracking crypto withdrawal {sell_cur}",
                                tags=["import", "cointracking"],
                            )

                    elif tx_type_lower == "staking":
                        if buy_amount is None or buy_amount <= 0 or not buy_cur:
                            skipped_invalid_rows += 1
                            warnings.append(f"Row {row_num}: invalid staking reward, skipping")
                            continue
                        if _is_fiat_currency(buy_cur):
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=context,
                                broker_id=broker_id,
                                asset_id=None,
                                type=TransactionType.INTEREST,
                                date=tx_date,
                                quantity=Decimal("0"),
                                cash=Currency(code=buy_cur, amount=abs(buy_amount)),
                                description=f"CoinTracking staking interest {buy_cur}",
                                tags=["import", "cointracking"],
                            )
                        else:
                            asset_id = get_asset_id(buy_cur)
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=context,
                                broker_id=broker_id,
                                asset_id=asset_id,
                                type=TransactionType.ADJUSTMENT,
                                date=tx_date,
                                quantity=abs(buy_amount),
                                cash=None,
                                description=f"CoinTracking staking reward {buy_cur}",
                                tags=["import", "cointracking"],
                            )

                    else:
                        skipped_unknown_types += 1
                        warnings.append(f"Row {row_num}: unknown type '{tx_type_raw}', skipping")
                        continue

                    create_fee(row_num, tx_date, fee_amount, fee_cur, asset_id, context)

        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}") from None
        except BRIMParseError:
            raise
        except Exception as e:
            raise BRIMParseError(f"Error parsing file: {e}") from e

        if skipped_crypto_trades:
            warnings.append(f"Summary: skipped {skipped_crypto_trades} unsupported crypto-to-crypto/fiat-to-fiat trade rows")
        if skipped_unknown_types:
            warnings.append(f"Summary: skipped {skipped_unknown_types} unknown type rows")
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
            "CoinTracking file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets_typed),
        )

        return BRIMParseOutput(transactions=transactions, warnings=warnings, validation_issues=validation_issues, extracted_assets=extracted_assets_typed)
