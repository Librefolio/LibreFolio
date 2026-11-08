"""What a translated page must keep from its source, beyond headings, links and code fences.

``validate_translations.py`` compares headings, links, fenced blocks (count and indentation), inline code,
list items, admonition counts and HTML. A page can still say something different in another language without
any of them noticing: a Mermaid arrow pointing the other way, a content tab dropped, a table row lost, a
command changed inside a block (filed as "comments translated"), a nested admonition missing. This module
holds the checks that look at those, as pure functions of two texts.

Each function returns ``Difference`` records; ``validate_translations.py`` wraps them in its own ``Issue``.

Standard library only (``dev.py`` loads the pipeline inside ``except ImportError: pass``).
"""

import re
from dataclasses import dataclass

from code_blocks import FencedBlock, _body, _key, _normalized, code_line_mask, pair_blocks, parse_fenced_blocks


@dataclass(frozen=True)
class Difference:
    """One difference between a source page and its translation."""

    check: str
    message: str
    line: int | None = None  # 1-based line of the translation, when there is one


# ---------------------------------------------------------------------------
# Mermaid: same diagrams, same nodes, same arrows, same colours
# ---------------------------------------------------------------------------

_QUOTED = re.compile(r'"[^"\n]*"')
_EDGE_LABEL = re.compile(r"\|[^|\n]*\|")
_INNERMOST = re.compile(r"\[[^\[\]\n]*\]|\([^()\n]*\)|\{[^{}\n]*\}")
_EDGE_TEXT = re.compile(r"(--|==)\s+(?!>)[^<>\n]*?\s+(-->|==>|---|===)")
_SEQUENCE_ARROW = r"(?:-->>|->>|-->|->|--x|-x|--\)|-\))"
_SEQUENCE_MESSAGE = re.compile(rf"^(?P<head>[\w .-]+?\s*{_SEQUENCE_ARROW}[+-]?\s*[\w .-]+?)\s*:.*$")
_NOTE = re.compile(r"^(?P<head>Note\s+(?:left of|right of|over)\s+[\w, ]+?)\s*:.*$", re.IGNORECASE)
_BLOCK_KEYWORD = re.compile(r"^(loop|alt|else|opt|par|and|critical|option|break|title)\b.*$", re.IGNORECASE)
_PARTICIPANT = re.compile(r"^(participant|actor)\s+(\S+)\s+as\s+.*$", re.IGNORECASE)
_SUBGRAPH = re.compile(r"^subgraph\s+(?P<id>[^\s\[\"]+)\s*(?P<rest>\[.*)?$")


def _blank_labels(line: str) -> str:
    """A flowchart line without the text a reader sees: quoted strings, edge labels, node shapes' content."""
    line = _QUOTED.sub('""', line)
    line = _EDGE_LABEL.sub("||", line)
    previous = None
    while previous != line:
        previous = line
        line = _INNERMOST.sub(lambda m: m.group(0)[0] + m.group(0)[-1], line)
    return _EDGE_TEXT.sub(r"\2", line)


def _skeleton_line(line: str) -> str:
    """One non-front-matter Mermaid line without the text a reader sees."""
    if re.match(r"^(style|classDef|class|linkStyle|click)\b", line):
        return re.sub(r"\s+", " ", line)
    participant = _PARTICIPANT.match(line)
    if participant:
        return f"{participant.group(1).lower()} {participant.group(2)}"
    note = _NOTE.match(line)
    if note:
        return re.sub(r"\s+", " ", note.group("head"))
    keyword = _BLOCK_KEYWORD.match(line)
    if keyword:
        return keyword.group(1).lower()
    message = _SEQUENCE_MESSAGE.match(line)
    if message:
        return re.sub(r"\s+", " ", message.group("head"))
    subgraph = _SUBGRAPH.match(line)
    if subgraph:
        return f"subgraph {subgraph.group('id')}" + ("[]" if subgraph.group("rest") else "")
    if line.startswith("subgraph"):
        return "subgraph"
    return re.sub(r"\s+", " ", _blank_labels(line))


def mermaid_skeleton(block: FencedBlock) -> list[str]:
    """The lines of a Mermaid block that do not depend on the language: ids, arrows, shapes, styles, config."""
    out: list[str] = []
    in_front_matter = False
    for raw in _body(block):
        line = raw.strip()
        if not line or line.startswith("%%"):
            continue
        if line == "---" and (in_front_matter or not out):
            in_front_matter = not in_front_matter
            out.append("---")
        elif in_front_matter:
            out.append(re.sub(r"^(title\s*:).*$", r"\1", line))
        else:
            out.append(_skeleton_line(line))
    return out


def check_mermaid(source: str, translated: str) -> list[Difference]:
    """Same number of Mermaid diagrams, and in each one the same front matter, nodes, arrows, ``style``/``classDef``."""
    src = [b for b in parse_fenced_blocks(source) if b.lang == "mermaid"]
    tr = [b for b in parse_fenced_blocks(translated) if b.lang == "mermaid"]
    found: list[Difference] = []
    if len(src) != len(tr):
        found.append(Difference("mermaid-count", f"Source has {len(src)} Mermaid diagrams, translation has {len(tr)}"))
    for number, (s, t) in enumerate(zip(src, tr, strict=False), 1):
        skeleton_s, skeleton_t = mermaid_skeleton(s), mermaid_skeleton(t)
        if skeleton_s == skeleton_t:
            continue
        for k in range(max(len(skeleton_s), len(skeleton_t))):
            a = skeleton_s[k] if k < len(skeleton_s) else "(nothing)"
            b = skeleton_t[k] if k < len(skeleton_t) else "(nothing)"
            if a != b:
                found.append(Difference("mermaid-structure", f"Diagram #{number}, line {k + 1} of the skeleton: source `{a[:70]}` vs translation `{b[:70]}`", t.start + 1))
                break
    return found


# ---------------------------------------------------------------------------
# Content tabs: same tabs, proper names kept, body indented by 4
# ---------------------------------------------------------------------------

_TAB = re.compile(r'^(?P<indent>[ \t]*)===(?P<mark>[+!]?)\s+"(?P<title>[^"]*)"\s*$')
# Product and platform names a tab title keeps in every language.
PROPER_NAMES = frozenset(
    {
        "Caddy",
        "Nginx",
        "nginx",
        "Traefik",
        "Tailscale",
        "Fly.io",
        "Docker",
        "Compose",
        "Gmail",
        "Linux",
        "macOS",
        "Windows",
        "Pipenv",
        "Python",
        "Node.js",
        "Ubuntu",
        "Debian",
        "Homebrew",
        "Brevo",
        "Mailgun",
        "SendGrid",
        "Outlook",
        "Office365",
        "iCloud",
        "Postfix",
        "SMTP",
        "STARTTLS",
        "SSL",
        "TLS",
        "Serve",
        "Funnel",
        "Cloudflare",
        "Apache",
        "Kubernetes",
        "Podman",
        "PowerShell",
        "Bash",
        "Zsh",
        "Fish",
        "WSL",
    }
)


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[\w.+#-]+", text) if not w.isdigit()]


def _tabs(text: str) -> list[tuple[int, re.Match]]:
    mask = code_line_mask(text)
    return [(i, m) for i, (line, in_code) in enumerate(zip(text.split("\n"), mask, strict=True)) if not in_code and (m := _TAB.match(line))]


def check_tabs(source: str, translated: str) -> list[Difference]:
    """Same content tabs in the same order; a proper name in the source title stays in the translated title;
    the body of a tab is indented by 4 spaces (1 space renders the tabs one below the other)."""
    found: list[Difference] = []
    src, tr = _tabs(source), _tabs(translated)
    if len(src) != len(tr):
        found.append(Difference("tab-count", f"Source has {len(src)} content tabs, translation has {len(tr)}"))
    for number, ((_, s), (line_index, t)) in enumerate(zip(src, tr, strict=False), 1):
        if s.group("mark") != t.group("mark"):
            found.append(Difference("tab-marker", f"Tab #{number}: marker `==={s.group('mark')}` became `==={t.group('mark')}`", line_index + 1))
        if len(s.group("indent")) != len(t.group("indent")):
            found.append(Difference("tab-nesting", f"Tab #{number} is nested {len(t.group('indent'))} spaces deep, the source {len(s.group('indent'))}", line_index + 1))
        for word in _words(s.group("title")):
            if (word in PROPER_NAMES or re.search(r"[a-z][A-Z]|\w\.\w", word)) and word not in t.group("title"):
                found.append(Difference("tab-title", f"Tab #{number}: the name `{word}` of `{s.group('title')}` is not in `{t.group('title')}`", line_index + 1))
    return found + _tab_body_indents(translated, tr)


def _tab_body_indents(translated: str, tabs: list[tuple[int, re.Match]]) -> list[Difference]:
    """The first line under each tab header starts 4 spaces deeper than the header."""
    lines = translated.split("\n")
    found: list[Difference] = []
    for line_index, match in tabs:
        step = line_index + 1
        while step < len(lines) and not lines[step].strip():
            step += 1
        if step < len(lines) and not _TAB.match(lines[step]):
            lead = len(lines[step]) - len(lines[step].lstrip(" "))
            if lead < len(match.group("indent")) + 4:
                found.append(Difference("tab-indent", f"The body of tab `{match.group('title')}` starts {lead - len(match.group('indent'))} spaces in, it needs 4", step + 1))
    return found


# ---------------------------------------------------------------------------
# Tables: same tables, same rows, same columns
# ---------------------------------------------------------------------------


def _cells(line: str) -> int:
    """Number of cells of a table row: pipes inside code spans or escaped do not split."""
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    count, in_code, i = 1, False, 0
    while i < len(text):
        char = text[i]
        if char == "\\":
            i += 2
            continue
        if char == "`":
            in_code = not in_code
        elif char == "|" and not in_code:
            count += 1
        i += 1
    return count


def tables(text: str) -> list[tuple[int, list[int]]]:
    """Each table outside fenced code: the 0-based line it starts on and the cell count of each of its rows."""
    mask = code_line_mask(text)
    found: list[tuple[int, list[int]]] = []
    current: list[int] = []
    start = 0
    for i, (line, in_code) in enumerate(zip(text.split("\n"), mask, strict=True)):
        if not in_code and line.strip().startswith("|"):
            if not current:
                start = i
            current.append(_cells(line))
        elif current:
            found.append((start, current))
            current = []
    if current:
        found.append((start, current))
    return found


def check_tables(source: str, translated: str) -> list[Difference]:
    """Same number of tables, and each one with the same rows and the same cells per row."""
    src, tr = tables(source), tables(translated)
    found: list[Difference] = []
    if len(src) != len(tr):
        found.append(Difference("table-count", f"Source has {len(src)} tables, translation has {len(tr)}"))
    for number, ((_, s), (start, t)) in enumerate(zip(src, tr, strict=False), 1):
        if s == t:
            continue
        if len(s) != len(t):
            found.append(Difference("table-shape", f"Table #{number}: source has {len(s)} rows, translation has {len(t)}", start + 1))
        else:
            row = next(k for k in range(len(s)) if s[k] != t[k])
            found.append(Difference("table-shape", f"Table #{number}, row {row + 1}: source has {s[row]} cells, translation has {t[row]}", start + 1 + row))
    return found


# ---------------------------------------------------------------------------
# Identifiers: variables, dev.py commands, paths
# ---------------------------------------------------------------------------

_ENV_VAR = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")
_DEV_COMMAND = re.compile(r"(?:\./)?dev\.py((?:\s+[a-z][\w-]*)+)")
_PATH = re.compile(r"(?<![\w/:.-])(?:~|\.{1,2})?/?(?:[\w.@-]+/)+[\w.@-]*")
_INLINE_SPAN = re.compile(r"(?P<ticks>`+)(?P<code>.+?)(?P=ticks)")


def _scan_parts(text: str) -> tuple[str, list[str]]:
    """Prose with inline code kept, and the comment-free lines of the fenced blocks (Mermaid excluded)."""
    mask = code_line_mask(text)
    prose = [line for line, in_code in zip(text.split("\n"), mask, strict=True) if not in_code]
    code_lines: list[str] = []
    for block in parse_fenced_blocks(text):
        if block.lang == "mermaid":
            continue
        for raw in _body(block):
            normalized = _normalized(raw, block.lang)
            if normalized and normalized not in ("#", "//"):
                code_lines.append(normalized)
    return "\n".join(prose), code_lines


def identifiers(text: str) -> dict[str, set[str]]:
    """The environment variables, ``dev.py`` commands and paths a page cites in inline code and code blocks.

    Bare prose is not read: a lifecycle state such as PARTIALLY_CLOSED is localized on purpose in a theory page.
    """
    prose, code_lines = _scan_parts(text)
    spans = [m.group("code").strip() for m in _INLINE_SPAN.finditer(prose)]
    code = spans + code_lines
    return {
        "variable": {v for chunk in code for v in _ENV_VAR.findall(chunk)},
        "command": {"dev.py " + " ".join(m.group(1).split()) for chunk in code for m in _DEV_COMMAND.finditer(chunk)},
        "path": {p.rstrip(".,;:") for chunk in code if "://" not in chunk for p in _PATH.findall(chunk) if "<P>" not in p and len(p) > 2},
    }


def check_identifiers(source: str, translated: str) -> list[Difference]:
    """The same set of ``LIBREFOLIO_*``-style variables, ``./dev.py …`` commands and paths in every language."""
    src, tr = identifiers(source), identifiers(translated)
    found: list[Difference] = []
    for kind in ("variable", "command", "path"):
        for name in sorted(src[kind] - tr[kind]):
            found.append(Difference(f"{kind}-missing", f"The {kind} `{name}` of the source is not in the translation"))
        for name in sorted(tr[kind] - src[kind]):
            found.append(Difference(f"{kind}-extra", f"The {kind} `{name}` is in the translation and not in the source"))
    return found


# ---------------------------------------------------------------------------
# Code blocks: a command is not a comment
# ---------------------------------------------------------------------------


def check_code_content(source: str, translated: str) -> list[Difference]:
    """Fenced blocks (Mermaid aside) are the same code once comments, placeholders and spacing are put aside.

    ``code-block-modified`` files every difference as "comments translated"; this one fails when a command,
    a setting or a log line differs.
    """
    src = [b for b in parse_fenced_blocks(source) if b.lang != "mermaid"]
    tr = [b for b in parse_fenced_blocks(translated) if b.lang != "mermaid"]
    pairs = pair_blocks(src, tr)
    paired_src = {i for i, _ in pairs}
    found: list[Difference] = []
    for i, j in pairs:
        if _key(src[i]) != _key(tr[j]):
            a, b = _key(src[i])[1], _key(tr[j])[1]
            k = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
            found.append(Difference("code-block-content", f"Block #{i + 1} ({src[i].lang or 'text'}): `{a[k] if k < len(a) else '(nothing)'}` became `{b[k] if k < len(b) else '(nothing)'}`", tr[j].start + 1))
    for i in range(len(src)):
        if i not in paired_src:
            first = next(iter(_key(src[i])[1]), "")
            found.append(Difference("code-block-content", f"Block #{i + 1} ({src[i].lang or 'text'}, `{first[:50]}`) has no equal block in the translation"))
    return found


# ---------------------------------------------------------------------------
# Admonitions (nested ones too) and heading anchors
# ---------------------------------------------------------------------------

_ADMONITION = re.compile(r"^(?P<indent>[ \t]*)(?P<marker>!!!|\?\?\?\+?)\s+(?P<kind>[\w-]+)")
_ANCHOR = re.compile(r"\{:\s*#(?P<id>[\w-]+)[^}]*\}")


def check_admonition_sequence(source: str, translated: str) -> list[Difference]:
    """The same admonitions in the same order: marker (``!!!``, ``???``, ``???+``), type and nesting depth.

    ``admonition-count`` reads only the ones at column 0; these include the ones inside list items and tabs.
    """

    def sequence(text: str):
        mask = code_line_mask(text)
        return [(i, m) for i, (line, in_code) in enumerate(zip(text.split("\n"), mask, strict=True)) if not in_code and (m := _ADMONITION.match(line))]

    src, tr = sequence(source), sequence(translated)
    found: list[Difference] = []
    if len(src) != len(tr):
        found.append(Difference("admonition-nested-count", f"Source has {len(src)} admonitions at any depth, translation has {len(tr)}"))
    for number, ((_, s), (line_index, t)) in enumerate(zip(src, tr, strict=False), 1):
        a = (s.group("marker"), s.group("kind"), len(s.group("indent")))
        b = (t.group("marker"), t.group("kind"), len(t.group("indent")))
        if a != b:
            found.append(Difference("admonition-sequence", f"Admonition #{number}: source `{a[0]} {a[1]}` at depth {a[2]}, translation `{b[0]} {b[1]}` at depth {b[2]}", line_index + 1))
    return found


def _slug(heading: str) -> str:
    """The id MkDocs builds from a heading text (ASCII English headings; emoji and punctuation dropped)."""
    text = _ANCHOR.sub("", heading)
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def check_heading_anchors(source: str, translated: str) -> list[Difference]:
    """Explicit ``{: #id }`` anchors: every one of the source is in the translation, and the translation adds
    none except the id MkDocs builds from a source heading (a translated heading keeps the English id that way)."""

    def anchors(text: str) -> list[str]:
        mask = code_line_mask(text)
        return [m.group("id") for line, in_code in zip(text.split("\n"), mask, strict=True) if not in_code for m in _ANCHOR.finditer(line)]

    def heading_slugs(text: str) -> set[str]:
        mask = code_line_mask(text)
        return {_slug(m.group(1)) for line, in_code in zip(text.split("\n"), mask, strict=True) if not in_code and (m := re.match(r"^#{1,6}\s+(.*)", line))}

    src, tr = anchors(source), anchors(translated)
    found: list[Difference] = []
    missing = sorted(set(src) - set(tr))
    if missing:
        found.append(Difference("anchor-id", f"Explicit anchors of the source missing in the translation: {missing}"))
    allowed = set(src) | heading_slugs(source)
    extra = sorted(set(tr) - allowed)
    if extra:
        found.append(Difference("anchor-id", f"Explicit anchors not in the source (and not the id of a source heading): {extra}"))
    if not missing and not extra and [a for a in src if a in tr] != [a for a in tr if a in src]:
        found.append(Difference("anchor-order", "The explicit anchors `{: #id }` are the same but not in the same order"))
    return found
