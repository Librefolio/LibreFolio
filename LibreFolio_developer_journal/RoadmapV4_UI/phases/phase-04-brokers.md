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

3. **Broker Form**: ✅ **VERIFICATO**
   - GenericCSV ordering: ✅ **FIXED** (code `'broker_generic_csv'`)
   - GenericCSV appare primo con "(default)" label ✅

4. **Files Page**: ✅ **VERIFICATO**
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

7. **Developer Tools**: ✅ **NUOVO**
   - **GUIDA-DARK-MODE.md**: ✅ Creata guida per modificare velocemente variabili dark mode

#### 🎯 Settings Unification Plan - Fase 1 & 2 COMPLETATE

**Fase 1 Completata** (20-01-2026):
- ✅ `SettingField.svelte` creato
- ✅ `SettingsLayout.svelte` creato  
- ✅ `SettingText.svelte` creato
- ⏳ SettingImageUpload rimandato a Image Crop Plan
- ✅ Test: 0 errors, 0 warnings

**Fase 2 Completata** (20-01-2026):
- ✅ PreferencesTab refactorizzato con nuovi componenti
- ✅ Ridotto da 451 → ~150 righe
- ✅ UI consistente, tutte le funzionalità mantenute
- ✅ Test: 0 errors, 0 warnings

**Prossimo**: Fase 3 - Refactor GlobalSettingsTab

**Link**: [`../plan-settings-unification.md`](../plan-settings-unification.md)

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

#### 2. Table Improvements Plan ✅ **APPROVATO**
**File**: [`../plan-table-improvements.md`](../plan-table-improvements.md)

**Obiettivo**: Migliorare tabelle Files (Static + BRIM) con sorting, filtering, pagination, e **preview**.

**Libreria scelta**: **TanStack Table** (motivazione: licenza MIT + features complete)

**Features implementate**:
- ✅ **Preview API Backend**: 
  - Text: `GET /uploads/file/{id}?offset=0&window=1000`
  - Images: `GET /uploads/file/{id}?img_preview=400x400`
  - Error 400 per file incompatibili

**Da implementare**:
- [ ] Setup TanStack Table
- [ ] Sorting multi-column
- [ ] Pagination con selettore (10/50/100/All)
- [ ] Filtering per nome/tipo/data
- [ ] Preview modal (Eye icon)
- [ ] Selezione multipla + bulk actions
- [ ] Delete confirmation banner (no alert)
- [ ] Rename file function

**Stima**: 3-6 giorni

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

#### 4. Table Libraries Comparison
**File**: [`../table-libraries-comparison.md`](../table-libraries-comparison.md)

**Documento di analisi** con comparazione dettagliata:
- TanStack Table (✅ raccomandato)
- Svelte-Simple-Datatables
- Native Custom
- ag-Grid Community

**Decisione**: TanStack Table approvato per scalabilità, features, e licenza MIT.

---

### 🗺️ Ordine di Implementazione Suggerito

Basandosi su priorità, dipendenze, e impatto:

1. **🥇 Table Improvements** (3-6 giorni)
   - **Motivazione**: Impatto immediato su UX, fondazione per Assets/Transactions/FX
   - **Blocca**: Nessun altro piano
   - **Estensibilità**: DataTable component riutilizzabile ovunque
   - **Status**: ✅ API backend pronta, frontend da implementare

2. **🥈 Image Crop** (2-4 giorni)
   - **Motivazione**: Necessario per Profile page e migliora UX upload
   - **Blocca**: Settings Unification (Profile avatar)
   - **Estensibilità**: Riutilizzabile per broker icons, asset logos, cover images
   - **Status**: 📋 Piano pronto, libreria valutata

3. **🥉 Settings Unification** (4-8 giorni)
   - **Motivazione**: Standardizza UI settings, introduce Profile page
   - **Dipende da**: Image Crop (per avatar upload)
   - **Estensibilità**: Componenti Setting* riutilizzabili per future pagine config
   - **Status**: 📋 Piano dettagliato, decisioni prese

---

### 📊 Timeline Totale Consolidation

**Ottimistico**: 9 giorni  
**Realistico**: 13 giorni  
**Con imprevisti**: 18 giorni

---

### 🔗 Collegamenti ai Documenti

| Documento | Descrizione | Status |
|-----------|-------------|--------|
| [plan-settings-unification.md](../plan-settings-unification.md) | Componenti condivisi Settings + Profile | 📋 Pronto |
| [plan-table-improvements.md](../plan-table-improvements.md) | TanStack Table + Preview | ✅ API Done |
| [plan-image-crop.md](../plan-image-crop.md) | Advanced crop component | 📋 Pronto |
| [table-libraries-comparison.md](../table-libraries-comparison.md) | Analisi librerie tabelle | ✅ Completato |
| [session-summary-20250120.md](../session-summary-20250120.md) | Riepilogo sessione fix | ✅ Completato |

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

