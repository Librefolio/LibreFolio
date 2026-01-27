# Piano Implementazione BRIM Multi-User

**Data**: 22 Gennaio 2026  
**Ultimo Aggiornamento**: 26 Gennaio 2026  
**Status**: ✅ COMPLETATO (Backend + Frontend Fase 4)  
**Dipendenze**: Analisi in `analysis-brim-multiuser.md`  
**Decisione**: Proposta ACCETTATA

---

## Riepilogo Decisioni

1. ✅ **Broker obbligatorio all'upload**: Il file BRIM deve essere associato a un broker al momento dell'upload, dopotutto un export da broker ha senso essere importato nello stesso
   broker
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

### 4.8 Migrazione a Zodios + Libreria Tipi TypeScript

**Data**: 27 Gennaio 2026  
**Status**: 🔄 IN PROGRESS  
**Stima**: 4-6 ore

---

#### Problema Identificato

1. **Tipi inline duplicati**: I tipi TypeScript per le entità backend sono definiti inline in vari componenti
2. **Client API manuale**: `client.ts` non sfrutta validazione runtime né type-safety automatica
3. **Schemi Zod inutilizzati**: `generated.ts` contiene schemi Zod e client Zodios non utilizzati

#### Soluzione: Zodios + Tipi Derivati da Zod

Sfruttare `openapi-zod-client` che già genera:

- **Schemi Zod** per validazione runtime delle risposte API
- **Client Zodios** type-safe con autocomplete
- **Tipi TypeScript** derivabili con `z.infer<typeof schema>`

---

#### Architettura Target

```
/lib/
├── api/
│   ├── generated.ts      # Auto-generato da OpenAPI (NON modificare)
│   ├── index.ts          # Export client Zodios wrappato + ApiError
│   └── client.ts         # DA RIMUOVERE dopo migrazione
│
└── types/
    ├── index.ts          # Barrel export di tutti i tipi
    ├── broker.ts         # Tipi broker derivati da Zod + UI-only
    ├── files.ts          # Tipi file (upload, BRIM)
    ├── transaction.ts    # Tipi transazione
    ├── user.ts           # Tipi utente/auth
    ├── settings.ts       # Tipi settings
    └── ui.ts             # Tipi frontend-only (props, state)
```

#### Come Funziona

```typescript
// /lib/types/broker.ts
import {z} from 'zod';
import {schemas} from '$lib/api/generated';

// Tipi derivati dagli schemi Zod (sincronizzati col backend)
export type Broker = z.infer<typeof schemas.BRReadItem>;
export type BrokerSummary = z.infer<typeof schemas.BRSummary>;
export type BrokerCreateItem = z.infer<typeof schemas.BRCreateItem>;

// Tipi frontend-only (stato UI)
export interface BrokerWithUIState extends Broker {
    isSelected?: boolean;
    isLoading?: boolean;
}
```

#### Vantaggi

| Prima (client manuale)                                 | Dopo (Zodios)                                            |
|--------------------------------------------------------|----------------------------------------------------------|
| `api.get<Broker[]>('/brokers')` - tipo "fiducia cieca" | `api.list_brokers_api_v1_brokers_get()` - tipo garantito |
| Nessuna validazione runtime                            | Validazione Zod automatica                               |
| Tipi definiti inline                                   | Tipi derivati da OpenAPI                                 |
| Errori a runtime se API cambia                         | Errori a compile-time                                    |

---

#### Analisi Dipendenze - File da Migrare

**Chiamate API trovate**: 28 chiamate in 16 file

| File                                                 | Chiamate API | Tipi Inline                              | Priorità            |
|------------------------------------------------------|--------------|------------------------------------------|---------------------|
| `lib/api/client.ts`                                  | -            | `ApiCallOptions`, `ApiError`             | P0 - Da sostituire  |
| `lib/stores/auth.ts`                                 | 4            | `AuthUser`, `AuthState`                  | P1 - Auth base      |
| `lib/stores/settings.ts`                             | ?            | -                                        | P1 - Settings store |
| `lib/components/auth/RegisterModal.svelte`           | 1            | -                                        | P1 - Auth           |
| `lib/components/settings/ProfileTab.svelte`          | ?            | -                                        | P1 - Settings       |
| `lib/components/settings/PasswordChangeModal.svelte` | ?            | -                                        | P1 - Settings       |
| `lib/components/settings/AboutTab.svelte`            | ?            | -                                        | P1 - Settings       |
| `lib/components/settings/GlobalSettingsTab.svelte`   | ?            | -                                        | P1 - Settings       |
| `lib/components/settings/PreferencesTab.svelte`      | 9            | `CurrencyInfo`                           | P1 - Settings       |
| `lib/components/brokers/BrokerModal.svelte`          | 2            | -                                        | P2 - Broker         |
| `lib/components/brokers/BrokerForm.svelte`           | 2            | -                                        | P2 - Broker         |
| `lib/components/brokers/BrokerIcon.svelte`           | 1            | -                                        | P2 - Broker         |
| `lib/components/brokers/CashTransactionModal.svelte` | 2            | -                                        | P2 - Broker         |
| `lib/components/brokers/BrokerSelect.svelte`         | 0            | `Broker`                                 | P2 - Broker         |
| `lib/components/ImportPluginSelect.svelte`           | 1            | `ImportPlugin`                           | P2 - Broker         |
| `routes/(app)/brokers/+page.svelte`                  | 3            | `Broker`, `BrokerSummary`                | P3 - Pages          |
| `routes/(app)/brokers/[id]/+page.svelte`             | 2            | `BrokerSummary`, `Transaction`           | P3 - Pages          |
| `routes/(app)/files/+page.svelte`                    | 5            | `UploadedFile`, `BrimFile`, `Broker`     | P3 - Pages          |
| `lib/components/files/FilesTable.svelte`             | 0            | `UploadedFile`, `BrimFile`, `BrokerInfo` | P3 - Files          |

**Schemi Zod disponibili in `generated.ts`** (riga 3168: `export const schemas`):

- Auth: `AuthUserResponse`, `AuthLoginResponse`, `AuthMeResponse`, `AuthRegisterRequest`, `AuthRegisterResponse`, `AuthLoginRequest`
- Settings: `UserSettingsRead`, `UserSettingsUpdate`, `GlobalSettingRead`, `GlobalSettingsListResponse`, `GlobalSettingUpdate`
- Broker: `BRReadItem`, `BRSummary`, `BRCreateItem`, `BRAssetHolding`
- BRIM: `BRIMFileInfo`, `BRIMFileStatus`, `BRIMPluginInfo`, `BRIMParseResponse`
- Files: `UploadFileInfo`
- Transaction: `TXReadItem`, `TXCreateItem_Input`, `TXCreateItem_Output`

---

#### Piano di Implementazione

##### Step 1: Infrastruttura Base (P0)

- [x] **1.1** Aggiornare `./dev.py api sync` per rigenerare `generated.ts` ✅
- [x] **1.2** Verificare che `schemas` sia esportato in `generated.ts` ✅ (riga 5359)
- [x] **1.3** Integrare `api sync` nel build frontend ✅
    - `./dev.py front build` ora esegue `api sync` prima di `npm run build`
    - Garantisce che i tipi siano sempre allineati col backend
- [x] **1.4** Creare `/lib/types/index.ts` (barrel export) ✅
- [x] **1.5** Creare `/lib/types/*.ts` (tutti i file di tipi) ✅
    - `common.ts`: Currency, UserRole, TransactionType, AssetType, IdentifierType
    - `user.ts`: AuthUser, AuthLoginResponse, AuthMeResponse, AuthState
    - `settings.ts`: UserSettings, GlobalSetting, Theme, SupportedLocale
    - `broker.ts`: Broker, BrokerSummary, BrokerAccessItem, BrokerInfo
    - `transaction.ts`: Transaction, TransactionCreateItem, TransactionTypeMetadata
    - `files.ts`: UploadedFile, BrimFile, BrimPlugin, BrimParseResponse
    - `asset.ts`: AssetMetadata, AssetInfo, AssetProviderInfo, PricePoint
- [x] **1.6** Aggiornare `/lib/api/index.ts` per esportare `schemas` ✅
- [x] **1.7** Fix backend docstring backticks in `IdentifierType` ✅
    - I backtick nel docstring rompevano il file generated.ts

**Dettaglio contenuti file:**

```typescript
// =========================================
// /lib/types/index.ts - Barrel export
// =========================================
// Re-esporta tutti i tipi dai file di dominio
// Permette: import type { Broker, AuthUser, BrimFile } from '$lib/types';

export * from './common';
export * from './user';
export * from './settings';
export * from './broker';
export * from './transaction';
export * from './files';
// NO ui.ts qui - quelli sono per uso interno dei componenti
```

```typescript
// =========================================
// /lib/types/common.ts - Tipi utility condivisi
// =========================================
// Tipi base usati in più domini, derivati da Zod

import {z} from 'zod';
import {schemas} from '$lib/api/generated';

// Valuta con codice e importo (usato ovunque: balances, transazioni, prezzi)
export type Currency = z.infer<typeof schemas.Currency_Output>;

// Ruoli utente per accesso broker
export type UserRole = z.infer<typeof schemas.UserRole>;

// Tipi di transazione
export type TransactionType = z.infer<typeof schemas.TransactionType>;

// Tipi di asset
export type AssetType = z.infer<typeof schemas.AssetType>;
```

```typescript
// =========================================
// /lib/api/index.ts - Client API wrapper
// =========================================
// Wrappa il client Zodios generato aggiungendo:
// - Headers custom (Accept-Language, credentials)
// - Gestione errori centralizzata
// - Redirect 401 → login

import {createApiClient} from './generated';
import {browser} from '$app/environment';
import {goto} from '$app/navigation';

// Crea client con configurazione custom
const baseClient = createApiClient('/api/v1', {
    // Zodios permette di passare un custom fetch
    // che aggiunge headers e gestisce errori
});

// Wrapper con headers e error handling
export const api = /* wrapper del baseClient */;

// Re-export per retrocompatibilità durante migrazione
export {ApiError} from './client';  // Temporaneo, poi rimuovere

// Re-export schemas per derivare tipi in /lib/types/
export {schemas} from './generated';
```

**Chiarimento su `/lib/api/index.ts`**:

Il wrapper **NON** gestisce l'autenticazione - quella è responsabilità del backend tramite session cookies HTTP-only.

| Responsabilità                      | Chi lo fa                                              |
|-------------------------------------|--------------------------------------------------------|
| Verificare se utente è loggato      | **Backend** (session middleware)                       |
| Inviare cookie con richieste        | **Browser** automaticamente (`credentials: 'include'`) |
| Gestire 401 e fare redirect         | **`/lib/api/index.ts`**                                |
| Aggiungere header `Accept-Language` | **`/lib/api/index.ts`**                                |

Il wrapper garantisce che:

1. Ogni richiesta includa i cookies di sessione (`credentials: 'include'`)
2. L'header `Accept-Language` sia sempre presente per i18n
3. Se il backend risponde 401 (sessione scaduta/invalida), l'utente venga rediretto al login

**Nota su `language.ts`**: È puramente frontend (gestisce localStorage + svelte-i18n), non fa chiamate API, quindi **non va migrato**.

##### Step 2: Tipi Auth & Settings (P1)

- [ ] **2.1** Creare `/lib/types/user.ts`:
    - `AuthUser` da `schemas.AuthUserResponse`
    - `AuthLoginResponse`, `AuthMeResponse`, `AuthRegisterResponse`
- [ ] **2.2** Creare `/lib/types/settings.ts`:
    - `UserSettings` da `schemas.UserSettingsRead`
    - `GlobalSetting` da `schemas.GlobalSettingRead`
- [ ] **2.3** Migrare `lib/stores/auth.ts` al nuovo client + tipi
- [ ] **2.4** Migrare `lib/stores/settings.ts`
- [ ] **2.5** Migrare componenti auth (`RegisterModal.svelte`)
- [ ] **2.6** Migrare componenti settings (`ProfileTab`, `PreferencesTab`, `GlobalSettingsTab`, etc.)

##### Step 3: Tipi Broker (P2)

- [ ] **3.1** Creare `/lib/types/broker.ts`:
    - `Broker` da `schemas.BRReadItem`
    - `BrokerSummary` da `schemas.BRSummary`
    - `BrokerCreateItem` da `schemas.BRCreateItem`
- [ ] **3.2** Creare `/lib/types/transaction.ts`:
    - `Transaction` da `schemas.TXReadItem`
- [ ] **3.3** Migrare componenti broker al nuovo client
- [ ] **3.4** Rimuovere tipi inline da componenti broker

##### Step 4: Tipi File (P3)

- [ ] **4.1** Creare `/lib/types/files.ts`:
    - `UploadedFile` da `schemas.UploadFileInfo`
    - `BrimFile` da `schemas.BRIMFileInfo`
    - `BrimPlugin` da `schemas.BRIMPluginInfo`
- [ ] **4.2** Migrare `/routes/(app)/files/+page.svelte`
- [ ] **4.3** Migrare `FilesTable.svelte`
- [ ] **4.4** Rimuovere tipi inline da componenti file

##### Step 5: Cleanup (P4)

- [ ] **5.1** Rimuovere `client.ts` vecchio
- [ ] **5.2** Aggiornare tutti gli import
- [ ] **5.3** Verificare build senza errori
- [ ] **5.4** Test manuale delle funzionalità
- [ ] **5.5** Aggiornare `00_project_welcome_agent.md` documentando l'uso che stiamo facendo di zod nel frontend e le linee guida da seguire per lo sviluppo dei prossimi componenti.

---

#### Note Tecniche

**Post-processing per export tipi**: Gli schemi Zod in `generated.ts` sono esportati via oggetto `schemas`, ma i tipi TypeScript no. Usiamo `z.infer<typeof schemas.X>` per
derivarli.

**Wrapper Zodios**: Il client Zodios generato non include headers custom. Creiamo un wrapper che:

- Aggiunge `Accept-Language` header
- Gestisce redirect 401 → login
- Mantiene `credentials: 'include'` per cookies

**Ordine migrazione**: Seguire l'ordine P0→P4 per evitare import circolari. Auth e stores prima, poi componenti, poi pagine.

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

| Fase       | Descrizione            | Stima     |
|------------|------------------------|-----------|
| 1          | Schema e Storage       | 2-3h      |
| 2          | Endpoint Modifications | 2-3h      |
| 3          | Migration & Tests      | 1-2h      |
| 4          | Frontend Files Page    | 2-3h      |
| 5          | Frontend Broker Page   | 1-2h      |
| **Totale** |                        | **8-13h** |

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
