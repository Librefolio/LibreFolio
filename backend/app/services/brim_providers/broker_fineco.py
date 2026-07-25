"""
Fineco Broker Report Import Plugin.

This plugin parses CSV exports from FinecoBank (Italian bank/broker),
specifically the "Movimenti Dossier Titoli" (securities dossier movements) report.

**Import philosophy (verbatim / no forex):**
This plugin is a faithful transcriber, not a re-calculator. Numbers are imported
exactly as they appear in the report. The currency of every monetary figure in a
row is taken from that row's ``Divisa`` column. The forex subsystem is never
involved and the report's ``Cambio`` (exchange rate) column is deliberately
ignored — no conversion of any kind is performed.

**File Format Characteristics:**
- A few metadata lines at the top (``Dossier:``, ``Intestatario:``, ``Titoli e operazioni``)
- A header row whose first cell is ``Operazione`` (located dynamically)
- Data rows below the header
- Separator: auto-detected via ``detect_csv_delimiter`` (never hardcoded)
- Italian column names and transaction descriptions

**Two export layout variants (auto-detected):**
- Variant A — 11 columns, no commission columns.
- Variant B — 15 columns, with 4 trailing commission columns.

**Columns (0-based):**
- 0  Operazione: Trade date (DD/MM/YYYY)
- 1  Data valuta: Value/settlement date (DD/MM/YYYY) — used as transaction date
- 2  Descrizione: Operation description (drives type mapping)
- 3  Titolo: Asset name
- 4  Isin: Asset ISIN
- 5  Segno: A = buy, V = sell, blank = cash payout
- 6  Quantita: Quantity
- 7  Divisa: Currency of the row's monetary figures
- 8  Prezzo: Price (in Divisa)
- 9  Cambio: Exchange rate — IGNORED
- 10 Controvalore: Settled cash figure (imported verbatim, tagged with Divisa)
- 11 Commissioni Fondi Sw/Ingr/Uscita       (Variant B only)
- 12 Commissioni Fondi Banca Corrispondente  (Variant B only)
- 13 Spese Fondi Sgr                          (Variant B only)
- 14 Commissioni amministrato                 (Variant B only)

**Supported Transaction Types (from Descrizione, using Segno for trades):**
- Compravendita titoli + A → BUY
- Compravendita titoli + V → SELL
- Dividendo → DIVIDEND
- Stacco Cedole → INTEREST (bond coupon)
- Rimborso → SELL (redemption / maturity)
- Aumento capitale → ADJUSTMENT (quantity change, no cash)
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

# =============================================================================
# CONSTANTS
# =============================================================================

# Fineco uses DD/MM/YYYY format
DATE_FORMAT = "%d/%m/%Y"

# Column indices (0-based), shared by both layout variants
COL_TRADE_DATE = 0  # Operazione
COL_VALUE_DATE = 1  # Data valuta
COL_DESC = 2  # Descrizione
COL_TITOLO = 3  # Titolo
COL_ISIN = 4  # Isin
COL_SEGNO = 5  # Segno (A/V)
COL_QUANTITY = 6  # Quantita
COL_CURRENCY = 7  # Divisa
COL_PRICE = 8  # Prezzo
COL_FX = 9  # Cambio (IGNORED)
COL_CONTROVALORE = 10  # Controvalore

# Commission columns (Variant B only)
COMMISSION_COLS = [11, 12, 13, 14]

# Minimum columns required for a usable data row (up to Controvalore)
MIN_COLUMNS = COL_CONTROVALORE + 1

# Fees are always charged/settled in EUR by Fineco; the per-row Divisa governs
# the trade figures, while commission columns are account-currency (EUR).
FEE_CURRENCY = "EUR"


def _parse_fineco_date(value: str) -> Optional[date_type]:
    """Parse Fineco date format (DD/MM/YYYY)."""
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except ValueError:
        return None


def _parse_fineco_number(value: str) -> Optional[Decimal]:
    """Parse a Fineco number.

    Tolerates both dot-decimal (e.g. ``105.71``) and Italian comma-decimal /
    thousands-separator formats (e.g. ``1.990,00``).
    """
    value = value.strip()
    if not value:
        return None

    # Italian format: comma is the decimal separator, dot is the thousands sep.
    if "," in value:
        value = value.replace(".", "").replace(",", ".")

    try:
        return Decimal(value)
    except InvalidOperation:
        return None


# =============================================================================
# PLUGIN IMPLEMENTATION
# =============================================================================


@register_provider(BRIMProviderRegistry)
class FinecoBrokerProvider(BRIMProvider):
    """
    FinecoBank (Italian bank/broker) CSV export import plugin.

    Handles the "Movimenti Dossier Titoli" report in both layout variants
    (with and without commission columns), following the verbatim / no-forex
    import philosophy documented at module level.
    """

    @property
    def provider_code(self) -> str:
        return "broker_fineco"

    @property
    def provider_name(self) -> str:
        return "Fineco"

    @property
    def description(self) -> str:
        return (
            "Import transactions from FinecoBank 'Movimenti Dossier Titoli' CSV export. "
            "Supports both export layouts (with and without commissions), buys, sells, "
            "dividends, bond coupons, redemptions and capital increases. Amounts are "
            "imported verbatim in the currency reported by the broker (no FX conversion)."
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
        """FinecoBank logo."""
        return "https://finecobank.com/favicon.ico"

    def can_parse(self, file_path: Path) -> bool:
        """
        Detect Fineco format by checking for distinctive patterns.

        Checks:
        - File has .csv extension
        - Contains the "Dossier" metadata marker
        - Contains the distinctive header columns (Operazione, Data valuta,
          Isin, Controvalore) within the first lines
        """
        if file_path.suffix.lower() != ".csv":
            return False

        try:
            content = self._read_file_head(file_path, num_lines=15)
            content_lower = content.lower()

            required_patterns = ["operazione", "data valuta", "isin", "controvalore"]
            if not all(p in content_lower for p in required_patterns):
                return False

            # Fineco-specific metadata marker at the top of the report
            if "dossier" not in content_lower:
                return False

            return True

        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """
        Parse a Fineco CSV export file.

        Returns:
            BRIMParseOutput with transactions, warnings, validation issues and
            extracted assets (fake IDs).
        """
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets_raw: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        detected_delim = self.detect_csv_delimiter(file_path)

        def _resolve_asset_id(isin: str, ticker: str, name: str, row_num: int) -> int:
            """Assign (or reuse) a fake asset ID keyed by ISIN/ticker/name."""
            nonlocal next_fake_id
            asset_key = isin if isin else ticker if ticker else f"UNKNOWN_ROW_{row_num}"
            if asset_key in asset_to_fake_id:
                return asset_to_fake_id[asset_key]
            fake_id = next_fake_id
            asset_to_fake_id[asset_key] = fake_id
            extracted_assets_raw[fake_id] = {
                "extracted_symbol": ticker if ticker else None,
                "extracted_isin": isin if isin else None,
                "extracted_name": name if name else None,
            }
            next_fake_id -= 1
            return fake_id

        try:
            with open(file_path, encoding="utf-8-sig") as f:
                reader = csv.reader(f, delimiter=detected_delim)
                rows = list(reader)

            # Locate the header row dynamically (first cell == "Operazione").
            # This tolerates a variable number of metadata lines and both variants.
            header_idx = None
            for idx, row in enumerate(rows):
                if row and row[0].strip().lower() == "operazione":
                    header_idx = idx
                    break

            if header_idx is None:
                raise BRIMParseError("Could not locate the 'Operazione' header row")

            has_commissions = len(rows[header_idx]) > COL_CONTROVALORE + 1

            for offset, row in enumerate(rows[header_idx + 1 :]):
                row_num = header_idx + 2 + offset  # 1-based row number for reporting

                # Skip empty rows
                if not row or all(not cell.strip() for cell in row):
                    continue

                if len(row) < MIN_COLUMNS:
                    warnings.append(f"Row {row_num}: insufficient columns, skipping")
                    continue

                # Settlement date = value date (Data valuta); fall back to trade date
                tx_date = _parse_fineco_date(row[COL_VALUE_DATE]) or _parse_fineco_date(row[COL_TRADE_DATE])
                if not tx_date:
                    warnings.append(f"Row {row_num}: invalid date, skipping")
                    continue

                descrizione = row[COL_DESC].strip()
                if not descrizione:
                    warnings.append(f"Row {row_num}: empty description, skipping")
                    continue

                segno = row[COL_SEGNO].strip().upper()

                tx_type = self._map_transaction_type(descrizione, segno)
                if tx_type is None:
                    warnings.append(f"Row {row_num}: unknown operation '{descrizione}', skipping")
                    continue

                # Verbatim currency from the Divisa column (no FX involvement)
                currency = row[COL_CURRENCY].strip() or "EUR"

                quantity = _parse_fineco_number(row[COL_QUANTITY]) or Decimal("0")
                controvalore = _parse_fineco_number(row[COL_CONTROVALORE]) or Decimal("0")

                ticker = ""  # Fineco reports do not include a ticker column
                isin = row[COL_ISIN].strip()
                name = row[COL_TITOLO].strip()

                # Apply per-type sign conventions (verbatim magnitude from source)
                quantity, cash = self._apply_sign_rules(tx_type, quantity, controvalore, currency)

                # Resolve asset link for asset-bearing types
                asset_id = _resolve_asset_id(isin, ticker, name, row_num)

                self._create_transaction(
                    row_num=row_num,
                    transactions=transactions,
                    validation_issues=validation_issues,
                    context=f"{descrizione}: {name}" if name else descrizione,
                    broker_id=broker_id,
                    asset_id=asset_id,
                    type=tx_type,
                    date=tx_date,
                    quantity=quantity,
                    cash=cash,
                    description=f"{descrizione}: {name}" if name else descrizione,
                    tags=["import", "fineco"],
                )

                # Variant B: emit a separate FEE transaction for total commissions
                if has_commissions:
                    fee_total = self._sum_commissions(row)
                    if fee_total > 0:
                        self._create_transaction(
                            row_num=row_num,
                            transactions=transactions,
                            validation_issues=validation_issues,
                            context=f"Fineco commissions: {name}" if name else "Fineco commissions",
                            broker_id=broker_id,
                            asset_id=asset_id,
                            type=TransactionType.FEE,
                            date=tx_date,
                            quantity=Decimal("0"),
                            cash=Currency(code=FEE_CURRENCY, amount=-fee_total),
                            description=f"Commissioni: {name}" if name else "Commissioni",
                            tags=["import", "fineco", "fee"],
                        )

        except BRIMParseError:
            raise
        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}") from None
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
            "Fineco file parsed",
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

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @staticmethod
    def _map_transaction_type(descrizione: str, segno: str) -> Optional[TransactionType]:
        """Map a Fineco operation description (+ Segno for trades) to a TransactionType."""
        desc = descrizione.lower()

        if "compravendita" in desc:
            if segno == "A":
                return TransactionType.BUY
            if segno == "V":
                return TransactionType.SELL
            return None
        if "dividendo" in desc:
            return TransactionType.DIVIDEND
        if "cedol" in desc:  # "Stacco Cedole"
            return TransactionType.INTEREST
        if "rimborso" in desc:
            return TransactionType.SELL
        if "aumento capitale" in desc:
            return TransactionType.ADJUSTMENT
        return None

    @staticmethod
    def _apply_sign_rules(tx_type: TransactionType, quantity: Decimal, controvalore: Decimal, currency: str):
        """Apply per-type sign conventions, returning (quantity, cash).

        Magnitudes come verbatim from the report; only the sign is set here.
        """
        qty = abs(quantity)
        amount = abs(controvalore)

        if tx_type == TransactionType.BUY:
            return qty, Currency(code=currency, amount=-amount)
        if tx_type == TransactionType.SELL:
            return -qty, Currency(code=currency, amount=amount)
        if tx_type in (TransactionType.DIVIDEND, TransactionType.INTEREST):
            return Decimal("0"), Currency(code=currency, amount=amount)
        if tx_type == TransactionType.ADJUSTMENT:
            # Quantity change, no cash movement
            return qty, None
        # Fallback (should not happen given _map_transaction_type)
        return quantity, Currency(code=currency, amount=amount) if amount else None

    @staticmethod
    def _sum_commissions(row: List[str]) -> Decimal:
        """Sum the Variant-B commission columns (absolute value)."""
        total = Decimal("0")
        for col in COMMISSION_COLS:
            if col < len(row):
                val = _parse_fineco_number(row[col])
                if val is not None:
                    total += abs(val)
        return total

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/fineco/"

    @property
    def test_file_pattern(self) -> Optional[str]:
        """Filename pattern for auto-detection tests."""
        return "fineco"
