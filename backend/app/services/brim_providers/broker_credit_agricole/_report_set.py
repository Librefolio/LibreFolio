"""Crédit Agricole as a report set: what the securities export and the account export say together.

The securities movements and the account movements are two views of the same facts. A coupon, a purchase, a fund
redemption or a maturity is a row in both; read apart, each is counted twice. This module reads the exports of a set,
decides which row of one is the same fact as which row of the other, and works out what the bank states about the cash.
It builds nothing the user imports: that is the combined file, written from this analysis.

The pieces, in the order the analysis runs:

1. **rows of one role** (rule M): several downloads of one export are joined day by day: identical rows count once; for a
   day the download with the most rows wins (a bank cuts an export short, it never adds a row);
2. **classes**: every row is a coupon, a buy, a redemption, a maturity, a transfer, a standalone cash row...;
3. **pairs**: a securities row and an account row of the same kind, the same amount to the cent and the same *value date*
   are one fact. Nothing is guessed: two candidates that would import something different are left out as ``ambiguous``;
4. **balances**: the XLSX states the account's opening and closing balance. Two consecutive statements either agree with the
   rows between them (``closed``), or differ because nothing covers the days between them (a ``hole``: the difference is
   money the files do not show), or differ although rows are there (``broken``: warn, never correct);
5. **truth points**: the opening, one per hole, and the closing balances to compare.

A transaction takes its date from the *operation date* column (``Data operazione``, ``Data Op.``), never from a value
date: the value date only pairs the rows (principle of the BRIM plugins: a movement is recorded when it happens).

Design and decisions: ``plan-phase01ImportTransactions.prompt.md``, "W5-7".
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.app.schemas.brim import BRIMCoverage, BRIMMemberSummary, BRIMNotice, BRIMSetShape
from backend.app.schemas.common import DateRangeModel
from backend.app.services.brim import brim_report_set_core as core
from backend.app.services.brim_providers import _brim_io as io
from backend.app.services.brim_providers.broker_credit_agricole._classify import (
    ACCOUNT_MATURITY_RE,
    ACCOUNT_RITENUTA_RE,
    ACCT_INCOME_CAUSALI,
    ACCT_MATURITY_CAUSALI,
    ACCT_SCT_CAUSALI,
    ACCT_UNRESOLVED_CAUSALI,
    BUY_CAUSALI,
    DIVIDEND_KEYWORDS,
    ISIN_RE,
    SUCCESSION_CAUSALI,
    classify_account_row,
    classify_trade_direction,
    income_asset_name,
    names_an_asset,
    sct_fund_redemption_name,
    trade_asset_name,
)
from backend.app.services.brim_providers.broker_credit_agricole._rows import (
    ROLE_ACCOUNT,
    ROLE_SECURITIES,
    AccountFile,
    AccountRow,
    SecuritiesFile,
    SecuritiesRow,
    account_fingerprint,
    detect_role,
    read_account,
    read_securities,
)

__all__ = ["Analysis", "describe_member", "describe_set", "detect_role"]

CURRENCY = "EUR"
MAX_MATCH_CANDIDATES = 8
CENT = core.CENT
ZERO = Decimal("0")

# --- classes -----------------------------------------------------------------

SECURITIES_CLASSES = {
    "CEDOLA": "coupon",
    "FONDI: RIMBORSO": "redeem",
    "TITOLI SCADUTI": "matured",
    **dict.fromkeys(BUY_CAUSALI, "buy"),
    **dict.fromkeys(SUCCESSION_CAUSALI, "transfer_in"),
}
#: Securities classes that carry cash, so that have a row in the account export.
PAIRED_SECURITIES = frozenset({"coupon", "buy", "redeem", "matured"})
#: Account class -> the securities class it is the other half of.
PAIRED_ACCOUNT = {"coupon": "coupon", "trade_buy": "buy", "redemption": "redeem", "maturity": "matured"}
#: Account classes that, without a securities row, still are real cash and are imported as they are.
STANDALONE_WITHOUT_PAIR = frozenset({"coupon", "dividend", "redemption", "maturity", "standalone"})

# --- zones, outcomes ---------------------------------------------------------

ZONE_BEFORE = "before"
ZONE_WINDOW = "window"
ZONE_GAP = "gap"


def classify_securities(row: SecuritiesRow) -> str:
    return SECURITIES_CLASSES.get(row.causale, "unknown")


def classify_account(row: AccountRow) -> Tuple[str, str]:
    """``(class, tier)`` of an account row: the class decides the pairing, the tier says whether its causale is known."""
    if row.amount is None:
        return "invalid", ""
    tier = classify_account_row(row.causale, row.description, row.amount, row.currency)[2]
    if row.causale in ACCT_MATURITY_CAUSALI and row.amount > 0:
        return "maturity", tier
    if row.causale in ACCT_UNRESOLVED_CAUSALI:
        trade_type, _reason = classify_trade_direction(row.description, row.amount)
        if trade_type is None:
            return "trade_unknown", tier
        return ("trade_buy" if row.amount < 0 else "trade_sell"), tier
    if row.causale in ACCT_SCT_CAUSALI and row.amount > 0 and sct_fund_redemption_name(row.description):
        return "redemption", tier
    if row.causale in ACCT_INCOME_CAUSALI and row.amount > 0:
        # A dividend (the word and a named security, the test the plugin uses for the DIVIDEND type) is no bond coupon: it
        # must never be paired with the coupon of the securities export that happens to have the same amount.
        description = row.description.upper()
        if any(keyword in description for keyword in DIVIDEND_KEYWORDS) and names_an_asset(description):
            return "dividend", tier
        return "coupon", tier
    return "standalone", tier


def account_name(row: AccountRow) -> str:
    """The security a paired account row names (the bank prints it truncated); empty when the row names none."""
    if row.klass == "coupon":
        isin = ISIN_RE.search(row.description.upper())
        return income_asset_name(row.description, isin.group(0)) if isin else ""
    if row.klass == "trade_buy":
        return trade_asset_name(row.description)
    if row.klass == "redemption":
        return sct_fund_redemption_name(row.description)
    if row.klass == "maturity":
        match = ACCOUNT_MATURITY_RE.search(row.description)
        return match.group("name").strip() if match else ""
    return ""


def account_isin(row: AccountRow) -> str:
    match = ISIN_RE.search(row.description.upper())
    return match.group(0) if match else ""


def account_withholding(row: AccountRow) -> Optional[Decimal]:
    """The withholding an income row spells out (``RITENUTA: 13,36``); the amount of the row is already net of it."""
    if row.klass != "coupon":
        return None
    match = ACCOUNT_RITENUTA_RE.search(row.description)
    if match is None:
        return None
    value = io.to_decimal_it(match.group("ritenuta"))
    return value if value is not None and value > 0 else None


def _account_trade_signature(row: AccountRow) -> Tuple[Any, ...]:
    """What an account row brings to the pair it is in: two rows with the same signature are interchangeable."""
    return (row.klass, row.amount, account_isin(row), account_withholding(row), core.norm(account_name(row)))


def _to_the_cent(amount: Optional[Decimal]) -> Decimal:
    """An amount to the cent, half-up on both sides of a pair: ``1000,005`` and ``1000,01`` are the same amount (known limit:
    ``1000,015`` against ``1000,01`` are not)."""
    return abs(amount or ZERO).quantize(CENT, rounding=ROUND_HALF_UP)


def _securities_key(row: SecuritiesRow) -> Tuple[Any, ...]:
    return (row.klass, row.value, _to_the_cent(row.ctv), row.currency)


def _account_key(row: AccountRow) -> Tuple[Any, ...]:
    return (PAIRED_ACCOUNT[row.klass], row.value, _to_the_cent(row.amount), row.currency)


def _assign(securities: List[SecuritiesRow], account: List[AccountRow]) -> Optional[List[Tuple[SecuritiesRow, AccountRow]]]:
    return core.assign(
        securities,
        account,
        max_candidates=MAX_MATCH_CANDIDATES,
        same_name=lambda sec, acc: core.compatible(sec.name, account_name(acc)),
        outcome_of=lambda sec: sec.trade_signature,
        label_of=lambda acc: acc.description,
        pair_outcome_of=lambda sec, acc: (sec.trade_signature, _account_trade_signature(acc)),
    )


def pair_rows(securities: Sequence[SecuritiesRow], account: Sequence[AccountRow]) -> Tuple[List[Tuple[SecuritiesRow, AccountRow]], List[Any]]:
    """The pairs, and the rows left out as ambiguous.

    A pair is the same kind of fact, the same amount to the cent and the same value date on both sides. A row without a value
    date, an amount or a kind that pairs takes part in no pair.
    """
    left = [row for row in securities if row.klass in PAIRED_SECURITIES and row.ctv is not None and row.value is not None]
    right = [row for row in account if row.klass in PAIRED_ACCOUNT and row.amount is not None and row.value is not None]
    return core.pair_by_key(left, right, left_key=_securities_key, right_key=_account_key, assign_group=_assign)


# =============================================================================
# BALANCES: STATEMENTS, INTERVALS, HOLES
# =============================================================================


@dataclass(frozen=True)
class Statement:
    """A balance the bank states for the end of a day (the operation date axis): ``Saldo Iniziale`` is that of the eve of ``Data dal``."""

    as_of: date
    amount: Decimal
    kind: str  # "start" (Saldo Iniziale) or "end" (Saldo Finale)
    file_index: int
    currency: str


@dataclass(frozen=True)
class Interval:
    """The stretch between two statements and what the rows in it say about it."""

    start: Statement
    end: Statement
    rows: int
    residual: Decimal
    kind: str  # "closed", "hole" or "broken"

    @property
    def days(self) -> DateRangeModel:
        return DateRangeModel(start=self.start.as_of + timedelta(days=1), end=self.end.as_of)


def explained_by_rows(start: Statement, end: Statement, rows: Sequence[AccountRow]) -> Interval:
    """Classify the stretch between two statements. A pure function of the two statements and the rows between them.

    ``residual`` is what the stated balances changed by, less the sum of the rows dated after ``start`` up to ``end`` (inclusive).

    - ``closed``: the residual is within a cent (or the statements are the same day and agree);
    - ``hole``: the residual is not zero and **no row at all** lies in the stretch: no file covers it, so the difference is
      money the files do not show. It becomes a correction of cash, dated at the end of the stretch;
    - ``broken``: the residual is not zero although rows are there, or a row cannot be summed: the files say something
      that does not add up. Warn; never correct (a correction could hide a missing row inside a covered stretch).
    """
    inside = [row for row in rows if start.as_of < row.op <= end.as_of]
    if any(row.amount is None for row in inside):
        return Interval(start, end, len(inside), ZERO, "broken")
    residual = (end.amount - start.amount) - sum((row.amount for row in inside if row.amount is not None), ZERO)
    if abs(residual) <= CENT:
        return Interval(start, end, len(inside), residual, "closed")
    return Interval(start, end, len(inside), residual, "hole" if not inside and end.as_of > start.as_of else "broken")


@dataclass
class CashTruth:
    """A balance the bank states, in LibreFolio's terms.

    ``stated`` is the bank's balance for the end of ``as_of``. ``amount`` is that balance seen the way LibreFolio records
    the rows: a pair is dated with the securities operation date, the bank books it on the account's own date, so what is
    recorded by ``as_of`` and what the bank has booked by then differ by the pairs in between (``in_flight``).
    """

    kind: str  # "opening", "gap" or "verification"
    as_of: date
    stated: Decimal
    in_flight: Decimal
    currency: str
    source: str

    @property
    def amount(self) -> Decimal:
        return self.stated + self.in_flight


@dataclass
class PositionTruth:
    """A position the files prove at a checkpoint: the quantity held, and the row that proves it."""

    as_of: date
    name: str
    quantity: Decimal
    proof: str
    rows: List[SecuritiesRow] = field(default_factory=list)


@dataclass
class Checkpoint:
    kind: str  # "opening" or "gap"
    cash: CashTruth
    positions: List[PositionTruth] = field(default_factory=list)


# =============================================================================
# THE ANALYSIS
# =============================================================================


class Analysis:
    """Everything the plugin knows about a set: kept rows, pairs, outcomes, statements, intervals, truth points."""

    def __init__(self, members: Dict[str, List[Path]]):
        securities_paths = list(members.get(ROLE_SECURITIES, []))
        account_paths = list(members.get(ROLE_ACCOUNT, []))
        self.securities_files: List[SecuritiesFile] = [read_securities(path, index + 1, len(securities_paths)) for index, path in enumerate(securities_paths)]
        self.account_files: List[AccountFile] = [read_account(path, index + 1, len(account_paths)) for index, path in enumerate(account_paths)]

        securities_merge = core.RoleMerge([file.rows for file in self.securities_files], lambda row: row.op, owner="most_rows", contradiction="not_contained")
        account_merge = core.RoleMerge([file.rows for file in self.account_files], lambda row: row.op, owner="most_rows", contradiction="not_contained")
        self.securities: List[SecuritiesRow] = sorted(securities_merge.kept, key=lambda row: (row.op, row.file_index, row.row))
        self.account: List[AccountRow] = sorted(account_merge.kept, key=lambda row: (row.op, row.file_index, row.row))
        self.superseded: List[Any] = [*securities_merge.superseded, *account_merge.superseded]
        self.mismatch: Dict[str, List[date]] = {ROLE_SECURITIES: securities_merge.mismatch_days, ROLE_ACCOUNT: account_merge.mismatch_days}

        for row in [*self.securities, *securities_merge.superseded]:
            row.klass = classify_securities(row)
        for row in [*self.account, *account_merge.superseded]:
            row.klass, row.tier = classify_account(row)

        self.conflicting_days: List[date] = []
        self.pairs, ambiguous = pair_rows(self.securities, self.account)
        self.ambiguous = {id(row) for row in ambiguous}
        self.cash_spans = self._cash_spans()
        self.statements = self._statements()
        self.intervals = self._intervals()
        self.opening_statement = self._opening_statement()
        self.holes = [interval for interval in self.intervals if interval.kind == "hole" and self._after_opening(interval.start.as_of)]
        self.broken = [interval for interval in self.intervals if interval.kind == "broken"]
        # A correction at the end of a hole also corrects whatever does not add up before it: after a broken stretch the
        # difference is no longer the hole's, so such a hole is reported and compared, never corrected.
        self.corrected_holes = [hole for hole in self.holes if not self._broken_before(hole)]
        self._settle()
        self.checkpoints = self._checkpoints()
        self.verifications = self._verifications()

    # ----------------------------------------------------------------- coverage

    def _cash_spans(self) -> List[Tuple[date, date]]:
        """The days the account files cover. A file whose balances add up covers the period its header declares (it may hold no
        row on the last day of it); any other file covers the days between its first and its last row."""
        spans: List[Tuple[date, date]] = []
        for file in self.account_files:
            declared = file.testata.declared
            if file.chain_closes and declared is not None:
                spans.append(declared)
            elif file.row_span is not None:
                spans.append(file.row_span)
        return core.merge_spans(spans)

    def _covered(self, day: Optional[date]) -> bool:
        return day is not None and any(start <= day <= end for start, end in self.cash_spans)

    # ----------------------------------------------------------------- statements

    def _statements(self) -> List[Statement]:
        found: List[Statement] = []
        for index, file in enumerate(self.account_files, start=1):
            testata = file.testata
            if not testata.has_balances or testata.date_from is None or testata.date_to is None or testata.opening is None or testata.closing is None:
                continue
            currency = testata.currency or CURRENCY
            found.append(Statement(testata.date_from - timedelta(days=1), testata.opening, "start", index, currency))
            found.append(Statement(testata.date_to, testata.closing, "end", index, currency))
        return sorted(found, key=lambda statement: (statement.as_of, statement.kind != "start", statement.file_index))

    def _intervals(self) -> List[Interval]:
        """One interval between each two statements of consecutive days; two statements of one day must agree."""
        by_day: Dict[date, List[Statement]] = {}
        for statement in self.statements:
            by_day.setdefault(statement.as_of, []).append(statement)
        chosen: List[Statement] = []
        for day in sorted(by_day):
            group = by_day[day]
            if any(abs(other.amount - group[0].amount) > CENT for other in group[1:]):
                self.conflicting_days.append(day)
            chosen.append(group[0])
        return [explained_by_rows(start, end, self.account) for start, end in zip(chosen, chosen[1:], strict=False)]

    def _opening_statement(self) -> Optional[Statement]:
        """The earliest ``Saldo Iniziale`` whose stretch to the next statement is closed or a hole (never one that does not add up)."""
        for interval in self.intervals:
            if interval.start.kind == "start" and interval.kind in ("closed", "hole") and interval.start.as_of not in self.conflicting_days:
                return interval.start
        return None

    def _after_opening(self, day: date) -> bool:
        return self.opening_statement is not None and day >= self.opening_statement.as_of

    def _broken_before(self, hole: Interval) -> bool:
        """A broken stretch between the opening and ``hole``."""
        return any(self._after_opening(other.start.as_of) and other.end.as_of <= hole.start.as_of for other in self.broken)

    def zone(self, day: Optional[date]) -> str:
        """``before`` the opening, in a ``gap`` (a hole), else ``window``; empty when the set states no balance."""
        if day is None or self.opening_statement is None:
            return ""
        if day <= self.opening_statement.as_of:
            return ZONE_BEFORE
        if any(hole.start.as_of < day <= hole.end.as_of for hole in self.holes):
            return ZONE_GAP
        return ZONE_WINDOW

    # ----------------------------------------------------------------- outcomes

    def _settle(self) -> None:
        for sec, acc in self.pairs:
            zone = self.zone(acc.op)
            sec.outcome.kind, sec.outcome.zone = "pair", zone
            acc.outcome.kind, acc.outcome.zone = "pair", zone
        for row in self.securities:
            if not row.outcome.kind:
                self._settle_securities(row)
        for row in self.account:
            if not row.outcome.kind:
                self._settle_account(row)
        for row in self.superseded:
            row.outcome.kind, row.outcome.zone, row.outcome.reason = "excluded", self.zone(row.op), "superseded"

    def _settle_securities(self, row: SecuritiesRow) -> None:
        zone = self.zone(row.op)
        outcome = row.outcome
        outcome.zone = zone
        if row.klass == "transfer_in":
            outcome.kind = "standalone"
        elif row.klass in PAIRED_SECURITIES:
            reason = self._unpaired_securities_reason(row)
            if reason != "ambiguous" and row.ctv is not None and self._inside_one_hole(row.op, row.value or row.op):
                # No account export covers these days, so the securities export is the only record of the movement: it is
                # recorded with its own cash, and the gap-fix proposes only what is left of the hole. Both dates must be
                # inside: a bank that books a day before the securities date (a fund) has the cash in the balance at the end
                # of the hole while the row is dated after it, and a row whose account counterpart is in a file just outside
                # the hole (an amount that differs by a cent) is counted by that row.
                outcome.kind, outcome.reason = "standalone", "in_gap"
            else:
                outcome.kind, outcome.reason = "excluded", reason
        else:
            outcome.kind, outcome.reason = "excluded", "unknown_type"

    def _inside_one_hole(self, *days: Optional[date]) -> bool:
        """Every one of ``days`` lies in the same hole (a row that straddles the end of a hole is not inside it)."""
        return any(all(day is not None and hole.start.as_of < day <= hole.end.as_of for day in days) for hole in self.holes)

    def _unpaired_securities_reason(self, row: SecuritiesRow) -> str:
        if id(row) in self.ambiguous:
            return "ambiguous"
        if not self.cash_spans:
            return "outside_cash_coverage"
        day = row.value or row.op
        if day > self.cash_spans[-1][1]:
            return "not_yet_settled"
        if not self._covered(day):
            return "outside_cash_coverage"
        return "no_counterpart"

    def _settle_account(self, row: AccountRow) -> None:
        outcome = row.outcome
        outcome.zone = self.zone(row.op)
        # An account row is cash the bank really moved: it is never dropped for lack of a pair, only for being unreadable.
        if row.klass == "invalid":
            outcome.kind, outcome.reason = "excluded", "invalid"
        elif id(row) in self.ambiguous:
            outcome.kind, outcome.reason = "standalone", "ambiguous"
        elif row.klass in STANDALONE_WITHOUT_PAIR:
            outcome.kind = "standalone"
        else:
            # A purchase or a sale on the account for which the securities export has no row: the money is real, what was
            # traded is not known from this row (the plugin asks the user, as it always has).
            outcome.kind, outcome.reason = "standalone", "no_counterpart"

    # ----------------------------------------------------------------- truth points

    def in_flight(self, day: date) -> Decimal:
        """The cash of the pairs the ledger and the bank date apart.

        A pair is recorded with the securities operation date and booked by the bank on the account's operation date. At the
        end of ``day`` the ledger holds it when its securities date is up to ``day``, the bank when its own is: the cash of the
        pairs held by one and not by the other is what separates the bank's balance from the ledger's. (The securities date is
        usually the earlier: an order on the 17th is booked on the 25th.)
        """
        total = ZERO
        for sec, acc in self.pairs:
            if acc.amount is None:
                continue
            recorded = sec.op <= day
            booked = acc.op <= day
            if recorded and not booked:
                total += acc.amount
            elif booked and not recorded:
                total -= acc.amount
        return total

    def _truth(self, kind: str, statement: Statement) -> CashTruth:
        return CashTruth(kind=kind, as_of=statement.as_of, stated=statement.amount, in_flight=self.in_flight(statement.as_of), currency=statement.currency, source=f"account#{statement.file_index}:{statement.kind}")

    def _checkpoints(self) -> List[Checkpoint]:
        if self.opening_statement is None:
            return []
        found = [Checkpoint("opening", self._truth("opening", self.opening_statement), self._opening_positions(self.opening_statement.as_of))]
        for hole in self.corrected_holes:
            found.append(Checkpoint("gap", self._truth("gap", hole.end)))
        return found

    def _paired_movements(self, day: date) -> Tuple[Dict[str, Decimal], set]:
        """The quantity the paired rows recorded by ``day`` add to each title (a purchase adds, a redemption takes away),
        and the titles with a maturity among them: its quantity is not in the file (it says 0), so the title has no proof."""
        moved: Dict[str, Decimal] = defaultdict(lambda: ZERO)
        unknown = set()
        for sec, _acc in self.pairs:
            if sec.op > day:
                continue
            key = core.norm(sec.name)
            if sec.klass == "matured":
                unknown.add(key)
            elif sec.klass == "buy":
                moved[key] += abs(sec.qty or ZERO)
            elif sec.klass == "redeem":
                moved[key] -= abs(sec.qty or ZERO)
        return moved, unknown

    def _opening_positions(self, day: date) -> List[PositionTruth]:
        """What the transfers from another dossier prove at the opening: the quantity of each title, exact.

        The quantity is seen the way LibreFolio records it, like the cash: the transfers up to ``day`` plus the purchases and
        redemptions recorded by ``day`` (a purchase made on the 29th and debited on the 1st counts at an opening of the 31st).
        """
        held: Dict[str, List[SecuritiesRow]] = {}
        for row in self.securities:
            if row.klass == "transfer_in" and row.op <= day and row.qty is not None:
                held.setdefault(core.norm(row.name), []).append(row)
        moved, unknown = self._paired_movements(day)
        return [PositionTruth(day, rows[0].name, sum((abs(row.qty) for row in rows if row.qty is not None), ZERO) + moved.get(key, ZERO), "exact:transfer_in", rows) for key, rows in sorted(held.items()) if key not in unknown]

    def _verifications(self) -> List[CashTruth]:
        """Balances to compare and never to correct: every ``Saldo Finale``, the cash of the securities header, and the
        ``Saldo Iniziale`` of a file that could not open the history."""
        marked = {checkpoint.cash.as_of for checkpoint in self.checkpoints}
        compared_only = {hole.end.as_of for hole in self.holes if hole not in self.corrected_holes}
        found: List[CashTruth] = []
        for statement in self.statements:
            usable_start = statement.kind == "start" and (self.opening_statement is None or statement.as_of < self.opening_statement.as_of or statement.as_of in compared_only)
            if (statement.kind == "end" or usable_start) and statement.as_of not in marked:
                found.append(self._truth("verification", statement))
                marked.add(statement.as_of)
        for file in self.securities_files:
            testata = file.testata
            if testata.liquidity is not None and testata.updated is not None and self.cash_spans and testata.updated not in marked and self._covered(testata.updated):
                currency = testata.liquidity_currency or CURRENCY
                statement = Statement(testata.updated, testata.liquidity, "end", 0, currency)
                found.append(CashTruth("verification", statement.as_of, statement.amount, self.in_flight(statement.as_of), currency, "securities:liquidity"))
                marked.add(statement.as_of)
        return sorted(found, key=lambda truth: truth.as_of)

    # ----------------------------------------------------------------- the shape of the set

    def segments(self) -> List[DateRangeModel]:
        spans = core.merge_spans(span for span in (core.coverage(file.rows, lambda row: row.op) for file in self.securities_files) if span)
        return [DateRangeModel(start=start, end=end) for start, end in spans]

    def gaps(self) -> List[DateRangeModel]:
        return [hole.days for hole in self.holes]

    def set_notices(self) -> List[BRIMNotice]:
        notices: List[BRIMNotice] = []
        for role, files in ((ROLE_SECURITIES, self.securities_files), (ROLE_ACCOUNT, self.account_files)):
            for index, file in enumerate(files, start=1):
                if not file.rows:
                    notices.append(BRIMNotice(severity="warning", code="empty_member", message=f"A {role} export has no rows", context={"role": role, "file": index}))
        for role, days in self.mismatch.items():
            if days:
                message = f"Two {role} exports disagree on {len(days)} day(s) they both cover: the export with more rows is used for those days"
                notices.append(BRIMNotice(severity="warning", code="overlap_mismatch", message=message, context={"role": role, "days": len(days), "first": days[0].isoformat(), "last": days[-1].isoformat()}))
        for hole in self.holes:
            message = f"No account export covers {hole.days.start.isoformat()} to {hole.days.end.isoformat()}: the bank's balances differ by {core.money(hole.residual)} over that period. Export the account movements for it if the bank still has them"
            corrected = hole in self.corrected_holes
            notices.append(BRIMNotice(severity="warning", code="account_gap", message=message, context={"start": hole.days.start.isoformat(), "end": hole.days.end.isoformat(), "amount": core.money(hole.residual), "corrected": corrected}))
        if self.broken or self.conflicting_days:
            first = self.broken[0].end.as_of if self.broken else self.conflicting_days[0]
            message = f"The balances stated by the account exports do not add up with their rows from {first.isoformat()}: they are only compared, never used for a correction"
            notices.append(BRIMNotice(severity="warning", code="balance_chain_broken", message=message, context={"date": first.isoformat()}))
        notices.extend(self._left_over_notices())
        if self.account_files and not self.statements:
            notices.append(BRIMNotice(severity="info", code="no_balance", message="No account export states a balance (only the Excel export does): the cash is not compared with the bank", context=None))
        return notices

    def _left_over_notices(self) -> List[BRIMNotice]:
        left_over = self._left_over_rows()
        texts = (
            ("ambiguous", "rows could not be matched with certainty between the securities and the account export"),
            ("no_counterpart", "rows have no matching row in the other export"),
        )
        return [BRIMNotice(severity="warning", code=code, message=f"{left_over[code]} {text}", context={"rows": left_over[code]}) for code, text in texts if left_over[code]]

    def _left_over_rows(self) -> Dict[str, int]:
        """How many rows were left without a pair: ambiguous ones, and the ones with no counterpart where there should be one."""
        rows = [*self.securities, *self.account]
        return {
            "ambiguous": sum(1 for row in rows if row.outcome.reason == "ambiguous"),
            "no_counterpart": sum(1 for row in rows if row.outcome.reason == "no_counterpart"),
        }

    def counts(self) -> Counter:
        """How many rows have each outcome (for the combined file's summary)."""
        return Counter((row.outcome.kind, row.outcome.reason) for row in [*self.securities, *self.account, *self.superseded])


# =============================================================================
# WHAT THE PLUGIN ANSWERS ABOUT A MEMBER AND A SET
# =============================================================================


def describe_member(path: Path) -> BRIMMemberSummary:
    """Role, rows and coverage of one export, read without combining anything.

    Coverage is on the operation-date axis: the days of the rows and, for an XLSX that states it, the period of its header,
    which can be wider than its rows (the bank cuts old rows off an export and keeps the period asked for); on the value axis,
    the days the rows settle.
    """
    role = detect_role(path)
    if role == ROLE_SECURITIES:
        file = read_securities(path)
        return BRIMMemberSummary(role=role, rows=len(file.rows), coverage=_coverage(file.rows, None), account_fingerprint=account_fingerprint(file.testata))
    if role == ROLE_ACCOUNT:
        account = read_account(path)
        return BRIMMemberSummary(role=role, rows=len(account.rows), coverage=_coverage(account.rows, account.testata.declared))
    return BRIMMemberSummary(role=None, rows=0)


def _coverage(rows: Sequence[Any], declared: Optional[Tuple[date, date]]) -> List[BRIMCoverage]:
    coverage: List[BRIMCoverage] = []
    trade = core.coverage(rows, lambda row: row.op)
    if trade is not None:
        coverage.append(BRIMCoverage(axis="trade", start=trade[0], end=trade[1]))
    if declared is not None and declared != trade:
        coverage.append(BRIMCoverage(axis="trade", start=declared[0], end=declared[1]))
    value = core.coverage(rows, lambda row: row.value)
    if value is not None:
        coverage.append(BRIMCoverage(axis="value", start=value[0], end=value[1]))
    return coverage


def describe_set(members: Dict[str, List[Path]]) -> BRIMSetShape:
    """The segments the securities exports cover, the holes of the account, and the notices of the set."""
    analysis = Analysis(members)
    return BRIMSetShape(segments=analysis.segments(), gaps=analysis.gaps(), notices=analysis.set_notices())
