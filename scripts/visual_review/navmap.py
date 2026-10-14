"""Read the gallery navigation map (``data/navigation_map.it.md``).

The map has one ``## <category>`` section per gallery category, each with a Markdown table whose columns are:
shot ids | viewports/languages | route | how to get there | user/data | components. A row may list several
shots, abbreviating the next ones as ``, -suffix`` or ``/ -suffix`` (e.g. ``transactions/form-modal-sell, -fee``).
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from scripts.visual_review._common import DATA

NAVMAP_PATH = DATA / "navigation_map.it.md"


def parse_navmap(text: str) -> tuple[dict[str, list[list[str]]], dict[str, str]]:  # noqa: C901 — flat line classifier: heading / table row / separator / intro line, no nested logic
    """Return ({category: [row cells]}, {category: intro text before its table})."""
    rows: dict[str, list[list[str]]] = defaultdict(list)
    intros: dict[str, str] = {}
    cat = None
    intro_lines: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^## (\w+)\s*$", line)
        if m:
            if cat and intro_lines:
                intros[cat] = "\n".join(intro_lines).strip()
            cat, intro_lines = m.group(1), []
            continue
        if cat is None:
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and cells[0] != "Shot" and not set(cells[0]) <= set("-: "):
                rows[cat].append(cells)
        elif line.startswith("---") or line.startswith("**Conteggio"):
            if intro_lines:
                intros[cat] = "\n".join(intro_lines).strip()
            cat, intro_lines = None, []
        elif not rows[cat]:
            intro_lines.append(line)
    if cat and intro_lines and cat not in intros:
        intros[cat] = "\n".join(intro_lines).strip()
    return rows, intros


def resolve_ids(cell: str, cat: str, actual: set[str]) -> list[str]:
    """Expand the shot ids of a row's first cell against the shot names really captured."""
    ids = re.findall(rf"\b{cat}/([\w-]+)", cell)
    out = [i for i in ids if i in actual]
    if ids:
        head = ids[0].split("-")[0]
        for tok in re.findall(r"(?:,|/)\s*-([\w-]+)", cell):
            cands = sorted((n for n in actual if n.endswith("-" + tok) and n.startswith(head)), key=len)
            if cands:
                out.append(cands[0])
    seen: list[str] = []
    for o in out:
        if o not in seen:
            seen.append(o)
    return seen


def load_navmap(path: Path = NAVMAP_PATH) -> tuple[dict[str, list[list[str]]], dict[str, str]]:
    return parse_navmap(path.read_text())
