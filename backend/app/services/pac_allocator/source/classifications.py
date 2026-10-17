"""Asset classifications for the planner source: the saved sector, geography and type distributions, parsed without modification, or a placeholder with an issue."""

from __future__ import annotations

import json
import re
from decimal import Decimal

import pycountry

from backend.app.db.models import Asset
from backend.app.schemas.portfolio import (
    PortfolioPlannerSourceClassification,
    PortfolioPlannerSourceIssue,
)
from backend.app.services.pac_allocator.source.keys import MARKET_PROVENANCE_ID, asset_key, classification_key, field_issue, text_param
from backend.app.utils.asset.sector import FinancialSector

_KNOWN_SECTORS = frozenset(sector.value for sector in FinancialSector)
# The metadata writers store Pydantic JSON, where a Decimal weight is plain decimal text ("0.6000").
_SAVED_WEIGHT_TEXT = re.compile(r"[0-9]+(?:\.[0-9]+)?")
# The catch-all geographic key the writers keep as it is (utils.asset.geo.normalize_country_keys).
_GEOGRAPHY_OTHER = "Other"


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
    if not isinstance(value, dict):
        return None
    distribution = value.get("distribution")
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
    issues: list[PortfolioPlannerSourceIssue],
) -> list[PortfolioPlannerSourceClassification]:
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

        if not asset.classification_params:
            for dimension in ("sector", "geography"):
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

        try:
            metadata = json.loads(
                asset.classification_params,
                parse_float=Decimal,
                parse_int=Decimal,
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            metadata = None
        if not isinstance(metadata, dict):
            rows.extend(
                [
                    _classification_placeholder(asset.id, "sector"),
                    _classification_placeholder(asset.id, "geography"),
                ]
            )
            issues.append(
                field_issue(
                    code="allocation.classification_invalid",
                    kind="invalid",
                    severity="warning",
                    section="classifications",
                    entity_kind="asset",
                    entity_id=asset_ref,
                    field="classification_params",
                )
            )
            continue

        for dimension, metadata_key in (
            ("sector", "sector_area"),
            ("geography", "geographic_area"),
        ):
            if metadata_key not in metadata or metadata[metadata_key] is None:
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
                metadata[metadata_key],
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
