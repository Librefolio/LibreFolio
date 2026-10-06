"""Why a scope asset was left out of a risk request: never priced, or not priced in the period.

Developer's decision of 29/09/2026. An asset excluded for `missing_price` that has no provider assigned
AND no price row at all has never been priced, and nothing will price it: the reason becomes
`no_price_source`, a permanent state the notice states in an informative tone. A provider that
returned nothing, or manual prices outside the period, leave it `missing_price` — occasional. (Outside
means after: rows before the period are carried into it, and the asset is not excluded at all.) A
missing FX rate is another cause altogether and keeps `missing_fx` whatever the provider.

Both facts come from one query per request, issued only when some exclusion is a missing price. The
service runs against rows this module writes to the test database and deletes afterwards.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, event
from sqlalchemy.ext.asyncio import AsyncSession

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from backend.app.db.models import Asset, AssetProviderAssignment, AssetType, PriceHistory, ProviderInputType  # noqa: E402
from backend.app.db.session import get_async_engine  # noqa: E402
from backend.app.schemas.risk import RiskAnalyticResult, RiskQueryRequest, RiskResultStatus  # noqa: E402
from backend.app.services.risk.service import RiskService  # noqa: E402

# A period of 2009 nothing else in the suite prices, and a currency nothing else stores a rate for.
PRICES_FROM = date(2009, 1, 19)
PERIOD_START = date(2009, 2, 2)
PERIOD_END = date(2009, 3, 31)
NO_RATE_CURRENCY = "LAK"
# When an asset is quoted: every day from a fortnight before the period to its end, only on days
# after it (manual prices entered later), or never.
QUOTE_SPANS: dict[str, tuple[date, date] | None] = {
    "period": (PRICES_FROM, PERIOD_END),
    "after": (date(2009, 5, 4), date(2009, 5, 29)),
    "never": None,
}

# key: (currency of its quotes, when it is quoted, provider assigned)
ASSETS: dict[str, tuple[str, str, bool]] = {
    "priced": ("EUR", "period", False),
    "priced_sourced": ("EUR", "period", True),
    "unsourced": ("EUR", "never", False),
    "sourced": ("EUR", "never", True),
    "manual_after": ("EUR", "after", False),
    "fx_unsourced": (NO_RATE_CURRENCY, "period", False),
    "fx_sourced": (NO_RATE_CURRENCY, "period", True),
}


def close(index: int, day: date) -> Decimal:
    """A drifting price with its own period per asset, so no two series are flat or identical."""
    offset = (day - PRICES_FROM).days
    return Decimal("100") + Decimal(offset % (5 + index)) + Decimal(offset) / Decimal("10")


def quote_days(when: str) -> list[date]:
    span = QUOTE_SPANS[when]
    if span is None:
        return []
    first, last = span
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


@dataclass(frozen=True)
class ReasonAssets:
    ids: dict[str, int]
    names: dict[str, str]


def session() -> AsyncSession:
    return AsyncSession(get_async_engine(), expire_on_commit=False)


@pytest.fixture(scope="module")
def reason_assets():
    marker = uuid4().hex

    async def setup() -> ReasonAssets:
        async with session() as db:
            assets = {key: Asset(display_name=f"Exclusion {key} {marker}", currency=currency, asset_type=AssetType.STOCK, active=True) for key, (currency, _quoted, _sourced) in ASSETS.items()}
            db.add_all(assets.values())
            await db.flush()
            db.add_all(PriceHistory(asset_id=assets[key].id, date=day, close=close(index, day), currency=currency, source_plugin_key="exclusion_test") for index, (key, (currency, quoted, _sourced)) in enumerate(ASSETS.items()) for day in quote_days(quoted))
            db.add_all(AssetProviderAssignment(asset_id=assets[key].id, provider_code="mockprov", identifier=f"exclusion-{key}-{marker}", identifier_type=ProviderInputType.AUTO_GENERATED) for key, (_currency, _quoted, sourced) in ASSETS.items() if sourced)
            await db.commit()
            return ReasonAssets(ids={key: asset.id for key, asset in assets.items()}, names={key: asset.display_name for key, asset in assets.items()})

    async def cleanup(data: ReasonAssets) -> None:
        async with session() as db:
            owned = list(data.ids.values())
            await db.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(owned)))
            await db.execute(delete(PriceHistory).where(PriceHistory.asset_id.in_(owned)))
            await db.execute(delete(Asset).where(Asset.id.in_(owned)))
            await db.commit()

    data = asyncio.run(setup())
    yield data
    asyncio.run(cleanup(data))


def asset_set_request(asset_ids: list[int]) -> RiskQueryRequest:
    """Two analytics that read the per-asset series, so one request can be told from one analytic."""
    return RiskQueryRequest.model_validate(
        {
            "scope": {"kind": "asset_set", "asset_ids": asset_ids},
            "date_range": {"start": PERIOD_START.isoformat(), "end": PERIOD_END.isoformat()},
            "target_currency": "EUR",
            "mode": "historical",
            "analytics": [
                {"instance_id": "correlation", "analytic_code": "correlation"},
                {"instance_id": "kpi", "analytic_code": "asset_set_kpi"},
            ],
        }
    )


async def run(asset_ids: list[int]) -> dict[str, RiskAnalyticResult]:
    async with session() as db:
        response = await RiskService(db).execute(user_id=1, request=asset_set_request(asset_ids))
    return {item.instance_id: item for item in response.items}


@contextmanager
def provider_reads() -> Iterator[list[str]]:
    """Every SQL statement that reads the provider assignments while the block runs.

    Stored prices are read by the series preparation as well, so the assignments table is what
    identifies the read that qualifies a missing price.
    """
    statements: list[str] = []
    engine = get_async_engine().sync_engine

    def record(_connection, _cursor, statement, _parameters, _context, _executemany) -> None:
        if "asset_provider_assignments" in statement.lower():
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


@pytest.mark.asyncio
async def test_a_missing_price_is_told_apart_by_whether_anything_could_ever_price_it(reason_assets):
    ids = reason_assets.ids

    results = await run(list(ids.values()))

    correlation = results["correlation"]
    assert correlation.output is not None, correlation.error
    # Presence barrier: quotes in the period keep an asset in, with or without a provider.
    assert set(correlation.output.asset_ids) == {ids["priced"], ids["priced_sourced"]}
    reasons = {item.asset_id: item.reason for item in correlation.metadata.excluded_assets}
    assert reasons == {
        # No provider and not a single price row: never priced, and nothing will price it.
        ids["unsourced"]: "no_price_source",
        # A provider that gave nothing for the period, or manual prices entered only after it.
        ids["sourced"]: "missing_price",
        ids["manual_after"]: "missing_price",
        # Another cause altogether, whatever the provider.
        ids["fx_unsourced"]: "missing_fx",
        ids["fx_sourced"]: "missing_fx",
    }
    # One answer per request: every analytic that reads the series states the same reasons.
    assert {item.asset_id: item.reason for item in results["kpi"].metadata.excluded_assets} == reasons


@pytest.mark.asyncio
async def test_each_reason_gets_its_own_sentence_naming_its_assets(reason_assets):
    ids, names = reason_assets.ids, reason_assets.names

    results = await run(list(ids.values()))

    correlation = results["correlation"]
    assert correlation.status == RiskResultStatus.PARTIAL
    by_reason = {warning.details["reason"]: warning for warning in correlation.warnings if warning.code == "assets_excluded"}
    assert {reason: (warning.message_i18n_key, sorted(warning.details["asset_ids"])) for reason, warning in by_reason.items()} == {
        "no_price_source": ("risk.warnings.assets_excluded_no_price_source", [ids["unsourced"]]),
        "missing_price": ("risk.warnings.assets_excluded_missing_price", sorted([ids["sourced"], ids["manual_after"]])),
        "missing_fx": ("risk.warnings.assets_excluded_missing_fx", sorted([ids["fx_unsourced"], ids["fx_sourced"]])),
    }
    assert by_reason["no_price_source"].message_params == {"names": names["unsourced"], "count": 1}
    occasional = by_reason["missing_price"].message_params
    assert (sorted(occasional["names"].split(", ")), occasional["count"]) == (sorted([names["sourced"], names["manual_after"]]), 2)


@pytest.mark.asyncio
async def test_the_price_sources_are_read_once_and_in_one_statement(reason_assets):
    ids = reason_assets.ids

    with provider_reads() as statements:
        results = await run([ids["priced"], ids["unsourced"], ids["sourced"], ids["manual_after"], ids["priced_sourced"]])

    # Two analytics and three missing prices to qualify: still a single read, and it asks both facts.
    assert {item.asset_id for item in results["correlation"].metadata.excluded_assets} == {ids["unsourced"], ids["sourced"], ids["manual_after"]}
    (read,) = statements
    assert "price_history" in read.lower(), read


@pytest.mark.asyncio
async def test_no_price_source_is_read_when_no_exclusion_is_a_missing_price(reason_assets):
    ids = reason_assets.ids

    with provider_reads() as statements:
        results = await run([ids["priced"], ids["fx_unsourced"], ids["fx_sourced"]])

    # Presence barrier: there are exclusions — only none of them is a missing price.
    assert {item.reason for item in results["correlation"].metadata.excluded_assets} == {"missing_fx"}
    assert statements == []


@pytest.mark.asyncio
async def test_no_price_source_is_read_when_nothing_is_excluded(reason_assets):
    ids = reason_assets.ids

    with provider_reads() as statements:
        results = await run([ids["priced"], ids["priced_sourced"]])

    assert all(result.output is not None and result.metadata.excluded_assets == [] for result in results.values()), results
    assert statements == []
