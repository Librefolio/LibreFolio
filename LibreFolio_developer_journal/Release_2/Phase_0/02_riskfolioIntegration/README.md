# Fase 0.1 — Integrazione Risk Analysis (Riskfolio-Lib) · Studio Preliminare

Questa cartella contiene lo studio di alto livello **prima** di scrivere il piano
implementativo della Fase 0.1 (Monte Carlo & Risk Metrics Engine). Lo scopo è
rispondere a una domanda architetturale chiave: *dove* mettere l'analisi del
rischio in LibreFolio e *quanto* di essa può essere reso modulare (stile
"segnali") invece di richiedere una UI ad-hoc ogni volta.

## Documenti

| # | File | Contenuto |
|---|------|-----------|
| 1 | [`analysis-phase01RiskModularityAndPlacement.md`](./analysis-phase01RiskModularityAndPlacement.md) | Analisi architetturale. Tassonomia degli output di rischio, la proposta `RiskAnalytic` plugin + "widget primitives", matrice di posizionamento UI per pagina, cosa implementare / rimandare / evitare, scelta libreria (Riskfolio-Lib vs numpy/pandas leggero) e async safety. |
| 2 | [`brainstorm-phase01RiskUiConcepts.md`](./brainstorm-phase01RiskUiConcepts.md) | Brainstorming visivo. 8 concept UI con **ASCII art** e, per ciascuno, "cosa fa notare all'utente" + costo/valore. Modalità fantasiosa per farsi un'idea concreta. |

## TL;DR delle conclusioni

1. **Il rischio NON è monoliticamente "ad-hoc".** Si scompone in **6 archetipi di
   output** (scalare, serie temporale, distribuzione, cono/fan, matrice, scatter).
   Se rendi modulari i **widget** (non i grafici a linee), la maggior parte delle
   metriche diventa pluggable.
2. **Una intera classe di metriche di rischio È GIÀ un segnale** (rolling
   volatility, drawdown underwater, rolling Sharpe, rolling beta, rendimento
   rolling N-periodi). Vanno aggiunte al sistema `SignalPlugin` esistente → **zero
   UI nuova**, riuso del grafico Asset Detail / FX.
3. Il resto (correlazione, Monte Carlo, stress test, frontiera efficiente) merita
   una **nuova tab "Risk"** a livello di Dashboard e Broker Detail, più una tab
   "Projections" nell'Asset Detail.
4. **Riskfolio-Lib solo dove serve davvero** (ottimizzazione/frontiera, misure di
   rischio avanzate). Per metriche scalari e serie rolling: `numpy`/`pandas`
   leggeri, wrappati in `asyncio.to_thread`.

## Riferimenti

- Roadmap Fase 0/0.1: [`../../Ai_ideas/phase_0_detailed_roadmap.md`](../../Ai_ideas/phase_0_detailed_roadmap.md)
- Roadmap strategica: [`../../Ai_ideas/roadmap_and_signals_brainstorm.md`](../../Ai_ideas/roadmap_and_signals_brainstorm.md)
- Migrazione segnali (Fase 0): [`../01_signalMigration/`](../01_signalMigration/)
- Gallery UI di riferimento: `mkdocs_src/docs/gallery/desktop/en/light/`
