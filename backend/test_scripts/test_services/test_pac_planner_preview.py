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
    exact 5 % (672.85)."""
    payload = reb.request("f-13457", holdings={"asset-a": "7000", "asset-b": "6000"}, cash="457", weights={"asset-a": "0.5", "asset-b": "0.5"})
    result = _rebalancer_preview(payload, custom_reference_amount={"amount": "60", "currency": "EUR"})
    assert [row[0] for row in _table(result)] == [130, 340, 670, 1_300]
    assert exact_fraction(result.custom.distance_weight) == Fraction(60 * 13_457, 2 * 670 * 670)


def test_preview_current_values_and_weights_per_item() -> None:
    """B4 test 7: T4 with a cash entry — A 5 000, B 4 800, cash 200 on F = 10 000: weights 1/2, 12/25, 1/50."""
    payload = reb.t4()
    payload["target_weights"] = [
        {"kind": "asset", "asset_id": "asset-a", "weight": "0.5", "minimum": None, "maximum": None},
        {"kind": "asset", "asset_id": "asset-b", "weight": "0.48", "minimum": None, "maximum": None},
        {"kind": "cash", "broker_id": reb.BROKER, "currency": "EUR", "weight": "0.02", "minimum": None, "maximum": None},
    ]
    result = _rebalancer_preview(payload)
    by_entry = {(item.kind, getattr(item, "asset_id", None) or f"{item.broker_id}:{item.currency}"): (_money(item.value), exact_fraction(item.weight)) for item in result.items}
    assert by_entry == {
        ("asset", "asset-a"): (5_000, Fraction(1, 2)),
        ("asset", "asset-b"): (4_800, Fraction(12, 25)),
        ("cash", f"{reb.BROKER}:EUR"): (200, Fraction(1, 50)),
    }


def test_pac_preview_total_is_the_cash_to_invest() -> None:
    """B4 test 8: the PAC's total is the cash it invests (the min fixture's 5 EUR); the PAC has no table."""
    request = PAC_TOOL_INPUT_ADAPTER.validate_python({**_pac_request(), "operation": "preview"})
    result = preview_pac_allocation(request)
    assert PAC_TOOL_OUTPUT_ADAPTER.validate_json(PAC_TOOL_OUTPUT_ADAPTER.dump_json(result), strict=True) == result
    assert (result.result_state, _money(result.total)) == ("preview_ready", 5)
    assert not hasattr(result, "table")


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
