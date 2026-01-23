# Piano: Migliorie Tabelle Files con TanStack Table

**Data**: 21 Gennaio 2026  
**Aggiornamento**: 23 Gennaio 2026  
**Status**: ✅ COMPLETATO - Tutte le feature principali implementate  
**Libreria**: TanStack Table v8 (`@tanstack/table-core`) + Adapter Custom Svelte 5

---

## Contesto

Le tabelle in `/files` (Static Resources e BRIM Reports) necessitano di miglioramenti significativi per UX e funzionalità.

### Alternative Valutate

Sono state valutate diverse librerie:
- **Svelte-Simple-Datatables**: Leggera ma feature limitate
- **ag-Grid Community**: Enterprise-grade ma overkill (~500KB)
- **Native Custom**: Zero dipendenze ma richiede implementazione completa
- **@tanstack/svelte-table v9 alpha**: Supporto Svelte 5 ma in alpha, non stabile

**Scelta finale: TanStack Table v8 con adapter custom** per stabilità e compatibilità con Svelte 5.

> **NOTA**: Quando TanStack Table v9 sarà stabile con supporto ufficiale Svelte 5, 
> migrare all'adapter ufficiale. Vedi `TODO_FUTURI.md` nella root del progetto.

---

## ✅ Completato (22 Gennaio 2026)

### Fase 1: Setup e Componente Base

- [x] Installato `@tanstack/table-core@^8.21.3` (stabile, non alpha)
- [x] Creato adapter custom in `frontend/src/lib/tanstack-table/`:
  - `createSvelteTable.svelte.ts` - Factory reattivo per Svelte 5
  - `FlexRender.svelte` - Helper per rendering celle
  - `DataTable.svelte` - Componente UI con sorting e pagination
  - `index.ts` - Re-export delle API core
- [x] Build verificata senza errori
- [x] Documentato in `TODO_FUTURI.md` la migrazione futura a v9

---

## Problemi Attuali

### Static Resources
- ❌ Nessuna icona per tipi file (PNG, TXT, etc.)
- ❌ Nessuna paginazione
- ❌ Nessun controllo elementi per pagina
- ❌ Nessun sorting
- ❌ Nessun filtering
- ❌ Delete senza conferma elegante (usa alert())

### BRIM Reports  
- ✅ Icone corrette per CSV
- ❌ Nessuna paginazione
- ❌ Nessun sorting/filtering

---

## Piano di Implementazione

### ✅ Fase 1: Setup e Componente Base (COMPLETATA - 22/01/2026)

- [x] Installato `@tanstack/table-core@^8.21.3` (stabile)
- [x] Creato adapter custom Svelte 5 in `$lib/tanstack-table/`
- [x] Componente `DataTable.svelte` con:
  - Props: `data`, `columns`, `pageSize`, `enableSorting`, `enablePagination`
  - Headless UI con styling Tailwind
  - Dark mode support
  - Sorting base implementato
  - Pagination base implementata

### ✅ Fase 2: Integrazione in Files Page (COMPLETATA - 22/01/2026)

- [x] Creato componente `FilesTable.svelte` in `$lib/components/files/`
- [x] Integrato nella list view di Static Resources
- [x] Integrato nella tabella BRIM Reports
- [x] Sorting funzionante su tutte le colonne
- [x] Pagination con selettore page size (10, 25, 50, 100)
- [x] Icone file per tipo (Image, CSV, Text, Generic)
- [x] Status badge per BRIM files
- [x] Rimosso CSS duplicato dalla pagina principale
- [x] Build verificata senza errori

### ✅ Fase 3: Features Avanzate (COMPLETATA - 22/01/2026)

**Richieste utente 22/01/2026 - Round 1:**

1. **Status tradotto** ✅
   - [x] Aggiunta traduzione per status BRIM (uploaded, parsed, failed, etc.)
   - [x] Traduzioni in EN, IT, FR, ES

2. **Pagination migliorata** ✅
   - [x] Selettore pagina numerico (input diretto)
   - [x] Page size: solo numeri nel dropdown
   - [x] Aggiunta opzione "∞" (illimitato/tutti)

3. **Colonne ridimensionabili** ✅
   - [x] Drag-to-resize delle colonne
   - [x] Salvataggio larghezze in localStorage

4. **Column visibility** ✅
   - [x] Dropdown "Show/Hide Columns" in toolbar
   - [x] Salvataggio preferenze in localStorage
   - [x] Reset ai default

5. **Pagination sticky/floating** ✅
   - [x] Controlli pagination sempre visibili (fixed bottom)
   - [x] Scroll permette di vedere oltre l'ultimo file

6. **Row selection** ✅
   - [x] Checkbox per selezione multipla
   - [x] Select all / Deselect all in header
   - [x] Contatore items selezionati
   - [x] Azione bulk delete

7. **View mode persistente** ✅
   - [x] Salvataggio grid/list in localStorage
   - [x] Default: list (tabella)

**Richieste utente 22/01/2026 - Round 2:**

8. **Selection visual feedback** ✅
   - [x] Righe selezionate con background blu chiaro
   - [x] Checkbox con icona Check invece di checkbox HTML
   - [x] Select All seleziona solo pagina corrente (e resetta selezioni precedenti)

9. **Bulk actions uniformate** ✅
   - [x] Stesse icone delle azioni singole (Download, Trash)
   - [x] Solo icone, testo come tooltip
   - [x] Delete in rosso per tutti
   - [x] Fix: bulk actions ora funzionano correttamente

10. **Resize handle visibile** ✅
    - [x] Handle visibile su hover della colonna
    - [x] Colore blu durante resize

11. **Colonne fisse** ✅
    - [x] Selezione (sticky left) - sempre
    - [x] Azioni (sticky right) - solo desktop (>768px)

12. **Pagination floating** ✅
    - [x] Pill centrata rispetto al container tabella
    - [x] Page numbers cliccabili
    - [x] Input editabile per pagina corrente
    - [x] Ellipsis semplici (editare pagina corrente è più comodo)
    - [x] Fix: page size e navigazione funzionano

13. **Column dropdown migliorato** ✅
    - [x] Icone Eye/EyeOff invece di checkbox
    - [x] GripVertical per drag (preparato per reorder futuro)
    - [x] Reset sotto con icona RotateCcw
    - [x] Fix: dropdown rimane aperto quando si togglea colonna

14. **Search** ✅
    - [x] Search box nel toolbar (sempre visibile)
    - [x] Filtra per nome file
    - [x] Clear button (X)

15. **Delete Confirmation Modal** ✅
    - [x] Modale invece di confirm browser
    - [x] Lista file foldabile per delete multiplo
    - [x] Traduzioni EN/IT/FR/ES
    - [x] Modale centrata rispetto all'area di lavoro

16. **Selezione persistente** ✅
    - [x] Selezione mantenuta tra pagine
    - [x] Selezione mantenuta cambiando page size

17. **Pagination balloon** ✅
    - [x] Sticky bottom con spazio dal bordo
    - [x] Segue lo scroll della finestra

**Componente:** `FilesTableAdvanced.svelte` (v2)
- Paginazione custom (non dipende da TanStack)
- Storage keys separati per tipo (static vs brim)

---

### ✅ Fase 3.5: Componentizzazione DataTable (COMPLETATA - 23/01/2026)

**Obiettivo**: Creare un componente `DataTable.svelte` generico e riusabile

**Motivazione**: 
- La tabella verrà riusata in `/brokers/{id}`, `/transactions`, `/assets`, ecc.
- Il design attuale piace, non vogliamo reinventare la ruota
- `FilesTableAdvanced` è troppo specifico per i file

**Struttura implementata**:

```
src/lib/components/table/
├── DataTable.svelte           # ✅ Componente principale generico
├── DataTablePagination.svelte # ✅ Pagination balloon (sticky)
├── DataTableToolbar.svelte    # ✅ Bulk actions + column toggle + reorder
├── DataTableColumnFilter.svelte # ✅ Filtro singola colonna (imbuto Excel)
├── ConfirmModal.svelte        # ✅ Modale conferma generica
└── types.ts                   # ✅ TypeScript interfaces
```

> **NOTA**: Il search globale NON ci sarà. Il filtro per nome sarà il filtro Excel della colonna "nome".

---

#### 3.5.1 Sistema Colonne Configurabili

Le colonne sono completamente controllate dall'utilizzatore, incluso:
- Ordine delle colonne
- Contenuto e tipo di rendering
- Filtri disponibili per colonna
- Sorting abilitato/disabilitato per colonna

**ColumnDef Interface**:
```typescript
interface ColumnDef<T> {
    id: string;
    header: string | (() => string);  // Label o funzione per i18n
    
    // Rendering
    cell: (row: T) => CellContent;    // Contenuto cella
    
    // Tipo di dato (determina filtro e sort)
    type: 'text' | 'number' | 'date' | 'enum' | 'custom';
    
    // Per tipo 'enum': opzioni disponibili
    enumOptions?: { value: string; label: string }[];
    
    // Comportamento
    sortable?: boolean;               // Default: true
    filterable?: boolean;             // Default: true
    resizable?: boolean;              // Default: true
    
    // Larghezza
    width?: number;                   // Larghezza iniziale in px
    minWidth?: number;                // Larghezza minima
    maxWidth?: number;                // Larghezza massima
}

// Contenuto cella flessibile
type CellContent = 
    | string 
    | number 
    | { type: 'icon-text'; icon: Component; text: string }
    | { type: 'badge'; text: string; variant: string }
    | { type: 'date'; value: Date; format?: string }
    | { type: 'size'; bytes: number }
    | { type: 'link'; text: string; href: string }
    | { type: 'custom'; component: Component; props: Record<string, any> };
```

**Esempio uso per Transactions**:
```typescript
const transactionColumns: ColumnDef<Transaction>[] = [
    {
        id: 'type',
        header: () => $t('transactions.type'),
        cell: (row) => ({ 
            type: 'icon-text', 
            icon: getTransactionIcon(row.type),  // BUY/SELL/DIV icon
            text: row.type 
        }),
        type: 'enum',
        enumOptions: [
            { value: 'BUY', label: 'Buy' },
            { value: 'SELL', label: 'Sell' },
            { value: 'DIVIDEND', label: 'Dividend' },
        ],
        width: 120,
    },
    {
        id: 'asset',
        header: () => $t('transactions.asset'),
        cell: (row) => ({
            type: 'icon-text',
            icon: getAssetIcon(row.asset),
            text: row.asset.name
        }),
        type: 'text',
        width: 200,
    },
    {
        id: 'date',
        header: () => $t('transactions.date'),
        cell: (row) => ({ type: 'date', value: row.date }),
        type: 'date',
        width: 120,
    },
    // ... altre colonne
];
```

---

#### 3.5.2 Colonne Fisse (Select e Actions)

Le colonne di selezione e azioni sono **separate** dalle colonne dati e hanno larghezza **percentuale fissa**:

```typescript
interface DataTableProps<T> {
    // ... altre props ...
    
    // Colonne speciali
    enableSelection?: boolean;        // Mostra colonna checkbox (default: true)
    selectionColumnWidth?: string;    // Default: '5%'
    
    enableActions?: boolean;          // Mostra colonna azioni (default: true)
    actionsColumnWidth?: string;      // Default: '10%'
    
    // Azioni - passate dall'utilizzatore
    rowActions?: RowAction<T>[];      // Azioni su singola riga
    bulkActions?: BulkAction<T>[];    // Azioni su selezione multipla
}

interface RowAction<T> {
    id: string;
    icon: Component;
    label: string | (() => string);
    onClick: (row: T) => void | Promise<void>;
    variant?: 'default' | 'danger';
    visible?: (row: T) => boolean;    // Condizionale
}

interface BulkAction<T> {
    id: string;
    icon: Component;
    label: string | (() => string);
    onClick: (rows: T[]) => void | Promise<void>;
    variant?: 'default' | 'danger';
    requireConfirm?: boolean;         // Mostra modale conferma
    confirmMessage?: string | ((count: number) => string);
}
```

**Layout colonne**:
```
| Select (5%) | Col1 | Col2 | Col3 | ... | Actions (10%) |
```

Le colonne dati si ridistribuiscono nel restante 85%.

---

#### 3.5.3 Props Complete DataTable

```typescript
interface DataTableProps<T> {
    // Dati
    data: T[];
    columns: ColumnDef<T>[];
    getRowId: (row: T) => string;
    
    // Storage
    storageKey: string;               // Per persistenza preferenze
    
    // Selezione
    enableSelection?: boolean;
    selectionColumnWidth?: string;
    onSelectionChange?: (selectedIds: string[]) => void;
    
    // Azioni
    enableActions?: boolean;
    actionsColumnWidth?: string;
    rowActions?: RowAction<T>[];
    bulkActions?: BulkAction<T>[];
    
    // Features
    enableSorting?: boolean;          // Default: true
    enableColumnFilters?: boolean;    // Default: true (filtri Excel)
    enableColumnResize?: boolean;     // Default: true
    enableColumnReorder?: boolean;    // Default: false (futuro)
    enablePagination?: boolean;       // Default: true
    
    // Pagination
    defaultPageSize?: number;         // Default: 10
    pageSizeOptions?: number[];       // Default: [10, 25, 50, 100, 0]
    
    // Stile
    emptyMessage?: string;
    loadingMessage?: string;
    isLoading?: boolean;
}
```

---

#### 3.5.4 Migrazione

1. Creare struttura `src/lib/components/table/`
2. Implementare `DataTable.svelte` con tutte le features
3. Creare `FilesTable.svelte` come wrapper che usa `DataTable`:
   ```svelte
   <DataTable
       data={files}
       columns={fileColumns}
       getRowId={(f) => f.id || f.file_id}
       storageKey="filesTable_{type}"
       rowActions={[
           { id: 'download', icon: Download, onClick: handleDownload },
           { id: 'delete', icon: Trash2, onClick: handleDelete, variant: 'danger' },
       ]}
       bulkActions={[
           { id: 'download', icon: Download, onClick: handleBulkDownload },
           { id: 'delete', icon: Trash2, onClick: handleBulkDelete, variant: 'danger', requireConfirm: true },
       ]}
   />
   ```
4. Testare con i 2 tab esistenti (static/brim)
5. Rimuovere `FilesTableAdvanced.svelte` dopo migrazione

---

### ✅ Fase 3.6: Estetica e Comportamento Tabella (COMPLETATA - 23/01/2026)

> Completata insieme alla fase 3.5 durante la componentizzazione.

#### 3.6.1 Estetica (durante componentizzazione)

**Sorting Colonne**:
- [x] Click su header per sort ASC/DESC/none
- [x] Icona freccia su/giù nell'header
- [ ] Multi-column sort (Shift+click) - opzionale/futuro

**Filtri Colonna Stile Excel**:
- [x] Icona imbuto nell'header colonna (se filterable)
- [x] Click apre popover con filtro appropriato al tipo:
  - **text**: input testo + modalità (contains/starts/ends/equals)
  - **enum**: checkbox multiple con opzioni + select all/clear all
  - **number**: range min-max
  - **size**: range min-max con slider logaritmico e unità (B/KB/MB/GB)
  - **date**: date range picker
- [x] Imbuto pieno = filtro attivo, icona reset per rimuovere

**Column Resize**:
- [x] Colonne select/actions: larghezza fissa (non ridimensionabili)
- [x] Colonne dati: ridimensionabili con drag
- [x] Rispetto minWidth/maxWidth da ColumnDef
- [x] Larghezze salvate in localStorage

**Column Reorder**:
- [x] Drag & drop nel dropdown "Show Columns" per riordinare
- [x] Grip handle visibile
- [x] Bottoni su/giù su mobile
- [x] Ordine salvato in localStorage

#### 3.6.2 Comportamento (passato dall'utilizzatore)

Le azioni sono **completamente gestite dall'utilizzatore** tramite props:

- `rowActions`: Array di azioni per singola riga
- `bulkActions`: Array di azioni per selezione multipla
- Ogni azione ha il proprio `onClick` handler
- La tabella gestisce solo:
  - Rendering bottoni/icone
  - Modale conferma (se `requireConfirm: true`)
  - Passaggio dati all'handler

**Esempio azioni Files**:
```typescript
const fileRowActions: RowAction<FileData>[] = [
    {
        id: 'download',
        icon: Download,
        label: () => $t('uploads.download'),
        onClick: async (file) => {
            const link = document.createElement('a');
            link.href = getDownloadUrl(file);
            link.download = file.filename;
            link.click();
        },
    },
    {
        id: 'delete',
        icon: Trash2,
        label: () => $t('common.delete'),
        onClick: async (file) => {
            await api.delete(`/uploads/${file.id}`);
            await loadFiles();
        },
        variant: 'danger',
    },
];

const fileBulkActions: BulkAction<FileData>[] = [
    {
        id: 'download',
        icon: Download,
        label: () => $t('uploads.download'),
        onClick: async (files) => {
            // Download sequenziale o ZIP
            for (const file of files) {
                await downloadFile(file);
            }
        },
    },
    {
        id: 'delete',
        icon: Trash2,
        label: () => $t('common.delete'),
        onClick: async (files) => {
            for (const file of files) {
                await api.delete(`/uploads/${file.id}`);
            }
            await loadFiles();
        },
        variant: 'danger',
        requireConfirm: true,
        confirmMessage: (count) => $t('uploads.deleteConfirmMultiple', { count }),
    },
];
```

---

### 📋 Fase 3.7: Features Aggiuntive (POST-componentizzazione e responsabilità delle pagine utilizzatrici del componente)

**1. Download Multiplo ZIP** (Priorità MEDIA)
- [ ] Seleziona multipli file → download come ZIP
- [ ] Richiede libreria JS (JSZip) o endpoint backend
- [ ] Progress indicator durante creazione ZIP

**2. Export Tabella** (Priorità BASSA)
- [ ] Export CSV dei dati visualizzati
- [ ] Export con filtri applicati

**3. Preview File** (Priorità BASSA)
- [ ] Preview testo con syntax highlighting
- [ ] Preview immagini con lightbox
- [ ] Preview PDF inline

---

### 📋 Fase 4: BRIM Multi-User Support

**Piano dettagliato**: `plan-brim-multiuser-implementation.md`  
**Analisi**: `analysis-brim-multiuser.md`

**Riepilogo modifiche**:
- Backend: broker_id obbligatorio all'upload, filtri per broker, caching parse result
- Frontend: filtro multi-broker, colonna broker, upload con selezione broker

**Stima**: ~8-13h totali

---

## Riferimenti

- TanStack Table v8 Core: https://tanstack.com/table/v8
- Adapter Svelte 5 custom in `$lib/tanstack-table/`
- Issue tracking: vedere file in `LibreFolio_developer_journal/`

---

## ✅ Fix Completati (23 Gennaio 2026 - Pomeriggio)

### Problemi risolti:

1. **Traduzione "Status" mancante** ✅
   - Aggiunta chiave `uploads.status` in EN/IT/FR/ES

2. **Colonna "Actions" in maiuscolo** ✅
   - Aggiunto `text-transform: none !important` su `.th-actions`

3. **Pagination scompare quando pageSize > righe** ✅
   - Modificata condizione: ora mostra sempre se `filteredData.length > 0`

4. **Delete singolo senza conferma** ✅
   - Aggiunto `requireConfirm` e `confirmMessage` a `RowAction<T>`
   - Implementata modale conferma per azioni singole in DataTable
   - FilesTable ora richiede conferma per delete singolo

5. **Filtri si chiudono durante digitazione** ✅
   - Rimosso `openFilterColumnId = null` da `applyColumnFilter()`
   - Il filtro ora resta aperto fino a click outside

6. **Settings Preferences non carica default globali** ✅
   - Corretto parsing risposta API `/settings/global`
   - L'API restituisce array `{ settings: [{ key, value }...] }`
   - Convertito in oggetto per accesso diretto

---

## 📋 TESTLIST UI v2 - 23 Gennaio 2026

### 1. Visualizzazione Base
- [x] Tabella renderizzata con dati
- [x] Colonne hanno nomi tradotti (incluso "Status")
- [x] Colonna "Actions" con solo iniziale maiuscola
- [x] Header sottile

### 2. Sorting
- [x] Click header → ASC → DESC → nessuno
- [x] Freccia visibile nell'header

### 3. Pagination
- [x] Balloon sempre visibile (anche con pochi dati)
- [x] Page size funziona (10, 25, 50, 100, ∞)
- [x] Numeri pagina cliccabili
- [x] Input pagina editabile
- [x] Traduzioni visibili

### 4. Selezione Righe
- [x] Checkbox su ogni riga
- [x] Select all seleziona pagina corrente
- [x] Contatore "N selezionati"
- [x] Righe selezionate con sfondo blu

### 5. Pulsanti Action (singola riga)
- [x] Icone Download e Delete visibili
- [x] Pulsanti con sfondo/bordo
- [x] Delete rosso
- [x] **DELETE SINGOLO mostra conferma**
- [x] **Modale delete singolo mostra nome file direttamente (no toggle)**

### 6. Bulk Actions
- [x] Appaiono con selezioni
- [x] Posizionate a destra
- [x] Delete multiplo mostra conferma
- [x] Modale mostra nomi file reali

### 7. Filtri Colonna
- [x] Icona imbuto visibile
- [x] Click apre popover
- [x] **Popover NON troncato dalla tabella** (min-height: 200px)
- [x] **Click fuori chiude il popover**
- [x] **Digitare NON chiude il popover**
- [x] Filtro testo si applica con debounce
- [x] Filtro enum: click singoli funziona
- [x] Reset pulisce il filtro
- [x] Imbuto colorato quando attivo

### 8. Show/Hide Columns
- [x] Icona occhio funziona
- [x] Toggle visibilità
- [x] Reset ripristina

### 9. Column Resize
- [x] Handle visibile su hover
- [x] Drag ridimensiona
- [x] Larghezza salvata
- [ ] **TODO:** Verificare comportamento con valori molto piccoli

### 10. Dark Mode
- [x] Tabella colori corretti
- [x] Filtri colori corretti
- [x] Modale colori corretti

### 11. Persistenza
- [x] Page size mantenuto
- [x] Colonne visibili mantenute
- [x] Larghezze mantenute
- [x] **Tab attivo memorizzato (static/brim)**

### 12. Settings Preferences
- [x] Cambia valuta in Global Settings (admin)
- [x] In User Preferences, Reset valuta
- [x] **Prende il valore da Global Settings**

---

## ✅ Fix Aggiuntivi (23 Gennaio 2026 - Sera)

1. **Altezza minima tabella** ✅
   - Aggiunto `min-height: 200px` su `.table-wrapper`
   - I filtri non vengono più troncati

2. **ConfirmModal lista singolo item** ✅
   - Se `items.length === 1`, la lista è sempre visibile
   - Il toggle appare solo se `items.length > 1`

---

## 🔧 PLAN: Column Resize Fix (23 Gennaio 2026)

### Problema Attuale
Il ridimensionamento delle colonne ha comportamenti inattesi:
- Le colonne hanno una larghezza minima implicita che impedisce di ridurle
- Il resize non è fluido
- Salvare e ripristinare le larghezze non funziona correttamente

### Alternative Analizzate

#### Opzione A: CSS table-layout fixed + width in px ⭐ PRIMA SCELTA
**Pro:**
- Controllo preciso delle larghezze
- Funziona con `table-layout: fixed`
- Larghezze salvabili in localStorage
- Minima riscrittura del codice esistente

**Contro:**
- Richiede gestire manualmente il resize di tutte le colonne
- La tabella non si adatta automaticamente al contenuto

#### Opzione D: ResizeObserver + CSS variables ⭐ FALLBACK
**Pro:**
- Moderno e performante
- Larghezze dinamiche via CSS vars
- Compatibile con table-layout fixed

**Contro:**
- Complessità implementativa maggiore
- Support browser (ok per moderni)

### ✅ Decisione: Opzione A - COMPLETATA (23 Gennaio 2026)

**Implementazione:**
1. ✅ minWidth default ridotto a 50px
2. ✅ maxWidth aumentato a 600px
3. ✅ CSS `td` con `white-space: nowrap`, `max-width: 0`, `overflow: hidden`
4. ✅ CSS `.td-data` con `word-break: break-word`
5. ✅ Larghezze salvate in localStorage

**File modificati:**
- `DataTable.svelte` - CSS e handleResize()

### Implementazione

```typescript
// Struttura state
let columnWidths: Record<string, number> = {};

// Default widths calculation
function calculateDefaultWidths() {
    const totalWidth = tableElement.offsetWidth;
    const fixedWidth = selectionWidth + actionsWidth;
    const availableWidth = totalWidth - fixedWidth;
    const perColumn = availableWidth / dataColumns.length;
    return Object.fromEntries(columns.map(c => [c.id, Math.max(perColumn, c.minWidth || 80)]));
}

// Resize handler
function handleResize(columnId: string, deltaX: number) {
    columnWidths[columnId] = Math.max(
        columns.find(c => c.id === columnId)?.minWidth || 50,
        columnWidths[columnId] + deltaX
    );
}
```

---

## 🔧 PLAN: Size Filter con Slider Logaritmico (23 Gennaio 2026)

### Requisiti
- Slider con scala logaritmica (base 10)
- Range: min file → max file della colonna
- Unità di misura dinamica (B, KB, MB, GB)
- Due handle (min e max)

### Layout ASCII Art - Soluzione Finale (C + A)

```
┌─────────────────────────────────────────────┐
│ FILTER                              [reset] │
├─────────────────────────────────────────────┤
│                                             │
│  Min: [___12___] [KB ▼]     (input + unità) │
│  Max: [___1.2__] [MB ▼]                     │
│                                             │
│  ├──●────────────────●──┤   (dual slider)   │
│  1B   10KB  100KB  1MB  10MB                │
│       └─── scala logaritmica ───┘           │
│                                             │
└─────────────────────────────────────────────┘
```

**Comportamento:**
- Modificare input → aggiorna slider
- Modificare slider → aggiorna input
- Dropdown unità: B, KB, MB, GB (auto-select in base al valore)

### Alternative UI

#### Opzione A: Dual Range Slider (solo slider)
```
  Min ──●─────────────────●── Max
       12KB              1.2MB
```
**Pro:** Compatto, intuitivo
**Contro:** Meno preciso per valori esatti

#### Opzione C: Input + Dropdown unità (solo input)
```
  Min: [___12___] [KB ▼]
  Max: [___1.2__] [MB ▼]
```
**Pro:** Precisione massima
**Contro:** Meno intuitivo per selezionare range visivamente

### ✅ Decisione: Opzione C + A - COMPLETATA (23 Gennaio 2026)

**Implementazione:**
- ✅ Input numerici con dropdown unità (B, KB, MB, GB)
- ✅ Dual range slider logaritmico
- ✅ Sincronizzazione bidirezionale (input ↔ slider)
- ✅ Min/Max calcolati automaticamente dai dati della colonna
- ✅ Nuovo tipo `ColumnType: 'size'`
- ✅ Nuovo tipo `SizeFilter` con `minBytes`/`maxBytes`
- ✅ Traduzioni aggiunte in EN/IT/FR/ES

**File modificati:**
- `types.ts` - aggiunto `'size'` a ColumnType, aggiunto `SizeFilter`
- `DataTableColumnFilter.svelte` - UI completa per size filter
- `DataTable.svelte` - gestione filtro size, calcolo min/max colonna
- `FilesTable.svelte` - colonna size usa `type: 'size'`
- `en.json`, `it.json`, `fr.json`, `es.json` - traduzioni

**Funzionalità:**
- Scala logaritmica per range file di dimensioni molto diverse
- Auto-conversione unità in base al valore
- Etichette min/max sotto lo slider
- Barra verde che evidenzia il range selezionato

### Implementazione

```typescript
// Conversione logaritmica
function toLogScale(bytes: number, minBytes: number, maxBytes: number): number {
    if (bytes <= 0) return 0;
    const logMin = Math.log10(Math.max(minBytes, 1));
    const logMax = Math.log10(Math.max(maxBytes, 1));
    const logVal = Math.log10(bytes);
    return (logVal - logMin) / (logMax - logMin) * 100;
}

function fromLogScale(percent: number, minBytes: number, maxBytes: number): number {
    const logMin = Math.log10(Math.max(minBytes, 1));
    const logMax = Math.log10(Math.max(maxBytes, 1));
    const logVal = logMin + (percent / 100) * (logMax - logMin);
    return Math.round(Math.pow(10, logVal));
}

// Format display
function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
}
```

---

## 🔧 PLAN: Column Reordering (23 Gennaio 2026)

### Requisiti
- Drag & drop colonne nel dropdown "Show/Hide Columns"
- Ordine salvato in localStorage
- Reset ripristina ordine originale

### Implementazione
Il dropdown già mostra un'icona `GripVertical` per il drag.
Serve implementare:

1. **Drag & Drop nel dropdown:**
   - `draggable="true"` sulle opzioni
   - `ondragstart`, `ondragover`, `ondrop` handlers
   - Visual feedback durante drag (bordo sopra/sotto durante hover)

2. **Persistenza:**
   - `columnOrder: string[]` in localStorage
   - Al mount: ordina colonne secondo ordine salvato

3. **Reset:**
   - Ripristina ordine da `columns` prop originale

### ✅ COMPLETATO (23 Gennaio 2026)
- [x] Aggiungere `draggable="true"` alle opzioni nel dropdown
- [x] Implementare drag handlers (`ondragstart`, `ondragover`, `ondrop`)
- [x] Aggiungere visual feedback durante drag (bordo sinistro verde)
- [x] Verificare che l'ordine sia rispettato nella tabella
- [x] Testare persistenza in localStorage

### File modificati:
- `DataTableToolbar.svelte` - dropdown con drag & drop
- `DataTable.svelte` - aggiunta funzione `reorderColumns` e `orderedColumns`

---

## 📋 PRIORITÀ IMPLEMENTAZIONE

1. ~~**Column Reordering**~~ ✅ COMPLETATO
2. ~~**Column Resize Fix**~~ ✅ COMPLETATO (Opzione A)
3. ~~**Size Filter con Slider**~~ ✅ COMPLETATO (Opzione C+A)

---

## 🔲 TODO FUTURI

### Mobile Column Reorder
Il riordinamento colonne su mobile attualmente usa bottoni su/giù invece del drag & drop.
**TODO:** Verificare se funziona correttamente su dispositivi touch reali e, se necessario:
- Implementare touch drag with `touchstart`, `touchmove`, `touchend`
- Oppure usare una libreria come SortableJS con opzione `handle`
- Testare su iOS Safari e Android Chrome

### File Uploader Image Preview
Il nuovo FileUploader supporta upload multiplo ma non ha anteprima immagini.
Vedi `TODO_FUTURI.md` nella root del progetto per dettagli.

---

## ✅ Note Finali

### Cleanup Completato (23/01/2026)

- [x] `FilesTableAdvanced.svelte` rimosso (sostituito da `components/table/DataTable.svelte`)
- [x] `tanstack-table/DataTable.svelte` rimosso (era un prototipo obsoleto)
- [x] Mantenuto l'adapter core in `tanstack-table/` per futura migrazione a v9:
  - `createSvelteTable.svelte.ts`
  - `FlexRender.svelte`
  - `index.ts`

### Componenti Finali

```
src/lib/components/
├── table/                      # Componenti DataTable generici
│   ├── DataTable.svelte        # 941 righe - Componente principale
│   ├── DataTablePagination.svelte
│   ├── DataTableToolbar.svelte
│   ├── DataTableColumnFilter.svelte
│   ├── ConfirmModal.svelte
│   └── types.ts
├── files/
│   └── FilesTable.svelte       # Wrapper specifico per /files
└── ui/
    └── FileUploader.svelte     # Upload multiplo generico
```
