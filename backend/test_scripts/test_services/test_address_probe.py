"""
The address probe — release 1.3, workstream A, lot A6a (plan phase01Accounts, A6.1 «Verifica dell'indirizzo», D-A3).

Under test: ``backend/app/services/accounts/address_probe.py``. When an administrator edits the server address in the
Invite dialog, the browser checks that THIS instance answers there: its own instance issues a nonce, the browser sends
it to the edited address, and only the instance that issued it answers ``match``. A stable instance id readable from any
origin was rejected (any web page could fingerprint a LibreFolio on its visitor's LAN); the nonce is a signed,
short-lived, stateless challenge::

    nonce = base64url without padding ( rand16 ‖ expiry ‖ HMAC-SHA256(derive_key(PROBE_PURPOSE), rand16 ‖ expiry) )

``rand16`` is 16 random bytes, ``expiry`` the expiry instant in whole unix seconds on 8 bytes big-endian, the MAC 32
bytes: 56 bytes, 75 characters. ``derive_key`` is the derivation of the instance key (workstream H,
``services/platform/instance_key.py``). The contract:

(a) ``PROBE_PURPOSE == "accounts.address-probe.v1"``, ``PROBE_TTL_SECONDS == 120``.
(b) ``issue_probe_nonce(*, now=None) -> (nonce, expires_at)``. Issued at a whole second ``T``, the nonce has exactly the
    layout above — its MAC recomputed here, independently of the module, with ``derive_key("accounts.address-probe.v1")``
    under the instance key of the test —, its expiry is ``T + 120`` and ``expires_at`` the aware UTC datetime of that
    instant. Without ``now``, the wall clock (``time.time()``). Every nonce is new: issued at the same instant, no two
    nonces and no two random parts are equal. The key is asked of ``derive_key(PROBE_PURPOSE)`` at every call, by the
    issue and by the check (a spy), and never kept: the instance key may change under a running process.
(c) ``verify_probe_nonce(nonce, *, now=None) -> bool``: ``True`` for a nonce of this instance while ``expiry >= now`` —
    at its issue, and still at its expiry second exactly —, ``False`` half a second later and after. ``now`` is compared
    as it is, not rounded to its second. Without ``now``, the wall clock: a nonce issued ten minutes ago is refused, one
    issued now is accepted. A nonce made here with the documented layout and the probe key of the instance is accepted:
    the format is the contract in both directions.
(d) ``False`` for everything else, and never an exception: every single bit flipped in each part, an expiry moved later
    under the original MAC, truncated, extended, padding added, characters outside base64url, whitespace, non-ASCII,
    empty, longer than 256 characters, the standard base64 alphabet (``+`` and ``/``), a non-canonical spelling of an
    issued nonce (its last character's two spare bits set: the same 56 bytes, but not the text the instance issued), 56
    random bytes, a MAC under the key of another purpose or under the instance key itself.
(e) Another instance: a nonce issued under key A is refused under key B and accepted under A again, both ways, with the
    key configured (``LIBREFOLIO_INSTANCE_KEY``) or generated in each instance's own data directory.
(f) Constant time: the check asks ``hmac.compare_digest`` (a spy), and the verdict on the MAC is its own: a comparator
    that says no refuses a valid nonce, one that says yes lets an altered MAC through — while the expiry is still checked.
(g) An unusable instance key never raises: ``derive_key`` raising ``InstanceKeyError``, a configured key too short, a key
    file that does not exist — ``False``.

Pure: no database, no server, no network. Every test starts as instance A: ``LIBREFOLIO_INSTANCE_KEY`` set with
``monkeypatch``, and the data directory in ``tmp_path`` (test mode), so that nothing can ever reach the lane's key file;
the generated keys of (e) and the key file of (g) live there too. ``derive_key`` and ``hmac.compare_digest`` are
replaced, where a test spies on them, both in their own module and under any name ``address_probe`` binds to them.

Red until A6a: ``backend.app.services.accounts.address_probe`` does not exist (``ModuleNotFoundError`` at collection).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from backend.app.services.accounts import address_probe
from backend.app.services.platform import instance_key
from backend.app.services.platform.instance_key import INSTANCE_KEY_FILE, InstanceKeyError
from backend.test_scripts.test_utils import print_section, print_success

KEY_VARIABLE = "LIBREFOLIO_INSTANCE_KEY"
KEY_FILE_VARIABLE = "LIBREFOLIO_INSTANCE_KEY_FILE"
#: The configured keys of instance A (every test starts as A) and of instance B: at least 32 characters (instance_key.py).
INSTANCE_KEYS = {"A": "address-probe-instance-key-A-0123456789abcdef", "B": "address-probe-instance-key-B-0123456789abcdef"}

#: The contract, written out here: a change in the module is caught, never followed.
PURPOSE = "accounts.address-probe.v1"
TTL_SECONDS = 120
RANDOM_BYTES = 16
EXPIRY_BYTES = 8
MAC_BYTES = 32
RAW_LENGTH = RANDOM_BYTES + EXPIRY_BYTES + MAC_BYTES
#: 56 bytes in base64url without padding.
NONCE_LENGTH = 75
#: Longer than this is refused outright; any length but NONCE_LENGTH is refused anyway.
MAX_LENGTH = 256
BASE64URL_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
NONCE_SHAPE = re.compile(r"[A-Za-z0-9_-]{75}")
#: The bits of each part in the 56 bytes, from bit 0, the high bit of the first byte: (first, end).
PART_BITS = {
    "random": (0, RANDOM_BYTES * 8),
    "expiry": (RANDOM_BYTES * 8, (RANDOM_BYTES + EXPIRY_BYTES) * 8),
    "mac": ((RANDOM_BYTES + EXPIRY_BYTES) * 8, RAW_LENGTH * 8),
}

#: The issue instant of most tests, a whole second (2027-01-15T08:00:00Z): the expiry is exactly NOW + 120.
NOW = 1_800_000_000
EXPIRY = NOW + TTL_SECONDS

#: The originals, taken before any test replaces them: expected values are computed with these, never with a spy.
REAL_DERIVE_KEY = instance_key.derive_key
REAL_COMPARE_DIGEST = hmac.compare_digest


# =============================================================================
# The instances, and the nonce taken apart
# =============================================================================


def _become(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, source: str) -> None:
    """This process becomes instance ``name``: a data directory of its own and, for ``configured``, its key in
    ``LIBREFOLIO_INSTANCE_KEY``; for ``generated``, no configured key, so that its first use generates the key file."""
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / f"instance-{name.lower()}"))
    if source == "configured":
        monkeypatch.setenv(KEY_VARIABLE, INSTANCE_KEYS[name])
    else:
        monkeypatch.delenv(KEY_VARIABLE, raising=False)


@pytest.fixture(autouse=True)
def instance_a(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Every test starts as instance A: its key configured, and a data directory of this test only.

    A configured key never reads the data directory; it is set all the same, so that a fallback to a generated key could
    only ever land in ``tmp_path``, never in the lane's ``secrets/``.
    """
    monkeypatch.delenv(KEY_FILE_VARIABLE, raising=False)
    monkeypatch.delenv("LIBREFOLIO_DATA_DIR", raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    _become(monkeypatch, tmp_path, "A", "configured")


def _b64(raw: bytes) -> str:
    """base64url without padding, as a nonce is written."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    """The bytes of a base64url text without padding (Python's lenient decoder: for this test's own values only)."""
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


@dataclass(frozen=True)
class Parts:
    """The three parts of a nonce."""

    random: bytes
    expiry: int
    mac: bytes


def _parts(nonce: object) -> Parts:
    """The parts of a nonce, its shape checked first: 75 base64url characters, 56 bytes."""
    assert isinstance(nonce, str) and NONCE_SHAPE.fullmatch(nonce), f"a nonce is {NONCE_LENGTH} base64url characters without padding, not {nonce!r}"
    raw = _unb64(nonce)
    assert len(raw) == RAW_LENGTH, f"a nonce holds {RAW_LENGTH} bytes, not {len(raw)}"
    return Parts(random=raw[:RANDOM_BYTES], expiry=int.from_bytes(raw[RANDOM_BYTES : RANDOM_BYTES + EXPIRY_BYTES], "big"), mac=raw[RANDOM_BYTES + EXPIRY_BYTES :])


def _probe_key() -> bytes:
    """The MAC key the contract names, under the current instance key: ``derive_key("accounts.address-probe.v1")``."""
    return REAL_DERIVE_KEY(PURPOSE)


def _mac(key: bytes, random_part: bytes, expiry: int) -> bytes:
    """HMAC-SHA256 of rand16 ‖ expiry_be8 under ``key``."""
    return hmac.new(key, random_part + expiry.to_bytes(EXPIRY_BYTES, "big"), hashlib.sha256).digest()


def _craft(random_part: bytes, expiry: int, key: bytes | None = None) -> str:
    """A nonce made here with the documented layout, under ``key``: by default the probe key of the current instance."""
    mac = _mac(_probe_key() if key is None else key, random_part, expiry)
    return _b64(random_part + expiry.to_bytes(EXPIRY_BYTES, "big") + mac)


def _with_bit_flipped(nonce: str, bit: int) -> str:
    """The nonce with one bit of its 56 bytes flipped (bit 0 is the high bit of the first byte), spelled canonically."""
    raw = bytearray(_unb64(nonce))
    raw[bit // 8] ^= 0x80 >> (bit % 8)
    return _b64(bytes(raw))


def _issue(now: float = NOW) -> tuple[str, datetime]:
    """A nonce of the current instance issued at ``now`` (a whole second by default), and its expires_at."""
    return address_probe.issue_probe_nonce(now=now)


def _verdict(candidate: str, now: float = NOW) -> object:
    """What verify_probe_nonce answers, or the exception it raised: it must never raise, so an exception is a wrong answer."""
    try:
        return address_probe.verify_probe_nonce(candidate, now=now)
    except Exception as exc:  # reported beside the wrong booleans, with its type
        return exc


def _not_refused(candidates: dict[str, str], now: float = NOW) -> dict[str, object]:
    """The candidates verify_probe_nonce does not answer exactly ``False``, with what it answered instead."""
    wrong: dict[str, object] = {}
    for label, candidate in candidates.items():
        verdict = _verdict(candidate, now)
        if verdict is not False:
            wrong[label] = verdict
    return wrong


# =============================================================================
# Spies and stand-ins
# =============================================================================


def _replace_derive_key(monkeypatch: pytest.MonkeyPatch, replacement: Callable[..., bytes]) -> None:
    """``replacement`` wherever the module may read ``derive_key``: H's module, and any name of address_probe bound to it."""
    monkeypatch.setattr(instance_key, "derive_key", replacement)
    for name, value in list(vars(address_probe).items()):
        if value is REAL_DERIVE_KEY:
            monkeypatch.setattr(address_probe, name, replacement)


def _replace_compare_digest(monkeypatch: pytest.MonkeyPatch, replacement: Callable[[object, object], bool]) -> None:
    """``replacement`` wherever the module may read ``hmac.compare_digest``: the ``hmac`` module, ``secrets`` (which
    re-exports the very same function), and any name of address_probe bound to it."""
    monkeypatch.setattr(hmac, "compare_digest", replacement)
    monkeypatch.setattr(secrets, "compare_digest", replacement)
    for name, value in list(vars(address_probe).items()):
        if value is REAL_COMPARE_DIGEST:
            monkeypatch.setattr(address_probe, name, replacement)


class _DeriveKeySpy:
    """derive_key, recording the (purpose, length) of every call."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, int]] = []

    def __call__(self, purpose: str, length: int = 32) -> bytes:
        self.asked.append((purpose, length))
        return REAL_DERIVE_KEY(purpose, length)


class _CompareDigestSpy:
    """hmac.compare_digest, counting its calls."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, first: object, second: object) -> bool:
        self.calls += 1
        return REAL_COMPARE_DIGEST(first, second)


def _unusable_derive_key(*_args: object, **_kwargs: object) -> bytes:
    """derive_key as it fails on a key it cannot use."""
    raise InstanceKeyError("the instance key cannot be used (raised by this test)")


def _break_derive_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """derive_key itself raises InstanceKeyError."""
    _replace_derive_key(monkeypatch, _unusable_derive_key)


def _configure_a_key_too_short(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """LIBREFOLIO_INSTANCE_KEY shorter than the 32 characters an instance key needs."""
    monkeypatch.setenv(KEY_VARIABLE, "too-short-for-an-instance-key")


def _configure_a_missing_key_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No key in LIBREFOLIO_INSTANCE_KEY, and LIBREFOLIO_INSTANCE_KEY_FILE naming a file that does not exist."""
    monkeypatch.delenv(KEY_VARIABLE, raising=False)
    monkeypatch.setenv(KEY_FILE_VARIABLE, str(tmp_path / "no-such-instance.key"))


# =============================================================================
# (a) The constants
# =============================================================================


def test_purpose_and_lifetime_are_those_of_the_contract():
    """AP-S-01 (a): the derivation purpose names the use and its version; a nonce lives two minutes."""
    print_section("AP-S-01: PROBE_PURPOSE and PROBE_TTL_SECONDS")
    assert address_probe.PROBE_PURPOSE == PURPOSE, f"PROBE_PURPOSE is {address_probe.PROBE_PURPOSE!r}, the contract says {PURPOSE!r}"
    assert address_probe.PROBE_TTL_SECONDS == TTL_SECONDS, f"PROBE_TTL_SECONDS is {address_probe.PROBE_TTL_SECONDS!r}, the contract says {TTL_SECONDS}"
    print_success(f"{PURPOSE}, {TTL_SECONDS} s")


# =============================================================================
# (b) issue_probe_nonce
# =============================================================================


def test_issue_gives_the_documented_layout_under_the_probe_key():
    """AP-S-02 (b): issued at a whole second T, the nonce is rand16 ‖ (T + 120) ‖ HMAC-SHA256(derive_key(purpose), …),
    its MAC recomputed here; expires_at is the aware UTC datetime of T + 120."""
    print_section("AP-S-02: the nonce's layout, its MAC and expires_at")
    issued = address_probe.issue_probe_nonce(now=NOW)
    assert isinstance(issued, tuple) and len(issued) == 2, f"issue_probe_nonce returns (nonce, expires_at), not {issued!r}"
    nonce, expires_at = issued
    parts = _parts(nonce)
    assert parts.expiry == EXPIRY, f"the expiry part is the issue instant plus {TTL_SECONDS} s, in whole unix seconds big-endian: {parts.expiry}, expected {EXPIRY}"
    assert parts.mac == _mac(_probe_key(), parts.random, parts.expiry), f"the MAC part must be HMAC-SHA256(derive_key({PURPOSE!r}), rand16 ‖ expiry_be8)"
    assert isinstance(expires_at, datetime) and expires_at.utcoffset() == timedelta(0), f"expires_at is an aware UTC datetime, not {expires_at!r}"
    assert expires_at == datetime.fromtimestamp(EXPIRY, tz=UTC), f"expires_at must be the expiry instant {datetime.fromtimestamp(EXPIRY, tz=UTC).isoformat()}, not {expires_at.isoformat()}"
    print_success(f"{nonce[:12]}… expires at {expires_at.isoformat()}")


def test_issue_without_now_reads_the_wall_clock():
    """AP-S-03 (b): without ``now`` the issue instant is time.time(); expires_at and the nonce's expiry are one instant."""
    print_section("AP-S-03: issue_probe_nonce() on the wall clock")
    before = time.time()
    nonce, expires_at = address_probe.issue_probe_nonce()
    after = time.time()
    expiry = _parts(nonce).expiry
    assert before + TTL_SECONDS - 1 < expiry < after + TTL_SECONDS + 1, f"issued between {before:.3f} and {after:.3f}, the expiry must be {TTL_SECONDS} s later, to the second: {expiry}"
    assert isinstance(expires_at, datetime) and expires_at.utcoffset() == timedelta(0), f"expires_at is an aware UTC datetime, not {expires_at!r}"
    assert abs(expires_at.timestamp() - expiry) < 1, f"expires_at ({expires_at.isoformat()}) and the expiry the nonce carries ({expiry}) must be the same instant, to the second"
    print_success(f"expiry {expiry}, expires_at {expires_at.isoformat()}")


def test_every_nonce_is_new():
    """AP-S-04 (b): issued at the same instant, no two nonces and no two random parts are equal."""
    print_section("AP-S-04: every nonce is new")
    nonces = [_issue()[0] for _ in range(64)]
    assert len(set(nonces)) == len(nonces), f"{len(nonces) - len(set(nonces))} repeated nonce(s) among {len(nonces)} issued at the same instant"
    randoms = {_parts(nonce).random for nonce in nonces}
    assert len(randoms) == len(nonces), "the random part must be drawn anew for every nonce"
    print_success(f"{len(nonces)} nonces issued at one instant, all different")


def test_the_key_is_asked_of_derive_key_at_every_call(monkeypatch):
    """AP-S-05 (b): the issue and the check take their key from derive_key(PROBE_PURPOSE), 32 bytes, at every call."""
    print_section("AP-S-05: derive_key(PROBE_PURPOSE) at every call")
    spy = _DeriveKeySpy()
    _replace_derive_key(monkeypatch, spy)
    nonce, _ = _issue()
    assert spy.asked and set(spy.asked) == {(PURPOSE, 32)}, f"issue_probe_nonce must ask derive_key({PURPOSE!r}) for a 32-byte key (its default length), and nothing else: {spy.asked}"
    spy.asked.clear()
    assert _verdict(nonce) is True, "Barrier: the nonce just issued is accepted"
    assert spy.asked and set(spy.asked) == {(PURPOSE, 32)}, f"verify_probe_nonce must ask derive_key({PURPOSE!r}) for its key, and nothing else: {spy.asked}"
    spy.asked.clear()
    _issue()
    assert spy.asked, "a second issue asks derive_key again: the derived key is never kept, the instance key may change under a running process"
    print_success("derive_key asked at every call, for the probe purpose only")


# =============================================================================
# (c) verify_probe_nonce: the nonces it accepts
# =============================================================================


@pytest.mark.parametrize(
    ("seconds_after_issue", "accepted"),
    [
        pytest.param(0, True, id="at-the-issue"),
        pytest.param(TTL_SECONDS - 1, True, id="one-second-before-the-expiry"),
        pytest.param(TTL_SECONDS, True, id="exactly-at-the-expiry"),
        pytest.param(TTL_SECONDS + 0.5, False, id="half-a-second-after-the-expiry"),
        pytest.param(TTL_SECONDS + 1, False, id="one-second-after-the-expiry"),
        pytest.param(24 * 3600, False, id="a-day-later"),
    ],
)
def test_a_nonce_is_valid_while_its_expiry_is_not_past(seconds_after_issue, accepted):
    """AP-S-06 (c): valid while ``expiry >= now``, ``now`` compared as it is, not rounded to its whole second."""
    nonce, _ = _issue()
    checked_at = NOW + seconds_after_issue
    verdict = _verdict(nonce, now=checked_at)
    assert verdict is accepted, f"a nonce expiring at {EXPIRY}, checked at {checked_at}: expected {accepted}, got {verdict!r}"


def test_verify_without_now_reads_the_wall_clock():
    """AP-S-07 (c): without ``now`` the check reads time.time(): issued now, accepted; issued ten minutes ago, refused."""
    print_section("AP-S-07: verify_probe_nonce() on the wall clock")
    fresh, _ = address_probe.issue_probe_nonce(now=time.time())
    stale, _ = address_probe.issue_probe_nonce(now=time.time() - 600)
    assert address_probe.verify_probe_nonce(fresh) is True, "a nonce issued now must be accepted by verify_probe_nonce() on the wall clock"
    assert address_probe.verify_probe_nonce(stale) is False, "a nonce issued ten minutes ago expired eight minutes ago: verify_probe_nonce() on the wall clock must refuse it"
    print_success("fresh accepted, stale refused")


def test_a_nonce_made_with_the_documented_layout_is_accepted():
    """AP-S-08 (c): the layout is the contract both ways: made here under the probe key of the instance, a nonce is
    accepted up to its expiry, and refused after it."""
    print_section("AP-S-08: a nonce made here with the documented layout")
    random_part = bytes(range(RANDOM_BYTES))
    verdict = _verdict(_craft(random_part, EXPIRY))
    assert verdict is True, f"a nonce made as base64url(rand16 ‖ expiry_be8 ‖ HMAC-SHA256(derive_key({PURPOSE!r}), rand16 ‖ expiry_be8)) must be accepted, got {verdict!r}"
    assert _verdict(_craft(random_part, NOW)) is True, "its expiry equal to now: still valid (expiry >= now)"
    assert _verdict(_craft(random_part, NOW - 1)) is False, "its expiry one second before now: expired"
    print_success("accepted up to its expiry, refused after")


# =============================================================================
# (d) verify_probe_nonce: everything else is False, and nothing raises
# =============================================================================


@pytest.mark.parametrize("part", list(PART_BITS))
def test_every_single_bit_flipped_is_refused(part):
    """AP-S-09 (d): any one bit flipped in the random part, in the expiry or in the MAC makes the nonce a forgery."""
    print_section(f"AP-S-09: every single bit of the {part} part flipped")
    nonce, _ = _issue()
    assert _verdict(nonce) is True, "Barrier: the nonce itself is accepted"
    first, end = PART_BITS[part]
    wrong = _not_refused({f"bit {bit}": _with_bit_flipped(nonce, bit) for bit in range(first, end)})
    assert not wrong, f"a nonce with one bit of its {part} part flipped must be refused (False); not refused: {wrong}"
    print_success(f"{end - first} single-bit forgeries of the {part} part refused")


def test_an_expiry_moved_later_is_refused():
    """AP-S-10 (d): what the MAC is for — a captured nonce cannot be kept alive by rewriting its expiry."""
    print_section("AP-S-10: the expiry moved an hour later, under the original MAC")
    nonce, _ = _issue()
    parts = _parts(nonce)
    later = _b64(parts.random + (parts.expiry + 3600).to_bytes(EXPIRY_BYTES, "big") + parts.mac)
    assert _verdict(nonce, now=EXPIRY + 60) is False, "Barrier: a minute after its expiry, the original is refused"
    wrong = _not_refused({"checked at the issue": later}) | _not_refused({"checked once the original has expired": later}, now=EXPIRY + 60)
    assert not wrong, f"the nonce with its expiry moved an hour later, under the original MAC, must be refused: {wrong}"
    print_success("the forged expiry is refused, before and after the real one")


#: Malformed spellings of an issued nonce: none may be accepted, none may raise.
MALFORMED = [
    pytest.param(lambda nonce: "", id="empty"),
    pytest.param(lambda nonce: " " * NONCE_LENGTH, id="75-spaces"),
    pytest.param(lambda nonce: nonce[:-1], id="truncated-by-one"),
    pytest.param(lambda nonce: nonce[:-2], id="truncated-by-two"),
    pytest.param(lambda nonce: nonce[:-4], id="truncated-by-four"),
    pytest.param(lambda nonce: nonce[: NONCE_LENGTH // 2], id="truncated-to-half"),
    pytest.param(lambda nonce: nonce + "A", id="extended-by-one"),
    pytest.param(lambda nonce: nonce + "AA", id="extended-by-two"),
    pytest.param(lambda nonce: nonce + "AAAA", id="extended-by-four"),
    pytest.param(lambda nonce: nonce + nonce, id="doubled"),
    pytest.param(lambda nonce: nonce + "=", id="padding-added"),
    pytest.param(lambda nonce: nonce + "==", id="double-padding-added"),
    pytest.param(lambda nonce: nonce[:37] + "!" + nonce[37:], id="non-base64-character-inserted"),
    pytest.param(lambda nonce: nonce[:37] + "." + nonce[38:], id="non-base64-character-replacing-one"),
    pytest.param(lambda nonce: " " + nonce, id="leading-space"),
    pytest.param(lambda nonce: nonce + "\n", id="trailing-newline"),
    pytest.param(lambda nonce: nonce[:37] + "\t" + nonce[37:], id="tab-inserted"),
    pytest.param(lambda nonce: nonce[:37] + "\x00" + nonce[38:], id="nul-character"),
    pytest.param(lambda nonce: nonce[:37] + "\u00e9" + nonce[38:], id="non-ascii-letter"),
    pytest.param(lambda nonce: nonce[:37] + "\u0663" + nonce[38:], id="non-ascii-digit"),
    pytest.param(lambda nonce: nonce[:37] + "\uff21" + nonce[38:], id="fullwidth-letter"),
    pytest.param(lambda nonce: "\u00e9" * NONCE_LENGTH, id="non-ascii-only"),
    pytest.param(lambda nonce: (nonce * 4)[: MAX_LENGTH + 1], id="257-characters"),
    pytest.param(lambda nonce: nonce * 4, id="300-characters"),
    pytest.param(lambda nonce: "A" * 100_000, id="100000-characters"),
]


@pytest.mark.parametrize("malform", MALFORMED)
def test_a_malformed_nonce_is_refused_without_raising(malform: Callable[[str], str]):
    """AP-S-11 (d): only 75 base64url characters can be a nonce. Python's lenient decoder would read several of these
    (padding, inserted characters, whitespace) as the very bytes of the nonce: the check must not be that lenient."""
    nonce, _ = _issue()
    candidate = malform(nonce)
    assert candidate != nonce, "Barrier: the case changes the nonce"
    verdict = _verdict(candidate)
    assert verdict is False, f"{len(candidate)} characters {candidate[:90]!r}: expected False, got {verdict!r}"


def test_a_non_canonical_spelling_of_an_issued_nonce_is_refused():
    """AP-S-12 (d): the last character carries two spare bits, zero in the nonce issued. With one of them set, Python's
    decoder still reads the same 56 bytes — but that text is not the nonce the instance issued."""
    print_section("AP-S-12: non-canonical spellings of an issued nonce")
    nonce, _ = _issue()
    last = BASE64URL_ALPHABET.index(nonce[-1])
    assert last % 4 == 0, f"Barrier: the nonce is issued in canonical base64url, the two spare bits of its last character zero: {nonce[-1]!r}"
    variants = {f"spare bits {spare:02b}": nonce[:-1] + BASE64URL_ALPHABET[last | spare] for spare in (1, 2, 3)}
    assert all(_unb64(variant) == _unb64(nonce) for variant in variants.values()), "Barrier: Python's lenient decoder reads the same 56 bytes from every variant"
    wrong = _not_refused(variants)
    assert not wrong, f"only the canonical spelling of an issued nonce is accepted; other spellings of the same bytes were not refused: {wrong}"
    print_success("the three non-canonical spellings refused")


def test_the_standard_base64_alphabet_is_refused():
    """AP-S-13 (d): ``+`` and ``/`` belong to base64, not to base64url: the same bytes in the other alphabet are refused."""
    print_section("AP-S-13: the standard base64 alphabet")
    random_part = bytes.fromhex("fbffbf") * 5 + bytes.fromhex("fb")
    nonce = _craft(random_part, EXPIRY)
    assert "-" in nonce and "_" in nonce and _verdict(nonce) is True, f"Barrier: the nonce made here spells '-' and '_', and is accepted: {nonce}"
    standard = nonce.replace("-", "+").replace("_", "/")
    verdict = _verdict(standard)
    assert verdict is False, f"{standard!r}, the same bytes in the standard base64 alphabet: expected False, got {verdict!r}"
    print_success("refused")


def test_random_bytes_of_the_right_length_are_refused():
    """AP-S-14 (d): 56 random bytes in base64url have the shape of a nonce, never its MAC."""
    print_section("AP-S-14: 56 random bytes")
    candidates = {f"random #{index}": _b64(secrets.token_bytes(RAW_LENGTH)) for index in range(32)}
    assert all(NONCE_SHAPE.fullmatch(candidate) for candidate in candidates.values()), "Barrier: every candidate has the shape of a nonce"
    wrong = _not_refused(candidates)
    assert not wrong, f"random bytes in the shape of a nonce must be refused: {wrong}"
    print_success(f"{len(candidates)} random candidates refused")


def test_a_mac_under_another_key_of_this_instance_is_refused():
    """AP-S-15 (d): only the probe key signs a probe: not the key of another purpose, not the instance key itself."""
    print_section("AP-S-15: a MAC under another key of this instance")
    random_part = secrets.token_bytes(RANDOM_BYTES)
    assert _verdict(_craft(random_part, EXPIRY)) is True, "Barrier: under the probe key, the nonce made here is accepted"
    candidates = {
        "derive_key('plugins.settings.v1'), another purpose": _craft(random_part, EXPIRY, REAL_DERIVE_KEY("plugins.settings.v1")),
        "the instance key itself, not derived": _craft(random_part, EXPIRY, INSTANCE_KEYS["A"].encode("utf-8")),
    }
    wrong = _not_refused(candidates)
    assert not wrong, f"a MAC under another key than derive_key({PURPOSE!r}) must be refused: {wrong}"
    print_success("refused")


# =============================================================================
# (e) Another instance
# =============================================================================


@pytest.mark.parametrize("source", ["configured", "generated"])
def test_a_nonce_of_another_instance_is_refused(monkeypatch, tmp_path, source):
    """AP-S-16 (e): the nonce is bound to the instance key — configured, or generated in each instance's data directory."""
    print_section(f"AP-S-16: another instance, {source} key")
    _become(monkeypatch, tmp_path, "A", source)
    nonce_a, _ = _issue()
    _become(monkeypatch, tmp_path, "B", source)
    nonce_b, _ = _issue()
    assert _verdict(nonce_a) is False, f"instance B ({source} key) must refuse a nonce of instance A"
    assert _verdict(nonce_b) is True, f"instance B ({source} key) accepts its own nonce"
    _become(monkeypatch, tmp_path, "A", source)
    assert _verdict(nonce_a) is True, f"instance A ({source} key) accepts its own nonce again: the refusal came from the key, from nothing else"
    assert _verdict(nonce_b) is False, f"instance A ({source} key) must refuse a nonce of instance B"
    if source == "generated":
        key_files = [tmp_path / f"instance-{name}" / INSTANCE_KEY_FILE for name in ("a", "b")]
        assert all(path.is_file() for path in key_files), f"Barrier: each instance generated a key file of its own: {key_files}"
        assert key_files[0].read_bytes() != key_files[1].read_bytes(), "Barrier: the two generated keys differ"
    print_success("each instance accepts its own nonces only")


# =============================================================================
# (f) Constant time
# =============================================================================


def test_the_mac_is_compared_with_hmac_compare_digest(monkeypatch):
    """AP-S-17 (f): the check asks hmac.compare_digest, never ``==`` alone."""
    print_section("AP-S-17: hmac.compare_digest is asked")
    nonce, _ = _issue()
    spy = _CompareDigestSpy()
    _replace_compare_digest(monkeypatch, spy)
    assert _verdict(nonce) is True, "Barrier: the nonce just issued is accepted"
    assert spy.calls, "verify_probe_nonce must compare the MAC with hmac.compare_digest, in constant time"
    print_success(f"hmac.compare_digest asked {spy.calls} time(s)")


def test_the_verdict_on_the_mac_is_the_one_of_compare_digest(monkeypatch):
    """AP-S-18 (f): compare_digest alone judges the MAC: a comparator that says no refuses a valid nonce, one that says
    yes lets an altered MAC through — no other comparison judges it beside. The expiry is checked whatever it says."""
    print_section("AP-S-18: the MAC verdict is compare_digest's")
    nonce, _ = _issue()
    altered = _with_bit_flipped(nonce, RAW_LENGTH * 8 - 1)
    _replace_compare_digest(monkeypatch, lambda first, second: False)
    assert _verdict(nonce) is False, "with a comparator that says no, a valid nonce must be refused: the MAC is judged by hmac.compare_digest"
    _replace_compare_digest(monkeypatch, lambda first, second: True)
    assert _verdict(altered) is True, "with a comparator that says yes, an altered MAC passes: nothing but hmac.compare_digest (no ==) may judge the MAC"
    assert _verdict(nonce, now=EXPIRY + 1) is False, "the expiry is checked whatever the comparator says"
    print_success("the MAC is judged by compare_digest alone; the expiry still checked")


# =============================================================================
# (g) An unusable instance key never raises
# =============================================================================


@pytest.mark.parametrize(
    "break_the_key",
    [
        pytest.param(_break_derive_key, id="derive-key-raises-InstanceKeyError"),
        pytest.param(_configure_a_key_too_short, id="configured-key-too-short"),
        pytest.param(_configure_a_missing_key_file, id="key-file-missing"),
    ],
)
def test_an_unusable_instance_key_refuses_without_raising(monkeypatch, tmp_path, break_the_key):
    """AP-S-19 (g): when the instance key cannot be used, nothing verifies and nothing raises: False."""
    print_section("AP-S-19: an unusable instance key")
    nonce, _ = _issue()
    break_the_key(monkeypatch, tmp_path)
    with pytest.raises(InstanceKeyError):
        instance_key.derive_key(PURPOSE)
    wrong = _not_refused({"the nonce issued before the key broke": nonce, "a text that is no nonce": "not-a-nonce"})
    assert not wrong, f"with an unusable instance key, verify_probe_nonce must answer False and never raise: {wrong}"
    print_success("False, no exception")
