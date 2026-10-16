r"""
The texts the API client generator pastes unescaped into the TypeScript client (workstream E, backlog E-5).

``./dev.py api sync`` writes ``app.openapi()`` to ``frontend/src/lib/api/openapi.json`` (``scripts/list_api_endpoints.py``),
then runs ``npm run generate-api``: ``openapi-zod-client`` 1.18.3 with ``--export-types --with-docs --with-description``
writes ``frontend/src/lib/api/generated.ts``, copying the texts of the document into that TypeScript source as they are,
unescaped. In lot E2b a model docstring that spanned lines and quoted ````GET /system/instance```` became a tagged
template: the client threw ``TypeError: "The email part of " is not a function`` at import, and every page of the app
broke. Nothing breaks the client today; this guard keeps it so. The generator pipeline stays as it is (coordinator's
decision): the texts have to fit it.

The rule was read from the generator's code (``getZodChain``, ``templates/default.hbs``, ``generateJSDocArray``,
``openApiToTypescript``), then confirmed by four isolated matrices: one text in one place of a small document, generated
and parsed with TypeScript (journal plan phase01Email, «E-5.0»). A text lands in one of four forms:

- template — ``.describe()`` of a text that holds a line break (``\n`` or ``\r``), written as a raw template literal
  `` `…` ``. Forbidden: a backtick (one is a syntax error; two, as in ````this````, make a tagged template, the
  TypeError of E2b), ``${`` (a substitution, run at import), ``\`` (a syntax error before ``x``, ``u`` or at the end, a
  silently altered text otherwise).
- quoted — ``.describe()`` of a one-line text, written between raw double quotes. Forbidden: ``"`` and ``\``;
  backticks, ``${`` and ``*/`` are fine.
- handlebars — the description of an operation, of a response whose status is not 2xx (with or without content) and of
  a request body, written as ``description: `{{text}}```: Handlebars escapes ``& < > " ' ` =`` and nothing else.
  Forbidden: ``${`` and ``\``; backticks are fine (they become ``&#x60;``).
- jsdoc — the ``/** … */`` the exported TypeScript types carry above a node: its ``description``, ``pattern``, ``enum``
  values (joined with ", "), ``default``, ``example`` and each of ``examples`` (as JSON), ``externalDocs.url``.
  Forbidden: ``*/``.

Where ``.describe()`` is written, and with which text:

- an object property: its own description. A property that is a ``$ref``, with or without sibling keys, carries the
  referenced component's own description, never the one beside the ``$ref``. A property with ``anyOf``/``oneOf`` and a
  description of its own carries that description;
- inline ``items`` and inline non-empty ``additionalProperties``: their own description. A ``$ref`` there carries the
  description beside it, never the component's (the reverse of a property), and nothing without one;
- a parameter (query, path, header): its own description, trimmed first (``String.prototype.trim``), so
  ``"One line `x`\n"`` is one line, quoted;
- the same rules hold inside the schemas of parameters, request bodies and responses.

Never in ``.describe()``: a component's description at its definition; the description of an ``anyOf``/``oneOf``/``allOf``
member, inline or ``$ref`` (the properties and items inside an inline member are written); the schema of a request body
or a response itself; 2xx and ``default`` responses (the generator's spec-compliant mode drops ``default``); components
no endpoint reaches. A parameter whose schema is a ``$ref`` overwrites the shared component's description with its own,
trimmed and maybe empty: whether the component's text then reaches a property depends on the order in which the
generator visits the endpoints (a GET reads its parameters before the response holding the property, a POST its body
before its parameters).

JSDoc lands on any non-``$ref`` node inside an exported type, not only on properties: ``*/`` in the description of
``items`` or of an ``anyOf`` member is a syntax error too. The component's own description and inline
``additionalProperties`` were found harmless.

Two conservative decisions (night of 2026-10-16, to review); the guard may flag a text today's client would not carry,
it misses none:

1. The order effect is ignored: a component's original text is checked at every property typed with it, and every
   parameter's own text at the parameter.
2. ``*/`` is checked on every schema node anywhere — the components and the schemas of parameters, request bodies and
   responses, recursively, ``$ref`` siblings included — for every key ``generateJSDocArray`` writes. Recursively means
   along every keyword the generator follows: ``properties``, ``items``, ``additionalProperties``, ``anyOf``,
   ``oneOf``, ``allOf``; 1.18.3 never reads ``prefixItems``, ``patternProperties`` or ``not``.

The walker also reads where the generator writes nothing: a component no endpoint reaches, a deprecated endpoint, a
cookie parameter, a response content other than JSON. A shape the rule was not verified on — a path item, parameter,
request body or response given by ``$ref``, a parameter described by ``content``, a ``$ref`` outside
``#/components/schemas/`` — fails OCT-032 until the rule is verified on it; FastAPI writes none of them.

When OCT-030 is red, each site gives where its text comes from, its form, the forbidden tokens and an excerpt.
``Model.field`` is a field's description, ``Model.field -> Other`` the docstring of the model ``Other`` the field is
typed with; ``[]``, ``{}``, ``<anyOf0>`` are the items, the values, a member of what precedes; a bare ``Model`` is the
model's docstring; ``GET /path`` is the route's docstring or ``description=``, ``GET /path ?name`` a parameter's
``description=``, ``GET /path 409`` a ``responses=`` entry, ``POST /path body`` the request body's description. Then:

- template: keep the docstring or description on one line, without ``"`` or ``\``; or rephrase it without backticks,
  ``${`` and ``\``. The E2b fix left a one-line docstring and moved the explanation into a code comment;
- quoted: rephrase it without ``"`` and ``\``;
- handlebars: rephrase it without ``${`` and ``\``;
- jsdoc: never write ``*/`` in a description, a pattern, an enum value, a default or an example.

Never patch ``generated.ts`` by hand: the next ``api sync`` writes it again.

When OCT-001 is red, the generator or its options changed: verify the rule again (journal plan
``LibreFolio_developer_journal/Release_2/Phase_1/08_email/plan-phase01Email.prompt.md``, «E-5.0», and its matrices)
before moving ``VERIFIED_VERSION`` or ``VERIFIED_OPTIONS``.

OCT-001 pins the generator; OCT-010…018 run the model on small hand-written documents, each case stating the
generator's verdict; OCT-020 and OCT-021 run it on what FastAPI and Pydantic write; OCT-030…032 on the real document,
``backend.app.main.app.openapi()``, the source ``api sync`` exports.

No database, no server, no network, and the tests write nothing. Importing ``backend.app.main`` (OCT-030…032 only)
configures the application's logging, which creates ``<data dir>/logs/`` and opens ``librefolio.log`` there, the lane's
log that its backend writes too: the runner keeps this unit in the category's ``write-scoped`` class, not ``pure``.
"""

from __future__ import annotations

import functools
import json
import re
import shlex
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from pydantic import BaseModel

from backend.test_scripts.test_utils import print_info, print_section, print_success

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_JSON = REPO_ROOT / "frontend" / "package.json"
PACKAGE_LOCK = REPO_ROOT / "frontend" / "package-lock.json"
PLAN = "LibreFolio_developer_journal/Release_2/Phase_1/08_email/plan-phase01Email.prompt.md"

GENERATOR = "openapi-zod-client"
#: The generator the rule was verified on, as frontend/package-lock.json pins it: what `npm ci` installs.
VERIFIED_VERSION = "1.18.3"
#: The options generate-api ran it with when the rule was verified, sorted, the output path aside.
VERIFIED_OPTIONS = ("--export-types", "--with-description", "--with-docs")
OUTPUT_OPTIONS = frozenset({"-o", "--output"})
REVERIFY = f"the rule this guard encodes was verified on {GENERATOR} {VERIFIED_VERSION} run with exactly {' '.join(VERIFIED_OPTIONS)}: verify it again (journal plan {PLAN}, «E-5.0», and its matrices) before moving VERIFIED_VERSION or VERIFIED_OPTIONS"

TEMPLATE = "template"
QUOTED = "quoted"
HANDLEBARS = "handlebars"
JSDOC = "jsdoc"
FORMS = (TEMPLATE, QUOTED, HANDLEBARS, JSDOC)

#: What each form cannot carry (see the module docstring).
FORBIDDEN: dict[str, tuple[str, ...]] = {
    TEMPLATE: ("`", "${", "\\"),
    QUOTED: ('"', "\\"),
    HANDLEBARS: ("${", "\\"),
    JSDOC: ("*/",),
}
WRITTEN_AS = {
    TEMPLATE: ".describe() of a text with a line break, written as a raw template literal `…`",
    QUOTED: '.describe() of a one-line text, written between raw double quotes "…"',
    HANDLEBARS: "the description of an endpoint, of a non-2xx response or of a request body, written as description: `{{text}}` (Handlebars escapes & < > \" ' ` = and nothing else)",
    JSDOC: "a text of a schema node, written inside a /** … */ comment of the exported types",
}
FIX_HINTS = {
    TEMPLATE: 'keep the docstring or description on one line, without " or \\; or rephrase it without backticks, ${ and \\ (the E2b fix left a one-line docstring and moved the explanation into a code comment)',
    QUOTED: 'rephrase it without " and \\ (on one line, backticks and ${ are fine)',
    HANDLEBARS: "rephrase it without ${ and \\ (backticks are fine there: Handlebars escapes them)",
    JSDOC: "never write */ in a description, a pattern, an enum value, a default or an example",
}
LOCATIONS = (
    "Reading a location: Model.field is a field's description; Model.field -> Other the docstring of the model Other the field is typed with; "
    "[] {} <anyOf0> the items, the values, a member of what precedes; a bare Model the model's docstring; GET /path the route's docstring or description=; "
    "GET /path ?name a parameter's description=; GET /path 409 a responses= entry; POST /path body the request body's description."
)

HTTP_METHODS = frozenset({"get", "put", "post", "delete", "options", "head", "patch", "trace"})
UNIONS = ("anyOf", "oneOf", "allOf")
SCHEMA_REF = "#/components/schemas/"
#: What String.prototype.trim removes: ECMAScript white space and line terminators. str.strip() differs (it removes
#: U+001C-U+001F and U+0085 too, and keeps U+FEFF), and a difference at the edge of a text can change its form.
JS_WHITESPACE = "\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
EXCERPT_WIDTH = 120

# What a schema node is to the node holding it, which decides whether its description goes into .describe().
ROOT = "root"  # a component, or the schema of a parameter, a request body or a response: never
FIELD = "field"  # an object property: its own description; a $ref: the component's
NESTED = "nested"  # inline items or additionalProperties: its own description; a $ref: the one beside it
MEMBER = "member"  # a member of anyOf, oneOf or allOf: never


# =============================================================================
# The model of the generator
# =============================================================================


@dataclass(frozen=True)
class Site:
    """A text the generator writes (or, conservatively, may write): where it comes from, its form, the text."""

    where: str
    form: str
    text: str

    @property
    def forbidden(self) -> tuple[str, ...]:
        """The tokens of the text its form cannot carry."""
        return tuple(token for token in FORBIDDEN[self.form] if token in self.text)


def zod_form(text: str) -> str:
    r"""The form ``getZodChain`` writes a description in: a template literal as soon as it holds ``\n`` or ``\r``."""
    return TEMPLATE if "\n" in text or "\r" in text else QUOTED


def js_trim(text: str) -> str:
    """``text.trim()`` in JavaScript, which the generator applies to a parameter's description."""
    return text.strip(JS_WHITESPACE)


def is_error_status(status: str) -> bool:
    """Whether the generator writes the description of a response: any status but ``default`` and 2xx (``4XX`` too)."""
    return status != "default" and not (status.isdigit() and 200 <= int(status) < 300)


def jsdoc_texts(node: dict[str, Any]) -> list[str]:
    """The texts ``generateJSDocArray`` writes about a schema node, numbers and flags aside, empty ones dropped."""
    texts = [node.get("description"), node.get("pattern")]
    if isinstance(node.get("enum"), list):
        texts.append(", ".join(value if isinstance(value, str) else json.dumps(value) for value in node["enum"]))
    texts += [json.dumps(node[key], ensure_ascii=False) for key in ("default", "example") if key in node]
    if isinstance(node.get("examples"), list):
        texts += [json.dumps(example, ensure_ascii=False) for example in node["examples"]]
    docs = node.get("externalDocs")
    texts.append(docs.get("url") if isinstance(docs, dict) else None)
    return [text for text in texts if isinstance(text, str) and text]


class ClientTextModel:
    """Every place where ``openapi-zod-client`` 1.18.3 would write a text of ``document``, with its form.

    ``sites`` holds them in document order: the components first, then the operations. ``property_refs`` counts the
    properties typed with each component, ``unmodelled`` lists the shapes the rule was not verified on.
    """

    def __init__(self, document: dict[str, Any]) -> None:
        self.document = document
        self.schemas: dict[str, Any] = (document.get("components") or {}).get("schemas") or {}
        self.sites: list[Site] = []
        self.property_refs: Counter[str] = Counter()
        self.unmodelled: list[str] = []

    def run(self) -> ClientTextModel:
        """Read every component, then every operation of every path."""
        for name, schema in self.schemas.items():
            self._visit(schema, name)
        for path, item in (self.document.get("paths") or {}).items():
            self._path(path, item)
        return self

    def latent(self) -> list[tuple[str, tuple[str, ...]]]:
        """Components whose own description its form could not carry, typed by no property yet: one field away from
        breaking the client, as in E2b. Each with its forbidden tokens."""
        found = []
        for name, schema in self.schemas.items():
            text = schema.get("description") if isinstance(schema, dict) else None
            if isinstance(text, str) and text and not self.property_refs[name]:
                forbidden = Site(name, zod_form(text), text).forbidden
                if forbidden:
                    found.append((name, forbidden))
        return found

    # -- schemas ------------------------------------------------------------------------------------------------------

    def _visit(self, node: Any, where: str, kind: str = ROOT) -> None:
        """A schema node and everything below it: JSDoc everywhere (decision 2), ``.describe()`` where it is written."""
        if not isinstance(node, dict):
            return
        self._jsdoc(node, where)
        if "$ref" in node:
            self._reference(node, where, kind)
            return
        if kind in (FIELD, NESTED):
            self._describe(node.get("description"), where)
        for name, child in _mapping(node.get("properties")).items():
            self._visit(child, f"{where}.{name}", FIELD)
        self._visit(node.get("items"), f"{where}[]", NESTED)
        self._visit(node.get("additionalProperties"), f"{where}{{}}", NESTED)
        for key in UNIONS:
            for index, member in enumerate(_sequence(node.get(key))):
                self._visit(member, f"{where}<{key}{index}>", MEMBER)

    def _reference(self, node: dict[str, Any], where: str, kind: str) -> None:
        """A ``$ref``: a property carries the component's description, items and additionalProperties the description
        beside the ``$ref``; anywhere else (a union member, a parameter, a body, a response) nothing is written."""
        target = self._component(node["$ref"], where)
        if kind == NESTED:
            self._describe(node.get("description"), where)
        elif kind == FIELD and target is not None:
            self.property_refs[target] += 1
            component = self.schemas[target]
            self._describe(component.get("description") if isinstance(component, dict) else None, f"{where} -> {target}")

    def _component(self, ref: Any, where: str) -> str | None:
        """The component ``ref`` points to; a reference outside ``#/components/schemas/`` or to nothing is unmodelled."""
        name = ref.removeprefix(SCHEMA_REF) if isinstance(ref, str) and ref.startswith(SCHEMA_REF) else None
        if name not in self.schemas:
            self.unmodelled.append(f"{where}: $ref {ref!r} is not a component of {SCHEMA_REF}")
            return None
        return name

    def _describe(self, text: Any, where: str) -> None:
        if isinstance(text, str) and text:
            self.sites.append(Site(where, zod_form(text), text))

    def _handlebars(self, text: Any, where: str) -> None:
        if isinstance(text, str) and text:
            self.sites.append(Site(where, HANDLEBARS, text))

    def _jsdoc(self, node: dict[str, Any], where: str) -> None:
        self.sites.extend(Site(where, JSDOC, text) for text in jsdoc_texts(node))

    # -- operations ---------------------------------------------------------------------------------------------------

    def _path(self, path: str, item: Any) -> None:
        if not isinstance(item, dict) or "$ref" in item:
            self.unmodelled.append(f"{path}: a path item that is not an inline object")
            return
        shared = _sequence(item.get("parameters"))
        for method, operation in item.items():
            if method in HTTP_METHODS and isinstance(operation, dict):
                self._operation(f"{method.upper()} {path}", operation, shared)

    def _operation(self, label: str, operation: dict[str, Any], shared: list[Any]) -> None:
        """An operation: its description, the parameters of the path and its own, its request body, its responses."""
        self._handlebars(operation.get("description"), label)
        for parameter in [*shared, *_sequence(operation.get("parameters"))]:
            self._parameter(parameter, label)
        if operation.get("requestBody") is not None:
            self._request_body(operation["requestBody"], f"{label} body")
        for status, response in _mapping(operation.get("responses")).items():
            self._response(response, f"{label} {status}", str(status))

    def _parameter(self, parameter: Any, label: str) -> None:
        """A parameter: its own description, trimmed, in ``.describe()``; its schema below it, read like any other."""
        if not isinstance(parameter, dict) or "$ref" in parameter:
            self.unmodelled.append(f"{label}: a parameter that is not an inline object: {parameter!r}")
            return
        where = f"{label} ?{parameter.get('name')}"
        if "content" in parameter:
            self.unmodelled.append(f"{where}: a parameter described by content instead of schema")
        description = parameter.get("description")
        self._describe(js_trim(description) if isinstance(description, str) else None, where)
        self._visit(parameter.get("schema"), where)

    def _request_body(self, body: Any, where: str) -> None:
        if not isinstance(body, dict) or "$ref" in body:
            self.unmodelled.append(f"{where}: a request body that is not an inline object")
            return
        self._handlebars(body.get("description"), where)
        self._content(body, where)

    def _response(self, response: Any, where: str, status: str) -> None:
        if not isinstance(response, dict) or "$ref" in response:
            self.unmodelled.append(f"{where}: a response that is not an inline object")
            return
        if is_error_status(status):
            self._handlebars(response.get("description"), where)
        self._content(response, where)

    def _content(self, holder: dict[str, Any], where: str) -> None:
        """The schemas of a body's or a response's content, every media type: their own description is never written."""
        for media in _mapping(holder.get("content")).values():
            if isinstance(media, dict):
                self._visit(media.get("schema"), where)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sequence(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def excerpt(site: Site, width: int = EXCERPT_WIDTH) -> str:
    """About ``width`` characters of the site's text, from a little before its first forbidden token, line breaks as ⏎."""
    first = min((site.text.index(token) for token in site.forbidden), default=0)
    start = max(0, first - width // 4)
    piece = site.text[start : start + width].replace("\r\n", "⏎").replace("\n", "⏎").replace("\r", "⏎")
    return ("…" if start else "") + piece + ("…" if start + width < len(site.text) else "")


def failure_report(sites: list[Site]) -> str:
    """What OCT-030 says when red: every site, grouped by form with the fix of its form, then how to read a location."""
    headline = f"{len(sites)} texts of app.openapi() that {GENERATOR} {VERIFIED_VERSION} would paste unescaped into frontend/src/lib/api/generated.ts"
    lines = [f"{headline}: after ./dev.py api sync the client would not parse, or would throw at import and break every page (lot E2b)."]
    for form in FORMS:
        group = [site for site in sites if site.form == form]
        if group:
            lines += ["", f"{form}: {WRITTEN_AS[form]}.", f"  fix: {FIX_HINTS[form]}."]
            lines += [f"  - [{form}] {site.where}  forbidden: {' '.join(site.forbidden)}  text: «{excerpt(site)}»" for site in group]
    return "\n".join([*lines, "", LOCATIONS])


# =============================================================================
# Small documents, in the shape of the matrices of «E-5.0»
# =============================================================================

LINE_BREAK = "\nSecond line."
#: The shape of lot E2b: double backticks in a text that spans lines.
E2B = "Read ``GET /system/instance`` first." + LINE_BREAK
#: A multi-line text with one pair of backticks, as the matrices wrote it.
BACKTICKS = "With `code`." + LINE_BREAK
CLEAN = "A clean text."
CLOSE = "Closes */ here."
#: A component without any text; a field typed with it makes Holder an exported TypeScript type, where JSDoc is written.
PLAIN = {"Plain": {"type": "object", "properties": {"v": {"type": "string"}}}}


def _ref(name: str) -> dict[str, str]:
    return {"$ref": f"{SCHEMA_REF}{name}"}


def _json(schema: dict[str, Any]) -> dict[str, Any]:
    return {"application/json": {"schema": schema}}


def _ok(schema: dict[str, Any]) -> dict[str, Any]:
    return {"description": "OK", "content": _json(schema)}


def _object(description: str) -> dict[str, Any]:
    return {"type": "object", "description": description, "properties": {"v": {"type": "string"}}}


def _enum(description: str) -> dict[str, Any]:
    return {"type": "string", "enum": ["a", "b"], "description": description}


def _query(name: str = "q", **fields: Any) -> dict[str, Any]:
    return {"name": name, "in": "query", "required": False, **fields}


def _document(fields: dict[str, Any] | None = None, *, components: dict[str, Any] | None = None, operation: dict[str, Any] | None = None, method: str = "get", path_parameters: list[Any] | None = None) -> dict[str, Any]:
    """A small OpenAPI 3.1 document: the component ``Holder`` with ``fields``, more ``components``, and one operation on
    ``/a`` answering ``Holder`` with 200, changed by ``operation``."""
    schemas = {"Holder": {"type": "object", "properties": dict(fields or {})}, **(components or {})}
    path_item: dict[str, Any] = {method: {"operationId": "op_a", "responses": {"200": _ok(_ref("Holder"))}, **(operation or {})}}
    if path_parameters:
        path_item["parameters"] = path_parameters
    return {"openapi": "3.1.0", "info": {"title": "probe", "version": "1"}, "paths": {"/a": path_item}, "components": {"schemas": schemas}}


def _model(document: dict[str, Any]) -> ClientTextModel:
    return ClientTextModel(document).run()


def _literal_sites(model: ClientTextModel) -> list[tuple[str, str, tuple[str, ...]]]:
    """The sites written as string literals (``.describe()`` and Handlebars), JSDoc aside: (where, form, forbidden)."""
    return [(site.where, site.form, site.forbidden) for site in model.sites if site.form != JSDOC]


def _flagged(model: ClientTextModel) -> list[tuple[str, str, tuple[str, ...]]]:
    """Every site, JSDoc included, holding a token its form cannot carry: (where, form, forbidden)."""
    return [(site.where, site.form, site.forbidden) for site in model.sites if site.forbidden]


def _latent(model: ClientTextModel) -> list[str]:
    return [name for name, _ in model.latent()]


# =============================================================================
# OCT-001: the generator the rule was verified on
# =============================================================================


def _generator_runs(script: str) -> list[tuple[str, ...]]:
    """The options of each run of the generator in an npm script, sorted, the output path aside (``--x=v`` as ``--x``)."""
    runs = []
    for command in re.split(r"[;&|]+", script):
        tokens = shlex.split(command)
        starts = [index for index, token in enumerate(tokens) if Path(token).name == GENERATOR]
        if starts:
            options = {token.split("=", 1)[0] for token in tokens[starts[0] + 1 :] if token.startswith("-")}
            runs.append(tuple(sorted(options - OUTPUT_OPTIONS)))
    return runs


def test_the_generator_is_the_one_the_rule_was_verified_on() -> None:
    """OCT-001 — tripwire: ``frontend/package-lock.json`` pins openapi-zod-client 1.18.3, and ``generate-api`` runs it
    once with exactly ``--export-types --with-docs --with-description`` besides its output path. Another version or
    another option can move a text to another place or form (``--default-status auto-correct`` writes the ``default``
    descriptions, ``--error-expr`` moves the line between errors and successes, ``-t`` swaps the template): the rule is
    verified again before the constants move."""
    print_section("OCT-001: openapi-zod-client, its version and its options")
    lock = json.loads(PACKAGE_LOCK.read_text(encoding="utf-8"))
    version = lock.get("packages", {}).get(f"node_modules/{GENERATOR}", {}).get("version")
    assert version == VERIFIED_VERSION, f"frontend/package-lock.json installs {GENERATOR} {version}; {REVERIFY}"

    script = json.loads(PACKAGE_JSON.read_text(encoding="utf-8")).get("scripts", {}).get("generate-api", "")
    runs = _generator_runs(script)
    assert runs == [VERIFIED_OPTIONS], f"the generate-api script of frontend/package.json runs {GENERATOR} {len(runs)} time(s), with the options {runs} (output path aside): {script!r}; {REVERIFY}"
    print_success(f"{GENERATOR} {version}, run once by generate-api with {' '.join(VERIFIED_OPTIONS)}")


# =============================================================================
# OCT-010…018: the model, case by case
# =============================================================================


@pytest.mark.parametrize(
    ("text", "form", "forbidden"),
    [
        pytest.param("Odd ` tick." + LINE_BREAK, TEMPLATE, ("`",), id="multi-line-single-backtick"),  # syntax error
        pytest.param("With ``code``." + LINE_BREAK, TEMPLATE, ("`",), id="multi-line-double-backticks"),  # tagged template: TypeError at import (E2b)
        pytest.param("With ${x}." + LINE_BREAK, TEMPLATE, ("${",), id="multi-line-substitution"),  # substitution, run at import
        pytest.param("Path C:\\xdir." + LINE_BREAK, TEMPLATE, ("\\",), id="multi-line-backslash-x"),  # syntax error
        pytest.param('Say "hi", it costs $5 {braces}.' + LINE_BREAK, TEMPLATE, (), id="multi-line-quote-and-dollar"),  # parses, text intact
        pytest.param("Carriage\rreturn ``x``.", TEMPLATE, ("`",), id="carriage-return-is-a-line-break"),  # getZodChain looks for \n, \r, \r\n
        pytest.param('Say "hi".', QUOTED, ('"',), id="one-line-quote"),  # syntax error
        pytest.param("Trailing \\", QUOTED, ("\\",), id="one-line-backslash"),  # syntax error
        pytest.param("One line `code`, ``more``.", QUOTED, (), id="one-line-backticks"),  # parses
        pytest.param("One line ${x}.", QUOTED, (), id="one-line-substitution"),  # parses: no substitution between double quotes
    ],
)
def test_a_field_description_takes_the_form_of_its_line_breaks(text: str, form: str, forbidden: tuple[str, ...]) -> None:
    """OCT-010 — ``.describe()`` of an inline field: a text with a line break goes into a raw template literal, where
    a backtick, ``${`` and ``\\`` break the client; a one-line text between raw double quotes, where ``"`` and ``\\`` do
    and the rest is fine («E-5.0», matrix 1, row property-inline)."""
    print_section(f"OCT-010: {text!r}")
    model = _model(_document({"p": {"type": "string", "description": text}}))
    assert _literal_sites(model) == [("Holder.p", form, forbidden)], f"expected Holder.p as {form} with forbidden {forbidden}, got {_literal_sites(model)}"
    print_success(f"{form}, forbidden {forbidden or 'none'}")


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        # matrix 1, property-ref: the component's text, syntax error
        pytest.param(_document({"p": _ref("Comp")}, components={"Comp": _object(E2B)}), [("Holder.p -> Comp", TEMPLATE, ("`",))], id="ref-field-carries-the-component-text"),
        # matrix 1, property-ref-sibling: a clean description beside the $ref changes nothing
        pytest.param(_document({"p": {**_ref("Comp"), "description": CLEAN}}, components={"Comp": _object(E2B)}), [("Holder.p -> Comp", TEMPLATE, ("`",))], id="ref-field-clean-sibling-hazardous-component"),
        # matrix 3, sibling-only-hazard: the description beside the $ref is never written
        pytest.param(_document({"p": {**_ref("Comp"), "description": E2B}}, components={"Comp": _object(CLEAN)}), [("Holder.p -> Comp", QUOTED, ())], id="ref-field-hazardous-sibling-clean-component"),
        # matrix 1, property-anyof: the field's own description, syntax error
        pytest.param(_document({"p": {"anyOf": [{"type": "string"}, {"type": "null"}], "description": E2B}}), [("Holder.p", TEMPLATE, ("`",))], id="union-field-own-description"),
        # code: properties are written at any depth
        pytest.param(_document({"p": {"type": "object", "properties": {"q": {"type": "string", "description": E2B}}}}), [("Holder.p.q", TEMPLATE, ("`",))], id="nested-inline-field"),
        # code: an inline member's properties are written
        pytest.param(_document({"p": {"anyOf": [{"type": "object", "properties": {"q": {"type": "string", "description": E2B}}}, {"type": "null"}]}}), [("Holder.p<anyOf0>.q", TEMPLATE, ("`",))], id="field-of-a-union-member"),
        # matrix 4, anyof-member-array-item-desc: an inline member's items are written, syntax error
        pytest.param(_document({"p": {"anyOf": [{"type": "array", "items": {"type": "string", "description": E2B}}, {"type": "null"}]}}), [("Holder.p<anyOf0>[]", TEMPLATE, ("`",))], id="items-of-a-union-member"),
        # code: a field typed with a component inside a response schema carries the component's text
        pytest.param(_document(components={"Comp": _object(E2B)}, operation={"responses": {"200": _ok({"type": "object", "properties": {"r": _ref("Comp")}})}}), [("GET /a 200.r -> Comp", TEMPLATE, ("`",))], id="ref-field-inside-a-response"),
    ],
)
def test_a_field_carries_its_own_description_or_its_component_s(document: dict[str, Any], expected: list[Any]) -> None:
    """OCT-011 — ``.describe()`` of a field: an inline field, at any depth and inside the members of a union, carries its
    own description; a field typed with a component (a ``$ref``) carries the component's own description, never the one
    written beside the ``$ref``; a union field carries its own («E-5.0», matrices 1, 3 and 4)."""
    print_section(f"OCT-011: {expected[0][0]}")
    model = _model(document)
    assert _literal_sites(model) == expected, f"expected {expected}, got {_literal_sites(model)}"
    assert _latent(model) == [], f"a component typed by a field is not latent: {model.latent()}"
    print_success(f"{expected}")


@pytest.mark.parametrize(
    ("document", "expected", "latent"),
    [
        # matrix 1, items-inline / additional-inline: syntax error
        pytest.param(_document({"p": {"type": "array", "items": {"type": "string", "description": E2B}}}), [("Holder.p[]", TEMPLATE, ("`",))], [], id="inline-items"),
        pytest.param(_document({"p": {"type": "object", "additionalProperties": {"type": "string", "description": E2B}}}), [("Holder.p{}", TEMPLATE, ("`",))], [], id="inline-additional-properties"),
        # matrix 4, items-ref-sibling / additional-ref-sibling: the description beside the $ref, syntax error
        pytest.param(_document({"p": {"type": "array", "items": {**_ref("Comp"), "description": E2B}}}, components={"Comp": _object(CLEAN)}), [("Holder.p[]", TEMPLATE, ("`",))], [], id="ref-items-hazardous-sibling-clean-component"),
        pytest.param(_document({"p": {"type": "object", "additionalProperties": {**_ref("Comp"), "description": E2B}}}, components={"Comp": _object(CLEAN)}), [("Holder.p{}", TEMPLATE, ("`",))], [], id="ref-additional-hazardous-sibling-clean-component"),
        # matrix 1 (items-ref) and 4: the component's text is never written there; a clean sibling is
        pytest.param(_document({"p": {"type": "array", "items": {**_ref("Comp"), "description": CLEAN}}}, components={"Comp": _object(E2B)}), [("Holder.p[]", QUOTED, ())], ["Comp"], id="ref-items-clean-sibling-hazardous-component"),
        pytest.param(_document({"p": {"type": "array", "items": _ref("Comp")}}, components={"Comp": _object(E2B)}), [], ["Comp"], id="ref-items-no-sibling-hazardous-component"),
        pytest.param(_document({"p": {"type": "object", "additionalProperties": {**_ref("Comp"), "description": CLEAN}}}, components={"Comp": _object(E2B)}), [("Holder.p{}", QUOTED, ())], ["Comp"], id="ref-additional-clean-sibling-hazardous-component"),
        pytest.param(_document({"p": {"type": "object", "additionalProperties": _ref("Comp")}}, components={"Comp": _object(E2B)}), [], ["Comp"], id="ref-additional-no-sibling-hazardous-component"),
        # code: the same inside the schemas of a response and of a request body
        pytest.param(_document(components={"Comp": _object(CLEAN)}, operation={"responses": {"200": _ok({"type": "array", "items": {**_ref("Comp"), "description": E2B}})}}), [("GET /a 200[]", TEMPLATE, ("`",))], [], id="ref-items-sibling-inside-a-response"),
        pytest.param(
            _document(components={"Comp": _object(CLEAN)}, method="post", operation={"requestBody": {"required": True, "content": _json({"type": "object", "additionalProperties": {**_ref("Comp"), "description": E2B}})}}),
            [("POST /a body{}", TEMPLATE, ("`",))],
            [],
            id="ref-additional-sibling-inside-a-request-body",
        ),
    ],
)
def test_items_and_values_carry_their_own_description_or_the_one_beside_their_ref(document: dict[str, Any], expected: list[Any], latent: list[str]) -> None:
    """OCT-012 — ``.describe()`` of inline ``items`` and ``additionalProperties``: their own description; for a
    ``$ref`` the description written beside it — the reverse of a field — never the component's, and nothing without
    one; the same inside the schemas of responses and request bodies («E-5.0», matrices 1 and 4). A component reached
    only this way stays latent."""
    print_section(f"OCT-012: {expected or latent}")
    model = _model(document)
    assert _literal_sites(model) == expected, f"expected {expected}, got {_literal_sites(model)}"
    assert _latent(model) == latent, f"expected the latent components {latent}, got {model.latent()}"
    print_success(f"{expected or 'nothing written'}, latent {latent}")


@pytest.mark.parametrize(
    ("document", "latent"),
    [
        # matrix 4: an inline member's own description is not in .describe() (it lands in JSDoc)
        pytest.param(_document({"p": {"anyOf": [{"type": "string", "description": E2B}, {"type": "null"}]}}), [], id="anyof-inline-member"),
        pytest.param(_document({"p": {"oneOf": [{"type": "string", "description": E2B}, {"type": "integer"}]}}), [], id="oneof-inline-member"),
        pytest.param(_document({"p": {"allOf": [{"type": "string", "description": E2B}]}}), [], id="allof-single-inline-member"),
        # matrix 1, anyof-member-ref, component-unreferenced, body-and-response-ref: not written
        pytest.param(_document({"p": {"anyOf": [_ref("Comp"), {"type": "null"}]}}, components={"Comp": _object(E2B)}), ["Comp"], id="ref-union-member"),
        pytest.param(_document(components={"Comp": _object(E2B)}), ["Comp"], id="unreferenced-component"),
        pytest.param(
            _document(components={"Comp": _object(E2B)}, method="post", operation={"requestBody": {"required": True, "content": _json(_ref("Comp"))}, "responses": {"200": _ok(_ref("Comp"))}}),
            ["Comp"],
            id="ref-request-body-and-response",
        ),
        # code: getZodChain is called without options on the schema of a body or a response, so never describes it
        pytest.param(_document(operation={"responses": {"200": _ok({"type": "object", "description": E2B, "properties": {}})}}), [], id="inline-response-schema"),
    ],
)
def test_union_members_and_payload_schemas_never_carry_their_description(document: dict[str, Any], latent: list[str]) -> None:
    """OCT-013 — not written into ``.describe()``: the description of an ``anyOf``/``oneOf``/``allOf`` member, inline
    or ``$ref``; a component no endpoint reaches; the schema of a request body or a response itself («E-5.0»,
    matrices 1 and 4). The text — E2b's, multi-line with double backticks — is read all the same: it is the text of a
    JSDoc site, which checks only ``*/``."""
    print_section(f"OCT-013: latent {latent}")
    model = _model(document)
    assert _literal_sites(model) == [], f"nothing is written into .describe() here, got {_literal_sites(model)}"
    assert _flagged(model) == [], f"nothing is flagged here, got {_flagged(model)}"
    assert [site.where for site in model.sites if site.text == E2B and site.form == JSDOC], "the walker never read the text: no JSDoc site carries it"
    assert _latent(model) == latent, f"expected the latent components {latent}, got {model.latent()}"
    print_success(f"not written, latent {latent}")


@pytest.mark.parametrize(
    ("document", "expected", "latent"),
    [
        # matrix 1, parameter: syntax error
        pytest.param(_document(operation={"parameters": [_query(description=BACKTICKS, schema={"type": "string"})]}), [("GET /a ?q", TEMPLATE, ("`",))], [], id="multi-line-backtick"),
        # code: trim() first, so the text is one line, quoted: the backticks are fine
        pytest.param(_document(operation={"parameters": [_query(description="One line `x`\n", schema={"type": "string"})]}), [("GET /a ?q", QUOTED, ())], [], id="trimmed-to-one-line"),
        # ECMAScript: U+0085 is not white space for trim(), so the line break before it stays: template
        pytest.param(_document(operation={"parameters": [_query(description="Tick `x`\n\u0085", schema={"type": "string"})]}), [("GET /a ?q", TEMPLATE, ("`",))], [], id="trimmed-as-javascript-trims"),
        # code: the parameters of the path item are the operation's too
        pytest.param(_document(path_parameters=[_query(description=BACKTICKS, schema={"type": "string"})]), [("GET /a ?q", TEMPLATE, ("`",))], [], id="path-level-parameter"),
        # matrix 2, parameter-ref-with-desc: the parameter's own text, syntax error
        pytest.param(_document(components={"Comp": _enum(CLEAN)}, operation={"parameters": [_query(description=BACKTICKS, schema=_ref("Comp"))]}), [("GET /a ?q", TEMPLATE, ("`",))], [], id="ref-schema-with-a-description"),
        # matrix 1, parameter-ref: without a description of its own the parameter writes nothing (the component's text is blanked)
        pytest.param(_document(components={"Comp": _enum(E2B)}, operation={"parameters": [_query(schema=_ref("Comp"))]}), [], ["Comp"], id="ref-schema-without-description"),
        # matrix 2, blank-then-property: today's client would not carry it in a GET; decision 1 flags it at the field
        pytest.param(_document({"p": _ref("Comp")}, components={"Comp": _enum(E2B)}, operation={"parameters": [_query(schema=_ref("Comp"))]}), [("Holder.p -> Comp", TEMPLATE, ("`",))], [], id="conservative-component-text-at-the-field"),
        # code: items inside a parameter's schema follow OCT-012
        pytest.param(_document(components={"Comp": _object(CLEAN)}, operation={"parameters": [_query(schema={"type": "array", "items": {**_ref("Comp"), "description": E2B}})]}), [("GET /a ?q[]", TEMPLATE, ("`",))], [], id="ref-items-sibling-inside-a-parameter"),
    ],
)
def test_a_parameter_carries_its_own_trimmed_description(document: dict[str, Any], expected: list[Any], latent: list[str]) -> None:
    """OCT-014 — ``.describe()`` of a parameter: its own description after ``trim()``, a ``$ref`` schema or not; the
    component a ``$ref`` schema points to gets the parameter's text instead of its own. Whether the component's text
    still reaches a field typed with it depends on the order the generator visits the endpoints: decision 1 ignores it
    and checks the text at the field («E-5.0», matrices 1 and 2)."""
    print_section(f"OCT-014: {expected or latent}")
    model = _model(document)
    assert _literal_sites(model) == expected, f"expected {expected}, got {_literal_sites(model)}"
    assert _latent(model) == latent, f"expected the latent components {latent}, got {model.latent()}"
    print_success(f"{expected or 'nothing written'}, latent {latent}")


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        # matrix 1, operation: parses, the backticks escaped to &#x60;
        pytest.param(_document(operation={"description": "Read ``this`` `first`." + LINE_BREAK}), [("GET /a", HANDLEBARS, ())], id="operation-backticks"),
        # matrix 1, operation: a substitution
        pytest.param(_document(operation={"description": "With ${x}."}), [("GET /a", HANDLEBARS, ("${",))], id="operation-substitution"),
        # matrix 1, operation: a syntax error
        pytest.param(_document(operation={"description": "Path C:\\xdir."}), [("GET /a", HANDLEBARS, ("\\",))], id="operation-backslash"),
        # matrix 3, error-response-dollar: a substitution
        pytest.param(_document(operation={"responses": {"200": _ok(_ref("Holder")), "409": {**_ok(_ref("Holder")), "description": "With ${x}."}}}), [("GET /a 409", HANDLEBARS, ("${",))], id="error-response"),
        # matrix 3, error-no-content-dollar: a substitution
        pytest.param(_document(operation={"responses": {"200": _ok(_ref("Holder")), "404": {"description": "With ${x}."}}}), [("GET /a 404", HANDLEBARS, ("${",))], id="error-response-without-content"),
        # matrix 1, response-description: never written
        pytest.param(_document(operation={"responses": {"200": {**_ok(_ref("Holder")), "description": "With ${x}."}}}), [], id="success-response"),
        # matrix 3, default-response-dollar: never written
        pytest.param(_document(operation={"responses": {"200": _ok(_ref("Holder")), "default": {**_ok(_ref("Holder")), "description": "With ${x}."}}}), [], id="default-response"),
        # matrix 3, body-description-dollar: a substitution
        pytest.param(_document(method="post", operation={"requestBody": {"description": "With ${x}.", "required": True, "content": _json(_ref("Holder"))}}), [("POST /a body", HANDLEBARS, ("${",))], id="request-body"),
    ],
)
def test_endpoint_error_and_body_descriptions_are_handlebars_templates(document: dict[str, Any], expected: list[Any]) -> None:
    """OCT-015 — ``description: `{{text}}``` for an operation, a response whose status is not 2xx (with or without
    content) and a request body: Handlebars escapes the backticks, not ``${`` nor ``\\``. A 2xx or ``default``
    response's description is never written («E-5.0», matrices 1 and 3)."""
    print_section(f"OCT-015: {expected}")
    model = _model(document)
    assert _literal_sites(model) == expected, f"expected {expected}, got {_literal_sites(model)}"
    print_success(f"{expected or 'not written'}")


@pytest.mark.parametrize(
    ("document", "where"),
    [
        # matrix 2, jsdoc-inline-in-type, and matrix 3, jsdoc-*-close: syntax error
        pytest.param(_document({"x": _ref("Plain"), "p": {"type": "string", "description": CLOSE}}, components=PLAIN), "Holder.p", id="field-description"),
        pytest.param(_document({"x": _ref("Plain"), "p": {"type": "string", "default": "*/5 * * * *"}}, components=PLAIN), "Holder.p", id="field-default"),
        pytest.param(_document({"x": _ref("Plain"), "p": {"type": "string", "pattern": "^.*/$"}}, components=PLAIN), "Holder.p", id="field-pattern"),
        pytest.param(_document({"x": _ref("Plain"), "p": {"type": "string", "enum": ["a", "*/x"]}}, components=PLAIN), "Holder.p", id="field-enum"),
        pytest.param(_document({"x": _ref("Plain"), "p": {"type": "string", "examples": ["*/x"]}}, components=PLAIN), "Holder.p", id="field-examples"),
        # code: generateJSDocArray writes example and externalDocs.url as well
        pytest.param(_document({"x": _ref("Plain"), "p": {"type": "string", "example": "*/x"}}, components=PLAIN), "Holder.p", id="field-example"),
        pytest.param(_document({"x": _ref("Plain"), "p": {"type": "string", "externalDocs": {"url": "https://example.org/*/x"}}}, components=PLAIN), "Holder.p", id="field-external-docs"),
        # matrix 4, jsdoc-items-desc-close / jsdoc-anyof-member-desc-close: syntax error
        pytest.param(_document({"x": _ref("Plain"), "p": {"type": "array", "items": {"type": "string", "description": CLOSE}}}, components=PLAIN), "Holder.p[]", id="items-description"),
        pytest.param(_document({"x": _ref("Plain"), "p": {"anyOf": [{"type": "string", "description": CLOSE}, {"type": "null"}]}}, components=PLAIN), "Holder.p<anyOf0>", id="anyof-member-description"),
        # decision 2, found harmless (matrix 4) or never seen, flagged all the same
        pytest.param(_document({"x": _ref("Plain"), "p": _ref("Comp")}, components={**PLAIN, "Comp": _object(CLOSE)}), "Comp", id="conservative-component-description"),
        pytest.param(_document({"x": _ref("Plain"), "p": {"type": "object", "additionalProperties": {"type": "string", "description": CLOSE}}}, components=PLAIN), "Holder.p{}", id="conservative-additional-properties"),
        pytest.param(_document({"x": _ref("Plain"), "p": {**_ref("Plain"), "description": CLOSE}}, components=PLAIN), "Holder.p", id="conservative-ref-sibling"),
        pytest.param(_document(operation={"parameters": [_query(schema={"type": "string", "default": "*/5 * * * *"})]}), "GET /a ?q", id="conservative-parameter-schema"),
        pytest.param(_document(operation={"responses": {"200": _ok({"type": "object", "properties": {"r": {"type": "string", "pattern": "^.*/$"}}})}}), "GET /a 200.r", id="conservative-response-schema"),
    ],
)
def test_no_schema_node_closes_a_jsdoc_comment(document: dict[str, Any], where: str) -> None:
    """OCT-016 — ``*/`` closes the ``/** … */`` the exported types carry above a node, whichever text of the node holds
    it: the description, the pattern, an enum value, the default, an example, ``externalDocs.url``. JSDoc lands on
    fields, items and union members («E-5.0», matrices 2, 3 and 4); decision 2 checks every schema node anywhere,
    ``$ref`` siblings included. One-line ``*/`` is fine in ``.describe()``: only the JSDoc site is flagged."""
    print_section(f"OCT-016: {where}")
    model = _model(document)
    assert _flagged(model) == [(where, JSDOC, ("*/",))], f"expected only {where} flagged as jsdoc, got {_flagged(model)}"
    print_success(f"{where}: jsdoc, */")


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        pytest.param(_document(operation={"parameters": [{"$ref": "#/components/parameters/Q"}]}), "GET /a: a parameter that is not an inline object", id="parameter-ref"),
        pytest.param(_document(operation={"parameters": [_query(content=_json({"type": "string"}))]}), "GET /a ?q: a parameter described by content", id="parameter-content"),
        pytest.param(_document(method="post", operation={"requestBody": {"$ref": "#/components/requestBodies/B"}}), "POST /a body: a request body that is not an inline object", id="request-body-ref"),
        pytest.param(_document(operation={"responses": {"200": {"$ref": "#/components/responses/R"}}}), "GET /a 200: a response that is not an inline object", id="response-ref"),
        pytest.param(_document({"p": {"$ref": "#/$defs/Comp"}}), "Holder.p: $ref '#/$defs/Comp' is not a component", id="ref-outside-the-components"),
        pytest.param(_document({"p": _ref("Missing")}), "Holder.p: $ref '#/components/schemas/Missing' is not a component", id="dangling-ref"),
    ],
)
def test_a_shape_the_rule_was_not_verified_on_is_reported(document: dict[str, Any], expected: str) -> None:
    """OCT-017 — the walker knows the shapes FastAPI writes. Anything else — a parameter, request body or response
    given by ``$ref``, a parameter described by ``content``, a ``$ref`` outside ``#/components/schemas/`` or to no
    component — is reported, and OCT-032 fails on it, instead of being skipped in silence."""
    print_section(f"OCT-017: {expected}")
    model = _model(document)
    assert len(model.unmodelled) == 1 and model.unmodelled[0].startswith(expected), f"expected one unmodelled shape starting with {expected!r}, got {model.unmodelled}"
    print_success(model.unmodelled[0])


def test_the_failure_report_names_each_site_its_form_tokens_excerpt_and_fix() -> None:
    """OCT-018 — what OCT-030 says when red: every site with its location, form and forbidden tokens, an excerpt of
    about 120 characters cut around the first forbidden token (line breaks shown as ⏎), the fix of each form present
    and no other, and how to read a location."""
    print_section("OCT-018: the failure report")
    long_text = "x" * 300 + " ``code`` " + "y" * 300 + LINE_BREAK
    sites = [Site("Outer.inner -> Inner", TEMPLATE, long_text), Site("Holder.p", JSDOC, CLOSE)]
    report = failure_report(sites)

    assert "[template] Outer.inner -> Inner  forbidden: `" in report and "[jsdoc] Holder.p  forbidden: */" in report, report
    assert FIX_HINTS[TEMPLATE] in report and FIX_HINTS[JSDOC] in report and FIX_HINTS[QUOTED] not in report, report
    assert LOCATIONS in report, report
    cut = excerpt(sites[0])
    assert "``code``" in cut and cut.startswith("…") and cut.endswith("…") and len(cut) <= EXCERPT_WIDTH + 2, cut
    assert f"«{cut}»" in report, report
    assert excerpt(Site("Holder.p", TEMPLATE, BACKTICKS)) == "With `code`.⏎Second line."
    print_success("location, form, tokens, excerpt, fix")


# =============================================================================
# OCT-020/021: what FastAPI and Pydantic write
# =============================================================================


class Inner(BaseModel):
    """A probe model whose docstring spans lines and quotes ``code``, like the model of lot E2b.

    Pydantic writes the docstring as the component's description, line break included.
    """

    value: str


class Outer(BaseModel):
    """A probe model with a field typed with Inner."""

    inner: Inner


class OuterIndirect(BaseModel):
    """A probe model that holds Inner only in a list and in a union with None."""

    items: list[Inner]
    maybe: Inner | None = None


def _fastapi_document(response_model: type[BaseModel]) -> dict[str, Any]:
    """The document of a one-route FastAPI app answering ``response_model``, as ``api sync`` writes it (JSON)."""
    app = FastAPI(title="E-5 probe", version="1")

    @app.get("/probe", response_model=response_model)
    def probe() -> None:  # no docstring: FastAPI would make it the operation's description
        return None

    return json.loads(json.dumps(app.openapi()))


def test_a_model_used_as_a_field_carries_its_docstring_into_the_client() -> None:
    """OCT-020 — the E2b shape, as FastAPI and Pydantic write it: ``Inner``, whose docstring spans lines and quotes
    ``code``, typed by the field ``Outer.inner``: flagged at ``Outer.inner -> Inner``, template, for its backticks."""
    print_section("OCT-020: Outer.inner typed with Inner")
    document = _fastapi_document(Outer)
    description = document["components"]["schemas"]["Inner"].get("description", "")
    assert "\n" in description and "``code``" in description, f"Pydantic no longer writes Inner's docstring as its multi-line description: {description!r}"
    model = _model(document)
    assert _flagged(model) == [("Outer.inner -> Inner", TEMPLATE, ("`",))], f"got {_flagged(model)}"
    print_success("Outer.inner -> Inner: template, `")


def test_a_model_held_in_a_list_or_a_union_writes_no_description() -> None:
    """OCT-021 — the same ``Inner`` held as ``list[Inner]`` and as ``Inner | None``: ``items`` that are a ``$ref``
    without a description beside it, and a ``$ref`` member of ``anyOf``, where nothing is written. Not flagged, and
    latent: the walker read the text (OCT-020 shows it flags it at a field) and found no field typed with ``Inner``."""
    print_section("OCT-021: Inner in list[Inner] and Inner | None")
    document = _fastapi_document(OuterIndirect)
    fields = document["components"]["schemas"]["OuterIndirect"]["properties"]
    assert fields["items"].get("items") == _ref("Inner"), f"FastAPI no longer writes list[Inner] as items $ref: {fields['items']}"
    assert _ref("Inner") in fields["maybe"].get("anyOf", []), f"FastAPI no longer writes Inner | None as an anyOf with a $ref: {fields['maybe']}"
    model = _model(document)
    assert _flagged(model) == [], f"got {_flagged(model)}"
    assert _latent(model) == ["Inner"], f"expected Inner latent, got {model.latent()}"
    print_success("not flagged, Inner latent")


# =============================================================================
# OCT-030…032: the real document
# =============================================================================


@functools.cache
def _real_model() -> ClientTextModel:
    """The model of ``app.openapi()``, as ``api sync`` writes it to ``frontend/src/lib/api/openapi.json`` (JSON)."""
    from backend.app.main import app  # noqa: PLC0415 — only the tests of the real document pay for importing the application

    return _model(json.loads(json.dumps(app.openapi())))


def test_no_text_of_the_real_document_breaks_the_client() -> None:
    """OCT-030 — the guard: no text of ``app.openapi()`` holds a token its form cannot carry. When red, the message
    lists every site with its location, form, forbidden tokens, an excerpt and the fix of its form."""
    print_section("OCT-030: the texts of app.openapi()")
    model = _real_model()
    flagged = [site for site in model.sites if site.forbidden]
    assert not flagged, failure_report(flagged)
    print_success(f"{len(model.sites)} sites, none holding a token its form cannot carry")


def test_the_walker_reaches_every_form_of_the_real_document() -> None:
    """OCT-031 — the presence barrier of OCT-030, which asserts an absence: each of the four forms has sites in the
    real document, and so do fields typed with a component (the path of E2b), so a walker that stopped reading cannot
    pass green. Prints, without asserting, the latent components: one field away from breaking the client."""
    print_section("OCT-031: what the walker reads in app.openapi()")
    model = _real_model()
    by_form = Counter(site.form for site in model.sites)
    assert all(by_form[form] for form in FORMS), f"no site of some forms in app.openapi(): {dict(by_form)}; the walker no longer reaches them"
    typed = [site for site in model.sites if " -> " in site.where]
    assert typed, "no field typed with a component in app.openapi(): the walker no longer follows the $ref of a field"
    latent = model.latent()
    print_info(f"{len(latent)} latent components (a description their form could not carry, typed by no field yet): {', '.join(name for name, _ in latent) or 'none'}")
    print_success(f"{dict(by_form)}, {len(typed)} fields typed with a component")


def test_the_real_document_has_only_shapes_the_rule_was_verified_on() -> None:
    """OCT-032 — every parameter, request body and response of ``app.openapi()`` is inline, and every ``$ref`` points
    into ``#/components/schemas/``: the shapes the rule was verified on. Anything else is listed, and the rule is
    verified on it before the model learns it."""
    print_section("OCT-032: the shapes of app.openapi()")
    model = _real_model()
    assert not model.unmodelled, f"shapes the rule was not verified on, {REVERIFY}:\n" + "\n".join(f"  - {shape}" for shape in model.unmodelled)
    print_success("only inline parameters, bodies and responses; every $ref in #/components/schemas/")
