"""Pure P1-r3 codec conformance; no transport, persistence or solver fixtures.

Financial output witnesses come from the public analyzer. Mutated output documents
exercise wire representability only: they do not certify the mutated economics.
The coordinator owns catalogue registration and authorizes validation separately.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path as FilePath
from textwrap import dedent
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from backend.app.schemas.pac_allocator import (
    PAC_ANALYZE_INPUT_ADAPTER,
    PAC_ANALYZE_OUTPUT_ADAPTER,
    PacAnalyzeInput,
    PacAnalyzeOutput,
)
from backend.app.services.pac_allocator import analyze_initial_state

Path = tuple[str | int, ...]
STATES = ("ready", "needs_input", "invalid", "unsupported")
ROOT_LITERALS = {
    "operation": "analyze",
    "result_kind": "initial_state_analysis",
    "numeric_policy_id": "pac-initial-state-v1",
    "trade_feasibility": "not_evaluated",
    "optimization": "not_run",
}
REASONS = {
    "input_missing",
    "input_invalid",
    "outside_p1_domain",
    "dependency_unavailable",
    "zero_initial_invested_value",
}
ISSUE_CODES = {
    "missing": {
        "rows_required", "field_required", "incomplete_decimal", "quote_required",
        "grid_required", "cash_vector_required", "valuation_rate_required",
    },
    "invalid": {
        "invalid_decimal_syntax", "invalid_currency", "invalid_date",
        "reference_after_asof", "nonpositive_price", "nonpositive_fx_rate",
        "invalid_quote_basis", "target_percent_out_of_range", "target_total_not_100",
        "nonpositive_quantity_step", "noninteger_whole_step", "negative_contribution",
        "duplicate_row_key", "duplicate_currency", "identity_rate_mismatch",
    },
    "unsupported": {
        "numeric_domain_exceeded", "currency_domain_exceeded",
        "quote_basis_unsupported", "short_inventory_unsupported",
        "initial_debt_unsupported",
    },
    "info": {
        "inventory_off_buy_grid", "reference_date_unspecified",
        "unused_valuation_reference", "identity_rate_redundant",
    },
}
PATH_FIELDS = {
    "report_currency", "as_of_date", "rows", "row_key", "instrument_key", "name",
    "initial_quantity", "quote", "raw_price", "currency", "quote_base_quantity",
    "reference_date", "target_percent", "buy_grid", "mode", "quantity_step",
    "cash_balances", "contributions", "valuation_rates", "amount", "rate_to_report",
}
PARAM_FIELDS = {"currency", "vector", "limit", "allowed_quote_bases", "unit"}
DECIMAL_PATHS = (
    ("rows", 0, "initial_quantity"),
    ("rows", 0, "target_percent"),
    ("rows", 0, "quote", "raw_price"),
    ("rows", 0, "buy_grid", "quantity_step"),
    ("cash_balances", 0, "amount"),
    ("contributions", 0, "amount"),
    ("valuation_rates", 0, "rate_to_report"),
)
CURRENCY_PATHS = (
    ("report_currency",),
    ("rows", 0, "quote", "currency"),
    ("cash_balances", 0, "currency"),
    ("contributions", 0, "currency"),
    ("valuation_rates", 0, "currency"),
)
DATE_PATHS = (
    ("as_of_date",),
    ("rows", 0, "quote", "reference_date"),
    ("valuation_rates", 0, "reference_date"),
)
NAME_PATH = ("rows", 0, "name")
TEXT_LIMITS = (
    *((path, 64) for path in DECIMAL_PATHS),
    *((path, 8) for path in CURRENCY_PATHS),
    *((path, 10) for path in DATE_PATHS),
    (NAME_PATH, 128),
)

# Every path indexes only a local, explicitly constructed witness. There is no
# shared collection, positional DB selection or service-test helper dependency.
NUMERIC_FIELDS = (
    (("rows", 0, "quantity", "value"), 26),
    (("rows", 0, "target_percent", "value"), 26),
    (("rows", 0, "initial_value_native", "value", "amount"), 52),
    (("rows", 0, "initial_value_reporting", "value", "amount"), 80),
    *(
        (("rows", 0, fact, "value", field), width)
        for fact in ("current_weight_percent", "deviation_pp")
        for field, width in (("numerator", 96), ("denominator", 80), ("approximation", 36))
    ),
    *(
        (("cash_pools", "value", 0, field), width)
        for field, width in (
            ("existing_amount", 26), ("contribution_amount", 26), ("combined_amount", 28)
        )
    ),
    *(
        (("cash_pools", "value", 0, field, "value", "amount"), 80)
        for field in ("existing_reporting", "contribution_reporting", "combined_reporting")
    ),
    *(
        (("totals", field, "value", "amount"), 80)
        for field in (
            "initial_invested_reporting", "existing_cash_reporting",
            "contributions_reporting", "cash_plus_contributions_reporting",
        )
    ),
    (("totals", "target_total_percent", "value"), 26),
    *(
        (("totals", fact, "value", field), width)
        for fact, widths in (
            ("max_abs_gap_pp", (96, 80, 36)),
            ("squared_gap_pp2", (192, 160, 36)),
        )
        for field, width in zip(("numerator", "denominator", "approximation"), widths)
    ),
    (("normalized", "rows", 0, "initial_quantity"), 26),
    (("normalized", "rows", 0, "quote", "raw_price"), 26),
    (("normalized", "rows", 0, "target_percent"), 26),
    (("normalized", "rows", 0, "buy_grid", "quantity_step"), 26),
    (("normalized", "cash_balances", 0, "amount"), 26),
    (("normalized", "contributions", 0, "amount"), 26),
    (("normalized", "valuation_rates", 0, "rate_to_report"), 26),
)


def _encode(value: Any, *, ensure_ascii: bool = False) -> bytes:
    return json.dumps(
        value, ensure_ascii=ensure_ascii, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")


def _at(value: Any, path: Path) -> Any:
    for token in path:
        value = value[token]
    return value


def _set(value: Any, path: Path, replacement: Any) -> None:
    _at(value, path[:-1])[path[-1]] = replacement


def _objects(value: Any, path: Path = ()):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from _objects(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _objects(child, (*path, index))


def _request() -> dict[str, Any]:
    return {
        "operation": "analyze",
        "report_currency": "EUR",
        "as_of_date": "2026-09-08",
        "rows": [{
            "row_key": "schema-owned::alpha",
            "instrument_key": "schema-owned-alpha",
            "name": "Codec witness",
            "initial_quantity": "10.125",
            "quote": {
                "raw_price": "10", "currency": "EUR",
                "quote_base_quantity": 1, "reference_date": None,
            },
            "target_percent": "100",
            "buy_grid": {"mode": "whole", "quantity_step": "1"},
        }],
        "cash_balances": [{"currency": "EUR", "amount": "0.005"}],
        "contributions": [{"currency": "EUR", "amount": "5"}],
        "valuation_rates": [{
            "currency": "USD", "rate_to_report": "0.9", "reference_date": "2026-09-08",
        }],
    }


def _roundtrip(adapter: TypeAdapter, payload: Any) -> Any:
    model = adapter.validate_json(_encode(payload))
    emitted = adapter.dump_json(model)
    assert adapter.validate_json(emitted) == model
    assert json.loads(emitted) == adapter.dump_python(model, mode="json")
    return model


def _reject(adapter: TypeAdapter, payload: Any, *, ensure_ascii: bool = False) -> None:
    with pytest.raises(ValidationError):
        adapter.validate_json(_encode(payload, ensure_ascii=ensure_ascii))


def _analyzed(payload: dict[str, Any], expected: str) -> dict[str, Any]:
    request: PacAnalyzeInput = _roundtrip(PAC_ANALYZE_INPUT_ADAPTER, payload)
    result: PacAnalyzeOutput = analyze_initial_state(request)
    validated = PAC_ANALYZE_OUTPUT_ADAPTER.validate_python(result)
    emitted = PAC_ANALYZE_OUTPUT_ADAPTER.dump_json(validated)
    assert PAC_ANALYZE_OUTPUT_ADAPTER.validate_json(emitted) == validated
    wire = json.loads(emitted)
    assert wire["availability"] == expected
    return wire


@pytest.fixture(scope="module")
def output_witnesses() -> dict[str, dict[str, Any]]:
    witnesses = {}
    for state, quantity in (
        ("ready", "10.125"), ("needs_input", None),
        ("invalid", "12abc"), ("unsupported", "-1"),
    ):
        payload = _request()
        _set(payload, ("rows", 0, "initial_quantity"), quantity)
        witnesses[state] = _analyzed(payload, state)
    return witnesses


def _issue_document(witnesses, kind: str, code: str) -> dict[str, Any]:
    """Change only codec data on an actual non-ready financial result."""
    wire = deepcopy(witnesses["invalid"])
    assert wire["issues"], "The invalid witness must supply a real issue"
    issue = deepcopy(next(iter(wire["issues"])))
    issue.update(
        kind=kind, code=code, path=["rows", 0, "initial_quantity"],
        related_row_indices=[0], params={},
    )
    wire["issues"] = [issue]
    return wire


def _resolve(root: dict, node: dict) -> dict:
    while "$ref" in node:
        reference = node["$ref"]
        assert reference.startswith("#/"), reference
        node = root
        for part in reference[2:].split("/"):
            node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def _branch(root: dict, node: dict, tag: str) -> dict:
    node = _resolve(root, node)
    mapping = node["discriminator"]["mapping"]
    assert tag in mapping
    assert mapping[tag] in {item.get("$ref") for item in node["oneOf"]}
    return _resolve(root, {"$ref": mapping[tag]})


def _shape(root: dict, node: dict, state: str = "ready") -> dict:
    """Inspect the actual export, never substitute a handwritten validator."""
    node = _resolve(root, node)
    if "anyOf" in node:
        nonnull = [item for item in node["anyOf"] if item.get("type") != "null"]
        assert len(nonnull) == 1
        return _shape(root, nonnull[0], state)
    if "discriminator" in node:
        mapping = node["discriminator"]["mapping"]
        tag = state if state in mapping else ("available" if "available" in mapping else "info")
        return _shape(root, _branch(root, node, tag), state)
    return node


def _schema_at(root: dict, path: Path, state: str = "ready") -> dict:
    node = root
    for token in path:
        node = _shape(root, node, state)
        node = node["items"] if isinstance(token, int) else node["properties"][token]
    return _shape(root, node, state)


def test_public_adapters_are_real_codecs():
    assert isinstance(PAC_ANALYZE_INPUT_ADAPTER, TypeAdapter)
    assert isinstance(PAC_ANALYZE_OUTPUT_ADAPTER, TypeAdapter)
    request = _roundtrip(PAC_ANALYZE_INPUT_ADAPTER, {"operation": "analyze"})
    assert isinstance(request, PacAnalyzeInput)
    assert TypeAdapter(PacAnalyzeInput).validate_json(b'{"operation":"analyze"}') == request
    for mode in ("validation", "serialization"):
        assert TypeAdapter(PacAnalyzeOutput).json_schema(mode=mode) == (
            PAC_ANALYZE_OUTPUT_ADAPTER.json_schema(mode=mode)
        )


@pytest.mark.parametrize("root", [None, [], ["analyze"], "analyze", True, False, 0, 1.5])
def test_wrong_input_root_is_structural(root):
    _reject(PAC_ANALYZE_INPUT_ADAPTER, root)


@pytest.mark.parametrize("payload", [
    {}, {"operation": None}, {"operation": "solve"}, {"operation": "ANALYZE"},
    {"operation": True}, {"operation": 1}, {"operation": {}},
])
def test_operation_is_required_and_analyze_only(payload):
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload)


def test_all_draft_cells_default_to_null_and_only_collections_default_empty():
    model = _roundtrip(PAC_ANALYZE_INPUT_ADAPTER, {"operation": "analyze"})
    assert model.model_dump(mode="json") == {
        "operation": "analyze", "report_currency": None, "as_of_date": None,
        "rows": [], "cash_balances": None, "contributions": None, "valuation_rates": [],
    }
    draft = {
        "operation": "analyze",
        "rows": [{"row_key": "owned", "instrument_key": "instrument"}],
        "cash_balances": [{}], "contributions": [{}], "valuation_rates": [{}],
    }
    expanded = _roundtrip(PAC_ANALYZE_INPUT_ADAPTER, draft).model_dump(mode="json")
    assert expanded["rows"] == [{
        "row_key": "owned", "instrument_key": "instrument", "name": None,
        "initial_quantity": None, "quote": None, "target_percent": None, "buy_grid": None,
    }]
    assert expanded["cash_balances"] == expanded["contributions"] == [
        {"currency": None, "amount": None}
    ]
    assert expanded["valuation_rates"] == [
        {"currency": None, "rate_to_report": None, "reference_date": None}
    ]
    draft["rows"][0].update(quote={}, buy_grid={})
    expanded = _roundtrip(PAC_ANALYZE_INPUT_ADAPTER, draft).model_dump(mode="json")
    assert expanded["rows"][0]["quote"] == {
        "raw_price": None, "currency": None,
        "quote_base_quantity": None, "reference_date": None,
    }
    assert expanded["rows"][0]["buy_grid"] == {"mode": None, "quantity_step": None}


@pytest.mark.parametrize("key", ["row_key", "instrument_key"])
@pytest.mark.parametrize("bad", [None, "", True, 17, [], {}])
def test_row_identity_is_required_nonnull_text(key, bad):
    payload = _request()
    del payload["rows"][0][key]
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload)
    payload["rows"][0][key] = bad
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload)


def test_unknown_fields_rejected_at_every_input_object():
    payload = _request()
    objects = list(_objects(payload))
    assert {path for path, _ in objects} == {
        (), ("rows", 0), ("rows", 0, "quote"), ("rows", 0, "buy_grid"),
        ("cash_balances", 0), ("contributions", 0), ("valuation_rates", 0),
    }
    for path, _ in objects:
        mutated = deepcopy(payload)
        _at(mutated, path)["unknown_p1_field"] = "not accepted"
        _reject(PAC_ANALYZE_INPUT_ADAPTER, mutated)


@pytest.mark.parametrize("field", [
    "candidate_trades", "fees", "reserves", "broker_id", "execution_fx",
    "operational_threshold", "initial_value", "draft_revision", "account_id",
])
def test_full_allocator_and_platform_fields_are_not_analyze_parameters(field):
    payload = _request()
    payload[field] = None
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload)


@pytest.mark.parametrize("path", [
    ("rows",), ("cash_balances",), ("contributions",), ("valuation_rates",),
    ("rows", 0), ("rows", 0, "quote"), ("rows", 0, "buy_grid"),
    ("cash_balances", 0), ("contributions", 0), ("valuation_rates", 0),
])
@pytest.mark.parametrize("bad", [True, 1, "{}", "[]"])
def test_nested_container_types_are_not_coerced(path, bad):
    payload = _request()
    _set(payload, path, bad)
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload)


@pytest.mark.parametrize("field", ["rows", "valuation_rates"])
def test_default_empty_collections_do_not_accept_null(field):
    _reject(PAC_ANALYZE_INPUT_ADAPTER, {"operation": "analyze", field: None})


@pytest.mark.parametrize("path", [
    ("rows",), ("cash_balances",), ("contributions",), ("valuation_rates",),
])
def test_input_arrays_do_not_accept_objects(path):
    payload = _request()
    _set(payload, path, {})
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload)


@pytest.mark.parametrize("path", [
    ("rows", 0), ("rows", 0, "quote"), ("rows", 0, "buy_grid"),
    ("cash_balances", 0), ("contributions", 0), ("valuation_rates", 0),
])
def test_input_objects_do_not_accept_arrays(path):
    payload = _request()
    _set(payload, path, [])
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload)


@pytest.mark.parametrize("path,limit", TEXT_LIMITS)
def test_explicit_null_draft_text_is_preserved_not_replaced_by_zero(path, limit):
    payload = _request()
    _set(payload, path, None)
    result = _roundtrip(PAC_ANALYZE_INPUT_ADAPTER, payload)
    assert _at(result.model_dump(mode="json"), path) is None


@pytest.mark.parametrize("path", (*CURRENCY_PATHS, *DATE_PATHS, NAME_PATH))
@pytest.mark.parametrize("bad", [True, False, 0, 1.5, [], {}])
def test_nonfinancial_draft_text_is_also_strict(path, bad):
    payload = _request()
    _set(payload, path, bad)
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload)


@pytest.mark.parametrize("field", ["cash_balances", "contributions"])
def test_null_cash_vectors_remain_distinct_from_explicit_closed_empty_vectors(field):
    payload = _request()
    payload[field] = None
    absent = _roundtrip(PAC_ANALYZE_INPUT_ADAPTER, payload)
    assert getattr(absent, field) is None
    payload[field] = []
    closed = _roundtrip(PAC_ANALYZE_INPUT_ADAPTER, payload)
    assert getattr(closed, field) == []
    assert PAC_ANALYZE_INPUT_ADAPTER.dump_json(absent) != (
        PAC_ANALYZE_INPUT_ADAPTER.dump_json(closed)
    )


@pytest.mark.parametrize("path", DECIMAL_PATHS)
@pytest.mark.parametrize("bad", [True, False, 0, 1, -2, 1.25, [], {}])
def test_financial_cells_require_strings_not_json_numbers_or_booleans(path, bad):
    payload = _request()
    _set(payload, path, bad)
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload)


@pytest.mark.parametrize("path", DECIMAL_PATHS)
@pytest.mark.parametrize("text", [
    "", "-", ".", "1e3", "12abc", "NaN", "Infinity", "-Infinity", "1,234.5",
    "1.2.3", "１２", "  +001.2300  ", "\x00", "\U0001f680",
])
def test_malformed_decimal_text_is_structural_input_not_codec_failure(path, text):
    payload = _request()
    _set(payload, path, text)
    result = _roundtrip(PAC_ANALYZE_INPUT_ADAPTER, payload)
    assert _at(result.model_dump(mode="json"), path) == text


@pytest.mark.parametrize("bad", [True, False, 1.0, 100.0, "1", "100", [], {}])
def test_quote_basis_is_a_strict_json_integer(bad):
    payload = _request()
    _set(payload, ("rows", 0, "quote", "quote_base_quantity"), bad)
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload)


@pytest.mark.parametrize("basis", [None, -1, 0, 1, 2, 100, 1000])
def test_quote_basis_domain_is_not_prematurely_enforced_on_drafts(basis):
    payload = _request()
    _set(payload, ("rows", 0, "quote", "quote_base_quantity"), basis)
    result = _roundtrip(PAC_ANALYZE_INPUT_ADAPTER, payload)
    assert result.rows[0].quote.quote_base_quantity == basis


@pytest.mark.parametrize("mode", [None, "whole", "fractional"])
def test_grid_mode_admitted_literals(mode):
    payload = _request()
    _set(payload, ("rows", 0, "buy_grid", "mode"), mode)
    _roundtrip(PAC_ANALYZE_INPUT_ADAPTER, payload)


@pytest.mark.parametrize("mode", ["continuous", "WHOLE", "", True, 1])
def test_grid_mode_rejects_unknown_literals(mode):
    payload = _request()
    _set(payload, ("rows", 0, "buy_grid", "mode"), mode)
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload)


@pytest.mark.parametrize("field,limit", [
    ("rows", 32), ("cash_balances", 4), ("contributions", 4), ("valuation_rates", 4),
])
def test_input_collection_boundaries(field, limit):
    payload = _request()
    template = deepcopy(next(iter(payload[field])))
    payload[field] = [deepcopy(template) for _ in range(limit)]
    assert len(getattr(_roundtrip(PAC_ANALYZE_INPUT_ADAPTER, payload), field)) == limit
    payload[field].append(deepcopy(template))
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload)


@pytest.mark.parametrize("path,limit", TEXT_LIMITS)
@pytest.mark.parametrize("character", ["x", "\U0001f680", "\x00"])
def test_input_lengths_count_unicode_codepoints_not_bytes_or_utf16(path, limit, character):
    payload = _request()
    text = character * limit
    _set(payload, path, text)
    result = _roundtrip(PAC_ANALYZE_INPUT_ADAPTER, payload)
    assert _at(result.model_dump(mode="json"), path) == text
    _set(payload, path, text + character)
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload)


@pytest.mark.parametrize("key,limit", [("row_key", 256), ("instrument_key", 128)])
def test_key_maximum_allows_quote_and_backslash_escaping(key, limit):
    payload = _request()
    text = ('"\\' * limit)[:limit]
    payload["rows"][0][key] = text
    result = _roundtrip(PAC_ANALYZE_INPUT_ADAPTER, payload)
    assert getattr(result.rows[0], key) == text
    payload["rows"][0][key] = text + "!"
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload)
    for character in map(chr, range(0x21, 0x7F)):
        payload["rows"][0][key] = character
        _roundtrip(PAC_ANALYZE_INPUT_ADAPTER, payload)


@pytest.mark.parametrize("key", ["row_key", "instrument_key"])
@pytest.mark.parametrize("bad", [
    " ", "a b", "\x00", "\n", "\t", "\x7f", "é", "\U0001f680",
])
def test_keys_are_nonempty_printable_ascii_without_whitespace(key, bad):
    payload = _request()
    payload["rows"][0][key] = bad
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload)


@pytest.mark.parametrize("path,limit", TEXT_LIMITS)
@pytest.mark.parametrize("bad", ["\ud800", "\udfff", "prefix\ud800suffix", "\ud800\ud800"])
def test_raw_text_rejects_lone_surrogates_in_python_and_actual_json(path, limit, bad):
    payload = _request()
    _set(payload, path, bad)
    with pytest.raises(ValidationError):
        PAC_ANALYZE_INPUT_ADAPTER.validate_python(payload)
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload, ensure_ascii=True)


@pytest.mark.parametrize("path,limit", TEXT_LIMITS)
def test_valid_json_surrogate_pairs_decode_to_one_scalar_at_boundaries(path, limit):
    payload = _request()
    text = "\U0001f680" * limit
    _set(payload, path, text)
    escaped = _encode(payload, ensure_ascii=True)
    assert b"\\ud83d\\ude80" in escaped
    parsed = PAC_ANALYZE_INPUT_ADAPTER.validate_json(escaped)
    assert _at(parsed.model_dump(mode="json"), path) == text
    emitted = PAC_ANALYZE_INPUT_ADAPTER.dump_json(parsed)
    assert text.encode("utf-8") in emitted
    assert PAC_ANALYZE_INPUT_ADAPTER.validate_json(emitted) == parsed
    _set(payload, path, text + "\U0001f680")
    _reject(PAC_ANALYZE_INPUT_ADAPTER, payload, ensure_ascii=True)


@pytest.mark.parametrize("adapter", [PAC_ANALYZE_INPUT_ADAPTER, PAC_ANALYZE_OUTPUT_ADAPTER])
def test_surrogate_object_keys_are_not_accepted(adapter, output_witnesses):
    payload = _request() if adapter is PAC_ANALYZE_INPUT_ADAPTER else deepcopy(output_witnesses["ready"])
    payload["\ud800"] = "bad key"
    _reject(adapter, payload, ensure_ascii=True)


@pytest.mark.parametrize("state", STATES)
def test_actual_output_has_complete_root_literals_and_conditional_normalized(state, output_witnesses):
    wire = deepcopy(output_witnesses[state])
    assert set(wire) == {
        *ROOT_LITERALS, "availability", "normalized", "rows", "cash_pools", "totals", "issues",
    }
    assert {key: wire[key] for key in ROOT_LITERALS} == ROOT_LITERALS
    assert (wire["normalized"] is not None) == (state == "ready")
    _roundtrip(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    wire["normalized"] = None if state == "ready" else deepcopy(output_witnesses["ready"]["normalized"])
    _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)


@pytest.mark.parametrize("root", [None, [], "ready", True, 1, {}])
def test_output_rejects_wrong_root_and_empty_success(root):
    _reject(PAC_ANALYZE_OUTPUT_ADAPTER, root)


@pytest.mark.parametrize("state", STATES)
def test_all_output_objects_are_closed_and_all_nonparam_fields_required(state, output_witnesses):
    wire = output_witnesses[state]
    objects = list(_objects(wire))
    assert objects
    for path, obj in objects:
        extra = deepcopy(wire)
        _at(extra, path)["unknown_p1_field"] = None
        _reject(PAC_ANALYZE_OUTPUT_ADAPTER, extra)
        if path and path[-1] == "params":
            continue  # Only the bounded issue parameter fields may be omitted.
        for field in obj:
            missing = deepcopy(wire)
            del _at(missing, path)[field]
            _reject(PAC_ANALYZE_OUTPUT_ADAPTER, missing)


@pytest.mark.parametrize("field", [*ROOT_LITERALS, "availability"])
@pytest.mark.parametrize("bad", [None, "", "solve", True, 1])
def test_output_discriminators_and_policy_literals_are_not_defaulted(field, bad, output_witnesses):
    wire = deepcopy(output_witnesses["ready"])
    wire[field] = bad
    _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)


@pytest.mark.parametrize("state", STATES)
def test_issue_array_caps_and_ready_info_only(state, output_witnesses):
    wire = deepcopy(output_witnesses[state])
    assert wire["issues"]
    limit = 80 if state == "ready" else 384
    template = deepcopy(next(iter(wire["issues"])))
    if state == "ready":
        assert all(issue["kind"] == "info" for issue in wire["issues"])
    wire["issues"] = [deepcopy(template) for _ in range(limit)]
    _roundtrip(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    wire["issues"].append(deepcopy(template))
    _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    if state == "ready":
        for kind in ("missing", "invalid", "unsupported"):
            code = min(ISSUE_CODES[kind])
            wire["issues"] = _issue_document(output_witnesses, kind, code)["issues"]
            _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)


@pytest.mark.parametrize("kind,code", [
    (kind, code) for kind, codes in ISSUE_CODES.items() for code in sorted(codes)
])
def test_issue_code_vocabulary_is_kind_specific(kind, code, output_witnesses):
    wire = _issue_document(output_witnesses, kind, code)
    _roundtrip(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    for other in ISSUE_CODES.keys() - {kind}:
        wire["issues"][0]["kind"] = other
        _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    wire["issues"][0]["kind"] = kind
    for bad in ("invalid_unknown", "raw_exception", "", None, 1):
        wire["issues"][0]["code"] = bad
        _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)


@pytest.mark.parametrize("bad", ["warning", "", None, True])
def test_unknown_issue_kind_is_rejected(bad, output_witnesses):
    wire = _issue_document(output_witnesses, "invalid", "invalid_decimal_syntax")
    wire["issues"][0]["kind"] = bad
    _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)


def test_fact_discriminated_shapes_and_closed_reason_vocabulary(output_witnesses):
    seen = set()
    for original in output_witnesses.values():
        facts = [
            (path, obj) for path, obj in _objects(original)
            if obj.get("availability") in {"available", "unavailable"}
        ]
        for path, fact in facts:
            seen.add(fact["availability"])
            assert set(fact) == {"availability", "value", "reason_codes"}
            available = fact["availability"] == "available"
            assert (fact["value"] is not None) == available
            if available:
                assert fact["reason_codes"] == []
            else:
                assert len(fact["reason_codes"]) == 1
                assert fact["reason_codes"][0] in REASONS
            invalid_reasons = (
                [["input_missing"], None, "input_missing"] if available
                else [[], ["input_missing", "input_invalid"], ["invented"], None, "input_missing"]
            )
            for reasons in invalid_reasons:
                wire = deepcopy(original)
                _at(wire, path)["reason_codes"] = reasons
                _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
            wire = deepcopy(original)
            _at(wire, path)["value"] = None if available else "0"
            _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
            for tag in ("", "ready", None, True):
                wire = deepcopy(original)
                _at(wire, path)["availability"] = tag
                _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
            if not available:
                for reason in REASONS:
                    wire = deepcopy(original)
                    _at(wire, path)["reason_codes"] = [reason]
                    _roundtrip(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    assert seen == {"available", "unavailable"}


@pytest.mark.parametrize("indices", [[], [0], [31], [0, 31], list(range(32))])
def test_related_row_indices_codec_boundaries(indices, output_witnesses):
    wire = _issue_document(output_witnesses, "invalid", "duplicate_row_key")
    wire["issues"][0]["related_row_indices"] = indices
    _roundtrip(PAC_ANALYZE_OUTPUT_ADAPTER, wire)


@pytest.mark.parametrize("indices", [
    [True], [False], [0.0], ["0"], [-1], [32], [0, 0],
    list(range(32)) + [0], ["schema-owned::alpha"], None,
])
def test_related_row_indices_are_strict_unique_indices_not_echoed_keys(indices, output_witnesses):
    wire = _issue_document(output_witnesses, "invalid", "duplicate_row_key")
    wire["issues"][0]["related_row_indices"] = indices
    _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)


def test_production_duplicate_projection_sorts_indices_in_original_row_order():
    payload = _request()
    template = payload["rows"][0]
    payload["rows"] = [
        {**deepcopy(template), "row_key": f"schema-owned::{index}", "target_percent": "3.125"}
        for index in range(32)
    ]
    affected = [0, 15, 31]
    for index in affected:
        payload["rows"][index]["row_key"] = "schema-owned::duplicate"
    wire = _analyzed(payload, "invalid")
    assert [
        (row["row_index"], row["row_key"], row["instrument_key"]) for row in wire["rows"]
    ] == [
        (index, row["row_key"], row["instrument_key"])
        for index, row in enumerate(payload["rows"])
    ]
    duplicates = [issue for issue in wire["issues"] if issue["code"] == "duplicate_row_key"]
    assert len(duplicates) == 1  # Exactly one duplicate group was constructed here.
    (duplicate,) = duplicates
    assert duplicate["related_row_indices"] == affected
    for issue in wire["issues"]:
        assert issue["related_row_indices"] == sorted(set(issue["related_row_indices"]))
        assert "related_row_keys" not in issue


@pytest.mark.parametrize("path", [
    [], ["rows", 31, "quote", "quote_base_quantity"], [0, 31],
    *[[field] for field in sorted(PATH_FIELDS)],
])
def test_issue_path_admits_only_bounded_input_tokens(path, output_witnesses):
    wire = _issue_document(output_witnesses, "invalid", "invalid_decimal_syntax")
    wire["issues"][0]["path"] = path
    _roundtrip(PAC_ANALYZE_OUTPUT_ADAPTER, wire)


@pytest.mark.parametrize("path", [
    ["rows"] * 5, [True], [False], [0.0], [-1], [32], ["0"], [None],
    ["/api/v1"], ["schema-owned::alpha"], ["exception"], ["x" * 20], None, "rows",
])
def test_issue_path_rejects_unbounded_tokens_and_non_strict_indices(path, output_witnesses):
    wire = _issue_document(output_witnesses, "invalid", "invalid_decimal_syntax")
    wire["issues"][0]["path"] = path
    _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)


@pytest.mark.parametrize("params", [
    {}, dict.fromkeys(sorted(PARAM_FIELDS)),
    {
        "currency": "EUR", "vector": "valuation_rates", "limit": 512,
        "allowed_quote_bases": [1, 100], "unit": "native_amount",
    },
    {"limit": 0}, {"allowed_quote_bases": []},
    *[{"vector": vector} for vector in ("cash_balances", "contributions", "valuation_rates")],
    *[{"unit": unit} for unit in ("quantity", "quote", "rate", "percent", "native_amount")],
])
def test_issue_params_admitted_shapes(params, output_witnesses):
    wire = _issue_document(output_witnesses, "invalid", "invalid_decimal_syntax")
    wire["issues"][0]["params"] = params
    _roundtrip(PAC_ANALYZE_OUTPUT_ADAPTER, wire)


@pytest.mark.parametrize("params", [
    {"currency": "eur"}, {"currency": "ZZZ"}, {"currency": "EURO"}, {"currency": True},
    {"vector": "rows"}, {"unit": "money"}, {"limit": -1}, {"limit": 513},
    {"limit": True}, {"limit": 1.0}, {"limit": "32"},
    {"allowed_quote_bases": [1, 100, 1]}, {"allowed_quote_bases": [2]},
    {"allowed_quote_bases": [True]}, {"allowed_quote_bases": [1.0]},
    {"allowed_quote_bases": ["100"]}, {"raw_input": "12abc"},
    {"exception": "private traceback"}, {"row_key": "opaque"}, None, [],
])
def test_issue_params_are_closed_and_field_bounded(params, output_witnesses):
    wire = _issue_document(output_witnesses, "invalid", "invalid_decimal_syntax")
    wire["issues"][0]["params"] = params
    _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)


@pytest.mark.parametrize("path,width", NUMERIC_FIELDS)
def test_output_numeric_fields_have_exact_wire_widths(path, width, output_witnesses):
    wire = deepcopy(output_witnesses["ready"])
    assert isinstance(_at(wire, path), str), path
    boundary = "1" + "0" * (width - 1)
    _set(wire, path, boundary)
    parsed = _roundtrip(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    assert _at(PAC_ANALYZE_OUTPUT_ADAPTER.dump_python(parsed, mode="json"), path) == boundary
    _set(wire, path, boundary + "0")
    _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    for bad in (True, False, 1, 1.0, None, [], {}, "", "1e3", "NaN", "01", "１２", "1,2", " 1 "):
        _set(wire, path, bad)
        _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)


@pytest.mark.parametrize("path,unit", [
    (("rows", 0, "current_weight_percent", "value"), "percent"),
    (("rows", 0, "deviation_pp", "value"), "percentage_points"),
    (("totals", "max_abs_gap_pp", "value"), "percentage_points"),
    (("totals", "squared_gap_pp2", "value"), "percentage_points_squared"),
])
def test_ratios_have_strict_metadata_positive_denominators_and_required_units(path, unit, output_witnesses):
    wire = deepcopy(output_witnesses["ready"])
    ratio = _at(wire, path)
    assert set(ratio) == {
        "numerator", "denominator", "unit", "approximation",
        "approximation_decimal_places", "approximation_exact",
    }
    assert ratio["unit"] == unit
    assert ratio["approximation_decimal_places"] == 28
    assert type(ratio["approximation_exact"]) is bool
    for mode in ("validation", "serialization"):
        schema = PAC_ANALYZE_OUTPUT_ADAPTER.json_schema(mode=mode)
        assert _schema_at(schema, (*path, "unit"))["const"] == unit
        assert _schema_at(schema, (*path, "approximation_decimal_places"))["const"] == 28
        assert _schema_at(schema, (*path, "approximation_exact"))["type"] == "boolean"
    for field, bad_values in (
        ("denominator", ("0", "-1", "0.0")),
        ("approximation_decimal_places", (27, 29, "28", True)),
        ("approximation_exact", (0, 1, "true", None)),
        ("unit", ("currency", None, True)),
    ):
        for bad in bad_values:
            mutated = deepcopy(wire)
            _at(mutated, path)[field] = bad
            _reject(PAC_ANALYZE_OUTPUT_ADAPTER, mutated)
    if path == ("totals", "squared_gap_pp2", "value"):
        ratio["numerator"] = "-1"
        _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)


@pytest.mark.parametrize("path", [
    ("rows", 0, "name"), ("normalized", "rows", 0, "name"),
])
@pytest.mark.parametrize("character", ["\U0001f680", "\x00"])
def test_output_names_preserve_128_unicode_scalars_and_reject_129(path, character, output_witnesses):
    wire = deepcopy(output_witnesses["ready"])
    _set(wire, path, character * 128)
    parsed = _roundtrip(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    emitted = PAC_ANALYZE_OUTPUT_ADAPTER.dump_json(parsed)
    assert _at(json.loads(emitted), path) == character * 128
    escaped = _encode(wire, ensure_ascii=True)
    assert PAC_ANALYZE_OUTPUT_ADAPTER.validate_json(escaped) == parsed
    _set(wire, path, character * 129)
    _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire, ensure_ascii=True)
    for surrogate in ("\ud800", "\udfff", "\ud800\ud800"):
        _set(wire, path, surrogate)
        _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire, ensure_ascii=True)
        with pytest.raises(ValidationError):
            PAC_ANALYZE_OUTPUT_ADAPTER.validate_python(wire)


@pytest.mark.parametrize("prefix", [("rows", 0), ("normalized", "rows", 0)])
@pytest.mark.parametrize("key,limit", [("row_key", 256), ("instrument_key", 128)])
def test_output_keys_retain_the_same_ascii_length_domain(prefix, key, limit, output_witnesses):
    wire = deepcopy(output_witnesses["ready"])
    path = (*prefix, key)
    _set(wire, path, "\\" * limit)
    _roundtrip(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    for bad in ("\\" * (limit + 1), "", " ", "\x00", "\x7f", "é", "\U0001f680"):
        _set(wire, path, bad)
        _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    for mode in ("validation", "serialization"):
        schema = PAC_ANALYZE_OUTPUT_ADAPTER.json_schema(mode=mode)
        field = _schema_at(schema, path)
        assert field["minLength"] == 1 and field["maxLength"] == limit
        assert re.fullmatch(field["pattern"], "\\" * limit)


@pytest.mark.parametrize("path", [
    ("normalized", "as_of_date"),
    ("normalized", "rows", 0, "quote", "reference_date"),
    ("normalized", "valuation_rates", 0, "reference_date"),
])
def test_normalized_dates_are_nullable_real_iso_dates_not_raw_drafts(path, output_witnesses):
    wire = deepcopy(output_witnesses["ready"])
    for valid in (None, "2024-02-29", "2026-09-08"):
        _set(wire, path, valid)
        _roundtrip(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    for bad in ("", "2026-02-29", "2026-13-01", "2026-9-08", "0000-01-01", True, 20260908):
        _set(wire, path, bad)
        _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)


def test_normalized_quote_basis_is_narrower_than_the_raw_integer_domain(output_witnesses):
    wire = deepcopy(output_witnesses["ready"])
    path = ("normalized", "rows", 0, "quote", "quote_base_quantity")
    for valid in (1, 100):
        _set(wire, path, valid)
        _roundtrip(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    for bad in (None, 0, -1, 2, 1000, True, 1.0, "100"):
        _set(wire, path, bad)
        _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    for mode in ("validation", "serialization"):
        schema = PAC_ANALYZE_OUTPUT_ADAPTER.json_schema(mode=mode)
        field = _schema_at(schema, path)
        assert field["type"] == "integer" and set(field["enum"]) == {1, 100}


@pytest.mark.parametrize("bad", [True, False, -1, 32, 0.0, "0", None])
def test_output_row_index_is_strict_zero_through_31(bad, output_witnesses):
    wire = deepcopy(output_witnesses["ready"])
    wire["rows"][0]["row_index"] = bad
    _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)


@pytest.mark.parametrize("path,limit", [
    (("rows",), 32),
    (("cash_pools", "value"), 4),
    (("normalized", "rows"), 32),
    (("normalized", "cash_balances"), 4),
    (("normalized", "contributions"), 4),
    (("normalized", "valuation_rates"), 5),
])
def test_output_collection_caps_are_codec_constraints(path, limit, output_witnesses):
    wire = deepcopy(output_witnesses["ready"])
    template = deepcopy(next(iter(_at(wire, path))))
    _set(wire, path, [deepcopy(template) for _ in range(limit)])
    _roundtrip(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    _at(wire, path).append(deepcopy(template))
    _reject(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    for mode in ("validation", "serialization"):
        schema = PAC_ANALYZE_OUTPUT_ADAPTER.json_schema(mode=mode)
        assert _schema_at(schema, path)["maxItems"] == limit


@pytest.mark.parametrize("mode", ["validation", "serialization"])
@pytest.mark.parametrize("adapter", [PAC_ANALYZE_INPUT_ADAPTER, PAC_ANALYZE_OUTPUT_ADAPTER])
def test_exported_objects_are_strict_and_literal_fields_required_without_defaults(mode, adapter):
    schema = adapter.json_schema(mode=mode)
    objects = [obj for _, obj in _objects(schema) if obj.get("type") == "object"]
    assert objects, "Export must contain the actual object definitions"
    for obj in objects:
        assert obj["additionalProperties"] is False, obj.get("title")
        properties = obj["properties"]
        required = set(obj.get("required", []))
        for field, spec in properties.items():
            resolved = _resolve(schema, spec)
            if "const" in resolved:
                assert field in required, (obj.get("title"), field)
                assert "default" not in spec
        if adapter is PAC_ANALYZE_OUTPUT_ADAPTER and set(properties) != PARAM_FIELDS:
            assert required == set(properties), obj.get("title")


@pytest.mark.parametrize("mode", ["validation", "serialization"])
def test_exported_input_defaults_and_field_specific_limits(mode):
    schema = PAC_ANALYZE_INPUT_ADAPTER.json_schema(mode=mode)
    root = _resolve(schema, schema)
    assert root["required"] == ["operation"]
    assert root["properties"]["operation"]["const"] == "analyze"
    for name in ("report_currency", "as_of_date", "cash_balances", "contributions"):
        field = root["properties"][name]
        assert field["default"] is None
        assert {"type": "null"} in field["anyOf"]
    row = _schema_at(schema, ("rows", 0))
    assert set(row["required"]) == {"row_key", "instrument_key"}
    for name in set(row["properties"]) - {"row_key", "instrument_key"}:
        assert row["properties"][name]["default"] is None
        assert {"type": "null"} in row["properties"][name]["anyOf"]
    for path in (
        ("rows", 0, "quote"), ("rows", 0, "buy_grid"),
        ("cash_balances", 0), ("contributions", 0), ("valuation_rates", 0),
    ):
        obj = _schema_at(schema, path)
        assert not obj.get("required")
        for prop in obj["properties"].values():
            assert prop["default"] is None
            assert {"type": "null"} in prop["anyOf"]
    for path, limit in TEXT_LIMITS:
        prop = _schema_at(schema, path)
        assert prop["type"] == "string"
        assert prop["maxLength"] == limit
        if path in DECIMAL_PATHS:
            assert "pattern" not in prop, "Malformed decimal drafts must remain structurally valid"
    for key, limit in (("row_key", 256), ("instrument_key", 128)):
        prop = _schema_at(schema, ("rows", 0, key))
        assert prop["minLength"] == 1
        assert prop["maxLength"] == limit
        assert re.fullmatch(prop["pattern"], '"\\')
        for bad in ("", " ", "é", "\x7f"):
            assert re.fullmatch(prop["pattern"], bad) is None
    for field, maximum in (("rows", 32), ("cash_balances", 4), ("contributions", 4), ("valuation_rates", 4)):
        assert _schema_at(schema, (field,))["maxItems"] == maximum


@pytest.mark.parametrize("mode", ["validation", "serialization"])
def test_exported_availability_branches_encode_conditional_bounds(mode):
    schema = PAC_ANALYZE_OUTPUT_ADAPTER.json_schema(mode=mode)
    union = _resolve(schema, schema)
    assert union["discriminator"]["propertyName"] == "availability"
    assert set(union["discriminator"]["mapping"]) == set(STATES)
    assert len(union["oneOf"]) == 4
    for state in STATES:
        branch = _branch(schema, schema, state)
        properties = branch["properties"]
        assert properties["availability"]["const"] == state
        assert {"availability", "normalized", "issues", *ROOT_LITERALS} <= set(branch["required"])
        for field, value in ROOT_LITERALS.items():
            assert properties[field]["const"] == value
            assert "default" not in properties[field]
        normalized = _resolve(schema, properties["normalized"])
        issues = properties["issues"]
        assert issues["maxItems"] == (80 if state == "ready" else 384)
        if state == "ready":
            assert normalized["type"] == "object"
            assert "anyOf" not in properties["normalized"]
            leaf = _resolve(schema, issues["items"])
            assert leaf["properties"]["kind"]["const"] == "info"
            assert set(leaf["properties"]["code"]["enum"]) == ISSUE_CODES["info"]
        else:
            assert normalized["type"] == "null"
            union = _resolve(schema, issues["items"])
            assert union["discriminator"]["propertyName"] == "kind"
            assert set(union["discriminator"]["mapping"]) == set(ISSUE_CODES)
            assert len(union["oneOf"]) == 4
            for kind, codes in ISSUE_CODES.items():
                leaf = _branch(schema, union, kind)
                assert leaf["properties"]["kind"]["const"] == kind
                assert set(leaf["properties"]["code"]["enum"]) == codes
        assert properties["rows"]["maxItems"] == 32


@pytest.mark.parametrize("mode", ["validation", "serialization"])
def test_exported_fact_unions_encode_nullability_reasons_and_nested_values(mode):
    schema = PAC_ANALYZE_OUTPUT_ADAPTER.json_schema(mode=mode)
    unions = [
        obj for _, obj in _objects(schema)
        if obj.get("discriminator", {}).get("propertyName") == "availability"
        and set(obj["discriminator"]["mapping"]) == {"available", "unavailable"}
    ]
    assert unions, "Facts must remain discriminated unions in the actual export"
    for union in unions:
        assert len(union["oneOf"]) == 2
        available = _branch(schema, union, "available")
        unavailable = _branch(schema, union, "unavailable")
        for obj in (available, unavailable):
            assert set(obj["required"]) == {"availability", "value", "reason_codes"}
            assert set(obj["properties"]) == {"availability", "value", "reason_codes"}
            assert "default" not in obj["properties"]["availability"]
            reasons = obj["properties"]["reason_codes"]
            assert set(_resolve(schema, reasons["items"])["enum"]) == REASONS
        assert available["properties"]["availability"]["const"] == "available"
        assert available["properties"]["reason_codes"]["maxItems"] == 0
        value = _resolve(schema, available["properties"]["value"])
        assert value["type"] in {"string", "object", "array"}
        assert "anyOf" not in value
        assert unavailable["properties"]["availability"]["const"] == "unavailable"
        assert unavailable["properties"]["value"]["type"] == "null"
        assert unavailable["properties"]["reason_codes"]["minItems"] == 1
        assert unavailable["properties"]["reason_codes"]["maxItems"] == 1
    row = _schema_at(schema, ("rows", 0))
    assert set(row["properties"]) == {
        "row_index", "row_key", "instrument_key", "name", "quantity",
        "initial_value_native", "initial_value_reporting", "current_weight_percent",
        "target_percent", "deviation_pp",
    }
    index = row["properties"]["row_index"]
    assert index["type"] == "integer" and index["minimum"] == 0 and index["maximum"] == 31
    for path in (("rows", 0, "name"), ("normalized", "rows", 0, "name")):
        assert _schema_at(schema, path)["maxLength"] == 128
    totals = _schema_at(schema, ("totals",))
    assert set(totals["properties"]) == {
        "initial_invested_reporting", "existing_cash_reporting", "contributions_reporting",
        "cash_plus_contributions_reporting", "target_total_percent", "max_abs_gap_pp",
        "squared_gap_pp2",
    }
    pools = _schema_at(schema, ("cash_pools", "value"))
    assert pools["type"] == "array" and pools["maxItems"] == 4
    pool = _resolve(schema, pools["items"])
    assert set(pool["properties"]) == {
        "currency", "existing_amount", "contribution_amount", "combined_amount",
        "existing_reporting", "contribution_reporting", "combined_reporting",
    }


@pytest.mark.parametrize("mode", ["validation", "serialization"])
@pytest.mark.parametrize("path,width", NUMERIC_FIELDS)
def test_exported_numeric_widths_match_each_validation_field(mode, path, width):
    schema = PAC_ANALYZE_OUTPUT_ADAPTER.json_schema(mode=mode)
    prop = _schema_at(schema, path)
    assert prop["type"] == "string"
    assert prop["minLength"] == 1
    assert prop["maxLength"] == width
    assert re.fullmatch(prop["pattern"], "1" + "0" * (width - 1))
    for malformed in ("NaN", "Infinity", "1e3", "１２", "01", " 1 "):
        assert re.fullmatch(prop["pattern"], malformed) is None


@pytest.mark.parametrize("mode", ["validation", "serialization"])
def test_exported_issue_paths_indices_and_params_are_bounded(mode):
    schema = PAC_ANALYZE_OUTPUT_ADAPTER.json_schema(mode=mode)
    issue = _schema_at(schema, ("issues", 0), state="invalid")
    props = issue["properties"]
    assert set(props) == {"kind", "code", "path", "related_row_indices", "params"}
    path = props["path"]
    assert path["maxItems"] == 4
    tokens = path["items"]["anyOf"]
    (names,) = [item for item in tokens if item.get("type") == "string"]
    (indices,) = [item for item in tokens if item.get("type") == "integer"]
    assert set(names["enum"]) == PATH_FIELDS
    assert max(map(len, names["enum"])) <= 19
    assert indices["minimum"] == 0 and indices["maximum"] == 31
    related = props["related_row_indices"]
    assert related["maxItems"] == 32 and related["uniqueItems"] is True
    assert related["items"]["type"] == "integer"
    assert related["items"]["minimum"] == 0 and related["items"]["maximum"] == 31
    params = _resolve(schema, props["params"])
    assert set(params["properties"]) == PARAM_FIELDS
    assert params["additionalProperties"] is False
    limit = _schema_at(schema, ("issues", 0, "params", "limit"), state="invalid")
    assert limit["type"] == "integer" and limit["minimum"] == 0 and limit["maximum"] == 512
    bases = _schema_at(schema, ("issues", 0, "params", "allowed_quote_bases"), state="invalid")
    assert bases["maxItems"] == 2
    assert bases["items"]["type"] == "integer" and set(bases["items"]["enum"]) == {1, 100}
    currency = _schema_at(schema, ("issues", 0, "params", "currency"), state="invalid")
    assert currency["minLength"] == currency["maxLength"] == 3
    vector = _schema_at(schema, ("issues", 0, "params", "vector"), state="invalid")
    assert set(vector["enum"]) == {"cash_balances", "contributions", "valuation_rates"}
    unit = _schema_at(schema, ("issues", 0, "params", "unit"), state="invalid")
    assert set(unit["enum"]) == {"quantity", "quote", "rate", "percent", "native_amount"}


def _escaped_key(index: int, length: int) -> str:
    # Five bits distinguish all 32 owned rows; every character needs JSON escaping.
    prefix = "".join('"' if index & (1 << bit) else "\\" for bit in range(5))
    return prefix + "\\" * (length - len(prefix))


def _stress_request(name: str, *, invalid: bool) -> dict[str, Any]:
    payload = _request()
    maximum = "999999999999.999999999999"
    currencies = ("EUR", "USD", "GBP", "JPY")
    payload["rows"] = []
    for index in range(32):
        payload["rows"].append({
            "row_key": _escaped_key(index, 256),
            "instrument_key": _escaped_key(index, 128),
            "name": name,
            "initial_quantity": maximum,
            "quote": {
                "raw_price": maximum, "currency": currencies[index % 4],
                "quote_base_quantity": 100, "reference_date": None,
            },
            "target_percent": "x" * 64 if invalid else "3.125",
            "buy_grid": {"mode": "whole", "quantity_step": "1"},
        })
    for field in ("cash_balances", "contributions"):
        payload[field] = [{"currency": currency, "amount": maximum} for currency in currencies]
    payload["valuation_rates"] = [
        {"currency": currency, "rate_to_report": "1" if currency == "EUR" else maximum,
         "reference_date": None}
        for currency in currencies
    ]
    return payload


@pytest.mark.parametrize("state,issue_limit", [("ready", 80), ("invalid", 384)])
@pytest.mark.parametrize("name", [
    "\U0001f680" * 128, "\x00" * 128, ("\U0001f680\x00\x01\x02" * 32),
], ids=["128-non-bmp", "128-six-byte-controls", "mixed-scalars-and-controls"])
def test_real_utf8_serialization_fits_256_kib_with_maximum_codec_issue_arrays(state, issue_limit, name):
    """Representability witness, not a runtime benchmark or a financial mutation oracle."""
    payload = _stress_request(name, invalid=state == "invalid")
    assert len(payload["rows"]) == 32
    assert len({row["row_key"] for row in payload["rows"]}) == 32
    assert all(len(row["row_key"]) == 256 and len(row["instrument_key"]) == 128 for row in payload["rows"])
    assert len(name) == 128
    wire = _analyzed(payload, state)
    assert len(wire["rows"]) == 32
    assert [(row["row_key"], row["instrument_key"], row["name"]) for row in wire["rows"]] == [
        (row["row_key"], row["instrument_key"], name) for row in payload["rows"]
    ]
    assert (wire["normalized"] is not None) == (state == "ready")
    assert len(wire["issues"]) <= issue_limit
    kind = "info" if state == "ready" else "invalid"
    seed = next(issue for issue in wire["issues"] if issue["kind"] == kind)
    issue = deepcopy(seed)
    issue.update(
        path=["rows", 31, "quote", "quote_base_quantity"],
        related_row_indices=list(range(32)),
        params={
            "currency": "EUR", "vector": "valuation_rates", "limit": 512,
            "allowed_quote_bases": [1, 100], "unit": "native_amount",
        },
    )
    # Saturate only the bounded issue codec, preserving actual financial facts.
    # Repeated issues are not a claim that the service naturally emits 80/384.
    wire["issues"] = [deepcopy(issue) for _ in range(issue_limit)]
    validated = _roundtrip(PAC_ANALYZE_OUTPUT_ADAPTER, wire)
    emitted = PAC_ANALYZE_OUTPUT_ADAPTER.dump_json(validated)
    decoded = json.loads(emitted)
    assert isinstance(decoded, dict), "Never double-encode the result as a JSON string"
    assert len(decoded["issues"]) == issue_limit
    assert len(decoded["rows"]) == 32
    assert emitted == _encode(decoded), "Output must use compact scalar-preserving UTF-8 JSON"
    assert len(emitted) < 256 * 1024, f"{state} codec witness emitted {len(emitted)} bytes"
    assert len(_encode(payload)) <= 128 * 1024
    if "\U0001f680" in name:
        assert "\U0001f680".encode("utf-8") in emitted
        assert b"\\ud83d" not in emitted.lower()
    if "\x00" in name:
        assert b"\\u0000" in emitted
    assert PAC_ANALYZE_OUTPUT_ADAPTER.validate_json(emitted) == validated


@pytest.mark.parametrize(
    "target",
    [
        "backend.app.schemas.pac_allocator",
        "backend.app.services.pac_allocator",
    ],
)
def test_p1_fresh_process_import_does_not_load_legacy_application_dependencies(target):
    """Observe a real interpreter; no fake packages or sys.modules manipulation."""
    script = dedent(
        """
        import importlib
        import json
        import sys

        before = sorted(sys.modules)
        module = importlib.import_module(sys.argv[1])
        assert module.__name__ == sys.argv[1]
        if sys.argv[1] == "backend.app.schemas.pac_allocator":
            from pydantic import TypeAdapter
            assert isinstance(module.PAC_ANALYZE_INPUT_ADAPTER, TypeAdapter)
            assert isinstance(module.PAC_ANALYZE_OUTPUT_ADAPTER, TypeAdapter)
        else:
            assert callable(module.analyze_initial_state)
        print(json.dumps({"before": before, "after": sorted(sys.modules)}))
        """
    )
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script, target],
        cwd=FilePath(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    observation = json.loads(completed.stdout)
    assert target in observation["after"]
    assert target not in observation["before"], "The witness must begin before the P1 import"
    forbidden = (
        "backend.app.api",
        "backend.app.main",
        "backend.app.db",
        "backend.app.services.broker_service",
        "backend.app.services.transaction_service",
        "backend.app.services.brim",
        "backend.app.services.asset_source_providers",
        "backend.app.services.fx_providers",
        "backend.app.schemas.brim",
        "backend.app.schemas.brokers",
        "backend.app.schemas.transactions",
        "backend.app.utils.financial.roi_utils",
        "backend.app.utils.financial.wac_utils",
        "sqlalchemy",
        "sqlmodel",
        "fastapi",
        "uvicorn",
        "httpx",
        "scipy",
    )
    for phase in ("before", "after"):
        loaded = [
            name
            for name in observation[phase]
            if any(name.startswith(prefix) for prefix in forbidden)
        ]
        assert loaded == [], (phase, loaded)


def test_lazy_parent_metadata_and_common_aliases_are_light_in_a_fresh_process():
    """dir/__all__/unknown attributes must not force heavy legacy lazy exports."""
    script = dedent(
        """
        import importlib
        import json
        import sys

        packages = {
            name: importlib.import_module(name)
            for name in (
                "backend.app.services",
                "backend.app.schemas",
                "backend.app.utils.financial",
            )
        }
        services = packages["backend.app.services"]
        schemas = packages["backend.app.schemas"]
        financial = packages["backend.app.utils.financial"]
        assert set(services.__all__) == {
            "BalanceValidationError", "BrokerService",
            "LinkedTransactionError", "TransactionService",
        }
        assert set(financial.__all__) == {
            "WACInputTX", "WACCalcResult", "compute_wac_from_txlist",
            "determine_target_currency", "CashFlowInput", "NAVSnapshot",
            "ROIResult", "SimpleROIPoint", "TWRRPoint", "MWRRPoint",
            "calculate_simple_roi", "calculate_simple_roi_series",
            "calculate_twrr", "calculate_twrr_series",
            "calculate_mwrr", "calculate_mwrr_series",
        }
        common_names = {
            "Currency", "BackwardFillInfo", "DateRangeModel", "OldNew",
            "BaseBulkResponse", "BaseDeleteResult", "BaseBulkDeleteResponse",
        }
        assert common_names | {
            "BRCreateItem", "TXCreateItem", "FAAssetCreateItem", "FAPricePoint",
            "BRIMFileInfo", "BRIMParseRequest", "FXConversionRequest",
            "SignalRequest", "SystemInfoResponse",
        } <= set(schemas.__all__)
        expected_modules = {
            "backend.app.services": {"broker_service", "transaction_service"},
            "backend.app.schemas": {
                "assets", "brim", "brokers", "common", "fx", "prices",
                "provider", "refresh", "signals", "system", "transactions",
            },
            "backend.app.utils.financial": {"roi_utils", "wac_utils"},
        }
        before_metadata = sorted(sys.modules)
        directories = {}
        for name, package in packages.items():
            assert all(isinstance(item, str) for item in package.__all__)
            directory = dir(package)
            assert directory == sorted(set(directory))
            assert set(package.__all__) | expected_modules[name] <= set(directory)
            directories[name] = directory
            try:
                getattr(package, "unknown_pac_test_export")
            except AttributeError:
                pass
            else:
                raise AssertionError(name + " accepted an unknown attribute")
            assert not hasattr(package, "unknown_pac_test_export")
        assert sorted(sys.modules) == before_metadata

        # Resolve the lazy root names before the direct module import.
        aliases = {name: getattr(schemas, name) for name in common_names}
        common = importlib.import_module("backend.app.schemas.common")
        from backend.app.schemas import Currency
        assert Currency is common.Currency
        assert schemas.common is common
        for name, value in aliases.items():
            assert value is getattr(common, name)
            assert value is getattr(schemas, name)
        print(json.dumps({
            "modules": sorted(sys.modules),
            "aliases": sorted(aliases),
            "directories": directories,
        }))
        """
    )
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=FilePath(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    observation = json.loads(completed.stdout)
    assert set(observation["aliases"]) == {
        "Currency", "BackwardFillInfo", "DateRangeModel", "OldNew",
        "BaseBulkResponse", "BaseDeleteResult", "BaseBulkDeleteResponse",
    }
    for name in observation["modules"]:
        assert not name.startswith(
            (
                "backend.app.db",
                "backend.app.api",
                "backend.app.main",
                "backend.app.services.broker_service",
                "backend.app.services.transaction_service",
                "backend.app.services.brim",
                "backend.app.schemas.brim",
                "backend.app.schemas.brokers",
                "backend.app.schemas.transactions",
                "backend.app.utils.financial.roi_utils",
                "backend.app.utils.financial.wac_utils",
                "sqlalchemy",
                "sqlmodel",
                "fastapi",
                "uvicorn",
                "httpx",
                "scipy",
            )
        ), name
