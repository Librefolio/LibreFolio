"""
H-61 checkpoint 2 · level L2 of the hosting panel, signed Ed25519 tickets (LibreFolio 1.3, workstream H, platform): the
configuration of L2 and the verification of one ticket, pure. The contract is H-61 CP2's, §1, and §2 without the ``jti``
registry (``test_hosting_panel_registry.py``); the dependency that uses both, ``panel_access``, is
``test_hosting_panel_access.py``'s.

Under test:

- ``backend/app/config/hosting_panel.py`` (§1, extended), read from the process environment at each call.
  ``panel_public_keys() -> dict[str, Ed25519PublicKey] | None`` from ``LIBREFOLIO_PANEL_PUBLIC_KEYS``, which is not a
  secret and has no ``_FILE``: ``kid:key[,kid:key…]``, the spaces around an entry ignored; a ``kid`` of
  ``[A-Za-z0-9._-]{1,64}``, unique; a ``key`` the raw Ed25519 public key (32 bytes) in base64url without padding, 43
  characters; 1 to 4 entries. Unset or blank: None, L2 off. Anything else: ``HostingPanelConfigError``
  ``PANEL_KEYS_INVALID``, naming the entry by its position and never a key. ``panel_clock_skew_seconds() -> int`` from
  ``LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS``: a whole number from 0 to 300, 60 while unset, anything else
  ``PANEL_CLOCK_SKEW_INVALID``. ``panel_audience() -> str``: the origin of ``public_url()``, ``scheme://host[:port]`` in
  lower case, without the scheme's default port (80, 443) nor a path; keys set but no usable ``LIBREFOLIO_PUBLIC_URL``,
  ``PANEL_AUDIENCE_UNAVAILABLE``.
- ``backend/app/services/platform/hosting_panel/tickets.py`` (§2, new): ``verify_ticket(value, scope, keys, audience,
  skew, now) -> TicketClaims | TicketRefusal``, pure, on PyJWT and ``cryptography``. In order: (1) unverifiable — more
  than 2048 bytes, not a JWS, an ``alg`` other than ``EdDSA``, a ``typ`` other than ``lf-panel+jwt``, a signature that
  does not verify —, a refusal without a ticket code, which the route answers with its scope's own 401; (2) a ``kid`` the
  keys do not hold, ``panel_ticket_unknown_key``; (3) ``jwt.decode`` with the key of the ``kid`` (signature, algorithm,
  audience, the required claims ``exp iat aud jti scope``), the times this module's own on the ``now`` it is given:
  ``exp <= now - skew`` ``panel_ticket_expired``, ``iat > now + skew`` ``panel_ticket_not_yet_valid``, then
  ``panel_ticket_wrong_audience``, ``panel_ticket_wrong_scope``, and ``panel_ticket_invalid`` for a ``jti`` outside its
  rule, a lifetime ``exp - iat`` over 300 s or a required claim missing.

The tests:

- HPT-001..007, ``panel_public_keys()`` (§1): unset or blank, None (001); 1, 2 and 4 entries, spaces around (002); read
  at each call (003); a ``kid`` at the edges of its rule (004); a malformed entry, at position 2 or 3, refused naming its
  position and never a key (005); five entries, a ``kid`` twice (006); no ``_FILE`` (007).
- HPT-008..010, ``panel_clock_skew_seconds()`` (§1): 60 while unset (008); 0, 45 and 300 taken (009); -1, 301, «sixty»
  and «1.5» refused (010).
- HPT-011..012, ``panel_audience()`` (§1): the canonical origin (011); no usable public URL (012).
- HPT-020..033, ``verify_ticket()`` (§2), each case once per scope: accepted, with its claims (020); two keys, each
  ``kid`` with its own key (021); unverifiable, eleven forms (022); 2048 bytes taken, 2049 unverifiable before the ``kid``
  is read (023); an unknown ``kid`` (024); the edges of the tolerance, for a skew of 60, 0 and 300 (025); the clock is
  ``now`` (026); a lifetime of 300 and 301 s (027); another audience (028), none (029); another scope (030); the rule of
  the ``jti`` (031); a required claim missing (032); two defects at once, the verdict of the one checked first (033).
- HPT-040 (§1 with §2): what the three readers give is what ``verify_ticket`` checks a panel's ticket against.

How. Pure: no server, no database, no network, no file outside ``tmp_path``, no clock. The keys are built from fixed
seeds with ``cryptography`` (``Ed25519PrivateKey.from_private_bytes``) — never a real key — and the tickets signed with
PyJWT (``jwt.encode(…, algorithm="EdDSA", headers={"typ": …, "kid": …})``); the forged ones too, through PyJWT's own
``none`` and ``HS256``. ``now`` is fixed at 2 000 000 000 (May 2033), far from the wall clock: a verifier that reads the
wall clock, or lets PyJWT check the times, refuses every good ticket of this file, all issued «in the future». The
variables of L2 are deleted before each test, then set through ``monkeypatch``. Every refusal stands beside a barrier:
the same ticket without its defect is accepted, or each defect of a pair alone gets its own verdict; a message that must
not hold a key is first shown to be the one that names the variable, or the entry's position.

Read here beyond the contract's words, each in one place of this file, so that another choice of the implementation
changes one line:

- ``TicketRefusal.code`` is the ``panel_ticket_*`` code, None for an unverifiable ticket («a refusal without a ticket
  code», TA-T1's brief); ``TicketClaims`` has ``kid``, ``jti``, ``scope``, ``iat`` and ``exp`` (the brief), the times in
  seconds since the epoch (``verdict``, ``claim_fields``).
- ``verify_ticket`` takes the contract's six parameters by name: ``scope`` a ``PanelScope``, ``keys`` a dict as
  ``panel_public_keys()`` returns it, ``now`` whole seconds since the epoch (``judge``).
- The rule of the ``jti``, which the contract does not spell: 16 to 64 characters and no ``/`` (the brief refuses 15,
  65 and a ``/``). Every ``jti`` taken here is lower-case hexadecimal, inside any alphabet such a rule may choose.
- A missing ``aud`` is ``panel_ticket_wrong_audience``, as the brief says, where the contract's «a required claim
  missing» would read ``panel_ticket_invalid``: HPT-029, a test of its own.
- The position of a malformed entry counts from 1 and shows as a number.

Red today: ``config/hosting_panel.py`` gives none of the three readers, and ``tickets.py`` does not exist. HPT-001..012
fail on «H-61 CP2: backend.app.config.hosting_panel gives no panel_public_keys» (``panel_clock_skew_seconds``,
``panel_audience``), HPT-020..033 on «H-61 CP2: backend/app/services/platform/hosting_panel/tickets.py is missing», and
HPT-040 on the first of these, its keys' reader. The file itself collects: it imports only what exists today.
"""

import base64
import hashlib
import importlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from backend.test_scripts.test_utils import print_section, print_success

# =============================================================================
# THE CONTRACT, SPELLED OUT
# =============================================================================

#: The modules of H-61 CP2, imported when a test needs them, and their files for the red message.
HOSTING_CONFIG_MODULE = "backend.app.config.hosting_panel"
TICKETS_MODULE = "backend.app.services.platform.hosting_panel.tickets"
ACCESS_MODULE = "backend.app.services.platform.hosting_panel.access"
_MODULE_FILES = {
    HOSTING_CONFIG_MODULE: "backend/app/config/hosting_panel.py",
    TICKETS_MODULE: "backend/app/services/platform/hosting_panel/tickets.py",
    ACCESS_MODULE: "backend/app/services/platform/hosting_panel/access.py",
}

#: The variables of L2, as .env.example writes them: spelled out here, so that a rename shows.
KEYS_VARIABLE = "LIBREFOLIO_PANEL_PUBLIC_KEYS"
SKEW_VARIABLE = "LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
#: The ``_FILE`` the keys do not have: they are not a secret.
KEYS_FILE_VARIABLE = KEYS_VARIABLE + "_FILE"
#: Every variable the readers could see: none is inherited from the runner's environment.
L2_VARIABLES = (KEYS_VARIABLE, KEYS_FILE_VARIABLE, SKEW_VARIABLE, PUBLIC_URL_VARIABLE)

#: The codes of ``HostingPanelConfigError`` (§1).
KEYS_INVALID = "PANEL_KEYS_INVALID"
SKEW_INVALID = "PANEL_CLOCK_SKEW_INVALID"
AUDIENCE_UNAVAILABLE = "PANEL_AUDIENCE_UNAVAILABLE"
#: The tolerance on a ticket's times while its variable is unset, in seconds.
DEFAULT_SKEW = 60

#: The ticket (§2): its header and its limits.
TICKET_TYP = "lf-panel+jwt"
ALGORITHM = "EdDSA"
MAX_TICKET_BYTES = 2048
MAX_LIFETIME = 300
#: The codes of the refusals of a ticket whose signature the keys verify, or whose kid they do not hold (§2).
UNKNOWN_KEY = "panel_ticket_unknown_key"
EXPIRED = "panel_ticket_expired"
NOT_YET_VALID = "panel_ticket_not_yet_valid"
WRONG_AUDIENCE = "panel_ticket_wrong_audience"
WRONG_SCOPE = "panel_ticket_wrong_scope"
INVALID = "panel_ticket_invalid"
#: The two other verdicts ``verdict`` reads: a ``TicketClaims``, and a ``TicketRefusal`` without a ticket code.
ACCEPTED = "accepted"
UNVERIFIABLE = "unverifiable: a refusal without a ticket code, the scope's own 401"

#: The three scopes, as ``PanelScope``'s values.
SCOPES = ("backup", "wake", "status")

# =============================================================================
# THE DATA OF THE TESTS: FIXED KEYS, A FIXED CLOCK
# =============================================================================

#: The verifier's clock: 2 000 000 000, in May 2033, far from the wall clock. A verifier that reads the wall clock, or
#: lets PyJWT check the times, refuses every good ticket of this file, all issued «in the future».
NOW = 2_000_000_000
#: The tolerance the tests give ``verify_ticket``, but where a test sets its own.
SKEW = DEFAULT_SKEW
#: The instance's audience, the canonical origin of its public URL; and another origin.
AUDIENCE = "https://mario.librefolio.eu"
OTHER_AUDIENCE = "https://luigi.librefolio.eu"
#: A ``jti`` as a panel draws one, 32 lower-case hexadecimal characters (``uuid4().hex``): inside any alphabet the rule
#: of the ``jti`` may choose.
JTI = "0123456789abcdef0123456789abcdef"
#: A good ticket's times: issued 10 s before ``NOW``, valid for two minutes.
ISSUED = NOW - 10
EXPIRES = ISSUED + 120

#: The seeds of the test keys, fixed: never a real key, never for production. C signs the forgeries; D and E only fill
#: the variable up to five entries.
SEEDS = {name: hashlib.sha256(f"LibreFolio H-61 CP2 test key {name}, never for production".encode()).digest() for name in "ABCDE"}
#: The kids of keys A and B, and one no test configures but HPT-024's barrier.
KID_A = "panel-2026a"
KID_B = "panel-2026b"
UNKNOWN_KID = "panel-2025-retired"
#: A claim set to this is left out of the ticket.
ABSENT = object()
#: What a ``TicketClaims`` carries (TA-T1's brief).
CLAIM_FIELDS = ("kid", "jti", "scope", "iat", "exp")


@cache
def private_key(name: str) -> Ed25519PrivateKey:
    """The private key of the seed ``name``."""
    return Ed25519PrivateKey.from_private_bytes(SEEDS[name])


def public_key(name: str) -> Ed25519PublicKey:
    """The public key of the seed ``name``."""
    return private_key(name).public_key()


def raw_bytes(key: Ed25519PublicKey) -> bytes:
    """The 32 bytes of a public key."""
    return key.public_bytes(Encoding.Raw, PublicFormat.Raw)


def raw_public(name: str) -> bytes:
    """The 32 bytes of the public key of the seed ``name``."""
    return raw_bytes(public_key(name))


def b64url(data: bytes) -> str:
    """``data`` in base64url without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def key_text(name: str) -> str:
    """The public key of the seed ``name`` as the variable writes it: base64url without padding, 43 characters."""
    return b64url(raw_public(name))


def entry(kid: str, name: str) -> str:
    """One entry of the variable, ``kid:key``: the public key of the seed ``name`` under ``kid``."""
    return f"{kid}:{key_text(name)}"


def entries(names: str) -> str:
    """One entry per seed of ``names``, under the kids ``k1``, ``k2``…, joined by commas."""
    return ",".join(entry(f"k{index}", name) for index, name in enumerate(names, 1))


# =============================================================================
# THE NEW NAMES OF H-61 CP2, IMPORTED WHEN A TEST RUNS
# =============================================================================


def _module(name: str) -> ModuleType:
    """The module ``name``, imported when a test needs it: before CP2 ``tickets.py`` does not exist, and the rest of this
    file must still be collected and run."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        # The module or its package missing is the red; a module it imports missing is a finding, raised as it is.
        if error.name not in (name, name.rpartition(".")[0]):
            raise
    pytest.fail(f"H-61 CP2: {_MODULE_FILES[name]} is missing")


def _given(module: ModuleType, name: str) -> Any:
    """``module.name``, the test failing when the module does not give it."""
    value = getattr(module, name, None)
    if value is None:
        pytest.fail(f"H-61 CP2: {module.__name__} gives no {name}")
    return value


def keys_reader() -> Callable[[], Any]:
    """``panel_public_keys`` (§1): before CP2, the test that asks for it fails here, and only that test."""
    return _given(_module(HOSTING_CONFIG_MODULE), "panel_public_keys")


def skew_reader() -> Callable[[], Any]:
    """``panel_clock_skew_seconds`` (§1): before CP2, the test that asks for it fails here."""
    return _given(_module(HOSTING_CONFIG_MODULE), "panel_clock_skew_seconds")


def audience_reader() -> Callable[[], Any]:
    """``panel_audience`` (§1): before CP2, the test that asks for it fails here."""
    return _given(_module(HOSTING_CONFIG_MODULE), "panel_audience")


def verifier() -> Callable[..., Any]:
    """``verify_ticket`` (§2): before CP2, the test that asks for it fails here, and only that test."""
    return _given(_module(TICKETS_MODULE), "verify_ticket")


def panel_scope(route: str) -> Any:
    """The ``PanelScope`` of ``route``, as ``panel_access`` will give it to ``verify_ticket`` (CP1)."""
    return _given(_module(ACCESS_MODULE), "PanelScope")(route)


@pytest.fixture(autouse=True)
def no_inherited_l2_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts with none of the variables of L2: nothing comes from the runner's environment."""
    for name in L2_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def refusal_of(read: Callable[[], Any]) -> Any:
    """The ``HostingPanelConfigError`` ``read()`` raises: the test fails when it returns, or raises anything else."""
    error_class = _given(_module(HOSTING_CONFIG_MODULE), "HostingPanelConfigError")
    with pytest.raises(error_class) as raised:
        read()
    return raised.value


def rendered(error: BaseException) -> str:
    """Every form an error may be shown in: its message, its repr, its arguments."""
    return f"{error} {error!r} {error.args}"


def shown_keys(text: str, *values: str) -> list[str]:
    """Which keys show in ``text``: the public keys of the five seeds and ``values`` (a malformed key), whole or by their
    first 12 characters. Named by a label, never written out."""
    candidates = {f"key {name}": key_text(name) for name in SEEDS}
    candidates.update({f"the malformed value #{index}": value for index, value in enumerate(values)})
    return [label for label, value in candidates.items() if len(value) >= 12 and (value in text or value[:12] in text)]


# =============================================================================
# A TICKET, AS A TEST MAKES IT, AND ITS VERDICT
# =============================================================================


@dataclass(frozen=True)
class Recipe:
    """A ticket for the route of the scope ``route``, as a test makes it, and the keys ``verify_ticket`` is given. By
    default what a panel signs: EdDSA by key A under ``KID_A``, ``typ`` ``lf-panel+jwt``, the claims of ``claims_for``.
    A defect changes one part (``dataclasses.replace``)."""

    route: str
    claims: Mapping[str, Any]
    kid: str | None = KID_A
    typ: str | None = TICKET_TYP
    algorithm: str = ALGORITHM
    #: EdDSA: the name of the seed that signs. HS256: the secret. none: None.
    signer: str | bytes | None = "A"
    #: The keys ``verify_ticket`` is given, as (kid, name of the seed).
    keys: tuple[tuple[str, str], ...] = ((KID_A, "A"),)
    #: What becomes of the ticket once signed (cut, rewritten, replaced); None leaves it as signed.
    finish: Callable[[str], str] | None = None


def claims_for(route: str, /, **changes: Any) -> dict[str, Any]:
    """The claims of the ticket a panel signs for the route of ``route`` at ``NOW``, with ``changes``; a claim set to
    ``ABSENT`` is left out."""
    claims = {"aud": AUDIENCE, "scope": route, "jti": JTI, "iat": ISSUED, "exp": EXPIRES, **changes}
    return {name: value for name, value in claims.items() if value is not ABSENT}


def a_ticket(route: str, /, **changes: Any) -> Recipe:
    """A panel's ticket for the route of ``route``, its claims changed by ``changes``."""
    return Recipe(route=route, claims=claims_for(route, **changes))


def with_claims(recipe: Recipe, **changes: Any) -> Recipe:
    """``recipe`` with its claims changed by ``changes``; a claim set to ``ABSENT`` is left out."""
    claims = {**recipe.claims, **changes}
    return replace(recipe, claims={name: value for name, value in claims.items() if value is not ABSENT})


def mint(recipe: Recipe) -> str:
    """The ticket ``recipe`` describes, signed with PyJWT, then finished."""
    headers: dict[str, Any] = {"typ": recipe.typ}  # None: PyJWT leaves typ out of the header
    if recipe.kid is not None:
        headers["kid"] = recipe.kid
    key = private_key(recipe.signer) if recipe.algorithm == ALGORITHM else recipe.signer
    token = jwt.encode(dict(recipe.claims), key, algorithm=recipe.algorithm, headers=headers)
    return token if recipe.finish is None else recipe.finish(token)


def key_map(pairs: tuple[tuple[str, str], ...]) -> dict[str, Ed25519PublicKey]:
    """The keys of ``pairs`` as ``verify_ticket`` takes them: each kid to its public key."""
    return {kid: public_key(name) for kid, name in pairs}


def judge(value: str, route: str, keys: Mapping[str, Ed25519PublicKey], *, audience: str = AUDIENCE, skew: int = SKEW, now: int = NOW) -> Any:
    """What ``verify_ticket`` returns for ``value`` on the route of ``route``: the contract's six parameters, by name."""
    verify_ticket = verifier()
    return verify_ticket(value=value, scope=panel_scope(route), keys=dict(keys), audience=audience, skew=skew, now=now)


def verdict(result: Any) -> str:
    """``ACCEPTED`` for a ``TicketClaims``; for a ``TicketRefusal``, its code, or ``UNVERIFIABLE`` when it has none."""
    tickets = _module(TICKETS_MODULE)
    claims_class, refusal_class = _given(tickets, "TicketClaims"), _given(tickets, "TicketRefusal")
    if isinstance(result, claims_class):
        return ACCEPTED
    if not isinstance(result, refusal_class):
        pytest.fail(f"verify_ticket returns a TicketClaims or a TicketRefusal: {result!r}")
    if not hasattr(result, "code"):
        pytest.fail(f"a TicketRefusal carries its code, None for an unverifiable ticket: {result!r}")
    return UNVERIFIABLE if result.code is None else result.code


def outcome(recipe: Recipe, **options: Any) -> str:
    """The verdict on the ticket of ``recipe``, under its keys; ``options`` the audience, the skew or the clock."""
    return verdict(judge(mint(recipe), recipe.route, key_map(recipe.keys), **options))


def claim_fields(result: Any) -> dict[str, Any]:
    """What a ``TicketClaims`` says of its ticket, by the brief's names: ``<missing>`` for a name it lacks."""
    return {name: getattr(result, name, "<missing>") for name in CLAIM_FIELDS}


def another_scope(route: str) -> str:
    """A scope other than ``route``: the next one."""
    return SCOPES[(SCOPES.index(route) + 1) % len(SCOPES)]


def expired(recipe: Recipe) -> Recipe:
    """``recipe`` with ``exp`` at ``NOW - SKEW``, the first instant past the tolerance; its lifetime kept."""
    lifetime = recipe.claims["exp"] - recipe.claims["iat"]
    return with_claims(recipe, exp=NOW - SKEW, iat=NOW - SKEW - lifetime)


def early(recipe: Recipe) -> Recipe:
    """``recipe`` with ``iat`` at ``NOW + SKEW + 1``, one second beyond the tolerance; its lifetime kept."""
    lifetime = recipe.claims["exp"] - recipe.claims["iat"]
    return with_claims(recipe, iat=NOW + SKEW + 1, exp=NOW + SKEW + 1 + lifetime)


def overlong(recipe: Recipe) -> Recipe:
    """``recipe`` living one second more than allowed: ``exp`` at ``iat + 301``, ``iat`` kept."""
    return with_claims(recipe, exp=recipe.claims["iat"] + MAX_LIFETIME + 1)


def extended_after_signing(token: str) -> str:
    """``token`` rewritten once signed, as its holder would lengthen it: ``exp`` one minute later, still within the
    lifetime; the header and the signature kept."""
    header, payload, signature = token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    claims["exp"] += 60
    return ".".join((header, b64url(json.dumps(claims, separators=(",", ":")).encode("utf-8")), signature))


#: Kids of 1 to 4 characters: the header's length moves with the kid's, so that a ticket of any size can be built.
SIZE_KIDS = ("s", "sz", "siz", "size")


def _padded(route: str, kid: str, length: int) -> str:
    """A good ticket for ``route`` under ``kid``, signed by key A, carrying a claim ``pad`` of ``length`` characters."""
    return mint(replace(a_ticket(route, pad="x" * length), kid=kid))


def sized(route: str, size: int) -> tuple[str, str]:
    """A good ticket for ``route`` of exactly ``size`` bytes, signed by key A, and its kid. It is padded by a claim of its
    own; a segment in base64url never takes one length in four, so the kid's length is searched as well as the pad's."""
    for kid in SIZE_KIDS:
        bare = len(_padded(route, kid, 0))
        start = max(0, (size - bare) * 3 // 4 - 3)
        for length in range(start, start + 10):
            token = _padded(route, kid, length)
            if len(token) == size:
                return token, kid
    pytest.fail(f"Precondition: no ticket of exactly {size} bytes could be built under the kids {SIZE_KIDS}")


# =============================================================================
# HPT-001..007 (§1): panel_public_keys()
# =============================================================================


@pytest.mark.parametrize("value", [None, "", "   ", " \t "], ids=["unset", "empty", "spaces", "spaces-and-a-tab"])
def test_without_public_keys_level_2_is_off(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """HPT-001 (§1): ``LIBREFOLIO_PANEL_PUBLIC_KEYS`` unset or blank: ``panel_public_keys()`` is None, L2 is off."""
    panel_public_keys = keys_reader()
    if value is not None:
        monkeypatch.setenv(KEYS_VARIABLE, value)

    assert panel_public_keys() is None, f"{KEYS_VARIABLE} {'unset' if value is None else repr(value)}: L2 is off, None"


#: Values of the variable, and the keys they hold: each kid to the name of its key's seed.
KEY_SETS = [
    pytest.param(lambda: entry(KID_A, "A"), {KID_A: "A"}, id="one-entry"),
    pytest.param(lambda: f"  {entry(KID_A, 'A')}  ,   {entry(KID_B, 'B')}  ", {KID_A: "A", KID_B: "B"}, id="two-entries-spaces-around"),
    pytest.param(lambda: entries("ABCD").replace(",", " , "), {f"k{index}": name for index, name in enumerate("ABCD", 1)}, id="four-entries-spaces-around"),
]


@pytest.mark.parametrize(("make", "expected"), KEY_SETS)
def test_the_public_keys_are_kid_key_entries_with_the_spaces_around_ignored(monkeypatch: pytest.MonkeyPatch, make: Callable[[], str], expected: dict[str, str]) -> None:
    """HPT-002 (§1): one, two and four entries ``kid:key``, spaces around each: a dict of each kid to the
    ``Ed25519PublicKey`` its text holds, the 32 bytes written in base64url."""
    print_section(f"H-61 CP2 §1: panel_public_keys(), {len(expected)} entr{'y' if len(expected) == 1 else 'ies'}")
    panel_public_keys = keys_reader()
    monkeypatch.setenv(KEYS_VARIABLE, make())
    keys = panel_public_keys()

    assert isinstance(keys, dict), f"panel_public_keys() is a dict of kid to key: {keys!r}"
    not_keys = {kid: type(key).__name__ for kid, key in keys.items() if not isinstance(key, Ed25519PublicKey)}
    assert not_keys == {}, f"each value is an Ed25519PublicKey: {not_keys}"
    held = {kid: raw_bytes(key) for kid, key in keys.items()}
    assert held == {kid: raw_public(name) for kid, name in expected.items()}, f"each kid with the key its text holds: kids {sorted(held)}, expected {sorted(expected)}"
    print_success(f"{sorted(held)}: each kid with its Ed25519 public key")


def test_the_public_keys_are_read_at_each_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """HPT-003 (§1): the variable is read at each call, as every variable of the module: a new value is the keys at the
    next call, and once it is unset L2 is off again."""
    panel_public_keys = keys_reader()
    monkeypatch.setenv(KEYS_VARIABLE, entry(KID_A, "A"))
    first = panel_public_keys()
    monkeypatch.setenv(KEYS_VARIABLE, entry(KID_B, "B"))
    second = panel_public_keys()
    monkeypatch.delenv(KEYS_VARIABLE)
    third = panel_public_keys()

    read = [None if keys is None else {kid: raw_bytes(key) for kid, key in keys.items()} for keys in (first, second, third)]
    assert read == [{KID_A: raw_public("A")}, {KID_B: raw_public("B")}, None], f"the variable is read at each call: kids {[None if keys is None else sorted(keys) for keys in read]}"


@pytest.mark.parametrize("kid", ["k", "K" * 64, "Panel.Key_2026-10.v1"], ids=["one-character", "64-characters", "letters-digits-dot-underscore-hyphen"])
def test_a_kid_of_1_to_64_allowed_characters_is_taken(monkeypatch: pytest.MonkeyPatch, kid: str) -> None:
    """HPT-004 (§1): the edges of a kid's rule, ``[A-Za-z0-9._-]{1,64}``: one character, 64, and every kind of character
    it allows, each taken as written."""
    panel_public_keys = keys_reader()
    monkeypatch.setenv(KEYS_VARIABLE, entry(kid, "A"))
    keys = panel_public_keys()

    held = None if keys is None else {name: raw_bytes(key) for name, key in keys.items()}
    assert held == {kid: raw_public("A")}, f"the kid {kid!r} is taken as written: {None if held is None else sorted(held)}"


#: An entry the variable cannot hold, by what is wrong with it. Each holds key C, or a spoiled copy of its text, where it
#: holds a key at all.
MALFORMED_ENTRIES = [
    pytest.param(lambda: key_text("C"), id="no-colon"),
    pytest.param(lambda: f"kc:x:{key_text('C')}", id="two-colons"),
    pytest.param(lambda: f":{key_text('C')}", id="empty-kid"),
    pytest.param(lambda: f"panel kc:{key_text('C')}", id="kid-with-a-space-inside"),
    pytest.param(lambda: f"panel/kc:{key_text('C')}", id="kid-with-a-slash"),
    pytest.param(lambda: f"panel-\u00e9:{key_text('C')}", id="kid-not-ascii"),
    pytest.param(lambda: f"{'k' * 65}:{key_text('C')}", id="kid-of-65-characters"),
    pytest.param(lambda: f"kc:{key_text('C')[:42]}", id="key-of-42-characters"),
    pytest.param(lambda: f"kc:{key_text('C')}A", id="key-of-44-characters"),
    pytest.param(lambda: f"kc:{key_text('C')}=", id="key-with-padding"),
    pytest.param(lambda: f"kc:{base64.b64encode(raw_public('C')).decode('ascii')}", id="key-in-standard-base64"),
    pytest.param(lambda: f"kc:+{key_text('C')[1:]}", id="key-with-a-plus"),
    pytest.param(lambda: f"kc:/{key_text('C')[1:]}", id="key-with-a-slash"),
    pytest.param(lambda: "", id="empty-entry"),
    pytest.param(lambda: "   ", id="blank-entry"),
]


@pytest.mark.parametrize("position", [2, 3])
@pytest.mark.parametrize("make", MALFORMED_ENTRIES)
def test_a_malformed_entry_raises_panel_keys_invalid_naming_its_position_never_a_key(monkeypatch: pytest.MonkeyPatch, make: Callable[[], str], position: int) -> None:
    """HPT-005 (§1): an entry without a colon or with two, a kid outside ``[A-Za-z0-9._-]{1,64}`` (empty, a space inside,
    a ``/``, not ASCII, 65 characters), a key that is not 43 characters of base64url without padding (42, 44, padded,
    standard base64, a ``+`` or a ``/``), an empty or blank entry — at position 2 or 3 between two good entries:
    ``HostingPanelConfigError`` ``PANEL_KEYS_INVALID`` on the variable, its message naming the entry's position (counted
    from 1), and never a key, the malformed one nor the good ones, whole or by their first 12 characters. Barrier: the
    two good entries alone are taken."""
    panel_public_keys = keys_reader()
    bad = make()
    good = [entry(KID_A, "A"), entry(KID_B, "B")]
    monkeypatch.setenv(KEYS_VARIABLE, ", ".join(good))
    taken = panel_public_keys()
    monkeypatch.setenv(KEYS_VARIABLE, ", ".join([*good[: position - 1], bad, *good[position - 1 :]]))
    error = refusal_of(panel_public_keys)

    assert taken is not None and sorted(taken) == [KID_A, KID_B], f"Barrier: the two good entries alone are taken: {taken!r}"
    assert (error.code, error.variable) == (KEYS_INVALID, KEYS_VARIABLE), f"the error's code and variable: {(error.code, error.variable)}"
    assert re.search(rf"(?<!\d){position}(?!\d)", str(error)), f"the message names the entry by its position, {position}: {error}"
    shown = shown_keys(rendered(error), bad.rpartition(":")[2].strip())
    assert shown == [], f"the message never holds a key, whole or in part: {shown}"


#: A value whose entries are each well formed, but not together; and the same value put right, which is taken.
WHOLE_VALUE_FORMS = [
    pytest.param(lambda: entries("ABCDE"), lambda: entries("ABCD"), id="five-entries"),
    pytest.param(
        lambda: f"{entry(KID_A, 'A')},{entry(KID_B, 'B')},{entry(KID_A, 'C')}",
        lambda: f"{entry(KID_A, 'A')},{entry(KID_B, 'B')},{entry('panel-2026c', 'C')}",
        id="a-kid-again-with-another-key",
    ),
    pytest.param(lambda: f"{entry(KID_A, 'A')},{entry(KID_A, 'A')}", lambda: entry(KID_A, "A"), id="an-entry-twice"),
]


@pytest.mark.parametrize(("make", "put_right"), WHOLE_VALUE_FORMS)
def test_five_entries_or_a_kid_twice_raise_panel_keys_invalid_never_a_key(monkeypatch: pytest.MonkeyPatch, make: Callable[[], str], put_right: Callable[[], str]) -> None:
    """HPT-006 (§1): 1 to 4 entries, each kid once: five entries, or a kid repeated — with another key, or the same entry
    twice — raise ``PANEL_KEYS_INVALID`` on the variable, and the message holds no key. Barrier: the value put right (four
    entries, a kid of its own, the entry once) is taken."""
    panel_public_keys = keys_reader()
    monkeypatch.setenv(KEYS_VARIABLE, put_right())
    taken = panel_public_keys()
    monkeypatch.setenv(KEYS_VARIABLE, make())
    error = refusal_of(panel_public_keys)

    assert isinstance(taken, dict) and taken, f"Barrier: the value put right is taken: {taken!r}"
    assert (error.code, error.variable) == (KEYS_INVALID, KEYS_VARIABLE), f"the error's code and variable: {(error.code, error.variable)}"
    assert KEYS_VARIABLE in str(error), f"Barrier: the message read is the one naming the variable: {error}"
    shown = shown_keys(rendered(error))
    assert shown == [], f"the message never holds a key, whole or in part: {shown}"


def test_the_public_keys_have_no_file_variable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """HPT-007 (§1): the keys are not a secret, so there is no ``LIBREFOLIO_PANEL_PUBLIC_KEYS_FILE``: such a variable,
    naming a file of good entries, leaves L2 off. Barrier: the same entries in the variable are the keys."""
    panel_public_keys = keys_reader()
    value = f"{entry(KID_A, 'A')},{entry(KID_B, 'B')}"
    path = tmp_path / "panel-public-keys"
    path.write_text(f"{value}\n", encoding="utf-8")
    monkeypatch.setenv(KEYS_FILE_VARIABLE, str(path))
    from_file = panel_public_keys()
    monkeypatch.delenv(KEYS_FILE_VARIABLE)
    monkeypatch.setenv(KEYS_VARIABLE, value)
    from_variable = panel_public_keys()

    assert from_variable is not None and sorted(from_variable) == [KID_A, KID_B], f"Barrier: the entries are good ones: {from_variable!r}"
    assert from_file is None, f"{KEYS_FILE_VARIABLE} is never read: the keys are not a secret, and L2 stays off"


# =============================================================================
# HPT-008..010 (§1): panel_clock_skew_seconds()
# =============================================================================


def test_the_clock_skew_is_60_seconds_while_unset() -> None:
    """HPT-008 (§1): ``LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS`` unset: 60 seconds, an ``int``."""
    panel_clock_skew_seconds = skew_reader()
    skew = panel_clock_skew_seconds()

    assert type(skew) is int and skew == DEFAULT_SKEW, f"unset, the tolerance is {DEFAULT_SKEW} s, an int: {skew!r}"


@pytest.mark.parametrize(("value", "expected"), [("0", 0), ("45", 45), ("300", 300)])
def test_a_clock_skew_from_0_to_300_seconds_is_taken(monkeypatch: pytest.MonkeyPatch, value: str, expected: int) -> None:
    """HPT-009 (§1): a whole number from 0 to 300 is the tolerance, both bounds included, as an ``int``."""
    panel_clock_skew_seconds = skew_reader()
    monkeypatch.setenv(SKEW_VARIABLE, value)
    skew = panel_clock_skew_seconds()

    assert type(skew) is int and skew == expected, f"{SKEW_VARIABLE}={value!r}: {skew!r}"


@pytest.mark.parametrize("value", ["-1", "301", "sixty", "1.5"])
def test_any_other_clock_skew_raises_panel_clock_skew_invalid(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """HPT-010 (§1): below 0, above 300, not a number, not a whole one: ``HostingPanelConfigError``
    ``PANEL_CLOCK_SKEW_INVALID`` on the variable."""
    panel_clock_skew_seconds = skew_reader()
    monkeypatch.setenv(SKEW_VARIABLE, value)
    error = refusal_of(panel_clock_skew_seconds)

    assert (error.code, error.variable) == (SKEW_INVALID, SKEW_VARIABLE), f"{SKEW_VARIABLE}={value!r}: {(error.code, error.variable)}"


# =============================================================================
# HPT-011..012 (§1): panel_audience()
# =============================================================================

#: A public URL, and the audience it gives: its origin in lower case, without the scheme's default port nor a path.
CANONICAL_ORIGINS = [
    pytest.param("https://Mario.LibreFolio.eu/", "https://mario.librefolio.eu", id="host-in-lower-case-trailing-slash-dropped"),
    pytest.param("HTTPS://MARIO.LIBREFOLIO.EU", "https://mario.librefolio.eu", id="scheme-in-lower-case"),
    pytest.param("https://mario.librefolio.eu:443", "https://mario.librefolio.eu", id="443-dropped-for-https"),
    pytest.param("http://mario.librefolio.eu:80", "http://mario.librefolio.eu", id="80-dropped-for-http"),
    pytest.param("https://mario.librefolio.eu:8443", "https://mario.librefolio.eu:8443", id="8443-kept"),
    pytest.param("http://mario.librefolio.eu:443", "http://mario.librefolio.eu:443", id="443-kept-for-http"),
    pytest.param("https://mario.librefolio.eu:80", "https://mario.librefolio.eu:80", id="80-kept-for-https"),
    pytest.param("https://mario.librefolio.eu/librefolio/app/", "https://mario.librefolio.eu", id="path-dropped"),
    pytest.param("https://Mario.LibreFolio.eu:8443/app?tab=1#top", "https://mario.librefolio.eu:8443", id="path-query-and-fragment-dropped"),
]


@pytest.mark.parametrize(("public_url", "origin"), CANONICAL_ORIGINS)
def test_the_audience_is_the_canonical_origin_of_the_public_url(monkeypatch: pytest.MonkeyPatch, public_url: str, origin: str) -> None:
    """HPT-011 (§1): ``panel_audience()`` is the origin of ``LIBREFOLIO_PUBLIC_URL``, ``scheme://host[:port]`` in lower
    case: 443 dropped for https and 80 for http, any other port kept, the path, the query and the fragment dropped. The
    keys are set, as whenever the audience is needed."""
    panel_audience = audience_reader()
    monkeypatch.setenv(KEYS_VARIABLE, entry(KID_A, "A"))
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, public_url)

    assert panel_audience() == origin, f"{PUBLIC_URL_VARIABLE}={public_url!r}: the audience is {origin!r}"


@pytest.mark.parametrize(
    "public_url",
    [None, "", "   ", "mario.librefolio.eu", "ftp://mario.librefolio.eu", "https://"],
    ids=["unset", "empty", "blank", "no-scheme", "not-http", "no-host"],
)
def test_without_a_usable_public_url_the_audience_is_unavailable(monkeypatch: pytest.MonkeyPatch, public_url: str | None) -> None:
    """HPT-012 (§1): the keys set and no usable ``LIBREFOLIO_PUBLIC_URL`` — unset, blank, or an address ``public_url()``
    refuses —: ``HostingPanelConfigError`` ``PANEL_AUDIENCE_UNAVAILABLE``. Barrier: with a usable one, the same keys have
    their audience."""
    panel_audience = audience_reader()
    monkeypatch.setenv(KEYS_VARIABLE, entry(KID_A, "A"))
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, AUDIENCE)
    usable = panel_audience()
    if public_url is None:
        monkeypatch.delenv(PUBLIC_URL_VARIABLE)
    else:
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, public_url)
    error = refusal_of(panel_audience)

    assert usable == AUDIENCE, f"Barrier: with a usable public URL the audience is its origin: {usable!r}"
    assert error.code == AUDIENCE_UNAVAILABLE, f"{PUBLIC_URL_VARIABLE} {'unset' if public_url is None else repr(public_url)}: {error.code}"


# =============================================================================
# HPT-020..033 (§2): verify_ticket(), each case once per scope
# =============================================================================


@pytest.mark.parametrize("scope", SCOPES)
def test_a_ticket_signed_by_a_configured_key_is_accepted_with_its_claims(scope: str) -> None:
    """HPT-020 (§2): a panel's ticket for the route's scope, signed with EdDSA by a configured key under its kid, ``typ``
    ``lf-panel+jwt``, ``aud`` the instance's, issued 10 s ago for two minutes: a ``TicketClaims`` with its ``kid``,
    ``jti``, ``scope``, ``iat`` and ``exp``."""
    print_section(f"H-61 CP2 §2: a good ticket, {scope} scope")
    verifier()
    recipe = a_ticket(scope)
    result = judge(mint(recipe), scope, key_map(recipe.keys))

    assert verdict(result) == ACCEPTED, f"a good ticket is accepted: {result!r}"
    claims = claim_fields(result)
    assert claims == {"kid": KID_A, "jti": JTI, "scope": scope, "iat": ISSUED, "exp": EXPIRES}, f"the claims of the ticket: {claims}"
    print_success(f"{scope}: TicketClaims with its kid, jti, scope, iat and exp")


@pytest.mark.parametrize("scope", SCOPES)
def test_with_two_keys_each_kid_verifies_with_its_own_key(scope: str) -> None:
    """HPT-021 (§2): two keys configured, as during a rotation: a ticket of each, under its own kid, is accepted with that
    kid. The kid picks the key: B's signature under A's kid does not verify, unverifiable."""
    verifier()
    both = ((KID_A, "A"), (KID_B, "B"))
    by_a = replace(a_ticket(scope), keys=both)
    by_b = replace(a_ticket(scope), kid=KID_B, signer="B", keys=both)
    b_under_a = replace(a_ticket(scope), signer="B", keys=both)
    results = {"key A under KID_A": judge(mint(by_a), scope, key_map(both)), "key B under KID_B": judge(mint(by_b), scope, key_map(both))}

    got = {label: (verdict(result), claim_fields(result)["kid"]) for label, result in results.items()}
    assert got == {"key A under KID_A": (ACCEPTED, KID_A), "key B under KID_B": (ACCEPTED, KID_B)}, f"each key's ticket accepted, with its kid: {got}"
    assert outcome(b_under_a) == UNVERIFIABLE, "the kid picks the key: B's signature under KID_A does not verify"


#: A ticket nobody can verify, by what is wrong with it: each made from a good ticket.
UNVERIFIABLE_FORMS = [
    pytest.param(lambda recipe: replace(recipe, algorithm="none", signer=None), id="alg-none"),
    pytest.param(lambda recipe: replace(recipe, algorithm="HS256", signer=raw_public("A")), id="hs256-keyed-with-the-public-keys-32-bytes"),
    pytest.param(lambda recipe: replace(recipe, algorithm="HS256", signer=key_text("A").encode("ascii")), id="hs256-keyed-with-the-public-keys-text"),
    pytest.param(lambda recipe: replace(recipe, typ="JWT"), id="typ-JWT"),
    pytest.param(lambda recipe: replace(recipe, typ=None), id="typ-missing"),
    pytest.param(lambda recipe: replace(recipe, signer="C"), id="another-keys-signature-under-the-kid"),
    pytest.param(lambda recipe: replace(recipe, finish=extended_after_signing), id="payload-rewritten-after-signing"),
    pytest.param(lambda recipe: replace(recipe, finish=lambda token: f"{token.rpartition('.')[0]}."), id="signature-removed"),
    pytest.param(lambda recipe: replace(recipe, finish=lambda token: token.rpartition(".")[0]), id="two-segments"),
    pytest.param(lambda recipe: replace(recipe, finish=lambda token: "not-a-ticket"), id="garbage"),
    pytest.param(lambda recipe: replace(recipe, finish=lambda token: ""), id="empty"),
]


@pytest.mark.parametrize("spoil", UNVERIFIABLE_FORMS)
@pytest.mark.parametrize("scope", SCOPES)
def test_an_unverifiable_ticket_is_refused_without_a_ticket_code(scope: str, spoil: Callable[[Recipe], Recipe]) -> None:
    """HPT-022 (§2): ``alg`` ``none``; HS256 keyed with the configured public key, its 32 bytes or its text (the confusion
    of algorithms); ``typ`` ``JWT``, or none; another key's signature under the configured kid; the payload rewritten
    once signed; the signature removed; two segments; garbage; nothing at all: a ``TicketRefusal`` without a ticket code,
    which the route answers with its scope's own 401, as a wrong token. Barrier: the same ticket unspoiled is accepted."""
    verifier()
    recipe = a_ticket(scope)

    assert outcome(recipe) == ACCEPTED, "Barrier: the same ticket unspoiled is accepted"
    assert outcome(spoil(recipe)) == UNVERIFIABLE, "a ticket nobody can verify is refused without a ticket code"


@pytest.mark.parametrize("scope", SCOPES)
def test_over_2048_bytes_a_ticket_is_unverifiable_before_its_kid_is_read(scope: str) -> None:
    """HPT-023 (§2): a good ticket of 2048 bytes is accepted, one of 2049 is unverifiable, however good its signature.
    The size is step 1, before the kid (step 2): under a kid the keys do not hold, the ticket of 2049 bytes is still
    unverifiable, while the one of 2048 is ``panel_ticket_unknown_key``. Both are padded by a claim of their own."""
    verifier()
    at_limit, at_limit_kid = sized(scope, MAX_TICKET_BYTES)
    over, over_kid = sized(scope, MAX_TICKET_BYTES + 1)
    only_a = {KID_A: public_key("A")}
    got = {
        "2048 bytes, its kid configured": verdict(judge(at_limit, scope, {at_limit_kid: public_key("A")})),
        "2049 bytes, its kid configured": verdict(judge(over, scope, {over_kid: public_key("A")})),
        "2048 bytes, its kid unknown": verdict(judge(at_limit, scope, only_a)),
        "2049 bytes, its kid unknown": verdict(judge(over, scope, only_a)),
    }

    assert (len(at_limit), len(over)) == (MAX_TICKET_BYTES, MAX_TICKET_BYTES + 1), "Precondition: tickets of 2048 and 2049 bytes"
    expected = {
        "2048 bytes, its kid configured": ACCEPTED,
        "2049 bytes, its kid configured": UNVERIFIABLE,
        "2048 bytes, its kid unknown": UNKNOWN_KEY,
        "2049 bytes, its kid unknown": UNVERIFIABLE,
    }
    assert got == expected, f"by size and kid: {got}"


@pytest.mark.parametrize("scope", SCOPES)
def test_a_good_signature_under_an_unknown_kid_is_panel_ticket_unknown_key(scope: str) -> None:
    """HPT-024 (§2): a ticket whose kid the keys do not hold — key A's signature under a kid nobody configured, or key B's
    under its own kid while only A is configured —: ``panel_ticket_unknown_key``. Barrier: with its kid configured, each
    is accepted."""
    verifier()
    renamed = replace(a_ticket(scope), kid=UNKNOWN_KID)
    retired = replace(a_ticket(scope), kid=KID_B, signer="B")
    got = {"A's signature under a kid nobody configured": outcome(renamed), "B's signature under KID_B, only KID_A configured": outcome(retired)}
    configured = {
        "A's signature under a kid nobody configured": outcome(replace(renamed, keys=((UNKNOWN_KID, "A"),))),
        "B's signature under KID_B, only KID_A configured": outcome(replace(retired, keys=((KID_A, "A"), (KID_B, "B")))),
    }

    assert configured == dict.fromkeys(configured, ACCEPTED), f"Barrier: with its kid configured, each ticket is accepted: {configured}"
    assert got == dict.fromkeys(got, UNKNOWN_KEY), f"a kid the keys do not hold: {got}"


@pytest.mark.parametrize("skew", [DEFAULT_SKEW, 0, 300])
@pytest.mark.parametrize("scope", SCOPES)
def test_the_tolerance_takes_both_of_its_edges(scope: str, skew: int) -> None:
    """HPT-025 (§2): with a tolerance of ``skew`` seconds (60, the default; 0 and 300, the bounds of its variable),
    ``iat`` at ``now + skew`` is accepted and one second later ``panel_ticket_not_yet_valid``; ``exp`` at
    ``now - skew + 1`` is accepted and one second earlier, at ``now - skew``, ``panel_ticket_expired``. Each ticket lives
    one minute."""
    verifier()
    edges = {
        "iat at now + skew": ({"iat": NOW + skew, "exp": NOW + skew + 60}, ACCEPTED),
        "iat at now + skew + 1": ({"iat": NOW + skew + 1, "exp": NOW + skew + 61}, NOT_YET_VALID),
        "exp at now - skew + 1": ({"iat": NOW - skew - 59, "exp": NOW - skew + 1}, ACCEPTED),
        "exp at now - skew": ({"iat": NOW - skew - 60, "exp": NOW - skew}, EXPIRED),
    }
    got = {label: outcome(a_ticket(scope, **claims), skew=skew) for label, (claims, _) in edges.items()}

    assert got == {label: expected for label, (_, expected) in edges.items()}, f"a tolerance of {skew} s: {got}"


@pytest.mark.parametrize("scope", SCOPES)
def test_the_clock_is_the_now_verify_ticket_is_given(scope: str) -> None:
    """HPT-026 (§2): the times are the module's own, on the ``now`` it is given, never the wall clock's: one ticket,
    issued at ``ISSUED`` and expiring at ``EXPIRES``, is not yet valid at ``ISSUED - 61``, accepted from ``ISSUED - 60``
    to ``EXPIRES + 59``, expired from ``EXPIRES + 60``."""
    verifier()
    recipe = a_ticket(scope)
    clocks = {
        "iat - skew - 1": (ISSUED - SKEW - 1, NOT_YET_VALID),
        "iat - skew": (ISSUED - SKEW, ACCEPTED),
        "the ticket's own now": (NOW, ACCEPTED),
        "exp + skew - 1": (EXPIRES + SKEW - 1, ACCEPTED),
        "exp + skew": (EXPIRES + SKEW, EXPIRED),
    }
    got = {label: outcome(recipe, now=now) for label, (now, _) in clocks.items()}

    assert got == {label: expected for label, (_, expected) in clocks.items()}, f"one ticket under five clocks: {got}"


@pytest.mark.parametrize("scope", SCOPES)
def test_a_lifetime_of_300_seconds_is_taken_and_301_is_panel_ticket_invalid(scope: str) -> None:
    """HPT-027 (§2): ``exp - iat`` of 300 s is accepted; 301, a ticket its signer built wrong, ``panel_ticket_invalid``."""
    verifier()
    got = {lifetime: outcome(a_ticket(scope, exp=ISSUED + lifetime)) for lifetime in (MAX_LIFETIME, MAX_LIFETIME + 1)}

    assert got == {MAX_LIFETIME: ACCEPTED, MAX_LIFETIME + 1: INVALID}, f"by lifetime, in seconds: {got}"


#: Origins other than the instance's: another host, another scheme, another port.
OTHER_AUDIENCES = [
    pytest.param(OTHER_AUDIENCE, id="another-host"),
    pytest.param("http://mario.librefolio.eu", id="another-scheme"),
    pytest.param("https://mario.librefolio.eu:8443", id="another-port"),
]


@pytest.mark.parametrize("audience", OTHER_AUDIENCES)
@pytest.mark.parametrize("scope", SCOPES)
def test_a_ticket_for_another_origin_is_panel_ticket_wrong_audience(scope: str, audience: str) -> None:
    """HPT-028 (§2): ``aud`` another origin — another host, scheme or port —: ``panel_ticket_wrong_audience``. Barrier:
    the same ticket for the instance's own origin is accepted."""
    verifier()

    assert outcome(a_ticket(scope)) == ACCEPTED, "Barrier: the ticket for the instance's audience is accepted"
    assert outcome(a_ticket(scope, aud=audience)) == WRONG_AUDIENCE, f"aud {audience!r}, the instance's {AUDIENCE!r}"


@pytest.mark.parametrize("scope", SCOPES)
def test_a_ticket_without_an_audience_is_panel_ticket_wrong_audience(scope: str) -> None:
    """HPT-029 (§2, as TA-T1's brief reads it): a ticket without ``aud`` gets ``panel_ticket_wrong_audience``, as one for
    another origin — though ``aud`` is among the required claims, whose absence the contract otherwise calls
    ``panel_ticket_invalid`` (HPT-032). Barrier: the same ticket with the instance's audience is accepted."""
    verifier()

    assert outcome(a_ticket(scope)) == ACCEPTED, "Barrier: the ticket for the instance's audience is accepted"
    assert outcome(a_ticket(scope, aud=ABSENT)) == WRONG_AUDIENCE, "a ticket without aud is for no audience, so not this one"


@pytest.mark.parametrize("scope", SCOPES)
def test_a_ticket_for_another_scope_is_panel_ticket_wrong_scope(scope: str) -> None:
    """HPT-030 (§2): a ticket opens its own scope's routes only: on the route of ``scope``, the ticket of each other
    scope, or of a scope that does not exist, gets ``panel_ticket_wrong_scope``. Barrier: the ticket of ``scope`` is
    accepted."""
    verifier()
    others = [other for other in SCOPES if other != scope] + ["admin"]
    got = {other: outcome(a_ticket(scope, scope=other)) for other in others}

    assert outcome(a_ticket(scope)) == ACCEPTED, f"Barrier: the ticket of the {scope} scope is accepted on its route"
    assert got == dict.fromkeys(others, WRONG_SCOPE), f"on the {scope} route, tickets of other scopes: {got}"


#: A ``jti`` and its verdict: 16 to 64 characters, and never a ``/``.
JTI_CASES = [
    pytest.param("a" * 15, INVALID, id="15-characters"),
    pytest.param("a" * 16, ACCEPTED, id="16-characters"),
    pytest.param("a" * 64, ACCEPTED, id="64-characters"),
    pytest.param("a" * 65, INVALID, id="65-characters"),
    pytest.param(f"{'a' * 15}/{'a' * 16}", INVALID, id="32-characters-with-a-slash"),
]


@pytest.mark.parametrize(("jti", "expected"), JTI_CASES)
@pytest.mark.parametrize("scope", SCOPES)
def test_a_jti_outside_its_rule_is_panel_ticket_invalid(scope: str, jti: str, expected: str) -> None:
    """HPT-031 (§2): a ``jti`` of 16 to 64 characters is accepted; one of 15 or 65, or holding a ``/``, breaks its rule:
    ``panel_ticket_invalid``."""
    verifier()

    assert outcome(a_ticket(scope, jti=jti)) == expected, f"a jti of {len(jti)} characters{', a / inside' if '/' in jti else ''}"


@pytest.mark.parametrize("claim", ["exp", "iat", "jti", "scope"])
@pytest.mark.parametrize("scope", SCOPES)
def test_a_required_claim_missing_is_panel_ticket_invalid(scope: str, claim: str) -> None:
    """HPT-032 (§2): ``exp``, ``iat``, ``jti`` and ``scope`` are required (``aud`` as well: HPT-029): a ticket without one
    of them, ``panel_ticket_invalid``. Barrier: the whole ticket is accepted."""
    verifier()

    assert outcome(a_ticket(scope)) == ACCEPTED, "Barrier: the whole ticket is accepted"
    assert outcome(a_ticket(scope, **{claim: ABSENT})) == INVALID, f"a ticket without {claim}"


#: One defect of a ticket, by name: the verdict it gets alone, and how it is made. The times move both ``iat`` and
#: ``exp``, keeping the lifetime; the lifetime moves ``exp`` only: so ``expired`` and ``early`` keep the defect of
#: ``overlong`` applied before them.
DEFECTS: dict[str, tuple[str, Callable[[Recipe], Recipe]]] = {
    "alg none": (UNVERIFIABLE, lambda recipe: replace(recipe, algorithm="none", signer=None)),
    "typ JWT": (UNVERIFIABLE, lambda recipe: replace(recipe, typ="JWT")),
    "another key's signature": (UNVERIFIABLE, lambda recipe: replace(recipe, signer="C")),
    "an unknown kid": (UNKNOWN_KEY, lambda recipe: replace(recipe, kid=UNKNOWN_KID)),
    "expired": (EXPIRED, expired),
    "not yet valid": (NOT_YET_VALID, early),
    "another audience": (WRONG_AUDIENCE, lambda recipe: with_claims(recipe, aud=OTHER_AUDIENCE)),
    "another scope": (WRONG_SCOPE, lambda recipe: with_claims(recipe, scope=another_scope(recipe.route))),
    "a jti of 15 characters": (INVALID, lambda recipe: with_claims(recipe, jti="a" * 15)),
    "a lifetime of 301 s": (INVALID, overlong),
    "no jti": (INVALID, lambda recipe: with_claims(recipe, jti=ABSENT)),
}

#: Pairs of defects of one ticket, first the one the contract checks first: the pair gets its verdict. Only the pairs
#: whose order the contract makes visible either way — by its numbered steps (1 unverifiable, 2 the kid, 3 the
#: decoding), and among the checks after the decoding by the order it lists them in, wherever PyJWT's decoding (which
#: checks the audience and the required claims before this module's times) cannot reverse it.
ORDER = [
    pytest.param("alg none", "an unknown kid", id="alg-before-the-kid"),
    pytest.param("typ JWT", "an unknown kid", id="typ-before-the-kid"),
    pytest.param("an unknown kid", "expired", id="the-kid-before-the-times"),
    pytest.param("an unknown kid", "another scope", id="the-kid-before-the-scope"),
    pytest.param("another key's signature", "expired", id="the-signature-before-the-times"),
    pytest.param("another key's signature", "no jti", id="the-signature-before-the-required-claims"),
    pytest.param("another audience", "another scope", id="the-audience-before-the-scope"),
    pytest.param("expired", "another scope", id="expired-before-the-scope"),
    pytest.param("not yet valid", "another scope", id="not-yet-valid-before-the-scope"),
    pytest.param("expired", "a lifetime of 301 s", id="expired-before-the-lifetime"),
    pytest.param("not yet valid", "a jti of 15 characters", id="not-yet-valid-before-the-jti"),
    pytest.param("another scope", "a jti of 15 characters", id="the-scope-before-the-jti"),
    pytest.param("another scope", "a lifetime of 301 s", id="the-scope-before-the-lifetime"),
]


@pytest.mark.parametrize(("first", "second"), ORDER)
@pytest.mark.parametrize("scope", SCOPES)
def test_two_defects_get_the_verdict_of_the_one_checked_first(scope: str, first: str, second: str) -> None:
    """HPT-033 (§2): a ticket with two defects gets the verdict of the one the contract checks first — among them, a ticket
    both expired and for another scope is ``panel_ticket_expired``. Barrier: each defect alone gets its own verdict, and
    the two verdicts differ, so that the pair shows the order."""
    verifier()
    (first_verdict, add_first), (second_verdict, add_second) = DEFECTS[first], DEFECTS[second]
    assert first_verdict != second_verdict, f"Precondition: {first!r} and {second!r} have verdicts of their own"
    base = a_ticket(scope)
    alone = {first: outcome(add_first(base)), second: outcome(add_second(base))}
    both = outcome(add_first(add_second(base)))

    assert alone == {first: first_verdict, second: second_verdict}, f"Barrier: each defect alone gets its own verdict: {alone}"
    assert both == first_verdict, f"{first} and {second} at once: {first} is checked first, {first_verdict}; got {both}"


# =============================================================================
# HPT-040 (§1 with §2): the readers and the verifier together
# =============================================================================


@pytest.mark.parametrize("scope", SCOPES)
def test_what_the_readers_give_is_what_a_panels_ticket_is_checked_against(monkeypatch: pytest.MonkeyPatch, scope: str) -> None:
    """HPT-040 (§1 with §2): the configuration as an operator writes it — two keys, spaces around; the public URL with its
    default port, a path and capitals; the tolerance unset — read by the three readers and given to ``verify_ticket``: a
    ticket of key B under its kid, ``aud`` the canonical origin, issued at the edge of the default tolerance (60 s
    ahead), is accepted."""
    print_section(f"H-61 CP2 §1 with §2: the readers feed verify_ticket, {scope} scope")
    panel_public_keys, panel_audience, panel_clock_skew_seconds = keys_reader(), audience_reader(), skew_reader()
    verifier()
    monkeypatch.setenv(KEYS_VARIABLE, f" {entry(KID_A, 'A')} , {entry(KID_B, 'B')} ")
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, "https://Mario.LibreFolio.eu:443/librefolio/")
    keys, audience, skew = panel_public_keys(), panel_audience(), panel_clock_skew_seconds()
    assert keys is not None and sorted(keys) == [KID_A, KID_B], f"Precondition: the two keys are read: {keys!r}"
    assert (audience, skew) == (AUDIENCE, DEFAULT_SKEW), f"Precondition: the canonical origin and the default tolerance: {(audience, skew)}"
    ticket = mint(replace(a_ticket(scope, iat=NOW + DEFAULT_SKEW, exp=NOW + DEFAULT_SKEW + 120), kid=KID_B, signer="B"))

    result = judge(ticket, scope, keys, audience=audience, skew=skew)

    assert verdict(result) == ACCEPTED, f"the ticket is accepted on what the readers give: {result!r}"
    assert claim_fields(result)["kid"] == KID_B, f"under key B's kid: {claim_fields(result)}"
    print_success(f"{scope}: keys, audience and tolerance from the environment verify a panel's ticket")
