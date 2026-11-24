"""ENR-3b: ``GET /assets/enrichers/{code}/search`` answers a source's refusal as a 429, never as an empty list.

A plugin whose source refused the search for too many requests raises ``EnricherRateLimited`` (a ``RateLimitedError``
with ``retry_after``, in seconds, or None). The route (``search_enricher``) turns any ``RateLimitedError`` into 429 with
``detail = {error_code: "RATE_LIMITED", retry_after: s, message}`` and ``Retry-After: s``, ``s = max(1, ceil(wait))``, or
60 when the source named none (``source_refused``). Any other failure of the plugin is not a 429: it goes out of the
route as it is (the app's handlers answer it).

Called directly, never through the shared backend: the lane serves only ``mockenrich``, which does not search, and a test
cannot put a plugin in that process's registry. The route is called as a coroutine with the enricher lookup replaced by a
stub plugin (``monkeypatch``) and the per-user probe limit off, so the shared limiter is never consumed. No assertion
reads the message text.

Pure: no database, no server, no network.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.api.v1.assets import enrichers
from backend.app.db.models import AssetType
from backend.app.services.enrichers.base import EnricherBinding, EnricherRateLimited, EnricherSearchResult
from backend.app.utils.runtime.cooldown import RateLimitedError

pytestmark = pytest.mark.asyncio

CODE = "enr3b-stub-enricher"
USER = SimpleNamespace(id=9_301)


class StubSearcher:
    """An enricher that searches: answers ``outcome`` (results, or an exception to raise), recording each query."""

    supports_search = True

    def __init__(self, outcome: Any) -> None:
        self.outcome = outcome
        self.queries: list[str] = []

    def search(self, query: str) -> list[EnricherSearchResult]:
        self.queries.append(query)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


@pytest.fixture
def serve(monkeypatch: pytest.MonkeyPatch):
    """``serve(outcome)`` makes ``CODE`` an enricher answering ``outcome``; the probe limit is off."""

    def install(outcome: Any) -> StubSearcher:
        stub = StubSearcher(outcome)

        async def lookup(code: str) -> StubSearcher:
            assert code == CODE
            return stub

        monkeypatch.setattr(enrichers, "_enricher", lookup, raising=True)
        monkeypatch.setattr(enrichers, "enforce_probe_limit", lambda user_id: None, raising=True)
        return stub

    return install


async def _search() -> Any:
    return await enrichers.search_enricher(CODE, "enr3b word", USER)


async def _refused() -> HTTPException:
    with pytest.raises(HTTPException) as raised:
        await _search()
    return raised.value


@pytest.mark.parametrize(
    ("retry_after", "seconds"),
    [(12.3, 13), (12.0, 12), (0.2, 1), (0.0, 1), (120.0, 120), (None, 60)],
    ids=["rounded-up", "whole", "under-a-second", "zero", "long", "none-named"],
)
async def test_a_refused_search_is_a_429_with_retry_after(serve, retry_after, seconds):
    refusal = EnricherRateLimited("refused", retry_after=retry_after)
    stub = serve(refusal)

    error = await _refused()

    assert stub.queries == ["enr3b word"], "barrier: the plugin was asked"
    assert error.status_code == 429
    assert error.detail["error_code"] == "RATE_LIMITED"
    assert error.detail["retry_after"] == seconds and isinstance(error.detail["retry_after"], int)
    assert error.detail["message"]
    assert error.headers == {"Retry-After": str(seconds)}, "the header equals the detail's retry_after"
    assert error.__cause__ is None or error.__cause__ is refusal


async def test_any_rate_limited_error_is_a_429(serve):
    """The route reads the core's marker, not the enricher's subclass: another domain's refusal is the same answer."""
    serve(RateLimitedError("refused", retry_after=5.0))
    error = await _refused()
    assert (error.status_code, error.detail["error_code"], error.headers["Retry-After"]) == (429, "RATE_LIMITED", "5")


@pytest.mark.parametrize("failure", [ValueError("unexpected answer"), RuntimeError("yfinance is not installed")], ids=["value", "runtime"])
async def test_another_failure_is_not_a_429(serve, failure):
    serve(failure)
    with pytest.raises(type(failure)) as raised:
        await _search()
    assert raised.value is failure, "re-raised as it is, not turned into a refusal"


async def test_an_answer_is_returned_not_a_429(serve):
    hit = EnricherSearchResult(name="Enel SpA", binding=EnricherBinding("TICKER", "ENEL.MI"), asset_type=AssetType.STOCK, page_url="https://example.test/ENEL.MI")
    stub = serve([hit])

    answer = await _search()

    assert stub.queries == ["enr3b word"]
    assert [(item.name, item.binding.identifier_type, item.binding.identifier, item.asset_type) for item in answer] == [("Enel SpA", "TICKER", "ENEL.MI", AssetType.STOCK)]


async def test_an_empty_answer_stays_an_empty_list(serve):
    serve([])
    assert await _search() == []
