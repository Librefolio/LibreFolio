# Report 50 — Gap documentazione e galleria screenshot: da v1.0.1 a HEAD

**Data**: 2026-09-03 · **Tipo**: solo analisi (la scrittura docs avverrà in seguito)
**Contesto**: 98 commit `v1.0.1..HEAD` + lavoro non committato del 02–03/09
 (P0/P1/P2 backlog, pannello cache, badge email, SETTINGS_REGISTRY, fix docs P3).
**Metodo**: 3 lane di analisi parallele (user/admin docs, developer docs, gallery.spec.ts)
 con verifica claim-per-claim contro il codice. I fix P3 dell'audit 08 sono atterrati OGGI
 nel tree — questo report non li ri-segnala, copre ciò che P3 non copriva.

## Sintesi esecutiva

1. **Il gap maggiore è il sottosistema Risk (beta)**: 5 superfici UI, zero documentazione
   utente E developer; i conteggi dei tab nelle pagine esistenti sono sbagliati
   (dashboard «three»→4, broker «four»→5).
2. **Segnali**: le pagine utente elencano ancora 4 indicatori contro i 22 plugin backend.
3. **Admin/settings**: righe scheduler con semantica UTC falsa (P3-6 trattenuto, da fare
   ora che il registry è atterrato), `require_email_verification` documentata come
   funzionante (è un placeholder con badge da oggi), installation ancora «Alpha»/v0.10.0.
4. **Gallery**: 115/116 PNG committati sono dell'era v1.0.0 → rigenerazione completa
   consigliata; 7 shot nello spec sono morti in modo SILENZIOSO (skip guardati, run verde
   lo stesso — i PNG vecchi mascherano la muffa); 12 nuovi shot necessari (risk ×4, cache,
   changelog, update modal, 3 step condizionali del wizard…); 13 shot esistenti riusabili
   in pagine senza immagini.
5. **Pagine che citano codice rimosso**: BaseDropdown presentato ancora come fondamento
   della gerarchia select in `developer/frontend/.../select.md` (eliminato oggi).

---

# Parte A — User/Admin docs

# Report 50 — USER/ADMIN docs alignment vs `v1.0.1..HEAD`

> Lane: ANALYSIS (read-only) · Branch `dev_release2` · Date 2026-09-03
> Delta: 98 commits + today's uncommitted tree (cache panel, email-verification badge, SETTINGS_REGISTRY, P3 mkdocs fixes).
> 08-audit cross-check: P3 documentation fixes are **in the tree today (uncommitted, 42 mkdocs files)** — verified per-page; they are NOT re-reported here except where the fix did **not** land (P3-6 scheduler semantics) or the gap was never in P3 scope.
> Translation note: **every page flagged below exists in 4 languages** (`.en/.it/.fr/.es`) unless marked "EN-only gap". A missing page means missing ×4; a misaligned EN page means re-translation debt ×4 (P3-27 batch already deferred).

---

## 1. Risk Analysis subsystem (beta) — 🔴 biggest gap

UI surfaces verified in code: dashboard **Risk** tab (`dashboard-tab-risk`, `RiskAnalysisPanel`), broker detail **Risk** tab (`broker-tab-risk`), asset detail **Risk** tab (`asset-detail-tab-risk`, `AssetRiskScenariosView`), assets list `AssetSetRiskPanel`. Labels: "Portfolio risk" / "Broker risk" / "Asset risk".

| Feature | User/Admin page today | Status | What's missing | Suggested gallery shots |
|---|---|---|---|---|
| Risk subsystem (9 analytics: historical metrics, VaR/CVaR, drawdown summary, correlation, risk contribution, stress test, comparison, simulation, allocation) | **None** — no `user/risk/**` page, no nav entry | **missing** | Whole page: what each analytic does, scopes (`asset`/`asset_set`/`portfolio`), parameter forms, data-quality status (`ok/partial/unavailable/failed`), why failures are honest (error taxonomy in user terms), beta disclaimer | `dashboard/risk-tab` (new), `risk/correlation-heatmap` (new), `risk/stress-test` (new), `risk/allocation` (new) |
| Dashboard Risk tab | `user/dashboard/index.en.md` says "**three** primary tabs" (Overview/Positions/Transactions) | **misaligned** | 4th tab "Risk" + what it contains | reuse → `dashboard/risk-tab` (new) |
| Broker Risk tab | `user/brokers/index.en.md` says "**four** primary tabs" | **misaligned** | 5th tab "Risk" scoped to the broker | `brokers/risk-tab` (new) |
| Asset Risk tab | `user/assets/detail/index.en.md` describes "features accessible from the toolbar", no tab row | **misaligned** | Overview/Risk tab structure; risk scenarios view; rolling-risk overlays on chart | `assets/detail-risk-tab` (new) |
| Asset-set risk (assets list page panel) | `user/assets/index.en.md` — absent | **missing** | Multi-select/set risk panel below the list | `assets/list-risk-panel` (new) |

## 2. Signals platform (backend plugins)

| Feature | Page today | Status | What's missing | Suggested shots |
|---|---|---|---|---|
| 22 backend indicator plugins (SMA, EMA, MACD, RSI, Bollinger, ADX, Aroon, ATR/NATR, CCI, Donchian, KAMA, MFI, OBV, PPO, ROC, Stoch-RSI, Drawdown, Rolling Beta/Return/Sharpe/Volatility) | `user/assets/detail/signals.en.md` lists **only EMA/MACD/RSI/Bollinger + comparison** (4 langs) | **misaligned** | The other ~17 indicators; grouped indicator search; KaTeX formula labels; per-signal diagnostics; spinner-during-load; partial-segment rendering for incomplete OHLCV | existing `assets/detail-signals-ema/-rsi/-macd/-bollinger` reusable per-indicator; new: `assets/detail-signals-adx` or a grouped-search shot |
| FX signals (9 FX-compatible plugins) | `user/fx/detail/signals.en.md` lists the same 4 | **misaligned** | Same as above, FX scope; drawdown `full_history` toggle (new param, also affects AI Export) | existing `fx/detail-signals` (regenerate — UI reworked) |
| Live preview in chart settings (`POST /signals/preview`, synthetic curve, no "unavailable" banner) | `user/fx/chart-settings.en.md` — no mention; still shows only 4 "Calculated Signals" + misleading "Synthetic Benchmarks — custom baskets" as *overlays* | **misaligned** | Preview rendering in the modal; corrected signal list; clarify synthetic curves are preview-only | existing `fx/chart-settings` (regenerate) |
| Asset chart settings modal (exists on assets list, `ChartSettingsModal` + preview) | **No page** (only FX has a chart-settings page) | **missing** | Short section in `assets/index.en.md` or `assets/detail/chart.en.md` | existing `assets/list` context; new optional `assets/chart-settings` |
| Asset detail page structure | `user/assets/detail/index.en.md` — signals bullet repeats the 4-indicator claim | **misaligned** | Update feature list (22 indicators, backend-computed) | — |

## 3. AI Export catalog (8 datasets / 11 analyses)

| Feature | Page today | Status | What's missing | Shots |
|---|---|---|---|---|
| V1 catalog, Export Data vs Request Analysis, 10-min draft memory, task-aware composition | `user/ai-export/{index,portfolio,broker,asset,fx}.en.md` | **adequate** (P3-20/21 landed: "eight"/"eleven", page-toolbar fix, 2 real asset tasks) | Nothing user-visible found | existing shots suffice (no AI-export shots in inventory — acceptable, modal is text) |

## 4. Broker importers (BRIM) — 19 new plugins

| Feature | Page today | Status | What's missing | Shots |
|---|---|---|---|---|
| 30 importers (19 new) | `user/transactions/import/` — all 19 pages exist (avanza…xtb); index table has 30 rows | **adequate** (P3-15/17 landed: eToro CSV-only, Directa CSV+XLSX, generic-csv types) | — | per-broker pages intentionally text-only |
| Duplicate resolver step 3, N-way compare, file-priority list | `user/brokers/import.en.md` (rewritten today, P3-25) | **adequate** | — | `brokers/import-wizard-duplicate` covers badges only; **no shot of the dedicated Duplicates step / N-way compare modal** → new `brokers/import-wizard-duplicates-step`, `brokers/import-nway-compare` |
| Corrections step (cash-vs-trade, bundled amounts, instrument-less fees) | documented in import.en.md | **adequate** text; no shot | — | new `brokers/import-wizard-corrections` |
| Unify-assets step + "Reuse existing asset" | documented in import.en.md | **adequate** text; no shot | — | new `brokers/import-wizard-unify` |
| Maturity/redemption advisory banners | not found in user pages | **missing** (minor) | One paragraph in `brokers/import.en.md` or `assets/detail/events.en.md` (maturity settlement page exists in theory docs) | — |
| Plugin diagnostics (`/system/plugin-diagnostics`, panel in Settings → About) | `user/settings/about.en.md` lists only version/license/links | **missing** | The diagnostics collapsible (`about-plugin-diagnostics`): per-registry load failures, why a plugin is absent | regenerate `settings/about`; new optional `settings/about-plugin-diagnostics` |

## 5. Asset identity / merge

| Feature | Page today | Status | What's missing | Shots |
|---|---|---|---|---|
| Merge from context menu; wizard merge on ambiguity; `identifier_other` JSON list | `user/assets/index.en.md` (context menu w/ Merge — P3-23 landed), `create-edit.en.md` ("Other identifiers"), `brokers/import.en.md` | **adequate** | — | existing |
| Assets page **usage panels** (yours / other users' / under-analysis) + per-asset transaction-count badges, stacked synced tables | `user/assets/index.en.md` — **absent** | **missing** | New section: the three panels, who sees what (shared assets), tx-count badge in grid + table | regenerate `assets/list` + `assets/list-table`; new `assets/list-usage-panels` |

## 6. Dashboard ownership / sharing / broker roles

| Feature | Page today | Status | What's missing | Shots |
|---|---|---|---|---|
| Ownership-aware aggregation (only owned brokers, scaled by share; 0% share = editor/viewer behavior; broker cards scale; instant cache invalidation on share edit) | `user/brokers/sharing.en.md` §Share Percentage note (P3-9 landed) — **but** `user/dashboard/{index,kpi-cards}.en.md` and `brokers/index.en.md` say nothing | **partial** | One short "Sharing affects these numbers" note on dashboard/index + kpi-cards; broker-card scaling note on brokers/index | — |
| Self-service leave / demote / last-owner-deletes-broker | sharing.en.md §Leaving (incl. danger box) | **adequate** | — | existing `brokers/sharing-modal` |
| User picker select in sharing panel | sharing.en.md "How to Share" | **adequate** | — | existing |
| Broker **delete guard** (tx count + guard dialog w/ filtered link) | not in `brokers/index.en.md` | **missing** (small) | Paragraph: deleting a broker with transactions opens a guard dialog | new optional `brokers/delete-guard-modal` |
| "View in Transactions" deep-link from broker Transactions tab | not in `brokers/import.en.md` | **missing** (small) | One line + filter carry-over | existing `brokers/transactions-tab` |

## 7. Docker light, changelog modal, update prompt

| Feature | Page today | Status | What's missing | Shots |
|---|---|---|---|---|
| Docker light variant (pull `*-light`) | `user/installation.en.md` §Image Variants | **adequate** (but example tag `v0.10.0-light` is pre-1.0 — cosmetic) | refresh example tags to `v1.1.0*` | — |
| `dev.py docker build --light` (build side) | `admin/docker_advanced.en.md` lists build commands **without** `--light` | **partial** | Add `--light` row + size note (~1.5 vs ~2.9 GB) | — |
| In-app changelog modal (sidebar version click, foldable panels, version index) | **nowhere** | **missing** | Paragraph in `user/settings/about.en.md` (or settings/index) | new `settings/changelog-modal` |
| Admin update-check modal (post-login, 1-day throttle, links updating guide) | **nowhere** | **missing** | Note in `admin/settings.en.md` or `admin/index.en.md`; cross-link `{installation.md#updating}` | new `auth/update-available-modal` |
| Updating guide staleness | `user/installation.en.md` §Updating says "**Alpha** Status", example `v0.10.0` | **misaligned** | Project is 1.1.0 / Beta (pyproject); refresh wording + tags. This is the page the update modal links to | — |

## 8. Settings / admin (incl. today's features)

| Feature | Page today | Status | What's missing | Shots |
|---|---|---|---|---|
| **Cache panel** (Global Settings: `GET settings/cache/status`, per-cache clear + clear-all, admin-gated clear, confirm modals) — landed today | `admin/settings.en.md` — absent | **missing** | New section: what each named cache is, TTL/size columns, clear vs clear-all, the "next fetch hits providers" slowdown warning | new `settings/cache-panel`; regenerate `settings/global-settings` |
| **Email-verification placeholder badge** (`require_email_verification` is a placeholder; UI now badges it) — landed today | `admin/settings.en.md` line 40 describes it as a **working** feature | **misaligned** | Add "(placeholder — email sending not implemented yet)" | regenerate `settings/global-settings` |
| `scheduler_history_sync_times` semantics | `admin/settings.en.md` line 44: "saved times are **stored in UTC**" — false since `c8bdbaea` (stored in `scheduler_timezone`, converted to UTC only for due-checks) | **misaligned** (P3-6 **did not land** — admin/settings.en.md untouched today) | Rewrite rows 44+47: times/days stored in configured zone; `scheduler_timezone` decides due slots | — |
| Settings categories | Categories section: Defaults omits `default_theme`; Sync & Uploads lists `scheduler_*` keys that in the UI live in the Configure modal (tab categories: session/security/sync/defaults/other) | **partial** | Align category membership with `GlobalSettingsTab.svelte` | — |
| Scheduler panel (Configure + Logs) | `admin/settings.en.md` §Market Data Scheduler | **adequate** (shots exist, used) | — | existing `settings/scheduler-config`, `settings/scheduler-log` |

## 9. Files, FX, transactions, valuation/FIFO

| Feature | Page today | Status | What's missing | Shots |
|---|---|---|---|---|
| Files page (tabs, context menus, preview, crop) | `user/files/index.en.md` | **adequate** (P3-22 landed) | — | reuse `files/preview-modal-csv` (+image/pdf/markdown/text) for the Preview bullets |
| FX MANUAL provider + CSV import + data editor | `user/fx/detail/data-editor.en.md`, `provider.md`, `fx/index.en.md` | **adequate** | — | existing |
| Single-row delete → bulk workspace; delete modal removed | `user/transactions/index.en.md` (P3-10 landed) | **adequate** | — | reuse `transactions/bulk-delete-pair-modal` |
| Bulk workspace split / promote / merge actions (`tx-action-modal`, `promote-merge-modal`) | index page covers deletion only | **partial** | Short section on split/promote/merge in the bulk workspace | reuse `transactions/action-modal`, `transactions/promote-merge-modal` |
| Clone preserves original date (all clone paths) | not documented (clone not listed among context-menu actions) | **missing** (minor) | List Edit/Clone/Delete as context-menu actions; note date preservation | — |
| Net annualized return (CAGR), 30-day guard, oldest-open-lot col, estimated market line, in-kind ADJUSTMENT cost basis | `user/dashboard/positions.en.md` (P3-14 landed: 13 cols, Annualized, Oldest open lot, dashed at-cost marker) | **adequate** | — | regenerate `dashboard/fifo-lots-*`, `dashboard/positions-*` |
| Dashboard data-quality banner | `user/dashboard/index.en.md` §Data Quality Banner — describes pre-foldable single-CTA behavior | **partial** | Foldable banner + one "go to asset" link per asset | — |

---

## Existing shots that could be REUSED in existing pages

| Shot (exists in `frontend/e2e/gallery.spec.ts`, committed PNG) | Page that could use it |
|---|---|
| `assets/detail-signals-ema` / `-rsi` / `-macd` / `-bollinger` | `assets/detail/signals.en.md` per-indicator sections (today: one generic `detail-signals` shot) |
| `assets/detail-chart-candlestick` | `assets/detail/chart.en.md` — candlestick view is **not documented at all**; add paragraph + shot |
| `assets/detail-measures-active` | `assets/detail/measures.en.md` (active measurement state) |
| `assets/list-filtered` | `assets/index.en.md` Smart Search / Type Filters bullets |
| `dashboard/transactions-tab` | `dashboard/index.en.md` Transactions tab bullet (tab has no image) |
| `files/preview-modal-csv` (+ `preview-modal-image/-pdf/-markdown/-text`) | `files/index.en.md` Preview context-menu bullets |
| `media/asset-picker-modal` | `assets/create-edit.en.md` or `misc/image-crop.en.md` (icon picking) |
| `transactions/picker-modal` | `transactions/form.en.md` (asset picker) |
| `transactions/action-modal`, `transactions/promote-merge-modal`, `transactions/bulk-delete-pair-modal` | `transactions/index.en.md` bulk-workspace section (once expanded) |

## Existing shots now STALE

**Systemic: 115 of 116 committed EN desktop PNGs date from 2026-07-13/14 (v1.0.0 era)** — the whole gallery predates the 1.1.0 UI. Only `transactions/bulk-delete-pair-modal.png` was regenerated (post-07-20). A full `./dev.py mkdocs gallery` regeneration pass is needed before tagging v1.1.0. Priority list (UI verifiably changed since):

| Shot | Why stale |
|---|---|
| `brokers/import-wizard-step1..4-resolution`, `import-wizard-duplicate`, `import-bulk-staging` | wizard reworked to 7-step conditional flow (Aug); spec updated, PNGs not |
| `settings/global-settings` | cache panel + email-verification placeholder badge land **today** |
| `settings/about` | plugin-diagnostics collapsible added to About tab |
| `dashboard/main`, `main-pct`, `kpi-top` | 4th tab (Risk) in the tab bar |
| `brokers/detail`, `info-tab`, `transactions-tab` | 5th tab (Risk) in the broker tab bar |
| `assets/detail-chart`, `detail-signals` + `-ema/-rsi/-macd/-bollinger` | Overview/Risk tab row; signals panel rework (grouped search, KaTeX, diagnostics) |
| `assets/list`, `list-table`, `list-filtered` | 3 usage panels + tx-count badges + asset-set risk panel |
| `fx/detail-signals`, `fx/chart-settings` | backend-plugin panel + live preview |
| `dashboard/positions-*`, `fifo-lots-*` | Annualized + Oldest-open-lot columns, estimated-line dashes |
| (not stale, deleted correctly) | no delete-modal shot remains in inventory — P3-10 alt-text fix landed in gallery pages |

**New shots to add to `gallery.spec.ts`** (no inventory entry exists): `dashboard/risk-tab`, `brokers/risk-tab`, `assets/detail-risk-tab`, `assets/list-risk-panel`, `settings/cache-panel`, `settings/changelog-modal`, `auth/update-available-modal`, `brokers/import-wizard-unify`, `brokers/import-wizard-corrections`, `brokers/import-wizard-duplicates-step` (+ optional `brokers/delete-guard-modal`, `settings/about-plugin-diagnostics`).

---

## Summary counts

| Verdict | Count | Items |
|---|---:|---|
| **Adequate** (verified post-P3) | 14 | AI Export catalog, import wizard 7-step, getting-started import, 19 broker pages + 30-row index, sharing rewrite (roles/leave/cascade/picker), FX manual+CSV, files page, Borsa Italiana funds, positions/annualized/oldest-lot, delete→bulk, SNB monthly, Watchtower guide, generic-csv/eToro, scheduler panel |
| **Partial** | 6 | ownership on dashboard pages, docker `--light` build flag, settings categories, bulk split/promote/merge, data-quality banner foldable, transactions clone documentation |
| **Misaligned** | 6 | signals pages ×2 (4 vs 22 indicators), fx/chart-settings (4 signals + preview + synthetic-benchmark claim), asset detail index, admin/settings scheduler-UTC (**P3-6 not landed**) + email-verification-as-functional, installation "Alpha"/v0.10.0, dashboard/broker tab counts (3→4, 4→5) |
| **Missing** | 9 | **Risk subsystem (whole area — 5 UI surfaces)**, assets usage panels, changelog modal, admin update prompt, cache panel, plugin-diagnostics panel, broker delete guard, "View in Transactions" deep-link, maturity advisory banners |
| Shots: **reusable** in existing pages | 13 | see reuse table |
| Shots: **stale** | ~35 priority (of 115 pre-delta PNGs — full regeneration advised) | see stale table |
| Shots: **new needed** | 12 | risk ×4, cache, changelog, update-modal, wizard conditional steps ×3, diagnostics, delete-guard |

**Top-3 priorities for the docs lane:** (1) create `user/risk.md` (or section) + fix tab counts on dashboard/brokers/asset-detail pages; (2) rewrite the two signals pages + fx/chart-settings against the 22-plugin catalog; (3) land the missed P3-6 scheduler-semantics fix + document today's cache panel and email-verification placeholder in `admin/settings.en.md`. All EN edits will need the IT/FR/ES translation batch (P3-27).


---

# Parte B — Developer docs

# Report 50 — Developer-docs alignment vs v1.0.1..HEAD (+ tree of 2026-09-03)

Scope: `mkdocs_src/docs/developer/**` only (EN-only by design). Inputs: 98 commits
`v1.0.1..HEAD`, CHANGELOG `[1.1.0]`, the 08 audit reports (their findings are NOT
repeated here — this report builds on top), and today's uncommitted tree
(SETTINGS_REGISTRY, cache admin endpoints, spawn-worker coverage sitecustomize,
C901/TRY400/S110/RUF022 gates, `expectChartCanvas`, `utils/json_utils.py`,
discriminator post-processor rule, TS client regen, `get_effective_base_currency`,
fifo_utils.py / AssetMetadataService / BaseDropdown / TransactionTypeBadge removals).

Method: every claim below was verified with grep/view against the current tree.
The 08 audit already covers *user/admin/theory* docs (its `mkdocs/01` and
`mkdocs/02` reports); this lane covers the **developer manual** only.

---

## 1. Area-by-area table

| # | Area (changed since v1.0.1) | Dev page today | Status | What's missing / misaligned | Priority |
|---|---|---|---|---|---|
| 1 | **Risk subsystem** (9 analytics, plugin registry, `spawn` workers, QuantLib/Riskfolio isolation, error taxonomy, per-result status, scenario catalog) | *none* — no page under `developer/backend/`, nav has no risk entry; only passing mentions of "risk" in unrelated pages | **missing** | Entire subsystem undocumented for developers: `backend/app/services/risk/` (service.py, base.py, metrics.py, `quant/` with `spawn_worker.py`/`quantlib_worker.py`/`riskfolio_worker.py`, `scenario_catalog/`), `/api/v1/risk` endpoints (catalog/query/scenario-catalog), scope-neutral analytics contract, worker lifecycle/reaping, error taxonomy + result status semantics. Biggest gap in the manual. | **blocks-new-dev** |
| 2 | **Signals backend platform** (22 plugins, `SignalService`, registry, annotations, fail-fast runtime, `POST /signals/preview`) | `architecture/patterns/signal_plugin_guide.md` (good, current) | **adequate** (guide) / **partial** (platform) | The plugin *authoring* guide is solid and matches code. Missing: a platform-level page (SignalService plan/coverage/execute/validate pipeline, the `/signals/preview` synthetic-curve endpoint used by global chart settings, frontend `lib/charts/signals/backendRenderer.ts` consumption path — zero dev-doc hits). | nice |
| 3 | **AI Export rebuilt catalog** (V1 contract, 67 components / 40 datasets / 11 analyses / 8 public datasets, task-aware composition, lot detail v2) | `architecture/patterns/ai_export_snapshot.md` + `composition` + `sampling` + `probe_workflow` | **adequate** | Catalog table in `ai_export_snapshot.md` matches CHANGELOG counts exactly; legacy-runtime removal explicitly stated ("no legacy builder fallback"). Verified current. | — |
| 4 | **BRIM: 19 new plugins + duplicate resolver + instrument unification** | `backend/brim/architecture.md`, `brim/providers_list.md`, `brim_plugin_guide.md`, `frontend/components/features/import-wizard.md`, `frontend/components/features/asset-identity.md` | **adequate** | `providers_list.md` lists all 30 importers incl. CA XLSX + Directa XLSX; architecture page documents the 7-step conditional wizard, unify-before-duplicates ordering and cross-file arbitration; asset-identity page documents the similarity engine. The N-way compare modal and file-priority list UI internals are thin but the architecture is covered. | nice |
| 5 | **Asset identity / unified price resolver; legacy valuation removed** | `backend/transactions/lots_analysis_service.md` (resolver tiers MARKET→TRADE_AVG→CARRIED→MISSING documented), `backend/transactions/fifo_lot_engine.md`; theory page `financial-theory/.../price-resolution.en.md` | **partial** | Resolver is documented *as consumed by lots analysis* but there is no developer page for `backend/app/services/price_resolver.py` itself (its contract is the single source for NAV/MWRR/TWRR/ROI — portfolio_engine consumption, staleness/backward-fill contract, and the "resolver is the only valuation path" invariant after legacy removal are only stated in the lots page). No mention of the removed `LIBREFOLIO_RESOLVER_VALUATION` flag era — fine — but no page owns the resolver contract. | **blocks-new-dev** (medium) |
| 6 | **Provider registry `params_schema` + plugin diagnostics endpoint** | `architecture/patterns/registry_pattern.md`, plugin guides, `backend/assets/architecture.md` (`params_schema` row present) | **partial** | `params_schema` is documented per-guide. Missing everywhere: `GET /api/v1/system/plugin-diagnostics` (per-registry load-failure reporting, surfaced in Settings → Info). Not in `developer/api/index.md`, not in registry_pattern.md, not in any plugin guide. | nice |
| 7 | **Test runner: catalogue, reachability, isolation classes, parallel Playwright, jsdom harness, JS/Svelte istanbul coverage** | `test-walkthrough/runner_architecture.md` (796 lines), `coverage-model.md`, `e2e.md` | **adequate** | Catalogue/reachability/ownership classes documented; V8/istanbul JS coverage documented. | — |
| 8 | **Spawn-worker coverage sitecustomize** (`backend/test_scripts/_coverage_sitecustomize/sitecustomize.py`, `COVERAGE_PROCESS_START`, Homebrew chain-exec coexistence) | *none* — `coverage-model.md` covers V8/istanbul for JS but has zero hits for spawn/multiprocessing/subprocess Python coverage | **missing** | The whole "coverage follows spawn children" mechanism (why spawn workers measured 0%, the `.coveragerc` `concurrency=multiprocessing` + `parallel=true` recipe, the Homebrew sitecustomize shadowing pitfall and the chain-exec rule) is documented only in the file's own docstring. A dev editing the runner or adding a spawned subsystem will rediscover the pitfall. | **blocks-new-dev** (small) |
| 9 | **Lint gates: ruff C901@10 + justified-noqa policy, TRY400, S110, RUF022** (`pyproject.toml`) | *none* — `dev_workflow.en.md` lint section lists only `./dev.py format` / `./dev.py lint` commands; zero hits for C901/TRY400/S110/RUF022/noqa-policy in the whole developer manual | **missing** | The policy the audit fought for ("levels zero don't hold without gates") is enforced in `pyproject.toml` but written down nowhere for developers: gate list, the justified-`# noqa: C901` convention for flat data packers vs `TODO(P2-refactor)` markers, the 5 comment-grouped barrels carrying `# noqa: RUF022`, `logger.exception`-over-`logger.error`-in-except (TRY400), no `except: pass` (S110). | **blocks-new-dev** |
| 10 | **Settings architecture: SETTINGS_REGISTRY + user-vs-global split + `get_effective_base_currency`** (`schemas/settings.py`, `settings_service.py`, scheduler/settings) | `architecture/settings.md` (61 lines) | **misaligned** | Page still describes the pre-1.1 world: says global settings "are managed via the `user_cli.py` script" and "Future versions will allow administrators to modify these settings through an admin UI" (the admin UI exists; the Global Settings admin page is even screenshotted in the frontend settings page). Missing: SETTINGS_REGISTRY as the single declaration point (`SettingSpec`, `user` typed columns vs `global_` key-value rows, `GLOBAL_SETTINGS_DEFAULTS` as source of defaults), the registry-constant call-site convention, and `get_effective_base_currency` (per-user → global default → EUR) — the helper fixed by audit P0 is absent from every dev page. | **blocks-new-dev** |
| 11 | **Cache registry + admin endpoints** (`GET /settings/cache/status` all-users, `POST /settings/cache/clear-all` + `/clear/{name}` admin-only; `utils/cache_utils.py` registry; `CachePanel.svelte`; CAPI-001..008 tests) | *none* | **missing** | New public API surface (3 endpoints) + new admin UI panel + the named-cache registry pattern in `cache_utils.py` are undocumented: nothing in `architecture/settings.md`, `api/index.md`, `frontend/components/features/settings.md`, or the security/access-control pages (the "read for all, clear admin-only" split is a deliberate access decision that belongs in `access_control.md`/settings docs). | **blocks-new-dev** |
| 12 | **Frontend: Svelte 5 runes adoption** | `frontend/index.md`, `frontend/state/index.md` | **adequate** | Runes policy stated up-front; `$:` regression noted in audit 10 is a code-debt matter, not docs. | — |
| 13 | **Frontend: shared settings wrappers with embedded prop; tx bulk workspace flows** | `frontend/components/features/settings.md`, `frontend/state/transaction-draft.md` | **partial** | `transaction-draft.md` documents the bulk staging sandbox well (incl. single-row delete routing through the workspace — consistent with TransactionDeleteModal removal). `settings.md` documents SettingsLayout/field components but has no CachePanel and no description of today's reworked Setting* wrappers (SettingCurrency/SettingSelect/SettingTheme/SettingToggle modified in tree with the embedded prop pattern). | nice |
| 14 | **`expectChartCanvas` e2e fixture + `data-chart-ready` product signals** | `test-walkthrough/e2e.md` documents `data-busy` waits; zero hits for `expectChartCanvas`/`data-chart-ready` | **partial** | The "wait on product state, never on the clock" philosophy is documented with `data-busy` as the example, but the chart-readiness signal contract (`data-chart-ready`, the `e2e/fixtures/charts.ts` helper now used by 4+ specs) is not mentioned — the natural place is e2e.md next to the `data-busy` example. | nice |
| 15 | **API contract discipline: response_model everywhere + discriminator post-processor rule + `json_schema_extra` enum** | `api/overview.md`, `api/index.md` | **partial** (overview) / **misaligned** (index) | `api/overview.md` documents the OpenAPI-first sync workflow but not the *rules* the pipeline now depends on: (a) every new member of a discriminated union must be registered in `frontend/scripts/fix-openapi-discriminators.mjs` (40 schemas today) or the generated TS client fails to compile; (b) discriminator fields want `Field(json_schema_extra={"enum": [...]})`; (c) response_model-on-every-endpoint discipline (audit: 17→6 stragglers). `api/index.md` router list stops at `/brim` — missing `/signals`, `/risk`, `/ai-export`, `/settings` cache routes. | **blocks-new-dev** (the discriminator rule breaks the build for anyone who doesn't know it) |
| 16 | **`utils/json_utils.py` validator-vs-sanitizer split** | *none* | **missing** (minor) | `ensure_json_safe` (validator, contract boundaries) vs `_json_safe_details` (sanitizer, provider probe) — the "do not merge them" policy lives only in module docstrings. One paragraph in a backend conventions page would do. | nice |
| 17 | **Base-currency resolution helper** (`get_effective_base_currency`: user → global → EUR; 4 call sites) | *none* (frontend state pages mention `settingsStore` base currency; backend helper undocumented) | **missing** | Folded into row 10 recommendation; listed separately because it was audit P0 bug #2/#4 — the fix's architecture (who wins when both user and global define a currency) is exactly the kind of decision the dev manual should record. | **blocks-new-dev** (with #10) |
| 18 | **Ownership-aware dashboard / broker self-service leave flows** | `architecture/users_and_brokers.md`, `architecture/access_control.md` | **partial** | Access-control page covers roles; the new semantics (0% ownership share valid, share-scaled dashboard aggregation, editor self-demote, last-owner-leaves-deletes-broker cascade) are not spelled out in the dev pages — only in user docs/CHANGELOG. | nice |

---

## 2. Developer docs that describe REMOVED things

Verified each removed symbol against the whole `developer/**` tree:

| Removed thing (when) | Doc mentions found | Verdict |
|---|---|---|
| **Legacy valuation engine** (`LAST_BUY_PRICE` / `LAST_SEED_COST` tiers, `LIBREFOLIO_RESOLVER_VALUATION` flag — removed in `2718ba90`) | none | ✅ clean — no dev doc references the legacy cascade |
| **Legacy AI Export runtime** (profile/assembler stack — removed in `615a52eb`) | `ai_export_snapshot.md:73,134` mention it only to say it no longer exists | ✅ clean (mentions are historical/correct) |
| **`fifo_utils.py`** (deleted today, tree) | none | ✅ clean |
| **`TransactionDeleteModal`** (removed in beta wave) | none | ✅ clean (audit 09 already confirmed surgical removal) |
| **Currency-graph invalidation** (`cachedProvidersHash`, `invalidateCurrencyGraph` — removed 03/09) | none | ✅ clean |
| **`AssetMetadataService`** (deleted today, tree; test file also gone) | only `fetch_asset_metadata()` provider-method hits — a *different* thing | ✅ clean |
| **`compute_wac_iterative_multi_broker`** (deleted today, tree — audit finding #6) | `wac.md` documents only the single-broker path | ✅ clean |
| **`TransactionTypeBadge.svelte`** (deleted today, tree) | none in `developer/**` | ✅ clean |
| **`BaseDropdown.svelte`** (deleted today, tree) | 🔴 **4 stale hits**: `frontend/components/core-ui/select.md` presents BaseDropdown as *the foundation of the whole select hierarchy* (mermaid diagram + prose); also `frontend/components/index.md:15`, `frontend/index.md:42`, `test-walkthrough/front-utility.md:14` | **STALE — must fix.** The component was deleted as an orphan (knip), so SimpleSelect/SearchSelect now self-contain open/close & positioning; select.md's core claim ("All select components are built on BaseDropdown") is false as of today. |

Net: the removal hygiene in dev docs is remarkably good — the audit's surgical-removal work held. The **only** stale-removal cluster is BaseDropdown, introduced by today's uncommitted tree.

---

## 3. NEW pages that should exist

**A. `developer/backend/risk/architecture.md`** (blocks-new-dev)
The Risk subsystem has no developer page at all. Should cover: the 9 analytics and the plugin registry (`base.py`, scope/return-mode contract per analytic); process isolation — `quant/spawn_worker.py` + QuantLib/Riskfolio dedicated workers, idle reaping, why a hung optimisation can't take down the event loop; the error taxonomy (`insufficient_history` … `execution_timeout`) and per-result status (`ok/partial/unavailable/failed`); the scenario catalog (built-ins, typed/audited scenarios); `/api/v1/risk` endpoints; and the beta contract caveat.

**B. `developer/architecture/settings.md` rewrite (or new `settings_registry.md`)** (blocks-new-dev)
Current page predates 1.1. Should document: the two storage models (typed `UserSettings` columns vs key-value `GlobalSetting` rows) and *why they stay separate* (P2-9 decision); `SETTINGS_REGISTRY`/`SettingSpec` as the single declaration point, with the registry-constant call-site convention and the legitimate exceptions (Alembic, tests); `GLOBAL_SETTINGS_DEFAULTS` as defaults source; `get_effective_base_currency` resolution chain (user → global → EUR); and the cache-admin endpoints with their access split (status readable by all authenticated users, clears admin-only) plus the CachePanel UI.

**C. `developer/test-walkthrough/coverage-model.md` — new "Python subprocess/spawn coverage" section** (blocks-new-dev, small)
Document the sitecustomize mechanism: `_coverage_sitecustomize/` on PYTHONPATH, `COVERAGE_PROCESS_START` + `.coveragerc` (`concurrency=multiprocessing,thread,gevent`, `parallel=true`), parallel data files and combine; the load-bearing no-op guard outside coverage runs; and the Homebrew `sitecustomize` shadowing pitfall with the chain-exec rule (P1-13) — the single most surprising infrastructure trap of this cycle.

**D. `developer/api/overview.md` — new "Contract rules" section** (blocks-new-dev)
The three rules that break the build when unknown: (1) every endpoint declares `response_model`; (2) every new discriminated-union member is registered in `frontend/scripts/fix-openapi-discriminators.mjs` (list why: `openapi-zod-client`'s exported `z.ZodType<T>` annotation hides the ZodObject methods `z.discriminatedUnion` needs); (3) discriminator fields carry `Field(json_schema_extra={"enum": [...]})`. Also refresh `api/index.md`'s router list (`/signals`, `/risk`, `/ai-export`, settings-cache).

**E. `developer/backend/transactions/price_resolver.md` (or a section in assets/architecture)** (blocks-new-dev, medium)
Give `backend/app/services/price_resolver.py` its own contract page: the tier ladder MARKET → TRADE_AVG → CARRIED/LOCF → MISSING, determinism/purity, staleness reporting under the backward-fill contract, who consumes it (NAV, MWRR, TWRR, ROI, lots analysis, AI Export), and the post-1.1 invariant "the resolver is the only valuation path" (legacy cascade and transition flag gone).

**F. `developer/architecture/patterns/registry_pattern.md` — plugin-diagnostics paragraph** (nice)
One section on `GET /api/v1/system/plugin-diagnostics`: per-registry load failures, why a missing runtime dependency (e.g. openpyxl-as-devDep bug) is now diagnosable, and where the UI surfaces it (Settings → Info).

---

## 4. Summary counts

- Areas surveyed: **18**
- **adequate**: 5 (AI export docs, BRIM architecture/list, asset identity, test runner core, Svelte-5 runes)
- **partial**: 6 (signals platform level, price resolver, params_schema+diagnostics, settings wrappers, expectChartCanvas, broker self-service)
- **misaligned**: 2 (`architecture/settings.md` — pre-1.1 world; `api/index.md` — router list stale)
- **missing**: 5 (risk subsystem, spawn coverage, lint-gate policy, cache admin, json_utils policy)
- **blocks-new-dev**: 8 rows (#1, #5, #8, #9, #10, #11, #15, #17 — several merge into the 6 proposed pages/sections)
- Stale-removal doc clusters: **1** (BaseDropdown — 4 files, introduced by today's tree); all other 8 removed-thing checks clean.

Top three actions, in order: (1) write the Risk architecture page — the largest shipped-but-undocumented subsystem; (2) rewrite `architecture/settings.md` to cover SETTINGS_REGISTRY + cache admin + base-currency resolution (fixes rows 10/11/17 in one pass); (3) fix the BaseDropdown staleness in `select.md` + 3 cross-refs before today's tree is committed.


---

# Parte C — Gallery (`frontend/e2e/gallery.spec.ts`)

# Report 50 — Gallery spec audit vs current UI (post v1.0.1 → HEAD 0550bc73)

Scope: `frontend/e2e/gallery.spec.ts` (2 948 lines, ~76 distinct shots × 4 langs × 2 themes × desktop/mobile).
Method: static read of the spec + grep of every testid/selector against `frontend/src`. No tests run.

Headline: **the spec would still run mostly green — three shots are silently dead** (selectors removed from the UI, guarded by `if (isVisible)` so nothing fails), **four more signal-variant shots silently skip** for the same reason, and the 7-step import-wizard rework left the step shots nominally working but visually stale, with the 3 new conditional steps completely unshot.

---

## 1. Shot-by-shot status

| category/name | still accurate? | stale because | action |
|---|---|---|---|
| auth/01-login | ✅ yes | — | keep |
| auth/02-register-empty | ✅ yes | — | keep |
| auth/03-register-filled | ✅ yes | — | keep |
| dashboard/kpi-top | ⚠️ stale content | Card 3 (Net Worth) now shows absolute ROI delta (`kpi-total-pnl-delta`) + KpiMetricBar start markers + cash composition tooltip; foldable DataQualityBanner (`data-quality-toggle`, collapsed by default) sits above; broker-filter panel in header row | update (regenerate) |
| dashboard/main | ⚠️ stale content | same header/banner/filter context | update |
| dashboard/main-pct | ⚠️ stale content | same | update |
| dashboard/menu-open | ✅ yes | mobile-only; Header unchanged | keep |
| dashboard/allocation-type-now / -history | ✅ yes | AllocationPanel untouched (tabs still `allocation-tab-{type,sector,geo}`, view-now/history) | keep |
| dashboard/allocation-sector-now / -history | ✅ yes | — | keep |
| dashboard/allocation-geo-now / -history | ✅ yes | — | keep |
| dashboard/positions-holdings-table / -map | ✅ yes | `positions-toggle-*`, `exposure-table`, `exposure-treemap` intact | keep |
| dashboard/positions-performance-table / -map | ✅ yes | `contribution-table`, `performance-chart` intact | keep |
| dashboard/fifo-lots-panel | ✅ yes | `lots-analysis-panel` intact | keep |
| dashboard/fifo-lots-wac-chart / -gantt-chart / -table / -comparison-chart / -comparison-chart-return / -custody-modal | ✅ yes | lot testids all present | keep |
| dashboard/transactions-tab | ✅ yes | `dashboard-tab-transazioni` intact | keep |
| dashboard/empty-state | ✅ yes | — | keep |
| settings/user-preferences | ✅ yes | `preference-language/currency/theme` intact | keep |
| settings/global-settings | ⚠️ stale content | Admin tab now embeds **CachePanel** (`GlobalSettingsTab.svelte:771`) and the **email placeholder badge** (`require_email_verification` in `PLACEHOLDER_KEYS`) | update |
| settings/about | ✅ yes | — | keep |
| settings/password-modal | ✅ yes | — | keep |
| settings/profile | ✅ yes | tab testid composed dynamically `settings-tab-{id}` ✓ | keep |
| settings/scheduler-config | ⚠️ stale content | **timezone-aware since 31/08**: modal has IANA tz picker (`selectedTz`, tz dropdown) — shot predates it | update |
| settings/scheduler-log | ⚠️ minor | log modal itself unchanged, but shown times now follow scheduler tz semantics | update |
| files/static-tab, brim-tab, static-grid | ✅ yes | `files-table-{static,brim}`, `view-mode-grid` intact | keep |
| files/preview-modal-csv / -image / -pdf / -markdown / -text | ✅ yes | `file-preview-modal` + `context-menu-action-preview` intact | keep |
| transactions/list | ✅ mostly | row-access badges / kebab-only actions now; selectors fine | update (cheap regenerate) |
| transactions/form-modal + 11 type variants | ⚠️ stale content | `tx-add-button`/`tx-form-modal`/`tx-form-type` intact; form gained WAC section + locked placeholders in dual layouts | update |
| transactions/picker-modal | ❌ **dead** | uses `button[data-action-id="edit"]` (line 1182) — removed 2026-07-18 (05712844); row actions are kebab-only now → **silent skip, no shot** | fix selector → `clickRowAction(row,'edit')`; keep name |
| transactions/action-modal | ❌ **dead** | uses `button[data-action-id="split"]` (line 1234) — same removal → silent skip | fix selector → `clickRowAction(row,'split')`; keep name |
| transactions/promote-merge-modal | ✅ yes | `toolbar-action-promote` composed by DataTableToolbar from `bulkActions` id `promote` ✓; skips if no compatible pair in mock (by design) | keep |
| transactions/bulk-delete-pair-modal | ✅ yes (retargeted) | T4 done right: dedicated delete modal removed; spec already shoots the **bulk workspace** (`tx-bulk-modal` + `tx-bulk-split-hint`, one collapsed `row-deleted`). Name kept for doc compat — content is the replacement shot the mission asks for | keep |
| brokers/list, detail, edit-modal, sharing-modal, info-tab | ✅ yes | all testids present | keep |
| brokers/positions-* (4) | ✅ yes | shared `screenshotPositionsVariants` helper | keep |
| brokers/fifo-lots-* (6) | ✅ yes | — | keep |
| brokers/transactions-tab | ✅ yes | — | keep |
| brokers/import-modal | ✅ yes | `import-files-modal` intact | keep |
| brokers/import-wizard-step1 | ⚠️ stale frame | still step `upload` (`import-wizard-step1` ✓) but stepper now renders up to 7 slots | update |
| brokers/import-wizard-step2 | ⚠️ stale frame | still step `select` ✓ | update |
| brokers/import-wizard-step3 | ⚠️ stale frame | still step `analyze` (parse results) ✓ | update |
| brokers/import-wizard-step4-resolution | ⚠️ stale frame + ⚠️ latent break | still the **review** step (`import-wizard-step4` kept) with resolve section ✓ — but this test (line 1714) lacks the `import-wizard-warning-confirm` guard its two siblings have: if parse yields warnings, `goNext` shows the overlay and the 10 s wait on step4 **hard-fails** | update + add warning guard |
| brokers/import-wizard-duplicate | ⚠️ stale frame | review-step tx table with "likely duplicate" badges; DB collisions still skip the duplicates step → flow still lands on review ✓ | update |
| brokers/import-bulk-staging | ❌ **dead** | uses `button[data-action-id="edit"]` (line 1828) → silent skip | fix selector; keep name |
| media/image-edit-modal | ✅ yes | `[data-cropper-ready]` still emitted by ImageCropper ✓ | keep |
| media/asset-picker-modal | ✅ yes | — | keep |
| media/file-uploader-empty | ✅ yes | — | keep |
| fx/list, list-table, list-filtered | ✅ yes | `fx-page`, `view-mode-list`, `fx-currency-filter` intact | keep |
| fx/add-pair-routes, add-pair-chain | ✅ yes | `fx-route-select`, `fx-route-direct-section`, `fx-route-chain-section` intact | keep |
| fx/sync-progress | ✅ yes | `fx-sync-all-button` intact (shoots whatever modal appears after 1.5 s) | keep |
| fx/detail-chart | ✅ yes | — | keep |
| fx/detail-signals | ⚠️ stale content | panel now backend-driven (spinner via `signalsLoading`) with 3 category tree-selects (indicator/comparison/benchmark) | update |
| fx/detail-measures, detail-editor, detail-csv-import | ✅ yes | `fx-detail-*`, `data-import-modal` intact | keep |
| fx/chart-settings | ✅ mostly | `chart-settings-modal` intact; modal now contains the signals catalog section | update (cheap) |
| fx/provider-config | ✅ yes | `fx-add-pair-modal` in editMode ✓ | keep |
| assets/list | ⚠️ stale content | **F15**: page is now 3 usage panels (`assets-panel-{own/others/watched}`) in grid + badges | update |
| assets/list-table | ⚠️ stale content | F15 round-2: **3 stacked tables** + new `txCount` column; `view-mode-list` intact | update |
| assets/list-filtered | ⚠️ stale content | search now filters across the 3 panels | update |
| assets/detail-chart, detail-chart-candlestick | ✅ yes | `chart-type-line/candlestick` intact | keep |
| assets/detail-signals | ⚠️ stale content | backend-driven panel + spinner; toggle testid intact | update |
| assets/detail-signals-ema / -rsi / -macd / -bollinger | ❌ **dead ×4** | options now `role="treeitem"` (grouped SignalTreeSelect, signals backend platform 557bb2b5); spec filters `[role="option"]` (lines 2586, 2627, 2668, 2709) → **silent skip**. `signals-indicator-select-button` itself still exists | fix selector → `signal-tree-option-*` testids |
| assets/detail-measures, detail-measures-active | ✅ yes | — | keep |
| assets/detail-classification | ✅ yes | — | keep |
| assets/detail-editor | ✅ yes | — | keep |
| assets/create-modal | ✅ yes | — | keep |
| assets/create-wizard-modal | ✅ yes | wizard flow + warning guard present ✓ | keep |

Steps of the 7-step wizard vs shots: `upload`→step1 ✓, `select`→step2 ✓, `analyze`→step3 ✓, **`assets`→NO SHOT**, **`fix`→NO SHOT**, **`duplicates`→NO SHOT**, `review`→step4-resolution + duplicate ✓.

## 2. Missing shots needed

| area/page | proposed category+name | what it should show | doc page that would use it |
|---|---|---|---|
| Import wizard — Unify step | brokers/import-wizard-step-assets | AssetGroupStep with a `proposed` group (needs a 2-file fixture with the same security under two codes) | user/brokers/import.en.md (describes 🧬 step, no image) |
| Import wizard — Corrections step | brokers/import-wizard-step-fix | FixFlaggedStep with a flagged row settled/pending | user/brokers/import.en.md (🧹/corrections prose) |
| Import wizard — Duplicates step | brokers/import-wizard-step-duplicates | `import-wizard-duplicate-resolver`: file-priority list + Total-overlap/Partial groups | user/brokers/import.en.md (duplicates prose) |
| Dashboard risk tab (beta) | dashboard/risk-tab | RiskAnalysisPanel (`dashboard-tab-risk` / `risk-analysis-panel`) with catalog loaded | new user page or user/dashboard/index.en.md; financial-theory risk-metrics pages could embed it |
| Broker risk tab | brokers/risk-tab | per-broker RiskAnalysisPanel (`broker-tab-risk`) | user/brokers/*.en.md |
| Assets correlation tab | assets/correlation-tab | AssetSetRiskPanel + CorrelationHeatmap (`assets-tab-correlation`) | user/assets/index.en.md |
| AI Export menu | dashboard/ai-export-menu (+ assets/ai-export-panel, fx/ai-export-panel, brokers/ai-export-panel) | `ai-export-button` → `ai-export-menu-panel` + `ai-export-options-panel` | user/ai-export/{index,portfolio,asset,broker,fx}.en.md — **all five currently have zero images** |
| Changelog modal (F12) | settings/changelog-modal | `changelog-modal` with index chips + foldable chapters | user/settings/about.en.md / misc |
| Admin update modal (F14) | settings/update-available-modal | `update-available-modal` version badges + guide link | admin docs (updating guide) |
| Cache panel | settings/cache-panel | CachePanel section of admin tab (folds into global-settings) | admin/settings.en.md |
| Data-quality banner expanded | dashboard/data-quality-banner | `data-quality-toggle` expanded with issue chips + CTAs | user/dashboard/index.en.md |
| Assets global page (whole) | assets/list-panels | annotated 3-panel view (own/others/watched) | user/assets/index.en.md |
| Broker access / sharing panel (F4) | brokers/access-panel | `broker-sharing-section` inline in info tab | user/brokers/sharing.en.md (has sharing-modal; inline panel unshot) |
| Tx clone flow | transactions/form-modal-clone | form pre-filled from kebab `context-menu-action-clone` | user/transactions/form.en.md |
| Mobile variants | — | already comprehensive: every shot runs in the mobile project; menu-open is mobile-only | — (no action) |

## 3. Reusable existing shots

| doc page lacking images | existing shot that fits |
|---|---|
| user/fx/detail/index.en.md | fx/detail-chart |
| user/pwa.en.md | dashboard/menu-open (mobile) |
| user/settings/index.en.md | settings/user-preferences |
| user/transactions/import/index.en.md + 28 per-broker pages (avanza…xtb) | brokers/import-modal, brokers/import-wizard-step1/step2 |
| user/transactions/import/generic-csv.en.md | brokers/import-wizard-step3 (generic parse) |
| user/assets/providers/*.en.md (6 pages) | assets/create-modal (provider config section) |
| user/fx/providers/*.en.md (5 pages) | fx/provider-config |
| user/assets/detail/events.en.md | ❌ none fits — event popover was never shot (gap) |
| user/ai-export/*.en.md | ❌ none fits — needs new shots (see §2) |
| admin/* (cli_tools, configuration, docker_advanced, filesystem, host_installation, index, service_exposure) | mostly prose by nature; admin/settings shots already exist for settings page |

## 4. Spec breakage risk (grep evidence)

| selector in gallery.spec.ts | status in current UI | evidence |
|---|---|---|
| `button[data-action-id="split"]` (L1234) | **REMOVED** — row actions are kebab-only: DataTable renders only `row-actions-{rowId}`; split lives in ContextMenu as `context-menu-action-split` | `grep -rn "data-action-id" src/` → 0 hits (3 hits remain, all in gallery.spec.ts). Removed in 05712844 (2026-07-18). DataTable.svelte:1348; ContextMenu.svelte:154; TransactionsTable.svelte:920 (id `split`) |
| `button[data-action-id="edit"]` (L1182, L1828) | **REMOVED** — same commit | same grep; TransactionsTable.svelte:900 (id `edit`) |
| `[role="option"]` for EMA/RSI/MACD/Bollinger (L2586/2627/2668/2709) | **REPLACED** — grouped SignalTreeSelect renders `role="treeitem"` (flat only on the comparison dropdown) | SignalTreeSelect.svelte:232 `role={flat ? 'option' : 'treeitem'}`; options carry `data-testid="signal-tree-option-{value}"` (L239). Introduced by signals backend platform (557bb2b5) |
| `signals-indicator-select-button` | OK | SignalTreeSelect renders `{testId}-button` (L266) |
| `import-wizard-step4` as "review" | OK but shifted semantics: `enterNextActiveStep` lands on `assets`/`fix`/`duplicates` first when active; for generic_simple.csv they stay inactive (single file → all groups `single`; no fix-step todos — missing-WAC is cost-basis, excluded by `isFixStepTodo`; DB collisions never open `duplicates`, ImportWizardModal.svelte:2580-2586) → flow still reaches review | ImportWizardModal.svelte:2641-2651 |
| missing `import-wizard-warning-confirm` guard in "step 4 asset resolution" test (L1714) | latent hard failure: `goNext` shows the warnings overlay when `step3Warnings.length > 0` (L2666-2669); both sibling tests (L1775-1779, L2887-2891) carry the guard, this one doesn't → 10 s timeout if a warning appears | ImportWizardModal.svelte:4604 (overlay button); guard present in spec since 3254909f |
| all other testids (≈90 checked: kpi-*, allocation-*, positions-toggle-*, date-preset-{1y,max}, settings-tab-*, scheduler-*, files-table-*, fx-*, asset-detail-*, broker-*, lot-*, import-wizard-{stepper,step1..4,next,parse,continue,warning-confirm}, tx-*, view-mode-*, file-uploader, data-cropper-ready, confirm-modal-*) | present | per-testid grep in session log; dynamic compositions verified (`settings-tab-{id}`, `allocation-tab-{tab}`, `date-preset-{key.toLowerCase()}`, `files-table-{type}`, `toolbar-action-{id}`) |

**Would `./dev.py mkdocs gallery` run green?** Yes — almost surely. All breakage is *silent* (guarded `isVisible` → skip, never assert), so the run stays green while 7 shots quietly stop being regenerated. Old PNGs persist on disk (`mkdocs_src/docs/gallery/desktop/en/light/transactions/action-modal.png` etc.), so docs keep rendering stale images — doc rot with no failure signal. Only hard-failure risk: the warning-overlay guard gap in `import-wizard-step4-resolution`.

## Summary counts

- Shots audited: **76** distinct names (auth 3, dashboard 17, settings 7, files 8, transactions 17, brokers 21, media 3, fx 13, assets 16 — variants counted individually).
- ✅ Accurate as-is: **45**
- ⚠️ Stale content/frame — regenerate: **17** (kpi-top, main, main-pct, global-settings, scheduler-config, scheduler-log, transactions/list, form-modal ×12 counting variants as one line each in table, import-wizard step1/2/3/4-resolution/duplicate, fx/detail-signals, fx/chart-settings, assets/list, list-table, list-filtered, detail-signals)
- ❌ Dead (silent skip, selector removed): **7** — transactions/picker-modal, transactions/action-modal, brokers/import-bulk-staging, assets/detail-signals-{ema,rsi,macd,bollinger}
- Missing shots proposed: **13** (incl. 3 new wizard steps, 3 risk surfaces, 4 AI-export surfaces, changelog, update, cache, data-quality, clone)
- Doc pages with zero images: **52** (.en.md), of which ~15 have a fitting existing shot (§3) and the ai-export set needs new shots.
- REMOVED components referenced by spec: TransactionDeleteModal — **none** (spec already retargeted to bulk workspace, T4); only the 2 removed selector patterns above.
