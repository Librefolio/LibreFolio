"""Intesa Sanpaolo broker report import plugin (BRIM).

Intesa Sanpaolo ships **two** different XLSX/CSV exports that this single plugin
recognises and parses (variant detected dynamically from the header, never from
a fixed line offset):

1. **Movements** (``lista_completa`` / "Lista Operazione"): the ordinary account
   movement list. Header row carries ``Data / Operazione / Dettagli / … /
   Valuta / Importo``. In practice only two securities operations appear —
   ``Cedole`` (bond coupons -> INTEREST) and ``Commissione Di Gest. E
   Amministr.`` (custody fee -> FEE) — but the same export can also contain
   everyday current-account rows. Any operation whose type this plugin does not
   recognise is **skipped with a warning, never raised**. There is **no ISIN**
   in this file: the asset is only present as free text inside ``Dettagli``.

2. **Portfolio snapshot** (``patrimonio``): the current holdings, in three
   sections — *Fondi e Sicav* (``ISIN``, ``Numero Quote``, ``Controvalore di
   carico fiscale €``), *Titoli di stato* (``ISIN``, ``Quantità``, ``Prezzo
   medio fiscale``, ``Controvalore di carico fiscale €``) and *Liquidità* (cash
   balance). The snapshot is turned into a **seed**: one ``DEPOSIT`` for the
   cash balance plus one ``ADJUSTMENT`` per asset (quantity from the snapshot,
   ``cost_basis_override`` = per-unit fiscal cost — the total ``Controvalore di
   carico fiscale €`` divided by quantity — no cash), all dated at the
   snapshot date (the most recent quote date found in the file).

**Two supported workflows** (documented for the user):

- *Mode 1 — brand-new account*: importing only the **movements** file is enough
  (there is no back-history to seed).
- *Mode 2 — account with years of history (recommended)*: seed with the
  **patrimonio** snapshot and also import the movements; the "before-opening"
  cross-check state then excludes movement rows that predate the broker's
  opening date.

The plugin is a faithful transcriber: it copies the reported figures verbatim
and never calls the FX subsystem or recomputes any amount.
"""

from __future__ import annotations

import re
from datetime import date as date_type
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMAssetNotice, BRIMExtractedAssetInfo, BRIMParseOutput, BRIMValidationIssue
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.brim_providers import _brim_io as io
from backend.app.services.provider_registry import BRIMProviderRegistry, register_provider

logger = structlog.get_logger(__name__)

# Marker used to tell a patrimonio (snapshot) file apart from a movements file.
_SNAPSHOT_MARKER = "controvalore di carico fiscale"

# Regex to strip the "Cedole Su <CCY> <nominal> " prefix from a coupon detail
# string, leaving the free-text asset name (e.g. "BTPIT 28GN30 160").
_COUPON_DETAIL_RE = re.compile(r"^\s*cedol\w*\s+su\s+[a-z]{3}\s+[\d.,]+\s+(.+?)\s*$", re.IGNORECASE)


def _map_movement_type(operazione: str) -> Optional[TransactionType]:
    """Map an Intesa movement ``Operazione`` label to a TransactionType.

    Returns ``None`` for anything not recognised (everyday banking rows), so the
    caller can skip the row with a warning instead of failing.
    """
    op = operazione.lower()
    if "cedol" in op:
        return TransactionType.INTEREST
    if "dividend" in op:
        return TransactionType.DIVIDEND
    if "commission" in op:
        return TransactionType.FEE
    if "ritenut" in op or "imposta" in op or "bollo" in op:
        return TransactionType.TAX
    return None


def _extract_coupon_asset_name(dettagli: str) -> Optional[str]:
    """Extract the asset name from a coupon ``Dettagli`` free-text field."""
    if not dettagli:
        return None
    match = _COUPON_DETAIL_RE.match(dettagli)
    if match:
        return match.group(1).strip()
    return dettagli.strip() or None


@register_provider(BRIMProviderRegistry)
class IntesaSanpaoloBrokerProvider(BRIMProvider):
    """Intesa Sanpaolo import plugin: movements list and portfolio snapshot."""

    @property
    def provider_code(self) -> str:
        return "broker_intesa"

    @property
    def provider_name(self) -> str:
        return "Intesa Sanpaolo"

    @property
    def description(self) -> str:
        return (
            "Import from Intesa Sanpaolo exports (CSV or XLSX). Handles the "
            "movements list (bond coupons and custody fees; unrecognised "
            "everyday-banking rows are skipped) and the portfolio snapshot "
            "(patrimonio), which is imported as a cash deposit plus one "
            "cost-basis adjustment per holding to seed an account with history."
        )

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv", ".xlsx"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> str:
        return "https://www.intesasanpaolo.com/favicon.ico"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/intesa/"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    @property
    def test_file_patterns(self) -> List[str]:
        return ["intesa-lista", "intesa-patrimonio"]

    def can_parse(self, file_path: Path) -> bool:
        """Detect an Intesa movements or patrimonio export (CSV or XLSX)."""
        if file_path.suffix.lower() not in (".csv", ".xlsx"):
            return False
        try:
            rows = io.read_rows(file_path)
        except Exception:
            return False
        blob = " \n ".join(io.cell_str(c).lower() for row in rows[:40] for c in row)
        # Patrimonio snapshot marker.
        if _SNAPSHOT_MARKER in blob:
            return True
        # Movements list: Intesa-specific header trio (CA uses Causale/Nome).
        if "operazione" in blob and "dettagli" in blob and "importo" in blob:
            return True
        return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        try:
            rows = io.read_rows(file_path)
        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}") from None
        except Exception as exc:
            raise BRIMParseError(f"Error reading file: {exc}") from exc

        blob = " \n ".join(io.cell_str(c).lower() for row in rows[:40] for c in row)
        if _SNAPSHOT_MARKER in blob:
            return self._parse_patrimonio(rows, broker_id)
        if io.find_header_row(rows, ["Operazione", "Dettagli", "Importo"]) is not None:
            return self._parse_movements(rows, broker_id)
        raise BRIMParseError("Unrecognised Intesa Sanpaolo layout (neither movements nor patrimonio)")

    # ------------------------------------------------------------------
    # Movements list
    # ------------------------------------------------------------------

    def _parse_movements(self, rows: List[List], broker_id: int) -> BRIMParseOutput:
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets: Dict[int, BRIMExtractedAssetInfo] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        header_idx = io.find_header_row(rows, ["Operazione", "Dettagli", "Importo"])
        if header_idx is None:
            raise BRIMParseError("Movements header row not found")
        col = io.build_col_index(
            rows[header_idx],
            {
                "date": ["Data"],
                "operazione": ["Operazione"],
                "dettagli": ["Dettagli"],
                "ccy": ["Valuta"],
                "importo": ["Importo"],
            },
        )

        for offset, row in enumerate(rows[header_idx + 1 :], start=header_idx + 2):
            if io.is_blank_row(row):
                continue
            tx_date = io.to_date(io.row_get(row, col, "date"))
            operazione = io.cell_str(io.row_get(row, col, "operazione"))
            if tx_date is None or not operazione:
                # Footer/summary or malformed row: silently skip blanks, warn otherwise.
                if operazione:
                    warnings.append(f"Riga {offset}: data mancante per '{operazione}', saltata")
                continue

            tx_type = _map_movement_type(operazione)
            if tx_type is None:
                warnings.append(f"Riga {offset}: operazione '{operazione}' non riconosciuta, saltata (non è un movimento titoli)")
                continue

            amount = io.to_decimal_it(io.row_get(row, col, "importo"))
            if amount is None:
                warnings.append(f"Riga {offset}: importo non valido per '{operazione}', saltata")
                continue

            currency = io.cell_str(io.row_get(row, col, "ccy")) or "EUR"
            dettagli = io.cell_str(io.row_get(row, col, "dettagli"))

            # Sign conventions: INTEREST/DIVIDEND cash > 0; FEE/TAX cash < 0.
            if tx_type in (TransactionType.INTEREST, TransactionType.DIVIDEND):
                amount = abs(amount)
            elif tx_type in (TransactionType.FEE, TransactionType.TAX):
                amount = -abs(amount)

            asset_id: Optional[int] = None
            if tx_type in (TransactionType.INTEREST, TransactionType.DIVIDEND):
                asset_name = _extract_coupon_asset_name(dettagli)
                if asset_name:
                    key = f"name:{asset_name.lower()}"
                    if key in asset_to_fake_id:
                        asset_id = asset_to_fake_id[key]
                    else:
                        asset_id = next_fake_id
                        asset_to_fake_id[key] = asset_id
                        extracted_assets[asset_id] = BRIMExtractedAssetInfo(extracted_symbol=None, extracted_isin=None, extracted_name=asset_name)
                        next_fake_id -= 1

            self._create_transaction(
                row_num=offset,
                transactions=transactions,
                validation_issues=validation_issues,
                context=f"{operazione}: {dettagli}" if dettagli else operazione,
                broker_id=broker_id,
                asset_id=asset_id,
                type=tx_type,
                date=tx_date,
                quantity=Decimal("0"),
                cash=Currency(code=currency, amount=amount) if amount != 0 else None,
                description=(f"{operazione}: {dettagli}" if dettagli else operazione)[:500],
                tags=["import", "intesa"],
            )

        if not transactions:
            warnings.append("Nessun movimento titoli importabile trovato (solo righe di conto corrente?)")

        # Advisory: flag assets whose movements include a maturity/redemption cue so the
        # create-asset UI can warn the security may be delisted/unsearchable. Advisory only.
        for _asset_id, _idxs in io.detect_maturity_hits(transactions).items():
            _info = extracted_assets.get(_asset_id)
            if _info is not None:
                _info.notices.append(
                    BRIMAssetNotice(
                        kind=io.MATURITY_NOTICE_KIND,
                        reason="Rilevata almeno una transazione di scadenza/rimborso.",
                        transaction_indexes=_idxs,
                    )
                )

        logger.info("Intesa movements parsed", transaction_count=len(transactions), warning_count=len(warnings), asset_count=len(extracted_assets))
        return BRIMParseOutput(transactions=transactions, warnings=warnings, validation_issues=validation_issues, extracted_assets=extracted_assets)

    # ------------------------------------------------------------------
    # Portfolio snapshot (patrimonio) -> DEPOSIT + ADJUSTMENT seed
    # ------------------------------------------------------------------

    def _parse_patrimonio(self, rows: List[List], broker_id: int) -> BRIMParseOutput:
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets: Dict[int, BRIMExtractedAssetInfo] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        # Collect asset rows across all "Descrizione / ISIN" sections and the
        # most recent quote date to use as the snapshot (seed) date.
        quote_dates: List[date_type] = []
        pending_assets: List[Dict] = []

        n = len(rows)
        i = 0
        while i < n:
            row = rows[i]
            cells_lower = [io.cell_str(c).lower() for c in row]
            is_section_header = any(c == "descrizione" for c in cells_lower) and any(c == "isin" for c in cells_lower)
            if not is_section_header:
                i += 1
                continue
            col = io.build_col_index(
                row,
                {
                    "name": ["Descrizione"],
                    "isin": ["ISIN"],
                    "qty": ["Numero Quote", "Quantità"],
                    "cost": ["Controvalore di carico fiscale €", "Controvalore di carico fiscale"],
                    "quotedate": ["Data Ultima Quota", "Data-Ora"],
                },
            )
            j = i + 1
            while j < n:
                drow = rows[j]
                name = io.cell_str(io.row_get(drow, col, "name"))
                name_lower = name.lower()
                if io.is_blank_row(drow):
                    j += 1
                    continue
                if name_lower.startswith("descrizione"):
                    break  # next section header
                if name_lower.startswith("totale") or name_lower.startswith("liquidità") or name_lower.startswith("saldo"):
                    break  # end of this section
                isin = io.cell_str(io.row_get(drow, col, "isin"))
                qty = io.to_decimal_it(io.row_get(drow, col, "qty"))
                cost = io.to_decimal_it(io.row_get(drow, col, "cost"))
                if isin and qty is not None and qty > 0:
                    pending_assets.append({"name": name, "isin": isin, "qty": qty, "cost": cost})
                    qdate = io.to_date(io.row_get(drow, col, "quotedate"))
                    if qdate is not None:
                        quote_dates.append(qdate)
                j += 1
            i = j

        snapshot_date = max(quote_dates) if quote_dates else date_type.today()
        if not quote_dates:
            warnings.append("Nessuna data di quotazione trovata nello snapshot; uso la data odierna come data seme")

        # Cash balance (Liquidità section): the "Saldo totale" row carries the amount.
        cash_amount = self._extract_liquidity(rows)
        if cash_amount is not None and cash_amount != 0:
            self._create_transaction(
                row_num=0,
                transactions=transactions,
                validation_issues=validation_issues,
                context="Patrimonio snapshot — liquidity",
                broker_id=broker_id,
                asset_id=None,
                type=TransactionType.DEPOSIT,
                date=snapshot_date,
                quantity=Decimal("0"),
                cash=Currency(code="EUR", amount=abs(cash_amount)),
                description="Snapshot seed (patrimonio) — cash liquidity",
                tags=["import", "intesa", "snapshot-seed"],
            )
        else:
            warnings.append("Nessuna liquidità trovata nello snapshot; deposito seme non creato")

        for idx, asset in enumerate(pending_assets):
            key = f"isin:{asset['isin'].upper()}"
            if key in asset_to_fake_id:
                asset_id = asset_to_fake_id[key]
            else:
                asset_id = next_fake_id
                asset_to_fake_id[key] = asset_id
                extracted_assets[asset_id] = BRIMExtractedAssetInfo(extracted_symbol=None, extracted_isin=asset["isin"], extracted_name=asset["name"])
                next_fake_id -= 1

            cost = asset["cost"]
            qty = asset["qty"]
            # ``cost_basis_override`` is a PER-UNIT weighted-average cost: the portfolio
            # engine and lot analysis multiply it by quantity to obtain the total cost
            # basis. The snapshot instead reports a TOTAL ``Controvalore di carico
            # fiscale €`` → divide by quantity to store the per-unit value.
            unit_cost = (cost / qty) if (cost is not None and qty and qty > 0) else None
            cost_override = Currency(code="EUR", amount=unit_cost) if unit_cost is not None else None
            if cost_override is None:
                warnings.append(f"Titolo '{asset['name']}': nessun costo fiscale nello snapshot; rettifica creata senza override del costo")

            self._create_transaction(
                row_num=idx + 1,
                transactions=transactions,
                validation_issues=validation_issues,
                context=f"Patrimonio snapshot — {asset['name']}",
                broker_id=broker_id,
                asset_id=asset_id,
                type=TransactionType.ADJUSTMENT,
                date=snapshot_date,
                quantity=asset["qty"],
                cash=None,
                cost_basis_mode="manual" if cost_override is not None else None,
                cost_basis_override=cost_override,
                description=f"Snapshot seed (patrimonio) — {asset['name']}"[:500],
                tags=["import", "intesa", "snapshot-seed"],
            )

        if not transactions:
            warnings.append("Nessuna posizione o liquidità trovata nello snapshot patrimonio")

        logger.info("Intesa patrimonio parsed", transaction_count=len(transactions), warning_count=len(warnings), asset_count=len(extracted_assets), snapshot_date=str(snapshot_date))
        return BRIMParseOutput(transactions=transactions, warnings=warnings, validation_issues=validation_issues, extracted_assets=extracted_assets)

    @staticmethod
    def _extract_liquidity(rows: List[List]) -> Optional[Decimal]:
        """Find the cash balance from the Liquidità / Saldo totale row."""
        for row in rows:
            joined = " ".join(io.cell_str(c).lower() for c in row)
            if "saldo totale" in joined or "saldo disponibilità" in joined:
                for cell in row:
                    value = io.to_decimal_it(cell)
                    if value is not None and value != 0:
                        return value
        return None

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "intesa"
