# LibreFolio - Ordine Step Suggerito

**Data Analisi**: 5 Novembre 2025  
**Stato Attuale**: Step 2 e Step 4 completati

---

## ✅ Stato Attuale - Aggiornamento 5 Nov 2025

### STEP 2 - Database Schema (Completato ✅)

- Database schema completo e migrazioni applicate
- Modelli definiti con tutti gli enum e constraint
- HOLD asset type e MANUAL valuation implementati
- Test completi e funzionanti
- Documentazione esaustiva
- `ensure_database_exists()` centralizzato
- **Test database isolation** implementato (3 Nov 2025)

### STEP 4 - FX Multi-Provider System (Completato ✅ - 5 Nov 2025)

**🎉 Completamento al 100%** - Sistema Production Ready

#### Implementazione Core

- ✅ **Abstract class + Factory Pattern**: FXRateProvider con 4 provider
- ✅ **4 Provider Centrali Banchi**: ECB (EUR), FED (USD), BOE (GBP), SNB (CHF)
- ✅ **Multi-base currency support**: Ready for future commercial APIs
- ✅ **Rate normalization**: Alphabetical ordering (base < quote) con inversion logic
- ✅ **Multi-unit currencies**: JPY, SEK, NOK, DKK gestiti correttamente (100 units = X)

#### Advanced Features

- ✅ **fx_currency_pair_sources table**: Auto-configuration system
- ✅ **Provider fallback logic**: Priority-based retry (priority 1 → 2 → 3...)
- ✅ **Inverse pairs support**: EUR/USD (ECB) + USD/EUR (FED) possono coesistere
- ✅ **Chunked deletion**: DELETE operations con strategy 500 IDs/batch
- ✅ **Numeric truncation system**: Previene false updates (Numeric 24,10 per FX rates)
- ✅ **Parallel queries**: API fetch + DB query in parallelo (~28% speedup)

#### API Endpoints (11 completi)

- ✅ GET /fx/currencies - List currencies by provider
- ✅ GET /fx/providers - List available providers
- ✅ GET /fx/pair-sources - List configurations
- ✅ POST /fx/pair-sources/bulk - Create/update configurations (atomic)
- ✅ DELETE /fx/pair-sources/bulk - Delete configurations
- ✅ POST /fx/sync/bulk - Sync rates (explicit provider + auto-config modes)
- ✅ POST /fx/convert/bulk - Convert currencies (single date + range support)
- ✅ POST /fx/rate-set/bulk - Manual rate insert/update
- ✅ DELETE /fx/rate-set/bulk - Delete rates by pair and date range

#### Test Coverage (45/45 - 100%)

- ✅ External: 28/28 (4 providers × 4 tests + 12 multi-unit tests)
- ✅ Database: 5/5 (create, validate, truncation, populate, fx-rates)
- ✅ Services: 1/1 (conversion logic con backward-fill)
- ✅ API: 11/11 (providers, pair-sources CRUD, sync, convert, delete)

#### Documentazione (5 guide complete)

- ✅ fx/api-reference.md (~650 linee, esempi cURL completi)
- ✅ fx-implementation.md (~300 linee, advanced features)
- ✅ testing-guide.md (aggiornato con 11/11 API tests)
- ✅ fx/provider-development.md (~280 linee, multi-base template)
- ✅ fx/providers.md (dettagli 4 provider)

#### Metriche Sviluppo

- **Fasi**: 7/7 (100%)
- **Task**: 122/122 (100%)
- **Tempo**: ~18 ore
- **Codice**: ~3500 linee backend
- **Docs**: ~15000 parole

---

## ✅ Cosa Abbiamo Ora (Post-Step 4)

- Database schema completo e migrazioni applicate
- Modelli definiti con tutti gli enum e constraint
- HOLD asset type e MANUAL valuation implementati
- CHECK constraint su fx_rates (base < quote)
- Test completi e funzionanti
- Documentazione esaustiva
- `ensure_database_exists()` centralizzato
- **Test database isolation** implementato (3 Nov 2025):
    - Flag `--test` / `LIBREFOLIO_TEST_MODE` per modalità test
    - `./dev.sh server:test` per server in modalità test (porta 8001, test_app.db)
    - Test automaticamente usano test_app.db, non app.db
    - Lazy engine initialization per rispettare override ambiente

---

## 📊 Analisi delle Dipendenze tra Step (Aggiornato 5 Nov 2025)

### ✅ STEP 04: FX Rates - COMPLETATO

**Cosa fornisce al sistema:**

- ✅ Service `fx.ensure_rates_multi_source()` - Fetch rates da 4 provider
- ✅ Service `fx.convert_bulk()` - Conversione multi-currency con backward-fill
- ✅ Multi-provider architecture pronta per estensioni
- ✅ Auto-configuration system per scelta automatica provider
- ✅ Fallback logic per resilienza
- ✅ 11 endpoint API completi e testati
- ✅ Documentazione completa

**Impatto sugli step successivi:**

- ✅ **Step 5 (Plugins)**: Può usare FX per convertire prezzi multi-valuta
- ✅ **Step 6 (Analysis)**: Può convertire tutto a base currency per aggregazioni
- ✅ **Step 3 (Transactions)**: Può validare importi multi-valuta

---

### STEP 03: Transactions & Cash

**Dipendenze:**

- ✅ Schema DB (completato)
- ✅ FX Service (completato - Step 4) ← **NUOVO**
- ❌ Analysis service per oversell guard (Step 6 raccomandato)
- ❌ Endpoint API non ancora implementati

**Cosa richiede:**

- Implementare endpoints REST API (POST /api/v1/transactions/*)
- Implementare service layer per business logic
- Implementare **oversell guard** (calcolo runtime inventory)
- Implementare auto-generazione cash movements

**⚠️ Problemi:**

- Richiede calcolo `held_qty_before` per oversell guard
- Questa logica è **molto simile** al FIFO matching dello Step 6
- **Rischio duplicazione**: implementazione parziale ora, poi rifatta completa in Step 6

---

### ✅ STEP 04: FX Rates (COMPLETATO 5 Nov 2025)

**Stato:** 🎉 **100% COMPLETATO** 🎉

**Cosa è stato implementato:**

- ✅ Multi-provider architecture con 4 centrali bancarie
- ✅ Abstract class + Factory pattern
- ✅ Service completo con HTTP client async (httpx)
- ✅ Conversione multi-valuta con backward-fill
- ✅ Auto-configuration system (fx_currency_pair_sources)
- ✅ Provider fallback logic (priority-based)
- ✅ 11 endpoint API completi
- ✅ 45/45 test passano (100%)
- ✅ Documentazione completa (5 guide)

**Risultato:**

- Sistema production-ready
- Fondamentale per Step 5, 6, 7
- Nessuna dipendenza bloccante rimanente

---

### STEP 05: Plugins (yfinance, CSS scraper, synthetic_yield)

**Dipendenze:**

- ✅ Schema DB (completato)
- ❌ Service layer
- ❌ HTTP client

**Cosa richiede:**

- Plugin system (registry, base classes, TypedDicts)
- yfinance integration
- CSS scraper (BeautifulSoup4)
- **synthetic_yield** per scheduled-yield assets (loans)

**✅ Vantaggi:**

- Relativamente **indipendente**
- synthetic_yield è **critico** per valutare loan assets
- Può essere fatto **prima o in parallelo**
- Necessario per Step 6 (valutazione asset nel tempo)

---

### STEP 06: Runtime Analysis (FIFO completo)

**Dipendenze:**

- ✅ Schema DB (completato)
- ✅ Transazioni esistenti nel DB (possono essere di test)
- ✅ Price history (richiede plugin system - Step 5)
- ✅ FX rates (richiede Step 4)

**Cosa richiede:**

- **FIFO matching completo** (BUY lots queue)
- Calcolo P/L realizzato
- Calcolo serie Invested/Market
- ROI metrics (Simple ROI, DW-ROI)
- Supporto scheduled-yield valuation

**💡 Nota importante:**

- Implementa la **stessa logica** necessaria per oversell guard di Step 3
- Una volta fatto, Step 3 può **riusare** questa logica
- Evita duplicazione di codice

---

### STEP 07: Portfolio Aggregations

**Dipendenze:**

- ✅ Tutti gli step precedenti
- ✅ Analysis service (Step 6)
- ✅ FX conversion (Step 4)

**Cosa richiede:**

- Aggregazioni portfolio-level
- Conversione a base currency
- Breakdown per broker/asset/asset_type

---

## 🎯 Ordine Suggerito

### ❌ Ordine Originale (Problematico)

```
✅ Step 2: DB Schema
→ Step 3: Transactions (oversell parziale)
→ Step 4: FX Rates
→ Step 5: Plugins
→ Step 6: Analysis (FIFO completo) ← Duplicazione!
→ Step 7: Portfolio
```

**Problema principale:**

- Step 3 richiede calcolo inventory per oversell guard
- Step 6 richiede FIFO matching completo (stessa cosa ma più completa)
- **Risultato**: implementi due volte la stessa logica!

---

### ✅ Ordine Suggerito (Aggiornato 5 Nov 2025)

```
✅ Step 2: DB Schema (COMPLETATO - 29 Ott 2025)
✅ Step 4: FX Rates (COMPLETATO - 5 Nov 2025)

→ Step 5: Plugins                     [PROSSIMO - yfinance, CSS scraper, synthetic_yield]
→ Step 3: Transactions & Cash         
→ Step 6: Runtime Analysis            [FIFO completo + scheduled-yield support]
→ Step 7: Portfolio Aggregations      [Usa tutto: FX, Plugins, Analysis]
→ Step 8+: Scheduler, Settings, Frontend, etc.
```

---

## 💡 Motivazioni del Nuovo Ordine

### 1. FX Rates Prima (Step 4 → Step 5)

**Perché:**

- ✅ Fondamentale per quasi tutto (analysis, portfolio, multi-currency)
- ✅ Completamente indipendente dalle transazioni
- ✅ Relativamente semplice da implementare
- ✅ Può essere testato in isolamento
- ✅ Necessario per Step 6 (conversion a base currency)

**Cosa fornisce:**

- Service `fx.ensure_rates(date_range, currencies)`
- Service `fx.convert(amount, from_cur, to_cur, date)`
- Forward-fill per date mancanti
- Endpoint `/api/v1/fx/sync/bulk`

---

### 2. Plugins Prima di Analysis (Step 5 → Step 6)

**Perché:**

- ✅ Analysis richiede valutazioni asset nel tempo
- ✅ Plugin system fornisce prezzi (market + synthetic)
- ✅ synthetic_yield è critico per loan assets
- ✅ Indipendente dalle transazioni

**Cosa fornisce:**

- yfinance: prezzi real-time per stocks/ETFs
- synthetic_yield: valutazione loans con interest schedule
- CSS scraper: backup per asset senza API
- Infrastruttura plugin riusabile

---

### 3. Analysis Prima di Transactions (Step 6 → Step 3)

**Perché (chiave!):**

**Step 6 implementa FIFO completo:**

```python
# services/analysis.py
def get_held_quantity_at_date(asset_id, broker_id, date) -> Decimal:
    """
    Calcola quantità detenuta a una certa data.
    Usa FIFO matching completo.
    """
    # Load transactions up to date
    # Build BUY lots queue
    # Process SELL/REMOVE/TRANSFER_OUT
    # Return remaining quantity
```

**Step 3 può riusare:**

```python
# services/transactions.py
async def create_sell_transaction(...):
    # Oversell guard
    held_qty = analysis.get_held_quantity_at_date(
        asset_id, broker_id, trade_date
    )
    if sell_qty > held_qty:
        raise HTTPException(400, "Oversell: attempting to sell more than held")
    
    # Proceed with transaction...
```

**Vantaggi:**

- ✅ **Zero duplicazione** di codice
- ✅ Step 3 più semplice (riusa logica esistente)
- ✅ FIFO matching in **un solo posto** (DRY)
- ✅ Test più robusti (logic già testata in Step 6)

---

### 4. Transactions Dopo Analysis (Step 3 dopo Step 6)

**Perché:**

- ✅ Può usare `analysis.get_held_quantity_at_date()` per oversell
- ✅ Implementazione più pulita e DRY
- ✅ Può testare immediatamente con analysis endpoints
- ✅ Tutta l'infrastruttura (FX, Plugins, Analysis) già pronta

**Cosa implementa:**

- POST /api/v1/transactions/buy (con auto cash movement)
- POST /api/v1/transactions/sell (con oversell guard)
- POST /api/v1/transactions/dividend
- POST /api/v1/transactions/transfer_asset
- POST /api/v1/cash/* (deposit, withdraw, transfer)
- Logica auto-generazione cash movements

---

## ⚠️ Problemi se si segue l'ordine originale (Step 3 subito)

### 1. Oversell Guard Parziale

**Step 3 ora:**

```python
# Devi implementare calcolo inventory
def check_oversell(asset_id, broker_id, date, qty):
    # Implementazione parziale/semplificata
    # Magari senza FIFO corretto
    # Magari senza gestire tutti i casi edge
```

**Step 6 dopo:**

```python
# Reimplementi la stessa cosa, ma completa
def fifo_matching(...):
    # FIFO completo con tutti i casi
    # BUY lots queue
    # Pro-rata fees/taxes
    # Matching corretto
```

**Risultato**: Codice duplicato, tempo sprecato, bug potenziali

---

### 2. Testing Limitato

**Senza plugins (Step 5):**

- ❌ Non puoi testare transazioni con valutazioni reali
- ❌ Non puoi verificare impatto su portfolio value
- ❌ Loan assets non valutabili

**Senza FX (Step 4):**

- ❌ Non puoi testare multi-currency
- ❌ Non puoi validare conversioni

**Senza Analysis (Step 6):**

- ❌ Non puoi verificare correttezza inventory
- ❌ Non puoi testare P/L

---

### 3. Dipendenze Mancanti

Step 3 presume:

- Service layer esistente
- HTTP client configurato
- Error handling standardizzato
- Validation layer

Meglio costruirli gradualmente:

```
FX (semplice) → Plugins (medio) → Analysis (complesso) → Transactions (usa tutto)
```

---

## 📈 Flusso Logico del Nuovo Ordine

```
┌─────────────────────────────────────────────────────────────┐
│ Step 4: FX Rates                                            │
│ - Fetch rates da ECB                                        │
│ - Conversione valute con forward-fill                       │
│ - Foundation per multi-currency                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Plugins                                             │
│ - yfinance per stocks/ETFs                                  │
│ - synthetic_yield per loans                                 │
│ - Sistema estensibile                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Runtime Analysis (FIFO completo)                    │
│ - FIFO matching BUY lots                                    │
│ - Calcolo inventory at any date   ← Questa logica!         │
│ - P/L realized                                              │
│ - Series Invested/Market                                    │
│ - ROI metrics                                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Riusa logica ↓
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Transactions & Cash                                 │
│ - Oversell guard usa analysis.get_held_quantity()           │
│ - Auto cash movements                                       │
│ - Endpoint transazioni                                      │
│ - SEMPLICE perché riusa infrastruttura esistente!          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 7: Portfolio Aggregations                              │
│ - Usa Analysis per aggregare                                │
│ - Usa FX per conversione                                    │
│ - Overview portfolio                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Raccomandazione Finale (Aggiornato 5 Nov 2025)

### ✅ PROCEDI CON STEP 5 (Plugins: yfinance, CSS scraper, synthetic_yield)

**Perché è la scelta migliore:**

1. **Necessario per Step 6**: Analysis richiede valutazioni asset
2. **Indipendente dalle transazioni**: Non serve inventory/FIFO
3. **Fondamentale per loan assets**: synthetic_yield è critico
4. **Testabile in isolamento**: Può essere testato con asset mock
5. **Modularità**: Sistema plugin riusabile per futuri data source

**Cosa implementare:**

#### 1. Plugin System Base (~2-3 giorni)

```python
✅ plugins/base.py - Abstract DataPlugin class
✅ plugins/registry.py - Plugin factory con discovery
✅ TypedDicts per CurrentValue e HistoricalData
✅ Error handling unificato (PluginError)
```

#### 2. yfinance Plugin (~1-2 giorni)

```python
✅ get_current_value() - usa fast_info.last_price
✅ get_history_value(start, end) - ritorna OHLC
✅ Currency detection automatica
✅ Error handling per ticker non trovati
```

#### 3. CSS Scraper Plugin (~1-2 giorni)

```python
✅ httpx + BeautifulSoup4
✅ Robust float parsing (gestisce "1.234,56" e "1,234.56")
✅ Configurable via plugin_params (url, selector)
✅ Optional history support
```

#### 4. synthetic_yield Plugin (~3-4 giorni) ← **Più complesso**

```python
✅ Read interest_schedule from asset
✅ Support multiple day-count conventions (ACT/365, ACT/360, 30/360)
✅ Support SIMPLE and COMPOUND interest
✅ Handle maturity + grace period + late_interest
✅ Generate daily price series (principal + accrued interest)
✅ No network I/O (pure computation)
```

#### 5. API Endpoints (~1 giorno)

```python
✅ POST /api/v1/assets/{id}/refresh-current
✅ POST /api/v1/assets/{id}/refresh-history?start=&end=
✅ POST /api/v1/plugins/test (validation endpoint)
```

**Stima totale**: 8-12 giorni

**Benefici immediati:**

- ✅ Loan assets diventano valutabili
- ✅ Stock/ETF prezzi automatici via yfinance
- ✅ Backup manual pricing via CSS scraper
- ✅ Infrastruttura pronta per Step 6 (Analysis)

**Dopo Step 5:**

- Step 6 (Analysis) può calcolare Market Value per tutti asset types
- Step 6 può generare serie Invested vs Market
- Step 3 (Transactions) non bloccato (Step 5 è indipendente)

---

## 📊 Confronto Tempi di Sviluppo (Aggiornato)

### Ordine Originale

```
Step 3: 5-7 giorni (oversell parziale)
✅ Step 4: 2-3 giorni (COMPLETATO in ~3 giorni)
Step 5: 4-5 giorni
Step 6: 6-8 giorni (FIFO completo + refactor Step 3) ← Spreco!
Total: 17-23 giorni + refactoring
```

### Ordine Suggerito (Aggiornato)

```
✅ Step 4: 2-3 giorni (COMPLETATO)
→ Step 5: 8-12 giorni  [PROSSIMO]
→ Step 6: 6-8 giorni (FIFO completo)
→ Step 3: 3-4 giorni (riusa Step 6, più semplice)
Total: 19-27 giorni, zero refactoring
```

**Risparmio**: Eliminata duplicazione FIFO + codice più pulito

**Note**: Step 5 richiede più tempo del previsto per synthetic_yield (interest schedules complessi)

---

## ✅ Checklist per Step 5 (Prossimo)

Quando passi a Step 5, implementa:

### 1. Plugin System Base

- [ ] `services/plugins/base.py` - Abstract DataPlugin class
- [ ] `services/plugins/registry.py` - Factory con discovery
- [ ] TypedDicts: `CurrentValue`, `PricePoint`, `HistoricalData`
- [ ] Exception: `PluginError` con error_code
- [ ] Test plugin registration

### 2. yfinance Plugin

- [ ] `services/plugins/yfinance_plugin.py`
- [ ] `get_current_value()` - usa yfinance.Ticker
- [ ] `get_history_value(start, end)` - ritorna OHLC
- [ ] Currency detection (ticker.info['currency'])
- [ ] Error handling (ticker non trovato, API error)
- [ ] Test con ticker reale (AAPL, MSFT)

### 3. CSS Scraper Plugin

- [ ] `services/plugins/cssscraper_plugin.py`
- [ ] httpx + BeautifulSoup4
- [ ] Robust float parsing ("1.234,56" e "1,234.56")
- [ ] Configurable (current_url, current_css_selector)
- [ ] Optional history support
- [ ] Test con HTML mock

### 4. synthetic_yield Plugin

- [ ] `services/plugins/synthetic_yield_plugin.py`
- [ ] Read asset.interest_schedule (JSON array)
- [ ] Day-count conventions: ACT/365, ACT/360, 30/360
- [ ] Interest types: SIMPLE, COMPOUND
- [ ] Maturity + grace period handling
- [ ] Late interest rate application
- [ ] Generate daily series (principal + accrued)
- [ ] Test con schedule complesso

### 5. API Endpoints

- [ ] `POST /api/v1/assets/{id}/refresh-current`
- [ ] `POST /api/v1/assets/{id}/refresh-history?start=&end=`
- [ ] `POST /api/v1/plugins/test` (validation)
- [ ] Error handling (plugin not found, config invalid)
- [ ] Test endpoint integration

### 6. Service Layer

- [ ] `services/pricing.py` - coordinate plugin calls
- [ ] `update_current_price(asset_id)` - update price_history
- [ ] `update_history(asset_id, start, end)` - bulk update
- [ ] Plugin selection logic (by asset.current_data_plugin_key)
- [ ] Test service layer

### 7. Documentazione

- [ ] Plugin development guide
- [ ] API documentation
- [ ] Example configurations
- [ ] Testing guide update

---

## 📚 Note Finali

### Principi Seguiti

1. **Build from bottom-up**: Data → Logic → API
2. **DRY (Don't Repeat Yourself)**: FIFO in un solo posto
3. **Dependencies first**: FX e Plugins prima di Analysis
4. **Test-driven**: Ogni step testabile in isolamento
5. **Progressive complexity**: Semplice → Medio → Complesso

### Flessibilità

Se durante Step 4-5-6 emergono necessità per endpoint transazioni semplici (es. solo BUY per test), si possono implementare **in modo minimale** senza oversell guard completo,
sapendo che verrà completato in Step 3 post-Step 6.

### Comunicazione

Questo documento va condiviso con il team per allineamento sulla strategia di sviluppo.

---

**Pronto per Step 5: Plugins System! 🚀**

---

## 📝 Note Finali - Review 5 Nov 2025

### ✅ Completato con Successo

**Step 4 (FX Multi-Provider)**:

- Sistema production-ready al 100%
- 45/45 test passano
- Documentazione completa (~15000 parole)
- Performance ottimizzate
- Architettura estensibile

**Qualità del codice**:

- ✅ Test coverage completo
- ✅ Error handling robusto
- ✅ Documentazione esaustiva
- ✅ Best practices async/await
- ✅ Type hints completi

### 🎯 Prossimo Step: Plugin System (Step 5)

**Priorità**: ⭐⭐⭐⭐⭐ (Fondamentale)

**Motivi**:

1. Necessario per Step 6 (Analysis)
2. Indipendente da transazioni
3. synthetic_yield critico per loan assets
4. yfinance + CSS scraper per market assets
5. Sistema plugin riusabile

**Stima**: 8-12 giorni
**Complessità**: Media-Alta (synthetic_yield complesso)

### 💡 Raccomandazione

**Procedi con Step 5 (Plugins)**. Il sistema FX è solido e completo, fornisce foundation perfetta per plugin system che potrà usare conversioni multi-currency per prezzi.

Step 3 (Transactions) può aspettare fino a dopo Step 6 (Analysis) per riusare logica FIFO completa ed evitare duplicazione codice.

