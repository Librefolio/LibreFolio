"""Pure Tool wire tests with owned payloads and private, strict Pydantic fixtures."""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError, ValidationInfo, field_validator
from pydantic_core import PydanticCustomError

from backend.app.schemas.tools import ToolError, ToolErrorCode
from backend.app.services.tools import wire
from backend.app.services.tools.base import ToolExecutionError


class _StrictFixtureModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)


class _CountRow(_StrictFixtureModel):
    count: int


class _RowBatch(_StrictFixtureModel):
    rows: list[_CountRow]


class _NamedRows(_StrictFixtureModel):
    rows: dict[str, _CountRow]


class _IndexedRows(_StrictFixtureModel):
    rows: dict[int, _CountRow]


class _NestedRow(_StrictFixtureModel):
    count: int
    child: _NestedRow | None = None


class _RejectedValue(_StrictFixtureModel):
    value: str

    @field_validator("value")
    @classmethod
    def reject_value(cls, value: str) -> str:
        raise ValueError(f"PRIVATE_MESSAGE_SENTINEL::{value}")


class _CustomIssueValue(_StrictFixtureModel):
    value: str

    @field_validator("value")
    @classmethod
    def reject_value(cls, value: str, info: ValidationInfo) -> str:
        context = info.context
        assert isinstance(context, dict)
        raise PydanticCustomError(context["issue_code"], "PRIVATE_MESSAGE_SENTINEL: {secret}", {"secret": context["secret"], "submitted": value})


def _place_text(text: str, location: str) -> object:
    if location == "root":
        return text
    if location == "list":
        return [text]
    if location == "value":
        return {"text": text}
    if location == "key":
        return {text: "safe"}
    if location == "nested-key":
        return {"rows": [{text: "safe"}]}
    raise AssertionError(f"Unknown fixture location: {location}")


def _nest(value: object, levels: int, kind: str) -> object:
    for _ in range(levels):
        value = [value] if kind == "list" else {"child": value}
    return value


def _ascii_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def _assert_public_error(error: ToolError, *, code: ToolErrorCode, issues: list[dict[str, object]], count: int, private: tuple[str, ...] = ()) -> None:
    assert isinstance(error, ToolError)
    payload = error.model_dump(mode="json")
    assert payload == {"code": code, "retryable": False, "issues": issues, "issue_count": count}
    public_forms = (wire.encode_json(payload).decode("utf-8"), error.model_dump_json(), str(error), repr(error))
    for secret in private:
        assert secret, "Privacy fixtures must use nonempty sentinels"
        assert all(secret not in rendered for rendered in public_forms)


def test_encode_json_is_compact_sorted_utf8_without_normalizing_keys_or_text() -> None:
    value = {"😀": "漢字", "é": "café", "e\u0301": "cafe\u0301", "a": [None, True, 1, 1.0, "1"]}
    expected = '{"a":[null,true,1,1.0,"1"],"e\u0301":"cafe\u0301","é":"café","😀":"漢字"}'.encode("utf-8")

    encoded = wire.encode_json(value)

    assert type(encoded) is bytes
    assert encoded == expected
    assert b"\\u" not in encoded
    assert wire.parse_json(encoded) == value
    assert wire.decode_json(encoded) == value


@pytest.mark.parametrize(
    ("start", "stop"),
    [
        pytest.param(0, 0xD800, id="bmp-before-surrogates"),
        pytest.param(0xE000, 0x10000, id="bmp-after-surrogates"),
        pytest.param(0x10000, 0x110000, id="all-non-bmp-scalars"),
    ],
)
@pytest.mark.parametrize("location", ("key", "value"))
def test_every_unicode_scalar_survives_the_wire(start: int, stop: int, location: str) -> None:
    # Includes controls, noncharacters and unassigned scalars, not only printable text.
    text = "".join(chr(codepoint) for codepoint in range(start, stop))
    value = _place_text(text, location)

    wire.validate_json_value(value)
    encoded = wire.encode_json(value)

    assert wire.parse_json(encoded) == value
    assert wire.decode_json(encoded) == value


@pytest.mark.parametrize("location", ("root", "list", "value", "key", "nested-key"))
@pytest.mark.parametrize(
    "text",
    [
        pytest.param("\ud800", id="first-high-surrogate"),
        pytest.param("\udbff", id="last-high-surrogate"),
        pytest.param("\udc00", id="first-low-surrogate"),
        pytest.param("\udfff", id="last-low-surrogate"),
        pytest.param("before\ud800after", id="embedded-surrogate"),
        pytest.param("\ud83d\ude00", id="python-code-units-are-not-a-scalar"),
    ],
)
def test_surrogates_are_rejected_before_json_encoder_is_entered(text: str, location: str, monkeypatch: pytest.MonkeyPatch) -> None:
    value = _place_text(text, location)

    def forbidden_encoder(*args: object, **kwargs: object) -> None:
        raise AssertionError("JSONEncoder must not be entered for invalid Unicode")

    with monkeypatch.context() as patch:
        patch.setattr(wire.json, "JSONEncoder", forbidden_encoder)

        with pytest.raises(ValueError, match="valid Unicode scalars"):
            wire.validate_json_value(value)
        with pytest.raises(ValueError, match="valid Unicode scalars"):
            wire.encode_json(value)
        with pytest.raises(ValueError, match="valid Unicode scalars"):
            wire.encode_json(value, max_bytes=0)


@pytest.mark.parametrize("location", ("root", "list", "value", "key", "nested-key"))
@pytest.mark.parametrize("surrogate", ("\ud800", "\udbff", "\udc00", "\udfff"))
def test_parse_json_defers_scalar_validation_but_decode_json_rejects_surrogates(surrogate: str, location: str, monkeypatch: pytest.MonkeyPatch) -> None:
    value = _place_text(surrogate, location)
    payload = _ascii_json(value)

    def forbidden_validation(*args: object, **kwargs: object) -> None:
        raise AssertionError("parse_json must not perform scalar validation")

    with monkeypatch.context() as patch:
        patch.setattr(wire, "validate_json_value", forbidden_validation)
        assert wire.parse_json(payload) == value

    with pytest.raises(ValueError, match="valid Unicode scalars"):
        wire.decode_json(payload)


@pytest.mark.parametrize(
    ("escaped", "scalar"),
    [
        pytest.param(r"\ud800\udc00", "\U00010000", id="first-non-bmp"),
        pytest.param(r"\ud834\udd1e", "\U0001d11e", id="musical-symbol"),
        pytest.param(r"\ud83d\ude00", "😀", id="emoji"),
        pytest.param(r"\udbff\udfff", "\U0010ffff", id="last-unicode-scalar"),
    ],
)
def test_escaped_surrogate_pairs_become_scalars_in_keys_and_values(escaped: str, scalar: str) -> None:
    payload = f'{{"{escaped}":["{escaped}"]}}'.encode("ascii")
    expected = {scalar: [scalar]}

    assert wire.parse_json(payload) == expected
    assert wire.decode_json(payload) == expected
    assert wire.encode_json(expected) == f'{{"{scalar}":["{scalar}"]}}'.encode("utf-8")


@pytest.mark.parametrize("literal", (b"NaN", b"Infinity", b"-Infinity", b"1e309", b"-1e309", b"9.99E999999"))
def test_both_parsers_reject_nonfinite_numbers_including_exponent_overflow(literal: bytes) -> None:
    for payload in (literal, b'{"rows":[' + literal + b"]}"):
        for parser in (wire.parse_json, wire.decode_json):
            with pytest.raises(ValueError):
                parser(payload)


@pytest.mark.parametrize("literal", ("nan", "inf", "-inf"))
def test_python_nonfinite_numbers_are_rejected_before_encoding(literal: str) -> None:
    number = float(literal)
    for value in (number, {"rows": [number]}):
        with pytest.raises(ValueError, match="numbers must be finite"):
            wire.validate_json_value(value)
        with pytest.raises(ValueError, match="numbers must be finite"):
            wire.encode_json(value)


def test_finite_exponents_and_nonfinite_looking_strings_remain_valid() -> None:
    payload = b'{"finite":[1e308,-1e308,1e-300],"text":["NaN","Infinity","1e309"]}'
    expected = {"finite": [1e308, -1e308, 1e-300], "text": ["NaN", "Infinity", "1e309"]}

    assert wire.parse_json(payload) == expected
    assert wire.decode_json(payload) == expected
    assert wire.decode_json(wire.encode_json(expected)) == expected


@pytest.mark.parametrize(
    "document",
    [
        '{"x":1,"x":2}',
        '{"x":null,"x":null}',
        r'{"a":1,"\u0061":2}',
        '{"é":1,"\\u00e9":2}',
        '{"😀":1,"\\ud83d\\ude00":2}',
        '{"outer":[{"x":1,"x":2}]}',
    ],
)
def test_both_parsers_reject_duplicate_decoded_keys(document: str) -> None:
    for parser in (wire.parse_json, wire.decode_json):
        with pytest.raises(ValueError, match="Duplicate JSON object keys"):
            parser(document.encode("utf-8"))


def test_duplicate_key_detection_is_scoped_to_each_object() -> None:
    payload = b'[{"x":1},{"x":2}]'
    expected = [{"x": 1}, {"x": 2}]

    assert wire.parse_json(payload) == expected
    assert wire.decode_json(payload) == expected


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"{",
        b"[1,]",
        b'{"a":}',
        b'{"a":1,}',
        b'{"a":1 "b":2}',
        b'{"a":01}',
        b"{'a':1}",
        b"true false",
        b"null trailing",
        b'"unterminated',
        b'"unescaped\nnewline"',
        b'"\\x41"',
        b'"\\u12G4"',
    ],
)
def test_malformed_json_fails_syntax_parsing(payload: bytes) -> None:
    for parser in (wire.parse_json, wire.decode_json):
        with pytest.raises(json.JSONDecodeError):
            parser(payload)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(b'"\xff"', id="invalid-leading-byte"),
        pytest.param(b'"\x80"', id="lone-continuation"),
        pytest.param(b'"\xc0\xaf"', id="overlong-sequence"),
        pytest.param(b'"\xc3"', id="incomplete-sequence"),
        pytest.param(b'"\xed\xa0\x80"', id="utf8-encoded-surrogate"),
        pytest.param(b'"\xf4\x90\x80\x80"', id="above-unicode-range"),
    ],
)
def test_both_parsers_reject_invalid_utf8(payload: bytes) -> None:
    for parser in (wire.parse_json, wire.decode_json):
        with pytest.raises(UnicodeDecodeError):
            parser(payload)


@pytest.mark.parametrize(
    ("payload", "expected", "scalar_type"),
    [
        pytest.param(b'"1"', "1", str, id="string"),
        pytest.param(b"1", 1, int, id="integer"),
        pytest.param(b"1.0", 1.0, float, id="float"),
        pytest.param(b"true", True, bool, id="true"),
        pytest.param(b"false", False, bool, id="false"),
        pytest.param(b"null", None, type(None), id="null"),
        pytest.param(b"-0.0", -0.0, float, id="negative-zero"),
    ],
)
def test_scalar_types_are_preserved_without_python_equality_conflation(payload: bytes, expected: object, scalar_type: type) -> None:
    for parser in (wire.parse_json, wire.decode_json):
        value = parser(payload)
        assert type(value) is scalar_type
        assert value == expected
        assert wire.encode_json(value) == payload


def test_missing_member_and_explicit_null_remain_distinct() -> None:
    for parser in (wire.parse_json, wire.decode_json):
        missing = parser(b"{}")
        explicit_null = parser(b'{"value":null}')

        assert missing == {}
        assert explicit_null == {"value": None}
        assert "value" not in missing
        assert "value" in explicit_null
        assert wire.encode_json(missing) == b"{}"
        assert wire.encode_json(explicit_null) == b'{"value":null}'


@pytest.mark.parametrize("payload", (b"null", b"false", b"1", b"1.0", b'"text"', b"[]", b"{}"))
def test_root_scalars_and_empty_containers_have_depth_zero(payload: bytes) -> None:
    value = wire.parse_json(payload)

    wire.validate_json_value(value, max_depth=0)
    assert wire.encode_json(value, max_depth=0) == payload
    assert wire.decode_json(payload, max_depth=0) == value


@pytest.mark.parametrize("kind", ("list", "dict"))
@pytest.mark.parametrize("limit", (0, 1, 2, 32))
def test_depth_limit_is_inclusive_and_counts_children_from_root_zero(kind: str, limit: int) -> None:
    at_limit = _nest(None, limit, kind)
    at_limit_payload = _ascii_json(at_limit)
    beyond_limit = _nest(None, limit + 1, kind)
    beyond_limit_payload = _ascii_json(beyond_limit)

    wire.validate_json_value(at_limit, max_depth=limit)
    assert wire.encode_json(at_limit, max_depth=limit) == at_limit_payload
    assert wire.decode_json(at_limit_payload, max_depth=limit) == at_limit
    assert wire.parse_json(beyond_limit_payload) == beyond_limit

    with pytest.raises(ValueError, match="nesting depth"):
        wire.validate_json_value(beyond_limit, max_depth=limit)
    with pytest.raises(ValueError, match="nesting depth"):
        wire.encode_json(beyond_limit, max_depth=limit)
    with pytest.raises(ValueError, match="nesting depth"):
        wire.decode_json(beyond_limit_payload, max_depth=limit)


@pytest.mark.parametrize("payload", (b"[[]]", b"[{}]", b'{"child":[]}', b'{"child":{}}'))
def test_empty_nested_containers_still_consume_one_depth_level(payload: bytes) -> None:
    value = wire.parse_json(payload)

    wire.validate_json_value(value, max_depth=1)
    assert wire.encode_json(value, max_depth=1) == payload
    assert wire.decode_json(payload, max_depth=1) == value
    with pytest.raises(ValueError, match="nesting depth"):
        wire.validate_json_value(value, max_depth=0)
    with pytest.raises(ValueError, match="nesting depth"):
        wire.encode_json(value, max_depth=0)
    with pytest.raises(ValueError, match="nesting depth"):
        wire.decode_json(payload, max_depth=0)


@pytest.mark.parametrize("kind", ("list", "dict"))
def test_default_depth_limit_is_32_but_parse_json_has_no_scalar_depth_check(kind: str) -> None:
    at_limit = _nest(None, 32, kind)
    beyond_limit = _nest(None, 33, kind)
    beyond_limit_payload = _ascii_json(beyond_limit)

    wire.validate_json_value(at_limit)
    assert wire.encode_json(at_limit) == _ascii_json(at_limit)
    assert wire.decode_json(_ascii_json(at_limit)) == at_limit
    assert wire.parse_json(beyond_limit_payload) == beyond_limit
    with pytest.raises(ValueError, match="nesting depth"):
        wire.validate_json_value(beyond_limit)
    with pytest.raises(ValueError, match="nesting depth"):
        wire.encode_json(beyond_limit)
    with pytest.raises(ValueError, match="nesting depth"):
        wire.decode_json(beyond_limit_payload)


@pytest.mark.parametrize("limit_code", (None, "output_limit_exceeded"))
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(0, b"0", id="single-byte"),
        pytest.param("é", b'"\xc3\xa9"', id="multibyte"),
        pytest.param("😀e\u0301", b'"\xf0\x9f\x98\x80e\xcc\x81"', id="non-bmp-decomposed"),
        pytest.param('\x00\n"\\', b'"\\u0000\\n\\"\\\\"', id="escaped-controls"),
    ],
)
def test_exact_encoded_byte_limit_passes_and_one_byte_overflow_raises(value: object, expected: bytes, limit_code: ToolErrorCode | None) -> None:
    options = {} if limit_code is None else {"limit_code": limit_code}
    expected_code = "input_limit_exceeded" if limit_code is None else limit_code

    assert wire.encode_json(value, max_bytes=len(expected), **options) == expected
    assert wire.encode_json(value, max_bytes=len(expected) + 1, **options) == expected
    with pytest.raises(ToolExecutionError) as caught:
        wire.encode_json(value, max_bytes=len(expected) - 1, **options)

    assert caught.value.code == expected_code
    assert caught.value.retryable is False
    assert str(caught.value) == expected_code


@pytest.mark.parametrize("limit_code", (None, "output_limit_exceeded"))
def test_byte_budget_includes_unicode_keys_and_all_container_bytes_without_truncation(limit_code: ToolErrorCode | None) -> None:
    value = {"é": "😀e\u0301\n", "a": [None, True]}
    expected_text = '{"a":[null,true],"é":"😀e\u0301\\n"}'
    expected = expected_text.encode("utf-8")
    options = {} if limit_code is None else {"limit_code": limit_code}
    expected_code = "input_limit_exceeded" if limit_code is None else limit_code

    assert len(expected) > len(expected_text)
    assert wire.encode_json(value, max_bytes=len(expected), **options) == expected
    for limit in (len(expected) - 1, len(expected_text)):
        with pytest.raises(ToolExecutionError) as caught:
            wire.encode_json(value, max_bytes=limit, **options)
        assert caught.value.code == expected_code
        assert caught.value.retryable is False


@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(object, id="opaque-object"),
        pytest.param(lambda: (1, 2), id="tuple"),
        pytest.param(lambda: {1, 2}, id="set"),
        pytest.param(lambda: frozenset({1}), id="frozenset"),
        pytest.param(lambda: b"bytes", id="bytes"),
        pytest.param(lambda: bytearray(b"bytes"), id="bytearray"),
        pytest.param(lambda: _CountRow(count=1), id="pydantic-model"),
    ],
)
def test_unsupported_python_objects_are_not_implicitly_serialized(factory: Callable[[], object]) -> None:
    unsupported = factory()
    for value in (unsupported, {"rows": [unsupported]}):
        with pytest.raises(ValueError, match="JSON values, not Python objects"):
            wire.validate_json_value(value)
        with pytest.raises(ValueError, match="JSON values, not Python objects"):
            wire.encode_json(value)


@pytest.mark.parametrize("key", (None, True, 1, 1.5, b"key", ("key",)))
def test_non_string_python_keys_are_rejected_instead_of_coerced(key: object) -> None:
    value = {key: "safe"}

    with pytest.raises(ValueError, match="object keys must be strings"):
        wire.validate_json_value(value)
    with pytest.raises(ValueError, match="object keys must be strings"):
        wire.encode_json(value)
    with pytest.raises(ValueError, match="Expected a JSON object"):
        wire.plain_json_object(value)


def test_plain_json_object_returns_the_owned_dictionary_without_copying() -> None:
    value = {"é": [1, None]}

    assert wire.plain_json_object(value) is value


@pytest.mark.parametrize("payload", (b"null", b"true", b"1", b'"text"', b"[]"))
def test_plain_json_object_rejects_non_object_json_roots(payload: bytes) -> None:
    value = wire.decode_json(payload)

    with pytest.raises(ValueError, match="Expected a JSON object"):
        wire.plain_json_object(value)


@pytest.mark.parametrize("code", ("invalid_parameters", "invalid_output"))
def test_validation_error_redacts_real_pydantic_input_exception_context_and_message(code: ToolErrorCode) -> None:
    private_input = "PRIVATE_INPUT_SENTINEL::submitted-value"
    with pytest.raises(ValidationError) as caught:
        _RejectedValue.model_validate({"value": private_input})

    (raw_issue,) = caught.value.errors(include_url=False)
    assert raw_issue["input"] == private_input
    assert "PRIVATE_MESSAGE_SENTINEL" in raw_issue["msg"]
    assert private_input in raw_issue["msg"]
    assert isinstance(raw_issue["ctx"]["error"], ValueError)
    assert private_input in str(raw_issue["ctx"]["error"])

    result = wire.validation_error(caught.value, code=code)

    _assert_public_error(result, code=code, issues=[{"code": "value_error", "path": ["value"]}], count=1, private=(private_input, "PRIVATE_MESSAGE_SENTINEL"))


@pytest.mark.parametrize("count", (1, 32, 33, 40))
def test_validation_error_caps_details_at_32_without_losing_the_total(count: int) -> None:
    private_input = "PRIVATE_INPUT_SENTINEL::not-an-integer"
    data = {"rows": [{"count": private_input} for _ in range(count)]}
    with pytest.raises(ValidationError) as caught:
        _RowBatch.model_validate(data)

    assert caught.value.error_count() == count
    result = wire.validation_error(caught.value, code="invalid_parameters")

    expected_issues = [{"code": "int_type", "path": ["rows", index, "count"]} for index in range(min(count, 32))]
    _assert_public_error(result, code="invalid_parameters", issues=expected_issues, count=count, private=(private_input,))


@pytest.mark.parametrize("safe_key", ("_", "field_19", "A" * 64))
def test_validation_error_preserves_safe_path_tokens_through_the_64_character_boundary(safe_key: str) -> None:
    private_input = "PRIVATE_INPUT_SENTINEL::wrong-count"
    with pytest.raises(ValidationError) as caught:
        _NamedRows.model_validate({"rows": {safe_key: {"count": private_input}}})

    (raw_issue,) = caught.value.errors(include_url=False)
    assert raw_issue["loc"] == ("rows", safe_key, "count")
    result = wire.validation_error(caught.value, code="invalid_parameters")

    _assert_public_error(result, code="invalid_parameters", issues=[{"code": "int_type", "path": ["rows", safe_key, "count"]}], count=1, private=(private_input,))


@pytest.mark.parametrize(
    "unsafe_key",
    [
        "",
        "0_PRIVATE_PATH_SENTINEL",
        "PRIVATE_PATH_SENTINEL/secret",
        "PRIVATE_PATH_SENTINEL.secret",
        "PRIVATE_PATH_SENTINEL-secret",
        "PRIVATE_PATH_SENTINEL\nsecret",
        "é_PRIVATE_PATH_SENTINEL",
        "k" * 65,
    ],
)
def test_validation_error_stops_at_an_unsafe_path_token_without_resuming(unsafe_key: str) -> None:
    private_input = "PRIVATE_INPUT_SENTINEL::wrong-count"
    with pytest.raises(ValidationError) as caught:
        _NamedRows.model_validate({"rows": {unsafe_key: {"count": private_input}}})

    (raw_issue,) = caught.value.errors(include_url=False)
    assert raw_issue["loc"] == ("rows", unsafe_key, "count")
    result = wire.validation_error(caught.value, code="invalid_parameters")
    private = (private_input, unsafe_key) if unsafe_key else (private_input,)

    _assert_public_error(result, code="invalid_parameters", issues=[{"code": "int_type", "path": ["rows"]}], count=1, private=private)


def test_validation_error_can_redact_the_entire_path_for_an_unsafe_extra_field() -> None:
    private_key = "PRIVATE_PATH_SENTINEL/extra"
    private_input = "PRIVATE_INPUT_SENTINEL::extra-value"
    with pytest.raises(ValidationError) as caught:
        _CountRow.model_validate({"count": 1, private_key: private_input})

    (raw_issue,) = caught.value.errors(include_url=False)
    assert raw_issue["loc"] == (private_key,)
    assert raw_issue["type"] == "extra_forbidden"
    result = wire.validation_error(caught.value, code="invalid_parameters")

    _assert_public_error(result, code="invalid_parameters", issues=[{"code": "extra_forbidden", "path": []}], count=1, private=(private_key, private_input))


@pytest.mark.parametrize("key", (-2, -1, 0, 7))
def test_validation_error_keeps_nonnegative_integer_path_tokens_only(key: int) -> None:
    private_input = "PRIVATE_INPUT_SENTINEL::wrong-count"
    with pytest.raises(ValidationError) as caught:
        _IndexedRows.model_validate({"rows": {key: {"count": private_input}}})

    (raw_issue,) = caught.value.errors(include_url=False)
    assert raw_issue["loc"] == ("rows", key, "count")
    result = wire.validation_error(caught.value, code="invalid_parameters")
    expected_path = ["rows", key, "count"] if key >= 0 else ["rows"]

    _assert_public_error(result, code="invalid_parameters", issues=[{"code": "int_type", "path": expected_path}], count=1, private=(private_input,))


@pytest.mark.parametrize("levels", (15, 16, 20))
def test_validation_error_caps_each_safe_path_at_16_tokens(levels: int) -> None:
    private_input = "PRIVATE_INPUT_SENTINEL::deep-count"
    data = {"count": private_input}
    for _ in range(levels):
        data = {"count": 0, "child": data}
    with pytest.raises(ValidationError) as caught:
        _NestedRow.model_validate(data)

    (raw_issue,) = caught.value.errors(include_url=False)
    full_path = ["child"] * levels + ["count"]
    assert raw_issue["loc"] == tuple(full_path)
    result = wire.validation_error(caught.value, code="invalid_parameters")

    _assert_public_error(result, code="invalid_parameters", issues=[{"code": "int_type", "path": full_path[:16]}], count=1, private=(private_input,))


@pytest.mark.parametrize(
    ("issue_code", "expected_code"),
    [
        pytest.param("custom_rule", "custom_rule", id="safe-word"),
        pytest.param("9.Rule-1_ok", "9.Rule-1_ok", id="safe-punctuation"),
        pytest.param("c" * 64, "c" * 64, id="safe-length-boundary"),
        pytest.param("", "validation_error", id="empty-code"),
        pytest.param("c" * 65, "validation_error", id="code-too-long"),
        pytest.param("PRIVATE_CODE_SENTINEL/secret", "validation_error", id="slash"),
        pytest.param("PRIVATE_CODE_SENTINEL secret", "validation_error", id="space"),
        pytest.param("PRIVATE_CODE_SENTINEL\nsecret", "validation_error", id="newline"),
        pytest.param("é_PRIVATE_CODE_SENTINEL", "validation_error", id="non-ascii"),
    ],
)
def test_validation_error_sanitizes_real_custom_codes_and_redacts_custom_context(issue_code: str, expected_code: str) -> None:
    private_input = "PRIVATE_INPUT_SENTINEL::custom-value"
    private_context = "PRIVATE_CONTEXT_SENTINEL::custom-context"
    with pytest.raises(ValidationError) as caught:
        _CustomIssueValue.model_validate({"value": private_input}, context={"issue_code": issue_code, "secret": private_context})

    (raw_issue,) = caught.value.errors(include_url=False)
    assert raw_issue["type"] == issue_code
    assert raw_issue["input"] == private_input
    assert raw_issue["ctx"] == {"secret": private_context, "submitted": private_input}
    assert "PRIVATE_MESSAGE_SENTINEL" in raw_issue["msg"]
    assert private_context in raw_issue["msg"]
    result = wire.validation_error(caught.value, code="invalid_parameters")
    private = (private_input, private_context, "PRIVATE_MESSAGE_SENTINEL")
    if expected_code == "validation_error" and issue_code:
        private += (issue_code,)

    _assert_public_error(result, code="invalid_parameters", issues=[{"code": expected_code, "path": ["value"]}], count=1, private=private)
