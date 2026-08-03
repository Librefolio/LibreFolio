"""Crédit Agricole broker report import plugin (BRIM).

Crédit Agricole exports the "Lista Movimenti Deposito Titoli" as both a
**CSV** (``;`` separated, UTF-8 BOM) and an **XLSX** carrying the same data. This
single plugin reads either format: the header row is located dynamically and the
columns are mapped by label, so the leading metadata columns present only in the
XLSX variant are handled transparently.

**Warning language follows the input format.** The only export format supported
today is the Italian one, so user-facing warnings are emitted in Italian. When a
differently localized Crédit Agricole export (a non-Italian entity) is added
later, its warnings should be emitted in that format's language.

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

This single plugin also reads the account "Lista Movimenti Conto" cash-movements
layout (``Data Op.;Data Val.;Causale;Descrizione;Importo;Divisa``). Those rows are
bank cash, mapped by causale to FEE/TAX (capital gain, bollo, canone, spese),
INTEREST/DIVIDEND (coupons/dividends, linked to their security by ISIN when named),
identifiable bond maturity SELL + optional premium INTEREST, or DEPOSIT/WITHDRAWAL by
sign (POS, utenze, prelievi, emoluments, giroconto and unidentified cash side of
trades). Account-mode transactions keep the bank description verbatim and carry the
causale as a tag.

Because the securities "Deposito Titoli" export is securities-only and does not
include bank cash movements, the plugin adds same-day cash counter-entries so the
broker cash nets to zero: DEPOSIT before every cash BUY, WITHDRAWAL after every
SELL, and a balancing WITHDRAWAL after every coupon (CEDOLA) and maturity-premium
INTEREST leg. Succession transfers carry no counter-entry (a cashless ADJUSTMENT).

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
    BRIMAssetNotice,
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


# End-of-export recap/summary rows CA appends after the last real movement.
# The XLSX export closes with labelled totals ("Totale Entrate/Uscite/Movimenti €"
# on the account layout, "Riepilogo ..." on some securities layouts); the CSV
# export omits them entirely. They carry no operation date and must never be
# imported as a transaction, so the parser recognises and drops them explicitly.
_RECAP_FOOTER_MARKERS = ("TOTALE", "RIEPILOGO", "SALDO FINALE")


def _is_recap_footer(text: str) -> bool:
    """True for a CA end-of-export recap/summary row identified by its label."""
    return text.strip().upper().startswith(_RECAP_FOOTER_MARKERS)


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


# ---------------------------------------------------------------------------
# Account "Lista Movimenti Conto" layout — cash-movement classification
# ---------------------------------------------------------------------------

# ISIN pattern used to decide whether an income row names a security. Both bond
# coupons (``CEDOLA:… ISIN …``) and dividends reference their security by ISIN and
# are linked to it; bank credit interest carries no ISIN and stays unallocated.
_ISIN_RE = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b")

# Causali whose rows are coupon/dividend income (cash in, unless clawed back).
_ACCT_INCOME_CAUSALI = {"CEDOLE, DIVIDENDI, PREMI ESTRATTI"}

# Account cash rows that can represent a matured / redeemed security. When the
# same account export also contains the final coupon with an ISIN + NOMINALE, the
# nominal is recovered in-file and the disposal is split into par SELL + premium
# INTEREST. When it is not identifiable, the whole redemption is still booked as a
# SELL (everything as sold, unknown nominal) — never a generic DEPOSIT.
_ACCT_MATURITY_CAUSALI = {"TITOLI SCADUTI O ESTRATTI"}

# Causali whose rows are securities fees/taxes (split by description keyword).
_ACCT_FEETAX_CAUSALI = {"COMMISS./SPESE SU OPERAZ. TITOLI", "COMMISSIONI/SPESE"}

# "INTERESSI/COMPETENZE" is sign-dependent: a debit is the account fee
# (CANONE MENSILE), a credit is real interest income.
_ACCT_CANONE_CAUSALI = {"INTERESSI/COMPETENZE"}

# Description keywords that make a fee row a TAX (capital gain, stamp duty,
# withholding) rather than a plain FEE (management/administration/coupon-detach).
_TAX_KEYWORDS = ("CAPITAL GAIN", "D.LGS 461", "461/97", "IMPOSTA", "BOLLO", "RITENUTA")

# Description keyword that marks a dividend (vs a bond coupon "CEDOLA").
_DIVIDEND_KEYWORDS = ("DIVIDEND",)

_ACCOUNT_MATURITY_RE = re.compile(r"RIMB\.TIT\.\s*(?P<name>.+?)\s*\((?P<code>[^)]*)\)", re.IGNORECASE)
_ACCOUNT_NOMINALE_RE = re.compile(r"\bNOMINALE\s*:\s*(?P<nominale>[\d\.\,]+)", re.IGNORECASE)


def _slug_causale(causale: str) -> str:
    """Compact, tag-safe slug of a causale (``"CEDOLE, DIVIDENDI"`` -> ``cedole_dividendi``)."""
    return re.sub(r"[^a-z0-9]+", "_", causale.lower()).strip("_")


def _names_an_asset(description_upper: str) -> bool:
    """True when the description carries an ISIN (gates DIVIDEND vs INTEREST)."""
    return bool(_ISIN_RE.search(description_upper))


def _income_asset_name(description: str, isin: str) -> str:
    """Best-effort security name for an account-mode income row (bond coupon or
    dividend): the text before the ISIN, minus a leading ``CEDOLA``/``DIVIDENDO``."""
    idx = description.upper().find(isin)
    head = description[:idx] if idx > 0 else description
    head = re.sub(r"^\s*(CEDOLA|DIVIDEND[OIA]?)\s*", "", head, flags=re.IGNORECASE).strip(" :-\t")
    return head or isin


def _digits_only(value: str) -> str:
    """Return only decimal digits from a broker identifier fragment."""
    return re.sub(r"\D+", "", value)


@register_provider(BRIMProviderRegistry)
class CreditAgricoleBrokerProvider(BRIMProvider):
    """Crédit Agricole "Lista Movimenti Deposito Titoli" import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_credit_agricole"

    @property
    def provider_name(self) -> str:
        return "Crédit Agricole"

    @property
    def description(self) -> str:
        return (
            "Import from Crédit Agricole exports (CSV or XLSX): the "
            "'Lista Movimenti Deposito Titoli' securities movements (coupons, "
            "purchases, redemptions, maturities, succession transfers; balanced "
            "with automatic cash counter-entries) and the 'Lista Movimenti Conto' "
            "account movements (liquidity, fees, taxes and income as "
            "deposits/withdrawals). Assets are identified by name only (no ISIN)."
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
        return "1.4.3"

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "credit_agricole"

    def can_parse(self, file_path: Path) -> bool:
        """Detect a Crédit Agricole securities- or account-movements export."""
        if file_path.suffix.lower() not in (".csv", ".xlsx"):
            return False
        try:
            rows = io.read_rows(file_path)
        except Exception:
            return False
        blob = " \n ".join(io.cell_str(c).lower() for row in rows[:40] for c in row)
        if "lista movimenti deposito titoli" in blob:
            return True
        # Securities layout header trio (Intesa uses Operazione/Dettagli, not Causale/Nome).
        if "data operazione" in blob and "causale" in blob and "nome" in blob:
            return True
        # Account "Lista Movimenti Conto" layout header trio.
        return "data op." in blob and "descrizione" in blob and "importo" in blob

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        try:
            rows = io.read_rows(file_path)
        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}") from None
        except Exception as exc:
            raise BRIMParseError(f"Error reading file: {exc}") from exc

        # This single plugin reads two Crédit Agricole layouts; the header row
        # decides which. Securities "Deposito Titoli" movements carry positions
        # and coupons; the account "Lista Movimenti Conto" carries bank cash
        # (liquidity, fees, taxes, income) with no per-asset detail.
        if io.find_header_row(rows, ["Data operazione", "Causale", "Quantità"]) is not None:
            return self._parse_securities(rows, broker_id)
        if io.find_header_row(rows, ["Data Op.", "Descrizione", "Importo"]) is not None:
            return self._parse_account_movements(rows, broker_id)
        raise BRIMParseError("Crédit Agricole header row not found (neither securities 'Deposito " "Titoli' nor account 'Lista Movimenti Conto' layout)")

    def _parse_securities(self, rows: List[List], broker_id: int) -> BRIMParseOutput:
        header_idx = io.find_header_row(rows, ["Data operazione", "Causale", "Quantità"])
        if header_idx is None:
            raise BRIMParseError("Crédit Agricole securities header row not found")

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
            ctv = io.to_decimal_it(io.row_get(row, col, "ctv"))
            if tx_date is None and _is_recap_footer(name):
                continue  # expected end-of-export recap row (XLSX only)
            if tx_date is None or not causale:
                continue  # non-movement leftover (blank/meta) — not a real trade

            currency = _resolve_currency(row, divisa_cols)
            price = io.to_decimal_it(io.row_get(row, col, "price"))
            qty = io.to_decimal_plain(io.row_get(row, col, "qty"))

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
                warnings.append(f"Riga {offset}: causale '{causale}' non riconosciuta, saltata")
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
                add_cash_counter_entry(
                    row_num=offset,
                    tx_type=TransactionType.WITHDRAWAL,
                    tx_date=tx_date,
                    currency_code=currency,
                    amount=-abs(maturity_surplus),
                    name=name,
                    trade_type=TransactionType.INTEREST,
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

            # A coupon (CEDOLA -> INTEREST) is income with no bank-cash counterpart
            # in this securities-only export; balance it with a WITHDRAWAL so the
            # broker cash nets to zero (mirrors BUY/SELL and the maturity premium).
            if tx_type == TransactionType.INTEREST and cash is not None and cash.amount != 0:
                add_cash_counter_entry(
                    row_num=offset,
                    tx_type=TransactionType.WITHDRAWAL,
                    tx_date=tx_date,
                    currency_code=currency,
                    amount=-abs(cash.amount),
                    name=name,
                    trade_type=TransactionType.INTEREST,
                )

        if succession_count:
            warnings.append(
                f"{succession_count} righe di successione (GIRO ALTRO DOSSIER / VERS.TITOLI) importate come RETTIFICA senza cassa (trasferimento in ingresso da un dossier non tracciato — nessun denaro speso, quindi nessun DEPOSITO creato). "
                "Ogni gamba conserva il proprio prezzo tramite cost_basis_override; uno stesso titolo può comparire in più gambe a prezzi diversi, rispecchiando il report della banca."
            )
        if not transactions:
            warnings.append("Nessuna transazione valida trovata nel file")

        # Advisory: flag assets whose transactions include a maturity/redemption (e.g. TITOLI
        # SCADUTI, FONDI: RIMBORSO) so the create-asset UI can warn that the security may be
        # delisted and unsearchable. Advisory only — never changes import behaviour.
        for _asset_id, _idxs in io.detect_maturity_hits(transactions).items():
            _info = extracted_assets.get(_asset_id)
            if _info is not None:
                _info.notices.append(
                    BRIMAssetNotice(
                        kind=io.MATURITY_NOTICE_KIND,
                        reason="Rilevata almeno una transazione di scadenza/rimborso (es. «TITOLI SCADUTI» o «FONDI: RIMBORSO»).",
                        transaction_indexes=_idxs,
                    )
                )

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

    # ------------------------------------------------------------------
    # Account "Lista Movimenti Conto" -> cash movements (liquidity/fees/taxes/income)
    # ------------------------------------------------------------------

    def _classify_account_row(self, causale: str, description: str, amount: Decimal, currency: str) -> tuple[TransactionType, Currency]:
        """Map one account-movements row to a ``(type, cash)`` pair.

        Typed mapping (verbatim amounts, per-row currency; identifiable income —
        bond coupon or dividend, both carrying an ISIN — is asset-linked by the
        caller, bank interest and generic cash stay unallocated):
        - securities fees/taxes -> TAX (capital gain / imposta / bollo / ritenuta)
          or FEE (management, administration, coupon-detach, monthly canone);
        - coupons / dividends / credit interest -> INTEREST, or DIVIDEND when the
          row both mentions a dividend and names a security (ISIN);
        - everything else (POS, utenze, prelievi, emoluments, giroconto and the
          cash side of securities trades) -> DEPOSIT/WITHDRAWAL by sign.

        Sign-robust: a positive fee is treated as a refund (DEPOSIT), negative
        income as a clawback (WITHDRAWAL). BRIM sign convention: FEE/TAX and
        WITHDRAWAL carry cash < 0; INTEREST/DIVIDEND and DEPOSIT carry cash > 0.
        """
        desc_u = description.upper()
        abs_amt = abs(amount)

        # Fees / taxes: securities operation charges, account charges, monthly canone.
        if causale in _ACCT_FEETAX_CAUSALI or (causale in _ACCT_CANONE_CAUSALI and amount < 0):
            if amount > 0:  # refunded charge
                return TransactionType.DEPOSIT, Currency(code=currency, amount=abs_amt)
            tx_type = TransactionType.TAX if any(kw in desc_u for kw in _TAX_KEYWORDS) else TransactionType.FEE
            return tx_type, Currency(code=currency, amount=-abs_amt)

        # Income: coupons, dividends, credit interest.
        if causale in _ACCT_INCOME_CAUSALI or (causale in _ACCT_CANONE_CAUSALI and amount > 0):
            if amount < 0:  # clawed-back income
                return TransactionType.WITHDRAWAL, Currency(code=currency, amount=-abs_amt)
            is_dividend = any(kw in desc_u for kw in _DIVIDEND_KEYWORDS) and _names_an_asset(desc_u)
            tx_type = TransactionType.DIVIDEND if is_dividend else TransactionType.INTEREST
            return tx_type, Currency(code=currency, amount=abs_amt)

        # Everything else (incl. the cash side of trades) -> deposit/withdrawal by sign.
        if amount > 0:
            return TransactionType.DEPOSIT, Currency(code=currency, amount=abs_amt)
        return TransactionType.WITHDRAWAL, Currency(code=currency, amount=-abs_amt)

    def _parse_account_movements(self, rows: List[List], broker_id: int) -> BRIMParseOutput:
        """Parse the account "Lista Movimenti Conto" cash-movements layout.

        Header: ``Data Op.;Data Val.;Causale;Descrizione;Importo;Divisa``. Most
        rows are bank cash with no per-asset detail, so transactions are
        unallocated (``asset_id=None``) — the causale is kept as a tag and the bank
        description is preserved verbatim. Exceptions are income rows (bond coupons
        and dividends) and maturity/redemption rows that name a security by ISIN,
        linked to fake assets keyed by that ISIN so the income appears under the
        asset in the FIFO lot detail.
        """
        transactions: List[TXCreateItem] = []
        warnings: List[str] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets: Dict[int, BRIMExtractedAssetInfo] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        def asset_id_for(*, key: str, name: str, isin: Optional[str]) -> int:
            nonlocal next_fake_id
            if key in asset_to_fake_id:
                return asset_to_fake_id[key]
            new_id = next_fake_id
            asset_to_fake_id[key] = new_id
            extracted_assets[new_id] = BRIMExtractedAssetInfo(
                extracted_symbol=None,
                extracted_isin=isin,
                extracted_name=name,
            )
            next_fake_id -= 1
            return new_id

        def income_asset_id(desc: str) -> Optional[int]:
            """Link an income row (bond coupon or dividend) to a fake asset keyed by its
            ISIN. Returns None when the row names no security (e.g. bank credit interest)."""
            match = _ISIN_RE.search(desc.upper())
            if match is None:
                return None
            isin = match.group(0)
            return asset_id_for(key=f"isin:{isin}", name=_income_asset_name(desc, isin), isin=isin)

        header_idx = io.find_header_row(rows, ["Data Op.", "Descrizione", "Importo"])
        if header_idx is None:
            raise BRIMParseError("Crédit Agricole account-movements header row not found")
        col = io.build_col_index(
            rows[header_idx],
            {
                "date": ["Data Op."],
                "causale": ["Causale"],
                "descrizione": ["Descrizione"],
                "importo": ["Importo"],
                "divisa": ["Divisa"],
            },
        )

        income_identity_by_date: Dict = {}
        for row in rows[header_idx + 1 :]:
            if io.is_blank_row(row):
                continue
            identity_date = io.to_date(io.row_get(row, col, "date"))
            identity_causale = io.cell_str(io.row_get(row, col, "causale")).upper()
            identity_description = io.cell_str(io.row_get(row, col, "descrizione"))
            if identity_date is None or identity_causale not in _ACCT_INCOME_CAUSALI:
                continue
            isin_match = _ISIN_RE.search(identity_description.upper())
            nominale_match = _ACCOUNT_NOMINALE_RE.search(identity_description)
            if isin_match is None or nominale_match is None:
                continue
            isin = isin_match.group(0)
            nominale = io.to_decimal_it(nominale_match.group("nominale"))
            if nominale is None or nominale <= 0:
                continue
            income_identity_by_date.setdefault(identity_date, []).append(
                {
                    "isin": isin,
                    "isin_digits": _digits_only(isin),
                    "name": _income_asset_name(identity_description, isin),
                    "nominale": nominale,
                }
            )

        for offset, row in enumerate(rows[header_idx + 1 :], start=header_idx + 2):
            if io.is_blank_row(row):
                continue
            tx_date = io.to_date(io.row_get(row, col, "date"))
            causale = io.cell_str(io.row_get(row, col, "causale")).upper()
            description = io.cell_str(io.row_get(row, col, "descrizione"))
            amount = io.to_decimal_it(io.row_get(row, col, "importo"))
            if tx_date is None and _is_recap_footer(description):
                continue  # expected end-of-export recap totals (XLSX only)
            if tx_date is None or not causale:
                continue  # non-movement leftover (blank/meta) — not a real movement

            if amount is None:
                warnings.append(f"Riga {offset}: importo non valido per '{causale}', saltata")
                continue
            if amount == 0:
                continue

            currency = io.cell_str(io.row_get(row, col, "divisa")) or "EUR"
            context = f"{causale}: {description}" if description else causale

            if causale in _ACCT_MATURITY_CAUSALI and amount > 0:
                maturity_match = _ACCOUNT_MATURITY_RE.search(description)
                maturity_code = _digits_only(maturity_match.group("code")) if maturity_match else ""
                maturity_name = maturity_match.group("name").strip() if maturity_match else description
                identity = next((item for item in income_identity_by_date.get(tx_date, []) if maturity_code and maturity_code in item["isin_digits"]), None)
                if identity is None:
                    # No same-day coupon carries this security's ISIN + NOMINALE, so we
                    # cannot split par principal from any premium. Book the whole redemption
                    # as a SELL at par — everything treated as the bond's disposal, no
                    # INTEREST leg — instead of external cash, so it reduces a position and
                    # never inflates paid-in capital (consistent with the securities-export
                    # fallback at ``_parse_securities``). With no position and no reported
                    # price we assume a par (100) redemption, so the derived nominal equals
                    # the cash (quantity < 0); flag it for the user to verify.
                    warnings.append(f"Riga {offset}: scadenza/rimborso '{description}' non collegabile a un titolo (ISIN/nominale non trovati nella stessa data); importata interamente come vendita a valore nominale (par 100, nessuna quota di interesse) — verifica il nominale.")
                    model = io.model_bond_maturity(ctv=abs(amount), price=Decimal(100), held_qty=None)
                    fallback_asset_id = asset_id_for(key=f"maturity:{maturity_code or maturity_name}", name=maturity_name, isin=None) if maturity_name else None
                    self._create_transaction(
                        row_num=offset,
                        transactions=transactions,
                        validation_issues=validation_issues,
                        context=context,
                        broker_id=broker_id,
                        asset_id=fallback_asset_id,
                        type=TransactionType.SELL,
                        date=tx_date,
                        quantity=-model.nominal,
                        cash=Currency(code=currency, amount=model.principal_cash),
                        description=f"[{causale} — rimborso/scadenza da conto, titolo non identificato] {maturity_name} (source: {description}; venduto interamente a par {model.par_price}, nominale derivato {model.nominal})"[:500],
                        tags=["import", "credit_agricole", _slug_causale(causale), "account_maturity"],
                    )
                    continue
                else:
                    nominale = identity["nominale"]
                    # Reuse the shared bond-redemption model (par principal + surplus-as-INTEREST),
                    # the same knowledge already used by the securities export and Fineco. The nominal
                    # is recovered in-file from the same-day coupon (income_identity_by_date), never the DB.
                    model = io.model_bond_maturity(ctv=abs(amount), price=None, held_qty=nominale)
                    asset_id = asset_id_for(key=f"isin:{identity['isin']}", name=identity["name"] or maturity_name, isin=identity["isin"])
                    sell_description = f"[{causale} — rimborso/scadenza da conto] {identity['name'] or maturity_name} (source: {description}; redeemed at par {model.par_price}, nominal {model.nominal})"
                    created = self._create_transaction(
                        row_num=offset,
                        transactions=transactions,
                        validation_issues=validation_issues,
                        context=context,
                        broker_id=broker_id,
                        asset_id=asset_id,
                        type=TransactionType.SELL,
                        date=tx_date,
                        quantity=-model.nominal,
                        cash=Currency(code=currency, amount=model.principal_cash),
                        description=sell_description[:500],
                        tags=["import", "credit_agricole", _slug_causale(causale), "account_maturity"],
                    )
                    if created is not None and model.surplus_cash > 0:
                        self._create_transaction(
                            row_num=offset,
                            transactions=transactions,
                            validation_issues=validation_issues,
                            context=f"Maturity premium for {identity['name'] or maturity_name}",
                            broker_id=broker_id,
                            asset_id=asset_id,
                            type=TransactionType.INTEREST,
                            date=tx_date,
                            quantity=Decimal("0"),
                            cash=Currency(code=currency, amount=model.surplus_cash),
                            description=f"[{causale} — premio/rivalutazione da conto] {identity['name'] or maturity_name} (source: {description}; surplus over par {model.surplus_cash})"[:500],
                            tags=["import", "credit_agricole", _slug_causale(causale), "maturity_premium"],
                        )
                    continue

            tx_type, cash = self._classify_account_row(causale, description, amount, currency)
            # Coupons (INTEREST) and dividends both name their security by ISIN — link the
            # income to that bond/fund so it shows under the asset in the FIFO lot detail.
            # Bank credit interest ("INTERESSI/COMPETENZE" credit) carries no ISIN and stays
            # unallocated (income_asset_id returns None).
            asset_id = income_asset_id(description) if tx_type in (TransactionType.INTEREST, TransactionType.DIVIDEND) else None

            self._create_transaction(
                row_num=offset,
                transactions=transactions,
                validation_issues=validation_issues,
                context=context,
                broker_id=broker_id,
                asset_id=asset_id,
                type=tx_type,
                date=tx_date,
                quantity=Decimal("0"),
                cash=cash,
                description=(description or causale)[:500],
                tags=["import", "credit_agricole", _slug_causale(causale)],
            )

        if not transactions:
            warnings.append("Nessun movimento di conto trovato nel file")

        logger.info(
            "Crédit Agricole account movements parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
        )
        return BRIMParseOutput(
            transactions=transactions,
            warnings=warnings,
            validation_issues=validation_issues,
            field_todos=[],
            extracted_assets=extracted_assets,
        )
