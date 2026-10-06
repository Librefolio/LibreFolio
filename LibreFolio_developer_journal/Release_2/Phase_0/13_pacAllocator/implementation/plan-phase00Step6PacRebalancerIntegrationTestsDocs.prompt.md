# Step 6 — integrazione Tool, test finali, docs e handoff

**Stato:** PENDING SOLVER, DOMAIN, CLIENT AND HUMAN UI APPROVAL.
> ⚠️ **Stato al 2026-09-24 (`f1047f766`).** Esistono:
> - solver e dominio;
> - client generato;
> - plugin `pac_allocator` `2.0.0` / `plan`.
>
> Il Rebalancer non ha ancora un servizio. Il renderer PAC v2 e la review umana sono il
> [piano Round 5](plan-phase00PacRound5PostMerge.prompt.md). La porta `6153` citata in
> §12, §14 e §15 è superata: valgono `6151` (suite) e `6161` (copia di prod), e a ogni
> `FROZEN` vanno provate libere **entrambe**. I selector di §6 sono riallineati nella nota
> dentro §6.

**Dipende da:** Step 1–5 secondo i gate dichiarati.

← Master: [piano implementativo](plan-phase00PacRebalancerImplementation.prompt.md)
← Precedente: [frontend e review umana](plan-phase00Step5PacRebalancerFrontendReview.prompt.md)

## 1. Scopo

Integrare core/solver nel Tool, generare il client, collegare i renderer,
formalizzare con test la UI approvata, aggiornare docs/i18n/changelog ed
eseguire tutti i gate sulla stessa revisione.

## 2. Ownership shared

Un solo integration writer modifica:

```text
backend/app/services/tool_plugins/pac_allocator.py
backend/app/services/pac_allocator/report.py
backend/app/services/pac_allocator/__init__.py
frontend/src/lib/features/tools/registry.ts
generated API/schema/client artifacts
scripts/test_runner/**
```

Lo stesso integration writer è nominato runner-catalogue owner da CP1: i
workstream Step 1–5 gli richiedono registrazioni, senza edit concorrenti.

Writer dedicati:

- `test-author`: test nuovi/riscritti;
- `docs-writer`: MkDocs English;
- i18n writer: cataloghi EN/IT/FR/ES tramite CLI;
- changelog writer: `CHANGELOG.md`.

Nessuno di questi file riceve merge “ours/theirs” wholesale.

## 3. Reporter

Il reporter riceve soltanto output evaluator/proof e:

- non ricalcola denaro;
- non colma missing facts;
- non cambia ranking;
- non promuove proof;
- ordina deterministicamente;
- serializza Decimal/ExactRatio secondo wire;
- produce Asset, exposure, Broker order, funding, FX e ledger rows complete;
- produce primary e deployment coerenti;
- include issue/provenance/status;
- revalida il result con il TypeAdapter;
- misura byte UTF-8 prima del return.

Se supera il cap, il compute fallisce esplicitamente con diagnostica interna
senza restituire JSON troncato.

## 4. Plugin

Flusso unico:

```text
validate
  -> normalize
  -> static exact precheck
  -> compile policy
  -> solve
  -> exact replay
  -> optional deployment
  -> proof/status
  -> report
  -> result revalidation
```

Due servizi distinti usano lo stesso package:

- PAC;
- Portfolio Rebalancer.

Vincoli:

- `operation="plan"`;
- plugin sottile;
- nessun DB/provider/domain import nel worker;
- `context.checkpoint()` tra fasi costose;
- stessi limits del descriptor;
- stesso fingerprint atteso;
- diagnostica admin priva di dati personali;
- compute bulk conserva isolamento per Tool ID.

## 5. Code generation e registry

1. eseguire
   `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync`;
2. verificare root request/result;
3. verificare union/discriminanti;
4. verificare Decimal string/nullability;
5. verificare `additionalProperties: false`;
6. verificare fingerprint;
7. collegare renderer PAC/Rebalancer;
8. ripetere sync;
9. seconda sync deve produrre zero diff.

Nessun edit manuale del generated client.

## 6. Runner

> ⚠️ **Nomi riallineati il 2026-09-24.** L'elenco sotto era una previsione. I selector
> realmente registrati al `f1047f766` sono:
> - `schemas pac-planner`;
> - `services pac-planner-{core,evaluator,oracle,policies,solver,proof,wire-numbers,report,service}`;
> - `services portfolio-allocation-source`;
> - `front-utility core-unit`;
> - `front-utility component-unit`.
>
> Fonti: [handoff §0.4](../../16_toolPlatform/handoff-pac-D.md).
>
> Non esistono né `services pac-planner-capacity`, né `api pac-tool`, né `front-utility pac-tool`,
> né `front-utility rebalancer-tool`. Il test API del planner è pianificato nel Round 5
> (TB1), con un nome nuovo da registrare: `api pac-planner-tool`. Il test del Rebalancer
> aspetta il suo servizio.

Prima del primo selector, il runner owner registra:

```text
schemas pac-planner
services pac-planner-core
services pac-planner-oracle
services pac-planner-solver
services pac-planner-capacity
services portfolio-allocation-source
api pac-tool
front-utility component-unit
front-utility pac-tool
front-utility rebalancer-tool
```

Regole:

- path reali, non glob troppo ampi;
- nessun orphan;
- vecchi test P1 migrati o rimossi;
- fixture sintetiche;
- test concorrenti non assumono ordine/count/stato globale;
- una sola coda runtime nella lane.

## 7. Test backend

`test-author` copre:

- schema strict e codegen;
- nonfinite e Unicode;
- exact arithmetic/rounding;
- ledger/fee/FX/tax;
- funding/contribution no-double-count;
- whole/monetary misti;
- min required/if-active e cap;
- holding nonnegative/no oversell/no BUY+SELL;
- fixed-L2/U;
- tutte le policy;
- variante freeze/promotion;
- oracle equality;
- proof semantics;
- SELL verifier;
- no-op/infeasible/limit;
- deterministic permutation;
- payload/capacity;
- auth/no-side-effect delle copy;
- cancellation/cleanup;
- bulk compute con Tool ID distinti.

Esempi storici `3484.14`/`3493.24` verificano soltanto aritmetica nelle loro
assunzioni, non optimum del nuovo obiettivo.

## 8. E2E post-review

Soltanto dopo PAC e Rebalancer `APPROVED`, `test-author` riscrive:

```text
frontend/e2e/tools/pac-allocator.spec.ts
frontend/e2e/tools/portfolio-rebalancer.spec.ts
frontend/e2e/tools/allocation-tool-fixtures.ts
```

Copertura:

- manuale/copy;
- nove step e invalidation;
- whole/monetary;
- multi-Broker/multi-currency/FX;
- primary/deployment;
- invest-only/invest-and-sell;
- no-op/invalid/needs_input/unsupported;
- infeasible proven;
- incumbent limitato con/senza incumbent;
- stale/late/account/abort;
- unauthorized copy;
- desktop/mobile;
- keyboard/privacy.

Selector solo `data-testid`; mai testo tradotto o classi CSS. Nessun sleep
temporale o count globale.

Un bug E2E:

1. viene isolato;
2. il product owner corregge;
3. se cambia superficie visibile, review umana mirata;
4. test-author aggiorna il test soltanto dopo decisione.

## 9. Documentazione

`docs-writer` aggiorna in inglese:

```text
mkdocs_src/docs/user/tools/pac-allocator/index.en.md
mkdocs_src/docs/user/tools/portfolio-rebalancer/index.en.md
pagina developer Tool/PAC-Rebalancer appropriata
```

Contenuti:

- distinzione PAC/Rebalancer;
- manuale e copy;
- whole/monetary;
- policy e modalità;
- primary/deployment;
- status/proof;
- fee/FX/tax/SELL;
- privacy;
- limiti supportati;
- nessuna esecuzione ordini;
- runbook sintetico.

MkDocs translation non parte senza richiesta esplicita. Il debito di
traduzione viene validato secondo le regole docs.

## 10. i18n e changelog

UI i18n:

- EN/IT/FR/ES;
- namespace esistente;
- audit duplicate/missing;
- placeholder coerenti;
- nessun testo hard-coded come selector.

Changelog:

- voce user-facing;
- Tool PAC/Rebalancer;
- policy e piani operativi;
- proof/status onesti;
- nessun dettaglio refactor invisibile.

## 11. Sequenza

- [ ] 1. Integrare reporter e plugin.
- [ ] 2. Registrare selector/path.
- [ ] 3. Eseguire API sync e controllo fingerprint.
- [ ] 4. Collegare renderer compilati.
- [ ] 5. Chiudere test backend mirati.
- [ ] 6. Chiudere unit/component frontend.
- [ ] 7. Ottenere doppia review UI `APPROVED`.
- [ ] 8. Invocare `test-author` per E2E.
- [ ] 9. Correggere bug e ripetere review mirata se necessaria.
- [ ] 10. Invocare `docs-writer`.
- [ ] 11. Aggiornare i18n e changelog.
- [ ] 12. Eseguire gate combinati su una revisione.
- [ ] 13. Eseguire review indipendenti finali.
- [ ] 14. Preparare handoff e congelare.

> **Nota 2026-10-05 (chiusura del round 5).** Il PAC è integrato in `dev_release2`: avanzamento
> a `7038c2224`, poi la riga del CHANGELOG in `d9aad0ec9`. Le caselle restano come sono:
> questa nota dice dove sono finiti i punti, senza spuntarli. Vale solo per il PAC; il
> Rebalancer riparte dall'analisi della riga 14 del [README](README.md).
> - **1. Plugin.** `services/tool_plugins/pac_allocator.py`.
> - **2. Selector.** `api pac-planner-tool`, `services pac-planner-*`, `schemas pac-planner`
>   e gli altri di [handoff §0.4](../../16_toolPlatform/handoff-pac-D.md).
> - **3. `api sync` e fingerprint.** Ai gate R14.8 sul merge `111b0bbd0` e di nuovo dopo la
>   compattazione (fingerprint in handoff §0.2).
> - **4. Renderer.** Registrato in `features/tools/registry.ts:241-244`; la card è nella
>   pagina Tools.
> - **5–6. Test backend e frontend.** Fatti, verdi ai gate del 05/10.
> - **7. Review UI.** Solo il PAC (via libera nel R14.5 del
>   [piano Round 5](plan-phase00PacRound5PostMerge.prompt.md)).
> - **8. E2E.** Non fatti. Il developer, il 05/10, li vuole dopo il Rebalancer, insieme ai
>   suoi, sfruttando le parti comuni. Prima ci sarà anche un E2E del motore lato backend, sul
>   modello di `backend/test_scripts/test_e2e/test_search_to_prices.py`: costruisce la
>   richiesta del tool solo con gli altri endpoint (portafoglio, asset, prezzi, FX) e prova i
>   casi limite.
> - **9. Correzioni.** Fatte nei round, più `0900f11fa`.
> - **10. Docs.** Le pagine utente sono allineate (S11, `a568d6f45`). Una pagina developer sul
>   motore PAC non c'è. In più, `developer/architecture/patterns/tool_plugins.en.md:287` dice
>   ancora che il registro non collega nessun componente e che `pac_allocator` risulta
>   `renderer_missing`: non è più vero dal 25/09 (`0210f9848`). La pagina è della
>   piattaforma Tool.
> - **11. i18n e CHANGELOG.** i18n fatto; il CHANGELOG l'ha scritto il coordinatore in
>   `d9aad0ec9`.
> - **12. Gate combinati.** Fatti sul merge `68483ddda` e prima dell'avanzamento.
> - **13. Review indipendenti.** Non fatte come review separate:
>   - matematica → slice di robustezza del solver (riga 12 del README);
>   - permessi e privacy → coperte dai test e dal controllo del coordinatore sul delta;
>   - risorse → domanda (b) dell'analisi del Rebalancer;
>   - code review → con la rimozione finale del P1 (riga 13 del README).
> - **14. Handoff.** `16_toolPlatform/handoff-pac-D.md`. L'integrazione è stata un
>   avanzamento di `dev_release2`.

## 12. Gate combinati

Comandi esatti vengono confermati dal runner/catalogue corrente. Tutti usano:

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
pipenv run python dev.py ...
```

Ordine:

1. selector schema/core/oracle/solver/capacity/source/API;
2. selector frontend unit/PAC/Rebalancer;
3. E2E approvati;
4. categorie integrate pertinenti;
5. lint/format backend;
6. frontend lint/format/type/build;
7. API sync idempotente;
8. i18n audit;
9. MkDocs strict build/link check;
10. payload witness e benchmark capacity;
11. orphan/dead-code scan;
12. private/generated/runtime artifact audit;
13. `git diff --check`;
14. `lsof -nP -iTCP:6153 -sTCP:LISTEN`.

I dettagli di un failure distinguono:

- pre-collection/infrastruttura;
- setup;
- test;
- artifact toccati;
- retry autorizzato.

Nessun red viene chiamato flaky senza `test-triage`.

## 13. Review finali

### Matematica/oracle

- unità/scaling;
- fixed `F_ref`;
- `L2_fixed`/`U`;
- no denominator shrink;
- ledger/fee/FX/tax;
- mixed instruction;
- variante monotona;
- proof e MIQCP boundary.

### Auth/privacy

- copy fail-closed;
- account switch;
- nessun dato in log/URL/fixture/screenshot/diagnostics;
- compute auth e isolation.

### Risorse

- soft/hard timeout;
- cancellation;
- worker cleanup;
- no process/thread/file residuo;
- memory bounds;
- port free.

### Code review

- nessuna duplicazione piattaforma C;
- nessun calcolo frontend;
- nessun fallback nascosto;
- generated files coerenti;
- P1 morto rimosso;
- docs coerenti al codice.

## 14. Handoff

```text
FINAL HANDOFF

Baseline:
- HEAD iniziale
- target SHA

Behavior:
- PAC
- Rebalancer
- policy/proof

Inventory:
- code
- tests
- docs/i18n/changelog

Evidence:
- selector/pass count
- full gates
- payload/capacity
- independent reviews

Exclusions:
- ignored/generated/private/runtime artifacts

Runtime:
- port 6153 free
- no owned process

Blockers/deferred:
- explicit only

Commit:
- proposed Conventional Commit

State:
- FROZEN
```

Il workstream non stagea il checkpoint ordinario e non crea commit.

## 15. Definition of Done

- plugin sottile e due servizi corretti;
- report backend-authored sotto cap;
- client/renderer/fingerprint coerenti e sync idempotente;
- runner senza orphan;
- test backend/frontend/E2E verdi;
- review umana precedente agli E2E;
- docs EN, UI i18n e changelog aggiornati;
- capacity e proof riesaminati sulla revisione finale;
- review indipendenti senza blocker;
- nessun artifact privato/runtime;
- porta `6153` libera;
- handoff completo e stato `FROZEN`.

→ Indice: [implementation bundle](README.md)
