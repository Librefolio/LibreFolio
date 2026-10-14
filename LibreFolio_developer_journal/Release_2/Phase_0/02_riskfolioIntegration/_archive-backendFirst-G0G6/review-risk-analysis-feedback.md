# Review — Risk Analysis Design · Feedback punto-per-punto

> Revisione critica dei documenti di studio della Fase 0.1 (Risk Analysis /
> Riskfolio-Lib) contro il codice reale di LibreFolio. Ogni osservazione è valutata
> con evidenza dal repository, non per compiacenza. **Vincolo:** solo
> documentazione — nessun codice applicativo, nessuna dipendenza, nessuna
> migrazione.

---

## 1. Executive summary

Lo studio originale era architetturalmente valido nell'intuizione (modularizzare i
**widget/renderer**, non i grafici) ma conteneva **quattro errori di sostanza
finanziaria/tecnica** che, se portati in implementazione, avrebbero prodotto
metriche numericamente incoerenti con il resto di LibreFolio:

1. **Serie sbagliata.** Non specificava che il rischio di portafoglio deve partire
   dal **TWRR** (neutro rispetto ai flussi), rischiando di misurare volatilità su
   delta di `nav_value` inquinati da depositi/prelievi.
2. **Annualizzazione a 252.** Il brainstorming assumeva implicitamente la
   convenzione borsistica dei 252 giorni; LibreFolio genera una **serie densa
   giornaliera** e annualizza a **365** (`roi_utils`). 252 sarebbe stato
   internamente incoerente.
3. **"Basta un `category:risk` nei segnali".** Il contratto `SignalPlugin` è
   `ASSET|FX` price-only, senza categoria `risk` né slot per benchmark/risk-free/pesi
   → semanticamente inadatto a metriche di portafoglio.
4. **Gap `AssetReturnSeries` non riconosciuto.** Non esiste una serie canonica di
   rendimenti per-asset convertiti in valuta: è il **prerequisito** di correlazione,
   beta e risk-contribution, e va costruito come estensione, non pipeline parallela.

**Esito:** delle 18 osservazioni, **14 ACCETTATE** e **4 ACCETTATE CON MODIFICHE**,
**0 respinte**. Le "modifiche" non indeboliscono le osservazioni: le correggono
verso la realtà del codice (es. la direzione dell'annualizzazione è giusta, ma il
numero corretto è 365, non 252; il riuso dei segnali è giusto a livello di
*renderer*, non di *dominio*). È stato creato un documento fondativo separato
(`contract-phase01RiskMetricsMathematical.md`) e aggiornati analisi, brainstorming
e README.

---

## 2. File analizzati (documenti dello studio)

| File | Stato |
|------|-------|
| `contract-phase01RiskMetricsMathematical.md` | **NUOVO** — contratto matematico/semantico fondativo |
| `analysis-phase01RiskModularityAndPlacement.md` | aggiornato in profondità (§3–§9 + roadmap R0–R9) |
| `brainstorm-phase01RiskUiConcepts.md` | aggiornato (Concept A/B/C/D/E/F/H + info architecture + tabella priorità) |
| `README.md` | aggiornato (indice, TL;DR revisionato, vincolo) |
| `review-risk-analysis-feedback.md` | **NUOVO** — questo report |

---

## 3. Componenti del repository ispezionati (evidenza)

| Area | File:riga | Fatto stabilito |
|------|-----------|-----------------|
| Annualizzazione | `backend/app/utils/financial/roi_utils.py:80,92` | `annualized_to_cumulative` usa `(1+r)^(days/365)-1` → **base 365** |
| Serie densa | `backend/app/services/portfolio_engine.py:435,983` | serie **per giorno di calendario**, forward-fill dei giorni non-dirty |
| TWRR | `roi_utils.py:207` (`calculate_twrr_series`), `schemas/portfolio.py:444` (`PortfolioHistoryPoint.twrr`) | serie TWRR **già esistente**, cashflow-neutral |
| Flussi di cassa | `portfolio_engine.py:227,1473` (`build_performance_inputs`, negazione segno) | depositi/prelievi separati via `external_cash_flows` |
| Tipo di rendimento | `roi_utils.py:191` | rendimenti **semplici/HPR**, non log; nessuna serie total-return |
| Dividendi | `portfolio_engine.py:840` | dividendi = income/cashflow, **non** reinvestiti nel prezzo |
| FX | `services/fx.py` (`convert_bulk`), `db/models.py` (`FxRate`) | conversione nel service layer per-data; engine senza I/O FX; backward-fill → `RateNotFoundError` |
| Contratto segnali | `schemas/signals.py:149-176,238-278` | `SignalDomain=ASSET|FX`; `SignalCategory=TREND|MOMENTUM|VOLATILITY|VOLUME` (**no risk**); input price_fields+events |
| Provenienza segnali | `schemas/signals.py` | `SignalStatus`, `SignalAvailabilityReason`, `SignalWarningCode`, `SignalWarmupMetadata`, `SignalExecutionContext.target_currency` |
| Data-quality | `schemas/portfolio.py:224` (`DataQualityReport`) | issues/severity/incomplete_nav_dates già modellati |
| Async | `services/signal_service.py:260` | compute segnali in `asyncio.to_thread`; nessun process pool nel repo |
| Renderer | `frontend/.../backendRenderer.ts`, `LineChart` | renderer temporale riusabile indipendente dal dominio |
| Scope | `portfolio_engine.py` (`broker_ids: list[int]|None`) | subset calcolabile ma "interno al subset" |

---

## 4. Matrice delle 18 decisioni

| # | Osservazione (sintesi) | Decisione |
|---|------------------------|-----------|
| 1 | Manca contratto matematico/semantico | **ACCETTO** |
| 2 | Definire la serie finanziaria analizzata | **ACCETTO** |
| 3 | Rischio storico realizzato ≠ composizione corrente | **ACCETTO** |
| 4 | La valuta target modifica il rischio, non solo la vista | **ACCETTO** |
| 5 | Frequenza/calendario/annualizzazione deterministici | **ACCETTO CON MODIFICHE** (365, non 252) |
| 6 | Correlazione/beta richiedono data-alignment esplicito | **ACCETTO** |
| 7 | Ogni risultato con provenance + data-quality metadata | **ACCETTO** |
| 8 | Riuso SignalPlugin: ok graficamente, rivalutare semanticamente | **ACCETTO CON MODIFICHE** (riuso renderer, non dominio) |
| 9 | Il contributo al rischio va definito matematicamente | **ACCETTO** |
| 10 | VaR/CVaR: esplicitare metodo, orizzonte, interpretazione | **ACCETTO** |
| 11 | Sharpe/Sortino/beta: parametri espliciti | **ACCETTO** |
| 12 | Monte Carlo = scenario condizionato, non previsione | **ACCETTO** |
| 13 | Lo stress test dovrebbe precedere il Monte Carlo | **ACCETTO** |
| 14 | Frontiera efficiente e Riskfolio-Lib opzionali | **ACCETTO** |
| 15 | Scope broker ≠ rischio complessivo | **ACCETTO** |
| 16 | Evitare un singolo punteggio opaco di rischio | **ACCETTO** |
| 17 | La Risk tab deve guidare, non accumulare grafici | **ACCETTO** |
| 18 | Async safety e strategia di esecuzione | **ACCETTO CON MODIFICHE** (to_thread ok per leggere; MC/opt → process pool) |

Riepilogo: **14 ACCETTO · 4 ACCETTO CON MODIFICHE · 0 REJECT · 0 DEFER.**

---

## 5. Motivazione dettagliata di ogni decisione

### #1 — Contratto matematico/semantico · ACCETTO
- **Evidenza:** i documenti classificavano gli output in archetipi grafici ma non
  definivano quale serie/formula/convenzione usare; il codice ha invece convenzioni
  precise (365, TWRR, HPR) che vanno rispettate.
- **Razionale:** senza un contratto, ogni metrica rischierebbe una convenzione
  diversa → numeri non confrontabili tra widget.
- **Conseguenza architetturale:** creato `contract-phase01RiskMetricsMathematical.md`
  come **fondamento** referenziato da tutti gli altri documenti.
- **Roadmap:** diventa lo step **R0** (precondizione di tutto).
- **Rischi:** nessuno; riduce il rischio di incoerenza.
- **Modifica:** documento nuovo completo (§0–§10).

### #2 — Serie finanziaria analizzata · ACCETTO
- **Evidenza:** `PortfolioHistoryPoint.twrr` (`schemas/portfolio.py:444`),
  `calculate_twrr_series` (`roi_utils.py:207`), separazione flussi
  (`portfolio_engine.py:227,1473`).
- **Razionale:** misurare volatilità su delta di `nav_value` mescolerebbe
  rendimento di mercato e movimenti di cassa → metrica priva di significato.
- **Conseguenza:** il contratto §1/§1.1 impone: **portafoglio → TWRR**; **asset →
  serie close** (con nota sull'asimmetria dividendi).
- **Roadmap:** abilita la modalità `historical` **senza nuovo backend** (il TWRR
  esiste già).
- **Rischi:** asimmetria dividendi (prezzo asset esclude income) → da dichiarare.
- **Modifica:** contratto §1, README TL;DR #1.

### #3 — Historical vs current_composition · ACCETTO
- **Evidenza:** engine ricostruisce i pesi storici reali; nessuna struttura applica
  pesi correnti a rendimenti passati.
- **Razionale:** sono due domande diverse ("che rischio ho corso" vs "che rischio
  avrei con l'allocazione di oggi"); confonderle inganna l'utente.
- **Conseguenza:** `historical` usa il TWRR esistente (subito); `current_composition`
  richiede `AssetReturnSeries`.
- **Roadmap:** `historical` prima, `current_composition` seconda ondata.
- **Rischi:** current_composition ignora i costi di ribilanciamento → etichettare come
  ipotetico.
- **Modifica:** contratto §3, README TL;DR #5.

### #4 — La valuta modifica il rischio · ACCETTO
- **Evidenza:** `convert_bulk` per-data nel service (`fx.py`); NAV/TWRR già in valuta
  target; nessun concetto di strumento currency-hedged.
- **Razionale:** la volatilità in EUR di un asset USD include la volatilità EUR/USD;
  è rischio reale per l'investitore, non presentazione.
- **Conseguenza:** ogni risultato dichiara la valuta; `AssetReturnSeries` deve
  calcolare i rendimenti **dopo** conversione, riusando l'FX del service.
- **Roadmap:** vincola il design di R1 (AssetReturnSeries in valuta).
- **Rischi:** FX mancante → backward-fill/staleness da propagare nei metadata.
- **Modifica:** contratto §7, brainstorming Concept D (nota "post-conversione").

### #5 — Frequenza/calendario/annualizzazione · ACCETTO CON MODIFICHE
- **Parte corretta:** serve una convenzione deterministica dichiarata.
- **Parte corretta solo in parte:** l'ipotesi implicita di 252 giorni. **Evidenza
  contraria:** `roi_utils.py:80,92` annualizza a **365**; l'engine produce una serie
  **per giorno di calendario** (`portfolio_engine.py:435,983`). Usare 252 sarebbe
  incoerente con il resto di LibreFolio.
- **Conseguenza:** volatilità annualizzata con **√365**; convenzione unica nel
  contratto §2.1.
- **Roadmap:** nessun ritardo; è una scelta di costante.
- **Rischi:** i valori risulteranno leggermente diversi dai tool che usano 252 → da
  spiegare nella UI/help.
- **Modifica:** contratto §2.1, README TL;DR #2.

### #6 — Data alignment correlazione/beta · ACCETTO
- **Evidenza:** nessuna serie per-asset canonica oggi → l'allineamento va definito
  esplicitamente prima di calcolare qualsiasi matrice.
- **Razionale:** una heatmap "precisa" su serie non comparabili è fuorviante.
- **Conseguenza:** contratto §5: **intersezione** delle date (no union), niente
  forward-fill dei rendimenti, `n` minimo di osservazioni, celle sotto-soglia marcate
  (`n<20`), copertura dichiarata.
- **Roadmap:** dipende da R1.
- **Rischi:** intersezione riduce il campione con asset di storia breve → esclusioni
  elencate.
- **Modifica:** contratto §5, brainstorming Concept D (footer con `n`, copertura).

### #7 — Provenance + data-quality metadata · ACCETTO
- **Evidenza:** pattern già esistenti — `SignalStatus`, `SignalWarningCode`,
  `SignalWarmupMetadata` (`schemas/signals.py`), `DataQualityReport`
  (`schemas/portfolio.py:224`).
- **Razionale:** coerenza con la natura auditabile di LibreFolio; non reinventare.
- **Conseguenza:** `RiskResultMetadata` **estende** questi pattern (finestra, valuta,
  n osservazioni, missing FX, staleness, warning).
- **Roadmap:** trasversale a tutte le metriche.
- **Rischi:** nessuno; riduce rischio di risultati "muti".
- **Modifica:** contratto §4, README TL;DR #7.

### #8 — Riuso SignalPlugin · ACCETTO CON MODIFICHE
- **Parte corretta:** riusare il **renderer** temporale (`backendRenderer.ts`) per
  drawdown/rolling vol/rolling Sharpe.
- **Parte da correggere:** trattarlo come estensione del **dominio** segnali.
  **Evidenza:** `SignalDomain=ASSET|FX` (no portfolio), `SignalCategory` senza
  `risk`, input solo price_fields+events → nessuno slot per benchmark/risk-free/pesi
  (`schemas/signals.py:149-176`).
- **Conseguenza:** contratto separato `RiskAnalytic`; solo 3 metriche price-only
  asset-scoped (drawdown, rolling vol, rolling return) *potrebbero* essere plugin
  estendendo `SignalCategory`.
- **Roadmap:** i "quick win" price-only restano vicini ai segnali; il resto passa da
  RiskAnalytic.
- **Rischi:** forzare tutto nei segnali avrebbe corrotto il contratto segnali.
- **Modifica:** analisi §3/§4, brainstorming Concept C, README TL;DR #4.

### #9 — Contributo al rischio definito matematicamente · ACCETTO
- **Evidenza:** il brainstorming usava "38% del rischio" senza formula.
- **Razionale:** "quota di rischio" è ambigua; serve la definizione formale.
- **Conseguenza:** contratto §6.7: `MCTR_i=(Σw)_i/σ_p`, `CCTR_i=w_i·MCTR_i` (somma a
  σ_p), **`PCTR_i=CCTR_i/σ_p`** (somma 100%). "X% del rischio" = **PCTR**. Cash/vol
  nulla = 0; contributi negativi mostrati; short fuori scope.
- **Roadmap:** risk-contribution (PCTR) **prima** del Monte Carlo.
- **Rischi:** dipende da `AssetReturnSeries` + pesi.
- **Modifica:** contratto §6.7, brainstorming Concept F (PCTR, casi limite).

### #10 — VaR/CVaR metodo/orizzonte · ACCETTO
- **Evidenza:** nessuna implementazione esistente → definizione libera dei parametri.
- **Razionale:** VaR/CVaR non sono "perdita massima"; senza metodo/orizzonte sono
  ingannevoli.
- **Conseguenza:** contratto §6.8: metodo (historical/parametrico), livello (95/99),
  orizzonte, interpretazione esplicita ("perdita superata con prob. α"), CVaR come
  media della coda.
- **Roadmap:** dopo risk-contribution, insieme/prima del Monte Carlo.
- **Rischi:** falsa percezione di limite → wording obbligato nella UI.
- **Modifica:** contratto §6.8.

### #11 — Sharpe/Sortino/beta parametri · ACCETTO
- **Evidenza:** rendimenti HPR (`roi_utils.py:191`), annualizzazione 365, TWRR per
  portafoglio.
- **Razionale:** senza risk-free e benchmark espliciti i ratio non sono confrontabili.
- **Conseguenza:** contratto §6 (schede): rf dichiarato e annualizzato coerente a 365;
  beta/Sortino con benchmark e MAR espliciti; Sharpe su rendimento eccedente.
- **Roadmap:** Sharpe rolling è un quick win price-only; beta dipende da benchmark +
  AssetReturnSeries.
- **Rischi:** scelta del benchmark → configurabile, non hard-coded.
- **Modifica:** contratto §6, brainstorming Concept C (Sharpe "non fortuna vs bravura").

### #12 — Monte Carlo come scenario condizionato · ACCETTO
- **Evidenza:** nessuna simulazione esistente; alto rischio di falsa precisione.
- **Razionale:** un fan chart sembra una previsione; va inquadrato come "distribuzione
  simulata sotto assunzioni".
- **Conseguenza:** rinominata la tab Asset "Projections" → **"Risk & Scenarios"**;
  label "simulato", seed mostrato, assunzioni (modello, drift, n path) visibili,
  guardrail testuali.
- **Roadmap:** scende di priorità (dopo stress test).
- **Rischi:** interpretazione deterministica da parte dell'utente → guardrail.
- **Modifica:** analisi §5, brainstorming Concept B, contratto §6.9.

### #13 — Stress test prima del Monte Carlo · ACCETTO
- **Evidenza:** lo stress test è deterministico e auditabile; il Monte Carlo no.
- **Razionale:** più comprensibile e verificabile per l'utente.
- **Conseguenza:** tre famiglie (historical replay / hypothetical shock / factor
  shock), ognuna con **assunzioni visibili** (es. «tassi +200bps → bond −8%» = input).
- **Roadmap:** stress test = R6, Monte Carlo = R8.
- **Rischi:** dataset scenari da curare.
- **Modifica:** contratto §6.10, brainstorming Concept E, tabella priorità.

### #14 — Frontiera/Riskfolio-Lib opzionali · ACCETTO
- **Evidenza:** Riskfolio-Lib introduce cvxpy e ottimizzazione; il resto delle
  metriche si fa con numpy/pandas.
- **Razionale:** evitare una dipendenza pesante e raccomandazioni imperative per una
  feature avanzata.
- **Conseguenza:** frontiera in accordion "Advanced", collassata, con disclaimer; mai
  imperativa.
- **Roadmap:** R9 opzionale.
- **Rischi:** estimation error → disclaimer obbligato.
- **Modifica:** analisi §6, brainstorming Concept G.

### #15 — Scope broker ≠ rischio totale · ACCETTO
- **Evidenza:** engine accetta `broker_ids: list[int]|None` → subset calcolabile, ma
  è "rischio interno al subset".
- **Razionale:** il rischio di un broker non è il rischio del patrimonio (mancano
  correlazioni cross-broker).
- **Conseguenza:** avviso esplicito nella Risk tab del Broker Detail ("scope: questo
  broker, non l'intero patrimonio").
- **Roadmap:** nessun impatto; è wording/UX.
- **Rischi:** interpretazione errata → nota in UI.
- **Modifica:** analisi §5 (matrice posizionamento).

### #16 — Nessun punteggio opaco · ACCETTO
- **Evidenza:** il brainstorming introduceva una banda qualitativa/indice di
  diversificazione sintetico.
- **Razionale:** un singolo "voto di rischio" nasconde le assunzioni e induce falsa
  fiducia.
- **Conseguenza:** rimosso lo score opaco; la KPI strip mostra metriche **con
  metadata** (finestra, valuta), non un giudizio.
- **Roadmap:** nessun impatto.
- **Rischi:** nessuno.
- **Modifica:** brainstorming Concept A/H.

### #17 — La Risk tab deve guidare · ACCETTO
- **Evidenza:** gli archetipi (S/T/D/C/M/F) sono utili al rendering, non alla
  comprensione.
- **Razionale:** una tab ordinata per tipo di grafico non risponde a domande.
- **Conseguenza:** information architecture per **domande progressive** (instabilità →
  peggiore perdita → concentrazione → diversificazione → scenari → simulazione),
  storico/osservabile prima del simulato.
- **Roadmap:** guida l'ordine visivo, non le dipendenze tecniche.
- **Rischi:** nessuno.
- **Modifica:** brainstorming (sezione "Information architecture").

### #18 — Async safety · ACCETTO CON MODIFICHE
- **Parte corretta:** i calcoli sono CPU-bound e non devono bloccare l'event loop.
- **Da precisare:** `asyncio.to_thread` (già usato in `signal_service.py:260`) è
  sufficiente per metriche leggere, ma **non** per Monte Carlo/ottimizzazione (GIL) →
  servono **process pool + timeout + limiti + cache**, oggi **assenti** nel repo.
- **Conseguenza:** contratto §9 distingue i due regimi di esecuzione.
- **Roadmap:** il process pool è precondizione di R8/R9, non di R2–R6.
- **Rischi:** senza limiti, un MC pesante potrebbe saturare CPU.
- **Modifica:** analisi §7, contratto §9, README TL;DR #9.

---

## 6. Modifiche effettuate, file per file

### `contract-phase01RiskMetricsMathematical.md` (NUOVO)
- §0 principio "consumare, non reimplementare"; §1 tassonomia serie mappata al codice
  + §1.1 regola di selezione serie (TWRR portafoglio / close asset); §2 `ReturnSeriesSpec`
  + §2.1 annualizzazione 365 con evidenza; §3 modalità historical/current_composition;
  §4 `RiskResultMetadata`; §5 data-alignment correlazione; §6 schede per-metrica
  (6.7 MCTR/CCTR/PCTR, 6.8 VaR/CVaR, 6.9 Monte Carlo, 6.10 stress); §7 valuta +
  gap `AssetReturnSeries`; §8 guardrail interpretativi; §9 async; §10 mermaid dipendenze.

### `analysis-phase01RiskModularityAndPlacement.md`
- §3 chiarito `RiskAnalytic` ≠ `SignalPlugin`; §4 correzione maggiore (evidenza
  `SignalDomain`/`SignalCategory`, riuso renderer non dominio); §5 matrice
  posizionamento (tab "Risk & Scenarios", avviso subset-scope broker); §6 libreria
  ripriorizzata; §7 async (to_thread vs process pool); §8 roadmap **R0–R9** (R1 =
  `AssetReturnSeries` collo di bottiglia); §9 conclusione. Link a contratto + review.

### `brainstorm-phase01RiskUiConcepts.md`
- Concept A: rimosso score opaco, KPI con metadata; B: tab rinominata, MC
  "simulato"/seed/guardrail; C: riuso renderer non dominio, Sharpe non "fortuna vs
  bravura"; D: data-alignment (intersezione, `n`, copertura, post-conversione FX);
  E: tre famiglie di stress con assunzioni visibili; F: "38% del rischio" → **PCTR**
  con casi limite (cash=0, negativi, somma 100%); H: wording TWRR; aggiunta sezione
  **information architecture**; tabella priorità riordinata (F/E prima di B/G) con
  colonna dipendenze e mappatura R2–R9.

### `README.md`
- Indice esteso (contratto #0, review #3); TL;DR riscritto (9 punti revisionati: TWRR,
  365, archetipi, renderer-non-dominio, due modalità, `AssetReturnSeries`, metadata,
  priorità, async); aggiunto il vincolo "solo documentazione".

---

## 7. Proposte rigettate e motivo

Nessuna delle 18 osservazioni è stata respinta. Sono stati invece **rigettati
elementi dei documenti originali** (auto-revisione), perché in conflitto con il
codice reale:

1. **"Aggiungere `category:risk` ai segnali."** *Rigettato* — `SignalCategory` non
   include risk e `SignalDomain` è `ASSET|FX` price-only senza slot per
   benchmark/risk-free/pesi (`schemas/signals.py:149-176`). *Alternativa:* riuso del
   solo renderer + contratto separato `RiskAnalytic`.
2. **Annualizzazione a 252.** *Rigettata* — incoerente con la base 365 di
   `roi_utils.py:80,92` e con la serie densa giornaliera. *Alternativa:* √365.
3. **Volatilità su delta di `nav_value`.** *Rigettata implicitamente* — inquinata dai
   flussi. *Alternativa:* TWRR (`schemas/portfolio.py:444`).
4. **Singolo punteggio/banda di rischio opaco (Concept A originale).** *Rigettato* —
   nasconde le assunzioni (osservazione #16). *Alternativa:* metriche con metadata.
5. **"Una sola scommessa" / "38% del rischio" senza formula.** *Rigettati* come
   wording fuorviante. *Alternativa:* PCTR formale (contratto §6.7).

---

## 8. Questioni rimaste aperte

1. **Definizione operativa di `AssetReturnSeries`** (granularità, gestione buchi,
   punto esatto di conversione FX rispetto al calcolo del rendimento). Decisione in
   fase di piano R1.
2. **Scelta del/dei benchmark** per beta/frontiera (indice per valuta? configurabile
   dall'utente?). Serve una policy di prodotto.
3. **Risk-free source**: costante manuale vs curva per valuta vs provider. Nessuna
   sorgente rf esiste oggi nel repo.
4. **Asimmetria dividendi**: se/quando introdurre una serie total-return per gli asset
   (oggi i dividendi sono cashflow, non nel prezzo — `portfolio_engine.py:840`).
5. **Limiti del process pool** (numero worker, timeout, dimensione cache) per Monte
   Carlo/ottimizzazione: da dimensionare in R8.
6. **Short/leverage** nel risk-contribution: attualmente fuori scope; da decidere se
   supportarli.

---

## 9. Nuova roadmap consigliata

| Step | Contenuto | Dipende da | Backend nuovo? |
|------|-----------|-----------|----------------|
| **R0** | Contratto matematico (questo studio) | — | no (doc) |
| **R1** | `AssetReturnSeries` (rendimenti per-asset in valuta, riuso FX) | R0 | sì (estensione) |
| **R2** | Metriche price-only asset-scoped via renderer segnali (drawdown, rolling vol, rolling return) | R0 | minimo |
| **R3** | Risk KPI strip + Risk tab contenitore (modalità `historical` su TWRR) | R0 | no (usa TWRR) |
| **R4** | Correlation matrix | R1 | sì |
| **R5** | Risk contribution PCTR (barre divergenti) | R1 + pesi | sì |
| **R6** | Stress test (hypothetical shock prima; 3 famiglie con deps distinte) | R0/R1 (+scenari) | sì |
| **R7** | Confronto risk-free/asset (`RiskFreeReference` vs `ComparisonBenchmark`) | R1 | sì |
| **R8** | VaR/CVaR (segno positivo) + Monte Carlo (process pool + seed + guardrail) | R1 + process pool | sì (infra) |
| **R9** | Frontiera efficiente (Riskfolio-Lib, opzionale) | R1–R8 | sì (dipendenza opz.) |

> Aggiornamento review-2: inserito il **confronto risk-free/asset a R7**; VaR/CVaR e
> Monte Carlo confluiscono in **R8**; R5 usa **barre divergenti** (non treemap).

Cambiamento chiave rispetto allo studio originale: **risk contribution (R5) e stress
test (R6) precedono il Monte Carlo (R8)**; `AssetReturnSeries` (R1) è il collo di
bottiglia esplicito.

---

## 10. Rischi tecnici e finanziari

**Finanziari**
- Interpretazione di VaR/CVaR come perdita massima → mitigato da wording obbligato
  (§6.8).
- Monte Carlo percepito come previsione → label "simulato" + assunzioni + seed (§6.9).
- Correlazioni su serie corte/non allineate → intersezione date + `n` minimo + celle
  marcate (§5).
- Numeri diversi da tool a **252 giorni fissi** → con il fattore osservato (review-3
  §2.1) i valori equity si riavvicinano ai tool a 252; spiegare comunque `A` in help.
- Risk-contribution scambiato per "peso" → PCTR con caveat "peso ≠ rischio".

**Tecnici**
- Monte Carlo/ottimizzazione bloccanti → process pool + timeout + cache (assenti oggi).
- FX mancante/stale non propagato → `RiskResultMetadata` con missing_fx/staleness.
- `AssetReturnSeries` come pipeline parallela → imporre riuso del layer FX/prezzi.
- Subset broker interpretato come rischio totale → avviso di scope in UI.

---

## 11. Controlli/test necessari nella futura implementazione

- **Coerenza annualizzazione:** test che verifichi il **fattore osservato**
  `A = oss.incluse × 365 / giorni-calendario` (review-3 §2.1) — non un `√365` fisso —
  e la sua coerenza con `annualized_to_cumulative` (`roi_utils.py`) sulla base
  giorni-di-calendario; verificare che `A → ~252` per un asset equity e `~365` per un
  asset 24/7 sullo stesso periodo.
- **Calendario congiunto:** giorno incluso se ≥1 asset ha nuova quotazione (altri con
  ultimo prezzo → rendimento derivato, eventualmente zero); giorno escluso se nessuno
  ha nuova quotazione; asset senza alcun prezzo → escluso; **mai** ffill dei rendimenti.
  Metadati `data_quality_status`/`carried_forward_price_points` popolati (review-3 §1).
- **Neutralità ai flussi:** deposito/prelievo non deve alterare la volatilità TWRR
  (property test con cashflow sintetici).
- **Risk-contribution:** `Σ CCTR_i == σ_p` e `Σ PCTR_i == 100%` entro tolleranza;
  cash/vol-nulla → 0; contributi negativi ammessi.
- **Data alignment correlazione:** calendario congiunto, esclusione sotto-soglia,
  copertura riportata; covarianza/PCTR su un **unico** calendario; diagonale = 1.
- **VaR/CVaR:** `CVaR ≥ VaR ≥ 0` (magnitudini positive di perdita, review-2 §6) per lo
  stesso α/orizzonte/metodo/campione; coerenza historical vs parametrico su dati noti.
- **FX:** metriche invarianti al cambio di valuta *solo* dove atteso; propagazione di
  missing/staleness nei metadata.
- **Async:** metriche leggere non bloccano l'event loop (`to_thread`); MC rispetta
  timeout e non satura i worker.
- **Provenienza:** ogni risultato espone finestra, valuta, `n`, `annualization_factor`,
  warning, esclusioni.

---

## 12. Differenze tra documentazione aggiornata e comportamento corrente del codice

Queste sono **estensioni proposte**, non ancora implementate (lo studio è
documentale):

| Documentato | Stato nel codice |
|-------------|------------------|
| `AssetReturnSeries` (rendimenti per-asset in valuta) | **Non esiste** — oggi il per-asset è lot/position-based (`lots_analysis_service`), non price-return |
| `RiskAnalytic` (contratto separato dai segnali) | **Non esiste** — solo `SignalPlugin` (`schemas/signals.py`) |
| `RiskResultMetadata` | **Non esiste** — esistono pattern analoghi da estendere (`SignalStatus`, `DataQualityReport`) |
| `SignalCategory` esteso con metriche price-only di rischio | **Non esteso** — categorie attuali: TREND/MOMENTUM/VOLATILITY/VOLUME |
| Process pool per MC/ottimizzazione | **Non esiste** — solo `asyncio.to_thread` |
| Tab "Risk & Scenarios" / Risk tab | **Non esistono** — UI attuale senza sezione rischio |
| Serie total-return per asset (dividendi nel prezzo) | **Non esiste** — dividendi come cashflow (`portfolio_engine.py:840`) |

**Coerente con il codice attuale (nessuna modifica richiesta):** uso del TWRR
esistente (`schemas/portfolio.py:444`), annualizzazione 365 (`roi_utils.py:80,92`),
FX nel service layer (`fx.py`), esecuzione in `to_thread` (`signal_service.py:260`).

---

# Capitolo 2 — Seconda revisione (review-2): raffinamenti su serie, comparazione e UI

> Seconda passata critica focalizzata su determinismo delle serie, estrazione
> matematica dei rendimenti, pipeline `AssetReturnSeries`, politica dei pesi,
> visualizzazione del contributo al rischio, convenzione VaR/CVaR, famiglie di
> stress, confronto risk-free/benchmark, total-return e frontiera. Verificata contro
> nuovo codice: `calculate_twrr_series` (`roi_utils.py:207-245`) e i componenti
> frontend `PerformanceChart.svelte`, `backendRenderer.ts`, `AssetSearchAutocomplete.svelte`,
> `AssetComparisonSignal.ts`, `ExposureTreemap.svelte`.

## A. Matrice delle decisioni (10 osservazioni)

| # | Osservazione (sintesi) | Decisione |
|---|------------------------|-----------|
| 1 | Calcoli sempre giornalieri; aggregazione solo visuale | **ACCEPT WITH CHANGES** (rimossa configurabilità frequenza/annualizzazione) |
| 2 | Estrazione rendimenti dalla TWRR cumulativa | **ACCEPT** |
| 3 | Definizione operativa `AssetReturnSeries` + split valorizzazione | **ACCEPT** |
| 4 | Politica dei pesi in `current_composition` | **ACCEPT** (`current_buy_and_hold` in 1ª impl.) |
| 5 | Risk contribution → barre divergenti, non treemap | **ACCEPT** |
| 6 | Convenzione segno VaR/CVaR = magnitudini positive | **ACCEPT** |
| 7 | Stress test: tre famiglie con dipendenze distinte | **ACCEPT** |
| 8 | Risk-free sintetico vs asset reale, contratti distinti | **ACCEPT** |
| 9 | Wording total-return/income | **ACCEPT** |
| 10 | Wording frontiera efficiente condizionato | **ACCEPT** |

Riepilogo: **9 ACCEPT · 1 ACCEPT WITH CHANGES · 0 REJECT · 0 DEFER.**

## B. Motivazione per decisione

**#1 Calcoli sempre giornalieri · ACCEPT WITH CHANGES**
- *Evidenza:* motore denso giornaliero (`portfolio_engine.py:435,983`), annualizzazione
  365 (`roi_utils.py:80,92`). *Modifica:* rimossi `frequency`/`resample_rule`/fattore
  configurabile dalla 1ª impl. (configurabilità prematura); fissati *daily · 365*.
- *Conseguenza matematica:* nessuna seconda frequenza implicita; nei multi-asset i
  giorni senza nuova quotazione sono **esclusi** dall'intersezione, **non** trattati
  come rendimento nullo (eviterebbero di gonfiare la stabilità). Mai ffill dei rendimenti.
- *UI:* downsampling = solo disegno; tooltip/metadati dichiarano "calcolo giornaliero".
- *Roadmap:* nessun ritardo; semplifica `ReturnSeriesSpec`.

> ⚠️ **Aggiornato in Capitolo 3 (review-3):** il calcolo resta giornaliero, ma (a)
> l'annualizzazione **non** è più un `365` fisso bensì il **fattore osservato** `A`
> (§2.1); (b) la regola multi-asset cambia: il giorno è **incluso** se ≥1 asset ha
> una nuova quotazione (gli altri valorizzati con l'ultimo prezzo, rendimento
> derivato eventualmente zero) ed **escluso** solo se **nessuno** ha nuova quotazione
> — superando l'esclusione-all'intersezione descritta qui.

**#2 Estrazione dalla TWRR · ACCEPT**
- *Evidenza:* `calculate_twrr_series` costruisce `compound=Π(1+hpr)` e salva
  `TWRR_t=compound−1` (`roi_utils.py:242`). *Matematica:* `r_t=(1+TWRR_t)/(1+TWRR_{t-1})−1
  = hpr_t`; `W_t=1+TWRR_t`. Coincide col motore, non re-derivazione.
- *Cautela:* TWRR cumulativa **quantizzata** → derivare dall'HPR di sotto-periodo, non
  differenziando cumulative arrotondate. Casi `v_start=0`/nessuna variazione → `r_t=0`.

**#3 `AssetReturnSeries` + split · ACCEPT**
- *Evidenza:* FX per-data nel service (`convert_bulk`); nessuna serie rendimento
  per-asset canonica. *Decisione:* pipeline `P^native ×FX → P^target → r`; conversione
  sul **prezzo**, non sul rendimento. Split `AssetValuationSeries` (prezzo convertito +
  provenance) vs `AssetReturnSeries` (rendimenti derivati). Nessun ffill di rendimenti.
- *Roadmap:* resta il collo di bottiglia R1.

**#4 Politica pesi `current_composition` · ACCEPT**
- *Evidenza:* nessun motore di ribilanciamento sintetico nel progetto. *Decisione:*
  `current_buy_and_hold` in 1ª impl. (no transazioni/costi/tasse simulati); politica
  **obbligatoria** nei metadati; `constant_weight`/`periodic_rebalance` = evoluzioni.

**#5 Barre divergenti, non treemap · ACCEPT**
- *Evidenza:* `ExposureTreemap.svelte` dimensiona per `current_value` (≥0); il PCTR può
  essere negativo. Esiste già un diverging bar chart (`PerformanceChart.svelte`, asse a
  zero `markLine{xAxis:0}`) e il renderer supporta `bar` (`backendRenderer.ts`,
  `buildBarSeries`). *Decisione:* riuso della **primitive** di barra divergente + adapter
  PCTR; **non** riuso di `PerformanceChart` così com'è (stacked-multi-componente).
- *UI/roadmap:* aggiornati Concept F, matrice posizionamento, tabella priorità, R5.

**#6 Segno VaR/CVaR · ACCEPT**
- *Matematica:* `L=−R`, `VaR_α=Q_α(L)`, `CVaR_α=E[L|L≥VaR_α]`, `CVaR≥VaR≥0`. Payload =
  magnitudine positiva; segno negativo = solo presentazione. Test indipendenti dal segno.

**#7 Stress: tre famiglie · ACCEPT**
- *Evidenza:* nessun factor-exposure model nel repo. *Decisione:* hypothetical shock
  primo (deterministico); historical replay dipende da `AssetReturnSeries`+pesi+policy;
  factor shock = evoluzione (serve modello di esposizione); shock per categoria ≠ analisi
  fattoriale. R6 non è un blocco omogeneo.

**#8 Risk-free vs asset reale · ACCEPT**
- *Evidenza:* esistono `AssetSearchAutocomplete.svelte` e `AssetComparisonSignal.ts`
  (keyed `assetId`) + dropdown "Comparison". *Decisione:* Modalità A `RiskFreeReference`
  (sintetico, varianza nulla, `rf_daily=(1+rf)^(1/365)−1`, alimenta Sharpe) vs Modalità B
  `ComparisonBenchmark` (active return, TE, IR, beta). Contratti **distinti**; nessun
  `benchmark_or_risk_free` unico; nessun asset reale trattato come risk-free; FX come
  fattore valutario con direzione esplicita. Nuovo Concept I.

**#9 Total return / income · ACCEPT**
- *Evidenza:* dividendi come cashflow (`portfolio_engine.py:840`), nessuna serie
  total-return. *Wording:* «price-only non rappresenta il rendimento totale; può
  sottostimare e alterare volatilità/drawdown». `return_basis` sempre propagato; confronti
  price-only = **parziali**. Non blocca R1 (parte price-only con basis esplicito).

**#10 Frontiera efficiente · ACCEPT**
- *Wording:* rimossi «ottimo»/«potresti ottenere…»; sostituiti con «massimo Sharpe
  **stimato nel campione**» e dipendenza esplicita da campione/finestra/stime/covarianza/
  vincoli/modello/estimation error. ASCII aggiornata.

## C. File modificati (review-2)

| File | Sezioni | Decisioni recepite |
|------|---------|--------------------|
| `contract-...md` | §1.2 (total-return), §1.3 (estrazione TWRR **nuova**), §2/§2.0/§2.1/§2.2 (daily-only, calendari), §3.1 (policy pesi **nuova**), §4 (metadata: policy, return_basis), §6.7 (barre), §6.8 (segno VaR), §6.10 (stress deps), §6.11 (confronto **nuova**), §8 (guardrail 9–10) | 1–10 |
| `analysis-...md` | §3 (primitives: DivergingBarChart/ComparisonPanel), §5 (matrice: barre, confronto), §6 (barre, stress deps, confronto), §8 (roadmap R5 barre, R6 stress, R7 confronto, R8 VaR+MC) | 5,7,8,9 |
| `brainstorm-...md` | Concept F (treemap→barre), Concept G (frontiera wording), Concept I (**nuovo** confronto), info architecture (7 domande), tabella priorità (I=R7, F=barre) | 5,8,10 |
| `README.md` | TL;DR precisazioni 10–19 | 1–10 |
| `review-...md` | questo Capitolo 2 | 1–10 |

## D. Questioni ancora aperte (review-2)

1. **Nomenclatura definitiva** `AssetValuationSeries`/`AssetReturnSeries` — da allineare
   alle convenzioni di naming del progetto in fase di piano R1.
2. **Sorgente del tasso risk-free** oltre l'input manuale (curva per valuta?) — resta
   aperta (nessuna sorgente rf nel repo); la baseline sintetica input-utente è sufficiente
   per la 1ª impl.
3. **Serie total-return per asset** (income/cedole nel prezzo) — richiede prodotto dati
   non ancora disponibile; `return_basis:total_return` previsto ma non producibile.
4. **Factor exposure model** per il factor shock rigoroso — richiede implementazione
   dedicata (evoluzione).
5. **Livello di estrazione della primitive** di barra divergente (nuovo componente
   generico vs adattamento) — da decidere in fase implementativa osservando se
   `PerformanceChart` è generalizzabile senza astrazione fragile.

## E. Controlli di coerenza eseguiti (review-2)

Comandi e wording verificati nella sezione **"Controlli finali"** in coda al documento.
In sintesi: nessun termine stale non intenzionale; PCTR non più associato alla treemap;
il grafico a barre è tra le primitive; il confronto risk-free/asset è nell'information
architecture; le dipendenze dei tre stress sono distinte; frequenza matematica = daily,
aggregazione = solo visuale; `AssetReturnSeries` precede ogni comparazione multi-asset;
il confronto obbligazionario espone la limitazione cedole; l'FX è fattore valutario;
nessun asset reale è "risk-free"; Sharpe ≠ Information Ratio; nessun benchmark hard-coded;
il tasso sintetico ha varianza nulla.

## F. Struttura del prossimo piano applicativo (proposta, non ancora implementazione)

Allo studio riallineato può seguire il piano `plan-phase01Step1RiskEngineFoundation`:
1. **R0** — formalizzare in codice `ReturnSeriesSpec` (daily + **fattore osservato**
   §2.1), `RiskResultMetadata` (+ qualità dati §2.3), `RiskMode`/policy, estrazione
   rendimenti TWRR (test §1.3).
2. **R1** — `AssetValuationSeries`/`AssetReturnSeries` come estensione del price/FX layer.
3. **R2–R3** — drawdown/rolling vol via renderer segnali + KPI card.
4. **R4–R5** — correlazione + risk contribution (barre divergenti).
5. **R6–R7** — stress (hypothetical) + confronto (risk-free/benchmark).
6. **R8–R9** — VaR/CVaR + Monte Carlo; frontiera opzionale.
Ogni step con i controlli/test della sezione §11 del Capitolo 1.

---

## Controlli finali (review-2) — comandi ed esito

Eseguiti nella cartella `Phase_0/02_riskfolioIntegration/`:

| Controllo | Comando (sintesi) | Esito |
|-----------|-------------------|-------|
| Treemap non più primaria per il rischio | `grep -i treemap *.md` | ✅ tutte le occorrenze sono negazioni/storico o riuso per valore; nessuna associa PCTR alla treemap |
| Nessun asset reale = risk-free | `grep -i "…risk-free"` | ✅ solo negazioni esplicite (ETF/BTP/obbligazione/FX «NON risk-free») |
| Wording assertivo frontiera rimosso | `grep "★ ottimo\|potresti ottenere il tuo\|meno rischio possibile"` | ✅ nessun match |
| Frequenza configurabile rimossa | `grep "frequency.*weekly.*monthly\|resample_rule"` | ✅ nessun match residuo |
| Cross-link relativi | `grep -oE "]\(\./…\)"` | ✅ i 5 target esistono tutti |
| Markdown linter disponibile | `command -v markdownlint mdl` | ⚠️ **assente** nel repo → nessun lint eseguibile |

Coerenza tra documenti verificata: il grafico a barre divergente è tra le primitive
(analisi §3, brainstorm Concept F); il confronto risk-free/asset è
nell'information architecture (brainstorm) e nella matrice di posizionamento
(analisi §5); le dipendenze dei tre stress sono distinte (contratto §6.10, analisi
§6); la frequenza matematica è dichiarata giornaliera e l'aggregazione come solo
visuale (contratto §2.0); `AssetReturnSeries` precede ogni comparazione multi-asset
(roadmap R1 < R4/R5); il tasso sintetico ha varianza nulla (contratto §6.11);
Sharpe e Information Ratio restano metriche distinte; nessun benchmark hard-coded.

---

# Capitolo 3 — Correzione finale (review-3)

> Terza passata: rifinitura di calendario, prezzi mancanti e **annualizzazione
> osservata**, con eliminazione dei residui della vecchia politica di frequenza.
> Documentale, nessun codice/dipendenza/migrazione. Alcune decisioni di questa
> passata **superano** esplicitamente formulazioni di review-2 (vedi sotto).

## 3.A Decisioni applicate

| # | Tema | Decisione |
|---|------|-----------|
| 1 | Calcolo giornaliero | Confermato daily-only; nessuna frequenza alternativa configurabile; l'aggregazione dei grafici resta **solo visuale** |
| 2 | Calendario congiunto | Giorno **incluso** se ≥1 asset ha nuova quotazione (altri = ultimo prezzo disponibile); **escluso** se nessuno; asset senza alcun prezzo → **escluso** (parziale). **Supera review-2 §2.2** |
| 3 | Ultimo prezzo ≠ ffill rendimento | Si mantiene il **prezzo**, poi si deriva il rendimento (può essere zero); **mai** ffill dei rendimenti |
| 4 | Annualizzazione **osservata** | `A = oss.incluse × 365 / giorni-calendario`, `σ_ann = σ·√A`; deterministica, nei metadati, uguale per tutte le metriche sullo stesso calendario. Elimina il `√365` fisso |
| 5 | Qualità dati = warning | `data_quality_status` (`ok|carried_forward|partial`); nessun banner se il giorno è escluso perché nessuno ha nuova quotazione; warning ordinario per ultimo-prezzo, grave per asset escluso |
| 6 | Sincronizzazione | Banner con «Sincronizza prezzi» che **riusa il refresh esistente**; il Risk Engine non scarica prezzi né corregge il DB |
| 7 | Stress | Rimossa la dipendenza `correlazione → factor shock`; hypothetical prima, historical replay su `AssetReturnSeries`+pesi, factor shock richiede factor exposure model (assente) |
| 8 | VaR/CVaR | Corretto il test futuro obsoleto `CVaR ≤ VaR` → **`CVaR ≥ VaR ≥ 0`** (magnitudini positive) |
| 9 | Tassonomia widget | Barre divergenti = **primitive aggiuntiva** `DB` oltre ai 6 archetipi S/T/D/C/M/F; distinta dal *Concept B* (Monte Carlo); concept UI = **9** (A–I) |
| 10 | Risk-free vs fattore osservato | Ribadito: `r_{f,daily}=(1+r_{f,annual})^(1/365)−1` su **giorni di calendario**, distinto dal fattore osservativo `A` |

## 3.B File modificati (review-3)

| File | Sezioni aggiornate |
|------|--------------------|
| `contract-...md` | §2 (spec: `joint_calendar`/`carry_forward_price`, annualization derivato), §2.1 (**annualizzazione osservata**, riscritta), §2.2 (**calendario congiunto**, riscritta, supera review-2), §2.3 (**nuova**: qualità dati + confine sync), §4 (metadata: `calendar_days`/`annualization_factor`/`assets_with_missing_prices`/`carried_forward_price_points`/`data_quality_status`), §5 (allineamento = calendario congiunto), §6 header + §6.1 (`√A`), §6.11 (rf su giorni calendario, nota), §7.1 (per-point `valuation_date`/`effective_price_date`/`is_carried_forward`; regola giorni), §9 (fattore osservato), §10 (mermaid: rimosso `COR→ST factor`, aggiunte 3 famiglie stress + FEM) |
| `analysis-...md` | §3 (primitive `DivergingBarChart`=`DB` aggiuntiva + `DataQualityBanner`; nota tassonomia), §5 (matrice: `DB (barre)`), §6 (**nuova** sezione trasversale banner qualità), §9 (6 archetipi + 2 primitive aggiuntive) |
| `brainstorm-...md` | Concept A (ASCII `ann.√A obs` + nota annualizzazione), info-architecture (**nuovo** elemento trasversale banner qualità con ASCII, ribadito 9 concept) |
| `README.md` | riga doc contratto (annualizzazione osservata), riga brainstorm (**9 concept**), TL;DR punto 2 (osservata), **nuova** sezione "Precisazioni 3ª revisione" (punti 20–24) |
| `review-...md` | §10 (nota 252 fissi), §11 (test annualizzazione osservata, calendario congiunto, **`CVaR ≥ VaR ≥ 0`**), §F (R0 daily+osservato), **questo Capitolo 3** |

## 3.C Incoerenze eliminate

- `annualization_factor: SEMPRE 365` / `√365` fisso → **fattore osservato** `A`.
- `alignment: intersection` + `Union+ffill opt-in` + «serie ricampionate alla stessa
  frequency» → **calendario congiunto** unico.
- «giorni senza nuova quotazione esclusi dall'intersezione, mai rendimento nullo»
  (review-2 §2.2) → giorno incluso se ≥1 asset ha nuova quotazione, altri con ultimo
  prezzo (rendimento derivato, eventualmente zero).
- `COR → ST[Stress test factor-based]` nel diagramma del contratto → rimosso.
- `CVaR ≤ VaR` nei test futuri → `CVaR ≥ VaR ≥ 0`.
- `archetipo B` per le barre (collisione con Concept B) → primitive `DB`.
- «8 concept» nel README → **9 concept** (A–I).

## 3.D Questioni ancora aperte (non riaperte da questo prompt)

- Nomenclatura definitiva `AssetValuationSeries`/`AssetReturnSeries` da allineare ai
  nomi reali del price layer in fase di piano.
- Sorgente e valuta del risk-free sintetico (config vs per-utente).
- Serie total-return per asset (income/cedole) — abilita confronti non parziali.
- Factor exposure model per il factor shock — assente, evoluzione successiva.
- Livello di estrazione della primitive barra divergente (riuso diretto vs adapter).

## 3.E Esito dei controlli finali (review-3)

| Controllo | Esito |
|-----------|-------|
| Termini stale (`√365 fisso`, `resample_rule`, `union`, `ffill rendimenti`, `CVaR ≤ VaR`, `correlation→factor`, `8 concept`) | ✅ nessun residuo non intenzionale; restano solo negazioni/storico |
| Annualizzazione | ✅ `A = N_incluse × 365 / D_calendar` in contratto §2.1, metadati §4, test §11, README |
| Calendario congiunto / carried-forward | ✅ contratto §2.2/§5/§7.1 coerenti; distinzione prezzo vs ffill-rendimento esplicita |
| Stress deps | ✅ nessun `correlazione → factor shock`; mermaid contratto §10 e roadmap R6 allineati |
| VaR/CVaR | ✅ `CVaR ≥ VaR ≥ 0` in contratto §6.8, analisi §6, review §11 |
| Cross-link relativi | ✅ i target esistono |
| Roadmap R0–R9 | ✅ identica in analisi §8, brainstorm priorità, review §F |
| Markdown linter | ⚠️ **assente** nel repo (`command -v markdownlint mdl`) → nessun lint eseguibile |

## 3.F Stato

Con queste correzioni non emergono ulteriori incompatibilità macroscopiche tra
contratto matematico, analisi, brainstorming, roadmap, test futuri e README. Lo
studio è **pronto per la scrittura del piano applicativo** (`plan-phase01Step1…`),
che **non** è ancora stato scritto e non introduce codice in questa fase.

---

# Capitolo 4 — Cleanup, riuso e piccole estensioni (review-4)

> Quarta passata: dallo studio finanziario (consolidato) all'**allineamento
> architetturale**. Ogni proposta verificata contro il **codice reale** (4 agent di
> esplorazione + ispezione diretta dell'ambiente). Principio: **riuso e piccole
> estensioni prima di nuove astrazioni**. Documentale, nessun codice/dipendenza/migrazione.

## 4.A Decisioni applicate

| # | Tema | Decisione | Evidenza |
|---|------|-----------|----------|
| 1 | Binario plugin | Rolling **asset-scoped** → `SignalPlugin` con estensioni minori; **portafoglio/multi-asset** → `RiskAnalytic` | `base.py:31-83`, `signal_service.py:118-1026`, `signals.py:93-96` |
| 2 | Sharpe | risk-free = **param scalare** del plugin, nessun cambio framework | `params_model` scalari `base.py:43`, `ema.py:37-63` |
| 3 | Beta | unica rolling con **serie secondaria dichiarata**: slot assente oggi → estensione di `SignalInputRequirements`/`SignalExecutionContext` + orchestrazione `SignalService` | `signals.py:303-318,260-273` (nessuno slot) |
| 4 | Beta ≠ risk-free | baseline varianza nulla → `var=0` → beta indefinito; solo benchmark variabili | contratto §6.5 |
| 5 | Utility comune | preparazione serie in **service layer** (non nei plugin): risolve serie/valuta/calendario congiunto/carried-forward/rendimenti/fattore osservato/qualità | `signal_service.py:793-1026` (coverage già lì), `fx.py:1225-1411` (`convert_bulk`) |
| 6 | Metadata | `data_quality_status`/`excluded_assets` **non** esistono in `DataQualityReport` → aggiungerli; qualità include **FX** carried-forward | `portfolio.py:224-239`, `fx.py:1395-1398` |
| 7 | Correlazione | un solo contratto; **casa primaria Asset Global** (2ª tab "Correlation", asset-centrica); broker = solo SET di asset | `assets/+page` (no tab), `PageToolbar.svelte:36-38,254-256` (tabs), `TabBar.svelte` |
| 8 | Stress per scope | 1 definizione scenario → Asset Detail % · Asset Global % multi · Dashboard/Broker € | contratto §6.10 |
| 9 | Sync | riusa **`PageSyncModal`** (prezzi+FX già supportati), preselezione, avvio manuale, invalidazione a carico pagina | `PageSyncModal.svelte:27-135`, `SyncModalBase.svelte`, `assets/+page:365-377` |
| 10 | Monte Carlo | nessuna lib MC installata (no Riskfolio/cvxpy; TA-lib senza simboli MC) → **GBM vettorizzato numpy/scipy**; process pool solo dopo benchmark | ambiente: `numpy 2.5.0`/`scipy 1.18.0`; web: Riskfolio non fa MC forward |
| 11 | Policy riuso | librerie e componenti UI: gerarchia riuso→estensione→nuovo; nomi semantici ≠ nomi classe | analisi §7.1/§7.2 |

## 4.B Componenti riusati (evidenza)

- **Backend:** `SignalPlugin` ABC + registry (`base.py`, `provider_registry.py:280-450`);
  coverage/availability/warmup (`signal_service.py:793-1026`); `convert_bulk`
  (`fx.py:1225-1411`); `PortfolioHistoryPoint.twrr`/`DailyPortfolioState`
  (`portfolio_engine.py:560-568,1049-1121`); `DataQualityReport`
  (`portfolio.py:224-239`); refresh prezzi/FX (`asset_source.bulk_refresh_prices`,
  `fx.sync_pairs_bulk`).
- **Frontend:** `PageToolbar`+`TabBar` (tab); `PageSyncModal`/`SyncModalBase`
  (sync prezzi+FX); `DataQualityBanner.svelte` (già esistente); `KpiCard.svelte`;
  `PerformanceChart.svelte`/`buildBarSeries` (barre divergenti); `LineChart.svelte`
  (band = cono MC, overlay renderer segnali); `AssetSearchAutocomplete.svelte`
  (confronto/aggiunta asset); `Tooltip.svelte` (prop `math` per KaTeX).

## 4.C Estensioni necessarie (piccole, mirate)

1. valore `SignalCategory.RISK` (o riuso `VOLATILITY`) — enum;
2. slot **serie secondaria** in `SignalInputRequirements`/`SignalExecutionContext` +
   orchestrazione `SignalService` (solo beta/confronto);
3. `data_quality_status`/`excluded_assets` in `DataQualityReport` (o `RiskResultMetadata`);
4. serie canonica **`AssetReturnSeries`** (gap §7, sopra `convert_bulk`+prezzi) —
   sblocca multi-asset;
5. **Asset Global → tab** (oggi senza tab): innesto su `PageToolbar`/`TabBar`;
6. **multi-select asset** (oggi `AssetSelect` è single-select) per il SET di correlazione;
7. **CorrelationHeatmap.svelte** (nessun componente heatmap esistente) — unico widget
   davvero nuovo;
8. **GBM vettorizzato** numpy/scipy nel service layer (nessuna nuova dipendenza).

## 4.D Proposte respinte / ridimensionate

- **Riskfolio-Lib per il Monte Carlo:** respinta — la libreria **non** fa simulazione
  forward (solo ottimizzazione convessa su matrice fornita) e non è installata; il MC
  resta numpy/scipy. Riskfolio-Lib rilevante **solo** per la frontiera (R9, opzionale).
- **Process pool a priori per il MC:** respinto senza benchmark; partire vettorizzato
  in `asyncio.to_thread`.
- **RiskAnalytic anche per le rolling asset:** ridimensionato — sovra-ingegnerizzato
  rispetto al riuso del `SignalPlugin` per lo scope asset.
- **`benchmark_or_risk_free` unico campo / risk-free come benchmark del beta:** respinti
  (semantica ambigua; beta indefinito).
- **Preparazione serie nei plugin:** respinta — deve stare nel service layer condiviso.

## 4.E Questioni ancora aperte (solo ciò che il codice non decide)

- Se `SignalCategory.RISK` sia un nuovo valore o un riuso di `VOLATILITY` — scelta di
  naming/UX da confermare in fase di piano.
- Forma esatta dello slot "serie secondaria" (campo dedicato vs lista dipendenze) e
  suo impatto sul catalogo segnali.
- Collocazione di `data_quality_status`/`excluded_assets` (estendere `DataQualityReport`
  vs nuovo `RiskResultMetadata`) — decisione di schema in fase di piano.
- Parametri di benchmark del Monte Carlo (n. path × asset × orizzonte) prima di
  decidere `to_thread` vs process pool.
- Nomenclatura definitiva `AssetReturnSeries` allineata ai nomi reali del price layer.
- Invalidazione cache FX/portfolio dopo refresh: oggi non esplicita fuori da
  `asset_source` (`fx.py`/`portfolio_engine.py` TTL-only) → verificare in fase di piano.

## 4.F Esito dei controlli finali (review-4)

| Controllo | Esito |
|-----------|-------|
| Dipendenze MC verificate (ambiente) | ✅ `numpy 2.5.0`/`pandas 3.0.3`/`scipy 1.18.0`/`ta-lib 0.7.1`/`pandas-ta-classic 0.6.52`; ❌ Riskfolio-Lib/cvxpy assenti; TA-lib senza simboli MC |
| Supporto MC riusabile | ✅ `numpy.random.Generator.multivariate_normal` + `scipy.stats.multivariate_normal/norm` presenti |
| Riuso sync prezzi+FX | ✅ `PageSyncModal` già combina asset+FX (`PageSyncModal.svelte:27-135`) |
| Banner qualità dati | ✅ `DataQualityBanner.svelte` già esistente |
| Tab Asset Global | ✅ fattibile via `PageToolbar`/`TabBar` (oggi Asset Global senza tab) |
| Boundary plugin/RiskAnalytic | ✅ coerente in analisi §3/§4/§9, brainstorm C, README p.4/25 |
| Cross-link relativi | ✅ target esistenti |
| Roadmap R0–R9 | ✅ invariata; il pivot non cambia l'ordine, solo il *binario* delle rolling asset |
| Markdown linter | ⚠️ **assente** nel repo → nessun lint eseguibile |

## 4.G Stato

Le proposte di review-4 risultano **coerenti col codice reale** e si traducono in
**riuso + piccole estensioni**, senza nuove astrazioni non necessarie. Non emergono
decisioni bloccanti. Lo studio è **pronto per la scrittura del piano applicativo**
(`plan-phase01Step1…`), che **non** è ancora scritto e non introduce codice in questa
fase. Struttura proposta del piano: vedi §4.H.

## 4.H Struttura del prossimo piano applicativo (proposta, non implementazione)

1. **Prerequisiti backend** — utility comune di preparazione serie (§4.1);
   `AssetReturnSeries` canonica; estensione `DataQualityReport`.
2. **Estensioni contratto segnali** — `SignalCategory.RISK`; slot serie secondaria +
   orchestrazione `SignalService` (per beta).
3. **Metriche rolling asset (SignalPlugin)** — drawdown, rolling vol, rolling return
   (price-only, subito); rolling Sharpe (param rf); rolling beta (serie secondaria).
4. **RiskAnalytic (scope portafoglio/multi-asset)** — correlazione (contratto unico),
   PCTR (barre divergenti), poi VaR/CVaR, stress (hypothetical→historical), Monte Carlo.
5. **UI** — Asset Global tab "Correlation" (+multi-select asset, +broker set, +add
   manuale); `CorrelationHeatmap.svelte` (nuovo); riuso `PageSyncModal`/`DataQualityBanner`;
   stress per scope; cono MC su band `LineChart`.
6. **Frontiera efficiente (R9, opzionale)** — install Riskfolio-Lib **solo** qui.
7. Ogni step: contratto → test → UI, con `RiskResultMetadata` sempre popolato.

---

## Riferimenti incrociati

- Contratto matematico: [`contract-phase01RiskMetricsMathematical.md`](./contract-phase01RiskMetricsMathematical.md)
- Analisi architetturale: [`analysis-phase01RiskModularityAndPlacement.md`](./analysis-phase01RiskModularityAndPlacement.md)
- Brainstorming UI: [`brainstorm-phase01RiskUiConcepts.md`](./brainstorm-phase01RiskUiConcepts.md)
- Indice: [`README.md`](./README.md)
