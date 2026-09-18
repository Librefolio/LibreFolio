"""Read-only Asset catalog and OWNER full-custody facts for allocation editors."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date as date_type
from decimal import Decimal

import pycountry
from babel.numbers import get_currency_precision
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, UserRole
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import (
    PlannerSourceSection,
    PortfolioAllocationSource,
    PortfolioAllocationSourceAsset,
    PortfolioAllocationSourceCashBalance,
    PortfolioAllocationSourceCashSource,
    PortfolioAllocationSourceContext,
    PortfolioAllocationSourceQuote,
    PortfolioPlannerSourceAsset,
    PortfolioPlannerSourceBroker,
    PortfolioPlannerSourceCashBalance,
    PortfolioPlannerSourceClassification,
    PortfolioPlannerSourceCurrencySpec,
    PortfolioPlannerSourceFieldPath,
    PortfolioPlannerSourceFxQuote,
    PortfolioPlannerSourceHolding,
    PortfolioPlannerSourceIssue,
    PortfolioPlannerSourcePrice,
    PortfolioPlannerSourceProvenance,
    PortfolioPlannerSourceRequest,
    PortfolioPlannerSourceResponse,
    PortfolioPlannerSourceSnapshot,
    PortfolioPlannerSourceTextParam,
    PortfolioPlannerSourceWacFxEvidence,
    PortfolioPlannerWacContext,
)
from backend.app.utils.datetime_utils import utcnow
from backend.app.utils.sector_fin_utils import FinancialSector


class PortfolioAllocationSourceAccessError(PermissionError):
    """Requested cash brokers are not OWNER-accessible to the caller."""

    def __init__(self, broker_ids: list[int]) -> None:
        self.broker_ids = tuple(sorted(broker_ids))
        super().__init__(f"Cash broker selection is not fully OWNER-accessible: {', '.join(map(str, self.broker_ids))}")


async def build_portfolio_allocation_source(
    session: AsyncSession,
    *,
    user_id: int,
    as_of_date: date_type,
    selected_cash_broker_ids: list[int],
) -> PortfolioAllocationSource:
    """Build catalog candidates, OWNER custody contexts, and native cash facts."""
    access_rows, accesses = await _load_owner_accesses(session, user_id=user_id)
    _ensure_cash_brokers_accessible(selected_cash_broker_ids=selected_cash_broker_ids, accesses=accesses)
    holding_rows = await _load_holding_rows(session, accesses=accesses, as_of_date=as_of_date)
    candidate_assets, candidate_asset_ids = await _load_candidate_assets(session, holding_rows=holding_rows)
    prices = await _load_latest_prices(session, candidate_asset_ids=candidate_asset_ids, as_of_date=as_of_date)
    total_counts, own_counts = await _load_usage_counts(
        session,
        accesses=accesses,
        candidate_asset_ids=candidate_asset_ids,
    )
    contexts_by_asset = _build_contexts_by_asset(holding_rows=holding_rows, accesses=accesses)
    source_assets = _build_source_assets(
        candidate_assets=candidate_assets,
        contexts_by_asset=contexts_by_asset,
        prices=prices,
        total_counts=total_counts,
        own_counts=own_counts,
        as_of_date=as_of_date,
    )
    cash_by_broker = await _load_cash_by_broker(session, accesses=accesses, as_of_date=as_of_date)
    cash_sources = _build_cash_sources(access_rows=access_rows, cash_by_broker=cash_by_broker)

    return PortfolioAllocationSource(
        generated_at=utcnow(),
        as_of_date=as_of_date,
        assets=source_assets,
        cash_sources=cash_sources,
        selected_cash_balances=_build_selected_cash_balances(
            selected_cash_broker_ids=selected_cash_broker_ids,
            cash_by_broker=cash_by_broker,
        ),
    )


async def _load_owner_accesses(
    session: AsyncSession,
    *,
    user_id: int,
) -> tuple[list, dict[int, tuple[BrokerUserAccess, Broker]]]:
    access_rows = (
        await session.execute(
            select(BrokerUserAccess, Broker)
            .join(Broker, Broker.id == BrokerUserAccess.broker_id)
            .where(
                BrokerUserAccess.user_id == user_id,
                BrokerUserAccess.role == UserRole.OWNER,
            )
            .order_by(Broker.name, Broker.id)
        )
    ).all()

    accesses: dict[int, tuple[BrokerUserAccess, Broker]] = {}
    for access, broker in access_rows:
        if broker.id is None:
            raise RuntimeError("Persisted broker is missing its id")
        accesses[broker.id] = (access, broker)
    return access_rows, accesses


def _ensure_cash_brokers_accessible(
    *,
    selected_cash_broker_ids: list[int],
    accesses: dict[int, tuple[BrokerUserAccess, Broker]],
) -> None:
    inaccessible_cash_broker_ids = sorted(set(selected_cash_broker_ids) - accesses.keys())
    if inaccessible_cash_broker_ids:
        raise PortfolioAllocationSourceAccessError(inaccessible_cash_broker_ids)


async def _load_holding_rows(
    session: AsyncSession,
    *,
    accesses: dict[int, tuple[BrokerUserAccess, Broker]],
    as_of_date: date_type,
) -> list:
    quantity_sum = func.sum(Transaction.quantity)
    if not accesses:
        return []
    return (
        await session.execute(
            select(
                Transaction.broker_id,
                Transaction.asset_id,
                quantity_sum.label("custody_quantity"),
            )
            .where(
                Transaction.broker_id.in_(accesses),
                Transaction.asset_id.is_not(None),
                Transaction.date <= as_of_date,
            )
            .group_by(Transaction.broker_id, Transaction.asset_id)
            .having(quantity_sum != 0)
        )
    ).all()


async def _load_candidate_assets(
    session: AsyncSession,
    *,
    holding_rows: list,
) -> tuple[list[Asset], set[int]]:
    all_assets = list((await session.execute(select(Asset).order_by(Asset.display_name, Asset.id))).scalars())
    assets_by_id = {asset.id: asset for asset in all_assets if asset.id is not None}
    current_asset_ids = {asset_id for _, asset_id, _ in holding_rows if asset_id is not None}
    missing_asset_ids = current_asset_ids - assets_by_id.keys()
    if missing_asset_ids:
        raise RuntimeError(f"Allocation source references missing assets: {sorted(missing_asset_ids)}")

    candidate_assets = [asset for asset in all_assets if asset.id is not None and (asset.active or asset.id in current_asset_ids)]
    candidate_asset_ids = {asset.id for asset in candidate_assets if asset.id is not None}
    return candidate_assets, candidate_asset_ids


async def _load_latest_prices(
    session: AsyncSession,
    *,
    candidate_asset_ids: set[int],
    as_of_date: date_type,
) -> dict[int, PriceHistory]:
    prices: dict[int, PriceHistory] = {}
    if not candidate_asset_ids:
        return prices

    latest_price_dates = (
        select(
            PriceHistory.asset_id.label("asset_id"),
            func.max(PriceHistory.date).label("latest_date"),
        )
        .where(
            PriceHistory.asset_id.in_(candidate_asset_ids),
            PriceHistory.close.is_not(None),
            PriceHistory.date <= as_of_date,
        )
        .group_by(PriceHistory.asset_id)
        .subquery()
    )
    price_rows = (
        await session.execute(
            select(PriceHistory).join(
                latest_price_dates,
                and_(
                    PriceHistory.asset_id == latest_price_dates.c.asset_id,
                    PriceHistory.date == latest_price_dates.c.latest_date,
                ),
            ),
        )
    ).scalars()
    return {price.asset_id: price for price in price_rows}


async def _load_usage_counts(
    session: AsyncSession,
    *,
    accesses: dict[int, tuple[BrokerUserAccess, Broker]],
    candidate_asset_ids: set[int],
) -> tuple[dict[int, int], dict[int, int]]:
    total_counts: dict[int, int] = {}
    if candidate_asset_ids:
        total_counts = {asset_id: count for asset_id, count in (await session.execute(select(Transaction.asset_id, func.count(Transaction.id)).where(Transaction.asset_id.in_(candidate_asset_ids)).group_by(Transaction.asset_id))).all() if asset_id is not None}

    positive_owner_broker_ids = {broker_id for broker_id, (access, _broker) in accesses.items() if access.share_percentage > 0}
    own_counts: dict[int, int] = {}
    if candidate_asset_ids and positive_owner_broker_ids:
        own_counts = {
            asset_id: count
            for asset_id, count in (
                await session.execute(
                    select(Transaction.asset_id, func.count(Transaction.id))
                    .where(
                        Transaction.asset_id.in_(candidate_asset_ids),
                        Transaction.broker_id.in_(positive_owner_broker_ids),
                    )
                    .group_by(Transaction.asset_id)
                )
            ).all()
            if asset_id is not None
        }
    return total_counts, own_counts


def _build_contexts_by_asset(
    *,
    holding_rows: list,
    accesses: dict[int, tuple[BrokerUserAccess, Broker]],
) -> dict[int, list[PortfolioAllocationSourceContext]]:
    contexts_by_asset: dict[int, list[PortfolioAllocationSourceContext]] = defaultdict(list)
    for broker_id, asset_id, custody_quantity in holding_rows:
        if asset_id is None:
            continue
        access, broker = accesses[broker_id]
        contexts_by_asset[asset_id].append(
            PortfolioAllocationSourceContext(
                context_key=f"asset:{asset_id}:broker:{broker_id}",
                broker_id=broker_id,
                broker_name=broker.name,
                broker_icon_url=broker.icon_url,
                broker_portal_url=broker.portal_url,
                broker_default_import_plugin=broker.default_import_plugin,
                ownership_share_percent=access.share_percentage * Decimal("100"),
                custody_quantity=custody_quantity,
            )
        )
    return contexts_by_asset


def _build_source_assets(
    *,
    candidate_assets: list[Asset],
    contexts_by_asset: dict[int, list[PortfolioAllocationSourceContext]],
    prices: dict[int, PriceHistory],
    total_counts: dict[int, int],
    own_counts: dict[int, int],
    as_of_date: date_type,
) -> list[PortfolioAllocationSourceAsset]:
    source_assets: list[PortfolioAllocationSourceAsset] = []
    for asset in candidate_assets:
        if asset.id is None:
            continue
        asset_id = asset.id
        contexts = contexts_by_asset.get(asset_id, [])
        price = prices.get(asset_id)
        reference_date = price.date if price else None
        usage_scope = "owned" if own_counts.get(asset_id, 0) > 0 else "other_users" if total_counts.get(asset_id, 0) > 0 else "observed"
        source_assets.append(
            PortfolioAllocationSourceAsset(
                asset_id=asset_id,
                instrument_key=f"asset:{asset_id}",
                candidate_key=f"asset:{asset_id}:candidate",
                name=asset.display_name,
                ticker=asset.identifier_ticker,
                asset_type=asset.asset_type.value,
                icon_url=asset.icon_url,
                active=asset.active,
                usage_scope=usage_scope,
                quote=PortfolioAllocationSourceQuote(
                    raw_price=price.close if price else None,
                    currency=price.currency if price else asset.currency,
                    quote_base_quantity=asset.quote_base_quantity or 1,
                    reference_date=reference_date,
                    source=price.source_plugin_key if price else None,
                    days_before_requested=(as_of_date - reference_date).days if reference_date else None,
                ),
                contexts=sorted(contexts, key=lambda item: (item.broker_name.casefold(), item.broker_id)),
            )
        )
    return source_assets


async def _load_cash_by_broker(
    session: AsyncSession,
    *,
    accesses: dict[int, tuple[BrokerUserAccess, Broker]],
    as_of_date: date_type,
) -> dict[int, dict[str, Decimal]]:
    cash_by_broker: dict[int, dict[str, Decimal]] = defaultdict(dict)
    if not accesses:
        return cash_by_broker

    cash_rows = (
        await session.execute(
            select(
                Transaction.broker_id,
                Transaction.currency,
                func.sum(Transaction.amount).label("cash_amount"),
            )
            .where(
                Transaction.broker_id.in_(accesses),
                Transaction.currency.is_not(None),
                Transaction.date <= as_of_date,
            )
            .group_by(Transaction.broker_id, Transaction.currency)
        )
    ).all()
    for broker_id, currency, amount in cash_rows:
        if currency is not None:
            cash_by_broker[broker_id][currency] = amount
    return cash_by_broker


def _build_cash_sources(
    *,
    access_rows: list,
    cash_by_broker: dict[int, dict[str, Decimal]],
) -> list[PortfolioAllocationSourceCashSource]:
    cash_sources: list[PortfolioAllocationSourceCashSource] = []
    for access, broker in access_rows:
        if broker.id is None:
            continue
        cash_sources.append(
            PortfolioAllocationSourceCashSource(
                broker_id=broker.id,
                broker_name=broker.name,
                broker_icon_url=broker.icon_url,
                broker_portal_url=broker.portal_url,
                broker_default_import_plugin=broker.default_import_plugin,
                ownership_share_percent=access.share_percentage * Decimal("100"),
                balances=[PortfolioAllocationSourceCashBalance(currency=currency, amount=amount) for currency, amount in sorted(cash_by_broker.get(broker.id, {}).items())],
            )
        )
    return cash_sources


def _build_selected_cash_balances(
    *,
    selected_cash_broker_ids: list[int],
    cash_by_broker: dict[int, dict[str, Decimal]],
) -> list[PortfolioAllocationSourceCashBalance]:
    selected_cash_by_currency: dict[str, Decimal] = {}
    for broker_id in selected_cash_broker_ids:
        for currency, amount in cash_by_broker.get(broker_id, {}).items():
            selected_cash_by_currency[currency] = selected_cash_by_currency.get(currency, Decimal("0")) + amount
    return [PortfolioAllocationSourceCashBalance(currency=currency, amount=amount) for currency, amount in sorted(selected_cash_by_currency.items())]


# =============================================================================
# Planner source v2 — dedicated uncached domain-copy endpoint
# =============================================================================

_PLANNER_SOURCE_REVISION = "2.0.0"
_PORTFOLIO_PROVENANCE_ID = "source:portfolio-ledger"
_MARKET_PROVENANCE_ID = "source:market-data"
_BROKER_PROVENANCE_ID = "source:broker-domain"
_FX_PROVENANCE_ID = "source:saved-fx"
_WAC_PROVENANCE_ID = "source:runtime-wac"
_KNOWN_SECTORS = frozenset(sector.value for sector in FinancialSector)


class PortfolioPlannerSourceAccessError(PermissionError):
    """The complete selected Broker scope is not available to the caller."""


class PortfolioPlannerSourceBrokerNotFoundError(PortfolioPlannerSourceAccessError):
    """Compatibility error type; selected Broker gaps now use the generic access error."""


class PortfolioPlannerSourceAssetNotFoundError(LookupError):
    """At least one explicitly selected Asset does not exist."""


def _asset_key(asset_id: int) -> str:
    return f"asset:{asset_id}"


def _broker_key(broker_id: int) -> str:
    return f"broker:{broker_id}"


def _holding_key(asset_id: int, broker_id: int) -> str:
    return f"holding:asset:{asset_id}:broker:{broker_id}"


def _cash_key(broker_id: int, currency: str) -> str:
    return f"cash:broker:{broker_id}:{currency}"


def _price_key(asset_id: int, reference_date: date_type) -> str:
    return f"price:asset:{asset_id}:{reference_date.isoformat()}"


def _wac_key(asset_id: int, broker_id: int, as_of: date_type, currency: str) -> str:
    return f"wac:asset:{asset_id}:broker:{broker_id}:{as_of.isoformat()}:{currency}"


def _classification_key(asset_id: int, dimension: str, category_id: str | None) -> str:
    if category_id is None:
        token = "none"
    else:
        token = hashlib.sha256(category_id.encode("utf-8")).hexdigest()[:12]
    return f"class:asset:{asset_id}:{dimension}:{token}"


def _fx_key(
    pair: str,
    reference_date: date_type,
    source: str,
) -> str:
    source_token = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]
    return f"fx:{pair}:{reference_date.isoformat()}:{source_token}"


def _field_issue(
    *,
    code: str,
    kind: str,
    severity: str,
    section: str,
    entity_kind: str,
    entity_id: str,
    field: str,
    params: list | None = None,
) -> PortfolioPlannerSourceIssue:
    return PortfolioPlannerSourceIssue(
        code=code,
        kind=kind,
        severity=severity,
        path=PortfolioPlannerSourceFieldPath(
            kind="field",
            section=section,
            entity_kind=entity_kind,
            entity_id=entity_id,
            field=field,
        ),
        message_key=code,
        params=params or [],
    )


def _text_param(name: str, value: str) -> PortfolioPlannerSourceTextParam:
    return PortfolioPlannerSourceTextParam(kind="text", name=name, value=value)


def _build_planner_provenance(
    requested_sections: set[PlannerSourceSection],
    *,
    captured_at,
) -> list[PortfolioPlannerSourceProvenance]:
    records = [
        PortfolioPlannerSourceProvenance(
            provenance_id=_PORTFOLIO_PROVENANCE_ID,
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
                provenance_id=_MARKET_PROVENANCE_ID,
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
                provenance_id=_BROKER_PROVENANCE_ID,
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
                provenance_id=_FX_PROVENANCE_ID,
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
                provenance_id=_WAC_PROVENANCE_ID,
                kind="domain_copy",
                domain="wac",
                source_ref="portfolio_service.compute_wac_iterative",
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


def _validated_currency(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return Currency.validate_code(value)
    except ValueError:
        return None


def _rates_match(left: Decimal, right: Decimal) -> bool:
    """Accept only Decimal-context round-off from derived inverse rates."""

    scale = max(abs(left), abs(right), Decimal("1"))
    return abs(left - right) <= scale * Decimal("1e-24")


def _build_planner_assets(
    candidate_assets: list[Asset],
    *,
    held_asset_ids: set[int],
    explicit_asset_selection: bool,
    issues: list[PortfolioPlannerSourceIssue],
) -> list[PortfolioPlannerSourceAsset]:
    rows: list[PortfolioPlannerSourceAsset] = []
    for asset in candidate_assets:
        if asset.id is None:
            continue
        asset_key = _asset_key(asset.id)
        asset_class = getattr(asset.asset_type, "value", asset.asset_type)
        if not isinstance(asset_class, str) or not asset_class:
            asset_class = ""
            issues.append(
                _field_issue(
                    code="allocation.asset_type_missing",
                    kind="missing",
                    severity="warning",
                    section="assets",
                    entity_kind="asset",
                    entity_id=asset_key,
                    field="asset_class",
                )
            )
        if explicit_asset_selection and not asset.active and asset.id not in held_asset_ids:
            issues.append(
                _field_issue(
                    code="allocation.asset_inactive_not_buyable",
                    kind="unsupported",
                    severity="error",
                    section="assets",
                    entity_kind="asset",
                    entity_id=asset_key,
                    field="active",
                )
            )
        rows.append(
            PortfolioPlannerSourceAsset(
                asset_id=asset_key,
                source_asset_id=asset.id,
                name=asset.display_name,
                ticker=asset.identifier_ticker,
                asset_class=asset_class,
                icon_url=asset.icon_url,
                active=asset.active,
                provenance_id=_MARKET_PROVENANCE_ID,
            )
        )
    return rows


def _observed_currencies_by_broker(
    cash_by_broker: dict[int, dict[str, Decimal]],
    *,
    issues: list[PortfolioPlannerSourceIssue],
) -> dict[int, list[str]]:
    observed: dict[int, list[str]] = {}
    for broker_id, balances in cash_by_broker.items():
        currencies: list[str] = []
        for raw_currency in sorted(balances):
            currency = _validated_currency(raw_currency)
            if currency is None:
                issues.append(
                    _field_issue(
                        code="allocation.currency_spec_missing",
                        kind="missing",
                        severity="error",
                        section="brokers",
                        entity_kind="broker",
                        entity_id=_broker_key(broker_id),
                        field="observed_currencies",
                    )
                )
                continue
            currencies.append(currency)
        observed[broker_id] = currencies
    return observed


def _build_planner_brokers(
    access_rows: list,
    *,
    observed_currencies: dict[int, list[str]],
    issues: list[PortfolioPlannerSourceIssue],
) -> list[PortfolioPlannerSourceBroker]:
    rows: list[PortfolioPlannerSourceBroker] = []
    for access, broker in access_rows:
        if broker.id is None:
            continue
        broker_key = _broker_key(broker.id)
        rows.append(
            PortfolioPlannerSourceBroker(
                broker_id=broker_key,
                source_broker_id=broker.id,
                name=broker.name,
                icon_url=broker.icon_url,
                portal_url=broker.portal_url,
                default_import_plugin=broker.default_import_plugin,
                access_role="OWNER",
                ownership_share=access.share_percentage,
                observed_currencies=observed_currencies.get(broker.id, []),
                active=broker.is_active,
                allow_cash_overdraft=broker.allow_cash_overdraft,
                allow_asset_shorting=broker.allow_asset_shorting,
                execution_profile_status="not_available",
                provenance_id=_BROKER_PROVENANCE_ID,
            )
        )
        if not broker.is_active:
            issues.append(
                _field_issue(
                    code="allocation.broker_inactive",
                    kind="unsupported",
                    severity="warning",
                    section="brokers",
                    entity_kind="broker",
                    entity_id=broker_key,
                    field="active",
                )
            )
        issues.append(
            _field_issue(
                code="allocation.broker_execution_profile_unsupported",
                kind="unsupported",
                severity="error",
                section="brokers",
                entity_kind="broker",
                entity_id=broker_key,
                field="execution_profile_status",
            )
        )
    return rows


def _build_planner_holdings(
    holding_rows: list,
    *,
    accesses: dict[int, tuple[BrokerUserAccess, Broker]],
    selected_asset_ids: set[int],
    issues: list[PortfolioPlannerSourceIssue],
) -> list[PortfolioPlannerSourceHolding]:
    rows: list[PortfolioPlannerSourceHolding] = []
    for broker_id, asset_id, custody_quantity in sorted(
        holding_rows,
        key=lambda row: (row[1], row[0]),
    ):
        if asset_id is None or asset_id not in selected_asset_ids:
            continue
        access, _broker = accesses[broker_id]
        holding_id = _holding_key(asset_id, broker_id)
        rows.append(
            PortfolioPlannerSourceHolding(
                holding_id=holding_id,
                asset_id=_asset_key(asset_id),
                broker_id=_broker_key(broker_id),
                custody_quantity=custody_quantity,
                ownership_share=access.share_percentage,
                economic_quantity=custody_quantity * access.share_percentage,
                quantity_unit="asset_unit",
                provenance_id=_PORTFOLIO_PROVENANCE_ID,
            )
        )
        if custody_quantity < 0:
            issues.append(
                _field_issue(
                    code="allocation.negative_inventory_unsupported",
                    kind="unsupported",
                    severity="error",
                    section="holdings",
                    entity_kind="holding",
                    entity_id=holding_id,
                    field="custody_quantity",
                )
            )
    return rows


def _build_planner_cash_balances(
    access_rows: list,
    *,
    cash_by_broker: dict[int, dict[str, Decimal]],
    issues: list[PortfolioPlannerSourceIssue],
) -> list[PortfolioPlannerSourceCashBalance]:
    rows: list[PortfolioPlannerSourceCashBalance] = []
    for access, broker in access_rows:
        if broker.id is None:
            continue
        for raw_currency, custody_amount in sorted(cash_by_broker.get(broker.id, {}).items()):
            currency = _validated_currency(raw_currency)
            if currency is None:
                issues.append(
                    _field_issue(
                        code="allocation.currency_spec_missing",
                        kind="missing",
                        severity="error",
                        section="cash_balances",
                        entity_kind="broker",
                        entity_id=_broker_key(broker.id),
                        field="currency",
                    )
                )
                continue
            cash_id = _cash_key(broker.id, currency)
            rows.append(
                PortfolioPlannerSourceCashBalance(
                    cash_id=cash_id,
                    broker_id=_broker_key(broker.id),
                    currency=currency,
                    custody_amount=custody_amount,
                    ownership_share=access.share_percentage,
                    economic_amount=custody_amount * access.share_percentage,
                    provenance_id=_PORTFOLIO_PROVENANCE_ID,
                )
            )
            if custody_amount < 0:
                issues.append(
                    _field_issue(
                        code="allocation.negative_cash_unsupported",
                        kind="unsupported",
                        severity="error",
                        section="cash_balances",
                        entity_kind="cash_balance",
                        entity_id=cash_id,
                        field="custody_amount",
                    )
                )
    return rows


def _build_planner_prices(
    candidate_assets: list[Asset],
    *,
    prices: dict[int, PriceHistory],
    as_of: date_type,
    issues: list[PortfolioPlannerSourceIssue],
) -> list[PortfolioPlannerSourcePrice]:
    rows: list[PortfolioPlannerSourcePrice] = []
    for asset in candidate_assets:
        if asset.id is None:
            continue
        asset_key = _asset_key(asset.id)
        price = prices.get(asset.id)
        reference_date = price.date if price else None
        price_id = _price_key(asset.id, reference_date or as_of)
        currency = _validated_currency(price.currency if price else asset.currency)
        if price is None:
            issues.append(
                _field_issue(
                    code="allocation.price_missing",
                    kind="missing",
                    severity="error",
                    section="prices",
                    entity_kind="price",
                    entity_id=price_id,
                    field="amount",
                )
            )
        elif reference_date is None:
            issues.append(
                _field_issue(
                    code="allocation.price_date_missing",
                    kind="missing",
                    severity="error",
                    section="prices",
                    entity_kind="price",
                    entity_id=price_id,
                    field="reference_date",
                )
            )
        if currency is None:
            issues.append(
                _field_issue(
                    code="allocation.currency_spec_missing",
                    kind="missing",
                    severity="error",
                    section="prices",
                    entity_kind="price",
                    entity_id=price_id,
                    field="currency",
                )
            )

        quote_base_quantity: Decimal | None = None
        if asset.quote_base_quantity is not None and asset.quote_base_quantity > 0:
            quote_base_quantity = Decimal(asset.quote_base_quantity)
        else:
            issues.append(
                _field_issue(
                    code="allocation.quote_base_quantity_missing",
                    kind="missing" if asset.quote_base_quantity is None else "invalid",
                    severity="error",
                    section="prices",
                    entity_kind="price",
                    entity_id=price_id,
                    field="quote_base_quantity",
                )
            )

        rows.append(
            PortfolioPlannerSourcePrice(
                price_id=price_id,
                asset_id=asset_key,
                amount=price.close if price else None,
                currency=currency,
                quote_base_quantity=quote_base_quantity,
                reference_date=reference_date,
                source=price.source_plugin_key if price else None,
                days_before_requested=(as_of - reference_date).days if reference_date else None,
                provenance_id=_MARKET_PROVENANCE_ID,
            )
        )
    return rows


def _classification_placeholder(
    asset_id: int,
    dimension: str,
) -> PortfolioPlannerSourceClassification:
    return PortfolioPlannerSourceClassification(
        classification_id=_classification_key(asset_id, dimension, None),
        asset_id=_asset_key(asset_id),
        dimension=dimension,
        category_id=None,
        label=None,
        weight=None,
        provenance_id=_MARKET_PROVENANCE_ID,
    )


def _parse_saved_distribution(  # noqa: C901 — direct validation keeps persisted classifications unmodified
    value,
    *,
    dimension: str,
) -> list[tuple[str, Decimal]] | None:
    if not isinstance(value, dict):
        return None
    distribution = value.get("distribution")
    if not isinstance(distribution, dict) or not distribution:
        return None

    parsed: list[tuple[str, Decimal]] = []
    for category, raw_weight in distribution.items():
        if not isinstance(category, str) or not category:
            return None
        if dimension == "sector" and category not in _KNOWN_SECTORS:
            return None
        if dimension == "geography" and (len(category) != 3 or category != category.upper() or pycountry.countries.get(alpha_3=category) is None):
            return None
        if not isinstance(raw_weight, Decimal):
            return None
        weight = raw_weight
        if not weight.is_finite() or weight < 0:
            return None
        parsed.append((category, weight))

    if sum((weight for _category, weight in parsed), Decimal("0")) != Decimal("1"):
        return None
    return sorted(parsed, key=lambda item: item[0])


def _build_planner_classifications(  # noqa: C901 — missing/invalid dimension outcomes stay explicit
    candidate_assets: list[Asset],
    *,
    issues: list[PortfolioPlannerSourceIssue],
) -> list[PortfolioPlannerSourceClassification]:
    rows: list[PortfolioPlannerSourceClassification] = []
    for asset in candidate_assets:
        if asset.id is None:
            continue
        asset_key = _asset_key(asset.id)
        asset_class = getattr(asset.asset_type, "value", asset.asset_type)
        if isinstance(asset_class, str) and asset_class:
            rows.append(
                PortfolioPlannerSourceClassification(
                    classification_id=_classification_key(asset.id, "asset_type", asset_class),
                    asset_id=asset_key,
                    dimension="asset_type",
                    category_id=asset_class,
                    label=asset_class,
                    weight=Decimal("1"),
                    provenance_id=_MARKET_PROVENANCE_ID,
                )
            )
        else:
            rows.append(_classification_placeholder(asset.id, "asset_type"))
            issues.append(
                _field_issue(
                    code="allocation.asset_type_missing",
                    kind="missing",
                    severity="warning",
                    section="classifications",
                    entity_kind="asset",
                    entity_id=asset_key,
                    field="asset_type",
                )
            )

        if not asset.classification_params:
            for dimension in ("sector", "geography"):
                rows.append(_classification_placeholder(asset.id, dimension))
                issues.append(
                    _field_issue(
                        code=f"allocation.classification_{dimension}_missing",
                        kind="missing",
                        severity="warning",
                        section="classifications",
                        entity_kind="asset",
                        entity_id=asset_key,
                        field=dimension,
                    )
                )
            continue

        try:
            metadata = json.loads(
                asset.classification_params,
                parse_float=Decimal,
                parse_int=Decimal,
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            metadata = None
        if not isinstance(metadata, dict):
            rows.extend(
                [
                    _classification_placeholder(asset.id, "sector"),
                    _classification_placeholder(asset.id, "geography"),
                ]
            )
            issues.append(
                _field_issue(
                    code="allocation.classification_invalid",
                    kind="invalid",
                    severity="warning",
                    section="classifications",
                    entity_kind="asset",
                    entity_id=asset_key,
                    field="classification_params",
                )
            )
            continue

        for dimension, metadata_key in (
            ("sector", "sector_area"),
            ("geography", "geographic_area"),
        ):
            if metadata_key not in metadata or metadata[metadata_key] is None:
                rows.append(_classification_placeholder(asset.id, dimension))
                issues.append(
                    _field_issue(
                        code=f"allocation.classification_{dimension}_missing",
                        kind="missing",
                        severity="warning",
                        section="classifications",
                        entity_kind="asset",
                        entity_id=asset_key,
                        field=dimension,
                    )
                )
                continue
            distribution = _parse_saved_distribution(
                metadata[metadata_key],
                dimension=dimension,
            )
            if distribution is None:
                rows.append(_classification_placeholder(asset.id, dimension))
                issues.append(
                    _field_issue(
                        code="allocation.classification_invalid",
                        kind="invalid",
                        severity="warning",
                        section="classifications",
                        entity_kind="asset",
                        entity_id=asset_key,
                        field=dimension,
                        params=[_text_param("dimension", dimension)],
                    )
                )
                continue
            rows.extend(
                PortfolioPlannerSourceClassification(
                    classification_id=_classification_key(asset.id, dimension, category),
                    asset_id=asset_key,
                    dimension=dimension,
                    category_id=category,
                    label=category,
                    weight=weight,
                    provenance_id=_MARKET_PROVENANCE_ID,
                )
                for category, weight in distribution
            )
    return rows


def _normalized_fx_pair(
    source_currency: str,
    destination_currency: str,
) -> tuple[str, str, bool]:
    if source_currency < destination_currency:
        return source_currency, destination_currency, False
    return destination_currency, source_currency, True


async def _load_latest_planner_fx_rows(
    session: AsyncSession,
    *,
    directed_pairs: list[tuple[str, str]],
    as_of: date_type,
) -> dict[tuple[str, str], FxRate]:
    normalized_pairs = {_normalized_fx_pair(source_currency, destination_currency)[:2] for source_currency, destination_currency in directed_pairs}
    if not normalized_pairs:
        return {}

    pair_filter = or_(*[and_(FxRate.base == base, FxRate.quote == quote) for base, quote in sorted(normalized_pairs)])
    latest_dates = (
        select(
            FxRate.base.label("base"),
            FxRate.quote.label("quote"),
            func.max(FxRate.date).label("latest_date"),
        )
        .where(pair_filter, FxRate.date <= as_of)
        .group_by(FxRate.base, FxRate.quote)
        .subquery()
    )
    rows = (
        await session.execute(
            select(FxRate).join(
                latest_dates,
                and_(
                    FxRate.base == latest_dates.c.base,
                    FxRate.quote == latest_dates.c.quote,
                    FxRate.date == latest_dates.c.latest_date,
                ),
            )
        )
    ).scalars()
    return {(row.base, row.quote): row for row in rows}


async def _load_current_wac_fx_rows(
    session: AsyncSession,
    *,
    windows: set[tuple[str, str, date_type, date_type]],
) -> dict[tuple[str, str, date_type], FxRate]:
    """Load latest saved rows for each TX cutoff, detecting stale WAC-cache evidence."""

    if not windows:
        return {}

    bounds: dict[tuple[str, str], tuple[date_type, date_type]] = {}
    for base, quote, claimed_date, transaction_date in windows:
        previous = bounds.get((base, quote))
        if previous is None:
            bounds[(base, quote)] = (claimed_date, transaction_date)
        else:
            bounds[(base, quote)] = (
                min(previous[0], claimed_date),
                max(previous[1], transaction_date),
            )

    stored_rows = (
        await session.execute(
            select(FxRate).where(
                or_(
                    *[
                        and_(
                            FxRate.base == base,
                            FxRate.quote == quote,
                            FxRate.date >= first_claimed_date,
                            FxRate.date <= last_transaction_date,
                        )
                        for (base, quote), (first_claimed_date, last_transaction_date) in sorted(bounds.items())
                    ]
                )
            )
        )
    ).scalars()
    rows_by_pair: dict[tuple[str, str], list[FxRate]] = defaultdict(list)
    for row in stored_rows:
        rows_by_pair[(row.base, row.quote)].append(row)
    for pair_rows in rows_by_pair.values():
        pair_rows.sort(key=lambda row: row.date, reverse=True)

    latest_rows: dict[tuple[str, str, date_type], FxRate] = {}
    for base, quote, _claimed_date, transaction_date in sorted(windows):
        latest_row = next(
            (row for row in rows_by_pair.get((base, quote), []) if row.date <= transaction_date),
            None,
        )
        if latest_row is not None:
            latest_rows[(base, quote, transaction_date)] = latest_row
    return latest_rows


async def _build_planner_wac_contexts(  # noqa: C901 — sequential WAC/evidence mapping is intentionally fail-closed
    session: AsyncSession,
    *,
    holding_rows: list,
    selected_asset_ids: set[int],
    assets_by_id: dict[int, Asset],
    as_of: date_type,
    target_currency: str,
    issues: list[PortfolioPlannerSourceIssue],
) -> tuple[list[PortfolioPlannerWacContext], set[str]]:
    # Lazy import avoids the portfolio_service → allocation_source module cycle.
    from backend.app.services.portfolio_service import compute_wac_iterative  # noqa: PLC0415

    prepared: list[tuple[int, int, object | None]] = []
    fx_windows: set[tuple[str, str, date_type, date_type]] = set()
    currencies = {target_currency}

    # Deliberately sequential: one AsyncSession is shared, and no provisional
    # item cap or silent truncation belongs in this domain endpoint.
    for broker_id, asset_id, _custody_quantity in sorted(
        holding_rows,
        key=lambda row: (row[1], row[0]),
    ):
        if asset_id is None or asset_id not in selected_asset_ids:
            continue
        asset = assets_by_id.get(asset_id)
        asset_currency = _validated_currency(asset.currency if asset else None)
        if asset is None or asset_currency is None:
            if asset is not None:
                issues.append(
                    _field_issue(
                        code="allocation.currency_spec_missing",
                        kind="missing",
                        severity="error",
                        section="currency_specs",
                        entity_kind="currency_spec",
                        entity_id=f"currency:asset:{asset_id}:invalid",
                        field="minor_unit",
                    )
                )
            prepared.append((broker_id, asset_id, None))
            continue
        result = await compute_wac_iterative(
            session=session,
            broker_id=broker_id,
            asset_id=asset_id,
            as_of_date=as_of,
            asset_currency=asset_currency,
            target_currency_override=target_currency,
            use_cache=False,
        )
        prepared.append((broker_id, asset_id, result))
        for qualifying_tx in result.wac_qualifying_txs:
            fx_info = qualifying_tx.fx_info
            source_currency = _validated_currency(qualifying_tx.original_currency)
            if fx_info is None or fx_info.fx_rate_date is None or source_currency is None or qualifying_tx.fx_rate_used is None or source_currency == target_currency:
                continue
            base, quote, _inverted = _normalized_fx_pair(source_currency, target_currency)
            fx_windows.add(
                (
                    base,
                    quote,
                    fx_info.fx_rate_date,
                    qualifying_tx.date,
                )
            )
            currencies.add(source_currency)

    current_fx_rows = await _load_current_wac_fx_rows(session, windows=fx_windows)
    rows: list[PortfolioPlannerWacContext] = []
    for broker_id, asset_id, result in prepared:
        holding_id = _holding_key(asset_id, broker_id)
        wac_id = _wac_key(asset_id, broker_id, as_of, target_currency)
        issues.append(
            _field_issue(
                code="allocation.fiscal_currency_missing",
                kind="missing",
                severity="warning",
                section="wac_contexts",
                entity_kind="wac_context",
                entity_id=wac_id,
                field="fiscal_currency",
            )
        )

        evidence_by_key: dict[
            tuple[str, str, date_type | None, Decimal | None, str | None],
            PortfolioPlannerSourceWacFxEvidence,
        ] = {}
        evidence_incomplete = False
        if result is not None:
            for qualifying_tx in result.wac_qualifying_txs:
                if qualifying_tx.original_currency is None:
                    continue
                source_currency = _validated_currency(qualifying_tx.original_currency)
                if source_currency == target_currency:
                    continue
                fx_info = qualifying_tx.fx_info
                rate = qualifying_tx.fx_rate_used
                if source_currency is None or fx_info is None or fx_info.fx_rate_date is None or rate is None:
                    evidence_incomplete = True
                    continue
                base, quote, inverted = _normalized_fx_pair(source_currency, target_currency)
                saved_row = current_fx_rows.get((base, quote, qualifying_tx.date))
                saved_directed_rate: Decimal | None = None
                if saved_row is not None and saved_row.rate > 0:
                    saved_directed_rate = Decimal("1") / saved_row.rate if inverted else saved_row.rate
                if saved_row is None or saved_row.date != fx_info.fx_rate_date or saved_directed_rate is None or not _rates_match(saved_directed_rate, rate):
                    evidence_incomplete = True
                    evidence = PortfolioPlannerSourceWacFxEvidence(
                        source_currency=source_currency,
                        destination_currency=target_currency,
                        rate=None,
                        reference_date=None,
                        source=None,
                        inverted=inverted,
                        status="missing",
                    )
                else:
                    evidence = PortfolioPlannerSourceWacFxEvidence(
                        source_currency=source_currency,
                        destination_currency=target_currency,
                        rate=saved_directed_rate,
                        reference_date=fx_info.fx_rate_date,
                        source=saved_row.source,
                        inverted=inverted,
                        status="available",
                    )
                evidence_key = (
                    evidence.source_currency,
                    evidence.destination_currency,
                    evidence.reference_date,
                    evidence.rate,
                    evidence.source,
                )
                evidence_by_key[evidence_key] = evidence

            for missing_pair in result.wac_missing_pairs:
                try:
                    source_currency, destination_currency = missing_pair.pair.split("/", maxsplit=1)
                    source_currency = Currency.validate_code(source_currency)
                    destination_currency = Currency.validate_code(destination_currency)
                except (TypeError, ValueError):
                    evidence_incomplete = True
                    continue
                _base, _quote, inverted = _normalized_fx_pair(
                    source_currency,
                    destination_currency,
                )
                currencies.update((source_currency, destination_currency))
                evidence = PortfolioPlannerSourceWacFxEvidence(
                    source_currency=source_currency,
                    destination_currency=destination_currency,
                    rate=None,
                    reference_date=None,
                    source=None,
                    inverted=inverted,
                    status="missing",
                )
                evidence_key = (
                    evidence.source_currency,
                    evidence.destination_currency,
                    evidence.reference_date,
                    evidence.rate,
                    evidence.source,
                )
                evidence_by_key[evidence_key] = evidence
                evidence_incomplete = True

        evidence = sorted(
            evidence_by_key.values(),
            key=lambda item: (
                item.source_currency,
                item.destination_currency,
                item.reference_date or date_type.min,
                str(item.rate) if item.rate is not None else "",
                item.source or "",
            ),
        )
        unit_cost = None
        if result is not None and result.wac is not None and result.wac.code == target_currency and not evidence_incomplete:
            unit_cost = result.wac.amount

        if evidence_incomplete or (result is not None and result.wac_missing_pairs):
            issues.append(
                _field_issue(
                    code="allocation.wac_fx_missing",
                    kind="missing",
                    severity="error",
                    section="wac_contexts",
                    entity_kind="wac_context",
                    entity_id=wac_id,
                    field="fx_evidence",
                )
            )
        elif unit_cost is None:
            issues.append(
                _field_issue(
                    code="allocation.wac_missing",
                    kind="missing",
                    severity="error",
                    section="wac_contexts",
                    entity_kind="wac_context",
                    entity_id=wac_id,
                    field="unit_cost",
                )
            )

        rows.append(
            PortfolioPlannerWacContext(
                wac_id=wac_id,
                holding_id=holding_id,
                asset_id=_asset_key(asset_id),
                broker_id=_broker_key(broker_id),
                method="runtime_wac",
                unit_cost=unit_cost,
                fiscal_currency=None,
                target_currency=target_currency,
                as_of=as_of,
                fx_evidence=evidence,
                provenance_id=_WAC_PROVENANCE_ID,
            )
        )
    return rows, currencies


async def _build_planner_fx_quotes(
    session: AsyncSession,
    *,
    request_pairs: list[str],
    as_of: date_type,
    issues: list[PortfolioPlannerSourceIssue],
) -> tuple[list[PortfolioPlannerSourceFxQuote], set[str]]:
    directed_pairs = [tuple(pair.split("/", maxsplit=1)) for pair in request_pairs]
    saved_rows = await _load_latest_planner_fx_rows(
        session,
        directed_pairs=directed_pairs,
        as_of=as_of,
    )
    rows: list[PortfolioPlannerSourceFxQuote] = []
    currencies: set[str] = set()

    for pair in sorted(request_pairs):
        base, quote = pair.split("/", maxsplit=1)
        currencies.update((base, quote))
        saved_row = saved_rows.get((base, quote))
        if saved_row is None:
            fx_id = _fx_key(pair, as_of, "missing")
            rows.append(
                PortfolioPlannerSourceFxQuote(
                    fx_quote_id=fx_id,
                    pair=pair,
                    rate=None,
                    reference_date=None,
                    source=None,
                    days_before_requested=None,
                    provenance_id=_FX_PROVENANCE_ID,
                )
            )
            issues.append(
                _field_issue(
                    code="allocation.saved_fx_missing",
                    kind="missing",
                    severity="error",
                    section="fx_quotes",
                    entity_kind="fx_quote",
                    entity_id=fx_id,
                    field="rate",
                    params=[_text_param("pair", pair)],
                )
            )
            continue

        fx_id = _fx_key(pair, saved_row.date, saved_row.source)
        rate = saved_row.rate if saved_row.rate > 0 else None
        if rate is None:
            issues.append(
                _field_issue(
                    code="allocation.saved_fx_invalid",
                    kind="invalid",
                    severity="error",
                    section="fx_quotes",
                    entity_kind="fx_quote",
                    entity_id=fx_id,
                    field="rate",
                    params=[_text_param("pair", pair)],
                )
            )
        rows.append(
            PortfolioPlannerSourceFxQuote(
                fx_quote_id=fx_id,
                pair=pair,
                rate=rate,
                reference_date=saved_row.date,
                source=saved_row.source,
                days_before_requested=(as_of - saved_row.date).days,
                provenance_id=_FX_PROVENANCE_ID,
            )
        )

    return rows, currencies


def _build_currency_specs(
    currencies: set[str],
    *,
    issues: list[PortfolioPlannerSourceIssue],
) -> list[PortfolioPlannerSourceCurrencySpec]:
    rows: list[PortfolioPlannerSourceCurrencySpec] = []
    for currency in sorted(currencies):
        normalized = _validated_currency(currency)
        entity_id = f"currency:{currency}" if currency.isascii() else "currency:invalid"
        if normalized is None:
            issues.append(
                _field_issue(
                    code="allocation.currency_spec_missing",
                    kind="missing",
                    severity="error",
                    section="currency_specs",
                    entity_kind="currency_spec",
                    entity_id=entity_id,
                    field="minor_unit",
                )
            )
            continue
        try:
            precision = get_currency_precision(normalized)
            if precision is None:
                precision = 2
            if precision < 0:
                raise ValueError("negative currency precision")
            minor_unit = Decimal("1").scaleb(-precision)
        except (ArithmeticError, TypeError, ValueError):
            issues.append(
                _field_issue(
                    code="allocation.currency_spec_missing",
                    kind="missing",
                    severity="error",
                    section="currency_specs",
                    entity_kind="currency_spec",
                    entity_id=f"currency:{normalized}",
                    field="minor_unit",
                )
            )
            continue
        rows.append(
            PortfolioPlannerSourceCurrencySpec(
                currency=normalized,
                minor_unit=minor_unit,
            )
        )
    return rows


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
        await _load_holding_rows(
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
        await _load_cash_by_broker(
            session,
            accesses=accesses,
            as_of_date=request.as_of,
        )
        if requested_sections & {"brokers", "cash_balances"}
        else {}
    )
    issues: list[PortfolioPlannerSourceIssue] = []

    assets = (
        _build_planner_assets(
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
        observed_currencies = _observed_currencies_by_broker(
            cash_by_broker,
            issues=issues,
        )
    brokers = (
        _build_planner_brokers(
            access_rows,
            observed_currencies=observed_currencies,
            issues=issues,
        )
        if "brokers" in requested_sections
        else []
    )

    holding_facts = (
        _build_planner_holdings(
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
        _build_planner_cash_balances(
            access_rows,
            cash_by_broker=cash_by_broker,
            issues=issues,
        )
        if "cash_balances" in requested_sections
        else []
    )

    prices_by_asset: dict[int, PriceHistory] = {}
    if "prices" in requested_sections:
        prices_by_asset = await _load_latest_prices(
            session,
            candidate_asset_ids=selected_asset_ids,
            as_of_date=request.as_of,
        )
    prices = (
        _build_planner_prices(
            candidate_assets,
            prices=prices_by_asset,
            as_of=request.as_of,
            issues=issues,
        )
        if "prices" in requested_sections
        else []
    )
    classifications = (
        _build_planner_classifications(
            candidate_assets,
            issues=issues,
        )
        if "classifications" in requested_sections
        else []
    )

    currencies = {request.target_currency}
    currencies.update(broker_currency for broker in brokers for broker_currency in broker.observed_currencies)
    currencies.update(cash.currency for cash in cash_balances)
    currencies.update(price.currency for price in prices if price.currency is not None)

    wac_contexts: list[PortfolioPlannerWacContext] = []
    if "wac_contexts" in requested_sections:
        wac_contexts, wac_currencies = await _build_planner_wac_contexts(
            session,
            holding_rows=selected_holding_rows,
            selected_asset_ids=selected_asset_ids,
            assets_by_id=assets_by_id,
            as_of=request.as_of,
            target_currency=request.target_currency,
            issues=issues,
        )
        currencies.update(wac_currencies)

    fx_quotes: list[PortfolioPlannerSourceFxQuote] = []
    if "fx_quotes" in requested_sections:
        fx_quotes, fx_currencies = await _build_planner_fx_quotes(
            session,
            request_pairs=request.fx_pairs,
            as_of=request.as_of,
            issues=issues,
        )
        currencies.update(fx_currencies)

    currency_specs = _build_currency_specs(currencies, issues=issues)
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
        currency_specs=currency_specs,
        provenance=provenance,
        assets=assets,
        brokers=brokers,
        holdings=holdings,
        cash_balances=cash_balances,
        prices=prices,
        classifications=classifications,
        wac_contexts=wac_contexts,
        fx_quotes=fx_quotes,
        issues=issues,
    )
