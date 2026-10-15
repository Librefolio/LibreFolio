"""Authenticated, uncached, read-only planner source: Portfolio, Broker, Asset, saved-price, WAC and saved-FX facts for planner copy actions."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, Broker, BrokerUserAccess, PriceHistory, UserRole
from backend.app.schemas.portfolio import (
    PlannerSourceSection,
    PortfolioPlannerCurrentDistribution,
    PortfolioPlannerSourceFxQuote,
    PortfolioPlannerSourceIssue,
    PortfolioPlannerSourceProvenance,
    PortfolioPlannerSourceRequest,
    PortfolioPlannerSourceResponse,
    PortfolioPlannerSourceSnapshot,
    PortfolioPlannerWacContext,
)
from backend.app.services.pac_allocator.source.classifications import build_planner_classifications
from backend.app.services.pac_allocator.source.distribution import build_planner_current_distribution
from backend.app.services.pac_allocator.source.entities import build_planner_assets, build_planner_brokers, build_planner_cash_balances, build_planner_holdings, build_planner_prices, observed_currencies_by_broker
from backend.app.services.pac_allocator.source.fx_quotes import build_planner_fx_quotes
from backend.app.services.pac_allocator.source.keys import BROKER_PROVENANCE_ID, ENGINE_PROVENANCE_ID, FX_PROVENANCE_ID, MARKET_PROVENANCE_ID, PORTFOLIO_PROVENANCE_ID, WAC_PROVENANCE_ID
from backend.app.services.pac_allocator.source.loaders import load_cash_by_broker, load_holding_rows, load_latest_prices
from backend.app.services.pac_allocator.source.wac import build_planner_wac_contexts
from backend.app.utils.datetime_utils import utcnow

_PLANNER_SOURCE_REVISION = "1.0.0"


class PortfolioPlannerSourceAccessError(PermissionError):
    """The complete selected Broker scope is not available to the caller."""


class PortfolioPlannerSourceBrokerNotFoundError(PortfolioPlannerSourceAccessError):
    """Compatibility error type; selected Broker gaps now use the generic access error."""


class PortfolioPlannerSourceAssetNotFoundError(LookupError):
    """At least one explicitly selected Asset does not exist."""


def _build_planner_provenance(
    requested_sections: set[PlannerSourceSection],
    *,
    captured_at,
) -> list[PortfolioPlannerSourceProvenance]:
    records = [
        PortfolioPlannerSourceProvenance(
            provenance_id=PORTFOLIO_PROVENANCE_ID,
            kind="domain_copy",
            domain="portfolio",
            source_ref="transactions+broker_user_access",
            source_label=None,
            captured_at=captured_at,
        )
    ]
    if requested_sections & {"assets", "prices", "classifications"}:
        records.append(
            PortfolioPlannerSourceProvenance(
                provenance_id=MARKET_PROVENANCE_ID,
                kind="domain_copy",
                domain="market_data",
                source_ref="assets+price_history",
                source_label=None,
                captured_at=captured_at,
            )
        )
    if "brokers" in requested_sections:
        records.append(
            PortfolioPlannerSourceProvenance(
                provenance_id=BROKER_PROVENANCE_ID,
                kind="domain_copy",
                domain="broker",
                source_ref="brokers+broker_user_access+transactions",
                source_label=None,
                captured_at=captured_at,
            )
        )
    if requested_sections & {"fx_quotes", "wac_contexts"}:
        records.append(
            PortfolioPlannerSourceProvenance(
                provenance_id=FX_PROVENANCE_ID,
                kind="domain_copy",
                domain="fx",
                source_ref="fx_rates",
                source_label=None,
                captured_at=captured_at,
            )
        )
    if "wac_contexts" in requested_sections:
        records.append(
            PortfolioPlannerSourceProvenance(
                provenance_id=WAC_PROVENANCE_ID,
                kind="domain_copy",
                domain="wac",
                source_ref="portfolio_service.compute_wac_iterative",
                source_label=None,
                captured_at=captured_at,
            )
        )
    if "current_distribution" in requested_sections:
        records.append(
            PortfolioPlannerSourceProvenance(
                provenance_id=ENGINE_PROVENANCE_ID,
                kind="domain_copy",
                domain="portfolio",
                source_ref="portfolio_engine.PortfolioCalculationEngine",
                source_label=None,
                captured_at=captured_at,
            )
        )
    return records


async def _load_selected_owner_accesses(
    session: AsyncSession,
    *,
    user_id: int,
    broker_ids: list[int],
) -> tuple[list, dict[int, tuple[BrokerUserAccess, Broker]]]:
    requested_ids = set(broker_ids)
    access_rows = (
        await session.execute(
            select(BrokerUserAccess, Broker)
            .join(Broker, Broker.id == BrokerUserAccess.broker_id)
            .where(
                Broker.id.in_(requested_ids),
                BrokerUserAccess.user_id == user_id,
                BrokerUserAccess.role == UserRole.OWNER,
            )
            .order_by(Broker.id)
        )
    ).all()
    accesses: dict[int, tuple[BrokerUserAccess, Broker]] = {}
    for access, broker in access_rows:
        if broker.id is None:
            raise RuntimeError("Persisted broker is missing its id")
        accesses[broker.id] = (access, broker)
    if set(accesses) != requested_ids:
        raise PortfolioPlannerSourceAccessError("Selected Broker scope is unavailable")
    return access_rows, accesses


async def _load_planner_assets(
    session: AsyncSession,
    *,
    requested_asset_ids: list[int] | None,
    held_asset_ids: set[int],
    include_catalog: bool,
) -> list[Asset]:
    if requested_asset_ids is not None:
        if not requested_asset_ids:
            return []
        rows = list((await session.execute(select(Asset).where(Asset.id.in_(requested_asset_ids)).order_by(Asset.display_name, Asset.id))).scalars())
        if {asset.id for asset in rows} != set(requested_asset_ids):
            raise PortfolioPlannerSourceAssetNotFoundError("Selected Asset scope contains a missing Asset")
        return rows

    if not include_catalog:
        return []
    all_assets = list((await session.execute(select(Asset).order_by(Asset.display_name, Asset.id))).scalars())
    return [asset for asset in all_assets if asset.id is not None and (asset.active or asset.id in held_asset_ids)]


async def build_portfolio_planner_source(
    session: AsyncSession,
    *,
    user_id: int,
    request: PortfolioPlannerSourceRequest,
) -> PortfolioPlannerSourceResponse:
    """Build one authenticated, read-only, uncached planner source snapshot."""
    captured_at = utcnow()
    requested_sections = set(request.requested_sections)
    access_rows, accesses = await _load_selected_owner_accesses(
        session,
        user_id=user_id,
        broker_ids=request.broker_ids,
    )

    # Broker authorization is complete before the first private ledger read.
    asset_sections = {
        "assets",
        "holdings",
        "prices",
        "classifications",
        "wac_contexts",
    }
    all_holding_rows = (
        await load_holding_rows(
            session,
            accesses=accesses,
            as_of_date=request.as_of,
        )
        if requested_sections & asset_sections
        else []
    )
    held_asset_ids = {asset_id for _broker_id, asset_id, _custody_quantity in all_holding_rows if asset_id is not None}
    candidate_assets = await _load_planner_assets(
        session,
        requested_asset_ids=request.asset_ids,
        held_asset_ids=held_asset_ids,
        include_catalog=bool(requested_sections & asset_sections),
    )
    selected_asset_ids = {asset.id for asset in candidate_assets if asset.id is not None}
    selected_holding_rows = [row for row in all_holding_rows if row[1] is not None and row[1] in selected_asset_ids]
    assets_by_id = {asset.id: asset for asset in candidate_assets if asset.id is not None}

    cash_by_broker = (
        await load_cash_by_broker(
            session,
            accesses=accesses,
            as_of_date=request.as_of,
        )
        if requested_sections & {"brokers", "cash_balances"}
        else {}
    )
    issues: list[PortfolioPlannerSourceIssue] = []

    assets = (
        build_planner_assets(
            candidate_assets,
            held_asset_ids=held_asset_ids,
            explicit_asset_selection=request.asset_ids is not None,
            issues=issues,
        )
        if "assets" in requested_sections
        else []
    )

    observed_currencies: dict[int, list[str]] = {}
    if "brokers" in requested_sections:
        observed_currencies = observed_currencies_by_broker(
            cash_by_broker,
            issues=issues,
        )
    brokers = (
        build_planner_brokers(
            access_rows,
            observed_currencies=observed_currencies,
            issues=issues,
        )
        if "brokers" in requested_sections
        else []
    )

    holding_facts = (
        build_planner_holdings(
            selected_holding_rows,
            accesses=accesses,
            selected_asset_ids=selected_asset_ids,
            issues=issues,
        )
        if requested_sections & {"holdings", "wac_contexts"}
        else []
    )
    holdings = holding_facts if "holdings" in requested_sections else []
    cash_balances = (
        build_planner_cash_balances(
            access_rows,
            cash_by_broker=cash_by_broker,
            issues=issues,
        )
        if "cash_balances" in requested_sections
        else []
    )

    prices_by_asset: dict[int, PriceHistory] = {}
    if "prices" in requested_sections:
        prices_by_asset = await load_latest_prices(
            session,
            candidate_asset_ids=selected_asset_ids,
            as_of_date=request.as_of,
        )
    prices = (
        build_planner_prices(
            candidate_assets,
            prices=prices_by_asset,
            as_of=request.as_of,
            issues=issues,
        )
        if "prices" in requested_sections
        else []
    )
    classifications = (
        build_planner_classifications(
            candidate_assets,
            issues=issues,
        )
        if "classifications" in requested_sections
        else []
    )

    wac_contexts: list[PortfolioPlannerWacContext] = []
    if "wac_contexts" in requested_sections:
        wac_contexts = await build_planner_wac_contexts(
            session,
            holding_rows=selected_holding_rows,
            selected_asset_ids=selected_asset_ids,
            assets_by_id=assets_by_id,
            as_of=request.as_of,
            target_currency=request.target_currency,
            issues=issues,
        )

    fx_quotes: list[PortfolioPlannerSourceFxQuote] = []
    if "fx_quotes" in requested_sections:
        fx_quotes = await build_planner_fx_quotes(
            session,
            request_pairs=request.fx_pairs,
            as_of=request.as_of,
            issues=issues,
        )

    current_distribution: PortfolioPlannerCurrentDistribution | None = None
    if "current_distribution" in requested_sections:
        current_distribution = await build_planner_current_distribution(
            session,
            user_id=user_id,
            broker_ids=list(accesses),
            scenario_asset_ids=[asset.id for asset in candidate_assets if asset.id is not None],
            as_of=request.as_of,
            target_currency=request.target_currency,
            issues=issues,
        )

    provenance = _build_planner_provenance(
        requested_sections,
        captured_at=captured_at,
    )
    return PortfolioPlannerSourceResponse(
        snapshot=PortfolioPlannerSourceSnapshot(
            as_of=request.as_of,
            target_currency=request.target_currency,
            generated_at=captured_at,
            requested_sections=request.requested_sections,
            source_revision=_PLANNER_SOURCE_REVISION,
        ),
        provenance=provenance,
        assets=assets,
        brokers=brokers,
        holdings=holdings,
        cash_balances=cash_balances,
        prices=prices,
        classifications=classifications,
        wac_contexts=wac_contexts,
        fx_quotes=fx_quotes,
        current_distribution=current_distribution,
        issues=issues,
    )
