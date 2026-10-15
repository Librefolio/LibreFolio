"""Planner source entities copied from the user's own data: assets, brokers, holdings, cash balances and saved prices, each with its provenance and its field issues."""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from backend.app.db.models import Asset, Broker, BrokerUserAccess, PriceHistory
from backend.app.schemas.portfolio import (
    PortfolioPlannerSourceAsset,
    PortfolioPlannerSourceBroker,
    PortfolioPlannerSourceCashBalance,
    PortfolioPlannerSourceHolding,
    PortfolioPlannerSourceIssue,
    PortfolioPlannerSourcePrice,
)
from backend.app.services.pac_allocator.source.keys import BROKER_PROVENANCE_ID, MARKET_PROVENANCE_ID, PORTFOLIO_PROVENANCE_ID, asset_key, broker_key, cash_key, field_issue, holding_key, price_key, validated_currency


def build_planner_assets(
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
        asset_ref = asset_key(asset.id)
        asset_class = getattr(asset.asset_type, "value", asset.asset_type)
        if not isinstance(asset_class, str) or not asset_class:
            asset_class = ""
            issues.append(
                field_issue(
                    code="allocation.asset_type_missing",
                    kind="missing",
                    severity="warning",
                    section="assets",
                    entity_kind="asset",
                    entity_id=asset_ref,
                    field="asset_class",
                )
            )
        if explicit_asset_selection and not asset.active and asset.id not in held_asset_ids:
            issues.append(
                field_issue(
                    code="allocation.asset_inactive_not_buyable",
                    kind="unsupported",
                    severity="error",
                    section="assets",
                    entity_kind="asset",
                    entity_id=asset_ref,
                    field="active",
                )
            )
        rows.append(
            PortfolioPlannerSourceAsset(
                asset_id=asset_ref,
                source_asset_id=asset.id,
                name=asset.display_name,
                ticker=asset.identifier_ticker,
                asset_class=asset_class,
                icon_url=asset.icon_url,
                active=asset.active,
                provenance_id=MARKET_PROVENANCE_ID,
            )
        )
    return rows


def observed_currencies_by_broker(
    cash_by_broker: dict[int, dict[str, Decimal]],
    *,
    issues: list[PortfolioPlannerSourceIssue],
) -> dict[int, list[str]]:
    observed: dict[int, list[str]] = {}
    for broker_id, balances in cash_by_broker.items():
        currencies: list[str] = []
        for raw_currency in sorted(balances):
            currency = validated_currency(raw_currency)
            if currency is None:
                issues.append(
                    field_issue(
                        code="allocation.currency_spec_missing",
                        kind="missing",
                        severity="error",
                        section="brokers",
                        entity_kind="broker",
                        entity_id=broker_key(broker_id),
                        field="observed_currencies",
                    )
                )
                continue
            currencies.append(currency)
        observed[broker_id] = currencies
    return observed


def build_planner_brokers(
    access_rows: list,
    *,
    observed_currencies: dict[int, list[str]],
    issues: list[PortfolioPlannerSourceIssue],
) -> list[PortfolioPlannerSourceBroker]:
    rows: list[PortfolioPlannerSourceBroker] = []
    for access, broker in access_rows:
        if broker.id is None:
            continue
        broker_ref = broker_key(broker.id)
        rows.append(
            PortfolioPlannerSourceBroker(
                broker_id=broker_ref,
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
                provenance_id=BROKER_PROVENANCE_ID,
            )
        )
        if not broker.is_active:
            issues.append(
                field_issue(
                    code="allocation.broker_inactive",
                    kind="unsupported",
                    severity="warning",
                    section="brokers",
                    entity_kind="broker",
                    entity_id=broker_ref,
                    field="active",
                )
            )
        issues.append(
            field_issue(
                code="allocation.broker_execution_profile_unsupported",
                kind="unsupported",
                severity="error",
                section="brokers",
                entity_kind="broker",
                entity_id=broker_ref,
                field="execution_profile_status",
            )
        )
    return rows


def build_planner_holdings(
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
        holding_id = holding_key(asset_id, broker_id)
        rows.append(
            PortfolioPlannerSourceHolding(
                holding_id=holding_id,
                asset_id=asset_key(asset_id),
                broker_id=broker_key(broker_id),
                custody_quantity=custody_quantity,
                ownership_share=access.share_percentage,
                economic_quantity=custody_quantity * access.share_percentage,
                quantity_unit="asset_unit",
                provenance_id=PORTFOLIO_PROVENANCE_ID,
            )
        )
        if custody_quantity < 0:
            issues.append(
                field_issue(
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


def build_planner_cash_balances(
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
            currency = validated_currency(raw_currency)
            if currency is None:
                issues.append(
                    field_issue(
                        code="allocation.currency_spec_missing",
                        kind="missing",
                        severity="error",
                        section="cash_balances",
                        entity_kind="broker",
                        entity_id=broker_key(broker.id),
                        field="currency",
                    )
                )
                continue
            cash_id = cash_key(broker.id, currency)
            rows.append(
                PortfolioPlannerSourceCashBalance(
                    cash_id=cash_id,
                    broker_id=broker_key(broker.id),
                    currency=currency,
                    custody_amount=custody_amount,
                    ownership_share=access.share_percentage,
                    economic_amount=custody_amount * access.share_percentage,
                    provenance_id=PORTFOLIO_PROVENANCE_ID,
                )
            )
            if custody_amount < 0:
                issues.append(
                    field_issue(
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


def build_planner_prices(
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
        asset_ref = asset_key(asset.id)
        price = prices.get(asset.id)
        reference_date = price.date if price else None
        price_id = price_key(asset.id, reference_date or as_of)
        currency = validated_currency(price.currency if price else asset.currency)
        if price is None:
            issues.append(
                field_issue(
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
                field_issue(
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
                field_issue(
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
                field_issue(
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
                asset_id=asset_ref,
                amount=price.close if price else None,
                currency=currency,
                quote_base_quantity=quote_base_quantity,
                reference_date=reference_date,
                source=price.source_plugin_key if price else None,
                days_before_requested=(as_of - reference_date).days if reference_date else None,
                provenance_id=MARKET_PROVENANCE_ID,
            )
        )
    return rows
