"""Project 76, lot C1 — the «bulk current-price read» contract of asset providers (pure: no DB, no server, no network).

A provider that can price many assets in one call says so; the core can then ask once instead of once per asset. This
file pins the contract, before any caller uses it:

1. ``FACurrentValueRequest`` (``schemas/prices.py``) is one item of such a call: ``key`` (non-empty), ``identifier``,
   ``identifier_type``, ``provider_params`` (``{}`` by default, a dict of its own per instance); a field it does not
   declare is refused.
2. ``AssetSourceProvider`` declares ``supports_bulk_current`` (False) and ``bulk_current_max_items`` (100); its
   ``get_current_values_bulk`` raises ``AssetSourceError`` ``NOT_SUPPORTED`` unless a plugin overrides it.
3. The declarations are checked when the class is defined (``TypeError``): ``supports_bulk_current`` a bool;
   ``bulk_current_max_items`` an int >= 1 (a bool, 1.5, 0 and -1 refused); ``supports_bulk_current = True`` only on a
   class that overrides ``get_current_values_bulk``. A well-formed declaration is accepted (guard).
4. ``MockProvider`` supports it (max 50 items): one call answers every item by its key, each answer equal to what
   ``get_current_value`` gives for the same inputs; ``mock_bulk_calls()`` records the keys of each call, in order.
5. An item carrying ``BULK_OMIT_PARAM`` is absent from the answer (no answer for that asset); the others stay.
6. ``INVALID_TICKER_12345`` answers an ``AssetSourceError`` ``NOT_FOUND`` under its key; the other items still answer.
7. An item carrying ``RATE_LIMITED_PARAM`` makes the WHOLE call raise ``AssetRateLimitedError`` (``retry_after`` 30.0);
   the call is recorded before anything else, so a refused call is recorded too.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from pydantic import ValidationError

from backend.app.db.models import IdentifierType
from backend.app.schemas import FACurrentValueRequest
from backend.app.schemas.prices import FACurrentValue
from backend.app.services.asset_source_providers.mockprov.plugin import (
    BULK_OMIT_PARAM,
    RATE_LIMITED_PARAM,
    MockProvider,
    mock_bulk_calls,
    reset_mock_bulk_calls,
)
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError, AssetSourceProvider
from backend.test_scripts.test_utils import print_section, print_success


@pytest.fixture(autouse=True)
def _fresh_mock_counter() -> Iterator[None]:
    reset_mock_bulk_calls()
    yield
    reset_mock_bulk_calls()


def _req(key: str, identifier: str = "AAA", **params) -> FACurrentValueRequest:
    return FACurrentValueRequest(key=key, identifier=identifier, identifier_type=IdentifierType.TICKER, provider_params=params)


def _define(**attrs) -> type:
    """A minimal concrete provider (only the abstract members) with the given class attributes; raises at definition."""

    async def get_current_value(self, identifier, identifier_type, provider_params):
        raise NotImplementedError

    async def get_history_value(self, identifier, identifier_type, provider_params, start_date, end_date):
        raise NotImplementedError

    body = {
        "provider_code": property(lambda self: "c1_test"),
        "provider_name": property(lambda self: "C1 test"),
        "test_cases": property(lambda self: []),
        "test_search_query": property(lambda self: None),
        "validate_params": lambda self, params: None,
        "get_current_value": get_current_value,
        "get_history_value": get_history_value,
    }
    body.update(attrs)
    return type("C1Provider", (AssetSourceProvider,), body)


async def _bulk_override(self, items):
    return {}


@pytest.mark.asyncio
async def test_c1_default_is_not_bulk_and_refuses_the_call():
    print_section("C1: base default")
    provider = _define()()
    assert provider.supports_bulk_current is False
    assert provider.bulk_current_max_items == 100
    with pytest.raises(AssetSourceError) as exc:
        await provider.get_current_values_bulk([_req("a")])
    assert exc.value.error_code == "NOT_SUPPORTED"
    print_success("default: not bulk, max 100, NOT_SUPPORTED")


@pytest.mark.parametrize(
    "attrs",
    [
        pytest.param({"supports_bulk_current": True}, id="true-without-override"),
        pytest.param({"supports_bulk_current": True, "get_current_values_bulk": _bulk_override, "bulk_current_max_items": 0}, id="max-0"),
        pytest.param({"supports_bulk_current": True, "get_current_values_bulk": _bulk_override, "bulk_current_max_items": -1}, id="max-minus-1"),
        pytest.param({"supports_bulk_current": True, "get_current_values_bulk": _bulk_override, "bulk_current_max_items": True}, id="max-bool"),
        pytest.param({"supports_bulk_current": True, "get_current_values_bulk": _bulk_override, "bulk_current_max_items": 1.5}, id="max-float"),
        pytest.param({"supports_bulk_current": "yes", "get_current_values_bulk": _bulk_override}, id="flag-not-bool"),
    ],
)
def test_c1_class_definition_guards_refuse(attrs):
    with pytest.raises(TypeError):
        _define(**attrs)
    print_success("refused at class definition")


def test_c1_class_definition_accepts_a_well_formed_declaration():
    cls = _define(supports_bulk_current=True, get_current_values_bulk=_bulk_override, bulk_current_max_items=1)
    assert cls.supports_bulk_current is True
    assert cls.bulk_current_max_items == 1
    print_success("True + override + max 1 accepted")


def test_c1_request_refuses_extra_fields_and_an_empty_key():
    with pytest.raises(ValidationError):
        FACurrentValueRequest(key="a", identifier="X", identifier_type=IdentifierType.TICKER, surprise=1)
    with pytest.raises(ValidationError):
        FACurrentValueRequest(key="", identifier="X", identifier_type=IdentifierType.TICKER)
    print_success("extra field and empty key refused")


def test_c1_request_provider_params_default_is_not_shared():
    a = FACurrentValueRequest(key="a", identifier="X", identifier_type=IdentifierType.TICKER)
    b = FACurrentValueRequest(key="b", identifier="X", identifier_type=IdentifierType.TICKER)
    assert a.provider_params == {} and b.provider_params == {}
    a.provider_params["x"] = 1
    assert b.provider_params == {}
    print_success("provider_params defaults to a dict of its own")


@pytest.mark.asyncio
async def test_c1_mock_answers_every_item_like_get_current_value_and_records_the_call():
    assert MockProvider.supports_bulk_current is True
    assert MockProvider.bulk_current_max_items == 50
    provider = MockProvider()
    items = [_req("k1", "AAA"), _req("k2", "BBB"), _req("k3", "CCC")]
    answer = await provider.get_current_values_bulk(items)
    assert mock_bulk_calls() == [("k1", "k2", "k3")]
    assert set(answer) == {"k1", "k2", "k3"}
    for item in items:
        single = await provider.get_current_value(item.identifier, item.identifier_type, item.provider_params)
        assert answer[item.key] == single
    print_success("3 items, one recorded call, each equal to get_current_value")


@pytest.mark.asyncio
async def test_c1_mock_omits_an_item_on_command():
    answer = await MockProvider().get_current_values_bulk([_req("keep"), _req("gone", **{BULK_OMIT_PARAM: True}), _req("keep2")])
    assert "gone" not in answer
    assert {"keep", "keep2"} <= set(answer)
    print_success("omitted key absent, others present")


@pytest.mark.asyncio
async def test_c1_mock_answers_an_invalid_ticker_with_its_own_error():
    answer = await MockProvider().get_current_values_bulk([_req("ok"), _req("bad", "INVALID_TICKER_12345"), _req("ok2")])
    assert isinstance(answer["bad"], AssetSourceError)
    assert answer["bad"].error_code == "NOT_FOUND"
    assert isinstance(answer["ok"], FACurrentValue)
    assert isinstance(answer["ok2"], FACurrentValue)
    print_success("NOT_FOUND under its key, others answered")


@pytest.mark.asyncio
async def test_c1_mock_rate_limited_item_refuses_the_whole_call_and_is_recorded():
    items = [_req("a"), _req("b", **{RATE_LIMITED_PARAM: 30}), _req("c")]
    with pytest.raises(AssetRateLimitedError) as exc:
        await MockProvider().get_current_values_bulk(items)
    assert exc.value.retry_after == 30.0
    assert mock_bulk_calls() == [("a", "b", "c")]
    print_success("whole call refused, retry_after 30.0, call recorded")
