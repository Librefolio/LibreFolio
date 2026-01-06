"""
DEGIRO Broker Report Import Plugin.

This plugin parses CSV exports from DEGIRO (European broker).

**File Format Characteristics:**
- First line: column headers
- Separator: comma
- Dutch/multi-language column names
- Dutch number format (comma as decimal separator)
- Multi-currency support (EUR, USD, GBP, etc.)
- Transaction type in `Omschrijving` column

**Supported Transaction Types (multi-language):**
- Koop / Buy / Compra / Achat → BUY
- Verkoop / Sell / Venta / Vente → SELL
- Dividend / Dividende → DIVIDEND
- Dividendbelasting / Impôts sur dividende → TAX
- iDEAL Deposit / Ingreso → DEPOSIT
- Withdrawal / Prelievo → WITHDRAWAL
- Transactiekosten / Kosten / Frais / Comissões → FEE
- Valuta Creditering / Credito → FX_IN (ignored - FX conversion)
- Valuta Debitering / Levantamento → FX_OUT (ignored - FX conversion)

**Columns:**
- Datum: Date (DD-MM-YYYY)
- Tijd: Time
- Product: Asset name
- ISIN: Asset ISIN
- Omschrijving: Description (contains transaction type)
- Mutatie: Amount change (with currency column after)
- Saldo: Balance (with currency column after)
"""
from __future__ import annotations

import csv
import re
from datetime import date as date_type, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Tuple, Dict, Optional

import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMProvider, BRIMParseError
from backend.app.services.provider_registry import register_provider, BRIMProviderRegistry

logger = structlog.get_logger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

# DEGIRO uses DD-MM-YYYY format
DATE_FORMAT = "%d-%m-%Y"

# Column names (Dutch, but may vary by language)
COL_DATE = "Datum"
COL_TIME = "Tijd"
COL_PRODUCT = "Product"
COL_ISIN = "ISIN"
COL_DESCRIPTION = "Omschrijving"

# Type patterns (multi-language, lowercase)
# Pattern → (TransactionType, requires_asset)
TYPE_PATTERNS: Dict[str, Tuple[TransactionType, bool]] = {
    # BUY patterns
    r"koop \d+": (TransactionType.BUY, True),
    r"buy \d+": (TransactionType.BUY, True),
    r"compra \d+": (TransactionType.BUY, True),
    r"achat \d+": (TransactionType.BUY, True),

    # SELL patterns
    r"verkoop \d+": (TransactionType.SELL, True),
    r"sell \d+": (TransactionType.SELL, True),
    r"venta \d+": (TransactionType.SELL, True),
    r"vente \d+": (TransactionType.SELL, True),

    # DIVIDEND
    r"^dividend": (TransactionType.DIVIDEND, True),
    r"^dividende": (TransactionType.DIVIDEND, True),

    # TAX on dividends
    r"dividendbelasting": (TransactionType.TAX, True),
    r"impôts sur dividende": (TransactionType.TAX, True),
    r"dividend tax": (TransactionType.TAX, True),

    # DEPOSIT
    r"ideal deposit": (TransactionType.DEPOSIT, False),
    r"^ingreso$": (TransactionType.DEPOSIT, False),
    r"^deposit": (TransactionType.DEPOSIT, False),

    # WITHDRAWAL
    r"withdrawal": (TransactionType.WITHDRAWAL, False),
    r"prelievo": (TransactionType.WITHDRAWAL, False),

    # FEES
    r"transactiekosten": (TransactionType.FEE, True),
    r"kosten van derden": (TransactionType.FEE, True),
    r"frais": (TransactionType.FEE, True),
    r"comissões": (TransactionType.FEE, True),
    r"aansluitingskosten": (TransactionType.FEE, False),  # Connection fees
    r"connection fee": (TransactionType.FEE, False),
    }

# Patterns to skip (FX conversions, internal transfers, etc.)
SKIP_PATTERNS = [
    r"valuta creditering",
    r"valuta debitering",
    r"crédito de divisa",
    r"levantamento de divisa",
    r"fx credit",
    r"fx debit",
    r"cash sweep",
    r"overboeking",  # Internal transfer
    r"flatex",
    r"reservation",
    r"productwijziging",  # Product change
    r"stock dividend",  # Stock dividend (not cash)
    r"variation fonds",
    r"conversion fonds",
    r"corporate action",
    r"courtesy",  # DEGIRO courtesy refunds
    ]


def _parse_degiro_date(value: str) -> Optional[date_type]:
    """Parse DEGIRO date format (DD-MM-YYYY)."""
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except ValueError:
        return None


def _parse_degiro_number(value: str) -> Optional[Decimal]:
    """Parse DEGIRO number (Dutch format: comma as decimal separator)."""
    value = value.strip()
    if not value:
        return None

    # Remove currency symbols and whitespace
    value = re.sub(r'[€$£¥]', '', value).strip()

    # Handle Dutch format: 1.234,56 → 1234.56
    # If both . and , present and comma is after dot, it's Dutch format
    if '.' in value and ',' in value:
        if value.rfind(',') > value.rfind('.'):
            # Dutch: thousands separator is ., decimal is ,
            value = value.replace('.', '').replace(',', '.')
        else:
            # US: thousands separator is ,, decimal is .
            value = value.replace(',', '')
    elif ',' in value:
        # Only comma - could be decimal separator or thousands
        parts = value.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Likely decimal separator
            value = value.replace(',', '.')
        else:
            # Might be thousands separator
            value = value.replace(',', '')

    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _detect_transaction_type(description: str) -> Tuple[Optional[TransactionType], bool]:
    """
    Detect transaction type from DEGIRO description.

    Returns:
        Tuple of (TransactionType, requires_asset) or (None, False) if not matched
    """
    desc_lower = description.lower().strip()

    # Check skip patterns first
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, desc_lower):
            return None, False

    # Check type patterns
    for pattern, (tx_type, requires_asset) in TYPE_PATTERNS.items():
        if re.search(pattern, desc_lower):
            return tx_type, requires_asset

    return None, False


def _extract_quantity_from_description(description: str) -> Decimal:
    """Extract quantity from description like 'Koop 5 @ 10.50 EUR'."""
    # Pattern 1: (Buy|Sell|Koop|Verkoop|etc.) <quantity> @ <price> <currency>
    # Pattern 2: (Compra|Venta) <quantity> <PRODUCT>@<price> (with space before @)

    # First try standard pattern
    match = re.search(r'(?:koop|verkoop|buy|sell|compra|venta|achat|vente)\s+(\d+(?:[.,]\d+)?)\s*@',
                      description, re.IGNORECASE)
    if match:
        qty_str = match.group(1).replace(',', '.')
        try:
            return Decimal(qty_str)
        except InvalidOperation:
            pass

    # Try pattern with product name between quantity and @
    # e.g., "Compra 6 ISHARES MSCI WOR A@49,785 EUR"
    match = re.search(r'(?:koop|verkoop|buy|sell|compra|venta|achat|vente)\s+(\d+(?:[.,]\d+)?)\s+[^@]+@',
                      description, re.IGNORECASE)
    if match:
        qty_str = match.group(1).replace(',', '.')
        try:
            return Decimal(qty_str)
        except InvalidOperation:
            pass

    return Decimal("0")


# =============================================================================
# PLUGIN IMPLEMENTATION
# =============================================================================

@register_provider(BRIMProviderRegistry)
class DegiroBrokerProvider(BRIMProvider):
    """
    DEGIRO (European broker) CSV export import plugin.

    Handles the specific format of DEGIRO's CSV exports including:
    - Multi-language descriptions (Dutch, English, French, Spanish, Portuguese, German)
    - DD-MM-YYYY date format
    - Dutch number format (comma as decimal)
    - Multi-currency support
    """

    @property
    def provider_code(self) -> str:
        return "broker_degiro"

    @property
    def provider_name(self) -> str:
        return "DEGIRO"

    @property
    def description(self) -> str:
        return (
            "Import transactions from DEGIRO CSV export. "
            "Supports multi-language descriptions (Dutch, English, French, etc.) "
            "and multi-currency transactions."
        )

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        """High priority - specific broker plugin."""
        return 100

    @property
    def icon_url(self) -> str:
        """DEGIRO logo."""
        return "https://www.degiro.com/favicon.ico"

    def can_parse(self, file_path: Path) -> bool:
        """
        Detect DEGIRO format by checking for distinctive header columns.
        """
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=5)
            content_lower = content.lower()

            # DEGIRO specific: must have these columns
            required_columns = ["datum", "tijd", "isin", "omschrijving"]

            # Check first line contains required columns
            first_line = content.split('\n')[0].lower() if content else ""

            return all(col in first_line for col in required_columns)

        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> Tuple[List[TXCreateItem], List[str], Dict[int, Dict]]:
        """
        Parse DEGIRO CSV export file.

        Returns:
            Tuple of (transactions, warnings, extracted_assets)
        """
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        extracted_assets: Dict[int, Dict] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)

                row_num = 1  # Header is row 1

                for row in reader:
                    row_num += 1

                    # Get description
                    description = row.get(COL_DESCRIPTION, "").strip()
                    if not description:
                        continue

                    # Detect transaction type
                    tx_type, requires_asset = _detect_transaction_type(description)
                    if tx_type is None:
                        # Skip this row (FX conversion, internal transfer, etc.)
                        continue

                    # Parse date
                    tx_date = _parse_degiro_date(row.get(COL_DATE, ""))
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date, skipping")
                        continue

                    # Get asset info
                    product = row.get(COL_PRODUCT, "").strip()
                    isin = row.get(COL_ISIN, "").strip()

                    # Determine asset_id
                    asset_id = None

                    if requires_asset:
                        if not isin and not product:
                            warnings.append(f"Row {row_num}: {tx_type.value} requires asset but none found, skipping")
                            continue

                        asset_key = isin if isin else product

                        if asset_key in asset_to_fake_id:
                            asset_id = asset_to_fake_id[asset_key]
                        else:
                            asset_id = next_fake_id
                            asset_to_fake_id[asset_key] = asset_id

                            extracted_assets[asset_id] = {
                                "extracted_symbol": None,  # DEGIRO doesn't provide symbols
                                "extracted_isin": isin if isin else None,
                                "extracted_name": product if product else None,
                                }

                            next_fake_id -= 1

                    # Find the amount columns
                    # DEGIRO has: ...,FX,Mutatie,,Saldo,,...
                    # The actual values are in columns after Mutatie and Saldo headers
                    amount = None
                    currency = "EUR"  # Default

                    # Try to find Mutatie column and its currency
                    for key, value in row.items():
                        if key and "mutatie" in key.lower():
                            amount = _parse_degiro_number(value)
                        # Currency is often in an empty-header column after Mutatie
                        if not key or key == "":
                            # This might be a currency column
                            val = value.strip().upper()
                            if val in ["EUR", "USD", "GBP", "CHF", "JPY", "CAD", "AUD"]:
                                if amount is not None:
                                    currency = val

                    # If we couldn't find amount via Mutatie, try other columns
                    if amount is None:
                        for key, value in row.items():
                            parsed = _parse_degiro_number(value)
                            if parsed is not None and parsed != Decimal("0"):
                                amount = parsed
                                break

                    if amount is None:
                        amount = Decimal("0")

                    # Extract quantity from description for BUY/SELL
                    quantity = Decimal("0")
                    if tx_type in [TransactionType.BUY, TransactionType.SELL]:
                        quantity = _extract_quantity_from_description(description)
                        if quantity == 0:
                            warnings.append(f"Row {row_num}: could not extract quantity from '{description}'")

                    # Adjust signs
                    if tx_type == TransactionType.SELL and quantity > 0:
                        quantity = -quantity

                    # Create transaction
                    try:
                        tx = TXCreateItem(
                            broker_id=broker_id,
                            asset_id=asset_id,
                            type=tx_type,
                            date=tx_date,
                            quantity=quantity,
                            cash=Currency(code=currency, amount=amount) if amount else None,
                            description=description,
                            tags=["import", "degiro"],
                            )
                        transactions.append(tx)

                    except Exception as e:
                        warnings.append(f"Row {row_num}: error creating transaction: {e}")
                        continue

        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}")
        except Exception as e:
            raise BRIMParseError(f"Error parsing file: {e}")

        if not transactions:
            raise BRIMParseError("No valid transactions found in file")

        logger.info(
            "DEGIRO file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets)
            )

        return transactions, warnings, extracted_assets
