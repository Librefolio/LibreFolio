"""
H-61 checkpoint 2 · signed tickets (L2) in the hosting panel's access (LibreFolio 1.3, workstream H, platform): the
tickets inside ``panel_access``, the one dependency every route of the hosting panel takes; the limiter's counting rule;
and the states the startup check ``platform.hosting_panel`` gains. The contract is H-61 CP2's, §3 and §4, with §1 and §2
for the ticket. It builds on CP1, whose tests (``test_hosting_panel_access.py``) this file follows and does not touch.

Under test:

- §1, the configuration, through the dependency and the check only: ``LIBREFOLIO_PANEL_PUBLIC_KEYS`` is
  ``kid:key[,kid:key…]``, spaces around the entries ignored, 1 to 4 entries, ``kid`` ``[A-Za-z0-9._-]{1,64}`` and unique,
  ``key`` a raw Ed25519 public key in base64url without padding (43 characters); unset or blank, L2 is off; anything
  else ``PANEL_KEYS_INVALID``, naming the entry by position, never the key. ``LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS``, an
  integer from 0 to 300, default 60, else ``PANEL_CLOCK_SKEW_INVALID``. The audience is the origin of
  ``LIBREFOLIO_PUBLIC_URL``, ``scheme://host[:port]`` in lower case, without a default port or a path; keys without a
  usable address, ``PANEL_AUDIENCE_UNAVAILABLE``.
- §2, the ticket: a compact JWS, ``alg`` ``EdDSA``, ``typ`` ``lf-panel+jwt``, its ``kid`` one of the keys; the claims
  ``exp``, ``iat``, ``aud``, ``jti`` and ``scope``, all required. Unverifiable (more than 2048 bytes, not a JWS, another
  ``alg``, another ``typ``, a signature that does not verify): the scope's 401 of today, no code of its own. A ``kid`` the
  keys do not know: ``panel_ticket_unknown_key``. Signed but refused: ``panel_ticket_expired``,
  ``panel_ticket_not_yet_valid`` (with ``Retry-After: 5``), ``panel_ticket_wrong_audience``, ``panel_ticket_wrong_scope``,
  ``panel_ticket_invalid`` (``exp − iat > 300``, a required claim missing). The ``jti`` registry is
  ``DATA_DIR/panel_tickets.sqlite3``: a ``jti`` already there, ``panel_ticket_replayed``; out of reach, the scope's 503.
  Every refusal a 401 with ``WWW-Authenticate: Bearer`` and ``{"detail": {"code", "message"}}``.
- §3, ``panel_access``, after the limiter: the scope's token, set and matching, is accepted (``credential="token"``);
  else, with keys set, ``verify_ticket`` then the registry, accepted as ``credential="ticket"``, the line also carrying
  ``kid`` and ``jti``; else refused. A scope is on when its token or the keys are set. ``PanelCaller`` gains ``kid`` and
  ``jti``, both ``None`` for a token. The limiter counts only what proves nothing (a wrong token, an unverifiable
  ticket, a missing credential): a ticket with a valid signature, refused, is never counted.
- §4, ``check_hosting_panel()``: unusable keys, a skew out of range, or keys without a usable ``LIBREFOLIO_PUBLIC_URL``,
  ``error``; with usable keys, a ``LIBREFOLIO_PUBLIC_URL`` holding a path other than the root, ``warning``
  ``instance.checks.hostingPanel.audiencePath`` with ``{path}``, in both profiles (the audience is the origin only, so
  two instances on one origin under different paths would accept each other's tickets: one origin per instance); in the
  managed profile a scope token beside the keys, ``warning`` ``instance.checks.hostingPanel.coexisting`` with
  ``{variables}``; self-hosted, ``ok``. The path warning comes first.

The tests:

- HPT-001..004, the scopes (§3, §1): the keys alone turn each scope on — no credential, its 401 ``missing`` and counted;
  a valid ticket, 200 with ``PanelCaller(scope, "ticket", kid, jti)`` and its INFO line whole —, while neither a token
  nor keys (unset, blank) is CP1's 404 (001); the token and the keys together: the token accepted as ``token``, ``kid``
  and ``jti`` None, CP1's line; a ticket accepted as ``ticket``; a wrong token refused and counted (002); two keys, each
  ``kid`` choosing its own key, spaces around the entries ignored; one key's signature under the other's ``kid``
  unverifiable (003); the audience is the canonical origin of ``LIBREFOLIO_PUBLIC_URL``: a ticket for it accepted, for the
  address as written or with a trailing slash ``panel_ticket_wrong_audience`` (004).
- HPT-010..013, the refusals (§2 through §3): each signed ticket refused gets its own code — expired, not yet valid with
  ``Retry-After: 5``, wrong audience, wrong scope, invalid (a lifetime over 300 s, no ``jti``), unknown key —, a Bearer
  challenge and one WARNING line, and is never counted (the unknown key: left open); a valid ticket then opens the scope
  (010); each unverifiable ticket — ``alg: none``, HS256 keyed with the public key, ``typ: JWT``, signed by a key not
  configured under a known ``kid``, its payload altered after signing, over 2048 bytes, not a JWS — gets the scope's 401
  of today and is counted (011); replay: a ticket refused for another scope keeps its ``jti``, opens its own scope once,
  then the same ticket or another one with its ``jti`` is ``panel_ticket_replayed``, never counted; the registry is
  ``panel_tickets.sqlite3`` in the data directory, in ``tmp_path`` (012); a registry out of reach: the scope's 503 to a
  valid ticket, not counted, while the token, read first, still opens the scope (013).
- HPT-020..021, the limiter (§3): what proves nothing — wrong tokens, missing credentials, ``Basic``, unverifiable
  tickets — is counted, and 20 of it close the address even to a valid ticket, whose ``jti`` the 429 does not record:
  once the window has passed the same ticket opens the scope (020); 30 expired tickets from one address, then every
  other refusal of a signed ticket and a replay, are never counted: a valid ticket is accepted after them (021).
- HPT-030, the lines (§3): every outcome at once, each request with a query canary: no ticket, no signature and no
  ``Authorization`` value in any answer, header or line; every line within CP1's fields plus ``kid`` and ``jti``.
- HPT-040..043, the startup check (§4): unusable keys, a skew out of range, keys without a usable
  ``LIBREFOLIO_PUBLIC_URL``: ``error`` in both profiles, the summary naming the code (and the variable, for the keys and
  the skew), never a key (040); usable keys alone, the skew unset, 0 or 300: ``ok``, ``hostingPanel.ok``, in both
  profiles (041); a token beside the keys: in the managed profile ``warning`` ``hostingPanel.coexisting``, its
  ``{variables}`` naming the token's variable; self-hosted ``ok`` (042); a path in ``LIBREFOLIO_PUBLIC_URL`` beside
  usable keys: ``warning`` ``hostingPanel.audiencePath`` with ``{"path": ...}`` (the path as written, without the one
  trailing slash ``env_url`` drops), in both profiles, a summary naming ``LIBREFOLIO_PUBLIC_URL`` (043a); the root,
  with or without its slash, ``ok`` (043b); without keys a path is not this check's business (043c); the precedence: an
  unusable token or unusable ticket settings stay ``error``, a token beside the keys in the managed profile gives the path
  warning, not ``coexisting`` (043d).

Left open by the contract, so not pinned: the text of the ``panel_ticket_*`` messages (each a non-empty text); the
``reason`` and the ``credential`` of a refused line (the credential one of ``token`` and ``ticket``), but ``missing`` for
a request without a credential, as in CP1; whether a ticket whose ``kid`` the keys do not know is counted; the message of
the registry's 503 (its code is the scope's ``…_unavailable``) and the outcome of its line; what a request meets while
the keys, the skew or the address cannot be used; whether ``{variables}`` of the coexisting warning names the backup
token, and its order; the i18n key of the check's errors (one of ``instance.checks.hostingPanel.*``).

How. Pure: no server, no lane database, no network, no file outside ``tmp_path``. As in CP1's file, a fresh
``FastAPI()`` holds one test route per scope, each taking ``Depends(panel_access(PanelScope(<scope>)))`` and recording
the caller it gets; the requests go through ``httpx.ASGITransport`` in this process, from a public peer, each with a
canary header, and each ends on the check that no configured token, no credential presented (the whole
``Authorization`` value, the ticket, its signature), no header value, no query value and not the client's address is in
the answer, its headers or any captured line. The log is captured with
``structlog.testing.capture_logs(processors=[merge_contextvars])`` behind a barrier, a canary logged through the access
module's own ``logger``; the lines the contract pins whole are compared whole, keys included. ``PANEL_ATTEMPTS`` is
replaced through ``monkeypatch`` by a ``SlidingWindowLimiter(20, 600)`` on a fake clock which records the calls the
dependency makes; the clock moves only when a test moves it, and nothing sleeps. The keys are Ed25519 keys built from
fixed seeds (the SHA-256 of a text naming each), never a real one; the tickets are signed with PyJWT, each with a new
``jti`` (16 random bytes in base64url, as the signer makes them). A ticket's times are set against the wall clock when it
is built, minutes away from every edge (a valid ticket was issued 5 s before and lives 240 s; an expired one ended 56
minutes before; an early one starts an hour later): the contract hands ``verify_ticket`` its ``now`` but names no clock
of ``panel_access`` a test could replace, and the edges are ``verify_ticket``'s own tests'. Every variable the
dependency and the check read for the panel (the three tokens and their ``_FILE``, the keys, the skew,
``LIBREFOLIO_PUBLIC_URL``) is removed before each test, which sets what it needs through ``monkeypatch``; the data
directory, where the registry lives, is ``tmp_path/data`` (test mode, ``LIBREFOLIO_TEST_DATA_DIR``), a precondition of
every test that sends a request. The check is called directly, its profile set through ``LIBREFOLIO_PROFILE``. This
file does not use ``from __future__ import annotations``: a test route's ``Annotated[..., Depends(...)]`` is built from
a local dependency.

Red today. L2 does not exist (CP1 only): ``panel_access`` reads no keys, so a scope without its token stays off and
answers 404 whatever the keys. HPT-001, 003, 004, 010, 011, 012, 020, 021 and 030 fail on the first request a ticket or a
missing credential makes to such a scope: 404 where 200, a ``panel_ticket_*`` code or the scope's 401 is expected
(HPT-001 and 021 after their barriers, which CP1 already holds). With a token beside the keys a ticket is a mismatched
token: HPT-002 fails on its 401 where 200 is expected, HPT-013 on that 401 where the scope's 503 is.
``check_hosting_panel()`` reads neither the keys, the skew nor ``LIBREFOLIO_PUBLIC_URL``: HPT-040 meets ``ok``
(``hostingPanel.off``) where ``error`` is expected, HPT-041 ``hostingPanel.off`` where ``hostingPanel.ok``, HPT-042
``ok`` where the managed profile's ``warning`` is, after its barrier (the tokens alone, ok, as in CP1). The file
collects today: it imports only what exists, and the access module in its fixture.

Red since the security review (the path warning, HPT-043): the check gives ``ok`` (``hostingPanel.ok``) for keys beside
a ``LIBREFOLIO_PUBLIC_URL`` with a path. HPT-043a fails on that, in both of its cases, after its barrier (the root is
``ok``); HPT-043d's managed case with a token beside the keys gets ``coexisting`` where ``audiencePath`` is expected. HPT-043b
and 043c, and the ``error`` cases of 043d, hold today and keep it so.
"""

import asyncio
import base64
import hashlib
import importlib
import itertools
import json
import secrets
import time
import uuid
from collections import Counter
from collections.abc import Callable, Hashable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Annotated, Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import Depends, FastAPI, Request
from structlog.contextvars import merge_contextvars
from structlog.testing import capture_logs

from backend.app.config import get_data_dir
from backend.app.services.platform import client_address as client_address_module
from backend.app.services.platform import config_audit
from backend.app.utils.runtime.rate_window import RateDecision, SlidingWindowLimiter
from backend.test_scripts.test_utils import print_section, print_success

# =============================================================================
# THE CONTRACT, SPELLED OUT
# =============================================================================

#: CP1's access module, which CP2 extends: imported by the fixture that needs it.
ACCESS_MODULE = "backend.app.services.platform.hosting_panel.access"
ACCESS_FILE = "backend/app/services/platform/hosting_panel/access.py"

#: The three scopes of the panel, as ``PanelScope``'s values.
BACKUP, WAKE, STATUS = "backup", "wake", "status"
SCOPES = (BACKUP, WAKE, STATUS)

#: The variables the panel's access reads, spelled out as .env.example writes them, so a rename shows.
FILE_SUFFIX = "_FILE"
VARIABLES = {BACKUP: "LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN", WAKE: "LIBREFOLIO_WAKE_TOKEN", STATUS: "LIBREFOLIO_PANEL_STATUS_TOKEN"}
TOKEN_VARIABLES = tuple(name for variable in VARIABLES.values() for name in (variable, variable + FILE_SUFFIX))
KEYS_VARIABLE = "LIBREFOLIO_PANEL_PUBLIC_KEYS"
SKEW_VARIABLE = "LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
#: Every variable removed before each test: none comes from the runner's environment. The keys are not a secret and
#: have no ``_FILE``: one left over from a shell is removed all the same.
PANEL_ENVIRONMENT = (*TOKEN_VARIABLES, KEYS_VARIABLE, KEYS_VARIABLE + FILE_SUFFIX, SKEW_VARIABLE, PUBLIC_URL_VARIABLE)
#: The names the coexisting warning's ``{variables}`` may hold: the scopes' tokens and the keys.
PANEL_VARIABLES = frozenset({*VARIABLES.values(), KEYS_VARIABLE})

#: The instance's address in every test but HPT-004, already in its canonical form, and so the tickets' audience.
PUBLIC_URL = "https://folio.example.com"
AUDIENCE = "https://folio.example.com"
OTHER_AUDIENCE = "https://other.example.com"

#: The test's data directory, below ``tmp_path``, and the registry the contract keeps there.
DATA_FOLDER = "data"
REGISTRY_FILE = "panel_tickets.sqlite3"

#: The ticket's header and its size limit.
TICKET_TYP = "lf-panel+jwt"
TICKET_ALGORITHM = "EdDSA"
TICKET_MAX_BYTES = 2048

#: A ticket's times, in seconds from the wall clock when it is built: minutes away from every edge, whatever the skew.
#: Valid: issued 5 s before, living 240 s. Expired: ended 3360 s before. Early: issued an hour later. Too long: 3600 s.
VALID_IAT_OFFSET = -5
VALID_LIFETIME = 240
EXPIRED_IAT_OFFSET = -3600
EARLY_IAT_OFFSET = 3600
LONG_LIFETIME = 3600

#: The answers, whole where the contract gives them whole: CP1's 404, and each scope's 401, 503 and the 429.
OFF_ANSWER = (404, {"detail": "Not Found"})
UNAUTHORIZED = {
    BACKUP: (401, {"detail": {"code": "backup_panel_unauthorized", "message": "A valid panel token is required"}}),
    WAKE: (401, {"detail": {"code": "wake_unauthorized", "message": "A valid wake-up token is required"}}),
    STATUS: (401, {"detail": {"code": "panel_status_unauthorized", "message": "A valid panel status token is required"}}),
}
UNAVAILABLE = {
    BACKUP: (503, {"detail": {"code": "backup_panel_unavailable", "message": "The panel token of this instance cannot be used"}}),
    WAKE: (503, {"detail": {"code": "wake_unavailable", "message": "The wake-up token of this instance cannot be used"}}),
    STATUS: (503, {"detail": {"code": "panel_status_unavailable", "message": "The panel status token of this instance cannot be used"}}),
}
TOO_MANY = (429, {"detail": {"code": "panel_too_many_attempts", "message": "Too many refused panel credentials from this address"}})

#: The codes of a signed ticket refused (§2): the scopes share them.
EXPIRED = "panel_ticket_expired"
NOT_YET_VALID = "panel_ticket_not_yet_valid"
WRONG_AUDIENCE = "panel_ticket_wrong_audience"
WRONG_SCOPE = "panel_ticket_wrong_scope"
INVALID = "panel_ticket_invalid"
UNKNOWN_KEY = "panel_ticket_unknown_key"
REPLAYED = "panel_ticket_replayed"
#: ``panel_ticket_not_yet_valid`` also asks the panel to retry, with a new ticket, in 5 seconds.
NOT_YET_VALID_RETRY_AFTER = "5"

#: The line of every request a scope that is on decides, and the keys a line may hold: CP1's, plus a ticket's ``kid`` and
#: ``jti``.
PANEL_LINE = "Hosting panel request"
LINE_KEYS = frozenset({"event", "log_level", "scope", "method", "path", "outcome", "credential", "reason", "retry_after", "request_id"})
TICKET_LINE_KEYS = LINE_KEYS | {"kid", "jti"}
CREDENTIALS = ("token", "ticket")
CAPTURE_CANARY = "H-61 CP2 test: the capture sees the access module's logger"

#: CP1's limiter: 20 refused credentials per address in any 600 seconds; its fake clock starts on a whole second.
PANEL_LIMIT = 20
PANEL_WINDOW_SECONDS = 600
START = 1_000.0
#: HPT-021: the expired tickets one address sends, more than the limit.
EXPIRED_COUNT = 30

#: The test routes, one per scope: method and path. The backup one has a path parameter, so a line's path is the
#: request's own; the three methods differ, so a line's method is the request's own.
ROUTES = {
    BACKUP: ("DELETE", "/hpt-test/backup/panel/jobs/{job_id}"),
    WAKE: ("POST", "/hpt-test/system/wake-sync"),
    STATUS: ("GET", "/hpt-test/panel/status"),
}
#: The peer of every request (``httpx.ASGITransport``'s ``client``): a public address, its own key.
PEER = ("203.0.113.50", 50000)
#: A header every request carries, whose value no line nor answer may hold.
CANARY_HEADER = "X-Hpt-Canary"
BASE_URL = "http://hpt.test"
#: Every in-process call ends within this, or the test fails instead of hanging.
CALL_SECONDS = 10.0
#: The shortest signature looked for in the answers and the log: a real one is 86 characters, and a shorter third segment
#: of a value that is no JWS could match by chance.
SIGNATURE_MIN_LENGTH = 16
#: What a view shows for an attribute or a field the object does not have.
ABSENT = "<absent>"

#: The check of §4, its i18n keys and the two profiles.
CHECK_ID = "platform.hosting_panel"
CHECK_KEY_PREFIX = "instance.checks.hostingPanel."
CHECK_OK = CHECK_KEY_PREFIX + "ok"
CHECK_COEXISTING = CHECK_KEY_PREFIX + "coexisting"
PROFILES = ("managed", "selfhosted")


# =============================================================================
# THE KEYS AND THE TICKETS OF A TEST
# =============================================================================


def b64url(data: bytes) -> str:
    """``data`` in base64url without padding, as a JWS and ``LIBREFOLIO_PANEL_PUBLIC_KEYS`` write bytes."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def from_b64url(text: str) -> bytes:
    """The bytes of ``text``, base64url without padding."""
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


@dataclass(frozen=True)
class SigningKey:
    """A test key of the panel: its ``kid``, its private half, which signs, and its public half as the variable writes it."""

    kid: str
    private: Ed25519PrivateKey
    public_text: str

    @property
    def entry(self) -> str:
        """The key as one entry of ``LIBREFOLIO_PANEL_PUBLIC_KEYS``: ``kid:key``."""
        return f"{self.kid}:{self.public_text}"


#: The text a test key's seed is derived from: fixed, so every run has the same keys; never a key of a real panel.
SEED_TEXT = "LibreFolio H-61 CP2, test_hosting_panel_access_tickets.py, a test key never used in production: {label}"


def signing_key(kid: str, label: str) -> SigningKey:
    """The test key ``label``: Ed25519 from a fixed seed, the SHA-256 of a text naming it."""
    seed = hashlib.sha256(SEED_TEXT.format(label=label).encode("utf-8")).digest()
    private = Ed25519PrivateKey.from_private_bytes(seed)
    raw = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return SigningKey(kid, private, b64url(raw))


KEY_A = signing_key("hp-key-a", "key A")
KEY_B = signing_key("hp-key-b.2026", "key B")
#: Never configured: it signs the tickets of a ``kid`` the instance does not know, and forgeries under a known ``kid``.
KEY_C = signing_key("hp-key-c", "key C")
#: Three more keys, so the variable can hold five entries, one too many.
EXTRA_KEYS = tuple(signing_key(f"hp-key-{number}", f"key {number}") for number in range(1, 4))
ALL_KEYS = (KEY_A, KEY_B, KEY_C, *EXTRA_KEYS)
UNKNOWN_KID = "hp-key-z"
#: The first characters of each test key as written: none may show in a result of the check (§1: never the key).
KEY_FRAGMENTS = tuple(key.public_text[:20] for key in ALL_KEYS)


def keys_value(*keys: SigningKey) -> str:
    """``LIBREFOLIO_PANEL_PUBLIC_KEYS`` holding ``keys``, in order, separated by commas."""
    return ",".join(key.entry for key in keys)


@dataclass(frozen=True)
class Ticket:
    """A ticket as a test built it: the compact JWS, the ``kid`` of its header, the ``jti`` of its claims (None without)."""

    value: str
    kid: str | None
    jti: str | None

    @property
    def authorization(self) -> str:
        """The ticket as the panel sends it: ``Authorization: Bearer <ticket>``."""
        return f"Bearer {self.value}"


def new_jti() -> str:
    """A ``jti`` as the signer makes one: 16 random bytes in base64url, 22 characters of ``[A-Za-z0-9_-]``."""
    return secrets.token_urlsafe(16)


def claims_for(
    scope: str,
    *,
    aud: str = AUDIENCE,
    iat_offset: int = VALID_IAT_OFFSET,
    lifetime: int = VALID_LIFETIME,
    jti: str | None = None,
    drop: Sequence[str] = (),
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The claims of a ticket for ``scope``: valid by default, a new ``jti``; ``drop`` removes required claims, ``extra``
    adds others. Integer times, ``iat`` ``iat_offset`` seconds from the wall clock now, ``exp`` ``lifetime`` after it."""
    iat = int(time.time()) + iat_offset
    claims: dict[str, Any] = {"aud": aud, "scope": scope, "iat": iat, "exp": iat + lifetime, "jti": new_jti() if jti is None else jti, **(extra or {})}
    for name in drop:
        del claims[name]
    return claims


def ticket(scope: str, *, key: SigningKey = KEY_A, kid: str | None = None, typ: str = TICKET_TYP, **claims: Any) -> Ticket:
    """A ticket for ``scope`` signed by ``key`` with EdDSA, its header naming ``kid`` (the key's own by default) and
    ``typ``; ``claims`` as ``claims_for`` takes them."""
    payload = claims_for(scope, **claims)
    header = {"typ": typ, "kid": key.kid if kid is None else kid}
    return Ticket(jwt.encode(payload, key.private, algorithm=TICKET_ALGORITHM, headers=header), header["kid"], payload.get("jti"))


def unsigned(scope: str) -> str:
    """A ticket with ``alg: none`` and no signature at all."""
    return jwt.encode(claims_for(scope), None, algorithm="none", headers={"typ": TICKET_TYP, "kid": KEY_A.kid})


def keyed_with_the_public_key(scope: str) -> str:
    """A ticket with ``alg: HS256`` whose HMAC key is key A's public half as written: the algorithm confusion a published
    key invites."""
    return jwt.encode(claims_for(scope), KEY_A.public_text, algorithm="HS256", headers={"typ": TICKET_TYP, "kid": KEY_A.kid})


def altered(value: str, **changes: Any) -> str:
    """``value`` with claims changed after signing, its signature kept."""
    header, payload, signature = value.split(".")
    claims = {**json.loads(from_b64url(payload)), **changes}
    return ".".join((header, b64url(json.dumps(claims, separators=(",", ":")).encode("utf-8")), signature))


def not_a_jws() -> str:
    """Three segments of random base64url: the shape of a JWS, nothing of its content."""
    return ".".join(secrets.token_urlsafe(18) for _ in range(3))


def other_scope(scope: str) -> str:
    """The scope after ``scope`` in ``SCOPES``, in a circle: never ``scope`` itself."""
    return SCOPES[(SCOPES.index(scope) + 1) % len(SCOPES)]


def a_token() -> str:
    """A token as the documentation suggests one (``openssl rand -hex 32``): 64 characters, new at each call."""
    return secrets.token_hex(32)


#: A ticket with a valid signature that the instance refuses, by case: its code, and how to build one for a scope. Each
#: has one defect only, far from every edge.
TICKET_REFUSALS: dict[str, tuple[str, Callable[[str], Ticket]]] = {
    "expired": (EXPIRED, lambda scope: ticket(scope, iat_offset=EXPIRED_IAT_OFFSET)),
    "not-yet-valid": (NOT_YET_VALID, lambda scope: ticket(scope, iat_offset=EARLY_IAT_OFFSET)),
    "wrong-audience": (WRONG_AUDIENCE, lambda scope: ticket(scope, aud=OTHER_AUDIENCE)),
    "wrong-scope": (WRONG_SCOPE, lambda scope: ticket(other_scope(scope))),
    "lifetime-over-300-seconds": (INVALID, lambda scope: ticket(scope, lifetime=LONG_LIFETIME)),
    "without-jti": (INVALID, lambda scope: ticket(scope, drop=("jti",))),
    "unknown-kid": (UNKNOWN_KEY, lambda scope: ticket(scope, key=KEY_C, kid=UNKNOWN_KID)),
}

#: A ticket that proves nothing, by kind: how to build one for a scope, as the value presented. Each is otherwise a
#: valid ticket for that scope.
OVERSIZED = "over-2048-bytes"
UNVERIFIABLE: dict[str, Callable[[str], str]] = {
    "alg-none": unsigned,
    "hs256-keyed-with-the-public-key": keyed_with_the_public_key,
    "typ-jwt": lambda scope: ticket(scope, typ="JWT").value,
    "signed-by-a-key-not-configured-under-a-known-kid": lambda scope: ticket(scope, key=KEY_C, kid=KEY_A.kid).value,
    "payload-altered-after-signing": lambda scope: altered(ticket(other_scope(scope)).value, scope=scope),
    OVERSIZED: lambda scope: ticket(scope, extra={"padding": "x" * 2100}).value,
    "not-a-jws": lambda scope: not_a_jws(),
}


# =============================================================================
# THE ENVIRONMENT, THE LIMITER, THE TEST ROUTES AND THE PANEL OF A TEST
# =============================================================================


def access_module() -> ModuleType:
    """CP1's ``access.py``, which CP2 extends: imported when a fixture needs it, so the file collects whatever it holds."""
    try:
        return importlib.import_module(ACCESS_MODULE)
    except ModuleNotFoundError as error:
        # The module or its package missing is CP1's red; a module it imports missing is a finding, raised as it is.
        if error.name not in (ACCESS_MODULE, ACCESS_MODULE.rpartition(".")[0]):
            raise
    pytest.fail(f"H-61: {ACCESS_FILE} is missing (checkpoint 1)")


@pytest.fixture(autouse=True)
def no_inherited_panel_configuration(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Every test starts with no token, no keys, no skew and no public address, whatever the runner's environment holds;
    in test mode, its data directory ``tmp_path/data`` (where the registry lives), and the self-hosted profile."""
    for name in PANEL_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / DATA_FOLDER))
    monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")


class FakeClock:
    """The limiter's clock: it moves only when the test moves it."""

    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class RecordingLimiter(SlidingWindowLimiter):
    """``SlidingWindowLimiter(20, 600)`` as CP1 builds ``PANEL_ATTEMPTS``, on the fake clock, recording each call the code
    under test makes, as ``(method, key)``. What the test reads goes through ``held`` and ``len``, which record nothing."""

    def __init__(self, clock: FakeClock) -> None:
        super().__init__(PANEL_LIMIT, PANEL_WINDOW_SECONDS, clock=clock)
        self.calls: list[tuple[str, Any]] = []

    def peek(self, key: Hashable = None, *, limit: int | None = None) -> RateDecision:
        self.calls.append(("peek", key))
        return super().peek(key, limit=limit)

    def hit(self, key: Hashable = None, *, limit: int | None = None) -> RateDecision:
        self.calls.append(("hit", key))
        return super().hit(key, limit=limit)

    def count(self, key: Hashable = None) -> int:
        self.calls.append(("count", key))
        return super().count(key)

    def reset(self, key: Hashable = None) -> None:
        self.calls.append(("reset", key))
        super().reset(key)

    def clear(self) -> None:
        self.calls.append(("clear", None))
        super().clear()

    def held(self, key: Hashable) -> int:
        """The hits of ``key`` in the window now, read by the test: not recorded."""
        return SlidingWindowLimiter.count(self, key)


#: The test routes' endpoints, built once per process from the access module (``panel_access`` gives the same object for
#: the same scope) and kept: FastAPI caches the context of an endpoint by its ``id()``, which a freed one could lend.
_ENDPOINTS: dict[str, Callable[..., Any]] = {}


def _served(request: Request, scope: str, caller: Any) -> dict[str, str]:
    """What a test route does once the dependency let the request through: record the caller it got, answer its scope."""
    request.app.state.served.append((scope, caller))
    return {"served": scope}


def _endpoint(access: ModuleType, scope: str) -> Callable[..., Any]:
    """The test route of ``scope``: its caller is ``Depends(panel_access(PanelScope(scope)))``."""
    if scope not in _ENDPOINTS:
        dependency = access.panel_access(access.PanelScope(scope))

        async def route(request: Request, caller: Annotated[Any, Depends(dependency)]) -> dict[str, str]:
            return _served(request, scope, caller)

        route.__name__ = route.__qualname__ = f"hpt_test_{scope}_route"
        _ENDPOINTS[scope] = route
    return _ENDPOINTS[scope]


def panel_app(access: ModuleType) -> FastAPI:
    """A fresh app holding the three test routes and nothing else."""
    app = FastAPI()
    app.state.served = []
    for scope in SCOPES:
        method, path = ROUTES[scope]
        app.add_api_route(path, _endpoint(access, scope), methods=[method])
    return app


def request_line(scope: str) -> tuple[str, str]:
    """The method and a path of ``scope``'s test route: the backup one with a job id of its own at each call."""
    method, template = ROUTES[scope]
    return method, template.replace("{job_id}", f"job-{uuid.uuid4().hex[:12]}")


def rate_key(client: tuple[str, int]) -> str | None:
    """The key of a peer, as ``client_rate_key`` gives it."""
    return client_address_module.client_rate_key(client[0])


@contextmanager
def client_address_state_kept() -> Iterator[None]:
    """What a request leaves in ``client_address``'s process state, put back as it was: the forwarding headers noted from
    peers nobody trusts and the warned flag. The module's own containers, in place."""
    module = client_address_module
    noted = {peer_class: set(names) for peer_class, names in module._untrusted_forwarding.items()}
    warned = list(module._warned)
    try:
        yield
    finally:
        for peer_class, names in module._untrusted_forwarding.items():
            names.clear()
            names.update(noted.get(peer_class, set()))
        module._warned[:] = warned


@dataclass
class Panel:
    """What a §3 test works with: the access module, its fresh app, the fake clock, the recording limiter in place of
    ``PANEL_ATTEMPTS``, the test's data directory, and the tokens it configured, which no answer nor line may hold."""

    access: ModuleType
    app: FastAPI
    clock: FakeClock
    limiter: RecordingLimiter
    monkeypatch: pytest.MonkeyPatch
    data_dir: Path
    header_canary: str = field(default_factory=lambda: f"hpt-header-{uuid.uuid4().hex}")
    configured: list[str] = field(default_factory=list)

    @property
    def registry(self) -> Path:
        """Where the contract keeps the ``jti`` registry: ``DATA_DIR/panel_tickets.sqlite3``."""
        return self.data_dir / REGISTRY_FILE

    def new_token(self, scope: str) -> str:
        """A new token for ``scope``, set in its variable."""
        token = a_token()
        self.monkeypatch.setenv(VARIABLES[scope], token)
        self.configured.append(token)
        return token

    def set_keys(self, value: str) -> None:
        """``LIBREFOLIO_PANEL_PUBLIC_KEYS`` as ``value``."""
        self.monkeypatch.setenv(KEYS_VARIABLE, value)


@pytest.fixture
def panel(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Panel]:
    """The access module with ``PANEL_ATTEMPTS`` replaced by a recording limiter on a fake clock, a fresh app of the three
    test routes, ``LIBREFOLIO_PUBLIC_URL`` set (the keys, unset, leave L2 off), the data directory created in
    ``tmp_path`` and checked to be the one the instance reads, ``LIBREFOLIO_CLIENT_IP_HEADER`` read as unset whatever the
    lane sets (``_configured_header`` replaced), and ``client_address``'s process state put back after the test."""
    access = access_module()
    missing = [name for name in ("PanelScope", "PanelCaller", "panel_access", "PANEL_ATTEMPTS", "logger") if getattr(access, name, None) is None]
    if missing:
        pytest.fail(f"H-61: {ACCESS_FILE} gives none of {missing} (checkpoint 1)")
    data_dir = (tmp_path / DATA_FOLDER).resolve()
    data_dir.mkdir()
    assert get_data_dir() == data_dir, f"Precondition: the data directory, where the jti registry lives, is this test's own in tmp_path, not {get_data_dir()}"
    clock = FakeClock(START)
    limiter = RecordingLimiter(clock)
    monkeypatch.setattr(access, "PANEL_ATTEMPTS", limiter)
    monkeypatch.setattr(client_address_module, "_configured_header", lambda: None)
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)
    with client_address_state_kept():
        yield Panel(access=access, app=panel_app(access), clock=clock, limiter=limiter, monkeypatch=monkeypatch, data_dir=data_dir)


# =============================================================================
# ONE REQUEST, ITS ANSWER, ITS LINES AND ITS CALLER
# =============================================================================


@dataclass(frozen=True)
class Exchange:
    """One request to the panel's app: the answer, the events logged while it ran, the calls the limiter received and the
    callers the test routes got meanwhile."""

    scope: str
    method: str
    path: str
    response: httpx.Response
    events: list[dict[str, Any]]
    limiter_calls: list[tuple[str, Any]]
    served: list[tuple[str, Any]]

    @property
    def answer(self) -> tuple[int, object]:
        """Status and body: the JSON of a JSON answer, the first bytes of any other, so a red always reads."""
        if self.response.headers.get("content-type", "").startswith("application/json"):
            return self.response.status_code, self.response.json()
        return self.response.status_code, self.response.content[:200]

    @property
    def challenge(self) -> str | None:
        return self.response.headers.get("www-authenticate")

    @property
    def retry_after(self) -> str | None:
        return self.response.headers.get("retry-after")

    @property
    def panel_lines(self) -> list[dict[str, Any]]:
        """The ``Hosting panel request`` lines, in order."""
        return [event for event in self.events if event.get("event") == PANEL_LINE]

    def shows(self, values: Iterable[str]) -> list[str]:
        """Where a value of ``values`` shows: the body, the headers (names and values), the log (every key and value of
        every line). Empty values are skipped, and a value is named by its position, never written out."""
        headers = "\n".join(f"{name}: {value}" for name, value in self.response.headers.multi_items())
        log = "\n".join([repr(self.events), *(f"{key}={value}" for event in self.events for key, value in event.items())])
        places = []
        for index, value in enumerate(values):
            if not value:
                continue
            found = {"body": value.encode("utf-8") in self.response.content, "headers": value in headers, "log": value in log}
            places.extend(f"value #{index} in the {place}" for place, shown in found.items() if shown)
        return places


def module_logger(access: ModuleType) -> Any:
    """The access module's own logger, on which the contract logs ``Hosting panel request``."""
    logger = getattr(access, "logger", None)
    if logger is None or not callable(getattr(logger, "debug", None)):
        pytest.fail(f"H-61: {ACCESS_FILE} has no module-level logger, on which «{PANEL_LINE}» is logged")
    return logger


def credential_secrets(authorization: str | None) -> list[str]:
    """What a request's ``Authorization`` gives away wherever it shows: the whole value, the credential presented and,
    for a ticket, its signature."""
    presented = authorization.partition(" ")[2].strip() if authorization else ""
    if not presented:
        return []
    found = [authorization, presented]
    signature = presented.rpartition(".")[2]
    if presented.count(".") == 2 and len(signature) >= SIGNATURE_MIN_LENGTH:
        found.append(signature)
    return found


def secret_values(panel: Panel, authorization: str | None, headers: Mapping[str, str], params: Mapping[str, str] | None, client: tuple[str, int]) -> list[str]:
    """What no answer and no line may hold: the tokens the test configured, the credential presented (the whole
    ``Authorization`` value, the ticket, its signature), every other header value sent, the query's values, the client's
    address and its key."""
    sent = [value for name, value in headers.items() if name != "Authorization"]
    return [*panel.configured, *credential_secrets(authorization), *sent, *(params or {}).values(), client[0], rate_key(client) or ""]


async def _request(transport: httpx.ASGITransport, method: str, path: str, headers: Mapping[str, str], params: Mapping[str, str] | None) -> httpx.Response:
    """One request through ``transport``, within ``CALL_SECONDS``."""
    try:
        async with asyncio.timeout(CALL_SECONDS):
            async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as http:
                return await http.request(method, path, headers=headers, params=params)
    except TimeoutError:
        pytest.fail(f"{method} {path}: no answer within {CALL_SECONDS} s")


async def send(panel: Panel, scope: str, *, authorization: str | None = None, params: Mapping[str, str] | None = None, client: tuple[str, int] = PEER) -> Exchange:
    """A request to ``scope``'s test route from ``client``, in this process: ``Authorization`` only when given, the canary
    header always; the log captured meanwhile, behind a canary logged through the access module's own logger. Ends on
    what every request of this file must hold: no configured token, no credential presented, no header value, no query
    value and not the client's address in the answer, its headers or a line."""
    method, path = request_line(scope)
    sent = {CANARY_HEADER: panel.header_canary}
    if authorization is not None:
        sent["Authorization"] = authorization
    calls_mark, served_mark = len(panel.limiter.calls), len(panel.app.state.served)
    transport = httpx.ASGITransport(app=panel.app, raise_app_exceptions=False, client=client)
    with capture_logs(processors=[merge_contextvars]) as events:
        module_logger(panel.access).debug(CAPTURE_CANARY)
        assert any(event.get("event") == CAPTURE_CANARY for event in events), f"barrier: the access module's logger does not reach capture_logs, so what this test reads of the log proves nothing: {events}"
        response = await _request(transport, method, path, sent, params)
    captured = [event for event in events if event.get("event") != CAPTURE_CANARY]
    exchange = Exchange(scope, method, path, response, captured, panel.limiter.calls[calls_mark:], panel.app.state.served[served_mark:])
    leaked = exchange.shows(secret_values(panel, authorization, sent, params, client))
    assert not leaked, f"{method} {path}: a secret left the server (a token, a ticket, its signature, the Authorization header, a header, the query or the client's address): {leaked}"
    return exchange


def accepted_line(exchange: Exchange, by: Ticket | None = None) -> dict[str, Any]:
    """The INFO line of an accepted request, whole: CP1's for the token; ``credential`` ``ticket``, ``kid`` and ``jti``
    for a ticket."""
    line: dict[str, Any] = {"event": PANEL_LINE, "log_level": "info", "scope": exchange.scope, "method": exchange.method, "path": exchange.path, "outcome": "accepted", "credential": "token" if by is None else "ticket"}
    if by is not None:
        line.update(kid=by.kid, jti=by.jti)
    return line


#: What a view of a warning line says of its credential and of its keys.
KNOWN_CREDENTIAL = "credential is token or ticket"
STRAY_KEYS = "keys outside the contract"


def warning_view(exchange: Exchange, *pinned: str) -> list[dict[str, Any]]:
    """The panel lines of ``exchange`` as far as the contract pins a line it does not give whole: the event, the level,
    the scope, the method, the path and the fields ``pinned``; whether the credential is ``token`` or ``ticket``; the keys
    outside CP1's fields plus ``kid`` and ``jti``."""
    names = ("event", "log_level", "scope", "method", "path", *pinned)
    return [{**{name: line.get(name, ABSENT) for name in names}, KNOWN_CREDENTIAL: line.get("credential") in CREDENTIALS, STRAY_KEYS: sorted(set(line) - TICKET_LINE_KEYS)} for line in exchange.panel_lines]


def warning_line(exchange: Exchange, **pinned: Any) -> dict[str, Any]:
    """The view ``warning_view`` must give of the one WARNING line of ``exchange``, with the fields ``pinned``."""
    return {"event": PANEL_LINE, "log_level": "warning", "scope": exchange.scope, "method": exchange.method, "path": exchange.path, **pinned, KNOWN_CREDENTIAL: True, STRAY_KEYS: []}


def ticket_refusal(exchange: Exchange) -> tuple[Any, ...]:
    """The answer to a signed ticket refused, as far as the contract gives it: the status, the body's keys, the detail's
    keys, the code, and whether the message is a text; any other answer as it is."""
    status, body = exchange.answer
    detail = body.get("detail") if isinstance(body, dict) else None
    if not isinstance(detail, dict):
        return status, body
    message = detail.get("message")
    return status, sorted(body), sorted(detail), detail.get("code"), isinstance(message, str) and bool(message.strip())


def refused_with(code: str, status: int = 401) -> tuple[Any, ...]:
    """What ``ticket_refusal`` must give for an answer ``status`` (401 by default) with ``code``:
    ``{"detail": {"code": code, "message": <text>}}``."""
    return status, ["detail"], ["code", "message"], code, True


def caller_view(caller: Any) -> dict[str, Any]:
    """The caller a test route got, as the contract describes it; an attribute it lacks shows as ``ABSENT``."""
    scope = getattr(caller, "scope", ABSENT)
    return {
        "class": type(caller).__name__,
        "scope": str(getattr(scope, "value", scope)),
        "scope class": type(scope).__name__,
        "credential": getattr(caller, "credential", ABSENT),
        "kid": getattr(caller, "kid", ABSENT),
        "jti": getattr(caller, "jti", ABSENT),
    }


def expected_caller(scope: str, credential: str, kid: str | None = None, jti: str | None = None) -> dict[str, Any]:
    """``PanelCaller(PanelScope(scope), credential, kid, jti)`` as ``caller_view`` shows it."""
    return {"class": "PanelCaller", "scope": scope, "scope class": "PanelScope", "credential": credential, "kid": kid, "jti": jti}


def callers(exchange: Exchange) -> list[dict[str, Any]]:
    """The callers the test routes got during ``exchange``, as ``caller_view`` shows them."""
    return [caller_view(caller) for _, caller in exchange.served]


# =============================================================================
# HPT-001..004 (§3, §1): the scopes
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", SCOPES)
async def test_the_keys_alone_turn_a_scope_on_and_a_valid_ticket_opens_it(panel: Panel, scope: str) -> None:
    """HPT-001 (§3): a scope is on when its token or the keys are set. Its token unset, with the keys unset or blank it
    is off, as in CP1: 404 ``Not Found`` to a valid ticket, no line, the limiter not read, the route never run. With the
    keys set it is on: a request without a credential gets the scope's 401 with ``WWW-Authenticate: Bearer`` and one
    WARNING line ``refused``/``missing``, and is counted; a valid ticket for the scope gets 200, the route's caller
    ``PanelCaller(scope, credential="ticket", kid, jti)``, one INFO line whole with the ticket's ``kid`` and ``jti``, the
    limiter peeked and never hit. For the status scope, that is ``GET /panel/status`` with the keys alone."""
    print_section(f"H-61 CP2 §3: the {scope} scope with the keys alone")
    key = rate_key(PEER)
    unset = await send(panel, scope, authorization=ticket(scope).authorization)
    panel.set_keys("   ")
    blank = await send(panel, scope, authorization=ticket(scope).authorization)
    panel.set_keys(keys_value(KEY_A))
    missing = await send(panel, scope)
    valid = ticket(scope)
    accepted = await send(panel, scope, authorization=valid.authorization)

    off = {"keys unset": unset, "keys blank": blank}
    states = {label: (exchange.answer, exchange.events, exchange.limiter_calls, exchange.served) for label, exchange in off.items()}
    assert states == dict.fromkeys(off, (OFF_ANSWER, [], [], [])), f"Barrier: without its token and without keys the {scope} scope is off, as in CP1: 404, no line, the limiter not read, the route not run: {states}"
    assert (missing.answer, missing.challenge) == (UNAUTHORIZED[scope], "Bearer"), f"H-61 CP2 §3: with {KEYS_VARIABLE} set and no token the {scope} scope is on: a request without a credential gets its 401 and a Bearer challenge, not 404: {missing.answer}, {missing.challenge!r}"
    assert missing.limiter_calls == [("peek", key), ("hit", key)], f"a missing credential proves nothing, and is counted: {missing.limiter_calls}"
    assert warning_view(missing, "outcome", "reason") == [warning_line(missing, outcome="refused", reason="missing")], f"one WARNING line, refused/missing: {missing.panel_lines}"
    assert accepted.answer == (200, {"served": scope}), f"H-61 CP2 §3: with the keys alone, a valid {scope} ticket opens the {scope} scope: {accepted.answer}"
    assert callers(accepted) == [expected_caller(scope, "ticket", KEY_A.kid, valid.jti)], f"the route's caller is PanelCaller({scope}, credential='ticket', kid, jti): {callers(accepted)}"
    assert accepted.panel_lines == [accepted_line(accepted, valid)], f"one INFO line, accepted, credential ticket, with the ticket's kid and jti: {accepted.panel_lines}"
    assert (accepted.limiter_calls, panel.limiter.held(key)) == ([("peek", key)], 1), f"an accepted ticket is peeked and never counted: {accepted.limiter_calls}, {panel.limiter.held(key)}"
    print_success(f"{scope}: off without keys; with them on, 401 missing, then 200 with a ticket")


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", SCOPES)
async def test_beside_the_keys_the_token_and_a_ticket_both_open_the_scope_and_a_wrong_token_is_refused(panel: Panel, scope: str) -> None:
    """HPT-002 (§3, decision β): the scope's token and the keys set together. The token is accepted as in CP1: 200, CP1's
    INFO line whole (``credential`` ``token``, no ``kid`` nor ``jti``), the caller ``PanelCaller(scope, "token")`` with
    ``kid`` and ``jti`` None. A valid ticket is accepted too: 200, its INFO line with ``kid`` and ``jti``, the caller's
    ``credential`` ``ticket``. Neither is counted. A wrong token gets the scope's 401 with a Bearer challenge and one
    WARNING line ``refused``, and is counted."""
    print_section(f"H-61 CP2 §3: the {scope} token and the keys together")
    token = panel.new_token(scope)
    panel.set_keys(keys_value(KEY_A))
    key = rate_key(PEER)
    valid = ticket(scope)

    by_token = await send(panel, scope, authorization=f"Bearer {token}")
    by_ticket = await send(panel, scope, authorization=valid.authorization)
    wrong = await send(panel, scope, authorization=f"Bearer {a_token()}")

    assert by_token.answer == (200, {"served": scope}) and by_token.panel_lines == [accepted_line(by_token)], f"the token is accepted as in CP1, its line whole: {by_token.answer}, {by_token.panel_lines}"
    assert by_ticket.answer == (200, {"served": scope}), f"H-61 CP2 §3 (β): beside the {scope} token, a valid ticket opens the scope too: {by_ticket.answer}"
    assert by_ticket.panel_lines == [accepted_line(by_ticket, valid)], f"one INFO line, accepted, credential ticket, with kid and jti: {by_ticket.panel_lines}"
    seen = {"token": callers(by_token), "ticket": callers(by_ticket)}
    assert seen == {"token": [expected_caller(scope, "token")], "ticket": [expected_caller(scope, "ticket", KEY_A.kid, valid.jti)]}, f"H-61 CP2 §3: PanelCaller gains kid and jti, both None for the token: {seen}"
    assert (wrong.answer, wrong.challenge, wrong.served) == (UNAUTHORIZED[scope], "Bearer", []), f"a wrong token gets the scope's 401 and a Bearer challenge: {wrong.answer}, {wrong.challenge!r}"
    assert warning_view(wrong, "outcome") == [warning_line(wrong, outcome="refused")], f"one WARNING line, refused: {wrong.panel_lines}"
    calls = {"token": by_token.limiter_calls, "ticket": by_ticket.limiter_calls, "wrong token": wrong.limiter_calls}
    assert calls == {"token": [("peek", key)], "ticket": [("peek", key)], "wrong token": [("peek", key), ("hit", key)]}, f"only the wrong token is counted: {calls}"
    print_success(f"{scope}: the token 200, a ticket 200, a wrong token 401 and counted")


#: HPT-003: two keys in the variable, separated by a comma, or with spaces around the entries, which are ignored.
TWO_KEYS = [
    pytest.param(keys_value(KEY_A, KEY_B), id="separated-by-a-comma"),
    pytest.param(f"  {KEY_A.entry} ,  {KEY_B.entry}  ", id="spaces-around-the-entries"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("keys", TWO_KEYS)
async def test_with_two_keys_each_kid_chooses_its_own_key(panel: Panel, keys: str) -> None:
    """HPT-003 (§1, §3): two keys, as a rotation holds them. A ticket signed by each, under its own ``kid``, opens the
    scope, its line and its caller naming that ``kid``; a ticket signed by key B under key A's ``kid`` does not verify:
    the scope's 401 of today, no code of its own, counted."""
    print_section("H-61 CP2 §1/§3: two keys, each kid chooses its key")
    panel.set_keys(keys)
    key = rate_key(PEER)
    signed = {"key A": ticket(WAKE, key=KEY_A), "key B": ticket(WAKE, key=KEY_B)}
    crossed = ticket(WAKE, key=KEY_B, kid=KEY_A.kid)

    accepted = {label: await send(panel, WAKE, authorization=item.authorization) for label, item in signed.items()}
    refused = await send(panel, WAKE, authorization=crossed.authorization)

    answers = {label: exchange.answer for label, exchange in accepted.items()}
    assert answers == dict.fromkeys(signed, (200, {"served": WAKE})), f"H-61 CP2 §1: with two keys, a ticket of each opens the scope: {answers}"
    lines = {label: exchange.panel_lines for label, exchange in accepted.items()}
    assert lines == {label: [accepted_line(accepted[label], item)] for label, item in signed.items()}, f"each INFO line names its own key's kid: {lines}"
    seen = {label: callers(exchange) for label, exchange in accepted.items()}
    assert seen == {label: [expected_caller(WAKE, "ticket", item.kid, item.jti)] for label, item in signed.items()}, f"each caller carries its ticket's kid and jti: {seen}"
    assert (refused.answer, refused.challenge, refused.served) == (UNAUTHORIZED[WAKE], "Bearer", []), f"key B's signature under key A's kid does not verify: the scope's 401 of today, no code of its own: {refused.answer}"
    assert refused.limiter_calls == [("peek", key), ("hit", key)], f"an unverifiable ticket is counted: {refused.limiter_calls}"
    print_success("key A and key B each accepted under their kid; a crossed signature refused and counted")


#: HPT-004: ``LIBREFOLIO_PUBLIC_URL`` as an admin may write it, and the audience it gives: its canonical origin.
AUDIENCES = [
    pytest.param("HTTPS://Folio.Example.COM:443/librefolio/", "https://folio.example.com", id="https-capitals-default-port-a-path"),
    pytest.param("http://Folio.Example.com:8080", "http://folio.example.com:8080", id="http-capitals-another-port"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("public_url", "origin"), AUDIENCES)
async def test_the_audience_is_the_canonical_origin_of_the_public_url(panel: Panel, public_url: str, origin: str) -> None:
    """HPT-004 (§1, §3): the dependency checks ``aud`` against the origin of ``LIBREFOLIO_PUBLIC_URL``, in lower case,
    without a default port or a path: a ticket for that origin is accepted; one for the address as written, or for the
    origin with a trailing slash, gets ``panel_ticket_wrong_audience``."""
    print_section(f"H-61 CP2 §1/§3: the audience of {public_url}")
    panel.monkeypatch.setenv(PUBLIC_URL_VARIABLE, public_url)
    panel.set_keys(keys_value(KEY_A))
    canonical = ticket(STATUS, aud=origin)
    others = {"the address as written": ticket(STATUS, aud=public_url), "the origin with a trailing slash": ticket(STATUS, aud=f"{origin}/")}

    accepted = await send(panel, STATUS, authorization=canonical.authorization)
    refused = {label: await send(panel, STATUS, authorization=item.authorization) for label, item in others.items()}

    assert accepted.answer == (200, {"served": STATUS}) and accepted.panel_lines == [accepted_line(accepted, canonical)], f"H-61 CP2 §1: the audience is {origin!r}, the origin of {public_url!r}: a ticket for it is accepted: {accepted.answer}, {accepted.panel_lines}"
    verdicts = {label: ticket_refusal(exchange) for label, exchange in refused.items()}
    assert verdicts == dict.fromkeys(others, refused_with(WRONG_AUDIENCE)), f"aud is compared whole with the canonical origin: {verdicts}"
    print_success(f"{public_url} gives the audience {origin}")


# =============================================================================
# HPT-010..013 (§2 through §3): the refusals
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("case", list(TICKET_REFUSALS))
@pytest.mark.parametrize("scope", SCOPES)
async def test_a_signed_ticket_refused_gets_its_own_code_and_is_never_counted(panel: Panel, scope: str, case: str) -> None:
    """HPT-010 (§2, §3): a ticket with a valid signature, refused — expired, not yet valid, for another audience, for
    another scope, living over 300 s, without a ``jti`` — gets 401 ``{"detail": {"code", "message"}}`` with its own
    ``panel_ticket_*`` code, ``WWW-Authenticate: Bearer``, and ``Retry-After: 5`` for ``panel_ticket_not_yet_valid``
    only; one WARNING line ``refused``; the route never runs; the limiter is peeked and never hit, as whoever holds the
    key sent it. A ``kid`` the keys do not know gets ``panel_ticket_unknown_key`` the same way, its counting left open.
    Barrier: the scope then accepts a valid ticket."""
    code, build = TICKET_REFUSALS[case]
    print_section(f"H-61 CP2 §2/§3: the {scope} scope, a ticket {case}: {code}")
    panel.set_keys(keys_value(KEY_A))
    key = rate_key(PEER)

    refused = await send(panel, scope, authorization=build(scope).authorization)
    valid = ticket(scope)
    accepted = await send(panel, scope, authorization=valid.authorization)

    assert ticket_refusal(refused) == refused_with(code), f"H-61 CP2 §2: a ticket {case} gets 401 {{'detail': {{'code': {code!r}, 'message': <a text>}}}}: {refused.answer}"
    headers = (refused.challenge, refused.retry_after)
    expected_headers = ("Bearer", NOT_YET_VALID_RETRY_AFTER if code == NOT_YET_VALID else None)
    assert headers == expected_headers, f"WWW-Authenticate and Retry-After of {code}: {headers}, expected {expected_headers}"
    assert warning_view(refused, "outcome") == [warning_line(refused, outcome="refused")], f"one WARNING line, refused: {refused.panel_lines}"
    assert refused.served == [], "the route never runs for a refused ticket"
    assert accepted.answer == (200, {"served": scope}) and accepted.panel_lines == [accepted_line(accepted, valid)], f"Barrier: the scope then accepts a valid ticket: {accepted.answer}, {accepted.panel_lines}"
    if code == UNKNOWN_KEY:
        # Left open by the contract: a kid the keys do not know proves no signature, yet the ticket is not «unverifiable»
        assert refused.limiter_calls[:1] == [("peek", key)], f"the limiter is read first: {refused.limiter_calls}"
    else:
        assert (refused.limiter_calls, panel.limiter.held(key)) == ([("peek", key)], 0), f"H-61 CP2 §3: a ticket with a valid signature, refused, is never counted: {refused.limiter_calls}, {panel.limiter.held(key)}"
    print_success(f"{scope}, {case}: 401 {code}")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", list(UNVERIFIABLE))
@pytest.mark.parametrize("scope", SCOPES)
async def test_an_unverifiable_ticket_gets_the_scopes_401_and_is_counted(panel: Panel, scope: str, kind: str) -> None:
    """HPT-011 (§2, §3): a ticket that proves nothing — ``alg: none``; HS256 keyed with the public key as written; ``typ``
    ``JWT``; signed by a key not configured, under a known ``kid``; its payload altered after signing; over 2048 bytes,
    though validly signed; not a JWS — gets the scope's 401 of today, whole, with a Bearer challenge and no
    ``Retry-After``: no code of its own. One WARNING line ``refused``; the route never runs; the refusal is counted.
    Barrier: the scope then accepts a valid ticket."""
    print_section(f"H-61 CP2 §2/§3: the {scope} scope, an unverifiable ticket: {kind}")
    panel.set_keys(keys_value(KEY_A))
    key = rate_key(PEER)
    value = UNVERIFIABLE[kind](scope)
    size = len(value.encode("utf-8"))
    assert (size > TICKET_MAX_BYTES) == (kind == OVERSIZED), f"Precondition: only the {OVERSIZED} ticket is over {TICKET_MAX_BYTES} bytes: {kind}, {size} bytes"

    refused = await send(panel, scope, authorization=f"Bearer {value}")
    valid = ticket(scope)
    accepted = await send(panel, scope, authorization=valid.authorization)

    assert (refused.answer, refused.challenge, refused.retry_after) == (UNAUTHORIZED[scope], "Bearer", None), f"H-61 CP2 §2: an unverifiable ticket ({kind}) gets the {scope} scope's 401 of today, no code of its own: {refused.answer}, {refused.challenge!r}, {refused.retry_after!r}"
    assert warning_view(refused, "outcome") == [warning_line(refused, outcome="refused")], f"one WARNING line, refused: {refused.panel_lines}"
    assert refused.served == [], "the route never runs for an unverifiable ticket"
    assert (refused.limiter_calls, panel.limiter.held(key)) == ([("peek", key), ("hit", key)], 1), f"H-61 CP2 §3: an unverifiable ticket proves nothing, and is counted: {refused.limiter_calls}, {panel.limiter.held(key)}"
    assert accepted.answer == (200, {"served": scope}), f"Barrier: the scope then accepts a valid ticket: {accepted.answer}"
    print_success(f"{scope}, {kind}: the scope's 401, counted")


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", SCOPES)
async def test_a_ticket_opens_its_scope_once(panel: Panel, scope: str) -> None:
    """HPT-012 (§2, §3): ``verify_ticket``, then the registry. A ticket first presented to another scope's route gets
    ``panel_ticket_wrong_scope`` and keeps its ``jti``: it then opens its own scope, once. The same ticket again, or
    another ticket with its ``jti``, gets 401 ``panel_ticket_replayed`` with a Bearer challenge and one WARNING line; the
    route never runs; neither is counted, nor the refusal for the wrong scope: each has a valid signature. A ticket with
    a new ``jti`` opens the scope. The registry is ``panel_tickets.sqlite3`` in the data directory, in ``tmp_path``."""
    print_section(f"H-61 CP2 §2/§3: the {scope} scope, a ticket used once")
    panel.set_keys(keys_value(KEY_A))
    key = rate_key(PEER)
    once = ticket(scope)
    same_jti = ticket(scope, jti=once.jti, iat_offset=VALID_IAT_OFFSET - 10)
    assert same_jti.value != once.value and same_jti.jti == once.jti, "Precondition: another ticket, with the same jti"

    elsewhere = await send(panel, other_scope(scope), authorization=once.authorization)
    first = await send(panel, scope, authorization=once.authorization)
    replays = {"the same ticket again": await send(panel, scope, authorization=once.authorization), "another ticket with its jti": await send(panel, scope, authorization=same_jti.authorization)}
    fresh = ticket(scope)
    renewed = await send(panel, scope, authorization=fresh.authorization)

    assert ticket_refusal(elsewhere) == refused_with(WRONG_SCOPE), f"presented first to the {other_scope(scope)} route, the ticket is refused for its scope: {elsewhere.answer}"
    assert first.answer == (200, {"served": scope}) and first.panel_lines == [accepted_line(first, once)], f"H-61 CP2 §2: refused before the registry, the ticket kept its jti, and opens its own scope: {first.answer}, {first.panel_lines}"
    verdicts = {label: (ticket_refusal(exchange), exchange.challenge, exchange.served) for label, exchange in replays.items()}
    assert verdicts == dict.fromkeys(replays, (refused_with(REPLAYED), "Bearer", [])), f"H-61 CP2 §2: a jti already accepted gets panel_ticket_replayed, and the route never runs: {verdicts}"
    lines = {label: warning_view(exchange, "outcome") for label, exchange in replays.items()}
    assert lines == {label: [warning_line(exchange, outcome="refused")] for label, exchange in replays.items()}, f"one WARNING line, refused, each: {lines}"
    calls = {label: exchange.limiter_calls for label, exchange in {"for another scope": elsewhere, **replays}.items()}
    assert calls == dict.fromkeys(calls, [("peek", key)]) and panel.limiter.held(key) == 0, f"H-61 CP2 §3: a replay, or a ticket for another scope, has a valid signature: never counted: {calls}"
    assert renewed.answer == (200, {"served": scope}) and callers(renewed) == [expected_caller(scope, "ticket", KEY_A.kid, fresh.jti)], f"a ticket with a new jti opens the scope: {renewed.answer}, {callers(renewed)}"
    assert panel.registry.is_file(), f"H-61 CP2 §2: the registry is DATA_DIR/{REGISTRY_FILE}, here in tmp_path; the data directory holds {sorted(path.name for path in panel.data_dir.iterdir())}"
    print_success(f"{scope}: accepted once, then panel_ticket_replayed twice, nothing counted")


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", SCOPES)
async def test_a_registry_out_of_reach_answers_503_to_a_ticket_and_never_to_the_token(panel: Panel, scope: str) -> None:
    """HPT-013 (§2, §3): the registry cannot be reached (a folder stands where its file should be): a valid ticket gets
    503 with the scope's ``…_unavailable`` code (``{"detail": {"code", "message"}}``, the message left open); the route
    never runs; the refusal is not counted, the signature being valid; one WARNING line. The scope's token, read before
    any ticket, never meets the registry: it opens the scope, CP1's line whole."""
    print_section(f"H-61 CP2 §2/§3: the {scope} scope, the registry out of reach")
    token = panel.new_token(scope)
    panel.set_keys(keys_value(KEY_A))
    panel.registry.mkdir()
    key = rate_key(PEER)
    valid = ticket(scope)
    unavailable_code = UNAVAILABLE[scope][1]["detail"]["code"]

    by_ticket = await send(panel, scope, authorization=valid.authorization)
    by_token = await send(panel, scope, authorization=f"Bearer {token}")

    assert ticket_refusal(by_ticket) == refused_with(unavailable_code, 503), f"H-61 CP2 §2: with the registry out of reach, a valid ticket gets the {scope} scope's 503, {unavailable_code}: {by_ticket.answer}"
    assert (by_ticket.limiter_calls, by_ticket.served) == ([("peek", key)], []), f"a valid signature is never counted, and the route never runs: {by_ticket.limiter_calls}, {by_ticket.served}"
    assert warning_view(by_ticket) == [warning_line(by_ticket)], f"one WARNING line: {by_ticket.panel_lines}"
    assert by_token.answer == (200, {"served": scope}) and by_token.panel_lines == [accepted_line(by_token)], f"H-61 CP2 §3: the token comes first and never meets the registry: {by_token.answer}, {by_token.panel_lines}"
    assert panel.limiter.held(key) == 0, f"nothing counted: {panel.limiter.held(key)}"
    print_success(f"{scope}: a ticket 503, the token 200")


# =============================================================================
# HPT-020..021 (§3): the limiter counts only what proves nothing
# =============================================================================


@pytest.mark.asyncio
async def test_what_proves_nothing_is_counted_and_twenty_of_it_close_the_door_even_to_a_valid_ticket(panel: Panel) -> None:
    """HPT-020 (§3): the backup token and the keys set. Barrier: a valid ticket opens the status scope, peeked and not
    counted. Then 20 requests that prove nothing, across the three scopes: another token (where a token is set, and
    where none is), no ``Authorization``, a valid ticket under ``Basic``, and every kind of unverifiable ticket; each gets
    its scope's 401 with a Bearer challenge, and is counted. The address is then over the limit: a valid ticket and the
    token meet 429 ``panel_too_many_attempts`` with ``Retry-After: 600`` and a WARNING line ``limited``, the limiter only
    peeked, the routes never run. The credential is not looked at: once the window has passed, that same ticket opens
    the scope, its ``jti`` never recorded by the 429."""
    print_section("H-61 CP2 §3: what proves nothing is counted")
    token = panel.new_token(BACKUP)
    panel.set_keys(keys_value(KEY_A))
    key = rate_key(PEER)
    opening = ticket(STATUS)
    proving_nothing: list[tuple[str, str, str | None]] = [
        (BACKUP, "another token", f"Bearer {a_token()}"),
        (WAKE, "another token, the scope having none", f"Bearer {a_token()}"),
        (BACKUP, "no Authorization", None),
        (STATUS, "no Authorization", None),
        (WAKE, "a valid ticket under Basic", f"Basic {ticket(WAKE).value}"),
    ]
    kinds, scopes = itertools.cycle(UNVERIFIABLE.items()), itertools.cycle(SCOPES)
    while len(proving_nothing) < PANEL_LIMIT:
        (kind, make), scope = next(kinds), next(scopes)
        proving_nothing.append((scope, f"unverifiable, {kind}", f"Bearer {make(scope)}"))

    opened = await send(panel, STATUS, authorization=opening.authorization)
    refusals = {f"#{index} {scope}, {label}": await send(panel, scope, authorization=authorization) for index, (scope, label, authorization) in enumerate(proving_nothing)}
    counted = panel.limiter.held(key)
    held_back = ticket(STATUS)
    limited = {"a valid ticket": await send(panel, STATUS, authorization=held_back.authorization), "the token": await send(panel, BACKUP, authorization=f"Bearer {token}")}
    panel.clock.advance(PANEL_WINDOW_SECONDS)
    later = await send(panel, STATUS, authorization=held_back.authorization)

    assert (opened.answer, opened.limiter_calls) == ((200, {"served": STATUS}), [("peek", key)]), f"H-61 CP2 §3: Barrier: with the keys, a valid ticket opens the status scope, peeked and not counted: {opened.answer}, {opened.limiter_calls}"
    answers = {label: (exchange.answer, exchange.challenge) for label, exchange in refusals.items()}
    assert answers == {label: (UNAUTHORIZED[exchange.scope], "Bearer") for label, exchange in refusals.items()}, f"each gets its scope's 401 of today: {answers}"
    calls = {label: exchange.limiter_calls for label, exchange in refusals.items()}
    assert calls == dict.fromkeys(refusals, [("peek", key), ("hit", key)]), f"H-61 CP2 §3: a wrong token, a missing credential and an unverifiable ticket are each counted: {calls}"
    assert counted == PANEL_LIMIT, f"the {PANEL_LIMIT} refusals counted: {counted}"
    verdicts = {label: (exchange.answer, exchange.retry_after, exchange.limiter_calls, exchange.served) for label, exchange in limited.items()}
    assert verdicts == dict.fromkeys(limited, (TOO_MANY, str(PANEL_WINDOW_SECONDS), [("peek", key)], [])), f"over the limit a valid ticket and the token meet 429, the credential not looked at: {verdicts}"
    lines = {label: warning_view(exchange, "outcome", "retry_after") for label, exchange in limited.items()}
    assert lines == {label: [warning_line(exchange, outcome="limited", retry_after=PANEL_WINDOW_SECONDS)] for label, exchange in limited.items()}, f"one WARNING line, limited, each: {lines}"
    assert later.answer == (200, {"served": STATUS}) and callers(later) == [expected_caller(STATUS, "ticket", KEY_A.kid, held_back.jti)], f"once the window has passed, the ticket the 429 met opens the scope: the 429 never recorded its jti: {later.answer}, {callers(later)}"
    print_success(f"{PANEL_LIMIT} refusals proving nothing counted; 429 to a valid ticket, accepted once the window has passed")


@pytest.mark.asyncio
async def test_signed_tickets_refused_are_never_counted_so_a_clock_behind_never_locks_the_panel_out(panel: Panel) -> None:
    """HPT-021 (§3): a ticket with a valid signature comes from whoever holds the key, so its refusal is never counted,
    or a panel whose clock is behind would lock itself out. Barrier: a request without a credential to the backup scope
    is counted on this test's limiter. Then 30 expired tickets from one address, each ``panel_ticket_expired``, never
    429, the limiter only peeked; a valid ticket is accepted; then a ticket not yet valid, one for another audience, one
    for another scope, one living over 300 s, one without a ``jti`` and the accepted one again, each with its own code,
    none counted; a new valid ticket is still accepted, and the count is the barrier's alone."""
    print_section("H-61 CP2 §3: a signed ticket refused is never counted")
    panel.new_token(BACKUP)
    panel.set_keys(keys_value(KEY_A))
    key = rate_key(PEER)

    barrier = await send(panel, BACKUP)
    expired = [await send(panel, STATUS, authorization=ticket(STATUS, iat_offset=EXPIRED_IAT_OFFSET).authorization) for _ in range(EXPIRED_COUNT)]
    valid = ticket(STATUS)
    accepted = await send(panel, STATUS, authorization=valid.authorization)
    others = {
        "not yet valid": (NOT_YET_VALID, ticket(STATUS, iat_offset=EARLY_IAT_OFFSET)),
        "for another audience": (WRONG_AUDIENCE, ticket(STATUS, aud=OTHER_AUDIENCE)),
        "for another scope": (WRONG_SCOPE, ticket(WAKE)),
        "living over 300 seconds": (INVALID, ticket(STATUS, lifetime=LONG_LIFETIME)),
        "without a jti": (INVALID, ticket(STATUS, drop=("jti",))),
        "the accepted one again": (REPLAYED, valid),
    }
    refused = {label: await send(panel, STATUS, authorization=item.authorization) for label, (_, item) in others.items()}
    last = await send(panel, STATUS, authorization=ticket(STATUS).authorization)

    assert (barrier.answer, barrier.limiter_calls) == (UNAUTHORIZED[BACKUP], [("peek", key), ("hit", key)]), f"Barrier: a missing credential is counted on this test's limiter, as in CP1: {barrier.answer}, {barrier.limiter_calls}"
    verdicts = [ticket_refusal(exchange) for exchange in expired]
    assert verdicts == [refused_with(EXPIRED)] * EXPIRED_COUNT, f"H-61 CP2 §2/§3: each of {EXPIRED_COUNT} expired tickets from one address gets panel_ticket_expired, never 429: {Counter(map(repr, verdicts))}"
    assert [exchange.limiter_calls for exchange in expired] == [[("peek", key)]] * EXPIRED_COUNT, "H-61 CP2 §3: an expired ticket has a valid signature: peeked, never counted"
    assert accepted.answer == (200, {"served": STATUS}), f"after {EXPIRED_COUNT} expired tickets from one address, a valid one is accepted: {accepted.answer}"
    seen = {label: ticket_refusal(exchange) for label, exchange in refused.items()}
    assert seen == {label: refused_with(code) for label, (code, _) in others.items()}, f"each signed ticket refused gets its own code: {seen}"
    calls = {label: exchange.limiter_calls for label, exchange in refused.items()}
    assert calls == dict.fromkeys(refused, [("peek", key)]), f"H-61 CP2 §3: none of them is counted: {calls}"
    assert last.answer == (200, {"served": STATUS}), f"a new valid ticket is still accepted: {last.answer}"
    assert panel.limiter.held(key) == 1, f"only the barrier's refusal is counted: {panel.limiter.held(key)}"
    print_success(f"{EXPIRED_COUNT} expired tickets and {len(others)} other refusals of signed tickets: none counted")


# =============================================================================
# HPT-030 (§3): the lines
# =============================================================================


@pytest.mark.asyncio
async def test_no_ticket_signature_or_authorization_reaches_a_line_or_an_answer(panel: Panel) -> None:
    """HPT-030 (§3): every outcome at once, each request with a query canary — a ticket accepted, the token accepted, a
    replay, a missing credential, a wrong token, every signed ticket refused, every unverifiable ticket, wrong tokens up
    to the limit, and a valid ticket limited. No ticket, no signature, no ``Authorization`` value, no token, no header
    or query value and not the client's address is in any answer, header or line: each request checks its own, and at
    the end every credential sent is looked for in every answer and every line. Barriers: each outcome reached, one line
    per request. Every line holds only CP1's fields, plus ``kid`` and ``jti``."""
    print_section("H-61 CP2 §3: no ticket, signature or Authorization anywhere")
    token = panel.new_token(BACKUP)
    panel.set_keys(keys_value(KEY_A))
    key = rate_key(PEER)
    query = {"token": f"canary-q-{uuid.uuid4().hex}"}
    good = ticket(STATUS)
    plan: list[tuple[str, str, str | None, str]] = [
        ("accepted, a ticket", STATUS, good.authorization, "accepted"),
        ("accepted, the token", BACKUP, f"Bearer {token}", "accepted"),
        ("replayed", STATUS, good.authorization, "refused"),
        ("missing", WAKE, None, "refused"),
        ("another token", BACKUP, f"Bearer {a_token()}", "refused"),
    ]
    scopes = itertools.cycle(SCOPES)
    for case, (_, build) in TICKET_REFUSALS.items():
        scope = next(scopes)
        plan.append((f"refused, {case}", scope, build(scope).authorization, "refused"))
    for kind, make in UNVERIFIABLE.items():
        scope = next(scopes)
        plan.append((f"unverifiable, {kind}", scope, f"Bearer {make(scope)}", "refused"))
    held_back = ticket(STATUS)

    exchanges = {label: await send(panel, scope, authorization=authorization, params=query) for label, scope, authorization, _ in plan}
    fillers: list[Exchange] = []
    while panel.limiter.held(key) < PANEL_LIMIT and len(fillers) < PANEL_LIMIT:
        fillers.append(await send(panel, BACKUP, authorization=f"Bearer {a_token()}", params=query))
    limited = await send(panel, STATUS, authorization=held_back.authorization, params=query)

    reached = {label: (exchange.response.status_code, [line.get("outcome") for line in exchange.panel_lines]) for label, exchange in exchanges.items()}
    assert reached == {label: (200 if outcome == "accepted" else 401, [outcome]) for label, _, _, outcome in plan}, f"Precondition: each outcome reached, with its one line: {reached}"
    filled = [exchange.response.status_code for exchange in fillers]
    assert filled == [401] * len(fillers) and panel.limiter.held(key) == PANEL_LIMIT, f"Precondition: wrong tokens up to the limit: {filled}, {panel.limiter.held(key)}"
    assert (limited.response.status_code, [line.get("outcome") for line in limited.panel_lines]) == (429, ["limited"]), f"Precondition: a valid ticket over the limit is limited: {limited.answer}, {limited.panel_lines}"
    everything = [*exchanges.values(), *fillers, limited]
    stray = sorted({name for exchange in everything for line in exchange.panel_lines for name in set(line) - TICKET_LINE_KEYS})
    assert stray == [], f"a line holds nothing but CP1's fields, kid and jti: {stray}"
    presented = [authorization for _, _, authorization, _ in plan if authorization] + [held_back.authorization]
    sent = [value for authorization in presented for value in credential_secrets(authorization)] + [token, query["token"], panel.header_canary]
    places = {label: exchange.shows(sent) for label, exchange in [*exchanges.items(), ("limited", limited)]}
    shown = {label: found for label, found in places.items() if found}
    assert shown == {}, f"a credential sent reached an answer or a line: {shown}"
    print_success(f"{len(everything)} requests, every outcome: no ticket, signature or Authorization anywhere")


# =============================================================================
# HPT-040..043 (§4): the startup check
# =============================================================================


def set_variables(monkeypatch: pytest.MonkeyPatch, variables: Mapping[str, str | None]) -> None:
    """Each variable of ``variables`` set to its value, or removed for None."""
    for name, value in variables.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)


def check_in(monkeypatch: pytest.MonkeyPatch, profile: str) -> Any:
    """``check_hosting_panel()`` evaluated now, in ``profile``."""
    monkeypatch.setenv(PROFILE_VARIABLE, profile)
    return config_audit.check_hosting_panel()


def check_state(result: Any) -> tuple[Any, ...]:
    """A check's result as the admin interface reads it: its id, severity, i18n key and the key's parameters."""
    return result.check_id, result.severity, result.i18n_key, result.detail


#: HPT-040: values of ``LIBREFOLIO_PANEL_PUBLIC_KEYS`` that cannot be used, by what is wrong with them.
INVALID_KEYS = (
    ("a-key-without-its-kid", KEY_A.public_text),
    ("an-empty-kid", f":{KEY_A.public_text}"),
    ("a-kid-holding-a-space", f"hp key:{KEY_A.public_text}"),
    ("a-kid-of-65-characters", f"{'k' * 65}:{KEY_A.public_text}"),
    ("a-key-of-42-characters", f"{KEY_A.kid}:{KEY_A.public_text[:-1]}"),
    ("a-key-with-its-padding", f"{KEY_A.kid}:{KEY_A.public_text}="),
    ("one-kid-twice", f"{KEY_A.kid}:{KEY_A.public_text},{KEY_A.kid}:{KEY_B.public_text}"),
    ("five-entries", keys_value(KEY_A, KEY_B, *EXTRA_KEYS)),
)
#: HPT-040: values of ``LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS`` that are no integer from 0 to 300.
INVALID_SKEWS = (("301", "301"), ("minus-1", "-1"), ("not-an-integer", "1.5"), ("with-a-unit", "60s"), ("a-word", "sixty"))
#: HPT-040: ``LIBREFOLIO_PUBLIC_URL`` giving no audience: unset, blank, not http(s), without a scheme.
UNUSABLE_PUBLIC_URLS = (("unset", None), ("blank", "   "), ("not-http", "ftp://folio.example.com"), ("without-a-scheme", "folio.example.com"))
#: HPT-040: each case: the variables it sets, over a usable ``LIBREFOLIO_PUBLIC_URL``; the code; the variable the summary
#: names (None: left open for the audience, which a missing address and the keys share).
CHECK_ERRORS = [
    *(pytest.param({KEYS_VARIABLE: value}, "PANEL_KEYS_INVALID", KEYS_VARIABLE, id=f"keys-{label}") for label, value in INVALID_KEYS),
    *(pytest.param({KEYS_VARIABLE: keys_value(KEY_A), SKEW_VARIABLE: value}, "PANEL_CLOCK_SKEW_INVALID", SKEW_VARIABLE, id=f"skew-{label}") for label, value in INVALID_SKEWS),
    *(pytest.param({KEYS_VARIABLE: keys_value(KEY_A), PUBLIC_URL_VARIABLE: value}, "PANEL_AUDIENCE_UNAVAILABLE", None, id=f"keys-and-a-public-url-{label}") for label, value in UNUSABLE_PUBLIC_URLS),
]


@pytest.mark.parametrize(("variables", "code", "variable"), CHECK_ERRORS)
def test_ticket_settings_that_cannot_be_used_are_an_error_of_the_check_in_every_profile(monkeypatch: pytest.MonkeyPatch, variables: dict[str, str | None], code: str, variable: str | None) -> None:
    """HPT-040 (§4): keys that cannot be used, a skew out of range, or usable keys without a usable
    ``LIBREFOLIO_PUBLIC_URL``: ``platform.hosting_panel`` is an error, in the managed profile and self-hosted alike, its
    i18n key one of the check's. Its summary names the code (and, for the keys and the skew, the variable), as CP1's
    names the variables and the codes; the parameters of its message are texts or integers; never a key, usable or not,
    in any field (§1: an entry is named by its position, never by its key)."""
    print_section(f"H-61 CP2 §4: {code}")
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)
    set_variables(monkeypatch, variables)

    results = {profile: check_in(monkeypatch, profile) for profile in PROFILES}

    states = {profile: (result.check_id, result.severity, result.i18n_key) for profile, result in results.items()}
    assert {profile: state[:2] for profile, state in states.items()} == dict.fromkeys(PROFILES, (CHECK_ID, "error")), f"H-61 CP2 §4: {code}: platform.hosting_panel is an error in every profile: {states}"
    assert all(state[2].startswith(CHECK_KEY_PREFIX) for state in states.values()), f"the error's i18n key is one of the check's, {CHECK_KEY_PREFIX}*: {states}"
    unnamed = {profile: [name for name in (code, variable) if name is not None and name not in result.summary] for profile, result in results.items()}
    assert unnamed == dict.fromkeys(PROFILES, []), f"the summary names the code and the variable: {unnamed} missing from {[result.summary for result in results.values()]}"
    loose = {profile: result.detail for profile, result in results.items() if not all(isinstance(value, str | int) for value in result.detail.values())}
    assert loose == {}, f"the parameters of an i18n message are texts or integers: {loose}"
    shown = [index for index, fragment in enumerate(KEY_FRAGMENTS) if any(fragment in repr(result) for result in results.values())]
    assert shown == [], f"§1: never a key in a result: test key(s) #{shown} shown"
    print_success(f"{code}: an error in every profile, never a key")


@pytest.mark.parametrize("skew", [pytest.param(None, id="skew-unset"), pytest.param("0", id="skew-0"), pytest.param("300", id="skew-300")])
def test_usable_keys_alone_are_ok_in_every_profile(monkeypatch: pytest.MonkeyPatch, skew: str | None) -> None:
    """HPT-041 (§4): usable keys (two, as a rotation holds them), a usable ``LIBREFOLIO_PUBLIC_URL``, the skew unset or at
    either end of 0 to 300, and no token: the panel is on, so the check is ``ok`` with ``instance.checks.hostingPanel.ok``
    and no detail, in the managed profile and self-hosted alike, as CP1's is for usable tokens."""
    print_section(f"H-61 CP2 §4: usable keys alone, skew {skew}")
    set_variables(monkeypatch, {KEYS_VARIABLE: keys_value(KEY_A, KEY_B), PUBLIC_URL_VARIABLE: PUBLIC_URL, SKEW_VARIABLE: skew})

    states = {profile: check_state(check_in(monkeypatch, profile)) for profile in PROFILES}

    assert states == dict.fromkeys(PROFILES, (CHECK_ID, "ok", CHECK_OK, {})), f"H-61 CP2 §4: usable keys alone are ok, hostingPanel.ok, in every profile: {states}"
    print_success("ok, hostingPanel.ok, in both profiles")


@pytest.mark.parametrize("scopes", [pytest.param((STATUS,), id="the-status-token"), pytest.param((WAKE,), id="the-wake-token"), pytest.param((WAKE, STATUS), id="the-wake-and-status-tokens")])
def test_a_token_beside_the_keys_is_a_warning_in_the_managed_profile_only(monkeypatch: pytest.MonkeyPatch, scopes: tuple[str, ...]) -> None:
    """HPT-042 (§4, decision β): usable keys and address, and a scope's token beside them. In the managed profile the
    check is a warning, ``instance.checks.hostingPanel.coexisting``, its detail exactly ``{"variables": ...}`` naming each
    token's variable among nothing but the panel's variables, with a summary; self-hosted it is ``ok``,
    ``hostingPanel.ok``, no detail. Never a token in a result. Barrier: the tokens alone are ok, ``hostingPanel.ok``, in
    the managed profile, as in CP1."""
    print_section(f"H-61 CP2 §4: {', '.join(scopes)} beside the keys")
    tokens = {scope: a_token() for scope in scopes}
    set_variables(monkeypatch, {VARIABLES[scope]: token for scope, token in tokens.items()})
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)
    alone = check_state(check_in(monkeypatch, "managed"))
    monkeypatch.setenv(KEYS_VARIABLE, keys_value(KEY_A))

    managed = check_in(monkeypatch, "managed")
    selfhosted = check_in(monkeypatch, "selfhosted")

    assert alone == (CHECK_ID, "ok", CHECK_OK, {}), f"Barrier: the tokens alone are ok in the managed profile, as in CP1: {alone}"
    shape = (managed.check_id, managed.severity, managed.i18n_key, sorted(managed.detail))
    assert shape == (CHECK_ID, "warning", CHECK_COEXISTING, ["variables"]), f"H-61 CP2 §4: in the managed profile a token beside the keys is a warning, {CHECK_COEXISTING} with {{variables}}: {check_state(managed)}"
    listed = {name.strip() for name in str(managed.detail["variables"]).split(",")}
    expected = {VARIABLES[scope] for scope in scopes}
    assert expected <= listed <= PANEL_VARIABLES, f"{{variables}} names each token beside the keys, and nothing but the panel's variables: {sorted(listed)}, expected {sorted(expected)}"
    assert managed.summary.strip(), "a warning has a summary for the log"
    assert check_state(selfhosted) == (CHECK_ID, "ok", CHECK_OK, {}), f"H-61 CP2 §4: self-hosted, a token beside the keys is ok: {check_state(selfhosted)}"
    shown = [scope for scope, token in tokens.items() if token in f"{managed!r} {selfhosted!r}"]
    assert shown == [], f"never a token in a result: the {shown} token(s) shown"
    print_success(f"managed: warning, {managed.detail}; self-hosted: ok")


# =============================================================================
# HPT-043 (§4): the path of LIBREFOLIO_PUBLIC_URL
# =============================================================================

#: The warning for a path in the public address, and its one parameter.
CHECK_AUDIENCE_PATH = CHECK_KEY_PREFIX + "audiencePath"
CHECK_OFF = CHECK_KEY_PREFIX + "off"
#: Addresses with a path, and the path the warning gives: as written, without the one trailing slash ``env_url`` drops.
PATH_URLS = [
    pytest.param("https://folio.example.com/app", "/app", id="a-path"),
    pytest.param("https://folio.example.com/a/b/", "/a/b", id="a-nested-path-with-a-trailing-slash"),
]
#: The root, with and without its slash: no path.
ROOT_URLS = [pytest.param("https://folio.example.com", id="the-root"), pytest.param("https://folio.example.com/", id="the-root-with-its-slash")]
#: The address of HPT-043c and 043d, with a path.
URL_WITH_PATH = "https://folio.example.com/app"


@pytest.mark.parametrize(("url", "path"), PATH_URLS)
def test_a_path_in_the_public_url_beside_usable_keys_is_a_warning_in_every_profile(monkeypatch: pytest.MonkeyPatch, url: str, path: str) -> None:
    """HPT-043a (§4): usable keys and a ``LIBREFOLIO_PUBLIC_URL`` with a path other than the root: ``platform.hosting_panel``
    is a ``warning``, ``instance.checks.hostingPanel.audiencePath``, its detail exactly ``{"path": <the path as written,
    without the one trailing slash env_url drops>}``, a non-empty summary naming ``LIBREFOLIO_PUBLIC_URL``, in the
    managed profile and self-hosted alike: the audience is the origin only, so two instances on one origin under
    different paths would accept each other's tickets. Never a key in the result. Barrier: the same keys with the root
    address are ``ok``, ``hostingPanel.ok``, in both profiles, so the keys are usable and the path alone is the cause."""
    print_section(f"H-61 CP2 §4: a path in the public address, {url}")
    set_variables(monkeypatch, {KEYS_VARIABLE: keys_value(KEY_A), PUBLIC_URL_VARIABLE: PUBLIC_URL})
    root = {profile: check_state(check_in(monkeypatch, profile)) for profile in PROFILES}
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, url)

    results = {profile: check_in(monkeypatch, profile) for profile in PROFILES}

    assert root == dict.fromkeys(PROFILES, (CHECK_ID, "ok", CHECK_OK, {})), f"Barrier: the keys with the root address are ok in every profile: {root}"
    states = {profile: check_state(result) for profile, result in results.items()}
    assert states == dict.fromkeys(PROFILES, (CHECK_ID, "warning", CHECK_AUDIENCE_PATH, {"path": path})), f"H-61 CP2 §4: a path in LIBREFOLIO_PUBLIC_URL is a warning, {CHECK_AUDIENCE_PATH} with exactly {{'path': {path!r}}}, in every profile: {states}"
    unnamed = [profile for profile, result in results.items() if PUBLIC_URL_VARIABLE not in result.summary]
    assert unnamed == [], f"the summary names {PUBLIC_URL_VARIABLE}: not in the summary of {unnamed}: {[result.summary for result in results.values()]}"
    shown = [index for index, fragment in enumerate(KEY_FRAGMENTS) if any(fragment in repr(result) for result in results.values())]
    assert shown == [], f"§1: never a key in a result: test key(s) #{shown} shown"
    print_success(f"{url}: warning audiencePath {{path: {path}}} in both profiles")


@pytest.mark.parametrize("url", ROOT_URLS)
def test_the_root_public_url_beside_usable_keys_is_ok_in_every_profile(monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    """HPT-043b (§4): usable keys and the root address, with or without its slash: no path, so ``ok``,
    ``hostingPanel.ok``, no detail, in both profiles. The barrier of the warning: it is the path that raises it, never
    the address."""
    print_section(f"H-61 CP2 §4: the root address, {url}")
    set_variables(monkeypatch, {KEYS_VARIABLE: keys_value(KEY_A), PUBLIC_URL_VARIABLE: url})

    states = {profile: check_state(check_in(monkeypatch, profile)) for profile in PROFILES}

    assert states == dict.fromkeys(PROFILES, (CHECK_ID, "ok", CHECK_OK, {})), f"H-61 CP2 §4: the root address has no path, so the check is ok in every profile: {states}"
    print_success(f"{url}: ok, hostingPanel.ok, in both profiles")


@pytest.mark.parametrize(
    ("token", "expected"),
    [pytest.param(None, CHECK_OFF, id="no-token-the-panel-is-off"), pytest.param(a_token(), CHECK_OK, id="a-status-token-the-panel-is-on")],
)
def test_a_path_in_the_public_url_without_keys_is_not_the_checks_business(monkeypatch: pytest.MonkeyPatch, token: str | None, expected: str) -> None:
    """HPT-043c (§4): no keys, so L2 is off and the audience is read by nobody: a path in ``LIBREFOLIO_PUBLIC_URL`` is
    not this check's business. Without a token the panel is off (``hostingPanel.off``), with a status token it reads
    ``ok`` (``hostingPanel.ok``), in both profiles, no detail, never ``audiencePath``."""
    print_section(f"H-61 CP2 §4: a path in the public address, no keys, {expected.rpartition('.')[2]}")
    set_variables(monkeypatch, {PUBLIC_URL_VARIABLE: URL_WITH_PATH, VARIABLES[STATUS]: token})

    states = {profile: check_state(check_in(monkeypatch, profile)) for profile in PROFILES}

    assert states == dict.fromkeys(PROFILES, (CHECK_ID, "ok", expected, {})), f"H-61 CP2 §4: without keys a path in the public address changes nothing, {expected}, never {CHECK_AUDIENCE_PATH}: {states}"
    print_success(f"no keys, a path: {expected.rpartition('.')[2]} in both profiles, no audiencePath")


#: HPT-043d: the cases where the path meets another state of the check, by what stands beside the keys and the path:
#: the variables it sets, the profiles it covers, and the severity and i18n key the check gives (None: the key is left
#: open, any one of the check's but ``audiencePath``).
PRECEDENCE = [
    pytest.param({VARIABLES[STATUS]: a_token()}, ("managed",), "warning", CHECK_AUDIENCE_PATH, id="managed-a-token-beside-the-keys-the-path-comes-first"),
    pytest.param({VARIABLES[STATUS]: "short"}, PROFILES, "error", None, id="an-unusable-token-stays-an-error"),
    pytest.param({SKEW_VARIABLE: "301"}, PROFILES, "error", None, id="unusable-ticket-settings-stay-an-error"),
]


@pytest.mark.parametrize(("variables", "profiles", "severity", "i18n_key"), PRECEDENCE)
def test_the_path_warning_comes_after_the_errors_and_before_the_coexisting_token(monkeypatch: pytest.MonkeyPatch, variables: dict[str, str | None], profiles: tuple[str, ...], severity: str, i18n_key: str | None) -> None:
    """HPT-043d (§4): usable keys and a path in ``LIBREFOLIO_PUBLIC_URL``, and something else beside them. A token that
    cannot be used (too short) or ticket settings that cannot be used (a skew of 301) stay ``error``, in both profiles,
    as without the path: the path warning does not hide them. In the managed profile a usable token beside the keys and
    the path gives ``audiencePath``, not ``coexisting``: the path comes first. Barrier: the same variables with the root
    address give no ``audiencePath`` (``coexisting`` for the token, the errors for the others), so the path is what
    changes the answer."""
    print_section(f"H-61 CP2 §4: a path and {', '.join(variables)}, {', '.join(profiles)}")
    set_variables(monkeypatch, {KEYS_VARIABLE: keys_value(KEY_A), PUBLIC_URL_VARIABLE: PUBLIC_URL, **variables})
    root = {profile: check_state(check_in(monkeypatch, profile)) for profile in profiles}
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, URL_WITH_PATH)

    results = {profile: check_in(monkeypatch, profile) for profile in profiles}

    assert all(state[2] != CHECK_AUDIENCE_PATH for state in root.values()), f"Barrier: without a path the audience warning is not raised: {root}"
    states = {profile: (result.check_id, result.severity, result.i18n_key) for profile, result in results.items()}
    assert {profile: state[:2] for profile, state in states.items()} == dict.fromkeys(profiles, (CHECK_ID, severity)), f"H-61 CP2 §4: with a path and {sorted(variables)}: {severity} in {profiles}: {states}"
    if i18n_key is None:
        assert all(state[2].startswith(CHECK_KEY_PREFIX) and state[2] != CHECK_AUDIENCE_PATH for state in states.values()), f"an error stays the check's own, never {CHECK_AUDIENCE_PATH}: {states}"
    else:
        assert {profile: state[2] for profile, state in states.items()} == dict.fromkeys(profiles, i18n_key), f"the path comes first, {i18n_key}, not {CHECK_COEXISTING}: {states}"
        assert all(result.detail == {"path": "/app"} for result in results.values()), f"the detail is the path, as written: {[result.detail for result in results.values()]}"
    tokens = [value for value in variables.values() if value and len(value) >= 32]  # the short, unusable one is a word the summary may hold
    shown = [token for token in tokens if token in repr(results)]
    assert shown == [], "never a token in a result"
    print_success(f"a path and {', '.join(variables)}: {severity}, {i18n_key or 'an error key of the check'}")
