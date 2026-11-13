"""The missing-rate failures of a conversion as data (CP-11d): ``split_fx_issues`` and the sentence of an HTTP error (api/v1/fx/currencies.py)."""

from datetime import date

from backend.app.api.v1.fx.currencies import _issue_detail_text
from backend.app.services.fx.conversion_issues import FxIssueText, day_issue, group_fx_issues, split_fx_issues
from backend.app.services.fx.stretch_conversion import rate_not_found_error


def _no_rate(index: int, source: str, destination: str, day: date) -> FxIssueText:
    return rate_not_found_error(index, source, destination, day)


class TestSplitFxIssues:
    def test_empty_list(self):
        assert split_fx_issues([]) == ([], [])

    def test_a_single_failure_becomes_one_issue_in_the_direction_of_the_conversion(self):
        # The text names the pair alphabetically (CHF/JPY); the issue says what was converted into what.
        plain, issues = split_fx_issues([_no_rate(1, "JPY", "CHF", date(2026, 3, 1))])
        assert plain == []
        assert [(i.code, i.from_currency, i.to_currency, i.first_date, i.last_date, i.count) for i in issues] == [("rate_not_found", "JPY", "CHF", date(2026, 3, 1), date(2026, 3, 1), 1)]

    def test_the_days_of_one_pair_are_one_issue(self):
        errors = [_no_rate(n, "CHF", "JPY", date(2026, 3, n)) for n in (3, 1, 2, 2)]
        _plain, issues = split_fx_issues(errors)
        assert [(i.first_date, i.last_date, i.count) for i in issues] == [(date(2026, 3, 1), date(2026, 3, 3), 3)]  # the day asked twice counts once

    def test_the_two_directions_of_a_pair_are_two_issues(self):
        _plain, issues = split_fx_issues([_no_rate(1, "CHF", "JPY", date(2026, 3, 1)), _no_rate(2, "JPY", "CHF", date(2026, 3, 1))])
        assert [(i.from_currency, i.to_currency) for i in issues] == [("CHF", "JPY"), ("JPY", "CHF")]

    def test_a_text_that_says_no_rate_is_kept_apart_from_the_other_errors(self):
        plain, issues = split_fx_issues(["Some other error", _no_rate(1, "CHF", "JPY", date(2026, 3, 1)), "Unrelated error message"])
        assert plain == ["Some other error", "Unrelated error message"]
        assert len(issues) == 1

    def test_the_text_of_a_failure_still_reads_as_before(self):
        text = _no_rate(4, "JPY", "CHF", date(2026, 3, 1))
        assert text == "Conversion 4: No FX rate found for CHF/JPY on or before 2026-03-01. Please sync rates using POST /api/v1/fx/currencies/sync"


class TestGroupFxIssues:
    def test_event_and_price_failures_of_a_pair_stay_apart(self):
        issues = group_fx_issues([day_issue("event_rate_missing", "USD", "EUR", date(2026, 3, 1)), day_issue("rate_not_found", "USD", "EUR", date(2026, 3, 1))])
        assert [i.code for i in issues] == ["event_rate_missing", "rate_not_found"]

    def test_an_already_grouped_issue_adds_its_count(self):
        grouped = group_fx_issues([day_issue("rate_not_found", "USD", "EUR", date(2026, 3, d)) for d in (1, 2, 3)])
        merged = group_fx_issues([*grouped, day_issue("rate_not_found", "USD", "EUR", date(2026, 3, 9))])
        assert [(i.first_date, i.last_date, i.count) for i in merged] == [(date(2026, 3, 1), date(2026, 3, 9), 4)]


class TestIssueDetailText:
    def test_one_day_and_many_days(self):
        one = day_issue("rate_not_found", "CHF", "JPY", date(2026, 3, 1))
        assert "CHF/JPY on or before 2026-03-01" in _issue_detail_text(one)
        many = group_fx_issues([day_issue("rate_not_found", "CHF", "JPY", date(2026, 3, d)) for d in (1, 2, 3)])[0]
        assert "CHF/JPY (3 dates: 2026-03-01 … 2026-03-03)" in _issue_detail_text(many)
