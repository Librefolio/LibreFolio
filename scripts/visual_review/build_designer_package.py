#!/usr/bin/env python3
"""Build the self-contained designer package from a gallery snapshot (LibreFolio visual review).

    pipenv run python -m scripts.visual_review.build_designer_package <work>/snapshots/<label> \\
        [--lang it] [--name LibreFolio_review_colori_v1.2] [--work-dir <dir>]

Output: <work>/package/<name>/ (APRI_QUI.html, desktop.html, mobile.html, note_designer.txt, img/) and
<work>/package/<name>.zip. Every page uses descendant paths only, so the unzipped folder opens offline by a
double click on APRI_QUI.html, from any location and in any browser.

Review-specific texts (area titles, hints, palette table, questions) live in review_content.py; the
navigation lines come from data/navigation_map.it.md. Tailwind swatches show the real OKLCH values of the
current frontend build (frontend/build), so build the frontend first for an accurate palette table.
"""

from __future__ import annotations

import argparse
import glob
import html
import json
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image

from scripts.visual_review import review_content as rc
from scripts.visual_review._common import REPO, work_dir
from scripts.visual_review.navmap import load_navmap, resolve_ids

VIEWPORTS = {"desktop": ("Desktop", "1280×720"), "mobile": ("Mobile", "430×932, iPhone 14 Pro Max")}
THEME_IT = {"light": "chiaro", "dark": "scuro"}
NOTE_TEMPLATE = (
    "LibreFolio — Note della designer (review colori)\nData:\n\n"
    "Formato consigliato (una nota per riga o per blocco):\n"
    "  <nome card> · <chiaro | scuro | entrambi> · <desktop | mobile | entrambi>: nota\n"
    "Esempio:\n"
    "  dashboard/kpi-top · scuro · desktop: il verde delle variazioni positive è troppo acceso rispetto al resto\n\n"
    "== Note generali (palette, ruoli dei colori, idee) ==\n\n\n"
    "== Note per schermata ==\n\n"
)

CSS = """
:root{--bg:#f4f4f5;--card:#fff;--ink:#18181b;--mute:#52525b;--line:#d4d4d8}
*{box-sizing:border-box}body{font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:var(--bg);color:var(--ink)}
main{max-width:1500px;margin:0 auto;padding:20px}a{color:#1d4ed8}code{font:13px ui-monospace,Menlo,monospace;background:#e4e4e7;padding:1px 5px;border-radius:4px}
.top{position:sticky;top:0;z-index:5;background:#18181b;color:#fff;padding:10px 20px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
.top a{color:#fff;font-weight:600}.top .sp{flex:1}
section.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:14px 0;scroll-margin-top:60px}
section.card h3{margin:0 0 2px;font-size:16px}section.card h3 code{font-size:15px;background:#fef3c7;color:#713f12}
.where{color:var(--mute);font-size:13px;margin:0 0 8px}.row{display:flex;gap:12px;align-items:flex-start}
figure{margin:0;flex:1;min-width:0}.mobile figure{flex:0 1 auto;max-width:49%}figcaption{font-size:12px;font-weight:700;margin-bottom:3px}
img{display:block;max-width:100%;height:auto;border:1px solid var(--line)}
details{background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:6px 10px;margin:6px 0 10px}summary{cursor:pointer;font-weight:600}
h2{margin:30px 0 4px;padding-top:10px;border-top:2px solid var(--line)}.toc li{margin:3px 0}.small{font-size:13px;color:var(--mute)}
table.pal{border-collapse:collapse;width:100%;background:#fff}table.pal td,table.pal th{border:1px solid var(--line);padding:6px 8px;vertical-align:top;text-align:left}
td.dk{background:#0f172a;color:#e2e8f0}.sw{display:inline-block;margin:2px 6px 2px 0;text-align:center;font-size:10px;line-height:1.2;max-width:92px}
.sw i{display:block;width:44px;height:26px;border-radius:5px;border:1px solid rgba(127,127,127,.5);margin:0 auto 2px}
.sample{font-weight:600}.box{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin:14px 0}
.box h2{border:0;margin-top:0;padding:0}
"""


def md_inline(s: str) -> str:
    """Markdown inline (`code`, **bold**, *italic*) to HTML, escaping everything else."""
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    return re.sub(r"(?<![*\w])\*([^*]+)\*(?![*\w])", r"<i>\1</i>", s)


def tailwind_values() -> dict[str, str]:
    """Tailwind v4 colour variables of the current frontend build (largest CSS asset)."""
    assets = glob.glob(str(REPO / "frontend/build/_app/immutable/assets/*.css"))
    if not assets:
        print("warning: no frontend build found — Tailwind swatches will show 'n/d'", file=sys.stderr)
        return {}
    css = Path(max(assets, key=lambda p: Path(p).stat().st_size)).read_text()
    vals: dict[str, str] = {}
    for name, val in re.findall(r"--color-([a-z]+-\d+):\s*(oklch\([^)]*\)|#[0-9a-fA-F]{3,8})", css):
        vals.setdefault(name, val)
    return vals


def swatch(spec: str, kind: str, tw: dict[str, str], dark: bool) -> str:
    if spec.startswith("tw:"):
        name = spec[3:]
        val = tw.get(name)
        label = f"{name}<br>{html.escape(val) if val else 'n/d'}"
    else:
        val, label = spec, spec
    if not val:
        return f'<span class="sw">{label}</span>'
    if kind == "text":
        bg = "#1e293b" if dark else "#ffffff"
        return f'<span class="sw"><i style="background:{bg};display:flex;align-items:center;justify-content:center"><b class="sample" style="color:{val}">Aa</b></i>{label}</span>'
    return f'<span class="sw"><i style="background:{val}"></i>{label}</span>'


def image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size


def page(title: str, nav: str, body: str) -> str:
    return f'<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' f"<title>{html.escape(title)}</title><style>{CSS}</style><div class=top>{nav}</div><main>{body}</main></html>"


Shots = dict[str, dict[str, dict[str, dict[str, str]]]]


def collect_shots(snap: Path, pkg: Path, lang: str) -> Shots:
    """Copy the screenshots of one language into pkg/img/<viewport>/<theme>/<category>/<name>.png."""
    shots: Shots = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for p in sorted((snap / "png").glob(f"*/{lang}/*/*/*.png")):
        vp, _lang, theme, cat, name = p.relative_to(snap / "png").with_suffix("").parts
        dest = pkg / "img" / vp / theme / cat / f"{name}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        shots[cat][name][vp][theme] = str(dest.relative_to(pkg))
    if not shots:
        raise SystemExit(f"no '{lang}' screenshots in {snap / 'png'}")
    return shots


def navigation(shots: Shots) -> tuple[dict[tuple[str, str], str], dict[str, list[str]]]:
    """Return the «Dove/Dati» line of every shot and the shot order of every area (navigation map order first)."""
    rows, _ = load_navmap()
    where: dict[tuple[str, str], str] = {}
    order: dict[str, list[str]] = {}
    for cat in shots:
        actual = set(shots[cat])
        seq: list[str] = []
        for cells in rows.get(cat, []):
            route, how, who = (cells + ["", "", "", "", ""])[2:5]
            for n in resolve_ids(cells[0], cat, actual):
                if n not in seq:
                    seq.append(n)
                where.setdefault((cat, n), f"<b>Dove:</b> {md_inline(route)} — {md_inline(how)} · <b>Dati:</b> {md_inline(who)}")
        order[cat] = seq + sorted(actual - set(seq))
    return where, order


def card(cat: str, n: str, vp: str, shots: Shots, pkg: Path, where: dict[tuple[str, str], str]) -> str:
    figs = []
    for th in ("light", "dark"):
        src = shots[cat][n][vp].get(th)
        if not src:
            figs.append(f"<figure><figcaption>{THEME_IT[th]}: —</figcaption></figure>")
            continue
        w, h = image_size(pkg / src)
        figs.append(f'<figure><figcaption>{THEME_IT[th]}</figcaption><a href="{src}" target="_blank"><img loading="lazy" width="{w}" height="{h}" src="{src}" alt="{cat}/{n} {THEME_IT[th]}"></a></figure>')
    other = "mobile" if vp == "desktop" else "desktop"
    alt = f' · <a href="{other}.html#{cat}/{n}">versione {other}</a>' if other in shots[cat][n] else ""
    return f'<section class=card id="{cat}/{n}"><h3><code>{cat}/{n}</code></h3><p class=where>{where.get((cat, n), "")}{alt}</p><div class="row {vp}">{"".join(figs)}</div></section>'


def write_viewport_page(pkg: Path, vp: str, cats: list[str], shots: Shots, order: dict[str, list[str]], where: dict[tuple[str, str], str], nav: str) -> None:
    vp_title, vp_size = VIEWPORTS[vp]
    toc, body = [], []
    for cat in cats:
        names = [n for n in order[cat] if vp in shots[cat][n]]
        if not names:
            continue
        title = rc.TITLES.get(cat, cat)
        toc.append(f'<li><a href="#area-{cat}"><b>{html.escape(title)}</b></a> ({len(names)}): ' + ", ".join(f'<a href="#{cat}/{n}">{n}</a>' for n in names) + "</li>")
        body.append(f'<h2 id="area-{cat}">{html.escape(title)} <span class=small>— <code>{cat}</code></span></h2>')
        if rc.LOOK.get(cat):
            body.append("<details><summary>Spunti dall'analisi tecnica (facoltativi)</summary><ul>" + "".join(f"<li>{md_inline(x)}</li>" for x in rc.LOOK[cat]) + "</ul></details>")
        body += [card(cat, n, vp, shots, pkg, where) for n in names]
    intro = (
        f"<h1>Schermate {vp_title.lower()} <span class=small>({vp_size})</span></h1>"
        f"<p class=small>Ogni card: tema chiaro a sinistra, scuro a destra. Clic su un'immagine per vederla a piena grandezza. "
        f"Nelle note citare il codice giallo della card, per esempio <code>dashboard/kpi-top</code>.</p>"
        f'<div class=box><b>Aree</b><ul class=toc>{"".join(toc)}</ul></div>'
    )
    (pkg / f"{vp}.html").write_text(page(f"LibreFolio — schermate {vp}", nav, intro + "".join(body)))


def write_guide(pkg: Path, meta: dict, shots: Shots, date: str, nav: str) -> None:
    n_shots = sum(len(v) for v in shots.values())
    tw = tailwind_values()
    pal_rows = [f"<tr><th>{html.escape(role)}</th><td>{''.join(swatch(s, kind, tw, False) for s in light)}</td>" f"<td class=dk>{''.join(swatch(s, kind, tw, True) for s in dark)}</td><td class=small>{html.escape(note)}</td></tr>" for role, kind, light, dark, note in rc.ROLES]
    missing_desktop = sorted(f"{c}/{n}" for c in shots for n in shots[c] if "desktop" not in shots[c][n] and n not in rc.MOBILE_ONLY)
    missing_line = f"<li>Schermate desktop mancanti (solo mobile): {', '.join(f'<code>{m}</code>' for m in missing_desktop)}.</li>" if missing_desktop else ""
    guide = f"""
<h1>LibreFolio — Review dei colori</h1>
<p>Grazie per l'aiuto! Qui ci sono tutte le schermate dell'app (<b>{n_shots}</b>), ognuna in tema <b>chiaro</b> e <b>scuro</b>,
per computer e per telefono. Servono a ragionare insieme su colori più coerenti.</p>
<div class=box><h2>Come si usa</h2><ol>
<li>Apri <a href="desktop.html"><b>Schermate desktop</b></a> oppure <a href="mobile.html"><b>Schermate mobile</b></a>.
In alto c'è l'indice per area (Dashboard, Asset, Transazioni…).</li>
<li>Ogni card mostra una schermata: <b>chiaro a sinistra, scuro a destra</b>. Clic sull'immagine per la piena grandezza.
Sotto il nome trovi dove si trova nell'app.</li>
<li>Scrivi le note in un file di testo (puoi usare <code>note_designer.txt</code>, incluso), citando il <b>nome della card</b> (in giallo), il tema e il dispositivo. Esempio:<br>
<code>dashboard/kpi-top · scuro · desktop: il verde delle variazioni positive è troppo acceso rispetto al resto</code></li>
<li>Le note generali (palette, ruoli dei colori, idee) vanno in fondo allo stesso file.</li></ol></div>
<div class=box><h2>Da sapere</h2><ul>
<li>Commit <code>{html.escape(str(meta.get("commit", "?"))[:10])}</code>, schermate catturate il <b>{date}</b> con dati di esempio (non reali); alcune usano dati simulati.</li>
<li>Animazioni ferme e nessun passaggio del mouse: hover, focus e menu aperti si valutano dal vivo con lo sviluppatore.</li>
<li>Desktop 1280×720 (alcune schermate sono più alte per mostrare un blocco intero); mobile 430×932.</li>
{missing_line}
<li><b>Fedeltà dei colori:</b> gli screenshot sono in sRGB. Molti colori dell'interfaccia sono definiti in OKLCH, più saturi
di sRGB: su un Mac recente l'app dal vivo può apparire un po' più satura delle immagini. Per confronti fedeli: zoom 100%,
luminosità costante, schermo calibrato se possibile.</li></ul></div>
<div class=box><h2>Su cosa ci serve il tuo parere (primo giro)</h2><ol>{"".join(f"<li>{a}</li>" for a in rc.ASKS)}</ol></div>
<div class=box><h2>Cosa sappiamo già</h2>
<p class=small>Dall'analisi tecnica del codice; non serve segnalarli di nuovo, ma i tuoi commenti su come risolverli sono preziosi.</p>
<ul>{"".join(f"<li>{k}</li>" for k in rc.KNOWN)}</ul></div>
<div class=box><h2>Palette attuale (valori più usati oggi)</h2>
<p class=small>Indicativa: per ogni ruolo i colori effettivamente più usati. I nomi come <code>gray-400</code> sono classi Tailwind
(valore OKLCH reale della build); gli <code>#hex</code> sono scritti a mano. Colonna scura su sfondo <code>#0f172a</code>; «Aa» = colore del testo.</p>
<table class=pal><tr><th>Ruolo</th><th>Chiaro</th><th>Scuro</th><th>Nota</th></tr>{"".join(pal_rows)}</table></div>
"""
    (pkg / "APRI_QUI.html").write_text(page("LibreFolio — Review colori", nav, guide))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the offline designer package from a gallery snapshot")
    ap.add_argument("snapshot")
    ap.add_argument("--lang", default="it")
    ap.add_argument("--name", default="LibreFolio_review_colori_v1.2")
    ap.add_argument("--work-dir", help="output root outside the repository")
    args = ap.parse_args()
    snap = Path(args.snapshot).expanduser().resolve()
    meta = json.loads((snap / "meta.json").read_text())
    out_root = work_dir(args.work_dir) / "package"
    pkg = out_root / args.name
    if pkg.exists():
        shutil.rmtree(pkg)
    (pkg / "img").mkdir(parents=True)

    shots = collect_shots(snap, pkg, args.lang)
    where, order = navigation(shots)
    cats = [c for c in rc.ORDER if c in shots] + sorted(c for c in shots if c not in rc.ORDER)
    date = meta.get("started", "?")[:10]

    def nav(current: str) -> str:
        items = [("APRI_QUI.html", "Guida"), ("desktop.html", "Schermate desktop"), ("mobile.html", "Schermate mobile")]
        links = " ".join(f'<a href="{h}">{"▸ " if h == current else ""}{t}</a>' for h, t in items)
        return f"<b>LibreFolio — review colori</b> {links}<span class=sp></span><span class=small style='color:#a1a1aa'>catturate il {date}</span>"

    for vp in VIEWPORTS:
        write_viewport_page(pkg, vp, cats, shots, order, where, nav(f"{vp}.html"))
    write_guide(pkg, meta, shots, date, nav("APRI_QUI.html"))
    (pkg / "note_designer.txt").write_text(NOTE_TEMPLATE)
    zip_path = Path(shutil.make_archive(str(out_root / args.name), "zip", root_dir=out_root, base_dir=args.name))
    n_png = sum(1 for _ in (pkg / "img").rglob("*.png"))
    print(f"package → {pkg} ({n_png} png, {sum(len(v) for v in shots.values())} shots); zip → {zip_path} ({zip_path.stat().st_size / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
