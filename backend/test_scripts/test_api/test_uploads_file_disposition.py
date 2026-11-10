"""
Test Suite: GET /uploads/file/{id} — shown in place or downloaded (H6-2, backlog H-44).

A PDF shown in an ``<iframe>`` (the file preview's fallback, ``source_url``) used to download, because the normal
serving branch always answered ``Content-Disposition: attachment``. The contract, the one the broker route
``/import/files/{id}/download`` already follows:

- the report types that cannot carry active content (``INLINE_SAFE_MEDIA_TYPES``, one set in
  ``services/files/inline_media.py`` shared by both routes) are served ``inline`` with their own media type;
  every other stored type (html, svg, xhtml, xml, octet-stream, unknown) stays ``attachment`` and keeps its media type;
- ``download=true`` is always ``attachment`` with the original file name, a PDF included;
- every normal-serving answer, inline or attachment, carries ``X-Content-Type-Options: nosniff``;
- unchanged: no session → 401.

Rows are identified by what each test uploaded; the expected set is written here as a literal, so the test does not
agree with the product by importing the very thing it checks (except the identity check of the shared set).
"""

from __future__ import annotations

import email.message
import uuid
from io import BytesIO

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_api.test_uploads_serve_file import _create_user_and_login, _png_bytes
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0

# The contract, as a literal: what may be shown in place.
EXPECTED_INLINE_SAFE = frozenset(
    {
        "application/pdf",
        "application/json",
        "text/plain",
        "text/csv",
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "image/bmp",
    }
)

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
CSV_BYTES = b"date,amount\n2026-01-01,10\n2026-01-02,20\n"
HTML_BYTES = b"<!DOCTYPE html><html><head><title>t</title></head><body><script>1</script><p>hello</p></body></html>"
SVG_BYTES = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4"/></svg>'
XHTML_BYTES = b'<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><body><p>x</p></body></html>'

# (label, file extension, bytes factory, declared type, must be shown in place: None = whatever the stored type says)
CASES = [
    ("pdf", ".pdf", lambda: PDF_BYTES, "application/pdf", True),
    ("png", ".png", _png_bytes, "image/png", True),
    ("csv", ".csv", lambda: CSV_BYTES, "text/csv", None),
    ("html", ".html", lambda: HTML_BYTES, "text/html", False),
    ("svg", ".svg", lambda: SVG_BYTES, "image/svg+xml", False),
    ("xhtml", ".xhtml", lambda: XHTML_BYTES, "application/xhtml+xml", False),
]


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as srv:
        if not srv.start_server():
            pytest.fail("Failed to start test server")
        yield srv


async def _upload(client: httpx.AsyncClient, extension: str, content: bytes, declared: str) -> tuple[str, str, str]:
    """Upload a file named by this test and return (file id, original name, STORED media type, from the upload answer)."""
    name = f"h62-{uuid.uuid4().hex[:8]}{extension}"
    resp = await client.post(f"{API_BASE}/uploads", files={"file": (name, BytesIO(content), declared)}, timeout=TIMEOUT)
    assert resp.status_code == 200, f"upload of {name} ({declared}): {resp.status_code} {resp.text[:200]}"
    file = resp.json()["file"]
    return file["id"], name, (file["mime_type"] or "").split(";")[0].strip().lower()


def content_disposition(header: str) -> tuple[str | None, str | None]:
    """The disposition type and the file name of a ``Content-Disposition`` header, its quoting or encoding undone (as test_backup_api.py)."""
    message = email.message.Message()
    message["Content-Disposition"] = header
    return message.get_content_disposition(), message.get_filename()


def _media_type(resp: httpx.Response) -> str:
    return resp.headers.get("content-type", "").split(";")[0].strip().lower()


def test_inline_safe_set_is_one_shared_object_without_active_types():
    """H6-2.1 — brokers and uploads use the identical set, from services/files/inline_media.py; no html/svg/xml/js in it."""
    print_section("H6-2.1: shared INLINE_SAFE_MEDIA_TYPES")
    from backend.app.api.v1.brokers import files as brokers  # noqa: PLC0415 — test-only
    from backend.app.services.files import inline_media  # noqa: PLC0415 — red until the shared module exists

    assert inline_media.INLINE_SAFE_MEDIA_TYPES == EXPECTED_INLINE_SAFE
    assert brokers.INLINE_SAFE_MEDIA_TYPES is inline_media.INLINE_SAFE_MEDIA_TYPES, "the broker route keeps no copy of the set"
    active = [m for m in inline_media.INLINE_SAFE_MEDIA_TYPES if any(word in m for word in ("html", "svg", "xml", "javascript", "ecmascript"))]
    assert not active, f"types that can run in the page's origin: {active}"
    print_success("✓ one shared set, no active content type")


@pytest.mark.asyncio
@pytest.mark.parametrize("label,extension,make,declared,must_inline", CASES, ids=[c[0] for c in CASES])
async def test_plain_serve_disposition_follows_the_stored_type(test_server, label, extension, make, declared, must_inline):
    """H6-2.2 — no ``download``: inline with its own type when the STORED type is in the safe set, attachment otherwise."""
    print_section(f"H6-2.2: plain serve, {label}")
    content = make()
    async with httpx.AsyncClient() as client:
        await _create_user_and_login(client)
        fid, name, stored = await _upload(client, extension, content, declared)
        inline = stored in EXPECTED_INLINE_SAFE
        if must_inline is not None:
            assert inline is must_inline, f"precondition: {label} is stored as {stored!r}"

        resp = await client.get(f"{API_BASE}/uploads/file/{fid}", timeout=TIMEOUT)
        assert resp.status_code == 200, resp.text[:200]
        assert resp.content == content
        disposition, _ = content_disposition(resp.headers.get("content-disposition", ""))
        assert disposition == ("inline" if inline else "attachment"), f"{label} stored as {stored!r}: Content-Disposition {resp.headers.get('content-disposition')!r}"
        assert _media_type(resp) == stored, f"the stored media type is kept: {resp.headers.get('content-type')!r}"
        assert resp.headers.get("x-content-type-options", "").lower() == "nosniff"
        print_success(f"✓ {label} ({stored}): {disposition}")


@pytest.mark.asyncio
@pytest.mark.parametrize("label,extension,make,declared,must_inline", CASES, ids=[c[0] for c in CASES])
async def test_download_flag_is_always_an_attachment_with_the_original_name(test_server, label, extension, make, declared, must_inline):
    """H6-2.3 — ``download=true``: attachment with the original file name for every type, a PDF included, nosniff too."""
    print_section(f"H6-2.3: download=true, {label}")
    async with httpx.AsyncClient() as client:
        await _create_user_and_login(client)
        fid, name, stored = await _upload(client, extension, make(), declared)

        resp = await client.get(f"{API_BASE}/uploads/file/{fid}", params={"download": "true"}, timeout=TIMEOUT)
        assert resp.status_code == 200, resp.text[:200]
        disposition, filename = content_disposition(resp.headers.get("content-disposition", ""))
        assert disposition == "attachment", f"{label}: Content-Disposition {resp.headers.get('content-disposition')!r}"
        assert filename == name
        assert resp.headers.get("x-content-type-options", "").lower() == "nosniff"
        print_success(f"✓ {label}: attachment named {name}")


@pytest.mark.asyncio
async def test_plain_serve_needs_a_session(test_server):
    """H6-2.4 — unchanged: without a session the file is a 401, whatever its type."""
    print_section("H6-2.4: no session")
    async with httpx.AsyncClient() as owner:
        await _create_user_and_login(owner)
        fid, _, _ = await _upload(owner, ".pdf", PDF_BYTES, "application/pdf")
    async with httpx.AsyncClient() as anonymous:
        resp = await anonymous.get(f"{API_BASE}/uploads/file/{fid}", timeout=TIMEOUT)
        assert resp.status_code == 401, resp.status_code
    print_success("✓ 401 without a session")
