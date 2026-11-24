"""
Asset type rules (lane 65, lot B1): ``backend/app/services/assets/type_rules.py``.

The family of an asset type and the INDEX rule live in one pure module. Pure: no database, no server.

(a) Every ``AssetType`` member has a family, and that family is itself a member.
(b) The rule: ``ETF_*`` -> ``ETF``, ``CROWDFUND_*`` -> ``CROWDFUND``, every other type is its own family.
(c) The examples of the plan: ETF -> ETF_STOCK no warning; CROWDFUND_REAL_ESTATE -> ETF_STOCK and STOCK -> BOND warn;
    a type change to INDEX warns without transactions and blocks with them (the blocked asset gets no warning).
(d) Only INDEX forbids transactions.
(e) Lane 80, lot ALF-B1b: ``asset_type_content`` — what a type holds, the class the «Allocazione» tab filters by — is the
    frontend's ``PRIMARY_TYPE_MAP`` (``frontend/src/lib/utils/assetTypes.ts``, read as text: the map is parsed, never
    copied here); ``ETF_MONETARY``, the generic ``ETF``, the replay's «Unknown» and any other value are their own.
"""

import re
from pathlib import Path

import pytest

from backend.app.db.models import AssetType
from backend.app.services.assets import type_rules
from backend.app.services.assets.type_rules import (
    TypeChangeVerdict,
    asset_type_content,
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


# ----------------------------------------------------------------------------
# (e) The content of a type, against the frontend's map (lane 80, ALF-B1b)
# ----------------------------------------------------------------------------

#: The frontend module that holds ``PRIMARY_TYPE_MAP``, the content view of a type.
ASSET_TYPES_TS = Path(__file__).resolve().parents[3] / "frontend" / "src" / "lib" / "utils" / "assetTypes.ts"

#: The expected content of every subtype, written here so that an empty or partial map turns the test red.
EXPECTED_CONTENT = {
    "ETF_STOCK": "STOCK",
    "ETF_BOND": "BOND",
    "ETF_COMMODITY": "COMMODITY",
    "ETF_REAL_ESTATE": "REAL_ESTATE",
    "ETF_CRYPTO": "CRYPTO",
    "CROWDFUND_REAL_ESTATE": "REAL_ESTATE",
}


def _frontend_primary_type_map() -> dict[str, str]:
    """``PRIMARY_TYPE_MAP``'s entries, parsed from the TypeScript source."""
    source = ASSET_TYPES_TS.read_text(encoding="utf-8")
    block = re.search(r"const PRIMARY_TYPE_MAP: Record<string, string> = \{(?P<body>[^}]*)\};", source)
    assert block is not None, f"PRIMARY_TYPE_MAP not found in {ASSET_TYPES_TS}"
    entries = dict(re.findall(r"^\s*([A-Z_]+):\s*'([A-Z_]+)',?\s*$", block.group("body"), flags=re.MULTILINE))
    assert entries, "precondition: the map has entries"
    return entries


def test_content_is_the_frontend_map():
    frontend = _frontend_primary_type_map()
    assert frontend == EXPECTED_CONTENT, "the frontend map changed: update EXPECTED_CONTENT and type_rules together"
    assert set(frontend) | set(frontend.values()) <= {member.value for member in AssetType}, "every key and value is an AssetType"


@pytest.mark.parametrize("asset_type", list(AssetType))
def test_every_member_has_the_frontends_content(asset_type):
    assert asset_type_content(asset_type.value) == _frontend_primary_type_map().get(asset_type.value, asset_type.value)


@pytest.mark.parametrize("value", ["ETF_MONETARY", "ETF", "STOCK", "Unknown", "NOT_A_TYPE"])
def test_a_type_without_a_subtype_holds_itself(value):
    """``ETF_MONETARY`` has no base type, ``ETF`` is the mixed residual, «Unknown» is the replay's name for an asset
    with no type: each is its own content, and no value raises."""
    assert asset_type_content(value) == value
