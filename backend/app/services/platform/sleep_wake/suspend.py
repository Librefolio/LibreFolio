"""Ask Fly.io to suspend this machine (workstream Z, release 1.3, F26).

Owner: workstream Z. A Fly Machine reaches the Machines API of its own app through the Unix socket ``/.fly/api``,
without a token: ``POST http://flaps/v1/apps/<app>/machines/<machine>/suspend`` freezes the machine (memory and CPU
state) until a request reaches it again, when Fly's proxy resumes it where it stopped. The process does not see the
suspension: the call may return after the machine has been resumed. ``FLY_APP_NAME`` and ``FLY_MACHINE_ID`` are set by
Fly on every machine and read through ``config/sleep_wake.py``; without them this is not a Fly machine, and nothing is
sent.

Only the idle monitor calls it (``idle_monitor.py``), with ``LIBREFOLIO_IDLE_SUSPEND_MODE=fly``.
"""

from collections.abc import Mapping
from urllib.parse import quote

import httpx

from backend.app.config.sleep_wake import fly_machine_identity

#: The Unix socket of the Machines API inside a Fly Machine.
FLY_API_SOCKET = "/.fly/api"
#: The host name the Machines API answers to on that socket.
FLY_API_BASE_URL = "http://flaps"


class SuspendError(Exception):
    """The machine could not be suspended; ``reason`` is a short code: ``not_on_fly``, ``http_<status>``, ``connection``."""

    def __init__(self, reason: str, message: str | None = None):
        super().__init__(message or reason)
        self.reason = reason


class FlySuspender:
    """Ask the Machines API of this Fly machine to suspend it, through ``/.fly/api``."""

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None, environ: Mapping[str, str] | None = None, timeout: float = 10.0):
        self._transport = transport
        self._environ = environ
        self._timeout = timeout

    def transport_factory(self) -> httpx.AsyncBaseTransport:
        """The transport of a request: the one given, or a new one on the Unix socket of the Machines API."""
        if self._transport is not None:
            return self._transport
        return httpx.AsyncHTTPTransport(uds=FLY_API_SOCKET)

    async def suspend(self) -> None:
        """Ask for the suspension of this machine; return once the Machines API has accepted it (any 2xx)."""
        identity = fly_machine_identity(self._environ)
        if identity is None:
            raise SuspendError("not_on_fly", "FLY_APP_NAME and FLY_MACHINE_ID are not set: this is not a Fly.io machine")
        app, machine = identity
        url = f"{FLY_API_BASE_URL}/v1/apps/{quote(app, safe='')}/machines/{quote(machine, safe='')}/suspend"
        try:
            async with httpx.AsyncClient(transport=self.transport_factory(), timeout=self._timeout) as client:
                response = await client.post(url)
        except httpx.HTTPError as exc:
            raise SuspendError("connection", f"the Fly Machines API did not answer: {type(exc).__name__}") from exc
        if not response.is_success:
            raise SuspendError(f"http_{response.status_code}", f"the Fly Machines API answered {response.status_code}")
