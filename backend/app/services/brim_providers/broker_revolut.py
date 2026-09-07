"""
Revolut Broker Report Import Plugin.

This plugin parses CSV exports from Revolut Trading / Crypto.

**File Format Characteristics:**
- First line: column headers
- Separator: comma
- ISO datetime format with timezone (YYYY-MM-DDTHH:MM:SS.ffffffZ)
- Multi-currency support (USD, EUR, GBP)
- Amount includes currency symbol ($, €, £)

**Supported Transaction Types:**
- BUY - MARKET / BUY - LIMIT → BUY
- SELL - MARKET / SELL - LIMIT → SELL
- DIVIDEND → DIVIDEND
- CASH TOP-UP → DEPOSIT
- CASH WITHDRAWAL → WITHDRAWAL
- CUSTODY FEE → FEE

**Invest columns:**
- Date: ISO timestamp
- Ticker: Asset symbol
- Type: Transaction type
- Quantity: Number of shares
- Price per share: Unit price
- Total Amount: Total value (with currency symbol)
- Currency: Currency code

**Crypto columns:**
- Symbol: Crypto symbol
- Type: Transaction type
- Quantity: Crypto quantity
- Price: Unit price with currency
- Value: Cash value with currency
- Fees: Fee with currency
- Date: Human-readable timestamp
"""

from __future__ import annotations

import csv
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMExtractedAssetInfo, BRIMParseOutput, BRIMValidationIssue
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.provider_registry import BRIMProviderRegistry, register_provider

logger = structlog.get_logger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

COL_DATE = "Date"
COL_TICKER = "Ticker"
COL_TYPE = "Type"
COL_QUANTITY = "Quantity"
COL_TOTAL = "Total Amount"
COL_CURRENCY = "Currency"

COL_SYMBOL = "Symbol"
COL_PRICE = "Price"
COL_VALUE = "Value"
COL_FEES = "Fees"

# Type mapping
TYPE_MAPPINGS: Dict[str, TransactionType] = {
    "buy - market": TransactionType.BUY,
    "buy - limit": TransactionType.BUY,
    "sell - market": TransactionType.SELL,
    "sell - limit": TransactionType.SELL,
    "dividend": TransactionType.DIVIDEND,
    "cash top-up": TransactionType.DEPOSIT,
    "cash withdrawal": TransactionType.WITHDRAWAL,
    "custody fee": TransactionType.FEE,
}

# Types to skip
SKIP_TYPES = [
    "transfer",
    "stock split",
]

CRYPTO_TYPE_MAPPINGS: Dict[str, TransactionType] = {
    "buy": TransactionType.BUY,
    "sell": TransactionType.SELL,
}

CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
}


def _parse_revolut_datetime(value: str) -> Optional[date_type]:
    """Parse Revolut ISO datetime format."""
    value = value.strip()
    if not value:
        return None

    # Remove timezone Z and truncate microseconds
    value = value.replace("Z", "")
    if "." in value:
        value = value[:26]  # Keep up to 6 decimal places

    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def _parse_revolut_amount(value: str) -> Tuple[Optional[Decimal], str]:
    """
    Parse Revolut amount with currency symbol.

    Handles both positive and negative values:
      $30.93, -$30.93, €30, -€30, £30, -£30

    Returns: (amount, currency_code)
    """
    value = value.strip()
    if not value:
        return None, "USD"

    # Extract optional leading minus
    negative = value.startswith("-")
    if negative:
        value = value[1:]

    # Detect currency from symbol
    currency = "USD"
    if value.startswith("$"):
        currency = "USD"
        value = value[1:]
    elif value.startswith("€"):
        currency = "EUR"
        value = value[1:]
    elif value.startswith("£"):
        currency = "GBP"
        value = value[1:]

    value = _normalise_revolut_number_text(value)

    try:
        result = Decimal(value)
        return (-result if negative else result), currency
    except InvalidOperation:
        return None, currency


def _parse_revolut_quantity(value: str) -> Optional[Decimal]:
    """Parse Revolut quantity (may use comma as decimal)."""
    value = value.strip()
    if not value:
        return None

    # Handle European format
    value = value.replace(",", ".")

    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _normalise_revolut_number_text(value: str) -> str:
    """Normalise decimal/thousands separators before Decimal parsing."""
    value = value.strip().replace("\u00a0", " ")
    if "," in value and "." in value:
        return value.replace(",", "")
    if "," in value:
        return value.replace(",", ".")
    return value


def _parse_revolut_crypto_datetime(value: str) -> Optional[date_type]:
    """Parse Revolut Crypto date format."""
    value = value.strip().strip('"')
    if not value:
        return None

    formats = [
        "%b %d, %Y, %I:%M:%S %p",
        "%B %d, %Y, %I:%M:%S %p",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def _parse_revolut_money_with_currency(value: str) -> Tuple[Optional[Decimal], Optional[str]]:
    """Parse crypto money values like '89,162.28 SEK', '€10.00', '$10.00'."""
    value = value.strip().strip('"').replace("\u00a0", " ")
    if not value:
        return None, None

    negative = value.startswith("-")
    if negative:
        value = value[1:].strip()

    currency: Optional[str] = None
    for symbol, code in CURRENCY_SYMBOLS.items():
        if value.startswith(symbol):
            currency = code
            value = value[len(symbol) :].strip()
            break

    parts = value.rsplit(" ", 1)
    if len(parts) == 2 and len(parts[1]) == 3 and parts[1].isalpha():
        currency = parts[1].upper()
        value = parts[0].strip()

    value = _normalise_revolut_number_text(value)

    try:
        amount = Decimal(value)
        return (-amount if negative else amount), currency
    except InvalidOperation:
        return None, currency


def _header_set(fieldnames: Optional[List[str]]) -> set[str]:
    """Normalise CSV headers for variant detection."""
    return {field.strip().lower() for field in (fieldnames or [])}


def _is_invest_header(fieldnames: Optional[List[str]]) -> bool:
    headers = _header_set(fieldnames)
    return {"date", "ticker", "type", "quantity", "price per share", "total amount", "fx rate"}.issubset(headers)


def _is_crypto_header(fieldnames: Optional[List[str]]) -> bool:
    headers = _header_set(fieldnames)
    return {"symbol", "type", "quantity", "price", "value", "fees", "date"}.issubset(headers)


# =============================================================================
# PLUGIN IMPLEMENTATION
# =============================================================================


@register_provider(BRIMProviderRegistry)
class RevolutBrokerProvider(BRIMProvider):
    """Revolut Trading CSV export import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_revolut"

    @property
    def provider_name(self) -> str:
        return "Revolut"

    @property
    def description(self) -> str:
        return "Import transactions from Revolut CSV exports. " "Supports investments, crypto, dividends, and cash movements."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> str:
        return "https://assets.revolut.com/assets/favicons/favicon-32x32.png"

    @property
    def plugin_version(self) -> str:
        return "1.1.0"

    def can_parse(self, file_path: Path) -> bool:
        """Detect Revolut invest or crypto format by checking distinctive headers."""
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=3)
            first_line = content.split("\n")[0] if content else ""
            header = next(csv.reader([first_line]))

            # Revolut specific columns - must NOT have Freetrade-specific columns
            first_line_lower = first_line.lower()
            if "stamp duty" in first_line_lower or "title" in first_line_lower:
                return False

            return _is_invest_header(header) or _is_crypto_header(header)

        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """Parse Revolut CSV export file."""
        detected_delim = self.detect_csv_delimiter(file_path)

        try:
            with open(file_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=detected_delim)
                if _is_invest_header(reader.fieldnames):
                    return self._parse_invest(reader, broker_id)
                if _is_crypto_header(reader.fieldnames):
                    return self._parse_crypto(reader, broker_id)
                raise BRIMParseError("Unsupported Revolut CSV header")

        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}") from None
        except BRIMParseError:
            raise
        except Exception as e:
            raise BRIMParseError(f"Error parsing file: {e}") from e

    def _parse_invest(self, reader: csv.DictReader, broker_id: int) -> BRIMParseOutput:  # noqa: C901 — flat row loop: validation guards and per-type field mapping, no nested logic
        """Parse Revolut Invest rows."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        row_num = 1

        for row in reader:
            row_num += 1

            tx_type_raw = row.get(COL_TYPE, "").strip().lower()
            if not tx_type_raw:
                continue

            if any(skip in tx_type_raw for skip in SKIP_TYPES):
                continue

            tx_type = None
            for pattern, mapped_type in TYPE_MAPPINGS.items():
                if pattern in tx_type_raw:
                    tx_type = mapped_type
                    break

            if tx_type is None:
                warnings.append(f"Row {row_num}: unknown type '{tx_type_raw}', skipping")
                continue

            tx_date = _parse_revolut_datetime(row.get(COL_DATE, ""))
            if not tx_date:
                warnings.append(f"Row {row_num}: invalid date, skipping")
                continue

            ticker = row.get(COL_TICKER, "").strip()

            asset_id = None
            asset_required = tx_type in [
                TransactionType.BUY,
                TransactionType.SELL,
                TransactionType.DIVIDEND,
            ]
            asset_optional = tx_type in [TransactionType.FEE, TransactionType.TAX]

            if asset_required or (asset_optional and ticker):
                if not ticker:
                    warnings.append(f"Row {row_num}: {tx_type.value} requires asset, skipping")
                    continue

                if ticker in asset_to_fake_id:
                    asset_id = asset_to_fake_id[ticker]
                else:
                    asset_id = next_fake_id
                    asset_to_fake_id[ticker] = asset_id

                    extracted_assets[asset_id] = {
                        "extracted_symbol": ticker,
                        "extracted_isin": None,
                        "extracted_name": None,
                    }

                    next_fake_id -= 1

            amount, amount_currency = _parse_revolut_amount(row.get(COL_TOTAL, ""))
            currency = row.get(COL_CURRENCY, "").strip().upper() or amount_currency

            quantity = _parse_revolut_quantity(row.get(COL_QUANTITY, ""))
            if quantity is None:
                quantity = Decimal("0")

            if tx_type == TransactionType.SELL and quantity > 0:
                quantity = -quantity
            if tx_type == TransactionType.BUY and amount and amount > 0:
                amount = -amount

            self._create_transaction(
                row_num=row_num,
                transactions=transactions,
                validation_issues=validation_issues,
                context=f"{tx_type_raw}: {ticker}" if ticker else tx_type_raw,
                broker_id=broker_id,
                asset_id=asset_id,
                type=tx_type,
                date=tx_date,
                quantity=quantity,
                cash=Currency(code=currency, amount=amount) if amount else None,
                description=f"{tx_type_raw}: {ticker}" if ticker else tx_type_raw,
                tags=["import", "revolut"],
            )

        if not transactions:
            warnings.append("No valid transactions found in file")

        # Convert raw dict to BRIMExtractedAssetInfo
        extracted_assets_typed: Dict[int, BRIMExtractedAssetInfo] = {
            fake_id: BRIMExtractedAssetInfo(
                extracted_symbol=info.get("extracted_symbol"),
                extracted_isin=info.get("extracted_isin"),
                extracted_name=info.get("extracted_name"),
            )
            for fake_id, info in extracted_assets.items()
        }

        logger.info(
            "Revolut file parsed",
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

    def _parse_crypto(self, reader: csv.DictReader, broker_id: int) -> BRIMParseOutput:  # noqa: C901 — flat row loop: validation guards and per-type sign rules, no nested logic
        """Parse Revolut Crypto rows."""
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE
        row_num = 1

        for row in reader:
            row_num += 1

            tx_type_raw = row.get(COL_TYPE, "").strip()
            tx_type_key = tx_type_raw.lower()
            if not tx_type_key:
                continue

            tx_type = CRYPTO_TYPE_MAPPINGS.get(tx_type_key)
            if tx_type is None:
                warnings.append(f"Row {row_num}: unsupported crypto type '{tx_type_raw}', skipping")
                continue

            tx_date = _parse_revolut_crypto_datetime(row.get(COL_DATE, ""))
            if not tx_date:
                warnings.append(f"Row {row_num}: invalid date, skipping")
                continue

            symbol = row.get(COL_SYMBOL, "").strip().upper()
            if not symbol:
                warnings.append(f"Row {row_num}: {tx_type.value} requires symbol, skipping")
                continue

            quantity = _parse_revolut_quantity(row.get(COL_QUANTITY, "")) or Decimal("0")
            amount, value_currency = _parse_revolut_money_with_currency(row.get(COL_VALUE, ""))
            _price, price_currency = _parse_revolut_money_with_currency(row.get(COL_PRICE, ""))
            currency = value_currency or price_currency
            if amount is None or not currency:
                warnings.append(f"Row {row_num}: invalid cash value, skipping")
                continue

            if tx_type == TransactionType.BUY:
                quantity = abs(quantity)
                amount = -abs(amount)
            elif tx_type == TransactionType.SELL:
                quantity = -abs(quantity)
                amount = abs(amount)

            if symbol in asset_to_fake_id:
                asset_id = asset_to_fake_id[symbol]
            else:
                asset_id = next_fake_id
                asset_to_fake_id[symbol] = asset_id
                extracted_assets[asset_id] = {
                    "extracted_symbol": symbol,
                    "extracted_isin": None,
                    "extracted_name": None,
                }
                next_fake_id -= 1

            description = f"{tx_type_key}: {symbol}"
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
                tags=["import", "revolut"],
            )

            fee_amount, fee_currency = _parse_revolut_money_with_currency(row.get(COL_FEES, ""))
            if fee_amount and fee_amount != 0:
                self._create_transaction(
                    row_num=row_num,
                    transactions=transactions,
                    validation_issues=validation_issues,
                    context=f"fee: {symbol}",
                    broker_id=broker_id,
                    asset_id=None,
                    type=TransactionType.FEE,
                    date=tx_date,
                    quantity=Decimal("0"),
                    cash=Currency(code=fee_currency or currency, amount=-abs(fee_amount)),
                    description=f"fee: {symbol}",
                    tags=["import", "revolut"],
                )

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
            "Revolut crypto file parsed",
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
        return "/mkdocs/user/transactions/import/revolut/"

    @property
    def test_file_pattern(self) -> Optional[str]:
        """Filename pattern for auto-detection tests."""
        return "revolut"

    @property
    def test_file_patterns(self) -> List[str]:
        """Filename patterns for all Revolut export variants."""
        return ["revolut-invest", "revolut-crypto"]
