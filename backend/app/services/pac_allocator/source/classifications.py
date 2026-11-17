"""Asset classifications for the planner source: the type, and the sector and geography distributions of the asset profile
on the planner's day (plan 68, D4), parsed without modification, or a placeholder with an issue."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from datetime import date
from decimal import Decimal
from typing import Any

import pycountry
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.portfolio.planner_source import PortfolioPlannerSourceClassification, PortfolioPlannerSourceIssue
from backend.app.services.assets.profile.store import read_steps
from backend.app.services.pac_allocator.source.keys import MARKET_PROVENANCE_ID, asset_key, classification_key, field_issue, text_param
from backend.app.utils.asset.sector import FinancialSector

_KNOWN_SECTORS = frozenset(sector.value for sector in FinancialSector)
# The profile stores a weight as plain decimal text ("0.6000", catalogue.normalize_value).
_SAVED_WEIGHT_TEXT = re.compile(r"[0-9]+(?:\.[0-9]+)?")
# The catch-all geographic key the profile keeps as it is (utils.asset.geo.normalize_country_keys).
_GEOGRAPHY_OTHER = "Other"


#: The profile voices the planner reads, by dimension (plan 68, D4).
_PROFILE_VOICES = ("sector", "geography")


async def load_profile_classifications(session: AsyncSession, asset_ids: Iterable[int], day: date) -> dict[int, dict[str, Any]]:
    """Each asset's sector and geography on ``day``, the planner's day (plan 68, D4): voice → the stored value of the step
    holding it, the first value carried back when the profile starts later; ``None`` for a voice emptied on purpose. An
    asset with no row is left out; ``classification_params`` is not read."""
    ids = sorted(set(asset_ids))
    if not ids:
        return {}
    steps = await read_steps(session, ids, DateRangeModel(start=day), _PROFILE_VOICES, carry_back=True)
    return {asset_id: {voice: voice_steps[-1].value for voice, voice_steps in voices.items() if voice_steps} for asset_id, voices in steps.items()}


def _classification_placeholder(
    asset_id: int,
    dimension: str,
) -> PortfolioPlannerSourceClassification:
    return PortfolioPlannerSourceClassification(
        classification_id=classification_key(asset_id, dimension, None),
        asset_id=asset_key(asset_id),
        dimension=dimension,
        category_id=None,
        label=None,
        weight=None,
        provenance_id=MARKET_PROVENANCE_ID,
    )


def _parse_saved_distribution(  # noqa: C901 — direct validation keeps persisted classifications unmodified
    value,
    *,
    dimension: str,
) -> list[tuple[str, Decimal]] | None:
    distribution = value
    if not isinstance(distribution, dict) or not distribution:
        return None

    parsed: list[tuple[str, Decimal]] = []
    for category, raw_weight in distribution.items():
        if not isinstance(category, str) or not category:
            return None
        if dimension == "sector" and category not in _KNOWN_SECTORS:
            return None
        if dimension == "geography" and category != _GEOGRAPHY_OTHER and (len(category) != 3 or category != category.upper() or pycountry.countries.get(alpha_3=category) is None):
            return None
        if isinstance(raw_weight, Decimal):
            weight = raw_weight
        elif isinstance(raw_weight, str) and _SAVED_WEIGHT_TEXT.fullmatch(raw_weight):
            weight = Decimal(raw_weight)
        else:
            return None
        if not weight.is_finite() or weight < 0:
            return None
        parsed.append((category, weight))

    if sum((weight for _category, weight in parsed), Decimal("0")) != Decimal("1"):
        return None
    return sorted(parsed, key=lambda item: item[0])


def build_planner_classifications(  # noqa: C901 — missing/invalid dimension outcomes stay explicit
    candidate_assets: list[Asset],
    *,
    profile: Mapping[int, Mapping[str, Any]],
    issues: list[PortfolioPlannerSourceIssue],
) -> list[PortfolioPlannerSourceClassification]:
    """The classification rows of the candidate assets: the type, and the sector and geography of ``profile`` (asset id →
    voice → stored value, ``load_profile_classifications``), each a placeholder with an issue when missing or invalid."""
    rows: list[PortfolioPlannerSourceClassification] = []
    for asset in candidate_assets:
        if asset.id is None:
            continue
        asset_ref = asset_key(asset.id)
        asset_class = getattr(asset.asset_type, "value", asset.asset_type)
        if isinstance(asset_class, str) and asset_class:
            rows.append(
                PortfolioPlannerSourceClassification(
                    classification_id=classification_key(asset.id, "asset_type", asset_class),
                    asset_id=asset_ref,
                    dimension="asset_type",
                    category_id=asset_class,
                    label=asset_class,
                    weight=Decimal("1"),
                    provenance_id=MARKET_PROVENANCE_ID,
                )
            )
        else:
            rows.append(_classification_placeholder(asset.id, "asset_type"))
            issues.append(
                field_issue(
                    code="allocation.asset_type_missing",
                    kind="missing",
                    severity="warning",
                    section="classifications",
                    entity_kind="asset",
                    entity_id=asset_ref,
                    field="asset_type",
                )
            )

        voices = profile.get(asset.id) or {}
        for dimension in _PROFILE_VOICES:
            if voices.get(dimension) is None:
                # No row of the voice, or emptied on purpose: the asset has no such distribution on the planner's day
                rows.append(_classification_placeholder(asset.id, dimension))
                issues.append(
                    field_issue(
                        code=f"allocation.classification_{dimension}_missing",
                        kind="missing",
                        severity="warning",
                        section="classifications",
                        entity_kind="asset",
                        entity_id=asset_ref,
                        field=dimension,
                    )
                )
                continue
            distribution = _parse_saved_distribution(
                voices[dimension],
                dimension=dimension,
            )
            if distribution is None:
                rows.append(_classification_placeholder(asset.id, dimension))
                issues.append(
                    field_issue(
                        code="allocation.classification_invalid",
                        kind="invalid",
                        severity="warning",
                        section="classifications",
                        entity_kind="asset",
                        entity_id=asset_ref,
                        field=dimension,
                        params=[text_param("dimension", dimension)],
                    )
                )
                continue
            rows.extend(
                PortfolioPlannerSourceClassification(
                    classification_id=classification_key(asset.id, dimension, category),
                    asset_id=asset_ref,
                    dimension=dimension,
                    category_id=category,
                    label=category,
                    weight=weight,
                    provenance_id=MARKET_PROVENANCE_ID,
                )
                for category, weight in distribution
            )
    return rows
