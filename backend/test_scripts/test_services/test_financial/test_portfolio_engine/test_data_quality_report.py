"""Unit tests for DerivedViewsBuilder.build_data_quality_report().

Verifies that all 5 active portfolio IssueCodes are generated correctly
from input data. Pure tests — no DB, no async.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from backend.app.schemas.portfolio import (
    IssueCode,
    IssueSeverity,
    MissingPriceAsset,
    StalePriceAsset,
)
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services.portfolio_engine import DailyPortfolioState, DerivedViewsBuilder

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


def _make_missing_fx(pair: str = "EUR-USD") -> WACMissingPairInfo:
    mock = MagicMock(spec=WACMissingPairInfo)
    mock.pair = pair
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
        assert date(2025, 1, 1) in report.incomplete_nav_dates


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
