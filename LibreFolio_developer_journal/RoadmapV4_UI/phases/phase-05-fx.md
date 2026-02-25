# Phase 5: FX Management

**Status**: ⏳ TODO  
**Durata**: ~4 giorni (aggiornata)  
**Priorità**: P1 (Important)  
**Dipendenze**: Phase 4.8 (Broker Sharing GUI), Phase 3 (Layout)

> **📌 Riferimento principale**: [`plan-phase05-to-08-upgrade.md` §4](../plan-phase05-to-08-upgrade.md)
> Questa sezione è stata **SUPERATA** dal piano aggiornato. Quando si arriva a implementare Phase 5,
> ripartire da §4 di `plan-phase05-to-08-upgrade.md` che contiene:
> - **Step 5.0**: `PriceChartShared.svelte` — componente ECharts condiviso tra FX e Assets (§9 per spec)
> - **Step 5.1**: CurrencyGrid con flag emoji e SearchSelect
> - **Step 5.2**: FxRateChart con gradiente opacità per dati stale (`staleDays`)
> - **Step 5.3**: PairSources CRUD con `DataTable` (esistente)
> - **Step 5.4**: FxSyncModal con date range, warning sovrascrittura, progress bar
>
> **Componenti da riusare (già esistenti da Phase 4)**:
> `DataTable`, `ModalBase`, `ConfirmModal`, `SearchSelect`, `SimpleSelect`, `LazyImage`
>
> **Novità rispetto a questo vecchio plan**:
> - Il chart usa ECharts con gradiente che sfuma dati stale: `opacity = max(0.3, 1.0 - staleDays * 0.15)`
> - Click-to-edit su data point del chart (per edit manuali)
> - `user_role` dal broker sharing condiziona i permessi (VIEWER = sola lettura, no sync)
> - Range selector integrato nel chart (1W, 1M, 3M, 6M, 1Y, ALL)

---

## Obiettivo

Implementare la gestione dei tassi di cambio: visualizzazione valute, configurazione pair sources, sincronizzazione e inserimento manuale.

---

## ⚠️ Nota: Plan Originale (Legacy)

Il contenuto sotto è il **plan originale** scritto prima delle fasi 4.5–4.8. I componenti UI suggeriti
(CurrencyCard, PairSourceTable, etc.) andranno **riscritti** usando `DataTable`, `ModalBase`, e gli altri
componenti unificati creati in Phase 4. Fare riferimento a §4 di `plan-phase05-to-08-upgrade.md` per
la versione aggiornata.

**Componenti previsti per questa fase (aggiornati)**:

- `PriceChartShared.svelte` - Chart ECharts condiviso FX/Assets (**NUOVO**, §9 per spec)
- `FxRateChart.svelte` - Wrapper FX per PriceChartShared
- `FxPairSourcesSection.svelte` - CRUD pair sources con DataTable
- `FxSyncModal.svelte` - Dialog sync con ModalBase
- `CurrencyGrid.svelte` - Grid valute con flag e SearchSelect

---

## 5.1 FX Currencies List (1 giorno)

### Tasks

- [ ] Creare `src/routes/(app)/fx/+page.svelte`
- [ ] Creare `src/routes/(app)/fx/+page.ts`
- [ ] Creare `src/lib/components/fx/CurrencyGrid.svelte`
- [ ] Creare `src/lib/components/fx/CurrencyCard.svelte`
- [ ] Implementare tabs per provider

### Page Structure

```svelte
<!-- src/routes/(app)/fx/+page.svelte -->
<h1>FX Rates Management</h1>

<!-- Provider Tabs -->
<div class="tabs">
  <button class:active={provider === 'ECB'} on:click={() => provider = 'ECB'}>
    🇪🇺 ECB
  </button>
  <button class:active={provider === 'FED'} on:click={() => provider = 'FED'}>
    🇺🇸 FED
  </button>
  <button class:active={provider === 'BOE'} on:click={() => provider = 'BOE'}>
    🇬🇧 BOE
  </button>
  <button class:active={provider === 'SNB'} on:click={() => provider = 'SNB'}>
    🇨🇭 SNB
  </button>
</div>

<!-- Currency Grid -->
<CurrencyGrid currencies={currenciesForProvider} />

<!-- Pair Sources Section -->
<PairSourceTable sources={pairSources} />

<!-- Sync Tool Section -->
<SyncTool />
```

### Currency Card

```svelte
<!-- CurrencyCard.svelte -->
<div class="currency-card bg-white rounded p-4 flex items-center gap-3">
  <span class="flag text-2xl">{flag}</span>
  <div>
    <div class="code font-bold">{currency.code}</div>
    <div class="name text-gray-600 text-sm">{currency.name}</div>
  </div>
</div>
```

### API Endpoints

| Endpoint                                       | Metodo | Descrizione              |
|------------------------------------------------|--------|--------------------------|
| `/api/v1/fx/currencies?provider={p}`           | GET    | Valute per provider      |
| `/api/v1/utilities/currencies?language={lang}` | GET    | Nomi localizzati + flags |

### File da Creare

| File                                        | Descrizione         |
|---------------------------------------------|---------------------|
| `src/routes/(app)/fx/+page.svelte`          | Pagina FX           |
| `src/routes/(app)/fx/+page.ts`              | Load function       |
| `src/lib/components/fx/CurrencyGrid.svelte` | Grid valute         |
| `src/lib/components/fx/CurrencyCard.svelte` | Card singola valuta |

---

## 5.2 Currency Pair Sources CRUD (1 giorno)

### Tasks

- [ ] Creare `src/lib/components/fx/PairSourceTable.svelte`
- [ ] Creare `src/lib/components/fx/AddPairModal.svelte`
- [ ] Creare `src/lib/components/fx/EditPairModal.svelte`
- [ ] Implementare delete con conferma

### Pair Source Table

```svelte
<!-- PairSourceTable.svelte -->
<table class="w-full">
  <thead>
    <tr>
      <th>Base</th>
      <th>Quote</th>
      <th>Provider</th>
      <th>Priority</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody>
    {#each sources as source}
      <tr>
        <td>{getFlag(source.base)} {source.base}</td>
        <td>{getFlag(source.quote)} {source.quote}</td>
        <td>{source.provider}</td>
        <td>{source.priority}</td>
        <td>
          <button on:click={() => editSource(source)}>Edit</button>
          <button on:click={() => deleteSource(source)}>Delete</button>
        </td>
      </tr>
    {/each}
  </tbody>
</table>

<button on:click={() => showAddModal = true}>+ Add Pair Source</button>
```

### Add/Edit Modal Form

```svelte
<!-- AddPairModal.svelte -->
<form on:submit|preventDefault={handleSubmit}>
  <!-- Base Currency -->
  <div class="field">
    <label>Base Currency</label>
    <CurrencySelect bind:value={base} currencies={allCurrencies} />
  </div>
  
  <!-- Quote Currency -->
  <div class="field">
    <label>Quote Currency</label>
    <CurrencySelect bind:value={quote} currencies={allCurrencies} />
  </div>
  
  <!-- Provider -->
  <div class="field">
    <label>Provider</label>
    <select bind:value={provider}>
      <option value="ECB">🇪🇺 ECB</option>
      <option value="FED">🇺🇸 FED</option>
      <option value="BOE">🇬🇧 BOE</option>
      <option value="SNB">🇨🇭 SNB</option>
      <option value="FALLBACK">Fallback</option>
    </select>
  </div>
  
  <!-- Priority -->
  <div class="field">
    <label>Priority (0-10)</label>
    <input type="range" min="0" max="10" bind:value={priority} />
    <span>{priority}</span>
  </div>
  
  <button type="submit">Save</button>
</form>
```

### Validazione

```typescript
// base !== quote
if (base === quote) {
    error = 'Base and quote currencies must be different';
    return;
}
```

### API Endpoints

| Endpoint                            | Metodo | Descrizione         |
|-------------------------------------|--------|---------------------|
| `/api/v1/fx/providers/pair-sources` | GET    | Lista pair sources  |
| `/api/v1/fx/providers/pair-sources` | POST   | Crea pair source    |
| `/api/v1/fx/providers/pair-sources` | DELETE | Elimina pair source |

### File da Creare

| File                                           | Descrizione          |
|------------------------------------------------|----------------------|
| `src/lib/components/fx/PairSourceTable.svelte` | Tabella pair sources |
| `src/lib/components/fx/AddPairModal.svelte`    | Modal aggiunta       |
| `src/lib/components/fx/EditPairModal.svelte`   | Modal modifica       |

---

## 5.3 FX Sync Tool + Manual Entry (1 giorno)

### Tasks

- [ ] Creare `src/lib/components/fx/SyncTool.svelte`
- [ ] Creare `src/lib/components/fx/ManualRateModal.svelte`
- [ ] Implementare progress durante sync
- [ ] Implementare feedback risultati

### Sync Tool Component

```svelte
<!-- SyncTool.svelte -->
<div class="sync-tool bg-gray-100 rounded p-4">
  <h3>Sync FX Rates</h3>
  
  <!-- Date Range -->
  <div class="flex gap-4">
    <div class="field">
      <label>Start Date</label>
      <input type="date" bind:value={startDate} />
    </div>
    <div class="field">
      <label>End Date</label>
      <input type="date" bind:value={endDate} />
    </div>
  </div>
  
  <!-- Currencies Multi-select -->
  <div class="field">
    <label>Currencies</label>
    <div class="currency-chips flex flex-wrap gap-2">
      {#each selectedCurrencies as curr}
        <span class="chip">{getFlag(curr)} {curr} ✕</span>
      {/each}
    </div>
    <CurrencySelect on:select={addCurrency} />
  </div>
  
  <!-- Provider (optional) -->
  <div class="field">
    <label>Provider (optional)</label>
    <select bind:value={provider}>
      <option value="">Use Pair Sources Config</option>
      <option value="ECB">ECB</option>
      <option value="FED">FED</option>
      <!-- ... -->
    </select>
  </div>
  
  <!-- Sync Button -->
  <button on:click={sync} disabled={syncing}>
    {syncing ? 'Syncing...' : 'Sync Now'}
  </button>
  
  <!-- Progress -->
  {#if syncing}
    <div class="progress-bar bg-libre-green h-2 rounded" style="width: {progress}%"></div>
  {/if}
  
  <!-- Results -->
  {#if result}
    <div class="result mt-4 p-3 bg-green-100 rounded">
      ✅ {result.fetched} rates fetched, {result.changed} changed
    </div>
  {/if}
</div>
```

### Manual Rate Modal

```svelte
<!-- ManualRateModal.svelte -->
<form on:submit|preventDefault={handleSubmit}>
  <h3>Add Manual Rate</h3>
  
  <div class="field">
    <label>Date</label>
    <input type="date" bind:value={date} required />
  </div>
  
  <div class="field">
    <label>Base Currency</label>
    <CurrencySelect bind:value={base} />
  </div>
  
  <div class="field">
    <label>Quote Currency</label>
    <CurrencySelect bind:value={quote} />
  </div>
  
  <div class="field">
    <label>Rate</label>
    <input type="number" step="0.000001" min="0" bind:value={rate} required />
    <span class="hint">1 {base} = {rate} {quote}</span>
  </div>
  
  <button type="submit">Save Rate</button>
</form>
```

### API Endpoints

| Endpoint                     | Metodo | Descrizione             |
|------------------------------|--------|-------------------------|
| `/api/v1/fx/currencies/sync` | GET    | Sync rates (con params) |
| `/api/v1/fx/currencies/rate` | POST   | Inserimento manuale     |

### File da Creare

| File                                           | Descrizione           |
|------------------------------------------------|-----------------------|
| `src/lib/components/fx/SyncTool.svelte`        | Tool sincronizzazione |
| `src/lib/components/fx/ManualRateModal.svelte` | Modal rate manuale    |

---

## Verifica Completamento

### Test Manuali

- [ ] Grid valute visibile per ogni provider tab
- [ ] Add pair source → appare in tabella
- [ ] Edit pair source → modifiche salvate
- [ ] Delete pair source → rimosso
- [ ] Sync rates → progress visibile → risultato mostrato
- [ ] Add manual rate → salvato correttamente
- [ ] Flags emoji corretti per ogni valuta

---

## Mockup Riferimento

- `/site/POC_UX/fx/fx_pair_*.jpg`

---

## Dipendenze

- **Richiede**: Phase 3 (Layout)
- **Opzionale per MVP**: Può essere saltato inizialmente

