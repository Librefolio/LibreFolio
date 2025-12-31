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

    # BIDIRECTIONAL Link with DEFERRABLE FK (2025-12-26)
    # Both transactions in a pair point to each other (A->B and B->A).
    # Uses DEFERRABLE INITIALLY DEFERRED to allow setting mutual links in same transaction.
    # FK constraint is only checked at COMMIT, not at INSERT/UPDATE time.
    related_transaction_id: Optional[int] = Field(
        foreign_key="transactions.id", 
        deferrable=True, 
        initially="DEFERRED",
        nullable=True
    )

    tags: Optional[str] = Field(default=None)  # Comma-separated tags (es: "tag1,tag2")
    description: Optional[str] = Field(default=None)

    created_at: datetime
    updated_at: datetime
```

La tabella dovrebbe essere:

| Colonna                  | Tipo     | Nullable | Default | Descrizione                                                                        |
|:-------------------------|:---------|:---------|:--------|:-----------------------------------------------------------------------------------|
| `id`                     | PK       | No       | -       | ID Univoco.                                                                        |
| `broker_id`              | FK       | No       | -       | Broker di appartenenza.                                                            |
| `asset_id`               | FK       | Sì       | -       | Asset coinvolto. NULL per movimenti puramente cash.                                |
| `type`                   | Enum     | No       | -       | Tipo di operazione.                                                                |
| `date`                   | Date     | No       | -       | Data di regolamento (Settlement Date).                                             |
| `quantity`               | Decimal  | No       | `0`     | Delta Asset. Positivo = Entrata. Negativo = Uscita.                                |
| `amount`                 | Decimal  | No       | `0`     | Delta Cash. Positivo = Incasso. Negativo = Spesa.                                  |
| `currency`               | String   | Sì       | -       | Codice valuta (ISO 4217) se `amount != 0`.                                         |
| `related_transaction_id` | FK       | Sì       | -       | **BIDIRECTIONAL**: punta alla transazione gemella. DEFERRABLE INITIALLY DEFERRED.  |
| `tags`                   | Text     | Sì       | -       | Lista di tag separati da virgola o JSON. Per raggruppamenti utente.                |
| `description`            | Text     | Sì       | -       | Note o descrizione originale.                                                      |
| `created_at`             | DateTime | No       | Now     | Timestamp creazione.                                                               |
| `updated_at`             | DateTime | No       | Now     | Timestamp aggiornamento.                                                           |

**Nota sulla FK DEFERRABLE (2025-12-26):**
- Permette di impostare A->B e B->A nella stessa transazione DB
- Il vincolo FK viene verificato solo al COMMIT, non all'INSERT
- Semplifica enormemente la logica di create e delete delle transazioni linkate
- Non serve più il workaround di "nullify before delete"

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


---

## Phase 3: Service Layer (Business Logic)

**Status:** ✅ **COMPLETATA** (2025-12-23)

**Razionale:** Centralizzare la logica complessa (validazione saldi, linking transazioni) per renderla riutilizzabile da API, Import e CLI.

### 3.1 `TransactionService` ✅

Implementato in `backend/app/services/transaction_service.py`:

**Metodi CRUD:**
- `create_bulk(items: List[TXCreateItem]) -> TXBulkCreateResponse`
- `query(params: TXQueryParams) -> List[TXReadItem]`
- `get_by_id(tx_id: int) -> Optional[TXReadItem]`
- `update_bulk(items: List[TXUpdateItem]) -> TXBulkUpdateResponse`
- `delete_bulk(items: List[TXDeleteItem]) -> TXBulkDeleteResponse`
- `delete_by_broker(broker_id: int) -> int` (per cascade delete)

**Metodi Balance:**
- `get_cash_balances(broker_id: int) -> Dict[str, Decimal]`
- `get_asset_holdings(broker_id: int) -> Dict[int, Decimal]`
- `get_cost_basis(broker_id: int, asset_id: int) -> Decimal`

**Logica interna:**
- `_validate_broker_balances(broker_id, from_date)`: Algoritmo giorno-per-giorno
- `_get_balances_before_date(broker_id, before_date)`: Starting point per validazione

**Eccezioni:**
- `BalanceValidationError`: Saldo negativo non permesso
- `LinkedTransactionError`: Errore su transazioni collegate

**Note implementative:**
- ✅ Link resolution automatico via `link_uuid` in create_bulk
- ✅ Delete automatico di transazioni collegate
- ✅ Validazione saldi giorno-per-giorno (non intra-day)
- ✅ Skip validation se `allow_cash_overdraft` AND `allow_asset_shorting` sono True

### 3.2 `BrokerService` ✅

Implementato in `backend/app/services/broker_service.py`:

**Metodi CRUD:**
- `create_bulk(items: List[BRCreateItem]) -> BRBulkCreateResponse`
- `get_all() -> List[BRReadItem]`
- `get_by_id(broker_id: int) -> Optional[BRReadItem]`
- `get_summary(broker_id: int) -> Optional[BRSummary]`
- `update_bulk(items, broker_ids) -> BRBulkUpdateResponse`
- `delete_bulk(items: List[BRDeleteItem]) -> BRBulkDeleteResponse`

**Note implementative:**
- ✅ Auto-crea DEPOSIT transactions per `initial_balances`
- ✅ `get_summary()` include cash_balances + holdings con cost basis e market value
- ✅ Valida saldi quando si disabilita overdraft/shorting
- ✅ `delete_bulk` con `force=True` cascade-delete tutte le transazioni


---

## Phase 4: API Layer

**Status:** ✅ **COMPLETATA** (2025-12-23)

**Razionale:** Esporre endpoint RESTful coerenti. Separare nettamente la gestione file (upload/delete) dal processing (import effettivo).

### 4.1 Broker Endpoints (`/api/v1/brokers`) ✅

Implementato in `backend/app/api/v1/brokers.py`:

- `POST /brokers`: Crea broker + depositi iniziali
- `GET /brokers`: Lista broker
- `GET /brokers/{id}`: Dettagli broker
- `GET /brokers/{id}/summary`: Broker con cash_balances e holdings
- `PATCH /brokers/{id}`: Aggiorna broker (valida se disabilita flags)
- `DELETE /brokers?ids=[]&force=`: Bulk delete con cascade opzionale

### 4.2 Transaction Endpoints (`/api/v1/transactions`) ✅

Implementato in `backend/app/api/v1/transactions.py`:

- `POST /transactions`: Bulk create con link_uuid resolution
- `GET /transactions`: Query con filtri (broker, asset, types, date_range, tags, currency)
- `GET /transactions/{id}`: Singola transazione
- `GET /transactions/types`: Metadata per tutti i tipi (validazione frontend)
- `PATCH /transactions`: Bulk update
- `DELETE /transactions?ids=[]`: Bulk delete con cascade linked

**Note implementative:**
- ✅ Tutti i services e endpoint convertiti ad async (AsyncSession, await)
- ✅ Commit/rollback gestito nell'endpoint dopo verifica errors
- ✅ Query params per date_range costruiti da `date_start` + `date_end`
- ✅ Delete di linked transaction fallisce se non si eliminano entrambe
- ✅ `TXReadItem.linked_transaction_id`: popolato bidirezionalmente dal service
  - `related_transaction_id`: campo DB (unidirezionale, B → A)
  - `linked_transaction_id`: campo DTO popolato in entrambi i versi per il frontend

### 4.3 Write and debug test scripts

✅ Piano di realizzazione dei test script: 01_test_broker_transaction_subsystem.md

---

## Phase 5: Broker Report Import System (BRIM)

**Status:** 🔲 **DA IMPLEMENTARE**

**Razionale:** Disaccoppiare il core dai formati specifici dei file broker. 
Il core applicativo non deve sapere cos'è un CSV Directa o un export Degiro.
I plugin traducono formati esterni in DTOs standard (`TXCreateItem`).

**Naming Convention:** Prefisso **BRIM** (Broker Report Import Manager) per allineamento con FX, FA, BR, TX.

**Principio chiave:** L'import genera transazioni **identiche** a quelle create manualmente.
Il flusso finale passa **sempre** da `TransactionService.create_bulk()`.

---

### 5.1 Pydantic Schemas (DTOs)

Schemas per l'import system in `backend/app/schemas/brim.py`:

```python
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from enum import Enum

class BRIMFileStatus(str, Enum):
    """Status of an uploaded file."""
    UPLOADED = "uploaded"
    IMPORTED = "imported"
    FAILED = "failed"

class BRIMFileInfo(BaseModel):
    """Information about an uploaded file."""
    file_id: str  # UUID, NOT path!
    filename: str  # Original filename
    size_bytes: int
    status: BRIMFileStatus
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    compatible_plugins: List[str]  # Plugin codes that can parse this file
    error_message: Optional[str] = None

class BRIMPluginInfo(BaseModel):
    """Information about an available import plugin."""
    code: str
    name: str
    description: str
    supported_extensions: List[str]

class BRIMParseRequest(BaseModel):
    """Request to parse an uploaded file (preview)."""
    plugin_code: str
    broker_id: int

class BRIMParseResponse(BaseModel):
    """Response from parsing a file - can be edited by user before import."""
    file_id: str
    plugin_code: str
    broker_id: int
    transactions: List[TXCreateItem]  # Standard transaction DTOs
    warnings: List[str] = []  # Parser warnings (e.g., skipped rows)
    
class BRIMImportRequest(BaseModel):
    """Request to import transactions - accepts edited TXCreateItem list."""
    file_id: str
    transactions: List[TXCreateItem]  # Potentially user-modified
    tags: Optional[List[str]] = None  # Additional tags to apply to all
```

---

### 5.2 Provider Base Class, Registry & Service

Tutto consolidato in un unico file: `backend/app/services/brim_provider.py`

Segue lo stesso pattern di `FXRateProvider` e `AssetSourceProvider`.

```python
"""
Broker Report Import Manager (BRIM) - Provider base class, registry, and service.

This module provides:
- BRIMProvider: Abstract base class for broker report import plugins
- BRIMProviderRegistry: Registry for auto-discovery of plugins
- File storage functions for uploaded broker reports
- Service functions for parsing and import coordination
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime
import uuid
import json

from backend.app.schemas.transactions import TXCreateItem
from backend.app.schemas.brim import BRIMFileInfo, BRIMFileStatus, BRIMParseResponse
from backend.app.services.provider_registry import AbstractProviderRegistry


# =============================================================================
# Abstract Base Class
# =============================================================================

class BRIMProvider(ABC):
    """Abstract base class for broker report import plugins.
    
    Each plugin is responsible for parsing a specific broker's file format
    and converting it to a list of TXCreateItem DTOs.
    """
    
    @property
    @abstractmethod
    def provider_code(self) -> str:
        """Unique plugin identifier (e.g., 'directa_csv', 'broker_generic_csv')."""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable plugin name (e.g., 'Directa CSV Export')."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description for UI display."""
        pass
    
    @property
    def supported_extensions(self) -> List[str]:
        """List of supported file extensions (e.g., ['.csv', '.xlsx'])."""
        return ['.csv']
    
    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if this plugin can parse the given file."""
        pass
    
    @abstractmethod
    def parse(self, file_path: Path, broker_id: int) -> Tuple[List[TXCreateItem], List[str]]:
        """Parse file and return (transactions, warnings)."""
        pass


class BRIMParseError(Exception):
    """Raised when a file cannot be parsed by a plugin."""
    pass


# =============================================================================
# Registry (extends AbstractProviderRegistry)
# =============================================================================

class BRIMProviderRegistry(AbstractProviderRegistry):
    """Registry for broker report import plugins.
    
    Auto-discovers plugins from `backend/app/services/brim_providers/`.
    """
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "brim_providers"
    
    @classmethod
    def get_compatible_plugins(cls, file_path: Path) -> List[str]:
        """Get list of plugin codes that can parse the given file."""
        cls.auto_discover()
        compatible = []
        for code, plugin_cls in cls._providers.items():
            try:
                instance = plugin_cls()
                if instance.can_parse(file_path):
                    compatible.append(code)
            except Exception:
                continue
        return compatible


# =============================================================================
# File Storage Functions
# =============================================================================

BROKER_REPORTS_DIR = Path(__file__).parent.parent.parent / "data" / "broker_reports"

def _ensure_dirs() -> None:
    """Create storage directories if they don't exist."""
    for subdir in ["uploaded", "imported", "failed"]:
        (BROKER_REPORTS_DIR / subdir).mkdir(parents=True, exist_ok=True)


def save_uploaded_file(content: bytes, original_filename: str) -> BRIMFileInfo:
    """
    Save an uploaded file to the 'uploaded' folder.
    
    Process:
    1. Generate a UUID for the file (security: never expose original filename in path)
    2. Determine file extension from original filename
    3. Write file content to: uploaded/{uuid}.{ext}
    4. Query BRIMProviderRegistry.get_compatible_plugins() to detect which plugins can parse this file
    5. Create metadata JSON sidecar: uploaded/{uuid}.json containing:
       - file_id, filename (original), size_bytes, status=UPLOADED
       - uploaded_at (UTC timestamp), compatible_plugins list
    6. Return BRIMFileInfo with all metadata
    
    Args:
        content: Raw file bytes from upload
        original_filename: Original filename (e.g., "report_2025.csv")
    
    Returns:
        BRIMFileInfo with file_id, compatible plugins, etc.
    """
    pass


def list_files(status: Optional[BRIMFileStatus] = None) -> List[BRIMFileInfo]:
    """
    List all files, optionally filtered by status.
    
    Process:
    1. Determine which folders to scan (one folder per status, or all if status=None)
    2. For each folder, glob all *.json metadata files
    3. Parse each JSON into BRIMFileInfo
    4. Return sorted list (most recent first by uploaded_at)
    
    Args:
        status: Optional filter (UPLOADED, IMPORTED, FAILED)
    
    Returns:
        List of BRIMFileInfo objects
    """
    pass


def get_file_info(file_id: str) -> Optional[BRIMFileInfo]:
    """
    Get metadata for a specific file by its UUID.
    
    Process:
    1. Search for {file_id}.json in all three folders (uploaded, imported, failed)
    2. Return first match, or None if not found
    
    Args:
        file_id: UUID of the file
    
    Returns:
        BRIMFileInfo or None if not found
    """
    pass


def get_file_path(file_id: str) -> Optional[Path]:
    """
    Get the actual filesystem path to a file for parsing.
    
    Process:
    1. Call get_file_info() to find the file and its current status
    2. Extract original extension from the stored filename
    3. Construct path: {status_folder}/{file_id}.{ext}
    4. Verify file exists, return Path or None
    
    Args:
        file_id: UUID of the file
    
    Returns:
        Path object or None if file not found
    """
    pass


def delete_file(file_id: str) -> bool:
    """
    Delete a file and its metadata.
    
    Process:
    1. Find file location via get_file_info()
    2. Delete both the data file and .json metadata
    3. Return True if deleted, False if not found
    
    Args:
        file_id: UUID of the file
    
    Returns:
        True if deleted, False if not found
    """
    pass


def move_to_imported(file_id: str) -> bool:
    """
    Move a successfully processed file from 'uploaded' to 'imported'.
    
    Process:
    1. Get current file info and verify status is UPLOADED
    2. Move data file: uploaded/{id}.ext → imported/{id}.ext
    3. Update metadata: status=IMPORTED, processed_at=now()
    4. Write updated metadata to imported/{id}.json
    5. Delete old metadata from uploaded/
    
    Args:
        file_id: UUID of the file
    
    Returns:
        True if moved, False if not found or wrong status
    """
    pass


def move_to_failed(file_id: str, error_message: str) -> bool:
    """
    Move a failed file from 'uploaded' to 'failed' with error details.
    
    Process:
    1. Get current file info and verify status is UPLOADED
    2. Move data file: uploaded/{id}.ext → failed/{id}.ext
    3. Update metadata: status=FAILED, processed_at=now(), error_message=error
    4. Write updated metadata to failed/{id}.json
    5. Delete old metadata from uploaded/
    
    Args:
        file_id: UUID of the file
        error_message: Error description to store
    
    Returns:
        True if moved, False if not found or wrong status
    """
    pass


# =============================================================================
# Service Functions
# =============================================================================

def parse_file(file_id: str, plugin_code: str, broker_id: int) -> BRIMParseResponse:
    """
    Parse a file using the specified plugin (preview only, no DB persistence).
    
    Process:
    1. Call get_file_path(file_id) to get actual file location
       - Raise FileNotFoundError if file doesn't exist
    2. Call BRIMProviderRegistry.get_provider_instance(plugin_code)
       - Raise ValueError if plugin not found
    3. Call plugin.can_parse(file_path)
       - Raise ValueError if plugin cannot parse this file type
    4. Call plugin.parse(file_path, broker_id)
       - Returns Tuple[List[TXCreateItem], List[str]]
       - Transactions are standard DTOs ready for TransactionService
       - Warnings include skipped rows, ambiguous data, etc.
    5. Build and return BRIMParseResponse with:
       - file_id, plugin_code, broker_id
       - transactions: List[TXCreateItem]
       - warnings: List[str]
    
    IMPORTANT: This function does NOT persist anything to DB.
    It's used for preview so user can review/edit before confirming.
    
    Args:
        file_id: UUID of the uploaded file
        plugin_code: Provider code (e.g., "broker_generic_csv")
        broker_id: Target broker ID for the transactions
    
    Returns:
        BRIMParseResponse with parsed transactions and warnings
    
    Raises:
        FileNotFoundError: File not found
        ValueError: Plugin not found or cannot parse file
        BRIMParseError: Plugin-specific parsing error
    """
    pass
```

**Directory Structure:**
```
backend/app/services/
├── provider_registry.py          # Existing (no changes needed, BRIMProviderRegistry in brim_provider.py)
├── brim_provider.py              # ALL BRIM logic: base class, registry, storage, service
├── transaction_service.py        # Used for final import (existing)
└── brim_providers/               # Plugins folder (auto-discovered)
    ├── __init__.py
    ├── broker_generic_csv.py     # First plugin
    └── sample_reports/           # Test files for all plugins
        ├── README.md             # Description of each test file
        ├── generic_simple.csv    # Basic CSV with all columns
        ├── generic_dates.csv     # Various date formats
        ├── generic_types.csv     # All transaction types
        └── ... (more test files)
```

**File Storage Structure:**

```
backend/data/broker_reports/
├── uploaded/          # File appena caricati, in attesa di processing
│   ├── {uuid}.csv     # File con estensione originale
│   └── {uuid}.json    # Metadata (filename originale, uploaded_at, etc.)
├── imported/          # File processati con successo
│   ├── {uuid}.csv
│   └── {uuid}.json
└── failed/            # File che hanno fallito il processing
    ├── {uuid}.csv
    └── {uuid}.json    # Include error_message
```

---

### 5.3 API Endpoints

File: `backend/app/api/v1/brim.py`

Endpoints REST che chiamano le funzioni in `brim_provider.py`.

#### File Management

##### `POST /api/v1/brim/upload`

Upload file per futuro processing.

- **Request:** `multipart/form-data` con campo `file`
- **Logic:** 
  - Legge bytes dal file
  - Chiama `brim_provider.save_uploaded_file(content, filename)`
- **Response:** `BRIMFileInfo`
- **Errors:** 400 se file vuoto, 413 se troppo grande

##### `GET /api/v1/brim/files`

Lista file uploadati.

- **Query params:** `status` (optional): `uploaded` | `imported` | `failed`
- **Logic:** Chiama `brim_provider.list_files(status)`
- **Response:** `List[BRIMFileInfo]`

##### `GET /api/v1/brim/files/{file_id}`

Ottiene info singolo file.

- **Logic:** Chiama `brim_provider.get_file_info(file_id)`
- **Response:** `BRIMFileInfo`
- **Errors:** 404 se file non trovato

##### `DELETE /api/v1/brim/files/{file_id}`

Elimina file.

- **Logic:** Chiama `brim_provider.delete_file(file_id)`
- **Response:** `{"success": true, "file_id": "..."}`
- **Errors:** 404 se file non trovato

#### Parsing & Import

##### `POST /api/v1/brim/files/{file_id}/parse`

Parse file e ritorna transazioni per review (preview).

- **Request body:** `BRIMParseRequest`
- **Logic:** Chiama `brim_provider.parse_file(file_id, plugin_code, broker_id)`
- **Response:** `BRIMParseResponse` con `List[TXCreateItem]` + warnings
- **Errors:** 404 se file non trovato, 400 se plugin non supporta il file

L'utente può ora:
1. Visualizzare le transazioni nel frontend
2. Modificare/aggiungere/rimuovere transazioni
3. Inviare la lista modificata a `/import`

##### `POST /api/v1/brim/files/{file_id}/import`

Importa transazioni (potenzialmente modificate dall'utente).

- **Request body:** `BRIMImportRequest` con `List[TXCreateItem]`
- **Logic:**
  1. Aggiunge `tags` a ogni item se specificati nella request
  2. **Chiama `TransactionService.create_bulk(transactions, session)`** (stesso codice dell'import manuale!)
  3. Se successo: chiama `brim_provider.move_to_imported(file_id)`
  4. Se errore: chiama `brim_provider.move_to_failed(file_id, error_message)`
- **Response:** `TXBulkCreateResponse` (stesso formato di POST /transactions)
- **Errors:** 404 se file non trovato, 400/422 per validation errors

**Nota importante:** Questo endpoint usa **esattamente lo stesso** `TransactionService.create_bulk()` 
usato da `POST /api/v1/transactions`. Le transazioni importate sono indistinguibili da quelle manuali.

#### Plugin Info

##### `GET /api/v1/brim/plugins`

Lista plugin disponibili.

- **Logic:** Chiama `brim_provider.BRIMProviderRegistry.list_providers()`
- **Response:** `List[BRIMPluginInfo]`

---

### 5.4 First Plugin: Generic CSV

File: `backend/app/services/brim_providers/broker_generic_csv.py`

Plugin base che usa il decorator `@register_provider(BRIMProviderRegistry)`.

**Features:**
- Configurazione colonne via header mapping
- Supporto per formati data comuni (ISO, DD/MM/YYYY, MM/DD/YYYY)
- Mapping automatico tipi transazione
- Skip righe vuote o commenti
- Ritorna warnings per righe problematiche

```python
from backend.app.services.brim_provider import BRIMProvider, BRIMParseError, BRIMProviderRegistry
from backend.app.services.provider_registry import register_provider

@register_provider(BRIMProviderRegistry)
class GenericCSVBrokerProvider(BRIMProvider):
    """Generic CSV import plugin with auto-detection of columns."""
    
    @property
    def provider_code(self) -> str:
        return "broker_generic_csv"
    
    @property
    def provider_name(self) -> str:
        return "Generic CSV"
    
    @property
    def description(self) -> str:
        return "Import transactions from a generic CSV file with auto-detected columns"
    
    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.csv'
    
    def parse(self, file_path: Path, broker_id: int) -> Tuple[List[TXCreateItem], List[str]]:
        transactions = []
        warnings = []
        # ... implementation
        return transactions, warnings
```

**Header Mapping (auto-detected):**
```python
HEADER_MAPPINGS = {
    "date": ["date", "data", "settlement_date", "value_date"],
    "type": ["type", "tipo", "transaction_type", "operation"],
    "quantity": ["quantity", "quantità", "qty", "shares"],
    "amount": ["amount", "importo", "value", "cash"],
    "currency": ["currency", "valuta", "ccy"],
    "description": ["description", "descrizione", "notes", "memo"],
    "asset": ["asset", "symbol", "ticker", "isin"],
}
```

**Type Mapping:**
```python
TYPE_MAPPINGS = {
    # BUY
    "buy": TransactionType.BUY,
    "acquisto": TransactionType.BUY,
    "purchase": TransactionType.BUY,
    # SELL
    "sell": TransactionType.SELL,
    "vendita": TransactionType.SELL,
    # ... etc
}
```

---

### 5.5 Flusso Completo

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND                                        │
├─────────────────────────────────────────────────────────────────────────┤
│  1. Upload file       ──POST /brim/upload──►  BRIMFileInfo               │
│                                                                          │
│  2. Select plugin     ──POST /brim/files/{id}/parse──►  BRIMParseResponse│
│     & broker                                              │              │
│                                                           ▼              │
│  3. Review/Edit       ◄── List[TXCreateItem] + warnings ─┘              │
│     transactions                                                         │
│     (user modifies)                                                      │
│                                                                          │
│  4. Confirm import    ──POST /brim/files/{id}/import──►  TXBulkResponse │
│                          (with modified List[TXCreateItem])              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                          BACKEND                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  /parse endpoint:                                                        │
│    brim_provider.parse_file() → BRIMProvider.parse() → List[TXCreateItem]│
│                                                                          │
│  /import endpoint:                                                       │
│    TransactionService.create_bulk(transactions) ← SAME AS MANUAL!       │
│    brim_provider.move_to_imported()                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 5.6 Test Strategy

#### Sample Reports Directory

La cartella `sample_reports/` contiene file di test per tutti i plugin:

```
backend/app/services/brim_providers/sample_reports/
├── README.md                     # Description of each test file and expected results
├── generic_simple.csv            # Basic CSV - all columns present
├── generic_dates.csv             # Various date formats
├── generic_types.csv             # All transaction types
├── generic_missing_cols.csv      # Missing optional columns
├── generic_bad_rows.csv          # Some invalid rows (should produce warnings)
├── generic_multilang.csv         # Mixed language headers (date, data, fecha)
└── ... (future broker-specific files: directa_export.csv, degiro_export.csv)
```

#### Test File: `backend/test_scripts/test_services/test_brim_providers.py`

**Struttura generica per tutti i plugin** (come FX e Asset providers):

I test sono scritti in modo generico e vengono eseguiti per TUTTI i plugin registrati contro TUTTI i file di esempio. Ogni file deve essere processato da almeno un plugin.

```python
"""
BRIM Provider Tests - Generic test suite for all broker report import plugins.

This test module:
1. Discovers ALL plugins via BRIMProviderRegistry
2. Discovers ALL sample files in sample_reports/
3. For each plugin, tests ALL files that the plugin claims to support
4. Verifies that EVERY sample file is processed by at least one plugin

Test Categories:
- Plugin Discovery & Registration
- File Compatibility Detection
- Parse Functionality
- Full Coverage Verification
"""
import pytest
from pathlib import Path
from backend.app.services.brim_provider import BRIMProviderRegistry, BRIMProvider

SAMPLE_REPORTS_DIR = Path(__file__).parent.parent.parent / "app" / "services" / "brim_providers" / "sample_reports"


class TestBRIMProviderDiscovery:
    """Test plugin auto-discovery and registration."""
    
    def test_registry_discovers_plugins(self):
        """At least one plugin should be registered."""
        providers = BRIMProviderRegistry.list_providers()
        assert len(providers) > 0
    
    def test_all_plugins_have_required_properties(self):
        """Each plugin must have code, name, description."""
        for info in BRIMProviderRegistry.list_providers():
            plugin = BRIMProviderRegistry.get_provider_instance(info['code'])
            assert plugin.provider_code
            assert plugin.provider_name
            assert plugin.description
            assert isinstance(plugin.supported_extensions, list)


class TestBRIMProviderParsing:
    """Generic parsing tests run for ALL plugins against ALL compatible files."""
    
    @pytest.fixture
    def all_sample_files(self) -> list[Path]:
        """Get all sample report files."""
        return [f for f in SAMPLE_REPORTS_DIR.glob("*.*") if f.suffix != '.md']
    
    @pytest.fixture
    def all_plugins(self) -> list[BRIMProvider]:
        """Get instances of all registered plugins."""
        BRIMProviderRegistry.auto_discover()
        return [
            BRIMProviderRegistry.get_provider_instance(info['code'])
            for info in BRIMProviderRegistry.list_providers()
        ]
    
    def test_each_plugin_parses_compatible_files(self, all_plugins, all_sample_files):
        """Each plugin should successfully parse files it claims to support."""
        for plugin in all_plugins:
            for file_path in all_sample_files:
                if plugin.can_parse(file_path):
                    # Plugin claims support - it MUST parse without exception
                    transactions, warnings = plugin.parse(file_path, broker_id=1)
                    
                    # Basic validations
                    assert isinstance(transactions, list)
                    assert isinstance(warnings, list)
                    
                    for tx in transactions:
                        assert tx.type is not None
                        assert tx.date is not None
                        assert tx.broker_id == 1
    
    def test_every_sample_file_is_processed(self, all_plugins, all_sample_files):
        """Every sample file must be processable by at least one plugin."""
        unprocessed = []
        
        for file_path in all_sample_files:
            processed = False
            for plugin in all_plugins:
                if plugin.can_parse(file_path):
                    try:
                        plugin.parse(file_path, broker_id=1)
                        processed = True
                        break
                    except Exception:
                        continue
            
            if not processed:
                unprocessed.append(file_path.name)
        
        assert not unprocessed, f"These files were not processed by any plugin: {unprocessed}"
    
    def test_parse_returns_valid_transactions(self, all_plugins, all_sample_files):
        """Parsed transactions must be valid TXCreateItem objects."""
        for plugin in all_plugins:
            for file_path in all_sample_files:
                if not plugin.can_parse(file_path):
                    continue
                
                transactions, _ = plugin.parse(file_path, broker_id=1)
                
                for tx in transactions:
                    assert hasattr(tx, 'type')
                    assert hasattr(tx, 'date')
                    assert hasattr(tx, 'broker_id')
                    if tx.cash:
                        assert tx.cash.amount is not None
                        assert tx.cash.code is not None


class TestBRIMFileCoverage:
    """Verify test file coverage."""
    
    def test_sample_reports_directory_exists(self):
        """Sample reports directory must exist."""
        assert SAMPLE_REPORTS_DIR.exists()
    
    def test_sample_reports_not_empty(self):
        """At least one sample file must exist."""
        files = [f for f in SAMPLE_REPORTS_DIR.glob("*.*") if f.suffix != '.md']
        assert len(files) > 0, "No sample report files found"
    
    def test_readme_documents_all_files(self):
        """README.md should document all sample files."""
        readme = SAMPLE_REPORTS_DIR / "README.md"
        if readme.exists():
            content = readme.read_text()
            for f in SAMPLE_REPORTS_DIR.glob("*.*"):
                if f.suffix != '.md':
                    assert f.name in content, f"README doesn't document: {f.name}"
```

#### Additional Test Files

**`test_brim_api.py`:**
- Upload endpoint
- List/get/delete endpoints
- Parse endpoint (preview)
- Import endpoint (uses TransactionService)
- Error handling
- Full flow: upload → parse → edit → import

---

## Phase 6: Export/Backup Endpoints

**Status:** 🔲 **PLACEHOLDER**

Placeholder per funzionalità future. Attualmente ritornano 501 Not Implemented.

- `GET /api/v1/backup/export`: Esporta dati in formato JSON/CSV
- `POST /api/v1/backup/restore`: Ripristina dati da backup

---

## Notes: Implementation Order

**Razionale:** Ordine logico per minimizzare i blocchi. Prima il DB, poi la logica core, infine le API e i plugin.

### Fasi Completate

1. ✅ **Phase 1 - DB Refactoring:** Schema unificato Transaction, update Broker, User models.
2. ✅ **Phase 2 - Pydantic Schemas:** DTOs per TX, BR con validazione business rules.
3. ✅ **Phase 3 - Service Layer:** TransactionService e BrokerService con balance validation.
4. ✅ **Phase 4 - API Layer:** Endpoints REST per brokers e transactions.
5. ✅ **Test Suite:** 190 test per schema, service, API (Categories 1-6).

### Fasi Successive

6. 🔲 **Phase 5 - Broker Report Import System (BRIM):**
   - [ ] Creare `schemas/brim.py` con DTOs (BRIMFileInfo, BRIMPluginInfo, BRIMParseRequest/Response, BRIMImportRequest)
   - [ ] Creare `services/brim_provider.py` con abstract class, registry, file storage e service functions
   - [ ] Creare `services/brim_providers/__init__.py`
   - [ ] Creare `services/brim_providers/sample_reports/` con file di test
   - [ ] Creare `services/brim_providers/broker_generic_csv.py` primo plugin
   - [ ] Creare `api/v1/brim.py` endpoints REST
   - [ ] Test suite per BRIM system (test_brim_providers.py, test_brim_api.py)

7. 🔲 **Phase 6 - Export/Backup:** Placeholder per funzionalità future.

