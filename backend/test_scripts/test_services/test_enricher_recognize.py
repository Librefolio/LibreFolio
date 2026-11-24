"""«Recognize» in cascade over the enrichers (project 68, lot B4): ``services/enrichers/recognize.py``.

Under test, ``recognize_cascade(asset_type, identifiers, *, plugins)`` — an async iterator of ``Recognized`` and
``IdentifierLearned`` — as its module docstring states the contract:

1. **Who is asked.** Every enricher of ``plugins`` that covers the asset type and accepts the type of a known
   identifier. One that does not cover the type, or accepts no known type, is never asked.
2. **The cascade.** A ``found`` naming a strong identifier (ISIN, LEI) not known yet yields ``IdentifierLearned`` (its
   source: the enricher's code) **before** the answers of the round it starts: the enrichers not found yet that accept
   it. One identifier learned twice is learned and searched once. A strong identifier different from the known one of
   its type makes that answer a ``conflict`` (``conflicts`` names it): it adds nothing and starts nothing. A weak one (a
   ticker) is only reported in ``identifiers``.
3. **Who is asked again** (consultant, 16/11). An enricher is asked with one identifier at a time, the strongest first
   (ISIN, LEI before TICKER; among equals, in the order known), until one finds: after a clean «not found» it is asked
   with the next one it accepts, from the request or learned, never twice with the same (type, value). An enricher
   found is never asked again; a ticker that finds but names a different ISIN is a ``conflict``.
4. **Failures.** A plugin that raises is an ``error`` answer carrying its message, and it stops that enricher: no call
   with another identifier, not even one learned later. The others still answer.
5. **Order of arrival** (round 38). The plugin calls run at once in worker threads and their answers come out as they
   complete: two enrichers of equal degree, each held on a ``threading.Event`` inside ``recognize``, released B first
   then A, give B's answer first. ``bindings.default_order(found_order=…)`` then keeps that arrival order between them,
   where the order by code alone says the opposite.
6. **The real test enricher.** ``mockenrich`` (test mode): an ISIN is found and brings ``lei_of(isin)``, learned from
   it; an identifier with the ``UNKNOWN`` prefix is not found and teaches nothing.

The synthetic enrichers are classes registered on ``EnricherRegistry`` under ``lab_recog_*`` codes (removed with their
claims at teardown) and passed explicitly through ``plugins=``. Each records the (type, value) it was asked with in a
list of its own, under a lock (the calls come from worker threads). The order of the first round's answers is never
asserted: only what the contract states.

Every cascade is consumed under a deadline (``DEADLINE``), a bound against a hang, never a wait. Held plugins wait on
their own event with a bound and raise when it runs out, and the test sets every event in ``finally``.

PURE: no database, no server, no network.

Red until the consultant's rule of 16/11 lands in B4: the identifiers are tried in the request's order, not the
strongest first, and an error is followed by a call with the next identifier.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic import ValidationError

from backend.app.config import is_test_mode
from backend.app.db.models import AssetType
from backend.app.schemas.assets.enrichers import FAEnricherRecognition, FAEnricherRecognizeRequest
from backend.app.services.enrichers import bindings
from backend.app.services.enrichers.base import EnricherBinding, EnricherPlugin, EnricherReadItem, EnricherRecognition, EnricherTerms
from backend.app.services.enrichers.recognize import IdentifierLearned, Recognized, RecognizeStatus, Seed, recognize_cascade
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.plugin_settings.fields import release_env_variables
from backend.test_scripts.test_utils import print_section, print_success

TEST_MODE_VARIABLE = "LIBREFOLIO_TEST_MODE"
MOCK_CODE = "mockenrich"
SETTINGS_FAMILY = "enricher"
LAB_PREFIX = "lab_recog_"
LAB_CLASS_PREFIX = "LabRecogEnricher_"
#: The bound on a whole cascade, and on every hold: against a hang, never a wait.
DEADLINE = 15.0

ISIN = "XS0LABRECOG1"
ISIN_OTHER = "XS0LABRECOG2"
LEI = "LABRECOGLEI000000001"
TICKER = "LABRCG"

Event = Recognized | IdentifierLearned


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


def _test_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TEST_MODE_VARIABLE, "1")
    assert is_test_mode() is True, f"barrier: with {TEST_MODE_VARIABLE}=1 is_test_mode() is false"


class _LabMethods(EnricherPlugin):
    """The abstract methods but ``recognize``: a synthetic enricher differs by its declarations and its answer."""

    def read(self, bindings, keys=None) -> Iterator[EnricherReadItem]:  # noqa: ARG002 — the contract's signature
        yield from ()

    def page_url(self, binding: EnricherBinding) -> str | None:
        return f"https://lab.invalid/{binding.identifier}"

    @property
    def test_cases(self) -> list[dict]:
        return []


@dataclass
class Lab:
    """A registered synthetic enricher: its code, an instance to pass through ``plugins=``, and the (type, value) of
    every ``recognize`` call, in call order."""

    code: str
    plugin: EnricherPlugin
    calls: list[tuple[str, str]] = field(default_factory=list)
    #: The whole binding of every call (ENR-2: the parameters a seed carries), in call order.
    bindings: list[EnricherBinding] = field(default_factory=list)


Answer = Callable[[EnricherBinding], EnricherRecognition]


def found(**identifiers: str) -> Answer:
    return lambda binding: EnricherRecognition(found=True, name=f"Lab {binding.identifier}", identifiers=dict(identifiers))


def not_found() -> Answer:
    return lambda binding: EnricherRecognition(found=False)


@pytest.fixture
def lab() -> Iterator[Callable[..., Lab]]:
    """``lab(name, accepts=…, answer=…, covers=…)`` registers a synthetic enricher (degree 10 for each covered type, the
    others ``None``) and gives back its ``Lab``. Removed from the registry, with its claims, at teardown."""
    codes: list[str] = []

    def register(name: str, *, accepts: tuple[str, ...] = ("ISIN",), answer: Answer, covers: Sequence[AssetType] = (AssetType.ETF,), params: Sequence[str] = ()) -> Lab:
        code = f"{LAB_PREFIX}{name}"
        calls: list[tuple[str, str]] = []
        bindings_seen: list[EnricherBinding] = []
        lock = threading.Lock()

        def recognize(self, binding: EnricherBinding) -> EnricherRecognition:  # noqa: ARG001 — the contract's signature
            with lock:
                calls.append((binding.identifier_type, binding.identifier))
                bindings_seen.append(binding)
            return answer(binding)

        attributes: dict[str, Any] = {
            "code": code,
            "name": f"Lab recognize {name} (testing)",
            "terms": EnricherTerms.OPEN,
            "accepted_identifier_types": accepts,
            "default_priority": {asset_type: (10 if asset_type in covers else None) for asset_type in AssetType},
            "voices": {asset_type: frozenset({"description"}) for asset_type in covers},
            "recognize": recognize,
            "params_schema": property(lambda self: [{"key": key, "type": "string"} for key in params]),
        }
        codes.append(code)
        EnricherRegistry.register(type(f"{LAB_CLASS_PREFIX}{name}", (_LabMethods,), attributes))
        plugin = EnricherRegistry.get_plugin_instance(code)
        assert isinstance(plugin, EnricherPlugin), f"barrier: {code} is not served after its registration"
        return Lab(code=code, plugin=plugin, calls=calls, bindings=bindings_seen)

    yield register
    storage = EnricherRegistry._get_storage()
    for code in codes:
        stored = storage.get(code)
        if stored is not None and getattr(stored, "__name__", "").startswith(LAB_CLASS_PREFIX):
            storage.pop(code, None)
        release_env_variables(SETTINGS_FAMILY, code)


async def _run(identifiers: dict[str, str], labs: Sequence[Lab | EnricherPlugin], asset_type: AssetType = AssetType.ETF, seeds: Sequence[Seed] = ()) -> list[Event]:
    """The whole cascade over ``labs``, consumed to its end under ``DEADLINE``."""
    plugins = [item.plugin if isinstance(item, Lab) else item for item in labs]

    async def consume() -> list[Event]:
        return [event async for event in recognize_cascade(asset_type, identifiers, plugins=plugins, seeds=seeds)]

    events = await asyncio.wait_for(consume(), DEADLINE)
    assert all(isinstance(event, (Recognized, IdentifierLearned)) for event in events), f"only Recognized and IdentifierLearned: {events}"
    return events


def _answers(events: list[Event], code: str) -> list[Recognized]:
    return [event for event in events if isinstance(event, Recognized) and event.code == code]


def _learned(events: list[Event]) -> list[IdentifierLearned]:
    return [event for event in events if isinstance(event, IdentifierLearned)]


def _asked(answer: Recognized) -> tuple[str, str]:
    return answer.binding.identifier_type, answer.binding.identifier


def _mine(order: list[str], codes: list[str]) -> list[str]:
    """``order`` restricted to the test's own codes: real enrichers may sit anywhere among them."""
    return [code for code in order if code in codes]


# =============================================================================
# 1. The cascade: a learned strong identifier starts a new round
# =============================================================================


@pytest.mark.asyncio
async def test_an_isin_found_with_a_lei_asks_the_enricher_that_accepts_only_the_lei(lab) -> None:
    """The plan's test: A (ISIN) finds the ISIN and names a LEI; B (LEI only) is asked with that LEI and finds it. The
    LEI is learned from A before B's answer."""
    print_section("recognize: ISIN → A → LEI → B")
    a = lab("plan_a", accepts=("ISIN",), answer=found(LEI=LEI))
    b = lab("plan_b", accepts=("LEI",), answer=found())

    events = await _run({"ISIN": ISIN}, [a, b])

    a_answers, b_answers = _answers(events, a.code), _answers(events, b.code)
    assert len(a_answers) == 1 and a_answers[0].status == RecognizeStatus.FOUND, f"A finds the ISIN: {events}"
    assert _asked(a_answers[0]) == ("ISIN", ISIN) and dict(a_answers[0].identifiers) == {"LEI": LEI}, f"A's answer: {a_answers[0]}"
    assert _learned(events) == [IdentifierLearned(identifier_type="LEI", identifier=LEI, source=a.code)], f"the LEI is learned from A, once: {events}"
    assert len(b_answers) == 1 and b_answers[0].status == RecognizeStatus.FOUND and _asked(b_answers[0]) == ("LEI", LEI), f"B finds the LEI: {events}"
    assert events.index(_learned(events)[0]) < events.index(b_answers[0]), f"the LEI is learned before B's answer: {events}"
    assert a.calls == [("ISIN", ISIN)] and b.calls == [("LEI", LEI)], f"A asked with the ISIN, B with the LEI, once each: {a.calls} {b.calls}"
    print_success("the LEI learned from A found B")


@pytest.mark.asyncio
async def test_the_same_lei_from_two_sources_is_learned_and_searched_once(lab) -> None:
    a1 = lab("twice_a1", accepts=("ISIN",), answer=found(LEI=LEI))
    a2 = lab("twice_a2", accepts=("ISIN",), answer=found(LEI=LEI))
    b = lab("twice_b", accepts=("LEI",), answer=found())

    events = await _run({"ISIN": ISIN}, [a1, a2, b])

    assert [answer.status for answer in _answers(events, a1.code) + _answers(events, a2.code)] == [RecognizeStatus.FOUND, RecognizeStatus.FOUND], f"both sources find the ISIN, the same LEI is no conflict: {events}"
    learned = _learned(events)
    assert len(learned) == 1 and (learned[0].identifier_type, learned[0].identifier) == ("LEI", LEI) and learned[0].source in {a1.code, a2.code}, f"the LEI is learned once: {learned}"
    assert b.calls == [("LEI", LEI)], f"B is asked exactly once with the LEI: {b.calls}"
    assert len(_answers(events, b.code)) == 1, f"one answer from B: {events}"


@pytest.mark.asyncio
async def test_an_isin_different_from_the_known_one_is_a_conflict_that_adds_and_starts_nothing(lab) -> None:
    """A names another ISIN (and a LEI): its answer is a conflict naming that ISIN. Nothing is learned: C (ISIN only, not
    found) is never asked with the other ISIN, D (LEI only) is never asked at all."""
    a = lab("conflict_a", accepts=("ISIN",), answer=found(ISIN=ISIN_OTHER, LEI=LEI))
    c = lab("conflict_c", accepts=("ISIN",), answer=not_found())
    d = lab("conflict_d", accepts=("LEI",), answer=found())

    events = await _run({"ISIN": ISIN}, [a, c, d])

    a_answers = _answers(events, a.code)
    assert len(a_answers) == 1 and a_answers[0].status == RecognizeStatus.CONFLICT, f"A's answer is a conflict: {events}"
    assert dict(a_answers[0].conflicts) == {"ISIN": ISIN_OTHER}, f"the conflict names the other ISIN: {a_answers[0]}"
    assert [answer.status for answer in _answers(events, c.code)] == [RecognizeStatus.NOT_FOUND], f"barrier: C answered: {events}"
    assert _learned(events) == [], f"a conflict teaches nothing: {events}"
    assert c.calls == [("ISIN", ISIN)], f"C is never asked with the other ISIN: {c.calls}"
    assert d.calls == [] and _answers(events, d.code) == [], f"the conflict's LEI starts nothing: {d.calls}"


@pytest.mark.asyncio
async def test_a_weak_identifier_returned_is_only_reported(lab) -> None:
    a = lab("weak_a", accepts=("ISIN",), answer=found(TICKER=TICKER))
    t = lab("weak_t", accepts=("TICKER",), answer=found())

    events = await _run({"ISIN": ISIN}, [a, t])

    a_answers = _answers(events, a.code)
    assert len(a_answers) == 1 and a_answers[0].status == RecognizeStatus.FOUND, f"barrier: A finds the ISIN: {events}"
    assert dict(a_answers[0].identifiers) == {"TICKER": TICKER}, f"the ticker is reported in A's answer: {a_answers[0]}"
    assert _learned(events) == [], f"a ticker is never learned: {events}"
    assert t.calls == [] and _answers(events, t.code) == [], f"a ticker starts nothing: {t.calls}"


# =============================================================================
# 2. Who is asked, with what
# =============================================================================


@pytest.mark.asyncio
async def test_an_enricher_not_covering_the_type_or_accepting_no_known_type_is_never_asked(lab) -> None:
    asked = lab("who_asked", accepts=("ISIN",), answer=found())
    not_covering = lab("who_stock", accepts=("ISIN",), answer=found(), covers=(AssetType.STOCK,))
    lei_only = lab("who_lei", accepts=("LEI",), answer=found())

    events = await _run({"ISIN": ISIN}, [asked, not_covering, lei_only])

    assert [answer.status for answer in _answers(events, asked.code)] == [RecognizeStatus.FOUND], f"barrier: the enricher that covers ETF and accepts the ISIN answers: {events}"
    assert not_covering.calls == [] and _answers(events, not_covering.code) == [], f"an enricher not covering ETF is never asked: {not_covering.calls}"
    assert lei_only.calls == [] and _answers(events, lei_only.code) == [], f"an enricher accepting no known type is never asked: {lei_only.calls}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("identifiers", "expected"),
    [
        pytest.param({"ISIN": ISIN, "LEI": LEI}, [("ISIN", ISIN), ("LEI", LEI)], id="isin-lei"),
        pytest.param({"LEI": LEI, "ISIN": ISIN}, [("LEI", LEI), ("ISIN", ISIN)], id="lei-isin"),
        pytest.param({"TICKER": TICKER, "ISIN": ISIN}, [("ISIN", ISIN), ("TICKER", TICKER)], id="ticker-isin"),
    ],
)
async def test_an_enricher_not_found_is_asked_with_each_identifier_it_accepts_strongest_first(lab, identifiers, expected) -> None:
    """Every identifier known, an enricher accepting them all that never finds: asked with one at a time, the strong
    ones (ISIN, LEI) before the weak ones (TICKER) whatever the request's order, among equals in the order known; each
    once, each a clean «not found»."""
    both = lab(f"strongest_{'_'.join(kind.lower() for kind in identifiers)}", accepts=("ISIN", "LEI", "TICKER"), answer=not_found())

    events = await _run(identifiers, [both])

    assert both.calls == expected, f"one at a time, strongest first, among equals in the order known: {both.calls}"
    assert [(_asked(answer), answer.status) for answer in _answers(events, both.code)] == [(asked, RecognizeStatus.NOT_FOUND) for asked in expected], f"one not found per identifier, in that order: {events}"


@pytest.mark.asyncio
async def test_an_enricher_stops_at_the_first_identifier_that_finds(lab) -> None:
    """The ticker named first, the ISIN tried first: found by the ISIN, the ticker is never tried."""
    a = lab("stop_found", accepts=("ISIN", "TICKER"), answer=found())

    events = await _run({"TICKER": TICKER, "ISIN": ISIN}, [a])

    assert a.calls == [("ISIN", ISIN)], f"found by the ISIN, never asked with the ticker: {a.calls}"
    assert [(_asked(answer), answer.status) for answer in _answers(events, a.code)] == [(("ISIN", ISIN), RecognizeStatus.FOUND)], f"one answer: {events}"


def _found_by_ticker(**identifiers: str) -> Answer:
    """Not found by anything but the ticker; found by the ticker, naming ``identifiers``."""
    return lambda binding: EnricherRecognition(found=binding.identifier_type == "TICKER", name="Lab by ticker" if binding.identifier_type == "TICKER" else None, identifiers=dict(identifiers) if binding.identifier_type == "TICKER" else {})


@pytest.mark.asyncio
async def test_an_enricher_not_found_by_the_isin_is_found_by_the_ticker(lab) -> None:
    a = lab("by_ticker", accepts=("ISIN", "TICKER"), answer=_found_by_ticker())

    events = await _run({"ISIN": ISIN, "TICKER": TICKER}, [a])

    assert a.calls == [("ISIN", ISIN), ("TICKER", TICKER)], f"the ISIN first, then the ticker: {a.calls}"
    assert [(_asked(answer), answer.status) for answer in _answers(events, a.code)] == [(("ISIN", ISIN), RecognizeStatus.NOT_FOUND), (("TICKER", TICKER), RecognizeStatus.FOUND)], f"not found by the ISIN, found by the ticker: {events}"


@pytest.mark.asyncio
async def test_an_enricher_found_by_the_ticker_naming_another_isin_is_a_conflict(lab) -> None:
    a = lab("by_ticker_conflict", accepts=("ISIN", "TICKER"), answer=_found_by_ticker(ISIN=ISIN_OTHER))

    events = await _run({"ISIN": ISIN, "TICKER": TICKER}, [a])

    assert a.calls == [("ISIN", ISIN), ("TICKER", TICKER)], f"barrier: the ISIN first, then the ticker: {a.calls}"
    ticker_answers = [answer for answer in _answers(events, a.code) if _asked(answer) == ("TICKER", TICKER)]
    assert len(ticker_answers) == 1 and ticker_answers[0].status == RecognizeStatus.CONFLICT, f"the ticker's answer is a conflict: {events}"
    assert dict(ticker_answers[0].conflicts) == {"ISIN": ISIN_OTHER}, f"it names the other ISIN: {ticker_answers[0]}"
    assert _learned(events) == [], f"a conflict teaches nothing: {events}"


@pytest.mark.asyncio
async def test_an_error_stops_that_enricher_even_for_a_lei_learned_later(lab) -> None:
    """E raises on the ISIN and would find by anything else; A finds the ISIN and teaches a LEI E accepts. E is never
    asked again: not with the ticker known, not with the LEI learned."""

    def raises_on_isin(binding: EnricherBinding) -> EnricherRecognition:
        if binding.identifier_type == "ISIN":
            raise RuntimeError("lab source down")
        return EnricherRecognition(found=True, name=f"Lab E {binding.identifier}")

    e = lab("error_stops", accepts=("ISIN", "LEI", "TICKER"), answer=raises_on_isin)
    a = lab("error_stops_teacher", accepts=("ISIN",), answer=found(LEI=LEI))

    events = await _run({"ISIN": ISIN, "TICKER": TICKER}, [e, a])

    assert _learned(events) == [IdentifierLearned(identifier_type="LEI", identifier=LEI, source=a.code)], f"barrier: the LEI is learned from A: {events}"
    assert [(_asked(answer), answer.status) for answer in _answers(events, e.code)] == [(("ISIN", ISIN), RecognizeStatus.ERROR)], f"one error answer from E: {events}"
    assert e.calls == [("ISIN", ISIN)], f"an error stops the enricher: no ticker, no learned LEI: {e.calls}"


@pytest.mark.asyncio
async def test_an_enricher_found_is_not_asked_again_with_a_learned_identifier(lab) -> None:
    """A accepts the ISIN and the LEI, finds the ISIN and names the LEI: the LEI is learned, but A is not asked again."""
    a = lab("found_once_a", accepts=("ISIN", "LEI"), answer=found(LEI=LEI))

    events = await _run({"ISIN": ISIN}, [a])

    assert _learned(events) == [IdentifierLearned(identifier_type="LEI", identifier=LEI, source=a.code)], f"barrier: the LEI is learned: {events}"
    assert a.calls == [("ISIN", ISIN)], f"an enricher found is not asked again: {a.calls}"
    assert len(_answers(events, a.code)) == 1, f"one answer from A: {events}"


@pytest.mark.asyncio
async def test_an_enricher_not_found_with_the_isin_is_asked_again_with_the_learned_lei(lab) -> None:
    a = lab("again_a", accepts=("ISIN",), answer=found(LEI=LEI))
    c = lab("again_c", accepts=("ISIN", "LEI"), answer=lambda binding: EnricherRecognition(found=binding.identifier_type == "LEI", name="Lab C" if binding.identifier_type == "LEI" else None))

    events = await _run({"ISIN": ISIN}, [a, c])

    assert sorted(c.calls) == [("ISIN", ISIN), ("LEI", LEI)], f"C asked with the ISIN, then with the learned LEI, once each: {c.calls}"
    c_answers = {_asked(answer): answer.status for answer in _answers(events, c.code)}
    assert c_answers == {("ISIN", ISIN): RecognizeStatus.NOT_FOUND, ("LEI", LEI): RecognizeStatus.FOUND}, f"not found with the ISIN, found with the LEI: {events}"
    lei_answer = next(answer for answer in _answers(events, c.code) if _asked(answer) == ("LEI", LEI))
    assert events.index(_learned(events)[0]) < events.index(lei_answer), f"the LEI is learned before C's answer with it: {events}"


@pytest.mark.asyncio
async def test_a_plugin_that_raises_is_an_error_and_the_others_still_answer(lab) -> None:
    def raises(binding: EnricherBinding) -> EnricherRecognition:
        raise RuntimeError(f"lab source down for {binding.identifier}")

    broken = lab("error_broken", accepts=("ISIN",), answer=raises)
    healthy = lab("error_healthy", accepts=("ISIN",), answer=found())

    events = await _run({"ISIN": ISIN}, [broken, healthy])

    broken_answers = _answers(events, broken.code)
    assert len(broken_answers) == 1 and broken_answers[0].status == RecognizeStatus.ERROR, f"a raising plugin is an error answer: {events}"
    assert broken_answers[0].error and f"lab source down for {ISIN}" in broken_answers[0].error, f"the error carries the message: {broken_answers[0]}"
    assert [answer.status for answer in _answers(events, healthy.code)] == [RecognizeStatus.FOUND], f"the other enricher still answers: {events}"


# =============================================================================
# 3. Order of arrival (round 38)
# =============================================================================


@pytest.mark.asyncio
async def test_answers_come_out_as_they_complete_and_default_order_keeps_that_arrival(lab) -> None:
    """A and B, same degree, A first by code and in ``plugins``. Each is held inside ``recognize`` on its own event.
    Both are asked at once; B is released first and its answer comes out first, then A's. ``default_order`` by code
    says A, B; with the found order it says B, A."""
    print_section("recognize: answers in order of arrival (round 38)")
    started = {"a": threading.Event(), "b": threading.Event()}
    release = {"a": threading.Event(), "b": threading.Event()}

    def held(key: str) -> Answer:
        def answer(binding: EnricherBinding) -> EnricherRecognition:
            started[key].set()
            if not release[key].wait(DEADLINE):
                raise TimeoutError(f"lab {key} was never released")
            return EnricherRecognition(found=True, name=f"Lab {key} {binding.identifier}")

        return answer

    a = lab("arrival_a", accepts=("ISIN",), answer=held("a"))
    b = lab("arrival_b", accepts=("ISIN",), answer=held("b"))
    stream = recognize_cascade(AssetType.ETF, {"ISIN": ISIN}, plugins=[a.plugin, b.plugin])
    first = asyncio.ensure_future(anext(stream))
    both = asyncio.ensure_future(asyncio.to_thread(lambda: started["a"].wait(DEADLINE) and started["b"].wait(DEADLINE)))
    try:
        await asyncio.wait({first, both}, timeout=DEADLINE, return_when=asyncio.FIRST_COMPLETED)
        if first.done():
            raise AssertionError(f"an answer came out before any enricher was released: {first.result()}")  # .result() raises the cascade's own failure
        assert await asyncio.wait_for(both, DEADLINE), f"A and B must be asked at once, each in its own worker thread: started {[key for key, event in started.items() if event.is_set()]}"

        release["b"].set()
        early = await asyncio.wait_for(first, DEADLINE)
        assert isinstance(early, Recognized) and early.code == b.code and early.status == RecognizeStatus.FOUND, f"B, released first, answers first: {early}"

        release["a"].set()
        late = await asyncio.wait_for(anext(stream), DEADLINE)
        assert isinstance(late, Recognized) and late.code == a.code and late.status == RecognizeStatus.FOUND, f"then A: {late}"
        rest = await asyncio.wait_for(_drain(stream), DEADLINE)
        assert [event for event in rest if isinstance(event, Recognized)] == [], f"no other answer: {rest}"
    finally:
        for event in (*started.values(), *release.values()):
            event.set()
        for task in (first, both):
            if not task.done():
                task.cancel()
        await asyncio.gather(first, both, return_exceptions=True)
        await stream.aclose()

    found_order = [early.code, late.code]
    assert _mine(bindings.default_order(AssetType.ETF), [a.code, b.code]) == [a.code, b.code], "barrier: by code alone the order is A, B"
    assert _mine(bindings.default_order(AssetType.ETF, found_order=found_order), [a.code, b.code]) == [b.code, a.code], "the found order keeps the arrival: B, A"
    print_success("B answered first and leads the default order")


async def _drain(stream: Any) -> list[Event]:
    return [event async for event in stream]


# =============================================================================
# 4. The real test enricher
# =============================================================================


def _mockenrich(monkeypatch: pytest.MonkeyPatch) -> EnricherPlugin:
    _test_mode(monkeypatch)
    plugin = EnricherRegistry.get_plugin_instance(MOCK_CODE)
    assert isinstance(plugin, EnricherPlugin), f"barrier: {MOCK_CODE} is served in test mode"
    return plugin


@pytest.mark.asyncio
async def test_mockenrich_finds_an_isin_and_the_lei_it_brings_is_learned(monkeypatch) -> None:
    from backend.app.services.enricher_providers.mockenrich.plugin import lei_of  # noqa: PLC0415 — the plugin's own rule, read in the test body

    mock = _mockenrich(monkeypatch)

    events = await _run({"ISIN": ISIN}, [mock])

    answers = _answers(events, MOCK_CODE)
    assert len(answers) == 1, f"one answer: mockenrich found is not asked again with the LEI: {events}"
    answer = answers[0]
    assert answer.status == RecognizeStatus.FOUND and _asked(answer) == ("ISIN", ISIN), f"mockenrich finds the ISIN: {answer}"
    assert answer.name == f"Mock {ISIN}" and answer.page_url == mock.page_url(EnricherBinding(identifier_type="ISIN", identifier=ISIN)), f"its name and page: {answer}"
    assert dict(answer.identifiers) == {"LEI": lei_of(ISIN)} and dict(answer.conflicts) == {} and answer.error is None, f"it brings the LEI: {answer}"
    assert _learned(events) == [IdentifierLearned(identifier_type="LEI", identifier=lei_of(ISIN), source=MOCK_CODE)], f"the LEI is learned from mockenrich: {events}"


@pytest.mark.asyncio
async def test_mockenrich_does_not_find_an_unknown_isin_and_nothing_is_learned(monkeypatch) -> None:
    from backend.app.services.enricher_providers.mockenrich.plugin import UNKNOWN_PREFIX  # noqa: PLC0415 — the plugin's own rule, read in the test body

    mock = _mockenrich(monkeypatch)
    unknown = f"{UNKNOWN_PREFIX}RECOG01"

    events = await _run({"ISIN": unknown}, [mock])

    assert [(_asked(answer), answer.status) for answer in _answers(events, MOCK_CODE)] == [(("ISIN", unknown), RecognizeStatus.NOT_FOUND)], f"not found: {events}"
    assert _learned(events) == [], f"nothing learned: {events}"


# =============================================================================
# 5. Seeds (ENR-2): the asset's price assignment starts the cascade
# =============================================================================

SEED_TICKER = "LABSEED.MI"


def _seed(code: str, kind: str, identifier: str, **params: Any) -> Seed:
    return Seed(code=code, binding=EnricherBinding(identifier_type=kind, identifier=identifier, params=dict(params)))


@pytest.mark.asyncio
async def test_a_seed_of_the_same_code_is_that_enrichers_first_call_with_its_declared_params(lab) -> None:
    """The seed's identifier is a type the enricher accepts: it is asked with it first, though the ISIN is stronger,
    with the parameters its ``params_schema`` declares and the undeclared one dropped; the answer's binding carries them."""
    a = lab("seed_first", accepts=("ISIN", "TICKER"), answer=found(), params=("mic",))

    events = await _run({"ISIN": ISIN}, [a], seeds=[_seed(a.code, "TICKER", SEED_TICKER, mic="XMIL", undeclared="x")])

    assert a.calls == [("TICKER", SEED_TICKER)], f"the seed is the first call, and it finds: {a.calls}"
    assert a.bindings[0].params == {"mic": "XMIL"}, f"declared params kept, undeclared dropped: {a.bindings[0].params}"
    answers = _answers(events, a.code)
    assert len(answers) == 1 and answers[0].status == RecognizeStatus.FOUND, f"barrier: A finds with the seed: {events}"
    assert _asked(answers[0]) == ("TICKER", SEED_TICKER) and dict(answers[0].binding.params) == {"mic": "XMIL"}, f"the answer's binding carries the seed params: {answers[0]}"


@pytest.mark.asyncio
async def test_a_seed_param_the_enricher_does_not_declare_is_dropped(lab) -> None:
    a = lab("seed_undeclared", accepts=("TICKER",), answer=found())

    events = await _run({}, [a], seeds=[_seed(a.code, "TICKER", SEED_TICKER, mic="XMIL")])

    assert a.calls == [("TICKER", SEED_TICKER)] and a.bindings[0].params == {}, f"no declared param, none passed: {a.bindings}"
    assert dict(_answers(events, a.code)[0].binding.params) == {}, f"the answer carries none: {events}"


@pytest.mark.asyncio
async def test_after_a_seed_not_found_the_enricher_goes_on_with_the_identifiers_known_without_repeating_the_seed(lab) -> None:
    a = lab("seed_then", accepts=("ISIN", "TICKER"), answer=not_found(), params=("mic",))

    events = await _run({"ISIN": ISIN}, [a], seeds=[_seed(a.code, "TICKER", SEED_TICKER, mic="XMIL")])

    assert a.calls == [("TICKER", SEED_TICKER), ("ISIN", ISIN)], f"the seed first, then the ISIN, the seed's ticker not asked twice: {a.calls}"
    assert a.bindings[1].params == {}, f"the later call is the plain one: {a.bindings[1]}"
    assert [answer.status for answer in _answers(events, a.code)] == [RecognizeStatus.NOT_FOUND, RecognizeStatus.NOT_FOUND], f"two clean not found: {events}"


@pytest.mark.asyncio
async def test_a_seed_identifier_joins_the_cascade_for_other_enrichers(lab) -> None:
    """A is the seed's code and accepts only the ISIN: its seed (a TICKER) is no binding for it, but the ticker is
    known now and another enricher accepting TICKER is asked with it."""
    a = lab("seed_join_a", accepts=("ISIN",), answer=not_found())
    t = lab("seed_join_t", accepts=("TICKER",), answer=found())

    events = await _run({"ISIN": ISIN}, [a, t], seeds=[_seed(a.code, "TICKER", SEED_TICKER)])

    assert a.calls == [("ISIN", ISIN)], f"A does not accept the seed's type: it is asked as before: {a.calls}"
    assert t.calls == [("TICKER", SEED_TICKER)], f"T is asked with the seed's ticker: {t.calls}"
    assert [answer.status for answer in _answers(events, t.code)] == [RecognizeStatus.FOUND], f"barrier: T answers: {events}"


@pytest.mark.asyncio
async def test_a_seed_of_a_code_with_no_covering_enricher_still_feeds_its_identifier(lab) -> None:
    t = lab("seed_nocover_t", accepts=("TICKER",), answer=found())
    other = lab("seed_nocover_stock", accepts=("TICKER",), answer=found(), covers=(AssetType.STOCK,))

    events = await _run({}, [t, other], seeds=[_seed(other.code, "TICKER", SEED_TICKER), _seed("lab_recog_nobody", "TICKER", "OTHER.X")])

    assert other.calls == [], f"the seed's enricher does not cover the type: never asked: {other.calls}"
    assert t.calls and t.calls[0] in {("TICKER", SEED_TICKER), ("TICKER", "OTHER.X")} and len(_answers(events, t.code)) == 1, f"T is asked with a seed's ticker: {t.calls}"


@pytest.mark.asyncio
async def test_a_seed_ticker_is_tried_before_the_assets_ticker_which_is_still_tried_after_a_not_found(lab) -> None:
    """R6: the seed ``SWDA.MI`` replaces the asset's ``SWDA``, which goes last, for the seed's enricher and for the
    others."""
    seeded = lab("seed_r6_a", accepts=("TICKER",), answer=not_found())
    other = lab("seed_r6_b", accepts=("TICKER",), answer=not_found())

    await _run({"TICKER": TICKER}, [seeded, other], seeds=[_seed(seeded.code, "TICKER", SEED_TICKER)])

    assert seeded.calls == [("TICKER", SEED_TICKER), ("TICKER", TICKER)], f"the seed's enricher: seed first, the asset's ticker after: {seeded.calls}"
    assert other.calls == [("TICKER", SEED_TICKER), ("TICKER", TICKER)], f"another enricher too: {other.calls}"


@pytest.mark.asyncio
async def test_a_seed_ticker_that_finds_leaves_the_assets_ticker_unasked(lab) -> None:
    a = lab("seed_r6_found", accepts=("TICKER",), answer=found())

    await _run({"TICKER": TICKER}, [a], seeds=[_seed(a.code, "TICKER", SEED_TICKER)])

    assert a.calls == [("TICKER", SEED_TICKER)], f"found with the seed: the asset's ticker is never asked: {a.calls}"


@pytest.mark.asyncio
async def test_a_seed_isin_different_from_the_assets_is_a_conflict_first_and_its_enricher_is_never_called(lab) -> None:
    a = lab("seed_conf_a", accepts=("ISIN",), answer=found(), params=("mic",))
    b = lab("seed_conf_b", accepts=("ISIN",), answer=not_found())

    events = await _run({"ISIN": ISIN}, [a, b], seeds=[_seed(a.code, "ISIN", ISIN_OTHER, mic="XMIL")])

    first = events[0]
    assert isinstance(first, Recognized) and first.code == a.code and first.status == RecognizeStatus.CONFLICT, f"the conflict comes first, for A: {events}"
    assert dict(first.conflicts) == {"ISIN": ISIN_OTHER}, f"it names the seed's ISIN: {first}"
    assert a.calls == [] and len(_answers(events, a.code)) == 1, f"A is never called, and answers only the conflict: {a.calls}"
    assert b.calls == [("ISIN", ISIN)], f"the seed's ISIN joins nothing: B is asked with the asset's: {b.calls}"
    assert _learned(events) == [], f"nothing learned: {events}"


@pytest.mark.asyncio
async def test_a_seed_isin_on_an_asset_without_isin_is_no_conflict_and_joins_the_cascade(lab) -> None:
    a = lab("seed_noisin_a", accepts=("ISIN", "TICKER"), answer=found(), params=("mic",))
    b = lab("seed_noisin_b", accepts=("ISIN",), answer=found())

    events = await _run({"TICKER": TICKER}, [a, b], seeds=[_seed(a.code, "ISIN", ISIN, mic="XMIL")])

    assert all(not (isinstance(event, Recognized) and event.status == RecognizeStatus.CONFLICT) for event in events), f"no ISIN to differ from: no conflict: {events}"
    assert a.calls == [("ISIN", ISIN)] and a.bindings[0].params == {"mic": "XMIL"}, f"the seed's plugin is asked with the seed binding: {a.calls} {a.bindings}"
    assert b.calls == [("ISIN", ISIN)] and b.bindings[0].params == {}, f"another plugin accepting ISIN is asked with the seed's ISIN: {b.calls}"


@pytest.mark.asyncio
async def test_a_seed_isin_equal_to_the_assets_is_no_conflict(lab) -> None:
    a = lab("seed_same_isin", accepts=("ISIN",), answer=found(), params=("mic",))

    events = await _run({"ISIN": ISIN}, [a], seeds=[_seed(a.code, "ISIN", ISIN, mic="XMIL")])

    assert [answer.status for answer in _answers(events, a.code)] == [RecognizeStatus.FOUND], f"a plain found: {events}"
    assert a.calls == [("ISIN", ISIN)] and a.bindings[0].params == {"mic": "XMIL"}, f"asked once, with the seed's params: {a.calls} {a.bindings}"


@pytest.mark.asyncio
async def test_a_strong_seed_conflict_of_a_code_with_no_covering_enricher_says_nothing_and_joins_nothing(lab) -> None:
    b = lab("seed_conf_nobody_b", accepts=("ISIN",), answer=not_found())

    events = await _run({"ISIN": ISIN}, [b], seeds=[_seed("lab_recog_nobody", "ISIN", ISIN_OTHER)])

    assert [(_asked(answer), answer.status) for answer in _answers(events, b.code)] == [(("ISIN", ISIN), RecognizeStatus.NOT_FOUND)], f"only the asset's ISIN is asked: {events}"
    assert all(not (isinstance(event, Recognized) and event.status == RecognizeStatus.CONFLICT) for event in events), f"no conflict without an enricher to carry it: {events}"


@pytest.mark.asyncio
async def test_a_seed_alone_without_identifiers_starts_the_cascade(lab) -> None:
    a = lab("seed_alone", accepts=("TICKER",), answer=found())

    events = await _run({}, [a], seeds=[_seed(a.code, "TICKER", SEED_TICKER)])

    assert a.calls == [("TICKER", SEED_TICKER)] and [answer.status for answer in _answers(events, a.code)] == [RecognizeStatus.FOUND], f"the seed alone asks: {a.calls}"


# =============================================================================
# 6. The request schema with seeds (ENR-2)
# =============================================================================


def _request(**fields: Any) -> FAEnricherRecognizeRequest:
    return FAEnricherRecognizeRequest.model_validate({"asset_type": "ETF", **fields})


GOOD_SEED = {"code": "yfinance", "identifier_type": "TICKER", "identifier": "SWDA.MI", "params": {"mic": "XMIL"}}


def test_a_request_with_seeds_is_accepted_and_keeps_them() -> None:
    request = _request(identifiers={"ISIN": ISIN}, seeds=[GOOD_SEED])
    assert len(request.seeds) == 1 and request.seeds[0].params == {"mic": "XMIL"} and request.seeds[0].code == "yfinance", f"the seed is kept: {request.seeds}"
    assert _request(identifiers={"ISIN": ISIN}).seeds == [], "no seeds by default"
    assert _request(identifiers={"ISIN": ISIN}, seeds=[{**GOOD_SEED, "params": None} | {"params": {}}]).seeds[0].params == {}, "empty params"


def test_a_request_with_only_seeds_is_accepted() -> None:
    assert _request(seeds=[GOOD_SEED]).identifiers == {}, "seeds alone, no identifiers"
    assert _request(identifiers={}, seeds=[GOOD_SEED]).seeds, "empty identifiers with a seed"


@pytest.mark.parametrize("fields", [{}, {"identifiers": {}}, {"identifiers": {"ISIN": "  "}}, {"identifiers": {}, "seeds": []}], ids=["nothing", "empty", "blank", "empty-seeds"])
def test_a_request_with_neither_identifiers_nor_seeds_is_refused(fields) -> None:
    with pytest.raises(ValidationError):
        _request(**fields)


@pytest.mark.parametrize(
    "seed",
    [
        {**GOOD_SEED, "extra": 1},
        {**GOOD_SEED, "identifier": ""},
        {**GOOD_SEED, "identifier": "x" * 257},
        {**GOOD_SEED, "identifier_type": ""},
        {**GOOD_SEED, "identifier_type": "T" * 33},
        {**GOOD_SEED, "code": "BAD CODE!"},
        {**GOOD_SEED, "code": "9lives"[:1]},
        {**GOOD_SEED, "code": ""},
        {k: v for k, v in GOOD_SEED.items() if k != "code"},
    ],
    ids=["extra-key", "empty-identifier", "long-identifier", "empty-type", "long-type", "bad-code", "digit-code", "empty-code", "no-code"],
)
def test_a_malformed_seed_is_refused(seed) -> None:
    with pytest.raises(ValidationError):
        _request(identifiers={"ISIN": ISIN}, seeds=[seed])


def test_a_code_with_a_valid_substring_is_refused() -> None:
    with pytest.raises(ValidationError):
        _request(identifiers={"ISIN": ISIN}, seeds=[{**GOOD_SEED, "code": "Bad Code!"}])


def test_more_than_eight_seeds_are_refused() -> None:
    _request(seeds=[GOOD_SEED] * 8)
    with pytest.raises(ValidationError):
        _request(seeds=[GOOD_SEED] * 9)


def test_a_recognition_carries_params_empty_by_default() -> None:
    assert FAEnricherRecognition(code="x", identifier_type="ISIN", identifier=ISIN, status="found").params == {}
    assert FAEnricherRecognition(code="x", identifier_type="ISIN", identifier=ISIN, status="found", params={"mic": "XMIL"}).params == {"mic": "XMIL"}
