"""Unit tests for DerivedViewsBuilder.build_data_quality_report().

Verifies that all 5 active portfolio IssueCodes are generated correctly
from input data. Pure tests — no DB, no async.

``TestTransferShareMismatchIssue`` (J-43b) reads ``ShareMismatch`` from ``models`` inside its tests, so on a ``models``
without it only those tests fail, never the module's collection. ``TestTransactionsBeforeFloorIssue`` (MF-SEC8-2a) reads
``RowsBeforeFloor`` the same way. ``TestReportSentences`` (MF-SEC8-2a) reads two files and writes none: the builder's
source and the four UI catalogues (merged in memory by ``scripts.i18n_catalog.load_catalog``).
"""

import ast
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import backend.app.services.financial_math.portfolio.models as portfolio_models
from backend.app.schemas.portfolio import (
    DataQualityStatus,
    IssueCode,
    IssueDomain,
    IssueSeverity,
    MissingPriceAsset,
    StalePriceAsset,
)
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState
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
        assert report.incomplete_nav_dates == []

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
# TRANSACTIONS_BEFORE_FLOOR (MF-SEC8-2a)
# =============================================================================

TRANSACTIONS_BEFORE_FLOOR = "TRANSACTIONS_BEFORE_FLOOR"


def _rows_before_floor(count: int, earliest: date):
    """A ``RowsBeforeFloor`` (MF-SEC8-2a), read from ``models`` when the test runs."""
    record = getattr(portfolio_models, "RowsBeforeFloor", None)
    if record is None:
        pytest.fail("financial_math.portfolio.models has no RowsBeforeFloor (MF-SEC8-2a): nothing carries the rows dated before 1900 to the report")
    return record(count=count, earliest=earliest)


def _floor_report(rows_before_floor):
    """The report of one complete day, given ``rows_before_floor``: a TypeError (no such parameter) fails the test."""
    try:
        return _make_views([_complete_state("2025-06-30")]).build_data_quality_report(rows_before_floor=rows_before_floor)
    except TypeError as exc:
        pytest.fail(f"build_data_quality_report(…, rows_before_floor=…) raised {exc!r}: it takes the scope's rows dated before 1900 (MF-SEC8-2a)")


def _floor_issues(report) -> list:
    """The report's TRANSACTIONS_BEFORE_FLOOR issues, matched on the code's value (HEAD has no enum member to name)."""
    return [i for i in report.issues if i.code == TRANSACTIONS_BEFORE_FLOOR]


class TestTransactionsBeforeFloorIssue:
    """MF-SEC8-2a: a transaction stored before ``EARLIEST_RANGE_START`` (1900-01-01; an older version or a hand edit — N74
    refuses new ones) is replayed on its own date, but no state is emitted before the floor, so the histories start on
    1900-01-01 silently. ``build_data_quality_report(rows_before_floor=RowsBeforeFloor(count, earliest))`` turns the
    engine's count into one WARNING ``TRANSACTIONS_BEFORE_FLOOR`` (coordinator's decision, no CTA): key
    ``dataQuality.transactionsBeforeFloor``, params ``{count, earliest}`` (the date in ISO form), ``count``, group
    ``transactions_before_floor``, no asset, no pair, no CTA. None, or a count of 0, gives none. Like the other warnings
    that fill no legacy gap field (MISSING_COST_BASIS, INVALID_SPLIT_RATIO), it does not move ``data_quality_status``.

    On HEAD f4a1e374f ``IssueCode`` has no ``TRANSACTIONS_BEFORE_FLOOR``, ``models`` no ``RowsBeforeFloor`` and the builder
    no ``rows_before_floor``: each test that needs one of them fails on that alone, and the module still collects.
    """

    def test_transactions_before_floor_is_a_portfolio_issue_code(self):
        """Red on HEAD: IssueCode has no TRANSACTIONS_BEFORE_FLOOR (the frontend keys on the string)."""
        assert getattr(IssueCode, TRANSACTIONS_BEFORE_FLOOR, None) == TRANSACTIONS_BEFORE_FLOOR, "schemas.portfolio.IssueCode has no TRANSACTIONS_BEFORE_FLOOR (MF-SEC8-2a)"

    def test_rows_before_the_floor_produce_one_warning_with_their_shape(self):
        """Red on HEAD (no RowsBeforeFloor). Three rows, the earliest on 0001-01-01 (``date.min``, the oldest a stored row
        can be): one WARNING with the contract's shape — the date written in full, four digits."""
        report = _floor_report(_rows_before_floor(3, date(1, 1, 1)))

        matching = _floor_issues(report)
        assert len(matching) == 1, [i.code for i in report.issues]
        issue = matching[0]
        assert {
            "domain": issue.domain,
            "severity": issue.severity,
            "message_i18n_key": issue.message_i18n_key,
            "message_params": issue.message_params,
            "count": issue.count,
            "affected_asset_ids": issue.affected_asset_ids,
            "affected_asset_names": issue.affected_asset_names,
            "affected_fx_pairs": issue.affected_fx_pairs,
            "cta_action": issue.cta_action,
            "cta_target": issue.cta_target,
            "group_key": issue.group_key,
        } == {
            "domain": IssueDomain.PORTFOLIO,
            "severity": IssueSeverity.WARNING,
            "message_i18n_key": "dataQuality.transactionsBeforeFloor",
            "message_params": {"count": 3, "earliest": "0001-01-01"},
            "count": 3,
            "affected_asset_ids": [],
            "affected_asset_names": [],
            "affected_fx_pairs": [],
            "cta_action": None,
            "cta_target": None,
            "group_key": "transactions_before_floor",
        }

    def test_the_params_are_the_count_and_the_earliest_date_given(self):
        """Red on HEAD (no RowsBeforeFloor). One row on 1899-12-31, the floor's eve: the params follow the record, they
        are not a constant."""
        issues = _floor_issues(_floor_report(_rows_before_floor(1, date(1899, 12, 31))))

        assert [(i.count, i.message_params) for i in issues] == [(1, {"count": 1, "earliest": "1899-12-31"})], issues

    @pytest.mark.parametrize("count", [pytest.param(None, id="none"), pytest.param(0, id="zero-count")])
    def test_nothing_before_the_floor_produces_no_issue(self, count):
        """Red on HEAD only by construction (TypeError: no ``rows_before_floor``; for a count of 0, no RowsBeforeFloor
        either). After the cure it guards that nothing to report gives no issue, not one counting 0."""
        rows_before_floor = None if count is None else _rows_before_floor(count, date(1, 1, 1))

        assert _floor_issues(_floor_report(rows_before_floor)) == []

    def test_guard_the_default_call_gives_no_issue(self):
        """Green on HEAD and after: a caller that does not pass the parameter gets no such issue."""
        report = _make_views([_complete_state("2025-06-30")]).build_data_quality_report()

        assert _floor_issues(report) == []

    def test_the_warning_alone_moves_the_status_as_the_other_warnings_do(self):
        """Red on HEAD (no RowsBeforeFloor). Barrier first: the warning is there. Then the status is what a warning that
        fills no legacy gap field leaves (MISSING_COST_BASIS alone, on the same day): ``ok`` — the histories are complete
        from the floor on, nothing in them is missing or carried forward."""
        report = _floor_report(_rows_before_floor(2, date(1890, 1, 1)))
        other_warning = _make_views([_complete_state("2025-06-30")]).build_data_quality_report(missing_cost_basis_assets=[(7, "ACME")])

        assert [i.count for i in _floor_issues(report)] == [2], [i.code for i in report.issues]
        assert [i.severity for i in other_warning.issues] == [IssueSeverity.WARNING], "precondition: the comparison is another warning, alone"
        assert report.data_quality_status == other_warning.data_quality_status == DataQualityStatus.OK


# =============================================================================
# QUOTE_IN_MINOR_UNIT (Z-32 (c))
# =============================================================================

QUOTE_IN_MINOR_UNIT = "QUOTE_IN_MINOR_UNIT"
#: Two London lines, in an order that is not the ids': the issue lists them as given.
QUOTED_IN_PENCE = [(9, "Vodafone Group"), (4, "Lloyds Banking Group")]


def _quote_report(quote_in_minor_unit_assets, views: DerivedViewsBuilder | None = None):
    """The report of one complete day (or of ``views``), given ``quote_in_minor_unit_assets``: a TypeError (no such
    parameter) fails the test."""
    views = views or _make_views([_complete_state("2025-06-30")])
    try:
        return views.build_data_quality_report(quote_in_minor_unit_assets=quote_in_minor_unit_assets)
    except TypeError as exc:
        pytest.fail(f"build_data_quality_report(…, quote_in_minor_unit_assets=…) raised {exc!r}: it takes the held assets whose provider quotes them in a minor unit the quote base does not account for (Z-32 (c) §6)")


def _quote_issues(report) -> list:
    """The report's QUOTE_IN_MINOR_UNIT issues, matched on the code's value (HEAD has no enum member to name)."""
    return [i for i in report.issues if i.code == QUOTE_IN_MINOR_UNIT]


class TestQuoteInMinorUnitIssue:
    """Z-32 (c) §6: Yahoo quotes a London line in pence (``GBp``); the price schemas fold the code to ``GBP``
    and keep the numbers, so a holding is worth a hundred times too much until its quote base is set to 100 by hand, and
    nothing told the user. ``build_data_quality_report(quote_in_minor_unit_assets=[(asset_id, name), …])`` — the held
    assets whose provider reported a minor unit the quote base does not account for (``PortfolioService`` decides who,
    pinned end to end in ``test_portfolio_api.py::TestQuoteInMinorUnitDataQuality``) — gives one issue shaped exactly as
    INVALID_SPLIT_RATIO's: domain ``portfolio``, code ``QUOTE_IN_MINOR_UNIT``, WARNING, key
    ``dataQuality.quoteInMinorUnit``, params ``{count}``, ``count``, the assets by id and name in the order given, a
    ``navigate_asset`` CTA to the first one, group ``quote_in_minor_unit``. None or an empty list gives none. Like
    INVALID_SPLIT_RATIO it fills no legacy field: every other field of the report, ``data_quality_status`` included, is
    what it is without it.

    On HEAD 80cef0e43 ``IssueCode`` has no ``QUOTE_IN_MINOR_UNIT`` and the builder no ``quote_in_minor_unit_assets``
    (TypeError): each test that needs one of them fails on that alone, and the module still collects.
    """

    def test_quote_in_minor_unit_is_a_portfolio_issue_code(self):
        """Red on HEAD: IssueCode has no QUOTE_IN_MINOR_UNIT (the frontend keys on the string)."""
        assert getattr(IssueCode, QUOTE_IN_MINOR_UNIT, None) == QUOTE_IN_MINOR_UNIT, "schemas.portfolio.IssueCode has no QUOTE_IN_MINOR_UNIT (Z-32 (c))"

    def test_listed_assets_produce_one_warning_with_their_shape(self):
        """Red on HEAD (TypeError: no ``quote_in_minor_unit_assets``). Vodafone (9) then Lloyds (4): one WARNING with
        the contract's shape — the assets in the order given, the CTA to the first given, not to the lowest id."""
        report = _quote_report(QUOTED_IN_PENCE)

        matching = _quote_issues(report)
        assert len(matching) == 1, [i.code for i in report.issues]
        issue = matching[0]
        assert {
            "domain": issue.domain,
            "severity": issue.severity,
            "message_i18n_key": issue.message_i18n_key,
            "message_params": issue.message_params,
            "count": issue.count,
            "affected_asset_ids": issue.affected_asset_ids,
            "affected_asset_names": issue.affected_asset_names,
            "affected_fx_pairs": issue.affected_fx_pairs,
            "cta_action": issue.cta_action,
            "cta_target": issue.cta_target,
            "group_key": issue.group_key,
        } == {
            "domain": IssueDomain.PORTFOLIO,
            "severity": IssueSeverity.WARNING,
            "message_i18n_key": "dataQuality.quoteInMinorUnit",
            "message_params": {"count": 2},
            "count": 2,
            "affected_asset_ids": [9, 4],
            "affected_asset_names": ["Vodafone Group", "Lloyds Banking Group"],
            "affected_fx_pairs": [],
            "cta_action": "navigate_asset",
            "cta_target": "9",
            "group_key": "quote_in_minor_unit",
        }

    def test_the_issue_is_shaped_as_invalid_split_ratio_s(self):
        """Red on HEAD (TypeError). The same two assets given to INVALID_SPLIT_RATIO (green on HEAD: the barrier) and to
        the new list: the two issues are the same object but for the code, the key and the group (§6: «exactly like
        INVALID_SPLIT_RATIO's shape»)."""
        views = _make_views([_complete_state("2025-06-30")])
        split = views.build_data_quality_report(invalid_split_assets=QUOTED_IN_PENCE)
        assert [i.code for i in split.issues] == [IssueCode.INVALID_SPLIT_RATIO], "barrier: the comparison is INVALID_SPLIT_RATIO, alone"

        matching = _quote_issues(_quote_report(QUOTED_IN_PENCE, views))

        assert len(matching) == 1, matching
        expected = split.issues[0].model_dump(mode="json") | {"code": QUOTE_IN_MINOR_UNIT, "message_i18n_key": "dataQuality.quoteInMinorUnit", "group_key": "quote_in_minor_unit"}
        assert matching[0].model_dump(mode="json") == expected

    def test_one_asset_counts_one(self):
        """Red on HEAD (TypeError). One asset: count 1, its id the CTA's target — the params follow the list, they are
        not a constant."""
        issues = _quote_issues(_quote_report([(31, "Tesco")]))

        assert [(i.count, i.message_params, i.affected_asset_ids, i.affected_asset_names, i.cta_target) for i in issues] == [(1, {"count": 1}, [31], ["Tesco"], "31")], issues

    @pytest.mark.parametrize("listed", [pytest.param(None, id="none"), pytest.param([], id="empty")])
    def test_nothing_listed_produces_no_issue(self, listed):
        """Red on HEAD only by construction (TypeError: no ``quote_in_minor_unit_assets``). After the cure it guards that
        nothing to report gives no issue, not one counting 0."""
        report = _quote_report(listed)

        assert _quote_issues(report) == []
        assert report.issues == [], [i.code for i in report.issues]

    def test_guard_the_default_call_gives_no_issue(self):
        """Green on HEAD and after: a caller that does not pass the parameter gets no such issue."""
        report = _make_views([_complete_state("2025-06-30")]).build_data_quality_report()

        assert _quote_issues(report) == []

    def test_the_rest_of_the_report_moves_as_with_an_invalid_split_ratio(self):
        """Red on HEAD (TypeError). Barrier first, green on HEAD: INVALID_SPLIT_RATIO alone leaves every other field of
        the report — the legacy lists, the counters, ``data_quality_status`` (``ok``) — as the report without it. Then
        the new warning alone leaves them exactly as INVALID_SPLIT_RATIO does."""
        views = _make_views([_complete_state("2025-06-29"), _complete_state("2025-06-30")])
        plain = views.build_data_quality_report()
        split = views.build_data_quality_report(invalid_split_assets=QUOTED_IN_PENCE)
        assert split.model_dump(mode="json", exclude={"issues"}) == plain.model_dump(mode="json", exclude={"issues"}), "barrier: INVALID_SPLIT_RATIO moves no other field"
        assert split.data_quality_status == DataQualityStatus.OK, "barrier: INVALID_SPLIT_RATIO alone leaves the status ok"

        quote = _quote_report(QUOTED_IN_PENCE, views)

        assert [i.code for i in quote.issues] == [QUOTE_IN_MINOR_UNIT], [i.code for i in quote.issues]
        assert quote.model_dump(mode="json", exclude={"issues"}) == split.model_dump(mode="json", exclude={"issues"})


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

    On HEAD f4a1e374f the scan and the gate are green (twelve keys, all translated); the floor's sentence is red: no
    catalogue has ``dataQuality.transactionsBeforeFloor``.
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
        language — the floor's key included once the builder writes it."""
        catalogue = load_catalog(language, fallback=False)
        keys = sorted({key for call in _issue_constructions() if (key := _literal_key(call)) is not None})

        missing = [key for key in keys if not _has_sentence(catalogue, key)]
        assert missing == [], f"{language}: no sentence for {missing}"

    @pytest.mark.parametrize("language", LANGUAGES)
    def test_the_floor_sentence_names_the_count_and_the_earliest_date(self, language):
        """Red on HEAD: no sentence. After the cure each language has one, and it uses both params the warning sends —
        a translation without ``{earliest}`` would hide the date the user has to correct."""
        catalogue = load_catalog(language, fallback=False)

        assert _has_sentence(catalogue, "dataQuality.transactionsBeforeFloor"), f"{language}: no sentence for dataQuality.transactionsBeforeFloor"
        sentence = str(_sentence(catalogue, "dataQuality.transactionsBeforeFloor"))
        assert {"{count}", "{earliest}"} <= set(re.findall(r"\{\w+\}", sentence)), f"{language}: {sentence!r}"
