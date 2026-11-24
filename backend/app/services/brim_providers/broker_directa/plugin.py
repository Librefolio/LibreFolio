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
- Provento etf/azioni, Dividendi, Coupon → DIVIDEND (but «Rit.provento etf» is the withholding on it: TAX)
- Cedola → INTEREST
- Conferimento → DEPOSIT
- Prelievo → WITHDRAWAL
- Rit.provento, Ritenuta, Tobin tax → TAX
- Commissioni → FEE

**Linked charges (project 66, P3):** a charge names its one parent (``parent_ref``), else it stays free.
- Commissioni, Tobin tax → the BUY/SELL with the same ``Riferimento ordine``; «Rit. etf» → the SELL of that reference.
- Any other «Rit.…» withholding without an order reference («Rit.cedola obb.», «Rit.provento etf»…) → the one
  DIVIDEND or INTEREST of the same operation date and ISIN (the ``Protocollo`` differs between the two rows).
- «Bollo portafoglio titoli» and the other account charges: no parent.

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

from dataclasses import dataclass
from datetime import date as date_type
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMExtractedAssetInfo, BRIMParseOutput, BRIMValidationIssue
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.brim_providers import _brim_io as io
from backend.app.services.platform.provider_registry import register_provider

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
COL_REFERENCE = 11  # Riferimento ordine (may be missing, empty or blank on rows that are not trades)

# Type mapping (lowercase search)
TYPE_MAPPINGS: Dict[str, TransactionType] = {
    # BUY
    "acquisto": TransactionType.BUY,
    # SELL
    "vendita": TransactionType.SELL,
    # A withholding first: «Rit.provento etf» is the tax on an income, not the income (project 66, P3; until 1.1.0 it
    # matched «provento» and became a positive DIVIDEND).
    "rit.": TransactionType.TAX,
    # DIVIDEND
    "provento": TransactionType.DIVIDEND,
    "dividendi": TransactionType.DIVIDEND,
    "dividendo": TransactionType.DIVIDEND,
    "coupon": TransactionType.DIVIDEND,
    # TAX
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


@dataclass(frozen=True)
class _CreatedRow:
    """A row of the output with what links a charge to its parent: its type text, ``Riferimento ordine`` and ISIN."""

    row_num: int
    tx: TXCreateItem
    tipo: str
    reference: str
    isin: str


def _parent_candidates(item: _CreatedRow, by_reference: Dict[str, List[TXCreateItem]], by_income: Dict[tuple, List[TXCreateItem]]) -> List[TXCreateItem]:
    """The rows a charge could belong to (project 66, P3).

    - A commission or a Tobin tax with a ``Riferimento ordine`` → the BUY/SELL of that reference.
    - A withholding («Rit.…») with a reference → the SELL of that reference («Rit. etf», the tax on a gain); without
      one → the DIVIDEND and INTEREST rows of its operation date and ISIN, both types together (the consultant, 21/11:
      «Rit.cedola obb.», «Rit.provento etf» and any other «Rit.» label on an income).

    Empty for the rest (account charges, a row with neither a reference nor an ISIN). The caller links only one candidate.
    """
    kind = "".join(item.tipo.lower().split())
    if ("commission" in kind or "tobin" in kind) and item.reference:
        return by_reference.get(item.reference, [])
    if "rit." not in kind:
        return []
    if item.reference:
        return [tx for tx in by_reference.get(item.reference, []) if tx.type == TransactionType.SELL]
    if item.isin:
        return [*by_income.get((TransactionType.DIVIDEND, item.tx.date, item.isin), []), *by_income.get((TransactionType.INTEREST, item.tx.date, item.isin), [])]
    return []


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
        return "Import transactions from Directa SIM export (CSV or XLSX). Supports all Italian transaction types including ETF dividends, bond coupons, taxes, and trading operations."

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

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:  # noqa: C901 — flat row loop: validation guards and per-type field mapping, no nested logic
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
        # Every row created, with what links a charge to its parent: linked once every row is read (``_link_charges``).
        created_rows: List[_CreatedRow] = []
        next_fake_id = FAKE_ASSET_ID_BASE

        # Read either variant (CSV or XLSX) into a uniform list[list[cell]]; the
        # delimiter (CSV) and worksheet (XLSX) are resolved inside _brim_io.
        try:
            rows = io.read_rows(file_path)
        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}", details={"code": "file_not_found", "context": {"file": file_path.name}}) from None
        except Exception as e:
            raise BRIMParseError(f"Error reading file: {e}", details={"code": "file_unreadable", "context": {"error": str(e)}}) from e

        # Both variants share the same layout; locate the labelled header row
        # dynamically (robust to metadata line-count changes) — the data columns
        # then sit at the fixed COL_* offsets below in CSV and XLSX alike.
        header_idx = io.find_header_row(rows, ["Data operazione", "Tipo operazione", "Isin"])
        if header_idx is None:
            raise BRIMParseError(
                "Directa header row not found (expected 'Data operazione'/'Tipo operazione'/'Isin')",
                details={"code": "header_row_not_found", "context": {"expected": "Data operazione, Tipo operazione, Isin"}},
            )

        # W-B86: the rows left out for a reason the plugin cannot call safe become two shared notices, with the link to open an issue.
        skips = io.RowSkips(rows[header_idx])

        for offset, row in enumerate(rows[header_idx + 1 :]):
            row_num = header_idx + 2 + offset  # 1-based line number for messages

            # Skip empty rows
            if io.is_blank_row(row):
                continue

            # Need at least the basic columns up to "Importo euro"
            if len(row) < COL_AMOUNT_EUR + 1:
                skips.unreadable(row_num, row, "colonne insufficienti")
                continue

            # Parse date
            tx_date = _parse_directa_date(row[COL_DATE])
            if not tx_date:
                skips.unreadable(row_num, row, f"data non valida: '{io.cell_str(row[COL_DATE])}'")
                continue

            # Parse type
            tipo_raw = io.cell_str(row[COL_TYPE])
            if not tipo_raw:
                skips.unreadable(row_num, row, "tipo operazione mancante")
                continue

            tx_type = _map_transaction_type(tipo_raw)
            if not tx_type:
                skips.unknown(row_num, row, f"tipo sconosciuto: '{tipo_raw}'")
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
            created = self._create_transaction(
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
            if created is not None:
                reference = io.cell_str(row[COL_REFERENCE]).strip() if len(row) > COL_REFERENCE else ""
                created_rows.append(_CreatedRow(row_num, created, tipo_raw, reference, isin))

        self._link_charges(created_rows, transactions)

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

        return BRIMParseOutput(transactions=transactions, warnings=[*warnings, *skips.notices()], validation_issues=validation_issues, extracted_assets=extracted_assets_typed)

    def _link_charges(self, created_rows: List[_CreatedRow], transactions: List[TXCreateItem]) -> None:
        """Link each charge to its one parent once every row is read, keeping the file's order (project 66, P3).

        - Commissioni, Tobin tax → the one BUY/SELL with the same ``Riferimento ordine``; a «Rit.…» with a reference → the
          one SELL. A reference that names no trade or several leaves the charge free.
        - A «Rit.…» without a reference → the one DIVIDEND or INTEREST of the same date and ISIN (``_parent_candidates``).
        """
        by_reference: Dict[str, List[TXCreateItem]] = {}
        by_income: Dict[tuple, List[TXCreateItem]] = {}
        for item in created_rows:
            if item.tx.type in (TransactionType.BUY, TransactionType.SELL) and item.reference:
                by_reference.setdefault(item.reference, []).append(item.tx)
            elif item.tx.type in (TransactionType.DIVIDEND, TransactionType.INTEREST) and item.isin:
                by_income.setdefault((item.tx.type, item.tx.date, item.isin), []).append(item.tx)
        for item in created_rows:
            if item.tx.type in (TransactionType.FEE, TransactionType.TAX):
                candidates = _parent_candidates(item, by_reference, by_income)
                if len(candidates) == 1:
                    self._link_existing_charge(item.tx, candidates[0], transactions, row_num=item.row_num)

    @property
    def plugin_version(self) -> str:
        # 1.1.0 — the rows left out (unreadable, unknown type) are reported with the shared notices and the link to open an issue (W-B86).
        # 1.2.0 — «Rit.provento etf» is a TAX, no longer a positive DIVIDEND; each charge is linked to its one parent (project 66, P3).
        return "1.2.0"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/directa/"

    @property
    def test_file_pattern(self) -> Optional[str]:
        """Filename pattern for auto-detection tests."""
        return "directa"
