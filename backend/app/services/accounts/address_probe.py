"""The address probe: does this very instance answer at another address?

The Invite dialog shows the address of the server, prefilled and editable (developer decision D-A3). When an
administrator edits it, the browser checks that this instance — not merely something — answers there, and no stable
identifier of the instance is readable across sites:

1. the dialog asks its own instance, as an administrator, for a nonce (``POST /users/address-probe``);
2. it sends the nonce, without credentials, to ``GET <address>/api/v1/auth/address-probe?nonce=…``;
3. only an instance holding the same instance key verifies the nonce's signature, and answers ``{match: true}``.

A nonce is ``rand16 ‖ expiry ‖ HMAC-SHA256(key, rand16 ‖ expiry)``, base64url without padding, valid
``PROBE_TTL_SECONDS``; the key is derived from the instance key (``derive_key``). Nothing is stored, so any worker
verifies a nonce any worker issued. Anything else — forged, signed by another instance, expired, malformed — is
``False``: the public answer is one bit, about a nonce only an administrator of this instance can obtain.
"""

import base64
import binascii
import functools
import hashlib
import hmac
import secrets
import string
import time
from datetime import UTC, datetime

import structlog

from backend.app.services.platform.instance_key import derive_key

logger = structlog.get_logger(__name__)

PROBE_PURPOSE = "accounts.address-probe.v1"
PROBE_TTL_SECONDS = 120
#: Longer answers ``False`` at once, before any decoding.
MAX_NONCE_LENGTH = 256

_RANDOM_BYTES = 16
_EXPIRY_BYTES = 8
_MAC_BYTES = 32
_SIGNED_BYTES = _RANDOM_BYTES + _EXPIRY_BYTES
#: base64url of 56 bytes, without padding.
_NONCE_LENGTH = 75
_ALPHABET = frozenset(string.ascii_letters + string.digits + "-_")


def _mac(message: bytes) -> bytes:
    return hmac.new(derive_key(PROBE_PURPOSE), message, hashlib.sha256).digest()


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


@functools.cache
def _report_unusable_key() -> None:
    """Log once per process that probes cannot be verified: the configuration audit says why at startup."""
    logger.warning("Address probe: the instance key cannot be used, every probe answers no match")


def issue_probe_nonce(*, now: float | None = None) -> tuple[str, datetime]:
    """A nonce for the address probe, and when it expires (aware UTC)."""
    expiry = int(time.time() if now is None else now) + PROBE_TTL_SECONDS
    message = secrets.token_bytes(_RANDOM_BYTES) + expiry.to_bytes(_EXPIRY_BYTES, "big")
    return _encode(message + _mac(message)), datetime.fromtimestamp(expiry, tz=UTC)


def verify_probe_nonce(nonce: str, *, now: float | None = None) -> bool:
    """Whether ``nonce`` was issued by this instance and has not expired; ``False`` for anything else, never raises."""
    if not isinstance(nonce, str) or len(nonce) > MAX_NONCE_LENGTH or len(nonce) != _NONCE_LENGTH or not set(nonce) <= _ALPHABET:
        return False
    try:
        raw = base64.urlsafe_b64decode(nonce + "=")
    except (binascii.Error, ValueError):
        return False
    # One spelling per nonce: a string that decodes to the same bytes through ignored low bits is not the nonce
    if len(raw) != _SIGNED_BYTES + _MAC_BYTES or _encode(raw) != nonce:
        return False
    message, mac = raw[:_SIGNED_BYTES], raw[_SIGNED_BYTES:]
    try:
        expected = _mac(message)
    except Exception:  # an unusable instance key, or anything under it: nothing can be verified
        _report_unusable_key()
        return False
    if not hmac.compare_digest(mac, expected):
        return False
    return int.from_bytes(message[_RANDOM_BYTES:], "big") >= (time.time() if now is None else now)
