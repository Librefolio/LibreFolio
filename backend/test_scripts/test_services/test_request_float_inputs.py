"""
Every float a request can carry refuses infinity and NaN in its schema (workstream H, platform, lot H-32; A-35 of A).

Why. A plain ``float`` takes ``inf``, ``-inf`` and ``nan``: pydantic v2 leaves ``allow_inf_nan`` on. And a request can
bring them. FastAPI parses a JSON body with Python's ``json`` (Starlette's ``Request.json()``), which reads the tokens
``Infinity``, ``-Infinity`` and ``NaN``, and turns a number too large for a double, ``1E+400``, into ``inf``; then it
validates the parsed body with ``validate_python``. A value let in at the edge is stored and used, and reads back as
``null`` (FastAPI 0.141 serialises ``inf`` and ``nan`` through pydantic, which writes ``null``), or breaks a route without
a ``response_model`` (Starlette's renderer writes JSON with ``allow_nan=False``). The rule decided for H-32: every float
reachable from a request refuses ``inf`` and ``nan`` in its schema, field by field; never in the base model, since
``StrictModel`` also backs hundreds of response and internal models.

Under test: the app of ``backend/app/main.py``, its routes, and the schemas their requests reach. The contract:

(a) What counts as a request float. The walk takes every route context of the app, through
    ``fastapi.routing.iter_route_contexts`` (an included router is a lazy ``_IncludedRouter`` in ``app.routes``, whose
    routes a plain iteration does not see), whose route is an ``APIRoute`` or a subclass of it. Of each it reads the
    effective dependant (the route's own, with the dependencies of the routers that include it) and every sub-dependant:
    the parameters of the path, the query, the headers, the cookies and the body, each with its annotation and its
    metadata. It opens ``Annotated`` (whose metadata belongs to that position), PEP 695 type aliases (a recursive one is
    walked down once), ``NewType``, type variables (their constraints or their bound), unions and ``Optional``; it goes
    into the items of ``list``, ``set``, ``frozenset``, ``deque`` and their abstract kin, the slots of a ``tuple``, the
    keys and the values of ``dict`` and its kin, and the fields of every pydantic model (``model_fields``), each model
    once per route. A *float leaf* is a position whose type is ``float`` or a subclass of it, alone or among the members
    of a union: a model field, named ``module.Model.field``; a parameter, ``param <name> (<where>) of
    <module.function>``; or a position inside one of them, ``[*]`` an item, ``[1]`` a tuple slot, ``{*}`` a dict value,
    ``{key}`` a dict key. Out of scope, as they declare no float: ``Any``, ``object`` and pydantic's ``JsonValue`` (any
    JSON value), each a free-form position instead, which the walk notes and (g) judges; the values of a ``Literal``;
    and the classes pydantic validates through their own schema (``Decimal``, which refuses ``inf`` and ``nan`` by
    default, dates, enums, uploads). Response models are not walked: the rule is about what comes in.
(b) How a leaf is judged. A ``TypeAdapter`` of the leaf's whole annotation, with the metadata of its field or parameter
    at the top level (``Annotated[annotation, *metadata]``), so that a union decides as a union
    (``str | int | float | bool | None`` takes a float as a float), and with ``ConfigDict(allow_inf_nan=...)`` when the
    model that owns the leaf sets it in its config; then ``validate_python`` of ``inf``, ``-inf``, ``nan`` and
    ``json.loads("1E+400")``, each of which must raise ``ValidationError``. The schema decides alone: a validator, or a
    check in a service, does not count. What the walk cannot read or judge is a *problem*, never skipped in silence: a
    forward reference nobody resolved; a generic it cannot open, a parametrised type alias among them; a dataclass, a
    ``TypedDict`` or a ``NamedTuple``, whose fields pydantic validates and the walk does not read; an adapter that cannot
    be built, or a probe that raises anything but a ``ValidationError``.
(c) Barriers on the real app, so that a FastAPI change hiding routes fails here instead of passing on nothing: at least
    150 API route contexts walked under ``/api/v1``, at least 60 of them with a body, among them the three routes of
    today's leaves; the five float fields of the signal annotation requests (``SignalLineCrossoverRequest.epsilon`` and
    ``relative_epsilon``, ``SignalThresholdCrossingRequest.epsilon``, ``relative_epsilon`` and ``threshold``) found, each
    reached by ``POST /api/v1/assets/prices/query`` and by ``POST /api/v1/fx/currencies/convert``; and no problem.
(d) The rule: no float leaf lets any of the four values through. Parametrised over the leaves the walk finds when this
    file is collected, with ``KNOWN_LEAVES``, the six of today, as a floor: the parametrisation is never empty, and a
    leaf of the floor the walk no longer finds fails by name. The message names the leaf, its annotation, what passed
    and the routes that reach it. Today the five signal fields pass (``FiniteFloat``, that is
    ``Annotated[float, AllowInfNan(False)]``), and ``PluginSettingWriteItem.value`` (``PluginSettingPlainValue | None``,
    ``PATCH /api/v1/settings/plugins/bulk``) is red: its float branch takes all four. The service refuses a number that
    is not finite before saving it (``validate_value``, ``services/plugin_settings/fields.py``), but the rule is the
    schema.
(e) Self-tests of the walk and of the judge, on a probe app built here: its routes in an ``APIRouter`` included under
    ``/api/v1/probe``, one in a router nested in it, one on the app itself, each walked with its full path. Reported,
    with what passes: a ``float`` field of the body (all four), ``Field(ge=0)`` alone (``inf`` and ``1E+400``), the
    float of a model inside a list of the body, a dict value, a tuple slot, a list of lists, a PEP 695 alias of
    ``float``, a recursive alias (the field and its items, and no further), a ``float`` query parameter of the nested
    router, the ``float`` of the route of the app itself, and the union of ``PluginSettingPlainValue``. Found and not
    reported: ``Annotated[float, AllowInfNan(False)]``, ``Field(ge=0, le=10)``, a field and a list item of a model whose
    config sets ``allow_inf_nan=False``, and the same union with ``Annotated[float, AllowInfNan(False)]`` as its float
    branch, the fix proposed for ``PluginSettingPlainValue``. Nothing else is a leaf there (a ``str`` key or slot,
    ``JsonValue``), and no problem. On an app of its own, a dataclass in a body is a problem, not a pass.
(f) The threat, end to end, on the probe app: ``{"x": 1E+400}``, and the same with ``NaN``, ``Infinity`` and
    ``-Infinity``, reaches the endpoint of a plain ``float`` as a number that is not finite, and never the endpoint of an
    ``Annotated[float, AllowInfNan(False)]``, which answers 422 ``finite_number``. The probe app writes its 422 without
    the ``input`` of each error: FastAPI's own handler echoes it, and Starlette's renderer cannot write a number that is
    not finite.
(g) H-34: free-form JSON. A position whose type is ``Any``, ``object`` or ``JsonValue``, alone or among the members of
    a union, takes any JSON value, a number that is not finite among them, and declares no float (d) could judge: a
    *free-form position*. The walk of (a) notes every one a request reaches, by owner, named as a leaf is (``{*}`` the
    values of a mapping), with the routes that reach it; what it does for the float leaves does not change. The set is
    exactly ``KNOWN_FREE_FORM``: a new one fails until it is added there with its probe, and one no request reaches any
    more fails until it is removed. The five of today: ``FAProviderAssignmentItem.provider_params{*}`` (``Any``,
    ``POST /api/v1/assets/provider``), ``FAProviderProbeRequest.provider_params{*}`` (``Any``,
    ``POST /api/v1/assets/provider/probe``), ``RiskAnalyticRequest.parameters{*}`` (``JsonValue``,
    ``POST /api/v1/risk/query``), ``SignalRequest.params{*}`` (``JsonValue``, ``POST /api/v1/assets/prices/query``,
    ``/fx/currencies/convert`` and ``/signals/preview``) and ``ToolComputeItem.parameters`` (``JsonValue``,
    ``POST /api/v1/tools/compute``). Each refuses a number that is not finite anywhere inside: ``inf``, ``-inf`` and
    ``nan`` at the top of the mapping, in a list, in a nested mapping, in a mapping inside a list. The probe of a
    position is the request model that holds it, validated in Python mode as FastAPI validates a parsed body, with the
    mapping in the field of the position (the position itself for ``ToolComputeItem.parameters``, its values for the
    others); the refusal is a ``ValidationError`` none of whose messages carries the number, since a 422 passes on the
    message of each error (without its ``input``). Here a validator of the field counts, unlike (b): a free-form
    position holds no float whose schema could refuse. The same body around a finite number is accepted: the barrier
    that the probe body is otherwise valid, so that a refusal is the number's doing. The provider probes name
    ``mockprov``, whose ``validate_params`` takes any parameters, and which must be registered: an unknown provider is
    refused whatever its parameters. Today ``ToolComputeItem`` refuses (``allow_inf_nan=False`` in the config of
    ``ToolTransportModel``, which ``JsonValue`` respects), and so does ``SignalRequest`` (``ensure_json_safe`` in a
    validator of ``params``); the two provider requests (``FAProviderConfigBase``) and ``RiskAnalyticRequest`` take
    every placement, and are red. Self-test, on an app of its own: ``Any``, ``object`` and ``JsonValue`` as a field, a
    list item behind ``Annotated``, a mapping value and behind ``Optional``, each noted with its type and its route,
    and the float beside them a leaf, not a free-form position.

How to fix a red: make the float itself refuse them. ``Annotated[float, AllowInfNan(False)]`` (pydantic's
``FiniteFloat``) on the float, or on the float branch of its union; or bounds that exclude both, a lower and an upper one
(``ge=0`` alone lets ``inf`` through); or ``allow_inf_nan=False`` in the config of a model only requests use, never in
``StrictModel``. For ``PluginSettingPlainValue``: ``str | int | Annotated[float, AllowInfNan(False)] | bool``, the
probe's ``FixedValueBody``. A new leaf needs no change here: the walk finds it, and it is parametrised on its own.
For a free-form position (g): ``ensure_json_safe`` (``backend/app/utils/json_utils.py``) in a ``mode="before"``
validator of its field, as ``SignalRequest.params`` has, which refuses a number that is not finite anywhere inside and
names its path, never its value; or ``allow_inf_nan=False`` in the config of a model only requests use, which
``JsonValue`` respects and ``Any`` does not. A new free-form position goes into ``KNOWN_FREE_FORM`` with its probe.

The app of ``backend/app/main.py`` is imported, as ``test_static_route_confinement.py`` imports it, and only read: no
request reaches it, its lifespan never runs. The probe apps are built in this process; the one of (f) is called through
``httpx.ASGITransport``. The request models of (g) are validated in this process; the provider ones look ``mockprov`` up
in the asset provider registry, which imports the provider plugins from their folders. No DB, no server, no network.
"""

import functools
import json
import math
import warnings
from collections import Counter, OrderedDict, defaultdict, deque
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, MutableMapping, MutableSequence, MutableSet, Sequence, Set
from dataclasses import dataclass, is_dataclass
from types import UnionType
from typing import Annotated, Any, ForwardRef, Literal, NewType, Self, TypeAliasType, TypeVar, Union, get_args, get_origin

import httpx
import pytest
import typing_extensions
from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute, iter_route_contexts
from pydantic import AllowInfNan, BaseModel, ConfigDict, Field, JsonValue, TypeAdapter, ValidationError
from pydantic.warnings import UnsupportedFieldAttributeWarning
from starlette.requests import Request

import backend.app.main as app_main
from backend.app.config import API_V1_PREFIX
from backend.app.schemas.provider import FAProviderAssignmentItem, FAProviderProbeRequest
from backend.app.schemas.risk import RiskAnalyticRequest
from backend.app.schemas.signals import SignalRequest
from backend.app.schemas.tools import ToolComputeItem
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.test_scripts.test_utils import print_section, print_success

#: (b): what the edge can hand to a float, by name: the three floats that are not finite, which Python's json also reads
#: from the tokens Infinity, -Infinity and NaN, and a literal too large for a double, which it reads as inf.
PROBES: dict[str, float] = {"inf": math.inf, "-inf": -math.inf, "nan": math.nan, "1E+400": json.loads("1E+400")}
#: (b): all four: what a float without any guard lets through.
EVERYTHING = tuple(PROBES)

#: (a): where FastAPI reads a parameter, as a Dependant names its lists (``<where>_params``).
PARAMETER_KINDS = ("path", "query", "header", "cookie", "body")
#: (a): the containers whose every item pydantic validates against one type: the walk reads it at ``[*]``.
ITEM_CONTAINERS = (list, set, frozenset, deque, Collection, Iterable, MutableSequence, MutableSet, Sequence, Set)
#: (a): the mappings: the walk reads their keys at ``{key}`` and their values at ``{*}``.
MAPPINGS = (dict, defaultdict, OrderedDict, Counter, Mapping, MutableMapping)
#: (a): what ``get_origin`` gives for a union: ``Union[X, Y]`` and ``Optional[X]``, or ``X | Y``.
UNIONS = (Union, UnionType)
#: (a): a PEP 695 alias (``type X = ...``), and the class typing_extensions gives ``TypeAliasType("X", ...)``, as for
#: pydantic's own ``JsonValue``.
TYPE_ALIASES = (TypeAliasType, typing_extensions.TypeAliasType)
#: (g): the types that take any JSON value without saying what it is: a position whose type is one of them, alone or among
#: the members of a union, is a free-form position.
FREE_FORM_TYPES = (Any, object, JsonValue)

#: (c): what the walk must see on the real app (177 API routes, 67 with a body, when this guard was written): fewer means
#: it no longer sees the app, and the rule would pass on nothing.
MIN_API_ROUTES = 150
MIN_API_ROUTES_WITH_BODY = 60

SIGNALS = "backend.app.schemas.signals"
#: (c): the float fields of the signal annotation requests, FiniteFloat each, and the routes whose bodies carry them.
SIGNAL_LEAVES = (
    f"{SIGNALS}.SignalLineCrossoverRequest.epsilon",
    f"{SIGNALS}.SignalLineCrossoverRequest.relative_epsilon",
    f"{SIGNALS}.SignalThresholdCrossingRequest.epsilon",
    f"{SIGNALS}.SignalThresholdCrossingRequest.relative_epsilon",
    f"{SIGNALS}.SignalThresholdCrossingRequest.threshold",
)
SIGNAL_ROUTES = (f"POST {API_V1_PREFIX}/assets/prices/query", f"POST {API_V1_PREFIX}/fx/currencies/convert")
#: (d): the float of a plugin settings write, open when this guard was written, and its route.
PLUGIN_SETTING_VALUE = "backend.app.schemas.plugin_settings.PluginSettingWriteItem.value"
PLUGIN_SETTINGS_ROUTE = f"PATCH {API_V1_PREFIX}/settings/plugins/bulk"
#: (d): the float leaves a request reached when this guard was written: the floor of the parametrisation.
KNOWN_LEAVES = (*SIGNAL_LEAVES, PLUGIN_SETTING_VALUE)
#: (d): how to fix a red, in its message.
FIX = (
    "A float a request reaches refuses inf, -inf, nan and 1E+400 in its schema: Annotated[float, AllowInfNan(False)] "
    "(pydantic's FiniteFloat) on the float, or on the float branch of its union; or bounds that exclude both, a lower and "
    "an upper one (ge=0 alone lets inf through); or allow_inf_nan=False in the config of a model only requests use, never "
    "in StrictModel. A validator, or a check in the service, does not count: the rule is the schema."
)

#: (e), (f): where the probe app mounts its router.
PROBE_PREFIX = f"{API_V1_PREFIX}/probe"


# =============================================================================
# (a) THE WALK, (b) THE JUDGE
# =============================================================================


@dataclass(frozen=True)
class FloatLeaf:
    """A place where a request can carry a float, and what its schema lets through there."""

    owner: str  # module.Model.field, or "param <name> (<where>) of <module.function>"; then the position inside, if any
    label: str  # the same without the modules: Model.field, "param <name> (<where>) of <function>"; the test id
    annotation: str  # what is judged: the annotation, the metadata of its field, its model's allow_inf_nan when set
    accepted: tuple[str, ...]  # the names of the PROBES the schema lets through, in their order; () refuses all four
    failure: str | None  # why the leaf could not be judged; None when it was
    routes: tuple[str, ...]  # "METHOD /path" of every route whose request reaches it, sorted

    def __str__(self) -> str:
        through = ", ".join(self.accepted) or "none of the four"
        return f"{self.owner} ({self.annotation}) lets {through} through; reached by {', '.join(self.routes)}"


@dataclass(frozen=True)
class FreeFormPosition:
    """(g) A place where a request can carry any JSON value, a number that is not finite among them."""

    owner: str  # named as a leaf is: module.Model.field, or a parameter; then the position inside, if any
    label: str  # the same without the modules: Model.field{*}; the test id
    annotation: str  # the free-form type found there: Any, object or JsonValue
    routes: tuple[str, ...]  # "METHOD /path" of every route whose request reaches it, sorted

    def __str__(self) -> str:
        return f"{self.owner} ({self.annotation}; reached by {', '.join(self.routes)})"


@dataclass(frozen=True)
class RequestFloats:
    """What the walk of an app found."""

    leaves: dict[str, FloatLeaf]  # by owner
    routes: tuple[str, ...]  # every API route context walked, as "METHOD /path"
    routes_with_body: tuple[str, ...]  # those whose request has a body
    problems: tuple[str, ...]  # what the walk could not read or judge, in the order met (b)
    free_form: dict[str, FreeFormPosition]  # the free-form positions, by owner (g)

    def labelled(self, label: str) -> FloatLeaf | None:
        """The leaf whose label is ``label``; None when the walk found none."""
        return next((leaf for leaf in self.leaves.values() if leaf.label == label), None)


@dataclass(frozen=True)
class _Owner:
    """Who holds a position: its full name and its label, each followed by the position inside it; and the type aliases
    open around the position, so that a recursive alias is walked down once."""

    full: str
    label: str
    aliases: tuple[Any, ...] = ()

    def at(self, position: str) -> Self:
        return type(self)(self.full + position, self.label + position, self.aliases)

    def within(self, aliases: Sequence[Any]) -> Self:
        return type(self)(self.full, self.label, (*self.aliases, *aliases))


def _under_api_v1(path: str) -> bool:
    return path == API_V1_PREFIX or path.startswith(f"{API_V1_PREFIX}/")


def _path_of(context: Any) -> str | None:
    """The full path a route context serves, read as ``test_instance_block.py`` reads it: an included plain route,
    WebSocket or mount is served by the Starlette route FastAPI builds for it (``starlette_route``), whose path carries
    the prefixes; any other context carries its own."""
    starlette_route = getattr(context, "starlette_route", None)
    return getattr(starlette_route, "path", None) if starlette_route is not None else context.path


def _route_key(context: Any) -> str:
    """A route as a request names it: ``PATCH /api/v1/settings/plugins/bulk``."""
    return f"{','.join(sorted(context.methods or ()))} {_path_of(context)}"


def _path_in(route: str) -> str:
    return route.partition(" ")[2]


def _text(annotation: Any) -> str:
    """An annotation as one writes it: ``float``, ``str | int | float | bool | None``, ``Annotated[float, Ge(ge=0)]``."""
    if isinstance(annotation, type) and not get_args(annotation):
        return annotation.__qualname__
    return repr(annotation).replace("typing.", "")


def _judged(annotation: Any, metadata: tuple[Any, ...]) -> Any:
    """What a leaf is judged on: its annotation, with the metadata of its field or parameter at the top level."""
    return Annotated[(annotation, *metadata)] if metadata else annotation


def _is_float(member: Any) -> bool:
    """``float`` or a subclass of it; never a generic alias, which ``issubclass`` refuses."""
    return get_origin(member) is None and isinstance(member, type) and issubclass(member, float)


def _is_named_tuple(member: type) -> bool:
    return issubclass(member, tuple) and hasattr(member, "_fields")


def _opened(annotation: Any) -> tuple[Any, ...] | None:
    """The members a position holds when its annotation stands for others, as pydantic reads it: the type of an
    ``Annotated``, the value of a type alias, the arguments of a union, the supertype of a ``NewType``, the constraints or
    the bound of a type variable. None for any other annotation, which is a member itself."""
    if get_origin(annotation) is Annotated:
        return get_args(annotation)[:1]
    if isinstance(annotation, TYPE_ALIASES):
        return (annotation.__value__,)
    if get_origin(annotation) in UNIONS:
        return get_args(annotation)
    if isinstance(annotation, NewType):
        return (annotation.__supertype__,)
    if isinstance(annotation, TypeVar):
        return tuple(filter(None, (*annotation.__constraints__, annotation.__bound__)))
    return None


def _positions_inside(origin: Any, member: Any) -> list[tuple[str, Any]] | None:
    """The positions inside a generic, each with its type: ``[*]`` the items of a sequence or a set, ``[0]``, ``[1]``...
    the slots of a tuple (``[*]`` those of ``tuple[X, ...]``), ``{key}`` and ``{*}`` the keys and the values of a mapping.
    None for a generic the walk cannot open."""
    arguments = get_args(member)
    if origin in ITEM_CONTAINERS:
        return [("[*]", argument) for argument in arguments[:1]]
    if origin is tuple and arguments[1:] == (Ellipsis,):
        return [("[*]", arguments[0])]
    if origin is tuple:
        return [(f"[{index}]", argument) for index, argument in enumerate(arguments)]
    if origin in MAPPINGS:
        return list(zip(("{key}", "{*}"), arguments, strict=False))
    return None


def judge(annotation: Any, metadata: tuple[Any, ...] = (), allow_inf_nan: bool | None = None) -> tuple[str, ...]:
    """(b) The names of the PROBES the schema of a leaf lets through; ``()`` when it refuses all four. Raises what building
    the adapter raises, and what a probe raises that is not a ``ValidationError``."""
    config = ConfigDict(allow_inf_nan=allow_inf_nan) if allow_inf_nan is not None else None
    with warnings.catch_warnings():
        # A Field() in the Annotated of an item may carry attributes an adapter does not use: FastAPI's ModelField
        # silences the same warning when it builds its own adapters.
        warnings.simplefilter("ignore", UnsupportedFieldAttributeWarning)
        adapter = TypeAdapter(_judged(annotation, metadata), config=config)
    return tuple(name for name, value in PROBES.items() if _lets_through(adapter, value))


def _lets_through(adapter: TypeAdapter[Any], value: float) -> bool:
    try:
        adapter.validate_python(value)
    except ValidationError:
        return False
    return True


class _Walk:
    """One walk of an app: the leaves found, each judged once, the free-form positions (g), the routes that reach each,
    the problems met."""

    def __init__(self) -> None:
        self.judged: dict[str, tuple[str, str, tuple[str, ...], str | None]] = {}  # owner: (label, annotation, accepted, failure)
        self.free_form: dict[str, tuple[str, dict[str, None]]] = {}  # owner: (label, the free-form types met there, each once)
        self.reached: dict[str, set[str]] = {}  # owner: the routes that reach it, a leaf or a free-form position
        self.problems: dict[str, None] = {}  # each once, in the order met
        self.route = ""  # the route being walked
        self.models: set[type[BaseModel]] = set()  # the models it has reached so far

    def request_of(self, route: str, dependant: Any) -> bool:
        """Walk the request of one route; whether it has a body."""
        self.route, self.models = route, set()
        return self._dependant(dependant, set())

    def result(self, routes: tuple[str, ...], routes_with_body: tuple[str, ...]) -> RequestFloats:
        leaves = {owner: FloatLeaf(owner, label, annotation, accepted, failure, tuple(sorted(self.reached[owner]))) for owner, (label, annotation, accepted, failure) in self.judged.items()}
        free_form = {owner: FreeFormPosition(owner, label, " | ".join(types), tuple(sorted(self.reached[owner]))) for owner, (label, types) in self.free_form.items()}
        return RequestFloats(leaves, routes, routes_with_body, tuple(self.problems), free_form)

    def _dependant(self, dependant: Any, seen: set[int]) -> bool:
        """The parameters of a dependant and of its sub-dependants; whether any of them reads the body."""
        if id(dependant) in seen:
            return False
        seen.add(id(dependant))
        for where in PARAMETER_KINDS:
            for parameter in getattr(dependant, f"{where}_params"):
                self._parameter(parameter, where, dependant.call)
        with_body = bool(dependant.body_params)
        for sub_dependant in dependant.dependencies:
            with_body = self._dependant(sub_dependant, seen) or with_body
        return with_body

    def _parameter(self, parameter: Any, where: str, call: Any) -> None:
        """A parameter of the path, the query, a header, a cookie or the body, owned by the function that declares it."""
        name = f"param {parameter.name} ({where}) of"
        function = f"{getattr(call, '__module__', '?')}.{getattr(call, '__qualname__', repr(call))}"
        owner = _Owner(f"{name} {function}", f"{name} {getattr(call, '__name__', repr(call))}")
        config = getattr(parameter, "config", None) or {}
        self._position(parameter.field_info.annotation, tuple(parameter.field_info.metadata), owner, config.get("allow_inf_nan"))

    def _model(self, model: type[BaseModel]) -> None:
        """The fields of a model, each with its metadata and the model's own allow_inf_nan; once per route."""
        if model in self.models:
            return
        self.models.add(model)
        allow_inf_nan = model.model_config.get("allow_inf_nan")
        for name, info in model.model_fields.items():
            owner = _Owner(f"{model.__module__}.{model.__qualname__}.{name}", f"{model.__qualname__}.{name}")
            self._position(info.annotation, tuple(info.metadata), owner, allow_inf_nan)

    def _position(self, annotation: Any, metadata: tuple[Any, ...], owner: _Owner, allow_inf_nan: bool | None) -> None:
        """One position: a leaf when a float is among its members; then what lies inside each member, unless the position
        opens again a type alias open around it: a recursive alias is walked down once."""
        opened: list[Any] = []
        members = list(self._members(annotation, owner, opened))
        if any(_is_float(member) for member in members):
            self._leaf(annotation, metadata, owner, allow_inf_nan)
        if any(alias is around for alias in opened for around in owner.aliases):
            return
        inner = owner.within(opened)
        for member in members:
            self._inside(member, inner, allow_inf_nan)

    def _members(self, annotation: Any, owner: _Owner, opened: list[Any]) -> Iterator[Any]:
        """What a value at this position may be; the type aliases it opens go to ``opened``, each once. ``Any``, ``object``
        and ``JsonValue`` make it a free-form position (g), and only that: nothing else changes for the leaves.
        ``JsonValue`` is out of scope for them (a); a forward reference is a problem."""
        if any(annotation is free_form for free_form in FREE_FORM_TYPES):
            self._free_form(annotation, owner)
        if annotation is JsonValue or any(annotation is alias for alias in opened):
            return
        if isinstance(annotation, str | ForwardRef):
            self._problem(owner, f"{annotation!r} is a forward reference nobody resolved")
            return
        if isinstance(annotation, TYPE_ALIASES):
            opened.append(annotation)
        members = _opened(annotation)
        if members is None:
            yield annotation
            return
        for member in members:
            yield from self._members(member, owner, opened)

    def _inside(self, member: Any, owner: _Owner, allow_inf_nan: bool | None) -> None:
        """The positions inside a generic member, or the fields of a model."""
        origin = get_origin(member)
        if origin is None:
            self._class(member, owner)
            return
        if origin is Literal or origin is type:
            return
        positions = _positions_inside(origin, member)
        if positions is None:
            self._problem(owner, f"{_text(member)} is a generic the walk cannot open: teach it how pydantic reads it")
            return
        for position, argument in positions:
            self._position(argument, (), owner.at(position), allow_inf_nan)

    def _class(self, member: Any, owner: _Owner) -> None:
        """A model is walked; a dataclass, a TypedDict or a NamedTuple is a problem; any other class holds no position."""
        if not isinstance(member, type):
            return
        if issubclass(member, BaseModel):
            self._model(member)
        elif is_dataclass(member) or typing_extensions.is_typeddict(member) or _is_named_tuple(member):
            self._problem(owner, f"{_text(member)} is a dataclass, a TypedDict or a NamedTuple: pydantic validates its fields, which the walk does not read")

    def _leaf(self, annotation: Any, metadata: tuple[Any, ...], owner: _Owner, allow_inf_nan: bool | None) -> None:
        """A float leaf, judged the first time a route reaches it."""
        self.reached.setdefault(owner.full, set()).add(self.route)
        if owner.full in self.judged:
            return
        text = _text(_judged(annotation, metadata)) + ("" if allow_inf_nan is None else f", allow_inf_nan={allow_inf_nan} in its model's config")
        try:
            accepted, failure = judge(annotation, metadata, allow_inf_nan), None
        except Exception as error:
            accepted, failure = (), f"{type(error).__name__}: {error}"
            self._problem(owner, f"cannot be judged ({text}): {failure}")
        self.judged[owner.full] = (owner.label, text, accepted, failure)

    def _free_form(self, annotation: Any, owner: _Owner) -> None:
        """A free-form position (g), noted with the routes that reach it and each free-form type it holds."""
        self.reached.setdefault(owner.full, set()).add(self.route)
        self.free_form.setdefault(owner.full, (owner.label, {}))[1][_text(annotation)] = None

    def _problem(self, owner: _Owner, what: str) -> None:
        self.problems[f"{owner.full}: {what}"] = None


def collect_request_floats(routes: Sequence[Any]) -> RequestFloats:
    """(a), (b) Every float leaf the requests of ``routes``, the routes of an app, reach: each judged, with the routes that
    reach it; (g) every free-form position they reach, with its routes; and what the walk could not read."""
    walk = _Walk()
    walked: list[str] = []
    with_body: list[str] = []
    for context in iter_route_contexts(routes):
        if not isinstance(context.original_route, APIRoute):
            continue
        route = _route_key(context)
        walked.append(route)
        if walk.request_of(route, context.dependant):
            with_body.append(route)
    return walk.result(tuple(walked), tuple(with_body))


@functools.cache
def real_walk() -> RequestFloats:
    """The walk of the app of ``backend/app/main.py``, once per process."""
    return collect_request_floats(app_main.app.routes)


def _labels_at_collection() -> dict[str, str]:
    """The labels of the app's leaves, by owner, when this file is collected. Empty when the walk fails: the barriers walk
    again, and fail with its error."""
    try:
        leaves = real_walk().leaves
    except Exception:
        return {}
    return {owner: leaf.label for owner, leaf in leaves.items()}


_LABELS = _labels_at_collection()
#: (d): every float leaf the walk finds, and the floor; the id of each case is the leaf's label (Model.field).
LEAF_OWNERS = sorted(set(_LABELS) | set(KNOWN_LEAVES))
LEAF_IDS = [_LABELS.get(owner, ".".join(owner.split(".")[-2:])) for owner in LEAF_OWNERS]


# =============================================================================
# THE PROBE APP (e), (f)
# =============================================================================


class PlainBody(BaseModel):
    """A plain float: all four get through."""

    x: float


class FiniteBody(BaseModel):
    """``FiniteFloat``, the fix: none gets through."""

    x: Annotated[float, AllowInfNan(False)]


class BoundedBody(BaseModel):
    """A lower and an upper bound: ``inf`` fails the upper, ``-inf`` and ``nan`` the lower."""

    x: float = Field(..., ge=0, le=10)


class LowerBoundBody(BaseModel):
    """A lower bound alone: ``nan`` and ``-inf`` fail it, ``inf`` passes."""

    x: float = Field(..., ge=0)


class NestedItem(BaseModel):
    """A model the body reaches only inside a list."""

    y: float


class NestingBody(BaseModel):
    items: list[NestedItem]


class ConfiguredBody(BaseModel):
    """A model whose config refuses ``inf`` and ``nan`` for all its floats: a field, and the items of a list."""

    model_config = ConfigDict(allow_inf_nan=False)

    x: float
    series: list[float]


class PlainValueBody(BaseModel):
    """The union of ``PluginSettingPlainValue``, and ``None``: a float takes the float branch."""

    value: str | int | float | bool | None = None


class FixedValueBody(BaseModel):
    """The same union with a float that refuses them: the fix proposed for ``PluginSettingPlainValue``."""

    value: str | int | Annotated[float, AllowInfNan(False)] | bool | None = None


class ContainersBody(BaseModel):
    """Floats inside containers: a dict value (its key a str), a tuple slot (the other one a str), a list of lists."""

    by_key: dict[str, float]
    pair: tuple[str, float]
    grid: list[list[float]]


type Ratio = float


class AliasBody(BaseModel):
    """A float behind a PEP 695 alias, as the PAC requests name their types."""

    ratio: Ratio


type Tree = float | list[Tree]


class TreeBody(BaseModel):
    """A recursive alias: a float, or a list of the same. The walk goes down it once: the field and its items."""

    tree: Tree


class JsonBody(BaseModel):
    """Any JSON value: out of scope (a), so no leaf."""

    params: dict[str, JsonValue]


class DirectBody(BaseModel):
    """The body of a route of the app itself, outside any router."""

    x: float


async def refusal_without_input(request: Request, error: RequestValidationError) -> JSONResponse:
    """The 422 of the probe app: each error without the ``input`` FastAPI's own handler echoes, which Starlette's renderer
    cannot write when it is a number that is not finite (``allow_nan=False``)."""
    return JSONResponse({"detail": [{"type": detail["type"], "loc": list(detail["loc"])} for detail in error.errors()]}, status_code=422)


def probe_app() -> FastAPI:
    """The app of the self-tests: its routes in a router included under ``PROBE_PREFIX``, one in a router nested in it,
    one on the app itself."""
    router = APIRouter()
    nested = APIRouter(prefix="/nested")

    @router.post("/plain")
    async def plain(body: PlainBody) -> dict[str, bool]:
        return {"finite": math.isfinite(body.x)}

    @router.post("/finite")
    async def finite(body: FiniteBody) -> dict[str, bool]:
        return {"finite": math.isfinite(body.x)}

    @router.post("/shapes")
    async def shapes(bounded: BoundedBody, lower: LowerBoundBody, nesting: NestingBody, configured: ConfiguredBody, plain_value: PlainValueBody, fixed_value: FixedValueBody, containers: ContainersBody, alias: AliasBody, tree: TreeBody, json_value: JsonBody) -> dict[str, bool]:
        return {"received": True}

    @nested.get("/ratio")
    async def read_ratio(ratio: float) -> dict[str, bool]:
        return {"finite": math.isfinite(ratio)}

    router.include_router(nested)
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None, exception_handlers={RequestValidationError: refusal_without_input})
    app.include_router(router, prefix=PROBE_PREFIX)

    @app.post(f"{API_V1_PREFIX}/direct")
    async def direct(body: DirectBody) -> dict[str, bool]:
        return {"finite": math.isfinite(body.x)}

    return app


SHAPES_ROUTE = f"POST {PROBE_PREFIX}/shapes"
#: (e): every route of the probe app, and whether its request has a body.
PROBE_ROUTES = {f"POST {PROBE_PREFIX}/plain": True, f"POST {PROBE_PREFIX}/finite": True, SHAPES_ROUTE: True, f"GET {PROBE_PREFIX}/nested/ratio": False, f"POST {API_V1_PREFIX}/direct": True}
#: (e): each float of the probe app, by test id: the label of its leaf, what its schema lets through, the route reaching it.
PROBE_CASES: dict[str, tuple[str, tuple[str, ...], str]] = {
    "plain-float": ("PlainBody.x", EVERYTHING, f"POST {PROBE_PREFIX}/plain"),
    "allow-inf-nan-false": ("FiniteBody.x", (), f"POST {PROBE_PREFIX}/finite"),
    "bounds-ge-and-le": ("BoundedBody.x", (), SHAPES_ROUTE),
    "lower-bound-alone": ("LowerBoundBody.x", ("inf", "1E+400"), SHAPES_ROUTE),
    "model-inside-a-list": ("NestedItem.y", EVERYTHING, SHAPES_ROUTE),
    "model-config-allow-inf-nan-false": ("ConfiguredBody.x", (), SHAPES_ROUTE),
    "model-config-on-a-list-item": ("ConfiguredBody.series[*]", (), SHAPES_ROUTE),
    "union-of-plugin-setting-values": ("PlainValueBody.value", EVERYTHING, SHAPES_ROUTE),
    "union-with-a-finite-float": ("FixedValueBody.value", (), SHAPES_ROUTE),
    "dict-value": ("ContainersBody.by_key{*}", EVERYTHING, SHAPES_ROUTE),
    "tuple-slot": ("ContainersBody.pair[1]", EVERYTHING, SHAPES_ROUTE),
    "list-of-lists": ("ContainersBody.grid[*][*]", EVERYTHING, SHAPES_ROUTE),
    "pep-695-alias": ("AliasBody.ratio", EVERYTHING, SHAPES_ROUTE),
    "recursive-alias": ("TreeBody.tree", EVERYTHING, SHAPES_ROUTE),
    "recursive-alias-walked-down-once": ("TreeBody.tree[*]", EVERYTHING, SHAPES_ROUTE),
    "query-parameter-of-a-nested-router": ("param ratio (query) of read_ratio", EVERYTHING, f"GET {PROBE_PREFIX}/nested/ratio"),
    "route-of-the-app-itself": ("DirectBody.x", EVERYTHING, f"POST {API_V1_PREFIX}/direct"),
}


@dataclass
class Point:
    """A stdlib dataclass in a body: pydantic validates its fields; the walk does not read them."""

    x: float


class PointBody(BaseModel):
    point: Point


#: (f): a body as a client may write it, its number not finite once Python's json reads it.
RAW_BODIES = {"1E+400": b'{"x": 1E+400}', "NaN": b'{"x": NaN}', "Infinity": b'{"x": Infinity}', "-Infinity": b'{"x": -Infinity}'}
JSON_HEADERS = {"content-type": "application/json"}


class FreeFormBody(BaseModel):
    """(g) Free-form JSON in each shape the walk opens: a field, a list item behind ``Annotated``, a mapping value, behind
    ``Optional``; and a float beside them, which stays a leaf."""

    anything: Any
    notes: list[Annotated[object, "a note"]]
    settings: dict[str, Any] | None = None
    payload: JsonValue
    maybe: Union[JsonValue, None] = None
    ratio: float


#: (g): the free-form positions of FreeFormBody, by label, each with its free-form type.
FREE_FORM_PROBE_POSITIONS = {"FreeFormBody.anything": "Any", "FreeFormBody.notes[*]": "object", "FreeFormBody.settings{*}": "Any", "FreeFormBody.payload": "JsonValue", "FreeFormBody.maybe": "JsonValue"}


# =============================================================================
# (g) FREE-FORM JSON: THE PROBES
# =============================================================================

#: (g): the asset provider the provider probes name. Its ``validate_params`` takes any parameters, so the plugin refuses
#: none of the placements and the request model decides alone; the registry discovers it from its folder in every mode
#: (``test_only`` only keeps it out of the users' lists).
PROBE_PROVIDER = "mockprov"


def _provider_config(value: JsonValue) -> dict[str, JsonValue]:
    """The body of a provider configuration (``FAProviderConfigBase``) with ``value`` as its ``provider_params``. A
    barrier: ``PROBE_PROVIDER`` must be registered, since an unknown provider is refused whatever its parameters, and that
    refusal would not be the number's doing."""
    codes = AssetProviderRegistry.list_plugin_codes()
    assert PROBE_PROVIDER in codes, f"barrier: the probe provider {PROBE_PROVIDER} is not registered ({codes}): every provider probe would be refused as an unknown provider, whatever its parameters"
    return {"provider_code": PROBE_PROVIDER, "identifier": "X", "identifier_type": "TICKER", "provider_params": value}


def probe_provider_assignment(value: JsonValue) -> BaseModel:
    """``POST /api/v1/assets/provider``: one assignment of its list."""
    return FAProviderAssignmentItem.model_validate({"asset_id": 1, **_provider_config(value)})


def probe_provider_probe(value: JsonValue) -> BaseModel:
    """``POST /api/v1/assets/provider/probe``: the configuration to probe, and one operation."""
    return FAProviderProbeRequest.model_validate({**_provider_config(value), "operations": ["current_price"]})


def probe_risk_analytic(value: JsonValue) -> BaseModel:
    """``POST /api/v1/risk/query``: one analytic of its list."""
    return RiskAnalyticRequest.model_validate({"instance_id": "a1", "analytic_code": "volatility", "parameters": value})


def probe_signal_request(value: JsonValue) -> BaseModel:
    """``POST /api/v1/assets/prices/query``, ``/fx/currencies/convert`` and ``/signals/preview``: a signal of a list."""
    return SignalRequest.model_validate({"instance_id": "s1", "signal_code": "EMA", "params": value})


def probe_tool_compute_item(value: JsonValue) -> BaseModel:
    """``POST /api/v1/tools/compute``: one item of its batch, every field strict (``ToolTransportModel``)."""
    return ToolComputeItem.model_validate({"correlation_id": "c1", "tool_code": "probe_tool", "contract_version": "1.0.0", "implementation_version": "1.0.0", "schema_fingerprint": "0" * 64, "parameters": value})


#: (g): the free-form positions a request reached when this guard was written, by owner, each with its probe: the request
#: model that holds the position, validated in Python mode around a mapping placed in the field of the position.
KNOWN_FREE_FORM: dict[str, Callable[[JsonValue], BaseModel]] = {
    "backend.app.schemas.provider.FAProviderAssignmentItem.provider_params{*}": probe_provider_assignment,
    "backend.app.schemas.provider.FAProviderProbeRequest.provider_params{*}": probe_provider_probe,
    "backend.app.schemas.risk.RiskAnalyticRequest.parameters{*}": probe_risk_analytic,
    "backend.app.schemas.signals.SignalRequest.params{*}": probe_signal_request,
    "backend.app.schemas.tools.ToolComputeItem.parameters": probe_tool_compute_item,
}
#: (g): where a probe puts a number that is not finite, by name: the number, and the mapping around it, which the probe
#: places in the field of the position. Wherever it lies, the number is inside a free-form position: within a value of the
#: mapping (``{*}``), or within the mapping itself (``ToolComputeItem.parameters``).
PLACEMENTS: dict[str, tuple[float, Callable[[float], dict[str, JsonValue]]]] = {
    "inf-at-the-top": (math.inf, lambda number: {"top": number}),
    "minus-inf-at-the-top": (-math.inf, lambda number: {"top": number}),
    "nan-at-the-top": (math.nan, lambda number: {"top": number}),
    "inf-in-a-list": (math.inf, lambda number: {"deep": [1, number]}),
    "nan-in-a-nested-mapping": (math.nan, lambda number: {"deep": {"x": number}}),
    "minus-inf-in-a-mapping-in-a-list": (-math.inf, lambda number: {"deep": [1, {"x": number}]}),
}
#: (g): the number of the barrier: each mapping of PLACEMENTS around it is a body every probe accepts.
FINITE = 2.5
#: (g): every known free-form position with every placement; the id of a case is the label of the position
#: (Model.field{*}) and the name of the placement.
FREE_FORM_LABELS = {owner: ".".join(owner.split(".")[-2:]) for owner in KNOWN_FREE_FORM}
FREE_FORM_CASES = [(owner, placement) for owner in KNOWN_FREE_FORM for placement in PLACEMENTS]
FREE_FORM_IDS = [f"{FREE_FORM_LABELS[owner]}-{placement}" for owner, placement in FREE_FORM_CASES]
#: (g): how to fix a red of a free-form position, in its message.
FREE_FORM_FIX = (
    "A free-form position a request reaches refuses a number that is not finite anywhere inside: ensure_json_safe "
    "(backend/app/utils/json_utils.py) in a mode='before' field_validator of its field, as SignalRequest.params has, which "
    "names the path and never the value; or allow_inf_nan=False in the config of a model only requests use, which "
    "JsonValue respects and Any does not."
)
#: (g): what to do when the free-form positions a request reaches are not KNOWN_FREE_FORM, in its message.
FREE_FORM_DRIFT = (
    "A new one goes into KNOWN_FREE_FORM with its probe, the request model that holds it, and refuses a number that is "
    "not finite anywhere inside (FREE_FORM_FIX). One no request reaches any more leaves KNOWN_FREE_FORM: the walk lost it "
    "(see the barriers), or its field moved or no longer holds free-form JSON."
)


# =============================================================================
# (c) BARRIERS ON THE REAL APP
# =============================================================================


def test_the_walk_reaches_the_api_routes_of_the_app() -> None:
    """(c) At least 150 API route contexts walked under /api/v1, at least 60 with a body, the routes of today's leaves
    among them: a walk that no longer sees the app would let the rule pass on nothing."""
    print_section("H-32: the routes walked")
    walk = real_walk()

    api = [route for route in walk.routes if _under_api_v1(_path_in(route))]
    with_body = [route for route in walk.routes_with_body if _under_api_v1(_path_in(route))]

    assert len(api) >= MIN_API_ROUTES, f"barrier: the walk reads {len(api)} API route contexts under {API_V1_PREFIX}, fewer than {MIN_API_ROUTES}: it no longer sees the routes of the app (has FastAPI changed how it serves an included router?)"
    assert len(with_body) >= MIN_API_ROUTES_WITH_BODY, f"barrier: {len(with_body)} of them have a body, fewer than {MIN_API_ROUTES_WITH_BODY}: the walk no longer sees the bodies"
    missing = sorted({*SIGNAL_ROUTES, PLUGIN_SETTINGS_ROUTE} - set(with_body))
    assert not missing, f"barrier: the routes of today's float leaves are not among the routes walked with a body: {missing}"
    print_success(f"✓ {len(api)} API routes under {API_V1_PREFIX}, {len(with_body)} with a body")


def test_the_walk_finds_the_float_fields_of_the_signal_requests() -> None:
    """(c) At least one float leaf: the five of the signal annotation requests, each through both routes whose bodies carry
    them. A walk that finds no float would let the rule pass on nothing."""
    print_section("H-32: the floats of the signal annotation requests")
    leaves = real_walk().leaves

    missing = [owner for owner in SIGNAL_LEAVES if owner not in leaves]
    assert not missing, f"barrier: the walk does not find {missing}; it finds {sorted(leaves)}"
    unreached = {owner: sorted(set(SIGNAL_ROUTES) - set(leaves[owner].routes)) for owner in SIGNAL_LEAVES if not set(SIGNAL_ROUTES) <= set(leaves[owner].routes)}
    assert not unreached, f"barrier: these fields are not reached through every route whose body carries them ({{field: routes missing}}): {unreached}"
    print_success(f"✓ {len(SIGNAL_LEAVES)} fields, each through {' and '.join(SIGNAL_ROUTES)}")


def test_the_walk_reads_everything_the_requests_of_the_app_reach() -> None:
    """(b), (c) No problem on the real app: every annotation a request reaches is read, and every float leaf judged."""
    print_section("H-32: nothing the walk cannot read")
    walk = real_walk()

    assert not walk.problems, "the walk met what it cannot read or judge, and skips nothing in silence: teach it, then judge again\n" + "\n".join(f"  {problem}" for problem in walk.problems)
    print_success(f"✓ {len(walk.leaves)} float leaves, each judged")


# =============================================================================
# (d) THE RULE
# =============================================================================


@pytest.mark.parametrize("owner", LEAF_OWNERS, ids=LEAF_IDS)
def test_a_float_a_request_reaches_refuses_inf_and_nan(owner: str) -> None:
    """(d) The schema of the leaf refuses inf, -inf, nan and 1E+400."""
    print_section(f"H-32: {owner}")
    leaf = real_walk().leaves.get(owner)

    assert leaf is not None, f"{owner} is in KNOWN_LEAVES, and no request of the app reaches it any more: the walk lost it (see the barriers), or the field moved or no longer holds a float; update KNOWN_LEAVES with that change"
    assert leaf.failure is None, f"{leaf.owner} cannot be judged ({leaf.annotation}): {leaf.failure}"
    assert not leaf.accepted, f"{leaf}. {FIX}"
    print_success(f"✓ {leaf}")


# =============================================================================
# (e) SELF-TESTS OF THE WALK AND OF THE JUDGE
# =============================================================================


@pytest.fixture(scope="module")
def probe_walk() -> RequestFloats:
    """The walk of the probe app."""
    return collect_request_floats(probe_app().routes)


def test_the_walk_reads_every_route_of_the_probe_app(probe_walk: RequestFloats) -> None:
    """(e) The routes of a router included with a prefix (an ``_IncludedRouter`` in ``app.routes``), the route of a router
    nested in it with both prefixes, the route of the app itself: each walked once, with its full path, with or without
    a body."""
    print_section("H-32 self-test: the routes of the probe app")
    with_body = sorted(route for route, body in PROBE_ROUTES.items() if body)

    assert sorted(probe_walk.routes) == sorted(PROBE_ROUTES), f"the walk must read every route of the probe app, each with its full path: {probe_walk.routes}"
    assert sorted(probe_walk.routes_with_body) == with_body, f"the routes with a body are {with_body}; the walk says {probe_walk.routes_with_body}"
    print_success(f"✓ {len(probe_walk.routes)} routes, {len(probe_walk.routes_with_body)} with a body")


@pytest.mark.parametrize(("label", "accepted", "route"), PROBE_CASES.values(), ids=list(PROBE_CASES))
def test_the_walk_finds_and_judges_each_float_of_the_probe_app(probe_walk: RequestFloats, label: str, accepted: tuple[str, ...], route: str) -> None:
    """(e) Each float of the probe app: found, reached by its route alone, and judged as pydantic validates it."""
    print_section(f"H-32 self-test: {label}")
    leaf = probe_walk.labelled(label)

    assert leaf is not None, f"the walk does not find {label} on the probe app; it finds {sorted(found.label for found in probe_walk.leaves.values())}"
    assert leaf.failure is None, f"{leaf.owner} cannot be judged: {leaf.failure}"
    assert leaf.accepted == accepted, f"{leaf}: expected {', '.join(accepted) or 'none of the four'} through"
    assert leaf.routes == (route,), f"{label} must be reached by {route} alone: {leaf.routes}"
    print_success(f"✓ {leaf}")


def test_nothing_else_is_a_float_leaf_of_the_probe_app(probe_walk: RequestFloats) -> None:
    """(e) The walk finds the floats of the probe app and nothing else: a str key, a str slot and ``JsonValue`` are no
    leaf; and the probe app holds nothing the walk cannot read."""
    print_section("H-32 self-test: nothing else")
    found = sorted(leaf.label for leaf in probe_walk.leaves.values())
    expected = sorted(label for label, _, _ in PROBE_CASES.values())

    assert found == expected, f"the float leaves of the probe app are {expected}; the walk finds {found}"
    assert not probe_walk.problems, f"the probe app holds nothing the walk cannot read: {probe_walk.problems}"
    print_success(f"✓ {len(found)} leaves, no problem")


def test_the_walk_reports_a_dataclass_as_a_problem() -> None:
    """(b), (e) A dataclass in a body is a problem named by the field that holds it, never a pass: its float, which the
    walk does not read, is no leaf."""
    print_section("H-32 self-test: what the walk cannot read")
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

    @app.post(f"{API_V1_PREFIX}/point")
    async def point(body: PointBody) -> dict[str, bool]:
        return {"finite": math.isfinite(body.point.x)}

    walk = collect_request_floats(app.routes)

    assert walk.routes == (f"POST {API_V1_PREFIX}/point",), f"barrier: the walk must read the route of the dataclass: {walk.routes}"
    owner = f"{PointBody.__module__}.PointBody.point"
    assert any(problem.startswith(f"{owner}: ") and "dataclass" in problem for problem in walk.problems), f"a dataclass in a body must be a problem named {owner}: {walk.problems}"
    assert not walk.leaves, f"the float inside the dataclass is not judged, so it must not read as a leaf: {list(walk.leaves)}"
    print_success(f"✓ {walk.problems[0]}")


# =============================================================================
# (f) THE THREAT, END TO END
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("body", RAW_BODIES.values(), ids=list(RAW_BODIES))
async def test_a_number_that_is_not_finite_reaches_a_plain_float_and_never_a_finite_one(body: bytes) -> None:
    """(f) What (e) judges for PlainBody.x and FiniteBody.x is what FastAPI does: the body reaches the endpoint of a plain
    float as a number that is not finite, and never the endpoint of an ``Annotated[float, AllowInfNan(False)]``, refused
    with 422 finite_number."""
    print_section(f"H-32: {body.decode()} at the edge")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=probe_app()), base_url="http://test") as client:
        plain = await client.post(f"{PROBE_PREFIX}/plain", content=body, headers=JSON_HEADERS)
        finite = await client.post(f"{PROBE_PREFIX}/finite", content=body, headers=JSON_HEADERS)

    assert plain.status_code == 200, f"a plain float takes {body.decode()}: {plain.status_code} {plain.text}"
    assert plain.json() == {"finite": False}, f"the endpoint of a plain float must receive a number that is not finite: {plain.text}"
    assert finite.status_code == 422, f"Annotated[float, AllowInfNan(False)] refuses {body.decode()} before its endpoint: {finite.status_code} {finite.text}"
    assert [error["type"] for error in finite.json()["detail"]] == ["finite_number"], f"the refusal must be finite_number: {finite.text}"
    print_success(f"✓ {body.decode()}: a plain float lets it in, a finite one answers 422 finite_number")


# =============================================================================
# (g) FREE-FORM JSON
# =============================================================================


def test_the_walk_finds_exactly_the_known_free_form_positions() -> None:
    """(g) The free-form positions the requests of the app reach are exactly KNOWN_FREE_FORM: a new one fails until it is
    added there with its probe, and one no request reaches any more fails until it is removed."""
    print_section("H-34: the free-form positions")
    found = real_walk().free_form

    drift = [f"  new: {found[owner]}" for owner in sorted(set(found) - set(KNOWN_FREE_FORM))]
    drift += [f"  vanished: {owner}" for owner in sorted(set(KNOWN_FREE_FORM) - set(found))]
    assert not drift, "the free-form positions a request reaches are not KNOWN_FREE_FORM:\n" + "\n".join(drift) + f"\n{FREE_FORM_DRIFT}"
    print_success(f"✓ {len(found)} free-form positions, each known: " + "; ".join(str(found[owner]) for owner in sorted(found)))


@pytest.mark.parametrize(("owner", "placement"), FREE_FORM_CASES, ids=FREE_FORM_IDS)
def test_each_free_form_position_refuses_a_non_finite_float_inside(owner: str, placement: str) -> None:
    """(g) The request model of the position refuses a number that is not finite wherever it lies inside the free-form
    value, and none of the messages of its refusal carries the number."""
    print_section(f"H-34: {owner}, {placement}")
    number, around = PLACEMENTS[placement]
    value = around(number)

    try:
        KNOWN_FREE_FORM[owner](value)
    except ValidationError as error:
        refusal = error
    else:
        pytest.fail(f"{owner} takes a number that is not finite ({placement}): {value!r} validates. {FREE_FORM_FIX}")
    messages = [detail["msg"] for detail in refusal.errors(include_input=False)]
    carried = [message for message in messages if repr(number) in message]
    assert not carried, f"the refusal of {owner} carries the number it refuses ({number!r}) in its message, which a 422 passes on: {carried}"
    print_success(f"✓ {owner} refuses {value!r}: {'; '.join(messages)}")


@pytest.mark.parametrize(("owner", "placement"), FREE_FORM_CASES, ids=FREE_FORM_IDS)
def test_each_free_form_probe_body_is_valid_when_finite(owner: str, placement: str) -> None:
    """(g) The barrier: the same body around a finite number is accepted, so that the refusal of a number that is not
    finite is that number's doing, and not that of a body the request model refuses anyway."""
    print_section(f"H-34 barrier: {owner}, {placement}")
    _, around = PLACEMENTS[placement]
    value = around(FINITE)

    try:
        KNOWN_FREE_FORM[owner](value)
    except ValidationError as error:
        pytest.fail(f"barrier: the probe of {owner} refuses a finite body ({placement}): {value!r}. Fix its probe in KNOWN_FREE_FORM until it validates: until then, a refusal of a number that is not finite proves nothing.\n{error}")
    print_success(f"✓ {owner} accepts {value!r}")


def test_the_walk_notes_each_free_form_position_and_nothing_else() -> None:
    """(g) On an app of its own: ``Any``, ``object`` and ``JsonValue`` as a field, a list item behind ``Annotated``, a
    mapping value and behind ``Optional``, each noted by its label with its type, reached by the route alone; the float
    beside them a leaf, not a free-form position; and nothing the walk cannot read."""
    print_section("H-34 self-test: the free-form positions of a probe app")
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

    @app.post(f"{API_V1_PREFIX}/free-form")
    async def receive(body: FreeFormBody) -> dict[str, bool]:
        return {"received": True}

    walk = collect_request_floats(app.routes)
    route = f"POST {API_V1_PREFIX}/free-form"
    found = {position.label: position.annotation for position in walk.free_form.values()}
    unreached = [str(position) for position in walk.free_form.values() if position.routes != (route,)]
    leaves = [leaf.label for leaf in walk.leaves.values()]

    assert walk.routes == (route,), f"barrier: the walk must read the route of the probe: {walk.routes}"
    assert found == FREE_FORM_PROBE_POSITIONS, f"the free-form positions of FreeFormBody are {FREE_FORM_PROBE_POSITIONS}; the walk notes {found}"
    assert not unreached, f"each must be reached by {route} alone: {unreached}"
    assert leaves == ["FreeFormBody.ratio"], f"the float beside them is the one leaf of FreeFormBody, and no free-form position: {leaves}"
    assert not walk.problems, f"FreeFormBody holds nothing the walk cannot read: {walk.problems}"
    print_success(f"✓ {len(found)} free-form positions, one float leaf, no problem")
