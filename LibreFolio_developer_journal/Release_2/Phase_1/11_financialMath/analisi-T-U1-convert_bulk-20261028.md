# T-U1 — I punti che chiamano `convert_bulk`: una politica unica per i buchi e l'età del tasso

> Ondata 6, giorno 1 (28/10/2026), MF, **sola lettura**. Base letta: `f4a5e6e0a` (i 7 commit fino a `32674edb8`
> non toccano `backend/app` né `frontend/src`: `git diff --stat f4a5e6e0a 32674edb8 -- backend/app frontend/src` è
> vuoto). Backlog: T-U1 (`BACKLOG_POST_1.2.md:864`), MF-A13 (`:10837`). Piano: [plan-phase01FinancialMath](plan-phase01FinancialMath.prompt.md), «Ondata 6».
> Compagno: [inventario dei «giorni in cui cambia qualcosa»](inventario-change-days-20261028.md).

## 0. In una frase

**La conversione è già una casa sola; quello che è scritto più volte è come i chiamanti raccontano un tasso che manca
e un tasso vecchio.** Dopo P3 ogni conversione passa da una sola lettura (`fx/conversion._usable_rates`: righe
utilizzabili, ancora del riempimento, blocchi di `FX_PAIRS_PER_QUERY`) e da una sola aritmetica (`_converted`:
`amount × rate` diretta, `amount / rate` inversa); `unit_rate_steps` e `convert_by_stretch` danno gli stessi numeri al
bit. Il backlog («cinque chiamanti, ognuno a modo suo») descriveva lo stato dell'11/10, non quello di oggi.

## 1. Chi chiama, contati

| Via | Quante | Dove |
|---|---|---|
| `convert_bulk(...)` diretta | **15** | tabella §2 |
| `unit_rate_steps(...)` | **4** | motore (`engine.py:679`), cassa nativa (`native_cash.py:509`), lotti (`lots/conversions.py:108`), prezzi osservati (`observed_prices.py:164`) |
| `convert_by_stretch(convert=convert_bulk)` | **1** | `/fx/convert` (`api/v1/fx/currencies.py:561`) |

I «~17» del backlog sono questi 15 + i 2 lettori «a gradini» nati dopo (motore, lotti), che leggono gli stessi tassi.

## 2. Tabella: cosa fa ognuno del buco e della provenienza

Legenda della provenienza: `rate_date` = giorno della riga di tasso usata; `bf` = `backward_fill_applied`.

| # | Chiamante | `raise_on_error` | Tasso **mancante** (`None`) | Provenienza `(rate_date, bf)` | Giudizio |
|---|---|---|---|---|---|
| 1 | `portfolio_service._convert_to_base` (`:530-549`; usi `:756`, `:783`, prezzo unitario e prezzo di ieri del riepilogo) | no | valore `None` + `WACMissingPairInfo("CCY/BASE", [giorno])` | **buttata** | stessa idea di 2, 3, 4, 6 |
| 2 | `financial_math/yield_on_cost._resolve_conversion_context` (`:471`) | no | reddito escluso + `WACMissingPairInfo` + `missing_by_key` | **tenuta**: `YieldOnCostFxProvenance` (`rate_date`, `days_back`) | stessa idea |
| 3 | `financial_math/average_cost.compute_average_costs` (`:360`) | no | `MissingConversion(pair, dates, leg)` (`:537`) | **tenuta**: `rate_date`, `days_back` (`:485`) | stessa idea, forma propria |
| 4 | `financial_math/lots/conversions.FxRateResolver` (`unit_rate_steps`) | — | `None` + `missing_pairs()` con `dates` **e** `ranges` (D-P4) | buttata (legge solo il valore del gradino) | stessa idea, la forma più completa |
| 5 | `financial_math/native_cash.compute_native_cash` (`:507` + `:509`) | no | movimento escluso + `missing_conversions()` (`MissingCashConversion`); un saldo contato senza tasso **solleva** (`_foreign_value :233`, invariante) | buttata | stessa idea, forma propria |
| 6 | motore: `DailyStateBuilder._convert/_convert_movement` (`daily_state.py:1051-1065`) su `AskedDayRates` | — | `None` + `_missing_fx["CCY/TARGET"]` (date, poi `ranges`) | **letta**: `rate_day_at` → `stale_fx_pairs` (D-P4) | stessa idea; l'unico con l'età |
| 7 | `assets/observed_prices.resolve_days` (`:187`, prezzi convertiti di `POST /assets/prices/query`) | no | punto **nativo** + errore `rate_not_found_error` (max 10, `MAX_CONVERSION_ERRORS`) | **tenuta per punto**: `backward_fill_info.fx_rate_date/fx_days_back` | scopo diverso (serie da mostrare) |
| 8 | `assets/price_query` eventi (`:838`) | no | evento nativo + `"Missing FX rate A->B for event on D"` | tenuta: `fx_info` (`fx_rate_date`, `fx_days_back`) | **copia di 9** |
| 9 | `assets/event_store.query_events_bulk` (`:677`) | no | come 8, stesso testo | come 8 | **copia di 8** (stesso blocco, 30 righe) |
| 10 | `assets/period_changes.get_period_changes_bulk` (`:123`) | no | valore `None` + `"No A/B rate on or before D"` | buttata | scopo diverso (variazioni a periodo fisso), testo proprio |
| 11 | `assets/period_changes.live_range_changes` (`:180`) | no | variazione vuota, **nessun messaggio** | buttata | scopo diverso; l'unico silenzioso |
| 12 | `fx/period_changes._range_references` (`:76`) e `get_fx_period_changes_bulk` (`:106`) | no | `None` + `"No A/B rate on or before D"` | buttata | come 10 |
| 13 | `risk/eligibility` (`:271`) | no | sonda: `fx_available = False` | buttata | scopo diverso (idoneità), vedi §4.3 |
| 14 | AI `portfolio_income._convert_income` (`:414`) | no | riga con `conversion_reason="fx_rate_not_found"` | tenuta: `ConversionProvenance(rate_date, backfill_applied, identity)` | contratto dell'export (AIX) |
| 15 | AI `fx_core._load_exposure_conversions` (`:452`) | **sì** | la sezione fallisce (`RuntimeError`) | tenuta: `effective_date`, `is_backward_filled` | contratto dell'export (AIX) |
| 16 | AI `technical_shared.load_fx_rate_series` (`:682`) | no | salta i giorni prima del primo tasso; dopo → `FxRateHistoryError` | tenuta: `actual_date`, `backward_filled` | contratto dell'export; vedi §4.4 |
| 17 | `/fx/convert` (`currencies.py:561`, via `convert_by_stretch`) | no | risultato omesso (`continue`, `:577`) + errori compressi (`:663`) | tenuta solo se `bf`: `BackwardFillInfo(actual_rate_date, days_back)` | API pubblica, scopo diverso |

## 3. Le idee ripetute (le vere copie)

### 3.1 «Un buco nei cambi» scritto in 5 forme

Un esempio solo: dividendo di **10 USD il 01/03/2019**, report in EUR, primo tasso EUR/USD salvato il **02/01/2020**.
`convert_bulk` dice `None` e scrive `"Conversion 0: No FX rate found for EUR/USD on or before 2019-03-01"`. Poi:

| Chiamante | Come lo racconta |
|---|---|
| riepilogo (1), YoC (2) | `WACMissingPairInfo(pair="USD/EUR", dates=[2019-03-01])` |
| costo medio (3) | `MissingConversion(pair="USD/EUR", dates=(2019-03-01,), leg=…)` |
| lotti (4) | `WACMissingPairInfo(pair="USD/EUR", dates=[…], ranges=[…])` |
| cassa nativa (5) | `MissingCashConversion(pair="USD/EUR", dates=(2019-03-01,))` |
| motore (6) | `_missing_fx["USD/EUR"] = {2019-03-01}` → `WACMissingPairInfo` |
| variazioni (10, 12) | `"No USD/EUR rate on or before 2019-03-01"` |
| eventi (8, 9) | `"Missing FX rate USD->EUR for event on 2019-03-01"` |

Lo stesso buco ha **tre nomi**: `EUR/USD` (la coppia salvata, nel testo di `convert_bulk`), `USD/EUR` (FROM/TO, in
tutti i raccoglitori) e `USD->EUR` (gli eventi). I raccoglitori (1–6) sono la stessa idea: «coppia FROM/TO → giorni (e
intervalli) che mancano»; cambiano solo il contenitore e se fondono gli intervalli.

Prova che è una forma sola: la riga che chiude la raccolta,
`WACMissingPairInfo(pair=…, dates=sorted(…), ranges=[DateSpan(…) for … in merged_spans(…)])`, è scritta **identica 4
volte**: `portfolio_service.py:362` e `:589`, `lots_analysis_service.py:852`, `lots/conversions.py:165`.

### 3.2 «Un tasso vecchio» con la stessa soglia in 2 posti

Esempio: ultima riga USD/EUR del **20/10/2026**, valutazione il **28/10/2026** → 8 giorni, soglia
`STALE_PRICE_THRESHOLD_DAYS = 7` (`platform/data_quality_thresholds.py:14`) → vecchio.

| Dove | Cosa ne fa |
|---|---|
| motore, `daily_state._stale_fx_pair` (`:991`) + `AskedDayRates.stale_turn_days` (`fx_rates.py:124`) | `stale_fx_pairs = {"USD/EUR": 2026-10-20}` sullo stato → `DataQualityReport.stale_fx_pairs` (`StaleFxPair`, `stale_days=8`) |
| rischio, `market_series.py:521` | `carried_forward_fx_pairs = ["USD/EUR"]` → avviso `risk.warnings.data_quality_stale_fx_rates` (mostrato) |
| riepilogo (1), lotti (4), variazioni (10–12), YoC (2) | **niente**: convertono con il tasso di 8 giorni senza dirlo |

Il predicato «`(giorno − rate_date).days > 7`» è scritto due volte (`daily_state.py:997`, `market_series.py:521`) e
una terza in forma di «giorno in cui diventa vecchio» (`rate_day + threshold + 1`, `fx_rates.py:136`).

### 3.3 Il blocco eventi copiato (8 = 9)

`price_query.py:815-862` e `event_store.py:675-707`: stesso ciclo, stesso testo d'errore, stesso
`FxBackwardFillInfo(fx_rate_date, fx_days_back)`, stessa deduplica degli errori. È una funzione sola scritta due volte.
File di X: lo segnalo, non lo tocco.

## 4. Scopi diversi (da lasciare dove sono)

1. **Serie da mostrare** (7, 8/9, 17): il punto resta nativo e porta la sua provenienza; il frontend nasconde il punto
   non convertito (E.8.2). Giusto così: una serie non ha un «report» dove raccogliere i buchi.
2. **Variazioni a periodo fisso** (10, 11, 12): una variazione senza uno dei due capi è vuota. 11 è silenziosa per
   scelta (prezzo live della pagina asset, Y D1); 10 e 12 scrivono un errore con testo proprio. Nessun numero cambia
   unificando il testo, ma il testo esce nell'API (`errors`): cambiarlo è una scelta da fare con X e Y.
3. **Idoneità del rischio** (13): sonda il tasso al **primo** e all'**ultimo** giorno della finestra. Esempio: finestra
   01/01–28/10/2026, primo tasso USD/EUR il 01/02/2026 → la sonda del 01/01 è `None` → `fx_available=False`, anche se 9
   mesi su 10 convertono. È più severa della conversione: per il rischio (serie piena) è coerente, ma va confermato da J
   che sia voluto. Non è materia di T-U1.
4. **AI Export** (14, 15, 16): ognuno ha il suo modello di provenienza nel contratto (`ConversionProvenance`,
   `FxExposureConversion`, `FxRateObservation`). Restano: li possiede AIX, il bump v2 li può allineare. Due note per
   AIX:
   - 16 chiede `convert_bulk` per **ogni giorno di calendario** di warm-up + finestra (centinaia di conversioni per
     chiamata): `unit_rate_steps` darebbe gli stessi numeri a gradini, come fa `observed_prices`. Solo costo.
   - 16, ramo «history became unavailable after it had started» (`:688`): con il riempimento illimitato non può
     succedere (se c'è una riga utilizzabile ≤ d, c'è anche per ogni d' > d). Codice morto, innocuo.
   - 15 divide `target_amount / native_amount` (`fx_core.py:515`) **solo per riconciliare** con una tolleranza: non è
     un tasso usato per un valore, resta.

## 5. Proposta: una politica unica in `financial_math`

**Nessun valore cambia.** È una fattorizzazione di forme, non di numeri.

### 5.1 Il raccoglitore dei buchi (P-1)

Un tipo solo nella casa, `financial_math/fx_rates.py` (dove già stanno `AskedDayRates` e `oriented_rate`):

```python
class MissingFxCollector:
    """FROM/TO pair → the days (and spans) a conversion was asked and not made."""
    def day(self, source: str, destination: str, day: date) -> None: ...
    def span(self, source: str, destination: str, first: date, last: date) -> None: ...
    def pairs(self) -> list[WACMissingPairInfo]:  # dates + ranges (merged_spans), sorted
        ...
```

- Lo usano 1, 2, 4, 6 (oggi quattro raccolte a mano di `WACMissingPairInfo`).
- 3 (`MissingConversion`, con `leg`) e 5 (`MissingCashConversion`): restano tipi propri del loro dominio, ma li
  **costruiscono** dal raccoglitore (un'etichetta di coppia sola).
- Un nome solo della coppia: **`FROM/TO`** (quello di tutti i raccoglitori e della qualità dei dati, che lo divide in
  `_missing_pair_sides`). Il testo di `convert_bulk` (`EUR/USD` = coppia salvata) resta com'è: è un messaggio d'errore
  dell'API, letto da `stretch_conversion.rate_not_found_error` e fissato dai test di parità.

### 5.2 Il predicato dell'età (P-2)

```python
def is_stale_rate(rate_date: date, day: date, threshold_days: int = STALE_PRICE_THRESHOLD_DAYS) -> bool:
    return (day - rate_date).days > threshold_days
```

Lo leggono `daily_state._stale_fx_pair`, `market_series.py:521` e (nella forma «primo giorno vecchio» =
`rate_date + threshold + 1`) `AskedDayRates.stale_turn_days`. Esempio di parità: riga 20/10, soglia 7 → vecchio dal
**28/10** (`20/10 + 8`), come oggi in tutti e tre.
La stessa regola «riga + soglia + 1, salvo un'osservazione più nuova prima» è scritta anche per i **prezzi**, in
`daily_state._stale_turn_days` (`:964-972`): il predicato unico serve a quattro punti, non a tre.

### 5.3 La lettura del risultato (P-3)

`convert_bulk` restituisce una tupla `(Currency, rate_date, bf) | None` che 9 chiamanti spacchettano a mano.
Un lettore solo:

```python
@dataclass(frozen=True, slots=True)
class FxProvenance:
    requested_date: date
    rate_date: date
    @property
    def days_back(self) -> int: ...      # (requested − rate).days, 0 the same day
    @property
    def backward_filled(self) -> bool: ...
```

Lo usano YoC (`YieldOnCostFxProvenance.days_back`), costo medio (`days_back`), eventi (`fx_days_back`), prezzi osservati
(`fx_days_back`), `/fx/convert` (`days_back`). Esempio: richiesto 28/10, riga 20/10 → `days_back = 8`,
`backward_filled = True`; richiesto 20/10, riga 20/10 → `0`, `False`.

### 5.4 Le classi di chiamante (la politica, scritta una volta)

| Classe | Chi | Tasso mancante | Tasso vecchio |
|---|---|---|---|
| **Aggregato** (un numero del report) | 1–6 | valore escluso (`None`) + `MissingFxCollector` → `MISSING_FX_RATES` | sullo stato del giorno di valutazione (`stale_fx_pairs`, motore) — il riepilogo e i lotti leggono il report del motore, non ne fanno uno loro |
| **Serie da mostrare** | 7, 8/9, 17 | punto nativo + errore (testo unico per gli eventi), max 10 | per punto: `fx_rate_date`, `fx_days_back` (`FxProvenance`) |
| **Variazione** | 10–12 | variazione vuota (+ errore dove c'è già) | nessuno |
| **Sonda** | 13 | `fx_available=False` | nessuno (il rischio ha il suo avviso da `market_series`) |
| **AI Export** | 14–16 | modello del contratto | modello del contratto (AIX) |

### 5.5 `STALE_FX`: dove siamo

- **Il dato c'è** (D-P4, ondata 5): `DataQualityReport.stale_fx_pairs`. **Il banner è di Y** in questa ondata
  (`DataQualityBanner.svelte`, 4 lingue). T-U1 aggiunge solo il predicato unico (P-2).
- Non c'è un `IssueCode.STALE_FX` accanto a `STALE_PRICE` (`schemas/portfolio.py:173`): il banner di Y può leggere
  `stale_fx_pairs` direttamente. **Domanda per il developer, solo se Y la pone**: serve anche una voce nella lista dei
  problemi (`issues`) oltre al banner? Consiglio: **no**, il banner basta (stesso dato, una superficie).
- Il riempimento resta illimitato: è la raccomandazione del coordinatore (17/10, «avviso sì, limite no»), messa fra le
  domande del developer; la risposta 18 del 26/10 riguarda solo il banner, e da allora nessuno ha chiesto un limite.

## 6. MF-A13 — il tasso ricavato per divisione, ricontato

Il backlog dice «tre volte». Oggi:

| Dove | Divisione | Stato |
|---|---|---|
| `observed_prices._converted` (`:125`) | `factor = close_convertito / close` → scala O, H, L | **divide** (nato da X5 di T) |
| `market_series.py:169` | `fx_rate = close / native_close` | **divide** |
| `/fx/convert` (`currencies.py:610`) | `rate = to_amount / from_amount` | **divide** (X8 del piano 43) |
| `ai_export/.../asset_resources.py:209` | — | **non divide più**: legge `original_close` e `fx_rate_date` |
| `fx_core.py:515` | `implied_rate` | divide **solo per riconciliare** (tolleranza): resta |

Osservazione: in `resolve_days` i gradini (`steps`) sono già caricati, quindi il tasso del giorno è
`steps[(src, tgt)].at(day)` senza divisione. **Attenzione al bit**: sulle coppie inverse `convert_bulk` fa
`close / rate`, mentre `close × steps.at(day)` = `close × (1 / rate)`: le due differiscono all'ultima delle 28 cifre.
Quindi la cura **non** ricalcola il close (resta quello di `convert_bulk`): porta il tasso sul punto per chi lo legge
(`market_series`, `/fx/convert`) e per scalare O/H/L.

**Piano di misura (prima di qualsiasi codice, con X):** sul DB di prova della corsia (`/tmp/librefolio-r13-o6-mf`),
per ogni punto convertito di ogni asset in valuta estera:
1. `f_div = close_conv / close` (oggi) contro `f_step = steps.at(day)` (proposta);
2. contare i punti con `f_div != f_step`, e a quale cifra differiscono;
3. per O/H/L: `O × f_div` contro `O × f_step`, arrotondati come li mostrano grafico e AI Export (la sonda mirata
   dell'export dice se serve un bump);
4. coppie dirette e inverse separate (mi aspetto 0 differenze sulle dirette, qualcuna all'ultima cifra sulle inverse).

## 7. Lotti che ne nascono (proposta al coordinatore)

| Lotto | Cosa | File | Peso | Quando |
|---|---|---|---|---|
| **T-U1a** | P-1 raccoglitore + P-2 predicato + P-3 lettore nella casa; 2, 3, 4, 5, 6 li usano | `financial_math/fx_rates.py`, `yield_on_cost.py`, `average_cost.py`, `lots/conversions.py`, `lots_analysis_service.py` (`:852`), `native_cash.py`, `portfolio/daily_state.py` | ~0,75 g | con **change-days** (stessi file: `native_cash`, `daily_state`, `lots/conversions`) |
| **T-U1b** | 1 (`_convert_to_base`) e le due chiusure `:362`, `:589` sul raccoglitore | `portfolio_service.py` | ~0,1 g | dentro **MF6-1** (è accanto a `_get_price_at_date`), prima del passaggio ad AIX |
| **T-U1c** | 8 = 9 in una funzione; `market_series:521` sul predicato | X (`price_query`, `event_store`), J (`market_series`) | ~0,25 g | X e J, dopo T-U1a; MF rivede |
| MF-A13 | il tasso sul punto (§6) | X + MF | come da kickoff | punto 11 del kickoff, dopo la misura |

Prove per T-U1a/b: suite `financial-math`, `roi-fifo-utils`, `api portfolio` verdi **senza** cambiare un atteso
(nessun numero cambia); un test nuovo per `MissingFxCollector` (date + intervalli fusi) e `is_stale_rate` (7 giorni no,
8 sì).
