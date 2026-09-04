#!/usr/bin/env python3
"""Check that every path cited in a wiki page's `## Source files` table exists.

Why this exists
---------------
A lint on 2026-09-01 found **144 of 1 828 cited paths (7,9 %) pointing at files
that do not exist**. The breakdown mattered more than the total:

* 85 were dated drift — three June 2026 refactors moved `stores/`,
  `components/transactions/` and `utils/`, and the wiki stayed put;
* 59 existed nowhere, and **23 of the 38 pages written the day before** carried
  one. The refactors were three months old: that is not the wiki ageing, it is
  an ingest transcribing paths out of plans without checking them;
* 4 were invented outright, built because they sounded right.

The trap has a name: **a plan is not a chronicle**. `plan-p8-runner-migration.md`
opens by declaring "awaiting approval, no repository file has been touched", and
was read in the indicative. The architecture did land — but the file names in
the wiki were the proposed ones, not the delivered ones.

None of the three classes survives a filesystem check, and none of them was
visible to the knowledge graph: the graph covers ~4 % of the code, so a BFS
query answers partially and looks complete. This check costs a fraction of a
second and finds all of them.

**Run it before writing a page, not six months after.**

Usage
-----
    python3 check_source_paths.py            # report, exit 1 if anything is missing
    python3 check_source_paths.py --quiet    # only the summary line
    python3 check_source_paths.py --page X   # one page
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

WIKI = Path(__file__).resolve().parent
REPO = WIKI.parent

# A path cited inside a markdown table cell, wrapped in backticks. Cells that
# carry prose rather than a path are filtered out by the heuristics below.
CELL = re.compile(r"`([^`]+)`")

# Not paths: prose, globs, symbols, URLs, npm packages, API endpoints and shell
# fragments all end up in these tables legitimately. So do abbreviated citations
# (`.../foo.md`) and bare filenames used as names rather than locations.
def looks_like_path(s: str) -> bool:
    s = s.strip()
    if not s or " " in s.rstrip("/"):
        return False
    if s.startswith(("http", "$", "-", "#", "@", "...", "/", "~")) or "://" in s:
        return False
    if "*" in s or "{" in s or "(" in s:
        return False
    # A repo-relative path has at least one separator. A bare `Foo.svelte` is a
    # name, not a location: resolving it would require guessing, and guessing is
    # what produced the invented paths in the first place.
    return "/" in s and not s.startswith(".")


def cited_paths(page: Path) -> list[tuple[int, str]]:
    """Every path cited under a `## Source files` heading, with its line number."""
    out: list[tuple[int, str]] = []
    in_section = False
    for n, line in enumerate(page.read_text(encoding="utf8").splitlines(), 1):
        if line.startswith("## "):
            in_section = "source files" in line.lower()
            continue
        if not in_section or not line.lstrip().startswith("|"):
            continue
        for cell in CELL.findall(line):
            # Strip a trailing line or symbol reference: `foo.py:120`,
            # `foo.py::function`, `foo.py (~line 42)`
            cleaned = re.sub(r"::.*$", "", cell).strip()
            cleaned = re.sub(r"[:#]\s*~?\d+.*$", "", cleaned).strip()
            cleaned = re.sub(r"\s*\(~?(line\s*)?\d+.*\)$", "", cleaned).strip()
            if looks_like_path(cleaned):
                out.append((n, cleaned))
    return out


def resolve(p: str) -> bool:
    candidate = (REPO / p) if not p.startswith("LibreFolio_devWiki") else (REPO / p)
    if candidate.exists():
        return True
    # Wiki-relative paths are cited without the LibreFolio_devWiki/ prefix.
    return (WIKI / p).exists()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quiet", action="store_true", help="only the summary line")
    ap.add_argument("--page", help="check a single page")
    args = ap.parse_args()

    pages = [WIKI / args.page] if args.page else sorted((WIKI / "wiki").rglob("*.md"))

    missing: dict[str, list[tuple[Path, int]]] = defaultdict(list)
    total = 0
    for page in pages:
        for line_no, path in cited_paths(page):
            total += 1
            if not resolve(path):
                missing[path].append((page, line_no))

    if not args.quiet:
        for path in sorted(missing):
            print(f"\n✗ {path}")
            for page, line_no in missing[path]:
                print(f"    {page.relative_to(WIKI)}:{line_no}")

    occurrences = sum(len(v) for v in missing.values())
    affected = len({p for v in missing.values() for p, _ in v})
    print(
        f"\n{len(missing)} path inesistenti ({occurrences} occorrenze) "
        f"su {total} citati, in {affected} pagine."
    )
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
