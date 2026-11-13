"""The small Rebalancer cases computed by hand (specifica-REB §11): T1, T4, T5, T6 and their reduced variants.

Not collected by pytest (leading underscore), like ``_pac_exhaustive_oracle.py``. One builder per case returns the exact
scenario; the numbers each case expects are written next to the test that reads them, as exact fractions. Lot B1 of project
67 brings them in; B2 (SCIP), B3 (the planner) and T0 reuse them.

Every case: valuation currency EUR, one Broker ``broker:x``, Assets priced 1 EUR a unit, so a holding of ``q`` units is
worth ``q`` EUR and the arithmetic of the specification reads off directly. Purchases go by amount, in steps of
``amount_step`` EUR, with a fixed fee of 5 EUR an order. Sales are not part of «Invest only».
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from backend.app.services.pac_allocator import models as pac_models
from backend.app.services.pac_allocator.numeric import ExactRatio

R = ExactRatio
ZERO = R(0)
ONE = R(1)
CENT = R(1, 100)
AS_OF = date(2026, 11, 13)
CAPTURED_AT = datetime(2026, 11, 13, 20, 0, tzinfo=UTC)
PROVENANCE = "provenance:reb-small"
BROKER = "broker:x"
FEE = R(5)


def money(amount: ExactRatio, currency: str = "EUR") -> pac_models.ExactMoney:
    return pac_models.ExactMoney(amount=amount, currency=currency)


def _asset(asset_id: str, price: ExactRatio, currency: str = "EUR") -> pac_models.ExactAsset:
    return pac_models.ExactAsset(
        asset_id=asset_id,
        identity_kind="manual",
        source_asset_id=None,
        name=asset_id,
        ticker=None,
        asset_class="fund",
        quote=pac_models.ExactAssetQuote(price=money(price, currency), quote_base_quantity=ONE, provenance_id=PROVENANCE),
        exposures=(),
    )


def _holding(asset_id: str, quantity: ExactRatio) -> pac_models.ExactHolding:
    return pac_models.ExactHolding(
        holding_id=f"holding:{asset_id}",
        asset_id=asset_id,
        broker_id=BROKER,
        custody_quantity=quantity,
        economic_share=ONE,
        economic_quantity=quantity,
        planning_quantity=quantity,
        provenance_id=PROVENANCE,
    )


def buy_decision(asset_id: str) -> str:
    """The decision ID of the buy route of ``asset_id``."""
    return f"buy:route:buy:{asset_id}"


def scenario(
    name: str,
    *,
    holdings: dict[str, ExactRatio],
    cash: ExactRatio,
    weights: dict[str, ExactRatio],
    prices: dict[str, ExactRatio] | None = None,
    whole_units: frozenset[str] = frozenset(),
    amount_step: ExactRatio = ONE,
    usd_asset: str | None = None,
    caps: dict[str, ExactRatio] | None = None,
    fee_rate: ExactRatio = ZERO,
    fee_cap: ExactRatio | None = None,
    **scenario_fields,
) -> pac_models.ExactPlannerScenario:
    """A Rebalancer «Invest only» scenario on one Broker, by the conventions of the module docstring.

    ``whole_units`` buy by whole units instead of by amount; ``usd_asset`` names an Asset quoted in USD (weight zero), whose
    buy route gives the Broker an EUR → USD conversion decision. ``caps`` bound the purchase of an Asset by amount (EUR), which
    keeps the oracle's domain small; ``fee_rate`` adds a proportional part to the 5 EUR fixed fee, ``fee_cap`` caps that part. ``scenario_fields`` go to ``ExactPlannerScenario`` as they are (the fidelity, the cash
    entries).
    """
    price_by_asset = dict.fromkeys(weights, ONE) | (prices or {})
    currencies = {"EUR"} | ({"USD"} if usd_asset else set())
    capabilities = [pac_models.ExactOrderCapability(capability_id="capability:eur-amount", kind="monetary_amount", order_step=amount_step)]
    if whole_units:
        capabilities.append(pac_models.ExactOrderCapability(capability_id="capability:eur-units", kind="whole_quantity", order_step=ONE))
    if usd_asset:
        capabilities.append(pac_models.ExactOrderCapability(capability_id="capability:usd-units", kind="whole_quantity", order_step=ONE))
    fees = []
    for capability in capabilities:
        currency = "USD" if capability.capability_id.startswith("capability:usd") else "EUR"
        fees.append(
            pac_models.ExactFeeSchedule(
                fee_schedule_id=f"fee:{capability.capability_id}",
                capability_id=capability.capability_id,
                side="buy",
                fixed_fee=money(FEE, currency),
                proportional_rate=fee_rate,
                minimum_fee=money(ZERO, currency),
                maximum_fee=None if fee_cap is None else money(fee_cap, currency),
            )
        )
    broker = pac_models.ExactBroker(
        broker_id=BROKER,
        identity_kind="manual",
        source_broker_id=None,
        name=BROKER,
        active=True,
        provenance_id=PROVENANCE,
        capabilities=tuple(sorted(capabilities, key=lambda item: item.capability_id)),
        fee_schedules=tuple(sorted(fees, key=lambda item: (item.capability_id, item.side, item.fee_schedule_id))),
        conversion_mode="manual",
    )
    assets = [_asset(asset_id, price_by_asset[asset_id], "USD" if asset_id == usd_asset else "EUR") for asset_id in weights]
    routes = []
    for asset_id in weights:
        capability_id = "capability:usd-units" if asset_id == usd_asset else "capability:eur-units" if asset_id in whole_units else "capability:eur-amount"
        routes.append(
            pac_models.ExactOrderRoute(
                route_id=f"route:buy:{asset_id}",
                broker_id=BROKER,
                asset_id=asset_id,
                capability_id=capability_id,
                fee_schedule_id=f"fee:{capability_id}",
                side="buy",
                minimum_if_active=pac_models.ExactOrderMinimum(kind="none", value=ZERO, currency=None),
                cap=pac_models.ExactOrderCap(kind="notional", value=caps[asset_id], currency="EUR") if caps and asset_id in caps else None,
                execution_margin_rate=ZERO,
                priority=0,
                provenance_id=PROVENANCE,
            )
        )
    return pac_models.ExactPlannerScenario(
        snapshot=pac_models.ExactSnapshot(snapshot_id=f"reb-small:{name}", draft_revision=1, captured_at=CAPTURED_AT),
        product="rebalancer",
        policy="invest_only",
        as_of_date=AS_OF,
        valuation_currency="EUR",
        currency_specs=tuple(pac_models.ExactCurrencySpec(currency=currency, minor_unit=CENT) for currency in sorted(currencies)),
        provenance=(pac_models.ExactProvenance(provenance_id=PROVENANCE, kind="manual", label="small cases", entered_at=CAPTURED_AT, domain=None, source_ref=None, source_label=None, captured_at=CAPTURED_AT),),
        # One USD is worth one EUR at the mid rate, and the spread makes every conversion lose: 1% of what it moves.
        fx_rates=(pac_models.ExactFxRate(pair_first="EUR", pair_second="USD", rate=ONE),) if usd_asset else (),
        fx_spread_rate=R(1, 100) if usd_asset else ZERO,
        assets=tuple(sorted(assets, key=lambda item: item.asset_id)),
        brokers=(broker,),
        holdings=tuple(sorted((_holding(asset_id, quantity) for asset_id, quantity in holdings.items() if quantity), key=lambda item: item.holding_id)),
        existing_cash=((pac_models.ExactExistingCash(cash_id="cash:x:eur", broker_id=BROKER, available=money(cash), selected=money(cash), provenance_id=PROVENANCE),) if cash else ()),
        contributions=(),
        funding_routes=(),
        order_routes=tuple(sorted(routes, key=lambda item: item.route_id)),
        target_weights=tuple(sorted((pac_models.ExactTargetWeight(asset_id=asset_id, weight=weight) for asset_id, weight in weights.items()), key=lambda item: item.asset_id)),
        sell_context=None,
        **({"target_fidelity": pac_models.BALANCED_FIDELITY} | scenario_fields),
    )


HALF = R(1, 2)


def t1(**fields) -> pac_models.ExactPlannerScenario:
    """T1: A 5 040, B 4 960, no cash; the best plan is no operation."""
    return scenario("t1", holdings={"asset:a": R(5040), "asset:b": R(4960)}, cash=ZERO, weights={"asset:a": HALF, "asset:b": HALF}, **fields)


def t4(*, amount_step: ExactRatio = ONE, weights_override: dict[str, ExactRatio] | None = None, **fields) -> pac_models.ExactPlannerScenario:
    """T4: A 5 000, B 4 800, cash 200; the best plan buys 195 of B (5 EUR of fee). ``weights_override`` replaces the Asset
    weights, for the variants where a cash cell holds part of the target."""
    weights = weights_override or {"asset:a": HALF, "asset:b": HALF}
    return scenario("t4", holdings={"asset:a": R(5000), "asset:b": R(4800)}, cash=R(200), weights=weights, amount_step=amount_step, **fields)


def t5(*, amount_step: ExactRatio = ONE, **fields) -> pac_models.ExactPlannerScenario:
    """T5: A 5 000, B 4 900, cash 100; at «Balanced» the best plan is no operation (a 5 EUR fee against a penalty of 2)."""
    return scenario("t5", holdings={"asset:a": R(5000), "asset:b": R(4900)}, cash=R(100), weights={"asset:a": HALF, "asset:b": HALF}, amount_step=amount_step, **fields)


def t6(*, with_usd: bool = False, **fields) -> pac_models.ExactPlannerScenario:
    """T6 (specifica §6.2): one Asset at 4 000 EUR a unit, one unit held, cash 6 000, ``λ = 4``; the best plan buys one unit.

    ``with_usd`` adds a USD Asset with weight zero priced out of reach: its route gives the Broker an EUR → USD conversion,
    so a plan can waste money on a conversion that buys nothing.
    """
    weights = {"asset:a": ONE} | ({"asset:usd": ZERO} if with_usd else {})
    prices = {"asset:a": R(4000)} | ({"asset:usd": R(100_000)} if with_usd else {})
    return scenario(
        "t6-usd" if with_usd else "t6",
        holdings={"asset:a": ONE},
        cash=R(6000),
        weights=weights,
        prices=prices,
        whole_units=frozenset({"asset:a"}),
        usd_asset="asset:usd" if with_usd else None,
        **fields,
    )


def t4_cash_over_target(*, fee_rate: ExactRatio = ZERO, fee_cap: ExactRatio | None = None, **fields) -> pac_models.ExactPlannerScenario:
    """T4 with 300 of cash and a target on it: A 50 %, B 48 %, the cell 2 %. ``F`` = 10 100, so the cell aims at 202 while it
    holds 300: a plan that leaves it above its target is where a model could lower the cell's cash for free and shorten
    ``D`` (the slack of a fee or of a posting rounded against the plan)."""
    return scenario(
        "t4-cash-over-target",
        holdings={"asset:a": R(5000), "asset:b": R(4800)},
        cash=R(300),
        weights={"asset:a": HALF, "asset:b": R(12, 25)},
        fee_rate=fee_rate,
        fee_cap=fee_cap,
        **({"cash_entries": (pac_models.ExactCashEntry(broker_id=BROKER, currency="EUR", minimum=None, maximum=None, weight=R(1, 50)),)} | fields),
    )
