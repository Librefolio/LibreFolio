"""The link of a charge to its parent (project 66, issue #25): the one module that reads and writes it.

A FEE or a TAX (a *charge*) may point at the transaction it belongs to, its *parent*, through
``transactions.parent_transaction_id``. The parent knows nothing; many charges, one parent; no chains. Which types are
charges and which are parents is a column of the type table (``TX_TYPE_METADATA[type].charge_role``, decision D2).

The rules of the plan («Le regole»), one place:

1. a charge is a FEE or a TAX; a parent is one of the six parent types (the two lists share no type: no chain);
2. the charge has the parent's broker;
3. the charge has the parent's asset, or none when the parent has none (D6b: a charge saved without an asset is not
   linked to a parent with one; the user clones it with the right asset, nothing is cleaned up);
4. date and currency are free;
5. no magic: changing a parent never changes its charges (the form sends every change in one batch);
6. a row that has charges and would stop being a parent is refused, with its charges (``chargesBlockParentType``);
7. the batch checks the rules on its final state, for every link it touches (the batch stages, from lot R3);
8. a row of a pair (``related_transaction_id`` set: one of the three pair types, or a pair stored before lot R0) is
   neither a charge nor a parent (``chargeRowIsPaired``): the user splits the pair first. The field decides, not the
   type; ``row_is_paired`` is the one predicate, also for the promotion of a row with charges (lot R5).

Rules 1–3 and 8 are ``charge_link_issue``, rule 6 is ``charges_parent_type_issue``: pure, on rows in memory, each answering
the first violation as ``(message, code, params)`` like ``TransactionValidationMixin._validate_linked_pair``. Where the
issue goes (operation, index, ``ref``) is the batch's: ``link_charges``, the batch stage after the pair links (lot R3),
resolves the parent each charge names (``parent_ref``: a create of the batch named by its ``ref``;
``parent_transaction_id``: a saved row) and writes the link on the batch's final state.

The reads: ``charge_ids_by_parent`` and ``charge_counts`` (the charges of some parents, through the partial index
``idx_transactions_parent`` of migration 006, step ``charge_links``), and the two conditions of the list's filters,
``charges_of_condition`` and ``without_parent_condition``.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ColumnElement, Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Transaction
from backend.app.schemas.transactions.batch import TXValidationCode, TXValidationIssue
from backend.app.schemas.transactions.type_metadata import charge_parent_types, charge_types
from backend.app.services.transactions.transaction_batch_context import TransactionBatchContext

if TYPE_CHECKING:
    from backend.app.services.transactions.transaction_service import TransactionService

#: Ids per ``IN (…)``: far below SQLite's 32 766 variables, so the full list of the transactions page fits any build.
_CHUNK = 500

#: ``(english message, code, params)``: the shape of every rule of the batch.
ChargeIssue = tuple[str, str, dict]


def row_is_paired(row: Transaction) -> bool:
    """Rule 8: whether ``row`` is a leg of a pair, by its ``related_transaction_id`` (never by its type)."""
    return row.related_transaction_id is not None


def charge_link_issue(charge: Transaction, parent: Optional[Transaction], parent_id: int) -> Optional[ChargeIssue]:
    """The first rule (1–3, 8) the link ``charge`` → ``parent`` breaks, or None when it is valid.

    ``parent`` is None when the row ``parent_id`` names does not exist **or** the user cannot see it: both answer
    ``chargeParentNotFound`` with the same params, so a refusal never tells a row of someone else's broker apart.
    Date and currency are never judged (rule 4).
    """
    if charge.type not in charge_types():
        return (
            f"a {charge.type.value} cannot be linked to a transaction: only a fee or a tax can",
            TXValidationCode.CHARGE_NOT_A_CHARGE.value,
            {"type": charge.type.value},
        )
    if row_is_paired(charge):
        return (
            "this charge is a leg of a linked pair: split the pair before linking it to a transaction",
            TXValidationCode.CHARGE_ROW_IS_PAIRED.value,
            {"role": "charge"},
        )
    if parent is None:
        return (
            f"the transaction {parent_id} this charge is linked to does not exist",
            TXValidationCode.CHARGE_PARENT_NOT_FOUND.value,
            {"parentId": parent_id},
        )
    if parent.type not in charge_parent_types():
        return (
            f"a charge cannot be linked to a {parent.type.value}: only to a buy, a sell, a dividend, an interest, a deposit or a withdrawal",
            TXValidationCode.CHARGE_PARENT_TYPE_NOT_ALLOWED.value,
            {"type": parent.type.value},
        )
    if row_is_paired(parent):
        return (
            "the transaction is a leg of a linked pair: split the pair before linking a charge to it",
            TXValidationCode.CHARGE_ROW_IS_PAIRED.value,
            {"role": "parent"},
        )
    if charge.broker_id != parent.broker_id:
        return (
            f"a charge must be on the broker of its transaction (broker {charge.broker_id}, the transaction's {parent.broker_id})",
            TXValidationCode.CHARGE_BROKER_MISMATCH.value,
            {"brokerId": charge.broker_id, "parentBrokerId": parent.broker_id},
        )
    if charge.asset_id is None and parent.asset_id is not None:
        return (
            f"a charge without an asset cannot be linked to a transaction of asset {parent.asset_id}: clone it with that asset",
            TXValidationCode.CHARGE_ASSET_MISSING.value,
            {"parentAssetId": parent.asset_id},
        )
    if charge.asset_id != parent.asset_id:
        return (
            f"a charge must have the asset of its transaction (asset {charge.asset_id}, the transaction's {parent.asset_id})",
            TXValidationCode.CHARGE_ASSET_MISMATCH.value,
            {"assetId": charge.asset_id, "parentAssetId": parent.asset_id},
        )
    return None


def charges_parent_type_issue(parent: Transaction, charge_ids: Sequence[int]) -> Optional[ChargeIssue]:
    """Rule 6: a row with charges whose type is no longer a parent type, or None.

    Every type change a batch allows keeps a parent a parent (the swap groups BUY/SELL, DEPOSIT/WITHDRAWAL,
    DIVIDEND/INTEREST); the one that does not is a promotion of a DEPOSIT or a WITHDRAWAL into a leg of a pair. The
    user unlinks the charges first: the refusal lists them.
    """
    if not charge_ids or parent.type in charge_parent_types():
        return None
    ids = sorted(charge_ids)
    return (
        f"this transaction has {len(ids)} linked charges and a {parent.type.value} cannot have any: unlink them first",
        TXValidationCode.CHARGES_BLOCK_PARENT_TYPE.value,
        {"type": parent.type.value, "chargeIds": ids},
    )


def _chunks(ids: Sequence[int]) -> Iterator[Sequence[int]]:
    """``ids`` in slices of ``_CHUNK``: one ``IN (…)`` each."""
    for start in range(0, len(ids), _CHUNK):
        yield ids[start : start + _CHUNK]


def charge_ids_by_parent_statement(parent_ids: Iterable[int]) -> Select:
    """The query of ``charge_ids_by_parent``: ``(id, parent_transaction_id)`` of the charges of ``parent_ids``.

    SQLite 3.53: ``SEARCH transactions USING COVERING INDEX idx_transactions_parent (parent_transaction_id=?)``.
    """
    return select(Transaction.id, Transaction.parent_transaction_id).where(Transaction.parent_transaction_id.in_(sorted(set(parent_ids))))


async def charge_ids_by_parent(session: AsyncSession, parent_ids: Iterable[int]) -> dict[int, list[int]]:
    """The ids of the charges of each parent asked, ascending; a parent without charges maps to []. No query for none."""
    asked = sorted(set(parent_ids))
    if not asked:
        return {}
    found: dict[int, list[int]] = {parent_id: [] for parent_id in asked}
    for chunk in _chunks(asked):
        for charge_id, parent_id in (await session.execute(charge_ids_by_parent_statement(chunk))).all():
            found[parent_id].append(charge_id)
    for ids in found.values():
        ids.sort()
    return found


async def charge_counts(session: AsyncSession, parent_ids: Iterable[int]) -> dict[int, int]:
    """How many charges point at each of ``parent_ids``; a row without charges is absent. No query for none.

    One grouped read per slice of ids, through ``idx_transactions_parent`` (a covering index for this query).
    """
    asked = sorted(set(parent_ids))
    counts: dict[int, int] = {}
    for chunk in _chunks(asked):
        statement = select(Transaction.parent_transaction_id, func.count(Transaction.id)).where(Transaction.parent_transaction_id.in_(chunk)).group_by(Transaction.parent_transaction_id)
        counts.update((parent_id, count) for parent_id, count in (await session.execute(statement)).all())
    return counts


def charges_of_condition(parent_ids: Sequence[int]) -> ColumnElement[bool]:
    """The list filter ``parent_ids``: the charges linked to these parents."""
    return Transaction.parent_transaction_id.in_(sorted(set(parent_ids)))


def without_parent_condition() -> ColumnElement[bool]:
    """The list filter ``without_parent``: the charges a parent could take (the candidates of the picker): a charge type,
    no parent, and not a leg of a pair (rule 8)."""
    return and_(Transaction.type.in_(sorted(charge_types())), Transaction.parent_transaction_id.is_(None), Transaction.related_transaction_id.is_(None))


# ─── the batch stage (lot R3) ─────────────────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _LinkRequest:
    """One link a batch asks for: the charge row, where its issue goes, and how it names its parent."""

    charge: Transaction
    operation: str
    index: int
    ref_id: Optional[int]
    parent_ref: Optional[str]
    parent_id: Optional[int]

    @property
    def field(self) -> str:
        """The field of the request that names the parent: where the form shows a refusal."""
        return "parent_ref" if self.parent_ref is not None else "parent_transaction_id"


def _name(value: Optional[str]) -> Optional[str]:
    """A batch name as the contract reads it: an empty string is no name."""
    return value or None


def _create_refs(context: TransactionBatchContext) -> tuple[dict[str, Transaction], set[str]]:
    """The row each ``ref`` of the creates names, and the refs used twice.

    A ref used by more than one create is refused on every create after the first (``chargeRefDuplicate``) and names no
    row. A create refused for its own reason has no row: its ref names nothing. ``ref`` and ``link_uuid`` are two name
    spaces.
    """
    refs: dict[str, Transaction] = {}
    duplicated: set[str] = set()
    for index, item in context.parsed_creates:
        ref = _name(item.ref)
        row = context.created_by_index.get(index)
        if ref is None or row is None:
            continue
        if ref in refs or ref in duplicated:
            duplicated.add(ref)
            context.issues.append(
                TXValidationIssue(
                    operation="create",
                    index=index,
                    ref_id=None,
                    error=f"the name '{ref}' is given to more than one row of the batch",
                    code=TXValidationCode.CHARGE_REF_DUPLICATE.value,
                    params={"ref": ref},
                    field="ref",
                )
            )
            continue
        refs[ref] = row
    for ref in duplicated:
        refs.pop(ref, None)
    return refs, duplicated


def _create_requests(context: TransactionBatchContext) -> list[_LinkRequest]:
    """The links the creates ask for, on the rows they created: a create refused for its own reason asks nothing."""
    requests: list[_LinkRequest] = []
    for index, item in context.parsed_creates:
        row = context.created_by_index.get(index)
        parent_ref, parent_id = _name(item.parent_ref), item.parent_transaction_id
        if row is None or (parent_ref is None and parent_id is None):
            continue
        requests.append(_LinkRequest(charge=row, operation="create", index=index, ref_id=None, parent_ref=parent_ref, parent_id=parent_id))
    return requests


async def _saved_parents(service: TransactionService, context: TransactionBatchContext, ids: set[int]) -> dict[int, Transaction]:
    """The saved parents the batch can link: they exist, the batch does not delete them, and the user can at least view
    their broker. Loading them never adds their broker to the batch's EDITOR check; any other id answers "not found"."""
    ids = ids - set(context.deletes)
    if not ids:
        return {}
    rows = await service.get_by_ids(sorted(ids))
    if context.user_id is not None:
        visible = await service._get_accessible_broker_ids(context.user_id)
        rows = [row for row in rows if row.broker_id in visible]
    return {row.id: row for row in rows}


def _issue(request: _LinkRequest, issue: ChargeIssue) -> TXValidationIssue:
    """A rule's answer as an issue of the charge's row; the parent's batch name joins the params when it was used."""
    message, code, params = issue
    if request.parent_ref is not None:
        params = {**params, "parentRef": request.parent_ref}
    return TXValidationIssue(operation=request.operation, index=request.index, ref_id=request.ref_id, error=message, code=code, params=params, field=request.field)


async def link_charges(service: TransactionService, context: TransactionBatchContext) -> None:
    """Batch stage after the pair links: resolve the parent each charge names and write the link, on the final state.

    The same on /validate and /commit: both run the whole pipeline. Every issue goes on the charge's row. Params never
    carry the id of a row created in this batch: /validate does not return those ids.
    """
    refs, duplicated = _create_refs(context)
    requests = _create_requests(context)
    if not requests:
        return
    saved = await _saved_parents(service, context, {request.parent_id for request in requests if request.parent_id is not None})
    for request in requests:
        if request.parent_ref is not None:
            if request.parent_ref in duplicated:
                continue
            parent = refs.get(request.parent_ref)
            if parent is None:
                context.issues.append(
                    _issue(
                        request,
                        (f"no row of the batch is named '{request.parent_ref}'", TXValidationCode.CHARGE_PARENT_REF_NOT_FOUND.value, {}),
                    )
                )
                continue
            issue = charge_link_issue(request.charge, parent, 0)
        else:
            assert request.parent_id is not None
            parent = saved.get(request.parent_id)
            issue = charge_link_issue(request.charge, parent, request.parent_id)
        if issue is not None:
            context.issues.append(_issue(request, issue))
            continue
        assert parent is not None
        request.charge.parent_transaction_id = parent.id
