"""The conversions that failed for want of an exchange rate, as data instead of prose (CP-11d).

``convert_bulk`` and the series that read its rates describe a failure as a text (kept: the services read it, the logs show it). The
text that says *no rate* is an ``FxIssueText``: a ``str`` that also carries the ``FxConversionIssue`` it describes, in the direction of
the conversion. An endpoint separates the two with ``split_fx_issues``: the texts that are no rate failure stay in ``errors``, the
others become ``fx_issues``, grouped by pair. Nothing reads the prose back.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from backend.app.schemas.common import FxConversionIssue


class FxIssueText(str):
    """The text of a failed conversion, carrying what it says (``issue``): a ``str`` for whoever prints it, data for whoever reads it."""

    issue: FxConversionIssue

    def __new__(cls, text: str, issue: FxConversionIssue) -> FxIssueText:
        self = super().__new__(cls, text)
        self.issue = issue
        return self


def day_issue(code: str, source: str, destination: str, day: date) -> FxConversionIssue:
    """One day of one conversion that failed, from ``source`` to ``destination``."""
    return FxConversionIssue(code=code, from_currency=source, to_currency=destination, first_date=day, last_date=day, count=1)


def group_fx_issues(issues: Iterable[FxConversionIssue]) -> list[FxConversionIssue]:
    """The issues of one answer, one per (code, direction): the days it failed on, counted once, in the order the pairs first failed."""
    days: dict[tuple[str, str, str], set[date]] = {}
    counted: dict[tuple[str, str, str], int] = {}
    bounds: dict[tuple[str, str, str], tuple[date, date]] = {}
    for issue in issues:
        key = (issue.code, issue.from_currency, issue.to_currency)
        first, last = bounds.get(key, (issue.first_date, issue.last_date))
        bounds[key] = (min(first, issue.first_date), max(last, issue.last_date))
        if issue.first_date == issue.last_date:
            days.setdefault(key, set()).add(issue.first_date)
        else:
            counted[key] = counted.get(key, 0) + issue.count
        days.setdefault(key, set())
    return [
        FxConversionIssue(code=code, from_currency=source, to_currency=destination, first_date=bounds[key][0], last_date=bounds[key][1], count=len(days[key]) + counted.get(key, 0))
        for key in bounds
        for code, source, destination in [key]
    ]


def split_fx_issues(errors: Iterable[str]) -> tuple[list[str], list[FxConversionIssue]]:
    """``errors`` as the endpoint answers them: the texts that carry no issue, and the issues of the others, grouped."""
    plain: list[str] = []
    issues: list[FxConversionIssue] = []
    for error in errors:
        issue = getattr(error, "issue", None)
        if isinstance(issue, FxConversionIssue):
            issues.append(issue)
        else:
            plain.append(str(error))
    return plain, group_fx_issues(issues)
