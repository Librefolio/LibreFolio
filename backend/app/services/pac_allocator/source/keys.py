"""Shared helpers of the planner source: the provenance ids of the copied facts, the stable keys of every copied entity, currency validation and the builder of field issues."""

from __future__ import annotations

import hashlib
from datetime import date as date_type
from decimal import Decimal

from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import (
    PortfolioPlannerSourceDateParam,
    PortfolioPlannerSourceFieldPath,
    PortfolioPlannerSourceIssue,
    PortfolioPlannerSourceTextParam,
)

PORTFOLIO_PROVENANCE_ID = "source:portfolio-ledger"
MARKET_PROVENANCE_ID = "source:market-data"
BROKER_PROVENANCE_ID = "source:broker-domain"
FX_PROVENANCE_ID = "source:saved-fx"
WAC_PROVENANCE_ID = "source:runtime-wac"
ENGINE_PROVENANCE_ID = "source:portfolio-engine"


def asset_key(asset_id: int) -> str:
    return f"asset:{asset_id}"


def broker_key(broker_id: int) -> str:
    return f"broker:{broker_id}"


def holding_key(asset_id: int, broker_id: int) -> str:
    return f"holding:asset:{asset_id}:broker:{broker_id}"


def cash_key(broker_id: int, currency: str) -> str:
    return f"cash:broker:{broker_id}:{currency}"


def price_key(asset_id: int, reference_date: date_type) -> str:
    return f"price:asset:{asset_id}:{reference_date.isoformat()}"


def wac_key(asset_id: int, broker_id: int, as_of: date_type, currency: str) -> str:
    return f"wac:asset:{asset_id}:broker:{broker_id}:{as_of.isoformat()}:{currency}"


def current_weight_key(asset_id: int) -> str:
    return f"current:asset:{asset_id}"


def classification_key(asset_id: int, dimension: str, category_id: str | None) -> str:
    if category_id is None:
        token = "none"
    else:
        token = hashlib.sha256(category_id.encode("utf-8")).hexdigest()[:12]
    return f"class:asset:{asset_id}:{dimension}:{token}"


def fx_key(
    pair: str,
    reference_date: date_type,
    source: str,
) -> str:
    source_token = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]
    return f"fx:{pair}:{reference_date.isoformat()}:{source_token}"


def field_issue(
    *,
    code: str,
    kind: str,
    severity: str,
    section: str,
    entity_kind: str,
    entity_id: str,
    field: str,
    params: list | None = None,
) -> PortfolioPlannerSourceIssue:
    return PortfolioPlannerSourceIssue(
        code=code,
        kind=kind,
        severity=severity,
        path=PortfolioPlannerSourceFieldPath(
            kind="field",
            section=section,
            entity_kind=entity_kind,
            entity_id=entity_id,
            field=field,
        ),
        message_key=code,
        params=params or [],
    )


def text_param(name: str, value: str) -> PortfolioPlannerSourceTextParam:
    return PortfolioPlannerSourceTextParam(kind="text", name=name, value=value)


def date_param(name: str, value: date_type) -> PortfolioPlannerSourceDateParam:
    return PortfolioPlannerSourceDateParam(kind="date", name=name, value=value)


def validated_currency(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return Currency.validate_code(value)
    except ValueError:
        return None


def normalized_fx_pair(
    source_currency: str,
    destination_currency: str,
) -> tuple[str, str, bool]:
    if source_currency < destination_currency:
        return source_currency, destination_currency, False
    return destination_currency, source_currency, True


def usable_rate(rate: Decimal | None) -> bool:
    """A saved FX rate the planner may use (X-R45b): finite and above 0. A 0 or an infinity is what an older version
    could store; a finite rate past the column's limits stays a value (developer, 19/10). The one rule of every saved rate
    the planner source reads: the quotes (``fx_quotes``) and the evidence of the average cost's rates (``wac``; MF's
    review of the X-R45 revert, 20/10)."""
    return rate is not None and rate.is_finite() and rate > 0
