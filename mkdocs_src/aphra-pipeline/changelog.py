"""The CHANGELOG's translation units: the preamble, the chapters, the pieces of a long chapter.

``CHANGELOG.md`` (the repository root, English) is translated into ``CHANGELOG.<lang>.md`` beside it. The app reads the
chapters by their ``## [x.y.z] - date`` line (``frontend/src/lib/features/changelog/changelog.ts``), so every
translation keeps those lines byte for byte, in the English order, and a chapter not translated yet is absent: the app
shows the English one.

A unit is the preamble (before the first chapter line) or one chapter. A unit up to ``PIECE_THRESHOLD`` characters is
one piece; a longer one is cut at its ``###`` and ``####`` lines: the chapter's intro is a piece of its own, and a part
that holds only its heading joins the part that follows. A piece is keyed by its headings' words, so an added ``####``
shifts no other key. The chapter line and the ``---`` rule that closes a unit are structure: never sent to the model,
copied.

Pure functions: no LLM, no cache writes. ``translate_docs`` and ``validate_translations`` share them and pass the
source explicitly, derived from their ``DOCS_DIR`` (``_changelog_source()``); ``SOURCE`` is only the default of a direct
call.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from code_blocks import code_line_mask

SOURCE = Path(__file__).resolve().parent.parent.parent / "CHANGELOG.md"
KEY = "CHANGELOG.md"
PREAMBLE = "preamble"
PIECE_THRESHOLD = 30_000

CHAPTER_LINE = re.compile(r"^## \[([^\]]+)\]")
PIECE_HEADING = re.compile(r"^(#{3,4}) (.*)$")
RULE = "---"


@dataclass
class Piece:
    key: str
    text: str

    @property
    def md5(self) -> str:
        return text_md5(self.text)


@dataclass
class Unit:
    """The preamble (``name`` ``preamble``, no ``heading``) or a chapter (``name`` its version)."""

    name: str
    heading: str
    body: str
    trailer: str  # the ``---`` that closes the unit in the source, or ""
    pieces: list[Piece] = field(default_factory=list)

    @property
    def split(self) -> bool:
        return len(self.pieces) > 1 or (bool(self.pieces) and "/" in self.pieces[0].key)

    def text(self, body: str | None = None) -> str:
        """The unit as a page would hold it: its chapter line, then ``body`` (the English one by default)."""
        body = self.body if body is None else body
        return f"{self.heading}\n\n{body}" if self.heading else body


@dataclass
class Translation:
    """A ``CHANGELOG.<lang>.md`` as read: its preamble, and its chapters by version, with their lines as written."""

    preamble: str
    chapters: dict[str, tuple[str, str]]  # version -> (chapter line, body)
    order: list[str]  # the versions, in the file's order (duplicates kept)


def text_md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def translated_path(lang: str, source: Path | None = None) -> Path:
    return (source or SOURCE).with_name(f"CHANGELOG.{lang}.md")


def read_text(path: Path) -> str:
    """Universal newlines, as ``read_text`` in text mode."""
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def _strip_rule(body: str) -> tuple[str, str]:
    lines = body.strip("\n").split("\n")
    if lines and lines[-1].strip() == RULE:
        return "\n".join(lines[:-1]).strip("\n"), RULE
    return body.strip("\n"), ""


def _units(text: str) -> list[tuple[str, str, str, str]]:
    """``(name, chapter line, body, trailer)`` for the preamble and each chapter, outside fenced code."""
    lines = text.split("\n")
    mask = code_line_mask(text)
    starts = [i for i, line in enumerate(lines) if not mask[i] and CHAPTER_LINE.match(line)]
    out = []
    preamble, trailer = _strip_rule("\n".join(lines[: starts[0]] if starts else lines))
    out.append((PREAMBLE, "", preamble, trailer))
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        body, trailer = _strip_rule("\n".join(lines[start + 1 : end]))
        out.append((CHAPTER_LINE.match(lines[start]).group(1), lines[start], body, trailer))
    return out


def _slug(heading_text: str) -> str:
    words = re.findall(r"[^\W_]+", heading_text.lower())
    return "-".join(words) or "part"


def cut_parts(body: str) -> list[str]:
    """``body`` cut at its ``###`` and ``####`` lines (outside fenced code); the intro is a part of its own, and a part
    that is only its heading joins the next one."""
    lines = body.split("\n")
    mask = code_line_mask(body)
    heads = [i for i, line in enumerate(lines) if not mask[i] and PIECE_HEADING.match(line)]
    if not heads:
        return [body.strip("\n")] if body.strip() else []
    head_set = set(heads)
    bounds = ([0] if heads[0] > 0 else []) + heads
    parts: list[str] = []
    pending: list[str] = []
    for n, start in enumerate(bounds):
        end = bounds[n + 1] if n + 1 < len(bounds) else len(lines)
        segment = lines[start:end]
        content = segment[1:] if start in head_set else segment
        pending.extend(segment)
        if any(line.strip() for line in content):
            parts.append("\n".join(pending).strip("\n"))
            pending = []
    if pending:
        tail = "\n".join(pending).strip("\n")
        if parts:
            parts[-1] = f"{parts[-1]}\n\n{tail}"
        else:
            parts.append(tail)
    return parts


def opens_with_heading(text: str) -> bool:
    """Whether the first line that is not blank is a ``###`` or ``####`` heading."""
    first = next((line for line in text.split("\n") if line.strip()), "")
    return bool(PIECE_HEADING.match(first))


def structure_change(english: str, translated: str) -> str | None:
    """Why the translation of a piece of a cut unit cannot take the piece's place in its chapter, or ``None``.

    It must cut into one part, and open with a heading exactly when the English piece does: an added heading cuts it in
    two, a lost one joins it to the part before it. Either way the chapter would no longer cut into its pieces, and
    every later run would translate it again."""
    parts = len(cut_parts(translated))
    if parts != 1:
        return f"the translation cuts into {parts} parts instead of 1"
    if opens_with_heading(translated) != opens_with_heading(english):
        if opens_with_heading(english):
            return "the translation drops the heading its English piece opens with"
        return "the translation opens with a heading its English piece does not have"
    return None


def part_ids(parts: list[str]) -> list[str]:
    """Each part's id from its headings: the ``###`` in force, then its ``####``; repeated ids get ``-2``, ``-3``."""
    ids, seen = [], {}
    h3 = ""
    for part in parts:
        h4 = ""
        lines = part.split("\n")
        for line, in_code in zip(lines, code_line_mask(part), strict=True):
            m = None if in_code else PIECE_HEADING.match(line)
            if not m:
                continue
            if len(m.group(1)) == 3:
                h3, h4 = _slug(m.group(2)), ""
            else:
                h4 = _slug(m.group(2))
        base = f"{h3}/{h4}" if h3 and h4 else (h4 or h3 or "intro")
        seen[base] = seen.get(base, 0) + 1
        ids.append(base if seen[base] == 1 else f"{base}-{seen[base]}")
    return ids


def english(text: str) -> list[Unit]:
    """The units of the English CHANGELOG, each with its pieces and their keys; an empty unit has no piece."""
    units = []
    for name, heading, body, trailer in _units(text):
        unit = Unit(name, heading, body, trailer)
        base = f"{KEY}#{name}"
        if not body.strip():
            pass  # nothing to translate; kept for the chapters' order
        elif len(body) <= PIECE_THRESHOLD:
            unit.pieces = [Piece(base, body)]
        else:
            parts = cut_parts(body)
            unit.pieces = [Piece(f"{base}/{pid}", part) for pid, part in zip(part_ids(parts), parts, strict=True)]
        units.append(unit)
    return units


def read_english(source: Path | None = None) -> list[Unit] | None:
    path = source or SOURCE
    return english(read_text(path)) if path.exists() else None


def parse_translation(text: str) -> Translation:
    chapters: dict[str, tuple[str, str]] = {}
    order: list[str] = []
    preamble = ""
    for name, heading, body, _trailer in _units(text):
        if name == PREAMBLE:
            preamble = body
            continue
        order.append(name)
        chapters.setdefault(name, (heading, body))
    return Translation(preamble, chapters, order)


def read_translation(lang: str, source: Path | None = None) -> Translation | None:
    path = translated_path(lang, source)
    return parse_translation(read_text(path)) if path.exists() else None


def unit_keys(unit_name: str, keys) -> list[str]:
    """The cache keys of a unit among ``keys``: the whole-unit key and its pieces' keys."""
    whole = f"{KEY}#{unit_name}"
    return [k for k in keys if k == whole or k.startswith(whole + "/")]


def translated_body(unit: Unit, translation: Translation | None) -> str | None:
    if translation is None:
        return None
    if unit.name == PREAMBLE:
        return translation.preamble or None
    found = translation.chapters.get(unit.name)
    return found[1] if found else None


def locate(unit: Unit, translation: Translation | None, hashes: dict, lang: str) -> tuple[dict[str, str], str]:
    """The translated text of each of ``unit``'s pieces in ``translation``, by key, and why some could not be found.

    A one-piece unit is its whole translated body. A cut unit is cut by the same rule, and the parts are matched to the
    keys by the indexes the last write recorded (``langs.<lang>.index``); with no index yet, by position, when the
    counts agree."""
    body = translated_body(unit, translation)
    if body is None:
        return {}, "absent"
    if not unit.split:
        return {unit.pieces[0].key: body}, ""
    parts = cut_parts(body)
    indexed = sorted(
        (entry["langs"][lang]["index"], key)
        for key in unit_keys(unit.name, hashes)
        for entry in [hashes[key]]
        if isinstance(entry.get("langs", {}).get(lang, {}).get("index"), int)
    )
    if indexed:
        if len(indexed) != len(parts):
            return {}, f"{len(parts)} parts for {len(indexed)} recorded pieces"
        return {key: parts[i] for (i, (_, key)) in enumerate(indexed)}, ""
    if len(parts) != len(unit.pieces):
        return {}, f"{len(parts)} parts for {len(unit.pieces)} pieces"
    return {piece.key: part for piece, part in zip(unit.pieces, parts, strict=True)}, ""


def assemble(units: list[Unit], bodies: dict[str, str]) -> str:
    """The translated file: each unit of ``units`` that has a body in ``bodies`` (by name), in the English order, with
    the English chapter line and the English closing rule."""
    present = [u for u in units if u.pieces and u.name in bodies]
    blocks = []
    for n, unit in enumerate(present):
        block = unit.text(bodies[unit.name].strip("\n"))
        if unit.trailer and n + 1 < len(present):
            block += f"\n\n{unit.trailer}"
        blocks.append(block)
    return "\n\n".join(blocks) + "\n"


def _tag_exists(version: str, repo: Path) -> bool:
    """Whether the release tag of ``version`` exists: ``v<version>`` or ``<version>``, the two forms the release
    workflow's tag guard accepts (a release candidate's ``-rc.N`` tag is not the release's)."""
    tags = (f"v{version}", version)
    if os.environ.get("GITHUB_REF") in {f"refs/tags/{tag}" for tag in tags}:
        return True
    for tag in tags:
        try:
            done = subprocess.run(["git", "-C", str(repo), "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
                                  capture_output=True, check=False)
        except OSError:
            return False
        if done.returncode == 0:
            return True
    return False


def released(units: list[Unit], source: Path | None = None) -> set[str]:
    """The units whose translation must be complete: the preamble, every chapter but the newest, and the newest once
    its tag (``v<version>`` or ``<version>``) exists or is the ref of the CI run. ``units`` must be every unit of the
    English, the empty ones included: a newest chapter still empty makes the one below it released."""
    chapters = [u.name for u in units if u.name != PREAMBLE]
    out = {PREAMBLE} | set(chapters[1:])
    if chapters and _tag_exists(chapters[0], (source or SOURCE).parent):
        out.add(chapters[0])
    return out
