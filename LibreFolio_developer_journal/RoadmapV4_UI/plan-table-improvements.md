# Piano: Migliorie Tabelle Files con TanStack Table

**Data**: 21 Gennaio 2026  
**Aggiornamento**: 22 Gennaio 2026  
**Status**: 🔄 IN CORSO  
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

### 🔄 Fase 2: Integrazione in Files Page (IN CORSO)

1. **Sostituire tabella Static Resources**
   - Usare `DataTable` component
   - Definire colonne tipizzate
   - Aggiungere icone per tipo file

2. **Sostituire tabella BRIM Reports**
   - Usare `DataTable` component
   - Mantenere icone CSV esistenti

### 📋 Fase 3: Features Avanzate (PIANIFICATO)

1. **Sorting Avanzato**
   - Multi-column sorting (shift+click)

2. **Pagination Avanzata**
   - Selettore page size: 10, 25, 50, 100
   - Indicatore: "Showing 1-10 of 42"

3. **Column Configuration**
   - Toggle visibilità colonne
   - Persistenza preferenze in localStorage

### 📋 Fase 4: Filtering e Search (PIANIFICATO)

1. **Global Search**
   - Input ricerca con debounce 300ms
   - Cerca in tutte le colonne testuali
   - Clear button

2. **Column Filters**
   - Dropdown per tipo file (Image, Text, CSV, etc.)
   - Date range picker per colonna data

### 📋 Fase 5: Azioni e Selezione (PIANIFICATO)

1. **Row Selection**
   - Checkbox per selezione multipla
   - Select all / Deselect all
   - Contatore items selezionati

2. **Bulk Actions**
   - Download ZIP di files selezionati
   - Delete selected con conferma

3. **Row Actions**
   - Preview (👁) - modal o drawer
     - **Testo**: Mostra contenuto con syntax highlighting opzionale
     - **Immagini**: Lightbox con zoom/pan
     - **Altri**: Messaggio "Preview not available"
   - Download (⬇)
   - Delete (🗑) con conferma elegante

### Fase 5: Delete Confirmation (0.5 giorni)

Sostituire `alert()` con conferma elegante:

1. **Inline Confirmation**
   - Row si espande con messaggio "Are you sure?"
   - Bottoni Cancel / Confirm Delete
   - Auto-close dopo 5 secondi

2. **Oppure Modal Confirmation**
   - Modal centrato leggero
   - Nome file evidenziato
   - Icona warning

### Fase 6: File Icons (0.5 giorni)

Estendere funzione `getFileIcon()`:

```typescript
const FILE_ICONS: Record<string, ComponentType> = {
  'csv': FileSpreadsheet,
  'xlsx': FileSpreadsheet,
  'png': Image,
  'jpg': Image,
  'jpeg': Image,
  'gif': Image,
  'webp': Image,
  'txt': FileText,
  'md': FileText,
  'json': FileJson,
  'pdf': FileType,
  // default
  'default': File
};
```

---

## Layout Finale

```
┌─────────────────────────────────────────────────────────────────┐
│ [🔍 Search...                    ] [Type: All ▾] [⚙ Columns]   │
├─────────────────────────────────────────────────────────────────┤
│ ☐ │ 📄 Name ↕        │ Type   │ Size ↕  │ Date ↕     │ Actions │
├───┼──────────────────┼────────┼─────────┼────────────┼─────────┤
│ ☐ │ 📊 report.csv    │ CSV    │ 1.2 MB  │ 20/01/2026 │ 👁 ⬇ 🗑 │
│ ☐ │ 🖼 logo.png      │ Image  │ 45 KB   │ 19/01/2026 │ 👁 ⬇ 🗑 │
│ ☐ │ 📝 notes.txt     │ Text   │ 2 KB    │ 18/01/2026 │ 👁 ⬇ 🗑 │
├───┴──────────────────┴────────┴─────────┴────────────┴─────────┤
│ ☐ Selected: 2 items                    [📥 Download] [🗑 Delete]│
├─────────────────────────────────────────────────────────────────┤
│ Showing 1-10 of 42         [10 ▾]  [◀ 1 2 3 ... 5 ▶]          │
└─────────────────────────────────────────────────────────────────┘
```

---

## File da Creare/Modificare

### Nuovi
| File | Descrizione |
|------|-------------|
| `frontend/src/lib/components/ui/DataTable.svelte` | Componente tabella generico |
| `frontend/src/lib/components/ui/DataTablePagination.svelte` | Controlli paginazione |
| `frontend/src/lib/components/ui/DataTableSearch.svelte` | Search + filters |
| `frontend/src/lib/components/ui/DeleteConfirmation.svelte` | Conferma eliminazione |

### Modificare
| File | Modifica |
|------|----------|
| `frontend/src/routes/(app)/files/+page.svelte` | Usare DataTable |
| `frontend/src/lib/utils/file-icons.ts` | Estendere icone |
| `frontend/package.json` | Aggiungere @tanstack/svelte-table |

---

## Stima Tempi

| Fase | Durata | Cumulativo |
|------|--------|------------|
| 1. Setup e Base | 0.5 giorni | 0.5 |
| 2. Core Features | 1 giorno | 1.5 |
| 3. Filtering | 0.5 giorni | 2 |
| 4. Azioni | 0.5 giorni | 2.5 |
| 5. Delete Confirm | 0.5 giorni | 3 |
| 6. File Icons | 0.5 giorni | 3.5 |

**Totale: ~3.5 giorni**

---

## Ordine di Esecuzione

```
1. npm install @tanstack/svelte-table
   ↓
2. Creare DataTable.svelte base
   ↓
3. Implementare sorting + pagination
   ↓
4. Integrare in /files page
   ↓
5. Aggiungere search + filters
   ↓
6. Implementare selezione + bulk actions
   ↓
7. Sostituire alert() con conferma elegante
   ↓
8. Estendere file icons
   ↓
9. Test e polish
```

---

## Note Tecniche

### TanStack Table - Pattern Base

```svelte
<script lang="ts">
  import { createSvelteTable, flexRender, getCoreRowModel, getSortedRowModel, getPaginationRowModel } from '@tanstack/svelte-table';
  
  const table = createSvelteTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });
</script>

<table>
  <thead>
    {#each $table.getHeaderGroups() as headerGroup}
      <tr>
        {#each headerGroup.headers as header}
          <th on:click={header.column.getToggleSortingHandler()}>
            {flexRender(header.column.columnDef.header, header.getContext())}
          </th>
        {/each}
      </tr>
    {/each}
  </thead>
  <tbody>
    {#each $table.getRowModel().rows as row}
      <tr>
        {#each row.getVisibleCells() as cell}
          <td>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
        {/each}
      </tr>
    {/each}
  </tbody>
</table>
```

### Persistenza Preferenze

```typescript
// Salvare in localStorage
const savePrefs = (key: string, value: any) => {
  localStorage.setItem(`datatable-${key}`, JSON.stringify(value));
};

// Ripristinare
const loadPrefs = <T>(key: string, defaultValue: T): T => {
  const saved = localStorage.getItem(`datatable-${key}`);
  return saved ? JSON.parse(saved) : defaultValue;
};
```
