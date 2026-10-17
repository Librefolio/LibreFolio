#!/usr/bin/env python3
"""Build a designer review round: the screens of today, before and after, the colours left, the open questions and the
role palette — every page in HTML and in Markdown (LibreFolio visual review).

    pipenv run python -m scripts.visual_review.build_designer_round <work>/snapshots/<after> \\
        --before <work>/snapshots/<before> --diff <work>/diffs/<before>__vs__<after> \\
        --inventory <work>/inventory/<after> --reasons <reasons.csv> --questions <questions.md> \\
        --name LibreFolio_review_colori_giro3_2026-10-16 [--round 3] [--lang it] [--format webp|png] \\
        [--palette .github/skills/design-tools/design-system/palette.md] [--copy-to ~/Downloads] [--work-dir <dir>]

Inputs:
    after, before   two gallery snapshots (gallery_snapshot.sh); the package shows the language --lang of both
    --diff          `gallery_tool diff <before> <after>` followed by `gallery_tool sheet`: its visible.json ranks the
                    before-and-after cards, the most visible change first
    --inventory     the output folder of `color_inventory.py --out`, run on the commit of <after>
    --reasons       why each file keeps legacy classes: `path;motivo;dettaglio;chi`, path under frontend/src
    --questions     the open questions (Markdown), copied as they are
    --palette       the role palette (Markdown), copied as it is; default: the design-system skill's palette.md

Output: <work>/package/<name>/ and <name>.zip (and a copy in --copy-to). The pages:
    LEGGIMI.md                                    the index, for an AI that reads Markdown
    APRI_QUI.html/.md                             the guide of the round
    desktop.html/.md, mobile.html/.md             the screens of today, light and dark side by side
    prima-e-dopo-desktop.html/.md, -mobile.*      before and after, light and dark, the most changed first
    colori-residui.html/.md                       the legacy palette classes left, file by file, by reason
    domande-aperte.md/.html, palette-ruoli.md/.html
    note_designer.txt, img/ (today), img/prima/ (before)
Every link is relative and descends from the package folder: it opens offline, from anywhere. WebP lossless keeps every
pixel of the PNG (the colours are exact) at about half its size; --format png keeps the PNG files.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import markdown
from PIL import Image

from scripts.visual_review import review_content as rc
from scripts.visual_review._common import REPO, work_dir
from scripts.visual_review.build_designer_package import NOTE_TEMPLATE, THEME_IT, VIEWPORTS, image_size, md_inline, page
from scripts.visual_review.navmap import load_navmap, resolve_ids

PALETTE_MD = REPO / ".github/skills/design-tools/design-system/palette.md"
EXTRA_CSS = """
table.cmp{border-collapse:collapse;width:100%}table.cmp td,table.cmp th{border:1px solid var(--line);padding:4px;vertical-align:top}
table.cmp th{font-size:12px;text-align:left;background:#fafafa}.mobile-cmp td{width:50%}
.badge{display:inline-block;font-size:12px;font-weight:600;padding:1px 7px;border-radius:9px;background:#e4e4e7;margin-left:6px}
.badge.new{background:#dcfce7;color:#14532d}.badge.gone{background:#fee2e2;color:#7f1d1d}.badge.size{background:#fef3c7;color:#713f12}
.md table{border-collapse:collapse;margin:8px 0}.md td,.md th{border:1px solid var(--line);padding:4px 8px;vertical-align:top;text-align:left}
.md h1{margin-top:4px}.chip{display:inline-block;width:14px;height:14px;border-radius:3px;border:1px solid rgba(127,127,127,.6);vertical-align:-2px;margin-right:4px}
.files td{font-size:13px}.files code{font-size:12px}
"""
#: The legacy colour classes beyond the palette families, as the colour gate defines them (LEGACY_COLOUR in theme-roles.mjs):
#: libre-* and primary-<shade>. A role utility (`text-lf-primary`) ends the same way and is not one.
LEGACY_CUSTOM = re.compile(r"(?<!-lf)-(libre-[a-z]+(?:-[a-z]+)*|primary-(?:50|[1-9]00))(/\d{1,3})?$")
NOT_A_COLOUR = {"transparent", "current"}
UNCLASSIFIED = "da-classificare"
REASON_TITLES = {
    "categoria": "Colori di categoria: restano, finché non ci sono i ruoli di categoria",
    "interruttore": "Interruttori: un colore per stato, in attesa del loro ruolo",
    "ruolo-mancante": "Manca un ruolo: serve una decisione",
    "attesa-1.3": "In attesa di un altro lavoro (1.3)",
    "in-lavorazione": "In lavorazione: vanno a zero a breve",
    UNCLASSIFIED: "Da classificare",
}


# ----------------------------------------------------------------------------- images
@dataclass
class Images:
    """The package's pictures: shots[cat][name][viewport][theme] → path under the package, for today and for before."""

    now: dict = field(default_factory=lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict))))
    before: dict = field(default_factory=lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict))))


def convert(job: tuple[str, str, str]) -> None:
    src, dest, fmt = job
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    if fmt == "png":
        shutil.copy2(src, dest)
        return
    with Image.open(src) as im:
        im.save(dest, format="WEBP", lossless=True, method=4)


def gather_images(snap: Path, root: str, lang: str, fmt: str, pkg: Path, table: dict) -> list[tuple[str, str, str]]:
    jobs = []
    for p in sorted((snap / "png").glob(f"*/{lang}/*/*/*.png")):
        vp, _lang, theme, cat, name = p.relative_to(snap / "png").with_suffix("").parts
        rel = f"{root}/{vp}/{theme}/{cat}/{name}.{fmt}"
        table[cat][name][vp][theme] = rel
        jobs.append((str(p), str(pkg / rel), fmt))
    return jobs


def collect_images(after: Path, before: Path, lang: str, fmt: str, pkg: Path) -> Images:
    images = Images()
    jobs = gather_images(after, "img", lang, fmt, pkg, images.now) + gather_images(before, "img/prima", lang, fmt, pkg, images.before)
    if not images.now:
        raise SystemExit(f"no '{lang}' screenshots in {after / 'png'}")
    workers = max(1, min(4, (os.cpu_count() or 2) // 2))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        list(pool.map(convert, jobs, chunksize=8))
    return images


# ----------------------------------------------------------------------------- navigation and order
def where_lines(shots: dict) -> tuple[dict[tuple[str, str], tuple[str, str]], dict[str, list[str]]]:
    """For every shot its «Dove/Dati» line, as HTML and as Markdown, and the shot order of every area."""
    rows, _ = load_navmap()
    where: dict[tuple[str, str], tuple[str, str]] = {}
    order: dict[str, list[str]] = {}
    for cat in shots:
        actual = set(shots[cat])
        seq: list[str] = []
        for cells in rows.get(cat, []):
            route, how, who = (cells + ["", "", "", "", ""])[2:5]
            for n in resolve_ids(cells[0], cat, actual):
                if n not in seq:
                    seq.append(n)
                where.setdefault((cat, n), (f"<b>Dove:</b> {md_inline(route)} — {md_inline(how)} · <b>Dati:</b> {md_inline(who)}", f"**Dove:** {route} — {how} · **Dati:** {who}"))
        order[cat] = seq + sorted(actual - set(seq))
    return where, order


def areas(shots: dict) -> list[str]:
    return [c for c in rc.ORDER if c in shots] + sorted(c for c in shots if c not in rc.ORDER)


def title(cat: str) -> str:
    return rc.TITLES.get(cat, cat)


def img_html(src: str, alt: str, pkg: Path) -> str:
    w, h = image_size(pkg / src)
    return f'<a href="{src}" target="_blank"><img loading="lazy" width="{w}" height="{h}" src="{src}" alt="{html.escape(alt)}"></a>'


# ----------------------------------------------------------------------------- the screens of today
def screens_page(pkg: Path, vp: str, images: Images, where: dict, order: dict, nav: str) -> None:
    shots = images.now
    vp_title, vp_size = VIEWPORTS[vp]
    toc, body, md = [], [], [f"# Schermate {vp_title.lower()} ({vp_size})", "", "Ogni schermata in tema chiaro e scuro. Nelle note citare il codice, per esempio `dashboard/kpi-top`.", ""]
    for cat in areas(shots):
        names = [n for n in order[cat] if vp in shots[cat][n]]
        if not names:
            continue
        toc.append(f'<li><a href="#area-{cat}"><b>{html.escape(title(cat))}</b></a> ({len(names)}): ' + ", ".join(f'<a href="#{cat}/{n}">{n}</a>' for n in names) + "</li>")
        body.append(f'<h2 id="area-{cat}">{html.escape(title(cat))} <span class=small>— <code>{cat}</code></span></h2>')
        md += [f"## {title(cat)} — `{cat}`", ""]
        for n in names:
            figs, lines = [], []
            for th in ("light", "dark"):
                src = shots[cat][n][vp].get(th)
                figs.append(f"<figure><figcaption>{THEME_IT[th]}</figcaption>{img_html(src, f'{cat}/{n} {THEME_IT[th]}', pkg)}</figure>" if src else f"<figure><figcaption>{THEME_IT[th]}: —</figcaption></figure>")
                lines.append(f"- {THEME_IT[th]}: ![{cat}/{n} {THEME_IT[th]}]({src})" if src else f"- {THEME_IT[th]}: —")
            w_html, w_md = where.get((cat, n), ("", ""))
            body.append(f'<section class=card id="{cat}/{n}"><h3><code>{cat}/{n}</code></h3><p class=where>{w_html}</p><div class="row {vp}">{"".join(figs)}</div></section>')
            md += [f"### `{cat}/{n}`", "", w_md, "", *lines, ""]
    intro = f'<h1>Schermate {vp_title.lower()} <span class=small>({vp_size})</span></h1><p class=small>Chiaro a sinistra, scuro a destra; clic per la piena grandezza. Nelle note citare il codice giallo della card.</p><div class=box><b>Aree</b><ul class=toc>{"".join(toc)}</ul></div>'
    (pkg / f"{vp}.html").write_text(page(f"LibreFolio — schermate {vp}", nav, intro + "".join(body)), encoding="utf-8")
    (pkg / f"{vp}.md").write_text("\n".join(md) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------- before and after
def ranking(diff: Path, lang: str, vp: str) -> dict[str, dict]:
    """Per shot of this language and viewport: the visible change (pixels over 12 levels, %) of each theme and the status."""
    per_image = json.loads((diff / "visible.json").read_text())["per_image"]
    out: dict[str, dict] = defaultdict(dict)
    for rel, rec in per_image.items():
        parts = rel[:-4].split("/")
        if len(parts) == 5 and parts[0] == vp and parts[1] == lang:
            out[f"{parts[3]}/{parts[4]}"][parts[2]] = rec
    return out


def change_label(themes: dict) -> tuple[float, str]:
    vis = {th: float(rec.get("vis12", 0.0)) for th, rec in themes.items()}
    score = statistics.mean(vis.values()) if vis else 0.0
    parts = ", ".join(f"{THEME_IT[th]} {v:.1f} %" for th, v in sorted(vis.items(), key=lambda kv: kv[0] != "light"))
    return score, parts


#: The badge of a before-and-after card: its CSS class and its text.
BADGES = {"new": "nuova, senza un prima", "gone": "sparita", "size": "altra altezza"}


def compare_card(cat: str, n: str, vp: str, images: Images, where: dict, pkg: Path, kind: str, label: str) -> tuple[str, list[str]]:
    badge = BADGES.get(kind, "")
    rows_html, rows_md = [], [f"### `{cat}/{n}`{' — ' + badge if badge else ''}", "", where.get((cat, n), ("", ""))[1], ""]
    if label:
        rows_md += [f"Cambio visibile (pixel che cambiano di più di 12 livelli): {label}.", ""]
    rows_md += ["| | prima (v1.2) | dopo (oggi) |", "|---|---|---|"]
    for th in ("light", "dark"):
        before, after = images.before[cat][n][vp].get(th), images.now[cat][n][vp].get(th)
        cell_b = img_html(before, f"{cat}/{n} {THEME_IT[th]} prima", pkg) if before else "—"
        cell_a = img_html(after, f"{cat}/{n} {THEME_IT[th]} dopo", pkg) if after else "—"
        rows_html.append(f"<tr><th>{THEME_IT[th]}</th><td>{cell_b}</td><td>{cell_a}</td></tr>")
        md_b = f"![{cat}/{n} {THEME_IT[th]} prima]({before})" if before else "—"
        md_a = f"![{cat}/{n} {THEME_IT[th]} dopo]({after})" if after else "—"
        rows_md.append(f"| {THEME_IT[th]} | {md_b} | {md_a} |")
    badge_html = f' <span class="badge {kind}">{html.escape(badge)}</span>' if badge else ""
    measure = f"<p class=small>Cambio visibile (pixel oltre 12 livelli): {html.escape(label)}</p>" if label else ""
    section = f'<section class=card id="{cat}/{n}"><h3><code>{cat}/{n}</code>{badge_html}</h3><p class=where>{where.get((cat, n), ("", ""))[0]}</p>{measure}<table class="cmp {vp}-cmp"><tr><th></th><th>prima (v1.2)</th><th>dopo (oggi)</th></tr>{"".join(rows_html)}</table></section>'
    return section, [*rows_md, ""]


def comparison_order(images: Images, rank: dict, vp: str) -> tuple[list[tuple[str, str, str, str]], int]:
    """The cards of a viewport, as (area, name, badge kind, change label): new and gone shots first, then the most visible change first."""
    keys = {(c, n) for c in images.now for n in images.now[c] if vp in images.now[c][n]} | {(c, n) for c in images.before for n in images.before[c] if vp in images.before[c][n]}
    cards = []
    for cat, n in keys:
        has_now, has_before = vp in images.now[cat][n], vp in images.before[cat][n]
        themes = rank.get(f"{cat}/{n}", {})
        score, label = change_label(themes)
        if not has_before:
            cards.append((0, -1.0, cat, n, "new", ""))
        elif not has_now:
            cards.append((1, -1.0, cat, n, "gone", ""))
        else:
            sized = any(rec.get("status") == "size_changed" for rec in themes.values())
            cards.append((2, -score, cat, n, "size" if sized else "", label))
    cards.sort()
    return [(cat, n, kind, label) for _, _, cat, n, kind, label in cards], sum(1 for c in cards if c[0] == 2)


def comparison_page(pkg: Path, vp: str, images: Images, diff: Path, lang: str, where: dict, dates: tuple[str, str], nav: str) -> None:
    rank = ranking(diff, lang, vp)
    cards, compared = comparison_order(images, rank, vp)
    note = f"Prima: la v1.2, schermate del {dates[0]}. Dopo: oggi, schermate del {dates[1]}. I dati di esempio seguono il giorno della cattura: numeri, date e grafici cambiano anche per questo. Il confronto dei colori resta valido."
    body, md = [], [f"# Prima e dopo — {VIEWPORTS[vp][0].lower()}", "", f"> {note}", "", f"Ordine: prima le schermate nuove e quelle sparite, poi le {compared} confrontate, dalla più cambiata. La misura è la quota di pixel che cambiano di più di 12 livelli.", ""]
    for cat, n, kind, label in cards:
        section, lines = compare_card(cat, n, vp, images, where, pkg, kind, label)
        body.append(section)
        md += lines
    intro = f"<h1>Prima e dopo — {VIEWPORTS[vp][0].lower()}</h1><div class=box><p><b>Da sapere:</b> {html.escape(note)}</p><p class=small>Ordine: prima le schermate nuove e quelle sparite, poi le {compared} confrontate, dalla più cambiata. La misura è la quota di pixel che cambiano di più di 12 livelli (chiaro, scuro).</p></div>"
    (pkg / f"prima-e-dopo-{vp}.html").write_text(page(f"LibreFolio — prima e dopo, {vp}", nav, intro + "".join(body)), encoding="utf-8")
    (pkg / f"prima-e-dopo-{vp}.md").write_text("\n".join(md) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------- the colours left
GATE_MODULE = REPO / "frontend/scripts/theme/theme-roles.mjs"
# The colour gate's own reading of a source: production files only (no .css, tests, generated files), comments blanked
# with their line breaks kept — so an inventory row (file, line) can be checked against the code a user's screen runs.
GATE_CODE = """
import {codeOf, isProductionSource} from %s;
import {readFileSync} from 'node:fs';
const files = JSON.parse(readFileSync(0, 'utf8'));
const out = {};
for (const rel of files) if (isProductionSource(rel)) out[rel] = [readFileSync(%s + '/' + rel, 'utf8'), codeOf(rel, readFileSync(%s + '/' + rel, 'utf8'))];
process.stdout.write(JSON.stringify(out));
"""


def gate_code(files: list[str]) -> dict[str, tuple[list[str], list[str]]]:
    """For each production file: its lines as written and without comments, read by theme-roles.mjs (node)."""
    src = json.dumps(str(REPO / "frontend" / "src"))
    script = GATE_CODE % (json.dumps(GATE_MODULE.as_uri()), src, src)
    result = subprocess.run(["node", "--input-type=module", "-e", script], input=json.dumps(files), capture_output=True, text=True, check=True)
    return {rel: (raw.split("\n"), code.split("\n")) for rel, (raw, code) in json.loads(result.stdout).items()}


def inventory_rows(inventory: Path) -> list[tuple[str, int, str]]:
    """The legacy colour classes of color_inventory.py, as (path under frontend/src, line, class): palette families with a
    shade, white and black, and the old custom tokens; test files, transparent and currentColor left out."""
    rows = []
    with open(inventory / "tailwind_color_classes.csv", newline="", encoding="utf-8") as f:
        rows += [(r["file"].removeprefix("src/"), int(r["line"]), r["raw"]) for r in csv.DictReader(f) if r["is_test"] != "True" and r["family"] not in NOT_A_COLOUR]
    with open(inventory / "custom_token_classes.csv", newline="", encoding="utf-8") as f:
        rows += [(r["file"].removeprefix("src/"), int(r["line"]), r["raw"]) for r in csv.DictReader(f) if r["is_test"] != "True" and LEGACY_CUSTOM.search(r["raw"])]
    return rows


def legacy_classes(inventory: Path) -> tuple[dict[str, Counter], dict[str, int]]:
    """Production files under frontend/src → their legacy colour classes in code, counted. color_inventory.py reads raw
    lines: a class named in a comment, or in app.css's legacy remap, is not a colour on screen, and is left out here."""
    rows = inventory_rows(inventory)
    code = gate_code(sorted({rel for rel, _, _ in rows}))
    found: dict[str, Counter] = defaultdict(Counter)
    left_out = Counter()
    for rel, line, raw in rows:
        if rel not in code:
            left_out["not a production source (css, test, generated)"] += 1
            continue
        written, blanked = code[rel]
        if line > len(written) or raw not in written[line - 1]:
            left_out["stale: the inventory is of another commit"] += 1
        elif raw not in blanked[line - 1]:
            left_out["in a comment"] += 1
        else:
            found[rel][raw] += 1
    return found, dict(left_out)


def read_reasons(path: Path) -> dict[str, dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return {row["path"].strip(): row for row in csv.DictReader(f, delimiter=";")}


def palette_values() -> dict[str, str]:
    """The colours the build defines for the legacy classes: Tailwind's `--color-<family>-<shade>`, and `libre-*` and
    `primary-*`. The first definition wins: the base theme's, before any override."""
    assets = sorted((REPO / "frontend/build/_app/immutable/assets").glob("*.css"), key=lambda p: p.stat().st_size, reverse=True)
    if not assets:
        print("warning: no frontend build: the colours left show no swatch", file=sys.stderr)
        return {}
    values: dict[str, str] = {}
    for name, value in re.findall(r"--color-([a-z]+-\d+|libre-[a-z-]+):\s*(oklch\([^)]*\)|#[0-9a-fA-F]{3,8})", assets[0].read_text(encoding="utf-8")):
        values.setdefault(name, value)
    return values


def colour_of(cls: str, tw: dict[str, str]) -> str | None:
    """The colour a legacy class paints, from the build's Tailwind variables: `dark:hover:bg-slate-700/50` → slate-700."""
    base = cls.split(":")[-1].split("/")[0]
    found = re.search(r"-(?:(white|black)|((?:[a-z]+)-(?:50|[1-9]00|950))|(libre-[a-z-]+))$", base)
    if not found:
        return None
    if found.group(1):
        return "#ffffff" if found.group(1) == "white" else "#000000"
    return tw.get(found.group(2) or found.group(3))


def residual_rows(found: dict[str, Counter], reasons: dict[str, dict]) -> tuple[dict[str, list[tuple[str, Counter, dict]]], list[str]]:
    groups: dict[str, list[tuple[str, Counter, dict]]] = defaultdict(list)
    for path, classes in sorted(found.items()):
        reason = reasons.get(path, {"motivo": UNCLASSIFIED, "dettaglio": "non è nell'elenco dei motivi", "chi": "—"})
        groups[reason["motivo"]].append((path, classes, reason))
    resolved = sorted(p for p in reasons if p not in found)
    return groups, resolved


def class_cells(classes: Counter, tw: dict[str, str]) -> tuple[str, str]:
    """The classes of a file with their counts and colours, as HTML (with a chip) and as Markdown (with the value)."""
    html_parts, md_parts = [], []
    for cls, n in sorted(classes.items(), key=lambda kv: (-kv[1], kv[0])):
        value = colour_of(cls, tw)
        chip = f'<i class=chip style="background:{html.escape(value)}"></i>' if value else ""
        html_parts.append(f"{chip}<code>{html.escape(cls)}</code> ×{n}")
        md_parts.append(f"`{cls}` ×{n}" + (f" ({value})" if value else ""))
    return "<br>".join(html_parts), "; ".join(md_parts)


def residual_page(pkg: Path, inventory: Path, reasons_csv: Path, after_commit: str, nav: str) -> list[str]:
    (found, left_out), reasons, tw = legacy_classes(inventory), read_reasons(reasons_csv), palette_values()
    if left_out.get("stale: the inventory is of another commit"):
        print(f"warning: {left_out['stale: the inventory is of another commit']} inventory rows do not match this checkout: run color_inventory.py at the snapshot's commit", file=sys.stderr)
    groups, resolved = residual_rows(found, reasons)
    total = sum(sum(c.values()) for c in found.values())
    skipped = f" Lasciate fuori {sum(left_out.values())} occorrenze che non dipingono niente: nominate in un commento o nelle regole di `app.css`." if left_out else ""
    head = f"Classi di colore della vecchia palette ancora nel codice al commit `{after_commit[:10]}`: **{total}** in **{len(found)}** file (inventario `color_inventory.py`, file di test esclusi).{skipped} Ogni file ha il suo motivo; i campioni mostrano il colore che la classe dipinge oggi."
    md = ["# Colori residui", "", head, "", "| Motivo | File | Classi |", "|---|---:|---:|"]
    md += [f"| {REASON_TITLES.get(r, r)} | {len(rows)} | {sum(sum(c.values()) for _, c, _ in rows)} |" for r, rows in sorted(groups.items(), key=lambda kv: list(REASON_TITLES).index(kv[0]) if kv[0] in REASON_TITLES else 99)]
    body = [f"<h1>Colori residui</h1><div class=box><p>{md_inline(head)}</p></div>"]
    for reason, rows in sorted(groups.items(), key=lambda kv: list(REASON_TITLES).index(kv[0]) if kv[0] in REASON_TITLES else 99):
        md += ["", f"## {REASON_TITLES.get(reason, reason)} ({len(rows)} file)", "", "| File | Perché | Chi | Classi |", "|---|---|---|---|"]
        trs = []
        for path, classes, why in sorted(rows, key=lambda r: -sum(r[1].values())):
            cells_html, cells_md = class_cells(classes, tw)
            md.append(f"| `{path}` ({sum(classes.values())}) | {why['dettaglio']} | {why['chi']} | {cells_md} |")
            trs.append(f"<tr><td><code>{html.escape(path)}</code><br><span class=small>{sum(classes.values())} classi</span></td><td>{html.escape(why['dettaglio'])}</td><td>{html.escape(why['chi'])}</td><td>{cells_html}</td></tr>")
        body.append(f"<h2>{html.escape(REASON_TITLES.get(reason, reason))} <span class=small>({len(rows)} file)</span></h2><table class='pal files'><tr><th>File</th><th>Perché</th><th>Chi</th><th>Classi</th></tr>{''.join(trs)}</table>")
    if resolved:
        md += ["", f"## Già migrati ({len(resolved)} file nell'elenco dei motivi, oggi senza classi)", ""] + [f"- `{p}`" for p in resolved]
        body.append(f"<h2>Già migrati <span class=small>({len(resolved)} file nell'elenco dei motivi, oggi senza classi)</span></h2><ul>" + "".join(f"<li><code>{html.escape(p)}</code></li>" for p in resolved) + "</ul>")
    (pkg / "colori-residui.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (pkg / "colori-residui.html").write_text(page("LibreFolio — colori residui", nav, "".join(body)), encoding="utf-8")
    return [path for path, _, _ in groups.get(UNCLASSIFIED, [])]


# ----------------------------------------------------------------------------- copied Markdown pages
HEX_CODE = re.compile(r"<code>(#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?)</code>")
REPO_LINK = re.compile(r'<a href="(?!https?:|#)([^"]+)">(.*?)</a>')


#: The files of the package a page may link to.
PACKAGE_FILES = {"APRI_QUI.html", "desktop.html", "mobile.html", "prima-e-dopo-desktop.html", "prima-e-dopo-mobile.html", "colori-residui.html", "domande-aperte.html", "palette-ruoli.html", "LEGGIMI.md", "note_designer.txt"}


def package_link(match: re.Match) -> str:
    """A link of a rendered page: to a page of the package (its HTML when it has one), or plain text when it points into
    the repository, which the package does not hold."""
    href, label = match.group(1), match.group(2)
    target, fragment = (href.split("#", 1) + [""])[:2]
    if target.endswith(".md") and f"{target[:-3]}.html" in PACKAGE_FILES:
        return f'<a href="{target[:-3]}.html{"#" + fragment if fragment else ""}">{label}</a>'
    return match.group(0) if target in PACKAGE_FILES else label


def render_markdown(text: str) -> str:
    """Markdown to HTML for the package: a chip before every #hex code, and the links made safe (package_link)."""
    rendered = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    rendered = HEX_CODE.sub(lambda m: f'<i class=chip style="background:{m.group(1)}"></i><code>{m.group(1)}</code>', rendered)
    return REPO_LINK.sub(package_link, rendered)


def copied_page(pkg: Path, src: Path, stem: str, heading: str, nav: str) -> None:
    text = src.read_text(encoding="utf-8")
    (pkg / f"{stem}.md").write_text(text, encoding="utf-8")
    (pkg / f"{stem}.html").write_text(page(f"LibreFolio — {heading}", nav, f"<div class='box md'>{render_markdown(text)}</div>"), encoding="utf-8")


# ----------------------------------------------------------------------------- guide and index
@dataclass
class Facts:
    round_no: int
    name: str
    after: dict
    before: dict
    counts: dict
    fmt: str


def guide_markdown(f: Facts) -> str:
    a, b = f.after, f.before
    return f"""# LibreFolio — review dei colori, giro {f.round_no}

Grazie ancora! Questo pacchetto mostra l'app **com'è oggi**, dopo la migrazione dei colori ai ruoli, e la confronta con
la **v1.2** che hai visto nel primo giro.

## Cosa c'è

- [Schermate desktop](desktop.md) e [schermate mobile](mobile.md): lo stato di oggi, {f.counts['now_shots']} schermate,
  ognuna in tema chiaro e scuro.
- [Prima e dopo, desktop](prima-e-dopo-desktop.md) e [mobile](prima-e-dopo-mobile.md): per ogni schermata la v1.2
  accanto a oggi, chiaro e scuro, dalla più cambiata. In testa, per ogni dispositivo, le schermate nuove e quelle
  sparite.
- [Colori residui](colori-residui.md): le classi della vecchia palette ancora nel codice, file per file, con il motivo
  e il colore che dipingono.
- [Domande aperte](domande-aperte.md): tutto quello su cui ci serve il tuo parere.
- [Palette dei ruoli](palette-ruoli.md): ogni ruolo di colore, con il valore in chiaro e in scuro e quando si usa.
- `note_designer.txt`: un modello per le tue note.
- Ogni pagina c'è anche in Markdown (`.md`), con le immagini per percorso relativo: l'indice è [`LEGGIMI.md`](LEGGIMI.md).

## Come citare

Ogni schermata ha un codice, per esempio `dashboard/kpi-top`. Nelle note: codice · chiaro, scuro o entrambi · desktop,
mobile o entrambi. Esempio: `dashboard/kpi-top · scuro · desktop: il verde delle variazioni è troppo acceso`.

## Da sapere

- Oggi: commit `{str(a.get('commit', '?'))[:10]}`, schermate del {a.get('started', '?')[:10]}. Prima: v1.2, commit
  `{str(b.get('commit', '?'))[:10]}`, schermate del {b.get('started', '?')[:10]}.
- I dati sono di esempio e seguono il giorno della cattura: fra prima e dopo cambiano anche numeri, date e grafici.
- Animazioni ferme, nessun passaggio del mouse: hover, focus e menu si valutano dal vivo.
- Desktop 1280×720 (alcune schermate più alte, per mostrare un blocco intero); mobile 430×932.
- {"Le immagini sono WebP senza perdita: i pixel sono quelli catturati, colori esatti." if f.fmt == "webp" else "Le immagini sono i PNG catturati."}
- **Fedeltà dei colori:** le immagini sono in sRGB, mentre molti colori dell'interfaccia sono definiti in OKLCH: su un
  Mac recente l'app dal vivo può apparire un po' più satura. Per confronti fedeli: zoom 100 %, luminosità costante.
"""


def index_markdown(f: Facts, unclassified: list[str]) -> str:
    ext = f.fmt
    note = f"\nNota: {len(unclassified)} file con classi residue non hanno ancora un motivo: sono in «Da classificare».\n" if unclassified else ""
    return f"""# LEGGIMI — indice del pacchetto `{f.name}`

Review dei colori di LibreFolio, giro {f.round_no}. Tutto è in Markdown e in HTML; i percorsi sono relativi a questa
cartella. Leggere prima la guida.

| File | Contenuto |
|---|---|
| `APRI_QUI.md` | La guida: cosa c'è, come citare, cosa sapere |
| `domande-aperte.md` | Le domande aperte per la designer: **il cuore del giro** |
| `palette-ruoli.md` | Ogni ruolo di colore: utility, valore in chiaro e in scuro, quando si usa (in inglese) |
| `colori-residui.md` | Le classi della vecchia palette rimaste, file per file, con motivo e colore |
| `desktop.md`, `mobile.md` | Le schermate di oggi, per area, in chiaro e in scuro ({f.counts['now_images']} immagini) |
| `prima-e-dopo-desktop.md`, `prima-e-dopo-mobile.md` | La v1.2 accanto a oggi, dalla schermata più cambiata |
| `note_designer.txt` | Il modello per le note |

## Convenzioni

- Codice di una schermata: `<area>/<nome>`, per esempio `dashboard/kpi-top`.
- Immagini di oggi: `img/<desktop|mobile>/<light|dark>/<area>/<nome>.{ext}`; della v1.2:
  `img/prima/<desktop|mobile>/<light|dark>/<area>/<nome>.{ext}`. `light` = chiaro, `dark` = scuro.
- Misura del cambiamento: la quota di pixel che cambiano di più di 12 livelli (su 255) fra prima e dopo.
- Nei file copiati (`palette-ruoli.md`, `domande-aperte.md`) i link a file del repository non funzionano qui: il loro
  testo basta.
{note}"""


def write_markdown_page(pkg: Path, stem: str, text: str, heading: str, nav: str) -> None:
    (pkg / f"{stem}.md").write_text(text, encoding="utf-8")
    (pkg / f"{stem}.html").write_text(page(f"LibreFolio — {heading}", nav, f"<div class='box md'>{render_markdown(text)}</div>"), encoding="utf-8")


# ----------------------------------------------------------------------------- main
NAV_ITEMS = [
    ("APRI_QUI.html", "Guida"),
    ("desktop.html", "Desktop"),
    ("mobile.html", "Mobile"),
    ("prima-e-dopo-desktop.html", "Prima/dopo desktop"),
    ("prima-e-dopo-mobile.html", "Prima/dopo mobile"),
    ("colori-residui.html", "Colori residui"),
    ("domande-aperte.html", "Domande"),
    ("palette-ruoli.html", "Palette"),
]


def nav_bar(current: str, round_no: int, date: str) -> str:
    links = " ".join(f'<a href="{h}">{"▸ " if h == current else ""}{t}</a>' for h, t in NAV_ITEMS)
    return f"<b>LibreFolio — colori, giro {round_no}</b> {links}<span class=sp></span><span class=small style='color:#a1a1aa'>schermate del {date}</span>"


def counts_of(images: Images) -> dict[str, int]:
    now = {(c, n) for c in images.now for n in images.now[c]}
    before = {(c, n) for c in images.before for n in images.before[c]}
    return {
        "now_shots": len(now),
        "now_images": sum(len(t) for c in images.now for n in images.now[c] for t in images.now[c][n].values()),
        "before_images": sum(len(t) for c in images.before for n in images.before[c] for t in images.before[c][n].values()),
        "new": len(now - before),
        "gone": len(before - now),
    }


def build(args: argparse.Namespace, pkg: Path) -> tuple[Facts, list[str]]:
    after, before, diff = (Path(p).expanduser().resolve() for p in (args.snapshot, args.before, args.diff))
    meta_a, meta_b = (json.loads((s / "meta.json").read_text()) for s in (after, before))
    images = collect_images(after, before, args.lang, args.format, pkg)
    where, order = where_lines(images.now)
    for cat, names in images.before.items():
        where_b, _ = where_lines({cat: names})
        for key, value in where_b.items():
            where.setdefault(key, value)
    date = meta_a.get("started", "?")[:10]
    facts = Facts(args.round, args.name, meta_a, meta_b, counts_of(images), args.format)
    for vp in VIEWPORTS:
        screens_page(pkg, vp, images, where, order, nav_bar(f"{vp}.html", args.round, date))
        comparison_page(pkg, vp, images, diff, args.lang, where, (meta_b.get("started", "?")[:10], date), nav_bar(f"prima-e-dopo-{vp}.html", args.round, date))
    checkout = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    if checkout != meta_a.get("commit"):
        print(f"warning: this checkout is at {checkout[:10]}, the snapshot at {str(meta_a.get('commit'))[:10]}: the colours left are the checkout's", file=sys.stderr)
    unclassified = residual_page(pkg, Path(args.inventory).expanduser().resolve(), Path(args.reasons).expanduser().resolve(), checkout, nav_bar("colori-residui.html", args.round, date))
    copied_page(pkg, Path(args.questions).expanduser().resolve(), "domande-aperte", "domande aperte", nav_bar("domande-aperte.html", args.round, date))
    copied_page(pkg, Path(args.palette).expanduser().resolve(), "palette-ruoli", "palette dei ruoli", nav_bar("palette-ruoli.html", args.round, date))
    write_markdown_page(pkg, "APRI_QUI", guide_markdown(facts), "guida", nav_bar("APRI_QUI.html", args.round, date))
    (pkg / "LEGGIMI.md").write_text(index_markdown(facts, unclassified), encoding="utf-8")
    (pkg / "note_designer.txt").write_text(NOTE_TEMPLATE.replace("(review colori)", f"(review colori, giro {args.round})"), encoding="utf-8")
    return facts, unclassified


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snapshot", help="the snapshot of today (after)")
    ap.add_argument("--before", required=True, help="the snapshot to compare with (before)")
    ap.add_argument("--diff", required=True, help="gallery_tool diff <before> <after>, then gallery_tool sheet on it")
    ap.add_argument("--inventory", required=True, help="color_inventory.py --out folder, run on the commit of the snapshot")
    ap.add_argument("--reasons", required=True, help="path;motivo;dettaglio;chi — why each file keeps legacy classes")
    ap.add_argument("--questions", required=True, help="the open questions, Markdown, copied as they are")
    ap.add_argument("--palette", default=str(PALETTE_MD), help="the role palette, Markdown, copied as it is")
    ap.add_argument("--name", required=True)
    ap.add_argument("--round", type=int, default=3)
    ap.add_argument("--lang", default="it")
    ap.add_argument("--format", choices=("webp", "png"), default="webp")
    ap.add_argument("--copy-to", help="also copy the zip into this folder (e.g. ~/Downloads)")
    ap.add_argument("--work-dir", help="output root outside the repository")
    args = ap.parse_args()
    out_root = work_dir(args.work_dir) / "package"
    pkg = out_root / args.name
    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True)
    started = datetime.now()
    facts, unclassified = build(args, pkg)
    for page_html in pkg.glob("*.html"):
        page_html.write_text(page_html.read_text(encoding="utf-8").replace("</style>", EXTRA_CSS + "</style>", 1), encoding="utf-8")
    zip_path = Path(shutil.make_archive(str(out_root / args.name), "zip", root_dir=out_root, base_dir=args.name))
    if args.copy_to:
        shutil.copy2(zip_path, Path(args.copy_to).expanduser() / zip_path.name)
    size = sum(p.stat().st_size for p in pkg.rglob("*") if p.is_file())
    print(f"package → {pkg}: {facts.counts['now_images']} images today, {facts.counts['before_images']} before, {facts.counts['new']} new and {facts.counts['gone']} gone shots; {size / 1e6:.0f} MB; zip {zip_path.stat().st_size / 1e6:.0f} MB; {(datetime.now() - started).seconds} s")
    if unclassified:
        print(f"da classificare: {len(unclassified)} file without a reason: {', '.join(unclassified)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
