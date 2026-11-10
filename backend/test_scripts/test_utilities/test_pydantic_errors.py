"""
W-B77 and W-B70 (the coordinator's decisions D-W70-5 and D-W70-1, 17/10): ``backend/app/utils/pydantic_errors.py``, the one
copy of how a pydantic error becomes the ``field`` and the ``params`` of an issue.

Today the rule exists twice: in the transaction batch's parse (``transaction_batch_stages``: ``_loc_to_field``,
``_PLAIN_PARAM_TYPES``, ``_lone_error_params``, read by ``_parse_lenient``) and in the broker import's (``brim_provider``: a
``_PLAIN_PARAM_TYPES`` of its own and two static methods of ``BRIMProvider``, read by ``_create_transaction``). Both give a
field's error (``loc`` not empty) no params, whatever its context, and both copy the context of each sub-error of a packed
error (``multipleBusinessRuleErrors``) as it comes.

The contract:

1. One module, ``backend.app.utils.pydantic_errors``, replaces the two copies — deleted, no alias, no shim — and both call
   sites import from it (D-W70-5).
2. ``PLAIN_PARAM_TYPES``: a tuple of exactly ``str``, ``int``, ``float``, ``bool`` and ``NoneType``, the plain data a
   context may hold to become params.
3. ``loc_to_field(loc)``, a tuple or a list: its int parts skipped, the others joined with «.»; a leading
   ``resolved_fields`` followed by a field is dropped (H-41: a promotion's merged value is named by its own field), and
   only a leading one — ``("body", 0, "cash", "amount")`` stays ``body.cash.amount``; ``None`` when nothing is left.
4. ``error_params(error)``: a new dict, equal to ``error["ctx"]``, when that is a non-empty dict whose every value is an
   instance of ``PLAIN_PARAM_TYPES``; ``None`` when ``ctx`` is missing, None, empty, or holds one value that is not — a
   ``value_error``'s exception, a Decimal bound, a date, a list, a dict, an object. It never reads ``loc``: a field's error
   keeps its plain context (D-W70-1) — ``string_too_long`` ``{max_length}``, ``greater_than`` ``{gt}``, a date's parsing
   error ``{error: <pydantic's text>}`` — and it serves a packed sub-error (``{code, msg, ctx}``) as it serves a pydantic
   error.

Where each path is pinned. The batch's issues, its field errors and its packed sub-errors included, through
``_parse_lenient``: ``test_services/test_transaction_service.py`` and, for a promote's resolved fields,
``test_services/test_transaction_decimal_places.py`` (H-41). The broker import's, through
``BRIMProvider._create_transaction``: ``test_services/test_brim_create_transaction.py`` — but for its packed branch meeting a
context that is not plain data, which no rule of ``TXCreateItem`` raises (their contexts are ``{type}``, ``{type, qty}``,
``{type, allowed}``, ``{broker_id}``, ``{asset_id}``, ``{asset_event_id}``) and which only a patched model would reach: that
branch is pinned here, by ``error_params`` on the packed shape, and by the two call sites keeping no copy of their own
(``TestOneCopy``).

Reds — every test of the module until it exists, each failing with W-B77's reason (``_shared``), never at collection; and
``TestOneCopy`` until the copies are gone and both call sites import the module. Guards — green today and after:
``TestOneCopyDetector``, the detector ``TestOneCopy`` relies on, proven both ways on in-memory sources (an absence is
asserted only by a detector shown to see a presence).

Pure: functions over values, pydantic models of the test's own, and two source files read with ``ast`` — nothing of the app
is imported but the module under test. No database, no server, no network, no writes.

Run: ``./dev.py test utils pydantic-errors``.
"""

import ast
import importlib
from datetime import date
from decimal import Decimal
from importlib.util import resolve_name
from pathlib import Path
from types import ModuleType
from typing import Any, List, Literal, Optional

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from pydantic_core import PydanticCustomError

SHARED_MODULE = "backend.app.utils.pydantic_errors"
REPO_ROOT = Path(__file__).resolve().parents[3]

# A context made only of plain data: each of str, int, float, bool and None.
PLAIN_CONTEXT = {"type": "BUY", "qty": "1.5", "count": 2, "ratio": 0.5, "flag": True, "none": None}
# An object no response can carry.
AN_OBJECT = object()


def _shared() -> ModuleType:
    """``backend.app.utils.pydantic_errors``; its absence, before the W-B77 cure, is each case's red rather than a collection error."""
    try:
        return importlib.import_module(SHARED_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != SHARED_MODULE:
            raise
    pytest.fail(f"W-B77: {SHARED_MODULE} does not exist yet: the one module (D-W70-5) of PLAIN_PARAM_TYPES, loc_to_field and error_params, which replaces the two copies of the rule, the batch's (transaction_batch_stages) and BRIM's (brim_provider).")


def _shared_attr(name: str) -> Any:
    """``name`` of the shared module; a module without it is the case's red, named."""
    module = _shared()
    if not hasattr(module, name):
        pytest.fail(f"W-B77: {SHARED_MODULE} has no {name}: its contract is PLAIN_PARAM_TYPES, loc_to_field(loc) and error_params(error).")
    return getattr(module, name)


def _errors(model: type[BaseModel], raw: dict) -> list[dict]:
    """The errors pydantic itself reports for ``raw`` under ``model``: the premise a case checks before it reads the module."""
    with pytest.raises(ValidationError) as refused:
        model.model_validate(raw)
    return refused.value.errors()


# =============================================================================
# PLAIN_PARAM_TYPES
# =============================================================================


class TestPlainParamTypes:
    """``PLAIN_PARAM_TYPES``: what a context may hold to become params, the five JSON scalars."""

    def test_exactly_the_five_plain_types(self):
        """A tuple — ``isinstance`` reads it — of exactly ``str``, ``int``, ``float``, ``bool`` and ``NoneType``, each once."""
        plain_types = _shared_attr("PLAIN_PARAM_TYPES")
        assert isinstance(plain_types, tuple), f"PLAIN_PARAM_TYPES must be a tuple, which isinstance reads; it is {type(plain_types).__name__}"
        assert len(plain_types) == 5 and set(plain_types) == {str, int, float, bool, type(None)}, f"PLAIN_PARAM_TYPES must be exactly str, int, float, bool and NoneType; it is {plain_types}"


# =============================================================================
# loc_to_field
# =============================================================================


class TestLocToField:
    """``loc_to_field(loc)``: the dotted path of a pydantic ``loc``, what an issue's ``field`` names."""

    @pytest.mark.parametrize(
        ("loc", "field"),
        [
            pytest.param(("type",), "type", id="one-field"),
            pytest.param(("cash", "amount"), "cash.amount", id="nested"),
            pytest.param(["cash", "amount"], "cash.amount", id="a-list"),
            pytest.param(("tags", 0), "tags", id="an-item-of-a-list"),
            pytest.param(("creates", 3, "items", 1, "quantity"), "creates.items.quantity", id="indices-skipped"),
            pytest.param(("body", 0, "cash", "amount"), "body.cash.amount", id="body-is-not-stripped"),
        ],
    )
    def test_the_path_of_a_field(self, loc, field):
        """The int parts skipped, the others joined with «.»; no prefix stripped but ``resolved_fields``."""
        loc_to_field = _shared_attr("loc_to_field")
        assert loc_to_field(loc) == field

    @pytest.mark.parametrize(
        ("loc", "field"),
        [
            pytest.param(("resolved_fields", "date"), "date", id="a-merged-field"),
            pytest.param(("resolved_fields", "cost_basis_override", "code"), "cost_basis_override.code", id="a-merged-nested-field"),
            pytest.param(("resolved_fields",), "resolved_fields", id="resolved-fields-alone"),
            pytest.param(("body", "resolved_fields", "date"), "body.resolved_fields.date", id="only-a-leading-one"),
        ],
    )
    def test_a_leading_resolved_fields_is_dropped(self, loc, field):
        """H-41: a promotion's merged value is named by its own field — ``resolved_fields.date`` is ``date`` — when
        ``resolved_fields`` leads and a field follows it; alone, or not leading, it stays."""
        loc_to_field = _shared_attr("loc_to_field")
        assert loc_to_field(loc) == field

    @pytest.mark.parametrize("loc", [pytest.param((), id="empty-tuple"), pytest.param([], id="empty-list"), pytest.param((0,), id="an-index-alone"), pytest.param((0, 1), id="indices-alone")])
    def test_nothing_left_is_none(self, loc):
        """Nothing but indices, or nothing at all: ``None``, never an empty text."""
        loc_to_field = _shared_attr("loc_to_field")
        assert loc_to_field(loc) is None


# =============================================================================
# error_params
# =============================================================================


class _Probe(BaseModel):
    """A model of the test's own, each field refused by one rule of pydantic's: the errors ``error_params`` reads in the app."""

    model_config = ConfigDict(extra="forbid")

    text: Optional[str] = Field(default=None, max_length=5)
    count: Optional[int] = Field(default=None, gt=0)
    price: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    day: Optional[date] = None
    kind: Optional[Literal["BUY", "SELL"]] = None
    items: Optional[List[int]] = Field(default=None, max_length=2)
    checked: Optional[int] = None

    @field_validator("checked")
    @classmethod
    def _at_most_one(cls, value: Optional[int]) -> Optional[int]:
        """A validator's refusal: pydantic's ``value_error``, its context the exception itself."""
        if value is not None and value > 1:
            raise ValueError("checked must be at most 1")
        return value


# The sub-errors ``_Packed`` packs, shaped as ``TXCreateItem`` packs its own (``{code, msg, ctx}``): an object beside a plain
# value and an exception — contexts no rule of the app packs today —, a plain context and an empty one.
PACKED_SUB_ERRORS = [
    {"code": "objectRule", "msg": "an object in its context", "ctx": {"type": "BUY", "obj": AN_OBJECT}},
    {"code": "exceptionRule", "msg": "an exception in its context", "ctx": {"error": ValueError("not plain data")}},
    {"code": "plainRule", "msg": "a plain context", "ctx": dict(PLAIN_CONTEXT)},
    {"code": "emptyRule", "msg": "an empty context", "ctx": {}},
]


class _Packed(BaseModel):
    """A row refused the way ``TXCreateItem`` refuses one breaking several rules: one ``multipleBusinessRuleErrors``, its
    ``ctx.errors`` the ``PACKED_SUB_ERRORS``. ``row`` only gives it something to validate."""

    row: int

    @model_validator(mode="after")
    def _pack(self) -> "_Packed":
        raise PydanticCustomError("multipleBusinessRuleErrors", "{error_count} business-rule validation errors", {"error_count": len(PACKED_SUB_ERRORS), "errors": PACKED_SUB_ERRORS})


class TestErrorParams:
    """``error_params(error)``: an error's context as the issue's params, when it is plain data (D-W70-1)."""

    def test_a_plain_context_is_copied(self):
        """A plain context: a new dict, equal to it; changing the params leaves the error's context as it was."""
        error_params = _shared_attr("error_params")
        context = dict(PLAIN_CONTEXT)
        error = {"type": "someRule", "loc": (), "msg": "m", "ctx": context}

        params = error_params(error)

        assert params == PLAIN_CONTEXT
        assert params is not context, "a new dict, not the error's context itself"
        params["type"] = "SELL"
        params["added"] = 1
        assert error["ctx"] is context and context == PLAIN_CONTEXT, f"changing the params must leave the error's context as it was; it reads {context}"

    @pytest.mark.parametrize(
        ("error", "params"),
        [
            pytest.param({"type": "string_too_long", "loc": ("description",), "msg": "m", "ctx": {"max_length": 500}}, {"max_length": 500}, id="string-too-long-on-a-field"),
            pytest.param({"type": "greater_than", "loc": ("id_a",), "msg": "m", "ctx": {"gt": 0}}, {"gt": 0}, id="greater-than-on-a-field"),
            pytest.param({"type": "greater_than_equal", "loc": ("body", 0, "asset_event_id"), "msg": "m", "ctx": {"ge": 0}}, {"ge": 0}, id="greater-than-equal-on-a-nested-field"),
            pytest.param({"type": "date_from_datetime_parsing", "loc": ("resolved_fields", "date"), "msg": "m", "ctx": {"error": "day value is outside expected range"}}, {"error": "day value is outside expected range"}, id="a-date-parsing-error-on-a-merged-field"),
            pytest.param({"type": "someRule", "loc": (), "msg": "m", "ctx": dict(PLAIN_CONTEXT)}, PLAIN_CONTEXT, id="model-level"),
            pytest.param({"type": "someRule", "msg": "m", "ctx": dict(PLAIN_CONTEXT)}, PLAIN_CONTEXT, id="no-loc-at-all"),
        ],
    )
    def test_loc_is_never_read(self, error, params):
        """W-B70 (D-W70-1): a field's error keeps its plain context as a model-level one does — ``loc`` given, empty or
        missing changes nothing. Today both copies give a field's error ``None``."""
        error_params = _shared_attr("error_params")
        assert error_params(error) == params

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(ValueError("Value out of range"), id="exception"),
            pytest.param(Decimal("1.5"), id="decimal"),
            pytest.param(date(2024, 1, 15), id="date"),
            pytest.param(["BUY", "SELL"], id="list"),
            pytest.param({"type": "BUY"}, id="dict"),
            pytest.param(AN_OBJECT, id="object"),
        ],
    )
    @pytest.mark.parametrize("loc", [pytest.param((), id="model-level"), pytest.param(("description",), id="field")])
    def test_one_value_not_plain_gives_none(self, loc, value):
        """One value that is not plain data, among plain ones, and the whole context stays out: ``None``."""
        error_params = _shared_attr("error_params")
        assert error_params({"type": "someRule", "loc": loc, "msg": "m", "ctx": {**PLAIN_CONTEXT, "extra": value}}) is None

    @pytest.mark.parametrize(
        "error",
        [
            pytest.param({"type": "missing", "loc": ("broker_id",), "msg": "m"}, id="ctx-missing"),
            pytest.param({"type": "someRule", "loc": (), "msg": "m", "ctx": None}, id="ctx-none"),
            pytest.param({"type": "someRule", "loc": (), "msg": "m", "ctx": {}}, id="ctx-empty"),
            pytest.param({"code": "emptyRule", "msg": "m", "ctx": {}}, id="packed-ctx-empty"),
        ],
    )
    def test_no_context_gives_none(self, error):
        """No context, or an empty one: ``None``, never an empty dict."""
        error_params = _shared_attr("error_params")
        assert error_params(error) is None

    def test_a_packed_sub_error_is_read_as_a_pydantic_error(self):
        """D-W70-1: the sub-errors of a packed error go through the same filter, each one. ``{code, msg, ctx}`` — no
        ``type``, no ``loc`` —: its context when plain, a new dict; otherwise ``None``. The broker import's packed branch
        meets no other filter: this is where its non-plain case is pinned."""
        error_params = _shared_attr("error_params")
        plain = {"code": "cashSignNegative", "msg": "BUY requires cash.amount < 0", "ctx": {"type": "BUY"}}
        params = error_params(plain)
        assert params == {"type": "BUY"}
        assert params is not plain["ctx"], "a new dict, not the sub-error's context itself"
        assert error_params({"code": "objectRule", "msg": "m", "ctx": {"type": "BUY", "obj": AN_OBJECT}}) is None
        assert error_params({"code": "exceptionRule", "msg": "m", "ctx": {"error": ValueError("not plain data")}}) is None

    def test_the_sub_errors_pydantic_reports_of_a_packed_error(self):
        """The packed shape as pydantic hands it over (``ctx.errors``): each sub-error's params, its plain context or
        ``None`` — the object and the exception never reach a response."""
        error_params = _shared_attr("error_params")
        errors = _errors(_Packed, {"row": 1})
        assert [(error["type"], error["loc"]) for error in errors] == [("multipleBusinessRuleErrors", ())], f"premise: one packed error, model-level; pydantic reports {errors}"
        sub_errors = errors[0]["ctx"]["errors"]
        assert [sub_error["code"] for sub_error in sub_errors] == ["objectRule", "exceptionRule", "plainRule", "emptyRule"], f"premise: pydantic hands the four sub-errors over as packed; it reports {sub_errors}"

        params = {sub_error["code"]: error_params(sub_error) for sub_error in sub_errors}

        assert params == {"objectRule": None, "exceptionRule": None, "plainRule": PLAIN_CONTEXT, "emptyRule": None}

    @pytest.mark.parametrize(
        ("raw", "code", "carries_params"),
        [
            pytest.param({"text": "toolong"}, "string_too_long", True, id="string-too-long"),
            pytest.param({"count": 0}, "greater_than", True, id="greater-than-an-int"),
            pytest.param({"day": "2026-02-30"}, "date_from_datetime_parsing", True, id="date-parsing"),
            pytest.param({"kind": "HOLD"}, "literal_error", True, id="literal-error"),
            pytest.param({"items": [1, 2, 3]}, "too_long", True, id="list-too-long"),
            pytest.param({"price": "0"}, "greater_than", False, id="greater-than-a-decimal"),
            pytest.param({"checked": 2}, "value_error", False, id="value-error"),
            pytest.param({"unknown": 1}, "extra_forbidden", False, id="extra-forbidden"),
            pytest.param({"text": 5}, "string_type", False, id="string-type"),
        ],
    )
    def test_the_errors_pydantic_reports(self, raw, code, carries_params):
        """pydantic's own errors, on the field each one names: its context, copied, when every value is plain data —
        ``{max_length}``, ``{gt}`` of an int, a date's parsing text, a literal's expected values, a list's lengths; ``None``
        for a ``{gt}`` holding a Decimal, a ``value_error``'s exception, and an error without context. The values are
        pydantic's, never pinned here: the case reads them from the error."""
        error_params = _shared_attr("error_params")
        loc_to_field = _shared_attr("loc_to_field")
        errors = _errors(_Probe, raw)
        assert [error["type"] for error in errors] == [code], f"premise: {raw} is refused by {code} alone; pydantic reports {errors}"
        error = errors[0]

        params = error_params(error)

        assert loc_to_field(error["loc"]) == next(iter(raw)), f"the field of {error['loc']}"
        if carries_params:
            assert params == error["ctx"], f"{code}: its plain context {error['ctx']!r} is its params; got {params!r}"
            assert params is not error["ctx"], "a new dict, not pydantic's context itself"
        else:
            assert params is None, f"{code}: its context {error.get('ctx')!r} is not plain data, or there is none: no params; got {params!r}"


# =============================================================================
# W-B77: ONE COPY — the two call sites keep none of their own
# =============================================================================

# The two call sites, by path and by package (a relative import resolves against it): moved, the guard fails loudly instead
# of scanning nothing.
CALL_SITES = {
    "the transaction batch's parse": (REPO_ROOT / "backend" / "app" / "services" / "transactions" / "transaction_batch_stages.py", "backend.app.services.transactions"),
    "the broker import's parse": (REPO_ROOT / "backend" / "app" / "services" / "brim" / "brim_provider.py", "backend.app.services.brim"),
}
# The names the two copies go by today, and the shared module's own: a call site binds none of them itself — no def, no
# assignment, no class attribute: no copy, no shim, no alias. It imports the shared names; an import renamed to one of
# them is an alias too.
OLD_NAMES = frozenset({"_loc_to_field", "_lone_error_params", "_PLAIN_PARAM_TYPES"})
SHARED_NAMES = frozenset({"loc_to_field", "error_params", "PLAIN_PARAM_TYPES"})


def _bindings(node: ast.AST) -> list[str]:
    """The names ``node`` binds: a def's or a class's name, an assignment's targets (a name, or the attribute of
    ``Provider.x = …``), the new name of a renamed import."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [node.name]
    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        stored = [part for target in targets for part in ast.walk(target) if isinstance(getattr(part, "ctx", None), ast.Store)]
        return [part.id if isinstance(part, ast.Name) else part.attr for part in stored if isinstance(part, (ast.Name, ast.Attribute))]
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return [alias.asname for alias in node.names if alias.asname]
    return []


def copies_in(source: str) -> list[str]:
    """Each binding of an old or a shared name in ``source``, with its line: what a call site still holds of the rule."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        found.extend(f"{name} (line {node.lineno})" for name in _bindings(node) if name in OLD_NAMES | SHARED_NAMES)
    return found


def imports_shared(source: str, package: str) -> bool:
    """Whether ``source`` imports the shared module, or from it: absolute, relative (resolved against ``package``), the
    module itself from ``backend.app.utils``, at module level or inside a function."""
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import) and any(alias.name == SHARED_MODULE for alias in node.names):
            return True
        if isinstance(node, ast.ImportFrom):
            module = resolve_name("." * node.level + (node.module or ""), package) if node.level else node.module
            if module == SHARED_MODULE or (module == "backend.app.utils" and any(alias.name == "pydantic_errors" for alias in node.names)):
                return True
    return False


# Every shape a copy could keep: a def at module level and as a static method, a constant, an annotated one, a class
# attribute, an attribute assigned from outside, an import renamed to an old name — each of the six names at least once.
COPY_SHAPES = """
from backend.app.utils.pydantic_errors import error_params as _lone_error_params
_PLAIN_PARAM_TYPES = (str, int, float, bool, type(None))
PLAIN_PARAM_TYPES: tuple = _PLAIN_PARAM_TYPES
def _loc_to_field(loc):
    return ".".join(str(part) for part in loc if not isinstance(part, int))
class Provider:
    @staticmethod
    def loc_to_field(loc):
        return _loc_to_field(loc)
    _loc_to_field = staticmethod(_loc_to_field)
Provider.error_params = staticmethod(_lone_error_params)
"""
# The shape the cure leaves: the shared names imported and called, bound to nothing else.
CURE_SHAPE = """
from backend.app.utils.pydantic_errors import error_params, loc_to_field
def parse(errors):
    params = [error_params(error) for error in errors]
    return [(loc_to_field(error.get("loc", ())), each) for error, each in zip(errors, params)]
"""


class TestOneCopyDetector:
    """Guard, green today and after: the detector ``TestOneCopy`` relies on sees a copy in every shape, and leaves the
    shape of the cure alone; it finds the shared module in every import form, and nowhere else."""

    def test_it_sees_every_shape_of_a_copy(self):
        found = copies_in(COPY_SHAPES)
        assert {entry.split(" ")[0] for entry in found} == OLD_NAMES | SHARED_NAMES, f"the detector must see each of the six names bound in COPY_SHAPES; it found {found}"

    def test_it_leaves_the_shape_of_the_cure_alone(self):
        assert copies_in(CURE_SHAPE) == []
        assert imports_shared(CURE_SHAPE, "backend.app.services.transactions")

    @pytest.mark.parametrize(
        ("source", "package"),
        [
            pytest.param("from backend.app.utils import pydantic_errors\n", "backend.app.services.brim", id="the-module-from-utils"),
            pytest.param("import backend.app.utils.pydantic_errors\n", "backend.app.services.brim", id="import-the-module"),
            pytest.param("from ...utils.pydantic_errors import error_params\n", "backend.app.services.transactions", id="relative"),
            pytest.param("def parse(error):\n    from backend.app.utils.pydantic_errors import error_params\n    return error_params(error)\n", "backend.app.services.brim", id="inside-a-function"),
        ],
    )
    def test_it_finds_every_import_of_the_module(self, source, package):
        assert imports_shared(source, package)

    @pytest.mark.parametrize(
        "source",
        [
            pytest.param("from backend.app.utils.datetime_utils import utcnow\n", id="another-utility"),
            pytest.param("from backend.app.utils import datetime_utils\n", id="another-module-from-utils"),
            pytest.param("import backend.app.utils\n", id="the-package"),
            pytest.param("from .pydantic_errors import error_params\n", id="a-namesake-elsewhere"),
        ],
    )
    def test_another_import_is_not_the_module(self, source):
        assert not imports_shared(source, "backend.app.services.brim")


class TestOneCopy:
    """W-B77 (D-W70-5): the transaction batch's parse and the broker import's keep no copy of the rule — deleted, no alias,
    no shim — and import the shared module. Red today: each holds its own (the batch ``_loc_to_field``,
    ``_PLAIN_PARAM_TYPES``, ``_lone_error_params``; the broker import ``_PLAIN_PARAM_TYPES`` and two static methods of
    ``BRIMProvider``), and neither imports the module."""

    @pytest.mark.parametrize("site", list(CALL_SITES), ids=["batch", "brim"])
    def test_the_call_site_keeps_no_copy_and_imports_the_shared_module(self, site):
        path, package = CALL_SITES[site]
        assert path.is_file(), f"scaffold: {site} is no longer at {path}: the guard would scan nothing"
        source = path.read_text(encoding="utf-8")

        violations = []
        copies = copies_in(source)
        if copies:
            violations.append(f"it still binds {', '.join(copies)}")
        if not imports_shared(source, package):
            violations.append(f"it does not import {SHARED_MODULE}")

        assert violations == [], f"W-B77 (D-W70-5): {site} ({path.relative_to(REPO_ROOT)}) must keep no copy of the rule — no alias, no shim — and import {SHARED_MODULE}: {'; '.join(violations)}"
