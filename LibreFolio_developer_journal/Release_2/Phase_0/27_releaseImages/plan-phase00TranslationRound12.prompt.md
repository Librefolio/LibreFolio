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

### 5. ✅ Second round — prepared 2026-10-10 (batch 12), run in batch 13 on train 31 (`f4a42bf4a`); its third round (5.9) closed in batches 14–15, 2026-10-11

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

**5.9 ✅ Third round** (coordinator 2026-10-11, after the respective trains; the cache stays M's) — closed 2026-10-11: I's pages in 5.9a–5.9c, P's pages and 5.4 in step 6, the devWiki note in step 7:
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

### 6. ✅ Part B and the French typography hook — batch 15, on train 37 (`41ddc61cb`), 2026-10-11 (checkpoint B)

> Coordinator 2026-10-11 17:57: batch 14 merged as `6fa720752`. Developer's decision, verbatim: «Hook di build per il francese nella 1.2, mentre I fa F; decimali nelle formule col punto (Consigliato)». The hook applies French typography only to the HTML of the French pages, never to the sources; it never touches `code`, `pre`, `kbd`, `script`, `style`, attributes, URLs or formulas (`arithmatex`). Tests: unit tests of the hook with positive and negative cases, strict build, `check-links`; a section on the pipeline's developer page. M-5 (decimals in formulas) stays after 1.2.

**6.0 ✅ Detectors on train 37** (`release-pipeline/runs/b15/b15_*_0.log`): `translate-validate` 6 errors, 15 warnings; `translate-diff` 6 pairs; dry-run 4 pages × 3. All four are small drifts since their cached version (found by MD5): `user/brokers/index` +2 (I's «Gain/Loss» paragraph and its link to `deposited-capital#internal-transfers-broker-lines`), `user/transactions/form` +1/−1 (P, the Manual cost of 0), `transaction-types/adjustment` +5/−3 (P: promote rule, the override of zero, the mandatory cost basis, the link to `#cost-basis-override`), `transaction-types/transfer` +2/−2 (P: the storage of a pair, the promote rule) → by hand in it/fr/es and stamped; no pipeline run.

**Plan**
1. **Hook** `mkdocs_src/hooks/fr_typography.py`, registered under `hooks:` in `mkdocs.yml`. Event `on_page_content`, only when `page.file.locale == "fr"` (mkdocs-static-i18n: the language of the source file; an English fallback page in the French build has `en`). It changes only the plain whitespace that already stands before `:` (U+00A0) and before `; ? !` (U+202F), before `%` and before a currency symbol after a number (U+202F), inside `« »` (U+00A0) and between thousand groups (U+202F); it never inserts a space. Text nodes only: tags and attributes pass through byte for byte; comments and the content of `code`, `pre`, `kbd`, `samp`, `var`, `textarea`, `script`, `style`, `svg`, `math` and of any element of class `arithmatex` are skipped. The TOC titles (`page.toc`, rendered by the theme) get the same treatment.
2. **Tests** (test-author): `backend/test_scripts/test_utilities/test_docs_fr_typography.py`, runner action `utils docs-fr-typography` (M writes `_backend_utils.py`).
3. **Proof**: two real builds of the site, without and with the hook: the en/it/es pages byte-identical, the fr pages different only in text whitespace; 0 plain spaces left before the signs in the fr pages' text.
4. **Developer page** (docs-writer): a section in `developer/docs/translation-pipeline.md`.
5. **Part B**: the 4 pages above; 5.4 with P's keys; section M of `BACKLOG_POST_1.2.md` (M-4: «nella 1.2, decisione del developer dell'11/10»).
6. **Gates**, then checkpoint B (with my view on the full pipeline run the developer wants).

**6.1 ✅ The hook** — 2026-10-11
> **Note implementazione**:
> - `mkdocs_src/hooks/fr_typography.py`, registered under `hooks:` in `mkdocs.yml`. `typeset(text)` replaces plain whitespace already standing before `:` (U+00A0), `; ? !` (U+202F), `%` and a currency symbol after a number (U+202F), inside `« »` (U+00A0) and between thousand groups (U+202F); a sign counts only when followed by a space, the end of the text, closing punctuation or an entity, and no space is ever inserted. `typeset_html` tokenizes tags with quoted attribute values (a `data-title` holding `<img …>` stays one tag) and skips comments, `code`/`pre`/`kbd`/`samp`/`var`/`svg`/`math`, `script`/`style`/`textarea` up to their end tag, and any element of class `arithmatex`.
> - `on_page_content`: only `page.file.locale == "fr"` (mkdocs-static-i18n: the language of the source file; the English fallbacks of the French build have `en`), content and `page.toc` titles («Étape 1 : …» in the sidebar TOC).
> - **⚠️ Fuori pista — the theme renders French labels outside the content**: a first real build left 2,576 plain spaces before signs, all one sidebar label («📉 Jusqu'où Peut-on Perdre ?», twice per page). Hence `on_nav` at priority −110, after mkdocs-static-i18n's −100: in the French build only, nav titles that are values of the French `nav_translations` are typeset (sidebar, tabs, header, `<title>`; the site has no footer links: `navigation.footer` is off); the English Developer Manual labels stay as they are.
> - **⚠️ Fuori pista — the proof itself**: `del config.plugins[name]` does not unregister a plugin's event handlers in MkDocs 1.6, so the first «without» build still ran the hook; the proof now removes its handlers from every event.
> - **Proof** (`release-pipeline/scripts/b15_hook_proof.py`, two real builds into /tmp, 40 s each): every en/it/es file byte-identical (only `search/search_index.json` differs, as it holds the French text); in all 322 French pages the two versions differ only in whitespace, with identical start tags (attributes included) and identical code/pre/kbd/script/style/formula content (checked with `html.parser`, independently of the hook's tokenizer); plain whitespace before `: ; ? ! %` in the French text: 6,575 → **0** in pages from a French source (final tree, after 6.3: 6,580 → 0, `runs/b15/b15_hook_proof_final.txt`) (28 remain in the English text of the English fallback pages, by design).
> - Runner action `utils docs-fr-typography` (M, `_backend_utils.py`).
> - **Tests** (test-author): `backend/test_scripts/test_utilities/test_docs_fr_typography.py`, **191 tests** (rules with exact code points, what is left alone, `typeset_html` on every skipped element and nesting, invariants over site-shaped samples, the i18n plugin's own `locale`, `on_page_content`, `on_nav` with stubs and through MkDocs' real plugin collection, the hook in the site configuration, a French page rendered in memory with the site's Markdown extensions). 36 one-defect mutants, each caught. The developer page section: `developer/docs/translation-pipeline.md` «🇫🇷 French Typography» (docs-writer), plus its stale Overview counts (36 → 208 sources, 108 → 624 translations).
> - **⚠️ Fuori pista — a bug the tests found**: a `<!--` inside `script`/`style`/`textarea` made the precomputed `finditer` skip the real tags after it (their attributes typeset). Fixed: tokens are searched from the current position. Also decided on the test-author's open points: `%` takes any whitespace before it (`<strong>50</strong> %`), and `iframe`/`noembed`/`noframes`/`xmp` are raw text too.

**6.2 ✅ Part B pages, by hand** — 2026-10-11
> **Note implementazione**: `user/brokers/index` it/fr/es: I's «Gain/Loss» paragraph with the app's labels (it «Gain/Loss», fr «Gain/Perte», es «Ganancia/Pérdida»; the percentage quoted as the app shows it, «0.00%»: `BrokerCard` uses `toFixed(2)%`, a product defect for P) and its link to the internal transfers; `user/transactions/form` it/fr/es line 39 (0 only for units that really cost nothing, such as the new shares of a split; for a gift, the donor's cost); `transaction-types/adjustment` it/fr/es (the promote rule, an override of zero, the unknown cost without override, the mandatory cost basis, the link to «Cost Basis Override» with each language's heading: it «Override del costo di carico», fr «Remplacement du coût de base», es «Anulación del coste base»; es «costo» → «coste» in the two bullets touched); `transaction-types/transfer` it/fr/es (how a pair is stored, the promote rule; es «Restricciones de Promote» → «de promoción», the table's «Promocionar» → the app's «Promover»). Validate 0 errors, 0 warnings; diff 624/624; the four English pages stamped; dry-run nothing pending.

**6.3 ✅ 5.4, UI labels against the catalogues** — 2026-10-11 (`release-pipeline/scripts/b15_ui_label_scan.py`)
> **Note implementazione**:
> - Scan: bold and italic spans paired by position with the English page's; when the English span is a label of the English catalogue, the translation must be that key's label (case-only differences ignored; links skipped — they name pages; catalogue patterns only for counts in brackets, «Save all ({n})»). ~6,100 labels checked; **1,367 differ**: 1,150 in user/admin/gallery/community pages (271 left in English, the rest paraphrased), 217 in theory pages, where the bold marks concepts, not quotes (left).
> - Review row by row, one reviewer per language (brief `release-pipeline/b15_label_review_brief.md`): quote the app's label and fix the grammar around it; concepts and brand names stay; app-versus-glossary conflicts recorded for the catalogues' owners.
> - Questions to the coordinator: it «AI Export» (glossary) vs the app's «Export AI»; es plural «brókers» (129) / «brókeres» (79, the app and the RAE). Answers: it «AI Export» stays until the developer decides; es «brókeres», yes.

> **Results**:
> - Review, one reviewer per language, two rounds (the second on the 155 rows of pages the first scan could not pair, then paired block by block): it 392 labels replaced, fr 349, es 318, each with the grammar around it; kept as concepts it 60, fr 49, es 51; it «AI Export» kept (10, developer's decision pending); app-versus-glossary conflicts recorded and sent to the coordinator by catalogue key (34). Plus by hand: the `danske-bank` fr English leftovers (wizard labels, «(détecté)», «Conserver les N lignes restantes telles quelles»), «⚡ Valider maintenant», form «À»/«De»/«A», the Support button in the three About pages, the data-quality «Synchroniser/Sincronizar» on the dashboard and correlation pages, it «Verifica a fine periodo», es «Combinar», fr «Journalière», fr «Versement».
> - **es plural «brókeres»** (coordinator, the app and the RAE): 120 words in 38 files; none left.
> - Final scan (`runs/b15/b15_ui_labels_final2.tsv`): 399 rows still differ. 248 are in theory pages, where the bold marks concepts (post-1.2, M-8). 151 are in user, admin and community pages, all decisions kept on purpose: 150 recorded, and the 151st, es «Todo» for the English «MAX», is right, because the app's button says «All».
> - **⚠️ Fuori pista — the scanner**: placeholder-only catalogue values («{month}») matched any label (first run: 0 differences), then «max {amount}» matched «Max Drawdown» (patterns now only for counts in brackets); italic line numbers were counted on a different string; links name pages, not labels (skipped). Fixed in `b15_ui_label_scan.py`.
> - Catalogue and product defects found, sent to the coordinator (P's mini-batch): es `pairQuantityMismatch` «un broker»; `BrokerCard` `toFixed(2)%`; fr/es «Comparaison des donnees» / «Comparacion»; fr «Téléchargés» for upload; es double «Combinar»; English hard-coded in `DataEditor.svelte`, `ChartAestheticsSection.svelte`, `DateRangePicker.svelte`. EN accuracy, for the English pages' owners: `user/assets/detail/chart` says **MAX** where the app shows «All»; `asset-types/other` names a «Manual» asset provider that does not exist.

**6.4 ✅ Gates** — 2026-10-11 19:03–19:15, lane 6158 (`release-pipeline/runs/b15/b15_final_*`)
> **Note implementazione**: `utils docs-fr-typography` 191, `translation-validator` 130, `gate-docs-links` 60, `translation-cache` 38, `translation-code-blocks` 80, `check-orphans` clean, `--workers 4 utils all` **1676 passed**; `translate-validate` 0 errors, 0 warnings; `translate-diff` 624/624 (a first run found es `correlation` one bold short: the reviewer had merged the two data-quality buttons into one quote — restored, and it/fr aligned to the banner's own label); `translate-check` green; dry-run nothing pending; strict build 0 WARNING/ERROR, 0 ⚠️/❌, «All 2988 relative asset URL(s) in the built site resolve»; `check-links` 95; asset scan 0 broken in 4 languages; masked-pair scan 624/624; coverage complete (235 nav labels per language, 0 missing); stamp audit 169 pairs, port check 0; hook proof PROOF_OK (6,580 → 0); `git diff --check` clean; ports 6158/6168 free.

**6.5 After 1.2 — section M of `BACKLOG_POST_1.2.md`** (M-4 marked ✅ «nella 1.2, decisione del developer dell'11/10»; new lines M-8, M-9).

**6.6 ✅ Checkpoint B** — 2026-10-11 (`release-pipeline/scripts/b15_stages.py`, read-only on the repo; manifest `release-pipeline/b15_commit_manifest.txt`, proposal `release-pipeline/commit_proposal_B15.txt`)
> **Note implementazione**:
> - Four commits, 222 paths (= `git status`), messages ASCII only: C1 the hook, its tests, the runner action, `mkdocs.yml`, the developer page (5); C2 the 12 part-B translations as HEAD plus the hand port only (snapshots in `release-pipeline/b15_commit_stages/c2_part_b/`, with SHA256SUMS) and the cache's four stamps (13); C3 every other translation, and 8 of the 12 part-B files again with their label and plural edits (210); C4 this plan and the backlog (2).
> - Replay on `git archive HEAD` with the shared venv: after C1, the five pure suites **499 passed** (191 + 130 + 60 + 80 + 38). The state after C2, before the label edits, checked alone (`b15_c2_state_check.py`): validate 0 errors, 0 warnings; diff 624/624; dry-run nothing pending.

### 7. ✅ Batch 16: P's labels, the developer's terms, the English accuracy pages, the Spanish register — on train 38 (`b578f4fec`), 2026-10-11 (checkpoint)

> Coordinator 2026-10-11 20:56: batch 15 merged as `9245ffb6f` (commits `a965956ab`…`e6f2df614`); train 38 = `b578f4fec` brings T (B3b) and P's audit mini-batch (`fix(i18n): localize broker percentages and labels`). Developer's decision, verbatim: «in italiano preferisco AI export» → the it catalogue follows the guide and the glossary. **M is assigned the i18n catalogues** for the value changes the developer decides, through `dev.py i18n`; his choices on the other 13 terminology rows come next, in this batch. Approved earlier (19:42): (a) the «Manual» provider on 5 asset-type pages, with `real-estate.en.md:22`'s wording and **No Provider**; (b) Borsa Italiana in the rows of `stocks`, `etfs`, `bonds`, `mutual-fund`; (c) «MAX» in `user/dashboard/index.en.md:51,109`; (d) `chart.it/fr.md:61` «Tutti»/«Tout»; the es «usted» forms, translation only, no stamp. F's pages (`positions`, `kpi-cards`, `deposited-capital`, `book-value`) are not M's.

**Plan**
1. Catalogues: the developer's decisions (`dev.py i18n update`), key parity and the i18n gates.
2. The guide's quotes realigned to the new labels: P's mini-batch and the catalogue decisions (`release-pipeline/scripts/b16_catalog_delta.py`, then the label scan).
3. English accuracy (docs-writer, brief `release-pipeline/b16_docs_writer_brief.md`), then it/fr/es by hand and the stamp.
4. Spanish register: the «usted» forms left in theory pages and one user page (`release-pipeline/runs/b16/b16_es_usted_classified.tsv`).
5. Gates, then the checkpoint.

**7.1 ✅ Catalogues and glossary — the developer's decisions** — 2026-10-11
> - it «Export AI» → «AI Export»: `assetDetail.aiExport`, `dashboard.aiExport`, `fxDetail.aiExport` (`dev.py i18n update KEY --it "AI Export"`; 3 lines in `it.json`, nothing else). The other 7 Italian `aiExport.*` values already said «AI Export»; no code or test reads the old value. The guide's 10 quotes stay as they are (they already say «AI Export»).
> - **The other 13 rows** (coordinator 21:37, developer verbatim: «applica tutti i tuoi consigli»), through `dev.py i18n update` (log `release-pipeline/runs/b16/b16_i18n_decisions.log`): es `dashboard.allocation` «Asignación de activos»; fr `dashboard.feesAndTaxes` «Frais et impôts»; `chartSettings.staleGradient` it «Gradiente dati obsoleti», fr «Dégradé données obsolètes», es «Degradado datos obsoletos»; es `signals.riskDrawdown.name` «Caída desde el máximo»; `risk.levels.l4.shockShowDetail` fr «Afficher le choc par catégorie», es «Mostrar el choque por grupo»; it `transactions.form.costBasis` «Costo di carico manuale» (`transactions.fields.cost_basis_override` already said so); it `onboarding.errors.loadTitle` «Non siamo riusciti a caricare le guide»; es `settings.defaultCurrency` «Divisa predeterminada», `csvImport.headerMismatch` «Las divisas del encabezado no coinciden»; es `brokers.sharing.demoteToViewer` «Cambiar a lector»; es `risk.actions.runReplay` «Ejecutar repetición»; es `assetDetail/dashboard/fxDetail.aiExport` «Exportación IA». Rows 3 (`dashboard.unrealizedDelta`) and 6 (FX Pair Analysis) keep the app.
> - **Sibling keys**, the same decision applied with coherence (coordinator: «sì a tutte»; log `b16_i18n_siblings.log`): fr/es `risk.levels.l4.shockHideDetail` (the same toggle); es `settings.globalSettingDescriptions.default_currency` (the same setting); es «visor» → «lector» (`brokers.sharing.demoteConfirm`, `selfDemoteDone`: the role is «Lector»); es «reproducción» → «repetición» (`risk.replay.title`, `.exclude`, `.results`, `.treatment.omitted_from_replay`); fr «taxes» → «impôts» (`importWizard.fixStep.groupCharges`, `groupChargesHint`, `importWizard.brimNotice.scalable_fees_unknown` ×3, `aiExport.dataset.portfolio.performance_flows.description`; «Impôts et taxes», duties, stays; `{taxes}` is a placeholder); it «onboarding» → «guide» (`onboarding.errors.degraded`, `progressUnavailable`). Total: es 19 lines, fr 8, it 8; key parity 4,347 × 4; canonical form; Vitest `src/lib/i18n/` 17 passed (the ICU plural changed in fr).
> - **⚠️ Fuori pista — the glossary, rows 3 and 6**: the literal instruction (unrealized P&L → «P&L non realizzato») would have put the glossary against the app, which says «P&L latente / latent» for `dashboard.unrealizedPnl` (51 times in the guide) and «non realizzata / non réalisée» only for «Unrealized change»; likewise the app writes «paire FX» and «paire de devises» 14 times each. Agreed with the coordinator: two entries added, nothing changed — «unrealized change» → «variazione non realizzata / variation non réalisée / variación no realizada», «FX Pair Analysis» → «Analisi della coppia FX / Analyse de la paire de devises / Análisis del par de divisas» (169 terms). The translation cache hashes only the English source: no page reopens.
> - Not touched: the `datePicker.presets` block (T adds `datePicker.presets.days` for the tables' «Δ 1D»).

**7.2 ✅ The guide's quotes realigned to the new labels** — 2026-10-11 (scripts `release-pipeline/scripts/b16_*.py`, each edit checked on its line before writing; translations only, no stamp)
> - **Tool** `b16_catalog_delta.py REPO BASE NEW` (`NEW = WORKTREE` reads the catalogues on disk): changed keys → the docs of that language quoting the old value; added keys → translations still quoting the English. Validated on history: D's glossary commit `cd0b404d2` 31 candidates with the docs of that time → 17 today; the FX strings `0cc4a5077` 8 → 0.
> - **P's mini-batch** (`41ddc61cb` → train 38; delta 22 candidates, all quotes; label scan: 21 new rows, 19 gone — the 11 it «AI Export», «Comparación/Comparaison», «Nuovo/Nuevo»): 21 edits on 12 pages (`b16_p_labels.py`) — fr «Rapports téléversés» ×4, «Recadrer et téléverser»; es «Sincronizar tipos de cambio» ×2, «Editar tipos de cambio» ×2, the FX editor's column «Tipo de cambio» (`fx.rate`, `FxDataEditorSection.svelte:58`) and its badge «Modificado» ×2, «Bróker para subidas», «Informes del bróker» ×3, «Asignar brókeres», the pair button «Unir» ×3 (`transactions.promoteSuggest.merge`; «Combinar» stays `mergeAllCombine`) and «Unir todos». Prose, by the English sense of each line (`b16_prose_terms.py`, 9 edits): fr upload → «téléverser» in 5 places (85 «télécharg*» read: the other 80 mean download); es «tipos de cambio» in `risk.es.md:131` and the link to the FX page («💱 Tipos de cambio», its title); 151 es «tasa(s)» read: interest, growth, return, tax and risk-free rates and the indicator ROC stay.
> - **Durations** (`b16_duration_labels.py`, 34 edits on 12 pages): date range and rolling-return window it/fr «1W…2Y/10Y» → «1S…2A/10A», with `chart.it/fr.md:61` «MAX» → «Tutti»/«Tout» (approved d); es three lines were wrong already (`fx/detail/chart.es.md:27`, `returns.es.md:132`, the alt of `chart.es.md:25`). The dashboard's candle widths, localized since 2026-09-22 (`datePicker.granularity.*Short`: days it G, fr J, es D) and missed by 5.4: it «1G…1A, 3G, 2S», fr «1J…1A, 3J, 2S» (es was right).
> - **⚠️ Fuori pista — two duration sets still hard-coded**: the AI Export period (`frontend/src/lib/features/ai-export/ui.ts:60–63`, «3M/6M/1Y») and the tables' «Δ 1W…5Y» columns (`AssetTable.svelte:252`, `FxTable.svelte:233`). Coordinator: T localizes them after FE1 with `datePicker.presets.*` (plus `datePicker.presets.days`, «Δ 1D»); M's 7 lines wait for T's checkpoint (`user/assets/index` ×3, `user/fx/index` ×2, `user/ai-export/index` fr/es).
> - **The developer's decisions** (delta `b578f4fec` → worktree: 69 candidates, 45 lines; `b16_decision_labels.py`, 47 edits on 37 pages): es «Exportación IA» ×12, «Divisa predeterminada» ×11 (with two gallery captions and an alt), «Ejecutar repetición» ×2 (+ «pulsa» where the verb was missing), «repetición histórica», «Cambiar a lector» ×2, «Asignación de activos» ×2, «Caída desde el máximo» ×3, «Mostrar el choque por grupo», «Degradado datos obsoletos» ×2, «Las divisas del encabezado no coinciden»; fr «Dégradé données obsolètes» ×2, «Frais et impôts» ×2, «Afficher le choc par catégorie»; it «Gradiente dati obsoleti» ×3, «Non siamo riusciti a caricare le guide», «Costo di carico manuale». Left: es «reproducción diaria» (the engine's replay), «visor» for the PDF and detail viewers, fr theory «compartiment» (the concept, not the toggle).
> - **«Rolling return» as the app says it** (coordinator: yes, in this batch; `b16_rolling_term.py`, 43 edits on 13 pages): it «Rendimento rolling» → «Rendimento mobile» (21; plural «rendimenti mobili»), es «Rentabilidad móvil» → «Rendimiento móvil» (22; agreement «un… otro… anualízalo», «los rendimientos móviles»). Headings changed have explicit ids or no incoming links. fr «Rendement glissant» already matched. **⚠️ Fuori pista — a 5.4 residue**: the batch-15 scan pairs bold/italic spans and skips links and plain text, so a mode named in a link or a caption escaped it; noted in M-9.

**7.3 ✅ English accuracy (a–d), ported and stamped** — 2026-10-11 (brief `release-pipeline/b16_docs_writer_brief.md`)
> - docs-writer, 11 changes on 9 English pages, each line checked against the brief before editing: `user/assets/detail/chart.en.md:61` **MAX** → **All** (`datePicker.presets.max`; the app has no «MAX» label); `user/dashboard/index.en.md:51` «presets from **1W** to **All**», `:109` «(MAX)» dropped; no «Manual» asset provider: `other.en.md:15,36` and the «Typical providers» rows of `commodities`, `crypto`, `mutual-fund`, `bonds` → «or prices entered by hand in the Data Editor» (`real-estate.en.md:22`'s wording) and «Tick **No Provider**…» (`assets.provider.noProvider`); Borsa Italiana added to `stocks`, `etfs`, `bonds`, `mutual-fund` (`borsa_italiana.py:76–95`). Also `chart.en.md:5` «_Last updated_» (the only one of the 9 pages with a date). Strict build 0 WARNING/ERROR, 0 ⚠️/❌, 2,988 asset URLs; `check-links` 95.
> - **⚠️ Fuori pista**: the first docs-writer run failed on a network error (DNS) before its first turn — nothing touched; relaunched.
> - Port by hand (`b16_en_accuracy_port.py`, 34 edits on 28 pages): rows and `other:15` with the phrases the translations already use in `real-estate` (it «o prezzi inseriti manualmente nell'[editor dati]», fr «ou prix saisis manuellement dans l'[éditeur de données]», es «o precios introducidos a mano en el [Editor de datos]»); `other:36` like `user/assets/providers/index` («Seleziona **Nessun Provider**…», «Cochez **Pas de Fournisseur**…», «Marca **Sin Proveedor**…», which also leaves the es «usted»), and `providers/index.es.md:73` «Sin proveedor» → the app's «Sin Proveedor»; dashboard «da **1S** a **Tutti**», «de **1S** à **Tout**», «de **1S** a **Todo**», «(MAX)» dropped; the three chart dates. `chart.it/fr.md:61` «Tutti/Tout» came with 7.2.
> - Kept: `real-estate` it/fr/es translate «Scheduled Investment» (the nav and the provider pages do too, the tables keep the English name: 12/11/11 occurrences) — a naming choice, not this batch's (post-1.2, M-10).
> - `translate-validate` 0 errors, 0 warnings; `translate-diff` 624/624; dry-run listed exactly the 9 pages × 3 → `translate-stamp` on each; dry-run «All files are up-to-date»; the cache changes in those 9 entries only.

**7.4 ✅ Spanish register: «usted» → «tú»** — 2026-10-11 (coordinator: yes, translation only, no stamp)
> - Imperatives and «usted» (`b16_es_usted_scan.py`, a gap of the batch-14 audit, which converted the user import guides only): 29 forms on 22 pages, 28 in theory pages and `user/settings/index.es.md:3` («le permite… si es administrador») → `b16_es_register.py`, 30 edits (`other.es.md:36` went with 7.3; `transfer.es.md:37` «costo base» → «coste base», the glossary's).
> - **⚠️ Fuori pista — the imperative scan saw a third of it**: possessives «su/sus» meaning "your", third-person verbs whose subject is the reader («si realizó depósitos», «aportó»), «le» = you. A marker scan against the English line («you/your») gave 85 candidates; a reviewer read each in context: 24 lines usted (35 edits, plus 6 on 4 neighbouring lines the scan missed: «le cuesta», capitalised «Sus…»), 61 not («su» = its, a third-person subject, impersonal «se», «cada uno de ustedes»). The scans pair lines by number, so the 68 pages that do not line up with their English were skipped: the reviewer read the 10 with markers in full — 42 edits in 5 pages (twrr 20, mwrr 15, `instruments/index` 3, `asset-allocation` 2, `sortino-ratio` 2), 5 clean. `b16_es_register_2.py`: 83 edits, from `runs/b16/b16_es_register_review*.tsv`.

**7.5 ✅ Lost headings and paragraphs** — 2026-10-11 (found by the register review; `b16_restore.py`)
> - **Headings missing their first word**: commit `2544a3e36` (2026-08-05, «Fix translation inconsistencies», emojis added to headings) replaced the first word of 98 headings in 35 files instead of prefixing it («### Comparación con el ROI Simple» → «### 📉 con el ROI Simple»). Later runs re-translated most pages; still broken today: 37, in `mwrr` it/fr/es (all 8 H3 — plausible ones too, «📈 Annualizzato», «🧾 KPI»), `timing-effect` it/fr/es (4 each), `fifo-lot-analysis.it.md:248`. Restored with the wording before that commit, after the emoji; the anchors linked from elsewhere are explicit ids, untouched. (The developer page `ai_export_probe_workflow.md:67` matched too, but there the commit renamed an emoji heading: not a truncation.)
> - **Two English paragraphs missing in all three translations** (capital-baseline deltas: `twrr.en.md:6`, `mwrr.en.md:88`), hidden because the pages' stamps were current — the case of the batch-12 devWiki note. Translated with the wording of `deposited-capital` and `roi` (base del capitale / référence de capital / base de capital; in natura / en nature / en especie).
> - Spanish errors: `mwrr.es.md:121–123` «Día 0/5/10» → «Año» (the example counts years), `:56` the Italian «Ora» → «Ahora», `twrr.es.md:15` «Per definición» → «Por definición», `how-to.es.md:150` «Únifícalo» → «Unifícalo».
> - Translation only, no stamp (the English pages did not change).

**7.6 ✅ Gates and checkpoint** — 2026-10-11 22:12–22:24, lane 6158, one command at a time (load 6 → 54: other lanes busy); `release-pipeline/scripts/b16_final_gates.sh`, logs `runs/b16/b16_final_*`
> **Note implementazione**:
> - Tests: `utils gate-i18n-usage` 195, `docs-fr-typography` 191, `translation-validator` 130, `gate-docs-links` 60, `translation-cache` 38, `translation-code-blocks` 80, `check-orphans` clean, `--workers 4 utils all` **1676 passed**; Vitest `src/lib/i18n/` 17 passed.
> - Translations: `translate-validate` 0 errors, 0 warnings; `translate-diff` 624/624; `translate-check` green; dry-run nothing pending. Site: strict build 0 WARNING/ERROR, 0 ⚠️/❌, 2,988 asset URLs resolve; `check-links` 95; asset scan 0 broken in 4 languages.
> - Audits: masked pairs 624/624; coverage complete (235 nav entries per language); copied numbers and attributes as in batch 15; glossary scan 227 → 214 hits (the decided terms; the restored «Card dei KPI» first added one — aligned to the glossary and the page, «Schede KPI», and es «Efecto Timing en el MWRR» like its page); label scan 399 → 370 rows (user/admin pages 151 → 133, all decided; one new theory row, «tasa» = frequency, kept); «usted» scan 46 → 18, all excluded classes (nouns «ajuste», «importe», «cierre», «Despliegue»; the neutral «ustedes»); stamp audit 178 pairs, port check 0; hook proof PROOF_OK (6,581 → 0).
> - Commit by commit (`b16_stages.py`, `b16_build_snapshots.py`, read-only on the repo): six commits, 142 paths (= `git status`); the doc edits come from scripts with explicit edit lists, and their replay on HEAD in commit order equals the worktree for all 126 files; 9 translations change in two commits, their intermediate contents in `release-pipeline/b16_commit_stages/` (SHA256SUMS). The state after each of C2–C5, checked alone (`b16_stage_states_check.py`): validate 0/0, diff 624/624, dry-run nothing pending.

### 8. ✅ Batch 17: T's durations — on train 40 (`ab7fe324e`), 2026-10-11

> Coordinator 22:28: batch 16 merged as `91be6a321` (commits `7c66234a7`…`5b22b06f1`); train 40 brings T's train 39, which localizes the last hard-coded durations with `datePicker.presets.*` (`c7b49085f`): the tables' «Δ» columns through `deltaPeriodLabel` (`frontend/src/lib/utils/assetPriceDerived.ts:126`, plus `datePicker.presets.days` for the fixed day column: it «1G», fr «1J», es «1D») and the AI Export period (`features/ai-export/ui.ts:60–63`: «3M», «6M», «1A» in it/fr/es).

**8.1 ✅ The 7 held lines** — 2026-10-11 (`release-pipeline/scripts/b17_durations_t.py`, translation only, no stamp)
> **Note implementazione**: of the 7 lines held in 7.2, the Spanish ones (`user/assets/index.es.md:28`, `user/fx/index.es.md:26`) and the French/Spanish AI Export line already read «1S…5A» / «1A». Changed: `user/assets/index` it/fr «1W…5Y» → «1S…5A», `user/fx/index.it.md:27` likewise, `user/ai-export/index.it.md:60` «**1Y**» → «**1A**»; and `user/fx/index.fr.md:26`, which paraphrased the columns («de 1 semaine à 5 ans») where the English quotes them, → «de 1S à 5A». The duration token scan leaves only «Treasury 10Y», a bond's name. No page quotes the fixed «Δ 1D» column (the English says «over one day»).
> - Gates (lane 6158, load 14): `translate-validate` 0 errors, 0 warnings; `translate-diff` 624/624; dry-run nothing pending; strict build 0 WARNING/ERROR, 0 ⚠️/❌, 2,988 asset URLs; `check-links` 95; asset scan 0 broken in 4 languages; `git diff --check` clean; ports 6158/6168 free.

### 9. ✅ Batch 18: the final round after F — on train 42 (`5d62658bb`), 2026-10-12 (checkpoint)

> Coordinator 04:25: F is in the target (train 42), M's branch fast-forwarded to `5d62658bb`. (1) F-5's translation debt: 6 English pages (`book-value`, `deposited-capital`, `index`, `nav`, `period-pnl`, `user/dashboard/positions`) with `translate-validate` 75 errors and 75 warnings on the target, plus one-line changes in `user/brokers/index`, `user/dashboard/charts`, `index`, `kpi-cards` — outside `dev` the remote pipeline blocks on `translate-validate`; (2) the port of `kpi-cards.fr.md:34` and `book-value.es.md:5` (batch-16 edits on F's pages); (3) the new key `dashboard.fxOnCash` (I's values), the it/fr/es catalogues assigned to M for this round; (4) the gallery: F adds «FX on cash» to the Performance view, and the labels of batches 16–17 — T-1 changes no UI.

**9.0 ✅ Detectors and classification** (`release-pipeline/runs/b18/`)
> **Note implementazione**: dry-run 10 English pages × 3 (~1.06M tokens through the pipeline). Every drift comes from one commit, `a4332b25b` («docs: document native cash and FX on cash»), found by the cache MD5 (`release-pipeline/scripts/b18_en_drift.py`): `index` +41/−3, `period-pnl` +40/−3, `deposited-capital` +18/−1, `book-value` +12/−2, `nav` +9/−1, the five user pages +1/−1 or +2/−2. **By hand**, not the pipeline: mostly prose, the formulas copied as they are, two new sections with explicit ids, one table, one admonition; a run would rewrite 30 pages and undo the hand reviews of batches 11–16 on them (labels, register, restored headings, glossary).

**9.1 ✅ The port** — 2026-10-12 (`release-pipeline/scripts/b18_port_*.py`: an engine plus one data module per page group; every edit an anchor found exactly once, display math copied from the English page by the script)
> **Note implementazione**: 75 edits on 30 translations. The pages' own conventions kept: `\mathrm{}` identifiers and `\text{replay}`, `\text{like}` in English, `\text{if }` in Italian and `\text{si }` in French/Spanish as elsewhere in `index`; formula thousands `1\,000` with the decimal point (the developer's decision, M-5), prose numbers localized (it/es `1.000`, `0,90`; fr `1 000`); each page's money style (it/es `€900`, fr `900 €`), table type names (it/fr BUY/DEPOSIT, es COMPRA/DEPÓSITO) and link texts («Portfolio Engine — §6», «Moteur de portefeuille — §6», «Motor de cartera — §6»); the app's labels quoted (`dashboard.fxOnCash`: «Effetto cambio sulla liquidità», «Effet de change sur les liquidités», «Efecto del tipo de cambio sobre el efectivo»; **Vendite/Ventes/Ventas**; the Performance view «vista Performance / vue Performance / vista Rendimiento»), and the terms of `deposited-capital` and `roi` (base del capitale / référence de capital / base de capital; quota di proprietà / part de propriété / cuota de propiedad). The new headings: «💱 Risultato di cambio sulla liquidità in valuta / Résultat de change sur les liquidités en devises / Resultado de cambio sobre el efectivo en divisas» (`#exchange-result-on-foreign-cash`), «💵» + the app label (`#fx-on-cash`), «💱 D — …» in `deposited-capital`. Batch 16's edits on F's pages are intact (`kpi-cards.fr.md:34` «Frais et impôts», `book-value.es.md:5` «tu cartera»).
> - `translate-validate` 75 errors / 75 warnings → **0 / 0**; `translate-diff` 624/624; the 10 English pages stamped (dry-run listed exactly them; the cache changes in those 10 entries); dry-run «nothing to translate». Strict build 0 WARNING/ERROR, 0 ⚠️/❌, 2,988 asset URLs; `check-links` 95.

**9.2 ✅ `dashboard.fxOnCash` and the glossary**
> **Note implementazione**: I's values are consistent — «Liquidità / Liquidités / Efectivo» are `dashboard.cashValue` on the same dashboard, «Cambio / Taux / Tipo de cambio» the sibling `dashboard.unrealizedFxEffect`, «tipo de cambio» the glossary's and the developer's es term. No catalogue change. Glossary (171 terms): «FX on cash» (the app label, lower case) and «exchange result on cash» (risultato di cambio sulla liquidità / résultat de change sur les liquidités / resultado de cambio sobre el efectivo), so a later run keeps this round's wording.

**9.3 ✅ Gallery** — full run on lane 6158, 2 workers, fresh populate, 04:47–05:49 (load 49 → 6; log `runs/b18/b18_gallery_full.log`)
> - **⚠️ Fuori pista — «FX on cash» cannot appear in the gallery**: the Performance-view shots replay `frontend/e2e/dashboard-report.json`, a normalized real capture whose `positions_contribution.other_effects` holds only «Unallocated costs». Rule 12 forbids editing it; a new capture comes only from the developer's data (`dev.py mkdocs normalize-dashboard-fixture`), with a broker holding foreign cash. Reported to the coordinator.
> **Note implementazione**: **251 passed, 1 skipped** (the desktop project skips «mobile menu open» by design), **0 failed**, 1.0 h; 2,816 of 2,824 shots retaken; the test server rebuilt the frontend from this tree at 04:49 (the catalogues of batches 16–17 and F's key are in the bundle). Checked by eye: the PAC step «ROUTING – WHAT EACH BROKER CAN BUY» with its spaced dash (en/it/fr), the toggle «Sintesi» / «Résumé» beside the step «Riepilogo» / «Récapitulatif» (D's points of 5.9), the es dashboard «Asignación de activos», «Brókeres», «Tipos de Cambio». The PNGs are gitignored: the published gallery comes from the CI run.
> - **⚠️ Fuori pista — 8 shots silently missed**: `create-wizard-modal` in 5 language/theme pairs, `import-wizard-step3` and `-step4-resolution` (mobile/en/light), `import-wizard-duplicate` (mobile/fr/light) kept their files of 8–9/10, while the test passed. The scenarios probe with `locator.isVisible({timeout})`, which ignores its timeout in Playwright 1.61 (found in batch 3; `e2e/fixtures/probe.ts` `appears()` was written for it): when the element is not visible at that instant, the shot is skipped. `gallery.spec.ts` still has 76 such probes, 33 guarding a screenshot (about 20 shot names); `appears()` is used nowhere. Proposed to the coordinator, not changed here.
> - Noted for the owners, not a translation matter: amounts are formatted with `toLocaleString(undefined, …)` (`lib/utils/currency/currencyFormat.ts`), i.e. by the browser's locale, so the it/fr/es shots — taken by an en-US browser — show «1,188.58 €» and the PAC «0.01 €»; a Playwright `locale` per language would make them match the guide.

**9.4 ✅ Gates and checkpoint** — 2026-10-12 05:50–05:55, lane 6158 (`release-pipeline/scripts/b18_final_gates.sh`, logs `runs/b18/b18_final_*`)
> **Note implementazione**: `utils gate-i18n-usage` 195, `docs-fr-typography` 191, `translation-validator` 130, `gate-docs-links` 60, `translation-cache` 38, `translation-code-blocks` 80, `check-orphans` clean, `--workers 4 utils all` **1676 passed**, Vitest `src/lib/i18n/` 17; `translate-validate` 0 errors, 0 warnings; `translate-diff` 624/624; `translate-check` green (its masked key fragment redacted in the log); dry-run «nothing to translate»; strict build 0 WARNING/ERROR, 0 ⚠️/❌, 2,988 asset URLs; `check-links` 95; asset scan 0 broken in 4 languages; masked pairs 624/624; coverage complete; label scan 370 rows, unchanged; «usted» scan 18, the excluded classes only; glossary scan 214 hits, unchanged (a first pass found 2 new ones of mine: fr «conversion de devises» and es «cambio de divisa» for «currency exchange» → the glossary's «change de devises», «cambio de divisas»); stamp audit 196 pairs, port check 0; hook proof PROOF_OK (6,630 → 0).
> - **⚠️ Fuori pista — the port engine**: an insertion keeps its anchor, so the first engine would have inserted twice on a second run; «already applied» is now checked first (a rerun applies 0 of 75), and the 75 edits replayed on HEAD reproduce the worktree byte for byte (30 files).
> - Commit by commit (`release-pipeline/scripts/b18_stages.py`): two commits, 34 paths (= `git status`), no file in both.

### 10. ✅ Batch 19: M-13, the gallery probes — on train 44 (`7b3c2b5ab`), 2026-10-12 (checkpoint)

> Coordinator 06:02: M-13 goes into 1.2 — a shot skipped in silence is a defect of the release run too, which redoes the gallery from scratch. Limited scope: test-author replaces with `appears()` the probes that stand in front of a shot; of the others only those that hide a skipped step the same way, listed for the coordinator; then the touched scenarios on lane 6158, showing that the 8 missed shots come out. M-12 and M-14 stay with the developer.

**10.0 ✅ Classification** — 2026-10-12 (`release-pipeline/scripts/b19_probe_map.py`, `b19_classify.py`; `runs/b19/b19_probe_classes.tsv`)
> **Note implementazione**: `gallery.spec.ts` holds **76** `isVisible({timeout})` probes (batch 18's «33 guarding a shot» was a rough count of probes followed by a shot). Read one by one, in four classes:
> - **A — 19 guard the shot** (the screenshot is inside their block; a miss skips it silently): 1025, 1857, 1896, 2753, 2870, 2873, 3281, 3352, 4101, 4108, 4115, 4118, 4417, 4735, 5334, 5612, 5638, 5650, 5654 — among them the outer probes of the 8 shots batch 18 missed.
> - **B — 29 prepare a later shot** (a miss leaves the shot taken in the wrong state, or lets a loop end without it, silently): the date presets of `selectMaxDateRange`/`selectOneYearDateRange` (909, 911, 921; 18 call sites), `selectTransactionType` (2603, 2608), the cache panel's unlock and Memory category (1969, 1982), the split kebab (2749), the clone form close (2799), the promote-merge selection clear and button (2847, 2860), the duplicate-table scroll (3377), the table views (4192, 4675), the FX filter (4213, 4217), the FX and asset panel toggles and scrolls (4463, 4468, 4499, 4524, 4529, 4885, 5324, 5363, 5369, 5393, 5398), the asset search (4702), the create-wizard combobox whose fallback may not open the dropdown (5641).
> - **C — 7 fail loud** when they miss (a later hard wait or expect stops the test): the FIFO retry loop, whose last attempt asserts (1342, 1361, 1365); the scheduler unlock, whose miss leaves a disabled button to click (1843); the wizard warnings overlay, which blocks step 4 and its `waitFor` (3302, 3367, 5627).
> - **D — 21 cleanups or a deliberate instant question**: the discard/close confirmations after the shot, every one followed by a fresh `navigateTo` in the next iteration (2569, 2624, 2631, 2635, 2811, 2880, 2889, 3208, 3245, 3317, 3389, 3435, 4078, 5663, 5677); the add-pair search fills, whose outcome the next `expect(option).toBeVisible` already guards (4246, 4259, 4312, 4325); the reset to the line chart, a page-local state reset by the next navigation (4744); «is this the login page now?» (1349), which `appears()` would slow by 1 s per pass.
> - Converted: **A + B = 48**; left as they are: C + D = 28.

**10.1 ✅ The conversion** — 2026-10-12, by test-author (three passes; static checks only, no suite)
> **Note implementazione**: `frontend/e2e/gallery.spec.ts` — the 48 probes become `appears(x, N)` from `./fixtures/probe`, each line in place, every timeout as written (59 lines replaced one for one: the import, the 48 probes, the 3 below and 7 comment lines; the file kept its 6,491 lines; the 3 step-1 barriers of 10.2 add 3 — every line number in this step is HEAD's). Prettier clean; `tsc -p tsconfig.e2e.json` shows only the 2 errors it had before (`onboarding-tour.spec.ts:863`, and `$lib/api/generated`, absent in a worktree).
> - **⚠️ Fuori pista — the same defect behind `isEnabled`**: test-author found 3 more probes outside the `isVisible` count, `parseBtn.isEnabled({timeout: 3_000})` at 3290, 3360 and 5620 — in 1.61 `isEnabled` waits only for the element to exist, then looks once, and the import wizard's parse button stays disabled until `step2CanParse`. A false skips the whole step 3 / step 4 / create-wizard branch: the same three tests as the 8 missed shots. An inline `expect(...).toBeEnabled(...).then(...)` is reflowed by Prettier onto 8 lines, so `fixtures/probe.ts` gains `becomesEnabled()`, the enabled twin of `appears()` (+18 lines, an export no other spec imports), and the three probes read `if (await becomesEnabled(parseBtn, 3_000)) {`.
> - Two comments that described the old helpers as looking «once» (716–720, 5191–5195) now say they wait half a second at most; rewrapped within their own lines.
> - Reported by test-author and **not** changed (the coordinator's call): a hard `expect` instead of `appears()` where the component always renders the element on the path — `selectTransactionType` (2603, 2608), the table views (4192, 4675), the wizard `fileRow` (3281, 3352, 5612), the cache unlock (1969), the broker edit button (4108), the asset search (4702), the date presets (909, 911, 921). And the cost of honest waits where the element legitimately never comes: about 5 s per incompatible pair at 2860, 1 s per mobile combination at 1982, 3 s per paired clone at 2799.

**10.2 ✅ The touched scenarios** — lane 6158, 2 workers, fresh populate, 06:40–07:08 (load 9 → 84 at 06:52 → 5; `runs/b19/b19_gallery.log`, `b19_verify.txt`, `b19_shot_coverage.txt`)
> **Note implementazione**: Playwright `-g` over the 43 titles per viewport that hold a converted probe or call a converted helper (`release-pipeline/scripts/b19_grep.py`): **86 passed, 0 failed**, 26.9 min, 1,018 PNGs retaken. **The 8 shots missed in batch 18 all come out** (06:54–07:07). Every other shot name of these scenarios 16/16 (2 viewports × 4 languages × 2 themes). 318 of the 1,018 PNGs differ in bytes from batch 18's; the pairs checked by eye (`form-modal-sell`, `fifo-lots-comparison-chart-return`) differ only by an hour more of data. The bundle is batch 18's build: `frontend/src` has not changed since `5d62658bb`.
> - **⚠️ Fuori pista — 6 other wizard shots missed in silence**, under load 84: `create-wizard-modal` (desktop/en/dark, desktop/it/light, mobile/en/dark), `import-wizard-step3` + `-step4-resolution` (mobile/it/light), `import-wizard-duplicate` (mobile/fr/dark). A real wait was not enough, because the wizard prelude raced. test-author found two causes in `ImportWizardModal.svelte`: step 2 loads its file list, plugins and set previews behind its own `data-busy` (:4596), which the prelude guessed with `waitForTimeout(800)`; and, the race no wait can fix, a Next clicked before step 1's broker list arrives lets `loadBrokerFiles()` read an empty list (:3512, :668), so every broker panel renders collapsed and the file row never exists (:3530). The other import specs settle step 1 first. Fix, by test-author: `waitForSettled(import-wizard-step1)` before Next (3 lines added), `waitForSettled(import-wizard-step2, 30_000)` in place of the 800 ms sleep (3), `waitForSettled(import-wizard-step4, 30_000)` before the create-wizard's asset select (1). The 3 tests again, fresh populate: 2 workers 07:24–07:27 and 4 workers 07:27–07:29, **6 passed each time, the 4 shot names 16/16 each time**.
> - A user who clicks Next that fast sees the same collapsed list (Next stays enabled while the brokers load, :5378): a product question, reported to the coordinator.

**10.3 ✅ Gates and checkpoint** — 2026-10-12 07:30, lane 6158 (`release-pipeline/scripts/b19_final_gates.sh`, logs `runs/b19/b19_final_*`)
> **Note implementazione**: `check-orphans` clean; Prettier on `e2e/**/*.ts` clean; `tsc -p tsconfig.e2e.json` only the 2 errors of HEAD; `git diff --check` clean; `gallery.spec.ts` 28 `isVisible({timeout` left (classes C and D), 48 `appears(`, 3 `becomesEnabled(`, no `isEnabled(`, 6,494 lines (HEAD 6,491: the 3 step-1 barriers); ports 6158 and 6168 free. No product file changed, so no backend or unit suite.

### 11. ✅ Batch 20: M-14, a browser locale per gallery language — on train 46 (`378338fed`), 2026-10-12 (checkpoint)

> Coordinator 09:57, the developer's decision (verbatim): «tanto gli screen vanno fatti in ogni caso, impostiamo il locale in playwright sin da ora, è la scelta giusta». Scope: a Playwright locale per gallery language (en-US, it-IT, fr-FR, es-ES) where the gallery picks the language; first the list of scenarios that type numbers or dates (the decimal comma and the date format could break them), fixed with test-author; a full gallery on 6158 showing nothing skipped; an it/fr/es sample checked by eye; M-14 closed in section M. Analysis sent FROZEN at 10:15, approved at 10:17 (the guard and the redraws included; M-17 opened for the two product strings).

**11.0 ✅ Analysis** — 2026-10-12 (`release-pipeline/runs/b20/b20_analysis.md`; probes `scripts/b20_locale_probe.cjs`, `b20_locale_probe2.cjs`, logs `runs/b20/b20_locale_probe*.log`)
> **Note implementazione**: about 36 app sites format with the browser locale — the amounts (`currencyFormat.ts:39,61`), the table dates (`dataTableLogic.ts:326-344`), KPI, performance and growth charts, the scheduler log; dates and percentages elsewhere follow the app language already, so today's it/fr/es shots mix the two.
> - **No scenario breaks on a typed number or date**: the risk simulation writes integers into `type="number"` fields (`L4Simulation.svelte:179,183,207`), the PAC planner's `ExactDecimalInput` keeps the canonical `.` in every language (`normalizeDecimalInput` reads one `.` or `,` as the decimal point whatever the locale), no date is typed, nothing parses page text, and the rows sort the same in the four locales.
> - **The real risk is a number drawn before the switch**: a language switch redraws nothing (no `{#key}`, the selector sets a store), and probe 2 shows «1,188.58» staying on a document after the locale moved. So the locale goes in before the page is drawn: first in every language loop (75 loops; the test generator at :2648 inside its test), and the tests that shoot one page set up before the loop redraw it per language.
> - **The mechanism** (probe 1, desktop and mobile): Playwright's `locale` is fixed per context, the gallery loops four languages in one page; Chromium's `Emulation.setLocaleOverride`, sent from a CDP session of the test, switches at runtime and holds across reloads and navigations. Trap: `@playwright/test` gives every context `locale: 'en-US'` (`playwright/lib/index.js:252`) and Chromium then refuses a second session («Another locale override is already in effect»); `test.use({locale: undefined})` falls back to the default, a fixture yielding `undefined` does not. `navigator.language` stays `en-US`, so the app's first-visit language is unchanged; this host is `it_IT`, so en-US is pinned explicitly.
> - **⚠️ Fuori pista — 13 tests, not 10**: `shootStaticPreview` (:2409) runs `eachLanguageAndTheme` for 4 tests (image, pdf, markdown, text previews); the first count attributed it to the test above it. The tests that shoot a page set up before the language loop are 3 auth pages, 2 PAC (the draft lives in memory only, `planner/draft.svelte.ts:4`) and 8 Files.
> - Seen on the way, product, not changed: `DateRangePicker.svelte:1109` (`'en'` hardcoded) and `GlobalSettingsTab.svelte:726` («Last updated:» in English) → M-17, for I after M-16.

**11.1 ✅ The implementation** — 2026-10-12, by test-author (two passes; static checks only)
> **Note implementazione**: new `frontend/e2e/fixtures/galleryLocale.ts`: `GALLERY_LOCALES` (en-US, it-IT, fr-FR, es-ES); `setBrowserLocale(page, lang)`, one CDP session per page, `Emulation.setLocaleOverride` plus Accept-Language, a no-op when the locale is already the one asked, and an error that names the cause when Chromium refuses; `stampDocumentLocale(page)`, an init script recording on each document the locale it began under; `expectDrawnUnder(page, lang)`, the check. In `gallery.spec.ts`:
> - the gallery's describe yields no locale (`test.use({locale: async ({}, use) => use(undefined)})`); the outer `beforeEach` stamps and pins `en-US` before anything loads;
> - the first statement of every language loop of a test or helper is `setBrowserLocale(page, lang)` (75 loops; the generated `transaction form modal variants` call it before their `navigateTo`);
> - the guard runs in `screenshot()` and `shootFiles()`, the only two `page.screenshot` calls;
> - the 13 tests that shoot a page set up before the loop redraw it per language: the 3 auth pages re-open `/` (`openLoginPage`), the 2 PAC tests build their draft again in each language (`perLanguage`, a helper that runs a set-up at the first combination of each language), the 8 Files tests re-open their URL inside `eachLanguageAndTheme`, which now takes it. Each redraw checks that the language survived the load (`html[lang]`).
> - **⚠️ Fuori pista — PAC leaves a dirty draft**: a full load of the planner with a draft raises the browser's leave-page dialog (`beforeNavigate` cancels a `leave`, `PacPlannerTool.svelte:252-261`); Playwright accepts it when no dialog listener is registered, as in the gallery. The headers of `fixtures/galleryPac.ts` and `fixtures/galleryFiles.ts`, which said one draft per test and one load per test, are corrected (comments only, by me).
> - The coordinator's extra line for I (M-16): `waitForSettled(import-wizard-step1)` before the `import-wizard-step1` shot (:3297); the 300 ms stays, since the modal's opening animation (Svelte, `ModalBase.svelte:238,240`) is not frozen by the style tag.
> - Prettier clean on the four files; `tsc -p tsconfig.e2e.json` only the 2 errors of HEAD.

**11.2 ✅ Smoke run** — lane 6158, 2 workers, fresh populate, 10:51–11:02 (load 12 → 40 → 19; `runs/b20/b20_smoke.log`)
> **Note implementazione**: the riskiest paths — the 13 redraws, the seeded languages (update modal, donation popup, welcome setup), the generated tests (en and it, light), a plain loop on each page kind (main dashboard, FX list, Asset list table), the risk simulation that types numbers: **44 passed, 0 failed**, the guard green on every shot. PAC steps 51 s (39–41 s with one draft), PAC result 59 s. The Italian dashboard now reads «+4788,01 €», «50.000,00 €», «49.890,40 €».
> - **⚠️ Fuori pista — percentages written with `toFixed`**: in the same card the returns read «10.59%», «14.07%», «(-4.04%)» — about 50 lines in some 30 files (`KpiSection.svelte:252-255,268`, risk levels, charts, FX cards) build a percentage with `toFixed(n)` and «%», so no locale reaches them. Product, not changed → M-18.

**11.3 ✅ Full gallery and the eye check** — lane 6158, 2 workers, fresh populate, 11:06–12:16 (load 18 → 115 → 57; `runs/b20/b20_full.log`)
> **Note implementazione**: **250 passed, 1 skipped** (the desktop project skips «mobile menu open» by design), **1 failed**, 1.2 h; every one of the 2,824 PNGs retaken, the guard green on every shot of the passing tests.
> - **⚠️ Fuori pista — the red, triaged (test-triage)**: `transaction form modal - all languages and themes` (desktop), Spanish iteration: `setLanguage` clicked «Español», the flag turned Spanish, but `<html lang>` stayed `fr` for 3 s, and the list beside it read «Network Error» (Axios's message for a request with no response). The backend logged no warning or error and never restarted; the offline guard aborted nothing (`afterEach` added no error). In the failure window (11:10–11:20) the macOS log shows a `utun5` interface attaching at 11:17:34 with addresses in Tailscale's ranges (`100.64.0.0/10`, `fd7a:115c:a1e0::/48`), and `configd` «network changed» eight times until 11:18:04: Chromium aborts the requests in flight on a network change, here the list and the Spanish dictionary. **Verdict: environment** — the shared machine's network moved under the run; unrelated to M-14. The same test alone, fresh populate, three times, both projects: **2 passed each time** (41–43 s, load 40–48), its 16 shots retaken.
> - **Eye check** (it/fr/es): the Italian KPI cards «+4788,01 €», «50.000,00 €»; the French transactions «11 oct. 2026», «-0,001», «-500,00 €»; the French scheduler log «11 oct., 23:00» and «12/10/2026 11:06:41»; the Spanish PAC result «≈3569,85 €», «2,7 s», «Escenario 12/10/2026». Four-digit amounts carry no thousands mark in it and es (CLDR), five-digit ones do. Still with the dot, all from `toFixed` (M-18): the percentages (KPI, risk lab «−10.7%», PAC «30.58%»), the file sizes «9.2 KB» (`formatBytes`), the durations «18.7s». Still in English: «Last updated:» (M-17).

**11.4 ✅ Gates and checkpoint** — 2026-10-12 12:22, lane 6158 (`release-pipeline/scripts/b20_final_gates.sh`, logs `runs/b20/b20_final_*`)
> **Note implementazione**: `check-orphans` clean; Prettier on `e2e/**/*.ts` clean; `tsc -p tsconfig.e2e.json` only the 2 errors of HEAD; `git diff --check` clean; `gallery.spec.ts`: 76 `setBrowserLocale(page, lang)` for 76 language loops (75 loop heads, and the generated test in place of its describe-level loop), 2 `expectDrawnUnder`, the probes of batch 19 unchanged (28 `isVisible({timeout`, 48 `appears(`); ports 6158 and 6168 free. The `testing-frontend` skill gains «Gallery: a language's shots are taken by a browser of that language». No product file changed, so no backend or unit suite. Commit by commit (`release-pipeline/scripts/b20_stages.py`): two commits, 7 paths (= `git status`), no file in both.

### 12. ⏳ Next, and what waits

1. devWiki: the coordinator hands the notes to the historian (his step 3): `release-pipeline/b12_devwiki_stamps_hide_stale_translations.md`, `b13_devwiki_anchors_from_render.md`, `b14_devwiki_raw_html_paths_in_translations.md`, `b15_devwiki_fr_typography_hook.md`.
2. Full pipeline run (translations + gallery): never forced (it would undo the hand reviews of batches 11–18); nothing is pending today.
3. The gallery's «FX on cash» shot: only after a new dashboard capture by the developer.
