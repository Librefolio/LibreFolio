# Phase 4: Brokers Management

**Status**: 🔄 IN PROGRESS  
**Durata**: 3 giorni  
**Priorità**: P0 (MVP)
**Dipendenze**: Phase 3

---

## Obiettivo

Implementare la gestione completa dei broker: lista, creazione, modifica, e vista dettaglio con cash balances.

---

## ⚠️ Riferimento Phase 9

Se vengono creati componenti riutilizzabili, seguire le linee guida in [Phase 9: Polish](./phase-09-polish.md) e aggiornare quella fase con i dettagli del componente.

**Componenti previsti per questa fase**:

- `BrokerCard.svelte` - Card display broker ✅
- `Modal.svelte` - Se non già esistente in Phase 9
- `CurrencySelect.svelte` → `FuzzySelect.svelte` ✅ (riutilizzabile)

---

## 4.1 Brokers List (1 giorno)

### Tasks

- [x] Creare `src/routes/(app)/brokers/+page.svelte`
- [x] Creare `src/routes/(app)/brokers/+page.ts` (load function)
- [x] Creare `src/lib/components/brokers/BrokerCard.svelte`
- [x] Implementare button "Add Broker"

### Miglioramenti Implementati (14-01-2026)

- [x] BrokerCard cliccabile ovunque (navigazione al dettaglio)
- [x] Hover animation sulla card
- [x] Icona broker (custom o favicon da portal_url)
- [x] Rimosso pulsante "occhio" (ridondante)
- [x] Nuovi campi DB: `icon_url`, `default_import_plugin`
- [x] Toggle per "Conto Attivo" invece di checkbox
- [x] Data apertura default = oggi
- [x] Checkbox trading in layout verticale con tooltip condizionali
- [x] Label aggiornate: "Consenti Acquisto con Leva", "Consenti Vendita allo Scoperto (Short)"
- [x] Initial balances: ordine invertito (amount, currency), dropdown verso l'alto
- [x] Prima valuta suggerita = default currency dell'utente
- [x] Conferma se si chiude modal con modifiche non salvate

### Load Function

```typescript
// src/routes/(app)/brokers/+page.ts
import {api} from '$lib/api';

export async function load() {
    const brokers = await api.get('/brokers');
    return {brokers};
}
```

### Broker Card Component

```svelte
<!-- BrokerCard.svelte -->
<div class="broker-card bg-white rounded-lg shadow p-4">
  <div class="header flex justify-between">
    <h3 class="font-bold">{broker.name}</h3>
    <div class="actions">
      <button on:click={() => goto(`/brokers/${broker.id}`)}>View</button>
      <button on:click={() => editBroker(broker)}>Edit</button>
      <button on:click={() => deleteBroker(broker.id)}>Delete</button>
    </div>
  </div>
  
  <p class="description text-gray-600">{broker.description}</p>
  
  {#if broker.portal_url}
    <a href={broker.portal_url} target="_blank" class="portal-link">
      Portal ↗
    </a>
  {/if}
  
  <!-- Cash Balances -->
  <div class="cash-balances mt-4 grid grid-cols-2 gap-2">
    {#each Object.entries(broker.cash_balances) as [currency, amount]}
      <div class="balance-chip flex items-center gap-2">
        <span class="flag">{getCurrencyFlag(currency)}</span>
        <span class="amount">{formatCurrency(amount, currency)}</span>
      </div>
    {/each}
  </div>
</div>
```

### API Endpoints

| Endpoint          | Metodo | Descrizione          |
|-------------------|--------|----------------------|
| `/api/v1/brokers` | GET    | Lista tutti i broker |

### File da Creare

| File                                           | Descrizione         |
|------------------------------------------------|---------------------|
| `src/routes/(app)/brokers/+page.svelte`        | Lista broker        |
| `src/routes/(app)/brokers/+page.ts`            | Load function       |
| `src/lib/components/brokers/BrokerCard.svelte` | Card singolo broker |

---

## 📋 Consolidation & Improvements (20 Gennaio 2026)

### Status Corrente

Dopo il completamento delle features base di Phase 4, sono emerse diverse necessità di refinement e standardizzazione:

#### ✅ Fix Completati (20-01-2026)

1. **Dark Mode**: ✅ **VERIFICATO**
    - Input/Select/Textarea: Solo border `#546175`, background trasparente
    - Tooltip: background `#61666f` ✅
    - **Login page AnimatedBackground**: ✅ **FIXED** - Aggiunto dark mode (`#1e293b` bg, `#1a4031` waves, `#4ade80` chart lines)

2. **Broker Icons**: ✅ **COMPLETO**
    - Reattività BrokerCard migliorata ✅
    - LazyImage bordino bianco rimosso (background transparent) ✅
    - **Portal URL empty string**: ✅ **FIXED**
        - BrokerForm invia `""` in edit mode
        - Schema + service: `""` → `None` in DB
    - **Plugin icon bordino**: ✅ **FIXED** - Rimosso `bg-gray-100` da plugin icon
    - **BrokerIcon component**: ✅ **COMPLETATO**
        - Prova icon_url → portal_url favicon → plugin icon API → Briefcase
        - Carica plugin list da API per ottenere icon_url reale
        - Gestisce stringhe vuote come null (fix finale)
        - Usato in BrokerCard e BrokerForm
        - Reattivo e gestisce errori automaticamente
    - **BrokerIcon sync fallback fix**: ✅ **FIXED** (20-01-2026)
        - Aggiunto `imageKey` + `{#key}` per forzare re-render durante moveToNextFallback()
        - Risolve problema icona plugin non mostrata quando icon_url cancellato
    - **BrokerIcon plugin load timing fix**: ✅ **FIXED** (21-01-2026)
        - Rimossa dipendenza `pluginsLoaded` da `propsKey` per evitare reset icona dopo 1 secondo
        - Ora reset solo quando cambiano i props reali (iconUrl, portalUrl, pluginCode)
        - Plugin icon caricato correttamente senza flashare il fallback

3. **Broker Form**: ✅ **VERIFICATO**
    - GenericCSV ordering: ✅ **FIXED** (code `'broker_generic_csv'`)
    - GenericCSV appare primo con "(default)" label ✅
    - **Form reactive to initialData**: ✅ **FIXED** (21-01-2026)
        - Form fields ora si aggiornano quando `initialData` cambia
        - Risolve problema modale modifica vuota dalla pagina dettaglio broker

4. **Broker Detail Page `/brokers/[id]`**: ✅ **FIXED** (21-01-2026)
    - Usa `BrokerIcon` invece di `LazyImage` per icona header
    - Modal modifica passa tutti i campi in `initialData` (inclusi `icon_url`, `default_import_plugin`, `is_active`, `opened_at`)

5. **Files Page**: ✅ **VERIFICATO**
    - Download con nome originale (`?download=true`) ✅
    - Button "Cancel" → "New File" (tradotto 4 lingue) ✅
    - ImageUploader preview reset corretto ✅

5. **Backend API - Preview Features**: ✅ **IMPLEMENTATO**
    - **Text Preview**: `?offset=0&window=1000` ✅
    - **Image Preview**: `?img_preview=400x400` ✅
        - ⚡ Resize in processo separato con `ProcessPoolExecutor`
        - ⚡ Non blocca server, frontend può fare richieste parallele
    - Pillow dependency installata ✅
    - Error handling per file incompatibili ✅

6. **UI/UX Polish**: ✅ **NUOVO**
    - **Burger menu hover rimosso**: ✅ No più illuminazione in dark mode (Header completamente)
    - **Sidebar logo hover rimosso**: ✅ No più opacity change
    - **Auth redirect fix**: ✅ **FIXED** (21-01-2026)
        - Layout (app) ora usa `$isAuthInitialized` per redirect reattivo
        - Utente non loggato viene rediretto immediatamente a `/` invece di schermo bianco

7. **Developer Tools**: ✅ **NUOVO**
    - **GUIDA-DARK-MODE.md**: ✅ Creata guida per modificare velocemente variabili dark mode

8. **Backend API Fixes**: ✅ **NUOVO** (21-01-2026)
    - **Broker Access Authorization**: 403 invece di 400 per errori di autorizzazione
        - `add_broker_access`, `update_broker_access`, `remove_broker_access`
        - Distingue "Only OWNERs can..." (403) da altri errori (400)
    - **Test deprecation warning fix**:
        - `test_profile_api.py`: cookies su client invece che per-request
        - `test_broker_access_api.py`: aspetta 403 per errori auth
    - **Logging cleanup**: Silenziati log verbose di aiosqlite/sqlalchemy

9. **BrokerIcon & BrokerModal Fixes**: ✅ **NUOVO** (21-01-2026)
    - **BrokerIcon.svelte**: Riorganizzato codice (funzioni prima dei reactive statements)
    - **BrokerForm.svelte**: Form reactive a initialData + bordi arrotondati footer
    - **vite.config.ts**: Aggiunto `base: '/'` per path assoluti (fix MIME type errors)
    - **svelte.config.js**: `fallback: 'index.html'` per SPA routing

10. **dev.py Server Flags**: ✅ **NUOVO** (21-01-2026)
    - `--rebuild, -r`: Forza rebuild frontend
    - `--debug, -d`: Debug mode (LOG_LEVEL=DEBUG + frontend debug build)
    - Supporto `LIBREFOLIO_LOG_LEVEL` env var nel backend

11. **Frontend Debug System**: ✅ **NUOVO** (21-01-2026)
    - File: `frontend/src/lib/debug.ts`
    - Tree-shaking: Codice debug eliminato in production
    - Attivazione: `VITE_DEBUG=true` in build
    - Debug logging aggiunto a: BrokerIcon, AppLayout, AuthStore, API client

12. **ProfileTab Completion**: ✅ **NUOVO** (21-01-2026)
    - Layout uniformato con Save/Undo a destra del campo
    - Edit lock con icona Pencil/PencilOff per prevenire modifiche accidentali
    - Delete Account con conferma (digita username)
    - Backend: DELETE `/auth/users/me` endpoint
    - Backend: `count_superusers()`, `delete_user()` in user_service
    - Test API: `TestDeleteAccount` (3 test)
    - Test Service: `TestCountSuperusers`, `TestDeleteUser` (4 test)
    - i18n: Chiavi per delete account + enable/disable editing (4 lingue)
    - Debug logging aggiunto a ProfileTab, PreferencesTab, GlobalSettingsTab

#### 🎯 Settings Unification Plan - COMPLETATO ✅

**File spostato in**: `phase-04-subplan/plan-settings-unification.md`

#### ⚠️ Issue Rimanenti (Non Bloccanti)

1. **BrokerCard refresh**: Lista non si aggiorna automaticamente dopo edit (serve F5)
    - Workaround: F5 manuale
    - Fix futuro: Key reactive o invalidate dopo update

2. **Delete confirmation**: Alert invece di banner centrato
    - Da implementare in Table Improvements plan

3. **Dark mode contrasto**: ⏳ **ATTESA FEEDBACK UTENTE**
    - Guida creata per modifiche rapide (`GUIDA-DARK-MODE.md`)
    - Utente deve testare e indicare valori CSS ottimali

### 🎯 Piani di Miglioramento Attivi

Sono stati creati diversi piani per affrontare problematiche di standardizzazione e usabilità:

#### 1. Settings Unification Plan

**File**: [`../plan-settings-unification.md`](../plan-settings-unification.md)

**Obiettivo**: Unificare PreferencesTab, GlobalSettingsTab e creare Profile Page con componenti riutilizzabili.

**Componenti da creare**:

- `SettingField.svelte` - Campo singolo con azioni
- `SettingsLayout.svelte` - Layout 2 colonne con sidebar
- `SettingText.svelte` - Text/email con edit inline
- `SettingImageUpload.svelte` - Upload con crop/resize

**Key Decisions**:

- ✅ Stato locale nei componenti (massima flessibilità)
- ✅ Validazione a livello componente quando possibile
- ✅ Profile page: Save globale ATTIVO (esclusi Password e Delete Account che hanno modali separate)

**Stima**: 4-8 giorni

#### 2. Table Improvements Plan ✅ **COMPLETATO (23-01-2026)**

**File**: [`../plan-table-improvements.md`](../plan-table-improvements.md)

**Obiettivo**: Migliorare tabelle Files (Static + BRIM) con sorting, filtering, pagination, e **preview**.

**Libreria scelta**: **TanStack Table v8** (motivazione: licenza MIT + features complete)

**Features implementate**:

- ✅ **Preview API Backend**:
    - Text: `GET /uploads/file/{id}?offset=0&window=1000`
    - Images: `GET /uploads/file/{id}?img_preview=400x400`
    - Error 400 per file incompatibili
- ✅ **DataTable Component Suite**:
    - `DataTable.svelte` - Componente principale generico (941 righe)
    - `DataTablePagination.svelte` - Pagination sticky balloon
    - `DataTableToolbar.svelte` - Bulk actions + column toggle + reorder
    - `DataTableColumnFilter.svelte` - Filtri Excel-style per tipo colonna
    - `ConfirmModal.svelte` - Modale conferma generica
    - `types.ts` - Interfacce TypeScript
- ✅ **Sorting**: Click header per ASC/DESC/none, icone freccia
- ✅ **Filtri colonna**: Text, Enum, Number, Size (logaritmico), Date
- ✅ **Column resize**: Drag con localStorage persistence
- ✅ **Column visibility**: Toggle con Eye/EyeOff
- ✅ **Column reorder**: Drag desktop, bottoni up/down mobile
- ✅ **Row selection**: Checkbox, select all, bulk operations
- ✅ **Pagination**: Sticky bottom, page sizes, infinite mode
- ✅ **FileUploader**: Upload multiplo con validazione client-side
- ✅ **Cleanup**: Rimossi FilesTableAdvanced e tanstack-table/DataTable obsoleti

**Stima originale**: 3-6 giorni | **Effettivo**: ~4 giorni

#### 2.5 BRIM Multi-User Support Plan ✅ **COMPLETED (27-01-2026)**

**File Piano**: [`../plan-brim-multiuser-implementation.md`](../plan-brim-multiuser-implementation.md)  
**File Analisi**: [`../analysis-brim-multiuser.md`](../analysis-brim-multiuser.md)

**Obiettivo**: Rendere il sistema BRIM compatibile con multi-utente e multi-broker.

**Backend ✅ Completato (24-01-2026)**:

- [x] `broker_id` obbligatorio all'upload (file associato al broker)
- [x] `uploaded_by_user_id` per tracciare chi ha caricato
- [x] Filtri per broker accessibili all'utente
- [x] Caching risultato parsing nel metadata JSON
- [x] Nuovo endpoint `GET /files/{id}/last-parse`
- [x] Verifica permessi EDITOR+ per upload/parse/delete
- [x] Sottocartelle broker per organizzazione file
- [x] 22 test API BRIM passati

**Frontend ✅ Completato (27-01-2026)**:

- [x] Colonna "Broker" con nome broker nella tabella Report Broker
- [x] Badge colorato per broker (colori generati algoritmicamente)
- [x] Filtro broker ora usa filtro colonna (rimosso dropdown separato)
- [x] Supporto parametro `broker_ids` come lista di int
- [x] Upload con broker_id obbligatorio
- [x] FileUploader: aggiunto parametro `accept` per tipi file
- [x] **Modale assegnazione broker per-file**:
    - Appare appena si selezionano file (via evento `on:change`)
    - Sezione "Assegna tutti a" per assegnazione batch
    - Lista file con dropdown broker individuale
    - Pulsante "Carica" grigio se non tutti i broker assegnati
    - Dopo upload, broker usati aggiunti automaticamente ai filtri
- [x] Conferma chiusura uploader con file in sospeso (sia static che brim)
- [x] Rimosso stato "processing" non esistente (refuso)
- [x] Traduzioni complete per modale (assignBrokers, assignAll, file, etc.)

**Storage Structure**:

```
broker_reports/
├── uploaded/
│   ├── broker_1/
│   └── broker_2/
├── parsed/
│   └── broker_1/
└── failed/
    └── broker_1/
```

**Stima backend**: 5-8h | **Effettivo backend**: ~6h
**Stima frontend**: 3-5h | **Effettivo frontend**: ~6h

#### 3. Image Crop Plan

**File**: [`../plan-image-crop.md`](../plan-image-crop.md)

**Obiettivo**: Implementare crop avanzato per avatar/icon/cover images.

**Libreria scelta**: **svelte-easy-crop** (leggera ~15KB, nativa Svelte)

**Features**:

- Crop area selection con drag
- Aspect ratio lock (1:1, 16:9, 4:3, free)
- Zoom & pan
- Rotate & flip (opzionali)
- Preview real-time multipli (50x50, 200x200)

**Use cases**:

- Avatar upload (1:1)
- Broker icon (1:1)
- Future cover images (16:9)

**Stima**: 2-4 giorni

#### 4. Bulk Download Plan

**File**: [`../plan-bulk-download-v2.md`](../plan-bulk-download-v2.md)

**Obiettivo**: Download multiplo di file come archivio o singolarmente.

**Features**:

- Download singoli file separati
- Download come archivio (tar, zip, 7z)
- Modal di selezione formato con preview dimensione stimata
- Service comune per creazione archivi (backend)
- Supporto per uploads statici e BRIM files

**Backend**:

- `archive_service.py` - service comune per creazione archivi
- Endpoint POST `/uploads/bulk-download`
- Endpoint POST `/brokers/import/bulk-download`

**Frontend**:

- `BulkDownloadModal.svelte` - modal selezione formato
- Integrazione in FilesTable per selezione multipla

**Stima**: 6-8h

---

### 🗺️ Ordine di Implementazione Suggerito

Basandosi su priorità, dipendenze, e impatto:

1. ~~**🥇 Table Improvements**~~ ✅ **COMPLETATO** (23-01-2026)
    - DataTable component suite implementata
    - Filtri Excel-style, sorting, pagination, column management
    - FileUploader con upload multiplo

2. ~~**🥇 BRIM Multi-User**~~ ✅ **COMPLETATO** (26-01-2026)
    - Backend: broker_id obbligatorio, permessi, caching parse
    - Frontend: colonna broker, filtri, upload con broker_id
    - 22 test API passati

3. **🥈 Image Crop** (2-4 giorni)
    - **Motivazione**: Necessario per Profile page e migliora UX upload
    - **Blocca**: Settings Unification (Profile avatar)
    - **Estensibilità**: Riutilizzabile per broker icons, asset logos, cover images
    - **Status**: 📋 Piano pronto, libreria valutata

4. **🥈 Bulk Download** (6-8h)
    - **Motivazione**: Migliora UX download multiplo
    - **Dipende da**: Niente
    - **Status**: 📋 Piano pronto (plan-bulk-download-v2.md)

5. **🥉 Settings Unification** (4-8 giorni)
    - **Motivazione**: Standardizza UI settings, introduce Profile page
    - **Dipende da**: Image Crop (per avatar upload)
    - **Estensibilità**: Componenti Setting* riutilizzabili per future pagine config
    - **Status**: 📋 Piano dettagliato, decisioni prese

---

### 📊 Timeline Totale Consolidation

**Ottimistico**: 10 giorni  
**Realistico**: 15 giorni  
**Con imprevisti**: 20 giorni

---

### 🔗 Collegamenti ai Documenti

| Documento                                                                         | Descrizione                                 | Status       |
|-----------------------------------------------------------------------------------|---------------------------------------------|--------------|
| [plan-settings-unification.md](phase-04-subplan/plan-settings-unification.md)     | Componenti condivisi Settings + Profile     | 📋 Pronto    |
| [plan-table-improvements.md](phase-04-subplan/plan-table-improvements.md)         | TanStack Table + Preview                    | ✅ Completato |
| [plan-image-crop.md](../plan-image-crop.md)                                       | Advanced crop component                     | 📋 Pronto    |
| [plan-bulk-download-v2.md](../plan-bulk-download-v2.md)                           | Bulk download as archive (zip/tar/7z)       | 📋 Pronto    |
| [plan-brim-multiuser-implementation.md](../plan-brim-multiuser-implementation.md) | BRIM Multi-User                             | ✅ Completato |
| [plan-data-separation.md](../plan-data-separation.md)                             | Data directory prod/test separation         | 📋 Pronto    |
| [plan-types-library.md](phase-04-subplan/plan-types-library.md)                   | TypeScript Types Library + Zodios Migration | ✅ Completato |

---

## 4.2 Add/Edit Broker Modal (1 giorno)

### Tasks

- [ ] Creare `src/lib/components/brokers/AddBrokerModal.svelte`
- [ ] Creare `src/lib/components/brokers/BrokerForm.svelte`
- [ ] Implementare validazione con Zod
- [ ] Implementare initial balances multi-currency

### Form Fields

```svelte
<!-- BrokerForm.svelte -->
<form on:submit|preventDefault={handleSubmit}>
  <!-- Name (required) -->
  <div class="field">
    <label>Name *</label>
    <input type="text" bind:value={name} required minlength="1" maxlength="255" />
  </div>
  
  <!-- Description (optional) -->
  <div class="field">
    <label>Description</label>
    <textarea bind:value={description}></textarea>
  </div>
  
  <!-- Portal URL (optional) -->
  <div class="field">
    <label>Portal URL</label>
    <input type="url" bind:value={portalUrl} placeholder="https://..." />
  </div>
  
  <!-- Initial Balances (multi-currency) -->
  <div class="field">
    <label>Initial Balances</label>
    {#each initialBalances as balance, i}
      <div class="balance-row flex gap-2">
        <select bind:value={balance.currency}>
          {#each currencies as c}
            <option value={c.code}>{c.flag} {c.code}</option>
          {/each}
        </select>
        <input type="number" step="0.01" bind:value={balance.amount} />
        <button type="button" on:click={() => removeBalance(i)}>✕</button>
      </div>
    {/each}
    <button type="button" on:click={addBalance}>+ Add Currency</button>
  </div>
  
  <!-- Flags -->
  <div class="flags flex gap-4">
    <label>
      <input type="checkbox" bind:checked={allowOverdraft} />
      Allow Overdraft
    </label>
    <label>
      <input type="checkbox" bind:checked={allowShorting} />
      Allow Shorting
    </label>
  </div>
  
  <button type="submit">{isEditing ? 'Save' : 'Create'}</button>
</form>
```

### API Endpoints

| Endpoint          | Metodo | Descrizione     |
|-------------------|--------|-----------------|
| `/api/v1/brokers` | POST   | Crea broker     |
| `/api/v1/brokers` | PATCH  | Modifica broker |

### Validazione (Zod)

```typescript
const BrokerSchema = z.object({
    name: z.string().min(1).max(255),
    description: z.string().optional(),
    portal_url: z.string().url().optional().or(z.literal('')),
    initial_balances: z.array(z.object({
        code: z.string().length(3),
        amount: z.number().positive()
    })).optional(),
    allow_overdraft: z.boolean().default(false),
    allow_shorting: z.boolean().default(false)
});
```

### File da Creare

| File                                               | Descrizione         |
|----------------------------------------------------|---------------------|
| `src/lib/components/brokers/AddBrokerModal.svelte` | Modal wrapper       |
| `src/lib/components/brokers/BrokerForm.svelte`     | Form riutilizzabile |

---

## 4.3 Broker Detail Page (1 giorno)

### Tasks

- [ ] Creare `src/routes/(app)/brokers/[id]/+page.svelte`
- [ ] Creare `src/routes/(app)/brokers/[id]/+page.ts`
- [ ] Creare `src/lib/components/brokers/CashBalanceCard.svelte`
- [ ] Creare `src/lib/components/brokers/CashTransactionModal.svelte`
- [ ] Implementare Deposit/Withdraw quick actions

### Load Function

```typescript
// src/routes/(app)/brokers/[id]/+page.ts
export async function load({params}) {
    const broker = await api.get(`/brokers/${params.id}/summary`);
    const transactions = await api.get(`/transactions?broker_id=${params.id}&limit=10`);
    return {broker, transactions};
}
```

### Page Sections

1. **Header**
    - Nome, descrizione, portal link
    - Edit button

2. **Cash Balances**
    - Card per ogni currency
    - Buttons "Deposit" / "Withdraw"

3. **Recent Transactions**
    - Ultime 10 transazioni
    - Link "View All" → `/transactions?broker_id={id}`

### Cash Transaction Modal

```svelte
<!-- CashTransactionModal.svelte -->
<form on:submit|preventDefault={handleSubmit}>
  <h2>{type === 'DEPOSIT' ? 'Deposit' : 'Withdraw'}</h2>
  
  <div class="field">
    <label>Amount</label>
    <input type="number" step="0.01" min="0.01" bind:value={amount} required />
  </div>
  
  <div class="field">
    <label>Currency</label>
    <select bind:value={currency}>
      {#each currencies as c}
        <option value={c.code}>{c.flag} {c.code}</option>
      {/each}
    </select>
  </div>
  
  <div class="field">
    <label>Date</label>
    <input type="date" bind:value={date} />
  </div>
  
  <div class="field">
    <label>Description (optional)</label>
    <textarea bind:value={description}></textarea>
  </div>
  
  <button type="submit">{type === 'DEPOSIT' ? 'Deposit' : 'Withdraw'}</button>
</form>
```

Questo crea una transazione tipo DEPOSIT o WITHDRAWAL via `POST /transactions`.

### API Endpoints

| Endpoint                       | Metodo | Descrizione                         |
|--------------------------------|--------|-------------------------------------|
| `/api/v1/brokers/{id}/summary` | GET    | Dettaglio broker con balances       |
| `/api/v1/transactions`         | GET    | Transazioni filtrate per broker     |
| `/api/v1/transactions`         | POST   | Crea transazione (deposit/withdraw) |

### File da Creare

| File                                                     | Descrizione            |
|----------------------------------------------------------|------------------------|
| `src/routes/(app)/brokers/[id]/+page.svelte`             | Dettaglio broker       |
| `src/routes/(app)/brokers/[id]/+page.ts`                 | Load function          |
| `src/lib/components/brokers/CashBalanceCard.svelte`      | Card balance           |
| `src/lib/components/brokers/CashTransactionModal.svelte` | Modal deposit/withdraw |

---

## Verifica Completamento

### Test Manuali

- [ ] Lista broker visibile (anche se vuota con empty state)
- [ ] Click "Add Broker" → modal aperto
- [ ] Crea broker → appare in lista
- [ ] Edit broker → modifiche salvate
- [ ] Delete broker → rimosso dalla lista
- [ ] Click su broker → dettaglio visibile
- [ ] Deposit cash → balance aggiornato
- [ ] Withdraw cash → balance aggiornato
- [ ] Recent transactions visibili nel dettaglio

---

## Mockup Riferimento

- `/site/POC_UX/brokers/broker_management_*.jpg`
- `/site/POC_UX/brokers/add-edit_broker_modal.jpg`
- `/site/POC_UX/cash/`

---

## Dipendenze

- **Richiede**: Phase 3 (Layout)
- **Sblocca**: Phase 7 (Transactions - richiede broker_id)

---

## 🐛 Bug e Improvements (29 Gennaio 2026)

Problemi minori rilevati durante i test finali della Phase 4.

### Bug da Correggere

| ID      | Priorità | Area     | Descrizione                                                                         | Stima |
|---------|----------|----------|-------------------------------------------------------------------------------------|-------|
| BUG-001 | P2       | Backend  | Broker esistente di altro utente: errore non indica chi è l'owner                   | 15min |
| BUG-002 | P2       | Frontend | BrokerSelect: icona mostra broker sbagliato durante ricerca (problema index)        | 30min |
| BUG-003 | P2       | Frontend | Files page: max upload size mostra sempre "10MB" anche se global setting diverso    | 30min |
| BUG-004 | P3       | i18n     | Francese: "Byte" tradotto con "B" invece di "O" (Octets) - verificare tutte le aree | 30min |
| BUG-005 | P2       | Docs     | MkDocs dark mode: colori non allineati con frontend theme                           | 1h    |

### Improvements da Implementare

| ID      | Priorità | Area     | Descrizione                                                                             | Stima |
|---------|----------|----------|-----------------------------------------------------------------------------------------|-------|
| IMP-001 | P2       | Frontend | Tabella: click su contatore righe selezionate deseleziona tutto (o aggiungere pulsante) | 20min |
| IMP-002 | P2       | Frontend | Risorse statiche: pulsante "Copy Link" per copiare URL risorsa (utile per icone broker) | 30min |
| IMP-003 | P2       | Frontend | Global Settings max file size: aggiungere unità di misura visibile                      | 15min |
| IMP-004 | P2       | Frontend | Global Settings max file size: warning se > 500MB (rischio riempire HDD server)         | 30min |

### Dettagli Tecnici

#### BUG-001: Messaggio errore broker esistente

**File**: `backend/app/services/broker_service.py` (o endpoint create)
**Modifica**: Quando un broker con lo stesso nome esiste già, includere nel messaggio:

- "Broker '{name}' already exists"
- Se possibile: "owned by user '{owner_username}'"

**Status**: ✅ COMPLETATO (29-01-2026) - Aggiunto controllo owner e messaggio personalizzato

#### BUG-002: BrokerSelect icona errata

**File**: `frontend/src/lib/components/brokers/BrokerSelect.svelte`
**Causa probabile**: L'icona viene presa dall'array filtrato usando l'index originale invece del broker filtrato
**Fix**: Usare il broker object diretto invece dell'index (aggiunta key al loop `{#each}`)

**Status**: ✅ COMPLETATO (29-01-2026) - Aggiunta `(broker.id)` come key nel loop filteredBrokers

#### BUG-003: Max upload size hardcoded

**File**: `frontend/src/routes/(app)/files/+page.svelte`
**Modifica**: Leggere il valore da global settings invece di hardcoded "10MB"

**Status**: ✅ COMPLETATO (29-01-2026) - Aggiunta loadGlobalSettings() che legge max_file_upload_mb

#### BUG-004: Traduzione Bytes in Francese

**File**: `frontend/src/lib/i18n/locales/fr.ts` (o json)
**Verifica**: Cercare tutte le occorrenze di "B" per bytes e sostituire con "o" (octets)

- KB → Ko
- MB → Mo
- GB → Go

**Status**: ✅ COMPLETATO (29-01-2026) - formatBytes usa ora $t() per le unità, traduzioni già presenti in fr.json

#### BUG-005: MkDocs dark mode

**File**: `mkdocs_src/docs/stylesheets/extra.css` o theme config
**Modifica**: Allineare palette colori dark mode con frontend:

- Background: simile a `bg-gray-900`
- Text: simile a `text-gray-100`
- Accent: brand green `#1a4031`

**Status**: 🔲 TODO (bassa priorità)

#### IMP-001: Deseleziona tutto

**File**: `frontend/src/lib/components/table/DataTableToolbar.svelte`
**Modifica**: Aggiungere onClick al badge contatore che chiama `table.resetRowSelection()`

**Status**: ✅ COMPLETATO (29-01-2026) - Badge contatore ora cliccabile con X per deselezionare

#### IMP-002: Copy Link per risorse statiche

**File**: `frontend/src/lib/components/files/FilesTable.svelte` (o actions)
**Modifica**: Aggiungere action "Copy Link" che copia URL completo della risorsa
**Uso**: Per ottenere link icona broker da inserire in icon_url

**Status**: ✅ COMPLETATO (29-01-2026) - Aggiunta action "Copy Link" con feedback visivo

#### IMP-003 & IMP-004: Max file size UX

**File**: `frontend/src/lib/components/settings/GlobalSettingsTab.svelte`
**Modifica IMP-003**: Mostrare unità (es: "10 MB", "100 MB")
**Modifica IMP-004**: Se valore > 500MB, mostrare warning:
> ⚠️ Large file uploads may fill server storage quickly

**Status**: ✅ COMPLETATO (29-01-2026) - Unità già mostrate via getSettingUnit(), aggiunto warning per >500MB

---

### Ordine di Implementazione Suggerito

1. ~~**BUG-003** - Blocca UX corretta upload~~ ✅ DONE
2. ~~**BUG-002** - Confonde utenti~~ ✅ DONE
3. ~~**IMP-001** - QoL tabelle~~ ✅ DONE
4. ~~**IMP-002** - Sblocca workflow icone broker~~ ✅ DONE
5. ~~**BUG-004** - i18n fix~~ ✅ DONE
6. ~~**IMP-003 + IMP-004** - UX global settings~~ ✅ DONE
7. ~~**BUG-001** - Backend minor~~ ✅ DONE
8. **BUG-005** - Docs polish (bassa priorità) 🔲 TODO

**Completati**: 7/8
**Stima rimanente**: ~30 min (solo BUG-005 mkdocs dark mode)

