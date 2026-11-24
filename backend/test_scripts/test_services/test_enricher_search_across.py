"""ENR-3 («Cerca online»): ``services/enrichers/search.py``, one text searched across several enrichers.

Under test, as the module docstring states the contract:

1. **``search_one(plugin, text)``**, one enricher's answer, a ``SearchOutcome``:
   - an enricher with a search runs it: ``ok`` via ``search``, its results, the types it accepts;
   - one without a search (ESMA, R12) is asked ``recognize`` only when the text has the form of an identifier type it
     accepts (ISIN, LEI, check digits included; any case, spaces around): found, one result bound to the upper-cased
     text; not found, none; ``ok`` via ``recognize``. A text that is not shaped, shaped for a type it does not accept, or
     that only looks like an ISIN (wrong check digit) is ``identifier_only`` with the accepted types and no call;
   - ``RateLimitedError`` is ``rate_limited`` with ``retry_after = refusal_wait(...)`` (ceil, at least 1, 60 when none);
   - any other exception is ``error``, ``error_code`` ``SOURCE_ERROR``, the message never in the outcome, the cause
     logged once with the enricher's code.
2. **``asked_codes``**: the codes given, each once, in order; else the default order of the asset type; else every enricher
   served.
3. **``search_enrichers``**: ``off`` (not served), ``not_covering`` and ``not_configured`` come first and run no call; the
   others run in threads and come as they finish; one failing never stops the others; a reader that stops after the
   first outcome (``aclose()``) cancels the tasks still pending, and no task is left awaiting a thread.

4. **The routes**, called as coroutines (no server): ``GET /assets/enrichers/search`` answers 422 for a text under 2
   characters once trimmed, for more than 16 codes and for a code that is not an enricher code (each before the probe
   limit is drawn); otherwise it draws the probe limit once, whatever the number of codes, and streams one
   ``enricher_results`` per code asked, with exactly the keys ``event, code, status, via, results,
   accepted_identifier_types, retry_after, error_code``, then ``done``; the per-enricher search is 400 for an enricher
   without a search and its results carry ``market``.

The enrichers are plain classes (never registered): the settings boundary (``configured_enricher``) is replaced by a table
of them, so no database is read. Every blocking plugin waits on a ``threading.Event`` with a bound, set at teardown.

Pure: no database, no server, no network.
"""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Callable, Iterator, Sequence
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.api.v1.assets import enrichers
from backend.app.db.models import AssetType
from backend.app.services.enrichers import search
from backend.app.services.enrichers.base import (
    EnricherBinding,
    EnricherPlugin,
    EnricherRateLimited,
    EnricherReadItem,
    EnricherRecognition,
    EnricherSearchResult,
    EnricherTerms,
)
from backend.app.services.enrichers.search import SOURCE_ERROR, SearchOutcome, SearchStatus, SearchVia, asked_codes, refusal_wait, search_enrichers, search_one
from backend.app.utils.runtime.cooldown import RateLimitedError

#: The bound on a whole search and on every hold: against a hang, never a wait.
DEADLINE = 15.0

ISIN = "IE00B4L5Y983"
ISIN_WRONG_CHECK = "IE00B4L5Y984"
LEI = "HWUPKR0MPOU8FGXBT394"


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


class _LabMethods(EnricherPlugin):
    def read(self, bindings, keys=None) -> Iterator[EnricherReadItem]:  # noqa: ARG002 — the contract's signature
        yield from ()

    def page_url(self, binding: EnricherBinding) -> str | None:
        return f"https://lab.invalid/{binding.identifier}"

    @property
    def test_cases(self) -> list[dict]:
        return []


class Recorder:
    """Records what a lab enricher was asked with, under a lock (the calls come from worker threads)."""

    def __init__(self) -> None:
        self.searches: list[str] = []
        self.recognized: list[EnricherBinding] = []
        self._lock = threading.Lock()

    def add_search(self, text: str) -> None:
        with self._lock:
            self.searches.append(text)

    def add_recognized(self, binding: EnricherBinding) -> None:
        with self._lock:
            self.recognized.append(binding)


@pytest.fixture
def lab() -> Iterator[Callable[..., tuple[EnricherPlugin, Recorder]]]:
    """``lab(code, accepts=…, search=…, recognize=…, covers=…)`` makes a plain enricher instance (never registered).

    ``search``: a callable ``text -> results`` (or raising); absent, the enricher has no search. ``recognize``: a callable
    ``binding -> EnricherRecognition`` (default: not found). Its recorder says what it was asked with.
    """

    def make(
        code: str,
        *,
        accepts: tuple[str, ...] = ("ISIN",),
        search: Callable[[str], list[EnricherSearchResult]] | None = None,
        recognize: Callable[[EnricherBinding], EnricherRecognition] | None = None,
        covers: Sequence[AssetType] = (AssetType.ETF, AssetType.STOCK),
    ) -> tuple[EnricherPlugin, Recorder]:
        recorder = Recorder()

        def do_recognize(self, binding: EnricherBinding) -> EnricherRecognition:  # noqa: ARG001
            recorder.add_recognized(binding)
            return recognize(binding) if recognize is not None else EnricherRecognition(found=False)

        attributes: dict[str, Any] = {
            "code": code,
            "name": f"Lab {code}",
            "terms": EnricherTerms.OPEN,
            "accepted_identifier_types": accepts,
            "default_priority": {asset_type: (10 if asset_type in covers else None) for asset_type in AssetType},
            "voices": {asset_type: frozenset({"description"}) for asset_type in covers},
            "recognize": do_recognize,
        }
        if search is not None:

            def do_search(self, query: str) -> list[EnricherSearchResult]:  # noqa: ARG001
                recorder.add_search(query)
                return search(query)

            attributes["search"] = do_search
        return type(f"LabSearch_{code}", (_LabMethods,), attributes)(), recorder

    return make


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch):
    """``served(plugin, missing=…)`` makes ``configured_enricher`` answer that plugin for its code; any other code is not
    served. The log of ``search`` is replaced by a recorder, ``served.logged``."""
    table: dict[str, tuple[EnricherPlugin, tuple[str, ...]]] = {}

    async def configured(code: str):
        plugin, missing = table.get(code, (None, ()))
        return plugin, missing

    class Logged:
        def __init__(self) -> None:
            self.warnings: list[tuple[str, dict[str, Any]]] = []

        def warning(self, message: str, **fields: Any) -> None:
            self.warnings.append((message, fields))

    logged = Logged()
    monkeypatch.setattr(search, "configured_enricher", configured, raising=True)
    monkeypatch.setattr(search, "logger", logged, raising=True)

    def serve(plugin: EnricherPlugin, missing: tuple[str, ...] = ()) -> EnricherPlugin:
        table[plugin.code] = (plugin, missing)
        return plugin

    serve.logged = logged  # type: ignore[attr-defined]
    return serve


def _hit(name: str = "Hit", identifier: str = "HIT", market: str | None = "Milan") -> EnricherSearchResult:
    return EnricherSearchResult(name=name, binding=EnricherBinding("TICKER", identifier), asset_type=AssetType.ETF, market=market)


async def _run(text: str, codes: Sequence[str], asset_type: AssetType | None = None) -> list[SearchOutcome]:
    async def consume() -> list[SearchOutcome]:
        return [outcome async for outcome in search_enrichers(text, codes, asset_type=asset_type)]

    return await asyncio.wait_for(consume(), DEADLINE)


def _by_code(outcomes: list[SearchOutcome]) -> dict[str, SearchOutcome]:
    assert len({outcome.code for outcome in outcomes}) == len(outcomes), f"one outcome per code: {outcomes}"
    return {outcome.code: outcome for outcome in outcomes}


# =============================================================================
# 1. search_one
# =============================================================================


def test_an_enricher_with_a_search_answers_its_results(lab):
    hits = [_hit("A", "AAA"), _hit("B", "BBB", market=None)]
    plugin, recorder = lab("lab_s1", accepts=("ISIN", "TICKER"), search=lambda text: hits)

    outcome = search_one(plugin, "world")

    assert recorder.searches == ["world"], "barrier: the search ran"
    assert (outcome.code, outcome.status, outcome.via) == ("lab_s1", SearchStatus.OK, SearchVia.SEARCH)
    assert outcome.results == hits
    assert outcome.accepted_identifier_types == ("ISIN", "TICKER")
    assert (outcome.retry_after, outcome.error_code) == (None, None)
    assert recorder.recognized == [], "an enricher with a search is never asked recognize"


def test_an_enricher_with_a_search_and_nothing_found_is_ok_and_empty(lab):
    plugin, _ = lab("lab_s2", search=lambda text: [])
    outcome = search_one(plugin, "nothing")
    assert (outcome.status, outcome.via, outcome.results) == (SearchStatus.OK, SearchVia.SEARCH, [])


@pytest.mark.parametrize("typed", [ISIN, ISIN.lower(), f"  {ISIN.lower()}  "], ids=["upper", "lower", "spaces"])
def test_an_isin_asks_recognize_of_an_enricher_without_search_and_a_found_is_one_result(lab, typed):
    plugin, recorder = lab("lab_r1", accepts=("ISIN", "LEI"), recognize=lambda binding: EnricherRecognition(found=True, name="Lab fund", page_url="https://lab.invalid/page"))

    outcome = search_one(plugin, typed)

    assert recorder.recognized == [EnricherBinding("ISIN", ISIN)], "asked once, with the upper-cased trimmed text"
    assert (outcome.status, outcome.via) == (SearchStatus.OK, SearchVia.RECOGNIZE)
    assert len(outcome.results) == 1
    (result,) = outcome.results
    assert (result.name, result.binding, result.page_url, result.market) == ("Lab fund", EnricherBinding("ISIN", ISIN), "https://lab.invalid/page", None)
    assert outcome.accepted_identifier_types == ("ISIN", "LEI")


def test_a_found_without_name_or_page_falls_back_to_the_identifier_and_the_plugins_page(lab):
    plugin, _ = lab("lab_r2", recognize=lambda binding: EnricherRecognition(found=True))
    (result,) = search_one(plugin, ISIN).results
    assert result.name == ISIN
    assert result.page_url == f"https://lab.invalid/{ISIN}"


def test_a_lei_asks_recognize_with_the_lei_type(lab):
    plugin, recorder = lab("lab_r3", accepts=("ISIN", "LEI"), recognize=lambda binding: EnricherRecognition(found=True, name="Lab entity"))
    outcome = search_one(plugin, LEI.lower())
    assert recorder.recognized == [EnricherBinding("LEI", LEI)]
    assert [result.binding for result in outcome.results] == [EnricherBinding("LEI", LEI)]


def test_a_not_found_recognize_is_ok_and_empty(lab):
    plugin, recorder = lab("lab_r4", recognize=lambda binding: EnricherRecognition(found=False))
    outcome = search_one(plugin, ISIN)
    assert len(recorder.recognized) == 1, "barrier: it was asked"
    assert (outcome.status, outcome.via, outcome.results) == (SearchStatus.OK, SearchVia.RECOGNIZE, [])


@pytest.mark.parametrize(
    ("accepts", "typed"),
    [
        (("ISIN", "LEI"), "world"),
        (("ISIN", "LEI"), "ENEL"),
        (("ISIN", "LEI"), ISIN_WRONG_CHECK),
        (("ISIN", "LEI"), "IE00B4L5Y98"),
        (("LEI",), ISIN),
        (("ISIN",), LEI),
        (("TICKER",), ISIN),
        (("TICKER", "ISIN"), "enel.mi"),
    ],
    ids=["a-name", "a-ticker", "typo-in-check-digit", "short-isin", "isin-for-a-lei-only-source", "lei-for-an-isin-only-source", "a-type-that-has-no-shape", "a-ticker-even-accepted"],
)
def test_a_text_that_is_not_an_identifier_of_an_accepted_type_is_identifier_only_and_costs_no_call(lab, accepts, typed):
    plugin, recorder = lab("lab_i1", accepts=accepts, recognize=lambda binding: EnricherRecognition(found=True))

    outcome = search_one(plugin, typed)

    assert (outcome.status, outcome.via, outcome.results) == (SearchStatus.IDENTIFIER_ONLY, None, [])
    assert outcome.accepted_identifier_types == accepts
    assert recorder.recognized == [], "no call to the source"


@pytest.mark.parametrize(("retry_after", "seconds"), [(12.3, 13), (12.0, 12), (0.2, 1), (None, 60)], ids=["rounded-up", "whole", "under-a-second", "none-named"])
def test_a_refusal_is_rate_limited_with_the_wait_of_the_per_enricher_route(lab, served, retry_after, seconds):
    refusal = EnricherRateLimited("refused", retry_after=retry_after)

    def refuse(text: str) -> list[EnricherSearchResult]:
        raise refusal

    plugin, _ = lab("lab_l1", search=refuse)

    outcome = search_one(plugin, "world")

    assert refusal_wait(refusal) == seconds
    assert (outcome.status, outcome.retry_after, outcome.results, outcome.error_code) == (SearchStatus.RATE_LIMITED, seconds, [], None)
    assert isinstance(outcome.retry_after, int)
    assert outcome.accepted_identifier_types == plugin.accepted_identifier_types


def test_any_rate_limited_error_is_a_refusal_and_a_recognize_one_too(lab, served):
    def refuse(binding: EnricherBinding) -> EnricherRecognition:
        raise RateLimitedError("refused", retry_after=5.0)

    plugin, _ = lab("lab_l2", recognize=refuse)
    outcome = search_one(plugin, ISIN)
    assert (outcome.status, outcome.retry_after) == (SearchStatus.RATE_LIMITED, 5)


@pytest.mark.parametrize("via", ["search", "recognize"])
def test_another_failure_is_an_error_with_a_code_the_message_stays_in_the_log_once(lab, served, via):
    secret = "boom: token=SECRET-123"

    def fail(*_: Any) -> Any:
        raise RuntimeError(secret)

    plugin, _ = lab("lab_e1", search=fail) if via == "search" else lab("lab_e1", recognize=fail)

    outcome = search_one(plugin, "world" if via == "search" else ISIN)

    assert (outcome.status, outcome.error_code, outcome.results, outcome.retry_after) == (SearchStatus.ERROR, SOURCE_ERROR, [], None)
    assert SOURCE_ERROR == "SOURCE_ERROR"
    assert secret not in repr(outcome) and "SECRET" not in repr(outcome)
    warnings = served.logged.warnings
    assert len(warnings) == 1, "logged once"
    assert warnings[0][1]["enricher"] == "lab_e1"
    assert isinstance(warnings[0][1].get("exc_info"), RuntimeError), "the cause is in the log"


# =============================================================================
# 2. asked_codes
# =============================================================================


def test_given_codes_are_asked_once_each_in_their_order(monkeypatch):
    monkeypatch.setattr(search, "default_order", lambda asset_type: pytest.fail("not asked when codes are given"))
    assert asked_codes(["b", "a", "b", "c", "a"], AssetType.ETF) == ["b", "a", "c"]
    assert asked_codes(["x"], None) == ["x"]


def test_without_codes_the_default_order_of_the_type_is_asked(monkeypatch):
    seen: list[AssetType] = []
    monkeypatch.setattr(search, "default_order", lambda asset_type: seen.append(asset_type) or ["z", "y"])
    for empty in (None, []):
        assert asked_codes(empty, AssetType.ETF) == ["z", "y"]
    assert seen == [AssetType.ETF, AssetType.ETF]


def test_without_codes_and_type_every_served_enricher_is_asked(monkeypatch, lab):
    first, _ = lab("lab_a1")
    second, _ = lab("lab_a2", covers=(AssetType.BOND,))
    monkeypatch.setattr(search, "installed_enrichers", lambda: [first, second])
    monkeypatch.setattr(search, "default_order", lambda asset_type: pytest.fail("no type: not asked"))
    assert asked_codes(None, None) == ["lab_a1", "lab_a2"]
    assert asked_codes([], None) == ["lab_a1", "lab_a2"]


# =============================================================================
# 3. search_enrichers
# =============================================================================


@pytest.mark.asyncio
async def test_an_unknown_code_is_off_and_asks_nothing(served, lab):
    plugin, recorder = lab("lab_o1", search=lambda text: [_hit()])
    served(plugin)

    outcomes = _by_code(await _run("world", ["lab_o1", "lab_nowhere"]))

    assert outcomes["lab_o1"].status == SearchStatus.OK, "barrier: the served one answered"
    assert outcomes["lab_nowhere"] == SearchOutcome(code="lab_nowhere", status=SearchStatus.OFF)
    assert recorder.searches == ["world"]


@pytest.mark.asyncio
async def test_off_not_covering_and_not_configured_come_first_without_a_call(served, lab):
    release = threading.Event()
    entered = threading.Event()

    def slow(text: str) -> list[EnricherSearchResult]:
        entered.set()
        assert release.wait(DEADLINE)
        return [_hit()]

    try:
        running, running_rec = lab("lab_p1", search=slow)
        bond_only, bond_rec = lab("lab_p2", accepts=("ISIN", "LEI"), search=lambda text: [_hit()], covers=(AssetType.BOND,))
        unconfigured, unconf_rec = lab("lab_p3", accepts=("ISIN",), search=lambda text: [_hit()])
        for item, missing in ((running, ()), (bond_only, ()), (unconfigured, ("api_key",))):
            served(item, missing)

        arrived: list[SearchOutcome] = []

        async def consume() -> None:
            async for outcome in search_enrichers("world", ["lab_p1", "lab_nowhere", "lab_p2", "lab_p3"], asset_type=AssetType.ETF):
                arrived.append(outcome)
                if len(arrived) == 3:
                    release.set()

        await asyncio.wait_for(consume(), DEADLINE)
    finally:
        release.set()

    assert [(outcome.code, outcome.status) for outcome in arrived[:3]] == [
        ("lab_nowhere", SearchStatus.OFF),
        ("lab_p2", SearchStatus.NOT_COVERING),
        ("lab_p3", SearchStatus.NOT_CONFIGURED),
    ], "settled before the slow one: in the order asked, ahead of the calls in flight"
    assert (arrived[3].code, arrived[3].status) == ("lab_p1", SearchStatus.OK)
    assert arrived[1].accepted_identifier_types == ("ISIN", "LEI") and arrived[2].accepted_identifier_types == ("ISIN",)
    assert (bond_rec.searches, unconf_rec.searches, running_rec.searches) == ([], [], ["world"]), "the refused ones were never called"


@pytest.mark.asyncio
async def test_without_an_asset_type_every_covering_is_asked(served, lab):
    bond_only, recorder = lab("lab_c1", search=lambda text: [_hit()], covers=(AssetType.BOND,))
    served(bond_only)
    (outcome,) = await _run("world", ["lab_c1"], asset_type=None)
    assert outcome.status == SearchStatus.OK and recorder.searches == ["world"]


@pytest.mark.asyncio
async def test_one_failing_source_does_not_stop_the_others(served, lab):
    def fail(text: str) -> list[EnricherSearchResult]:
        raise RuntimeError("down")

    def refuse(text: str) -> list[EnricherSearchResult]:
        raise EnricherRateLimited("slow down", retry_after=2.0)

    failing, _ = lab("lab_f1", search=fail)
    refusing, _ = lab("lab_f2", search=refuse)
    working, _ = lab("lab_f3", search=lambda text: [_hit("Fine", "FINE")])
    esma, _ = lab("lab_f4", accepts=("ISIN", "LEI"))
    for item in (failing, refusing, working, esma):
        served(item)

    outcomes = _by_code(await _run("world", ["lab_f1", "lab_f2", "lab_f3", "lab_f4"]))

    assert outcomes["lab_f1"].status == SearchStatus.ERROR and outcomes["lab_f1"].error_code == SOURCE_ERROR
    assert (outcomes["lab_f2"].status, outcomes["lab_f2"].retry_after) == (SearchStatus.RATE_LIMITED, 2)
    assert [result.name for result in outcomes["lab_f3"].results] == ["Fine"]
    assert outcomes["lab_f4"].status == SearchStatus.IDENTIFIER_ONLY
    assert sorted(warning[1]["enricher"] for warning in served.logged.warnings) == ["lab_f1", "lab_f2"], "each failure logged once, with its enricher"


@pytest.mark.asyncio
async def test_the_answers_come_as_they_finish_not_in_the_order_asked(served, lab):
    release_first = threading.Event()
    second_done = threading.Event()

    def first(text: str) -> list[EnricherSearchResult]:
        assert release_first.wait(DEADLINE)
        return [_hit("First", "ONE")]

    def second(text: str) -> list[EnricherSearchResult]:
        second_done.set()
        return [_hit("Second", "TWO")]

    slow, _ = lab("lab_t1", search=first)
    quick, _ = lab("lab_t2", search=second)
    served(slow)
    served(quick)
    arrived: list[str] = []
    try:

        async def consume() -> None:
            async for outcome in search_enrichers("world", ["lab_t1", "lab_t2"]):
                arrived.append(outcome.code)
                release_first.set()

        await asyncio.wait_for(consume(), DEADLINE)
    finally:
        release_first.set()

    assert arrived == ["lab_t2", "lab_t1"]


@pytest.mark.asyncio
async def test_a_reader_that_stops_early_cancels_the_calls_still_in_flight(served, lab):
    """The closing condition: after ``aclose()`` no task of the search is left awaiting its thread."""
    release = threading.Event()
    entered = threading.Event()

    def blocked(text: str) -> list[EnricherSearchResult]:
        entered.set()
        release.wait(DEADLINE)
        return [_hit("Late", "LATE")]

    stuck, stuck_rec = lab("lab_x1", search=blocked)
    quick, _ = lab("lab_x2", search=lambda text: [_hit("Quick", "QUICK")])
    served(stuck)
    served(quick)
    before = asyncio.all_tasks()
    generator = search_enrichers("world", ["lab_x1", "lab_x2"])
    try:
        first = await asyncio.wait_for(anext(generator), DEADLINE)
        assert first.code == "lab_x2", "barrier: the quick one answered while the other is held"
        assert await asyncio.wait_for(asyncio.to_thread(entered.wait, DEADLINE), DEADLINE + 5), "barrier: the held call is running in its thread"
        mine = asyncio.all_tasks() - before
        pending = [task for task in mine if not task.done()]
        assert pending, "barrier: a task is awaiting the held call"

        await generator.aclose()
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert all(task.done() for task in mine), "every task the search made is finished"
        assert all(task.cancelled() for task in pending), "the ones in flight were cancelled, not awaited"
        with pytest.raises(StopAsyncIteration):
            await anext(generator)
    finally:
        release.set()
    assert stuck_rec.searches == ["world"], "the held call really was made"
    await asyncio.sleep(0.05)
    assert all(task.done() for task in asyncio.all_tasks() - before - {asyncio.current_task()}), "nothing of the search is left running"


@pytest.mark.asyncio
async def test_a_reader_that_stops_before_the_first_answer_leaves_nothing_awaiting(served, lab):
    """The same, with only held calls: the generator is closed while it waits for none of them to be done."""
    release = threading.Event()
    entered = threading.Event()

    def blocked(text: str) -> list[EnricherSearchResult]:
        entered.set()
        release.wait(DEADLINE)
        return []

    stuck, _ = lab("lab_y1", search=blocked)
    off_first = "lab_nowhere"
    served(stuck)
    before = asyncio.all_tasks()
    generator = search_enrichers("world", [off_first, "lab_y1"])
    try:
        first = await asyncio.wait_for(anext(generator), DEADLINE)
        assert (first.code, first.status) == (off_first, SearchStatus.OFF)
        await generator.aclose()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        leftover = asyncio.all_tasks() - before - {asyncio.current_task()}
        assert all(task.done() for task in leftover), "no task left awaiting"
    finally:
        release.set()


# =============================================================================
# 4. The routes
# =============================================================================

USER = SimpleNamespace(id=9_303)
EVENT_KEYS = {"event", "code", "status", "via", "results", "accepted_identifier_types", "retry_after", "error_code"}


@pytest.fixture
def probe(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """The probe limit replaced by a counter of the users it was drawn for."""
    drawn: list[int] = []
    monkeypatch.setattr(enrichers, "enforce_probe_limit", lambda user_id: drawn.append(user_id), raising=True)
    return drawn


async def _across(q: str, codes: list[str] | None = None, asset_type: AssetType | None = None) -> list[dict[str, Any]]:
    response = await enrichers.search_across_enrichers(q=q, codes=codes, asset_type=asset_type, current_user=USER)
    assert response.media_type == "text/event-stream"
    chunks = [chunk async for chunk in response.body_iterator]
    events = []
    for chunk in chunks:
        text = chunk if isinstance(chunk, str) else chunk.decode()
        assert text.startswith("data: ") and text.endswith("\n\n"), text
        events.append(json.loads(text[len("data: ") :]))
    return events


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["", " ", "a", "  a  ", "\t\n"], ids=["empty", "blank", "one", "one-padded", "whitespace"])
async def test_a_text_under_two_characters_once_trimmed_is_422_before_the_probe_limit(probe, text):
    with pytest.raises(HTTPException) as refused:
        await _across(text, ["mockenrich"])
    assert refused.value.status_code == 422
    assert probe == [], "a refused request draws nothing"


@pytest.mark.asyncio
async def test_two_characters_once_trimmed_are_enough(probe, served):
    events = await _across("  ab ", ["lab_nowhere"])
    assert [event["event"] for event in events] == ["enricher_results", "done"]
    assert probe == [USER.id]


@pytest.mark.asyncio
@pytest.mark.parametrize("codes", [[f"lab_c{index}" for index in range(17)], ["Bad Code"], ["ok_code", "UPPER"], ["1abc"], ["a/b"], [""]], ids=["seventeen", "space", "upper", "digit-first", "slash", "empty-code"])
async def test_too_many_codes_or_a_bad_code_is_422(probe, codes):
    with pytest.raises(HTTPException) as refused:
        await _across("world", codes)
    assert refused.value.status_code == 422
    assert probe == []


@pytest.mark.asyncio
async def test_sixteen_codes_are_accepted(probe, served):
    codes = [f"lab_c{index}" for index in range(16)]
    events = await _across("world", codes)
    assert [event["code"] for event in events[:-1]] == codes
    assert events[-1] == {"event": "done", "codes": codes}


@pytest.mark.asyncio
async def test_one_enricher_results_per_code_then_done_with_exactly_the_keys_and_one_probe(probe, served, lab):
    hit = _hit("Lab World", "LABW", market="Milan")
    searching, _ = lab("lab_q1", accepts=("ISIN", "TICKER"), search=lambda text: [hit])
    esma, _ = lab("lab_q2", accepts=("ISIN", "LEI"))
    refusing, _ = lab("lab_q3", search=lambda text: (_ for _ in ()).throw(EnricherRateLimited("refused", retry_after=7.2)))
    failing, _ = lab("lab_q4", search=lambda text: (_ for _ in ()).throw(RuntimeError("secret detail")))
    for item in (searching, esma, refusing, failing):
        served(item)
    codes = ["lab_q1", "lab_q2", "lab_q3", "lab_q4", "lab_nowhere"]

    events = await _across("  world  ", codes)

    assert probe == [USER.id], "counted once, however many enrichers it asks"
    *answers, done = events
    assert done == {"event": "done", "codes": codes}
    assert all(set(event) == EVENT_KEYS for event in answers), [set(event) ^ EVENT_KEYS for event in answers]
    assert all(event["event"] == "enricher_results" for event in answers)
    assert sorted(event["code"] for event in answers) == sorted(codes), "one per code"
    by_code = {event["code"]: event for event in answers}
    ok = by_code["lab_q1"]
    assert (ok["status"], ok["via"], ok["retry_after"], ok["error_code"]) == ("ok", "search", None, None)
    assert ok["accepted_identifier_types"] == ["ISIN", "TICKER"]
    assert [(r["name"], r["binding"]["identifier_type"], r["binding"]["identifier"], r["market"]) for r in ok["results"]] == [("Lab World", "TICKER", "LABW", "Milan")]
    assert (by_code["lab_q2"]["status"], by_code["lab_q2"]["via"], by_code["lab_q2"]["results"]) == ("identifier_only", None, [])
    assert by_code["lab_q2"]["accepted_identifier_types"] == ["ISIN", "LEI"]
    assert (by_code["lab_q3"]["status"], by_code["lab_q3"]["retry_after"]) == ("rate_limited", 8)
    assert (by_code["lab_q4"]["status"], by_code["lab_q4"]["error_code"]) == ("error", "SOURCE_ERROR")
    assert "secret" not in json.dumps(by_code["lab_q4"])
    assert (by_code["lab_nowhere"]["status"], by_code["lab_nowhere"]["via"], by_code["lab_nowhere"]["results"]) == ("off", None, [])


@pytest.mark.asyncio
async def test_without_codes_the_type_decides_who_is_asked(probe, served, lab, monkeypatch):
    plugin, _ = lab("lab_d1", search=lambda text: [_hit()])
    served(plugin)
    seen: list[AssetType] = []
    monkeypatch.setattr(search, "default_order", lambda asset_type: seen.append(asset_type) or ["lab_d1"])

    events = await _across("world", None, AssetType.ETF)

    assert seen == [AssetType.ETF]
    assert [event.get("code") for event in events] == ["lab_d1", None]
    assert events[-1] == {"event": "done", "codes": ["lab_d1"]}


@pytest.mark.asyncio
async def test_a_repeated_code_is_asked_and_reported_once(probe, served, lab):
    plugin, recorder = lab("lab_d2", search=lambda text: [])
    served(plugin)
    events = await _across("world", ["lab_d2", "lab_d2"])
    assert [event["code"] for event in events[:-1]] == ["lab_d2"]
    assert events[-1]["codes"] == ["lab_d2"]
    assert recorder.searches == ["world"]


@pytest.mark.asyncio
async def test_the_per_enricher_search_is_400_for_an_enricher_without_search(lab, monkeypatch):
    plugin, _ = lab("lab_n1")
    assert plugin.supports_search is False, "barrier"

    async def lookup(code: str) -> EnricherPlugin:
        return plugin

    monkeypatch.setattr(enrichers, "_enricher", lookup, raising=True)
    monkeypatch.setattr(enrichers, "enforce_probe_limit", lambda user_id: None, raising=True)
    with pytest.raises(HTTPException) as refused:
        await enrichers.search_enricher("lab_n1", "world", USER)
    assert refused.value.status_code == 400


@pytest.mark.asyncio
async def test_the_per_enricher_search_results_carry_the_market(lab, monkeypatch):
    plugin, _ = lab("lab_n2", accepts=("TICKER",), search=lambda text: [_hit("A", "AAA", market="Milan"), _hit("B", "BBB", market=None)])

    async def lookup(code: str) -> EnricherPlugin:
        return plugin

    monkeypatch.setattr(enrichers, "_enricher", lookup, raising=True)
    monkeypatch.setattr(enrichers, "enforce_probe_limit", lambda user_id: None, raising=True)

    answer = await enrichers.search_enricher("lab_n2", "world", USER)

    assert [(item.binding.identifier, item.market) for item in answer] == [("AAA", "Milan"), ("BBB", None)]
