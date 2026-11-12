#!/usr/bin/env python3
"""Quantitative colour inventory of frontend/src (LibreFolio visual review).

Counts every colour expression in .svelte/.ts/.js/.css sources (generated API files excluded):
Tailwind palette classes (with variants and opacity), custom-token classes (libre-*, theme-*,
primary-*, accent-*, and the lf-* colour roles of lib/theme/tokens.css), arbitrary values, hex literals, rgb()/hsl()/oklch()/color-mix() calls,
CSS custom-property definitions and var() uses. Test files are kept in the CSVs (is_test) but
excluded from the summary.

    pipenv run python -m scripts.visual_review.color_inventory [--out <dir>] [--work-dir <dir>]

Writes 00_inventory_summary.md plus CSVs to --out (default: <work dir>/inventory).
Read-only on the repository.
"""

from __future__ import annotations

import argparse
import collections
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from scripts.visual_review._common import REPO, work_dir

ROOT = REPO / "frontend" / "src"
# The Designer Lab's own sources are tooling, not the app: frontend/scripts/designer-lab/scan-colors.mjs skips them too,
# so the two inventories keep counting the same tree.
LAB_DIRS = ("lib/dev/designer-lab/", "routes/designer-lab/")

EXTS = {".svelte", ".ts", ".js", ".css"}
FAMILIES = ("slate gray zinc neutral stone red orange amber yellow lime green emerald teal cyan sky blue " "indigo violet purple fuchsia pink rose").split()
PREFIXES = ("bg text border border-t border-b border-l border-r border-x border-y ring ring-offset outline " "divide from via to fill stroke shadow accent caret decoration placeholder").split()

tw_re = re.compile(r"(?<![\w-])((?:[a-z0-9-]+:)*)(" + "|".join(sorted(PREFIXES, key=len, reverse=True)) + r")-(" + "|".join(FAMILIES) + r")-(50|100|200|300|400|500|600|700|800|900|950)(/\d{1,3}|/\[[^\]]+\])?(?![\w-])")
tw_bw_re = re.compile(r"(?<![\w-])((?:[a-z0-9-]+:)*)(bg|text|border|ring|fill|stroke|from|to|via)-(white|black|transparent|current)(/\d{1,3})?(?![\w-])")
tw_custom_re = re.compile(r"(?<![\w-])((?:[a-z0-9-]+:)*)(" + "|".join(sorted(PREFIXES, key=len, reverse=True)) + r")-(libre-[a-z-]+|theme-[a-z-]+|primary[a-z-]*|accent[a-z-]*|lf-[a-z0-9-]+)(/\d{1,3})?(?![\w-])")
tw_arbitrary_re = re.compile(r"(?<![\w-])((?:[a-z0-9-]+:)*)(bg|text|border|ring|fill|stroke|from|to|via|outline|divide|shadow)-\[([^\]]*(?:#|rgb|hsl|var\(|oklch)[^\]]*)\]")
hex_re = re.compile(r"(?<![\w&])#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")
func_re = re.compile(r"\b(rgba?|hsla?|oklch|color-mix)\(([^()]*(?:\([^()]*\)[^()]*)*)\)")
var_use_re = re.compile(r"var\(\s*(--[\w-]+)")
var_def_re = re.compile(r"^\s*(--[\w-]+)\s*:\s*([^;]+);", re.M)


def is_test(p) -> bool:
    s = str(p)
    return "__tests__" in s or "__mocks__" in s or ".test." in s or ".spec." in s


_SVELTE_REGION_RE = re.compile(r"<(script|style)\b[^>]*>([\s\S]*?)</\1\s*>")


def _blank(chars: list[str], start: int, stop: int) -> None:
    for k in range(start, stop):
        if chars[k] not in "\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029":
            chars[k] = " "


def mask_comments_in(text: str, mode: str, start: int = 0, end: int | None = None) -> str:  # noqa: C901 — one scanner, one loop over the characters
    """``text`` with every character of a comment replaced by a space (newlines kept: lines and columns do not move).

    ``mode`` ``css`` knows ``/* … */``; ``script`` knows that and ``// …``, and skips strings and template literals (with
    their ``${…}``), so ``'https://x'`` is not a comment; ``markup`` knows ``<!-- … -->``. Mirrored by ``maskCommentsIn`` of
    ``frontend/scripts/designer-lab/scan-colors.mjs``: change one, change the other.
    """
    end = len(text) if end is None else end
    chars = list(text)
    if mode == "markup":
        i = start
        while i < end:
            if text.startswith("<!--", i):
                close = text.find("-->", i + 4)
                stop = end if close == -1 or close + 3 > end else close + 3
                _blank(chars, i, stop)
                i = stop
            else:
                i += 1
        return "".join(chars)
    # Template literals nest: each ``${`` opens a code context whose own braces are counted.
    stack = [["code", 0]]
    i = start
    while i < end:
        c = text[i]
        top = stack[-1]
        if top[0] == "tpl":
            if c == "\\":
                i += 1
            elif c == "`":
                stack.pop()
            elif c == "$" and text[i + 1 : i + 2] == "{":
                stack.append(["code", 0])
                i += 1
            i += 1
            continue
        if c == "/" and text[i + 1 : i + 2] == "*":
            close = text.find("*/", i + 2)
            stop = end if close == -1 or close + 2 > end else close + 2
            _blank(chars, i, stop)
            i = stop - 1
        elif mode == "script" and c == "/" and text[i + 1 : i + 2] == "/":
            stop = text.find("\n", i)
            if stop == -1 or stop > end:
                stop = end
            _blank(chars, i, stop)
            i = stop - 1
        elif c in "\"'":
            i += 1
            while i < end and text[i] != c and text[i] != "\n":
                if text[i] == "\\":
                    i += 1
                i += 1
        elif mode == "script" and c == "`":
            stack.append(["tpl", 0])
        elif mode == "script" and c == "{":
            top[1] += 1
        elif mode == "script" and c == "}":
            if top[1] == 0 and len(stack) > 1:
                stack.pop()
            else:
                top[1] -= 1
        i += 1
    return "".join(chars)


def mask_comments(rel: str, text: str) -> str:
    """A source with its comments blanked out, by file kind: ``.css`` as CSS, ``.svelte`` per region (its ``<script>`` as
    script, its ``<style>`` as CSS, the markup around them for ``<!-- -->``), anything else as script."""
    if rel.endswith(".css"):
        return mask_comments_in(text, "css")
    if not rel.endswith(".svelte"):
        return mask_comments_in(text, "script")
    chars = list(mask_comments_in(text, "markup"))
    for m in _SVELTE_REGION_RE.finditer(text):
        start = m.start() + m.group(0).index(">") + 1
        end = start + len(m.group(2))
        part = mask_comments_in(text, "css" if m.group(1) == "style" else "script", start, end)
        chars[start:end] = part[start:end]
    return "".join(chars)


@dataclass
class Scan:
    """Everything collected from the sources; per_file counts production files only."""

    files: int = 0
    tw_rows: list = field(default_factory=list)
    hex_rows: list = field(default_factory=list)
    func_rows: list = field(default_factory=list)
    arb_rows: list = field(default_factory=list)
    custom_rows: list = field(default_factory=list)
    var_defs: list = field(default_factory=list)
    var_uses: collections.Counter = field(default_factory=collections.Counter)
    var_use_files: dict = field(default_factory=lambda: collections.defaultdict(set))
    per_file: dict = field(default_factory=lambda: collections.defaultdict(collections.Counter))

    def count(self, rel: str, test: bool, key: str) -> None:
        if not test:
            self.per_file[rel][key] += 1


def source_files() -> list[Path]:
    files = [p for p in ROOT.rglob("*") if p.suffix in EXTS and p.is_file() and "node_modules" not in p.parts]
    return sorted(p for p in files if not p.name.startswith("generated") and "openapi" not in p.name and "tool-contract-map" not in p.name and not p.relative_to(ROOT).as_posix().startswith(LAB_DIRS))


def scan_line(s: Scan, rel: str, ln: int, line: str, code: str, test: bool) -> None:
    """``line`` is what the CSVs quote; ``code`` is the same line with its comments blanked, and is what is matched."""
    for m in tw_re.finditer(code):
        variants, prefix, fam, shade, op = m.groups()
        s.tw_rows.append((rel, ln, test, variants, prefix, fam, shade, op or "", m.group(0)))
        s.count(rel, test, "tw")
        if "dark:" in variants:
            s.count(rel, test, "tw_dark")
    for m in tw_bw_re.finditer(code):
        variants, prefix, col, op = m.groups()
        s.tw_rows.append((rel, ln, test, variants, prefix, col, "", op or "", m.group(0)))
    for m in tw_custom_re.finditer(code):
        s.custom_rows.append((rel, ln, test, m.group(0)))
        s.count(rel, test, "custom_token")
    for m in tw_arbitrary_re.finditer(code):
        s.arb_rows.append((rel, ln, test, m.group(0)))
        s.count(rel, test, "arbitrary")
    for m in hex_re.finditer(code):
        s.hex_rows.append((rel, ln, test, "#" + m.group(1).lower(), line.strip()[:160]))
        s.count(rel, test, "hex")
    for m in func_re.finditer(code):
        s.func_rows.append((rel, ln, test, m.group(0)[:80], line.strip()[:160]))
        s.count(rel, test, "fn")
    for m in var_use_re.finditer(code):
        s.var_uses[m.group(1)] += 1
        s.var_use_files[m.group(1)].add(rel)
        s.count(rel, test, "var")


def scan_sources(files: list[Path]) -> Scan:
    s = Scan(files=len(files))
    for p in files:
        rel = str(p.relative_to(ROOT.parent))
        test = is_test(p)
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        # The colours counted are the code's: a colour written in a comment is not one (L6-1). Same lines, same columns.
        code = mask_comments(rel, text)
        for ln, (line, code_line) in enumerate(zip(text.splitlines(), code.splitlines(), strict=True), 1):
            scan_line(s, rel, ln, line, code_line, test)
        for m in var_def_re.finditer(code):
            s.var_defs.append((rel, code[: m.start()].count("\n") + 1, m.group(1), m.group(2).strip()))
    return s


def score(c: collections.Counter) -> int:
    return c["tw"] + c["hex"] + c["fn"] + c["arbitrary"] + c["var"] + c["custom_token"]


def write_csv(out: Path, name: str, header: list[str], rows) -> None:
    with open(out / name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def write_csvs(out: Path, s: Scan) -> None:
    defined_names = {d[2] for d in s.var_defs}
    write_csv(out, "tailwind_color_classes.csv", ["file", "line", "is_test", "variants", "prefix", "family", "shade", "opacity", "raw"], s.tw_rows)
    write_csv(out, "hex_literals.csv", ["file", "line", "is_test", "hex", "context"], s.hex_rows)
    write_csv(out, "color_functions.csv", ["file", "line", "is_test", "expr", "context"], s.func_rows)
    write_csv(out, "arbitrary_tailwind.csv", ["file", "line", "is_test", "raw"], s.arb_rows)
    write_csv(out, "custom_token_classes.csv", ["file", "line", "is_test", "raw"], s.custom_rows)
    write_csv(out, "css_var_definitions.csv", ["file", "line", "name", "value"], s.var_defs)
    write_csv(out, "css_var_usage.csv", ["name", "uses", "files", "defined"], sorted(((k, v, len(s.var_use_files[k]), k in defined_names) for k, v in s.var_uses.items()), key=lambda r: -r[1]))
    write_csv(
        out,
        "per_file_summary.csv",
        ["file", "tw_palette", "tw_dark", "custom_token", "arbitrary", "hex", "rgb_hsl_fn", "var_uses"],
        sorted(((f, c["tw"], c["tw_dark"], c["custom_token"], c["arbitrary"], c["hex"], c["fn"], c["var"]) for f, c in s.per_file.items()), key=lambda r: -sum(r[1:])),
    )


def write_summary(out: Path, s: Scan) -> int:  # noqa: C901 — flat report: independent sections, one loop each, no nested decisions
    defined_names = {d[2] for d in s.var_defs}
    prod_tw = [r for r in s.tw_rows if not r[2]]
    pal_tw = [r for r in prod_tw if r[6]]
    fam_c = collections.Counter(r[5] for r in prod_tw)
    fam_shade = collections.Counter((r[5], r[6]) for r in pal_tw)
    prefix_fam = collections.Counter((r[4], r[5]) for r in prod_tw)
    variant_c = collections.Counter(v for r in prod_tw for v in r[3].split(":") if v)
    op_c = collections.Counter(r[7] for r in prod_tw if r[7])
    prod_hex = [r for r in s.hex_rows if not r[2]]
    hex_c = collections.Counter(r[3] for r in prod_hex)
    hex_files = collections.defaultdict(set)
    for r in prod_hex:
        hex_files[r[3]].add(r[0])
    raw_c = collections.Counter(r[8] for r in prod_tw)
    prod_custom = collections.Counter(r[3] for r in s.custom_rows if not r[2])
    prod_arb = collections.Counter(r[3] for r in s.arb_rows if not r[2])
    fn_c = collections.Counter(re.sub(r"\s+", "", r[3]).lower() for r in s.func_rows if not r[2])

    L = []
    P = L.append
    P("# Frontend color inventory — quantitative snapshot\n")
    P(f"Source: `frontend/src` (generated API files excluded). Files scanned: {s.files}. Test files excluded from the stats below (kept in CSVs with `is_test`).\n")
    P("## Totals (production code)\n")
    P(f"- Tailwind palette + white/black/transparent color classes: **{len(prod_tw)}** (with `dark:`: {sum(1 for r in prod_tw if 'dark:' in r[3])})")
    P(f"- Custom-token Tailwind classes (libre-*/theme-*/primary/accent/lf-*): **{sum(prod_custom.values())}**")
    P(f"- Arbitrary-value color classes (`bg-[#...]`, `text-[var(--...)]`): **{sum(prod_arb.values())}**")
    P(f"- Hex literals: **{len(prod_hex)}** ({len(hex_c)} distinct)")
    P(f"- rgb()/rgba()/hsl()/oklch()/color-mix(): **{sum(fn_c.values())}** ({len(fn_c)} distinct)")
    P(f"- `var(--…)` usages: **{sum(s.var_uses.values())}** across {len(s.var_uses)} distinct properties")
    P(f"- CSS custom property definitions: **{len(s.var_defs)}**\n")

    P("## Tailwind color families (prod)\n")
    P("| Family | Uses | Top shades |")
    P("|---|---:|---|")
    for fam, n in fam_c.most_common():
        shades = sorted(((s, c) for (f, s), c in fam_shade.items() if f == fam), key=lambda x: -x[1])[:9]
        P(f"| {fam} | {n} | " + ", ".join(f"{s}×{c}" for s, c in shades) + " |")

    P("\n## Prefix × family (prod, top 70)\n")
    P("| Prefix | Family | Uses |")
    P("|---|---|---:|")
    for (pre, fam), n in prefix_fam.most_common(70):
        P(f"| {pre} | {fam} | {n} |")

    P("\n## Variants on color classes (prod)\n")
    P(", ".join(f"`{v}`×{n}" for v, n in variant_c.most_common(30)))
    P("\n## Opacity modifiers (prod)\n")
    P(", ".join(f"`{o}`×{n}" for o, n in op_c.most_common()))

    P("\n## Most frequent exact color classes (prod, top 100)\n")
    P("| Class | Uses |")
    P("|---|---:|")
    for c, n in raw_c.most_common(100):
        P(f"| `{c}` | {n} |")

    P("\n## Custom-token classes (prod)\n")
    P("| Class | Uses |")
    P("|---|---:|")
    for c, n in prod_custom.most_common():
        P(f"| `{c}` | {n} |")

    P("\n## Arbitrary-value color classes (prod)\n")
    P("| Class | Uses |")
    P("|---|---:|")
    for c, n in prod_arb.most_common():
        P(f"| `{c}` | {n} |")

    P("\n## Hex literals (prod) — distinct values by frequency\n")
    P("| Hex | Uses | Files | Example files |")
    P("|---|---:|---:|---|")
    for h, n in hex_c.most_common():
        fs = sorted(hex_files[h])
        P(f"| `{h}` | {n} | {len(fs)} | " + "<br>".join(f.replace("src/", "") for f in fs[:4]) + (" …" if len(fs) > 4 else "") + " |")

    P("\n## rgb/rgba/hsl/color-mix (prod) — distinct expressions (top 80)\n")
    P("| Expression | Uses |")
    P("|---|---:|")
    for e, n in fn_c.most_common(80):
        P(f"| `{e}` | {n} |")

    P("\n## CSS custom properties — definitions\n")
    P("| Property | Value | Defined at | var() uses |")
    P("|---|---|---|---:|")
    for f, ln, name, val in s.var_defs:
        P(f"| `{name}` | `{val[:70]}` | {f}:{ln} | {s.var_uses.get(name, 0)} |")

    P("\n## var() references with no definition in frontend/src\n")
    for k, v in sorted(((k, v) for k, v in s.var_uses.items() if k not in defined_names), key=lambda x: -x[1]):
        P(f"- `{k}` ×{v} — e.g. {sorted(s.var_use_files[k])[0]}")

    P("\n## Hotspot files (prod)\n")
    P("| File | TW palette | of which dark: | custom tokens | arbitrary | hex | rgb/hsl | var() |")
    P("|---|---:|---:|---:|---:|---:|---:|---:|")
    rows = sorted(((f, c) for f, c in s.per_file.items() if not is_test(f)), key=lambda kv: -score(kv[1]))
    for f, c in rows[:80]:
        P(f"| {f} | {c['tw']} | {c['tw_dark']} | {c['custom_token']} | {c['arbitrary']} | {c['hex']} | {c['fn']} | {c['var']} |")

    P("\n## Light-only candidates: ≥3 palette classes, zero `dark:`, zero var()\n")
    for f, c in rows:
        if c["tw"] >= 3 and c["tw_dark"] == 0 and c["var"] == 0:
            P(f"- {f} ({c['tw']} palette classes)")

    (out / "00_inventory_summary.md").write_text("\n".join(L) + "\n")
    return len(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Colour inventory of frontend/src")
    ap.add_argument("--out", help="output directory (default: <work dir>/inventory)")
    ap.add_argument("--work-dir", help="output root outside the repository")
    args = ap.parse_args()
    out = Path(args.out).expanduser().resolve() if args.out else work_dir(args.work_dir) / "inventory"
    if out == REPO or REPO in out.parents:
        raise SystemExit(f"--out {out} is inside the repository: choose a path outside it")
    out.mkdir(parents=True, exist_ok=True)
    s = scan_sources(source_files())
    write_csvs(out, s)
    n = write_summary(out, s)
    print("written", out / "00_inventory_summary.md", n, "lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
