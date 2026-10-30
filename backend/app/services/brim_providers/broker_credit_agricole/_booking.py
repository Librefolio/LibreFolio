"""Crédit Agricole: from the rows of a combined file to transactions.

The combined file (``_combined.py``) holds one line per fact: a securities row and the account row it is the same fact as (a
*pair*), a row on its own, a row left out. This module books them:

- an **account row on its own** is booked exactly as the plugin has always booked a "Lista Movimenti Conto" row (typed by its
  causale, linked to its security by ISIN, the withholding of a coupon as its own tax leg, an unresolved trade asked of the
  user), :meth:`Booking.book_account_row`;
- a **transfer from another dossier** is a cashless adjustment that seeds the position, :meth:`Booking.book_transfer_in`;
- a **pair** (a coupon, a purchase, a fund redemption, a maturity) is one transaction whose cash is the account's: nothing
  balances it, so there is no automatic counter-entry anywhere in a combined file, :meth:`Booking.book_movement`. A securities
  row inside a hole of the account (no account export covers it) is booked the same way with the cash its own row states.

A transaction is dated with the *operation date* (``Data operazione`` for a pair and for a securities row, ``Data Op.`` for an
account row on its own), never with a value date.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

import structlog

from backend.app.db.models import Transaction, TransactionType
from backend.app.db.precision import round_computed_value
from backend.app.schemas.brim import (
    FAKE_ASSET_ID_BASE,
    BRIMEvidence,
    BRIMExtractedAssetInfo,
    BRIMFieldTodo,
    BRIMNotice,
    BRIMValidationIssue,
)
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim.brim_provider import BRIMProvider
from backend.app.services.brim_providers import _brim_io as io
from backend.app.services.brim_providers._brim_output import attach_maturity_notices
from backend.app.services.brim_providers.broker_credit_agricole._classify import (
    ACCOUNT_MATURITY_RE,
    ACCOUNT_NOMINALE_RE,
    ACCOUNT_RITENUTA_RE,
    ACCT_FEETAX_CAUSALI_SECURITIES,
    ACCT_INCOME_CAUSALI,
    ACCT_MATURITY_CAUSALI,
    ACCT_SCT_CAUSALI,
    ACCT_UNRESOLVED_CAUSALI,
    BUY_CAUSALI,
    ISIN_RE,
    SUCCESSION_CAUSALI,
    TIER_UNKNOWN,
    TIER_UNRESOLVED,
    charge_asset_name,
    classify_account_row,
    classify_trade_direction,
    digits_only,
    fmt_money,
    income_asset_name,
    is_bond,
    is_recap_footer,
    is_truncation_of,
    normalize_trade_name,
    prefix_matches,
    sct_fund_redemption_name,
    slug_causale,
    trade_asset_name,
)
from backend.app.services.brim_providers.broker_credit_agricole._report_set import account_withholding
from backend.app.services.brim_providers.broker_credit_agricole._rows import AccountRow, SecuritiesRow

logger = structlog.get_logger(__name__)

ZERO = Decimal("0")
TAGS = ["import", "credit_agricole"]

MATURITY_NOTICE_REASON = "Rilevata almeno una transazione di scadenza/rimborso (es. «TITOLI SCADUTI» o «FONDI: RIMBORSO»)."

#: The account rows as a small sheet: the columns the account arm reads, in this order.
ACCOUNT_SHEET_HEADER = ("Data Op.", "Causale", "Descrizione", "Importo", "Divisa")
_SHEET_COLUMNS = {"date": 0, "causale": 1, "descrizione": 2, "importo": 3, "divisa": 4}
_SHEET_EVIDENCE = [(label, index) for index, label in enumerate(ACCOUNT_SHEET_HEADER)]
#: What a securities row shows in the evidence of a notice.
SECURITIES_EVIDENCE_HEADERS = ("Data operazione", "Nome", "Causale", "Prezzo", "Quantità", "Controvalore")


def sheet_row(row: AccountRow) -> List[str]:
    """An account row as a line of the sheet (the cells are the file's own figures)."""
    return [row.cells.get("Data Op.", ""), row.causale, row.description, row.cells.get("Importo", ""), row.currency]


@dataclass
class Booking:
    """Turns the rows of a combined Crédit Agricole file into transactions, field todos and notices.

    The account arm and the transfer arm are the ones the plugin has always had (versions up to 1.5.0 ran them over a whole
    file; the combined file runs them row by row, over the rows it kept). The pair arm is new: a securities row and the account
    row it is the same fact as become one transaction, the cash being the account's.

    The account rows are seen as a small sheet (``ACCOUNT_SHEET_HEADER``): the identity of a security (ISIN and nominal from a
    coupon), the charges near a trade and the evidence of a todo are read from it, whichever outcome its rows have.
    """

    provider: BRIMProvider
    broker_id: int
    col: Dict[str, int] = field(default_factory=lambda: dict(_SHEET_COLUMNS))
    evidence_cols: List[tuple[str, int]] = field(default_factory=lambda: list(_SHEET_EVIDENCE))
    transactions: List[TXCreateItem] = field(default_factory=list)
    warnings: List[BRIMNotice] = field(default_factory=list)
    validation_issues: List[BRIMValidationIssue] = field(default_factory=list)
    field_todos: List[BRIMFieldTodo] = field(default_factory=list)
    extracted_assets: Dict[int, BRIMExtractedAssetInfo] = field(default_factory=dict)
    asset_to_fake_id: Dict[str, int] = field(default_factory=dict)
    next_fake_id: int = FAKE_ASSET_ID_BASE
    income_identity_by_date: Dict[Any, List[Dict[str, Any]]] = field(default_factory=dict)
    nominal_by_isin: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    charge_rows_by_date: Dict[Any, List[Dict[str, Any]]] = field(default_factory=dict)
    unknown_causali: Dict[str, List[tuple[int, Sequence]]] = field(default_factory=dict)
    held: Dict[str, Decimal] = field(default_factory=dict)
    succession_rows: List[Tuple[int, SecuritiesRow]] = field(default_factory=list)

    @property
    def evidence_headers(self) -> List[str]:
        return [label for label, _ in self.evidence_cols]

    def asset_id_for(self, *, key: str, name: str, isin: Optional[str]) -> int:
        """Return stable fake ID, upgrading placeholder/truncated names in place."""
        if key in self.asset_to_fake_id:
            existing_id = self.asset_to_fake_id[key]
            known = self.extracted_assets[existing_id]
            current = known.extracted_name or ""
            if (current == isin and name != isin) or is_truncation_of(current, name):
                self.extracted_assets[existing_id] = BRIMExtractedAssetInfo(
                    extracted_symbol=known.extracted_symbol,
                    extracted_isin=known.extracted_isin,
                    extracted_name=name,
                )
            return existing_id

        new_id = self.next_fake_id
        self.asset_to_fake_id[key] = new_id
        self.extracted_assets[new_id] = BRIMExtractedAssetInfo(
            extracted_symbol=None,
            extracted_isin=isin,
            extracted_name=name,
        )
        self.next_fake_id -= 1
        return new_id

    def income_asset_id(self, description: str) -> Optional[int]:
        match = ISIN_RE.search(description.upper())
        if match is None:
            return None
        isin = match.group(0)
        return self.asset_id_for(
            key=f"isin:{isin}",
            name=income_asset_name(description, isin),
            isin=isin,
        )

    def charge_asset_id(self, description: str) -> Optional[int]:
        match = ISIN_RE.search(description.upper())
        if match is None:
            return None
        isin = match.group(0)
        return self.asset_id_for(
            key=f"isin:{isin}",
            name=charge_asset_name(description, isin),
            isin=isin,
        )

    def source_row_evidence(
        self,
        row: Sequence,
        row_num: int,
        *,
        comment: Optional[str] = None,
        title: str = "Riga del file",
    ) -> BRIMEvidence:
        return BRIMEvidence(
            title=title,
            headers=self.evidence_headers,
            rows=[[io.cell_str(row[column]) if column < len(row) else "" for _, column in self.evidence_cols]],
            row_numbers=[row_num],
            comment=comment,
        )

    def build_identity_indexes(self, rows: Sequence[Sequence], header_idx: int, numbers: Sequence[int]) -> None:  # noqa: C901 — explicit prepass guards preserve source-row evidence
        """Prepass: index charges plus coupon-derived ISIN/name/nominal identities (``numbers``: the line of each row, header included)."""
        for row_num, row in zip(numbers[header_idx + 1 :], rows[header_idx + 1 :], strict=True):
            if io.is_blank_row(row):
                continue
            tx_date = io.to_date(io.row_get(row, self.col, "date"))
            causale = io.cell_str(io.row_get(row, self.col, "causale")).upper()
            description = io.cell_str(io.row_get(row, self.col, "descrizione"))
            if tx_date is None:
                continue
            if causale in ACCT_FEETAX_CAUSALI_SECURITIES:
                amount = io.to_decimal_it(io.row_get(row, self.col, "importo"))
                if amount is not None and amount != 0:
                    self.charge_rows_by_date.setdefault(tx_date, []).append(
                        {
                            "row": row,
                            "row_num": row_num,
                            "amount": amount,
                            "description": description,
                        }
                    )
            if causale not in ACCT_INCOME_CAUSALI:
                continue
            isin_match = ISIN_RE.search(description.upper())
            nominal_match = ACCOUNT_NOMINALE_RE.search(description)
            if isin_match is None or nominal_match is None:
                continue
            isin = isin_match.group(0)
            nominal = io.to_decimal_it(nominal_match.group("nominale"))
            if nominal is None or nominal <= 0:
                continue
            name = income_asset_name(description, isin)
            self.income_identity_by_date.setdefault(tx_date, []).append(
                {
                    "isin": isin,
                    "isin_digits": digits_only(isin),
                    "name": name,
                    "nominale": nominal,
                }
            )
            entry = self.nominal_by_isin.setdefault(
                isin,
                {
                    "isin": isin,
                    "name": name,
                    "nominals": set(),
                    "row": row,
                    "row_num": row_num,
                },
            )
            if len(name) > len(entry["name"]):
                entry["name"] = name
            entry["nominals"].add(nominal)

        for entry in self.nominal_by_isin.values():
            entry["norm"] = normalize_trade_name(entry["name"])

    def nominal_candidates_for(self, trade_name: str) -> List[Dict[str, Any]]:
        normalized = normalize_trade_name(trade_name)
        if not normalized:
            return []
        return [entry for entry in self.nominal_by_isin.values() if prefix_matches(normalized, entry["norm"])]

    def charge_rows_near(self, tx_date: Any, *, days: int = 3) -> List[Dict[str, Any]]:
        found: List[Dict[str, Any]] = []
        for delta_days in range(-days, days + 1):
            found.extend(
                self.charge_rows_by_date.get(
                    tx_date + timedelta(days=delta_days),
                    [],
                )
            )
        return sorted(found, key=lambda item: item["row_num"])

    def split_suggestions_for(
        self,
        *,
        tx_date: Any,
        is_buy: bool,
        amount: Decimal,
        currency: str,
        description: str,
        nominal: Optional[Decimal] = None,
    ) -> List[str]:
        hints: List[str] = []
        nearby = self.charge_rows_near(tx_date)
        if nearby:
            listed = ", ".join(f"riga {item['row_num']} ({fmt_money(abs(item['amount']))} {currency})" for item in nearby[:3])
            hints.append("Il file registra già delle spese su titoli a ridosso di questa data — " f"{listed}. Sono transazioni a sé: se le scorpori anche da qui le conti " "due volte.")
        else:
            hints.append("Nei giorni intorno a questa operazione il file non registra nessuna " "riga di commissioni: se una commissione c'è stata, è dentro questo totale.")
        upper = (description or "").upper()
        is_fund = any(token in upper for token in ("SICAV", "FONDO", "FUND", "ETF"))
        if is_fund:
            hints.append("È un fondo, non un'obbligazione: non ci sono ratei cedolari da " "scorporare, quindi la differenza rispetto al prezzo sono commissioni o imposte.")
        elif is_buy:
            hints.append("Se è un'obbligazione e non l'hai comprata all'emissione, il totale " "contiene anche il rateo cedolare che hai rimborsato al venditore: " "registralo come voce a parte, non fa parte del costo del titolo.")
        if nominal is not None and abs(amount) == nominal:
            hints.append("Il totale coincide al centesimo con il valore nominale: è il caso " "tipico dell'acquisto all'emissione, alla pari e senza oneri. Se è " "andata così, non c'è nulla da scorporare.")
        if not is_buy:
            hints.append("Su una vendita l'importo accreditato è già netto: per registrare il " "ricavo lordo scorpora qui le spese trattenute, l'incasso sul conto non cambia.")
        hints.append("I numeri esatti sono sulla nota informativa dell'operazione: da lì leggi " "il controvalore del solo titolo e le singole voci di spesa.")
        return hints

    def try_account_trade(
        self,
        *,
        row: Sequence,
        offset: int,
        tx_date: Any,
        causale: str,
        description: str,
        amount: Decimal,
        currency: str,
        context: str,
    ) -> Optional[Dict[str, Any]]:
        """Resolve one account cash row into a trade when in-file evidence permits."""
        trade_type, direction_reason = classify_trade_direction(description, amount)
        if trade_type is None:
            return {"reason": direction_reason}

        trade_name = trade_asset_name(description)
        if not trade_name:
            return {"reason": "no_name", "type": trade_type}

        candidates = self.nominal_candidates_for(trade_name)
        if not candidates:
            return {"reason": "no_quantity", "type": trade_type, "name": trade_name}
        if len(candidates) > 1:
            return {
                "reason": "ambiguous_name",
                "type": trade_type,
                "name": trade_name,
                "candidates": candidates,
            }
        identity = candidates[0]
        if len(identity["nominals"]) > 1:
            return {
                "reason": "ambiguous_nominal",
                "type": trade_type,
                "name": trade_name,
                "candidates": candidates,
            }

        nominal: Decimal = next(iter(identity["nominals"]))
        best_name = identity["name"] if len(identity["name"]) >= len(trade_name) else trade_name
        asset_id = self.asset_id_for(
            key=f"isin:{identity['isin']}",
            name=best_name,
            isin=identity["isin"],
        )
        is_buy = trade_type == TransactionType.BUY
        created = self.provider._create_transaction(
            row_num=offset,
            transactions=self.transactions,
            validation_issues=self.validation_issues,
            context=context,
            broker_id=self.broker_id,
            asset_id=asset_id,
            type=trade_type,
            date=tx_date,
            quantity=nominal if is_buy else -nominal,
            cash=Currency(
                code=currency,
                amount=-abs(amount) if is_buy else abs(amount),
            ),
            description=(description or causale)[:500],
            tags=[
                "import",
                "credit_agricole",
                slug_causale(causale),
                "account_trade",
            ],
        )
        if created is None:
            return None

        delta = abs(amount) - nominal
        verb = "acquisto" if is_buy else "vendita"
        if not is_buy:
            self.field_todos.append(
                BRIMFieldTodo(
                    tx_index=len(self.transactions) - 1,
                    field="quantity",
                    severity="warning",
                    reason_code="ca_account_trade_sell_quantity_presumed",
                    message=(f"Riga {offset}: vendita di {best_name}. Ho usato " f"{fmt_money(nominal)} come quantità, cioè il valore nominale " "che risulta dalle cedole. Se hai venduto solo una parte, correggila."),
                    context={
                        "causale": causale,
                        "row": offset,
                        "isin": identity["isin"],
                        "nominale": str(nominal),
                    },
                    evidence=[
                        self.source_row_evidence(
                            row,
                            offset,
                            comment=("Il file dice quanto denaro è entrato, non quante quote " f"sono uscite. Le cedole di {identity['isin']} riportano " f"un nominale di {nominal}: è la posizione, quindi è " "giusto solo se hai venduto tutto."),
                        )
                    ],
                )
            )
        if not is_buy:
            trade_comment = f"Sul conto sono entrati {fmt_money(abs(amount))} {currency}, ed è un " "importo netto: le spese sulla vendita sono già state trattenute e il file " "non le espone. Il ricavo lordo e le singole spese non sono quindi " "ricavabili da questa riga."
        elif delta != 0:
            trade_comment = (
                f"Dal conto sono usciti {fmt_money(abs(amount))} {currency}. Guardando "
                "il resto del file ho trovato una cedola dello stesso titolo "
                f"(riga {identity['row_num']}) che dichiara {fmt_money(nominal)} di "
                "valore nominale, cioè il capitale del titolo. I due numeri non "
                f"coincidono ({fmt_money(abs(delta))} {currency} di differenza): il "
                "totale di questa riga mette insieme il prezzo del titolo, il rateo "
                "cedolare maturato e le eventuali commissioni, e il file non li separa. "
                "La cassa è comunque giusta; è il costo di carico a essere approssimato."
            )
        else:
            trade_comment = (
                f"Dal conto sono usciti {fmt_money(abs(amount))} {currency}, esattamente "
                "quanto il valore nominale dichiarato dalla cedola alla riga "
                f"{identity['row_num']}. È il caso dell'acquisto all'emissione, alla pari "
                "e senza oneri: se è andata così non c'è nulla da correggere. Se invece "
                "la nota informativa espone commissioni o rateo, il file li ha inglobati "
                "qui dentro."
            )
        self.field_todos.append(
            BRIMFieldTodo(
                tx_index=len(self.transactions) - 1,
                field="cash",
                severity="warning",
                reason_code="ca_account_trade_bundled_amount",
                message=(f"Riga {offset}: {verb} di {best_name} — l'importo di questa riga " "potrebbe raggruppare più voci insieme."),
                context={
                    "causale": causale,
                    "row": offset,
                    "isin": identity["isin"],
                    "cash": str(abs(amount)),
                    "nominale": str(nominal),
                    "delta": str(delta),
                    "currency": currency,
                    "nominale_row": identity["row_num"],
                    "compare_nominal": is_buy,
                    "split_hint": "trade_charges",
                    "split_suggestions": self.split_suggestions_for(
                        tx_date=tx_date,
                        is_buy=is_buy,
                        amount=amount,
                        currency=currency,
                        description=description,
                        nominal=nominal,
                    ),
                },
                evidence=[
                    self.source_row_evidence(
                        row,
                        offset,
                        title=f"Riga di {verb}",
                        comment=trade_comment,
                    ),
                    self.source_row_evidence(
                        identity["row"],
                        identity["row_num"],
                        title="Cedola che ha fornito il nominale",
                        comment=(f"L'ISIN {identity['isin']} e il valore nominale " f"{fmt_money(nominal)} vengono da qui: è il capitale del " "titolo, cioè quanto la banca rimborsa a scadenza, non quanto " "hai pagato."),
                    ),
                ],
            )
        )
        return None

    @staticmethod
    def trade_fallback_message(
        offset: int,
        info: Dict[str, Any],
        booked_as: str,
    ) -> tuple[str, str]:
        reason = info.get("reason")
        name = info.get("name") or ""
        if reason == "sign_mismatch":
            return (
                f"Riga {offset}: la descrizione e il segno dell'importo si contraddicono. Verifica l'operazione e completala.",
                "La descrizione parla di acquisto ma il denaro entra (o viceversa). Non tipizzo su un dato che si contraddice: " f"l'ho registrata come {booked_as} di cassa. Apri la transazione, scegli il tipo giusto e il titolo.",
            )
        if reason == "ambiguous_name":
            names = ", ".join(f"{candidate['name']} ({candidate['isin']})" for candidate in info.get("candidates", []))
            return (
                f"Riga {offset}: '{name}' corrisponde a più titoli. Scegli quello giusto e la quantità.",
                f"Il nome nella riga combacia con più titoli presenti nel file: {names}. Scegliere al posto tuo significherebbe " f"rischiare una posizione sbagliata, quindi l'ho registrata come {booked_as} di cassa.",
            )
        if reason == "ambiguous_nominal":
            return (
                f"Riga {offset}: per '{name}' le cedole riportano nominali diversi. Inserisci la quantità giusta.",
                "Le cedole di questo titolo non concordano su un unico nominale (la posizione è cambiata nel tempo), quindi non " f"posso ricavarne la quantità dell'operazione. L'ho registrata come {booked_as} di cassa.",
            )
        if reason == "no_quantity":
            return (
                f"Riga {offset}: operazione su '{name}' senza quantità ricavabile. Scegli il titolo e inserisci la quantità.",
                f"Questa riga è un'operazione su titoli e il titolo si legge ('{name}'), ma la quantità no: nel file non ci sono " f"cedole di questo strumento da cui ricavarla (i fondi non ne staccano). L'importo è giusto, l'ho registrata come {booked_as} di cassa.",
            )
        if reason == "fund_redemption":
            return (
                f"Riga {offset}: sembra il disinvestimento di '{name}', arrivato come bonifico. Scegli il fondo e inserisci le quote vendute.",
                f"Il denaro arriva da '{name}' e la causale parla di rimborso sullo stesso fondo: è un disinvestimento pagato per bonifico, "
                f"non un accredito qualsiasi. Le quote vendute il file non le dice — un fondo riporta il controvalore, non il numero di quote — "
                f"quindi l'ho registrata come {booked_as} di cassa. Cambiala in vendita, scegli il fondo e inserisci le quote: "
                "altrimenti la posizione resta aperta per sempre.",
            )
        return (
            f"Riga {offset}: operazione su titoli registrata come movimento di cassa perché da questo file non ricavo quantità e strumento. Verificala e completala.",
            "Questa riga è un'operazione su titoli, ma la descrizione non riporta quantità né codice del titolo. " f"L'ho registrata come {booked_as} di cassa: l'importo è giusto, il titolo manca. " "Apri la transazione, cambia il tipo in acquisto o vendita e scegli il titolo.",
        )

    # ------------------------------------------------------------------ the sheet and the assets

    def read_sheet(self, rows: Sequence[AccountRow], numbers: Sequence[int]) -> None:
        """Index the account rows: ``numbers`` are their lines in the combined file, the numbers the user sees."""
        sheet = [list(ACCOUNT_SHEET_HEADER), *(sheet_row(row) for row in rows)]
        self.build_identity_indexes(sheet, 0, [0, *numbers])

    def read_positions(self, rows: Sequence[SecuritiesRow]) -> None:
        """The nominal held per security, from the securities rows that are imported: a maturity reports ``0`` and closes what is held."""
        for row in rows:
            key = row.name.lower()
            if not key:
                continue
            if row.causale in BUY_CAUSALI or row.causale in SUCCESSION_CAUSALI:
                self.held[key] = self.held.get(key, ZERO) + abs(row.qty or ZERO)
            elif row.causale == "FONDI: RIMBORSO":
                self.held[key] = self.held.get(key, ZERO) - abs(row.qty or ZERO)

    def name_asset_id(self, name: str) -> int:
        """The id of a security the securities export names (it carries no ISIN)."""
        key = f"name:{name.lower()}"
        if key in self.asset_to_fake_id:
            return self.asset_to_fake_id[key]
        new_id = self.next_fake_id
        self.asset_to_fake_id[key] = new_id
        self.extracted_assets[new_id] = BRIMExtractedAssetInfo(extracted_symbol=None, extracted_isin=None, extracted_name=name)
        self.next_fake_id -= 1
        return new_id

    def link_isin(self, isin: str, name: str) -> None:
        """A pair says that the security ``name`` of the securities export is ``isin``: a row of the account that names that ISIN is the same asset."""
        asset_id = self.name_asset_id(name)
        key = f"isin:{isin}"
        if key in self.asset_to_fake_id:
            return
        self.asset_to_fake_id[key] = asset_id
        known = self.extracted_assets[asset_id]
        self.extracted_assets[asset_id] = BRIMExtractedAssetInfo(extracted_symbol=known.extracted_symbol, extracted_isin=isin, extracted_name=known.extracted_name)

    # ------------------------------------------------------------------ the account arm

    def book_account_row(self, row: Sequence[str], offset: int) -> None:  # noqa: C901 — the causale dispatch the plugin has always had, one row at a time
        """Book one account row on its own: the "Lista Movimenti Conto" rule, unchanged since 1.0."""
        if io.is_blank_row(row):
            return
        tx_date = io.to_date(io.row_get(row, self.col, "date"))
        causale = io.cell_str(io.row_get(row, self.col, "causale")).upper()
        description = io.cell_str(io.row_get(row, self.col, "descrizione"))
        amount = io.to_decimal_it(io.row_get(row, self.col, "importo"))
        if tx_date is None and is_recap_footer(description):
            return  # expected end-of-export recap totals (XLSX only)
        if tx_date is None or not causale:
            return  # non-movement leftover (blank/meta) — not a real movement

        if amount is None:
            self.warnings.append(
                BRIMNotice(
                    severity="warning",
                    code="ca_account_invalid_amount",
                    message=f"Riga {offset}: importo non valido per '{causale}', saltata",
                    context={"causale": causale, "row": offset, "report_issue": True},
                    evidence=[self.source_row_evidence(row, offset, comment="L'importo di questa riga non è leggibile come numero, quindi la riga è stata scartata.")],
                )
            )
            return
        if amount == 0:
            return

        currency = io.cell_str(io.row_get(row, self.col, "divisa")) or "EUR"
        context = f"{causale}: {description}" if description else causale

        if causale in ACCT_MATURITY_CAUSALI and amount > 0:
            maturity_match = ACCOUNT_MATURITY_RE.search(description)
            maturity_code = digits_only(maturity_match.group("code")) if maturity_match else ""
            maturity_name = maturity_match.group("name").strip() if maturity_match else description
            identity = next((item for item in self.income_identity_by_date.get(tx_date, []) if maturity_code and maturity_code in item["isin_digits"]), None)
            if identity is None:
                # No same-day coupon carries this security's ISIN + NOMINALE, so we
                # cannot split par principal from any premium. Book the whole redemption
                # as a SELL at par — everything treated as the bond's disposal, no
                # INTEREST leg — instead of external cash, so it reduces a position and
                # never inflates paid-in capital (consistent with the securities-export
                # fallback at ``_parse_securities``). With no position and no reported
                # price we assume a par (100) redemption, so the derived nominal equals
                # the cash (quantity < 0); flag it for the user to verify.
                self.warnings.append(
                    BRIMNotice(
                        severity="warning",
                        code="ca_account_maturity_unlinked",
                        message=f"Riga {offset}: scadenza/rimborso '{description}' non collegabile a un titolo (ISIN e nominale non trovati nella stessa data); importata interamente come vendita a valore nominale (par 100, nessuna quota di interesse) — verifica il nominale.",
                        context={"causale": causale, "row": offset},
                        evidence=[self.source_row_evidence(row, offset, comment="Per scorporare il capitale dal premio mi serve il nominale, che di solito ricavo dalla cedola pagata lo stesso giorno. Qui quella cedola non c'è, quindi ho trattato tutto l'importo come rimborso alla pari.")],
                    )
                )
                model = io.model_bond_maturity(ctv=abs(amount), price=Decimal(100), held_qty=None)
                fallback_asset_id = self.asset_id_for(key=f"maturity:{maturity_code or maturity_name}", name=maturity_name, isin=None) if maturity_name else None
                self.provider._create_transaction(
                    row_num=offset,
                    transactions=self.transactions,
                    validation_issues=self.validation_issues,
                    context=context,
                    broker_id=self.broker_id,
                    asset_id=fallback_asset_id,
                    type=TransactionType.SELL,
                    date=tx_date,
                    quantity=-model.nominal,
                    cash=Currency(code=currency, amount=model.principal_cash),
                    description=f"[{causale} — rimborso/scadenza da conto, titolo non identificato] {maturity_name} (source: {description}; venduto interamente a par {model.par_price}, nominale derivato {model.nominal})"[:500],
                    tags=["import", "credit_agricole", slug_causale(causale), "account_maturity"],
                )
                return
            else:
                nominale = identity["nominale"]
                # Reuse the shared bond-redemption model (par principal + surplus-as-INTEREST),
                # the same knowledge already used by the securities export and Fineco. The nominal
                # is recovered in-file from the same-day coupon (self.income_identity_by_date), never the DB.
                model = io.model_bond_maturity(ctv=abs(amount), price=None, held_qty=nominale)
                asset_id = self.asset_id_for(key=f"isin:{identity['isin']}", name=identity["name"] or maturity_name, isin=identity["isin"])
                sell_description = f"[{causale} — rimborso/scadenza da conto] {identity['name'] or maturity_name} (source: {description}; redeemed at par {model.par_price}, nominal {model.nominal})"
                created = self.provider._create_transaction(
                    row_num=offset,
                    transactions=self.transactions,
                    validation_issues=self.validation_issues,
                    context=context,
                    broker_id=self.broker_id,
                    asset_id=asset_id,
                    type=TransactionType.SELL,
                    date=tx_date,
                    quantity=-model.nominal,
                    cash=Currency(code=currency, amount=model.principal_cash),
                    description=sell_description[:500],
                    tags=["import", "credit_agricole", slug_causale(causale), "account_maturity"],
                )
                if created is not None and model.surplus_cash > 0:
                    self.provider._create_transaction(
                        row_num=offset,
                        transactions=self.transactions,
                        validation_issues=self.validation_issues,
                        context=f"Maturity premium for {identity['name'] or maturity_name}",
                        broker_id=self.broker_id,
                        asset_id=asset_id,
                        type=TransactionType.INTEREST,
                        date=tx_date,
                        quantity=Decimal("0"),
                        cash=Currency(code=currency, amount=model.surplus_cash),
                        description=f"[{causale} — premio/rivalutazione da conto] {identity['name'] or maturity_name} (source: {description}; surplus over par {model.surplus_cash})"[:500],
                        tags=["import", "credit_agricole", slug_causale(causale), "maturity_premium"],
                    )
                return

        trade_fallback: Optional[Dict] = None
        if causale in ACCT_UNRESOLVED_CAUSALI:
            trade_fallback = self.try_account_trade(
                row=row,
                offset=offset,
                tx_date=tx_date,
                causale=causale,
                description=description,
                amount=amount,
                currency=currency,
                context=context,
            )
            if trade_fallback is None:
                return  # booked as a real trade — nothing left to fall back on
        elif causale in ACCT_SCT_CAUSALI and amount > 0:
            # A fund redemption paid by wire. The name is readable, the number of
            # units never is: a fund states the countervalue, not the quantity, and
            # this layout has no coupon to recover it from. Straight to the fallback
            # so the user supplies the quantity in the correction step.
            fund_name = sct_fund_redemption_name(description)
            if fund_name:
                trade_fallback = {"reason": "fund_redemption", "type": TransactionType.SELL, "name": fund_name}

        tx_type, cash, tier = classify_account_row(causale, description, amount, currency)
        # Coupons (INTEREST) and dividends both name their security by ISIN — link the
        # income to that bond/fund so it shows under the asset in the FIFO lot detail.
        # Bank credit interest ("INTERESSI/COMPETENZE" credit) carries no ISIN and stays
        # unallocated (income_asset_id returns None).
        # A charge on a securities operation names its security by ISIN as often as a
        # coupon does ("SPESE STACCO CEDOLA ... TIT: IT000..."), so look it up the same
        # way: a fee attached to the bond it was charged for lands in that bond's cost
        # basis instead of drifting into unallocated account expenses.
        if tx_type in (TransactionType.INTEREST, TransactionType.DIVIDEND):
            asset_id = self.income_asset_id(description)
        elif tx_type in (TransactionType.FEE, TransactionType.TAX):
            asset_id = self.charge_asset_id(description)
        else:
            asset_id = None

        # B4 — the coupon reaches us already netted, but the file spells out the
        # withholding it suffered ("RITENUTA: 13,36"). Import the *gross* income and
        # book the tax as its own leg: the two sum back to the netted amount, so the
        # cash balance still matches the bank's Saldo Finale, while the tax stops
        # being invisible. Only on real income: a clawback (negative "CEDOLA") is
        # classified as cash and grossing it up would invent a refund.
        withholding: Optional[Decimal] = None
        if tx_type in (TransactionType.INTEREST, TransactionType.DIVIDEND) and amount > 0:
            withholding_match = ACCOUNT_RITENUTA_RE.search(description)
            if withholding_match is not None:
                parsed = io.to_decimal_it(withholding_match.group("ritenuta"))
                if parsed is not None and parsed > 0:
                    withholding = parsed
                    cash = Currency(code=currency, amount=cash.amount + withholding)

        created = self.provider._create_transaction(
            row_num=offset,
            transactions=self.transactions,
            validation_issues=self.validation_issues,
            context=context,
            broker_id=self.broker_id,
            asset_id=asset_id,
            type=tx_type,
            date=tx_date,
            quantity=Decimal("0"),
            cash=cash,
            description=(description or causale)[:500],
            tags=["import", "credit_agricole", slug_causale(causale)],
        )

        if created is None:
            return

        if withholding is not None:
            self.provider._create_transaction(
                row_num=offset,
                transactions=self.transactions,
                validation_issues=self.validation_issues,
                context=f"Withholding tax on {context}",
                broker_id=self.broker_id,
                asset_id=asset_id,
                type=TransactionType.TAX,
                date=tx_date,
                quantity=Decimal("0"),
                cash=Currency(code=currency, amount=-withholding),
                description=f"[{causale} — ritenuta] {description}"[:500],
                tags=["import", "credit_agricole", slug_causale(causale), "withholding_tax"],
            )

        if tier == TIER_UNRESOLVED:
            # The money is right, the security (or its quantity) is missing. Block
            # rather than guess: a silent withdrawal loses the position entirely, and
            # the loss only surfaces much later as an unexplained gap in the cost basis.
            booked_as = "prelievo" if tx_type == TransactionType.WITHDRAWAL else "versamento"
            todo_message, todo_comment = self.trade_fallback_message(offset, trade_fallback or {}, booked_as)
            self.field_todos.append(
                BRIMFieldTodo(
                    tx_index=len(self.transactions) - 1,
                    field="asset_id",
                    severity="blocker",
                    reason_code="ca_account_trade_unresolved",
                    message=todo_message,
                    context={
                        "causale": causale,
                        "row": offset,
                        "reason": (trade_fallback or {}).get("reason", "no_keyword"),
                        # Same affordance as a resolved trade: this row is a trade too,
                        # only a less complete one, and the total it carries is bundled
                        # for exactly the same reason. The correction step shows the
                        # split zone once the user has supplied type, asset and quantity.
                        "split_hint": "trade_charges",
                        "cash": str(abs(amount)),
                        "currency": currency,
                        "compare_nominal": False,
                        "split_suggestions": self.split_suggestions_for(tx_date=tx_date, is_buy=amount < 0, amount=amount, currency=currency, description=description),
                    },
                    evidence=[self.source_row_evidence(row, offset, comment=todo_comment)],
                )
            )
        elif tier == TIER_UNKNOWN:
            self.unknown_causali.setdefault(causale, []).append((offset, row))

        # A charge on a securities operation belongs to the security it was charged
        # for. This layout names neither, so the charge lands unallocated and silently
        # skews the cost basis of whatever it belonged to. Flagged as a warning, not a
        # blocker: the file may genuinely never say, and a fee is still a real expense.
        if causale in ACCT_FEETAX_CAUSALI_SECURITIES and tx_type in (TransactionType.FEE, TransactionType.TAX) and asset_id is None:
            self.field_todos.append(
                BRIMFieldTodo(
                    tx_index=len(self.transactions) - 1,
                    field="asset_id",
                    severity="warning",
                    reason_code="ca_account_charge_unallocated",
                    message=f"Riga {offset}: spesa su operazione titoli non collegata a nessun titolo. Assegnala al titolo giusto, oppure tienila così se riguarda il conto.",
                    context={"causale": causale, "row": offset},
                    evidence=[
                        self.source_row_evidence(
                            row,
                            offset,
                            comment=(
                                "Questa è una spesa o imposta su un'operazione in titoli, ma la descrizione non dice su quale. "
                                "Resta a carico del conto invece che del titolo, e il costo di carico di quel titolo risulta più basso del reale. "
                                "Scegli il titolo a cui appartiene, oppure tienila com'è se è una spesa di conto."
                            ),
                        )
                    ],
                )
            )

    # ------------------------------------------------------------------ the securities arms

    def book_transfer_in(self, row: SecuritiesRow, offset: int) -> None:
        """Securities transferred from a dossier that LibreFolio does not track.

        This is the receiving leg of a transfer whose paying leg lives on another, untracked account, so NO money was spent
        here. It is an ADJUSTMENT that seeds the position and carries the per-unit book price via ``cost_basis_override``
        (bond/fund price convention). No DEPOSIT is emitted, so paid-in capital is not inflated; each leg keeps its own price.
        """
        name = row.name
        quantity = abs(row.qty) if row.qty is not None else ZERO
        cost_override: Optional[Currency] = None
        cost_basis_mode: Optional[str] = None
        if row.price is not None and quantity > 0:
            # A bond's price is a percentage of its nominal: the per-unit cost is computed, so it is rounded explicitly to what
            # the column keeps (C-97, decision D6); another price is the file's, as read.
            unit_cost = round_computed_value(row.price / Decimal(100), Transaction, "cost_basis_override") if is_bond(name) else row.price
            cost_override = Currency(code=row.currency, amount=unit_cost)
            cost_basis_mode = "manual"
        description = f"[{row.causale} — successione / transfer-in] {name} (price {row.price}, qty {quantity})"
        self.succession_rows.append((offset, row))
        self.provider._create_transaction(
            row_num=offset,
            transactions=self.transactions,
            validation_issues=self.validation_issues,
            context=description,
            broker_id=self.broker_id,
            asset_id=self.name_asset_id(name) if name else None,
            type=TransactionType.ADJUSTMENT,
            date=row.op,
            quantity=quantity,
            cash=None,
            cost_basis_mode=cost_basis_mode,
            cost_basis_override=cost_override,
            description=description[:500],
            tags=list(TAGS),
        )

    def book_movement(self, row: SecuritiesRow, offset: int, cash: Decimal, account: Optional[AccountRow] = None) -> None:  # noqa: C901 — one arm per securities class
        """Book a coupon, a purchase, a fund redemption or a maturity; ``cash`` is the amount the bank moved (``account``: its row).

        The cash is the account's, so nothing balances it. A coupon is booked gross when the account row spells out its
        withholding: the two sum back to the net amount the bank credited, and the tax stops being invisible.
        """
        name, currency, causale = row.name, row.currency, row.causale
        amount = abs(cash)
        description = f"{causale}: {name}"
        tx_type: TransactionType
        quantity = ZERO
        booked: Optional[Currency]
        withholding: Optional[Decimal] = None
        surplus: Optional[Decimal] = None
        derived_quantity = False
        if row.klass == "coupon":
            tx_type = TransactionType.INTEREST
            withholding = account_withholding(account) if account is not None else None
            booked = Currency(code=currency, amount=amount + (withholding or ZERO))
        elif row.klass == "buy":
            tx_type = TransactionType.BUY
            quantity = abs(row.qty) if row.qty is not None else ZERO
            booked = Currency(code=currency, amount=-amount)
        elif row.klass == "redeem":
            tx_type = TransactionType.SELL
            quantity = -abs(row.qty) if row.qty is not None else ZERO
            booked = Currency(code=currency, amount=amount)
        else:  # matured: a bond redeemed at par, whatever the bank credited above par is a premium
            tx_type = TransactionType.SELL
            held = self.held.get(name.lower(), ZERO) if name else ZERO
            model = io.model_bond_maturity(ctv=amount, price=row.price, held_qty=held if held > 0 else None)
            if model.nominal > 0:
                quantity = -model.nominal
                booked = Currency(code=currency, amount=model.principal_cash)
                surplus = model.surplus_cash
                derived_quantity = model.source == "derived"
                description = f"{causale}: {name} (redeemed at par {model.par_price}, nominal {model.nominal} [{model.source}]" + (f", premium {model.surplus_cash})" if model.surplus_cash > 0 else ")")
            else:
                booked = Currency(code=currency, amount=amount)
                quantity = -abs(row.qty) if row.qty is not None else ZERO
        asset_id = self.name_asset_id(name) if name else None
        created = self.provider._create_transaction(
            row_num=offset,
            transactions=self.transactions,
            validation_issues=self.validation_issues,
            context=description,
            broker_id=self.broker_id,
            asset_id=asset_id,
            type=tx_type,
            date=row.op,
            quantity=quantity,
            cash=booked,
            description=description[:500],
            tags=list(TAGS),
        )
        if created is None:
            return
        if derived_quantity:
            self.field_todos.append(
                BRIMFieldTodo(
                    tx_index=len(self.transactions) - 1,
                    field="quantity",
                    severity="warning",
                    reason_code="derived_quantity",
                    message=f"Obbligazione scaduta '{name}': nel file non c'è la posizione di partenza (per esempio perché l'estratto è parziale), quindi il nominale è ricavato da controvalore e prezzo. Verifica che corrisponda alla posizione che stai chiudendo.",
                    context={"causale": causale, "ctv": str(amount), "price": str(row.price)},
                )
            )
        if surplus is not None and surplus > 0:
            # What the bank credited above par (premio fedeltà, a revaluation): income, like a coupon; the SELL stays at par.
            self.provider._create_transaction(
                row_num=offset,
                transactions=self.transactions,
                validation_issues=self.validation_issues,
                context=f"Maturity premium for {name}",
                broker_id=self.broker_id,
                asset_id=asset_id,
                type=TransactionType.INTEREST,
                date=row.op,
                quantity=ZERO,
                cash=Currency(code=currency, amount=abs(surplus)),
                description=f"[TITOLI SCADUTI — premio/rivalutazione a scadenza] {name} (surplus over par {surplus})"[:500],
                tags=[*TAGS, "maturity_premium"],
            )
        if withholding is not None and account is not None:
            self.provider._create_transaction(
                row_num=offset,
                transactions=self.transactions,
                validation_issues=self.validation_issues,
                context=f"Withholding tax on {description}",
                broker_id=self.broker_id,
                asset_id=asset_id,
                type=TransactionType.TAX,
                date=row.op,
                quantity=ZERO,
                cash=Currency(code=currency, amount=-withholding),
                description=f"[{account.causale} — ritenuta] {account.description}"[:500],
                tags=[*TAGS, slug_causale(account.causale), "withholding_tax"],
            )

    # ------------------------------------------------------------------ what the rows say once all are booked

    def notices(self) -> List[BRIMNotice]:
        """The notices the rows booked raise together: the transfers, and the causali the plugin has never seen."""
        found: List[BRIMNotice] = []
        if self.succession_rows:
            # Describes correct, intentional behaviour, so it is INFO, not a warning. This raw wording is the Italian fallback: the
            # frontend prefers the localised `importWizard.brimNotice.ca_succession_transfer_in`, keyed on `code` and interpolated
            # with `context` — a plugin runs backend-side and cannot know the reader's locale.
            found.append(
                BRIMNotice(
                    severity="info",
                    code="ca_succession_transfer_in",
                    message=(
                        f"Sono stati identificati dei titoli trasferiti da un altro dossier ({len(self.succession_rows)} righe).\n"
                        "Sono stati registrati come transazioni di tipo «Rettifica» perché non hanno un movimento di cassa "
                        "associato: si suppone quindi che fossero già tuoi presso un altro broker.\n"
                        "In caso affermativo, e se quel broker è tracciato su LibreFolio, importando l'altra metà della "
                        "transazione il sistema proporrà di collegare le due e di trasformarle in un «Trasferimento titoli».\n"
                        "Di seguito le righe in dettaglio:"
                    ),
                    context={"row_count": len(self.succession_rows)},
                    evidence=[
                        BRIMEvidence(
                            title="Righe di trasferimento",
                            headers=list(SECURITIES_EVIDENCE_HEADERS),
                            rows=[[row.cells.get(label, "") for label in SECURITIES_EVIDENCE_HEADERS] for _, row in self.succession_rows],
                            row_numbers=[number for number, _ in self.succession_rows],
                            comment="Ogni riga qui sotto è un versamento titoli senza contropartita di cassa: nessun denaro è uscito dal conto, quindi la posizione è stata aperta come «Rettifica».",
                        )
                    ],
                )
            )
        if self.unknown_causali:
            # Not an error: the cash is booked correctly by sign. It is a disclosure — a causale the registry has never seen may
            # well be a securities operation in disguise, exactly like COMPRAVENDITA was.
            total_rows = sum(len(items) for items in self.unknown_causali.values())
            found.append(
                BRIMNotice(
                    severity="info",
                    code="ca_unknown_causale",
                    message=(f"{total_rows} righe con {len(self.unknown_causali)} causali non ancora previste sono state registrate come versamento o prelievo, in base al segno dell'importo. " "Se una di queste è in realtà un'operazione su titoli, correggila prima di importare."),
                    context={"causali": sorted(self.unknown_causali), "row_count": total_rows, "report_issue": True},
                    evidence=[
                        BRIMEvidence(
                            title="Righe con causale non prevista",
                            headers=self.evidence_headers,
                            rows=[[io.cell_str(r[cidx]) if cidx < len(r) else "" for _, cidx in self.evidence_cols] for items in self.unknown_causali.values() for _, r in items],
                            row_numbers=[num for items in self.unknown_causali.values() for num, _ in items],
                        )
                    ],
                )
            )
        return found

    def attach_maturity_notices(self) -> None:
        attach_maturity_notices(self.transactions, self.extracted_assets, reason=MATURITY_NOTICE_REASON)
