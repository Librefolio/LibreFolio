#!/usr/bin/env python3
"""Pixel-compare gallery snapshots and browse them (LibreFolio visual review).

Run from the repository root with the project venv (Pillow + numpy):
    pipenv run python -m scripts.visual_review.gallery_tool <subcommand> ...

Subcommands
-----------
diff    Compare two snapshots (A = reference, B = candidate) pixel by pixel.
        ... diff <work>/snapshots/A <work>/snapshots/B --out <work>/diffs/A__vs__B [--tol 0]
            [--emit-masks]                       # write per-image change masks (use on a noise run)
            [--ignore-masks <work>/diffs/X/masks] # ignore pixels known to be volatile
            [--common-only]                      # compare only shots present in both (filtered runs)
        Writes report.md, summary.json, index.html (A | B | changed pixels in red) and composites/.

browse  Build HTML pages for one snapshot: every shot, light and dark side by side.
        ... browse <work>/snapshots/A [--langs it,en] [--viewports desktop,mobile]
        Writes <snapshot>/index.html (+ one page per viewport/language, next to png/).

stability  Classify every shot (stable / low / medium / unstable) from a NOISE diff — a diff between two
        captures of the same commit on the same day — and write stability.json / stability.md into it.
        ... stability <work>/diffs/noise__r1__vs__r2
        Then pass it to later diffs: diff A B --out … --ignore-masks <noise>/masks --stability <noise>/stability.json

sheet   Rank a diff's shots by VISIBLE change and write a contact sheet into the diff. At tolerance 0 a colour
        migration «changes» nearly every image by a few levels; `sheet` counts the pixels whose largest channel change
        exceeds 12 levels (and 4, and 32), with the diff's noise masks applied, and writes visible.json and
        contact_sheet.<lang>.html: one row per shot, A and B side by side, light and dark, desktop and mobile, the most
        visible change first, with the new, gone and resized images listed on top.
        ... sheet <work>/diffs/A__vs__B [--lang it] [--a <snapshot A>] [--b <snapshot B>] [--recompute]
        The measures cover every language and are kept in visible.json, so another --lang only rewrites the page.

Snapshot layout (written by gallery_snapshot.sh):
    <snapshot>/png/<viewport>/<lang>/<theme>/<category>/<name>.png, <snapshot>/meta.json
Snapshots captured on different days differ by construction (the test data follows date.today()).
"""

from __future__ import annotations

import argparse
import html
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

THEMES = ("light", "dark")
# Lower rank = reviewed first in a diff: changes on shots that never move on their own are the likely real ones.
NOISE_RANK = {"stable": 0, "unknown": 0, "n/a": 0, "low": 1, "medium": 2, "unstable": 3}


# ----------------------------------------------------------------------------- helpers
def list_pngs(snapshot: Path) -> dict[str, Path]:
    root = snapshot / "png"
    return {str(p.relative_to(root)): p for p in sorted(root.rglob("*.png"))}


def parse_rel(rel: str) -> dict[str, str]:
    parts = rel[:-4].split("/")
    if len(parts) != 5:
        return {"viewport": "?", "lang": "?", "theme": "?", "category": "/".join(parts[:-1]), "name": parts[-1]}
    v, lang, theme, cat, name = parts
    return {"viewport": v, "lang": lang, "theme": theme, "category": cat, "name": name}


def load_meta(snapshot: Path) -> dict:
    f = snapshot / "meta.json"
    return json.loads(f.read_text()) if f.exists() else {"label": snapshot.name}


def load_rgb(p: Path) -> np.ndarray:
    with Image.open(p) as im:
        return np.asarray(im.convert("RGB"), dtype=np.int16)


def dilate(mask: np.ndarray, r: int) -> np.ndarray:
    if r <= 0 or not mask.any():
        return mask
    out = mask.copy()
    h, w = mask.shape
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy == 0 and dx == 0:
                continue
            ys, yd = (slice(dy, h), slice(0, h - dy)) if dy >= 0 else (slice(0, h + dy), slice(-dy, h))
            xs, xd = (slice(dx, w), slice(0, w - dx)) if dx >= 0 else (slice(0, w + dx), slice(-dx, w))
            out[yd, xd] |= mask[ys, xs]
    return out


def rel_link(target: Path, start_dir: Path) -> str:
    return html.escape(os.path.relpath(target, start_dir))


# ----------------------------------------------------------------------------- diff
def make_composite(a: np.ndarray, b: np.ndarray, changed: np.ndarray, dest: Path, max_w: int = 2400) -> None:
    hi = (b.mean(axis=2, keepdims=True) * 0.35).repeat(3, axis=2).astype(np.int16)
    vis = dilate(changed, 2)
    hi[vis] = (255, 0, 64)
    sep = np.full((a.shape[0], 8, 3), 255, dtype=np.int16)
    comp = np.concatenate([a, sep, b, sep, hi], axis=1).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(comp)
    if img.width > max_w:
        img = img.resize((max_w, round(img.height * max_w / img.width)), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=82)


def apply_ignore_mask(raw: np.ndarray, ignore_dir: Path | None, rel: str) -> tuple[np.ndarray, int]:
    """Drop the pixels a noise mask marks as volatile; return (changed, ignored count)."""
    if ignore_dir is None or not (ignore_dir / rel).exists():
        return raw, 0
    with Image.open(ignore_dir / rel) as m:
        mask = np.asarray(m.convert("L")) > 0
    if mask.shape != raw.shape:
        return raw, 0
    return raw & ~mask, int((raw & mask).sum())


def compare_pair(rel: str, a_path: Path, b_path: Path, args: argparse.Namespace, ignore_dir: Path | None, out: Path) -> dict:
    a, b = load_rgb(a_path), load_rgb(b_path)
    if a.shape != b.shape:
        return {"status": "size_changed", "size_a": list(a.shape[:2]), "size_b": list(b.shape[:2])}
    delta = np.abs(a - b).max(axis=2)
    raw = delta > args.tol
    changed, ignored = apply_ignore_mask(raw, ignore_dir, rel)
    n = int(changed.sum())
    info = {"changed_px": n, "ignored_px": ignored, "total_px": int(changed.size), "pct": round(100 * n / changed.size, 4), "max_delta": int(delta.max())}
    if n:
        ys, xs = np.nonzero(changed)
        comp = out / "composites" / (rel[:-4] + ".jpg")
        make_composite(a, b, changed, comp)
        info.update(bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], status="changed", composite=str(comp.relative_to(out)))
    else:
        info["status"] = "identical"
    if args.emit_masks and raw.any():
        mp = out / "masks" / rel
        mp.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray((dilate(raw, args.mask_dilate) * 255).astype(np.uint8)).save(mp, optimize=True)
    return info


def diff_report_md(results: list[dict], changed: list[dict], meta_a: dict, meta_b: dict, args: argparse.Namespace, ignore_dir: Path | None, ranked: bool) -> str:
    status = Counter(r["status"] for r in results)
    by_cat: dict[str, Counter] = defaultdict(Counter)
    for r in results:
        by_cat[r["category"]][r["status"]] += 1
    L = [f"# Gallery diff — `{meta_a.get('label')}` → `{meta_b.get('label')}`", ""]
    for k, m in (("A (reference)", meta_a), ("B (candidate)", meta_b)):
        L.append(f"- **{k}**: commit `{str(m.get('commit', '?'))[:10]}`, started {m.get('started', '?')}, exit {m.get('exit_code', '?')}, png {m.get('png_captured', '?')}, stale {m.get('png_stale_not_regenerated', '?')}")
    L += [f"- Tolerance per channel: {args.tol}; ignore masks: {ignore_dir or 'none'}", "", "## Totals", "", "| Status | Images |", "|---|---:|"]
    L += [f"| {k} | {v} |" for k, v in sorted(status.items())]
    if meta_a.get("started", "")[:10] != meta_b.get("started", "")[:10]:
        L += ["", "> ⚠️ A and B were captured on different days: the test data is generated from `date.today()`, so date-driven content (axes, ranges, values) differs by construction. Re-capture both on the same day."]
    L += ["", "## By category", "", "| Category | identical | changed | size_changed | missing_in_A | missing_in_B |", "|---|---:|---:|---:|---:|---:|"]
    L += [f"| {cat} | {c['identical']} | {c['changed']} | {c['size_changed']} | {c['missing_in_A']} | {c['missing_in_B']} |" for cat, c in sorted(by_cat.items())]
    if ranked:
        likely = sum(1 for r in changed if r["noise"] in ("stable", "unknown"))
        L += ["", f"> **{likely} changed images belong to shots that were stable (or unseen) in the noise run** — review them first: they are the likely real changes. Shots classed `unstable` change on their own between identical runs; compare those by eye."]
    L += ["", f"## Changed images ({len(changed)}) — likely-real first (noise class), then by % of changed pixels", "", "| Image | noise | % px | px | max Δ | bbox (x0,y0,x1,y1) |", "|---|---|---:|---:|---:|---|"]
    L += [f"| [{r['rel']}]({r['composite']}) | {r['noise']} | {r['pct']} | {r['changed_px']} | {r['max_delta']} | {r.get('bbox')} |" for r in changed]
    for st in ("size_changed", "missing_in_A", "missing_in_B"):
        rows = [r for r in results if r["status"] == st]
        if rows:
            L += ["", f"## {st} ({len(rows)})", ""] + [f"- {r['rel']} {r.get('size_a', '')} {r.get('size_b', '')}" for r in rows]
    return "\n".join(L) + "\n"


def diff_index_html(changed: list[dict], status: Counter, meta_a: dict, meta_b: dict, a_files: dict[str, Path], b_files: dict[str, Path], out: Path) -> str:
    cards = [
        f'<div class="card" data-k="{html.escape(r["rel"])}"><h3>{html.escape(r["rel"])} — {r["pct"]}% '
        f'({r["changed_px"]} px, maxΔ {r["max_delta"]}, noise: {html.escape(r["noise"])})</h3>'
        f'<a href="{html.escape(r["composite"])}"><img loading="lazy" src="{html.escape(r["composite"])}"></a>'
        f'<p><a href="{rel_link(a_files[r["rel"]], out)}">A full</a> · <a href="{rel_link(b_files[r["rel"]], out)}">B full</a></p></div>'
        for r in changed
    ]
    return f"""<!doctype html><meta charset="utf-8"><title>Gallery diff {html.escape(meta_a.get('label', ''))} → {html.escape(meta_b.get('label', ''))}</title>
<style>body{{font:14px system-ui;margin:16px;background:#f4f4f5}}.card{{background:#fff;margin:12px 0;padding:8px;border-radius:8px}}
img{{max-width:100%}}h3{{font-size:13px;margin:4px 0}}input{{width:420px;padding:6px}}</style>
<h1>Gallery diff: {html.escape(meta_a.get('label', ''))} → {html.escape(meta_b.get('label', ''))}</h1>
<p>Each row: <b>A (reference)</b> | <b>B (candidate)</b> | changed pixels in red. Totals: {html.escape(json.dumps(dict(status)))}</p>
<input placeholder="filter (e.g. dark/dashboard)" oninput="for(const c of document.querySelectorAll('.card'))c.style.display=c.dataset.k.includes(this.value)?'':'none'">
{''.join(cards) or '<p>No changed images.</p>'}"""


def cmd_diff(args: argparse.Namespace) -> int:
    a_dir, b_dir, out = Path(args.a).resolve(), Path(args.b).resolve(), Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    a_files, b_files = list_pngs(a_dir), list_pngs(b_dir)
    ignore_dir = Path(args.ignore_masks).resolve() if args.ignore_masks else None
    if args.common_only:
        common = set(a_files) & set(b_files)
        a_files = {k: v for k, v in a_files.items() if k in common}
        b_files = {k: v for k, v in b_files.items() if k in common}
    results = []
    for rel in sorted(set(a_files) | set(b_files)):
        info = {"rel": rel, **parse_rel(rel)}
        if rel not in b_files:
            info["status"] = "missing_in_B"
        elif rel not in a_files:
            info["status"] = "missing_in_A"
        else:
            info.update(compare_pair(rel, a_files[rel], b_files[rel], args, ignore_dir, out))
        results.append(info)

    stability = json.loads(Path(args.stability).read_text()) if args.stability else {}
    for r in results:
        r["noise"] = stability.get(f"{r['category']}/{r['name']}", {}).get("class", "unknown") if stability else "n/a"
    status = Counter(r["status"] for r in results)
    meta_a, meta_b = load_meta(a_dir), load_meta(b_dir)
    summary = {"A": meta_a, "B": meta_b, "a_dir": str(a_dir), "b_dir": str(b_dir), "tol": args.tol, "ignore_masks": str(ignore_dir) if ignore_dir else None, "counts": dict(status), "results": results}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    changed = sorted((r for r in results if r["status"] == "changed"), key=lambda r: (NOISE_RANK.get(r["noise"], 0), -r["pct"]))
    (out / "report.md").write_text(diff_report_md(results, changed, meta_a, meta_b, args, ignore_dir, bool(stability)))
    (out / "index.html").write_text(diff_index_html(changed, status, meta_a, meta_b, a_files, b_files, out))
    print(json.dumps(dict(status)), "→", out / "report.md")
    return 0


# ----------------------------------------------------------------------------- browse
def browse_page(files: dict[str, Path], meta: dict, out: Path, vp: str, lang: str) -> int:
    """Write <vp>-<lang>.html (light and dark side by side for every shot); return the number of shots."""
    shots: dict[str, dict[str, Path]] = defaultdict(dict)
    for rel, p in files.items():
        info = parse_rel(rel)
        if info["viewport"] == vp and info["lang"] == lang:
            shots[f"{info['category']}/{info['name']}"][info["theme"]] = p
    if not shots:
        return 0
    by_cat: dict[str, list[str]] = defaultdict(list)
    for key in sorted(shots):
        by_cat[key.split("/")[0]].append(key)
    toc = "".join(f"<li><b>{html.escape(cat)}</b> ({len(keys)}): " + ", ".join(f'<a href="#{html.escape(k)}">{html.escape(k.split("/", 1)[1])}</a>' for k in keys) + "</li>" for cat, keys in sorted(by_cat.items()))
    body = []
    for cat, keys in sorted(by_cat.items()):
        body.append(f'<h2 id="cat-{html.escape(cat)}">{html.escape(cat)}</h2>')
        for k in keys:
            cells = "".join(figure(shots[k].get(th), th, out) for th in THEMES)
            body.append(f'<section id="{html.escape(k)}"><h3>{html.escape(k)} <a href="#{html.escape(k)}">#</a></h3><div class="row {vp}">{cells}</div></section>')
    name = f"{vp}-{lang}.html"
    (out / name).write_text(f"""<!doctype html><meta charset="utf-8"><title>LibreFolio gallery — {vp} {lang}</title>
<style>body{{font:14px system-ui;margin:16px;background:#e4e4e7}}section{{background:#fff;border-radius:8px;padding:8px;margin:10px 0;scroll-margin-top:8px}}
.row{{display:flex;gap:10px;align-items:flex-start}}.row figure{{margin:0;flex:1;min-width:0}}.row.mobile figure{{flex:0 1 auto;max-width:48%}}
img{{max-width:100%;height:auto;border:1px solid #d4d4d8;display:block}}
figcaption{{font-weight:600;font-size:12px}}h3{{font-size:14px;margin:2px 0 6px}}ul{{line-height:1.6}}</style>
<h1>LibreFolio gallery — {vp} / {lang}</h1>
<p><a href="index.html">↑ index</a> · Snapshot <code>{html.escape(meta.get('label', ''))}</code>, commit <code>{html.escape(str(meta.get('commit', '?'))[:10])}</code>,
captured {html.escape(str(meta.get('started', '?')))}. Click an image for full size. Anchors: <code>{name}#category/name</code>.</p>
<ul>{toc}</ul>{''.join(body)}""")
    return len(shots)


def figure(p: Path | None, theme: str, out: Path) -> str:
    if p is None:
        return f"<figure><figcaption>{theme}: —</figcaption></figure>"
    with Image.open(p) as im:
        w, h = im.size
    src = rel_link(p, out)
    return f'<figure><figcaption>{theme}</figcaption><a href="{src}"><img loading="lazy" width="{w}" height="{h}" src="{src}"></a></figure>'


def cmd_browse(args: argparse.Namespace) -> int:
    """Pages live in the snapshot root (next to png/) so every image path stays a descendant path:
    some local previewers refuse ``../`` sub-resources. Each <img> declares its size, so lazy
    loading never shifts the layout and ``#category/name`` anchors land on the right shot."""
    snap = Path(args.snapshot).resolve()
    files = list_pngs(snap)
    meta = load_meta(snap)
    index_links = []
    for vp in (x for x in args.viewports.split(",") if x):
        for lang in (x for x in args.langs.split(",") if x):
            n = browse_page(files, meta, snap, vp, lang)
            if n:
                index_links.append(f'<li><a href="{vp}-{lang}.html">{vp} / {lang}</a> — {n} shots</li>')
    (snap / "index.html").write_text(f"""<!doctype html><meta charset="utf-8"><title>LibreFolio gallery — {html.escape(meta.get('label', ''))}</title>
<style>body{{font:15px system-ui;margin:24px}}</style><h1>LibreFolio gallery — {html.escape(meta.get('label', ''))}</h1>
<p>Commit <code>{html.escape(str(meta.get('commit', '?')))}</code>, captured {html.escape(str(meta.get('started', '?')))}.</p>
<p>Every page shows each screen in light and dark side by side.</p>
<ul>{''.join(index_links)}</ul>""")
    print("browse pages →", snap / "index.html")
    return 0


# ----------------------------------------------------------------------------- stability
def cmd_stability(args: argparse.Namespace) -> int:
    """Classify every shot from a noise diff (two runs of the same commit, same day).

    stable   — identical in every variant (viewport × language × theme) present in both runs;
    low      — some variant changed, never more than 0.1 % of its pixels (antialiasing, sub-pixel timing);
    medium   — up to 1 %: small dynamic areas (timestamps, a spinner, a counter);
    unstable — over 1 %, or a different image height: the shot changes on its own; a diff on it is weak evidence.
    """
    noise = Path(args.noise_diff).resolve()
    summary = json.loads((noise / "summary.json").read_text())
    per: dict[str, dict] = defaultdict(lambda: {"variants": 0, "changed": 0, "size_changed": 0, "pcts": [], "max_delta": 0})
    for r in summary["results"]:
        if r["status"] in ("missing_in_A", "missing_in_B"):
            continue
        s = per[f"{r['category']}/{r['name']}"]
        s["variants"] += 1
        if r["status"] == "size_changed":
            s["size_changed"] += 1
        elif r["status"] == "changed":
            s["changed"] += 1
            s["pcts"].append(r["pct"])
            s["max_delta"] = max(s["max_delta"], r["max_delta"])
    out: dict[str, dict] = {}
    for shot, s in sorted(per.items()):
        mx = max(s["pcts"], default=0.0)
        cls = "unstable" if s["size_changed"] or mx >= 1 else "medium" if mx >= 0.1 else "low" if s["changed"] else "stable"
        out[shot] = {"class": cls, "variants": s["variants"], "changed": s["changed"], "size_changed": s["size_changed"], "max_pct": round(mx, 4), "median_pct": round(sorted(s["pcts"])[len(s["pcts"]) // 2], 4) if s["pcts"] else 0.0, "max_delta": s["max_delta"]}
    (noise / "stability.json").write_text(json.dumps(out, indent=1))
    counts = Counter(v["class"] for v in out.values())
    L = [f"# Shot stability — noise run `{summary['A'].get('label')}` vs `{summary['B'].get('label')}`", "", "Two captures of the same commit on the same day. A shot that changes here changes on its own: a diff on it is weak evidence.", "", "| Class | Shots |", "|---|---:|"] + [
        f"| {k} | {counts.get(k, 0)} |" for k in ("stable", "low", "medium", "unstable")
    ]
    L += ["", "| Shot | class | changed / variants | size changed | median % | max % | max Δ |", "|---|---|---:|---:|---:|---:|---:|"]
    for shot, v in sorted(out.items(), key=lambda kv: (-NOISE_RANK[kv[1]["class"]], -kv[1]["max_pct"], kv[0])):
        L.append(f"| `{shot}` | {v['class']} | {v['changed']}/{v['variants']} | {v['size_changed']} | {v['median_pct']} | {v['max_pct']} | {v['max_delta']} |")
    (noise / "stability.md").write_text("\n".join(L) + "\n")
    print(dict(counts), "→", noise / "stability.md")
    return 0


# ----------------------------------------------------------------------------- sheet
# The thresholds `sheet` measures, in levels of the largest channel change, and the one it ranks by: a change of a few
# levels is invisible on screen (colour-role rounding), one of over 12 starts to show, one of over 32 is plain.
VISIBLE_THRESHOLDS = (4, 12, 32)
SHEET_THRESHOLD = 12
VIEWPORTS = ("desktop", "mobile")
STRUCTURAL = ("size_changed", "missing_in_A", "missing_in_B")


def visible_metrics(a: np.ndarray, b: np.ndarray, ignore: np.ndarray | None) -> dict:
    """The share (%) of pixels whose largest channel change exceeds each threshold; for two heights, on the area both share, top-aligned."""
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    delta = np.abs(a[:h, :w] - b[:h, :w]).max(axis=2)
    if ignore is not None and ignore.shape == delta.shape:
        delta[ignore] = 0
    metrics: dict = {f"vis{t}": round(100 * float((delta > t).sum()) / delta.size, 3) for t in VISIBLE_THRESHOLDS}
    metrics["max_delta"] = int(delta.max())
    return metrics


def load_ignore_mask(ignore_dir: Path | None, rel: str) -> np.ndarray | None:
    if ignore_dir is None or not (ignore_dir / rel).exists():
        return None
    with Image.open(ignore_dir / rel) as m:
        return np.asarray(m.convert("L")) > 0


def sheet_snapshots(diff: Path, summary: dict, args: argparse.Namespace) -> tuple[Path, Path]:
    """The diff's two snapshots: as given, else as the diff recorded them, else <work>/snapshots/<label> (diffs written before the record)."""
    snapshots = diff.parent.parent / "snapshots"
    a = args.a or summary.get("a_dir") or str(snapshots / summary["A"].get("label", "?"))
    b = args.b or summary.get("b_dir") or str(snapshots / summary["B"].get("label", "?"))
    found = Path(a).resolve(), Path(b).resolve()
    for snapshot in found:
        if not (snapshot / "png").is_dir():
            raise SystemExit(f"{snapshot} is not a snapshot (no png/): pass it with --a / --b")
    return found


def shot_table(per_image: dict[str, dict]) -> dict[str, dict]:
    """Every shot's visible change over its variants (every language, theme and viewport): the median and the largest."""
    shots: dict[str, list[dict]] = defaultdict(list)
    for rel, rec in per_image.items():
        p = parse_rel(rel)
        shots[f"{p['category']}/{p['name']}"].append(rec)
    per_shot = {}
    for shot, recs in sorted(shots.items()):
        vis = [rec[f"vis{SHEET_THRESHOLD}"] for rec in recs]
        per_shot[shot] = {"noise": recs[0]["noise"], "variants": len(recs), "statuses": dict(Counter(rec["status"] for rec in recs)), "median": round(statistics.median(vis), 3), "max": max(vis)}
    return per_shot


def measure_images(summary: dict, a_dir: Path, b_dir: Path) -> dict[str, dict]:
    """Every image's visible change, the diff's ignore masks applied: the slow part, a few minutes for a full gallery."""
    ignore_dir = Path(summary["ignore_masks"]) if summary.get("ignore_masks") else None
    per_image: dict[str, dict] = {}
    for r in summary["results"]:
        rel, status = r["rel"], r["status"]
        rec = {"status": status, "noise": r.get("noise", "n/a"), "pct": r.get("pct", 0.0), "composite": r.get("composite")}
        if status in ("changed", "size_changed"):
            a, b = load_rgb(a_dir / "png" / rel), load_rgb(b_dir / "png" / rel)
            rec.update(visible_metrics(a, b, load_ignore_mask(ignore_dir, rel)))
            if status == "size_changed":
                rec["size"] = f"{a.shape[1]}×{a.shape[0]} → {b.shape[1]}×{b.shape[0]}"
        else:
            rec.update({f"vis{t}": 0.0 for t in VISIBLE_THRESHOLDS})
        per_image[rel] = rec
    return per_image


def visible_table(diff: Path, summary: dict, a_dir: Path, b_dir: Path, recompute: bool) -> dict:
    """The images' visible change, measured once and kept in <diff>/visible.json while it matches the diff, and the shots' from them."""
    cache = diff / "visible.json"
    key = {"images": len(summary["results"]), "ignore_masks": summary.get("ignore_masks"), "thresholds": list(VISIBLE_THRESHOLDS)}
    cached = json.loads(cache.read_text()) if cache.exists() and not recompute else {}
    per_image = cached["per_image"] if cached and all(cached.get(k) == v for k, v in key.items()) else measure_images(summary, a_dir, b_dir)
    data = {**key, "ranked_by": SHEET_THRESHOLD, "per_shot": shot_table(per_image), "per_image": per_image}
    cache.write_text(json.dumps(data, indent=1))
    return data


def sheet_html(data: dict, summary: dict, a_dir: Path, b_dir: Path, diff: Path, lang: str) -> str:
    per_shot, per_image, t = data["per_shot"], data["per_image"], SHEET_THRESHOLD
    order = sorted(per_shot, key=lambda s: (-per_shot[s]["median"], s))
    bands = Counter("≥ 10 %" if v["median"] >= 10 else "1–10 %" if v["median"] >= 1 else "0.1–1 %" if v["median"] >= 0.1 else "< 0.1 %" for v in per_shot.values())
    structural = [s for s in order if set(per_shot[s]["statuses"]) & set(STRUCTURAL)]

    def picture(p: Path, label: str) -> str:
        img = f'<img loading="lazy" src="{rel_link(p, diff)}" alt="">' if p.exists() else '<div class="miss">—</div>'
        return f"<figure>{img}<figcaption>{label}</figcaption></figure>"

    rows = []
    for shot in order:
        info, cells = per_shot[shot], []
        for vp in VIEWPORTS:
            for theme in THEMES:
                rel = f"{vp}/{lang}/{theme}/{shot}.png"
                rec = per_image.get(rel)
                if rec is None:
                    cells.append(f'<td class="na">{vp} · {theme}: —</td>')
                    continue
                notes = {"missing_in_A": ["<b>new</b>"], "missing_in_B": ["<b>gone</b>"]}.get(rec["status"], [f"Δ&gt;{t}: {rec[f'vis{t}']:.1f} %", f"Δ&gt;32: {rec['vis32']:.1f} %"])
                if rec.get("size"):
                    notes.append(f"<b>size {html.escape(rec['size'])}</b>")
                if rec.get("composite"):
                    notes.append(f'<a href="{html.escape(rec["composite"])}">diff</a>')
                cells.append(f'<td><div class="cap">{vp} · {theme} · {" · ".join(notes)}</div><div class="pair">{picture(a_dir / "png" / rel, "A")}{picture(b_dir / "png" / rel, "B")}</div></td>')
        statuses = ", ".join(f"{k} {v}" for k, v in sorted(info["statuses"].items()))
        meta = f"Δ&gt;{t} median {info['median']:.1f} % (max {info['max']:.1f} %)<br>noise: {html.escape(str(info['noise']))}<br>{html.escape(statuses)}"
        rows.append(f'<tr><th id="{html.escape(shot)}"><div class="shot">{html.escape(shot)}</div><div class="meta">{meta}</div></th>{"".join(cells)}</tr>')
    meta_a, meta_b = summary["A"], summary["B"]
    who = " → ".join(f"{side} <code>{html.escape(str(m.get('label', '?')))}</code> ({html.escape(str(m.get('commit', '?'))[:9])})" for side, m in (("A", meta_a), ("B", meta_b)))
    band_rows = "".join(f"<tr><td>{band}</td><td>{bands.get(band, 0)}</td></tr>" for band in ("≥ 10 %", "1–10 %", "0.1–1 %", "< 0.1 %"))
    struct_items = "".join(f'<li><a href="#{html.escape(s)}">{html.escape(s)}</a>: {html.escape(", ".join(f"{k} {v}" for k, v in sorted(per_shot[s]["statuses"].items())))}</li>' for s in structural)
    return f"""<!doctype html><meta charset="utf-8"><title>Contact sheet {html.escape(str(meta_a.get('label', 'A')))} → {html.escape(str(meta_b.get('label', 'B')))} ({lang})</title>
<style>
body{{font:13px system-ui,sans-serif;margin:12px;background:#f4f4f2}} table{{border-collapse:collapse}} th,td{{border-bottom:1px solid #ccc;vertical-align:top;padding:6px}}
th{{text-align:left;width:180px;position:sticky;left:0;background:#f4f4f2}} .shot{{font-weight:600;word-break:break-all}} .meta{{font-weight:400;color:#555;margin-top:4px}}
.pair{{display:flex;gap:4px}} figure{{margin:0}} figcaption{{color:#666;font-size:11px}} img{{width:260px;border:1px solid #bbb;display:block}}
.cap{{color:#333;font-size:11px;margin-bottom:3px}} .na,.miss{{color:#999}} .bands td{{padding:2px 10px;border:none}}
</style>
<h1>Contact sheet: {who}, language {html.escape(lang)}</h1>
<p>One row per shot, the most visible change first. «Δ&gt;{t}» is the share of pixels whose largest channel change exceeds {t} levels, with the diff's noise masks
applied (ignore masks: {html.escape(str(summary.get('ignore_masks') or 'none'))}): under about 1 % a change is usually invisible (colour rounding). The ranking uses the
median over every language, theme and viewport; the pictures show «{html.escape(lang)}». «diff» opens the composite A | B | changed pixels.</p>
<table class="bands"><tr><th>Δ&gt;{t} median</th><th>shots</th></tr>{band_rows}</table>
<h2>New, gone or resized ({len(structural)})</h2><ul>{struct_items or "<li>none</li>"}</ul>
<table>{"".join(rows)}</table>
"""


def cmd_sheet(args: argparse.Namespace) -> int:
    diff = Path(args.diff).resolve()
    summary_file = diff / "summary.json"
    if not summary_file.exists():
        raise SystemExit(f"{diff} has no summary.json: run `diff` first")
    summary = json.loads(summary_file.read_text())
    a_dir, b_dir = sheet_snapshots(diff, summary, args)
    data = visible_table(diff, summary, a_dir, b_dir, args.recompute)
    out = diff / f"contact_sheet.{args.lang}.html"
    out.write_text(sheet_html(data, summary, a_dir, b_dir, diff, args.lang))
    print(f"{len(data['per_shot'])} shots, {len(data['per_image'])} images → {out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("diff")
    d.add_argument("a")
    d.add_argument("b")
    d.add_argument("--out", required=True)
    d.add_argument("--tol", type=int, default=0, help="per-channel tolerance (0 = exact)")
    d.add_argument("--emit-masks", action="store_true")
    d.add_argument("--mask-dilate", type=int, default=3)
    d.add_argument("--ignore-masks")
    d.add_argument("--common-only", action="store_true", help="compare only images present in both snapshots (for filtered/partial runs)")
    d.add_argument("--stability", help="stability.json from `stability` on a noise run: ranks likely-real changes first")
    d.set_defaults(fn=cmd_diff)
    s = sub.add_parser("stability", help="classify every shot from a noise diff (two identical runs)")
    s.add_argument("noise_diff", help="output directory of `diff A B` where A and B are identical runs")
    s.set_defaults(fn=cmd_stability)
    b = sub.add_parser("browse")
    b.add_argument("snapshot")
    b.add_argument("--langs", default="en")
    b.add_argument("--viewports", default="desktop,mobile")
    b.set_defaults(fn=cmd_browse)
    c = sub.add_parser("sheet", help="rank a diff's shots by visible change and write a contact sheet")
    c.add_argument("diff", help="output directory of `diff A B`")
    c.add_argument("--lang", default="en", help="language of the shots shown (the ranking covers every language)")
    c.add_argument("--a", help="snapshot A (default: the one the diff recorded, else <work>/snapshots/<A's label>)")
    c.add_argument("--b", help="snapshot B (default: the one the diff recorded, else <work>/snapshots/<B's label>)")
    c.add_argument("--recompute", action="store_true", help="measure again even when visible.json matches the diff")
    c.set_defaults(fn=cmd_sheet)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
