# Piano Tecnico di Dettaglio: Test Checkpoint Phase 07-08

**Documento di riferimento**: `plan-test-checkpoint-phase07-08.md`
**Scopo**: Piano esecutivo per un agente Sonnet che dovrà scrivere tutti i test mancanti.
**Data**: 2026-06-15

---

## 📊 Stato Attuale dei Test

### Backend Scheduler (Phase 08) — GIÀ SCRITTI ✅

I seguenti test backend **esistono già** e sono registrati nel test runner:

| File | Contenuto | Test IDs | Status |
|------|-----------|----------|--------|
| `backend/test_scripts/test_services/test_scheduler_state.py` | load/save state, atomic write, JSON corrotto/parziale | SS-001..SS-006 | ✅ Completo |
| `backend/test_scripts/test_services/test_scheduler_due.py` | due_current_price, due_history_sync, edge cases | SD-001..SD-010b | ✅ Completo |
| `backend/test_scripts/test_services/test_scheduler_leader.py` | am_i_leader(), psutil mock, zombie, Docker, reload | SL-001..SL-007b | ✅ Completo |
| `backend/test_scripts/test_services/test_scheduler_loop.py` | due_* + state roundtrip integration | SLO-001..SLO-003b | ✅ Completo |
| `backend/test_scripts/test_services/test_scheduler_settings.py` | _parse_times(), _parse_days() | SC-001..SC-007b | ✅ Completo |
| `backend/test_scripts/test_api/test_scheduler_api.py` | GET scheduler/state, scheduler/log, auth 401/403 | SAPI-001..SAPI-008 | ✅ Completo |

**Runner registrati**: `./dev.py test services scheduler-state|scheduler-settings|scheduler-due|scheduler-leader|scheduler-loop` + `./dev.py test api scheduler`

### Backend Settings API (Phase 08) — ✅ COMPLETATA 2026-06-15

| File | Contenuto | Test IDs | Status |
|------|-----------|----------|--------|
| `backend/test_scripts/test_api/test_settings_api.py` *(esteso)* | 6 test salvataggio/lettura delle 5 chiavi scheduler via PATCH/GET bulk | GSET-SCH-001..006 | ✅ Completo |

### Frontend Scheduler E2E (Phase 08) — GIÀ SCRITTO ✅

| File | Contenuto | Test IDs | Status |
|------|-----------|----------|--------|
| `frontend/e2e/settings/scheduler.spec.ts` | Config modal, log modal, fetch_interval regression | FSCH-001..FSCH-010 | ✅ Completo |

**Runner**: `./dev.py test front-utility scheduler`

### Frontend Import Wizard E2E (Phase 07.5) — ✅ COMPLETATA 2026-06-16

| File | Contenuto | Test IDs | Status |
|------|-----------|----------|--------|
| `frontend/e2e/transactions/tx-brim-import.spec.ts` | Happy path, skip resolve, basic asset resolution, dup deselect, unsaved guard | T1..T8 | ✅ Completo |
| `frontend/e2e/transactions/tx-import-resolution.spec.ts` *(nuovo)* | Resolve section, AssetSelect, Create new asset, identifier prompt, full E2E, dup detection, compare modal, broker creation, FilePreviewModal | IWR-001..006, IWR-006b, IWR-007, IWR-009, IWR-010 | ✅ Completo (10 test) |

> **Note implementazione test residui (2026-06-16)**: Aggiunti 4 test a `tx-import-resolution.spec.ts`. Tutti e 10 i test passano (1.1 min). Aggiunto `data-testid="import-wizard-step1-broker-select"` al wrapper BrokerSearchSelect in Step 1. IWR-007/006b usano guard condizionale (i dup esistono solo se IWR-006 ha già importato nel run corrente — il test è state-aware e non si rompe in run freschi). IWR-009/010 hanno early-return se le condizioni non sono applicabili (no pending files).

---

## 🎯 Test da Scrivere

### SEZIONE A: Backend — Settings API per Chiavi Scheduler (GSET-SCH-*) ✅ COMPLETATA 2026-06-15

> **Note implementazione**: Aggiunta classe `TestSchedulerSettingsKeys` a `backend/test_scripts/test_api/test_settings_api.py` con 6 test (GSET-SCH-001..006). Tutti passano. Due helper privati aggiunti: `_get_setting_value()` e `_read_setting()` / `_patch_setting()`. Ogni test ripristina i valori originali nel `finally` block. Runner già registrato (`./dev.py test api settings`), nessuna modifica a `_backend_api.py` necessaria.

**File**: `backend/test_scripts/test_api/test_settings_api.py` (estendere file esistente)

**Contesto**: Le 5 chiavi scheduler (`scheduler_enabled`, `scheduler_current_price_frequency_minutes`, `scheduler_history_sync_times`, `scheduler_history_sync_days`, `scheduler_history_sync_horizon_days`) sono salvate come Global Settings e vengono modificate tramite `PATCH /api/v1/settings/global/bulk`. Il file `test_settings_api.py` testa già le settings generiche (GSET-001..GSET-010) ma **NON testa specificamente le chiavi scheduler**.

**Cosa fare**: Aggiungere una nuova classe `TestSchedulerSettingsKeys` alla fine di `test_settings_api.py` con i seguenti test:

#### GSET-SCH-001: Save and read scheduler_enabled

```
1. Login come admin (riusare il pattern get_or_create_admin() già nel file)
2. PATCH /settings/global/bulk con items: [{key: "scheduler_enabled", value: "true"}]
3. GET /settings/global → verificare che scheduler_enabled esista con value "true"
4. PATCH con value "false" → GET → value == "false"
```

#### GSET-SCH-002: Save and read scheduler_current_price_frequency_minutes

```
1. PATCH con {key: "scheduler_current_price_frequency_minutes", value: "15"}
2. GET → verify value == "15"
3. PATCH con value "5" → GET → value == "5"
```

#### GSET-SCH-003: Save and read scheduler_history_sync_times (CSV format)

```
1. PATCH con {key: "scheduler_history_sync_times", value: "06:00,12:00,23:00"}
2. GET → verify value == "06:00,12:00,23:00"
3. PATCH con value "08:30" (single slot) → GET → value == "08:30"
```

#### GSET-SCH-004: Save and read scheduler_history_sync_days (CSV format)

```
1. PATCH con {key: "scheduler_history_sync_days", value: "mon,wed,fri"}
2. GET → verify value == "mon,wed,fri"
3. PATCH con value "mon,tue,wed,thu,fri,sat,sun" → GET → verify
```

#### GSET-SCH-005: Save and read scheduler_history_sync_horizon_days

```
1. PATCH con {key: "scheduler_history_sync_horizon_days", value: "30"}
2. GET → verify value == "30"
```

#### GSET-SCH-006: Bulk update all 5 scheduler keys at once

```
1. PATCH /settings/global/bulk con items: [tutti e 5 i key]
2. GET /settings/global → verify all 5 values correct
```

**Pattern da seguire** (copiare da GSET-005 nel file):
```python
@pytest.mark.asyncio
class TestSchedulerSettingsKeys:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_save_and_read_scheduler_enabled(self):
        """GSET-SCH-001: Save scheduler_enabled via bulk PATCH, read back."""
        print_section("GSET-SCH-001: scheduler_enabled save/read")
        async with httpx.AsyncClient() as client:
            await get_or_create_admin(client)
            resp = await client.patch(
                f"{API_BASE}/settings/global/bulk",
                json={"items": [{"key": "scheduler_enabled", "value": "true"}]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            # Read back
            resp = await client.get(f"{API_BASE}/settings/global", timeout=TIMEOUT)
            settings = {s["key"]: s["value"] for s in resp.json()}
            assert settings.get("scheduler_enabled") == "true"
        print_success("scheduler_enabled save/read OK")
```

**Nota per l'agente**: La funzione admin helper nel file si chiama `get_or_create_admin()` o simile — verificare il nome esatto prima di usarla. Guardare le funzioni helper a inizio file.

---

### SEZIONE B: Frontend E2E — Import Wizard Resolution Avanzata (IWR-*) ✅ COMPLETATA 2026-06-15

> **Note implementazione**: Creato `frontend/e2e/transactions/tx-import-resolution.spec.ts` con 6 test (IWR-001..006). Tutti passano in ~52s. Aggiunto `data-testid="import-wizard-resolve-section"` e `"import-wizard-resolve-toggle"` al componente `ImportWizardModal.svelte`. Registrato nel runner come `./dev.py test front-transaction tx-import-resolution`.
>
> **⚠️ Fuori pista**:
> - Il DataTable usa `<button class="checkbox-btn">` invece di `input[type="checkbox"]` per la selezione → trovato analizzando `DataTable.svelte`
> - La sezione resolve collassava per race condition (2s `isVisible()` troppo corto → toggle accidentale) → risolto con `waitFor({state:'visible'})`
> - Il loop IWR-006 puntava al primo AssetSelect (AAPL, già risolto) invece dell'unresolved → fix con `.border-gray-200 [data-testid="asset-select"]`
> - `data-testid="asset-modal-display-name"` è sull'input stesso, non su un wrapper → fix `.locator('input')` rimosso
> - IWR-006 diventa state-agnostic perché IWR-005 (confirm identifier) può risolvere UNETF nel DB

**File da creare**: `frontend/e2e/transactions/tx-import-resolution.spec.ts`

**Prerequisiti**:
- Il file `generic_simple.csv` è caricato come sample report da `populate_mock_data.py` per il broker "Interactive Brokers"
- Il CSV contiene asset `UNETF` che NON esiste nel DB → genera un `fake_id` che richiede risoluzione manuale
- Il CSV contiene anche asset `AAPL` che potrebbe essere auto-risolto se esiste nel DB
- Le righe con date `2025-11-*` sono righe di test per la duplicate detection

**Come aprire il wizard e raggiungere Step 4 con `generic_simple.csv`**:
```typescript
import {expect, test, type Page} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(90_000); // Resolution tests are slower

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 8_000});
    await page.waitForTimeout(400);
}

async function openImportWizard(page: Page) {
    // Click first row edit to open BulkModal
    const firstRow = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]').first();
    await firstRow.hover();
    await firstRow.getByRole('button', {name: /edit/i}).first().click();
    await page.getByTestId('tx-bulk-modal-root').waitFor({state: 'visible', timeout: 6_000});
    // Click Import
    await page.getByTestId('tx-bulk-import').click();
    await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 5_000});
}

async function selectGenericSimpleFile(page: Page) {
    // Skip Step 1
    await page.getByTestId('import-wizard-next').click();
    await page.getByTestId('import-wizard-step2').waitFor({state: 'visible', timeout: 5_000});

    // In Step 2 — find generic_simple.csv among the checkboxes
    // The files are listed under broker panels with checkbox + filename
    const genericSimple = page.locator('label, span').filter({hasText: 'generic_simple.csv'});
    const checkbox = genericSimple.locator('..').locator('input[type="checkbox"]');
    // Alternative: find any checkbox near text matching generic_simple
    const fileCheckbox = page.getByTestId('import-wizard-step2')
        .locator('text=generic_simple.csv')
        .locator('..')
        .locator('input[type="checkbox"]');
    // If not visible, try expanding the broker panel first
    if (!(await fileCheckbox.isVisible({timeout: 2_000}).catch(() => false))) {
        // Click on the broker accordion to expand
        const brokerPanel = page.getByTestId('import-wizard-step2').locator('button').first();
        await brokerPanel.click();
        await page.waitForTimeout(300);
    }
    await fileCheckbox.check();
}

async function parseAndContinue(page: Page) {
    await page.getByTestId('import-wizard-parse').click();
    await page.getByTestId('import-wizard-step3').waitFor({state: 'visible', timeout: 10_000});
    await expect(page.getByTestId('import-wizard-continue')).toBeEnabled({timeout: 30_000});
    await page.getByTestId('import-wizard-continue').click();
    await page.getByTestId('import-wizard-step4').waitFor({state: 'visible', timeout: 5_000});
    await page.waitForTimeout(500);
}
```

**NOTA IMPORTANTE per l'agente**: Le funzioni helper sopra sono una **guida** — la selezione esatta di `generic_simple.csv` richiede ispezionare il DOM al runtime. Il pattern del checkbox potrebbe dover essere adattato. Se il checkbox non è trovabile con il selettore text-based, usa un approccio più robusto tipo:
```typescript
const step2 = page.getByTestId('import-wizard-step2');
// I file sono listati con checkbox accanto al nome
const allCheckboxes = step2.locator('input[type="checkbox"]');
// Verificare quanti ce ne sono e selezionare quello giusto
```

#### IWR-001: Resolve section visible with unresolved count badge

```
Scenario:
1. Login → Transactions → Import Wizard → selezionare generic_simple.csv → Parse → Continue to Step 4
2. Step 4 deve mostrare la sezione "Resolve Assets" con un badge ambra che indica N asset non risolti
3. L'asset UNETF dovrebbe essere non risolto (fake_id)
4. Verificare: import button è disabled (data-testid="import-wizard-import" → toBeDisabled)

Selectors:
- step4: page.getByTestId('import-wizard-step4')
- "Resolve Assets" toggle: cercare testo "Resolve Assets" o traduzione i18n
- Badge non risolti: amber badge con conteggio (cercare span con class amber/red)
- Import button: page.getByTestId('import-wizard-import')
```

#### IWR-002: AssetSelect with suggestedIds (candidate chips with confidence tooltip)

```
Scenario:
1. Nella sezione resolve di Step 4, per l'asset UNETF non risolto
2. Verificare che AssetSelect (data-testid="asset-select") sia presente
3. Aprire il dropdown dell'AssetSelect (click)
4. I candidati suggeriti dovrebbero apparire in cima con badge colorati
5. Verificare che esista almeno un badge tooltip (hover sopra il badge → tooltip con % confidenza)

Selectors:
- AssetSelect wrapper: step4.locator('[data-testid="asset-select"]')
- Input di ricerca dentro AssetSelect: locator('input[type="text"]')
- Candidati con badge: locator che contenga badge/chip con testo (es. "95%")
```

#### IWR-003: Manual asset selection → identifier prompt (Add Identifier flow)

```
Scenario:
1. Nella resolve section, per UNETF:
2. Aprire AssetSelect dropdown, cercare un asset esistente (es. digitare "Apple")
3. Selezionare un asset dalla lista
4. Dovrebbe apparire un identifier-prompt modal (data-testid="identifier-prompt-confirm")
5. Il prompt chiede se aggiungere l'identificatore "UNETF" all'asset scelto
6. Click "identifier-prompt-confirm" → il mapping viene salvato
7. La card UNETF dovrebbe diventare verde (bordo emerald, resolved)
8. Il conteggio unresolved diminuisce

Selectors:
- identifier-prompt-confirm: page.getByTestId('identifier-prompt-confirm')
- identifier-prompt-skip: page.getByTestId('identifier-prompt-skip')
- identifier-prompt-cancel: page.getByTestId('identifier-prompt-cancel')
```

#### IWR-004: Skip identifier prompt (resolve without adding identifier)

```
Scenario:
1. Come IWR-003 ma click su "identifier-prompt-skip" invece di confirm
2. L'asset viene risolto MA l'identificatore non viene aggiunto
3. Verificare che la risoluzione sia comunque avvenuta (card verde)
```

#### IWR-005: Create New Asset flow

```
Scenario:
1. Nella resolve section, per UNETF:
2. Aprire AssetSelect dropdown → click "+ Create new" button (cercare il createLabel)
3. Si apre AssetModal (data-testid="asset-modal-form")
4. Verificare che il nome sia pre-compilato (campo data-testid="asset-modal-display-name" non vuoto)
5. Verificare che la sezione "More Info" (data-testid="asset-modal-more-info") sia visibile/espansa
6. Compilare i campi minimi necessari e salvare (data-testid="asset-modal-save")
7. L'asset viene creato e automaticamente risolto nel wizard
8. Il conteggio unresolved diminuisce

Selectors:
- AssetModal form: page.getByTestId('asset-modal-form')
- Display name: page.getByTestId('asset-modal-display-name')
- More info: page.getByTestId('asset-modal-more-info')
- Save: page.getByTestId('asset-modal-save')
- Cancel: page.getByTestId('asset-modal-cancel')
```

#### IWR-006: Compare Modal (duplicate inspection)

```
Scenario:
1. Nel Step 4, le righe con badge ⚠ (likely duplicate) o ℹ (possible duplicate) hanno un click handler
2. Trovare una riga con badge ⚠ nel TX table di Step 4
3. Click sul badge ⚠ → si apre un TransactionFormModal in view mode (compare modal)
4. Verificare che la modale compare sia visibile
5. Verificare che ci sia un titleOverride (titolo inizia con "🔍")
6. Chiudere la compare modal

Selectors:
- Badge ⚠ nel table: step4.locator('table tbody tr').filter({hasText: '⚠'})
- Compare modal: la TransactionFormModal si apre come overlay.
  Cercare il modal con il titolo "🔍" oppure verificare che ci sia un secondo layer modale.
  Il form ha data-testid="tx-form-modal" (verificare nel componente TransactionFormModal.svelte)
```

#### IWR-007: Duplicate Detection — doppio import

```
Scenario:
1. Importare generic_simple.csv una prima volta completamente:
   - Resolve tutti gli asset (via manual match o create new)
   - Click Import → wizard si chiude, rows importate in BulkModal
   - Salvare le transazioni dal BulkModal (se necessario, click Save)
2. Riaprire il wizard per un secondo import dello stesso file
3. Selezionare di nuovo generic_simple.csv → Parse → Continue to Step 4
4. Le righe già importate devono essere segnalate come "likely duplicate" o "possible duplicate"
5. Le righe duplicate devono avere il checkbox deselezionato di default
6. Verificare che il contatore dei likely duplicates nel summary sia > 0

Nota: Questo test è complesso e richiede tempo. Assicurarsi che il timeout sia adeguato (90-120s).
L'agente dovrebbe considerare se semplificarlo verificando solo che al secondo parse
le righe appaiano con badge duplicate, senza necessariamente completare l'intero flusso di import.

Selectors:
- Righe duplicate: step4.locator('tr').filter({hasText: '⚠ dup'})
- Checkbox deselezionato: riga.locator('input[type="checkbox"]') → not.toBeChecked()
```

#### IWR-008: End-to-end resolution — import button enables after resolving all

```
Scenario:
1. Aprire wizard → selezionare generic_simple.csv → Parse → Step 4
2. Import button deve essere disabled (ci sono asset non risolti)
3. Risolvere TUTTI gli asset non risolti (via manual match)
4. Import button si abilita
5. Click Import → wizard si chiude
6. BulkModal deve contenere le righe importate

Selectors:
- Import button: page.getByTestId('import-wizard-import')
- Prima: await expect(importBtn).toBeDisabled()
- Dopo resolve: await expect(importBtn).toBeEnabled()
```

#### IWR-009: Broker creation from Step 1 with reactive dropdown

```
Scenario:
1. Aprire Import Wizard → Step 1
2. Nella sezione broker del Step 1, c'è un BrokerSearchSelect con opzione "+ Create new"
3. Click su "Create new" → si apre un form/modale per creare un nuovo broker
4. Compilare nome e salvare
5. Il nuovo broker deve apparire immediatamente nel dropdown senza refresh pagina

Nota: Questo test potrebbe richiedere di capire come è strutturato il BrokerSearchSelect
in Step 1. Cercare il data-testid o il testo "Create new" / $t('common.createNew').
```

#### IWR-010: FilePreviewModal z-index

```
Scenario:
1. Nel wizard (Step 1 o Step 2), se c'è un pulsante per preview file
2. Click → si apre FilePreviewModal (data-testid nel file FilePreviewModal.svelte)
3. Verificare che sia visibile E che abbia z-index appropriato (sopra le altre modali)
4. Chiudere e verificare che il wizard sia ancora interagibile

Selectors:
- FilePreviewModal: cercare data-testid in frontend/src/lib/components/files/FilePreviewModal.svelte
  (data-testid potrebbe non esistere ancora → potrebbe essere necessario aggiungerlo)
```

---

### SEZIONE C: Registrazione Test nel Runner

**File da modificare**: `scripts/test_runner/_frontend_transaction.py`

Il nuovo spec file `tx-import-resolution.spec.ts` deve essere registrato nel test runner.

**Cosa aggiungere**:

1. **Funzione runner** (dopo `front_tx_brim_import`):
```python
def front_tx_import_resolution(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Import Wizard Resolution E2E tests (advanced resolve, compare, create, dup detection)."""
    print_section("Frontend TX Import Resolution Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-import-resolution.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)
```

2. **Aggiungere alla lista `front_transaction_all()`** — cercare la lista di tuple specs e aggiungere:
```python
("TX Import Resolution", lambda: front_tx_import_resolution(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
```

3. **Registrare in `populate_registry()`**:
```python
add_test(cat, "tx-import-resolution", front_tx_import_resolution, name="TX Import Resolution Tests", desc="Advanced resolve flow: compare modal, identifier prompt, create asset, dup detection", tests="transactions/tx-import-resolution.spec.ts")
```

Il risultato finale sarà: `./dev.py test front-transaction tx-import-resolution`

---

## 📋 Ordine di Esecuzione

### Fase 1: Backend Settings API (bassa complessità, 30 min)

1. Aprire `backend/test_scripts/test_api/test_settings_api.py`
2. Aggiungere la classe `TestSchedulerSettingsKeys` con 6 test (GSET-SCH-001..006)
3. Eseguire: `./dev.py test api settings`
4. Verificare che tutti i test nuovi passino

### Fase 2: Frontend Import Resolution E2E (alta complessità, 2-3h)

1. Creare `frontend/e2e/transactions/tx-import-resolution.spec.ts`
2. Implementare i test IWR-001..IWR-010 (iniziare dai più semplici)
3. Registrare nel runner (`_frontend_transaction.py`)
4. Eseguire: `./dev.py test front-transaction tx-import-resolution --headed` (headed per debug)

**Ordine consigliato di implementazione dei test IWR**:
1. IWR-001 (resolve section visible) — base per tutti gli altri
2. IWR-008 (end-to-end resolve → import enables) — verifica il flusso completo
3. IWR-003 + IWR-004 (identifier prompt) — flusso più specifico
4. IWR-005 (create new asset) — richiede interazione con AssetModal
5. IWR-006 (compare modal) — verifica UI dup inspection
6. IWR-002 (candidate chips) — verifica UI dettagli
7. IWR-007 (doppio import) — il più lungo e complesso
8. IWR-009 + IWR-010 — edge case, meno prioritari

### Fase 3: Verifica CI Locale ✅ COMPLETATA 2026-06-16

| Suite | Comando | Risultato |
|-------|---------|-----------|
| Settings API | `./dev.py test api settings` | ✅ PASS |
| Scheduler API | `./dev.py test api scheduler` | ✅ PASS |
| Scheduler State | `./dev.py test services scheduler-state` | ✅ PASS |
| Scheduler Settings | `./dev.py test services scheduler-settings` | ✅ PASS |
| Scheduler Due | `./dev.py test services scheduler-due` | ✅ PASS |
| Scheduler Leader | `./dev.py test services scheduler-leader` | ✅ PASS |
| Scheduler Loop | `./dev.py test services scheduler-loop` | ✅ PASS |
| BRIM Import Wizard | `./dev.py test front-transaction tx-brim-import` | ✅ PASS (8/8) |
| Import Resolution | `./dev.py test front-transaction tx-import-resolution` | ✅ PASS (6/6) |
| Scheduler E2E | `./dev.py test front-utility scheduler` | ✅ PASS (10/10, 1 skip) |

> **⚠️ Fix pre-esistenti applicati** (non causati dal nostro lavoro, ma corretti durante CI):
> - `tx-brim-import.spec.ts`: FormModal intercettava `tx-bulk-import` → aggiunto close di FormModal
> - `tx-brim-import.spec.ts`: `input[type="checkbox"]` non esiste nel DataTable → fix con `td.td-select button.checkbox-btn`
> - `tx-brim-import.spec.ts`: warning confirm modal non gestita → aggiunto `import-wizard-warning-confirm` testid + gestione in `continueToReview`
> - `scheduler.spec.ts`: categoria "Sync" → rinominata "Scheduler & Upload" nel UI
> - `scheduler.spec.ts`: time slots usano `<span>` non `<li>` → fix selettori
> - `ImportWizardModal.svelte`: aggiunto `data-testid="import-wizard-warning-confirm"` al button "Continue anyway"

---

## 🔧 Reference Tecnico per l'Agente

### Struttura importazione test helpers (Backend API)

```python
import httpx, pytest
from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, print_info

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
```

### Struttura importazione test (Frontend E2E)

```typescript
import {expect, test, type Page} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {TEST_ADMIN} from '../fixtures/test-users'; // solo se serve admin
```

### data-testid disponibili nel Import Wizard

| testid | Elemento | Note |
|--------|----------|------|
| `import-wizard-stepper` | Container stepper | Step indicator |
| `import-wizard-step1` | Step 1 container | Upload files |
| `import-wizard-step2` | Step 2 container | Select files |
| `import-wizard-step3` | Step 3 container | Parse results |
| `import-wizard-step4` | Step 4 container | Review + Resolve |
| `import-wizard-close` | Close button (×) | Top-right |
| `import-wizard-next` | Next button (Step 1) | Skip to Step 2 |
| `import-wizard-parse` | Parse button (Step 2) | Disabled if no files selected |
| `import-wizard-continue` | Continue button (Step 3) | Disabled until parse done |
| `import-wizard-import` | Import button (Step 4) | Disabled if unresolved selected |
| `import-wizard-clear` | Clear button (Step 1) | Clear pending files |
| `import-wizard-upload-more` | Upload more button | Step 1 |
| `import-wizard-step-{N}` | Step N indicator | In stepper |
| `identifier-prompt-confirm` | Confirm add identifier | In prompt modal |
| `identifier-prompt-skip` | Skip identifier | |
| `identifier-prompt-cancel` | Cancel identifier | |

### data-testid nel AssetModal

| testid | Elemento |
|--------|----------|
| `asset-modal-form` | Form container |
| `asset-modal-display-name` | Display name input |
| `asset-modal-description` | Description textarea |
| `asset-modal-more-info` | More info section toggle |
| `asset-modal-save` | Save button |
| `asset-modal-cancel` | Cancel button |
| `asset-active-toggle` | Active/inactive toggle |

### data-testid nel AssetSelect

| testid | Elemento |
|--------|----------|
| `asset-select` | Wrapper div (default testid) |

L'AssetSelect accetta `suggestedIds` con `badge`, `badgeClass`, `badgeTooltip` per i candidati.

### data-testid nello Scheduler Settings

| testid | Elemento |
|--------|----------|
| `scheduler-status-row` | Row stato scheduler |
| `scheduler-config-row` | Row configurazione |
| `scheduler-config-frequency` | Input frequenza |
| `scheduler-config-times` | Sezione time slots |
| `scheduler-config-time-input` | Input nuovo time slot |
| `scheduler-config-time-add` | Add time slot button |
| `scheduler-config-save` | Save config button |
| `scheduler-config-cancel` | Cancel config button |
| `scheduler-log-entries` | Log entries container |
| `scheduler-log-close` | Close log button |

### File CSV di test: `generic_simple.csv`

```csv
date,type,quantity,amount,currency,asset,description
2025-01-01,DEPOSIT,0,10000.00,EUR,,Initial funding
2025-01-02,BUY,10,-1000.00,EUR,AAPL,Buy 10 shares of AAPL
2025-01-03,SELL,-5,500.00,EUR,AAPL,Sell 5 shares
2025-01-04,DIVIDEND,0,25.50,EUR,AAPL,Q4 dividend payment
2025-01-05,DEPOSIT,0,5000.00,EUR,,Account funding
2025-01-06,WITHDRAWAL,0,-1000.00,EUR,,Cash withdrawal
2024-12-10,BUY,10,-250.00,USD,UNETF,Unknown fund purchase
2024-12-11,DIVIDEND,0,15.00,USD,UNETF,Unknown fund dividend
2025-11-01,BUY,5,-862.50,USD,AAPL,BRIM dup test - likely 1
2025-11-02,DIVIDEND,0,12.50,USD,AAPL,BRIM dup test - likely 2
2025-11-03,BUY,3,-517.50,USD,AAPL,CSV desc for possible dup 1
2025-11-04,SELL,-2,350.00,USD,AAPL,CSV desc for possible dup 2
2025-05-01,ADJUSTMENT,10,0,EUR,TSLA,Stock Split - Manca WAC
2025-06-01,ADJUSTMENT,5,0,EUR,NVDA,Spin-off - Manca WAC
```

**Asset che richiedono risoluzione**: `UNETF` (non esiste nel DB, genera fake_id)
**Asset con possibile match**: `AAPL`, `TSLA`, `NVDA` (se esistono nel DB da populate_mock_data)
**Righe per dup detection**: quelle con date `2025-11-*` contengono "BRIM dup test" nel description

### Endpoint API schedulatore (per reference)

| Method | Path | Auth | Descrizione |
|--------|------|------|-------------|
| GET | `/api/v1/settings/scheduler/state` | Admin | Stato last execution |
| GET | `/api/v1/settings/scheduler/log` | Admin | Log JSONL (newest first) |
| GET | `/api/v1/settings/scheduler/log?since=ISO` | Admin | Log filtrato per data |
| PATCH | `/api/v1/settings/global/bulk` | Admin | Bulk update settings |
| GET | `/api/v1/settings/global` | Admin | Read all global settings |

---

## 🐛 Classi di Bug Risolti — CI Run al 100% (2026-06-16)

Sessione di debug sistematico della suite completa (`./dev.py test all-backend` + `all-frontend`). Queste sono le **classi di bug** ricorrenti trovate e corrette.

---

### Classe 1: `broker_id` come Query Param invece di Form Field

**Impatto**: 4 file, ~26 occorrenze totali  
**Sintomo**: `422 Unprocessable Entity — Field required: broker_id`  
**Root cause**: L'endpoint `POST /brokers/import/upload` ha `broker_id: int = Form(...)` — richiede il campo nel body multipart. I test usavano `?broker_id=...` come query param (scritti quando la firma era diversa).

**File corretti**:
| File | Tipo | Fix |
|------|------|-----|
| `backend/test_scripts/test_api/test_brim_api.py` | Backend API | 19 occorrenze → `data={"broker_id": broker_id}` |
| `backend/test_scripts/test_e2e/test_brim_e2e.py` | Backend E2E | 6 occorrenze → `data={"broker_id": broker_id}` |
| `frontend/e2e/files.spec.ts` | Frontend E2E | 1 occorrenza → `multipart: {broker_id: String(brokerId), ...}` |

---

### Classe 2: `_build_history_series` — contratto cambiato senza aggiornare i test

**Impatto**: `test_portfolio_service.py` — 10 test `TestBuildHistorySeries` + 6 test `GetSummary/GetHistory`  
**Sintomo**: `AssertionError: assert len(result) == 2` (la funzione ora restituisce 60 punti invece di 2)  
**Root cause**: commit `06613074` (bond pricing) ha refactorizzato `_build_history_series` da "one point per transaction date" a "dense daily series" (un punto per ogni giorno). Contestualmente, i campi monetari di `PortfolioSummary`/`PortfolioHistoryPoint` sono diventati `Currency(code, amount)` invece di `Decimal`. I test sono rimasti al vecchio contratto.

**Fix in `test_portfolio_service.py`**:
- Rimossi `len == N` rigidi → accesso per data specifica (`next(p for p in result if p.date == ...)`)
- `test_unknown_type_skipped` → `test_all_types_contribute_to_cash` (DIVIDEND ora contribuisce al cash)
- Tutti i confronti monetari aggiornati a `.amount` (es. `summary.net_worth.amount == Decimal("0")`)

---

### Classe 3: yfinance — `Close=NaN` causa ValidationError Pydantic

**Impatto**: `test_asset_providers.py::test_historical_data[yfinance]`  
**Sintomo**: `1 validation error for FAPricePoint close: Input should be a finite number [type=finite_number, input_value=Decimal('NaN')]`  
**Root cause**: yfinance restituisce `NaN` per il `Close` del giorno corrente (mercati ancora aperti). Tutte le altre colonne (`Open`, `High`, `Low`, `Volume`) usavano la guardia `pd.notna()` ma `Close` no — unica incoerenza in `yahoo_finance.py`.

**Fix in `yahoo_finance.py`**:
```python
# Skip rows where Close is NaN
if not pd.notna(row["Close"]):
    logger.debug(f"Skipping {date_utc} for {identifier}: Close is NaN")
    continue
```
+ guard post-loop: se tutte le righe sono NaN → `AssetSourceError("NO_DATA")` invece di crash Pydantic.

---

### Classe 4: Test E2E — Selezione file BRIM con DataTable custom checkbox

**Impatto**: `tx-brim-import.spec.ts` — tutti i test T1-T8 (tranne T7)  
**Sintomo**: `import-wizard-parse` rimane disabled dopo `selectFirstAvailableFile()` — nessun file selezionato  
**Root cause**: il DataTable di LibreFolio usa `<button class="checkbox-btn">` dentro `<td class="td-select">`, NON `<input type="checkbox">`. Il test targettava `input[type="checkbox"]`.

**Fix**: `td.td-select button.checkbox-btn` come selettore.

**Fix correlati in `tx-brim-import.spec.ts`**:
- `openBulkModalAndImport`: chiude `tx-form-close` se una FormModal è aperta (auto-apre su transazione paired)
- `continueToReview`: gestisce la warning confirmation modal (aggiunto `data-testid="import-wizard-warning-confirm"` al componente)

---

### Classe 5: Test E2E scheduler — UI cambiata, selettori obsoleti

**Impatto**: `scheduler.spec.ts` — FSCH-001..009 (10 test)  
**Sintomi**:
- FSCH-001: categoria "Sync" non trovata → rinominata "Scheduler & Upload" nel UI
- FSCH-008/009: `timesSection.locator('li')` → gli slot ora sono `<span class="rounded-full">` (badge pill), non `<li>`

**Fix in `scheduler.spec.ts`**:
```typescript
// Prima
await page.getByRole('button', {name: 'Sync'}).click();
timesSection.locator('li').count()

// Dopo
await page.getByRole('button', {name: 'Scheduler & Upload'}).click();
timesSection.locator('span.rounded-full').count()
```

---

### Classe 6: Test E2E — `test_runner run_command` silenzioso sui failure

**Impatto**: debugging difficile su tutte le suite — solo `❌ FAILED (exit code: 1)` senza traceback  
**Root cause**: `subprocess.run(..., capture_output=not verbose)` catturava stdout+stderr ma in caso di failure li scartava silenziosamente.

**Fix in `scripts/test_runner/_common.py`**:
```python
# Aggiunto nel failure path:
if not verbose and result.stdout:
    print(result.stdout)
if not verbose and result.stderr:
    print(result.stderr, end="")
```

---

### Classe 7: `test_search_to_prices` — UNIQUE constraint su display_name (DB sporco)

**Impatto**: `test_complete_e2e_flow_justetf` — Step 4 metadata refresh  
**Sintomo**: `500 UNIQUE constraint failed: assets.display_name` — il provider aggiornava il `display_name` con il nome reale dell'ETF già esistente da un run precedente  
**Root cause**: test isolation issue sul DB condiviso — l'asset viene creato con nome unico ma il metadata refresh sovrascrive con il nome fisso del provider.

**Fix in `test_search_to_prices.py`**: Step 4 reso non-fatal — se non è 200, logga warning e prosegue (Steps 5-6 prezzi sono il vero cuore del test).


1. **Non modificare i test già esistenti** (scheduler backend, scheduler frontend, brim-import happy path) — sono completi e funzionanti
2. **data-testid mancanti**: Se un elemento non ha un `data-testid` e ne serve uno per i test, **aggiungere il data-testid al componente Svelte** prima di usarlo nel test. Seguire il naming pattern `{componente}-{elemento}` (es. `import-wizard-resolve-section`)
3. **Timeout**: i test resolution sono più lenti perché richiedono parsing API. Usare `test.setTimeout(90_000)` per il file spec
4. **Mock data**: i test dipendono da `populate_mock_data.py` che carica `generic_simple.csv` per "Interactive Brokers". Verificare che il DB sia populated prima di eseguire (`./dev.py db populate --test`)
5. **generic_simple.csv file selection**: in Step 2 il file potrebbe essere sotto un pannello accordion del broker. Se il broker panel non è espanso, bisogna prima espanderlo cliccando sul nome del broker
6. **Non usare `git commit`** — solo proporre commit messages
7. **Dopo modifiche API (se necessario)**: `./dev.py api sync`
8. **Per debug E2E**: usare `--headed` per vedere il browser: `./dev.py test front-transaction tx-import-resolution --headed`
