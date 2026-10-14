# Piano Implementativo — Risk Analysis (Fase 0.1)

**Stato**: ▶️ G6 AUTORIZZATO — G0-G5 chiusi; esecuzione backend-first avviata

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
scope/scenario foundation + frontend funzionale
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
15. P13 usa Riskfolio-Lib 7.0.1 dopo gate host/Linux arm64/amd64.
16. UI: wiring, i18n, stati, render e test funzionali; niente polish/gallery.
17. Nessuna migrazione DB prevista.
18. Nessun `git commit`, push o history rewrite.
19. Scope patrimoniale G6: `portfolio + broker_ids`; eliminare `kind=broker`.
20. Assets Global: `Assets | Correlation | Scenarios | Allocation`.
21. P13 frontend solo in Allocation; non holdings-aware.
22. Catalogo scenari statico/typed/startup-loaded, built-in + host YAML.
23. Historical replay con rendimenti osservati e proxy manuali; hypothetical shock
    a dimensione singola con `Other=100%` e precedenza Paese > UE > Other.
24. Replay audit trail typed: contatori, mapping original→proxy, esclusioni e
    policy effettive; qualità in `DataQualityReport`.
25. Accordion open/closed non invalida dati; request identity e data generation
    governano cache/refetch.
26. Shock bucket UX: presenti nello scope + `Mostra tutti`; `Other` sempre visibile
    per sector/geography.
27. YAML `tags` opzionali/inerti per discovery futura; nessuna UI/API avanzata G6.
28. Replay portfolio/broker: esclusioni come residuo a rendimento zero, senza
    rinormalizzare i pesi rimanenti.
29. Una sola vista funzionale per volta; gate visuale umano obbligatorio prima
    della successiva.

## 4. Sub-plan

| Step | File | P-map | Stato |
|---|---|---|---|
| 1 | [`plan-phase01Step1QuantFoundation.prompt.md`](./plan-phase01Step1QuantFoundation.prompt.md) | P0 | ✅ G1 |
| 2 | [`plan-phase01Step2CanonicalSeriesMetadata.prompt.md`](./plan-phase01Step2CanonicalSeriesMetadata.prompt.md) | P1-P2 | ✅ G2 |
| 3 | [`plan-phase01Step3RollingRiskBackend.prompt.md`](./plan-phase01Step3RollingRiskBackend.prompt.md) | P3-P4 backend | ✅ G3 |
| 4 | [`plan-phase01Step4MultiAssetRiskBackend.prompt.md`](./plan-phase01Step4MultiAssetRiskBackend.prompt.md) | P5 + backend P6-P10 | ✅ G4 |
| 5 | [`plan-phase01Step5SimulationScaleOptimization.prompt.md`](./plan-phase01Step5SimulationScaleOptimization.prompt.md) | P11-P13 | ✅ G5 corretto e verificato |
| 6 | [`plan-phase01Step6RiskFrontendIntegration.prompt.md`](./plan-phase01Step6RiskFrontendIntegration.prompt.md) + [`IA`](./plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md) | scope/scenari/UI P4/P6-P13 | ▶️ backend G6 completato e client congelato; foundation frontend successiva |

> **Note implementazione G1/G3 — 27 Luglio 2026**: QuantLib 1.43 è importabile
> nell'immagine LibreFolio finale; Riskfolio/P13 restano esclusi. I cinque rolling
> risk sono completi dal caricamento bulk alla UI metadata-driven: client sync,
> categoria Risk, picker asset persistito, request gating, EN/IT/FR/ES ed E2E
> funzionale. Nessuna matematica è stata aggiunta al frontend.
>
> **Note implementazione G4 — 27 Luglio 2026**: introdotti contratto e registry
> `RiskAnalytic`, service bulk e API autenticata per KPI TWRR, correlazione, PCTR,
> stress, confronto e historical VaR/CVaR. Il percorso reale sul DB test popolato
> copre tutti i sei analytics; OpenAPI/client e 17 chiavi backend-driven EN/IT/FR/ES
> sono sincronizzati. Review indipendente senza finding ad alta confidenza.
>
> **Note implementazione G5 correttivo — 28 Luglio 2026**: sostituito il motore
> NumPy/thread con QuantLib MC/QMC in worker `spawn` persistente. Aggiunto
> `portfolio_optimization` Riskfolio 7.0.1 in pool separato; P12 misura speedup
> warm `1,938x`/`1,477x` con due worker e mantiene default configurabile 1 per
> budget RAM. Oracle GBM analitici, QMC convergence, solver/frontier/bound,
> timeout/recycle e cache sono coperti. RQMC rimosso.
>
> **⚠️ Fuori pista G5 — 28 Luglio 2026**: il primo lock rigenerato aveva incluso
> upgrade wildcard non correlati; ricostruita la baseline e mantenuta soltanto la
> closure Riskfolio. `api sync` ha inoltre richiesto la correzione documentale di
> un backtick provider che rompeva il TypeScript generato.
>
> **Rettifica G6 — 28 Luglio 2026**: il sub-plan risultava “non iniziato”, ma la
> worktree contiene già store, componenti, quattro route ed E2E mock risk creati
> prima della correzione G5. Nessun nuovo lavoro G6 è stato svolto dopo lo stop
> backend; il materiale esistente resta da auditare e ricertificare, e P13 UI è
> assente. Vedi
> [`report-phase01RiskAnalysisCurrentStateAndHandoff.md`](./report-phase01RiskAnalysisCurrentStateAndHandoff.md).
>
> **Note audit/remediation G5 — 28 Luglio 2026**: separati i controlli
> `random_seed` MC e `sobol_start_index` QMC in contratto, cache, metadata, API e
> frontend minimo. Aggiunto idle reap configurabile ai due pool `spawn`, sicuro con
> coda/in-flight e seguito da restart lazy. Il probe pulito 7.3.0 conferma il
> conflitto `vectorbt`/Numba con NumPy 2.5.1: production resta su Riskfolio 7.0.1.
> G6 è stato riconciliato contro il codice reale nel relativo sub-plan, senza
> iniziarne l'implementazione.
>
> **Revisione IA G6 — 29 Luglio 2026**: confermati Asset Detail
> `Overview | Risk & Scenarios`, Assets Global
> `Assets | Correlation | Scenarios | Allocation`, Dashboard/Broker come summary +
> pannelli condivisi lazy e P13 solo in Allocation. Pianificati inoltre scope
> `portfolio.broker_ids`, catalogo YAML typed startup-loaded, historical replay con
> proxy manuali e hypothetical shock con `Other=100%`/`european_union`. Nessuna
> implementazione era ancora autorizzata in quella revisione.
>
> **Chiarimenti finali IA — 29 Luglio 2026**: definiti audit trail proxy,
> lifecycle lazy/cache, UX bucket presenti+`Mostra tutti` e `tags` YAML opzionali.
> IA approvata esplicitamente. L'utente ha inoltre fissato esclusioni replay come
> residuo zero-return e gate per singola vista funzionale.
>
> **Note implementazione G6-00 — 29 Luglio 2026**: aggiornati IA, contratto,
> piano applicativo, master, recap, README, devWiki e work item. La nuova catena
> ha un solo predecessore per item; G6-11 è il primo step tecnico.
>
> **Note implementazione G6-11 — 29 Luglio 2026**: unificato lo scope in
> `portfolio + broker_ids`, con lista canonicalizzata, subset esatto, access
> control esplicito, metadata/cache identity e `composition_as_of`. Migrato il
> Broker Detail, confermata la Dashboard già portfolio, eliminato il runtime
> `kind=broker` e rigenerato il client. Test Risk backend e risk-store verdi.
>
> **⚠️ Fuori pista G6-11**: `front check` resta bloccato esclusivamente da
> quattro errori concorrenti `SignalAreaSeries`, non dal contratto Risk.
>
> **Note implementazione G6-12 — 29 Luglio 2026**: aggiunto catalogo scenario
> statico e typed, built-in + host, validato e caricato allo startup. Pubblicati
> otto preset, localizzazioni YAML, tag opzionali, diagnostica host e gruppo
> geografico versionato `european_union`; endpoint Risk e client generato sono
> sincronizzati. Test schema, service e API verdi.
>
> **⚠️ Fuori pista G6-12**: la generazione client ha richiesto di riallineare il
> post-processor dei discriminatori ai nomi AI Export già presenti nella OpenAPI
> corrente; nessuna semantica AI Export è stata modificata.
>
> **Note implementazione G6-12A — 29 Luglio 2026**: historical replay separa il
> periodo osservato dal riferimento della composizione, carica prezzi/FX storici
> dedicati e supporta proxy manuali ed esclusioni typed. I proxy sostituiscono
> soltanto i rendimenti; gli esclusi portfolio conservano il peso come residuo a
> rendimento zero. Audit, qualità, metadata e client sono sincronizzati; test
> matematici, schema, service e API verdi.
>
> **⚠️ Fuori pista G6-12A**: corretto il bootstrap Zod delle nuove union
> discriminate. Il bundle statico `:6040` non può ancora essere rigenerato per
> errori concorrenti AI Export non correlati; il modulo API sorgente Risk si
> inizializza correttamente.
>
> **Note implementazione G6-12B — 29 Luglio 2026**: hypothetical shock usa una
> sola dimensione e bucket canonici. Asset class è diretto; settore/geografia
> applicano esposizioni percentuali, fallback `Other=100%` non degradante e
> audit typed. La geografia rispetta `country > european_union > Other` senza
> somma; output e metadata espongono configurazione e regole effettive, inclusi
> bucket configurati a esposizione zero. Test schema, matematici, service e API
> verdi.
>
> **Note implementazione chiusura backend G6 — 29 Luglio 2026**: suite Risk
> service completa (93 test), API post-sync (10 test) e Ruff mirato verdi.
> OpenAPI/client risultano idempotenti e il runtime Risk espone solo
> `asset | asset_set | portfolio`; il pannello provvisorio usa il nuovo payload
> hypothetical a bucket. Client Zod, risk-store unit test, `front check`, build
> statico e smoke login sul server reale `:6040` sono verdi.
>
> **⚠️ Fuori pista chiusura G6**: il crash login apparteneva al bundle statico
> precedente con discriminator Zod incompleti. Dopo la stabilizzazione dei cambi
> concorrenti AI Export è stato possibile rigenerare il client e ricostruire il
> bundle senza modificare la semantica AI Export.
>
> **Note implementazione G6-13 — 29 Luglio 2026**: foundation frontend non
> visuale completata. Builder e request identity typed canonicalizzano solo
> collezioni unordered, il risk store conserva in-flight/risultato/errore e le
> query condivise scartano risposte stale. Stati replay, hypothetical,
> simulazione e relativo view switch sono pronti senza comporre nuove pagine.
> Undici test Vitest e `front check` sono verdi.
>
> **Note implementazione G6-20 — 29 Luglio 2026**: Asset Detail adotta
> `Overview | Risk & Scenarios` preservando integralmente la vista esistente.
> La nuova vista riusa i rolling Risk SignalPlugin e compone query asset-scoped
> per downside, confronto reale, hypothetical shock, historical replay e
> MC/QMC. Editor e response espongono configurazione effettiva, audit bucket,
> fallback, proxy/esclusioni e policy replay; la simulazione offre
> `Evoluzione | Distribuzione finale`. Test risk-store, Risk E2E, regressione
> Asset Detail, type-check, build, i18n e smoke login sono verdi.
>
> **Gate H1 — IN ATTESA**: nessuna vista G6 successiva è autorizzata finché
> l'utente non approva visualmente Asset Detail.
>
> **Review H1 — 30 Luglio 2026**: la V1 funzionale è stata riaperta. La toolbar
> completa deve restare visibile in entrambe le tab; `Abs/%` migra nel componente
> prezzo condiviso Asset/FX e AI Export prende il suo posto nelle PageToolbar.
> La tab Risk non dipenderà più dai Signals salvati: `historical_kpi`,
> VaR/CVaR e i rolling Risk canonici vengono calcolati automaticamente. Confronto
> e beta attendono un asset reale; scenari e simulazione restano lazy. Il gate H1
> è ora suddiviso in review shell, observed/downside, confronto e scenari.
>
> **Avanzamento H1 — 30 Luglio 2026**: H1-R1–R4 completati.
> `historical_kpi@2.0.0` sostituisce senza alias il precedente codice
> portfolio-only, usa close-return canonici per asset e TWRR per portafoglio.
> Test Risk service/API e rigenerazione idempotente OpenAPI/client sono verdi.
> `Abs/%` vive ora nel `PriceChartFull` condiviso; AI Export occupa le
> `PageToolbar` Asset/FX e non gli header Signals. La toolbar Asset resta
> disponibile in entrambe le tab e il Refresh page-level invalida anche la query
> Risk. Durante H1-G1 il `TabBar` Asset esterno è stato eliminato: la navigazione
> `Overview | Risk & Scenarios` usa ora la zona tabs integrata della
> `PageToolbar`, come Dashboard. H1-G1 è approvato; H1-R5 è il prossimo item
> lineare.

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
| G4 — Deterministico | ✅ RiskAnalytic/API P5-P10 testati, OpenAPI stabile |
| G5 — Avanzato | ✅ QuantLib MC/QMC + spawn + idle reap + Riskfolio P13; oracle e benchmark verdi |
| G6 — Applicazione | ▶️ autorizzato; catena lineare backend → viste con gate umani |
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
- stesso controllo di sequenza canonico → stesso output;
- single/multi-worker equivalenti.

## 8. Rollback

- dipendenza respinta: rimuoverla interamente da manifest/lock/Docker/test;
- nessun endpoint/UI per capability assente;
- schema additive dove possibile;
- risultati non persistiti;
- worker count >1 può restare disattivato di default con benchmark documentato;
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

Snapshot persistente dei 37 work item:
[`workItems/README.md`](./workItems/README.md).

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
