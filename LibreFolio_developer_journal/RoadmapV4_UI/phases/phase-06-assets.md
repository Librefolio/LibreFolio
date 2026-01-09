# Phase 6: Assets Management

**Status**: ⏳ TODO  
**Durata**: 4 giorni  
**Priorità**: P0 (MVP)
**Dipendenze**: Phase 3

---

## Obiettivo

Implementare la gestione completa degli asset: lista con filtri, creazione con smart search, e vista dettaglio con price chart.

---

## ⚠️ Riferimento Phase 9

Se vengono creati componenti riutilizzabili, seguire le linee guida in [Phase 9: Polish](./phase-09-polish.md) e aggiornare quella fase con i dettagli del componente.

**Componenti previsti per questa fase**:

- `AssetSearchAutocomplete.svelte` - Ricerca smart multi-provider
- `PriceChart.svelte` - Chart ECharts per prezzi
- `Badge.svelte` - Se non già in Phase 9
- `Pagination.svelte` - Se non già in Phase 9

---

## 6.1 Assets List (Query & Filter) (1 giorno)

### Tasks

- [ ] Creare `src/routes/(app)/assets/+page.svelte`
- [ ] Creare `src/routes/(app)/assets/+page.ts`
- [ ] Creare `src/lib/components/assets/AssetTable.svelte`
- [ ] Creare `src/lib/components/assets/AssetFilters.svelte`
- [ ] Implementare paginazione (se > 50 risultati)

### Filter Controls

```svelte
<!-- AssetFilters.svelte -->
<div class="filters flex flex-wrap gap-4 mb-4">
  <!-- Search -->
  <div class="field flex-1">
    <input 
      type="search" 
      placeholder="Search by name, ticker, ISIN..."
      bind:value={search}
      on:input={debounce(applyFilters, 300)}
    />
  </div>
  
  <!-- Asset Type -->
  <div class="field">
    <select bind:value={assetType} on:change={applyFilters}>
      <option value="">All Types</option>
      <option value="STOCK">Stock</option>
      <option value="ETF">ETF</option>
      <option value="BOND">Bond</option>
      <option value="FUND">Fund</option>
      <option value="CRYPTO">Crypto</option>
      <option value="COMMODITY">Commodity</option>
      <option value="OTHER">Other</option>
    </select>
  </div>
  
  <!-- Currency -->
  <div class="field">
    <CurrencySelect 
      bind:value={currency} 
      on:change={applyFilters}
      allowEmpty
      emptyLabel="All Currencies"
    />
  </div>
  
  <!-- Active Only -->
  <div class="field">
    <label class="flex items-center gap-2">
      <input type="checkbox" bind:checked={activeOnly} on:change={applyFilters} />
      Active Only
    </label>
  </div>
  
  <!-- Reset -->
  <button on:click={resetFilters} class="text-gray-600">Reset</button>
</div>
```

### Asset Table

```svelte
<!-- AssetTable.svelte -->
<table class="w-full">
  <thead>
    <tr>
      <th on:click={() => sortBy('display_name')}>Name {sortIcon('display_name')}</th>
      <th on:click={() => sortBy('asset_type')}>Type</th>
      <th on:click={() => sortBy('currency')}>Currency</th>
      <th>Identifiers</th>
      <th>Provider</th>
      <th>Status</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody>
    {#each assets as asset}
      <tr>
        <td class="flex items-center gap-2">
          <img src={asset.icon_url || defaultIcon} class="w-6 h-6" />
          <span>{asset.display_name}</span>
        </td>
        <td><Badge variant={asset.asset_type}>{asset.asset_type}</Badge></td>
        <td>{getFlag(asset.currency)} {asset.currency}</td>
        <td class="text-xs text-gray-600">
          {#if asset.identifier_ticker}{asset.identifier_ticker}{/if}
          {#if asset.identifier_isin} / {asset.identifier_isin}{/if}
        </td>
        <td>
          {#if asset.has_provider}
            <Badge variant="success">Assigned</Badge>
          {:else}
            <Badge variant="neutral">None</Badge>
          {/if}
        </td>
        <td>
          {#if asset.active}
            <Badge variant="success">Active</Badge>
          {:else}
            <Badge variant="neutral">Inactive</Badge>
          {/if}
        </td>
        <td>
          <button on:click={() => goto(`/assets/${asset.id}`)}>View</button>
          <button on:click={() => editAsset(asset)}>Edit</button>
          <button on:click={() => deleteAsset(asset.id)}>Delete</button>
        </td>
      </tr>
    {/each}
  </tbody>
</table>
```

### API Endpoints

| Endpoint               | Metodo | Descrizione      |
|------------------------|--------|------------------|
| `/api/v1/assets/query` | GET    | Lista con filtri |

Query params: `search`, `asset_type`, `currency`, `active`

### File da Creare

| File                                            | Descrizione    |
|-------------------------------------------------|----------------|
| `src/routes/(app)/assets/+page.svelte`          | Lista assets   |
| `src/routes/(app)/assets/+page.ts`              | Load function  |
| `src/lib/components/assets/AssetTable.svelte`   | Tabella assets |
| `src/lib/components/assets/AssetFilters.svelte` | Filtri         |

---

## 6.2 Add/Edit Asset Modal (Smart Search) (2 giorni)

### Tasks

- [ ] Creare `src/lib/components/assets/AddAssetModal.svelte`
- [ ] Creare `src/lib/components/assets/EditAssetModal.svelte`
- [ ] Creare `src/lib/components/assets/AssetSearchAutocomplete.svelte`
- [ ] Implementare multi-provider search
- [ ] Implementare auto-fill da search result

### Smart Search Flow

1. User digita query (es. "AAPL" o "Apple")
2. Sistema cerca su provider selezionati (yfinance, justetf, etc.)
3. Dropdown mostra risultati con info
4. User seleziona → form auto-compilato
5. User può modificare campi
6. Submit crea asset nel DB

### Search Autocomplete

```svelte
<!-- AssetSearchAutocomplete.svelte -->
<div class="autocomplete relative">
  <!-- Provider Selection -->
  <div class="providers mb-2 flex gap-2">
    {#each providers as p}
      <label class="flex items-center gap-1">
        <input 
          type="checkbox" 
          checked={selectedProviders.includes(p.code)}
          on:change={() => toggleProvider(p.code)}
        />
        {p.name}
      </label>
    {/each}
  </div>
  
  <!-- Search Input -->
  <input 
    type="search"
    placeholder="Search by ticker, ISIN, or name..."
    bind:value={query}
    on:input={debounce(search, 300)}
    on:focus={() => showDropdown = true}
  />
  
  <!-- Results Dropdown -->
  {#if showDropdown && results.length > 0}
    <ul class="dropdown absolute w-full bg-white shadow-lg rounded mt-1 max-h-64 overflow-auto">
      {#each results as result}
        <li 
          class="p-3 hover:bg-gray-100 cursor-pointer"
          on:click={() => selectResult(result)}
        >
          <div class="flex items-center gap-3">
            <img src={result.icon_url || getTypeIcon(result.asset_type)} class="w-8 h-8" />
            <div>
              <div class="font-bold">{result.display_name}</div>
              <div class="text-sm text-gray-600">
                {result.symbol || result.isin} · {result.currency} · {result.asset_type}
              </div>
              <div class="text-xs text-gray-400">via {result.source}</div>
            </div>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</div>
```

### Add Asset Form

```svelte
<!-- AddAssetModal.svelte -->
<div class="modal">
  <h2>Add Asset</h2>
  
  <!-- Smart Search -->
  <div class="section">
    <h3>Search External Providers</h3>
    <AssetSearchAutocomplete on:select={autoFillForm} />
  </div>
  
  <hr />
  
  <!-- Manual Form -->
  <form on:submit|preventDefault={handleSubmit}>
    <!-- Display Name -->
    <div class="field">
      <label>Display Name *</label>
      <input type="text" bind:value={displayName} required />
    </div>
    
    <!-- Asset Type -->
    <div class="field">
      <label>Asset Type *</label>
      <select bind:value={assetType} required>
        <option value="STOCK">Stock</option>
        <option value="ETF">ETF</option>
        <option value="BOND">Bond</option>
        <option value="FUND">Fund</option>
        <option value="CRYPTO">Crypto</option>
        <option value="COMMODITY">Commodity</option>
        <option value="OTHER">Other</option>
      </select>
    </div>
    
    <!-- Currency -->
    <div class="field">
      <label>Currency *</label>
      <CurrencySelect bind:value={currency} required />
    </div>
    
    <!-- Icon URL -->
    <div class="field">
      <label>Icon URL (optional)</label>
      <input type="url" bind:value={iconUrl} />
    </div>
    
    <!-- Identifiers (collapsible) -->
    <details class="identifiers">
      <summary>Identifiers</summary>
      <div class="grid grid-cols-2 gap-4 mt-2">
        <div class="field">
          <label>ISIN</label>
          <input type="text" bind:value={isin} maxlength="12" />
        </div>
        <div class="field">
          <label>Ticker</label>
          <input type="text" bind:value={ticker} />
        </div>
        <div class="field">
          <label>CUSIP</label>
          <input type="text" bind:value={cusip} />
        </div>
        <div class="field">
          <label>SEDOL</label>
          <input type="text" bind:value={sedol} />
        </div>
        <div class="field">
          <label>FIGI</label>
          <input type="text" bind:value={figi} />
        </div>
        <div class="field">
          <label>Other</label>
          <input type="text" bind:value={other} />
        </div>
      </div>
    </details>
    
    <button type="submit">Create Asset</button>
  </form>
</div>
```

### API Endpoints

| Endpoint                         | Metodo | Descrizione                |
|----------------------------------|--------|----------------------------|
| `/api/v1/assets/provider`        | GET    | Lista provider disponibili |
| `/api/v1/assets/provider/search` | GET    | Cerca su provider esterni  |
| `/api/v1/assets`                 | POST   | Crea asset                 |
| `/api/v1/assets`                 | PATCH  | Modifica asset             |

### File da Creare

| File                                                       | Descrizione     |
|------------------------------------------------------------|-----------------|
| `src/lib/components/assets/AddAssetModal.svelte`           | Modal creazione |
| `src/lib/components/assets/EditAssetModal.svelte`          | Modal modifica  |
| `src/lib/components/assets/AssetSearchAutocomplete.svelte` | Ricerca smart   |

---

## 6.3 Asset Detail Page (1 giorno)

### Tasks

- [ ] Creare `src/routes/(app)/assets/[id]/+page.svelte`
- [ ] Creare `src/routes/(app)/assets/[id]/+page.ts`
- [ ] Creare `src/lib/components/assets/AssetDetailHeader.svelte`
- [ ] Creare `src/lib/components/assets/ProviderAssignmentSection.svelte`
- [ ] Creare `src/lib/components/assets/PriceChart.svelte` (ECharts)

### Page Sections

1. **Header**
    - Icon + Display Name + Type badge
    - Currency + Active status
    - Edit button

2. **Provider Assignment**
    - Current provider (if any)
    - Button to assign/change provider
    - Modal con form

3. **Price History Chart**
    - ECharts line chart
    - Range selector: 1M, 3M, 6M, 1Y, ALL

4. **Metadata**
    - Identifiers (ISIN, Ticker, etc.)
    - Classification (sector, geographic area)

### Price Chart (ECharts)

```svelte
<!-- PriceChart.svelte -->
<script>
  import * as echarts from 'echarts';
  import { onMount, onDestroy } from 'svelte';
  
  export let priceData: { date: string; close: number }[] = [];
  export let currency: string = 'EUR';
  
  let chartContainer: HTMLDivElement;
  let chart: echarts.ECharts;
  
  $: if (chart && priceData) {
    updateChart();
  }
  
  onMount(() => {
    chart = echarts.init(chartContainer);
    updateChart();
    
    const resizeObserver = new ResizeObserver(() => chart.resize());
    resizeObserver.observe(chartContainer);
    
    return () => resizeObserver.disconnect();
  });
  
  onDestroy(() => chart?.dispose());
  
  function updateChart() {
    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: priceData.map(d => d.date)
      },
      yAxis: {
        type: 'value',
        name: currency
      },
      series: [{
        type: 'line',
        data: priceData.map(d => d.close),
        smooth: true,
        itemStyle: { color: '#1A4D3E' },
        areaStyle: { color: 'rgba(26, 77, 62, 0.1)' }
      }]
    });
  }
</script>

<div class="chart-container h-64" bind:this={chartContainer}></div>
```

### API Endpoints

| Endpoint                                             | Metodo | Descrizione         |
|------------------------------------------------------|--------|---------------------|
| `/api/v1/assets?ids={id}`                            | GET    | Dettaglio asset     |
| `/api/v1/assets/provider/assignments?asset_ids={id}` | GET    | Provider assignment |
| `/api/v1/assets/prices/{id}`                         | GET    | Price history       |
| `/api/v1/assets/provider`                            | POST   | Assign provider     |

### File da Creare

| File                                                         | Descrizione     |
|--------------------------------------------------------------|-----------------|
| `src/routes/(app)/assets/[id]/+page.svelte`                  | Dettaglio asset |
| `src/routes/(app)/assets/[id]/+page.ts`                      | Load function   |
| `src/lib/components/assets/AssetDetailHeader.svelte`         | Header          |
| `src/lib/components/assets/ProviderAssignmentSection.svelte` | Provider        |
| `src/lib/components/assets/PriceChart.svelte`                | Chart ECharts   |

---

## Verifica Completamento

### Test Manuali

- [ ] Lista assets visibile (anche vuota con empty state)
- [ ] Filtri funzionano (search, type, currency, active)
- [ ] Smart search trova asset su provider esterni
- [ ] Selezione da search auto-compila form
- [ ] Crea asset manualmente → appare in lista
- [ ] Edit asset → modifiche salvate
- [ ] Delete asset → rimosso
- [ ] Dettaglio asset → tutte le sezioni visibili
- [ ] Assign provider → price chart popolato
- [ ] Chart range selector funziona

---

## Dipendenze

- **Richiede**: Phase 3 (Layout)
- **Sblocca**: Phase 7 (Transactions con asset_id)

