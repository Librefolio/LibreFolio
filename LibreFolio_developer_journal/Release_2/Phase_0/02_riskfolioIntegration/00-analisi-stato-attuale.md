# 00 — Analisi dello stato attuale

**Data**: 16 Settembre 2026
**Metodo**: inventario verificato **sul codice**, non sui documenti di piano.
**Baseline**: `e1f3fe177861d2b9b953b218f66ea7d4714ab405`

> I documenti della prima campagna descrivono lo stato *inteso*. Questo documento
> descrive lo stato *reale*. Dove divergono, vale questo.

---

## 1. Backend — completo, solido, sovradimensionato

### 1.1 Analytics registrati

Nove `RiskAnalytic` in `backend/app/services/risk_plugins/`, tutti auto-registrati
via `@register_plugin(RiskAnalyticRegistry)`:

| Analytic | `analytic_code` | Scope supportati | UI |
|---|---|---|:---:|
| KPI storici (vol, maxDD, durata, Sharpe, Sortino) | `historical_kpi` | asset, portfolio | ✅ |
| Correlazione | `correlation` | asset_set, portfolio | ✅ |
| Contributo al rischio (MCTR/CCTR/PCTR) | `risk_contribution` | **portfolio soltanto** | ✅ |
| VaR / CVaR storici | `historical_var` | asset, portfolio | ✅ |
| Riepilogo drawdown datato | `drawdown_summary` | asset, portfolio | ✅ |
| Confronto con benchmark reale | `comparison` | asset, portfolio | ✅ |
| Stress (shock ipotetico + replay storico) | `stress` | asset, asset_set, portfolio | ✅ |
| Simulazione Monte Carlo / QMC | `simulation` | asset, portfolio | ✅ |
| Ottimizzazione di portafoglio | `portfolio_optimization` | portfolio, asset_set | ❌ |

### 1.2 Segnali rolling di categoria RISK

Sei `SignalPlugin` in `backend/app/services/signal_plugins/`:
`drawdown`, `rolling_volatility`, `rolling_return`, `rolling_sharpe`, `rolling_beta`,
`calendar_rolling_return`.

Consumati oggi nella **Overview di Asset Detail**. Restano dove sono.

### 1.3 Infrastruttura

- Due `SpawnWorkerPool` separati e lazy: `simulation` (QuantLib) e `optimization`
  (Riskfolio/CVXPY), con idle reap, coda bounded, timeout e recycle di lane.
- Cache parent content-keyed con collasso dei miss concorrenti.
- Catalogo scenari YAML typed, caricato allo startup:
  `backend/app/services/risk/scenario_catalog/built_in/` — 9 file
  (4 historical, 4 hypothetical, 1 geography).
- API: `backend/app/api/v1/risk.py`, 3 endpoint (2 GET + 1 POST).
- Nessuna migrazione DB introdotta dalla campagna Risk.

### 1.4 Fatti misurati da conservare

| Misura | Valore |
|---|---|
| Simulazione warm, 1 asset · 1.024 path · 30g MC | 0,071 s |
| Simulazione warm, 5 asset · 4.096 path · 90g QMC | 2,353 s |
| Ottimizzazione cold / warm | 2,863 s / **0,0159 s** |
| Peak RSS ottimizzazione | ~340,6 MB |
| Immagine Docker finale, non compressa | 2.781.625.742 byte |

> Il costo di `portfolio_optimization` **non è la CPU** (0,0159 s warm). Il costo sono
> le dipendenze: Riskfolio-Lib 7.0.1, CVXPY, CLARABEL, SCS e un intero worker pool
> presenti in ogni installazione per una funzione non raggiungibile.
> Quanto pesino davvero sull'immagine **non è mai stato misurato**.

---

## 2. Frontend — fermo al 26% del piano

### 2.1 Inventario

| File | Righe |
|---|---:|
| `frontend/src/lib/components/risk/RiskAnalysisPanel.svelte` | **1.271** |
| `frontend/src/lib/components/risk/riskAnalysisHelpers.test.ts` | 398 |
| `frontend/src/lib/stores/risk/riskStore.test.ts` | 354 |
| `frontend/src/lib/stores/risk/riskStore.svelte.ts` | 194 |
| `frontend/src/lib/components/risk/riskAnalysisHelpers.ts` | 184 |
| `frontend/src/lib/components/risk/AssetSetRiskPanel.svelte` | 173 |
| `frontend/src/lib/risk/riskRequest.ts` | 163 |
| `frontend/src/lib/components/risk/CorrelationHeatmap.svelte` | 124 |
| `frontend/src/lib/components/risk/RiskResultFrame.svelte` | 119 |
| `frontend/src/lib/components/risk/AssetRiskScenariosView.svelte` | 105 |
| `frontend/src/lib/risk/riskTypes.ts` | 42 |
| `frontend/src/lib/components/risk/RiskBetaBanner.svelte` | 11 |
| **Totale** | **3.138** |

**Il 40% del codice frontend Risk sta in un solo file**, che impila in una colonna
verticale: KPI, correlazione, contributo, VaR, confronto, stress, replay e simulazione.

### 2.2 Punti di ingresso

| Route | Componente | Scope |
|---|---|---|
| `(app)/dashboard/+page.svelte:752` | `RiskAnalysisPanel` | portfolio |
| `(app)/brokers/[id]/+page.svelte:592` | `RiskAnalysisPanel` | portfolio + broker_ids |
| `(app)/assets/+page.svelte:1493` | `AssetSetRiskPanel` → `RiskAnalysisPanel` | asset_set |
| `(app)/assets/[id]/+page.svelte:2484` | `AssetRiskScenariosView` → `RiskAnalysisPanel` | asset |

Banner beta (`RiskBetaBanner`) montato in 3 dei 4 ingressi.

### 2.3 Asset Global — contesto aggiornato

`(app)/assets/+page.svelte` ha due tab (`ASSET_TAB_IDS = ['assets', 'correlation']`) e,
dalla consegna F15 round-2, la vista tabellare è **divisa in tre pannelli** discriminati
da `txScope` (riga 98 e 1585-1615):

- `own` — asset posseduti dall'utente;
- `others` — asset posseduti da altri utenti di cui si ha visibilità;
- `analysis` — **asset osservati e non posseduti**.

Il terzo pannello rende il concetto di *laboratorio* già di prima classe nel modello dati.

---

## 3. Stato del piano precedente

`_archive-backendFirst-G0G6/workItems/g6-frontend.md`: catena di **23 work item**,
eseguiti fino al **numero 7**.

| Gate | Stato reale |
|---|---|
| G0 — piano | ✅ |
| G1 — fondamenta quant | ✅ |
| G2 — serie canoniche e metadata | ✅ |
| G3 — rolling risk | ✅ |
| G4 — multi-asset deterministico | ✅ |
| G5 — simulazione, scala, ottimizzazione | ✅ auditato |
| **G6 — applicazione** | **🔴 7/23** |
| GF — chiusura | ⛔ dipendente da G6 |

Item G6 mai eseguiti: Correlation, Scenarios, Allocation, Broker Risk, Dashboard Risk,
Home card, validazione integrata, handoff. L'ultimo item avviato e non concluso è
`H1-R5` — *«rischio osservato automatico»*.

> Il banner beta non è un giudizio sulla qualità dei calcoli: è **il segnaposto di una
> catena di piano interrotta**.

---

## 4. Lacune verificate

| # | Lacuna | Evidenza |
|---|---|---|
| 1 | `portfolio_optimization` non è raggiungibile dalla UI | nessuna occorrenza in `frontend/src/lib/risk`, `components/risk`, `stores/risk` |
| 2 | Asset Detail non può mostrare il contributo al rischio del proprio portafoglio | `RiskContributionAnalytic.supported_scopes = (RiskScopeKind.PORTFOLIO,)` |
| 3 | Asset Global apre con **fino a 100 asset** preselezionati | `AssetSetRiskPanel`, `seedInitialized` → `.slice(0, 100)` |
| 4 | Il filtro broker di Asset Global costruisce solo il **set**, senza pesi, con la stessa etichetta usata in Broker Detail dove i pesi ci sono | `AssetSetRiskPanel.applyBrokerFilter()` |
| 5 | Asset Global è intitolato «Correlation» ma renderizza anche lo stress | `title={$t('risk.analytics.correlation.name')}` |
| 6 | La card rolling di Asset Detail mostra **un solo valore puntuale**, non la forma nel tempo | `AssetRiskScenariosView`, `latestRollingPoint` |
| 7 | `sobol_start_index` è esposto come controllo utente | `RiskAnalysisPanel:1224` |

---

## 5. Cosa resta valido dell'archivio

Da **non** riaprire e da continuare a citare come fonte:

- `contract-phase01RiskMetricsMathematical.md` — annualizzazione osservata, calendario
  congiunto, derivazione dei rendimenti dal TWRR, qualità del dato;
- `report-phase01RiskBackendAuditAndRemediation.md` — architettura dei worker;
- `spike-phase01SimulationAdapters.md` — oracle analitici GBM;
- `benchmark-phase01SimulationScale.md` — misure di prestazione;
- `spike-phase01QuantLibraries.md` — versioni e closure delle dipendenze.

Da considerare **superato**:

- la catena G6 e la sua sequenza di viste;
- la gerarchia di priorità fra le metriche;
- l'information architecture a quattro tab di Assets Global.
