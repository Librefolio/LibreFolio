"""
Crypto.com Broker Report Import Plugin.

Best-effort parser for Crypto.com CSV exports. The export mixes purchases,
internal transfers, swaps, card operations, lockups, and rewards in one format.
This plugin stays conservative: it imports only clearly classifiable buys,
sells, and crypto/cash rewards. Internal transfers, swaps, lock/unlock rows,
and ambiguous movements are skipped with warnings.
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

COL_TIMESTAMP = "Timestamp (UTC)"
COL_DESCRIPTION = "Transaction Description"
COL_CURRENCY = "Currency"
COL_AMOUNT = "Amount"
COL_NATIVE_CURRENCY = "Native Currency"
COL_NATIVE_AMOUNT = "Native Amount"
COL_KIND = "Transaction Kind"
COL_HASH = "Transaction Hash"

BUY_KINDS = {"viban_purchase", "crypto_purchase"}
SELL_KINDS = {"viban_sell", "crypto_sell", "crypto_sale"}
SKIP_KIND_PARTS = [
    "_transfer",
    "transfer_",
    "crypto_to_exchange_transfer",
    "crypto_wallet_swap_",
    "crypto_exchange",
    "crypto_deposit",
    "lockup",
    "card_top_up",
]
REWARD_KIND_PARTS = ["reward", "interest", "cashback"]


def _parse_cryptocom_datetime(value: str) -> Optional[date_type]:
    """Parse Crypto.com UTC timestamp."""
    value = value.strip()
    if not value:
        return None
    formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(value: str) -> Optional[Decimal]:
    """Parse Crypto.com decimal."""
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
class CryptoComBrokerProvider(BRIMProvider):
    """Crypto.com CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_cryptocom"

    @property
    def provider_name(self) -> str:
        return "Crypto.com"

    @property
    def description(self) -> str:
        return "Best-effort Crypto.com CSV import. Imports clear buys, sells, and rewards; skips internal transfers, swaps, lockups, and ambiguous rows with warnings."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> str:
        return "https://crypto.com/favicon.ico"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/cryptocom/"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Crypto.com format by distinctive headers."""
        if file_path.suffix.lower() != ".csv":
            return False
        try:
            content = self._read_file_head(file_path, num_lines=3)
            first_line = content.split("\n")[0].lower() if content else ""
            required = [
                "timestamp (utc)",
                "transaction description",
                "native currency",
                "transaction kind",
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

    @staticmethod
    def _should_skip_kind(kind: str) -> bool:
        return any(part in kind for part in SKIP_KIND_PARTS)

    @staticmethod
    def _is_reward_kind(kind: str) -> bool:
        return kind == "crypto_earn_interest_paid" or any(part in kind for part in REWARD_KIND_PARTS)

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """Parse Crypto.com CSV export file."""
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
                    kind = row.get(COL_KIND, "").strip().lower()
                    if not kind:
                        continue

                    tx_date = _parse_cryptocom_datetime(row.get(COL_TIMESTAMP, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid timestamp, skipping")
                        continue

                    description = row.get(COL_DESCRIPTION, "").strip() or kind
                    tx_hash = row.get(COL_HASH, "").strip()
                    desc_suffix = f" ({tx_hash})" if tx_hash else ""
                    symbol = row.get(COL_CURRENCY, "").strip().upper()
                    amount = _parse_decimal(row.get(COL_AMOUNT, "")) or Decimal("0")
                    native_currency = row.get(COL_NATIVE_CURRENCY, "").strip().upper()
                    native_amount = _parse_decimal(row.get(COL_NATIVE_AMOUNT, "")) or Decimal("0")

                    if kind in BUY_KINDS:
                        if not symbol or _is_fiat_currency(symbol):
                            warnings.append(f"Row {row_num}: buy missing crypto currency, skipping")
                            continue
                        if native_amount == 0 or not native_currency:
                            warnings.append(f"Row {row_num}: buy missing native fiat amount, skipping")
                            continue
                        asset_id, next_fake_id = self._get_asset_id(symbol, asset_to_fake_id, extracted_assets, next_fake_id)
                        self._create_transaction(
                            row_num=row_num,
                            transactions=transactions,
                            validation_issues=validation_issues,
                            context=f"{kind}: {symbol}",
                            broker_id=broker_id,
                            asset_id=asset_id,
                            type=TransactionType.BUY,
                            date=tx_date,
                            quantity=abs(amount),
                            cash=Currency(code=native_currency, amount=-abs(native_amount)),
                            description=f"{description}{desc_suffix}",
                            tags=["import", "cryptocom", "crypto"],
                        )
                    elif kind in SELL_KINDS:
                        if not symbol or _is_fiat_currency(symbol):
                            warnings.append(f"Row {row_num}: sell missing crypto currency, skipping")
                            continue
                        if native_amount == 0 or not native_currency:
                            warnings.append(f"Row {row_num}: sell missing native fiat amount, skipping")
                            continue
                        asset_id, next_fake_id = self._get_asset_id(symbol, asset_to_fake_id, extracted_assets, next_fake_id)
                        self._create_transaction(
                            row_num=row_num,
                            transactions=transactions,
                            validation_issues=validation_issues,
                            context=f"{kind}: {symbol}",
                            broker_id=broker_id,
                            asset_id=asset_id,
                            type=TransactionType.SELL,
                            date=tx_date,
                            quantity=-abs(amount),
                            cash=Currency(code=native_currency, amount=abs(native_amount)),
                            description=f"{description}{desc_suffix}",
                            tags=["import", "cryptocom", "crypto"],
                        )
                    elif self._is_reward_kind(kind):
                        if symbol and not _is_fiat_currency(symbol) and amount != 0:
                            asset_id, next_fake_id = self._get_asset_id(symbol, asset_to_fake_id, extracted_assets, next_fake_id)
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=f"{kind}: {symbol}",
                                broker_id=broker_id,
                                asset_id=asset_id,
                                type=TransactionType.ADJUSTMENT,
                                date=tx_date,
                                quantity=amount,
                                cash=None,
                                description=f"{description} (Value: {native_amount} {native_currency}){desc_suffix}" if native_amount and native_currency else f"{description}{desc_suffix}",
                                tags=["import", "cryptocom", "reward", "crypto"],
                            )
                        elif symbol and _is_fiat_currency(symbol) and amount > 0:
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=f"{kind}: {symbol}",
                                broker_id=broker_id,
                                asset_id=None,
                                type=TransactionType.INTEREST,
                                date=tx_date,
                                quantity=Decimal("0"),
                                cash=Currency(code=symbol, amount=abs(amount)),
                                description=f"{description}{desc_suffix}",
                                tags=["import", "cryptocom", "reward"],
                            )
                        elif native_currency and native_amount > 0:
                            self._create_transaction(
                                row_num=row_num,
                                transactions=transactions,
                                validation_issues=validation_issues,
                                context=f"{kind}: {native_currency}",
                                broker_id=broker_id,
                                asset_id=None,
                                type=TransactionType.INTEREST,
                                date=tx_date,
                                quantity=Decimal("0"),
                                cash=Currency(code=native_currency, amount=abs(native_amount)),
                                description=f"{description}{desc_suffix}",
                                tags=["import", "cryptocom", "reward"],
                            )
                        else:
                            warnings.append(f"Row {row_num}: reward has no importable amount, skipping")
                    elif self._should_skip_kind(kind):
                        warnings.append(f"Row {row_num}: skipped internal/ambiguous Crypto.com kind '{kind}'")
                    else:
                        warnings.append(f"Row {row_num}: unsupported Crypto.com kind '{kind}', skipping")

        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}") from None
        except Exception as e:
            raise BRIMParseError(f"Error parsing file: {e}") from e

        if not transactions:
            warnings.append("No valid transactions found in file")

        logger.info("Crypto.com file parsed", transaction_count=len(transactions), warning_count=len(warnings), asset_count=len(extracted_assets))

        return BRIMParseOutput(transactions=transactions, warnings=warnings, validation_issues=validation_issues, extracted_assets=extracted_assets)

    @property
    def test_file_pattern(self) -> Optional[str]:
        """Filename pattern for auto-detection tests."""
        return "cryptocom"
