# Piano Implementazione BRIM Multi-User

**Data**: 22 Gennaio 2026  
**Ultimo Aggiornamento**: 26 Gennaio 2026  
**Status**: ✅ COMPLETATO (Backend + Frontend Fase 4)  
**Dipendenze**: Analisi in `analysis-brim-multiuser.md`  
**Decisione**: Proposta ACCETTATA

---

## Riepilogo Decisioni

1. ✅ **Broker obbligatorio all'upload**: Il file BRIM deve essere associato a un broker al momento dell'upload, dopotutto un export da broker ha senso essere importato nello stesso broker
2. ✅ **Permessi basati su ruolo broker**: VIEWER=read, EDITOR+=write/delete
3. ✅ **Filtro multi-broker**: Frontend con checkbox multiple
4. ✅ **Storage per broker**: Sottocartelle `broker_{id}/` dentro le cartelle status
5. ✅ **Parse result caching**: Salvare risultato parsing nel JSON del file

---

## ✅ Fase 1: Backend - Schema e Storage (COMPLETATA 23-01-2026)

### 1.1 Estendere BRIMFileInfo Schema ✅

**File**: `backend/app/schemas/brim.py`

```python
class BRIMFileInfo(BaseModel):
    # Campi esistenti
    file_id: str
    filename: str
    size_bytes: int
    status: BRIMFileStatus
    uploaded_at: datetime
    processed_at: Optional[datetime]
    compatible_plugins: List[str]
    error_message: Optional[str]
    
    # NUOVI CAMPI ✅
    uploaded_by_user_id: Optional[int] = None
    target_broker_id: Optional[int] = None
    last_parse_result: Optional[dict] = None
```

### 1.2 Modificare Storage Structure ✅

**File**: `backend/app/services/brim_provider.py`

Struttura target:
```
broker_reports/
├── uploaded/
│   ├── broker_1/
│   │   ├── {uuid}.csv
│   │   └── {uuid}.json
│   └── broker_2/
├── parsed/
│   └── broker_1/
└── failed/
    └── broker_1/
```

**Modifiche completate**:
- [x] `_ensure_dirs()`: Crea sottocartelle broker on-demand
- [x] `_get_folder_for_status()`: Supporta broker_id
- [x] `save_uploaded_file()`: Accetta `user_id` e `broker_id`, salva in sottocartella
- [x] `list_files()`: Supporta filtro `broker_ids: List[int]`, cerca nelle sottocartelle
- [x] `get_file_info()`: Cerca in tutte le sottocartelle broker
- [x] `get_file_path()`: Supporta sottocartelle broker
- [x] `delete_file()`: Supporta sottocartelle broker

### 1.3 Caching Parse Result ✅

Campo `last_parse_result` aggiunto a BRIMFileInfo e metadata JSON.

---

## ✅ Fase 2: Backend - Endpoint Modifications (COMPLETATA 23-01-2026)

### 2.1 Modificare Upload Endpoint ✅

**Endpoint**: `POST /api/v1/brokers/import/upload`

**Modifiche completate**:
- [x] Aggiunto parametro `broker_id` (obbligatorio)
- [x] Verifica permessi utente sul broker (EDITOR+)
- [x] Salva `uploaded_by_user_id` e `target_broker_id`

### 2.2 Modificare List Files Endpoint ✅

**Endpoint**: `GET /api/v1/brokers/import/files`

**Modifiche completate**:
- [x] Aggiunto parametro `broker_ids: List[int]` (opzionale)
- [x] Filtra per broker accessibili all'utente
- [x] Superuser vede tutto
- [x] Aggiunto metodo `get_accessible_broker_ids()` a BrokerService

### 2.3 Modificare Get/Delete/Download Endpoints ✅

**Modifiche completate**:
- [x] `GET /files/{file_id}` - verifica accesso broker (VIEWER+)
- [x] `DELETE /files/{file_id}` - verifica accesso broker (EDITOR+)
- [x] `GET /files/{file_id}/download` - verifica accesso broker (VIEWER+)

### 2.4 Nuovo Endpoint: Load Cached Parse ✅

**Endpoint**: `GET /api/v1/brokers/import/files/{file_id}/last-parse`

- [x] Ritorna `last_parse_result` dal metadata
- [x] Verifica permessi broker

### 2.5 Modificare Parse Endpoint ✅

- [x] Aggiunta verifica permessi (EDITOR+)

---

## 📋 Fase 3: Backend - Migration & Tests ✅ COMPLETED (24-01-2026)

### 3.1 Migration Script

**Approccio Alpha Reset** (raccomandato):
```bash
# Pulisci tutti i file esistenti
rm -rf backend/data/broker_reports/*

# Ricrea struttura base
mkdir -p backend/data/broker_reports/{uploaded,parsed,failed}

# Ricrea i .gitkeep
touch backend/data/broker_reports/uploaded/.gitkeep
touch backend/data/broker_reports/parsed/.gitkeep
touch backend/data/broker_reports/failed/.gitkeep
```

### 3.2 Tests ✅

Test API aggiornati per coprire tutti i nuovi comportamenti multi-user:

- [x] Test upload con broker_id (MU-001, MU-002)
- [x] Test list files con filtro broker_ids (MU-003)
- [x] Test permessi accesso broker (MU-004) - upload negato senza accesso
- [x] Test parse con caching result (MU-006)
- [x] Test load-last-parse endpoint (MU-007)
- [x] Test download file endpoint (MU-009)
- [x] Fix `_move_file` per gestire sottocartelle broker
- [x] Fix `save_parse_result` per cercare in sottocartelle broker

**Risultato**: 22/22 test BRIM passati

---

## ✅ Fase 4: Frontend - Files Page (COMPLETATA 27-01-2026)

### 4.1 Filtro Multi-Broker ✅

- [x] Filtro broker ora integrato come filtro colonna enum
- [x] Mostra solo broker accessibili
- [x] Superuser vede tutti i broker

### 4.2 Colonna Broker ✅

- [x] Nuova colonna "Broker" nella tabella Report Broker
- [x] Mostra nome broker dal mapping interno
- [x] Badge colorato per broker (colori generati algoritmicamente da hue rotation)
- [x] Supporto multi-lingua per traduzioni

### 4.3 Upload con Broker Selection ✅

- [x] Upload richiede broker_id (passato da pagina)
- [x] FileUploader: aggiunto parametro `accept` per filtro tipi file
- [x] Supporto `.csv,.xlsx,.xls` per report broker
- [x] Modale conferma chiusura uploader con file in sospeso (sia static che brim)
- [x] Pulsante cambia da "Carica" a "Chiudi" quando uploader aperto
- [x] **Modale assegnazione broker per-file**: 
  - Appare appena si selezionano file (via evento `on:change`)
  - Sezione "Assegna tutti a" per assegnazione batch
  - Lista file con dropdown broker individuale
  - Pulsante "Carica" grigio se non tutti i broker assegnati
  - Dopo upload, broker usati aggiunti automaticamente ai filtri

### 4.4 Icone File Migliorate ✅

- [x] Icone specifiche per: immagini, video, audio, spreadsheet, JSON, code, archivi, PDF, testi
- [x] Icona non si riduce troppo su schermi stretti (flex-shrink: 0)

### 4.5 Stati File Corretti ✅

- [x] Rimosso stato "processing" non esistente (era refuso)
- [x] Rimosso stato "imported" non esistente
- [x] Stati validi: uploaded, parsed, failed, error

### 4.6 Fix e Miglioramenti ✅

- [x] Pagination: layout 2 righe mobile corretto
- [x] Page size selector funziona correttamente su mobile
- [x] Rimosso warning CSS `.dropdown-icon` unused
- [x] `broker_ids` parameter inviato come lista di int (non stringa)
- [x] Traduzioni complete per uploads (selectBroker, selected, chooseBroker, assignBrokers, assignAll, file, etc.)

### 4.7 Miglioramenti Dropdown Broker ✅ (27-01-2026)

**Obiettivo**: Migliorare l'UX del dropdown broker nella modale di upload BRIM.

**Implementato**:
- [x] Componente `BrokerSelect.svelte` con stile custom
- [x] Icona broker prima del nome (riusa BrokerIcon.svelte)
- [x] **Ricerca inline nel bottone**: quando si apre, il bottone mostra 🔍 + input
  - Focus automatico quando si apre
  - Query cancellata quando si chiude
  - Navigazione tastiera (ArrowUp/Down, Enter, Escape)
- [x] Chiusura automatica altri dropdown quando se ne apre uno nuovo (via CustomEvent)
- [x] **Click fuori chiude il dropdown** (usa mousedown con capture)
- [x] Prop `dropdownDirection` per scegliere se aprire verso l'alto ('up') o il basso ('down')
- [x] "Assegna tutti a:" usa `dropdownDirection="down"` per evitare troncamento
- [x] **Max 3 elementi visibili** nella lista (132px), poi scroll
- [x] **Allineamento "Assegna tutti"**: label con `flex: 1` spinge il dropdown a destra
- [x] **Fix posizionamento file-row**: aggiunto `position: relative` per dropdown corretto
- [x] Funzionamento corretto su mobile
- [x] Build senza warning CSS

### 4.8 Libreria Tipi TypeScript Riutilizzabili (TODO)

**Problema identificato**: I tipi TypeScript per le entità backend sono definiti inline in vari componenti, causando duplicazione e possibili inconsistenze.

**File con tipi inline da consolidare**:

| File | Tipi Definiti | Note |
|------|---------------|------|
| `/routes/(app)/brokers/+page.svelte` | `Broker`, `BrokerSummary` | Versione completa con tutti i campi |
| `/routes/(app)/brokers/[id]/+page.svelte` | `BrokerSummary`, `Transaction` | Estende Broker con holdings/balances |
| `/routes/(app)/files/+page.svelte` | `Broker` (semplificato) | Solo id, name |
| `/lib/components/files/FilesTable.svelte` | `BrimFile`, `BrokerInfo`, `UploadedFile` | Tipi per file upload |
| `/lib/components/brokers/BrokerSelect.svelte` | `Broker` | Definito inline |

**Struttura proposta** - Creare `/lib/types/index.ts`:

```typescript
// /lib/types/index.ts

// ============================================
// BROKER TYPES
// ============================================
export interface Broker {
  id: number;
  name: string;
  description?: string | null;
  portal_url?: string | null;
  icon_url?: string | null;
  default_import_plugin?: string | null;
  allow_cash_overdraft: boolean;
  allow_asset_shorting: boolean;
  is_active: boolean;
  opened_at?: string | null;
}

export interface BrokerWithBalances extends Broker {
  cash_balances: CashBalance[];
  holdings: Holding[];
}

export interface CashBalance {
  code: string;
  amount: number;
  symbol?: string;
}

export interface Holding {
  asset_id: number;
  asset_name?: string;
  quantity?: number;
}

// ============================================
// FILE TYPES
// ============================================
export interface UploadedFile {
  file_id: string;
  original_name: string;
  status: string;
  uploaded_at: string;
  size_bytes?: number;
  content_type?: string;
}

export interface BrimFile {
  file_id: string;
  filename: string;
  status: 'uploaded' | 'parsed' | 'failed' | 'error';
  uploaded_at: string;
  size_bytes?: number;
  compatible_plugins?: string[];
  error_message?: string | null;
  uploaded_by_user_id?: number;
  target_broker_id?: number;
  last_parse_result?: ParseResult | null;
}

export interface ParseResult {
  transactions: ParsedTransaction[];
  warnings: string[];
  asset_mappings: AssetMapping[];
  duplicates_report: DuplicatesReport;
}

export interface ParsedTransaction {
  date: string;
  type: string;
  quantity?: number;
  amount: number;
  currency: string;
  description?: string;
  asset_identifier?: string;
  fake_asset_id?: number;
}

export interface AssetMapping {
  fake_asset_id: number;
  original_identifier: string;
  suggested_asset_id?: number;
  suggested_asset_name?: string;
}

export interface DuplicatesReport {
  tx_unique_indices: number[];
  possible_duplicates: DuplicateGroup[];
  likely_duplicates: DuplicateGroup[];
}

export interface DuplicateGroup {
  new_tx_index: number;
  existing_tx_ids: number[];
  match_score: number;
}

// ============================================
// TRANSACTION TYPES
// ============================================
export interface Transaction {
  id: number;
  type: string;
  date: string;
  currency: string;
  total_amount: number;
  quantity?: number;
  unit_price?: number;
  asset_id?: number;
  asset_name?: string;
  broker_id: number;
  description?: string;
}

// ============================================
// USER TYPES
// ============================================
export interface User {
  id: number;
  username: string;
  email?: string;
  is_superuser: boolean;
  is_active: boolean;
}

// ============================================
// ASSET TYPES
// ============================================
export interface Asset {
  id: number;
  name: string;
  symbol?: string;
  isin?: string;
  asset_type: string;
  currency?: string;
}
```

**Implementazione**:
- [ ] Creare file `/lib/types/index.ts`
- [ ] Esportare tutti i tipi dal barrel file
- [ ] Aggiornare `BrokerSelect.svelte` per usare `import type { Broker } from '$lib/types'`
- [ ] Aggiornare `/routes/(app)/brokers/+page.svelte`
- [ ] Aggiornare `/routes/(app)/brokers/[id]/+page.svelte`
- [ ] Aggiornare `/routes/(app)/files/+page.svelte`
- [ ] Aggiornare `/lib/components/files/FilesTable.svelte`
- [ ] Aggiungere alias `$lib/types` in `svelte.config.js` se necessario
- [ ] Verificare che build passi senza errori TypeScript

**Benefici**:
- Singola fonte di verità per i tipi
- Autocomplete IDE migliorato
- Refactoring più sicuro
- Documentazione implicita delle API

---

## Fase 5: Frontend - Broker Page Integration (1-2 ore)

### 5.1 Tab/Sezione Files

- [ ] Riusare `FilesTableAdvanced` (o futuro `DataTable`)
- [ ] `broker_id` implicito dalla pagina
- [ ] Filtro broker nascosto (singolo broker)

### 5.2 Upload Diretto

- [ ] Button "Upload" nella sezione files
- [ ] `broker_id` automatico

---

## Timeline Stimata

| Fase | Descrizione | Stima |
|------|-------------|-------|
| 1 | Schema e Storage | 2-3h |
| 2 | Endpoint Modifications | 2-3h |
| 3 | Migration & Tests | 1-2h |
| 4 | Frontend Files Page | 2-3h |
| 5 | Frontend Broker Page | 1-2h |
| **Totale** | | **8-13h** |

---

## Checklist Pre-Implementazione

- [ ] Backup database esistente
- [ ] Documentare struttura file attuale
- [ ] Creare branch `feature/brim-multiuser`

## Checklist Post-Implementazione

- [ ] Tutti i test passano
- [ ] Documentazione API aggiornata
- [ ] File README aggiornato se necessario
- [ ] Merge in `dev`
