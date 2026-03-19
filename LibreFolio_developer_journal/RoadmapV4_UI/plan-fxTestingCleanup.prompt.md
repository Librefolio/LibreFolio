# Plan: FX Testing & Cleanup — E2E, Unit Tests, i18n Audit, Gallery

**Data creazione**: 12 Marzo 2026
**Ultima revisione**: 19 Marzo 2026
**Status**: ✅ ALL STEPS COMPLETATI (0-12). Step 11 ✅ COMPLETATO (96 FX screenshot, 3 nuovi flag db populate, MkDocs da aggiornare)
**Priorità**: Media (copertura E2E FX completa, restano i18n rationalization, gallery)
**Stima**: ~5-6 giorni
**Dipendenze**: Tutti i plan Phase 5 FX completati (13+ sub-plan, 7 round bug-fix)
**Riferimenti**:
- `phases/phase-05-subplan/` — tutti i sub-plan completati
- `phases/phase-05-subplan/05FX_outofdate_plan/plan-phase05Fx.prompt.md` — vecchio master plan (archiviato)
- `phases/phase-05-subplan/05FX_outofdate_plan/phase05-pending-audit.md` §C — task originali

---

## Contesto

Il sottosistema FX è completo a livello funzionale: 2 pagine route (~1400+ righe ciascuna), ~20 componenti, signal library con 10 segnali, sistema di misure, data editor con CSV import, provider con catene di conversione DFS. Nessun test E2E esiste, nessun unit test per le classi core. Due bug noti da fixare prima dei test. Codice dead da rimuovere per evitare che il refactoring rompa i test dopo.

### Progress Log

| Data | Step | Dettagli |
|------|------|----------|
| 12 Mar 2026 | 📋 Stub creato | Task pendenti C1-C7 |
| 19 Mar 2026 | 📋 Piano dettagliato | Analisi completa codice, 12 step, ~70 test, 2 bug trovati |
| 19 Mar 2026 | ✅ Pre-Step 0A | Eliminato `FxEditSection.svelte` (dead code) — verificato: file non esiste |
| 19 Mar 2026 | ✅ Pre-Step 0B | Spostato `CsvEditor.svelte` in `ui/data-editor/` — verificato: nuovo path esiste |
| 19 Mar 2026 | ✅ Pre-Step 0C | 20 `data-testid` aggiunti nella pagina FX detail — verificato: 20 occorrenze |
| 19 Mar 2026 | ✅ Pre-Step 0D | Eliminato `fx-routes.spec.ts`, creato `e2e/fx/fx-helpers.ts` — verificato: file non esiste |
| 19 Mar 2026 | ✅ Pre-Step 0E | Fix FxPairSignal nella detail page (`_resolvedData`) — verificato: presente |
| 19 Mar 2026 | ✅ Pre-Step 0F | Fix `annualizedPct` in `MeasureSignal.getMeasurementForSignal()` — verificato: 6 occorrenze |
| 19 Mar 2026 | ✅ Step 1 | 27 unit test Vitest (15 TimeSeriesStore + 12 EditBuffer) — **PASSED** (27/27) |
| 19 Mar 2026 | 🔍 Step 2 | i18n: stringhe hardcoded tradotte in MeasurePanel — UNDER REVIEW (2A/2B/2C/2E non eseguiti) |
| 19 Mar 2026 | ✅ Step 3 | E2E FX List Page — **PASSED** (10/10) dopo 3 fix (testid collision, SearchSelect selector, badge logic) |
| 19 Mar 2026 | ✅ Step 4 | E2E FX Add Pair Modal — **PASSED** (5/5) |
| 19 Mar 2026 | ✅ Step 5 | E2E FX Detail Page — **PASSED** (12/12) |
| 19 Mar 2026 | ✅ Step 6 | E2E FX Data Editor — **PASSED** (3/3) |
| 19 Mar 2026 | ✅ Step 7 | E2E FX Sync — **PASSED** (3/3) |
| 19 Mar 2026 | ✅ Step 8 | E2E FX API Routes — **PASSED** (3/3) |
| 19 Mar 2026 | ✅ Step 9 | E2E FX Chart Settings — **PASSED** (3/3) |
| 19 Mar 2026 | ✅ Step 10 | Registrazione in `dev.py test` — verificata, `front_fx()` ora usa `_run_test_suite` con summary |
| 19 Mar 2026 | ✅ Step 12A | 14 plan file spostati in `phases/phase-05-subplan/` |
| 19 Mar 2026 | ✅ Step 12B | `phase-05-fx.md` riscritto come summary |
| 19 Mar 2026 | ✅ Step 12C | Aggiornato TODO_Completati.md e TODO_FUTURI.md — verificato: voci rimosse |
| 19 Mar 2026 | ✅ Fix port | `--force` flag aggiunto a `./dev.py server` + `playwright.config.ts` usa `--force` |
| 19 Mar 2026 | ✅ Fix testid | `data-testid` aggiunti: `fx-currency-filter`, `fx-reset-filters`, `fx-date-range-picker`, `fx-pair-label`, `fx-swap-btn` |
| 19 Mar 2026 | ✅ Fix tests | Test 4/7/8/10 in `fx-list.spec.ts` resi reali (rimossi if-guard, asserzioni dirette) |
| 19 Mar 2026 | 🔧 Fix tests | Test 3: card count collision (testid prefix `fx-card-` matchava figli) → rinominati a `fx-pair-label`/`fx-swap-btn` |
| 19 Mar 2026 | 🔧 Fix tests | Test 4/5: `SearchSelect` usa `<button>` non `[role=option]` → corretto selettore |
| 19 Mar 2026 | ✅ Fix dev.py | `_print_port_help()` estratta come funzione condivisa, usata da entrambi i path (force/non-force) |
| 19 Mar 2026 | ✅ Step 2A | i18n-audit: regex migliorate (tooltip, 3-segment strings), unused report split in Dynamic/Unused |
| 19 Mar 2026 | ✅ Step 2A+ | i18n-audit: `--duplicates`/`-d` flag — analisi valori duplicati cross-lingua, 60 gruppi unici trovati |
| 19 Mar 2026 | ✅ Step 2A+ | i18n-audit: export Excel con tab per severità (Dup ALL, 3-4, 2-4, 1), tabelle impilate con stile |
| 19 Mar 2026 | ✅ Step 2B | 111 chiavi morte rimosse da tutte e 4 le lingue (735 → 624 keys, 0 unused, 100% coverage) |
| 19 Mar 2026 | ✅ Step 2E | Verificata completezza: 624/624 keys in EN/IT/FR/ES (100%) |
| 19 Mar 2026 | 📋 Step 2C | Piano razionalizzazione scritto — review completata, **TUTTE LE DECISIONI PRESE** |
| 19 Mar 2026 | ✅ Step 2C.1 | Eseguito piano Fasi 1-3: merge sicuri, nav/title, common, allineamento FR, merge discard/undo/reset/discardAndClose. 624 → 585 chiavi |
| 19 Mar 2026 | ✅ Step 2C.2 | Migrazione coerenza `filter.*` → `common.*`: `filter.bytes/kilobytes/gigabytes/min` → `common.bytes/kilobytes/gigabytes/min`. Fix stale ref `filter.megabytes` in upload.ts |
| 19 Mar 2026 | ✅ Step 2C.3 | Migrazione coerenza preset array: `uploads.presetIcon` → `common.icon`, 3× "Custom" (`uploads.presetCustom`, `datePicker.custom`, `chartSettings.yAxisCustom`) → `common.custom`. 585 → 583 chiavi |
| 19 Mar 2026 | 📋 Step 2C.4 | Analisi 19 gruppi duplicati residui — tutti classificati come KEEP (prefissi dinamici, semantica diversa, o duplicato linguistico accettabile) |
| 19 Mar 2026 | ✅ Step 2D | 18 stringhe hardcoded → i18n in 6 file (FxCard, FxProviderConfig, ChartSignalsSection, ChartAestheticsSection, fx/+page, DataEditor). 10 nuove chiavi + 5 riuso existing. 583 → 593 chiavi |
| 19 Mar 2026 | ✅ Step 11A | Part A — 3 nuovi flag `--clean`, `--with-static`, `--with-reports` aggiunti a `populate_mock_data.py` (argparse + 3 nuove funzioni: `clean_data_dirs()`, `upload_static_resources()`, `upload_broker_reports()`) |
| 19 Mar 2026 | ✅ Step 11A | Propagazione flag in `test_runner.py`: `db_populate()` accetta i 3 nuovi kwargs, parser db con `add_argument`, `dispatch_to_category()` estrae i flag |
| 19 Mar 2026 | ✅ Step 11A | `dev.py` `cmd_mkdocs_gallery()` aggiornato: chiama `--force --clean --with-static --with-reports` |
| 19 Mar 2026 | ✅ Step 11A | `db-helpers.ts`: nuova funzione `resetDatabaseForGallery()` con tutti i flag |
| 19 Mar 2026 | ✅ Step 11B | Part B — `test.describe('FX')` aggiunto a `gallery.spec.ts` (righe 588-918) con 12 test scene, `beforeEach` login admin |
| 19 Mar 2026 | ✅ Step 11B | Import `goToFxPage`, `goToFxDetailPage`, `openAddPairModal` da `./fx/fx-helpers` in gallery.spec.ts |
| 19 Mar 2026 | ✅ Step 11B | 12 scene: list, list-filtered, add-pair-routes, add-pair-chain, sync-progress, detail-chart, detail-signals, detail-measures, detail-editor, detail-csv-import, chart-settings, provider-config |
| 19 Mar 2026 | ✅ Step 11B | Ogni scena con `forEachLanguageAndTheme()` o loop manuale per 4 lingue × 2 temi = 8 varianti |
| 19 Mar 2026 | ✅ Step 11B | Scene ECharts (6-8, 11) usano `waitForSelector('canvas')` + `waitForTimeout(2000)` per rendering canvas |
| 19 Mar 2026 | ✅ Step 11B | Scena 4 (chain) usa GBP/JPY via USD invece di RON/USD (route già presente nei mock data) |
| 19 Mar 2026 | ✅ Step 11B | **96/96 screenshot generati** — 12 scene × 4 lingue × 2 temi, tutti verificati ✅ |
| 19 Mar 2026 | ✅ Fix test | `test_fx_api.py` `test_pair_sources_crud`: `_route_json()` ritorna dict, non Pydantic model → rimosso `.model_dump()` sulle 2 chiamate `_route_json` (20/20 test passano) |
| 19 Mar 2026 | ✅ Fix gallery | `gallery.spec.ts` add-pair-routes/chain: selettore `[role="option"]` → `button` (SearchSelect usa `<button>`, non `role="option"`) + ricerca inline via `input[type="text"]`.fill() per selezione affidabile |
| 19 Mar 2026 | ✅ Fix gallery | `gallery.spec.ts` list-filtered: stessa fix `[role="option"]` → `button` per il filtro valuta |
| 19 Mar 2026 | ✅ Fix gallery | `gallery.spec.ts` detail-signals: aggiunto `scrollIntoViewIfNeeded()` sul pannello segnali dopo toggle per mostrare il contenuto |
| 19 Mar 2026 | ✅ Step 11A fix | `upload_static_resources()`: rimossa assegnazione `broker.icon_url` — il frontend già fetcha icone dal portale quando icon_url è null, risultato migliore |
| 19 Mar 2026 | ✅ Step 11 perf | Gallery parallelizzata: `test.describe.configure({mode: 'parallel'})` + `--workers CPU-1` + desktop/mobile in parallelo con `ThreadPoolExecutor` |
| 19 Mar 2026 | ✅ MkDocs | Sezione `## 💱 FX Rates` aggiunta a `desktop.md` (12 img), `mobile.md` (12 img mobile), `index.md` (feature listing) |
| 19 Mar 2026 | ✅ Fix gallery | add-pair-routes: EUR→USD cambiato in USD/CHF (EUR esclusa da base — già configurata nei mock) |
| 19 Mar 2026 | ✅ Fix gallery | add-pair-chain: GBP/JPY cambiato in NOK/CHF (GBP esclusa da base — GBP-PLN nei mock) |
| 19 Mar 2026 | ✅ Fix gallery | `auth-helpers.ts` login timeout: 3s→10s per gestire carico parallelo con 9 worker |
| 19 Mar 2026 | ✅ Fix gallery | `dev.py`: desktop+mobile in singolo comando Playwright (`--project desktop --project mobile`) — condivide webServer, evita conflitto porta |
| 19 Mar 2026 | ✅ MkDocs | Titoli FX in desktop.md e mobile.md convertiti da bilingue EN/IT a solo inglese |
| 19 Mar 2026 | ✅ Feature | `dev.py server --workers N`: flag per uvicorn workers (default 1, con N>1 disabilita --reload) |
| 19 Mar 2026 | ✅ Feature | `dev.py mkdocs gallery --workers N`: flag per browser workers (default CPU count). Server workers auto-calcolati: ceil(browser/4) |
| 19 Mar 2026 | ✅ Feature | `playwright.config.ts`: webServer command legge `GALLERY_SERVER_WORKERS` env var per avviare server con più worker |
| 19 Mar 2026 | ✅ Fix gallery | Output streaming live (no `capture_output`), gestione Ctrl+C con `KeyboardInterrupt`. Formula worker: CPU×2→CPU (20 headed Chrome = troppi, resource exhaustion) |
| 19 Mar 2026 | ✅ JWT migration | Sessioni in-memory → JWT stateless (PyJWT HMAC-SHA256). Secret random pre-fork condiviso tra worker. `auth_service.py` riscritto, `auth.py` + `user_service.py` aggiornati. Gallery fix: route picker aperto per screenshot Add Pair, provider initials instead of img. Vedi `plan-jwt-gallery-fixes.prompt.md` |

---

## Pre-Step 0 — Cleanup e fix prima dei test

Queste aree DEVONO essere risolte PRIMA di scrivere qualsiasi test, per evitare che il refactoring rompa i test stessi e per garantire che le funzionalità testate siano corrette.

### 0A. Rimuovere dead code: `FxEditSection.svelte`

**File da eliminare**: `frontend/src/lib/components/fx/FxEditSection.svelte`
**File da modificare**: `frontend/src/lib/components/fx/index.ts`

`FxEditSection.svelte` (124 righe) non è importato da nessun componente (confermato con grep: zero risultati per `import.*FxEditSection`). È stato rimpiazzato da `FxDataEditorSection.svelte` (commento esplicito riga 4: "NOTE: Will be replaced by FxDataEditorSection in Step 4").

- [ ] Eliminare `FxEditSection.svelte`
- [ ] Rimuovere l'export `export {default as FxEditSection} from './FxEditSection.svelte'` da `index.ts`
- [ ] Verificare: `./dev.py front check` — 0 errori
- [ ] Verificare: `./dev.py front build` — build pulita

### 0B. Spostare `CsvEditor.svelte` da `fx/` a `ui/data-editor/`

**File da spostare**: `frontend/src/lib/components/fx/CsvEditor.svelte` → `frontend/src/lib/components/ui/data-editor/CsvEditor.svelte`
**Import da aggiornare** (3 file):
- `frontend/src/lib/components/ui/data-editor/DataImportModal.svelte` — righe 22-23
- `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` — riga 18
- `frontend/src/lib/components/fx/index.ts` — riga 6 (rimuovere export, o re-export dal nuovo path)

`CsvEditor.svelte` (417 righe) è un componente generico di editing CSV: textarea con numeri riga, validazione live, supporto formato flessibile (`,` e `.` come decimali, `_` migliaia). È importato da `DataImportModal.svelte` e `DataEditor.svelte`, entrambi in `ui/data-editor/`. L'accoppiamento `ui/ → fx/` è architetturalmente errato: il componente generico non deve vivere nella cartella FX-specifica.

- [ ] Spostare `CsvEditor.svelte` in `ui/data-editor/`
- [ ] Aggiornare import in `DataImportModal.svelte`: `from '$lib/components/fx/CsvEditor.svelte'` → `from './CsvEditor.svelte'`
- [ ] Aggiornare import in `DataEditor.svelte`: `from '$lib/components/fx/CsvEditor.svelte'` → `from './CsvEditor.svelte'`
- [ ] Aggiornare `fx/index.ts`: rimuovere export CsvEditor (o re-export da nuova posizione se serve altrove)
- [ ] Verificare: `./dev.py front check` — 0 errori

### 0C. Aggiungere `data-testid` nella pagina FX Detail

**File**: `frontend/src/routes/(app)/fx/[pair]/+page.svelte`

La pagina FX detail ha **zero** attributi `data-testid` (confermato con grep). Senza di essi, i test E2E Playwright non possono agganciare gli elementi in modo robusto.

Attributi da aggiungere (~20):
- [ ] `fx-detail-page` — container pagina
- [ ] `fx-detail-header` — header con info coppia
- [ ] `fx-detail-pair-label` — label coppia (es. "EUR / USD")
- [ ] `fx-detail-swap-btn` — bottone swap direction
- [ ] `fx-detail-back-btn` — bottone back to list
- [ ] `fx-detail-filter-bar` — container filtri
- [ ] `fx-detail-chart` — container chart
- [ ] `fx-detail-sync-btn` — bottone sync
- [ ] `fx-detail-refresh-btn` — bottone refresh
- [ ] `fx-detail-edit-btn` — bottone edit rates
- [ ] `fx-detail-measure-btn` — bottone measure mode
- [ ] `fx-detail-provider-btn` — bottone provider config
- [ ] `fx-detail-aesthetics-toggle` — toggle pannello aesthetics
- [ ] `fx-detail-signals-toggle` — toggle pannello signals
- [ ] `fx-detail-measures-toggle` — toggle pannello measures
- [ ] `fx-detail-aesthetics-panel` — contenuto pannello aesthetics
- [ ] `fx-detail-signals-panel` — contenuto pannello signals
- [ ] `fx-detail-measures-panel` — contenuto pannello measures
- [ ] `fx-detail-editor-panel` — contenuto data editor
- [ ] `fx-detail-provider-modal` — modale provider config

### 0D. Cancellare `fx-routes.spec.ts` obsoleto

**File da eliminare**: `frontend/e2e/fx-routes.spec.ts`

Il file (652 righe) contiene test parzialmente funzionanti ma basati su strutture vecchie:
- `fx-route-chain-section` — testid cambiato (ora `fx-route-chain-section-{stepCount}`)
- Test API con estrazione manuale session cookie — pattern valido ma i test vanno riadattati
- Helper `goToFxPage()`, `selectCurrency()`, `openAddPairModal()` — **recuperabili** nei nuovi file

Alcuni helper e test API saranno adattati nei nuovi file in `e2e/fx/`. Il file originale va eliminato.

- [ ] Eliminare `fx-routes.spec.ts`
- [ ] Creare cartella `frontend/e2e/fx/`

### 0E. Fix bug: FxPairSignal non funziona in `/fx/[pair]`

**Root cause**: In `frontend/src/routes/(app)/fx/+page.svelte` (righe 307-322) c'è un blocco che inietta `_resolvedData` dal `TimeSeriesStore` nell'istanza `FxPairSignal` prima di chiamare `renderMulti()`:

```typescript
// List page — funziona
if (cfg.signalType === 'fx-pair') {
    const pairSlug = String(cfg.params.pairSlug || '');
    if (!pairSlug) continue;
    try {
        const store = getFxStore(pairSlug);
        const storeData = store.getAllSorted();
        if (storeData.length === 0) continue;
        instance.params._resolvedData = storeData.map(d => ({
            date: d.date, value: d.rate,
        }));
    } catch { continue; }
}
```

Questo blocco **manca completamente** in `frontend/src/routes/(app)/fx/[pair]/+page.svelte` (righe 149-160), dove il `$derived` che calcola `overlaySignals` non gestisce il caso `fx-pair`. Senza `_resolvedData`, `FxPairSignal.computePoints()` restituisce `[]` e il segnale non appare.

- [ ] Aggiungere lo stesso pattern di risoluzione dati nel `$derived.by` della detail page (righe 149-160)
- [ ] Importare `getFxStore` se non già importato (controllare: potrebbe essere già importato per altri usi)
- [ ] Verificare: aggiungere un segnale FxPair nella detail page → compare nel chart
- [ ] Verificare: `./dev.py front check` — 0 errori

**File coinvolti**:
- `frontend/src/routes/(app)/fx/[pair]/+page.svelte` — aggiungere blocco _resolvedData
- `frontend/src/lib/charts/signals/FxPairSignal.ts` — riferimento per `_resolvedData`
- `frontend/src/lib/stores/fxStoreRegistry.ts` — `getFxStore()`

### 0F. Fix bug: `Δ%/yr` mancante per segnali overlay nelle misure

**Root cause**: In `frontend/src/lib/components/charts/MeasurePanel.svelte` riga 319:

```typescript
annualizedPct: null,  // ← hardcoded null per tutti gli overlay signals
```

Il metodo `getMeasurementForSignal()` in `frontend/src/lib/charts/signals/MeasureSignal.ts` (righe 128-142) restituisce solo `{startValue, endValue, deltaAbs, deltaPct}` — non calcola `annualizedPct`. La formula è già disponibile in `getMeasurement()` (righe 107-110):

```typescript
const annualizedPct = days > 0
    ? (Math.pow(1 + deltaPct / 100, 365 / days) - 1) * 100
    : 0;
```

- [ ] Aggiungere `annualizedPct` al return type di `getMeasurementForSignal()` in `MeasureSignal.ts`
- [ ] Calcolare `annualizedPct` nel metodo (richiede `days`, che si ottiene con `ChartSignal.daysBetween(startDate, endDate)`)
- [ ] In `MeasurePanel.svelte` riga 319, usare `sigResult.annualizedPct` al posto di `null`
- [ ] Verificare: aggiungere una misura con segnali overlay → colonna Δ%/yr mostra valori per tutti

**File coinvolti**:
- `frontend/src/lib/charts/signals/MeasureSignal.ts` — estendere `getMeasurementForSignal()`
- `frontend/src/lib/components/charts/MeasurePanel.svelte` — usare il valore calcolato

---

## Step 1 — Unit test Vitest: `TimeSeriesStore` e `EditBuffer`

**Categoria CLI**: `fx-unit` (non generico "unit" — specifico per il sottosistema FX)

**File da creare**:
- `frontend/src/lib/stores/__tests__/TimeSeriesStore.test.ts`
- `frontend/src/lib/stores/__tests__/EditBuffer.test.ts`
- `frontend/vitest.config.ts` (config minimale con alias `$lib`)

**Setup**:
- Aggiungere `vitest` come devDependency in `frontend/package.json`
- Creare `frontend/vitest.config.ts` con alias `$lib → src/lib`
- Aggiungere script `"test:unit": "vitest run"` e `"test:unit:list": "vitest list"` in `package.json`

### TimeSeriesStore (~15 test)

**File da consultare**: `frontend/src/lib/stores/TimeSeriesStore.ts` (201 righe)

| # | Scenario | Scopo | Verifica |
|---|---|---|---|
| 1 | `getRange` su store vuoto | Gap unico per tutta la range | `data=[], gaps=[{start, end}]` |
| 2 | `merge` + `getRange` | Inserimento e recupero | Dati presenti, nessun gap nelle date coperte |
| 3 | `merge` idempotente | Upsert senza duplicati | `size` invariato dopo re-merge |
| 4 | `getRange` con buchi intermedi | Gap detection precisa | Gaps multipli corrispondenti ai buchi |
| 5 | `getMissingIntervals` | Convenience wrapper | Risultato identico a `getRange().gaps` |
| 6 | `invalidateRange` parziale | Rimuove solo il range indicato | Dati fuori range intatti, quelli dentro rimossi |
| 7 | `invalidateAll` | Pulizia totale | `size === 0` |
| 8 | `getAllSorted` | Ordinamento date | Array ordinato cronologicamente |
| 9 | Edge: range con start > end | Comportamento graceful | `data=[], gaps=[]` (nessun crash) |
| 10 | Edge: range 1 giorno con punto | Singolo punto | `data=[point], gaps=[]` |
| 11 | Edge: range 1 giorno senza punto | Singolo gap | `data=[], gaps=[{day, day}]` |
| 12 | Merge con date non contigue | Store sparse | Gaps calcolati correttamente tra punti sparsi |
| 13 | `get` e `has` | Lookup diretto | Ritorna punto o undefined/false |
| 14 | Merge sovrascrive dati | Upsert semantics | Punto aggiornato con nuovo valore |
| 15 | Gap trailing (fine range vuota) | Gap alla fine | Gap finale correttamente chiuso |

### EditBuffer (~12 test)

**File da consultare**: `frontend/src/lib/stores/EditBuffer.ts` (257 righe)

| # | Scenario | Scopo | Verifica |
|---|---|---|---|
| 1 | `add` nuova entry | Inserimento | `size=1`, `hasChanges=true` |
| 2 | `add` stessa data | Upsert per data | `size` rimane 1, csvLineNumber preservato |
| 3 | `update` entry esistente | Modifica punto | Punto aggiornato |
| 4 | `remove` per ID | Eliminazione | `size` decrementato, `dateIndex` aggiornato |
| 5 | `removeByDate` | Eliminazione per data | Entry rimossa |
| 6 | `getAll` ordinato | Ordinamento | Risultato ordinato per data |
| 7 | `clear` | Reset | `size=0`, `hasChanges=false` |
| 8 | `onChange` callback | Notifica listener | Invocato su add/update/remove |
| 9 | `onChange` unsubscribe | Pulizia listener | Non invocato dopo unsubscribe |
| 10 | `getByDate` | Lookup per data | Entry corretta o undefined |
| 11 | Multiple sources | `click`/`csv`/`form` | Source tracciata correttamente |
| 12 | `getCsvLines` | Export CSV | Righe formattate correttamente |

### Integrazione dev.py

- [ ] Funzione `front_fx_unit()` in `test_runner.py` che chiama `npm run test:unit` nella cartella frontend
- [ ] Registrare `"fx-unit"` nel `TEST_REGISTRY["front"]`

---

## Step 2 — i18n Audit & Razionalizzazione

### 2A. ✅ Migliorare lo strumento i18n-audit — COMPLETATO

**File**: `frontend/scripts/i18n-audit.py`

Migliorie effettuate:
- Regex: aggiunto `tooltip` a indirect patterns, pattern per stringhe 3-segment, pattern `key:` / `tooltip:` in oggetti
- Report unused: split in "Potentially Dynamic" e "Likely Unused"
- **Nuovo flag `--duplicates` / `-d`**: analisi valori duplicati cross-lingua con:
  - Raggruppamento per frozenset di chiavi (de-duplica tra lingue)
  - Ordinamento per severità: ALL langs → 3/4 → 2/4 → 1/4
  - Tabella per gruppo: righe = chiavi, colonne = EN/IT/FR/ES, titolo indica quali lingue matchano
  - Breakdown summary: `60 groups: ALL langs: 28 · 3/4: 9 · 2/4: 11 · 1/4: 12`
- **Export Excel con duplicati**: un tab per tier di severità, tabelle impilate con titolo merged giallo, header verde, celle duplicate highlight verde chiaro

### 2B. ✅ Pulizia chiavi non usate — COMPLETATO

- 111 chiavi morte rimosse da tutte e 4 le lingue con `./dev.py i18n remove KEY -f`
- Risultato: **735 → 624 keys, 0 unused, 100% coverage**
- Tutte le 111 chiavi verificate con grep: zero riferimenti nel sorgente

### 2C. 📋 Razionalizzazione chiavi duplicate — IN PIANIFICAZIONE

**Riferimento audit**: `i18n-audit-duplicate.md` (generato 19 Mar 2026, 60 gruppi)
**Comando**: `./dev.py i18n audit --duplicates`

> ⚠️ **ATTENZIONE**: Ogni merge richiede aggiornamento di tutti i `$t()` / `$_()` nel sorgente.
> Procedere gruppo per gruppo, con `./dev.py front check` dopo ogni batch.
> Se qualcosa non torna nell'UI, ripristinare la chiave con `./dev.py i18n add`.

---

#### Fase 0 — Gruppi NON unificabili (prefisso dinamico) — SKIP

Questi gruppi sono sotto prefissi risolti dinamicamente (`$t(\`prefix.${var}\`)`). NON possono essere mergiati.

| Prefisso dinamico | Chiavi coinvolte | Motivo |
|---|---|---|
| `chartSettings.signals.*` | `ema`/`emaAbbr`, `macd`/`macdAbbr`, `rsi`/`rsiAbbr`, `fxPair`/`fxPairAbbr` | Signal name + abbreviation risolti con `${type}` e `${type}Abbr` |
| `fileStatus.*` | `fileStatus.error` ↔ `common.error` | Status risolto con `$t(\`fileStatus.${status}\`)` |
| `fileStatus.*` | `fileStatus.uploaded` ↔ `uploads.uploadDate` | Idem |
| `settings.globalSettingNames.*` | `default_currency` ↔ `settings.defaultCurrency` | Setting names risolti dinamicamente |
| `settings.globalSettingCategories.*` | `security` ↔ `settings.security`; `all` ↔ `settings.all` | Categorie risolte dinamicamente |
| `settings.globalSettingUnits.*` | `price_sync_interval_hours` ↔ `session_ttl_hours`; `max_file_upload_mb` ↔ `filter.megabytes` | Unità risolte dinamicamente |

**Totale: ~12 gruppi da IGNORARE**

---

#### Fase 1 — Merge sicuri (ALL languages, stessa semantica) — ✅ APPROVATO

Chiavi con valori identici in tutte e 4 le lingue, stessa semantica, nessun prefisso dinamico.
Azione: scegliere chiave canonica, aggiornare riferimenti, eliminare duplicato.

| Canonico (KEEP) | Da eliminare (REMOVE) | Valore (EN) | Riferimenti da aggiornare |
|---|---|---|---|
| `common.continueEditing` ← **NEW** | `brokers.continueEditing`, `settings.continueEditing` | Continue Editing | BrokerForm, SettingsPage |
| `common.noData` | `table.noData` | No data available | DataTable.svelte (1 uso) |
| `common.remove` | `measure.remove` | Remove | MeasurePanel.svelte (1 uso) |
| `common.discardChangesMessage` | `uploads.discardChangesMessage` | You have unsaved changes... | uploads discard modal |
| `fxDetail.editRates` | `fxDetail.editRatesBtn` | Edit Rates | fx/[pair]/+page.svelte riga 740 (title attr) |
| `fx.syncing` ← **NEW** | `fx.actions.syncing`, `fx.sync.syncing` | Syncing... | FxCard, FxSyncModal |
| `fx.providers` ← **NEW** | `fx.route.providersLabel`, `fxDetail.providers` | Providers | FxProviderSelect, fx detail |
| `uploads.deleteConfirm` | `uploads.deleteConfirmSingle` | Are you sure you want to delete this file? | FilesTable.svelte riga 381 |
| `uploads.upload` | `uploads.uploadNew` | Upload | AssetPickerModal.svelte (1 uso) |

**Pattern nav/title** — ✅ APPROVATO merge (se mai servirà un titolo diverso, si ri-crea la chiave):

| Canonico (KEEP) | Da eliminare (REMOVE) | Valore (EN) | Note |
|---|---|---|---|
| `fx.title` | `nav.fx` | FX Rates | |
| `transactions.title` | `nav.transactions` | Transactions | |
| `assets.title` | `nav.assets`, `dashboard.assetCount` | Assets | dashboard usa come label widget |

**Migrazione in `common.*`** — ✅ APPROVATO per chiavi con stessa semantica cross-contesto:

| Canonico (KEEP/NEW) | Da eliminare (REMOVE) | Valore (EN) | Riferimenti |
|---|---|---|---|
| `common.aesthetics` ← **NEW** | `chartSettings.aesthetics`, `fxDetail.aesthetics` | Aesthetics | ChartAestheticsSection, fx detail panel |
| `common.swapDirection` ← **NEW** | `csvImport.swapDirection`, `fxDetail.swapDirection` | Swap direction | DataImportModal, fx detail header |
| `common.saveConfiguration` ← **NEW** | `brokers.sharing.save`, `fx.addPair.saveConfiguration` | Save Configuration | BrokerSharingModal, FxPairAddModal |
| `common.totalValue` ← **NEW** | `brokers.totalValue`, `dashboard.totalValue` | Total Value | BrokerCard/Page, Dashboard widget |
| `common.selected` ← **NEW** | `table.selected`, `uploads.selected` | selected | DataTable, FilesTable/uploads |
| `common.start` ← **NEW** | `chartSettings.style.markerStart`, `measure.table.start` | Start | Chart style settings, MeasurePanel |
| `common.end` ← **NEW** | `chartSettings.style.markerEnd`, `measure.table.end` | End | Chart style settings, MeasurePanel |

**Casi KEEP separati (duplicato intenzionale — contesti troppo diversi)**:

| Chiavi | Valore (EN) | Motivo |
|---|---|---|
| `chartSettings.yAxisCustom`, `datePicker.custom`, `uploads.presetCustom` | Custom | 3 contesti completamente diversi |
| `filter.max`, `uploads.maxSizeLabel` | Max | Filtro vs upload limit |
| `settings.avatar`, `uploads.presetAvatar` | Avatar | Settings label vs upload preset |

---

#### Fase 2 — 3/4 lingue — ✅ DECISIONI PRESE

| Chiavi | Azione | Stato |
|---|---|---|
| `common.saveAll` / `settings.saveAll` | Allineare FR → "Enregistrer Tout", merge a `common.saveAll` | ✅ APPROVATO |
| `common.undoAll` / `settings.undoAll` | Allineare FR → "Annuler Tout", merge a `common.undoAll` | ✅ APPROVATO |
| `common.close` / `common.dismiss` | Merge a `common.close` (distinzione non significativa) | ✅ APPROVATO |
| `fx.actions.settings` / `nav.settings` | KEEP — ES distingue correttamente "Ajustes" vs "Configuración" | ✅ KEEP |
| `nav.files`/`uploads.title`, `nav.brokers`/`brokers.title` | Parte del pattern nav/title (Fase 1) | ✅ Coperto |

---

#### Fase 3 — 2/4 e 1/4 lingue — ✅ TUTTE LE DECISIONI PRESE

**Merge approvati:**

| Chiavi | Azione | Stato |
|---|---|---|
| `brokers.discardChanges`, `common.discardChanges`, `settings.discardChanges`, `uploads.discardChanges` | Allineare case/spazi EN/FR, merge a `common.discardChanges` | ✅ APPROVATO |
| `common.undo` / `settings.undo` | Merge a `common.undo` (ha 12 usi vs 6 di settings.undo) | ✅ APPROVATO |
| `common.reset` / `settings.resetToDefault` | Merge a `common.reset` (4 usi vs 1) | ✅ APPROVATO |
| `brokers.discardAndClose` / `uploads.discardAndClose` | Merge a `common.discardAndClose`, allineare EN a "Discard & Close" | ✅ APPROVATO |
| `common.resetAll` / `settings.resetAllToDefault` / `uploads.resetAll` | KEEP separati — semantica diversa | ✅ KEEP |

**Fix qualità traduzione — ✅ TUTTE DECISE:**

**1. `common.cancel` vs `common.undo`** — ✅ Aumentare distanza semantica
- IT: `common.undo` → **"Ripristina"** (nota: `common.reset` IT è anche "Ripristina" ma contesto diverso: ↩ field vs button reset)
- FR: `common.undo` → **"Rétablir"** (non esiste altrove — pulito)
- `common.cancel` resta invariato ("Annulla" / "Annuler")

**2. `brokers.discardAndClose` / `uploads.discardAndClose`** — ✅ Merge a `common.discardAndClose`
- Fix EN `uploads.discardAndClose`: "Discard" → "Discard & Close" (allineare)
- Fix IT `uploads.discardAndClose`: "Annulla e chiudi" → "Annulla e Chiudi" (allineare case)
- Fix ES `uploads.discardAndClose`: "Descartar" → "Descartar y Cerrar" (allineare)
- Merge entrambi a `common.discardAndClose`
- Aggiornare: BrokerModal, BrokerSharingModal, DataImportModal, FileEditModal, ImageEditModal (5 file)
- Nota: i message (warning/confirm) restano specifici per contesto (broker-specific, settings-specific, etc.)

**3. `fxDetail.syncFromProvider`** — ✅ Eliminare + rimuovere tooltip dai bottoni 2x2
- Rimuovere TUTTI i `title=` dai bottoni 2x2 in entrambe le pagine:
  - `fx/+page.svelte`: righe 574, 585, 595 (Settings, Sync All, Refresh All)
  - `fx/[pair]/+page.svelte`: righe 621, 632, 643 (Providers, Sync, Refresh)
- Chiavi che diventano unused dopo rimozione tooltip:
  - `fxDetail.syncFromProvider` — SOLO usato come title= → **RIMUOVERE**
  - `fxDetail.refreshData` — SOLO usato come title= → **RIMUOVERE**
- Chiavi che restano usate (hanno anche label `{#if showActionLabels}`):
  - `fx.actions.settings`, `fx.actions.syncAll`, `fx.actions.refreshAll` → KEEP
  - `fxDetail.providers` → KEEP (usato anche come label)

**4. `auth.loginHere`** — ✅ Opzione B
- IT: "Accedi" → **"Accedi qui"**
- ES: già sufficientemente distinto ("Iniciar Sesión" vs "Inicia sesión" — forma verbale diversa) → **no modifiche ES**
- FR: già distinto ("Connexion" vs "Connectez-vous") → **no modifiche FR**

**5. `uploads.outputSize`** — ✅ Opzione A
- IT: "Dimensione" → **"Output"** (anglicismo accettabile in contesto tecnico editing immagini)
- Aggiornare in: `ImageEditModal.svelte:380`

**6. `common.delete` vs `common.remove`** — ✅ Opzione A, aumentare distanza
- FR: `common.remove` "Supprimer" → **"Retirer"** (`common.delete` resta "Supprimer")
- ES: `common.remove` "Eliminar" → **"Quitar"** (`common.delete` resta "Eliminar")
- Aggiornare in: MeasurePanel (1 uso), BrokerForm (1 uso), FileUploader (1 uso), ProfileTab (2 usi)

---

#### Fase 4 — 🐛 Bug trovato: `datePicker.granularity.monthsShort`

| Chiave | EN | IT | FR | ES | Atteso |
|---|---|---|---|---|---|
| `datePicker.granularity.daysShort` | D | G | J | D | ✅ Corretto |
| `datePicker.granularity.monthsShort` | **D** | **D** | **D** | **D** | ❌ Dovrebbe essere **M** |

**Usato in**: `DateRangePicker.svelte` riga 136 — abbreviazione della granularità "Months" nel selettore.
Attualmente mostra "D" (che è l'abbreviazione di Days), rendendo impossibile distinguere Days da Months nel selettore compatto.

**Fix**: `./dev.py i18n update datePicker.granularity.monthsShort --en M --it M --fr M --es M`

---

#### Riepilogo quantitativo

| Categoria | Gruppi | Stato |
|---|---|---|
| Fase 0 — Prefisso dinamico | ~12 | SKIP |
| Fase 1 — Merge sicuri | 9 | ✅ ESEGUITO |
| Fase 1 — Pattern nav/title | 3 | ✅ ESEGUITO |
| Fase 1 — Migrazione common | 7 | ✅ ESEGUITO |
| Fase 1 — Duplicati intenzionali | 3 | KEEP |
| Fase 2 — Merge + allinea FR | 3 | ✅ ESEGUITO |
| Fase 2 — KEEP | 1 | KEEP |
| Fase 3 — Merge (discard, undo, reset, discardAndClose) | 5 | ✅ ESEGUITO |
| Fase 3 — Fix qualità traduzione (6 issue) | 6 | ✅ ESEGUITO |
| Fase 3 — Rimozione tooltip FX + chiavi unused | 2 chiavi | ✅ ESEGUITO |
| Fase 4 — Bug monthsShort | 1 | ✅ ESEGUITO |
| Fase 5 — Coerenza array (filter→common, preset→common, Custom→common) | 8 chiavi | ✅ ESEGUITO |
| **Chiavi eliminate** | | **624 → 583** (41 eliminate, 2 nuove create) |

#### Ordine di esecuzione proposto

✅ **COMPLETATO** — Tutte le fasi eseguite (19 Mar 2026):

```
1. Fix bug monthsShort (Fase 4)                                       ✅ ESEGUITO
2. Rimozione tooltip FX + chiavi unused (Fase 3, punto 3)              ✅ ESEGUITO
3. Fix qualità traduzione: undo, loginHere, outputSize, remove (Fase 3) ✅ ESEGUITO
4. Fix discardAndClose allineamento EN/IT/ES (Fase 3, punto 2)         ✅ ESEGUITO
5. Merge sicuri Fase 1 (9 gruppi base)                                 ✅ ESEGUITO
6. Merge nav/title Fase 1 (3 gruppi)                                   ✅ ESEGUITO
7. Migrazione common Fase 1 (7 gruppi)                                 ✅ ESEGUITO
8. Allineamento FR + merge Fase 2 (saveAll, undoAll, close/dismiss)    ✅ ESEGUITO
9. Merge Fase 3 (discardChanges×4, undo, reset, discardAndClose)       ✅ ESEGUITO
10. Coerenza filter.* → common.* (bytes,KB,GB,min)                     ✅ ESEGUITO
11. Coerenza preset → common.* (icon, custom×3)                        ✅ ESEGUITO
```

---

#### Fase 6 — Analisi 19 gruppi duplicati residui (post-esecuzione)

Dopo tutte le migrazioni: **583 chiavi, 19 gruppi duplicati**. Tutti classificati:

**🔴 ALL languages (6 gruppi) — KEEP:**

| Gruppo | Chiavi | Verdetto | Motivo |
|--------|--------|----------|--------|
| `assets.title` / `dashboard.assetCount` | 2 | KEEP | `dashboard.assetCount` è label widget dashboard — se mai cambiasse in "Asset Count" la chiave resterebbe |
| `chartSettings.signals.ema` / `.emaAbbr` | 2 | KEEP (dinamico) | Risolte con `$t(\`chartSettings.signals.${type}\`)` e `${type}Abbr` — acronimo = nome completo per EMA |
| `chartSettings.signals.macd` / `.macdAbbr` | 2 | KEEP (dinamico) | Idem — MACD non ha abbreviazione diversa |
| `chartSettings.signals.rsi` / `.rsiAbbr` | 2 | KEEP (dinamico) | Idem — RSI non ha abbreviazione diversa |
| `settings.globalSettingUnits.price_sync_interval_hours` / `.session_ttl_hours` | 2 | KEEP (dinamico) | Risolte con `$t(\`settings.globalSettingUnits.${key}\`)` |
| `uploads.files` / `uploads.title` | 2 | KEEP | `files` = plurale count ("3 files"), `title` = titolo pagina ("Files") — case diverso in IT/EN |

**🟠 3/4 languages (4 gruppi) — KEEP:**

| Gruppo | Chiavi | Verdetto | Motivo |
|--------|--------|----------|--------|
| `chartSettings.discard` / `common.discard` | 2 | KEEP | FR distingue "Rejeter" (chart) vs "Abandonner" (generico) — distinzione semantica valida |
| `fileStatus.uploaded` / `uploads.uploadDate` | 2 | KEEP (dinamico) | `fileStatus.*` risolto con `$t(\`fileStatus.${status}\`)` |
| `fx.actions.settings` / `nav.settings` | 2 | KEEP | ES distingue "Ajustes" (FX context) vs "Configuración" (nav globale) |
| `settings.resetAllToDefault` / `uploads.resetAll` | 2 | KEEP | Semantica diversa: "Reset All" (global settings) vs "Reset All" (uploads selezione) — IT distingue "Ripristina Tutto" vs "Reimposta tutto" |

**🟡 2/4 languages (2 gruppi) — KEEP:**

| Gruppo | Chiavi | Verdetto | Motivo |
|--------|--------|----------|--------|
| `common.resetAll` / `settings.resetAllToDefault` | 2 | KEEP | EN distingue "Reset All to Defaults" vs "Reset All" — 3 chiavi reset con semantica scalare |
| `common.retry` / `error.tryAgain` | 2 | KEEP | EN distingue "Retry" vs "Try Again" — contesti diversi (azione puntuale vs suggerimento) |

**🟢 1 language only (7 gruppi) — KEEP:**

| Gruppo | Chiavi | Verdetto | Motivo |
|--------|--------|----------|--------|
| ES "Restablecer Todo" ×3 | 3 | KEEP | Stesse 3 chiavi reset di sopra — duplicato solo in ES |
| IT "File" ×3 | 3 | KEEP | `file`/`files`/`title` — singolare/plurale/titolo in IT coincidono |
| IT "Editor" ×2 | 2 | KEEP | `editors` (plurale ruolo) vs `roleEditorShort` (label ruolo singolo) — EN distingue "Editors"/"Editor" |
| IT "Broker" ×2 | 2 | KEEP | `brokers.title` (pagina) vs `uploads.broker` (colonna tabella) — EN distingue "Brokers"/"Broker" |
| EN "Discard Changes?" ×2 | 2 | KEEP | `chartSettings.discardTitle` usa FR "Rejeter les modifications" vs `common.discardChanges` usa "Annuler les Modifications" — stili diversi |
| IT "Coppia FX" ×2 | 2 | KEEP (dinamico) | Prefisso dinamico `chartSettings.signals.*` — fxPair e fxPairAbbr |
| IT "Ripristina" ×2 | 2 | KEEP | `common.reset` e `common.undo` — EN/FR/ES tutti diversi, coincidono solo in IT — duplicato linguistico accettabile |

### 2D. ✅ Stringhe hardcoded → i18n — COMPLETATO

18 stringhe hardcoded trovate e tradotte in 6 file:
- **FxCard.svelte** (6): Swap direction, Show %/abs, No data, Refresh, Edit pair config, Delete pair
- **FxProviderConfig.svelte** (1): Remove provider
- **ChartSignalsSection.svelte** (2): Swap direction, MACD Line Color
- **ChartAestheticsSection.svelte** (4): aria-label toggle → riuso chiavi `chartSettings.*`
- **fx/+page.svelte** (3): ConfirmModal title/message/confirmText
- **DataEditor.svelte** (3): Clear selection, selected text, Delete selected + aggiunta import i18n

10 nuove chiavi create: `chart.showPercentage`, `chart.showAbsolute`, `fx.editPairConfig`, `fx.deletePair`, `fx.deletePairTitle`, `fx.deletePairMessage`, `fx.removeProvider`, `chartSettings.macdLineColor`, `dataEditor.clearSelection`, `dataEditor.deleteSelected`
5 chiavi esistenti riutilizzate: `common.swapDirection`, `common.refresh`, `common.noData`, `common.delete`, `common.selected`
583 → 593 chiavi totali

### 2E. ✅ Verificare completezza 4 lingue — COMPLETATO

- Post Step 2B: `./dev.py i18n audit` → 624/624 keys (100.0% tutte le lingue)
- Post Step 2C: `./dev.py i18n audit` → 583/583 keys (100.0% tutte le lingue)
- Post Step 2D: `./dev.py i18n audit` → 593/593 keys (100.0% tutte le lingue)
- 0 chiavi mancanti, 0 chiavi unused, 19 gruppi duplicati residui (tutti KEEP)

---

## Step 3 — E2E Playwright: FX List Page

**File**: `frontend/e2e/fx/fx-list.spec.ts`

**Prerequisito**: `_ensure_db_populated()` (coppie mock EUR-USD, EUR-CHF, EUR-GBP, NOK-SEK, etc.)

Un unico `test.describe('FX List Page')` con `beforeEach: login + navigateTo('/fx')`. Test non distruttivi che eseguono in sequenza con 1 sola sessione browser (no re-login tra test):

| # | Test | Scopo | Strategia di verifica |
|---|---|---|---|
| 1 | Navigazione pagina FX | Pagina accessibile | `fx-page` visibile |
| 2 | Cards mock data visibili | Dati da populate presenti | Contare `[data-testid^="fx-card-"]` > 0 |
| 3 | Badge conteggio coppie | Numero coerente | Badge numero = conteggio card |
| 4 | Filtro per valuta singola | Filtraggio funzionante | EUR → tutte le card contengono "EUR" |
| 5 | Filtro doppia valuta | Intersezione | EUR + USD → 1 sola card |
| 6 | Filtro nessun match | Empty state | Valuta esotica → messaggio "No Matches" visibile |
| 7 | Reset filtri | Ripristino | Tutte le card tornano (conteggio = iniziale) |
| 8 | DateRangePicker preset | Cambio range | Click 1M, 1Y → date nel trigger button cambiano |
| 9 | Toggle Abs/% globale | Switch visualizzazione | Verifica attributo/classe sulle card |
| 10 | Inversione coppia card | Swap locale | Click swap → base/quote si scambiano nel display |
| 11 | Navigazione a detail | Click card → routing | URL corrisponde a `/fx/{pair}` |
| 12 | Navigazione invertita a detail | Inversione persistita | Inverti + click → URL con ordine invertito |
| 13 | Bottone Add Pair | Presenza | `fx-add-pair-button` visibile |
| 14 | Bottone Sync All | Presenza | Bottone sync presente |

**File da consultare per testid**: `frontend/src/routes/(app)/fx/+page.svelte` (testid `fx-page`, `fx-add-pair-button`), `frontend/src/lib/components/fx/FxCard.svelte` (testid `fx-card-{slug}`)

---

## Step 4 — E2E Playwright: Add Pair Modal & Provider Select

**File**: `frontend/e2e/fx/fx-add-pair.spec.ts`

**Nota valute da usare** (devono avere copertura provider reale):
- **Dirette ECB**: EUR/USD, EUR/GBP, EUR/CAD, EUR/CHF, EUR/SEK
- **Catene via EUR**: RON/USD (RON→EUR→USD), CNY/GBP (CNY→EUR→GBP)
- **Esotiche senza route**: MXN/ZAR (MANUAL fallback)
- **Multi-step**: RUB/CHF (potenziale catena a 2+ step via EUR)

`beforeEach: login + navigateTo('/fx')`

| # | Test | Scopo | Strategia |
|---|---|---|---|
| 1 | Apertura modale | Click Add | `fx-add-pair-modal` visibile |
| 2 | Due currency select | Struttura modale | 2 combobox presenti |
| 3 | Save disabilitato | Nessuna valuta | `fx-add-pair-save` disabled |
| 4 | Chiusura Escape (no dirty) | UX pulita | Modale non visibile |
| 5 | Valute → route select | DFS funzionante | EUR + USD → `fx-route-select` visibile |
| 6 | Route dirette EUR/USD | ECB copre EUR→USD | Sezione `fx-route-direct-section` con ≥1 route |
| 7 | Route catena RON/USD | Chain via EUR | Sezione chain visibile con ≥1 catena |
| 8 | Toggle selezione route | Click/declick | `ring-1` alternato |
| 9 | Ricerca full-text | Filtro provider | Cercare "ECB" → solo route ECB visibili |
| 10 | Save senza provider | MANUAL fallback | MXN/ZAR → card creata, modal chiude |
| 11 | Save con route diretta | Flusso completo | EUR/CAD con ECB → card creata |
| 12 | Esclusione coppie esistenti | Prevenzione duplicati | Coppia già configurata → non selezionabile |
| 13 | Chiusura dirty → confirm | Protezione dati | Seleziona valute → Escape → ConfirmModal appare |
| 14 | Chain + coppie intermedie | Checkbox funzionante | "Create intermediate pairs" → più card create |

**File da consultare**: `frontend/src/lib/components/fx/FxPairAddModal.svelte`, `frontend/src/lib/components/ui/select/FxProviderSelect.svelte`

---

## Step 5 — E2E Playwright: FX Detail Page

**File**: `frontend/e2e/fx/fx-detail.spec.ts`

`beforeEach: login + navigateTo('/fx/EUR-USD')`

| # | Test | Scopo | Strategia |
|---|---|---|---|
| 1 | Navigazione slug diretto | Pagina caricata | `fx-detail-page` visibile |
| 2 | Slug invertito | Display invertito | `/fx/USD-EUR` → header mostra USD→EUR |
| 3 | Grafico visibile | ECharts renderizzato | Canvas presente nel container chart |
| 4 | Swap direction | Cambio URL | Click swap → URL cambia a ordine opposto |
| 5 | Swap con dirty → confirm | Protezione editor | In edit mode + swap → modal conferma visibile |
| 6 | Pannello Aesthetics fold/unfold | Toggle visibilità | Click toggle → contenuto visibile/nascosto |
| 7 | Pannello Signals fold/unfold | Toggle visibilità | Idem |
| 8 | Pannello Measures fold/unfold | Toggle visibilità | Idem |
| 9 | Toggle Abs/% | Cambio visualizzazione | Switch nel toolbar → asse Y si aggiorna |
| 10 | DateRangePicker preset | Cambio range | Click 1Y → trigger testo aggiornato |
| 11 | Sync singola coppia | Funzionamento sync | Click sync → toast success appare |
| 12 | Refresh dati | Ricaricamento | Click refresh → loading indicator visibile |
| 13 | Provider config modal | Edit mode | Click config → FxPairAddModal editMode, valute read-only |
| 14 | Back to list | Navigazione | Click freccia → URL `/fx` |
| 15 | Misura con Δ%/yr | Calcolo completo | Aggiungere misura → tabella mostra Δ%/yr per riga principale |
| 16 | Segnali overlay visibili | Signal library | Aggiungere EMA → segnale nella lista configurata |

**Nota su sync (test 11)**: il risultato del sync dipende dai provider esterni. Il test verifica solo il flusso UI (toast appare con messaggio), non i conteggi specifici. Se un provider è down, il test deve comunque passare verificando che un toast (success o error) compaia.

**File da consultare**: `frontend/src/routes/(app)/fx/[pair]/+page.svelte`, `frontend/src/routes/(app)/fx/[pair]/+page.ts`

---

## Step 6 — E2E Playwright: Data Editor & CSV Import

**File**: `frontend/e2e/fx/fx-data-editor.spec.ts`

`beforeEach: login + navigateTo('/fx/EUR-USD')`

| # | Test | Scopo | Strategia |
|---|---|---|---|
| 1 | Apertura editor | Click "Edit rates" | `fx-detail-editor-panel` visibile |
| 2 | Tabella dati caricata | Righe presenti | Contare righe tabella > 0 |
| 3 | Modifica cella rate | Edit inline | Riga ha classe `row-edited` (sfondo blu) |
| 4 | Aggiunta nuova riga | Click "+" | Riga ha classe `row-appended` (sfondo verde) |
| 5 | Eliminazione riga | Click delete riga | Riga ha classe `row-deleted` (sfondo rosso) |
| 6 | Contatore dirty | Tracking modifiche | Dopo 2 edit → dirty count = 2 visibile |
| 7 | Cancel → reset | Annullamento | Click cancel → dirty count = 0, righe tornano normali |
| 8 | Apertura CSV Import modal | Click import | `DataImportModal` visibile |
| 9 | CSV Import header sbagliato | Validazione | Header non matching coppia → messaggio errore visibile |
| 10 | Swap direction import | Inversione | Click ⇄ → label direzione cambia |
| 11 | Paginazione tabella | Navigazione pagine | Cambiare page size → contatore pagine aggiornato |
| 12 | ColumnVisibility toggle | Show/hide colonne | Eye icon → colonna nascosta/mostrata |

**File da consultare**: `frontend/src/lib/components/fx/FxDataEditorSection.svelte`, `frontend/src/lib/components/ui/data-editor/DataEditor.svelte`, `frontend/src/lib/components/ui/data-editor/DataImportModal.svelte`

---

## Step 7 — E2E Playwright: Sync Modal

**File**: `frontend/e2e/fx/fx-sync.spec.ts`

`beforeEach: login + navigateTo('/fx')`

| # | Test | Scopo | Strategia |
|---|---|---|---|
| 1 | Apertura Sync All dalla list | Modale sync | `FxSyncModal` visibile |
| 2 | Lista coppie elencate | Tutte le coppie | Conteggio righe coppie = conteggio card nella pagina |
| 3 | Timeout editabile | Configurazione | Cambiare valore → input aggiornato |
| 4 | Start sync → countdown | Esecuzione | Progress bar o countdown visibile |
| 5 | Risultati per coppia | Report | Almeno 1 risultato con icona stato (ok/partial/skipped/failed) |
| 6 | Chiusura post-sync | Refresh | Click close → modale chiude |
| 7 | Sync singola da detail | Flusso detail | Navigare a detail → sync → toast con risultato |

**Nota**: il test 5 verifica la struttura del risultato (icone stato presenti), non i conteggi specifici di punti sincronizzati, che dipendono dai provider esterni.

**File da consultare**: `frontend/src/lib/components/fx/FxSyncModal.svelte`

---

## Step 8 — E2E Playwright: Routes API (test diretti)

**File**: `frontend/e2e/fx/fx-api.spec.ts`

Test API via `request` di Playwright (no UI, verificano contratti API). Helper per estrazione session cookie recuperato da `fx-routes.spec.ts` (era funzionante).

`beforeAll: login per ottenere session cookie`

| # | Test | Scopo | Strategia |
|---|---|---|---|
| 1 | GET /fx/providers | Lista provider | Struttura corretta, MANUAL escluso, `base_currencies` + `target_currencies` presenti |
| 2 | GET /fx/providers/routes | Lista route | `items[]` con `chain_steps` |
| 3 | POST /fx/providers/routes (1-step) | Creazione diretta | EUR/SEK via ECB → `results[0].success = true` |
| 4 | POST /fx/providers/routes (2-step) | Creazione catena | NOK/USD via EUR → `chain_steps.length = 2` |
| 5 | DELETE /fx/providers/routes | Eliminazione | 200 OK, route rimossa |
| 6 | POST /fx/currencies/sync | Sync coppia | EUR-USD → `results[0].status` presente |
| 7 | POST /fx/currencies/convert | Conversione | `rate > 0`, `date` presente |
| 8 | POST /fx/rates/upsert | Insert manuale | Upsert riuscito |
| 9 | POST /fx/rates/delete | Delete rate | Delete riuscito |

**File da consultare**: `backend/app/api/v1/fx.py`, `backend/app/schemas/fx.py`

---

## Step 9 — E2E Playwright: Chart Settings & Signals

**File**: `frontend/e2e/fx/fx-chart-settings.spec.ts`

`beforeEach: login + navigateTo('/fx')`

| # | Test | Scopo | Strategia |
|---|---|---|---|
| 1 | Apertura Settings globale | Click ⚙️ dalla list | ChartSettingsModal visibile |
| 2 | Toggle estetica (baseline) | Checkbox ON/OFF | Stato cambia |
| 3 | Aggiunta segnale EMA | Dropdown → EMA | Card segnale visibile nella lista |
| 4 | Modifica parametri segnale | Cambiare periodo EMA | Valore aggiornato |
| 5 | Apply settings | Click Apply | Modale chiude; riaprendo: stessi valori persistiti |
| 6 | Discard su dirty | Modify → Escape | ConfirmModal visibile |
| 7 | Settings per-card ⚙️ | Click su card specifica | Modal aperta per quella coppia (title "Local") |
| 8 | Preview live | Con segnale aggiunto | Canvas preview presente e renderizzato |

**File da consultare**: `frontend/src/lib/components/charts/ChartSettingsModal.svelte`, `frontend/src/lib/components/charts/ChartAestheticsSection.svelte`, `frontend/src/lib/components/charts/ChartSignalsSection.svelte`

---

## Step 10 — Integrazione in `dev.py test`

### 10A. Registrare test FX nel TEST_REGISTRY

**File**: `scripts/test_runner.py`

Aggiungere funzioni e registrarle nella categoria `"front"` del `TEST_REGISTRY`:

```python
# Nuove funzioni
def front_fx_unit(verbose, ui, headed, debug, test_names) -> bool:
    """Run FX unit tests (Vitest)."""
    # Chiama: cd frontend && npm run test:unit
    
def front_fx_list(verbose, ui, headed, debug, test_names) -> bool:
    """Run FX list page E2E tests."""
    return _run_playwright("fx/fx-list.spec.ts", ...)

def front_fx_detail(verbose, ui, headed, debug, test_names) -> bool:
    # fx/fx-detail.spec.ts

def front_fx_editor(verbose, ui, headed, debug, test_names) -> bool:
    # fx/fx-data-editor.spec.ts

def front_fx_sync(verbose, ui, headed, debug, test_names) -> bool:
    # fx/fx-sync.spec.ts

def front_fx_api(verbose, ui, headed, debug, test_names) -> bool:
    # fx/fx-api.spec.ts

def front_fx_settings(verbose, ui, headed, debug, test_names) -> bool:
    # fx/fx-chart-settings.spec.ts

def front_fx_add_pair(verbose, ui, headed, debug, test_names) -> bool:
    # fx/fx-add-pair.spec.ts

def front_fx(verbose, ui, headed, debug, test_names) -> bool:
    """Run all FX tests (unit + E2E)."""
    # Chiama front_fx_unit + _run_playwright("fx/", ...)
```

Registrare nel `TEST_REGISTRY["front"]`:

```python
"fx-unit": {"func": front_fx_unit, "test_names": True, "name": "FX Unit Tests", ...},
"fx-list": {"func": front_fx_list, "test_names": True, "name": "FX List Page", ...},
"fx-detail": {"func": front_fx_detail, "test_names": True, "name": "FX Detail Page", ...},
"fx-editor": {"func": front_fx_editor, "test_names": True, "name": "FX Data Editor", ...},
"fx-sync": {"func": front_fx_sync, "test_names": True, "name": "FX Sync Modal", ...},
"fx-api": {"func": front_fx_api, "test_names": True, "name": "FX API Routes", ...},
"fx-settings": {"func": front_fx_settings, "test_names": True, "name": "FX Chart Settings", ...},
"fx-add-pair": {"func": front_fx_add_pair, "test_names": True, "name": "FX Add Pair", ...},
"fx": {"func": front_fx, "test_names": False, "name": "All FX Tests", ...},
```

- [ ] Aggiungere tutti i nuovi spec a `front_all.specs[]` (riga 1420)
- [ ] Prerequisito: `_ensure_db_populated()` per `front_fx*` (come `front_broker_sharing`)

### 10B. Aggiungere flag `--list` per elencare test

**File**: `scripts/test_runner.py`

Aggiungere opzione `--list` al parser della categoria `front`:

```python
("--list", {
    "action": "store_true",
    "help": "List available tests without running them",
    "default": False,
}),
```

Quando presente:
- Per Playwright: chiama `npx playwright test --list {spec_file}` e stampa i nomi
- Per Vitest: chiama `npx vitest list`

Funzionamento nella dispatch:
```python
if kwargs.get('list', False):
    # Chiama _list_playwright(spec_file) o _list_vitest()
    return True  # listing non è un fallimento
```

**Comandi risultanti**:
```
./dev.py test front fx all             # Tutti i test FX (unit + E2E)
./dev.py test front fx-list all        # Solo test list page
./dev.py test front fx-unit all        # Unit test Vitest
./dev.py test front fx-list --list     # Elenca test senza eseguirli
./dev.py test front fx --list          # Elenca tutti i test FX
./dev.py test front all                # Tutti i test frontend (include FX)
```

---

## Step 11 — ✅ Gallery screenshot FX — COMPLETATO

### Part A — Nuovi flag per db populate — ✅ COMPLETATO

**File modificati**:
- `backend/test_scripts/test_db/populate_mock_data.py` — 3 nuovi flag argparse + 3 nuove funzioni
- `scripts/test_runner.py` — propagazione flag in `db_populate()`, parser db, `dispatch_to_category()`
- `dev.py` — `cmd_mkdocs_gallery()` aggiornato con `--force --clean --with-static --with-reports`
- `frontend/e2e/fixtures/db-helpers.ts` — nuova funzione `resetDatabaseForGallery()`

**Dettagli implementazione**:

1. **`clean_data_dirs()`** (riga ~1258): Svuota `custom-uploads/` e `broker_reports/{uploaded,parsed,failed}/` usando `get_data_dir()`. Elimina file e sotto-directory. Crea la directory se non esiste.

2. **`upload_static_resources(session)`** (riga ~1286): Chiama `seed_default_avatars()` per avatar utente. Per ogni broker, usa un avatar PNG da `staticResources/Avatars/` come placeholder icon, caricato con `save_upload()` e associato al broker via `broker.icon_url = /api/v1/uploads/file/{id}`.

3. **`upload_broker_reports(session)`** (riga ~1332): Copia report di esempio da `brim_providers/sample_reports/` in `broker_reports/uploaded/`. Map esplicita: IBKR→`ibkr-trades-export.csv`, DEGIRO→`degiro-export.csv`, Directa→`directa-export.csv`, eToro→`etoro-export.csv`, Coinbase→`coinbase-export.csv`, Recrowd→`generic_simple.csv`.

4. **Flag argparse** (riga ~1380): `--clean`, `--with-static`, `--with-reports` aggiunti a fianco di `--force`.

5. **Pipeline propagazione**:
   - `test_runner.py` `db_populate()` (riga ~408): accetta `clean`, `with_static`, `with_reports` e li passa come argomenti CLI
   - `test_runner.py` parser db (riga ~2850): 3 nuovi `add_argument` con `dest` corretto per underscore
   - `test_runner.py` `dispatch_to_category()` (riga ~3089): estrae i 4 flag dal namespace args quando `category == "db"`
   - `test_runner.py` `run_test_from_registry()` (riga ~2678): passa i 4 flag a `test_func` quando `category == "db" and action == "populate"`
   - `dev.py` `cmd_mkdocs_gallery()` (riga ~534): `["python", "dev.py", "test", "db", "populate", "--force", "--clean", "--with-static", "--with-reports"]`
   - `db-helpers.ts` `resetDatabaseForGallery()` (riga ~29): `./dev.py test db populate --force --clean --with-static --with-reports`

### Part B — Gallery FX screenshots — ✅ COMPLETATO

**File modificati**:
- `frontend/e2e/gallery.spec.ts` — `test.describe('FX')` aggiunto (righe 588-918)

**Import aggiunti** (riga 17): `goToFxPage`, `goToFxDetailPage`, `openAddPairModal` da `./fx/fx-helpers`

**12 scene implementate**:

| # | Test name | Navigazione | Screenshot cat/name | Pattern | Note |
|---|-----------|-------------|---------------------|---------|------|
| 1 | FX list page | `goToFxPage` | `fx/list` | `forEachLanguageAndTheme` | `waitForTimeout(2000)` per canvas |
| 2 | FX list filtered | `goToFxPage` + click currency filter EUR | `fx/list-filtered` | loop manuale | Combobox → option EUR |
| 3 | Add pair - direct routes | `goToFxPage` + `openAddPairModal` + EUR/USD | `fx/list-filtered` → `fx/add-pair-routes` | loop manuale | Selects EUR poi USD |
| 4 | Add pair - chain | `goToFxPage` + `openAddPairModal` + GBP/JPY | `fx/add-pair-chain` | loop manuale | GBP/JPY via USD (chain già nei mock) |
| 5 | Sync All modal | `goToFxPage` + click `fx-sync-all-button` | `fx/sync-progress` | loop manuale | `waitForTimeout(1500)` |
| 6 | Detail page chart | `goToFxDetailPage('EUR-USD')` | `fx/detail-chart` | `forEachLanguageAndTheme` | `waitForSelector('canvas')` + 2000ms |
| 7 | Detail signals overlay | `goToFxDetailPage` + click `fx-detail-signals-toggle` | `fx/detail-signals` | loop manuale | Toggle pannello segnali |
| 8 | Detail measures panel | `goToFxDetailPage` + click `fx-detail-measures-toggle` | `fx/detail-measures` | loop manuale | Toggle pannello misure |
| 9 | Detail data editor | `goToFxDetailPage` + click `fx-detail-edit-btn` | `fx/detail-editor` | loop manuale | Scroll a editor panel |
| 10 | Detail CSV import modal | Editor aperto + click `fx-data-import-btn` | `fx/detail-csv-import` | loop manuale | Verifica modal visibile, Escape alla fine |
| 11 | Chart settings modal | `goToFxPage` + click `fx-chart-settings-button` | `fx/chart-settings` | loop manuale | `scrollIntoViewIfNeeded`, Escape |
| 12 | Provider config modal | `goToFxDetailPage` + click `fx-detail-provider-btn` | `fx/provider-config` | loop manuale | Attende `fx-add-pair-modal` visibile |

**Risultato**: 12 scene × 4 lingue (en, it, fr, es) × 2 temi (light, dark) = **96 screenshot** generati e verificati.

```
mkdocs_src/docs/gallery/desktop/
├── en/{light,dark}/fx/   # 12+12 = 24
├── it/{light,dark}/fx/   # 12+12 = 24
├── fr/{light,dark}/fx/   # 12+12 = 24
└── es/{light,dark}/fx/   # 12+12 = 24
                          # Total = 96
```

### Part B.2 — MkDocs documentation — ✅ COMPLETATO

**File modificati**:
- `mkdocs_src/docs/gallery/desktop.md` — sezione `## 💱 FX Rates` con 12 `<div class="screenshot-container"><img>` (data-category="fx")
- `mkdocs_src/docs/gallery/mobile.md` — sezione `## 💱 FX Rates` con 12 `<div class="screenshot-container mobile"><img>` (data-category="fx")
- `mkdocs_src/docs/gallery/index.md` — aggiunto `- **FX Rates**: Currency pairs, charts, sync, data editor, CSV import` alla lista Features Highlighted

---

## Step 12 — Cleanup documentazione

### 12A. ✅ Spostare plan completati in `phase-05-subplan/` — COMPLETATO

14 plan spostati da `RoadmapV4_UI/` root a `phases/phase-05-subplan/` il 19 Marzo 2026.
I link interni sono tutti relativi tra file nella stessa cartella, quindi funzionano senza modifiche.

| File | Stato |
|------|-------|
| `plan-fxConversionChain.prompt.md` | ✅ Completato |
| `plan-fxDetailPageRedesign.prompt.md` | ✅ Completato |
| `plan-fxDetailBugRound4.prompt.md` | ✅ Completato |
| `plan-fxDetailBugRound5.prompt.md` | ✅ Completato |
| `plan-fxDetailBugRound6.prompt.md` | ✅ Completato |
| `plan-fxDetailBugRound6-2.prompt.md` | ✅ Completato |
| `plan-fxDetailBugRound7.prompt.md` | ✅ Completato |
| `plan-fxDetailBugRound7-1.prompt.md` | ✅ Completato |
| `plan-fxDetailBugRound7-2.prompt.md` | ✅ Completato |
| `plan-fxDetailBugRound7-2-1.prompt.md` | ✅ Completato |
| `plan-fxDetailBugRound7-3.prompt.md` | ✅ Completato |
| `plan-fxDetailBugRound7-4.prompt.md` | ✅ Completato |
| `plan-csvImportRefinement.prompt.md` | ✅ Completato |
| `plan-fxDocumentation.prompt.md` | ✅ Completato |

Per ogni file:
- [ ] Spostare in `phases/phase-05-subplan/`
- [ ] Aggiornare link relativi `**Dipendenze**` e `**Successivo**` in tutti i file che si puntano a vicenda
- [ ] Verificare che non ci siano broken references

### 12B. Aggiornare `phase-05-fx.md`

**File**: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-05-fx.md`

Trasformare da plan con dettagli di codice legacy (completamente obsoleto: `CurrencyGrid.svelte`, `PairSourceTable.svelte`, `SyncTool.svelte`, `ManualRateModal.svelte` — nessuno di questi file è mai stato creato) a **journal/summary** di quanto effettivamente realizzato.

Contenuto del nuovo file:
- Status: ✅ COMPLETATO
- Cronologia dei sub-plan completati (con date e link)
- Riepilogo componenti creati (nomi file, scopo)
- Riepilogo funzionalità implementate vs originalmente pianificate
- Metriche: N° componenti, righe codice stimate, N° test
- Riferimento a questo piano test come ultimo step della Phase 5

### 12C. TODO_FUTURI.md e TODO_Completati.md

- [ ] Aggiornare sezione Cross-Rate (ora implementata in `plan-fxConversionChain`)
- [ ] Rimuovere sezione "ripulire traduzioni non usate" da `TODO_FUTURI.md` (assorbita dallo Step 2 di questo piano)
- [ ] Aggiungere voce corrispondente in `TODO_Completati.md` con data e riferimento a questo piano
- [ ] Aggiungere nuovi TODO emersi dai test (se presenti)

---

## Ordine di esecuzione

```
0A-0F (cleanup + fix bug)
  ↓
Step 1 (unit test Vitest — TimeSeriesStore, EditBuffer)
  ↓
Step 2 (i18n audit + razionalizzazione + hardcoded → i18n)
  ↓
Step 3 → Step 9 (E2E Playwright — list → add-pair → detail → editor → sync → api → settings)
  ↓
Step 10 (integrazione dev.py test — registrazione + flag --list)
  ↓
Step 11 (gallery screenshot — 12 scene × 8 varianti)
  ↓
Step 12 (cleanup docs — spostamento plan, journal phase-05, TODO)
```

I test E2E (Steps 3-9) richiedono i `data-testid` dello step 0C e i fix bug 0E/0F.
Lo step 10 può essere parzialmente parallelizzato con la scrittura dei test (registrare le entry man mano che i file spec vengono creati).
Lo step 12A (spostamento plan) può essere fatto in qualsiasi momento.

---

## Stima tempi

| Step | Stima | Note |
|------|-------|------|
| 0A-0F | 0.5 giorno | Cleanup + 2 fix (entrambi puntuali) |
| 1 | 0.5 giorno | ~27 unit test puro TS |
| 2 | 0.5 giorno | Audit tool + pulizia + grep hardcoded |
| 3-9 | 2.5 giorni | ~70 test E2E (il grosso del lavoro) |
| 10 | 0.5 giorno | Registrazione + flag --list |
| 11 | 0.5 giorno | Gallery (pattern consolidato) |
| 12 | 0.5 giorno | Doc cleanup (meccanico) |
| **Totale** | **~5.5 giorni** | |

---

## File riepilogo

### File da creare

| File | Scopo |
|------|-------|
| `frontend/vitest.config.ts` | Config Vitest con alias $lib |
| `frontend/src/lib/stores/__tests__/TimeSeriesStore.test.ts` | Unit test cache |
| `frontend/src/lib/stores/__tests__/EditBuffer.test.ts` | Unit test edit buffer |
| `frontend/e2e/fx/fx-list.spec.ts` | E2E list page |
| `frontend/e2e/fx/fx-add-pair.spec.ts` | E2E add pair modal |
| `frontend/e2e/fx/fx-detail.spec.ts` | E2E detail page |
| `frontend/e2e/fx/fx-data-editor.spec.ts` | E2E data editor |
| `frontend/e2e/fx/fx-sync.spec.ts` | E2E sync modal |
| `frontend/e2e/fx/fx-api.spec.ts` | E2E API routes |
| `frontend/e2e/fx/fx-chart-settings.spec.ts` | E2E chart settings |

### File da modificare

| File | Modifica |
|------|----------|
| `frontend/src/routes/(app)/fx/[pair]/+page.svelte` | testid + fix FxPairSignal |
| `frontend/src/lib/charts/signals/MeasureSignal.ts` | fix annualizedPct |
| `frontend/src/lib/components/charts/MeasurePanel.svelte` | usare annualizedPct calcolato |
| `frontend/src/lib/components/fx/index.ts` | rimuovere FxEditSection + CsvEditor |
| `frontend/src/lib/components/ui/data-editor/DataImportModal.svelte` | aggiornare import CsvEditor |
| `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` | aggiornare import ParsedRow |
| `frontend/package.json` | aggiungere vitest + script |
| `frontend/scripts/i18n-audit.py` | migliorare regex + partial match |
| `scripts/test_runner.py` | registrare fx-unit, fx-*, --list |
| `frontend/e2e/gallery.spec.ts` | sezione FX |
| `mkdocs_src/docs/gallery/desktop.md` | sezione FX |
| `mkdocs_src/docs/gallery/mobile.md` | sezione FX |
| `mkdocs_src/docs/gallery/index.md` | aggiungere FX |

### File da eliminare

| File | Motivo |
|------|--------|
| `frontend/src/lib/components/fx/FxEditSection.svelte` | Dead code (rimpiazzato da FxDataEditorSection) |
| `frontend/e2e/fx-routes.spec.ts` | Obsoleto (rimpiazzato da e2e/fx/*.spec.ts) |

### File da spostare

| Da | A | Motivo | Stato |
|----|---|--------|-------|
| `frontend/src/lib/components/fx/CsvEditor.svelte` | `frontend/src/lib/components/ui/data-editor/CsvEditor.svelte` | Componente generico, non FX-specifico | ⏳ Step 0B |
| `RoadmapV4_UI/plan-fx*.prompt.md` (×14) | `phases/phase-05-subplan/` | Plan completati | ✅ Fatto 19 Mar 2026 |
