"""RN-25 — the rates scenario of an asset: its price moved by −modified duration × Δy, the duration read in its profile.

The consultant's decisions (18/11/2026): the scenario exists where the profile holds a `modified_duration` (not by asset
type); rates up and down by the same steps, with opposite figures; no duration is an unavailable answer that says why
(`no_modified_duration`), never a zero. The analytic reads no price, so no observation gate applies to it.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from backend.app.db.models import Asset, AssetProfileUpdate, AssetType
from backend.app.schemas.risk.scope import RiskAnalyticRequest, RiskQueryRequest
from backend.app.schemas.risk.vocabulary import RiskErrorCode, RiskMode, RiskOutputKind, RiskResultStatus, RiskScopeKind
from backend.app.services.assets.profile.catalogue import normalize_value
from backend.app.services.financial_math.bond_duration import duration_price_change
from backend.app.services.risk import scope as risk_scope_module
from backend.app.services.risk import service as risk_service_module
from backend.app.services.risk.base import RiskAssetClassification, RiskUnavailableError
from backend.app.services.risk.plan import AnalyticPlan, reads_asset_profile, reads_no_price_series
from backend.app.services.risk.results import available_observations
from backend.app.services.risk.service import RiskService
from backend.app.services.risk_plugins.rate_shock.plugin import RateShockAnalytic, RateShockParams
from backend.test_scripts.test_services.test_risk_analytics import make_context
from backend.test_scripts.test_services.test_risk_service import NamesDb, make_prepared_set, scope_inputs

STEPS = (0.005, 0.01, 0.02, -0.005, -0.01, -0.02)
BOND_ID = 7


def _bond_context(classification: RiskAssetClassification):
    return make_context(
        {BOND_ID: [0.001, -0.002, 0.0015, 0.0005] * 6},
        scope_kind=RiskScopeKind.ASSET,
        mode=RiskMode.CURRENT_COMPOSITION,
        scope_asset_ids=(BOND_ID,),
        primary_asset_id=BOND_ID,
        asset_classifications={BOND_ID: classification},
    )


def test_the_declaration_is_one_asset_in_the_current_composition():
    assert RateShockAnalytic.analytic_code == "rate_shock"
    assert RateShockAnalytic.supported_scopes == (RiskScopeKind.ASSET,)
    assert RateShockAnalytic.output_kind == RiskOutputKind.RATE_SHOCK


def test_each_step_moves_the_price_by_minus_the_duration_times_the_move_up_and_down():
    classification = RiskAssetClassification(asset_class="BOND", modified_duration=1.8, modified_duration_read_on=date(2026, 11, 8), modified_duration_source="borsa_italiana")
    output = RateShockAnalytic().compute(RateShockParams(yield_changes=list(STEPS)), _bond_context(classification)).output

    assert output.modified_duration == 1.8
    assert output.duration_read_on == date(2026, 11, 8)
    assert output.duration_source == "borsa_italiana"
    assert [scenario.yield_change for scenario in output.scenarios] == list(STEPS)
    for scenario in output.scenarios:
        assert scenario.price_change == duration_price_change(1.8, scenario.yield_change)
    by_move = {scenario.yield_change: scenario.price_change for scenario in output.scenarios}
    assert by_move[0.01] == pytest.approx(-0.018)
    assert by_move[-0.01] == pytest.approx(0.018), "rates down by one point: the opposite figure"


def test_no_duration_in_the_profile_is_unavailable_and_says_why():
    for classification in (RiskAssetClassification(asset_class="BOND"), RiskAssetClassification(asset_class="STOCK")):
        with pytest.raises(RiskUnavailableError) as raised:
            RateShockAnalytic().compute(RateShockParams(yield_changes=[0.01]), _bond_context(classification))
        assert raised.value.code == RiskErrorCode.DATA_UNAVAILABLE
        assert raised.value.details == {"reason": "no_modified_duration"}


@pytest.mark.parametrize("yield_changes", [[], [0.01, 0.01], [0.0], [0.021], [-0.021], [float("nan")], [0.01] * 13])
def test_a_move_list_that_is_not_one_is_refused(yield_changes):
    with pytest.raises(ValidationError):
        RateShockParams(yield_changes=yield_changes)


def test_the_scenario_reads_the_asset_profile_and_no_observation_gate():
    request = RiskAnalyticRequest(instance_id="rates", analytic_code="rate_shock", parameters={"yield_changes": [0.01]})
    plan = AnalyticPlan(request=request, analytic_class=RateShockAnalytic, analytic=RateShockAnalytic(), params=RateShockParams(yield_changes=[0.01]))
    assert reads_asset_profile(plan)
    assert reads_no_price_series(plan), "the series' data quality, history warnings and exclusions are not the scenario's"
    assert available_observations(plan, _bond_context(RiskAssetClassification(asset_class="BOND"))) is None


@asynccontextmanager
async def _bond_book(directory):
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'rn25_risk.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            assets = {
                "btp": Asset(display_name="RN25 BTP", currency="EUR", asset_type=AssetType.BOND),
                "unread": Asset(display_name="RN25 bond without duration", currency="EUR", asset_type=AssetType.BOND),
                "garbled": Asset(display_name="RN25 unreadable duration", currency="EUR", asset_type=AssetType.BOND),
            }
            session.add_all(assets.values())
            await session.flush()

            def row(name, value, day, *, raw=False):
                text = value if raw else json.dumps(normalize_value("modified_duration", value))
                return AssetProfileUpdate(asset_id=assets[name].id, key="modified_duration", value=text, source="borsa_italiana", read_on=day)

            session.add_all([row("btp", "1.95", date(2026, 10, 1)), row("btp", "1.8", date(2026, 11, 8)), row("garbled", '"soon"', date(2026, 11, 8), raw=True)])
            await session.commit()
            yield engine, {name: asset.id for name, asset in assets.items()}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_the_duration_is_the_profile_reading_holding_the_analysis_day(tmp_path):
    async with _bond_book(tmp_path) as (engine, ids):
        async with AsyncSession(engine, expire_on_commit=False) as session:
            loaded = await risk_scope_module.load_asset_classifications(session, tuple(ids.values()), date(2026, 11, 18))
            before_any_reading = await risk_scope_module.load_asset_classifications(session, (ids["btp"],), date(2026, 9, 1))

    btp = loaded[ids["btp"]]
    assert btp.modified_duration == pytest.approx(1.8), "the latest reading at or before the day"
    assert btp.modified_duration_read_on == date(2026, 11, 8)
    assert btp.modified_duration_source == "borsa_italiana"
    assert loaded[ids["unread"]].modified_duration is None
    garbled = loaded[ids["garbled"]]
    assert garbled.modified_duration is None and garbled.modified_duration_read_on is None, "an unreadable value is no duration"
    early = before_any_reading[ids["btp"]]
    assert (early.modified_duration, early.modified_duration_read_on) == (pytest.approx(1.95), date(2026, 10, 1)), "before the first reading: the first one, with its own day (D3's rule)"


async def _execute_rate_shock(monkeypatch, classification: RiskAssetClassification):
    """One `rate_shock` through `RiskService.execute` on asset 1, its profile handed in by the scope (`load_asset_classifications`)."""
    service = RiskService(db=NamesDb({1: "RN25 bond"}))
    prepared = make_prepared_set({1: [0.0] * 20})

    async def fake_scope(_db, **_kwargs):
        return scope_inputs((1,))

    async def fake_assets(_db, _asset_ids):
        return {1}

    async def fake_prepare(_db, **_kwargs):
        return prepared

    async def fake_classifications(_db, _asset_ids, _day):
        return {1: classification}

    monkeypatch.setattr(risk_service_module, "load_scope_inputs", fake_scope)
    monkeypatch.setattr(risk_service_module, "load_existing_asset_ids", fake_assets)
    monkeypatch.setattr(risk_service_module, "prepare_asset_series", fake_prepare)
    monkeypatch.setattr(risk_service_module, "load_asset_classifications", fake_classifications)
    response = await service.execute(
        user_id=7,
        request=RiskQueryRequest.model_validate(
            {
                "scope": {"kind": "asset", "asset_id": 1},
                "date_range": {"start": "2026-01-02", "end": "2026-01-21"},
                "target_currency": "EUR",
                "mode": "current_composition",
                "composition_policy": "current_buy_and_hold",
                "analytics": [{"instance_id": "rates", "analytic_code": "rate_shock", "parameters": {"yield_changes": [0.01, -0.01]}}],
            }
        ),
    )
    return response.items[0]


@pytest.mark.asyncio
async def test_through_the_service_a_duration_gives_the_scenarios(monkeypatch):
    result = await _execute_rate_shock(monkeypatch, RiskAssetClassification(asset_class="BOND", modified_duration=1.8, modified_duration_read_on=date(2026, 1, 15), modified_duration_source="borsa_italiana"))

    assert result.status == RiskResultStatus.OK
    assert [(scenario.yield_change, scenario.price_change) for scenario in result.output.scenarios] == [(0.01, pytest.approx(-0.018)), (-0.01, pytest.approx(0.018))]
    assert result.output.duration_read_on == date(2026, 1, 15)
    assert result.metadata.params == {"yield_changes": [0.01, -0.01]}


@pytest.mark.asyncio
async def test_through_the_service_no_duration_is_unavailable_with_its_reason_on_the_result(monkeypatch):
    result = await _execute_rate_shock(monkeypatch, RiskAssetClassification(asset_class="BOND"))

    assert result.status == RiskResultStatus.UNAVAILABLE
    assert result.output is None
    assert result.error.code == RiskErrorCode.DATA_UNAVAILABLE
    assert result.error.details == {"reason": "no_modified_duration"}
