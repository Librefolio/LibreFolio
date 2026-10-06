# Plan Phase 00 — Release images (production frontend, real light/full) + HTTP compression (+ queued Tailscale watchdog)

**Creato**: 2026-10-06
**Baseline/target**: `c77c7f09e168004b4f50740d7736abe56327fe2b` (`dev_release2`), HEAD verified after the fast-forward (from `c8daff33f`)
**Workstream**: M — branch `e-alfy-cloud-resource-sizing`, worktree `LibreFolio-worktrees/e-alfy-upgraded-telegram`
**Coordinator**: session `c8328a01-f208-4ade-a352-0486d1f14de2`
**Runtime lane**: ports `6158`/`6168`, data dir `/tmp/librefolio-r2-m`; results outside the repo in `LibreFolio-cloud-sizing/release-images/`
**Origin**: the two release blockers found by the cloud sizing study (`LibreFolio-cloud-sizing/REPORT.md`, items 1 and 7)
**Autorizzazione developer**: plan approved in M's session on 2026-10-06 14:27 (exit from plan mode); D9 and O3 relayed by the coordinator at 14:37.
**Follow-up**: the coordinator's «passo 8» (flattened code blocks in IT/FR/ES translations, the cause behind the step-6 hand fix) → [plan-phase00TranslatedCodeIndent.prompt.md](plan-phase00TranslatedCodeIndent.prompt.md)

## 0. Decisions (developer verbatim where quoted; relayed by the coordinator)

| Topic | Decision |
|---|---|
| `latest` mapping | «è corretto che la latest punti anche alla light, mi torna, quello che è errato è che light e full hanno la stessa size con il debug attivo» → `latest` = light **stays**; the `release.yml` tag mapping is unchanged |
| Compression | «direi proprio che va fatta» |
| O3, docs tags | «fare che latest sia il tag-light è stata un ottima mossa, non ha senso fare il latest-full o correggere, come è ora va bene, correggiamo la guida e allineamola a questa logica» → docs only: `latest` = light, `X.Y.Z` = full, `X.Y.Z-light` = light (no `v`); remove `latest-light` and `v1.1.0-light` from the guide |
| Option E (`dev.py` rebuild on mode mismatch) | not done: `dev.py` untouched |
| D9 (a) | workaround A re-approved: «riusa il builder col certificato aziendale che avevi approvato il 05/10», same conditions (never pushed, CA absent from the runtime image, everything deleted at the end) |
| D9 (b/c) | clone `node_modules` with `cp -c` from `/tmp/librefolio-r2-m-src/bff29231c/frontend/node_modules` into the proof scratch and the worktree's `frontend/`, after checking the lock hash against the target (recorded); no npm install |
| Runner registration | new entries only: `_backend_api.py` before `:743`, `_backend_utils.py` after `:270`, keeping ≥ 5 lines away from `:680`/`:692`/`:303` |
| Out of scope | multi-arch, `JWT_SECRET`, the `latest` mapping; CHANGELOG belongs to the coordinator |
| Tailscale watchdog | queued as step 6: only after the developer has tested the script on his server and the coordinator says go |

## Sintesi (italiano, analisi del 2026-10-06)

- **Frontend di debug.** La release esegue `front build` (produzione) e poi la gallery. La gallery avvia `dev.py server --test`, che forza la modalità debug e ricostruisce `frontend/build` senza minify e con le sourcemap. Le due `docker build` copiano quella build: 58 MB invece di 21. **Fix:** un `front build` di produzione dopo la gallery, più uno stadio di controllo nel Dockerfile che fa fallire la build dell'immagine se il frontend non è di produzione. Il controllo vale per la CI e per le build locali.
- **Full e light identiche.** La CI costruisce il sito MkDocs **prima** della gallery e non lo ricostruisce dopo, quindi gli screenshot non entrano mai in `site/gallery/`. Anche la full li carica online e le due varianti sono identiche byte per byte. **Fix:** ricostruire il sito dopo la gallery. La full porterà ~2.050 PNG (≈ 357 MB misurati su GitHub Pages), la light continuerà a toglierli. Stima: light ≈ 1,60 GB scompattata / ≈ 446 MB compressa; full ≈ 1,96 GB / ≈ 0,8 GB.
- **Cosa togliere ancora alla light** (misurato): sviluppatori 94 MB, traduzioni 200 MB. Sconsiglio entrambi per la 1.2: diventerebbero link rotti nell'help in-app, e servirebbe un fallback online in `main.py` fuori dal perimetro.
- **Compressione HTTP.** Propongo il `GZipMiddleware` di Starlette 1.6 accanto al CORS, con `minimum_size=1024` e `compresslevel=6`, lasciando le esclusioni di default. Ho verificato nel sorgente installato che salta già immagini, font, archivi, SSE (`text/event-stream`), le risposte 206 e quelle già codificate. Mette `Vary: Accept-Encoding` e comprime in un thread i corpi ≥ 128 KiB.
  - **Livello:** misurato sui corpi reali, il 6 dà la stessa dimensione del 9 con un terzo della CPU. Il costo è ~40 ms di CPU per sessione.
  - **Byte stimati:** prima visita 7,5 → 2,8 MB, sessione 5,8 → 0,8 MB, pagina docs 202 → 20 KB.
  - **Pre-compressione in build:** non per la 1.2. Guadagna solo 0,37 MB alla prima visita e tocca file fuori dal perimetro.
- **Watchdog Tailscale:** è il passo 6, in coda. Si fa dopo il tuo test sul server e il via del coordinatore: lo script testato e le aggiunte al compose nelle 4 lingue, più un paragrafo EN.
- **Correzione al mio REPORT:** gli asset `/_app/immutable/` **hanno** `Cache-Control: immutable`; avevo letto il campo sbagliato. Lo correggo.
- **Immagini Docker sparite:** non ci sono più immagini locali, nemmeno T2 e d9; non le ho rimosse io. Per `run_delta.sh` vanno ricostruite.
- **Decisioni per te** (sezione 9): le principali sono il contenuto di light e full, il guard nel Dockerfile, i parametri gzip e i permessi per le build di prova (builder col certificato aziendale, `node_modules`).

## 0. Identity and baseline

| | |
|---|---|
| Worktree | `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-upgraded-telegram` |
| Branch | `e-alfy-cloud-resource-sizing` (app-managed name) |
| HEAD | `c8daff33f496425f2ad79abce516827196bc2fe9`, clean |
| Target (analysis) | `dev_release2` `aa74797ff`: `c8daff33f` is its ancestor; `git diff c8daff33f aa74797ff` is **empty** for `release.yml`, `Dockerfile`, `.dockerignore`, `backend/app/main.py`, `dev.py`, `frontend/svelte.config.js`, `frontend/vite.config.ts`, `scripts/cli_base.py`, `mkdocs_src/mkdocs.yml` |
| Lane | ports 6158/6168, data dir `/tmp/librefolio-r2-m`; results outside the repo in `LibreFolio-cloud-sizing/` |
| Coordinator | session `c8328a01-f208-4ade-a352-0486d1f14de2` |
| Graph | graphify artefacts absent in this worktree (expected); devWiki not needed for these surfaces |

Found today:
- **No Docker images are left on the daemon**: T2/d9/base images, 0 images; build cache 287 records, volumes 3. My last image check passed at 11:20. The daemon has no events since 09:15 UTC, so it was restarted and the removal cannot be attributed; I did not remove these images. `scripts/run_delta.sh` therefore needs fresh builds (decision D9).
- **REPORT correction**: item 7 says the hashed assets have no `Cache-Control`. Wrong: all 1,387 `/_app/immutable/` responses carry `public, max-age=31536000, immutable` (`main.py:419-423`); my check had read a non-existent field. Fixed after approval (results dir).

## 1. Current state

### 1.1 The published images ship the debug frontend
1. `release.yml:114` builds the frontend with `dev.py front build` (production; marker `frontend/build/.build-debug` = `0`, `dev.py:1994`).
2. `release.yml:133` builds MkDocs, then `release.yml:143-160` runs the gallery (`dev.py mkdocs gallery --workers 4`).
3. Playwright's webServer is `./dev.py server --test …` (`frontend/playwright.config.ts:164`).
4. `cmd_server` forces `debug_mode = True` in test mode (`dev.py:185`) and calls `auto_build_frontend(debug=True)` (`dev.py:216`).
5. The mode mismatch triggers a rebuild with `npm run build:debug` (`frontend/package.json:9`: `--mode development`; `vite.config.ts:91-92`: sourcemaps on, minify off), and the marker becomes `1`.
6. Both `docker build` steps (`release.yml:248`, `:258`) run with `frontend/build` still in that state, and `Dockerfile:102` copies it as is.
- **Result:** 58 MB of frontend instead of 21 MB, with 103 `.map` files (REPORT item 1).
- **Locally:** `_docker_ensure_assets_built` (`dev.py:1465`) rebuilds only when sources are stale (`check_frontend_needs_build`), not on a mode mismatch. A debug build left by `server --test` therefore ships in local images too (it happened to the first d9 image on 2026-10-05).

### 1.2 `full` and `light` are byte-identical
- **The variants** (`Dockerfile:20-41`): `docs-full` copies `mkdocs_src/site/`. `docs-light` copies it too, then deletes images under `/site/gallery` (`:35-39`).
- **Where the screenshots come from:** they are gitignored (`.gitignore:79`). The gallery writes them to `mkdocs_src/docs/gallery/{viewport}/{lang}/{theme}/{category}/{name}.png` (`dev.py:886`, `frontend/e2e/gallery.spec.ts:139-148`).
- **Why the full image has none:** CI builds the site **before** the gallery (`release.yml:133`, deliberately: fast webServer start) and never rebuilds it. So `site/gallery/` holds 0 PNG, the full image holds none, and **both variants fetch the screenshots from GitHub Pages** through the fallback in `gallery-img-loader.js:109-170`.
- **Locally**, the MkDocs staleness check only looks at `*.md` files (`dev.py:1494-1506`).
- **Documented contract broken:** `user/installation.en.md:174` says full "includes … screenshots … for fully offline use"; `admin/docker_advanced.en.md:189` says "~1.5 GB vs ~2.9 GB full".
- **Tag mismatches found** (the `latest` mapping is out of scope, so these are only flagged):
  - On release events `latest` resolves to the light image (metadata-action's automatic `latest` is emitted by both metadata steps, and the light build runs last); the developer confirmed this is intended.
  - `latest-light` is produced only on `main` pushes (`release.yml:241`) and did not exist in the registry, yet the docs tell users to pull it (`installation.en.md:175,188`).
  - The release-notes snippet prints `%s-light` with the `v`-prefixed tag (`release.yml:304`), but images are tagged without `v` (`1.1.0-light`). The docs example `v1.1.0-light` (`installation.en.md:177`) does not exist either.

### 1.3 HTTP compression
- **Current state:** the only middleware is CORS (`main.py:332-337`). No response is compressed (all 1,680 responses of the container walk: identity).
- **Serving paths:**
  - `/_app` → `ImmutableStaticFiles` (`main.py:419-426`): StaticFiles with ETag, 304 and Range, plus the immutable 1-year cache.
  - `/mkdocs/{path}` → `FileResponse` (`main.py:377-390`): no `Cache-Control`, no 304.
  - `/` → `index.html` (`main.py:393-405`).
  - The catch-all serves build-root files and `200.html` with `no-cache` (`main.py:440-468`).
- **Streaming responses:**
  - SSE asset search (`api/v1/assets.py:536-545`, `text/event-stream`, `X-Accel-Buffering: no`);
  - backup exports `StreamingResponse` JSON/CSV (`api/v1/backup.py:264-394`);
  - uploads: images and files with a 1 h cache (`api/v1/uploads.py:451-469, 483, 555`).
- **Stack:** FastAPI 0.141.1, Starlette 1.6.0, uvicorn 0.52.4. Uvicorn does not implement `http.response.pathsend`, so `FileResponse` streams 64 KiB chunks.
- **Starlette 1.6 `GZipMiddleware`** (read in the installed source):
  - defaults: `minimum_size=500`, `compresslevel=9`;
  - **excludes** gzip/zip archives, `audio/*`, `video/*`, woff/woff2, avif/gif/jpeg/png/webp and `text/event-stream`;
  - **skips** status 206 and responses that already carry `Content-Encoding`;
  - adds `Vary: Accept-Encoding` to every response eligible by size (gzip and identity alike);
  - streams with `Z_SYNC_FLUSH` per chunk (no buffering of SSE-like streams);
  - compresses bodies ≥ 128 KiB in a worker thread with its own limiter (40), so the event loop is not blocked (project async rule).
- Runtime brotli is not available: `brotli` is a dev-only lock entry, so adding it would be a new dependency.

## 2. Measurements behind the decisions

| What | Result | Source |
|---|---|---|
| Gallery screenshots meant for `full` | 129 (category, name) pairs; en/light: desktop 128 PNG, 15.4 MB (avg 120 KB); mobile 129, 28.2 MB (219 KB); the other 7 lang/theme combinations are 1.00–1.05×; **≈ 2,056 PNG ≈ 357 MB**; served only at the site root (no per-language copies, checked on Pages) | `ri_gallery_sizes.json` (594 HEAD requests on GitHub Pages, no download) |
| Docs site without screenshots (T2 build) | 279 MB, 1,369 files; HTML 266 MB (1,258 pages, ~206 KiB each; the primary nav is ~39 % of each page); 66.5 MB per language; per language: developer 23.6, financial-theory 20.4, user 18.9, admin 1.8, community 0.6, gallery pages 0.7 MB; search index 4.9 MB; doc images 3.3 MB; Material sourcemaps 1.3 MB | `ri_docs_site_t2.txt` |
| Frontend | production 21 MB, debug 58 MB (103 `.map`) | REPORT item 1 |
| gzip on the real bodies of a session (HAR of the T2 container walk; best of 3; host load 25) | API JSON, 37 unique, 2.41 MB: L1 0.28 MB / 7.5 ms · L6 **0.22 MB / 19 ms** · L9 0.21 MB / 62 ms. Static text, 8.47 MB: L1 3.20 / 71 ms · L6 **2.79 / 236 ms** · L9 2.79 / 287 ms. Docs page: 202 → 20 KB at 1.3 ms (L6) | `ri_gzip_levels.json` |
| `minimum_size` | 11 of 37 API bodies < 500 B, 13 < 1,024 B; going to 1,024 forgoes 1.3 KB per session | same |
| Wire bytes with gzip-6 (T2 walk what-if) | cold first visit 7.54 → ≈ 2.76 MB; warm 8-page session 5.75 → ≈ 0.83 MB | REPORT item 7 |

## 3. Options and recommendation

### 3.1 Production frontend in the image
| Option | What | Verdict |
|---|---|---|
| A | `release.yml`: a production `dev.py front build` **after** the gallery, before `docker build` | **yes** (≈ +1.5–2 min of CI) |
| B | Move the existing build after the gallery | no: the gallery still needs a build first, and the webServer would rebuild in debug inside its 120 s start timeout |
| C | **Fail-closed guard in the Dockerfile**: a `frontend` stage copies `frontend/build/`, runs `scripts/docker/check_frontend_build.sh` (fails on `.build-debug` = `1`, on `.coverage-instrumented`, on any `*.map`, or when `index.html`/`200.html` is missing), and the final stage copies `--from=frontend` instead of from the context. Same bytes, no extra layer; protects CI **and** local builds | **yes** |
| D | Build the frontend inside Docker (node stage) | no: npm network in the build (TLS interception locally), slower, breaks the `dev.py docker build` model |
| E | `dev.py` `_docker_ensure_assets_built`: rebuild on a mode mismatch (reuse `auto_build_frontend(debug=False)`) | optional: `dev.py` is a shared surface, so it needs assignment; without it, the guard's message tells the user to run `./dev.py front build` |

### 3.2 What `light` drops (proposal with measured sizes)
| Candidate | Size | Proposal |
|---|---|---|
| Gallery screenshots (≈ 2,056 PNG) | **≈ 357 MB** | **in full, not in light**: the documented design, restored by rebuilding the docs after the gallery |
| Docs text, 4 languages | 279 MB | keep in both (offline help, navigation intact) |
| – developer section | 94 MB (23.6 × 4) | keep: removing it leaves 404s in the in-app navigation unless `mkdocs_static` falls back to the online site (`main.py:377-390`, outside "middleware only") |
| – IT/FR/ES translations | 200 MB | keep, for the same reason |
| Material JS sourcemaps in the docs | 1.3 MB | negligible |
| Not light-specific: third-party test suites 158 MB, docs tooling at runtime 65 MB, nav weight (`navigation.prune` ≈ −39 % of HTML, incompatible with `navigation.expand`) | — | **outside this P0**: separate decisions, both variants |

Expected after the fix:

| Variant | Unpacked | Compressed |
|---|---|---|
| light | ≈ 1.60 GB | ≈ 446 MB (T2 local estimate) |
| full | ≈ 1.96 GB | ≈ 0.8 GB (PNGs barely compress) |

The gallery is best-effort: full ships the screenshots that succeeded, and the rest load online.

Docs rebuild, two ways: **(P1, recommended)** a second `dev.py mkdocs build` after the gallery (≈ 1 min, canonical, same `continue-on-error` semantics on `dev`); (P2) copy the PNGs into `site/gallery/` (seconds, but it hand-edits the build output).

### 3.3 HTTP compression
| Option | Verdict |
|---|---|
| **G1** Starlette `GZipMiddleware(minimum_size=1024, compresslevel=6)`, default exclusions | **yes** |
| G2 G1 + build-time precompression (SvelteKit `precompress: true` + `.br`/`.gz` negotiation in `ImmutableStaticFiles`) | not for 1.2: −0.37 MB on the cold visit only (br-11 2.06 vs gzip-6 2.43 MB of static), −0.24 CPU-s per browser per release; costs +~5 MB of image, negotiation/ETag/304 code, and touches `svelte.config.js` + `main.py:419-426` (outside the assigned surfaces) |
| G3 runtime brotli/zstd | no (new dependency; Safari lacks zstd) |
| G4 reverse proxy | not available in a single-image Fly deployment |

**Placement:**
- import `from fastapi.middleware.gzip import GZipMiddleware` as `main.py:23` (after the CORS import at `:22`);
- `app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)` right after the CORS block (`:337`), which makes gzip the outermost user middleware;
- a short comment with the reasons.

Arguments are explicit so a Starlette upgrade cannot change them silently.

**Interactions:**

| Surface | Behaviour with G1 |
|---|---|
| `/_app` | JS/CSS compressed in 64 KiB chunks; PNG and fonts skipped; `Cache-Control: immutable` and the strong ETag kept |
| ETag | Reusing the identity ETag for the gzip representation is a spec nit. Accepted: no shared cache sits in front, and immutable assets are never revalidated. |
| Docs and SPA (`FileResponse`) | Compressed (docs pages ÷10); still no 304 (unchanged) |
| Range | 206 stays identity |
| SSE | Excluded |
| Backup exports | Streamed gzip; the browser saves the decoded file |
| Large JSON (≥ 128 KiB) | Compressed off the event loop |

**CPU:** ≈ 40 ms per typical session, plus ≈ 0.24 s per browser per release for static assets.

**BREACH:** auth responses are < 1 KiB, so never compressed, and no CSRF token travels in a body. Low risk for a same-origin single-tenant app; noted.

### 3.4 Small items inside the assigned surfaces (optional, each needs a yes)
- **O1** `.dockerignore`: add `**/__pycache__/` and `**/*.pyc`. Today the patterns match only at the root, so local builds after running the server ship stale bytecode; the published images are clean.
- **O2** `release.yml:304` release notes: strip the leading `v` so the printed pull commands exist (`1.1.0`, `1.1.0-light`).
- **O3** Docs vs registry tags (`latest-light`, `v1.1.0-light`): this touches the mapping decision, so it is the developer's call. Either the docs say `latest` = light and name real tags, or CI also emits `latest-light`/full tags on releases.

## 4. Steps (implementation only after approval + fast-forward)

0. **Baseline.** Check that HEAD equals the target the coordinator sends, the worktree is clean and the file:line references above still hold. Write the journal plan. Copy this analysis's evidence to `LibreFolio-cloud-sizing/release-images/` and fix REPORT item 7 there.
1. **Image** (`Dockerfile`, new `scripts/docker/check_frontend_build.sh`, `release.yml`, optional O1/O2):
   - frontend check stage + `COPY --from=frontend` (C);
   - after the gallery step: "Rebuild frontend (production, for the image)" (A) and "Rebuild MkDocs with the gallery screenshots" (P1, `continue-on-error` on `dev`, added to the soft-failed report);
   - Dockerfile header and light-stage comments updated.
2. **Compression** (`backend/app/main.py`, middleware region only): G1 as in 3.3; lint/format with the project tools on the changed file.
3. **Tests** (test-author, distinct files):
   - **T1, API category, live lane server:** `Content-Encoding`/`Vary` matrix:
     - large JSON with `Accept-Encoding: gzip`: gzip, `Vary` present, decoded body equals the identity body;
     - the same request without gzip: identity with `Vary`;
     - a response < 1 KiB: identity;
     - a `/_app/immutable` asset: gzip, with `Cache-Control` and ETag kept;
     - PNG: identity;
     - `Range` → 206 identity;
     - SSE `text/event-stream`: identity, only if a non-live provider can be used, else covered by the middleware configuration.
   - **T2, utility category, no server:** the guard script on temp dirs (production OK; `.build-debug` = 1, `.map`, `.coverage-instrumented`, missing index → non-zero and a clear message).
   - **T3 (optional):** a `release.yml` order contract test (PyYAML): a production `front build` and a `mkdocs build` sit after the gallery step and before both build-push steps.
   - Registration in the runner catalogue (shared surface: coordinate).
4. **Proof without publishing:** section 5. Results in `LibreFolio-cloud-sizing/release-images/`.
5. **Docs** (docs-writer, EN only):
   - `user/installation.en.md:170-190` and `admin/docker_advanced.en.md:189-205`: what full/light contain, measured sizes, internet need, tags as decided in O3;
   - optional admin note that the app compresses responses itself.
   - Then `dev.py mkdocs build` (strict), `check-links`, `translate-validate`; stamp only if the edit stays punctual.
6. **Queued — Tailscale watchdog** (only after the developer has tested the script on his server and the coordinator says go):
   - replace `mkdocs_src/docs/static/tailscale-guide/custom_startup.sh` (32 lines today; `containerboot &` unsupervised at `:6`, an unbounded `until … Running` loop at `:20-23`) with the coordinator's tested script (`…/c8328a01…/files/tailscale-guide/custom_startup.sh`, 71 lines), after a diff review;
   - in **both** compose blocks of all 4 `admin/service_exposure.{en,it,fr,es}.md` (`:430-466` and `:545-580`, identical code), add `TS_ENABLE_HEALTH_CHECK=true`, `TS_LOCAL_ADDR_PORT=127.0.0.1:9002` and a `healthcheck` with `wget -q -O /dev/null http://127.0.0.1:9002/healthz` (Tailscale ≥ 1.78);
   - one EN prose paragraph via docs-writer (plain Docker does not restart unhealthy containers, so the watchdog exit is what restarts; no autoheal), **no translation stamp**;
   - checks: `sh -n`, a fake-binary scenario run in `alpine` (no network), and `mkdocs build` + `check-links`. Note: the guide downloads the script from `main`, so users get the fix only after the next merge to `main`.
7. **Checkpoint handoff:** no server or container left; ports free; `git diff --check`; inventory; proposed commit message; FROZEN. The CHANGELOG belongs to the coordinator.

## 5. How each fix is proven without publishing

1. **Scratch tree.** Copy the worktree's tracked files, modifications included (`git ls-files | tar`), into `/tmp/librefolio-r2-m-src/<sha>-ri`.
2. **Reproduce the CI order there:**
   - production `front build`;
   - `mkdocs build`;
   - `dev.py server --test --test-port 6158 --data-dir /tmp/librefolio-r2-m/ri`, started until ready and stopped: the exact debug flip of CI;
   - 32 real screenshots (2 categories × 2 viewports × 4 languages × 2 themes, ≈ 3 MB from GitHub Pages) placed in `docs/gallery/`;
   - then the **new** steps: `front build` + `mkdocs build`.
3. **Image builds.** `docker build` full and light with the unmodified Dockerfile (workaround A for pip, D9).
4. **Content checks** on both images:
   - `.build-debug` = 0 and no `*.map` under `/app/frontend/build`;
   - JS minified;
   - full holds the 32 PNGs under `site/gallery`, light holds 0;
   - full − light = the PNG bytes;
   - unpacked size (`docker image inspect`) and compressed estimate (`14_compressed_estimate.py`).
5. **Negative control.** The same build with the debug `frontend/build` (step 2 without the new steps) **must fail** at the guard, with the message.
6. **CI order** (no workflow run): the T3 test, plus a dry replay of the `run:` lines of the changed steps in the scratch.
7. **Compression.** Run the light image on 6158 with R-mock.
   - Header matrix with `curl` (as T1, plus a docs page and the SSE stream: the time to the first event must not grow).
   - `netwalk_container.sh`: expect a cold first visit ≈ 2.8 MB and a warm session ≈ 0.8–0.9 MB (baseline 7.54 / 5.75), with `content-encoding: gzip` on text.
   - Core session CPU-s with `run_case.py`: within noise of the T2 baseline.
8. **Backend tests** on the lane: T1/T2/(T3), plus the existing API smoke selectors that touch `main.py`.
9. **Cleanup.** Remove every image and container built for the proof; delete the CA copies.

## 6. Risks
- **Full grows to ≈ 0.8 GB compressed** (by design); light is the default `latest`. The GHA cache holds the extra 357 MB layer (10 GB limit, LRU).
- **CI takes ~+3 min** (one more `front build` + `mkdocs build`).
- **A failed docs rebuild on `dev`** (`continue-on-error`) could leave a partial site in the nightly. That risk exists today for the first build; the report step will list it.
- **A guard false positive** if a future production build legitimately emits `.map` files: the message names the file; adjust the rule then.
- **Local friction:** after `server --test`, `dev.py docker build` fails at the guard until `./dev.py front build` runs. That is intended; option E removes it.
- **gzip CPU on a 6.25 % shared vCPU:** measured small (≈ 40 ms per session), and large bodies are compressed off-loop. Chunked transfer replaces `Content-Length` on streamed static files.
- **Starlette behaviour changes on upgrade:** the arguments are explicit, and T1 pins the observable behaviour.

## 7. Conflict forecast

| File | Change | Overlap |
|---|---|---|
| `backend/app/main.py` | +1 import at `:23`, +~8 lines after `:337` | The Risk family edits imports `~:41-52` and the lifespan `:269-299`, ≥ 18 lines away, so I expect a clean textual merge; the middleware is semantically independent |
| `Dockerfile`, `.dockerignore`, `release.yml` | owned (coordinator: no other branch) | none expected |
| `scripts/docker/check_frontend_build.sh` | new | none |
| tests | new files; **catalogue registration is shared** | coordinate |
| docs EN pages | installation/docker_advanced | creates translation debt for IT/FR/ES (normal); unknown other editors → coordinator |
| Tailscale step | script + `service_exposure.*.md` ×4 | unknown other editors → coordinator |
| CHANGELOG | not touched (coordinator) | — |

## 8. Definition of done
- Both proof images: production frontend (guard passes; negative control fails); full contains the screenshots and light does not; sizes measured and recorded.
- Compression verified on the wire: headers matrix, netwalk bytes, SSE unaffected, CPU within noise.
- T1/T2(/T3) green on lane 6158; lint/format clean; `git diff --check` clean.
- Docs EN updated; strict build + links OK.
- Results and commands recorded in `LibreFolio-cloud-sizing/release-images/` and in the journal plan, with every detour as "Fuori pista".
- No container, server or proof image left; ports free.
- Tailscale step done separately when released by the coordinator.

## 9. Decisions needed (recommendation first)
- **D1 Light/full content:** full = text + screenshots, light = text only, i.e. the documented design (recommended). Alternatives: additionally drop the developer docs or translations from light.
- **D2 Frontend guard:** A + C (recommended); add E if the coordinator assigns `dev.py`.
- **D3 Docs rebuild after the gallery:** P1, a second `mkdocs build` (recommended), or P2, a PNG copy.
- **D4 Compression:** G1 with `minimum_size=1024`, `compresslevel=6` (recommended); G2 later, if Fly CPU proves tight.
- **D5 Optional items:** O1 `.dockerignore` (recommended yes), O2 release-notes tag (recommended yes), O3 docs tags (developer's call).
- **D6 T3** (YAML order test): recommended yes.
- **D7 Test registration** in the shared runner catalogue: coordinator to sequence.
- **D8 Docs scope:** EN pages only (variants + optional compression note).
- **D9 Proof infrastructure:**
  - (a) re-approve **workaround A** (a throwaway pip builder trusting the corporate CA, never pushed, deleted afterwards), since all images are gone;
  - (b) `node_modules` for the production builds: reuse the T2 scratch's (same lock hash, checked first) or run an approved `npm ci` from the lock;
  - (c) the same for the **worktree** to run T1, because `dev.py test` starts `server --test`, which builds the frontend.

## 10. Commands (lane)
```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6158 --data-dir /tmp/librefolio-r2-m api <action-from-catalogue>
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6158 --data-dir /tmp/librefolio-r2-m utility <action-from-catalogue>
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs build && … mkdocs check-links   # docs
docker build -f Dockerfile [--build-arg DOCS_VARIANT=light] --build-context pybuilder=docker-image://<builder> -t lf-m-ri:<variant> <scratch>
lsof -nP -iTCP:6158 -sTCP:LISTEN; lsof -nP -iTCP:6168 -sTCP:LISTEN   # free at handoff
```

## Progress (after every step: ✅ with date, «Note implementazione», «Fuori pista»)

### 0. ✅ Baseline, journal, evidence — 2026-10-06
- Fast-forward `c8daff33f` → `c77c7f09e` run by the developer (`/tmp/libreFolio_ff_m_to_target.sh`, coordinator-reviewed); HEAD verified `c77c7f09e`, clean. The four touched files are byte-identical to the base of the drafts (`cmp` against `git show c8daff33f:<file>`).
- File:line references re-checked on `c77c7f09e`: `main.py:22` CORS import, `:331-337` CORS block, `:419-426` `ImmutableStaticFiles`, `:47-52` Risk imports, `:219` lifespan; `release.yml:143` gallery, `:167` soft-fail report, `:177`, `:303`.
- Lock check for the `node_modules` clone (`release-images/evidence/node_modules_lock_check.txt`): `frontend/package-lock.json` sha256 `0dbeb7bd7f3ecb0510e26a5a3ad1042aa1d46fb41248f05b1d99fa3360d67c6a` = target = T2 scratch; `package.json` `8746adb5…` identical; installed tree vs lock: 433 packages, 0 missing, 0 version mismatches, 0 extra (134 optional packages for other platforms not installed).
> **Note implementazione**: the evidence of the analysis and the drafts live in `LibreFolio-cloud-sizing/release-images/` (`evidence/`, `drafts/release-images.diff`, `scripts/15-17`). Pre-work before the fast-forward, outside the repo:
> - the guard script was tested on 9 cases (`evidence/guard_cases.txt`);
> - the draft Dockerfile stages were built for real (`evidence/docker_stages.txt`: the guard passes on production and fails on the CI-style debug build; the full docs stage keeps the gallery PNGs, light strips them);
> - GZip behaviour was checked on LibreFolio's serving patterns (`evidence/gzip_behaviour.txt`).
> **⚠️ Fuori pista**:
> - REPORT item 7 had wrongly said `/_app/immutable` assets lack `Cache-Control`; corrected in `REPORT.md` on 2026-10-06.
> - Every local Docker image (T2/d9/base) disappeared between 11:20 and 13:50, not removed by M; the daemon had been restarted, so there are no events. `run_delta.sh` will need fresh builds.

### 1. ✅ Image fix (Dockerfile frontend stage + guard script, `release.yml`, `.dockerignore`) — 2026-10-06
- `Dockerfile`:
  - new stage `frontend` (`FROM python:3.13-slim`) copies `scripts/docker/check_frontend_build.sh` and `frontend/build/`, then runs the check;
  - the final stage copies `--from=frontend /build/` instead of the context;
  - header comments updated (full = screenshots only if the gallery ran before the docs build).
- New `scripts/docker/check_frontend_build.sh` (POSIX sh). It fails on a missing `index.html` or `200.html`, `.build-debug` = 1, `.coverage-instrumented`, or any `*.map`; without a marker it only warns.
- `release.yml`:
  - after the gallery: "Rebuild SvelteKit Frontend (production, for the images)" and "Rebuild MkDocs Documentation (with the gallery screenshots)" (`id: rebuild-mkdocs`, `continue-on-error` on `dev`), the latter added to the nightly soft-fail report;
  - release notes print `${TAG_NAME#v}` (O2);
  - tag mapping untouched.
- `.dockerignore`: `**/__pycache__/`, `**/*.pyc`, `**/*.pyo` (O1).
> **Note implementazione**: applied by copying the drafts (`LibreFolio-cloud-sizing/release-images/drafts/`), whose base was verified byte-identical to `c77c7f09e` (`cmp`). Dash/sh syntax and YAML order checked.

### 2. ✅ HTTP compression (`main.py` middleware) — 2026-10-06
- `main.py:23` imports `GZipMiddleware`; `main.py:340-345` adds a comment and `app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)` right after the CORS block. The Risk regions (imports `:48-53`, lifespan `:220`) are untouched.
- `ruff check` passed and `black` left the file unchanged.
> **Note implementazione**: behaviour pinned in `release-images/evidence/gzip_behaviour.txt` (TestClient matrix on the real build files) before T1.
### 3. ✅ Tests (test-author) and gates — 2026-10-06
- **New tests:**
  - **T1** `backend/test_scripts/test_api/test_http_compression_api.py` (8 tests, GZIP-001…008). Bodies are read raw (`aiter_raw`) and URLs discovered from the served `index.html`. Covers:
    - `openapi.json` gzip vs identity (`Vary` on both, equal decoded JSON);
    - `/system/health` untouched;
    - the largest immutable chunk: gzip + `immutable` + ETag, 304, `Range` → 206 identity;
    - PNGs untouched;
    - the SSE search stream, offline via `providers=mockprov` with its own user (created and deleted);
    - the SPA fallback: gzip + `no-cache`.
  - **T2** `backend/test_scripts/test_utilities/test_check_frontend_build.py` (14): every rule of the guard, markers `0`/`0\n`/`1`/`1\n`/`" 1\r\n"`, a named `.map`, a directory with spaces, the usage error.
  - **T3** `backend/test_scripts/test_utilities/test_release_image_contract.py` (17, of which 11 negative on mutated text):
    - workflow order: production front build + docs build between the gallery and both image builds; the report reads `rebuild-mkdocs`;
    - Dockerfile: the frontend reaches the final stage only through the guarded stage; no direct context copy.
- **Registration** (new entries only):
  - `_backend_api.py`: def `:252-261`, entry `:753-762` right before `all` (`:763`), `write-scoped` because of the SSE user;
  - `_backend_utils.py`: defs `:172-189`, entries `:289-308` after `ai-export-probe-helpers`, `pure`;
  - `check-orphans` clean.
- **Runs** (lane 6158, data dir `/tmp/librefolio-r2-m/ri-test`):

  | Selector | Result |
  |---|---|
  | `utils check-frontend-build` | 14 passed |
  | `utils release-image-contract` | 17 passed |
  | `api http-compression` | 8 passed |
  | `--fresh-run --workers 4 api all` | **green**: 54 parallel units, 759 passed, 2 skipped (not compression-related), + 2 exclusive units, 32 passed; 0 failed. No existing API test depended on uncompressed bodies or `Content-Length`. |
  | `--workers 4 utils all` | 817 passed, **1 failed** |
  | `e2e all` | 7 passed |
- Each test was shown able to fail: T2 against mutated copies of the guard; T3 against the pre-change `HEAD` files (3 workflow and 2 Dockerfile violations); T1 by reasoning.
> **⚠️ Fuori pista**:
> - **Pre-existing red on the baseline**, unrelated to this work: `test_runtime_isolation.py::test_startup_timeout_matches_the_playwright_ci_contract[ci-absent]` expects 120 s, but commit `9db350102` ("wait up to 300 s for the shared backend") made `scripts/test_runner/_server.py:47` `STARTUP_TIMEOUT` a fixed 300. Both files are identical to `c77c7f09e`. Reported to the coordinator; not fixed here (out of scope).
> - The backend `e2e` category (`search-to-prices`) queries **live providers** (justETF, Borsa Italiana, yfinance; a few dozen requests, not proxied or counted exactly). It ran as a standard gate; no further live-provider selector will be run.
> - The worktree's `frontend/build` is now a debug build (from `server --test`), so a local `dev.py docker build` there would be refused by the new guard until `./dev.py front build`, which is the intended behaviour.
### 4. ✅ Proof without publishing — 2026-10-06
- **Proof scratch** `/tmp/librefolio-r2-m-src/c77c7f09e-ri`:
  - `git archive c77c7f09e` + the 5 changed/new files (sha256 in `evidence/proof_scratch.txt`);
  - `requirements.txt` from the T2 scratch (same `Pipfile.lock` `c6fb47b5…`);
  - `node_modules` cloned (`cp -cR`, same lock `0dbeb7bd…`).
- **CI replay** (`scripts/ri_ci_replay.sh`, `evidence/ci_replay_{A,B}.log`):
  - phase A (today's CI order: `front build` → `mkdocs build` → the gallery's debug flip `front build --debug`) left marker 1, 110 `.map` files, a 59.6 MB frontend and 0 PNG in `site/gallery`;
  - 32 real screenshots (2 pairs × 2 viewports × 4 languages × 2 themes, 2.96 MB, from GitHub Pages) were placed in `docs/gallery/`;
  - phase B (the new steps: `front build` → `mkdocs build`) left marker 0, 0 `.map`, a 21.4 MB frontend and 32 PNG in `site/gallery`.
- **Negative control** (`evidence/docker_build_negative_debug.log`): the full `docker build` with the phase-A frontend **fails in 10 s** at the frontend stage with the guard message; no image is produced.
- **Images** (unmodified product flow, no override; `evidence/docker_build_{full,light}.log`, `evidence/image_contents.txt`): `docker build` full in 86 s, light in 4 s. Both carry a production frontend (marker 0, 0 maps, 21.2 MB, minified JS).
  - Full holds 32 gallery PNG and light 0; the 50 `static/` PNG stay in both.
  - Docker `.Size` full − light = **2,961,040 B = exactly the PNG bytes**.
  - Compressed (gzip-6 estimate, `evidence/compressed_estimate_ri_*.json`): light 438.4 MB (≈ 443 MB calibrated); the 32 PNG add 2.77 MB.
  - Extrapolated to the full screenshot set (≈ 357 MB): **full ≈ 1.95 GB unpacked / ≈ 0.78 GB compressed; light ≈ 1.59 GB / ≈ 443 MB**.
- **O1 proof**: 2 stale nested `.pyc` in the context reach the image with the original `.dockerignore` (2) and not with the new one (0).
> **⚠️ Fuori pista**:
> - **Workaround A was not needed.** The network no longer intercepts TLS: pypi, files.pythonhosted, github, jsdelivr and googleapis present their public issuers from the host and from the Docker VM (Python 3.13, strict verification). The images were built with the product Dockerfile's own pybuilder stage; no CA was exported, so there is nothing to delete.
> - The negative control used `front build --debug` instead of a lane `server --test` start. It is the same code path (`dev.py:185` → `:216` → `cmd_fe_build(debug=True)`), and it keeps port 6158 free for test-author.
- **Compression on the wire** (`scripts/ri_wire_ab.sh`, `evidence/wire_ab_summary.txt`, `evidence/wire_light*_r{1,2}/`): A/B of two light images identical except `main.py` (`lf-m-ri:light` with GZip, `lf-m-ri:light-nogzip` with the `c77c7f09e` file; only the backend layer differs). Setup: lane port **6168** (6158 was in use by the test run), dataset R-mock, 1 vCPU, Playwright walk (`netwalk.cjs`), 2 rounds in opposite order.

  | Window | without gzip | with gzip |
  |---|---|---|
  | cold first visit | 7,456–7,489 KB | **2,780–2,785 KB (−63 %)** |
  | warm 8-page session | 5,374–5,935 KB | **888–889 KB (−84 %)** |
  | dashboard reload | 387 KB | **55 KB** |
  | idle | 0 | 0 |
  | walk CPU-s (cgroup) | 12.8 / 18.2 | 15.4 / 16.1 |

  - CPU means: 15.5 vs 15.7 (+0.2 s, within the noise of host load 12–38; the offline estimate was ≈ 0.3 s).
  - curl matrix: `openapi.json` 655 → 116 KB with `Vary: Accept-Encoding`; identity requests get identity + `Vary`; health (15 B) untouched; `/` and the SPA route gzip with `no-cache` kept; docs page gzip (chunked); favicon PNG untouched; `Range` → 206 identity.
> **⚠️ Fuori pista**: the immutable JS that curl picked first from `index.html` is an 83-byte entry, so it is correctly left uncompressed by `minimum_size`. The large chunks' compression shows in the walk instead (static 7,099 → 2,450 KB).

### 5. ✅ Docs EN (docs-writer) — 2026-10-06
- **`user/installation.en.md`:**
  - `:126` says `latest` is the light variant (recommended default).
  - `:172-198` rewrites "Image Variants" (anchor kept):
    - both variants share the app and all text pages;
    - light ≈ 450 MB download / ≈ 1.6 GB on disk;
    - full adds ≈ 2,000 screenshots, ≈ 0.8 GB / ≈ 2 GB;
    - tag table `latest` = light, `X.Y.Z` = full, `X.Y.Z-light` = light; no `v`, no `latest-light`;
    - the compose example for full is `:1.1.0`.
  - `:225` pin example `1.1.0` / `1.1.0-light`.
- **`admin/docker_advanced.en.md`:**
  - `:189` CLI comment without the wrong sizes;
  - `:199-210` local `dev.py` tags vs registry tags, plus a warning "A debug frontend build fails the image build — on purpose" quoting the guard message and the fix;
  - `:214-223` the screenshot tip with the full order (`mkdocs gallery` → `front build` → `mkdocs build` → `docker build`);
  - `:351-352` gzip note (a reverse proxy need not compress again).
- **Checks:**
  - `mkdocs build` strict: OK.
  - `check-links`: exit 1 only for the pre-existing `user/assets/detail/chart/#rolling-return` (anchor missing in it/fr/es; not touched).
  - `translate-validate` on these two pages: 0 → 27 errors / 6 warnings (it/fr/es). This is real translation debt, **not stamped**.
> **⚠️ Fuori pista** (flagged, not changed; outside the assigned pages):
> - `developer/docs/release-pipeline.md` is stale beyond this change: it describes a `force_gallery` input and a screenshot cache that no longer exist, tags `vX.Y.Z`, `--workers 8`, and has a `file:///…` link to a local checkout.
> - A manual `workflow_dispatch` on `main` would tag `latest` = full and create `latest-light`, because of `enable=main` at `release.yml:241,256`. That contradicts the documented logic; the tag mapping is out of scope.
> - The `1.1.0` examples and the "Beta (version 1.1.0)" line need bumping at the 1.2 release. Note that the published 1.1.0 full image has no screenshots: that was the bug.
### 6. ✅ Tailscale watchdog — 2026-10-06
- **Go:** developer, via the coordinator: «Sì, M porta lo script nella guida adesso». The script was tested on his two containers (LibreFolio, Home Assistant); on Home Assistant it restarted on a real `tailscale up` failure instead of hanging.
- **Script:** `mkdocs_src/docs/static/tailscale-guide/custom_startup.sh` replaced with the coordinator's 16:45 version (sha256 `2dd585bc…`; git mode `100644` kept). Diff reviewed: same variables, same socat proxy, funnel still in foreground mode (now supervised), plus the watchdog, explicit `TS_SOCKET`, `STARTUP_TIMEOUT` (180), `DEBUG=1`, a TERM trap and fail-fast required variables.
- **Compose** (`admin/service_exposure.{en,it,fr,es}.md`, both Tailscale blocks):
  - added `TS_ENABLE_HEALTH_CHECK=true`, `TS_LOCAL_ADDR_PORT=127.0.0.1:9002`, `STARTUP_TIMEOUT=180` (optional) and the `healthcheck` block (`wget … http://127.0.0.1:9002/healthz`, 30 s / 5 s / 3 retries / 120 s), with short comments written per language;
  - applied by `LibreFolio-cloud-sizing/release-images/tailscale/ts_compose_edit.py`;
  - check: all 8 blocks parse as YAML and are identical across languages once the localized placeholders are normalized (`compose_yaml_check.txt`).
- **EN prose** (docs-writer, not stamped):
  - the folded panel «Upgrading from an earlier version of the script» at the end of section 1. It uses `wget -O custom_startup.sh` because a plain `wget` would save `custom_startup.sh.1` next to the old file;
  - the watchdog and health-check bullets, and the note that plain Docker does not restart an unhealthy container (so no autoheal);
  - 4 parameter-table rows: `TS_ENABLE_HEALTH_CHECK`, `TS_LOCAL_ADDR_PORT`, `STARTUP_TIMEOUT`, `DEBUG`;
  - the folded troubleshooting note in section 3: the line right after `Running 'tailscale up'` above `USAGE`, `--flag=value` or `--flag value`, the CasaOS tip, the other causes, `DEBUG=1`;
  - an explicit `{: #3-startup-and-approval }` on the section 3 heading, the same slug, so translations keep the link.
- **Verified with the real binaries** (`tailscale/tailscale:latest` = 1.102.5, busybox 1.37, `--network none`; `release-images/tailscale/flag_forms.txt`):
  - the image has `CMD` containerboot and no entrypoint, so the guide's `command:` makes the script PID 1;
  - `tailscale up` accepts `--advertise-tags=tag:container` and `--advertise-tags tag:container`, and a bare `--advertise-tags` gives `flag needs an argument: -advertise-tags`;
  - the real containerboot splits `TS_EXTRA_ARGS` on spaces. With the truncated value it logs `Running 'tailscale up'` → the flag error → description → `USAGE` → `failed to auth tailscale: … exit status 2` and exits 1; with both value forms it keeps running;
  - containerboot starts tailscaled with `--socket=/tmp/tailscaled.sock`, the script's default.
  - Tailscale's docker-params page confirms `/healthz` (1.78+, 200 with a tailnet IP, else 503) and the `[::]:9002` default.
- **Watchdog scenarios** (`release-images/tailscale/ts_watchdog_scenarios.sh`, fake containerboot/tailscale/socat bind-mounted, no network): **8/8** in the real tailscale image and **8/8** in `alpine:3.20`, each checked on exit code and log message:
  - containerboot dies at boot → exit 1 in 3–4 s;
  - Running never reached (`STARTUP_TIMEOUT=6`) → exit 1 in 6 s;
  - funnel / containerboot / socat stop later → «X stopped.», exit 1 in 12–13 s;
  - `HOST_IP` missing → message, exit 2;
  - `docker stop` → exit 0 in 1 s;
  - healthy → stays running.
- **Before/after of the developer's bug** (`scenarios_before_after_hang.txt`), with containerboot dying at boot and `apk` available: the old script leaves the container **running after 21 s** in its `sleep 2` loop; the new one exits 1 in 4 s.
- **Checks:** `sh -n` OK (host and busybox); `mkdocs build` strict OK.
  - `check-links`: only the pre-existing `user/assets/detail/chart/#rolling-return` failure.
  - `translate-validate` for `service_exposure`: 0 → 18 errors / 33 warnings (it/fr/es): real debt, not stamped.
> **⚠️ Fuori pista**:
> - **The IT/FR/ES compose blocks were not identical to EN.** The translation pipeline had **flattened their YAML indentation** (`tailscale-librefolio:` and `image:` at the same level), so anyone copying the compose from the IT/FR/ES guide got invalid YAML. Lines correspond one to one, so each line got the EN line's indentation back while keeping its translated text and placeholders (e.g. `<ruta_elegida>`).
> - **The same defect is systemic:** 15 page/language pairs have code blocks whose relative indentation differs from EN, with otherwise identical code. YAML compose blocks are broken in `admin/docker_advanced` and `admin/service_exposure` (other blocks of this page: mermaid, JSON, text); also `user/assets/create-edit` and five technical-indicator pages. `translate-validate` does not detect it. Flagged to the coordinator for the pipeline; only the two Tailscale blocks were fixed here.
> - The first scenario run mounted the repo file as is (`100644`): `exec … permission denied`, and one verdict was a false pass. The harness now mirrors the guide's `chmod +x` and checks the log message of each scenario.
> - docs-writer briefly ran a local web server in `/tmp` to test `wget` overwrite behaviour, outside the lane ports. It was stopped and removed; no process of ours is listening.
### 7. ✅ Checkpoint handoff — 2026-10-06
- **Final checks:** `git diff --check` clean. The 5 product files the images were built from in the proof scratch are byte-identical to the worktree (sha256 in `evidence/proof_scratch.txt`). Ports 6158/6168 free; no `lf-m-*` container, volume or image; no server.
- **Cleanup:**
  - **removed:** proof images `lf-m-ri:{full,light,light-nogzip}`; the stage-test and O1-control images; today's build-cache records from these builds (20.61 → 17.99 GB; 4 shared 0-byte records of the re-pulled `python:3.13-slim` left); `/tmp/librefolio-r2-m-src/c77c7f09e-ri` (1.3 GB); `/tmp/librefolio-r2-m/ri` (347 MB); `/tmp/librefolio-r2-m/ri-test` (test data dir); temp logs (copied to `evidence/gate_*.log` first).
  - **kept:** `python:3.13-slim`, `alpine:3.20`; T2 scratch `/tmp/librefolio-r2-m-src/bff29231c` (`run_delta.sh`); `/tmp/librefolio-r2-m/snapshots`.
  - **in the worktree (gitignored):** `frontend/node_modules` (APFS clone), a debug `frontend/build`, `mkdocs_src/site`, `.testLog/`.
  - No CA exported, so there is no CA copy to delete.
- **Proposed commits:** `LibreFolio-cloud-sizing/release-images/commit_proposal.txt` (the coordinator stages and commits).
- **State: FROZEN.** Step 6 (Tailscale) waits for the coordinator.

### 8. ✅ Startup-timeout contract (the coordinator's «step 7») — 2026-10-06
- **Origin:** the pre-existing red found by step 3's `utils all` gate. The coordinator relayed it after integrating P0 (`dda56c9e1` → `810bab323`; `dev_release2` = `3d6f12eea` with the CHANGELOG), and assigned the fix, `playwright.config.ts`, `_server.py` and `test_runtime_isolation.py` to M.
- **`frontend/playwright.config.ts`:**
  - `STARTUP_TIMEOUT_RAW = process.env.LIBREFOLIO_TEST_STARTUP_TIMEOUT ?? '300'`, a guard that throws unless it is a whole number of seconds, and `STARTUP_TIMEOUT_S`;
  - `webServer.timeout` becomes `STARTUP_TIMEOUT_S * 1000` (was `process.env.CI ? 300 * 1000 : 120 * 1000`).
- **`scripts/test_runner/_server.py:43-48`:** comment only. The value `int(os.environ.get("LIBREFOLIO_TEST_STARTUP_TIMEOUT", "300"))` is unchanged and now cross-referenced.
- **Config evaluated for real** (esbuild bundle under `frontend/node_modules/.cache`, script `release-images/scripts/pwcfg_probe.mjs`): default 300000 ms, `CI=true` 300000, override 45 → 45000, `CI=true` + 600 → 600000, `abc` and `""` → throws. Python: 300 / 300 / 45.
- **Test (test-author):** `test_runtime_isolation.py:1282-1390` replaces the CI-parametrized test with:
  - `test_startup_timeout_ignores_ci_and_honours_the_override` (4 cases, fresh subprocesses);
  - `test_playwright_webserver_waits_exactly_as_long_as_the_runner`: static and Node-free; one env read, its default equal to the runner's (300), `webServer.timeout` = `S * 1000` found by brace depth, no `process.env.CI`;
  - `test_playwright_wait_check_rejects_a_drifted_config`: 6 in-memory drift controls, including the old ternary.
- **Gates** (lane 6158):

  | Selector | Before | After |
  |---|---|---|
  | `utils runtime-isolation` | red | 143/143 |
  | `--workers 4 utils all` | — | green, 827 passed, 0 failed |
  | `--no-shared-server front-utility utilities` (Playwright starts its own webServer: `[WebServer]` lines in the log) | — | 16 passed |
- Lint: prettier `--check` OK on the config; ruff OK; black clean on the test. `_server.py` already has pre-existing black drift at `:112-140`, not reformatted (comment-only edit).
> **⚠️ Fuori pista**:
> - The first E2E attempt stopped **before Playwright** with `no such table: users`. My step-7 cleanup had deleted the lane data dir `/tmp/librefolio-r2-m/ri-test`, and `--no-shared-server` runs create no schema. Fixed by `db create` + `db populate --force --with-reports` on the lane's own data dir, then the run passed. Infrastructure, not product.
> - `dev.py:396` still says "gallery/E2E 120s timeout" in a comment. `dev.py` is outside this step, so it is flagged only.
> - Overrides are not parsed identically, and this is not pinned. Python `int()` also accepts `+45`, `4_5` and `-5`, which the TS guard rejects; both reject `abc` and `""`.

### 9. ➡️ Translated code-block indentation (the coordinator's «passo 8») — 2026-10-06
- Analysis approved (B + C, ERROR `code-block-indent`, repair only of the pages the next alignment does not re-translate). Executed in [plan-phase00TranslatedCodeIndent.prompt.md](plan-phase00TranslatedCodeIndent.prompt.md).
