"""Focused exact-normalization contract tests for Planner v2."""

from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import Any, cast, get_args

import pytest

from backend.app.schemas.pac_allocator import (
    PAC_PLAN_INPUT_ADAPTER,
    REBALANCER_PLAN_INPUT_ADAPTER,
    FiniteDecimal,
    PlannerIssue,
    PlannerIssueCode,
    PlannerIssuePath,
)
from backend.app.schemas.pac_allocator import (
    ExactRatio as WireExactRatio,
)
from backend.app.services.pac_allocator.issues import (
    CANONICAL_ISSUE_CODES,
    W1_NORMALIZER_ISSUE_DEFINITIONS,
    IssueKind,
    IssueSeverity,
    canonicalize_issues,
    field_path,
    make_issue,
    normalization_availability,
    normalizer_issue_definition,
    section_path,
)
from backend.app.services.pac_allocator.models import ExactPlannerScenario
from backend.app.services.pac_allocator.normalize import (
    PlannerV2NormalizationResult,
    exact_number_to_ratio,
    normalize_pac_plan,
    normalize_planner_request,
    normalize_rebalancer_plan,
)
from backend.app.services.pac_allocator.numeric import ExactRatio

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "pac_allocator"
PAC_FIXTURE = "pac_plan_request.min.v2.json"
REBALANCER_FIXTURE = "rebalancer_plan_request.medium.v2.json"

JsonObject = dict[str, Any]


def _wire(payload: Any) -> bytes:
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fixture(name: str) -> JsonObject:
    payload = json.loads((FIXTURE_DIR / name).read_bytes())
    assert isinstance(payload, dict)
    return payload


def _find_row(rows: list[JsonObject], key: str, value: str) -> JsonObject:
    matches = [row for row in rows if row.get(key) == value]
    assert len(matches) == 1, f"Expected one {key}={value!r}, found {len(matches)}"
    (row,) = matches
    return row


def _normalize_payload(
    product: str,
    payload: JsonObject,
    *,
    source_issues: tuple[PlannerIssue, ...] = (),
) -> PlannerV2NormalizationResult:
    if product == "pac":
        request = PAC_PLAN_INPUT_ADAPTER.validate_json(_wire(payload), strict=True)
        return normalize_pac_plan(request, source_issues=source_issues)
    if product == "rebalancer":
        request = REBALANCER_PLAN_INPUT_ADAPTER.validate_json(
            _wire(payload),
            strict=True,
        )
        return normalize_rebalancer_plan(
            request,
            source_issues=source_issues,
        )
    raise AssertionError(f"Unknown Planner product {product!r}")


def _single_issue(
    result: PlannerV2NormalizationResult,
    code: PlannerIssueCode,
    *,
    severity: IssueSeverity | None = None,
) -> PlannerIssue:
    matches = [issue for issue in result.issues if issue.code == code and (severity is None or issue.severity == severity)]
    assert len(matches) == 1, f"Expected one {code}/{severity or '*'}, found {len(matches)} in " f"{tuple(issue.code for issue in result.issues)!r}"
    (issue,) = matches
    return issue


def _w1_issue(
    code: PlannerIssueCode,
    path: PlannerIssuePath,
) -> PlannerIssue:
    return make_issue(normalizer_issue_definition(code), path)


def _source_issue(
    code: PlannerIssueCode,
    *,
    kind: IssueKind,
    severity: IssueSeverity,
    path: PlannerIssuePath,
) -> PlannerIssue:
    return PlannerIssue(
        code=code,
        severity=severity,
        kind=kind,
        path=path,
        message_key=code,
        params=[],
    )


def _field_wire_path(
    section: str,
    entity_kind: str,
    entity_id: str,
    field: str,
) -> JsonObject:
    return {
        "kind": "field",
        "section": section,
        "entity_kind": entity_kind,
        "entity_id": entity_id,
        "field": field,
    }


def _section_wire_path(section: str) -> JsonObject:
    return {"kind": "section", "section": section}


def _issue_wire_path(issue: PlannerIssue) -> JsonObject:
    path = issue.model_dump(mode="json")["path"]
    assert isinstance(path, dict)
    return path


def _stale_source_warning() -> PlannerIssue:
    return _source_issue(
        "allocation.provenance_stale_confirmed",
        kind="info",
        severity="warning",
        path=field_path(
            "assets",
            "asset",
            "asset-one",
            "quote.freshness",
        ),
    )


def _inactive_source_warning(
    broker_id: str = "broker-one",
) -> PlannerIssue:
    return _source_issue(
        "allocation.broker_inactive",
        kind="unsupported",
        severity="warning",
        path=field_path(
            "brokers",
            "broker",
            broker_id,
            "active",
        ),
    )


EXACT_NUMBER_CASES = (
    pytest.param(
        FiniteDecimal(kind="finite_decimal", value="1.2300"),
        (123, 100),
        id="finite-trailing-zeroes",
    ),
    pytest.param(
        FiniteDecimal(kind="finite_decimal", value="-0.125"),
        (-1, 8),
        id="finite-negative",
    ),
    pytest.param(
        FiniteDecimal(kind="finite_decimal", value="1000"),
        (1000, 1),
        id="finite-integer",
    ),
    pytest.param(
        WireExactRatio(
            kind="exact_ratio",
            numerator="1",
            denominator="3",
            display_decimal="0.333333",
            display_scale=6,
            display_authority="non_authoritative",
        ),
        (1, 3),
        id="ratio-nonterminating",
    ),
    pytest.param(
        WireExactRatio(
            kind="exact_ratio",
            numerator="-3",
            denominator="20",
            display_decimal="-0.15",
            display_scale=2,
            display_authority="non_authoritative",
        ),
        (-3, 20),
        id="ratio-negative",
    ),
    pytest.param(
        WireExactRatio(
            kind="exact_ratio",
            numerator="0",
            denominator="1",
            display_decimal="0.000",
            display_scale=3,
            display_authority="non_authoritative",
        ),
        (0, 1),
        id="ratio-zero",
    ),
)


@pytest.mark.parametrize(("wire_number", "expected"), EXACT_NUMBER_CASES)
def test_exact_number_to_ratio_is_lossless(
    wire_number: FiniteDecimal | WireExactRatio,
    expected: tuple[int, int],
) -> None:
    normalized = exact_number_to_ratio(wire_number)

    assert isinstance(normalized, ExactRatio)
    assert normalized.as_integer_ratio() == expected


def test_minimal_pac_normalizes_to_immutable_canonical_exact_scenario() -> None:
    request = PAC_PLAN_INPUT_ADAPTER.validate_json(
        (FIXTURE_DIR / PAC_FIXTURE).read_bytes(),
        strict=True,
    )

    result = normalize_pac_plan(request)

    assert result == normalize_planner_request(request)
    assert result.availability == "ready"
    assert result.ready is True
    assert result.issues == ()
    assert result.scenario is result.normalized
    scenario = result.normalized
    assert isinstance(scenario, ExactPlannerScenario)
    assert scenario.product == "pac"
    assert scenario.holdings == ()
    assert scenario.sell_context is None

    identity_axes = (
        (scenario.currency_specs, "currency"),
        (scenario.provenance, "provenance_id"),
        (scenario.valuation_rates, "rate_id"),
        (scenario.assets, "asset_id"),
        (scenario.brokers, "broker_id"),
        (scenario.holdings, "holding_id"),
        (scenario.existing_cash, "cash_id"),
        (scenario.contributions, "contribution_id"),
        (scenario.funding_routes, "route_id"),
        (scenario.order_routes, "route_id"),
        (scenario.fx_quotes, "quote_id"),
        (scenario.fx_routes, "route_id"),
        (scenario.target_weights, "asset_id"),
    )
    for rows, attribute in identity_axes:
        identities = tuple(getattr(row, attribute) for row in rows)
        assert identities == tuple(sorted(set(identities)))

    asset = next(row for row in scenario.assets if row.asset_id == "asset-one")
    assert tuple((exposure.dimension, exposure.category) for exposure in asset.exposures) == (
        ("asset_type", "equity"),
        ("geography", "unknown"),
        ("sector", "broad"),
    )
    assert asset.quote.price.amount == ExactRatio(10)
    cash = next(row for row in scenario.existing_cash if row.cash_id == "cash-broker-one-eur")
    assert cash.selected.amount == ExactRatio(5)
    assert isinstance(scenario.assets, tuple)
    with pytest.raises(FrozenInstanceError):
        scenario.policy = "min_fragmentation"


AVAILABILITY_CASES = (
    pytest.param((), False, "ready", id="no-issues"),
    pytest.param(
        (),
        True,
        "ready",
        id="imported-warning-only",
    ),
    pytest.param(
        ("allocation.capacity_unsupported",),
        False,
        "unsupported",
        id="unsupported",
    ),
    pytest.param(
        (
            "allocation.capacity_unsupported",
            "allocation.nonpositive_price",
        ),
        False,
        "invalid",
        id="invalid-over-unsupported",
    ),
    pytest.param(
        ("allocation.price_missing",),
        False,
        "needs_input",
        id="missing",
    ),
    pytest.param(
        (
            "allocation.price_missing",
            "allocation.capacity_unsupported",
            "allocation.nonpositive_price",
        ),
        False,
        "needs_input",
        id="missing-over-invalid-and-unsupported",
    ),
)


@pytest.mark.parametrize(
    ("codes", "include_source_warning", "expected"),
    AVAILABILITY_CASES,
)
def test_normalization_availability_uses_frozen_error_precedence(
    codes: tuple[PlannerIssueCode, ...],
    include_source_warning: bool,
    expected: str,
) -> None:
    issues = tuple(_w1_issue(code, section_path("input")) for code in codes)
    if include_source_warning:
        issues = (_stale_source_warning(), *issues)

    assert normalization_availability(issues) == expected


def _mutate_currency_minor_unit(payload: JsonObject, value: str) -> None:
    currency = _find_row(payload["currency_specs"], "currency", "EUR")
    currency["minor_unit"] = value


def _mutate_valuation_rate(payload: JsonObject, value: str) -> None:
    valuation_rate = _find_row(
        payload["valuation_rates"],
        "valuation_rate_id",
        "valuation-usd-eur",
    )
    valuation_rate["rate"] = value


def _mutate_price(payload: JsonObject, value: str) -> None:
    asset = _find_row(payload["assets"], "asset_id", "asset-one")
    asset["quote"]["amount"] = value


def _mutate_quote_basis(payload: JsonObject, value: str) -> None:
    asset = _find_row(payload["assets"], "asset_id", "asset-one")
    asset["quote"]["quote_base_quantity"] = value


def _mutate_exposure_weight(payload: JsonObject, value: str) -> None:
    asset = _find_row(payload["assets"], "asset_id", "asset-one")
    exposure = _find_row(
        asset["exposures"],
        "dimension",
        "asset_type",
    )
    exposure["weight"] = value


def _mutate_target_weight(payload: JsonObject, value: str) -> None:
    target = _find_row(payload["target_weights"], "asset_id", "asset-one")
    target["weight"] = value


def _mutate_economic_share(payload: JsonObject, value: str) -> None:
    holding = _find_row(
        payload["holdings"],
        "holding_id",
        "holding-a-alpha",
    )
    holding["economic_share"] = value


def _mutate_planning_quantity(payload: JsonObject, value: str) -> None:
    holding = _find_row(
        payload["holdings"],
        "holding_id",
        "holding-b-beta",
    )
    holding["planning_quantity"] = value


def _mutate_cash_selection(payload: JsonObject, value: str) -> None:
    cash = _find_row(
        payload["existing_cash"],
        "cash_id",
        "cash-broker-one-eur",
    )
    cash["selected"]["amount"] = value


def _mutate_fx_rate(payload: JsonObject, value: str) -> None:
    quote = _find_row(
        payload["fx_quotes"],
        "fx_quote_id",
        "fxq-eur-usd",
    )
    quote["rate"] = value


def _mutate_tax_rate(payload: JsonObject, value: str) -> None:
    sell_context = payload["sell_context"]
    assert isinstance(sell_context, dict)
    tax = _find_row(
        sell_context["asset_taxes"],
        "asset_id",
        "asset-a",
    )
    tax["tax_rate"] = value


RANGE_MUTATORS: dict[str, Callable[[JsonObject, str], None]] = {
    "currency-minor-unit": _mutate_currency_minor_unit,
    "valuation-rate": _mutate_valuation_rate,
    "price": _mutate_price,
    "quote-basis": _mutate_quote_basis,
    "exposure-weight": _mutate_exposure_weight,
    "target-weight": _mutate_target_weight,
    "target-total": _mutate_target_weight,
    "economic-share": _mutate_economic_share,
    "planning-quantity": _mutate_planning_quantity,
    "cash-selection": _mutate_cash_selection,
    "fx-rate": _mutate_fx_rate,
    "tax-rate": _mutate_tax_rate,
}


def _apply_range_mutation(
    payload: JsonObject,
    mutation: str,
    value: str,
) -> None:
    mutator = RANGE_MUTATORS.get(mutation)
    if mutator is None:
        raise AssertionError(f"Unknown range mutation {mutation!r}")
    mutator(payload, value)


RANGE_ISSUE_CASES = (
    pytest.param(
        "pac",
        "currency-minor-unit",
        "0",
        "allocation.currency_minor_unit_nonpositive",
        _field_wire_path("input", "currency", "EUR", "minor_unit"),
        id="currency-minor-unit",
    ),
    pytest.param(
        "rebalancer",
        "valuation-rate",
        "0",
        "allocation.nonpositive_valuation_rate",
        _field_wire_path("fx", "currency", "USD", "rate"),
        id="valuation-rate",
    ),
    pytest.param(
        "pac",
        "price",
        "0",
        "allocation.nonpositive_price",
        _field_wire_path("assets", "asset", "asset-one", "quote.amount"),
        id="price",
    ),
    pytest.param(
        "pac",
        "quote-basis",
        "0",
        "allocation.invalid_quote_basis",
        _field_wire_path(
            "assets",
            "asset",
            "asset-one",
            "quote.quote_base_quantity",
        ),
        id="quote-basis",
    ),
    pytest.param(
        "pac",
        "exposure-weight",
        "1.25",
        "allocation.exposure_weight_out_of_range",
        _field_wire_path("assets", "asset", "asset-one", "exposures.weight"),
        id="exposure-weight",
    ),
    pytest.param(
        "pac",
        "target-weight",
        "1.25",
        "allocation.target_weight_out_of_range",
        _field_wire_path("targets", "asset", "asset-one", "weight"),
        id="target-weight",
    ),
    pytest.param(
        "pac",
        "target-total",
        "0.5",
        "allocation.target_total_not_one",
        _section_wire_path("targets"),
        id="target-total",
    ),
    pytest.param(
        "rebalancer",
        "economic-share",
        "1.5",
        "allocation.economic_share_out_of_range",
        _field_wire_path(
            "holdings",
            "holding",
            "holding-a-alpha",
            "economic_share",
        ),
        id="economic-share",
    ),
    pytest.param(
        "rebalancer",
        "planning-quantity",
        "-1",
        "allocation.planning_quantity_negative",
        _field_wire_path(
            "holdings",
            "holding",
            "holding-b-beta",
            "planning_quantity",
        ),
        id="planning-quantity",
    ),
    pytest.param(
        "pac",
        "cash-selection",
        "6",
        "allocation.cash_selection_invalid",
        _field_wire_path(
            "cash",
            "cash",
            "cash-broker-one-eur",
            "selected",
        ),
        id="cash-selection",
    ),
    pytest.param(
        "rebalancer",
        "fx-rate",
        "0",
        "allocation.nonpositive_fx_rate",
        _field_wire_path("fx", "fx_quote", "fxq-eur-usd", "rate"),
        id="fx-rate",
    ),
    pytest.param(
        "rebalancer",
        "tax-rate",
        "1.5",
        "portfolio_rebalancer.tax_rate_out_of_range",
        _field_wire_path("policy", "asset", "asset-a", "tax_rate"),
        id="tax-rate",
    ),
)


@pytest.mark.parametrize(
    ("product", "mutation", "value", "code", "expected_path"),
    RANGE_ISSUE_CASES,
)
def test_key_range_checks_emit_frozen_codes_and_paths(
    product: str,
    mutation: str,
    value: str,
    code: PlannerIssueCode,
    expected_path: JsonObject,
) -> None:
    fixture_name = PAC_FIXTURE if product == "pac" else REBALANCER_FIXTURE
    payload = _fixture(fixture_name)
    _apply_range_mutation(payload, mutation, value)

    result = _normalize_payload(product, payload)
    issue = _single_issue(result, code)

    assert result.availability == "invalid"
    assert issue.kind == "invalid"
    assert issue.severity == "error"
    assert _issue_wire_path(issue) == expected_path


@pytest.mark.parametrize(
    "include_source_warning",
    (
        pytest.param(False, id="no-source-warning"),
        pytest.param(True, id="preserve-source-warning"),
    ),
)
def test_accepted_stale_observation_emits_no_w1_warning(
    include_source_warning: bool,
) -> None:
    payload = _fixture(PAC_FIXTURE)
    asset = _find_row(payload["assets"], "asset_id", "asset-one")
    asset["quote"]["freshness"] = {
        "kind": "stale",
        "age_days": 3,
        "accepted": True,
    }
    source_warning = _stale_source_warning() if include_source_warning else None
    source_issues = (source_warning,) if source_warning is not None else ()

    result = _normalize_payload(
        "pac",
        payload,
        source_issues=source_issues,
    )

    assert result.availability == "ready"
    assert result.ready is True
    if source_warning is None:
        assert result.issues == ()
    else:
        assert result.issues == (source_warning,)
    scenario = result.normalized
    assert scenario is not None
    exact_asset = next(row for row in scenario.assets if row.asset_id == "asset-one")
    assert exact_asset.quote.freshness.kind == "stale"
    assert exact_asset.quote.freshness.age_days == 3
    assert exact_asset.quote.freshness.accepted is True


STALE_INVALID_CASES = (
    pytest.param(
        -1,
        True,
        "allocation.stale_age_negative",
        id="negative-age",
    ),
    pytest.param(
        3,
        False,
        "allocation.stale_observation_not_accepted",
        id="not-accepted",
    ),
)


@pytest.mark.parametrize(("age_days", "accepted", "code"), STALE_INVALID_CASES)
def test_invalid_stale_observation_emits_exact_w1_error(
    age_days: int,
    accepted: bool,
    code: PlannerIssueCode,
) -> None:
    payload = _fixture(PAC_FIXTURE)
    asset = _find_row(payload["assets"], "asset_id", "asset-one")
    asset["quote"]["freshness"] = {
        "kind": "stale",
        "age_days": age_days,
        "accepted": accepted,
    }

    result = _normalize_payload("pac", payload)
    issue = _single_issue(result, code)

    assert result.availability == "invalid"
    assert result.normalized is None
    assert tuple(row.code for row in result.issues) == (code,)
    assert issue.kind == "invalid"
    assert issue.severity == "error"
    assert _issue_wire_path(issue) == _field_wire_path(
        "assets",
        "asset",
        "asset-one",
        "quote.freshness",
    )


def _inactive_custody_only_payload() -> JsonObject:
    payload = _fixture(PAC_FIXTURE)
    broker = _find_row(payload["brokers"], "broker_id", "broker-one")
    broker["identity"] = {
        "kind": "domain_broker",
        "source_broker_id": "synthetic-broker-one",
        "name": "Synthetic Broker One",
        "active": False,
    }
    broker["capabilities"] = []
    broker["fee_schedules"] = []
    cash = _find_row(
        payload["existing_cash"],
        "cash_id",
        "cash-broker-one-eur",
    )
    cash["selected"]["amount"] = "0"
    payload["funding_routes"] = []
    payload["order_routes"] = []
    payload["fx_quotes"] = []
    payload["fx_routes"] = []
    return payload


def _inactive_executable_payload(
    trigger: str,
) -> tuple[str, JsonObject, str]:
    if trigger == "sell-route":
        payload = _fixture(REBALANCER_FIXTURE)
        holding = _find_row(
            payload["holdings"],
            "holding_id",
            "holding-a-alpha",
        )
        holding["economic_share"] = "1"
        sell_context = payload["sell_context"]
        assert isinstance(sell_context, dict)
        tax = _find_row(
            sell_context["asset_taxes"],
            "asset_id",
            "asset-a",
        )
        tax["tax_rate"] = "0.25"
        return "rebalancer", payload, "broker-alpha"

    payload = _inactive_custody_only_payload()
    baseline = _fixture(PAC_FIXTURE)
    baseline_broker = _find_row(
        baseline["brokers"],
        "broker_id",
        "broker-one",
    )
    broker = _find_row(payload["brokers"], "broker_id", "broker-one")
    if trigger == "capability":
        broker["capabilities"] = deepcopy(baseline_broker["capabilities"])
    elif trigger == "funding-route":
        payload["funding_routes"] = [
            {
                "funding_route_id": "fund-cash-broker-one",
                "source": {
                    "kind": "existing_cash",
                    "cash_id": "cash-broker-one-eur",
                },
                "broker_id": "broker-one",
                "currency": "EUR",
                "priority": 1,
                "transfer_cap": {
                    "amount": "5",
                    "currency": "EUR",
                },
                "provenance_id": "prov-manual",
            }
        ]
    elif trigger == "buy-route":
        broker["capabilities"] = deepcopy(baseline_broker["capabilities"])
        broker["fee_schedules"] = deepcopy(baseline_broker["fee_schedules"])
        payload["order_routes"] = deepcopy(baseline["order_routes"])
    elif trigger == "fx-route":
        medium = _fixture(REBALANCER_FIXTURE)
        usd_spec = deepcopy(_find_row(medium["currency_specs"], "currency", "USD"))
        valuation_rate = deepcopy(
            _find_row(
                medium["valuation_rates"],
                "valuation_rate_id",
                "valuation-usd-eur",
            )
        )
        quote = deepcopy(_find_row(medium["fx_quotes"], "fx_quote_id", "fxq-eur-usd"))
        route = deepcopy(_find_row(medium["fx_routes"], "fx_route_id", "fxr-beta-eur-usd"))
        valuation_rate["provenance_id"] = "prov-manual"
        quote["provenance_id"] = "prov-manual"
        route["broker_id"] = "broker-one"
        payload["currency_specs"].append(usd_spec)
        payload["valuation_rates"] = [valuation_rate]
        payload["fx_quotes"] = [quote]
        payload["fx_routes"] = [route]
    elif trigger == "selected-cash":
        cash = _find_row(
            payload["existing_cash"],
            "cash_id",
            "cash-broker-one-eur",
        )
        cash["selected"]["amount"] = "5"
    else:
        raise AssertionError(f"Unknown inactive Broker trigger {trigger!r}")
    return "pac", payload, "broker-one"


def test_inactive_custody_only_adds_no_issue_and_cash_is_not_spendable() -> None:
    payload = _inactive_custody_only_payload()
    without_source = _normalize_payload("pac", payload)
    source_warning = _inactive_source_warning()
    with_source = _normalize_payload(
        "pac",
        payload,
        source_issues=(source_warning,),
    )

    assert without_source.availability == "ready"
    assert without_source.issues == ()
    assert with_source.availability == "ready"
    assert with_source.issues == (source_warning,)
    scenario = with_source.normalized
    assert scenario is not None
    broker = next(row for row in scenario.brokers if row.broker_id == "broker-one")
    assert broker.active is False
    cash = next(row for row in scenario.existing_cash if row.cash_id == "cash-broker-one-eur")
    assert cash.available.amount == ExactRatio(5)
    assert cash.selected.amount == ExactRatio(0)
    assert sum(
        (row.selected.amount for row in scenario.existing_cash),
        ExactRatio(0),
    ) == ExactRatio(0)
    assert scenario.funding_routes == ()
    assert scenario.order_routes == ()
    assert scenario.fx_routes == ()


@pytest.mark.parametrize(
    "trigger",
    (
        pytest.param("capability", id="capability"),
        pytest.param("funding-route", id="funding-route"),
        pytest.param("buy-route", id="buy-route"),
        pytest.param("sell-route", id="sell-route"),
        pytest.param("fx-route", id="fx-route"),
        pytest.param("selected-cash", id="selected-cash"),
    ),
)
def test_inactive_domain_broker_executable_surfaces_escalate_to_unsupported(
    trigger: str,
) -> None:
    product, payload, broker_id = _inactive_executable_payload(trigger)
    source_warning = _inactive_source_warning(broker_id)
    result = _normalize_payload(
        product,
        payload,
        source_issues=(source_warning,),
    )

    inactive_error = _single_issue(
        result,
        "allocation.broker_inactive",
        severity="error",
    )
    preserved_warning = _single_issue(
        result,
        "allocation.broker_inactive",
        severity="warning",
    )
    assert result.availability == "unsupported"
    assert result.normalized is None
    assert inactive_error.kind == "unsupported"
    assert inactive_error.severity == "error"
    assert _issue_wire_path(inactive_error) == _field_wire_path(
        "brokers",
        "broker",
        broker_id,
        "active",
    )
    assert preserved_warning == source_warning
    assert preserved_warning.model_dump(mode="json") == (source_warning.model_dump(mode="json"))
    blocking = tuple(issue for issue in result.issues if issue.severity == "error")
    assert blocking == (inactive_error,)


EXECUTION_PROFILE_CASES = (
    pytest.param(
        True,
        False,
        ("allocation.broker_inactive",),
        "ready",
        id="inactive-only",
    ),
    pytest.param(
        False,
        True,
        ("allocation.broker_execution_profile_unsupported",),
        "unsupported",
        id="execution-profile-only",
    ),
    pytest.param(
        True,
        True,
        (
            "allocation.broker_inactive",
            "allocation.broker_execution_profile_unsupported",
        ),
        "unsupported",
        id="both-independent",
    ),
)


@pytest.mark.parametrize(
    (
        "include_inactive",
        "include_execution_profile",
        "expected_codes",
        "expected_availability",
    ),
    EXECUTION_PROFILE_CASES,
)
def test_imported_execution_profile_issue_is_independent_from_broker_activity(
    include_inactive: bool,
    include_execution_profile: bool,
    expected_codes: tuple[PlannerIssueCode, ...],
    expected_availability: str,
) -> None:
    source_issues: list[PlannerIssue] = []
    if include_inactive:
        source_issues.append(
            _source_issue(
                "allocation.broker_inactive",
                kind="unsupported",
                severity="warning",
                path=field_path(
                    "brokers",
                    "broker",
                    "broker-one",
                    "active",
                ),
            )
        )
    if include_execution_profile:
        source_issues.append(
            _source_issue(
                "allocation.broker_execution_profile_unsupported",
                kind="unsupported",
                severity="error",
                path=field_path(
                    "brokers",
                    "broker",
                    "broker-one",
                    "execution_profile_status",
                ),
            )
        )

    expected_issues = canonicalize_issues(source_issues)
    result = _normalize_payload(
        "pac",
        _fixture(PAC_FIXTURE),
        source_issues=tuple(source_issues),
    )

    assert result.availability == expected_availability
    assert result.issues == expected_issues
    assert tuple(issue.code for issue in result.issues) == expected_codes
    assert tuple(issue.model_dump(mode="json") for issue in result.issues) == tuple(issue.model_dump(mode="json") for issue in expected_issues)


def test_canonical_issue_universe_matches_schema_and_w1_map_is_explicit() -> None:
    schema_codes = tuple(get_args(PlannerIssueCode))

    assert schema_codes == CANONICAL_ISSUE_CODES
    assert len(schema_codes) == 89
    assert len(set(schema_codes)) == 89
    assert set(W1_NORMALIZER_ISSUE_DEFINITIONS) < set(schema_codes)
    for code, definition in W1_NORMALIZER_ISSUE_DEFINITIONS.items():
        assert normalizer_issue_definition(code) is definition
        assert definition.code == code
        assert definition.kind in {"missing", "invalid", "unsupported"}
        assert definition.severity == "error"
        assert definition.producer == "w1_normalizer"


REQUIRED_NONPRODUCER_CODES = {
    "allocation.asset_inactive_not_buyable",
    "allocation.asset_type_missing",
    "allocation.broker_execution_profile_unsupported",
    "allocation.classification_geography_missing",
    "allocation.classification_invalid",
    "allocation.classification_sector_missing",
    "allocation.deployment_omitted",
    "allocation.provenance_stale_confirmed",
    "allocation.solver_limit_no_incumbent",
    "allocation.zero_selected_funding",
    "pac_allocator.initial_holding_forbidden",
    "portfolio_rebalancer.sell_irreducibility_unresolved",
}


def test_nonproducer_and_unknown_codes_have_no_invented_w1_definition() -> None:
    nonproducer_codes = tuple(code for code in CANONICAL_ISSUE_CODES if code not in W1_NORMALIZER_ISSUE_DEFINITIONS)

    assert REQUIRED_NONPRODUCER_CODES <= set(nonproducer_codes)
    for code in nonproducer_codes:
        with pytest.raises(
            KeyError,
            match="No explicit W1 normalizer IssueDefinition",
        ):
            normalizer_issue_definition(code)
    with pytest.raises(
        KeyError,
        match="No explicit W1 normalizer IssueDefinition",
    ):
        normalizer_issue_definition(cast(PlannerIssueCode, "allocation.unknown_w1_issue"))


def test_issue_canonicalization_is_deterministic_and_deduplicates_exact_rows() -> None:
    price = _w1_issue(
        "allocation.nonpositive_price",
        field_path(
            "assets",
            "asset",
            "asset-one",
            "quote.amount",
        ),
    )
    duplicate_price = _w1_issue(
        "allocation.nonpositive_price",
        field_path(
            "assets",
            "asset",
            "asset-one",
            "quote.amount",
        ),
    )
    inactive = _w1_issue(
        "allocation.broker_inactive",
        field_path(
            "brokers",
            "broker",
            "broker-one",
            "active",
        ),
    )
    cash = _w1_issue(
        "allocation.cash_selection_invalid",
        field_path(
            "cash",
            "cash",
            "cash-broker-one-eur",
            "selected",
        ),
    )
    target = _w1_issue(
        "allocation.target_total_not_one",
        section_path("targets"),
    )
    scrambled = [target, price, cash, duplicate_price, inactive]

    canonical = canonicalize_issues(scrambled)

    assert canonical == (price, inactive, cash, target)
    assert canonicalize_issues(list(reversed(scrambled))) == canonical


def test_semantically_invalid_medium_rebalancer_fixture_never_becomes_ready() -> None:
    request = REBALANCER_PLAN_INPUT_ADAPTER.validate_json(
        (FIXTURE_DIR / REBALANCER_FIXTURE).read_bytes(),
        strict=True,
    )

    result = normalize_rebalancer_plan(request)

    assert result.availability == "invalid"
    assert result.ready is False
    assert result.normalized is None
    assert result.scenario is None
    expected_paths = {
        "allocation.broker_inactive": _field_wire_path(
            "brokers",
            "broker",
            "broker-alpha",
            "active",
        ),
        "allocation.economic_share_out_of_range": _field_wire_path(
            "holdings",
            "holding",
            "holding-a-alpha",
            "economic_share",
        ),
        "portfolio_rebalancer.tax_rate_out_of_range": _field_wire_path(
            "policy",
            "asset",
            "asset-a",
            "tax_rate",
        ),
    }
    for code, expected_path in expected_paths.items():
        assert _issue_wire_path(_single_issue(result, code)) == expected_path


def _ready_rebalancer_payload() -> JsonObject:
    payload = _fixture(REBALANCER_FIXTURE)
    _find_row(payload["holdings"], "holding_id", "holding-a-alpha")["economic_share"] = "1"
    sell_context = payload["sell_context"]
    assert isinstance(sell_context, dict)
    _find_row(sell_context["asset_taxes"], "asset_id", "asset-a")["tax_rate"] = "0.25"
    _find_row(payload["brokers"], "broker_id", "broker-alpha")["identity"]["active"] = True
    return payload


def _ready_rebalancer_scenario() -> ExactPlannerScenario:
    result = _normalize_payload("rebalancer", _ready_rebalancer_payload())
    assert result.availability == "ready"
    assert result.issues == ()
    assert result.normalized is not None
    return result.normalized


def _assert_duplicate_issue(
    result: PlannerV2NormalizationResult,
    *,
    expected_path: JsonObject,
    expected_params: list[JsonObject],
) -> PlannerIssue:
    issue = _single_issue(result, "allocation.duplicate_id")
    assert result.availability == "invalid"
    assert result.normalized is None
    assert issue.kind == "invalid"
    assert issue.severity == "error"
    assert _issue_wire_path(issue) == expected_path
    assert [param.model_dump(mode="json") for param in issue.params] == expected_params
    return issue


def test_duplicate_domain_asset_source_id_is_canonical_and_typed() -> None:
    payload = _fixture(REBALANCER_FIXTURE)
    asset_a = _find_row(payload["assets"], "asset_id", "asset-a")
    asset_b = _find_row(payload["assets"], "asset_id", "asset-b")
    source_asset_id = asset_a["identity"]["source_asset_id"]
    assert isinstance(source_asset_id, str)
    asset_b["identity"]["source_asset_id"] = source_asset_id

    result = _normalize_payload("rebalancer", payload)
    reversed_payload = deepcopy(payload)
    reversed_payload["assets"] = list(reversed(reversed_payload["assets"]))
    reversed_result = _normalize_payload("rebalancer", reversed_payload)

    duplicate = _assert_duplicate_issue(
        result,
        expected_path=_field_wire_path(
            "assets",
            "asset",
            "asset-a",
            "identity.source_asset_id",
        ),
        expected_params=[
            {
                "kind": "text",
                "name": "source_asset_id",
                "value": source_asset_id,
            }
        ],
    )
    assert duplicate == _single_issue(reversed_result, "allocation.duplicate_id")
    assert result.issues == reversed_result.issues


def test_duplicate_domain_broker_source_id_is_canonical_and_typed() -> None:
    payload = _fixture(REBALANCER_FIXTURE)
    broker_alpha = _find_row(payload["brokers"], "broker_id", "broker-alpha")
    broker_beta = _find_row(payload["brokers"], "broker_id", "broker-beta")
    source_broker_id = broker_alpha["identity"]["source_broker_id"]
    assert isinstance(source_broker_id, str)
    broker_beta["identity"] = {
        "kind": "domain_broker",
        "source_broker_id": source_broker_id,
        "name": broker_beta["identity"]["name"],
        "active": True,
    }

    result = _normalize_payload("rebalancer", payload)
    reversed_payload = deepcopy(payload)
    reversed_payload["brokers"] = list(reversed(reversed_payload["brokers"]))
    reversed_result = _normalize_payload("rebalancer", reversed_payload)

    duplicate = _assert_duplicate_issue(
        result,
        expected_path=_field_wire_path(
            "brokers",
            "broker",
            "broker-alpha",
            "identity.source_broker_id",
        ),
        expected_params=[
            {
                "kind": "text",
                "name": "source_broker_id",
                "value": source_broker_id,
            }
        ],
    )
    assert duplicate == _single_issue(reversed_result, "allocation.duplicate_id")
    assert result.issues == reversed_result.issues


def test_matching_asset_aliases_and_broker_names_do_not_define_identity() -> None:
    payload = _fixture(REBALANCER_FIXTURE)
    asset_a = _find_row(payload["assets"], "asset_id", "asset-a")
    asset_b = _find_row(payload["assets"], "asset_id", "asset-b")
    asset_b["identity"]["name"] = asset_a["identity"]["name"]
    asset_b["identity"]["ticker"] = asset_a["identity"]["ticker"]

    broker_alpha = _find_row(payload["brokers"], "broker_id", "broker-alpha")
    broker_beta = _find_row(payload["brokers"], "broker_id", "broker-beta")
    broker_beta["identity"] = {
        "kind": "domain_broker",
        "source_broker_id": "synthetic-broker-distinct",
        "name": broker_alpha["identity"]["name"],
        "active": True,
    }

    result = _normalize_payload("rebalancer", payload)

    assert not [issue for issue in result.issues if issue.code == "allocation.duplicate_id"]


def test_duplicate_exposure_key_is_canonical_and_typed() -> None:
    payload = _fixture(PAC_FIXTURE)
    asset = _find_row(payload["assets"], "asset_id", "asset-one")
    exposure = next(item for item in asset["exposures"] if item["dimension"] == "asset_type")
    duplicate_exposure = deepcopy(exposure)
    duplicate_exposure["label"] = "Duplicate equity label"
    asset["exposures"].append(duplicate_exposure)

    result = _normalize_payload("pac", payload)
    reversed_payload = deepcopy(payload)
    reversed_asset = _find_row(reversed_payload["assets"], "asset_id", "asset-one")
    reversed_asset["exposures"] = list(reversed(reversed_asset["exposures"]))
    reversed_result = _normalize_payload("pac", reversed_payload)

    duplicate = _assert_duplicate_issue(
        result,
        expected_path=_field_wire_path(
            "assets",
            "asset",
            "asset-one",
            "exposures.dimension_category",
        ),
        expected_params=[
            {"kind": "id", "name": "category_id", "value": "equity"},
            {
                "kind": "text",
                "name": "dimension",
                "value": "asset_type",
            },
        ],
    )
    assert duplicate == _single_issue(reversed_result, "allocation.duplicate_id")
    assert result.issues == reversed_result.issues


def test_same_exposure_category_in_different_dimensions_remains_ready() -> None:
    payload = _fixture(PAC_FIXTURE)
    asset = _find_row(payload["assets"], "asset_id", "asset-one")
    sector = next(item for item in asset["exposures"] if item["dimension"] == "sector")
    sector["category_id"] = "equity"
    sector["label"] = "Equity category reused in another dimension"

    result = _normalize_payload("pac", payload)

    assert result.availability == "ready"
    assert result.issues == ()
    assert result.normalized is not None


def test_duplicate_holding_pair_is_canonical_typed_and_suppresses_wac_lookup() -> None:
    payload = _fixture(REBALANCER_FIXTURE)
    holding_a = _find_row(payload["holdings"], "holding_id", "holding-a-alpha")
    holding_d = _find_row(payload["holdings"], "holding_id", "holding-d-alpha")
    holding_d["asset_id"] = holding_a["asset_id"]
    holding_d["broker_id"] = holding_a["broker_id"]

    result = _normalize_payload("rebalancer", payload)
    reversed_payload = deepcopy(payload)
    reversed_payload["holdings"] = list(reversed(reversed_payload["holdings"]))
    reversed_result = _normalize_payload("rebalancer", reversed_payload)

    duplicate = _assert_duplicate_issue(
        result,
        expected_path=_field_wire_path(
            "holdings",
            "holding",
            "holding-a-alpha",
            "asset_id.broker_id",
        ),
        expected_params=[
            {"kind": "id", "name": "asset_id", "value": "asset-a"},
            {"kind": "id", "name": "broker_id", "value": "broker-alpha"},
        ],
    )
    assert duplicate == _single_issue(reversed_result, "allocation.duplicate_id")
    assert result.issues == reversed_result.issues
    assert not [issue for issue in result.issues if issue.code == "allocation.wac_missing"]


def test_holdings_may_share_only_asset_or_only_broker() -> None:
    payload = _ready_rebalancer_payload()
    holding_d = _find_row(payload["holdings"], "holding_id", "holding-d-alpha")
    holding_d["asset_id"] = "asset-b"

    result = _normalize_payload("rebalancer", payload)

    assert result.availability == "ready"
    assert result.issues == ()
    assert result.normalized is not None
    holding_pairs = {(holding.asset_id, holding.broker_id) for holding in result.normalized.holdings}
    assert {
        ("asset-a", "broker-alpha"),
        ("asset-b", "broker-alpha"),
        ("asset-b", "broker-beta"),
    } <= holding_pairs


def _replace_with_duplicate_exposure_key(
    scenario: ExactPlannerScenario,
) -> object:
    asset = next(item for item in scenario.assets if item.asset_id == "asset-a")
    exposure = next(item for item in asset.exposures if item.dimension == "asset_type")
    return replace(asset, exposures=(exposure, exposure))


def _replace_with_duplicate_domain_asset_source(
    scenario: ExactPlannerScenario,
) -> object:
    asset_a = next(item for item in scenario.assets if item.asset_id == "asset-a")
    asset_b = next(item for item in scenario.assets if item.asset_id == "asset-b")
    duplicate_asset = replace(
        asset_b,
        source_asset_id=asset_a.source_asset_id,
    )
    assets = tuple(duplicate_asset if item.asset_id == duplicate_asset.asset_id else item for item in scenario.assets)
    return replace(scenario, assets=assets)


def _replace_with_duplicate_domain_broker_source(
    scenario: ExactPlannerScenario,
) -> object:
    broker_alpha = next(item for item in scenario.brokers if item.broker_id == "broker-alpha")
    broker_beta = next(item for item in scenario.brokers if item.broker_id == "broker-beta")
    duplicate_broker = replace(
        broker_beta,
        identity_kind="domain",
        source_broker_id=broker_alpha.source_broker_id,
        active=True,
    )
    brokers = tuple(duplicate_broker if item.broker_id == duplicate_broker.broker_id else item for item in scenario.brokers)
    return replace(scenario, brokers=brokers)


def _replace_with_duplicate_holding_pair(
    scenario: ExactPlannerScenario,
) -> object:
    holding_a = next(item for item in scenario.holdings if item.holding_id == "holding-a-alpha")
    holding_d = next(item for item in scenario.holdings if item.holding_id == "holding-d-alpha")
    duplicate_holding = replace(
        holding_d,
        asset_id=holding_a.asset_id,
        broker_id=holding_a.broker_id,
    )
    holdings = tuple(duplicate_holding if item.holding_id == duplicate_holding.holding_id else item for item in scenario.holdings)
    return replace(scenario, holdings=holdings)


EXACT_MODEL_DUPLICATE_CASES = (
    pytest.param(
        _replace_with_duplicate_exposure_key,
        "asset exposures must not contain duplicate keys",
        id="exposure-key",
    ),
    pytest.param(
        _replace_with_duplicate_domain_asset_source,
        "domain asset source identities must not contain duplicate values",
        id="domain-asset-source",
    ),
    pytest.param(
        _replace_with_duplicate_domain_broker_source,
        "domain broker source identities must not contain duplicate values",
        id="domain-broker-source",
    ),
    pytest.param(
        _replace_with_duplicate_holding_pair,
        "holding Asset×Broker identities must not contain duplicate values",
        id="holding-pair",
    ),
)


@pytest.mark.parametrize(
    ("mutation", "message"),
    EXACT_MODEL_DUPLICATE_CASES,
)
def test_immutable_exact_models_reject_duplicate_semantic_identities(
    mutation: Callable[[ExactPlannerScenario], object],
    message: str,
) -> None:
    scenario = _ready_rebalancer_scenario()

    with pytest.raises(ValueError, match=message):
        mutation(scenario)
