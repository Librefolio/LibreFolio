"""``NoInputEchoRoute``: FastAPI's 422 without the ``input`` it echoes, in one home for every router that receives a secret
(release 1.3, workstream B, lot B4: workstream X's class moved; X reviews).

Under test: ``backend/app/api/no_echo.py``, new in B4. FastAPI's own 422 repeats in each error's ``input`` what the
client sent: for a missing field, the whole body beside it, a password included; for an extra field or a value too long,
the value itself. ``api/v1/plugin_settings.py`` already drops it with a private ``_NoInputEchoRoute``; B4 moves that
class to ``backend.app.api.no_echo`` as ``NoInputEchoRoute`` and puts it on the backup routes that receive a password.
The frozen contract, ``b4-test-brief.md`` §3 and §4:

(a) On a router with ``route_class=NoInputEchoRoute``, a body the validation refuses is a 422 whose errors keep ``type``,
    ``loc`` and ``msg`` (and ``ctx`` when the error has one) and never carry ``input``: a ``username`` missing beside a
    password, an extra field, a password over its ``max_length``. The password's text appears nowhere in the answer.
    Each case first proves, on a plain ``APIRoute``, that FastAPI does echo it there: a case that never echoes would
    prove nothing.
(b) Nothing else of the route changes: a valid body reaches the endpoint, 200 with its answer; an ``HTTPException`` the
    endpoint raises keeps its status and its detail.
(c) One home: ``plugin_settings`` keeps no ``_NoInputEchoRoute`` of its own; its router, and each of its routes, use
    ``NoInputEchoRoute``.
(d) The backup routers that receive a password, ``instance_router`` (``POST /backup/instance``) and ``restore_router``
    (``POST /backup/restore/stage``), use it: the router, and each of its routes.

Pure: a tiny ``FastAPI()`` of each test behind ``httpx.ASGITransport``, in process; the routers are only imported. No
server, no database, no data directory.

Red until B4: ``backend/app/api/no_echo.py`` does not exist yet, so the import at the top (``from backend.app.api import
no_echo``) fails at collection, for every test of the module.
"""

import httpx
import pytest
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field

from backend.app.api import no_echo
from backend.app.api.v1 import plugin_settings
from backend.app.api.v1.backup import instance, restore
from backend.test_scripts.test_utils import print_section, print_success

#: The class under test. Imported through its package, which exists today: the import fails at collection, ``cannot
#: import name 'no_echo'``, until B4 adds the module.
NoInputEchoRoute = no_echo.NoInputEchoRoute

#: The password of the requests, and a secret carried by an extra field: neither may ever come back.
SECRET = "S3cret-Example-Pass!"
EXTRA_SECRET = "S3cret-Extra-Field-Value!"
#: The longest password the model takes, as the backup's request models take it.
PASSWORD_MAX_LENGTH = 1024
#: A password one character over that length, holding the secret: what FastAPI echoes in full.
TOO_LONG = (SECRET * (PASSWORD_MAX_LENGTH // len(SECRET) + 1))[: PASSWORD_MAX_LENGTH + 1]
LOGIN = "/b4/login"
REFUSING = "/b4/refusing"
#: The detail of the ``HTTPException`` the refusing endpoint raises, as the backup routes answer a weak password.
REFUSAL_DETAIL = {"code": "password_too_weak", "rules": ["min_length"]}


class Credentials(BaseModel):
    """The body of the test's routes: strict about its fields, as the backup's request models are."""

    model_config = ConfigDict(extra="forbid")

    username: str
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)


def tiny_app(route_class: type[APIRoute]) -> FastAPI:
    """A ``FastAPI()`` holding one router of ``route_class``: a route that answers, and one that refuses."""
    router = APIRouter(route_class=route_class)

    @router.post(LOGIN)
    def login(credentials: Credentials) -> dict[str, str]:
        return {"username": credentials.username}

    @router.post(REFUSING)
    def refusing(credentials: Credentials) -> dict[str, str]:
        raise HTTPException(status_code=400, detail=REFUSAL_DETAIL)

    app = FastAPI()
    app.include_router(router)
    return app


async def post(app: FastAPI, path: str, body: dict) -> httpx.Response:
    """``POST`` ``body`` as JSON to ``app``, in process; an exception the app does not answer comes back as a plain 500."""
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://in-process") as client:
        return await client.post(path, json=body)


#: (body, the (type, loc) of the error it gets, that error's ``ctx`` (``None``: the validation gives it none), the secret a
#: plain FastAPI echoes for it).
MALFORMED_BODIES = [
    pytest.param({"password": SECRET}, ("missing", ("body", "username")), None, SECRET, id="a-username-missing-beside-the-password"),
    pytest.param({"username": "b4-user", "password": SECRET, "unexpected": EXTRA_SECRET}, ("extra_forbidden", ("body", "unexpected")), None, EXTRA_SECRET, id="an-extra-field"),
    pytest.param({"username": "b4-user", "password": TOO_LONG}, ("string_too_long", ("body", "password")), {"max_length": PASSWORD_MAX_LENGTH}, SECRET, id="a-password-over-its-max-length"),
]

#: The backup routers that receive a password (§4).
PASSWORD_ROUTERS = [
    pytest.param(instance.instance_router, id="instance_router"),
    pytest.param(restore.restore_router, id="restore_router"),
]


def api_routes_not_using_the_class(router: APIRouter) -> list[str]:
    """The routes of ``router`` that are not a ``NoInputEchoRoute``, as ``METHODS path (class)``."""
    return [f"{sorted(route.methods)} {route.path} ({type(route).__name__})" for route in router.routes if isinstance(route, APIRoute) and not isinstance(route, NoInputEchoRoute)]


# =============================================================================
# (a) A refused body: 422, never its input
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(("body", "expected_error", "expected_ctx", "echoed"), MALFORMED_BODIES)
async def test_a_refused_body_is_a_422_that_never_echoes_it(body: dict, expected_error: tuple[str, tuple[str, str]], expected_ctx: dict | None, echoed: str):
    """(a) FastAPI's 422, each error with ``type``, ``loc`` and ``msg`` and without ``input``; the expected error among
    them, its ``ctx`` kept; neither secret anywhere in the answer, which a plain ``APIRoute`` does echo."""
    print_section(f"B4: a 422 without input, {expected_error[0]}")
    plain = await post(tiny_app(APIRoute), LOGIN, body)
    assert plain.status_code == 422 and echoed in plain.text, f"test bug: a plain APIRoute must echo this case, or it proves nothing: {plain.status_code} {plain.text[:300]}"

    response = await post(tiny_app(NoInputEchoRoute), LOGIN, body)

    assert response.status_code == 422, f"FastAPI's own refusal, 422: got {response.status_code} {response.text[:300]}"
    errors = response.json().get("detail")
    assert isinstance(errors, list) and errors, f"a 422 lists its errors in detail: {response.text[:300]}"
    echoing = [error for error in errors if "input" in error]
    assert echoing == [], f"no error may carry input: {echoing}"
    incomplete = [error for error in errors if not {"type", "loc", "msg"} <= set(error)]
    assert incomplete == [], f"every error keeps type, loc and msg: {incomplete}"
    matching = [error for error in errors if (error["type"], tuple(error["loc"])) == expected_error]
    assert len(matching) == 1, f"one error {expected_error}: {errors}"
    assert matching[0].get("ctx") == expected_ctx, f"the error keeps the ctx the validation gave it, {expected_ctx}: {matching[0]}"
    leaked = [secret for secret in (SECRET, EXTRA_SECRET) if secret in response.text]
    assert leaked == [], f"the answer repeats a secret of the request: {leaked} in {response.text[:300]}"
    print_success(f"422 {expected_error}, no input, no secret")


# =============================================================================
# (b) The rest of the route, unchanged
# =============================================================================


@pytest.mark.asyncio
async def test_a_valid_body_reaches_the_endpoint():
    """(b) A valid body: 200, the endpoint's answer, as on a plain route."""
    response = await post(tiny_app(NoInputEchoRoute), LOGIN, {"username": "b4-user", "password": SECRET})

    assert (response.status_code, response.json()) == (200, {"username": "b4-user"}), f"a valid body reaches the endpoint: {response.status_code} {response.text[:300]}"


@pytest.mark.asyncio
async def test_an_http_exception_of_the_endpoint_keeps_its_status_and_detail():
    """(b) Only the validation's 422 is changed: an ``HTTPException`` the endpoint raises (a 400 with a code, as the
    backup routes refuse a weak password) comes back as it was raised."""
    response = await post(tiny_app(NoInputEchoRoute), REFUSING, {"username": "b4-user", "password": SECRET})

    assert (response.status_code, response.json()) == (400, {"detail": REFUSAL_DETAIL}), f"the endpoint's own refusal, unchanged: {response.status_code} {response.text[:300]}"


# =============================================================================
# (c)-(d) Who uses it
# =============================================================================


def test_plugin_settings_uses_the_shared_class_and_keeps_no_copy():
    """(c) One home: the class is defined in ``backend.app.api.no_echo`` and is an ``APIRoute``; ``plugin_settings`` no
    longer defines ``_NoInputEchoRoute``, and its router, with each of its routes, uses ``NoInputEchoRoute``."""
    assert NoInputEchoRoute.__module__ == "backend.app.api.no_echo" and issubclass(NoInputEchoRoute, APIRoute), f"NoInputEchoRoute must be an APIRoute defined in backend.app.api.no_echo, not {NoInputEchoRoute.__module__}"
    assert not hasattr(plugin_settings, "_NoInputEchoRoute"), "plugin_settings keeps a private _NoInputEchoRoute beside the shared class: two copies to keep alike"
    assert plugin_settings.router.route_class is NoInputEchoRoute, f"plugin_settings.router must use NoInputEchoRoute: it uses {plugin_settings.router.route_class!r}"
    assert any(isinstance(route, APIRoute) for route in plugin_settings.router.routes), "precondition: plugin_settings.router has routes"
    assert api_routes_not_using_the_class(plugin_settings.router) == [], f"every route of plugin_settings uses NoInputEchoRoute: {api_routes_not_using_the_class(plugin_settings.router)}"


@pytest.mark.parametrize("router", PASSWORD_ROUTERS)
def test_the_backup_routers_that_receive_a_password_use_it(router: APIRouter):
    """(d) ``instance_router`` and ``restore_router`` use ``NoInputEchoRoute``: the router's ``route_class``, and each of
    its routes (a ``route_class`` set after the routes were declared would leave them plain)."""
    assert router.route_class is NoInputEchoRoute, f"the router must use NoInputEchoRoute: it uses {router.route_class!r}"
    assert any(isinstance(route, APIRoute) for route in router.routes), "precondition: the router has routes"
    assert api_routes_not_using_the_class(router) == [], f"every route must be a NoInputEchoRoute: {api_routes_not_using_the_class(router)}"
