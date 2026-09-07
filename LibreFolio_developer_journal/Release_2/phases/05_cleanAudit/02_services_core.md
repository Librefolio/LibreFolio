# 02 — Servizi core (portfolio, FIFO, lots, transactions)

> `portfolio_service.py`, `portfolio_engine.py`, `lots_analysis_service.py`,
> `transaction_service.py`, `fifo_lot_engine.py`, `utils/financial/`
> 10 965 righe · Gravità massima: 🔴

---

## Sintesi

Questo è il cuore finanziario di LibreFolio e si vede: la qualità algoritmica è alta, il
`FifoLotEngine` è un pezzo di ingegneria serio (lotti, chiusure, frammenti, eventi
economici, trasferimenti, custodia, qualità del dato), e il commento *"WAC is computed
inline during the daily state build — no separate `compute_wac_iterative` calls needed
(eliminates N×M DB round-trips)"* dimostra che l'ottimizzazione è già una preoccupazione
consapevole di chi scrive.

Il debito qui non nasce da disattenzione ma da **refactoring lasciati a metà**. Il
passaggio da `portfolio_service` a `portfolio_engine` ha funzionato — l'engine è in
produzione — ma l'implementazione precedente non è mai stata rimossa, e in un punto la
sostituzione ha lasciato una chiamata rotta.

---

## Metriche

| File | Righe | Nota |
|---|---:|---|
| `portfolio_service.py` | 2 492 | contiene ~156 righe di residuo pre-engine |
| `portfolio_engine.py` | 2 296 | implementazione corrente |
| `lots_analysis_service.py` | 2 055 | |
| `transaction_service.py` | 1 727 | contiene la funzione più complessa del progetto |
| `fifo_lot_engine.py` | 1 554 | motore FIFO corrente |
| `utils/financial/fifo_utils.py` | 148 | motore FIFO **precedente**, superato |

Rilievi ruff: 25 `C901`, 11 `RUF100`, 6 `SIM108`, 5 `PERF401`.

### Le funzioni più complesse del progetto

| Complessità | Funzione | File |
|---:|---|---|
| **112** | `execute_batch` | `transaction_service.py` |
| **97** | `build` | `portfolio_engine.py` |
| **73** | `get_summary` | `portfolio_service.py` |
| **62** | `get_positions_contribution` | `portfolio_service.py` |
| 35 | `get_lots_analysis` | `lots_analysis_service.py` |
| 32 | `compute_wac_iterative_multi_broker` | `portfolio_service.py` |
| 32 | `compute_wac_iterative` | `portfolio_service.py` |
| 26 | `calculate` | `portfolio_engine.py` |

La soglia ruff è 10. Il valore 112 non è un numero da lint report: significa oltre cento
percorsi di esecuzione indipendenti in una singola funzione.

---

## Reperti

### 🔴 B1 — `get_global_setting()` chiamata con argomenti invertiti e un positional di troppo

**Dove**: `backend/app/services/portfolio_engine.py:1960`

```python
# portfolio_engine.py:42
from backend.app.services.settings_service import get_global_setting
...
# portfolio_engine.py:1960 — dentro calculate()
if target_currency is None:
    target_currency = await get_global_setting(self.db, "base_currency", "EUR")
```

La firma importata è:

```python
# settings_service.py:128
async def get_global_setting(key: str, session: AsyncSession) -> Optional[GlobalSettingRead]
```

Tre errori sovrapposti in una riga:

1. **Argomenti invertiti** — `key` riceve una `AsyncSession`, `session` riceve la
   stringa `"base_currency"`.
2. **Un positional di troppo** — la funzione accetta 2 argomenti, ne vengono passati 3.
   `TypeError: get_global_setting() takes 2 positional arguments but 3 were given`.
3. **Funzione sbagliata** — la firma `(session, key, default)` corrisponde esattamente a
   `global_settings_service.get_setting_value(session, key, default)`. È quella che
   l'autore intendeva chiamare.

**Il bug è latente, non attivo**: tutti i chiamanti reali di `calculate()`
(`portfolio_service.py:1103`, `1699`, `2222`, `2331`) passano `target_currency`
esplicitamente, quindi il ramo non viene mai imboccato. L'unica altra occorrenza
(`portfolio_engine.py:1937`) è dentro un docstring.

Resta però una mina: il primo chiamante che ometterà `target_currency` — cosa che la
firma con default `None` autorizza esplicitamente — otterrà un `TypeError` in
produzione. Ed è codice mai eseguito, quindi nessun test lo copre.

```python
# Rimedio
from backend.app.services.global_settings_service import get_setting_value
...
target_currency = await get_setting_value(self.db, "default_currency", "EUR")
```

Si noti `default_currency`, non `base_currency` — vedi reperto B2.

---

### 🔴 B2 — La chiave `"base_currency"` non esiste fra i global settings

**Dove**: `lots_analysis_service.py:581`, `portfolio_service.py:846`,
`portfolio_engine.py:1960`

Tre punti del codice leggono l'impostazione globale `"base_currency"`:

```python
# lots_analysis_service.py:581
async def _get_base_currency(self) -> str:
    setting = await get_global_setting("base_currency", self.db)
    return setting.value if setting else "EUR"
```

Ma `GLOBAL_SETTINGS_DEFAULTS` (`backend/app/schemas/settings.py`) non contiene alcuna
chiave `base_currency`. Le chiavi dichiarate sono `session_ttl_hours`,
`enable_registration`, `require_email_verification`, `max_file_upload_mb`,
`scheduler_*`, `default_currency`, `default_language`.

Quella giusta è **`default_currency`**, descritta come *"Default display currency for
new users"*.

Conseguenza: la query non trova nulla, `setting` è `None`, e il fallback restituisce
**sempre** `"EUR"` hardcoded. L'amministratore che imposta una valuta di default diversa
la vede correttamente applicata alle preferenze utente (quel percorso usa la chiave
giusta, `settings_service.py:55`) ma **non** alle valutazioni di portafoglio, ai lotti e
al motore.

Il bug non si manifesta come errore: si manifesta come un'impostazione che non ha
effetto. È il tipo di difetto che sopravvive alle release.

Da verificare durante il fix se la semantica voluta è davvero `default_currency` o se
serve una chiave dedicata `base_currency` da aggiungere ai default — è una decisione di
dominio, non meccanica.

---

### 🔴 B3 — WAC multi-broker completo, testato e cablato a nulla

**Dove**: `backend/app/services/portfolio_service.py:347`
(`compute_wac_iterative_multi_broker`, complessità 32)

```python
async def compute_wac_iterative_multi_broker(
    session, broker_ids: list[int], asset_id, as_of_date, asset_currency, ...
) -> WACPreviewResultItem:
    """Compute unified WAC (PMC) for one asset across multiple brokers.

    Transactions from all brokers are treated as one unified position for WAC
    purposes. This is valid for WAC because it depends on cumulative quantity
    and cost, but it is NOT equivalent to FIFO lot tracking, which remains
    strictly per-broker elsewhere in codebase.
    """
```

Il docstring è preciso e argomenta la correttezza finanziaria della scelta. La funzione
ha una suite di test dedicata (`test_portfolio_service.py`, 4 casi fra cui un test di
idempotenza). **Nessun codice di produzione la chiama.**

> **Tracciatura della logica**: `compute_wac_iterative` (versione a broker singolo)
> **è** viva — la usano `portfolio_api.py:65` e `transaction_service.py:1650`. Ma non
> assorbe la variante multi-broker: la prima accetta `broker_id: int`, la seconda
> `broker_ids: list[int]` e calcola una posizione unificata. Sono capacità **diverse**.

Non è codice morto: è una **funzionalità sviluppata, verificata e mai esposta**. Va
deciso se cablarla (un endpoint WAC aggregato cross-broker) o se rimuoverla insieme ai
test. La rimozione perde una capacità che oggi non esiste altrove.

**Nota aggiuntiva**: le due funzioni hanno entrambe complessità 32 e struttura quasi
identica (query → conversione FX → delega a `compute_wac_from_txlist`). Differiscono
solo nel filtro `Transaction.broker_id == broker_id` contro
`Transaction.broker_id.in_(broker_ids)`. Se si decide di tenerle entrambe, andrebbero
unificate in una sola funzione che accetta una lista — dimezzando 64 punti di
complessità.

---

### 🟡 B4 — Residuo pre-engine in `portfolio_service.py`

**Dove**: `portfolio_service.py`, righe ~605–765

Il refactoring verso `PortfolioEngine` ha spostato il calcolo dello storico, ma il
blocco precedente è rimasto in casa. Oggi `get_history()` (riga 1674) delega
all'engine:

```python
# portfolio_service.py:1713
history_dicts = views.build_history()
```

mentre il vecchio percorso è ancora presente e vivo solo grazie ai propri test:

| Simbolo | Riga | Stato |
|---|---:|---|
| `_HistoryTxRow` | 605 | usato solo dal blocco legacy |
| `_HistoryQtyRow` | 622 | **non referenziato da nessuno** |
| `_HistoryCalcPoint` | 636 | usato solo dal blocco legacy |
| `_price_on_date` | 653 | solo test |
| `_daily_state_as_of` | 673 | |
| `_build_history_series` | 691 | solo test |

Sono circa **156 righe**. La conferma sta nel docstring stesso di
`_build_history_series`: *"`market_value`/`nav_value` are temporary placeholders at this
stage and are patched later by the mark-to-market layer in `get_history()`"* — ma
`get_history()` non lo chiama più.

Anche il test lo documenta: *"NOTE: `_build_history_series` was refactored to produce a
dense daily series"*.

> **Tracciatura**: logica **riassorbita** da `portfolio_engine.build_history()`
> (riga 1577) e dal `DerivedViewsBuilder`. Rimozione sicura, insieme ai ~10 test unitari
> che la coprono.

Stesso discorso per `_bulk_load_asset_prices` (riga 897) e `_get_quote_base_map`
(riga 936): entrambi metodi di `PortfolioService` usati solo dai test, il caricamento
prezzi ora avviene nell'engine.

---

### 🟡 B5 — `fifo_utils.calculate_fifo_lots` superato da `FifoLotEngine`

**Dove**: `backend/app/utils/financial/fifo_utils.py:66` (148 righe di modulo)

Motore FIFO puro — *"pure math, no I/O"*, matching con `deque`. Nessun import in tutto
`backend/app`; solo `test_fifo_utils.py` lo usa.

> **Tracciatura**: logica **riassorbita** da `fifo_lot_engine.py` (1 554 righe), che
> copre il matching FIFO più lotti, chiusure, frammenti temporali, eventi economici,
> trasferimenti, tipi di custodia e diagnostica di qualità del dato. La storia git lo
> conferma: `fifo_utils.py` risale al commit *"feat(portfolio): add financial services"*
> ed è stato toccato l'ultima volta dal *"refactor(portfolio-engine)"*, mentre
> `fifo_lot_engine.py` nasce dopo con *"First iteration with fifo-engine"*.

Rimozione sicura del modulo e dei suoi test.

⚠️ Prima di rimuovere, verificare che `FifoLotEngine` copra davvero i casi limite
testati da `test_fifo_utils.py` (11 test). Se qualche caso limite non è coperto
dall'engine, il test va **portato** sull'engine, non buttato.

---

### 🟡 B6 — `execute_batch`: complessità 112

**Dove**: `backend/app/services/transaction_service.py` (`execute_batch`)

Undici volte la soglia, la funzione più complessa del progetto con distacco. Gestisce
l'esecuzione batch di operazioni sulle transazioni: creazione, aggiornamento,
cancellazione, validazioni, collegamenti fra transazioni, effetti collaterali.

Non è codice sbagliato — è codice **impossibile da tenere in testa tutto insieme**, con
oltre cento percorsi indipendenti. Ogni modifica futura in quest'area è un rischio, e la
copertura dei test non può realisticamente esplorare tutte le combinazioni.

Estrazione consigliata per tipo di operazione (un handler per verbo, con dispatch
tabellare). Intervento non urgente ma da pianificare: è l'unico punto del codebase dove
la complessità è di per sé un rischio operativo.

Stessa famiglia, meno gravi: `build` (97, `portfolio_engine.py`), `get_summary` (73) e
`get_positions_contribution` (62) in `portfolio_service.py`.

---

### 🟢 B7 — Aggregatori di qualità del dato usati solo dai test

**Dove**: `portfolio_engine.py:1690`, `1697`, `1704`, `1711`

Quattro metodi simmetrici di `DerivedViewsBuilder`:

```python
def aggregate_missing_price_ids(self) -> set[int]: ...
def aggregate_stale_price_ids(self) -> set[int]: ...
def aggregate_missing_fx_pairs(self) -> set[str]: ...
def aggregate_transaction_implied_ids(self) -> set[int]: ...
```

Ciascuno è un fold banale (4-5 righe) sugli stati giornalieri. Nessun chiamante in
produzione.

> **Tracciatura**: subito dopo, `build_data_quality_report()` (riga 1717) produce il
> report di qualità che il resto del sistema usa, ma calcola le aggregazioni per conto
> suo invece di appoggiarsi a questi quattro metodi.

Non è logica persa: è **duplicazione**. Delle due l'una — o
`build_data_quality_report()` li usa, oppure vanno rimossi. La prima opzione è
preferibile: sono già testati.

---

### 🟢 B8 — Alias di compatibilità senza consumatori

**Dove**: `portfolio_engine.py:450`, `456`

```python
@property
def valuation_price(self) -> Decimal | None:
    """Compatibility alias for the effective current-unit price."""
    return self.valuation_effective_unit_price
```

Alias introdotti per non rompere consumatori durante una rinomina. La rinomina è
completa: nessuno usa più i nomi vecchi, né il backend, né i test, né il frontend.

> **Tracciatura**: logica **riassorbita** dai campi con il nome nuovo
> (`valuation_effective_unit_price`, `valuation_effective_currency`).

Rimozione sicura. Stesso caso per `fifo_lot_engine.py:342`
(`signed_quantity_by_broker`), usato solo dai test.

---

## Interventi raccomandati

| Priorità | Intervento | Costo | Rischio |
|---|---|---|---|
| 1 | Correggere `portfolio_engine.py:1960` — funzione, ordine argomenti e chiave | basso | basso |
| 2 | Decidere la semantica di `base_currency` vs `default_currency` e allineare i 3 call site | basso | medio |
| 3 | Decidere su `compute_wac_iterative_multi_broker`: cablare o rimuovere | medio | — |
| 4 | Rimuovere il blocco pre-engine di `portfolio_service.py` (~156 righe + test) | basso | basso |
| 5 | Rimuovere `fifo_utils.py` — **dopo** aver verificato i casi limite sull'engine | basso | medio |
| 6 | Far usare a `build_data_quality_report()` i quattro `aggregate_*` | basso | basso |
| 7 | Rimuovere gli alias `valuation_price*` e `signed_quantity_by_broker` | basso | nullo |
| 8 | Pianificare la scomposizione di `execute_batch` (112) | alto | medio |

Gli interventi 1 e 2 sono bug. Il 3 è una decisione di prodotto che non va presa da
sola. Dal 4 al 7 sono pulizia a rischio basso che restituisce ~250 righe. L'8 è lavoro
strutturale da programmare, non da improvvisare.
