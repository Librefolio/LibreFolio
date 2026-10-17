"""R13-SEC7-1 — AI Export bounds the period before any component sees it.

``AiExportSnapshotService.prepare_request`` copied ``request.period`` into the ``BuildScope`` as it came
(``AiExportPeriod`` only checks the order), and the components loop over the scope's period: a period ending
9999-12-30 or starting 0001-01-01 walks millions of days (e.g. ``technical_shared._bucket_index_by_date``), and the
portfolio and broker datasets hand it to the portfolio engine.

The bound these tests pin, read through ``prepare_request`` (its ``scope``) and ``build_snapshot`` (what
``POST /api/v1/ai-export/snapshot`` runs; the component sees ``context.scope`` and ``context.bucket_plan``):

* ``period_end = min(request.period.end, max_end)`` with ``max_end = today + 1 day`` (one day of slack for users
  east of UTC);
* ``period_start = max(request.period.start, period_end - 100 years)``, and never after ``period_end``.

"100 years before" is pinned as the same month and day 100 calendar years earlier
(``day.replace(year=day.year - 100)``), a 29 February with no counterpart mapping to 28 February. For any day of
2001-2199 that case cannot arise -- a leap year minus 100 is a leap year there -- so the fallback only documents the
choice. Subtracting 36 525 days gives the same day for every end from 2000-02-29 to 2100-02-28; subtracting 36 500
days does not (25 days later).

The service runs over a test-owned registry (one portfolio dataset whose component records the context it is built
with) and a mocked session, as in test_ai_export_runtime_service.py: no database, no network. ``today`` is read before
and after the call: a run that crosses midnight may legitimately see either day.
"""

from __future__ import annotations

import time
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.ai_export_runtime import (
    AI_EXPORT_CATALOG_VERSION,
    AiExportDatasetSelection,
    AiExportDetailLevel,
    AiExportPortfolioSnapshotRequest,
)
from backend.app.services.ai_export.analyses.spec import AnalysisRegistry
from backend.app.services.ai_export.catalog_visibility import CatalogVisibility
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.types import ALL_DETAIL_LEVELS, Domain, PeriodBehavior
from backend.app.services.ai_export.datasets.spec import DatasetRegistry, DatasetSpec
from backend.app.services.ai_export.runtime_service import AiExportSnapshotService

ONE_DAY = timedelta(days=1)
USER_ID = 41
# Moderate values: the old code copies them into the scope as they come, so a red fails fast.
AHEAD = timedelta(days=400)
# The extreme values the API accepts.
EXTREME_START = date(1, 1, 1)
EXTREME_END = date(9999, 12, 30)
QUICK_SECONDS = 30


class _ValuePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int


def _century_before(day: date) -> date:
    """The same month and day 100 calendar years earlier; a 29 February with no counterpart is 28 February."""
    try:
        return day.replace(year=day.year - 100)
    except ValueError:
        return day.replace(year=day.year - 100, day=28)


def _tomorrows(before: date, after: date) -> set[date]:
    """max_end as the service may have read it: tomorrow of the day read before the call, or after it."""
    return {before + ONE_DAY, after + ONE_DAY}


def _mock_session() -> AsyncMock:
    """A session whose user can reach no broker: a portfolio scope over every accessible broker is then empty."""
    session = AsyncMock(spec=AsyncSession)

    async def _execute(statement):  # noqa: ARG001
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        return result

    session.execute.side_effect = _execute
    return session


def _service(seen: list) -> AiExportSnapshotService:
    """One public portfolio dataset whose only component records the scope and bucket plan it is built with."""

    def _build(context, dependencies):  # noqa: ARG001
        seen.append((context.scope, context.bucket_plan))
        return _ValuePayload(value=1)

    component = ComponentSpec(
        component_id="portfolio.summary",
        version=1,
        domains=frozenset({Domain.PORTFOLIO}),
        output_model=_ValuePayload,
        builder=_build,
        period_behavior=PeriodBehavior.WINDOWED,
    )
    dataset = DatasetSpec(
        dataset_id="portfolio.overview",
        version=1,
        domain=Domain.PORTFOLIO,
        display_i18n_key="aiExport.dataset.portfolio.overview.display",
        description_i18n_key="aiExport.dataset.portfolio.overview.description",
        icon="database",
        applicability_code="always_applicable",
        applicable_pages=(Domain.PORTFOLIO.value,),
        required_component_ids=("portfolio.summary",),
        optional_component_ids=(),
        section_order=("portfolio.summary",),
        technical_requirements=(),
        period_semantics=PeriodBehavior.WINDOWED,
        supported_detail_levels=ALL_DETAIL_LEVELS,
        visibility=CatalogVisibility.PUBLIC,
    )
    component_registry = ComponentRegistry((component,))
    dataset_registry = DatasetRegistry((dataset,), component_registry=component_registry)
    return AiExportSnapshotService(
        _mock_session(),
        component_registry=component_registry,
        dataset_registry=dataset_registry,
        analysis_registry=AnalysisRegistry((), dataset_registry=dataset_registry),
    )


def _request(start: date, end: date) -> AiExportPortfolioSnapshotRequest:
    return AiExportPortfolioSnapshotRequest(
        domain="portfolio",
        selection=AiExportDatasetSelection(kind="dataset", id="portfolio.overview", version=1),
        detail_level=AiExportDetailLevel.STANDARD,
        period={"start": start, "end": end},
        target_currency="EUR",
        expected_catalog_version=AI_EXPORT_CATALOG_VERSION,
    )


async def _prepared_period(start: date, end: date) -> tuple[date, date]:
    prepared = await _service([]).prepare_request(USER_ID, _request(start, end))
    return prepared.scope.period_start, prepared.scope.period_end


class TestPeriodIsBoundedWhenTheScopeIsBuilt:
    @pytest.mark.asyncio
    async def test_end_after_tomorrow_is_clamped_to_tomorrow(self):
        """Red (R13-SEC7-1): a period ending 400 days ahead gets scope.period_end = tomorrow (max_end = today + 1);
        its start, 30 days ago, is inside the bound and stays.

        Before: prepare_request copied request.period.end into the BuildScope, 400 days past today (9999-12-30 as
        well), and every component looped to it."""
        before = date.today()
        start = before - timedelta(days=30)

        period_start, period_end = await _prepared_period(start, before + AHEAD)
        after = date.today()

        assert period_end in _tomorrows(before, after), f"scope.period_end is {period_end}, expected tomorrow ({before + ONE_DAY})"
        assert period_start == start

    @pytest.mark.asyncio
    async def test_start_more_than_a_century_before_the_end_moves_to_a_century_before(self):
        """Red (R13-SEC7-1): a period from 0001-01-01 to today gets scope.period_start = today - 100 years (same
        month and day, see the module docstring); its end, today, is inside the bound and stays.

        Before: prepare_request copied 0001-01-01 into the BuildScope, ~740 000 days for the components to walk."""
        today = date.today()

        period_start, period_end = await _prepared_period(EXTREME_START, today)

        assert period_end == today
        assert period_start == _century_before(today), f"scope.period_start is {period_start}, expected {_century_before(today)}"

    @pytest.mark.asyncio
    async def test_period_entirely_after_tomorrow_collapses_on_tomorrow(self):
        """Red (R13-SEC7-1): a period from 300 to 400 days ahead ends at tomorrow and, since its start may never
        be after its end, starts there too: the scope is the single day max_end.

        Before: prepare_request copied the future period as it came."""
        before = date.today()

        period_start, period_end = await _prepared_period(before + timedelta(days=300), before + AHEAD)
        after = date.today()

        assert period_end in _tomorrows(before, after), f"scope.period_end is {period_end}, expected tomorrow ({before + ONE_DAY})"
        assert period_start == period_end, f"scope.period_start is {period_start}, after or before the clamped end {period_end}"

    @pytest.mark.asyncio
    async def test_components_and_bucket_plan_receive_the_bounded_period(self):
        """Red (R13-SEC7-1): build_snapshot (POST /api/v1/ai-export/snapshot) with a period ending 400 days ahead
        hands every component a scope and a bucket plan that end at tomorrow.

        Before: the component was built over the raw period, 400 days past today, and the bucket plan with it."""
        seen: list = []
        before = date.today()
        start = before - timedelta(days=30)

        await _service(seen).build_snapshot(USER_ID, _request(start, before + AHEAD))
        after = date.today()

        ((scope, bucket_plan),) = seen
        assert scope.period_end in _tomorrows(before, after), f"the component saw period_end {scope.period_end}, expected tomorrow ({before + ONE_DAY})"
        assert scope.period_start == start
        assert (bucket_plan.start, bucket_plan.end) == (scope.period_start, scope.period_end), "the bucket plan must cover the bounded period"


class TestPeriodWithinBoundsIsUnchanged:
    @pytest.mark.asyncio
    async def test_past_period_is_unchanged(self):
        """Guard: a period from 90 days ago to today passes into the scope unchanged."""
        today = date.today()
        start = today - timedelta(days=90)

        assert await _prepared_period(start, today) == (start, today)

    @pytest.mark.asyncio
    async def test_period_on_the_bounds_is_unchanged(self):
        """Guard: a period from exactly 100 years before tomorrow to tomorrow sits on both bounds and passes
        unchanged -- tomorrow is inside the bound (one day of slack), and so is the century before it."""
        tomorrow = date.today() + ONE_DAY
        start = _century_before(tomorrow)

        assert await _prepared_period(start, tomorrow) == (start, tomorrow)


class TestExtremeRangesFinishQuickly:
    """Guards (new code only): the extreme period the API accepts -- 0001-01-01 to 9999-12-30 -- comes back
    bounded, well within QUICK_SECONDS.

    Unlike the engine and the lots, the old code does not hang here: prepare_request only copies the period, so
    these fail fast on it (the build_snapshot one after building a bucket plan over ~3.65 M days). They sit in the
    class of the same name so that one ``-k "not TestExtremeRangesFinishQuickly"`` deselects every extreme case."""

    @pytest.mark.asyncio
    async def test_prepare_with_0001_01_01_to_9999_12_30(self):
        """Guard (new code only): the scope of the extreme period is [tomorrow - 100 years, tomorrow]."""
        before = date.today()
        started = time.monotonic()
        period_start, period_end = await _prepared_period(EXTREME_START, EXTREME_END)
        elapsed = time.monotonic() - started
        after = date.today()

        assert elapsed < QUICK_SECONDS, f"prepare_request took {elapsed:.1f}s"
        assert period_end in _tomorrows(before, after), f"scope.period_end is {period_end}, expected tomorrow ({before + ONE_DAY})"
        assert period_start == _century_before(period_end), f"scope.period_start is {period_start}, expected {_century_before(period_end)}"

    @pytest.mark.asyncio
    async def test_snapshot_with_0001_01_01_to_9999_12_30(self):
        """Guard (new code only): build_snapshot of the extreme period builds its component over
        [tomorrow - 100 years, tomorrow], fast."""
        seen: list = []
        before = date.today()
        started = time.monotonic()
        await _service(seen).build_snapshot(USER_ID, _request(EXTREME_START, EXTREME_END))
        elapsed = time.monotonic() - started
        after = date.today()

        assert elapsed < QUICK_SECONDS, f"build_snapshot took {elapsed:.1f}s"
        ((scope, bucket_plan),) = seen
        assert scope.period_end in _tomorrows(before, after)
        assert scope.period_start == _century_before(scope.period_end)
        assert (bucket_plan.start, bucket_plan.end) == (scope.period_start, scope.period_end)
