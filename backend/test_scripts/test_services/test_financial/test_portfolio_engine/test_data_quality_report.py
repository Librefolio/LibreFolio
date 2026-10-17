"""Unit tests for DerivedViewsBuilder.build_data_quality_report().

Verifies that all 5 active portfolio IssueCodes are generated correctly
from input data. Pure tests — no DB, no async.

``TestTransferShareMismatchIssue`` (J-43b) reads ``ShareMismatch`` from ``models`` inside its tests, so on a ``models``
without it only those tests fail, never the module's collection.
"""

import re
from datetime import date
from decimal import Decimal
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
