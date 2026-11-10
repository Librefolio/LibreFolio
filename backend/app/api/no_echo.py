"""Routes whose 422 never repeats what the client sent: a malformed request may hold a password or a secret.

FastAPI's validation errors carry each failing value as ``input``; for a missing field, ``input`` is the whole body, the
secret beside it included. A route that receives a secret uses ``NoInputEchoRoute`` (``APIRouter(route_class=…)``).
Born in the plugin settings' router (workstream X), shared here so that every such route has the same one.
"""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute


class NoInputEchoRoute(APIRoute):
    """A 422 without the ``input`` FastAPI echoes: the input of a malformed request may hold a secret.

    The errors keep ``type``, ``loc``, ``msg`` and ``ctx``. The new error is raised outside the ``except`` block, so it
    keeps no reference to the original one and its body.
    """

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def no_echo_handler(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError as error:
                errors = [{key: value for key, value in detail.items() if key != "input"} for detail in error.errors()]
            raise RequestValidationError(errors)

        return no_echo_handler
