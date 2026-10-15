# Visual review tools (`scripts/visual_review/`)

Tools for reviewing LibreFolio's look with a designer and for checking that a refactor did not change it:

- capture the documentation gallery (~177 screens × desktop/mobile × 4 languages × light/dark) as an
  immutable **snapshot**;
- **pixel-diff** two snapshots, ranking the changes that are likely real first;
- build an offline **designer package** (one double click, no install);
- start a **live test server** for the designer;
- count every colour expression of the frontend (**colour inventory**).

First used for the colour review of v1.2 (October 2026). All outputs are large and go **outside the
repository**, to `--work-dir`, else `$LF_VISUAL_REVIEW_DIR`, else `LibreFolio_subRepo/LibreFolio_visual_review` next to the
main checkout when `LibreFolio_subRepo` exists (the developer's layout; worktrees resolve the main checkout through git),
else `~/LibreFolio_visual_review`.

| File | What it does |
|---|---|
| `gallery_snapshot.sh` | Runs `./dev.py mkdocs gallery` in a lane and freezes the PNGs it wrote into `<work>/snapshots/<label>/` with `meta.json` and the log |
| `gallery_tool.py` | `diff` (pixel compare), `stability` (classify shots from a noise run), `browse` (HTML pages, light and dark side by side) |
| `live_price_check.py` | Checks, in the lane's backend log, that no live-price request reached the backend while a snapshot was captured (exit 1: capture again) |
| `build_designer_package.py` | Offline package for the designer: `APRI_QUI.html`, `desktop.html`, `mobile.html`, `note_designer.txt`, images, zip |
| `build_review_notes.py` | The team's Markdown working notes: navigation per shot, role vocabulary, decisions |
| `designer_live.sh` | Test server with the gallery's data on its own lane (default port 6160), reachable from the local network |
| `color_inventory.py` | Quantitative colour inventory of `frontend/src` (Markdown summary and CSVs) |
| `review_content.py` | **Review-specific** texts: area titles, hints, palette table, questions, note templates. Update it for each review |
| `data/navigation_map.it.md` | How to reach every gallery shot in the app (route, steps, user, data). Update it when the gallery changes |
| `navmap.py`, `_common.py` | Helpers |

## Prerequisites

- Run everything from the repository root. Python tools use the project venv, which already has Pillow and numpy:
  `pipenv run python -m scripts.visual_review.<tool> …`.
- **Linked worktrees** must reuse the main venv. Export `PIPENV_CUSTOM_VENV_NAME=<main venv name>` before
  `pipenv run` (see `.github/copilot-instructions.md`); otherwise pipenv creates an empty venv. The shell
  scripts refuse to start without it.
- The gallery needs `frontend/node_modules`. In a fresh worktree, run the approved `npm ci` first.

## Lanes and rules

- Each run uses one **lane**: one port and one data directory, never shared by two active runs.
  - Coordinator default: `6150` + `/tmp/librefolio-r2-main`.
  - Children: `6151+` + `/tmp/librefolio-r2-<letter>`.
  - Designer live server: `6160` + `/tmp/librefolio-color-review`.
- A busy port stops the scripts. Never use `--force`.
- **Compare captures of the same day only.** The test database is generated from `date.today()`, so
  snapshots of different days differ by construction (axes, ranges, values). `diff` warns when the dates differ.
- **The app version is pinned.** The sidebar, the changelog and the About tab show the build's version, which is
  `git describe` by default and so differs between any two commits. `gallery_snapshot.sh` exports
  `LF_APP_VERSION` (default `v0.0.0-review`) and rebuilds the frontend in debug mode first when the checkout's
  build does not carry it (`build.log` in the snapshot). `meta.json` records it as `app_version`.
- A full gallery takes about **31–34 min** at 10 workers and about **500 MB** (four languages).
  A `diff` of two full snapshots takes about 3.5 min. The designer package weighs about 120 MB per language.

## Workflow

### 1. Noise baseline (once per comparison day)
Two captures of the same commit show what changes on its own:
```bash
scripts/visual_review/gallery_snapshot.sh base-r1
scripts/visual_review/gallery_snapshot.sh base-r2
W=/Users/ea_enel/Documents/00_My/LibreFolio_subRepo/LibreFolio_visual_review   # the default work dir on the developer's machine
pipenv run python -m scripts.visual_review.live_price_check $W/snapshots/base-r1 $W/snapshots/base-r2   # must exit 0
pipenv run python -m scripts.visual_review.gallery_tool diff $W/snapshots/base-r1 $W/snapshots/base-r2 \
    --out $W/diffs/noise --emit-masks
pipenv run python -m scripts.visual_review.gallery_tool stability $W/diffs/noise   # stability.md / .json
```
`live_price_check.py` reads the lane's backend log (`<data dir>/logs/librefolio.log`, found through each
snapshot's `meta.json`) for the time of each capture. If a live-price request reached the backend, it asked a
provider and rewrote today's candle in the shared test database, so every later shot of that asset changed: the
script exits `1` and the capture must be taken again. That happened once on 14/10/2026, before the gallery left
each page ahead of dropping its offline guard. Exit `2` means the log cannot vouch for the capture: wrong log, or a
log without DEBUG lines.

Every shot gets a class:

| Class | Meaning |
|---|---|
| `stable` | Identical in every variant |
| `low` | At most 0.1 % of pixels changed: antialiasing |
| `medium` | At most 1 % changed: small dynamic areas |
| `unstable` | Over 1 %, or a different image height |

A diff on an `unstable` shot is weak evidence: compare it by eye.

### 2. Check a change
Capture the reference and the candidate on the **same day**. They may run in parallel on two lanes:
```bash
scripts/visual_review/gallery_snapshot.sh ref                                   # target checkout, lane 6150
scripts/visual_review/gallery_snapshot.sh cand --checkout <worktree> --port 6151 --data-dir /tmp/librefolio-r2-x
pipenv run python -m scripts.visual_review.live_price_check $W/snapshots/ref $W/snapshots/cand   # must exit 0
pipenv run python -m scripts.visual_review.gallery_tool diff $W/snapshots/ref $W/snapshots/cand --out $W/diffs/ref__vs__cand \
    --ignore-masks $W/diffs/noise/masks --stability $W/diffs/noise/stability.json
open $W/diffs/ref__vs__cand/index.html       # A | B | changed pixels in red; likely-real changes first
```
For a filtered capture (`-- -f "Dashboard"`), add `--common-only` to the diff.
A refactor that should not change the look must give `identical`, plus noise on the `unstable` shots.

### 3. Designer package
```bash
pipenv run python -m scripts.visual_review.gallery_tool browse $W/snapshots/ref --langs it,en   # optional HTML pages for the team
pipenv run python -m scripts.visual_review.build_designer_package $W/snapshots/ref --lang it --name LibreFolio_review_colori_vX
```
Send `$W/package/<name>.zip`. The designer unzips it and double-clicks `APRI_QUI.html`. Each screen shows its code
(`dashboard/kpi-top`), to quote in her notes.

Before a new review, update `review_content.py` (hints, palette table, questions) and `data/navigation_map.it.md`.
Gallery shots missing from the map are still published, with «?» as navigation.

Build the frontend first (`./dev.py front build`): the palette table reads the real Tailwind OKLCH values from `frontend/build`.

### 4. Live server for the designer
```bash
scripts/visual_review/designer_live.sh            # --refresh to re-copy the latest gallery data
```
- Address: `http://localhost:6160`, or `http://<this-machine>:6160` from the same network.
- Login: `e2e_test_admin` / `E2eAdminPass123!`.
- The test server always serves the frontend debug build, so debug-only pages (e.g. the Designer Lab) are there too.

### 5. Colour inventory and team notes
```bash
pipenv run python -m scripts.visual_review.color_inventory            # → $W/inventory/00_inventory_summary.md + CSVs
pipenv run python -m scripts.visual_review.build_review_notes $W/snapshots/ref   # → $W/notes/NOTE_DESIGNER.md
```

## Known gallery behaviour (14/10/2026, commit `27228466c`)

- **Failures under a full run.** Two full runs at 10 workers each had 4–5 failed tests, all on desktop, and a different set each time:
  - login stuck on «auth-loading» in the first burst of tests;
  - three transaction modals;
  - `Dashboard Risk › what-if crisis replay`.

  The failed tests passed again in isolation (`-- --no-populate --desktop-only -w 5 -f "<names>"`).
- **The what-if replay preset** failed on desktop in 2 of 3 runs. The crisis menu opens with the option, but
  `chooseReplayPreset` (`frontend/e2e/fixtures/galleryRiskDashboard.ts`) never stops on it.
- **27 shots of 177 are `unstable`.** Two causes seen so far:
  - the animated login background, not fully frozen (`auth/*`);
  - a scroll offset of a few pixels that shifts a whole panel (`*/fifo-lots-panel`, `*/fifo-lots-wac-chart`).

  Making the gallery deterministic (frozen background, no smooth scrolling, stable scroll position) would turn
  most of them into `stable`.
- **Screenshots are sRGB.** Tailwind v4 colours are OKLCH and often outside sRGB, so the live app on a wide-gamut
  display (recent Macs) looks more saturated than the PNGs.
