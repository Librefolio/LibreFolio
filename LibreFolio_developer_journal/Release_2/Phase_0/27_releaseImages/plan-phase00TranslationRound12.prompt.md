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

### 3. ⏳ Phase 3: the launch (the developer)

> - **Files:** `release-pipeline/runs/b11_pipeline_files.txt`, 101 EN pages. Excluded: the 25 stamped, the 4 deferred, S's 3.
> - **Dry run:** 101 × 3 = **303 translations, about 8.37 M tokens** (6.45 M in, 1.92 M out).
> - **Configuration:** the worktree's `mkdocs_src/aphra-pipeline/.env` (Doubleword, `deepseek-ai/DeepSeek-V4.1-Flash`, key present, web search off). Model check and `translate-check` green.
> - **Command** (from the worktree, with the shared venv; `--file` is mandatory: without it the pipeline would also take the deferred pages and S's):
>   - `cd /Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-upgraded-telegram && PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs translate --workers 3 --file $(cat /Users/ea_enel/Documents/00_My/LibreFolio-cloud-sizing/release-pipeline/runs/b11_pipeline_files.txt) 2>&1 | tee /Users/ea_enel/Documents/00_My/LibreFolio-cloud-sizing/release-pipeline/runs/b11_pipeline_run.log`
