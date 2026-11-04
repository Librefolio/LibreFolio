"""MF-A3 (workstream MF, wave 6) — the Performance table's annualized column: a closed flight too short to annualize.

Module under test: ``backend/app/services/financial_math/portfolio/contributions.py``.

What changed (HEAD ``8ebdb3857`` → the working tree): ``closed_flight_too_short(opened, closed, date_from)`` is new. It
says whether a position closed in the period was held in it under the 30 days ``cumulative_to_annualized`` needs: the
flight runs from its first opening, clamped to ``date_from``, to its last close, and the floor is
``returns.annualizes``, the same predicate the annualization uses. The service uses it on a fully sold row whose closed
rule gives no value: that row shows no annualized return instead of the period's general rule
(``test_financial/test_positions_contribution_short_flight_and_open_base.py``).

(MF-A11, the open row's ``left_base``, was reverted by MF before landing — the numbers did not confirm it — so this
file asserts nothing about it; the name of the file stays as briefed.)

Guards, unchanged on HEAD and on the tree: the closed row of 100 units bought at 10 on 2025-01-10 and sold at 9 on
2025-04-20 annualizes −10 % over its 100 days of flight, −0.319254 (``closed_position_annualized``); under 30 days the
closed rule gives None, which is what the service's general-rule fallback used to see.

Red on HEAD ``8ebdb3857`` (the module of that commit, extracted with ``git archive``): the whole file fails at
collection, ``ImportError: cannot import name 'closed_flight_too_short' from
'backend.app.services.financial_math.portfolio.contributions'`` — new API.

Isolation: PURE — no database, no server, no network, no clock. Runs in ``./dev.py test services financial-math``
(the runner collects the whole ``test_financial_math/`` directory); alone:
``./dev.py test services financial-math test_contributions_short_flight_and_open_base``.

Reference: backend/app/services/financial_math/portfolio/contributions.py (closed_flight_too_short,
closed_position_annualized), backend/app/services/financial_math/returns.py (annualizes, cumulative_to_annualized).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from backend.app.services.financial_math.portfolio.contributions import closed_flight_too_short, closed_position_annualized
from backend.app.services.financial_math.returns import annualizes

D = Decimal

DATE_FROM = date(2025, 1, 1)
OPENED = date(2025, 1, 10)
SOLD = date(2025, 4, 20)


class TestClosedRuleUnchanged:
    """Guard: the closed rule itself is HEAD's."""

    def test_the_closed_row_over_its_flight(self):
        """All 100 sold at 9 after 100 days: −100 on 1 000 over the flight."""
        assert (SOLD - OPENED).days == 100
        assert closed_position_annualized(D("-100"), D("1000"), OPENED, SOLD, DATE_FROM) == D("-0.319254")

    def test_under_thirty_days_the_closed_rule_gives_none(self):
        """Ten days of flight: no value from the closed rule — the case the service now shows as «—»."""
        assert closed_position_annualized(D("100"), D("1000"), DATE_FROM - timedelta(days=31), DATE_FROM + timedelta(days=10), DATE_FROM) is None


class TestClosedFlightTooShort:
    """MF-A3: under the 30-day floor of ``cumulative_to_annualized`` — the same predicate, ``annualizes``."""

    def test_ten_days_is_too_short(self):
        assert closed_flight_too_short(OPENED, OPENED + timedelta(days=10), DATE_FROM) is True

    def test_thirty_days_is_enough(self):
        assert closed_flight_too_short(OPENED, OPENED + timedelta(days=30), DATE_FROM) is False

    def test_twenty_nine_days_is_too_short(self):
        assert closed_flight_too_short(OPENED, OPENED + timedelta(days=29), DATE_FROM) is True

    def test_clamped_to_date_from(self):
        """Opened long before the period: the flight counts from ``date_from``. 19 days after it is too short, 40 is
        not — although both flights are over a month from the opening."""
        opened = date(2024, 6, 1)
        assert closed_flight_too_short(opened, DATE_FROM + timedelta(days=19), DATE_FROM) is True
        assert closed_flight_too_short(opened, DATE_FROM + timedelta(days=40), DATE_FROM) is False

    def test_without_date_from_from_the_opening(self):
        assert closed_flight_too_short(OPENED, OPENED + timedelta(days=10), None) is True
        assert closed_flight_too_short(OPENED, SOLD, None) is False

    def test_an_unknown_end_is_not_short(self):
        """No opening or no close: nothing to measure, never «too short»."""
        assert closed_flight_too_short(None, SOLD, DATE_FROM) is False
        assert closed_flight_too_short(OPENED, None, DATE_FROM) is False

    def test_the_floor_is_the_annualization_s(self):
        """The predicate agrees with ``annualizes`` on the day count, both sides of the floor."""
        for days in (0, 1, 29, 30, 31, 365):
            assert closed_flight_too_short(OPENED, OPENED + timedelta(days=days), None) is (not annualizes(days)), days
