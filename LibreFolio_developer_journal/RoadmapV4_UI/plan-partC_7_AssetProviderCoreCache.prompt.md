# Plan: Core-level Cache + Thread Isolation per Asset Providers (v2)

Layer centralizzato di cache e isolamento thread in `asset_source.py` per **tutti** i provider, senza eccezioni. Il core intercetta ogni chiamata ai metodi dei provider (`get_history_value`, `get_current_value`, `fetch_asset_metadata`, `search`) e:
1. Controlla la cache core (per history, current, metadata)
2. Esegue la chiamata provider in un thread dedicato con event loop proprio, così un plugin mal scritto non può bloccare l'event loop principale
3. Popola la cache core al ritorno

I plugin mantengono le proprie cache interne per sotto-operazioni (es. currency discovery di yfinance), ma tutta la logica di cache pricing/metadata e thread safety è responsabilità del core.

---

## Operazioni che toccano la rete

| Metodo provider | Cache core? | TTL | Note |
|---|---|---|---|
| `get_history_value()` | ✅ Smart range | 15 min | Per-date, gap filling intelligente |
| `get_current_value()` | ✅ | 2 min | Polling frontend ogni 30s |
| `fetch_asset_metadata()` | ✅ | 30 min | Refresh esplicito dall'utente |
| `search()` | ✅ 2 livelli | 24h items / 15min query | Layer 1: items per identifiers, Layer 2: query→results |

Tutte le operazioni passano per il thread isolation. La `search()` ha una cache a due livelli: items individuali (24h) per lookup fuzzy istantaneo + mapping query esatta (15min) per evitare ri-chiamate.

---

## Step 1 — Thread Isolation: `_run_provider_in_thread()`

**File:** `backend/app/services/asset_source.py` (modulo-level, nuova funzione utility)

Creare un wrapper che esegue **qualsiasi** coroutine provider in un thread dedicato con event loop proprio:

```python
async def _run_provider_in_thread(coro_factory, *, timeout: float = 60.0):
    """
    Run a provider coroutine in a dedicated thread with its own event loop.
    
    Protects the main event loop from blocking provider implementations.
    Even a well-written async provider (httpx) works fine — it just uses
    the thread's event loop instead of the main one.
    
    A badly-written provider that does `requests.get()` directly in an
    async def will block the thread, NOT the main event loop.
    
    Args:
        coro_factory: Zero-arg callable that returns the coroutine to run.
                     Example: lambda: provider.get_current_value(id, type, params)
        timeout: Maximum time to wait (seconds). Default 60s.
    
    Returns:
        Result of the coroutine.
    
    Raises:
        asyncio.TimeoutError: If provider takes longer than timeout.
        Any exception raised by the provider.
    """
    def _sync_runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro_factory())
        finally:
            loop.close()
    
    return await asyncio.wait_for(
        asyncio.to_thread(_sync_runner),
        timeout=timeout,
    )
```

**Impatto:** Tutti i callsite che oggi fanno `await provider.method()` passano a `await _run_provider_in_thread(lambda: provider.method())`.

---

## Step 2 — Cache Core: struttura dati

**File:** `backend/app/services/asset_source.py` (modulo-level)

```python
# Core caches — automatic TTL expiration via theine timer wheel
_asset_history_cache = get_ttl_cache("asset_history_fetch", maxsize=500, ttl=900)     # 15 min
_asset_current_cache = get_ttl_cache("asset_current_fetch", maxsize=300, ttl=120)     # 2 min
_asset_metadata_cache = get_ttl_cache("asset_metadata_fetch", maxsize=200, ttl=1800)  # 30 min
_search_result_cache = get_ttl_cache("search_results", maxsize=5000, ttl=86400)       # 24h — individual items
_search_query_cache = get_ttl_cache("search_queries", maxsize=500, ttl=900)           # 15 min — query→results
```

### History cache — smart range con per-date granularity

La chiave è `(provider_code, identifier, identifier_type_str)`.
Il valore è un `dict` con struttura `{"dates": {date_iso: price_point_dict, ...}, "events": [event_dict, ...]}`.

**Algoritmo su fetch per range [start, end]:**

```
1. cache_key = (provider_code, identifier, str(identifier_type))
2. cached_entry, ok = _asset_history_cache.get(cache_key)
3. if ok:
     cached_dates = cached_entry["dates"]
     - Calcola quali date in [start..end] sono assenti (gap)
     - Se nessun gap → return dati dalla cache
     - Se ci sono gap → fetch_start = min(gap), fetch_end = max(gap)
       (rigenera anche i punti intermedi già in cache, reset TTL unico)
4. else:
     - fetch_start = start, fetch_end = end
5. Chiama provider per [fetch_start, fetch_end] tramite _run_provider_in_thread()
6. Merge risultato nella cached_dates dict + events
7. Re-set in cache (reset TTL per l'intera entry)
8. Return solo le date in [start..end]
```

**Nota gap detection:** Per evitare iterazioni giornaliere inutili, confrontare il range richiesto con le date min/max presenti in cache. Se `cache_min > start` o `cache_max < end`, o se la densità cached è sotto una soglia (es. mancano >20% dei giorni lavorativi attesi), fare fetch dell'intero intervallo scoperto `[min(missing), max(missing)]`. Questo evita chiamate frammentate al provider.

### Current cache

Chiave: `(provider_code, identifier, identifier_type_str)` → valore: `FACurrentValue` serializzato.

### Metadata cache

Chiave: `(provider_code, identifier, identifier_type_str)` → valore: `FAAssetPatchItem` serializzato (o None).

---

## Step 3 — Integrare in `_fetch_single()` dentro `bulk_refresh_prices()`

**File:** `backend/app/services/asset_source.py` (~riga 1831)

La funzione `_fetch_single()` oggi:
1. Chiama `prov.get_history_value()` direttamente con `await`
2. Chiama `prov.get_current_value()` direttamente con `await`

Dopo la modifica:
1. **History**: applica l'algoritmo smart range (Step 2) con `_run_provider_in_thread()`
2. **Current**: check `_asset_current_cache` → se miss, `_run_provider_in_thread(lambda: prov.get_current_value(...))` → popola cache

---

## Step 4 — Search: thread isolation + cache a due livelli

**File:** `backend/app/services/asset_source.py` (~riga 3016)

La search ha due endpoint: uno bloccante (REST) e uno streaming (WebSocket). Entrambi devono beneficiare della cache e del thread isolation.

### Cache Layer 1: Result Items (TTL 24h)

Cache per singolo risultato, keyed per `(provider_code, display_name_lower, tuple(identifiers))`.

Ogni volta che un provider restituisce risultati di ricerca, ogni item viene salvato individualmente:
```python
_search_result_cache = get_ttl_cache("search_results", maxsize=5000, ttl=86400)  # 24h
```

**Chiave:** `(provider_code, display_name.lower().strip(), frozenset(identifiers))` dove `identifiers` include tutti gli ID tornati (ticker, ISIN, UUID, ecc.).

**Lookup su nuova query:** scansionare le chiavi della cache con un `contains` fuzzy sulla query → ritorno immediato dei match. Questa è la risposta "istantanea" dalla cache.

### Cache Layer 2: Query→Results Mapping (TTL 15min)

Cache per la query esatta, così ricerche identiche ripetute in un breve intervallo non colpiscono i provider:
```python
_search_query_cache = get_ttl_cache("search_queries", maxsize=500, ttl=900)  # 15 min
```

**Chiave:** `(provider_code, query.lower().strip())`
**Valore:** `list[dict]` — i risultati completi del provider per quella query.

### Algoritmo search (unificato REST + WebSocket)

```
1. Costruire set provider_codes da interrogare
2. Per ogni provider, in parallelo:
   a. Cercare match nella Layer 2 (query esatta):
      - Se hit → ritornare subito quei risultati (REST: accumula, WS: invia)
      - Se miss → passare a step b
   b. Cercare match nella Layer 1 (contains fuzzy su chiavi):
      - Se trovati → ritornare subito come risultati "cached" (REST: accumula, WS: invia)
   c. In ogni caso, lanciare la search al provider via _run_provider_in_thread()
   d. Quando il provider risponde:
      - Per ogni item: se già in Layer 1 (stessa key) → reset TTL, skip
      - Per item nuovi → aggiungerli alla risposta (WS: invia, REST: accumula) + popola Layer 1
      - Popolare Layer 2 con (query, tutti i risultati)
3. Ritornare risultati aggregati
```

Questo garantisce:
- Query ripetuta entro 15min → risposta istantanea dalla Layer 2, nessuna chiamata provider
- Query diversa ma asset già visto → match da Layer 1 (istantaneo), poi provider conferma/aggiunge
- Query nuova → provider chiamati, risultati cachati per prossime ricerche

---

## Step 5 — Integrare in `refresh_assets_from_provider()` (cache metadata)

**File:** `backend/app/services/asset_source.py` (~riga 944)

Oggi:
```python
patch_item = await provider.fetch_asset_metadata(...)
```

Dopo:
```python
meta_cache_key = (provider_code, identifier, str(identifier_type))
cached_meta, meta_ok = _asset_metadata_cache.get(meta_cache_key)
if meta_ok:
    patch_item = cached_meta
else:
    patch_item = await _run_provider_in_thread(
        lambda: provider.fetch_asset_metadata(identifier, identifier_type, provider_params),
        timeout=30.0,
    )
    _asset_metadata_cache.set(meta_cache_key, patch_item)
```

---

## Step 6 — Integrare in `probe_provider_config()` (solo thread isolation, NO cache)

**File:** `backend/app/services/asset_source.py` (~riga 1348)

Le probe devono bypassare la cache (l'utente vuole testare la connessione reale al provider). Applicare solo thread isolation:

```python
value = await _run_provider_in_thread(
    lambda: provider.get_current_value(config.identifier, mapped_id_type, params),
    timeout=15.0,
)
```

(Analogamente per _probe_history e _probe_metadata.)

---

## Step 7 — Migrare i provider esistenti

### 7a. yahoo_finance.py
- **Rimuovere** `_current_value_cache` (riga 64) e relativi get/set → sostituita dalla cache core
- **Rimuovere** `_search_cache` (riga 58) → sostituita dalla cache core a due livelli
- **Rimuovere** tutti i `asyncio.to_thread()` interni → il core li esegue già in thread isolato
- **Tenere** `_currency_cache` (sotto-operazione interna: currency discovery per symbol, non è una operazione di pricing)
- I metodi diventano `async def` che chiamano direttamente la libreria sync (yfinance) senza wrapping — il core si occupa del thread

### 7b. justetf.py
- **Rimuovere** tutti i `asyncio.to_thread()` interni
- **Tenere** `_overview_cache`, `_chart_cache`, `_etf_list_cache` (sotto-operazioni interne per search/metadata)
- Semplificazione analoga a yahoo

### 7c. css_scraper.py
- Nessuna modifica necessaria — è già nativamente async (httpx). Il thread isolation del core lo esegue in thread comunque (overhead minimo, sicurezza massima).

### 7d. scheduled_investment.py
- Nessuna modifica — dati sintetici (CPU-bound). La cache core cachera il risultato per 15min, evitando ricalcoli ripetuti. Il thread isolation protegge nel caso di computazioni lunghe.

---

## Step 8 — Test: analisi impatto e aggiornamenti

### Test esistenti da aggiornare

| File test | Impatto | Azione |
|---|---|---|
| `test_utilities/test_cache_utils.py` | ❌ Nessuno | Le cache utils non cambiano — solo nuove istanze create. Nessuna modifica. |
| `test_api/test_assets_prices.py` | ⚠️ Medio | Il test `test_sync_prices_from_provider` chiama l'endpoint di sync. Con la cache core, un secondo sync identico entro 15min restituisce dati dalla cache. I test devono: (a) verificare che i contatori (points_fetched/changed) siano coerenti anche con cache; (b) eventualmente chiamare `clear_cache("asset_history_fetch")` tra test che richiedono dati freschi. |
| `test_e2e/test_search_to_prices.py` | ⚠️ Medio | Il flusso Search→Create→Assign→Refresh→Sync potrebbe vedere cache hit sulla search (Layer 2, 15min). Aggiungere cleanup cache tra step se necessario, o accettare che i risultati cached sono equivalenti. |
| `test_api/test_fx_sync.py` | ❌ Nessuno | FX ha già la propria cache (`_fx_fetch_cache`). Nessuna modifica necessaria. |

### Nuovi test da creare

**File:** `test_utilities/test_provider_core_cache.py` (nuovo)

1. **`test_run_provider_in_thread_blocking`**: Mock provider con `time.sleep(2)` → verifica che il main event loop non si blocca (misura elapsed time con `asyncio.gather` parallelo).

2. **`test_run_provider_in_thread_timeout`**: Mock provider che blocca 10s → timeout 3s → `TimeoutError`.

3. **`test_run_provider_in_thread_exception_propagation`**: Mock provider che lancia `AssetSourceError` → eccezione propagata correttamente al caller.

4. **`test_history_cache_full_hit`**: Popola cache con date [d1..d10], richiedi [d1..d10] → 0 chiamate provider.

5. **`test_history_cache_partial_gap`**: Cache con [d1,d2,d5,d6,d9,d10], richiedi [d1..d10] → provider chiamato per [d3..d8], cache aggiornata.

6. **`test_history_cache_full_miss`**: Cache vuota, richiedi [d1..d10] → provider chiamato per [d1..d10], cache popolata.

7. **`test_current_cache_hit`**: Set cache, richiedi → nessuna chiamata provider.

8. **`test_current_cache_miss_and_populate`**: Cache vuota → provider chiamato → cache popolata → seconda richiesta → cache hit.

9. **`test_metadata_cache_hit`**: Analoga a current.

10. **`test_search_layer2_exact_query_hit`**: Query "Apple" cached in Layer 2 → ritorno immediato senza provider.

11. **`test_search_layer1_fuzzy_match`**: Item "Apple Inc." in Layer 1, query "apple" → match fuzzy → ritorno istantaneo + provider chiamato in parallelo → nessun nuovo risultato → solo TTL reset.

12. **`test_search_new_results_added`**: Layer 1 ha "Apple Inc.", provider ritorna "Apple Inc." + "Apple Corp." → "Apple Corp." aggiunto a Layer 1, risposta include entrambi.

13. **`test_probe_bypasses_cache`**: Cache popolata → probe → provider sempre chiamato (no cache).

### Test da eseguire dopo implementazione

```bash
./dev.py test ...
```

---

## Step 9 — Fix log yfinance verbosi ✅

**File:** `backend/app/logging_config.py`

**Già implementato.** Aggiunto `yfinance` e `peewee` alla lista dei logger silenziati (livello WARNING). I messaggi verbosi (`get_raw_json()`, `Entering get()`, cookie/crumb negotiation, ecc.) non inquinano più la console — solo i warning/error di yfinance vengono mostrati.

---

## Step 10 — Documentazione

1. **Docstring `AssetSourceProvider`** → aggiungere sezione "Core Infrastructure":
   - "Il core esegue i vostri metodi in un thread dedicato — non dovete preoccuparvi di asyncio.to_thread()"
   - "Il core cachea automaticamente i risultati di get_history_value/get_current_value/fetch_asset_metadata/search"
   - "Se avete sotto-operazioni costose (es. currency discovery), usate le vostre cache interne"

2. **Knowledge base** → aggiornare `01_backend.md` con la sezione "Provider Core Cache & Thread Isolation"

---

## Considerazioni

1. **Overhead thread per provider nativamente async (css_scraper):** Minimo (~100μs per spawn thread + event loop). La sicurezza uniforme vale il costo. Se in futuro diventa un bottleneck misurabile, si può aggiungere un opt-in flag, ma oggi non serve.

2. **Deduplication in-flight:** Due sync concorrenti per lo stesso asset vedono entrambi cache miss. Nella v1 accettiamo il duplicato (la cache si popola al primo completamento, il secondo avrà hit). Se serve, in v2 si aggiunge un `dict[key, asyncio.Future]` per coalescere fetch concorrenti.

3. **Events nella history cache:** Gli events (dividendi, split) sono inclusi nella stessa entry della history cache come campo separato `"events"`. Un re-fetch della history rigenera anche gli events.

4. **Admin panel:** Le 5 cache (`asset_history_fetch`, `asset_current_fetch`, `asset_metadata_fetch`, `search_results`, `search_queries`) sono automaticamente visibili in `list_caches()` e pulibili via `clear_cache()` grazie al registry globale di `cache_utils.py`.

5. **Backward compatibility interfaccia:** L'interfaccia dei provider (metodi astratti) NON cambia. I provider sono ignari del wrapping thread — i loro `async def` vengono eseguiti in un event loop dedicato. Nessuna modifica all'interfaccia richiesta per plugin esterni.

6. **`asyncio.to_thread()` rimosso dai provider:** Dopo la migrazione, i provider interni (yahoo, justetf) possono semplificare enormemente il loro codice rimuovendo tutti i `asyncio.to_thread()` — il core si occupa di tutto.

---

## Collegamento

- Piano precedente: [C.6b — Fix post-test C.6](plan-partC_6b_PostTestFixes.prompt.md)
- Piano origine: [Part C — Currency Conversion](plan-partCCurrencyConversion.prompt.md)







