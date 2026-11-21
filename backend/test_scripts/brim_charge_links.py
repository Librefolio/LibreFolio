"""Test helpers for the linked charges a BRIM plugin emits (project 66, lot P1a, contract §3 and §6.2–§6.3).

Two checks every plugin test can call, and that the lots P2–P6 call on the real plugins:

- ``charge_link_structure_problems`` / ``assert_charge_link_structure``: the **structure** of a parse output — every
  ``ref`` unique, every ``parent_ref`` naming a ``ref`` of the same output, every name at most 36 characters. The domain
  rules of a link (which types, same broker, same asset) are not copied here: ``BRIMProvider._create_linked_charge``
  already applied them through ``services/transactions/charges.py`` (contract §6.2).
- ``assert_reimport_adds_nothing``: a file imported with the previous version of a plugin, imported again with the new
  one, adds no row (contract §6.3). The previous rows are saved without links, as a user of today has them; every
  incoming row must appear in the duplicate report of ``detect_tx_duplicates``, at any level.

Not a test module: no ``test_`` prefix, nothing collected here.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, Transaction
from backend.app.schemas.brim import BRIMAssetMapping, BRIMParseOutput, is_fake_asset_id
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim.brim_provider import BRIMProvider
from backend.app.services.brim.duplicates import detect_tx_duplicates

#: The ``max_length`` of ``TXCreateItem.ref`` and ``parent_ref``: a name of the batch.
REF_MAX_LENGTH = 36


def _describe(index: int, tx: TXCreateItem) -> str:
    """One row of an output, as a failure names it: position, type, date, amount, the two names."""
    cash = f"{tx.cash.amount} {tx.cash.code}" if tx.cash else "no cash"
    return f"#{index} {tx.type.value} {tx.date} {cash} ref={tx.ref!r} parent_ref={tx.parent_ref!r}"


def charge_link_structure_problems(transactions: Sequence[TXCreateItem]) -> List[str]:
    """The structural problems of the links of one parse output, one line each; ``[]`` when there is none.

    - a ``ref`` given to more than one row;
    - a ``parent_ref`` that names no ``ref`` of the output (an orphan);
    - a ``ref`` or a ``parent_ref`` longer than ``REF_MAX_LENGTH``.

    An empty string is no name, as the batch reads it (``charges._name``).
    """
    problems: List[str] = []
    named: Dict[str, int] = {}
    for index, tx in enumerate(transactions):
        if not tx.ref:
            continue
        if len(tx.ref) > REF_MAX_LENGTH:
            problems.append(f"ref longer than {REF_MAX_LENGTH} characters: {_describe(index, tx)}")
        if tx.ref in named:
            problems.append(f"ref {tx.ref!r} already given to row #{named[tx.ref]}: {_describe(index, tx)}")
        else:
            named[tx.ref] = index
    for index, tx in enumerate(transactions):
        if not tx.parent_ref:
            continue
        if len(tx.parent_ref) > REF_MAX_LENGTH:
            problems.append(f"parent_ref longer than {REF_MAX_LENGTH} characters: {_describe(index, tx)}")
        if tx.parent_ref not in named:
            problems.append(f"parent_ref {tx.parent_ref!r} names no ref of the output: {_describe(index, tx)}")
    return problems


def assert_charge_link_structure(output: BRIMParseOutput | Sequence[TXCreateItem], label: str) -> None:
    """Fail when the links of ``output`` (a parse output or its rows) are not well formed; ``label`` names the sample."""
    transactions = output.transactions if isinstance(output, BRIMParseOutput) else output
    problems = charge_link_structure_problems(transactions)
    assert not problems, f"{label}: {len(problems)} broken link(s) in the plugin output:\n  " + "\n  ".join(problems)


# ─── the reimport criterion (contract §6.3) ───────────────────────────────────────────────────────────────────────────


def _stored_row(tx: TXCreateItem, broker_id: int, real_assets: Dict[int, int]) -> Transaction:
    """``tx`` as a user of today has it saved: on ``broker_id``, its fake asset mapped to a real one, no link to a parent."""
    asset_id = real_assets.get(tx.asset_id, tx.asset_id) if tx.asset_id is not None else None
    return Transaction(
        broker_id=broker_id,
        asset_id=asset_id,
        type=tx.type,
        date=tx.date,
        quantity=tx.quantity,
        amount=tx.cash.amount if tx.cash else 0,
        currency=tx.cash.code if tx.cash else None,
        description=tx.description,
        tags=tx.get_tags_csv(),
        cost_basis_override=tx.cost_basis_override.amount if tx.cost_basis_override else None,
        cost_basis_currency=tx.cost_basis_override.code if tx.cost_basis_override else None,
        parent_transaction_id=None,  # the links are stripped: today's rows have none
    )


def _fake_asset_ids(rows: Iterable[TXCreateItem]) -> List[int]:
    """The fake asset ids ``rows`` use, in first-seen order."""
    return list(dict.fromkeys(tx.asset_id for tx in rows if tx.asset_id is not None and is_fake_asset_id(tx.asset_id)))


async def assert_reimport_adds_nothing(
    previous_rows: Sequence[TXCreateItem],
    plugin: BRIMProvider,
    sample_path: Path,
    broker_id: int,
    session: AsyncSession,
) -> BRIMParseOutput:
    """The file ``sample_path``, parsed by ``plugin``, adds no row to a broker that holds ``previous_rows`` (§6.3).

    1. ``previous_rows`` (the output of the previous version of the plugin on the same file, captured before the
       change) are saved on ``broker_id``, **without links**: ``ref`` and ``parent_ref`` do not exist in the database,
       and ``parent_transaction_id`` stays empty. Each fake asset id becomes a real ``Asset`` of its own; the legs that
       share a ``link_uuid`` become a stored pair.
    2. ``plugin`` parses ``sample_path`` on ``broker_id``.
    3. ``detect_tx_duplicates`` runs on the new rows, with the fake ids the previous rows also used resolved to the same
       real assets (``asset_mappings``, as the wizard auto-resolves them): a row that now carries an asset is matched
       through the ``asset_id == real OR asset_id IS NULL`` branch, the case at risk of P1a.
    4. Every incoming row is in the duplicate report, at any level (``POSSIBLE`` … ``LIKELY_WITH_ASSET``): the wizard
       shows it as a duplicate. A row in ``tx_unique_indices`` is a row the reimport would add.

    Everything this helper saves (rows and assets) is deleted before it returns, whatever the outcome. Returns the new
    parse output, so the caller can check what it was about.
    """
    fake_ids = _fake_asset_ids(previous_rows)
    marker = uuid.uuid4().hex[:8]
    assets = [Asset(display_name=f"Reimport probe {marker} {fake_id}", currency="EUR") for fake_id in fake_ids]
    saved_ids: List[int] = []
    asset_ids: List[int] = []
    try:
        session.add_all(assets)
        await session.flush()
        asset_ids = [asset.id for asset in assets]
        real_assets = dict(zip(fake_ids, asset_ids, strict=True))

        saved = [_stored_row(tx, broker_id, real_assets) for tx in previous_rows]
        session.add_all(saved)
        await session.flush()
        saved_ids = [row.id for row in saved]
        legs: Dict[str, List[Transaction]] = {}
        for tx, row in zip(previous_rows, saved, strict=True):
            if tx.link_uuid:
                legs.setdefault(tx.link_uuid, []).append(row)
        for pair in legs.values():
            if len(pair) == 2:
                pair[0].related_transaction_id, pair[1].related_transaction_id = pair[1].id, pair[0].id
        await session.commit()

        output = plugin.parse(sample_path, broker_id)
        mappings = [BRIMAssetMapping(fake_asset_id=fake_id, selected_asset_id=real_assets[fake_id]) for fake_id in _fake_asset_ids(output.transactions) if fake_id in real_assets]
        report = await detect_tx_duplicates(transactions=output.transactions, broker_id=broker_id, session=session, asset_mappings=mappings)

        found = {candidate.tx_row_index for candidate in (*report.tx_possible_duplicates, *report.tx_likely_duplicates)}
        new_rows = [_describe(index, tx) for index, tx in enumerate(output.transactions) if index not in found]
        assert not new_rows, f"{plugin.provider_code} [{Path(sample_path).name}]: the reimport adds {len(new_rows)} of {len(output.transactions)} row(s) " f"to a broker that holds the previous version's {len(previous_rows)}:\n  " + "\n  ".join(new_rows)
        assert report.tx_unique_indices == [], f"duplicate report lists unique rows: {report.tx_unique_indices}"
        return output
    finally:
        await _delete_saved(session, saved_ids, asset_ids)


async def _delete_saved(session: AsyncSession, row_ids: List[int], asset_ids: List[int]) -> None:
    """Delete what ``assert_reimport_adds_nothing`` saved, by id (the ORM objects are expired after the commit): the
    pairs unlinked first, then the rows, then the assets. Nothing was saved when the ids are empty (a failed flush)."""
    await session.rollback()
    if row_ids:
        await session.execute(update(Transaction).where(Transaction.id.in_(row_ids)).values(related_transaction_id=None).execution_options(synchronize_session=False))
        await session.execute(delete(Transaction).where(Transaction.id.in_(row_ids)).execution_options(synchronize_session=False))
    if asset_ids:
        await session.execute(delete(Asset).where(Asset.id.in_(asset_ids)).execution_options(synchronize_session=False))
    await session.commit()
