"""B4 of project 67: the scenario preview of both Tools (contract §11, decisioni-REB §7.3, §11.2).

``preview_pac_allocation`` and ``preview_rebalancing`` (``services/pac_allocator/preview.py``) read the request of ``plan``
with the engine's normalizer and exact arithmetic, and return the numbers the screen shows before the calculation: the
total of the plan; for the Rebalancer today's value and weight of every target entry and the table «maximum acceptable
cost» with the «custom» fidelity both ways. No optimizer: the module never imports SCIP.

The figures are those of decisioni-REB §7.3, as exact fractions: the «6» of its table is 25/4 rounded on screen.
"""

from __future__ import annotations

import json
import subprocess
import sys
from fractions import Fraction

import pytest

from backend.app.schemas.pac_allocator.exact import exact_fraction
from backend.app.schemas.pac_allocator.preview import PAC_TOOL_INPUT_ADAPTER, PAC_TOOL_OUTPUT_ADAPTER, REBALANCER_TOOL_INPUT_ADAPTER, REBALANCER_TOOL_OUTPUT_ADAPTER
from backend.app.services.pac_allocator.planner import plan_rebalancing
from backend.app.services.pac_allocator.preview import preview_pac_allocation, preview_rebalancing
from backend.test_scripts.test_schemas.test_pac_planner_schemas import _pac_request
from backend.test_scripts.test_services import _reb_small_requests as reb


def _money(money) -> Fraction:
    return exact_fraction(money.value)


def _rebalancer_preview(payload: dict, **extra):
    request = REBALANCER_TOOL_INPUT_ADAPTER.validate_python({**payload, "operation": "preview", **extra})
    result = preview_rebalancing(request)
    # The real gate: every preview survives its service's output union, both ways.
    assert REBALANCER_TOOL_OUTPUT_ADAPTER.validate_json(REBALANCER_TOOL_OUTPUT_ADAPTER.dump_json(result), strict=True) == result
    # G5-2: the items cover F whole, «other cash» included (the screen's «Now» column sums to 100 %).
    if result.result_state == "preview_ready":
        assert sum((_money(item.value) for item in result.items), Fraction(0)) == _money(result.total)
    return result


def _twenty_thousand(**fields) -> dict:
    """A scenario worth F = 20 000 EUR: A 10 000, B 9 000, cash 1 000."""
    return reb.request("f-20000", holdings={"asset-a": "10000", "asset-b": "9000"}, cash="1000", weights={"asset-a": "0.5", "asset-b": "0.5"}, **fields)


def _table(result) -> list[tuple[Fraction, ...]]:
    return [(_money(row.misplaced), _money(row.cost_aware), _money(row.balanced), _money(row.faithful)) for row in result.table.rows]


def test_preview_table_on_twenty_thousand() -> None:
    """B4 test 3: rows 200, 500, 1 000, 2 000; at most 1 / 4 / 16, 25/4 / 25 / 100, 25 / 100 / 400, 100 / 400 / 1 600 (cost
    aware ¼, balanced 1, faithful 4); the reference is the 1 000 row; the λ of the levels travel with the table."""
    result = _rebalancer_preview(_twenty_thousand())
    assert result.result_state == "preview_ready" and _money(result.total) == 20_000
    assert _table(result) == [
        (200, 1, 4, 16),
        (500, Fraction(25, 4), 25, 100),
        (1_000, 25, 100, 400),
        (2_000, 100, 400, 1_600),
    ]
    assert [row.reference for row in result.table.rows] == [False, False, True, False]
    weights = result.table.level_weights
    assert (exact_fraction(weights.cost_aware), exact_fraction(weights.balanced), exact_fraction(weights.faithful)) == (Fraction(1, 4), 1, 4)
    assert result.custom is None and all(row.custom is None for row in result.table.rows)


def test_preview_custom_from_euros_gives_lambda_and_column() -> None:
    """B4 test 4: 60 EUR on the reference row give λ = 3/5, and the column 12/5 (2.4) / 15 / 60 / 240."""
    result = _rebalancer_preview(_twenty_thousand(), custom_reference_amount={"amount": "60", "currency": "EUR"})
    assert (exact_fraction(result.custom.distance_weight), _money(result.custom.reference_amount)) == (Fraction(3, 5), 60)
    assert [_money(row.custom) for row in result.table.rows] == [Fraction(12, 5), 15, 60, 240]


def test_preview_custom_from_lambda_gives_the_euros() -> None:
    """B4 test 5: a custom λ = 3/5 gives back 60 EUR and the same column: the round trip is exact."""
    result = _rebalancer_preview(_twenty_thousand(fidelity={"kind": "custom", "lambda": "0.6"}))
    assert (exact_fraction(result.custom.distance_weight), _money(result.custom.reference_amount)) == (Fraction(3, 5), 60)
    assert [_money(row.custom) for row in result.table.rows] == [Fraction(12, 5), 15, 60, 240]


def test_preview_rows_follow_the_scenario_total() -> None:
    """B4 test 6: on 13 457 EUR the rows are 130, 340, 670, 1 300, and λ is computed with 670, the figure shown, never the
    exact 5 % (672.85): 60·13 457/(2·670²), to six significant digits (Q1)."""
    payload = reb.request("f-13457", holdings={"asset-a": "7000", "asset-b": "6000"}, cash="457", weights={"asset-a": "0.5", "asset-b": "0.5"})
    result = _rebalancer_preview(payload, custom_reference_amount={"amount": "60", "currency": "EUR"})
    assert [row[0] for row in _table(result)] == [130, 340, 670, 1_300]
    assert exact_fraction(result.custom.distance_weight) == Fraction(899_332, 1_000_000)


def test_preview_current_values_and_weights_per_item() -> None:
    """B4 test 7: T4 with a cash entry — A 5 000, B 4 800, cash 200 on F = 10 000: weights 1/2, 12/25, 1/50."""
    payload = reb.t4()
    payload["target_weights"] = [
        {"kind": "asset", "asset_id": "asset-a", "weight": "0.5", "minimum": None, "maximum": None},
        {"kind": "asset", "asset_id": "asset-b", "weight": "0.48", "minimum": None, "maximum": None},
        {"kind": "cash", "broker_id": reb.BROKER, "currency": "EUR", "weight": "0.02", "minimum": None, "maximum": None},
    ]
    result = _rebalancer_preview(payload)
    by_entry = {(item.kind, getattr(item, "asset_id", None) or f"{item.broker_id}:{item.currency}"): (_money(item.value), exact_fraction(item.weight)) for item in result.items if item.kind != "other_cash"}
    assert by_entry == {
        ("asset", "asset-a"): (5_000, Fraction(1, 2)),
        ("asset", "asset-b"): (4_800, Fraction(12, 25)),
        ("cash", f"{reb.BROKER}:EUR"): (200, Fraction(1, 50)),
    }


def test_preview_other_cash_is_an_item_of_its_own() -> None:
    """G5-2 of project 67: «Altra cassa», the cash outside the cash entries, has its value and weight today, from the engine
    (the frontend may not subtract, N1). T4 (A 5 000, B 4 800, cash 200): without a cash entry the 200 are other cash, 1/50
    of F; with the entry on that cell there is none left, 0."""
    payload = reb.t4()
    payload["target_weights"] = [
        {"kind": "asset", "asset_id": "asset-a", "weight": "0.5", "minimum": None, "maximum": None},
        {"kind": "asset", "asset_id": "asset-b", "weight": "0.5", "minimum": None, "maximum": None},
    ]
    other = [item for item in _rebalancer_preview(payload).items if item.kind == "other_cash"]
    assert [(_money(item.value), exact_fraction(item.weight)) for item in other] == [(200, Fraction(1, 50))]

    payload["target_weights"] = [*payload["target_weights"][:1], {**payload["target_weights"][1], "weight": "0.48"}, {"kind": "cash", "broker_id": reb.BROKER, "currency": "EUR", "weight": "0.02", "minimum": None, "maximum": None}]
    other = [item for item in _rebalancer_preview(payload).items if item.kind == "other_cash"]
    assert [(_money(item.value), exact_fraction(item.weight)) for item in other] == [(0, 0)]


def test_preview_other_cash_counts_the_contributions_and_every_cash_entry_has_its_now() -> None:
    """G5-2: a contribution is money of F without a target of its own, so it is «other cash» too. T4 plus 300 of
    contribution: F = 10 300; without a cash entry other cash is 500. A cash entry still at 0 % (no weight, no limit: the
    engine leaves it out of the scenario) shows its 200 today all the same, and other cash keeps the 300."""
    payload = reb.t4()
    payload["contributions"] = [{"contribution_id": "salary", "label": "Salary", "amount": {"amount": "300", "currency": "EUR"}, "provenance_id": reb.PROVENANCE}]
    result = _rebalancer_preview(payload)
    assert _money(result.total) == 10_300
    assert [_money(item.value) for item in result.items if item.kind == "other_cash"] == [500]

    payload["target_weights"] = [*payload["target_weights"], {"kind": "cash", "broker_id": reb.BROKER, "currency": "EUR", "weight": "0", "minimum": None, "maximum": None}]
    items = _rebalancer_preview(payload).items
    assert [(item.broker_id, _money(item.value)) for item in items if item.kind == "cash"] == [(reb.BROKER, 200)]
    assert [_money(item.value) for item in items if item.kind == "other_cash"] == [300]


def test_preview_counts_a_positions_only_broker_in_f_and_today() -> None:
    """Q-F3a-5b of project 67: a position at a Broker outside the scenario counts in F and in «Now». T4 (A 5 000, B 4 800,
    cash 200) plus 1 000 of A at a positions-only Broker: F = 11 000, A today 6 000."""
    result = _rebalancer_preview(reb.with_positions_only_broker(reb.t4()))

    assert result.result_state == "preview_ready" and _money(result.total) == 11_000
    by_asset = {item.asset_id: _money(item.value) for item in result.items if item.kind == "asset"}
    assert by_asset == {"asset-a": 6_000, "asset-b": 4_800}


def test_pac_preview_total_is_the_cash_to_invest() -> None:
    """B4 test 8: the PAC's total is the cash it invests (the min fixture's 5 EUR); the PAC has no table."""
    request = PAC_TOOL_INPUT_ADAPTER.validate_python({**_pac_request(), "operation": "preview"})
    result = preview_pac_allocation(request)
    assert PAC_TOOL_OUTPUT_ADAPTER.validate_json(PAC_TOOL_OUTPUT_ADAPTER.dump_json(result), strict=True) == result
    assert (result.result_state, _money(result.total)) == ("preview_ready", 5)
    assert not hasattr(result, "table")


def test_preview_counts_targets_that_do_not_sum_to_one_and_the_plan_still_refuses_them() -> None:
    """F3a step 8 of project 67: the preview counts while the user is still typing the targets (the plan's «even incomplete»).
    F, today's items and the table do not depend on the weights: with A and B at 30 % each (total 60 %) T4 still previews
    F = 10 000 (the screen shows the control total itself: the ready preview carries no error); the plan refuses the same
    request as before, with `allocation.target_total_not_one`."""
    payload = reb.t4()
    for entry in payload["target_weights"]:
        entry["weight"] = "0.3"
    # A cash entry with a weight only (no limit) is still an entry of the counted scenario.
    payload["target_weights"].append({"kind": "cash", "broker_id": reb.BROKER, "currency": "EUR", "weight": "0.1", "minimum": None, "maximum": None})

    result = _rebalancer_preview(payload)

    assert result.result_state == "preview_ready" and _money(result.total) == 10_000
    assert {item.asset_id: _money(item.value) for item in result.items if item.kind == "asset"} == {"asset-a": 5_000, "asset-b": 4_800}
    assert [(item.broker_id, _money(item.value)) for item in result.items if item.kind == "cash"] == [(reb.BROKER, 200)]
    assert result.issues == []
    plan = plan_rebalancing(REBALANCER_TOOL_INPUT_ADAPTER.validate_python(payload))
    assert (plan.availability, [issue.code for issue in plan.issues]) == ("invalid", ["allocation.target_total_not_one"])


def test_preview_numbers_do_not_depend_on_the_weights() -> None:
    """What the preview answers reads no weight: the same scenario with complete weights and with 30 % + 30 % gives the same
    total, items, table and limit problems (the counted scenario's neutral weights never show)."""
    complete = reb.t4()
    complete["target_weights"][0]["maximum"] = {"kind": "amount", "amount": {"amount": "100", "currency": "EUR"}}
    incomplete = reb.t4()
    incomplete["target_weights"][0]["maximum"] = {"kind": "amount", "amount": {"amount": "100", "currency": "EUR"}}
    for entry in incomplete["target_weights"]:
        entry["weight"] = "0.3"

    left, right = _rebalancer_preview(complete), _rebalancer_preview(incomplete)

    assert (left.total, left.items, left.table, [issue.code for issue in left.limit_problems]) == (right.total, right.items, right.table, [issue.code for issue in right.limit_problems])
    assert [issue.code for issue in left.limit_problems] == ["allocation.bound_max_below_current"]


def test_plan_refusal_of_incomplete_targets_is_unchanged() -> None:
    """The counted scenario is the preview's only: ``plan`` answers incomplete targets exactly as before, with the target
    total's issue alone (no limit cross check is run for it)."""
    payload = reb.t4()
    payload["target_weights"][0]["maximum"] = {"kind": "amount", "amount": {"amount": "100", "currency": "EUR"}}
    for entry in payload["target_weights"]:
        entry["weight"] = "0.3"

    plan = plan_rebalancing(REBALANCER_TOOL_INPUT_ADAPTER.validate_python(payload))

    assert (plan.availability, [issue.code for issue in plan.issues]) == ("invalid", ["allocation.target_total_not_one"])


def test_pac_preview_counts_targets_that_do_not_sum_to_one() -> None:
    """The same for the PAC: its total is the cash it invests, whatever the weights say so far."""
    payload = _pac_request()
    for entry in payload["target_weights"]:
        entry["weight"] = "0.1"
    request = PAC_TOOL_INPUT_ADAPTER.validate_python({**payload, "operation": "preview"})

    result = preview_pac_allocation(request)

    assert (result.result_state, _money(result.total)) == ("preview_ready", 5)
    assert result.issues == []


def _without_a_price(payload: dict) -> dict:
    payload["assets"][0]["quote"] = None
    return payload


@pytest.mark.parametrize("product", ["pac", "rebalancer"])
def test_preview_without_a_price_answers_needs_input(product: str) -> None:
    """B4 test 9: a missing price answers ``needs_input`` with the code of ``plan``, and no number."""
    if product == "pac":
        result = preview_pac_allocation(PAC_TOOL_INPUT_ADAPTER.validate_python({**_without_a_price(_pac_request()), "operation": "preview"}))
        assert PAC_TOOL_OUTPUT_ADAPTER.validate_python(result.model_dump(mode="python")) == result
    else:
        result = _rebalancer_preview(_without_a_price(reb.t4()))
    assert (result.result_state, result.availability) == ("preview_needs_input", "needs_input")
    assert "allocation.price_missing" in {issue.code for issue in result.issues}
    assert not hasattr(result, "total")


def test_preview_with_zero_total_has_no_table() -> None:
    """B4 test 10: a portfolio worth nothing has no total to scale: no table, and the answer says why with its code."""
    payload = reb.t4()
    payload["existing_cash"] = []
    for holding in payload["holdings"]:
        holding["planning_quantity"] = "0"
    result = _rebalancer_preview(payload)
    assert result.result_state == "preview_needs_input"
    assert "portfolio_rebalancer.nonpositive_current_portfolio" in {issue.code for issue in result.issues}
    assert not hasattr(result, "table")


_NO_SCIP_PROBE = """
import sys
from backend.app.schemas.pac_allocator.preview import REBALANCER_TOOL_INPUT_ADAPTER
from backend.app.services.pac_allocator.preview import preview_rebalancing
request = REBALANCER_TOOL_INPUT_ADAPTER.validate_json(sys.stdin.read())
result = preview_rebalancing(request)
assert result.result_state == "preview_ready", result
assert "pyscipopt" not in sys.modules, "the preview imported SCIP"
assert "backend.app.services.pac_allocator.solver" not in sys.modules, "the preview imported the solver"
print("PREVIEW-WITHOUT-SCIP-OK")
"""


def test_preview_never_imports_or_calls_scip() -> None:
    """B4 test 11 (model: the SCIP isolation test of the planner): in a fresh interpreter the preview of T4 runs to
    ``ready`` with neither ``pyscipopt`` nor the solver module ever imported."""
    payload = json.dumps({**reb.t4(), "operation": "preview"})
    completed = subprocess.run([sys.executable, "-c", _NO_SCIP_PROBE], input=payload, capture_output=True, text=True, timeout=120, check=False)
    assert completed.returncode == 0, completed.stderr[-2_000:]
    assert "PREVIEW-WITHOUT-SCIP-OK" in completed.stdout


def test_preview_target_first_has_no_column() -> None:
    """B4 test 12 (M33): «Target first» has no maximum, so no custom column; the three levels stay."""
    result = _rebalancer_preview(_twenty_thousand(fidelity={"kind": "target_first"}))
    assert result.custom is None and all(row.custom is None for row in result.table.rows)
    assert _table(result)[2] == (1_000, 25, 100, 400)


def test_preview_with_a_total_that_does_not_terminate() -> None:
    """A USD Asset at 1.085 USD a EUR makes ``F`` a ratio with no decimal form: the preview is still ready, survives the
    output union both ways, and every cell is the formula of its row (the schema checks it exactly)."""
    payload = reb.request("f-usd", holdings={"asset-a": "5000", "asset-b": "40"}, cash="300", weights={"asset-a": "0.5", "asset-b": "0.5"}, prices={"asset-b": "100"})
    payload["assets"][1]["quote"]["currency"] = "USD"
    payload["fx_rates"] = {"EUR/USD": "1.085"}
    payload["brokers"][0]["capabilities"].append({"kind": "monetary_amount", "capability_id": "cap-usd-amount", "order_amount_step": {"amount": "1", "currency": "USD"}})
    payload["brokers"][0]["fee_schedules"].append({"fee_schedule_id": "fee-cap-usd-amount", "capability_id": "cap-usd-amount", "side": "buy", "fixed_fee": {"amount": "5", "currency": "USD"}, "rate": "0"})
    route = next(route for route in payload["order_routes"] if route["asset_id"] == "asset-b")
    route.update(capability_id="cap-usd-amount", fee_schedule_id="fee-cap-usd-amount")
    result = _rebalancer_preview(payload, custom_reference_amount={"amount": "60", "currency": "EUR"})
    total = _money(result.total)
    assert result.result_state == "preview_ready" and total == 5_300 + Fraction(4_000_000, 1_085)
    # 1 085 = 5 · 7 · 31: the 7 and the 31 stay in the denominator, so no decimal holds F.
    assert total.denominator % 217 == 0


def test_preview_result_fits_its_byte_cap_on_a_large_request() -> None:
    """The preview answers one row per target entry, smaller than the entry in the request: on 120 Assets and 10 cash entries,
    with ratio weights, the result is smaller than the request, so the plan's result cap (512 KiB, twice the parameter cap)
    holds any preview a request can ask for."""
    weights = {f"asset-{index:03d}": "0.0075" for index in range(120)}
    payload = reb.request("large", holdings={asset: str(37 + index) for index, asset in enumerate(weights)}, cash="1234.57", weights=weights)
    payload["target_weights"] += [{"kind": "cash", "broker_id": reb.BROKER, "currency": currency, "weight": "0.01", "minimum": None, "maximum": None} for currency in ("EUR", "USD", "CHF", "GBP", "JPY", "SEK", "NOK", "DKK", "PLN", "CZK")]
    payload["fx_rates"] = dict.fromkeys(("EUR/USD", "CHF/EUR", "EUR/GBP", "EUR/JPY", "EUR/SEK", "EUR/NOK", "DKK/EUR", "EUR/PLN", "CZK/EUR"), "1.1")
    result = _rebalancer_preview(payload)
    assert result.result_state == "preview_ready", [issue.code for issue in result.issues]
    size = len(REBALANCER_TOOL_OUTPUT_ADAPTER.dump_json(result))
    assert size < len(json.dumps({**payload, "operation": "preview"})), size


# --------------------------------------------------------------------------
# The consultant's answer to the B4 checkpoint: Q1 (the custom λ rounded in the backend) and Q2 (limit problems)
# --------------------------------------------------------------------------


def _cents(value: Fraction) -> Fraction:
    """``value`` to the cent, half up: how the screen shows an amount."""
    return Fraction(int(value * 100 + Fraction(1, 2)), 100)


def test_custom_lambda_round_trip_is_stable() -> None:
    """Q1: on 13 457 EUR, 60 EUR give λ rounded to 6 significant digits, with the euros and the column derived from that λ;
    sending that λ back gives the same λ and again 60.00 EUR on the reference row."""
    payload = reb.request("f-13457", holdings={"asset-a": "7000", "asset-b": "6000"}, cash="457", weights={"asset-a": "0.5", "asset-b": "0.5"})
    first = _rebalancer_preview(payload, custom_reference_amount={"amount": "60", "currency": "EUR"})
    lam = exact_fraction(first.custom.distance_weight)
    assert lam != Fraction(60 * 13_457, 2 * 670 * 670)
    assert len(str(lam.numerator).strip("0")) <= 6 and all(prime in (2, 5) for prime in _prime_factors(lam.denominator))
    assert _cents(_money(first.custom.reference_amount)) == 60
    sent = _decimal_text(lam)
    second = _rebalancer_preview({**payload, "target_fidelity": {"kind": "custom", "lambda": sent}})
    assert exact_fraction(second.custom.distance_weight) == lam
    assert _cents(_money(second.custom.reference_amount)) == 60
    assert [_money(row.custom) for row in second.table.rows] == [_money(row.custom) for row in first.table.rows]


def _prime_factors(n: int) -> set[int]:
    found, factor = set(), 2
    while factor * factor <= n:
        while n % factor == 0:
            found.add(factor)
            n //= factor
        factor += 1
    return found | ({n} if n > 1 else set())


def _decimal_text(value: Fraction) -> str:
    """A terminating fraction as plain decimal text."""
    scale = 0
    while (value * 10**scale).denominator != 1:
        scale += 1
    digits = str(int(value * 10**scale)).rjust(scale + 1, "0")
    return digits if scale == 0 else f"{digits[:-scale]}.{digits[-scale:]}"


def test_a_tiny_custom_amount_never_gives_a_zero_lambda() -> None:
    """Q1: 0.01 EUR on F = 200 000 EUR (reference row 10 000) gives λ = 1/100 000, still positive at 6 significant digits."""
    payload = reb.request("f-200000", holdings={"asset-a": "100000", "asset-b": "90000"}, cash="10000", weights={"asset-a": "0.5", "asset-b": "0.5"})
    result = _rebalancer_preview(payload, custom_reference_amount={"amount": "0.01", "currency": "EUR"})
    assert exact_fraction(result.custom.distance_weight) == Fraction(1, 100_000)


def _with_limits(payload: dict, *, minimum: str | None = None, maximum: str | None = None) -> dict:
    entry = next(entry for entry in payload["target_weights"] if entry.get("asset_id") == "asset-a")
    if minimum is not None:
        entry["minimum"] = {"kind": "amount", "amount": {"amount": minimum, "currency": "EUR"}}
    if maximum is not None:
        entry["maximum"] = {"kind": "amount", "amount": {"amount": maximum, "currency": "EUR"}}
    return payload


LIMIT_PROBLEM_CASES = (
    pytest.param({"minimum": "6000", "maximum": "5500"}, "allocation.bound_min_above_max", id="min-above-max"),
    pytest.param({"minimum": "20000"}, "allocation.bounds_min_sum_exceeds_reference", id="min-over-the-total"),
    pytest.param({"maximum": "4000"}, "allocation.bound_max_below_current", id="max-below-current"),
)


@pytest.mark.parametrize(("limits", "code"), LIMIT_PROBLEM_CASES)
def test_preview_keeps_its_numbers_with_limit_problems(limits: dict, code: str) -> None:
    """Q2: the three cross checks of the limits keep the preview ready, with the total and today's items, and name the
    problem in ``limit_problems`` (same code, same entry); the plan still answers ``invalid``."""
    result = _rebalancer_preview(_with_limits(reb.t4(), **limits))
    assert result.result_state == "preview_ready"
    assert _money(result.total) == 10_000 and result.items
    assert {(problem.code, problem.path.entity_id) for problem in result.limit_problems} >= {(code, "asset-a")}
    assert not [issue for issue in result.issues if issue.severity == "error"]

    plan = plan_rebalancing(REBALANCER_TOOL_INPUT_ADAPTER.validate_python(_with_limits(reb.t4(), **limits)))
    assert plan.result_state == "invalid" and code in {issue.code for issue in plan.issues}


def test_a_limit_of_the_wrong_shape_still_makes_the_preview_invalid() -> None:
    """Q2: a single limit of the wrong shape (here a share over 100 %) stays ``preview_invalid``."""
    payload = reb.t4()
    payload["target_weights"][0]["maximum"] = {"kind": "share", "share": "1.5"}
    result = _rebalancer_preview(payload)
    assert result.result_state == "preview_invalid"
    assert "allocation.target_weight_out_of_range" in {issue.code for issue in result.issues}


def test_pac_preview_keeps_its_total_with_a_limit_problem() -> None:
    """Q2 for the PAC: a minimum over the cash it invests keeps the total and names the problem."""
    payload = {**_pac_request(), "operation": "preview"}
    payload["target_weights"][0]["minimum"] = {"kind": "amount", "amount": {"amount": "50", "currency": "EUR"}}
    result = preview_pac_allocation(PAC_TOOL_INPUT_ADAPTER.validate_python(payload))
    assert PAC_TOOL_OUTPUT_ADAPTER.validate_python(result.model_dump(mode="python")) == result
    assert result.result_state == "preview_ready" and _money(result.total) == 5
    assert "allocation.bounds_min_sum_exceeds_reference" in {problem.code for problem in result.limit_problems}
