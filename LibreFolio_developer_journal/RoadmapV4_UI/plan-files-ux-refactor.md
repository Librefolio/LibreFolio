# Plan: Files Page UX Refactoring + URL Deep-Linking

**Data creazione**: 30 Gennaio 2026  
**Status**: 📋 DA IMPLEMENTARE  
**Priorità**: P1  
**Stima**: 3h totali (Step 2: 1h, Step 3: 2h)

---

## 🎯 Obiettivo

Migliorare l'esperienza utente della pagina `/files` e della sezione Import Files nel broker detail:

1. **URL Deep-Linking**: Permettere di linkare direttamente a filtri specifici
2. **Broker Detail → Files**: Link diretto con filtro broker pre-applicato
3. **Refactor Import Files Section**: Da sezione inline a modale con DataTable

---

## 📋 Problema Attuale

### Pagina `/files`

- I filtri non sono sincronizzati con l'URL
- Non è possibile fare deep-link a una vista specifica
- Cambiando tab si perdono i filtri

### Broker Detail Import Files

- Sezione sempre visibile (occupa spazio)
- Lista custom non riutilizza DataTable
- Delete usa `confirm()` invece di ConfirmModal
- Link "Manage all files" non passa filtro broker

---

## 🔧 Step 2: Files Page URL Filters (1h)

### 2.1 URL Parameters Supportati

```
/files?tab=static|brim&broker_id=1,2,3&status=uploaded,parsed&search=report
```

| Param       | Tipo                         | Descrizione       | Default      |
|-------------|------------------------------|-------------------|--------------|
| `tab`       | `'static' \| 'brim'`         | Tab attiva        | `'static'`   |
| `broker_id` | `number[]` (comma-separated) | Filtro broker IDs | `[]` (tutti) |
| `status`    | `string[]` (comma-separated) | Filtro stati file | `[]` (tutti) |
| `search`    | `string`                     | Ricerca testuale  | `''`         |

### 2.2 Modifiche a `/files/+page.svelte`

```typescript
// Imports
import {page} from '$app/stores';
import {goto} from '$app/navigation';
import {browser} from '$app/environment';

// Read URL params on mount
onMount(() => {
    if (browser) {
        const params = $page.url.searchParams;

        // Tab
        const tabParam = params.get('tab');
        if (tabParam === 'static' || tabParam === 'brim') {
            activeTab = tabParam;
        }

        // Broker IDs
        const brokerParam = params.get('broker_id');
        if (brokerParam) {
            selectedBrokerIds = brokerParam.split(',').map(Number).filter(n => !isNaN(n));
        }

        // Status
        const statusParam = params.get('status');
        if (statusParam) {
            selectedStatuses = statusParam.split(',');
        }

        // Search
        const searchParam = params.get('search');
        if (searchParam) {
            searchQuery = searchParam;
        }
    }
});

// Update URL when filters change (without page reload)
function updateUrlParams() {
    if (!browser) return;

    const params = new URLSearchParams();

    if (activeTab !== 'static') {
        params.set('tab', activeTab);
    }
    if (selectedBrokerIds.length > 0) {
        params.set('broker_id', selectedBrokerIds.join(','));
    }
    if (selectedStatuses.length > 0) {
        params.set('status', selectedStatuses.join(','));
    }
    if (searchQuery) {
        params.set('search', searchQuery);
    }

    const newUrl = params.toString() ? `?${params.toString()}` : '/files';
    goto(newUrl, {replaceState: true, noScroll: true});
}

// Call updateUrlParams when filters change
$: if (browser) {
    updateUrlParams();
}
```

### 2.3 Modifiche a BrokerImportFiles "Manage all files" Link

```svelte
<!-- In BrokerImportFiles.svelte -->
<a 
    href="/files?tab=brim&broker_id={brokerId}" 
    class="text-sm text-libre-green hover:underline"
>
    {$_('brokers.manageFiles')}
</a>
```

---

## 🔧 Step 3: Import Files UX Refactoring (2h)

### 3.1 Nuovo Componente: `BrokerImportFilesModal.svelte`

Sostituisce la sezione inline con una modale.

**Props:**

```typescript
interface Props {
    brokerId: number;
    brokerName: string;
    isOpen: boolean;
    onClose: () => void;
}
```

**Struttura:**

```svelte
<script lang="ts">
    import { _ } from '$lib/i18n';
    import { X, FileUp, ExternalLink } from 'lucide-svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import ConfirmModal from '$lib/components/table/ConfirmModal.svelte';
    import FileUploader from '$lib/components/FileUploader.svelte';
    
    // ... state management
</script>

{#if isOpen}
<div class="modal-backdrop" onclick={onClose}>
    <div class="modal-content" onclick|stopPropagation>
        <!-- Header -->
        <div class="modal-header">
            <h2>{$_('brokers.importFiles')} - {brokerName}</h2>
            <button onclick={onClose}><X size={20}/></button>
        </div>
        
        <!-- Upload Area (collapsible) -->
        <div class="upload-section">
            <FileUploader 
                accept=".csv,.xlsx,.xls"
                onUpload={handleUpload}
                brokerId={brokerId}
            />
        </div>
        
        <!-- Files Table -->
        <DataTable 
            data={files}
            columns={columns}
            onDelete={handleDelete}
        />
        
        <!-- Footer -->
        <div class="modal-footer">
            <a href="/files?tab=brim&broker_id={brokerId}">
                <ExternalLink size={14}/>
                {$_('brokers.manageFiles')}
            </a>
        </div>
    </div>
</div>
{/if}

<!-- Delete Confirmation -->
<ConfirmModal
    isOpen={deleteConfirmOpen}
    title={$_('common.confirmDelete')}
    message={$_('uploads.deleteConfirmMessage')}
    onConfirm={confirmDelete}
    onCancel={() => deleteConfirmOpen = false}
/>
```

### 3.2 Colonne DataTable per Files

```typescript
const columns = [
    {
        key: 'filename',
        label: $_('uploads.fileName'),
        type: 'text' as const,
        sortable: true,
        render: (file) => ({
            icon: getFileIcon(file.filename),
            text: file.filename
        })
    },
    {
        key: 'size_bytes',
        label: $_('uploads.fileSize'),
        type: 'size' as const,
        sortable: true
    },
    {
        key: 'status',
        label: $_('uploads.status'),
        type: 'enum' as const,
        sortable: true,
        enumOptions: [
            {value: 'uploaded', label: $_('fileStatus.uploaded')},
            {value: 'parsed', label: $_('fileStatus.parsed')},
            {value: 'failed', label: $_('fileStatus.failed')}
        ]
    },
    {
        key: 'uploaded_at',
        label: $_('uploads.uploadDate'),
        type: 'date' as const,
        sortable: true
    }
];
```

### 3.3 Modifiche a Broker Detail Page

```svelte
<!-- In /brokers/[id]/+page.svelte -->
<script>
    let importFilesModalOpen = false;
</script>

<!-- Header buttons -->
<button onclick={() => importFilesModalOpen = true}>
    <FileUp size={16}/>
    {$_('brokers.importFiles')}
</button>

<!-- Modal -->
<BrokerImportFilesModal
    brokerId={broker.id}
    brokerName={broker.name}
    isOpen={importFilesModalOpen}
    onClose={() => importFilesModalOpen = false}
/>
```

### 3.4 Upload Auto-Assign Broker

Nel componente FileUploader/BrokerImportFilesModal, quando `brokerId` è passato:

- Non mostrare BrokerSelect
- Usare direttamente `brokerId` nell'upload
- Messaggio conferma: "File will be assigned to {brokerName}"

---

## 📝 Traduzioni Necessarie

```json
{
  "uploads": {
    "deleteConfirmMessage": "Are you sure you want to delete this file? This action cannot be undone.",
    "fileWillBeAssigned": "File will be assigned to {broker}"
  }
}
```

---

## ✅ Checklist Implementazione

### Step 2: URL Filters

- [ ] Leggere params da URL in `onMount`
- [ ] Funzione `updateUrlParams()` che aggiorna URL senza reload
- [ ] Reactive statement che chiama `updateUrlParams` quando cambiano filtri
- [ ] Test: aprire `/files?tab=brim&broker_id=1` → filtri applicati
- [ ] Test: cambiare filtri → URL si aggiorna

### Step 3: Import Files Modal

- [ ] Creare `BrokerImportFilesModal.svelte`
- [ ] Rimuovere sezione inline da broker detail
- [ ] Aggiungere button per aprire modale
- [ ] Integrare DataTable nel modale
- [ ] Sostituire `confirm()` con ConfirmModal
- [ ] Test: upload file → appare in tabella
- [ ] Test: delete → modale conferma → file rimosso
- [ ] Test: "Manage all files" → naviga a `/files?tab=brim&broker_id=X`

---

## 🔗 Dipendenze

- `DataTable.svelte` - già esistente ✅
- `ConfirmModal.svelte` - già esistente ✅
- `FileUploader.svelte` - già esistente ✅
- Traduzioni - da aggiungere

---

## 📚 File Coinvolti

| File                                               | Modifiche                      |
|----------------------------------------------------|--------------------------------|
| `routes/(app)/files/+page.svelte`                  | URL params sync                |
| `routes/(app)/brokers/[id]/+page.svelte`           | Button modale, rimuovi sezione |
| `components/brokers/BrokerImportFilesModal.svelte` | NUOVO                          |
| `components/brokers/BrokerImportFiles.svelte`      | DA RIMUOVERE o refactor        |
| `i18n/*.json`                                      | Nuove traduzioni               |
