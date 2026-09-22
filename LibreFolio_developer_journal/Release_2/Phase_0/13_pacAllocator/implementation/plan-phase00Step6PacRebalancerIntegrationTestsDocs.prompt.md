# Step 6 — integrazione Tool, test finali, docs e handoff

**Stato:** PENDING SOLVER, DOMAIN, CLIENT AND HUMAN UI APPROVAL.
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
