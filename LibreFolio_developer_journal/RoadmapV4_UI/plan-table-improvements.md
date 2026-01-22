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

16. **Selezione persistente** ✅
    - [x] Selezione mantenuta tra pagine
    - [x] Selezione mantenuta cambiando page size

17. **Pagination balloon** ✅
    - [x] Sticky bottom con spazio dal bordo
    - [x] Segue lo scroll della finestra

**TODO Fase 3:**
- [ ] Sorting colonne (click su header)
- [ ] Filtri per colonna stile Excel
- [ ] Column reorder drag & drop
- [ ] Download multiplo come ZIP

**Componente:** `FilesTableAdvanced.svelte` (v2)
- Paginazione custom (non dipende da TanStack)
- Storage keys separati per tipo (static vs brim)

---

### 📋 Fase 4: BRIM Multi-User Support (RICHIEDE BACKEND)

**Analisi completa**: `analysis-brim-multiuser.md`

**Situazione attuale:**
- ❌ I file BRIM non tracciano chi li ha caricati (user_id)
- ❌ I file BRIM non tracciano a quale broker sono stati parsati
- ❌ L'endpoint `/import/files` non filtra per utente

**Modifiche backend necessarie:**
1. Estendere schema `BRIMFileInfo` con:
   - `uploaded_by_user_id: int`
   - `uploaded_by_username: Optional[str]`
   - `target_broker_id: Optional[int]`
   - `target_broker_name: Optional[str]`

2. Modificare endpoint `/import/upload`:
   - Salvare `user_id` e `username` nel metadata

3. Modificare endpoint `/import/files`:
   - Parametro opzionale `user_id` (solo superuser)
   - Utenti normali vedono solo i propri file

4. Nuovo endpoint `/import/files/users`:
   - Lista utenti che hanno caricato file (solo superuser)

**Modifiche frontend:**
- Dropdown filtro utente (solo se superuser)
- Colonna "Utente" (solo se superuser e mostrata)
- Colonna "Broker" (per file parsed)

**Stima**: ~1 giorno (5.5h backend + 2.5h frontend)

---

### 📋 Fase 5: Filtering e Search (PIANIFICATO)

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
