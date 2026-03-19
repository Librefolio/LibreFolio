# Agent Prompt: FX Testing & Cleanup — Phase 5 Finale

## Chi sei e cosa stai facendo

Sei un agente di sviluppo che lavora su **LibreFolio**, un portfolio tracker finanziario open-source con:
- **Backend**: Python (FastAPI + SQLAlchemy + Alembic)
- **Frontend**: SvelteKit 5 (runes mode `$state`, `$derived`, `$effect`) + TypeScript + Tailwind CSS + ECharts
- **Test E2E**: Playwright
- **Test unitari frontend**: Vitest (da configurare)
- **i18n**: `svelte-i18n` con 4 lingue (EN, IT, FR, ES) — file JSON in `frontend/src/lib/i18n/`
- **Dev CLI**: `./dev.py` — script Python con sistema di comandi (`test`, `front`, `db`, `i18n`, ecc.)

Stai implementando il piano **`plan-fxTestingCleanup.prompt.md`** — l'ultimo step della **Phase 5 (FX Management)**. La Phase 5 ha implementato l'intero sistema di gestione tassi di cambio (21 sub-plan, 7 round di bug-fix, ~50+ componenti Svelte). Adesso serve:

1. **Cleanup** — Rimuovere dead code, spostare componenti, aggiungere `data-testid`
2. **Bug fix** — 2 bug noti (FxPairSignal, MeasureSignal annualizedPct)
3. **Unit test** — Vitest per `TimeSeriesStore` e `EditBuffer`
4. **i18n audit** — Pulizia chiavi orfane, hardcoded → i18n
5. **Test E2E** — ~70 test Playwright per tutte le pagine FX
6. **Integrazione `dev.py`** — Registrare i nuovi test nel CLI
7. **Gallery** — Screenshot FX per la documentazione
8. **Cleanup doc** — Aggiornare TODO_Completati.md, TODO_FUTURI.md

---

## Il piano dettagliato

**LEGGI SUBITO** il file:
```
LibreFolio_developer_journal/RoadmapV4_UI/plan-fxTestingCleanup.prompt.md
```
Contiene ~730 righe con ogni singolo step, i file da creare/modificare/eliminare, le tabelle dei test case, e l'ordine di esecuzione. Seguilo alla lettera.

### Ordine di esecuzione (dal piano)

```
Pre-Step 0A-0F → Step 1 → Step 2 → Step 3-9 → Step 10 → Step 11 → Step 12
```

### Cosa è già stato fatto (19 Mar 2026)

- ✅ **Step 12A**: 14 plan file spostati in `phases/phase-05-subplan/`
- ✅ **Step 12B**: `phase-05-fx.md` riscritto come summary
- ✅ **Step 12C** (parziale): Nota aggiunta nel piano per TODO_Completati.md

**Tutto il resto è da fare**, partendo da Pre-Step 0A.

---

## Struttura del progetto (file chiave)

### Frontend — Pagine FX

| File | Descrizione |
|------|-------------|
| `frontend/src/routes/(app)/fx/+page.svelte` | FX list page (~1400+ righe) |
| `frontend/src/routes/(app)/fx/[pair]/+page.svelte` | FX detail page (~1400+ righe) |
| `frontend/src/routes/(app)/fx/[pair]/+page.ts` | Load function per detail |

### Frontend — Componenti FX

| File | Descrizione |
|------|-------------|
| `frontend/src/lib/components/fx/FxCard.svelte` | Card singola coppia nella list |
| `frontend/src/lib/components/fx/FxDataEditorSection.svelte` | Sezione data editor nella detail |
| `frontend/src/lib/components/fx/FxPairAddModal.svelte` | Modale aggiunta/modifica coppia |
| `frontend/src/lib/components/fx/FxSyncModal.svelte` | Modale sync tassi |
| `frontend/src/lib/components/fx/FxProviderConfig.svelte` | Config provider per coppia |
| `frontend/src/lib/components/fx/CsvEditor.svelte` | Editor CSV generico (**da spostare** in `ui/data-editor/`) |
| `frontend/src/lib/components/fx/FxEditSection.svelte` | **Dead code** — da eliminare |
| `frontend/src/lib/components/fx/index.ts` | Barrel exports |

### Frontend — Chart & Signals

| File | Descrizione |
|------|-------------|
| `frontend/src/lib/components/charts/MeasurePanel.svelte` | Pannello misure — **bug `annualizedPct`** |
| `frontend/src/lib/components/charts/ChartSettingsModal.svelte` | Settings chart |
| `frontend/src/lib/components/charts/ChartAestheticsSection.svelte` | Aesthetics |
| `frontend/src/lib/components/charts/ChartSignalsSection.svelte` | Configurazione segnali |
| `frontend/src/lib/charts/signals/MeasureSignal.ts` | **Bug**: `getMeasurementForSignal()` non calcola `annualizedPct` |
| `frontend/src/lib/charts/signals/FxPairSignal.ts` | FxPairSignal — **bug**: manca `_resolvedData` nella detail page |
| `frontend/src/lib/charts/signals/ChartSignal.ts` | Classe base segnali |

### Frontend — Stores

| File | Descrizione |
|------|-------------|
| `frontend/src/lib/stores/TimeSeriesStore.ts` | Cache time-series con gap detection — **unit test da scrivere** |
| `frontend/src/lib/stores/EditBuffer.ts` | Buffer editing con undo — **unit test da scrivere** |
| `frontend/src/lib/stores/fxStoreRegistry.ts` | Registry `getFxStore()` |

### Frontend — Data Editor (UI condiviso)

| File | Descrizione |
|------|-------------|
| `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` | Editor dati generico |
| `frontend/src/lib/components/ui/data-editor/DataImportModal.svelte` | Modale import CSV |
| `frontend/src/lib/components/ui/data-editor/DataEditorTypes.ts` | Tipi condivisi |

### Test E2E — Esistenti (pattern da seguire)

| File | Descrizione |
|------|-------------|
| `frontend/e2e/brokers.spec.ts` | **Esempio pattern** — login + navigateTo + testid |
| `frontend/e2e/broker-sharing.spec.ts` | Esempio con `_ensure_db_populated()` |
| `frontend/e2e/fx-routes.spec.ts` | **Obsoleto** — da eliminare, ma contiene helper utili da recuperare |
| `frontend/e2e/fixtures/auth-helpers.ts` | `login()`, `navigateTo()`, `setLanguage()` |
| `frontend/e2e/fixtures/db-helpers.ts` | `resetDatabase()`, `populateDatabase()` |
| `frontend/e2e/fixtures/test-users.ts` | `TEST_USER` credentials |
| `frontend/e2e/gallery.spec.ts` | Gallery screenshot — aggiungere sezione FX |

### Backend — API FX

| File | Descrizione |
|------|-------------|
| `backend/app/api/v1/fx.py` | Endpoint API FX |
| `backend/app/schemas/fx.py` | Schemi Pydantic per FX |

### Dev CLI

| File | Descrizione |
|------|-------------|
| `scripts/test_runner.py` | Registry test — aggiungere `fx-*` entries |
| `dev.py` | Entry point CLI |

### Documentazione

| File | Descrizione |
|------|-------------|
| `TODO_FUTURI.md` | Todo — rimuovere voce i18n cleanup |
| `TODO_Completati.md` | Completati — aggiungere voce i18n cleanup |
| `frontend/scripts/i18n-audit.py` | Tool audit i18n — migliorare regex |
| `mkdocs_src/docs/gallery/desktop.md` | Gallery desktop — aggiungere sezione FX |
| `mkdocs_src/docs/gallery/mobile.md` | Gallery mobile — aggiungere sezione FX |

---

## Pattern e convenzioni

### Pattern test E2E

```typescript
import {expect, test} from '@playwright/test';
import {login, navigateTo} from './fixtures/auth-helpers';   // NB: path relativo dalla cartella e2e/fx/
import {TEST_USER} from './fixtures/test-users';

test.describe('FX ...', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('test name', async ({page}) => {
        await navigateTo(page, '/fx');
        await expect(page.getByTestId('fx-page')).toBeVisible();
    });
});
```

**Nota import per file in `e2e/fx/`**: i fixture sono in `e2e/fixtures/`, quindi gli import dai file in `e2e/fx/` saranno `'../fixtures/auth-helpers'`.

### Pattern `data-testid`

```svelte
<div data-testid="fx-detail-page">...</div>
```

### Pattern test_runner.py

```python
def front_fx_list(verbose=False, ui=False, headed=False, debug=False, test_names=None) -> bool:
    """Run FX list page E2E tests."""
    if not _ensure_db_populated():
        return False
    return _run_playwright("fx/fx-list.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names)
```

Registrare in `TEST_REGISTRY["front"]`:
```python
"fx-list": {"func": front_fx_list, "test_names": True, "name": "FX List Page", ...},
```

### Svelte 5 runes

Il progetto usa Svelte 5 con runes. **NON usare** `$:`, `let:`, `export let`. Usare:
- `let x = $state(...)` per stato reattivo
- `let y = $derived(...)` o `$derived.by(() => ...)` per valori derivati
- `$effect(() => ...)` per side effects
- `$props()` per props dei componenti

### Comandi utili

```bash
./dev.py front check        # svelte-check (type-check)
./dev.py front build        # Build produzione
./dev.py front dev          # Dev server
./dev.py test front auth    # Test E2E auth
./dev.py i18n audit         # Audit chiavi i18n
./dev.py i18n remove KEY    # Rimuovi chiave i18n
./dev.py i18n add KEY       # Aggiungi chiave i18n
```

---

## Direttive operative

1. **Segui il piano alla lettera**: ogni step ha file specifici, test case numerati, e verifiche da fare. Non inventare step extra.

2. **Ordine rigoroso**: Pre-Step 0A-0F **prima** di qualsiasi test. I test E2E dipendono dai `data-testid` (0C) e dai fix bug (0E, 0F).

3. **Verifica dopo ogni step**: esegui `./dev.py front check` dopo ogni modifica frontend. Zero errori richiesti.

4. **Test incrementali**: scrivi i test per uno step, eseguili, fixali, poi passa allo step successivo. Non scrivere tutti i test in blocco.

5. **Recupera helper da `fx-routes.spec.ts`**: le funzioni `goToFxPage()`, `selectCurrency()`, `openAddPairModal()` sono valide e riusabili. Adattale (path import) e mettile in un helper locale `e2e/fx/fx-helpers.ts` o inline.

6. **i18n**: quando trovi stringhe hardcoded, usa `$t('chiave')`. Aggiungi la chiave nei 4 file JSON (en, it, fr, es) in `frontend/src/lib/i18n/`.

7. **Commit logici**: ogni Pre-Step (0A, 0B, ...) e ogni Step (1, 2, ...) è un'unità di lavoro autonoma.

8. **Gallery**: segui il pattern esistente in `gallery.spec.ts`. Ogni screenshot ha 4 lingue × 2 temi = 8 varianti.

---

## Primo step da eseguire

Inizia da **Pre-Step 0A**: eliminare `FxEditSection.svelte` e aggiornare `index.ts`. Poi procedi in ordine.

Quando inizi, leggi i file indicati nel piano prima di modificarli. Se un file ha cambiamenti non previsti dal piano, segnalalo e adattati.

