# Fase 05c – Code Factoring & Schema Unification Checklist

## Obiettivi Principali

1. Aggiungere test di backward-fill che verifichi la propagazione del campo `volume`.
2. Introdurre logging strutturato nel fallback provider (`_fetch_provider_history`) per diagnosi errori.
3. Documentare la nuova colonna `volume` in `docs/database-schema.md` e nella guida API.
4. Uniformare le API: sostituire `PriceQueryResult` con `PricePointModel` eliminando duplicati.
5. Eseguire un censimento di tutte le classi Pydantic (`BaseModel`), raggruppare quelle simili, proporre merge e migrazioni.
6. (Nuovo) Consolidare i modelli di sync FX dentro lo stesso file `refresh.py` insieme ai modelli FA di refresh, mantenendo distinzione semantica (sezione FA Refresh / sezione FX
   Sync) ma unificandone la collocazione per coerenza operativa.
7. (Nuovo) Aggiungere docstring di scopo in testa a TUTTI i file sotto `schemas/` (common, assets, provider, prices, refresh, fx) che descrivano finalità, domini coperti e note di
   design (naming FX/FA, differenze strutturali 2 vs 3 livelli, assenza retro‑compatibilità).
8. (Nuovo) Verificare ed eliminare ogni residuo di definizioni Pydantic dentro `api/v1/*.py` spostandole nei relativi file schema (nessuna definizione inline negli endpoint).
   Retro‑compatibilità non richiesta.

---

## 1. Test Backward-Fill con Volume

- [x] 1.1 Creare nuovo test `test_backward_fill_volume_propagation` in `backend/test_scripts/test_services/test_asset_source.py`.
    - Scenario: prezzi disponibili per i primi 2 giorni con volume; terzo e quarto giorno mancanti -> verificare propagazione `close` e `volume`.
    - Asserzioni: `PricePointModel.backward_fill_info` non è `None`; `volume` backfilled = ultimo noto.
- [x] 1.2 Caso edge: primo giorno senza dati -> nessun backfill (lista più corta) + log esplicativo.
- [x] 1.3 Aggiornare summary test runner per includere conteggio backfilled con volume.
- [x] 1.4 Aggiornare documentazione di testing (cartella `docs/testing/`).

## 2. Logging Fallback Provider

- [x] 2.1 Aggiungere logger e `warning` dettagliato (`provider_code`, `asset_id`, eccezione) se `_fetch_provider_history` fallisce.
- [x] 2.2 Log distinto: provider non registrato vs eccezione runtime.
- [x] 2.3 Test che forza provider inesistente verificando fallback + nessun crash.

## 3. Documentazione Colonna Volume

- [x] 3.1 Aggiornare `docs/database-schema.md` sezione "PriceHistory.volume" (tipo, dominio, motivazioni: liquidità, VWAP futuro).
- [x] 3.2 Aggiornare guida API (es. `api-development-guide.md`) includendo `volume` nella risposta get prices.
- [x] 3.3 Nota retrocompatibilità: prima assente, ora presente (null se sconosciuto).
- [x] 3.4 Aggiornare `FEATURE_COVERAGE_REPORT.md`.

## 4. Uniformare API: Eliminare PriceQueryResult

- [x] 4.1 Analisi differenze tra `PriceQueryResult` e `PricePointModel`.
- [x] 4.2 Rimuovere `PriceQueryResult`.
- [x] 4.3 Modificare endpoint GET `/assets/{asset_id}/prices`.
- [x] 4.4 Aggiornare test (service tests già passano - 15/15).
- [x] 4.5 Grep globale riferimenti (solo in documentazione/checklist).
- [x] 4.6 Aggiornare documentazione API.
- [x] 4.7 Validare assenza cicli import (✅ verificato).

## 5. Censimento & Unificazione Classi Pydantic

(Sezioni inventario e raggruppamenti invariati – già analizzati)

#### Aggiornamento Decisioni Utente

- "Scelta utente" accettata: spostare anche le classi FX di sync in `refresh.py` sotto sezione dedicata.
- Docstring esplicativo richiesto per ogni file schema.
- Rimozione definizioni inline da `api/v1/*.py` obbligatoria.

---

## 6. Mapping Dettagliato Spostamenti Classe per Classe (Aggiornato)

### 6.1 Creazione / Aggiornamento File Schema

- `backend/app/schemas/provider.py`: provider info & assignment (FA + FX)
- `backend/app/schemas/prices.py`: operazioni prezzi FA (upsert, delete, query)
- `backend/app/schemas/refresh.py`: sezione FA Refresh + sezione FX Sync (NUOVO spostamento FXSyncResponse e correlati)
- `backend/app/schemas/common.py`: aggiungere `DateRangeModel` (con validazione `end >= start` se presente)
- `backend/app/schemas/assets.py`: modelli asset (PricePointModel, InterestRatePeriod, ScheduledInvestment*)
- `backend/app/schemas/fx.py`: resta per upsert/delete/conversion/pair sources FX; rimuovere componenti sync spostati.

### 6.2 Provider Schemas (come prima)

**API v1 - Financial Assets (FA) (`backend/app/api/v1/assets.py`):**

- ProviderAssignmentItem
- BulkAssignProvidersRequest
- ProviderAssignmentResult
- BulkAssignProvidersResponse
- BulkRemoveProvidersRequest
- BulkRemoveProvidersResponse
- PriceUpsertItem
- AssetPricesUpsert
- BulkUpsertPricesRequest
- AssetPricesUpsertResult
- BulkUpsertPricesResponse
- DateRange
- AssetPricesDelete
- BulkDeletePricesRequest
- AssetPricesDeleteResult
- BulkDeletePricesResponse
- RefreshItem
- BulkRefreshRequest
- RefreshResult
- BulkRefreshResponse
- **PriceQueryResult** (da eliminare - duplicato)
- GetPricesResponse
- ProviderInfo

**Schemas - FX (`backend/app/schemas/fx.py`):**

- ProviderInfoModel
- ProvidersResponseModel
- SyncResponseModel
- ConversionRequestModel
- ConvertRequestModel
- ConversionResultModel
- ConvertResponseModel
- RateUpsertItemModel
- UpsertRatesRequestModel
- RateUpsertResultModel
- UpsertRatesResponseModel
- RateDeleteRequestModel
- DeleteRatesRequestModel
- RateDeleteResultModel
- DeleteRatesResponseModel
- PairSourceItemModel
- PairSourcesResponseModel
- CreatePairSourcesRequestModel
- PairSourceResultModel
- CreatePairSourcesResponseModel

**Schemas - Assets (`backend/app/schemas/assets.py`):**

- BackwardFillInfo
- CurrentValueModel
- PricePointModel
- HistoricalDataModel
- AssetProviderAssignmentModel
- InterestRatePeriod
- LateInterestConfig
- ScheduledInvestmentSchedule
- ScheduledInvestmentParams

**Schemas - Common (`backend/app/schemas/common.py`):**

- BackwardFillInfo (già presente, condiviso)

### 6.3 Price Schemas (come prima)

- [x] 7.3.1 Copiare e rinominare classi FA prices in `schemas/prices.py`:
    - `PriceUpsertItem` → `FAUpsertItem`
    - `AssetPricesUpsert` → `FAUpsert`
    - `BulkUpsertPricesRequest` → `FABulkUpsertRequest`
    - `AssetPricesUpsertResult` → `FAUpsertResult`
    - `BulkUpsertPricesResponse` → `FABulkUpsertResponse`
    - `AssetPricesDelete` → `FAAssetDelete` (sostituire `DateRange` con `DateRangeModel`)
    - `BulkDeletePricesRequest` → `FABulkDeleteRequest`
    - `AssetPricesDeleteResult` → `FAAssetDeleteResult`
    - `BulkDeletePricesResponse` → `FABulkDeleteResponse`
    - `GetPricesResponse` → `FAGetPricesResponse` (usare `PricePointModel`)
- [x] 7.3.2 Eliminare definizione `PriceQueryResult` da `api/v1/assets.py`.
- [x] 7.3.3 Aggiornare `FAGetPricesResponse` per usare `List[PricePointModel]` da `schemas/assets`.
- [x] 7.3.4 Aggiornare import in `api/v1/assets.py`:
    - Rimuovere classi spostate.
    - Aggiungere `from backend.app.schemas.prices import FAUpsertItem, FABulkUpsertRequest, ...`
    - Aggiungere `from backend.app.schemas.common import DateRangeModel`
- [x] 7.3.5 Aggiornare tutti gli endpoint prices per usare nuovi nomi.
- [x] 7.3.6 Aggiornare `backend/app/services/asset_source.py` per ritornare `PricePointModel` invece di dict.
- [x] 7.3.7 Test: eseguire `./test_runner.py services asset-source`.

### 6.4 Refresh / Sync Schemas (AGGIORNATO)

| Origine          | Classe Attuale      | Nuovo Nome / Destinazione          | Note                                                 |
|------------------|---------------------|------------------------------------|------------------------------------------------------|
| api/v1/assets.py | RefreshItem         | FARefreshItem (refresh.py)         | Sezione FA Refresh                                   |
| api/v1/assets.py | BulkRefreshRequest  | FABulkRefreshRequest (refresh.py)  |                                                      |
| api/v1/assets.py | RefreshResult       | FARefreshResult (refresh.py)       |                                                      |
| api/v1/assets.py | BulkRefreshResponse | FABulkRefreshResponse (refresh.py) |                                                      |
| schemas/fx.py    | SyncResponseModel   | FXSyncResponse (refresh.py)        | Spostato per consolidare operazioni di aggiornamento |

(Conversion, Upsert, Delete FX rimangono in `fx.py`.)

### 6.5 Rinominazioni In-Place FX (AGGIORNATO)

Rinominare classi (rimozione suffisso `Model`, prefisso `FX`) tranne `FXSyncResponse` ora in refresh.

- `ProviderInfoModel` → `FXProviderInfo`
- `ProvidersResponseModel` → `FXProvidersResponse`
- `ConversionRequestModel` → `FXConversionRequest`
- `ConvertRequestModel` → `FXConvertRequest`
- `ConversionResultModel` → `FXConversionResult`
- `ConvertResponseModel` → `FXConvertResponse`
- `RateUpsertItemModel` → `FXUpsertItem`
- `UpsertRatesRequestModel` → `FXBulkUpsertRequest`
- `RateUpsertResultModel` → `FXUpsertResult`
- `UpsertRatesResponseModel` → `FXBulkUpsertResponse`
- `RateDeleteRequestModel` → `FXDeleteItem`
- `DeleteRatesRequestModel` → `FXBulkDeleteRequest`
- `RateDeleteResultModel` → `FXDeleteResult`
- `DeleteRatesResponseModel` → `FXBulkDeleteResponse`
- `PairSourceItemModel` → `FXPairSourceItem`
- `PairSourcesResponseModel` → `FXPairSourcesResponse`
- `CreatePairSourcesRequestModel` → `FXCreatePairSourcesRequest`
- `PairSourceResultModel` → `FXPairSourceResult`
- `CreatePairSourcesResponseModel` → `FXCreatePairSourcesResponse`

### 6.6 Aggiunta a `schemas/common.py`

```python
class DateRangeModel(BaseModel):
    """Base date range model (reusable across FA/FX)."""
    model_config = ConfigDict(extra="forbid")
    
    start: date = Field(..., description="Start date (inclusive)")
    end: Optional[date] = Field(None, description="End date (inclusive, optional = single day)")
```

[//]: # TODO: Pensare per il futuro e capire se si può fattorizzare in questa classe il controllo `end >= start` via validatore pydantic e riusarlo su tutto il software.

Scelta utente: aggiungere, nel commento dei file appena creati, e negli altri file di schemas, una breve descrizione del loro scopo e contenuto.

### 6.7 Docstring Obbligatorie (NUOVA SEZIONE)

- [ ] Inserire in ogni file `schemas/*.py` una docstring iniziale che includa:
    - Scopo del file.
    - Dominio (FA, FX, Common, Provider, Refresh/Sync).
    - Convenzioni di naming (prefisso FX/FA (Forex/Financial Asset)).
    - Nota retro‑compatibilità: non mantenuta in fase di refactoring.
    - Differenze strutturali FA vs FX (3 livelli vs 2 livelli) dove pertinente.

---

## 7. Sequenza Step-by-Step Implementazione (Aggiornata)

### Phase 1: Preparazione File e Common

- [ ] 7.1.1 Creare `provider.py`.
- [ ] 7.1.2 Creare `prices.py`.
- [ ] 7.1.3 Creare/estendere `refresh.py` includendo sezione FA Refresh + FX Sync.
- [ ] 7.1.4 Aggiornare `common.py` con `DateRangeModel` (validazione `end >= start`).
- [ ] 7.1.5 Docstring di scopo in tutti i file schema (inclusi già esistenti).

### Phase 2: Migrazione Provider Schemas

- [ ] 7.2.x (come versione precedente) + docstring provider.

### Phase 3: Migrazione Price Schemas

- [ ] 7.3.x (come versione precedente) + rimozione `PriceQueryResult` + docstring prices.

### Phase 4: Migrazione Refresh & Sync Schemas

- [ ] 7.4.1 Spostare classi FA Refresh.
- [ ] 7.4.2 Spostare `FXSyncResponse` da `fx.py` a `refresh.py` con docstring sezione FX Sync.
- [ ] 7.4.3 Aggiornare endpoint FX che usano `SyncResponseModel` → `FXSyncResponse` (da nuovo path).
- [ ] 7.4.4 Aggiornare import endpoint FA Refresh.
- [ ] 7.4.5 Verifica nessuna definizione pydantic rimasta inline in `api/v1`.
- [ ] 7.4.6 Test incrementale (services).

### Phase 5: Rinominazioni FX In-Place

- [ ] 7.5.1 Rinominare classi FX rimanenti (`RateUpsertItemModel` etc.).
- [ ] 7.5.2 Aggiornare import `api/v1/fx.py`.
- [ ] 7.5.3 Docstring `fx.py` aggiornata (senza sezione sync).
- [ ] 7.5.4 Test FX.

### Phase 6: Aggiornamento Test Scripts

- [ ] 7.6.1 Grep vecchi nomi.
- [ ] 7.6.2 Aggiornare test asset source.
- [ ] 7.6.3 Aggiornare test FX (se presenti).
- [ ] 7.6.4 Test completo services.

### Phase 7: Cleanup & Export

- [ ] 7.7.1 Rimuovere duplicati da `api/v1/assets.py` e `api/v1/fx.py`.
- [ ] 7.7.2 Controllo import inutilizzati.
- [ ] 7.7.3 Aggiornare `schemas/__init__.py` (includere nuovi moduli + FXSyncResponse da refresh).
- [ ] 7.7.4 Grep finale per confermare eliminazione `PriceQueryResult`, `ProviderAssignmentItem`, `SyncResponseModel` (vecchio nome).
- [ ] 7.7.5 Test finale combinato (utils, services, db).

### Phase 8: Documentazione

- [ ] 7.8.1 Aggiornare `api-development-guide.md` (nuova organizzazione, docstring guidance, differenze FA vs FX, file refresh consolidato).
- [ ] 7.8.2 Aggiornare `database-schema.md` (colonna volume + nota refactoring, nessuna retro‑compatibilità necessaria).
- [ ] 7.8.3 Aggiornare `FEATURE_COVERAGE_REPORT.md` (stato refactoring schema).
- [ ] 7.8.4 Aggiornare `REMEDIATION_PLAN.md` (spuntare passi) + aggiungere sezione "Schema Consolidation Completed".

### Phase 9: Verifica Endpoint Puliti

- [ ] 7.9.1 Grep pydantic pattern in `api/v1` (regex `class .*\(BaseModel\)`).
- [ ] 7.9.2 Se presenti residui: spostamento immediato in file schema + rimozione.
- [ ] 7.9.3 Conferma finale (log) "No inline Pydantic models in api/v1".

---

## 8. Test & Validazione (Aggiornato)

### 8.1 Incrementali

- [ ] Provider, Prices, Refresh+Sync, FX rename, Test Scripts.

### 8.2 Completi

- [ ] utils all
- [ ] services all
- [ ] db all
- [ ] Smoke API (6 endpoint) + `POST /fx/sync/bulk` usando nuovo import.

### 8.3 Import

- [ ] Nessun ciclo import.
- [ ] api/v1 importa solo da schemas.
- [ ] schemas non importa da api/.

### 8.4 Docstring Presence

- [ ] Verifica ogni file schema ha docstring e menziona naming FX/FA.

---

## 9. Rischi & Mitigazioni (Aggiornato)

| Rischio                            | Probabilità | Impatto | Mitigazione                                               |
|------------------------------------|-------------|---------|-----------------------------------------------------------|
| Cicli import                       | Media       | Alto    | Docstring + separazione rigorosa, test import sequenziale |
| Test rotti rename/sposta           | Alta        | Medio   | Esecuzione incrementale per fase                          |
| Definizioni inline residue         | Media       | Medio   | Grep regex prima del cleanup finale                       |
| Confusione refresh vs sync         | Media       | Medio   | Docstring file refresh + sezioni FA / FX separate         |
| Perdita storica modelli rimossi    | Bassa       | Basso   | Changelog interno (FEATURE_COVERAGE_REPORT)               |
| Volume non propagato correttamente | Media       | Alto    | Test 1.1 + log diagnostico                                |

---

## 10. Output Attesi al Termine (Aggiornato)

### Struttura Finale Schema

```
backend/app/schemas/
  ├── __init__.py (exports completi)
  ├── common.py (DateRangeModel, BackwardFillInfo)
  ├── assets.py (PricePointModel, HistoricalDataModel, InterestRatePeriod, ScheduledInvestment*)
  ├── provider.py (FAProviderInfo, FXProviderInfo, FAProviderAssignment, FA/FXBulkAssign/Remove)
  ├── prices.py (FAUpsertItem, FAUpsert, FABulkUpsert/Delete, FAGetPricesResponse)
  ├── refresh.py (FARefreshItem, FABulkRefresh*, FXSyncResponse)
  └── fx.py (FXUpsertItem, FXBulkUpsert/Delete, FXConversion*, FXPairSource*)
```

### Metriche di Successo

- ✅ Eliminato `PriceQueryResult`.
- ✅ Eliminato `ProviderAssignmentItem`.
- ✅ Spostato `FXSyncResponse` in `refresh.py`.
- ✅ Tutte le classi FX senza suffisso `Model`.
- ✅ Convenzione naming FX/FA applicata.
- ✅ Nessuna definizione Pydantic inline in `api/v1`.
- ✅ Test verdi (utils + services + db).
- ✅ Docstring presenti e coerenti.
- ✅ Documentazione aggiornata.
- ✅ Nessun ciclo import.

### Checklist Quality Gates (Aggiornata)

- [ ] Build & Import Pass.
- [ ] Lint Pass (imports puliti).
- [ ] Unit test pass (services + utils + db).
- [ ] API smoke test pass.
- [ ] Docstring presenti in ogni schema file.
- [ ] Documentazione coerente (no riferimenti a classi eliminate).
- [ ] Grep globale clean (vecchi nomi rimossi).
- [ ] Log finale: "Schema consolidation completed".

---

Fine checklist implementazione – pronta per esecuzione step-by-step aggiornata.
