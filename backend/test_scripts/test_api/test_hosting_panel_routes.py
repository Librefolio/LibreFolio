"""
The hosting panel's routes in the app the server runs (workstream H, lot H-61, checkpoint 1): contract §3, «Adoption and
the OpenAPI tag», with the status route of §4 among them.

Under test: the composition that gives the six routes the single tag ``HOSTING_PANEL_TAG``, «Hosting panel», exported by
``backend/app/services/platform/hosting_panel/access.py``. FastAPI adds a router's tags, and an include's, to those of
the routes it includes, and never replaces them: so the tag is no longer a parent router's, it is given by each include,
and the routers stay where they are.

- ``api/v1/backup/__init__.py``: ``backup_router`` (``/backup``) has no tag of its own; it includes ``instance``,
  ``restore`` and ``exports`` with «Backup & Export», and ``panel``, the four backup routes of the panel, with «Hosting
  panel».
- ``api/v1/system/__init__.py``: the ``/system`` router includes each resource router with «System», but ``wake``,
  ``POST /system/wake-sync``, with «Hosting panel».
- ``api/v1/router.py`` includes one of the panel's routers only, the new ``api/v1/panel.py`` (the status route of §4),
  under ``/panel`` with «Hosting panel».

Then what each route asks for and documents through ``panel_access(scope)``: the security scheme of its scope, and the
429 of the limiter the three scopes share. Read on ``backend.app.main.app``, the app the server runs, in two views: its
route table (``fastapi.routing.iter_route_contexts``, the effective routes, prefixes and tags applied) and its OpenAPI
document (``app.openapi()``, the document ``api sync`` writes for the web app's client). Both views give the effective
tags, whichever router or include adds them: the tests pin the outcome, never the composition.

- HPR-001, the tag: ``access.HOSTING_PANEL_TAG`` is ``"Hosting panel"``.
- HPR-002, each of the six panel routes of ``PANEL_ROUTES``: its method and path are served by exactly one route, whose
  endpoint is the function pinned there (paths, methods and endpoint names do not change), whose tags are exactly
  ``["Hosting panel"]``, in the route table and in the document, and whose ``operationId`` is the string pinned there.
  FastAPI's default ``generate_unique_id`` (``fastapi/utils.py``; ``backend.app.main`` names no other) makes it from the
  endpoint's name and the full path, ``re.sub(r"\\W", "_", name + path)``, then ``_`` and the method in lower case: so
  the five ids of today, and the aliases of the web app's client (``frontend/src/lib/api/generated.ts``), stay as they
  are, and the status route's is pinned from its first day.
- HPR-003, the tag is theirs alone: the operations of the document, and the routes of the table, that carry «Hosting
  panel» are exactly the six. Control, so the tags are read and not merely missing: two neighbours keep exactly the tag
  their include gives them, ``POST /api/v1/backup/instance`` «Backup & Export» and ``GET /api/v1/system/health``
  «System»; a parent router that kept its own tag beside the includes' would give them that tag twice (and the panel's
  routes two tags, HPR-002).
- HPR-004, the security schemes: ``BackupPanelToken`` for the four backup routes, ``WakeToken`` for the wake-up,
  ``PanelStatusToken`` for the status route, each an HTTP bearer scheme. Each of the six asks for its scope's scheme and
  nothing else; no other operation asks for any of the three, and none asks for two of them.
- HPR-005, each of the six documents 429 beside its 401, 404 and 503.

D7 (contract L3 §10 option A, the last lot of wave 4): HPR-009 pins that the panel status's ``restore`` documents
the ``unreadable`` state and its reasons (``io``, ``not_a_file``, ``invalid``). Red until D7.

H-62 (contract L3 §5) adds the seven routes of the panel's restore (``api/v1/backup/panel_restore.py``, scope
``backup:restore``, ticket only) to ``PANEL_ROUTES``: HPR-002, HPR-003 and HPR-005 cover them as the six; HPR-004 stays on
the six token routes (``TOKEN_ROUTES``); HPR-006 pins that the seven share one bearer scheme of their own, and HPR-007
that each documents 409 and 423 too. Red until H-62.

Red at the base, ``74b4c9c88``: ``hosting_panel/access.py`` did not exist (HPR-001); the four backup routes carried
«Backup & Export» and the wake-up «System», and the status route did not exist (HPR-002, HPR-003); nor did
``PanelStatusToken`` (HPR-004); no panel route documented a 429 (HPR-005). With the includes above and the shared
dependency in place, the four cases that need the status route stay red until ``api/v1/panel.py`` serves it: HPR-002
and HPR-005 for ``GET /api/v1/panel/status``, HPR-003 and HPR-004.

Pure: the app is read, never called — no request, no server, no database, no network. The ``app`` fixture imports
``backend.app.main`` unless the process holds it already. That import configures the process's logging
(``configure_logging()``: structlog, and the root logger's handlers, one of them on the data directory's log file): here
it runs with that function replaced by a no-op, put back as soon as the import returns, and at the end of the module the
app's module leaves ``sys.modules`` again, so that a later import in the same process (the runner's workers run several
files in one) runs whole, as if this module had never imported it. What stays is what any import of the app registers,
the same each time: the media types the app serves (``register_served_types``). The document is ``app.openapi()``, read
through a JSON copy; the app's cached document is put back at the end of the module.
"""

from __future__ import annotations

import importlib
import json
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute, iter_route_contexts

from backend.app import logging_config
from backend.app.config import is_test_mode
from backend.test_scripts.test_utils import print_section, print_success

#: The tag of the six routes, spelled out: a rename is a change of this file.
HOSTING_PANEL = "Hosting panel"
#: The module of the app the server runs.
MAIN_MODULE = "backend.app.main"


@dataclass(frozen=True)
class PanelRoute:
    """A route of the hosting panel: a short name for its case, its method and full path, the endpoint that serves it
    (``<module>.<function>``), its OpenAPI ``operationId`` and the security scheme of its scope."""

    name: str
    method: str
    path: str
    endpoint: str
    operation_id: str
    scheme: str | None

    @property
    def operation(self) -> str:
        return f"{self.method} {self.path}"


#: The six routes of the hosting panel with a token scope (contract §3): the five of today as they are, and the status
#: route of §4.
TOKEN_ROUTES = (
    PanelRoute(
        "start",
        "POST",
        "/api/v1/backup/panel/jobs",
        "backend.app.api.v1.backup.panel.start_panel_backup",
        "start_panel_backup_api_v1_backup_panel_jobs_post",
        "BackupPanelToken",
    ),
    PanelRoute(
        "poll",
        "GET",
        "/api/v1/backup/panel/jobs/{job_id}",
        "backend.app.api.v1.backup.panel.get_panel_backup_job",
        "get_panel_backup_job_api_v1_backup_panel_jobs__job_id__get",
        "BackupPanelToken",
    ),
    PanelRoute(
        "download",
        "GET",
        "/api/v1/backup/panel/jobs/{job_id}/file",
        "backend.app.api.v1.backup.panel.download_panel_backup",
        "download_panel_backup_api_v1_backup_panel_jobs__job_id__file_get",
        "BackupPanelToken",
    ),
    PanelRoute(
        "delete",
        "DELETE",
        "/api/v1/backup/panel/jobs/{job_id}",
        "backend.app.api.v1.backup.panel.delete_panel_backup_job",
        "delete_panel_backup_job_api_v1_backup_panel_jobs__job_id__delete",
        "BackupPanelToken",
    ),
    PanelRoute(
        "wake-sync",
        "POST",
        "/api/v1/system/wake-sync",
        "backend.app.api.v1.system.wake.wake_sync",
        "wake_sync_api_v1_system_wake_sync_post",
        "WakeToken",
    ),
    PanelRoute(
        "status",
        "GET",
        "/api/v1/panel/status",
        "backend.app.api.v1.panel.get_panel_status",
        "get_panel_status_api_v1_panel_status_get",
        "PanelStatusToken",
    ),
)
#: H-62 (contract L3 §5): the seven routes of the panel's restore, scope ``backup:restore``, ticket only. Their scheme's
#: name is the implementation's (``None`` here): HPR-006 pins that it is one bearer scheme of their own. Red until H-62.
_RESTORE = "backend.app.api.v1.backup.panel_restore"
RESTORE_ROUTES = (
    PanelRoute("restore-upload", "PUT", "/api/v1/backup/panel/restore/upload", f"{_RESTORE}.upload_panel_restore_archive", "upload_panel_restore_archive_api_v1_backup_panel_restore_upload_put", None),
    PanelRoute("restore-stage", "POST", "/api/v1/backup/panel/restore/stage", f"{_RESTORE}.start_panel_restore_check", "start_panel_restore_check_api_v1_backup_panel_restore_stage_post", None),
    PanelRoute("restore-poll", "GET", "/api/v1/backup/panel/restore/stage/{stage_id}", f"{_RESTORE}.get_panel_restore_check", "get_panel_restore_check_api_v1_backup_panel_restore_stage__stage_id__get", None),
    PanelRoute(
        "restore-confirm",
        "POST",
        "/api/v1/backup/panel/restore/stage/{stage_id}/confirm",
        f"{_RESTORE}.confirm_panel_restore_check",
        "confirm_panel_restore_check_api_v1_backup_panel_restore_stage__stage_id__confirm_post",
        None,
    ),
    PanelRoute("restore-restart", "POST", "/api/v1/backup/panel/restore/restart", f"{_RESTORE}.restart_panel_restore", "restart_panel_restore_api_v1_backup_panel_restore_restart_post", None),
    PanelRoute("restore-status", "GET", "/api/v1/backup/panel/restore/status", f"{_RESTORE}.get_panel_restore_status", "get_panel_restore_status_api_v1_backup_panel_restore_status_get", None),
    PanelRoute("restore-cancel", "DELETE", "/api/v1/backup/panel/restore/pending", f"{_RESTORE}.cancel_panel_pending_restore", "cancel_panel_pending_restore_api_v1_backup_panel_restore_pending_delete", None),
)
#: Every route of the hosting panel: the six with a token scope and, since H-62, the seven of the restore.
PANEL_ROUTES = TOKEN_ROUTES + RESTORE_ROUTES
RESTORE_CASES = [pytest.param(route, id=route.name) for route in RESTORE_ROUTES]
#: H-62: what the restore routes document besides: 409 ``restore_mode_required`` and 423 ``instance_blocked``.
RESTORE_GATE_ANSWERS = frozenset({"409", "423"})
#: One case per route.
ROUTE_CASES = [pytest.param(route, id=route.name) for route in PANEL_ROUTES]
#: The security schemes of the three scopes (contract §2).
SCHEMES = ("BackupPanelToken", "WakeToken", "PanelStatusToken")
#: What every panel route documents through the shared dependency: 401, 404 and 503 as today, and the limiter's 429.
PANEL_ANSWERS = frozenset({"401", "404", "429", "503"})
#: The control of HPR-003: two neighbours of the panel's routes, with the single tag of their own routers.
NEIGHBOURS = {"POST /api/v1/backup/instance": ["Backup & Export"], "GET /api/v1/system/health": ["System"]}


# =============================================================================
# The app the server runs, and its two views
# =============================================================================


def _leave_logging_as_it_is(*_args: object, **_kwargs: object) -> None:
    """Stands in for ``configure_logging()`` while the ``app`` fixture imports the app: the process's logging stays as it was."""


@pytest.fixture(scope="module")
def app() -> Iterator[FastAPI]:
    """``backend.app.main.app``, read and never called. Imported here unless the process holds it already, with
    ``configure_logging`` a no-op for the import only; then dropped from ``sys.modules`` at the end of the module, so the
    process is left as it was found (the module's docstring)."""
    assert is_test_mode(), "Precondition: test mode, as every unit of the runner sets it, so the app reads the lane's test configuration only"
    if MAIN_MODULE in sys.modules:
        yield sys.modules[MAIN_MODULE].app
        return
    package = sys.modules["backend.app"]
    had_attribute = "main" in vars(package)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(logging_config, "configure_logging", _leave_logging_as_it_is)
        main = importlib.import_module(MAIN_MODULE)
    try:
        yield main.app
    finally:
        # Out of the process's modules again: a later import of the app runs whole, its logging configuration included
        sys.modules.pop(MAIN_MODULE, None)
        if not had_attribute:
            vars(package).pop("main", None)


@pytest.fixture(scope="module")
def document(app: FastAPI) -> Iterator[dict[str, Any]]:
    """The app's OpenAPI document, as ``api sync`` writes it, through a JSON copy; the app's cached document is put back
    at the end of the module."""
    cached = app.openapi_schema
    try:
        yield json.loads(json.dumps(app.openapi()))
    finally:
        app.openapi_schema = cached


def _api_routes(app: FastAPI) -> list[Any]:
    """The route table: the effective API routes of ``app``, with their full paths, methods, endpoints and tags."""
    return [context for context in iter_route_contexts(app.routes) if isinstance(context.original_route, APIRoute)]


def _endpoint_name(endpoint: object) -> str:
    """``<module>.<function>`` of an endpoint."""
    return f"{getattr(endpoint, '__module__', '?')}.{getattr(endpoint, '__name__', '?')}"


def _operations(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The operations of the document, by ``METHOD path``."""
    return {f"{method.upper()} {path}": operation for path, item in document.get("paths", {}).items() for method, operation in item.items() if isinstance(operation, dict)}


def _asked(operation: dict[str, Any]) -> list[str]:
    """The security schemes an operation asks for, in its order."""
    return [scheme for requirement in operation.get("security", []) for scheme in requirement]


# =============================================================================
# HPR-001: the tag
# =============================================================================


def test_the_tag_is_hosting_panel_from_the_access_module():
    """HPR-001: ``HOSTING_PANEL_TAG``, exported by ``services/platform/hosting_panel/access.py`` (contract §2 and §3), is
    «Hosting panel»: the single tag of the six routes, in the document and in the client generated from it."""
    print_section("HPR-001: the tag of the hosting panel's routes")
    from backend.app.services.platform.hosting_panel import access  # noqa: PLC0415 — H-61's new module, imported by the test that reads it

    tag = getattr(access, "HOSTING_PANEL_TAG", None)

    assert tag == HOSTING_PANEL, f"H-61: access.HOSTING_PANEL_TAG must be {HOSTING_PANEL!r}, not {tag!r}"
    print_success(f"HOSTING_PANEL_TAG = {tag!r}")


# =============================================================================
# HPR-002..003: the six routes, under the single tag «Hosting panel»
# =============================================================================


@pytest.mark.parametrize("route", ROUTE_CASES)
def test_each_panel_route_keeps_its_endpoint_and_operation_id_under_the_hosting_panel_tag_alone(app, document, route):
    """HPR-002: one route serves the method and the path, with the endpoint pinned in ``PANEL_ROUTES``; its tags are
    exactly «Hosting panel», in the route table and in the document; its ``operationId`` is the one pinned there, the id
    FastAPI's default builds, so the client's alias does not change."""
    served = [context for context in _api_routes(app) if context.path == route.path and route.method in (context.methods or ())]
    operation = _operations(document).get(route.operation)

    table = [(_endpoint_name(context.endpoint), list(context.tags), context.unique_id) for context in served]
    documented = None if operation is None else (operation.get("tags"), operation.get("operationId"))

    expected_table = [(route.endpoint, [HOSTING_PANEL], route.operation_id)]
    expected_document = ([HOSTING_PANEL], route.operation_id)
    assert (table, documented) == (expected_table, expected_document), (
        f"{route.operation}: exactly one route serves it, {route.endpoint}, with the single tag {HOSTING_PANEL!r} and the operationId {route.operation_id!r}, in the route table and in the document:\n"
        f"  expected table {expected_table}, document {expected_document}\n"
        f"  got      table {table}, document {documented}"
    )
    print_success(f"{route.operation}: {route.endpoint}, [{HOSTING_PANEL!r}], {route.operation_id}")


def test_only_the_six_panel_routes_carry_the_hosting_panel_tag(app, document):
    """HPR-003: the operations of the document, and the routes of the table, that carry «Hosting panel» are exactly the
    six: no other route gains it, and none of the six is listed twice. Control: two neighbours keep their routers' own
    tags, in both views, so the tags are read and not merely missing."""
    print_section("HPR-003: the tag «Hosting panel» is the six routes' alone")
    operations = _operations(document)
    routes = _api_routes(app)
    table_tags = {f"{method} {context.path}": list(context.tags) for context in routes for method in sorted(context.methods or ())}
    neighbours = ({name: operations.get(name, {}).get("tags") for name in NEIGHBOURS}, {name: table_tags.get(name) for name in NEIGHBOURS})
    assert neighbours == (NEIGHBOURS, NEIGHBOURS), f"Control: the neighbours keep their routers' tags, in the document and in the route table:\n  expected {NEIGHBOURS}\n  got      {neighbours}"

    in_document = sorted(name for name, operation in operations.items() if HOSTING_PANEL in operation.get("tags", []))
    in_table = sorted(f"{method} {context.path}" for context in routes if HOSTING_PANEL in context.tags for method in sorted(context.methods or ()))

    expected = sorted(route.operation for route in PANEL_ROUTES)
    assert (in_document, in_table) == (expected, expected), f"the routes carrying {HOSTING_PANEL!r} must be exactly the six panel routes, once each:\n  expected {expected}\n  got      document {in_document}, route table {in_table}"
    print_success(f"{len(expected)} routes carry {HOSTING_PANEL!r}, and no other: {expected}")


# =============================================================================
# HPR-004: the security scheme of each scope
# =============================================================================


def test_each_scope_has_its_bearer_scheme_and_each_route_asks_for_its_own_alone(document):
    """HPR-004: ``BackupPanelToken``, ``WakeToken`` and ``PanelStatusToken`` are HTTP bearer schemes; the four backup
    routes ask for the first, the wake-up for the second, the status route for the third, each for that scheme and
    nothing else; no other operation asks for any of the three, and none asks for two of them."""
    print_section("HPR-004: the security scheme of each scope")
    operations = _operations(document)
    schemes = document.get("components", {}).get("securitySchemes", {})

    kinds = {name: ((schemes.get(name) or {}).get("type"), (schemes.get(name) or {}).get("scheme")) for name in SCHEMES}
    asking = {name: sorted(operation_name for operation_name, operation in operations.items() if name in _asked(operation)) for name in SCHEMES}
    security = {route.operation: (operations.get(route.operation) or {}).get("security") for route in TOKEN_ROUTES}
    doubles = sorted(operation_name for operation_name, operation in operations.items() if len(set(_asked(operation)) & set(SCHEMES)) > 1)

    expected_kinds = dict.fromkeys(SCHEMES, ("http", "bearer"))
    expected_asking = {name: sorted(route.operation for route in TOKEN_ROUTES if route.scheme == name) for name in SCHEMES}
    expected_security = {route.operation: [{route.scheme: []}] for route in TOKEN_ROUTES}
    assert kinds == expected_kinds, f"each scope's scheme is an HTTP bearer scheme of the document:\n  expected {expected_kinds}\n  got      {kinds}"
    assert asking == expected_asking, f"each scheme is asked for by its scope's routes, and by no other operation:\n  expected {expected_asking}\n  got      {asking}"
    assert security == expected_security, f"each panel route asks for its scope's scheme and nothing else:\n  expected {expected_security}\n  got      {security}"
    assert doubles == [], f"no operation asks for two of {list(SCHEMES)}: {doubles}"
    print_success(f"{', '.join(f'{name}: {len(operation_names)} route(s)' for name, operation_names in asking.items())}")


# =============================================================================
# HPR-005: the documented answers
# =============================================================================


@pytest.mark.parametrize("route", ROUTE_CASES)
def test_each_panel_route_documents_429_beside_401_404_and_503(document, route):
    """HPR-005: the shared dependency answers 404 when the scope is off, 429 when the address is over the limit, 401
    without the right token and 503 when the token cannot be used: each panel route documents all four."""
    operation = _operations(document).get(route.operation)
    assert operation is not None, f"{route.operation} must be in the document: its paths are {sorted(document.get('paths', {}))}"

    documented = set(operation.get("responses", {}))

    missing = sorted(PANEL_ANSWERS - documented)
    assert missing == [], f"{route.operation} must document {sorted(PANEL_ANSWERS)}: {missing} missing; it documents {sorted(documented)}"
    print_success(f"{route.operation}: documents {sorted(PANEL_ANSWERS & documented)}")


# =============================================================================
# HPR-006..007: the routes of the panel's restore (H-62)
# =============================================================================


def test_the_restore_routes_ask_for_one_bearer_scheme_of_their_own(document):
    """HPR-006 (H-62, contract L3 §5): the seven routes of the panel's restore each ask for exactly one security scheme,
    the same for the seven, an HTTP bearer, none of the three token scopes' schemes, and asked for by no other
    operation: the restore's scope is ticket only."""
    operations = _operations(document)
    schemes = document.get("components", {}).get("securitySchemes", {})
    asked = {route.operation: _asked(operations.get(route.operation) or {}) for route in RESTORE_ROUTES}
    assert all(len(names) == 1 for names in asked.values()), f"each restore route asks for exactly one scheme: {asked}"
    names = {names[0] for names in asked.values()}
    assert len(names) == 1, f"the seven ask for the same scheme: {asked}"
    name = names.pop()
    assert name not in SCHEMES, f"the restore's scheme is its own, not one of {list(SCHEMES)}: {name}"
    assert ((schemes.get(name) or {}).get("type"), (schemes.get(name) or {}).get("scheme")) == ("http", "bearer"), f"{name} is an HTTP bearer scheme: {schemes.get(name)}"
    others = sorted(operation_name for operation_name, operation in operations.items() if name in _asked(operation) and operation_name not in asked)
    assert others == [], f"no other operation asks for {name}: {others}"
    print_success(f"the seven restore routes: {name} (bearer), theirs alone")


@pytest.mark.parametrize("route", RESTORE_CASES)
def test_each_restore_route_documents_the_mode_and_the_block(document, route):
    """HPR-007 (H-62, contract L3 §5): each restore route documents 409 (``restore_mode_required``) and 423
    (``instance_blocked``) beside the four answers of the shared dependency."""
    operation = _operations(document).get(route.operation)
    assert operation is not None, f"{route.operation} must be in the document"
    missing = sorted((PANEL_ANSWERS | RESTORE_GATE_ANSWERS) - set(operation.get("responses", {})))
    assert missing == [], f"{route.operation} must document {sorted(PANEL_ANSWERS | RESTORE_GATE_ANSWERS)}: {missing} missing"


#: SEC-review point 9: the codes of the 503 each restore route that reads a limit documents, beside the ticket settings'.
RESTORE_503_CODES = {
    "PUT /api/v1/backup/panel/restore/upload": ("backup_upload_unavailable", "backup_restore_unavailable"),
    "POST /api/v1/backup/panel/restore/stage": ("backup_restore_unavailable",),
}


@pytest.mark.parametrize("operation_name", sorted(RESTORE_503_CODES))
def test_the_restore_routes_that_read_a_limit_document_each_code_of_their_503(document, operation_name):
    """HPR-008 (H-62, SEC-review point 9): ``PUT …/panel/restore/upload`` answers 503 ``backup_upload_unavailable`` when
    the upload limit cannot be read, and 503 ``backup_restore_unavailable`` when the panel's ticket settings cannot be
    used: its 503 documents both codes. ``POST …/stage`` documents ``backup_restore_unavailable``, for the restore limit
    and for the ticket settings (guard)."""
    operation = _operations(document).get(operation_name)
    assert operation is not None, f"{operation_name} must be in the document"
    description = ((operation.get("responses") or {}).get("503") or {}).get("description", "")

    missing = [code for code in RESTORE_503_CODES[operation_name] if f"`{code}`" not in description]
    assert missing == [], f"{operation_name}: its 503 must document {list(RESTORE_503_CODES[operation_name])}: {missing} missing from {description!r}"
    print_success(f"{operation_name}: 503 documents {list(RESTORE_503_CODES[operation_name])}")


# =============================================================================
# HPR-009 (D7): the panel status's restore can be unreadable
# =============================================================================

#: D7 (contract L3 §10 option A): the states and the reasons ``PanelRestoreSummary`` must admit, and its five keys.
SUMMARY_KEYS = frozenset({"state", "reason", "waiting", "backup_created_at", "stage_id"})
SUMMARY_STATES = frozenset({"pending", "in_progress", "committed", "rolled_back", "unreadable"})
SUMMARY_REASONS = frozenset({"first_start_failed", "swap_interrupted", "swap_failed", "stage_missing", "io", "not_a_file", "invalid"})


def _component(schema: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    """``schema``, or the component its ``$ref`` names."""
    reference = schema.get("$ref")
    if not isinstance(reference, str):
        return schema
    return document.get("components", {}).get("schemas", {}).get(reference.rsplit("/", 1)[-1], {})


def _values(schema: dict[str, Any], document: dict[str, Any]) -> tuple[set[Any], bool]:
    """The values a schema's enums and consts admit, through ``$ref``, ``anyOf`` and ``oneOf``; and whether it admits
    null."""
    schema = _component(schema, document)
    values: set[Any] = set(schema.get("enum", []))
    if "const" in schema:
        values.add(schema["const"])
    nullable = schema.get("type") == "null" or None in values
    for variant in (*schema.get("anyOf", []), *schema.get("oneOf", [])):
        more, null = _values(variant, document)
        values |= more
        nullable = nullable or null
    values.discard(None)
    return values, nullable


def test_the_panel_status_restore_documents_the_unreadable_state_and_its_reasons(document):
    """HPR-009 (D7): in the document, ``PanelStatusResponse.restore`` is a ``PanelRestoreSummary`` or null; the summary
    keeps exactly its five properties (no other allowed); its ``state`` enum includes ``unreadable`` beside the four
    states of a restore recorded, its ``reason`` (nullable) the reasons of a rollback and of an unreadable state."""
    components = document.get("components", {}).get("schemas", {})
    restore = (components.get("PanelStatusResponse", {}).get("properties") or {}).get("restore", {})
    references = [variant for variant in restore.get("anyOf", [restore]) if "$ref" in variant]
    assert len(references) == 1, f"PanelStatusResponse.restore is one component or null: {restore}"
    summary = _component(references[0], document)
    properties = summary.get("properties") or {}
    assert set(properties) == SUMMARY_KEYS and summary.get("additionalProperties") is False, f"the restore summary has exactly {sorted(SUMMARY_KEYS)} and no other: {summary}"

    states, _ = _values(properties["state"], document)
    reasons, reason_nullable = _values(properties["reason"], document)
    assert SUMMARY_STATES <= states, f"D7: PanelRestoreSummary.state must admit {sorted(SUMMARY_STATES)}: missing {sorted(SUMMARY_STATES - states)}, documented {sorted(states)}"
    assert SUMMARY_REASONS <= reasons and reason_nullable, f"D7: PanelRestoreSummary.reason must admit {sorted(SUMMARY_REASONS)} or null: missing {sorted(SUMMARY_REASONS - reasons)}, documented {sorted(reasons)}, nullable {reason_nullable}"
    print_success(f"PanelRestoreSummary: state {sorted(states)}, reason {sorted(reasons)} or null")
