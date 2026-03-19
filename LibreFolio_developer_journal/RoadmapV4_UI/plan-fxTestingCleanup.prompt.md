# Plan: FX Testing & Cleanup — E2E, Unit Tests, i18n Audit, Gallery

**Data creazione**: 12 Marzo 2026
**Ultima revisione**: 19 Marzo 2026
**Status**: 🔧 IN PROGRESS — Steps 1-9 verificati (3 fix in fx-list.spec.ts da rivalidare), Steps 10-12 da fare
**Priorità**: Alta (zero copertura E2E FX, 2 bug noti da fixare)
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
| 19 Mar 2026 | 🔍 Pre-Step 0A | Eliminato `FxEditSection.svelte` (dead code) — UNDER REVIEW |
| 19 Mar 2026 | 🔍 Pre-Step 0B | Spostato `CsvEditor.svelte` in `ui/data-editor/` — UNDER REVIEW |
| 19 Mar 2026 | 🔍 Pre-Step 0C | 20 `data-testid` aggiunti nella pagina FX detail — UNDER REVIEW |
| 19 Mar 2026 | 🔍 Pre-Step 0D | Eliminato `fx-routes.spec.ts`, creato `e2e/fx/fx-helpers.ts` — UNDER REVIEW |
| 19 Mar 2026 | 🔍 Pre-Step 0E | Fix FxPairSignal nella detail page (`_resolvedData`) — UNDER REVIEW |
| 19 Mar 2026 | 🔍 Pre-Step 0F | Fix `annualizedPct` in `MeasureSignal.getMeasurementForSignal()` — UNDER REVIEW |
| 19 Mar 2026 | ✅ Step 1 | 27 unit test Vitest (15 TimeSeriesStore + 12 EditBuffer) — **PASSED** (27/27) |
| 19 Mar 2026 | 🔍 Step 2 | i18n: stringhe hardcoded tradotte (MeasurePanel, FxDetail, BrokerDetail) — UNDER REVIEW |
| 19 Mar 2026 | 🔧 Step 3 | E2E FX List Page — 7/10 passed, 3 failed (badge count, filter, reset) — fix applicati |
| 19 Mar 2026 | ✅ Step 4 | E2E FX Add Pair Modal — **PASSED** (5/5) |
| 19 Mar 2026 | ✅ Step 5 | E2E FX Detail Page — **PASSED** (12/12) |
| 19 Mar 2026 | ✅ Step 6 | E2E FX Data Editor — **PASSED** (3/3) |
| 19 Mar 2026 | ✅ Step 7 | E2E FX Sync — **PASSED** (3/3) |
| 19 Mar 2026 | ✅ Step 8 | E2E FX API Routes — **PASSED** (3/3) |
| 19 Mar 2026 | ✅ Step 9 | E2E FX Chart Settings — **PASSED** (3/3) |
| 19 Mar 2026 | 🔍 Step 10 | Registrazione in `dev.py test` + riorganizzazione categorie (front-utility, front-user, front-fx) — UNDER REVIEW |
| 19 Mar 2026 | ✅ Step 12A | 14 plan file spostati in `phases/phase-05-subplan/` |
| 19 Mar 2026 | ✅ Step 12B | `phase-05-fx.md` riscritto come summary |
| 19 Mar 2026 | 🔍 Step 12C | Aggiornato TODO_Completati.md e TODO_FUTURI.md — UNDER REVIEW |
| 19 Mar 2026 | ✅ Fix port | `--force` flag aggiunto a `./dev.py server` + `playwright.config.ts` usa `--force` |
| 19 Mar 2026 | ✅ Fix testid | `data-testid` aggiunti: `fx-currency-filter`, `fx-reset-filters`, `fx-date-range-picker`, `fx-pair-label`, `fx-swap-btn` |
| 19 Mar 2026 | ✅ Fix tests | Test 4/7/8/10 in `fx-list.spec.ts` resi reali (rimossi if-guard, asserzioni dirette) |
| 19 Mar 2026 | 🔧 Fix tests | Test 3: card count collision (testid prefix `fx-card-` matchava figli) → rinominati a `fx-pair-label`/`fx-swap-btn` |
| 19 Mar 2026 | 🔧 Fix tests | Test 4/5: `SearchSelect` usa `<button>` non `[role=option]` → corretto selettore |
| 19 Mar 2026 | ✅ Fix dev.py | `_print_port_help()` estratta come funzione condivisa, usata da entrambi i path (force/non-force) |

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

### 2A. Migliorare lo strumento i18n-audit

**File**: `frontend/scripts/i18n-audit.py`

Le regex `patterns_dynamic` (righe 98-103) catturano prefissi da template literal (`` `prefix.${var}` ``) e concatenazione (`'prefix.' + var`). Tuttavia mancano alcuni pattern usati nel codice:

1. **Chiavi con suffisso variabile**: `$t(\`chartSettings.signals.\${type}Abbr\`)` — il prefisso catturato è `chartSettings.signals` ma il suffisso composito (`emaAbbr`, `rsiAbbr`) non viene matchato individualmente. Le chiavi finali sono coperte dal prefix matching, ma il report dovrebbe segnalarle come "match parziale (dinamico)".

2. **Concatenazione a 2+ segmenti**: `$t('chartSettings.signals.' + key)` — la regex attuale cattura `chartSettings.signals` come prefisso. Verificare che funzioni per concatenazioni su 2+ livelli di profondità.

3. **Nuovo output**: aggiungere una sezione **"⚠️ Partial Match (Dynamic)"** nel report che elenca chiavi marcate come "non usate" il cui prefisso fino al penultimo segmento appare tra i pattern dinamici rilevati. Messaggio: "Possibile match dinamico, verifica manuale necessaria".

- [ ] Aggiungere regex per pattern `$t(prefix + '.' + suffix + key)` con 2+ segmenti
- [ ] Aggiungere sezione "Partial Match (Dynamic)" nel report `generate_unused_keys_report()`
- [ ] Testare con `./dev.py i18n audit` e verificare che i falsi positivi diminuiscano

### 2B. Pulizia chiavi non usate

- [ ] Eseguire `./dev.py i18n audit`, analizzare output
- [ ] Distinguere chiavi veramente morte da falsi positivi dinamici (usando la nuova sezione 2A)
- [ ] Eliminare chiavi confermate inutilizzate con `./dev.py i18n remove`

### 2C. Razionalizzazione chiavi

- [ ] Verificare consistenza categorizzazione: `fx.*`, `fxDetail.*`, `chartSettings.*`, `measure.*`, `chart.*`, `csvImport.*`
- [ ] Cercare chiavi duplicate/sovrapponibili tra sezioni (es. `common.save` vs potenziali duplicati)
- [ ] Consolidare o duplicare esplicitamente dove serve

### 2D. Stringhe hardcoded → i18n

Grep sistematico nei file FX per stringhe hardcoded da tradurre:

**File da ispezionare**:
- `frontend/src/lib/components/fx/*.svelte`
- `frontend/src/lib/components/charts/*.svelte`
- `frontend/src/routes/(app)/fx/**/*.svelte`
- `frontend/src/lib/components/ui/data-editor/*.svelte`

Casi già identificati:
- `MeasurePanel.svelte` righe 276/281/286 — header colonne `'Δ Abs'`, `'Δ %'`, `'Δ%/yr'` non i18n (le altre colonne usano `$t()`)
- Cercare altri con: `grep -rn '"[A-Z][a-z]' --include="*.svelte"` nei file sopra
- Annotare stringhe backend hardcoded (es. "System Broker creation") come TODO futuri

### 2E. Verificare completezza 4 lingue

- [ ] `./dev.py i18n audit` — tutte le chiavi devono avere valore in EN/IT/FR/ES
- [ ] Aggiungere chiavi mancanti con `./dev.py i18n add`

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

## Step 11 — Gallery screenshot FX

**File da modificare**:
- `frontend/e2e/gallery.spec.ts` — aggiungere `test.describe('FX')`
- `mkdocs_src/docs/gallery/desktop.md` — nuova sezione
- `mkdocs_src/docs/gallery/mobile.md` — nuova sezione
- `mkdocs_src/docs/gallery/index.md` — aggiungere FX alla lista features

Aggiungere un `test.describe('FX')` nella gallery con screenshot:

| # | Screenshot | Categoria | Nome | Note |
|---|---|---|---|---|
| 1 | FX list page con card | `fx` | `list` | 4-6 card con mini-chart |
| 2 | FX list con filtro valuta | `fx` | `list-filtered` | Filtro EUR attivo |
| 3 | Add Pair modal con route dirette | `fx` | `add-pair-routes` | EUR/USD con ECB visibile |
| 4 | Add Pair modal con catena | `fx` | `add-pair-chain` | RON/USD con catena via EUR |
| 5 | Sync All modal | `fx` | `sync-progress` | Con risultati per coppia |
| 6 | FX detail page con chart | `fx` | `detail-chart` | Grafico linea con dati |
| 7 | FX detail con segnale overlay | `fx` | `detail-signals` | Pannello segnali aperto con EMA |
| 8 | FX detail con misure | `fx` | `detail-measures` | MeasurePanel con tabella riepilogo |
| 9 | FX detail Data Editor | `fx` | `detail-editor` | DataEditor con righe colorate |
| 10 | FX detail CSV Import modal | `fx` | `detail-csv-import` | DataImportModal con preview |
| 11 | ChartSettingsModal | `fx` | `chart-settings` | Settings con EMA + Bollinger |
| 12 | Provider config (edit mode) | `fx` | `provider-config` | FxPairAddModal con catena |

Ogni screenshot: 4 lingue × 2 temi = 8 varianti × 12 = **96 nuovi screenshot**.

Aggiornare `desktop.md` e `mobile.md` con sezione `## 💱 FX Rates` contenente tutti i nuovi screenshot con descrizioni bilingue.

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
