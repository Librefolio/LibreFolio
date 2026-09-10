"""PURE P1 initial-state witnesses; no DB, server, provider or solver fixtures.

All expectations use literal decimals or independently calculated Fractions. The
public adapters are also exercised on actual results, not substitute wire models.
Catalogue ownership belongs to the coordinator: services / pac-analyze.
"""

from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from decimal import ROUND_DOWN, ROUND_UP, getcontext, localcontext
from fractions import Fraction
from pathlib import Path
from textwrap import dedent

import pytest

from backend.app.schemas.pac_allocator import (
    PAC_ANALYZE_INPUT_ADAPTER,
    PAC_ANALYZE_OUTPUT_ADAPTER,
)
from backend.app.services.pac_allocator import analyze_initial_state


def _row(
    key="Alfa/X",
    *,
    quantity="1",
    price="10",
    currency="EUR",
    basis=1,
    target="100",
    mode="whole",
    step="1",
    instrument="Alfa",
):
    return {
        "row_key": key,
        "instrument_key": instrument,
        "name": key,
        "initial_quantity": quantity,
        "quote": {
            "raw_price": price,
            "currency": currency,
            "quote_base_quantity": basis,
            "reference_date": "2026-09-08",
        },
        "target_percent": target,
        "buy_grid": {"mode": mode, "quantity_step": step},
    }


def _request(rows=None):
    return {
        "operation": "analyze",
        "report_currency": "EUR",
        "as_of_date": "2026-09-08",
        "rows": [_row()] if rows is None else rows,
        "cash_balances": [],
        "contributions": [],
        "valuation_rates": [],
    }


def _rate(currency="USD", value="0.9", reference_date="2026-09-08"):
    return {
        "currency": currency,
        "rate_to_report": value,
        "reference_date": reference_date,
    }


def _put(raw, path, value):
    """Address a field of this test's own, explicitly constructed input."""
    parent = raw
    for token in path[:-1]:
        parent = parent[token]
    parent[path[-1]] = value


def _facts_have_one_primary_reason(node):
    if isinstance(node, dict):
        if "reason_codes" in node:
            if node["availability"] == "available":
                assert node["value"] is not None
                assert node["reason_codes"] == []
            else:
                assert node["availability"] == "unavailable"
                assert node["value"] is None
                assert len(node["reason_codes"]) == 1
        for value in node.values():
            _facts_have_one_primary_reason(value)
    elif isinstance(node, list):
        for value in node:
            _facts_have_one_primary_reason(value)


def _analyze(raw):
    before = deepcopy(raw)
    request = PAC_ANALYZE_INPUT_ADAPTER.validate_python(raw)
    model_before = request.model_dump(mode="json")
    result = analyze_initial_state(request)
    emitted = PAC_ANALYZE_OUTPUT_ADAPTER.dump_json(result)
    decoded = PAC_ANALYZE_OUTPUT_ADAPTER.validate_json(emitted)
    assert PAC_ANALYZE_OUTPUT_ADAPTER.dump_json(decoded) == emitted
    assert raw == before
    assert request.model_dump(mode="json") == model_before
    wire = json.loads(emitted)
    assert wire["operation"] == "analyze"
    assert wire["result_kind"] == "initial_state_analysis"
    assert wire["numeric_policy_id"] == "pac-initial-state-v1"
    assert wire["trade_feasibility"] == "not_evaluated"
    assert wire["optimization"] == "not_run"
    assert (wire["normalized"] is not None) == (wire["availability"] == "ready")
    for issue in wire["issues"]:
        assert issue["related_row_indices"] == sorted(set(issue["related_row_indices"]))
        assert all(type(index) is int and 0 <= index < len(wire["rows"]) for index in issue["related_row_indices"])
    _facts_have_one_primary_reason(wire)
    return wire


def _rows(result):
    """Use identity for ordinary facts; ordered assertions have their own test."""
    by_key = {row["row_key"]: row for row in result["rows"]}
    assert len(by_key) == len(result["rows"]), "This helper requires unique row keys"
    return by_key


def _value(fact):
    assert fact["availability"] == "available", fact
    assert fact["reason_codes"] == []
    return fact["value"]


def _unavailable(fact, reason=None):
    assert fact["availability"] == "unavailable", fact
    assert fact["value"] is None
    assert len(fact["reason_codes"]) == 1
    if reason is not None:
        assert fact["reason_codes"] == [reason]


def _money(fact, amount, currency="EUR"):
    assert _value(fact) == {"currency": currency, "amount": amount}


def _issue(result, code, path=None, kind=None):
    matches = [issue for issue in result["issues"] if issue["code"] == code and (path is None or issue["path"] == list(path))]
    assert len(matches) == 1, (code, path, result["issues"])
    (found,) = matches
    if kind is not None:
        assert found["kind"] == kind
    return found


def _truncate_28(value):
    """Independent integer-only oracle, including tiny negatives and exact zero."""
    scaled = abs(value.numerator) * 10**28 // value.denominator
    integer, fraction = divmod(scaled, 10**28)
    suffix = f"{fraction:028d}".rstrip("0")
    text = f"{integer}.{suffix}" if suffix else str(integer)
    return f"-{text}" if value < 0 and scaled else text


def _ratio(fact, numerator, denominator, unit):
    value = _value(fact)
    expected_numerator = Fraction(numerator)
    expected_denominator = Fraction(denominator)
    assert expected_denominator > 0
    # Check the authoritative unreduced evidence, not merely a rounded quotient.
    assert Fraction(value["numerator"]) == expected_numerator
    assert Fraction(value["denominator"]) == expected_denominator
    exact = expected_numerator / expected_denominator
    assert value["unit"] == unit
    assert value["approximation_decimal_places"] == 28
    assert value["approximation"] == _truncate_28(exact)
    assert value["approximation_exact"] is (Fraction(value["approximation"]) == exact)
    assert abs(exact - Fraction(value["approximation"])) < Fraction(1, 10**28)


def _cash_witness():
    raw = _request(
        [
            _row("Alfa/X", quantity="10", target="50"),
            _row("Alfa/Y", quantity="0", target="50"),
        ]
    )
    raw["cash_balances"] = [
        {"currency": "EUR", "amount": "0.005"},
        {"currency": "USD", "amount": "10"},
    ]
    raw["contributions"] = [{"currency": "EUR", "amount": "5"}]
    raw["valuation_rates"] = [_rate()]
    return raw


def test_empty_draft_is_unknown_not_an_empty_zero_portfolio():
    result = _analyze({"operation": "analyze"})
    assert result["availability"] == "needs_input"
    assert result["rows"] == []
    _issue(result, "rows_required", ("rows",), "missing")
    for vector in ("cash_balances", "contributions"):
        _issue(result, "cash_vector_required", (vector,), "missing")
    _unavailable(result["totals"]["initial_invested_reporting"])
    _unavailable(result["totals"]["max_abs_gap_pp"])
    _unavailable(result["totals"]["squared_gap_pp2"])
    _unavailable(result["cash_pools"])


@pytest.mark.parametrize(
    ("quantity", "price", "basis", "expected"),
    [("10.125", "10", 1, "101.25"), ("3.25", "98.5", 100, "3.20125")],
)
def test_custody_fractions_are_not_rounded_to_the_whole_buy_grid(quantity, price, basis, expected):
    result = _analyze(_request([_row(quantity=quantity, price=price, basis=basis)]))
    assert result["availability"] == "ready"
    row = _rows(result)["Alfa/X"]
    assert _value(row["quantity"]) == quantity
    _money(row["initial_value_native"], expected)
    _money(row["initial_value_reporting"], expected)
    _money(result["totals"]["initial_invested_reporting"], expected)
    assert Fraction(expected) == Fraction(quantity) * Fraction(price) / basis
    normalized = {item["row_key"]: item for item in result["normalized"]["rows"]}["Alfa/X"]
    assert normalized["initial_quantity"] == quantity
    assert normalized["buy_grid"] == {"mode": "whole", "quantity_step": "1"}
    issue = _issue(result, "inventory_off_buy_grid", ("rows", 0, "initial_quantity"), "info")
    assert issue["related_row_indices"] == [0]


def test_repeated_instrument_is_scored_per_compound_row_not_aggregated():
    result = _analyze(_request([_row("Alfa/X", quantity="10", target="50"), _row("Alfa/Y", quantity="0", target="50")]))
    assert result["availability"] == "ready"
    rows = _rows(result)
    assert rows["Alfa/X"]["instrument_key"] == rows["Alfa/Y"]["instrument_key"] == "Alfa"
    _money(result["totals"]["initial_invested_reporting"], "100")
    _ratio(rows["Alfa/X"]["current_weight_percent"], 10000, 100, "percent")
    _ratio(rows["Alfa/Y"]["current_weight_percent"], 0, 100, "percent")
    _ratio(rows["Alfa/X"]["deviation_pp"], 5000, 100, "percentage_points")
    _ratio(rows["Alfa/Y"]["deviation_pp"], -5000, 100, "percentage_points")
    _ratio(result["totals"]["max_abs_gap_pp"], 5000, 100, "percentage_points")
    _ratio(result["totals"]["squared_gap_pp2"], 50_000_000, 10000, "percentage_points_squared")
    assert _value(result["totals"]["squared_gap_pp2"])["approximation"] == "5000"
    assert "trades" not in result
    assert "proposals" not in result


def test_cash_is_pooled_once_and_valued_without_changing_native_currency():
    result = _analyze(_cash_witness())
    assert result["availability"] == "ready"
    pools = {pool["currency"]: pool for pool in _value(result["cash_pools"])}
    assert set(pools) == {"EUR", "USD"}
    assert pools["EUR"]["existing_amount"] == "0.005"
    assert pools["EUR"]["contribution_amount"] == "5"
    assert pools["EUR"]["combined_amount"] == "5.005"
    assert pools["USD"]["existing_amount"] == pools["USD"]["combined_amount"] == "10"
    assert pools["USD"]["contribution_amount"] == "0"
    _money(pools["USD"]["combined_reporting"], "9")
    _money(result["totals"]["existing_cash_reporting"], "9.005")
    _money(result["totals"]["contributions_reporting"], "5")
    _money(result["totals"]["cash_plus_contributions_reporting"], "14.005")
    assert Fraction("14.005") == Fraction("0.005") + Fraction("10") * Fraction("0.9") + 5
    assert all("broker" not in pool for pool in pools.values())
    balances = {item["currency"]: item["amount"] for item in result["normalized"]["cash_balances"]}
    assert balances == {"EUR": "0.005", "USD": "10"}


def test_missing_cash_fx_keeps_native_pools_but_not_a_subset_total():
    raw = _cash_witness()
    raw["valuation_rates"] = []
    result = _analyze(raw)
    assert result["availability"] == "needs_input"
    _issue(result, "valuation_rate_required", kind="missing")
    pools = {pool["currency"]: pool for pool in _value(result["cash_pools"])}
    assert pools["EUR"]["combined_amount"] == "5.005"
    assert pools["USD"]["combined_amount"] == "10"
    _money(pools["EUR"]["combined_reporting"], "5.005")
    _unavailable(pools["USD"]["existing_reporting"])
    _unavailable(pools["USD"]["combined_reporting"])
    _money(pools["USD"]["contribution_reporting"], "0")
    _unavailable(result["totals"]["existing_cash_reporting"])
    _unavailable(result["totals"]["cash_plus_contributions_reporting"])
    _money(result["totals"]["contributions_reporting"], "5")
    _money(result["totals"]["initial_invested_reporting"], "100")


def test_missing_nonzero_row_fx_never_renormalizes_the_known_subset():
    raw = _request([_row("Alfa/X", target="50"), _row("Alfa/Y", currency="USD", target="50")])
    result = _analyze(raw)
    assert result["availability"] == "needs_input"
    rows = _rows(result)
    _money(rows["Alfa/X"]["initial_value_reporting"], "10")
    _money(rows["Alfa/Y"]["initial_value_native"], "10", "USD")
    _unavailable(rows["Alfa/Y"]["initial_value_reporting"])
    _unavailable(result["totals"]["initial_invested_reporting"])
    for row in rows.values():
        _unavailable(row["current_weight_percent"])
        _unavailable(row["deviation_pp"])
    _unavailable(result["totals"]["max_abs_gap_pp"])
    _unavailable(result["totals"]["squared_gap_pp2"])


def test_explicit_zero_conversion_is_known_without_inventing_a_missing_fx_rate():
    raw = _request([_row("Alfa/X"), _row("Alfa/Y", quantity="0", currency="USD", target="0")])
    result = _analyze(raw)
    assert result["availability"] == "needs_input"
    _issue(result, "valuation_rate_required", kind="missing")
    rows = _rows(result)
    _money(rows["Alfa/Y"]["initial_value_native"], "0", "USD")
    _money(rows["Alfa/Y"]["initial_value_reporting"], "0")
    _money(result["totals"]["initial_invested_reporting"], "10")
    _ratio(rows["Alfa/X"]["current_weight_percent"], 1000, 10, "percent")
    _ratio(rows["Alfa/Y"]["current_weight_percent"], 0, 10, "percent")
    _ratio(result["totals"]["max_abs_gap_pp"], 0, 10, "percentage_points")


def test_zero_initial_investment_can_be_ready_but_has_no_weights_or_score():
    raw = _request([_row(quantity="0")])
    raw["contributions"] = [{"currency": "EUR", "amount": "100"}]
    result = _analyze(raw)
    assert result["availability"] == "ready"
    _money(result["totals"]["initial_invested_reporting"], "0")
    _money(result["totals"]["cash_plus_contributions_reporting"], "100")
    row = _rows(result)["Alfa/X"]
    for fact in (
        row["current_weight_percent"],
        row["deviation_pp"],
        result["totals"]["max_abs_gap_pp"],
        result["totals"]["squared_gap_pp2"],
    ):
        _unavailable(fact, "zero_initial_invested_value")


@pytest.mark.parametrize("vector", ["cash_balances", "contributions"])
def test_null_vector_is_unknown_while_explicit_empty_is_closed_zero(vector):
    raw = _request()
    raw[vector] = None
    missing = _analyze(raw)
    assert missing["availability"] == "needs_input"
    _issue(missing, "cash_vector_required", (vector,), "missing")
    _unavailable(missing["cash_pools"], "input_missing")
    _unavailable(missing["totals"]["cash_plus_contributions_reporting"])
    other_total = "contributions_reporting" if vector == "cash_balances" else "existing_cash_reporting"
    _money(missing["totals"][other_total], "0")
    raw[vector] = []
    complete = _analyze(raw)
    assert complete["availability"] == "ready"
    for total in ("existing_cash_reporting", "contributions_reporting", "cash_plus_contributions_reporting"):
        _money(complete["totals"][total], "0")


def test_closed_sparse_vectors_zero_fill_only_the_declared_active_universe():
    raw = _request([_row(currency="USD")])
    raw["cash_balances"] = [{"currency": "EUR", "amount": "10"}]
    raw["valuation_rates"] = [_rate()]
    result = _analyze(raw)
    pools = {item["currency"]: item for item in _value(result["cash_pools"])}
    assert set(pools) == {"EUR", "USD"}
    assert pools["USD"]["existing_amount"] == pools["USD"]["contribution_amount"] == "0"
    assert pools["EUR"]["combined_amount"] == "10"
    _money(result["totals"]["cash_plus_contributions_reporting"], "10")


@pytest.mark.parametrize("amount", [None, "12abc"])
def test_unresolved_vector_entry_cannot_supply_zero_for_omitted_currencies(amount):
    raw = _request([_row(currency="USD")])
    raw["valuation_rates"] = [_rate()]
    raw["cash_balances"] = [{"currency": "EUR", "amount": amount}]
    result = _analyze(raw)
    assert result["availability"] == ("needs_input" if amount is None else "invalid")
    _unavailable(result["cash_pools"])
    _unavailable(result["totals"]["existing_cash_reporting"])
    _money(result["totals"]["contributions_reporting"], "0")
    _money(result["totals"]["initial_invested_reporting"], "9")


@pytest.mark.parametrize("vector", ["cash_balances", "contributions", "valuation_rates"])
def test_duplicate_normalized_currency_is_invalid_and_not_summed(vector):
    raw = _request([_row(currency="USD")])
    raw["valuation_rates"] = [_rate()]
    if vector == "valuation_rates":
        raw[vector] = [_rate("USD", "0.9"), _rate(" usd ", "0.1"), _rate("usd", "1")]
    else:
        raw[vector] = [
            {"currency": "USD", "amount": "1"},
            {"currency": " usd ", "amount": "2"},
            {"currency": "usd", "amount": "3"},
        ]
    result = _analyze(raw)
    assert result["availability"] == "invalid"
    duplicate = _issue(result, "duplicate_currency", kind="invalid")
    assert duplicate["params"]["vector"] == vector
    assert duplicate["params"]["currency"] == "USD"
    if vector == "valuation_rates":
        _unavailable(_rows(result)["Alfa/X"]["initial_value_reporting"])
    else:
        _unavailable(result["cash_pools"], "input_invalid")
        total = "existing_cash_reporting" if vector == "cash_balances" else "contributions_reporting"
        _unavailable(result["totals"][total], "input_invalid")


def test_duplicate_row_keys_retain_each_input_row_and_one_group_issue():
    raw = _request([_row("same", quantity=str(index), target=target) for index, target in enumerate(("20", "30", "50"))])
    result = _analyze(raw)
    assert result["availability"] == "invalid"
    assert [(row["row_index"], row["row_key"], _value(row["quantity"])) for row in result["rows"]] == [(0, "same", "0"), (1, "same", "1"), (2, "same", "2")]
    assert _issue(result, "duplicate_row_key", kind="invalid")["related_row_indices"] == [0, 1, 2]


@pytest.mark.parametrize(
    ("raw_quantity", "canonical"),
    [
        ("999999999999.123456789012", "999999999999.123456789012"),
        ("0.000000000001", "0.000000000001"),
        ("000000000001.2300000000000", "1.23"),
        ("  +00010.125000000000000  ", "10.125"),
        ("-000.000000000000000", "0"),
        ("0" * 63 + "1", "1"),
        ("1." + "0" * 62, "1"),
    ],
)
def test_numeric_admission_normalizes_zero_padding_without_value_loss(raw_quantity, canonical):
    result = _analyze(_request([_row(quantity=raw_quantity, price="1")]))
    assert result["availability"] == "ready"
    row = _rows(result)["Alfa/X"]
    assert _value(row["quantity"]) == canonical
    _money(row["initial_value_native"], canonical)


@pytest.mark.parametrize(
    "path",
    [
        ("rows", 0, "initial_quantity"),
        ("rows", 0, "quote", "raw_price"),
        ("rows", 0, "target_percent"),
        ("rows", 0, "buy_grid", "quantity_step"),
        ("cash_balances", 0, "amount"),
        ("contributions", 0, "amount"),
        ("valuation_rates", 0, "rate_to_report"),
    ],
)
@pytest.mark.parametrize("text", ["1000000000000", "0.0000000000001", "1.1234567890121"])
def test_nonzero_thirteenth_digit_is_unsupported_not_rounded(path, text):
    raw = _request()
    raw["cash_balances"] = [{"currency": "EUR", "amount": "0"}]
    raw["contributions"] = [{"currency": "EUR", "amount": "0"}]
    raw["valuation_rates"] = [_rate()]
    _put(raw, path, text)
    result = _analyze(raw)
    assert result["availability"] == "unsupported"
    assert _issue(result, "numeric_domain_exceeded", path, "unsupported")["params"]["limit"] == 12
    if path == ("rows", 0, "initial_quantity"):
        _unavailable(_rows(result)["Alfa/X"]["quantity"], "outside_p1_domain")
        _unavailable(result["totals"]["initial_invested_reporting"])


@pytest.mark.parametrize(
    "path",
    [
        ("rows", 0, "initial_quantity"),
        ("rows", 0, "quote", "raw_price"),
        ("rows", 0, "target_percent"),
        ("rows", 0, "buy_grid", "quantity_step"),
        ("cash_balances", 0, "amount"),
        ("contributions", 0, "amount"),
        ("valuation_rates", 0, "rate_to_report"),
    ],
)
@pytest.mark.parametrize("text", ["1e3", "12abc", "NaN", "Infinity", "-Infinity", "1,25", "1_000", "1 000", "１２", "🧮" * 64])
def test_malformed_decimal_cells_are_domain_issues_not_cleaned_or_coerced(path, text):
    raw = _request()
    raw["cash_balances"] = [{"currency": "EUR", "amount": "0"}]
    raw["contributions"] = [{"currency": "EUR", "amount": "0"}]
    raw["valuation_rates"] = [_rate()]
    _put(raw, path, text)
    result = _analyze(raw)
    assert result["availability"] == "invalid"
    issue = _issue(result, "invalid_decimal_syntax", path, "invalid")
    assert issue["related_row_indices"] == ([0] if path[0] == "rows" else [])
    assert text not in json.dumps(result["issues"], ensure_ascii=False)


@pytest.mark.parametrize(("text", "code"), [(None, "field_required"), ("", "field_required"), (" ", "field_required"), ("+", "incomplete_decimal"), ("-.", "incomplete_decimal"), (".", "incomplete_decimal")])
def test_unfinished_numeric_cell_is_missing_not_zero(text, code):
    result = _analyze(_request([_row(quantity=text)]))
    assert result["availability"] == "needs_input"
    _issue(result, code, ("rows", 0, "initial_quantity"), "missing")
    _unavailable(_rows(result)["Alfa/X"]["quantity"], "input_missing")


@pytest.mark.parametrize(
    ("path", "value", "availability", "code"),
    [
        (("rows", 0, "initial_quantity"), "-0.001", "unsupported", "short_inventory_unsupported"),
        (("cash_balances", 0, "amount"), "-0.001", "unsupported", "initial_debt_unsupported"),
        (("contributions", 0, "amount"), "-0.001", "invalid", "negative_contribution"),
        (("rows", 0, "quote", "raw_price"), "0", "invalid", "nonpositive_price"),
        (("rows", 0, "quote", "raw_price"), "-1", "invalid", "nonpositive_price"),
        (("valuation_rates", 0, "rate_to_report"), "0", "invalid", "nonpositive_fx_rate"),
        (("valuation_rates", 0, "rate_to_report"), "-1", "invalid", "nonpositive_fx_rate"),
        (("rows", 0, "quote", "quote_base_quantity"), 2, "unsupported", "quote_basis_unsupported"),
        (("rows", 0, "quote", "quote_base_quantity"), 1000, "unsupported", "quote_basis_unsupported"),
        (("rows", 0, "quote", "quote_base_quantity"), 0, "invalid", "invalid_quote_basis"),
        (("rows", 0, "quote", "quote_base_quantity"), -1, "invalid", "invalid_quote_basis"),
        (("rows", 0, "quote", "quote_base_quantity"), None, "needs_input", "field_required"),
        (("rows", 0, "target_percent"), "-1", "invalid", "target_percent_out_of_range"),
        (("rows", 0, "target_percent"), "100.000000000001", "invalid", "target_percent_out_of_range"),
        (("rows", 0, "buy_grid", "quantity_step"), "0", "invalid", "nonpositive_quantity_step"),
        (("rows", 0, "buy_grid", "quantity_step"), "-1", "invalid", "nonpositive_quantity_step"),
        (("rows", 0, "buy_grid", "quantity_step"), "0.5", "invalid", "noninteger_whole_step"),
    ],
)
def test_domain_classification_for_sign_basis_target_and_buy_step(path, value, availability, code):
    raw = _request()
    raw["cash_balances"] = [{"currency": "EUR", "amount": "0"}]
    raw["contributions"] = [{"currency": "EUR", "amount": "0"}]
    raw["valuation_rates"] = [_rate()]
    _put(raw, path, value)
    result = _analyze(raw)
    assert result["availability"] == availability
    _issue(result, code, path)


@pytest.mark.parametrize(("mode", "step"), [("whole", "2"), ("fractional", "0.000000000001"), ("fractional", "0.3"), ("fractional", "2")])
def test_effective_buy_grid_accepts_any_admitted_positive_step_for_its_mode(mode, step):
    result = _analyze(_request([_row(quantity="1.125", mode=mode, step=step)]))
    assert result["availability"] == "ready"
    assert _value(_rows(result)["Alfa/X"]["quantity"]) == "1.125"
    _money(result["totals"]["initial_invested_reporting"], "11.25")


@pytest.mark.parametrize(("targets", "total"), [(("0.5", "0.5"), "1"), (("50", "49.99"), "99.99"), (("50", "49.999999999999"), "99.999999999999")])
def test_targets_must_sum_exactly_100_without_fraction_inference_or_rebalancing(targets, total):
    raw = _request([_row("Alfa/X", target=targets[0]), _row("Alfa/Y", target=targets[1])])
    result = _analyze(raw)
    assert result["availability"] == "invalid"
    _issue(result, "target_total_not_100", kind="invalid")
    assert Fraction(total) == sum(map(Fraction, targets))
    for key, target in zip(("Alfa/X", "Alfa/Y"), targets, strict=True):
        row = _rows(result)[key]
        assert _value(row["target_percent"]) == target
        _ratio(row["current_weight_percent"], 1000, 20, "percent")
        _unavailable(row["deviation_pp"])
    _unavailable(result["totals"]["max_abs_gap_pp"])


@pytest.mark.parametrize("target", [None, "abc"])
def test_unresolved_target_preserves_complete_market_values_and_weights(target):
    result = _analyze(_request([_row(target=target)]))
    assert result["availability"] == ("needs_input" if target is None else "invalid")
    row = _rows(result)["Alfa/X"]
    _money(row["initial_value_reporting"], "10")
    _money(result["totals"]["initial_invested_reporting"], "10")
    _ratio(row["current_weight_percent"], 1000, 10, "percent")
    _unavailable(row["target_percent"])
    _unavailable(row["deviation_pp"])
    _unavailable(result["totals"]["target_total_percent"])
    _unavailable(result["totals"]["squared_gap_pp2"])


def test_fractional_target_sum_of_exactly_100_is_ready():
    result = _analyze(_request([_row("Alfa/X", target="33.333333333333"), _row("Alfa/Y", target="66.666666666667")]))
    assert result["availability"] == "ready"
    assert _value(result["totals"]["target_total_percent"]) == "100"


@pytest.mark.parametrize(("path", "code"), [(("rows", 0, "name"), "field_required"), (("rows", 0, "quote"), "quote_required"), (("rows", 0, "buy_grid"), "grid_required")])
def test_missing_row_inputs_keep_other_independent_facts(path, code):
    raw = _request()
    _put(raw, path, None)
    result = _analyze(raw)
    assert result["availability"] == "needs_input"
    _issue(result, code, path, "missing")
    assert _value(_rows(result)["Alfa/X"]["quantity"]) == "1"


def test_currency_normalization_and_identity_rate_are_explicit_and_deterministic():
    raw = _request([_row(currency=" usd ")])
    raw["report_currency"] = " eur "
    raw["cash_balances"] = [{"currency": " usd ", "amount": "2"}, {"currency": "eur", "amount": "3"}]
    raw["valuation_rates"] = [_rate("usd", "0.9")]
    result = _analyze(raw)
    assert result["availability"] == "ready"
    state = result["normalized"]
    assert state["report_currency"] == "EUR"
    assert [item["currency"] for item in state["cash_balances"]] == ["EUR", "USD"]
    rates = {item["currency"]: item for item in state["valuation_rates"]}
    assert rates["EUR"]["rate_to_report"] == "1"
    assert rates["USD"]["rate_to_report"] == "0.9"
    assert len(rates) == len(state["valuation_rates"]) == 2
    _money(result["totals"]["initial_invested_reporting"], "9")


@pytest.mark.parametrize(("rate", "availability", "code"), [("1", "ready", "identity_rate_redundant"), ("2", "invalid", "identity_rate_mismatch")])
def test_supplied_identity_rate_cannot_redefine_reporting_currency(rate, availability, code):
    raw = _request()
    raw["valuation_rates"] = [_rate("EUR", rate)]
    result = _analyze(raw)
    assert result["availability"] == availability
    _issue(result, code)
    _money(result["totals"]["initial_invested_reporting"], "10")
    if availability == "ready":
        identity = [entry for entry in result["normalized"]["valuation_rates"] if entry["currency"] == "EUR"]
        assert len(identity) == 1
        (entry,) = identity
        assert entry["rate_to_report"] == "1"


def test_unused_rates_are_retained_without_creating_cash_or_active_currencies():
    raw = _request()
    raw["valuation_rates"] = [_rate(currency) for currency in ("USD", "GBP", "CHF", "JPY")]
    result = _analyze(raw)
    assert result["availability"] == "ready"
    assert {entry["currency"] for entry in result["normalized"]["valuation_rates"]} == {"EUR", "USD", "GBP", "CHF", "JPY"}
    assert len(result["normalized"]["valuation_rates"]) == 5
    assert {pool["currency"] for pool in _value(result["cash_pools"])} == {"EUR"}
    assert {issue["params"]["currency"] for issue in result["issues"] if issue["code"] == "unused_valuation_reference"} == {"USD", "GBP", "CHF", "JPY"}
    _money(result["totals"]["cash_plus_contributions_reporting"], "0")


@pytest.mark.parametrize("path", [("report_currency",), ("rows", 0, "quote", "currency"), ("cash_balances", 0, "currency"), ("valuation_rates", 0, "currency")])
def test_invalid_currency_is_not_silently_replaced_by_reporting_currency(path):
    raw = _request()
    raw["cash_balances"] = [{"currency": "EUR", "amount": "1"}]
    raw["valuation_rates"] = [_rate()]
    _put(raw, path, "BADCODE")
    result = _analyze(raw)
    assert result["availability"] == "invalid"
    _issue(result, "invalid_currency", path, "invalid")


def test_four_active_currencies_are_ready_but_five_are_unsupported_without_missing_rate_cascade():
    currencies = ("EUR", "USD", "GBP", "CHF")
    raw = _request([_row(currency, currency=currency, target="25") for currency in currencies])
    raw["valuation_rates"] = [_rate(currency, "1") for currency in currencies if currency != "EUR"]
    ready = _analyze(raw)
    assert ready["availability"] == "ready"
    assert {pool["currency"] for pool in _value(ready["cash_pools"])} == set(currencies)
    raw["cash_balances"] = [{"currency": "JPY", "amount": "1"}]
    raw["valuation_rates"] = []
    unsupported = _analyze(raw)
    assert unsupported["availability"] == "unsupported"
    assert _issue(unsupported, "currency_domain_exceeded", kind="unsupported")["params"]["limit"] == 4
    assert not any(issue["code"] == "valuation_rate_required" for issue in unsupported["issues"])
    _unavailable(unsupported["cash_pools"], "outside_p1_domain")


@pytest.mark.parametrize("path", [("as_of_date",), ("rows", 0, "quote", "reference_date"), ("valuation_rates", 0, "reference_date")])
@pytest.mark.parametrize("text", ["2026-02-30", "2026-2-01", "not-a-date", "0000-01-01"])
def test_dates_require_a_complete_real_calendar_date(path, text):
    raw = _request()
    raw["valuation_rates"] = [_rate()]
    _put(raw, path, text)
    result = _analyze(raw)
    assert result["availability"] == "invalid"
    _issue(result, "invalid_date", path, "invalid")


@pytest.mark.parametrize("source", ["quote", "rate"])
@pytest.mark.parametrize(
    ("reference_date", "code"),
    [("2026-02-30", "invalid_date"), ("2026-09-09", "reference_after_asof")],
)
def test_invalid_reference_date_blocks_only_its_dependent_valuations(source, reference_date, code):
    raw = _request(
        [
            _row("Domestic/X", target="50"),
            _row("Foreign/Y", currency="USD", target="50"),
        ]
    )
    raw["valuation_rates"] = [_rate()]
    raw["cash_balances"] = [{"currency": "USD", "amount": "1"}]
    raw["contributions"] = [{"currency": "EUR", "amount": "5"}]
    path = ("rows", 1, "quote", "reference_date") if source == "quote" else ("valuation_rates", 0, "reference_date")
    _put(raw, path, reference_date)
    result = _analyze(raw)
    assert result["availability"] == "invalid"
    _issue(result, code, path, "invalid")
    rows = _rows(result)
    foreign = rows["Foreign/Y"]
    assert _value(foreign["quantity"]) == "1"
    _unavailable(foreign["initial_value_reporting"], "input_invalid")
    _money(rows["Domestic/X"]["initial_value_native"], "10")
    _money(rows["Domestic/X"]["initial_value_reporting"], "10")
    _unavailable(result["totals"]["initial_invested_reporting"])
    for row in rows.values():
        _unavailable(row["current_weight_percent"])
        _unavailable(row["deviation_pp"])
    pools = {pool["currency"]: pool for pool in _value(result["cash_pools"])}
    assert pools["USD"]["existing_amount"] == pools["USD"]["combined_amount"] == "1"
    _money(result["totals"]["contributions_reporting"], "5")
    if source == "quote":
        _unavailable(foreign["initial_value_native"], "input_invalid")
        _money(pools["USD"]["combined_reporting"], "0.9")
        _money(result["totals"]["existing_cash_reporting"], "0.9")
        _money(result["totals"]["cash_plus_contributions_reporting"], "5.9")
    else:
        _money(foreign["initial_value_native"], "10", "USD")
        _unavailable(pools["USD"]["combined_reporting"], "input_invalid")
        _unavailable(result["totals"]["existing_cash_reporting"], "input_invalid")
        _unavailable(result["totals"]["cash_plus_contributions_reporting"])


@pytest.mark.parametrize("path", [("rows", 0, "quote", "reference_date"), ("valuation_rates", 0, "reference_date")])
def test_future_reference_is_compared_only_with_the_provided_as_of_date(path):
    raw = _request([_row(currency="USD")])
    raw["valuation_rates"] = [_rate()]
    _put(raw, path, "2099-01-02")
    raw["as_of_date"] = "2099-01-01"
    invalid = _analyze(raw)
    assert invalid["availability"] == "invalid"
    _issue(invalid, "reference_after_asof", path, "invalid")
    raw["as_of_date"] = "2099-01-02"
    assert _analyze(raw)["availability"] == "ready"
    raw["as_of_date"] = None
    undated = _analyze(raw)
    assert undated["availability"] == "ready"
    assert undated["normalized"]["as_of_date"] is None
    assert not any(issue["code"] == "reference_after_asof" for issue in undated["issues"])


def test_missing_dates_are_informational_and_never_replaced_with_today():
    raw = _request([_row(currency="USD")])
    raw["as_of_date"] = None
    _put(raw, ("rows", 0, "quote", "reference_date"), None)
    raw["valuation_rates"] = [_rate(reference_date=None)]
    result = _analyze(raw)
    assert result["availability"] == "ready"
    for path in (("as_of_date",), ("rows", 0, "quote", "reference_date"), ("valuation_rates", 0, "reference_date")):
        _issue(result, "reference_date_unspecified", path, "info")
    assert result["normalized"]["as_of_date"] is None
    assert all(row["quote"]["reference_date"] is None for row in result["normalized"]["rows"])
    assert all(rate["reference_date"] is None for rate in result["normalized"]["valuation_rates"])


def test_availability_precedence_collects_all_primary_field_issues():
    raw = _request([_row(quantity="-1", target=None, price="abc")])
    invalid = _analyze(raw)
    assert invalid["availability"] == "invalid"
    for code, path, kind in (
        ("invalid_decimal_syntax", ("rows", 0, "quote", "raw_price"), "invalid"),
        ("short_inventory_unsupported", ("rows", 0, "initial_quantity"), "unsupported"),
        ("field_required", ("rows", 0, "target_percent"), "missing"),
    ):
        _issue(invalid, code, path, kind)
    assert len(invalid["issues"]) == 3
    _put(raw, ("rows", 0, "quote", "raw_price"), "10")
    assert _analyze(raw)["availability"] == "unsupported"
    _put(raw, ("rows", 0, "initial_quantity"), "1")
    assert _analyze(raw)["availability"] == "needs_input"
    _put(raw, ("rows", 0, "target_percent"), "100")
    assert _analyze(raw)["availability"] == "ready"


def test_semantic_error_rows_keep_input_order_identity_and_revision_relative_indices():
    raw = _request([_row("Z/X", quantity="1", target="30"), _row("A/X", quantity="bad", target="40"), _row("M/X", quantity="-1", target="30")])
    result = _analyze(raw)
    assert [(row["row_index"], row["row_key"], row["instrument_key"]) for row in result["rows"]] == [(0, "Z/X", "Alfa"), (1, "A/X", "Alfa"), (2, "M/X", "Alfa")]
    for index, code in ((1, "invalid_decimal_syntax"), (2, "short_inventory_unsupported")):
        assert _issue(result, code)["related_row_indices"] == [index]
    assert [issue["path"] for issue in result["issues"]] == [["rows", 1, "initial_quantity"], ["rows", 2, "initial_quantity"]]
    raw["rows"].reverse()
    reordered = _analyze(raw)
    assert [row["row_key"] for row in reordered["rows"]] == ["M/X", "A/X", "Z/X"]
    assert _issue(reordered, "short_inventory_unsupported")["related_row_indices"] == [0]


def test_issue_order_is_header_rows_vectors_rates_then_cross_field_groups():
    raw = _request([_row("same", quantity="bad", target="50"), _row("same", price="bad", target="50")])
    raw["as_of_date"] = "bad"
    raw["cash_balances"] = [{"currency": "EUR", "amount": "bad"}]
    raw["contributions"] = [{"currency": "EUR", "amount": "-1"}]
    raw["valuation_rates"] = [_rate("USD", "bad")]
    result = _analyze(raw)
    assert [issue["path"] for issue in result["issues"]] == [
        ["as_of_date"],
        ["rows", 0, "initial_quantity"],
        ["rows", 1, "quote", "raw_price"],
        ["cash_balances", 0, "amount"],
        ["contributions", 0, "amount"],
        ["valuation_rates", 0, "rate_to_report"],
        ["rows", 0, "row_key"],
    ]


def test_nonterminating_ratios_truncate_towards_zero_but_preserve_exact_evidence():
    raw = _request([_row("Alfa/X", quantity="1", price="1", target="50"), _row("Alfa/Y", quantity="2", price="1", target="50")])
    result = _analyze(raw)
    rows = _rows(result)
    _ratio(rows["Alfa/X"]["current_weight_percent"], 100, 3, "percent")
    _ratio(rows["Alfa/Y"]["current_weight_percent"], 200, 3, "percent")
    _ratio(rows["Alfa/X"]["deviation_pp"], -50, 3, "percentage_points")
    _ratio(rows["Alfa/Y"]["deviation_pp"], 50, 3, "percentage_points")
    _ratio(result["totals"]["max_abs_gap_pp"], 50, 3, "percentage_points")
    _ratio(result["totals"]["squared_gap_pp2"], 5000, 9, "percentage_points_squared")
    assert _value(rows["Alfa/X"]["deviation_pp"])["approximation"] == "-16.6666666666666666666666666666"


def test_approximate_zero_does_not_claim_exact_alignment():
    raw = _request(
        [
            _row("Tiny/X", quantity="0.000000000001", price="0.000000000001", currency="USD", basis=100, target="0"),
            _row("Large/X", quantity="999999999999", price="999999999999", target="100"),
        ]
    )
    raw["valuation_rates"] = [_rate("USD", "0.000000000001")]
    result = _analyze(raw)
    assert result["availability"] == "ready"
    tiny_value = Fraction(1, 10**38)
    large_value = Fraction(999999999999**2)
    invested = tiny_value + large_value
    rows = _rows(result)
    for key, numerator in (("Tiny/X", 100 * tiny_value), ("Large/X", -100 * tiny_value)):
        _ratio(rows[key]["deviation_pp"], numerator, invested, "percentage_points")
        gap = _value(rows[key]["deviation_pp"])
        assert gap["approximation"] == "0"
        assert gap["approximation_exact"] is False
        assert Fraction(gap["numerator"]) != 0
    _ratio(result["totals"]["squared_gap_pp2"], 2 * (100 * tiny_value) ** 2, invested**2, "percentage_points_squared")


@pytest.mark.parametrize(("precision", "rounding"), [(2, ROUND_DOWN), (7, ROUND_UP)])
def test_boundary_arithmetic_is_independent_of_hostile_ambient_decimal_context(precision, rounding):
    raw = _request(
        [
            _row("Large/X", quantity="999999999999.999999999999", price="999999999999.999999999999", currency="USD", basis=100, target="33.333333333333", mode="fractional", step="0.000000000001"),
            _row("Small/Y", quantity="0.000000000001", price="0.000000000001", target="66.666666666667", mode="fractional", step="0.000000000001"),
        ]
    )
    raw["valuation_rates"] = [_rate("USD", "999999999999.999999999999")]
    raw["cash_balances"] = [{"currency": "USD", "amount": "999999999999.999999999999"}]
    raw["contributions"] = [{"currency": "USD", "amount": "0.000000000001"}]
    ordinary = _analyze(raw)
    with localcontext() as ambient:
        ambient.prec = precision
        ambient.rounding = rounding
        ambient.Emin = -6
        ambient.Emax = 6
        for signal in ambient.traps:
            ambient.traps[signal] = True
        ambient.clear_flags()
        before = (ambient.prec, ambient.rounding, ambient.Emin, ambient.Emax, dict(ambient.traps), dict(ambient.flags))
        hostile = _analyze(raw)
        assert getcontext() is ambient
        assert (ambient.prec, ambient.rounding, ambient.Emin, ambient.Emax, dict(ambient.traps), dict(ambient.flags)) == before
    assert hostile == ordinary
    assert hostile["availability"] == "ready"
    maximum = Fraction("999999999999.999999999999")
    values = {"Large/X": maximum**3 / 100, "Small/Y": Fraction(1, 10**24)}
    invested = sum(values.values())
    assert Fraction(_value(hostile["totals"]["initial_invested_reporting"])["amount"]) == invested
    gaps = {}
    for key, target in (("Large/X", "33.333333333333"), ("Small/Y", "66.666666666667")):
        gaps[key] = 100 * values[key] - Fraction(target) * invested
        row = _rows(hostile)[key]
        _ratio(row["current_weight_percent"], 100 * values[key], invested, "percent")
        _ratio(row["deviation_pp"], gaps[key], invested, "percentage_points")
    _ratio(hostile["totals"]["max_abs_gap_pp"], max(map(abs, gaps.values())), invested, "percentage_points")
    _ratio(hostile["totals"]["squared_gap_pp2"], sum(gap**2 for gap in gaps.values()), invested**2, "percentage_points_squared")
    expected_cash = maximum**2 + Fraction("0.000000000001") * maximum
    assert Fraction(_value(hostile["totals"]["cash_plus_contributions_reporting"])["amount"]) == expected_cash


def test_raw_and_validated_input_are_unmodified_and_results_do_not_share_mutable_lists():
    raw = _cash_witness()
    before = deepcopy(raw)
    request = PAC_ANALYZE_INPUT_ADAPTER.validate_python(raw)
    model_before = request.model_dump(mode="json")
    first = analyze_initial_state(request)
    first_wire = PAC_ANALYZE_OUTPUT_ADAPTER.dump_json(first)
    # Containers are deliberately mutated only on this test's returned object.
    # Frozen scalar fields do not prove nested-list ownership or absence of caches.
    first.rows.clear()
    first.issues.clear()
    assert first.normalized is not None
    first.normalized.rows.clear()
    first.normalized.cash_balances.clear()
    second = analyze_initial_state(request)
    assert PAC_ANALYZE_OUTPUT_ADAPTER.dump_json(second) == first_wire
    assert request.model_dump(mode="json") == model_before
    assert raw == before
    assert _analyze({"operation": "analyze"})["availability"] == "needs_input"
    assert PAC_ANALYZE_OUTPUT_ADAPTER.dump_json(analyze_initial_state(request)) == first_wire


def test_checkpoint_cancellation_propagates_unchanged_at_early_middle_and_last_checks():
    raw = _request([_row(f"row-{index}", quantity=str(index), target="3.125") for index in range(32)])
    request = PAC_ANALYZE_INPUT_ADAPTER.validate_python(raw)
    calls = 0

    def count():
        nonlocal calls
        calls += 1

    complete = analyze_initial_state(request, checkpoint=count)
    expected = PAC_ANALYZE_OUTPUT_ADAPTER.dump_json(analyze_initial_state(request))
    assert PAC_ANALYZE_OUTPUT_ADAPTER.dump_json(complete) == expected
    assert calls >= 3, "P1 must offer cooperative checkpoints during bounded work"
    for stop_at in sorted({1, calls // 2, calls}):
        seen = 0
        error = ArithmeticError(f"cancel-at-{stop_at}")

        def cancel(stop_at=stop_at, error=error):
            nonlocal seen
            seen += 1
            if seen == stop_at:
                raise error

        with pytest.raises(ArithmeticError) as caught:
            analyze_initial_state(request, checkpoint=cancel)
        assert caught.value is error
        assert seen == stop_at
        assert PAC_ANALYZE_OUTPUT_ADAPTER.dump_json(analyze_initial_state(request)) == expected


@pytest.mark.parametrize("invalid", [False, True])
def test_actual_32_row_unicode_wire_witness_is_bounded_without_clipping_facts(invalid):
    currencies = ("EUR", "USD", "GBP", "CHF")
    rows = []
    for index in range(32):
        key = f"{index:02d}" + '\\"' * 127
        row = _row(
            key,
            quantity="9" * 12 + "." + "9" * 12,
            price="9" * 12 + "." + "9" * 12,
            currency=currencies[index % len(currencies)],
            target="3.125",
            basis=100,
            instrument='\\"' * 64,
        )
        row["name"] = ("🧮" if index % 2 else "\x01") * 128
        row["quote"]["reference_date"] = None
        if invalid:
            row["initial_quantity"] = "🧮" * 64
            row["quote"]["raw_price"] = "x" * 64
            row["target_percent"] = "NaN"
            row["buy_grid"]["quantity_step"] = "1e3"
        rows.append(row)
    raw = _request(rows)
    raw["as_of_date"] = None
    raw["cash_balances"] = [{"currency": currency, "amount": "999999999999.999999999999"} for currency in currencies]
    raw["contributions"] = deepcopy(raw["cash_balances"])
    raw["valuation_rates"] = [_rate(currency, "999999999999.999999999999", None) for currency in currencies if currency != "EUR"]
    result = _analyze(raw)
    assert result["availability"] == ("invalid" if invalid else "ready")
    assert [row["row_key"] for row in result["rows"]] == [row["row_key"] for row in raw["rows"]]
    assert [row["row_index"] for row in result["rows"]] == list(range(32))
    assert len(result["issues"]) <= (384 if invalid else 80)
    if invalid:
        assert len([issue for issue in result["issues"] if issue["code"] == "invalid_decimal_syntax"]) == 4 * 32
    else:
        assert len(result["normalized"]["rows"]) == 32
    emitted = PAC_ANALYZE_OUTPUT_ADAPTER.dump_json(PAC_ANALYZE_OUTPUT_ADAPTER.validate_python(result))
    compact_utf8 = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    assert len(emitted) <= 256 * 1024
    assert len(compact_utf8) <= 256 * 1024
    assert "🧮".encode() in emitted
    assert b"\\u0001" in emitted
    assert json.loads(emitted) == json.loads(compact_utf8)


@pytest.mark.parametrize(
    ("package", "exports", "module_aliases"),
    [
        (
            "backend.app.services",
            {
                "BrokerService": "broker_service",
                "TransactionService": "transaction_service",
                "BalanceValidationError": "transaction_service",
                "LinkedTransactionError": "transaction_service",
            },
            ("broker_service", "transaction_service"),
        ),
        (
            "backend.app.schemas",
            {
                "BRCreateItem": "brokers",
                "TXCreateItem": "transactions",
                "TX_TYPE_METADATA": "transactions",
                "FAAssetCreateItem": "assets",
                "FAPricePoint": "prices",
                "FAProviderInfo": "provider",
                "FARefreshItem": "refresh",
                "FXConversionRequest": "fx",
                "SignalRequest": "signals",
                "SystemInfoResponse": "system",
                "BRIMFileInfo": "brim",
                "BRIMParseRequest": "brim",
                "FAKE_ASSET_ID_BASE": "brim",
                "is_fake_asset_id": "brim",
            },
            (
                "brokers",
                "transactions",
                "assets",
                "prices",
                "provider",
                "refresh",
                "fx",
                "signals",
                "system",
                "brim",
            ),
        ),
        (
            "backend.app.utils.financial",
            {
                "WACInputTX": "wac_utils",
                "WACCalcResult": "wac_utils",
                "compute_wac_from_txlist": "wac_utils",
                "determine_target_currency": "wac_utils",
                "CashFlowInput": "roi_utils",
                "NAVSnapshot": "roi_utils",
                "ROIResult": "roi_utils",
                "SimpleROIPoint": "roi_utils",
                "TWRRPoint": "roi_utils",
                "MWRRPoint": "roi_utils",
                "calculate_simple_roi": "roi_utils",
                "calculate_simple_roi_series": "roi_utils",
                "calculate_twrr": "roi_utils",
                "calculate_twrr_series": "roi_utils",
                "calculate_mwrr": "roi_utils",
                "calculate_mwrr_series": "roi_utils",
            },
            ("roi_utils", "wac_utils"),
        ),
    ],
)
def test_legacy_lazy_reexports_preserve_canonical_identity_in_a_fresh_process(package, exports, module_aliases):
    """Deferred service-slot test: never part of the lightweight schema selector.

    Resolves real legacy Broker/BRIM/ROI/WAC imports, but invokes no service,
    database operation, provider, HTTP request or application lifecycle.
    """
    script = dedent("""
        import importlib
        import json
        import sys

        package_name, expected, aliases = sys.argv[1:]
        expected = json.loads(expected)
        aliases = json.loads(aliases)
        root = importlib.import_module(package_name)
        declared_before = list(root.__all__)
        directory_before = dir(root)
        assert set(expected) <= set(declared_before)
        assert set(declared_before) | set(aliases) <= set(directory_before)
        checked = []
        for name, module_name in expected.items():
            # Ask the package first so the real lazy re-export path is exercised.
            exported = getattr(root, name)
            canonical_module = importlib.import_module(package_name + "." + module_name)
            assert exported is getattr(canonical_module, name), name
            assert getattr(root, name) is exported, name
            checked.append(name)
        for module_name in aliases:
            exported_module = getattr(root, module_name)
            assert exported_module is importlib.import_module(package_name + "." + module_name)
        # Every declared star-import name must still resolve, not only examples.
        for name in root.__all__:
            getattr(root, name)
        assert root.__all__ == declared_before
        assert set(directory_before) <= set(dir(root))
        try:
            getattr(root, "unknown_pac_legacy_export")
        except AttributeError:
            pass
        else:
            raise AssertionError("Unknown legacy export must raise AttributeError")
        print("PAC_LEGACY_IMPORT_RESULT=" + json.dumps({
            "package": package_name, "checked": sorted(checked),
            "module_aliases": sorted(aliases),
        }))
        """)
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            script,
            package,
            json.dumps(exports),
            json.dumps(module_aliases),
        ],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    marker = "PAC_LEGACY_IMPORT_RESULT="
    observations = [json.loads(line.removeprefix(marker)) for line in completed.stdout.splitlines() if line.startswith(marker)]
    assert len(observations) == 1, completed.stdout
    (observation,) = observations
    assert observation == {
        "package": package,
        "checked": sorted(exports),
        "module_aliases": sorted(module_aliases),
    }
