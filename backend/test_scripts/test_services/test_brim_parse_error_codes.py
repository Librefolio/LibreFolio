"""Every ``BRIMParseError`` a BRIM plugin raises carries a code the import wizard translates (lot W5-6, backlog E-21).

C-70b made a failed parse answer ``400 {code: "parse_failed", plugin_code, plugin_name, reason: {code, message, context}}``
where ``reason.code`` and ``reason.context`` come from ``BRIMParseError.details["code"]`` / ``details["context"]`` and the
wizard translates ``importWizard.parseRefusal.<code>`` with the context as ICU values. A raise without a code shows the
user an English sentence. These tests keep the plugins honest, **statically** (``ast`` over every ``.py`` under
``backend/app/services/brim_providers/``), so a new plugin or a new raise is caught without anybody remembering this file:

1. every ``BRIMParseError(...)`` call has ``details={"code": …}`` (a dict literal with the constant key ``"code"``; the value
   may be any expression, e.g. a refusal's code); a ``"context"`` that is a dict literal has string-constant keys.
2. a coded raise is not swallowed: inside a ``try`` body a broad ``except Exception`` (or a bare ``except``) must come
   after an ``except BRIMParseError`` that re-raises.
3. every constant code used has a non-empty ``importWizard.parseRefusal.<code>`` in the four source catalogues
   (``frontend/src/lib/i18n/importWizard/{en,it,fr,es}.json``).
4. the placeholders of the English text are all supplied by the ``context`` of the raise sites of that code (``plugin_name``
   is always allowed: the wizard adds it), and it/fr/es use exactly the placeholder names of English.
5. behaviour: the generic CSV and DEGIRO really raise the codes (and contexts) the catalogue expects.

``BRIMSetRequiredError`` is a separate path (report sets) and is not looked at. No count of raises is asserted anywhere:
the number of raises must not matter, every offender is named by ``file:line``.

Pure: reads source files and the catalogues, writes only under ``tmp_path``; no database, no server.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import pytest

from backend.app.services.brim.brim_provider import BRIMParseError
from backend.app.services.brim.registry import BRIMProviderRegistry

REPO_ROOT = Path(__file__).resolve().parents[3]
PROVIDERS_DIR = REPO_ROOT / "backend" / "app" / "services" / "brim_providers"
I18N_DIR = REPO_ROOT / "frontend" / "src" / "lib" / "i18n" / "importWizard"
LANGUAGES = ("en", "it", "fr", "es")
REFUSAL_PREFIX = ("importWizard", "parseRefusal")
#: The wizard adds ``plugin_name`` to the ICU values whenever the reason names a plugin, whatever the plugin's context holds.
ALWAYS_ALLOWED = {"plugin_name"}
ERROR_NAME = "BRIMParseError"
BROAD_NAMES = {"Exception", "BaseException"}


# =============================================================================
# STATIC SCAN
# =============================================================================


class RaiseSite:
    """One call ``BRIMParseError(...)``: where it is and what ``details`` it gives."""

    def __init__(self, path: Path, call: ast.Call):
        self.path = path
        self.call = call
        self.line = call.lineno
        self.where = f"{path.relative_to(REPO_ROOT)}:{call.lineno}"
        self.details = self._details()

    def _details(self) -> Optional[ast.expr]:
        for keyword in self.call.keywords:
            if keyword.arg == "details":
                return keyword.value
        if len(self.call.args) >= 2:
            return self.call.args[1]
        return None

    def _entry(self, key: str) -> Optional[ast.expr]:
        if not isinstance(self.details, ast.Dict):
            return None
        for k, v in zip(self.details.keys, self.details.values, strict=True):
            if isinstance(k, ast.Constant) and k.value == key:
                return v
        return None

    @property
    def has_code(self) -> bool:
        return self._entry("code") is not None

    @property
    def constant_code(self) -> Optional[str]:
        value = self._entry("code")
        return value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None

    @property
    def context(self) -> Optional[ast.expr]:
        return self._entry("context")

    @property
    def context_keys(self) -> Optional[Set[str]]:
        """The keys of a dict-literal ``context``; ``None`` when it is not a dict literal (unknowable statically)."""
        ctx = self.context
        if ctx is None:
            return set()
        if not isinstance(ctx, ast.Dict):
            return None
        return {k.value for k in ctx.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}

    def problem(self) -> Optional[str]:
        if self.details is None:
            return "no details= at all"
        if not isinstance(self.details, ast.Dict):
            return "details= is not a dict literal"
        if not self.has_code:
            return 'details has no "code" key'
        ctx = self.context
        if isinstance(ctx, ast.Dict):
            bad = [k for k in ctx.keys if not (isinstance(k, ast.Constant) and isinstance(k.value, str))]
            if bad:
                return 'details["context"] dict literal has a key that is not a string constant'
        return None


def _is_error_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (isinstance(func, ast.Name) and func.id == ERROR_NAME) or (isinstance(func, ast.Attribute) and func.attr == ERROR_NAME)


def _provider_files() -> List[Path]:
    files = sorted(p for p in PROVIDERS_DIR.rglob("*.py") if "__pycache__" not in p.parts)
    assert files, f"no plugin source found under {PROVIDERS_DIR}"
    return files


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def all_sites() -> List[RaiseSite]:
    sites: List[RaiseSite] = []
    for path in _provider_files():
        for node in ast.walk(_parse(path)):
            if _is_error_call(node):
                sites.append(RaiseSite(path, node))  # type: ignore[arg-type]
    return sites


def _walk_no_scopes(nodes: List[ast.stmt]) -> Iterator[ast.AST]:
    """Every node under ``nodes`` without entering a nested function, lambda or class (a raise there is not this try's)."""
    stack: List[ast.AST] = list(nodes)
    while stack:
        node = stack.pop()
        yield node
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            stack.append(child)


def _handler_names(handler: ast.ExceptHandler) -> Set[str]:
    node = handler.type
    if node is None:
        return {"<bare>"}
    elts = node.elts if isinstance(node, ast.Tuple) else [node]
    names: Set[str] = set()
    for elt in elts:
        if isinstance(elt, ast.Name):
            names.add(elt.id)
        elif isinstance(elt, ast.Attribute):
            names.add(elt.attr)
    return names


def _reraises(handler: ast.ExceptHandler) -> bool:
    return any(isinstance(n, ast.Raise) for n in _walk_no_scopes(handler.body))


# =============================================================================
# CATALOGUES + ICU
# =============================================================================


def _catalogue(lang: str) -> Dict[str, Any]:
    return json.loads((I18N_DIR / f"{lang}.json").read_text(encoding="utf-8"))


def _refusal_text(lang: str, code: str) -> Optional[str]:
    node: Any = _catalogue(lang)
    for part in (*REFUSAL_PREFIX, code):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, str) and node.strip() else None


def _matching_brace(text: str, start: int) -> int:
    depth = 0
    i = start
    while i < len(text):
        ch = text[i]
        if ch == "'" and i + 1 < len(text) and text[i + 1] in "{}":
            end = text.find("'", i + 1)
            i = end if end != -1 else len(text)
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def icu_placeholders(text: str) -> Set[str]:
    """The argument names of an ICU message: the identifier before the first comma / closing brace of each ``{...}``.

    The branches of ``plural`` / ``select`` are read as messages of their own (``{count, plural, one {… {columns} …}}``
    needs ``columns`` too); ``#`` is not a name. An apostrophe quotes only when it precedes a brace.
    """
    names: Set[str] = set()
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "'" and i + 1 < len(text) and text[i + 1] in "{}":
            end = text.find("'", i + 1)
            i = (end if end != -1 else len(text)) + 1
            continue
        if ch == "{":
            close = _matching_brace(text, i)
            if close == -1:
                names.add(text[i + 1 :].strip())
                break
            inner = text[i + 1 : close]
            head, comma, rest = inner.partition(",")
            names.add(head.strip())
            if comma:
                kind, comma2, branches = rest.partition(",")
                if comma2 and kind.strip() in {"plural", "select", "selectordinal"}:
                    j = 0
                    while j < len(branches):
                        if branches[j] == "{":
                            end = _matching_brace(branches, j)
                            if end == -1:
                                break
                            names |= icu_placeholders(branches[j + 1 : end])
                            j = end
                        j += 1
            i = close + 1
            continue
        i += 1
    names.discard("")
    return names


def _constant_codes() -> Dict[str, List[RaiseSite]]:
    codes: Dict[str, List[RaiseSite]] = {}
    for site in all_sites():
        code = site.constant_code
        if code is not None:
            codes.setdefault(code, []).append(site)
    return codes


# =============================================================================
# 1. EVERY RAISE IS CODED
# =============================================================================


def test_every_parse_error_carries_a_code():
    offenders = [f"{s.where}: {s.problem()}" for s in all_sites() if s.problem()]
    assert not offenders, "BRIMParseError raised without a coded details= (the user would read English):\n  " + "\n  ".join(offenders)


# =============================================================================
# 2. A CODED RAISE IS NOT SWALLOWED
# =============================================================================


def swallowed_raises(tree: ast.AST) -> List[Tuple[int, List[int]]]:
    """``(line of the broad handler, lines of the BRIMParseError raises in that try body)`` for every swallowing ``try``."""
    found: List[Tuple[int, List[int]]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        raises = [n for n in _walk_no_scopes(node.body) if isinstance(n, ast.Raise) and n.exc is not None and _is_error_call(n.exc)]
        if not raises:
            continue
        for handler in node.handlers:
            names = _handler_names(handler)
            if ERROR_NAME in names and _reraises(handler):
                break  # the coded error passes through before any broad handler sees it
            if names & (BROAD_NAMES | {"<bare>"}):
                found.append((handler.lineno, sorted(r.lineno for r in raises)))
                break
    return found


def test_coded_parse_errors_are_not_swallowed_by_a_broad_except():
    offenders: List[str] = []
    for path in _provider_files():
        rel = path.relative_to(REPO_ROOT)
        for handler_line, raise_lines in swallowed_raises(_parse(path)):
            offenders.append(f"{rel}:{handler_line}: broad except would swallow the BRIMParseError raised at line(s) {raise_lines} (add `except BRIMParseError: raise` before it)")
    assert not offenders, "a coded BRIMParseError is turned into another error by a broad except:\n  " + "\n  ".join(offenders)


def test_swallow_detector_sees_what_it_should():
    """The detector is not vacuous: it flags a broad handler over a raise, and accepts the guarded and the narrow forms."""
    bad = "try:\n    raise BRIMParseError('x', details={'code': 'c'})\nexcept Exception as e:\n    raise BRIMParseError('y') from e\n"
    bare = "try:\n    raise BRIMParseError('x', details={'code': 'c'})\nexcept:\n    pass\n"
    guarded = "try:\n    raise BRIMParseError('x', details={'code': 'c'})\nexcept BRIMParseError:\n    raise\nexcept Exception as e:\n    raise BRIMParseError('y') from e\n"
    guarded_late = "try:\n    raise BRIMParseError('x', details={'code': 'c'})\nexcept Exception:\n    pass\nexcept BRIMParseError:\n    raise\n"
    narrow = "try:\n    raise BRIMParseError('x', details={'code': 'c'})\nexcept ValueError:\n    pass\n"
    in_handler = "try:\n    pass\nexcept Exception as e:\n    raise BRIMParseError('x', details={'code': 'c'}) from e\n"
    assert swallowed_raises(ast.parse(bad)) == [(3, [2])]
    assert swallowed_raises(ast.parse(bare)) == [(3, [2])]
    assert swallowed_raises(ast.parse(guarded_late)) == [(3, [2])]
    assert swallowed_raises(ast.parse(guarded)) == []
    assert swallowed_raises(ast.parse(narrow)) == []
    assert swallowed_raises(ast.parse(in_handler)) == []


# =============================================================================
# 3. EVERY CODE HAS ITS TEXT IN THE FOUR CATALOGUES
# =============================================================================


def test_every_code_has_a_text_in_all_four_catalogues():
    codes = _constant_codes()
    assert codes, "no constant code found at all: nothing to translate (is the scan broken, or is nothing coded yet?)"
    missing: List[str] = []
    for code in sorted(codes):
        sites = ", ".join(s.where for s in codes[code])
        for lang in LANGUAGES:
            if _refusal_text(lang, code) is None:
                missing.append(f"{'.'.join(REFUSAL_PREFIX)}.{code} missing or empty in importWizard/{lang}.json (raised at {sites})")
    assert not missing, "codes without a translation:\n  " + "\n  ".join(missing)


# =============================================================================
# 4. PLACEHOLDERS AGREE
# =============================================================================


def test_english_placeholders_are_supplied_by_the_context_of_the_raise_sites():
    problems: List[str] = []
    for code, sites in sorted(_constant_codes().items()):
        text = _refusal_text("en", code)
        if text is None:
            continue  # reported by the catalogue test
        provided: Set[str] = set(ALWAYS_ALLOWED)
        unknowable = False
        for site in sites:
            keys = site.context_keys
            if keys is None:
                unknowable = True
            else:
                provided |= keys
        if unknowable:
            continue  # a context built elsewhere: not decidable statically, stay conservative
        extra = icu_placeholders(text) - provided
        if extra:
            where = ", ".join(s.where for s in sites)
            problems.append(f"{code}: the English text uses {sorted(extra)} but no raise site supplies it in context (sites: {where}; supplied: {sorted(provided - ALWAYS_ALLOWED)})")
    assert not problems, "placeholders the wizard cannot fill:\n  " + "\n  ".join(problems)


def test_translations_use_the_same_placeholders_as_english():
    problems: List[str] = []
    for code in sorted(_constant_codes()):
        english = _refusal_text("en", code)
        if english is None:
            continue
        want = icu_placeholders(english)
        for lang in LANGUAGES[1:]:
            text = _refusal_text(lang, code)
            if text is None:
                continue  # reported by the catalogue test
            got = icu_placeholders(text)
            if got != want:
                problems.append(f"{code} [{lang}]: placeholders {sorted(got)} != English {sorted(want)}")
    assert not problems, "translations whose placeholders differ from English:\n  " + "\n  ".join(problems)


def test_icu_placeholder_parser():
    """The parser the two tests above lean on: plural branches count, ``#`` and plain text do not."""
    assert icu_placeholders("The {plugin_name} plugin reads only .csv files.") == {"plugin_name"}
    assert icu_placeholders("{count, plural, one {Column {columns} not found.} other {Columns {columns} not found.}}") == {"count", "columns"}
    assert icu_placeholders("{n, plural, one {# row} other {# rows}}") == {"n"}
    assert icu_placeholders("Scalable's own export, no argument.") == set()
    assert icu_placeholders("{kind, select, a {x {name}} other {y}}") == {"kind", "name"}


# =============================================================================
# 5. BEHAVIOUR: THE REAL PLUGINS RAISE THE CODES
# =============================================================================


def _plugin(code: str):
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(code)
    assert plugin is not None, f"plugin {code} is not registered"
    return plugin


def _parse_error(code: str, path: Path) -> BRIMParseError:
    with pytest.raises(BRIMParseError) as info:
        _plugin(code).parse(path, 1)
    return info.value


@pytest.mark.parametrize(
    "header,column",
    [
        ("type,amount,currency", "date"),
        ("date,amount,currency", "type"),
    ],
)
def test_generic_csv_missing_required_column_is_coded(tmp_path: Path, header: str, column: str):
    path = tmp_path / "generic_missing_column.csv"
    path.write_text(f"{header}\nBUY,10,EUR\n", encoding="utf-8")
    err = _parse_error("broker_generic_csv", path)
    assert err.details.get("code") == "missing_columns"
    assert err.details.get("context") == {"columns": column, "count": 1}
    assert "headers" in err.details, "the old details['headers'] key must stay (diagnostics)"


def test_degiro_empty_file_is_coded(tmp_path: Path):
    path = tmp_path / "degiro_empty.csv"
    path.write_text("", encoding="utf-8")
    err = _parse_error("broker_degiro", path)
    assert err.details.get("code") == "file_empty"


def test_degiro_other_csv_is_coded(tmp_path: Path):
    path = tmp_path / "degiro_other.csv"
    path.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    err = _parse_error("broker_degiro", path)
    assert err.details.get("code") == "degiro_not_account_statement"
