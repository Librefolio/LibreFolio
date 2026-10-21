"""Z-32 (d) (workstream «Z - Sospensione e risveglio», LibreFolio 1.3.0): a provider may suggest the quote base of an
asset — how many units one market price refers to (``quote_base_quantity``, «Units per single price») — in its search
results and in the metadata operation of the provider probe. The web modal will offer it (a later lot); here, the backend.

Why. Yahoo Finance quotes London lines in pence and reports the currency ``GBp``; LibreFolio stores the asset's currency
folded to ``GBP`` (``schemas/common.py``, ``iso_currency_code``), so such a line needs ``quote_base_quantity = 100``, or
every price counts 100 times. ``utils/currency_units.py`` already lists the minor units (``MINOR_UNIT_FACTORS``: only
``GBp`` today; ``ZAc`` and ``ILA`` are out of scope). The contract pinned here, decided by the developer (point 5 revised
on 19/10: sequential, not in parallel; then: no call for a provider that keeps the base class's hook):

1. ``FAQuoteBaseSuggestion`` (``schemas/provider.py``), a ``StrictModel``: ``quantity: int``, required, at least 1 (1 is
   valid: «per unit», it overrides the asset type's default; 0, negatives, non-integers refused);
   ``quote_currency: Optional[str] = None``, the quote currency as the provider reports it, not normalized (``GBp``
   stays ``GBp``: no ISO validation, no upper-casing). An extra field is refused.
2. ``FAProviderSearchResultItem.quote_base_suggestion`` and ``ProbeMetadataResult.quote_base_suggestion``, both
   ``Optional[FAQuoteBaseSuggestion] = None``, serialized as null when absent, as the other optional fields of the two
   models are; both in the OpenAPI document, whose component has ``quantity`` required and ``minimum`` 1.
3. The search (``AssetSearchService.search``) and the streamed search the web form's autocomplete reads
   (``AssetSearchService.search_stream``): a plugin's result dict may carry ``"quote_base_suggestion"``, a dict or an
   ``FAQuoteBaseSuggestion``; it reaches the result — in the stream, each result of the ``provider_results`` event has
   the key, as plain JSON. Absent: None (null). Invalid (``quantity`` 0, negative, not a number, fractional or missing,
   an unknown key, not a dict at all): dropped (None) with a warning in the log, which names the provider or the
   result; the result, its neighbours and the rest of the search stay (no exception, no ``providers_with_errors``, no
   ``provider_error`` event).
4. ``AssetSourceProvider.suggest_quote_base(identifier, identifier_type, provider_params=None)``, a coroutine function
   next to ``fetch_asset_metadata``: the base class answers None and does no I/O.
5. The probe (``ProviderManagementOperations.probe_provider_config``, reached as ``AssetSourceManager``), when
   ``metadata`` is among the operations: once ``fetch_asset_metadata`` has answered (a patch or None), and only then,
   the probe asks ``suggest_quote_base``, with the same arguments, through ``core.call_provider``, with its own timeout
   of 5 s; the answer is ``ProbeMetadataResult.quote_base_suggestion``. Never in parallel: after a pause the core gives
   one trial call to a single caller, and a parallel suggestion could take it and make the metadata answer «paused».
   The metadata failing (any exception, a refusal for too many requests, a timeout): the suggestion is not asked. The
   suggestion failing (an exception, a refusal, a timeout): None, and ``success``, ``patch_data``, ``error``… exactly
   as without it. ``patch_data`` never carries the suggestion. Not asked without the ``metadata`` operation, nor of a
   provider that keeps the base class's ``suggest_quote_base`` (no second ``core.call_provider`` at all), nor of a test
   double that is no ``AssetSourceProvider`` and has no such method.
6. The metadata refresh never asks the suggestion and never changes ``quote_base_quantity`` for it: in
   ``test_api/test_assets_provider.py`` (QBS-A05).
7. Yahoo Finance: ``search`` adds ``{"quantity": 100, "quote_currency": "GBp"}`` (or the model) to each result whose
   currency (``_fetch_currency``) has a minor-unit factor, nothing to a ``GBP``, ``USD``, missing or empty one;
   ``suggest_quote_base`` answers ``FAQuoteBaseSuggestion(quantity=100, quote_currency="GBp")`` for a ``GBp`` line and
   None for ``GBP``, ``USD`` or no currency.
8. mockprov: ``MINOR_UNIT_QUERY = "lf-minor-unit"`` and ``MINOR_UNIT_IDENTIFIER = "MOCK_MINOR_UNIT"``; that query finds
   one ``GBp`` STOCK, ``MOCK_MINOR_UNIT``, carrying the suggestion; ``suggest_quote_base`` answers it for that
   identifier only; the other searches unchanged.

The HTTP side of 2, 3 (the plain search only), 5, 6 and 8 runs on the lane's server in
``test_api/test_assets_provider.py`` (QBS-A01…A06).

Isolation: PURE — no lane database, no server, no network. The providers of the search and probe cases are in-process
doubles without settings, handed out by ``AssetProviderRegistry.get_provider_instance`` for codes of their own
(``monkeypatch``), so ``core.configured_provider`` binds nothing and reads no row; the pauses after «too many requests»
go to a private ``Cooldowns`` on a fake clock; ``core.call_provider`` is wrapped, never replaced, to record the calls;
the Yahoo plugin's ``yf`` module is a fake (no socket); mockprov is called directly, never through
``configured_provider`` (its settings live in the database). Provider codes, queries and Yahoo symbols are unique per
test, so the process's search, metadata and currency caches answer for no other test. The OpenAPI document read here is
that of an application of the test around the real ``provider_router``: importing ``backend.app.main`` would run
``configure_logging``, which opens the lane's log file (``openapi-client-text`` in ``_backend_schemas.py`` says why that
is not PURE); ``test_assets_provider.py`` reads the document the lane's server serves.

Red before Z-32 (d) (HEAD 6510fe169), each for the reason its docstring gives: QBS-S01…S04 and S07 (no
``FAQuoteBaseSuggestion``); QBS-S05 and S06 (``FAProviderSearchResultItem`` and ``ProbeMetadataResult`` have no
``quote_base_suggestion``); QBS-S08 (no such component, no such properties in the document); QBS-R01…R03 (a search
result has no ``quote_base_suggestion``, and nothing warns about an invalid one; R01 also builds the model); QBS-R04
(it builds the model too; then a streamed result has no ``quote_base_suggestion`` key — written after the cure, which
reached the plain search only, it stays red until the stream carries the key); QBS-B01 (``AssetSourceProvider`` has no
``suggest_quote_base``); QBS-P01, P02 and P04 (no ``FAQuoteBaseSuggestion`` for their provider to answer; then the
missing field); QBS-P03 (the probe never asks a suggestion, and its metadata result has no field for one); QBS-P06 and
P07 only for that missing field. The «not asked» halves of P04, P06 and P07 are green by
construction: nothing asks a suggestion yet. QBS-Y01 and Y02 (Yahoo neither suggests in its search nor has
``suggest_quote_base``); QBS-M01, M02 and M04 (mockprov has neither the two constants nor ``suggest_quote_base``).
Green before and after, by construction — guards: QBS-P05 (no suggestion asked without the metadata operation) and
QBS-M03 (mockprov's other searches).
"""

from __future__ import annotations

import collections
import copy
import dataclasses
import inspect
import json
import logging
import os
import socket
import uuid
from collections.abc import AsyncIterator, Callable, Sequence
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from pydantic import ValidationError
from structlog.testing import capture_logs

from backend.app.db.models import AssetType, IdentifierType
from backend.app.schemas import provider as provider_schemas
from backend.app.schemas.assets.assets import FAAssetPatchItem
from backend.app.schemas.common import StrictModel
from backend.app.schemas.provider import FAProviderConfigBase, FAProviderProbeResponse, FAProviderSearchResponse, FAProviderSearchResultItem, ProbeMetadataResult, ProbeOperation
from backend.app.services.asset_source_providers.mockprov import plugin as mockprov_plugin
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.asset_source_providers.yahoo_finance import plugin as yfp
from backend.app.services.asset_source_providers.yahoo_finance.plugin import YahooFinanceProvider
from backend.app.services.assets import core
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError, AssetSourceProvider
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.assets.search import AssetSearchService
from backend.app.services.platform import provider_cooldown
from backend.app.utils.runtime.cooldown import Cooldowns
from backend.test_scripts.test_utils import print_section, print_success

#: The contract's names and values (Z-32 (d)), written here and not read from the code under test.
MODEL_NAME = "FAQuoteBaseSuggestion"
FIELD = "quote_base_suggestion"
GBP_PENCE = {"quantity": 100, "quote_currency": "GBp"}  # a London line quoted in pence, as JSON
SUGGESTION_TIMEOUT_S = 5.0  # the suggestion's own timeout in the probe
MINOR_UNIT_QUERY = "lf-minor-unit"  # mockprov's MINOR_UNIT_QUERY
MINOR_UNIT_IDENTIFIER = "MOCK_MINOR_UNIT"  # mockprov's MINOR_UNIT_IDENTIFIER

IDENTIFIER = "QBSX.L"  # the line every probe of this file asks
PARAMS = {"exchange": "LSE"}  # provider parameters, so that "the same arguments" means something
_ABSENT = object()


# =============================================================================
# THE CONTRACT'S NEW NAMES, READ AT THE CALL
# =============================================================================


def _model() -> type:
    """``FAQuoteBaseSuggestion``, read from the schema module at the call: while it is missing, the test asking it fails
    saying so, and the other tests of the file still run."""
    model = getattr(provider_schemas, MODEL_NAME, None)
    if model is None:
        pytest.fail(f"backend.app.schemas.provider has no {MODEL_NAME}: Z-32 (d)'s quote base suggestion (quantity, quote_currency)", pytrace=False)
    return model


def _suggestion(quantity: int, quote_currency: str | None = None) -> Any:
    return _model()(quantity=quantity, quote_currency=quote_currency)


def _mockprov_constant(name: str) -> str:
    """A constant of mockprov's plugin module, read at the call: while it is missing, the test asking it fails saying so."""
    value = getattr(mockprov_plugin, name, None)
    if value is None:
        pytest.fail(f"backend.app.services.asset_source_providers.mockprov.plugin has no {name}: Z-32 (d)'s minor-unit line", pytrace=False)
    return value


def _plain(value: Any) -> Any:
    """A suggestion as plain data, whether a plugin gave a dict or the model: what the contract compares."""
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else value


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _code() -> str:
    """A provider code of this test only: the registry hand-out, the pauses and the caches are keyed by it."""
    return f"qbs_{uuid.uuid4().hex[:12]}"


# =============================================================================
# PROVIDERS OF THE TEST
# =============================================================================


def _patch(**fields: Any) -> FAAssetPatchItem:
    """The metadata a provider of the test answers: a STOCK with its ticker, and ``fields``."""
    return FAAssetPatchItem(asset_id=0, asset_type=AssetType.STOCK, identifier_ticker=IDENTIFIER, **fields)


class _QuoteBaseFake(AssetSourceProvider):
    """A provider of the test that keeps the base class's ``suggest_quote_base``: no settings, no I/O.

    Its search answers ``items`` (a copy each time); its metadata ``patch`` (None included), or raises what
    ``metadata_error`` builds. ``received`` records each method's arguments, from the provider's thread.
    """

    def __init__(self, code: str, *, items: Sequence[dict] = (), patch: FAAssetPatchItem | None = None, metadata_error: Callable[[], BaseException] | None = None) -> None:
        super().__init__()
        self._code = code
        self._items = list(items)
        self._patch = patch
        self._metadata_error = metadata_error
        self.received: dict[str, list[tuple]] = collections.defaultdict(list)

    @property
    def provider_code(self) -> str:
        return self._code

    @property
    def provider_name(self) -> str:
        return f"Z-32 (d) test provider {self._code}"

    @property
    def test_cases(self) -> list[dict]:
        return []

    @property
    def test_search_query(self) -> str | None:
        return "qbs"

    def validate_params(self, params: dict | None) -> None:
        return None

    async def get_current_value(self, identifier, identifier_type, provider_params=None):
        self.received["get_current_value"].append((identifier, identifier_type, provider_params))
        raise AssetSourceError("not this file's subject (testing)", "NOT_SUPPORTED")

    async def get_history_value(self, identifier, identifier_type, provider_params, start_date, end_date):
        self.received["get_history_value"].append((identifier, identifier_type, provider_params))
        raise AssetSourceError("not this file's subject (testing)", "NOT_SUPPORTED")

    async def search(self, query: str) -> list[dict]:
        self.received["search"].append((query,))
        return copy.deepcopy(self._items)

    async def fetch_asset_metadata(self, identifier, identifier_type, provider_params=None):
        self.received["fetch_asset_metadata"].append((identifier, identifier_type, provider_params))
        if self._metadata_error is not None:
            raise self._metadata_error()
        return None if self._patch is None else self._patch.model_copy(deep=True)


class _SuggestingFake(_QuoteBaseFake):
    """The same provider, overriding ``suggest_quote_base``: it answers ``suggestion`` (None included), or raises what
    ``suggestion_error`` builds."""

    def __init__(self, code: str, *, suggestion: Any = None, suggestion_error: Callable[[], BaseException] | None = None, **kwargs: Any) -> None:
        super().__init__(code, **kwargs)
        self._suggestion = suggestion
        self._suggestion_error = suggestion_error

    async def suggest_quote_base(self, identifier, identifier_type, provider_params=None):
        self.received["suggest_quote_base"].append((identifier, identifier_type, provider_params))
        if self._suggestion_error is not None:
            raise self._suggestion_error()
        return None if self._suggestion is None else self._suggestion.model_copy()


class _PlainDouble:
    """A test double that is no ``AssetSourceProvider`` and has no ``suggest_quote_base``: the core lets it through as it
    is (no settings, no pause). Its metadata is ``patch``."""

    def __init__(self, code: str, patch: FAAssetPatchItem) -> None:
        self.provider_code = code
        self._patch = patch
        self.received: dict[str, list[tuple]] = collections.defaultdict(list)

    def validate_params(self, params: dict | None) -> None:
        return None

    def get_asset_url(self, identifier, identifier_type=None, provider_params=None) -> str | None:
        return None

    async def fetch_asset_metadata(self, identifier, identifier_type, provider_params=None):
        self.received["fetch_asset_metadata"].append((identifier, identifier_type, provider_params))
        return self._patch.model_copy(deep=True)


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


class _FakeClock:
    """A clock that moves only when a test moves it."""

    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture(autouse=True)
def private_cooldowns(monkeypatch: pytest.MonkeyPatch) -> Cooldowns:
    """Pauses on (60 s, an hour at most), kept in a private instance on a fake clock without jitter: a refusal a test
    provokes pauses no provider of the process, and none outlives the test."""
    for name in list(os.environ):
        if name.startswith("LIBREFOLIO_PROVIDER_COOLDOWN_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS", "60")
    monkeypatch.setenv("LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS", "3600")
    private = Cooldowns(60, 3600, jitter=0.0, clock=_FakeClock())
    monkeypatch.setattr(provider_cooldown, "PROVIDER_COOLDOWNS", private)
    return private


def _hand_out(monkeypatch: pytest.MonkeyPatch, *providers: Any) -> None:
    """``AssetProviderRegistry`` hands out these very objects for their codes, and its own providers for the others."""
    by_code = {provider.provider_code: provider for provider in providers}
    original = AssetProviderRegistry.get_provider_instance

    def get_provider_instance(_cls, code, **kwargs):
        return by_code[code] if code in by_code else original(code, **kwargs)

    monkeypatch.setattr(AssetProviderRegistry, "get_provider_instance", classmethod(get_provider_instance))


@dataclasses.dataclass
class _ProviderCall:
    """One ``core.call_provider`` made by the code under test."""

    timeout: float
    scope: str | None
    open_at_start: tuple[int, ...]  # the indexes of the calls not yet ended when this one was entered
    method: str | None = None  # the provider method it ran; None when the boundary refused before reaching it


def _record_provider_calls(monkeypatch: pytest.MonkeyPatch) -> list[_ProviderCall]:
    """Every ``core.call_provider`` from now on, in the order the calls are entered: the provider method each runs (the
    name of the coroutine it hands to the provider's thread), its timeout and scope, and the calls still open when it
    was entered. The calls still go through the real boundary."""
    real = core.call_provider
    calls: list[_ProviderCall] = []
    open_calls: set[int] = set()

    async def recording(provider, fn, *, timeout, scope=None):
        index = len(calls)
        call = _ProviderCall(timeout=timeout, scope=scope, open_at_start=tuple(sorted(open_calls)))
        calls.append(call)
        open_calls.add(index)

        def named():
            coroutine = fn()
            call.method = getattr(coroutine, "__name__", type(coroutine).__name__)
            return coroutine

        try:
            return await real(provider, named, timeout=timeout, scope=scope)
        finally:
            open_calls.discard(index)

    monkeypatch.setattr(core, "call_provider", recording)
    return calls


def _item(identifier: str, suggestion: Any = _ABSENT) -> dict:
    """One result as a plugin's search returns it — a GBp STOCK —, with ``quote_base_suggestion`` when given."""
    item = {"identifier": identifier, "identifier_type": IdentifierType.TICKER, "display_name": f"QBS {identifier}", "currency": "GBp", "type": "STOCK"}
    if suggestion is not _ABSENT:
        item[FIELD] = suggestion
    return item


def _by_identifier(response: FAProviderSearchResponse) -> dict[str, FAProviderSearchResultItem]:
    found: dict[str, FAProviderSearchResultItem] = {}
    for item in response.results:
        assert item.identifier not in found, f"two results {item.identifier} in one answer: {[result.identifier for result in response.results]}"
        found[item.identifier] = item
    return found


def _item_suggestion(item: FAProviderSearchResultItem) -> Any:
    """A search result's ``quote_base_suggestion``, as JSON; the test fails, saying so, while the field does not exist."""
    dumped = item.model_dump(mode="json")
    if FIELD not in dumped:
        pytest.fail(f"FAProviderSearchResultItem has no {FIELD} (Z-32 (d), point 2): its fields are {sorted(dumped)}", pytrace=False)
    return dumped[FIELD]


async def _sse(stream: AsyncIterator[str]) -> list[dict]:
    """The events of a streamed search (``AssetSearchService.search_stream``), in their order, each chunk one
    ``data: {json}`` event decoded as the web form's autocomplete decodes it (as ``test_rate_limit_results.py`` reads
    them)."""
    events: list[dict] = []
    async for chunk in stream:
        assert chunk.startswith("data: ") and chunk.endswith("\n\n"), f"not one SSE event: {chunk!r}"
        events.append(json.loads(chunk[len("data: ") :]))
    return events


def _streamed_suggestion(result: dict) -> Any:
    """A streamed result's ``quote_base_suggestion``, as the event's JSON decodes it (a dict or null); the test fails,
    saying so, while the stream does not carry the key."""
    if FIELD not in result:
        pytest.fail(f"the streamed search result has no {FIELD} (Z-32 (d), point 3, the stream): its keys are {sorted(result)}", pytrace=False)
    return result[FIELD]


def _warnings_naming(events: list[dict], records: list[logging.LogRecord], *names: str) -> list[str]:
    """The warnings of the log that name one of ``names``: structlog's (``capture_logs``) and the standard library's
    (``caplog``), whichever the code under test writes to."""
    found = [str(event) for event in events if event.get("log_level") == "warning" and any(name in str(event) for name in names)]
    found += [record.getMessage() for record in records if record.levelno == logging.WARNING and any(name in record.getMessage() for name in names)]
    return found


async def _probe(code: str, operations: list[ProbeOperation], *, provider_params: dict | None = None) -> FAProviderProbeResponse:
    config = FAProviderConfigBase(provider_code=code, identifier=IDENTIFIER, identifier_type="TICKER", provider_params=provider_params)
    return await AssetSourceManager.probe_provider_config(config, operations)


def _metadata_outcome(response: FAProviderProbeResponse) -> dict:
    """The metadata operation's own outcome, as JSON: every field but its timing and the suggestion."""
    assert response.metadata is not None, "barrier: the probe answered the metadata operation it was asked"
    dumped = response.metadata.model_dump(mode="json")
    return {name: value for name, value in dumped.items() if name not in {"execution_time_ms", FIELD}}


def _probe_suggestion(response: FAProviderProbeResponse) -> Any:
    """The metadata result's ``quote_base_suggestion``, as JSON; the test fails, saying so, while the field does not
    exist."""
    assert response.metadata is not None, "barrier: the probe answered the metadata operation it was asked"
    dumped = response.metadata.model_dump(mode="json")
    if FIELD not in dumped:
        pytest.fail(f"ProbeMetadataResult has no {FIELD} (Z-32 (d), point 2): its fields are {sorted(dumped)}", pytrace=False)
    return dumped[FIELD]


def _symbol() -> str:
    """A London symbol of this test only: ``_fetch_currency`` caches by symbol for the whole process."""
    return f"QBS{uuid.uuid4().hex[:8].upper()}.L"


def _fake_yahoo(monkeypatch: pytest.MonkeyPatch, currencies: dict[str, str | None]) -> None:
    """The Yahoo plugin's ``yf`` module replaced: ``Search`` answers one Yahoo quote per symbol of ``currencies``,
    ``Ticker`` reports each symbol's currency — in ``fast_info``, which ``_fetch_currency`` reads, and in ``info``. No
    socket is opened."""
    quotes = [{"symbol": symbol, "quoteType": "EQUITY", "longname": f"QBS {symbol}", "isYahooFinance": True} for symbol in currencies]

    def ticker(symbol: str) -> SimpleNamespace:
        currency = currencies.get(symbol)
        return SimpleNamespace(fast_info={"currency": currency}, info={"currency": currency, "symbol": symbol})

    def search(query: str) -> SimpleNamespace:
        return SimpleNamespace(quotes=quotes)

    monkeypatch.setattr(yfp, "YFINANCE_AVAILABLE", True)
    monkeypatch.setattr(yfp, "yf", SimpleNamespace(Ticker=ticker, Search=search))


def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any connection or name lookup fails the test."""

    def refuse(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("a connection was opened: the base class's suggest_quote_base must do no I/O")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


def _provider_routes_document() -> dict[str, Any]:
    """The OpenAPI document of an application of the test around the real ``provider_router`` (``/assets/provider``:
    the search and the probe included), as JSON."""
    from backend.app.api.v1.assets.providers import provider_router  # noqa: PLC0415 — only the document's test pays for importing the routes

    app = FastAPI(title="Z-32 (d) provider routes", version="1")
    app.include_router(provider_router, prefix="/api/v1/assets")
    return json.loads(json.dumps(app.openapi()))


def _component(schemas: dict[str, Any], name: str) -> tuple[str, dict[str, Any]]:
    """The component ``name``, or its ``-Output`` form (FastAPI's name when a model's two schemas differ)."""
    for key in (name, f"{name}-Output"):
        if key in schemas:
            return key, schemas[key]
    pytest.fail(f"the document has no component {name}", pytrace=False)


def _refs(schema: dict[str, Any]) -> list[str]:
    """The components a property refers to: its own ``$ref``, or those of its ``anyOf``/``oneOf``/``allOf`` members."""
    parts = [schema, *schema.get("anyOf", []), *schema.get("oneOf", []), *schema.get("allOf", [])]
    return [part["$ref"].rsplit("/", 1)[-1] for part in parts if "$ref" in part]


# =============================================================================
# QBS-S — THE SCHEMAS (points 1 and 2)
# =============================================================================


def test_qbs_s01_quantity_is_a_whole_number_of_at_least_one():
    """QBS-S01 — point 1: ``quantity`` 1 («per unit»: it overrides the asset type's default), 100 and 10 000 are kept as
    given; ``quote_currency`` may be left out.

    Red before Z-32 (d): there is no ``FAQuoteBaseSuggestion``.
    """
    model = _model()
    for quantity in (1, 100, 10_000):
        suggestion = model(quantity=quantity)
        assert suggestion.quantity == quantity and type(suggestion.quantity) is int, f"quantity {quantity} became {suggestion.quantity!r}"


_QUANTITIES_REFUSED = [
    pytest.param({"quantity": 0}, "quantity", id="zero"),
    pytest.param({"quantity": -1}, "quantity", id="minus-one"),
    pytest.param({"quantity": -100}, "quantity", id="minus-a-hundred"),
    pytest.param({"quantity": 1.5}, "quantity", id="fractional"),
    pytest.param({"quantity": "abc"}, "quantity", id="not-a-number"),
    pytest.param({"quantity": None}, "quantity", id="null"),
    pytest.param({}, "quantity", id="missing"),
]


@pytest.mark.parametrize(("fields", "at_fault"), _QUANTITIES_REFUSED)
def test_qbs_s02_a_quantity_below_one_or_not_whole_is_refused(fields, at_fault):
    """QBS-S02 — point 1: ``quantity`` is required, a whole number, at least 1: 0, -1, -100, 1.5, ``"abc"``, null and a
    missing one are refused, the error on ``quantity`` alone.

    Red before Z-32 (d): there is no ``FAQuoteBaseSuggestion``.
    """
    model = _model()
    with pytest.raises(ValidationError) as refused:
        model(quote_currency="GBp", **fields)
    assert [error["loc"] for error in refused.value.errors()] == [(at_fault,)], f"{fields}: refused for {refused.value.errors()}"


def test_qbs_s03_quote_currency_is_kept_as_the_provider_reports_it():
    """QBS-S03 — point 1: ``quote_currency`` defaults to None; ``GBp``, ``GBX`` and ``usd`` stay exactly as given — no ISO
    validation, no upper-casing (``GBp`` folded to ``GBP`` would hide the very minor unit it tells).

    Red before Z-32 (d): there is no ``FAQuoteBaseSuggestion``.
    """
    model = _model()
    assert model(quantity=100).quote_currency is None
    for reported in ("GBp", "GBX", "usd"):
        suggestion = model(quantity=100, quote_currency=reported)
        assert suggestion.quote_currency == reported, f"{reported!r} became {suggestion.quote_currency!r}: the quote currency is kept as reported"
        assert suggestion.model_dump(mode="json") == {"quantity": 100, "quote_currency": reported}


def test_qbs_s04_the_suggestion_refuses_an_extra_field():
    """QBS-S04 — point 1: a ``StrictModel``: an extra field is refused (``extra_forbidden``).

    Red before Z-32 (d): there is no ``FAQuoteBaseSuggestion``.
    """
    model = _model()
    assert issubclass(model, StrictModel), f"{MODEL_NAME} must be a StrictModel: its bases are {model.__mro__[1:]}"
    with pytest.raises(ValidationError) as refused:
        model(quantity=100, quote_currency="GBp", factor=100)
    assert [(error["loc"], error["type"]) for error in refused.value.errors()] == [(("factor",), "extra_forbidden")]


_RESULT_ITEM = {"identifier": IDENTIFIER, "identifier_type": IdentifierType.TICKER, "display_name": "QBS line", "provider_code": "qbs"}


def test_qbs_s05_a_search_result_carries_an_optional_suggestion():
    """QBS-S05 — point 2: ``FAProviderSearchResultItem.quote_base_suggestion``: None by default, serialized as null, as
    ``provider_url`` is; a dict becomes the model and serializes back to it; an invalid one is refused on its
    ``quantity``.

    Red before Z-32 (d): the item has no such field, and refuses it as an extra one.
    """
    without = FAProviderSearchResultItem(**_RESULT_ITEM).model_dump(mode="json")
    assert "provider_url" in without and without["provider_url"] is None, "barrier: the item's optional fields serialize as null"
    assert FIELD in without, f"FAProviderSearchResultItem has no {FIELD}: its fields are {sorted(without)}"
    assert without[FIELD] is None, f"absent, the suggestion must serialize as null: {without[FIELD]!r}"

    item = FAProviderSearchResultItem(**_RESULT_ITEM, quote_base_suggestion=dict(GBP_PENCE))
    assert isinstance(item.quote_base_suggestion, _model()), f"the dict must become an {MODEL_NAME}: {item.quote_base_suggestion!r}"
    assert item.model_dump(mode="json")[FIELD] == GBP_PENCE

    with pytest.raises(ValidationError) as refused:
        FAProviderSearchResultItem(**_RESULT_ITEM, quote_base_suggestion={"quantity": 0})
    assert [error["loc"] for error in refused.value.errors()] == [(FIELD, "quantity")]


def test_qbs_s06_a_probe_metadata_result_carries_an_optional_suggestion():
    """QBS-S06 — point 2: ``ProbeMetadataResult.quote_base_suggestion``: None by default, serialized as null, as
    ``patch_data`` is; a dict becomes the model and serializes back to it.

    Red before Z-32 (d): the result has no such field, and refuses it as an extra one.
    """
    without = ProbeMetadataResult(success=True, execution_time_ms=0).model_dump(mode="json")
    assert "patch_data" in without and without["patch_data"] is None, "barrier: the result's optional fields serialize as null"
    assert FIELD in without, f"ProbeMetadataResult has no {FIELD}: its fields are {sorted(without)}"
    assert without[FIELD] is None, f"absent, the suggestion must serialize as null: {without[FIELD]!r}"

    result = ProbeMetadataResult(success=True, execution_time_ms=0, quote_base_suggestion=dict(GBP_PENCE))
    assert isinstance(result.quote_base_suggestion, _model()), f"the dict must become an {MODEL_NAME}: {result.quote_base_suggestion!r}"
    assert result.model_dump(mode="json")[FIELD] == GBP_PENCE


def test_qbs_s07_the_json_schema_of_the_suggestion():
    """QBS-S07 — points 1 and 2: the model's JSON schema: ``quantity`` an integer with ``minimum`` 1, the only required
    property; ``quote_currency`` a property; no additional property.

    Red before Z-32 (d): there is no ``FAQuoteBaseSuggestion``.
    """
    schema = _model().model_json_schema()
    assert schema.get("required") == ["quantity"], f"required: {schema.get('required')}"
    quantity = schema["properties"]["quantity"]
    assert (quantity.get("type"), quantity.get("minimum")) == ("integer", 1), f"quantity: {quantity}"
    assert "quote_currency" in schema["properties"], f"properties: {sorted(schema['properties'])}"
    assert schema.get("additionalProperties") is False, "a StrictModel's schema admits no additional property"


def test_qbs_s08_the_openapi_document_of_the_provider_routes():
    """QBS-S08 — point 2: in the OpenAPI document of the real provider routes, ``FAProviderSearchResultItem`` and
    ``ProbeMetadataResult`` have an optional, nullable ``quote_base_suggestion`` referring to the
    ``FAQuoteBaseSuggestion`` component, whose ``quantity`` is a required integer with ``minimum`` 1 and whose
    ``quote_currency`` is optional.

    Red before Z-32 (d): neither model has the property, and there is no such component.
    """
    print_section("QBS-S08: the OpenAPI document of the provider routes")
    schemas = _provider_routes_document()["components"]["schemas"]
    referenced: set[str] = set()
    for parent in ("FAProviderSearchResultItem", "ProbeMetadataResult"):
        key, component = _component(schemas, parent)
        properties = component.get("properties", {})
        assert FIELD in properties, f"{key} documents no {FIELD}: its properties are {sorted(properties)}"
        prop = properties[FIELD]
        assert FIELD not in component.get("required", []), f"{key}.{FIELD} must be optional: required {component.get('required')}"
        assert {"type": "null"} in prop.get("anyOf", []), f"{key}.{FIELD} must be nullable: {prop}"
        refs = _refs(prop)
        assert len(refs) == 1 and refs[0].split("-")[0] == MODEL_NAME, f"{key}.{FIELD} must refer to {MODEL_NAME}: {prop}"
        referenced.add(refs[0])
    for key in sorted(referenced):
        component = schemas[key]
        quantity = component.get("properties", {}).get("quantity", {})
        assert "quantity" in component.get("required", []), f"{key}: quantity must be required: {component.get('required')}"
        assert (quantity.get("type"), quantity.get("minimum")) == ("integer", 1), f"{key}.quantity: {quantity}"
        assert "quote_currency" not in component.get("required", []), f"{key}: quote_currency must be optional"
    print_success(f"both answers refer to {sorted(referenced)}: quantity required, minimum 1")


# =============================================================================
# QBS-R — THE SEARCH (point 3)
# =============================================================================


@pytest.mark.asyncio
async def test_qbs_r01_a_plugin_suggestion_reaches_its_search_result(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    """QBS-R01 — point 3: one search of a provider of the test whose results carry a dict suggestion, the model itself,
    a ``{"quantity": 1}`` and none: each result gets its own (100 GBp; 100 GBp; 1 without a currency; None), the provider
    answers without error, and no warning names it.

    Red before Z-32 (d): there is no ``FAQuoteBaseSuggestion``, and a search result has no ``quote_base_suggestion``.
    """
    print_section("QBS-R01: a plugin's suggestion reaches its result")
    code = _code()
    items = [_item("QBS-DICT", dict(GBP_PENCE)), _item("QBS-MODEL", _suggestion(100, "GBp")), _item("QBS-PER-UNIT", {"quantity": 1}), _item("QBS-WITHOUT")]
    _hand_out(monkeypatch, _QuoteBaseFake(code, items=items))
    caplog.set_level(logging.WARNING)

    with capture_logs() as events:
        response = await AssetSearchService.search(_unique("qbs-valid"), provider_codes=[code])

    assert (response.providers_queried, response.providers_with_errors) == ([code], []), f"barrier: the provider answered: {response.providers_queried}, errors {response.providers_with_errors}"
    results = _by_identifier(response)
    assert set(results) == {"QBS-DICT", "QBS-MODEL", "QBS-PER-UNIT", "QBS-WITHOUT"}, f"results: {sorted(results)}"
    got = {identifier: _item_suggestion(result) for identifier, result in results.items()}
    assert got == {"QBS-DICT": GBP_PENCE, "QBS-MODEL": GBP_PENCE, "QBS-PER-UNIT": {"quantity": 1, "quote_currency": None}, "QBS-WITHOUT": None}, f"suggestions: {got}"
    assert not _warnings_naming(events, caplog.records, code), "valid suggestions, or none, are nothing to warn about"
    print_success("dict, model, 1 and none: each on its own result")


_INVALID_SUGGESTIONS = [
    pytest.param({"quantity": 0, "quote_currency": "GBp"}, id="quantity-zero"),
    pytest.param({"quantity": -100, "quote_currency": "GBp"}, id="quantity-negative"),
    pytest.param({"quantity": "abc"}, id="quantity-not-a-number"),
    pytest.param({"quantity": 1.5}, id="quantity-fractional"),
    pytest.param({"quote_currency": "GBp"}, id="quantity-missing"),
    pytest.param({"quantity": 100, "quote_currency": "GBp", "factor": 100}, id="an-unknown-key"),
    pytest.param("100", id="a-string"),
    pytest.param(100, id="a-number"),
    pytest.param(["quantity", 100], id="a-list"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", _INVALID_SUGGESTIONS)
async def test_qbs_r02_an_invalid_suggestion_is_dropped_with_a_warning_and_its_result_stays(invalid: Any, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    """QBS-R02 — point 3: a result whose suggestion is invalid keeps everything but the suggestion (None); its neighbours
    — one with a valid suggestion, one without — are untouched; the search raises nothing and lists no provider with
    errors; a warning names the provider or the result.

    Red before Z-32 (d): a search result has no ``quote_base_suggestion``, and nothing warns.
    """
    code = _code()
    items = [_item("QBS-INVALID", invalid), _item("QBS-VALID", dict(GBP_PENCE)), _item("QBS-WITHOUT")]
    _hand_out(monkeypatch, _QuoteBaseFake(code, items=items))
    caplog.set_level(logging.WARNING)

    with capture_logs() as events:
        response = await AssetSearchService.search(_unique("qbs-invalid"), provider_codes=[code])

    assert (response.providers_queried, response.providers_with_errors, response.providers_not_configured) == ([code], [], []), f"an invalid suggestion must not make the provider fail: errors {response.providers_with_errors}"
    results = _by_identifier(response)
    assert set(results) == {"QBS-INVALID", "QBS-VALID", "QBS-WITHOUT"}, f"the result with the invalid suggestion, or a neighbour, was lost: {sorted(results)}"
    got = {identifier: _item_suggestion(result) for identifier, result in results.items()}
    assert got == {"QBS-INVALID": None, "QBS-VALID": GBP_PENCE, "QBS-WITHOUT": None}, f"{invalid!r} must be dropped, the neighbours untouched: {got}"
    assert results["QBS-INVALID"].display_name == "QBS QBS-INVALID", f"the result keeps the rest of what the plugin said: {results['QBS-INVALID']}"
    assert _warnings_naming(events, caplog.records, code, "QBS-INVALID"), f"no warning names the provider ({code}) or the result (QBS-INVALID): {events}"


@pytest.mark.asyncio
async def test_qbs_r03_a_search_answered_from_the_query_cache_keeps_the_suggestion(monkeypatch: pytest.MonkeyPatch):
    """QBS-R03 — point 3: the same query twice: the second is answered from the core's query cache (the provider asked
    once) and still carries the suggestion.

    Red before Z-32 (d): a search result has no ``quote_base_suggestion``.
    """
    code = _code()
    provider = _QuoteBaseFake(code, items=[_item("QBS-CACHED", dict(GBP_PENCE))])
    _hand_out(monkeypatch, provider)
    query = _unique("qbs-cached")

    fresh = await AssetSearchService.search(query, provider_codes=[code])
    cached = await AssetSearchService.search(query, provider_codes=[code])

    assert provider.received["search"] == [(query,)], f"barrier: the second search must come from the query cache: {provider.received['search']}"
    for label, response in (("fresh", fresh), ("cached", cached)):
        results = _by_identifier(response)
        assert set(results) == {"QBS-CACHED"}, f"{label}: {sorted(results)}"
        assert _item_suggestion(results["QBS-CACHED"]) == GBP_PENCE, f"the {label} answer lost the suggestion"


@pytest.mark.asyncio
async def test_qbs_r04_the_streamed_search_carries_the_suggestion(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    """QBS-R04 — point 3, the stream: one ``AssetSearchService.search_stream`` — the search the web form's autocomplete
    reads (``GET /assets/provider/search/stream``) — of a provider of the test whose results carry a dict suggestion,
    the model itself, a ``{"quantity": 1}``, none and an invalid one (``quantity`` 0): its ``provider_results`` event
    has one result per item, each with the key ``quote_base_suggestion``, as plain JSON — the values the plain search
    gives (QBS-R01, R02): 100 GBp; 100 GBp; 1 without a currency; null; null, the invalid one dropped with the same
    warning, which names the provider or the result. Every other key of a result stays as the stream built it, no
    ``provider_error`` event, and ``done`` lists the provider among those queried, not among those with errors.

    Red before the stream carries it: the streamed results have no ``quote_base_suggestion`` key (the plain search has
    it since the cure).
    """
    print_section("QBS-R04: the streamed search carries the suggestion")
    code = _code()
    items = [_item("QBS-DICT", dict(GBP_PENCE)), _item("QBS-MODEL", _suggestion(100, "GBp")), _item("QBS-PER-UNIT", {"quantity": 1}), _item("QBS-WITHOUT"), _item("QBS-INVALID", {"quantity": 0, "quote_currency": "GBp"})]
    _hand_out(monkeypatch, _QuoteBaseFake(code, items=items))
    caplog.set_level(logging.WARNING)

    with capture_logs() as events:
        streamed = await _sse(AssetSearchService.search_stream(_unique("qbs-stream"), provider_codes=[code]))

    errors = [event for event in streamed if event.get("event") == "provider_error" and event.get("provider_code") == code]
    assert not errors, f"an invalid suggestion must not make the provider fail: {errors}"
    assert streamed and streamed[-1].get("event") == "done", f"barrier: the stream ends on its done event: {streamed}"
    done = streamed[-1]
    assert (done["providers_queried"], done["providers_with_errors"], done["total_results"]) == ([code], [], len(items)), f"the provider queried, not in error, every result counted: {done}"
    (answer,) = [event for event in streamed if event.get("event") == "provider_results" and event.get("provider_code") == code]
    results = {result.get("identifier"): result for result in answer["results"]}
    assert len(results) == len(answer["results"]) and set(results) == {"QBS-DICT", "QBS-MODEL", "QBS-PER-UNIT", "QBS-WITHOUT", "QBS-INVALID"}, f"one result per item: {[result.get('identifier') for result in answer['results']]}"
    for identifier, result in results.items():
        before = {"identifier": identifier, "identifier_type": "TICKER", "display_name": f"QBS {identifier}", "provider_code": code, "currency": "GBp", "asset_type": "STOCK", "provider_url": None, "provider_params": None, "via_web": False}
        assert {key: result.get(key, "(missing)") for key in before} == before, f"barrier: every other key of the streamed result as before: {result}"
    got = {identifier: _streamed_suggestion(result) for identifier, result in results.items()}
    assert got == {"QBS-DICT": GBP_PENCE, "QBS-MODEL": GBP_PENCE, "QBS-PER-UNIT": {"quantity": 1, "quote_currency": None}, "QBS-WITHOUT": None, "QBS-INVALID": None}, f"suggestions: {got}"
    assert _warnings_naming(events, caplog.records, code, "QBS-INVALID"), f"no warning names the provider ({code}) or the result (QBS-INVALID): {events}"
    assert not _warnings_naming(events, caplog.records, "QBS-DICT", "QBS-MODEL", "QBS-PER-UNIT", "QBS-WITHOUT"), "valid suggestions, or none, are nothing to warn about"
    print_success("dict, model, 1, none and an invalid one: each streamed with its own, as the plain search gives them")


# =============================================================================
# QBS-B — THE PLUGIN HOOK (point 4)
# =============================================================================


@pytest.mark.asyncio
async def test_qbs_b01_the_base_class_suggests_nothing(monkeypatch: pytest.MonkeyPatch):
    """QBS-B01 — point 4: ``AssetSourceProvider.suggest_quote_base(self, identifier, identifier_type,
    provider_params=None)`` is a coroutine function; a provider that keeps it answers None — for a ticker or an ISIN,
    with parameters or without — and opens no connection.

    Red before Z-32 (d): ``AssetSourceProvider`` has no ``suggest_quote_base``.
    """
    hook = vars(AssetSourceProvider).get("suggest_quote_base")
    if hook is None:
        pytest.fail("AssetSourceProvider has no suggest_quote_base: Z-32 (d)'s plugin hook (point 4)", pytrace=False)
    assert inspect.iscoroutinefunction(hook), "suggest_quote_base must be a coroutine function, as every provider call is"
    parameters = list(inspect.signature(hook).parameters.values())
    assert [parameter.name for parameter in parameters] == ["self", "identifier", "identifier_type", "provider_params"], f"signature: {inspect.signature(hook)}"
    assert parameters[-1].default is None, "provider_params defaults to None"

    provider = _QuoteBaseFake(_code())
    _no_network(monkeypatch)
    answers = [
        await provider.suggest_quote_base(IDENTIFIER, IdentifierType.TICKER),
        await provider.suggest_quote_base(IDENTIFIER, IdentifierType.TICKER, dict(PARAMS)),
        await provider.suggest_quote_base("GB00QBS00001", IdentifierType.ISIN, None),
    ]
    assert answers == [None, None, None], f"the base class must suggest nothing: {answers}"


# =============================================================================
# QBS-P — THE PROBE (point 5)
# =============================================================================


_PATCH_VARIANTS = [
    pytest.param({}, id="a-patch-without-a-quote-base"),
    pytest.param({"quote_base_quantity": 10}, id="a-patch-with-its-own-quote-base"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("own_fields", _PATCH_VARIANTS)
async def test_qbs_p01_the_probe_asks_the_suggestion_after_the_metadata_answered(own_fields: dict, monkeypatch: pytest.MonkeyPatch):
    """QBS-P01 — point 5: with ``metadata`` asked, a provider that overrides ``suggest_quote_base`` (100 GBp): the
    metadata result carries the suggestion, and its own outcome — ``success``, ``patch_data``, ``error``… — is exactly
    the outcome of the same provider without the hook; ``patch_data``'s ``quote_base_quantity`` stays the patch's own
    (none, or 10), never the suggestion's 100. Two ``core.call_provider``: ``fetch_asset_metadata``, then
    ``suggest_quote_base``, entered only once the metadata call had ended, with a timeout of 5 s and the arguments the
    metadata received.

    Red before Z-32 (d): there is no ``FAQuoteBaseSuggestion``; the probe never asks a suggestion, and its metadata
    result has no ``quote_base_suggestion``.
    """
    print_section("QBS-P01: the suggestion, after the metadata, 5 s")
    patch = _patch(**own_fields)
    baseline = _QuoteBaseFake(_code(), patch=patch)
    subject = _SuggestingFake(_code(), patch=patch, suggestion=_suggestion(100, "GBp"))
    _hand_out(monkeypatch, baseline, subject)
    without = await _probe(baseline.provider_code, [ProbeOperation.METADATA], provider_params=dict(PARAMS))
    calls = _record_provider_calls(monkeypatch)

    response = await _probe(subject.provider_code, [ProbeOperation.METADATA], provider_params=dict(PARAMS))

    expected = _metadata_outcome(without)
    assert (expected["success"], expected["patch_data"]) == (True, patch.model_dump(mode="json")), f"barrier: without the hook the probe answers the provider's metadata: {expected}"
    assert _probe_suggestion(response) == GBP_PENCE, "the provider's suggestion must reach the metadata result"
    assert _metadata_outcome(response) == expected, "the suggestion changed the metadata's own outcome"
    assert response.metadata.patch_data.get("quote_base_quantity") == own_fields.get("quote_base_quantity"), f"patch_data carries the suggestion: {response.metadata.patch_data}"
    assert [call.method for call in calls] == ["fetch_asset_metadata", "suggest_quote_base"], f"the calls through core.call_provider: {calls}"
    assert calls[1].open_at_start == (), "the suggestion was asked while the metadata call was still open: in parallel, not after it"
    assert calls[1].timeout == SUGGESTION_TIMEOUT_S, f"the suggestion's timeout must be {SUGGESTION_TIMEOUT_S} s: {calls[1].timeout}"
    assert subject.received["suggest_quote_base"] == subject.received["fetch_asset_metadata"] == [(IDENTIFIER, IdentifierType.TICKER, PARAMS)], f"the suggestion must receive the metadata's arguments: {dict(subject.received)}"
    print_success("metadata, then the suggestion (5 s), patch_data untouched")


@pytest.mark.asyncio
async def test_qbs_p02_metadata_answered_none_the_suggestion_is_still_asked(monkeypatch: pytest.MonkeyPatch):
    """QBS-P02 — point 5: a provider answering no metadata (None) has answered: the suggestion is asked after it and
    reaches the result, whose own outcome stays the one without the hook (no success, no patch, the same error).

    Red before Z-32 (d): there is no ``FAQuoteBaseSuggestion``; the probe never asks a suggestion.
    """
    baseline = _QuoteBaseFake(_code(), patch=None)
    subject = _SuggestingFake(_code(), patch=None, suggestion=_suggestion(100, "GBp"))
    _hand_out(monkeypatch, baseline, subject)
    without = await _probe(baseline.provider_code, [ProbeOperation.METADATA])
    calls = _record_provider_calls(monkeypatch)

    response = await _probe(subject.provider_code, [ProbeOperation.METADATA])

    expected = _metadata_outcome(without)
    assert (expected["success"], expected["patch_data"]) == (False, None), f"barrier: no metadata is no success: {expected}"
    assert _probe_suggestion(response) == GBP_PENCE, "None is an answer: the suggestion must be asked and reach the result"
    assert _metadata_outcome(response) == expected, "the suggestion changed the metadata's own outcome"
    assert [call.method for call in calls] == ["fetch_asset_metadata", "suggest_quote_base"], f"the calls through core.call_provider: {calls}"
    assert calls[1].open_at_start == (), "the suggestion was asked while the metadata call was still open"


_SUGGESTION_FAILURES = [
    pytest.param(lambda: RuntimeError("the suggestion broke (testing)"), id="an-exception"),
    pytest.param(lambda: AssetSourceError("the suggestion failed (testing)", "FETCH_ERROR"), id="a-provider-error"),
    pytest.param(lambda: AssetRateLimitedError("the suggestion was refused for too many requests (testing)", retry_after=30.0), id="a-refusal-for-too-many-requests"),
    pytest.param(lambda: TimeoutError("simulated: the suggestion's 5 s ran out (testing)"), id="a-timeout"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", _SUGGESTION_FAILURES)
async def test_qbs_p03_a_failing_suggestion_is_none_and_changes_nothing(failure: Callable[[], BaseException], monkeypatch: pytest.MonkeyPatch):
    """QBS-P03 — point 5: the suggestion fails — an exception, a provider error, a refusal for too many requests, a
    timeout (the error ``asyncio.wait_for`` raises, raised by the provider: no clock is waited on) —: the suggestion is
    None and the metadata's own outcome is exactly the one without the hook (success, the same patch, no error).

    Red before Z-32 (d): the probe never asks a suggestion, and its metadata result has no ``quote_base_suggestion``.
    """
    patch = _patch()
    baseline = _QuoteBaseFake(_code(), patch=patch)
    subject = _SuggestingFake(_code(), patch=patch, suggestion_error=failure)
    _hand_out(monkeypatch, baseline, subject)
    without = await _probe(baseline.provider_code, [ProbeOperation.METADATA])
    calls = _record_provider_calls(monkeypatch)

    response = await _probe(subject.provider_code, [ProbeOperation.METADATA])

    expected = _metadata_outcome(without)
    assert expected["success"] is True, f"barrier: without the hook the metadata succeeds: {expected}"
    assert _probe_suggestion(response) is None, "a failed suggestion must be None"
    assert _metadata_outcome(response) == expected, "the suggestion's failure changed the metadata's own outcome"
    assert [call.method for call in calls] == ["fetch_asset_metadata", "suggest_quote_base"], f"barrier: the suggestion was asked, and failed: {calls}"


_METADATA_FAILURES = [
    pytest.param(lambda: RuntimeError("the metadata broke (testing)"), id="an-exception"),
    pytest.param(lambda: AssetSourceError("the metadata failed (testing)", "FETCH_ERROR"), id="a-provider-error"),
    pytest.param(lambda: AssetRateLimitedError("the metadata was refused for too many requests (testing)", retry_after=30.0), id="a-refusal-for-too-many-requests"),
    pytest.param(lambda: TimeoutError("simulated: the metadata's 15 s ran out (testing)"), id="a-timeout"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", _METADATA_FAILURES)
async def test_qbs_p04_a_failing_metadata_asks_no_suggestion(failure: Callable[[], BaseException], monkeypatch: pytest.MonkeyPatch):
    """QBS-P04 — point 5: the metadata fails — an exception, a provider error, a refusal for too many requests, a
    timeout —: the suggestion is not asked (one ``core.call_provider`` only, the provider's hook never reached), it is
    None, and the metadata's outcome is exactly the one without the hook.

    Red before Z-32 (d): there is no ``FAQuoteBaseSuggestion``, and the metadata result has no
    ``quote_base_suggestion``. The «not asked» half is green by construction: nothing asks a suggestion yet.
    """
    baseline = _QuoteBaseFake(_code(), metadata_error=failure)
    subject = _SuggestingFake(_code(), metadata_error=failure, suggestion=_suggestion(100, "GBp"))
    _hand_out(monkeypatch, baseline, subject)
    without = await _probe(baseline.provider_code, [ProbeOperation.METADATA])
    calls = _record_provider_calls(monkeypatch)

    response = await _probe(subject.provider_code, [ProbeOperation.METADATA])

    assert [call.method for call in calls] == ["fetch_asset_metadata"], f"after a failed metadata call the suggestion must not be asked, not even reach core.call_provider: {calls}"
    assert "suggest_quote_base" not in subject.received, "the provider's suggest_quote_base was called"
    expected = _metadata_outcome(without)
    assert expected["success"] is False, f"barrier: the metadata failed: {expected}"
    assert _metadata_outcome(response) == expected, "the probe of a provider with the hook failed differently"
    assert _probe_suggestion(response) is None, "no metadata, no suggestion"


@pytest.mark.asyncio
async def test_qbs_p05_without_the_metadata_operation_no_suggestion_is_asked(monkeypatch: pytest.MonkeyPatch):
    """QBS-P05 — point 5: a probe of the current price and the history only, of a provider that overrides the hook:
    neither its metadata nor its suggestion is asked, and there is no metadata result.

    Green before Z-32 (d), by construction: nothing asks a suggestion yet. A guard: the cure must not ask one outside
    the metadata operation.
    """
    subject = _SuggestingFake(_code(), patch=_patch(), suggestion=None)
    _hand_out(monkeypatch, subject)
    calls = _record_provider_calls(monkeypatch)

    response = await _probe(subject.provider_code, [ProbeOperation.CURRENT_PRICE, ProbeOperation.HISTORY])

    assert response.metadata is None, "metadata was not asked"
    assert {"get_current_value", "get_history_value"} <= set(subject.received), f"barrier: the two operations asked reached the provider: {sorted(subject.received)}"
    assert not {"fetch_asset_metadata", "suggest_quote_base"} & set(subject.received), f"asked without the metadata operation: {sorted(subject.received)}"
    assert "suggest_quote_base" not in [call.method for call in calls], f"the calls through core.call_provider: {calls}"


@pytest.mark.asyncio
async def test_qbs_p06_a_provider_keeping_the_base_class_hook_is_asked_nothing_more(monkeypatch: pytest.MonkeyPatch):
    """QBS-P06 — point 5: a provider that keeps the base class's ``suggest_quote_base``: one ``core.call_provider`` only,
    the metadata's; the suggestion None; the metadata answered as usual.

    Red before Z-32 (d): the metadata result has no ``quote_base_suggestion``. The «one call» half is green by
    construction: nothing asks a suggestion yet.
    """
    patch = _patch()
    provider = _QuoteBaseFake(_code(), patch=patch)
    assert "suggest_quote_base" not in vars(_QuoteBaseFake), "barrier: this provider keeps the base class's hook"
    _hand_out(monkeypatch, provider)
    calls = _record_provider_calls(monkeypatch)

    response = await _probe(provider.provider_code, [ProbeOperation.METADATA])

    assert [call.method for call in calls] == ["fetch_asset_metadata"], f"a provider keeping the base class's hook must not be asked a suggestion: {calls}"
    outcome = _metadata_outcome(response)
    assert (outcome["success"], outcome["patch_data"]) == (True, patch.model_dump(mode="json")), f"barrier: the metadata answered: {outcome}"
    assert _probe_suggestion(response) is None


@pytest.mark.asyncio
async def test_qbs_p07_a_double_without_the_hook_is_asked_nothing_more(monkeypatch: pytest.MonkeyPatch):
    """QBS-P07 — point 5: a test double that is no ``AssetSourceProvider`` and has no ``suggest_quote_base``: one
    ``core.call_provider`` only, the metadata's; the suggestion None; nothing raised for the missing method.

    Red before Z-32 (d): the metadata result has no ``quote_base_suggestion``. The «one call» half is green by
    construction.
    """
    patch = _patch()
    double = _PlainDouble(_code(), patch)
    assert not isinstance(double, AssetSourceProvider) and not hasattr(double, "suggest_quote_base"), "barrier: a double without the hook"
    _hand_out(monkeypatch, double)
    calls = _record_provider_calls(monkeypatch)

    response = await _probe(double.provider_code, [ProbeOperation.METADATA])

    assert [call.method for call in calls] == ["fetch_asset_metadata"], f"a double without the hook must not be asked a suggestion: {calls}"
    outcome = _metadata_outcome(response)
    assert (outcome["success"], outcome["patch_data"]) == (True, patch.model_dump(mode="json")), f"barrier: the metadata answered: {outcome}"
    assert _probe_suggestion(response) is None


# =============================================================================
# QBS-Y — YAHOO FINANCE (point 7)
# =============================================================================


@pytest.mark.asyncio
async def test_qbs_y01_yahoo_search_suggests_100_for_a_pence_line_only(monkeypatch: pytest.MonkeyPatch):
    """QBS-Y01 — point 7: Yahoo's search over five London quotes reported in ``GBp``, ``GBP``, ``USD``, no currency and
    an empty one: the ``GBp`` result carries ``{"quantity": 100, "quote_currency": "GBp"}`` (a dict or the model); the
    other four no suggestion. No network: ``yf`` is a fake.

    Red before Z-32 (d): the search's results carry no suggestion.
    """
    print_section("QBS-Y01: Yahoo search, a pence line")
    pence, pounds, dollars, unknown, blank = (_symbol() for _ in range(5))
    currencies = {pence: "GBp", pounds: "GBP", dollars: "USD", unknown: None, blank: ""}
    _fake_yahoo(monkeypatch, currencies)

    results = await YahooFinanceProvider().search("qbs london")

    by_symbol = {result["identifier"]: result for result in results}
    assert set(by_symbol) == set(currencies), f"barrier: one result per Yahoo quote: {sorted(by_symbol)}"
    assert _plain(by_symbol[pence].get(FIELD)) == GBP_PENCE, f"the GBp line must suggest 100 GBp: {by_symbol[pence]}"
    others = {currencies[symbol]: by_symbol[symbol].get(FIELD) for symbol in (pounds, dollars, unknown, blank)}
    assert others == dict.fromkeys(others), f"only a minor unit is a reason to suggest: {others}"
    print_success("GBp → 100 GBp; GBP, USD, none and empty → nothing")


@pytest.mark.asyncio
async def test_qbs_y02_yahoo_suggest_quote_base_reads_the_reported_currency(monkeypatch: pytest.MonkeyPatch):
    """QBS-Y02 — point 7: ``YahooFinanceProvider.suggest_quote_base``: a line reported in ``GBp`` answers
    ``FAQuoteBaseSuggestion(quantity=100, quote_currency="GBp")``; ``GBP``, ``USD`` and no currency answer None. No
    network: ``yf`` is a fake.

    Red before Z-32 (d): there is no ``FAQuoteBaseSuggestion``, and the provider has no ``suggest_quote_base``.
    """
    model = _model()
    pence, pounds, dollars, unknown = (_symbol() for _ in range(4))
    _fake_yahoo(monkeypatch, {pence: "GBp", pounds: "GBP", dollars: "USD", unknown: None})
    provider = YahooFinanceProvider()
    if not hasattr(provider, "suggest_quote_base"):
        pytest.fail("YahooFinanceProvider has no suggest_quote_base (Z-32 (d), point 7)", pytrace=False)

    answer = await provider.suggest_quote_base(pence, IdentifierType.TICKER, None)
    others = {currency: await provider.suggest_quote_base(symbol, IdentifierType.TICKER, None) for symbol, currency in ((pounds, "GBP"), (dollars, "USD"), (unknown, None))}

    assert isinstance(answer, model), f"a GBp line must answer an {MODEL_NAME}: {answer!r}"
    assert answer.model_dump(mode="json") == GBP_PENCE, f"a GBp line: {answer!r}"
    assert others == {"GBP": None, "USD": None, None: None}, f"only a minor unit is a reason to suggest: {others}"


# =============================================================================
# QBS-M — MOCKPROV (point 8)
# =============================================================================


def test_qbs_m01_mockprov_names_its_minor_unit_line():
    """QBS-M01 — point 8: mockprov's module has ``MINOR_UNIT_QUERY = "lf-minor-unit"`` and ``MINOR_UNIT_IDENTIFIER =
    "MOCK_MINOR_UNIT"``.

    Red before Z-32 (d): neither constant exists.
    """
    assert (_mockprov_constant("MINOR_UNIT_QUERY"), _mockprov_constant("MINOR_UNIT_IDENTIFIER")) == (MINOR_UNIT_QUERY, MINOR_UNIT_IDENTIFIER)


@pytest.mark.asyncio
async def test_qbs_m02_mockprov_minor_unit_search_finds_one_pence_line():
    """QBS-M02 — point 8: mockprov's search for ``MINOR_UNIT_QUERY`` answers one result: ``MOCK_MINOR_UNIT``, a TICKER, a
    ``GBp`` STOCK with a display name, carrying ``{"quantity": 100, "quote_currency": "GBp"}`` (a dict or the model).

    Red before Z-32 (d): there is no ``MINOR_UNIT_QUERY`` (and ``lf-minor-unit`` answers ``MOCK_LF-MINOR-UNIT``, in USD,
    without a suggestion).
    """
    query, identifier = _mockprov_constant("MINOR_UNIT_QUERY"), _mockprov_constant("MINOR_UNIT_IDENTIFIER")

    results = await MockProvider().search(query)

    assert len(results) == 1, f"one result for {query}: {results}"
    (result,) = results
    assert (result.get("identifier"), result.get("identifier_type"), result.get("currency"), result.get("type")) == (identifier, IdentifierType.TICKER, "GBp", "STOCK"), f"the minor-unit line: {result}"
    assert isinstance(result.get("display_name"), str) and result["display_name"].strip(), f"a display name: {result}"
    assert _plain(result.get(FIELD)) == GBP_PENCE, f"the minor-unit line must suggest 100 GBp: {result}"


@pytest.mark.asyncio
async def test_qbs_m03_mockprov_other_searches_are_unchanged():
    """QBS-M03 — point 8: any other query (its own ``TEST``, a query of this test) answers as before — one
    ``MOCK_<QUERY>`` in USD, type MOCK — with no suggestion.

    Green before Z-32 (d), by construction. A guard: the cure adds a line, it changes no other.
    """
    provider = MockProvider()
    for query in ("TEST", _unique("qbs-other")):
        results = await provider.search(query)
        assert len(results) == 1, f"one result for {query}: {results}"
        (result,) = results
        expected = {"identifier": f"MOCK_{query.upper()}", "identifier_type": IdentifierType.TICKER, "display_name": f"Mock Asset: {query}", "currency": "USD", "type": "MOCK"}
        assert {key: value for key, value in result.items() if key != FIELD} == expected, f"{query}: {result}"
        assert result.get(FIELD) is None, f"{query} must suggest nothing: {result}"


@pytest.mark.asyncio
async def test_qbs_m04_mockprov_suggests_for_its_minor_unit_line_only():
    """QBS-M04 — point 8: mockprov's ``suggest_quote_base`` answers ``FAQuoteBaseSuggestion(quantity=100,
    quote_currency="GBp")`` for ``MINOR_UNIT_IDENTIFIER``, None for any other identifier (``MOCK``, ``MOCK_REFRESH``,
    one of this test).

    Red before Z-32 (d): there is no ``FAQuoteBaseSuggestion``, no ``MINOR_UNIT_IDENTIFIER``, and mockprov has no
    ``suggest_quote_base``.
    """
    model = _model()
    identifier = _mockprov_constant("MINOR_UNIT_IDENTIFIER")
    provider = MockProvider()
    if not hasattr(provider, "suggest_quote_base"):
        pytest.fail("MockProvider has no suggest_quote_base (Z-32 (d), point 8)", pytrace=False)

    answer = await provider.suggest_quote_base(identifier, IdentifierType.TICKER, None)
    others = {other: await provider.suggest_quote_base(other, IdentifierType.TICKER, None) for other in ("MOCK", "MOCK_REFRESH", _unique("MOCK_QBS"))}

    assert isinstance(answer, model), f"{identifier} must answer an {MODEL_NAME}: {answer!r}"
    assert answer.model_dump(mode="json") == GBP_PENCE, f"{identifier}: {answer!r}"
    assert others == dict.fromkeys(others), f"any other identifier must answer None: {others}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
