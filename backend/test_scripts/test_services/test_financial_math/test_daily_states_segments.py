"""MF5-1 «P4» — the engine keeps only its computed days: ``StateSegment`` and ``DailyStates``, the model contract.

Today ``PortfolioCalculationResult.daily_states`` is a ``list`` with one ``DailyPortfolioState`` per calendar day: a quiet
day (nothing changes) is the previous state copied by ``dataclasses.replace`` with its containers copied. A scope with
one row in 1900 holds ~46 000 of them, nearly all copies.

The cure (``financial_math/portfolio/models.py``), pinned here:

- ``StateSegment(start, end, state)``, frozen and slotted: ``state`` is the computed state of ``start``
  (``state.date == start``), and it holds through ``end`` inclusive. ``state_on(day)``: on ``start`` the stored object
  itself; on a later day of the segment a NEW state built as the engine builds a quiet day today —
  ``replace(state, date=day, external_cash_flow=0, acquisition_funding=None)`` with every container copied
  (``by_type``, ``by_sector``, ``by_geography``, the four data-quality sets, ``transaction_implied_last_quote_dates``,
  ``broker_contributions``, ``unrealized_by_currency``), ``pnl_candle`` and every other field carried; outside the
  segment ``ValueError``.
- ``DailyStates(segments)``, a ``Sequence[DailyPortfolioState]`` over the calendar days ``first_date..last_date``:
  ``ValueError`` unless the segments are ascending, contiguous (``next.start == prev.end + 1 day``) and each
  ``state.date == start``; ``len`` counts days; ``[i]`` / ``[slice]`` / iteration build the quiet days on the fly through
  ``StateSegment.state_on``; ``==`` compares element-wise with any sequence (a plain list); ``segment_at``, ``state_on``,
  ``state_as_of`` look a day up; ``iter_segments(date_from, date_to)`` yields the segments overlapping the window, clipped
  (a segment whose start moved carries ``state_on(new_start)``; an unclipped one is yielded as stored).

Counting. ``StateSegment.state_on`` is replaced on the class through ``monkeypatch`` (a slotted dataclass restricts its
instances' attributes, not its class's): every quiet-day materialization goes through it, so the count says how many
days a read built. Beside it, ``DailyPortfolioState.__init__`` is counted too (``dataclasses.replace`` constructs through
it), so a read that bypassed ``state_on`` would still be seen.

RED on HEAD 1fd80c481, by absence: ``StateSegment`` and ``DailyStates`` do not exist, the module fails at collection with
``ImportError``. Pure: no database, no server, no network; every state is built by hand.

Runs in ``./dev.py test services financial-math`` (the runner collects the whole ``test_financial_math/`` directory).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.services.financial_math.portfolio.models import (
    AcquisitionFundingContribution,
    BrokerDailyContribution,
    DailyPortfolioState,
    DailyStates,
    PnlCandleContribution,
    StateSegment,
    UnrealizedSplit,
)

# The three fields a quiet day does not carry from its segment's computed day.
QUIET_FIELDS = {"date", "external_cash_flow", "acquisition_funding"}
# The containers a quiet day copies (never shares with the stored state).
CONTAINER_FIELDS = {
    "by_type",
    "by_sector",
    "by_geography",
    "missing_price_asset_ids",
    "missing_fx_pairs",
    "stale_price_asset_ids",
    "transaction_implied_asset_ids",
    "transaction_implied_last_quote_dates",
    "broker_contributions",
    "unrealized_by_currency",
    "by_asset",
}

D1 = date(2025, 1, 1)
D2 = date(2025, 1, 2)
D6 = date(2025, 1, 6)
D7 = date(2025, 1, 7)
D9 = date(2025, 1, 9)


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _state(day: date, seed: int) -> DailyPortfolioState:
    """A computed day's state, every field filled with a value of its own (``seed`` tells two segments apart), every
    container non-empty, a candle and an acquisition funding present, a non-zero external flow."""

    def amount(offset: int) -> Decimal:
        return Decimal(seed * 1000 + offset) / Decimal("100")

    return DailyPortfolioState(
        date=day,
        cash_value=amount(1),
        market_value=amount(2),
        broker_nav_value=amount(3),
        in_transit_cash_value=amount(4),
        in_transit_asset_market_value=amount(5),
        in_transit_market_value=amount(6),
        nav_value=amount(7),
        open_cost_basis=amount(8),
        in_transit_asset_cost_basis=amount(9),
        in_transit_book_value=amount(10),
        book_value=amount(11),
        unrealized_gain_loss=amount(12),
        external_cash_flow=amount(13),
        cumulative_external_cash_flow=amount(14),
        book_asset_like=amount(15),
        cash_from_contributed_capital=amount(16),
        cash_from_generated_returns=amount(17),
        total_pnl=amount(18),
        by_type={"ETF": amount(19), "Stock": amount(20)},
        by_sector={"Technology": amount(21)},
        by_geography={"US": amount(22)},
        missing_price_asset_ids={seed, 900 + seed},
        missing_fx_pairs={"USD/EUR"},
        stale_price_asset_ids={800 + seed},
        transaction_implied_asset_ids={700 + seed},
        transaction_implied_last_quote_dates={700 + seed: day - timedelta(days=3)},
        nav_complete=seed % 2 == 0,
        broker_contributions={10: BrokerDailyContribution(broker_id=10, nav_contribution=amount(7), capital_contribution=amount(14), pnl_contribution=amount(18), in_transit_contribution=amount(6))},
        pnl_candle=PnlCandleContribution(open=amount(23), high=amount(24), low=amount(25), close=amount(18)),
        acquisition_funding=AcquisitionFundingContribution(from_new_capital=amount(26), from_reinvested=amount(27)),
        unrealized_by_currency={"USD": UnrealizedSplit(asset=amount(28), fx=amount(29), unsplit=amount(30))},
        by_asset={600 + seed: amount(31), 650 + seed: amount(32)},
    )


def _three_segments() -> tuple[StateSegment, StateSegment, StateSegment]:
    """S1: 2025-01-01 alone; S2: 01-02 .. 01-06 (five days); S3: 01-07 .. 01-09 (three days)."""
    return (
        StateSegment(start=D1, end=D1, state=_state(D1, 1)),
        StateSegment(start=D2, end=D6, state=_state(D2, 2)),
        StateSegment(start=D7, end=D9, state=_state(D7, 3)),
    )


def _field_values(state: DailyPortfolioState, *, skip: set[str] = frozenset()) -> dict:
    return {f.name: getattr(state, f.name) for f in dataclasses.fields(DailyPortfolioState) if f.name not in skip}


def _assert_quiet_day_of(materialized: DailyPortfolioState, stored: DailyPortfolioState, day: date) -> None:
    """``materialized`` is the quiet day ``day`` of a segment whose computed state is ``stored``."""
    assert materialized is not stored
    assert materialized.date == day
    assert materialized.external_cash_flow == Decimal(0)
    assert materialized.acquisition_funding is None
    assert _field_values(materialized, skip=QUIET_FIELDS) == _field_values(stored, skip=QUIET_FIELDS)
    for name in CONTAINER_FIELDS:
        assert getattr(materialized, name) is not getattr(stored, name), f"{name} is shared with the stored state"


@pytest.fixture
def materializations(monkeypatch) -> list[date]:
    """Every day ``StateSegment.state_on`` is asked for, in order."""
    calls: list[date] = []
    real_state_on = StateSegment.state_on

    def counting_state_on(self, day):
        calls.append(day)
        return real_state_on(self, day)

    monkeypatch.setattr(StateSegment, "state_on", counting_state_on)
    return calls


@pytest.fixture
def constructions(monkeypatch) -> list[date]:
    """Every ``DailyPortfolioState`` constructed (``dataclasses.replace`` constructs through ``__init__``), by its date."""
    built: list[date] = []
    real_init = DailyPortfolioState.__init__

    def counting_init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        built.append(self.date)

    monkeypatch.setattr(DailyPortfolioState, "__init__", counting_init)
    return built


# =============================================================================
# THE FIXTURE ITSELF
# =============================================================================


class TestTheFixture:
    def test_every_container_field_of_the_state_is_in_the_copied_list(self):
        """Guard of the field-by-field tests: every dict/set field of ``DailyPortfolioState`` is a container the quiet
        day must copy, so a container added later without a copy turns these tests red, not silent."""
        state = _state(D1, 1)
        containers = {name for name, value in _field_values(state).items() if isinstance(value, (dict, set, list))}
        assert containers == CONTAINER_FIELDS
        assert all(_field_values(state)[name] for name in CONTAINER_FIELDS), "every container is non-empty"
        assert state.external_cash_flow != 0 and state.acquisition_funding is not None and state.pnl_candle is not None


# =============================================================================
# StateSegment
# =============================================================================


class TestStateSegment:
    def test_the_computed_day_is_the_stored_object(self):
        seg = StateSegment(start=D2, end=D6, state=_state(D2, 2))
        assert seg.state_on(D2) is seg.state

    @pytest.mark.parametrize("day", _days(date(2025, 1, 3), D6), ids=lambda d: d.isoformat())
    def test_a_quiet_day_is_a_new_state_built_like_the_engine_builds_one(self, day):
        """Field by field: date moved, external flow 0, acquisition funding None, everything else equal (candle and
        scalars carried), containers equal but never the stored objects."""
        stored = _state(D2, 2)
        seg = StateSegment(start=D2, end=D6, state=stored)
        before = _field_values(stored)

        materialized = seg.state_on(day)

        _assert_quiet_day_of(materialized, stored, day)
        assert materialized.pnl_candle == stored.pnl_candle
        assert materialized.nav_complete == stored.nav_complete
        assert _field_values(stored) == before, "the stored state is never mutated"

    def test_mutating_a_quiet_days_containers_leaves_the_stored_state_and_later_reads_unchanged(self):
        stored = _state(D2, 2)
        seg = StateSegment(start=D2, end=D6, state=stored)
        before = _field_values(stored)

        quiet = seg.state_on(date(2025, 1, 4))
        quiet.by_type["Bond"] = Decimal("999")
        quiet.by_sector.clear()
        quiet.by_geography["IT"] = Decimal("1")
        quiet.missing_price_asset_ids.add(4242)
        quiet.missing_fx_pairs.add("GBP/EUR")
        quiet.stale_price_asset_ids.clear()
        quiet.transaction_implied_asset_ids.add(4343)
        quiet.transaction_implied_last_quote_dates[4343] = None
        quiet.broker_contributions.clear()
        quiet.unrealized_by_currency["CHF"] = UnrealizedSplit()

        assert _field_values(stored) == before
        again = seg.state_on(date(2025, 1, 4))
        assert _field_values(again, skip=QUIET_FIELDS) == _field_values(stored, skip=QUIET_FIELDS)

    @pytest.mark.parametrize("day", [D1, date(2025, 1, 7), date(2024, 12, 31), date(2026, 1, 2)], ids=lambda d: d.isoformat())
    def test_a_day_outside_the_segment_is_a_value_error(self, day):
        seg = StateSegment(start=D2, end=D6, state=_state(D2, 2))
        with pytest.raises(ValueError):
            seg.state_on(day)

    def test_a_one_day_segment_answers_its_day_only(self):
        seg = StateSegment(start=D1, end=D1, state=_state(D1, 1))
        assert seg.state_on(D1) is seg.state
        with pytest.raises(ValueError):
            seg.state_on(D2)

    def test_the_segment_is_frozen(self):
        seg = StateSegment(start=D2, end=D6, state=_state(D2, 2))
        with pytest.raises(dataclasses.FrozenInstanceError):
            seg.end = D9  # type: ignore[misc]

    def test_state_on_is_patchable_on_the_class(self, materializations):
        """The counting technique of these tests and of the engine's: ``state_on`` replaced on the slotted class."""
        seg = StateSegment(start=D2, end=D6, state=_state(D2, 2))
        seg.state_on(date(2025, 1, 3))
        assert materializations == [date(2025, 1, 3)]


# =============================================================================
# DailyStates — construction
# =============================================================================


class TestConstruction:
    def test_the_segments_are_kept_in_order_and_iterables_are_accepted(self):
        s1, s2, s3 = _three_segments()
        ds = DailyStates(seg for seg in (s1, s2, s3))
        assert ds.segments == (s1, s2, s3)
        assert all(kept is given for kept, given in zip(ds.segments, (s1, s2, s3), strict=True))
        assert (ds.first_date, ds.last_date) == (D1, D9)
        assert isinstance(ds, Sequence)

    def test_unordered_segments_are_a_value_error(self):
        s1, s2, s3 = _three_segments()
        with pytest.raises(ValueError):
            DailyStates([s2, s1, s3])

    def test_a_gap_between_segments_is_a_value_error(self):
        s1, _s2, s3 = _three_segments()
        with pytest.raises(ValueError):
            DailyStates([s1, s3])

    def test_overlapping_segments_are_a_value_error(self):
        s1, s2, _s3 = _three_segments()
        overlapping = StateSegment(start=date(2025, 1, 5), end=D9, state=_state(date(2025, 1, 5), 3))
        with pytest.raises(ValueError):
            DailyStates([s1, s2, overlapping])

    def test_a_repeated_segment_is_a_value_error(self):
        s1, s2, _s3 = _three_segments()
        with pytest.raises(ValueError):
            DailyStates([s1, s2, s2])

    def test_a_state_not_dated_on_its_segments_start_is_a_value_error(self):
        """The mismatch may be refused by ``StateSegment`` itself or by ``DailyStates``: both are inside the block."""
        s1, _s2, _s3 = _three_segments()
        with pytest.raises(ValueError):
            DailyStates([s1, StateSegment(start=D2, end=D6, state=_state(date(2025, 1, 3), 2))])

    def test_an_empty_sequence(self, materializations):
        ds = DailyStates()
        assert len(ds) == 0
        assert not ds
        assert ds.segments == ()
        assert (ds.first_date, ds.last_date) == (None, None)
        assert list(ds) == []
        assert ds[0:3] == []
        with pytest.raises(IndexError):
            ds[0]
        with pytest.raises(IndexError):
            ds[-1]
        assert ds.segment_at(D1) is None
        assert ds.state_on(D1) is None
        assert ds.state_as_of(D1) is None
        assert list(ds.iter_segments()) == []
        assert list(ds.iter_segments(D1, D9)) == []
        assert ds == []
        assert materializations == []


# =============================================================================
# DailyStates — length, indexing, slices, iteration
# =============================================================================


class TestSequence:
    def test_len_counts_calendar_days_without_building_any(self, materializations, constructions):
        ds = DailyStates(_three_segments())
        constructions.clear()  # the three computed states the fixture built
        assert len(ds) == 9
        assert ds
        assert materializations == [] and constructions == []

    def test_a_computed_day_is_the_stored_object(self):
        s1, s2, s3 = segs = _three_segments()
        ds = DailyStates(segs)
        assert ds[0] is s1.state
        assert ds[1] is s2.state
        assert ds[6] is s3.state

    def test_each_index_is_its_calendar_day(self, materializations):
        segs = _three_segments()
        ds = DailyStates(segs)
        for index, day in enumerate(_days(D1, D9)):
            assert ds[index].date == day
        assert len(materializations) <= 9

    def test_a_quiet_day_by_index_follows_the_rule(self):
        _s1, s2, s3 = segs = _three_segments()
        ds = DailyStates(segs)
        _assert_quiet_day_of(ds[3], s2.state, date(2025, 1, 4))
        _assert_quiet_day_of(ds[8], s3.state, D9)

    @pytest.mark.parametrize(("index", "day"), [(-1, D9), (-3, D7), (-4, D6), (-9, D1)])
    def test_negative_indexes_count_from_the_end(self, index, day):
        ds = DailyStates(_three_segments())
        assert ds[index].date == day

    @pytest.mark.parametrize("index", [9, 10, 46_000, -10, -46_000])
    def test_an_index_out_of_range_is_an_index_error(self, index):
        ds = DailyStates(_three_segments())
        with pytest.raises(IndexError):
            ds[index]

    @pytest.mark.parametrize(
        ("sl", "days"),
        [
            pytest.param(slice(2, 5), _days(date(2025, 1, 3), date(2025, 1, 5)), id="inside-S2"),
            pytest.param(slice(4, 8), _days(date(2025, 1, 5), date(2025, 1, 8)), id="across-S2-S3"),
            pytest.param(slice(None, None), _days(D1, D9), id="whole"),
            pytest.param(slice(7, None), [date(2025, 1, 8), D9], id="open-end"),
            pytest.param(slice(None, 2), [D1, D2], id="open-start"),
            pytest.param(slice(-2, None), [date(2025, 1, 8), D9], id="negative-start"),
            pytest.param(slice(0, -8), [D1], id="negative-stop"),
            pytest.param(slice(5, 2), [], id="empty"),
            pytest.param(slice(3, 100), _days(date(2025, 1, 4), D9), id="stop-past-the-end"),
            pytest.param(slice(2, 5, 1), _days(date(2025, 1, 3), date(2025, 1, 5)), id="explicit-step-1"),
        ],
    )
    def test_a_slice_is_a_list_of_its_days_and_builds_only_them(self, materializations, sl, days):
        ds = DailyStates(_three_segments())
        materializations.clear()

        sliced = ds[sl]

        assert isinstance(sliced, list)
        assert [state.date for state in sliced] == days
        assert len(materializations) <= len(days), f"{len(materializations)} days built for a slice of {len(days)}"

    def test_a_slice_equals_the_same_slice_of_the_dense_list(self):
        ds = DailyStates(_three_segments())
        dense = list(ds)
        for sl in (slice(2, 5), slice(4, 8), slice(None), slice(-3, None)):
            assert ds[sl] == dense[sl]

    def test_iteration_yields_every_day_in_order(self):
        s1, s2, s3 = segs = _three_segments()
        ds = DailyStates(segs)
        states = list(ds)
        assert [state.date for state in states] == _days(D1, D9)
        assert states[0] is s1.state and states[1] is s2.state and states[6] is s3.state
        for state in states[2:6]:
            _assert_quiet_day_of(state, s2.state, state.date)
        for state in states[7:]:
            _assert_quiet_day_of(state, s3.state, state.date)

    def test_iteration_builds_each_day_once(self, materializations):
        ds = DailyStates(_three_segments())
        materializations.clear()
        list(ds)
        assert len(materializations) <= 9

    def test_a_materialized_day_mutated_leaves_later_reads_unchanged(self):
        _s1, s2, _s3 = segs = _three_segments()
        before = _field_values(s2.state)
        ds = DailyStates(segs)

        ds[3].by_type["Bond"] = Decimal("1")
        ds[3].missing_fx_pairs.add("JPY/EUR")

        assert ds[3].by_type == s2.state.by_type
        assert ds[3].missing_fx_pairs == s2.state.missing_fx_pairs
        assert _field_values(s2.state) == before


# =============================================================================
# DailyStates — lookups by day
# =============================================================================


class TestLookups:
    @pytest.mark.parametrize(("day", "which"), [(D1, 0), (D2, 1), (date(2025, 1, 4), 1), (D6, 1), (D7, 2), (D9, 2)])
    def test_segment_at_is_the_stored_segment_containing_the_day(self, materializations, day, which):
        segs = _three_segments()
        ds = DailyStates(segs)
        assert ds.segment_at(day) is segs[which]
        assert materializations == []

    @pytest.mark.parametrize("day", [date(2024, 12, 31), date(2025, 1, 10), date(1900, 1, 1)])
    def test_segment_at_outside_is_none(self, day):
        assert DailyStates(_three_segments()).segment_at(day) is None

    def test_state_on_is_the_exact_day(self, materializations):
        _s1, s2, _s3 = segs = _three_segments()
        ds = DailyStates(segs)
        assert ds.state_on(D2) is s2.state
        materializations.clear()
        quiet = ds.state_on(date(2025, 1, 5))
        _assert_quiet_day_of(quiet, s2.state, date(2025, 1, 5))
        assert len(materializations) <= 1

    @pytest.mark.parametrize("day", [date(2024, 12, 31), date(2025, 1, 10)])
    def test_state_on_outside_is_none(self, day):
        assert DailyStates(_three_segments()).state_on(day) is None

    def test_state_as_of_inside_is_the_exact_day(self, materializations):
        _s1, s2, s3 = segs = _three_segments()
        ds = DailyStates(segs)
        assert ds.state_as_of(D7) is s3.state
        materializations.clear()
        assert ds.state_as_of(date(2025, 1, 4)).date == date(2025, 1, 4)
        _assert_quiet_day_of(ds.state_as_of(date(2025, 1, 4)), s2.state, date(2025, 1, 4))
        assert len(materializations) <= 2

    @pytest.mark.parametrize("day", [date(2025, 1, 10), date(2025, 6, 1), date(2100, 1, 1)])
    def test_state_as_of_after_the_last_day_is_the_last_days_state(self, day):
        _s1, _s2, s3 = segs = _three_segments()
        ds = DailyStates(segs)
        state = ds.state_as_of(day)
        assert state.date == D9
        _assert_quiet_day_of(state, s3.state, D9)

    def test_state_as_of_after_the_last_day_on_a_computed_last_day_is_the_stored_object(self):
        s1, s2 = _three_segments()[:2]
        s3 = StateSegment(start=D7, end=D7, state=_state(D7, 3))
        ds = DailyStates([s1, s2, s3])
        assert ds.state_as_of(date(2025, 2, 1)) is s3.state

    @pytest.mark.parametrize("day", [date(2024, 12, 31), date(1900, 1, 1)])
    def test_state_as_of_before_the_first_day_is_none(self, day):
        assert DailyStates(_three_segments()).state_as_of(day) is None

    def test_lookups_agree_with_the_dense_list_on_every_day_around(self):
        ds = DailyStates(_three_segments())
        dense = list(ds)
        by_day = {state.date: state for state in dense}
        for day in _days(date(2024, 12, 29), date(2025, 1, 12)):
            assert ds.state_on(day) == by_day.get(day)
            expected_as_of = by_day.get(min(day, D9)) if day >= D1 else None
            assert ds.state_as_of(day) == expected_as_of


# =============================================================================
# DailyStates — iter_segments
# =============================================================================


def _spans(segments) -> list[tuple[date, date]]:
    return [(seg.start, seg.end) for seg in segments]


class TestIterSegments:
    def test_open_bounds_yield_every_stored_segment(self, materializations):
        segs = _three_segments()
        ds = DailyStates(segs)
        got = list(ds.iter_segments())
        assert len(got) == 3 and all(a is b for a, b in zip(got, segs, strict=True))
        assert materializations == []

    def test_a_window_wider_than_everything_yields_every_stored_segment(self):
        segs = _three_segments()
        got = list(DailyStates(segs).iter_segments(date(2024, 12, 1), date(2025, 2, 1)))
        assert len(got) == 3 and all(a is b for a, b in zip(got, segs, strict=True))

    def test_a_window_inside_one_segment_is_that_segment_clipped(self):
        _s1, s2, _s3 = segs = _three_segments()
        got = list(DailyStates(segs).iter_segments(date(2025, 1, 3), date(2025, 1, 5)))
        assert _spans(got) == [(date(2025, 1, 3), date(2025, 1, 5))]
        assert got[0].state.date == date(2025, 1, 3)
        _assert_quiet_day_of(got[0].state, s2.state, date(2025, 1, 3))

    def test_a_window_across_segments_clips_both_ends(self):
        _s1, s2, s3 = segs = _three_segments()
        got = list(DailyStates(segs).iter_segments(date(2025, 1, 4), date(2025, 1, 8)))
        assert _spans(got) == [(date(2025, 1, 4), D6), (D7, date(2025, 1, 8))]
        _assert_quiet_day_of(got[0].state, s2.state, date(2025, 1, 4))
        assert got[1].state is s3.state, "a segment clipped at its end only keeps its stored state"

    def test_a_window_starting_on_a_segment_start_keeps_the_stored_segments(self):
        _s1, s2, s3 = segs = _three_segments()
        got = list(DailyStates(segs).iter_segments(D2, D9))
        assert len(got) == 2 and got[0] is s2 and got[1] is s3

    def test_only_date_from(self):
        _s1, s2, s3 = segs = _three_segments()
        got = list(DailyStates(segs).iter_segments(date(2025, 1, 5)))
        assert _spans(got) == [(date(2025, 1, 5), D6), (D7, D9)]
        _assert_quiet_day_of(got[0].state, s2.state, date(2025, 1, 5))
        assert got[1] is s3

    def test_only_date_to(self):
        s1, _s2, _s3 = segs = _three_segments()
        got = list(DailyStates(segs).iter_segments(None, D1))
        assert len(got) == 1 and got[0] is s1

    def test_a_one_day_window_on_a_quiet_day(self):
        _s1, _s2, s3 = segs = _three_segments()
        got = list(DailyStates(segs).iter_segments(date(2025, 1, 8), date(2025, 1, 8)))
        assert _spans(got) == [(date(2025, 1, 8), date(2025, 1, 8))]
        _assert_quiet_day_of(got[0].state, s3.state, date(2025, 1, 8))

    @pytest.mark.parametrize(
        ("date_from", "date_to"),
        [
            pytest.param(date(2024, 12, 1), date(2024, 12, 31), id="before-everything"),
            pytest.param(date(2025, 1, 10), date(2025, 1, 20), id="after-everything"),
            pytest.param(date(2025, 1, 10), None, id="open-end-after-everything"),
            pytest.param(None, date(2024, 12, 31), id="open-start-before-everything"),
        ],
    )
    def test_a_window_outside_yields_nothing(self, materializations, date_from, date_to):
        assert list(DailyStates(_three_segments()).iter_segments(date_from, date_to)) == []
        assert materializations == []

    def test_the_clipped_segments_cover_the_window_contiguously_and_agree_with_the_dense_list(self):
        """For every window around the data: the yielded segments are contiguous, cover exactly the window's part of
        [first_date, last_date], each state is dated on its start, and each day's state is the dense list's."""
        ds = DailyStates(_three_segments())
        by_day = {state.date: state for state in ds}
        around = _days(date(2024, 12, 31), date(2025, 1, 10))
        for date_from in around:
            for date_to in around:
                if date_to < date_from:
                    continue
                got = list(ds.iter_segments(date_from, date_to))
                covered = [day for seg in got for day in _days(seg.start, seg.end)]
                assert covered == [day for day in _days(date_from, date_to) if D1 <= day <= D9], (date_from, date_to)
                for seg in got:
                    assert seg.state.date == seg.start
                    for day in _days(seg.start, seg.end):
                        assert seg.state_on(day) == by_day[day]
                if got:
                    DailyStates(got)  # a valid DailyStates of its own: ascending, contiguous, dated on each start


# =============================================================================
# DailyStates — equality
# =============================================================================


class TestEquality:
    def test_equal_to_its_dense_list(self):
        ds = DailyStates(_three_segments())
        dense = list(ds)
        assert ds == dense
        assert dense == ds

    def test_equal_to_a_dense_list_built_by_hand(self):
        s1, s2, s3 = segs = _three_segments()
        by_hand = [s1.state, s2.state]
        by_hand += [dataclasses.replace(s2.state, date=day, external_cash_flow=Decimal(0), acquisition_funding=None) for day in _days(date(2025, 1, 3), D6)]
        by_hand += [s3.state]
        by_hand += [dataclasses.replace(s3.state, date=day, external_cash_flow=Decimal(0), acquisition_funding=None) for day in _days(date(2025, 1, 8), D9)]
        assert DailyStates(segs) == by_hand

    def test_equal_to_another_daily_states_of_the_same_segments(self):
        assert DailyStates(_three_segments()) == DailyStates(_three_segments())

    def test_not_equal_when_one_day_differs(self):
        ds = DailyStates(_three_segments())
        dense = list(ds)
        dense[4] = dataclasses.replace(dense[4], nav_value=dense[4].nav_value + 1)
        assert ds != dense

    def test_not_equal_when_lengths_differ(self):
        ds = DailyStates(_three_segments())
        dense = list(ds)
        assert ds != dense[:-1]
        assert ds != [*dense, dense[-1]]

    def test_the_empty_sequence_equals_the_empty_list(self):
        assert DailyStates() == []
        assert DailyStates() != list(DailyStates(_three_segments()))
