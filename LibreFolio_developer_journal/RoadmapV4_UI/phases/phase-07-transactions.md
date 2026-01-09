# Phase 7: Transactions Management

**Status**: ⏳ TODO  
**Durata**: 5 giorni  
**Priorità**: P0 (MVP)
**Dipendenze**: Phase 4 (Brokers), Phase 6 (Assets)

---

## Obiettivo

Implementare la gestione completa delle transazioni: lista con filtri, creazione/modifica manuale, e import da broker report (BRIM).

---

## ⚠️ Riferimento Phase 9

Se vengono creati componenti riutilizzabili, seguire le linee guida in [Phase 9: Polish](./phase-09-polish.md) e aggiornare quella fase con i dettagli del componente.

**Componenti previsti per questa fase**:

- `TransactionTable.svelte` - Tabella transazioni specializzata
- `TransactionForm.svelte` - Form dinamico per tipo transazione
- `DatePicker.svelte` - Selezione data (se non già in Phase 9)
- Import Wizard steps - UploadStep, ParseStep, ReviewStep, ImportStep

---

## 7.1 Transactions List (1.5 giorni)

### Tasks

- [ ] Creare `src/routes/(app)/transactions/+page.svelte`
- [ ] Creare `src/routes/(app)/transactions/+page.ts`
- [ ] Creare `src/lib/components/transactions/TransactionTable.svelte`
- [ ] Creare `src/lib/components/transactions/TransactionFilters.svelte`
- [ ] Implementare paginazione

### Filter Controls

```svelte
<!-- TransactionFilters.svelte -->
<div class="filters flex flex-wrap gap-4 mb-4">
  <!-- Date Range -->
  <div class="flex gap-2">
    <div class="field">
      <label>From</label>
      <input type="date" bind:value={startDate} on:change={applyFilters} />
    </div>
    <div class="field">
      <label>To</label>
      <input type="date" bind:value={endDate} on:change={applyFilters} />
    </div>
  </div>
  
  <!-- Transaction Type -->
  <div class="field">
    <label>Type</label>
    <select bind:value={type} on:change={applyFilters}>
      <option value="">All Types</option>
      {#each transactionTypes as t}
        <option value={t.value}>{t.label}</option>
      {/each}
    </select>
  </div>
  
  <!-- Broker -->
  <div class="field">
    <label>Broker</label>
    <select bind:value={brokerId} on:change={applyFilters}>
      <option value="">All Brokers</option>
      {#each brokers as b}
        <option value={b.id}>{b.name}</option>
      {/each}
    </select>
  </div>
  
  <!-- Asset -->
  <div class="field">
    <label>Asset</label>
    <AssetSearchInput 
      bind:value={assetId} 
      on:change={applyFilters}
      placeholder="Filter by asset..."
    />
  </div>
  
  <button on:click={resetFilters}>Reset</button>
</div>
```

### Transaction Table

```svelte
<!-- TransactionTable.svelte -->
<table class="w-full">
  <thead>
    <tr>
      <th on:click={() => sortBy('date')}>Date {sortIcon('date')}</th>
      <th>Type</th>
      <th>Asset</th>
      <th>Quantity</th>
      <th>Cash</th>
      <th>Broker</th>
      <th>Description</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody>
    {#each transactions as tx}
      <tr>
        <td>{formatDate(tx.date)}</td>
        <td>
          <Badge variant={getTypeVariant(tx.type)}>
            {getTypeIcon(tx.type)} {tx.type}
          </Badge>
        </td>
        <td>
          {#if tx.asset}
            <a href="/assets/{tx.asset.id}" class="hover:underline">
              {tx.asset.display_name}
            </a>
          {:else}
            <span class="text-gray-400">-</span>
          {/if}
        </td>
        <td class:text-green-600={tx.quantity > 0} class:text-red-600={tx.quantity < 0}>
          {#if tx.quantity !== 0}
            {formatNumber(tx.quantity)}
          {:else}
            -
          {/if}
        </td>
        <td class:text-green-600={tx.cash?.amount > 0} class:text-red-600={tx.cash?.amount < 0}>
          {#if tx.cash}
            {formatCurrency(tx.cash.amount, tx.cash.code)}
          {:else}
            -
          {/if}
        </td>
        <td>{tx.broker?.name}</td>
        <td class="text-gray-600 text-sm truncate max-w-xs">{tx.description || '-'}</td>
        <td>
          <button on:click={() => editTransaction(tx)}>Edit</button>
          <button on:click={() => deleteTransaction(tx.id)}>Delete</button>
        </td>
      </tr>
    {/each}
  </tbody>
</table>

<!-- Pagination -->
{#if totalPages > 1}
  <Pagination 
    current={page} 
    total={totalPages} 
    on:change={(e) => goToPage(e.detail)} 
  />
{/if}
```

### Transaction Types

```typescript
const TRANSACTION_TYPES = [
    {value: 'BUY', label: 'Buy', icon: '📈', requiresAsset: true, requiresCash: true},
    {value: 'SELL', label: 'Sell', icon: '📉', requiresAsset: true, requiresCash: true},
    {value: 'DIVIDEND', label: 'Dividend', icon: '💰', requiresAsset: true, requiresCash: true},
    {value: 'INTEREST', label: 'Interest', icon: '🏦', requiresAsset: false, requiresCash: true},
    {value: 'DEPOSIT', label: 'Deposit', icon: '⬆️', requiresAsset: false, requiresCash: true},
    {value: 'WITHDRAWAL', label: 'Withdrawal', icon: '⬇️', requiresAsset: false, requiresCash: true},
    {value: 'FEE', label: 'Fee', icon: '💸', requiresAsset: false, requiresCash: true},
    {value: 'TAX', label: 'Tax', icon: '🏛️', requiresAsset: false, requiresCash: true},
    {value: 'ADJUSTMENT', label: 'Adjustment', icon: '⚖️', requiresAsset: true, requiresCash: false},
    // ... altri tipi
];
```

### API Endpoints

| Endpoint                     | Metodo | Descrizione            |
|------------------------------|--------|------------------------|
| `/api/v1/transactions`       | GET    | Lista con filtri       |
| `/api/v1/transactions/types` | GET    | Lista tipi disponibili |

### File da Creare

| File                                                        | Descrizione   |
|-------------------------------------------------------------|---------------|
| `src/routes/(app)/transactions/+page.svelte`                | Lista         |
| `src/routes/(app)/transactions/+page.ts`                    | Load function |
| `src/lib/components/transactions/TransactionTable.svelte`   | Tabella       |
| `src/lib/components/transactions/TransactionFilters.svelte` | Filtri        |

---

## 7.2 Add/Edit Transaction Modal (1.5 giorni)

### Tasks

- [ ] Creare `src/lib/components/transactions/AddTransactionModal.svelte`
- [ ] Creare `src/lib/components/transactions/TransactionForm.svelte`
- [ ] Implementare validazione dinamica in base a type
- [ ] Implementare auto-hide campi non richiesti

### Dynamic Form

```svelte
<!-- TransactionForm.svelte -->
<form on:submit|preventDefault={handleSubmit}>
  <!-- Transaction Type -->
  <div class="field">
    <label>Type *</label>
    <select bind:value={type} on:change={updateFormRequirements} required>
      {#each transactionTypes as t}
        <option value={t.value}>{t.icon} {t.label}</option>
      {/each}
    </select>
  </div>
  
  <!-- Broker -->
  <div class="field">
    <label>Broker *</label>
    <select bind:value={brokerId} required>
      {#each brokers as b}
        <option value={b.id}>{b.name}</option>
      {/each}
    </select>
  </div>
  
  <!-- Date -->
  <div class="field">
    <label>Date *</label>
    <input type="date" bind:value={date} required />
  </div>
  
  <!-- Asset (conditional) -->
  {#if requiresAsset}
    <div class="field">
      <label>Asset {assetRequired ? '*' : ''}</label>
      <AssetSearchInput 
        bind:value={assetId} 
        required={assetRequired}
      />
    </div>
  {/if}
  
  <!-- Quantity (conditional) -->
  {#if requiresQuantity}
    <div class="field">
      <label>Quantity *</label>
      <input type="number" step="any" bind:value={quantity} required />
    </div>
  {/if}
  
  <!-- Cash (conditional) -->
  {#if requiresCash}
    <div class="field cash-field">
      <label>Amount *</label>
      <div class="flex gap-2">
        <input type="number" step="0.01" bind:value={cashAmount} required />
        <CurrencySelect bind:value={cashCurrency} />
      </div>
      <p class="hint text-sm text-gray-500">
        {#if type === 'BUY'}
          Negative = cash outflow (payment)
        {:else if type === 'SELL' || type === 'DIVIDEND'}
          Positive = cash inflow (receipt)
        {/if}
      </p>
    </div>
  {/if}
  
  <!-- Description -->
  <div class="field">
    <label>Description</label>
    <textarea bind:value={description} rows="2"></textarea>
  </div>
  
  <!-- Tags -->
  <div class="field">
    <label>Tags</label>
    <TagsInput bind:value={tags} />
  </div>
  
  <div class="actions flex gap-2">
    <button type="button" on:click={cancel}>Cancel</button>
    <button type="submit">{isEditing ? 'Save' : 'Create'}</button>
  </div>
</form>
```

### Validation Rules per Type

```typescript
const VALIDATION_RULES = {
    BUY: {asset: 'required', quantity: 'required', cash: 'required'},
    SELL: {asset: 'required', quantity: 'required', cash: 'required'},
    DIVIDEND: {asset: 'required', quantity: 'none', cash: 'required'},
    INTEREST: {asset: 'optional', quantity: 'none', cash: 'required'},
    DEPOSIT: {asset: 'none', quantity: 'none', cash: 'required'},
    WITHDRAWAL: {asset: 'none', quantity: 'none', cash: 'required'},
    FEE: {asset: 'optional', quantity: 'none', cash: 'required'},
    TAX: {asset: 'optional', quantity: 'none', cash: 'required'},
    ADJUSTMENT: {asset: 'required', quantity: 'required', cash: 'none'},
};
```

### API Endpoints

| Endpoint                    | Metodo | Descrizione          |
|-----------------------------|--------|----------------------|
| `/api/v1/transactions`      | POST   | Crea transazione     |
| `/api/v1/transactions`      | PATCH  | Modifica transazione |
| `/api/v1/transactions/{id}` | DELETE | Elimina transazione  |

### File da Creare

| File                                                         | Descrizione   |
|--------------------------------------------------------------|---------------|
| `src/lib/components/transactions/AddTransactionModal.svelte` | Modal wrapper |
| `src/lib/components/transactions/TransactionForm.svelte`     | Form dinamico |

---

## 7.3 Broker Report Import Flow (2 giorni)

### Tasks

- [ ] Creare `src/routes/(app)/transactions/import/+page.svelte`
- [ ] Creare `src/lib/components/import/UploadStep.svelte`
- [ ] Creare `src/lib/components/import/ParseStep.svelte`
- [ ] Creare `src/lib/components/import/ReviewStep.svelte`
- [ ] Creare `src/lib/components/import/ImportStep.svelte`

### Import Wizard Steps

```svelte
<!-- Import page with steps -->
<div class="import-wizard">
  <div class="steps flex mb-8">
    <Step number={1} label="Upload" active={step === 1} done={step > 1} />
    <Step number={2} label="Parse" active={step === 2} done={step > 2} />
    <Step number={3} label="Review" active={step === 3} done={step > 3} />
    <Step number={4} label="Import" active={step === 4} done={step > 4} />
  </div>
  
  {#if step === 1}
    <UploadStep on:uploaded={handleUploaded} />
  {:else if step === 2}
    <ParseStep {fileId} {compatiblePlugins} on:parsed={handleParsed} />
  {:else if step === 3}
    <ReviewStep {parseResult} on:confirmed={handleConfirmed} />
  {:else if step === 4}
    <ImportStep {transactionsToImport} on:done={handleDone} />
  {/if}
</div>
```

### Step 1: Upload

```svelte
<!-- UploadStep.svelte -->
<div class="upload-step">
  <!-- Broker Selection -->
  <div class="field">
    <label>Broker *</label>
    <select bind:value={brokerId} required>
      {#each brokers as b}
        <option value={b.id}>{b.name}</option>
      {/each}
    </select>
  </div>
  
  <!-- File Upload -->
  <div 
    class="dropzone border-2 border-dashed rounded-lg p-8 text-center"
    class:border-libre-green={dragOver}
    on:dragover|preventDefault={() => dragOver = true}
    on:dragleave={() => dragOver = false}
    on:drop|preventDefault={handleDrop}
  >
    <input type="file" accept=".csv,.xlsx" bind:files on:change={handleFileSelect} hidden />
    <p>Drag & drop file here, or <button on:click={triggerFileSelect}>browse</button></p>
    {#if selectedFile}
      <p class="mt-2">📄 {selectedFile.name}</p>
    {/if}
  </div>
  
  <button on:click={upload} disabled={!brokerId || !selectedFile || uploading}>
    {uploading ? 'Uploading...' : 'Upload'}
  </button>
</div>
```

### Step 2: Parse

```svelte
<!-- ParseStep.svelte -->
<div class="parse-step">
  <p>File: {filename}</p>
  
  <!-- Plugin Selection -->
  <div class="field">
    <label>Import Plugin</label>
    {#if compatiblePlugins.length === 1}
      <p>Auto-detected: <strong>{compatiblePlugins[0]}</strong></p>
    {:else}
      <select bind:value={selectedPlugin}>
        {#each compatiblePlugins as plugin}
          <option value={plugin}>{getPluginName(plugin)}</option>
        {/each}
      </select>
    {/if}
  </div>
  
  <button on:click={parse} disabled={parsing}>
    {parsing ? 'Parsing...' : 'Parse File'}
  </button>
</div>
```

### Step 3: Review (Più complesso)

```svelte
<!-- ReviewStep.svelte -->
<div class="review-step">
  <!-- Transactions Preview -->
  <section class="transactions-preview">
    <h3>Transactions ({transactions.length})</h3>
    <table class="w-full">
      <thead>
        <tr>
          <th><input type="checkbox" bind:checked={selectAll} /></th>
          <th>Type</th>
          <th>Date</th>
          <th>Asset</th>
          <th>Qty</th>
          <th>Cash</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {#each transactions as tx, i}
          <tr class:opacity-50={!selectedIndices.includes(i)}>
            <td><input type="checkbox" checked={selectedIndices.includes(i)} on:change={() => toggleSelect(i)} /></td>
            <td>{tx.type}</td>
            <td>{formatDate(tx.date)}</td>
            <td>
              {#if assetMappings[tx.asset_id]?.selected_asset_id}
                ✅ {getAssetName(assetMappings[tx.asset_id].selected_asset_id)}
              {:else if assetMappings[tx.asset_id]?.candidates.length > 0}
                ⚠️ <select on:change={(e) => selectAsset(tx.asset_id, e.target.value)}>
                  <option value="">Select asset...</option>
                  {#each assetMappings[tx.asset_id].candidates as c}
                    <option value={c.asset_id}>{c.display_name}</option>
                  {/each}
                </select>
              {:else if tx.asset_id}
                ❌ Not found - <button on:click={() => createAsset(tx.asset_id)}>Create</button>
              {:else}
                -
              {/if}
            </td>
            <td>{tx.quantity}</td>
            <td>{formatCurrency(tx.cash?.amount, tx.cash?.code)}</td>
            <td>
              {#if isDuplicate(i)}
                <Badge variant="warning">Duplicate?</Badge>
              {:else}
                <Badge variant="success">New</Badge>
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </section>
  
  <!-- Duplicate Warnings -->
  {#if duplicatesReport.tx_likely_duplicates.length > 0}
    <section class="duplicates-warning mt-4 p-4 bg-yellow-50 rounded">
      <h4>⚠️ Likely Duplicates ({duplicatesReport.tx_likely_duplicates.length})</h4>
      <p class="text-sm">These transactions appear to already exist in your database.</p>
      <!-- Dettagli... -->
    </section>
  {/if}
  
  <div class="actions mt-4 flex gap-4">
    <button on:click={back}>← Back</button>
    <button 
      on:click={confirmImport} 
      disabled={!canImport}
      class="bg-libre-green text-white"
    >
      Import {selectedIndices.length} Transactions →
    </button>
  </div>
</div>
```

### Step 4: Import

```svelte
<!-- ImportStep.svelte -->
<div class="import-step text-center">
  {#if importing}
    <div class="spinner"></div>
    <p>Importing {current}/{total} transactions...</p>
    <div class="progress-bar bg-libre-green h-2 rounded" style="width: {progress}%"></div>
  {:else if result}
    <div class="result">
      {#if result.success}
        <div class="text-4xl">✅</div>
        <h3>Import Complete!</h3>
        <p>{result.imported} transactions imported successfully.</p>
        {#if result.errors.length > 0}
          <p class="text-yellow-600">{result.errors.length} failed.</p>
        {/if}
      {:else}
        <div class="text-4xl">❌</div>
        <h3>Import Failed</h3>
        <p>{result.error}</p>
      {/if}
      <button on:click={() => goto('/transactions')}>View Transactions</button>
    </div>
  {/if}
</div>
```

### API Endpoints

| Endpoint                                  | Metodo | Descrizione              |
|-------------------------------------------|--------|--------------------------|
| `/api/v1/brokers/import/upload`           | POST   | Upload file              |
| `/api/v1/brokers/import/files/{id}/parse` | POST   | Parse file               |
| `/api/v1/brokers/import/plugins`          | GET    | Lista plugins            |
| `/api/v1/transactions`                    | POST   | Bulk create transactions |

### File da Creare

| File                                                | Descrizione   |
|-----------------------------------------------------|---------------|
| `src/routes/(app)/transactions/import/+page.svelte` | Import wizard |
| `src/lib/components/import/UploadStep.svelte`       | Step 1        |
| `src/lib/components/import/ParseStep.svelte`        | Step 2        |
| `src/lib/components/import/ReviewStep.svelte`       | Step 3        |
| `src/lib/components/import/ImportStep.svelte`       | Step 4        |

---

## Verifica Completamento

### Test Manuali

- [ ] Lista transazioni visibile
- [ ] Filtri funzionano (date, type, broker, asset)
- [ ] Ordinamento per data funziona
- [ ] Paginazione funziona
- [ ] Add transaction manuale → appare in lista
- [ ] Edit transaction → modifiche salvate
- [ ] Delete transaction → rimosso
- [ ] Import: upload file → parse → review → import
- [ ] Import: asset mapping funziona
- [ ] Import: duplicates warning visibile
- [ ] Import: può deselezionare transazioni

---

## Dipendenze

- **Richiede**: Phase 4 (Brokers), Phase 6 (Assets)
- **Sblocca**: Phase 8 (Dashboard usa transactions)

