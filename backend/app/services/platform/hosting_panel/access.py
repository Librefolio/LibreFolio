"""The access of a hosting panel to its routes: one dependency for every scope (lot H-61, level L1).

Owner: workstream H (platform). A hosting panel calls an instance without a user session, with a credential per scope
(decision Q2): ``backup`` (``/backup/panel/jobs…``, workstream B), ``wake`` (``POST /system/wake-sync``, workstream Z)
and ``status`` (``GET /panel/status``). ``panel_access(scope)`` is the dependency of each route:

1. The scope's token is read at each call (``config/backup.py``, ``config/sleep_wake.py``,
   ``config/hosting_panel.py``). Unset, the route answers 404 ``Not Found``, as a path that does not exist, and nothing
   is logged or counted (decision Q3). One the server cannot use answers 503 with the scope's code, and is logged.
2. An address that sent too many refused credentials (``PANEL_ATTEMPT_LIMIT`` in ``PANEL_ATTEMPT_WINDOW_SECONDS``,
   every scope together) gets 429 ``panel_too_many_attempts`` with ``Retry-After``, before its credential is read. The
   address is the one the other limits per client count (``rate_limit_address``): none behind a proxy LibreFolio does
   not trust, and then no limit. The counts live in this process.
3. The credential travels only in ``Authorization: Bearer``, never in the URL, and is compared in constant time with
   the scope's token: a token never opens another scope. Missing or different, the answer is 401 with the scope's code
   and ``WWW-Authenticate: Bearer``, and the refusal is counted for the address. A correct one is never counted.

Each call to a scope that is on writes one line, ``Hosting panel request`` (a scope that is off writes none): the scope, the method, the path without its
query, the outcome, the kind of credential, and the reason of a refusal; INFO when accepted, WARNING otherwise. Never
the token, the value sent, a header, the query or the address: uvicorn's access line has the address. The bodies and
the codes of the backup and wake-up routes are the ones they had before (``backup_panel_*``, ``wake_*``). The six
routes share the OpenAPI tag ``HOSTING_PANEL_TAG``; each scope keeps its own bearer scheme.
"""

import hmac
import math
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.config import SecretFileError
from backend.app.config.backup import BackupConfigError, backup_download_token
from backend.app.config.hosting_panel import PANEL_STATUS_TOKEN_VARIABLE, HostingPanelConfigError, panel_status_token
from backend.app.config.sleep_wake import WAKE_TOKEN_VARIABLE, SleepWakeConfigError, wake_token
from backend.app.logging_config import get_logger
from backend.app.services.platform.client_address import client_rate_key, rate_limit_address
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter

logger = get_logger(__name__)

#: The OpenAPI tag of every route of the hosting panel, and of no other: a neutral name, since the code is public.
HOSTING_PANEL_TAG = "Hosting panel"

#: Refused credentials an address may send in ``PANEL_ATTEMPT_WINDOW_SECONDS``, every scope together, before a 429.
PANEL_ATTEMPT_LIMIT = 20
PANEL_ATTEMPT_WINDOW_SECONDS = 600.0
TOO_MANY_ATTEMPTS_CODE = "panel_too_many_attempts"


def new_panel_attempts() -> SlidingWindowLimiter:
    """A limiter of refused panel credentials: ``PANEL_ATTEMPT_LIMIT`` per address in ``PANEL_ATTEMPT_WINDOW_SECONDS``."""
    return SlidingWindowLimiter(PANEL_ATTEMPT_LIMIT, PANEL_ATTEMPT_WINDOW_SECONDS)


#: The refused credentials, per address: read at each call, so a test can replace it with one on its own clock.
PANEL_ATTEMPTS = new_panel_attempts()

REQUEST_LINE = "Hosting panel request"


class PanelScope(StrEnum):
    """What a credential of the hosting panel opens: one scope, never another."""

    BACKUP = "backup"
    WAKE = "wake"
    STATUS = "status"


@dataclass(frozen=True)
class PanelCaller:
    """The panel's call a dependency let through: its scope, and how it proved itself."""

    scope: PanelScope
    credential: Literal["token", "ticket"]


@dataclass(frozen=True)
class _ScopeRules:
    """How a scope reads its token and refuses a caller."""

    read_token: Callable[[], str | None]
    config_errors: tuple[type[Exception], ...]
    unusable_line: str
    unusable_fields: Callable[[Exception], dict[str, str]]
    unauthorized_code: str
    unauthorized_message: str
    unavailable_code: str
    unavailable_message: str
    bearer: HTTPBearer


_RULES: dict[PanelScope, _ScopeRules] = {
    PanelScope.BACKUP: _ScopeRules(
        read_token=lambda: backup_download_token(),
        config_errors=(SecretFileError, BackupConfigError),
        unusable_line="The hosting panel's backup token cannot be used: its routes refuse every request",
        unusable_fields=lambda exc: {"error": str(exc)},
        unauthorized_code="backup_panel_unauthorized",
        unauthorized_message="A valid panel token is required",
        unavailable_code="backup_panel_unavailable",
        unavailable_message="The panel token of this instance cannot be used",
        bearer=HTTPBearer(auto_error=False, scheme_name="BackupPanelToken", description="LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN, sent as `Authorization: Bearer <token>`"),
    ),
    PanelScope.WAKE: _ScopeRules(
        read_token=lambda: wake_token(),
        config_errors=(SecretFileError, SleepWakeConfigError),
        unusable_line="The wake-up token cannot be used: the scheduled wake-up refuses every request",
        unusable_fields=lambda exc: {"variable": WAKE_TOKEN_VARIABLE, "error": str(exc)},
        unauthorized_code="wake_unauthorized",
        unauthorized_message="A valid wake-up token is required",
        unavailable_code="wake_unavailable",
        unavailable_message="The wake-up token of this instance cannot be used",
        bearer=HTTPBearer(auto_error=False, scheme_name="WakeToken", description="LIBREFOLIO_WAKE_TOKEN, sent as `Authorization: Bearer <token>`"),
    ),
    PanelScope.STATUS: _ScopeRules(
        read_token=lambda: panel_status_token(),
        config_errors=(SecretFileError, HostingPanelConfigError),
        unusable_line="The panel status token cannot be used: the status route refuses every request",
        unusable_fields=lambda exc: {"variable": PANEL_STATUS_TOKEN_VARIABLE, "error": str(exc)},
        unauthorized_code="panel_status_unauthorized",
        unauthorized_message="A valid panel status token is required",
        unavailable_code="panel_status_unavailable",
        unavailable_message="The panel status token of this instance cannot be used",
        bearer=HTTPBearer(auto_error=False, scheme_name="PanelStatusToken", description="LIBREFOLIO_PANEL_STATUS_TOKEN, sent as `Authorization: Bearer <token>`"),
    ),
}


def _refusal(status_code: int, code: str, message: str, headers: dict[str, str] | None = None) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message}, headers=headers)


def _line(request: Request, scope: PanelScope, outcome: str, **fields: object) -> None:
    """The one line of a call: never a credential, a header, the query or the address."""
    write = logger.info if outcome == "accepted" else logger.warning
    write(REQUEST_LINE, scope=scope.value, method=request.method, path=request.url.path, outcome=outcome, credential="token", **fields)


def _make_access(scope: PanelScope) -> Callable[..., PanelCaller]:
    rules = _RULES[scope]

    def access(request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(rules.bearer)]) -> PanelCaller:
        try:
            expected = rules.read_token()
        except rules.config_errors as exc:
            logger.error(rules.unusable_line, **rules.unusable_fields(exc))
            _line(request, scope, "unavailable", reason="unusable")
            raise _refusal(status.HTTP_503_SERVICE_UNAVAILABLE, rules.unavailable_code, rules.unavailable_message) from None
        if expected is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
        attempts = PANEL_ATTEMPTS
        key = client_rate_key(rate_limit_address(request))
        if key is not None:
            decision = attempts.peek(key)
            if not decision.allowed:
                retry_after = max(1, math.ceil(decision.retry_after))
                _line(request, scope, "limited", retry_after=retry_after)
                raise _refusal(status.HTTP_429_TOO_MANY_REQUESTS, TOO_MANY_ATTEMPTS_CODE, "Too many refused panel credentials from this address", headers={"Retry-After": str(retry_after)})
        presented = credentials.credentials if credentials is not None else None
        if presented is not None and hmac.compare_digest(presented.encode("utf-8"), expected.encode("utf-8")):
            _line(request, scope, "accepted")
            return PanelCaller(scope=scope, credential="token")
        if key is not None:
            attempts.hit(key)
        _line(request, scope, "refused", reason="missing" if presented is None else "mismatch")
        raise _refusal(status.HTTP_401_UNAUTHORIZED, rules.unauthorized_code, rules.unauthorized_message, headers={"WWW-Authenticate": "Bearer"})

    access.__name__ = f"panel_access_{scope.value}"
    return access


_ACCESS: dict[PanelScope, Callable[..., PanelCaller]] = {scope: _make_access(scope) for scope in PanelScope}


def panel_access(scope: PanelScope) -> Callable[..., PanelCaller]:
    """The dependency of the routes of ``scope``: the same object for the same scope, so FastAPI runs it once a request."""
    return _ACCESS[scope]
