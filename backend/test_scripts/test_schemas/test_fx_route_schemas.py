"""FX route input compatibility and response-only metadata contracts.

Metadata derivation belongs to the API's ORM projection, not these DTOs.
All provider names here describe configuration; no provider is fetched.
"""

import json

import pytest
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import ValidationError

from backend.app.schemas.fx import (
    FXConversionRouteItem,
    FXConversionRouteReadItem,
    FXConversionRouteResult,
    FXConversionRoutesResponse,
    FXCreateRoutesResponse,
    FXDeleteRouteResult,
)
from backend.app.schemas.refresh import FXSyncPairResult


def _route_payload():
    return {
        "base": "RON",
        "quote": "USD",
        "priority": 1,
        "chain_steps": [
            {"from": "RON", "to": "EUR", "provider": "MOCKFX"},
            {"from": "EUR", "to": "USD", "provider": "MOCKFX"},
        ],
    }


def _response_payload(model):
    payload = {**_route_payload(), "is_chain": True, "providers_used": ["MOCKFX"]}
    if model is FXConversionRouteResult:
        payload.update(success=True, action="created")
    return payload


class TestFXRouteInputContract:
    def test_metadata_is_not_an_input_field_and_extra_ignore_is_unchanged(self):
        payload = _route_payload()
        item = FXConversionRouteItem.model_validate(payload)
        spoofed = FXConversionRouteItem.model_validate({**payload, "is_chain": False, "providers_used": ["BOGUS"], "unrelated_extra": True})

        assert item.model_dump(by_alias=True) == payload
        assert spoofed.model_dump(by_alias=True) == payload
        assert FXConversionRouteItem.model_config.get("extra") in (None, "ignore")
        schema = FXConversionRouteItem.model_json_schema()
        assert set(schema["properties"]) == {"base", "quote", "priority", "chain_steps"}
        assert set(schema["required"]) == {"base", "quote", "priority", "chain_steps"}
        assert schema.get("additionalProperties") is not False

    @pytest.mark.parametrize(
        "base,quote,steps",
        [
            pytest.param("EUR", "USD", [{"from": "EUR", "to": "USD", "provider": "MOCKFX"}], id="direct"),
            pytest.param("EUR", "USD", [{"from": "USD", "to": "EUR", "provider": "MOCKFX"}], id="inverse"),
            pytest.param(
                "RON",
                "USD",
                [
                    {"from": "RON", "to": "EUR", "provider": "MOCKFX"},
                    {"from": "EUR", "to": "USD", "provider": "MOCKFX"},
                ],
                id="repeated-provider",
            ),
            pytest.param(
                "CHF",
                "USD",
                [
                    {"from": "CHF", "to": "EUR", "provider": "SNB"},
                    {"from": "EUR", "to": "USD", "provider": "ECB"},
                ],
                id="ordered-distinct-providers",
            ),
            pytest.param("EUR", "USD", [{"from": "EUR", "to": "USD", "provider": "MANUAL"}], id="manual"),
        ],
    )
    def test_valid_configurations_keep_full_ordered_steps(self, base, quote, steps):
        payload = {"base": base, "quote": quote, "priority": 1, "chain_steps": steps}
        assert FXConversionRouteItem.model_validate(payload).model_dump(by_alias=True) == payload

    @pytest.mark.parametrize(
        "steps,error_fragment",
        [
            pytest.param([], "at least 1", id="empty"),
            pytest.param(
                [
                    {"from": "RON", "to": "EUR", "provider": "MOCKFX"},
                    {"from": "GBP", "to": "USD", "provider": "MOCKFX"},
                ],
                "Chain discontinuity",
                id="discontinuous",
            ),
            pytest.param(
                [
                    {"from": "RON", "to": "EUR", "provider": "MOCKFX"},
                    {"from": "EUR", "to": "RON", "provider": "ECB"},
                    {"from": "RON", "to": "USD", "provider": "MOCKFX"},
                ],
                "Duplicate edge",
                id="reversed-edge-different-provider",
            ),
            pytest.param(
                [{"from": "EUR", "to": "USD", "provider": "MOCKFX"}],
                "don't match pair",
                id="mismatched-endpoints",
            ),
            pytest.param(
                [
                    {"from": "RON", "to": "EUR", "provider": "MANUAL"},
                    {"from": "EUR", "to": "USD", "provider": "MOCKFX"},
                ],
                "MANUAL provider cannot",
                id="mixed-manual-chain",
            ),
        ],
    )
    def test_invalid_chain_shapes_are_rejected(self, steps, error_fragment):
        with pytest.raises(ValidationError, match=error_fragment):
            FXConversionRouteItem.model_validate({**_route_payload(), "chain_steps": steps})


@pytest.mark.parametrize("model", [FXConversionRouteReadItem, FXConversionRouteResult])
class TestFXRouteResponseContract:
    @pytest.mark.parametrize("missing", ["is_chain", "providers_used"])
    def test_metadata_fields_are_required(self, model, missing):
        payload = _response_payload(model)
        del payload[missing]
        with pytest.raises(ValidationError) as exc:
            model.model_validate(payload)
        assert any(error["loc"] == (missing,) and error["type"] == "missing" for error in exc.value.errors())

    @pytest.mark.parametrize(
        "field,value",
        [
            ("is_chain", None),
            ("is_chain", "chain"),
            ("providers_used", None),
            ("providers_used", "MOCKFX"),
            ("providers_used", [None]),
        ],
    )
    def test_metadata_requires_bool_and_string_list_shapes(self, model, field, value):
        with pytest.raises(ValidationError) as exc:
            model.model_validate({**_response_payload(model), field: value})
        assert any(error["loc"][0] == field for error in exc.value.errors())

    def test_wire_metadata_is_bool_and_list_with_lossless_step_aliases(self, model):
        item = model.model_validate(_response_payload(model))
        wire = json.loads(item.model_dump_json(by_alias=True))
        assert type(wire["is_chain"]) is bool
        assert wire["is_chain"] is True
        assert type(wire["providers_used"]) is list
        assert wire["providers_used"] == ["MOCKFX"]
        assert wire["chain_steps"] == _route_payload()["chain_steps"]
        assert item.model_dump()["chain_steps"] == [
            {"from_currency": "RON", "to_currency": "EUR", "provider": "MOCKFX"},
            {"from_currency": "EUR", "to_currency": "USD", "provider": "MOCKFX"},
        ]

    def test_json_schema_marks_required_metadata_read_only(self, model):
        for mode in ("validation", "serialization"):
            schema = model.model_json_schema(mode=mode)
            assert {"is_chain", "providers_used"} <= set(schema["required"])
            flag = schema["properties"]["is_chain"]
            membership = schema["properties"]["providers_used"]
            assert flag["type"] == "boolean"
            assert flag["readOnly"] is True
            assert "default" not in flag
            assert membership["type"] == "array"
            assert membership["items"]["type"] == "string"
            assert membership["readOnly"] is True
            assert membership["uniqueItems"] is True
            assert "default" not in membership


class TestFXRouteResponseEnvelopes:
    def test_list_and_create_envelopes_preserve_metadata(self):
        read_item = FXConversionRouteReadItem.model_validate(_response_payload(FXConversionRouteReadItem))
        result = FXConversionRouteResult.model_validate(_response_payload(FXConversionRouteResult))
        listed = FXConversionRoutesResponse(items=[read_item])
        created = FXCreateRoutesResponse(results=[result], success_count=1, error_count=0)
        assert issubclass(FXConversionRouteReadItem, FXConversionRouteItem)
        assert json.loads(listed.model_dump_json(by_alias=True))["items"] == [read_item.model_dump(by_alias=True)]
        assert json.loads(created.model_dump_json(by_alias=True))["results"] == [result.model_dump(by_alias=True)]

    def test_list_envelope_rejects_input_item_without_response_metadata(self):
        with pytest.raises(ValidationError) as exc:
            FXConversionRoutesResponse.model_validate({"items": [_route_payload()]})
        missing = {error["loc"] for error in exc.value.errors() if error["type"] == "missing"}
        assert {("items", 0, "is_chain"), ("items", 0, "providers_used")} <= missing

    def test_empty_list_stays_empty(self):
        assert FXConversionRoutesResponse(items=[]).model_dump()["items"] == []

    def test_delete_and_sync_results_do_not_gain_route_metadata(self):
        for model in (FXDeleteRouteResult, FXSyncPairResult):
            assert {"is_chain", "providers_used"}.isdisjoint(model.model_fields)
        assert "provider_used" in FXSyncPairResult.model_fields


def test_route_openapi_separates_request_and_response_metadata():
    """Mount only the router; no real app startup, client, session, or fetch."""
    from backend.app.api.v1 import fx as fx_api  # noqa: PLC0415 — router import only for this OpenAPI contract

    app = FastAPI()
    app.include_router(fx_api.router_providers)
    document = get_openapi(title="FX route contract", version="test", routes=app.routes)
    schemas = document["components"]["schemas"]
    routes = document["paths"]["/providers/routes"]

    def resolve(reference):
        return schemas[reference["$ref"].rsplit("/", 1)[-1]]

    request_array = routes["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert request_array["type"] == "array"
    request_item = resolve(request_array["items"])
    assert set(request_item["properties"]) == {"base", "quote", "priority", "chain_steps"}
    assert set(request_item["required"]) == {"base", "quote", "priority", "chain_steps"}
    assert request_item.get("additionalProperties") is not False
    step_schema = resolve(request_item["properties"]["chain_steps"]["items"])
    assert set(step_schema["properties"]) == {"from", "to", "provider"}

    for operation, status, collection in (("get", "200", "items"), ("post", "201", "results")):
        envelope = resolve(routes[operation]["responses"][status]["content"]["application/json"]["schema"])
        item = resolve(envelope["properties"][collection]["items"])
        assert {"is_chain", "providers_used"} <= set(item["required"])
        assert item["properties"]["is_chain"]["type"] == "boolean"
        assert item["properties"]["is_chain"]["readOnly"] is True
        membership = item["properties"]["providers_used"]
        assert membership["type"] == "array"
        assert membership["items"]["type"] == "string"
        assert membership["readOnly"] is True
        assert membership["uniqueItems"] is True
        output_step = resolve(item["properties"]["chain_steps"]["items"])
        assert set(output_step["properties"]) == {"from", "to", "provider"}

    validation_error = resolve(routes["post"]["responses"]["422"]["content"]["application/json"]["schema"])
    assert {"is_chain", "providers_used"}.isdisjoint(validation_error["properties"])
