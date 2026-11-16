"""Focused exact-normalization contract tests for Planner v2."""

from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast, get_args

import pytest

from backend.app.schemas.pac_allocator.base import PlannerIssueCode
from backend.app.schemas.pac_allocator.exact import ExactRatio as WireExactRatio
from backend.app.schemas.pac_allocator.exact import FiniteDecimal
from backend.app.schemas.pac_allocator.issues import PlannerIssue, PlannerIssuePath
from backend.app.schemas.pac_allocator.request import PlannerFundingRouteInput
from backend.app.schemas.pac_allocator.results import PAC_PLAN_INPUT_ADAPTER, REBALANCER_PLAN_INPUT_ADAPTER
from backend.app.services.financial_math.fx_rates import oriented_rate
from backend.app.services.pac_allocator import normalize
from backend.app.services.pac_allocator.evaluation.evaluator import build_exact_policy_view
from backend.app.services.pac_allocator.evaluation.reachability import fx_decision_specs
from backend.app.services.pac_allocator.evaluation.scenario import build_scenario_index
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
from backend.app.services.pac_allocator.models import FIDELITY_LEVEL_WEIGHTS, ExactFeeSchedule, ExactMoney, ExactPlannerScenario
from backend.app.services.pac_allocator.normalize import (
    PlannerV2NormalizationResult,
    _deposit_id,
    currency_minor_unit,
    exact_number_to_ratio,
    normalize_pac_plan,
    normalize_planner_request,
    normalize_rebalancer_plan,
)
from backend.app.services.pac_allocator.numeric import ExactRatio
from backend.test_scripts.test_services._pac_synthetic_requests import (
    FX_TRIANGLE,
    amount_limit,
    asset_entry,
    cash_entry,
    fx_conversion_request,
    fx_two_assets_one_pair_request,
    fx_two_brokers_request,
    fx_two_sources_request,
    fx_two_way_request,
    share_limit,
)

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "pac_allocator"
PAC_FIXTURE = "pac_plan_request.min.2-0-0.json"
REBALANCER_FIXTURE = "rebalancer_plan_request.medium.2-0-0.json"

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
    # Contract compaction withdrew `quote.freshness`; the warning stays a source-side fact
    # about the quote, so it points at a quote field that still exists.
    return _source_issue(
        "allocation.provenance_stale_confirmed",
        kind="info",
        severity="warning",
        path=field_path(
            "assets",
            "asset",
            "asset-one",
            "quote.provenance_id",
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
        (scenario.assets, "asset_id"),
        (scenario.brokers, "broker_id"),
        (scenario.holdings, "holding_id"),
        (scenario.existing_cash, "cash_id"),
        (scenario.contributions, "contribution_id"),
        (scenario.funding_routes, "route_id"),
        (scenario.order_routes, "route_id"),
        (scenario.fx_rates, "pair_key"),
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
    payload["fx_rates"]["EUR/USD"] = value


RANGE_MUTATORS: dict[str, Callable[[JsonObject, str], None]] = {
    "price": _mutate_price,
    "quote-basis": _mutate_quote_basis,
    "exposure-weight": _mutate_exposure_weight,
    "target-weight": _mutate_target_weight,
    "target-total": _mutate_target_weight,
    "economic-share": _mutate_economic_share,
    "planning-quantity": _mutate_planning_quantity,
    "cash-selection": _mutate_cash_selection,
    "fx-rate": _mutate_fx_rate,
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
    # NOTE: value is "-1", not "0" -- REBALANCER_FIXTURE holds asset-c (USD)
    # against a EUR valuation_currency, so validate_current_portfolio's own
    # fx_rate("USD", "EUR") call takes this same EUR/USD pair's *reciprocal*.
    # A literal "0" makes that reciprocal computation divide by zero and
    # crash before this test's `nonpositive_fx_rate` issue assertion is even
    # reached (see final report -- reported as a production concern, not
    # fixed here). "-1" is equally nonpositive and exercises the same issue
    # path without hitting that unrelated crash.
    pytest.param(
        "rebalancer",
        "fx-rate",
        "-1",
        "allocation.nonpositive_fx_rate",
        _field_wire_path("fx", "fx_rate", "EUR/USD", "rate"),
        id="fx-rate",
    ),
    # «tax-rate» left with B3 (project 67): the normalizer reads the ``tax`` section from C1-C2 on, which brings the case back.
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


# C-76: each negative cash amount is reported on the field that holds it, so the
# form points at the amount to fix; a selection above the available amount is
# reported only when neither amount is negative, and zero is valid for both.
CASH_AMOUNT_ISSUE_CODES = frozenset(
    {
        "allocation.negative_cash_unsupported",
        "allocation.cash_selection_invalid",
    }
)

CASH_AMOUNT_CASES = (
    pytest.param(
        "100",
        "-1",
        (("allocation.negative_cash_unsupported", "selected"),),
        id="negative-selected",
    ),
    pytest.param(
        "-1",
        "0",
        (("allocation.negative_cash_unsupported", "available"),),
        id="negative-available",
    ),
    pytest.param(
        "-1",
        "-1",
        (
            ("allocation.negative_cash_unsupported", "available"),
            ("allocation.negative_cash_unsupported", "selected"),
        ),
        id="both-negative",
    ),
    pytest.param(
        "100",
        "150",
        (("allocation.cash_selection_invalid", "selected"),),
        id="selection-above-available",
    ),
    pytest.param("100", "0", (), id="zero-selection"),
    pytest.param("0", "0", (), id="zero-cash"),
)


def _mutate_cash_amounts(payload: JsonObject, available: str, selected: str) -> None:
    cash = _find_row(
        payload["existing_cash"],
        "cash_id",
        "cash-broker-one-eur",
    )
    cash["available"]["amount"] = available
    cash["selected"]["amount"] = selected


def _issue_order(issue: PlannerIssue) -> str:
    return json.dumps(issue.model_dump(mode="json"), sort_keys=True)


@pytest.mark.parametrize(
    ("available", "selected", "expected"),
    CASH_AMOUNT_CASES,
)
def test_cash_amount_issues_name_the_field_that_is_wrong(
    available: str,
    selected: str,
    expected: tuple[tuple[PlannerIssueCode, str], ...],
) -> None:
    """A negative amount is reported on its own path: `available` when the
    available amount is negative, `selected` when the amount to use is, one
    issue each when both are. Every cash-amount issue the request produced is
    compared, whole, with the normalizer's own definition of that code, so a
    missing, extra or misplaced issue all fail here.
    """
    payload = _fixture(PAC_FIXTURE)
    _mutate_cash_amounts(payload, available, selected)

    result = _normalize_payload("pac", payload)

    found = sorted(
        (issue for issue in result.issues if issue.code in CASH_AMOUNT_ISSUE_CODES),
        key=_issue_order,
    )
    wanted = sorted(
        (_w1_issue(code, field_path("cash", "cash", "cash-broker-one-eur", field)) for code, field in expected),
        key=_issue_order,
    )
    assert found == wanted


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
    return payload


def _rebalancer_fixture_without_mismatched_route_c_alpha_buy() -> JsonObject:
    """A fresh REBALANCER_FIXTURE copy with route-c-alpha-buy dropped.

    route-c-alpha-buy (asset-c, quote currency USD) references fee schedule
    fee-alpha-eur-buy (EUR), which is shared with three EUR-asset buy routes
    at broker-alpha and so cannot be recolored to USD without breaking those.
    Under the "fees always in the asset's own quote currency" rule this route
    alone raises allocation.currency_mismatch; every caller of this helper
    only exercises broker-alpha/asset-a/b/d or the inactive-Broker surfaces,
    never asset-c (whose only holding is at broker-beta, backed by the
    correctly-USD-denominated route-c-beta-buy), so dropping it is safe.
    """
    payload = _fixture(REBALANCER_FIXTURE)
    payload["order_routes"] = [route for route in payload["order_routes"] if route["route_id"] != "route-c-alpha-buy"]
    return payload


def _inactive_executable_payload(
    trigger: str,
) -> tuple[str, JsonObject, str]:
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


@pytest.mark.parametrize(
    "trigger",
    (
        pytest.param("capability", id="capability"),
        pytest.param("funding-route", id="funding-route"),
        pytest.param("buy-route", id="buy-route"),
        # «sell-route» waits for C1 (project 67): until then no Rebalancer request with a sale route passes the schema (S1).
        # NOTE: "fx-route" was deleted -- it exercised a Broker becoming
        # "executable" solely by hosting an FX route/quote object. FX facts
        # are now global, broker-less `ExactFxRate` entries in the canonical
        # fx_rates map, so no FX concept can make a Broker executable anymore;
        # there is nothing left for this trigger to construct or assert.
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
    assert len(schema_codes) == 78
    assert len(set(schema_codes)) == 78
    # FX conversion fix: an incoherent cross rate is a closed code of its own.
    assert "allocation.fx_rate_inconsistent" in schema_codes
    # Contract compaction: the planner reads neither a quote date nor a freshness any more.
    assert not {"allocation.price_date_missing", "allocation.stale_age_negative", "allocation.stale_observation_not_accepted"} & set(schema_codes)
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
        "allocation.currency_mismatch": _field_wire_path(
            "routing",
            "order_route",
            "route-c-alpha-buy",
            "fee_schedule_id",
        ),
    }
    for code, expected_path in expected_paths.items():
        assert _issue_wire_path(_single_issue(result, code)) == expected_path
    # The ``tax`` section is not read before C1-C2 (B3 of project 67): no tax issue, whatever it holds.
    assert not [issue for issue in result.issues if issue.code.startswith("portfolio_rebalancer.tax")]


def _ready_rebalancer_payload() -> JsonObject:
    payload = _rebalancer_fixture_without_mismatched_route_c_alpha_buy()
    _find_row(payload["holdings"], "holding_id", "holding-a-alpha")["economic_share"] = "1"
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


# ---------------------------------------------------------------------------
# R4.9 — each Broker's conversion mode travels from the request into the exact
# model untouched, and the exact model admits only the two published modes.
# ---------------------------------------------------------------------------

CONVERSION_MODES = ("manual", "automatic")


def _ready_pac_payload() -> JsonObject:
    return _fixture(PAC_FIXTURE)


CONVERSION_MODE_CARRY_CASES = tuple(
    pytest.param(product, build_payload, broker_id, mode, id=f"{product}-{broker_id}-{mode}")
    for product, build_payload, broker_id in (
        ("pac", _ready_pac_payload, "broker-one"),
        ("rebalancer", _ready_rebalancer_payload, "broker-alpha"),
        ("rebalancer", _ready_rebalancer_payload, "broker-beta"),
    )
    for mode in CONVERSION_MODES
)


@pytest.mark.parametrize(
    ("product", "build_payload", "broker_id", "mode"),
    CONVERSION_MODE_CARRY_CASES,
)
def test_normalization_carries_each_broker_conversion_mode_into_the_exact_model(
    product: str,
    build_payload: Callable[[], JsonObject],
    broker_id: str,
    mode: str,
) -> None:
    payload = build_payload()
    _find_row(payload["brokers"], "broker_id", broker_id)["conversion_mode"] = mode
    requested = {row["broker_id"]: row["conversion_mode"] for row in payload["brokers"]}

    result = _normalize_payload(product, payload)

    assert result.availability == "ready", result.issues
    assert result.normalized is not None
    normalized = {broker.broker_id: broker.conversion_mode for broker in result.normalized.brokers}
    assert normalized[broker_id] == mode
    # Per Broker, not per request: every other Broker keeps the mode it asked for.
    assert normalized == requested


@pytest.mark.parametrize("mode", CONVERSION_MODES)
def test_exact_broker_accepts_each_published_conversion_mode(mode: str) -> None:
    broker = next(item for item in _ready_rebalancer_scenario().brokers if item.broker_id == "broker-alpha")

    assert replace(broker, conversion_mode=mode).conversion_mode == mode


@pytest.mark.parametrize(
    "mode",
    (
        pytest.param("Manual", id="capitalised"),
        pytest.param("auto", id="abbreviated"),
        pytest.param("", id="empty"),
        pytest.param(None, id="none"),
    ),
)
def test_exact_broker_rejects_an_unknown_conversion_mode(mode: object) -> None:
    broker = next(item for item in _ready_rebalancer_scenario().brokers if item.broker_id == "broker-alpha")

    with pytest.raises(ValueError, match="unknown Broker conversion mode"):
        replace(broker, conversion_mode=mode)


# ---------------------------------------------------------------------------
# C0b.3 — an Asset's exposures may not sum above one within a dimension.
# ---------------------------------------------------------------------------

EXPOSURE_WEIGHT_WIRE_PATH = _field_wire_path("assets", "asset", "asset-one", "exposures.weight")
EXPOSURE_TOTAL_CODE: PlannerIssueCode = "allocation.exposure_total_exceeds_one"
FIXTURE_EXPOSURE_CATEGORIES = (
    ("asset_type", "equity"),
    ("sector", "broad"),
    ("geography", "unknown"),
)


def _exposure(dimension: str, category_id: str, weight: str) -> JsonObject:
    return {
        "dimension": dimension,
        "category_id": category_id,
        "label": f"{dimension} {category_id}",
        "weight": weight,
        "provenance_id": "prov-manual",
    }


def _pac_payload_with_exposures(*exposures: JsonObject) -> JsonObject:
    payload = _fixture(PAC_FIXTURE)
    asset = _find_row(payload["assets"], "asset_id", "asset-one")
    asset["exposures"] = [deepcopy(exposure) for exposure in exposures]
    return payload


def _split_dimension(dimension: str, category_id: str, weights: tuple[str, ...]) -> list[JsonObject]:
    return [_exposure(dimension, category_id if index == 0 else f"{category_id}-{index}", weight) for index, weight in enumerate(weights)]


def _exposure_total_issues(result: PlannerV2NormalizationResult) -> list[PlannerIssue]:
    return [issue for issue in result.issues if issue.code == EXPOSURE_TOTAL_CODE]


def _dimension_params(issue: PlannerIssue) -> list[JsonObject]:
    return [param.model_dump(mode="json") for param in issue.params]


def test_exposure_dimension_total_above_one_is_one_typed_invalid_issue() -> None:
    payload = _pac_payload_with_exposures(
        _exposure("asset_type", "equity", "1"),
        _exposure("sector", "broad", "0.7"),
        _exposure("sector", "tech", "0.5"),
        _exposure("geography", "unknown", "1"),
    )

    result = _normalize_payload("pac", payload)
    issue = _single_issue(result, EXPOSURE_TOTAL_CODE)

    assert result.availability == "invalid"
    assert result.ready is False
    assert result.normalized is None
    assert tuple(row.code for row in result.issues) == (EXPOSURE_TOTAL_CODE,)
    assert issue.model_dump(mode="json") == {
        "code": EXPOSURE_TOTAL_CODE,
        "severity": "error",
        "kind": "invalid",
        "path": EXPOSURE_WEIGHT_WIRE_PATH,
        "message_key": EXPOSURE_TOTAL_CODE,
        "params": [{"kind": "text", "name": "dimension", "value": "sector"}],
    }
    assert normalizer_issue_definition(EXPOSURE_TOTAL_CODE).kind == "invalid"


@pytest.mark.parametrize(
    "weights",
    (
        pytest.param(("0.5", "0.5"), id="exactly-one"),
        pytest.param(("0.3333", "0.6667"), id="exactly-one-at-four-decimals"),
        pytest.param(("0.3", "0.2"), id="below-one-keeps-a-residual"),
        pytest.param(("0", "0"), id="zero"),
    ),
)
def test_exposure_dimension_total_up_to_one_is_accepted(weights: tuple[str, ...]) -> None:
    payload = _pac_payload_with_exposures(
        _exposure("asset_type", "equity", "1"),
        *_split_dimension("sector", "broad", weights),
        _exposure("geography", "unknown", "1"),
    )

    result = _normalize_payload("pac", payload)

    assert result.availability == "ready"
    assert result.issues == ()


@pytest.mark.parametrize(
    "weights",
    (
        pytest.param(("1.25", "0.5"), id="above-one-weight"),
        pytest.param(("-0.25", "1", "0.75"), id="negative-weight-with-total-above-one"),
    ),
)
def test_out_of_range_exposure_weight_is_the_only_issue_for_its_dimension(weights: tuple[str, ...]) -> None:
    payload = _pac_payload_with_exposures(
        _exposure("asset_type", "equity", "1"),
        *_split_dimension("sector", "broad", weights),
        _exposure("geography", "unknown", "1"),
    )

    result = _normalize_payload("pac", payload)
    issue = _single_issue(result, "allocation.exposure_weight_out_of_range")

    assert result.availability == "invalid"
    assert tuple(row.code for row in result.issues) == ("allocation.exposure_weight_out_of_range",)
    assert _issue_wire_path(issue) == EXPOSURE_WEIGHT_WIRE_PATH
    assert _exposure_total_issues(result) == []


@pytest.mark.parametrize("over_dimension", ("asset_type", "sector", "geography"))
def test_exposure_total_issue_names_only_the_dimension_above_one(over_dimension: str) -> None:
    exposures: list[JsonObject] = []
    for dimension, category_id in FIXTURE_EXPOSURE_CATEGORIES:
        weights = ("0.7", "0.5") if dimension == over_dimension else ("0.6", "0.4")
        exposures.extend(_split_dimension(dimension, category_id, weights))
    payload = _pac_payload_with_exposures(*exposures)

    result = _normalize_payload("pac", payload)
    issue = _single_issue(result, EXPOSURE_TOTAL_CODE)

    assert result.availability == "invalid"
    assert tuple(row.code for row in result.issues) == (EXPOSURE_TOTAL_CODE,)
    assert _issue_wire_path(issue) == EXPOSURE_WEIGHT_WIRE_PATH
    assert _dimension_params(issue) == [{"kind": "text", "name": "dimension", "value": over_dimension}]


def test_exposure_totals_are_checked_per_dimension() -> None:
    payload = _pac_payload_with_exposures(
        *_split_dimension("asset_type", "equity", ("0.8", "0.8")),
        *_split_dimension("sector", "broad", ("1.5", "0.5")),
        *_split_dimension("geography", "unknown", ("0.9", "0.2")),
    )

    result = _normalize_payload("pac", payload)

    assert result.availability == "invalid"
    # The out-of-range sector weight suppresses only the sector total.
    _single_issue(result, "allocation.exposure_weight_out_of_range")
    totals = _exposure_total_issues(result)
    assert [_dimension_params(issue) for issue in totals] == [
        [{"kind": "text", "name": "dimension", "value": "asset_type"}],
        [{"kind": "text", "name": "dimension", "value": "geography"}],
    ]
    assert all(_issue_wire_path(issue) == EXPOSURE_WEIGHT_WIRE_PATH for issue in totals)


@pytest.mark.parametrize(
    ("weights", "expects_total_issue"),
    (
        pytest.param(("0.6", "0.6"), True, id="duplicates-sum-above-one"),
        pytest.param(("0.5", "0.5"), False, id="duplicates-sum-to-one"),
    ),
)
def test_duplicate_exposure_rows_still_count_toward_the_dimension_total(
    weights: tuple[str, str],
    expects_total_issue: bool,
) -> None:
    payload = _pac_payload_with_exposures(
        _exposure("asset_type", "equity", "1"),
        *(_exposure("sector", "broad", weight) for weight in weights),
        _exposure("geography", "unknown", "1"),
    )

    result = _normalize_payload("pac", payload)

    assert result.availability == "invalid"
    _single_issue(result, "allocation.duplicate_id")
    totals = _exposure_total_issues(result)
    if expects_total_issue:
        assert [_dimension_params(issue) for issue in totals] == [[{"kind": "text", "name": "dimension", "value": "sector"}]]
    else:
        assert totals == []


# ---------------------------------------------------------------------------
# C0b.1 — the currency quantum is CLDR's, via babel; the request carries none.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("currency", "expected"),
    (
        pytest.param("JPY", ExactRatio(1), id="jpy-zero-digits"),
        pytest.param("EUR", ExactRatio(1, 100), id="eur-cldr-default-two-digits"),
        pytest.param("USD", ExactRatio(1, 100), id="usd-two-digits"),
        pytest.param("KWD", ExactRatio(1, 1000), id="kwd-three-digits"),
    ),
)
def test_currency_minor_unit_is_the_cldr_quantum(currency: str, expected: ExactRatio) -> None:
    assert currency_minor_unit(currency) == expected


def test_normalized_scenario_derives_every_referenced_currency_quantum_from_babel() -> None:
    payload = _fixture(PAC_FIXTURE)
    assert "currency_specs" not in payload
    payload["fx_rates"] = {"EUR/JPY": "160", "EUR/KWD": "0.33"}

    result = _normalize_payload("pac", payload)

    assert result.availability == "ready"
    scenario = result.normalized
    assert scenario is not None
    assert tuple((spec.currency, spec.minor_unit) for spec in scenario.currency_specs) == (
        ("EUR", ExactRatio(1, 100)),
        ("JPY", ExactRatio(1)),
        ("KWD", ExactRatio(1, 1000)),
    )


# ---------------------------------------------------------------------------
# Contract compaction — the wire may omit what has a default or is optional;
# the normalizer resolves it into an exact scenario the engine already reads
# (no transfer cap = the whole selected source; F1-extended fee instances).
# ---------------------------------------------------------------------------

COMPACT_PAC_FIXTURE = "pac_plan_request.compact.2-0-0.json"
CANDIDATE_MAX_PAC_FIXTURE = "pac_plan_request.candidate-max.2-0-0.json"
PAC_ROUTE_ID = "route-asset-one-broker-one-buy"
PAC_CAPABILITY_ID = "cap-broker-one-eur-whole"
PAC_FEE_SCHEDULE_ID = "fee-broker-one-eur-buy"
ALPHA_CAPABILITY_ID = "cap-alpha-eur-whole"


def _money(amount: ExactRatio, currency: str) -> ExactMoney:
    return ExactMoney(amount=amount, currency=currency)


def _zero_fee_instance(fee_schedule_id: str, capability_id: str, currency: str, rate: ExactRatio = ExactRatio(0)) -> ExactFeeSchedule:
    return ExactFeeSchedule(
        fee_schedule_id=fee_schedule_id,
        capability_id=capability_id,
        side="buy",
        fixed_fee=_money(ExactRatio(0), currency),
        proportional_rate=rate,
        minimum_fee=_money(ExactRatio(0), currency),
        maximum_fee=None,
    )


def _ready_scenario(product: str, payload: JsonObject) -> ExactPlannerScenario:
    result = _normalize_payload(product, payload)
    assert result.availability == "ready", tuple((issue.code, _issue_wire_path(issue)) for issue in result.issues)
    assert result.issues == ()
    assert result.normalized is not None
    return result.normalized


def _exact_fee_schedules(scenario: ExactPlannerScenario, broker_id: str) -> tuple[ExactFeeSchedule, ...]:
    return next(row for row in scenario.brokers if row.broker_id == broker_id).fee_schedules


def _route_fee_schedule_ids(scenario: ExactPlannerScenario) -> dict[str, str]:
    return {route.route_id: route.fee_schedule_id for route in scenario.order_routes}


def _ready_rebalancer_payload_with_every_route() -> JsonObject:
    """`_ready_rebalancer_payload()` with route-c-alpha-buy (a USD asset at broker-alpha) restored."""
    payload = _ready_rebalancer_payload()
    payload["order_routes"] = _fixture(REBALANCER_FIXTURE)["order_routes"]
    return payload


def _pac_payload_with_uncapped_cash_funding_route() -> JsonObject:
    payload = _ready_pac_payload()
    cash = _find_row(payload["existing_cash"], "cash_id", "cash-broker-one-eur")
    # 8 available, 5 selected: an absent cap must take the *selected* amount.
    cash["available"]["amount"] = "8.00"
    payload["funding_routes"] = [
        {
            "funding_route_id": "fund-cash-broker-one",
            "source": {"kind": "existing_cash", "cash_id": "cash-broker-one-eur"},
            "broker_id": "broker-one",
            "currency": "EUR",
            "provenance_id": "prov-manual",
        }
    ]
    return payload


ABSENT_TRANSFER_CAP_CASES = (
    pytest.param(
        "pac",
        _pac_payload_with_uncapped_cash_funding_route,
        {"fund-cash-broker-one": (_money(ExactRatio(5), "EUR"), 0)},
        id="existing-cash-takes-the-selected-amount",
    ),
    # The Rebalancer's deposits are generated without a cap: ``test_rebalancer_deposits_and_lanes_are_generated``.
)


@pytest.mark.parametrize(("product", "build_payload", "expected"), ABSENT_TRANSFER_CAP_CASES)
def test_absent_transfer_cap_resolves_to_the_whole_selected_source(
    product: str,
    build_payload: Callable[[], JsonObject],
    expected: dict[str, tuple[ExactMoney, int]],
) -> None:
    scenario = _ready_scenario(product, build_payload())

    assert {route.route_id: (route.transfer_cap, route.priority) for route in scenario.funding_routes} == expected


def test_compact_twin_buy_route_without_schedule_gets_the_implicit_zero_instance() -> None:
    implicit_id = f"~zero~{PAC_CAPABILITY_ID}~EUR"

    scenario = _ready_scenario("pac", _fixture(COMPACT_PAC_FIXTURE))

    assert _exact_fee_schedules(scenario, "broker-one") == (_zero_fee_instance(implicit_id, PAC_CAPABILITY_ID, "EUR"),)
    assert _route_fee_schedule_ids(scenario) == {PAC_ROUTE_ID: implicit_id}


def test_buy_routes_without_schedule_share_one_implicit_zero_instance_per_capability_and_currency() -> None:
    payload = _ready_rebalancer_payload()
    for route_id in ("route-a-alpha-buy", "route-b-alpha-buy"):
        del _find_row(payload["order_routes"], "route_id", route_id)["fee_schedule_id"]
    implicit_id = f"~zero~{ALPHA_CAPABILITY_ID}~EUR"

    scenario = _ready_scenario("rebalancer", payload)

    schedules = _exact_fee_schedules(scenario, "broker-alpha")
    assert tuple((row.capability_id, row.side, row.fee_schedule_id) for row in schedules) == (
        (ALPHA_CAPABILITY_ID, "buy", "fee-alpha-eur-buy"),
        (ALPHA_CAPABILITY_ID, "buy", implicit_id),
        (ALPHA_CAPABILITY_ID, "sell", "fee-alpha-eur-sell"),
    )
    assert next(row for row in schedules if row.fee_schedule_id == implicit_id) == _zero_fee_instance(implicit_id, ALPHA_CAPABILITY_ID, "EUR")
    routes = _route_fee_schedule_ids(scenario)
    assert (routes["route-a-alpha-buy"], routes["route-b-alpha-buy"]) == (implicit_id, implicit_id)
    # The SELL schedule stays on the Broker; no route uses it until C1 (project 67) lets a sale route in.
    assert routes["route-d-alpha-buy"] == "fee-alpha-eur-buy"


def test_currency_free_schedule_gets_one_instance_per_quote_currency_that_uses_it() -> None:
    payload = _ready_rebalancer_payload_with_every_route()
    alpha = _find_row(payload["brokers"], "broker_id", "broker-alpha")
    alpha["fee_schedules"] = [
        _find_row(alpha["fee_schedules"], "fee_schedule_id", "fee-alpha-eur-sell"),
        # No money field: the schedule takes the quote currency of each route using it.
        {"fee_schedule_id": "fee-alpha-buy", "capability_id": ALPHA_CAPABILITY_ID, "side": "buy", "rate": "0.002"},
        # Currency-free and used by no route: no instance at all.
        {"fee_schedule_id": "fee-alpha-spare-buy", "capability_id": ALPHA_CAPABILITY_ID, "side": "buy", "rate": "0.01"},
    ]
    for route in payload["order_routes"]:
        if route["fee_schedule_id"] == "fee-alpha-eur-buy":
            route["fee_schedule_id"] = "fee-alpha-buy"

    scenario = _ready_scenario("rebalancer", payload)

    alpha_schedules = _exact_fee_schedules(scenario, "broker-alpha")
    sell_schedule = next(row for row in alpha_schedules if row.fee_schedule_id == "fee-alpha-eur-sell")
    assert alpha_schedules == (
        _zero_fee_instance("fee-alpha-buy~EUR", ALPHA_CAPABILITY_ID, "EUR", ExactRatio(1, 500)),
        _zero_fee_instance("fee-alpha-buy~USD", ALPHA_CAPABILITY_ID, "USD", ExactRatio(1, 500)),
        sell_schedule,
    )
    # Currency-bearing schedules keep the caller's ID.
    assert tuple(row.fee_schedule_id for row in _exact_fee_schedules(scenario, "broker-beta")) == (
        "fee-beta-eur-buy",
        "fee-beta-eur-sell",
        "fee-beta-usd-buy",
        "fee-beta-usd-sell",
    )
    assert _route_fee_schedule_ids(scenario) == {
        "route-a-alpha-buy": "fee-alpha-buy~EUR",
        "route-b-alpha-buy": "fee-alpha-buy~EUR",
        "route-b-beta-buy": "fee-beta-eur-buy",
        "route-c-alpha-buy": "fee-alpha-buy~USD",
        "route-c-beta-buy": "fee-beta-usd-buy",
        "route-d-alpha-buy": "fee-alpha-buy~EUR",
        "route-d-beta-buy": "fee-beta-eur-buy",
    }


def _pac_payload_with_fee_schedule(**money_fields: JsonObject | str) -> JsonObject:
    payload = _ready_pac_payload()
    broker = _find_row(payload["brokers"], "broker_id", "broker-one")
    broker["fee_schedules"] = [
        {
            "fee_schedule_id": PAC_FEE_SCHEDULE_ID,
            "capability_id": PAC_CAPABILITY_ID,
            "side": "buy",
            **money_fields,
        }
    ]
    return payload


def _money_wire(amount: str, currency: str) -> JsonObject:
    return {"amount": amount, "currency": currency}


def _amount_cap_wire(amount: str, currency: str) -> JsonObject:
    return {"kind": "amount", "amount": _money_wire(amount, currency)}


PRESENT_MONEY_FIELD_CASES = (
    pytest.param(
        {"fixed_fee": _money_wire("1.50", "EUR")},
        (ExactRatio(3, 2), ExactRatio(0), ExactRatio(0), None),
        id="fixed-fee-only",
    ),
    pytest.param(
        {"variable_floor": _money_wire("0.50", "EUR"), "rate": "0.01"},
        (ExactRatio(0), ExactRatio(1, 100), ExactRatio(1, 2), None),
        id="variable-floor-only",
    ),
    pytest.param(
        # The absent floor counts as zero, so it cannot exceed the cap.
        {"variable_cap": _amount_cap_wire("2", "EUR"), "rate": "0.01"},
        (ExactRatio(0), ExactRatio(1, 100), ExactRatio(0), ExactRatio(2)),
        id="variable-cap-only",
    ),
)


@pytest.mark.parametrize(("money_fields", "expected"), PRESENT_MONEY_FIELD_CASES)
def test_schedule_currency_is_the_one_of_its_present_money_fields_and_absent_money_is_zero(
    money_fields: JsonObject,
    expected: tuple[ExactRatio, ExactRatio, ExactRatio, ExactRatio | None],
) -> None:
    fixed_fee, rate, minimum_fee, maximum_fee = expected

    scenario = _ready_scenario("pac", _pac_payload_with_fee_schedule(**money_fields))

    assert _exact_fee_schedules(scenario, "broker-one") == (
        ExactFeeSchedule(
            fee_schedule_id=PAC_FEE_SCHEDULE_ID,
            capability_id=PAC_CAPABILITY_ID,
            side="buy",
            fixed_fee=_money(fixed_fee, "EUR"),
            proportional_rate=rate,
            minimum_fee=_money(minimum_fee, "EUR"),
            maximum_fee=None if maximum_fee is None else _money(maximum_fee, "EUR"),
        ),
    )
    assert _route_fee_schedule_ids(scenario) == {PAC_ROUTE_ID: PAC_FEE_SCHEDULE_ID}


SCHEDULE_CURRENCY_MISMATCH_CASES = (
    pytest.param(
        {"fixed_fee": _money_wire("1", "EUR"), "variable_floor": _money_wire("0.50", "USD")},
        _field_wire_path("brokers", "broker", "broker-one", "fee_schedules"),
        id="fixed-eur-floor-usd",
    ),
    pytest.param(
        {"fixed_fee": _money_wire("1", "EUR"), "variable_cap": _amount_cap_wire("2", "USD")},
        _field_wire_path("brokers", "broker", "broker-one", "fee_schedules"),
        id="fixed-eur-cap-usd",
    ),
    pytest.param(
        # A currency-bearing schedule still has to match the route's quote currency.
        {"variable_floor": _money_wire("0.50", "USD")},
        _field_wire_path("routing", "order_route", PAC_ROUTE_ID, "fee_schedule_id"),
        id="usd-schedule-on-an-eur-route",
    ),
)


@pytest.mark.parametrize(("money_fields", "expected_path"), SCHEDULE_CURRENCY_MISMATCH_CASES)
def test_schedule_money_in_two_currencies_or_off_the_route_currency_is_a_currency_mismatch(
    money_fields: JsonObject,
    expected_path: JsonObject,
) -> None:
    payload = _pac_payload_with_fee_schedule(**money_fields)
    # The USD fee money needs FX coverage, otherwise `allocation.fx_rate_missing` (missing) would outrank the mismatch (invalid).
    payload["fx_rates"] = {**payload.get("fx_rates", {}), "EUR/USD": "1.10"}

    result = _normalize_payload("pac", payload)

    assert result.availability == "invalid"
    assert result.normalized is None
    blocking = tuple((issue.code, _issue_wire_path(issue)) for issue in result.issues if issue.severity == "error")
    assert blocking == (("allocation.currency_mismatch", expected_path),)


@pytest.mark.parametrize(
    "keep_schedules",
    (
        pytest.param(True, id="other-schedules-present"),
        pytest.param(False, id="broker-without-schedules"),
    ),
)
def test_dangling_buy_fee_schedule_id_still_reports_fee_schedule_missing(keep_schedules: bool) -> None:
    payload = _ready_pac_payload()
    if not keep_schedules:
        del _find_row(payload["brokers"], "broker_id", "broker-one")["fee_schedules"]
    _find_row(payload["order_routes"], "route_id", PAC_ROUTE_ID)["fee_schedule_id"] = "fee-nowhere"

    result = _normalize_payload("pac", payload)

    issue = _single_issue(result, "allocation.fee_schedule_missing")
    assert tuple(row.code for row in result.issues) == ("allocation.fee_schedule_missing",)
    assert result.availability == "needs_input"
    assert result.normalized is None
    assert _issue_wire_path(issue) == _field_wire_path("routing", "order_route", PAC_ROUTE_ID, "fee_schedule_id")


def test_missing_quote_reports_price_and_basis_but_no_quote_date() -> None:
    payload = _ready_pac_payload()
    _find_row(payload["assets"], "asset_id", "asset-one")["quote"] = None

    result = _normalize_payload("pac", payload)

    assert result.availability == "needs_input"
    assert result.normalized is None
    assert tuple((issue.code, _issue_wire_path(issue)) for issue in result.issues) == (
        ("allocation.price_missing", _field_wire_path("assets", "asset", "asset-one", "quote.amount")),
        ("allocation.quote_base_quantity_missing", _field_wire_path("assets", "asset", "asset-one", "quote.quote_base_quantity")),
    )


EXPLICIT_NORMALIZATION_CASES = (
    pytest.param("pac", _ready_pac_payload, id="pac-min"),
    pytest.param("pac", lambda: _fixture(CANDIDATE_MAX_PAC_FIXTURE), id="pac-candidate-max"),
    pytest.param("rebalancer", _ready_rebalancer_payload, id="rebalancer-medium-ready"),
)


@pytest.mark.parametrize(("product", "build_payload"), EXPLICIT_NORMALIZATION_CASES)
def test_defaults_omitted_dump_normalizes_exactly_like_the_explicit_request(
    product: str,
    build_payload: Callable[[], JsonObject],
) -> None:
    explicit = build_payload()
    adapter = PAC_PLAN_INPUT_ADAPTER if product == "pac" else REBALANCER_PLAN_INPUT_ADAPTER
    validated = adapter.validate_json(_wire(explicit), strict=True)
    compact = validated.model_dump(mode="json", exclude_defaults=True)
    assert compact != validated.model_dump(mode="json")

    assert _normalize_payload(product, compact) == _normalize_payload(product, explicit)


# ---------------------------------------------------------------------------
# FX coherence (FX conversion fix). A declared cross rate that, net of the
# spread, beats the triangle through the valuation currency is an FX arbitrage:
# converting c→q and valuing the credit at q→V would be worth more V than c→V
# directly. The evaluator used to meet it deep in the replay, as a negative
# spread loss, and raise. The normalizer now refuses it up front with
# `allocation.fx_rate_inconsistent`.
# The rule: for every BUY route quoted in q, and every cash-pool currency c ≠ q
# of its Broker (existing cash, funding routes, SELL-route quote currencies),
# skip when c or q is the valuation currency V or a needed rate is missing;
# otherwise it is a violation iff rate(c→q)·(1−spread)·rate(q→V) > rate(c→V),
# beyond the ten-decimal coherence band pinned further down.
# The comparison is strict, so the implied rate itself is coherent. The issue
# is reported once per pair, however many routes reach it.
# The planner-level cases, and the rounding-residual defect, live in
# test_pac_planner_planner.py.
# ---------------------------------------------------------------------------

FX_RATE_INCONSISTENT_CODE: PlannerIssueCode = "allocation.fx_rate_inconsistent"
# The one issue an incoherent CHF/USD raises (valuation EUR); its params are sorted by name.
CHF_USD_INCONSISTENT_ISSUE: JsonObject = {
    "code": FX_RATE_INCONSISTENT_CODE,
    "severity": "error",
    "kind": "invalid",
    "path": _field_wire_path("fx", "fx_rate", "CHF/USD", "rate"),
    "message_key": FX_RATE_INCONSISTENT_CODE,
    "params": [
        {"kind": "currency", "name": "destination_currency", "value": "USD"},
        {"kind": "id", "name": "pair", "value": "CHF/USD"},
        {"kind": "currency", "name": "source_currency", "value": "CHF"},
        {"kind": "currency", "name": "valuation_currency", "value": "EUR"},
    ],
}


def _issue_dumps(result: PlannerV2NormalizationResult) -> list[JsonObject]:
    return [issue.model_dump(mode="json") for issue in result.issues]


@pytest.mark.parametrize(
    ("funding_currency", "assets", "cross_rate", "spread"),
    (
        # The implied rate itself, 1.06 × 1.085: equality is coherent.
        pytest.param("CHF", [("USD", "10.00")], "1.1501", "0", id="implied-rate"),
        # 1.437625 × 0.8 = 1.1501 exactly: the spread brings the cross back onto the triangle.
        pytest.param("CHF", [("USD", "10.00")], "1.437625", "0.2", id="spread-boundary"),
        # The quote currency is the valuation currency: CHF→EUR is the direct rate, so there is no triangle.
        pytest.param("CHF", [("EUR", "10.00")], "1.16", "0", id="quote-is-valuation"),
        # An incoherent CHF/USD that no conversion of this plan uses is not reported.
        pytest.param("EUR", [("EUR", "10.00")], "1.1502", "0", id="unused-cross-rate"),
    ),
)
def test_coherent_or_unused_cross_rate_is_ready(
    funding_currency: str,
    assets: list[tuple[str, str]],
    cross_rate: str,
    spread: str,
) -> None:
    payload = fx_conversion_request(
        f"coherent-{funding_currency}-{cross_rate}-{spread}",
        funding_currency=funding_currency,
        assets=assets,
        fx_rates={**FX_TRIANGLE, "CHF/USD": cross_rate},
        fx_spread_rate=spread,
    )

    result = _normalize_payload("pac", payload)

    assert result.availability == "ready"
    assert result.issues == ()


def test_cross_rate_just_beyond_the_spread_is_one_typed_invalid_issue() -> None:
    # One millionth above the boundary: 1.437626 × 0.8 / 1.085 > 1.06.
    payload = fx_conversion_request(
        "beyond-the-spread",
        funding_currency="CHF",
        assets=[("USD", "10.00")],
        fx_rates={**FX_TRIANGLE, "CHF/USD": "1.437626"},
        fx_spread_rate="0.2",
    )

    result = _normalize_payload("pac", payload)

    assert result.availability == "invalid"
    assert result.normalized is None
    assert _issue_dumps(result) == [CHF_USD_INCONSISTENT_ISSUE]


# The coherence band. A stored rate carries ten decimals, so a cross rate cannot
# always hit the triangle exactly: a cross just above it, within half a unit of
# the tenth decimal on each of the three stored rates, is coherent, and the
# conversion then plans at the triangle (the evaluator suite pins that rate).
# RON→USD through EUR: 1.085 / 4.97 = 31/142 = 0.21830985915…
RON_USD_INCONSISTENT_ISSUE: JsonObject = {
    "code": FX_RATE_INCONSISTENT_CODE,
    "severity": "error",
    "kind": "invalid",
    "path": _field_wire_path("fx", "fx_rate", "RON/USD", "rate"),
    "message_key": FX_RATE_INCONSISTENT_CODE,
    "params": [
        {"kind": "currency", "name": "destination_currency", "value": "USD"},
        {"kind": "id", "name": "pair", "value": "RON/USD"},
        {"kind": "currency", "name": "source_currency", "value": "RON"},
        {"kind": "currency", "name": "valuation_currency", "value": "EUR"},
    ],
}


@pytest.mark.parametrize(
    ("cross_rate", "availability", "issues"),
    (
        # The triangle rounded at the tenth decimal: relatively 2.1e-10 above it, inside the 2.9e-10 band.
        pytest.param("0.2183098592", "ready", [], id="above-triangle-inside-band"),
        # One unit of the tenth decimal more: relatively 6.6e-10 above the triangle, beyond the band.
        pytest.param("0.2183098593", "invalid", [RON_USD_INCONSISTENT_ISSUE], id="above-triangle-beyond-band"),
        # The triangle truncated at the tenth decimal: below it, coherent with or without the band.
        pytest.param("0.2183098591", "ready", [], id="below-triangle"),
    ),
)
def test_cross_rate_within_the_ten_decimal_band_of_the_triangle_is_coherent(
    cross_rate: str,
    availability: str,
    issues: list[JsonObject],
) -> None:
    payload = fx_conversion_request(
        f"ron-usd-band-{cross_rate}",
        funding_currency="RON",
        assets=[("USD", "21.83")],
        fx_rates={"EUR/RON": "4.97", "EUR/USD": "1.085", "RON/USD": cross_rate},
    )

    result = _normalize_payload("pac", payload)

    assert result.availability == availability
    assert _issue_dumps(result) == issues
    assert (result.normalized is None) == (availability == "invalid")


def test_missing_cross_rate_is_reported_missing_and_not_also_inconsistent() -> None:
    payload = fx_conversion_request(
        "missing-cross-rate",
        funding_currency="CHF",
        assets=[("USD", "10.00")],
        fx_rates=dict(FX_TRIANGLE),
    )

    result = _normalize_payload("pac", payload)

    assert result.availability == "needs_input"
    assert tuple(issue.code for issue in result.issues) == ("allocation.fx_rate_missing",)


def test_incoherent_cross_rate_is_reported_once_for_its_pair() -> None:
    # Two USD-quoted Assets, two BUY routes reaching the same CHF→USD conversion: one issue.
    payload = fx_conversion_request(
        "two-routes-one-pair",
        funding_currency="CHF",
        assets=[("USD", "10.00"), ("USD", "20.00")],
        fx_rates={**FX_TRIANGLE, "CHF/USD": "1.1502"},
    )

    result = _normalize_payload("pac", payload)

    assert _single_issue(result, FX_RATE_INCONSISTENT_CODE).model_dump(mode="json") == CHF_USD_INCONSISTENT_ISSUE


def _rebalancer_payload_funded_in_chf(cross_rate: str) -> JsonObject:
    payload = _ready_rebalancer_payload()
    for contribution in payload["contributions"]:
        contribution["amount"]["currency"] = "CHF"
    payload["fx_rates"] = {**FX_TRIANGLE, "CHF/USD": cross_rate}
    return payload


def test_rebalancer_incoherent_cross_rate_is_one_invalid_issue() -> None:
    # The violating route is route-c-beta-buy: broker-beta, funded in CHF, buys the USD-quoted asset-c.
    result = _normalize_payload("rebalancer", _rebalancer_payload_funded_in_chf("1.1502"))

    issue = _single_issue(result, FX_RATE_INCONSISTENT_CODE)
    assert result.availability == "invalid"
    assert result.normalized is None
    assert _issue_wire_path(issue)["entity_id"] == "CHF/USD"
    assert issue.model_dump(mode="json") == CHF_USD_INCONSISTENT_ISSUE


def test_rebalancer_coherent_cross_rate_is_ready() -> None:
    result = _normalize_payload("rebalancer", _rebalancer_payload_funded_in_chf("1.1501"))

    assert result.availability == "ready"
    assert result.issues == ()


def test_fx_rate_inconsistent_has_an_explicit_w1_definition() -> None:
    # Resolved inside the test, never at import: an unknown code must fail this test, not collection.
    definition = normalizer_issue_definition(FX_RATE_INCONSISTENT_CODE)

    assert definition.code == FX_RATE_INCONSISTENT_CODE
    assert definition.kind == "invalid"
    assert definition.severity == "error"
    assert definition.producer == "w1_normalizer"


# ---------------------------------------------------------------------------
# A0 (project 67): the normalizer reads a stored FX rate through the house's ``oriented_rate``
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("source", "destination"), [pytest.param("EUR", "USD", id="stored-direction"), pytest.param("USD", "EUR", id="inverse-direction")])
def test_normalizer_fx_rate_is_the_oriented_rate(monkeypatch, source, destination):
    """``fx_rate`` and ``_stored_fx_rate`` give what ``financial_math.fx_rates.oriented_rate`` gives, in both directions:
    no inversion of their own. ``oriented_rate`` is replaced in the module by a recorder that delegates; before A0 the
    module has no such name, so ``monkeypatch.setattr`` is the red."""
    calls: list[tuple] = []

    def recorder(rate, from_currency, to_currency):
        calls.append((rate, from_currency, to_currency))
        return oriented_rate(rate, from_currency, to_currency)

    monkeypatch.setattr(normalize, "oriented_rate", recorder)
    normalizer_class = normalize._PlannerV2Normalizer
    stub = SimpleNamespace(request=SimpleNamespace(fx_rates={"EUR/USD": "1.25"}), _fx_pair_key=normalizer_class._fx_pair_key)
    stored = ExactRatio(5, 4)

    read = normalizer_class.fx_rate(stub, source, destination)
    assert read == oriented_rate(stored, source, destination)
    assert calls == [(stored, source, destination)]

    calls.clear()
    assert normalizer_class._stored_fx_rate(read, source, destination) == stored
    assert calls and calls[0][1:] == (source, destination)


def test_normalized_pac_scenario_has_no_broker_transfer() -> None:
    """A2 step 10 (specification §15 n. 2): in the PAC the funding routes stay as the user declares them; the transfers between
    Brokers belong to the Rebalancer. A normalized PAC scenario has no transfer lane, and its view no ``broker_transfer`` decision."""
    for payload in (_fixture(PAC_FIXTURE), fx_conversion_request("no-transfer", funding_currency="EUR", assets=[("USD", "10.00")], fx_rates={"EUR/USD": "1.085"})):
        scenario = _normalize_payload("pac", payload).normalized
        assert scenario.transfer_lanes == ()
        assert not [access for access in build_exact_policy_view(scenario).decisions if access.family == "broker_transfer"]


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: fx_conversion_request("pairs-one", funding_currency="EUR", assets=[("USD", "10.00")], fx_rates={"EUR/USD": "1.085"}), id="one-pair"),
        pytest.param(fx_two_assets_one_pair_request, id="N1-two-routes-one-pair"),
        pytest.param(fx_two_way_request, id="N2-both-directions"),
        pytest.param(fx_two_brokers_request, id="N3-two-brokers"),
        pytest.param(fx_two_sources_request, id="N4-two-sources"),
    ],
)
def test_normalizer_and_engine_agree_on_conversion_pairs(build):
    """A2 step 14: the normalizer checks a rate (and its coherence) for every conversion a buy may need, from its own
    reading of the cash pools; the engine plans exactly those conversions, from ``fx_decision_specs``. The two readings of
    the pool-currency rule (D2 a) must name the same (Broker, source, destination) pairs."""
    payload = build()
    request = PAC_PLAN_INPUT_ADAPTER.validate_json(_wire(payload), strict=True)
    normalizer = normalize._PlannerV2Normalizer(request, ())
    normalizer.validate_assets()
    pools = normalizer._cash_pool_currencies_by_broker()
    checked = {(route.broker_id, pool, normalizer.asset_by_id[route.asset_id].quote.currency) for route in request.order_routes if route.side == "buy" for pool in pools.get(route.broker_id, set()) if pool != normalizer.asset_by_id[route.asset_id].quote.currency}

    scenario = _normalize_payload("pac", payload).normalized
    planned = {(spec.broker_id, spec.source_currency, spec.destination_currency) for spec in fx_decision_specs(scenario, build_scenario_index(scenario), None)}
    assert planned == checked
    assert planned, "every case converts"


# ---------------------------------------------------------------------------
# A4 step 3 (project 67): target entries with limits, read from the request
# ---------------------------------------------------------------------------


def _issues(result, code: str) -> list:
    return [issue for issue in result.issues if issue.code == code]


def test_minimum_above_maximum_is_invalid_and_names_the_entry() -> None:
    """The check of M1 from the request: an Asset whose minimum is above its maximum is ``invalid``, and the issue names the
    entry (its minimum), so the interface can mark that row. Amounts and shares may be mixed: a share is read against the reference."""
    payload = _fixture(PAC_FIXTURE)
    payload["target_weights"] = [asset_entry("asset-one", "1", minimum=amount_limit("4"), maximum=amount_limit("3"))]

    result = _normalize_payload("pac", payload)

    assert (result.availability, result.normalized) == ("invalid", None)
    (issue,) = _issues(result, "allocation.bound_min_above_max")
    assert issue.path.model_dump() == {"kind": "field", "section": "targets", "entity_kind": "asset", "entity_id": "asset-one", "field": "minimum"}
    assert issue.severity == "error" and issue.kind == "invalid"

    mixed = _fixture(PAC_FIXTURE)
    mixed["target_weights"] = [asset_entry("asset-one", "1", minimum=share_limit("0.8"), maximum=amount_limit("3"))]  # 80% of EUR5 = 4 > 3
    assert _issues(_normalize_payload("pac", mixed), "allocation.bound_min_above_max")


def test_rebalancer_cash_weight_reaches_the_exact_entry() -> None:
    """B3 of project 67 (contract §5.2): a Rebalancer cash entry with a weight is an entry of the target; the weights of the
    Assets and the cash entries sum to one together, and the weight reaches the exact entry. Without the cash weight the Assets
    alone sum to 0.95, which is «not one»."""
    scenario = _ready_rebalancer_scenario()
    assert [(entry.broker_id, entry.currency, entry.weight, entry.minimum, entry.maximum) for entry in scenario.cash_entries] == [("broker-alpha", "EUR", ExactRatio(1, 20), None, None)]

    short = _ready_rebalancer_payload()
    short["target_weights"] = [entry for entry in short["target_weights"] if entry["kind"] == "asset"]
    assert _issues(_normalize_payload("rebalancer", short), "allocation.target_total_not_one")

    out_of_range = _ready_rebalancer_payload()
    next(entry for entry in out_of_range["target_weights"] if entry["kind"] == "cash")["weight"] = "1.05"
    result = _normalize_payload("rebalancer", out_of_range)
    assert _issues(result, "allocation.target_weight_out_of_range") and not _issues(result, "allocation.target_total_not_one")


def test_rebalancer_cash_item_on_a_broker_without_routes_is_reached_by_a_lane() -> None:
    """A 5 % cash item on an active Broker that neither buys nor holds cash: the deposits go to the Brokers that buy, and a
    lane in the item's currency reaches its cell, so its target is not unreachable by construction."""
    payload = _ready_rebalancer_payload()
    payload["brokers"].append({"broker_id": "broker-gamma", "identity": {"kind": "manual_broker", "name": "Synthetic Broker Gamma"}, "provenance_id": "prov-manual", "conversion_mode": "manual"})
    next(entry for entry in payload["target_weights"] if entry["kind"] == "cash")["broker_id"] = "broker-gamma"

    scenario = _ready_scenario("rebalancer", payload)

    assert ("broker-alpha", "broker-gamma", "EUR") in {(lane.source_broker_id, lane.destination_broker_id, lane.currency) for lane in scenario.transfer_lanes}
    assert "broker-gamma" not in {route.broker_id for route in scenario.funding_routes}


def test_cash_entry_with_a_weight_is_unsupported_in_a_pac() -> None:
    """Contract §5.2: a PAC cash entry may carry a minimum and a maximum; a weight other than zero is «unsupported» (it arrives
    with the Rebalancer). A zero weight with no limit says nothing and is ignored."""
    payload = _fixture(PAC_FIXTURE)
    payload["target_weights"] = [asset_entry("asset-one", "1"), cash_entry("broker-one", "EUR", weight="0.5")]
    result = _normalize_payload("pac", payload)
    assert result.availability == "unsupported"
    (issue,) = _issues(result, "pac_allocator.cash_weight_unsupported")
    assert issue.path.model_dump() == {"kind": "field", "section": "targets", "entity_kind": "cash", "entity_id": "broker-one:EUR", "field": "weight"}

    fine = _fixture(PAC_FIXTURE)
    fine["target_weights"] = [asset_entry("asset-one", "1"), cash_entry("broker-one", "EUR", maximum=amount_limit("3")), cash_entry("broker-one", "USD")]
    result = _normalize_payload("pac", fine)
    assert result.availability == "ready", [issue.code for issue in result.issues]
    assert [(entry.broker_id, entry.currency) for entry in result.normalized.cash_entries] == [("broker-one", "EUR")]


def test_limit_values_are_checked_before_the_scenario_is_built() -> None:
    """An amount in another currency than the valuation one, a negative amount and a share outside [0, 1] are refused with the
    entry's field named; a cash entry at an unknown Broker is a missing reference."""
    cases = {
        "allocation.currency_mismatch": asset_entry("asset-one", "1", maximum=amount_limit("3", "USD")),
        "allocation.target_weight_out_of_range": asset_entry("asset-one", "1", minimum=amount_limit("-1")),
    }
    for code, entry in cases.items():
        payload = _fixture(PAC_FIXTURE)
        payload["target_weights"] = [entry]
        assert _issues(_normalize_payload("pac", payload), code), code
    share = _fixture(PAC_FIXTURE)
    share["target_weights"] = [asset_entry("asset-one", "1", maximum=share_limit("1.5"))]
    assert _issues(_normalize_payload("pac", share), "allocation.target_weight_out_of_range")
    unknown = _fixture(PAC_FIXTURE)
    unknown["target_weights"] = [asset_entry("asset-one", "1"), cash_entry("broker-nowhere", "EUR", maximum=amount_limit("3"))]
    assert _issues(_normalize_payload("pac", unknown), "allocation.reference_not_found")


FIDELITY_LAMBDA_CASES = (
    pytest.param({"kind": "level", "level": "cost_aware"}, "weighted", ExactRatio(1, 4), id="cost-aware"),
    pytest.param({"kind": "level", "level": "balanced"}, "weighted", ExactRatio(1), id="balanced"),
    pytest.param({"kind": "level", "level": "faithful"}, "weighted", ExactRatio(4), id="faithful"),
    pytest.param({"kind": "custom", "lambda": "2.5"}, "weighted", ExactRatio(5, 2), id="custom"),
    pytest.param({"kind": "target_first"}, "target_first", None, id="target-first"),
)


@pytest.mark.parametrize(("fidelity", "kind", "distance_weight"), FIDELITY_LAMBDA_CASES)
def test_normalizer_maps_each_fidelity_level_to_its_lambda(fidelity: JsonObject, kind: str, distance_weight: ExactRatio | None) -> None:
    """B3 test 5 (specifica §6.3): a level reads its ``λ`` off the one table (¼, 1, 4) the preview of B4 reuses; a custom
    ``λ`` goes through exactly; «Target first» has none. The PAC has no fidelity: its objectives do not depend on it."""
    payload = _ready_rebalancer_payload()
    payload["target_fidelity"] = fidelity
    scenario = _ready_scenario("rebalancer", payload)
    assert (scenario.target_fidelity.kind, scenario.target_fidelity.distance_weight) == (kind, distance_weight)
    if fidelity["kind"] == "level":
        assert FIDELITY_LEVEL_WEIGHTS[fidelity["level"]] == distance_weight

    pac = _normalize_payload("pac", _fixture(PAC_FIXTURE))
    assert pac.ready and pac.normalized.target_fidelity is None


def test_rebalancer_deposits_and_lanes_are_generated() -> None:
    """Specification §15 n. 2, B3 of project 67: every contribution may be deposited, whole, at every Broker with a buy
    route, in its own currency and with its provenance; transfers join every ordered pair of the Brokers, in every currency
    of their cash, of the contributions and of the quotes they buy. The PAC keeps the funding routes it declares, and no lane."""
    scenario = _ready_rebalancer_scenario()
    assert {(route.route_id, route.source_kind, route.source_id, route.broker_id, route.currency, route.transfer_cap, route.priority, route.provenance_id) for route in scenario.funding_routes} == {
        ("deposit:16:contribution-eur12:broker-alpha", "contribution", "contribution-eur", "broker-alpha", "EUR", _money(ExactRatio(50), "EUR"), 0, "prov-manual"),
        ("deposit:16:contribution-eur11:broker-beta", "contribution", "contribution-eur", "broker-beta", "EUR", _money(ExactRatio(50), "EUR"), 0, "prov-manual"),
    }
    assert [(lane.source_broker_id, lane.destination_broker_id, lane.currency) for lane in scenario.transfer_lanes] == [
        ("broker-alpha", "broker-beta", "EUR"),
        ("broker-alpha", "broker-beta", "USD"),
        ("broker-beta", "broker-alpha", "EUR"),
        ("broker-beta", "broker-alpha", "USD"),
    ]
    assert scenario.sell_context is None

    pac = _ready_scenario("pac", _pac_payload_with_uncapped_cash_funding_route())
    assert [route.route_id for route in pac.funding_routes] == ["fund-cash-broker-one"]
    assert pac.transfer_lanes == ()


def test_deposit_ids_never_collide_and_stay_ids() -> None:
    """Two pairs whose IDs contain ``:`` stay apart (length prefixes), and a pair past 128 characters still gives an ID."""
    assert _deposit_id("a:b", "c") != _deposit_id("a", "b:c")
    long_id = _deposit_id("c" * 128, "b" * 128)
    assert len(long_id) <= 128 and long_id != _deposit_id("c" * 128, "b" * 127)
    route = {"funding_route_id": long_id, "source": {"kind": "contribution", "contribution_id": "c"}, "broker_id": "b", "currency": "EUR", "provenance_id": "p"}
    assert PlannerFundingRouteInput.model_validate_json(json.dumps(route), strict=True).funding_route_id == long_id


def test_rebalancer_lanes_skip_an_inactive_broker_that_keeps_only_custody() -> None:
    """An inactive Broker with only custody and a cash row selected at zero is ready (V9 keeps its facts), and gets no lane:
    a lane moves cash only between active Brokers (``_validate_transfer_lanes``)."""
    payload = _ready_rebalancer_payload()
    payload["brokers"].append(
        {
            "broker_id": "broker-gamma",
            "identity": {"kind": "domain_broker", "source_broker_id": "synthetic-broker-gamma", "name": "Synthetic Broker Gamma", "active": False},
            "provenance_id": "prov-portfolio",
            "conversion_mode": "manual",
        }
    )
    payload["existing_cash"] = [{"cash_id": "cash-gamma-eur", "broker_id": "broker-gamma", "available": {"amount": "7", "currency": "EUR"}, "selected": {"amount": "0", "currency": "EUR"}, "provenance_id": "prov-portfolio"}]

    scenario = _ready_scenario("rebalancer", payload)

    assert "broker-gamma" in {broker.broker_id for broker in scenario.brokers}
    assert not [lane for lane in scenario.transfer_lanes if "broker-gamma" in (lane.source_broker_id, lane.destination_broker_id)]
