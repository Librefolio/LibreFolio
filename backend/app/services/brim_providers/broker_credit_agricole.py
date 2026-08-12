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
bank cash, classified through an explicit **four-tier causale registry** so that no
causale can pass unnoticed:

1. *typed* — FEE/TAX (capital gain, bollo, canone, spese), INTEREST/DIVIDEND
   (coupons/dividends, linked to their security by ISIN when named), or an
   identifiable bond maturity SELL + optional premium INTEREST;
2. *unresolved* — recognised as a securities operation (COMPRAVENDITA) whose
   quantity and instrument this layout does not carry: booked as cash by sign and
   flagged with a **blocker** field-todo carrying the source row as evidence;
3. *declared cash* — POS, utenze, prelievi, emolumenti, giroconto: deposit/withdrawal
   by sign, silently, because here the fallback *is* the right answer;
4. *unknown* — any causale the registry has never seen: same cash fallback plus an
   INFO notice naming it, so a new causale can never enter the fallback quietly.

Tiers 2-4 all produce the same, correct cash movement; they differ only in what the
plugin declares about it. Account-mode transactions keep the bank description
verbatim and carry the causale as a tag.

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
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import (
    FAKE_ASSET_ID_BASE,
    BRIMAssetNotice,
    BRIMEvidence,
    BRIMExtractedAssetInfo,
    BRIMFieldTodo,
    BRIMNotice,
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

# The subset that is a charge *on a security*, and therefore belongs to one. The
# others ("COMMISSIONI/SPESE", the monthly canone) are account charges and are
# correctly left unallocated, so only these are worth flagging when no asset is found.
_ACCT_FEETAX_CAUSALI_SECURITIES = {"COMMISS./SPESE SU OPERAZ. TITOLI"}

# "INTERESSI/COMPETENZE" is sign-dependent: a debit is the account fee
# (CANONE MENSILE), a credit is real interest income.
_ACCT_CANONE_CAUSALI = {"INTERESSI/COMPETENZE"}

# --- Causale registry: tier 2 and tier 3 -----------------------------------
#
# The account layout used to type four causale groups and send *everything else*
# to a deposit/withdrawal fallback by sign. That fallback is right for real bank
# cash and wrong for the cash leg of a trade — and the two were indistinguishable,
# so a lost trade looked exactly like a supermarket payment.
#
# The registry makes the difference explicit. Every causale lands in exactly one
# of four tiers and none can pass unnoticed:
#   1. typed          -> a dedicated handler builds a complete transaction
#   2. unresolved     -> cash fallback + a *blocker* todo: recognised as not-cash,
#                        but this layout alone does not carry the security
#   3. declared cash  -> deposit/withdrawal by sign, silently: the fallback IS the
#                        right answer here, and saying so turns silence from "not
#                        handled" into "handled, and it is cash"
#   4. unknown        -> deposit/withdrawal by sign + an INFO notice naming the
#                        causale, so a new one can never enter the fallback quietly
#
# Classification stays a pure function of causale + description: no DB, no
# network, no state — the BRIM contract.

# Tier 3 — causali for which deposit/withdrawal by sign is the correct answer.
_ACCT_DECLARED_CASH_CAUSALI = {
    "PAGAMENTO TRAMITE POS",
    "PAGAMENTO UTENZE",
    "PRELIEVO SPORT. AUTOM. ALTRA BANCA",
    "PRELIEVO NOSTRO SPORTELLO AUTOM.",
    "ACCREDITO EMOLUMENTI",
    "GIROCONTO/BONIFICO",
}

# Tier 2 — securities operations booked on the cash account. The row carries the
# money but not the quantity or the instrument, and the matching securities leg
# only exists when the "Deposito Titoli" export covers the same period. Booked as
# cash (the amount is right) and flagged blocker (the security is missing).
_ACCT_UNRESOLVED_CAUSALI = {"COMPRAVENDITA TITOLI/FONDI/OPZIONI"}

# Direction keywords inside a COMPRAVENDITA description. The sign of the amount
# confirms them; a disagreement between word and sign is never resolved by
# guessing — the row stays cash and is flagged instead.
_ACCT_TRADE_BUY_KEYWORDS = ("NOTA INF. ACQ", "NOTA INF.ACQ", "ACQUIST", "SOTTOSC")
_ACCT_TRADE_SELL_KEYWORDS = ("NOTA INF. VEND", "NOTA INF.VEND", "VENDIT", "VEND.", "DISINVEST", "RIMBORS")

# Tier 2b — a fund redemption does not reach the account as a securities operation:
# the fund house simply wires the money over, so the row lands under the ordinary
# transfer causale and looks exactly like any other incoming payment. Booking it as
# a plain deposit leaves the position open forever, and the loss only surfaces later
# as an unexplained gap in the cost basis. See ``_sct_fund_redemption_name`` for how
# the two are told apart.
_ACCT_SCT_CAUSALI = {"GIROCONTO/BONIFICO"}
# The ordering party of an incoming transfer, printed before the operation text:
#   ORD:AMUNDI PRIMO INVESTIMENTO DT.ORD:000000 DESCR.OPERAZIONE SCT::RIMBORSI ...
_ACCT_SCT_ORDER_RE = re.compile(r"\bORD\s*:\s*(?P<party>.+?)\s+DT\.?\s*ORD\s*:(?P<rest>.*)$", re.IGNORECASE | re.DOTALL)
_ACCT_SCT_REDEMPTION_KEYWORDS = ("RIMBORS", "DISINVEST", "LIQUIDAZ")
# Below this length an ordering party says nothing and would match by accident.
_ACCT_SCT_PARTY_MIN = 8

# The instrument name inside a trade description, printed either after ``TIT:``
# (bonds) or after the order reference (funds):
#   NOTA INF. ACQ. TIT:BTP 01/03/35 3,35%
#   SOTTOSC SICAV ORD.:2025/003955841 AMUNDI PIO GLOB EQ G
_ACCT_TRADE_TIT_RE = re.compile(r"\bTIT\.?\s*:\s*(?P<name>.+)$", re.IGNORECASE)
_ACCT_TRADE_ORDER_RE = re.compile(r"\bORD\.?\s*:\s*\S+\s+(?P<name>.+)$", re.IGNORECASE)
# Reference fragments that follow the name and are not part of it.
_ACCT_TRADE_NAME_STOP_RE = re.compile(r"\s+(?:DOSS?(?:IER)?\.?\s*:|RUB\.?\s*:|DATA\s*:|MOV\s*[:.]).*$", re.IGNORECASE)
# Below this length a prefix match says nothing ("BTP" matches every bond).
_ACCT_TRADE_NAME_MIN_MATCH = 6

# Tier labels returned by ``_classify_account_row`` alongside the (type, cash) pair.
_TIER_TYPED = "typed"
_TIER_UNRESOLVED = "unresolved"
_TIER_DECLARED_CASH = "declared_cash"
_TIER_UNKNOWN = "unknown"

# Description keywords that make a fee row a TAX (capital gain, stamp duty,
# withholding) rather than a plain FEE (management/administration/coupon-detach).
_TAX_KEYWORDS = ("CAPITAL GAIN", "D.LGS 461", "461/97", "IMPOSTA", "BOLLO", "RITENUTA")

# Description keyword that marks a dividend (vs a bond coupon "CEDOLA").
_DIVIDEND_KEYWORDS = ("DIVIDEND",)

_ACCOUNT_MATURITY_RE = re.compile(r"RIMB\.TIT\.\s*(?P<name>.+?)\s*\((?P<code>[^)]*)\)", re.IGNORECASE)
_ACCOUNT_NOMINALE_RE = re.compile(r"\bNOMINALE\s*:\s*(?P<nominale>[\d\.\,]+)", re.IGNORECASE)
# Withholding spelled out inside an income description ("... ALIQ: 12,50 RITENUTA: 13,36").
_ACCOUNT_RITENUTA_RE = re.compile(r"\bRITENUT[AE]\s*:\s*(?P<ritenuta>[\d\.\,]+)", re.IGNORECASE)


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


def _charge_asset_name(description: str, isin: str) -> str:
    """Best-effort security name for an account-mode securities charge.

    A charge line names the instrument *after* its ISIN and before the movement
    reference::

        SPESE STACCO CEDOLA DEL 21/11/2024 DOSSIER: ... TIT: IT0005332827 BTP 05/26 0.55FOICUM MOV:252419599

    Crédit Agricole prints this name in full, while the matching coupon line
    truncates it to 19 characters (``BTP 05/26 0.55FOICU``), so the charge is the
    better naming source of the two. Returns the ISIN when no name follows it.
    """
    idx = description.upper().find(isin)
    if idx < 0:
        return isin
    tail = description[idx + len(isin) :]
    tail = re.split(r"\bMOV\s*[:.]", tail, maxsplit=1)[0]
    return tail.strip(" :-\t") or isin


def _is_truncation_of(short: str, full: str) -> bool:
    """True when ``short`` looks like ``full`` cut off by the bank's field width.

    Crédit Agricole prints the same security name at different widths depending on
    the row type, so the same instrument reaches us as both ``BTP 05/26 0.55FOICU``
    and ``BTP 05/26 0.55FOICUM``. Keeping the longer form avoids creating an asset
    under a name that will never match the one already in the portfolio.
    """
    return len(full) > len(short) and bool(short) and full.upper().startswith(short.upper())


def _digits_only(value: str) -> str:
    """Return only decimal digits from a broker identifier fragment."""
    return re.sub(r"\D+", "", value)


def _fmt_money(value: Decimal) -> str:
    """Italian thousands/decimal notation, the way the statement itself writes numbers.

    The messages this plugin emits are read next to the bank's own rows: ``46603.73``
    beside ``46.603,73`` reads as a different number at a glance, and the whole point of
    these messages is that the user can check them against the file.
    """
    return f"{value:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _classify_trade_direction(description: str, amount: Decimal) -> tuple[Optional[TransactionType], str]:
    """Direction of a ``COMPRAVENDITA`` row from its description, confirmed by the sign.

    Returns ``(type, reason)`` where reason is one of ``ok`` / ``no_keyword`` /
    ``sign_mismatch``. Word and sign must agree: a purchase spends money, a sale
    brings it in. When they disagree the row is *not* typed — a trade booked in the
    wrong direction is far worse than one left to the user, because it opens a
    position that silently poisons every FIFO match downstream.
    """
    upper = description.upper()
    is_buy_word = any(kw in upper for kw in _ACCT_TRADE_BUY_KEYWORDS)
    is_sell_word = any(kw in upper for kw in _ACCT_TRADE_SELL_KEYWORDS)
    if is_buy_word == is_sell_word:  # neither, or both (contradictory wording)
        return None, "no_keyword"
    if is_buy_word:
        return (TransactionType.BUY, "ok") if amount < 0 else (None, "sign_mismatch")
    return (TransactionType.SELL, "ok") if amount > 0 else (None, "sign_mismatch")


def _trade_asset_name(description: str) -> str:
    """Best-effort instrument name carried by a ``COMPRAVENDITA`` description."""
    match = _ACCT_TRADE_TIT_RE.search(description) or _ACCT_TRADE_ORDER_RE.search(description)
    raw = match.group("name") if match else description
    return _ACCT_TRADE_NAME_STOP_RE.sub("", raw).strip(" :-\t")


def _normalize_trade_name(name: str) -> str:
    """Uppercase, whitespace-collapsed form used to compare truncated names."""
    return re.sub(r"\s+", " ", name).strip().upper()


def _squash(text: str) -> str:
    """Uppercase, letters and digits only — the form that survives column wrapping.

    The bank breaks a long name across the column width and the break lands inside a
    word (``AMUNDI PRIMO INVES TIMENTO``), so any comparison that keeps whitespace
    fails on exactly the rows that matter.
    """
    return re.sub(r"[^A-Z0-9]+", "", text.upper())


def _sct_fund_redemption_name(description: str) -> str:
    """Name of the fund behind an incoming transfer that is really a redemption, or ``""``.

    A fund pays a disinvestment out by wire, so it arrives under the same causale as a
    salary or a refund from the tax office. Three signals have to agree before the row
    is treated as a securities operation, because getting this wrong on ordinary bank
    cash would invent a position out of a grocery refund:

    1. the transfer names an ordering party long enough to identify anything;
    2. the operation text says a redemption happened;
    3. **the ordering party is named again inside that text** — the payer and the
       subject of the payment are the same entity, which is what distinguishes
       "AMUNDI PRIMO INVESTIMENTO ... RIMBORSI SU AMUNDI PRIMO INVESTIMENTO CL B"
       from "DIVISIONE SERVIZI ... RIMBORSO IRPEF" or "NUOVE VIE ... SALDO RIMB COSTO
       ENERGIA", where the refund is about something the payer is not.

    Signal 3 is the load-bearing one: on the real exports the redemption keyword alone
    fires on three rows out of four.
    """
    match = _ACCT_SCT_ORDER_RE.search(description)
    if match is None:
        return ""
    party = _normalize_trade_name(match.group("party"))
    rest = match.group("rest")
    if len(_squash(party)) < _ACCT_SCT_PARTY_MIN:
        return ""
    if not any(kw in rest.upper() for kw in _ACCT_SCT_REDEMPTION_KEYWORDS):
        return ""
    if _squash(party) not in _squash(rest):
        return ""
    return party


def _prefix_matches(a: str, b: str) -> bool:
    """True when two normalized names are the same instrument cut at different widths.

    The bank truncates the same security to a different length depending on the row
    type, so the trade may be the shorter form or the longer one — the comparison
    has to work in both directions, and equality would miss every real case.
    """
    if len(a) < _ACCT_TRADE_NAME_MIN_MATCH or len(b) < _ACCT_TRADE_NAME_MIN_MATCH:
        return False
    return a.startswith(b) or b.startswith(a)


def _attach_maturity_notices(transactions: List[TXCreateItem], extracted_assets: Dict[int, BRIMExtractedAssetInfo]) -> None:
    """Flag assets whose transactions include a maturity/redemption (``TITOLI SCADUTI``,
    ``FONDI: RIMBORSO``) so the create-asset UI can warn that the security is probably
    delisted and will not be found by any price provider.

    Advisory only — never changes import behaviour. Both layouts need it: the securities
    export and the account statement each book redemptions, and an asset created from the
    account statement is exactly the one the user has no other way of recognising as expired.
    """
    for asset_id, idxs in io.detect_maturity_hits(transactions).items():
        info = extracted_assets.get(asset_id)
        if info is not None:
            info.notices.append(
                BRIMAssetNotice(
                    kind=io.MATURITY_NOTICE_KIND,
                    reason="Rilevata almeno una transazione di scadenza/rimborso (es. «TITOLI SCADUTI» o «FONDI: RIMBORSO»).",
                    transaction_indexes=idxs,
                )
            )


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

        # Column labels of the real header row, for rendering source rows back to
        # the user as a navigable table (see ``source_row_evidence``).
        sec_evidence_cols = [(label, col[key]) for label, key in (("Data operazione", "date"), ("Nome", "name"), ("Causale", "causale"), ("Prezzo", "price"), ("Quantità", "qty"), ("Controvalore in Euro", "ctv")) if col.get(key) is not None]
        sec_evidence_headers = [label for label, _ in sec_evidence_cols]

        def sec_row_values(row: Sequence) -> List[str]:
            return [io.cell_str(row[cidx]) if cidx < len(row) else "" for _, cidx in sec_evidence_cols]

        transactions: List[TXCreateItem] = []
        warnings: List[BRIMNotice] = []
        validation_issues: List[BRIMValidationIssue] = []
        field_todos: List[BRIMFieldTodo] = []
        extracted_assets: Dict[int, BRIMExtractedAssetInfo] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE
        succession_rows: List[tuple[int, Sequence]] = []

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
                succession_rows.append((offset, row))
            else:
                warnings.append(
                    BRIMNotice(
                        severity="warning",
                        code="ca_securities_unknown_causale",
                        message=f"Riga {offset}: causale '{causale}' non riconosciuta, saltata",
                        context={"causale": causale, "row": offset},
                        evidence=[
                            BRIMEvidence(
                                title="Riga del file",
                                headers=sec_evidence_headers,
                                rows=[sec_row_values(row)],
                                row_numbers=[offset],
                                comment="Non so cosa farne di questa causale, quindi la riga non è stata importata: se contiene un movimento vero, va inserito a mano.",
                            )
                        ],
                    )
                )
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

        if succession_rows:
            # Describes correct, intentional behaviour, so it is INFO, not a warning.
            # This raw wording is the Italian fallback: the frontend prefers the
            # localised `importWizard.brimNotice.ca_succession_transfer_in`, keyed on
            # `code` and interpolated with `context` — a plugin runs backend-side and
            # cannot know the reader's locale.
            warnings.append(
                BRIMNotice(
                    severity="info",
                    code="ca_succession_transfer_in",
                    message=(
                        f"Sono stati identificati dei titoli trasferiti da un altro dossier ({len(succession_rows)} righe).\n"
                        "Sono stati registrati come transazioni di tipo «Rettifica» perché non hanno un movimento di cassa "
                        "associato: si suppone quindi che fossero già tuoi presso un altro broker.\n"
                        "In caso affermativo, e se quel broker è tracciato su LibreFolio, importando l'altra metà della "
                        "transazione il sistema proporrà di collegare le due e di trasformarle in un «Trasferimento titoli».\n"
                        "Di seguito le righe in dettaglio:"
                    ),
                    context={"row_count": len(succession_rows)},
                    evidence=[
                        BRIMEvidence(
                            title="Righe di trasferimento",
                            headers=sec_evidence_headers,
                            rows=[sec_row_values(r) for _, r in succession_rows],
                            row_numbers=[num for num, _ in succession_rows],
                        )
                    ],
                )
            )
        if not transactions:
            warnings.append(BRIMNotice(severity="warning", code="ca_securities_empty", message="Nessuna transazione valida trovata nel file"))

        _attach_maturity_notices(transactions, extracted_assets)

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

    def _classify_account_row(self, causale: str, description: str, amount: Decimal, currency: str) -> tuple[TransactionType, Currency, str]:
        """Map one account-movements row to a ``(type, cash, tier)`` triple.

        The tier is the registry level the causale fell into (see the module-level
        registry constants). It carries no accounting meaning: it tells the caller
        *how confident the plugin is*, so it can stay silent, explain itself, or
        stop the import.

        Tier 1 — typed (verbatim amounts, per-row currency; identifiable income —
        bond coupon or dividend, both carrying an ISIN — is asset-linked by the
        caller, bank interest stays unallocated):
        - securities fees/taxes -> TAX (capital gain / imposta / bollo / ritenuta)
          or FEE (management, administration, coupon-detach, monthly canone);
        - coupons / dividends / credit interest -> INTEREST, or DIVIDEND when the
          row both mentions a dividend and names a security (ISIN).

        Tiers 2-4 all produce DEPOSIT/WITHDRAWAL by sign — the cash is always
        booked correctly — and differ only in what the caller must then say about
        it: nothing (tier 3), an INFO notice (tier 4), or a blocking todo (tier 2).

        Sign-robust: a positive fee is treated as a refund (DEPOSIT), negative
        income as a clawback (WITHDRAWAL). BRIM sign convention: FEE/TAX and
        WITHDRAWAL carry cash < 0; INTEREST/DIVIDEND and DEPOSIT carry cash > 0.
        """
        desc_u = description.upper()
        abs_amt = abs(amount)

        # --- Tier 1: typed ---------------------------------------------------
        # Fees / taxes: securities operation charges, account charges, monthly canone.
        if causale in _ACCT_FEETAX_CAUSALI or (causale in _ACCT_CANONE_CAUSALI and amount < 0):
            if amount > 0:  # refunded charge
                return TransactionType.DEPOSIT, Currency(code=currency, amount=abs_amt), _TIER_TYPED
            tx_type = TransactionType.TAX if any(kw in desc_u for kw in _TAX_KEYWORDS) else TransactionType.FEE
            return tx_type, Currency(code=currency, amount=-abs_amt), _TIER_TYPED

        # Income: coupons, dividends, credit interest.
        if causale in _ACCT_INCOME_CAUSALI or (causale in _ACCT_CANONE_CAUSALI and amount > 0):
            if amount < 0:  # clawed-back income
                return TransactionType.WITHDRAWAL, Currency(code=currency, amount=-abs_amt), _TIER_TYPED
            is_dividend = any(kw in desc_u for kw in _DIVIDEND_KEYWORDS) and _names_an_asset(desc_u)
            tx_type = TransactionType.DIVIDEND if is_dividend else TransactionType.INTEREST
            return tx_type, Currency(code=currency, amount=abs_amt), _TIER_TYPED

        # --- Tiers 2-4: cash by sign, differing only in what we declare -------
        if causale in _ACCT_UNRESOLVED_CAUSALI:
            tier = _TIER_UNRESOLVED
        elif causale in _ACCT_SCT_CAUSALI and amount > 0 and _sct_fund_redemption_name(description):
            # An incoming transfer that pays out a fund: cash-correct, security missing.
            tier = _TIER_UNRESOLVED
        elif causale in _ACCT_DECLARED_CASH_CAUSALI:
            tier = _TIER_DECLARED_CASH
        else:
            tier = _TIER_UNKNOWN

        if amount > 0:
            return TransactionType.DEPOSIT, Currency(code=currency, amount=abs_amt), tier
        return TransactionType.WITHDRAWAL, Currency(code=currency, amount=-abs_amt), tier

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
        warnings: List[BRIMNotice] = []
        validation_issues: List[BRIMValidationIssue] = []
        field_todos: List[BRIMFieldTodo] = []
        extracted_assets: Dict[int, BRIMExtractedAssetInfo] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE

        def asset_id_for(*, key: str, name: str, isin: Optional[str]) -> int:
            nonlocal next_fake_id
            if key in asset_to_fake_id:
                existing_id = asset_to_fake_id[key]
                # Rows arrive in file order, so a charge on a security can be read before
                # the coupon that actually names it. The charge can only offer the ISIN as
                # a placeholder, so let a real name take its place when one turns up.
                known = extracted_assets[existing_id]
                current = known.extracted_name or ""
                upgrade = (current == isin and name != isin) or _is_truncation_of(current, name)
                if upgrade:
                    extracted_assets[existing_id] = BRIMExtractedAssetInfo(extracted_symbol=known.extracted_symbol, extracted_isin=known.extracted_isin, extracted_name=name)
                return existing_id
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

        def charge_asset_id(desc: str) -> Optional[int]:
            """Link a securities charge to the instrument it was charged for, by ISIN.

            Keyed exactly like an income row so the fee joins the same security. The name
            is read from the fragment that follows the ISIN, never from the head of the
            line: a charge line opens by describing the *charge* ("SPESE STACCO CEDOLA
            DEL 21/05/2026 DOSSIER: ..."), and taking that text as a name would put the
            fee's own wording in the user's asset list.
            """
            match = _ISIN_RE.search(desc.upper())
            if match is None:
                return None
            isin = match.group(0)
            return asset_id_for(key=f"isin:{isin}", name=_charge_asset_name(desc, isin), isin=isin)

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

        # Column labels of the real header row, used to render the source row back
        # to the user as a navigable table. Only the mapped columns are kept, in a
        # stable order: the raw header also carries the export's filler columns.
        evidence_cols = [(label, col[key]) for label, key in (("Data Op.", "date"), ("Causale", "causale"), ("Descrizione", "descrizione"), ("Importo", "importo"), ("Divisa", "divisa")) if col.get(key) is not None]
        evidence_headers = [label for label, _ in evidence_cols]

        def source_row_evidence(row: Sequence, row_num: int, *, comment: Optional[str] = None, title: str = "Riga del file") -> BRIMEvidence:
            """The originating file row as a one-row table, so the user can check us.

            Attached to the todo at the moment the plugin gives up, which is the only
            moment the row is still in hand: re-reading the file preview later would
            cost a second fetch and, worse, misalign the indexes if the preview
            truncates or paginates.
            """
            return BRIMEvidence(
                title=title,
                headers=evidence_headers,
                rows=[[io.cell_str(row[cidx]) if cidx < len(row) else "" for _, cidx in evidence_cols]],
                row_numbers=[row_num],
                comment=comment,
            )

        income_identity_by_date: Dict = {}
        # ISIN -> {name, nominals} built from the income rows (B2, filled in the pre-pass below).
        nominal_by_isin: Dict[str, Dict] = {}
        # Securities charges already booked as rows of their own, by date. Used to tell the
        # user whether a commission is *inside* a trade total or *beside* it: extracting a
        # charge that the file already books separately would count it twice.
        charge_rows_by_date: Dict = {}
        # Tier-4 rows, grouped by causale, so an unregistered causale is reported once
        # with its rows rather than once per row.
        unknown_causali: Dict[str, List[tuple[int, Sequence]]] = {}

        for identity_offset, row in enumerate(rows[header_idx + 1 :], start=header_idx + 2):
            if io.is_blank_row(row):
                continue
            identity_date = io.to_date(io.row_get(row, col, "date"))
            identity_causale = io.cell_str(io.row_get(row, col, "causale")).upper()
            identity_description = io.cell_str(io.row_get(row, col, "descrizione"))
            if identity_date is None:
                continue
            if identity_causale in _ACCT_FEETAX_CAUSALI_SECURITIES:
                charge_amount = io.to_decimal_it(io.row_get(row, col, "importo"))
                if charge_amount is not None and charge_amount != 0:
                    charge_rows_by_date.setdefault(identity_date, []).append({"row": row, "row_num": identity_offset, "amount": charge_amount, "description": identity_description})
            if identity_causale not in _ACCT_INCOME_CAUSALI:
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
            # B2 — name -> (ISIN, nominal) index over the whole file. A trade row names
            # its instrument but never its quantity; the coupons of that same bond carry
            # both the ISIN and the NOMINALE, i.e. exactly what the trade is missing.
            # Same mechanism as income_identity_by_date, keyed by name instead of date
            # because a purchase and its coupons never share one.
            identity_name = _income_asset_name(identity_description, isin)
            entry = nominal_by_isin.setdefault(isin, {"isin": isin, "name": identity_name, "nominals": set(), "row": row, "row_num": identity_offset})
            if len(identity_name) > len(entry["name"]):
                entry["name"] = identity_name  # keep the least truncated form seen
            entry["nominals"].add(nominale)

        for entry in nominal_by_isin.values():
            entry["norm"] = _normalize_trade_name(entry["name"])

        def nominal_candidates_for(trade_name: str) -> List[Dict]:
            """Coupon-derived identities whose name is the same instrument as ``trade_name``."""
            norm = _normalize_trade_name(trade_name)
            if not norm:
                return []
            return [entry for entry in nominal_by_isin.values() if _prefix_matches(norm, entry["norm"])]

        def charge_rows_near(tx_date, *, days: int = 3) -> List[Dict]:
            """Securities-charge rows the file books on its own within ``days`` of a trade.

            The window is deliberately wide: a commission is often value-dated a day or
            two off the trade. False positives are harmless here — the suggestion only
            *warns* the user not to extract a charge twice, it never moves money.
            """
            found: List[Dict] = []
            for delta_days in range(-days, days + 1):
                found.extend(charge_rows_by_date.get(tx_date + timedelta(days=delta_days), []))
            return sorted(found, key=lambda item: item["row_num"])

        def split_suggestions_for(*, tx_date, is_buy: bool, amount: Decimal, currency: str, description: str, nominal: Optional[Decimal] = None) -> List[str]:
            """What the *rest of the file* can say about a bundled trade total.

            Every line is read off the export, never inferred from market data: the point
            is to narrow down what the total contains, so the user splits it from their
            contract note instead of guessing. Order matters — the double-counting warning
            comes first because it is the only one that can cause a wrong import.
            """
            hints: List[str] = []
            nearby = charge_rows_near(tx_date)
            if nearby:
                listed = ", ".join(f"riga {item['row_num']} ({_fmt_money(abs(item['amount']))} {currency})" for item in nearby[:3])
                hints.append(f"Il file registra già delle spese su titoli a ridosso di questa data — {listed}. Sono transazioni a sé: se le scorpori anche da qui le conti due volte.")
            else:
                hints.append("Nei giorni intorno a questa operazione il file non registra nessuna riga di commissioni: se una commissione c'è stata, è dentro questo totale.")
            upper = (description or "").upper()
            is_fund = any(token in upper for token in ("SICAV", "FONDO", "FUND", "ETF"))
            if is_fund:
                hints.append("È un fondo, non un'obbligazione: non ci sono ratei cedolari da scorporare, quindi la differenza rispetto al prezzo sono commissioni o imposte.")
            elif is_buy:
                hints.append("Se è un'obbligazione e non l'hai comprata all'emissione, il totale contiene anche il rateo cedolare che hai rimborsato al venditore: registralo come voce a parte, non fa parte del costo del titolo.")
            if nominal is not None and abs(amount) == nominal:
                hints.append("Il totale coincide al centesimo con il valore nominale: è il caso tipico dell'acquisto all'emissione, alla pari e senza oneri. Se è andata così, non c'è nulla da scorporare.")
            if not is_buy:
                hints.append("Su una vendita l'importo accreditato è già netto: per registrare il ricavo lordo scorpora qui le spese trattenute, l'incasso sul conto non cambia.")
            hints.append("I numeri esatti sono sulla nota informativa dell'operazione: da lì leggi il controvalore del solo titolo e le singole voci di spesa.")
            return hints

        def try_account_trade(
            *,
            row: Sequence,
            offset: int,
            tx_date,
            causale: str,
            description: str,
            amount: Decimal,
            currency: str,
            context: str,
        ) -> Optional[Dict]:
            """Book a ``COMPRAVENDITA`` row as a real BUY/SELL when the file allows it.

            Returns ``None`` once the row is dealt with (trade created, or dropped with a
            validation issue), or a ``{"reason", ...}`` dict saying why it could not be
            typed, so the caller falls back to cash and explains the gap in the user's terms.

            ⚠️ **No cash counterpart here.** In the securities-only export the cash side is
            absent and has to be synthesised; on the account statement *the row itself is
            the cash*, so adding a counterpart would double the movement.
            """
            trade_type, direction_reason = _classify_trade_direction(description, amount)
            if trade_type is None:
                return {"reason": direction_reason}

            trade_name = _trade_asset_name(description)
            if not trade_name:
                return {"reason": "no_name", "type": trade_type}

            candidates = nominal_candidates_for(trade_name)
            if not candidates:
                return {"reason": "no_quantity", "type": trade_type, "name": trade_name}
            if len(candidates) > 1:
                return {"reason": "ambiguous_name", "type": trade_type, "name": trade_name, "candidates": candidates}
            identity = candidates[0]
            if len(identity["nominals"]) > 1:
                return {"reason": "ambiguous_nominal", "type": trade_type, "name": trade_name, "candidates": candidates}

            nominal: Decimal = next(iter(identity["nominals"]))
            best_name = identity["name"] if len(identity["name"]) >= len(trade_name) else trade_name
            asset_id = asset_id_for(key=f"isin:{identity['isin']}", name=best_name, isin=identity["isin"])
            is_buy = trade_type == TransactionType.BUY
            created = self._create_transaction(
                row_num=offset,
                transactions=transactions,
                validation_issues=validation_issues,
                context=context,
                broker_id=broker_id,
                asset_id=asset_id,
                type=trade_type,
                date=tx_date,
                quantity=nominal if is_buy else -nominal,
                cash=Currency(code=currency, amount=-abs(amount) if is_buy else abs(amount)),
                description=(description or causale)[:500],
                tags=["import", "credit_agricole", _slug_causale(causale), "account_trade"],
            )
            if created is None:
                return None

            # B3 — the row carries one net number that packs several events together.
            # The flag does not wait for a contradiction: this layout *never* separates
            # the price of a security from the charges levied on it, so every trade it
            # books is potentially bundled and every trade is flagged. Making the warning
            # depend on a coupon being present would make it depend on what else happens
            # to sit in the same export — import the purchase alone, in a period with no
            # coupon, and the identical row would pass unflagged.
            #
            # Deriving the breakdown ourselves was tried on the real data and does not
            # reconcile (one of the two residues comes out negative), so the plugin states
            # the problem instead of inventing an answer. It goes out as a field todo
            # rather than a notice because the user *can* answer it: the numbers are on
            # their contract note, and the correction step turns the row into a trade at
            # the clean price plus one leg per charge.
            delta = abs(amount) - nominal
            verb = "acquisto" if is_buy else "vendita"
            if not is_buy:
                # The coupon says how much of the bond was *held*, not how much was sold.
                # For a full sale the two coincide, for a partial one they do not, and the
                # file never says which — so the quantity is declared as presumed rather
                # than passed off as read. Kept separate from the bundled-amount todo
                # below: they ask the user two different questions (how many, how much of
                # what), and merging them would make answering one look like answering both.
                field_todos.append(
                    BRIMFieldTodo(
                        tx_index=len(transactions) - 1,
                        field="quantity",
                        severity="warning",
                        reason_code="ca_account_trade_sell_quantity_presumed",
                        message=f"Riga {offset}: vendita di {best_name}. Ho usato {_fmt_money(nominal)} come quantità, cioè il valore nominale che risulta dalle cedole. Se hai venduto solo una parte, correggila.",
                        context={"causale": causale, "row": offset, "isin": identity["isin"], "nominale": str(nominal)},
                        evidence=[
                            source_row_evidence(
                                row,
                                offset,
                                comment=(f"Il file dice quanto denaro è entrato, non quante quote sono uscite. Le cedole di {identity['isin']} " f"riportano un nominale di {nominal}: è la posizione, quindi è giusto solo se hai venduto tutto."),
                            )
                        ],
                    )
                )
            if not is_buy:
                trade_comment = f"Sul conto sono entrati {_fmt_money(abs(amount))} {currency}, ed è un importo netto: le spese sulla vendita sono già state " "trattenute e il file non le espone. Il ricavo lordo e le singole spese non sono quindi ricavabili da questa riga."
            elif delta != 0:
                trade_comment = (
                    f"Dal conto sono usciti {_fmt_money(abs(amount))} {currency}. Guardando il resto del file ho trovato una cedola dello stesso "
                    f"titolo (riga {identity['row_num']}) che dichiara {_fmt_money(nominal)} di valore nominale, cioè il capitale del titolo. "
                    f"I due numeri non coincidono ({_fmt_money(abs(delta))} {currency} di differenza): il totale di questa riga mette insieme il "
                    "prezzo del titolo, il rateo cedolare maturato e le eventuali commissioni, e il file non li separa. La cassa è comunque "
                    "giusta; è il costo di carico a essere approssimato."
                )
            else:
                trade_comment = (
                    f"Dal conto sono usciti {_fmt_money(abs(amount))} {currency}, esattamente quanto il valore nominale dichiarato dalla cedola "
                    f"alla riga {identity['row_num']}. È il caso dell'acquisto all'emissione, alla pari e senza oneri: se è andata così non c'è "
                    "nulla da correggere. Se invece la nota informativa espone commissioni o rateo, il file li ha inglobati qui dentro."
                )
            field_todos.append(
                BRIMFieldTodo(
                    tx_index=len(transactions) - 1,
                    field="cash",
                    severity="warning",
                    reason_code="ca_account_trade_bundled_amount",
                    message=f"Riga {offset}: {verb} di {best_name} — l'importo di questa riga potrebbe raggruppare più voci insieme.",
                    context={
                        "causale": causale,
                        "row": offset,
                        "isin": identity["isin"],
                        "cash": str(abs(amount)),
                        "nominale": str(nominal),
                        "delta": str(delta),
                        "currency": currency,
                        "nominale_row": identity["row_num"],
                        # The nominal is the quantity in both directions, but it is a *term
                        # of comparison* only on a purchase: on a sale the proceeds have no
                        # reason to resemble the face value, and showing them side by side
                        # would invite the user to read a gap that means nothing.
                        "compare_nominal": is_buy,
                        "split_hint": "trade_charges",
                        "split_suggestions": split_suggestions_for(tx_date=tx_date, is_buy=is_buy, amount=amount, currency=currency, description=description, nominal=nominal),
                    },
                    evidence=[
                        source_row_evidence(row, offset, title=f"Riga di {verb}", comment=trade_comment),
                        source_row_evidence(
                            identity["row"],
                            identity["row_num"],
                            title="Cedola che ha fornito il nominale",
                            comment=(f"L'ISIN {identity['isin']} e il valore nominale {_fmt_money(nominal)} vengono da qui: è il capitale del titolo, " "cioè quanto la banca rimborsa a scadenza, non quanto hai pagato."),
                        ),
                    ],
                )
            )
            return None

        def trade_fallback_message(offset: int, info: Dict, booked_as: str) -> tuple[str, str]:
            """User-facing message + evidence comment for a trade that stayed cash."""
            reason = info.get("reason")
            name = info.get("name") or ""
            if reason == "sign_mismatch":
                return (
                    f"Riga {offset}: la descrizione e il segno dell'importo si contraddicono. Verifica l'operazione e completala.",
                    "La descrizione parla di acquisto ma il denaro entra (o viceversa). Non tipizzo su un dato che si contraddice: " f"l'ho registrata come {booked_as} di cassa. Apri la transazione, scegli il tipo giusto e il titolo.",
                )
            if reason == "ambiguous_name":
                names = ", ".join(f"{c['name']} ({c['isin']})" for c in info.get("candidates", []))
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
            # no_keyword / no_name — the description does not say what happened.
            return (
                f"Riga {offset}: operazione su titoli registrata come movimento di cassa perché da questo file non ricavo quantità e strumento. Verificala e completala.",
                "Questa riga è un'operazione su titoli, ma la descrizione non riporta quantità né codice del titolo. " f"L'ho registrata come {booked_as} di cassa: l'importo è giusto, il titolo manca. " "Apri la transazione, cambia il tipo in acquisto o vendita e scegli il titolo.",
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
                warnings.append(
                    BRIMNotice(
                        severity="warning",
                        code="ca_account_invalid_amount",
                        message=f"Riga {offset}: importo non valido per '{causale}', saltata",
                        context={"causale": causale, "row": offset},
                        evidence=[source_row_evidence(row, offset, comment="L'importo di questa riga non è leggibile come numero, quindi la riga è stata scartata.")],
                    )
                )
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
                    warnings.append(
                        BRIMNotice(
                            severity="warning",
                            code="ca_account_maturity_unlinked",
                            message=f"Riga {offset}: scadenza/rimborso '{description}' non collegabile a un titolo (ISIN e nominale non trovati nella stessa data); importata interamente come vendita a valore nominale (par 100, nessuna quota di interesse) — verifica il nominale.",
                            context={"causale": causale, "row": offset},
                            evidence=[source_row_evidence(row, offset, comment="Per scorporare il capitale dal premio mi serve il nominale, che di solito ricavo dalla cedola pagata lo stesso giorno. Qui quella cedola non c'è, quindi ho trattato tutto l'importo come rimborso alla pari.")],
                        )
                    )
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

            trade_fallback: Optional[Dict] = None
            if causale in _ACCT_UNRESOLVED_CAUSALI:
                trade_fallback = try_account_trade(
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
                    continue  # booked as a real trade — nothing left to fall back on
            elif causale in _ACCT_SCT_CAUSALI and amount > 0:
                # A fund redemption paid by wire. The name is readable, the number of
                # units never is: a fund states the countervalue, not the quantity, and
                # this layout has no coupon to recover it from. Straight to the fallback
                # so the user supplies the quantity in the correction step.
                fund_name = _sct_fund_redemption_name(description)
                if fund_name:
                    trade_fallback = {"reason": "fund_redemption", "type": TransactionType.SELL, "name": fund_name}

            tx_type, cash, tier = self._classify_account_row(causale, description, amount, currency)
            # Coupons (INTEREST) and dividends both name their security by ISIN — link the
            # income to that bond/fund so it shows under the asset in the FIFO lot detail.
            # Bank credit interest ("INTERESSI/COMPETENZE" credit) carries no ISIN and stays
            # unallocated (income_asset_id returns None).
            # A charge on a securities operation names its security by ISIN as often as a
            # coupon does ("SPESE STACCO CEDOLA ... TIT: IT000..."), so look it up the same
            # way: a fee attached to the bond it was charged for lands in that bond's cost
            # basis instead of drifting into unallocated account expenses.
            if tx_type in (TransactionType.INTEREST, TransactionType.DIVIDEND):
                asset_id = income_asset_id(description)
            elif tx_type in (TransactionType.FEE, TransactionType.TAX):
                asset_id = charge_asset_id(description)
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
                withholding_match = _ACCOUNT_RITENUTA_RE.search(description)
                if withholding_match is not None:
                    parsed = io.to_decimal_it(withholding_match.group("ritenuta"))
                    if parsed is not None and parsed > 0:
                        withholding = parsed
                        cash = Currency(code=currency, amount=cash.amount + withholding)

            created = self._create_transaction(
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

            if created is None:
                continue

            if withholding is not None:
                self._create_transaction(
                    row_num=offset,
                    transactions=transactions,
                    validation_issues=validation_issues,
                    context=f"Withholding tax on {context}",
                    broker_id=broker_id,
                    asset_id=asset_id,
                    type=TransactionType.TAX,
                    date=tx_date,
                    quantity=Decimal("0"),
                    cash=Currency(code=currency, amount=-withholding),
                    description=f"[{causale} — ritenuta] {description}"[:500],
                    tags=["import", "credit_agricole", _slug_causale(causale), "withholding_tax"],
                )

            if tier == _TIER_UNRESOLVED:
                # The money is right, the security (or its quantity) is missing. Block
                # rather than guess: a silent withdrawal loses the position entirely, and
                # the loss only surfaces much later as an unexplained gap in the cost basis.
                booked_as = "prelievo" if tx_type == TransactionType.WITHDRAWAL else "versamento"
                todo_message, todo_comment = trade_fallback_message(offset, trade_fallback or {}, booked_as)
                field_todos.append(
                    BRIMFieldTodo(
                        tx_index=len(transactions) - 1,
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
                            "split_suggestions": split_suggestions_for(tx_date=tx_date, is_buy=amount < 0, amount=amount, currency=currency, description=description),
                        },
                        evidence=[source_row_evidence(row, offset, comment=todo_comment)],
                    )
                )
            elif tier == _TIER_UNKNOWN:
                unknown_causali.setdefault(causale, []).append((offset, row))

            # A charge on a securities operation belongs to the security it was charged
            # for. This layout names neither, so the charge lands unallocated and silently
            # skews the cost basis of whatever it belonged to. Flagged as a warning, not a
            # blocker: the file may genuinely never say, and a fee is still a real expense.
            if causale in _ACCT_FEETAX_CAUSALI_SECURITIES and tx_type in (TransactionType.FEE, TransactionType.TAX) and asset_id is None:
                field_todos.append(
                    BRIMFieldTodo(
                        tx_index=len(transactions) - 1,
                        field="asset_id",
                        severity="warning",
                        reason_code="ca_account_charge_unallocated",
                        message=f"Riga {offset}: spesa su operazione titoli non collegata a nessun titolo. Assegnala al titolo giusto, oppure tienila così se riguarda il conto.",
                        context={"causale": causale, "row": offset},
                        evidence=[
                            source_row_evidence(
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

        if unknown_causali:
            # Not an error: the cash is booked correctly by sign. It is a disclosure —
            # a causale the registry has never seen may well be a securities operation
            # in disguise, exactly like COMPRAVENDITA was.
            total_rows = sum(len(items) for items in unknown_causali.values())
            warnings.append(
                BRIMNotice(
                    severity="info",
                    code="ca_unknown_causale",
                    message=(f"{total_rows} righe con {len(unknown_causali)} causali non ancora previste sono state registrate come versamento o prelievo, in base al segno dell'importo. " "Se una di queste è in realtà un'operazione su titoli, correggila prima di importare."),
                    context={"causali": sorted(unknown_causali), "row_count": total_rows},
                    evidence=[
                        BRIMEvidence(
                            title="Righe con causale non prevista",
                            headers=evidence_headers,
                            rows=[[io.cell_str(r[cidx]) if cidx < len(r) else "" for _, cidx in evidence_cols] for items in unknown_causali.values() for _, r in items],
                            row_numbers=[num for items in unknown_causali.values() for num, _ in items],
                        )
                    ],
                )
            )

        if not transactions:
            warnings.append(BRIMNotice(severity="warning", code="ca_account_empty", message="Nessun movimento di conto trovato nel file"))

        _attach_maturity_notices(transactions, extracted_assets)

        logger.info(
            "Crédit Agricole account movements parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            field_todo_count=len(field_todos),
            unknown_causale_count=len(unknown_causali),
        )
        return BRIMParseOutput(
            transactions=transactions,
            warnings=warnings,
            validation_issues=validation_issues,
            field_todos=field_todos,
            extracted_assets=extracted_assets,
        )
