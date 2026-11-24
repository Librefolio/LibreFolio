"""81 U35 — one sync per FX pair at a time: ``POST /fx/currencies/sync`` refuses a second sync of a pair that is already syncing.

The testlist (7.2, 23/11): during «Sinc. Tutto» (long) a 3-month sync of one pair started as well, with no warning. The
system must say that a sync is already running and make the reader wait. The guard that holds across tabs and users is the
backend's: an in-process registry of the pairs being synced (``services/fx/sync_claims.py``); the browser's own registry
covers one tab only.

The contract, pinned here:

1. A second request for a pair that is syncing is refused with **409** and ``detail`` ``{"code": "fx_sync_in_progress",
   "pairs": [{"pair": "EUR-USD", "started_at": "<ISO UTC>"}]}``: the pair and when its running sync began. The sync is
   never started twice.
2. Two requests for **different** pairs do not block each other: both run at the same time.
3. ``USD-EUR`` and ``EUR-USD`` are one pair (the request normalizes to alphabetical order).
4. A request that touches several pairs, one of them busy («Sinc. Tutto» over a pair already syncing), is refused whole,
   naming the busy pairs only; its free pairs are not claimed (a request for one of them right after still runs).
5. The claim ends with the sync, whatever its end: success, a refusal of the date range, a failure (500). A later request
   runs.
6. The weekly job skips the pairs that are busy and syncs the others (``claim_free_pairs``), logging the skipped ones.

How: the route of ``currencies.py`` mounted on a private ``FastAPI`` app served in this process by ``httpx.ASGITransport``
(no server, no port, no network), its session and user dependencies overridden, and ``sync_pairs_bulk`` replaced by a double
that waits on a gate the test opens (an ``asyncio.Event``) — so «at the same time» is verified, not assumed. Isolation: PURE
— no lane database, no network; the registry is cleared around every test.
"""

import asyncio
from datetime import UTC, date, datetime

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from backend.app.api.v1.fx import currencies
from backend.app.schemas.refresh import FXSyncBulkResponse, SyncDateRangeModel
from backend.app.services.fx import sync_claims
from backend.app.services.fx.sync_claims import FxSyncBusy, claim_free_pairs, claim_pairs, sync_pair_key

TODAY = date.today()
START = TODAY.replace(day=1)


@pytest.fixture(autouse=True)
def _clean_registry():
    sync_claims.reset_for_tests()
    yield
    sync_claims.reset_for_tests()


class _FakeSync:
    """A ``sync_pairs_bulk`` that records its calls and waits on a gate before answering."""

    def __init__(self) -> None:
        self.gate = asyncio.Event()
        self.started: list[list[str]] = []
        self.running = 0
        self.max_running = 0
        self.fail = False

    async def __call__(self, session, pairs, date_range):
        self.started.append(list(pairs))
        self.running += 1
        self.max_running = max(self.max_running, self.running)
        try:
            await self.gate.wait()
            if self.fail:
                raise RuntimeError("boom")
            return FXSyncBulkResponse(results=[], success_count=0, date_range=SyncDateRangeModel(start=date_range[0], end=date_range[1]), total_points_changed=0)
        finally:
            self.running -= 1


@pytest.fixture
def fake_sync(monkeypatch) -> _FakeSync:
    fake = _FakeSync()
    monkeypatch.setattr(currencies, "sync_pairs_bulk", fake)
    return fake


@pytest_asyncio.fixture
async def http():
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    app.include_router(currencies.router_currencies, prefix="/fx")
    app.dependency_overrides[currencies.get_session_generator] = lambda: None
    app.dependency_overrides[currencies.get_current_user] = lambda: None
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://fxsync.test") as client:
        yield client


def _body(*pairs: str) -> dict:
    return {"pairs": list(pairs), "start": START.isoformat(), "end": TODAY.isoformat()}


async def _post(http: httpx.AsyncClient, *pairs: str, wait: float | None = None) -> httpx.Response:
    """POST the sync. With ``wait``, a request that is still waiting for the gate after that many seconds fails the test:
    a refused request answers at once, so one that waits was let in."""
    request = http.post("/fx/currencies/sync", json=_body(*pairs))
    if wait is None:
        return await request
    try:
        return await asyncio.wait_for(request, timeout=wait)
    except TimeoutError:
        raise AssertionError(f"the request for {pairs} was not refused: it is waiting for its sync") from None


async def _until(condition, what: str, timeout: float = 5.0) -> None:
    """Poll a condition with a deadline (never a fixed sleep)."""
    deadline = asyncio.get_running_loop().time() + timeout
    while not condition():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError(f"never happened: {what}")
        await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_a_second_sync_of_the_same_pair_is_refused_with_409_and_never_started(http, fake_sync):
    first = asyncio.create_task(_post(http, "EUR-USD"))
    await _until(lambda: len(fake_sync.started) == 1, "the first sync started")

    second = await _post(http, "EUR-USD", wait=5)

    assert second.status_code == 409, second.text
    detail = second.json()["detail"]
    assert detail["code"] == "fx_sync_in_progress"
    assert [entry["pair"] for entry in detail["pairs"]] == ["EUR-USD"]
    started = datetime.fromisoformat(detail["pairs"][0]["started_at"])
    assert started.tzinfo is not None, "started_at carries no timezone"
    assert abs((datetime.now(UTC) - started).total_seconds()) < 30, "started_at is not when the running sync began"
    assert len(fake_sync.started) == 1, "the refused request started a sync"

    fake_sync.gate.set()
    assert (await first).status_code == 200


@pytest.mark.asyncio
async def test_two_different_pairs_sync_at_the_same_time(http, fake_sync):
    one = asyncio.create_task(_post(http, "EUR-USD"))
    other = asyncio.create_task(_post(http, "EUR-GBP"))
    await _until(lambda: fake_sync.max_running == 2, "both syncs running at once")

    fake_sync.gate.set()
    assert (await one).status_code == 200
    assert (await other).status_code == 200


@pytest.mark.asyncio
async def test_the_two_spellings_of_a_pair_are_one_pair(http, fake_sync):
    first = asyncio.create_task(_post(http, "EUR-USD"))
    await _until(lambda: len(fake_sync.started) == 1, "the first sync started")

    second = await _post(http, "USD-EUR", wait=5)

    assert second.status_code == 409, second.text
    assert [entry["pair"] for entry in second.json()["detail"]["pairs"]] == ["EUR-USD"]
    fake_sync.gate.set()
    await first


@pytest.mark.asyncio
async def test_a_request_over_several_pairs_is_refused_whole_naming_the_busy_ones_and_claims_nothing(http, fake_sync):
    busy = asyncio.create_task(_post(http, "EUR-USD"))
    await _until(lambda: len(fake_sync.started) == 1, "the pair is syncing")

    everything = await _post(http, "EUR-GBP", "EUR-USD", "CHF-EUR", wait=5)

    assert everything.status_code == 409, everything.text
    assert [entry["pair"] for entry in everything.json()["detail"]["pairs"]] == ["EUR-USD"], "it names more than the busy pair"
    assert len(fake_sync.started) == 1, "the refused request started a sync"
    # Its free pairs were never claimed: one of them syncs now.
    free = asyncio.create_task(_post(http, "EUR-GBP"))
    await _until(lambda: len(fake_sync.started) == 2, "a free pair of the refused request syncs")

    fake_sync.gate.set()
    assert (await busy).status_code == 200
    assert (await free).status_code == 200


@pytest.mark.asyncio
async def test_the_claim_ends_with_the_sync_whatever_its_end(http, fake_sync):
    fake_sync.gate.set()
    assert (await _post(http, "EUR-USD")).status_code == 200
    assert (await _post(http, "EUR-USD")).status_code == 200, "a finished sync still holds its pair"

    fake_sync.fail = True
    assert (await _post(http, "EUR-USD")).status_code == 500
    fake_sync.fail = False
    assert (await _post(http, "EUR-USD")).status_code == 200, "a failed sync still holds its pair"


@pytest.mark.asyncio
async def test_a_refused_date_range_holds_no_pair(http, fake_sync):
    fake_sync.gate.set()
    refused = await http.post("/fx/currencies/sync", json={"pairs": ["EUR-USD"], "start": TODAY.isoformat(), "end": (TODAY.replace(year=TODAY.year - 1)).isoformat()})
    assert refused.status_code == 400
    assert (await _post(http, "EUR-USD")).status_code == 200


def test_the_registry_claims_atomically_and_releases():
    with claim_pairs(["EUR-USD", "GBP-EUR"]):
        with pytest.raises(FxSyncBusy) as busy:
            with claim_pairs(["EUR-GBP", "CHF-EUR"]):
                pass
        assert list(busy.value.busy) == ["EUR-GBP"], "GBP-EUR and EUR-GBP are one pair"
        with claim_pairs(["CHF-EUR"]):
            pass
    with claim_pairs(["EUR-USD"]):
        pass


def test_the_key_of_a_pair_is_alphabetical():
    assert sync_pair_key("usd-eur") == "EUR-USD"
    assert sync_pair_key("EUR-USD") == "EUR-USD"


def test_the_weekly_job_takes_the_free_pairs_and_names_the_busy_ones():
    with claim_pairs(["EUR-USD"]):
        with claim_free_pairs(["EUR-USD", "EUR-GBP", "CHF-EUR"]) as (free, busy):
            assert free == ["EUR-GBP", "CHF-EUR"]
            assert list(busy) == ["EUR-USD"]
            with pytest.raises(FxSyncBusy):
                with claim_pairs(["EUR-GBP"]):
                    pass
        with claim_pairs(["EUR-GBP"]):  # the job's claim ended with it
            pass
