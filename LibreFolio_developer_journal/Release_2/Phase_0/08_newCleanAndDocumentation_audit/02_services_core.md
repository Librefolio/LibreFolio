# 02 — Servizi core — verifica 2026-09-02

> Fonte: [report archiviato](../../phases/05_cleanAudit/02_services_core.md) (audit 2026-08-05/07)
> Metodo: analisi statica read-only; nessun test eseguito (run full seriale in corso sul DB condiviso).
> Baseline di confronto: commit `09cbb7e2` (ultimo commit prima dei report, 05/08 mattina);
> l'esecuzione S1–S3 è `be8394bb` (05/08 pomeriggio); il working tree del 02/09 è parte della realtà verificata.

---

## Sintesi esecutiva

Il bilancio a un mese è **misto ma in chiara direzione positiva sulla pulizia strutturale**:
l'esecuzione S1–S3 (stesso giorno dell'audit) ha rimosso il blocco pre-engine di
`portfolio_service.py` (B4, −130 righe sorgente / −176 righe test), gli alias di
compatibilità (B8) e i `try/except/pass` (C6, vedi report 03). **Nessuno dei tre bug 🔴,
però, è stato toccato**: B1 (chiamata rotta latente) e B2 (chiave inesistente) sono
identici a un mese fa, riga per riga, e B3 (WAC multi-broker mai cablato) attende ancora
una decisione. `execute_batch` è persino peggiorato (112 → **115**). Nel frattempo le
ondate beta hanno aggiunto guardie difensive (`_daily_state_as_of` è oggi codice vivo) e
nuova copertura test, senza introdurre codice morto rilevante in questo ambito.

Voto di sintesi: pulizia "facile" fatta subito; i tre reperti rossi — quelli che
richiedono una decisione di dominio — sono tutti ancora sul tavolo.

---

## Tabella di verifica

| Voce vecchia | Stato 2026-08 | Stato verificato oggi | Evidenza (file:riga attuale) | Azione |
|---|---|---|---|---|
| B1 — `get_global_setting()` argomenti invertiti + positional di troppo | 🔴 aperto | **ANCORA VALIDO** | `backend/app/services/portfolio_engine.py:1967` (`await get_global_setting(self.db, "base_currency", "EUR")`); import a `:42`; firma `settings_service.py:128` `(key, session)` a 2 argomenti | Task 1 |
| B2 — chiave `"base_currency"` inesistente | 🔴 aperto | **ANCORA VALIDO** | `lots_analysis_service.py:581`, `portfolio_service.py:719`, `portfolio_engine.py:1967`; `GLOBAL_SETTINGS_DEFAULTS` in `schemas/settings.py` ha `default_currency` (`:135`), nessuna `base_currency` | Task 2 |
| B3 — `compute_wac_iterative_multi_broker` cablato a nulla | 🔴 aperto | **ANCORA VALIDO** | `portfolio_service.py:347`; zero chiamanti produzione, solo `test_portfolio_service.py:40,136,191,269,289,353`. La variante singola è viva: `portfolio_api.py:65`, `transaction_service.py:1662` | Task 3 |
| B4 — residuo pre-engine (~156 righe, 6 simboli) | 🟡 aperto | **FATTO (blocco) / PARZIALE (2 helper)** | `_HistoryTxRow`, `_HistoryQtyRow`, `_HistoryCalcPoint`, `_price_on_date`, `_build_history_series` **rimossi** (grep: zero occorrenze in `backend/`); `_daily_state_as_of` (`:600`) sopravvissuto e oggi **vivo** (`:895`, `:989`); `_bulk_load_asset_prices` (`:770`) e `_get_quote_base_map` (`:809`) restano **test-only** | Task 4 |
| B5 — `fifo_utils.calculate_fifo_lots` superato | 🟡 aperto | **ANCORA VALIDO** | `backend/app/utils/financial/fifo_utils.py` presente, 148 righe; unico consumatore `test_fifo_utils.py` (11 test); registrato in `scripts/test_runner/_backend_services.py:463` | Task 5 |
| B6 — `execute_batch` complessità 112 | 🟡 aperto | **ANCORA VALIDO, peggiorato** | `transaction_service.py:937-1578`, C901 = **115** (riprodotto: `ruff check --select C901`) | Task 8 |
| B7 — 4 `aggregate_*` usati solo dai test | 🟢 aperto | **ANCORA VALIDO** | `portfolio_engine.py:1678,1685,1692,1699`; unici chiamanti `test_daily_state_builder.py:783-786`; `build_data_quality_report` (`:1706`) li ignora e lavora su DTO pre-costruiti | Task 6 |
| B8 — alias `valuation_price*` e `signed_quantity_by_broker` | 🟢 aperto | **FATTO** (con residuo nuovo, vedi N-02-A) | alias rimossi da `portfolio_engine.py` (diff `09cbb7e2..HEAD`); `signed_quantity_by_broker` eliminato da `fifo_lot_engine.py` (era `:339-345`); zero occorrenze residue | — |
| Assorbimento `get_session_ttl`/`_sync` (citato in indice generale) | — | **FATTO** | `settings_service.py` non li contiene più (funzioni presenti: `:32,46,80,128,144,161,188`); `global_settings_service.py:75` espone `get_session_ttl_hours`; test spostati in `test_global_settings_service.py` | — |

### Metriche riprodotte

Comandi eseguiti (working tree 02/09):

```bash
wc -l backend/app/services/{portfolio_service,portfolio_engine,lots_analysis_service,transaction_service,fifo_lot_engine}.py backend/app/utils/financial/fifo_utils.py
# 2385 / 2311 / 2055 / 1739 / 1547 / 148   (audit: 2492 / 2296 / 2055 / 1727 / 1554 / 148)

cd backend && pipenv run ruff check app/services/portfolio_service.py app/services/portfolio_engine.py \
  app/services/lots_analysis_service.py app/services/transaction_service.py app/services/fifo_lot_engine.py \
  app/utils/financial/ --select C901,RUF100,SIM108,PERF401 --output-format concise | awk -F: '{print $4}' | sort | uniq -c
# 26 C901 · 11 RUF100 · 7 SIM108 · 4 PERF401   (audit: 25 / 11 / 6 / 5)
```

Funzioni di punta (C901, soglia 10), verificate una per una:

| Funzione | Audit | Oggi | Posizione attuale |
|---|---:|---:|---|
| `execute_batch` | 112 | **115** | `transaction_service.py:937` |
| `build` | 97 | 97 | `portfolio_engine.py:562` |
| `get_summary` | 73 | 73 | `portfolio_service.py:943` |
| `get_positions_contribution` | 62 | 62 | `portfolio_service.py:1707` |
| `get_lots_analysis` | 35 | 35 | `lots_analysis_service.py:169` |
| `compute_wac_iterative_multi_broker` | 32 | 32 | `portfolio_service.py:347` |
| `compute_wac_iterative` | 32 | 32 | `portfolio_service.py:95` |
| `calculate` | 26 | 26 | `portfolio_engine.py:1952` |

---

## Dettaglio reperti ancora aperti / regrediti

### B1 — invariato, ancora latente

`portfolio_engine.py:1966-1967`:

```python
if target_currency is None:
    target_currency = await get_global_setting(self.db, "base_currency", "EUR")
```

Tre errori sovrapposti confermati: argomenti invertiti, 3 positional contro i 2 della
firma (`settings_service.py:128`), funzione sbagliata (quella voluta è
`global_settings_service.get_setting_value(session, key, default)`, `:30`).
Resta latente: tutti e 4 i chiamanti produzione di `calculate()`
(`portfolio_service.py:976, 1581, 2108, 2222` — verificati con `grep -A6`) passano
`target_currency` esplicitamente. La firma con default `None` continua ad autorizzare il
ramo rotto. **Sopravvissuto a due ondate di remediation pur essendo la priorità 1
dell'audit e un fix da una riga.**

### B2 — invariato

Le tre letture di `"base_currency"` (`lots_analysis_service.py:581`,
`portfolio_service.py:719`, `portfolio_engine.py:1967`) non trovano alcuna chiave nei
default (`schemas/settings.py:135` dichiara `default_currency`); il fallback `"EUR"`
hardcoded scatta sempre. Il percorso preferenze utente usa la chiave giusta
(`settings_service.py:55,91`) — la divergenza di semantica segnalata dall'audit è intatta.

### B3 — invariato

`compute_wac_iterative_multi_broker` (`portfolio_service.py:347`) conserva docstring,
test dedicati (5 call site in `test_portfolio_service.py`) e zero chiamanti di
produzione. Confermata la quasi-identità strutturale con la variante singola: differenza
di filtro a `:116` (`broker_id ==`) contro `:370` (`broker_id.in_()`); entrambe C901=32.

### B4 — rimozione confermata, con due sopravvissuti

La rimozione S1–S3 è reale: nessuna occorrenza residua dei 5 simboli, e il test runner
li cerca ancora invano nelle stringhe descrittive (vedi N-02-B). Però:

- `_bulk_load_asset_prices` (`portfolio_service.py:770`) — chiamanti: solo
  `test_portfolio_service.py:971,974`.
- `_get_quote_base_map` (`:809`) — chiamanti: solo `test_portfolio_service.py:972,989`.
- `_daily_state_as_of` (`:600`) — **promosso a codice vivo**: usato a `:895` (metriche di
  periodo) e `:989` (get_summary) come guardia anti cache-blob; non va più rimosso.

### B6 — peggiorato

`execute_batch` oggi misura 115 (+3) e copre ~640 righe (`:937-1578`). Le ondate beta
(delete via bulk modal, wizard import) hanno aggiunto percorsi invece di estrarre handler.
La raccomandazione (dispatch tabellare per verbo) è più attuale di prima.

### B7 — invariato

I quattro `aggregate_*` (`portfolio_engine.py:1678-1704`) restano fold banali consumati
solo da `test_daily_state_builder.py:783-786`. `build_data_quality_report` (`:1706`) è
cresciuto a C901=18 e continua a calcolare per conto suo.

---

## Task riesumati

| # | Task (evidenza) | Stima |
|---|---|---|
| 1 | **B1**: `portfolio_engine.py:1967` → `get_setting_value(self.db, "default_currency", "EUR")`, fissare import `:42`. Un ramo oggi non coperto da test: aggiungere un test che chiama `calculate()` senza `target_currency` | **S** |
| 2 | **B2**: decidere se la semantica è `default_currency` o una nuova chiave `base_currency` dedicata; allineare i 3 call site (`lots_analysis_service.py:581`, `portfolio_service.py:719`, `portfolio_engine.py:1967`). Decisione di dominio, poi meccanica | **S** (dopo decisione) |
| 3 | **B3**: decidere su `compute_wac_iterative_multi_broker` (`portfolio_service.py:347`): cablare un endpoint WAC aggregato cross-broker oppure rimuovere funzione + 5 test. Se tenuta, unificare con la variante singola (un solo filtro `in_()`) | **M** |
| 4 | **B4-residuo**: `_bulk_load_asset_prices` (`:770`) e `_get_quote_base_map` (`:809`) sono test-only: o li usano i percorsi vivi o si rimuovono con i loro test | **S** |
| 5 | **B5**: rimuovere `utils/financial/fifo_utils.py` (148 righe) + `test_fifo_utils.py` (11 test) **dopo** aver mappato i casi limite su `FifoLotEngine`; aggiornare la registration `scripts/test_runner/_backend_services.py:463` | **S/M** |
| 6 | **B7**: far usare i 4 `aggregate_*` a `build_data_quality_report` (`portfolio_engine.py:1706`) o rimuoverli | **S** |
| 7 | **N-02-A**: rimuovere l'alias `ValuationResult.unit_price` (`portfolio_engine.py:145-149`), test-only (`test_daily_state_builder.py:595,631`); aggiornare i 2 assert a `effective_unit_price` | **S** |
| 8 | **B6**: pianificare la scomposizione di `execute_batch` (115, ~640 righe) in handler per verbo con dispatch tabellare | **L** |
| 9 | **N-02-B**: pulire le stringhe stale del test runner (`scripts/test_runner/_backend_services.py:408,466,830,836`) che citano `get_session_ttl_sync` e `_build_history_series`, simboli rimossi in S1–S3 | **S** |

---

## Nuovi rilievi

### N-02-A — Un alias di compatibilità è sopravvissuto alla bonifica B8 (🟢)

`portfolio_engine.py:145-149`: la property `ValuationResult.unit_price` dichiara
*"Compatibility alias for callers that previously read the effective price"*. I
consumatori di produzione usano `effective_unit_price` (`:1147`); l'alias è usato solo da
due assert di test (`test_daily_state_builder.py:595,631`). Stessa famiglia di B8, non
citato dall'audit: la bonifica alias va completata.

### N-02-B — Il test runner cita simboli rimossi (🟢, cosmetico)

`scripts/test_runner/_backend_services.py`:
- `:408` docstring *"Test settings service: get_session_ttl_sync"* — simbolo rimosso in S1–S3;
- `:830` `desc="get_session_ttl_sync"`;
- `:466` e `:836` citano `_build_history_series` — rimosso in S1–S3.

Solo stringhe di stampa CLI, nessun impatto funzionale; ma sono esattamente il tipo di
riferimento fantasma che un audit futuro rincorrerebbe.

### Cross-ref fuori ambito — regressione S110

L'esecuzione S1–S3 dichiarava *"`S110` in `backend/app/` è ora 0"*. Oggi:

```bash
cd backend && pipenv run ruff check app/ --select S110 --output-format concise
# app/utils/cache_utils.py:82:9: S110 try-except-pass detected  (1 errore)
```

Un `except Exception: pass` (con commento difensivo) in `cache_utils.py:80-83`, fuori
dall'ambito di questo report ma da segnalare al report crosscutting.

### Note positive dalle ondate beta (ambito core)

- **E2 — guardia dividendi/interessi su NAV**: nuovo test
  `test_portfolio_service.py:434+` (*"a DIVIDEND and an INTEREST move nav exactly like a
  DEPOSIT"*) con fixture fresche e invariante `nav == cash + market_value`. Copertura
  aggiunta, nessun debito.
- `_daily_state_as_of` (`portfolio_service.py:600`): guardia difensiva ben documentata
  contro cache-blob più ampi del range richiesto — il residuo B4 è diventato codice utile.
- Nessun codice morto nato dal refactor drawdown/full_history riscontrato nei file di
  questo ambito (dettagli nel report 03, sezione beta).

---

## Cross-reference

- Report 03 (pricing/FX) per C6 (`try/except/pass`, FATTO) e per la crescita di
  `asset_source.py`, che alimenta la complessità di `transaction_service` via bulk modal.
- Esecuzione S1–S3: [15_esecuzione_s1_s3.md](../../phases/05_cleanAudit/15_esecuzione_s1_s3.md)
  (righe 110-114: rimozione blocco pre-engine; 115-122: sette rimozioni con assorbimento,
  fra cui `get_session_ttl*` e gli alias B8).
- Indice audit originale: [INDEX.md](../../phases/05_cleanAudit/INDEX.md).
