# PAC & Rebalancer — implementation bundle

**Stato:** READY FOR PLANNING CHECKPOINT.
**Baseline:** `b0a410b8805789b200aa7a66a2494c397fb1bc52`.
**Scope corrente:** piani soltanto; nessuna implementazione prodotto è
autorizzata da questi file.

Questo bundle traduce la suite target PAC/Rebalancer in workstream eseguibili,
con dipendenze, ownership, gate, selector e Definition of Done. Non ridefinisce
il prodotto: in caso di conflitto prevalgono i cinque design autorevoli e il
lavoro si ferma per una decisione esplicita.

## Autorità

- [Target master](../plan-phase00PacRebalancerTargetDesign.prompt.md)
- [UI target](../plan-phase00PacRebalancerUiTarget.prompt.md)
- [Nucleo matematico](../plan-phase00PacRebalancerMathematicalCore.prompt.md)
- [Policy, obiettivi e vincoli](../plan-phase00PacRebalancerPolicies.prompt.md)
- [Architettura target](../plan-phase00PacRebalancerArchitecture.prompt.md)

## Piani di esecuzione

| Ordine | Piano | Contenuto | Gate in uscita |
|---:|---|---|---|
| 0 | [Master implementativo](plan-phase00PacRebalancerImplementation.prompt.md) | DAG, ownership, checkpoint, lane, acceptance globale | autorizzazione prodotto separata |
| 1 | [Contratti e capacità](plan-phase00Step1PacRebalancerContractsCapacity.prompt.md) | handshake Tool, wire MCP-friendly, payload, PySCIPOpt/SCIP, benchmark | contract + capacity freeze |
| 2 | [Core esatto e oracle](plan-phase00Step2PacRebalancerExactCore.prompt.md) | normalizer, `ExactRatio`, ledger, evaluator, oracle | exact-core checkpoint |
| 3 | [Solver e policy](plan-phase00Step3PacRebalancerSolverPolicies.prompt.md) | compiler, SCIP, fixed-L2, variante, proof, SELL | solver-policy checkpoint |
| 4 | [Copie dominio](plan-phase00Step4PacRebalancerDomainCopies.prompt.md) | Asset/Portfolio/Broker/FX, permessi, provenance | domain-copy checkpoint |
| 5 | [Frontend e review umana](plan-phase00Step5PacRebalancerFrontendReview.prompt.md) | shell, PAC/Rebalancer, lifecycle, grafici, approvazione | UI APPROVED |
| 6 | [Integrazione, test e docs](plan-phase00Step6PacRebalancerIntegrationTestsDocs.prompt.md) | plugin/client, runner, E2E post-review, docs, gate finali | final handoff |

## Ordine e parallelismo

```text
planning checkpoint
  -> explicit product authorization
      -> Tool handshake
          -> public contract -> MCP review + payload witness
          -> domain-copy audit
          -> developer-owned PySCIPOpt update
          -> ExactQuantityInput extraction

MCP review + payload witness
  -> exact core -> exhaustive oracle
  -> shared frontend shell

PySCIPOpt update + payload-supported domain
  -> SCIP capacity probes

exact core + capacity probes
  -> solver/policy engine

exact core + oracle + solver
  -> report/plugin/generated client

domain copy + shell + client
  -> PAC UI
  -> Rebalancer UI

PAC UI + Rebalancer UI
  -> human review
      -> E2E authoring
      -> docs/i18n/changelog
          -> combined gates -> independent reviews -> FROZEN handoff
```

Workstream indipendenti possono procedere in parallelo soltanto dopo il proprio
gate. Tutti i comandi che usano backend/DB condividono una sola coda nella lane
assegnata; il parallelismo dei file non autorizza runtime concorrenti.

## Regole di avanzamento

1. Il coordinator assegna file esclusivi e un solo writer per ogni superficie
   condivisa/generata.
2. Ogni subpiano viene aggiornato subito dopo ogni step completato:

   ```text
   - [x] Step N — titolo — YYYY-MM-DD
     > **Nota implementazione**: ...
     > **Evidenza**: comando, selector, pass count, hash.
     > **⚠️ Fuori pista**: ...
   ```

3. Test mirati chiudono ogni slice; suite integrate soltanto ai checkpoint
   dichiarati.
4. La review umana di PAC e Rebalancer precede gli E2E completi.
5. Nessun workstream esegue commit, merge, rebase, push o reset.
6. Un cambio a obiettivi, constraint, ledger, proof o UX approvata torna ai
   design autorevoli prima di proseguire.

## Stato

La materializzazione di questo bundle non apre il gate prodotto. Dopo il
checkpoint planning-only servono:

1. SHA pulito verificato dal coordinator;
2. autorizzazione developer esplicita all'implementazione;
3. assegnazione workstream/lane;
4. handshake con il gruppo C.
