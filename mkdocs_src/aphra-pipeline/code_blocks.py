"""Fenced code blocks of a translated page versus its English source.

Shared by ``translate_docs.py`` (the pipeline restores the source indentation before it
writes a translation) and ``validate_translations.py`` (``code-block-indent`` check).

Translation never has a reason to change the indentation of code, so every translated
block that pairs with its source block keeps the source leading whitespace, line by
line, fences included. Only the text after the indentation is the translator's:
comments, Mermaid labels, placeholders.

Standard library only: ``dev.py`` loads the pipeline commands inside
``except ImportError: pass``, so a third-party import would make them vanish silently.
"""

import difflib
import re
from dataclasses import dataclass

_FENCE_OPEN = re.compile(r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})(?P<info>[^`]*)$")
_HASH_COMMENT_LANGS = frozenset({"", "bash", "sh", "shell", "zsh", "console", "yaml", "yml", "toml", "python", "py", "text", "dockerfile", "env", "dotenv", "ini", "conf"})
_SLASH_COMMENT_LANGS = frozenset({"json", "jsonc", "json5", "hujson", "js", "javascript", "ts", "typescript"})
_PLACEHOLDER = re.compile(r"<[^<>\"'\s]+>")
# On a stripped line: the code, the gap, then an inline comment. A comment-only line has no code part, so it never matches.
_INLINE_COMMENT = re.compile(r"^(?P<code>.*?\S)(?P<gap>[ \t]+)(?P<comment>(?:#|//)(?=\s|$).*)$")


@dataclass(frozen=True)
class FencedBlock:
    """A fenced code block; ``start``/``end`` are 0-based line indexes in ``text.split('\\n')``."""

    start: int
    end: int
    indent: str
    lang: str
    lines: tuple[str, ...]
    closed: bool


@dataclass(frozen=True)
class IndentIssue:
    """A paired block whose translated lines (0-based indexes in the translation) lost the source indentation."""

    source_block: FencedBlock
    translated_block: FencedBlock
    lines: tuple[int, ...]


def parse_fenced_blocks(text: str) -> list[FencedBlock]:
    """Backtick and tilde fences of 3+ characters, at any indentation (lists, content tabs, admonitions).

    A block closes on a fence of the same character, at least as long, with nothing after it.
    An unclosed fence runs to the last line (``closed=False``).
    """
    lines = text.split("\n")
    blocks: list[FencedBlock] = []
    i = 0
    while i < len(lines):
        opening = _FENCE_OPEN.match(lines[i])
        if not opening:
            i += 1
            continue
        fence = opening.group("fence")
        closing = re.compile(rf"^[ \t]*{re.escape(fence[0])}{{{len(fence)},}}[ \t]*$")
        j = i + 1
        while j < len(lines) and not closing.match(lines[j]):
            j += 1
        closed = j < len(lines)
        end = j if closed else len(lines) - 1
        info = opening.group("info").split()
        blocks.append(FencedBlock(start=i, end=end, indent=opening.group("indent"), lang=info[0].lower() if info else "", lines=tuple(lines[i : end + 1]), closed=closed))
        i = end + 1
    return blocks


def code_line_mask(text: str) -> list[bool]:
    """One flag per line of ``text.split('\\n')``: True inside a fenced block, fences included."""
    mask = [False] * len(text.split("\n"))
    for block in parse_fenced_blocks(text):
        mask[block.start : block.end + 1] = [True] * (block.end - block.start + 1)
    return mask


def _body(block: FencedBlock) -> tuple[str, ...]:
    return block.lines[1:-1] if block.closed else block.lines[1:]


def _normalized(line: str, lang: str) -> str | None:
    """A code line without what translation may change: indentation, spacing, comments, placeholders."""
    text = line.strip()
    if not text:
        return None
    if lang in _HASH_COMMENT_LANGS:
        if text.startswith("#"):
            return "#"
        text = re.sub(r"\s+#(?=\s|$).*$", "", text)
    elif lang in _SLASH_COMMENT_LANGS:
        if text.startswith("//"):
            return "//"
        text = re.sub(r"\s+//(?=\s|$).*$", "", text)
    text = _PLACEHOLDER.sub("<P>", text)
    return re.sub(r"\s+", " ", text)


def _key(block: FencedBlock) -> tuple:
    return block.lang, tuple(line for line in (_normalized(raw, block.lang) for raw in _body(block)) if line is not None)


def pair_blocks(source_blocks: list[FencedBlock], translated_blocks: list[FencedBlock]) -> list[tuple[int, int]]:
    """Pair each translated block with its source block: ``(source_index, translated_index)``, monotonic.

    Blocks with the same code pair by content, so a block present on one side only does
    not shift the others. Inside a stretch that differs (translated Mermaid labels, HuJSON
    comments), the remaining blocks pair in order when language and line count match.
    """
    matcher = difflib.SequenceMatcher(a=[_key(b) for b in source_blocks], b=[_key(b) for b in translated_blocks], autojunk=False)
    pairs: list[tuple[int, int]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            pairs.extend((i1 + k, j1 + k) for k in range(i2 - i1))
        elif tag == "replace":
            free = list(range(j1, j2))
            for i in range(i1, i2):
                source = source_blocks[i]
                for position, j in enumerate(free):
                    if translated_blocks[j].lang == source.lang and len(translated_blocks[j].lines) == len(source.lines):
                        pairs.append((i, j))
                        free = free[position + 1 :]
                        break
    return pairs


def _aligned_pairs(source: str, translated: str):
    """Paired blocks that can be compared line by line: both closed, same number of lines."""
    source_blocks, translated_blocks = parse_fenced_blocks(source), parse_fenced_blocks(translated)
    for i, j in pair_blocks(source_blocks, translated_blocks):
        src, tr = source_blocks[i], translated_blocks[j]
        if src.closed and tr.closed and len(src.lines) == len(tr.lines):
            yield src, tr


def _lead(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def _restored_line(source_line: str, translated_line: str) -> str:
    if source_line.split() == translated_line.split():
        return source_line.rstrip()
    restored = _lead(source_line) + translated_line.strip()
    source_parts, translated_parts = _INLINE_COMMENT.match(source_line.strip()), _INLINE_COMMENT.match(translated_line.strip())
    if source_parts and translated_parts and source_parts.group("code") == translated_parts.group("code"):
        restored = _lead(source_line) + translated_parts.group("code") + source_parts.group("gap") + translated_parts.group("comment")
    return restored


def restore_code_indent(source: str, translated: str) -> tuple[str, int]:
    """Give every paired translated block the source whitespace back; return the text and the changed line count.

    Line by line, fences included: a line whose tokens equal the source line becomes the
    source line; any other line gets the source leading whitespace in front of its own
    text (plus the source gap before an inline comment when the code part is identical).
    Blank lines on either side, prose and unpaired blocks are left alone, and no trailing
    whitespace is ever added.
    """
    lines = translated.split("\n")
    changed = 0
    for src, tr in _aligned_pairs(source, translated):
        for offset, (source_line, translated_line) in enumerate(zip(src.lines, tr.lines, strict=True)):
            if not source_line.strip() or not translated_line.strip():
                continue
            restored = _restored_line(source_line, translated_line)
            if restored.rstrip() != translated_line.rstrip():
                lines[tr.start + offset] = restored
                changed += 1
    return "\n".join(lines), changed


def code_indent_issues(source: str, translated: str) -> list[IndentIssue]:
    """Paired blocks whose non-blank translated lines do not start with the source leading whitespace."""
    issues = []
    for src, tr in _aligned_pairs(source, translated):
        drifted = tuple(tr.start + offset for offset, (source_line, translated_line) in enumerate(zip(src.lines, tr.lines, strict=True)) if source_line.strip() and translated_line.strip() and _lead(source_line) != _lead(translated_line))
        if drifted:
            issues.append(IndentIssue(source_block=src, translated_block=tr, lines=drifted))
    return issues
