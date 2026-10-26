"""Unit tests for DerivedViewsBuilder.build_data_quality_report().

Verifies that all 5 active portfolio IssueCodes are generated correctly
from input data. Pure tests — no DB, no async.

``TestTransferShareMismatchIssue`` (J-43b) reads ``ShareMismatch`` from ``models`` inside its tests, so on a ``models``
without it only those tests fail, never the module's collection. ``TestReportSentences`` (MF-SEC8-2a) reads two files and
writes none: the builder's source and the four UI catalogues (merged in memory by ``scripts.i18n_catalog.load_catalog``).

MF-PAV-L1: the report no longer warns about transactions dated before 1900 (the engine's history starts on the first row,
whatever its year): ``TestNoTransactionsBeforeFloorIssue`` pins that the builder has no ``rows_before_floor`` parameter and
``IssueCode`` no ``TRANSACTIONS_BEFORE_FLOOR``.

``TestNonIsoCurrencyIssue`` (E-19b2) passes ``non_iso_currency_assets`` and ``report_currency`` through one helper that
turns the TypeError of a builder without them into a failure, and ``TestNonIsoCurrencyAssets`` reads
``PortfolioService._non_iso_currency_assets`` with ``getattr``: before E-19b2 only their tests fail, never the module's
collection.
"""

import ast
import inspect
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import backend.app.services.financial_math.portfolio.models as portfolio_models
from backend.app.schemas.common import DateSpan, shown_currency_text, suggested_iso_currency
from backend.app.schemas.portfolio import (
    DataQualityStatus,
    IssueCode,
    IssueDomain,
    IssueSeverity,
    MissingPriceAsset,
    StalePriceAsset,
)
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services.financial_math.portfolio.data_quality import build_data_quality_report
from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState
from backend.app.services.portfolio_service import HeldAssetQuoteFacts, PortfolioService
from backend.app.utils.currency_units import minor_unit_factor
from scripts.i18n_catalog import load_catalog

# =============================================================================
# HELPERS
# =============================================================================


def _make_views(daily_states: list[DailyPortfolioState] | None = None) -> DerivedViewsBuilder:
    """Build a DerivedViewsBuilder with the given daily states (or empty list)."""
    return DerivedViewsBuilder(daily_states=daily_states or [], target_currency="EUR")


def _make_missing_asset(asset_id: int = 1, name: str = "Test Asset") -> MissingPriceAsset:
    return MissingPriceAsset(
        asset_id=asset_id,
        name=name,
        broker_id=1,
        broker_name="TestBroker",
        quantity=Decimal("10"),
        currency="USD",
    )


def _make_stale_asset(asset_id: int = 2, name: str = "Stale Asset") -> StalePriceAsset:
    return StalePriceAsset(
        asset_id=asset_id,
        name=name,
        last_price_date=date(2024, 1, 1),
        stale_days=30,
    )


def _make_missing_fx(pair: str = "EUR-USD", dates: list[date] | None = None) -> WACMissingPairInfo:
    mock = MagicMock(spec=WACMissingPairInfo)
    mock.pair = pair
    mock.dates = dates or [date(2025, 1, 1)]
    return mock


def _incomplete_state(dt: str) -> DailyPortfolioState:
    """Create a DailyPortfolioState with nav_complete=False."""
    state = MagicMock(spec=DailyPortfolioState)
    state.date = date.fromisoformat(dt)
    state.nav_complete = False
    state.missing_fx_pairs = set()
    return state


def _complete_state(dt: str) -> DailyPortfolioState:
    """Create a DailyPortfolioState with nav_complete=True."""
    state = MagicMock(spec=DailyPortfolioState)
    state.date = date.fromisoformat(dt)
    state.nav_complete = True
    state.missing_fx_pairs = set()
    return state


# =============================================================================
# MISSING_PRICE
# =============================================================================


class TestMissingPriceIssue:
    def test_no_missing_price_produces_no_issue(self):
        views = _make_views()
        report = views.build_data_quality_report()
        codes = [i.code for i in report.issues]
        assert IssueCode.MISSING_PRICE not in codes

    def test_missing_price_produces_error_issue(self):
        views = _make_views()
        report = views.build_data_quality_report(missing_price_assets_dto=[_make_missing_asset()])
        issue = next(i for i in report.issues if i.code == IssueCode.MISSING_PRICE)
        assert issue.severity == IssueSeverity.ERROR

    def test_missing_price_includes_asset_names(self):
        assets = [_make_missing_asset(1, "Apple"), _make_missing_asset(2, "Google")]
        views = _make_views()
        report = views.build_data_quality_report(missing_price_assets_dto=assets)
        issue = next(i for i in report.issues if i.code == IssueCode.MISSING_PRICE)
        assert "Apple" in issue.affected_asset_names
        assert "Google" in issue.affected_asset_names
        assert issue.count == 2

    def test_missing_price_has_navigate_asset_cta(self):
        views = _make_views()
        report = views.build_data_quality_report(missing_price_assets_dto=[_make_missing_asset()])
        issue = next(i for i in report.issues if i.code == IssueCode.MISSING_PRICE)
        assert issue.cta_action == "navigate_asset"

    def test_missing_price_also_in_legacy_field(self):
        assets = [_make_missing_asset()]
        views = _make_views()
        report = views.build_data_quality_report(missing_price_assets_dto=assets)
        assert report.missing_price_assets == assets


# =============================================================================
# STALE_PRICE
# =============================================================================


class TestStalePriceIssue:
    def test_no_stale_price_produces_no_issue(self):
        views = _make_views()
        report = views.build_data_quality_report()
        codes = [i.code for i in report.issues]
        assert IssueCode.STALE_PRICE not in codes

    def test_stale_price_produces_warning_issue(self):
        views = _make_views()
        report = views.build_data_quality_report(stale_prices_dto=[_make_stale_asset()])
        issue = next(i for i in report.issues if i.code == IssueCode.STALE_PRICE)
        assert issue.severity == IssueSeverity.WARNING

    def test_stale_price_includes_asset_names(self):
        assets = [_make_stale_asset(1, "OldAsset")]
        views = _make_views()
        report = views.build_data_quality_report(stale_prices_dto=assets)
        issue = next(i for i in report.issues if i.code == IssueCode.STALE_PRICE)
        assert "OldAsset" in issue.affected_asset_names
        assert issue.count == 1

    def test_stale_price_cta_syncs_asset_prices(self):
        """D8 (30/09): the STALE_PRICE CTA is the «Sincronizza» button.

        A stale quote is cured by fetching the provider again, not by opening the
        asset page, so the issue asks the dashboard for ``sync_asset_prices``.
        ``cta_target`` is deliberately not asserted: the dashboard syncs every id in
        ``affected_asset_ids``, the target carries no contract.
        """
        views = _make_views()
        report = views.build_data_quality_report(stale_prices_dto=[_make_stale_asset(7, "Stale ETF")])
        issue = next(i for i in report.issues if i.code == IssueCode.STALE_PRICE)
        assert issue.cta_action == "sync_asset_prices"

    def test_stale_price_keeps_message_key_count_and_affected_assets(self):
        """Control for D8: only the CTA changes; the message contract stays.

        WARNING, ``dataQuality.stalePrice`` with ``{count}``, and the affected ids and
        names aligned with the input order — the banner zips the two arrays.
        """
        assets = [_make_stale_asset(7, "Stale ETF"), _make_stale_asset(8, "Stale Bond")]
        views = _make_views()
        report = views.build_data_quality_report(stale_prices_dto=assets)
        issue = next(i for i in report.issues if i.code == IssueCode.STALE_PRICE)
        assert issue.severity == IssueSeverity.WARNING
        assert issue.message_i18n_key == "dataQuality.stalePrice"
        assert issue.message_params["count"] == 2
        assert issue.count == 2
        assert issue.affected_asset_ids == [7, 8]
        assert issue.affected_asset_names == ["Stale ETF", "Stale Bond"]

    def test_stale_prices_alone_report_carried_forward_status(self):
        """Control for D8 §3: a stale quote is carried forward, not a partial result.

        With nothing worse in the report (no missing price, FX or NAV day), the
        derived status is ``carried_forward`` and ``stale_prices`` is the input as
        given. The status is derived by the schema, so this holds as soon as
        ``get_summary`` passes ``stale_prices_dto`` at all.
        """
        stale = [_make_stale_asset(7, "Stale ETF")]
        views = _make_views()
        report = views.build_data_quality_report(stale_prices_dto=stale)
        assert report.stale_prices == stale
        assert report.data_quality_status == DataQualityStatus.CARRIED_FORWARD


# =============================================================================
# MISSING_FX_MARKET
# =============================================================================


class TestMissingFxMarketIssue:
    def test_no_missing_fx_produces_no_issue(self):
        views = _make_views()
        report = views.build_data_quality_report()
        codes = [i.code for i in report.issues]
        assert IssueCode.MISSING_FX_MARKET not in codes

    def test_missing_fx_produces_warning_issue(self):
        views = _make_views()
        report = views.build_data_quality_report(missing_fx_pairs_dto=[_make_missing_fx("EUR-USD")])
        issue = next(i for i in report.issues if i.code == IssueCode.MISSING_FX_MARKET)
        assert issue.severity == IssueSeverity.WARNING

    def test_missing_fx_deduplicates_pairs(self):
        # Same pair appearing twice (e.g. from multiple assets)
        views = _make_views()
        report = views.build_data_quality_report(missing_fx_pairs_dto=[_make_missing_fx("EUR-USD"), _make_missing_fx("EUR-USD")])
        issue = next(i for i in report.issues if i.code == IssueCode.MISSING_FX_MARKET)
        assert issue.affected_fx_pairs == ["EUR-USD"]
        assert issue.count == 1

    def test_missing_fx_lists_pairs(self):
        views = _make_views()
        report = views.build_data_quality_report(missing_fx_pairs_dto=[_make_missing_fx("EUR-USD"), _make_missing_fx("EUR-GBP")])
        issue = next(i for i in report.issues if i.code == IssueCode.MISSING_FX_MARKET)
        assert "EUR-USD" in issue.affected_fx_pairs
        assert "EUR-GBP" in issue.affected_fx_pairs

    def test_missing_fx_has_add_fx_pair_cta(self):
        views = _make_views()
        report = views.build_data_quality_report(missing_fx_pairs_dto=[_make_missing_fx("EUR-USD")])
        issue = next(i for i in report.issues if i.code == IssueCode.MISSING_FX_MARKET)
        assert issue.cta_action == "add_fx_pair"

    def test_configured_real_provider_missing_fx_produces_rates_issue(self):
        views = _make_views()
        report = views.build_data_quality_report(
            missing_fx_pairs_dto=[_make_missing_fx("RON/EUR", [date(2025, 1, 1), date(2025, 1, 3)])],
            configured_fx_pairs={"EUR-RON"},
            real_provider_fx_pairs={"EUR-RON"},
        )
        issue = next(i for i in report.issues if i.code == IssueCode.MISSING_FX_RATES)
        assert issue.cta_action == "sync_fx_pair"
        assert issue.cta_target == "EUR-RON"
        assert issue.message_i18n_key == "dataQuality.missingFxRates"
        assert issue.message_params == {"count": 1, "date_from": "2025-01-01", "date_to": "2025-01-03", "dates_count": 2}
        assert issue.affected_fx_pairs == ["EUR-RON"]
        assert IssueCode.MISSING_FX_MARKET not in [i.code for i in report.issues]

    def test_configured_manual_missing_fx_navigates_to_fx(self):
        views = _make_views()
        report = views.build_data_quality_report(
            missing_fx_pairs_dto=[_make_missing_fx("RON/EUR")],
            configured_fx_pairs={"EUR-RON"},
            real_provider_fx_pairs=set(),
        )
        issue = next(i for i in report.issues if i.code == IssueCode.MISSING_FX_RATES)
        assert issue.cta_action == "navigate_fx"
        assert issue.cta_target == "EUR-RON"
        assert issue.message_i18n_key == "dataQuality.missingFxRatesManual"

    def test_missing_fx_can_split_into_three_buckets(self):
        views = _make_views()
        report = views.build_data_quality_report(
            missing_fx_pairs_dto=[
                _make_missing_fx("USD/EUR", [date(2025, 1, 1)]),
                _make_missing_fx("RON/EUR", [date(2025, 1, 2)]),
                _make_missing_fx("NOK/EUR", [date(2025, 1, 3)]),
            ],
            configured_fx_pairs={"EUR-RON", "EUR-NOK"},
            real_provider_fx_pairs={"EUR-RON"},
        )
        market_issue = next(i for i in report.issues if i.group_key == "missing_fx")
        real_issue = next(i for i in report.issues if i.group_key == "missing_fx_rates")
        manual_issue = next(i for i in report.issues if i.group_key == "missing_fx_rates_manual")
        assert market_issue.affected_fx_pairs == ["EUR-USD"]
        assert real_issue.affected_fx_pairs == ["EUR-RON"]
        assert manual_issue.affected_fx_pairs == ["EUR-NOK"]


# =============================================================================
# MISSING_FX_RATES — the days of the ranges count too (D-P4)
# =============================================================================


def _rates_issues(report) -> list:
    """The MISSING_FX_RATES issues of the report that carry dates (the real-provider bucket), found by code and key."""
    return [i for i in report.issues if i.code == IssueCode.MISSING_FX_RATES and i.message_i18n_key == "dataQuality.missingFxRates"]


def _rates_params(pairs: list[WACMissingPairInfo], *slugs: str) -> dict:
    """``message_params`` of the single real-provider MISSING_FX_RATES issue for ``pairs``, all configured with a real provider."""
    report = build_data_quality_report([], missing_fx_pairs_dto=pairs, configured_fx_pairs=set(slugs), real_provider_fx_pairs=set(slugs))
    issues = _rates_issues(report)
    assert len(issues) == 1
    return issues[0].message_params


class TestMissingFxRatesCountsTheRanges:
    """MISSING_FX_RATES ``date_from`` / ``date_to`` / ``dates_count`` cover the UNION of the days of ``dates`` and of every
    day of ``ranges``.

    D-P4 moved the valuation days of a missing pair from ``dates`` (one entry per day) to ``ranges`` (consecutive days
    merged), keeping in ``dates`` the movements' dates only. The report once read ``dates`` alone: a pair missing a
    rate on a long valuation range showed the count and the bounds of its movements only, hiding most of the gap the
    user is asked to sync. Each case below gives numbers that differ from the ``dates``-only ones, so ignoring the
    ranges fails it.
    """

    def test_dates_and_a_range_are_added(self):
        d1, d3, d7 = date(2025, 1, 1), date(2025, 1, 3), date(2025, 1, 7)
        pair = WACMissingPairInfo(pair="RON/EUR", dates=[d1], ranges=[DateSpan(start=d3, end=d7)])
        params = _rates_params([pair], "EUR-RON")
        assert params["date_from"] == "2025-01-01"
        assert params["date_to"] == "2025-01-07"  # dates alone would stop at 2025-01-01
        assert params["dates_count"] == 6  # 1 movement date + 5 days of the range; dates alone: 1

    def test_a_date_inside_a_range_is_counted_once(self):
        d3, d4, d5 = date(2025, 1, 3), date(2025, 1, 4), date(2025, 1, 5)
        pair = WACMissingPairInfo(pair="RON/EUR", dates=[d4], ranges=[DateSpan(start=d3, end=d5)])
        params = _rates_params([pair], "EUR-RON")
        assert params["date_from"] == "2025-01-03"
        assert params["date_to"] == "2025-01-05"
        assert params["dates_count"] == 3  # not 4: the date is one of the range's days

    def test_ranges_alone_give_the_bounds_and_the_days(self):
        d2, d6 = date(2025, 1, 2), date(2025, 1, 6)
        pair = WACMissingPairInfo(pair="RON/EUR", dates=[], ranges=[DateSpan(start=d2, end=d6)])
        params = _rates_params([pair], "EUR-RON")
        assert params["date_from"] == "2025-01-02"  # dates alone: "" (no bound)
        assert params["date_to"] == "2025-01-06"
        assert params["dates_count"] == 5  # dates alone: 0

    def test_touching_ranges_of_two_pairs_merge_into_one_span(self):
        first = WACMissingPairInfo(pair="RON/EUR", dates=[], ranges=[DateSpan(start=date(2025, 1, 1), end=date(2025, 1, 2))])
        second = WACMissingPairInfo(pair="NOK/EUR", dates=[], ranges=[DateSpan(start=date(2025, 1, 3), end=date(2025, 1, 4))])
        params = _rates_params([first, second], "EUR-RON", "EUR-NOK")
        assert params["count"] == 2
        assert params["date_from"] == "2025-01-01"
        assert params["date_to"] == "2025-01-04"
        assert params["dates_count"] == 4  # 2 + 2 consecutive days, one merged span


# =============================================================================
# NAV_INCOMPLETE
# =============================================================================


class TestNavIncompleteIssue:
    def test_no_incomplete_days_produces_no_issue(self):
        states = [_complete_state("2025-01-01"), _complete_state("2025-01-02")]
        views = _make_views(states)
        report = views.build_data_quality_report()
        codes = [i.code for i in report.issues]
        assert IssueCode.NAV_INCOMPLETE not in codes

    def test_incomplete_days_produce_info_issue(self):
        states = [_incomplete_state("2025-01-01"), _complete_state("2025-01-02")]
        views = _make_views(states)
        report = views.build_data_quality_report()
        issue = next(i for i in report.issues if i.code == IssueCode.NAV_INCOMPLETE)
        assert issue.severity == IssueSeverity.INFO

    def test_nav_incomplete_includes_count(self):
        states = [_incomplete_state("2025-01-01"), _incomplete_state("2025-01-02"), _complete_state("2025-01-03")]
        views = _make_views(states)
        report = views.build_data_quality_report()
        issue = next(i for i in report.issues if i.code == IssueCode.NAV_INCOMPLETE)
        assert issue.count == 2

    def test_nav_incomplete_includes_date_range(self):
        states = [_incomplete_state("2025-01-01"), _incomplete_state("2025-01-05"), _complete_state("2025-01-10")]
        views = _make_views(states)
        report = views.build_data_quality_report()
        issue = next(i for i in report.issues if i.code == IssueCode.NAV_INCOMPLETE)
        assert issue.message_params["date_from"] == "2025-01-01"
        assert issue.message_params["date_to"] == "2025-01-05"

    def test_nav_incomplete_also_in_legacy_field(self):
        states = [_incomplete_state("2025-01-01")]
        views = _make_views(states)
        report = views.build_data_quality_report()
        assert any(span.start <= date(2025, 1, 1) <= span.end for span in report.incomplete_nav_ranges)

    def test_nav_incomplete_outside_period_is_not_reported(self):
        """A gap before the displayed window must not raise an issue.

        ``daily_states`` always starts at the first transaction, so a dashboard
        showing the last three months still carries years of older states. A gap
        out there changes nothing on screen: every period figure is re-based to
        the window, so reporting it asks the user to fix something invisible.
        """
        states = [_incomplete_state("2019-03-04"), _complete_state("2025-06-01"), _complete_state("2025-06-30")]
        views = _make_views(states)
        report = views.build_data_quality_report(period_from=date(2025, 6, 1), period_to=date(2025, 6, 30))
        assert not any(i.code == IssueCode.NAV_INCOMPLETE for i in report.issues)
        assert report.incomplete_nav_ranges == []

    def test_nav_incomplete_inside_period_is_reported(self):
        states = [_incomplete_state("2019-03-04"), _incomplete_state("2025-06-10"), _complete_state("2025-06-30")]
        views = _make_views(states)
        report = views.build_data_quality_report(period_from=date(2025, 6, 1), period_to=date(2025, 6, 30))
        issue = next(i for i in report.issues if i.code == IssueCode.NAV_INCOMPLETE)
        assert issue.count == 1
        assert issue.message_params["date_from"] == "2025-06-10"

    def test_nav_incomplete_on_the_opening_day_is_reported(self):
        """The state at ``period_from`` is the opening balance of the period.

        ``financial_math.portfolio.period.period_pnl`` reads it to derive period P&L, so an
        incomplete NAV there does move what the user is looking at.
        """
        states = [_incomplete_state("2025-06-01"), _complete_state("2025-06-30")]
        views = _make_views(states)
        report = views.build_data_quality_report(period_from=date(2025, 6, 1), period_to=date(2025, 6, 30))
        issue = next(i for i in report.issues if i.code == IssueCode.NAV_INCOMPLETE)
        assert issue.count == 1

    def test_nav_incomplete_without_period_scans_everything(self):
        """No bounds means no window: callers that want the whole history still get it."""
        states = [_incomplete_state("2019-03-04"), _incomplete_state("2025-06-10")]
        views = _make_views(states)
        report = views.build_data_quality_report()
        issue = next(i for i in report.issues if i.code == IssueCode.NAV_INCOMPLETE)
        assert issue.count == 2


# =============================================================================
# MWRR_NOT_CALCULABLE
# =============================================================================


class TestMwrrNotCalculableIssue:
    def test_mwrr_available_produces_no_issue(self):
        views = _make_views()
        report = views.build_data_quality_report(mwrr_available=True)
        codes = [i.code for i in report.issues]
        assert IssueCode.MWRR_NOT_CALCULABLE not in codes

    def test_mwrr_not_available_produces_info_issue(self):
        views = _make_views()
        report = views.build_data_quality_report(mwrr_available=False)
        issue = next(i for i in report.issues if i.code == IssueCode.MWRR_NOT_CALCULABLE)
        assert issue.severity == IssueSeverity.INFO

    def test_mwrr_not_available_has_no_cta(self):
        views = _make_views()
        report = views.build_data_quality_report(mwrr_available=False)
        issue = next(i for i in report.issues if i.code == IssueCode.MWRR_NOT_CALCULABLE)
        assert not issue.cta_action


# =============================================================================
# ISSUE ORDERING
# =============================================================================


class TestIssueOrdering:
    def test_empty_inputs_produce_no_issues(self):
        views = _make_views()
        report = views.build_data_quality_report()
        assert report.issues == []

    def test_all_five_codes_can_appear_together(self):
        states = [_incomplete_state("2025-01-01")]
        views = _make_views(states)
        report = views.build_data_quality_report(
            missing_price_assets_dto=[_make_missing_asset()],
            stale_prices_dto=[_make_stale_asset()],
            missing_fx_pairs_dto=[_make_missing_fx()],
            mwrr_available=False,
        )
        codes = {i.code for i in report.issues}
        assert IssueCode.MISSING_PRICE in codes
        assert IssueCode.STALE_PRICE in codes
        assert IssueCode.MISSING_FX_MARKET in codes
        assert IssueCode.NAV_INCOMPLETE in codes
        assert IssueCode.MWRR_NOT_CALCULABLE in codes
        assert len(report.issues) == 5


# =============================================================================
# TRANSACTION_IMPLIED (issue generation)
# =============================================================================


class TestTransactionImpliedIssue:
    def test_no_implied_assets_produces_no_issue(self):
        views = _make_views()
        report = views.build_data_quality_report()
        codes = [i.code for i in report.issues]
        assert IssueCode.TRANSACTION_IMPLIED not in codes

    def test_implied_assets_produce_warning_issue(self):
        views = _make_views()
        asset = _make_missing_asset(1, "BTP Più")
        report = views.build_data_quality_report(transaction_implied_assets_dto=[asset])
        issue = next(i for i in report.issues if i.code == IssueCode.TRANSACTION_IMPLIED)
        assert issue.severity == IssueSeverity.WARNING

    def test_implied_assets_include_names(self):
        views = _make_views()
        asset = _make_missing_asset(42, "BTP SC 2033")
        report = views.build_data_quality_report(transaction_implied_assets_dto=[asset])
        issue = next(i for i in report.issues if i.code == IssueCode.TRANSACTION_IMPLIED)
        assert "BTP SC 2033" in issue.affected_asset_names
        assert 42 in issue.affected_asset_ids
        assert issue.count == 1

    def test_implied_has_navigate_asset_cta(self):
        views = _make_views()
        report = views.build_data_quality_report(transaction_implied_assets_dto=[_make_missing_asset()])
        issue = next(i for i in report.issues if i.code == IssueCode.TRANSACTION_IMPLIED)
        assert issue.cta_action == "navigate_asset"

    def test_all_six_codes_can_appear_together(self):
        """With TRANSACTION_IMPLIED added, all 6 codes can appear simultaneously."""
        states = [_incomplete_state("2025-01-01")]
        views = _make_views(states)
        report = views.build_data_quality_report(
            missing_price_assets_dto=[_make_missing_asset()],
            transaction_implied_assets_dto=[_make_missing_asset(3, "BTP")],
            stale_prices_dto=[_make_stale_asset()],
            missing_fx_pairs_dto=[_make_missing_fx()],
            mwrr_available=False,
        )
        codes = {i.code for i in report.issues}
        assert IssueCode.MISSING_PRICE in codes
        assert IssueCode.TRANSACTION_IMPLIED in codes
        assert IssueCode.STALE_PRICE in codes
        assert IssueCode.MISSING_FX_MARKET in codes
        assert IssueCode.NAV_INCOMPLETE in codes
        assert IssueCode.MWRR_NOT_CALCULABLE in codes
        assert len(report.issues) == 6


# =============================================================================
# VALUED_AT_COST (J-17) — the code; its issue is pinned through PortfolioService.get_summary
# =============================================================================


class TestValuedAtCostIssueCode:
    def test_valued_at_cost_is_a_portfolio_issue_code(self):
        """J-17: holdings valued at their book cost on the report's last day (no price observation at all)
        are listed under their own warning, ``VALUED_AT_COST``. Its shape, grace and manual-asset rule are
        pinned end to end in ``test_portfolio_service.py::TestValuedAtCostDataQuality``.

        Before J-17: AttributeError — IssueCode had no VALUED_AT_COST.
        """
        assert IssueCode.VALUED_AT_COST == "VALUED_AT_COST"
        assert IssueCode("VALUED_AT_COST") is IssueCode.VALUED_AT_COST


class TestValuedAtCostIssue:
    """J-17: ``build_data_quality_report(valued_at_cost_assets_dto=...)`` turns the assets the caller lists
    (with a provider, past the grace: ``PortfolioService.get_summary`` decides who) into one warning, shaped
    like TRANSACTION_IMPLIED: key ``dataQuality.valuedAtCost``, params ``count`` and ``as_of_date`` (the
    report's last day), the assets by id and name, a ``navigate_asset`` CTA to the first one, group
    ``valued_at_cost``. It is its own issue: listing assets at cost adds neither TRANSACTION_IMPLIED nor
    MISSING_PRICE.
    """

    def test_no_valued_at_cost_assets_produce_no_issue(self):
        """Guard: nothing listed, no issue (green before and after J-17: today nothing produces the code)."""
        report = _make_views([_complete_state("2025-06-30")]).build_data_quality_report()
        assert "VALUED_AT_COST" not in {i.code for i in report.issues}

    def test_valued_at_cost_assets_produce_one_warning_with_their_shape(self):
        """Before J-17: TypeError — build_data_quality_report had no ``valued_at_cost_assets_dto``."""
        states = [_complete_state("2025-06-29"), _complete_state("2025-06-30")]
        assets = [_make_missing_asset(7, "Unquoted fund"), _make_missing_asset(9, "Private note")]

        report = _make_views(states).build_data_quality_report(valued_at_cost_assets_dto=assets)

        matching = [i for i in report.issues if i.code == "VALUED_AT_COST"]
        assert len(matching) == 1, [i.code for i in report.issues]
        issue = matching[0]
        assert {
            "code": issue.code,
            "domain": issue.domain,
            "severity": issue.severity,
            "message_i18n_key": issue.message_i18n_key,
            "message_params": issue.message_params,
            "count": issue.count,
            "affected_asset_ids": issue.affected_asset_ids,
            "affected_asset_names": issue.affected_asset_names,
            "cta_action": issue.cta_action,
            "cta_target": issue.cta_target,
            "group_key": issue.group_key,
        } == {
            "code": IssueCode.VALUED_AT_COST,
            "domain": IssueDomain.PORTFOLIO,
            "severity": IssueSeverity.WARNING,
            "message_i18n_key": "dataQuality.valuedAtCost",
            "message_params": {"count": 2, "as_of_date": "2025-06-30"},
            "count": 2,
            "affected_asset_ids": [7, 9],
            "affected_asset_names": ["Unquoted fund", "Private note"],
            "cta_action": "navigate_asset",
            "cta_target": "7",
            "group_key": "valued_at_cost",
        }
        codes = {i.code for i in report.issues}
        assert IssueCode.TRANSACTION_IMPLIED not in codes
        assert IssueCode.MISSING_PRICE not in codes


# =============================================================================
# TRANSFER_SHARE_MISMATCH (J-43b)
# =============================================================================


def _share_mismatch(tx_ids: tuple[int, int], dt: str, *, broker_ids: tuple[int, int] = (10, 20), shares: tuple[str, str] = ("1", "0.5")):
    """A ``ShareMismatch`` (J-43): a linked internal pair between brokers owned at different shares, read from
    ``models`` when the test runs."""
    return portfolio_models.ShareMismatch(tx_ids=tx_ids, broker_ids=broker_ids, shares=(Decimal(shares[0]), Decimal(shares[1])), date=date.fromisoformat(dt))


def _share_mismatch_issues(report) -> list:
    """The report's TRANSFER_SHARE_MISMATCH issues, matched on the code's value (HEAD has no enum member to name)."""
    return [i for i in report.issues if i.code == "TRANSFER_SHARE_MISMATCH"]


def _numbers_in(text: str) -> set[int]:
    """Every integer written in ``text``, whole: 7101 is not found in 71012."""
    return {int(number) for number in re.findall(r"\d+", text)}


def _strings_naming(report, tx_ids: tuple[int, int]) -> list[str]:
    """The ``share_mismatch_warnings`` strings that name both transactions of a pair."""
    return [text for text in report.share_mismatch_warnings if set(tx_ids) <= _numbers_in(text)]


class TestTransferShareMismatchIssue:
    """J-43b: ``build_data_quality_report(share_mismatches=...)`` turns the linked internal pairs between brokers owned
    at different shares (``ShareMismatch``, from the engine's classification) into the user's explanation of the P&L
    their gap makes (D-MF4 = a): one string per pair in ``share_mismatch_warnings``, naming both transactions (the rest
    of its text is not pinned), and one INFO issue ``TRANSFER_SHARE_MISMATCH`` counting them — key
    ``dataQuality.transferShareMismatch``, params ``{count}``, group ``transfer_share_mismatch``, no CTA, no asset, no
    pair. Only the pairs dated on or before ``period_to`` count (every pair without one); none counted, no issue. An INFO
    issue: the status does not move.

    On HEAD 252835dce ``models`` has no ``ShareMismatch`` (AttributeError, raised while the arguments are built),
    ``build_data_quality_report`` takes no ``share_mismatches`` (TypeError, once ``ShareMismatch`` exists) and
    ``IssueCode`` has no ``TRANSFER_SHARE_MISMATCH`` (ValueError): every test that passes mismatches is red for that
    alone, the guards of the bound and of the status included.
    """

    def test_transfer_share_mismatch_is_a_portfolio_issue_code(self):
        """Red (J-43b). HEAD: ValueError — IssueCode has no TRANSFER_SHARE_MISMATCH."""
        assert IssueCode("TRANSFER_SHARE_MISMATCH") == "TRANSFER_SHARE_MISMATCH"

    def test_no_share_mismatches_produce_no_issue(self):
        """Guard (green on HEAD and after J-43): nothing passed, no issue and no string."""
        report = _make_views([_complete_state("2025-06-30")]).build_data_quality_report(period_to=date(2025, 6, 30))
        assert _share_mismatch_issues(report) == []
        assert report.share_mismatch_warnings == []

    @pytest.mark.parametrize("share_mismatches", [None, []], ids=["none", "empty"])
    def test_an_empty_share_mismatch_list_produces_no_issue(self, share_mismatches):
        """Red (J-43b) on HEAD only by construction: TypeError, no ``share_mismatches``. After J-43 it guards that
        nothing to report gives no issue at all, not one counting 0."""
        report = _make_views([_complete_state("2025-06-30")]).build_data_quality_report(share_mismatches=share_mismatches, period_to=date(2025, 6, 30))
        assert _share_mismatch_issues(report) == []
        assert report.share_mismatch_warnings == []

    def test_one_share_mismatch_produces_one_info_issue_with_its_shape(self):
        """Red (J-43b). One pair (7101, 7102), brokers 10 at 1 and 20 at 0.5, dated 2025-06-10 inside the window
        2025-06-01..2025-06-30: one INFO issue with the contract's shape, and one string naming both transactions.

        HEAD: AttributeError — ``models`` has no ShareMismatch (then TypeError: build_data_quality_report has no
        ``share_mismatches``)."""
        states = [_complete_state("2025-06-01"), _complete_state("2025-06-30")]

        report = _make_views(states).build_data_quality_report(share_mismatches=[_share_mismatch((7101, 7102), "2025-06-10")], period_from=date(2025, 6, 1), period_to=date(2025, 6, 30))

        matching = _share_mismatch_issues(report)
        assert len(matching) == 1, [i.code for i in report.issues]
        issue = matching[0]
        assert {
            "code": issue.code,
            "domain": issue.domain,
            "severity": issue.severity,
            "message_i18n_key": issue.message_i18n_key,
            "message_params": issue.message_params,
            "count": issue.count,
            "affected_asset_ids": issue.affected_asset_ids,
            "affected_asset_names": issue.affected_asset_names,
            "affected_fx_pairs": issue.affected_fx_pairs,
            "cta_action": issue.cta_action,
            "group_key": issue.group_key,
        } == {
            "code": IssueCode("TRANSFER_SHARE_MISMATCH"),
            "domain": IssueDomain.PORTFOLIO,
            "severity": IssueSeverity.INFO,
            "message_i18n_key": "dataQuality.transferShareMismatch",
            "message_params": {"count": 1},
            "count": 1,
            "affected_asset_ids": [],
            "affected_asset_names": [],
            "affected_fx_pairs": [],
            "cta_action": None,
            "group_key": "transfer_share_mismatch",
        }
        assert len(report.share_mismatch_warnings) == 1, report.share_mismatch_warnings
        assert {7101, 7102} <= _numbers_in(report.share_mismatch_warnings[0]), report.share_mismatch_warnings

    def test_each_share_mismatch_is_counted_and_named(self):
        """Red (J-43b). Two pairs: (7201, 7202) on 2025-06-05, 10 -> 20, and (7203, 7204) on 2025-06-20 the other way,
        20 -> 10. One issue counting 2, two strings, each naming both transactions of its own pair.

        HEAD: AttributeError (no ShareMismatch), then TypeError (no ``share_mismatches``)."""
        mismatches = [_share_mismatch((7201, 7202), "2025-06-05"), _share_mismatch((7203, 7204), "2025-06-20", broker_ids=(20, 10), shares=("0.5", "1"))]

        report = _make_views([_complete_state("2025-06-30")]).build_data_quality_report(share_mismatches=mismatches, period_to=date(2025, 6, 30))

        assert [(i.count, i.message_params) for i in _share_mismatch_issues(report)] == [(2, {"count": 2})], [i.code for i in report.issues]
        assert len(report.share_mismatch_warnings) == 2, report.share_mismatch_warnings
        assert [len(_strings_naming(report, ids)) for ids in ((7201, 7202), (7203, 7204))] == [1, 1], report.share_mismatch_warnings

    def test_only_the_pairs_up_to_period_to_count(self):
        """Red (J-43b). Window 2025-06-01..2025-06-30. The bound is ``period_to`` alone: a pair from before the window
        (2025-03-10) still counts — its gap stays in the cumulative P&L —, one dated on ``period_to`` counts, one dated
        the day after does not. One issue counting 2; the strings name the first two pairs and never the third.

        HEAD: AttributeError (no ShareMismatch), then TypeError (no ``share_mismatches``)."""
        mismatches = [_share_mismatch((7301, 7302), "2025-03-10"), _share_mismatch((7303, 7304), "2025-06-30"), _share_mismatch((7305, 7306), "2025-07-01")]
        states = [_complete_state("2025-06-01"), _complete_state("2025-06-30")]

        report = _make_views(states).build_data_quality_report(share_mismatches=mismatches, period_from=date(2025, 6, 1), period_to=date(2025, 6, 30))

        assert [i.count for i in _share_mismatch_issues(report)] == [2], [i.code for i in report.issues]
        assert len(report.share_mismatch_warnings) == 2, report.share_mismatch_warnings
        assert [len(_strings_naming(report, ids)) for ids in ((7301, 7302), (7303, 7304))] == [1, 1], report.share_mismatch_warnings
        assert [text for text in report.share_mismatch_warnings if _numbers_in(text) & {7305, 7306}] == [], report.share_mismatch_warnings

    def test_a_pair_after_period_to_is_not_reported(self):
        """Red (J-43b) on HEAD only by construction (AttributeError: no ShareMismatch; then TypeError: no
        ``share_mismatches``); after J-43 it guards the bound. Barrier first: without ``period_to`` the pair (7401, 7402)
        of 2025-07-15 is reported. With the window ending 2025-06-30 nothing is counted: no issue at all, not one
        counting 0, and no string."""
        mismatch = _share_mismatch((7401, 7402), "2025-07-15")
        views = _make_views([_complete_state("2025-06-30")])

        unbounded = views.build_data_quality_report(share_mismatches=[mismatch])
        assert [i.count for i in _share_mismatch_issues(unbounded)] == [1], [i.code for i in unbounded.issues]

        bounded = views.build_data_quality_report(share_mismatches=[mismatch], period_to=date(2025, 6, 30))
        assert _share_mismatch_issues(bounded) == []
        assert bounded.share_mismatch_warnings == []

    def test_share_mismatches_alone_keep_the_status_ok(self):
        """Red (J-43b) on HEAD only by construction (AttributeError: no ShareMismatch; then TypeError: no
        ``share_mismatches``); after J-43 it guards the status. Barrier first: the pair is counted. Then a report with
        nothing else is still ``ok``: an INFO issue and its strings degrade nothing."""
        report = _make_views([_complete_state("2025-06-30")]).build_data_quality_report(share_mismatches=[_share_mismatch((7501, 7502), "2025-06-10")], period_to=date(2025, 6, 30))

        assert [i.count for i in _share_mismatch_issues(report)] == [1], [i.code for i in report.issues]
        assert report.data_quality_status == DataQualityStatus.OK


# =============================================================================
# NO TRANSACTIONS_BEFORE_FLOOR (MF-PAV-L1)
# =============================================================================


class TestNoTransactionsBeforeFloorIssue:
    """MF-PAV-L1: the engine's history starts on the first transaction, even before 1900, so the report has nothing to warn
    about: ``RowsBeforeFloor``, ``build_data_quality_report(rows_before_floor=…)`` and the WARNING ``TRANSACTIONS_BEFORE_FLOOR``
    (MF-SEC8-2a, never released) are gone."""

    def test_the_builder_takes_no_rows_before_floor(self):
        """RED on HEAD 999f1899e: ``build_data_quality_report`` still has a ``rows_before_floor`` parameter. Read on the
        function's signature and, because ``DerivedViewsBuilder.build_data_quality_report`` forwards ``**kwargs``, on a call
        through it: an unknown keyword is a ``TypeError``."""
        assert "rows_before_floor" not in inspect.signature(build_data_quality_report).parameters, "build_data_quality_report still takes rows_before_floor: the report counts no row before 1900"
        with pytest.raises(TypeError, match="rows_before_floor"):
            _make_views([_complete_state("2025-06-30")]).build_data_quality_report(rows_before_floor=None)

    def test_no_issue_code_names_the_floor(self):
        """RED on HEAD: ``IssueCode`` still has ``TRANSACTIONS_BEFORE_FLOOR``."""
        assert "TRANSACTIONS_BEFORE_FLOOR" not in IssueCode.__members__, "IssueCode has no TRANSACTIONS_BEFORE_FLOOR: the report emits no such issue"

    def test_guard_a_complete_day_has_no_issue(self):
        """GUARD (green on HEAD too): a report of one complete day, with nothing to report, holds no issue at all."""
        assert _make_views([_complete_state("2025-06-30")]).build_data_quality_report().issues == []


# =============================================================================
# NON_ISO_CURRENCY (E-19b2) — a currency stored as no ISO 4217 code is named, never asked for as an FX pair
# =============================================================================

NON_ISO_CURRENCY = "NON_ISO_CURRENCY"
NON_ISO_SUGGESTION = "dataQuality.nonIsoCurrencySuggestion"
NON_ISO_CANDIDATES = "dataQuality.nonIsoCurrencyCandidates"
NON_ISO_UNKNOWN = "dataQuality.nonIsoCurrencyUnknown"
NON_ISO_REPORT = "dataQuality.nonIsoReportCurrency"
NON_ISO_REPORT_UNKNOWN = "dataQuality.nonIsoReportCurrencyUnknown"
NON_ISO_KEYS = (NON_ISO_SUGGESTION, NON_ISO_CANDIDATES, NON_ISO_UNKNOWN, NON_ISO_REPORT, NON_ISO_REPORT_UNKNOWN)
MISSING_FX_CODES = (IssueCode.MISSING_FX_MARKET, IssueCode.MISSING_FX_RATES)
#: The currency the reports below convert to, unless a test says otherwise.
REPORT_CURRENCY = "EUR"


def _fx(pair: str, *days: str) -> WACMissingPairInfo:
    """A conversion the engine could not make, as it reports one: ``FROM/TO`` with both codes as stored, and its dates
    (2025-01-01 when none is given)."""
    return WACMissingPairInfo(pair=pair, dates=[date.fromisoformat(day) for day in days] or [date(2025, 1, 1)])


def _non_iso_report(pairs: list[WACMissingPairInfo] | None = None, *, assets: list[tuple[int, str, str]] | None = None, report_currency: str | None = REPORT_CURRENCY, views: DerivedViewsBuilder | None = None, **other):
    """The report of one complete day (or of ``views``) given the missing conversions, ``non_iso_currency_assets`` and
    ``report_currency``: a TypeError (no such parameter) fails the test."""
    views = views or _make_views([_complete_state("2025-06-30")])
    try:
        return views.build_data_quality_report(missing_fx_pairs_dto=pairs, non_iso_currency_assets=assets, report_currency=report_currency, **other)
    except TypeError as exc:
        pytest.fail(f"red until E-19b2: build_data_quality_report(…, non_iso_currency_assets=…, report_currency=…) raised {exc!r}: it takes the held assets whose currency is no ISO 4217 code, and the currency the report converts to")


def _lots_report(pairs: list[WACMissingPairInfo]):
    """The gap report as ``LotsAnalysisService`` builds it: no daily state, the missing pairs, the two pair sets (empty
    here) — and neither ``non_iso_currency_assets`` nor ``report_currency``."""
    return build_data_quality_report([], missing_fx_pairs_dto=pairs, configured_fx_pairs=set(), real_provider_fx_pairs=set())


def _non_iso_issues(report) -> list:
    """The report's NON_ISO_CURRENCY issues, in its order, matched on the code's value (HEAD has no enum member to name)."""
    return [i for i in report.issues if i.code == NON_ISO_CURRENCY]


def _shape(issue) -> dict:
    """Every field of an issue but its code."""
    fields = ("domain", "severity", "message_i18n_key", "message_params", "count", "affected_asset_ids", "affected_asset_names", "affected_fx_pairs", "cta_action", "cta_target", "group_key")
    return {field: getattr(issue, field) for field in fields}


def _non_iso(value: str, key: str, params: dict, assets: tuple[tuple[int, str], ...] = ()) -> dict:
    """The contract's issue for ``value``: a portfolio WARNING with ``key`` and ``params``, the listed assets stored in that
    value by id and name in the order given (``count`` their number, None without one), no FX pair, no CTA, and the whole
    value in the group key."""
    return {
        "domain": IssueDomain.PORTFOLIO,
        "severity": IssueSeverity.WARNING,
        "message_i18n_key": key,
        "message_params": params,
        "count": len(assets) or None,
        "affected_asset_ids": [asset_id for asset_id, _ in assets],
        "affected_asset_names": [name for _, name in assets],
        "affected_fx_pairs": [],
        "cta_action": None,
        "cta_target": None,
        "group_key": f"non_iso_currency:{value}",
    }


def _fx_groups(report) -> dict[str, list[str]]:
    """The report's MISSING_FX_* issues by group key, each with the slugs it lists."""
    return {i.group_key: i.affected_fx_pairs for i in report.issues if i.code in MISSING_FX_CODES}


def _named_pairs(report) -> list[tuple[str, str]]:
    """(code, slug) of every pair an issue of the report names: in its list of pairs, or as its CTA's target."""
    listed = [(str(i.code), slug) for i in report.issues for slug in i.affected_fx_pairs]
    targeted = [(str(i.code), i.cta_target) for i in report.issues if i.code in MISSING_FX_CODES and i.cta_target]
    return listed + targeted


def _held(asset_id: int, name: str, currency: str) -> HeldAssetQuoteFacts:
    """A held asset as ``PortfolioService._held_asset_quote_facts`` reads it: its id, its name, its currency as stored."""
    return HeldAssetQuoteFacts(asset_id=asset_id, name=name, currency=currency)


class TestNonIsoCurrencyIssue:
    """E-19b2: since E-18 a write takes only ISO 4217 alphabetic codes, but an older version stored a currency as written
    (``978``, ``EURO``, ``eur``, ``Bolívar Soberano``). Such a code breaks every conversion, and each one missing is
    reported as ``FROM/TO`` with the codes as stored: the report turned ``978/EUR`` into a MISSING_FX_MARKET ``978-EUR``
    (whose «Add FX pair» gets a 422) and a stored ``eur`` into the nonsense ``EUR-EUR`` (the slug upper-cases).

    ``build_data_quality_report(non_iso_currency_assets=[(asset_id, name, currency), …], report_currency=…)`` collects
    every value ``is_canonical_iso_currency`` refuses: each such side of a missing pair (its TO side is ``report_currency``
    when the pair ends with ``"/" + report_currency``, else the pair splits at its last ``/``: a value holding a ``/``
    stays whole), the currency of each listed asset, and ``report_currency`` itself. One WARNING ``NON_ISO_CURRENCY`` per
    value, sorted by value, right after INVALID_SPLIT_RATIO and before every MISSING_FX_* issue: domain ``portfolio``, no
    CTA, no pair, group ``non_iso_currency:<value>`` (the whole value: the banner keys its rows on code and group), the
    listed assets stored in that value by id and name (``count`` their number, None without one), and the value as
    ``shown_currency_text`` quotes it (16 characters, then ``…``) in ``message_params["value"]``. The key: for the report
    currency ``dataQuality.nonIsoReportCurrency`` with ``suggestion`` when ``suggested_iso_currency`` names one, else
    ``dataQuality.nonIsoReportCurrencyUnknown``; for any other value ``dataQuality.nonIsoCurrencySuggestion`` with
    ``suggestion``, else ``dataQuality.nonIsoCurrencyCandidates`` with ``candidates`` («VED, VES») when
    ``iso_currency_candidates`` gives two or more, else ``dataQuality.nonIsoCurrencyUnknown``. A minor unit
    ``minor_unit_factor`` recognises (``GBp``) gets neither suggestion nor candidates: GBP would read pence as pounds.
    MISSING_FX_MARKET and MISSING_FX_RATES (all three groups) keep only the pairs whose two sides are canonical; the raw
    ``missing_fx_pairs`` keeps every pair. A caller passing neither parameter (the lots gap report) still gets the pair
    sides, with the generic keys, and the filtering.

    On HEAD 2fbbf4c4c ``IssueCode`` has no ``NON_ISO_CURRENCY`` and the builder takes neither parameter: each test passing
    one fails on its TypeError alone, the lots form on its assertions; the guards are green.
    """

    def test_non_iso_currency_is_a_portfolio_issue_code_right_after_invalid_split_ratio(self):
        """Red until E-19b2: IssueCode has no NON_ISO_CURRENCY (the frontend keys on the string). It is declared right
        after INVALID_SPLIT_RATIO, as its issues are placed. Red on HEAD 065c9df77 too: the pence warning's code still
        sits between the two (Z-32cr removes it)."""
        members = [member.value for member in IssueCode]

        assert NON_ISO_CURRENCY in members, "red until E-19b2: schemas.portfolio.IssueCode has no NON_ISO_CURRENCY"
        assert members[members.index(IssueCode.INVALID_SPLIT_RATIO) + 1] == NON_ISO_CURRENCY, members

    def test_a_numeric_code_alone_gives_one_warning_and_no_fx_issue(self):
        """Red until E-19b2 (TypeError). ``978/EUR`` into EUR, no pair configured: the code is named — one WARNING with the
        contract's shape: the suggestion EUR, no asset (count None), no pair, no CTA — and no MISSING_FX_* issue asks for
        a pair that cannot exist."""
        report = _non_iso_report([_fx("978/EUR")])

        assert [i.code for i in report.issues] == [NON_ISO_CURRENCY], _named_pairs(report)
        assert _named_pairs(report) == []
        assert [_shape(i) for i in _non_iso_issues(report)] == [_non_iso("978", NON_ISO_SUGGESTION, {"value": "978", "suggestion": "EUR"})]

    @pytest.mark.parametrize(
        ("configured", "real_provider", "group_key", "params", "cta_target"),
        [
            pytest.param(set(), set(), "missing_fx", {"count": 1}, None, id="not-configured"),
            pytest.param({"978-EUR", "EUR-USD"}, {"978-EUR", "EUR-USD"}, "missing_fx_rates", {"count": 1, "date_from": "2025-02-10", "date_to": "2025-02-10", "dates_count": 1}, "EUR-USD", id="configured-real-provider"),
            pytest.param({"978-EUR", "EUR-USD"}, set(), "missing_fx_rates_manual", {"count": 1}, "EUR-USD", id="configured-manual"),
        ],
    )
    def test_each_fx_group_keeps_only_the_canonical_pairs(self, configured, real_provider, group_key, params, cta_target):
        """Red until E-19b2 (TypeError). ``978/EUR`` (missing on 2025-01-01 and 2025-03-31) beside ``USD/EUR`` (on
        2025-02-10), both configured the same way: the group lists ``EUR-USD`` alone and counts 1, its dates are USD's
        only, its CTA targets ``EUR-USD``; no other MISSING_FX_* group; 978 is named once, as NON_ISO_CURRENCY."""
        pairs = [_fx("978/EUR", "2025-01-01", "2025-03-31"), _fx("USD/EUR", "2025-02-10")]

        report = _non_iso_report(pairs, configured_fx_pairs=configured, real_provider_fx_pairs=real_provider)

        assert _fx_groups(report) == {group_key: ["EUR-USD"]}, _named_pairs(report)
        assert [(i.count, i.message_params, i.cta_target) for i in report.issues if i.group_key == group_key] == [(1, params, cta_target)]
        assert [i.group_key for i in _non_iso_issues(report)] == ["non_iso_currency:978"]

    @pytest.mark.parametrize("configured", [pytest.param(set(), id="not-configured"), pytest.param({"EUR-EUR"}, id="configured-as-the-slug-reads-it")])
    def test_a_lower_case_code_is_named_and_never_paired_with_itself(self, configured):
        """Red until E-19b2 (TypeError). A stored ``eur`` into EUR: ``eur`` is named with the suggestion EUR, and no issue
        names ``EUR-EUR`` (nor any pair) — not configured, nor configured as the upper-casing slug would read it."""
        report = _non_iso_report([_fx("eur/EUR")], configured_fx_pairs=configured, real_provider_fx_pairs=configured)

        assert _named_pairs(report) == []
        assert [_shape(i) for i in _non_iso_issues(report)] == [_non_iso("eur", NON_ISO_SUGGESTION, {"value": "eur", "suggestion": "EUR"})]

    @pytest.mark.parametrize(
        ("value", "key", "extra"),
        [
            pytest.param("978", NON_ISO_SUGGESTION, {"suggestion": "EUR"}, id="numeric-code"),
            pytest.param("EURO", NON_ISO_SUGGESTION, {"suggestion": "EUR"}, id="name"),
            pytest.param("Bolívar Soberano", NON_ISO_CANDIDATES, {"candidates": "VED, VES"}, id="name-of-two-currencies"),
            pytest.param("BTC", NON_ISO_UNKNOWN, {}, id="no-iso-code"),
        ],
    )
    def test_the_key_follows_what_the_value_stands_for(self, value, key, extra):
        """Red until E-19b2 (TypeError). ``<value>/EUR``: a value standing for one code (978, EURO) gives the suggestion
        EUR; the name ISO 4217 gives two currencies gives both as ``candidates``, «VED, VES»; a value standing for no code
        (BTC) gives the unknown key, with the value alone. No MISSING_FX_* issue in any case."""
        report = _non_iso_report([_fx(f"{value}/EUR")])

        assert _fx_groups(report) == {}, _named_pairs(report)
        assert [_shape(i) for i in _non_iso_issues(report)] == [_non_iso(value, key, {"value": value} | extra)]

    @pytest.mark.parametrize("value", [pytest.param("GBp", id="GBp"), pytest.param(" GBp ", id="padded-GBp")])
    def test_a_minor_unit_gets_neither_suggestion_nor_candidates(self, value):
        """Red until E-19b2 (TypeError). ``GBp`` is pence: ``suggested_iso_currency`` gives GBP (the barrier), and
        relabelling would read pence as pounds, 100 times too much. What ``minor_unit_factor`` recognises — padded too, it
        strips — gets the unknown key, with the value alone."""
        assert (suggested_iso_currency(value), minor_unit_factor(value)) == ("GBP", 100), "barrier: the helper suggests GBP, and the value is a known minor unit"

        report = _non_iso_report([_fx(f"{value}/EUR")])

        assert _fx_groups(report) == {}, _named_pairs(report)
        assert [_shape(i) for i in _non_iso_issues(report)] == [_non_iso(value, NON_ISO_UNKNOWN, {"value": value})]

    def test_one_issue_per_value_sorted_by_value(self):
        """Red until E-19b2 (TypeError). ``eur/EUR``, ``BTC/EUR``, ``978/EUR`` and ``978/USD`` (a pair into another
        currency splits at its last ``/``): three values, three issues sorted by value — 978, BTC, eur —, each with its
        own group key; 978 is named once although two pairs carry it."""
        report = _non_iso_report([_fx("eur/EUR"), _fx("BTC/EUR"), _fx("978/EUR"), _fx("978/USD")])

        assert [(i.group_key, i.message_params.get("value")) for i in _non_iso_issues(report)] == [("non_iso_currency:978", "978"), ("non_iso_currency:BTC", "BTC"), ("non_iso_currency:eur", "eur")]
        assert _fx_groups(report) == {}, _named_pairs(report)

    def test_a_value_in_a_pair_and_on_a_listed_asset_is_one_issue_carrying_the_asset(self):
        """Red until E-19b2 (TypeError). ``978/EUR`` and the held asset 7 stored in 978: one issue, carrying the asset."""
        report = _non_iso_report([_fx("978/EUR")], assets=[(7, "Old ledger fund", "978")])

        assert [_shape(i) for i in _non_iso_issues(report)] == [_non_iso("978", NON_ISO_SUGGESTION, {"value": "978", "suggestion": "EUR"}, ((7, "Old ledger fund"),))]

    def test_listed_assets_alone_give_their_issues(self):
        """Red until E-19b2 (TypeError). No missing pair; three held assets — 9 in EURO, then 4 and 12 in 978: two issues,
        978 first, each with its assets in the order given and their number."""
        report = _non_iso_report(None, assets=[(9, "Fund B", "EURO"), (4, "Fund A", "978"), (12, "Fund C", "978")])

        assert [_shape(i) for i in _non_iso_issues(report)] == [
            _non_iso("978", NON_ISO_SUGGESTION, {"value": "978", "suggestion": "EUR"}, ((4, "Fund A"), (12, "Fund C"))),
            _non_iso("EURO", NON_ISO_SUGGESTION, {"value": "EURO", "suggestion": "EUR"}, ((9, "Fund B"),)),
        ]
        assert _fx_groups(report) == {}

    @pytest.mark.parametrize(
        ("report_currency", "pairs", "key", "params"),
        [
            pytest.param("978", ["USD/978"], NON_ISO_REPORT, {"value": "978", "suggestion": "EUR"}, id="numeric-code"),
            pytest.param("978", [], NON_ISO_REPORT, {"value": "978", "suggestion": "EUR"}, id="numeric-code-no-missing-pair"),
            pytest.param("Bolívar Soberano", ["USD/Bolívar Soberano"], NON_ISO_REPORT_UNKNOWN, {"value": "Bolívar Soberano"}, id="name-of-two-currencies"),
            pytest.param("GBp", ["USD/GBp"], NON_ISO_REPORT_UNKNOWN, {"value": "GBp"}, id="minor-unit"),
            pytest.param("Unidad de Fomento", ["USD/Unidad de Fomento"], NON_ISO_REPORT, {"value": "Unidad de Foment…", "suggestion": "CLF"}, id="long-name"),
        ],
    )
    def test_a_non_iso_report_currency_gets_the_report_keys(self, report_currency, pairs, key, params):
        """Red until E-19b2 (TypeError). The report converts to a currency stored as no ISO code (a base currency an older
        version kept): every conversion into it fails, and that is what to say. One issue, with the report's key — the
        suggestion when ``suggested_iso_currency`` names one, else the unknown key (two candidates, a minor unit) —, even
        without a missing pair; nothing for USD, no MISSING_FX_* issue. A long value is quoted cut, keyed whole."""
        report = _non_iso_report([_fx(pair) for pair in pairs] or None, report_currency=report_currency)

        assert [_shape(i) for i in _non_iso_issues(report)] == [_non_iso(report_currency, key, params)]
        assert _fx_groups(report) == {}, _named_pairs(report)

    def test_a_listed_asset_stored_in_the_report_currency_rides_on_its_issue(self):
        """Red until E-19b2 (TypeError). Report currency 978, and the held asset 7 stored in 978 too: one issue, the
        report's key, carrying the asset (count 1)."""
        report = _non_iso_report([_fx("USD/978")], assets=[(7, "Old ledger fund", "978")], report_currency="978")

        assert [_shape(i) for i in _non_iso_issues(report)] == [_non_iso("978", NON_ISO_REPORT, {"value": "978", "suggestion": "EUR"}, ((7, "Old ledger fund"),))]

    def test_a_report_currency_holding_a_slash_is_one_value(self):
        """Red until E-19b2 (TypeError). Report currency ``X/Y``, pair ``USD/X/Y``: the pair ends with ``/X/Y``, so its TO
        side is ``X/Y`` whole — one issue, the report's unknown key — and USD is canonical: nothing for ``USD/X`` nor ``Y``."""
        report = _non_iso_report([_fx("USD/X/Y")], report_currency="X/Y")

        assert [_shape(i) for i in _non_iso_issues(report)] == [_non_iso("X/Y", NON_ISO_REPORT_UNKNOWN, {"value": "X/Y"})]
        assert _fx_groups(report) == {}, _named_pairs(report)

    @pytest.mark.parametrize("form", ["with-report-currency", "lots-form"])
    def test_a_from_value_holding_a_slash_is_one_value(self, form):
        """Red until E-19b2 (TypeError with a report currency; the lots form on its assertions). ``A/B/EUR``: into EUR its TO
        side is EUR, and without a report currency the pair splits at its last ``/``: either way the value is ``A/B``,
        whole, with the unknown key."""
        pairs = [_fx("A/B/EUR")]

        report = _non_iso_report(pairs) if form == "with-report-currency" else _lots_report(pairs)

        assert [_shape(i) for i in _non_iso_issues(report)] == [_non_iso("A/B", NON_ISO_UNKNOWN, {"value": "A/B"})]
        assert _fx_groups(report) == {}, _named_pairs(report)

    def test_a_long_value_is_quoted_cut_and_keyed_whole(self):
        """Red until E-19b2 (TypeError). ``Australian Dollar`` (17 characters, a pair's side) and ``a currency nobody ever
        wrote`` (28, a held asset's): the params quote each as ``shown_currency_text`` does — 16 characters, then ``…`` —,
        the suggestion is read on the whole value (AUD), and the group key holds it whole."""
        assert [shown_currency_text(value) for value in ("Australian Dollar", "a currency nobody ever wrote")] == ["Australian Dolla…", "a currency nobod…"], "barrier: both values are longer than what is quoted"

        report = _non_iso_report([_fx("Australian Dollar/EUR")], assets=[(3, "Ledger fund", "a currency nobody ever wrote")])

        assert [_shape(i) for i in _non_iso_issues(report)] == [
            _non_iso("Australian Dollar", NON_ISO_SUGGESTION, {"value": "Australian Dolla…", "suggestion": "AUD"}),
            _non_iso("a currency nobody ever wrote", NON_ISO_UNKNOWN, {"value": "a currency nobod…"}, ((3, "Ledger fund"),)),
        ]

    def test_the_lots_form_names_the_pair_sides_with_the_generic_keys(self):
        """Red until E-19b2 (on its assertions: the call is HEAD's). The lots gap report passes neither parameter:
        ``978/EUR``, ``USD/EUR`` and ``USD/978`` give one issue for 978 — the generic key, also where 978 is a TO side —,
        and MISSING_FX_MARKET lists ``EUR-USD`` alone; the raw ``missing_fx_pairs`` is the input, whole."""
        pairs = [_fx("978/EUR"), _fx("USD/EUR"), _fx("USD/978")]

        report = _lots_report(pairs)

        assert [_shape(i) for i in _non_iso_issues(report)] == [_non_iso("978", NON_ISO_SUGGESTION, {"value": "978", "suggestion": "EUR"})]
        assert _named_pairs(report) == [("MISSING_FX_MARKET", "EUR-USD")]
        assert [pair.model_dump(mode="json") for pair in report.missing_fx_pairs] == [pair.model_dump(mode="json") for pair in pairs]

    def test_the_raw_missing_pairs_stay_the_full_input(self):
        """Red until E-19b2 (TypeError). The issues leave out the pairs with a side that is no ISO code; the raw
        ``missing_fx_pairs`` does not: the three pairs as given, in their order — and the status stays ``partial``: those
        conversions did fail."""
        pairs = [_fx("978/EUR", "2025-01-01"), _fx("eur/EUR", "2025-01-02"), _fx("USD/EUR", "2025-01-03")]

        report = _non_iso_report(pairs, assets=[(7, "Old ledger fund", "978")])

        assert [i.group_key for i in _non_iso_issues(report)] == ["non_iso_currency:978", "non_iso_currency:eur"], "barrier: both values are named"
        assert [pair.model_dump(mode="json") for pair in report.missing_fx_pairs] == [pair.model_dump(mode="json") for pair in pairs]
        assert report.data_quality_status == DataQualityStatus.PARTIAL

    def test_the_issues_sit_after_invalid_split_ratio_and_before_the_missing_fx_issues(self):
        """Red until E-19b2 (TypeError). With the issues around them in the report — INVALID_SPLIT_RATIO, both MISSING_FX_*
        codes, NAV_INCOMPLETE —, the NON_ISO_CURRENCY issues come right after INVALID_SPLIT_RATIO, sorted, and before every
        MISSING_FX_* issue."""
        report = _non_iso_report(
            [_fx("978/EUR"), _fx("USD/EUR"), _fx("RON/EUR")],
            assets=[(5, "Old ledger fund", "eur")],
            views=_make_views([_incomplete_state("2025-06-30")]),
            invalid_split_assets=[(6, "Split fund")],
            configured_fx_pairs={"EUR-RON"},
            real_provider_fx_pairs={"EUR-RON"},
        )

        assert [(i.code, i.group_key) for i in report.issues] == [
            (IssueCode.INVALID_SPLIT_RATIO, "invalid_split_ratio"),
            (NON_ISO_CURRENCY, "non_iso_currency:978"),
            (NON_ISO_CURRENCY, "non_iso_currency:eur"),
            (IssueCode.MISSING_FX_MARKET, "missing_fx"),
            (IssueCode.MISSING_FX_RATES, "missing_fx_rates"),
            (IssueCode.NAV_INCOMPLETE, "nav_incomplete"),
        ]

    def test_guard_canonical_pairs_passed_as_today_are_reported_as_today(self):
        """Green on HEAD and after: ``USD/EUR``, ``RON/EUR`` (configured, real provider) and ``NOK/EUR`` (configured,
        manual), passed as every caller passes them today — through ``DerivedViewsBuilder`` and in the lots form: no
        NON_ISO_CURRENCY issue, the three groups as they were."""
        kwargs = {"missing_fx_pairs_dto": [_fx("USD/EUR"), _fx("RON/EUR"), _fx("NOK/EUR")], "configured_fx_pairs": {"EUR-RON", "EUR-NOK"}, "real_provider_fx_pairs": {"EUR-RON"}}

        for report in (_make_views([_complete_state("2025-06-30")]).build_data_quality_report(**kwargs), build_data_quality_report([], **kwargs)):
            assert _non_iso_issues(report) == []
            assert _fx_groups(report) == {"missing_fx": ["EUR-USD"], "missing_fx_rates": ["EUR-RON"], "missing_fx_rates_manual": ["EUR-NOK"]}

    @pytest.mark.parametrize("assets", [pytest.param(None, id="no-asset-list"), pytest.param([], id="empty-asset-list")])
    def test_canonical_inputs_are_unchanged_by_the_new_parameters(self, assets):
        """Red until E-19b2 only by construction (TypeError: no such parameter). After the cure it guards that canonical
        codes everywhere — the pairs, the report currency EUR, no asset listed — give the very report the call without the
        new parameters gives: no issue added or dropped, no field moved."""
        views = _make_views([_incomplete_state("2025-06-29"), _complete_state("2025-06-30")])
        pairs = [_fx("USD/EUR", "2025-06-29"), _fx("RON/EUR", "2025-06-29"), _fx("NOK/EUR", "2025-06-29")]
        other = {"configured_fx_pairs": {"EUR-RON", "EUR-NOK"}, "real_provider_fx_pairs": {"EUR-RON"}, "invalid_split_assets": [(6, "Split fund")]}
        plain = views.build_data_quality_report(missing_fx_pairs_dto=pairs, **other)
        expected_codes = [IssueCode.INVALID_SPLIT_RATIO, IssueCode.MISSING_FX_MARKET, IssueCode.MISSING_FX_RATES, IssueCode.MISSING_FX_RATES, IssueCode.NAV_INCOMPLETE]
        assert [i.code for i in plain.issues] == expected_codes, "barrier: the comparison holds issues to keep"

        with_parameters = _non_iso_report(pairs, assets=assets, views=views, **other)

        assert with_parameters.model_dump(mode="json") == plain.model_dump(mode="json")


class TestNonIsoCurrencyAssets:
    """E-19b2: ``PortfolioService._non_iso_currency_assets(facts)``, a staticmethod, lists ``(asset_id, name, currency)``
    of the held assets (``HeldAssetQuoteFacts``: id, name and stored currency, read once by ``_held_asset_quote_facts``)
    whose currency ``is_canonical_iso_currency`` refuses, in the facts' order. Both report call sites pass it as
    ``non_iso_currency_assets`` (``or None``), with ``report_currency=base_currency``: pinned end to end in
    ``test_portfolio_api.py::TestNonIsoCurrencyDataQuality``.

    On HEAD 2fbbf4c4c ``PortfolioService`` has no such method: both tests fail on that alone. On HEAD 065c9df77
    ``HeldAssetQuoteFacts`` still requires the quote base, provider code and reported currency only the pence warning
    read (Z-32cr removes the three): ``_held`` fails on its TypeError, in both tests.
    """

    @staticmethod
    def _lister():
        """``PortfolioService._non_iso_currency_assets``; until it exists the test fails here."""
        lister = getattr(PortfolioService, "_non_iso_currency_assets", None)
        if lister is None:
            pytest.fail("red until E-19b2: PortfolioService has no _non_iso_currency_assets: nothing lists the held assets whose currency is no ISO 4217 code", pytrace=False)
        return lister

    def test_the_held_assets_stored_in_no_iso_code_are_listed_in_the_facts_order(self):
        """Red until E-19b2. Eight held assets, in an order that is not the ids': EUR, GBP (a London line in pounds) and
        XXX (an ISO 4217 code) are canonical; 978, eur, `` EUR`` (padded), GBp and Bolívar Soberano are not, and are
        listed as given — id, name, the currency as stored."""
        facts = [
            _held(12, "Fund in euro", "EUR"),
            _held(3, "Fund in 978", "978"),
            _held(8, "Lower-case fund", "eur"),
            _held(17, "London line in pounds", "GBP"),
            _held(5, "Padded fund", " EUR"),
            _held(21, "London line in pence", "GBp"),
            _held(2, "Test-code fund", "XXX"),
            _held(9, "Bolívar fund", "Bolívar Soberano"),
        ]

        listed = self._lister()(facts)

        assert listed == [(3, "Fund in 978", "978"), (8, "Lower-case fund", "eur"), (5, "Padded fund", " EUR"), (21, "London line in pence", "GBp"), (9, "Bolívar fund", "Bolívar Soberano")]

    def test_no_held_asset_or_canonical_ones_only_list_nothing(self):
        """Red until E-19b2 only by construction (no method). Then: no fact, and canonical currencies only, list nothing."""
        lister = self._lister()

        assert lister([]) == []
        assert lister([_held(12, "Fund in euro", "EUR"), _held(17, "London line in pounds", "GBP")]) == []


# =============================================================================
# THE REPORT'S SENTENCES (MF-SEC8-2a) — every key the builder writes has one in each language
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parents[5]
DATA_QUALITY_SOURCE = REPO_ROOT / "backend" / "app" / "services" / "financial_math" / "portfolio" / "data_quality.py"
LANGUAGES = ("en", "it", "fr", "es")


def _issue_constructions() -> list[ast.Call]:
    """Every ``DataQualityIssue(...)`` call written in ``data_quality.py``."""
    tree = ast.parse(DATA_QUALITY_SOURCE.read_text(encoding="utf-8"), filename=str(DATA_QUALITY_SOURCE))
    return [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "DataQualityIssue"]


def _literal_key(call: ast.Call) -> str | None:
    for keyword in call.keywords:
        if keyword.arg == "message_i18n_key" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
            return keyword.value.value
    return None


def _sentence(catalogue: dict, key: str) -> object:
    node: object = catalogue
    for part in key.split("."):
        node = node.get(part) if isinstance(node, dict) else None
    return node


def _has_sentence(catalogue: dict, key: str) -> bool:
    sentence = _sentence(catalogue, key)
    return isinstance(sentence, str) and bool(sentence.strip())


class TestReportSentences:
    """The builder's ``message_i18n_key`` values are read from its source (a key built on a rare branch would escape a
    run), then looked up in the four UI catalogues merged from their sources without the English fallback
    (``scripts.i18n_catalog.load_catalog``, as ``test_risk_warnings_i18n.py`` does for the risk warnings). No gate checked
    this for ``data_quality.py`` before MF-SEC8-2a.

    The gate reads the builder's source: a key the builder no longer writes (the floor's, ``dataQuality.transactionsBeforeFloor``,
    gone with MF-PAV-L1) is not asked for.
    """

    def test_the_scan_reaches_the_builder_s_keys(self):
        """Presence barrier (green on HEAD and after): a scan that found nothing would make the gate vacuous; and every
        issue the builder writes carries a literal key, the only kind the gate can check."""
        calls = _issue_constructions()
        keys = {_literal_key(call) for call in calls}

        assert {"dataQuality.missingPrice", "dataQuality.invalidSplitRatio", "dataQuality.transferShareMismatch"} <= keys, sorted(map(str, keys))
        assert [call.lineno for call in calls if _literal_key(call) is None] == [], "DataQualityIssue built without a literal message_i18n_key"

    @pytest.mark.parametrize("language", LANGUAGES)
    def test_every_key_the_builder_writes_has_a_sentence(self, language):
        """Gate (green on HEAD and after): each literal key of ``data_quality.py`` has a non-empty sentence in the
        language."""
        catalogue = load_catalog(language, fallback=False)
        keys = sorted({key for call in _issue_constructions() if (key := _literal_key(call)) is not None})

        missing = [key for key in keys if not _has_sentence(catalogue, key)]
        assert missing == [], f"{language}: no sentence for {missing}"


class TestNonIsoCurrencySentences:
    """E-19b2: the five keys of NON_ISO_CURRENCY (``NON_ISO_KEYS``) are written as literals in ``data_quality.py``, the only
    kind ``TestReportSentences`` reads: so its gate checks a sentence for each in every language. Their placeholders
    (``{value}``, ``{suggestion}``, ``{candidates}``, the same in the four languages) are pinned by the frontend, in
    ``DataQualityBanner.nonIso.test.ts``.
    """

    def test_the_builder_writes_the_five_keys_as_literals(self):
        """Red until E-19b2: ``data_quality.py`` writes none of them."""
        keys = {_literal_key(call) for call in _issue_constructions()}

        assert sorted(set(NON_ISO_KEYS) - keys) == [], "red until E-19b2: data_quality.py does not write these NON_ISO_CURRENCY keys as literals"
