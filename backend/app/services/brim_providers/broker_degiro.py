"""
DEGIRO Broker Report Import Plugin.

Reads DEGIRO's **Account Statement** (Inbox → Account Statement → CSV, usually ``Account.csv``)
in any language. The export has the same twelve columns in every language, so they are read by
position, never by name:

    1 date · 2 time · 3 value date · 4 product · 5 ISIN · 6 description · 7 FX rate ·
    8 currency of the change · 9 change amount (unnamed) · 10 balance currency ·
    11 balance (unnamed, ignored) · 12 Order Id

A row whose date and time are empty continues the row above: DEGIRO wraps a long Order Id or
description onto the next line, so its cells are appended to the previous row's.

**How rows are classified**, in this order:

1. No amount → an information line, skipped.
2. **Currency conversions.** A row with an FX rate is one leg; its partner is the row of the same
   order (same Order Id, or the same date and time when there is none) in another currency with
   the opposite sign — the adjacent one when several qualify. The rate itself is never used: a BRIM
   plugin ignores the report's exchange-rate column. Both legs become ``FX_CONVERSION`` with one
   deterministic ``link_uuid`` and one shared description, as the batch requires of a pair.
3. **Trades.** ISIN, Order Id and a description that starts with ``<verb> <quantity> …@<price> <CCY>``
   (or the old German ``zu je``): the sign of the amount gives the direction, so any language works.
4. A trade written after a ``PREFIX:`` is a corporate action (product change, split, merger, stock
   dividend…): not imported, listed in a warning.
5. **Order costs.** The other negative rows of an order are fees; transaction taxes (stamp duty,
   ``Transactiebelasting``) are taxes.
6. Any other zero-amount row about a product is listed in a warning; without a product it is skipped.
7. A multilingual word table — every language on every row, because DEGIRO mixes languages in one
   file — for taxes (before dividends), dividends, promotions and interest, fees, deposits and
   withdrawals; internal rows (cash sweep, flatex transfers, reservations) are skipped silently.
8. Anything else is listed in a warning with its source row.

**Numbers**: the decimal mark is decided per value when it is certain, and by the file's own mark
only for the ambiguous ``1.000`` / ``49,785`` (one separator followed by exactly three digits).

**Warning language follows the input format**: the header decides between English, Dutch, German,
French and Spanish messages; any other language gets English. The notice codes (``degiro_*``) have
no ``importWizard.brimNotice.*`` key on purpose, so the file's language reaches the user.

The **Transactions** export (the list of orders) is recognised as DEGIRO's too: it imports nothing
and says to export the Account Statement instead.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import structlog
from pydantic import ValidationError

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMEvidence, BRIMExtractedAssetInfo, BRIMNotice, BRIMParseOutput, BRIMValidationIssue
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.brim_providers._brim_io import read_rows, to_decimal_it, to_decimal_plain
from backend.app.services.provider_registry import BRIMProviderRegistry, register_provider

logger = structlog.get_logger(__name__)

# =============================================================================
# LAYOUT
# =============================================================================

DATE_FORMAT = "%d-%m-%Y"
_STATEMENT_COLUMNS = 12
_ORDERS_MIN_COLUMNS = 16
_DATE, _TIME, _VALUE_DATE, _PRODUCT, _ISIN, _DESCRIPTION, _FX, _CURRENCY, _AMOUNT, _BALANCE_CURRENCY, _BALANCE, _ORDER_ID = range(_STATEMENT_COLUMNS)

_DATE_RE = re.compile(r"^\d{2}-\d{2}-\d{4}$")
_OTHER_MARK = {",": ".", ".": ","}
_TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")
_TAGS = ("import", "degiro")
_LINK_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "librefolio:brim:broker_degiro:fx-pair")

# A trade: ``<verb> <quantity>`` then ``… @ <price>`` (``Koop 1 @ 33,9 USD``, ``Buy 5 APPLE INC@180,25 USD``)
# or the old German ``Kauf 4 zu je 12,5 EUR``. The quantity takes ``.``/``,`` grouping, never spaces,
# so a product name starting with digits (``Buy 5 888 HOLDINGS@…``) does not swallow it.
_QUANTITY = r"(?P<qty>\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)(?=[\s@])"
_TRADE_RE = re.compile(rf"^[^\W\d_]+\s+{_QUANTITY}(?:[^@]*@\s*\d|\s+zu\s+je\s+\d)", re.IGNORECASE)
# ``PRODUCTWIJZIGING : Koop 500 @ …``, ``STOCK DIVIDEND: Koop 999 @ 0 EUR``: a trade after a label.
_PREFIX_RE = re.compile(r"^[^:]{2,}:\s*(?P<rest>.+)$")

# =============================================================================
# LANGUAGE (of the messages only: rows are classified in every language)
# =============================================================================

# Header names per language, folded (lowercase, no accents), Account Statement and orders list.
# Sources: plan 31_brimDegiro §1.8 (open-source importers, each string cited there).
_HEADER_WORDS: Dict[str, frozenset] = {
    "en": frozenset({"date", "time", "value date", "product", "description", "change", "balance", "order id", "reference exchange", "venue", "quantity", "price", "local value", "exchange rate", "autofx fee"}),
    "nl": frozenset({"datum", "tijd", "valutadatum", "product", "omschrijving", "mutatie", "saldo", "order id", "beurs", "uitvoeringsplaats", "aantal", "koers", "lokale waarde", "wisselkoers", "autofx kosten"}),
    "de": frozenset({"datum", "uhrzeit", "valutadatum", "produkt", "beschreibung", "anderung", "saldo", "order-id", "referenzborse", "ausfuhrungsort", "anzahl", "kurs", "wert in lokalwahrung", "wechselkurs", "autofx-gebuhr"}),
    "fr": frozenset({"date", "heure", "date de", "produit", "description", "mouvements", "solde", "id ordre", "bourse de reference", "lieu d'execution", "quantite", "cours", "valeur locale", "taux de change", "frais autofx"}),
    "es": frozenset({"fecha", "hora", "fecha valor", "producto", "descripcion", "tipo", "variacion", "saldo", "id orden", "bolsa de referencia", "centro de ejecucion", "numero", "precio", "valor local", "tipo de cambio", "comision autofx"}),
}
_MIN_LANGUAGE_MATCHES = 3

_MESSAGES: Dict[str, Dict[str, str]] = {
    "en": {
        "evidence_title": "Source rows",
        "degiro_unknown_rows": "{n} rows were not recognised and were not imported: check them in the source rows below.",
        "degiro_unpaired_fx": "{n} currency conversion rows have no matching leg and were not imported.",
        "degiro_unexpected_sign": "{n} rows have an amount with an unexpected sign for their type and were not imported.",
        "degiro_quantity_unreadable": "The quantity of {n} trades could not be read; they were not imported.",
        "degiro_flatex_withdrawal": "{n} withdrawal rows of the flatex account were not imported: add the withdrawal by hand if money left your account.",
        "degiro_not_imported": "{n} rows describe DEGIRO operations that LibreFolio does not import automatically (corporate actions, money market funds, capital returns): check the positions they affect.",
        "degiro_orders_list": "This is DEGIRO's list of orders (Transactions): it has no dividends, deposits, withdrawals or currency conversions. LibreFolio reads the Account Statement: export it from DEGIRO (Inbox → Account Statement) as CSV.",
    },
    "nl": {
        "evidence_title": "Bronregels",
        "degiro_unknown_rows": "{n} regels zijn niet herkend en niet geïmporteerd: controleer ze in de bronregels hieronder.",
        "degiro_unpaired_fx": "{n} regels van een valutawissel hebben geen tegenhanger en zijn niet geïmporteerd.",
        "degiro_unexpected_sign": "{n} regels hebben een bedrag met een onverwacht teken voor hun soort en zijn niet geïmporteerd.",
        "degiro_quantity_unreadable": "Van {n} transacties kon het aantal niet worden gelezen; ze zijn niet geïmporteerd.",
        "degiro_flatex_withdrawal": "{n} opnameregels van de flatex-rekening zijn niet geïmporteerd: voeg de opname handmatig toe als er geld van je rekening is gegaan.",
        "degiro_not_imported": "{n} regels beschrijven DEGIRO-handelingen die LibreFolio niet automatisch importeert (corporate actions, geldmarktfondsen, kapitaaluitkeringen): controleer de posities die ze raken.",
        "degiro_orders_list": "Dit is de orderlijst van DEGIRO (Transacties): daarin staan geen dividenden, stortingen, opnames of valutawissels. LibreFolio leest het rekeningoverzicht: exporteer het in DEGIRO (Inbox → Account Statement) als CSV.",
    },
    "de": {
        "evidence_title": "Quellzeilen",
        "degiro_unknown_rows": "{n} Zeilen wurden nicht erkannt und nicht importiert: prüfen Sie sie in den Quellzeilen unten.",
        "degiro_unpaired_fx": "{n} Zeilen eines Währungswechsels haben keine Gegenbuchung und wurden nicht importiert.",
        "degiro_unexpected_sign": "{n} Zeilen haben einen Betrag mit einem für ihren Typ unerwarteten Vorzeichen und wurden nicht importiert.",
        "degiro_quantity_unreadable": "Bei {n} Trades konnte die Stückzahl nicht gelesen werden; sie wurden nicht importiert.",
        "degiro_flatex_withdrawal": "{n} Auszahlungszeilen des flatex-Kontos wurden nicht importiert: erfassen Sie die Auszahlung von Hand, falls Geld Ihr Konto verlassen hat.",
        "degiro_not_imported": "{n} Zeilen beschreiben DEGIRO-Vorgänge, die LibreFolio nicht automatisch importiert (Kapitalmaßnahmen, Geldmarktfonds, Kapitalrückzahlungen): prüfen Sie die betroffenen Positionen.",
        "degiro_orders_list": "Dies ist die Orderliste von DEGIRO (Transaktionen): Sie enthält keine Dividenden, Einzahlungen, Auszahlungen oder Währungswechsel. LibreFolio liest die Kontoübersicht: Exportieren Sie sie in DEGIRO (Inbox → Account Statement) als CSV.",
    },
    "fr": {
        "evidence_title": "Lignes source",
        "degiro_unknown_rows": "{n} lignes n'ont pas été reconnues et n'ont pas été importées : vérifiez-les dans les lignes source ci-dessous.",
        "degiro_unpaired_fx": "{n} lignes d'une opération de change n'ont pas de contrepartie et n'ont pas été importées.",
        "degiro_unexpected_sign": "{n} lignes ont un montant d'un signe inattendu pour leur type et n'ont pas été importées.",
        "degiro_quantity_unreadable": "La quantité de {n} transactions n'a pas pu être lue ; elles n'ont pas été importées.",
        "degiro_flatex_withdrawal": "{n} lignes de retrait du compte flatex n'ont pas été importées : ajoutez le retrait à la main si de l'argent a quitté votre compte.",
        "degiro_not_imported": "{n} lignes décrivent des opérations DEGIRO que LibreFolio n'importe pas automatiquement (opérations sur titres, fonds monétaires, remboursements de capital) : vérifiez les positions concernées.",
        "degiro_orders_list": "Ceci est la liste des ordres de DEGIRO (Transactions) : elle ne contient ni dividendes, ni dépôts, ni retraits, ni opérations de change. LibreFolio lit le relevé de compte : exportez-le depuis DEGIRO (Inbox → Account Statement) en CSV.",
    },
    "es": {
        "evidence_title": "Filas de origen",
        "degiro_unknown_rows": "{n} filas no se han reconocido y no se han importado: revísalas en las filas de origen de abajo.",
        "degiro_unpaired_fx": "{n} filas de un cambio de divisa no tienen contrapartida y no se han importado.",
        "degiro_unexpected_sign": "{n} filas tienen un importe con un signo inesperado para su tipo y no se han importado.",
        "degiro_quantity_unreadable": "No se ha podido leer la cantidad de {n} operaciones; no se han importado.",
        "degiro_flatex_withdrawal": "{n} filas de retirada de la cuenta flatex no se han importado: añade la retirada a mano si salió dinero de tu cuenta.",
        "degiro_not_imported": "{n} filas describen operaciones de DEGIRO que LibreFolio no importa automáticamente (operaciones corporativas, fondos monetarios, devoluciones de capital): revisa las posiciones afectadas.",
        "degiro_orders_list": "Esta es la lista de órdenes de DEGIRO (Transacciones): no contiene dividendos, ingresos, retiradas ni cambios de divisa. LibreFolio lee el estado de cuenta: expórtalo desde DEGIRO (Inbox → Account Statement) como CSV.",
    },
}

# One notice per code, in this order.
_NOTICE_CODES = ("degiro_unknown_rows", "degiro_unpaired_fx", "degiro_unexpected_sign", "degiro_quantity_unreadable", "degiro_flatex_withdrawal", "degiro_not_imported")

# =============================================================================
# WORD TABLE (folded text: lowercase, no accents, mojibake repaired)
# =============================================================================

_SKIP, _FX_WORD, _FLATEX_WITHDRAWAL, _NOT_IMPORTED, _PROMOTION, _INTEREST, _TYPED = "skip", "fx", "flatex_withdrawal", "not_imported", "promotion", "interest", "typed"


def _words(*patterns: str) -> re.Pattern[str]:
    return re.compile("|".join(rf"\b{pattern}\b" for pattern in patterns))


# The legs of a currency conversion, by name: used when a leg could not be paired by structure.
_FX_WORDS = _words(r"valuta (?:creditering|debitering)", r"fx (?:credit|debit)", r"wahrungswechsel", r"fx-(?:gutschrift|belastung)", r"operation de change", r"(?:credit|debit) fx", r"cambio de divisa", r"(?:credito|prelievo) fx", r"(?:credito|levantamento) de divisa", r"fx vyuctovani")
_TRANSACTION_TAX = _words(r"transactiebelasting", r"stamp duty", r"finanztransaktionssteuer", r"taxe sur les transactions financieres", r"impuesto sobre (?:las )?transacciones financieras")

# (kind, type, pattern): first match wins. Taxes come before dividends ("Dividendbelasting"),
# FX legs and flatex withdrawals before deposits and withdrawals ("Ingreso Cambio de Divisa").
_WORD_RULES: Tuple[Tuple[str, Optional[TransactionType], re.Pattern[str]], ...] = (
    (_SKIP, None, _words(r"cash sweep", r"flatexdegiro bank", r"flatex bank", r"reservation", r"reservering", r"reservierung", r"reserva", r"prenotazione")),
    (_FX_WORD, None, _FX_WORDS),
    (_FLATEX_WITHDRAWAL, None, _words(r"(?:processed )?flatex withdrawal", r"flatex terugstorting", r"prelievo flatex")),
    (_NOT_IMPORTED, None, _words(r"fonds monetaires", r"geldmarktfonds\w*", r"money market", r"penezniho fondu", r"capital return", r"kapitaals?uitkering", r"kapitalruckzahlung", r"remboursement de capital", r"corporate action cash settlement", r"contante verrekening", r"verrekening van aandelen")),
    (
        _TYPED,
        TransactionType.TAX,
        _words(r"dividendbelasting", r"dividend tax", r"dividendensteuer", r"quellensteuer", r"impots? sur (?:les )?dividendes?", r"retencion del dividendo", r"ritenuta sul dividendo", r"imposta sui dividendi", r"imposto sobre dividendos?", r"belasting op vervangend dividend"),
    ),
    (_TYPED, TransactionType.TAX, _TRANSACTION_TAX),
    (_TYPED, TransactionType.DIVIDEND, _words(r"dividend(?:e|o|a|en)?", r"fund distribution", r"(?:fonds)?ausschuttung")),
    (_PROMOTION, TransactionType.INTEREST, _words(r"courtesy", r"rebate", r"promoti(?:on|e)", r"propagace", r"rabatt?", r"neukundenaktion")),
    (_INTEREST, TransactionType.INTEREST, _words(r"interest", r"rente", r"zinsen", r"interets?", r"intereses", r"interessi", r"juros", r"urok")),
    (
        _TYPED,
        TransactionType.FEE,
        _words(
            r"aansluitingskosten",
            r"connection fee",
            r"anschlussgebuhren",
            r"borsengebuhren",
            r"frais de connexion\w*",
            r"costi di connessione",
            r"custo de conectividade",
            r"comision de conectividad",
            r"poplatek",
            r"corporate action kosten",
            r"corporate action costs?",
            r"adr/gdr",
            r"realtimekurse",
            r"handelsmodalitaten",
            r"activiteitskosten",
        ),
    ),
    (_TYPED, TransactionType.DEPOSIT, _words(r"deposit", r"storting", r"einzahlung", r"depot", r"versement de fonds", r"ingreso", r"deposito", r"vklad")),
    (_TYPED, TransactionType.WITHDRAWAL, _words(r"withdrawal", r"auszahlung", r"retrait de fonds", r"retirada", r"prelievo", r"levantamento")),
)

_POSITIVE_TYPES = frozenset({TransactionType.DIVIDEND, TransactionType.INTEREST, TransactionType.DEPOSIT})
_NEGATIVE_TYPES = frozenset({TransactionType.TAX, TransactionType.FEE, TransactionType.WITHDRAWAL})
_ASSET_TYPES = frozenset({TransactionType.DIVIDEND, TransactionType.TAX, TransactionType.FEE})

# =============================================================================
# HELPERS
# =============================================================================


def _repair_mojibake(text: str) -> str:
    """``CrÃ©dito`` → ``Crédito``: UTF-8 bytes once read as Windows-1252 (seen in real exports)."""
    if "Ã" not in text and "Â" not in text:
        return text
    for codec in ("cp1252", "latin-1"):
        try:
            return text.encode(codec).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return text


def _fold(text: str) -> str:
    """Lowercase, without accents, mojibake repaired: what the word table matches against."""
    decomposed = unicodedata.normalize("NFKD", _repair_mojibake(text))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower().strip()


def _parse_degiro_date(value: str) -> Optional[date_type]:
    """Parse DEGIRO's date (DD-MM-YYYY)."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except ValueError:
        return None


def _certain_mark(text: str) -> Optional[str]:
    """The decimal mark of ``text`` when its digits say it for sure; ``None`` when ambiguous or absent.

    Both marks → the last one is decimal; a repeated mark groups thousands, so the other one is
    decimal; a single mark followed by 1, 2 or ≥4 digits (or after a zero) is decimal. Only one
    mark followed by exactly three digits (``1.000``, ``49,785``) is left open.
    """
    digits = re.sub(r"[^\d.,]", "", text)
    marks = [ch for ch in digits if ch in ".,"]
    if not marks:
        return None
    if len(set(marks)) == 2:
        return marks[-1]
    mark = marks[0]
    if len(marks) > 1:
        return _OTHER_MARK[mark]
    whole, fraction = digits.split(mark)
    return mark if len(fraction) != 3 or whole in ("", "0") else None


def _parse_degiro_number(value: str, decimal_hint: Optional[str] = None) -> Optional[Decimal]:
    """Parse a DEGIRO number: per value when certain, ``decimal_hint`` (the file's mark) when ambiguous.

    Without a hint an ambiguous value reads its one mark as decimal. Spaces group thousands.
    """
    text = (value or "").strip()
    if not text:
        return None
    mark = _certain_mark(text) or (decimal_hint if decimal_hint in (",", ".") else None) or ("," if "," in text else ".")
    return to_decimal_it(text) if mark == "," else to_decimal_plain(text)


def _extract_quantity_from_description(description: str, decimal_hint: Optional[str] = None) -> Decimal:
    """The quantity of a trade description (``Koop 1 @ 33,9 USD`` → 1); 0 when there is none."""
    match = _TRADE_RE.match((description or "").strip())
    if not match:
        return Decimal("0")
    quantity = _parse_degiro_number(match.group("qty"), decimal_hint)
    return quantity if quantity is not None else Decimal("0")


def _detect_language(header: Sequence[str]) -> str:
    """The language of the messages, from the header: the best unique match with ≥3 names, else English."""
    names = [_fold(str(cell)) for cell in header]
    names = [name for name in names if name and name != "fx" and "isin" not in name]
    scores = {language: sum(1 for name in names if name in words) for language, words in _HEADER_WORDS.items()}
    best = max(scores.values(), default=0)
    winners = [language for language, score in scores.items() if score == best]
    return winners[0] if best >= _MIN_LANGUAGE_MATCHES and len(winners) == 1 else "en"


def _texts(language: str) -> Dict[str, str]:
    return _MESSAGES.get(language, _MESSAGES["en"])


def _is_dated(row: Sequence[str]) -> bool:
    return len(row) >= 2 and bool(_DATE_RE.match(str(row[_DATE]).strip())) and bool(_TIME_RE.match(str(row[_TIME]).strip()))


def _is_statement_header(header: Sequence[str], rows: Sequence[Sequence[str]]) -> bool:
    cells = [str(cell).strip() for cell in header]
    extra_is_empty = all(len(row) <= _STATEMENT_COLUMNS or not str(row[_STATEMENT_COLUMNS]).strip() for row in rows)
    if len(cells) == _STATEMENT_COLUMNS + 1 and not cells[-1] and extra_is_empty:
        cells = cells[:_STATEMENT_COLUMNS]
    return len(cells) == _STATEMENT_COLUMNS and not cells[_AMOUNT] and not cells[_BALANCE] and "isin" in cells[_ISIN].lower()


def _is_orders_header(header: Sequence[str]) -> bool:
    cells = [str(cell).strip() for cell in header]
    return len(cells) >= _ORDERS_MIN_COLUMNS and "isin" in cells[3].lower() and not cells[8] and not cells[10]


def _layout(header: Sequence[str], rows: Sequence[Sequence[str]]) -> Optional[str]:
    """``"statement"``, ``"orders"`` or ``None``, from the header and the first data row."""
    first = next((row for row in rows if any(str(cell).strip() for cell in row)), None)
    if first is None or not _is_dated(first):
        return None
    if _is_statement_header(header, rows):
        return "statement"
    if _is_orders_header(header):
        return "orders"
    return None


@dataclass
class _Row:
    """One statement row (continuations merged): its first physical line and its 12 cells."""

    line: int
    cells: List[str]
    amount: Optional[Decimal] = None
    folded: str = ""

    @property
    def description(self) -> str:
        return self.cells[_DESCRIPTION]

    @property
    def currency(self) -> str:
        return self.cells[_CURRENCY].upper()

    @property
    def isin(self) -> str:
        return self.cells[_ISIN]

    @property
    def product(self) -> str:
        return self.cells[_PRODUCT]

    @property
    def order_id(self) -> str:
        return self.cells[_ORDER_ID]

    def group(self) -> Tuple[str, ...]:
        """The order a row belongs to: its Order Id, or its date and time when it has none."""
        return ("order", self.order_id) if self.order_id else ("time", self.cells[_DATE], self.cells[_TIME])

    def is_trade(self) -> bool:
        return bool(self.isin and self.order_id and self.amount and _TRADE_RE.match(self.description))


def _merge_rows(raw_rows: Sequence[Sequence[str]]) -> List[_Row]:
    """Data rows (line 2 on) with continuation lines appended to the row above."""
    merged: List[_Row] = []
    for line, raw in enumerate(raw_rows, start=2):
        cells = [str(cell).strip() for cell in list(raw)[:_STATEMENT_COLUMNS]]
        cells += [""] * (_STATEMENT_COLUMNS - len(cells))
        if not any(cells):
            continue
        if not cells[_DATE] and not cells[_TIME] and merged:
            _append_continuation(merged[-1], cells)
            continue
        merged.append(_Row(line=line, cells=cells))
    return merged


def _append_continuation(row: _Row, tail: Sequence[str]) -> None:
    """DEGIRO wraps by character count (an Order Id is cut mid-UUID): the tail is appended verbatim."""
    for index, part in enumerate(tail):
        if part:
            row.cells[index] = f"{row.cells[index]}{part}"


def _decimal_hint(rows: Sequence[_Row]) -> Optional[str]:
    """The file's decimal mark, voted by the amounts whose mark is certain; ``None`` on a tie."""
    votes = {",": 0, ".": 0}
    for row in rows:
        for raw in (row.cells[_AMOUNT], row.cells[_BALANCE]):
            mark = _certain_mark(raw) if raw else None
            if mark:
                votes[mark] += 1
    if votes[","] == votes["."]:
        return None
    return "," if votes[","] > votes["."] else "."


def _is_counter_leg(leg: _Row, other: _Row) -> bool:
    return bool(other.amount) and bool(other.currency) and other.currency != leg.currency and (other.amount > 0) != (leg.amount > 0) and not _TRADE_RE.match(other.description)


def _pair_fx_legs(rows: Sequence[_Row]) -> Dict[int, int]:
    """Row index → partner index for every currency conversion found (both directions)."""
    groups: Dict[Tuple[str, ...], List[int]] = {}
    for index, row in enumerate(rows):
        groups.setdefault(row.group(), []).append(index)
    pairs: Dict[int, int] = {}
    for index, row in enumerate(rows):
        if index in pairs or not row.cells[_FX] or not row.amount:
            continue
        candidates = [other for other in groups[row.group()] if other != index and other not in pairs and _is_counter_leg(row, rows[other])]
        if len(candidates) > 1:
            candidates = [other for other in candidates if abs(other - index) == 1]
        if len(candidates) == 1:
            pairs[index] = candidates[0]
            pairs[candidates[0]] = index
    return pairs


def _evidence_headers(header: Sequence[str]) -> List[str]:
    """The file's own header; an unnamed column is named after the one before it (``Mutatie #``)."""
    names = [str(cell).strip() for cell in list(header)[:_STATEMENT_COLUMNS]]
    names += [""] * (_STATEMENT_COLUMNS - len(names))
    return [name or (f"{names[index - 1]} #" if index else "#") for index, name in enumerate(names)]


def _orders_list_output(language: str, rows: int) -> BRIMParseOutput:
    notice = BRIMNotice(severity="warning", code="degiro_orders_list", message=_texts(language)["degiro_orders_list"].format(n=rows), context={"language": language, "count": rows})
    return BRIMParseOutput(transactions=[], warnings=[notice])


# =============================================================================
# STATEMENT READER
# =============================================================================


class _StatementReader:
    """Classifies the rows of one Account Statement and builds the parse output."""

    def __init__(self, provider: BRIMProvider, broker_id: int, header: Sequence[str], language: str, raw_rows: Sequence[Sequence[str]]):
        self.provider = provider
        self.broker_id = broker_id
        self.header = header
        self.language = language
        self.digest = hashlib.sha256(json.dumps([list(map(str, row)) for row in raw_rows], ensure_ascii=False).encode("utf-8")).hexdigest()
        self.rows = _merge_rows(raw_rows[1:])
        self.hint = _decimal_hint(self.rows)
        for row in self.rows:
            row.amount = _parse_degiro_number(row.cells[_AMOUNT], self.hint)
            row.folded = _fold(row.description)
        self.pairs = _pair_fx_legs(self.rows)
        self.transactions: List[TXCreateItem] = []
        self.validation_issues: List[BRIMValidationIssue] = []
        self.flagged: Dict[str, List[_Row]] = {code: [] for code in _NOTICE_CODES}
        self.assets: Dict[int, BRIMExtractedAssetInfo] = {}
        self.asset_ids: Dict[str, int] = {}
        self.next_fake_id = FAKE_ASSET_ID_BASE

    # -- output -----------------------------------------------------------------

    def run(self) -> BRIMParseOutput:
        for index, row in enumerate(self.rows):
            self._row(index, row)
        return BRIMParseOutput(transactions=self.transactions, warnings=self._notices(), validation_issues=self.validation_issues, extracted_assets=self.assets)

    def _notices(self) -> List[BRIMNotice]:
        texts = _texts(self.language)
        headers = _evidence_headers(self.header)
        notices = []
        for code in _NOTICE_CODES:
            rows = self.flagged[code]
            if not rows:
                continue
            evidence = BRIMEvidence(title=texts["evidence_title"], headers=headers, rows=[list(row.cells) for row in rows], row_numbers=[row.line for row in rows])
            notices.append(BRIMNotice(severity="warning", code=code, message=texts[code].format(n=len(rows)), evidence=[evidence], context={"language": self.language, "count": len(rows)}))
        return notices

    def _flag(self, code: str, row: _Row) -> None:
        self.flagged[code].append(row)

    # -- classification -----------------------------------------------------------

    def _row(self, index: int, row: _Row) -> None:
        if not row.cells[_AMOUNT]:
            return  # information line
        if index in self.pairs:
            if self.pairs[index] > index:
                self._fx_pair(row, self.rows[self.pairs[index]])
            return
        if row.amount is None or _parse_degiro_date(row.cells[_DATE]) is None or not row.currency:
            self._flag("degiro_unknown_rows", row)
        elif row.cells[_FX]:
            self._flag("degiro_unpaired_fx", row)
        elif not self._structural(row):
            self._by_words(row)

    def _structural(self, row: _Row) -> bool:
        """Trades, corporate actions, order costs and zero amounts; False when the words must decide."""
        if row.is_trade():
            self._trade(row)
        elif self._is_corporate_action(row):
            self._flag("degiro_not_imported", row)
        elif _FX_WORDS.search(row.folded):
            self._flag("degiro_unpaired_fx", row)  # a leg the structure could not pair is never a fee
        elif row.order_id and row.amount < 0:
            self._emit(row, TransactionType.TAX if _TRANSACTION_TAX.search(row.folded) else TransactionType.FEE)
        elif row.amount == 0:
            if row.isin:
                self._flag("degiro_not_imported", row)
        else:
            return False
        return True

    @staticmethod
    def _is_corporate_action(row: _Row) -> bool:
        prefixed = _PREFIX_RE.match(row.description)
        return bool(prefixed and _TRADE_RE.match(prefixed.group("rest").strip()))

    def _by_words(self, row: _Row) -> None:
        kind, tx_type = next(((kind, tx_type) for kind, tx_type, pattern in _WORD_RULES if pattern.search(row.folded)), (None, None))
        if kind == _SKIP:
            return
        if kind in (_FX_WORD, _FLATEX_WITHDRAWAL, _NOT_IMPORTED):
            self._flag({_FX_WORD: "degiro_unpaired_fx", _FLATEX_WITHDRAWAL: "degiro_flatex_withdrawal", _NOT_IMPORTED: "degiro_not_imported"}[kind], row)
        elif kind == _INTEREST and row.amount < 0:
            self._emit(row, TransactionType.FEE)  # interest charged (e.g. ``Intérêts débiteurs``) is a cost
        elif tx_type is not None:
            self._emit(row, tx_type)
        else:
            self._flag("degiro_unknown_rows", row)

    # -- transactions ---------------------------------------------------------------

    def _trade(self, row: _Row) -> None:
        quantity = _extract_quantity_from_description(row.description, self.hint)
        if quantity <= 0:
            self._flag("degiro_quantity_unreadable", row)
            return
        buy = row.amount < 0
        self._create(row, TransactionType.BUY if buy else TransactionType.SELL, quantity if buy else -quantity, self._asset_id(row), row.description)

    def _emit(self, row: _Row, tx_type: TransactionType) -> None:
        """A single-row transaction whose sign the type dictates; a contradicting sign is listed instead."""
        if (tx_type in _POSITIVE_TYPES and row.amount <= 0) or (tx_type in _NEGATIVE_TYPES and row.amount >= 0):
            self._flag("degiro_unexpected_sign", row)
            return
        asset_id = self._asset_id(row) if tx_type in _ASSET_TYPES else None
        if tx_type == TransactionType.DIVIDEND and asset_id is None:
            self._flag("degiro_unknown_rows", row)  # a dividend needs its product
            return
        self._create(row, tx_type, Decimal("0"), asset_id, row.description)

    def _fx_pair(self, first: _Row, second: _Row) -> None:
        same_text = _fold(first.description) == _fold(second.description)
        description = first.description if same_text else f"{first.description} / {second.description}"
        link_uuid = str(uuid.uuid5(_LINK_NAMESPACE, f"{self.digest}:{first.line}:{second.line}"))
        for leg in (first, second):
            self._create(leg, TransactionType.FX_CONVERSION, Decimal("0"), None, description, link_uuid=link_uuid)

    def _create(self, row: _Row, tx_type: TransactionType, quantity: Decimal, asset_id: Optional[int], description: str, link_uuid: Optional[str] = None) -> None:
        try:
            cash = Currency(code=row.currency, amount=row.amount)
        except (ValueError, ValidationError):
            self._flag("degiro_unknown_rows", row)  # not an ISO 4217 currency
            return
        self.provider._create_transaction(
            row_num=row.line,
            transactions=self.transactions,
            validation_issues=self.validation_issues,
            context=row.description,
            broker_id=self.broker_id,
            asset_id=asset_id,
            type=tx_type,
            date=_parse_degiro_date(row.cells[_DATE]),
            quantity=quantity,
            cash=cash,
            description=description,
            tags=list(_TAGS),
            link_uuid=link_uuid,
        )

    def _asset_id(self, row: _Row) -> Optional[int]:
        """One fake asset id per ISIN (product name when there is none)."""
        key = row.isin or row.product
        if not key:
            return None
        if key not in self.asset_ids:
            self.asset_ids[key] = self.next_fake_id
            self.assets[self.next_fake_id] = BRIMExtractedAssetInfo(extracted_symbol=None, extracted_isin=row.isin or None, extracted_name=row.product or None)
            self.next_fake_id -= 1
        return self.asset_ids[key]


# =============================================================================
# PLUGIN IMPLEMENTATION
# =============================================================================


@register_provider(BRIMProviderRegistry)
class DegiroBrokerProvider(BRIMProvider):
    """DEGIRO Account Statement (CSV) import plugin, any language: see the module docstring."""

    @property
    def provider_code(self) -> str:
        return "broker_degiro"

    @property
    def provider_name(self) -> str:
        return "DEGIRO"

    @property
    def description(self) -> str:
        return "Import DEGIRO's Account Statement (CSV) in any language: trades, fees, dividends, taxes, interest, deposits, withdrawals and currency conversions, each in its own currency."

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

    @property
    def plugin_version(self) -> str:
        """2.0.0: columns read by position in any language, amounts and currencies per row, FX pairs."""
        return "2.0.0"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/degiro/"

    @property
    def test_file_pattern(self) -> Optional[str]:
        """Filename pattern for auto-detection tests."""
        return "degiro"

    def can_parse(self, file_path: Path) -> bool:
        """The Account Statement, or the orders list (recognised to point to the statement)."""
        return self._inspect(file_path)[0] is not None

    def cannot_parse_reason(self, file_path: Path) -> Optional[str]:
        """Why ``can_parse`` refuses a file; ``None`` exactly when it accepts it."""
        return self._inspect(file_path)[1]

    def _inspect(self, file_path: Path) -> Tuple[Optional[str], Optional[str]]:
        if file_path.suffix.lower() != ".csv":
            return None, "only the CSV export is read: download the Account Statement as CSV"
        try:
            head = list(csv.reader(io.StringIO(self._read_file_head(file_path, num_lines=8)), delimiter=self.detect_csv_delimiter(file_path)))
        except Exception:  # noqa: BLE001 — can_parse never raises: an unreadable file is just not ours
            return None, "the file could not be read"
        if len(head) < 2:
            return None, "the file has no movement rows"
        layout = _layout(head[0], head[1:])
        if layout is None:
            return None, "this is not a DEGIRO Account Statement: expected 12 columns with the ISIN fifth, unnamed amount columns ninth and eleventh, and dates as DD-MM-YYYY"
        return layout, None

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """Parse an Account Statement; the orders list gives no transactions and one notice."""
        rows = self._read(file_path)
        header = [cell.strip() for cell in rows[0]]
        language = _detect_language(header)
        layout = _layout(header, rows[1:])
        if layout == "orders":
            return _orders_list_output(language, sum(1 for row in rows[1:] if any(cell.strip() for cell in row)))
        if layout != "statement":
            raise BRIMParseError("Not a DEGIRO Account Statement", details={"file": file_path.name})
        output = _StatementReader(self, broker_id, header, language, rows).run()
        logger.info("DEGIRO file parsed", transaction_count=len(output.transactions), notice_count=len(output.warnings), asset_count=len(output.extracted_assets), language=language)
        return output

    def _read(self, file_path: Path) -> List[List[str]]:
        try:
            rows = read_rows(file_path, delimiter=self.detect_csv_delimiter(file_path))
        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}") from None
        except Exception as e:
            raise BRIMParseError(f"Error reading file: {e}") from e
        rows = [[str(cell) for cell in row] for row in rows]
        if not rows:
            raise BRIMParseError("The file is empty", details={"file": file_path.name})
        return rows
