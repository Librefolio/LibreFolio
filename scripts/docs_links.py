"""Discovery of cross-boundary documentation links (frontend/backend → MkDocs).

This module exists because the gate that used to hold this logic could not be
tested: its resolver was a function nested inside the command body, reachable
only by running the whole command against the real tree. A gate that cannot be
interrogated cannot be proven, and this one had three blind spots that survived
for exactly that reason.

**What it used to miss.**

1. ``docsPath={DOC_PATHS[row.id]}`` — a dynamic prop. The old comment said a
   dynamic path "is skipped by construction", and it was: only quoted literals
   were read. But the values of that map are static, so the skip was a choice,
   not a limit.

2. ``<DocsLink path={typeInfo.docsPath}>`` and ``path={documentation}`` — paths
   that originate in the **backend** and arrive through the API. The old scope 2
   named two provider directories by hand, so every plugin family created after
   it was written was invisible *by default*. ``signal_plugins`` already was.

3. Nothing was ever reported as unverifiable. A path the gate could not resolve
   simply vanished from the output, and an empty error list read as "all good".

**The trap this module deliberately avoids.** The natural repair — scan the map
literals too — is worse than the disease. ``DOC_PATHS`` holds template literals
built on a constant::

    const DOCS = 'financial-theory/technical-analysis/risk-metrics';
    day: `${DOCS}/conditional-value-at-risk/`

and the old resolver *deletes* ``${…}`` rather than resolving it, leaving
``conditional-value-at-risk`` — a plausible path that does not exist. The gate
would stop being blind and start being wrong, which is worse: a false positive
on a healthy link teaches people to ignore the output, and a gate that is
learned-to-be-ignored is worth less than no gate at all.

So: resolve constants, and when a value genuinely cannot be resolved, say so.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

#: Service sub-packages scanned for backend-declared docs paths. Discovered by
#: glob rather than listed, so a new plugin family is covered the day it lands.
BACKEND_SERVICE_GLOB = "*_providers", "*_plugins"

_CONST_DECL = re.compile(
    r"\bconst\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=\n]*)?=\s*['\"]([^'\"]+)['\"]"
)
_INTERP = re.compile(r"\$\{([^}]*)\}")
#: Both interpolation dialects that appear in a docs path: the JS template form
#: ``${X}`` and the Svelte markup form ``{X}`` inside an attribute value.
_ANY_INTERP = re.compile(r"\$\{([^}]*)\}|\{([^}]*)\}")

_DOCS_PATH_LITERAL = re.compile(r"""docsPath\s*[:=]\s*['"]([^'"]+)['"]""")
_DOCS_PATH_TEMPLATE = re.compile(r"""docsPath\s*[:=]\s*`([^`]+)`""")
_MKDOCS_URL = re.compile(r"""/mkdocs/([^'"`,\s)]+)""")
_DOCSLINK_PROP = re.compile(
    r"""\b(?:localizedFallbackPath|path)\s*=\s*['"]([^'"]+)['"]"""
)
_MAP_ENTRY = re.compile(r"""^\s*[A-Za-z0-9_'"]+\s*:\s*(?:`([^`]+)`|['"]([^'"]+)['"])\s*,?\s*$""")

_BACKEND_DOCS = re.compile(r"""\bdocs_path\s*=\s*['"]([^'"]+)['"]""")
_BACKEND_TOOL_DOCS = re.compile(r"""\bpath\s*=\s*['"]([^'"]+)['"]""")
_BACKEND_MKDOCS_URL = re.compile(r"""['"](/mkdocs/[^'"]+)['"]""")


@dataclass
class Link:
    """One documentation reference found in the sources."""

    path: str
    origin: str
    confident: bool = True
    """False when an unknown interpolation was dropped to obtain this path."""


@dataclass
class Discovery:
    links: list[Link] = field(default_factory=list)
    unverified: list[Link] = field(default_factory=list)
    """References whose value could not be resolved statically. Declared, never silent."""

    def add(self, raw: str, origin: str, consts: dict[str, str]) -> None:
        if _is_not_a_reference(raw):
            return
        resolved = resolve(raw, consts)
        if resolved is None:
            self.unverified.append(Link(raw, origin, confident=False))
        else:
            path, confident = resolved
            self.links.append(Link(path, origin, confident=confident))


def resolve(raw: str, consts: dict[str, str] | None = None) -> tuple[str, bool] | None:
    """Normalise a documentation path, resolving constants instead of deleting them.

    Returns ``(path, confident)`` or ``None`` when nothing checkable remains.

    ``confident`` is the part that matters. A ``${…}`` whose value is a known
    constant resolves exactly, and a failure to find that page is a real error.
    An *unknown* interpolation can only be guessed at by deleting it — which is
    right for an optional language prefix (``/mkdocs/${prefix}user/…``) and wrong
    for a required segment (``${DOCS}/max-drawdown/``). The guess is therefore
    allowed to *confirm* a link and never to *condemn* one: a speculative path
    that resolves is a pass, and one that does not is reported as unverifiable,
    not as broken.

    That asymmetry is the whole difference between a gate that stops being blind
    and one that starts being wrong.
    """
    consts = consts or {}
    missing: list[str] = []

    def _sub(match: re.Match) -> str:
        name = (match.group(1) or match.group(2) or "").strip()
        if name in consts:
            return consts[name]
        missing.append(name)
        return ""

    cleaned = _ANY_INTERP.sub(_sub, raw)
    if any(ch in cleaned for ch in "${}"):
        return None
    cleaned = cleaned.strip().lstrip("/").rstrip("/")
    if not cleaned or ":path" in cleaned or cleaned.startswith(("http://", "https://")):
        return None
    return cleaned, not missing


def _is_test_file(path: Path) -> bool:
    """Fixtures, mocks and generated artefacts are not sources of documentation links.

    ``api/generated.ts`` matters as much as the test files: it is produced by
    ``api sync``, is git-ignored, and therefore exists in some worktrees and not
    others. Reading it would make this gate's output depend on whether someone
    happened to run a code generator — which is exactly the kind of lane-age
    difference that makes one worktree green and another red for no reason.
    """
    return path.name.endswith((".test.ts", ".spec.ts")) or path.name == "generated.ts"


def _is_not_a_reference(raw: str) -> bool:
    """True when the value was never a documentation path to begin with.

    A route placeholder such as ``/mkdocs/:path`` is a URL pattern, not a link;
    declaring it "unverifiable" would fill the report with noise and teach the
    reader to skim past the section that exists precisely to be read.
    """
    return ":path" in raw or raw.startswith(("http://", "https://"))


def _map_values(content: str, name: str) -> list[str]:
    """Return the raw values of a ``const NAME: Record<…> = { k: v, … }`` literal."""
    start = re.search(rf"\bconst\s+{re.escape(name)}\b[^=]*=\s*\{{", content)
    if not start:
        return []
    depth, i = 0, start.end() - 1
    while i < len(content):
        if content[i] == "{":
            depth += 1
        elif content[i] == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = content[start.end(): i]
    return [m.group(1) or m.group(2) for m in (_MAP_ENTRY.match(ln) for ln in body.splitlines()) if m]


def _scan_line(found: Discovery, line: str, origin: str, content: str, consts: dict[str, str]) -> None:
    """Fold every documentation reference on one source line into ``found``."""
    for m in _DOCS_PATH_LITERAL.finditer(line):
        found.add(m.group(1), origin, consts)
    for m in _DOCS_PATH_TEMPLATE.finditer(line):
        found.add(m.group(1), origin, consts)
    for m in _MKDOCS_URL.finditer(line):
        found.add(m.group(1).rstrip("/"), origin, consts)
    if "<DocsLink" in line:
        for m in _DOCSLINK_PROP.finditer(line):
            found.add(m.group(1), origin, consts)

    # A dynamic prop whose value comes from a local map is not a runtime
    # unknown: the map is right there. This is the whole difference between
    # "skipped by construction" and "skipped".
    for m in re.finditer(r"""\b(?:docsPath|path)\s*=\s*\{([^}]+)\}""", line):
        expression = m.group(1).strip()
        subscript = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\[.*\]", expression)
        values = _map_values(content, subscript.group(1)) if subscript else []
        if values:
            for value in values:
                found.add(value, f"{origin} via {subscript.group(1)}", consts)
        elif "<DocsLink" in line or "docsPath" in m.group(0):
            # Anything else genuinely arrives at runtime — from the API, from a
            # descriptor, from a snippet parameter. That is not an error, but it
            # must not pass silently either.
            found.unverified.append(Link("{" + expression + "}", origin, confident=False))


def collect_frontend(src_dir: Path) -> Discovery:
    """Scan ``frontend/src`` for documentation references."""
    found = Discovery()

    for ext in ("*.ts", "*.svelte"):
        for path in sorted(src_dir.rglob(ext)):
            if _is_test_file(path):
                continue
            try:
                content = path.read_text()
            except OSError:
                continue
            consts = dict(_CONST_DECL.findall(content))
            for i, line in enumerate(content.splitlines(), 1):
                _scan_line(found, line, f"{path}:{i}", content, consts)

    return found


def collect_backend(services_dir: Path) -> Discovery:
    """Scan backend service plugins for declared documentation paths.

    Every ``*_providers`` / ``*_plugins`` package is covered by glob. The gate
    used to name two directories by hand, so a family added later — such as
    ``signal_plugins``, seventeen pages — was invisible until someone remembered
    to edit the list. Nobody did.
    """
    found = Discovery()
    if not services_dir.is_dir():
        return found

    seen_dirs = sorted(
        {d for pattern in BACKEND_SERVICE_GLOB for d in services_dir.glob(pattern) if d.is_dir()}
    )
    for pdir in seen_dirs:
        for path in sorted(pdir.glob("*.py")):
            try:
                content = path.read_text()
            except OSError:
                continue
            origin = str(path)
            for m in _BACKEND_DOCS.finditer(content):
                found.add(m.group(1), origin, {})
            for m in _BACKEND_MKDOCS_URL.finditer(content):
                found.add(m.group(1).replace("/mkdocs/", "").rstrip("/"), origin, {})
            for m in _BACKEND_TOOL_DOCS.finditer(content):
                value = m.group(1)
                if value.startswith(("user/", "developer/", "financial-theory/")):
                    found.add(value, origin, {})

    return found


def find_page(docs_root: Path, path: str) -> Path | None:
    """Resolve a docs path to a source page, honouring ``use_directory_urls``.

    ``use_directory_urls`` is not declared in ``mkdocs.yml``, so it defaults to
    true and the served shape is a directory URL. Both spellings are accepted
    here; the *served* form is what belongs in the sources.
    """
    file_part = path.split("#", 1)[0].rstrip("/")
    for candidate in (
        docs_root / f"{file_part}.en.md",
        docs_root / file_part / "index.en.md",
        docs_root / f"{file_part}.md",
        docs_root / file_part / "index.md",
    ):
        if candidate.exists():
            return candidate
    return None


def deduplicate(links: list[Link]) -> list[Link]:
    """One entry per distinct path, keeping the first origin that produced it."""
    seen: set[str] = set()
    unique: list[Link] = []
    for link in links:
        if link.path in seen:
            continue
        seen.add(link.path)
        unique.append(link)
    return unique
