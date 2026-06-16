# Plan: Gallery Screenshot Update (Phase 07+08+09)

> **Obiettivo**: Aggiornare `gallery.spec.ts` per coprire tutte le funzionalità sviluppate nelle fasi 07 (Transazioni + Import Wizard), 08 (Scheduler) e 09 (Dashboard), e aggiornare di conseguenza i file Markdown della documentazione MkDocs.
>
> **Riferimento**: Derivato da `implementation_plan.md` (agente 262e42ad).

---

## File coinvolti

| File | Azione |
|------|--------|
| `frontend/e2e/gallery.spec.ts` | MODIFY — aggiunta nuovi `test.describe` |
| `mkdocs_src/docs/gallery/desktop.en.md` | MODIFY — nuove sezioni |
| `mkdocs_src/docs/gallery/desktop.it.md` | MODIFY — nuove sezioni (IT) | Tradotto in seguito
| `mkdocs_src/docs/gallery/desktop.fr.md` | MODIFY — nuove sezioni (FR) | Tradotto in seguito
| `mkdocs_src/docs/gallery/desktop.es.md` | MODIFY — nuove sezioni (ES) | Tradotto in seguito
| `mkdocs_src/docs/gallery/mobile.en.md` | MODIFY — nuove sezioni |
| `mkdocs_src/docs/gallery/mobile.it.md` | MODIFY — nuove sezioni (IT) | Tradotto in seguito
| `mkdocs_src/docs/gallery/mobile.fr.md` | MODIFY — nuove sezioni (FR) | Tradotto in seguito
| `mkdocs_src/docs/gallery/mobile.es.md` | MODIFY — nuove sezioni (ES) | Tradotto in seguito

---

## Risultati analisi del codice (Mock Data)

> **✅ Q1 — Mock Data Transazioni — RISOLTO**
> Il `populate_mock_data.py` crea già tutti i dati necessari:
>
> | Scenario | Tag / Descrizione | Note |
> |----------|-------------------|------|
> | **Promote/Merge** | tag `promote-test` | Withdrawal+Deposit su Coinbase/IB (cash transfer) e due ADJUSTMENT opposti su AAPL IB↔Directa |
> | **Linked TRANSFER** | `"Transfer AAPL IB ↔ DEGIRO"` | `related_transaction_id` bidirezionale — usabile per `BulkDeleteLinkedPairModal` |
> | **Linked FX_CONVERSION** | `FX_CONVERSION` pair su IB | EUR↔USD con `related_transaction_id` — usabile per `BulkDeleteLinkedPairModal` |
> | **Split** | tag `suggest-discover` | Coppie standalone (loaded+hidden) pensate per il flusso di abbinamento parziale |
>
> **Nessuna modifica a `populate_mock_data.py` necessaria per Q1.**

> **⚠️ Q2 — Dashboard Empty State — DA FARE**
> L'utente `e2e_test_empty` **non esiste** nel mock DB. Il modo più semplice e stabile è la **opzione B**:
> aggiungere in `populate_mock_data.py` un utente senza broker né transazioni, usato esclusivamente dal test gallery.
>
> **Modifica da pianificare**: aggiungere alla funzione di creazione utenti:
> ```python
> ("e2e_test_empty", "empty@test.example.com", "E2eEmptyPass123!", False),
> ```
> …e **non** assegnargli alcun broker/accesso. Il test gallery farà login con questo utente per fotografare l'empty state.

---

## Parte 1 — gallery.spec.ts

### Ordine di esecuzione degli screenshot

L'ordine di sviluppo (aggiunta dei test) è:
1. Transactions Core & Modals
2. Import Wizard (4 step)
3. Scheduler Settings
4. Dashboard (multi-scroll + empty)
5. Files (file preview)
6. Assets (create wizard + metadata AAPL)

> **Nota**: L'ordine visivo nella documentazione MkDocs segue il menu laterale dell'app (Dashboard prima), non l'ordine di sviluppo dei test.

---

### BLOCCO 1 — Transactions Core & Modals

Da aggiungere come nuovo `test.describe('Transactions', ...)` DOPO il blocco `Files`.

**Prerequisiti Playwright**:
- Login come `TEST_ADMIN` (ha OWNER su tutti i broker → vede tutto)
- Navigazione a `/transactions`
- DB mock già popolato con ricco dataset (BUY, SELL, DIVIDEND, TRANSFER, FX_CONVERSION, ecc.)

#### 1.1 — `transactions/list`
```typescript
// Navigare a /transactions
// waitForLoadState('networkidle')
// freezeAnimations
// screenshot → category: 'transactions', name: 'list'
```

#### 1.2 — `transactions/form-modal`
```typescript
// Aprire form tramite data-testid del pulsante "Add"
// Attendere che il form sia visibile
// waitForNetworkSettled (carica asset, broker)
// screenshot → name: 'form-modal'
// Chiudere con Escape
```

#### 1.3 — `transactions/picker-modal`
```typescript
// Aprire una transazione esistente in edit
// Cliccare il selettore di accoppiamento (se presente come data-testid)
// screenshot → name: 'picker-modal'
// Chiudere con Escape
```

#### 1.4 — `transactions/action-modal` (Split confirm)
```typescript
// Filtrare per tag 'suggest-discover' (o cercare nel testo)
// Trovare una TX con tag 'suggest-discover-loaded' nella tabella
// Aprire il TransactionPickerModal, cercare la TX partner 'suggest-discover-hidden'
// Quando le quantità non coincidono → la UI proporrà lo split → TransactionActionModal aperta
// screenshot → name: 'action-modal'
// Chiudere con Escape
```

#### 1.5 — `transactions/promote-merge-modal`
```typescript
// Le TX tag 'promote-test' sono standalone (non linkate)
// Filtro per descrizione '[promote-test]' o tag 'promote-test'
// Aprire una TX (es. il Withdrawal) e usare l'azione "Promuovi/Unisci"
// → PromoteMergeModal mostra le due TX candidate
// screenshot → name: 'promote-merge-modal'
// Chiudere con Escape
```

#### 1.6 — `transactions/bulk-delete-pair-modal`
```typescript
// Le TX con related_transaction_id già settato sono:
//   - TRANSFER AAPL: IB ↔ DEGIRO (tag 'rebalance', desc 'Transfer AAPL IB ↔ DEGIRO')
//   - TRANSFER BTC: Coinbase ↔ IB (tag 'rebalance', desc 'Transfer BTC Coinbase ↔ IB')
//   - FX_CONVERSION pair su IB
// Trovarne una nella tabella (filtrare per tipo 'TRANSFER' o tag 'rebalance')
// Cliccare delete → BulkDeleteLinkedPairModal rileva il partner e mostra opzioni
// screenshot → name: 'bulk-delete-pair-modal'
// Chiudere con Escape senza confermare
```

---

### BLOCCO 2 — Import Wizard (4 Step)

Da aggiungere come `test.describe` separato DENTRO al blocco `Brokers` esistente, DOPO il test `import-modal` (che sarà eventualmente deprecato in favore del wizard).

**File di test da usare**: 
- Happy path (step 1→2→3): il file IBKR già usato nei test E2E esistenti
- Step 4 (resolution): `generic_simple.csv` (contiene ticker non riconosciuti → fake_id)

**Prerequisiti**:
- Il wizard si apre dalla pagina `/transactions` con pulsante "Import" o dalla pagina broker detail

#### 2.1 — `brokers/import-wizard-step1`
```typescript
// Navigare alla pagina /transactions
// Aprire l'ImportWizardModal (via data-testid del pulsante import)
// Attendere step 1 visibile
// screenshot → name: 'import-wizard-step1'
// NON chiudere, continuare al passo successivo
```

#### 2.2 — `brokers/import-wizard-step2`
```typescript
// Caricare il file IBKR via page.setInputFiles(locator, filePath)
// Cliccare "Avanti" per andare allo step 2
// Attendere che la griglia file-plugin sia visibile
// screenshot → name: 'import-wizard-step2'
```

#### 2.3 — `brokers/import-wizard-step4-resolution`
```typescript
// Caricare generic_simple.csv
// Avanzare fino allo step 4
// Attendere che le card "unresolved" siano visibili
// screenshot → name: 'import-wizard-step4-resolution'
```

#### 2.4 — `brokers/import-wizard-duplicate`
```typescript
// Importare il file IBKR UNA PRIMA VOLTA (setup)
// Riaprire il wizard e ricaricare lo stesso file
// Allo step 4 i badge "likely duplicate" saranno presenti
// screenshot → name: 'import-wizard-duplicate'
```

#### 2.5 — `brokers/import-compare-modal`
```typescript
// Dopo il double import sopra, click sul badge ⚠️ di una riga duplicata
// Attendere l'apertura della ParseDetailModal / compare view
// screenshot → name: 'import-compare-modal'
// Chiudere
```

#### 2.6 — `brokers/import-bulk-staging`
```typescript
// Dopo risoluzione asset (o usando file senza fake_id)
// Cliccare "Import" per aprire TransactionBulkModal (staging)
// Attendere che la grid delle pending ops sia visibile
// screenshot → name: 'import-bulk-staging'
// Chiudere senza salvare
```

---

### BLOCCO 3 — Settings: Scheduler

Da aggiungere DENTRO al blocco `Settings` esistente, dopo il test `global-settings`.

**Prerequisiti**: Login come `TEST_ADMIN` (già gestito da `beforeEach` del blocco Settings)

#### 3.1 — `settings/scheduler-config`
```typescript
// Navigare a /settings
// Cliccare tab admin
// Attendere che global-settings-tab sia visibile e spinner sparito
// Trovare il pulsante di apertura Scheduler Config Modal (data-testid)
// Cliccare → attendere che la modale sia visibile
// screenshot → name: 'scheduler-config'
// Chiudere con Escape
```

#### 3.2 — `settings/scheduler-log`
```typescript
// Stessa navigazione (o riutilizzare stato di 3.1)
// Trovare il pulsante "Log" / "Storico esecuzioni" (data-testid)
// Cliccare → attendere che la modale sia visibile
// screenshot → name: 'scheduler-log'
// Chiudere con Escape
```

---

### BLOCCO 4 — Dashboard Multi-scroll + Empty State

Aggiungere dentro `test.describe('Dashboard')` esistente.

#### 4.1 — `dashboard/allocation-charts`
```typescript
// Navigare a /dashboard
// waitForLoadState + freezeAnimations
// Scrollare fino ai grafici di allocazione (sector/geography)
// waitForNetworkSettled (ECharts può ritardare)
// screenshot → name: 'allocation-charts'
// Scroll back to top per non interferire col test successivo
```

#### 4.2 — `dashboard/empty-state`
```typescript
// Login con TEST_EMPTY = { username: 'e2e_test_empty', password: 'E2eEmptyPass123!' }
// (utente da creare in populate_mock_data.py — nessun broker, nessuna TX)
// Navigare a /dashboard
// waitForLoadState + freezeAnimations
// screenshot → name: 'empty-state'
// ⚠️ Aggiungere TEST_EMPTY a frontend/e2e/fixtures/test-users.ts
```

---

### BLOCCO 5 — Files: File Preview Modal

Da aggiungere dentro `test.describe('Files')` esistente.

#### 5.1 — `files/preview-modal`
```typescript
// Navigare a /files?tab=brim
// Trovare il primo file caricato nella lista (data-testid)
// Cliccare su "Preview" o icona di anteprima
// Attendere FilePreviewModal visibile
// screenshot → name: 'preview-modal'
// Chiudere con Escape
```

---

### BLOCCO 6 — Assets: Wizard Create + Metadata AAPL

Da aggiungere dentro `test.describe('Assets')` esistente.

#### 6.1 — `assets/create-wizard-modal`
```typescript
// Navigare alla lista asset
// Aprire create modal (data-testid del pulsante +)
// Aspettare che il form sia visibile
// Aprire sezione "Ulteriori info" se collapsata
// screenshot → name: 'create-wizard-modal'
// Chiudere con Escape
```

#### 6.2 — `assets/detail-metadata`
```typescript
// Usare navigateToAssetByName(page, 'Apple') [helper esistente]
// waitForLoadState + freezeAnimations
// Scrollare fino alla sezione "Classification / Metadata"
// (mappa geografica + distribuzione settori)
// waitForNetworkSettled
// screenshot → name: 'detail-metadata'
```

---

## Parte 2 — Aggiornamento Markdown Gallery

Dopo aver generato gli screenshot, aggiornare i file Markdown. Le modifiche sono identiche per tutti i file `desktop.{lang}.md` e `mobile.{lang}.md` (cambia solo la lingua del testo descrittivo).

> **Ordine visivo nei file Markdown**: segue il menu laterale dell'app:
> Auth → Dashboard → Transactions → Brokers (+ Import Wizard) → FX → Assets → Files → Media → Settings

---

### 2.1 — Sezione Dashboard (espandere quella esistente)

**Posizione**: Dopo `### 📈 Main Dashboard` (linea ~42 in desktop.en.md)

Aggiungere:

```markdown
### 📊 Allocation & Composition

Asset allocation broken down by sector, currency, and geography — with interactive donut charts.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="allocation-charts" alt="Dashboard Allocation Charts">
</div>

### 🌱 Empty State (New Portfolio)

A clean onboarding state — shown to new users before any data is entered.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="empty-state" alt="Dashboard Empty State">
</div>
```

---

### 2.2 — Nuova sezione Transactions (NUOVA)

**Posizione**: Inserire dopo il blocco `## 📊 Dashboard` e PRIMA di `## ⚙️ Settings` (rispettando l'ordine del menu dell'app).

```markdown
---

## 📒 Transactions

### 📋 Transaction List

All your recorded financial operations in a filterable, sortable table view.

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="list" alt="Transaction List">
</div>

### ➕ Add / Edit Transaction

Record a new operation — buy, sell, dividend, fee — with asset lookup and automatic sign handling.

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal" alt="Transaction Form Modal">
</div>

### 🔗 Transaction Picker

Search and link an existing transaction to create paired operations (e.g. FX trades, transfers).

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="picker-modal" alt="Transaction Picker Modal">
</div>

### ✂️ Split Confirm

When linking transactions with mismatched quantities, the system proposes a split — previewing the result before confirming.

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="action-modal" alt="Transaction Split Modal">
</div>

### 🔀 Merge / Promote

Merge related operations (e.g. two partial fills of the same order) into a single consolidated transaction.

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="promote-merge-modal" alt="Promote Merge Modal">
</div>

### 🗑️ Delete Linked Pair

When deleting a transaction that is part of a linked pair (FX trade, transfer), you can choose to remove just one leg or both.

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="bulk-delete-pair-modal" alt="Bulk Delete Linked Pair Modal">
</div>
```

---

### 2.3 — Sezione Brokers: Import Wizard (sostituire / espandere)

**Posizione**: Dentro `## 🏦 Brokers`, DOPO `### 📥 Import Modal` (che sarà mantenuto per backward compat).

```markdown
### 🧙 Import Wizard — Step 1: Upload

Select one or more broker export files and assign the target broker account.

<div class="screenshot-container">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Import Wizard Step 1">
</div>

### ⚙️ Import Wizard — Step 2: Parser Config

Assign the correct parser plugin to each uploaded file. The system auto-suggests the best match.

<div class="screenshot-container">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Import Wizard Step 2">
</div>

### 🔍 Import Wizard — Step 4: Asset Resolution

Unknown assets (not yet in your database) are shown as cards. Search, create, or skip each one before importing.

<div class="screenshot-container">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Import Wizard Asset Resolution">
</div>

### ⚠️ Duplicate Detection

Transactions already present in the database are automatically flagged. Duplicates are deselected by default.

<div class="screenshot-container">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Import Wizard Duplicate Detection">
</div>

### 🔎 Compare View

Click the warning badge on a flagged row to compare the incoming transaction side-by-side with the existing one.

<div class="screenshot-container">
    <img class="gallery-img" data-category="brokers" data-name="import-compare-modal" alt="Import Compare Modal">
</div>

### 📦 Bulk Staging

Before committing to the database, review all selected transactions in the staging grid. Edit, reorder, or remove before saving.

<div class="screenshot-container">
    <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Import Bulk Staging">
</div>
```

---

### 2.4 — Sezione Settings: Scheduler (aggiungere)

**Posizione**: Dentro `## ⚙️ Settings`, DOPO `### 🛡️ Global Settings (Admin)`.

```markdown
### 🕐 Market Data Scheduler — Config

Configure the automatic market data sync daemon: update frequency, history sync times, and active days.

<div class="screenshot-container">
    <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Scheduler Config Modal">
</div>

### 📜 Market Data Scheduler — Log

View the history of scheduler executions, with duration, status, and per-asset details.

<div class="screenshot-container">
    <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Scheduler Log Modal">
</div>
```

---

### 2.5 — Sezione Files: Preview (aggiungere)

**Posizione**: Dentro `## 📁 Files`, DOPO `### 📋 Broker Reports (BRIM)`.

```markdown
### 👁️ File Preview

Preview the raw content of a broker report file (CSV, XLSX) directly in the browser before parsing.

<div class="screenshot-container">
    <img class="gallery-img" data-category="files" data-name="preview-modal" alt="File Preview Modal">
</div>
```

---

### 2.6 — Sezione Assets: Create Wizard + Metadata (aggiungere)

**Posizione**: Dentro `## 💼 Assets`, DOPO `### ➕ Create Asset Modal` e dopo `### 🗂️ Classification`.

```markdown
### 🧙 Create Asset (from Import Wizard)

When resolving an unknown asset during import, the creation form opens pre-filled with the extracted name, type, and identifiers.

<div class="screenshot-container">
    <img class="gallery-img" data-category="assets" data-name="create-wizard-modal" alt="Create Asset from Wizard">
</div>

### 🌍 Metadata & Geography

For assets with rich metadata (e.g. Apple Inc.), explore geographic distribution and sector breakdown on an interactive world map.

<div class="screenshot-container">
    <img class="gallery-img" data-category="assets" data-name="detail-metadata" alt="Asset Metadata & Geography">
</div>
```

---

## Checklist Esecuzione

### Parte 1 — gallery.spec.ts

- [ ] **Setup Q1**: Verificare/arricchire mock data in `populate_mock_data.py` per transazioni linkate
- [ ] **Setup Q2**: Decidere approccio empty state (utente dedicato vs al volo)
- [ ] **1.1** Aggiungere blocco `Transactions` → test `list`
- [ ] **1.2** Aggiungere test `form-modal`
- [ ] **1.3** Aggiungere test `picker-modal`
- [ ] **1.4** Aggiungere test `action-modal` (Split)
- [ ] **1.5** Aggiungere test `promote-merge-modal`
- [ ] **1.6** Aggiungere test `bulk-delete-pair-modal`
- [ ] **2.1** Aggiungere test `import-wizard-step1`
- [ ] **2.2** Aggiungere test `import-wizard-step2`
- [ ] **2.3** Aggiungere test `import-wizard-step4-resolution`
- [ ] **2.4** Aggiungere test `import-wizard-duplicate`
- [ ] **2.5** Aggiungere test `import-compare-modal`
- [ ] **2.6** Aggiungere test `import-bulk-staging`
- [ ] **3.1** Aggiungere test `scheduler-config` nel blocco Settings
- [ ] **3.2** Aggiungere test `scheduler-log` nel blocco Settings
- [ ] **4.1** Aggiungere test `allocation-charts` nel blocco Dashboard
- [ ] **4.2** Aggiungere test `empty-state` nel blocco Dashboard
- [ ] **5.1** Aggiungere test `preview-modal` nel blocco Files
- [ ] **6.1** Aggiungere test `create-wizard-modal` nel blocco Assets
- [ ] **6.2** Aggiungere test `detail-metadata` nel blocco Assets
- [ ] **Eseguire**: `./dev.py mkdocs gallery` e verificare tutti i PNG generati

### Parte 2 — Markdown Gallery

- [ ] **2.1** Espandere sezione Dashboard (EN, IT, FR, ES per desktop + mobile)
- [ ] **2.2** Aggiungere sezione Transactions (EN, IT, FR, ES per desktop + mobile)
- [ ] **2.3** Espandere sezione Brokers con Import Wizard (EN, IT, FR, ES per desktop + mobile)
- [ ] **2.4** Aggiungere Scheduler in Settings (EN, IT, FR, ES per desktop + mobile)
- [ ] **2.5** Aggiungere File Preview in Files (EN, IT, FR, ES per desktop + mobile)
- [ ] **2.6** Aggiungere Create Wizard + Metadata in Assets (EN, IT, FR, ES per desktop + mobile)
- [ ] **Rieseguire** `./dev.py mkdocs gallery` e verificare pagine HTML generate correttamente
