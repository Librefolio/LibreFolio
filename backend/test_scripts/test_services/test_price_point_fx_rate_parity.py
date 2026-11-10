"""MF-A13, financial math's parity: a converted price point is its native price times the day's unit rate — the one formula
of the portfolio engine — and that changes no value anyone reads rounded.

Why. Before MF-A13 the price query took a point's close from ``convert_bulk`` (the native close times the stored rate on a
direct pair, divided by it on an inverse one) and scaled open, high and low by ``close_converted / close``. The engine
values the same price as ``amount × AskedDayRates[(source, target, day)]``, the unit rate of the day's step
(``fx.conversion.unit_rate_steps``: the stored rate on a direct pair, one over it on an inverse one). On an inverse pair
the two differ at the last of the 28 significant digits: the chart close was not the number the valuation used. MF-A13
(X) adds ``FAPricePoint.fx_rate``, the day's step, and makes close, open, high and low ``original_* × fx_rate``.

The contract pinned here, from financial math's side:

1. **Direct pair** (EUR asset → USD): every converted point is bit-identical (value and exponent) to the pre-MF-A13 pass:
   nothing changes.
2. **Inverse pair** (USD, GBP asset → EUR): each of close, open, high and low differs from the pre-MF-A13 pass at most at
   the last of its 28 significant digits (fewer than 10 units of it; for the close also a relative difference ≤ 1e-27)
   and is equal once quantized to 1e-12, to 1e-6 and to cents unless a rounding tie lies between the two (then one
   quantum apart: a last digit can flip a rounded value sitting on a tie). The counts are printed, never asserted.
3. **One formula with the engine**: for the same native price, day and target, ``original_* × AskedDayRates[(src, tgt,
   day)]`` built from ``unit_rate_steps`` as the engine builds it (``portfolio/engine.py``, the rate map of the
   valuation) is the point's value, to the digit and the exponent, on both pair orientations.
4. ``point.fx_rate`` is ``unit_rate_steps(...)[(src, tgt)].at(day)``, to the digit and the exponent; a point that did not
   convert (native, a close of 0, no usable rate) has ``fx_rate`` None.

The pre-MF-A13 pass is a copy written here (``pre_a13_convert``: ``head_convert`` of ``test_price_query_observations.py``
as it was at e5c147685^), not read from the code under test. The corpus (assets, prices, rates, windows) and the dense
fill are the ones of ``test_price_query_observations.py``, imported: they did not change with MF-A13.

Red before MF-A13: 3 (the inverse close is ``convert_bulk``'s quotient, not the native close times the step) and 4 (no
``fx_rate``). 1 and 2 are green on both sides by design: they bound the change.

Isolation: PURE. A private SQLite file under ``tmp_path``; the market holiday table empty where the price query reads it;
no lane database, no server, no network.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Sequence
from datetime import date
from decimal import ROUND_FLOOR, Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel
from backend.app.db.models import Asset, AssetType, FxRate, PriceHistory
from backend.app.schemas.common import Currency
from backend.app.schemas.prices import AssetBackwardFillInfo, FAPricePoint
from backend.app.services.assets import price_query
from backend.app.services.financial_math.fx_rates import AskedDayRates
from backend.app.services.fx.conversion import convert_bulk as head_convert_bulk
from backend.app.services.fx.conversion import unit_rate_steps
from backend.test_scripts.test_services import test_price_query_observations as corpus

#: Direct pairs: the asset's currency sorts before the target, the stored rate is read as it is
DIRECT = [("eur", "USD", "all"), ("eur", "USD", "over-the-rate-gap"), ("late", "USD", "all")]
#: Inverse pairs: the asset's currency sorts after the target, the stored rate is read inverted (``zero`` holds a close of 0)
INVERSE = [("usd", "EUR", "all"), ("usd", "EUR", "over-the-rate-gap"), ("usd", "EUR", "holiday"), ("gbp", "EUR", "all"), ("zero", "EUR", "all")]
#: Items with points that do not convert: native (no target, the asset's own currency), a pair with no rate, a close of 0
UNCONVERTED = [("eur", None, "all"), ("usd", "USD", "all"), ("chf", "EUR", "all"), ("zero", "EUR", "all")]

PRICES = ("open", "high", "low", "close")
#: The pre-MF-A13 inverse close is one rounding (native ÷ rate), the new one two (1 ÷ rate, then ×): on the corpus at most
#: 2 units of the 28th digit apart, a relative difference ≤ 5.9e-28. Open, high and low were three roundings before (the
#: close's quotient, the factor ``converted / close``, the product) and two now: up to 4 units of the 28th digit apart, a
#: relative difference up to 1.18e-27 on a mantissa below 3.4, so for them the bound is the digit, not 1e-27.
CLOSE_RELATIVE_BOUND = Decimal("1e-27")
QUANTA = (Decimal("1e-12"), Decimal("1e-6"), Decimal("0.01"))


def _last_digit(value: Decimal) -> Decimal:
    """One unit of the 28th significant digit of ``value`` (the default context's precision)."""
    return Decimal(10) ** (value.adjusted() - 27)


def _ids(cases: Sequence[tuple[str, str | None, str]]) -> list[str]:
    return [f"{asset}-{target or 'native'}-{window}" for asset, target, window in cases]


@pytest_asyncio.fixture
async def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[corpus._World]:
    """The corpus of ``test_price_query_observations.py`` on a private SQLite file, the market holiday table empty where
    the price query reads it (the same build as its ``world``)."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'price_point_fx_rate_parity.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            session.add_all([Asset(id=corpus.IDS[name], display_name=f"MF-A13 {name} {uuid.uuid4().hex[:8]}", currency=corpus.HISTORIES[name][3], asset_type=AssetType.STOCK) for name in corpus.IDS])
            await session.flush()
            for name in corpus.IDS:
                await session.execute(insert(PriceHistory), corpus._price_rows(name))
            await session.execute(insert(FxRate), corpus._rate_rows())
            await session.commit()

        async def _no_market_holidays() -> frozenset[date]:
            return frozenset()

        monkeypatch.setattr(price_query, "ensure_market_holidays", _no_market_holidays)
        yield corpus._World(engine)
    finally:
        await engine.dispose()


# =============================================================================
# THE PRE-MF-A13 PASS, COPIED: ``head_convert`` as it was at e5c147685^
# =============================================================================


async def pre_a13_convert(session: AsyncSession, prices: list[FAPricePoint], target: str | None) -> tuple[list[FAPricePoint], list[str]]:  # noqa: C901 — a copy of the pass as it was
    """The conversion pass before MF-A13: the close is ``convert_bulk``'s amount, open, high and low are scaled by
    ``converted_close / original_close``."""
    errors: list[str] = []
    prices = list(prices)
    if not target or not prices:
        return prices, errors
    conversions = []
    indices = []
    for i, p in enumerate(prices):
        if p.currency == target:
            continue
        conversions.append((Currency(code=p.currency, amount=p.close), target, p.date))
        indices.append(i)
    if not conversions:
        return prices, errors
    converted, conv_errors = await head_convert_bulk(session, conversions, raise_on_error=False)
    if conv_errors:
        seen: set[str] = set()
        deduped = []
        for err in conv_errors:
            if err not in seen:
                seen.add(err)
                deduped.append(err)
        if len(deduped) > 10:
            deduped = deduped[:10] + [f"… and {len(deduped) - 10} more FX conversion failures"]
        errors.extend(deduped)
    conv_idx = 0
    for pi in indices:
        conv_result = converted[conv_idx]
        original = prices[pi]
        if conv_result is None:
            old_bfi = original.backward_fill_info
            prices[pi] = FAPricePoint(
                date=original.date,
                open=original.open,
                high=original.high,
                low=original.low,
                close=original.close,
                volume=original.volume,
                currency=original.currency,
                original_currency=original.original_currency,
                original_close=original.original_close,
                original_open=original.original_open,
                original_high=original.original_high,
                original_low=original.original_low,
                source_plugin_key=original.source_plugin_key,
                backward_fill_info=AssetBackwardFillInfo(actual_rate_date=old_bfi.actual_rate_date if old_bfi else original.date, days_back=old_bfi.days_back if old_bfi else 0, fx_rate_date=None, fx_days_back=None),
            )
            conv_idx += 1
            continue
        converted_currency, rate_date, _applied = conv_result
        original_close = original.close
        if original_close and original_close != 0:
            fx_factor = converted_currency.amount / original_close
        else:
            conv_idx += 1
            continue
        fx_days_back = (original.date - rate_date).days if rate_date < original.date else 0
        old_bfi = original.backward_fill_info
        if old_bfi:
            new_bfi = AssetBackwardFillInfo(actual_rate_date=old_bfi.actual_rate_date, days_back=old_bfi.days_back, fx_rate_date=rate_date, fx_days_back=fx_days_back)
        elif fx_days_back > 0:
            new_bfi = AssetBackwardFillInfo(actual_rate_date=original.date, days_back=0, fx_rate_date=rate_date, fx_days_back=fx_days_back)
        else:
            new_bfi = None
        prices[pi] = FAPricePoint(
            date=original.date,
            open=original.open * fx_factor if original.open is not None else None,
            high=original.high * fx_factor if original.high is not None else None,
            low=original.low * fx_factor if original.low is not None else None,
            close=converted_currency.amount,
            volume=original.volume,
            currency=target,
            original_currency=original.currency,
            original_close=original_close,
            original_open=original.open,
            original_high=original.high,
            original_low=original.low,
            source_plugin_key=original.source_plugin_key,
            backward_fill_info=new_bfi,
        )
        conv_idx += 1
    return prices, errors


async def pre_a13_series(world: corpus._World, asset: str, window: str, target: str | None) -> list[FAPricePoint]:
    """The series of an item as the pre-MF-A13 pipeline answered it: the dense fill (unchanged by MF-A13), then the copy."""
    start, end = corpus.WINDOWS[window]
    rows = await corpus._rows(world, asset)
    seed = max((row for day, row in rows.items() if day < start), key=lambda row: row.date, default=None)
    window_rows = {day: row for day, row in rows.items() if start <= day <= end}
    async with AsyncSession(world.engine, expire_on_commit=False) as session:
        points, _errors = await pre_a13_convert(session, corpus.head_dense(window_rows, start, end, seed), target)
    return points


# =============================================================================
# HELPERS
# =============================================================================


def _without(points: Sequence[FAPricePoint], fields: Sequence[str]) -> list[dict]:
    """The JSON dump of each point (strings: value and exponent) without ``fields``; ``fx_rate`` is left out wherever the
    schema has it, so that the pre-MF-A13 copy, which never sets it, compares."""
    dumped = []
    for point in points:
        row = point.model_dump(mode="json")
        for field in (*fields, "fx_rate"):
            row.pop(field, None)
        dumped.append(row)
    return dumped


def _converted(points: Sequence[FAPricePoint], asset: str, target: str) -> list[FAPricePoint]:
    """The points of ``points`` that were converted from the asset's currency into ``target``."""
    source = corpus.HISTORIES[asset][3]
    return [point for point in points if point.currency == target and point.original_currency == source]


async def _engine_rates(world: corpus._World, source: str, target: str, points: Sequence[FAPricePoint]) -> tuple[dict, AskedDayRates]:
    """The steps of ``source → target`` over the days of ``points``, and the rate map the portfolio engine builds from them
    (``AskedDayRates(unit_rate_steps(pairs), pairs)``, ``portfolio/engine.py``)."""
    pairs = {(source, target): [(min(point.date for point in points), max(point.date for point in points))]}
    async with AsyncSession(world.engine, expire_on_commit=False) as session:
        steps = await unit_rate_steps(session, pairs)
    return steps, AskedDayRates(steps, pairs)


# =============================================================================
# 1 — DIRECT PAIR: nothing changes
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(("asset", "target", "window"), DIRECT, ids=_ids(DIRECT))
async def test_a13p1_on_a_direct_pair_every_point_is_the_pre_a13_point_to_the_digit(world, asset, target, window):
    """1: on a direct pair (native × stored rate) every point of ``get_prices_bulk`` — close, open, high, low, the
    ``original_*``, currency and ``backward_fill_info`` — is the pre-MF-A13 pass's, value and exponent: zero changes."""
    expected = await pre_a13_series(world, asset, window, target)
    (result,) = await corpus._query(world, world.item(asset, window, target))

    assert _converted(result.prices, asset, target), f"premise: {asset} → {target} over {window} holds converted points"
    assert _without(result.prices, ()) == _without(expected, ()), f"{asset} → {target} over {window}: a point differs from the pre-MF-A13 pass on a direct pair"


# =============================================================================
# 2 — INVERSE PAIR: the last digit at most; a rounded value only across a rounding tie
# =============================================================================


def _tie_between(low: Decimal, high: Decimal, quantum: Decimal) -> Decimal | None:
    """The rounding tie of ``quantum`` (a value halfway between two of its multiples) in ``[low, high]``, the nearest to
    ``low``; None when there is none."""
    tie = low.quantize(quantum, rounding=ROUND_FLOOR) + quantum / 2
    if tie < low:
        tie += quantum
    return tie if tie <= high else None


def _moved_price(where: str, field: str, new: Decimal, old: Decimal, worst: dict[str, tuple[Decimal, Decimal]], flips: dict[Decimal, list[str]]) -> list[str]:
    """The violations of one price that moved from ``old`` (pre-MF-A13) to ``new``: more than the last of its 28 digits, a
    close beyond ``CLOSE_RELATIVE_BOUND``, a quantized value that changes with no rounding tie between the two (or by more
    than one quantum). Records the largest differences of ``field`` in ``worst`` and each quantized value that flips in
    ``flips``."""
    violations: list[str] = []
    relative = abs(new - old) / abs(old)
    last_digits = abs(new - old) / _last_digit(old)
    worst[field] = (max(worst[field][0], relative), max(worst[field][1], last_digits))
    if last_digits >= 10:
        violations.append(f"{where}: {last_digits} units of the 28th significant digit apart, more than the last digit")
    if field == "close" and relative > CLOSE_RELATIVE_BOUND:
        violations.append(f"{where}: relative difference {relative} > {CLOSE_RELATIVE_BOUND}")
    low, high = sorted((new, old))
    for quantum in QUANTA:
        rounded_new, rounded_old = new.quantize(quantum), old.quantize(quantum)
        if rounded_new == rounded_old:
            continue
        tie = _tie_between(low, high, quantum)
        flips[quantum].append(f"{where} (tie {tie})")
        if tie is None or abs(rounded_new - rounded_old) != quantum:
            violations.append(f"{where}: quantized to {quantum} {rounded_new} vs {rounded_old}, with no rounding tie between them")
    return violations


@pytest.mark.asyncio
async def test_a13p2_on_an_inverse_pair_a_price_moves_at_its_last_digit_and_a_rounded_one_only_across_a_tie(world):
    """2: on an inverse pair (native ÷ stored rate before, native × (1 ÷ stored rate) now) each of close, open, high and
    low differs from the pre-MF-A13 pass at most at the last of its 28 significant digits (fewer than 10 units of it; the
    close also within a relative 1e-27, see ``CLOSE_RELATIVE_BOUND`` for why open, high and low are not). Every other
    field of the point is the pre-MF-A13 one.

    Quantized to 1e-12, to 1e-6 and to cents the two are equal, except where a rounding tie of that quantum lies between
    them: there they differ by one quantum, and only there. A difference at the last digit cannot be hidden by rounding
    when the value sits on a tie: on this corpus GBP → EUR on 2025-06-20, the pre-MF-A13 close is the exact quotient
    399.5129875 (→ 399.512988 at 1e-6, half even), the new one 399.5129874999999999999999999 (→ 399.512987).

    The counts — prices that differ, rounded values that flip — are printed (``-s``), never asserted: they depend on the
    corpus, the bounds do not. Every violation is collected before the assertion, so one run shows them all.
    """
    compared = differing = points_differing = 0
    worst = {field: (Decimal(0), Decimal(0)) for field in PRICES}  # field -> (largest relative difference, largest in units of the 28th digit)
    flips: dict[Decimal, list[str]] = {quantum: [] for quantum in QUANTA}
    violations: list[str] = []
    for asset, target, window in INVERSE:
        expected = await pre_a13_series(world, asset, window, target)
        (result,) = await corpus._query(world, world.item(asset, window, target))
        label = f"{asset} → {target} over {window}"

        assert _converted(result.prices, asset, target), f"premise: {label} holds converted points"
        assert _without(result.prices, PRICES) == _without(expected, PRICES), f"{label}: a field other than the prices differs from the pre-MF-A13 pass"
        for now, before in zip(result.prices, expected, strict=True):
            point_moved = False
            for field in PRICES:
                new, old = getattr(now, field), getattr(before, field)
                where = f"{label} {now.date} {field}: {new} vs pre-MF-A13 {old}"
                if old is None or new is None:
                    if new is not old:
                        violations.append(f"{where}: one of the two is missing")
                    continue
                compared += 1
                if new == old:
                    continue
                differing += 1
                point_moved = True
                violations.extend(_moved_price(where, field, new, old, worst, flips))
            points_differing += point_moved
    print(f"\nMF-A13 inverse parity: {differing} of {compared} prices differ from the pre-MF-A13 pass, on {points_differing} points")
    for field, (relative, last_digits) in worst.items():
        print(f"MF-A13 inverse parity: {field}: largest difference {last_digits} units of the 28th digit, relative {relative}")
    for quantum, flipped in flips.items():
        print(f"MF-A13 inverse parity: quantized to {quantum}: {len(flipped)} values flip across a tie" + "".join(f"\n  {line}" for line in flipped))
    assert not violations, "\n".join(violations)


# =============================================================================
# 3 — ONE FORMULA WITH THE ENGINE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(("asset", "target", "window"), DIRECT + INVERSE, ids=_ids(DIRECT + INVERSE))
async def test_a13p3_a_converted_price_is_the_native_price_times_the_engines_rate_of_the_day(world, asset, target, window):
    """3: for every converted point, ``original_* × AskedDayRates[(source, target, day)]`` — the rate map the portfolio
    engine values a mark with, built from the same ``unit_rate_steps`` — is the point's close, open, high and low, to the
    digit and the exponent, on a direct and on an inverse pair: the chart's close is the number the valuation uses.

    Red before MF-A13 on the inverse pairs: the close was ``convert_bulk``'s native ÷ stored rate.
    """
    source = corpus.HISTORIES[asset][3]
    (result,) = await corpus._query(world, world.item(asset, window, target))
    converted = _converted(result.prices, asset, target)
    assert converted, f"premise: {asset} → {target} over {window} holds converted points"
    _steps, rates = await _engine_rates(world, source, target, converted)

    for point in converted:
        rate = rates[(source, target, point.date)]
        for field, original in (("close", point.original_close), ("open", point.original_open), ("high", point.original_high), ("low", point.original_low)):
            value = getattr(point, field)
            if original is None:
                assert value is None, f"{point.date} {field}: {value} without an original"
                continue
            assert str(value) == str(original * rate), f"{asset} → {target} {point.date} {field}: the point says {value}, the engine values {original} × {rate} = {original * rate}"


# =============================================================================
# 4 — THE POINT SAYS ITS RATE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(("asset", "target", "window"), DIRECT + INVERSE, ids=_ids(DIRECT + INVERSE))
async def test_a13p4_a_converted_point_carries_the_step_of_its_day(world, asset, target, window):
    """4: ``point.fx_rate`` is ``unit_rate_steps(...)[(source, target)].at(day)``, value and exponent: the stored rate on
    a direct pair, one over it on an inverse one, carried over the days without a stored rate.

    Red before MF-A13: ``FAPricePoint`` has no ``fx_rate``.
    """
    assert "fx_rate" in FAPricePoint.model_fields, "MF-A13 not applied: FAPricePoint has no fx_rate"
    source = corpus.HISTORIES[asset][3]
    (result,) = await corpus._query(world, world.item(asset, window, target))
    converted = _converted(result.prices, asset, target)
    assert converted, f"premise: {asset} → {target} over {window} holds converted points"
    steps, _rates = await _engine_rates(world, source, target, converted)

    for point in converted:
        step = steps[(source, target)].at(point.date)
        assert step is not None, f"premise: {source} → {target} has a step on {point.date}"
        assert point.fx_rate is not None and str(point.fx_rate) == str(step), f"{asset} → {target} {point.date}: fx_rate {point.fx_rate}, the day's step {step}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("asset", "target", "window"), UNCONVERTED, ids=_ids(UNCONVERTED))
async def test_a13p4_a_point_that_did_not_convert_has_no_rate(world, asset, target, window):
    """4: a point in its own currency — no target, a target that is the asset's currency, a pair with no usable rate
    (CHF → EUR), a close of 0 (left native) — has ``fx_rate`` None."""
    assert "fx_rate" in FAPricePoint.model_fields, "MF-A13 not applied: FAPricePoint has no fx_rate"
    source = corpus.HISTORIES[asset][3]
    (result,) = await corpus._query(world, world.item(asset, window, target))
    unconverted = [point for point in result.prices if point.currency == source]
    assert unconverted, f"premise: {asset} → {target or 'native'} over {window} holds points left in {source}"
    if (asset, target) == ("zero", "EUR"):
        assert any(point.original_close is None and point.close == 0 for point in unconverted), "premise: the close of 0 is left native"
    assert [point.date for point in unconverted if point.fx_rate is not None] == [], f"{asset} → {target or 'native'}: a point left in {source} carries an fx_rate"
