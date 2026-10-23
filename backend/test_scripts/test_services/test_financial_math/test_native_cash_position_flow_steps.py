"""MF5-1b — ``NativeCash.position_flow_steps``: each position's income and costs as cumulative steps by date.

``NativeCash.flows(date_from, date_to)`` answers one window: income (DIVIDEND, INTEREST, signed) and costs (FEE, TAX,
absolute) by ``(broker_id, asset_id)``, each movement converted at its own date and counted at its share. Workstreams J
and Y need the same figures on every day of a period, per position: asking ``flows`` once per day walks every movement
once per day. The cure is one walk that returns the steps:

``position_flow_steps(date_from: date | None = None, date_to: date | None = None)
-> dict[tuple[int, int], list[tuple[date, Decimal, Decimal]]]``

- keys: the ``(broker_id, asset_id)`` with at least one income or cost movement that has a position, a conversion
  (value not None), and a date in ``(date_from, date_to]`` — the window and counting rules of ``flows()``;
- one entry per date holding such a movement of that position (a zero amount included), ascending:
  ``(day, income cumulative, costs cumulative)``, the cumulatives being exactly
  ``flows(date_from, day).income_by_position.get(key, Decimal("0"))`` and ``.costs_by_position.get(...)`` (value and
  ``as_tuple()``) when the movements are stored in date order, as the engine loads them (date, id);
- unallocated movements (asset_id None), other types and missing conversions never appear.

The book (report EUR, built by hand like ``test_native_cash.py``, in date order): two brokers (A at share 1, B at 0.5),
two assets, dividends and interest, a negative dividend correction, fees and taxes, a zero fee, a USD dividend
converted (B, at 0.5), a GBP dividend with no conversion (skipped) and another converted later, a JPY dividend never
converted (its position never appears), deposits, a BUY and unallocated interest and tax (never appear).

What is tested: hand-computed steps for the whole history (anchors); for several windows (open and closed bounds, a
bound on a movement day, an empty window), the keys, the dates and both cumulatives against ``flows`` on every listed
day, and on every day of the window the last entry on or before it against ``flows`` (no entry: the key is absent from
``flows``); the defaults are ``(None, None)``.

Ambiguity resolved: a position with income but no cost yet (or the reverse) carries ``Decimal("0")`` on the other
side — ``flows``' own zero (``_ZERO``), compared by ``as_tuple()``.

Pure: no database, no server, no network; ``unit_rates`` is empty (no balance is valued here).

RED on HEAD 5dc68b650, by absence: ``NativeCash`` has no ``position_flow_steps``; every test fails with
``AttributeError`` (the module collects).

Runs in ``./dev.py test services financial-math`` (the runner collects the whole ``test_financial_math/`` directory).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.services.financial_math.native_cash import CashMovement, NativeCash

A, B = 10, 20
X, Y = 100, 200
ZERO = Decimal("0")

# (id, type, day, broker, asset, currency, amount, share, converted) — stored in date order, as the engine loads them.
_ROWS = [
    (1, "DEPOSIT", date(2025, 1, 2), A, None, "EUR", "1000", "1", "1000"),
    (2, "DIVIDEND", date(2025, 1, 3), A, X, "EUR", "10.50", "1", "10.50"),
    (3, "FEE", date(2025, 1, 3), A, X, "EUR", "-1.20", "1", "-1.20"),
    (4, "DIVIDEND", date(2025, 1, 3), B, X, "USD", "20", "0.5", "18.40"),
    (5, "TAX", date(2025, 1, 5), A, X, "EUR", "-2", "1", "-2"),
    (6, "INTEREST", date(2025, 1, 5), A, None, "EUR", "3", "1", "3"),
    (7, "DIVIDEND", date(2025, 1, 6), A, Y, "GBP", "5", "1", None),  # missing conversion: skipped
    (8, "DIVIDEND", date(2025, 1, 7), A, X, "EUR", "-4.00", "1", "-4.00"),  # a negative correction keeps its sign
    (9, "FEE", date(2025, 1, 8), B, X, "EUR", "0", "0.5", "0"),  # a zero amount is still an entry
    (10, "BUY", date(2025, 1, 9), A, X, "EUR", "-500", "1", "-500"),
    (11, "DIVIDEND", date(2025, 1, 10), A, Y, "GBP", "6", "1", "7.02"),
    (12, "DIVIDEND", date(2025, 1, 11), B, Y, "JPY", "100", "0.5", None),  # never converted: (B, Y) never appears
    (13, "TAX", date(2025, 1, 12), B, None, "EUR", "-1", "0.5", "-1"),
    (14, "INTEREST", date(2025, 1, 12), A, X, "EUR", "1.25", "1", "1.25"),
    (15, "TAX", date(2025, 1, 12), B, X, "USD", "-3", "0.5", "-2.76"),
    (16, "WITHDRAWAL", date(2025, 1, 14), A, None, "EUR", "-100", "1", "-100"),
]

FIRST, LAST = date(2025, 1, 1), date(2025, 1, 15)


def _cash() -> NativeCash:
    movements = tuple(CashMovement(movement_id=mid, transaction_type=kind, date=day, broker_id=broker, asset_id=asset, currency=currency, amount=Decimal(amount), share=Decimal(share)) for mid, kind, day, broker, asset, currency, amount, share, _converted in _ROWS)
    converted = tuple(None if value is None else Decimal(value) for *_rest, value in _ROWS)
    return NativeCash(report_currency="EUR", movements=movements, converted=converted, unit_rates={})


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _same(got: Decimal, expected: Decimal) -> bool:
    return isinstance(got, Decimal) and got == expected and got.as_tuple() == expected.as_tuple()


def _flows_pair(cash: NativeCash, date_from: date | None, day: date, key: tuple[int, int]) -> tuple[Decimal, Decimal] | None:
    """``flows(date_from, day)``'s income and costs of ``key``; None when the key is in neither."""
    flows = cash.flows(date_from, day)
    if key not in flows.income_by_position and key not in flows.costs_by_position:
        return None
    return flows.income_by_position.get(key, ZERO), flows.costs_by_position.get(key, ZERO)


def _expected_dates(date_from: date | None, date_to: date | None) -> dict[tuple[int, int], list[date]]:
    """From the rows: the dates of each position's counted income/cost movements in the window."""
    dates: dict[tuple[int, int], set[date]] = {}
    for _mid, kind, day, broker, asset, _currency, _amount, _share, converted in _ROWS:
        if kind not in {"DIVIDEND", "INTEREST", "FEE", "TAX"} or asset is None or converted is None:
            continue
        if (date_from is not None and day <= date_from) or (date_to is not None and day > date_to):
            continue
        dates.setdefault((broker, asset), set()).add(day)
    return {key: sorted(days) for key, days in dates.items()}


WINDOWS = [
    pytest.param(None, None, id="whole-history"),
    pytest.param(date(2025, 1, 3), None, id="open-left-on-a-movement-day"),
    pytest.param(None, date(2025, 1, 7), id="closed-right-on-a-movement-day"),
    pytest.param(date(2025, 1, 4), date(2025, 1, 10), id="closed-both"),
    pytest.param(date(2025, 1, 2), date(2025, 1, 3), id="one-day"),
    pytest.param(date(2025, 1, 12), None, id="after-every-position-movement"),
]


class TestTheWholeHistoryByHand:
    """Anchors: the steps of the whole history, computed by hand from the rows."""

    def test_the_keys(self):
        steps = _cash().position_flow_steps()
        assert set(steps) == {(A, X), (B, X), (A, Y)}, "no unallocated movement, no never-converted position"

    def test_a_x(self):
        """Dividend 10.50 and fee 1.20 (01-03), tax 2 (01-05), a -4.00 correction (01-07), interest 1.25 (01-12)."""
        got = _cash().position_flow_steps()[(A, X)]
        expected = [
            (date(2025, 1, 3), Decimal("10.50"), Decimal("1.20")),
            (date(2025, 1, 5), Decimal("10.50"), Decimal("3.20")),
            (date(2025, 1, 7), Decimal("6.50"), Decimal("3.20")),
            (date(2025, 1, 12), Decimal("7.75"), Decimal("3.20")),
        ]
        assert [day for day, _i, _c in got] == [day for day, _i, _c in expected], "one entry per movement date; the BUY of 01-09 is none"
        for (day, income, costs), (_d, want_income, want_costs) in zip(got, expected, strict=True):
            assert _same(income, want_income), f"{day}: income {income!r}"
            assert _same(costs, want_costs), f"{day}: costs {costs!r}"

    def test_b_x_at_its_share(self):
        """At 0.5: a USD dividend converted 18.40 (9.200), a zero fee (an entry), a USD tax converted -2.76 (1.380)."""
        got = _cash().position_flow_steps()[(B, X)]
        expected = [
            (date(2025, 1, 3), Decimal("9.200"), ZERO),
            (date(2025, 1, 8), Decimal("9.200"), Decimal("0.0")),
            (date(2025, 1, 12), Decimal("9.200"), Decimal("1.380")),
        ]
        assert [day for day, _i, _c in got] == [day for day, _i, _c in expected]
        for (day, income, costs), (_d, want_income, want_costs) in zip(got, expected, strict=True):
            assert _same(income, want_income), f"{day}: income {income!r}"
            assert _same(costs, want_costs), f"{day}: costs {costs!r}"

    def test_a_y_skips_the_missing_conversion(self):
        """The GBP dividend of 01-06 has no conversion: no entry; the one of 01-10 is converted 7.02."""
        got = _cash().position_flow_steps()[(A, Y)]
        assert len(got) == 1
        day, income, costs = got[0]
        assert day == date(2025, 1, 10)
        assert _same(income, Decimal("7.02"))
        assert _same(costs, ZERO)


class TestAgainstFlows:
    @pytest.mark.parametrize(("date_from", "date_to"), WINDOWS)
    def test_the_keys_and_the_dates(self, date_from, date_to):
        steps = _cash().position_flow_steps(date_from, date_to)
        expected = _expected_dates(date_from, date_to)
        assert set(steps) == set(expected)
        for key, entries in steps.items():
            assert isinstance(entries, list)
            assert [entry[0] for entry in entries] == expected[key], key

    @pytest.mark.parametrize(("date_from", "date_to"), WINDOWS)
    def test_every_entry_is_flows_up_to_its_day(self, date_from, date_to):
        cash = _cash()
        steps = cash.position_flow_steps(date_from, date_to)
        assert steps or date_from == date(2025, 1, 12), "precondition: the window holds position movements"
        for key, entries in steps.items():
            for entry in entries:
                assert isinstance(entry, tuple) and len(entry) == 3
                day, income, costs = entry
                want = _flows_pair(cash, date_from, day, key)
                assert want is not None, f"{key} {day}: flows does not know the key"
                assert _same(income, want[0]), f"{key} {day}: income {income!r}, flows {want[0]!r}"
                assert _same(costs, want[1]), f"{key} {day}: costs {costs!r}, flows {want[1]!r}"

    @pytest.mark.parametrize(("date_from", "date_to"), WINDOWS)
    def test_every_day_reads_the_last_entry_on_or_before_it(self, date_from, date_to):
        """On every day of the window (and the days around the listed ones), the last entry on or before the day is
        ``flows(date_from, day)`` for that key; with no entry yet, ``flows`` does not know the key."""
        cash = _cash()
        steps = cash.position_flow_steps(date_from, date_to)
        first = (date_from + timedelta(days=1)) if date_from is not None else FIRST
        last = date_to if date_to is not None else LAST
        keys = set(steps) | {(A, X), (B, X), (A, Y), (B, Y)}
        for key in keys:
            entries = steps.get(key, [])
            for day in _days(first, last):
                before = [entry for entry in entries if entry[0] <= day]
                want = _flows_pair(cash, date_from, day, key)
                if not before:
                    assert want is None, f"{key} {day}: no entry, but flows gives {want}"
                    continue
                _d, income, costs = before[-1]
                assert want is not None, f"{key} {day}"
                assert _same(income, want[0]), f"{key} {day}: income {income!r}, flows {want[0]!r}"
                assert _same(costs, want[1]), f"{key} {day}: costs {costs!r}, flows {want[1]!r}"

    def test_an_empty_window_has_no_key(self):
        cash = _cash()
        assert cash.position_flow_steps(date(2025, 1, 12), date(2025, 1, 15)) == {}
        assert cash.position_flow_steps(date(2025, 1, 13), date(2025, 1, 14)) == {}

    def test_the_defaults_are_the_whole_history(self):
        cash = _cash()
        assert cash.position_flow_steps() == cash.position_flow_steps(None, None)
        assert cash.position_flow_steps(date_to=date(2025, 1, 7)) == cash.position_flow_steps(None, date(2025, 1, 7))
