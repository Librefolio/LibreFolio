# TODO FUTURI

Questo file documenta miglioramenti futuri, migrazioni pianificate, e note tecniche importanti per il progetto LibreFolio.

---

## 📦 TanStack Table v9 Migration

**Data aggiunta**: 22 Gennaio 2026  
**Status**: ⏳ IN ATTESA (v9 in alpha)  
**Priorità**: Bassa (fino a release stabile)

### Contesto

Abbiamo scelto di usare **TanStack Table v8** con un **adapter custom Svelte 5** invece dell'adapter ufficiale `@tanstack/svelte-table` per i seguenti motivi:

1. **v8 adapter ufficiale** (`@tanstack/svelte-table`): Non compatibile con Svelte 5 (usa API interne Svelte 3/4)
2. **v9 con supporto Svelte 5**: Ancora in versione **alpha** (`9.0.0-alpha.x`)
   - Aggiornamenti frequenti
   - Potenziali breaking changes
   - Non adatto per produzione

### Soluzione Attuale

- **Libreria**: `@tanstack/table-core@^8.21.3` (stabile)
- **Adapter**: Custom in `frontend/src/lib/tanstack-table/`
- **Componenti**:
  - `createSvelteTable.svelte.ts` - Factory reattivo per Svelte 5
  - `DataTable.svelte` - Componente UI riutilizzabile
  - `FlexRender.svelte` - Helper per rendering celle
  - `index.ts` - Re-export delle API core

### Azione Futura

Quando TanStack Table v9 sarà **rilasciato come stabile** con supporto ufficiale Svelte 5:

1. **Installare** l'adapter ufficiale:
   ```bash
   npm install @tanstack/svelte-table
   ```

2. **Aggiornare import** in tutti i componenti:
   ```typescript
   // Da:
   import { createSvelteTable, getCoreRowModel } from '$lib/tanstack-table';
   
   // A:
   import { createSvelteTable, getCoreRowModel } from '@tanstack/svelte-table';
   ```

3. **Rimuovere** la cartella `src/lib/tanstack-table/` (adapter custom)

4. **Testare** tutte le tabelle (Files, future: Assets, Transactions, FX)

### Riferimenti

- [TanStack Table Docs](https://tanstack.com/table/latest)
- [TanStack Table GitHub](https://github.com/TanStack/table)
- [Svelte 5 Compatibility Discussion](https://github.com/TanStack/table/discussions/4454)

---

## 📱 Mobile Column Reorder (DataTable)

**Data aggiunta**: 23 Gennaio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Bassa

### Contesto
Il riordinamento colonne nella DataTable funziona con drag & drop su desktop, ma su mobile usiamo bottoni su/giù. Potrebbe essere migliorato con touch drag nativo.

### Azione Futura
1. Verificare comportamento su dispositivi touch reali (iOS Safari, Android Chrome)
2. Se necessario, implementare touch drag con `touchstart`, `touchmove`, `touchend`
3. Oppure integrare libreria come SortableJS con opzione `handle`

### File coinvolti
- `frontend/src/lib/components/table/DataTableToolbar.svelte`

---

## 🖼️ File Uploader Image Preview

**Data aggiunta**: 23 Gennaio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Media

### Contesto
Il nuovo FileUploader supporta upload multiplo di qualsiasi tipo di file. Per le immagini sarebbe utile:
- Anteprima dell'immagine
- Resize/crop prima dell'upload (riutilizzando ImageUploader)
- Navigazione tra i file nella lista

### Azione Futura
1. Rilevare se il file è un'immagine (`file.type.startsWith('image/')`)
2. Aggiungere pulsante "Preview" per aprire modale con anteprima
3. Integrare funzionalità di resize da ImageUploader
4. Permettere navigazione tra file con frecce

### File coinvolti
- `frontend/src/lib/components/ui/FileUploader.svelte`
- `frontend/src/lib/components/ui/ImageUploader.svelte` (da riutilizzare)

---

## 🖼️ Image Crop Component

**Data aggiunta**: 22 Gennaio 2026  
**Status**: 📋 PIANIFICATO  
**File**: `LibreFolio_developer_journal/RoadmapV4_UI/plan-image-crop.md`

Implementare crop avanzato per avatar e icone broker con `svelte-easy-crop`.

---

## Ripensare struttura di accesso ai broker Utente-SuperUtente per essere GDPR compliant
**Nota GDPR**: La visibilità dei dati di altri utenti da parte del superuser deve essere
ripensata per essere GDPR compliant. Possibili approcci:
- Superuser non vede dati personali di altri utenti senza consenso esplicito
- Log di accesso ai dati di altri utenti
- Anonimizzazione dei dati visualizzati (solo statistiche aggregate)
- Meccanismo di "data request" invece di accesso diretto (utente concede accesso all'assistenza per x tempo)


---

## 📁 Template per Nuovi TODO

```markdown
## 📌 [Titolo]

**Data aggiunta**: [Data]  
**Status**: [⏳ IN ATTESA | 📋 PIANIFICATO | 🔄 IN CORSO | ✅ COMPLETATO]  
**Priorità**: [Alta | Media | Bassa]

### Contesto
[Descrizione del problema o motivazione]

### Azione Futura
[Passi da eseguire quando sarà il momento]

### Riferimenti
[Link a documentazione, issue, PR]
```
