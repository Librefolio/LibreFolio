"""
Directa Broker Report Import Plugin.

This plugin parses **CSV and XLSX** exports from Directa SIM (Italian broker).
Both variants carry the *same* logical layout (identical rows and column order);
only the reading differs, so a single parse path handles both via ``_brim_io``.

**File Format Characteristics:**
- First rows: metadata (account info, extraction date, filters)
- Header row: column labels ("Data operazione" … "Divisa")
- Following rows: data
- CSV separator: comma/semicolon (auto-detected); Encoding: UTF-8 BOM
- XLSX: first non-empty worksheet, native cell types (numbers/dates)
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

from datetime import date as date_type
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMExtractedAssetInfo, BRIMParseOutput, BRIMValidationIssue
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.brim_providers import _brim_io as io
from backend.app.services.provider_registry import BRIMProviderRegistry, register_provider

logger = structlog.get_logger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

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
    # TAX (must be before cedola/provento to catch "Rit.cedola", "Rit.provento")
    "rit.": TransactionType.TAX,
    "ritenuta": TransactionType.TAX,
    "tobin": TransactionType.TAX,
    "bollo": TransactionType.TAX,  # Bollo portafoglio titoli (stamp duty)
    "imposta": TransactionType.TAX,  # generic tax keyword
    # INTEREST (bond coupons)
    "cedola": TransactionType.INTEREST,
    # DEPOSIT
    "conferimento": TransactionType.DEPOSIT,
    "bonifico": TransactionType.DEPOSIT,
    # WITHDRAWAL
    "prelievo": TransactionType.WITHDRAWAL,
    # FEE
    "commissioni": TransactionType.FEE,
    "commissione": TransactionType.FEE,
}


def _parse_directa_date(value: Any) -> Optional[date_type]:
    """Parse a Directa date (DD-MM-YYYY) from CSV text or a native XLSX date."""
    return io.to_date(value, formats=(DATE_FORMAT,))


def _parse_directa_number(value: Any) -> Optional[Decimal]:
    """Parse a Directa number from CSV text or a native XLSX ``int``/``float``.

    Directa CSV exports are inconsistent about the decimal separator (some use
    ``,``, others ``.``) but never carry a thousands separator, so a plain
    comma->dot normalisation parses both variants correctly. XLSX cells already
    arrive as native numbers and are taken verbatim.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    s = str(value).strip()
    if not s:
        return None
    # Directa never uses thousands separators — a bare comma->dot swap is safe.
    s = s.replace(",", ".")
    try:
        return Decimal(s)
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
    Directa SIM (Italian broker) CSV/XLSX export import plugin.

    Handles the specific format of Directa's exports (both CSV and XLSX, which
    share the same layout) including:
    - metadata header rows followed by a labelled column-header row
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
        return "Import transactions from Directa SIM export (CSV or XLSX). " "Supports all Italian transaction types including ETF dividends, " "bond coupons, taxes, and trading operations."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv", ".xlsx"]

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
        Detect Directa format (CSV or XLSX) by its distinctive header labels.

        Checks:
        - File has a ``.csv`` or ``.xlsx`` extension
        - Header labels "Data operazione"/"Tipo operazione"/"Isin"/"Importo euro"
          appear in the first rows
        - The "Conto :" account-metadata marker is present
        """
        if file_path.suffix.lower() not in (".csv", ".xlsx"):
            return False

        try:
            rows = io.read_rows(file_path)
        except Exception:
            return False

        blob = " \n ".join(io.cell_str(c).lower() for row in rows[:20] for c in row)

        # Must have all the distinctive column-header labels …
        required_patterns = ["data operazione", "tipo operazione", "isin", "importo euro"]
        if not all(p in blob for p in required_patterns):
            return False

        # … plus the "Conto :" account-metadata marker.
        return "conto :" in blob or "conto:" in blob

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """
        Parse a Directa CSV or XLSX export file.

        Returns:
            Tuple of (transactions, warnings, extracted_assets)
        """
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets_raw: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        # Read either variant (CSV or XLSX) into a uniform list[list[cell]]; the
        # delimiter (CSV) and worksheet (XLSX) are resolved inside _brim_io.
        try:
            rows = io.read_rows(file_path)
        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}") from None
        except Exception as e:
            raise BRIMParseError(f"Error reading file: {e}") from e

        # Both variants share the same layout; locate the labelled header row
        # dynamically (robust to metadata line-count changes) — the data columns
        # then sit at the fixed COL_* offsets below in CSV and XLSX alike.
        header_idx = io.find_header_row(rows, ["Data operazione", "Tipo operazione", "Isin"])
        if header_idx is None:
            raise BRIMParseError("Directa header row not found (expected 'Data operazione'/'Tipo operazione'/'Isin')")

        for offset, row in enumerate(rows[header_idx + 1 :]):
            row_num = header_idx + 2 + offset  # 1-based line number for messages

            # Skip empty rows
            if io.is_blank_row(row):
                continue

            # Need at least the basic columns up to "Importo euro"
            if len(row) < COL_AMOUNT_EUR + 1:
                warnings.append(f"Riga {row_num}: colonne insufficienti, saltata")
                continue

            # Parse date
            tx_date = _parse_directa_date(row[COL_DATE])
            if not tx_date:
                warnings.append(f"Riga {row_num}: data '{io.cell_str(row[COL_DATE])}' non valida, saltata")
                continue

            # Parse type
            tipo_raw = io.cell_str(row[COL_TYPE])
            if not tipo_raw:
                warnings.append(f"Riga {row_num}: tipo operazione mancante, saltata")
                continue

            tx_type = _map_transaction_type(tipo_raw)
            if not tx_type:
                warnings.append(f"Riga {row_num}: tipo '{tipo_raw}' sconosciuto, saltata")
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
            currency = io.cell_str(row[COL_CURRENCY]) if len(row) > COL_CURRENCY else "EUR"
            if not currency:
                currency = "EUR"

            # Get description
            description = io.cell_str(row[COL_DESC]) if len(row) > COL_DESC else ""

            # Get asset info
            ticker = io.cell_str(row[COL_TICKER]) if len(row) > COL_TICKER else ""
            isin = io.cell_str(row[COL_ISIN]) if len(row) > COL_ISIN else ""

            # Determine asset_id
            asset_id = None

            # Types that require an asset
            asset_required = tx_type in [
                TransactionType.BUY,
                TransactionType.SELL,
                TransactionType.DIVIDEND,
                TransactionType.INTEREST,
            ]
            # FEE/TAX rows sometimes carry the same ticker/ISIN as the
            # position they relate to (e.g. "Rit.cedola obb." withholding
            # tax on a bond coupon) — link when resolvable, but never
            # force a placeholder asset for genuinely account-level rows
            # (e.g. "Bollo" stamp duty, generic commissions).
            asset_optional = tx_type in [TransactionType.FEE, TransactionType.TAX]

            if asset_required or (asset_optional and (isin or ticker)):
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
            # Directa exports dividend/interest/coupon as negative amounts (debit view);
            # project rules require cash > 0 for these types.
            if tx_type in (TransactionType.DIVIDEND, TransactionType.INTEREST) and amount is not None and amount < 0:
                amount = -amount

            # Create transaction (parent handles validation errors)
            self._create_transaction(
                row_num=row_num,
                transactions=transactions,
                validation_issues=validation_issues,
                context=f"{tipo_raw}: {description}" if description else tipo_raw,
                broker_id=broker_id,
                asset_id=asset_id,
                type=tx_type,
                date=tx_date,
                quantity=quantity,
                cash=Currency(code=currency, amount=amount) if amount else None,
                description=f"{tipo_raw}: {description}" if description else tipo_raw,
                tags=["import", "directa"],
            )

        if not transactions:
            warnings.append("Nessuna transazione valida trovata nel file")

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
            asset_count=len(extracted_assets_typed),
        )

        return BRIMParseOutput(transactions=transactions, warnings=warnings, validation_issues=validation_issues, extracted_assets=extracted_assets_typed)

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/directa/"

    @property
    def test_file_pattern(self) -> Optional[str]:
        """Filename pattern for auto-detection tests."""
        return "directa"
