"""
Test Suite: GET /uploads/file/{id} — preview, download and MIME branches.

Covers Phase 7 Part 3 Closure_2 G-batch7 §2: ``serve_file`` was at 13%
coverage with only the 404 guard exercised. This suite locks the
business-logic surface:

- Plain serve (no flags) returns the original bytes with the stored MIME.
- Text preview (``offset`` + ``window``) returns a sliced UTF-8 window.
- Text preview rejected with 400 for non-text MIME.
- Image preview (``img_preview=WxH``) returns a resized image.
- Image preview rejected with 400 for non-image MIME.
- Image preview rejected with 400 for malformed dimensions.
- ``download=true`` sets a Content-Disposition with the original filename.

Decision 36 (scope of uploaded files, red until it lands), as three fixture users of populate_mock_data.py (helpers of
test_uploads_api.py, the lane populated): a personal file is served in every mode (plain, download, image preview,
text window) to its owner and the admin, and to anyone else answers like a file that does not exist, a thumbnail
already cached included; a common one is served to everyone; image previews go out ``Cache-Control: private``.

Plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G-batch7 #2.
"""

from __future__ import annotations

import time
import uuid
from io import BytesIO

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_api.test_uploads_api import (
    SCOPE_TEXT,
    Actor,
    hidden_problem,
    media_type,
    scope_lane,
    scope_name,
)
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


# ============================================================================
# Fixtures & helpers
# ============================================================================


def _uname() -> str:
    return f"g7sf_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"


async def _create_user_and_login(client: httpx.AsyncClient) -> None:
    username = _uname()
    password = "TestPass123!"
    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": f"{username}@test.com", "password": password},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 201, resp.text
    login = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT,
    )
    assert login.status_code == 200, login.text
    session = login.cookies.get("session")
    if session:
        client.cookies.set("session", session)


async def _upload(client: httpx.AsyncClient, name: str, content: bytes, mime: str) -> str:
    """Upload a file and return its file_id."""
    files = {"file": (name, BytesIO(content), mime)}
    resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return resp.json()["file"]["id"]


def _png_bytes(width: int = 64, height: int = 48) -> bytes:
    """Build a real PNG via Pillow so server-side resize works."""
    from PIL import Image  # noqa: PLC0415 — local import, test-only

    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _image_size(content: bytes) -> tuple[int, int]:
    """The pixel size of an image answer."""
    from PIL import Image  # noqa: PLC0415 — local import, test-only

    return Image.open(BytesIO(content)).size


def _cache_directives(response: httpx.Response) -> set[str]:
    """The directive names of ``Cache-Control``, lower case: ``private, max-age=3600`` → {"private", "max-age"}."""
    return {part.split("=", 1)[0].strip().lower() for part in response.headers.get("cache-control", "").split(",") if part.strip()}


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as srv:
        if not srv.start_server():
            pytest.fail("Failed to start test server")
        yield srv


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_serve_plain_returns_full_content(test_server):
    """G7§2.1 — Plain GET returns the uploaded bytes verbatim."""
    print_section("G7§2.1: serve plain content")
    async with httpx.AsyncClient() as client:
        await _create_user_and_login(client)
        content = b"plain text body line one\nline two\n"
        fid = await _upload(client, "plain.txt", content, "text/plain")
        resp = await client.get(f"{API_BASE}/uploads/file/{fid}", timeout=TIMEOUT)
        assert resp.status_code == 200
        assert resp.content == content
        assert resp.headers.get("content-type", "").startswith("text/plain")
        print_success("✓ Plain serve returns original bytes")


@pytest.mark.asyncio
async def test_text_preview_returns_window(test_server):
    """G7§2.2 — Text preview slices the file via offset/window."""
    print_section("G7§2.2: text preview window")
    async with httpx.AsyncClient() as client:
        await _create_user_and_login(client)
        body = b"".join(f"line-{i:03d}\n".encode() for i in range(50))
        fid = await _upload(client, "doc.txt", body, "text/plain")
        # Read 20 bytes starting at offset 9 → "line-001\nline-002\nl"
        resp = await client.get(
            f"{API_BASE}/uploads/file/{fid}",
            params={"offset": 9, "window": 20},
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200
        text = resp.text
        assert "line-001" in text
        assert len(text) <= 20
        print_success("✓ Text preview returns sliced window")


@pytest.mark.asyncio
async def test_text_preview_rejected_for_image_mime(test_server):
    """G7§2.3 — Text preview on image/* returns 400 with explanatory detail."""
    print_section("G7§2.3: text preview rejected on image MIME")
    async with httpx.AsyncClient() as client:
        await _create_user_and_login(client)
        fid = await _upload(client, "tiny.png", _png_bytes(8, 8), "image/png")
        resp = await client.get(
            f"{API_BASE}/uploads/file/{fid}",
            params={"offset": 0, "window": 100},
            timeout=TIMEOUT,
        )
        assert resp.status_code == 400
        assert "text preview" in resp.json()["detail"].lower()
        print_success("✓ Text preview rejected with 400 on image MIME")


@pytest.mark.asyncio
async def test_image_preview_resizes(test_server):
    """G7§2.4 — Image preview returns a resized image with cache headers (private since decision 36)."""
    print_section("G7§2.4: image preview resizes")
    async with httpx.AsyncClient() as client:
        await _create_user_and_login(client)
        original = _png_bytes(width=400, height=300)
        fid = await _upload(client, "big.png", original, "image/png")
        resp = await client.get(
            f"{API_BASE}/uploads/file/{fid}",
            params={"img_preview": "100x100"},
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("image/")
        directives = _cache_directives(resp)
        assert "private" in directives and "public" not in directives, f"a thumbnail is content behind the login: Cache-Control {resp.headers.get('cache-control')!r}"
        # Resized image should be smaller than the original
        assert 0 < len(resp.content) <= len(original)
        # Re-fetch hits the in-process preview cache (still 200, same bytes)
        resp2 = await client.get(
            f"{API_BASE}/uploads/file/{fid}",
            params={"img_preview": "100x100"},
            timeout=TIMEOUT,
        )
        assert resp2.status_code == 200
        assert resp2.content == resp.content
        print_success("✓ Image preview resized + cache hit")


@pytest.mark.asyncio
async def test_image_preview_rejected_for_text_mime(test_server):
    """G7§2.5 — Image preview on text/* returns 400."""
    print_section("G7§2.5: image preview rejected on text MIME")
    async with httpx.AsyncClient() as client:
        await _create_user_and_login(client)
        fid = await _upload(client, "doc.txt", b"hello", "text/plain")
        resp = await client.get(
            f"{API_BASE}/uploads/file/{fid}",
            params={"img_preview": "200x200"},
            timeout=TIMEOUT,
        )
        assert resp.status_code == 400
        assert "image preview" in resp.json()["detail"].lower()
        print_success("✓ Image preview rejected with 400 on text MIME")


@pytest.mark.asyncio
async def test_image_preview_invalid_dimensions(test_server):
    """G7§2.6 — Malformed ``img_preview`` value returns 400."""
    print_section("G7§2.6: image preview invalid dimensions")
    async with httpx.AsyncClient() as client:
        await _create_user_and_login(client)
        fid = await _upload(client, "img.png", _png_bytes(), "image/png")
        resp = await client.get(
            f"{API_BASE}/uploads/file/{fid}",
            params={"img_preview": "not-a-size"},
            timeout=TIMEOUT,
        )
        assert resp.status_code == 400
        assert "WIDTHxHEIGHT" in resp.json()["detail"] or "format" in resp.json()["detail"].lower()
        print_success("✓ Invalid dimensions rejected with 400")


@pytest.mark.asyncio
async def test_download_flag_sets_original_filename(test_server):
    """G7§2.7 — ``download=true`` adds Content-Disposition with original name."""
    print_section("G7§2.7: download flag sets filename")
    async with httpx.AsyncClient() as client:
        await _create_user_and_login(client)
        original_name = f"my-report-{uuid.uuid4().hex[:6]}.txt"
        fid = await _upload(client, original_name, b"download me", "text/plain")
        resp = await client.get(
            f"{API_BASE}/uploads/file/{fid}",
            params={"download": "true"},
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200
        cd = resp.headers.get("content-disposition", "")
        # FastAPI's FileResponse sets ``filename=`` (and may add filename* RFC5987)
        assert original_name in cd, f"Expected '{original_name}' in {cd!r}"
        print_success("✓ Download flag sets original filename in Content-Disposition")


@pytest.mark.asyncio
async def test_serve_unknown_id_returns_404(test_server):
    """G7§2.8 — Unknown file id returns 404 (regression guard)."""
    print_section("G7§2.8: unknown id 404")
    async with httpx.AsyncClient() as client:
        await _create_user_and_login(client)
        resp = await client.get(
            f"{API_BASE}/uploads/file/{uuid.uuid4().hex}",
            timeout=TIMEOUT,
        )
        assert resp.status_code == 404
        print_success("✓ Unknown id returns 404")


# ============================================================================
# Scope of uploaded files (decision 36): every mode of GET /uploads/file/{id}
# ============================================================================


def _serve_cases(image: dict, text: dict) -> list[tuple[str, dict, dict]]:
    """Every mode of GET /uploads/file/{id}: (label, the file, the query)."""
    return [
        ("plain image", image, {}),
        ("download image", image, {"download": "true"}),
        ("img_preview 64x64", image, {"img_preview": "64x64"}),
        ("plain text", text, {}),
        ("download text", text, {"download": "true"}),
        ("text window offset=0 window=10", text, {"offset": 0, "window": 10}),
    ]


async def _served_problem(actor: Actor, label: str, file: dict, params: dict, original: bytes) -> str | None:
    """What is wrong with ``actor``'s answer in one mode, on a file they may read, or None."""
    resp = await actor.client.get(f"{API_BASE}/uploads/file/{file['id']}", params=params, timeout=TIMEOUT)
    where = f"{actor.label} GET /uploads/file/{{id}} ({label})"
    if resp.status_code != 200:
        return f"{where}: answers {resp.status_code} {resp.text[:200]!r}, expected 200"
    if "img_preview" in params:
        return None if media_type(resp).startswith("image/") else f"{where}: content-type {resp.headers.get('content-type')!r}, expected an image"
    if "window" in params:
        expected = original.decode()[: params["window"]]
        return None if resp.text == expected else f"{where}: {resp.text!r}, expected {expected!r}"
    if resp.content != original:
        return f"{where}: {len(resp.content)} bytes that are not the uploaded file"
    if params.get("download") == "true" and file["original_name"] not in resp.headers.get("content-disposition", ""):
        return f"{where}: content-disposition {resp.headers.get('content-disposition')!r} does not name {file['original_name']}"
    return None


@pytest.mark.asyncio
async def test_personal_files_are_served_to_owner_and_admin_only(test_server):
    """SCOPE-SERVE-1 — A's personal image and text: A and the admin get every mode, B the answer of a missing file."""
    print_section("SCOPE-SERVE-1: personal files, every mode")
    async with scope_lane() as lane:
        png = _png_bytes(200, 150)
        image = await lane.upload(lane.a, scope_name("serve-personal", ".png"), png, "image/png", scope="personal")
        text = await lane.upload(lane.a, scope_name("serve-personal", ".txt"), SCOPE_TEXT, "text/plain", scope="personal")
        originals = {image["id"]: png, text["id"]: SCOPE_TEXT}
        cases = _serve_cases(image, text)

        # Every mode answers its owner: the barrier that gives B's 404 its meaning.
        problems = [problem for label, file, params in cases if (problem := await _served_problem(lane.a, label, file, params, originals[file["id"]]))]
        assert not problems, "the owner of the files:\n" + "\n".join(problems)

        problems = [f"({label}) {problem}" for label, file, params in cases if (problem := await hidden_problem(lane.b, "GET", "/uploads/file/{id}", file["id"], params=params))]
        problems += [problem for label, file, params in cases if (problem := await _served_problem(lane.admin, label, file, params, originals[file["id"]]))]
        assert not problems, f"A's personal files, {len(problems)} problem(s):\n" + "\n".join(problems)
        print_success("✓ Personal files: every mode to A and the admin, 404 to B")


@pytest.mark.asyncio
async def test_common_files_are_served_to_everyone(test_server):
    """SCOPE-SERVE-2 — A's common image (inherited) and text (asked): every mode to A, B and the admin.

    Green before decision 36 too, nothing being hidden yet: it guards that the new check hides personal files only."""
    print_section("SCOPE-SERVE-2: common files, every mode")
    async with scope_lane() as lane:
        png = _png_bytes(200, 150)
        image = await lane.upload(lane.a, scope_name("serve-common", ".png"), png, "image/png")  # no scope: an image inherits common
        text = await lane.upload(lane.a, scope_name("serve-common", ".txt"), SCOPE_TEXT, "text/plain", scope="common")
        originals = {image["id"]: png, text["id"]: SCOPE_TEXT}

        problems = [problem for actor in (lane.a, lane.b, lane.admin) for label, file, params in _serve_cases(image, text) if (problem := await _served_problem(actor, label, file, params, originals[file["id"]]))]
        assert not problems, f"A's common files, {len(problems)} problem(s):\n" + "\n".join(problems)
        print_success("✓ Common files: every mode to everyone")


@pytest.mark.asyncio
async def test_cached_thumbnail_of_a_personal_image_is_not_served_to_others(test_server):
    """SCOPE-SERVE-3 — once A's thumbnail is in the preview cache, B still gets the answer of a missing file."""
    print_section("SCOPE-SERVE-3: cached thumbnail, another user")
    async with scope_lane() as lane:
        image = await lane.upload(lane.a, scope_name("thumb-personal", ".png"), _png_bytes(200, 150), "image/png", scope="personal")
        url = f"{API_BASE}/uploads/file/{image['id']}"
        params = {"img_preview": "64x64"}

        first = await lane.a.client.get(url, params=params, timeout=TIMEOUT)
        assert first.status_code == 200, f"A's thumbnail: {first.status_code} {first.text[:200]}"
        assert _image_size(first.content) == (64, 48), "precondition: a generated thumbnail, the kind the preview cache keeps"
        again = await lane.a.client.get(url, params=params, timeout=TIMEOUT)
        assert (again.status_code, again.content) == (200, first.content), "precondition: the thumbnail answers again, now from the cache"

        problem = await hidden_problem(lane.b, "GET", "/uploads/file/{id}", image["id"], params=params)
        assert problem is None, f"with A's thumbnail cached: {problem}"
        admin = await lane.admin.client.get(url, params=params, timeout=TIMEOUT)
        assert (admin.status_code, admin.content) == (200, first.content), f"the admin's thumbnail: {admin.status_code}"
        print_success("✓ Cached thumbnail not served to another user")


@pytest.mark.asyncio
async def test_image_preview_answers_are_private(test_server):
    """SCOPE-SERVE-4 — img_preview answers carry Cache-Control private, never public: generated, cached, or the original
    served as it is (smaller than the box), for a common and a personal image."""
    print_section("SCOPE-SERVE-4: Cache-Control of image previews")
    async with scope_lane() as lane:
        problems = []
        for scope in (None, "personal"):
            png = _png_bytes(200, 150)
            image = await lane.upload(lane.a, scope_name("cache-control", ".png"), png, "image/png", scope=scope)
            url = f"{API_BASE}/uploads/file/{image['id']}"
            generated = await lane.a.client.get(url, params={"img_preview": "64x64"}, timeout=TIMEOUT)
            cached = await lane.a.client.get(url, params={"img_preview": "64x64"}, timeout=TIMEOUT)
            as_is = await lane.a.client.get(url, params={"img_preview": "1600x1600"}, timeout=TIMEOUT)
            assert (generated.status_code, cached.status_code, as_is.status_code) == (200, 200, 200)
            assert _image_size(generated.content) == (64, 48) and cached.content == generated.content and as_is.content == png, "precondition: a generated thumbnail, the same from the cache, and the original as it is"

            for label, resp in (("generated", generated), ("cached", cached), ("original, smaller than the box", as_is)):
                directives = _cache_directives(resp)
                if "private" not in directives or "public" in directives:
                    problems.append(f"{scope or 'inherited common'} image, {label} preview: Cache-Control {resp.headers.get('cache-control')!r}")
        assert not problems, "image previews are content behind the login, never for a shared cache:\n" + "\n".join(problems)
        print_success("✓ Image previews are private")


@pytest.mark.asyncio
async def test_mismatched_modes_on_a_personal_file_are_404_never_400(test_server):
    """SCOPE-SERVE-5 — modes that do not fit the file: a thumbnail of a text file, a text window on an image, a malformed
    img_preview. The owner gets the 400 that names the problem; B gets the answer of a missing file, never that 400,
    which would tell B the file exists, and its type."""
    print_section("SCOPE-SERVE-5: mismatched modes, another user")
    async with scope_lane() as lane:
        image = await lane.upload(lane.a, scope_name("mismatch-personal", ".png"), _png_bytes(200, 150), "image/png", scope="personal")
        text = await lane.upload(lane.a, scope_name("mismatch-personal", ".txt"), SCOPE_TEXT, "text/plain", scope="personal")
        cases = [
            ("img_preview on a text file", text, {"img_preview": "64x64"}),
            ("text window on an image", image, {"offset": 0, "window": 10}),
            ("malformed img_preview", image, {"img_preview": "not-a-size"}),
        ]

        # The owner gets the 400: these modes really do not fit, so the 404 B gets below is the hidden-file answer.
        problems = []
        for label, file, params in cases:
            resp = await lane.a.client.get(f"{API_BASE}/uploads/file/{file['id']}", params=params, timeout=TIMEOUT)
            if resp.status_code != 400:
                problems.append(f"A ({label}): answers {resp.status_code} {resp.text[:200]!r}, expected 400")
        assert not problems, "the owner of the files:\n" + "\n".join(problems)

        problems = [f"({label}) {problem}" for label, file, params in cases if (problem := await hidden_problem(lane.b, "GET", "/uploads/file/{id}", file["id"], params=params))]
        assert not problems, "A's personal files, modes that do not fit:\n" + "\n".join(problems)
        print_success("✓ Mismatched modes: 400 to the owner, the missing-file 404 to B")
