"""The signed tickets of a hosting panel (lot H-61, level L2): one Ed25519 key of the panel for every instance.

Owner: workstream H (platform). A hosting panel that runs many instances holds one Ed25519 private key; each instance
holds only its public keys (``LIBREFOLIO_PANEL_PUBLIC_KEYS``, ``config/hosting_panel.py``). For each call the panel
signs a ticket: a JWS in compact form (a JWT), ``alg`` ``EdDSA`` (RFC 8037), ``typ`` ``lf-panel+jwt``, ``kid`` the label
of its key, and the claims ``aud`` (the origin of ``LIBREFOLIO_PUBLIC_URL``: the instance it is for), ``scope``
(``backup``, ``wake`` or ``status``), ``iat`` and ``exp`` (whole seconds, at most 300 apart) and ``jti`` (16 to 64
letters, digits, ``_`` or ``-``, used once: ``ticket_registry.py``). PyJWT and ``cryptography`` verify the signature:
no cryptography is written here.

``verify_ticket`` answers what a ticket is worth for a scope, at a moment. PyJWT checks the signature and the algorithm
only; every claim is checked here, in the contract's order, with the given ``now`` and the clock tolerance:

1. unverifiable, without a code of its own: more than ``TICKET_MAX_BYTES``, not a JWS, an ``alg`` other than
   ``EdDSA``, a ``typ`` other than ``lf-panel+jwt``, no ``kid``, a signature that does not verify. Only who holds a
   genuinely signed ticket learns why it was refused (decision Q8);
2. a ``kid`` the keys do not hold: ``panel_ticket_unknown_key`` (a rotation half done shows at once);
3. then, the signature being the panel's: the times (``exp <= now - skew`` expired, ``iat > now + skew`` not yet
   valid), the audience (missing or another), the scope, and last the rules of the ``jti`` and of the lifetime. A
   claim missing or of the wrong type is ``panel_ticket_invalid``, a bug of the signer, except a missing ``aud``, which
   is ``panel_ticket_wrong_audience``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

#: The type of a ticket, in its header: no other JWT signed with the same key is ever a ticket.
TICKET_TYPE = "lf-panel+jwt"
TICKET_ALGORITHM = "EdDSA"
#: The most bytes a ticket may hold, measured before anything is read.
TICKET_MAX_BYTES = 2048
#: The longest a ticket may live, ``exp - iat``, whatever the signer asks.
TICKET_MAX_LIFETIME_SECONDS = 300
JTI_PATTERN = re.compile(r"[A-Za-z0-9_-]{16,64}")
#: The seconds an answer «not yet valid» asks the panel to wait: the instance's clock is behind (a machine resumed).
NOT_YET_VALID_RETRY_AFTER_SECONDS = 5

UNKNOWN_KEY = "panel_ticket_unknown_key"
EXPIRED = "panel_ticket_expired"
NOT_YET_VALID = "panel_ticket_not_yet_valid"
WRONG_AUDIENCE = "panel_ticket_wrong_audience"
WRONG_SCOPE = "panel_ticket_wrong_scope"
INVALID = "panel_ticket_invalid"
#: Given by the access, not here: the registry (``ticket_registry.py``) already holds the ticket's ``jti``.
REPLAYED = "panel_ticket_replayed"

#: A JWS verifier that checks the signature and the algorithm, and nothing of the payload.
_JWS = jwt.PyJWS()


@dataclass(frozen=True)
class TicketClaims:
    """A ticket verified for a scope: its key's label, its id, its scope and its two times (seconds since the epoch)."""

    kid: str
    jti: str
    scope: str
    iat: int
    exp: int


@dataclass(frozen=True)
class TicketRefusal:
    """A ticket refused: ``code`` is a ``panel_ticket_*`` code when its signature is the panel's or its key unknown, else None."""

    code: str | None
    kid: str | None = None


def _int_claim(claims: dict, name: str) -> int | None:
    value = claims.get(name)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _signed_claims(value: str, keys: dict[str, Ed25519PublicKey]) -> tuple[str, dict] | TicketRefusal:
    """Steps 1 and 2: the ``kid`` and the claims of a ticket whose signature is the panel's, or why it is refused."""
    if len(value.encode("utf-8", errors="replace")) > TICKET_MAX_BYTES:
        return TicketRefusal(None)
    try:
        header = jwt.get_unverified_header(value)
    except jwt.PyJWTError:
        return TicketRefusal(None)
    kid = header.get("kid")
    if header.get("alg") != TICKET_ALGORITHM or header.get("typ") != TICKET_TYPE or not isinstance(kid, str):
        return TicketRefusal(None)
    key = keys.get(kid)
    if key is None:
        return TicketRefusal(UNKNOWN_KEY, kid)
    try:
        payload = _JWS.decode(value, key, algorithms=[TICKET_ALGORITHM])
    except jwt.PyJWTError:
        return TicketRefusal(None)
    # The signature is the panel's: from here every refusal says why
    try:
        claims = json.loads(payload)
    except ValueError:
        return TicketRefusal(INVALID, kid)
    return (kid, claims) if isinstance(claims, dict) else TicketRefusal(INVALID, kid)


def _checked_claims(kid: str, claims: dict, scope: str, audience: str, skew: int, now: float) -> TicketClaims | TicketRefusal:
    """Step 3: the claims of a ticket signed by the panel, checked in the contract's order."""
    iat, exp = _int_claim(claims, "iat"), _int_claim(claims, "exp")
    if iat is None or exp is None:
        return TicketRefusal(INVALID, kid)
    if exp <= now - skew:
        return TicketRefusal(EXPIRED, kid)
    if iat > now + skew:
        return TicketRefusal(NOT_YET_VALID, kid)
    if claims.get("aud") != audience:
        return TicketRefusal(WRONG_AUDIENCE, kid)
    claimed_scope, jti = claims.get("scope"), claims.get("jti")
    if not isinstance(claimed_scope, str):
        return TicketRefusal(INVALID, kid)
    if claimed_scope != scope:
        return TicketRefusal(WRONG_SCOPE, kid)
    if not isinstance(jti, str) or not JTI_PATTERN.fullmatch(jti) or exp <= iat or exp - iat > TICKET_MAX_LIFETIME_SECONDS:
        return TicketRefusal(INVALID, kid)
    return TicketClaims(kid=kid, jti=jti, scope=claimed_scope, iat=iat, exp=exp)


def verify_ticket(value: str, scope: str, keys: dict[str, Ed25519PublicKey], audience: str, skew: int, now: float) -> TicketClaims | TicketRefusal:
    """What ``value`` is worth for ``scope`` at ``now``: its claims, or why it is refused (see the module's comment)."""
    signed = _signed_claims(value, keys)
    if isinstance(signed, TicketRefusal):
        return signed
    kid, claims = signed
    return _checked_claims(kid, claims, scope, audience, skew, now)
