"""
Address Probe by image — release 1.3, lot H-55 v2, step 2 (the CSP is enforced in every profile).

The Invite dialog checks that THIS instance answers at an edited address (``test_address_probe_api.py``: nonce from
``POST /users/address-probe``, then a ``GET <address>/api/v1/auth/address-probe?nonce=…`` whose JSON the browser reads).
Under an enforced ``connect-src`` a ``fetch`` to another origin is blocked, while ``img-src`` is not enforced: so the
same check is also an image, whose size is readable across origins without CORS. One route, in a module of its own:

``GET /api/v1/auth/address-probe.png?nonce=…`` (``backend/app/api/v1/address_probe_image.py``: a router with no prefix,
the route path ``/auth/address-probe.png``, included by ``api/v1/router.py``; ``auth.py`` does not define it).

- Public: no session, a valid, a forged or no cookie change nothing. A sync ``def`` (the key read is file I/O).
- 200 and ``Content-Type: image/png`` always, a valid PNG: **1x1** when ``address_probe.verify_probe_nonce(nonce)`` is
  true, **2x1** for anything else — forged (a well-formed nonce with a wrong MAC), another instance's, expired, empty,
  missing, too long (more than ``MAX_NONCE_LENGTH``). Status and media type are the same either way: only the size says
  yes or no.
- ``Cache-Control: no-store`` on every answer, 1x1 or 2x1.
- Its endpoint function is NOT in ``instance_block.ALLOWED_WHEN_BLOCKED``, like the JSON probe (decision A6a): on a blocked
  instance it answers the 401 of a public route outside the list (``test_instance_block.py``, ``PUBLIC_READS_OUTSIDE_THE_LIST``).
- The JSON route ``GET /auth/address-probe`` stays as it is (curl, older clients): a barrier here.

Where it runs: **in process**, the app of ``main.py`` through ``httpx.ASGITransport`` (its lifespan does not run), as the
in-process cases of ``test_address_probe_api.py`` do. The route reads no database and needs no session, and the nonce is
stateless, so nothing is asked of the lane's server: the instance key of this process is set with ``monkeypatch`` to a
key of this test (``KEY_A``; ``KEY_B`` is «another instance»), for the issue and the check alike. No key file, no row, no
server is touched: write-scoped by construction, nothing to clean up. The lane's server is not asked, so setting the key
in this process cannot reach it.

Red until H-55 v2 step 2: ``GET /auth/address-probe.png`` falls on the SPA catch-all of ``main.py`` (404, HTML), so every
test below that asks it fails on its status or media type; the source checks fail on the missing module. The new module is
imported inside the tests that need it, never at collection.
"""

import contextlib
import importlib
import struct
import zlib
from collections.abc import Iterator
from pathlib import Path
from typing import Optional
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from backend.app.api.v1 import auth as auth_api
from backend.app.config import API_V1_PREFIX, is_test_mode
from backend.test_scripts.test_utils import print_section, print_success

TIMEOUT = 30.0
COOKIE = auth_api.SESSION_COOKIE_NAME

IMAGE_PATH = "/auth/address-probe.png"
JSON_PATH = "/auth/address-probe"
#: Imported inside the tests that need it: until step 2 only they fail on it, not the collection.
IMAGE_MODULE = "backend.app.api.v1.address_probe_image"
PROBE_MODULE = "backend.app.services.accounts.address_probe"

KEY_VARIABLE = "LIBREFOLIO_INSTANCE_KEY"
KEY_FILE_VARIABLE = "LIBREFOLIO_INSTANCE_KEY_FILE"
#: Two instance keys of this test, at least 32 characters (instance_key.py).
KEY_A = "address-probe-image-instance-key-A-0123456789"
KEY_B = "address-probe-image-instance-key-B-0123456789"
#: How long before the check the expired nonce is issued: expired eight minutes ago, far from any clock jitter.
EXPIRED_AGO_SECONDS = 600

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MATCH_SIZE = (1, 1)
NO_MATCH_SIZE = (2, 1)

BACKEND_DIR = Path(__file__).resolve().parents[2]
API_V1_DIR = BACKEND_DIR / "app" / "api" / "v1"


# =============================================================================
# A PNG, read with the standard library
# =============================================================================


def png_size(data: bytes) -> tuple[int, int]:
    """(width, height) of a PNG, after proving it is one: the signature, IHDR first (13 bytes), every chunk's CRC, IDAT data
    that inflates, IEND last with nothing after it. Raises AssertionError saying what is wrong."""
    assert data[:8] == PNG_SIGNATURE, f"not a PNG: the first bytes are {data[:8]!r}, the signature is {PNG_SIGNATURE!r}"
    offset = 8
    chunks: list[tuple[bytes, bytes]] = []
    while offset < len(data):
        assert offset + 8 <= len(data), f"truncated PNG: a chunk header at byte {offset} is cut"
        (length,) = struct.unpack(">I", data[offset : offset + 4])
        kind = data[offset + 4 : offset + 8]
        body = data[offset + 8 : offset + 8 + length]
        crc_bytes = data[offset + 8 + length : offset + 12 + length]
        assert len(body) == length and len(crc_bytes) == 4, f"truncated PNG: the {kind!r} chunk at byte {offset} is cut"
        (crc,) = struct.unpack(">I", crc_bytes)
        assert crc == zlib.crc32(kind + body), f"PNG chunk {kind!r} at byte {offset}: wrong CRC"
        chunks.append((kind, body))
        offset += 12 + length
    assert chunks and chunks[0][0] == b"IHDR" and len(chunks[0][1]) == 13, f"a PNG starts with a 13-byte IHDR chunk: {[kind for kind, _ in chunks]!r}"
    assert chunks[-1][0] == b"IEND", f"a PNG ends with IEND: {[kind for kind, _ in chunks]!r}"
    idat = b"".join(body for kind, body in chunks if kind == b"IDAT")
    assert idat, "a PNG holds at least one IDAT chunk"
    try:
        zlib.decompress(idat)
    except zlib.error as error:
        raise AssertionError(f"the IDAT data of the PNG does not inflate: {error}") from error
    width, height = struct.unpack(">II", chunks[0][1][:8])
    return width, height


# =============================================================================
# The app in process, the instance key of this process
# =============================================================================


@pytest.fixture(scope="module")
def app() -> FastAPI:
    """The app the lane's server runs, in this process: test mode, or nothing runs."""
    assert is_test_mode(), "Precondition: test mode, so that the app in process derives from the lane's data directory, never from the production one"
    from backend.app.main import app as main_app  # noqa: PLC0415 — the server's own app, imported only by the fixture that needs it

    return main_app


@contextlib.contextmanager
def _instance_key(monkeypatch: pytest.MonkeyPatch, key: str) -> Iterator[None]:
    """In this process, for the block only: the instance key ``key`` (and no key file)."""
    with monkeypatch.context() as patched:
        patched.delenv(KEY_FILE_VARIABLE, raising=False)
        patched.setenv(KEY_VARIABLE, key)
        yield


def _issue(monkeypatch: pytest.MonkeyPatch, *, key: str, now: Optional[float] = None) -> str:
    """A nonce issued in this process by the service, under ``key``; ``now`` in the past issues an expired one."""
    probe = importlib.import_module(PROBE_MODULE)
    with _instance_key(monkeypatch, key):
        nonce, _ = probe.issue_probe_nonce(now=now)
    return nonce


def _with_last_byte_flipped(nonce: str) -> str:
    """A well-formed nonce whose MAC is wrong: the lowest bit of the last of its 56 bytes flipped, spelled canonically."""
    import base64  # noqa: PLC0415 — only this helper decodes a nonce

    raw = bytearray(base64.urlsafe_b64decode(nonce + "=" * (-len(nonce) % 4)))
    raw[-1] ^= 0x01
    return base64.urlsafe_b64encode(bytes(raw)).rstrip(b"=").decode("ascii")


async def _get(app: FastAPI, path: str, *, params: Optional[dict[str, str]] = None, headers: Optional[dict[str, str]] = None) -> httpx.Response:
    """``GET /api/v1<path>`` on the app in process, from a client of its own: only ``headers`` decide what is sent."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://librefolio.test") as client:
        return await client.get(f"{API_V1_PREFIX}{path}", params=params, headers=headers or {}, timeout=TIMEOUT)


def _cache_directives(response: httpx.Response) -> set[str]:
    """The directives of the response's Cache-Control, lower-cased."""
    return {directive.strip().lower() for directive in response.headers.get("cache-control", "").split(",") if directive.strip()}


def _violations(response: httpx.Response, expected_size: tuple[int, int]) -> list[str]:
    """Why an answer is not 200 ``image/png`` with a valid PNG of ``expected_size`` and ``Cache-Control: no-store``: empty
    when it is."""
    problems: list[str] = []
    if response.status_code != 200:
        problems.append(f"status {response.status_code}")
    media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type != "image/png":
        problems.append(f"Content-Type {response.headers.get('content-type')!r}")
    if "no-store" not in _cache_directives(response):
        problems.append(f"Cache-Control {response.headers.get('cache-control')!r}")
    if not problems:
        try:
            size = png_size(response.content)
        except AssertionError as error:
            problems.append(str(error))
        else:
            if size != expected_size:
                problems.append(f"PNG size {size[0]}x{size[1]}")
    return problems


def _assert_image(response: httpx.Response, expected_size: tuple[int, int], case: str) -> None:
    """The whole answer of the image probe, not only its size: status, media type, cache header, a decodable PNG."""
    problems = _violations(response, expected_size)
    expected = f"{expected_size[0]}x{expected_size[1]}"
    assert not problems, f"GET {IMAGE_PATH}, {case}: expected 200 image/png, a valid PNG of {expected} and Cache-Control: no-store; wrong: {'; '.join(problems)}"


# =============================================================================
# 1. The image says yes (1x1) or no (2x1), and nothing else differs
# =============================================================================


@pytest.mark.asyncio
async def test_image_probe_is_a_1x1_png_for_a_nonce_just_issued(app, monkeypatch):
    """AP-IMG-01: a nonce of this instance, not yet expired, gets a decodable 1x1 PNG, as many times as it is asked (the
    check is stateless, nothing is consumed)."""
    print_section(f"AP-IMG-01: GET {IMAGE_PATH} with an issued nonce")
    nonce = _issue(monkeypatch, key=KEY_A)
    with _instance_key(monkeypatch, KEY_A):
        _assert_image(await _get(app, IMAGE_PATH, params={"nonce": nonce}), MATCH_SIZE, "a nonce just issued")
        _assert_image(await _get(app, IMAGE_PATH, params={"nonce": nonce}), MATCH_SIZE, "the same nonce asked again")
    print_success("1x1, twice, image/png, no-store")


#: Each case builds what the browser sends as ``nonce`` (None: the parameter is missing altogether). Built in the test, with
#: the monkeypatch, because two of them need another key than the one the check runs under.
NOT_A_MATCH = [
    pytest.param(lambda monkeypatch, probe: _with_last_byte_flipped(_issue(monkeypatch, key=KEY_A)), id="forged-wrong-mac"),
    pytest.param(lambda monkeypatch, probe: _issue(monkeypatch, key=KEY_B), id="other-instance"),
    pytest.param(lambda monkeypatch, probe: _issue(monkeypatch, key=KEY_A, now=_expired_instant()), id="expired"),
    pytest.param(lambda monkeypatch, probe: "", id="empty"),
    pytest.param(lambda monkeypatch, probe: None, id="missing-parameter"),
    pytest.param(lambda monkeypatch, probe: "A" * (probe.MAX_NONCE_LENGTH + 1), id="too-long"),
    pytest.param(lambda monkeypatch, probe: _issue(monkeypatch, key=KEY_A) + "A" * (probe.MAX_NONCE_LENGTH + 1 - 75), id="valid-nonce-padded-too-long"),
]


def _expired_instant() -> float:
    """A past ``now`` for ``issue_probe_nonce``: ``EXPIRED_AGO_SECONDS`` ago, so the nonce issued with it expired long before the check."""
    import time  # noqa: PLC0415 — only this helper reads the clock

    return time.time() - EXPIRED_AGO_SECONDS


@pytest.mark.asyncio
@pytest.mark.parametrize("build", NOT_A_MATCH)
async def test_image_probe_is_a_2x1_png_for_anything_that_is_not_a_match(app, monkeypatch, build):
    """AP-IMG-02: forged, another instance's, expired, empty, missing, too long — the same 200 ``image/png`` with a valid
    PNG, 2x1 (the «no»). The control: the very same check says 1x1 for a nonce of this instance (AP-IMG-01 and the barrier
    below), so a route that always said «no» fails there, and one that always said «yes» fails here."""
    print_section(f"AP-IMG-02: GET {IMAGE_PATH} with something that is not a match")
    probe = importlib.import_module(PROBE_MODULE)
    nonce = build(monkeypatch, probe)
    params = None if nonce is None else {"nonce": nonce}
    with _instance_key(monkeypatch, KEY_A):
        control = _issue_now_under_current_key(probe)
        _assert_image(await _get(app, IMAGE_PATH, params={"nonce": control}), MATCH_SIZE, "Barrier: a nonce issued under this key, asked first")
        _assert_image(await _get(app, IMAGE_PATH, params=params), NO_MATCH_SIZE, f"nonce {nonce!r:.40}")
    print_success("2x1, image/png, no-store; the control said 1x1")


def _issue_now_under_current_key(probe) -> str:
    """A nonce issued now under the instance key currently set in this process."""
    nonce, _ = probe.issue_probe_nonce()
    return nonce


@pytest.mark.asyncio
async def test_image_probe_answers_the_same_status_and_type_whatever_the_nonce(app, monkeypatch):
    """AP-IMG-03: the yes and the no differ in the image's size and in nothing else a caller can read: the status code and
    the media type are the same, and so is ``Cache-Control``, so that no other signal leaks the verdict."""
    print_section("AP-IMG-03: yes and no look alike but for the size")
    good = _issue(monkeypatch, key=KEY_A)
    bad = _with_last_byte_flipped(good)
    with _instance_key(monkeypatch, KEY_A):
        yes = await _get(app, IMAGE_PATH, params={"nonce": good})
        no = await _get(app, IMAGE_PATH, params={"nonce": bad})
    assert (yes.status_code, no.status_code) == (200, 200), f"both answers are 200: yes {yes.status_code}, no {no.status_code}"
    assert yes.headers.get("content-type") == no.headers.get("content-type"), f"the same Content-Type: yes {yes.headers.get('content-type')!r}, no {no.headers.get('content-type')!r}"
    assert yes.headers.get("content-type", "").split(";", 1)[0].strip().lower() == "image/png", f"image/png, not {yes.headers.get('content-type')!r}"
    assert _cache_directives(yes) == _cache_directives(no), f"the same Cache-Control: yes {yes.headers.get('cache-control')!r}, no {no.headers.get('cache-control')!r}"
    assert (png_size(yes.content), png_size(no.content)) == (MATCH_SIZE, NO_MATCH_SIZE), "the size, 1x1 or 2x1, is the verdict"
    print_success("same status, same type, same cache header; only the size differs")


@pytest.mark.asyncio
@pytest.mark.parametrize("session", ["no-cookie", "forged-cookie"])
async def test_image_probe_needs_no_session(app, monkeypatch, session):
    """AP-IMG-04: public, and reading no session: with no cookie or a forged one, the same answers (1x1 for a nonce of
    this instance, 2x1 for its forgery)."""
    print_section(f"AP-IMG-04: GET {IMAGE_PATH} with {session}")
    headers = None if session == "no-cookie" else {"Cookie": f"{COOKIE}=forged-{uuid4().hex}"}
    good = _issue(monkeypatch, key=KEY_A)
    with _instance_key(monkeypatch, KEY_A):
        _assert_image(await _get(app, IMAGE_PATH, params={"nonce": good}, headers=headers), MATCH_SIZE, f"an issued nonce, with {session}")
        _assert_image(await _get(app, IMAGE_PATH, params={"nonce": _with_last_byte_flipped(good)}, headers=headers), NO_MATCH_SIZE, f"a forged nonce, with {session}")
    print_success(f"{session}: 1x1 for the nonce, 2x1 for its forgery")


# =============================================================================
# 2. Where the route lives, and what the block lets through
# =============================================================================


def test_the_image_route_has_a_module_of_its_own_and_auth_py_does_not_define_it():
    """AP-IMG-05: the route lives in ``api/v1/address_probe_image.py``; ``auth.py`` (workstream E edits it next) never names
    ``address-probe.png``, and the new module serves exactly that path."""
    print_section("AP-IMG-05: the route's module")
    module_file = API_V1_DIR / "address_probe_image.py"
    assert module_file.is_file(), f"the image probe lives in {module_file.relative_to(BACKEND_DIR.parent)}: the module does not exist"
    assert "address-probe.png" not in (API_V1_DIR / "auth.py").read_text(encoding="utf-8"), "auth.py must not define the image probe: its route is in address_probe_image.py"
    assert IMAGE_PATH in module_file.read_text(encoding="utf-8"), f"address_probe_image.py serves the route path {IMAGE_PATH}"
    print_success("address_probe_image.py exists, serves the path; auth.py does not")


def _image_route_endpoint(app: FastAPI):
    """The endpoint function of the one GET route of the app at ``/api/v1/auth/address-probe.png``; the test fails when it is
    not exactly one. Through ``iter_route_contexts``: an included router is a lazy ``_IncludedRouter`` in ``app.routes``,
    whose routes a plain iteration does not see (as ``test_instance_block.py`` walks them)."""
    from fastapi.routing import APIRoute, iter_route_contexts  # noqa: PLC0415 — only this helper walks the routes

    path = f"{API_V1_PREFIX}{IMAGE_PATH}"
    endpoints = []
    for context in iter_route_contexts(app.routes):
        starlette_route = getattr(context, "starlette_route", None)
        context_path = getattr(starlette_route, "path", None) if starlette_route is not None else context.path
        if context_path == path and isinstance(context.original_route, APIRoute) and "GET" in (context.methods or ()):
            endpoints.append(context.original_route.endpoint)
    assert len(endpoints) == 1, f"the app must serve GET {path} with exactly one endpoint, found {len(endpoints)}"
    return endpoints[0]


def test_the_image_endpoint_is_in_the_module_and_not_allowed_when_blocked(app):
    """AP-IMG-06: the endpoint of the image route is defined in ``address_probe_image`` (not in ``auth``), is a plain
    ``def`` (the key read is file I/O) and is NOT in ``instance_block.ALLOWED_WHEN_BLOCKED``, like the JSON probe (decision
    A6a): on a blocked instance it answers the 401 of a public route outside the list, read as «cannot verify». That 401
    is pinned with a request in ``test_instance_block.py`` (``PUBLIC_READS_OUTSIDE_THE_LIST``)."""
    print_section("AP-IMG-06: the endpoint and the block")
    import inspect  # noqa: PLC0415 — only this test inspects the endpoint

    from backend.app.api.v1.instance_block import ALLOWED_WHEN_BLOCKED  # noqa: PLC0415

    module = importlib.import_module(IMAGE_MODULE)
    endpoint = _image_route_endpoint(app)
    assert endpoint.__module__ == module.__name__, f"the endpoint is defined in {module.__name__}, not in {endpoint.__module__}"
    assert not inspect.iscoroutinefunction(endpoint), "the endpoint is a sync def: deriving the key reads a file, which must not block the event loop"
    assert endpoint not in ALLOWED_WHEN_BLOCKED, f"{endpoint.__module__}.{endpoint.__name__} must stay outside instance_block.ALLOWED_WHEN_BLOCKED, like the JSON probe (decision A6a)"
    print_success(f"{endpoint.__module__}.{endpoint.__name__}: a sync def, outside the allowed list")


# =============================================================================
# 3. Barrier: the JSON route stays as it is
# =============================================================================


@pytest.mark.asyncio
async def test_the_json_probe_still_answers_as_before(app, monkeypatch):
    """AP-IMG-07 (barrier, green today and after): ``GET /auth/address-probe`` still answers 200 ``{"match": <bool>}`` with
    ``Access-Control-Allow-Origin: *`` and ``Cache-Control: no-store`` — for curl and older clients — true for a nonce
    of this instance, false for its forgery."""
    print_section(f"AP-IMG-07: GET {JSON_PATH} is unchanged")
    good = _issue(monkeypatch, key=KEY_A)
    with _instance_key(monkeypatch, KEY_A):
        yes = await _get(app, JSON_PATH, params={"nonce": good})
        no = await _get(app, JSON_PATH, params={"nonce": _with_last_byte_flipped(good)})
    for response, verdict in ((yes, True), (no, False)):
        assert response.status_code == 200 and response.json() == {"match": verdict}, f"GET {JSON_PATH}: expected 200 {{'match': {verdict}}}, got {response.status_code} {response.text!r}"
        assert response.headers.get_list("access-control-allow-origin") == ["*"], f"GET {JSON_PATH}: Access-Control-Allow-Origin must be * once: {response.headers.get_list('access-control-allow-origin')!r}"
        assert "no-store" in _cache_directives(response), f"GET {JSON_PATH}: Cache-Control no-store: {response.headers.get('cache-control')!r}"
    print_success("the JSON route: true for the nonce, false for its forgery, both headers")
