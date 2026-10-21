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
| `gallery_snapshot.sh` | Runs `./dev.py mkdocs gallery` in a lane and freezes the PNGs it wrote into `<work>/snapshots/<label>/` with `meta.json`, the log and `mixed_elements.json` |
| `gallery_tool.py` | `diff` (pixel compare), `stability` (classify shots from a noise run), `sheet` (rank a diff's shots by visible change, contact sheet), `mixed` (the elements that mix role and legacy colour classes, by area), `browse` (HTML pages, light and dark side by side) |
| `live_price_check.py` | Checks, in the lane's backend log, that no live-price request reached the backend while a snapshot was captured (exit 1: capture again) |
| `build_designer_package.py` | Offline package for the designer: `APRI_QUI.html`, `desktop.html`, `mobile.html`, `note_designer.txt`, images, zip |
| `build_designer_round.py` | The package of a later round: today, before and after, the colours left by reason, the open questions, the role palette; every page in HTML and Markdown |
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
- **Compare captures of the same day only: the same local and the same UTC date.**
  - The test database is generated from `date.today()`, the local date. Snapshots of different days differ by
    construction (axes, ranges, values), and `diff` warns when the dates differ.
  - The PAC planner dates its scenario on the earlier of the local and the UTC date (`planner/defaults.ts`,
    `defaultAsOf`, rule N26). Between local midnight and UTC midnight its result shows the day before, with other
    figures and a page 24 px taller. That window is 00:00–02:00 in Rome's summer time and 00:00–01:00 in winter.
  - On 16/10/2026, `g-ref13-r1`/`r2` (00:02–01:31) and `g-ref13-r3` (05:28) differed in every PAC result shot (those
    snapshots were deleted on 19/10). The reference trio of 18/10 was captured from 02:00 on, out of that window.
  - So never capture in that window, and never let a reference and its candidate straddle it.
- **The app version is pinned.** The sidebar, the changelog and the About tab show the build's version, which is
  `git describe` by default and so differs between any two commits. `gallery_snapshot.sh` exports
  `LF_APP_VERSION` (default `v0.0.0-review`) and rebuilds the frontend in debug mode first when the checkout's
  build does not carry it (`build.log` in the snapshot). `meta.json` records it as `app_version`.
- A full gallery takes **30–40 min** at **6 workers** (`-- --workers 6`) and about **500 MB** (four languages): 30 min
  for 2824 PNG on 15/10, 31–39 min for 2888–2904 PNG on 16/10.
  Until C-94 (J) makes the default about 60 % of the cores, do not leave the worker count at its default:
  `dev.py mkdocs gallery` starts one browser worker per CPU plus three server workers, which saturates a 10-core
  machine. On 15/10/2026 a run at 10 workers reached load 65 and had 8 red tests in its first 10 minutes, with requests
  stuck for 10–20 s; the same tests passed alone, and two full runs at 6 workers had none.
  A `diff` of two full snapshots takes 3.5–7 min; with 2700 changed images (a colour migration), about 23 min, most of
  it writing the composites. The designer package weighs about 120 MB per language.

## Workflow

### 1. Noise baseline (once per comparison day)
Two captures of the same commit show what changes on its own:
```bash
scripts/visual_review/gallery_snapshot.sh base-r1 -- --workers 6
scripts/visual_review/gallery_snapshot.sh base-r2 -- --workers 6
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
scripts/visual_review/gallery_snapshot.sh ref -- --workers 6                    # target checkout, lane 6150
scripts/visual_review/gallery_snapshot.sh cand --checkout <worktree> --port 6151 --data-dir /tmp/librefolio-r2-x -- --workers 6
pipenv run python -m scripts.visual_review.live_price_check $W/snapshots/ref $W/snapshots/cand   # must exit 0
pipenv run python -m scripts.visual_review.gallery_tool diff $W/snapshots/ref $W/snapshots/cand --out $W/diffs/ref__vs__cand \
    --ignore-masks $W/diffs/noise/masks --stability $W/diffs/noise/stability.json
open $W/diffs/ref__vs__cand/index.html       # A | B | changed pixels in red; likely-real changes first
pipenv run python -m scripts.visual_review.gallery_tool sheet $W/diffs/ref__vs__cand --lang it
open $W/diffs/ref__vs__cand/contact_sheet.it.html   # one row per shot, the most VISIBLE change first
```
For a filtered capture (`-- -f "Dashboard"`), add `--common-only` to the diff.
A refactor that should not change the look must give `identical`, plus noise on the `unstable` shots.
A change meant to be seen, like a colour migration, «changes» nearly every image at tolerance 0. Read it with `sheet`:
- it ranks the shots by the share of pixels whose largest channel change exceeds 12 levels, the noise masks applied;
- it lists on top the images that are new, gone or of another size;
- the measures are kept in `visible.json`, so another `--lang` takes a second.

Measuring a full gallery takes about 5 min.

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

### 3b. A later review round: today, before and after, colours left, questions
`build_designer_round.py` builds the package of a later round (giro 3 on 16/10). Every page comes in HTML and in
Markdown, with relative image paths, and `LEGGIMI.md` indexes them for a designer's AI. Run it on the snapshot's commit:
```bash
pipenv run python -m scripts.visual_review.gallery_tool diff $W/snapshots/baseline-r2 $W/snapshots/cand --out $W/diffs/baseline-r2__vs__cand
pipenv run python -m scripts.visual_review.gallery_tool sheet $W/diffs/baseline-r2__vs__cand --lang it
pipenv run python -m scripts.visual_review.color_inventory --out $W/inventory/cand
pipenv run python -m scripts.visual_review.build_designer_round $W/snapshots/cand --before $W/snapshots/baseline-r2 \
    --diff $W/diffs/baseline-r2__vs__cand --inventory $W/inventory/cand --reasons <motivi.csv> --questions <domande.md> \
    --name LibreFolio_review_colori_giroN_<date> --round N --copy-to ~/Downloads
```
- **Pages:**
  - `desktop`/`mobile`: the screens of today.
  - `prima-e-dopo-desktop`/`-mobile`: before and after, light and dark. The new and gone shots come first, then the
    most visible change (`visible.json` of `sheet`).
  - `colori-residui`: the legacy palette classes left, file by file, grouped by reason, with the colour each one
    paints.
  - `domande-aperte` and `palette-ruoli`: the Markdown files given, copied as they are and rendered.
  - `APRI_QUI` and `LEGGIMI.md`.
- **The colours left** come from `color_inventory.py`, kept only where the colour gate would count them: production
  code outside comments (`codeOf` of `theme-roles.mjs`), legacy classes as the gate defines them. On 16/10 this gave
  the gate's own files: 185 against 185.
- **The reasons** come from a `path;motivo;dettaglio;chi` file (path under `frontend/src`). A file without a reason is
  listed under «Da classificare» and named on the console.
- **Images** are WebP lossless by default: the same pixels as the PNG, about half the size (`--format png` keeps PNG).
  One language of two galleries, the before-and-after included, makes a zip of about 140 MB.
- **The «before» is called v1.2**, and the pages say that the two captures are of different days: true for the round
  of 16/10. For another «before» or a pair of the same day (round 3, 18/10), the text of the generated pages had to be
  corrected after the build. An option for it is planned (G-27).

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

### 6. Mixed elements (the runtime twin of G3)
The colour gate G3 (`frontend/scripts/theme/theme-roles.mjs`) forbids an element that mixes role utilities
(`bg-lf-card`) with legacy colour classes (`text-gray-500`): `app.css` exempts every element carrying `-lf-` from its
legacy dark remap, so such an element breaks in dark. G3 reads the sources, and cannot see a class composed at runtime:
a `className` or `contentClass` prop passed between areas, an imported constant, a concatenation.

So every snapshot scans each shot, after the capture, with the gate's own patterns. The scan is
`frontend/e2e/fixtures/galleryMixed.ts`, on only when `gallery_snapshot.sh` sets `LF_GALLERY_MIXED_DIR`. It only
reports: a scan error is a record, never a red, and the PNG does not change.
- `mixed_elements.json` in the snapshot has one record per shot: the elements with classes, with a role class, with a
  legacy class, and the mixed ones (tag, test id, nearest test id above it, selector, classes, on screen or not).
- A run's log shows `🎨 <shot>: N mixed` for a shot that has some.

```bash
pipenv run python -m scripts.visual_review.gallery_tool mixed $W/snapshots/cand                # by folder of the candidate file
pipenv run python -m scripts.visual_review.gallery_tool mixed $W/snapshots/cand --by section    # by gallery section
pipenv run python -m scripts.visual_review.gallery_tool mixed $W/snapshots/cand --area lib/components/assets --on-screen
```
- The summary checks that every PNG has its record, and prints each distinct mixed element once, with its shots.
- **The candidate file is a hint, not a proof.** It is the file that writes the element's test id, or its nearest
  ancestor's: after a test-id key (`data-testid=`, `testid=`, `testId:`), whole, else composed from its longest prefix
  (`global-settings-category-{cat.id}`). The element may belong to a child component, and its class may come from the
  caller. An id found only as a plain string (`'chart'`) is a weak clue: such elements sit in their own group, not in
  an area.
- `gallery_tool mixed <snapshot> --collect` merges the records by hand, for example after a run interrupted before the
  script's end. On a retry, the latest record of a shot wins.

## Known gallery behaviour (18/10/2026, the reference trio)

Three full runs at 6 workers, all on 18/10 after 02:00, so with the same local and UTC date. They are the reference
after A8b (the Administration group of Settings), A9 (the legal notice) and the designer's round 3. The record is in
G's plan, «Galleria del giro 3»:
[plan-phase00GalleryDeterminism.prompt.md](../../LibreFolio_developer_journal/Release_2/Phase_1/10_colorSystem/G-galleryDeterminism/plan-phase00GalleryDeterminism.prompt.md).

| Snapshot | Commit | Captured | Tests |
|---|---|---|---|
| `g-r3-prima-ba8e06763-full` | `ba8e06763`, the target just before round 3 | 02:00–02:34 | 31.1 min |
| `g-r3-dopo-cd686f445-full` | `cd686f445`, round 3 complete | 02:36–03:10 | 29.4 min, after a 143 s build |
| `g-r3-dopo2-cd686f445-full` | `cd686f445` again | 03:10–03:42 | 29.3 min |

- **The reference is this trio.** It was kept on 19/10, when every older snapshot and diff was deleted to free the disk.
  - **Noise masks and stability:** `diffs/g-r3-dopo-cd686f445__vs__g-r3-dopo2-cd686f445` (`masks/`,
    `stability.json`), the same commit twice on the same day. Pass them to `diff` with `--ignore-masks` and
    `--stability`.
  - **For the eye on another day:** the three snapshots. A pixel diff still needs a reference captured on the
    candidate's day (see «Lanes and rules»).
  - The `-full` snapshots keep the PNGs, `meta.json` and `mixed_elements.json`. The base runs, their fills and their
    logs were deleted.
- **Each run:** 258 tests passed, 1 skipped (`mobile menu open`, on desktop), 1 red, 2900 PNG. No live price, no mixed
  element, no CSP violation outside `e2e/csp-baseline.json` (H-43).
  - The red is the same in the three runs, alone at 2 and 1 workers too: `Onboarding › welcome setup` on the phone in
    `fr` and `es`. Since A9 the legal notice under the card makes the page taller than the screen, and the shot wants
    the whole form in view (G-25). Those 4 images are missing on every side.
- **Noise (dopo↔dopo2):** 2081 of 2900 images identical. Classes: 27 `stable`, 133 `low`, 18 `medium`, 4 `unstable`.
  - Unstable:
    - `assets/detail-editor` and `brokers/import-nway-compare`, as on 16/10;
    - `auth/01-login`: one variant, at most 5 levels, so invisible;
    - `settings/password-modal`: on the phone in `es/dark` the page behind the modal stops at another scroll (G-26).
  - Since 16/10, `assets/detail-measures` went from `unstable` to `low` (G-11), and `files/brim-report-sets` from
    `unstable` to `medium`.
- **Round 3, prima↔dopo:** with the noise masked, 2055 of 2900 images are identical (1766 raw); 350 differ only in the
  noise, negligibly or in unstable shots; 495 changed beyond the noise; none is of another size. The designer's sheet,
  by area of the round: `sheets/r3-2026-10-18/index.html`.

## Known gallery behaviour (16/10/2026, commit `a2c1c39f4`, G-13)

History: the snapshots and diffs named in this section and in the next one were deleted on 19/10/2026. The analyses
in G's evidence remain.

Three full runs of the same commit at 6 workers (`g-ref13-r1`/`r2`/`r3`). The analysis is in G's evidence:
[analysis-g13-2026-10-16.md](../../LibreFolio_developer_journal/Release_2/Phase_1/10_colorSystem/G-galleryDeterminism/evidence/analysis-g13-2026-10-16.md).

- **Red tests come from load.**
  - r1 ran at load 35–45, beside other lanes' builds. It had 6 red tests: `page.screenshot` waiting for fonts, and
    20 s click timeouts.
  - r2 and r3 ran on a quiet machine, with 0 red tests.
- **The noise pair is r1↔r2.** It has the same commit and the same local and UTC date; r3 has another UTC date (see
  «Lanes and rules»).
  - Classes: 22 `stable`, 137 `low`, 18 `medium`, 4 `unstable`.
  - Unstable:
    - G-11 on the phone in `es/light`, one variant each: `assets/detail-measures` and now `assets/detail-editor`;
    - `files/brim-report-sets`: the random name of the disposable account, which also resizes the open filter;
    - `brokers/import-nway-compare`: the order of the set's two files.
- **`media/asset-picker-modal` is `low`.** It was unstable before H's fix of the order of uploads (G-10).
- **The reference for the candidates of 16/10 was `g-ref13-r3`**, with the masks and the stability of
  `g-ref13__r1__vs__r2`. Since 18/10 it is the trio above.
- **After a colour migration, «changed» is not «visible».** At tolerance 0 nearly every image changes by a few levels.
  `gallery_tool sheet` ranks the shots by visible change. The night's candidate:
  `diffs/g-ref13-r3__vs__g-cand16a/contact_sheet.it.html` and `visible.json`. Of 182 shots, by median visible change:
  91 at 10 % or more (dialogs and wizards), 53 at 1–10 %, 20 at 0.1–1 %, 18 under 0.1 %.

## Known gallery behaviour (15/10/2026, commit `2338aaf79`)

Two full runs of the same commit (`g-final3-r1`/`r2`, 6 workers, both clean for `live_price_check`). The analysis of
every unstable and medium shot is in G's evidence:
[analysis-final-2026-10-15.md](../../LibreFolio_developer_journal/Release_2/Phase_1/10_colorSystem/G-galleryDeterminism/evidence/analysis-final-2026-10-15.md).

- **No red test at 6 workers.** The failures of the 14/10 full runs did not recur: login stuck on «auth-loading», three
  transaction modals, `Dashboard Risk › what-if crisis replay`. At 10 workers the machine saturates (see above).
- **The what-if replay preset** is now chosen in every run: `chooseReplayPreset` parks the pointer and walks the menu
  in both directions (G-3).
- **6 shots of 177 are `unstable`**, down from 27 on 14/10.
  - By content, accepted:
    - `media/asset-picker-modal`: the seed's image order;
    - `brokers/import-nway-compare`: the order of the set's two files.
  - By framing, fixed by G after the measure (checkpoint 2). A `scrollIntoViewIfNeeded()` depended on where the page
    was:
    - `assets/detail-measures` and `detail-measures-active` on the phone;
    - `settings/about-plugin-diagnostics` on the phone;
    - the page behind the modal of `settings/scheduler-config`.

    Verified alone twice: all stable or `low`, except one variant. On the phone in `es/light`, the header of
    `assets/detail-measures` can stay visible where the page ends before the chart (G-11).
- **The seeded scheduler log has fixed times on the day before**, and its modal lists the last 24 hours. A reference
  and a candidate taken on two sides of about 06:00, 12:10, 18:00 or 23:00 differ in `settings/scheduler-log`.
  This is content.
- **19 shots are `medium`.**
  - Content: times, the names of disposable accounts, random codes, durations measured in ms, the order of uploaded files.
  - Two render residues: the sticky cells of the FIFO lots table, and the antialiasing of the RSI and MACD canvases.
- **Screenshots are sRGB.** Tailwind v4 colours are OKLCH and often outside sRGB, so the live app on a wide-gamut
  display (recent Macs) looks more saturated than the PNGs.
