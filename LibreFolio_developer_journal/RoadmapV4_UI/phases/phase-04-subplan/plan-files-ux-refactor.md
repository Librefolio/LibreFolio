# Plan: Files Page UX Refactoring + URL Deep-Linking

**Data creazione**: 30 Gennaio 2026  
**Status**: ✅ COMPLETATO  
**Priorità**: P1  
**Stima**: 3h totali (Step 2: 1h ✅, Step 3: 1h ✅)
**Completato**: 2 Febbraio 2026

### Note Finali

Durante l'implementazione è stato necessario:

- Aggiungere un custom `paramsSerializer` in `zodios-client.ts` per serializzare gli array come `key=1&key=2` invece di `key[]=1` (formato atteso da FastAPI)
- Sostituire tutte le chiamate `fetch()` dirette con il client Zodios tipizzato

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

### 2.1 Sistema URL Filters Dinamico

**Obiettivo**: Permettere deep-linking a qualsiasi combinazione di filtri tramite URL. Il sistema deve essere **dinamico** e funzionare con qualsiasi colonna DataTable, non
hardcoded per un sottoinsieme specifico.

**Principi**:

1. Ogni colonna ha una `urlKey` per il mapping URL ↔ stato filtro
2. I valori ammessi nell'URL sono gli stessi dei filtri della tabella
3. Se una key non viene trovata nelle colonne, viene ignorata e rimossa dall'URL
4. Il sistema parsa `key=value` e inizializza i filtri di conseguenza

**URL Format**:

```
/files?tab=brim&filename=report&broker=1,2&status=uploaded,parsed&size=1000-50000&date=2026-01-01,2026-01-31
```

**Mapping Colonne ↔ URL Keys**:

| Colonna    | URL Key    | Tipo    | Formato Valori URL           |
|------------|------------|---------|------------------------------|
| `filename` | `filename` | text    | Stringa (search query)       |
| `broker`   | `broker`   | enum    | IDs comma-separated: `1,2,3` |
| `status`   | `status`   | enum    | Values comma-separated       |
| `size`     | `size`     | size    | `min-max` in bytes           |
| `date`     | `date`     | date    | `start,end` ISO format       |
| N/A        | `tab`      | special | `static` \| `brim`           |

### 2.2 Implementazione in FilesTable

Ogni `ColumnDef` avrà un campo opzionale `urlKey`:

```typescript
interface ColumnDef<T> {
    // ...existing fields...
    urlKey?: string;  // Key per URL params (default: column id)
}
```

### 2.3 Utility Functions per URL Sync

```typescript
// In $lib/utils/urlFilters.ts

export interface UrlFilterConfig {
    urlKey: string;
    type: 'text' | 'enum' | 'size' | 'date';
}

/**
 * Parse URL params into filter state.
 * Unknown keys are ignored.
 */
export function parseUrlFilters(
    searchParams: URLSearchParams,
    columns: UrlFilterConfig[]
): Map<string, any> {
    const filters = new Map<string, any>();
    const validKeys = new Set(columns.map(c => c.urlKey));
    
    for (const [key, value] of searchParams.entries()) {
        if (!validKeys.has(key)) continue;  // Ignore unknown keys
        
        const col = columns.find(c => c.urlKey === key);
        if (!col) continue;
        
        switch (col.type) {
            case 'text':
                filters.set(key, value);
                break;
            case 'enum':
                filters.set(key, value.split(',').filter(v => v));
                break;
            case 'size':
                const [min, max] = value.split('-').map(Number);
                filters.set(key, { min: min || 0, max: max || Infinity });
                break;
            case 'date':
                const [start, end] = value.split(',');
                filters.set(key, { start, end });
                break;
        }
    }
    
    return filters;
}

/**
 * Build URL params from filter state.
 * Only includes non-default values.
 */
export function buildUrlFilters(
    filters: Map<string, any>,
    columns: UrlFilterConfig[]
): URLSearchParams {
    const params = new URLSearchParams();
    
    for (const col of columns) {
        const value = filters.get(col.urlKey);
        if (value === undefined || value === null || value === '') continue;
        
        switch (col.type) {
            case 'text':
                if (value) params.set(col.urlKey, value);
                break;
            case 'enum':
                if (Array.isArray(value) && value.length > 0) {
                    params.set(col.urlKey, value.join(','));
                }
                break;
            case 'size':
                if (value.min > 0 || value.max < Infinity) {
                    params.set(col.urlKey, `${value.min}-${value.max === Infinity ? '' : value.max}`);
                }
                break;
            case 'date':
                if (value.start || value.end) {
                    params.set(col.urlKey, `${value.start || ''},${value.end || ''}`);
                }
                break;
        }
    }
    
    return params;
}
```

### 2.4 Modifiche a `/files/+page.svelte`

```typescript
import { page } from '$app/stores';
import { goto } from '$app/navigation';
import { browser } from '$app/environment';
import { parseUrlFilters, buildUrlFilters, type UrlFilterConfig } from '$lib/utils/urlFilters';

// Define URL-filterable columns
const urlFilterColumns: UrlFilterConfig[] = [
    { urlKey: 'filename', type: 'text' },
    { urlKey: 'broker', type: 'enum' },
    { urlKey: 'status', type: 'enum' },
    { urlKey: 'size', type: 'size' },
    { urlKey: 'date', type: 'date' },
];

// Reference to FilesTable for filter sync
let filesTableRef: FilesTable;

onMount(() => {
    if (browser) {
        const params = $page.url.searchParams;
        
        // Special handling for tab
        const tabParam = params.get('tab');
        if (tabParam === 'static' || tabParam === 'brim') {
            activeTab = tabParam;
        }
        
        // Parse column filters
        const filters = parseUrlFilters(params, urlFilterColumns);
        
        // Apply filters to FilesTable (will be set via bind)
        if (filesTableRef) {
            filesTableRef.setFiltersFromUrl(filters);
        }
    }
});

// Update URL when filters change (called by FilesTable)
function handleFiltersChanged(event: CustomEvent<Map<string, any>>) {
    if (!browser) return;
    
    const params = buildUrlFilters(event.detail, urlFilterColumns);
    
    // Add tab if not default
    if (activeTab !== 'static') {
        params.set('tab', activeTab);
    }
    
    const newUrl = params.toString() ? `/files?${params.toString()}` : '/files';
    goto(newUrl, { replaceState: true, noScroll: true });
}
```

**FilesTable Integration**:

```svelte
<FilesTable
    bind:this={filesTableRef}
    files={activeTab === 'static' ? staticFiles : brimFiles}
    type={activeTab}
    onDelete={handleDelete}
    onFiltersChanged={handleFiltersChanged}
    urlFilterColumns={urlFilterColumns}
/>
```);

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

### Step 2: URL Filters ✅

- [x] Creare `$lib/utils/urlFilters.ts` con utility per parsing/building URL params
- [x] Aggiungere `urlKey` a `ColumnDef` in types.ts
- [x] Aggiungere `initialFilters` e `onFiltersChange` props a DataTable
- [x] Aggiungere props a FilesTable e propagare a DataTable
- [x] Leggere params da URL in `onMount` nella pagina files
- [x] Funzione `handleFiltersChange()` che aggiorna URL senza reload
- [x] Funzione `setActiveTab()` che aggiorna URL e pulisce filtri tab-specific
- [x] **Fix**: Tab sempre presente in URL (anche `static`) per copia/incolla
- [x] **Fix**: Usare `history.replaceState` invece di `goto` per preservare focus input
- [x] **Fix**: Supporto matchMode in URL per filtri testo (formato: `value:matchMode`)
- [x] **Fix**: Non pulire filtri al cambio tab (utente può farlo manualmente)
- [x] Test: aprire `/files?tab=brim&broker=1` → filtri applicati ✅
- [x] Test: cambiare filtri → URL si aggiorna ✅

### Step 3: Import Files Modal ✅

- [x] Creare `BrokerImportFilesModal.svelte` con DataTable integrato
- [x] Filtrare solo i file del broker corrente (fix: uso fetch con formato `broker_ids=X`)
- [x] Nascondere colonna broker (prop `showBrokerColumn={false}`)
- [x] Upload file auto-assegnati al broker corrente
- [x] Rimuovere sezione inline `BrokerImportFiles` da broker detail
- [x] Aggiungere bottone per aprire modale (spostato tra Broker Info e Transactions)
- [x] Link "Gestisci tutti i file" in header a destra
- [x] Bottoni Refresh/Upload in footer a destra
- [x] Bottone Upload diventa grigio quando uploader è aperto
- [x] Conferma chiusura con file pending (click X, backdrop, ESC)
- [x] Modale conferma stile warning (non danger)
- [x] Traduzioni: `common.refresh`, `uploads.pendingUploads`, etc.

---

## 🔗 Dipendenze

- `DataTable.svelte` - già esistente ✅
- `ConfirmModal.svelte` - già esistente ✅
- `FileUploader.svelte` - già esistente ✅
- Traduzioni - da aggiungere

---

## 📚 File Coinvolti

| File                                               | Modifiche                                    |
|----------------------------------------------------|----------------------------------------------|
| `routes/(app)/files/+page.svelte`                  | URL params sync ✅                            |
| `routes/(app)/brokers/[id]/+page.svelte`           | Button modale, rimuovi sezione inline ✅      |
| `components/brokers/BrokerImportFilesModal.svelte` | NUOVO - Modale con DataTable ✅               |
| `components/brokers/BrokerImportFiles.svelte`      | Migliorato ma non più usato in broker detail |
| `components/files/FilesTable.svelte`               | Aggiunto urlKey alle colonne ✅               |
| `components/table/DataTable.svelte`                | Props initialFilters, onFiltersChange ✅      |
| `components/table/types.ts`                        | Aggiunto urlKey a ColumnDef ✅                |
| `lib/utils/urlFilters.ts`                          | NUOVO - Utility parse/build URL filters ✅    |
