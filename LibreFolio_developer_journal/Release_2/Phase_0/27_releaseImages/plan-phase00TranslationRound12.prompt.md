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

### 5. ⏳ Second round — prepared 2026-10-10 (batch 12), running in batch 13 on train 31 (`f4a42bf4a`)

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
> - `user/dashboard/charts`, `portfolio-engine/deposited-capital`: I's batch 41 is **active** (not paused, as written earlier); its EN pages are not ready yet — they join this round if they land in time, otherwise a small third round.

**5.3 Ids to supersede.** Batch 11 put 18 ids into S's stale translations so that links from the pages re-translated in round 1 resolve. The pipeline's output must replace all of them; then `anchor-missing` must stay at 0:
> - faithful (9): `#review`, `#opening-date`, `#only-when-needed` in `import/how-to.{it,fr,es}.md` (it 49/225/279, fr 60/231/288, es 46/232/279);
> - **provisional (9), the ones that must not survive:** `#guided-first-import` on the «step-by-step guide» H2 of `import/how-to.{it,fr,es}.md` (it 14, fr 15, es 14); `#bulk-workspace` and `#link-pairs` as paragraph ids in `transactions/index.{it,fr,es}.md` (34 and 41). They serve 12 links: getting-started ×3 → `#guided-first-import`; brokers/import ×3 and transactions/form ×3 → `#bulk-workspace`; transactions/form ×3 → `#link-pairs`.

**5.4 Checks after S's catalogues.** S changes UI labels in the catalogues before 1.2 (rettifica, imposta, giroconto, desdoblamiento…). Re-run the glossary scan and the UI lookup on the integrated tree, and align any page whose quoted label no longer matches the app (by hand, no stamp when only the translation changes).

**5.5 Gates** as in phase 4: `translate-validate --hide-localized` (target: 0 errors, 0 warnings), `translate-diff --issues-only` (0), `translate-check`, `utils translation-cache`, `utils translation-code-blocks`, `check-orphans`, strict `mkdocs build` (0 WARNING/ERROR), `check-links`, `translate --dry-run` (nothing pending), `git diff --check`; plus the stamp audit (`b11_stamp_audit.py`, `b11_stamp_port_check.py`) on the stamped pages.

> **Sequence** (coordinator, 11:49): train 30 is in (`dev_release2` = `d59762e0a`, S integrated: `import/how-to`, `import/index`, `transactions/index`, the new `import/scalable`, the «Portal URL» line). M closes batch 12 first; the developer merges the target into M's branch; the second round runs on that base.
> I's batch-41 EN pages (`user/dashboard/charts.en.md`, `portfolio-engine/deposited-capital.en.md`) join this round if they are in by then, otherwise a small third round. `deposited-capital` was ported by hand in batch 11 (Capital Baseline, `InKindCapital`): classify I's diff from the git log, not from the counts.

**Batch 13 — execution** (coordinator 13:09: batch 12 merged as `344407d03`, train 31 `f4a42bf4a` with D's catalogues and Risk 02; M's worktree fast-forwarded, clean)

**5.0 ✅ Detectors on train 31** (`release-pipeline/runs/b13/b13_*_0.log`)
> **Note implementazione**: `translate --dry-run`: 5 pages × 3 = 15 (S's 3, the new `import/scalable`, and `user/brokers/index`); `translate-validate`: 90 errors, 159 warnings, 3 files missing (`scalable` ×3) — **all 249 issues on those 5 pages, 0 outside**; `translate-diff`: 12 pairs, same pages.

**5.2 ✅ `user/brokers/index` by hand** — the only EN change since its pipeline translation is the «Portal URL» line (`d5c649e9f`, icon order: custom → the Default Import Plugin's when made for this broker → the website's → a generic importer's → a briefcase). Written in it/fr/es with the page's own bold labels; validate clean in the 3 languages; `translate-stamp --file user/brokers/index.en.md`.

**5.1 ✅ Pipeline** — 4 pages × 3 = 12 translations, ~517K tokens (in ~395K, out ~122K): `import/how-to`, `import/index`, `import/scalable` (new), `transactions/index`. List: `release-pipeline/runs/b13/b13_pipeline_files.txt`. `translate-check` green (DeepSeek-V4.1-Flash via Doubleword, web search off, key present). The prompts carry the batch-12 `data-title` rule (`import/how-to` has 7 captions).
> Command (the developer, from the worktree):
> `cd /Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-upgraded-telegram && PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs translate --workers 3 --file $(cat /Users/ea_enel/Documents/00_My/LibreFolio-cloud-sizing/release-pipeline/runs/b13/b13_pipeline_files.txt) 2>&1 | tee /Users/ea_enel/Documents/00_My/LibreFolio-cloud-sizing/release-pipeline/runs/b13/b13_pipeline_run.log`

**5.3 ✅ — the ids:** every target anchor (`#review`, `#opening-date`, `#only-when-needed`, `#guided-first-import`, `#link-pairs`, `#bulk-workspace`) is an explicit `{: #id }` on an EN heading, so the run carries them onto the right translated headings and replaces the batch-11 ids. Check after the run: no paragraph-level `{: #bulk-workspace }` / `{: #link-pairs }` left, `anchor-missing` 0.

**5.6 ✅ `pending_langs` removed** (its own commit): 29 entries, each `["it","fr","es"]` while the same entries have all three in `langs_done` — the field contradicted the cache, and no code reads it (coordinator checked the `.py`; M found no other reader). Removed with a format-preserving rewrite (HEAD round-trips byte for byte). The cache file also carries the 5.2 stamp and will carry the run: the intermediate content for the separate commit is produced by `release-pipeline/scripts/b13_cache_without_pending_langs.py` (HEAD minus `pending_langs`, nothing else; verified).

**5.7 ✅ Validator unit tests** — 2026-10-11 (its own commit; test-author): new `backend/test_scripts/test_utilities/test_translation_validator.py` and runner action `utils translation-validator` (M is the writer of `_backend_utils.py` for it). A check whose behaviour looks wrong is reported to the coordinator before any change.
> **Note implementazione** (test-author): 71 tests, 25 functions (strings in memory and docs trees under `tmp_path`; an autouse fixture redirects `DOCS_DIR`, so the repo's docs and cache are never opened); runner action `utils translation-validator` (`isolation="pure"`, +20 lines after `translation-cache`). RED vs the pre-batch-11 pipeline (`01c6f1ae4`): 64 failed, 7 passed (47 missing functions, 17 behaviour). GREEN, lane 6158: validator 71, cache 38, code-blocks 80, `check-orphans` clean, `--workers 4 utils all` 1395 passed; 21 in-memory mutants of the checks each caught; ruff/black clean. Logs `runs/b13/b13_validator_*`.
>
> **⚠️ Fuori pista — a wrong behaviour of `anchor-missing`, reported to the coordinator before any change** (no test locks it in):
> - `_page_anchors` (batch 11, mine) offers the text slug of a heading that has an explicit id, does not seed the duplicate counter with explicit ids, and reads `{#…}` / `id="…"` written in inline code; Python-Markdown gives an explicit-id heading only its id (`## Dettagli {: #details }` → build `{details}`, validator `{details, dettagli}`). Verified independently with Python-Markdown (`/tmp` probe, real tag parsing).
> - Corpus-wide, against a render with the site's own extensions (`mkdocs.config.load_config` → `markdown_extensions` + `mdx_configs`; 944 pages in 5.8 s): the validator accepts **1179 ids the build lacks** (335 pages: false negatives) and misses **109 heading ids the build has** (73 pages, e.g. emoji shortcodes in headings: false errors if linked). Today 0 links are affected (0 `anchor-missing`, and the strict build agrees). `dev.py` `_mkdocs_anchor_slugs` (check-links) has the same flaw. Log `runs/b13/b13_anchor_corpus_current.log`.
> - Also: the `inline-code-missing` message names a changed number without its separators (`1,000.50` → «`100050` missing»): message only.

**5.1/5.3 — after the run** (launched by the developer 2026-10-11 12:03; 12/12, 0 failed, 11 min 49 s, ~517K tokens; log `runs/b13/b13_pipeline_run.log`)
> **Note implementazione**:
> - The 2 BOLD_MARKERS of the run (both fr, Δ+1 each) are the same pattern as batch 11 — a glossary term bolded: «**lecteur**» in `transactions/index.fr:33`, «**Lots de rapports**» in `import/how-to.fr` (a table cell). Removed; bold counts equal to the EN (134/134, 228/228). Found by pairing blank-line blocks, since the tool's line pairing drifts after rewrapping.
> - **⚠️ Fuori pista — the French `transactions/index` had left ~30 UI labels in English** (Edit, Clone, Delete, Save All, Merge, Merge all (N), All left/right, Combine, Reset All/selected, Promote pair, Split pair, the row states new/edit/del, Got it…), and the dialog title in italics. IT and ES had translated them. Found by a scan of the new pages' bold spans equal to the EN that the UI catalogue translates (`release-pipeline/runs/b13/b13_ui_bold_scan.txt`); fixed with the exact catalogue labels, picked by context (keys in `b13_ui_label_keys.txt`: e.g. «Review» → `importWizard.todoWarningConfirmReview` «Vérifier»; the states → `transactions.bulk.stateNew/Edit/Del` «nouveau/modif./suppr.»).
> - `import/scalable` (new page): the importer names follow the UI (`brimPlugins.broker_scalable(_deposit).name`): it «Scalable Capital conto broker / conto deposito», fr «… compte-titres / compte rémunéré», es «… cuenta de valores / cuenta remunerada», in the bold labels and the icon alts; the account nouns aligned with them and with the importer's own notices (fr «compte courtier/de dépôt» → «compte-titres/rémunéré», es «cuenta de bróker/overnight» → «cuenta de valores/remunerada»; «fichier courtier» / «archivo de bróker» stay, as the UI says); es «**Parse**» → «**Analizar**» (`importWizard.step3Title`). Kept: the example broker names in italics (*Scalable broker*…), names the user types.
> - `import/index.fr`: the 6 favicon alts were left as in the EN («favicon Intesa Sanpaolo») — now «favicon d'Intesa Sanpaolo», «du Crédit Agricole», «de …» (it/es already had «di/de»).
> - **5.3:** every target anchor (`#review`, `#opening-date`, `#only-when-needed`, `#guided-first-import`, `#wrong-broker`, `#link-pairs`, `#bulk-workspace`) sits on the matching translated heading in it/fr/es; no paragraph-level id is left: the 9 provisional ids of batch 11 are gone.
> - **For 5.4 (after P's keys):** IT/ES translated the labels, not always with the app's words: it `transactions/index` «**Dividi coppia**» (UI «Scollega coppia»), «**Ho capito**» (UI «Capito»), the dialog title «*Suggerimenti che non hai guardato*» (UI «Suggerimenti non ancora visti»); es «**Añadir transacción**» (UI «Agregar Transacción»), «*Sugerencias que no has revisado*» (UI «Sugerencias aún sin revisar»). The 5.4 scan must compare every bold/italic label with the catalogue, not only those left in English.
> - Gates (12:22, load ~5): `translate-validate --hide-localized` **0 errors, 0 warnings** on 624 files (from 90/159 at the start of the batch; the first fully clean run of the release); `translate-diff` 624/624 clean; `translate --dry-run` nothing pending; strict `mkdocs build` 0 WARNING/ERROR; `check-links` 95 valid.

**5.8 ✅ `anchor-missing` from the real render — option (b)** (coordinator 2026-10-11 12:08: «(b)… è proprio lo scopo del controllo»; `check-links` aligned in a separate commit)
> **Note implementazione**:
> - NEW `mkdocs_src/aphra-pipeline/page_anchors.py`: `render_anchors(source)` renders through MkDocs' own `Page.render` with the site configuration (`load_config(mkdocs_src/mkdocs.yml)`, loaded once), front matter split like `Page.read_source`, MkDocs logging silenced; it returns `Page.present_anchor_ids`, the set `mkdocs build --strict` checks (tree ids, `<a name>`, raw-HTML ids). `file_anchors(path)` reads utf-8-sig like MkDocs and renders each version of a file once (cache on path, mtime, size). MkDocs is imported only inside the functions.
> - `validate_translations.py`: the hand-made slugs (`_toc_slug`, `_page_anchors`, the two regexes, `unicodedata`) removed; `check_link_anchors` uses `file_anchors` / `render_anchors` (in-page anchors rendered lazily once — the old `setdefault` re-computed them on every link). `inline-code-missing` names the source's spelling (`1,000.50`, not `100050`).
> - `dev.py` check-links: `_mkdocs_anchor_slugs` → `_mkdocs_page_anchors` = the same `file_anchors`, imported inside the function; the command first checks `page_anchors` + `mkdocs` and otherwise exits 1 with «check-links needs MkDocs and mkdocs_src/aphra-pipeline/page_anchors.py». Verified with MkDocs made unimportable: `dev.py --help` exit 0, `check-links` exit 1 with the message. Importing `validate_translations` does not import MkDocs either.
> - **Proof of exactness:** a real `mkdocs build` (all 4 languages, into `/tmp`) with `Page.render` wrapped to record each page's `present_anchor_ids`, compared with `file_anchors` on the same files: **946/946 identical, 13,992 ids** (`runs/b13/b13_anchor_parity_2.log`; a first run during the pipeline differed on 1 file the run rewrote mid-probe). Cost: 5.8 s for the whole corpus; `translate-validate` 7.2 s in total.
> - `check-links`: 95 valid links before and after, identical list (the 10 with an anchor included) — `runs/b13/b13_checklinks_before.log`, `_after.log`, `_2.log`.
> - The 71 tests of 5.7 pass unchanged against (b): none had locked in the old behaviour.
> - **Tests of the corrected behaviour** (test-author, 2026-10-11):
>   - `test_translation_validator.py` 71 → **96**: the source spelling in the `inline-code-missing` message, every anchor case against the render (explicit-id spellings, duplicates numbered after explicit ids, inline code vs raw-HTML ids, emoji shortcodes, front matter, BOM), `file_anchors`' cache per file version, and the fixtures checked against `render_anchors` instead of bare Python-Markdown. RED on HEAD's validator: 12 failed; on `page_anchors.py` without the BOM strip: 3 failed (the 3 BOM tests); 8 one-defect mutants of `page_anchors.py` each caught.
>   - `test_docs_links_gate.py` 29 → **37** (dev.py in child processes): the anchor verdict per language, an explicit id's text slug that is no anchor, `_mkdocs_page_anchors == file_anchors`, and dev.py without MkDocs (`--help` exit 0; `check-links` exit 1 with its message). RED on HEAD's dev.py: 5 failed.
>   - Runner descriptions (`_backend_utils.py`, M): translation-validator in C2 (batches 11-13, `page_anchors.py` in «Testing»), gate-docs-links in C3 (dev.py's anchor verdict, dev.py without MkDocs, `mkdocs.yml` read).
> - `developer/docs/translation-pipeline.md` (docs-writer, C2): the `anchor-missing` bullet said anchors were Python-Markdown slugs plus explicit ids; it now says they are the ids of the page's own MkDocs render, an explicit id replacing the text slug; the `inline-code-missing` message; a `Tests:` line for `utils translation-validator`.
> - **⚠️ Fuori pista — a byte-order mark hid a page's first heading** (found by the test-author while writing the tests): `validate_file` reads the translation with `utf-8`, so a leading `\ufeff` reached `render_anchors` and the first heading lost its id — an in-page `anchor-missing` false positive (HEAD had the same). The build reads with `utf-8-sig`. Fixed in `render_anchors` (`source.removeprefix("\ufeff")`), so both callers are covered whatever encoding they read with. No docs file has a BOM today.
> - Lint (`--config pyproject.toml`): `page_anchors.py` ruff 0, black clean (`functools.cache`; the lazy MkDocs imports carry `# noqa: PLC0415 — <reason>`, the repo's convention). `dev.py` ruff 43 findings, as on HEAD: the two lazy imports are marked the same way, and the pre-existing C901 of `cmd_mkdocs_check_links` goes from 19 to 20 with the import guard. `validate_translations.py` ruff 22, as on HEAD. Neither file was black-clean on HEAD (47 and 27 hunks, unchanged), and black would rewrite none of the added lines. `check-links` after the lint edits: the same 95 (`runs/b13/b13_checklinks_3.log`).

**5.5 ✅ Gates on the final tree** — 2026-10-11 13:01–13:04, lane 6158, one command at a time (load 15 → 44: other lanes busy); logs `runs/b13/b13_final_*.log`, summary `b13_final_gates_summary.txt`
> **Note implementazione**:
> - `utils translation-validator` 96 passed, `utils gate-docs-links` 37, `utils translation-cache` 38, `utils translation-code-blocks` 80, `check-orphans` clean; then `--workers 4 utils all` (dev.py changed, and several suites run it): **1428 passed**, 30 units, exit 0 (5.7's run: 1395; +25 validator, +8 gate).
> - `translate-validate --hide-localized` **0 errors, 0 warnings**; `translate-diff --issues-only` 624/624 clean; `translate-check` green (DeepSeek-V4.1-Flash via Doubleword); `translate --dry-run` «All files are up-to-date»; strict `mkdocs build` 0 WARNING/ERROR (59 s); `check-links` the same 95 valid links as before (b); `git diff --check` clean; ports 6158/6168 free.
> - **Commit by commit** (`release-pipeline/scripts/b13_stages.py`, read-only on the repo): three paths change in more than one commit (`_backend_utils.py` C1→C2→C3, the validator tests C1→C2, the cache C4→C5); their intermediate contents are snapshots in `release-pipeline/b13_commit_stages/`. `manifest` gives each commit's blob ids and the tree it must have (git tree hashing reproduced on `HEAD^{tree}`), and checks that the commits' paths are `git status`'s 24. `replay` rebuilds C1→C3 on a `git archive` copy and runs each stage's pure tests: C1 71 passed (on HEAD's validator), C2 243 (96 + HEAD's 29 gate tests + 80 + 38), C3 133 (96 + 37). The cache: C4 = HEAD minus the 29 `pending_langs`, nothing else; C4 → C5 changes only the 5 pages of this round (`import/scalable` new).
> - Stamp audit (`b11_stamp_audit.py`, `b11_stamp_port_check.py`): this round's only stamp, `user/brokers/index` ×3, ported every token the EN added.
> - **⚠️ Fuori pista — the port check had false positives:** it flagged `directa` ×3 (`3,000`) and `fifo-lot-analysis` it (`1000`), stamps older than this round; the translations have «3.000», «3 000», «1.000». Fixed in the script (numbers compared without digit grouping, as `inline-code-missing` does; a really missing number, e.g. 300 for 3,000, is still flagged): 0 pairs. The script now takes the audit and output paths, so batch 11's evidence stays as it was.
> - `translate-check` prints a masked fragment of the API key: redacted in the 4 logs that had it.

**5.9 ⏳ Third round** (coordinator 2026-10-11, after the respective trains; the cache stays M's):
> - I's EN pages, train 32: `portfolio-engine/deposited-capital`, `user/dashboard/charts`.
> - P's 2 user pages, batch 42: `financial-theory/instruments/transaction-types/adjustment` and `transfer` (P writes them in English only and does not stamp).
> - 5.4 after P's 2 keys (`transactions.errors.pairQuantityMismatch`, `pairAssetMismatch`), which come with batch 42's checkpoint.
> - The devWiki note `release-pipeline/b12_devwiki_stamps_hide_stale_translations.md` goes to the historian.

**5.9a I's pages** — base train 33 (`c0d933abf`, tree `4ea074465be5`, batch 13 merged as `3a2e14514`); logs `release-pipeline/runs/b14/`
> **Note implementazione** (triage, 2026-10-11 13:22):
> - Detectors: `translate-validate` 36 errors, 36 warnings, **all on I's 2 pages** (`charts` 2+2 per language, `deposited-capital` 10+10): S's pages, `scalable` and `brokers/index` stay clean (train 32 had 126 = these 36 + the 90 batch 13 cleared). `translate-diff` 6 files, 45 anomalies, same pages; dry-run 2 × 3 = 6 (~298K tokens).
> - Classified from the EN diff since the cached version (found by MD5: `charts` = `797a629d7`, the batch-11 run; `deposited-capital` = `de252a38a`, the batch-11 stamp); one commit since, I's `3801cf93e`:
>   - `user/dashboard/charts` +10/−1: the «Broker lines» paragraph rewritten (no jump at a transfer), 4 bullets (in transit, different ownership shares, no value on the arrival day, brokers outside the view), the closing sentence, a Theory link to `deposited-capital.md#internal-transfers-broker-lines`. **Small → by hand**: the pipeline would re-translate the whole page (~165K tokens) and undo batch 11's glossary review of the rest.
>   - `portfolio-engine/deposited-capital` +137/−4: a new H2 «Internal Transfers in the Broker Lines» (6 H3, display math, 3 tables, 2 worked examples), the What-Counts table and the `InKindCapital` paragraph rewritten. **Large → pipeline**: 1 page × 3 = 3 translations, ~132.6K tokens (in ~101.2K, out ~31.4K); `translate-check` green. Command sent to the coordinator; the developer launches it.
>   - Anchors: the new section's targets (`charts.md#pnl-line`, `index.md#2-valuation-price`) are shared explicit ids in all 4 languages; `#internal-transfers-broker-lines` is an explicit id on the EN H2, so the run carries it.
> - `charts` by hand (`release-pipeline/scripts/b14_charts_broker_lines.py`): it/fr/es with the page's own words (ambito / périmètre / ámbito, filtro broker / filtre de courtiers / filtro de bróker, the glossary's in transito / en transit / en tránsito, the sharing page's quote di proprietà / parts de propriété / porcentajes de propiedad); es says «títulos» for securities so that «valor» stays the value. Structure equal to the EN (220 lines, 30 bullets, 28 links, 132 bold, 68 blocks). Validate: only the expected `anchor-missing` on the Theory link, until the run writes the section. The stamp waits for the end of the run: both write `.translate-hashes.json`.

**Gallery — next remote pipeline run** (from D): the PAC shots of batch 12 predate D's fixes; check that the space in «ROUTING –» (`pac-step-routing`, desktop) and «Sintesi» / «Résumé» on the toggle (it, fr) show.

**5.9b ✅ Broken images in translations** — 2026-10-11 (coordinator 2026-10-11 13:3x, found by train 33's gates)
> **⚠️ Fuori pista — a defect my batch-13 gates missed:** the strict build printed «⚠️ 3 broken icon path(s)» (`static/icons/brokers/scalable.png`, `user/transactions/import/index` it/fr/es, from the second round); my check counted only WARNING/ERROR lines, and `dev.py` prints that list with ⚠️/❌ and still exits 0. From now on ⚠️/❌ in a build log are red for my gates.
> **Note implementazione**:
> - The coordinator's scan of every relative `<img>` in the built site: 21 broken, 7 per translation language, 0 in English — the 3 Scalable icons, and 18 older ones (since 2026-06-20) in `user/assets/providers/index` (×4), `css-scraper` and `scheduled-investment` (the icon is inside the H1). Reproduced on the batch-13 site with every tag that carries a file URL, not only `<img>` (`release-pipeline/scripts/b14_site_asset_scan.py`): the same 21, nothing else. All 440,200 relative page links resolve.
> - Cause, measured: `site/it|fr|es` hold only HTML (0 other files), so every file is served from the root, and a translated page is built one folder deeper. MkDocs rewrites Markdown images, not raw HTML: a raw-HTML relative URL copied from the English is always broken in a translation. The validator's `_is_expected_relative_depth_shift` accepted one more `../` but also the unchanged copy; `dev.py`'s post-build check looked only at `static/icons` and did not fail the build. No translation used the shift.
> - Fix (`release-pipeline/scripts/b14_shift_asset_paths.py`): one more `../` on the 21 references, in 12 files, only where the translation repeated an EN `src`; translation only, no stamp. Static check: the 28 raw-HTML relative `src` of the docs (7 EN, 21 translated) all resolve from their pages' build folders. Final proof (rebuild + scan, 0 in all 4 languages) after the pipeline run.
> - Prevention proposed to the coordinator, decision **(a) + (b), (c) no** (14:03, with the `dev.py` grant for the post-build check and `cmd_mkdocs_build`'s return code): (a) `dev.py`'s post-build check over every relative file URL (`img`/`source` `src`/`srcset`, `video` `src`/`poster`, `audio`, `<a href>` to a non-HTML file), failing `mkdocs build` with exit 1 — 3.7 s on 1,290 pages / 2,988 URLs; (b) `translate-validate`: a relative file URL copied unchanged from the English is an ERROR (`html-asset-depth`), with the expected value — never a false positive in this layout; (c) a deterministic pipeline step: not now. Tests via test-author in `test_docs_links_gate.py` and `test_translation_validator.py`.
> - **(a) implemented** (`dev.py`): `_relative_asset_urls()` + `_check_asset_paths_in_built_site(site_dir=None)` replace `_check_image_paths_in_built_site()`; every relative file URL of the built site (img/source `src`/`srcset`, video `src`/`poster`, audio `src`, `<a href>` to a non-HTML file), resolved from the page's folder like a browser (query/fragment dropped, percent-decoded, entities unescaped, HTML comments ignored); anything resolving outside the site is broken; `mkdocs build` returns **1** on a broken URL. 3.4 s on the site.
> - **(b) implemented** (`validate_translations.py`): `html-asset-depth` (❌ ERROR) — a raw-HTML relative file path (`src`, `srcset` candidates, `poster`, `href` to a file) copied unchanged from the English; code and HTML comments ignored; line numbers of the translation; the hint is the real path, computed from the page's build folder (`_translated_file_url`: directory URLs, `<lang>/` prefix; one more `../` only for a path that climbs to the root). HEAD's translations: 21; after the fix: 0 (624 pairs).
> - **⚠️ Fuori pista — a third false positive, found by the full validation:** `latex-inline-count` WARN on `deposited-capital` it/fr/es (148 vs 149): the extractor's suffix-currency rule (a digit before the `$`, «500 $») dropped `$A$` in the English «…on day 3 $A$'s line…» while the translations kept it. Inline math is now read as pymdownx.arithmatex reads it (smart dollar: no whitespace inside the delimiters, no unescaped `$` in the content); the suffix rule is gone. Corpus: old rule 3 mismatches (all false), new rule 0 over 624 pairs, no new mismatch anywhere.
> - **Tests** (test-author, same agent): `test_docs_links_gate.py` 37 → **60** (`TestBuiltSiteAssets` 20, `TestMkdocsBuild` 3), `test_translation_validator.py` 96 → **130** (`TestHtmlAssetDepth` 18 incl. the real-path hint and comments, `TestInlineMath` 15, registration 1). RED on HEAD `c0d933abf`: validator 23 failed (17 missing function, 6 behaviour), gate 22 failed (20 missing function, 2 behaviour); each refinement red on the version before it; 35 one-defect mutants all caught. GREEN on lane 6158: 130 / 60 / translation-code-blocks 80 / translation-cache 38 / check-orphans clean. Developer pages (docs-writer): `translation-pipeline.md` (`html-asset-depth`, four checks, the build's check, `Tests:`), `release-pipeline.md` (the build checks its own output).

> - Lint (`--config pyproject.toml`): `dev.py` ruff 43, `validate_translations.py` 22, as on HEAD (`check_latex` C901 20 → 19); the runner and both test files clean; black would rewrite none of the added lines. Commit split: 7 commits, intermediate contents in `release-pipeline/b14_commit_stages/`, replay on `git archive HEAD` green at every code stage (C2 156, C3 293, C4 308).

**5.9c ✅ I's pages after the run** (developer launch, 3/3, 0 failed, 5 min 25 s, ~132.6K tokens; log `runs/b14/b14_pipeline_run.log`)
> **Note implementazione**:
> - `deposited-capital`: validate 0 errors (the 3 `latex-inline-count` WARNs were the false positive above); diff clean. Review: it «riga/righe» (table rows) used for the chart lines in 17 places → «linea/linee» (the transaction and table rows stay «riga»); the H2 «…nelle righe dei broker» → «nelle linee per broker», as on `charts`; the formulas' numbers localized like es did (it `1.000`, fr `1\,000`, `0{,}5`: «1{,}000» reads as «1» in it/fr). The new section's link texts follow their targets (sharing page, valuation price, `#pnl-line`).
> - `charts` (hand port of 5.9a) stamped after the run: `translate --dry-run` «All files are up-to-date».

**5.9d ✅ Audit of the whole translated guide (part A)** — developer: «fare tutte le verifiche, comprese quelle di localizzazione»; scripts `release-pipeline/scripts/b14_*_scan.py`, logs `runs/b14/`
> **Note implementazione** (numbers on the final tree, 2026-10-11 14:52–14:59, lane 6158):
> 1. **Coverage:** 322 nav pages; 208 in it/fr/es, 114 English only by policy (Developer Manual), 0 missing, 0 English page outside the nav, 0 translation without its English. `nav_translations`: 48 labels per language had no entry (shown in English, e.g. «KPI Cards», «Charts», «Value at Risk»), 2 keys were stale (`Single`, `CLI Tools` renamed in the nav) and 11 values contradicted the glossary or the pages' titles («Drawdown Corrente/Actuel/Actual», «Trasferimento Titoli»…, «P&L del Periodo», «Immobiliare & P2P»): now 235 entries per language, 0 missing, 0 stale.
> 2. **Freshness:** stamp audit 166 pairs on 56 pages (an EN change before a stamp), port check 0 pairs with an EN token missing; masked-pair scan 624/624 after removing 4 legacy `failed` flags (`cash-transfer` it/fr/es, `revolut` es, June runs) whose content was verified current (the EN's new carousel and steps are in every translation); `translate --dry-run` nothing pending.
> 3. **Structure:** `translate-validate` 0 errors, 0 warnings (624 files); `translate-diff` 624/624; `translate-check` green.
> 4. **Built site:** strict build 0 WARNING/ERROR and 0 ⚠️/❌; `check-links` 95; asset check 2,988 relative asset URLs resolve, 0 broken in en/it/fr/es; `anchor-missing` 0.
> 5. **Localization:**
>    - glossary (the conflict table over every page): 223 hits read by sense → 7 deviations fixed (fr «Drawdown depuis le sommet» → «Repli…» ×2, fr mobile gallery «fractionnement» → «division» ×4, es «pérdidas y ganancias (P&L)» → «P&L»), 216 legitimate (rate «tasa», preview «aperçu», bank transfers, the app's own «Benchmarks Synthétiques», third-party labels);
>    - text left in English: fr FIFO H1, `danske-bank` fr (a sentence and 5 wizard labels: the app's «Séparer le prix des frais ?», «Appliquer la correction», «Suivant : Sélectionner», «Téléverser»), fr «Lignes de l’espace de travail : …», 3 link texts «… on Wikipedia/StockCharts», `snb` it admonition title; short attributes: 15 fixed (alt «About»/«Profile», `form.it` captions and alts «BUY…» → «ACQUISTO…», the dashboard «Allocation» caption), 25 fr favicon alts aligned («favicon de/d'/du …»); the rest are names (PDF, EMA, RSI…) or the same word (fr «Simulation», «Image»); the validator's `text-untranslated` 0;
>    - French typography: 78 missing spaces added («5,18 %», «ex. :», «X %»); a first pass touched 4 CSS `width: 100%` lines inside multi-line tags — reverted, script hardened (an unclosed tag is skipped to its `>`);
>    - numbers in the prose: 234 written in the English format localized in 52 files (it/es `28.398`/`5,18`, fr `28 398`/`5,18`); kept: versions (Tailscale 1.78, LibreFolio 1.2), AGPL-3.0, formulas; formulas: the English thousands `1{,}000` (read as «1» in it/fr/es) localized in 12 places (`deposited-capital` it/fr, `pac-allocator` it/fr/es); dates: 0 English month names, 0 slash dates (ISO only);
>    - Spanish register: 17 pages addressed the reader as «usted» (older import guides): now «tú» like the rest of the guide and the app (115 lines, one for one; structure identical);
>    - UI words as the app writes them: the full scan is 5.4 (part B); the English leftovers above are fixed now.
> - **⚠️ Fuori pista:** the copy of `b11_glossary_scan_ci.py` first overwrote batch 11's `runs/b11_glossary_scan_ci.json` / `_contexts_ci.txt` (outside the repo): regenerated from batch 11's tree (`ac6ddd452`, `git archive`), the b14 run filed under `runs/b14/`.
>
> **Open, with the reason:**
> - 5.4, the full scan of bold/italic labels against the catalogues, and P's pages (`adjustment`, `transfer`, the new link to «Cost Basis Override»): part B, after train 34 (P's keys and pages). Known items: it `transactions/index` «Dividi coppia», «Ho capito», the dialog title; es «Añadir transacción», the dialog title; it `danske-bank` «Caricamento» (the app: «Carica»); `pac-allocator` «Sintesi/Résumé», «Torna a Riepilogo».
> - **French non-breaking spaces**: a plain (breakable) space before `: ; ? ! %` in 3,630 places on 207 pages, U+00A0 nowhere, and every pipeline run writes plain spaces — a convention decision, not a fix: (a) normalize the sources + a validator check + a pipeline step, (b) a build hook that applies French typography to the fr pages' HTML (no source change, future runs covered), (c) keep the plain space. M recommends (b).
> - **Decimals inside formulas**: 318 in 66 files keep the international dot (`$1.50$`); the thousands are localized. Whether formulas use the decimal comma (`0{,}5`, as `deposited-capital` now does) is a convention to decide.

**After 1.2 — section M of `Phase_0/BACKLOG_POST_1.2.md`** (rule of train 36; the coordinator transcribes these lines until the realignment, then M writes them in its section):
> - **M-4 · Lo spazio insecabile della tipografia francese** — medio; M, 11/10: solo se la decisione non entra nella 1.2. Dettagli: questo piano, sezione «5.9d», «Open».
> - **M-5 · La virgola decimale nelle formule** — basso; M, 11/10. Dettagli: questo piano, sezione «5.9d», «Open».
> - **M-6 · Il `../` di `srcset` e `poster` in `html-attr-mismatch`** — minimo; docs-writer di M, 11/10: `_is_expected_relative_depth_shift` accepts the extra `../` only for `src`/`href`, so a corrected `srcset` or `poster` would warn; no page uses them today.
> - **M-7 · La guida dei plugin BRIM e le favicon locali** — minimo; docs-writer di M, 11/10: `developer/architecture/patterns/brim_plugin_guide.md` (~1515–1531) has authors copy a card with `<img src="<favicon-url>">` into every `index.<lang>.md`; a local relative favicon needs one more `../` in the translations. English page: for its owner's section.
> - Details for two existing lines: the `../` pipeline step — the prompts (`prompts/short_article/step3_user.txt:16`, `step4_user.txt`/`step5_user.txt:28`) require `src`/`href` copied verbatim, so re-translating the 4 pages with local raw-HTML images brings the copy back (`html-asset-depth` reports it); the stamp audit — together with the masked-pair scan, its three scripts live outside the repo (`release-pipeline/scripts/b11_stamp_audit.py`, `b11_stamp_port_check.py`, `b11_masked_scan.py`).
