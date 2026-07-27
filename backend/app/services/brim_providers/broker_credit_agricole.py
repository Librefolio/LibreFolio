"""Crédit Agricole Italia broker report import plugin (BRIM).

Crédit Agricole Italia exports the "Lista Movimenti Deposito Titoli" as both a
**CSV** (``;`` separated, UTF-8 BOM) and an **XLSX** carrying the same data. This
single plugin reads either format: the header row is located dynamically and the
columns are mapped by label, so the leading metadata columns present only in the
XLSX variant are handled transparently.

**No ISIN** is present — the asset is only identified by its ``Nome``.

Number conventions in this export are mixed and handled per column:
- ``Prezzo`` and ``Controvalore in Euro`` are Italian-formatted (``50.683,13``).
- ``Quantità`` uses dotted decimals for funds (``1867.178``) and plain integers
  for bond nominals (``50000``).
- ``Cambio`` (FX rate) is **ignored** (BRIM never converts currencies).

Causale mapping:
- ``CEDOLA`` -> INTEREST (quantity 0; the nominal in the Quantità column is the
  bond face value, not a trade, so it is ignored). Cash = +Controvalore.
- ``ACQ.CONT.SU MERC.`` / ``SICAV: SOTTOSCR`` -> DEPOSIT + BUY.
- ``FONDI: RIMBORSO`` -> SELL + WITHDRAWAL.
- ``TITOLI SCADUTI`` -> bond redemption at maturity. A bond is always redeemed at
  **par** (100): the SELL closes the *held* nominal at par and any amount the bank
  credited above par (premio fedeltà / ``FOI`` revaluation of a BTP Italia) is
  booked as a separate INTEREST leg (reddito di capitale). The held nominal is
  taken from the position built by the other rows (succession / buys); only when no
  position is found is the nominal derived from Controvalore / Prezzo and flagged
  with a *verify* field-todo. A matching WITHDRAWAL neutralises the par principal.
- ``GIRO ALTRO DOSSIER`` / ``VERS.TITOLI`` -> ADJUSTMENT (cashless transfer-in).
  These are the succession transfers (nonno -> nonna): the receiving leg of a
  transfer whose paying leg lives on another, untracked dossier. No money was
  spent here, so the security is seeded with an ADJUSTMENT that sets the position
  and carries the per-unit book price via ``cost_basis_override`` (bond/fund price
  convention), mirroring the patrimonio-snapshot pattern. No DEPOSIT is emitted, so
  paid-in capital is not inflated. Each source leg is preserved as its own
  ADJUSTMENT with the originating causale kept in the description.

Because this Crédit Agricole export is securities-only and does not include bank
cash movements, the plugin adds same-day cash counter-entries: DEPOSIT before
every cash BUY and WITHDRAWAL after every SELL. Succession transfers and coupons
carry no counter-entry (a succession is a cashless ADJUSTMENT; a coupon is income).

The plugin transcribes reported figures verbatim and never calls the FX
subsystem.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import (
    FAKE_ASSET_ID_BASE,
    BRIMExtractedAssetInfo,
    BRIMFieldTodo,
    BRIMParseOutput,
    BRIMValidationIssue,
)
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.brim_providers import _brim_io as io
from backend.app.services.provider_registry import BRIMProviderRegistry, register_provider

logger = structlog.get_logger(__name__)

# Causali that represent the nonno -> nonna succession transfers (Controvalore 0).
_SUCCESSION_CAUSALI = {"GIRO ALTRO DOSSIER", "VERS.TITOLI"}

# Causali that increase a securities position (cash buys and fund subscriptions).
_BUY_CAUSALI = {"ACQ.CONT.SU MERC.", "SICAV: SOTTOSCR"}

# Name keywords that identify a bond (price quoted per 100 of nominal).
_BOND_KEYWORDS = ("BTP", "BOT", "CCT", "CTZ", "BUND", "OAT", "OBBLIG", "CCTEU")


def _is_bond(name: str) -> bool:
    """Heuristic: a bond is priced per 100 of nominal; a fund is priced per unit."""
    upper = name.upper()
    return any(kw in upper for kw in _BOND_KEYWORDS)


_ISO_CCY_RE = re.compile(r"^[A-Za-z]{3}$")


def _resolve_currency(row: Sequence, divisa_cols: Sequence[int], default: str = "EUR") -> str:
    """Pick the first valid ISO-like currency code among the ``Divisa`` columns.

    The XLSX variant duplicates the causale into the transaction ``Divisa``
    column, so the header position alone is unreliable; scanning every
    ``Divisa``/``Divisa prezzo`` column and taking the first 3-letter code is
    robust for both CSV and XLSX.
    """
    for cidx in divisa_cols:
        if cidx < len(row):
            value = io.cell_str(row[cidx])
            if _ISO_CCY_RE.match(value):
                return value.upper()
    return default


@register_provider(BRIMProviderRegistry)
class CreditAgricoleItaliaBrokerProvider(BRIMProvider):
    """Crédit Agricole Italia "Lista Movimenti Deposito Titoli" import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_credit_agricole"

    @property
    def provider_name(self) -> str:
        return "Crédit Agricole Italia"

    @property
    def description(self) -> str:
        return (
            "Import from Crédit Agricole Italia 'Lista Movimenti Deposito "
            "Titoli' exports (CSV or XLSX). Maps coupons, purchases, "
            "redemptions, maturities and succession transfers; the securities-only "
            "export is balanced with automatic cash counter-entries. Assets are identified by "
            "name only (no ISIN in the export)."
        )

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv", ".xlsx"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> str:
        return "https://www.credit-agricole.it/favicon.ico"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/credit_agricole/"

    @property
    def plugin_version(self) -> str:
        return "1.3.0"

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "credit_agricole"

    def can_parse(self, file_path: Path) -> bool:
        """Detect a Crédit Agricole Italia securities-movements export."""
        if file_path.suffix.lower() not in (".csv", ".xlsx"):
            return False
        try:
            rows = io.read_rows(file_path)
        except Exception:
            return False
        blob = " \n ".join(io.cell_str(c).lower() for row in rows[:40] for c in row)
        if "lista movimenti deposito titoli" in blob:
            return True
        # Header trio unique to CA (Intesa uses Operazione/Dettagli, not Causale/Nome).
        return "data operazione" in blob and "causale" in blob and "nome" in blob

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        try:
            rows = io.read_rows(file_path)
        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}") from None
        except Exception as exc:
            raise BRIMParseError(f"Error reading file: {exc}") from exc

        header_idx = io.find_header_row(rows, ["Data operazione", "Causale", "Quantità"])
        if header_idx is None:
            raise BRIMParseError("Crédit Agricole header row not found")

        col = io.build_col_index(
            rows[header_idx],
            {
                "date": ["Data operazione"],
                "name": ["Nome"],
                "causale": ["Causale"],
                "price": ["Prezzo"],
                "qty": ["Quantità"],
                "ctv": ["Controvalore in Euro", "Ctv in Eur"],
            },
        )
        # Every column whose header mentions "Divisa" (transaction and price
        # currency); the currency is resolved per row from these (see above).
        divisa_cols = [idx for idx, cell in enumerate(rows[header_idx]) if "divisa" in io.cell_str(cell).lower()]

        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        field_todos: List[BRIMFieldTodo] = []
        extracted_assets: Dict[int, BRIMExtractedAssetInfo] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE
        succession_count = 0

        def fake_id_for(name: str) -> int:
            nonlocal next_fake_id
            key = f"name:{name.lower()}"
            if key in asset_to_fake_id:
                return asset_to_fake_id[key]
            new_id = next_fake_id
            asset_to_fake_id[key] = new_id
            extracted_assets[new_id] = BRIMExtractedAssetInfo(extracted_symbol=None, extracted_isin=None, extracted_name=name)
            next_fake_id -= 1
            return new_id

        def add_cash_counter_entry(
            *,
            row_num: int,
            tx_type: TransactionType,
            tx_date,
            currency_code: str,
            amount: Decimal,
            name: str,
            trade_type: TransactionType,
        ) -> None:
            direction = trade_type.value
            description = f"Auto cash for {direction} {name} (Crédit Agricole securities-only export)"
            self._create_transaction(
                row_num=row_num,
                transactions=transactions,
                validation_issues=validation_issues,
                context=description,
                broker_id=broker_id,
                asset_id=None,
                type=tx_type,
                date=tx_date,
                quantity=Decimal("0"),
                cash=Currency(code=currency_code, amount=amount),
                description=description[:500],
                tags=["import", "credit_agricole", "auto_cash"],
            )

        # Pass 1 — net nominal held per security. A maturity (``TITOLI SCADUTI``)
        # reports Quantità 0, so the true nominal lives in the position built by the
        # other rows (succession legs / cash buys, less any fund redemptions). This
        # lets the redemption close the *exact* held nominal at par instead of an
        # approximate value derived from Controvalore / Prezzo. Coupons and the
        # maturities themselves do not change the position and are excluded.
        position_by_name: Dict[str, Decimal] = {}
        for row in rows[header_idx + 1 :]:
            if io.is_blank_row(row):
                continue
            p1_causale = io.cell_str(io.row_get(row, col, "causale")).upper()
            p1_name = io.cell_str(io.row_get(row, col, "name"))
            if not p1_name:
                continue
            p1_qty = io.to_decimal_plain(io.row_get(row, col, "qty")) or Decimal("0")
            p1_key = p1_name.lower()
            if p1_causale in _BUY_CAUSALI or p1_causale in _SUCCESSION_CAUSALI:
                position_by_name[p1_key] = position_by_name.get(p1_key, Decimal("0")) + abs(p1_qty)
            elif p1_causale == "FONDI: RIMBORSO":
                position_by_name[p1_key] = position_by_name.get(p1_key, Decimal("0")) - abs(p1_qty)

        for offset, row in enumerate(rows[header_idx + 1 :], start=header_idx + 2):
            if io.is_blank_row(row):
                continue
            tx_date = io.to_date(io.row_get(row, col, "date"))
            causale = io.cell_str(io.row_get(row, col, "causale")).upper()
            name = io.cell_str(io.row_get(row, col, "name"))
            if tx_date is None or not causale:
                if causale or name:
                    warnings.append(f"Row {offset}: missing date/causale ('{causale}'), skipping")
                continue

            currency = _resolve_currency(row, divisa_cols)
            price = io.to_decimal_it(io.row_get(row, col, "price"))
            qty = io.to_decimal_plain(io.row_get(row, col, "qty"))
            ctv = io.to_decimal_it(io.row_get(row, col, "ctv"))

            tx_type: Optional[TransactionType] = None
            final_qty = Decimal("0")
            cash: Optional[Currency] = None
            description = f"{causale}: {name}"
            derived_quantity = False
            maturity_surplus: Optional[Decimal] = None
            cost_override: Optional[Currency] = None
            cost_basis_mode: Optional[str] = None

            if causale == "CEDOLA":
                tx_type = TransactionType.INTEREST
                final_qty = Decimal("0")  # nominal in Quantità is face value, not a trade
                cash = Currency(code=currency, amount=abs(ctv)) if ctv is not None else None
            elif causale in _BUY_CAUSALI:
                tx_type = TransactionType.BUY
                final_qty = abs(qty) if qty is not None else Decimal("0")
                cash = Currency(code=currency, amount=-abs(ctv)) if ctv is not None else None
            elif causale == "FONDI: RIMBORSO":
                tx_type = TransactionType.SELL
                final_qty = -abs(qty) if qty is not None else Decimal("0")
                cash = Currency(code=currency, amount=abs(ctv)) if ctv is not None else None
            elif causale == "TITOLI SCADUTI":
                tx_type = TransactionType.SELL
                # Assumption (documented on the plugin's user page): a "TITOLI SCADUTI"
                # row is a bond redeemed at par (100). Close the held nominal at par and
                # book anything credited above par (premio fedeltà / FOI revaluation) as a
                # separate INTEREST leg. The nominal comes from the position built by the
                # other rows; an orphan redemption (no position in the file, e.g. a partial
                # download) derives it from Ctv/Prezzo and is flagged for the user to verify.
                held = position_by_name.get(name.lower(), Decimal("0")) if name else Decimal("0")
                if ctv is not None:
                    model = io.model_bond_maturity(ctv=ctv, price=price, held_qty=held if held > 0 else None)
                    if model.nominal > 0:
                        final_qty = -model.nominal
                        cash = Currency(code=currency, amount=model.principal_cash)
                        maturity_surplus = model.surplus_cash
                        derived_quantity = model.source == "derived"
                        description = f"{causale}: {name} (redeemed at par {model.par_price}, nominal {model.nominal} [{model.source}]" + (f", premium {model.surplus_cash})" if model.surplus_cash > 0 else ")")
                    else:
                        cash = Currency(code=currency, amount=abs(ctv))
                        final_qty = -abs(qty) if qty is not None else Decimal("0")
                else:
                    # No countervalue reported: keep the row verbatim (no split possible).
                    cash = None
                    final_qty = -abs(qty) if qty is not None else Decimal("0")
            elif causale in _SUCCESSION_CAUSALI:
                # Succession / transfer-in from a dossier not tracked in LibreFolio: this
                # is the receiving leg of a transfer whose paying leg lives on another,
                # untracked account, so NO money was spent here. Model it as an ADJUSTMENT
                # that seeds the position and carries the per-unit book price via
                # cost_basis_override (bond/fund price convention), mirroring the
                # patrimonio-snapshot pattern. No DEPOSIT is emitted, so paid-in capital is
                # not inflated; each leg keeps its own price, faithful to the report.
                tx_type = TransactionType.ADJUSTMENT
                final_qty = abs(qty) if qty is not None else Decimal("0")
                if price is not None and final_qty > 0:
                    unit_cost = (price / Decimal(100)) if _is_bond(name) else price
                    cost_override = Currency(code=currency, amount=unit_cost)
                    cost_basis_mode = "manual"
                cash = None
                description = f"[{causale} — successione / transfer-in] {name} (price {price}, qty {final_qty})"
                succession_count += 1
            else:
                warnings.append(f"Row {offset}: unrecognised causale '{causale}', skipped")
                continue

            asset_id = fake_id_for(name) if name else None

            buy_counter_start = len(transactions)
            if tx_type == TransactionType.BUY and cash is not None:
                add_cash_counter_entry(
                    row_num=offset,
                    tx_type=TransactionType.DEPOSIT,
                    tx_date=tx_date,
                    currency_code=currency,
                    amount=abs(cash.amount),
                    name=name,
                    trade_type=tx_type,
                )

            created = self._create_transaction(
                row_num=offset,
                transactions=transactions,
                validation_issues=validation_issues,
                context=description,
                broker_id=broker_id,
                asset_id=asset_id,
                type=tx_type,
                date=tx_date,
                quantity=final_qty,
                cash=cash,
                cost_basis_mode=cost_basis_mode,
                cost_basis_override=cost_override,
                description=description[:500],
                tags=["import", "credit_agricole"],
            )

            if created is None:
                if tx_type == TransactionType.BUY and len(transactions) > buy_counter_start:
                    del transactions[buy_counter_start:]
                continue

            if created is not None and derived_quantity:
                field_todos.append(
                    BRIMFieldTodo(
                        tx_index=transactions.index(created),
                        field="quantity",
                        severity="warning",
                        reason_code="derived_quantity",
                        message=f"Matured bond '{name}': no prior position was found in this file (e.g. a partial download), so the nominal was inferred from countervalue/price. Verify it matches the holding you are closing.",
                        context={"causale": causale, "ctv": str(ctv), "price": str(price)},
                    )
                )

            # Amount credited above par at maturity = premio fedeltà / FOI revaluation.
            # Booked as INTEREST (reddito di capitale), mirroring coupons (CEDOLA), so
            # the SELL leg stays exactly at par and the position closes to zero.
            if created is not None and maturity_surplus is not None and maturity_surplus > 0:
                self._create_transaction(
                    row_num=offset,
                    transactions=transactions,
                    validation_issues=validation_issues,
                    context=f"Maturity premium for {name}",
                    broker_id=broker_id,
                    asset_id=asset_id,
                    type=TransactionType.INTEREST,
                    date=tx_date,
                    quantity=Decimal("0"),
                    cash=Currency(code=currency, amount=abs(maturity_surplus)),
                    description=f"[TITOLI SCADUTI — premio/rivalutazione a scadenza] {name} (surplus over par {maturity_surplus})"[:500],
                    tags=["import", "credit_agricole", "maturity_premium"],
                )

            if tx_type == TransactionType.SELL and cash is not None:
                add_cash_counter_entry(
                    row_num=offset,
                    tx_type=TransactionType.WITHDRAWAL,
                    tx_date=tx_date,
                    currency_code=currency,
                    amount=-abs(cash.amount),
                    name=name,
                    trade_type=tx_type,
                )

        if succession_count:
            warnings.append(
                f"{succession_count} succession row(s) (GIRO ALTRO DOSSIER / VERS.TITOLI) imported as cashless ADJUSTMENT (transfer-in from an untracked dossier — no money was spent, so no DEPOSIT is created). "
                "Each leg keeps its own price via cost_basis_override; a security may appear in multiple legs at different prices, mirroring the bank report."
            )
        if not transactions:
            warnings.append("No valid transactions found in file")

        logger.info(
            "Crédit Agricole file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets),
            field_todo_count=len(field_todos),
        )
        return BRIMParseOutput(
            transactions=transactions,
            warnings=warnings,
            validation_issues=validation_issues,
            field_todos=field_todos,
            extracted_assets=extracted_assets,
        )
