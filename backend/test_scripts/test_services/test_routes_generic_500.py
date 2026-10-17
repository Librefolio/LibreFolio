"""X-R74 (release 1.3, workstream X) — a 500 of the asset and FX routes names no error; the error is logged instead.

The defect, on HEAD 1bef78be1. R13-SEC9-3 cured ``api/v1/assets/prices.py``: a 500 there answered ``detail=str(e)``, and
an SQL error echoes its statement, naming the schema. The same answer stands at 26 sites of six route files —
``detail=str(e)`` in ``api/v1/assets/providers.py`` (7), ``crud.py`` (7), ``events.py`` (5) and ``market_data.py`` (2);
``f"…: {e!s}"`` in ``api/v1/fx/providers.py`` (4) and ``currencies.py`` (1, ``sync_rates``). The probe and the five FX
sites do not log the error either: the caller gets its text, the server's log nothing.

The cure's contract, pinned here:

1. Each of those 500s answers a fixed, non-empty detail that names no error — no word of the SQL, not the error's class,
   not an ``AssetSourceError``'s code — and logs the error with its exception on the route module's ``logger``:
   ``logger.exception(...)`` in the ``except`` block (``error``/``critical`` with ``exc_info`` count too). The shape
   ``prices.py`` and ``fx/currencies.py``'s ``delete_rates_endpoint`` already have («Internal error while …»).
2. Guards, what the cure keeps: the authored refusals answer as they do — the probe's 400 with the error's message; the
   409 ``{"error_code", "message", "params"}`` of ``assign_providers_bulk``, ``remove_providers_bulk`` and
   ``wipe_market_data``; an upsert's coded status (``_REFUSAL_STATUS``, here ``EVENT_IN_USE``); ``wipe_market_data``'s 404
   ``ASSET_NOT_FOUND`` with the error's text; the FX sync's 502 «Failed to sync rates: …».
3. One more leak, through a 400: ``merge_assets``. ``AssetCRUDService.merge_assets`` rolls back whatever stops a merge,
   logs it with its exception on the service module's ``logger`` and re-raises it as
   ``AssetSourceError(f"Merge failed: {e!s}", "MERGE_FAILED")``, which the route answers with its text: 404 for
   ``NOT_FOUND``, 400 otherwise. An SQL error during the merge so reaches the caller as a 400 «Merge failed: <the SQL>» —
   a 400, not a 500, because the service wraps the error into a code the route answers by itself. The cure keeps that
   status and ``MERGE_FAILED`` and changes the text only. ``MERGE_ASSETS`` replaces the service and cannot see this: here
   the real one runs, on a session whose ``execute`` answers the source and target lookups, then raises at the read of
   the price history, the first statement in the merge's ``try`` (``_LookupsThenFailing``).

The way in: the ROUTE BODY, called directly with its arguments as FastAPI hands them — a body model, ids, a user stand-in
with an ``id``, a session double (``_Session``). On each site's path the awaited call that fails is replaced for the test
(``monkeypatch``) by ``_Failing``, which counts its calls and raises: the route's service (a method of
``AssetSourceManager`` or ``AssetCRUDService``, or a function the route's module imported: ``configured_fx_provider``,
``sync_pairs_bulk``), or the session's ``execute`` where the route reads through the session itself
(``get_provider_assignments``, ``read_assets_bulk``, ``list_routes``, ``create_routes_bulk``, ``delete_routes_bulk``). It
raises ``RuntimeError(LEAK)``; at the three fallbacks for an ``AssetSourceError`` of a code the route does not answer by
itself (``assign_providers_bulk``, ``remove_providers_bulk``, ``upsert_events_bulk``), an ``AssetSourceError`` with
``LEAK`` as its message and ``UNKNOWN_CODE`` as its code. The module's ``logger`` is a ``_RecordingLogger``, which keeps
the exception being handled at each line. Before anything is asserted, the double is proved called (the barrier): a
route that fails earlier, in its own validation, cannot pass by accident.

What lies upstream of a site and is not under test is held still: the probe's per-user limit is off for the test
(``probe_limiter`` answers None); the FX provider routes see one public provider, ``FX_CODE`` (``_OneFxProvider`` in
place of ``FXProviderRegistry``), whatever FX plugins the checkout installs — ``list_providers`` then awaits
``configured_fx_provider`` for it, and a route through it passes ``create_routes_bulk``'s provider check and reaches the
session. The asset provider bodies are real ones for ``scheduled_investment`` without parameters, which its plugin
validates offline (as ``test_probe_rate_limit.py`` builds them).

Red on HEAD 1bef78be1: ``test_xr74_a_500_names_no_error_and_logs_it``, all 26 cases — the detail echoes the error; the
probe and the five FX cases, besides, log nothing. ``test_xr74_a_failed_merge_names_no_error_and_logs_it`` too: the 400
reads «Merge failed: SELECT secret_column FROM secret_table» (the service already logs the error). Green before and after:
``test_xr74_guard_an_authored_refusal_answers_as_before`` (7 cases).

Isolation: PURE — no database, no server, no network. The services, the session, the loggers and the two upstream
lookups are replaced for the test only (``monkeypatch``).

Reference: backend/app/api/v1/assets/providers.py, crud.py, events.py, market_data.py; backend/app/api/v1/fx/providers.py,
currencies.py; backend/app/services/assets/crud.py (``merge_assets``). The model:
``test_current_prices_bulk.py::test_sec9_3_a_failure_answers_500_without_echoing_it``.
"""

from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.api.v1.assets import crud as crud_routes
from backend.app.api.v1.assets import events as event_routes
from backend.app.api.v1.assets import market_data as market_data_routes
from backend.app.api.v1.assets import providers as asset_provider_routes
from backend.app.api.v1.fx import currencies as fx_currency_routes
from backend.app.api.v1.fx import providers as fx_provider_routes
from backend.app.schemas.assets.assets import FAAssetCreateItem, FAAssetMergeRequest, FAAssetPatchItem
from backend.app.schemas.assets.events import FAEventQueryItem, FAEventUpsert
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.fx import FXConversionRouteItem, FXDeleteRouteItem
from backend.app.schemas.provider import FAProviderAssignmentItem, FAProviderProbeRequest, ProbeOperation
from backend.app.schemas.refresh import FXSyncPairRequest
from backend.app.services.assets import crud as crud_service
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.assets.crud import AssetCRUDService
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.fx.base import FXServiceError
from backend.test_scripts.test_utils import print_section, print_success

#: What the failing call raises: an SQL error names the schema.
LEAK = "SELECT secret_column FROM secret_table"
#: The code of the ``AssetSourceError`` raised at the fallbacks: no route here answers it by itself.
UNKNOWN_CODE = "XR74_UNHANDLED_CODE"
#: The provider of the asset provider bodies: a real one, which validates them offline (no parameters given).
PROVIDER_CODE = "scheduled_investment"
#: The one public FX provider the FX provider routes see (``_OneFxProvider``).
FX_CODE = "XR74FX"
#: The signed-in user, as the routes read it: an id, nothing else.
USER = SimpleNamespace(id=7_401)
#: A past week, before today whatever today is: the range of the bodies that take one.
WEEK_START, WEEK_END = date(2025, 6, 2), date(2025, 6, 6)


# =============================================================================
# THE DOUBLES: THE FAILING CALL, THE SESSION, THE LOGGER, THE FX REGISTRY
# =============================================================================


class _Failing:
    """Stands in for the call a site's route awaits: counts its calls and raises ``error`` at each."""

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    async def __call__(self, *_args: Any, **_kwargs: Any) -> Any:
        self.calls += 1
        raise self.error


class _Session:
    """Stands in for the route's ``AsyncSession``. ``execute`` is the double it is handed: the failing one where the site
    reads through the session, elsewhere one the route must not reach before its service (it fails, saying so).
    ``rollback`` is counted and does nothing: the FX route writers roll back in their ``except``."""

    def __init__(self, execute: _Failing | None = None) -> None:
        self.execute = execute if execute is not None else _Failing(AssertionError("a statement on the session: the route was to fail in its service first"))
        self.rollbacks = 0

    async def rollback(self) -> None:
        self.rollbacks += 1


class _RecordingLogger:
    """Stands in for the route module's logger: records every line at any level, with the exception being handled."""

    def __init__(self) -> None:
        self.lines: list[tuple[str, str, dict, BaseException | None]] = []

    def __getattr__(self, level: str) -> Callable[..., None]:
        def log(message: str = "", *_args: Any, **kwargs: Any) -> None:
            self.lines.append((level, str(message), kwargs, sys.exc_info()[1]))

        return log


class _OneFxProvider:
    """Stands in for ``FXProviderRegistry`` in the FX provider routes: one provider, ``FX_CODE``, listed and public (not
    test-only), whatever FX plugins the checkout installs."""

    test_only = False

    @classmethod
    def list_providers(cls) -> list[dict[str, str]]:
        return [{"code": FX_CODE, "name": "X-R74 FX"}]

    @classmethod
    def get_plugin(cls, code: str) -> type | None:
        return cls if code == FX_CODE else None


def _probes_unlimited(monkeypatch: pytest.MonkeyPatch) -> None:
    """The probe's per-user limit off for the test: ``probe_limiter`` answers None, no count kept."""
    monkeypatch.setattr(asset_provider_routes, "probe_limiter", lambda: None)


def _one_fx_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """The FX provider routes see ``_OneFxProvider`` for ``FXProviderRegistry``."""
    monkeypatch.setattr(fx_provider_routes, "FXProviderRegistry", _OneFxProvider)


# =============================================================================
# THE SITES: EACH ROUTE, ITS ARGUMENTS, THE AWAITED CALL THAT FAILS ON ITS PATH
# =============================================================================


@dataclass(frozen=True)
class _Site:
    """A route and the awaited call that fails on its path: ``owner.name`` — a method of a service class, or a function the
    route's module imported —, or the session's ``execute`` when ``owner`` is None. ``module`` is the route's module, whose
    ``logger`` is recorded; ``prepare`` holds still what lies upstream of the call and is not under test."""

    module: ModuleType
    call: Callable[[_Session], Awaitable[Any]]
    owner: Any = None
    name: str = "execute"
    prepare: Callable[[pytest.MonkeyPatch], None] | None = None

    @property
    def failing_call(self) -> str:
        if self.owner is None:
            return "session.execute"
        return f"{getattr(self.owner, '__name__', self.owner)}.{self.name}"


def _probe_request() -> FAProviderProbeRequest:
    return FAProviderProbeRequest(provider_code=PROVIDER_CODE, identifier="xr74", identifier_type="AUTO_GENERATED", provider_params=None, operations=[ProbeOperation.CURRENT_PRICE])


def _assignment() -> FAProviderAssignmentItem:
    return FAProviderAssignmentItem(asset_id=1, provider_code=PROVIDER_CODE, identifier="xr74", identifier_type="AUTO_GENERATED", provider_params=None)


def _list_assets(session: _Session) -> Awaitable[Any]:
    """``GET /assets/query`` with every query parameter given, as FastAPI hands them: one left out would be its
    ``Query(...)`` default, not None, and fail the filters' validation before the service."""
    return crud_routes.list_assets(currency="EUR", asset_type=None, active=None, is_benchmark=None, search="X-R74", isin=None, ticker=None, cusip=None, sedol=None, figi=None, uuid=None, identifier_other=None, identifier_contains=None, session=session, current_user=USER)


def _route_item() -> FXConversionRouteItem:
    """A one-step route through ``FX_CODE``, its step as a request spells it: past ``create_routes_bulk``'s provider
    check, so it reaches the session."""
    return FXConversionRouteItem(base="EUR", quote="USD", priority=1, chain_steps=[{"from": "EUR", "to": "USD", "provider": FX_CODE}])


# api/v1/assets/providers.py
PROBE = _Site(asset_provider_routes, lambda _session: asset_provider_routes.probe_provider_config(request=_probe_request(), current_user=USER), AssetSourceManager, "probe_provider_config", prepare=_probes_unlimited)
ASSIGN = _Site(asset_provider_routes, lambda session: asset_provider_routes.assign_providers_bulk(assignments=[_assignment()], session=session, _current_user=USER), AssetSourceManager, "bulk_assign_providers")
REMOVE = _Site(asset_provider_routes, lambda session: asset_provider_routes.remove_providers_bulk(asset_ids=[1, 2], session=session, _current_user=USER), AssetSourceManager, "bulk_remove_providers")
ASSIGNMENTS = _Site(asset_provider_routes, lambda session: asset_provider_routes.get_provider_assignments(asset_ids=[1, 2], session=session, _current_user=USER))
REFRESH = _Site(asset_provider_routes, lambda session: asset_provider_routes.refresh_assets_from_provider(asset_ids=[1, 2], session=session, _current_user=USER), AssetSourceManager, "refresh_assets_from_provider")
# api/v1/assets/crud.py
CREATE_ASSETS = _Site(crud_routes, lambda session: crud_routes.create_assets_bulk(assets=[FAAssetCreateItem(display_name="X-R74 asset", currency="EUR")], session=session, _current_user=USER), AssetCRUDService, "create_assets_bulk")
PATCH_ASSETS = _Site(crud_routes, lambda session: crud_routes.patch_assets_bulk(assets=[FAAssetPatchItem(asset_id=1, display_name="X-R74 asset")], session=session, _current_user=USER), AssetCRUDService, "patch_assets_bulk")
ALL_ASSETS = _Site(crud_routes, lambda session: crud_routes.get_all_assets(session=session, current_user=USER), AssetCRUDService, "list_assets")
QUERY_ASSETS = _Site(crud_routes, _list_assets, AssetCRUDService, "list_assets")
DELETE_ASSETS = _Site(crud_routes, lambda session: crud_routes.delete_assets_bulk(asset_ids=[1, 2], session=session, _current_user=USER), AssetCRUDService, "delete_assets_bulk")
MERGE_ASSETS = _Site(crud_routes, lambda session: crud_routes.merge_assets(payload=FAAssetMergeRequest(source_asset_id=1, target_asset_id=2, dry_run=True), session=session, _current_user=USER), AssetCRUDService, "merge_assets")
READ_ASSETS = _Site(crud_routes, lambda session: crud_routes.read_assets_bulk(asset_ids=[1, 2], session=session, _current_user=USER))
# api/v1/assets/events.py
UPSERT_EVENTS = _Site(event_routes, lambda session: event_routes.upsert_events_bulk(assets=[FAEventUpsert(asset_id=1, delete_ids=[3])], session=session, _current_user=USER), AssetSourceManager, "bulk_upsert_events")
DELETE_EVENTS = _Site(event_routes, lambda session: event_routes.delete_events_bulk(asset_id=1, ids=[3, 4], session=session, current_user=USER), AssetSourceManager, "delete_events_bulk")
QUERY_EVENTS = _Site(event_routes, lambda session: event_routes.query_events_bulk(requests=[FAEventQueryItem(asset_id=1, date_range=DateRangeModel(start=WEEK_START, end=WEEK_END))], session=session, _current_user=USER), AssetSourceManager, "query_events_bulk")
EVENTS_BY_IDS = _Site(event_routes, lambda session: event_routes.get_events_by_ids(ids=[3, 4], session=session, _current_user=USER), AssetSourceManager, "get_events_by_ids")
# api/v1/assets/market_data.py
MARKET_DATA_SUMMARY = _Site(market_data_routes, lambda session: market_data_routes.market_data_summary(asset_id=1, session=session, _current_user=USER), AssetSourceManager, "wipe_market_data_for_currency_change")
WIPE = _Site(market_data_routes, lambda session: market_data_routes.wipe_market_data(asset_id=1, session=session, _current_user=USER), AssetSourceManager, "wipe_market_data_for_currency_change")
# api/v1/fx/providers.py
FX_PROVIDERS = _Site(fx_provider_routes, lambda _session: fx_provider_routes.list_providers(providers=None, _current_user=USER), fx_provider_routes, "configured_fx_provider", prepare=_one_fx_provider)
FX_ROUTES = _Site(fx_provider_routes, lambda session: fx_provider_routes.list_routes(session=session, _current_user=USER))
CREATE_FX_ROUTES = _Site(fx_provider_routes, lambda session: fx_provider_routes.create_routes_bulk(routes=[_route_item()], session=session, _current_user=USER), prepare=_one_fx_provider)
DELETE_FX_ROUTES = _Site(fx_provider_routes, lambda session: fx_provider_routes.delete_routes_bulk(routes=[FXDeleteRouteItem(base="EUR", quote="USD", priority=1)], session=session, _current_user=USER))
# api/v1/fx/currencies.py
SYNC = _Site(fx_currency_routes, lambda session: fx_currency_routes.sync_rates(body=FXSyncPairRequest(pairs=["EUR-USD"], start=WEEK_START, end=WEEK_END), session=session, _current_user=USER), fx_currency_routes, "sync_pairs_bulk")


def _install(monkeypatch: pytest.MonkeyPatch, site: _Site, failing: _Failing) -> _Session:
    """Put ``failing`` where the site's route awaits it, for the test; answer the session to hand the route."""
    if site.prepare is not None:
        site.prepare(monkeypatch)
    if site.owner is None:
        return _Session(failing)
    monkeypatch.setattr(site.owner, site.name, staticmethod(failing) if isinstance(site.owner, type) else failing)
    return _Session()


async def _outcome(make_call: Callable[[], Awaitable[Any]]) -> HTTPException | str:
    """The ``HTTPException`` the call raises — the route's answer —; otherwise what happened instead, in a line."""
    try:
        answer = await make_call()
    except HTTPException as refused:
        return refused
    except Exception as raised:
        return f"no HTTP answer: {type(raised).__name__} raised ({raised})"
    return f"no refusal: the route answered {repr(answer)[:200]}"


def _shown(outcome: HTTPException | str) -> str:
    return f"{outcome.status_code} {outcome.detail!r}" if isinstance(outcome, HTTPException) else outcome


# =============================================================================
# THE 26 SITES: A 500 NAMES NO ERROR, AND LOGS IT
# =============================================================================


def _sql_error() -> RuntimeError:
    """What a failing read raises: its text names the schema."""
    return RuntimeError(LEAK)


def _unknown_code_error() -> AssetSourceError:
    """An ``AssetSourceError`` of a code the route does not answer by itself, the same text as its message."""
    return AssetSourceError(LEAK, UNKNOWN_CODE)


def _leak_words(error: BaseException) -> list[str]:
    """What a detail naming the error would hold: words of ``LEAK``, the error's class, an ``AssetSourceError``'s code."""
    return list(dict.fromkeys(word for word in ("SELECT", "secret", "FROM", "RuntimeError", type(error).__name__, getattr(error, "error_code", None)) if word))


def _logged_with_its_exception(log: _RecordingLogger, error: BaseException) -> bool:
    """A line of ``log`` holds ``error`` with its traceback: ``exception`` while handling it, or ``error``/``critical``
    with ``exc_info`` (True while handling it, or the error itself)."""
    for level, _message, kwargs, handled in log.lines:
        exc_info = kwargs.get("exc_info")
        if level == "exception" and (handled is error or exc_info is error):
            return True
        if level in ("error", "critical") and (exc_info is error or (exc_info is True and handled is error)):
            return True
    return False


SITES_500 = [
    # api/v1/assets/providers.py
    pytest.param(PROBE, _sql_error, id="assets_providers-probe_provider_config"),
    pytest.param(ASSIGN, _unknown_code_error, id="assets_providers-assign_providers_bulk-unknown_code"),
    pytest.param(ASSIGN, _sql_error, id="assets_providers-assign_providers_bulk-exception"),
    pytest.param(REMOVE, _unknown_code_error, id="assets_providers-remove_providers_bulk-unknown_code"),
    pytest.param(REMOVE, _sql_error, id="assets_providers-remove_providers_bulk-exception"),
    pytest.param(ASSIGNMENTS, _sql_error, id="assets_providers-get_provider_assignments"),
    pytest.param(REFRESH, _sql_error, id="assets_providers-refresh_assets_from_provider"),
    # api/v1/assets/crud.py
    pytest.param(CREATE_ASSETS, _sql_error, id="assets_crud-create_assets_bulk"),
    pytest.param(PATCH_ASSETS, _sql_error, id="assets_crud-patch_assets_bulk"),
    pytest.param(ALL_ASSETS, _sql_error, id="assets_crud-get_all_assets"),
    pytest.param(QUERY_ASSETS, _sql_error, id="assets_crud-list_assets"),
    pytest.param(DELETE_ASSETS, _sql_error, id="assets_crud-delete_assets_bulk"),
    pytest.param(MERGE_ASSETS, _sql_error, id="assets_crud-merge_assets"),
    pytest.param(READ_ASSETS, _sql_error, id="assets_crud-read_assets_bulk"),
    # api/v1/assets/events.py
    pytest.param(UPSERT_EVENTS, _unknown_code_error, id="assets_events-upsert_events_bulk-unknown_code"),
    pytest.param(UPSERT_EVENTS, _sql_error, id="assets_events-upsert_events_bulk-exception"),
    pytest.param(DELETE_EVENTS, _sql_error, id="assets_events-delete_events_bulk"),
    pytest.param(QUERY_EVENTS, _sql_error, id="assets_events-query_events_bulk"),
    pytest.param(EVENTS_BY_IDS, _sql_error, id="assets_events-get_events_by_ids"),
    # api/v1/assets/market_data.py
    pytest.param(MARKET_DATA_SUMMARY, _sql_error, id="assets_market_data-market_data_summary"),
    pytest.param(WIPE, _sql_error, id="assets_market_data-wipe_market_data"),
    # api/v1/fx/providers.py
    pytest.param(FX_PROVIDERS, _sql_error, id="fx_providers-list_providers"),
    pytest.param(FX_ROUTES, _sql_error, id="fx_providers-list_routes"),
    pytest.param(CREATE_FX_ROUTES, _sql_error, id="fx_providers-create_routes_bulk"),
    pytest.param(DELETE_FX_ROUTES, _sql_error, id="fx_providers-delete_routes_bulk"),
    # api/v1/fx/currencies.py
    pytest.param(SYNC, _sql_error, id="fx_currencies-sync_rates"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("site, make_error", SITES_500)
async def test_xr74_a_500_names_no_error_and_logs_it(monkeypatch, site, make_error):
    """The awaited call on the site's path raises ``RuntimeError(LEAK)`` — at an ``AssetSourceError`` fallback, an
    ``AssetSourceError`` of ``UNKNOWN_CODE`` with ``LEAK`` as its message. The barrier first: that call was made. Then the
    route answers 500 with a non-empty detail that holds no word of the error (``SELECT``, ``secret``, ``FROM``, the
    error's class, the code), and the error is logged with its exception on the route module's ``logger``.

    Red on HEAD 1bef78be1, every case: the detail echoes the error (``detail=str(e)``; ``f"…: {e!s}"`` at the FX sites).
    The probe and the five FX cases, besides, log nothing.
    """
    error = make_error()
    print_section(f"X-R74: {site.failing_call} raises {type(error).__name__}")
    failing = _Failing(error)
    session = _install(monkeypatch, site, failing)
    log = _RecordingLogger()
    monkeypatch.setattr(site.module, "logger", log)

    outcome = await _outcome(lambda: site.call(session))

    assert failing.calls, f"barrier: {site.failing_call} was never called, the route stopped before it ({_shown(outcome)})"
    assert isinstance(outcome, HTTPException), outcome
    assert outcome.status_code == 500, f"{outcome.status_code}: {outcome.detail!r}"
    detail = str(outcome.detail)
    assert detail.strip(), f"an empty detail: {outcome.detail!r}"
    problems = []
    leaked = [word for word in _leak_words(error) if word in detail]
    if leaked:
        problems.append(f"the 500 echoes the error ({', '.join(leaked)}): {outcome.detail!r}")
    if not _logged_with_its_exception(log, error):
        problems.append(f"the error is not logged with its exception: {[(level, message) for level, message, _kwargs, _handled in log.lines]}")
    assert not problems, "; ".join(problems)
    print_success(f"500 {outcome.detail!r}; the error logged")


# =============================================================================
# THE FAILED MERGE: A 400 NAMES NO ERROR, AND THE SERVICE LOGS IT
# =============================================================================


class _LookupsThenFailing(_Failing):
    """Stands in for the session's ``execute`` on the path of the real ``AssetCRUDService.merge_assets``. Its first
    statements, the source and target lookups, are answered with ``rows``, one each and in order: a result whose
    ``scalar_one_or_none`` is the row. Every later one is counted and raises ``error`` (``_Failing``) — the first is the
    read of the price history, the first statement inside the merge's ``try``. ``calls`` counts the failing ones only:
    the barrier. Nothing else is awaited on the session before it; after it, the merge's ``except`` awaits
    ``rollback``, ``_Session``'s no-op."""

    def __init__(self, rows: list[Any], error: Exception) -> None:
        super().__init__(error)
        self.rows = list(rows)

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self.rows:
            row = self.rows.pop(0)
            return SimpleNamespace(scalar_one_or_none=lambda: row)
        return await super().__call__(*args, **kwargs)


@pytest.mark.asyncio
async def test_xr74_a_failed_merge_names_no_error_and_logs_it(monkeypatch):
    """``POST /assets/merge`` over the real ``AssetCRUDService.merge_assets``: the session finds the source (1) and the
    target (2), then its read of the price history raises ``RuntimeError(LEAK)``. The barrier first: that read was made —
    a merge refused earlier (``NOT_FOUND``, ``SAME_ASSET``, ``INVALID_PRIMARY``) cannot pass by accident. Then the route
    answers 400 — the status it gives the service's ``MERGE_FAILED``, which the cure keeps — with a non-empty detail that
    holds no word of the error, and the error is logged with its exception on the service module's ``logger``; the route
    does not log on this path.

    Red on HEAD 1bef78be1: the 400 reads «Merge failed: SELECT secret_column FROM secret_table» — the service wraps
    ``{e!s}`` into its ``AssetSourceError`` and the route answers ``detail=str(e)``. The log is already there. Green with
    the cure: «Merge failed: internal error», the status, the code and the log unchanged.
    """
    error = _sql_error()
    print_section("X-R74: the merge's read of the price history raises RuntimeError")
    # The source and the target as the merge reads them before its failing read: every identifier column absent (read
    # with ``getattr(asset, column, None)``, the target's written back with ``setattr``), no soft identifier (None, which
    # ``merge_other_identifiers`` takes).
    failing = _LookupsThenFailing([SimpleNamespace(id=1, identifier_other=None), SimpleNamespace(id=2, identifier_other=None)], error)
    session = _Session(failing)
    log = _RecordingLogger()
    monkeypatch.setattr(crud_service, "logger", log)
    payload = FAAssetMergeRequest(source_asset_id=1, target_asset_id=2, dry_run=False)

    outcome = await _outcome(lambda: crud_routes.merge_assets(payload=payload, session=session, _current_user=USER))

    assert failing.calls, f"barrier: the merge never read the price history, it stopped before ({_shown(outcome)})"
    assert isinstance(outcome, HTTPException), outcome
    assert outcome.status_code == 400, f"{outcome.status_code}: {outcome.detail!r}"
    detail = str(outcome.detail)
    assert detail.strip(), f"an empty detail: {outcome.detail!r}"
    problems = []
    leaked = [word for word in _leak_words(error) if word in detail]
    if leaked:
        problems.append(f"the 400 echoes the error ({', '.join(leaked)}): {outcome.detail!r}")
    if not _logged_with_its_exception(log, error):
        problems.append(f"the error is not logged with its exception: {[(level, message) for level, message, _kwargs, _handled in log.lines]}")
    assert not problems, "; ".join(problems)
    print_success(f"400 {outcome.detail!r}; the error logged")


# =============================================================================
# GUARDS — THE AUTHORED REFUSALS ANSWER AS BEFORE
# =============================================================================


def _probe_refusal() -> AssetSourceError:
    """``probe_provider_config``'s refusal of a provider it cannot configure."""
    return AssetSourceError(f"Unknown provider: {PROVIDER_CODE}", "UNKNOWN_PROVIDER")


def _wipe_refusal() -> AssetSourceError:
    """X-R49, as ``_reject_wipes_of_costless_split_adjustments`` raises it."""
    return AssetSourceError(
        "PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST: this change would delete 1 split(s) the provider generated, with 2 linked adjustment(s) without a purchase cost; give them a cost first",
        "PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST",
        {"asset_id": 1, "item_index": 0, "splits": [{"event_id": 41, "date": "2025-06-02", "transaction_ids": [17], "hidden_transactions_count": 1}]},
    )


def _removal_refusal() -> AssetSourceError:
    """X-R62, as ``_reject_removals_of_linked_events`` raises it."""
    return AssetSourceError(
        "PROVIDER_REMOVAL_LINKED_TRANSACTIONS: removing the provider would delete 1 event(s) it generated, linked to 2 transaction(s); unlink them first",
        "PROVIDER_REMOVAL_LINKED_TRANSACTIONS",
        {"asset_id": 2, "item_index": 1, "events": [{"event_id": 52, "date": "2025-06-03", "type": "DIVIDEND", "transaction_ids": [18], "hidden_transactions_count": 1}]},
    )


def _event_in_use() -> AssetSourceError:
    """``EVENT_IN_USE`` (409 in ``_REFUSAL_STATUS``), as ``_delete_item_events`` raises it, the item named."""
    return AssetSourceError(
        "EVENT_IN_USE: the DIVIDEND event of asset 1 on 2025-06-04 is linked to transactions",
        "EVENT_IN_USE",
        {"asset_id": 1, "item_index": 0, "events": [{"id": 3, "date": "2025-06-04", "type": "DIVIDEND", "linked_transactions": 2}]},
    )


def _asset_not_found() -> AssetSourceError:
    """``wipe_market_data_for_currency_change``'s refusal of an asset that does not exist."""
    return AssetSourceError("Asset 1 not found", "ASSET_NOT_FOUND")


def _market_data_refusal() -> AssetSourceError:
    """X-R48, as ``wipe_market_data_for_currency_change`` raises it."""
    return AssetSourceError(
        "MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST: 1 split(s) of this asset have 2 linked adjustment(s) without a purchase cost; give them a cost before deleting the asset's events",
        "MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST",
        {"splits": [{"event_id": 41, "date": "2025-06-02", "transaction_ids": [17], "hidden_transactions_count": 1}]},
    )


def _provider_failure() -> FXServiceError:
    """An ``FXServiceError`` out of the FX sync, in the text the FX service gives a provider it does not know. Today's
    ``sync_pairs_bulk`` catches its providers' failures itself (the pair answers ``failed``): what this holds is the
    route's mapping of one that reaches it, which the cure keeps."""
    return FXServiceError(f"Unknown FX provider: {FX_CODE}. Available providers: none registered")


def _its_message(error: AssetSourceError) -> str:
    return error.message


def _its_text(error: Exception) -> str:
    return str(error)


def _coded(error: AssetSourceError) -> dict[str, Any]:
    return {"error_code": error.error_code, "message": error.message, "params": error.details}


def _sync_failed(error: Exception) -> str:
    return f"Failed to sync rates: {error}"


GUARDS = [
    pytest.param(PROBE, _probe_refusal, 400, _its_message, id="assets_providers-probe_provider_config-400"),
    pytest.param(ASSIGN, _wipe_refusal, 409, _coded, id="assets_providers-assign_providers_bulk-409"),
    pytest.param(REMOVE, _removal_refusal, 409, _coded, id="assets_providers-remove_providers_bulk-409"),
    pytest.param(UPSERT_EVENTS, _event_in_use, 409, _coded, id="assets_events-upsert_events_bulk-409"),
    pytest.param(WIPE, _asset_not_found, 404, _its_text, id="assets_market_data-wipe_market_data-404"),
    pytest.param(WIPE, _market_data_refusal, 409, _coded, id="assets_market_data-wipe_market_data-409"),
    pytest.param(SYNC, _provider_failure, 502, _sync_failed, id="fx_currencies-sync_rates-502"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("site, make_error, status, answered", GUARDS)
async def test_xr74_guard_an_authored_refusal_answers_as_before(monkeypatch, site, make_error, status, answered):
    """The call on the site's path raises the refusal its service authors. The barrier first: that call was made. Then
    the route answers it as it does on HEAD 1bef78be1 — that status, that detail: the probe's 400 with the message, a 409
    ``{"error_code", "message", "params"}``, the 404 ``ASSET_NOT_FOUND`` with the error's text, the sync's 502 «Failed to
    sync rates: …». The cure changes the 500s only.

    Guard: green on HEAD 1bef78be1 too.
    """
    error = make_error()
    print_section(f"X-R74 guard: {site.failing_call} refuses with {getattr(error, 'error_code', type(error).__name__)}")
    failing = _Failing(error)
    session = _install(monkeypatch, site, failing)

    outcome = await _outcome(lambda: site.call(session))

    assert failing.calls, f"barrier: {site.failing_call} was never called, the route stopped before it ({_shown(outcome)})"
    assert isinstance(outcome, HTTPException), outcome
    assert (outcome.status_code, outcome.detail) == (status, answered(error))
    print_success(f"{outcome.status_code} {outcome.detail!r}")
