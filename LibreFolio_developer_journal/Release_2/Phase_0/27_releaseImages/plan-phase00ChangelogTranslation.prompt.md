# Plan — the CHANGELOG in Italian, French and Spanish (Release 2, workstream M, batch 25)

> Back: [plan-phase00TranslationRound12.prompt.md](plan-phase00TranslationRound12.prompt.md), step 16 («Next», item 5).
> Analysis: `release-pipeline/runs/b22/changelog_analysis.md` (M, 12/10), sent with batch 22's checkpoint.

## Brief

- The developer, through the coordinator, 12/10 (verbatim): «si ma fai anche la traduzione delle cose non ancora
  rilasciate, tanto stiamo rifinendo, ci fossero piccole aggiunte, andremo in append».
- The coordinator, 12/10: the pipeline as in the analysis — `CHANGELOG.{it,fr,es}.md`, the `## [x.y.z] - date` lines
  identical, one hash per chapter, [1.2.0] in pieces by `####`, `dev.py` untouched; **every chapter now, [1.2.0]
  included**; additions in append: for [1.2.0] one hash per piece, so a new line re-translates only its `####`; small
  additions may be ported by hand and stamped, as for the pages; in CI the open chapter is information only and becomes
  blocking with its tag; the contract with the frontend (a missing chapter shows in English, chapter by chapter, keyed
  by the version) goes to T (the frontend is T's, not I's: coordinator, later the same day); `CHANGELOG.md` is the
  coordinator's alone.
- Also in this batch: the gallery's `changelog-modal-search` shot (`frontend/e2e/gallery.spec.ts:1984`) searches
  `'Added'`, which the translated chapters will not contain: a word that stays the same in the four languages; and the
  it/fr/es of the sentence T adds to `user/settings/about.en.md` (§Changelog Modal), once T's batch is in.
- Coordinator, 12/10 16:0x: T changed `user/settings/about.en.md` (§Changelog Modal: the first sentence, and a new
  paragraph between the two lists on the modal in the UI's language), in train 60; its it/fr/es and the stamp are M's,
  once this branch is aligned to it. The app's label is `changelog.notTranslated`: «Not translated yet» / «Non ancora
  tradotto» / «Pas encore traduit» / «Aún sin traducir».

## Design

**Files.** `CHANGELOG.it.md`, `CHANGELOG.fr.md`, `CHANGELOG.es.md` beside `CHANGELOG.md`: the translated preamble, then
the chapters in the English order, each opened by its `## [x.y.z] - date` line byte for byte. A chapter not translated
yet is absent (never an English copy): the app shows the English one.

**Units and pieces** (`mkdocs_src/aphra-pipeline/changelog.py`, pure functions, no LLM):
- the preamble (before the first `## [`) is one unit, `CHANGELOG.md#preamble`;
- a chapter up to 30,000 characters is one piece, `CHANGELOG.md#<version>` (today [1.1.0] 26 KB, [1.0.1], [1.0.0]);
- a longer chapter (today [1.2.0], 74.5 KB) is cut at its `###` and `####` lines; a part that holds only its heading
  (`### 🐛 Fixed`) and the chapter's intro join the part that follows. Each piece is keyed by its headings' words,
  `CHANGELOG.md#1.2.0/fixed/documentation`: an added `####` does not shift the others. Today 20 pieces;
- the `## [x.y.z]` line is never sent to the model: it is copied.

**Cache.** One entry per piece in `.translate-hashes.json`, the same shape and the same transitions as a page (`md5` of
the piece's text, `langs_done`, `langs`), plus `langs.<lang>.index`, the piece's position in the translated chapter
when it was last written: the translated chapter is cut by the same rule, and the indexes say which translated part is
which piece, even after pieces were added, removed or moved in English.

**translate.** With no `--file`, or with `--file CHANGELOG.md`: a piece is translated when its md5 or its language is
not done, or when its translated part cannot be found. Each piece goes through the same steps as a page (analysis,
then translate, critique, refine per language), from a temporary `<piece>.en.md`, so the seams and their tests stay as
they are. A chapter is rewritten only when every piece of it has a translation (new or kept); otherwise the old one
stays and the failure is recorded.

**translate-stamp `--file CHANGELOG.md`.** For each language, each chapter present whose translated parts match the
English pieces in number: every piece stamped at its current md5, with its index. A chapter whose structure differs is
named and skipped.

**translate-validate and translate-diff.** With no `--file`, or with `--file CHANGELOG.md`: every chapter line of a
translation must be an English one, in the English order; each chapter present goes through the page checks; a
released chapter that is missing, stale (a piece changed since its translation) or wrong is an error; the open
chapter's findings are information only. Released: every chapter but the newest; the newest once its tag `v<version>`
exists in the repository or is the ref of the CI run (`GITHUB_REF`).

**Tests** (test-author): in the existing units `test_translation_cache.py` and `test_translation_validator.py` (no
runner registration); the cache sandbox points the changelog at `tmp_path`.

**Docs** (docs-writer): a «Changelog» section in `mkdocs_src/docs/developer/docs/translation-pipeline.md`.

## Steps

1. ✅ Plan, design (this file) — 2026-10-12 15:45.
2. ✅ `changelog.py`: split, pieces, keys, the translated file's parts, assembly, the release policy — 2026-10-12.
   > **Note implementazione**: pure module beside `translate_docs.py`. The preamble and every chapter are units; the `---`
   > that closes a unit and the chapter line are structure (copied, never translated). Today: preamble 249 characters,
   > [1.2.0] 74,510 → 21 pieces (`intro`, `added`, `fixed/security` … `fixed/documentation`, `changed`,
   > `changed/purchase-cost-and-p-l` …, `breaking-changes`), [1.1.0] 26,120, [1.0.1] 1,485, [1.0.0] 3,401 one piece each.
   > Assembling the English pieces gives back `CHANGELOG.md` byte for byte (0 diff lines); cutting the assembled text
   > again finds the 21 pieces.
   > - **⚠️ Fuori pista — the intro is a piece of its own**: the analysis had it join the next part; [1.2.0]'s intro
   >   («Preparing v1.2.0…», 102 characters) is the part most likely to change before the release, and joined to
   >   «✨ Added» (16,801 characters) every touch would re-translate both. Only a part that is its heading alone joins the
   >   next one (`### 🐛 Fixed` → `fixed/security`).
3. ✅ `translate_docs.py`: translate (plan, dry-run, run, assembly), stamp; `validate_translations.py` and
   `translate-diff`: the changelog checks and the policy — 2026-10-12.
   > **Note implementazione**: `run_translate` = the pages (`_run_translate_pages`, the former body, unchanged) then
   > `_run_translate_changelog`; the CHANGELOG is in scope with no `--file`, or with `--file CHANGELOG.md`. Its path is
   > `DOCS_DIR.parent.parent / "CHANGELOG.md"`, read at call time: the tests' sandboxes, which point `DOCS_DIR` at
   > `tmp_path`, never see the repository's file (verified: the four pipeline units green, 38/130/80/60, no
   > `CHANGELOG.*.md` written). A piece goes through `_analyze_source` and `_translate_one_lang` from a temporary
   > `piece-NNN.en.md`, so the seams and the tests that hold the fakes to them are unchanged. `translate-stamp --file
   > CHANGELOG.md` (never by default); `translate-diff` and `translate-validate` include the CHANGELOG with no `--file`
   > (CI) and report the open chapter as ℹ️ information. `validate_file` keeps its signature over a new `validate_text`.
   > - Dry-run on the real file: 25 pieces × 3 = 75 translations, ~1.05M tokens (in ~828K, out ~223K).
   > - Smoke test with a fake model in a temporary tree (`release-pipeline/scripts/b25_smoke.py`, 17 checks, all pass):
   >   first run 75 calls and the chapter lines identical; second run nothing; one line added to `#### 📚 Documentation`
   >   → only that piece ×3, `translate-validate` still 0 (open chapter); a new `####` → only it; a hand port + stamp →
   >   3 pieces stamped, nothing left; a released chapter edited → `changelog-stale` error.
4. ✅ Tests (test-author), the gallery word (test-author), the developer doc (docs-writer) — 2026-10-12 17:00.
   > **Note implementazione**: docs-writer wrote `## 📜 The CHANGELOG {: #changelog }` in
   > `mkdocs_src/docs/developer/docs/translation-pipeline.md` (five sub-sections: pieces, cache, commands, the open
   > chapter with a findings table, adding a line), and fixed three stale spots of the page (the «Architecture» tree now
   > lists `changelog.py` and `page_anchors.py`; the «Overview» names the CHANGELOG; the sub-command list has all six);
   > `check-links` clean. Its review found two code issues, fixed by M: `translate-diff` decided the open chapter
   > without the empty chapters (an empty newest chapter would make the two commands disagree) — `released()` now always
   > gets every unit; and `_tag_exists` accepted only `v<version>` while the release workflow's guard also accepts
   > `<version>` — both forms now. test-author wrote the tests (not run during the translation: their autouse guard
   > watches the tracked cache and `config.toml`, which the run changes) and found three defects and a risk, all fixed
   > by M: (A) `part_ids` read headings inside fenced code; (B) a section removed from the English, with nothing else
   > changed, left the translations behind — an empty plan now rebuilds the outdated files from the parts found, with no
   > model call (`_changelog_rebuild`), and `_changelog_write` writes a file only when its text changes; (C) the
   > open-chapter disagreement above; (D) a new translation of a piece of a cut chapter that does not cut back into one
   > part (the model added or dropped a heading) is refused as failed, so the indexes never drift from the file.
   > - **Run** (M's lane, one command at a time): `--fresh-run utils translation-cache` 80 passed and 1 failed;
   >   `utils translation-validator` 174 passed; `--workers 4 utils all` 1,821 passed and the same 1 failed;
   >   `check-orphans` clean for the backend. The guard stayed green with the real `CHANGELOG.{it,fr,es}.md` present.
   > - **⚠️ Fuori pista — fix D had a second door**: `test_a_new_translation_that_drops_the_heading_its_piece_opens_with_is_refused_too`.
   >   A translation that loses its opening `####` is one part on its own, so D accepted it; in the chapter it merges into
   >   the part before it: exit 0, then every later run plans the whole chapter again in that language. Fixed by M in two
   >   layers: `changelog.structure_change` (one part, *and* a heading at the start exactly when the English piece opens
   >   with one), and `translate_docs._changelog_misfits`, a check on the whole chapter before each write that catches a
   >   break at a seam, such as a code fence left open (that chapter's new pieces in that language are refused, and the
   >   chapter keeps its text). test-author added a pure test of `structure_change` [6 cases] and the seam case end to
   >   end: `translation-cache` 88/88, `translation-validator` 174/174; black leaves both files unchanged; `dev.py lint`
   >   clean.
   > - The gallery word: `CHANGELOG_SEARCH_TERM = 'Docker'` in `frontend/e2e/gallery.spec.ts` (Prettier clean).
5. ✅ Dry-run on the real CHANGELOG: pieces and estimate; then the run (it, fr, es) — 2026-10-12 15:55–16:34.
   > **Note implementazione**: `dev.py mkdocs translate --file CHANGELOG.md --workers 6` (Doubleword flex queue,
   > `deepseek-ai/DeepSeek-V4.1-Flash`): 25 pieces × 3 = 75 translations, 0 failed, 38 min 59 s, estimate ~1.05M tokens;
   > `CHANGELOG.{it,fr,es}.md` with 5 units each (preamble, 1.2.0, 1.1.0, 1.0.1, 1.0.0), chapter lines identical; the
   > post-step reported no structural issue. Then `translate-validate` 0/0, `translate-diff` 642/642 (627 pages + 15
   > chapters), dry-run «nothing to translate». The branch had been fast-forwarded to `094c92b99` (train 59, with its
   > two CHANGELOG lines) at 15:42, before the run: the run read that English. Log `release-pipeline/runs/b25/b25_translate.log`
   > (12 «sk-» matches, all the piece key `risk-analysis…`; no key).
6. ✅ Review of the output (labels against the catalogues, the glossary, the structure); hand fixes; stamp — 2026-10-12 17:02.
   > **Note implementazione** (after the fast-forward to `bd8ee8e4d`, train 61: T's frontend and
   > `about.en.md`, U-1; `CHANGELOG.md` unchanged, the dry-run still empty for it): `release-pipeline/scripts/b25_changelog_review.py`
   > (bold spans paired piece by piece against the UI catalogues; batch 11's glossary rules; English lines left). First
   > pass: 21 labels differing, 17 glossary hits, 5 pieces with unequal bold counts, 0 English lines. Fixed by
   > `scripts/b25_changelog_fixes.py` (28 replacements, counts asserted, no heading touched, so the cache stays valid):
   > the buttons as the catalogues write them (`sharedResource.syncSelection` «Sinc. selezione» / «Sync. sélection» /
   > «Sinc. selección», `syncAll`, `refreshAll` «Recharger Tout», `support.copyAndGo` «Copier et ouvrir» / «Copiar y
   > abrir», `importWizard.step3Title` «Analizza» / «Analizar» for an English «Parse» left in it and es,
   > `importWizard.reportSet.readAs` «Letto come» / «Lu comme» / «Leído como», `settings.defaultCurrency` es «Divisa
   > predeterminada», the data-quality banner's `dataQuality.cta.sync_fx_pair` «Sincronizza» / «Synchroniser» /
   > «Sincronizar» for its three «Sync rates»); es «tasa» → «tipo de cambio» where it is an exchange rate (2) and «límite de
   > tasa» → «límite de solicitudes»; a fr bold the English does not have («**Analyser**») and fr italics nested in a
   > bold title removed; the 1.1.0 title on `except: pass` rewritten in the three languages. Second pass: 0 labels
   > differing; the 14 glossary hits left are right in context (fr «aperçu» = preview ×7, the old words quoted by the
   > entry that changes them, es «tasa libre de riesgo»); 3 unequal bold counts left, all the 1.1.0 title whose bold now
   > ends with code (the scanner blanks code: an artefact, as in batch 22).
   > - T's `user/settings/about.en.md` (§Changelog Modal) ported to it/fr/es: the first sentence (the modal shows the
   >   bundled changelog in the interface language) and the new paragraph between the two lists, with the app's label
   >   (`changelog.notTranslated`). Stamped once the tests were over (the stamp writes the tracked cache their guard
   >   watches): `translate-stamp --file user/settings/about.en.md`, it/fr/es. Then `translate --dry-run`: «Nothing to
   >   translate» for the pages, «nothing to translate» for the CHANGELOG.
7. ✅ The widened M-19 line. The coordinator wrote the new ending in English («online, every one of those pages called
   a third-party server», `e9bc300f0`). After the fast-forward, M ported that piece by hand into it/fr/es, then ran
   `translate-stamp --file CHANGELOG.md` — 2026-10-12 17:33.
   > **Note implementazione**: the coordinator fast-forwarded the branch to `0afac8e14` (train 64), with 103 files and
   > no overlap with M's dirty paths but one: `BACKLOG_POST_1.2.md`. The target had added its own hunks, and V's 67
   > lines in section V, above and below section M. Git refuses a fast-forward over a locally modified file it changes,
   > so M resolved it with no Git write:
   > - M's version saved outside the repo (`release-pipeline/b25_backlog/`);
   > - the worktree file set back to HEAD's content; the fast-forward;
   > - `git merge-file -p` on copies (base = old HEAD, mine, new HEAD): clean. It is checked that M's 19 lines are
   >   exactly the merged file's difference from the new HEAD, and the target's hunks exactly its difference from M's.
   >
   > The port (`release-pipeline/scripts/b25_m19_line_port.py`) replaces only the words that changed, asserting one
   > occurrence each: it «ognuna di quelle pagine», fr «chacune de ces pages», es «cada una de esas páginas». The
   > dry-run then planned exactly `CHANGELOG.md#1.2.0/fixed/documentation` ×3, which is the append path working. The
   > stamp marked those 3, and the next dry-run said «nothing to translate» for the pages and the CHANGELOG.
   > - **⚠️ Fuori pista — the stamp printed a moved md5**: for fr and es it showed `c067b072→c067b072`, the md5 the
   >   first language had just written. `_stamp_changelog` now keeps each piece's md5 from before the run for the
   >   message. Only the output changed; the tests match the line up to `(MD5 `.
8. ✅ M-19 follow-up, by the coordinator's decisions (2026-10-12 17:03): MathJax's fonts, `typesetPromise`, M-22 —
   2026-10-12 17:33.
   > **Note implementazione**:
   > - **Found** by the test-author writing the M-19 spec. **Proven** by M in a browser
   >   (`release-pipeline/scripts/b25_mathjax_fonts_probe.cjs`: Playwright on `financial-theory/fundamentals/day-count/`,
   >   with the built site served on 6168).
   >   - With the local copy, the 4 formulas drew, but `MJXZERO`, `MJXTEX` and `MJXTEX-I` ended in `error` (404 on
   >     `vendor/mathjax/output/chtml/fonts/woff-v2/MathJax_*.woff`): the letters were upright and the fraction clipped.
   >   - Through jsDelivr, with the local copy refused, the same faces were `loaded`.
   >   - GitHub Pages (1.1.0) serves `tex-mml-chtml.js` (200) without its fonts (404). Before M-19, nested pages fell back
   >     to the CDN. M-19 alone would have shipped degraded formulas in 1.2, in the image and on the public site.
   > - **`scripts/update_js_cache.py`** (assigned to M for this batch): a js library's `companions`.
   >   - The names come from the cached script (`MathJax_[A-Za-z0-9-]+\.woff`, 22 files) and the address from the
   >     library's URL (`…/es5/output/chtml/fonts/woff-v2/`). The files go under `vendor/mathjax/output/chtml/fonts/woff-v2/`.
   >   - They are checked on every run, even when the script's ETag matches (the JS path returns early there), and
   >     downloaded again when the script changes.
   >   - A file that fails keeps its cached copy; without one, it is a hard failure for the `mkdocs` consumer, as the
   >     script is. A 200 that is not a font (no `wOFF`) is refused. Files the script no longer names are removed.
   >   - `dev.py cache js`, run twice: the first run wrote 22 files (321 KB) with the script up to date; the second said
   >     «Companions up-to-date».
   > - **`mathjax.js`** calls `MathJax.typesetPromise()` only once it exists. Material's `document$` fires before
   >   lib-loader has loaded MathJax, which threw a `TypeError` on every page. There is no `navigation.instant`, so the
   >   call never did anything anyway.
   > - **After `dev.py mkdocs build`** (74 s, all 3012 asset URLs resolve), the site has the 22 fonts. The probe:
   >   - the 3 faces are `loaded`, and the fonts answer 200 from the local path;
   >   - 0 `typesetPromise` errors;
   >   - the formula is drawn as through the CDN (`runs/b25/b25_mathjax_{local,cdn}_{before,after}.png`).
   > - **The image and the published site.**
   >   - The Dockerfile copies `mkdocs_src/site/` whole; `.dockerignore` excludes only the docs sources, and the light
   >     variant deletes only gallery images.
   >   - `release.yml` runs `dev.py front build`, which calls `update_js_cache`, then `dev.py mkdocs build` before the
   >     images, and `mkdocs deploy` (gh-deploy builds from `docs/`).
   >   - So the fonts follow the script. A local `dev.py docker build` on an already-built site does not take them
   >     without `dev.py mkdocs build`: that is M-21, which now names the vendor files too.
   > - **M-22** (Mermaid draws only with internet): filed in section M of the backlog, for after 1.2.
   > - **Tests**:
   >   - test-author added `TestCompanions` to `test_update_js_cache.py`: 32 cases. `utils js-cache-fail-loud` gives
   >     63 passed (31 before); black leaves the file unchanged, and `dev.py lint` is clean. Breaking the code 12
   >     ways in memory turned each break red, including the defect itself (companions fetched only after a script
   >     download).
   >   - **⚠️ Fuori pista — three edge cases in the new code**, found by test-author and unreachable with today's
   >     config, fixed by M with a test each:
   >     - the stale-file cleanup removed any unnamed file in the target folder (with `dir: "."`, the script itself):
   >       it now removes only files the pattern matches;
   >     - an empty `dir` pointed at the host's root: `""` and `"."` now mean the script's own folder;
   >     - with no record and no `current_hash` (a lost manifest), the files on disk were trusted: a missing record
   >       now means everything is downloaded once.
   >   - The M-19 spec gained the checks on the font answers (at least one, each a 200 under the copy's
   >     `output/chtml/fonts/woff-v2/`), on the MJX faces (none in `error`, at least one `loaded`, after
   >     `document.fonts.ready`), and on `typesetPromise` (no page error naming it). It is now 225 lines; Prettier and
   >     a strict `tsc` on the file are clean. It is parked outside the repo (`release-pipeline/pending/`) until T's
   >     CP1 frees `_frontend_utility.py`, because an unregistered spec turns `check-orphans` red (it returns 1).
   > - **Lint outside the gate.** `dev.py lint` covers `backend/` only, so ruff ran read-only, with the project's
   >   config, on the four changed product files, compared with their HEAD versions. Two new findings were fixed:
   >   3 `zip()` calls in `changelog.py` now pass `strict=True` (equal lengths by construction), and the
   >   `validate_translations.py` import block is sorted. The rest follows each file's style (complexity,
   >   `timezone.utc`, local imports), where 41 kinds of finding were already there.
   > - **⚠️ Fuori pista — node broken on the host, 17:17–17:26** (the developer's `brew upgrade`; coordinator's stop at
   >   17:23). No command of M's failed. The Prettier step left the gates and came back, and the spec's run in M's
   >   lane moved after the fast-forward.
9. ✅ Gates, checkpoint — 2026-10-12 17:50.
   > **Note implementazione** (base `0afac8e14`, train 64; script `release-pipeline/scripts/b25_final_gates.sh`, logs
   > `runs/b25/b25_final_*`, the machine's load beside each step, 65–148):
   > - `--workers 4 utils all`: 32 units, 1,861 passed, 0 failed (121 s). That is the run before plus the reds fixed
   >   and 39 new cases.
   > - `check-orphans` clean: backend, 109 e2e specs, 347 unit tests.
   > - `translate-validate --hide-localized`: 630 files, 0/0. `translate-diff --issues-only`: 642 of 642 clean.
   > - `translate-check` exit 0 (log redacted: 0 key-like strings); dry-run «nothing to translate» for the pages and
   >   the CHANGELOG.
   > - Strict build 0 (all 3,012 relative asset URLs resolve); `check-links` 95 valid; `git diff --check` clean.
   > - The batch scans (assets, masked, coverage, copied, glossary, labels, usted, hook, stamp audit, stamp port) all
   >   exit 0.
   > - Prettier on `gallery.spec.ts` is clean, run from `frontend/`.
   >   - **⚠️ Fuori pista**: the gate first ran it from the repository root, where Prettier does not find
   >     `prettier-plugin-svelte` (exit 1 in 0 s, a tool failure, not a format finding). The script is fixed.
   > - **The M-19 spec, once, in M's lane, unregistered**: `release-pipeline/scripts/b25_run_offline_math_spec.py`
   >   calls what the proposed `front_docs_offline_math` would call, inside the runner's lane
   >   (`configure_test_runtime`, 6158, `/tmp/librefolio-r2-m`) and its `SharedTestServer`.
   >   - The runner's `_ensure_db_populated` repopulated the lane's database, as every front unit does.
   >   - 2 passed: English 1.2 s, Italian 0.7 s.
   >   - **Negative control**: with the site's `vendor/mathjax/output/` renamed away, both fail on the font assertion
   >     with its message («a 404 there is a font the site does not have: ./dev.py cache js, then ./dev.py mkdocs
   >     build»). The folder was restored (22 fonts) and the spec parked again; 6158 and 6168 are free.
10. ✅ The first append, batch 26 — 2026-10-12 18:00. Committed: batch 25 is `2aecd5a6f`…`81e221f4e` (tree
    `8c50c8df95eb`), train 66; the branch fast-forwarded to `b91d6d902`, which adds one line to [1.2.0] → ✨ Added,
    after «Connection security in the sidebar»: «**The changelog speaks your language.** …, marked “Not translated
    yet”.»
    > **Note implementazione**: the dry-run planned `CHANGELOG.md#1.2.0/added` ×3, ~50.4K tokens each. A model run
    > would also re-translate the whole 16.8 KB piece over its hand review (batch 25, step 6). So the line was ported by
    > hand instead (`release-pipeline/scripts/b26_changelog_line_port.py`), inserted after the translated
    > connection-security bullet with one occurrence asserted. The label is read from `changelog.notTranslated` in each
    > catalogue: «Non ancora tradotto», «Pas encore traduit», «Aún sin traducir». Each file keeps its own words and
    > marks:
    > - it: «il changelog» (as `about.it.md` and the other lines), «l'app», “…”;
    > - fr: «journal des modifications», «l'application», « … » with plain spaces, as the whole file has them;
    > - es: «registro de cambios», «la aplicación», «…», tú.
    >
    > Then:
    > - `translate-stamp --file CHANGELOG.md` stamped `1.2.0/added` ×3, and the next dry-run was empty (pages and
    >   CHANGELOG);
    > - `translate-validate` 630 files 0/0, `translate-diff` 642/642 clean, `git diff --check` clean;
    > - the review scan (`b26_changelog_review.py`) matches batch 25's last pass: 0 labels differing, the same 14
    >   legitimate glossary hits, the same 3 bold-count artefacts in 1.1.0.
    >
    > U's two unit descriptions for `_backend_utils.py` (`translation-cache`, `translation-validator`) were checked
    > against the tests and the code at the coordinator's request: ok, sent to U.
    > - **⚠️ Fuori pista — French spacing in the app's changelog (M-23)**: `mkdocs_src/hooks/fr_typography.py` puts the
    >   no-break spaces into French pages at build time («the sources never change»), and the translations keep plain
    >   spaces. The in-app modal renders `CHANGELOG.fr.md` without MkDocs (`frontend/src/lib/features/changelog/changelog.ts`
    >   applies no such rule), so a line there can break before `;` `:` `?` `!` `%` or inside « ». The same rules belong
    >   in the modal's renderer, for French. That is outside M's scope; filed as M-23.
