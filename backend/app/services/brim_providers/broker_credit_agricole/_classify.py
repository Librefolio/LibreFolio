"""Crédit Agricole: the causale registry and the pure classifiers of a row.

What a row of the two Crédit Agricole exports (the securities movements, the account movements) is, as a function of its
causale, its description and its amount: no file, no state, no database. The plugin's parse and the report-set analysis
(``_report_set.py``) read the same tables, so a row is classified one way wherever it is read.

The registry puts every account causale in exactly one of four tiers (typed, unresolved, declared cash, unknown): see the
comment above ``TIER_TYPED``.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Optional, Sequence

from backend.app.db.models import TransactionType
from backend.app.schemas.common import Currency
from backend.app.services.brim_providers import _brim_io as io

# Causali that represent the nonno -> nonna succession transfers (Controvalore 0).
SUCCESSION_CAUSALI = {"GIRO ALTRO DOSSIER", "VERS.TITOLI"}

# Causali that increase a securities position (cash buys and fund subscriptions).
BUY_CAUSALI = {"ACQ.CONT.SU MERC.", "SICAV: SOTTOSCR"}

# Name keywords that identify a bond (price quoted per 100 of nominal).
BOND_KEYWORDS = ("BTP", "BOT", "CCT", "CTZ", "BUND", "OAT", "OBBLIG", "CCTEU")


def is_bond(name: str) -> bool:
    """Heuristic: a bond is priced per 100 of nominal; a fund is priced per unit."""
    upper = name.upper()
    return any(kw in upper for kw in BOND_KEYWORDS)


# End-of-export recap/summary rows CA appends after the last real movement.
# The XLSX export closes with labelled totals ("Totale Entrate/Uscite/Movimenti €"
# on the account layout, "Riepilogo ..." on some securities layouts); the CSV
# export omits them entirely. They carry no operation date and must never be
# imported as a transaction, so the parser recognises and drops them explicitly.
RECAP_FOOTER_MARKERS = ("TOTALE", "RIEPILOGO", "SALDO FINALE")


def is_recap_footer(text: str) -> bool:
    """True for a CA end-of-export recap/summary row identified by its label."""
    return text.strip().upper().startswith(RECAP_FOOTER_MARKERS)


ISO_CCY_RE = re.compile(r"^[A-Za-z]{3}$")


def resolve_currency(row: Sequence, divisa_cols: Sequence[int], default: str = "EUR") -> str:
    """Pick the first valid ISO-like currency code among the ``Divisa`` columns.

    The XLSX variant duplicates the causale into the transaction ``Divisa``
    column, so the header position alone is unreliable; scanning every
    ``Divisa``/``Divisa prezzo`` column and taking the first 3-letter code is
    robust for both CSV and XLSX.
    """
    for cidx in divisa_cols:
        if cidx < len(row):
            value = io.cell_str(row[cidx])
            if ISO_CCY_RE.match(value):
                return value.upper()
    return default


# ---------------------------------------------------------------------------
# Account "Lista Movimenti Conto" layout — cash-movement classification
# ---------------------------------------------------------------------------

# ISIN pattern used to decide whether an income row names a security. Both bond
# coupons (``CEDOLA:… ISIN …``) and dividends reference their security by ISIN and
# are linked to it; bank credit interest carries no ISIN and stays unallocated.
ISIN_RE = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b")

# Causali whose rows are coupon/dividend income (cash in, unless clawed back).
ACCT_INCOME_CAUSALI = {"CEDOLE, DIVIDENDI, PREMI ESTRATTI"}

# Account cash rows that can represent a matured / redeemed security. When the
# same account export also contains the final coupon with an ISIN + NOMINALE, the
# nominal is recovered in-file and the disposal is split into par SELL + premium
# INTEREST. When it is not identifiable, the whole redemption is still booked as a
# SELL (everything as sold, unknown nominal) — never a generic DEPOSIT.
ACCT_MATURITY_CAUSALI = {"TITOLI SCADUTI O ESTRATTI"}

# Causali whose rows are securities fees/taxes (split by description keyword).
ACCT_FEETAX_CAUSALI = {"COMMISS./SPESE SU OPERAZ. TITOLI", "COMMISSIONI/SPESE"}

# The subset that is a charge *on a security*, and therefore belongs to one. The
# others ("COMMISSIONI/SPESE", the monthly canone) are account charges and are
# correctly left unallocated, so only these are worth flagging when no asset is found.
ACCT_FEETAX_CAUSALI_SECURITIES = {"COMMISS./SPESE SU OPERAZ. TITOLI"}

# "INTERESSI/COMPETENZE" is sign-dependent: a debit is the account fee
# (CANONE MENSILE), a credit is real interest income.
ACCT_CANONE_CAUSALI = {"INTERESSI/COMPETENZE"}

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
ACCT_DECLARED_CASH_CAUSALI = {
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
ACCT_UNRESOLVED_CAUSALI = {"COMPRAVENDITA TITOLI/FONDI/OPZIONI"}

# Direction keywords inside a COMPRAVENDITA description. The sign of the amount
# confirms them; a disagreement between word and sign is never resolved by
# guessing — the row stays cash and is flagged instead.
ACCT_TRADE_BUY_KEYWORDS = ("NOTA INF. ACQ", "NOTA INF.ACQ", "ACQUIST", "SOTTOSC")
ACCT_TRADE_SELL_KEYWORDS = ("NOTA INF. VEND", "NOTA INF.VEND", "VENDIT", "VEND.", "DISINVEST", "RIMBORS")

# Tier 2b — a fund redemption does not reach the account as a securities operation:
# the fund house simply wires the money over, so the row lands under the ordinary
# transfer causale and looks exactly like any other incoming payment. Booking it as
# a plain deposit leaves the position open forever, and the loss only surfaces later
# as an unexplained gap in the cost basis. See ``sct_fund_redemption_name`` for how
# the two are told apart.
ACCT_SCT_CAUSALI = {"GIROCONTO/BONIFICO"}
# The ordering party of an incoming transfer, printed before the operation text:
#   ORD:AMUNDI PRIMO INVESTIMENTO DT.ORD:000000 DESCR.OPERAZIONE SCT::RIMBORSI ...
ACCT_SCT_ORDER_RE = re.compile(r"\bORD\s*:\s*(?P<party>.+?)\s+DT\.?\s*ORD\s*:(?P<rest>.*)$", re.IGNORECASE | re.DOTALL)
ACCT_SCT_REDEMPTION_KEYWORDS = ("RIMBORS", "DISINVEST", "LIQUIDAZ")
# Below this length an ordering party says nothing and would match by accident.
ACCT_SCT_PARTY_MIN = 8

# The instrument name inside a trade description, printed either after ``TIT:``
# (bonds) or after the order reference (funds):
#   NOTA INF. ACQ. TIT:BTP 01/03/35 3,35%
#   SOTTOSC SICAV ORD.:2025/003955841 AMUNDI PIO GLOB EQ G
ACCT_TRADE_TIT_RE = re.compile(r"\bTIT\.?\s*:\s*(?P<name>.+)$", re.IGNORECASE)
ACCT_TRADE_ORDER_RE = re.compile(r"\bORD\.?\s*:\s*\S+\s+(?P<name>.+)$", re.IGNORECASE)
# Reference fragments that follow the name and are not part of it.
ACCT_TRADE_NAME_STOP_RE = re.compile(r"\s+(?:DOSS?(?:IER)?\.?\s*:|RUB\.?\s*:|DATA\s*:|MOV\s*[:.]).*$", re.IGNORECASE)
# Below this length a prefix match says nothing ("BTP" matches every bond).
ACCT_TRADE_NAME_MIN_MATCH = 6

# Tier labels returned by ``classify_account_row`` alongside the (type, cash) pair.
TIER_TYPED = "typed"
TIER_UNRESOLVED = "unresolved"
TIER_DECLARED_CASH = "declared_cash"
TIER_UNKNOWN = "unknown"

# Description keywords that make a fee row a TAX (capital gain, stamp duty,
# withholding) rather than a plain FEE (management/administration/coupon-detach).
TAX_KEYWORDS = ("CAPITAL GAIN", "D.LGS 461", "461/97", "IMPOSTA", "BOLLO", "RITENUTA")

# Description keyword that marks a dividend (vs a bond coupon "CEDOLA").
DIVIDEND_KEYWORDS = ("DIVIDEND",)

ACCOUNT_MATURITY_RE = re.compile(r"RIMB\.TIT\.\s*(?P<name>.+?)\s*\((?P<code>[^)]*)\)", re.IGNORECASE)
ACCOUNT_NOMINALE_RE = re.compile(r"\bNOMINALE\s*:\s*(?P<nominale>[\d\.\,]+)", re.IGNORECASE)
# Withholding spelled out inside an income description ("... ALIQ: 12,50 RITENUTA: 13,36").
ACCOUNT_RITENUTA_RE = re.compile(r"\bRITENUT[AE]\s*:\s*(?P<ritenuta>[\d\.\,]+)", re.IGNORECASE)


def slug_causale(causale: str) -> str:
    """Compact, tag-safe slug of a causale (``"CEDOLE, DIVIDENDI"`` -> ``cedole_dividendi``)."""
    return re.sub(r"[^a-z0-9]+", "_", causale.lower()).strip("_")


def names_an_asset(description_upper: str) -> bool:
    """True when the description carries an ISIN (gates DIVIDEND vs INTEREST)."""
    return bool(ISIN_RE.search(description_upper))


def income_asset_name(description: str, isin: str) -> str:
    """Best-effort security name for an account-mode income row (bond coupon or
    dividend): the text before the ISIN, minus a leading ``CEDOLA``/``DIVIDENDO``."""
    idx = description.upper().find(isin)
    head = description[:idx] if idx > 0 else description
    head = re.sub(r"^\s*(CEDOLA|DIVIDEND[OIA]?)\s*", "", head, flags=re.IGNORECASE).strip(" :-\t")
    return head or isin


def charge_asset_name(description: str, isin: str) -> str:
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


def is_truncation_of(short: str, full: str) -> bool:
    """True when ``short`` looks like ``full`` cut off by the bank's field width.

    Crédit Agricole prints the same security name at different widths depending on
    the row type, so the same instrument reaches us as both ``BTP 05/26 0.55FOICU``
    and ``BTP 05/26 0.55FOICUM``. Keeping the longer form avoids creating an asset
    under a name that will never match the one already in the portfolio.
    """
    return len(full) > len(short) and bool(short) and full.upper().startswith(short.upper())


def digits_only(value: str) -> str:
    """Return only decimal digits from a broker identifier fragment."""
    return re.sub(r"\D+", "", value)


def fmt_money(value: Decimal) -> str:
    """Italian thousands/decimal notation, the way the statement itself writes numbers.

    The messages this plugin emits are read next to the bank's own rows: ``46603.73``
    beside ``46.603,73`` reads as a different number at a glance, and the whole point of
    these messages is that the user can check them against the file.
    """
    return f"{value:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def classify_trade_direction(description: str, amount: Decimal) -> tuple[Optional[TransactionType], str]:
    """Direction of a ``COMPRAVENDITA`` row from its description, confirmed by the sign.

    Returns ``(type, reason)`` where reason is one of ``ok`` / ``no_keyword`` /
    ``sign_mismatch``. Word and sign must agree: a purchase spends money, a sale
    brings it in. When they disagree the row is *not* typed — a trade booked in the
    wrong direction is far worse than one left to the user, because it opens a
    position that silently poisons every FIFO match downstream.
    """
    upper = description.upper()
    is_buy_word = any(kw in upper for kw in ACCT_TRADE_BUY_KEYWORDS)
    is_sell_word = any(kw in upper for kw in ACCT_TRADE_SELL_KEYWORDS)
    if is_buy_word == is_sell_word:  # neither, or both (contradictory wording)
        return None, "no_keyword"
    if is_buy_word:
        return (TransactionType.BUY, "ok") if amount < 0 else (None, "sign_mismatch")
    return (TransactionType.SELL, "ok") if amount > 0 else (None, "sign_mismatch")


def trade_asset_name(description: str) -> str:
    """Best-effort instrument name carried by a ``COMPRAVENDITA`` description."""
    match = ACCT_TRADE_TIT_RE.search(description) or ACCT_TRADE_ORDER_RE.search(description)
    raw = match.group("name") if match else description
    return ACCT_TRADE_NAME_STOP_RE.sub("", raw).strip(" :-\t")


def normalize_trade_name(name: str) -> str:
    """Uppercase, whitespace-collapsed form used to compare truncated names."""
    return re.sub(r"\s+", " ", name).strip().upper()


def squash(text: str) -> str:
    """Uppercase, letters and digits only — the form that survives column wrapping.

    The bank breaks a long name across the column width and the break lands inside a
    word (``AMUNDI PRIMO INVES TIMENTO``), so any comparison that keeps whitespace
    fails on exactly the rows that matter.
    """
    return re.sub(r"[^A-Z0-9]+", "", text.upper())


def sct_fund_redemption_name(description: str) -> str:
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
    match = ACCT_SCT_ORDER_RE.search(description)
    if match is None:
        return ""
    party = normalize_trade_name(match.group("party"))
    rest = match.group("rest")
    if len(squash(party)) < ACCT_SCT_PARTY_MIN:
        return ""
    if not any(kw in rest.upper() for kw in ACCT_SCT_REDEMPTION_KEYWORDS):
        return ""
    if squash(party) not in squash(rest):
        return ""
    return party


def prefix_matches(a: str, b: str) -> bool:
    """True when two normalized names are the same instrument cut at different widths.

    The bank truncates the same security to a different length depending on the row
    type, so the trade may be the shorter form or the longer one — the comparison
    has to work in both directions, and equality would miss every real case.
    """
    if len(a) < ACCT_TRADE_NAME_MIN_MATCH or len(b) < ACCT_TRADE_NAME_MIN_MATCH:
        return False
    return a.startswith(b) or b.startswith(a)


def classify_account_row(causale: str, description: str, amount: Decimal, currency: str) -> tuple[TransactionType, Currency, str]:
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
    if causale in ACCT_FEETAX_CAUSALI or (causale in ACCT_CANONE_CAUSALI and amount < 0):
        if amount > 0:  # refunded charge
            return TransactionType.DEPOSIT, Currency(code=currency, amount=abs_amt), TIER_TYPED
        tx_type = TransactionType.TAX if any(kw in desc_u for kw in TAX_KEYWORDS) else TransactionType.FEE
        return tx_type, Currency(code=currency, amount=-abs_amt), TIER_TYPED

    # Income: coupons, dividends, credit interest.
    if causale in ACCT_INCOME_CAUSALI or (causale in ACCT_CANONE_CAUSALI and amount > 0):
        if amount < 0:  # clawed-back income
            return TransactionType.WITHDRAWAL, Currency(code=currency, amount=-abs_amt), TIER_TYPED
        is_dividend = any(kw in desc_u for kw in DIVIDEND_KEYWORDS) and names_an_asset(desc_u)
        tx_type = TransactionType.DIVIDEND if is_dividend else TransactionType.INTEREST
        return tx_type, Currency(code=currency, amount=abs_amt), TIER_TYPED

    # --- Tiers 2-4: cash by sign, differing only in what we declare -------
    if causale in ACCT_UNRESOLVED_CAUSALI:
        tier = TIER_UNRESOLVED
    elif causale in ACCT_SCT_CAUSALI and amount > 0 and sct_fund_redemption_name(description):
        # An incoming transfer that pays out a fund: cash-correct, security missing.
        tier = TIER_UNRESOLVED
    elif causale in ACCT_DECLARED_CASH_CAUSALI:
        tier = TIER_DECLARED_CASH
    else:
        tier = TIER_UNKNOWN

    if amount > 0:
        return TransactionType.DEPOSIT, Currency(code=currency, amount=abs_amt), tier
    return TransactionType.WITHDRAWAL, Currency(code=currency, amount=-abs_amt), tier
