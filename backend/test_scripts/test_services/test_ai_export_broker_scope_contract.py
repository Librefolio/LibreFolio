"""78 L10b — the contract of the nine broker readers: an empty scope is refused, never read as «every broker».

WHAT. Every AI Export reader that hands the scope's brokers to a service goes through `scope_broker_ids`. On an empty
`BuildScope.broker_scope` each one raises `NoBrokerScopeError` (`reason_code` `no_owned_brokers`) before it calls the
service, so no service is ever called with `broker_ids=None` or `[]`.

WHY. The services below the AI Export read `None`, and even an empty list, as «every broker the user can access»
(`PortfolioReportQuery.broker_ids`, `data_access.py`, `lots_analysis_service.py`, Risk with `None`). Since 78 L10b an
empty scope means **no broker** (the user owns none and the request named none, D13). A reader that passed it through
would hand the user the brokers only shared with them: the opposite of D13. `prepare_request` keeps an empty scope away
from these readers (`test_ai_export_owned_broker_scope.py`, OS-07); this contract is the guard behind that gate.

THE READERS, one case each:
1. asset report (`load_asset_report`), 2. asset lots (`load_asset_lots`), 3. FX exposure report
(`_load_exposure_report`), 4. drawdown history start (`_execute_drawdown`), 5. risk scope (`export_risk_scope`),
6. portfolio report (`load_portfolio_report`), 7. transacted assets (`discover_transacted_asset_ids`), 8. portfolio
lots (`load_lots_results`), 9. income timeline (`_load_income_records`).

A tenth case reads the source: no module of the AI Export components turns the scope back into `None` (`... if
scope.broker_scope else None`, `or None`), the pattern every reader had before L10b.

Isolation: PURE. A stub context runs each loader on a sentinel session; every service the readers could reach is
replaced by a spy that records the call. No database, no server, no network.

Runs in ``./dev.py test services ai-export``; alone:
``pipenv run python -m pytest -q backend/test_scripts/test_services/test_ai_export_broker_scope_contract.py``.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from datetime import date
from pathlib import Path

import pytest

from backend.app.config import PROJECT_ROOT
from backend.app.schemas.risk.scope import PortfolioRiskScope
from backend.app.schemas.risk.vocabulary import RiskScopeKind
from backend.app.services.ai_export.components import asset_resources, drawdown_context, fx_core, portfolio_income
from backend.app.services.ai_export.components.broker_scope import REASON_NO_OWNED_BROKERS, NoBrokerScopeError, scope_broker_ids
from backend.app.services.ai_export.components.payloads import portfolio_broker
from backend.app.services.ai_export.components.types import BrokerScopeSource, BuildScope, DetailLevel, Domain, ResourceKey

START = date(2026, 1, 1)
END = date(2026, 3, 31)
SESSION = object()  # a sentinel: no reader may reach a query with it


def _empty_scope(domain: Domain) -> BuildScope:
    """A scope with no broker: the user owns none and the request named none."""
    extra: dict = {}
    if domain is Domain.ASSET:
        extra["asset_id"] = 7
    elif domain is Domain.FX:
        extra.update(base_currency="USD", quote_currency="EUR")
    return BuildScope(
        request_id=f"l10b-contract-{domain.value}",
        user_id=1,
        domain=domain,
        detail_level=DetailLevel.STANDARD,
        period_start=START,
        period_end=END,
        target_currency="EUR",
        broker_scope=(),
        broker_scope_source=BrokerScopeSource.OWNED,
        owned_broker_ids=(),
        **extra,
    )


class _Context:
    """The part of `BuildContext` the readers use: the scope, and `db_resource` running the loader at once."""

    def __init__(self, scope: BuildScope) -> None:
        self.scope = scope

    async def db_resource(self, key, loader: Callable[[object], Awaitable[object]]):  # noqa: ARG002
        return await loader(SESSION)


@pytest.fixture
def service_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, object]]:
    """Every service a reader could reach, as a spy: the list of (service, broker_ids) it was called with."""
    calls: list[tuple[str, object]] = []

    async def report(self, *args, **kwargs):  # noqa: ARG001
        query = kwargs.get("query", args[-1] if args else None)
        calls.append(("PortfolioService.get_report", getattr(query, "broker_ids", "?")))

    async def lots(self, *args, **kwargs):  # noqa: ARG001
        calls.append(("LotsAnalysisService.get_lots_analysis", kwargs.get("broker_ids", "?")))

    async def sentinels(*args, **kwargs):  # noqa: ARG001
        calls.append(("resolve_date_sentinels", kwargs.get("broker_ids", "?")))

    async def risk(self, *args, **kwargs):  # noqa: ARG001
        calls.append(("RiskService.execute", getattr(kwargs.get("request"), "scope", "?")))

    async def transacted(session, broker_ids, as_of):  # noqa: ARG001
        calls.append(("default_transaction_asset_ids_loader", broker_ids))
        return set()

    async def accessible(session, user_id):  # noqa: ARG001
        return [1, 2, 3]  # the accessible brokers: what an empty scope must never widen to

    from backend.app.services.portfolio.lots_analysis_service import LotsAnalysisService  # noqa: PLC0415
    from backend.app.services.portfolio.portfolio_service import PortfolioService  # noqa: PLC0415
    from backend.app.services.risk.service import RiskService  # noqa: PLC0415

    monkeypatch.setattr(PortfolioService, "get_report", report)
    monkeypatch.setattr(LotsAnalysisService, "get_lots_analysis", lots)
    monkeypatch.setattr(RiskService, "execute", risk)
    monkeypatch.setattr(drawdown_context, "resolve_date_sentinels", sentinels)
    monkeypatch.setattr(portfolio_broker, "default_transaction_asset_ids_loader", transacted)
    monkeypatch.setattr(portfolio_income, "resolve_accessible_broker_ids", accessible)
    return calls


async def _asset_report() -> object:
    return await asset_resources.load_asset_report(_empty_scope(Domain.ASSET))(SESSION)


async def _asset_lots() -> object:
    return await asset_resources.load_asset_lots(_empty_scope(Domain.ASSET))(SESSION)


async def _fx_exposure_report() -> object:
    return await fx_core._load_exposure_report(_Context(_empty_scope(Domain.FX)))


async def _drawdown_history_start() -> object:
    scope = _empty_scope(Domain.PORTFOLIO)
    # The Risk scope as a caller would hand it; its brokers are not the point: the start bound reads the build scope's.
    risk_scope = PortfolioRiskScope(kind=RiskScopeKind.PORTFOLIO, broker_ids=[1], apply_ownership_share=True)
    key = ResourceKey("l10b.contract.drawdown", object)
    return await drawdown_context._execute_drawdown(_Context(scope), scope, resource_key=key, risk_scope=risk_scope, target_currency="EUR")


async def _risk_scope() -> object:
    return portfolio_broker.export_risk_scope(_empty_scope(Domain.PORTFOLIO))


async def _portfolio_report() -> object:
    scope = _empty_scope(Domain.PORTFOLIO)
    return await portfolio_broker.load_portfolio_report(_Context(scope), scope, ResourceKey("l10b.contract.report", object))


async def _transacted_assets() -> object:
    return await portfolio_broker.discover_transacted_asset_ids(SESSION, _empty_scope(Domain.PORTFOLIO))


async def _portfolio_lots() -> object:
    scope = _empty_scope(Domain.PORTFOLIO)
    return await portfolio_broker.load_lots_results(_Context(scope), scope, ResourceKey("l10b.contract.lots", object))


async def _income_timeline() -> object:
    scope = _empty_scope(Domain.PORTFOLIO)
    return await portfolio_income._load_income_records(_Context(scope), scope)


_READERS: tuple[tuple[str, Callable[[], Awaitable[object]]], ...] = (
    ("asset report", _asset_report),
    ("asset lots", _asset_lots),
    ("fx exposure report", _fx_exposure_report),
    ("drawdown history start", _drawdown_history_start),
    ("risk scope", _risk_scope),
    ("portfolio report", _portfolio_report),
    ("transacted assets", _transacted_assets),
    ("portfolio lots", _portfolio_lots),
    ("income timeline", _income_timeline),
)


@pytest.mark.asyncio
@pytest.mark.parametrize(("reader", "call"), _READERS, ids=[reader for reader, _call in _READERS])
async def test_bc01_an_empty_scope_is_refused_and_reaches_no_service(service_calls, reader, call):
    with pytest.raises(NoBrokerScopeError) as raised:
        await call()

    assert raised.value.reason_code == REASON_NO_OWNED_BROKERS
    assert raised.value.reader == reader
    assert service_calls == [], f"{reader} called a service with an empty scope: {service_calls}"


def test_bc02_a_scope_with_brokers_passes_them_through():
    scope = BuildScope(
        request_id="l10b-contract-brokers",
        user_id=1,
        domain=Domain.PORTFOLIO,
        detail_level=DetailLevel.STANDARD,
        period_start=START,
        period_end=END,
        target_currency="EUR",
        broker_scope=(3, 1),
    )

    assert scope_broker_ids(scope, reader="any") == [1, 3]


_COMPONENTS_DIR = Path(PROJECT_ROOT) / "backend" / "app" / "services" / "ai_export" / "components"
_WIDENING = re.compile(r"broker_scope\)?\s+if\s+\S*broker_scope\s+else\s+None|broker_scope\)?\s+or\s+None|broker_ids\s+or\s+None")


def test_bc03_no_component_turns_the_scope_back_into_none():
    """The pre-L10b pattern, `list(scope.broker_scope) if scope.broker_scope else None` or `... or None`, is gone."""
    offenders = [f"{path.relative_to(_COMPONENTS_DIR)}:{number}: {line.strip()}" for path in sorted(_COMPONENTS_DIR.rglob("*.py")) for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1) if _WIDENING.search(line) and not line.lstrip().startswith("#")]
    assert offenders == [], "\n".join(offenders)
