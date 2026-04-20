# Phase 7 — Part 2: BRIM Plugin v2 (Events & UI Metadata)

> **Status**: 📋 Pianificato
> **Predecessore**: [`plan-phase07-transaction-Part1.md`](./plan-phase07-transaction-Part1.md) (✅ completato)
> **Phase overview**: [`phases/phase-07-transactions.md`](./phases/phase-07-transactions.md) — sezione "Parte 2"
> **Giorni stimati**: 2

---

## 🎯 Obiettivo

Evolvere la classe base [`BRIMProvider`](../../backend/app/services/brim_provider.py) con una firma `parse() → BRIMParseOutput` che include `asset_events`, e aggiungere metadati per il rendering dinamico della Staging Modal (`capabilities`, `preview_columns`, `docs_url`). Riscrivere i **11 plugin broker** senza wrapper legacy (v1 mai andata in produzione). Introdurre un nuovo endpoint `POST /api/v1/brokers/import/commit` che crea **atomicamente** eventi + transazioni, con rollback totale in caso di qualunque fallimento.

---

## 🧱 Situazione di partenza

- [`BRIMProvider.parse()`](../../backend/app/services/brim_provider.py:274) ritorna `Tuple[List[TXCreateItem], List[str], Dict[int, BRIMExtractedAssetInfo]]`.
- Nessun metodo per gli eventi (`asset_events`).
- Nessun `docs_url` / `capabilities` / `preview_columns` — TODO esplicito a [L319–327](../../backend/app/services/brim_provider.py:319).
- Le 11 subclassi in [`brim_providers/`](../../backend/app/services/brim_providers/) sono:
  `broker_directa`, `broker_ibkr`, `broker_freetrade`, `broker_schwab`, `broker_trading212`, `broker_etoro`, `broker_degiro`, `broker_generic_csv`, `broker_revolut`, `broker_coinbase`, `broker_finpension`.
- Endpoint esistente [`POST /files/{file_id}/parse`](../../backend/app/api/v1/brokers.py:638) ritorna `BRIMParseResponse` con solo transactions + asset_mappings + duplicates + warnings.
- [`TransactionService.create_bulk()`](../../backend/app/services/transaction_service.py:133) **non committa** (la commit è gestita dalla dependency `get_session_generator`) e **non solleva** su errori per-item (raccoglie in `results[]`). Questo ci consente di condividere la sessione e di chiamare `rollback()` esplicito.
- [`AssetCRUDService.bulk_upsert_events_manual()`](../../backend/app/services/asset_source.py:2334) segue lo stesso pattern (sessione condivisa, no commit interno).

---

## 🧠 Decisioni architetturali

| Tema | Scelta | Motivazione |
|------|--------|-------------|
| **Linking TX ↔ evento nel commit** | Nessun ref simbolico. Plugin popola `TXCreateItem.asset_event_id` **solo** se l'evento esiste già in DB (via own search). Eventi nuovi e TX nuove sono indipendenti. | Il linking TX↔nuovo-evento non è requisito di import: l'utente lo fa manualmente post-import dalla Staging Modal (feature Part 5). Evita complessità inutile. |
| **Evento duplicato (stesso `asset_id, date, type`)** | Fail esplicito con messaggio chiaro. Nessun upsert silenzioso nel path import. | Nella realtà finanziaria non esistono eventi multipli dello stesso tipo nello stesso giorno sullo stesso asset. Un duplicato = errore dato, utente deve correggere tipo/data/valore esistente. |
| **Atomicità commit** | Rollback totale se anche una sola TX o evento fallisce. Flag `rolled_back: bool` nel response. | Un import BRIM è un insieme coerente: o entra tutto o niente. |
| **`preview_columns()`** | `@abstractmethod` — obbligatorio per tutti gli 11 plugin. | Nessuna scorciatoia: questa è la fase strutturale, si costruisce dritto. |
| **`capabilities`** | `BRIMCapabilities` come BaseModel Pydantic in `schemas/brim.py` (serializzabile verso il frontend tramite `BRIMPluginInfo`). | Pattern coerente con `provider_params_schema` di FX/Asset. |
| **Wrapper legacy v1** | ❌ nessuno. Refactor pulito. | v1 mai andata in produzione. |
| **Schemi base da `common.py`** | `BRIMCommitResponse` estende `BaseBulkResponse[BRIMCommitResultItem]`. Gli altri schemi nuovi non hanno match in `common.py`. | `BaseBulkResponse` fornisce già `results`, `success_count`, `failed_count` computed. |

---

## 🧩 Steps

### Step 1 — Schemi in [`backend/app/schemas/brim.py`](../../backend/app/schemas/brim.py)

Aggiungere:

- **`BRIMCapabilities`** (`BaseModel` + `ConfigDict(extra="forbid")`):
  ```python
  class BRIMCapabilities(BaseModel):
      model_config = ConfigDict(extra="forbid")
      supports_events: bool = False          # plugin estrae asset_events (es. IBKR)
      supports_fees_aggregation: bool = False  # plugin aggrega fee in una TX unica
      multi_broker_file: bool = False        # un singolo file può contenere TX di broker diversi
      # Estendibile in futuro con altri flag
  ```

- **`BRIMPreviewColumn`** (`BaseModel` + `ConfigDict(extra="forbid")`):
  ```python
  class BRIMPreviewColumn(BaseModel):
      model_config = ConfigDict(extra="forbid")
      key: str                      # chiave del campo nella riga TX/event
      label: str                    # etichetta colonna (passata a i18n lato frontend)
      type: Literal["text", "number", "date", "currency", "enum", "boolean"]
      width: Optional[str] = None   # es. "120px", "10%"
      align: Optional[Literal["left", "center", "right"]] = None
  ```

- **`BRIMParseOutput`** (`BaseModel`) — il nuovo tipo di ritorno di `BRIMProvider.parse()`:
  ```python
  class BRIMParseOutput(BaseModel):
      model_config = ConfigDict(extra="forbid")
      transactions: List[TXCreateItem] = Field(default_factory=list)
      warnings: List[str] = Field(default_factory=list)
      extracted_assets: Dict[int, BRIMExtractedAssetInfo] = Field(default_factory=dict)
      asset_events: List[FAAssetEventPoint] = Field(default_factory=list)
  ```

- **`BRIMCommitRequest`**:
  ```python
  class BRIMCommitRequest(BaseModel):
      model_config = ConfigDict(extra="forbid")
      file_id: str
      broker_id: int = Field(..., gt=0)
      transactions: List[TXCreateItem] = Field(default_factory=list)
      asset_events: List[FAEventUpsert] = Field(default_factory=list)   # raggruppati per asset_id
      asset_mappings: List[BRIMAssetMapping] = Field(default_factory=list)
  ```

- **`BRIMCommitResultItem`**:
  ```python
  class BRIMCommitResultItem(BaseModel):
      success: bool
      kind: Literal["tx", "event"]
      tx_id: Optional[int] = None
      event_id: Optional[int] = None
      error: Optional[str] = None
  ```

- **`BRIMCommitResponse`** (estende `BaseBulkResponse[BRIMCommitResultItem]`):
  ```python
  class BRIMCommitResponse(BaseBulkResponse[BRIMCommitResultItem]):
      rolled_back: bool = False
      created_tx_ids: List[int] = Field(default_factory=list)
      created_event_ids: List[int] = Field(default_factory=list)
  ```

- **Estendere `BRIMPluginInfo`** con:
  ```python
  docs_url: Optional[str] = None
  capabilities: BRIMCapabilities = Field(default_factory=BRIMCapabilities)
  preview_columns: List[BRIMPreviewColumn] = Field(default_factory=list)
  ```

- **Estendere `BRIMParseResponse`** con:
  ```python
  asset_events: List[FAAssetEventPoint] = Field(default_factory=list)
  ```

**Import aggiuntivi**: `FAAssetEventPoint`, `FAEventUpsert` da `schemas/prices.py`; `BaseBulkResponse` da `schemas/common.py`; `Literal` da `typing`.

---

### Step 2 — Evolvere classe base [`BRIMProvider`](../../backend/app/services/brim_provider.py:85)

1. Cambiare firma:
   ```python
   @abstractmethod
   def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
       ...
   ```
   Aggiornare docstring per descrivere i 4 campi dell'output.

2. Aggiungere 3 property/method:
   ```python
   @property
   def docs_url(self) -> Optional[str]:
       """URL alla documentazione del plugin. Default: None."""
       return None

   @property
   def capabilities(self) -> BRIMCapabilities:
       """Feature flags del plugin. Default: tutto False."""
       return BRIMCapabilities()

   @abstractmethod
   def preview_columns(self) -> List[BRIMPreviewColumn]:
       """Colonne da mostrare nella Staging Modal per questo plugin.
       Obbligatorio in ogni subclass — niente default."""
       pass
   ```

3. Rimuovere il TODO [L319–327](../../backend/app/services/brim_provider.py:319).

4. Aggiornare `to_plugin_info()` per propagare:
   ```python
   return BRIMPluginInfo(
       code=self.provider_code,
       name=self.provider_name,
       description=self.description,
       supported_extensions=self.supported_extensions,
       icon_url=self.icon_url,
       docs_url=self.docs_url,
       capabilities=self.capabilities,
       preview_columns=self.preview_columns(),
   )
   ```

5. Aggiornare docstring di classe per riflettere le nuove responsabilità.

---

### Step 3 — Refactor 11 plugin in [`backend/app/services/brim_providers/`](../../backend/app/services/brim_providers/)

Per ciascuno dei file:
`broker_directa.py`, `broker_ibkr.py`, `broker_freetrade.py`, `broker_schwab.py`, `broker_trading212.py`, `broker_etoro.py`, `broker_degiro.py`, `broker_generic_csv.py`, `broker_revolut.py`, `broker_coinbase.py`, `broker_finpension.py`:

1. **Cambiare signature `parse()`** → ritornare `BRIMParseOutput` invece della tupla. `asset_events=[]` default. I plugin che già estraggono dividend (tipicamente **IBKR**, **Schwab**) popolano `asset_events` coerentemente.

2. **Implementare `preview_columns()`** obbligatoriamente. Baseline minima per tutti:
   - `date`, `type`, `quantity`, `asset`, `cash_amount`, `cash_currency`.
   Plugin specifici aggiungono colonne native (es. `fees`, `exchange`, `notes`).

3. **Dichiarare `capabilities`** con flag coerenti:
   - IBKR / Schwab: `supports_events=True` se estraggono dividend.
   - Plugin che aggregano fee (es. Degiro): `supports_fees_aggregation=True`.
   - Plugin multi-broker (se presenti): `multi_broker_file=True`.
   - Altri: tutto False.

4. **Aggiungere `docs_url`** dove rilevante (link alla doc interna MkDocs, es. `/mkdocs/user/brokers/directa/`).

5. **Nessun wrapper legacy**. Chi importa `BRIMProvider` in test/notebook deve essere aggiornato.

---

### Step 4 — Nuovo service `commit_import()` in [`backend/app/services/brim_provider.py`](../../backend/app/services/brim_provider.py)

Aggiungere funzione async dopo `parse_file()`:

```python
async def commit_import(
    req: BRIMCommitRequest,
    session: AsyncSession,
    user_id: int,
) -> BRIMCommitResponse:
    """
    Commit atomico di transazioni + eventi da un import BRIM.

    Flow:
    1. Upsert eventi (strict: fail se duplicato (asset_id, date, type) già in DB).
    2. Create transazioni via TransactionService.create_bulk().
    3. Se qualunque step fallisce → await session.rollback() + response con rolled_back=True.
    4. Altrimenti commit implicito via FastAPI dependency.
    """
    results: List[BRIMCommitResultItem] = []
    created_event_ids: List[int] = []
    created_tx_ids: List[int] = []

    # --- Phase 1: Events ---
    event_errors: List[str] = []
    if req.asset_events:
        event_res = await AssetCRUDService.bulk_upsert_events_strict(
            data=req.asset_events,
            session=session,
        )
        for r in event_res["results"]:
            if r.get("error"):
                event_errors.append(r["error"])
                results.append(BRIMCommitResultItem(
                    success=False, kind="event", error=r["error"],
                ))
            else:
                created_event_ids.extend(r.get("event_ids", []))
                for eid in r.get("event_ids", []):
                    results.append(BRIMCommitResultItem(
                        success=True, kind="event", event_id=eid,
                    ))

    # --- Phase 2: Transactions ---
    tx_res = None
    if not event_errors:
        tx_svc = TransactionService(session)
        tx_res = await tx_svc.create_bulk(req.transactions, user_id=user_id)
        for r in tx_res.results:
            if r.success:
                created_tx_ids.append(r.transaction_id)
                results.append(BRIMCommitResultItem(
                    success=True, kind="tx", tx_id=r.transaction_id,
                ))
            else:
                results.append(BRIMCommitResultItem(
                    success=False, kind="tx", error=r.error,
                ))

    # --- Phase 3: Atomicity check ---
    any_failure = (
        bool(event_errors)
        or (tx_res is not None and (tx_res.success_count < len(req.transactions) or tx_res.errors))
    )

    if any_failure:
        await session.rollback()
        return BRIMCommitResponse(
            results=results,
            success_count=0,
            rolled_back=True,
            created_tx_ids=[],
            created_event_ids=[],
        )

    return BRIMCommitResponse(
        results=results,
        success_count=sum(1 for r in results if r.success),
        rolled_back=False,
        created_tx_ids=created_tx_ids,
        created_event_ids=created_event_ids,
    )
```

**Nuovo helper `bulk_upsert_events_strict`** in [`asset_source.py`](../../backend/app/services/asset_source.py):

Rispetto a `bulk_upsert_events_manual`, questa variante deve:
- Fallire (senza raise, ritornando errore in `results`) se `(asset_id, date, type)` già esiste in DB o compare duplicato nel batch stesso.
- Ritornare gli `event_ids` reali creati (necessari per il response).

Verificare prima il comportamento attuale di `_upsert_asset_events` (update silenzioso vs insert): se oggi fa update, il nuovo helper usa una pre-check esplicita con `SELECT` su `(asset_id, date, type)` e raise interno catturato come `error` nel dict di risultato.

---

### Step 5 — Endpoint API

1. **Nuovo**: `POST /api/v1/brokers/import/commit` in [`backend/app/api/v1/brokers.py`](../../backend/app/api/v1/brokers.py):
   ```python
   @brim_router.post("/commit", response_model=BRIMCommitResponse)
   async def commit_import_endpoint(
       request: BRIMCommitRequest,
       current_user: User = Depends(get_current_user),
       session: AsyncSession = Depends(get_session_generator),
   ) -> BRIMCommitResponse:
       # EDITOR-gated sul broker_id target
       broker_service = BrokerService(session)
       role = await broker_service._check_user_access(
           request.broker_id, current_user.id, min_role=UserRole.EDITOR,
       )
       if role is None and not current_user.is_superuser:
           raise HTTPException(status_code=403, detail="EDITOR or OWNER access required")

       response = await commit_import(request, session, current_user.id)

       if not response.rolled_back:
           # Sposta il file in parsed/ solo se il commit è andato a buon fine
           brim_provider.move_to_parsed(request.file_id)

       return response
   ```

2. **Aggiornare endpoint esistente** [`POST /files/{file_id}/parse`](../../backend/app/api/v1/brokers.py:638):
   - Cambiare il chiamante a `brim_provider.parse_file()` per unpack del nuovo `BRIMParseOutput`.
   - Propagare `asset_events` nella `BRIMParseResponse`.

3. **Aggiornare `parse_file()` in `brim_provider.py`** di conseguenza: ora ritorna `BRIMParseOutput` (o una tupla estesa a 4 elementi, coerente con il cambio di firma del plugin).

---

### Step 6 — Test & rigenerazione client

**Test backend** (sotto `backend/test_scripts/`):

1. Unit per ciascun plugin (`test_brim_provider_<nome>.py`):
   - Verifica che `parse()` ritorni `BRIMParseOutput` con la forma attesa.
   - Verifica `preview_columns()` non vuoto, `capabilities` coerenti.
   - Fixture da `backend/app/services/brim_providers/sample_reports/`.

2. Integration `test_brim_commit_import.py`:
   - Success case (eventi + TX ok).
   - Failure case: evento duplicato → rollback, nessuna TX creata.
   - Failure case: TX fallisce (broker access denied) → rollback, nessun evento creato.
   - Edge: commit con solo TX (no events), solo events (no TX), vuoto.

3. API `test_api_brim_commit.py`:
   - Matrix OWNER / EDITOR / VIEWER × broker owned/foreign.
   - 403 per ruoli insufficienti.
   - `rolled_back` flag presente e consistente nella response.

**Regen**:
- `./dev.py api sync` per rigenerare [`frontend/src/lib/api/generated.ts`](../../frontend/src/lib/api/generated.ts) e `openapi.json`.
- **Nessun `db create-clean`**: nessuna modifica a `001_initial.py`.

---

## 📦 Deliverable

- [ ] Classe base `BRIMProvider` estesa con `docs_url`, `capabilities`, `preview_columns`, `parse() → BRIMParseOutput`.
- [ ] 11 plugin broker refactorati, nessun wrapper legacy.
- [ ] Schemi `BRIMCapabilities`, `BRIMPreviewColumn`, `BRIMParseOutput`, `BRIMCommitRequest`, `BRIMCommitResultItem`, `BRIMCommitResponse` aggiunti.
- [ ] `BRIMPluginInfo` e `BRIMParseResponse` estesi.
- [ ] Nuovo helper `AssetCRUDService.bulk_upsert_events_strict` per validazione unicità.
- [ ] Service `commit_import()` atomico con rollback esplicito.
- [ ] Endpoint `POST /api/v1/brokers/import/commit` EDITOR-gated.
- [ ] Endpoint `POST /files/{file_id}/parse` aggiornato per propagare `asset_events`.
- [ ] Client TypeScript rigenerato via `./dev.py api sync`.
- [ ] Test suite backend green: unit per 11 plugin + integration commit + API matrix.

---

## ⚠️ Open points (da chiarire durante Step 4)

1. **Comportamento attuale di `_upsert_asset_events`** in [`asset_source.py`](../../backend/app/services/asset_source.py): esegue update silenzioso su conflitto `(asset_id, date, type)` o crea duplicato? Leggere il codice prima di scrivere `bulk_upsert_events_strict`. Se già fa update, estrarre la logica di pre-check in un helper riusabile; se crea duplicato, il nuovo helper sarà sostanzialmente una versione con pre-check `SELECT`.

2. **Coerenza `rolled_back` con `BaseBulkResponse`**: `BaseBulkResponse[T]` ha `success_count`. Se `rolled_back=True` impostiamo `success_count=0` anche se le Phase 1/2 avevano parziali successi in memoria — coerente con la semantica "nessuna modifica al DB".

3. **Conseguenze sul frontend (Part 4)**: la Staging Modal dovrà rendering-ire `preview_columns` del plugin usato, mostrare un banner rosso se `rolled_back=True` con `results` per debug. Questo è lavoro di Part 4 — qui ci limitiamo a esporre l'API.

---

## 🔗 Cross-link

- **Piano padre** (Phase 7 overview): [`phases/phase-07-transactions.md`](./phases/phase-07-transactions.md), sezione "Parte 2 — BRIM Plugin v2".
- **Predecessore** (Part 1): [`plan-phase07-transaction-Part1.md`](./plan-phase07-transaction-Part1.md).
- **Successori** (Part 3, 4, 5): da creare quando Part 2 sarà completata.
- **Feature correlata**: linking manuale TX↔evento dalla Staging Modal → spostata in **Part 5** (deferred da Part 1).

