"""MF5-1b — ``position_period_pnl``: one position's period P&L from its boundary values, in its one home.

Today the formula lives inline in ``PortfolioService.get_positions_contribution`` (``portfolio_service.py``, «Unrealized
change per position»): the unrealized change of a row from its unrealized result at the end of the period's start day
and at its end, plus the internal-transfer tract adjustment (P22), then the period P&L as the sum of the known parts
(unrealized change, realized, income, fees taken out). Workstreams J and Y need the same figure per frame, so it moves,
unchanged, to ``financial_math/portfolio/contributions.py``:

```python
@dataclass(frozen=True, slots=True)
class PositionPeriodPnl:
    unrealized_delta: Decimal | None
    period_pnl: Decimal | None

def position_period_pnl(*, held_at_start, held_at_end, unrealized_start, unrealized_end,
                        transfer_adjustment, realized, income, fees) -> PositionPeriodPnl
```

The rules, the service's own (lifted, never reinterpreted):

- unknown = (held at start and its unrealized at start is None) or (held at end and its unrealized at end is None):
  then the unrealized change is None — never a figure that hides the missing part;
- otherwise, when any of unrealized_end / unrealized_start / transfer_adjustment is known, the change is
  ``(unrealized_end or 0) - (unrealized_start or 0) + (transfer_adjustment or 0)`` (a boundary not held counts as zero);
  with none of the three, None;
- period P&L = ``Decimal("0")`` + the known parts among [change, realized, income, ``0 - fees`` when fees is truthy]
  in that order; None when no part is known. Fees of zero (``Decimal("0")``) are not a part: they are None.

Every expected value is an exact Decimal, compared by value AND by ``as_tuple()`` (the exponent is part of the
contract: ``Decimal("10.50")`` is not ``Decimal("10.5")``).

Pure: no database, no server, no network. The service's parity with this function is proved elsewhere (no AST test).

RED on HEAD 5dc68b650, by absence: ``PositionPeriodPnl`` and ``position_period_pnl`` do not exist in
``contributions.py``; the module fails at collection with ``ImportError``.

Runs in ``./dev.py test services financial-math`` (the runner collects the whole ``test_financial_math/`` directory).
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal

import pytest

from backend.app.services.financial_math.portfolio.contributions import PositionPeriodPnl, position_period_pnl

D = Decimal


def _same(got: Decimal | None, expected: Decimal | None) -> bool:
    """Equal by value and by digits/exponent (None only equals None)."""
    if expected is None or got is None:
        return got is None and expected is None
    return got == expected and got.as_tuple() == expected.as_tuple()


def _call(**overrides) -> PositionPeriodPnl:
    kwargs = {
        "held_at_start": False,
        "held_at_end": False,
        "unrealized_start": None,
        "unrealized_end": None,
        "transfer_adjustment": None,
        "realized": None,
        "income": None,
        "fees": None,
    }
    kwargs.update(overrides)
    return position_period_pnl(**kwargs)


# (id, inputs, expected unrealized_delta, expected period_pnl)
CASES = [
    # ── held at both boundaries ──
    pytest.param(
        {"held_at_start": True, "held_at_end": True, "unrealized_start": D("100.25"), "unrealized_end": D("150.50")},
        D("50.25"),
        D("50.25"),
        id="held-both-unrealized-only",
    ),
    pytest.param(
        {"held_at_start": True, "held_at_end": True, "unrealized_start": D("100.25"), "unrealized_end": D("80"), "realized": D("12.5"), "income": D("3.10"), "fees": D("1.05")},
        D("-20.25"),
        D("-5.70"),
        id="held-both-every-part",
    ),
    pytest.param(
        {"held_at_start": True, "held_at_end": True, "unrealized_start": D("-40"), "unrealized_end": D("-10.0")},
        D("30.0"),
        D("30.0"),
        id="held-both-losses-shrinking",
    ),
    # ── held at one boundary only: the other counts as zero ──
    pytest.param(
        {"held_at_start": False, "held_at_end": True, "unrealized_end": D("75.40"), "income": D("2")},
        D("75.40"),
        D("77.40"),
        id="opened-in-the-period",
    ),
    pytest.param(
        {"held_at_start": True, "held_at_end": False, "unrealized_start": D("60.00"), "realized": D("90.00")},
        D("-60.00"),
        D("30.00"),
        id="closed-in-the-period",
    ),
    # ── an unknown boundary makes the change unknown; the other parts still count ──
    pytest.param(
        {"held_at_start": True, "held_at_end": True, "unrealized_start": None, "unrealized_end": D("10"), "realized": D("5.5")},
        None,
        D("5.5"),
        id="unknown-at-start-held",
    ),
    pytest.param(
        {"held_at_start": True, "held_at_end": True, "unrealized_start": D("10"), "unrealized_end": None, "transfer_adjustment": D("4")},
        None,
        None,
        id="unknown-at-end-held-adjustment-ignored",
    ),
    pytest.param(
        {"held_at_start": False, "held_at_end": True, "unrealized_end": None, "income": D("1.25"), "fees": D("0.25")},
        None,
        D("1.00"),
        id="opened-unknown-at-end-income-and-fees",
    ),
    # ── not held: an unknown value at that boundary is not unknown, it is zero ──
    pytest.param(
        {"held_at_start": False, "held_at_end": True, "unrealized_start": None, "unrealized_end": D("8.8")},
        D("8.8"),
        D("8.8"),
        id="not-held-at-start-none-is-zero",
    ),
    # ── the transfer tract adjustment (P22) ──
    pytest.param(
        {"transfer_adjustment": D("5.00")},
        D("5.00"),
        D("5.00"),
        id="transfer-adjustment-alone",
    ),
    pytest.param(
        {"held_at_start": True, "held_at_end": True, "unrealized_start": D("20"), "unrealized_end": D("35"), "transfer_adjustment": D("-7.5")},
        D("7.5"),
        D("7.5"),
        id="held-both-with-adjustment",
    ),
    pytest.param(
        {"held_at_start": True, "held_at_end": False, "unrealized_start": D("12"), "transfer_adjustment": D("3")},
        D("-9"),
        D("-9"),
        id="sender-closed-by-a-transfer",
    ),
    # ── fees: zero is not a part, None is not a part; a positive fee is taken out ──
    pytest.param(
        {"fees": D("0")},
        None,
        None,
        id="fees-zero-alone-is-nothing",
    ),
    pytest.param(
        {"fees": D("0.00"), "income": D("4.20")},
        None,
        D("4.20"),
        id="fees-zero-with-income",
    ),
    pytest.param(
        {"fees": D("2.30")},
        None,
        D("-2.30"),
        id="fees-alone",
    ),
    pytest.param(
        {"fees": None, "realized": D("-15.75")},
        None,
        D("-15.75"),
        id="fees-none-realized-loss",
    ),
    # ── realized / income alone; zeros that are known ──
    pytest.param(
        {"realized": D("0")},
        None,
        D("0"),
        id="realized-zero-is-a-known-part",
    ),
    pytest.param(
        {"income": D("-3.00")},
        None,
        D("-3.00"),
        id="negative-income-correction",
    ),
    pytest.param(
        {"held_at_start": True, "held_at_end": True, "unrealized_start": D("0"), "unrealized_end": D("0")},
        D("0"),
        D("0"),
        id="held-both-zero-unrealized",
    ),
    # ── nothing known ──
    pytest.param(
        {},
        None,
        None,
        id="all-none",
    ),
]


class TestPositionPeriodPnl:
    @pytest.mark.parametrize(("inputs", "expected_delta", "expected_pnl"), CASES)
    def test_the_table(self, inputs, expected_delta, expected_pnl):
        got = _call(**inputs)
        assert isinstance(got, PositionPeriodPnl)
        assert _same(got.unrealized_delta, expected_delta), f"unrealized_delta {got.unrealized_delta!r}, expected {expected_delta!r}"
        assert _same(got.period_pnl, expected_pnl), f"period_pnl {got.period_pnl!r}, expected {expected_pnl!r}"

    def test_the_arguments_are_keyword_only(self):
        with pytest.raises(TypeError):
            position_period_pnl(True, True, D("1"), D("2"), None, None, None, None)  # type: ignore[misc]

    def test_the_result_is_a_frozen_slotted_dataclass(self):
        got = _call(realized=D("1"))
        assert [f.name for f in dataclasses.fields(PositionPeriodPnl)] == ["unrealized_delta", "period_pnl"]
        with pytest.raises(dataclasses.FrozenInstanceError):
            got.period_pnl = D("2")  # type: ignore[misc]
        assert not hasattr(got, "__dict__"), "slots=True"

    def test_the_period_pnl_sums_in_the_services_order_from_zero(self):
        """The sum starts from ``Decimal("0")`` and adds the parts in order: a result whose exponent depends on the
        start value would show it. ``Decimal("0")`` + ``Decimal("1.0")`` + ``Decimal("2.00")`` = ``Decimal("3.00")``."""
        got = _call(held_at_start=False, held_at_end=True, unrealized_end=D("1.0"), realized=D("2.00"))
        assert _same(got.unrealized_delta, D("1.0"))
        assert _same(got.period_pnl, D("3.00"))
