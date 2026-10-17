"""
The limit on failed sign-ins (F15, decision D-A5 of 14/10): 10 failures in 15 minutes per identifier, 50 per address.

- A wrong password counts once in each. An attempt over either limit is refused before any password is checked (429
  ``TOO_MANY_ATTEMPTS``, with ``Retry-After``), and a refusal is not counted: knocking does not push the unlock away.
- A sign-in that succeeds forgets the failures of its identifier, not those of its address.
- The other checks of the current password — a change of password, a change of address — count under the account's
  username, the same key a sign-in typed with that username uses.
- The identifier counts as typed, stripped, with A–Z folded and nothing else (decision P18), whether an account matches
  it or not: the answer never tells which identifiers exist.
- The address is workstream H's ``client_rate_key()`` of the address the routes pass: ``rate_limit_address()``, None
  behind a reverse proxy LibreFolio does not trust (decision N70), where every visitor would share the proxy's address
  and 50 failures from anyone would refuse everyone; then only the identifier's limit applies. An IPv6 client counts
  by its /64.
- In memory, per process: with N worker processes the limits are N times these. ``LIBREFOLIO_LOGIN_LIMIT=off`` turns it
  off — the test lanes do, for their suites sign in wrongly on purpose from one address — and the configuration checks
  say so (``checks.check_login_limit``: the startup log, ``GET /security/checks``).

The functions read the module's two limiters when they run, so a test replaces them with its own.
"""

from backend.app.config.accounts import login_limit_enabled
from backend.app.services.accounts.user_service import email_fold
from backend.app.services.platform.client_address import client_rate_key
from backend.app.utils.runtime.rate_window import RateDecision, SlidingWindowLimiter

WINDOW_SECONDS = 15 * 60
LOGIN_BY_IDENTIFIER = SlidingWindowLimiter(10, WINDOW_SECONDS)
LOGIN_BY_ADDRESS = SlidingWindowLimiter(50, WINDOW_SECONDS)


def identifier_key(identifier: str) -> str:
    """The key of what was typed in the identifier field: stripped, A–Z folded (``" Alice "`` and ``"ALICE"`` are one)."""
    return email_fold(identifier.strip())


def refusal(identifier: str, address: str | None) -> RateDecision | None:
    """The refusal an attempt gets now, without counting it: None while both limits allow another failure.

    When both refuse, the longer wait. Without an address only the identifier's limit applies.
    """
    if not login_limit_enabled():
        return None
    decisions = [LOGIN_BY_IDENTIFIER.peek(identifier_key(identifier))]
    address_key = client_rate_key(address)
    if address_key is not None:
        decisions.append(LOGIN_BY_ADDRESS.peek(address_key))
    refused = [decision for decision in decisions if not decision.allowed]
    return max(refused, key=lambda decision: decision.retry_after) if refused else None


def record_failure(identifier: str, address: str | None) -> None:
    """One failure for the identifier, and for the address when there is one; nothing while the limit is off."""
    if not login_limit_enabled():
        return
    LOGIN_BY_IDENTIFIER.hit(identifier_key(identifier))
    address_key = client_rate_key(address)
    if address_key is not None:
        LOGIN_BY_ADDRESS.hit(address_key)


def record_success(identifier: str) -> None:
    """The right password: the identifier's failures are forgotten. The address keeps its own."""
    LOGIN_BY_IDENTIFIER.reset(identifier_key(identifier))
