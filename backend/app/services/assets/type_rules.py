"""
Asset type rules: the family of a type and the INDEX rule, in one place.

Pure functions, no database. The bulk asset edit and the transaction batch import what they need from here, so the
rule is written once.

Family: ``ETF_*`` -> ``ETF``, ``CROWDFUND_*`` -> ``CROWDFUND``, every other type is its own family.
INDEX: transactions are forbidden for an asset of that type, and an asset that has transactions cannot become one.
"""

from __future__ import annotations

from enum import StrEnum

from backend.app.db.models import AssetType

#: Message of the error raised when a transaction is created for an INDEX asset.
INDEX_TRANSACTIONS_ERROR = "Cannot create transactions for INDEX assets"

_FAMILY_PREFIXES: tuple[tuple[str, AssetType], ...] = (
    ("ETF_", AssetType.ETF),
    ("CROWDFUND_", AssetType.CROWDFUND),
)


class TypeChangeVerdict(StrEnum):
    """What a change of asset type means: fine, fine with a warning, or refused."""

    OK = "ok"
    FAMILY_WARNING = "family_warning"
    INDEX_WITH_TRANSACTIONS = "index_with_transactions"


def asset_type_family(asset_type: AssetType | str) -> AssetType:
    """Return the family of ``asset_type`` (a base type): ETF_STOCK -> ETF, STOCK -> STOCK."""
    value = AssetType(asset_type)
    for prefix, family in _FAMILY_PREFIXES:
        if value.value.startswith(prefix):
            return family
    return value


def family_changed(old: AssetType | str, new: AssetType | str) -> bool:
    """True when moving from ``old`` to ``new`` crosses to another family."""
    return asset_type_family(old) != asset_type_family(new)


def type_allows_transactions(asset_type: AssetType | str) -> bool:
    """Only INDEX forbids transactions."""
    return AssetType(asset_type) != AssetType.INDEX


def classify_type_change(old: AssetType | str, new: AssetType | str, tx_count: int) -> TypeChangeVerdict:
    """
    Judge a type change of one asset that has ``tx_count`` transactions.

    - becoming INDEX with transactions -> ``INDEX_WITH_TRANSACTIONS`` (blocked, and no family warning on top);
    - an asset that already is INDEX is never blocked, whatever it holds: no clean-up;
    - any other change of family -> ``FAMILY_WARNING``;
    - else ``OK``.
    """
    old_type, new_type = AssetType(old), AssetType(new)
    if new_type == AssetType.INDEX and old_type != AssetType.INDEX and tx_count > 0:
        return TypeChangeVerdict.INDEX_WITH_TRANSACTIONS
    if family_changed(old_type, new_type):
        return TypeChangeVerdict.FAMILY_WARNING
    return TypeChangeVerdict.OK
