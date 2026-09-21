"""Pure Decimal-domain tests for PAC allocation and portfolio rebalancing P1.

All inputs are owned in-memory witnesses.  Expectations are literal monetary
values or independently evaluated :class:`fractions.Fraction` ratios; the tests
do not reproduce the production evaluator.
"""

from __future__ import annotations

import json
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any

import pytest

from backend.app.schemas.pac_allocator import (
    P1_MAX_CURRENCIES,
    P1_MAX_ISSUES,
    P1_MAX_NATIVE_AMOUNT_CHARS,
    P1_MAX_ROWS,
    P1_RESULT_BYTES,
    PAC_ANALYZE_INPUT_ADAPTER,
    PAC_ANALYZE_OUTPUT_ADAPTER,
    REBALANCE_ANALYZE_INPUT_ADAPTER,
    REBALANCE_ANALYZE_OUTPUT_ADAPTER,
    RebalanceAnalyzeInvalid,
)
from backend.app.services.pac_allocator import (
    analyze_pac_budget,
    analyze_rebalancing,
)
from backend.app.services.pac_allocator.numeric import (
    decimal_context,
    decimal_text,
)

Path = tuple[str | int, ...]


def _asset(
    instrument_key: str = "asset-alpha",
    *,
    name: str = "Alpha",
    buy_grid: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "instrument_key": instrument_key,
        "name": name,
        "buy_grid": buy_grid,
    }


def _target(
    instrument_key: str = "asset-alpha",
    percent: str | None = "100",
) -> dict[str, object]:
    return {
        "instrument_key": instrument_key,
        "target_percent": percent,
    }


def _holding(
    row_key: str = "custody-alpha",
    instrument_key: str = "asset-alpha",
    *,
    name: str = "Alpha",
    quantity: str | None = "2",
    price: str | None = "25",
    currency: str | None = "EUR",
    basis: int | None = 1,
    reference_date: str | None = "2026-09-14",
    buy_grid: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "row_key": row_key,
        "instrument_key": instrument_key,
        "name": name,
        "quantity": quantity,
        "quote": {
            "raw_price": price,
            "currency": currency,
            "quote_base_quantity": basis,
            "reference_date": reference_date,
        },
        "buy_grid": buy_grid,
    }


def _rate(
    currency: str,
    rate: str | None,
    reference_date: str | None = "2026-09-14",
) -> dict[str, object]:
    return {
        "currency": currency,
        "rate_to_report": rate,
        "reference_date": reference_date,
    }


def _contribution(
    currency: str = "EUR",
    amount: str | None = "5",
    monetary_step: str | None = "0.01",
) -> dict[str, object]:
    return {
        "currency": currency,
        "amount": amount,
        "monetary_step": monetary_step,
    }


def _pac_request(
    *,
    assets: list[dict[str, object]] | None = None,
    targets: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    selected = [_asset()] if assets is None else assets
    target_vector = [_target()] if targets is None else targets
    return {
        "operation": "analyze",
        "report_currency": "EUR",
        "as_of_date": "2026-09-14",
        "assets": selected,
        "targets": target_vector,
        "cash_balances": [],
        "contributions": [],
        "valuation_rates": [],
    }


def _rebalance_request(
    *,
    holdings: list[dict[str, object]] | None = None,
    targets: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    selected = [_holding()] if holdings is None else holdings
    target_vector = [_target()] if targets is None else targets
    return {
        "operation": "analyze",
        "report_currency": "EUR",
        "as_of_date": "2026-09-14",
        "holdings": selected,
        "targets": target_vector,
        "cash_balances": [],
        "contributions": [],
        "valuation_rates": [],
    }


def _at(value: Any, path: Path) -> Any:
    for token in path:
        value = value[token]
    return value


def _set(value: Any, path: Path, replacement: Any) -> None:
    _at(value, path[:-1])[path[-1]] = replacement


def _facts_have_one_primary_reason(node: Any) -> None:
    if isinstance(node, dict):
        if "reason_codes" in node:
            if node["availability"] == "available":
                assert node["value"] is not None
                assert node["reason_codes"] == []
            else:
                assert node["availability"] == "unavailable"
                assert node["value"] is None
                assert len(node["reason_codes"]) == 1
        for child in node.values():
            _facts_have_one_primary_reason(child)
    elif isinstance(node, list):
        for child in node:
            _facts_have_one_primary_reason(child)


def _analyze_pac(raw: dict[str, object]) -> dict[str, Any]:
    before = deepcopy(raw)
    request = PAC_ANALYZE_INPUT_ADAPTER.validate_python(raw, strict=True)
    model_before = request.model_dump(mode="json")
    result = analyze_pac_budget(request)
    emitted = PAC_ANALYZE_OUTPUT_ADAPTER.dump_json(result)
    assert PAC_ANALYZE_OUTPUT_ADAPTER.validate_json(emitted, strict=True) == result
    assert raw == before
    assert request.model_dump(mode="json") == model_before
    wire = json.loads(emitted)
    assert wire["operation"] == "analyze"
    assert wire["result_kind"] == "pac_budget_analysis"
    assert wire["numeric_policy_id"] == "pac-budget-allocation-v1"
    assert (wire["normalized"] is not None) is (wire["availability"] == "ready")
    _facts_have_one_primary_reason(wire)
    return wire


def _analyze_rebalancer(raw: dict[str, object]) -> dict[str, Any]:
    before = deepcopy(raw)
    request = REBALANCE_ANALYZE_INPUT_ADAPTER.validate_python(raw, strict=True)
    model_before = request.model_dump(mode="json")
    result = analyze_rebalancing(request)
    emitted = REBALANCE_ANALYZE_OUTPUT_ADAPTER.dump_json(result)
    assert REBALANCE_ANALYZE_OUTPUT_ADAPTER.validate_json(emitted, strict=True) == result
    assert raw == before
    assert request.model_dump(mode="json") == model_before
    wire = json.loads(emitted)
    assert wire["operation"] == "analyze"
    assert wire["result_kind"] == "portfolio_rebalancing_analysis"
    assert wire["numeric_policy_id"] == "portfolio-rebalancing-v1"
    assert (wire["normalized"] is not None) is (wire["availability"] == "ready")
    _facts_have_one_primary_reason(wire)
    return wire


def _value(fact: dict[str, Any]) -> Any:
    assert fact["availability"] == "available", fact
    assert fact["reason_codes"] == []
    return fact["value"]


def _unavailable(
    fact: dict[str, Any],
    reason: str | None = None,
) -> None:
    assert fact["availability"] == "unavailable", fact
    assert fact["value"] is None
    assert len(fact["reason_codes"]) == 1
    if reason is not None:
        assert fact["reason_codes"] == [reason]


def _money(
    fact: dict[str, Any],
    amount: str,
    currency: str = "EUR",
) -> None:
    assert _value(fact) == {"currency": currency, "amount": amount}


def _truncate_28(value: Fraction) -> str:
    """Independent truncation oracle for the public ratio approximation."""
    scaled = abs(value.numerator) * 10**28 // value.denominator
    whole, fraction = divmod(scaled, 10**28)
    suffix = f"{fraction:028d}".rstrip("0")
    text = f"{whole}.{suffix}" if suffix else str(whole)
    return f"-{text}" if value < 0 and scaled else text


def _ratio(
    fact: dict[str, Any],
    numerator: int | str,
    denominator: int | str,
    unit: str,
) -> None:
    value = _value(fact)
    expected_numerator = Fraction(numerator)
    expected_denominator = Fraction(denominator)
    expected = expected_numerator / expected_denominator
    assert Fraction(value["numerator"]) == expected_numerator
    assert Fraction(value["denominator"]) == expected_denominator
    assert value["unit"] == unit
    assert value["approximation_decimal_places"] == 28
    assert value["approximation"] == _truncate_28(expected)
    assert value["approximation_exact"] is (Fraction(value["approximation"]) == expected)


def _issue(
    result: dict[str, Any],
    code: str,
    path: Path | None = None,
    kind: str | None = None,
) -> dict[str, Any]:
    matches = [issue for issue in result["issues"] if issue["code"] == code and (path is None or issue["path"] == list(path))]
    assert len(matches) == 1, (code, path, result["issues"])
    (issue,) = matches
    if kind is not None:
        assert issue["kind"] == kind
    return issue


def _allocations(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_key = {allocation["instrument_key"]: allocation for allocation in result["allocations"]}
    assert len(by_key) == len(result["allocations"])
    return by_key


def _holdings(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_key = {holding["row_key"]: holding for holding in result["holdings"]}
    assert len(by_key) == len(result["holdings"])
    return by_key


def _instruments(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_key = {instrument["instrument_key"]: instrument for instrument in result["instruments"]}
    assert len(by_key) == len(result["instruments"])
    return by_key


def test_rebalancer_maximal_malformed_draft_exceeds_legacy_issue_cap_and_stays_typed():
    holdings = [
        _holding(
            row_key=f"duplicate-row-{index // 2}",
            instrument_key=f"selected-{index}",
            name="",
            quantity="-1",
            price="0",
            currency="INVALID",
            basis=0,
            reference_date="2026-99-99",
            buy_grid={"mode": None, "quantity_step": "0"},
        )
        for index in range(P1_MAX_ROWS)
    ]
    contributions = [_contribution("INVALID", "-1", "0") for _index in range(P1_MAX_ROWS)]
    targets = [_target(f"orphan-{index // 2}", "-1") for index in range(P1_MAX_ROWS)]
    cash_balances = [{"currency": "INVALID", "amount": "-1"} for _index in range(P1_MAX_CURRENCIES)]
    valuation_rates = [_rate("INVALID", "0", "2026-99-99") for _index in range(P1_MAX_CURRENCIES)]
    assert len(holdings) == len(contributions) == len(targets) == P1_MAX_ROWS == 32
    assert len(cash_balances) == len(valuation_rates) == P1_MAX_CURRENCIES == 4

    raw = _rebalance_request(holdings=holdings, targets=targets)
    raw.update(
        {
            "report_currency": "INVALID",
            "as_of_date": "2026-99-99",
            "cash_balances": cash_balances,
            "contributions": contributions,
            "valuation_rates": valuation_rates,
        }
    )
    request = REBALANCE_ANALYZE_INPUT_ADAPTER.validate_python(raw, strict=True)

    result = analyze_rebalancing(request)
    emitted = REBALANCE_ANALYZE_OUTPUT_ADAPTER.dump_json(result)
    round_tripped = REBALANCE_ANALYZE_OUTPUT_ADAPTER.validate_json(
        emitted,
        strict=True,
    )

    assert isinstance(result, RebalanceAnalyzeInvalid)
    assert isinstance(round_tripped, RebalanceAnalyzeInvalid)
    assert round_tripped == result
    assert P1_MAX_ISSUES == 512
    assert 384 < len(result.issues) <= P1_MAX_ISSUES
    assert P1_RESULT_BYTES == 256 * 1024
    assert len(emitted) < P1_RESULT_BYTES

    wire = json.loads(emitted)
    assert wire["availability"] == "invalid"
    assert wire["normalized"] is None
    assert len(wire["issues"]) == len(result.issues)
    issue_shapes = {(issue["kind"], issue["code"], tuple(issue["path"])) for issue in wire["issues"]}
    assert {
        ("invalid", "invalid_currency", ("report_currency",)),
        (
            "unsupported",
            "short_inventory_unsupported",
            ("holdings", 31, "quantity"),
        ),
        (
            "invalid",
            "duplicate_row_key",
            ("holdings", 0, "row_key"),
        ),
        (
            "invalid",
            "negative_contribution",
            ("contributions", 31, "amount"),
        ),
        (
            "invalid",
            "duplicate_target_instrument",
            ("targets", 0, "instrument_key"),
        ),
        (
            "invalid",
            "target_instrument_not_selected",
            ("targets", 0, "instrument_key"),
        ),
        ("missing", "target_required", ("targets",)),
    } <= issue_shapes
    assert any(issue.kind == "missing" and issue.code == "target_required" and issue.path == ["targets"] and issue.related_indices == [31] and issue.params.instrument_key == "selected-31" for issue in result.issues)


def test_pac_multicurrency_cash_and_contributions_are_counted_once():
    raw = _pac_request(
        assets=[
            _asset("asset-alpha", name="Alpha"),
            _asset("asset-beta", name="Beta"),
        ],
        targets=[
            _target("asset-alpha", "25"),
            _target("asset-beta", "75"),
        ],
    )
    raw["cash_balances"] = [
        {"currency": "EUR", "amount": "0.005"},
        {"currency": "USD", "amount": "10"},
    ]
    raw["contributions"] = [
        _contribution("EUR", "5", "0.01"),
        _contribution("GBP", "4", "0.25"),
    ]
    raw["valuation_rates"] = [
        _rate("USD", "0.9"),
        _rate("GBP", "1.25"),
    ]

    result = _analyze_pac(raw)

    assert result["availability"] == "ready"
    assert result["issues"] == []
    _money(result["totals"]["existing_cash_reporting"], "9.005")
    _money(result["totals"]["contributions_reporting"], "10")
    _money(result["totals"]["investable_budget_reporting"], "19.005")
    assert _value(result["totals"]["target_total_percent"]) == "100"

    allocations = _allocations(result)
    _money(
        allocations["asset-alpha"]["ideal_allocation_reporting"],
        "4.75125",
    )
    _money(
        allocations["asset-beta"]["ideal_allocation_reporting"],
        "14.25375",
    )
    assert Fraction("4.75125") == Fraction("19.005") * Fraction(25, 100)
    assert Fraction("14.25375") == Fraction("19.005") * Fraction(75, 100)

    pools = {pool["currency"]: pool for pool in _value(result["cash_pools"])}
    assert set(pools) == {"EUR", "GBP", "USD"}
    assert pools["EUR"]["existing_amount"] == "0.005"
    assert pools["EUR"]["contribution_amount"] == "5"
    assert pools["EUR"]["combined_amount"] == "5.005"
    assert pools["USD"]["existing_amount"] == "10"
    assert pools["USD"]["contribution_amount"] == "0"
    assert pools["GBP"]["existing_amount"] == "0"
    assert pools["GBP"]["contribution_amount"] == "4"
    _money(pools["USD"]["combined_reporting"], "9")
    _money(pools["GBP"]["combined_reporting"], "5")
    assert result["normalized"]["cash_balances"] == [
        {"currency": "EUR", "amount": "0.005"},
        {"currency": "USD", "amount": "10"},
    ]
    assert result["normalized"]["contributions"] == [
        {"currency": "EUR", "amount": "5", "monetary_step": "0.01"},
        {"currency": "GBP", "amount": "4", "monetary_step": "0.25"},
    ]


@pytest.mark.parametrize("service", ["pac", "rebalancer"])
def test_more_than_four_same_currency_contributions_are_valid_and_sum_exactly(
    service,
):
    raw = _pac_request() if service == "pac" else _rebalance_request()
    raw["cash_balances"] = [{"currency": "EUR", "amount": "0.499999999985"}]
    contributions = [
        _contribution(
            "EUR",
            "0.100000000001",
            "0.000000000001",
        ),
        _contribution(
            "EUR",
            "0.100000000002",
            "0.000000000001",
        ),
        _contribution(
            "EUR",
            "0.100000000003",
            "0.000000000001",
        ),
        _contribution(
            "EUR",
            "0.100000000004",
            "0.000000000001",
        ),
        _contribution(
            "EUR",
            "0.100000000005",
            "0.000000000001",
        ),
    ]
    assert len(contributions) > 4
    raw["contributions"] = contributions

    result = _analyze_pac(raw) if service == "pac" else _analyze_rebalancer(raw)

    assert result["availability"] == "ready"
    assert all(issue["code"] != "duplicate_currency" for issue in result["issues"])
    _money(result["totals"]["existing_cash_reporting"], "0.499999999985")
    _money(result["totals"]["contributions_reporting"], "0.500000000015")
    combined_field = "investable_budget_reporting" if service == "pac" else "cash_plus_contributions_reporting"
    _money(result["totals"][combined_field], "1")

    pools = {pool["currency"]: pool for pool in _value(result["cash_pools"])}
    assert set(pools) == {"EUR"}
    assert pools["EUR"]["existing_amount"] == "0.499999999985"
    assert pools["EUR"]["contribution_amount"] == "0.500000000015"
    assert pools["EUR"]["combined_amount"] == "1"

    normalized = result["normalized"]["contributions"]
    assert normalized == contributions

    if service == "pac":
        allocation = _allocations(result)["asset-alpha"]
        _money(allocation["ideal_allocation_reporting"], "1")
    else:
        instrument = _instruments(result)["asset-alpha"]
        _money(result["totals"]["current_invested_reporting"], "50")
        _money(instrument["current_value_reporting"], "50")
        _money(instrument["target_value_reporting"], "50")
        _money(instrument["value_gap_to_target_reporting"], "0")


@pytest.mark.parametrize("service", ["pac", "rebalancer"])
def test_more_than_four_distinct_native_currencies_is_typed_unsupported(
    service,
):
    raw = _pac_request() if service == "pac" else _rebalance_request()
    raw["contributions"] = [_contribution(currency, "1", "1") for currency in ("EUR", "USD", "GBP", "CHF", "JPY")]

    result = _analyze_pac(raw) if service == "pac" else _analyze_rebalancer(raw)

    assert result["availability"] == "unsupported"
    assert result["normalized"] is None
    assert all(issue["code"] != "duplicate_currency" for issue in result["issues"])
    assert [(issue["kind"], issue["code"], issue["path"]) for issue in result["issues"]] == [
        (
            "unsupported",
            "currency_domain_exceeded",
            ["report_currency"],
        )
    ]
    (issue,) = result["issues"]
    assert issue["related_indices"] == []
    assert issue["params"]["limit"] == 4


@pytest.mark.parametrize("service", ["pac", "rebalancer"])
def test_duplicate_existing_cash_currency_remains_invalid(service):
    raw = _pac_request() if service == "pac" else _rebalance_request()
    raw["cash_balances"] = [
        {"currency": "EUR", "amount": "1"},
        {"currency": "EUR", "amount": "2"},
    ]

    result = _analyze_pac(raw) if service == "pac" else _analyze_rebalancer(raw)

    assert result["availability"] == "invalid"
    assert result["normalized"] is None
    issue = _issue(
        result,
        "duplicate_currency",
        ("cash_balances", 0, "currency"),
        "invalid",
    )
    assert issue["related_indices"] == [0, 1]
    assert issue["params"]["currency"] == "EUR"
    assert issue["params"]["vector"] == "cash_balances"
    _unavailable(result["cash_pools"], "input_invalid")
    _unavailable(
        result["totals"]["existing_cash_reporting"],
        "input_invalid",
    )
    combined_field = "investable_budget_reporting" if service == "pac" else "cash_plus_contributions_reporting"
    _unavailable(result["totals"][combined_field], "input_invalid")


@pytest.mark.parametrize("service", ["pac", "rebalancer"])
def test_duplicate_valuation_rate_currency_remains_invalid(service):
    if service == "pac":
        raw = _pac_request()
        raw["cash_balances"] = [{"currency": "USD", "amount": "10"}]
    else:
        raw = _rebalance_request(
            holdings=[_holding(currency="USD")],
        )
    raw["valuation_rates"] = [
        _rate("USD", "0.9"),
        _rate("USD", "0.8"),
    ]

    result = _analyze_pac(raw) if service == "pac" else _analyze_rebalancer(raw)

    assert result["availability"] == "invalid"
    assert result["normalized"] is None
    issue = _issue(
        result,
        "duplicate_currency",
        ("valuation_rates", 0, "currency"),
        "invalid",
    )
    assert issue["related_indices"] == [0, 1]
    assert issue["params"]["currency"] == "USD"
    assert issue["params"]["vector"] == "valuation_rates"


@pytest.mark.parametrize(
    ("cash", "contribution", "step", "targets", "budget", "ideals"),
    [
        (
            "0",
            "0",
            "0.01",
            ("20", "80"),
            "0",
            ("0", "0"),
        ),
        (
            "0.000000000001",
            "0.000000000002",
            "0.000000000001",
            ("1", "99"),
            "0.000000000003",
            ("0.00000000000003", "0.00000000000297"),
        ),
        (
            "7.25",
            "0",
            "0.25",
            ("12.5", "87.5"),
            "7.25",
            ("0.90625", "6.34375"),
        ),
    ],
    ids=["zero-no-op", "sub-picounit-ideals", "arbitrary-decimal"],
)
def test_pac_zero_low_and_decimal_budgets_remain_ready_and_exact(
    cash,
    contribution,
    step,
    targets,
    budget,
    ideals,
):
    raw = _pac_request(
        assets=[_asset("asset-a"), _asset("asset-b")],
        targets=[
            _target("asset-a", targets[0]),
            _target("asset-b", targets[1]),
        ],
    )
    raw["cash_balances"] = [{"currency": "EUR", "amount": cash}]
    raw["contributions"] = [_contribution("EUR", contribution, step)]

    result = _analyze_pac(raw)

    assert result["availability"] == "ready"
    _money(result["totals"]["investable_budget_reporting"], budget)
    allocations = _allocations(result)
    _money(allocations["asset-a"]["ideal_allocation_reporting"], ideals[0])
    _money(allocations["asset-b"]["ideal_allocation_reporting"], ideals[1])
    assert not result["issues"]


def test_pac_optional_future_buy_grid_never_quantizes_budget_allocations():
    raw = _pac_request(
        assets=[
            _asset(
                "asset-a",
                buy_grid={"mode": "whole", "quantity_step": "3"},
            ),
            _asset(
                "asset-b",
                buy_grid={"mode": "fractional", "quantity_step": "0.125"},
            ),
        ],
        targets=[_target("asset-a", "50"), _target("asset-b", "50")],
    )
    raw["cash_balances"] = [{"currency": "EUR", "amount": "10"}]

    result = _analyze_pac(raw)

    assert result["availability"] == "ready"
    for allocation in _allocations(result).values():
        _money(allocation["ideal_allocation_reporting"], "5")
        assert set(allocation) == {
            "target_index",
            "instrument_key",
            "name",
            "target_percent",
            "ideal_allocation_reporting",
        }
    assert all("quantity" not in key for allocation in result["allocations"] for key in allocation)


def _aggregation_request() -> dict[str, object]:
    raw = _rebalance_request(
        holdings=[
            _holding(
                "broker-a::shared",
                "instrument-shared",
                name="Same display",
                quantity="30",
                price="10",
                currency="USD",
                basis=3,
            ),
            _holding(
                "broker-b::shared",
                "instrument-shared",
                name="Same display",
                quantity="250",
                price="4",
                currency="GBP",
                basis=100,
            ),
            _holding(
                "broker-c::distinct",
                "instrument-distinct",
                name="Same display",
                quantity="2",
                price="49",
                currency="EUR",
                basis=1,
            ),
        ],
        targets=[
            _target("instrument-shared", "60"),
            _target("instrument-distinct", "40"),
        ],
    )
    raw["cash_balances"] = [{"currency": "USD", "amount": "1000"}]
    raw["contributions"] = [_contribution("GBP", "100", "0.25")]
    raw["valuation_rates"] = [_rate("USD", "0.9"), _rate("GBP", "1.2")]
    return raw


def test_rebalancer_aggregates_custodies_by_instrument_not_display_name():
    result = _analyze_rebalancer(_aggregation_request())

    assert result["availability"] == "ready"
    holdings = _holdings(result)
    assert set(holdings) == {
        "broker-a::shared",
        "broker-b::shared",
        "broker-c::distinct",
    }
    _money(
        holdings["broker-a::shared"]["current_value_native"],
        "100",
        "USD",
    )
    _money(
        holdings["broker-a::shared"]["current_value_reporting"],
        "90",
    )
    _money(
        holdings["broker-b::shared"]["current_value_native"],
        "10",
        "GBP",
    )
    _money(
        holdings["broker-b::shared"]["current_value_reporting"],
        "12",
    )
    _money(
        holdings["broker-c::distinct"]["current_value_reporting"],
        "98",
    )

    instruments = _instruments(result)
    assert set(instruments) == {
        "instrument-shared",
        "instrument-distinct",
    }
    shared = instruments["instrument-shared"]
    distinct = instruments["instrument-distinct"]
    assert shared["custody_context_count"] == 2
    assert distinct["custody_context_count"] == 1
    assert shared["name"] == distinct["name"] == "Same display"
    _money(shared["current_value_reporting"], "102")
    _money(distinct["current_value_reporting"], "98")
    _money(result["totals"]["current_invested_reporting"], "200")

    _ratio(shared["current_weight_percent"], 10_200, 200, "percent")
    _ratio(distinct["current_weight_percent"], 9_800, 200, "percent")
    _money(shared["target_value_reporting"], "120")
    _money(distinct["target_value_reporting"], "80")
    _money(shared["value_gap_to_target_reporting"], "18")
    _money(distinct["value_gap_to_target_reporting"], "-18")
    _ratio(shared["gap_to_target_pp"], 1_800, 200, "percentage_points")
    _ratio(
        distinct["gap_to_target_pp"],
        -1_800,
        200,
        "percentage_points",
    )
    _ratio(
        result["totals"]["max_abs_gap_pp"],
        1_800,
        200,
        "percentage_points",
    )
    _ratio(
        result["totals"]["squared_gap_pp2"],
        6_480_000,
        40_000,
        "percentage_points_squared",
    )

    # Cash and contributions are contextual pools, never the invested denominator.
    _money(result["totals"]["existing_cash_reporting"], "900")
    _money(result["totals"]["contributions_reporting"], "120")
    _money(result["totals"]["cash_plus_contributions_reporting"], "1020")
    assert _value(shared["current_weight_percent"])["denominator"] == "200"
    assert _value(shared["gap_to_target_pp"])["denominator"] == "200"


def _instrument_projection(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    projection = {}
    for key, instrument in _instruments(result).items():
        projection[key] = {field: value for field, value in instrument.items() if field not in {"target_index", "name"}}
    return projection


def _holding_projection(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    projection = {}
    for key, holding in _holdings(result).items():
        projection[key] = {field: value for field, value in holding.items() if field != "holding_index"}
    return projection


def test_custody_permutation_preserves_source_and_canonical_values():
    original_raw = _aggregation_request()
    permuted_raw = deepcopy(original_raw)
    permuted_raw["holdings"] = list(reversed(permuted_raw["holdings"]))

    original = _analyze_rebalancer(original_raw)
    permuted = _analyze_rebalancer(permuted_raw)

    assert _instrument_projection(permuted) == _instrument_projection(original)
    assert _holding_projection(permuted) == _holding_projection(original)
    assert permuted["totals"] == original["totals"]
    assert [holding["row_key"] for holding in original["holdings"]] == [item["row_key"] for item in original_raw["holdings"]]
    assert [holding["row_key"] for holding in permuted["holdings"]] == [item["row_key"] for item in permuted_raw["holdings"]]


def test_target_permutation_changes_presentation_only():
    original_raw = _aggregation_request()
    permuted_raw = deepcopy(original_raw)
    permuted_raw["targets"] = list(reversed(permuted_raw["targets"]))

    original = _analyze_rebalancer(original_raw)
    permuted = _analyze_rebalancer(permuted_raw)

    assert _instrument_projection(permuted) == _instrument_projection(original)
    assert permuted["totals"] == original["totals"]
    assert [instrument["instrument_key"] for instrument in original["instruments"]] == [item["instrument_key"] for item in original_raw["targets"]]
    assert [instrument["instrument_key"] for instrument in permuted["instruments"]] == [item["instrument_key"] for item in permuted_raw["targets"]]
    assert [target["instrument_key"] for target in permuted["normalized"]["targets"]] == [item["instrument_key"] for item in permuted_raw["targets"]]


def test_zero_invested_rebalancing_is_ready_with_unavailable_ratios():
    raw = _rebalance_request(
        holdings=[
            _holding("custody-a", "asset-a", quantity="0"),
            _holding("custody-b", "asset-b", quantity="0"),
        ],
        targets=[_target("asset-a", "30"), _target("asset-b", "70")],
    )
    raw["cash_balances"] = [{"currency": "EUR", "amount": "1000"}]
    raw["contributions"] = [_contribution("EUR", "500", "1")]

    result = _analyze_rebalancer(raw)

    assert result["availability"] == "ready"
    _money(result["totals"]["current_invested_reporting"], "0")
    _money(result["totals"]["cash_plus_contributions_reporting"], "1500")
    for instrument in _instruments(result).values():
        _money(instrument["current_value_reporting"], "0")
        _money(instrument["target_value_reporting"], "0")
        _money(instrument["value_gap_to_target_reporting"], "0")
        _unavailable(
            instrument["current_weight_percent"],
            "zero_invested_value",
        )
        _unavailable(instrument["gap_to_target_pp"], "zero_invested_value")
    _unavailable(
        result["totals"]["max_abs_gap_pp"],
        "zero_invested_value",
    )
    _unavailable(
        result["totals"]["squared_gap_pp2"],
        "zero_invested_value",
    )


@pytest.mark.parametrize(
    ("field", "value", "availability", "code", "kind"),
    [
        ("quote", None, "needs_input", "quote_required", "missing"),
        ("raw_price", None, "needs_input", "field_required", "missing"),
        (
            "raw_price",
            "NaN",
            "invalid",
            "invalid_decimal_syntax",
            "invalid",
        ),
        (
            "raw_price",
            "Infinity",
            "invalid",
            "invalid_decimal_syntax",
            "invalid",
        ),
        (
            "raw_price",
            "-Infinity",
            "invalid",
            "invalid_decimal_syntax",
            "invalid",
        ),
        ("raw_price", "0", "invalid", "nonpositive_price", "invalid"),
        (
            "quote_base_quantity",
            None,
            "needs_input",
            "field_required",
            "missing",
        ),
        (
            "quote_base_quantity",
            0,
            "invalid",
            "invalid_quote_basis",
            "invalid",
        ),
        ("currency", "BAD", "invalid", "invalid_currency", "invalid"),
    ],
)
def test_missing_invalid_and_nonfinite_quote_keeps_holding_facts(
    field,
    value,
    availability,
    code,
    kind,
):
    raw = _rebalance_request()
    if field == "quote":
        raw["holdings"][0]["quote"] = value
        path = ("holdings", 0, "quote")
    else:
        raw["holdings"][0]["quote"][field] = value
        path = ("holdings", 0, "quote", field)

    result = _analyze_rebalancer(raw)

    assert result["availability"] == availability
    assert result["normalized"] is None
    issue = _issue(result, code, path, kind)
    assert issue["related_indices"] == [0]
    holding = _holdings(result)["custody-alpha"]
    assert _value(holding["quantity"]) == "2"
    _unavailable(
        holding["current_value_native"],
        "input_missing" if availability == "needs_input" else "input_invalid",
    )
    _unavailable(
        holding["current_value_reporting"],
        "input_missing" if availability == "needs_input" else "input_invalid",
    )
    assert "asset-alpha" in _instruments(result)


@pytest.mark.parametrize(
    ("rate", "availability", "code", "kind", "reason"),
    [
        (
            None,
            "needs_input",
            "valuation_rate_required",
            "missing",
            "input_missing",
        ),
        (
            "NaN",
            "invalid",
            "invalid_decimal_syntax",
            "invalid",
            "input_invalid",
        ),
        (
            "Infinity",
            "invalid",
            "invalid_decimal_syntax",
            "invalid",
            "input_invalid",
        ),
        (
            "0",
            "invalid",
            "nonpositive_fx_rate",
            "invalid",
            "input_invalid",
        ),
    ],
)
def test_missing_invalid_and_nonfinite_fx_never_defaults_or_omits(
    rate,
    availability,
    code,
    kind,
    reason,
):
    raw = _rebalance_request(
        holdings=[
            _holding(
                currency="USD",
                quantity="2",
                price="25",
            )
        ]
    )
    raw["valuation_rates"] = [] if rate is None else [_rate("USD", rate)]

    result = _analyze_rebalancer(raw)

    assert result["availability"] == availability
    assert result["normalized"] is None
    issue = _issue(result, code, kind=kind)
    if code == "valuation_rate_required":
        assert issue["path"] == ["valuation_rates"]
        assert issue["related_indices"] == [0]
        assert issue["params"]["currency"] == "USD"
    holding = _holdings(result)["custody-alpha"]
    _money(holding["current_value_native"], "50", "USD")
    _unavailable(holding["current_value_reporting"], reason)
    instrument = _instruments(result)["asset-alpha"]
    _unavailable(instrument["current_value_reporting"], reason)
    _unavailable(result["totals"]["current_invested_reporting"], reason)


@pytest.mark.parametrize(
    ("target", "availability", "code", "kind", "reason"),
    [
        (None, "needs_input", "field_required", "missing", "input_missing"),
        (
            "NaN",
            "invalid",
            "invalid_decimal_syntax",
            "invalid",
            "input_invalid",
        ),
        (
            "Infinity",
            "invalid",
            "invalid_decimal_syntax",
            "invalid",
            "input_invalid",
        ),
        (
            "-1",
            "invalid",
            "target_percent_out_of_range",
            "invalid",
            "input_invalid",
        ),
        (
            "100.000000000001",
            "invalid",
            "target_percent_out_of_range",
            "invalid",
            "input_invalid",
        ),
    ],
)
def test_missing_and_nonfinite_target_preserve_current_market_facts(
    target,
    availability,
    code,
    kind,
    reason,
):
    raw = _rebalance_request(targets=[_target(percent=target)])
    result = _analyze_rebalancer(raw)

    assert result["availability"] == availability
    _issue(result, code, ("targets", 0, "target_percent"), kind)
    holding = _holdings(result)["custody-alpha"]
    _money(holding["current_value_reporting"], "50")
    _money(result["totals"]["current_invested_reporting"], "50")
    instrument = _instruments(result)["asset-alpha"]
    _ratio(instrument["current_weight_percent"], 5_000, 50, "percent")
    _unavailable(instrument["target_percent"], reason)
    _unavailable(instrument["target_value_reporting"], reason)
    _unavailable(instrument["value_gap_to_target_reporting"], reason)
    _unavailable(instrument["gap_to_target_pp"], reason)


def test_pac_missing_fx_preserves_native_pool_without_subset_budget():
    raw = _pac_request()
    raw["cash_balances"] = [{"currency": "USD", "amount": "10"}]

    result = _analyze_pac(raw)

    assert result["availability"] == "needs_input"
    issue = _issue(
        result,
        "valuation_rate_required",
        ("valuation_rates",),
        "missing",
    )
    assert issue["params"]["currency"] == "USD"
    pools = {pool["currency"]: pool for pool in _value(result["cash_pools"])}
    assert pools["USD"]["existing_amount"] == "10"
    assert pools["USD"]["combined_amount"] == "10"
    _unavailable(pools["USD"]["existing_reporting"], "input_missing")
    _unavailable(pools["USD"]["combined_reporting"], "input_missing")
    _unavailable(
        result["totals"]["investable_budget_reporting"],
        "input_missing",
    )
    _unavailable(
        _allocations(result)["asset-alpha"]["ideal_allocation_reporting"],
        "input_missing",
    )


@pytest.mark.parametrize("vector", ["cash_balances", "contributions"])
def test_unsupplied_cash_vector_is_unknown_while_explicit_empty_is_zero(vector):
    raw = _pac_request()
    raw[vector] = None

    missing = _analyze_pac(raw)

    assert missing["availability"] == "needs_input"
    issue = _issue(
        missing,
        "cash_vector_required",
        (vector,),
        "missing",
    )
    assert issue["params"]["vector"] == vector
    assert missing["normalized"] is None
    _unavailable(missing["cash_pools"], "input_missing")
    _unavailable(
        missing["totals"]["investable_budget_reporting"],
        "input_missing",
    )

    raw[vector] = []
    closed = _analyze_pac(raw)
    assert closed["availability"] == "ready"
    _money(closed["totals"]["investable_budget_reporting"], "0")
    assert _value(closed["cash_pools"]) == []


@pytest.mark.parametrize(
    ("basis", "quantity", "price", "expected"),
    [
        pytest.param(3, "9", "10", "30", id="basis-three"),
        pytest.param(100, "3.25", "98.5", "3.20125", id="basis-hundred"),
        pytest.param(1000, "2500", "4", "10", id="basis-thousand"),
        pytest.param(
            999_999_999_999,
            "999999999999",
            "1",
            "1",
            id="maximum-twelve-digit-basis",
        ),
    ],
)
def test_admitted_positive_quote_base_scales_exactly(
    basis,
    quantity,
    price,
    expected,
):
    raw = _rebalance_request(
        holdings=[
            _holding(
                quantity=quantity,
                price=price,
                basis=basis,
            )
        ]
    )
    result = _analyze_rebalancer(raw)

    assert result["availability"] == "ready"
    holding = _holdings(result)["custody-alpha"]
    _money(holding["current_value_native"], expected)
    _money(holding["current_value_reporting"], expected)
    _money(result["totals"]["current_invested_reporting"], expected)
    normalized = {item["row_key"]: item for item in result["normalized"]["holdings"]}
    assert normalized["custody-alpha"]["quote_base_quantity"] == basis
    assert Fraction(expected) == Fraction(quantity) * Fraction(price) / basis


def test_thirteen_digit_quote_base_is_typed_unsupported_at_its_input_path():
    raw = _rebalance_request(
        holdings=[
            _holding(
                quantity="1",
                price="1",
                basis=1_000_000_000_000,
            )
        ]
    )

    result = _analyze_rebalancer(raw)

    assert result["availability"] == "unsupported"
    assert result["normalized"] is None
    issue = _issue(
        result,
        "numeric_domain_exceeded",
        ("holdings", 0, "quote", "quote_base_quantity"),
        "unsupported",
    )
    assert issue["related_indices"] == [0]
    assert issue["params"]["unit"] == "quantity"
    assert issue["params"]["limit"] == 12

    holding = _holdings(result)["custody-alpha"]
    assert _value(holding["quantity"]) == "1"
    _unavailable(holding["current_value_native"], "outside_p1_domain")
    _unavailable(holding["current_value_reporting"], "outside_p1_domain")


def test_rebalancer_quote_basis_three_without_cancellation_is_typed_unsupported():
    raw = _rebalance_request(
        holdings=[
            _holding(
                quantity="1",
                price="1",
                basis=3,
            )
        ]
    )

    result = _analyze_rebalancer(raw)

    assert result["availability"] == "unsupported"
    issue = _issue(
        result,
        "numeric_domain_exceeded",
        ("holdings", 0, "quote"),
        "unsupported",
    )
    assert issue["related_indices"] == [0]
    assert issue["params"]["unit"] == "quote"
    assert issue["params"]["limit"] == 256

    holding = _holdings(result)["custody-alpha"]
    _unavailable(holding["current_value_native"], "outside_p1_domain")
    _unavailable(holding["current_value_reporting"], "outside_p1_domain")

    instrument = _instruments(result)["asset-alpha"]
    _unavailable(instrument["current_value_reporting"], "outside_p1_domain")
    _unavailable(instrument["current_weight_percent"], "outside_p1_domain")
    _unavailable(instrument["target_value_reporting"], "outside_p1_domain")
    _unavailable(
        instrument["value_gap_to_target_reporting"],
        "outside_p1_domain",
    )
    _unavailable(instrument["gap_to_target_pp"], "outside_p1_domain")

    _unavailable(
        result["totals"]["current_invested_reporting"],
        "outside_p1_domain",
    )
    _unavailable(result["totals"]["max_abs_gap_pp"], "outside_p1_domain")
    _unavailable(result["totals"]["squared_gap_pp2"], "outside_p1_domain")


def test_rebalancer_terminating_native_value_over_canonical_limit_is_typed_unsupported():
    quantity = "0.000000000001"
    raw_price = "0.000000000001"
    quote_base_quantity = 2**39
    with localcontext(decimal_context()):
        product = Decimal(quantity) * Decimal(raw_price)
        basis = Decimal(quote_base_quantity)
        native_value = product / basis
        assert native_value * basis == product
    canonical = decimal_text(native_value)
    assert canonical == ("0.000000000000000000000000000000000001818989403545856475830078125")
    assert len(canonical) == 65
    assert len(canonical) > P1_MAX_NATIVE_AMOUNT_CHARS == 52

    raw = _rebalance_request(
        holdings=[
            _holding(
                quantity=quantity,
                price=raw_price,
                basis=quote_base_quantity,
            )
        ]
    )

    result = _analyze_rebalancer(raw)

    assert result["availability"] == "unsupported"
    assert result["normalized"] is None
    issue = _issue(
        result,
        "numeric_domain_exceeded",
        ("holdings", 0, "quote"),
        "unsupported",
    )
    assert issue["related_indices"] == [0]
    assert issue["params"]["unit"] == "quote"
    assert issue["params"]["limit"] == 256

    holding = _holdings(result)["custody-alpha"]
    assert _value(holding["quantity"]) == quantity
    for field in ("current_value_native", "current_value_reporting"):
        _unavailable(holding[field], "outside_p1_domain")

    instrument = _instruments(result)["asset-alpha"]
    for field in (
        "current_value_reporting",
        "current_weight_percent",
        "target_value_reporting",
        "value_gap_to_target_reporting",
        "gap_to_target_pp",
    ):
        _unavailable(instrument[field], "outside_p1_domain")

    for field in (
        "current_invested_reporting",
        "max_abs_gap_pp",
        "squared_gap_pp2",
    ):
        _unavailable(result["totals"][field], "outside_p1_domain")


def test_rebalancer_quote_basis_three_with_cancellation_is_exact_and_ready():
    raw = _rebalance_request(
        holdings=[
            _holding(
                quantity="1",
                price="3",
                basis=3,
            )
        ]
    )

    result = _analyze_rebalancer(raw)

    assert result["availability"] == "ready"
    assert result["issues"] == []

    holding = _holdings(result)["custody-alpha"]
    _money(holding["current_value_native"], "1")
    _money(holding["current_value_reporting"], "1")

    instrument = _instruments(result)["asset-alpha"]
    _money(instrument["current_value_reporting"], "1")
    _ratio(instrument["current_weight_percent"], 100, 1, "percent")
    _money(instrument["target_value_reporting"], "1")
    _money(instrument["value_gap_to_target_reporting"], "0")
    _ratio(instrument["gap_to_target_pp"], 0, 1, "percentage_points")

    _money(result["totals"]["current_invested_reporting"], "1")
    _ratio(result["totals"]["max_abs_gap_pp"], 0, 1, "percentage_points")
    _ratio(
        result["totals"]["squared_gap_pp2"],
        0,
        1,
        "percentage_points_squared",
    )


def test_negative_inventory_is_unsupported_and_never_omitted():
    raw = _rebalance_request(holdings=[_holding(quantity="-0.001")])
    result = _analyze_rebalancer(raw)

    assert result["availability"] == "unsupported"
    assert result["normalized"] is None
    issue = _issue(
        result,
        "short_inventory_unsupported",
        ("holdings", 0, "quantity"),
        "unsupported",
    )
    assert issue["related_indices"] == [0]
    holding = _holdings(result)["custody-alpha"]
    _unavailable(holding["quantity"], "outside_p1_domain")
    _unavailable(holding["current_value_native"], "outside_p1_domain")
    _unavailable(holding["current_value_reporting"], "outside_p1_domain")
    assert "asset-alpha" in _instruments(result)


def _two_instrument_request(service: str) -> dict[str, object]:
    targets = [_target("asset-a", "50"), _target("asset-b", "50")]
    if service == "pac":
        return _pac_request(
            assets=[_asset("asset-a"), _asset("asset-b")],
            targets=targets,
        )
    return _rebalance_request(
        holdings=[
            _holding("custody-a", "asset-a"),
            _holding("custody-b", "asset-b"),
        ],
        targets=targets,
    )


@pytest.mark.parametrize(
    ("case", "availability", "expected_codes"),
    [
        (
            "missing-all",
            "needs_input",
            {"targets_required", "target_required"},
        ),
        ("missing-selected", "needs_input", {"target_required"}),
        (
            "orphan",
            "invalid",
            {"target_instrument_not_selected", "target_required"},
        ),
        (
            "duplicate",
            "invalid",
            {"duplicate_target_instrument", "target_required"},
        ),
        ("wrong-total", "invalid", {"target_total_not_100"}),
    ],
)
@pytest.mark.parametrize("service", ["pac", "rebalancer"])
def test_target_vector_is_complete_unique_selected_and_exactly_100(
    service,
    case,
    availability,
    expected_codes,
):
    raw = _two_instrument_request(service)
    if case == "missing-all":
        raw["targets"] = []
    elif case == "missing-selected":
        raw["targets"] = [_target("asset-a", "100")]
    elif case == "orphan":
        raw["targets"] = [
            _target("asset-a", "50"),
            _target("asset-orphan", "50"),
        ]
    elif case == "duplicate":
        raw["targets"] = [
            _target("asset-a", "50"),
            _target("asset-a", "50"),
        ]
    else:
        raw["targets"] = [
            _target("asset-a", "50"),
            _target("asset-b", "49.999999999999"),
        ]

    analyze = _analyze_pac if service == "pac" else _analyze_rebalancer
    result = analyze(raw)

    assert result["availability"] == availability
    assert result["normalized"] is None
    codes = {issue["code"] for issue in result["issues"]}
    assert expected_codes <= codes
    if "target_required" in expected_codes:
        missing = [issue for issue in result["issues"] if issue["code"] == "target_required"]
        assert missing
        assert all(issue["kind"] == "missing" for issue in missing)
    if case == "orphan":
        issue = _issue(
            result,
            "target_instrument_not_selected",
            kind="invalid",
        )
        assert issue["params"]["instrument_key"] == "asset-orphan"
    if case == "duplicate":
        issue = _issue(
            result,
            "duplicate_target_instrument",
            kind="invalid",
        )
        assert issue["related_indices"] == [0, 1]
    if case == "wrong-total":
        issue = _issue(
            result,
            "target_total_not_100",
            ("targets",),
            "invalid",
        )
        assert issue["related_indices"] == [0, 1]


def test_pac_duplicate_instrument_is_invalid_not_aggregated():
    raw = _pac_request(
        assets=[
            _asset("same-instrument", name="Custody-looking A"),
            _asset("same-instrument", name="Custody-looking B"),
        ],
        targets=[_target("same-instrument", "100")],
    )
    raw["cash_balances"] = [{"currency": "EUR", "amount": "10"}]

    result = _analyze_pac(raw)

    assert result["availability"] == "invalid"
    assert result["normalized"] is None
    issue = _issue(
        result,
        "duplicate_instrument",
        ("assets", 0, "instrument_key"),
        "invalid",
    )
    assert issue["related_indices"] == [0, 1]
    allocation = _allocations(result)["same-instrument"]
    _unavailable(allocation["ideal_allocation_reporting"], "input_invalid")


def test_duplicate_holding_row_key_is_invalid_but_source_rows_remain():
    raw = _rebalance_request(
        holdings=[
            _holding("duplicate-row", "asset-a", quantity="1"),
            _holding("duplicate-row", "asset-b", quantity="2"),
        ],
        targets=[_target("asset-a", "50"), _target("asset-b", "50")],
    )
    result = _analyze_rebalancer(raw)

    assert result["availability"] == "invalid"
    assert result["normalized"] is None
    issue = _issue(
        result,
        "duplicate_row_key",
        ("holdings", 0, "row_key"),
        "invalid",
    )
    assert issue["related_indices"] == [0, 1]
    assert [holding["instrument_key"] for holding in result["holdings"]] == ["asset-a", "asset-b"]
    assert [_value(holding["quantity"]) for holding in result["holdings"]] == [
        "1",
        "2",
    ]
    _unavailable(
        result["totals"]["current_invested_reporting"],
        "input_invalid",
    )


@pytest.mark.parametrize("service", ["pac", "rebalancer"])
@pytest.mark.parametrize(
    ("grid", "availability", "code"),
    [
        ({"mode": "whole", "quantity_step": "2"}, "ready", None),
        (
            {"mode": "fractional", "quantity_step": "0.125"},
            "ready",
            None,
        ),
        (
            {"mode": "whole", "quantity_step": "0.5"},
            "invalid",
            "noninteger_whole_step",
        ),
        (
            {"mode": "fractional", "quantity_step": "0"},
            "invalid",
            "nonpositive_quantity_step",
        ),
        (
            {"mode": None, "quantity_step": "1"},
            "needs_input",
            "field_required",
        ),
    ],
)
def test_optional_future_buy_grid_validation(
    service,
    grid,
    availability,
    code,
):
    if service == "pac":
        raw = _pac_request(assets=[_asset(buy_grid=grid)])
        path = ("assets", 0, "buy_grid")
        result = _analyze_pac(raw)
    else:
        raw = _rebalance_request(holdings=[_holding(quantity="2", buy_grid=grid)])
        path = ("holdings", 0, "buy_grid")
        result = _analyze_rebalancer(raw)
    assert result["availability"] == availability
    if code == "field_required":
        _issue(result, code, (*path, "mode"), "missing")
    elif code is not None:
        _issue(result, code, (*path, "quantity_step"), "invalid")


@pytest.mark.parametrize(
    ("mode", "step", "quantity", "off_grid"),
    [
        ("whole", "1", "10.125", True),
        ("fractional", "0.125", "10.125", False),
        ("fractional", "0.2", "10.125", True),
    ],
)
def test_existing_inventory_is_unchanged_and_off_grid_is_info_only(
    mode,
    step,
    quantity,
    off_grid,
):
    raw = _rebalance_request(
        holdings=[
            _holding(
                quantity=quantity,
                price="10",
                buy_grid={"mode": mode, "quantity_step": step},
            )
        ]
    )
    result = _analyze_rebalancer(raw)

    assert result["availability"] == "ready"
    holding = _holdings(result)["custody-alpha"]
    assert _value(holding["quantity"]) == quantity
    _money(holding["current_value_reporting"], "101.25")
    normalized = {item["row_key"]: item for item in result["normalized"]["holdings"]}["custody-alpha"]
    assert normalized["quantity"] == quantity
    assert normalized["buy_grid"] == {
        "mode": mode,
        "quantity_step": step,
    }
    issues = [issue for issue in result["issues"] if issue["code"] == "inventory_off_buy_grid"]
    assert len(issues) == int(off_grid)
    if off_grid:
        (issue,) = issues
        assert issue["kind"] == "info"
        assert issue["path"] == ["holdings", 0, "quantity"]
        assert issue["related_indices"] == [0]


@pytest.mark.parametrize(
    ("amount", "step", "availability", "code", "kind"),
    [
        ("0.3", "0.1", "ready", None, None),
        (
            "0.300000000001",
            "0.1",
            "invalid",
            "contribution_not_multiple_of_monetary_step",
            "invalid",
        ),
        ("0.03", None, "needs_input", "field_required", "missing"),
        ("0.03", "0", "invalid", "nonpositive_monetary_step", "invalid"),
        ("-1", "0.01", "invalid", "negative_contribution", "invalid"),
    ],
)
def test_contribution_monetary_step_is_positive_and_an_exact_multiple(
    amount,
    step,
    availability,
    code,
    kind,
):
    raw = _pac_request()
    raw["contributions"] = [_contribution(amount=amount, monetary_step=step)]
    result = _analyze_pac(raw)

    assert result["availability"] == availability
    if code is None:
        assert result["normalized"]["contributions"] == [
            {
                "currency": "EUR",
                "amount": amount,
                "monetary_step": step,
            }
        ]
        _money(result["totals"]["contributions_reporting"], amount)
    else:
        path_field = (
            "amount"
            if code
            in {
                "contribution_not_multiple_of_monetary_step",
                "negative_contribution",
            }
            else "monetary_step"
        )
        issue = _issue(
            result,
            code,
            ("contributions", 0, path_field),
            kind,
        )
        if code == "contribution_not_multiple_of_monetary_step":
            assert issue["params"]["unit"] == "native_amount"


@pytest.mark.parametrize(
    ("service", "path"),
    [
        ("pac", ("cash_balances", 0, "amount")),
        ("pac", ("contributions", 0, "amount")),
        ("pac", ("targets", 0, "target_percent")),
        ("rebalancer", ("holdings", 0, "quantity")),
        ("rebalancer", ("holdings", 0, "quote", "raw_price")),
        ("rebalancer", ("valuation_rates", 0, "rate_to_report")),
    ],
)
@pytest.mark.parametrize(
    "text",
    ["1000000000000", "0.0000000000001", "1.1234567890121"],
)
def test_nonzero_thirteenth_digit_is_unsupported_never_rounded(
    service,
    path,
    text,
):
    if service == "pac":
        raw = _pac_request()
        raw["cash_balances"] = [{"currency": "EUR", "amount": "0"}]
        raw["contributions"] = [_contribution("EUR", "0", "0.000000000001")]
        result_analyzer = _analyze_pac
    else:
        raw = _rebalance_request(holdings=[_holding(currency="USD" if path[0] == "valuation_rates" else "EUR")])
        raw["valuation_rates"] = [_rate("USD", "1")] if path[0] == "valuation_rates" else []
        result_analyzer = _analyze_rebalancer
    _set(raw, path, text)

    result = result_analyzer(raw)

    assert result["availability"] == "unsupported"
    assert result["normalized"] is None
    issue = _issue(
        result,
        "numeric_domain_exceeded",
        path,
        "unsupported",
    )
    assert issue["params"]["limit"] == 12


def test_maximum_admitted_whole_and_fraction_digits_are_preserved():
    maximum = "999999999999.123456789012"
    pac_raw = _pac_request()
    pac_raw["cash_balances"] = [{"currency": "EUR", "amount": maximum}]
    pac = _analyze_pac(pac_raw)
    assert pac["availability"] == "ready"
    _money(pac["totals"]["investable_budget_reporting"], maximum)
    assert pac["normalized"]["cash_balances"] == [{"currency": "EUR", "amount": maximum}]

    rebalance_raw = _rebalance_request(holdings=[_holding(quantity=maximum, price="1")])
    rebalancer = _analyze_rebalancer(rebalance_raw)
    assert rebalancer["availability"] == "ready"
    holding = _holdings(rebalancer)["custody-alpha"]
    assert _value(holding["quantity"]) == maximum
    _money(holding["current_value_reporting"], maximum)
