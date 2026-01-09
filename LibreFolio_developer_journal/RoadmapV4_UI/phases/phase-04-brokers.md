# Phase 4: Brokers Management

**Status**: ⏳ TODO  
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

- `BrokerCard.svelte` - Card display broker
- `Modal.svelte` - Se non già esistente in Phase 9
- `CurrencySelect.svelte` - Selector valuta riutilizzabile

---

## 4.1 Brokers List (1 giorno)

### Tasks

- [ ] Creare `src/routes/(app)/brokers/+page.svelte`
- [ ] Creare `src/routes/(app)/brokers/+page.ts` (load function)
- [ ] Creare `src/lib/components/brokers/BrokerCard.svelte`
- [ ] Implementare button "Add Broker"

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

