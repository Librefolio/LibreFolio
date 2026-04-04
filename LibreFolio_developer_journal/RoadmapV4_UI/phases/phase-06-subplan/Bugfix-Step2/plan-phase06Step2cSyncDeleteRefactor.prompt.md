# Step 2c — Asset Sync Modal + Bulk Delete + Backend Convergence + Refactoring

**Obiettivo**: Creare `AssetSyncModal.svelte` (pattern `FxSyncModal`), migliorare la bulk delete con `ConfirmModal` + lista items, evolvere `FARefreshResult` nel backend per allinearla a `FXSyncPairResult`, creare un componente padre generico `SyncModalBase.svelte` con specializzazioni FX/Asset, rinominare `fxSync.ts` → `providerHelpers.ts`, fattorizzare layout responsive e utility sync in helper condivisi.

**Durata stimata**: ~1.5 giorni

---

## Step A–F — Prima tranche ✅ COMPLETATA

- **A**: `SyncStatus` enum condiviso, `FARefreshResult` arricchito, `FXSyncPairResult.errors`, test migrati, API client rigenerato
- **B**: `SyncModalBase.svelte`, `FxSyncModal` wrapper, `AssetSyncModal` wrapper
- **C**: Collegamento modali in `assets/+page.svelte`, sync via modale
- **D**: Bulk delete con `ConfirmModal` + lista nomi
- **E**: `syncHelpers.ts`, `providerHelpers.ts` (rinomina), `responsiveLayout.svelte.ts`
- **F**: 6 chiavi i18n (EN/IT/FR/ES)

---

## Step G — Fix Post-Review — ✅ COMPLETATO

### Riepilogo Implementazione

| Sub-step | Status | Note |
|----------|--------|------|
| **G1** | ✅ | Pipeline 3-fasi: PREPARE (batch queries) → FETCH (parallel, no DB) → PERSIST (per-task session). Fix "transaction closed". |
| **G2** | ✅ | FX FAILED: `message=None`, errore solo in `errors[]`. Chain PARTIAL: `errors[]` da leg_errors. |
| **G3** | ~~SCARTATO~~ | |
| **G4** | ✅ | `getProviderIconUrl` esteso con asset provider cache (`ensureAssetProvidersCached()`). |
| **G5** | ✅ | `ConfirmModal`: prop `description` + CSS. Chiavi i18n `confirmQuestion`/`confirmWarning` (4 lingue). |
| **G6** | ✅ | `ConfirmModal`: prop `results` con ✅/❌. Toast FX con count rate. Bulk delete mostra per-item. |
| **G7** | ✅ | `FAAssetDeleteResult`: `display_name` + `error_code` ("HAS_TRANSACTIONS"/"NOT_FOUND"). |
| **G8** | ✅ | TODO_FUTURI: nota Phase 7 link transazioni in delete modal. |
| **G9** | ✅ | `front-utility.all.name` → "All Frontend Utility Tests". |

### Fix aggiuntivi post-review

- **Currency fallback**: rimosso `"USD"` hardcoded → usa `asset.currency` come fallback (semanticamente corretto).
- **Asset provider icon cache**: `providerHelpers.ts` ora cerca icone in FX providers **e** asset providers (via `ensureAssetProvidersCached()`).
- **Test rafforzati**: `test_asset_source_refresh.py` passa da 1 smoke test a 7 test: single status, multi-asset concurrent (5 asset), SKIPPED, FAILED, mixed, currency fallback.

### Nota su crypto (BTC/ETH): 1↓ 1Δ

Bitcoin ed Ethereum restituiscono solo 1 punto (current value) perché:
- yfinance fornisce la cronologia per crypto ma il `db populate` potrebbe non configurare correttamente l'identifier o le date
- Lo status PARTIAL ("Current value only") è corretto — il provider funziona, ma la history non è disponibile per quell'identifier

### G1. Rearchitettura `bulk_refresh_prices` → pipeline 3-fasi (pattern FX)

#### Analisi comparativa delle due architetture

##### FX `sync_pairs_bulk` — Pipeline 3-fasi

```
Phase 1 — PREPARE (shared session, 1 query)
├── SELECT * FROM fx_conversion_route ORDER BY priority
├── Group legs by provider: {ECB: [EUR,GBP,CHF], FED: [USD,JPY]}
└── Create asyncio.Event per-leg

Phase 2 — FETCH (no DB, parallel per-provider)
├── ECB.fetch_rates(date_range, [EUR,GBP,CHF])  ← 1 call, N currencies
├── FED.fetch_rates(date_range, [USD,JPY])       ← 1 call, N currencies
├── Populate leg_rates dict
└── Signal Events

Phase 3 — PERSIST (per-task session, parallel)
├── _process_route("EUR-USD"):
│   └── async with AsyncSession(engine) as s: upsert+commit
├── _process_route("CHF-JPY"):
│   └── async with AsyncSession(engine) as s: upsert+commit
└── (N route coroutines, all parallel, each its own session)
```

**Proprietà chiave**: FX providers sono **batch-capable** (`fetch_rates` accetta N currencies in 1 call). Raggruppare per provider è un'ottimizzazione enorme: 14 coppie → 4 chiamate API (una per banca centrale).

##### Asset attuale — Monolitico per-item (BROKEN)

```
Per ogni asset (asyncio.gather, STESSA session!):
├── READ: get_asset_provider(session)        ← concurrent read
├── READ: select(Asset).where(id=N)(session) ← concurrent read
├── FETCH: prov.get_history_value()          ← network OK
├── WRITE: bulk_upsert_prices(session)       ← 💥 concurrent commit
└── WRITE: session.add(assignment)+commit()  ← 💥 concurrent commit
```

**Problema**: N task condividono 1 session → commit concorrenti → "This transaction is closed".

##### Differenza fondamentale nelle API dei provider

| Aspetto | FX Provider (`FXRateProvider`) | Asset Provider (`AssetSourceProvider`) |
|---------|-------------------------------|---------------------------------------|
| **Batch** | `fetch_rates(range, [CUR1,CUR2,...])` → 1 call, N currencies | `get_history_value(identifier, ...)` → 1 call, 1 asset |
| **Grouping** | Per provider (ECB serve 10 pair in 1 call) | Impossibile (ogni asset ha identifier diverso) |
| **Chain** | Multi-step (EUR→GBP→PLN via ECB+BOE) | Singolo provider per asset |
| **Config** | Route con priority + steps JSON | Assignment 1:1 asset→provider |

Asset providers non sono batch-capable: yfinance per AAPL e yfinance per MSFT richiedono 2 chiamate separate (identifier diverso). Il raggruppamento per-provider non dà beneficio API.

#### Migrazione proposta: pipeline 3-fasi per Asset

Nonostante le differenze API, la **separazione in 3 fasi è il fix architetturale corretto**:

```
Phase 1 — PREPARE (shared session, 2 batch queries)
├── SELECT * FROM asset_provider_assignment WHERE asset_id IN (...)
├── SELECT id, display_name, currency FROM asset WHERE id IN (...)
├── Build prepared_items dict: {asset_id → {assignment, asset, provider_instance, params}}
└── Filter: skip assets senza provider (→ SKIPPED result immediato)

Phase 2 — FETCH (no DB, parallel con semaphore)
├── Per ogni asset con provider:
│   ├── async with sem:
│   │   ├── prov.get_history_value(identifier, params, start, end)
│   │   └── prov.get_current_value(identifier, params)
│   └── Store in fetch_results: {asset_id → {prices: [...], source: "..."}}
└── Errori network → store in fetch_errors: {asset_id → str}

Phase 3 — PERSIST (per-task session, parallel)
├── Per ogni asset con dati fetchati:
│   └── async with AsyncSession(engine) as s:
│       ├── bulk_upsert_prices([upsert_obj], s)
│       ├── assignment.last_fetch_at = utcnow(); s.add(); s.commit()
│       └── → FARefreshResult con status/elapsed_ms/etc
└── Errori DB isolati per-task, non corrompono le altre
```

**Benefici rispetto all'attuale**:
1. **Correttezza**: nessun commit concorrente sulla stessa session
2. **Performance Phase 1**: 2 batch query (IN clause) invece di N query sequenziali
3. **Isolamento errori**: un DB error su asset 3 non blocca asset 4-7
4. **Chiarezza**: separazione netta read/fetch/write

#### Orchestratore generico: analisi fattibilità

| Fase | FX | Asset | Generalizzabile? |
|------|-----|-------|-------------------|
| **Phase 1** | 1 query route | 2 query batch (assignment + asset) | ❌ Query diverse, schema diversi |
| **Phase 2** | Raggruppato per provider, Event-based | Per-item con semaphore | ❌ Strategie fetch incompatibili |
| **Phase 3** | Chain computation + upsert FxRate | Upsert PriceHistory + update assignment | ❌ Modelli DB diversi |
| **Result** | `FXSyncPairResult` | `FARefreshResult` | ❌ Schema diversi |
| **Summary** | `FXSyncBulkResponse` | `FABulkRefreshResponse` | ⚠️ Simili ma campi diversi |

**Conclusione**: le 3 fasi sono le stesse *concettualmente* (prepare → fetch → persist) ma l'implementazione di ogni fase è completamente diversa. Un orchestratore generico richiederebbe 4+ callback tipizzati + generics complessi → più codice e complessità del benefit.

**Decisione**: applicare lo stesso **design pattern** (3-fasi con session separation) ma con implementazione dedicata. Il pattern è una convenzione documentata, non una classe astratta.

---

### G2. FX `errors` nelle catene — eliminare ridondanza

**Fix**:
- **FAILED (exception)**: `errors = [str(e)]`, `message = None`
- **FAILED (no route)**: `errors = ["No route configuration found for {slug}"]`, `message = None`
- **PARTIAL catena con leg errors**: `errors` popolato da `leg_errors` (stringhe da `chain_leg_details[].error`), `message` = nota informativa
- **OK/PARTIAL senza errori**: `errors = []`, `message` = nota opzionale

---

### ~~G3. Bottone Sync All spin~~ → SCARTATO

La modale fornisce feedback sufficiente.

---

### G4. Provider icon nel risultato asset sync

In `AssetSyncModal.svelte` `resultRow`:
- `getProviderIconUrl(pr.provider_used)` per cercare l'icona
- Se trovata: `<img>` come in FX
- Se assente: text badge (comportamento attuale)

---

### G5. Delete singola — accapo (Opzione A: due props)

`ConfirmModal`: aggiungere prop `description?: string` renderizzata sotto `message`.

Chiavi i18n (4 lingue):
- `assets.delete.confirmQuestion` → `Delete "{name}"?`
- `assets.delete.confirmWarning` → `Provider assignments and price history will be removed. ⚠️`

---

### G6. Delete — risultati sempre visibili nella modale + toast tradotti

#### Arricchimento `ConfirmModal`

Aggiungere prop **sempre attiva** `results?: {label: string; success: boolean; detail?: string}[]`.
Quando `results` è popolato (dopo l'azione):
- Il body della modale mostra la lista ✅/❌ al posto di message+items
- Il bottone conferma diventa "Close"
- Non serve disattivare: se non serve, non si passa la prop

#### Bulk delete asset

Dopo `confirmBulkDeleteAssets()`:
- Popola `results` dalla response backend
- Modale mostra: `✅ Apple Inc. — deleted` / `❌ Ethereum — has existing transactions`
- Toast riassuntivo solo alla chiusura

#### Delete singola asset

Toast con dettaglio tradotto:
- Successo: `"{name}" deleted` (invariato)
- Fallimento: chiave `assets.delete.hasTransactions` → `Cannot delete "{name}": has existing transactions`

#### FX delete — count rate nel toast (tradotto)

**Singola**: dopo delete FX, toast con count: `"{pair}" deleted ({count} rates removed)`
**Bulk**: modale mostra per-coppia: `✅ EUR/USD — deleted (62 rates)` / `❌ CHF/JPY — error`

Chiave i18n `fx.delete.toastOk` → `{pair} deleted ({count} rates removed)` (4 lingue)

---

### G7. Delete singola — backend compatto

Aggiungere a `FAAssetDeleteResult`:
```python
display_name: Optional[str] = None   # nome asset
error_code: Optional[str] = None     # "HAS_TRANSACTIONS" | "NOT_FOUND" | None
```

Il service popola `display_name` da `asset.display_name` (già in memoria, zero query extra) e `error_code` strutturato.
Il frontend usa `error_code` → chiave i18n con `{name: display_name}`.

---

### G8. TODO_FUTURI — Link transazioni

Nota da aggiungere a `TODO_FUTURI.md` per Phase 7. che specifica che quando la pagina transazioni sarà implementata, bisognerà linkare le transazioni collegate a un asset direttamente nella modale di delete (es. "This asset has 3 transactions: View → /transactions?asset_id=123") e nella pagina dettaglio asset.

---

### G9. dev.py test count fix

Rinominare `front-utility.all.name`: `"All Utility Tests"` → `"All Frontend Utility Tests"`.

---

## Ordine di Esecuzione Step G

```
G1 (rearchitettura 3-fasi bulk_refresh_prices — CRITICO)
 │
G9 (dev.py fix — 1 riga)
 │
G2 (FX errors: eliminare ridondanza message/errors)
 │
G7 (backend: display_name + error_code su FAAssetDeleteResult)
 │   └── ./dev.py api sync
 │
G4 (provider icon in AssetSyncModal)
 │
G5 (ConfirmModal description prop + i18n accapo)
 │
G6 (ConfirmModal results prop + toast FX count + toast asset tradotto)
 │
G8 (TODO_FUTURI nota)
```

---


## Verifiche Finali

- [x] `npm run build` — senza errori ✅
- [x] `svelte-check` — 0 errors, 0 warnings ✅
- [x] `./dev.py test all` — **10/10** ✅ (confermato dall'utente)
- [x] Asset sync bulk (7 asset) — 5 OK, 2 PARTIAL (crypto = current value only) ✅
- [x] FX sync — funziona come prima ✅
- [x] Delete singola asset con transazioni — toast con nome tradotto ✅
- [x] Delete bulk asset mix successo/fallimento — modale mostra dettaglio per-item ✅
- [x] FX delete singola — toast con count rate ✅
- [x] FX delete bulk — modale mostra dettaglio per-coppia ✅
- [x] Test asset-source-refresh: 7/7 passati (da 1 smoke → 7 test robusti) ✅
- [x] Provider icon nella sync modal — ora carica icone asset provider ✅
- [x] Currency fallback — usa `asset.currency` invece di USD hardcoded ✅

### Fix post-review (Round 2)

| Fix | Descrizione |
|-----|-------------|
| **providerHelpers separation** | `getProviderIconUrl` (FX only) e `getAssetProviderIconUrl` (asset only) — registri separati per evitare collisioni |
| **FX delete accapo** | `deletePairQuestion` + `deletePairWarning` (come fatto per asset) — sia single che bulk |
| **Provider icon in tabella** | `provider_code` aggiunto a `FAinfoResponse` + `FAAssetMetadataResponse` backend; tabella usa `assetProviderBadgeHtml()` per icona/testo |
| **db populate** | 2 asset senza transazioni (NVIDIA, Amundi MSCI World) per testare delete success |
| **Crypto PARTIAL** | Confermato come test futuro — necessita pagina dettaglio asset (Phase 6 Step 4) |

