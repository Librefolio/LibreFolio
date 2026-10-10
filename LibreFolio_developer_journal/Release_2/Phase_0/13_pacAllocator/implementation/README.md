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
| 15 | [Conversioni FX del PAC](plan-phase00PacFxConversionFix.prompt.md) | difetto trovato da M con la gallery: «Calculation failed» appena una fonte di finanziamento è in una valuta diversa da quella dello scenario. Correzione A (residuo di arrotondamento del ledger esatto, `ExactNumber`), 2A (cambi incrociati incoerenti rifiutati con `allocation.fx_rate_inconsistent`), precisione adattiva in pagina; log del motore coi chiamanti in un commit a sé; contratto 1.0.0. Pagina utente del PAC: cambi coerenti e residuo «≈» (S9, `docs(pac)`). Eseguita prima della riga 14 | ✅ `bffc634b0` `fix(pac)`, `b3843e2f8` `chore(pac)`, `f720f7879` `docs(pac)`, `8a79ff34d` journal; merge `95fb05f17` nel treno 21 (`dev_release2` = `9b2acdd5d`), gate verdi del coordinator: `api all` 828, `schemas all` 1705, le 9 suite PAC, i tool e `tools-wire` |
| 16 | [Arrotondamento contro il piano](plan-phase00PacRoundingDirectionFix.prompt.md) | reperto di M con la gallery in USD: l'ottimizzatore sfrutta l'arrotondamento HALF_UP dei crediti (passi da pochi centesimi, «Rounding ≈ −0,02 EUR»). Regola (a): crediti per difetto, debiti per eccesso, su tutte e 7 le famiglie; banda del validatore di una minor unit per posting; C-FXPOS; n. 15 B1 (banda β dei tassi a dieci decimali, tasso al triangolo dentro la banda); contratto 1.0.0 | ✅ `96283eaa5` `fix(pac)`, `85b2a3125` `docs(pac)`, `9a6974eff` journal; merge `b81b92fd1` nel treno 26 (`dev_release2` = `083ed26dc`). Chiusura S10: `style(pac)` sul debito di formato del S8 |

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

**Stato al 2026-10-09.** Il bundle è stato eseguito. Il planner PAC 1.0.0 è integrato in
`dev_release2` con le righe 7–13, 15 e 16; l'ultima è entrata col treno 26 (`083ed26dc`). Fuori
dalla 1.2 restano la riga 14, l'analisi del Rebalancer, e con essa gli E2E dedicati del PAC, che si
fanno insieme a quelli del Rebalancer. L'opzione (e) della riga 16, una sola conversione per broker e
coppia, resta nel [backlog](#backlog) di questa cartella, insieme ai difetti di prodotto trovati da M
negli scatti del lotto 9. Il Rebalancer non è ancora implementato: gli Step 1–6
restano il riferimento per il suo disegno, con le note di mappatura del 05/10.

**Stato alla nascita del bundle** (testo originale):

La materializzazione di questo bundle non apre il gate prodotto. Dopo il
checkpoint planning-only servono:

1. SHA pulito verificato dal coordinator;
2. autorizzazione developer esplicita all'implementazione;
3. assegnazione workstream/lane;
4. handshake con il gruppo C.

## Backlog

**Al 2026-10-09.** Rinvii aperti di questa cartella, fuori dalla 1.2. Le ancore valgono a `9f060ef6e`;
`planner/` sta per `frontend/src/lib/features/tools/pac-allocator/planner/`. Le cause marcate
«ipotesi» vengono dalla sola lettura del codice: vanno confermate nel browser prima della cura.

### Difetti di prodotto dagli scatti del lotto 9

Trovati da M nella gallery del PAC, nel [piano della gallery](../../27_releaseImages/plan-phase00ReleaseGallery.prompt.md)
§22.3–22.4 (`:1706-1737`). Le revisioni immagine per immagine sono in
`release-pipeline/runs/b9_review_desktop_steps.{tsv,md}` e `release-pipeline/runs/b9_review_mobile_steps.{tsv,md}`.
Il manifest `release-pipeline/runs/b9_pac_manifest.md` dà percorso, sha256 e verdetto di ognuna delle 144 immagini.
Le immagini sono fuori dal repository. Una combinazione è una lingua (en, it, fr, es) per un tema (chiaro, scuro).

| # | Reperto di M | Difetto | Scatti | Ancora nel codice | Note |
|---:|---|---|---|---|---|
| 1 | C | La colonna Asset taglia «MSFT Microsoft Corporation» a metà lettera, senza «…»: «…Corp», «…Cor» in es. | `pac-step-targets` desktop, 8 combinazioni su 8; piano della gallery `:1710` | Il nome passa da `planner/shared/AssetNameCell.svelte:16` a `planner/shared/MarqueeName.svelte:16` (R11.6: il nome scorre invece di essere tagliato, il testo intero sta nel tooltip). `overflowScrollTextClass` (`frontend/src/lib/utils/overflowScroll.ts:16`) taglia senza `text-overflow: ellipsis`. A riposo il testo resta tagliato: per 2 s prima di ogni scorrimento (`frontend/src/lib/actions/scrollOnOverflow.ts:22`), e sempre con `prefers-reduced-motion` (`:49`, `:121`). La colonna ha `minWidth: 160` (`planner/steps/TargetsStep.svelte:109`). | Da decidere: «…» a riposo nel solo `MarqueeName`, oppure una colonna più larga. Il marquee è condiviso da 24 file `.svelte`; `MarqueeName` serve anche `ReviewCell` e `ResultCell`. |
| 2 | F | L'intestazione «Actions» c'è, ma nelle righe non c'è il ⋮. | `pac-step-review` mobile, 8 su 8; piano della gallery `:1723` | Le azioni non hanno `visible` (`planner/steps/ReviewStep.svelte:117-119`, `:201-203`), quindi il ⋮ viene disegnato (`frontend/src/lib/components/table/DataTable.svelte:1431-1452`). Ipotesi: sotto i 768 px la media query rende statiche le celle azioni (`DataTable.svelte:2295-2301`). Però `thead.sticky-header th` (`:1614-1619`; `stickyHeader` vale `true`, `:161`) è più specifica di `.th-actions`, quindi l'intestazione resta `sticky` con `right: 0` (`:1658-1660`). Resta incollata al bordo destro, mentre le celle col ⋮ restano fuori, a destra. | `DataTable` è condiviso e non è del PAC: la cura va concordata con chi lo possiede. Lo stesso effetto è possibile in ogni tabella con azioni più larga del telefono. Causa probabile in comune con la riga 5. |
| 3 | — | Nel titolo del passo Routing manca lo spazio prima del trattino: «ROUTING–». | `pac-step-routing` desktop; piano della gallery `:1711` | `planner/PacPlannerTool.svelte:354`: lo spazio prima del trattino è il primo carattere di `<span data-testid="pac-planner-routing-intro"> – …</span>`, e Svelte 5 toglie gli spazi all'inizio e alla fine di un tag. Il maiuscolo viene da `SECTION_TITLE` (`planner/ui.ts:36`). Riga introdotta in `6f29ec1cf`. | Correzione di una riga: uno spazio esplicito prima del trattino, per esempio `{' '}`. Vale per tutte e 4 le lingue. |
| 4 | — | In it e fr una sola parola indica due cose: il passo «Review» e il toggle «Summary» sotto i passi, nella stessa card. È «Riepilogo» in it e «Récapitulatif» in fr. | Passi desktop; piano della gallery `:1711` | `tools.pacAllocator.planner.steps.review` (`it.json:4857`, `fr.json:4857`); `…summary.toggle` (`:4904`) e `…summary.title` (`:4903`). In it anche la colonna `…review.colSummary` dello stesso passo (`it.json:4788`). Il toggle sta sotto `StepNav` (`planner/PacPlannerTool.svelte:338-340`). In en ed es le parole sono già distinte: Review/Summary, Revisión/Resumen. | Si toccano solo i cataloghi, con `dev.py i18n` e un solo writer. La parola la sceglie il developer. |
| 5 | D | Su mobile la tabella dei target non sta nella larghezza del telefono. I nomi sono tagliati a sinistra («APL Apple Inc.»), gli input Target % a destra e senza «%», e «Actions» sta sopra gli input. | `pac-step-targets` mobile, 8 su 8; piano della gallery `:1720-1721` | Larghezze dichiarate in `planner/steps/TargetsStep.svelte:102-135` e `:203-213`: selezione 48 px (`DataTable.svelte:131`), Asset min 160, Distribuzione 200 (min 100), Target % 140 (min 128), azioni 64. Il minimo supera i 500 px. Ipotesi: la colonna di selezione è `sticky` a sinistra (`DataTable.svelte:1648-1651`, `:1974-1978`) e copre i nomi quando la tabella scorre; «Actions» si comporta come nella riga 2. | Difetto di prodotto più fixture. M corregge solo la fixture (blur e reset orizzontale) nel lotto 10. Da decidere: un layout per il telefono, oppure la cura della riga 2 nel `DataTable`. |

Fuori da questo backlog:

- G, lo spazio prima di «%» in `es.json`, è assegnato a S;
- A, B ed E sono di inquadratura o di fixture e restano nel piano della gallery.

### Rinvii di design

- **(e) della riga 16**: una sola conversione per broker e coppia di valute. Con la regola (a) spezzare una
  conversione non conviene, ma il solver può lasciarne più d'una, ciascuna arrotondata contro il piano.
  Fonderle sempre resta da fare; i test non fissano lo spezzamento. Vedi il
  [piano della riga 16](plan-phase00PacRoundingDirectionFix.prompt.md), `:62`, `:143-148` e `:233`.
