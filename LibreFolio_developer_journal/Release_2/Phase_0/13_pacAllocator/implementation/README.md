# PAC & Rebalancer — implementation bundle

**Stato:** READY FOR PLANNING CHECKPOINT.
**Baseline:** `b0a410b8805789b200aa7a66a2494c397fb1bc52`.
**Scope corrente:** piani soltanto; nessuna implementazione prodotto è
autorizzata da questi file.

> ⚠️ **Stato al 2026-09-24 (`f1047f766`).** L'header sopra descrive il bundle alla sua
> nascita. Da allora:
> - il planner v2 è implementato e integrato (`3913fe217`);
> - il P1 è stato rimosso (`b82e59ffa`);
> - il budget del solver è propagato (`a7cd01b07`).
>
> Il lavoro in corso è il [piano Round 5](plan-phase00PacRound5PostMerge.prompt.md):
> documenti allineati, UI PAC 2.0.0 nella build, STOP per la review di dettaglio.
> L'ordine completo è nella tabella «Piani successivi all'integrazione», sotto «Piani di esecuzione».
>
> ⚠️ **Aggiornamento del 2026-09-25 (`0210f9848`).** Il Round 5 è committato. Prima dello STOP
> entra il suo Passo F, con le decisioni del developer registrate al §2 del piano:
> - **D-X1:** in produzione gira solo SCIP, e il suo esito fa fede. L'oracolo esaustivo resta
>   solo nei test, come gate d'accordo su domini piccoli.
> - **X2 e QX1-a:** il minimo e il tetto delle commissioni si modellano in modo esatto.
> - **QX1-b:** un piano che dopo gli arrotondamenti supera una cassa di al più `N` unità minime
>   esce con l'importo da aggiungere.
>
> I cinque design autorevoli hanno in testa una nota con la stessa data. Nel grafo sotto, «exact
> core → exhaustive oracle» resta vero per lo Step 2, ma l'oracolo non è più una fonte di prova in
> produzione.
>
> ⚠️ **Aggiornamento del 2026-10-05 (`7038c2224`).** Il Round 5 è chiuso e integrato.
> `dev_release2` è avanzato a `7038c2224`, poi il coordinatore ha aggiunto il CHANGELOG
> (`d9aad0ec9`). Il contratto pubblicato è la versione 1.0.0 compattata (riga 11).
> - Il P1 rimosso il 24/09 era il tool `analyze`. Resta la sorgente `allocation_source` di
>   `POST /portfolio/report`, con il suo client: la toglie la riga 13. (Corretto il 06/10: questa nota
>   diceva `include_allocation_source` di `GET /portfolio/report`.)
> - Il lavoro seguente, approvato dal developer il 05/10, è nelle righe 12–14 della tabella «Piani
>   successivi all'integrazione».
> - Gli E2E del PAC si fanno dopo il Rebalancer, insieme ai suoi. Il server MCP resta fuori round.
> - Le note di mappatura del 05/10 negli Step 1–6 dicono, voce per voce, dove è stato consegnato
>   ogni gate e cosa resta aperto.

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

## Piani successivi all'integrazione

Piani nati dopo il merge del planner v2, in ordine di esecuzione. Ciascuno ha il link
al precedente in testa.

| Ordine | Piano | Contenuto | Stato |
|---:|---|---|---|
| 7 | [Remediation](plan-phase00PacRebalancerRemediation.prompt.md) | fasi e gate dopo la verifica della checklist Step 3; sette decisioni del developer | ✅ committato `c7e25da93` |
| 8 | [Rimozione residui P1](plan-phase00PacP1ResidueRemoval.prompt.md) | P1 `analyze` rimosso, `plan` v2 cablato, pagine MkDocs | ✅ `b82e59ffa` … `154182295` |
| 9 | [Budget del solver](plan-phase00PacSolverBudget.prompt.md) | budget reale dell'engine propagato a SCIP | ✅ `a7cd01b07`, `3e513fea2` |
| 10 | [Round 5 post-merge](plan-phase00PacRound5PostMerge.prompt.md) | documenti allineati, descrizione della card, UI PAC 2.0.0 nella build, STOP per la review di dettaglio | ✅ `4cd2cda56` … `946095d58`; integrato col fast-forward di `dev_release2` a `7038c2224` (chiuso il 2026-10-05) |
| 11 | [Compattazione del contratto](plan-phase00PacContractCompaction.prompt.md) | wire compatto 1.0.0: freshness e data del prezzo tolte, default nello schema, commissioni facoltative; prima dell'integrazione | ✅ `ac18ce097`, `9e4140376`; merge `68483ddda`, gate finali verdi; pagine utente PAC allineate (S11) |
| 12 | [Robustezza del solver](plan-phase00PacSolverRobustness.prompt.md) | A1, R10, P-a, P-c, P-d e voce 13, più R3 in sola lettura: prima la review matematica, poi i test rossi, poi il codice; nessun cambio di versione del contratto | ✅ `638961728` `chore(pac)` C901, `8fa96ac28` `fix(pac)`, `a8ad1a500` journal; merge `7ba60a62f` (albero `59873db3e`), validato verde il 2026-10-06 sulla 6151; contratto 1.0.0 e fingerprint invariati |
| 13 | [Rimozione finale del P1](plan-phase00PacP1FinalRemoval.prompt.md) | diversa dalla riga 8: toglie il ramo `allocation_source` di `POST /portfolio/report`, i suoi 7 schemi, `allocationSource.ts` e le chiavi i18n morte (le 28 `tools.portfolioRebalancer.*` comprese); il report passa da 13 a 12 sezioni; poi R7 in un `fix(pac)` a sé | ✅ S0–S8 `6ebad820b` `refactor(pac)`, `838be2b6f` journal: 285 chiavi tolte ×4 (da 4 508 a 4 223 per lingua), 18 gate verdi sulla 6151; S10 validazione del treno 2 ✅; R7 (plurali delle quantità e aiuti della distribuzione) `dbedcc822` `fix(pac)`, `f374f1e5b` journal; merge `9f06df702` con `dev_release2` `c9a602f74`, rivalidato sulla 6151: 8 gate su 8 verdi |
| 14 | Analisi del Rebalancer — piano da definire | massimo riuso del PAC (compilatore, verifier, report, UI); domanda (b) sul numero di Asset con le misure; un solo salto di versione del contratto; E2E backend del motore; squadra e rischi | ⏳ dopo la riga 13 |
| 15 | [Conversioni FX del PAC](plan-phase00PacFxConversionFix.prompt.md) | difetto trovato da M con la gallery: «Calculation failed» appena una fonte di finanziamento è in una valuta diversa da quella dello scenario. Correzione A (residuo di arrotondamento del ledger esatto, `ExactNumber`), 2A (cambi incrociati incoerenti rifiutati con `allocation.fx_rate_inconsistent`), precisione adattiva in pagina; log del motore coi chiamanti in un commit a sé; contratto 1.0.0. Pagina utente del PAC: cambi coerenti e residuo «≈» (S9, `docs(pac)`). Eseguita prima della riga 14 | 🔄 S0–S9 ✅, gate verdi sulla 6151 il 2026-10-09, `mkdocs build` strict verde; CHECKPOINT READY, in attesa degli SHA |

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

**Stato al 2026-10-05.** Il bundle è stato eseguito. Il planner PAC 1.0.0 è integrato in
`dev_release2` (righe 7–11). Restano le righe 12–14, nell'ordine approvato dal developer il
05/10. Il Rebalancer non è ancora implementato: gli Step 1–6 restano il riferimento per il suo
disegno, con le note di mappatura del 05/10.

**Stato alla nascita del bundle** (testo originale):

La materializzazione di questo bundle non apre il gate prodotto. Dopo il
checkpoint planning-only servono:

1. SHA pulito verificato dal coordinator;
2. autorizzazione developer esplicita all'implementazione;
3. assegnazione workstream/lane;
4. handshake con il gruppo C.
