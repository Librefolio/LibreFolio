# Implementation Plan: Unified Transaction & Plugin System

Questo documento rappresenta il piano esecutivo finale per la rifondazione del sistema di transazioni, la gestione dei broker e il sistema di importazione plugin.

---

## Phase 1: Database Refactoring (Models)

**Razionale:** Semplificare la struttura dati rimuovendo ridondanze (tabelle cash separate) e centralizzando tutto in un'unica tabella `transactions` per garantire atomicità e
facilità di query.

**Status:** ✅ **COMPLETATA** (2025-12-22)

### 1.1 Cleanup

- ✅ Cancellare direttamente `app.db` e `test.db`, non serve portarseli dietro.
- ✅ Modificare `001_initial.py` eliminando le Tabelle: `cash_movements`, `cash_accounts`.
- ✅ **Remove Code:** Rimuovere i relativi file `models.py`, `schemas`, `crud` associati a queste tabelle.

**Note implementative:**

- Rimossi `CashMovement`, `CashAccount`, `CashMovementType` da `models.py`
- Aggiornati `base.py` e `__init__.py` per rimuovere gli export obsoleti
- Riscritti `populate_mock_data.py` e `test_db_referential_integrity.py` per la nuova struttura

### 1.2 New/Updated Models (`backend/app/db/models.py`)

#### `User` & `UserSettings` (New) ✅

**Razionale:** Introdurre la multi-utenza e le preferenze fin da subito per evitare refactoring pesanti in futuro.

- ✅ **User:** `id`, `username`, `email`, `hashed_password`, `is_active`, `created_at`.
- ✅ **UserSettings:** `user_id` (FK), `base_currency`, `language`, `theme`.
- ✅ **BrokerUserAccess:** `user_id`, `broker_id`, `role` (OWNER/VIEWER).

**Note implementative:**

- Aggiunto enum `UserRole` (OWNER/VIEWER)
- `UserSettings` ha validatore Pydantic per `base_currency` via `Currency.validate_code()`

#### `Broker` (Update) ✅

**Razionale:** Rendere il broker un contenitore flessibile. Rimuoviamo la lista esplicita delle valute supportate: le valute esistono se esistono transazioni in quella valuta.

- ✅ **Remove:** Relazione con `cash_accounts`.
- ✅ **Add:**
    - `allow_cash_overdraft`: Bool (Default `False`): permetterà, quando a true con uno sviluppo dietro, di gestire operazioni con prestiti (quindi in debito) abilitando la
      possibilità di avere il bilancio cash negativo.
    - `allow_asset_shorting`: Bool (Default `False`): permetterà, quando a true con uno sviluppo dietro, di gestire operazione di short (vendere prima di avere l'asset) e abiliterà
      quindi la possibilità di avere asset negativi. Probabilmente dovrà essere creata una flag anche nella tabella asset per contro confermare che quell'asset è shortabile.

#### `Transaction` (New Unified Table) ✅

**Razionale:** Unica fonte di verità. Gestisce sia asset che cash, supporta collegamenti per trasferimenti e tag per raggruppamenti utente.

```python
class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    broker_id: int = Field(foreign_key="brokers.id", nullable=False)
    asset_id: Optional[int] = Field(foreign_key="assets.id", nullable=True)

    type: TransactionType = Field(nullable=False)  # Enum
    date: date = Field(nullable=False)  # Settlement Date

    # Signs: + In, - Out. Default 0, Not Null per semplificare calcoli (SUM).
    quantity: Decimal = Field(default=0, nullable=False)
    amount: Decimal = Field(default=0, nullable=False)
    currency: Optional[str] = Field(default=None)  # Required if amount != 0

    # Unidirectional Link: The second transaction points to the first.
    # Used for TRANSFER and FX_CONVERSION.
    related_transaction_id: Optional[int] = Field(foreign_key="transactions.id", nullable=True)

    tags: Optional[str] = Field(default=None)  # Comma-separated tags (es: "tag1,tag2")
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

### 1.3 Transaction Types Reference Table ✅

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

### 1.4 Analisi Vincoli per Tipo Transazione

Tabella che definisce quali campi sono obbligatori/opzionali per ogni tipo di transazione e il perché.

| Tipo            | `asset_id`   | `cash` (amount+currency) | `link_uuid`  | Motivazione                                                     |
|:----------------|:-------------|:-------------------------|:-------------|:----------------------------------------------------------------|
| `BUY`           | **REQUIRED** | **REQUIRED** (< 0)       | NULL         | Compro un asset specifico pagando cash                          |
| `SELL`          | **REQUIRED** | **REQUIRED** (> 0)       | NULL         | Vendo un asset specifico ricevendo cash                         |
| `DIVIDEND`      | **REQUIRED** | **REQUIRED** (> 0)       | NULL         | Dividendo è sempre legato ad un asset posseduto                 |
| `INTEREST`      | **OPTIONAL** | **REQUIRED** (> 0)       | NULL         | Può essere legato ad asset (bond) o standalone (conto deposito) |
| `DEPOSIT`       | NULL         | **REQUIRED** (> 0)       | NULL         | Versamento cash puro, nessun asset coinvolto                    |
| `WITHDRAWAL`    | NULL         | **REQUIRED** (< 0)       | NULL         | Prelievo cash puro, nessun asset coinvolto                      |
| `FEE`           | **OPTIONAL** | **REQUIRED** (< 0)       | NULL         | Commissione può essere su asset (trading) o standalone (canone) |
| `TAX`           | **OPTIONAL** | **REQUIRED** (< 0)       | NULL         | Tassa può essere su asset (capital gain) o standalone (bollo)   |
| `TRANSFER`      | **REQUIRED** | NULL                     | **REQUIRED** | Sposto asset tra broker, no movimento cash                      |
| `FX_CONVERSION` | NULL         | **REQUIRED** (+/-)       | **REQUIRED** | Cambio valuta, nessun asset coinvolto, due tx linkate           |
| `ADJUSTMENT`    | **REQUIRED** | NULL                     | OPTIONAL     | Rettifica quantità asset (split, regalo), no cash               |

**Legenda:**

- **REQUIRED**: Campo obbligatorio
- **OPTIONAL**: Campo opzionale (può essere presente o meno)
- **NULL**: Campo deve essere vuoto/assente
- **(> 0)** / **(< 0)** / **(+/-)**: Segno atteso per l'amount

**Note:**

- `INTEREST` è OPTIONAL su asset_id perché: interessi da bond → asset_id presente; interessi da conto deposito → asset_id NULL
- `FEE` è OPTIONAL su asset_id perché: commissione trading → asset_id presente; canone annuale broker → asset_id NULL
- `TAX` è OPTIONAL su asset_id perché: capital gain tax → asset_id presente; imposta di bollo → asset_id NULL

**Note implementative aggiuntive (oltre il piano originale):**

- ✅ Aggiunta validazione currency con `@lru_cache(maxsize=256)` per performance
- ✅ Creata funzione `_validate_currency_field()` helper in models.py
- ✅ Validazione usa `Currency.validate_code()` (ISO 4217 + crypto supportati)
- ✅ Modelli con validatore currency: `UserSettings`, `Asset`, `Transaction`, `PriceHistory`, `FxRate`, `FxCurrencyPairSource`
- ✅ Test aggiornati per la nuova struttura unificata (`db_schema_validate.py`, `test_db_referential_integrity.py`)
- ✅ Script `populate_mock_data.py` riscritto per usare il modello Transaction unificato
- ⚠️ **Nota su validazione SQLModel**: I validatori `@field_validator` nei modelli `table=True` non vengono convertiti in vincoli SQL nella tabella. 
     Quindi se un altra applicazione o un altro pezzo di codice facesse una INSERT nella tabella senza passare per la classe pydantic, i validator verrebbero ignorati.

---

## Phase 2: Pydantic Schemas (DTOs)

**Status:** ✅ **COMPLETATA** (2025-12-22)

**Razionale:** Definire contratti rigidi per l'input/output delle API e dei Plugin, separando la logica di validazione dal modello DB.

### Convenzioni di Naming Adottate

| Prefisso | Dominio          | Esempio                                     |
|:---------|:-----------------|:--------------------------------------------|
| `FA`     | Financial Assets | `FAAssetCreateItem`, `FABulkCreateResponse` |
| `FX`     | Foreign Exchange | `FXConversionRequest`, `FXSyncResponse`     |
| `TX`     | Transactions     | `TXCreateItem`, `TXReadItem`                |
| `BR`     | Brokers          | `BRCreateItem`, `BRSummary`                 |

**Regole generali:**

- Suffisso `Item` per elementi singoli in liste (es. `TXCreateItem`, `BRDeleteItem`)
- Suffisso `Result` per risultato di operazione singola (es. `TXCreateResult`)
- Suffisso `Response` per risposta bulk completa (es. `TXBulkCreateResponse`)
- Prefisso `Bulk` per operazioni su liste

### 2.1 Transaction Schemas (TX) ✅

Implementati in `backend/app/schemas/transactions.py`:

**Create/Read/Update/Delete:**

- **`TXCreateItem`**: DTO per creazione con validazione business rules
- **`TXReadItem`**: DTO per lettura con `from_db_model(tx: Transaction)` factory
- **`TXUpdateItem`**: DTO per aggiornamento (solo campi modificabili)
- **`TXDeleteItem`**: DTO per delete singolo
- **`TXQueryParams`**: DTO per filtri query con `DateRangeModel`

**Bulk Responses:**

- **`TXCreateResultItem`** + **`TXBulkCreateResponse`**
- **`TXUpdateResultItem`** + **`TXBulkUpdateResponse`**
- **`TXDeleteResult`** (extends `BaseDeleteResult`) + **`TXBulkDeleteResponse`**

**Metadata:**

- **`TXTypeMetadata`**: Metadata per validazione frontend con:
    - `asset_mode: AssetMode` = `"REQUIRED"` | `"OPTIONAL"` | `"FORBIDDEN"`
    - `allowed_quantity_sign: SignType` = `"+"` | `"-"` | `"0"` | `"+/-"`
    - `allowed_cash_sign: SignType`
- **`TX_TYPE_METADATA`**: Dict con regole per tutti i tipi

**Type Aliases:**

- **`SignType`**: `Literal["+", "-", "0", "+/-"]`
- **`AssetMode`**: `Literal["REQUIRED", "OPTIONAL", "FORBIDDEN"]`

**Utilities (DRY):**

- **`validate_tags_list(v)`**: Validatore condiviso per tags
- **`tags_to_csv(tags)`**: Conversione List[str] → CSV per DB

**Note implementative:**

- ✅ Usa `Currency` da common.py per campo `cash` (amount + code insieme)
- ✅ Usa `DateRangeModel` da common.py per `date_range` in query
- ✅ Usa `BaseDeleteResult`, `BaseBulkResponse`, `BaseBulkDeleteResponse`
- ✅ `@model_validator` per validare regole business (vedi tabella 1.4)
- ✅ Tags: `List[str]` in schema, convertito in CSV per DB tramite `tags_to_csv()`
- ✅ `TXReadItem.from_db_model(tx: Transaction)` per conversione DB→DTO
- ✅ `TXTypeMetadata.asset_mode` con 3 valori: REQUIRED/OPTIONAL/FORBIDDEN
- ✅ INTEREST, FEE, TAX hanno `asset_mode="OPTIONAL"` (possono o meno essere legati ad asset)

**Perché separare TXReadItem da Transaction (SQLModel)?**

1. Il modello DB ha `amount` e `currency` separati; lo schema usa `Currency` (oggetto unico)
2. Il modello DB ha `tags` come stringa CSV; lo schema usa `List[str]`
3. Disaccoppiamento DTO/DB è best practice per evitare leak di dettagli implementativi

**Come aggiornare related_transaction_id?**

- Non è aggiornabile direttamente tramite `TXUpdateItem`
- Per modificare link: delete entrambe + re-create con nuovo `link_uuid`
- Oppure: inviare update per ENTRAMBE le transazioni nello stesso bulk request

### 2.2 Broker Schemas (BR) ✅

Implementati in `backend/app/schemas/brokers.py`:

**Create/Read/Update/Delete:**

- **`BRCreateItem`**: Con `initial_balances: List[Currency]` per auto-creazione DEPOSIT
- **`BRReadItem`**: DTO semplice con `from_attributes=True`
- **`BRUpdateItem`**: DTO per aggiornamento
- **`BRDeleteItem`**: DTO per delete con flag `force`

**Summary con Holdings:**

- **`BRAssetHolding`**: Singola posizione asset con:
    - `quantity`, `total_cost`, `average_cost_per_unit`
    - `current_price`, `current_value` (se prezzo disponibile)
    - `unrealized_pnl`, `unrealized_pnl_percent`
- **`BRSummary`**: Estende `BRReadItem` con:
    - `cash_balances: List[Currency]`
    - `holdings: List[BRAssetHolding]`
    - `total_value_base_currency: Optional[Currency]`

**Bulk Responses:**

- **`BRCreateResult`** + **`BRBulkCreateResponse`**
- **`BRUpdateResult`** + **`BRBulkUpdateResponse`**
- **`BRDeleteResult`** (extends `BaseDeleteResult` + `transactions_deleted`) + **`BRBulkDeleteResponse`**

**User Access:**

- **`BRUserAccessCreateItem`**
- **`BRUserAccessReadItem`**
- **`BRUserAccessUpdateItem`**

**Note implementative:**

- ✅ Riusa `Currency` per `initial_balances`, `cash_balances`, `total_cost`, `current_value`, `unrealized_pnl`
- ✅ Riusa classi base da common.py
- ✅ `BRReadItem` mappa direttamente da SQLModel Broker
- ✅ `BRSummary` include holdings con cost basis e market value per analisi portafoglio
- ✅ `BRDeleteItem.force`: se True, cascade delete di tutte le transazioni associate
    - `force=False` (default): delete fallisce se esistono transazioni → errore con conteggio
    - `force=True`: elimina broker E tutte le transazioni → `BRDeleteResult.transactions_deleted` mostra quante

### 2.3 Plugin Schemas

Da implementare nella Phase 5 (Plugin Infrastructure).

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
- `DELETE /files/{file_id}`: Elimina fisicamente il file (se non processato o per pulizia), inserire una data clean rigida, essendo un operazione potenzialmente hackerabbile, l'id
  deve essere un numero e la richeista deve essere una lista di numeri int.
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

1. **DB Migration:** Eliminare vecchie tabelle, creare `Transaction`, aggiornare `Broker`.
2. **Broker Logic:** Implementare Service e API per Broker (inclusa logica initial deposit).
3. **Transaction Core:** Implementare `TransactionService` (CRUD, Validation, Linking).
4. **Transaction API:** Implementare Endpoints.
5. **Plugin Infrastructure:** Creare classe base, registry e file management.
6. **Generic CSV Plugin:** Implementare il primo plugin "Generic CSV".
7. **Import API:** Collegare il tutto.
