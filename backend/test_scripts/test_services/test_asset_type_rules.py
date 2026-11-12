"""
Asset type rules (lane 65, lot B1): ``backend/app/services/assets/type_rules.py``.

The family of an asset type and the INDEX rule live in one pure module. Pure: no database, no server.

(a) Every ``AssetType`` member has a family, and that family is itself a member.
(b) The rule: ``ETF_*`` -> ``ETF``, ``CROWDFUND_*`` -> ``CROWDFUND``, every other type is its own family.
(c) The examples of the plan: ETF -> ETF_STOCK no warning; CROWDFUND_REAL_ESTATE -> ETF_STOCK and STOCK -> BOND warn;
    a type change to INDEX warns without transactions and blocks with them (the blocked asset gets no warning).
(d) Only INDEX forbids transactions.
"""

import pytest

from backend.app.db.models import AssetType
from backend.app.services.assets import type_rules
from backend.app.services.assets.type_rules import (
    TypeChangeVerdict,
    asset_type_family,
    classify_type_change,
    family_changed,
    type_allows_transactions,
)


@pytest.mark.parametrize("asset_type", list(AssetType))
def test_every_member_has_a_family(asset_type):
    family = asset_type_family(asset_type)
    assert isinstance(family, AssetType)
    # a family is a base type: its own family
    assert asset_type_family(family) == family


def test_family_rule():
    for member in AssetType:
        if member.value.startswith("ETF_"):
            assert asset_type_family(member) == AssetType.ETF
        elif member.value.startswith("CROWDFUND_"):
            assert asset_type_family(member) == AssetType.CROWDFUND
        else:
            assert asset_type_family(member) == member


def test_family_accepts_plain_string():
    assert asset_type_family("ETF_BOND") == AssetType.ETF


def test_family_changed_examples():
    assert family_changed(AssetType.ETF, AssetType.ETF_STOCK) is False
    assert family_changed(AssetType.ETF_STOCK, AssetType.ETF_BOND) is False
    assert family_changed(AssetType.CROWDFUND_REAL_ESTATE, AssetType.ETF_STOCK) is True
    assert family_changed(AssetType.STOCK, AssetType.BOND) is True
    assert family_changed(AssetType.STOCK, AssetType.STOCK) is False


def test_classify_examples():
    c = classify_type_change
    assert c(AssetType.ETF, AssetType.ETF_STOCK, tx_count=0) == TypeChangeVerdict.OK
    assert c(AssetType.CROWDFUND_REAL_ESTATE, AssetType.ETF_STOCK, tx_count=3) == TypeChangeVerdict.FAMILY_WARNING
    assert c(AssetType.STOCK, AssetType.BOND, tx_count=0) == TypeChangeVerdict.FAMILY_WARNING
    assert c(AssetType.ETF, AssetType.INDEX, tx_count=0) == TypeChangeVerdict.FAMILY_WARNING
    # blocked: no warning on top
    assert c(AssetType.ETF, AssetType.INDEX, tx_count=2) == TypeChangeVerdict.INDEX_WITH_TRANSACTIONS


def test_classify_already_index_is_left_alone():
    """An INDEX that already has transactions is not touched: no clean-up, no block, no warning."""
    assert classify_type_change(AssetType.INDEX, AssetType.INDEX, tx_count=5) == TypeChangeVerdict.OK
    # leaving INDEX is a family change, never blocked
    assert classify_type_change(AssetType.INDEX, AssetType.STOCK, tx_count=5) == TypeChangeVerdict.FAMILY_WARNING


def test_only_index_forbids_transactions():
    for member in AssetType:
        assert type_allows_transactions(member) is (member != AssetType.INDEX)
    assert type_rules.INDEX_TRANSACTIONS_ERROR == "Cannot create transactions for INDEX assets"
