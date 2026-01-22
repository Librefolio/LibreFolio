# Piano Implementazione BRIM Multi-User

**Data**: 22 Gennaio 2026  
**Status**: 📋 PIANIFICATO  
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

## Fase 1: Backend - Schema e Storage (2-3 ore)

### 1.1 Estendere BRIMFileInfo Schema

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
    
    # NUOVI CAMPI
    uploaded_by_user_id: int
    target_broker_id: int
    last_parse_result: Optional[dict] = None  # Cached parse result
```

### 1.2 Modificare Storage Structure

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

**Modifiche**:
- [ ] `_ensure_dirs()`: Creare sottocartelle broker on-demand
- [ ] `save_uploaded_file()`: Accettare `user_id` e `broker_id`, salvare in sottocartella
- [ ] `_move_file()`: Mantenere struttura broker durante spostamento
- [ ] `list_files()`: Supportare filtro `broker_ids: List[int]`
- [ ] `get_file_info()`: Cercare in tutte le sottocartelle broker

### 1.3 Caching Parse Result

**Nuovo campo nel metadata JSON**:
```json
{
    "file_id": "...",
    "filename": "...",
    "status": "parsed",
    "uploaded_by_user_id": 1,
    "target_broker_id": 2,
    "last_parse_result": {
        "plugin_code": "broker_directa",
        "parsed_at": "2026-01-22T10:00:00Z",
        "transactions": [...],
        "assets": [...],
        "summary": {...}
    }
}
```

**Comportamento**:
- Dopo parse success → salva risultato in `last_parse_result`
- Re-parse → sovrascrive `last_parse_result`
- Nuovo endpoint per caricare cached result

---

## Fase 2: Backend - Endpoint Modifications (2-3 ore)

### 2.1 Modificare Upload Endpoint

**Endpoint**: `POST /api/v1/brokers/import/upload`

**Modifiche**:
- [ ] Aggiungere parametro `broker_id` (obbligatorio)
- [ ] Verificare permessi utente sul broker (EDITOR+)
- [ ] Salvare `uploaded_by_user_id` e `target_broker_id`

```python
@brim_router.post("/upload")
async def upload_file(
    file: UploadFile,
    broker_id: int = Query(..., description="Target broker ID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BRIMFileInfo:
    # 1. Verifica accesso broker (EDITOR+)
    role = await broker_service.get_user_role(broker_id, current_user.id, session)
    if not current_user.is_superuser and role not in [UserRole.OWNER, UserRole.EDITOR]:
        raise HTTPException(403, "EDITOR access required to upload files")
    
    # 2. Salva file con metadata estesi
    file_info = brim_provider.save_uploaded_file(
        content=await file.read(),
        filename=file.filename,
        user_id=current_user.id,
        broker_id=broker_id,
    )
    return file_info
```

### 2.2 Modificare List Files Endpoint

**Endpoint**: `GET /api/v1/brokers/import/files`

**Modifiche**:
- [ ] Aggiungere parametro `broker_ids: List[int]` (opzionale)
- [ ] Filtrare per broker accessibili all'utente
- [ ] Superuser vede tutto

```python
@brim_router.get("/files")
async def list_files(
    broker_ids: Optional[List[int]] = Query(None),
    status: Optional[BRIMFileStatus] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[BRIMFileInfo]:
    # 1. Ottieni broker accessibili
    if current_user.is_superuser:
        accessible = None  # Tutti
    else:
        accessible = await broker_service.get_accessible_broker_ids(
            current_user.id, session
        )
    
    # 2. Interseca con filtro richiesto
    if broker_ids and accessible is not None:
        broker_ids = [b for b in broker_ids if b in accessible]
    elif accessible is not None:
        broker_ids = accessible
    
    # 3. Lista file
    return brim_provider.list_files(status=status, broker_ids=broker_ids)
```

### 2.3 Modificare Delete/Download Endpoints

**Modifiche**:
- [ ] Verificare permessi su `target_broker_id` del file
- [ ] VIEWER può download, EDITOR+ può delete

### 2.4 Nuovo Endpoint: Load Cached Parse

**Endpoint**: `GET /api/v1/brokers/import/files/{file_id}/last-parse`

```python
@brim_router.get("/files/{file_id}/last-parse")
async def get_last_parse_result(
    file_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Optional[dict]:
    """
    Ritorna il risultato dell'ultimo parsing, se disponibile.
    Utile per ricaricare una preview senza ri-parsare.
    """
    file_info = brim_provider.get_file_info(file_id)
    if not file_info:
        raise HTTPException(404, "File not found")
    
    # Verifica permessi
    role = await broker_service.get_user_role(
        file_info.target_broker_id, current_user.id, session
    )
    if not current_user.is_superuser and role is None:
        raise HTTPException(403, "Access denied")
    
    return file_info.last_parse_result
```

### 2.5 Modificare Parse Endpoint

**Endpoint**: `POST /api/v1/brokers/import/files/{file_id}/parse`

**Modifiche**:
- [ ] Dopo parse success, salvare risultato in `last_parse_result`
- [ ] Rimuovere `broker_id` dal body (già nel file metadata)

---

## Fase 3: Backend - Migration & Tests (1-2 ore)

### 3.1 Migration Script

**Approccio Alpha Reset** (raccomandato):
```bash
# Pulisci tutti i file esistenti
rm -rf backend/data/broker_reports/*

# Ricrea struttura base
mkdir -p backend/data/broker_reports/{uploaded,parsed,failed}
```

### 3.2 Tests

- [ ] Test upload con broker_id
- [ ] Test list files con filtro broker_ids
- [ ] Test permessi (VIEWER vs EDITOR)
- [ ] Test parse con caching result
- [ ] Test load-last-parse endpoint

---

## Fase 4: Frontend - Files Page (2-3 ore)

### 4.1 Filtro Multi-Broker

- [ ] Dropdown con checkbox per selezionare broker
- [ ] Mostra solo broker accessibili
- [ ] Superuser vede tutti i broker
- [ ] Salvataggio preferenza in localStorage

### 4.2 Colonna Broker

- [ ] Nuova colonna "Broker" nella tabella
- [ ] Link cliccabile alla pagina del broker
- [ ] Nascondi se filtrato per singolo broker

### 4.3 Upload con Broker Selection

- [ ] Se non in pagina broker, mostrare selector prima di upload
- [ ] Disabilitare upload se nessun broker con permessi EDITOR+

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
