"""Gap-fix: align LibreFolio with what the bank states.

A report-set plugin declares truth points: at a checkpoint the bank states the
cash balance and proves some positions. The gap-fix compares them with what
LibreFolio will know at that date - the saved transactions, minus the ones the
bulk editor is deleting, plus the editor's unsaved rows, the rows the wizard is
about to hand over and the corrections of the earlier checkpoints - and proposes
only the difference, as ordinary transactions tagged ``gap_fix``. It writes
nothing: the user chooses what to import, and the editor saves it.

Design: ``LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/design-phase00BrimReportSets.md`` (section 3.6).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from typing import Dict, Iterable, List, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Transaction, TransactionType
from backend.app.schemas.brim import (
    BRIMCheckpoint,
    BRIMFieldTodo,
    BRIMGapFixCashRow,
    BRIMGapFixCheckpointResult,
    BRIMGapFixExplanation,
    BRIMGapFixPositionRow,
    BRIMGapFixRequest,
    BRIMGapFixResponse,
    BRIMGapFixVerificationResult,
    BRIMNotice,
    BRIMTruthCash,
    is_fake_asset_id,
)
from backend.app.schemas.common import Currency, is_canonical_iso_currency, shown_currency_text, suggested_iso_currency
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim.brim_provider import BRIMProvider
from backend.app.services.brim.brim_report_sets import GAP_FIX_TAG, BRIMLedgerUnreadable, BRIMSetPluginNotFound
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.services.transactions.unreadable_rows import UnreadableLedgerError

# Differences at or below one cent are rounding, not a gap.
CASH_TOLERANCE = Decimal("0.01")
ZERO = Decimal("0")
#: How many of a broker's non-ISO cash codes the refusal names (E-19a); the others are counted.
NON_ISO_CODES_NAMED = 5


def _plugin(plugin_code: str) -> BRIMProvider:
    plugin = BRIMProviderRegistry.get_provider_instance(plugin_code)
    if plugin is None:
        raise BRIMSetPluginNotFound(f"Unknown import plugin: {plugin_code}")
    return plugin


def _in_memory(items: Iterable[TXCreateItem], broker_id: int, as_of: date) -> Tuple[Dict[str, Decimal], Dict[int, Decimal]]:
    """Cash per currency and quantity per asset of unsaved rows of the broker dated on or before ``as_of``."""
    cash: Dict[str, Decimal] = defaultdict(lambda: ZERO)
    quantities: Dict[int, Decimal] = defaultdict(lambda: ZERO)
    for item in items:
        if item.broker_id != broker_id or item.date > as_of:
            continue
        if item.cash is not None:
            cash[item.cash.code] += item.cash.amount
        if item.asset_id is not None and item.quantity is not None:
            quantities[item.asset_id] += item.quantity
    return cash, quantities


async def _refuse_non_iso_cash(session: AsyncSession, request: BRIMGapFixRequest, as_of: date) -> None:
    """Refuse the comparison when the broker's cash up to ``as_of`` is held in a code that is not a canonical ISO 4217
    code (E-19a): a name or a number an earlier version saved as written (``978``, ``EURO``), or another case (``eur``).

    Such a balance is a bucket of its own, which the bank's ``EUR`` never meets: compared anyway, the gap-fix would propose
    a correction for money already there. The rows are the ones ``get_balances_at_end_of`` sums (dated up to ``as_of``,
    without ``pending_delete_tx_ids``) and only their cash currency counts. The broker is the caller's own (its editor),
    so the codes are named, at most ``NON_ISO_CODES_NAMED``, each with the code it stands for.
    """
    stmt = select(Transaction.currency).where(Transaction.broker_id == request.broker_id, Transaction.date <= as_of, Transaction.currency.isnot(None)).distinct()
    if request.pending_delete_tx_ids:
        stmt = stmt.where(Transaction.id.notin_(list(request.pending_delete_tx_ids)))
    codes = sorted(code for code in (await session.execute(stmt)).scalars() if code and not is_canonical_iso_currency(code))
    if not codes:
        return
    named = ", ".join(f"{shown_currency_text(code)!r} ({suggested_iso_currency(code) or 'no ISO code'})" for code in codes[:NON_ISO_CODES_NAMED])
    more = f" and {len(codes) - NON_ISO_CODES_NAMED} more" if len(codes) > NON_ISO_CODES_NAMED else ""
    raise BRIMLedgerUnreadable(f"LibreFolio's balances of this broker cannot be compared with the bank: its transactions hold currency codes that are not ISO 4217 codes: {named}{more}. Correct them first.")


async def _state_at(session: AsyncSession, request: BRIMGapFixRequest, as_of: date, proposals: Sequence[TXCreateItem]) -> Tuple[Dict[str, Decimal], Dict[int, Decimal]]:
    """What LibreFolio will know at the end of ``as_of``; refused when the broker's transactions up to it hold a value that
    is no number (W-B74), or a cash currency that is not an ISO 4217 code (E-19a): compared with the bank, a wrong balance
    would propose a wrong correction."""
    try:
        db_cash, db_quantities = await TransactionService(session).get_balances_at_end_of(request.broker_id, as_of, exclude_tx_ids=request.pending_delete_tx_ids)
    except UnreadableLedgerError as exc:
        raise BRIMLedgerUnreadable(f"LibreFolio's balances of this broker cannot be compared with the bank: {exc.count} of its transactions hold a value that is not a number. Ask the administrator to repair them.") from exc
    await _refuse_non_iso_cash(session, request, as_of)
    cash: Dict[str, Decimal] = defaultdict(lambda: ZERO, {code: Decimal(amount or 0) for code, amount in db_cash.items()})
    quantities: Dict[int, Decimal] = defaultdict(lambda: ZERO, {asset_id: Decimal(quantity or 0) for asset_id, quantity in db_quantities.items()})
    mem_cash, mem_quantities = _in_memory([*request.pending_creates, *request.selection, *proposals], request.broker_id, as_of)
    for code, amount in mem_cash.items():
        cash[code] += amount
    for asset_id, quantity in mem_quantities.items():
        quantities[asset_id] += quantity
    return cash, quantities


def _proposal_description(plugin: BRIMProvider, as_of: date, what: str) -> str:
    return f"Gap-fix {as_of.isoformat()} — {plugin.provider_name}: {what} at the end of the day, as stated by the bank"


def _cash_rows(bank: Iterable[BRIMTruthCash], librefolio: Dict[str, Decimal]) -> List[BRIMGapFixCashRow]:
    return [BRIMGapFixCashRow(currency=item.currency, bank=item.amount, librefolio=librefolio[item.currency], difference=item.amount - librefolio[item.currency]) for item in bank]


async def _present_counter(session: AsyncSession, request: BRIMGapFixRequest, dates: Sequence[date]) -> Counter:
    """Multiset of (date, currency, amount) LibreFolio has for the broker on the given dates."""
    present: Counter = Counter()
    if not dates:
        return present
    stmt = select(Transaction.date, Transaction.currency, Transaction.amount).where(Transaction.broker_id == request.broker_id, Transaction.date.in_(sorted(set(dates))), Transaction.currency.isnot(None))
    if request.pending_delete_tx_ids:
        stmt = stmt.where(Transaction.id.notin_(list(request.pending_delete_tx_ids)))
    for tx_date, currency, amount in (await session.execute(stmt)).all():
        present[(tx_date, currency, Decimal(amount or 0))] += 1
    for item in [*request.pending_creates, *request.selection]:
        if item.broker_id == request.broker_id and item.cash is not None:
            present[(item.date, item.cash.code, item.cash.amount)] += 1
    return present


async def _explain(session: AsyncSession, request: BRIMGapFixRequest, checkpoint: BRIMCheckpoint, cash_rows: Sequence[BRIMGapFixCashRow]) -> BRIMGapFixExplanation:
    rows = checkpoint.absorbed.rows
    present = await _present_counter(session, request, [row.as_of for row in rows])
    missing_cash: Dict[str, Decimal] = defaultdict(lambda: ZERO)
    missing_count = 0
    for row in rows:
        key = (row.as_of, row.currency, row.amount)
        if present[key] > 0:
            present[key] -= 1
            continue
        missing_count += 1
        missing_cash[row.currency] += row.amount
    opening = list(checkpoint.absorbed.opening_cash) if checkpoint.kind == "opening" else []
    opening_by_code = {item.currency: item.amount for item in opening}
    unexplained = []
    for row in cash_rows:
        rest = row.difference - missing_cash.get(row.currency, ZERO) - opening_by_code.get(row.currency, ZERO)
        if abs(rest) > CASH_TOLERANCE:
            unexplained.append(BRIMTruthCash(currency=row.currency, amount=rest))
    return BRIMGapFixExplanation(
        absorbed_count=len(rows),
        absorbed_missing_count=missing_count,
        absorbed_missing_cash=[BRIMTruthCash(currency=code, amount=amount) for code, amount in sorted(missing_cash.items())],
        opening_cash=opening,
        unexplained_cash=unexplained,
    )


def _cash_proposals(plugin: BRIMProvider, request: BRIMGapFixRequest, checkpoint: BRIMCheckpoint, cash_rows: Sequence[BRIMGapFixCashRow], tags: List[str]) -> List[TXCreateItem]:
    proposals = []
    for row in cash_rows:
        if abs(row.difference) <= CASH_TOLERANCE:
            continue
        proposals.append(
            TXCreateItem(
                broker_id=request.broker_id,
                type=TransactionType.DEPOSIT if row.difference > 0 else TransactionType.WITHDRAWAL,
                date=checkpoint.as_of,
                cash=Currency(code=row.currency, amount=row.difference),
                tags=list(tags),
                description=_proposal_description(plugin, checkpoint.as_of, f"{row.currency} cash balance"),
            )
        )
    return proposals


def _position_proposals(
    plugin: BRIMProvider,
    request: BRIMGapFixRequest,
    checkpoint: BRIMCheckpoint,
    quantities: Dict[int, Decimal],
    tags: List[str],
    offset: int,
) -> Tuple[List[BRIMGapFixPositionRow], List[TXCreateItem], List[BRIMFieldTodo], List[BRIMNotice]]:
    rows: List[BRIMGapFixPositionRow] = []
    proposals: List[TXCreateItem] = []
    todos: List[BRIMFieldTodo] = []
    notes: List[BRIMNotice] = []
    for position in checkpoint.positions:
        if is_fake_asset_id(position.asset_id):
            notes.append(BRIMNotice(severity="warning", code="unresolved_asset", message="A position of the bank refers to a security that is not resolved yet: it was left out", context={"asset_id": position.asset_id}))
            continue
        have = quantities[position.asset_id]
        missing = position.quantity - have
        if position.exactness == "at_least":
            missing = max(missing, ZERO)
        rows.append(BRIMGapFixPositionRow(asset_id=position.asset_id, exactness=position.exactness, bank=position.quantity, librefolio=have, difference=missing))
        if missing == 0:
            continue
        proposal = TXCreateItem(
            broker_id=request.broker_id,
            asset_id=position.asset_id,
            type=TransactionType.ADJUSTMENT,
            date=checkpoint.as_of,
            quantity=missing,
            cost_basis_override=position.unit_cost if missing > 0 else None,
            tags=list(tags),
            description=_proposal_description(plugin, checkpoint.as_of, "position"),
        )
        if missing > 0 and position.unit_cost is None:
            todos.append(
                BRIMFieldTodo(
                    tx_index=offset + len(proposals),
                    field="cost_basis_override",
                    severity="blocker",
                    reason_code="gap_fix_cost",
                    message="Enter the per-unit cost of this position (the bank's website shows the average price)",
                )
            )
        proposals.append(proposal)
    return rows, proposals, todos, notes


async def compute_gap_fix(session: AsyncSession, request: BRIMGapFixRequest) -> BRIMGapFixResponse:
    """Compare every truth point with LibreFolio and propose the gap-fix corrections."""
    plugin = _plugin(request.plugin_code)
    tags = ["import", plugin.history_tag, GAP_FIX_TAG]
    accepted: List[TXCreateItem] = []
    results: List[BRIMGapFixCheckpointResult] = []

    for checkpoint in sorted(request.checkpoints, key=lambda item: item.as_of):
        cash, quantities = await _state_at(session, request, checkpoint.as_of, accepted)
        cash_rows = _cash_rows(checkpoint.cash, cash)
        cash_proposals = _cash_proposals(plugin, request, checkpoint, cash_rows, tags)
        position_rows, position_proposals, todos, notes = _position_proposals(plugin, request, checkpoint, quantities, tags, offset=len(cash_proposals))
        explanation = await _explain(session, request, checkpoint, cash_rows)
        explanation.notes.extend(notes)
        proposals = [*cash_proposals, *position_proposals]
        accepted.extend(proposals)
        results.append(
            BRIMGapFixCheckpointResult(
                as_of=checkpoint.as_of,
                kind=checkpoint.kind,
                cash=cash_rows,
                positions=position_rows,
                proposals=proposals,
                todos=todos,
                explanation=explanation,
            )
        )

    verifications: List[BRIMGapFixVerificationResult] = []
    for verification in sorted(request.verifications, key=lambda item: item.as_of):
        cash, _ = await _state_at(session, request, verification.as_of, accepted)
        cash_rows = _cash_rows(verification.cash, cash)
        verifications.append(BRIMGapFixVerificationResult(as_of=verification.as_of, ok=all(abs(row.difference) <= CASH_TOLERANCE for row in cash_rows), cash=cash_rows))

    return BRIMGapFixResponse(checkpoints=results, verifications=verifications)
