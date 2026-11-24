"""Lane 80, lot ALF-B1a — an asset's allocation parts have one home, and the engine's result carries what they read.

The allocation of a day splits each held position's market value by asset type, sector and country
(``DailyStateBuilder._distribute_allocation``, plan 68 D2). The «Allocazione» tab (issue #89) rebuilds filtered views
from ``by_asset`` with the same split, so the split moves into one pure function of ``daily_state``:

- ``allocation_parts(asset_type, classification, day, value) -> AllocationParts``: ``type_key`` (the asset type, the
  value whole), ``sector`` and ``geography`` as ordered ``(key, amount)`` pairs — the weights of ``day`` in their own
  order, ``value * weight`` each; no weights (no profile, a voice absent or emptied on purpose) → ``(("Unknown",
  value),)``; the country «Other» is named «Unknown» but stays a pair of its own, so the builder adds the same
  amounts in the same order as before;
- ``_distribute_allocation`` adds those pairs into its buckets, and the day's allocation is unchanged (the D2 tests of
  ``test_asset_allocation.py`` pin the values; :class:`TestTheBuilderUsesTheParts` pins the identity, by value and
  exponent, against the parts of each position frame);
- ``PortfolioCalculationResult.asset_types`` and ``.asset_classifications``: the maps the replay read, empty by
  default (the engine's early returns).

Pure: the builder fed by hand (the book of ``test_asset_allocation.py``), no database, no server.

RED on HEAD 17397f5a5, by absence: ``daily_state`` has no ``allocation_parts`` (``AttributeError``) and the result no
``asset_types`` (``AttributeError``).

Runs in ``./dev.py test services financial-math`` (the runner collects the whole ``test_financial_math/`` directory).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from backend.app.services.financial_math.portfolio import daily_state as daily_state_module
from backend.app.services.financial_math.portfolio.daily_state import ClassificationStep, DailyStateBuilder
from backend.app.services.financial_math.portfolio.models import DailyStates, PortfolioCalculationResult
from backend.test_scripts.test_services.test_financial_math.test_asset_allocation import (
    BOOK_FROM,
    BOOK_TO,
    GEO_1,
    GEO_2,
    SECTOR_1,
    W_GEO,
    G,
    W,
    X,
    _book,
    _builder_kwargs,
    _days,
    _same,
    _steps,
    _whole,
)

ZERO = Decimal("0")
MID = date(2025, 4, 10)


def _parts(*args):
    return daily_state_module.allocation_parts(*args)


def _pairs_same(got, expected) -> bool:
    return len(got) == len(expected) and all(a[0] == b[0] and _same(a[1], b[1]) for a, b in zip(got, expected, strict=True))


class TestTheParts:
    def test_no_profile_is_unknown_in_both_voices(self):
        parts = _parts("STOCK", None, MID, Decimal("123.45"))
        assert parts.type_key == "STOCK"
        assert _pairs_same(parts.sector, (("Unknown", Decimal("123.45")),))
        assert _pairs_same(parts.geography, (("Unknown", Decimal("123.45")),))

    def test_the_weights_of_the_day_in_their_order_other_country_as_a_pair_of_its_own(self):
        value = Decimal("200.10")
        classification = {"geography": _whole({"USA": "0.2500", "Other": "0.5000", "JPN": "0.2500"}), "sector": _whole({"Other": "0.4000", "Technology": "0.6000"})}
        parts = _parts("ETF_STOCK", classification, MID, value)
        assert _pairs_same(parts.geography, (("USA", value * Decimal("0.2500")), ("Unknown", value * Decimal("0.5000")), ("JPN", value * Decimal("0.2500"))))
        assert _pairs_same(parts.sector, (("Other", value * Decimal("0.4000")), ("Technology", value * Decimal("0.6000")))), "the sector «Other» is a real slice"

    def test_an_emptied_or_absent_voice_is_unknown(self):
        value = Decimal("50")
        parts = _parts("BOND", {"geography": _steps((BOOK_FROM, BOOK_TO, None))}, MID, value)
        assert _pairs_same(parts.geography, (("Unknown", value),)), "a voice emptied on purpose"
        assert _pairs_same(parts.sector, (("Unknown", value),)), "a voice absent"

    def test_the_step_of_the_day_before_the_first_and_after_the_last(self):
        first, second = date(2025, 4, 5), date(2025, 4, 12)
        steps = _steps((first, date(2025, 4, 11), {"USA": "1.0000"}), (second, date(2025, 4, 15), {"JPN": "1.0000"}))
        value = Decimal("10")
        on = {day: _parts("STOCK", {"geography": steps}, day, value).geography[0][0] for day in (BOOK_FROM, first, MID, second, BOOK_TO)}
        assert on == {BOOK_FROM: "USA", first: "USA", MID: "USA", second: "JPN", BOOK_TO: "JPN"}


def _classifications() -> dict:
    """X with geography in two steps (GEO_1, then GEO_2 with «Other») and one sector step; W with one geography step
    and no sector voice; G (never valued) without a profile."""
    return {
        X: {"geography": _steps((BOOK_FROM, date(2025, 4, 9), GEO_1), (MID, BOOK_TO, GEO_2)), "sector": _whole(SECTOR_1)},
        W: {"geography": _whole(W_GEO)},
        G: None,
    }


def _build_with_frames() -> PortfolioCalculationResult:
    book = _book()
    book["asset_classifications"] = _classifications()
    book["asset_types"] = {X: "ETF_STOCK", G: "STOCK", W: "BOND"}
    return DailyStateBuilder(**_builder_kwargs(**book, date_from=BOOK_FROM, compute_position_frames=True)).build()


def _dict_problems(day, name: str, got: dict, expected: dict) -> list[str]:
    if got.keys() != expected.keys():
        return [f"{day} {name}: keys {sorted(got)} != {sorted(expected)}"]
    return [f"{day} {name}[{key}]: {got[key]!r} != {expected[key]!r}" for key in expected if not _same(got[key], expected[key])]


class TestTheBuilderUsesTheParts:
    def test_every_day_is_the_sum_of_the_parts_of_its_position_frames(self):
        result = _build_with_frames()
        assert result.position_frames, "precondition: the frames were asked"
        problems: list[str] = []
        for day in _days(BOOK_FROM, BOOK_TO):
            state = result.daily_states.state_on(day)
            by_type: dict[str, Decimal] = {}
            by_sector: dict[str, Decimal] = {}
            by_geo: dict[str, Decimal] = {}
            for frame in result.position_frames:
                if not (frame.start <= day <= frame.end) or frame.market_value is None:
                    continue
                parts = _parts(result.asset_types.get(frame.asset_id, "Unknown"), result.asset_classifications.get(frame.asset_id), day, frame.market_value)
                by_type[parts.type_key] = by_type.get(parts.type_key, ZERO) + frame.market_value
                for bucket, pairs in ((by_sector, parts.sector), (by_geo, parts.geography)):
                    for key, amount in pairs:
                        bucket[key] = bucket.get(key, ZERO) + amount
            cash = state.cash_value
            by_type["Liquidity"] = by_type.get("Liquidity", ZERO) + cash + state.in_transit_cash_value
            by_sector["Liquidity"] = by_sector.get("Liquidity", ZERO) + cash + state.in_transit_cash_value
            problems += _dict_problems(day, "by_type", dict(state.by_type), by_type)
            problems += _dict_problems(day, "by_sector", dict(state.by_sector), by_sector)
            problems += _dict_problems(day, "by_geography", dict(state.by_geography), by_geo)
        assert problems == []

    def test_the_book_reaches_every_branch(self):
        result = _build_with_frames()
        late = result.daily_states.state_on(BOOK_TO)
        assert "Unknown" in late.by_geography and "Other" not in late.by_geography, "X's «Other» country is Unknown"
        assert "Unknown" in late.by_sector, "W has no sector voice"
        assert {"ETF_STOCK", "BOND", "Liquidity"} <= set(late.by_type), late.by_type


class TestTheResultCarriesWhatTheReplayRead:
    def test_the_builder_puts_its_maps_on_the_result(self):
        result = _build_with_frames()
        assert result.asset_types == {X: "ETF_STOCK", G: "STOCK", W: "BOND"}
        assert dict(result.asset_classifications) == _classifications()
        assert isinstance(next(iter(result.asset_classifications[X]["geography"])), ClassificationStep)

    def test_a_result_without_a_replay_has_empty_maps(self):
        result = PortfolioCalculationResult(daily_states=DailyStates())
        assert result.asset_types == {} and dict(result.asset_classifications) == {}


class TestOneVoice:
    """Lane 80, B2: ``allocation_voice_parts`` is one voice of ``allocation_parts``, the same pairs (the «Allocazione»
    history splits only the dimension it shows)."""

    def test_each_voice_is_allocation_parts_voice(self):
        classifications = (
            None,
            {daily_state_module.GEOGRAPHY_VOICE: _whole(GEO_2), daily_state_module.SECTOR_VOICE: _whole(SECTOR_1)},
            {daily_state_module.GEOGRAPHY_VOICE: _whole(None)},
            {daily_state_module.SECTOR_VOICE: _steps((BOOK_FROM, BOOK_FROM, SECTOR_1), (BOOK_FROM + timedelta(days=1), BOOK_TO, W_GEO))},
        )
        value = Decimal("1234.56")
        for classification in classifications:
            for day in (BOOK_FROM, BOOK_FROM + timedelta(days=3), BOOK_TO):
                parts = daily_state_module.allocation_parts("ETF_STOCK", classification, day, value)
                assert daily_state_module.allocation_voice_parts(classification, daily_state_module.SECTOR_VOICE, day, value) == parts.sector
                assert daily_state_module.allocation_voice_parts(classification, daily_state_module.GEOGRAPHY_VOICE, day, value) == parts.geography
