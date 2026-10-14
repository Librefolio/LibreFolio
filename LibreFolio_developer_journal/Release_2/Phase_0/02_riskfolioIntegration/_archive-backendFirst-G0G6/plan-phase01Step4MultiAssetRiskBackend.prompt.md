# Step 4 — Multi-Asset Deterministic Backend (P5 + backend P6-P10)

**Stato**: ✅ COMPLETATO — Gate G4 chiuso il 27 Luglio 2026.

← Step precedente:
[`plan-phase01Step3RollingRiskBackend.prompt.md`](./plan-phase01Step3RollingRiskBackend.prompt.md)

← Master:
[`plan-phase01RiskAnalysisImplementation.prompt.md`](./plan-phase01RiskAnalysisImplementation.prompt.md)

→ Step successivo:
[`plan-phase01Step5SimulationScaleOptimization.prompt.md`](./plan-phase01Step5SimulationScaleOptimization.prompt.md)

## 1. Obiettivo

Completare contratto, matematica deterministica, service e API multi-asset prima
di qualunque UI risk.

## 2. Fondazione

### 4.1 — Schemi risk

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Definire scope/mode/output/status, request union discriminate, catalog definition,
metadata, qualità e risultati serializzabili.

> **Note implementazione**: esteso `schemas/risk.py` con scope discriminati
> `asset`/`asset_set`/`portfolio`/`broker`, query bulk strict, policy
> `current_buy_and_hold`, definizione catalogo, stati/errori machine-readable e
> union discriminata degli output KPI/matrice/PCTR/stress/comparison/VaR-CVaR.
> `RiskResultMetadata` ora dichiara anche lo scope. I risultati di successo
> richiedono output+metadata+qualità; indisponibilità/failure richiedono errore
> esplicito. I test schema coprono serializzazione, discriminatori, duplicate,
> mode/policy e invariante `CVaR >= VaR`; 6 test passati.

### 4.2 — `RiskAnalytic` registry

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Pattern auto-descrittivo riusato dai segnali:

- `code`, `output_kind`, `scopes`, `modes`;
- `params_model`, `min_observations`, `algo_version`;
- compute puro su prepared context.

> **Note implementazione**: aggiunti `RiskAnalytic`, `RiskExecutionContext`,
> `RiskComputation` e `RiskUnavailableError` nel boundary DB-free
> `services/risk/base.py`. Il registry auto-discovering riusa
> `AbstractPluginRegistry`, normalizza codici lowercase, rifiuta duplicati,
> modelli parametri non strict, classi astratte/stateful e import falliti. Il
> catalogo è derivato dal JSON Schema del `params_model`. Aggiunta la cartella
> plugin dedicata `services/risk_plugins/`; 10 test contratto/schema passati.

### 4.3 — `RiskService` bulk

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

- auth/scope resolution;
- un data load;
- un joint calendar;
- più analytics;
- error isolation;
- `asyncio.to_thread` solo per NumPy/pandas light compute.

> **Note implementazione**: aggiunto `RiskService`: risolve e autorizza scope,
> usa una sola `PortfolioService.get_report()` (quindi un solo engine/report) per
> portfolio/broker, aggrega pesi e valori correnti target-currency, carica prezzi
> asset in bulk una volta e costruisce un solo `PreparedAssetSeriesSet` condiviso.
> Il TWRR cumulato del report è riconvertito in rendimenti periodali esatti; la
> modalità corrente applica `current_buy_and_hold`. Registry lookup, scope/mode,
> parametri, history insufficiente, dominio matematico e crash interni sono
> isolati per analytic mantenendo l'ordine richiesto. Broker non accessibile
> fallisce prima del calcolo. I calcoli CPU puri passano da `asyncio.to_thread`;
> nessun plugin accede a DB/FX.
>
> **⚠️ Fuori pista**: NAV con cash negativo/leva o valori asset negativi non può
> essere rappresentato dal contratto long-only/cash-zero della prima ondata:
> gli analytics dipendenti dalla composizione risultano esplicitamente
> `DATA_UNAVAILABLE`, senza normalizzazione silenziosa. Valore in-transit non
> mappabile a una serie asset è dichiarato come residuo zero-return con warning.
>
> **Verifica**: 4 test service coprono singolo scope load/report, pesi+cash,
> estrazione TWRR, auth broker, errori catalogo/scope/parametri e isolamento di un
> crash senza abortire gli altri risultati.

### 4.4 — API risk

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Default:

- `GET /api/v1/risk/catalog`;
- `POST /api/v1/risk/query`.

Rolling asset resta nel contratto segnali.

> **Note implementazione**: aggiunto router autenticato `/risk` con catalogo
> statico e query bulk, dependency-injected `RiskService`, mapping 403 per broker
> non accessibile e 404 per scope asset inesistente. Il router v1 include i nuovi
> endpoint; OpenAPI espone il discriminator `scope.kind` con mapping dei quattro
> scope e la union discriminata degli output. Cinque test ASGI coprono auth,
> catalogo, delega user-aware, mapping errori e 422 prima del service.
>
> **⚠️ Fuori pista**: `openapi-zod-client` perde i metodi `ZodObject` quando una
> variante discriminata è annotata come `z.ZodType<T>`. Esteso il fix post-codegen
> già usato da Signals/AI Export alle quattro varianti scope e ai sei output risk;
> client rigenerato, type-check e build frontend verdi.

## 3. Analytics

> **Fondazione matematica comune — completata 27 Luglio 2026**:
> `services/risk/metrics.py` ora include recupero dei rendimenti periodali da TWRR
> cumulato, wealth/drawdown+durata, Sortino, Pearson/covarianza su calendario
> comune, MCTR/CCTR/PCTR, replay `current_buy_and_hold`, shock ponderati,
> comparison TE/IR/correlazione/beta e historical VaR/CVaR con quantile empirico
> osservato `higher`. Fixture manuali verificano additività PCTR, contributo
> negativo, cash zero, drift buy-and-hold, confronto identico e
> `CVaR >= VaR >= 0`; 12 test matematici/rolling passati.

### 4.5 — KPI portfolio historical

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

TWRR periodale: volatility, max drawdown/duration, Sharpe, Sortino.

> **Note implementazione**: plugin `portfolio_kpi` historical per scope
> portfolio/broker. Consuma esclusivamente rendimenti periodali TWRR, fattore
> osservato e giorni di calendario; espone volatilità, max drawdown negativo,
> durata underwater, Sharpe con `RiskFreeReference` e Sortino con MAR esplicito.
> Deviazioni nulle restano `null` con warning, mai numeri inventati.

### 4.6 — Correlation

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Pearson post-FX, matrice unica, n_obs/coverage per cella, insufficient esplicito.

> **Note implementazione**: plugin `correlation` riusa le serie canoniche
> target-currency sul singolo joint calendar. Ogni cella espone valore,
> osservazioni, coverage e stato `ok|insufficient|undefined`; serie piatte non
> diventano correlazione zero. Soglie minime sono parametri catalogo.

### 4.7 — Risk contribution

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

MCTR/CCTR/PCTR su covarianza comune; pesi correnti; cash/zero-vol = 0;
contributi negativi preservati.

> **Note implementazione**: plugin `risk_contribution` usa una sola matrice di
> covarianza annualizzata e pesi NAV target-currency; cash resta peso a
> rendimento/volatilità zero. Output separa MCTR/CCTR/PCTR. Fixture
> semidefinita verifica `ΣCCTR=σp`, `ΣPCTR=1` e PCTR negativo non troncato.

### 4.8 — Stress

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

- hypothetical deterministico;
- historical replay `current_buy_and_hold`;
- factor shock escluso.

Una definizione scenario, proiezione per scope.

> **Note implementazione**: plugin `stress` con parametri discriminati
> `hypothetical`/`historical_replay`. Gli shock sono input espliciti per asset;
> asset-set restituisce percentuali per strumento senza pesi inventati, mentre
> portfolio/broker proiettano contributo e importo usando pesi/valori correnti.
> Il replay applica esclusivamente `current_buy_and_hold`, senza ribilanciamento.

### 4.9 — Comparison

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Contratti distinti:

- risk-free → excess return/Sharpe;
- comparison asset → active return, TE, IR, correlation, beta, cumulative,
  drawdown comparison.

> **Note implementazione**: il risk-free resta contratto separato e alimenta
> Sharpe; plugin `comparison` accetta solo `comparison_asset_id` reale, allinea
> l'intersezione delle date e produce active return cumulato, TE/IR annualizzati,
> correlazione, beta, curve cumulative e drawdown. Benchmark flat → beta/
> correlazione `null` con warning.

### 4.10 — VaR/CVaR

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Historical simulation default; loss magnitude positiva; horizon esplicito e
rendimenti composti; parametric solo dopo default verde.

> **Note implementazione**: plugin `historical_var` historical-only nel metodo
> (utilizzabile sui due mode di serie) con confidence/horizon espliciti,
> rendimenti multi-osservazione composti e quantile empirico `higher`.
> Perdite clampate a magnitudini non negative; CVaR è media della coda
> `L >= VaR`. Nessun metodo parametrico aggiunto.

> **Verifica analytics 4.5-4.10**: registry scopre 6 plugin; 18 test puri
> registry/matematica/plugin passati, inclusi PCTR negativo, stress %/€, replay
> buy-and-hold, confronto identico e `CVaR >= VaR >= 0`.

## 4. Scope

- asset;
- asset set senza pesi per correlation/stress %;
- portfolio;
- broker subset con pesi e semantica "rischio interno".

`historical` usa TWRR. `current_composition` usa esclusivamente
`current_buy_and_hold`.

## 5. Test matematici

- matrice/covarianza comune;
- correlation simmetrica/diagonale;
- `ΣCCTR=σp`, `ΣPCTR≈100%`;
- PCTR negativo;
- cash zero;
- TE/IR/beta edge;
- comparison identica;
- `CVaR≥VaR≥0`;
- stress %/€ coerenti;
- TWRR cash-flow neutral;
- currency/calendar/quality;
- API bulk/auth/error isolation.

## 6. Gate G4

- ✅ catalog/service/API verdi;
- ✅ analytics P5/P8/P9/P10 deterministiche verdi;
- ✅ backend contracts per P6/P7 pronti;
- ✅ OpenAPI/client sync stabile;
- ✅ nessun frontend risk necessario per validare matematica.

> **Verifica chiusura G4 — 27 Luglio 2026**: suite schema risk, registry,
> matematica, plugin, service e API verdi; il test API `risk` è registrato nel
> runner e include una query reale sul DB test popolato per broker scope,
> `historical` + `current_composition`, coprendo tutti i sei analytics. Verificati
> anche `CVaR >= VaR >= 0` e `ΣPCTR = 1` sul percorso completo
> router → sessione DB → PortfolioService → serie canoniche → plugin. Il client
> OpenAPI è rigenerato; frontend type-check/build verdi; audit i18n con zero chiavi
> backend mancanti dopo l'aggiunta delle 17 label/descrizioni risk EN/IT/FR/ES.
> Review indipendente ad alta confidenza: nessun bug matematico, auth, async o
> schema trovato.
>
> **⚠️ Baseline non bloccante**: lint repository-wide resta rosso su 33 violazioni
> preesistenti in settings/scheduler/ROI test; il format check frontend segnala
> `backendRenderer.ts`, file non modificato dal delta Risk. Il primo run aggregato
> API/backend ha inoltre esposto lock/reset del DB nel runner multi-gruppo; i gruppi
> risk e adiacenti eseguiti isolatamente sono verdi. Questi elementi non alterano
> il gate matematico/API G4 e restano da rivalutare nel gate finale GF.

## 7. Rischi/fallback

- endpoint troppo generico → union discriminate per scope;
- PCTR ritarda → correlation/KPI prima, gate resta chiuso finché PCTR non è verificato;
- historical stress incompleto → hypothetical spedibile, historical dichiarato partial;
- parametric VaR non affidabile → historical-only.

## 8. Progress rule

Dopo ogni task aggiornare stato/data/note/fuori-pista qui e nel master.
