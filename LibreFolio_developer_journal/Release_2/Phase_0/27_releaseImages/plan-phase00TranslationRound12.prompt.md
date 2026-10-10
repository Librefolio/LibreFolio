# 🌍 Release 1.2 translation round (workstream M, batch 11)

> Back to: [plan-phase00ReleaseGallery.prompt.md](plan-phase00ReleaseGallery.prompt.md) (batch 11 → step 24). Earlier alignment analysis: R12 §2 (`release-pipeline/r12_analysis.md`, 07/10) and [plan-phase00TranslatedCodeIndent.prompt.md](plan-phase00TranslatedCodeIndent.prompt.md).

## Brief

**Developer** (via the coordinator, 10/10 00:26), verbatim: «arrivati a questo punto credo potrebbe avere senso avviare la pipeline di traduzione, ma per farlo vorrei che avviassi o usassi un agente apposito, eso deve prima guardare, come spiega la skill tutto quello che c'è da tradurre, gli errori, le discrepanze e così via, le piccole modifiche puntuali risolverle, e poi avviare la pipeline per quelle grandi, al termine poi rifare il trial e finire di risolvere. l'avvio della pipeline però lo voglio fare io, puoi predisporre per arrivare all'avvio della pipeline?»

**Coordinator's brief:**
- Phase 1, triage:
  - run `translate-validate --hide-localized`, `translate-diff --issues-only` and `translate --dry-run`;
  - classify every page from its EN diff since the last stamp, into a table with page, languages, type, small or large, and evidence;
  - cover the I-08 notes.
- Phase 2, the small fixes:
  - targeted edits in it/fr/es, then `translate-stamp`, then `mkdocs build` strict with no new WARNING or ERROR;
  - **checkpoint A**, as separate commits, then FROZEN.
- Phase 3, preparing the launch: the exact list of pages and languages, the file count and token estimate, the configuration needed, and the full command. **The developer launches it.**
- Phase 4, after the pipeline: validate and diff again, fix the residues, stamp, `mkdocs build` strict and `check-links`, then **checkpoint B**.
- Rules:
  - the translations and `.translate-hashes.json` are M's until the round ends;
  - EN pages are not rewritten; an EN error is reported to the coordinator;
  - outside this round: S's pages (Scalable, import, Bulk, BRIM guide) and the possible P&L-per-broker correction;
  - no servers, no tests.

**Additions:**
- **Glossary** (developer, verbatim: «forse bisogna aggiornare il mkdocs_src/aphra-pipeline/glossaries/glossary.json per quando avviamo le traduzioni, ora che è cresciuto tanto il progetto»):
  - it/fr/es are taken from the UI catalogues; terms the UI lacks are M's proposals, marked as such;
  - the 58 existing terms are checked (e.g. «live ticker» → «Live Prices», WAC);
  - the list of terms added and changed goes to the developer before the launch;
  - a separate commit in checkpoint A.
- **Model** (developer, verbatim: «di ad M di impostare per la pipeline aphra il modello deepseek-ai/DeepSeek-V4.1-Flash se non è già impostato»):
  - a worktree `.env` (ignored by git) with only the non-secret lines (Doubleword, `APHRA_MODEL` and `APHRA_CRITIQUER` = `deepseek-ai/DeepSeek-V4.1-Flash`, `APHRA_WEB_SEARCH=false`);
  - the key is added by the developer;
  - a command that checks the model exists on Doubleword;
  - optional: `.env.example` (the Doubleword example on V4.1, comments in English).

## Steps

### 1. ✅ Phase 1: triage — 2026-10-10

> - **Baseline:** HEAD `fbb57eb41`, tree `eb2090da4488` (= the expected one); worktree clean.
> - **Detectors** (read-only; the worktree status before and after is identical):
>   - `translate-validate --hide-localized`: 549 files, 72 missing, **2,126 errors**, 2,276 warnings (`runs/b11_validate.log`);
>   - `translate-diff --issues-only`: 270 files with **2,253 anomalies**, 72 missing (`runs/b11_diff.log`);
>   - `translate --dry-run`: **133 files × 3 = 399 translations, about 9.7 M tokens** (7.5 M in, 2.2 M out; `runs/b11_dryrun.log`).
> - **M's triage** (`release-pipeline/scripts/b11_translation_triage.py`, `runs/b11_triage/triage.json`, the diffs in `runs/b11_triage/diffs/`):
>   - for each stale page, the EN base the translation was made from: the newest commit whose blob md5 equals the cached md5;
>   - then the diff base..HEAD and the list of commits.
> - The 207 nav pages make 621 pairs: 222 fresh, 327 stale, 72 new (missing). **The fresh pairs have no issues**: every detector finding is among the 133 pages to align.
> - **Classification** (`runs/b11_triage_table.md`):
>
> | class | pages | pairs | estimated tokens |
> |---|---|---|---|
> | small: by hand in it/fr/es, then stamp | 28 | 84 | 0.94 M saved |
> | large: pipeline | 94 | 282 | 8.04 M |
> | on hold: S? (`user/transactions/import/**`) | 11 | 33 | 0.73 M |
>
> - **Small pages:**
>   - the 20 indicator pages: «days» → «sessions», the «Drawn across closed days» notes and the sessions paragraph in the index;
>   - `community/contribute`, `asset-types/etfs`, `gallery/index`, `portfolio-engine/deposited-capital`, `user/index`, `fx/providers/ecb`, `performance-metrics/index`;
>   - `user/settings/profile`, urgent (L).
>   - Every validate error on these pages is explained by their EN diff.
> - **I-08 notes:**
>   - `#rolling-return` is already explicit in EN (`chart.en.md:22`); `chart` is large and goes to the pipeline.
>   - The 3 `check-links` exceptions are already explicit anchors in EN too: `scheduled-investment` (`#how-value-is-calculated`, `#interest-schedule-editor`) and `create-edit#importing-a-distribution-csv`. After the pipeline, check the anchors in the 4 languages.
>   - `docker_advanced` is large (pipeline); `user/tools/*` are new pages (pipeline).
> - **Questions to the coordinator:** S's exact page list (are `user/brokers/import`, `user/transactions/{index,form}` S's?); which page the P&L-per-broker correction touches.
> - **Launch preparation:**
>   - worktree `.env` created, 4 non-secret lines: Doubleword mode, all 4 roles on `deepseek-ai/DeepSeek-V4.1-Flash`, web search off, no key;
>   - model check: `release-pipeline/scripts/b11_check_doubleword_model.{sh,py}`. The key goes from the file to curl via stdin (`-H @-`), never on screen or in argv; exit 0 if `APHRA_MODEL` exists, 2 if not; the parser tested on fake answers.
> - Phase 1 report sent to the coordinator (00:45).

### 2. ✅ Phase 2: the small fixes, the glossary, `.env.example` — 2026-10-10 (checkpoint A)

> **Coordinator's answers** (01:05):
> 1. S's pages = only `user/transactions/import/how-to`, `user/transactions/import/index`, `user/transactions/index` (plus the new `scalable`, not in the target). The other 9 under `import/` (danske-bank included, L's), `user/brokers/import` and `user/transactions/form` go to the pipeline.
> 2. P&L per broker: on hold, nothing to exclude; if a text changes (probably the line table of `user/dashboard/charts`), it gets fixed by hand in the second round.
> - **Train:** checkpoint A goes into train 29 with P's folder-40 archive; the glossary list is shown to the developer before that batch; afterwards the worktree advances and the developer launches the pipeline there.
>
> **2.1 ⚠️ Off track: small pages that depend on anchors still untranslated** (`release-pipeline/scripts/b11_anchor_check.py`, M, 01:10)
> - A link to `page.md#anchor` from an it/fr/es page lands on `page.<lang>.md`; if that translation is stale and lacks the anchor, `mkdocs build --strict` fails (`validation.anchors: warn`).
> - Four small pages link to anchors that only the pipeline will bring:
>   - `community/contribute` → `user/settings/about#support-librefolio`;
>   - `asset-types/etfs` → `asset-types/index#etf-family`;
>   - `indicators/index` → `user/assets/detail/chart#primary-modes`;
>   - `user/settings/profile` → `getting-started#welcome-setup`.
>   - The EN anchors are all explicit (`{: #… }`).
> - **Decision (M):** these four are fixed by hand **after the pipeline** (phase 4), stamped then, and **left out of the pipeline's file list** (`--file`).
>   - **`profile` is split:** the urgent part (account deletion with the last-Owner rule) is done now, not stamped; the «Also settable from the Welcome page» note with its link comes in phase 4, then the stamp.
>
> **Final classification after the answers:**
>
> | class | pages |
> |---|---|
> | small, done and stamped in phase 2 | **25** (19 indicators, `gallery/index`, `deposited-capital`, `user/index`, `fx/providers/ecb`, `performance-metrics/index`, `import/directa`) |
> | small, partial now (not stamped) | 1 (`user/settings/profile`: deletion) |
> | small, after the pipeline | 3 (`contribute`, `asset-types/etfs`, `indicators/index`) + the `profile` note |
> | pipeline | **101** (the 94 large − `user/transactions/index` + 8 under `import/`, danske-bank included) |
> | on hold (S) | 3 (`import/how-to`, `import/index`, `transactions/index`) |
>
> **2.2 ✅ The small fixes** (M, 01:20; `release-pipeline/scripts/b11_small_fixes.py`: 150 edits on 78 files, each matching once, checked with `--check` before writing)
> - **Indicators:**
>   - «days» → sessions, following the UI's terms (`signals.units.sessions`): it «sedute», fr «séances», es «sesiones»; in the parameter tables, the RSI/OBV/EMA/SMA/trend prose, the ADX formula and ROC in momentum;
>   - the «Drawn across closed days» notes in Bollinger and Donchian, «middle band/line» following each page (it «banda centrale»/«punto medio», fr «bande centrale»/«ligne médiane», es «banda media»/«línea media»).
>   - **Pre-existing mistranslation fixed:** `aroon.es` «Ventana obsoleta» → «Ventana retrospectiva» (a «Lookback window» translated as «stale», probably the glossary's `stale → obsoleto` applied out of context).
>   - FR: two lines with narrow no-break spaces (U+202F, `sma.fr`, `trend.fr`) kept as they were.
> - **`gallery/index`:** Security, Onboarding (UI: «Primo utilizzo» / «Prise en main» / «Introducción»), Risk analysis, Tools. Terms from the UI: `onboarding.*`, `risk.replay.title`, `tools.pacAllocator.name`.
> - **`deposited-capital`:** the 3-step list → 2 steps (cost at historical rates).
> - **`user/index`:** the «A header that makes room» tip, plus the Tools bullet (wording from `tools.pacAllocator.description`). ES keeps the page's «usted».
> - **`fx/providers/ecb`:** about 30 currencies, ISK in, BGN out, the paragraph on discontinued currencies.
> - **`performance-metrics/index`:**
>   - the Yield on Cost row («Rendimento sul costo» / «Rendement sur coût» / «Rendimiento sobre coste», `dashboard.yieldOnCostValue`);
>   - section 9, the WAC row at historical rates, and the YOC link in the closing sentence.
>   - The WAC acronym follows the page (PMC/PMP) until the glossary decision.
> - **`import/directa`:** the Beta notice removed.
> - **`user/settings/profile`** (partial): deletion of the account and its settings; the last-Owner rule (link to `brokers/sharing.md`); the failed-deletion sentence; the warning without «your brokers… are removed». Roles from `brokers.sharing.roleOwnerShort`.
> - **Checks:**
>   - `translate-validate --hide-localized` on the 26 pages: 0 errors except `profile` (9: the deferred note, expected);
>   - `translate-diff --issues-only`: 75/78 clean, 3 = `profile`;
>   - `git diff --check` clean.
> - **Stamp:** `translate-stamp` of the 25 (not `profile`; `runs/b11_stamp_A.log`). Then `translate --dry-run` on the same: «All files are up-to-date».
> - **`mkdocs build` (strict): exit 0, 0 WARNING/ERROR**, 43 s (`runs/b11_build_A1.log`).
>
> **2.3 ✅ `.env.example`** (M, 01:25): the Doubleword section is in English, with the example on `deepseek-ai/DeepSeek-V4.1-Flash`, the roles following `APHRA_MODEL`, and the advice to check the id with `GET /v1/models`; the queue-timeout and parallel-languages sections are in English too.
>
> **Developer to M** (directly, 00:57), verbatim: «riguado il .env di aphra, se ti serve chiedi al coordinatore di copiarlo nel tuo worktree, ok aggiornare l'example, ma ti servono anche gli altri dati».
> - The coordinator (00:59), on the developer's authorisation, **added only the missing variable**, `DOUBLEWORD_API_KEY`, without printing it.
> - Names now: `APHRA_BASE_URL APHRA_MODEL APHRA_CRITIQUER APHRA_WEB_SEARCH DOUBLEWORD_API_KEY`; M's 4 lines unchanged; permissions 600, ignored by git.
>
> **2.4 ✅ Model and configuration check** (M, 01:35)
> - `b11_check_doubleword_model.sh`: **36 models on Doubleword; the only id with «V4.1» is `deepseek-ai/DeepSeek-V4.1-Flash`, which is present** (exit 0, `runs/b11_model_check.log`).
> - `translate-check` (`runs/b11_translate_check.log`, with the masked-key line filtered out): Aphra importable, Doubleword with its key, model `deepseek-ai/DeepSeek-V4.1-Flash` (from `.env`), web search off, it/fr/es, 207 files, cache 200/200, **Doubleword connection OK**.
> - **Pipeline list** (`runs/b11_pipeline_files.txt`): 101 pages; `translate --dry-run --file …` gives **101 files × 3 = 303 translations, about 8.37 M tokens** (6.45 M in, 1.92 M out; `runs/b11_pipeline_dryrun.log`).
>
> **2.5 ✅ Glossary: proposal ready, waiting for the developer** (read-only agent + M, 01:40)
> - Files: `release-pipeline/runs/b11_glossary_proposal.md` (table with term, it/fr/es, status, UI key, note; conflicts with the translated docs; 16 questions) and `b11_glossary_candidate.json` (170 terms, same format, `_meta` unchanged).
> - Of the 58 terms: 38 kept, **14 changed**, 6 with no use in the EN docs, kept for now. **112 added** (25 accounting, 2 session, 34 risk, 22 PAC, 9 import, 3 privacy, 5 connection, 6 onboarding, 6 UI). **10 are M's proposals** (the UI has no such string): book value, conditional drawdown at risk, worst realization, Sortino ratio, target weight, import wizard, todo banner, data-quality banner, privacy mode, connection security indicator.
> - **How the glossary is used:** `_load_glossary()` renders every term; the block reaches only the Critique and Refine prompts (`step4_user.txt`, `step5_user.txt`), not the first translation. Hence the multi-word terms and the sense tags (`session (login)`, `split (corporate action)`). The block per language goes from about 1.7k to 5.6k characters.
> - **For the developer** (sent to the coordinator, 01:45):
>   - WAC in FR/ES: the UI has «CMP» in the transaction form and «PRU»/«PMC» in the newer screens; «PMP» is in no UI string. The candidate uses PRU/PMC.
>   - The 99 up-to-date pages are not re-translated: FR/ES PMP 31× in 8 pages, benchmark 27× in 10, ES «panel de control» 11× in 6. Either targeted fixes in phase 4, or keep the docs' term.
>   - IT labels that disagree with the rest of the UI: «Aggiustamento», «Tassa».
>   - Debatable labels: «Bonifico» vs «giroconto», Titoli vs Asset, split ES/FR, ES «auto-hospedado».
>   - UI bugs: FR «VNI», ES «VAN», ES Configuración/Ajustes, three words for drawdown.
>   - The glossary's size.
> - Phase 2's small pages use the page's own WAC term (FR/ES PMP): to align before the commit if the developer chooses PRU/PMC.
>
> **Developer's decisions on the glossary** (via the coordinator, 01:30), his choices verbatim:
> 1. «PRU in francese e PMC in spagnolo, ovunque (Consigliato)»;
> 2. «Applica tutte le correzioni della tabella (Consigliato)»;
> 3. «M le corregge a mano dopo la pipeline (Consigliato)».
> - **Corrected labels** (S changes them in the catalogues before 1.2; the glossary uses them already):
>   - IT: «rettifica», «rettifica prezzo», «imposta/imposte»;
>   - cash transfer «giroconto / virement / transferencia de fondos»;
>   - asset transfer «trasferimento asset / transfert d'actif»;
>   - split es «desdoblamiento»; self-hosted es «autoalojado»; NAV everywhere; settings es «configuración»;
>   - drawdown: IT «drawdown» for the whole family; FR «repli» («perte maximale» only for the max); ES «caída».
> - **Coordinator's choices:**
>   - benchmark fr/es «indice de référence» / «índice de referencia»;
>   - drop the 6 unused terms;
>   - card it «scheda»; tooltip it «tooltip»; toggle → «toggle (on/off switch)»;
>   - keep all 112 new terms; the sense tags are OK.
> - **Phase 4:** M fixes by hand the up-to-date pages where the glossary changes a term (PMP, benchmark, panel de control, card and the others in the conflicts table). No stamp: the EN does not change.
>
> **2.6 ✅ Glossary installed, WAC aligned, gates** (M, 02:00)
> - `mkdocs_src/aphra-pipeline/glossaries/glossary.json`: **167 terms**, i.e. 170 in the candidate − 6 unused + 3 explicit (`taxes`, `maximum drawdown`, the UI's `per-asset drawdowns`); same format, `_meta` unchanged (`runs/b11_glossary_final.json`).
>   - `_load_glossary()` renders 167 lines for it/fr/es, about 5.5k characters each.
>   - Checked lines: `WAC → PMC/PRU/PMC`, `cash transfer → giroconto/virement/transferencia de fondos`, `max drawdown → drawdown massimo/perte maximale/caída máxima`, `toggle (on/off switch)`, `tooltip → tooltip` (it).
> - **WAC in the small pages:** `performance-metrics/index` and `portfolio-engine/deposited-capital`, FR PMP → PRU and «prix moyen pondéré» → «prix de revient unitaire» (19 + 1 replacements), ES PMP → PMC and «precio medio ponderado» → «precio medio de compra» (19 + 1).
>   - FR/ES heading «📊 Prix moyen pondéré» → «📊 Prix de revient unitaire (PRU)» (no link targets its anchor).
>   - The stamp stays valid (the EN did not change).
> - **Gates:**
>   - `mkdocs build` strict: exit 0, **0 WARNING/ERROR** (`runs/b11_build_A2.log`);
>   - `translate-validate` on the 26 pages: 9 errors, all in `profile` (the deferred note);
>   - stamped pages «up-to-date»;
>   - `git diff --check` clean.
> - **Checkpoint A:** the 25 small pages + the urgent half of `profile`, the stamp (hashes), the glossary, `.env.example`, this plan. The 3 missing small pages (28 → 25):
>   - `community/contribute`, `asset-types/etfs`, `indicators/index` are moved to phase 4: they link to anchors that only the pipeline brings to it/fr/es, and the strict build would fail;
>   - `profile` is partial;
>   - `import/directa`, freed from S's area, joins the 25.

### 3. ✅ Phase 3: the launch (the developer) — 2026-10-10

> **Note implementazione**: checkpoint A committed by the developer (batch 24): `8f30a7f03` (26 translations), `c9cf30edc` (glossary), `416bdccac` (`.env.example`), `01c6f1ae4` (journal).
> - **Run** 01:53–02:08, launched by the developer with 400 workers instead of 3: 299 done, 4 failed for network (`runs/b11_pipeline_run.log`).
> - **Retry** at 09:43 by the coordinator: 4 of 4, no structure warning (`runs/b11_pipeline_retry.log`). Before it, the coordinator removed the failed language from `langs_done` in those 4 entries (`/tmp/libreFolio_b11_retry.sh`): the cache bug of step 4.1.
> - **Result:** 231 translations modified, 72 new, the cache; the dry run on the list says «up-to-date».

> - **Files:** `release-pipeline/runs/b11_pipeline_files.txt`, 101 EN pages. Excluded: the 25 stamped, the 4 deferred, S's 3.
> - **Dry run:** 101 × 3 = **303 translations, about 8.37 M tokens** (6.45 M in, 1.92 M out).
> - **Configuration:** the worktree's `mkdocs_src/aphra-pipeline/.env` (Doubleword, `deepseek-ai/DeepSeek-V4.1-Flash`, key present, web search off). Model check and `translate-check` green.
> - **Command** (from the worktree, with the shared venv; `--file` is mandatory: without it the pipeline would also take the deferred pages and S's):
>   - `cd /Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-upgraded-telegram && PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs translate --workers 3 --file $(cat /Users/ea_enel/Documents/00_My/LibreFolio-cloud-sizing/release-pipeline/runs/b11_pipeline_files.txt) 2>&1 | tee /Users/ea_enel/Documents/00_My/LibreFolio-cloud-sizing/release-pipeline/runs/b11_pipeline_run.log`

### 4. ✅ Phase 4: after the pipeline — 2026-10-10 (checkpoint B)

> Coordinator brief at 10:01. Developer, verbatim: «ricorda ad M di fare comunque tutti i check che abbiamo sviluppato, build della doc compresa alla fine, e di guardare con occhio critico, se i check non sono corretti, danno falsi positivi o negativi, etc... vanno corretti, mentre al contrario bisogna correggere la doc».

**4.1 ✅ The cache bug** (`mkdocs_src/aphra-pipeline/translate_docs.py`)
> **Note implementazione**: an entry's `md5` is now the EN version its `langs_done` were translated or stamped from, and every write goes through 5 pure helpers placed after `_file_md5`:
> - `_needs_translation` (the plan);
> - `_cache_mark_analyzed`: resets `langs_done` when the md5 changes — the bug: a language that then failed, was cut by an interruption or left out by `--lang` stayed «done»;
> - `_cache_mark_translated`;
> - `_cache_mark_failed`: keeps the last `translated_at`, adds `failed*`, never marks the language done (before, a failure wrote `translated_at = now`);
> - `_cache_stamp`: keeps the other languages only for an unchanged md5 and clears `failed*` on the stamped ones; `run_stamp` prints «pending again».
> - Used by the plan, the parallel and sequential analyze/success/failure sites and `run_stamp`. The success sites no longer re-hash the file.
>
> **⚠️ Fuori pista**: the test-author found a second, older race — the md5 was read from disk only *after* the analysis (hours on the flex queue), so an EN edit saved meanwhile was recorded as translated. Fixed with `_read_source(path) -> (text, md5)`: one read, md5 of those bytes, text decoded from the same bytes with universal newlines. `_pipeline_analyze` returns `source_md5`; the sequential loop reads it before the analysis.

**4.2 ✅ Regression tests** (test-author)
> **Note implementazione**: `backend/test_scripts/test_utilities/test_translation_cache.py`, **38 ids**, and the runner action `utils translation-cache` (`scripts/test_runner/_backend_utils.py`, `isolation="pure"`). They drive the real `run_translate`/`run_stamp`, with the four LLM seams faked, on a docs tree under `tmp_path`, and include a barrier on the fakes' contract.
> - RED vs HEAD `01c6f1ae4`: 13 failed, 9 passed, 16 errors (transitions missing).
> - RED vs the first fix (no `_read_source`): 5 failed — the 4 edit-during-analysis ids (LF/CRLF × parallel/sequential) and the barrier.
> - GREEN on lane 6158: `utils translation-cache` 38 passed; `utils translation-code-blocks` 80 passed; `test check-orphans` clean; `--workers 4 utils all` 1320 passed (first round).
> - Logs: `runs/b11_cache_*`, `runs/b11_cache_v2_*`.

**4.3 ✅ Masked pairs in older rounds** (`release-pipeline/scripts/b11_masked_scan.py`, `runs/b11_masked_scan.json`)
> **Note implementazione**: rule — the EN version at the translation file's last commit must equal the cached md5, plus the `failed` flags. Result: 593 pairs OK.
> - 4 stale `failed` flags (`cash-transfer` it/fr/es, `revolut` es, June): the translations are verified aligned with the current EN; the flags stay (a stamp skips unchanged entries).
> - 3 stale pairs: `fundamentals/day-count` it/fr/es said the function lives in `backend/app/utils/financial_math.py`; fixed by hand (the EN says the provider module). No stamp needed.
>
> **⚠️ Fuori pista**: 2 bugs in my scan script — the porcelain `strip()` mangled the first dirty path; entries whose md5 ≠ current EN must be skipped.

**4.4 ✅ The 16 structure warnings of the run** (`release-pipeline/scripts/b11_struct_fixes.py`, 19 edits on 14 files)
> **Note implementazione**:
> - extra bold on glossary terms removed (signals it, faq es, brokers/index fr, kpi-cards es ×7, danske-bank fr, dashboard/index it, sharing fr, etoro fr);
> - missing bold added (image-crop it, correlation es, risk-contribution it);
> - pac-allocator es: the continuation paragraph turned into a bullet, restored;
> - portfolio-engine/index fr: `$> 0.01$` lost its delimiters, restored;
> - CDaR es: 2 links restored.
> - The 3 `LINE_COUNT` were false positives (4.5).

**4.5 ✅ The checks, corrected where they were wrong**
> **Note implementazione**:
> - **`LINE_COUNT` false positive** (`translate_docs.py` `_structural_diff`): the EN wraps at ~80 columns, the translation writes one line per paragraph. The fingerprint now has `block_count` (blank-line separated) and check 12 compares blocks (threshold max(3, 15%)). The 3 cases are clean; a half-truncated page is still flagged.
> - **`html-attr-missing` false positive** (`validate_translations.py`): 201 warnings, all on `user/fx/detail/data-editor`, because inline code `` `EUR<USD` `` was read as a `<usd>` tag. `_strip_code_blocks` is now fence-aware (`code_line_mask`: tilde, indented, info strings), and `_strip_code` also removes inline code for the 3 HTML checks. Old vs new validator on all 621 pairs: only those 201 warnings change.
> - **False negative — English alt texts:** the validator skipped `alt`/`title`/`aria-label` (translation expected) but never checked they were translated. New check `text-untranslated` (WARN, ≥ 3 words, identical to a source value, «Buy Me a Coffee» allowed). It found **141** outside S's pages.
> - **Root cause in the pipeline prompts:** `step3_user.txt:16`, `step4_user.txt:28`, `step5_user.txt:27-28` told the model to copy «HTML attributes» verbatim / not translate them. They now separate technical attributes (`src`, `href`, `class`, `id`, `style`, `data-*`) from the human text of `alt`, `title`, `aria-label`, which is translated. Placeholders unchanged.
> - **False negative — anchors:** no validator checked that `page.md#anchor` lands on an anchor of the *translated* target; `mkdocs build --strict` stops at the first language. New check `anchor-missing` (ERROR): resolves `page.<lang>.md` with EN fallback, Python-Markdown's default slug, explicit ids, HTML ids, one issue per page and URL. Cross-checked with a non-strict build into `/tmp`: same 51 links (and, with the 13 new ids removed in memory, the same 18 of family B).

**4.6 ✅ The 4 deferred pages** (`release-pipeline/scripts/b11_deferred_pages.py`)
> **Note implementazione**: the anchors they need now exist in it/fr/es (`welcome-setup`, `support-librefolio`, `etf-family`, `stored-carries`, `primary-modes`). Written by hand from their EN diffs: the profile Welcome note, the contribute paragraph, the ETF subtypes paragraph, the indicators «sessions» paragraph (glossary «seduta/séance/sesión»). Then `translate-stamp --file` for the 4; `translate --dry-run` lists only S's 3 pages.

**4.7 ✅ Alt texts translated** (`release-pipeline/scripts/b11_alt_apply.py`)
> **Note implementazione**: 170 replacements in 54 page×language files (≥ 3-word ones plus the 2-word ones in the same tags), labels from the UI catalogues and the glossary; every mapping used at least once. `text-untranslated` outside S's pages: 141 → 0. Plus UI labels the pages had wrong: es «Copiar y abrir» (about, gallery desktop/mobile), es «Diagnóstico de plugins», it «Diagnostica plugin».

**4.8 ✅ Glossary alignment of the pages the run did not re-translate** (`release-pipeline/scripts/b11_glossary_scan.py`, `b11_glossary_align.py`)
> **Note implementazione**: **327 replacements in 109 files**, exact literals with expected counts, sense-aware:
> - WAC FR PMP → PRU, ES → PMC;
> - NAV (FR VNI → NAV, «le NAV» as the UI);
> - benchmark (market sense) → indice de référence / índice de referencia, synthetic benchmark unchanged;
> - overview → vue d'ensemble / resumen (FR «aperçu» = preview stays);
> - dashboard ES → Panel;
> - open-source ES → código abierto;
> - cost basis → coût de base / costo di carico;
> - currency conversion → conversione di valuta / conversion de devise;
> - cash transfer → giroconto / virement / transferencia de fondos (a real bank wire stays «bonifico / transferencia bancaria»);
> - split (corporate action) → IT split, ES desdoblamiento (the ES `split` page rewritten term by term, «Forward Forward» headings fixed); the unlink action → UI «Scollega coppia / Séparer la paire / Separar par»;
> - tax IT tassa → imposta, FR taxe → impôt (proper names «taxe Tobin», «Taxe sur les transactions financières» and Coinbase's «Taxes» menu stay; ES «tasa» = rate stays);
> - IT adeguamento/aggiustamento → rettifica (prezzo);
> - drawdown: risk indicator names from the UI, «perte maximale» / «caída máxima» for the max;
> - AI Export FR/ES → export IA / exportación IA;
> - tooltip FR/ES → infobulle / información emergente; card IT → scheda.
> - Residual scan hits are all intentional (preview, rate, wire, synthetic benchmark, UI names, parentheticals, CSS classes, HTML comments).
>
> **⚠️ Fuori pista**: the scanner masked link targets, so the first dry run had 15 literal mismatches (`**[text](url)**`), fixed; a duplicate dict key wiped the `adjustment.es` entry, caught by the re-scan and re-applied; the script is now idempotent («already applied» is not an error).

**4.9 ✅ Explicit heading ids for links into translated pages** (`release-pipeline/scripts/b11_anchor_ids.py`)
> **Note implementazione**: 13 headings, translation side only (EN untouched; the id equals the EN auto slug): `docker_advanced` `#test-mode` (it/fr/es), `filesystem` `#backup` (fr/es), `cli_tools` `#reset-a-password-or-lock-an-account` (it/fr/es), `dashboard/index` `#data-quality-banner` (it/fr/es), `danske-bank` `#end-of-period-check` (it/es) — 18 build warnings closed.

**4.10 ✅ `MKDOCS_ANCHOR_EXCEPTIONS`** (`dev.py`): the 3 entries removed, the dict is empty; the 3 anchors exist in all 4 languages.

**4.11 ✅ Links into S's stale pages** (`release-pipeline/scripts/b11_s_page_ids.py`; coordinator decision (a))
> **Note implementazione**: the 33 remaining strict-build warnings were links from pages re-translated in this round into S's 2 stale pages. Ids in the it/fr/es translations of S's pages (they are translations, so mine; S's branch touches only the EN):
> - **faithful, 21 links:** `#review` (the «Step 4» heading), `#opening-date` (the «broker's opening date» heading), `#only-when-needed` (the paragraph that introduces the steps that appear only when needed);
> - **⚠️ PROVISIONAL, 12 links — the second round, after S is integrated, must replace them:**
>   - `user/transactions/import/how-to.{it,fr,es}.md` — `{: #guided-first-import }` on the «step-by-step guide» H2 (no equivalent: the EN «Guided First Import» section is newer than the translation);
>   - `user/transactions/index.{it,fr,es}.md` — `{: #bulk-workspace }` on the paragraph about the clone/bulk workspace;
>   - `user/transactions/index.{it,fr,es}.md` — `{: #link-pairs }` on the «composite transactions / promotion» row.
> - Also fixed in `transactions/index.it`: «إcco» → «Ecco» (a stray Arabic letter; a scan for foreign scripts in all translations found only this one).

**4.12 ✅ `nav_translations`** (`mkdocs_src/mkdocs.yml`, only that section; coordinator: M is the writer, the nav is not touched — S adds the scalable line in his branch)
> **Note implementazione**: 25 labels aligned to the glossary and the page titles (`release-pipeline/scripts/b11_nav_labels.py`), e.g. it Split / Giroconto / Commissioni & Imposte / Drawdown Massimo / Prezzo Medio di Carico / AI Export; fr Vue d'ensemble / Division / Frais & Impôts / Perte Maximale / Choix de l'Indice de Référence / Prix de Revient Unitaire; es Brókeres / Panel / Transferencia de Fondos / Caída Máxima / Precio Medio de Compra / Exportación IA. YAML reloads; the only remaining «benchmark» labels are the synthetic ones (glossary).
>
> **⚠️ Fuori pista**: «Overview Providers» and «Split & Promote» stay English. My report to the coordinator listed them as untranslated, but the file says «kept in English per dev-manual policy»: they are Developer Manual entries, like «Service Architecture». Reported as my error in checkpoint B.

**4.13 ✅ Round 2: what the first pass could not see** (`release-pipeline/scripts/b11_glossary_align2.py`, 160 replacements in 46 files)
> **Note implementazione**:
> - **Capitalised forms** (titles, type rows) missed by the case-sensitive scan (`Trasferimento di Liquidità`, `Conversione Valutaria`, `Transferencia de Efectivo`, `Descripción General`, `Transfert de fonds`…), plus the UI action labels Promuovi / Promouvoir / Promocionar, and ES «base de costo» → «coste base».
> - **Stale translations hidden by old stamps** — `b11_stamp_audit.py`: 160 (page, lang) pairs on 54 pages had an EN change after their last translation and then a stamp; `b11_stamp_port_check.py` (inline code, link URLs, numbers added to the EN must be in the translation) and a manual read of the larger EN diffs found the unported ones:
>   - `transaction-types/adjustment` it/fr/es (stamped 2026-08-04): cashless `ADJUSTMENT`, succession holdings, imported examples, seeds and in-kind capital — ported;
>   - `portfolio-engine/deposited-capital` it/fr/es: Capital Baseline, `InKindCapital` paragraph, `asset_event_id` row, `CapitalBaseline` formula — ported;
>   - `fifo-engine/index` it/fr/es: reference price source `unavailable`;
>   - `fifo-engine/fifo-lot-analysis` it: the price-lookup paragraph (`LotsAnalysisService`), a stale pointer removed.
>   - Every other stamp was verified ported (transfer, fee, deposit-withdrawal, credits-legal, dividend, maturity-settlement, …). S's 2 pages are on the list too and are left to S's round.
> - **Identifiers the model had translated**, restored verbatim: `price-resolution` es (`MARKET_PRICE`, `TRADE_AVG`, `CARRIED`, `MISSING`, `LAST_TRADE_PRICE`, the Mermaid node labels included); `net-annualized-return` it/fr/es (`StartValue`, `net_total_return`, `total_return`; es `PyG` → `PnL`); `obv` fr `period`; `trend` fr `+DM`/`-DM`; `buy-sell` it/fr/es; `fifo-lot-analysis` it `reference_unit_price`.
> - `nav` fr H1 «Valeur Netative Inventaire» fixed.
> - 30 trailing-whitespace lines that the run had copied from the EN into `index` and `admin/service_exposure` (it/fr/es) stripped: `git diff --check` clean.
>
> **⚠️ Fuori pista**: the round-2 engine re-counted insertions as pending (the old text survives inside the new one): a second `--apply` would have duplicated 4 paragraphs. Caught on the dry run, fixed in both scripts, single insertions verified.

**4.14 ✅ One more false negative of the checks: inline code** (`validate_translations.py`)
> **Note implementazione**: new check `inline-code-missing` (WARN): every inline code span of the source must appear verbatim in the translation, digit grouping ignored (`1,000.50` = `1.000,50`). It found the identifiers of 4.13; now 0 outside S's pages. Lint: 2 new `B905` on my `zip()` calls fixed with `strict=True`; ruff counts equal to or below HEAD; black was not clean at HEAD on these files and is not reformatted.

**4.15 ✅ Final gates** (2026-10-10 ~11:05, load 6–17 on the shared machine)
> **Note implementazione**:
> - `translate-validate --hide-localized`: 84 errors and 144 warnings, **all on S's 3 pages** (0 outside); `anchor-missing` 0; `text-untranslated` 0 outside S.
> - `translate-diff --issues-only`: 9 pairs with issues, all S's 3 pages.
> - `translate-check`: green (224/224 cached, Doubleword OK).
> - `mkdocs build` strict: exit 0, **0 WARNING/ERROR**.
> - `check-links`: 94 valid, no known exception left, `#rolling-return` ✅.
> - Lane 6158: `utils translation-cache` 38 passed, `utils translation-code-blocks` 80 passed, `check-orphans` clean.
> - `git diff --check` clean. No server started; ports 6158/6168 free.
> - Logs: `runs/b11_final_*`.

**4.16 Proposed follow-ups (not done: EN or shared)**
> - `mkdocs_src/docs/developer/docs/translation-pipeline.md` (EN, Developer Manual): document the cache semantics (md5 = version translated/stamped from; failures never done; stamp keeps other languages only for the same md5), the 3 new validator checks and the prompts' alt/title policy.
> - devWiki: file «stamps hide stale translations», with the audit method.
> - A stamp audit after every round (`b11_stamp_audit.py` + `b11_stamp_port_check.py`) could become a `translate-validate` option.
> - Batch 12 (2026-10-10): the developer page is assigned to M (docs-writer); the devWiki entry goes to the historian through the coordinator.

### 5. ⏳ Second round — prepared 2026-10-10 (batch 12), to run after train 30 (S integrated)

> Coordinator, batch 12: «prepara l'elenco … ma eseguilo dopo il treno 30, quando S è dentro. Le pagine EN del lotto 41 di I arriveranno dopo.» Nothing below has been run.

**5.1 Pipeline** (large drift; the developer launches it, as for phase 3). S's three pages plus his new one, 3 languages each:

| Page (`user/transactions/…`) | Why | Today (base `e32f47133`) |
|---|---|---|
| `import/how-to` | S rewrote the EN (guided first import, steps that appear only when needed, review, opening date) | translations of 2026-09-04; 84 validate errors and 144 warnings are all on these three pages |
| `import/index` | S's EN (report sets, the plugin list) | stamped 2026-10-05 over an EN change of +195/−41 lines (stamp audit) |
| `index` | S's EN: bulk workspace, link pairs, «Save all», «Merge all» | translations of 2026-06-19, the table split by an untranslated paragraph |
| `import/scalable` | new page (S adds it, with its nav line) | absent from the target |

> - Dry run today: `transactions/index` ~18.4K, `import/index` ~58.7K, `import/how-to` ~47.6K tokens per language, so ~374K for the three existing pages, before S's changes and without `scalable`. Re-estimate with `translate --dry-run` on the integrated tree.
> - The prompts now translate `alt`/`title` (batch 11): the 54 English alt texts on these pages go with the run.

**5.2 By hand, then `translate-stamp`** (small drift):
> - `user/brokers/index.{it,fr,es}.md:34`, the «Portal URL» line: port S's EN rewrite (icon order: custom → plugin → favicon → briefcase), then `translate-stamp --file user/brokers/index.en.md`.
> - `user/dashboard/charts`: only if the P&L-per-broker change (paused) alters its table of lines.

**5.3 Ids to supersede.** Batch 11 put 18 ids into S's stale translations so that links from the pages re-translated in round 1 resolve. The pipeline's output must replace all of them; then `anchor-missing` must stay at 0:
> - faithful (9): `#review`, `#opening-date`, `#only-when-needed` in `import/how-to.{it,fr,es}.md` (it 49/225/279, fr 60/231/288, es 46/232/279);
> - **provisional (9), the ones that must not survive:** `#guided-first-import` on the «step-by-step guide» H2 of `import/how-to.{it,fr,es}.md` (it 14, fr 15, es 14); `#bulk-workspace` and `#link-pairs` as paragraph ids in `transactions/index.{it,fr,es}.md` (34 and 41). They serve 12 links: getting-started ×3 → `#guided-first-import`; brokers/import ×3 and transactions/form ×3 → `#bulk-workspace`; transactions/form ×3 → `#link-pairs`.

**5.4 Checks after S's catalogues.** S changes UI labels in the catalogues before 1.2 (rettifica, imposta, giroconto, desdoblamiento…). Re-run the glossary scan and the UI lookup on the integrated tree, and align any page whose quoted label no longer matches the app (by hand, no stamp when only the translation changes).

**5.5 Gates** as in phase 4: `translate-validate --hide-localized` (target: 0 errors, 0 warnings), `translate-diff --issues-only` (0), `translate-check`, `utils translation-cache`, `utils translation-code-blocks`, `check-orphans`, strict `mkdocs build` (0 WARNING/ERROR), `check-links`, `translate --dry-run` (nothing pending), `git diff --check`; plus the stamp audit (`b11_stamp_audit.py`, `b11_stamp_port_check.py`) on the stamped pages.

> **Sequence** (coordinator, 11:49): train 30 is in (`dev_release2` = `d59762e0a`, S integrated: `import/how-to`, `import/index`, `transactions/index`, the new `import/scalable`, the «Portal URL» line). M closes batch 12 first; the developer merges the target into M's branch; the second round runs on that base.
> I's batch-41 EN pages (`user/dashboard/charts.en.md`, `portfolio-engine/deposited-capital.en.md`) join this round if they are in by then, otherwise a small third round. `deposited-capital` was ported by hand in batch 11 (Capital Baseline, `InKindCapital`): classify I's diff from the git log, not from the counts.
