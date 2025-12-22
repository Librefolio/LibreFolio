# Implementation Plan: Unified Transaction & Plugin System

Questo documento rappresenta il piano esecutivo finale per la rifondazione del sistema di transazioni, la gestione dei broker e il sistema di importazione plugin.

---

## Phase 1: Database Refactoring (Models)

**Razionale:** Semplificare la struttura dati rimuovendo ridondanze (tabelle cash separate) e centralizzando tutto in un'unica tabella `transactions` per garantire atomicità e facilità di query.

### 1.1 Cleanup

- Cancellare direttamente `app.db` e `test.db`, non serve portarseli dietro.
- Modificare `001_initial.py` eliminando le Tabelle: `cash_movements`, `cash_accounts`.
- **Remove Code:** Rimuovere i relativi file `models.py`, `schemas`, `crud` associati a queste tabelle.

### 1.2 New/Updated Models (`backend/app/db/models.py`)

#### `User` & `UserSettings` (New)
**Razionale:** Introdurre la multi-utenza e le preferenze fin da subito per evitare refactoring pesanti in futuro.
- **User:** `id`, `username`, `email`, `hashed_password`, `is_active`, `created_at`.
- **UserSettings:** `user_id` (FK), `base_currency`, `language`, `theme`.
- **BrokerUserAccess:** `user_id`, `broker_id`, `role` (OWNER/VIEWER).

#### `Broker` (Update)
**Razionale:** Rendere il broker un contenitore flessibile. Rimuoviamo la lista esplicita delle valute supportate: le valute esistono se esistono transazioni in quella valuta.
- **Remove:** Relazione con `cash_accounts`.
- **Add:**
    - `allow_cash_overdraft`: Bool (Default `False`): permetterà, quando a true con uno sviluppo dietro, di gestire operazioni con prestiti (quindi in debito) abilitando la
      possibilità di avere il bilancio cash negativo.
    - `allow_asset_shorting`: Bool (Default `False`): permetterà, quando a true con uno sviluppo dietro, di gestire operazione di short (vendere prima di avere l'asset) e abiliterà
      quindi la possibilità di avere asset negativi. Probabilmente dovrà essere creata una flag anche nella tabella asset per contro confermare che quell'asset è shortabile.

#### `Transaction` (New Unified Table)
**Razionale:** Unica fonte di verità. Gestisce sia asset che cash, supporta collegamenti per trasferimenti e tag per raggruppamenti utente.
```python
class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    broker_id: int = Field(foreign_key="brokers.id", nullable=False)
    asset_id: Optional[int] = Field(foreign_key="assets.id", nullable=True)
    
    type: TransactionType = Field(nullable=False) # Enum
    date: date = Field(nullable=False) # Settlement Date
    
    # Signs: + In, - Out. Default 0, Not Null per semplificare calcoli (SUM).
    quantity: Decimal = Field(default=0, nullable=False) 
    amount: Decimal = Field(default=0, nullable=False)
    currency: Optional[str] = Field(default=None) # Required if amount != 0
    
    # Unidirectional Link: The second transaction points to the first.
    # Used for TRANSFER and FX_CONVERSION.
    related_transaction_id: Optional[int] = Field(foreign_key="transactions.id", nullable=True)
    
    tags: Optional[str] = Field(default=None) # Comma-separated tags (es: "tag1,tag2")
    description: Optional[str] = Field(default=None)
    
    created_at: datetime
    updated_at: datetime
```

La tabella dovrebbe essere:

| Colonna                  | Tipo     | Nullable | Default | Descrizione                                                         |
|:-------------------------|:---------|:---------|:--------|:--------------------------------------------------------------------|
| `id`                     | PK       | No       | -       | ID Univoco.                                                         |
| `broker_id`              | FK       | No       | -       | Broker di appartenenza.                                             |
| `asset_id`               | FK       | Sì       | -       | Asset coinvolto. NULL per movimenti puramente cash.                 |
| `type`                   | Enum     | No       | -       | Tipo di operazione.                                                 |
| `date`                   | Date     | No       | -       | Data di regolamento (Settlement Date).                              |
| `quantity`               | Decimal  | No       | `0`     | Delta Asset. Positivo = Entrata. Negativo = Uscita.                 |
| `amount`                 | Decimal  | No       | `0`     | Delta Cash. Positivo = Incasso. Negativo = Spesa.                   |
| `currency`               | String   | Sì       | -       | Codice valuta (ISO 4217) se `amount != 0`.                          |
| `related_transaction_id` | FK       | Sì       | -       | Punta alla transazione "gemella". Indice DB necessario.             |
| `tags`                   | Text     | Sì       | -       | Lista di tag separati da virgola o JSON. Per raggruppamenti utente. |
| `description`            | Text     | Sì       | -       | Note o descrizione originale.                                       |
| `created_at`             | DateTime | No       | Now     | Timestamp creazione.                                                |
| `updated_at`             | DateTime | No       | Now     | Timestamp aggiornamento.                                            |


### 1.3 Transaction Types Reference Table

**Razionale:** Definizione chiara della semantica di ogni operazione per guidare lo sviluppo della business logic e dei validatori.

| Enum            | Scopo                             | Segni Tipici      | Related ID       |
|:----------------|:----------------------------------|:------------------|:-----------------|
| `BUY`           | Acquisto asset con cash.          | Qty > 0, Amt < 0  | NULL             |
| `SELL`          | Vendita asset per cash.           | Qty < 0, Amt > 0  | NULL             |
| `DIVIDEND`      | Incasso dividendi.                | Qty = 0, Amt > 0  | NULL             |
| `INTEREST`      | Incasso interessi.                | Qty = 0, Amt > 0  | NULL             |
| `DEPOSIT`       | Versamento liquidità.             | Qty = 0, Amt > 0  | NULL             |
| `WITHDRAWAL`    | Prelievo liquidità.               | Qty = 0, Amt < 0  | NULL             |
| `FEE`           | Commissioni.                      | Qty = 0, Amt < 0  | NULL             |
| `TAX`           | Tasse.                            | Qty = 0, Amt < 0  | NULL             |
| `TRANSFER`      | Spostamento asset tra broker.     | Qty +/- , Amt = 0 | **OBBLIGATORIO** |
| `FX_CONVERSION` | Cambio valuta.                    | Qty = 0, Amt +/-  | **OBBLIGATORIO** |
| `ADJUSTMENT`    | Rettifiche Asset (Split, Omaggi). | Qty +/- , Amt = 0 | Opzionale        |

Nota: `ADJUSTMENT` esiste per operazioni manuali di correzione che non riguardano la transazione inserita male,
ma degli eventi speciali che effettivamente il broker fa sui tuoi asset/conti e che vanno fuori dalle regole classiche.

---

## Phase 2: Pydantic Schemas (DTOs)

**Razionale:** Definire contratti rigidi per l'input/output delle API e dei Plugin, separando la logica di validazione dal modello DB.

### 2.1 Transaction Schemas (Demo Implementation)

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from decimal import Decimal
from typing import Optional, List
from datetime import date
from backend.app.schemas.common import Currency

class TransactionCreate(BaseModel):
    broker_id: int
    asset_id: Optional[int] = None
    type: str  # Enum TransactionType
    date: date
    
    quantity: Decimal = Field(default=Decimal(0))
    
    # Uso di Currency da common.py per gestire amount + currency
    # Nota: Currency richiede 'code' e 'amount'.
    # Se amount è 0, questo campo può essere opzionale o gestito come Currency.zero("EUR")
    # ma per flessibilità API, lo teniamo opzionale e validiamo.
    cash_amount: Optional[Currency] = None 
    
    description: Optional[str] = None
    
    # Tags: Lista di stringhe in input, convertita in stringa CSV nel DB
    tags: Optional[List[str]] = None
    
    # Campo speciale per linking durante creazione bulk
    link_uuid: Optional[str] = None 

    @model_validator(mode='after')
    def validate_cash(self):
        # Se non c'è cash_amount, assumiamo 0.
        # Se c'è, Currency valida già che code sia valido.
        return self

class TransactionRead(TransactionCreate):
    id: int
    related_transaction_id: Optional[int] = None
    created_at: date
    # Override tags per tornare List[str] partendo dalla stringa CSV del DB
    tags: Optional[List[str]] = None

class TransactionUpdate(BaseModel):
    id: int
    date: Optional[date] = None
    quantity: Optional[Decimal] = None
    cash_amount: Optional[Currency] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
```

### 2.2 Broker Schemas (Demo Implementation)

```python
class BrokerCreate(BaseModel):
    name: str
    description: Optional[str] = None
    allow_cash_overdraft: bool = False
    allow_asset_shorting: bool = False
    
    # Dizionario opzionale per creare depositi iniziali automatici
    # Es: {"EUR": 1000.00, "USD": 500.00}
    initial_balances: Optional[dict[str, Decimal]] = None

    @field_validator('initial_balances')
    @classmethod
    def validate_currencies(cls, v):
        if v:
            for code in v.keys():
                Currency.validate_code(code) # Usa validatore statico di common.py
        return v

# BrokerRead rimosso come richiesto, si usa direttamente il modello SQLModel o un DTO semplice
```

### 2.3 Plugin Schemas (Demo Implementation)

```python
from backend.app.schemas.common import BaseBulkResponse

class ImportResult(BaseBulkResponse): # Estende BaseBulkResponse
    file_id: str
    status: str # "SUCCESS", "PARTIAL", "FAILED"
    # results, success_count, errors ereditati da BaseBulkResponse
```

---

## Phase 3: Service Layer (Business Logic)

**Razionale:** Centralizzare la logica complessa (validazione saldi, linking transazioni) per renderla riutilizzabile da API, Import e CLI.

### 3.1 `BrokerService`
- **Create:**
  - Crea record `Broker`.
  - Gestisce `initial_balances`: per ogni valuta > 0, chiama `TransactionService.create_transaction_bulk` con una transazione `DEPOSIT`.
- **Update (`update_broker`):**
  - Aggiorna campi semplici (nome, descrizione).
  - Se vengono modificati i flag `allow_cash_overdraft` o `allow_asset_shorting` da `True` a `False`:
    - Chiama `TransactionService.validate_balances` per assicurarsi che lo stato attuale non violi i nuovi vincoli.
    - Se violazione, rollback e errore.
- **Delete (`delete_broker`):**
  - Verifica se ci sono transazioni associate al broker.
  - Se ci sono transazioni (anche solo depositi iniziali), blocca l'eliminazione (o richiede force delete che svuota tutto).
  - Elimina il broker.
- **Logic:** Non gestisce più liste di valute supportate. Le valute sono implicite nelle transazioni.

### 3.2 `TransactionService`
- **`create_transaction_bulk(transactions: List[TransactionCreate])`:**
  1. **DB Transaction Start.**
  2. **Insert:** Inserisce le righe. Converte `tags: List[str]` in stringa CSV.
  3. **Link Resolution:** Raggruppa per `link_uuid`.
     - Se trova coppia (A, B), aggiorna B.related_transaction_id = A.id.
  4. **Validation:** Chiama `validate_balances` per i broker coinvolti.
  5. **Commit.**
- **`update_transaction_bulk(updates: List[TransactionUpdate])`:**
  1. **DB Transaction Start.**
  2. **Update:** Applica le modifiche.
     - Nota: Non aggiorna automaticamente le transazioni collegate (related). Il frontend deve inviare update per entrambe.
  3. **Validation:** Se cambiano `amount`, `quantity` o `date`, chiama `validate_balances`.
  4. **Commit.**
- **`delete_transaction_bulk(ids: List[int])`:**
  - Verifica integrità coppie (se cancello A, devo cancellare B).
  - Esegue delete.
  - Valida saldi post-cancellazione.
- **`validate_balances(broker_id, from_date)`:**
  - **Algoritmo:**
    1. Recupera il saldo iniziale al giorno `from_date - 1` (somma di tutte le transazioni precedenti).
    2. Recupera tutte le transazioni dal giorno `from_date` in poi, ordinate per data.
    3. Itera giorno per giorno:
       - Somma tutte le transazioni del giorno `T` al saldo corrente.
       - Verifica: `Saldo_T >= 0` (se flag overdraft/shorting sono False).
       - Se negativo in qualsiasi giorno, solleva eccezione e rollback.
  - Questo garantisce che non si vada mai in rosso a fine giornata, indipendentemente dall'ordine intra-day.

### 3.3 `PluginSystem` (Abstract & Registry)
**Razionale:** Disaccoppiare il core dai formati specifici dei file. Il core non deve sapere cos'è un CSV Directa.
- **Base Class `TransactionImportPlugin`:**
  - `code`: str
  - `is_supported(file_path) -> bool`: Ritorna True se il plugin supporta il file (check estensione/contenuto).
  - `parse(file_path) -> List[TransactionCreate]`: Ritorna DTOs puri.
- **Core Functions:**
  - `process_file(file_id, plugin_code)`:
    1. Recupera file path.
    2. Istanzia plugin.
    3. `dtos = plugin.parse(path)`.
    4. Chiama `TransactionService.create_transaction_bulk(dtos)`.
    5. Gestisce errori e sposta file.

---

## Phase 4: API Layer

**Razionale:** Esporre endpoint RESTful coerenti. Separare nettamente la gestione file (upload/delete) dal processing (import effettivo).

### 4.1 Broker Endpoints (`/api/v1/brokers`)
- `POST /`: Crea broker + depositi iniziali.
- `GET /`: Lista broker.
- `PATCH /{id}`: Chiama `BrokerService.update_broker`.
- `DELETE /{id}`: Chiama `BrokerService.delete_broker`.

### 4.2 Transaction Endpoints (`/api/v1/transactions`)
- `POST /`: Chiama `create_transaction_bulk`.
- `GET /`: Filtri (`broker_id`, `asset_id`, `date_range`, `tags`).
- `DELETE /`: Chiama `delete_transaction_bulk`.
- `PATCH /`: Chiama `update_transaction_bulk`.
- `GET /types`: Ritorna metadata enum (icone, descrizioni).

### 4.3 Import Endpoints (`/api/v1/import`)
- `POST /upload`: Upload file in `backend/data/brokerReports/uploaded/`.
  - **Response:** `{ "file_id": "...", "supported_plugins": ["directa_csv", "generic_csv"] }`
  - Il backend itera sui plugin registrati chiamando `is_supported(path)` per popolare la lista.
- `GET /files`: Lista file.
    - Query param: `status` (`uploaded` | `imported` | `all` | `failed`).
    - Ritorna lista con metadata e lista di `supported_plugins`.
- `DELETE /files/{file_id}`: Elimina fisicamente il file (se non processato o per pulizia), inserire una data clean rigida, essendo un operazione potenzialmente hackerabbile, l'id deve essere un numero e la richeista deve essere una lista di numeri int.
- `POST /process/{file_id}`:
    - Params: `plugin_code`, `tags`, ....
    - Esegue parsing e inserimento tramite `PluginSystem.process_file`.
    - Sposta file in `imported/` se un successo, in `failed/` se errore.

### 4.4 Export/Backup Endpoints (`/api/v1/export`)

**Razionale:** Placeholder per funzionalità future. Attualmente ritornano 501 Not Implemented o un messaggio JSON fisso.

- `GET /transactions`: "To Be Developed".
- `POST /restore`: "To Be Developed".

---

## Phase 5: Implementation Steps (Execution Order)

**Razionale:** Ordine logico per minimizzare i blocchi. Prima il DB, poi la logica core, infine le API e i plugin.

1.  **DB Migration:** Eliminare vecchie tabelle, creare `Transaction`, aggiornare `Broker`.
2.  **Broker Logic:** Implementare Service e API per Broker (inclusa logica initial deposit).
3.  **Transaction Core:** Implementare `TransactionService` (CRUD, Validation, Linking).
4.  **Transaction API:** Implementare Endpoints.
5.  **Plugin Infrastructure:** Creare classe base, registry e file management.
6.  **Generic CSV Plugin:** Implementare il primo plugin "Generic CSV".
7.  **Import API:** Collegare il tutto.
