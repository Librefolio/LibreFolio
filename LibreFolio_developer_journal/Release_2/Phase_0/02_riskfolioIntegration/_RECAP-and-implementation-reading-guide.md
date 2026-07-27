# Riepilogo & Prompt di ripresa — Risk Analysis (Fase 0.1)

> **Scopo di questo file.** Punto d'ingresso unico per riprendere il lavoro sulla
> Risk Analysis. Contiene: (1) cosa c'è in questa cartella e in che ordine leggerlo,
> (2) un **prompt di ripresa** copiabile per una nuova sessione, (3) un **suggerimento
> di lettura** in ottica di piano implementativo multi-fase. **Documentale, nessun
> codice.**

---

## 1. Contenuto della cartella (mappa)

| Ordine | File | Cos'è | Righe | Stato |
|--------|------|-------|-------|-------|
| 0 | [`contract-phase01RiskMetricsMathematical.md`](./contract-phase01RiskMetricsMathematical.md) | **Contratto matematico/semantico fondativo.** Serie da consumare (TWRR portafoglio, close asset), annualizzazione osservata (§2.1), calendario congiunto + ultimo prezzo (§2.2), qualità+sync (§2.3), `RiskResultMetadata` (§4), allineamento (§5), schede per-metrica (beta §6.5, PCTR §6.7, VaR/CVaR §6.8, stress §6.10, risk-free/benchmark §6.11), gap `AssetReturnSeries` (§7), dipendenze (§10). | 805 | approvato |
| 1 | [`analysis-phase01RiskModularityAndPlacement.md`](./analysis-phase01RiskModularityAndPlacement.md) | **Spina dorsale architetturale.** Tassonomia output, `RiskAnalytic` vs `SignalPlugin` (§4), utility comune serie (§4.1), inventario riuso backend (§4.2), matrice posizionamento UI (§5), policy libreria/componenti (§7/7.1/7.2), roadmap R0–R9 (§8), conclusione due-binari (§9). | 496 | approvato |
| 2 | [`brainstorm-phase01RiskUiConcepts.md`](./brainstorm-phase01RiskUiConcepts.md) | **Brainstorming visivo.** 9 concept UI (A–I) con ASCII art + «cosa fa notare» + costo/valore; D-bis (Asset Global Correlation), D-ter (asset-centric), E-bis (multi-asset % stress), banner→PageSyncModal. | 553 | approvato |
| 3 | [`review-risk-analysis-feedback.md`](./review-risk-analysis-feedback.md) | **Log decisionale critico** (Capitoli 1–4). 18 osservazioni valutate ACCETTO/CON MODIFICHE/RESPINGO/RIMANDO con evidenza dal codice; Cap. 4 = decisioni review-4 + skeleton del piano. | 851 | approvato |
| 4 | [`plan-phase01RiskAnalysisApplication.prompt.md`](./plan-phase01RiskAnalysisApplication.prompt.md) | **Piano applicativo P0–P13.** Principi, decisioni D1–D12, librerie (QuantLib/Riskfolio in P0, NumPy/SciPy, QMCPy fuori), matrice capability, classificazione invalidazione, step verificabili, test+benchmark, doppio critical path, tracciabilità R0–R9↔P0–P13. | 709 | **da eseguire** |
| — | [`README.md`](./README.md) | Indice + TL;DR + punti decisionali review-2/3/4. | 155 | vivo |
| — | `_RECAP-and-implementation-reading-guide.md` | **Questo file** — riepilogo, prompt di ripresa, guida di lettura. | — | vivo |

**Catena logica:** contratto (*cosa è vero*) → analisi (*dove va nel sistema*) →
brainstorm (*che aspetto ha*) → review (*perché così, cosa scartato*) → piano (*come
costruirlo, in che ordine*).

---

## 2. Decisioni cardine già consolidate (non riaprire)

- **Backend calcola, frontend presenta.** Riuso prima di nuove astrazioni.
- **Due binari:** rolling asset-scoped → `SignalPlugin` (nuova `SignalCategory.RISK`);
  portafoglio/multi-asset → contratto `RiskAnalytic`. Renderer segnali riusato in entrambi.
- **Calcolo sempre giornaliero**; annualizzazione **osservata** `A = N_incl × 365 / D_cal`
  (né 252 né 365 fissi); calendario congiunto + ultimo prezzo (mai forward-fill dei
  rendimenti); `CVaR ≥ VaR ≥ 0`.
- **Rolling beta solo con asset reale** (`comparison_asset` / `comparison_asset_id`);
  nessun benchmark sintetico. Risk-free solo parametro dello Sharpe.
- **Utility comune** di preparazione serie (unico punto, estratta da `SignalService`).
- **Estendere `DataQualityReport`** (qualità sorgente) separato da `RiskResultMetadata`
  (contesto esecuzione).
- **Sync via `PageSyncModal`** (prezzi+FX); la cache portfolio è **content-keyed** →
  auto-invalidante (nessun nuovo sistema di invalidazione).
- **UI:** Correlazione primaria in Asset Global (tab); Dashboard/Broker Risk; stress
  differenziato per scope (% / % multi / €).
- **Librerie:** QuantLib (motore quant/simulazione, adapter) + Riskfolio-Lib (frontiera),
  **entrambe verificate e installate in P0**; NumPy/SciPy base+fallback+RQMC; **QMCPy
  fuori dal piano** (solo fallback futuro). Parallelismo **solo `spawn`**, dopo benchmark.

---

## 3. Prompt di ripresa (copiabile in una nuova sessione)

```text
Contesto: LibreFolio, Fase 0.1 — Risk Analysis. Lo studio è APPROVATO e il piano
applicativo è scritto. Tutti i documenti sono in:
LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/

Leggi in quest'ordine:
1. _RECAP-and-implementation-reading-guide.md  (mappa + decisioni cardine)
2. contract-phase01RiskMetricsMathematical.md  (verità matematica/semantica)
3. analysis-phase01RiskModularityAndPlacement.md (architettura, R0–R9)
4. plan-phase01RiskAnalysisApplication.prompt.md (piano applicativo P0–P13)
Consulta brainstorm-* (UI/ASCII) e review-* (razionale) solo quando servono.

Vincoli non negoziabili (già decisi, NON riaprire):
- backend calcola / frontend presenta; riuso prima di nuove astrazioni;
- due binari: SignalPlugin (rolling, SignalCategory.RISK) vs RiskAnalytic (multi-asset);
- calcolo giornaliero + annualizzazione osservata + calendario congiunto; CVaR≥VaR≥0;
- rolling beta solo con comparison_asset reale; risk-free solo per lo Sharpe;
- utility comune di preparazione serie; DataQualityReport esteso vs RiskResultMetadata;
- sync via PageSyncModal; cache content-keyed (niente nuovo sistema di invalidazione);
- QuantLib + Riskfolio-Lib installate/validate in P0; NumPy/SciPy fallback+RQMC;
  QMCPy fuori dal piano; parallelismo solo spawn e solo dopo benchmark.

Obiettivo di questa sessione: <SCEGLIERE UNA FASE — vedi guida §4 del recap, es.
"Fase A: fondamenta P0+P1+P2">. Per ogni step del piano rispetta i campi
obiettivo/gap/file/contratto/schema/service/frontend/deps/test/migrazione/criteri/
rischi/fallback. Verifica sempre contro il codice reale (evidenza file:linea) prima di
proporre nuovi elementi. Documenta prima di implementare; niente dipendenze/migrazioni/
endpoint finché la fase non lo prevede.
```

---

## 4. Come leggere i documenti per un piano implementativo multi-fase

Il piano ha **13 step (P0–P13)** ma **non vanno eseguiti 1-a-1 in sequenza lineare**.
Il suggerimento è raggrupparli in **fasi di consegna coese**, ciascuna con un valore
utente o un rischio da abbattere. Due percorsi avanzano in parallelo (funzionale vs
librerie quantitative).

```text
                 PERCORSO FUNZIONALE                 PERCORSO LIBRERIE QUANT
                 (valore utente)                     (abbatti rischio infra)

  Fase A ─ Fondamenta      P1 · P2                    P0  (probe+install QuantLib+Riskfolio)
              │                                          │
  Fase B ─ Rolling & UI    P3 · P4 (Asset Detail)        │  (spike simulazione in prep.)
              │                                          │
  Fase C ─ Multi-asset     P5 · P6 · P7                   │
              │            (correlazione/PCTR/KPI)        │
  Fase D ─ Scenari & conf. P8 · P9 · P10                  │
              │            (stress/confronto/VaR)         │
  Fase E ─ Simulazione     ───────────────────────────►  P11 (MC/QMC/RQMC)
              │                                          │
  Fase F ─ Scala & advanced                              P12 (spawn) · P13 (frontiera)
```

### Ordine di lettura consigliato per PIANIFICARE ogni fase

1. **Parti dal `contract-`** per la fase in oggetto: fissa formule, convenzioni,
   metadata e casi limite *prima* di toccare architettura o UI. È la fonte di verità.
2. **Poi `analysis-` §4/§4.1/§4.2 e §5**: decidi *dove* vive il codice (SignalPlugin vs
   RiskAnalytic vs utility) e quali elementi esistenti riusare — evita di reinventare.
3. **Poi la sezione P-corrispondente del `plan-`**: è la checklist operativa (file,
   contratto, service, frontend, test, criteri, rischi, fallback, dipendenze).
4. **`brainstorm-`** solo quando pianifichi la UI di quella fase (ASCII → layout,
   «cosa fa notare all'utente» → priorità dei widget).
5. **`review-`** come corte d'appello: se qualcosa sembra ambiguo, la decisione e il
   razionale sono lì (evita di riaprire scelte già chiuse).

### Fasi suggerite (raggruppamento dei P0–P13)

- **Fase A — Fondamenta invisibili** (`P0` + `P1` + `P2`). Nessuna UI. Sblocca tutto:
  librerie installate/validate, utility serie unica, `DataQualityReport`+metadata.
  *Criterio di uscita:* segnali esistenti invariati; CI verde con le nuove librerie.
- **Fase B — Primo valore utente** (`P3` + `P4`). Rolling risk in Asset Detail
  (drawdown, vol, return, Sharpe, beta con `comparison_asset`). *Criterio:* 5 plugin nel
  catalogo, renderizzati, con warning corretti.
- **Fase C — Vista di portafoglio** (`P5` + `P6` + `P7`). `RiskAnalytic`, correlazione
  in Asset Global, KPI/PCTR in Dashboard e Broker Risk. *Criterio:* heatmap + PCTR +
  KPI storici su TWRR, con qualità dati.
- **Fase D — Scenari e confronto** (`P8` + `P9` + `P10`). Stress per scope, confronto
  risk-free/comparison_asset multi-scope, VaR/CVaR. *Criterio:* uno scenario → output
  %/€; confronto A/B; `CVaR≥VaR≥0`.
- **Fase E — Simulazione** (`P11`). Motore MC/QMC/RQMC componibile dietro adapter, dopo
  lo spike QuantLib vs NumPy/SciPy. *Criterio:* seed deterministico, metriche corrette.
- **Fase F — Scala & advanced** (`P12` + `P13`). Parallelismo `spawn` **solo se i
  benchmark lo giustificano**; frontiera/ottimizzazione con Riskfolio-Lib (opzionale).

### Principi trasversali per ogni fase
- **Spike prima del commitment:** P0 (probe+install) e lo spike simulazione (P11) sono
  cancelli: non progettare adapter contro mock, decidi con evidenza.
- **Ogni nuovo elemento** dichiara gap + alternativa esistente valutata + test di
  non-regressione (principio del piano §0).
- **Tracciabilità:** ogni PR mappa a uno step P e, a ritroso, a un requisito R0–R9
  (tabella in fondo al piano).
- **Confini stabili:** i risultati sono DTO serializzabili; nessun oggetto QuantLib in
  dominio/API; matematica mai nel frontend.

---

## 5. Cosa NON è ancora deciso (rimane ai probe/spike)
Compatibilità QuantLib↔Python 3.13 e wheel nel container (P0) · scrambling/RQMC nel
binding SWIG (P0/P11) · composizione QuantLib+`scipy.stats.qmc` (P11) · peso Docker di
QuantLib e Riskfolio+solver (P0) · soglia per attivare il pool `spawn` (P12) · forma
finale di `comparison_asset_series` (P3) e `AssetReturnSeries` (P1).

---

## Riferimenti
- Indice cartella: [`README.md`](./README.md)
- Piano applicativo: [`plan-phase01RiskAnalysisApplication.prompt.md`](./plan-phase01RiskAnalysisApplication.prompt.md)
