# Phase 7: Transactions System — Macro Plan

**Status**: ⏳ TODO
**Durata stimata**: ~11 giorni (multi-sprint, Parti 1+2+3+4+4b+5 = 1+2+2+2+1+3)
**Priorità**: P0 (MVP)
**Dipendenze**:
- Phase 4 (Brokers + `BrokerUserAccess` OWNER/EDITOR/VIEWER)
- Phase 5 (FX)
- Phase 6 (Assets + `AssetMatchingWizard` + `AssetModal`)
- Phase 6 Step 3 Round 12 ✅ (`AssetEvent` + `FAAssetEventPoint` cross-provider)

**Complessità**: ⚠️ ALTA

> **📌 Riferimenti precedenti**:
> - [`plan-phase05-to-08-upgrade.md` §6](../plan-phase05-to-08-upgrade.md) — **obsoleto**: idea originale con regimi fiscali / cash split (posticipati a Phase 8+)
> - [`plan-phase7b-filePreview.md`](../plan-phase7b-filePreview.md) — **assorbito in Parte 4b** di questo piano (File Preview System)
>
> Questo documento **sostituisce** la vecchia stesura di Phase 7 con un design unificato
> che tiene conto dell'infrastruttura completata dopo Round 12 (AssetEvent) e del
> sottosistema BRIM già operativo con upload/parse file. Incorpora inoltre il piano
> autonomo di File Preview come Parte 4b (utile per ispezionare i file BRIM prima del parsing).

---

## 🎯 Obiettivo

Completare il sotto-sistema transazioni end-to-end:

1. **Riallineare** il modello DB/schema con il nuovo design "eventi-first" collegando
   `Transaction → AssetEvent` e uniformando il controllo accessi per-utente.
2. **Estendere** i plugin BRIM per produrre anche eventi asset + metadata UI, così che
   il frontend possa renderizzare preview coerenti.
3. **Consolidare** le API in modalità **full-bulk** (no endpoint singoli), con endpoint
   dry-run per validazione e endpoint di event-suggestion.
4. **Costruire** la pagina `/transactions` in stile DataTable-with-header-filters,
   coerente con `AssetTable` / `FxTable` / `BrokerImportFilesModal`.
5. **Unificare** l'inserimento manuale, l'output BRIM e il clone di righe esistenti in
   **una sola Staging Modal** con asset-grouping colorato, SearchSelect per bulk-assign,
   event-matching automatico via tolerance slider, e commit atomico broker-aware.
6. **Aggiungere un sistema di File Preview** (assorbito dal vecchio piano `plan-phase7b-filePreview.md`)
   che permetta di ispezionare inline file image / text / table / markdown / code sia nella Files page
   sia nel `BrokerImportFilesModal` prima del parsing BRIM.

**Escluso da questa fase** (rinviato a Phase 8+ / futuro):
regimi fiscali (FIFO/LIFO/PMC), Cash Split, Over-Sell Protection, Smart Assistant per
auto-linking massivo degli eventi retroattivi.

---

## 📊 Analisi Situazione Attuale

### Backend — già solido ✅
- `Transaction` (tabella unificata, bidirectional link via `related_transaction_id`, balance validation)
- `AssetEvent` (DIVIDEND / INTEREST / PRICE_ADJUSTMENT / SPLIT / MATURITY_SETTLEMENT)
- `TransactionService.create_bulk` con access control `EDITOR` per broker
- `BRIMProvider` base + 11 plugin broker
- Flusso BRIM: upload → parse → review → commit funzionante

### Gap identificati

| # | Gap | Impatto |
|---|-----|---------|
| 1 | Link `Transaction ↔ AssetEvent` assente | Una `DIVIDEND` tx non sa da quale `AssetEvent` globale deriva. Blocca smart assistant. |
| 2 | Access control incoerente | `GET/PATCH/DELETE /transactions` non filtrano per `BrokerUserAccess` dell'utente corrente. Solo `POST` verifica `EDITOR`. |
| 3 | BRIM non emette eventi | I plugin ritornano solo `List[TXCreateItem]`. Uno SPLIT globale in un estratto conto non viene propagato come `AssetEvent`. |
| 4 | Frontend `/transactions` è un placeholder | Nessuna lista, nessun filtro, nessun import UI. |
| 5 | Nessuna "Staging Area" | BRIM popola stato locale del componente e invia a `POST /transactions`. Manca modale unificata con validazione bulk + preview bilanci + asset resolver. |
| 6 | `BRIMProvider` non espone metadata UI | No `docs_url`, no `capabilities`, no `preview_columns`. Il frontend non può renderizzare colonne broker-specifiche. |

### Endpoint già esistenti da **riusare** (nessuna duplicazione)

| Necessità | Endpoint | Note |
|-----------|----------|------|
| Broker visibili all'utente | `GET /api/v1/brokers` | Già filtrato per `BrokerUserAccess` |
| Upload file BRIM | `POST /api/v1/brokers/import/upload` | |
| Parsing BRIM | `POST /api/v1/brokers/import/files/{file_id}/parse` | Trigger esplicito, non auto |
| Cached last parse | `GET /api/v1/brokers/import/files/{file_id}/last-parse` | Per riapertura Staging |
| Plugin list | `GET /api/v1/brokers/import/plugins` | |
| Asset search | `GET /api/v1/assets/query` + `GET /api/v1/assets/provider/search` | Per resolver |
| Eventi asset | `POST /api/v1/assets/events/query` | Per matching su date |

### Verifiche di dipendenza
- ✅ **Round 12 completato**: `FAAssetEventPoint` integrato in `yahoo_finance.py`,
  `justetf.py`, `scheduled_investment.py`, `asset_source.py`. Gli eventi sono già
  persistiti correttamente in `asset_events`.
- ⏳ **Step 5 Phase 6** (`AssetMatchingWizard`) — necessario per la Staging Modal.
  Se non completato prima di Part 5, il "+ Create new asset" userà direttamente
  `AssetModal` in create mode.

---

## 🗂️ Suddivisione in 6 Parti (Sprint)

| # | Parte | Area | Target | Effort | Dettaglio |
|---|-------|------|--------|--------|-----------|
| **1** | Backend DB & Schema Realignment | models, schemas, migration | Link `Transaction ↔ AssetEvent`, access control uniforme | 1g | **Dettagliato** (prossimo piano) |
| **2** | BRIM Plugin v2 — Events & UI Metadata | `BRIMProvider` base + refactor 11 plugin | Plugin emettono eventi, espongono capability UI | 2g | **Dettagliato** |
| **3** | API Consolidation — full-bulk | endpoints, service, pytest | Visibilità per-utente, `validate` dry-run, `events/suggest`, test ≥85% | 2g | **Dettagliato** |
| **4** | Frontend — Pagina `/transactions` | route, DataTable, filtri colonna | Lista utente con filtri header, GoTo linked pair, bulk actions | 2g | **Alto livello** |
| **4b** | Frontend — File Preview System | backend service + modale multi-tipo | Preview inline (image/text/table/markdown/code) su Files page + BRIM files | 1g | **Alto livello** |
| **5** | Frontend — Staging Modal | modale unificata, asset resolver | Manual + BRIM + Clone, grouping colorato, tolerance slider | 3g | **Alto livello** |

Le Parti 1–3 sono **dettagliate** (alta confidenza, basso rischio di cambio).
Le Parti 4 / 4b / 5 restano **alto livello** (ASCII art + principi UX) — target e situazione
di partenza ben definiti, attività da raffinare in piano di dettaglio dedicato al
momento dell'esecuzione.

**Ordine consigliato**: 1 → 2 → 3 → 4 → 4b → 5.
La 4b può essere anticipata o posticipata rispetto alla 5 senza impatti: è **autonoma**
rispetto al modello dati transazioni.

---

## 🔷 Parte 1 — Backend: DB & Schema Realignment

### Situazione di partenza
- `models.py`: `Transaction` e `AssetEvent` esistono ma **senza FK** tra loro
- `TransactionType.DIVIDEND/INTEREST` sono "orfani" rispetto agli `AssetEventType` omonimi
- `BrokerUserAccess` presente, check solo in `create_bulk`

### Attività
1. Aggiungere `asset_event_id: Optional[int]` a `Transaction` (FK `asset_events.id`, `ondelete="SET NULL"`, nullable, indicizzato). Semantica: quando presente, la transazione è **la realizzazione personale** di un evento asset globale.
2. Aggiornare `TXCreateItem` / `TXReadItem` / `TXUpdateItem` con `asset_event_id` (optional).
3. Aggiungere flag `event_compatible: bool` a `TX_TYPE_METADATA` (true per DIVIDEND, INTEREST, ADJUSTMENT/split).
4. Validatore in `TXCreateItem.model_validator`: se `asset_event_id` presente, `asset_id` deve matchare `asset_event.asset_id` e il `type` deve essere `event_compatible`.
5. Estendere `alembic/versions/001_initial.py` con nuova colonna + indice. Rigenerare DB con `./dev.py db create-clean`.
6. Aggiornare test `test_identifier_columns_match_enum` e suite `transaction_service`.

### Deliverable
Migrazione applicata, schema coerente, test pre-esistenti verdi, nuovo campo propagato in tutte le API.

---

## 🔷 Parte 2 — BRIM Plugin v2: Events & UI Metadata

### Situazione di partenza
- `BRIMProvider.parse()` ritorna `Tuple[List[TXCreateItem], List[str], Dict[int, BRIMExtractedAssetInfo]]`
- Nessun metodo per eventi
- Nessun `params_schema` / `docs_url` (TODO esistente a L319 di `brim_provider.py`)

### Attività
1. **Evolvere la classe base `BRIMProvider`**:
   - Cambiare firma `parse()` → ritorna `BRIMParseOutput` (nuovo schema) con:
     `transactions`, `warnings`, `extracted_assets`, `asset_events: List[FAAssetEventPoint]`.
   - `@property docs_url: Optional[str]` (default `None`).
   - `@property capabilities: BRIMCapabilities` (dataclass: `supports_events`, `supports_fees_aggregation`, `multi_broker_file`, …).
   - `@abstractmethod preview_columns() -> List[BRIMPreviewColumn]` per colonne custom nella Staging.
2. **Refactor 11 plugin** broker: adeguare alla nuova firma. Default `asset_events=[]`. **Nessuna legacy wrapper** (rompi e risolvi — la v1 non è mai andata in produzione).
3. Estendere `BRIMParseResponse` con `asset_events` e propagare in `parse_file()` / endpoint `POST /brokers/import/files/{id}/parse`.
4. **Nuovo endpoint** `POST /api/v1/brokers/import/commit`:
   accetta payload unificato `{transactions, asset_events, asset_mappings}` e committa **atomicamente** creando prima eventi, poi transazioni con FK risolte. Rollback totale se una qualsiasi `TXCreateItem` fallisce.
5. Schema additivi in `backend/app/schemas/brim.py`:
   `BRIMCapabilities`, `BRIMPreviewColumn`, `BRIMCommitRequest`, `BRIMCommitResponse`.

### Deliverable
Classe base estesa, 11 plugin allineati, endpoint `commit` atomico, frontend può leggere `capabilities` + `preview_columns` per rendering dinamico.

---

## 🔷 Parte 3 — API Consolidation (full-bulk)

### Principi
- **Niente endpoint singoli**: no `GET /transactions/{id}`, no `DELETE /transactions/{id}`. Tutto via liste di ID.
- **Niente endpoint duplicati**: `GET /api/v1/brokers` già ritorna i broker accessibili.
- **Access control uniforme** su ogni verbo, derivato da `BrokerUserAccess`.

### Attività
1. **Rimuovere** `GET /api/v1/transactions/{tx_id}`.
   Sostituito da `GET /api/v1/transactions?ids=1,2,3` (query list param), che ordina la risposta nello **stesso ordine** degli ID richiesti (pattern già adottato in `/api/v1/assets`).
2. **Uniformare access control**:
   - `GET /transactions` → filtra automaticamente per broker accessibili dall'utente (JOIN con `BrokerUserAccess`).
   - `PATCH /transactions` → per-item check `EDITOR` su ogni broker coinvolto.
   - `DELETE /transactions?ids=...` → per-item check `EDITOR`.
   - Tutto gestito in `TransactionService` (generalizzare helper `_check_broker_access`).
3. **Nuovo endpoint** `POST /api/v1/transactions/validate` (body: `List[TXCreateItem]`):
   dry-run di `create_bulk` **senza commit**. Ritorna `validation_errors` per item + `balance_preview` per broker coinvolto. Consumato in live dalla Staging Modal (debounced 500ms).
4. **Nuovo endpoint** `POST /api/v1/transactions/events/suggest`
   (body: `[{asset_id, date, type, tolerance_days}]`):
   ricerca eventi candidati entro ±tolerance. Risposta per-item: lista `AssetEvent` ordinata per distanza temporale dalla data richiesta. Usato in Staging/Edit quando l'utente cambia asset su righe DIVIDEND/INTEREST/ADJUSTMENT.
5. **Ampliamento schemi**: `asset_event_id` (da Parte 1) propagato in `create_bulk` / `update_bulk`.
6. **Test matrix**:
   - OWNER / EDITOR / VIEWER × GET / POST / PATCH / DELETE × owned / foreign broker
   - `validate` senza side-effect (DB invariato)
   - `events/suggest` con tolleranza 0 / 3 / 7 / 14 giorni
   - Link `asset_event_id` rifiutato se `asset_id` mismatch
   - Copertura ≥85% su `transaction_service` e `brim_provider`

### Deliverable
API bulk coerenti, niente endpoint singolari, suite test green, endpoint di supporto per la Staging Modal pronti.

---

## 🔷 Parte 4 — Frontend: Pagina `/transactions` (Alto Livello)

### Principi UX
- **Filtri tutti nelle column header** tramite `DataTableColumnFilter` già esistente (date range, enum multiselect, text search, number range, asset autocomplete, tag multiselect).
- **Toolbar minima**: solo azioni globali (`↻ Refresh`, `Cols▾ ColumnVisibilityToggle`, `📥 Import ▾`, `+ New`).
- **Paginatore server-side** via `DataTablePagination` esistente.
- **`SelectionBar`** per bulk actions (pattern `BrokerImportFilesModal`).
- **GoTo linked pair**: click 🔗 naviga alla pagina contenente la riga pair, evidenziandola (stesso pattern dei data-editor asset/forex dopo doppio-click). Implementazione: `?highlight_id=N` in query string + scroll + pulse.
- **Indicatore ●evt**: badge viola quando `asset_event_id != null`, tooltip con dettagli evento.
- **Badge tipo** via `TransactionTypeBadge.svelte`, guidato da `TXTypeMetadata` cached post-boot (coerente con `broker_detail` — BUY verde, SELL rosso, DIVIDEND viola…).

### Wireframe ASCII

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│  Transactions                        [↻] [Cols▾] [📥 Import ▾] [+ New]           │
│  All transactions across your accessible brokers                                  │
├───────────────────────────────────────────────────────────────────────────────────┤
│ ☐ │Date▲▼🔽 │Type🔽  │Asset 🔍🔽      │Qty 🔽    │Cash 🔽     │Broker🔽 │Tags🔽 │⋯│
├───┼─────────┼────────┼────────────────┼──────────┼────────────┼─────────┼───────┼─┤
│ ☐ │04-15-26 │🛒 BUY  │VWCE            │+10.00    │-€1,050.00  │Degiro   │—      │✎│
│ ☐ │04-10-26 │💵 DIV  │AAPL            │ 0        │+€12.40     │IBKR     │div    │✎│←●evt
│ ☐ │04-08-26 │💱 FX   │—               │ 0        │-$1,000.00  │IBKR     │—      │✎│🔗
│ ☐ │04-08-26 │💱 FX   │—               │ 0        │+€921.50    │IBKR     │—      │✎│🔗
│ ☐ │04-05-26 │🔄 XFER │BTC             │-0.5      │—           │Coinbase │—      │✎│🔗
│ ☐ │04-05-26 │🔄 XFER │BTC             │+0.5      │—           │Ledger   │—      │✎│🔗
│ ☐ │04-01-26 │💰 DEP  │—               │ 0        │+€2,000.00  │Degiro   │—      │✎│
├───────────────────────────────────────────────────────────────────────────────────┤
│ ▾ 3 selected: [✎ Edit bulk] [📋 Clone to staging] [🗑 Delete]  ← SelectionBar    │
│                                                                                   │
│  Rows per page: [50 ▾]      ◀ Prev   Page 1 of 12   Next ▶   Total 582 tx       │
└───────────────────────────────────────────────────────────────────────────────────┘

🔽 = column filter popover    🔗 = GoTo linked pair    ●evt = linked AssetEvent
```

### Attività (alto livello)
- Route `src/routes/(app)/transactions/+page.svelte` + `+page.ts` carica `GET /transactions` + `GET /brokers` + `GET /transactions/types`.
- Componente `TransactionsTable.svelte` wrapper di `DataTable` con colonne: select, date, type, asset, qty, cash, broker, tags, `linked_icon`, `event_icon`, actions.
- Filtri sincronizzati con **query string** per linkabilità (`/transactions?broker_id=3&type=DIVIDEND`).
- Icona 🔗 (lucide `Link2`) visibile se `related_transaction_id != null`. Click → filtra pagina su `?ids=<this>,<related>&highlight=<related>` → scroll + pulse.
- Icona ● (badge viola) se `asset_event_id != null`, tooltip con evento.
- **Bulk actions** in `SelectionBar`:
  - `✎ Edit bulk` → apre Staging Modal (Parte 5) in modalità **edit** con N righe pre-caricate come `TXUpdateItem`.
  - `📋 Clone to staging` → apre Staging Modal in modalità **create** con N righe clonate (id stripped, data=oggi default).
  - `🗑 Delete` → `ConfirmModal` + `DELETE /transactions?ids=...`.
- **Single-row actions** (icona ✎ in colonna azioni): stesso flow dei bulk ma con N=1.
- **Import menu**:
  - "From broker file…" → apre `BrokerImportFilesModal` esistente. Dopo parse successful → auto-apre Staging in modalità BRIM.
  - "Manual entry…" → apre Staging vuota.

### Deliverable
Pagina funzionante con visualizzazione + filtri + delete/edit/clone via Staging Modal.

---

## 🔷 Parte 4b — Frontend: File Preview System (Alto Livello)

### Motivazione
Prima di cliccare "Parse" su un file BRIM uploadato, l'utente vuole poter **ispezionare il
contenuto grezzo** per verificare encoding, separatore, intestazioni, righe di spazzatura.
Lo stesso meccanismo serve nella pagina Files per i file statici. Questo piano era stato
disegnato autonomamente in [`plan-phase7b-filePreview.md`](../plan-phase7b-filePreview.md)
e viene ora **assorbito** qui con i necessari aggiornamenti di stack.

### Situazione di partenza
- Nessun endpoint di preview file (solo download diretto)
- `BrokerImportFilesModal` mostra solo metadata (nome, dimensione, stato)
- Files page mostra solo lista, senza preview

### Principi UX
- **Bottone 👁 preview** visibile solo per file con `canPreview(filename) === true`.
- **Modale unificata** `FilePreviewModal` (basata su `ModalBase` esistente) che auto-detecta il tipo dal backend e renderizza il sub-componente appropriato.
- **Integrazione in 3 posizioni**:
  - Pagina `/files` tab Static
  - Pagina `/files` tab BRIM
  - `BrokerImportFilesModal` (nuovo accesso via Import ▾ dalla pagina `/transactions`)
- **Binari/archivi**: NO preview, solo download (nessun bottone visualizzato).

### Tipi supportati

| Categoria | Estensioni | Componente | Controlli |
|-----------|------------|------------|-----------|
| Image | jpg, jpeg, png, gif, webp, svg | `ImagePreview.svelte` | Slider qualità 25/50/75/100%, dimensioni originali |
| Text | txt, log, json, xml, yaml, yml | `TextPreview.svelte` | Line-range picker, line numbers, total lines |
| Markdown | md, markdown | `MarkdownPreview.svelte` | Toggle raw/rendered (via `marked` + `dompurify`) |
| Table | csv, xlsx, xls | `TablePreview.svelte` | Wrapper `DataTable`, row-range picker, total rows |
| Code | py, js, ts, html, css, sql | `CodePreview.svelte` | Syntax highlighting (`highlight.js`), line-range picker |
| Unsupported | zip, tar, pdf, … | — | Solo download, nessun bottone preview |

### Wireframe ASCII (caso CSV BRIM)

```
╔════════════════════════════════════════════════════════════════════════╗
║ 👁 Preview — degiro_2026-04.csv · 12.3 KB · 847 rows               [✕]║
╠════════════════════════════════════════════════════════════════════════╣
║ Type: CSV      From row: [1▾]    To row: [50▾]    Total: 847          ║
║ Separator: [auto ▾]   Encoding: [utf-8 ▾]                             ║
╠════════════════════════════════════════════════════════════════════════╣
║ # │Date       │Product             │ISIN         │Qty     │Price      ║
║ 1 │04-15-2026 │VANGUARD FTSE ALLW  │IE00BK5BQT80 │+10     │€105.00    ║
║ 2 │04-15-2026 │VANGUARD FTSE ALLW  │IE00BK5BQT80 │ 0      │-€0.50 fee ║
║ 3 │04-10-2026 │APPLE INC           │US0378331005 │ 0      │+€12.40 div║
║ ...                                                                    ║
╠════════════════════════════════════════════════════════════════════════╣
║                       [Download full file]  [Close]                    ║
╚════════════════════════════════════════════════════════════════════════╝
```

### Backend

| File | Azione | Descrizione |
|------|--------|-------------|
| `backend/app/services/file_preview.py` | **Nuovo** | `PreviewType` enum, `detect_preview_type()`, `get_text_preview()`, `get_table_preview()`, `get_markdown_preview()`, `get_image_preview()` |
| `backend/app/schemas/uploads.py` | Modifica | `FilePreviewResponse` + `FilePreviewMetadata` |
| `backend/app/api/v1/uploads.py` | Modifica | `GET /files/{file_id}/preview` (param: `start_line`, `end_line`, `render_md`, `img_quality`) |
| `backend/app/api/v1/brokers.py` | Modifica | `GET /brokers/import/files/{file_id}/preview` (stessa shape) |
| `backend/app/config.py` | Modifica | `PREVIEW_MAX_LINES`, `PREVIEW_MAX_FILE_SIZE_MB` |

### Frontend

| File | Azione | Descrizione |
|------|--------|-------------|
| `src/lib/types/preview.ts` | **Nuovo** | `PreviewType`, `FilePreviewResponse`, `FilePreviewMetadata` |
| `src/lib/utils/filePreview.ts` | **Nuovo** | `canPreview(filename)` |
| `src/lib/components/ui/media/FilePreviewModal.svelte` | **Nuovo** | Modale principale (wraps `ModalBase`, Svelte 5 runes) |
| `src/lib/components/ui/media/ImagePreview.svelte` | **Nuovo** | Slider qualità |
| `src/lib/components/ui/media/TextPreview.svelte` | **Nuovo** | Line-range, line numbers |
| `src/lib/components/ui/media/MarkdownPreview.svelte` | **Nuovo** | `marked` + `dompurify`, toggle raw/rendered |
| `src/lib/components/ui/media/TablePreview.svelte` | **Nuovo** | Wrapper `DataTable` esistente |
| `src/lib/components/ui/media/CodePreview.svelte` | **Nuovo** | `highlight.js` |
| `src/lib/components/files/FilesTable.svelte` | Modifica | Bottone 👁 in colonna azioni |
| `src/lib/components/brokers/BrokerImportFilesModal.svelte` | Modifica | Bottone 👁 prima di "Parse" |

### Dipendenze nuove

**Backend** (`pipenv install`): `python-magic`, `openpyxl` (se non già), `markdown`.
**Frontend** (`npm install`): `marked`, `dompurify`, `highlight.js`.

### Attività (alto livello)
1. Backend: `PreviewService` con dispatch per tipo (30m setup + 2h API + schema).
2. Schema response unificato `FilePreviewResponse` propagato nei due endpoint.
3. Frontend: utility `canPreview()` + `FilePreviewModal` master (15m setup + 3h componenti).
4. Integrazione Files page (tab Static + BRIM) e `BrokerImportFilesModal` (~1h).
5. i18n (~15m): chiavi `files.preview`, `files.quality`, `files.fromLine`, `files.toLine`, `files.totalLines`, `files.totalRows`, `files.showRaw`, `files.showRendered`, `files.previewUnsupported` × 4 lingue.
6. Test E2E Playwright: image+quality, text+range, csv→DataTable, markdown toggle, binary no-preview, brim file preview (~1h).

### Deliverable
Sistema preview funzionante in 3 punti di accesso (Files Static, Files BRIM, BrokerImportFilesModal), con 5 sub-componenti tipo-specifici e copertura E2E.

### Note di sicurezza/perf
- **Streaming** per file testuali grandi (evitare caricamento totale in RAM).
- **DOMPurify** obbligatorio sul markdown renderizzato per evitare XSS.
- **Cache** opzionale (LRU in-memory) per preview frequenti.
- **Size limit** via `PREVIEW_MAX_FILE_SIZE_MB` — oltre, ritorna errore strutturato con indicazione "file troppo grande, solo download".

---

## 🔷 Parte 5 — Frontend: Staging Modal (Alto Livello)

### Flusso BRIM completo

```
1. User apre Import ▾ → "From broker file…"
2. BrokerImportFilesModal (esistente) → seleziona broker + file già uploadato
   (oppure upload nuovo file via POST /brokers/import/upload)
3. User clicca "Parse" sulla riga file → POST /brokers/import/files/{id}/parse
   con { plugin_code, broker_id }
4. Backend ritorna BRIMParseResponse (transactions + asset_mappings + duplicates
   + warnings + asset_events — propagati da Parte 2)
5. Frontend auto-apre Staging Modal pre-popolata
6. In Staging: user risolve asset, rivede duplicati, auto-linka eventi,
   commit via POST /brokers/import/commit
7. File marcato PARSED dal backend a fine commit
```

### Principi UX aggiuntivi
- **Tutte le colonne hanno filtri header** (stesso pattern della lista).
- **Asset grouping per colore**: ogni `asset_id` unico in staging riceve un colore distintivo (pastello, ~8 colori ciclici). Le righe con stesso asset condividono il colore. Modificare l'asset di una riga la sposta nel gruppo-colore corrispondente.
- **SearchSelect globale per colore**: sopra la tabella, un `SearchSelect` per ogni colore attivo che modifica **in bulk** tutte le righe di quel gruppo.
- **Split asset**: bottone 🎨 in row-actions per "slegare" una riga da un gruppo e metterla in un gruppo nuovo (utile quando BRIM raggruppa male).
- **SearchSelect manuale**: oltre al resolver automatico (da `extracted_symbol`/`isin`/`name`), l'utente può aprire `SearchSelect.svelte` (riuso da `AssetCompare`) per selezionare esplicitamente tra gli asset del DB, OPPURE cliccare "+ Create new" → apre `AssetModal` esistente (o `AssetMatchingWizard` quando completato).
- **Event matching automatico**:
  - Quando user seleziona asset su riga DIVIDEND/INTEREST/ADJUSTMENT → frontend chiama `POST /transactions/events/suggest` con `tolerance_days` (default 7, slider 0–14).
  - 1 match → auto-link. N>1 → popover con scelta. 0 → nessun link (user può aprire ricerca manuale).
  - Slider tolerance visibile in un settings popover ⚙ della modale.
- **Auto-pair TRANSFER/FX_CONVERSION** (strutturalmente identici: entrambi usano `related_transaction_id` + `link_uuid`): quando user sceglie `type=TRANSFER` o `type=FX_CONVERSION` → auto-genera riga-coppia con `link_uuid` condiviso e segni invertiti. Le due righe sono editate insieme.
- **Duplicate banner** (da `BRIMDuplicateReport`): chip `⚠ 2 possible duplicates` → click espande pannello con checklist ignora/importa.
- **Validazione live**: debounced 500ms → `POST /transactions/validate` → banner errori per-riga + balance preview aggiornato.
- **Modalità-solo** (no route dedicata, sempre modale larga ~95vw × 90vh).

### Wireframe ASCII

```
╔══════════════════════════════════════════════════════════════════════════════════════╗
║ 📥 Staging — 8 tx ready · 2 unresolved · 2 possible duplicates            ⚙  [✕]  ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ Source: BRIM "Degiro CSV" · File: report_apr.csv · Broker: Degiro                   ║
║                                                                                      ║
║ 🎨 Asset groups: [🟦 VWCE▾] [🟨 BTC ▾] [🟥 AAPL▾] [🟩 unresolved 🔍"TSLA"▾] [+]   ║
║    ↑ ogni SearchSelect modifica tutte le righe di quel colore                       ║
║                                                                                      ║
║ Event matching tolerance: [──●────] 7 days    Auto-link on asset change: [✓]        ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ ☐│Date 🔽│Type🔽 │Asset (group) 🔍🔽│Qty 🔽 │Cash 🔽    │Link🔽│Evt🔽│✓│⋯ │         ║
║ ─┼───────┼───────┼───────────────────┼───────┼───────────┼──────┼─────┼─┼──┤         ║
║🟦│04-15  │🛒 BUY │VWCE               │+10.00 │-€1,050    │—     │—    │✓│⚙│         ║
║🟦│04-15  │🛒 BUY │VWCE               │+5.00  │-€525      │—     │—    │✓│⚙│         ║
║🟥│04-10  │💵 DIV │AAPL               │ 0     │+€12.40    │—     │🔗evt│✓│⚙│ ←auto   ║
║🟨│04-08  │🔄 XFER│BTC                │-0.5   │—          │pair A│—    │✓│⚙│         ║
║🟨│04-08  │🔄 XFER│BTC                │+0.5   │—          │pair A│—    │✓│⚙│         ║
║🟩│04-05  │🛒 BUY │🔍 "TSLA" unres.   │+3.00  │-$750      │—     │—    │✕│⚙│ ⚠       ║
║🟩│04-02  │💵 DIV │🔍 "MSFT" unres.   │ 0     │+$22       │—     │—    │✕│⚙│ ⚠       ║
║  │04-01  │💰 DEP │—                  │ 0     │+€2,000    │—     │—    │✓│⚙│         ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ ⚠ Row 3: AAPL dividend in DB il 2026-04-11 (1d off) → [Auto-link] [Ignore]          ║
║                                                                                      ║
║ Balance preview (Degiro): Cash EUR −€1,575 · Holdings VWCE +15                      ║
║                                                                                      ║
║      [Cancel]  [Validate (live)]  [Commit 6/8 tx ▸]  (2 unresolved blocked)         ║
╚══════════════════════════════════════════════════════════════════════════════════════╝

Icone: ⚙ row-actions (split asset, remove, duplicate, open event matcher)
       🔗evt = asset_event_id assegnato (click = popover evento)
```

### Sub-componenti pianificati

| Componente | Ruolo |
|------------|-------|
| `TransactionStagingModal.svelte` | Modale larga, stato locale `$state` con draft list |
| `StagingTable.svelte` | `DataTable` con celle editabili + color-band sinistra per gruppo asset |
| `AssetGroupSelector.svelte` | Riga di `SearchSelect` colorati sopra la tabella |
| `RowActions.svelte` | Menu ⚙ per riga (split-asset / remove / duplicate / event-matcher) |
| `EventSuggestionPopover.svelte` | Mostra risultato `events/suggest` |
| `BalancePreviewPanel.svelte` | Usa risposta `POST /transactions/validate` |
| `DuplicateBanner.svelte` | Da `BRIMDuplicateReport`, checklist ignora/importa |

### Modalità di apertura

| Modalità | Origine | Commit endpoint |
|----------|---------|-----------------|
| `create-manual` | Start vuoto, `+ Add row` | `POST /transactions` |
| `create-brim` | Pre-popolato da `BRIMParseResponse` | `POST /brokers/import/commit` (atomico + eventi) |
| `edit-bulk` | Pre-popolato da N `TXReadItem` → `TXUpdateItem` draft | `PATCH /transactions` |
| `clone-bulk` | Clone di N righe (id stripped) | `POST /transactions` |

### Deliverable
Modale unificata che copre i 4 ingressi, riusa `AssetModal` / `AssetMatchingWizard`, con validazione server live e commit atomico broker-aware.

---

## 🗂️ File da Creare / Modificare (riepilogo)

### Backend (modifiche)

| File | Modifica | Parte |
|------|----------|-------|
| `backend/app/db/models.py` | `Transaction.asset_event_id` FK + index | 1 |
| `backend/app/schemas/transactions.py` | `asset_event_id` in TXCreate/Update/Read, validator, `event_compatible` in `TX_TYPE_METADATA` | 1 |
| `backend/alembic/versions/001_initial.py` | Aggiungere colonna + indice | 1 |
| `backend/app/services/brim_provider.py` | Base class v2: `BRIMParseOutput`, `capabilities`, `preview_columns`, `docs_url` | 2 |
| `backend/app/services/brim_providers/*.py` (×11) | Refactor parse() alla nuova firma | 2 |
| `backend/app/schemas/brim.py` | `BRIMCapabilities`, `BRIMPreviewColumn`, `BRIMCommitRequest/Response`, `asset_events` in `BRIMParseResponse` | 2 |
| `backend/app/api/v1/brokers.py` | `POST /brokers/import/commit` atomico | 2 |
| `backend/app/api/v1/transactions.py` | Rimuovere `GET /{tx_id}`, uniformare access control, `POST /validate`, `POST /events/suggest` | 3 |
| `backend/app/services/transaction_service.py` | Generalizzare `_check_broker_access`, `validate_bulk`, `suggest_events` | 3 |
| `backend/app/services/file_preview.py` | **Nuovo**: dispatch preview per tipo (image/text/table/markdown/code) | 4b |
| `backend/app/schemas/uploads.py` | `FilePreviewResponse` + `FilePreviewMetadata` | 4b |
| `backend/app/api/v1/uploads.py` | `GET /files/{file_id}/preview` | 4b |
| `backend/app/api/v1/brokers.py` (import) | `GET /brokers/import/files/{file_id}/preview` | 4b |
| `backend/app/config.py` | `PREVIEW_MAX_LINES`, `PREVIEW_MAX_FILE_SIZE_MB` | 4b |

### Frontend (nuovi)

| File | Descrizione | Parte |
|------|-------------|-------|
| `src/routes/(app)/transactions/+page.svelte` | Lista con filtri header | 4 |
| `src/routes/(app)/transactions/+page.ts` | Load function | 4 |
| `src/lib/components/transactions/TransactionsTable.svelte` | Wrapper `DataTable` | 4 |
| `src/lib/components/transactions/TransactionTypeBadge.svelte` | Badge tipo da `TXTypeMetadata` | 4 |
| `src/lib/components/transactions/TransactionStagingModal.svelte` | Modale unificata | 5 |
| `src/lib/components/transactions/StagingTable.svelte` | Editable DataTable con color-band | 5 |
| `src/lib/components/transactions/AssetGroupSelector.svelte` | `SearchSelect` per colore | 5 |
| `src/lib/components/transactions/RowActions.svelte` | Menu ⚙ per riga | 5 |
| `src/lib/components/transactions/EventSuggestionPopover.svelte` | Popover eventi candidati | 5 |
| `src/lib/components/transactions/BalancePreviewPanel.svelte` | Preview bilanci dal validate | 5 |
| `src/lib/components/transactions/DuplicateBanner.svelte` | Banner duplicati BRIM | 5 |
| `src/lib/types/preview.ts` | Tipi TS `PreviewType`, `FilePreviewResponse` | 4b |
| `src/lib/utils/filePreview.ts` | `canPreview(filename)` | 4b |
| `src/lib/components/ui/media/FilePreviewModal.svelte` | Modale unificata preview | 4b |
| `src/lib/components/ui/media/ImagePreview.svelte` | Preview immagini con quality slider | 4b |
| `src/lib/components/ui/media/TextPreview.svelte` | Preview testo con line-range | 4b |
| `src/lib/components/ui/media/MarkdownPreview.svelte` | Preview markdown raw/rendered | 4b |
| `src/lib/components/ui/media/TablePreview.svelte` | Preview CSV/Excel via `DataTable` | 4b |
| `src/lib/components/ui/media/CodePreview.svelte` | Syntax highlighting | 4b |

### Frontend (modifiche)

| File | Modifica | Parte |
|------|----------|-------|
| `src/lib/components/brokers/BrokerImportFilesModal.svelte` | Dopo parse ok → emit event → Staging auto-open. Bottone 👁 Preview per riga (Parte 4b) | 4/4b/5 |
| `src/lib/components/files/FilesTable.svelte` | Bottone 👁 in colonna azioni (Static + BRIM tab) | 4b |
| `src/lib/api/*` | Rigenerare tipi dopo `./dev.py api sync` | tutte |

---

## 🔎 Considerazioni finali & Decisioni

| # | Decisione | Note |
|---|-----------|------|
| 1 | **Event-linking**: opt-in con auto-suggest slider 0–14gg alla selezione asset (create + edit) | Grouping per colore + SearchSelect per bulk-assign di tutte le righe dello stesso gruppo |
| 2 | **No legacy BRIM**: rompo firma `parse()` in tutti gli 11 plugin, niente wrapper | La v1 non è mai andata in produzione |
| 3 | **Solo modale, niente route dedicata** | Modale larga ~95vw × 90vh sufficiente per tutti i flussi |
| 4 | **FX_CONVERSION ≡ TRANSFER** strutturalmente | Entrambi usano `related_transaction_id` + `link_uuid`, auto-pair in Staging |
| 5 | **Round 12 completato** ✅ | AssetEvent infrastructure operativa, Parte 1 può procedere |
| 6 | **Full-bulk API** | Niente `GET/DELETE /transactions/{id}`, tutto via liste di ID |
| 7 | **Riuso endpoint esistenti** | `GET /brokers` è già filtrato per access → niente `accessible-brokers` nuovo |
| 8 | **Smart assistant retroattivo** (matching eventi ↔ transazioni storiche) | Posticipato a Phase 8+ |
| 9 | **Regimi fiscali / Cash Split / Over-Sell Protection** | Posticipati a Phase 8+ (erano nel piano originale `plan-phase05-to-08-upgrade.md §6` ma fuori scope MVP) |
| 10 | **File Preview System** incorporato come Parte 4b | Assorbe il vecchio `plan-phase7b-filePreview.md`. Allineato a Svelte 5 runes + `ModalBase` + `DataTable` esistenti. Autonomo rispetto al modello transazioni: può essere implementato in parallelo a Parti 1–3 se ci sono risorse |

---

## ✅ Verifica Completamento

### Test manuali end-to-end
- [ ] Lista transazioni visibile con filtri colonna funzionanti
- [ ] GoTo linked pair: click 🔗 → scroll + pulse su riga related
- [ ] Badge ●evt visibile su transazioni con `asset_event_id`
- [ ] `+ New` apre Staging vuota → add rows → validate → commit OK
- [ ] Clone bulk: 3 righe selezionate → `📋 Clone to staging` → Staging pre-popolata
- [ ] Edit bulk: 3 righe selezionate → `✎ Edit bulk` → Staging in mode edit → PATCH OK
- [ ] Delete bulk con conferma
- [ ] Import → upload file → parse → Staging auto-apre con BRIM data + eventi
- [ ] Asset grouping: cambio asset via `SearchSelect` globale → tutte le righe del colore aggiornate
- [ ] Split asset: 🎨 su una riga → nuovo gruppo-colore creato
- [ ] Event tolerance slider 0/7/14 → comportamento corretto
- [ ] Auto-pair TRANSFER: selezione `type=TRANSFER` su una riga → auto-crea riga coppia
- [ ] VIEWER su broker → no bottoni edit/delete/create
- [ ] Duplicati BRIM: banner + checklist funziona
- [ ] **Parte 4b**: Bottone 👁 visibile solo su file supportati
- [ ] **Parte 4b**: Preview CSV BRIM mostra `DataTable` con row-range
- [ ] **Parte 4b**: Preview immagine con quality slider funzionante
- [ ] **Parte 4b**: Preview markdown toggle raw/rendered
- [ ] **Parte 4b**: File binario → nessun bottone preview
- [ ] **Parte 4b**: Preview accessibile da Files page + `BrokerImportFilesModal`

### Test backend
- [ ] Access matrix OWNER/EDITOR/VIEWER × verb × owned/foreign broker
- [ ] `POST /transactions/validate` senza side-effect
- [ ] `POST /transactions/events/suggest` tolleranze varie
- [ ] `asset_event_id` validator rifiuta mismatch
- [ ] `POST /brokers/import/commit` rollback atomico su failure
- [ ] Copertura ≥85% su `transaction_service` e `brim_provider`

---

## 📎 Dipendenze & Sblocca

- **Richiede**:
  - Phase 4 (Brokers + BrokerUserAccess) ✅
  - Phase 5 (FX) ✅
  - Phase 6 (Assets + AssetModal) ✅
  - Phase 6 Step 3 Round 12 (AssetEvent) ✅
  - Phase 6 Step 5 (AssetMatchingWizard) — se non pronto, fallback a `AssetModal`
- **Sblocca**: Phase 8 (Dashboard consuma transazioni + eventi per P&L e distribuzioni)

---

## 📁 Archivio previsto (post-completamento)

```
phases/phase-07-subplan/
├── README.md
├── plan-phase07Part1-DbSchemaRealignment.prompt.md        (Parte 1)
├── plan-phase07Part2-BrimPluginV2.prompt.md               (Parte 2)
├── plan-phase07Part3-ApiConsolidation.prompt.md           (Parte 3)
├── plan-phase07Part4-TransactionsPage.prompt.md           (Parte 4)
├── plan-phase07Part4b-FilePreviewSystem.prompt.md         (Parte 4b)
└── plan-phase07Part5-StagingModal.prompt.md               (Parte 5)
```

---

**Prossimo passo**: creare il **piano di dettaglio della Parte 1**
(`plan-phase07Part1-DbSchemaRealignment.prompt.md`), prerequisito diretto di tutto il
resto (senza `asset_event_id` FK non si può né estendere BRIM né costruire il frontend).
