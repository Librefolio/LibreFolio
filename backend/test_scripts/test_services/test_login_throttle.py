"""``backend.app.services.accounts.login_throttle``: a limit on failed sign-ins (release 1.3, workstream A, lot A8a — F15, decision D-A5 and point 4 of 14/10).

The sign-in counts its failures per identifier and per client address, in a sliding window of 15 minutes, and stops
looking at passwords once either count is full. The contract pinned here (C1, with the switch of C3 as the throttle
reads it; the switch itself and its configuration check are pinned in ``test_accounts_checks.py``):

1. ``LOGIN_BY_IDENTIFIER = SlidingWindowLimiter(10, 15 * 60)`` and ``LOGIN_BY_ADDRESS = SlidingWindowLimiter(50, 15 * 60)``
   at module level, read by the functions at call time.
2. ``identifier_key(identifier)``: stripped, A–Z folded and nothing else (decision P18, the rule of ``email_fold``):
   ``" Alice "``, ``"ALICE"`` and ``"alice"`` share one key; ``"Émile"`` and ``"émile"`` do not, nor ``"Straße"`` and
   ``"STRASSE"``, which ``str.casefold`` would merge (E's «forgot password» limit does; this one keeps P18). The
   identifier's limiter is keyed by exactly ``identifier_key(identifier)``, in every function.
3. ``refusal(identifier, address) -> RateDecision | None``: ``None`` while both limits allow one more failure, otherwise
   the refusing decision (``allowed`` False, ``remaining`` 0); when both refuse, ``retry_after`` is the longer of the two
   waits. It only looks: no call ever counts. Without an address only the identifier's limit applies; an address counts
   under ``client_rate_key(address)`` (workstream H): an IPv6 client by its /64.
4. ``record_failure(identifier, address)``: one failure in each limit, the address's only with an address. A failure
   while a limit refuses is not counted there: knocking never moves the unlock. Whether it counts in the other limit
   is left unpinned: at the API a refused attempt never reaches the password check, so it records no failure at all.
5. ``record_success(identifier)``: forgets the identifier's failures, never the address's.
6. ``LIBREFOLIO_LOGIN_LIMIT=off`` (any case, spaces around): ``refusal()`` is ``None`` whatever happened and
   ``record_failure()`` records nothing, so once the limit is back on, nothing done while it was off counts. Failures
   recorded before a switch-off are not cleared by it: they expire with their window, and that is left unpinned.

Points 2, 4 and 6 follow the owner's answers of 17/10 (6, 5 and 3).

The scenes, on an injected clock: ten failures refuse the identifier, from any address; nine, a success, then ten more
refuse only after those ten; knocking on a refused identifier or from a refused address leaves the wait shrinking with
the clock and the unlock where the refusal announced it; after the window the identifier is allowed again and counts
from zero; fifty failures from one address over fifty identifiers refuse a new identifier there, and nowhere else.

Harness: each test gets two limiters of its own, with the contract's limits, on one fake clock (``Limits``), and its
first line puts them in the module with ``monkeypatch.setattr`` (``Limits.throttle()``): no test counts in, or is counted
by, the process's own limiters, and nothing waits for time to pass — the test sets ``clock.now``. An autouse fixture
removes any ``LIBREFOLIO_LOGIN_LIMIT`` the lane inherited; a test sets its own with ``monkeypatch``. The identifier's
limit is read under ``identifier_key(identifier)``, the address's under ``client_rate_key(address)``.

Pure: no database, no server, no network, nothing written.

Red until lot A8a: ``login_throttle`` does not exist. Each test imports it in its own body (``importlib``, through
``_throttle_module()``), so each fails on its own with «red until A8a». The one guard, the address keys these scenes
rely on, is green today and must stay green.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from types import ModuleType

import pytest

from backend.app.services.platform.client_address import client_rate_key
from backend.app.utils.runtime.rate_window import RateDecision, SlidingWindowLimiter
from backend.test_scripts.test_utils import print_section, print_success

THROTTLE_MODULE = "backend.app.services.accounts.login_throttle"
#: The names lot A8a adds in ``login_throttle``.
THROTTLE_NAMES = ("LOGIN_BY_IDENTIFIER", "LOGIN_BY_ADDRESS", "identifier_key", "refusal", "record_failure", "record_success")
LOGIN_LIMIT_VARIABLE = "LIBREFOLIO_LOGIN_LIMIT"

#: The contract's limits: 10 failures per identifier and 50 per client address, in any 15 minutes.
IDENTIFIER_LIMIT = 10
ADDRESS_LIMIT = 50
WINDOW_SECONDS = 15 * 60
FULL_WAIT = float(WINDOW_SECONDS)
#: The fake clock's start: the first failure of most scenes.
START = 1_000.0

#: Documentation addresses (RFC 5737 and RFC 3849).
ADDRESS = "203.0.113.5"
OTHER_ADDRESS = "198.51.100.7"
#: Fifty addresses of one IPv6 /64, a fifty-first of the same /64, and one of the next /64.
SAME_64 = [f"2001:db8:1:2::{k + 1:x}" for k in range(ADDRESS_LIMIT)]
SAME_64_NEWCOMER = "2001:db8:1:2:ffff:ffff:ffff:fffe"
NEXT_64 = "2001:db8:1:3::1"


class FakeClock:
    """A clock that moves only when the test sets it: ``clock.now = …``."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


def _module_or_red(name: str) -> ModuleType:
    """The module ``name``; when it does not exist, the test fails as a red of lot A8a. A module that exists and cannot be imported raises as it is."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name != name:
            raise
        pytest.fail(f"red until A8a: {name} does not exist", pytrace=False)


def _throttle_module() -> ModuleType:
    """``login_throttle`` holding every name of C1, or a red of lot A8a naming what is missing."""
    module = _module_or_red(THROTTLE_MODULE)
    missing = [name for name in THROTTLE_NAMES if not hasattr(module, name)]
    if missing:
        pytest.fail(f"red until A8a: {THROTTLE_MODULE} has no {', '.join(missing)}", pytrace=False)
    return module


@dataclass
class Limits:
    """Two limiters of one test, with the contract's limits on one fake clock; ``throttle()`` puts them in the module."""

    monkeypatch: pytest.MonkeyPatch
    clock: FakeClock
    by_identifier: SlidingWindowLimiter
    by_address: SlidingWindowLimiter

    def throttle(self) -> ModuleType:
        """``login_throttle`` with these limiters in place of its own until the test ends — red until A8a."""
        module = _throttle_module()
        self.monkeypatch.setattr(module, "LOGIN_BY_IDENTIFIER", self.by_identifier)
        self.monkeypatch.setattr(module, "LOGIN_BY_ADDRESS", self.by_address)
        return module


def _fresh_limits(monkeypatch: pytest.MonkeyPatch) -> Limits:
    """Ten per identifier and fifty per address in 900 s, both on a new fake clock at ``START``."""
    clock = FakeClock()
    return Limits(monkeypatch, clock, SlidingWindowLimiter(IDENTIFIER_LIMIT, WINDOW_SECONDS, clock=clock), SlidingWindowLimiter(ADDRESS_LIMIT, WINDOW_SECONDS, clock=clock))


@pytest.fixture
def limits(monkeypatch: pytest.MonkeyPatch) -> Limits:
    return _fresh_limits(monkeypatch)


@pytest.fixture(autouse=True)
def _no_inherited_login_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any ``LIBREFOLIO_LOGIN_LIMIT`` the lane inherited is removed: the limit is on unless a test turns it off."""
    monkeypatch.delenv(LOGIN_LIMIT_VARIABLE, raising=False)


def _set_login_limit(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """``LIBREFOLIO_LOGIN_LIMIT=value``, or unset for ``None``."""
    if value is None:
        monkeypatch.delenv(LOGIN_LIMIT_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(LOGIN_LIMIT_VARIABLE, value)


def _fail_as(throttle: ModuleType, limits: Limits, identifier: str, address: str | None, count: int, *, first_at: float = START, step: float = 0.0) -> None:
    """``count`` failures of ``identifier`` from ``address``, the first at ``first_at``, then one every ``step`` seconds."""
    for k in range(count):
        limits.clock.now = first_at + k * step
        throttle.record_failure(identifier, address)


def _fail_from(throttle: ModuleType, limits: Limits, address: str | None, count: int, *, first_at: float = START, step: float = 0.0, prefix: str = "user") -> None:
    """``count`` failures from ``address``, one for each identifier ``{prefix}-0``, ``{prefix}-1``…, timed as ``_fail_as``: no identifier nears its own limit."""
    for k in range(count):
        limits.clock.now = first_at + k * step
        throttle.record_failure(f"{prefix}-{k}", address)


def _assert_refused(decision: object, retry_after: float, scene: str) -> None:
    """``decision`` is a refusal: a ``RateDecision`` allowing nothing, with nothing remaining, ``retry_after`` seconds to wait."""
    assert isinstance(decision, RateDecision), f"{scene}: refusal() must return the refusing RateDecision, not {decision!r}"
    assert (decision.allowed, decision.remaining, decision.retry_after) == (False, 0, retry_after), f"{scene}: expected a refusal for {retry_after} s, got {decision}"


# =============================================================================
# THE LIMITERS AND THE KEY OF AN IDENTIFIER (contracts 1 and 2)
# =============================================================================


# red until A8a
def test_the_module_ships_ten_per_identifier_and_fifty_per_address_in_fifteen_minutes() -> None:
    """LT-001 — contract 1: as the module ships them (this test installs nothing), ``LOGIN_BY_IDENTIFIER`` is a ``SlidingWindowLimiter`` of 10 in 900 s and ``LOGIN_BY_ADDRESS`` another one, of 50 in 900 s."""
    print_section("LT-001: the shipped limiters")
    throttle = _throttle_module()

    by_identifier, by_address = throttle.LOGIN_BY_IDENTIFIER, throttle.LOGIN_BY_ADDRESS

    assert isinstance(by_identifier, SlidingWindowLimiter) and isinstance(by_address, SlidingWindowLimiter), f"two SlidingWindowLimiter expected: {by_identifier!r}, {by_address!r}"
    assert by_identifier is not by_address, "one limiter for both counts: an address's failures would lock identifiers, and an identifier's an address"
    assert (by_identifier.limit, by_identifier.window_seconds) == (IDENTIFIER_LIMIT, WINDOW_SECONDS), f"LOGIN_BY_IDENTIFIER allows {by_identifier.limit} in {by_identifier.window_seconds} s"
    assert (by_address.limit, by_address.window_seconds) == (ADDRESS_LIMIT, WINDOW_SECONDS), f"LOGIN_BY_ADDRESS allows {by_address.limit} in {by_address.window_seconds} s"
    print_success("10 per identifier, 50 per address, in 15 minutes")


IDENTIFIER_KEYS = [
    pytest.param("alice", "alice", id="lower"),
    pytest.param("ALICE", "alice", id="upper"),
    pytest.param(" Alice ", "alice", id="spaces-around"),
    pytest.param("\tAlice\n", "alice", id="tab-and-newline-around"),
    pytest.param("Alice@Example.COM", "alice@example.com", id="an-email-address"),
    pytest.param("Émile", "Émile", id="a-non-ascii-capital-stays"),
    pytest.param("ÉMILE", "Émile", id="only-a-to-z-folds"),
    pytest.param("émile", "émile", id="non-ascii-lower"),
    pytest.param("Straße", "straße", id="sharp-s-stays"),
    pytest.param("STRASSE", "strasse", id="double-s"),
]


# red until A8a
@pytest.mark.parametrize(("identifier", "key"), IDENTIFIER_KEYS)
def test_identifier_key_strips_and_folds_a_to_z_and_nothing_else(identifier: str, key: str) -> None:
    """LT-002 — contract 2: ``identifier_key`` strips what surrounds the identifier and folds A–Z to a–z, nothing else (P18): É stays É, ß stays ß."""
    print_section(f"LT-002: identifier_key({identifier!r})")
    throttle = _throttle_module()

    result = throttle.identifier_key(identifier)

    assert type(result) is str and result == key, f"identifier_key({identifier!r}) is {result!r}, expected {key!r}: stripped, A–Z folded and nothing else"
    print_success(f"{identifier!r} → {key!r}")


# red until A8a
def test_the_spellings_of_one_identifier_share_a_key_and_other_letters_do_not() -> None:
    """LT-003 — contract 2: ``" Alice "``, ``"ALICE"`` and ``"alice"`` share one key; ``"Émile"`` and ``"émile"`` do not (``str.lower`` would merge them), nor ``"Straße"`` and ``"STRASSE"`` (``str.casefold`` would)."""
    print_section("LT-003: shared and distinct keys")
    throttle = _throttle_module()

    shared = {throttle.identifier_key(spelling) for spelling in (" Alice ", "ALICE", "alice")}

    assert len(shared) == 1, f"one identifier in three spellings must count as one: {shared}"
    assert throttle.identifier_key("Émile") != throttle.identifier_key("émile"), "Émile and émile share a key: only A–Z folds (P18)"
    assert throttle.identifier_key("Straße") != throttle.identifier_key("STRASSE"), "Straße and STRASSE share a key: that is a casefold, not the A–Z fold of P18"
    print_success(f"one key for Alice: {shared}")


# =============================================================================
# REFUSAL: TEN PER IDENTIFIER, FIFTY PER ADDRESS, ONLY LOOKING (contracts 2 and 3)
# =============================================================================


# red until A8a
def test_ten_failures_of_an_identifier_refuse_it_from_any_address(limits: Limits) -> None:
    """LT-004 — contract 3: nine failures of ``alice``, ten seconds apart, leave her allowed after each; the tenth, at ``START + 90``, refuses her — from her address, from another one, without one — for 810 s, until her first failure leaves the window. Bob, from her address, is not refused."""
    print_section("LT-004: ten failures refuse the identifier")
    throttle = limits.throttle()
    assert throttle.refusal("alice", ADDRESS) is None, "barrier: nothing recorded, nobody refused"

    for failure in range(1, IDENTIFIER_LIMIT):
        limits.clock.now = START + 10 * (failure - 1)
        throttle.record_failure("alice", ADDRESS)
        assert throttle.refusal("alice", ADDRESS) is None, f"after {failure} failure(s) alice must still be allowed: the limit is {IDENTIFIER_LIMIT}"
    limits.clock.now = START + 90
    throttle.record_failure("alice", ADDRESS)

    for address in (ADDRESS, OTHER_ADDRESS, None):
        _assert_refused(throttle.refusal("alice", address), 810.0, f"ten failures of alice, asked from {address!r}")
    assert throttle.refusal("bob", ADDRESS) is None, "bob shares alice's address: her ten failures are not the address's fifty"
    print_success("refused for 810 s, from any address")


# red until A8a
def test_refusal_only_looks_and_never_counts(limits: Limits) -> None:
    """LT-005 — contract 3: a hundred and fifty calls of ``refusal()`` — three times the address's limit — record nothing in either limit, and ``alice`` still needs ten failures to be refused; asked again and again once refused, her count stays ten and her wait the same."""
    print_section("LT-005: refusal() only looks")
    throttle = limits.throttle()

    for _ in range(3 * ADDRESS_LIMIT):
        assert throttle.refusal("alice", ADDRESS) is None, "nothing recorded: nobody refused"
    assert (len(limits.by_identifier), len(limits.by_address)) == (0, 0), f"refusal() recorded {len(limits.by_identifier)} identifier key(s) and {len(limits.by_address)} address key(s)"

    _fail_as(throttle, limits, "alice", ADDRESS, IDENTIFIER_LIMIT - 1)
    assert throttle.refusal("alice", ADDRESS) is None, "nine failures: allowed, so the looks before them counted nothing"
    throttle.record_failure("alice", ADDRESS)
    for _ in range(3 * ADDRESS_LIMIT):
        _assert_refused(throttle.refusal("alice", ADDRESS), FULL_WAIT, "ten failures at one instant, asked again and again")
    assert limits.by_identifier.count(throttle.identifier_key("alice")) == IDENTIFIER_LIMIT, "asking while refused counted a failure"
    print_success("150 looks, nothing counted")


# red until A8a
def test_the_identifier_limit_counts_the_failures_from_every_address(limits: Limits) -> None:
    """LT-006 — contract 3: ten failures of ``alice``, each from another address: she is refused from an eleventh address and without one — the count is the identifier's, not the pair's —, while each of those addresses, one failure each, still lets ``bob`` try."""
    print_section("LT-006: one identifier, ten addresses")
    throttle = limits.throttle()
    addresses = [f"192.0.2.{k}" for k in range(1, IDENTIFIER_LIMIT + 1)]

    for address in addresses:
        throttle.record_failure("alice", address)

    for address in (OTHER_ADDRESS, None):
        _assert_refused(throttle.refusal("alice", address), FULL_WAIT, f"ten failures of alice from ten addresses, asked from {address!r}")
    assert [address for address in addresses if throttle.refusal("bob", address) is not None] == [], "an address with one failure refused bob"
    print_success("refused wherever she comes from")


# red until A8a
def test_every_function_keys_the_identifier_by_identifier_key(limits: Limits) -> None:
    """LT-007 — contract 2: ten failures recorded under five spellings of Alice are one key holding ten failures, and refuse a sixth spelling; a success under a seventh forgets them. ``Émile``'s ten failures refuse ``ÉMILE`` (A–Z folded, É kept) and not ``émile``."""
    print_section("LT-007: one key in every function")
    throttle = limits.throttle()
    spellings = [" Alice ", "ALICE", "alice", "\tAlice\n", "aLiCe"]

    for failure in range(IDENTIFIER_LIMIT):
        throttle.record_failure(spellings[failure % len(spellings)], None)

    assert (len(limits.by_identifier), limits.by_identifier.count(throttle.identifier_key("alice"))) == (1, IDENTIFIER_LIMIT), "five spellings of alice must be one key holding her ten failures"
    _assert_refused(throttle.refusal("ALICE ", None), FULL_WAIT, "ten failures under five spellings, asked as 'ALICE '")
    throttle.record_success(" alice")
    assert throttle.refusal("Alice", None) is None, "a success under another spelling must forget alice's failures"

    _fail_as(throttle, limits, "Émile", None, IDENTIFIER_LIMIT)
    _assert_refused(throttle.refusal("ÉMILE", None), FULL_WAIT, "Émile's ten failures, asked as ÉMILE (A–Z folded, É kept)")
    assert throttle.refusal("émile", None) is None, "émile is another identifier than Émile: only A–Z folds (P18)"
    print_success("one identifier, whatever its spelling")


# red until A8a
def test_fifty_failures_from_one_address_refuse_a_new_identifier_there_and_nowhere_else(limits: Limits) -> None:
    """LT-008 — contract 3: fifty identifiers fail once each from one address, a second apart: after forty-nine a newcomer there is allowed, after the fiftieth refused for 851 s (until the first failure leaves the window). The newcomer from another address, or without one, is allowed, and so is each of the fifty from elsewhere."""
    print_section("LT-008: fifty failures from one address")
    throttle = limits.throttle()
    _fail_from(throttle, limits, ADDRESS, ADDRESS_LIMIT - 1, step=1.0)
    assert throttle.refusal("newcomer", ADDRESS) is None, "forty-nine failures from the address: still allowed"

    limits.clock.now = START + ADDRESS_LIMIT - 1
    throttle.record_failure(f"user-{ADDRESS_LIMIT - 1}", ADDRESS)

    _assert_refused(throttle.refusal("newcomer", ADDRESS), 851.0, "fifty failures from the address, a newcomer there")
    assert throttle.refusal("newcomer", OTHER_ADDRESS) is None, "another address is not refused for this one's failures"
    assert throttle.refusal("newcomer", None) is None, "without an address only the identifier's limit applies"
    assert [k for k in range(ADDRESS_LIMIT) if throttle.refusal(f"user-{k}", OTHER_ADDRESS) is not None] == [], "one failure each: none of the fifty is refused from elsewhere"
    print_success("refused there, and only there")


# red until A8a
def test_an_ipv6_client_counts_by_its_64(limits: Limits) -> None:
    """LT-009 — contract 3: fifty failures, each from another address of ``2001:db8:1:2::/64`` and for another identifier, refuse a newcomer from a fifty-first address of that /64; from the next /64 the newcomer is allowed.

    Premise first: workstream H's ``client_rate_key`` gives the fifty-one addresses one key and the next /64 another.
    """
    print_section("LT-009: an IPv6 client by its /64")
    keys = {client_rate_key(address) for address in [*SAME_64, SAME_64_NEWCOMER]}
    assert len(keys) == 1 and client_rate_key(NEXT_64) not in keys, f"premise: one key for the /64 ({keys}), another for the next ({client_rate_key(NEXT_64)!r})"
    throttle = limits.throttle()

    for k, address in enumerate(SAME_64):
        throttle.record_failure(f"user-{k}", address)

    _assert_refused(throttle.refusal("newcomer", SAME_64_NEWCOMER), FULL_WAIT, "fifty failures from fifty addresses of one /64, a newcomer from another address of it")
    assert throttle.refusal("newcomer", NEXT_64) is None, "the next /64 is another client"
    print_success("one /64, one count")


# red until A8a
def test_without_an_address_only_the_identifier_limit_applies(limits: Limits) -> None:
    """LT-010 — contracts 3 and 4: sixty identifiers failing once each without an address record nothing in the address's limit — there is no shared count of «no address» — and refuse no newcomer; an address refused for its fifty failures does not refuse a newcomer who has no address; ``alice``'s own ten failures without an address still refuse her."""
    print_section("LT-010: no address")
    throttle = limits.throttle()

    _fail_from(throttle, limits, None, ADDRESS_LIMIT + 10, prefix="anonymous")
    assert len(limits.by_address) == 0, f"record_failure() without an address counted under {len(limits.by_address)} address key(s)"
    assert throttle.refusal("newcomer", None) is None, "sixty failures without an address are nobody's address"

    _fail_from(throttle, limits, ADDRESS, ADDRESS_LIMIT)
    _assert_refused(throttle.refusal("newcomer", ADDRESS), FULL_WAIT, "barrier: fifty failures from the address")
    assert throttle.refusal("newcomer", None) is None, "without an address the address's limit does not apply"

    _fail_as(throttle, limits, "alice", None, IDENTIFIER_LIMIT)
    _assert_refused(throttle.refusal("alice", None), FULL_WAIT, "alice's ten failures without an address")
    print_success("without an address, the identifier alone counts")


BOTH_REFUSE = [
    pytest.param(300.0, 0.0, 800.0, 500.0, id="the-identifier-waits-longer"),
    pytest.param(0.0, 200.0, 500.0, 700.0, id="the-address-waits-longer"),
]


# red until A8a
@pytest.mark.parametrize(("identifier_at", "address_at", "identifier_wait", "address_wait"), BOTH_REFUSE)
def test_when_both_limits_refuse_the_longer_wait_wins(limits: Limits, identifier_at: float, address_at: float, identifier_wait: float, address_wait: float) -> None:
    """LT-011 — contract 3: ``alice`` fails ten times without an address at ``START + identifier_at``; fifty other identifiers fail once each from one address at ``START + address_at``. At ``START + 400`` each limit alone refuses with its own wait — alice without an address, a newcomer from the address —, and alice from the address waits the longer of the two, whichever limit holds it."""
    print_section(f"LT-011: both refuse, the identifier for {identifier_wait:.0f} s, the address for {address_wait:.0f} s")
    throttle = limits.throttle()
    if identifier_at <= address_at:
        _fail_as(throttle, limits, "alice", None, IDENTIFIER_LIMIT, first_at=START + identifier_at)
        _fail_from(throttle, limits, ADDRESS, ADDRESS_LIMIT, first_at=START + address_at)
    else:
        _fail_from(throttle, limits, ADDRESS, ADDRESS_LIMIT, first_at=START + address_at)
        _fail_as(throttle, limits, "alice", None, IDENTIFIER_LIMIT, first_at=START + identifier_at)
    limits.clock.now = START + 400

    _assert_refused(throttle.refusal("alice", None), identifier_wait, "barrier: alice's own limit alone")
    _assert_refused(throttle.refusal("newcomer", ADDRESS), address_wait, "barrier: the address's limit alone")
    _assert_refused(throttle.refusal("alice", ADDRESS), max(identifier_wait, address_wait), "alice from the address: both refuse, the longer wait wins")
    print_success(f"{max(identifier_wait, address_wait):.0f} s")


# =============================================================================
# THE WINDOW: KNOCKING NEVER MOVES THE UNLOCK, AND THE WINDOW ENDS (contracts 3 and 4)
# =============================================================================


# red until A8a
def test_knocking_on_a_refused_identifier_never_moves_its_unlock(limits: Limits) -> None:
    """LT-012 — contract 4: ten failures of ``alice`` from ``START`` to ``START + 90`` refuse her until ``START + 900``. Eighty more, every ten seconds until ``START + 890``, are not counted: after each, her wait is exactly what is left until ``START + 900``; her count stays ten; at ``START + 900`` she is allowed. Without an address, so her own limit alone is in play."""
    print_section("LT-012: knocking on a refused identifier")
    throttle = limits.throttle()
    _fail_as(throttle, limits, "alice", None, IDENTIFIER_LIMIT, step=10.0)
    unlock = START + WINDOW_SECONDS

    for knock in range(1, 81):
        limits.clock.now = START + 90 + 10 * knock
        throttle.record_failure("alice", None)
        _assert_refused(throttle.refusal("alice", None), unlock - limits.clock.now, f"knock {knock}, at START + {limits.clock.now - START:.0f}")

    assert limits.by_identifier.count(throttle.identifier_key("alice")) == IDENTIFIER_LIMIT, "a failure while refused was counted"
    limits.clock.now = unlock
    assert throttle.refusal("alice", None) is None, "her first failure left the window: alice must be allowed when the refusal said"
    print_success("eighty knocks, the unlock unmoved")


# red until A8a
def test_knocking_from_a_refused_address_never_moves_its_unlock(limits: Limits) -> None:
    """LT-013 — contract 4: fifty identifiers fail once each from one address, a second apart from ``START``: the address is refused until ``START + 900``. Forty-two new identifiers then fail from it every twenty seconds until ``START + 889``, none counted there: after each, a newcomer from the address waits exactly what is left until ``START + 900``; the address's count stays fifty; at ``START + 900`` the newcomer is allowed."""
    print_section("LT-013: knocking from a refused address")
    throttle = limits.throttle()
    _fail_from(throttle, limits, ADDRESS, ADDRESS_LIMIT, step=1.0)
    unlock = START + WINDOW_SECONDS

    for knock in range(1, 43):
        limits.clock.now = START + 49 + 20 * knock
        throttle.record_failure(f"knocker-{knock}", ADDRESS)
        _assert_refused(throttle.refusal("newcomer", ADDRESS), unlock - limits.clock.now, f"knock {knock}, at START + {limits.clock.now - START:.0f}")

    assert limits.by_address.count(client_rate_key(ADDRESS)) == ADDRESS_LIMIT, "a failure from a refused address was counted there"
    limits.clock.now = unlock
    assert throttle.refusal("newcomer", ADDRESS) is None, "the address's first failure left the window: the newcomer must be allowed when the refusal said"
    print_success("forty-two knocks, the unlock unmoved")


# red until A8a
def test_after_the_window_the_identifier_is_allowed_again_from_zero(limits: Limits) -> None:
    """LT-014 — contract 3: ten failures at ``START`` still refuse ``alice`` one second before the window ends (1 s to wait); at ``START + 900`` she is allowed again, and counts from zero: nine new failures leave her allowed, the tenth refuses her for the full window."""
    print_section("LT-014: the window ends")
    throttle = limits.throttle()
    _fail_as(throttle, limits, "alice", ADDRESS, IDENTIFIER_LIMIT)

    limits.clock.now = START + WINDOW_SECONDS - 1
    _assert_refused(throttle.refusal("alice", ADDRESS), 1.0, "one second before the window ends")
    limits.clock.now = START + WINDOW_SECONDS
    assert throttle.refusal("alice", ADDRESS) is None, "the window has passed: alice must be allowed again"

    _fail_as(throttle, limits, "alice", ADDRESS, IDENTIFIER_LIMIT - 1, first_at=START + WINDOW_SECONDS)
    assert throttle.refusal("alice", ADDRESS) is None, "nine failures in the new window: allowed"
    throttle.record_failure("alice", ADDRESS)
    _assert_refused(throttle.refusal("alice", ADDRESS), FULL_WAIT, "ten failures in the new window")
    print_success("allowed again after 15 minutes, counting from zero")


# =============================================================================
# RECORD_SUCCESS (contract 5)
# =============================================================================


# red until A8a
def test_a_success_forgets_the_identifiers_failures(limits: Limits) -> None:
    """LT-015 — contract 5: nine failures, a success, then ten more failures: allowed after each of the first nine new ones — eighteen in all, past the limit had the success forgotten nothing —, refused after the tenth, for the full window."""
    print_section("LT-015: a success starts the identifier from zero")
    throttle = limits.throttle()
    _fail_as(throttle, limits, "alice", ADDRESS, IDENTIFIER_LIMIT - 1)
    assert throttle.refusal("alice", ADDRESS) is None, "barrier: nine failures, still allowed"

    throttle.record_success("alice")

    for failure in range(1, IDENTIFIER_LIMIT):
        throttle.record_failure("alice", ADDRESS)
        assert throttle.refusal("alice", ADDRESS) is None, f"{failure} failure(s) since the success, {IDENTIFIER_LIMIT - 1 + failure} in all: the success must have forgotten the nine before it"
    throttle.record_failure("alice", ADDRESS)
    _assert_refused(throttle.refusal("alice", ADDRESS), FULL_WAIT, "ten failures since the success")
    print_success("refused only after ten new failures")


# red until A8a
def test_a_success_never_forgets_the_addresss_failures(limits: Limits) -> None:
    """LT-016 — contract 5: forty identifiers fail once each from one address at ``START``, then ``alice`` ten times there at ``START + 100``. At ``START + 100`` alice is refused by her own count (900 s) and a newcomer there by the address's (800 s). Her success forgets her failures — she is no longer refused without an address — but not the address's: from it, she and the newcomer still wait 800 s."""
    print_section("LT-016: a success leaves the address's count alone")
    throttle = limits.throttle()
    _fail_from(throttle, limits, ADDRESS, ADDRESS_LIMIT - IDENTIFIER_LIMIT)
    _fail_as(throttle, limits, "alice", ADDRESS, IDENTIFIER_LIMIT, first_at=START + 100)
    _assert_refused(throttle.refusal("alice", None), 900.0, "barrier: alice's ten failures")
    _assert_refused(throttle.refusal("newcomer", ADDRESS), 800.0, "barrier: fifty failures from the address")

    throttle.record_success("alice")

    assert throttle.refusal("alice", None) is None, "a success must forget the identifier's failures"
    _assert_refused(throttle.refusal("alice", ADDRESS), 800.0, "alice after her success, from the address of fifty failures")
    _assert_refused(throttle.refusal("newcomer", ADDRESS), 800.0, "a newcomer from that address, after alice's success")
    print_success("the identifier forgotten, the address not")


# =============================================================================
# THE MODULE'S LIMITERS, READ AT CALL TIME (contract 1)
# =============================================================================


# red until A8a
def test_the_functions_read_the_module_limiters_at_call_time(limits: Limits) -> None:
    """LT-017 — contract 1: once the module's two limiters are replaced, ``record_failure`` counts in the replacements — the identifier under ``identifier_key``, the address under ``client_rate_key`` — and not in the limiters the module shipped with; ``refusal`` reads the replacement (filled directly, it refuses); ``record_success`` empties it."""
    print_section("LT-017: the limiters read at call time")
    shipped = _throttle_module()
    identifier, address = "lt-017 Call-Time", "192.0.2.117"
    key, address_key = shipped.identifier_key(identifier), client_rate_key(address)
    shipped_limiters = (shipped.LOGIN_BY_IDENTIFIER, shipped.LOGIN_BY_ADDRESS)
    shipped_counts = (shipped_limiters[0].count(key), shipped_limiters[1].count(address_key))
    throttle = limits.throttle()

    throttle.record_failure(identifier, address)

    assert (limits.by_identifier.count(key), limits.by_address.count(address_key)) == (1, 1), "record_failure() must count in the limiters the module holds now"
    assert (shipped_limiters[0].count(key), shipped_limiters[1].count(address_key)) == shipped_counts, "record_failure() counted in the limiters the module shipped with"
    for _ in range(IDENTIFIER_LIMIT - 1):
        limits.by_identifier.hit(key)
    _assert_refused(throttle.refusal(identifier, None), FULL_WAIT, "the replacement, filled directly")
    throttle.record_success(identifier)
    assert limits.by_identifier.count(key) == 0, "record_success() must empty the replacement"
    print_success("the module's limiters as they are at each call")


# =============================================================================
# LIBREFOLIO_LOGIN_LIMIT=off (contract 6)
# =============================================================================


# red until A8a
@pytest.mark.parametrize("spelling", ["off", "OFF", " Off "], ids=["off", "OFF", "spaces-around-Off"])
def test_off_refuses_nobody_whatever_happened(limits: Limits, monkeypatch: pytest.MonkeyPatch, spelling: str) -> None:
    """LT-018 — contract 6: both limits refusing — ``alice``'s ten failures, her address's fifty —, ``LIBREFOLIO_LOGIN_LIMIT`` set to ``off`` in any case, spaces around, makes ``refusal()`` ``None`` for alice from that address, alice without an address and a newcomer from it."""
    print_section(f"LT-018: LIBREFOLIO_LOGIN_LIMIT={spelling!r}")
    throttle = limits.throttle()
    _fail_from(throttle, limits, ADDRESS, ADDRESS_LIMIT - IDENTIFIER_LIMIT)
    _fail_as(throttle, limits, "alice", ADDRESS, IDENTIFIER_LIMIT)
    _assert_refused(throttle.refusal("alice", ADDRESS), FULL_WAIT, "barrier: the limit on, both counts full")

    monkeypatch.setenv(LOGIN_LIMIT_VARIABLE, spelling)

    asked = [("alice", ADDRESS), ("alice", None), ("newcomer", ADDRESS)]
    refused = [(identifier, address, decision) for identifier, address in asked if (decision := throttle.refusal(identifier, address)) is not None]
    assert refused == [], f"LIBREFOLIO_LOGIN_LIMIT={spelling!r}: the limit is off, nobody is refused: {refused}"
    print_success("nobody refused")


# red until A8a
@pytest.mark.parametrize("back_on", [None, "on"], ids=["unset", "on"])
def test_failures_while_off_record_nothing_and_count_for_nothing_once_on_again(limits: Limits, monkeypatch: pytest.MonkeyPatch, back_on: str | None) -> None:
    """LT-019 — contract 6: while ``LIBREFOLIO_LOGIN_LIMIT=off``, twenty failures of ``alice`` and fifty of other identifiers from her address record nothing in either limit, and nobody is refused. Back on — the variable unset, or ``on`` —, alice from that address is allowed, nine new failures leave her allowed and the tenth refuses her: what happened while off counts for nothing, and the limit works again. No failure comes before the switch-off here: what becomes of those (they expire with their window) is left unpinned."""
    print_section(f"LT-019: off, then {back_on or 'unset'}")
    throttle = limits.throttle()
    monkeypatch.setenv(LOGIN_LIMIT_VARIABLE, "off")

    _fail_as(throttle, limits, "alice", ADDRESS, 2 * IDENTIFIER_LIMIT)
    _fail_from(throttle, limits, ADDRESS, ADDRESS_LIMIT)

    assert (len(limits.by_identifier), len(limits.by_address)) == (0, 0), f"LIBREFOLIO_LOGIN_LIMIT=off: record_failure() recorded {len(limits.by_identifier)} identifier key(s) and {len(limits.by_address)} address key(s)"
    assert throttle.refusal("alice", ADDRESS) is None, "off: nobody refused"

    _set_login_limit(monkeypatch, back_on)

    assert throttle.refusal("alice", ADDRESS) is None, "back on: what happened while off must not count"
    _fail_as(throttle, limits, "alice", ADDRESS, IDENTIFIER_LIMIT - 1)
    assert throttle.refusal("alice", ADDRESS) is None, "back on: nine failures, still allowed"
    throttle.record_failure("alice", ADDRESS)
    _assert_refused(throttle.refusal("alice", ADDRESS), FULL_WAIT, "back on: the tenth failure")
    print_success("off counted nothing; back on, the limit works")


# =============================================================================
# GUARD: THE PREMISES OF THE ADDRESS SCENES
# =============================================================================


# guard
def test_guard_the_address_keys_these_scenes_rely_on() -> None:
    """LT-020 — guard, green today and to stay green: the premises of the address scenes, from workstream H's ``client_rate_key``. An IPv4 address is its own key; two addresses of one IPv6 /64 share a key and the next /64 has another; without an address there is no key, so no shared count of «no address» can exist."""
    print_section("LT-020: the address keys (guard)")

    assert (client_rate_key(ADDRESS), client_rate_key(OTHER_ADDRESS)) == (ADDRESS, OTHER_ADDRESS), "an IPv4 address must be its own key"
    assert client_rate_key(SAME_64[0]) == client_rate_key(SAME_64_NEWCOMER) != client_rate_key(NEXT_64), "one IPv6 /64, one key; the next /64, another"
    assert client_rate_key(None) is None, "no address, no key"
    print_success("IPv4 as is, IPv6 by its /64, nothing without an address")
