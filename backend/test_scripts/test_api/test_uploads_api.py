"""
Uploads API Tests.

Tests for static file upload endpoints:
- POST /uploads: Upload file
- GET /uploads: List files
- GET /uploads/{id}: File info
- GET /uploads/{id}/preview: Structured preview payload
- GET /uploads/file/{id}: Download file
- DELETE /uploads/{id}: Delete file
- PATCH /uploads/{id}: Change the scope of a file (decision 36)
- GET /uploads/plugin/{type}/{path}: Serve plugin static asset, and the icons bundled with the BRIM plugins

Decision 36 (scope of uploaded files, red until it lands): a common file is read by every signed-in user, a personal
one by its owner and the admin only; to anyone else it answers exactly like a file that does not exist. The SCOPE-*
tests run as three fixture users of populate_mock_data.py — A (e2e_test_user), B (e2e_test_user2) and the admin
(e2e_test_admin) —, so the lane must be populated (db populate --force); each deletes the files it wrote.
"""

import io
import json
import mimetypes
import os
import threading
import uuid
import zipfile
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from backend.app.api.v1 import uploads as uploads_api
from backend.app.config import get_settings
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.files.static_uploads import get_uploads_dir
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, print_warning

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30
# The test server's origin: a plugin's icon_url is a path on it.
SERVER_BASE = f"http://localhost:{settings.TEST_PORT}"
# The URL of a file of the BRIM plugins' static folder (BRIMProvider.generate_static_url), served by GET /uploads/plugin/brim/{path}.
BRIM_STATIC_PREFIX = "/api/v1/uploads/plugin/brim/"


def unique_username() -> str:
    """Generate a unique username."""
    timestamp = int(datetime.now().timestamp() * 1000)
    return f"upload_test_{timestamp}"


# ============================================================================
# HELPERS
# ============================================================================


async def create_user_and_login(client: httpx.AsyncClient) -> tuple[int, str]:
    """Create user, login, return (user_id, username)."""
    username = unique_username()
    email = f"{username}@test.com"
    password = "TestPass123!"

    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )
    user_id = resp.json()["user"]["id"]

    login_resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)
    session = login_resp.cookies.get("session")
    if session:
        client.cookies.set("session", session)

    return user_id, username


def create_test_file(name: str = "test.txt", content: bytes = b"Hello World") -> tuple[str, bytes]:
    """Create a test file for upload."""
    return name, content


def create_png_bytes(width: int = 64, height: int = 48) -> bytes:
    """Create a real PNG image for preview tests."""
    from PIL import Image  # noqa: PLC0415 — test-only local import

    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def create_xlsx_bytes() -> bytes:
    """Create a workbook with sparse cells and multiple sheets."""
    from openpyxl import Workbook  # noqa: PLC0415 — test-only local import

    workbook = Workbook()
    summary = workbook.active
    summary.title = "Summary"
    summary["A1"] = "Name"
    summary["B1"] = "Amount"
    summary["A2"] = "Cash"
    summary["C3"] = "Sparse"

    details = workbook.create_sheet("Details")
    details["A1"] = "Date"
    details["B1"] = "Type"
    details["A2"] = "2025-01-01"
    details["B2"] = "BUY"

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def create_damaged_xlsx_bytes() -> bytes:
    """Create synthetic bytes for a file named .xlsx that are no workbook, not even a zip archive (F2)."""
    return b"LibreFolio F2 synthetic bytes: not an Excel workbook and not a zip archive.\n" * 16


def create_minimal_pdf_bytes() -> bytes:
    """Create a tiny but valid PDF file."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Contents 4 0 R>>endobj\n"
        b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 72 120 Td (Preview PDF) Tj ET\nendstream endobj\n"
        b"xref\n0 5\n0000000000 65535 f \n"
        b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n256\n%%EOF\n"
    )


def read_sample_xls_bytes() -> bytes:
    """Read committed legacy XLS sample for preview coverage."""
    sample_path = Path(__file__).resolve().parents[3] / "backend" / "staticResources" / "FilePreviewSamples" / "file_example_XLS_10.xls"
    return sample_path.read_bytes()


def media_type(response: httpx.Response) -> str:
    """The media type of a response's content-type, without its parameters."""
    return response.headers.get("content-type", "").split(";")[0].strip().lower()


async def bundled_icon_problem(client: httpx.AsyncClient, code: str, icon_url: str) -> str | None:
    """GET a BRIM plugin's bundled icon on the test server; what is wrong with the answer (status, image type of the file, its bytes), or None.

    ``icon_url`` must start with ``BRIM_STATIC_PREFIX``: the request goes to the test server, never to a third party."""
    asset_path = uploads_api.PLUGIN_STATIC_DIRS["brim"] / icon_url.removeprefix(BRIM_STATIC_PREFIX)
    expected_type = mimetypes.guess_type(asset_path.name)[0] or ""
    response = await client.get(f"{SERVER_BASE}{icon_url}", timeout=TIMEOUT)
    if response.status_code != 200:
        return f"{code}: GET {icon_url} answers {response.status_code}"
    if not expected_type.startswith("image/") or media_type(response) != expected_type:
        return f"{code}: GET {icon_url} has content-type {response.headers.get('content-type')!r}, the image type of {asset_path.name} is {expected_type!r}"
    if response.content != asset_path.read_bytes():
        return f"{code}: GET {icon_url} answers {len(response.content)} bytes that are not the file {asset_path}"
    return None


class _DirectUploadFile:
    """Minimal UploadFile test double for direct endpoint unit tests."""

    def __init__(self, filename: str, content: bytes, content_type: str):
        self.filename = filename
        self.content_type = content_type
        self._content = content

    async def read(self) -> bytes:
        return self._content


# ============================================================================
# SCOPE OF UPLOADED FILES (decision 36) — HELPERS
# ============================================================================
#
# Also imported by test_uploads_serve_file.py, for the modes of GET /uploads/file/{id}.

#: The fixture users of populate_mock_data.py: A owns the files, B is another user, and the admin.
E2E_USER = ("e2e_test_user", "E2eTestPass123!")
E2E_USER2 = ("e2e_test_user2", "E2eTestPass456!")
E2E_ADMIN = ("e2e_test_admin", "E2eAdminPass123!")

#: What every route answers for a file that does not exist; another user's personal file answers exactly the same.
NOT_FOUND = {"detail": "File not found"}

SCOPE_TEXT = b"decision 36 scope probe: line one\nline two\n"


def scope_name(label: str, ext: str) -> str:
    """A file name that tells the test's files apart in a log: the ids identify them, never the name."""
    return f"scope-{label}-{uuid.uuid4().hex[:10]}{ext}"


def response_body(response: httpx.Response):
    """The JSON body of an answer, its text when it is not JSON."""
    try:
        return response.json()
    except ValueError:
        return response.text


@dataclass(eq=False)
class Actor:
    """A fixture user signed in on a client of their own."""

    label: str
    client: httpx.AsyncClient
    user_id: int
    is_admin: bool


async def sign_in(client: httpx.AsyncClient, label: str, username: str, password: str, *, admin: bool) -> Actor:
    """Sign a fixture user in; the precondition (the lane is populated, the role is the one the test needs) is checked."""
    resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)
    assert resp.status_code == 200, f"{username} cannot sign in ({resp.status_code} {resp.text}): the SCOPE tests need the lane populated (db populate --force)"
    session = resp.cookies.get("session")
    if session:
        client.cookies.set("session", session)
    user = resp.json()["user"]
    assert user["is_superuser"] is admin, f"precondition: {username} has is_superuser={user['is_superuser']}, the test needs {admin}"
    return Actor(label, client, user["id"], admin)


@dataclass
class ScopeLane:
    """A (e2e_test_user), B (e2e_test_user2) and the admin. Whoever writes cleans up: every file uploaded or written
    through the lane is deleted on exit, by its owner, else by the admin."""

    a: Actor
    b: Actor
    admin: Actor
    files: list[tuple[Actor, str]] = field(default_factory=list)
    paths: list[Path] = field(default_factory=list)

    async def upload(self, actor: Actor, name: str, content: bytes, mime: str, scope: str | None = None) -> dict:
        """POST /uploads as ``actor``, with the multipart field ``scope`` when given; the file of the answer."""
        data = None if scope is None else {"scope": scope}
        resp = await actor.client.post(f"{API_BASE}/uploads", files={"file": (name, BytesIO(content), mime)}, data=data, timeout=TIMEOUT)
        assert resp.status_code == 200, f"{actor.label} could not upload {name} (scope={scope}): {resp.status_code} {resp.text}"
        uploaded = resp.json()["file"]
        self.files.append((actor, uploaded["id"]))
        return uploaded

    def write_legacy(self, owner_id: int, name: str, content: bytes, mime: str) -> str:
        """Store a file as uploads were stored before decision 36 — a sidecar without ``scope`` — straight into the
        lane's custom-uploads, the folder the lane's server reads; its id. The admin deletes it on exit."""
        file_id = str(uuid.uuid4())
        ext = Path(name).suffix.lower()
        uploads_dir = get_uploads_dir()
        uploads_dir.mkdir(parents=True, exist_ok=True)
        data_path, sidecar_path = uploads_dir / f"{file_id}{ext}", uploads_dir / f"{file_id}.json"
        self.files.append((self.admin, file_id))
        self.paths += [data_path, sidecar_path]
        data_path.write_bytes(content)
        metadata = {
            "id": file_id,
            "original_name": name,
            "extension": ext,
            "mime_type": mime,
            "size_bytes": len(content),
            "uploaded_at": datetime.now(UTC).isoformat(),
            "uploaded_by_user_id": owner_id,
            "description": None,
        }
        # Whole, then renamed: a neighbour listing the folder never reads half a sidecar (nor this temporary, not *.json).
        partial = uploads_dir / f"{file_id}.json.partial"
        partial.write_text(json.dumps(metadata, indent=2))
        os.replace(partial, sidecar_path)
        return file_id

    async def cleanup(self) -> list[str]:
        """Delete every file of the lane; what could not be deleted through the API."""
        leftovers = []
        for deleter, file_id in reversed(self.files):
            resp = await deleter.client.delete(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)
            if resp.status_code == 404 and deleter is not self.admin:
                resp = await self.admin.client.delete(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)
            if resp.status_code not in (200, 404):
                leftovers.append(f"{file_id}: DELETE answered {resp.status_code} {resp.text}")
        for path in self.paths:
            path.unlink(missing_ok=True)
        return leftovers


@asynccontextmanager
async def scope_lane():
    """A, B and the admin, each signed in on a client; on exit every file the test wrote through the lane is deleted."""
    async with httpx.AsyncClient() as a_client, httpx.AsyncClient() as b_client, httpx.AsyncClient() as admin_client:
        lane = ScopeLane(
            a=await sign_in(a_client, "A", *E2E_USER, admin=False),
            b=await sign_in(b_client, "B", *E2E_USER2, admin=False),
            admin=await sign_in(admin_client, "admin", *E2E_ADMIN, admin=True),
        )
        try:
            yield lane
        except BaseException:
            for leftover in await lane.cleanup():
                print_warning(f"cleanup: {leftover}")
            raise
        leftovers = await lane.cleanup()
        assert not leftovers, "files of this test left in the lane:\n" + "\n".join(leftovers)


async def hidden_problem(actor: Actor, method: str, path: str, file_id: str, *, params: dict | None = None, json_body: dict | None = None) -> str | None:
    """What is wrong with ``actor``'s answer on a file that must look missing to them, or None.

    ``path`` holds ``{id}``. The answer must be the one a file that does not exist gets on the same route, query and
    body: 404 {"detail": "File not found"}, so that it does not tell the file exists."""
    where = f"{actor.label} {method} {path} {params or ''}".rstrip()
    missing = await actor.client.request(method, f"{API_BASE}{path.format(id=uuid.uuid4())}", params=params, json=json_body, timeout=TIMEOUT)
    if (missing.status_code, response_body(missing)) != (404, NOT_FOUND):
        return f"{where}: a file that does not exist answers {missing.status_code} {missing.text[:200]!r}, expected 404 {NOT_FOUND}"
    answer = await actor.client.request(method, f"{API_BASE}{path.format(id=file_id)}", params=params, json=json_body, timeout=TIMEOUT)
    if answer.status_code != 404:
        return f"{where}: answers {answer.status_code}, where a file that does not exist answers 404: the file is disclosed"
    if response_body(answer) != NOT_FOUND:
        return f"{where}: answers 404 {answer.text[:200]!r}, a file that does not exist answers {NOT_FOUND}"
    return None


async def read_problem(actor: Actor, path: str, file_id: str, params: dict | None = None) -> str | None:
    """What is wrong with ``actor``'s GET on a file they may read (200 expected), or None."""
    resp = await actor.client.get(f"{API_BASE}{path.format(id=file_id)}", params=params, timeout=TIMEOUT)
    if resp.status_code != 200:
        return f"{actor.label} GET {path} {params or ''}: answers {resp.status_code} {resp.text[:200]!r}, expected 200"
    return None


async def listed(actor: Actor, **params) -> dict[str, dict]:
    """GET /uploads as ``actor``: the items by id."""
    resp = await actor.client.get(f"{API_BASE}/uploads", params=params or None, timeout=TIMEOUT)
    assert resp.status_code == 200, f"{actor.label} GET /uploads {params}: {resp.status_code} {resp.text}"
    return {item["id"]: item for item in resp.json()["items"]}


async def info_of(actor: Actor, file_id: str) -> dict:
    """GET /uploads/{id} as ``actor``, who may read the file."""
    resp = await actor.client.get(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)
    assert resp.status_code == 200, f"{actor.label} GET /uploads/{{id}}: {resp.status_code} {resp.text}"
    return resp.json()


async def patch_scope(actor: Actor, file_id: str, body: dict) -> httpx.Response:
    """PATCH /uploads/{id} as ``actor`` with the JSON ``body``."""
    return await actor.client.patch(f"{API_BASE}/uploads/{file_id}", json=body, timeout=TIMEOUT)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def test_server():
    """Start test server."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# DIRECT ENDPOINT UNIT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_upload_file_direct_happy_path(monkeypatch):
    """UPLOAD-U1: Direct upload_file() call returns save_upload result, with can_delete set for the uploader."""
    captured: dict[str, object] = {}
    expected = uploads_api.UploadFileInfo(
        id="direct-upload-id",
        original_name="direct.txt",
        mime_type="text/plain",
        size_bytes=11,
        uploaded_at=datetime.now(),
        uploaded_by_user_id=42,
        scope=uploads_api.UploadScope.PERSONAL,
        description="Direct path",
        url="/api/v1/uploads/file/direct-upload-id",
    )

    async def fake_get_max_upload_mb(_session) -> int:
        return 5

    def fake_save_upload(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(uploads_api, "get_max_upload_mb", fake_get_max_upload_mb)
    monkeypatch.setattr(uploads_api, "save_upload", fake_save_upload)

    # Called directly, every Form parameter is passed: an omitted one would be FastAPI's Form() marker, not None.
    response = await uploads_api.upload_file(
        file=_DirectUploadFile("direct.txt", b"hello world", "text/plain"),
        description="Direct path",
        scope=None,
        current_user=SimpleNamespace(id=42, is_superuser=False),
        session=object(),
    )

    assert response.file == expected.model_copy(update={"can_delete": True})
    assert captured["original_filename"] == "direct.txt"
    assert captured["description"] == "Direct path"
    assert captured["mime_type"] == "text/plain"
    assert captured["scope"] is None


@pytest.mark.asyncio
async def test_get_upload_file_preview_direct_uses_info_mime_fallback(monkeypatch):
    """UPLOAD-U2: Direct preview call takes the MIME type of the file's info.

    It used to be the fallback of a separate lookup (get_upload_mime_type); since decision 36 the handler reads the
    file's info first, for its visibility, and that info is the only source of the MIME type."""
    info = uploads_api.UploadFileInfo(
        id="preview-id",
        original_name="notes.md",
        mime_type="text/markdown",
        size_bytes=12,
        uploaded_at=datetime.now(),
        uploaded_by_user_id=7,
        scope=uploads_api.UploadScope.PERSONAL,
        description=None,
        url="/api/v1/uploads/file/preview-id",
    )
    captured: dict[str, object] = {}

    def fake_build_preview_response(file_path, filename, mime_type, size_bytes, links, sheet_name=None):
        captured.update(
            {
                "file_path": file_path,
                "filename": filename,
                "mime_type": mime_type,
                "size_bytes": size_bytes,
                "sheet_name": sheet_name,
                "source_url": links.source_url,
            }
        )
        return uploads_api.FilePreviewResponse(
            preview_type="markdown",
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            source_url=links.source_url,
            download_url=links.download_url,
            preview_url=links.preview_url,
            text_content="# Title\n",
            total_lines=1,
        )

    monkeypatch.setattr(uploads_api, "get_upload_info", lambda _file_id: info)
    monkeypatch.setattr(uploads_api, "get_upload_path", lambda _file_id: Path(__file__))
    monkeypatch.setattr(uploads_api, "build_preview_response", fake_build_preview_response)

    response = await uploads_api.get_upload_file_preview(
        file_id="preview-id",
        sheet_name="Sheet1",
        current_user=SimpleNamespace(id=7, is_superuser=False),
    )

    assert response.preview_type == "markdown"
    assert captured["mime_type"] == "text/markdown"
    assert captured["sheet_name"] == "Sheet1"
    assert str(captured["file_path"]).endswith("test_uploads_api.py")


@pytest.mark.asyncio
async def test_serve_plugin_static_direct_returns_file_response():
    """UPLOAD-U3: Direct plugin static call resolves existing asset."""
    candidate = None
    for provider_type, base_dir in uploads_api.PLUGIN_STATIC_DIRS.items():
        for asset_path in sorted(base_dir.rglob("*")):
            if asset_path.is_file():
                candidate = (provider_type, asset_path, asset_path.relative_to(base_dir).as_posix())
                break
        if candidate:
            break

    assert candidate is not None, "Expected at least one plugin static asset in repository"
    provider_type, asset_path, rel_path = candidate

    response = await uploads_api.serve_plugin_static(
        provider_type=provider_type,
        path=rel_path,
        _current_user=SimpleNamespace(id=1),
    )

    assert Path(response.path) == asset_path.resolve()
    assert response.media_type


# The declared async-I/O fix of decision 36: the handlers read and write the sidecars in a worker thread, never on the
# event loop. Each service function the handler calls is replaced by a fake that records the thread it ran on; the
# handler is called directly, so the test's thread is the event loop's. Thread identity, not the to_thread call itself:
# any way off the loop passes.


def _direct_info(file_id: str, uploader: int) -> uploads_api.UploadFileInfo:
    """A personal text file of ``uploader``, as the service answers it."""
    return uploads_api.UploadFileInfo(
        id=file_id,
        original_name=f"{file_id}.txt",
        mime_type="text/plain",
        size_bytes=5,
        uploaded_at=datetime.now(UTC),
        uploaded_by_user_id=uploader,
        scope=uploads_api.UploadScope.PERSONAL,
        url=f"/api/v1/uploads/file/{file_id}",
    )


def record_service_threads(monkeypatch, **answers) -> dict[str, list[int]]:
    """Replace service functions of the uploads API by fakes giving ``answers``; the threads each one ran on, by name."""
    threads: dict[str, list[int]] = {name: [] for name in answers}

    def fake_for(name: str, answer):
        def fake(*_args, **_kwargs):
            threads[name].append(threading.get_ident())
            return answer

        return fake

    for name, answer in answers.items():
        monkeypatch.setattr(uploads_api, name, fake_for(name, answer))
    return threads


def on_the_event_loop(threads: dict[str, list[int]], loop_thread: int) -> list[str]:
    """The service functions that never ran, or ran on the event loop's thread."""
    problems = [f"{name} never ran" for name, ran_on in threads.items() if not ran_on]
    problems += [f"{name} ran on the event loop's thread" for name, ran_on in threads.items() if loop_thread in ran_on]
    return problems


@pytest.mark.asyncio
async def test_list_files_direct_reads_off_the_event_loop(monkeypatch):
    """UPLOAD-U4: list_files() reads the sidecars (list_uploads) in a worker thread."""
    threads = record_service_threads(monkeypatch, list_uploads=([_direct_info("listed-id", uploader=7)], 1))

    response = await uploads_api.list_files(current_user=SimpleNamespace(id=7, is_superuser=False), my_files_only=False)

    assert [(item.id, item.can_delete) for item in response.items] == [("listed-id", True)]
    problems = on_the_event_loop(threads, threading.get_ident())
    assert not problems, "list_files: " + "; ".join(problems)


@pytest.mark.asyncio
async def test_get_file_info_direct_reads_off_the_event_loop(monkeypatch):
    """UPLOAD-U5: get_file_info() reads the sidecar (get_upload_info) in a worker thread."""
    threads = record_service_threads(monkeypatch, get_upload_info=_direct_info("info-id", uploader=7))

    response = await uploads_api.get_file_info(file_id="info-id", current_user=SimpleNamespace(id=7, is_superuser=False))

    assert (response.id, response.can_delete) == ("info-id", True)
    problems = on_the_event_loop(threads, threading.get_ident())
    assert not problems, "get_file_info: " + "; ".join(problems)


@pytest.mark.asyncio
async def test_upload_file_direct_saves_off_the_event_loop(monkeypatch):
    """UPLOAD-U6: upload_file() writes the file and its sidecar (save_upload) in a worker thread."""

    async def fake_get_max_upload_mb(_session) -> int:
        return 5

    monkeypatch.setattr(uploads_api, "get_max_upload_mb", fake_get_max_upload_mb)
    threads = record_service_threads(monkeypatch, save_upload=_direct_info("saved-id", uploader=42))

    response = await uploads_api.upload_file(
        file=_DirectUploadFile("saved.txt", b"saved", "text/plain"),
        description=None,
        scope=None,
        current_user=SimpleNamespace(id=42, is_superuser=False),
        session=object(),
    )

    assert (response.file.id, response.file.can_delete) == ("saved-id", True)
    problems = on_the_event_loop(threads, threading.get_ident())
    assert not problems, "upload_file: " + "; ".join(problems)


# ============================================================================
# UPLOAD TESTS
# ============================================================================


class TestUpload:
    """Tests for POST /uploads."""

    @pytest.mark.asyncio
    async def test_upload_valid_file(self, test_server):
        """UPLOAD-001: Upload valid file."""
        print_section("UPLOAD-001: Upload valid file")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            filename, content = create_test_file("test_upload.txt", b"Test content")

            files = {"file": (filename, BytesIO(content), "text/plain")}
            response = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert data["success"] is True
            assert data["file"]["original_name"] == filename
            assert data["file"]["size_bytes"] == len(content)
            assert "id" in data["file"]

            print_success("✓ File uploaded successfully")

    @pytest.mark.asyncio
    async def test_upload_requires_auth(self, test_server):
        """UPLOAD: Upload requires authentication."""
        print_section("UPLOAD: Requires auth")

        async with httpx.AsyncClient() as client:
            filename, content = create_test_file()
            files = {"file": (filename, BytesIO(content), "text/plain")}

            response = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)

            assert response.status_code == 401

            print_success("✓ Upload requires auth")


# ============================================================================
# LIST TESTS
# ============================================================================


class TestListUploads:
    """Tests for GET /uploads."""

    @pytest.mark.asyncio
    async def test_list_uploads(self, test_server):
        """UPLOAD-003: List all uploads."""
        print_section("UPLOAD-003: List uploads")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            # Upload a file first
            filename, content = create_test_file("list_test.txt", b"Content")
            files = {"file": (filename, BytesIO(content), "text/plain")}
            await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)

            # List
            response = await client.get(f"{API_BASE}/uploads", timeout=TIMEOUT)

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert len(data["items"]) >= 1

            print_success("✓ Listed uploads")

    @pytest.mark.asyncio
    async def test_list_my_files_only(self, test_server):
        """UPLOAD-004: List only my files."""
        print_section("UPLOAD-004: List my files only")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            # User 1 uploads
            user1_id, _ = await create_user_and_login(client1)
            files1 = {"file": ("user1_file.txt", BytesIO(b"User1"), "text/plain")}
            upload1_resp = await client1.post(f"{API_BASE}/uploads", files=files1, timeout=TIMEOUT)
            file1_id = upload1_resp.json()["file"]["id"]

            # User 2 uploads
            user2_id, _ = await create_user_and_login(client2)
            files2 = {"file": ("user2_file.txt", BytesIO(b"User2"), "text/plain")}
            await client2.post(f"{API_BASE}/uploads", files=files2, timeout=TIMEOUT)

            # User 2 lists only their files
            response = await client2.get(f"{API_BASE}/uploads", params={"my_files_only": True}, timeout=TIMEOUT)

            assert response.status_code == 200
            data = response.json()
            file_ids = [f["id"] for f in data["items"]]
            assert file1_id not in file_ids  # User 1's file should not be in user 2's list

            print_success("✓ Filtered to my files only")


# ============================================================================
# FILE INFO TESTS
# ============================================================================


class TestFileInfo:
    """Tests for GET /uploads/{id}."""

    @pytest.mark.asyncio
    async def test_get_file_info(self, test_server):
        """UPLOAD-005: Get file info."""
        print_section("UPLOAD-005: Get file info")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            # Upload
            filename, content = create_test_file("info_test.txt", b"Info content")
            files = {"file": (filename, BytesIO(content), "text/plain")}
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            # Get info
            response = await client.get(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == file_id
            assert data["original_name"] == filename

            print_success("✓ Got file info")


# ============================================================================
# STRUCTURED PREVIEW TESTS
# ============================================================================


class TestStructuredPreview:
    """Tests for GET /uploads/{id}/preview."""

    @pytest.mark.asyncio
    async def test_markdown_preview_payload(self, test_server):
        """UPLOAD-005B: Markdown preview returns raw content and metadata."""
        print_section("UPLOAD-005B: Markdown preview payload")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            files = {"file": ("notes.md", BytesIO(b"# Heading\n\nBody line\n"), "text/markdown")}
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            response = await client.get(f"{API_BASE}/uploads/{file_id}/preview", timeout=TIMEOUT)

            assert response.status_code == 200, response.text
            data = response.json()
            assert data["preview_type"] == "markdown"
            assert data["text_content"] == "# Heading\n\nBody line\n"
            assert data["total_lines"] == 3
            assert data["download_url"].endswith("?download=true")

            print_success("✓ Markdown preview payload returned")

    @pytest.mark.asyncio
    async def test_image_preview_payload(self, test_server):
        """UPLOAD-005C: Image preview returns dimensions and optimized URL."""
        print_section("UPLOAD-005C: Image preview payload")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            files = {"file": ("chart.png", BytesIO(create_png_bytes(120, 90)), "image/png")}
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            response = await client.get(f"{API_BASE}/uploads/{file_id}/preview", timeout=TIMEOUT)

            assert response.status_code == 200, response.text
            data = response.json()
            assert data["preview_type"] == "image"
            assert data["image_width"] == 120
            assert data["image_height"] == 90
            assert data["preview_url"].endswith("img_preview=1600x1600")

            print_success("✓ Image preview metadata returned")

    @pytest.mark.asyncio
    async def test_pdf_preview_payload(self, test_server):
        """UPLOAD-005D: PDF preview returns embeddable source URL."""
        print_section("UPLOAD-005D: PDF preview payload")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            files = {"file": ("sample.pdf", BytesIO(create_minimal_pdf_bytes()), "application/pdf")}
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            response = await client.get(f"{API_BASE}/uploads/{file_id}/preview", timeout=TIMEOUT)

            assert response.status_code == 200, response.text
            data = response.json()
            assert data["preview_type"] == "pdf"
            assert data["source_url"].endswith(f"/api/v1/uploads/file/{file_id}")
            assert data["preview_url"] is None

            print_success("✓ PDF preview payload returned")

    @pytest.mark.asyncio
    async def test_excel_preview_sheet_selection(self, test_server):
        """UPLOAD-005E: Excel preview preserves sparse cells and sheet selection."""
        print_section("UPLOAD-005E: Excel preview sheet selection")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            files = {
                "file": (
                    "preview.xlsx",
                    BytesIO(create_xlsx_bytes()),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            }
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            response = await client.get(
                f"{API_BASE}/uploads/{file_id}/preview",
                params={"sheet_name": "Summary"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, response.text
            data = response.json()
            assert data["preview_type"] == "table"
            assert data["sheet_names"] == ["Summary", "Details"]
            assert data["active_sheet_name"] == "Summary"
            assert data["total_rows"] == 3
            assert data["total_cols"] == 3
            assert data["table_rows"][0] == ["Name", "Amount", ""]
            assert data["table_rows"][2][2] == "Sparse"

            print_success("✓ Excel preview respects used range")

    @pytest.mark.asyncio
    async def test_legacy_xls_preview_payload(self, test_server):
        """UPLOAD-005F: Legacy XLS preview works when xlrd is available."""
        print_section("UPLOAD-005F: Legacy XLS preview payload")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            files = {
                "file": (
                    "preview.xls",
                    BytesIO(read_sample_xls_bytes()),
                    "application/vnd.ms-excel",
                )
            }
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            response = await client.get(
                f"{API_BASE}/uploads/{file_id}/preview",
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, response.text
            data = response.json()
            assert data["preview_type"] == "table"
            assert data["total_rows"] > 0
            assert data["total_cols"] > 0
            assert isinstance(data["table_rows"], list)
            assert len(data["table_rows"]) > 0

            print_success("✓ Legacy XLS preview returned table payload")

    @pytest.mark.asyncio
    async def test_preview_falls_back_to_metadata_mime(self, test_server):
        """UPLOAD-005G: Preview uses the MIME type stored in the file's metadata.

        It used to check the fallback when a separate lookup (get_upload_mime_type) answered None; since decision 36
        the preview reads the file's info first, for its visibility, and takes the MIME type from it: there is no
        other lookup to fall back from, and the test now overlaps UPLOAD-005B."""
        print_section("UPLOAD-005G: Preview MIME from the metadata")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            files = {"file": ("fallback.md", BytesIO(b"# Title\nBody\n"), "text/markdown")}
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            response = await client.get(f"{API_BASE}/uploads/{file_id}/preview", timeout=TIMEOUT)

            assert response.status_code == 200, response.text
            data = response.json()
            assert data["preview_type"] == "markdown"
            assert data["text_content"].startswith("# Title")

            print_success("✓ Preview used metadata MIME fallback")

    @pytest.mark.asyncio
    async def test_damaged_xlsx_preview_returns_400(self, test_server):
        """UPLOAD-005H: Preview of a damaged .xlsx answers 400 (not 500, F2) with ``detail`` ``{"code": "preview_unreadable", "message": <English text>}`` (an object since lot W5-5, C-70b)."""
        print_section("UPLOAD-005H: Damaged XLSX preview answers 400")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            files = {
                "file": (
                    "damaged.xlsx",
                    BytesIO(create_damaged_xlsx_bytes()),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            }
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            assert upload_resp.status_code == 200, upload_resp.text
            file_id = upload_resp.json()["file"]["id"]

            try:
                response = await client.get(f"{API_BASE}/uploads/{file_id}/preview", timeout=TIMEOUT)

                assert response.status_code == 400, f"the preview of a damaged .xlsx answers {response.status_code} {response.text}: a damaged workbook is the user's file, not a fault of the server (F2)"
                detail = response.json().get("detail")
                assert isinstance(detail, dict), f"the 400 says why in a detail object the wizard translates, not in an English sentence (C-70b): {response.text}"
                assert detail.get("code") == "preview_unreadable", f"a damaged workbook is unreadable, not unsupported: {response.text}"
                assert isinstance(detail.get("message"), str) and detail["message"].strip(), f"the English text stays as the diagnostic message: {response.text}"
                assert set(detail) == {"code", "message"}, f"the keys of a preview failure: {response.text}"
            finally:
                # Whoever uploads cleans up: the owner deletes the file, as UPLOAD-007 does.
                delete_resp = await client.delete(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)
                assert delete_resp.status_code == 200, delete_resp.text

            print_success("✓ Damaged XLSX preview answered 400")

    @pytest.mark.asyncio
    async def test_unsupported_preview_returns_400_with_the_unsupported_code(self, test_server):
        """UPLOAD-005I: Preview of a file whose type has no preview (a zip archive: no image, text, table or PDF) answers 400 with
        ``detail`` ``{"code": "preview_unsupported", "message": <English text naming the file>}`` (C-70b): an object, so the
        wizard translates the failure instead of showing the English sentence."""
        print_section("UPLOAD-005I: Unsupported preview answers 400 with its code")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            name = f"archive_{uuid.uuid4().hex[:8]}.zip"
            archive = BytesIO()
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("inside.txt", "a member of an archive the preview does not open\n")
            files = {"file": (name, BytesIO(archive.getvalue()), "application/zip")}
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            assert upload_resp.status_code == 200, upload_resp.text
            file_id = upload_resp.json()["file"]["id"]

            try:
                response = await client.get(f"{API_BASE}/uploads/{file_id}/preview", timeout=TIMEOUT)

                assert response.status_code == 400, f"premise: a file with no preview type answers 400: {response.status_code} {response.text}"
                detail = response.json().get("detail")
                assert isinstance(detail, dict), f"the 400 says why in a detail object the wizard translates, not in an English sentence (C-70b): {response.text}"
                assert set(detail) == {"code", "message"}, f"the keys of a preview failure: {response.text}"
                assert detail["code"] == "preview_unsupported", response.text
                assert isinstance(detail["message"], str) and name in detail["message"], f"the English text stays as the diagnostic message, naming the file: {response.text}"
            finally:
                delete_resp = await client.delete(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)
                assert delete_resp.status_code == 200, delete_resp.text

            print_success("✓ Unsupported preview answered 400 with preview_unsupported")


# ============================================================================
# DOWNLOAD TESTS
# ============================================================================


class TestDownload:
    """Tests for GET /uploads/file/{id}."""

    @pytest.mark.asyncio
    async def test_download_file(self, test_server):
        """UPLOAD-006: Download file."""
        print_section("UPLOAD-006: Download file")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            # Upload
            filename, content = create_test_file("download_test.txt", b"Download me!")
            files = {"file": (filename, BytesIO(content), "text/plain")}
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            # Download
            response = await client.get(f"{API_BASE}/uploads/file/{file_id}", timeout=TIMEOUT)

            assert response.status_code == 200
            assert response.content == content

            print_success("✓ Downloaded file")


# ============================================================================
# DELETE TESTS
# ============================================================================


class TestDelete:
    """Tests for DELETE /uploads/{id}."""

    @pytest.mark.asyncio
    async def test_delete_own_file(self, test_server):
        """UPLOAD-007: Delete own file."""
        print_section("UPLOAD-007: Delete own file")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            # Upload
            files = {"file": ("delete_test.txt", BytesIO(b"Delete me"), "text/plain")}
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            # Delete
            response = await client.delete(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)

            assert response.status_code == 200
            assert response.json()["success"] is True

            # Verify deleted
            get_resp = await client.get(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)
            assert get_resp.status_code == 404

            print_success("✓ Deleted own file")

    @pytest.mark.asyncio
    async def test_cannot_delete_others_file(self, test_server):
        """UPLOAD-008: Cannot delete other's file (non-superuser).

        The file is uploaded common, so user 2 sees it and gets 403. A personal file of another user answers 404
        instead, like a file that does not exist (decision 36): TestUploadScopeDelete."""
        print_section("UPLOAD-008: Cannot delete other's file")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            # User 1 uploads
            await create_user_and_login(client1)
            files = {"file": ("protected.txt", BytesIO(b"Protected"), "text/plain")}
            upload_resp = await client1.post(f"{API_BASE}/uploads", files=files, data={"scope": "common"}, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            # User 2 tries to delete
            await create_user_and_login(client2)
            response = await client2.delete(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)

            assert response.status_code == 403

            print_success("✓ Cannot delete other's file")


# ============================================================================
# PLUGIN STATIC TESTS
# ============================================================================


class TestPluginStatic:
    """Tests for GET /uploads/plugin/{type}/{path}."""

    @pytest.mark.asyncio
    async def test_plugin_static_serves_existing_asset(self, test_server):
        """UPLOAD-010: Serve real plugin asset from static directory."""
        print_section("UPLOAD-010: Plugin static serves existing asset")

        candidate = None
        for provider_type, base_dir in uploads_api.PLUGIN_STATIC_DIRS.items():
            for asset_path in sorted(base_dir.rglob("*")):
                if asset_path.is_file():
                    candidate = (provider_type, asset_path, asset_path.relative_to(base_dir).as_posix())
                    break
            if candidate:
                break

        assert candidate is not None, "Expected at least one plugin static asset in repository"
        provider_type, asset_path, rel_path = candidate

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            response = await client.get(
                f"{API_BASE}/uploads/plugin/{provider_type}/{rel_path}",
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, response.text
            assert response.content == asset_path.read_bytes()
            assert response.headers.get("content-type")

            print_success("✓ Served existing plugin asset")

    @pytest.mark.asyncio
    async def test_plugin_static_serves_every_bundled_brim_icon(self, test_server):
        """UPLOAD-010C: Every BRIM plugin whose icon_url is a file of the static folder gets it served: 200, the image type of the file, its bytes.

        The plugins as GET /brokers/import/plugins lists them: Scalable's two since 37_brimScalable. Only icons under BRIM_STATIC_PREFIX are
        requested, and only from the test server."""
        print_section("UPLOAD-010C: Plugin static serves every bundled BRIM icon")

        icons = {info.code: info.icon_url for info in BRIMProviderRegistry.list_plugin_info() if (info.icon_url or "").startswith(BRIM_STATIC_PREFIX)}
        assert icons, "premise: one registered BRIM plugin at least bundles its icon (broker_scalable and broker_scalable_deposit do), or this check passes on nothing"

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            problems = []
            for code, icon_url in sorted(icons.items()):
                problem = await bundled_icon_problem(client, code, icon_url)
                if problem:
                    problems.append(problem)

        assert not problems, f"{len(problems)} bundled BRIM icon(s) not served as their file:\n" + "\n".join(f"  {problem}" for problem in problems)

        print_success(f"✓ {len(icons)} bundled BRIM icon(s) served as their file")

    @pytest.mark.asyncio
    async def test_plugin_static_not_found(self, test_server):
        """UPLOAD-011: 404 for non-existent plugin asset."""
        print_section("UPLOAD-011: Plugin static not found")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            response = await client.get(f"{API_BASE}/uploads/plugin/brim/nonexistent/logo.png", timeout=TIMEOUT)

            assert response.status_code == 404

            print_success("✓ Got 404 for non-existent asset")


# ============================================================================
# FILE SIZE LIMIT TESTS
# ============================================================================


class TestFileSizeLimit:
    """Tests for max file upload size."""

    @pytest.mark.asyncio
    async def test_file_too_large_rejected(self, test_server):
        """UPLOAD-012: File larger than max_file_upload_mb is rejected."""
        print_section("UPLOAD-012: File too large rejected")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            # Get current max file size setting
            settings_resp = await client.get(f"{API_BASE}/settings/global", timeout=TIMEOUT)
            max_mb = 10  # Default fallback
            for setting in settings_resp.json().get("items", []):
                if setting.get("key") == "max_file_upload_mb":
                    max_mb = int(setting.get("value", 10))
                    break

            # Create file larger than max (max_mb + 1 MB)
            large_content = b"X" * ((max_mb + 1) * 1024 * 1024)
            files = {"file": ("large_file.bin", BytesIO(large_content), "application/octet-stream")}

            response = await client.post(f"{API_BASE}/uploads", files=files, timeout=60)  # Longer timeout for large file

            # Should be rejected with 413 or 400
            assert response.status_code in [
                400,
                413,
            ], f"Expected 400/413, got {response.status_code}"

            print_success("✓ Large file correctly rejected")


# ============================================================================
# SUPERUSER DELETE TESTS
# ============================================================================


class TestSuperuserDelete:
    """Tests for superuser file deletion capabilities."""

    @pytest.mark.asyncio
    async def test_superuser_can_delete_any_file(self, test_server):
        """UPLOAD-013: Superuser can delete any user's file."""
        print_section("UPLOAD-013: Superuser deletes any file")

        async with httpx.AsyncClient() as admin_client, httpx.AsyncClient() as user_client:
            # Create admin (first user)
            await create_user_and_login(admin_client)
            me_resp = await admin_client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
            is_superuser = me_resp.json().get("user", {}).get("is_superuser", False)

            if not is_superuser:
                pytest.skip("First user is not superuser")

            # Regular user uploads file
            await create_user_and_login(user_client)
            files = {"file": ("user_file.txt", BytesIO(b"User content"), "text/plain")}
            upload_resp = await user_client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            # Superuser deletes it
            response = await admin_client.delete(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)

            assert response.status_code == 200
            assert response.json()["success"] is True

            print_success("✓ Superuser deleted user's file")


# ============================================================================
# SECURITY VALIDATION TESTS
# ============================================================================


class TestUploadSecurity:
    """Tests for upload security validation."""

    @pytest.mark.asyncio
    async def test_blocked_executable_extension(self, test_server):
        """UPLOAD-014: Executable file extension is blocked."""
        print_section("UPLOAD-014: Blocked executable extension")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            # Try to upload .exe file
            files = {"file": ("malware.exe", BytesIO(b"MZ\x90\x00"), "application/octet-stream")}
            response = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)

            assert response.status_code == 400
            assert "not allowed" in response.json()["detail"].lower()

            print_success("✓ Executable extension blocked")

    @pytest.mark.asyncio
    async def test_blocked_script_extension(self, test_server):
        """UPLOAD-015: Script file extension is blocked."""
        print_section("UPLOAD-015: Blocked script extension")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            # Try to upload .sh script
            files = {"file": ("script.sh", BytesIO(b"#!/bin/bash\nrm -rf /"), "text/plain")}
            response = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)

            assert response.status_code == 400
            assert "not allowed" in response.json()["detail"].lower()

            print_success("✓ Script extension blocked")

    @pytest.mark.asyncio
    async def test_allowed_image_upload(self, test_server):
        """UPLOAD-016: Image files are allowed."""
        print_section("UPLOAD-016: Image upload allowed")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            # PNG magic bytes
            png_header = b"\x89PNG\r\n\x1a\n"
            files = {"file": ("test.png", BytesIO(png_header + b"\x00" * 100), "image/png")}
            response = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)

            assert response.status_code == 200
            assert response.json()["success"] is True

            print_success("✓ Image upload allowed")


# ============================================================================
# SCOPE OF UPLOADED FILES (decision 36)
# ============================================================================


class TestUploadScopeOnPost:
    """POST /uploads takes an optional multipart field ``scope``: stored as given; without it the inheritance rule's
    result is stored (image/* common, anything else personal); any other value 422. The answer's file carries the
    effective ``scope`` and ``can_delete`` for the uploader."""

    @pytest.mark.asyncio
    async def test_without_scope_the_inherited_scope_is_stored(self, test_server):
        """SCOPE-POST-1: without scope, an image is stored common and a text file personal."""
        print_section("SCOPE-POST-1: without scope, image → common, text → personal")

        async with scope_lane() as lane:
            image = await lane.upload(lane.a, scope_name("inherit", ".png"), create_png_bytes(), "image/png")
            text = await lane.upload(lane.a, scope_name("inherit", ".txt"), SCOPE_TEXT, "text/plain")
            assert image["mime_type"].startswith("image/") and text["mime_type"].startswith("text/"), f"precondition: detected {image['mime_type']} and {text['mime_type']}"

            answered = {"image": (image.get("scope"), image.get("can_delete")), "text": (text.get("scope"), text.get("can_delete"))}
            assert answered == {"image": ("common", True), "text": ("personal", True)}, f"POST /uploads answered (scope, can_delete) {answered}"
            read_back = {"image": (await info_of(lane.a, image["id"])).get("scope"), "text": (await info_of(lane.a, text["id"])).get("scope")}
            assert read_back == {"image": "common", "text": "personal"}, f"GET /uploads/{{id}} reads the scopes {read_back}"

        print_success("✓ Inherited scope stored: image common, text personal")

    @pytest.mark.asyncio
    async def test_with_scope_it_is_stored_as_given(self, test_server):
        """SCOPE-POST-2: the scope asked for is stored as given, against the inheritance rule too."""
        print_section("SCOPE-POST-2: scope stored as given")

        async with scope_lane() as lane:
            image = await lane.upload(lane.a, scope_name("asked-personal", ".png"), create_png_bytes(), "image/png", scope="personal")
            text = await lane.upload(lane.a, scope_name("asked-common", ".txt"), SCOPE_TEXT, "text/plain", scope="common")

            answered = {"image": (image.get("scope"), image.get("can_delete")), "text": (text.get("scope"), text.get("can_delete"))}
            assert answered == {"image": ("personal", True), "text": ("common", True)}, f"POST /uploads answered (scope, can_delete) {answered}"
            read_back = {"image": (await info_of(lane.a, image["id"])).get("scope"), "text": (await info_of(lane.a, text["id"])).get("scope")}
            assert read_back == {"image": "personal", "text": "common"}, f"GET /uploads/{{id}} reads the scopes {read_back}"

        print_success("✓ Scope stored as given")

    @pytest.mark.asyncio
    async def test_any_other_scope_is_refused_and_nothing_is_stored(self, test_server):
        """SCOPE-POST-3: a scope other than common or personal is a 422, and no file is stored."""
        print_section("SCOPE-POST-3: invalid scope → 422")

        async with scope_lane() as lane:
            problems = []
            for value in ("public", "COMMON"):
                name = scope_name("refused", ".txt")
                resp = await lane.a.client.post(f"{API_BASE}/uploads", files={"file": (name, BytesIO(SCOPE_TEXT), "text/plain")}, data={"scope": value}, timeout=TIMEOUT)
                if resp.status_code == 200:
                    lane.files.append((lane.a, resp.json()["file"]["id"]))  # stored after all: whoever writes cleans up
                if resp.status_code != 422:
                    problems.append(f"scope={value!r}: answered {resp.status_code}, expected 422")
                mine = await listed(lane.a, my_files_only=True)
                if any(item["original_name"] == name for item in mine.values()):
                    problems.append(f"scope={value!r}: the file was stored")
            assert not problems, "POST /uploads with an invalid scope:\n" + "\n".join(problems)

        print_success("✓ Invalid scopes refused, nothing stored")


class TestUploadScopeList:
    """GET /uploads: every common file plus one's own personal ones; the admin sees everything. ``my_files_only``:
    one's own files, both scopes. Every item carries its effective ``scope`` and ``can_delete`` for whoever asks."""

    @pytest.mark.asyncio
    async def test_list_shows_every_common_file_and_only_own_personal_ones(self, test_server):
        """SCOPE-LIST-1: who lists which of four files (A/B × personal/common)."""
        print_section("SCOPE-LIST-1: common files for all, personal ones for their owner and the admin")

        async with scope_lane() as lane:
            a_personal = (await lane.upload(lane.a, scope_name("a-personal", ".txt"), SCOPE_TEXT, "text/plain", scope="personal"))["id"]
            a_common = (await lane.upload(lane.a, scope_name("a-common", ".txt"), SCOPE_TEXT, "text/plain", scope="common"))["id"]
            b_personal = (await lane.upload(lane.b, scope_name("b-personal", ".txt"), SCOPE_TEXT, "text/plain", scope="personal"))["id"]
            b_common = (await lane.upload(lane.b, scope_name("b-common", ".png"), create_png_bytes(), "image/png"))["id"]  # no scope: an image inherits common
            names = {a_personal: "A's personal file", a_common: "A's common file", b_personal: "B's personal file", b_common: "B's image (common, inherited)"}
            views = [(lane.a, {a_personal, a_common, b_common}, {b_personal}), (lane.b, {b_personal, b_common, a_common}, {a_personal}), (lane.admin, set(names), set())]

            problems, lists = [], {}
            for actor, visible, hidden in views:
                items = lists[actor.label] = await listed(actor)
                problems += [f"{actor.label} does not list {names[file_id]}" for file_id in sorted(visible - items.keys())]
                problems += [f"{actor.label} lists {names[file_id]}" for file_id in sorted(hidden & items.keys())]
            assert not problems, "GET /uploads:\n" + "\n".join(problems)

            # Every item, the neighbours' too: an effective scope, no personal file of somebody else (but for the admin),
            # and can_delete for whoever asks — the owner or the admin.
            for actor, _, _ in views:
                for item in lists[actor.label].values():
                    scope, can_delete, owner = item.get("scope"), item.get("can_delete"), item["uploaded_by_user_id"]
                    if scope not in ("common", "personal"):
                        problems.append(f"{actor.label}: item {item['id']} has scope {scope!r}")
                    elif scope == "personal" and owner != actor.user_id and not actor.is_admin:
                        problems.append(f"{actor.label}: lists the personal file {item['id']} of user {owner}")
                    if can_delete is not (actor.is_admin or owner == actor.user_id):
                        problems.append(f"{actor.label}: item {item['id']} of user {owner} has can_delete={can_delete!r}")
            assert not problems, f"GET /uploads, {len(problems)} item problem(s), the first 20:\n" + "\n".join(problems[:20])

            scopes = {names[file_id]: lists["admin"][file_id]["scope"] for file_id in names}
            assert scopes == {names[a_personal]: "personal", names[a_common]: "common", names[b_personal]: "personal", names[b_common]: "common"}, f"the admin lists the scopes {scopes}"

        print_success("✓ Common files for all, personal ones for owner and admin")

    @pytest.mark.asyncio
    async def test_my_files_only_lists_own_files_of_both_scopes(self, test_server):
        """SCOPE-LIST-2: my_files_only lists one's own files, personal and common, and nobody else's (the admin too)."""
        print_section("SCOPE-LIST-2: my_files_only, both scopes")

        async with scope_lane() as lane:
            a_personal = (await lane.upload(lane.a, scope_name("a-personal", ".txt"), SCOPE_TEXT, "text/plain", scope="personal"))["id"]
            a_common = (await lane.upload(lane.a, scope_name("a-common", ".txt"), SCOPE_TEXT, "text/plain", scope="common"))["id"]
            b_common = (await lane.upload(lane.b, scope_name("b-common", ".txt"), SCOPE_TEXT, "text/plain", scope="common"))["id"]
            names = {a_personal: "A's personal file", a_common: "A's common file", b_common: "B's common file"}
            views = [(lane.a, {a_personal, a_common}, {b_common}), (lane.b, {b_common}, {a_personal, a_common}), (lane.admin, set(), set(names))]

            problems, lists = [], {}
            for actor, own, foreign in views:
                items = lists[actor.label] = await listed(actor, my_files_only=True)
                problems += [f"{actor.label} does not list {names[file_id]}" for file_id in sorted(own - items.keys())]
                problems += [f"{actor.label} lists {names[file_id]}" for file_id in sorted(foreign & items.keys())]
                problems += [f"{actor.label} lists {file_id} of user {item['uploaded_by_user_id']}" for file_id, item in items.items() if item["uploaded_by_user_id"] != actor.user_id][:5]
            assert not problems, "GET /uploads?my_files_only=true:\n" + "\n".join(problems)

            scopes = {names[file_id]: lists["A"][file_id].get("scope") for file_id in (a_personal, a_common)}
            assert scopes == {names[a_personal]: "personal", names[a_common]: "common"}, f"A's own files are listed with the scopes {scopes}"

        print_success("✓ my_files_only: own files, both scopes")


class TestUploadScopeRead:
    """GET /uploads/{id} and /uploads/{id}/preview. A personal file: its owner and the admin read it, anyone else gets the
    answer of a file that does not exist. A common file: everyone reads it."""

    ROUTES = ("/uploads/{id}", "/uploads/{id}/preview")

    @pytest.mark.asyncio
    async def test_personal_file_info_and_preview_are_hidden_from_other_users(self, test_server):
        """SCOPE-READ-1: B gets 404 like a missing file; A and the admin get 200."""
        print_section("SCOPE-READ-1: personal file, info and preview")

        async with scope_lane() as lane:
            file_id = (await lane.upload(lane.a, scope_name("a-personal", ".txt"), SCOPE_TEXT, "text/plain", scope="personal"))["id"]

            # The file is there and readable, by its owner: the barrier that gives B's 404 its meaning.
            problems = [problem for route in self.ROUTES if (problem := await read_problem(lane.a, route, file_id))]
            assert not problems, "\n".join(problems)

            problems = [problem for route in self.ROUTES if (problem := await hidden_problem(lane.b, "GET", route, file_id))]
            problems += [problem for route in self.ROUTES if (problem := await read_problem(lane.admin, route, file_id))]
            assert not problems, "A's personal file:\n" + "\n".join(problems)

            seen = {}
            for actor in (lane.a, lane.admin):
                info = await info_of(actor, file_id)
                seen[actor.label] = (info.get("scope"), info.get("can_delete"))
            assert seen == {"A": ("personal", True), "admin": ("personal", True)}, f"(scope, can_delete) as read: {seen}"

        print_success("✓ Personal file: 404 to B, 200 to A and the admin")

    @pytest.mark.asyncio
    async def test_common_file_info_and_preview_are_read_by_everyone(self, test_server):
        """SCOPE-READ-2: all three get 200; can_delete only for the owner and the admin."""
        print_section("SCOPE-READ-2: common file, info and preview")

        async with scope_lane() as lane:
            file_id = (await lane.upload(lane.a, scope_name("a-common", ".txt"), SCOPE_TEXT, "text/plain", scope="common"))["id"]

            problems = [problem for actor in (lane.a, lane.b, lane.admin) for route in self.ROUTES if (problem := await read_problem(actor, route, file_id))]
            assert not problems, "A's common file:\n" + "\n".join(problems)

            seen = {}
            for actor in (lane.a, lane.b, lane.admin):
                info = await info_of(actor, file_id)
                seen[actor.label] = (info.get("scope"), info.get("can_delete"))
            assert seen == {"A": ("common", True), "B": ("common", False), "admin": ("common", True)}, f"(scope, can_delete) as read: {seen}"

        print_success("✓ Common file: 200 to everyone")


class TestUploadScopeDelete:
    """DELETE /uploads/{id}: the owner or the admin. Another user gets 403 on a common file (visible, not theirs) and
    404 on a personal one (not visible)."""

    @pytest.mark.asyncio
    async def test_owner_and_admin_delete_a_personal_file(self, test_server):
        """SCOPE-DEL-1: unchanged by decision 36, and kept so: the hidden-file rule stops neither the owner nor the admin."""
        print_section("SCOPE-DEL-1: owner and admin delete a personal file")

        async with scope_lane() as lane:
            by_owner = (await lane.upload(lane.a, scope_name("a-personal", ".txt"), SCOPE_TEXT, "text/plain", scope="personal"))["id"]
            by_admin = (await lane.upload(lane.a, scope_name("a-personal", ".txt"), SCOPE_TEXT, "text/plain", scope="personal"))["id"]

            for actor, file_id in ((lane.a, by_owner), (lane.admin, by_admin)):
                resp = await actor.client.delete(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)
                assert resp.status_code == 200, f"{actor.label} DELETE on A's personal file: {resp.status_code} {resp.text}"
                assert resp.json()["success"] is True
                gone = await lane.a.client.get(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)
                assert gone.status_code == 404, f"after {actor.label}'s DELETE the file still answers {gone.status_code}"

        print_success("✓ Owner and admin delete a personal file")

    @pytest.mark.asyncio
    async def test_other_user_gets_403_on_a_common_file_and_404_on_a_personal_one(self, test_server):
        """SCOPE-DEL-2: B's DELETE: 403 on A's common file, 404 like a missing file on A's personal one; both stay."""
        print_section("SCOPE-DEL-2: another user's DELETE")

        async with scope_lane() as lane:
            common = (await lane.upload(lane.a, scope_name("a-common", ".txt"), SCOPE_TEXT, "text/plain", scope="common"))["id"]
            personal = (await lane.upload(lane.a, scope_name("a-personal", ".txt"), SCOPE_TEXT, "text/plain", scope="personal"))["id"]

            resp = await lane.b.client.delete(f"{API_BASE}/uploads/{common}", timeout=TIMEOUT)
            assert resp.status_code == 403, f"B DELETE on A's common file: {resp.status_code} {resp.text}, expected 403"
            problem = await hidden_problem(lane.b, "DELETE", "/uploads/{id}", personal)
            assert problem is None, f"B DELETE on A's personal file: {problem}"

            for file_id in (common, personal):
                still = await lane.a.client.get(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)
                assert still.status_code == 200, f"a refused DELETE removed the file: {still.status_code}"

        print_success("✓ 403 on common, 404 on personal")


class TestUploadScopePatch:
    """PATCH /uploads/{id} with ``{"scope": "common" | "personal"}``: the owner or the admin, 200 with the updated file
    info. Another user: 403 on a common file, 404 on a personal one. Invalid body 422, missing file 404."""

    @pytest.mark.asyncio
    async def test_owner_and_admin_change_the_scope(self, test_server):
        """SCOPE-PATCH-1: A makes the file common, the admin makes it personal again; each answer is the updated info."""
        print_section("SCOPE-PATCH-1: owner and admin change the scope")

        async with scope_lane() as lane:
            file_id = (await lane.upload(lane.a, scope_name("a-switch", ".txt"), SCOPE_TEXT, "text/plain", scope="personal"))["id"]

            for actor, scope in ((lane.a, "common"), (lane.admin, "personal")):
                resp = await patch_scope(actor, file_id, {"scope": scope})
                assert resp.status_code == 200, f"{actor.label} PATCH /uploads/{{id}} {{'scope': {scope!r}}}: {resp.status_code} {resp.text}"
                body = resp.json()
                assert (body.get("id"), body.get("scope"), body.get("can_delete")) == (file_id, scope, True), f"{actor.label}'s PATCH answered {body}"
                assert body == await info_of(actor, file_id), "the PATCH answers the updated file info, as GET /uploads/{id} reads it"

        print_success("✓ Owner and admin change the scope")

    @pytest.mark.asyncio
    async def test_other_user_gets_403_on_a_common_file_and_404_on_a_personal_one(self, test_server):
        """SCOPE-PATCH-2: B's PATCH: 403 on A's common file, 404 like a missing file on A's personal one; nothing changes."""
        print_section("SCOPE-PATCH-2: another user's PATCH")

        async with scope_lane() as lane:
            common = (await lane.upload(lane.a, scope_name("a-common", ".txt"), SCOPE_TEXT, "text/plain", scope="common"))["id"]
            personal = (await lane.upload(lane.a, scope_name("a-personal", ".txt"), SCOPE_TEXT, "text/plain", scope="personal"))["id"]

            resp = await patch_scope(lane.b, common, {"scope": "personal"})
            assert resp.status_code == 403, f"B PATCH on A's common file: {resp.status_code} {resp.text}, expected 403"
            problem = await hidden_problem(lane.b, "PATCH", "/uploads/{id}", personal, json_body={"scope": "common"})
            assert problem is None, f"B PATCH on A's personal file: {problem}"

            scopes = {"common": (await info_of(lane.a, common)).get("scope"), "personal": (await info_of(lane.a, personal)).get("scope")}
            assert scopes == {"common": "common", "personal": "personal"}, f"a refused PATCH changed the scope: {scopes}"

        print_success("✓ 403 on common, 404 on personal, nothing changed")

    @pytest.mark.asyncio
    async def test_invalid_bodies_are_refused_and_a_missing_file_is_404(self, test_server):
        """SCOPE-PATCH-3: invalid scope, missing scope or an extra field → 422; a missing id → 404; nothing changes."""
        print_section("SCOPE-PATCH-3: 422 bodies, 404 missing id")

        async with scope_lane() as lane:
            file_id = (await lane.upload(lane.a, scope_name("a-personal", ".txt"), SCOPE_TEXT, "text/plain", scope="personal"))["id"]

            problems = []
            for label, body in (("invalid scope", {"scope": "public"}), ("missing scope", {}), ("extra field", {"scope": "common", "uploaded_by_user_id": lane.b.user_id})):
                resp = await patch_scope(lane.a, file_id, body)
                if resp.status_code != 422:
                    problems.append(f"A PATCH, {label} {body}: answered {resp.status_code} {resp.text[:200]!r}, expected 422")
            for actor in (lane.a, lane.admin):
                resp = await patch_scope(actor, str(uuid.uuid4()), {"scope": "common"})
                if (resp.status_code, response_body(resp)) != (404, NOT_FOUND):
                    problems.append(f"{actor.label} PATCH on a missing id: answered {resp.status_code} {resp.text[:200]!r}, expected 404 {NOT_FOUND}")
            assert not problems, "PATCH /uploads/{id}:\n" + "\n".join(problems)

            info = await info_of(lane.a, file_id)
            assert (info.get("scope"), info["uploaded_by_user_id"]) == ("personal", lane.a.user_id), f"a refused PATCH changed the file: {info}"

        print_success("✓ Invalid bodies 422, missing id 404")

    @pytest.mark.asyncio
    async def test_scope_switch_changes_what_other_users_read_at_once(self, test_server):
        """SCOPE-PATCH-4: personal → common, B lists and reads it; common → personal, B gets 404 at once."""
        print_section("SCOPE-PATCH-4: a switch is seen at once")

        async with scope_lane() as lane:
            file_id = (await lane.upload(lane.a, scope_name("a-switch", ".txt"), SCOPE_TEXT, "text/plain", scope="personal"))["id"]
            routes = ("/uploads/{id}", "/uploads/{id}/preview", "/uploads/file/{id}")

            problem = await hidden_problem(lane.b, "GET", "/uploads/{id}", file_id)
            assert problem is None, f"precondition, the file is personal: {problem}"

            resp = await patch_scope(lane.a, file_id, {"scope": "common"})
            assert resp.status_code == 200, f"A PATCH personal → common: {resp.status_code} {resp.text}"
            assert file_id in await listed(lane.b), "made common, the file is not in B's list"
            problems = [problem for route in routes if (problem := await read_problem(lane.b, route, file_id))]
            assert not problems, "made common:\n" + "\n".join(problems)

            resp = await patch_scope(lane.a, file_id, {"scope": "personal"})
            assert resp.status_code == 200, f"A PATCH common → personal: {resp.status_code} {resp.text}"
            problems = [problem for route in routes if (problem := await hidden_problem(lane.b, "GET", route, file_id))]
            assert not problems, "made personal again:\n" + "\n".join(problems)
            assert file_id not in await listed(lane.b), "made personal again, the file is still in B's list"

        print_success("✓ The switch is seen at once")


class TestUploadScopeLegacy:
    """Files stored before decision 36 have no ``scope`` in their sidecar: the inheritance rule classifies them (an image
    or a file of the system common, anything else personal), and an admin's PATCH stores the field."""

    @pytest.mark.asyncio
    async def test_legacy_files_inherit_their_scope_and_an_admin_patch_stores_it(self, test_server):
        """SCOPE-LEGACY-1: legacy PNG and system file common, legacy text personal; the admin's PATCH writes the scope."""
        print_section("SCOPE-LEGACY-1: legacy sidecars")

        async with scope_lane() as lane:
            image = lane.write_legacy(lane.a.user_id, scope_name("legacy", ".png"), create_png_bytes(), "image/png")
            text = lane.write_legacy(lane.a.user_id, scope_name("legacy", ".txt"), SCOPE_TEXT, "text/plain")
            system = lane.write_legacy(0, scope_name("legacy-system", ".txt"), SCOPE_TEXT, "text/plain")

            seen = {}
            for label, actor, file_id in (("A's legacy image, by B", lane.b, image), ("the system's legacy text, by B", lane.b, system), ("A's legacy text, by A", lane.a, text)):
                info = await info_of(actor, file_id)
                seen[label] = (info.get("scope"), info.get("can_delete"))
            expected = {"A's legacy image, by B": ("common", False), "the system's legacy text, by B": ("common", False), "A's legacy text, by A": ("personal", True)}
            assert seen == expected, f"(scope, can_delete) of the legacy files: {seen}"
            problem = await hidden_problem(lane.b, "GET", "/uploads/{id}", text)
            assert problem is None, f"A's legacy text file: {problem}"

            # The admin's PATCH stores the field, even when it is the value the rule gives anyway (the text file).
            for file_id in (image, text):
                resp = await patch_scope(lane.admin, file_id, {"scope": "personal"})
                assert resp.status_code == 200, f"admin PATCH on a legacy file: {resp.status_code} {resp.text}"
                sidecar = json.loads((get_uploads_dir() / f"{file_id}.json").read_text())
                assert sidecar.get("scope") == "personal", f"the admin's PATCH did not store the scope in the legacy sidecar: {sidecar}"
            problem = await hidden_problem(lane.b, "GET", "/uploads/{id}", image)
            assert problem is None, f"A's legacy image made personal: {problem}"

        print_success("✓ Legacy files inherit their scope, the admin's PATCH stores it")


class TestUploadIdsTheFilesystemCannotName:
    """An id with a NUL byte, sent percent-encoded (%00), names no file: the server decodes it into the id, where
    ``os.stat()`` raises ValueError instead of OSError. The answer must be the missing-file 404, the same as for a
    random missing id, never a 500."""

    @pytest.mark.asyncio
    async def test_nul_byte_in_the_id_answers_the_missing_file_404(self, test_server):
        """UPLOAD-NUL-1: GET /uploads/{id} and GET /uploads/file/{id} with %00 in the id."""
        print_section("UPLOAD-NUL-1: %00 in the id → the missing-file 404")

        async with httpx.AsyncClient() as client:
            await sign_in(client, "A", *E2E_USER, admin=False)
            nul_id = f"{uuid.uuid4()}%00"
            problems = []
            for route in ("/uploads/{id}", "/uploads/file/{id}"):
                missing = await client.get(f"{API_BASE}{route.format(id=uuid.uuid4())}", timeout=TIMEOUT)
                answer = await client.get(f"{API_BASE}{route.format(id=nul_id)}", timeout=TIMEOUT)
                assert b"%00" in answer.request.url.raw_path, f"precondition: the client sends the NUL percent-encoded; it sent {answer.request.url.raw_path!r}"
                if (missing.status_code, response_body(missing)) != (404, NOT_FOUND):
                    problems.append(f"GET {route}: a random missing id answers {missing.status_code} {missing.text[:200]!r}, expected 404 {NOT_FOUND}")
                elif (answer.status_code, response_body(answer)) != (404, NOT_FOUND):
                    problems.append(f"GET {route} with %00 in the id: answers {answer.status_code} {answer.text[:200]!r}, a missing id answers 404 {NOT_FOUND}")
            assert not problems, "\n".join(problems)

        print_success("✓ %00 in the id: the missing-file 404 on both routes")
