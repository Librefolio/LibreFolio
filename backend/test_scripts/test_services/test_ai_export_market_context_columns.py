"""78 L6 S2 — a market row declares only the columns its component reports.

One market row served four components, and seven columns were filled only on a flag: the ones a component did not
turn on came out `null` in every row, and the prompt named them on `omitted_null_columns`, «explicitly unavailable». Now each
component has its own row, and a column it does not report is not in its payload.

- MC-01: the contract, per component: the exact set of columns its row declares; the portfolio weight only where there
  is a portfolio (the asset and FX rows had it `null` too).
- MC-02: a row built for a component carries exactly those columns, whatever came in (all seven extension signals and
  a weight supplied): the flags are gone, the row's class decides.
- MC-03: a declared column that cannot be computed stays in the row as `None` (really unavailable, and the prompt still
  says so): `ema_200` with three closes, `ema_20` of the asset with no signal.
- MC-04: every row prints its columns in the one column order (inheritance would put a row's own columns last).
- MC-05: the returns of the row are the one `price_return` (78 L6 S2b), and the four components that print them are
  over their 1.3.0 version, so their figures may change. The texts the prompt prints for these values are pinned in
  `snapshotDataRendererL6.test.ts`, on the same cases.

Isolation: PURE (no database, no server, no network): models and the row builder only.

Runs in ``./dev.py test services ai-export-pure``; alone:
``pipenv run python -m pytest -q backend/test_scripts/test_services/test_ai_export_market_context_columns.py``.
"""

from __future__ import annotations

from datetime import date

import pytest

from backend.app.services.ai_export.components import technical_context
from backend.app.services.ai_export.components.technical_context import (
    MARKET_CONTEXT_COLUMN_ORDER,
    AssetPositionMarketContextRow,
    FxMarketContextRow,
    MarketContextRowBase,
    TechnicalMarketContextRow,
)

COMMON_COLUMNS = frozenset(
    {
        "entity_id",
        "value_unit",
        "observation_count",
        "available_start",
        "available_end",
        "current_value",
        "current_date",
        "return_1m_ratio",
        "return_3m_ratio",
        "return_period_ratio",
        "minimum_value",
        "minimum_date",
        "maximum_value",
        "maximum_date",
        "ema_50",
        "ema_200",
        "kama_20",
        "rsi_14",
        "rsi_14_state",
        "daily_return_volatility_ratio",
        "current_vs_ema_50",
        "current_vs_ema_200",
        "ema_50_vs_ema_200",
    }
)
PORTFOLIO_COLUMNS = COMMON_COLUMNS | {"portfolio_weight_ratio", "natr_14_percent"}
# No NATR in the FX row: a rate has no highs and lows, so the pair's signals never ask for it
ASSET_COLUMNS = COMMON_COLUMNS | {"ema_20", "natr_14_percent", "atr_14", "bollinger_lower", "bollinger_middle", "bollinger_upper"}
FX_COLUMNS = COMMON_COLUMNS | {"ema_20", "ppo_12_26_9_percent", "roc_20_percent"}

#: The contract: each market-context component and the columns of its row.
EXPECTED_COLUMNS = {
    "portfolio.asset_market_context": PORTFOLIO_COLUMNS,
    "broker.asset_market_context": PORTFOLIO_COLUMNS,
    "asset.position_market_context": ASSET_COLUMNS,
    "fx.market_summary": FX_COLUMNS,
}
EXTENSION_COLUMNS = (PORTFOLIO_COLUMNS | ASSET_COLUMNS | FX_COLUMNS) - COMMON_COLUMNS
ROW_MODELS = [TechnicalMarketContextRow, AssetPositionMarketContextRow, FxMarketContextRow]


def _spec(component_id: str):
    return next(spec for spec in technical_context.TECHNICAL_CONTEXT_COMPONENTS if spec.component_id == component_id)


def _row_model(component_id: str) -> type[MarketContextRowBase]:
    entities = _spec(component_id).output_model.model_fields["entities"].annotation
    row_model, _ellipsis = entities.__args__
    return row_model


@pytest.mark.parametrize("component_id", sorted(EXPECTED_COLUMNS))
def test_mc01_each_component_declares_exactly_its_columns(component_id):
    assert set(_row_model(component_id).model_fields) == EXPECTED_COLUMNS[component_id]


def test_mc01_the_asset_component_is_at_version_2():
    """The asset's row lost PPO, ROC and the weight and gained the volatility of S1: a builder change over the released v1."""
    assert _spec("asset.position_market_context").version == 2


def _points(count: int) -> tuple[tuple[date, float], ...]:
    return tuple((date(2026, 9, day), 100.0 + day) for day in range(1, count + 1))


@pytest.mark.parametrize("row_model", ROW_MODELS)
def test_mc02_a_row_carries_exactly_its_declared_columns(row_model, monkeypatch):
    # Every extension signal is supplied: the row's class alone decides which columns it carries
    values = {"ema_20": 1.0, "natr_14": 1.5, "atr_14": 2.0, "ppo_12_26_9": 3.0, "roc_20": 4.0}
    monkeypatch.setattr(technical_context, "_latest_scalar", lambda result, key: (date(2026, 9, 3), values[result]) if result in values else None)
    monkeypatch.setattr(technical_context, "_latest_band", lambda result, key: (date(2026, 9, 3), 1.0, 2.0, 3.0) if result == "bollinger_20_2" else None)
    monkeypatch.setattr(technical_context, "_signal_map", lambda results: {code: code for code in ("ema_20", "natr_14", "atr_14", "ppo_12_26_9", "roc_20", "bollinger_20_2")})

    row = technical_context._market_context_row(row_model, entity_id="asset:1", value_unit="EUR", points=_points(3), results=(), period_start=date(2026, 9, 1), period_end=date(2026, 9, 3), portfolio_weight_ratio=0.5)

    dumped = row.model_dump(mode="json")
    assert set(dumped) == set(row_model.model_fields)
    for column in set(row_model.model_fields) & EXTENSION_COLUMNS:
        assert dumped[column] is not None, f"{column} was supplied and declared: it is filled"


@pytest.mark.parametrize("row_model", ROW_MODELS)
def test_mc03_a_declared_column_that_cannot_be_computed_stays_unavailable(row_model):
    row = technical_context._market_context_row(row_model, entity_id="asset:1", value_unit="EUR", points=_points(3), results=(), period_start=date(2026, 9, 1), period_end=date(2026, 9, 3))

    dumped = row.model_dump(mode="json")
    # No signal came in: three closes do not make an EMA 200. The column is declared, so it stays, null
    assert "ema_200" in dumped and dumped["ema_200"] is None
    if "ema_20" in row_model.model_fields:
        assert "ema_20" in dumped and dumped["ema_20"] is None


@pytest.mark.parametrize("row_model", ROW_MODELS)
def test_mc04_every_row_prints_its_columns_in_the_one_order(row_model):
    assert set(row_model.model_fields) <= set(MARKET_CONTEXT_COLUMN_ORDER), "a column missing from the order would be dropped"
    row = technical_context._market_context_row(row_model, entity_id="asset:1", value_unit="EUR", points=_points(3), results=(), period_start=date(2026, 9, 1), period_end=date(2026, 9, 3))

    keys = list(row.model_dump(mode="json"))
    assert keys == [name for name in MARKET_CONTEXT_COLUMN_ORDER if name in row_model.model_fields]


#: The versions of 1.3.0 of the components that print `_return_ratio`; each is over it, so its figures may change.
RELEASED_IN_1_3_0 = dict.fromkeys(EXPECTED_COLUMNS, 1)


@pytest.mark.parametrize("component_id", sorted(RELEASED_IN_1_3_0))
def test_mc05_every_component_that_prints_the_return_is_over_its_1_3_0_version(component_id):
    assert _spec(component_id).version > RELEASED_IN_1_3_0[component_id]


#: Two values, and `price_return` of the second over the first: the same cases as `snapshotDataRendererL6.test.ts`.
RETURN_CASES = [
    (100.00, 101.50, 0.015),
    (285.17, 264.10, -0.07388575235824245),
    (1.1014, 1.1223, 0.018975848919556927),
    (59137.16, 58564.98, -0.009675473086634528),
    (4.50, 4.14, -0.08),
    (288.00, 272.97, -0.0521875),
]


@pytest.mark.parametrize(("start", "end", "expected"), RETURN_CASES)
def test_mc05_the_return_of_a_row_is_the_one_price_return(start, end, expected):
    points = ((date(2026, 9, 1), start), (date(2026, 9, 2), end))
    assert technical_context._return_ratio(points, date(2026, 9, 1)) == expected


def test_mc05_a_zero_start_gives_no_return():
    points = ((date(2026, 9, 1), 0.0), (date(2026, 9, 2), 5.0))
    assert technical_context._return_ratio(points, date(2026, 9, 1)) is None
