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
"""

from __future__ import annotations

import re
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
_TEMPLATE = re.compile(r"`([^`]*)`")
_INTERP = re.compile(r"\$\{([^}]*)\}")

# Only templates shaped like a key are considered: word characters, dots and
# interpolations. This excludes CSS, URLs, testIds and prose, which otherwise
# contribute junk "namespaces" such as `#` or `<strong>`.
_KEY_TEMPLATE = re.compile(r"(?:[A-Za-z0-9_.]|\$\{[^}]*\})+")

_CONST_DECL = re.compile(
    r"\bconst\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=\n]*)?=\s*['\"]([^'\"]+)['\"]"
)

# An identifier-ish literal: the shape a backend "code" takes.
_CODE_LITERAL = re.compile(r"['\"]([a-z][a-z0-9]*(?:_[a-z0-9]+)*)['\"]")


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


def _union_members(text: str, name: str) -> list[str] | None:
    """Expand ``name: 'a' | 'b'`` — a typed union — into its members.

    Returns ``None`` when ``name`` has no string-literal union type, which is the
    honest answer for ``code: string | null | undefined``: the set is not finite.
    """
    pattern = re.compile(
        rf"\b{re.escape(name)}\s*:\s*((?:'[^']*'|\"[^\"]*\")(?:\s*\|\s*(?:'[^']*'|\"[^\"]*\"))+)"
    )
    m = pattern.search(text)
    if not m:
        return None
    return re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))


def _expand(template: str, consts: dict[str, str], text: str) -> tuple[list[str], bool]:
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
            resolved.append([consts[key]])
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


def _template_verdict(
    template: str, consts: dict[str, str], text: str
) -> tuple[list[str], bool, bool]:
    """Resolve one key template into ``(candidates, trailing_only, fully_resolved)``."""
    candidates, trailing_only = _expand(template, consts, text)
    unresolved = [u.strip() for u in _INTERP.findall(template)]
    fully_resolved = not any(
        u not in consts and _union_members(text, u.split(".")[0]) is None for u in unresolved
    )
    return candidates, trailing_only, fully_resolved


def _record_template(usage: Usage, template: str, consts: dict[str, str], text: str, origin: str) -> None:
    """Fold one template literal into the accumulated evidence."""
    candidates, trailing_only, fully_resolved = _template_verdict(template, consts, text)
    head = template.split("${", 1)[0].rstrip(".")

    if not candidates:
        if head and "." in head:
            usage.unverified_prefixes.setdefault(head, origin)
        return

    if fully_resolved:
        usage.exact.update(c for c in candidates if "." in c)
        return

    for cand in candidates:
        if "." not in cand:
            continue
        prefix = cand if cand.endswith(".") else cand + "."
        if trailing_only:
            usage.families.setdefault(prefix, origin)
        else:
            usage.unverified_prefixes.setdefault(prefix.rstrip("."), origin)

    # The bare root the old truncation would have produced is now superseded by
    # the expansion above — but only when the expansion produced something usable.
    if head and "." not in head and any("." in c for c in candidates):
        usage.suppressed_roots.add(head)


def collect_from_source(src_dir: Path) -> Usage:
    """Scan the frontend for translation-key evidence."""
    usage = Usage()

    for ext in ("*.svelte", "*.ts", "*.js"):
        for path in src_dir.rglob(ext):
            sp = str(path)
            if "node_modules" in sp or "/build/" in sp:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                continue

            consts = dict(_CONST_DECL.findall(content))

            # Literals inside a translation call, including every branch of a
            # ternary — `$t(cond ? 'a.b' : 'a.c')` must yield both, not neither.
            for call in _CALL.finditer(content):
                region = _argument_region(content, call.end() - 1)
                usage.exact.update(m.group(1) for m in _KEY_LITERAL.finditer(region))

            # Templates are scanned over the whole file, not only inside calls:
            # the shape that started all of this assigns the key to a variable
            # first (`const key = \`risk.${prefix}.${code}\``) and translates it
            # on the next line.
            for tm in _TEMPLATE.finditer(content):
                template = tm.group(1)
                if "${" not in template or not _KEY_TEMPLATE.fullmatch(template):
                    continue
                line = content.count("\n", 0, tm.start()) + 1
                _record_template(usage, template, consts, content, f"{path.name}:{line}")

    return usage


def harvest_vocabulary(backend_dir: Path) -> set[str]:
    """Collect identifier-shaped string literals emitted by the producer.

    These are the ``code`` values that become the final segment of keys such as
    ``risk.warnings.${code}``. Absence here is the only evidence that can tell a
    dead dynamic key from one merely awaiting its trigger — and it is deliberately
    permissive: a vocabulary can only ever prove presence.
    """
    vocab: set[str] = set()
    if not backend_dir.is_dir():
        return vocab
    for path in backend_dir.rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        try:
            vocab.update(_CODE_LITERAL.findall(path.read_text(encoding="utf-8")))
        except OSError:
            continue
    return vocab


def _camel_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _family_verdict(key: str, usage: Usage) -> str | None:
    """Verdict from a resolved dynamic family, or ``None`` when none applies."""
    for family in usage.families:
        if not key.startswith(family):
            continue
        leaf = key[len(family):]
        if "." in leaf:
            continue
        if leaf in usage.vocabulary or _camel_to_snake(leaf) in usage.vocabulary:
            return USED
        return UNVERIFIED
    return None


def classify(key: str, usage: Usage, legacy_prefixes: set[str] | None = None) -> str:
    """Return ``USED``, ``UNVERIFIED`` or ``DEAD`` for one catalogue key."""
    if key in usage.exact:
        return USED

    for prefix in legacy_prefixes or ():
        if prefix not in usage.suppressed_roots and key.startswith(prefix):
            return USED

    verdict = _family_verdict(key, usage)
    if verdict is not None:
        return verdict

    for prefix in usage.unverified_prefixes:
        if key == prefix or key.startswith(prefix + "."):
            return UNVERIFIED

    return DEAD
