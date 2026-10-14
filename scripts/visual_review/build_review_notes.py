#!/usr/bin/env python3
"""Generate the team's Markdown working notes for a colour review (LibreFolio visual review).

    pipenv run python -m scripts.visual_review.build_review_notes <work>/snapshots/<label> [--force] [--work-dir <dir>]

Writes <work>/notes/NOTE_DESIGNER.md: how to view the screenshots, the legend of known problems, the role
vocabulary and first-round decisions to fill in, then one section per gallery area with the navigation
table (route, steps, data), the analysis hints and one ✏️ line per shot. Links point to the snapshot's
browse pages (run `gallery_tool browse` on the same snapshot first).

Never overwrites an existing NOTE_DESIGNER.md (someone may have written in it): it writes
NOTE_DESIGNER.generated.md next to it instead, unless --force.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from scripts.visual_review import review_content as rc
from scripts.visual_review._common import work_dir
from scripts.visual_review.navmap import load_navmap, resolve_ids

LINK_LANG = "it"


def area_section(i: int, cat: str, actual: set[str], rows: list[list[str]], intro: str | None, links, unmapped: list[str]) -> list[str]:
    """Markdown of one gallery area: navigation table, analysis hints, one ✏️ line per shot."""
    out = [f"\n### 5.{i} {rc.TITLES.get(cat, cat)} — `{cat}` ({len(actual)} schermate)\n"]
    if intro:
        out.append(intro + "\n")
    out += ["| Schermata | Vedi | Come arrivarci | Utente / dati | Componenti |", "|---|---|---|---|---|"]
    mapped: list[str] = []
    for cells in rows:
        ids = resolve_ids(cells[0], cat, actual)
        mapped += [n for n in ids if n not in mapped]
        label = "<br>".join(f"`{cat}/{n}`" for n in ids) if ids else cells[0]
        see = "<br>".join(links(n) for n in ids) if ids else "?"
        route, how, who, comp = (cells + ["", "", "", "", "", ""])[2:6]
        out.append(f"| {label} | {see} | {route} — {how} | {who} | {comp} |")
    missing = sorted(actual - set(mapped))
    out += [f"| `{cat}/{n}` | {links(n)} | ? (non trovata nella mappa) | ? | ? |" for n in missing]
    unmapped += [f"{cat}/{n}" for n in missing]
    if rc.LOOK.get(cat):
        out += ["\n**Cosa guardare** (spunti dall'analisi, da confermare a schermo):"] + [f"- {x}" for x in rc.LOOK[cat]]
    out += [f"\n**✏️ Note — {cat}**"] + [f"- [ ] `{cat}/{n}` — " for n in mapped + missing] + ["- ✏️ Note generali sull'area:"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate the Markdown working notes of a colour review")
    ap.add_argument("snapshot")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--work-dir", help="output root outside the repository")
    args = ap.parse_args()
    snap = Path(args.snapshot).expanduser().resolve()
    meta = json.loads((snap / "meta.json").read_text())
    notes_dir = work_dir(args.work_dir) / "notes"
    notes_dir.mkdir(exist_ok=True)
    snap_rel = os.path.relpath(snap, notes_dir)

    shots: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for p in (snap / "png").rglob("*.png"):
        vp, _lang, _theme, cat, name = p.relative_to(snap / "png").with_suffix("").parts
        shots[cat][name].add(vp)
    rows, intros = load_navmap()

    def links(cat: str, name: str) -> str:
        vps = shots[cat].get(name, set())
        parts = []
        if "desktop" in vps:
            parts.append(f"[🖥]({snap_rel}/desktop-{LINK_LANG}.html#{cat}/{name})")
        elif name not in rc.MOBILE_ONLY:
            parts.append("⚠️ desktop non catturata")
        if "mobile" in vps:
            parts.append(f"[📱]({snap_rel}/mobile-{LINK_LANG}.html#{cat}/{name})")
        return " ".join(parts) or "—"

    n_shots = sum(len(v) for v in shots.values())
    out = [rc.NOTES_HEADER.format(commit=meta.get("commit", "?")[:10], date=meta.get("started", "?")[:10], snap_rel=snap_rel, n_shots=n_shots)]
    unmapped: list[str] = []
    cats = [c for c in rc.ORDER if c in shots] + sorted(c for c in shots if c not in rc.ORDER)
    for i, cat in enumerate(cats, 1):
        out += area_section(i, cat, set(shots[cat]), rows.get(cat, []), intros.get(cat), lambda n, c=cat: links(c, n), unmapped)
    out.append(rc.NOTES_FOOTER)

    dest = notes_dir / "NOTE_DESIGNER.md"
    if dest.exists() and not args.force:
        dest = dest.with_name("NOTE_DESIGNER.generated.md")
        print("NOTE_DESIGNER.md exists: writing", dest.name, "instead (use --force to overwrite)")
    dest.write_text("\n".join(out) + "\n")
    print(f"written {dest} — {n_shots} shots, {len(unmapped)} not in the navigation map: {unmapped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
