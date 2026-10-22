"""Uploaded content reaches the browser only as types that cannot run (``backend/app/api/v1/uploads.py``, ``backend/app/api/v1/brokers.py``).

Two routes send back a file that a user uploaded:

* the text preview of an upload (``GET /api/v1/uploads/file/{file_id}`` with ``?offset=`` or
  ``?window=``) is always ``text/plain; charset=utf-8`` with ``X-Content-Type-Options: nosniff``,
  whatever type was stored for the file: an uploaded document is shown, never run. A stored CSV is
  still readable as text;
* a broker report (``GET /api/v1/brokers/import/files/{file_id}/download``) opens in place
  (``Content-Disposition: inline``) only when ``download=false`` is asked for and the type guessed
  from its file name cannot carry active content (PDF, JSON, plain text, CSV, raster images). Any
  other type, and every request with ``download=true`` (the default), is an attachment. Every
  answer carries ``nosniff``.

Each router is mounted on a fresh app whose sign-in (and session) dependencies are overridden; the
broker import router is mounted alone, so its routes answer under ``/api/v1/import``. A broker
report's storage lookups are monkeypatched to hand back a file written under ``tmp_path``; an
upload is a real one, its file and sidecar written into a data directory of the test's own under
``tmp_path``, uploaded by the signed-in user (whom decision 36 lets see it whatever its scope). The
assertions read behaviour only, never a constant of the modules, so the file runs unchanged against
older releases. No DB, no server, no network.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI, HTTPException

import backend.app.api.v1.brokers as brokers
import backend.app.api.v1.uploads as uploads
from backend.app.services.files.static_uploads import get_uploads_dir

SIGNED_IN = SimpleNamespace(id=1, is_superuser=False)

UPLOAD_ID = "3f0d6a52-text-preview"
REPORT_ID = "9c41e7b0-broker-report"
REPORT_BYTES = b"report body\n"

HTML_DOCUMENT = "<!doctype html>\n<html><body><h1>Quarterly report</h1><p>Shown as text.</p></body></html>\n"
XML_DOCUMENT = '<?xml version="1.0" encoding="utf-8"?>\n<report><line amount="12.50">Fee</line></report>\n'
CSV_DOCUMENT = "date,amount,currency\n2026-01-02,12.50,EUR\n2026-01-03,7.25,EUR\n"

PREVIEW_QUERIES = {"offset": {"offset": "0"}, "window": {"window": "4096"}}

#: Report names whose type can carry active content, or is unknown: never shown in place.
ACTIVE_OR_UNKNOWN_REPORTS = ["report.html", "report.svg", "report.xml", "report.xhtml", "report"]
#: Report names whose type cannot carry active content: shown in place when asked.
SAFE_REPORTS = ["report.pdf", "report.png", "report.csv", "report.json", "report.txt"]


def _media_type(response: httpx.Response) -> tuple[str, dict[str, str]]:
    """``Content-Type`` split into its lower-cased type and parameters."""
    kind, *params = (part.strip() for part in response.headers.get("content-type", "").split(";"))
    parsed = {}
    for param in params:
        name, _, value = param.partition("=")
        parsed[name.strip().lower()] = value.strip().strip('"').lower()
    return kind.lower(), parsed


def _disposition(response: httpx.Response) -> str:
    """The disposition type of ``Content-Disposition``: ``inline`` or ``attachment``."""
    return response.headers.get("content-disposition", "").split(";")[0].strip().lower()


async def _get(app: FastAPI, url: str, params: dict | None = None) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(url, params=params)


# ---------------------------------------------------------------------------
# Text preview of an upload: /api/v1/uploads/file/{file_id}?offset=…|window=…
# ---------------------------------------------------------------------------


def uploads_app() -> FastAPI:
    """The uploads router on a fresh app, signed in: the global app is left untouched."""
    app = FastAPI()
    app.include_router(uploads.router, prefix="/api/v1")
    app.dependency_overrides[uploads.get_current_user] = lambda: SIGNED_IN
    return app


@pytest.fixture
def store_upload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Store one upload of the signed-in user with the given text and stored type; return its id.

    A real file and its sidecar, in a data directory of this test's own under ``tmp_path``: the route
    finds it, may show it to its uploader and reads the stored type, through the service as for any
    upload. The id is new at each call, so no sidecar of another test is ever confused with it.
    """
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    uploads_dir = get_uploads_dir()
    assert uploads_dir.is_relative_to(tmp_path.resolve()), f"the uploads directory must be this test's own, under {tmp_path}, not {uploads_dir}"

    def store(text: str, stored_type: str) -> str:
        file_id = f"{UPLOAD_ID}-{uuid.uuid4().hex[:8]}"
        content = text.encode("utf-8")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        (uploads_dir / f"{file_id}.upload").write_bytes(content)
        sidecar = {
            "id": file_id,
            "original_name": "document.upload",
            "extension": ".upload",
            "mime_type": stored_type,
            "size_bytes": len(content),
            "uploaded_at": "2026-01-15T09:30:00+00:00",
            "uploaded_by_user_id": SIGNED_IN.id,
            "description": None,
            "scope": "personal",
        }
        (uploads_dir / f"{file_id}.json").write_text(json.dumps(sidecar))
        return file_id

    return store


@pytest.mark.asyncio
@pytest.mark.parametrize("query", PREVIEW_QUERIES.values(), ids=list(PREVIEW_QUERIES))
@pytest.mark.parametrize(("stored_type", "text"), [("text/html", HTML_DOCUMENT), ("text/xml", XML_DOCUMENT)], ids=["text-html", "text-xml"])
async def test_text_preview_is_plain_text_whatever_the_stored_type(store_upload, stored_type: str, text: str, query: dict) -> None:
    file_id = store_upload(text, stored_type)

    response = await _get(uploads_app(), f"/api/v1/uploads/file/{file_id}", params=query)

    assert response.status_code == 200
    kind, params = _media_type(response)
    assert kind == "text/plain", f"an upload stored as {stored_type} was previewed as {response.headers.get('content-type')}"
    assert params.get("charset") == "utf-8"
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.content == text.encode("utf-8")


@pytest.mark.asyncio
@pytest.mark.parametrize(("query", "expected"), [({"offset": "0"}, CSV_DOCUMENT), ({"window": "21"}, CSV_DOCUMENT[:21])], ids=["whole-file", "first-characters"])
async def test_text_preview_of_a_csv_upload_is_still_readable(store_upload, query: dict, expected: str) -> None:
    file_id = store_upload(CSV_DOCUMENT, "text/csv")

    response = await _get(uploads_app(), f"/api/v1/uploads/file/{file_id}", params=query)

    assert response.status_code == 200
    assert _media_type(response)[0].startswith("text/")
    assert response.content == expected.encode("utf-8")


# ---------------------------------------------------------------------------
# Broker report: /api/v1/import/files/{file_id}/download
# ---------------------------------------------------------------------------


def brim_app() -> FastAPI:
    """The broker import router on a fresh app, signed in, with no session: the global app is left untouched."""
    app = FastAPI()
    app.include_router(brokers.brim_router, prefix="/api/v1")
    app.dependency_overrides[brokers.get_current_user] = lambda: SIGNED_IN
    app.dependency_overrides[brokers.get_session_generator] = lambda: None
    return app


@pytest.fixture
def store_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Store one broker report under ``tmp_path``, known to the route by ``filename``; return its id."""

    def store(filename: str) -> str:
        path = tmp_path / "stored-report.bin"
        path.write_bytes(REPORT_BYTES)

        async def file_with_access(file_id: str, current_user, session, **_kwargs) -> SimpleNamespace:
            if file_id != REPORT_ID:
                raise HTTPException(status_code=404, detail="File not found")
            return SimpleNamespace(filename=filename, target_broker_id=None)

        monkeypatch.setattr(brokers, "_get_brim_file_with_access", file_with_access)
        monkeypatch.setattr(brokers.brim_provider, "get_file_path", lambda file_id: path if file_id == REPORT_ID else None)
        return REPORT_ID

    return store


def _download_url(file_id: str) -> str:
    return f"/api/v1/import/files/{file_id}/download"


@pytest.mark.asyncio
@pytest.mark.parametrize("filename", ACTIVE_OR_UNKNOWN_REPORTS)
async def test_report_of_an_active_or_unknown_type_is_always_a_download(store_report, filename: str) -> None:
    file_id = store_report(filename)

    response = await _get(brim_app(), _download_url(file_id), params={"download": "false"})

    assert response.status_code == 200
    assert _disposition(response) == "attachment", f"{filename} ({response.headers.get('content-type')}) was sent {response.headers.get('content-disposition')!r}"
    assert response.content == REPORT_BYTES


@pytest.mark.asyncio
@pytest.mark.parametrize("filename", SAFE_REPORTS)
async def test_report_of_a_safe_type_opens_in_place_when_asked(store_report, filename: str) -> None:
    file_id = store_report(filename)

    response = await _get(brim_app(), _download_url(file_id), params={"download": "false"})

    assert response.status_code == 200
    assert _disposition(response) == "inline", f"{filename} ({response.headers.get('content-type')}) was sent {response.headers.get('content-disposition')!r}"
    assert response.content == REPORT_BYTES


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [None, {"download": "true"}], ids=["default", "download-true"])
@pytest.mark.parametrize("filename", ["report.pdf", "report.png", "report.csv", "report.html"])
async def test_report_is_a_download_by_default_and_with_download_true(store_report, filename: str, params: dict | None) -> None:
    file_id = store_report(filename)

    response = await _get(brim_app(), _download_url(file_id), params=params)

    assert response.status_code == 200
    assert _disposition(response) == "attachment"
    assert response.content == REPORT_BYTES


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [None, {"download": "true"}, {"download": "false"}], ids=["default", "download-true", "download-false"])
@pytest.mark.parametrize("filename", ["report.pdf", "report.html", "report.svg", "report"])
async def test_every_report_answer_forbids_type_sniffing(store_report, filename: str, params: dict | None) -> None:
    file_id = store_report(filename)

    response = await _get(brim_app(), _download_url(file_id), params=params)

    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"


# ---------------------------------------------------------------------------
# H-55 v2 review (R1 a, b): an uploaded file never reaches the browser as a script
# ---------------------------------------------------------------------------
#
# ``script-src 'self'`` trusts every same-origin file, so a stored ``report.js`` served as ``text/javascript`` runs from a
# ``<script src>`` of the app's own origin. Two cures, pinned here:
#
# * a broker report that is not shown in place goes out as ``application/octet-stream`` + attachment, its own name kept,
#   whatever its extension; a type that cannot carry active content keeps its own type, inline, when asked in place;
# * the two file routes (the report's download, ``GET /api/v1/uploads/file/{id}``) refuse a request whose
#   ``Sec-Fetch-Dest`` says the browser means to run the answer: 403 ``file_not_a_script``.

OCTET_STREAM = "application/octet-stream"

#: Report names that must never go out under their own type: a script's, a page's, an image that can carry script.
SCRIPT_LIKE_REPORTS = ["q3-report.js", "q3-report.mjs", "q3-report.html", "q3-report.svg"]
#: (report name, its type) of the types that cannot carry active content.
INLINE_SAFE_REPORTS = [("q3-report.csv", "text/csv"), ("q3-report.pdf", "application/pdf"), ("q3-report.png", "image/png"), ("q3-report.json", "application/json"), ("q3-report.txt", "text/plain")]

#: The destinations of a fetch that runs the answer as code (the guard's list, written here).
SCRIPT_DESTINATIONS = ["script", "worker", "sharedworker", "serviceworker", "audioworklet", "paintworklet"]
#: The ways a browser says it will not run it (``empty`` is a ``fetch()``/XHR), and the same header spelled in other cases.
PASSING_DESTINATIONS = ["document", "image", "empty", "iframe", "style", "font"]
SCRIPT_SPELLINGS = ["SCRIPT", "Script", "  script  ", "WorkEr", "SharedWorker", "SERVICEWORKER"]


def _filename_of(response: httpx.Response) -> str:
    """The file name of ``Content-Disposition`` (the plain ``filename=`` parameter), or ``""``."""
    for part in response.headers.get("content-disposition", "").split(";")[1:]:
        name, _, value = part.strip().partition("=")
        if name.lower() == "filename":
            return value.strip('"')
    return ""


async def _get_with(app: FastAPI, url: str, headers: dict[str, str] | None = None, params: dict | None = None) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(url, headers=headers, params=params)


def _not_a_script_refusal(response: httpx.Response, what: str) -> None:
    assert response.status_code == 403, f"{what}: answered {response.status_code}, wanted 403: {response.text[:200]}"
    detail = response.json().get("detail")
    assert isinstance(detail, dict) and detail.get("code") == "file_not_a_script", f"{what}: detail is {detail!r}, wanted an object whose code is 'file_not_a_script'"
    assert detail.get("message"), f"{what}: the refusal carries no message"


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [None, {"download": "true"}, {"download": "false"}], ids=["default", "download-true", "download-false"])
@pytest.mark.parametrize("filename", SCRIPT_LIKE_REPORTS)
async def test_a_report_that_could_run_goes_out_as_octet_stream_with_its_own_name(store_report, filename: str, params: dict | None) -> None:
    file_id = store_report(filename)

    response = await _get(brim_app(), _download_url(file_id), params=params)

    assert response.status_code == 200
    assert _media_type(response)[0] == OCTET_STREAM, f"{filename} was sent as {response.headers.get('content-type')}: a report that is not shown in place never carries its own (script, page, image) type"
    assert _disposition(response) == "attachment"
    assert _filename_of(response) == filename, f"the original name is kept: {response.headers.get('content-disposition')!r}"
    assert response.content == REPORT_BYTES


@pytest.mark.asyncio
@pytest.mark.parametrize(("filename", "own_type"), INLINE_SAFE_REPORTS)
async def test_a_safe_report_keeps_its_own_type_when_shown_in_place(store_report, filename: str, own_type: str) -> None:
    file_id = store_report(filename)

    response = await _get(brim_app(), _download_url(file_id), params={"download": "false"})

    assert response.status_code == 200
    assert _media_type(response)[0] == own_type, f"{filename} was sent as {response.headers.get('content-type')}, not {own_type}"
    assert _disposition(response) == "inline"
    assert response.content == REPORT_BYTES


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [None, {"download": "true"}], ids=["default", "download-true"])
@pytest.mark.parametrize(("filename", "own_type"), INLINE_SAFE_REPORTS)
async def test_a_download_is_always_octet_stream_even_for_a_safe_type(store_report, filename: str, own_type: str, params: dict | None) -> None:
    file_id = store_report(filename)

    response = await _get(brim_app(), _download_url(file_id), params=params)

    assert response.status_code == 200
    assert _media_type(response)[0] == OCTET_STREAM, f"{filename} asked as a download was sent as {response.headers.get('content-type')}, not {OCTET_STREAM}"
    assert _disposition(response) == "attachment"
    assert _filename_of(response) == filename
    assert response.content == REPORT_BYTES


@pytest.mark.asyncio
@pytest.mark.parametrize("destination", SCRIPT_DESTINATIONS + SCRIPT_SPELLINGS)
async def test_the_report_download_refuses_a_script_destination(store_report, destination: str) -> None:
    file_id = store_report("q3-report.csv")

    response = await _get_with(brim_app(), _download_url(file_id), headers={"Sec-Fetch-Dest": destination})

    _not_a_script_refusal(response, f"download with Sec-Fetch-Dest {destination!r}")


@pytest.mark.asyncio
@pytest.mark.parametrize("destination", PASSING_DESTINATIONS + [None])
async def test_the_report_download_answers_any_other_destination_and_no_header(store_report, destination: str | None) -> None:
    file_id = store_report("q3-report.csv")

    response = await _get_with(brim_app(), _download_url(file_id), headers={"Sec-Fetch-Dest": destination} if destination is not None else None)

    assert response.status_code == 200, f"Sec-Fetch-Dest {destination!r}: {response.status_code} {response.text[:200]}"
    assert response.content == REPORT_BYTES


@pytest.mark.asyncio
@pytest.mark.parametrize("destination", SCRIPT_DESTINATIONS + SCRIPT_SPELLINGS)
async def test_the_static_upload_refuses_a_script_destination(store_upload, destination: str) -> None:
    file_id = store_upload(CSV_DOCUMENT, "text/csv")

    response = await _get_with(uploads_app(), f"/api/v1/uploads/file/{file_id}", headers={"Sec-Fetch-Dest": destination})

    _not_a_script_refusal(response, f"upload with Sec-Fetch-Dest {destination!r}")


@pytest.mark.asyncio
@pytest.mark.parametrize("destination", PASSING_DESTINATIONS + [None])
async def test_the_static_upload_answers_any_other_destination_and_no_header(store_upload, destination: str | None) -> None:
    file_id = store_upload(CSV_DOCUMENT, "text/csv")

    response = await _get_with(uploads_app(), f"/api/v1/uploads/file/{file_id}", headers={"Sec-Fetch-Dest": destination} if destination is not None else None)

    assert response.status_code == 200, f"Sec-Fetch-Dest {destination!r}: {response.status_code} {response.text[:200]}"
    assert response.content == CSV_DOCUMENT.encode("utf-8")


@pytest.mark.asyncio
@pytest.mark.parametrize("destination", ["script", "SCRIPT", "image", None])
async def test_the_guard_dependency_itself(destination: str | None) -> None:
    """``backend/app/api/file_fetch_guard.py``: ``refuse_script_destination(request)`` raises the 403 for a script destination and returns for the rest."""
    import inspect  # noqa: PLC0415 — local import, test-only

    from starlette.requests import Request  # noqa: PLC0415

    from backend.app.api.file_fetch_guard import refuse_script_destination  # noqa: PLC0415 — the module is new: a missing one fails this test, never the collection

    headers = [(b"sec-fetch-dest", destination.encode())] if destination is not None else []
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": headers, "query_string": b""})
    runs_the_answer = destination is not None and destination.strip().lower() == "script"

    try:
        outcome = refuse_script_destination(request)
        if inspect.isawaitable(outcome):
            await outcome
    except HTTPException as refusal:
        assert runs_the_answer, f"Sec-Fetch-Dest {destination!r} was refused ({refusal.status_code}): only a script destination is"
        assert refusal.status_code == 403
        assert isinstance(refusal.detail, dict) and refusal.detail.get("code") == "file_not_a_script"
    else:
        assert not runs_the_answer, f"Sec-Fetch-Dest {destination!r} passed: the guard must answer 403 file_not_a_script"
