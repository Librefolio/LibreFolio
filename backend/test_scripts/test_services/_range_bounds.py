"""Lift R13-SEC7-1's bound on date ranges for the suites whose data lives far in the future.

R13-SEC7-1 ends every range that is walked day by day -- the portfolio engine's replay, the summary and the report, the
lots histories, risk's portfolio scope, an AI Export period, and (X-R55) the asset price queries and the FX conversions --
at ``latest_range_end()``, tomorrow. The modules that apply the bound import the function by name, so a test replaces
the name where it is read: replacing it in ``backend.app.utils.datetime_utils`` would change nothing.
"""

from __future__ import annotations

from datetime import date

import pytest

#: Where a range enters: every module that reads ``latest_range_end``, imported by name.
RANGE_BOUND_CONSUMERS = (
    "backend.app.services.financial_math.portfolio.engine",
    "backend.app.services.portfolio_service",
    "backend.app.services.lots_analysis_service",
    "backend.app.services.risk.scope",
    "backend.app.services.ai_export.runtime_service",
    "backend.app.services.assets.price_query",
    "backend.app.api.v1.fx.currencies",
)


def lift_range_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``latest_range_end()`` answer ``date.max`` in every consumer, for as long as ``monkeypatch`` is active.

    These scenarios live in 2032–2091 so they own their rows; as far as the bound against far-future ranges goes, they
    run as if today were after their data (R13-SEC7-1).

    ``setattr`` raises when a consumer does not import the name: a module that stops reading the seam fails here, by
    name, instead of clamping a far-future scenario to tomorrow behind the test's back. ``date.max`` is a bound to compare
    with (``min``), never a day to add to: ``date.max + timedelta(days=1)`` overflows.
    """
    for module in RANGE_BOUND_CONSUMERS:
        monkeypatch.setattr(f"{module}.latest_range_end", lambda: date.max)
