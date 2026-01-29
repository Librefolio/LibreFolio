# Analisi Backend BRIM per Multi-User/Multi-Broker Support

**Data**: 22 Gennaio 2026  
**Status**: 📋 ANALISI v2 - Decisioni Aggiornate

---

## Contesto Sistema Esistente

### Modello Permessi Broker (Già Implementato)

Il sistema ha già un modello di accesso a 3 livelli per i broker:

```python
class UserRole(str, Enum):
    OWNER = "OWNER"  # Full access: CRUD broker, manage access, delete
    EDITOR = "EDITOR"  # Modify broker/transactions, can only remove self
    VIEWER = "VIEWER"  # Read-only access
```

**API esistenti:**

- `GET /brokers/{id}/access` - Lista utenti con accesso
- `POST /brokers/{id}/access` - Aggiungi accesso (solo OWNER)
- `PATCH /brokers/{id}/access/{user_id}` - Modifica ruolo (solo OWNER)
- `DELETE /brokers/{id}/access/{user_id}` - Rimuovi accesso

**Superuser**: Ha accesso a tutti i broker indipendentemente dai permessi.

---

## Situazione Attuale BRIM

### Schema BRIMFileInfo Attuale

```python
class BRIMFileInfo(BaseModel):
    file_id: str           # UUID del file
    filename: str          # Nome originale
    size_bytes: int        # Dimensione
    status: BRIMFileStatus # uploaded | parsed | imported | failed
    uploaded_at: datetime
    processed_at: Optional[datetime]
    compatible_plugins: List[str]
    error_message: Optional[str]
```

### Problemi

1. ❌ **Nessun `uploaded_by_user_id`** - Chi ha caricato il file
2. ❌ **Nessun `target_broker_id`** - File non associato a broker
3. ❌ L'upload avviene senza specificare il broker
4. ❌ Non c'è filtro per broker nella lista files

---

## Confronto Flussi: Attuale vs Proposto

### Endpoint Attuali BR IMPORT

| Metodo | Endpoint                                          | Descrizione                       |
|--------|---------------------------------------------------|-----------------------------------|
| GET    | `/api/v1/brokers/import/files`                    | Lista tutti i file caricati       |
| GET    | `/api/v1/brokers/import/files/{file_id}`          | Dettagli file specifico           |
| DELETE | `/api/v1/brokers/import/files/{file_id}`          | Elimina file                      |
| GET    | `/api/v1/brokers/import/files/{file_id}/download` | Download file                     |
| POST   | `/api/v1/brokers/import/files/{file_id}/parse`    | Parse file → preview transactions |
| GET    | `/api/v1/brokers/import/plugins`                  | Lista plugin disponibili          |
| POST   | `/api/v1/brokers/import/upload`                   | Upload file (senza broker!)       |

### Flusso ATTUALE (ipotetico)

```
1. Upload file
   POST /brokers/import/upload
   → File salvato senza associazione broker
   → Nessun controllo permessi su broker
   
2. Parse file  
   POST /brokers/import/files/{id}/parse
   Body: { plugin_code, broker_id }
   → Ritorna lista transazioni preview
   → Il broker_id è specificato QUI, non all'upload
   
3. Frontend fa mapping/review
   → Utente conferma le transazioni
   
4. Import transactions
   POST /transactions
   Body: { broker_id, transactions[] }
   → Le transazioni vengono salvate
```

**Problemi del flusso attuale:**

- Upload senza controllo permessi broker
- File "orfano" finché non viene parsato
- Nessun modo di sapere a quale broker appartiene un file
- Nella pagina Files non si può filtrare per broker

### Flusso PROPOSTO (Broker-First)

```
1. Upload file CON broker_id
   POST /brokers/import/upload
   Body: { file, broker_id }  ← NUOVO parametro obbligatorio
   → Verifica permessi: EDITOR+ sul broker
   → Salva uploaded_by_user_id e target_broker_id
   
2. Parse file
   POST /brokers/import/files/{id}/parse
   Body: { plugin_code }
   → broker_id già noto dal file metadata
   → Verifica permessi: EDITOR+ sul broker
   → Ritorna lista transazioni preview
   
3. Frontend fa mapping/review (invariato)
   → Utente conferma le transazioni
   
4. Import transactions (invariato)
   POST /transactions
   Body: { broker_id, transactions[] }
```

### Modifiche API Necessarie

| Endpoint                                  | Modifica                                          |
|-------------------------------------------|---------------------------------------------------|
| `POST /brokers/import/upload`             | + `broker_id` obbligatorio nel body o query param |
| `GET /brokers/import/files`               | + filtro `broker_ids[]` (multi-select)            |
| `DELETE /brokers/import/files/{id}`       | + check permessi su target_broker_id              |
| `GET /brokers/import/files/{id}/download` | + check permessi (VIEWER+ ok)                     |
| Schema `BRIMFileInfo`                     | + `uploaded_by_user_id`, `target_broker_id`       |

### Endpoint NON necessari (già esistenti)

- `POST /transactions` - già gestisce broker_id
- `GET /brokers/{id}/access` - già implementato
- Permessi OWNER/EDITOR/VIEWER - già implementati

---

## Nuova Architettura Proposta

### Principio Chiave: **Broker-First**

> Un file BRIM deve essere associato a un broker **al momento dell'upload**, non dopo.

**Motivo**:

- L'utente deve avere almeno EDITOR sul broker per caricare file
- Il file è logicamente parte del broker
- Semplifica filtri e permessi

### Flusso Upload Proposto

```
1. Utente è nella pagina del broker
   → Upload: broker_id è implicito
   
2. Utente è nella pagina Transactions
   → Deve selezionare broker prima di upload
   → Modale: "Seleziona broker di destinazione" → poi Upload
   
3. Utente è nella pagina Files
   → Vede solo files dei broker a cui ha accesso
   → Per upload: stesso flusso di Transactions
```

### Schema BRIMFileInfo Aggiornato

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

    # NUOVI CAMPI (solo ID, no nomi):
    uploaded_by_user_id: int  # Chi ha caricato
    target_broker_id: int  # Broker destinazione (OBBLIGATORIO)
```

---

## Modifiche API

### 1. Upload (`POST /brokers/{broker_id}/import/upload`)

**Cambiamento**: Endpoint ora sotto il broker, non globale.

```python
@brim_router.post("/{broker_id}/upload")
async def upload_file(
        broker_id: int,
        file: UploadFile,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
        ) -> BRIMFileInfo:
    # 1. Verifica accesso al broker (EDITOR o superiore)
    role = await broker_service.get_user_role(broker_id, current_user.id)
    if role is None and not current_user.is_superuser:
        raise HTTPException(404, "Broker not found or access denied")
    if role == UserRole.VIEWER:
        raise HTTPException(403, "VIEWER cannot upload files")

    # 2. Salva file con broker_id e user_id
    file_info = brim_provider.save_uploaded_file(
        content,
        filename,
        user_id=current_user.id,
        broker_id=broker_id,
        )
    return file_info
```

### 2. List Files (`GET /brokers/import/files`)

**Filtro per broker** con multi-select:

```python
@brim_router.get("/files")
async def list_files(
        broker_ids: Optional[List[int]] = Query(None),  # Multi-select
        status: Optional[BRIMFileStatus] = None,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
        ) -> List[BRIMFileInfo]:
    # 1. Ottieni broker accessibili dall'utente
    if current_user.is_superuser:
        accessible_broker_ids = None  # Tutti
    else:
        accessible_broker_ids = await broker_service.get_accessible_broker_ids(current_user.id)

    # 2. Applica filtro broker_ids (interseca con accessibili)
    if broker_ids:
        if accessible_broker_ids is not None:
            broker_ids = [b for b in broker_ids if b in accessible_broker_ids]
    else:
        broker_ids = accessible_broker_ids  # Tutti quelli accessibili

    # 3. Filtra files
    return brim_provider.list_files(
        status=status,
        broker_ids=broker_ids,
        )
```

### 3. Delete (`DELETE /brokers/import/files/{id}`)

```python
@brim_router.delete("/files/{file_id}")
async def delete_file(
        file_id: str,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
        ) -> dict:
    file_info = brim_provider.get_file_info(file_id)
    if not file_info:
        raise HTTPException(404, "File not found")

    # Verifica permessi: EDITOR+ sul broker o Superuser
    role = await broker_service.get_user_role(file_info.target_broker_id, current_user.id)

    can_delete = (
            current_user.is_superuser or
            role in [UserRole.OWNER, UserRole.EDITOR]
    )

    if not can_delete:
        raise HTTPException(403, "No permission to delete this file")

    brim_provider.delete_file(file_id)
    return {"success": True}
```

### 4. Download (`GET /brokers/import/files/{id}/download`)

```python
# VIEWER può scaricare (read-only)
role = await broker_service.get_user_role(file_info.target_broker_id, current_user.id)
if role is None and not current_user.is_superuser:
    raise HTTPException(403, "No access to this file")
```

---

## Parse Result Caching

### Problema

Attualmente, ogni volta che si vuole vedere il risultato di un parsing, bisogna ri-parsare il file. Questo è inefficiente e lento.

### Soluzione

Salvare il risultato del parsing nel metadata JSON del file.

### Schema Esteso

```python
class BRIMFileInfo(BaseModel):
    # ... campi esistenti ...
    
    # Nuovo campo per cache parse
    last_parse_result: Optional[BRIMParseResultCache] = None

class BRIMParseResultCache(BaseModel):
    plugin_code: str
    parsed_at: datetime
    transactions: List[BRIMParsedTransaction]
    assets: List[BRIMAssetCandidate]
    summary: BRIMParseSummary
```

### Metadata JSON Esempio

```json
{
    "file_id": "abc-123",
    "filename": "export.csv",
    "status": "parsed",
    "uploaded_by_user_id": 1,
    "target_broker_id": 2,
    "last_parse_result": {
        "plugin_code": "broker_directa",
        "parsed_at": "2026-01-22T10:00:00Z",
        "transactions": [
            {"date": "2026-01-15", "type": "BUY", ...},
            ...
        ],
        "assets": [...],
        "summary": {
            "total_transactions": 15,
            "buy_count": 10,
            "sell_count": 5,
            ...
        }
    }
}
```

### Nuovo Endpoint: Load Last Parse

```python
@brim_router.get("/files/{file_id}/last-parse")
async def get_last_parse_result(
        file_id: str,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
        ) -> Optional[BRIMParseResultCache]:
    """
    Ritorna il risultato dell'ultimo parsing, se disponibile.
    Utile per ricaricare una preview senza ri-parsare il file.
    
    Returns:
        - Parse result se disponibile
        - None se file mai parsato o in status UPLOADED
        - 404 se file non trovato
        - 403 se utente non ha accesso al broker
    """
    file_info = brim_provider.get_file_info(file_id)
    if not file_info:
        raise HTTPException(404, "File not found")

    # Verifica permessi (VIEWER+ ok)
    role = await broker_service.get_user_role(
        file_info.target_broker_id, current_user.id, session
        )
    if not current_user.is_superuser and role is None:
        raise HTTPException(403, "Access denied")

    return file_info.last_parse_result
```

### Comportamento Parse Endpoint

Modifica a `POST /files/{file_id}/parse`:

```python
@brim_router.post("/files/{file_id}/parse")
async def parse_file(...) -> BRIMParseResponse:
    # ... parsing logic ...
    
    # Dopo successo, salva risultato nel metadata
    if parse_success:
        brim_provider.update_file_metadata(
            file_id,
            last_parse_result={
                "plugin_code": plugin_code,
                "parsed_at": utcnow().isoformat(),
                "transactions": parsed_transactions,
                "assets": asset_candidates,
                "summary": summary,
            }
        )
    
    return response
```

### Vantaggi

1. **Performance**: Non serve ri-parsare per vedere risultato precedente
2. **UX**: L'utente può tornare sulla pagina e vedere subito i dati
3. **Debug**: Facile ispezionare cosa è stato estratto
4. **Audit**: Traccia di cosa è stato parsato e quando

---

## Modifiche Frontend

### Pagina Files (`/files`)

1. **Filtro multi-broker** (dropdown con checkbox):
    - Mostra solo broker a cui l'utente ha accesso
    - Default: tutti i broker accessibili selezionati
    - Superuser vede tutti i broker

2. **Colonna "Broker"**:
    - Mostra nome broker
    - Link cliccabile alla pagina del broker

3. **Azioni condizionali**:
    - Download: sempre visibile (VIEWER+)
    - Delete: solo se EDITOR+ sul broker

### Pagina Broker (`/brokers/{id}`)

1. **Tab/sezione "Files importati"**:
    - FilesTableAdvanced con `broker_id` fisso
    - Upload button (se EDITOR+)

2. **Upload diretto**:
    - Non serve selettore broker (è implicito)

### Pagina Transactions (`/transactions`)

1. **Import Transactions button**:
    - Step 1: Seleziona broker (dropdown)
    - Step 2: Upload file
    - Step 3: Parse e review

### Pagina Brokers (`/brokers`)

1. **Stesso filtro utente** (solo per superuser):
    - Dropdown "Mostra broker di: [Tutti gli utenti | User1 | User2...]"
    - Utenti normali vedono solo i propri broker

---

## Permessi Riepilogo

| Azione     | VIEWER                      | EDITOR | OWNER | Superuser |
|------------|-----------------------------|--------|-------|-----------|
| List files | ✅ (solo broker accessibili) | ✅      | ✅     | ✅ (tutti) |
| Download   | ✅                           | ✅      | ✅     | ✅         |
| Upload     | ❌                           | ✅      | ✅     | ✅         |
| Delete     | ❌                           | ✅      | ✅     | ✅         |
| Parse      | ❌                           | ✅      | ✅     | ✅         |

---

## Piano di Implementazione

### Fase A: Backend (Priorità ALTA - 1 giorno)

1. [ ] Estendere `BRIMFileInfo` schema
2. [ ] Modificare `save_uploaded_file()` per accettare `user_id` e `broker_id`
3. [ ] Aggiungere `broker_id` come campo obbligatorio in upload
4. [ ] Modificare `list_files()` per filtro `broker_ids[]`
5. [ ] Aggiungere check permessi su delete/download
6. [ ] Migration: pulire files esistenti (alpha reset)

### Fase B: Frontend - Files Page (2-3 ore)

1. [ ] Dropdown multi-broker nel filtro
2. [ ] Colonna "Broker" con link
3. [ ] Azioni condizionali per permessi

### Fase C: Frontend - Broker Page (1-2 ore)

1. [ ] Tab/sezione files nel dettaglio broker
2. [ ] Upload diretto con broker_id implicito

### Fase D: Frontend - Transactions (1-2 ore)

1. [ ] Flusso import con selezione broker preliminare

---

## Timeline Consigliata

**Backend**: Implementare subito (non dipende da UI)

- Stabilizza le API
- Permette test manuali
- Blocca poco del frontend

**Frontend Files Page**: Dopo completamento tabelle (già in corso)

- Aggiungere filtro broker è un'estensione naturale

**Frontend Broker Page / Transactions**: In parallelo o dopo

- Dipende da priorità feature

---

## Note Migrazione

### Alpha Reset

Essendo in fase alpha:

1. Cancellare tutti i file in `broker_reports/`
2. Aggiornare schema JSON con nuovi campi
3. I nuovi upload avranno `uploaded_by_user_id` e `target_broker_id`

### Retrocompatibilità

Per file esistenti senza i nuovi campi:

- `uploaded_by_user_id`: se null, assegnare all'admin (user_id=1)
- `target_broker_id`: se null, file non associato → nascondere o richiedere assegnazione

---

## Domande Aperte

1. ✅ **Broker obbligatorio all'upload**: Confermato
2. ✅ **Permessi basati su ruolo broker**: VIEWER=read, EDITOR+=write
3. ✅ **Filtro multi-broker**: Checkbox multiple nel dropdown
4. ⏳ **UI filtro broker in /files**: Stile da definire (pills? dropdown con check?)

---

## Struttura Storage File System

### Stato Attuale

Il backend usa una struttura basata su **status** del file:

```
broker_reports/
├── uploaded/           # File appena caricati
│   ├── {uuid}.csv      # File dati
│   └── {uuid}.json     # Metadata
├── parsed/             # File parsati con successo  
│   ├── {uuid}.csv
│   └── {uuid}.json
└── failed/             # File con errore di parsing
    ├── {uuid}.csv
    └── {uuid}.json
```

**Flusso attuale:**

1. `POST /upload` → file va in `uploaded/`
2. `POST /parse` → se successo, file va in `parsed/`, altrimenti in `failed/`
3. Lo spostamento avviene in `_move_file()` in `brim_provider.py`

### Proposta: Struttura per Broker

Con l'introduzione di `target_broker_id`, possiamo organizzare per broker:

**Opzione A: Broker come primo livello**

```
broker_reports/
├── broker_{id}/
│   ├── uploaded/
│   ├── parsed/
│   └── failed/
└── broker_{id2}/
    └── ...
```

**Opzione B: Status primo, broker secondo** (preferita)

```
broker_reports/
├── uploaded/
│   ├── broker_{id}/
│   │   ├── {uuid}.csv
│   │   └── {uuid}.json
│   └── broker_{id2}/
├── parsed/
│   └── broker_{id}/
└── failed/
    └── broker_{id}/
```

### Raccomandazione

**Opzione B** è preferibile perché:

1. Mantiene compatibilità con struttura attuale (cartelle status esistono già)
2. Permette operazioni bulk per status (es. "pulisci tutti i failed")
3. Il `target_broker_id` è già nel metadata JSON, la cartella è ridondante ma utile per:
    - Pulizia veloce quando un broker viene eliminato
    - Query filesystem senza leggere ogni JSON

### Modifiche Backend Necessarie

1. `save_uploaded_file()`: Creare sottocartella `broker_{id}/` in `uploaded/`
2. `_move_file()`: Mantenere struttura broker durante lo spostamento
3. `list_files()`: Supportare filtro `broker_ids[]` (già nel piano)
4. `delete_broker()`: Opzionalmente pulire i file associati

### Considerazioni su Cancellazione Broker

Quando un broker viene eliminato:

- **Opzione 1**: Cancellare tutti i file associati (pulizia completa)
- **Opzione 2**: Mantenere i file ma marcarli come "orfani"
- **Opzione 3**: Richiedere che non ci siano file prima di eliminare

**Raccomandazione**: Opzione 1 per semplicità in fase alpha. Mostrare warning all'utente.

