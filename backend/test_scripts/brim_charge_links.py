"""Test helpers for the linked charges a BRIM plugin emits (project 66, lot P1a, contract §3 and §6.2–§6.3).

Two checks every plugin test can call, and that the lots P2–P6 call on the real plugins:

- ``charge_link_structure_problems`` / ``assert_charge_link_structure``: the **structure** of a parse output — every
  ``ref`` unique, every ``parent_ref`` naming a ``ref`` of the same output, every name at most 36 characters. The domain
  rules of a link (which types, same broker, same asset) are not copied here: ``BRIMProvider._create_linked_charge``
  already applied them through ``services/transactions/charges.py`` (contract §6.2).
- ``assert_reimport_adds_nothing``: a file imported with the previous version of a plugin, imported again with the new
  one, adds no row (contract §6.3). The previous rows are saved without links, as a user of today has them; every
  incoming row must appear in the duplicate report of ``detect_tx_duplicates``, at any level.

And what the lots P2–P6 add on top (project 66, P2 contract §2, fixed by the wave P2a):

- **the snapshot of the previous version** (``load_previous_output``): the rows a plugin emitted on one of its samples
  *before* its lot changed it, saved as JSON under ``test_external/brim_previous_outputs/<plugin_code>/<sample>.json``.
  It is the ``previous_rows`` of the reimport criterion, never the new output stripped of its names (that would hide an
  amount, an asset or a type that changed). ``changes_besides_links`` compares a new output with it.
- **the expected links of a sample** (``assert_expected_charge_links``): which FEE/TAX names which parent, and which
  charges stay free. ``_create_linked_charge`` leaves a charge free in silence, so the structure check alone would pass
  with zero links (P1a-b).
- ``private_broker``: an in-memory database with one broker, for the reimport criterion of a plugin test.
- ``reimport_report`` / ``sample_reimport_report``: the reimport without its verdict, for a lot that changes amounts on
  purpose (Danske, P2c, contract §2.5): the test pins which rows are recognised and which are new.

**Capturing a snapshot** — only on the code *before* the lot changes the plugin, from the repository root::

    PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m backend.test_scripts.brim_charge_links \\
        capture --plugin broker_degiro --head <short HEAD> degiro-export.csv [more samples…]

It refuses an output that already carries ``ref``/``parent_ref`` (``--allow-links`` for a plugin that linked before
the lot, generic_csv), and it never replaces a snapshot taken at another plugin version (``--replace`` only re-takes
one at the same version). Never run it after the code change of the same wave.

**A report-set plugin** (``is_report_set_plugin``, Crédit Agricole) never parses one of its exports alone: a sample is
then a *set* written ``a.csv+b.xlsx`` (one member alone is a set of one), its members' roles read by ``detect_role``,
combined by the plugin and written by the core (``write_combined_csv``) as the set API does, and the combined file is
parsed (wave P2b). The snapshot is ``<plugin_code>/<stem a>+<stem b>.json`` and lists each member with its sha256::

    … capture --plugin broker_credit_agricole --head <short HEAD> credit_agricole-securities.csv+credit_agricole-account.xlsx

Not a test module: no ``test_`` prefix, nothing collected here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import uuid
from collections import Counter
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, AsyncIterator, Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

from backend.app.db.models import Asset, Broker, Transaction
from backend.app.schemas.brim import BRIMAssetMapping, BRIMExtractedAssetInfo, BRIMParseOutput, is_fake_asset_id
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.schemas.transactions.type_metadata import charge_types
from backend.app.services.brim.brim_provider import BRIMProvider
from backend.app.services.brim.combined_files import write_combined_csv
from backend.app.services.brim.duplicates import detect_tx_duplicates
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.test_scripts.brim_samples import BRIM_PROVIDERS_DIR, REPO_ROOT, SampleDir

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
    report = await reimport_report(previous_rows, plugin, sample_path, broker_id, session)
    output = report.output
    new_rows = [_describe(index, tx) for index, tx in enumerate(output.transactions) if index not in report.duplicates]
    assert not new_rows, f"{plugin.provider_code} [{Path(sample_path).name}]: the reimport adds {len(new_rows)} of {len(output.transactions)} row(s) " f"to a broker that holds the previous version's {len(previous_rows)}:\n  " + "\n  ".join(new_rows)
    assert report.unique == [], f"duplicate report lists unique rows: {report.unique}"
    return output


@dataclass(frozen=True)
class ReimportReport:
    """What a reimport over the previous version's rows finds (``reimport_report``): the new parse output, the indices
    of its rows the duplicate report names (at any level), and the indices it lists as unique (rows it would add)."""

    output: BRIMParseOutput
    duplicates: FrozenSet[int]
    unique: List[int]


async def reimport_report(
    previous_rows: Sequence[TXCreateItem],
    plugin: BRIMProvider,
    sample_path: Path,
    broker_id: int,
    session: AsyncSession,
) -> ReimportReport:
    """Steps 1–3 of ``assert_reimport_adds_nothing``, without its verdict: for a lot where the reimport is *expected* to
    add some rows (Danske, P2c: the trades whose amount changes, and their new fees; P2 contract §2.5), so the test pins
    both sides. Everything saved is deleted before it returns."""
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

        found = frozenset(candidate.tx_row_index for candidate in (*report.tx_possible_duplicates, *report.tx_likely_duplicates))
        return ReimportReport(output=output, duplicates=found, unique=list(report.tx_unique_indices))
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


@asynccontextmanager
async def private_broker(name: str = "Linked charges reimport") -> AsyncIterator[Tuple[AsyncSession, int]]:
    """An in-memory database of this test alone, with the ORM schema and one broker: never the lane's database.

    For ``assert_reimport_adds_nothing`` in a plugin test that is otherwise pure. The engine is disposed on exit (the
    aiosqlite leak guard of the shared conftest)."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    session = AsyncSession(engine)
    try:
        broker = Broker(name=name)
        session.add(broker)
        await session.commit()
        await session.refresh(broker)
        yield session, broker.id
    finally:
        await session.close()
        await engine.dispose()


# ─── the snapshot of the previous version (P2 contract §2.1) ──────────────────────────────────────────────────────────

#: Where the snapshots live: ``<plugin_code>/<sample stem>.json``.
PREVIOUS_OUTPUTS_DIR = Path(__file__).resolve().parent / "test_external" / "brim_previous_outputs"
#: The shape of a snapshot file; a loader that meets another one fails instead of guessing.
SNAPSHOT_FORMAT = "lf-brim-previous-output/1"
#: The broker a snapshot is parsed for. It is not stored: the loader gives each row the test's broker.
_CAPTURE_BROKER_ID = 1
#: Fields a linking version may add to a row: names of the batch, nothing else (``changes_besides_links``).
LINK_FIELDS = ("ref", "parent_ref")
#: Joins the members of a report set in a sample name: ``credit_agricole-securities.csv+credit_agricole-account.xlsx``.
SET_SEPARATOR = "+"
#: The name of the combined file a report set is parsed from (the parse output never names it).
COMBINED_FILE_NAME = "combined.csv"


@dataclass(frozen=True)
class PreviousOutput:
    """A snapshot as loaded: the plugin and its version, the commit it was taken on, its rows on the test's broker."""

    plugin_code: str
    plugin_version: str
    sample: str  # the sample's path from ``brim_providers/``; for a report set, its members' paths joined by ``SET_SEPARATOR``
    source_head: str
    transactions: List[TXCreateItem]
    extracted_assets: Dict[int, BRIMExtractedAssetInfo]


def sample_members(sample_name: str) -> List[str]:
    """The file names of a sample name: one, or the members of a report set (``a.csv+b.xlsx``)."""
    names = [name.strip() for name in sample_name.split(SET_SEPARATOR)]
    if not all(names):
        raise ValueError(f"{sample_name!r}: an empty member in the sample name")
    return names


def previous_output_path(plugin_code: str, sample_name: str) -> Path:
    """The snapshot file of ``sample_name`` (a file name of ``sample_reports/``, or a report set ``a.csv+b.xlsx``) read by
    ``plugin_code``: ``<stem>.json``, the names of a set joined by ``SET_SEPARATOR``. A CSV is named by its stem (the
    files of P2a), any other file keeps its extension: ``credit_agricole-conti.csv`` and ``credit_agricole-conti.xlsx``
    are two samples, so two snapshots."""
    names = [Path(name).stem if Path(name).suffix.lower() == ".csv" else Path(name).name for name in sample_members(sample_name)]
    return PREVIOUS_OUTPUTS_DIR / plugin_code / f"{SET_SEPARATOR.join(names)}.json"


def sample_input(plugin: BRIMProvider, sample_name: str, folder: Path) -> Path:
    """The file ``plugin.parse`` reads for ``sample_name``.

    A plain plugin reads the sample itself. A report-set plugin never parses one of its exports alone: the members are
    given their role (``detect_role``), combined by the plugin and written by the core in ``folder`` as the set API does
    (``COMBINED_FILE_NAME``, replaced if there), and that combined file is what ``parse`` reads.
    """
    samples = SampleDir()
    names = sample_members(sample_name)
    paths = [samples / name for name in names]
    missing = [name for name, path in zip(names, paths, strict=True) if not path.is_file()]
    if missing:
        raise ValueError(f"no sample {', '.join(missing)}")
    if not plugin.is_report_set_plugin:
        if len(paths) != 1:
            raise ValueError(f"{plugin.provider_code} is not a report-set plugin: {sample_name!r} names {len(paths)} files")
        return paths[0]
    members: Dict[str, List[Path]] = {}
    for name, path in zip(names, paths, strict=True):
        role = plugin.detect_role(path)
        if role is None:
            raise ValueError(f"{plugin.provider_code} reads {name} as no role of its set")
        members.setdefault(role, []).append(path)
    folder.mkdir(parents=True, exist_ok=True)
    combined = folder / COMBINED_FILE_NAME
    write_combined_csv(combined, plugin.combine(members))
    return combined


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rebuild(row: Dict[str, Any], broker_id: int) -> TXCreateItem:
    return TXCreateItem.model_validate({**row, "broker_id": broker_id})


def load_previous_snapshot(plugin_code: str, sample_name: str, broker_id: int) -> PreviousOutput:
    """The snapshot of ``sample_name`` read by ``plugin_code``, its rows rebuilt on ``broker_id``.

    Fails when the file is missing, has another format, or when the sample changed since it was taken (its sha256): the
    rows would no longer be the previous version's output *of this file*.
    """
    path = previous_output_path(plugin_code, sample_name)
    assert path.is_file(), f"no snapshot of the previous version for {plugin_code} [{sample_name}]: {path} (capture it before the code change)"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("format") == SNAPSHOT_FORMAT, f"{path}: format {data.get('format')!r}, expected {SNAPSHOT_FORMAT!r}"
    assert data["plugin_code"] == plugin_code, f"{path}: taken for {data['plugin_code']}, not {plugin_code}"
    # A report set lists its members (P2b); a single sample is one member of its own (the P2a files, unchanged).
    members = data.get("members") or [{"sample": data["sample"], "sample_sha256": data["sample_sha256"]}]
    expected = [Path(name).name for name in sample_members(sample_name)]
    assert [Path(member["sample"]).name for member in members] == expected, f"{path}: taken on {[member['sample'] for member in members]}, not on {expected}"
    for member in members:
        sample_path = BRIM_PROVIDERS_DIR / member["sample"]
        assert sample_path.is_file(), f"{path}: its sample {member['sample']} no longer exists"
        assert _sha256(sample_path) == member["sample_sha256"], f"{path}: the sample {member['sample']} changed after the snapshot was taken (HEAD {data['source_head']}): " "the snapshot no longer describes this file"
    return PreviousOutput(
        plugin_code=data["plugin_code"],
        plugin_version=data["plugin_version"],
        sample=SET_SEPARATOR.join(member["sample"] for member in members),
        source_head=data["source_head"],
        transactions=[_rebuild(row, broker_id) for row in data["transactions"]],
        extracted_assets={int(fake_id): BRIMExtractedAssetInfo.model_validate(info) for fake_id, info in data["extracted_assets"].items()},
    )


def load_previous_output(plugin_code: str, sample_name: str, broker_id: int) -> List[TXCreateItem]:
    """The rows the previous version of ``plugin_code`` emitted on ``sample_name``, on ``broker_id``: the
    ``previous_rows`` of ``assert_reimport_adds_nothing``."""
    return load_previous_snapshot(plugin_code, sample_name, broker_id).transactions


def _snapshot_rows(plugin: BRIMProvider, output: BRIMParseOutput, label: str, allow_links: bool) -> List[Dict[str, Any]]:
    """The rows of ``output`` as a snapshot stores them (no broker); refuses links (unless ``allow_links``) and rows that
    do not come back equal from their JSON (a Decimal or a date that would not round-trip)."""
    rows: List[Dict[str, Any]] = []
    for index, tx in enumerate(output.transactions):
        if not allow_links and (tx.ref or tx.parent_ref):
            raise ValueError(f"{plugin.provider_code} [{label}]: row {_describe(index, tx)} already carries a link: is this the code after the change?")
        row = tx.model_dump(mode="json")
        if row.pop("broker_id") != _CAPTURE_BROKER_ID:
            raise ValueError(f"{plugin.provider_code} [{label}]: row #{index} is not on the broker parse was given")
        if _rebuild(row, _CAPTURE_BROKER_ID) != tx:
            raise ValueError(f"{plugin.provider_code} [{label}]: row {_describe(index, tx)} does not round-trip through JSON")
        rows.append(row)
    return rows


def _snapshot(plugin: BRIMProvider, output: BRIMParseOutput, source_head: str, sample: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "format": SNAPSHOT_FORMAT,
        "comment": "Output of the plugin BEFORE its project-66 lot changed it (P2 contract §2.1). Never re-take it after the code change.",
        "plugin_code": plugin.provider_code,
        "plugin_version": plugin.plugin_version,
        "source_head": source_head,
        "captured_on": date.today().isoformat(),
        **sample,
        "extracted_assets": {str(fake_id): info.model_dump(mode="json") for fake_id, info in output.extracted_assets.items()},
        "transactions": rows,
    }


def _member(path: Path) -> Dict[str, str]:
    return {"sample": path.resolve().relative_to(BRIM_PROVIDERS_DIR).as_posix(), "sample_sha256": _sha256(path)}


def capture_previous_output(plugin: BRIMProvider, sample_path: Path, *, source_head: str, allow_links: bool = False) -> Dict[str, Any]:
    """The snapshot of ``plugin`` on ``sample_path``, as ``load_previous_snapshot`` reads it (not written here).

    Refuses an output with ``ref``/``parent_ref`` unless ``allow_links`` (a previous version has no links, P2–P5), and
    an output whose rows do not come back equal from their JSON (a Decimal or a date that would not round-trip).
    """
    output = plugin.parse(sample_path, _CAPTURE_BROKER_ID)
    rows = _snapshot_rows(plugin, output, sample_path.name, allow_links)
    return _snapshot(plugin, output, source_head, _member(sample_path), rows)


def capture_previous_set_output(plugin: BRIMProvider, sample_name: str, *, source_head: str, allow_links: bool = False) -> Dict[str, Any]:
    """The snapshot of a report-set ``plugin`` on the set ``sample_name`` (``a.csv+b.xlsx``, or one member alone): the
    members combined and parsed as ``sample_input`` does, each member listed with its sha256 (``members``)."""
    with tempfile.TemporaryDirectory(prefix="lf-brim-capture-") as folder:
        output = plugin.parse(sample_input(plugin, sample_name, Path(folder)), _CAPTURE_BROKER_ID)
    rows = _snapshot_rows(plugin, output, sample_name, allow_links)
    samples = SampleDir()
    return _snapshot(plugin, output, source_head, {"members": [_member(samples / name) for name in sample_members(sample_name)]}, rows)


async def assert_sample_reimport_adds_nothing(plugin: BRIMProvider, sample_name: str) -> BRIMParseOutput:
    """The reimport criterion on one sample, in a database of its own: the snapshot of the previous version of
    ``plugin`` on ``sample_name`` is saved without links, then the sample parsed by ``plugin`` must add no row."""
    async with private_broker(f"Reimport {plugin.provider_code}") as (session, broker_id):
        previous_rows = load_previous_output(plugin.provider_code, sample_name, broker_id)
        with tempfile.TemporaryDirectory(prefix="lf-brim-reimport-") as folder:
            return await assert_reimport_adds_nothing(previous_rows, plugin, sample_input(plugin, sample_name, Path(folder)), broker_id, session)


async def sample_reimport_report(plugin: BRIMProvider, sample_name: str) -> ReimportReport:
    """``reimport_report`` on one sample, in a database of its own: the snapshot of the previous version of ``plugin`` on
    ``sample_name`` is saved without links, then the sample is parsed by ``plugin`` and checked for duplicates."""
    async with private_broker(f"Reimport {plugin.provider_code}") as (session, broker_id):
        previous_rows = load_previous_output(plugin.provider_code, sample_name, broker_id)
        with tempfile.TemporaryDirectory(prefix="lf-brim-reimport-") as folder:
            return await reimport_report(previous_rows, plugin, sample_input(plugin, sample_name, Path(folder)), broker_id, session)


def version_tuple(version: str) -> Tuple[int, ...]:
    """``"1.10.0"`` as ``(1, 10, 0)``: versions compared as numbers, never as text."""
    return tuple(int(part) for part in version.split("."))


def _comparable_row(tx: TXCreateItem) -> Dict[str, Any]:
    return tx.model_dump(mode="json", exclude=set(LINK_FIELDS))


def changes_besides_links(previous_rows: Sequence[TXCreateItem], current_rows: Sequence[TXCreateItem]) -> List[str]:
    """What a new output changed of the previous one besides the names (``ref``, ``parent_ref``), one line each.

    The rows are compared in order, field by field (type, date, quantity, cash, asset, broker, description, tags…): a
    lot that only links its charges adds names and never changes a number (P2 contract §2.1). ``[]`` when nothing else
    changed.
    """
    problems: List[str] = []
    if len(previous_rows) != len(current_rows):
        problems.append(f"{len(current_rows)} rows, the previous version emitted {len(previous_rows)}")
    for index, (before, after) in enumerate(zip(previous_rows, current_rows, strict=False)):
        old, new = _comparable_row(before), _comparable_row(after)
        changed = {field: (old[field], new[field]) for field in old if old[field] != new[field]}
        if changed:
            problems.append(f"#{index} {before.type.value} {before.date}: " + ", ".join(f"{field} {was!r} → {now!r}" for field, (was, now) in changed.items()))
    return problems


# ─── the expected links of a sample (P2 contract §2.3) ────────────────────────────────────────────────────────────────

#: A row of a parse output, named without its position: type, ISO date, cash amount (text), cash currency, and the
#: identifier the plugin extracted for its asset (ISIN, else symbol), None for no asset.
RowKey = Tuple[str, str, str, str, Optional[str]]


def _identifier(output: BRIMParseOutput, asset_id: Optional[int]) -> Optional[str]:
    if asset_id is None:
        return None
    info = output.extracted_assets.get(asset_id)
    return (info.extracted_isin or info.extracted_symbol) if info else f"asset {asset_id}"


def _matches(output: BRIMParseOutput, tx: TXCreateItem, key: RowKey) -> bool:
    tx_type, day, amount, currency, identifier = key
    return tx.type.value == tx_type and tx.date.isoformat() == day and tx.cash is not None and tx.cash.amount == Decimal(amount) and tx.cash.code == currency and _identifier(output, tx.asset_id) == identifier


def _find(output: BRIMParseOutput, key: RowKey, problems: List[str]) -> Optional[TXCreateItem]:
    found = [tx for tx in output.transactions if _matches(output, tx, key)]
    if len(found) != 1:
        problems.append(f"{len(found)} rows match {key}: a key names exactly one row of the output")
        return None
    return found[0]


def _linked_problems(output: BRIMParseOutput, linked: Sequence[Tuple[RowKey, RowKey]], declared: List[int]) -> List[str]:
    """The (charge, parent) pairs that do not hold: the charge names the parent, with its asset and its broker."""
    problems: List[str] = []
    kinds = {tx_type.value for tx_type in charge_types()}
    for charge_key, parent_key in linked:
        if charge_key[0] not in kinds:
            problems.append(f"the expectation links {charge_key}, which is not a charge type")
        charge, parent = _find(output, charge_key, problems), _find(output, parent_key, problems)
        if charge is None or parent is None:
            continue
        declared.append(id(charge))
        if not parent.ref or charge.parent_ref != parent.ref:
            problems.append(f"{charge_key} should name {parent_key} as its parent: parent_ref={charge.parent_ref!r}, the parent's ref={parent.ref!r}")
        if charge.asset_id != parent.asset_id:
            problems.append(f"{charge_key} should have its parent's asset: {charge.asset_id} vs {parent.asset_id}")
        if charge.broker_id != parent.broker_id:
            problems.append(f"{charge_key} should be on its parent's broker: {charge.broker_id} vs {parent.broker_id}")
    return problems


def _free_problems(output: BRIMParseOutput, free: Sequence[RowKey], declared: List[int]) -> List[str]:
    """The charges expected free that name a parent.

    A key listed n times names exactly n rows (identical free charges, e.g. three connection fees of one day): rows alike
    that all stay free need no position to be told apart."""
    problems: List[str] = []
    for charge_key, times in Counter(free).items():
        charges = [tx for tx in output.transactions if _matches(output, tx, charge_key)]
        if len(charges) != times:
            problems.append(f"{len(charges)} rows match {charge_key}: the expectation lists it {times} time(s), one per row")
            continue
        for charge in charges:
            declared.append(id(charge))
            if charge.parent_ref:
                problems.append(f"{charge_key} should stay free, it names {charge.parent_ref!r}")
    return problems


def charge_link_expectation_problems(output: BRIMParseOutput, *, linked: Sequence[Tuple[RowKey, RowKey]], free: Sequence[RowKey], exhaustive: bool = True) -> List[str]:
    """How ``output`` differs from the links a sample is expected to give, one line each; ``[]`` when it matches.

    - ``linked``: (charge, parent) — the charge names the parent (``parent_ref`` = the parent's non-empty ``ref``) and
      has the parent's asset and broker;
    - ``free``: the charges that name no parent (a key listed n times names n identical rows);
    - with ``exhaustive`` (the default) every FEE and TAX of the output is declared in one of the two (an undeclared
      charge is a problem); in any case no row that is not a charge names a parent.

    Each key of ``linked`` must name exactly one row (``RowKey``): two rows alike are told apart by their security, never
    by position; identical free charges are listed once per row.
    """
    declared: List[int] = []
    problems = [*_linked_problems(output, linked, declared), *_free_problems(output, free, declared)]
    charges = charge_types()
    for index, tx in enumerate(output.transactions):
        if exhaustive and tx.type in charges and id(tx) not in declared:
            problems.append(f"charge not declared by the expectation: {_describe(index, tx)}")
        if tx.type not in charges and tx.parent_ref:
            problems.append(f"a row that is not a charge names a parent: {_describe(index, tx)}")
    repeated = [key for key, count in Counter(declared).items() if count > 1]
    if repeated:
        problems.append(f"{len(repeated)} charge(s) declared more than once")
    return problems


def assert_expected_charge_links(output: BRIMParseOutput, label: str, *, linked: Sequence[Tuple[RowKey, RowKey]], free: Sequence[RowKey], exhaustive: bool = True) -> None:
    """Fail when the links of ``output`` are not the expected ones (``charge_link_expectation_problems``); ``label``
    names the sample."""
    problems = charge_link_expectation_problems(output, linked=linked, free=free, exhaustive=exhaustive)
    assert not problems, f"{label}: {len(problems)} unexpected link(s):\n  " + "\n  ".join(problems)


# ─── the capture command ──────────────────────────────────────────────────────────────────────────────────────────────


def _capture_main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m backend.test_scripts.brim_charge_links", description="Snapshot of a BRIM plugin's output on its samples, BEFORE the code change (project 66).")
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("capture", help="write the snapshot of each sample")
    capture.add_argument("--plugin", required=True, help="the plugin code, e.g. broker_degiro")
    capture.add_argument("--head", required=True, help="the short HEAD of the code the snapshot is taken on (before the change)")
    capture.add_argument("--replace", action="store_true", help="re-take a snapshot that exists, only at the same plugin version")
    capture.add_argument("--allow-links", action="store_true", help="accept an output that already links (a plugin that linked before its lot)")
    capture.add_argument("samples", nargs="+", help="sample file names, as in sample_reports/; for a report-set plugin a set, its members joined by '+'")
    args = parser.parse_args(argv)

    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(args.plugin)
    if plugin is None:
        parser.error(f"no BRIM plugin {args.plugin}")
    samples = SampleDir()
    is_set = plugin.is_report_set_plugin
    for sample_name in args.samples:
        target = previous_output_path(args.plugin, sample_name)
        if target.exists():
            existing = json.loads(target.read_text(encoding="utf-8"))
            if existing.get("plugin_version") != plugin.plugin_version:
                parser.error(f"{target}: taken at version {existing.get('plugin_version')}, the plugin is now {plugin.plugin_version}: the code changed, the snapshot stays")
            if not args.replace:
                parser.error(f"{target} exists: --replace to re-take it at the same version")
        missing = [name for name in sample_members(sample_name) if not (samples / name).is_file()]
        if missing:
            parser.error(f"no sample {', '.join(missing)}")
        if is_set:
            snapshot = capture_previous_set_output(plugin, sample_name, source_head=args.head, allow_links=args.allow_links)
        else:
            if len(sample_members(sample_name)) != 1:
                parser.error(f"{args.plugin} is not a report-set plugin: one file per sample")
            snapshot = capture_previous_output(plugin, samples / sample_name, source_head=args.head, allow_links=args.allow_links)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{target.relative_to(REPO_ROOT)}: {len(snapshot['transactions'])} rows, {args.plugin} {plugin.plugin_version}, HEAD {args.head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_capture_main())
