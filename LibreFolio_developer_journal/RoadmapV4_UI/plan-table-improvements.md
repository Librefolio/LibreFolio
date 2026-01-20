# Piano: Migliorie Tabelle Files e BRIM

**Data**: 20 Gennaio 2026  
**Status**: 📋 DA REVIEW

---

## Problema Attuale

Le tabelle in `/files` (Static Resources e BRIM Reports) hanno diversi problemi:

### Static Resources
- ❌ Nessuna icona per tipi file (PNG, TXT)
- ❌ Nessuna paginazione
- ❌ Nessun controllo elementi per pagina
- ❌ Download salva con UUID invece del nome originale (**FIXED**)
- ❌ Delete senza conferma chiara (**DA MIGLIORARE**)
- ❌ Nomenclatura "Cancel" invece di "New File" (**FIXED**)
- ❌ Nessuna funzione rename/edit metadata

### BRIM Reports
- ✅ Icone corrette per CSV
- ❌ Nessuna paginazione
- ❌ Nessun controllo elementi per pagina
- ✅ Download funziona correttamente

### Entrambe
- ❌ Nessun sorting
- ❌ Nessun filtering
- ❌ Nessuna selezione multipla

---

## Soluzioni Proposte

### A. Fix Immediati (già implementati o semplici)

1. ✅ **Download con nome originale** - Aggiunto parametro `download=true` all'API
2. ✅ **Nomenclatura bottone** - Cambiato da "Cancel" a "New File"
3. 🔧 **Delete confirmation banner** - Sostituire alert() con banner centrato
4. 🔧 **Icone file types** - Estendere `getFileIcon()` per gestire PNG, TXT, etc.

### B. Funzionalità Tabella Avanzata

#### Opzione 1: Tabella Nativa + Componente Custom
- **Pro**: Controllo totale, bundle size ridotto
- **Contro**: Più lavoro iniziale, dobbiamo implementare tutto

#### Opzione 2: TanStack Table (svelte-table)
- **Pro**: Standard de-facto, feature complete, ottimizzata
- **Contro**: Curva apprendimento, bundle size ~40KB
- **Link**: https://tanstack.com/table/latest

#### Opzione 3: Svelte-Simple-Datatables
- **Pro**: Leggera, fatta per Svelte
- **Contro**: Meno features, meno attiva
- **Link**: https://github.com/vincjo/simple-datatables

#### Opzione 4: ag-Grid Community
- **Pro**: Enterprise-grade, tutte le features
- **Contro**: Bundle size enorme (~500KB), overkill
- **Link**: https://www.ag-grid.com

---

## Scelta Consigliata: TanStack Table ✅

### Perché TanStack Table?
1. **Headless UI**: Controllo totale sullo styling (compatibile con nostro design)
2. **Feature complete**: sorting, filtering, pagination, selezione, column resizing
3. **TypeScript-first**: Ottima DX
4. **Ottimizzato**: Virtual scrolling per grandi dataset
5. **Documentazione**: Eccellente con esempi Svelte
6. **Comunità**: Molto attiva, usata da grandi progetti

### Features da Implementare

#### Fase 1: Core Features
- [ ] **Sorting**: Click su header per sort ascendente/discendente
- [ ] **Pagination**: 
  - Selettore: 10, 50, 100, Tutti
  - Navigazione: First, Prev, Next, Last
  - Indicatore: "Showing 1-10 of 42"
- [ ] **Column configuration**: Visibilità, width, order

#### Fase 2: Advanced Features  
- [ ] **Filtering**: 
  - Text search per nome file
  - Filter per tipo file (CSV, Image, Text, etc.)
  - Filter per data range
- [ ] **Selection**: 
  - Checkbox per selezione multipla
  - Azioni bulk: Download ZIP, Delete selected
- [ ] **Column resizing**: Drag header per ridimensionare
- [ ] **File Preview**: 
  - Icona "Eye" per preview in modal
  - Text files: Mostra prime 1000 caratteri (usando `?offset=0&window=1000`)
  - Images: Thumbnail ridimensionata (usando `?img_preview=400x400`)
  - Error handling per file binari non supportati

#### Fase 3: Polish
- [ ] **Empty state**: Messaggio quando nessun risultato
- [ ] **Loading state**: Skeleton durante fetch
- [ ] **Export**: CSV, JSON export dei dati filtrati
- [ ] **Preview Modal**: Componente riutilizzabile per preview
  - Text: Syntax highlighting (opzionale)
  - Images: Lightbox con zoom
  - Unsupported: Messaggio "Preview not available"

---

## Layout Proposto

```
┌─────────────────────────────────────────────────────────────────┐
│ [Search...] [Type: All ▾] [Date: Any ▾]         [⚙ Columns]    │
├─────────────────────────────────────────────────────────────────┤
│ ☐ │ Name ↕        │ Type  │ Size ↕  │ Date ↕      │ Actions   │
├───┼───────────────┼───────┼─────────┼─────────────┼───────────┤
│ ☐ │ 📄 report.csv │ CSV   │ 1.2 MB  │ 2026-01-20  │ 👁 ⬇ 🗑  │
│ ☐ │ 🖼 logo.png   │ Image │ 45 KB   │ 2026-01-19  │ 👁 ⬇ 🗑  │
│ ☐ │ 📝 notes.txt  │ Text  │ 2 KB    │ 2026-01-18  │ 👁 ⬇ 🗑  │
├───┴───────────────┴───────┴─────────┴─────────────┴───────────┤
│ Showing 1-10 of 42          [10 ▾] [< 1 2 3 ... >] [Last]    │
└─────────────────────────────────────────────────────────────────┘

Selected: 2 items  [Download ZIP] [Delete Selected]

Actions: 👁 Preview | ⬇ Download | 🗑 Delete
```

---

## Alternative per Libreria Tabelle

| Libreria | Bundle | Features | Svelte Support | Raccomandazione |
|----------|--------|----------|----------------|-----------------|
| **TanStack Table** | ~40KB | ⭐⭐⭐⭐⭐ | Nativo | ✅ **CONSIGLIATO** |
| Svelte-Simple-Datatables | ~15KB | ⭐⭐⭐ | Nativo | 🟡 OK per semplice |
| Native Custom | 0KB | ⭐⭐ | - | 🟡 Solo se tempo abbonda |
| ag-Grid Community | ~500KB | ⭐⭐⭐⭐⭐ | Wrapper | ❌ Overkill |

### Confronto Dettagliato

#### TanStack Table (Raccomandato)
```bash
npm install @tanstack/svelte-table
```
- ✅ Headless: Styling completamente custom
- ✅ TypeScript-first
- ✅ Virtual scrolling
- ✅ Server-side pagination support
- ✅ Ottima documentazione
- ❌ Bundle size medio

**Esempio Codice**:
```svelte
<script>
  import { createSvelteTable, flexRender } from '@tanstack/svelte-table';
  
  const table = createSvelteTable({
    data: files,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });
</script>
```

#### Svelte-Simple-Datatables
```bash
npm install @vincjo/datatables
```
- ✅ Leggera
- ✅ Facile da usare
- ✅ Stile incluso (customizzabile)
- ❌ Meno features avanzate
- ❌ Community più piccola

#### Native Custom
- ✅ Zero dipendenze
- ✅ Bundle size minimo
- ❌ Dobbiamo implementare tutto
- ❌ Maintenance overhead
- ❌ No virtual scrolling

---

## Piano di Implementazione

### Fase 1: Setup e Core (1 giorno)
1. [ ] Installare TanStack Table
2. [ ] Creare componente `DataTable.svelte` generico
3. [ ] Implementare sorting di base
4. [ ] Implementare pagination con selettore elementi

### Fase 2: Integrazione Files Page (0.5 giorni)
1. [ ] Sostituire tabella Static Resources
2. [ ] Sostituire tabella BRIM Reports
3. [ ] Aggiungere icone per tutti i tipi file
4. [ ] Testare dark mode

### Fase 3: Features Avanzate (1.5 giorni)
1. [ ] Filtering per nome e tipo
2. [ ] Selezione multipla con azioni bulk
3. [ ] Column resizing
4. [ ] Empty/Loading states
5. [ ] **Preview Modal con API integration**:
   - [ ] Text files: `GET /uploads/file/{id}?offset=0&window=1000`
   - [ ] Images: `GET /uploads/file/{id}?img_preview=400x400`
   - [ ] Error handling per file non supportati

### Fase 4: Rename e Delete Improvements (0.5 giorni)
1. [ ] Implementare rename file (modal inline)
2. [ ] Banner conferma delete centrato invece di alert()
3. [ ] API per rename: `PATCH /uploads/{id}` con `{"original_name": "nuovo.txt"}`
4. [ ] Warning che link esistenti diventeranno invalidi

### Fase 5: Polish (0.5 giorni)
1. [ ] Animazioni transizioni
2. [ ] Responsive mobile (collapse su card view?)
3. [ ] Accessibilità (keyboard navigation)
4. [ ] Test con grandi dataset (100+ files)

---

## File da Creare/Modificare

| File | Descrizione |
|------|-------------|
| `src/lib/components/ui/DataTable.svelte` | Componente tabella riutilizzabile |
| `src/lib/components/ui/TablePagination.svelte` | Controlli pagination |
| `src/lib/components/ui/DeleteConfirmBanner.svelte` | Banner conferma centrato |
| `src/lib/components/files/RenameFileModal.svelte` | Modale rename inline |
| `src/lib/components/files/FilePreviewModal.svelte` | **NEW**: Preview text/images |
| `src/routes/(app)/files/+page.svelte` | Aggiornare con nuova tabella |
| `backend/app/api/v1/uploads.py` | ✅ **DONE**: Parametri preview aggiunti |

---

## API Changes Necessarie

### ✅ IMPLEMENTATO: File Preview Parameters
```python
@router.get("/file/{file_id}")
async def serve_file(
    file_id: str,
    download: bool = False,
    offset: Optional[int] = None,      # Text preview: start position
    window: Optional[int] = None,      # Text preview: bytes to read
    img_preview: Optional[str] = None, # Image resize: "WIDTHxHEIGHT"
):
    """
    Preview modes:
    - Text: ?offset=0&window=1000 (returns first 1000 chars)
    - Image: ?img_preview=200x200 (returns resized, max dimension)
    
    Raises 400 if preview params used on incompatible file type.
    """
```

**Dependencies Added**: 
- `Pillow` per image resizing (async-safe, multi-process capable)

### Nuovo Endpoint: Rename File
```python
@router.patch("/{file_id}", response_model=UploadFileInfo)
async def rename_file(
    file_id: str,
    name: str,
    current_user: User = Depends(get_current_user),
):
    """
    Rename an uploaded file.
    
    Warning: Existing links will break if URL structure changes.
    """
    # Validate ownership
    # Update metadata
    # Return updated info
```

---

## Domande per Review

1. **Libreria**: ✅ **APPROVATO** - TanStack Table (motivazione: licenza + features)
2. **Rename**: Implementare in Fase 4 ok?
3. **Bulk actions**: Priorità alta o media?
4. **Virtual scrolling**: Necessario per il caso d'uso attuale?
5. **Mobile**: Card view o tabella responsive?
6. **Preview**: Implementare lightbox avanzato o modal semplice?

---

## Stima Tempo Totale

Con TanStack Table + Preview features:
- **Ottimistico**: 3 giorni
- **Realistico**: 4.5 giorni
- **Con imprevisti**: 6 giorni

---

**Status**: ✅ **APPROVATO** - TanStack Table + Preview API implementata
**Next**: Iniziare Fase 1 (Setup TanStack Table)
2. **Rename**: Implementare subito o dopo?
3. **Bulk actions**: Priorità alta o media?
4. **Virtual scrolling**: Necessario per il caso d'uso attuale?
5. **Mobile**: Card view o tabella responsive?

---

## Stima Tempo Totale

Con TanStack Table:
- **Ottimistico**: 2.5 giorni
- **Realistico**: 3.5 giorni
- **Con imprevisti**: 5 giorni

---

**Note Finali**

Questa implementazione renderà le tabelle:
1. ✅ Consistenti tra Static e BRIM
2. ✅ Scalabili (100+ files)
3. ✅ User-friendly (sorting, pagination, search)
4. ✅ Riutilizzabili (DataTable.svelte per future tabelle)
5. ✅ Accessibili (keyboard, screen readers)

**Attendo review e decisione su libreria da usare.**
