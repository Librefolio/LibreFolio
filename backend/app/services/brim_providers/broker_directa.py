"""
Directa Broker Report Import Plugin.

This plugin parses CSV exports from Directa SIM (Italian broker).

**File Format Characteristics:**
- First 9 lines: metadata (account info, extraction date, filters)
- Line 10: column headers
- Line 11+: data rows
- Separator: comma
- Encoding: UTF-8 BOM
- Italian column names and transaction types

**Supported Transaction Types:**
- Acquisto → BUY
- Vendita → SELL
- Provento etf/azioni, Dividendi, Coupon → DIVIDEND
- Cedola → INTEREST
- Conferimento → DEPOSIT
- Prelievo → WITHDRAWAL
- Rit.provento, Ritenuta, Tobin tax → TAX
- Commissioni → FEE

**Columns:**
- Data operazione: Transaction date (DD-MM-YYYY)
- Tipo operazione: Transaction type
- Ticker: Asset symbol
- Isin: Asset ISIN
- Descrizione: Description
- Quantità: Quantity
- Importo euro: Amount in EUR
- Divisa: Currency (usually EUR)
"""
from __future__ import annotations

import csv
from datetime import date as date_type, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Tuple, Dict, Optional

import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMExtractedAssetInfo
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMProvider, BRIMParseError
from backend.app.services.provider_registry import register_provider, BRIMProviderRegistry

logger = structlog.get_logger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

# Number of header lines to skip before data
HEADER_LINES_TO_SKIP = 9

# Directa uses DD-MM-YYYY format
DATE_FORMAT = "%d-%m-%Y"

# Column indices (0-based) after header row
COL_DATE = 0  # Data operazione
COL_VALUTA_DATE = 1  # Data valuta
COL_TYPE = 2  # Tipo operazione
COL_TICKER = 3  # Ticker
COL_ISIN = 4  # Isin
COL_PROTOCOL = 5  # Protocollo
COL_DESC = 6  # Descrizione
COL_QUANTITY = 7  # Quantità
COL_AMOUNT_EUR = 8  # Importo euro
COL_AMOUNT_DIV = 9  # Importo Divisa
COL_CURRENCY = 10  # Divisa

# Type mapping (lowercase search)
TYPE_MAPPINGS: Dict[str, TransactionType] = {
    # BUY
    "acquisto": TransactionType.BUY,

    # SELL
    "vendita": TransactionType.SELL,

    # DIVIDEND
    "provento": TransactionType.DIVIDEND,
    "dividendi": TransactionType.DIVIDEND,
    "dividendo": TransactionType.DIVIDEND,
    "coupon": TransactionType.DIVIDEND,

    # INTEREST (bond coupons)
    "cedola": TransactionType.INTEREST,

    # DEPOSIT
    "conferimento": TransactionType.DEPOSIT,
    "bonifico": TransactionType.DEPOSIT,

    # WITHDRAWAL
    "prelievo": TransactionType.WITHDRAWAL,

    # TAX
    "rit.": TransactionType.TAX,
    "ritenuta": TransactionType.TAX,
    "tobin": TransactionType.TAX,

    # FEE
    "commissioni": TransactionType.FEE,
    "commissione": TransactionType.FEE,
    }


def _parse_directa_date(value: str) -> Optional[date_type]:
    """Parse Directa date format (DD-MM-YYYY)."""
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except ValueError:
        return None


def _parse_directa_number(value: str) -> Optional[Decimal]:
    """Parse Directa number (Italian format, may be negative)."""
    value = value.strip()
    if not value:
        return None

    # Replace comma with dot for decimal separator
    value = value.replace(",", ".")

    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _map_transaction_type(tipo: str) -> Optional[TransactionType]:
    """Map Directa transaction type to TransactionType enum."""
    tipo_lower = tipo.lower().strip()

    # Check each mapping keyword
    for keyword, tx_type in TYPE_MAPPINGS.items():
        if keyword in tipo_lower:
            return tx_type

    return None


# =============================================================================
# PLUGIN IMPLEMENTATION
# =============================================================================

@register_provider(BRIMProviderRegistry)
class DirectaBrokerProvider(BRIMProvider):
    """
    Directa SIM (Italian broker) CSV export import plugin.

    Handles the specific format of Directa's CSV exports including:
    - 9-line header metadata
    - Italian column names and transaction types
    - DD-MM-YYYY date format
    - EUR as primary currency
    """

    @property
    def provider_code(self) -> str:
        return "broker_directa"

    @property
    def provider_name(self) -> str:
        return "Directa SIM"

    @property
    def description(self) -> str:
        return (
            "Import transactions from Directa SIM CSV export. "
            "Supports all Italian transaction types including ETF dividends, "
            "bond coupons, taxes, and trading operations."
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
        """Directa SIM logo."""
        return "https://www.directa.it/favicon.ico"

    def can_parse(self, file_path: Path) -> bool:
        """
        Detect Directa format by checking for distinctive patterns.

        Checks:
        - File has .csv extension
        - Contains "Data operazione" and "Tipo operazione" in first 15 lines
        - Contains "Conto :" metadata marker
        """
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=15)
            content_lower = content.lower()

            # Check for Directa-specific patterns
            required_patterns = [
                "data operazione",
                "tipo operazione",
                "isin",
                "importo euro"
                ]

            # Must have all required patterns
            if not all(p in content_lower for p in required_patterns):
                return False

            # Additional check: should have "Conto :" metadata
            if "conto :" not in content_lower and "conto:" not in content_lower:
                return False

            return True

        except Exception:
            return False

    def parse(
        self,
        file_path: Path,
        broker_id: int
        ) -> Tuple[List[TXCreateItem], List[str], Dict[int, BRIMExtractedAssetInfo]]:
        """
        Parse Directa CSV export file.

        Returns:
            Tuple of (transactions, warnings, extracted_assets)
        """
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        extracted_assets_raw: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                # Skip header lines
                for _ in range(HEADER_LINES_TO_SKIP):
                    f.readline()

                reader = csv.reader(f)

                # Read column header row
                header = next(reader, None)
                if not header:
                    raise BRIMParseError("File has no data after header")

                row_num = HEADER_LINES_TO_SKIP + 1  # For error reporting

                for row in reader:
                    row_num += 1

                    # Skip empty rows
                    if not row or all(not cell.strip() for cell in row):
                        continue

                    # Need at least basic columns
                    if len(row) < COL_AMOUNT_EUR + 1:
                        warnings.append(f"Row {row_num}: insufficient columns, skipping")
                        continue

                    # Parse date
                    tx_date = _parse_directa_date(row[COL_DATE])
                    if not tx_date:
                        warnings.append(f"Row {row_num}: invalid date '{row[COL_DATE]}', skipping")
                        continue

                    # Parse type
                    tipo_raw = row[COL_TYPE].strip()
                    if not tipo_raw:
                        warnings.append(f"Row {row_num}: empty transaction type, skipping")
                        continue

                    tx_type = _map_transaction_type(tipo_raw)
                    if not tx_type:
                        warnings.append(f"Row {row_num}: unknown type '{tipo_raw}', skipping")
                        continue

                    # Parse amount
                    amount = _parse_directa_number(row[COL_AMOUNT_EUR])
                    if amount is None:
                        amount = Decimal("0")

                    # Parse quantity
                    quantity = _parse_directa_number(row[COL_QUANTITY])
                    if quantity is None:
                        quantity = Decimal("0")

                    # Get currency (default EUR)
                    currency = row[COL_CURRENCY].strip() if len(row) > COL_CURRENCY else "EUR"
                    if not currency:
                        currency = "EUR"

                    # Get description
                    description = row[COL_DESC].strip() if len(row) > COL_DESC else ""

                    # Get asset info
                    ticker = row[COL_TICKER].strip() if len(row) > COL_TICKER else ""
                    isin = row[COL_ISIN].strip() if len(row) > COL_ISIN else ""

                    # Determine asset_id
                    asset_id = None

                    # Types that require an asset
                    asset_required = tx_type in [
                        TransactionType.BUY,
                        TransactionType.SELL,
                        TransactionType.DIVIDEND,
                        TransactionType.INTEREST,
                        ]

                    if asset_required:
                        # Create a unique key for this asset
                        asset_key = isin if isin else ticker if ticker else f"UNKNOWN_ROW_{row_num}"

                        if asset_key in asset_to_fake_id:
                            asset_id = asset_to_fake_id[asset_key]
                        else:
                            asset_id = next_fake_id
                            asset_to_fake_id[asset_key] = asset_id

                            # Store extracted info
                            extracted_assets_raw[asset_id] = {
                                "extracted_symbol": ticker if ticker else None,
                                "extracted_isin": isin if isin else None,
                                "extracted_name": description if description else None,
                                }

                            next_fake_id -= 1

                    # Adjust quantity sign for SELL
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
                            description=f"{tipo_raw}: {description}" if description else tipo_raw,
                            tags=["import", "directa"],
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

        # Convert raw dict to BRIMExtractedAssetInfo
        extracted_assets_typed: Dict[int, BRIMExtractedAssetInfo] = {
            fake_id: BRIMExtractedAssetInfo(
                extracted_symbol=info.get("extracted_symbol"),
                extracted_isin=info.get("extracted_isin"),
                extracted_name=info.get("extracted_name"),
                )
            for fake_id, info in extracted_assets_raw.items()
            }

        logger.info(
            "Directa file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets_typed)
            )

        return transactions, warnings, extracted_assets_typed

    @property
    def test_file_pattern(self) -> Optional[str]:
        """Filename pattern for auto-detection tests."""
        return "directa"
