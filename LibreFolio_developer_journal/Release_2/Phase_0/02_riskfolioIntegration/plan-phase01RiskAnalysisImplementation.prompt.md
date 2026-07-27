# Piano Implementativo — Risk Analysis (Fase 0.1)

**Stato**: 🟡 IN ESECUZIONE — Gate G0-G3 chiusi; Step 4 avviato (4.1 completato).

**Data avvio**: 27 Luglio 2026

← Piano applicativo:
[`plan-phase01RiskAnalysisApplication.prompt.md`](./plan-phase01RiskAnalysisApplication.prompt.md)

## 1. Obiettivo

Eseguire integralmente il piano P0–P13 con ordine backend-first:

```text
P0 dipendenze quantitative
    ↓
P1-P2 serie canoniche + metadata
    ↓
P3-P4 rolling risk backend
    ↓
P5-P10 multi-asset deterministico + API
    ↓
P11-P13 simulazione / scala / frontiera
    ↓
frontend funzionale minimo
    ↓
verifica integrata + knowledge layer
```

Nessuna matematica vive nel frontend. Nessuna fase UI inizia prima dei gate
backend applicabili.

## 2. Baseline autoritativa

La worktree corrente, anche sporca, è la baseline. I file target contengono lavoro
precedente non necessariamente committato:

- non ripristinare né sovrascrivere modifiche esistenti;
- leggere sempre il diff reale prima di modificare un file;
- integrare il nuovo lavoro sullo stato corrente;
- fermarsi solo se compare un conflitto diretto non risolvibile senza una scelta
  dell'utente.

## 3. Decisioni vincolanti

1. Backend calcola, frontend presenta.
2. Rolling asset-scoped → `SignalPlugin`.
3. Multi-asset/portfolio → `RiskAnalytic`.
4. Unica utility service-layer per preparare serie.
5. Frequenza matematica sempre giornaliera.
6. Annualizzazione osservata `A = N_included × 365 / D_calendar`.
7. Conversione prezzo prima del rendimento.
8. Calendario congiunto; carry-forward prezzo, mai rendimento.
9. Beta solo contro asset reale variabile.
10. `DataQualityReport` = qualità sorgente; `RiskResultMetadata` = contesto calcolo.
11. Cache eventuale content-keyed; nessun nuovo sistema di invalidazione.
12. QuantLib/Riskfolio adottati solo dopo probe reale.
13. QuantLib mai concorrente in thread; isolamento `spawn`.
14. P12 scala a più worker solo con benchmark.
15. P13 resta capability condizionata al gate Riskfolio.
16. UI: wiring, i18n, stati, render e test funzionali; niente polish/gallery.
17. Nessuna migrazione DB prevista.
18. Nessun `git commit`, push o history rewrite.

## 4. Sub-plan

| Step | File | P-map | Stato |
|---|---|---|---|
| 1 | [`plan-phase01Step1QuantFoundation.prompt.md`](./plan-phase01Step1QuantFoundation.prompt.md) | P0 | ✅ G1 |
| 2 | [`plan-phase01Step2CanonicalSeriesMetadata.prompt.md`](./plan-phase01Step2CanonicalSeriesMetadata.prompt.md) | P1-P2 | ✅ G2 |
| 3 | [`plan-phase01Step3RollingRiskBackend.prompt.md`](./plan-phase01Step3RollingRiskBackend.prompt.md) | P3-P4 backend | ✅ G3 |
| 4 | [`plan-phase01Step4MultiAssetRiskBackend.prompt.md`](./plan-phase01Step4MultiAssetRiskBackend.prompt.md) | P5 + backend P6-P10 | ⏳ |
| 5 | [`plan-phase01Step5SimulationScaleOptimization.prompt.md`](./plan-phase01Step5SimulationScaleOptimization.prompt.md) | P11-P13 | ⏳ P11-P12 · 🚫 P13 |
| 6 | [`plan-phase01Step6RiskFrontendIntegration.prompt.md`](./plan-phase01Step6RiskFrontendIntegration.prompt.md) | UI P4/P6-P13 | ⏳ |

> **Note implementazione G1/G3 — 27 Luglio 2026**: QuantLib 1.43 è importabile
> nell'immagine LibreFolio finale; Riskfolio/P13 restano esclusi. I cinque rolling
> risk sono completi dal caricamento bulk alla UI metadata-driven: client sync,
> categoria Risk, picker asset persistito, request gating, EN/IT/FR/ES ed E2E
> funzionale. Nessuna matematica è stata aggiunta al frontend.

## 5. Convenzioni di esecuzione

Per ogni task:

1. segnare `IN CORSO`;
2. rileggere file e diff coinvolti;
3. modificare solo scope necessario;
4. eseguire test target;
5. aggiornare immediatamente sub-plan e tabella master con:
   - ✅ + data;
   - `> **Note implementazione**: ...`;
   - `> **⚠️ Fuori pista**: ...` se necessario;
6. non superare il gate corrente.

## 6. Gate

| Gate | Uscita richiesta |
|---|---|
| G0 — Piano | ✅ master/sub-plan/cross-link/recap completi |
| G1 — Quant | ✅ decisione riproducibile su QuantLib/Riskfolio; lock/Docker/CI coerenti |
| G2 — Serie | ✅ parità segnali + joint calendar/FX/metadata testati |
| G3 — Rolling | ✅ 5 plugin nel catalogo, formule/status/client/render testati |
| G4 — Deterministico | RiskAnalytic/API P5-P10 testati, OpenAPI stabile |
| G5 — Avanzato | adapter simulazione verde; P12/P13 con decisione misurata |
| G6 — Frontend | quattro scope renderizzati e funzionali |
| GF — Finale | backend/frontend/Docker/docs/graph verdi |

## 7. Strategia matematica

Ogni formula richiede:

- fixture piccola calcolabile a mano;
- test degli invarianti;
- cross-check NumPy/SciPy o libreria solo come secondo oracolo;
- edge case espliciti;
- tolleranza numerica motivata;
- metadata che descrivono campione/metodo.

Invarianti minimi:

- cash flow non altera TWRR;
- `A=N×365/D`;
- `DD≤0`;
- beta benchmark varianza zero → indisponibile;
- matrice correlazione simmetrica;
- `ΣCCTR=σp`, `ΣPCTR≈100%`;
- `CVaR≥VaR≥0`;
- stesso seed → stesso output;
- single/multi-worker equivalenti.

## 8. Rollback

- dipendenza respinta: rimuoverla interamente da manifest/lock/Docker/test;
- nessun endpoint/UI per capability assente;
- schema additive dove possibile;
- risultati non persistiti;
- P12/P13 possono chiudersi con decisione documentata di non attivazione;
- modifiche preesistenti mai ripristinate.

## 9. Fuori scope

- factor exposure model/factor shock;
- total-return per asset;
- hedging;
- frequenze non giornaliere;
- QMCPy;
- risk score opachi;
- raccomandazioni finanziarie;
- polish/fillings/gallery/screenshot;
- persistenza DB dei risultati.

## 10. Tracking

### D0 — Materializzazione piano

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

**Obiettivo**: creare master + sei sub-plan, cross-linkare le fonti e aggiornare
recap/indice.

**Accettazione**:

- sette file esistono;
- link relativi validi;
- P0-P13 mappati una sola volta;
- progress rule presente in ogni sub-plan.

> **Note implementazione**: creati master e sei sub-plan backend-first, con
> tracciabilità P0-P13, gate, fallback, regole di avanzamento e cross-link.
> Aggiornati piano applicativo, README e guida di ripresa.

---

→ Step 1:
[`plan-phase01Step1QuantFoundation.prompt.md`](./plan-phase01Step1QuantFoundation.prompt.md)
