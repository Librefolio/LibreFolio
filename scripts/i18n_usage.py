"""Evidence-based i18n key usage analysis.

The audit this module serves used to answer a two-valued question — *used* or
*unused* — with a one-sided rule: a key was "used" when some prefix extracted
from the source matched its start. When an interpolation sits at the **first**
segment of a template, that prefix degenerates to the bare namespace root::

    RiskResultFrame.svelte:27   const key = `risk.${prefix}.${code}`
                                             ^^^^ prefix extracted: "risk"

and ``"risk.anything".startswith("risk")`` is true for the whole namespace. No
key under it could ever be reported. The absolution was not a judgement, it was
an artefact of truncation.

This module replaces the truncation with three ideas:

1. **Resolve what is resolvable.** A ``${VAR}`` whose value is a module-level
   string constant, or whose declared type is a union of string literals, has a
   finite and *statically known* expansion. ``translatedCode(prefix: 'errors' |
   'warnings', …)`` says exactly which two families exist — the information was
   in the code all along, and the old rule threw it away.

2. **Three verdicts, not two.** A key can be ``USED`` (proven), ``DEAD``
   (proven absent) or ``UNVERIFIED`` (its family exists but its final segment is
   produced at runtime). Collapsing ``UNVERIFIED`` into ``USED`` absolves
   everything; collapsing it into ``DEAD`` condemns live keys. Both are wrong in
   the same dimension, in opposite directions.

3. **Evidence for a dynamic segment lives in its producer.** ``risk.warnings.${code}``
   is rendered from codes the *backend* emits, so the backend's string literals
   are the vocabulary that decides. A frontend-only search cannot see them, which
   is why a naive repair reports live warnings as orphans.

Note the asymmetry this exposes: ``risk.errors.*`` currently survives the old
audit only because ``levelHelpers.ts:210`` happens to spell ``risk.errors.``
literally in a second call site. ``risk.warnings`` appears nowhere in the
sources at all — the typed union is the *only* place that information exists.

The October 2026 audit (Release 2, workstream O) measured 118 live keys among the
250 this module reported dead, and the whole ``risk.*`` namespace absolved again.
The rules below close those holes; each one only ever *adds* evidence:

- **Test sources prove nothing** (R1). A key named only by a ``*.test.ts`` file is
  not used by the product, and a template in a test must not invent a family.
- **A literal is a literal** (R2). Any quoted string equal to a key proves it,
  whatever function receives it: ``translateOr($_, 'k', …)``, ``label('k')``,
  ``afterCopyKey: 'k'``, a ternary across lines, a dictionary in the backend.
- **A single literal type is a union of one** (R3), in a parameter list:
  ``translatedCode(prefix: 'errors', …)`` must expand like ``'errors' | 'warnings'``
  did, or the bare root comes back and absolves 481 keys.
- **The backend builds keys too** (R4): ``f"ns.reason.{code}"`` is a family, and its
  vocabulary includes ``camelCase``, ``UPPER_SNAKE`` and Title Case names.
- **The file that builds a family names its members** (R5): a helper called as
  ``text('compute.title')``, a ``titleKey:`` list, a map indexed in the template.
- **A suffix on a key is a key** (R6): ``${definition.displayNameKey}Full``.
- **Nested templates are templates**: ``…${$t(`risk.valueStatus.${s}`)}…`` is
  parsed with its own backticks, not by pairing them blindly.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path

USED = "used"
UNVERIFIED = "unverified"
DEAD = "dead"

# A translation call: $t(…), $_(…), t(…), _(…). We capture the argument region
# up to the first closing paren or comma-at-depth-0 so that a ternary like
# `$t(cond ? 'a.b' : 'a.c')` yields both literals instead of neither.
_CALL = re.compile(r"(?:\$t|\$_|(?<![A-Za-z0-9_])t|(?<![A-Za-z0-9_])_)\s*\(")

_KEY_LITERAL = re.compile(r"['\"]([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)['\"]")
_INTERP = re.compile(r"\$\{([^}]*)\}")

# Only templates shaped like a key are considered: word characters, dots and
# interpolations. This excludes CSS, URLs, testIds and prose, which otherwise
# contribute junk "namespaces" such as `#` or `<strong>`.
_KEY_TEMPLATE = re.compile(r"(?:[A-Za-z0-9_.]|\$\{[^}]*\})+")

_CONST_DECL = re.compile(
    r"\bconst\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=\n]*)?=\s*['\"]([^'\"]+)['\"]"
)

# A prefix chosen between two literals, e.g.
#   let keyPrefix = $derived(scope === 'simulation' ? 'risk.betaBanner.simulation' : 'risk.betaBanner');
# Both branches are finite and written down, so a template built on it resolves to
# both — exactly like a typed union, and unlike a free `string`. Without this, the
# template `${keyPrefix}.title` has no literal head at all and every key it renders
# is reported dead (review 22/09, §1.7: four live `risk.betaBanner.*` keys).
_CONDITIONAL_DECL = re.compile(r"\b(?:const|let)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=\n]*)?=\s*(?:\$derived\(\s*)?[^?;\n`]+\?\s*['\"]([^'\"\n]+)['\"]\s*:\s*['\"]([^'\"\n]+)['\"]")

# R2: a whole key written as a literal, in any quotes; a backtick string counts only
# without interpolation, which the character class already excludes.
_ANY_KEY_LITERAL = re.compile(r"""(['"`])([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)\1""")

# R1: what a test source looks like, and where sources are never searched.
_TEST_SUFFIXES = (".test.ts", ".spec.ts", ".test.js", ".spec.js")
_TEST_DIRS = frozenset({"__tests__", "__mocks__"})
_SKIPPED_DIRS = frozenset({"node_modules", "build"})
_SOURCE_GLOBS = ("*.svelte", "*.ts", "*.js")

# R3: a parameter list — parentheses followed by an optional return type and then a
# body or an arrow. A call (`f({prefix: 'x'})`) is followed by neither.
_PARAM_LIST = re.compile(r"\(([^()]*)\)\s*(?::\s*[^=;{}()]+?)?\s*(?:=>|\{)")

# R4: identifier-shaped literals of any case, Title Case phrases, and f-strings whose
# literal head is a key prefix.
_IDENT_LITERAL = re.compile(r"""['"]([A-Za-z][A-Za-z0-9_]*)['"]""")
_TITLE_PHRASE = re.compile(r"""['"]([A-Z][A-Za-z0-9]*(?: [A-Z][A-Za-z0-9]*)+)['"]""")
_BACKEND_FSTRING = re.compile(r"""(?<![A-Za-z0-9_])[rR]?[fF][rR]?(['"])([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*\.)\{""")

# R5: the words a file writes down — quoted strings, and object keys holding a literal
# (`{primal: '…'}`). A parameter annotation (`(kind: string)`) is no such key.
_QUOTED_WORD = re.compile(r"""(['"])([A-Za-z0-9_.]+)\1""")
_OBJECT_KEY = re.compile(r"""(?<![\w$.])([A-Za-z_$][\w$]*)\s*:\s*(?=['"])""")
_CONCAT = re.compile(r"""(['"])([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*\.)\1\s*\+""")

# R5, under any family: an interpolation that names a property (`step.titleKey`) or
# indexes a map (`BADGE_KEY[kind]`), with an optional literal fallback.
_MEMBER_CHAIN = re.compile(r"[A-Za-z_$][\w$]*(?:\??\.[A-Za-z_$][\w$]*)+")
_INDEXED_MAP = re.compile(r"([A-Za-z_$][\w$]*)\s*\[[^\]]*\]")

# R6: a whole key expression followed by a literal suffix.
_SUFFIX_TEMPLATE = re.compile(r"^\$\{[^}]*\}([A-Za-z0-9_]+)$")


def _resolvable_names(content: str) -> dict[str, list[str]]:
    """Every identifier whose string value(s) are written in the file.

    A ``const`` has one value; a literal conditional has two. Both are finite, so
    both can be expanded instead of ending the prefix.
    """
    names: dict[str, list[str]] = {name: [value] for name, value in _CONST_DECL.findall(content)}
    for name, first, second in _CONDITIONAL_DECL.findall(content):
        values = names.setdefault(name, [])
        values.extend(v for v in (first, second) if v not in values)
    return names


@dataclass
class Usage:
    """What the sources prove about translation keys."""

    exact: set[str] = field(default_factory=set)
    """Whole keys proven to be referenced literally (after const resolution)."""

    families: dict[str, str] = field(default_factory=dict)
    """``prefix. -> origin``. The prefix resolved; the final segment did not."""

    unverified_prefixes: dict[str, str] = field(default_factory=dict)
    """``prefix -> origin`` where an interpolation could not be resolved at all."""

    suppressed_roots: set[str] = field(default_factory=set)
    """Bare roots the old truncation would have emitted, now superseded."""

    vocabulary: set[str] = field(default_factory=set)
    """Code literals harvested from the producer (backend)."""

    family_vocab: dict[str, set[str]] = field(default_factory=dict)
    """``prefix -> rests`` named by the files that build the family (R5)."""

    suffixes: set[str] = field(default_factory=set)
    """Literal suffixes appended to a whole key expression, e.g. ``Full`` (R6)."""


def is_test_source(path: Path) -> bool:
    """True for a test, a spec, or anything under ``__tests__`` / ``__mocks__`` (R1)."""
    return path.name.endswith(_TEST_SUFFIXES) or any(part in _TEST_DIRS for part in path.parts)


def iter_source_files(src_dir: Path) -> Iterator[Path]:
    """Every product source under ``src_dir``: no dependencies, no build output, no tests."""
    for pattern in _SOURCE_GLOBS:
        for path in sorted(src_dir.rglob(pattern)):
            relative = path.relative_to(src_dir)
            if any(part in _SKIPPED_DIRS for part in relative.parts) or is_test_source(relative):
                continue
            yield path


def _parameter_literal_type(text: str, name: str) -> list[str] | None:
    """Expand ``name: 'a'`` (or ``'a' | 'b'``) when it types a function parameter."""
    member = re.compile(
        rf"(?<![\w$.]){re.escape(name)}\s*\??\s*:\s*((?:'[^']*'|\"[^\"]*\")(?:\s*\|\s*(?:'[^']*'|\"[^\"]*\"))*)\s*(?=[,=]|$)"
    )
    for params in _PARAM_LIST.finditer(text):
        m = member.search(params.group(1).strip())
        if m:
            return re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
    return None


def _union_members(text: str, name: str) -> list[str] | None:
    """Expand ``name: 'a' | 'b'`` — a typed union — into its members.

    Returns ``None`` when ``name`` has no string-literal union type, which is the
    honest answer for ``code: string | null | undefined``: the set is not finite.
    A single literal (``prefix: 'errors'``) is a union of one, but only where it
    types a parameter: as an object property it is a value, not a type (R3).
    """
    pattern = re.compile(
        rf"\b{re.escape(name)}\s*:\s*((?:'[^']*'|\"[^\"]*\")(?:\s*\|\s*(?:'[^']*'|\"[^\"]*\"))+)"
    )
    m = pattern.search(text)
    if m:
        return re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
    return _parameter_literal_type(text, name)


def _expand(template: str, consts: dict[str, list[str]], text: str) -> tuple[list[str], bool]:
    """Expand a template literal into concrete prefixes.

    Returns ``(candidates, trailing_only)``. ``trailing_only`` is True when every
    unresolved interpolation sits at the very end — the case where the prefix is
    known and only the last segment is produced at runtime.
    """
    parts = _INTERP.split(template)
    literals, names = parts[0::2], parts[1::2]

    resolved: list[list[str] | None] = []
    for name in names:
        key = name.strip()
        if key in consts:
            resolved.append(list(consts[key]))
            continue
        members = _union_members(text, key.split(".")[0]) if key else None
        resolved.append(members)

    last_unresolved = max(
        (i for i, r in enumerate(resolved) if r is None), default=-1
    )
    if last_unresolved == -1:
        trailing_only = True
        cut = len(names)
    else:
        # Everything after the last unresolved interpolation must be empty for
        # the prefix to be a genuine prefix.
        trailing_only = all(r is not None for r in resolved[:last_unresolved]) and not "".join(
            literals[last_unresolved + 1:]
        ).strip()
        cut = last_unresolved

    candidates = [literals[0]]
    for i in range(cut):
        options = resolved[i]
        if options is None:
            return [], False
        candidates = [c + opt + literals[i + 1] for c in candidates for opt in options]

    return candidates, trailing_only


def _argument_region(content: str, start: int) -> str:
    """Return the text of a call's argument list, balanced on parentheses."""
    depth, i = 0, start
    while i < len(content):
        ch = content[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return content[start + 1: i]
        i += 1
    return content[start: start + 400]


def _skip_string(content: str, i: int) -> int:
    """Index just past the quoted string opening at ``i``."""
    quote, j, n = content[i], i + 1, len(content)
    while j < n and content[j] != quote and content[j] != "\n":
        j += 2 if content[j] == "\\" else 1
    return j + 1


def _interpolation_end(content: str, i: int) -> int | None:
    """Index just past the ``}`` closing an interpolation whose body starts at ``i``."""
    depth, n = 1, len(content)
    while i < n:
        ch = content[i]
        if ch == "`":
            end = _template_end(content, i)
            if end is None:
                return None
            i = end + 1
            continue
        if ch in "'\"":
            i = _skip_string(content, i)
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def _template_end(content: str, start: int) -> int | None:
    """Index of the backtick closing the template opened at ``start``, nested ones included."""
    i, n = start + 1, len(content)
    while i < n:
        ch = content[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "`":
            return i
        if content.startswith("${", i):
            end = _interpolation_end(content, i + 2)
            if end is None:
                return None
            i = end
            continue
        i += 1
    return None


def _iter_key_templates(content: str) -> Iterator[tuple[int, str]]:
    """Every key-shaped template literal with an interpolation, nested ones included.

    Each backtick is tried as an opening and parsed with its own interpolations, so
    a template inside another template's ``${…}`` is found exactly; a closing
    backtick tried as an opening yields text that is never key-shaped.
    """
    for m in re.finditer("`", content):
        start = m.start()
        if start and content[start - 1] == "\\":
            continue
        end = _template_end(content, start)
        if end is None:
            continue
        body = content[start + 1: end]
        if "${" in body and _KEY_TEMPLATE.fullmatch(body):
            yield start, body


def _matching_brace(content: str, open_index: int) -> int:
    """Index of the ``}`` matching the ``{`` at ``open_index`` (strings skipped)."""
    depth, i, n = 0, open_index, len(content)
    while i < n:
        ch = content[i]
        if ch in "'\"`":
            i = _skip_string(content, i) if ch != "`" else (_template_end(content, i) or i) + 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return n


class _FileContext:
    """The words one source file writes down, computed once and on demand (R5)."""

    def __init__(self, content: str) -> None:
        self.content = content
        self._words: set[str] | None = None
        self._narrow: set[str] | None = None

    def words(self) -> set[str]:
        if self._words is None:
            self._words = {m.group(2) for m in _QUOTED_WORD.finditer(self.content)} | set(_OBJECT_KEY.findall(self.content))
        return self._words

    def narrow_rests(self) -> set[str]:
        """Words, plus ``head.word`` for every key-template head (``help.${key}``)."""
        if self._narrow is None:
            heads = {body.split("${", 1)[0] for _, body in _iter_key_templates(self.content)}
            heads = {h for h in heads if h.endswith(".")}
            words = self.words()
            self._narrow = words | {h + w for h in heads for w in words if "." not in w}
        return self._narrow

    def property_values(self, prop: str) -> set[str]:
        return set(re.findall(rf"(?<![\w$]){re.escape(prop)}\s*:\s*['\"]([^'\"]+)['\"]", self.content))

    def map_values(self, name: str) -> set[str]:
        m = re.search(rf"(?<![\w$.]){re.escape(name)}\s*(?::[^=\n]*)?=\s*\{{", self.content)
        if not m:
            return set()
        end = _matching_brace(self.content, m.end() - 1)
        return set(re.findall(r":\s*['\"]([^'\"]+)['\"]", self.content[m.end(): end]))


def _directed_values(expression: str, ctx: _FileContext) -> set[str]:
    """Values an interpolation can take, read from what it names (R5, any family).

    ``step.titleKey`` → every ``titleKey:`` value in the file; ``MAP[kind] ?? 'x'`` →
    the values of ``MAP`` and the literal fallback. A call (``sectorKey(e.name)``)
    transforms what it reads, so it names nothing.
    """
    parts = re.split(r"\?\?|\|\|", expression, maxsplit=1)
    main = parts[0].strip()
    fallback = parts[1] if len(parts) > 1 else ""
    values = set(re.findall(r"['\"]([A-Za-z0-9_.]+)['\"]", fallback))
    indexed = _INDEXED_MAP.fullmatch(main)
    if indexed:
        values |= ctx.map_values(indexed.group(1))
    elif _MEMBER_CHAIN.fullmatch(main):
        values |= ctx.property_values(re.split(r"\??\.", main)[-1])
    return values


def _template_verdict(
    template: str, consts: dict[str, list[str]], text: str
) -> tuple[list[str], bool, bool]:
    """Resolve one key template into ``(candidates, trailing_only, fully_resolved)``."""
    candidates, trailing_only = _expand(template, consts, text)
    unresolved = [u.strip() for u in _INTERP.findall(template)]
    fully_resolved = not any(
        u not in consts and _union_members(text, u.split(".")[0]) is None for u in unresolved
    )
    return candidates, trailing_only, fully_resolved


def _record_family(usage: Usage, prefix: str, origin: str, rests: set[str]) -> None:
    usage.families.setdefault(prefix, origin)
    usage.family_vocab.setdefault(prefix, set()).update(rests)


def _family_rests(prefix: str, last_expression: str, ctx: _FileContext | None) -> set[str]:
    """The members the building file names for a family (R5)."""
    if ctx is None:
        return set()
    rests = _directed_values(last_expression, ctx)
    if _is_narrow(prefix):
        rests |= ctx.narrow_rests()
    return rests


def _keep_union_family(
    usage: Usage, template: str, consts: dict[str, list[str]], text: str, origin: str, ctx: _FileContext | None
) -> None:
    """Keep the family of a template whose last segment was resolved by a union.

    A union is found by its name anywhere in the file, so it may type another
    function's parameter: `${kind}` resolved by `kind: 'long' | 'short'` of a date
    helper. The expansion stands, and the family stays too, so that the members the
    runtime really produces are never condemned.
    """
    if not template.endswith("}"):
        return
    cut = template.rfind("${")
    last = template[cut + 2: -1].strip()
    if last in consts:
        return
    prefixes, _trailing = _expand(template[:cut], consts, text)
    for prefix in prefixes:
        if "." in prefix:
            _record_family(usage, prefix, origin, _family_rests(prefix, last, ctx))


def _record_candidates(
    usage: Usage, candidates: list[str], trailing_only: bool, last_expression: str, origin: str, ctx: _FileContext | None
) -> None:
    """A trailing interpolation makes a family; a mid-template one, an unverified prefix."""
    for cand in candidates:
        if "." not in cand:
            continue
        if trailing_only:
            # A camelCase continuation (`historyDays${day}`) keeps its prefix as written.
            _record_family(usage, cand, origin, _family_rests(cand, last_expression, ctx))
        else:
            usage.unverified_prefixes.setdefault(cand.rstrip("."), origin)


def _record_template(
    usage: Usage, template: str, consts: dict[str, list[str]], text: str, origin: str, ctx: _FileContext | None = None
) -> None:
    """Fold one template literal into the accumulated evidence."""
    candidates, trailing_only, fully_resolved = _template_verdict(template, consts, text)
    head = template.split("${", 1)[0].rstrip(".")

    # R6: `${expr}Suffix` appends a suffix to a whole key — unless `expr` resolves
    # (`${P}intro` with `const P = 'ns.step.'` is an ordinary resolved key).
    suffix = _SUFFIX_TEMPLATE.match(template)
    if suffix and not fully_resolved:
        usage.suffixes.add(suffix.group(1))
        return

    if not candidates:
        if head and "." in head:
            usage.unverified_prefixes.setdefault(head, origin)
        return

    if fully_resolved:
        usage.exact.update(c for c in candidates if "." in c)
        _keep_union_family(usage, template, consts, text, origin, ctx)
        return

    _record_candidates(usage, candidates, trailing_only, _INTERP.findall(template)[-1], origin, ctx)

    # The bare root the old truncation would have produced is now superseded by
    # the expansion above — but only when the expansion produced something usable.
    if head and "." not in head and any("." in c for c in candidates):
        usage.suppressed_roots.add(head)


def collect_from_source(src_dir: Path) -> Usage:
    """Scan the frontend's product sources (never its tests) for key evidence."""
    usage = Usage()

    for path in iter_source_files(src_dir):
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue

        consts = _resolvable_names(content)
        ctx = _FileContext(content)

        # Literals inside a translation call, including every branch of a
        # ternary — `$t(cond ? 'a.b' : 'a.c')` must yield both, not neither.
        for call in _CALL.finditer(content):
            region = _argument_region(content, call.end() - 1)
            usage.exact.update(m.group(1) for m in _KEY_LITERAL.finditer(region))

        # R2: a whole key written anywhere is a reference, whoever receives it.
        usage.exact.update(m.group(2) for m in _ANY_KEY_LITERAL.finditer(content))

        # Templates are scanned over the whole file, not only inside calls:
        # the shape that started all of this assigns the key to a variable
        # first (`const key = \`risk.${prefix}.${code}\``) and translates it
        # on the next line. Nested templates are parsed, not paired blindly.
        for start, template in _iter_key_templates(content):
            line = content.count("\n", 0, start) + 1
            _record_template(usage, template, consts, content, f"{path.name}:{line}", ctx)

        # `'ns.cat.' + code` is a family too.
        for m in _CONCAT.finditer(content):
            prefix = m.group(2)
            rests = ctx.narrow_rests() if _is_narrow(prefix) else set()
            _record_family(usage, prefix, f"{path.name}:{content.count(chr(10), 0, m.start()) + 1}", rests)

    return usage


def _python_sources(backend_dir: Path) -> Iterator[tuple[Path, str]]:
    if not backend_dir.is_dir():
        return
    for path in sorted(backend_dir.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except OSError:
            continue


def harvest_vocabulary(backend_dir: Path) -> set[str]:
    """Collect identifier-shaped string literals emitted by the producer.

    These are the ``code`` values that become the final segment of keys such as
    ``risk.warnings.${code}``. Absence here is the only evidence that can tell a
    dead dynamic key from one merely awaiting its trigger — and it is deliberately
    permissive: a vocabulary can only ever prove presence. Any case counts
    (``flat_series``, ``deeperTechnical``, ``FETCH_ERROR``), and a Title Case name
    counts without its spaces (``"Health Care"`` → ``HealthCare``) (R4).
    """
    vocab: set[str] = set()
    for _path, text in _python_sources(backend_dir):
        vocab.update(_IDENT_LITERAL.findall(text))
        vocab.update(phrase.replace(" ", "") for phrase in _TITLE_PHRASE.findall(text))
        # Dotted codes too (`allocation.duplicate_id`): the rest of a key under a family.
        vocab.update(m.group(2) for m in _ANY_KEY_LITERAL.finditer(text) if m.group(1) != "`")
    return vocab


def harvest_backend_keys(backend_dir: Path) -> set[str]:
    """Whole keys the backend writes as literals — fields, dictionaries, constants (R2)."""
    keys: set[str] = set()
    for _path, text in _python_sources(backend_dir):
        keys.update(m.group(2) for m in _ANY_KEY_LITERAL.finditer(text) if m.group(1) != "`")
    return keys


def harvest_backend_families(backend_dir: Path) -> dict[str, str]:
    """Key prefixes the backend completes at runtime: ``f"ns.reason.{code}"`` (R4)."""
    families: dict[str, str] = {}
    for path, text in _python_sources(backend_dir):
        for m in _BACKEND_FSTRING.finditer(text):
            families.setdefault(m.group(2), f"{path.name}:{text.count(chr(10), 0, m.start()) + 1}")
    return families


def phantom_families(families: Mapping[str, str], keys: Iterable[str]) -> list[str]:
    """Families with no catalogue key under them: built at runtime, rendered from nothing (R7)."""
    key_list = list(keys)
    return sorted(prefix for prefix in families if not any(k.startswith(prefix) for k in key_list))


def _camel_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _is_narrow(family: str) -> bool:
    """A family two segments deep (``ns.sub.``) or a camelCase continuation
    (``ns.sched.historyDays``): its own file is a fair witness for its members."""
    return family.count(".") >= 2 or not family.endswith(".")


def _family_verdict(key: str, usage: Usage) -> str | None:
    """Verdict from a resolved dynamic family, or ``None`` when none applies.

    Under a family a single-segment rest is never ``DEAD``: the runtime produces it.
    A dotted rest counts as under the family only when the family is narrow — under
    ``importWizard.`` it would hide every dead nested key — unless the file that
    builds the family names it. The file, or the producer's vocabulary, promotes a
    rest to ``USED``.
    """
    matched = False
    for family in usage.families:
        if not key.startswith(family) or len(key) == len(family):
            continue
        rest = key[len(family):]
        if rest in usage.family_vocab.get(family, ()) or rest in usage.vocabulary:
            return USED
        if "." in rest:
            matched = matched or _is_narrow(family)
            continue
        matched = True
        if rest in usage.vocabulary or _camel_to_snake(rest) in usage.vocabulary:
            return USED
    return UNVERIFIED if matched else None


def classify(key: str, usage: Usage, legacy_prefixes: set[str] | None = None) -> str:
    """Return ``USED``, ``UNVERIFIED`` or ``DEAD`` for one catalogue key.

    A legacy prefix — the truncated ``prefix.${`` of the old regex scan — is no longer
    proof of use: it only keeps a key out of ``DEAD``. Measured on the October 2026
    tree, every key it used to absolve is covered by the evidence above, so the
    demotion condemns nothing and stops hiding dead keys (§5.3).
    """
    if key in usage.exact:
        return USED

    for suffix in usage.suffixes:
        if key.endswith(suffix) and key[: -len(suffix)] in usage.exact:
            return USED

    verdict = _family_verdict(key, usage)
    if verdict == USED:
        return USED

    legacy = any(prefix not in usage.suppressed_roots and key.startswith(prefix) for prefix in legacy_prefixes or ())
    if verdict is not None or legacy:
        return UNVERIFIED

    for prefix in usage.unverified_prefixes:
        if key == prefix or key.startswith(prefix + "."):
            return UNVERIFIED

    return DEAD
