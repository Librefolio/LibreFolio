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

Plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G-batch7 #2.
"""

from __future__ import annotations

import time
import uuid
from io import BytesIO

import httpx
import pytest

from backend.app.config import get_settings
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
    """G7§2.4 — Image preview returns a resized image with cache headers."""
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
        assert resp.headers.get("cache-control", "").startswith("public")
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

