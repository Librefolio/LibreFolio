"""Linked charges in a BRIM plugin (project 66, lot P1a): the helpers of the parent ``BRIMProvider``.

Written red-first, before the code (contract ``66-P1a-contract.md``, §4 as corrected by §6). What the lot adds to
``backend/app/services/brim/brim_provider.py``:

- ``_create_linked_charge(row_num, transactions, validation_issues, parent, *, context=None, **kwargs)``: a FEE or a TAX
  that belongs to ``parent``, a row the plugin already created. The link is judged by ``charge_link_issue``
  (``services/transactions/charges.py``) on a view of the incoming rows, ``related_transaction_id`` read from
  ``link_uuid``. The charge's asset is filled with the parent's **only when it is missing** (contract §9): never changed,
  never removed, and the link is judged after the filling, on the charge's real values. A valid link gives the charge
  ``parent_ref = parent.ref`` (the parent named first when it has no name) and the parent's broker; an invalid one (a
  parent ADJUSTMENT, a CASH_TRANSFER, a leg of a pair, a FEE, a charge whose own asset differs from the parent's) gives a
  free charge with the plugin's own values, the parent's broker when it has none, and no issue (§6.1, §7.2). A charge
  type other than FEE or TAX is a programming error: ``ValueError``. An invalid item is an issue and ``None``, as with
  ``_create_transaction``.
- ``_ensure_ref(parent, transactions)``: the name of a parent, ``r<n>`` with n = 1 + its position in ``transactions``
  found by identity (never ``list.index``: two equal trades of one day are equal for pydantic), ``-2``, ``-3``… on a
  collision; the existing name when it has one; at most 36 characters (§2, §6.4).

The common structural check of a plugin output (§3, §6.2: ``backend/test_scripts/brim_charge_links.py``) is run on every
registered plugin and sample by ``test_external/test_brim_providers.py``; here it is checked against fake plugins: one
that emits an orphan ``parent_ref`` by hand (the check must report it) and one that links through the helper. The
reimport criterion (§6.3) runs on a private in-memory database: the previous version of a fake plugin emits a FEE with
no asset and no link, the new one the same FEE with its parent's asset and ``parent_ref``; nothing is added.

Until the code exists, every test that calls ``_create_linked_charge`` or ``_ensure_ref`` fails with ``AttributeError``.

What the wave P2b adds to ``brim_charge_links.py`` is checked at the end: identical free charges listed once per row,
the snapshot of a report set (its members combined as the set API does, each with its sha256), the snapshot file names.
The same wave adds ``_link_existing_charge(charge, parent, transactions, *, row_num=0)``, which links a charge already
in the output (degiro, Crédit Agricole link after reading the whole file): its guards, and its parity with
``_create_linked_charge`` (one shared check, ``_charge_link_check``), close the file.

PURE for the runner: no server, no shared database (the reimport tests open their own in-memory SQLite and dispose it).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

import pytest

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMParseOutput, BRIMValidationIssue
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim.brim_provider import BRIMProvider
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.test_scripts import brim_charge_links
from backend.test_scripts.brim_charge_links import (
    REF_MAX_LENGTH,
    assert_charge_link_structure,
    assert_reimport_adds_nothing,
    capture_previous_set_output,
    charge_link_expectation_problems,
    charge_link_structure_problems,
    load_previous_snapshot,
    previous_output_path,
    private_broker,
    sample_input,
)

BROKER_ID = 7
DAY = date(2025, 3, 14)
#: Two fake asset ids, as a plugin numbers them (downwards from FAKE_ASSET_ID_BASE).
FAKE_A = FAKE_ASSET_ID_BASE
FAKE_B = FAKE_ASSET_ID_BASE - 1
PAIR_UUID = "8a3c1f2e-5b6d-4e7f-9a0b-1c2d3e4f5a6b"


class FakeBroker(BRIMProvider):
    """A minimal plugin: only what the abstract base requires. Never registered, so the plugin suites never see it."""

    @property
    def provider_code(self) -> str:
        return "test_linked_charges"

    @property
    def provider_name(self) -> str:
        return "Linked charges test plugin"

    @property
    def description(self) -> str:
        return "Fake plugin for the linked-charge helpers"

    def can_parse(self, file_path: Path) -> bool:
        return True

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        return BRIMParseOutput(transactions=[], warnings=[], extracted_assets={})


@pytest.fixture
def provider() -> FakeBroker:
    return FakeBroker()


# ─── builders ─────────────────────────────────────────────────────────────────────────────────────────────────────────


def _parent_kwargs(tx_type: TransactionType, **overrides) -> dict:
    """The kwargs of a valid row of ``tx_type`` on BROKER_ID, as a plugin passes them to ``_create_transaction``."""
    shapes = {
        TransactionType.BUY: {"asset_id": FAKE_A, "quantity": Decimal("10"), "cash": Currency(code="EUR", amount=Decimal("-1000"))},
        TransactionType.SELL: {"asset_id": FAKE_A, "quantity": Decimal("-10"), "cash": Currency(code="EUR", amount=Decimal("1100"))},
        TransactionType.DEPOSIT: {"asset_id": None, "quantity": Decimal("0"), "cash": Currency(code="EUR", amount=Decimal("500"))},
        TransactionType.ADJUSTMENT: {"asset_id": FAKE_A, "quantity": Decimal("5"), "cash": None},
        TransactionType.CASH_TRANSFER: {"asset_id": None, "quantity": Decimal("0"), "cash": Currency(code="EUR", amount=Decimal("300")), "link_uuid": PAIR_UUID},
        TransactionType.FEE: {"asset_id": FAKE_A, "quantity": Decimal("0"), "cash": Currency(code="EUR", amount=Decimal("-4"))},
    }
    kwargs = {"broker_id": BROKER_ID, "type": tx_type, "date": DAY, "description": f"{tx_type.value} row", **shapes[tx_type]}
    kwargs.update(overrides)
    return kwargs


def _charge_kwargs(tx_type: TransactionType = TransactionType.FEE, **overrides) -> dict:
    """The kwargs of a valid charge on BROKER_ID: no asset unless an override gives one."""
    kwargs = {"broker_id": BROKER_ID, "type": tx_type, "date": DAY, "quantity": Decimal("0"), "cash": Currency(code="EUR", amount=Decimal("-2.50")), "description": f"{tx_type.value} charge"}
    kwargs.update(overrides)
    return kwargs


def _add_parent(provider: BRIMProvider, transactions: List[TXCreateItem], tx_type: TransactionType, **overrides) -> TXCreateItem:
    """A parent row created as a plugin creates it, its validity checked (the premise of every case)."""
    issues: List[BRIMValidationIssue] = []
    row = provider._create_transaction(row_num=len(transactions) + 1, transactions=transactions, validation_issues=issues, **_parent_kwargs(tx_type, **overrides))
    assert row is not None and issues == [], f"premise: a valid {tx_type.value} parent; issues {issues}"
    return row


def _link(provider: BRIMProvider, transactions: List[TXCreateItem], parent: TXCreateItem, issues: Optional[List[BRIMValidationIssue]] = None, **kwargs) -> Optional[TXCreateItem]:
    """``_create_linked_charge`` called as a plugin calls it: the parent named, the charge's fields as kwargs."""
    return provider._create_linked_charge(row_num=99, transactions=transactions, validation_issues=issues if issues is not None else [], parent=parent, context="charge row", **kwargs)


# ─── _create_linked_charge: a valid link ──────────────────────────────────────────────────────────────────────────────


class TestLinkedChargeValid:
    """A charge under a parent type: ``parent_ref`` is the parent's name, the broker is the parent's, a missing asset is
    the parent's."""

    def test_fee_under_buy_with_fake_asset(self, provider):
        transactions: List[TXCreateItem] = []
        buy = _add_parent(provider, transactions, TransactionType.BUY)
        assert buy.ref is None, "premise: a row created by _create_transaction has no name"
        issues: List[BRIMValidationIssue] = []

        fee = _link(provider, transactions, buy, issues, **_charge_kwargs(asset_id=FAKE_A))

        assert fee is not None and issues == [], f"a valid FEE under a BUY is created; issues {issues}"
        assert len(transactions) == 2 and transactions[0] is buy and transactions[1] is fee, "the charge is appended after its parent, the parent object is kept"
        assert buy.ref, "the parent without a name receives one"
        assert len(buy.ref) <= REF_MAX_LENGTH
        assert fee.parent_ref == buy.ref
        assert fee.parent_transaction_id is None, "a parent of the same file is named by ref, never by id"
        assert (fee.type, fee.broker_id, fee.asset_id) == (TransactionType.FEE, buy.broker_id, FAKE_A)
        assert (fee.cash, fee.date, fee.description) == (Currency(code="EUR", amount=Decimal("-2.50")), DAY, "FEE charge"), "the charge keeps its own amount, date and text"
        assert charge_link_structure_problems(transactions) == []

    def test_charge_without_asset_takes_the_parents(self, provider):
        """The case at risk of the reimport: a plugin that passes no asset for the fee still gets the parent's (rule 3)."""
        transactions: List[TXCreateItem] = []
        buy = _add_parent(provider, transactions, TransactionType.BUY)

        fee = _link(provider, transactions, buy, **_charge_kwargs())

        assert fee is not None
        assert (fee.parent_ref, fee.asset_id) == (buy.ref, FAKE_A)

    def test_parent_named_by_the_plugin_keeps_its_name(self, provider):
        transactions: List[TXCreateItem] = []
        buy = _add_parent(provider, transactions, TransactionType.BUY, ref="order-42")

        fee = _link(provider, transactions, buy, **_charge_kwargs())

        assert fee is not None
        assert buy.ref == "order-42"
        assert fee.parent_ref == "order-42"

    def test_two_charges_share_the_parent_named_once(self, provider):
        transactions: List[TXCreateItem] = []
        _add_parent(provider, transactions, TransactionType.DEPOSIT)  # a row before the parent: the name is not r1
        buy = _add_parent(provider, transactions, TransactionType.BUY)

        fee = _link(provider, transactions, buy, **_charge_kwargs())
        name_after_first = buy.ref
        tax = _link(provider, transactions, buy, **_charge_kwargs(TransactionType.TAX, cash=Currency(code="EUR", amount=Decimal("-0.20"))))

        assert fee is not None and tax is not None
        assert name_after_first, "the first charge names the parent"
        assert buy.ref == name_after_first, "the second charge does not rename the parent"
        assert fee.parent_ref == tax.parent_ref == buy.ref
        assert transactions[0].ref is None, "only the parent is named"
        assert charge_link_structure_problems(transactions) == []

    @pytest.mark.parametrize("own_broker", [BROKER_ID + 1, None], ids=["kwargs-other-broker", "kwargs-without-broker"])
    def test_charge_takes_the_parents_broker(self, provider, own_broker):
        """Coordinator's decision (P1a, answer 3a): like the asset, the broker is always the parent's (rule 2): a
        different ``broker_id`` in the kwargs is overridden, and the kwargs may omit it."""
        transactions: List[TXCreateItem] = []
        buy = _add_parent(provider, transactions, TransactionType.BUY)
        kwargs = _charge_kwargs()
        if own_broker is None:
            del kwargs["broker_id"]
        else:
            kwargs["broker_id"] = own_broker
        issues: List[BRIMValidationIssue] = []

        fee = _link(provider, transactions, buy, issues, **kwargs)

        assert fee is not None and issues == [], f"issues {issues}"
        assert fee.broker_id == BROKER_ID, f"the parent's broker wins; got {fee.broker_id}"
        assert fee.parent_ref == buy.ref and buy.ref
        assert fee.asset_id == FAKE_A


# ─── _create_linked_charge: the asset is filled only when missing (contract §9) ───────────────────────────────────────

_ABSENT = object()  # the kwargs carry no asset_id key at all

#: The table of contract §9: (charge's asset in the kwargs, parent type, expected linked?, expected charge asset).
#: BUY and SELL carry FAKE_A (asset Y); DEPOSIT carries none. FAKE_B is the charge's own asset X.
ASSET_RULE = [
    pytest.param(_ABSENT, TransactionType.BUY, True, FAKE_A, id="absent-under-Y-linked-takes-Y"),
    pytest.param(None, TransactionType.BUY, True, FAKE_A, id="none-under-Y-linked-takes-Y"),
    pytest.param(FAKE_A, TransactionType.BUY, True, FAKE_A, id="Y-under-Y-linked-keeps-Y"),
    pytest.param(FAKE_B, TransactionType.SELL, False, FAKE_B, id="X-under-Y-free-keeps-X"),
    pytest.param(FAKE_B, TransactionType.DEPOSIT, False, FAKE_B, id="X-under-no-asset-free-keeps-X"),
    pytest.param(_ABSENT, TransactionType.DEPOSIT, True, None, id="absent-under-no-asset-linked-without-asset"),
    pytest.param(None, TransactionType.DEPOSIT, True, None, id="none-under-no-asset-linked-without-asset"),
]


@pytest.mark.parametrize(("own_asset", "parent_type", "linked", "expected_asset"), ASSET_RULE)
def test_asset_is_filled_only_when_missing(provider, own_asset, parent_type, linked, expected_asset):
    """Contract §9 (consultant, P1a-b): the helper fills the charge's asset with the parent's only when it is missing;
    it never changes it and never removes it, and ``charge_link_issue`` judges the charge's real values after the
    filling. A charge with its own asset X under a parent with asset Y, or under a parent without asset, is free: it
    keeps X, gets no ``parent_ref``, leaves the parent unnamed, and is no issue for the user."""
    transactions: List[TXCreateItem] = []
    parent = _add_parent(provider, transactions, parent_type)
    kwargs = _charge_kwargs()
    if own_asset is not _ABSENT:
        kwargs["asset_id"] = own_asset
    issues: List[BRIMValidationIssue] = []

    fee = _link(provider, transactions, parent, issues, **kwargs)

    assert fee is not None and issues == [], f"the charge is created, no issue; got {issues}"
    assert transactions[-1] is fee and len(transactions) == 2
    assert fee.asset_id == expected_asset, f"asset {expected_asset} expected; got {fee.asset_id}"
    assert fee.broker_id == parent.broker_id
    if linked:
        assert parent.ref, "a linked charge names its parent"
        assert fee.parent_ref == parent.ref
    else:
        assert not fee.parent_ref, f"a charge whose own asset is not the parent's stays free; got parent_ref {fee.parent_ref!r}"
        assert parent.ref is None, f"no link, no name; the {parent_type.value} parent got {parent.ref!r}"
    assert charge_link_structure_problems(transactions) == []


# ─── _create_linked_charge: an invalid link gives a free charge (§6.1) ────────────────────────────────────────────────


#: The parents a charge cannot be linked to. The DEPOSIT with ``link_uuid`` is the discriminating case of the view (a
#: parent type, only its ``link_uuid`` makes it a leg, rule 8); the batch refuses it already (R0), the case stays as a defence.
INVALID_PARENTS = [
    pytest.param(TransactionType.ADJUSTMENT, {}, id="parent-adjustment"),
    pytest.param(TransactionType.CASH_TRANSFER, {}, id="parent-cash-transfer"),
    pytest.param(TransactionType.DEPOSIT, {"link_uuid": PAIR_UUID}, id="parent-pair-leg-deposit"),
    pytest.param(TransactionType.FEE, {}, id="tax-on-a-fee"),
]


def _charge_type_for(parent_type: TransactionType) -> TransactionType:
    """A TAX on a FEE (a charge under a charge), a FEE on anything else."""
    return TransactionType.TAX if parent_type == TransactionType.FEE else TransactionType.FEE


@pytest.mark.parametrize(("parent_type", "parent_overrides"), INVALID_PARENTS)
def test_invalid_link_gives_a_free_charge_with_its_own_values(provider, parent_type, parent_overrides):
    """D10: a parent that is not a parent is no error; the charge is created as today, with the plugin's values."""
    transactions: List[TXCreateItem] = []
    parent = _add_parent(provider, transactions, parent_type, **parent_overrides)
    issues: List[BRIMValidationIssue] = []
    tax = _charge_type_for(parent_type)

    charge = _link(provider, transactions, parent, issues, **_charge_kwargs(tax, asset_id=FAKE_B))

    assert charge is not None, f"the charge is still created; issues {issues}"
    assert issues == [], f"a link the commit would refuse is not the user's problem: no issue; got {issues}"
    assert transactions[-1] is charge and len(transactions) == 2
    assert not charge.parent_ref, f"no link to a {parent_type.value}{' leg' if parent_overrides else ''}; got parent_ref {charge.parent_ref!r}"
    assert charge.parent_transaction_id is None
    assert (charge.type, charge.broker_id, charge.asset_id) == (tax, BROKER_ID, FAKE_B), "the free charge keeps the plugin's own values, asset included"
    assert charge_link_structure_problems(transactions) == []


@pytest.mark.parametrize(("parent_type", "parent_overrides"), INVALID_PARENTS)
def test_free_charge_leaves_the_parent_unnamed(provider, parent_type, parent_overrides):
    """Coordinator's decision (P1a, answer 3b): a parent nothing is linked to gets no name; its ``ref`` stays None."""
    transactions: List[TXCreateItem] = []
    parent = _add_parent(provider, transactions, parent_type, **parent_overrides)

    charge = _link(provider, transactions, parent, **_charge_kwargs(_charge_type_for(parent_type), asset_id=FAKE_B))

    assert charge is not None and not charge.parent_ref, "premise: the charge is free"
    assert parent.ref is None, f"no link, no name: the {parent_type.value} parent got ref {parent.ref!r}"


@pytest.mark.parametrize(("parent_type", "parent_overrides"), INVALID_PARENTS)
def test_free_charge_without_broker_takes_the_parents(provider, parent_type, parent_overrides):
    """Coordinator's decision (P1a contract §7.2, widened): ``broker_id`` omitted from the kwargs is the parent's broker
    on the free branch too. ``TXCreateItem`` requires a broker: passing the kwargs as they are would lose the charge as
    an issue (``brokerRequired`` or a missing field). A ``broker_id`` the plugin passes stays its own on that branch."""
    transactions: List[TXCreateItem] = []
    parent = _add_parent(provider, transactions, parent_type, **parent_overrides)
    kwargs = _charge_kwargs(_charge_type_for(parent_type), asset_id=FAKE_B)
    del kwargs["broker_id"]
    issues: List[BRIMValidationIssue] = []

    charge = _link(provider, transactions, parent, issues, **kwargs)

    assert issues == [], f"the free charge without broker_id is not lost as an issue; got {[(i.code, i.field) for i in issues]}"
    assert charge is not None and transactions[-1] is charge and len(transactions) == 2
    assert not charge.parent_ref, f"the charge stays free; got parent_ref {charge.parent_ref!r}"
    assert charge.broker_id == parent.broker_id == BROKER_ID
    assert charge.asset_id == FAKE_B, "the rest of the plugin's values are kept"
    assert parent.ref is None, f"no link, no name; got {parent.ref!r}"


# ─── _create_linked_charge: programming errors and invalid items ──────────────────────────────────────────────────────


@pytest.mark.parametrize("charge_type", [TransactionType.BUY, TransactionType.DIVIDEND, TransactionType.ADJUSTMENT], ids=lambda t: t.value)
def test_charge_type_other_than_fee_or_tax_raises(provider, charge_type):
    """The charge's type is fixed by the plugin's code, not by the file: a wrong one is a ValueError the plugin test finds."""
    transactions: List[TXCreateItem] = []
    buy = _add_parent(provider, transactions, TransactionType.BUY)

    with pytest.raises(ValueError):
        _link(provider, transactions, buy, **_charge_kwargs(charge_type))

    assert transactions == [buy], "nothing is appended"


def test_invalid_item_is_an_issue_and_none(provider):
    """A FEE with a positive amount: the issues ``_create_transaction`` gives for the same row, and ``None``."""
    transactions: List[TXCreateItem] = []
    buy = _add_parent(provider, transactions, TransactionType.BUY)
    wrong = _charge_kwargs(cash=Currency(code="EUR", amount=Decimal("2.50")))
    expected: List[BRIMValidationIssue] = []
    assert provider._create_transaction(row_num=99, transactions=[], validation_issues=expected, context="charge row", **{**wrong, "asset_id": FAKE_A}) is None
    assert expected, "premise: _create_transaction refuses the row"
    issues: List[BRIMValidationIssue] = []

    charge = _link(provider, transactions, buy, issues, **wrong)

    assert charge is None
    assert transactions == [buy], "nothing is appended"
    assert [(i.row, i.code, i.context) for i in issues] == [(i.row, i.code, i.context) for i in expected]


@pytest.mark.parametrize("helper", ["_create_linked_charge", "_ensure_ref"])
def test_parent_not_in_transactions_raises(provider, helper):
    """Coordinator's decision (P1a, answer 3c): a parent that is not in ``transactions`` — by identity: an equal copy of
    a row of the list is not that row — is a programming error of the plugin, a ValueError from both helpers."""
    transactions: List[TXCreateItem] = []
    buy = _add_parent(provider, transactions, TransactionType.BUY)
    stray = buy.model_copy()
    assert stray == buy and stray is not buy, "premise: equal by value, not the row of the list"

    with pytest.raises(ValueError):
        if helper == "_create_linked_charge":
            _link(provider, transactions, stray, **_charge_kwargs())
        else:
            provider._ensure_ref(stray, transactions)

    assert transactions == [buy] and transactions[0] is buy, "nothing is appended"
    assert (buy.ref, stray.ref) == (None, None), "nothing is named"


# ─── _ensure_ref ──────────────────────────────────────────────────────────────────────────────────────────────────────


def _three_buys(provider: BRIMProvider) -> List[TXCreateItem]:
    transactions: List[TXCreateItem] = []
    for quantity in ("1", "2", "3"):
        _add_parent(provider, transactions, TransactionType.BUY, quantity=Decimal(quantity))
    return transactions


class TestEnsureRef:
    def test_unique_names_over_three_parents(self, provider):
        transactions = _three_buys(provider)

        names = [provider._ensure_ref(tx, transactions) for tx in transactions]

        assert names == ["r1", "r2", "r3"]
        assert [tx.ref for tx in transactions] == names, "the name is written on the parent object"

    def test_equal_trades_get_different_names(self, provider):
        """Two equal trades of one day are equal for pydantic: the position is found by identity, never by value."""
        transactions: List[TXCreateItem] = []
        first = _add_parent(provider, transactions, TransactionType.BUY)
        second = _add_parent(provider, transactions, TransactionType.BUY)
        assert first == second and first is not second, "premise: equal by value, two objects"

        name = provider._ensure_ref(second, transactions)

        assert name == "r2"
        assert first.ref is None, "the first trade is not touched"
        assert provider._ensure_ref(first, transactions) == "r1"

    def test_collision_with_an_existing_name_takes_a_suffix(self, provider):
        transactions = _three_buys(provider)
        transactions[0].ref = "r2"  # a plugin that named a row itself, or joined two sub-parsers
        transactions[2].ref = "r2-2"

        name = provider._ensure_ref(transactions[1], transactions)

        assert name == "r2-3"
        assert transactions[1].ref == "r2-3"
        assert charge_link_structure_problems(transactions) == []

    def test_existing_name_is_returned_and_kept(self, provider):
        transactions = _three_buys(provider)
        transactions[1].ref = "mine"

        assert provider._ensure_ref(transactions[1], transactions) == "mine"
        assert transactions[1].ref == "mine"

    def test_idempotent(self, provider):
        transactions = _three_buys(provider)

        first = provider._ensure_ref(transactions[2], transactions)
        again = provider._ensure_ref(transactions[2], transactions)

        assert first == again == transactions[2].ref == "r3"
        assert [tx.ref for tx in transactions] == [None, None, "r3"]

    def test_deterministic_across_two_runs(self, provider):
        """The same input gives the same names, as ``link_uuid`` does: two parses compare without luck."""
        runs = []
        for _ in range(2):
            transactions = _three_buys(FakeBroker())
            FakeBroker()._ensure_ref(transactions[2], transactions)
            FakeBroker()._ensure_ref(transactions[0], transactions)
            runs.append([tx.ref for tx in transactions])

        assert runs[0] == runs[1] == ["r1", None, "r3"]

    def test_name_fits_the_field(self, provider):
        transactions: List[TXCreateItem] = []
        for index in range(12):
            _add_parent(provider, transactions, TransactionType.BUY, quantity=Decimal(index + 1))
        transactions[0].ref = "r12"
        transactions[1].ref = "r12-2"

        name = provider._ensure_ref(transactions[11], transactions)

        assert name == "r12-3" and len(name) <= REF_MAX_LENGTH


# ─── the structural check on fake plugins (§3, §6.2) ──────────────────────────────────────────────────────────────────


def _buy_item(**overrides) -> TXCreateItem:
    return TXCreateItem(**_parent_kwargs(TransactionType.BUY, **overrides))


def _fee_item(**overrides) -> TXCreateItem:
    return TXCreateItem(**_charge_kwargs(**{"asset_id": FAKE_A, **overrides}))


class OrphanLinkBroker(FakeBroker):
    """A plugin that writes a ``parent_ref`` by hand and gets it wrong: no row of its output is named ``r9``."""

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        return BRIMParseOutput(transactions=[_buy_item(ref="r1"), _fee_item(parent_ref="r9")])


class HelperLinkBroker(FakeBroker):
    """A plugin that links its fee through the helper, as P2–P6 will."""

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        transactions: List[TXCreateItem] = []
        issues: List[BRIMValidationIssue] = []
        buy = self._create_transaction(row_num=1, transactions=transactions, validation_issues=issues, **_parent_kwargs(TransactionType.BUY, broker_id=broker_id))
        self._create_linked_charge(2, transactions, issues, buy, **_charge_kwargs(broker_id=broker_id, description="Commission ACME"))
        return BRIMParseOutput(transactions=transactions, validation_issues=issues)


class TestStructureCheck:
    """The checker the common plugin test runs: a red where a link is broken, silence where none is."""

    def test_orphan_parent_ref_of_a_fake_plugin_is_reported(self, tmp_path):
        """RED by design of the plugin: the common test must fail on it, so the checker must say why."""
        output = OrphanLinkBroker().parse(tmp_path / "orphan.csv", BROKER_ID)

        problems = charge_link_structure_problems(output.transactions)

        assert len(problems) == 1 and "'r9' names no ref" in problems[0], problems
        with pytest.raises(AssertionError, match="names no ref"):
            assert_charge_link_structure(output, "OrphanLinkBroker [orphan.csv]")

    def test_duplicate_ref_is_reported(self):
        rows = [_buy_item(ref="r1"), _buy_item(ref="r1", quantity=Decimal("2")), _fee_item(parent_ref="r1")]

        problems = charge_link_structure_problems(rows)

        assert len(problems) == 1 and "already given to row #0" in problems[0], problems

    def test_name_longer_than_the_field_is_reported(self):
        """The model refuses a name over 36 characters; a row built around validation (``model_copy``) is still caught."""
        long_name = "r" * (REF_MAX_LENGTH + 1)
        rows = [_buy_item().model_copy(update={"ref": long_name}), _fee_item().model_copy(update={"parent_ref": long_name})]

        problems = charge_link_structure_problems(rows)

        assert sum("longer than" in problem for problem in problems) == 2, problems

    def test_output_without_links_has_no_problem(self):
        assert charge_link_structure_problems([_buy_item(), _fee_item(), _buy_item(ref="lonely")]) == []

    def test_output_of_the_helper_is_well_formed(self, tmp_path):
        output = HelperLinkBroker().parse(tmp_path / "linked.csv", BROKER_ID)

        assert output.validation_issues == []
        assert [tx.type for tx in output.transactions] == [TransactionType.BUY, TransactionType.FEE]
        assert output.transactions[1].parent_ref == output.transactions[0].ref
        assert_charge_link_structure(output, "HelperLinkBroker [linked.csv]")


# ─── the reimport criterion (§6.3) ────────────────────────────────────────────────────────────────────────────────────


class PreviousVersionBroker(FakeBroker):
    """The plugin before it linked: a BUY and its commission, the FEE with no asset and no link."""

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        transactions: List[TXCreateItem] = []
        issues: List[BRIMValidationIssue] = []
        self._create_transaction(row_num=1, transactions=transactions, validation_issues=issues, **_parent_kwargs(TransactionType.BUY, broker_id=broker_id))
        self._create_transaction(row_num=2, transactions=transactions, validation_issues=issues, **_charge_kwargs(broker_id=broker_id, description="Commission ACME"))
        return BRIMParseOutput(transactions=transactions, validation_issues=issues)


class BuyOnlyBroker(FakeBroker):
    """A version that did not import the commission at all: the reimport by the linking version adds the fee."""

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        transactions: List[TXCreateItem] = []
        self._create_transaction(row_num=1, transactions=transactions, validation_issues=[], **_parent_kwargs(TransactionType.BUY, broker_id=broker_id))
        return BRIMParseOutput(transactions=transactions)


async def _reimport(tmp_path: Path, previous: Callable[[], FakeBroker], current: FakeBroker) -> BRIMParseOutput:
    sample = tmp_path / "fake-broker.csv"
    sample.write_text("fake broker export\n", encoding="utf-8")
    async with private_broker() as (session, broker_id):
        previous_rows = previous().parse(sample, broker_id).transactions
        return await assert_reimport_adds_nothing(previous_rows, current, sample, broker_id, session)


@pytest.mark.asyncio
class TestReimportAddsNothing:
    async def test_same_version_adds_nothing(self, tmp_path):
        """Guard of the helper, green today: the previous rows reimported by the same version are all duplicates."""
        output = await _reimport(tmp_path, PreviousVersionBroker, PreviousVersionBroker())

        assert len(output.transactions) == 2

    async def test_helper_reports_a_row_it_would_add(self, tmp_path):
        """Guard of the helper, green today: the criterion is not vacuous, a fee the previous version never had is new."""
        with pytest.raises(AssertionError, match=r"adds 1 of 2 row\(s\)"):
            await _reimport(tmp_path, BuyOnlyBroker, PreviousVersionBroker())

    async def test_fee_taking_the_parents_asset_adds_nothing(self, tmp_path):
        """The case at risk of P1a: the linked FEE now carries the BUY's asset and ``parent_ref``; the stored FEE has
        neither. It must still be found (the ``asset_id IS NULL`` branch of the duplicate search), so nothing is added."""
        current = HelperLinkBroker()
        premise = current.parse(tmp_path / "premise.csv", BROKER_ID)
        assert premise.validation_issues == [] and len(premise.transactions) == 2, f"premise: the linking version gives the same two rows; {premise}"
        buy, fee = premise.transactions
        assert (fee.type, fee.asset_id, fee.parent_ref) == (TransactionType.FEE, buy.asset_id, buy.ref) and buy.ref, "premise: the FEE is linked and carries the parent's asset"

        output = await _reimport(tmp_path, PreviousVersionBroker, current)

        assert [tx.type for tx in output.transactions] == [TransactionType.BUY, TransactionType.FEE]


# ─── the helpers of the wave P2b (brim_charge_links.py) ───────────────────────────────────────────────────────────────


def _fee_row(**overrides) -> TXCreateItem:
    """A free FEE of 2.50 EUR on ``DAY``, no asset: the shape of an account's connection fee."""
    return TXCreateItem(**{**_charge_kwargs(asset_id=None, cash=Currency(code="EUR", amount=Decimal("-2.50"))), **overrides})


FEE_KEY = ("FEE", DAY.isoformat(), "-2.50", "EUR", None)


class TestIdenticalFreeCharges:
    """``free`` lists a key once per row: identical free charges (the four connection fees of one day of a DEGIRO
    statement) are declared without a position."""

    def test_a_key_listed_once_per_row_matches(self):
        output = BRIMParseOutput(transactions=[_fee_row(), _fee_row()])

        assert charge_link_expectation_problems(output, linked=[], free=[FEE_KEY, FEE_KEY]) == []

    def test_a_key_listed_fewer_times_than_its_rows_is_reported(self):
        output = BRIMParseOutput(transactions=[_fee_row(), _fee_row()])

        problems = charge_link_expectation_problems(output, linked=[], free=[FEE_KEY])
        assert any("2 rows match" in problem and "1 time(s)" in problem for problem in problems), problems

    def test_one_of_the_identical_rows_naming_a_parent_is_reported(self):
        parent = TXCreateItem(**_parent_kwargs(TransactionType.BUY, ref="r1"))
        output = BRIMParseOutput(transactions=[parent, _fee_row(), _fee_row(parent_ref="r1")])

        problems = charge_link_expectation_problems(output, linked=[], free=[FEE_KEY, FEE_KEY])
        assert any("should stay free" in problem for problem in problems), problems


class TestReportSetSnapshot:
    """A report-set plugin (Crédit Agricole) is captured on a set of samples: combined by the plugin, written by the core,
    parsed; each member listed with its sha256. The file names keep the extension of a non-CSV member."""

    SET = "credit_agricole-securities.csv+credit_agricole-account.xlsx"

    @staticmethod
    def _plugin() -> BRIMProvider:
        BRIMProviderRegistry.auto_discover()
        plugin = BRIMProviderRegistry.get_provider_instance("broker_credit_agricole")
        assert plugin is not None and plugin.is_report_set_plugin, "presence barrier: the Crédit Agricole report-set plugin"
        return plugin

    @pytest.mark.parametrize(
        ("sample", "stem"),
        [
            ("fineco-export.csv", "fineco-export"),
            ("credit_agricole-conti.xlsx", "credit_agricole-conti.xlsx"),
            ("credit_agricole-securities.csv+credit_agricole-account.xlsx", "credit_agricole-securities+credit_agricole-account.xlsx"),
        ],
    )
    def test_the_snapshot_file_name(self, sample: str, stem: str):
        assert previous_output_path("broker_x", sample).name == f"{stem}.json"

    def test_a_set_is_captured_and_loaded_back(self, tmp_path, monkeypatch):
        plugin = self._plugin()
        snapshot = capture_previous_set_output(plugin, self.SET, source_head="0000000", allow_links=True)
        assert [member["sample"].rsplit("/", 1)[-1] for member in snapshot["members"]] == self.SET.split("+")
        assert all(len(member["sample_sha256"]) == 64 for member in snapshot["members"])

        monkeypatch.setattr(brim_charge_links, "PREVIOUS_OUTPUTS_DIR", tmp_path)
        target = previous_output_path(plugin.provider_code, self.SET)
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(snapshot), encoding="utf-8")
        loaded = load_previous_snapshot(plugin.provider_code, self.SET, BROKER_ID)

        fresh = plugin.parse(sample_input(plugin, self.SET, tmp_path / "combined"), BROKER_ID)
        assert loaded.transactions == fresh.transactions, "the loaded rows are the parse of the combined set, on the test's broker"

    def test_a_member_that_changed_fails_the_load(self, tmp_path, monkeypatch):
        plugin = self._plugin()
        snapshot = capture_previous_set_output(plugin, self.SET, source_head="0000000", allow_links=True)
        snapshot["members"][1]["sample_sha256"] = "0" * 64

        monkeypatch.setattr(brim_charge_links, "PREVIOUS_OUTPUTS_DIR", tmp_path)
        target = previous_output_path(plugin.provider_code, self.SET)
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(snapshot), encoding="utf-8")
        with pytest.raises(AssertionError, match="changed after the snapshot was taken"):
            load_previous_snapshot(plugin.provider_code, self.SET, BROKER_ID)


# ─── _link_existing_charge: a charge already in the output linked afterwards (wave P2b) ───────────────────────────────


def _add_charge(provider: BRIMProvider, transactions: List[TXCreateItem], tx_type: TransactionType = TransactionType.FEE, **overrides) -> TXCreateItem:
    """A free charge created as a plugin creates it before it knows its parent, its validity checked (the premise)."""
    issues: List[BRIMValidationIssue] = []
    row = provider._create_transaction(row_num=len(transactions) + 1, transactions=transactions, validation_issues=issues, **_charge_kwargs(tx_type, **overrides))
    assert row is not None and issues == [], f"premise: a valid free {tx_type.value}; issues {issues}"
    assert not row.parent_ref, "premise: the charge starts free"
    return row


class TestLinkExistingChargeValid:
    """Guards of P2b, green at once: a valid link names the parent, gives the charge its ``parent_ref`` and broker."""

    def test_charge_before_its_parent_names_the_parent_by_position(self, provider):
        """The degiro shape: the charge comes first in the output, the parent after; the output order is kept."""
        transactions: List[TXCreateItem] = []
        fee = _add_charge(provider, transactions, asset_id=FAKE_A)
        buy = _add_parent(provider, transactions, TransactionType.BUY)
        assert buy.ref is None, "premise: the parent has no name"

        linked = provider._link_existing_charge(fee, buy, transactions, row_num=1)

        assert linked is True
        assert buy.ref == "r2", f"the parent is named by its position in the output; got {buy.ref!r}"
        assert fee.parent_ref == "r2"
        assert fee.parent_transaction_id is None, "a parent of the same file is named by ref, never by id"
        assert transactions == [fee, buy] and transactions[0] is fee and transactions[1] is buy, "nothing is moved or appended"
        assert (fee.cash, fee.date, fee.description) == (Currency(code="EUR", amount=Decimal("-2.50")), DAY, "FEE charge"), "the charge keeps its own amount, date and text"
        assert charge_link_structure_problems(transactions) == []

    def test_parent_named_by_the_plugin_keeps_its_name(self, provider):
        transactions: List[TXCreateItem] = []
        buy = _add_parent(provider, transactions, TransactionType.BUY, ref="order-42")
        fee = _add_charge(provider, transactions)

        assert provider._link_existing_charge(fee, buy, transactions) is True

        assert buy.ref == "order-42"
        assert fee.parent_ref == "order-42"

    def test_charge_takes_the_parents_broker(self, provider):
        """Rule 2: the broker is always the parent's, as with ``_create_linked_charge``."""
        transactions: List[TXCreateItem] = []
        buy = _add_parent(provider, transactions, TransactionType.BUY)
        fee = _add_charge(provider, transactions, broker_id=BROKER_ID + 1)
        assert fee.broker_id == BROKER_ID + 1, "premise: the charge was created on another broker"

        assert provider._link_existing_charge(fee, buy, transactions) is True

        assert fee.broker_id == BROKER_ID
        assert fee.parent_ref == buy.ref and buy.ref

    def test_two_charges_share_the_parent_named_once(self, provider):
        transactions: List[TXCreateItem] = []
        buy = _add_parent(provider, transactions, TransactionType.BUY)
        fee = _add_charge(provider, transactions)
        tax = _add_charge(provider, transactions, TransactionType.TAX, cash=Currency(code="EUR", amount=Decimal("-0.20")))

        assert provider._link_existing_charge(fee, buy, transactions) is True
        name_after_first = buy.ref
        assert provider._link_existing_charge(tax, buy, transactions) is True

        assert name_after_first == buy.ref == "r1"
        assert fee.parent_ref == tax.parent_ref == "r1"
        assert charge_link_structure_problems(transactions) == []


#: (charge's own asset, parent type, expected asset after the link). Only the cases that link: the refused ones are below.
EXISTING_ASSET_RULE = [
    pytest.param(None, TransactionType.BUY, FAKE_A, id="none-under-Y-takes-Y"),
    pytest.param(FAKE_A, TransactionType.BUY, FAKE_A, id="Y-under-Y-keeps-Y"),
    pytest.param(None, TransactionType.DEPOSIT, None, id="none-under-no-asset-stays-without"),
]


@pytest.mark.parametrize(("own_asset", "parent_type", "expected_asset"), EXISTING_ASSET_RULE)
def test_link_existing_fills_the_asset_only_when_missing(provider, own_asset, parent_type, expected_asset):
    """Contract §9: a charge without an asset takes the parent's; one with the parent's asset keeps it."""
    transactions: List[TXCreateItem] = []
    parent = _add_parent(provider, transactions, parent_type)
    fee = _add_charge(provider, transactions, asset_id=own_asset)

    assert provider._link_existing_charge(fee, parent, transactions) is True

    assert fee.asset_id == expected_asset, f"asset {expected_asset} expected; got {fee.asset_id}"
    assert fee.parent_ref == parent.ref and parent.ref


#: The links the rules refuse: (parent type, parent overrides, charge type, charge overrides).
REFUSED_EXISTING = [
    pytest.param(TransactionType.SELL, {}, TransactionType.FEE, {"asset_id": FAKE_B}, id="charge-with-another-asset"),
    pytest.param(TransactionType.DEPOSIT, {}, TransactionType.FEE, {"asset_id": FAKE_B}, id="charge-with-asset-under-no-asset"),
    pytest.param(TransactionType.DEPOSIT, {"link_uuid": PAIR_UUID}, TransactionType.FEE, {}, id="parent-pair-leg"),
    pytest.param(TransactionType.FEE, {}, TransactionType.TAX, {"asset_id": FAKE_A}, id="tax-on-a-fee"),
    pytest.param(TransactionType.BUY, {}, TransactionType.FEE, {"asset_id": FAKE_A, "link_uuid": PAIR_UUID}, id="charge-pair-leg"),
    pytest.param(TransactionType.ADJUSTMENT, {}, TransactionType.FEE, {"asset_id": FAKE_A}, id="parent-adjustment"),
    pytest.param(TransactionType.CASH_TRANSFER, {}, TransactionType.FEE, {}, id="parent-cash-transfer"),
]


@pytest.mark.parametrize(("parent_type", "parent_overrides", "charge_type", "charge_overrides"), REFUSED_EXISTING)
def test_link_existing_refused_leaves_everything_untouched(provider, parent_type, parent_overrides, charge_type, charge_overrides):
    """D10: a refused link is no error. ``False``, the charge byte for byte as it was, the parent unnamed."""
    transactions: List[TXCreateItem] = []
    parent = _add_parent(provider, transactions, parent_type, **parent_overrides)
    charge = _add_charge(provider, transactions, charge_type, **charge_overrides)
    charge_before, parent_before = charge.model_dump(), parent.model_dump()

    linked = provider._link_existing_charge(charge, parent, transactions, row_num=2)

    assert linked is False
    assert charge.model_dump() == charge_before, "a refused link changes nothing on the charge"
    assert parent.model_dump() == parent_before, "nor on the parent"
    assert parent.ref is None, f"no link, no name; got {parent.ref!r}"
    assert transactions == [parent, charge] and transactions[0] is parent and transactions[1] is charge
    assert charge_link_structure_problems(transactions) == []


# ─── _link_existing_charge: programming errors ────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("charge_type", [TransactionType.BUY, TransactionType.DEPOSIT], ids=lambda t: t.value)
def test_link_existing_non_charge_raises(provider, charge_type):
    transactions: List[TXCreateItem] = []
    parent = _add_parent(provider, transactions, TransactionType.BUY)
    other = _add_parent(provider, transactions, charge_type)
    before = [tx.model_dump() for tx in transactions]

    with pytest.raises(ValueError):
        provider._link_existing_charge(other, parent, transactions)

    assert [tx.model_dump() for tx in transactions] == before, "nothing is changed"


@pytest.mark.parametrize("stray_role", ["charge", "parent"])
def test_link_existing_row_not_in_transactions_raises(provider, stray_role):
    """By identity: an equal copy of a row of the list is not that row."""
    transactions: List[TXCreateItem] = []
    buy = _add_parent(provider, transactions, TransactionType.BUY)
    fee = _add_charge(provider, transactions)
    stray = (fee if stray_role == "charge" else buy).model_copy()
    assert stray == (fee if stray_role == "charge" else buy), "premise: equal by value, not the row of the list"
    before = [tx.model_dump() for tx in transactions]

    with pytest.raises(ValueError):
        if stray_role == "charge":
            provider._link_existing_charge(stray, buy, transactions)
        else:
            provider._link_existing_charge(fee, stray, transactions)

    assert [tx.model_dump() for tx in transactions] == before, "nothing is changed, nothing is named"
    assert (stray.ref, stray.parent_ref) == (None, None)


# ─── parity: _link_existing_charge and _create_linked_charge give the same verdict and the same charge ────────────────

PARITY = [
    pytest.param(TransactionType.BUY, {}, TransactionType.FEE, {}, True, id="fee-without-asset-under-buy"),
    pytest.param(TransactionType.BUY, {}, TransactionType.FEE, {"asset_id": FAKE_A, "broker_id": BROKER_ID + 1}, True, id="fee-other-broker-under-buy"),
    pytest.param(TransactionType.DEPOSIT, {}, TransactionType.TAX, {}, True, id="tax-under-deposit"),
    pytest.param(TransactionType.SELL, {}, TransactionType.FEE, {"asset_id": FAKE_B}, False, id="fee-another-asset"),
    pytest.param(TransactionType.DEPOSIT, {"link_uuid": PAIR_UUID}, TransactionType.FEE, {}, False, id="parent-pair-leg"),
    pytest.param(TransactionType.FEE, {}, TransactionType.TAX, {"asset_id": FAKE_A}, False, id="tax-on-a-fee"),
    pytest.param(TransactionType.ADJUSTMENT, {}, TransactionType.FEE, {"asset_id": FAKE_A}, False, id="parent-adjustment"),
]


@pytest.mark.parametrize(("parent_type", "parent_overrides", "charge_type", "charge_overrides", "linked"), PARITY)
def test_link_existing_matches_create_linked(provider, parent_type, parent_overrides, charge_type, charge_overrides, linked):
    """The two helpers share one check (``_charge_link_check``): for the same inputs, the same verdict, the same charge
    and the same parent name. Each runs on its own output, parent first, charge second."""
    created_out: List[TXCreateItem] = []
    created_parent = _add_parent(provider, created_out, parent_type, **parent_overrides)
    created = _link(provider, created_out, created_parent, **_charge_kwargs(charge_type, **charge_overrides))
    assert created is not None, "premise: _create_linked_charge creates the charge"

    existing_out: List[TXCreateItem] = []
    existing_parent = _add_parent(provider, existing_out, parent_type, **parent_overrides)
    existing = _add_charge(provider, existing_out, charge_type, **charge_overrides)

    verdict = provider._link_existing_charge(existing, existing_parent, existing_out)

    assert verdict is linked and bool(created.parent_ref) is linked, f"verdicts: existing {verdict}, created {bool(created.parent_ref)}, expected {linked}"
    assert existing.model_dump() == created.model_dump(), "the same resulting charge"
    assert existing_parent.ref == created_parent.ref


# ─── _create_charge_of: the same-row pattern of P4 (a parent, or None when the plugin's parent was refused) ──────────


def _charge_of(provider: BRIMProvider, transactions: List[TXCreateItem], parent: Optional[TXCreateItem], issues: List[BRIMValidationIssue], **kwargs) -> Optional[TXCreateItem]:
    """``_create_charge_of`` called as a plugin calls it: the return of the parent's ``_create_transaction``, the charge's
    fields as kwargs."""
    return provider._create_charge_of(parent, 99, transactions, issues, context="charge row", **kwargs)


def _issue_view(issues: List[BRIMValidationIssue]) -> List[tuple]:
    return [(i.row, i.code, i.field, i.context) for i in issues]


#: Charges with no parent to name: (charge type, overrides). The last one has no broker: refused, as by ``_create_transaction``.
WITHOUT_PARENT = [
    pytest.param(TransactionType.FEE, {"asset_id": FAKE_A}, id="fee-with-asset"),
    pytest.param(TransactionType.TAX, {}, id="tax-without-asset"),
    pytest.param(TransactionType.FEE, {"broker_id": None}, id="fee-without-broker"),
]


@pytest.mark.parametrize(("charge_type", "charge_overrides"), WITHOUT_PARENT)
def test_charge_of_without_parent_is_create_transaction(provider, charge_type, charge_overrides):
    """Guard of P4: parent ``None`` (the plugin's booking was refused) → exactly ``_create_transaction`` with the same
    kwargs: the same row or ``None``, the same issues, free. A booking of an earlier row, in the output just before, is
    never named nor used."""
    kwargs = _charge_kwargs(charge_type, **charge_overrides)
    expected_out: List[TXCreateItem] = []
    expected_issues: List[BRIMValidationIssue] = []
    expected = provider._create_transaction(99, expected_out, expected_issues, context="charge row", **kwargs)

    transactions: List[TXCreateItem] = []
    earlier = _add_parent(provider, transactions, TransactionType.BUY)
    issues: List[BRIMValidationIssue] = []

    charge = _charge_of(provider, transactions, None, issues, **kwargs)

    assert _issue_view(issues) == _issue_view(expected_issues)
    if expected is None:
        assert charge is None and transactions == [earlier], "refused as by _create_transaction: nothing appended"
    else:
        assert charge is not None and transactions[-1] is charge and len(transactions) == 2
        assert charge.model_dump() == expected.model_dump(), "the same row _create_transaction gives"
        assert charge.parent_ref is None
    assert earlier.ref is None, f"the earlier booking is not named: got {earlier.ref!r}"


#: (parent type, parent overrides, charge type, charge overrides): valid links and refused ones alike.
CHARGE_OF_PARITY = [
    pytest.param(TransactionType.BUY, {}, TransactionType.FEE, {}, id="fee-without-asset-under-buy"),
    pytest.param(TransactionType.BUY, {}, TransactionType.FEE, {"asset_id": FAKE_A, "broker_id": BROKER_ID + 1}, id="fee-other-broker-under-buy"),
    pytest.param(TransactionType.SELL, {}, TransactionType.TAX, {"asset_id": FAKE_A}, id="tax-under-sell"),
    pytest.param(TransactionType.DEPOSIT, {}, TransactionType.TAX, {}, id="tax-under-deposit"),
    pytest.param(TransactionType.SELL, {}, TransactionType.FEE, {"asset_id": FAKE_B}, id="fee-another-asset"),
    pytest.param(TransactionType.ADJUSTMENT, {}, TransactionType.FEE, {"asset_id": FAKE_A}, id="parent-adjustment"),
    pytest.param(TransactionType.DEPOSIT, {"link_uuid": PAIR_UUID}, TransactionType.FEE, {}, id="parent-pair-leg"),
]


@pytest.mark.parametrize(("parent_type", "parent_overrides", "charge_type", "charge_overrides"), CHARGE_OF_PARITY)
def test_charge_of_with_a_parent_is_create_linked_charge(provider, parent_type, parent_overrides, charge_type, charge_overrides):
    """Guard of P4: a parent given → exactly ``_create_linked_charge`` with the same arguments, each on its own output:
    the same charge, the same issues, the same parent name, the same rows."""
    linked_out: List[TXCreateItem] = []
    linked_parent = _add_parent(provider, linked_out, parent_type, **parent_overrides)
    linked_issues: List[BRIMValidationIssue] = []
    expected = _link(provider, linked_out, linked_parent, linked_issues, **_charge_kwargs(charge_type, **charge_overrides))
    assert expected is not None, "premise: _create_linked_charge creates the charge"

    transactions: List[TXCreateItem] = []
    parent = _add_parent(provider, transactions, parent_type, **parent_overrides)
    issues: List[BRIMValidationIssue] = []

    charge = _charge_of(provider, transactions, parent, issues, **_charge_kwargs(charge_type, **charge_overrides))

    assert charge is not None and transactions == [parent, charge] and transactions[1] is charge
    assert charge.model_dump() == expected.model_dump(), "the same charge _create_linked_charge gives"
    assert parent.ref == linked_parent.ref, f"the same parent name: {parent.ref!r} vs {linked_parent.ref!r}"
    assert _issue_view(issues) == _issue_view(linked_issues)
    assert charge_link_structure_problems(transactions) == []


def test_charge_of_a_valid_parent_names_it(provider):
    """Guard of P4, the link itself: a FEE without an asset under a BUY names the BUY and takes its asset and broker."""
    transactions: List[TXCreateItem] = []
    buy = _add_parent(provider, transactions, TransactionType.BUY)
    issues: List[BRIMValidationIssue] = []

    fee = _charge_of(provider, transactions, buy, issues, **_charge_kwargs())

    assert issues == [] and fee is not None
    assert buy.ref and fee.parent_ref == buy.ref
    assert (fee.asset_id, fee.broker_id) == (buy.asset_id, buy.broker_id) == (FAKE_A, BROKER_ID)


@pytest.mark.parametrize(("parent_type", "parent_overrides"), INVALID_PARENTS)
def test_charge_of_an_invalid_parent_is_free_and_leaves_it_unnamed(provider, parent_type, parent_overrides):
    """Guard of P4 (D10): a parent that cannot be one — an ADJUSTMENT, a CASH_TRANSFER, a leg of a pair, a FEE under a
    TAX — gives a charge created free, with the plugin's own values and no issue; the parent gets no name."""
    transactions: List[TXCreateItem] = []
    parent = _add_parent(provider, transactions, parent_type, **parent_overrides)
    charge_type = _charge_type_for(parent_type)
    issues: List[BRIMValidationIssue] = []

    charge = _charge_of(provider, transactions, parent, issues, **_charge_kwargs(charge_type, asset_id=FAKE_B))

    assert charge is not None and issues == [], f"created, no issue; issues {issues}"
    assert transactions == [parent, charge] and transactions[1] is charge
    assert not charge.parent_ref and charge.parent_transaction_id is None
    assert (charge.type, charge.broker_id, charge.asset_id) == (charge_type, BROKER_ID, FAKE_B), "the plugin's own values"
    assert parent.ref is None, f"no link, no name: got {parent.ref!r}"


@pytest.mark.parametrize("with_parent", [False, True], ids=["parent-none", "parent-buy"])
def test_charge_of_a_refused_charge_is_none_and_an_issue(provider, with_parent):
    """Guard of P4: a charge the validation refuses (a FEE with a positive amount) → ``None``, nothing appended, and the
    issues ``_create_transaction`` records for the same row — with a parent or without one."""
    wrong = _charge_kwargs(cash=Currency(code="EUR", amount=Decimal("2.50")))
    expected_issues: List[BRIMValidationIssue] = []
    assert provider._create_transaction(99, [], expected_issues, context="charge row", **{**wrong, "asset_id": FAKE_A}) is None
    assert expected_issues, "premise: _create_transaction refuses the row"
    transactions: List[TXCreateItem] = []
    buy = _add_parent(provider, transactions, TransactionType.BUY)
    issues: List[BRIMValidationIssue] = []

    charge = _charge_of(provider, transactions, buy if with_parent else None, issues, **wrong)

    assert charge is None
    assert transactions == [buy], "nothing is appended"
    assert _issue_view(issues) == _issue_view(expected_issues)
