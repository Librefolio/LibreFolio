# Plan — Broker Import Recovery (Intesa + Credit Agricole) & UX/Data-Integrity Fixes

> Recovery plan after Marco's prod import (user `marco` / prod DB
> `backend/data/prod/sqlite/app.db`). Root-causes two data-integrity bugs and tracks
> the plugin / import-wizard / asset-search improvements noted during the import.
>
> **Scope decision = `code_only`** — no prod repair script is written; the plan documents
> exactly what was wrong so the user can correct / re-import their own data.

Related history:
- BRIM bridge / import wizard: `phases/phase-07-subplan/Parte5/plan-phase07Part5-BRIMImportBridge.prompt.md`
- BRIM plugin guide (dev): `.github/skills/brim-tools/brim-plugin/SKILL.md` + backend dev manual

---

## 0. Context

The user recovered more broker exports (Intesa "Marco", Credit Agricole "Nonna Anna"),
built the two BRIM plugins, imported into prod, and observed a broken portfolio engine
(a BTP showing `-917k / -99.99%`) plus a `-3.95B` unrealized-variation figure. Investigation
found **two independent bugs** (RC-A, RC-B) and produced a batch of plugin / wizard / search
improvements.

---

## 1. Root causes (confirmed)

### RC-A — Quantity 1000× corruption (`-917k / -99.99%` display)
- The Intesa plugin emitted `quantity: "91.861"` **correctly** (verified in the saved parse
  JSON). Backend Pydantic coercion is also correct (`Decimal('91.861')`).
- The DB stored `91861` on the tx, whose `updated_at` ≠ `created_at`: the row was **manually
  edited after import** and saved corrupted (in-place UPDATE, not a re-import). Sibling rows
  that were never edited survived.
- Mechanism: the transaction edit form used `<input type="number">`. In an **Italian-locale
  browser** `type="number"` treats `.` as a **thousands separator**, so a dot-decimal like
  `91.861` round-trips to `91861` on save. This is the user's "virgola e punto delle migliaia"
  bug — it is the **quantity**, not the WAC (the stored WAC `9990.96` is correct).

### RC-B — Systematic asset mis-mapping (patrimonio seeds → wrong assets)
- Broker seed ADJUSTMENTs carried descriptions naming EURIZON funds / specific BTPs but were
  linked to unrelated positionally-adjacent assets.
- The plugin emitted the **correct ISINs** and the matching assets already existed with those
  exact ISINs (created before the patrimonio import). The wizard did **not auto-bind
  exact-ISIN matches**; a wrong manual default was accepted. A **wizard** bug, not the plugin.

---

## 2. Decisions (confirmed with user)

| Topic | Decision |
|-------|----------|
| Repair scope | `code_only` — no prod repair script; document the correction path. |
| **CA succession** (`GIRO ALTRO DOSSIER` / `VERS.TITOLI`) | **cashless ADJUSTMENT** (transfer-in from an untracked dossier — no money spent → **no DEPOSIT**). *This reverses the earlier BUY+DEPOSIT idea.* Origin causale kept in the description; per-unit book price carried via `cost_basis_override`. |
| CA cash model | Securities-only export → **BUY gets a matching DEPOSIT**, **SELL gets a matching WITHDRAWAL** (CA is also a normal bank; the export lists only titoli). Succession is the exception: cashless, no DEPOSIT. |
| Matured-bond redemption (`TITOLI SCADUTI`) | Bonds quoted at 100. Redemption price > 100 (e.g. `100.40`, `100.80`) → the excess is **interest/coupon**, modeled atomically as **SELL @ 100 + DIVIDEND for the excess**. Documented as a plugin note. Applies to **all** plugins, not only CA. |
| Opening boundary (Step 4 non-importable) | **`<=`** — rows dated **on or before** the broker opening date are non-importable (opening day inclusive in the block, so patrimonio seeds must be dated **after** the opening date). |
| Succession warning wording | Faithful-to-report, "cashless ADJUSTMENT (transfer-in … no DEPOSIT)". |

---

## 3. Workstreams — status

### A — Quantity / decimal input corruption (frontend, RC-A) — ✅ done
- **A1** Locale-fragile numeric inputs in `TransactionFormModal.svelte` (quantity, amount,
  cost-basis) changed from `type="number"` to locale-safe text + decimal parse/normalize
  (canonical dot-decimal preserved). ✅
- **A2** Audited the other transaction forms / bulk modal / dual-form inputs for the same
  `type="number"` dot-decimal round-trip; fixed. ✅

### B — Import-wizard asset resolution / ISIN auto-match (RC-B) — ✅ done
- **B1** Extracted assets with an **exact ISIN match** to an existing asset are now
  **auto-bound / pre-resolved** (and ranked first), not left to a possibly-wrong manual
  default. ✅
- **B2** Guarded the `fake_asset_id → real asset_id` mapping against positional/index
  misbinding (keyed by identity, never by order). ✅

### C — CA plugin (`broker_credit_agricole.py`, now `plugin_version = 1.3.0`) — ✅ done
- **C1** Succession `GIRO ALTRO DOSSIER` / `VERS.TITOLI` → **cashless ADJUSTMENT**
  (`cost_basis_override` per-unit: bond `price/100`, fund/stock `price`; `cash=None`; origin
  causale in the description). Warning reworded. ✅
- **C2** Cash counter-entries: **BUY → DEPOSIT**, **SELL → WITHDRAWAL** (succession excepted,
  cashless). ✅
- **C3** Matured-bond redemption (`TITOLI SCADUTI`): SELL @ 100 + DIVIDEND for the > 100
  excess; shared bond-maturity helper; derived-nominal manual-verify flag; tests + samples +
  English docs (`mkdocs_src/docs/user/transactions/import/credit_agricole.en.md`); version
  bump. ✅

### D — Import wizard Step 4 UX (`ImportWizardModal.svelte`) — ✅ done
- **D1** Opening boundary → **`<=`** (exclude the opening day). ✅
- **D2** Refresh / recheck after broker-opening edit re-evaluates the before-opening flag
  (reactive `brokers` state updates; explicit recheck affordance). ✅
- **D3** Step 4 column showing the **destination broker** each row saves to. ✅
- **D4** Discoverable **edit-broker-opening** button for rows blocked by a too-far-ahead
  opening date. ✅

### E — Asset create / search — ✅ (E1–E3 done) · ⏳ (E4 designed, not built)
- **E1** Create-asset-from-wizard description now includes **all identified candidate names**
  (not only the chosen provider's). ✅
- **E2** Fixed name truncation `"… - STRATEGIA"` (full name shown / CSS-ellipsis, value
  preserved). ✅
- **E3** Investigated why Borsa Italiana site-search misses EURIZON funds (`cerca()` uses BI
  site-search: poor fund coverage, no ISIN-direct, no fuzzy on the broker name). Documented. ✅
- **E4 — ⏳ Borsa-Italiana-scoped search-engine fallback (design captured, not implemented).**
  See §5.

### Cross-cutting import/UX fixes — ✅ done
- Broker delete → **cascade BRIM file cleanup** (`brokers.py._delete_brim_files_for_brokers`,
  filtered to exact `target_broker_id`, best-effort, post-commit). ✅
- File **delete** action always visible in `BrokerImportFiles.svelte` (was hover-only). ✅
- **Search "searching forever" hang** fixed in `AssetSearchAutocomplete.svelte`: terminal
  `done` SSE event now stops the spinner immediately (`streamDone` + `reader.cancel()`);
  added an `AbortController` client timeout (`SEARCH_TIMEOUT_MS = 30000`) that surfaces
  `assets.search.timeout` (en/it/fr/es) instead of hanging; backend per-provider stream
  timeout reduced `30s → 20s` (`asset_source.py`). On timeout it does **not** fall back to
  REST (would hang the same way). ✅
- Bulk-transaction modal **manual-fields banner**: now blocks / warns when
  `Manual Fields Required` exist (previously let the user save silently). ✅
- Label rename **"Duplicates" → "Stato transazioni"** (evolved beyond dedup). ✅
- **NAV last-buy fallback**: assets without a market price use the last BUY as a unit-value
  estimate for NAV instead of being dropped. ✅
- Researched the broker-report **"obsoleto"** state (when it is assigned; documented). ✅

### F — Verification — ✅ done
- Backend: BRIM provider suite green (442 tests); `ruff` + `black` clean on all touched files.
- Frontend: `./dev.py front check` → **0 errors / 0 warnings**; `prettier` clean on the
  changed `.svelte` + i18n JSON.
- No `./dev.py api sync` needed (no OpenAPI schema change: before-opening is frontend-derived,
  CA cash reuses existing DTOs).

---

## 4. Prod handoff (⚠️ user action required)

Prod currently runs **pre-fix** plugin/wizard code, so the imported data is still corrupted.
To get correct numbers, **redeploy the fixed build, then**:

1. Delete the affected broker's imported rows **and** its BRIM files (now cascades on broker
   delete), then **re-import** the patrimonio + movements. With the ISIN auto-bind fix (B) the
   seeds bind to the correct EURIZON / BTP assets, and with the CA cashless-ADJUSTMENT +
   redemption model (C) the succession / matured-bond rows are correct. **or**
2. Manually correct in place: relink the mis-mapped seed ADJUSTMENTs to their exact-ISIN
   assets, and set the corrupted quantity back to its dot-decimal value (e.g. `91.861`).

Set the broker **opening date strictly before** the patrimonio snapshot date (boundary is now
`<=`) so the seeds import and pre-opening movements are excluded.

---

## 5. E4 — Borsa-Italiana-scoped search-engine fallback (⏳ design, not built)

**Problem.** `borsa_italiana.py.search()` uses the `cerca()` scraping lib (BI native
site-search): scarce fund coverage, no fuzzy match on the broker name, no ISIN-direct. Real
BI fund pages exist (e.g. `LU2178929613`) but are unreachable via site-search. This is a
**Borsa-Italiana-specific** gap, not a cross-provider one.

**⚠️ Empirical test (2026-07-27, `borsa_italiana_scraping` live) — corrects an earlier claim:**
- `ottieni_prezzo_corrente("IT0005441883")` (a listed BTP) → **works**: `57.25 EUR`,
  `fonte='api'`. So the **by-ISIN path works for listed bonds/stocks** (there is a real BI
  API behind it).
- `ottieni_prezzo_corrente("LU2178929613")` (the EURIZON **fund**) → the by-ISIN path *does*
  resolve to the "pagina scheda", but raises **`DatiNonDisponibili: impossibile estrarre il
  prezzo dalla pagina scheda`** — it **cannot extract the NAV** from the fund page layout.
- `cerca("LU2178929613")` and `cerca("EURIZON NEXT 2.0 DIVERSIFICATO 40 P")` → **0 results**.
- **Conclusion:** ISIN-first covers bonds/stocks but **NOT funds**. The fund gap is *not* a
  search problem — ISIN→page resolution already works — it is a **NAV-extraction** problem on
  the BI fund detail page (`/borsa/fondi/dettaglio/{code}.html`), whose NAV is dated
  ("Data: gg/mm", lagged daily NAV) and lives in a different DOM than stock/bond pages.

**Approach (user-refined + corrected by the test).** Two independent pieces:
1. **BI fund-page NAV extractor (the real fix for `LU2178929613`).** Extend the scraping lib
   / provider so that, for a fund ISIN, it parses the fund detail page and returns
   `(nav, as_of_date)`. Resolution to the page already works; only extraction is missing. The
   UI must label it "NAV al gg/mm" (not a live current price). This alone unblocks the user's
   fund without any meta-search.
2. **BI-scoped search-engine fallback (only if name-based fund discovery is still needed).**
   When `cerca()` returns empty, query a search engine constrained to `site:borsaitaliana.it`,
   locate the fund/asset page, then extract identifiers from it. Wire it **only** into the
   `borsa_italiana` provider.

**Design notes / options:**
- **Meta-search transport:** do **not** scrape Google (ToS / CAPTCHA / fragile). Prefer an
  official search API (Brave / Bing / SerpAPI) behind a small pluggable interface + a
  `site:borsaitaliana.it` filter. Key + cost required → make it opt-in / configurable.
- **Page extraction:** from the resolved BI page, parse ISIN + internal code + the dated NAV.
  BI fund pages expose a **NAV with an "as-of" date** (daily NAV, lagged — *not* intraday):
  the provider should return `(price, as_of)` and the UI must label it "NAV al gg/mm" so it is
  not confused with a live current price.
- **Cheaper partial wins (deferred, may precede the fund-extractor):**
  - **E-ISIN-first:** if the query matches an ISIN regex `[A-Z]{2}[A-Z0-9]{9}\d`, fetch
    directly by ISIN and synthesize the match even when site-search fails. **Empirically
    (2026-07-27) this covers listed bonds/stocks only** (BI `api` path); it does **not** cover
    funds (see the ⚠️ note above — funds fail at NAV extraction, not resolution).
  - **E-fund-NAV-date:** the BI fund provider must extract and surface the NAV "as-of" date
    `(price, as_of)` — this is part of the fund-page extractor above, not optional.
  - **E-name-normalize:** extend `_SEARCH_TERM_ABBREVIATIONS` (e.g. `DIVERSIFICATO → DIVERS`)
    — low value / fragile; only if trivial. (Note: `cerca()` returns 0 even for the exact
    name here, so name-normalize alone will not help this fund.)

**Recommendation:** the user's fund (`LU2178929613`) is unblocked only by the **BI fund-page
NAV extractor** (piece 1) — ISIN-first and name-normalize do **not** cover funds (verified).
Ship the fund-page extractor first; add the BI-scoped meta-search (piece 2) only if broader
name-based fund discovery is still needed afterwards.

---

## 6. Notes / caveats
- `WITHDRAWAL` (q=0, cash<0) and `DEPOSIT` (q=0, cash>0) both exist; **ADJUSTMENT must carry no
  cash** — that is why CA succession (cashless) uses ADJUSTMENT while ordinary CA buys/sells
  get the DEPOSIT/WITHDRAWAL counter-entry.
- `cost_basis_override` is **per-unit** (bond `price/100`, else `price`); the FIFO lot engine
  opens ADJUSTMENT_IN at `unit_price=0` and takes the real basis from the override valuation
  path (`transaction_service` requires the override for ADJUSTMENT qty>0).
- Matured-bond "excess over 100 = interest" is an **assumption** for `TITOLI SCADUTI`
  (BTP/quoted bonds redeemed at 100); documented per-plugin, to be generalized if
  counter-examples appear.
- Keep code / comments / docs **English**; UI strings **EN/IT/FR/ES**; user docs English-only.
- **Never** `git commit` / `push` / history-mutate — propose messages only; the user commits.
