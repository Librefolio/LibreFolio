# Piano D — Robustezza del solver PAC, senza toccare il contratto

**Stato:** ✅ consegnato il 2026-10-06 (CHECKPOINT READY, poi FROZEN). Iniziato il 2026-10-05: il via è del coordinator alle 17:39, dopo il commit J1 `8c98a03c1`.
**Baseline:** `8c98a03c1` su `e-alfy-allocatore-pac`, cioè `7038c2224` più il journal J1.
Verificata il 2026-10-05 alle 18:11: albero pulito, stage vuoto, porta 6151 libera.
**Posizione:** `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacSolverRobustness.prompt.md`
← Precedente: [`plan-phase00PacContractCompaction.prompt.md`](plan-phase00PacContractCompaction.prompt.md) (riga 11 del README).
→ Seguente: `plan-phase00PacP1FinalRemoval.prompt.md` (riga 13 del README), da creare.
**Corsia:** suite `6151` + `/tmp/librefolio-r2-d`, un comando per volta. Nessun server di review.

Le righe citate sono misurate alla baseline. Se il codice cambia, prevale il codice.

---

## 0. Perché

Il developer, il 2026-10-05, sull'analisi che proponeva questa slice:

> «si approvo il piano»
>
> «Prima la correzione del solver, poi la pulizia P1 (Consigliato)»
>
> «Sì, tutte come raccomanda D (Consigliato)»

L'ultima risposta copre sei domande. Per questa slice contano tre:
- la slice si fa prima dell'analisi del Rebalancer, perché il Rebalancer userà lo stesso solver;
- il testo «Proven optimal» va precisato, nelle docs EN e nell'i18n ×4;
- l'avviso nella UI sul dominio difficile (opzione F) è rinviato.

Le risposte del coordinator, sempre del 2026-10-05:
- **R3** entra nella review matematica che apre la slice, solo in lettura. Se una correzione
  cambiasse il contratto, mi fermo e lo dico al coordinator.
- **`hypothesis`** va nel backlog: aggiungerla cambia le dipendenze, e quel passo spetta al developer.
- **La voce 13** si riduce alla riserva `_POST_ENGINE_RESERVE_MS`.

Due richieste del developer valgono per tutto il piano:
- **Nomi veri.** Gli agenti si chiamano col loro tipo: agente `general-purpose`, test-author,
  docs-writer. Nessun modello è fissato: vale quello predefinito dell'harness.
- **Parole semplici.** Prima il fatto concreto, poi, se serve, il nome tecnico. Il modello è la frase
  che gli ha reso chiaro il difetto: la distanza minima veniva bloccata a 474,9999988 invece che a
  475, così alcuni piani buoni venivano scartati, e ne usciva un piano con 7 ordini invece che con 6.

## 1. Il problema, detto semplice

**Come lavora il solver.** Il piano si sceglie con la cascata della Strategia:
1. vicinanza ai target (distanza L2);
2. soldi non investiti;
3. priorità di Broker e fonti;
4. costi espliciti;
5. numero di ordini.

Il solver risolve un criterio alla volta, a **stadi**. Chiuso uno stadio, ne **blocca il valore** e
passa al criterio successivo, cercando solo fra i piani che non peggiorano i criteri già chiusi.
Alla fine ci sono gli **stadi di spareggio**: scelgono sempre lo stesso piano fra quelli
equivalenti, così gli stessi dati danno lo stesso piano. Ogni piano, prima di essere pubblicato, è
ricontrollato in aritmetica esatta (Decimal) dall'evaluator.

**I casi di misura.** Sono sonde in-process, senza DB, server né porta (§3.7).
- **M 5×2.** 5 Asset con prezzi da 20 a 50 € (20 + 7,5·i), con un target di un quinto ciascuno.
  2 Broker che possono comprarli tutti, al massimo 1 000 unità per ogni coppia Asset-Broker:
  - tutti e due pagano lo 0,1 % dell'ordine, con un tetto di 10,00 € su questa parte;
  - b00 nient'altro;
  - b01 anche 1,00 € fissi.
  1 500 € di cassa per Broker, quindi 600 € di target per Asset.
  > **Correzione del 2026-10-06** (review S1, §13.10). La prima versione diceva «al massimo 10 unità
  > ciascuno» e «b00 gratis»: erano falsi tutti e due. 10,00 € è il tetto della commissione
  > variabile, non un limite di unità: il piano da 6 ordini compra 29 unità del primo Asset presso
  > b01. E b00 paga lo 0,1 % come b01: nel piano da 6 ordini, 1,4925 € dei 5,975 € di costi espliciti.
- **M 10×2.** Lo stesso con 10 Asset, un decimo ciascuno: prezzi fino a 87,50 €, 300 € di target per
  Asset.
- **Realistico 10×3.** Prezzi al centesimo e 3 Broker:
  - 0,19 % con minimo 1,50 € e massimo 18 €;
  - 0,99 € fissi;
  - 2,00 € fissi.
  Cassa 1 200 / 800 / 500 €.

### 1.1 P-a — il valore bloccato finisce sotto quello vero

- **Cosa succede.** Su M 5×2 il primo stadio trova un piano con distanza L2 esatta 475. Il solver
  però la calcola a modo suo e riporta 474,9999988: lavora con un margine d'errore di circa un
  milionesimo. Il blocco viene messo a 474,9999988 (più un margine di un millesimo di miliardesimo),
  cioè **sotto** 475.
- **La conseguenza.** I piani che valgono esattamente 475 restano fuori dal blocco, a rigore. Il
  solver ne tiene alcuni e ne scarta altri, secondo i suoi arrotondamenti interni.
  - Lo stadio 3 «dimostra» che la priorità migliore vale 11.
  - Il piano pubblicato ha 10: batte un ottimo che lo stadio dichiara di aver dimostrato.
  - Esiste un piano valido con 9 e con **6 ordini invece di 7**. Oggi esce quello da 7 ordini, con
    l'etichetta «Ottimo dimostrato».
  - Dove si perdono, misurato dalla review: nella ricerca, che giudica il blocco con un margine fisso
    di un milionesimo. Il controllo finale, che misura in proporzione, li accetterebbe (§13.2).
- **Il rimedio.** Bloccare al più alto fra due valori: quello del solver e quello esatto del piano
  trovato. Così il piano trovato resta dentro il blocco, e con lui tutti i piani ugualmente buoni.
  - Il prototipo, su M 5×2, pubblica (475, 25, **9**, 239/40, **6 ordini**) in 27,80 s. Il
    prototipo bloccava al solo valore esatto; la review, con la regola del massimo della §4.1,
    ottiene lo stesso piano in 25,11 s (§13.3).
  - Su altre 15 varianti (8 della griglia M e 7 realistiche) il piano finale non cambia. Anche
    questa misura è del prototipo «solo esatto»: con la regola del massimo la ripete la diagnostica
    di S2/S6.
- **Il limite, detto onestamente.** Il solver accetta errori fino a circa un milionesimo con importi
  come questi, e di più quando il target di un Asset supera circa 100 000 unità della valuta di
  riferimento (§13.2). Uno stadio successivo può quindi peggiorare uno stadio già chiuso di quella
  quantità. «Ottimo dimostrato» vuol dire: entro la precisione del solver.

### 1.2 P-c — un controllo finale, come rete

- Per ogni stadio che il solver dichiara chiuso, il valore esatto del piano pubblicato deve stare fra
  il limite inferiore che il solver ha dimostrato e il miglior valore che ha trovato, più la
  tolleranza.
- Se non ci sta, il piano resta valido, ma non si dice «dimostrato»: esce «Ottimalità non
  dimostrata».
- Su M 5×2, oggi, il controllo scatterebbe: lo stadio 3 dice 11, il piano pubblicato ha 10.
- P-c prende solo le contraddizioni che si vedono. P-a ne toglie la causa; P-c è la rete se una
  causa nuova sfuggisse.

### 1.3 A1 — quando il tempo finisce a metà

- **Oggi.** Se il tempo finisce durante uno stadio, gli stadi successivi non partono, e si pubblica
  il piano grezzo di quello stadio. Su M 10×2 sono 14 ordini, con spezzature da 1 unità che pagano la
  commissione fissa.
- **A1.**
  - Una riserva di tempo, ma solo sul primo stadio.
  - Se uno stadio non finisce, se ne blocca il valore sul piano trovato.
  - Il tempo rimasto migliora i criteri successivi, senza peggiorare quello.
- **Misure del prototipo:**

  | Caso | Ordini | Costi espliciti | Priorità | Tempo |
  |---|---|---|---|---|
  | M 10×2 | 14 → **10** | 8,965 → **7,965** | 20 → 15 | 23,55 s |
  | Realistico 10×3 | 13 → **10** | 20,98 → **15,49** | 25 → 15 | 18,86 s |

  Su M 10×2 la distanza L2 (3 100) e i soldi non investiti (35) non cambiano.

  > **Rimisurato dalla review S1** (§13.5). Il prototipo seguiva un'altra regola (Fuori pista di S1,
  > §12); la review ha usato quella esatta della §4.3. Stessi piani; il calcolo intero dura fra 28 e
  > 30 s, perché la coda usa tutto il tempo che resta.
- **Quello che resta vero.** Il piano resta «Ottimalità non dimostrata», e gli stadi dopo
  l'interruzione si vedono come non conclusi.
- **Perché la riserva solo sul primo stadio.** Con una riserva su ogni stadio, M 5×2 perdeva la
  prova: il secondo stadio riceveva 4,5 s, e gliene servono 6,4.

### 1.4 R10 — il tempo che finisce durante uno spareggio

- Gli stadi di spareggio non compaiono nel report: il wire non ha un nome per loro
  (`planner_report.py:870-877`).
- Se il tempo finisce proprio durante uno spareggio:
  - il motivo dello stop dice «limite di tempo»;
  - il report non mostra nessuno stadio interrotto;
  - la validazione rifiuta il risultato, e l'utente vede un errore del tool invece di un piano.
- Il difetto è dimostrato dalla sonda `r10_demo.py`.
- Il rimedio, α:
  - in quel caso l'ultimo stadio pubblicato si mostra come non concluso, così report e motivo dello
    stop dicono la stessa cosa;
  - la prova è già «non dimostrata», perché `conclude_with_solver` vede lo spareggio non chiuso
    (`proof.py:206`).
- Facoltativo, β: una piccola riserva di tempo per gli spareggi, che misurati costano al massimo
  0,098 s.
  > **Scartata dalla review S1** (§13.6). Il «0,098 s» non vale sempre: sul realistico 10×3 i 30
  > spareggi costano in tutto 1,85 s. E quando il primo stadio viene interrotto, la sua riserva di A1
  > fa già da β.

### 1.5 P-d — i testi che promettono troppo

- **Docs EN** `user/tools/pac-allocator/index.en.md`:
  - `:41`, «so the same data always give the same plan»: vero solo per i calcoli completati;
  - `:83`, «no better plan exists»: va aggiunto «entro la precisione del solver». Non «circa un
    milionesimo»: con importi grandi la precisione è più larga (§13.2);
  - `:139-142`: va aggiunto il terzo caso, quello di P-c, in cui i numeri del solver non tornano col
    controllo esatto.
- **i18n**: `badges.help.optimalProven` ×4 dice la stessa cosa di `:83`.
- **La frase dello spareggio finale** `tools.pacAllocator.planner.strategy.tieBreak` (×4) dice «the
  same data always give the same plan», come la `:41`. Compare nel passo Strategia
  (`StrategyStep.svelte:109`) e sotto gli obiettivi del risultato (`ProofPanel.svelte:213`). Si
  aggiorna in S4 con `dev.py i18n update` ×4 e i due fallback, allineata alla `:41`:
  - EN: "If a tie is still left, a fixed order of Assets and Brokers decides. A search that ends by
    itself always gives the same plan for the same data; one stopped by a time or node limit may give
    a different plan."
  - IT: «Se resta ancora un pareggio, decide un ordine fisso di Asset e Broker. Una ricerca che finisce
    da sola dà sempre lo stesso piano con gli stessi dati; una fermata da un limite di tempo o di nodi
    può darne un altro.»
  - FR ed ES con lo stesso senso. Se la frase sulla ricerca fermata da un limite diventa ambigua,
    meglio una parola in più che una frase più corta: lì FR ed ES ripetono «piano».

  > Approvata dal coordinatore come parte di P-d (06/10). L'ho trovata io il 2026-10-06 alle 15:15,
  > preparando i testi di S4; la lista approvata non la comprendeva.
- **L'aiuto delle colonne della prova** (`proof.help.status` e `proof.help.absoluteGap`, ×4) diventa
  falso con A1. Uno stadio della coda può essere «non terminato» con gap 0, e oggi il testo dice che
  0 vuol dire «chiuso all'ottimo». L'ha trovato la review; la proposta è nella §13.8.
- **L'aiuto del badge «Ottimalità non dimostrata»** dice sempre «The solver stopped before closing
  every stage…» (`model.ts:104-107`). Dopo P-c un piano può essere non dimostrato anche con tutti gli
  stadi chiusi, e quel testo sarebbe falso. La decisione è nella §4.6.
- **Commenti e docstring:**
  - `solver.py:88-97` attribuisce l'errore al float64 (circa 2e-16). Quello misurato è 1,19e-6, e
    viene dalle tolleranze di SCIP;
  - `planner_report.py:940-985`: il «ginocchio fra 50 e 60 decisioni» è smentito dalle misure di M.
    Anche «each stage gets a wall-clock slice» non è più vero: ogni stadio riceve tutto il tempo
    rimasto;
  - `planner.py:183-187` rimanda a quel ginocchio.

### 1.6 Voce 13 — la riserva dopo il solver

- `_POST_ENGINE_RESERVE_MS = 2_000` (`tool_plugins/pac_allocator.py:79`) è il tempo tenuto da parte,
  dopo il solver, per il ricontrollo esatto e il report.
- Va rimisurata dopo P-a, P-c e A1, che aggiungono valutazioni esatte, circa 1 ms ciascuna.
- Il tetto delle route non ha più un valore predefinito dal 30/09 (`NoOrderCap`, R8.5): lì non c'è
  niente da rimisurare.
- `limits/nodes` resta non passato: l'opzione G è rinviata.

### 1.7 R3 — gli arrotondamenti oltre la cassa (sola lettura)

- **QX1-b (25/09).** Un piano può chiudere una cassa (Broker × valuta) sotto zero di al più `N`
  unità minime della sua valuta.
  - `N` conta gli importi arrotondati registrati nella cassa: addebito e commissione di ogni ordine
    attivo, e crediti FX.
  - Il risultato mostra l'importo da aggiungere (`rounding_top_ups`).
- **Il debito.** MathematicalCore §22 chiedeva una review matematica di QX1-b, che non si è mai fatta
  come review a sé (chiusura di R3 in Round5PostMerge).
- **L'osservazione S17 da spiegare.** Un ETF a 33,335 €, contributo 100,00 €, 3 unità:
  - U = −0,005 €;
  - saldo finale −0,01 €;
  - riga «Rounding» 0,005 €;
  - integrazione 0,01 €.
- **La mia lettura, da confermare.** I numeri tornano:
  - 3 × 33,335 = 100,005 € esatti;
  - l'addebito HALF_UP è 100,01 €;
  - −0,01 = −0,005 (U) − 0,005 (Rounding);
  - 0,01 ≤ 1 × 0,01.
- **Se servisse una correzione** che cambia il contratto: STOP e messaggio al coordinator.

## 2. Vincoli

- **Nessun salto di versione.** Contratto, implementazione, UI e documentazione restano `1.0.0`
  (`tool_plugins/pac_allocator.py:132-133`, `:147`, `:151`). Non sono mai stati rilasciati.
- **Nessuna modifica a `backend/app/schemas/pac_allocator.py`.** Le sue docstring entrano nel
  fingerprint (`tools/schema.py:18-30`, `:227-229`). I due fingerprint fissati devono restare
  questi (`test_schemas/test_pac_planner_schemas.py:3761-3774`, test `:3777-3785`):
  - PAC `4f061103f96ac9f4fc2fbe69d94beed7381e2dce6e4fea2c57b2eb97f27b58bb`;
  - Rebalancer `be2bb19d144e07fb208ae08a26f31433ac418b722786aeab62b1021b82b18e62`.
- **Nessun cambio di struttura della UI.** Cambiano testi (i18n con `dev.py i18n update`), fallback
  e commenti. In più, solo se approvata, una condizione nella scelta del testo d'aiuto (§4.6).
- **Matematica del modello invariata.** `git diff` vuoto su `evaluator.py`, `ledger.py`,
  `constraints.py`, `compiler.py`, `objectives.py`, `normalize.py`, `models.py` e sull'oracolo
  `_pac_exhaustive_oracle.py`. Cambia solo come il solver percorre la cascata.
- **Nessuna dipendenza nuova** (`hypothesis` resta nel backlog).

## 3. Fatti, con le righe

### 3.1 `backend/app/services/pac_allocator/solver.py` (439 righe)

- Docstring del modulo `:1-41`. `DEFAULT_SOLVER_TIME_BUDGET_SECONDS = 3.5` a `:86`: il default per
  chi non ha una finestra, come test e sonde. La Tool passa 30 s.
- Commento sbagliato del margine `:88-97`; `STAGE_PIN_RELATIVE_SLACK = 1e-12` a `:98`, esportato in
  `__all__` (`:63`).
- Stadi interi: `_INTEGRAL_STAGE_CODES` `:105` (`route_priority`, `active_order_rows`) più il
  prefisso `tie:` `:106`. Stati di limite: `_LIMIT_STATUSES` `:110-126`.
- `SolverStageReport` `:148-171`, con `scope: global | incumbent_face` a `:162`. `SolverRunResult`
  `:174-203`, con `anomaly`.
- `_extract_candidate` `:238-253`: `round(getVal)`, senza clamp.
- `_pin_value` `:256-266`: stadi interi `round`, continui `v + |v|·1e-12`.
- `_unfinished_report` `:269-285`: uno stadio mai partito, senza osservazioni.
- `_apply_engine_settings` `:288-300`: `limits/nodes` solo se arriva `node_limit`. La produzione non
  lo passa mai.
- `solve_policy_program` `:303-343`.
- `_solve_stages` `:346-439`:
  - con `remaining <= 0` lo stadio è `budget_exhausted`, e il ciclo continua (`:368-370`);
  - il blocco usa `freeTransform` più `addCons(expr <= pin)` (`:372-376`);
  - `limits/time` è tutto il tempo rimasto (`:378`);
  - il candidato è sovrascritto a ogni soluzione (`:393-395`);
  - finito vuol dire `optimal` con una soluzione (`:397`);
  - il blocco dello stadio successivo nasce dal primal di SCIP (`:417-419`);
  - il primo stadio `infeasible` dà `reported_infeasible` (`:399`, `:422-426`);
  - le anomalie sono a `:428-434`;
  - dopo uno stadio non finito, tutti i successivi sono `not_reached`, e il ciclo si ferma
    (`:436-437`).

### 3.2 `backend/app/services/pac_allocator/planner_report.py`

- `build_solver_evidence` `:867-911`: toglie gli stadi `tie:*` (`:890`) e passa `scope` e `status`
  così come sono.
- `build_stop_reason` `:914-989`: la docstring `:915-985` è in parte smentita; la logica è `:986-989`
  («`node_limit` se *uno qualunque* degli stadi non finiti ha `nodelimit`, altrimenti `time_limit`»).

### 3.3 `backend/app/services/pac_allocator/planner.py` e `proof.py`

- `plan_pac_allocation` `:124-171`. La valutazione esatta del candidato è a `:166`, `_conclude` a
  `:204-210`. La docstring di `_search` (`:174-196`) rimanda al ginocchio a `:183-187`.
- `conclude_with_solver` (`proof.py:167-215`) dà `not_proven` per:
  - un esito che non è un incumbent;
  - un'`anomaly` (`:204`);
  - nessuno stadio, o uno stadio non chiuso `optimal`, spareggi compresi (`:206`);
  - un candidato pubblicato diverso da quello di SCIP (`:208`).

### 3.4 Lo schema, in sola lettura

- `SolverStageEvidence` `:980-1026`:
  - uno stadio `finished` porta tutte le osservazioni;
  - `infeasible` solo all'ordinale 1, `global`;
  - con primal e duale presenti, l'ordine segue il senso, e il gap assoluto è ≥ |p − d|;
  - uno stadio `unfinished` può portare osservazioni oppure nessuna.
- `ReportedFloatingSolverEvidence.validate_stage_order` `:1036-1048`: nessuno stadio `finished`
  dopo uno `unfinished`. Quindi, con A1, ogni stadio della coda va riportato `unfinished`.
- `_validate_solver_status_proof` `:2235-2260`: `optimal_proven` vuole ogni stadio `finished`.
- `_validate_stop_evidence` `:2283-2290`: `completed` se e solo se nessuno stadio è `unfinished`.
- `PacPlannerReadyIncumbentResult` `:2404` ammette `completed` con `not_proven`: è il caso nuovo di P-c.

### 3.5 Il Tool e la finestra del motore

- `claim_engine_window` (`tools/base.py:55-68`): servono 30 000 ms di motore più la riserva prima
  della soft deadline di 44 000 ms.
- `tool_plugins/pac_allocator.py`:
  - commenti della riserva `:72-78`, valore `:79`;
  - `engine_timeout_ms=30_000` `:90`;
  - commento del compute `:168-185`.

### 3.6 La UI

- `planner/result/model.ts`:
  - fallback EN di `optimalProven` `:94`;
  - scelta dell'aiuto per `not_proven` `:104-107`, con il fallback EN di `floatingUnfinished` a
    `:107`;
  - `STOP_HELP.completed` (`:31`, «ended its search by itself») resta vero.
- `planner/result/ProofPanel.svelte:172`: commento «Every finished stage is SCIP-optimal, so a
  published plan that is not proven always has an open stage». Dopo P-c è falso.
- `StateNotice.svelte:22` mostra `limited` solo quando lo stop non è `completed`: resta corretto.
- Chiavi (`frontend/src/lib/i18n/*.json`):
  - `…result.badges.help.optimalProven` `:4557`;
  - `…result.proof.floatingFinished` `:4774`, oggi **non usata**: il suo ramo fu tolto come
    irraggiungibile in Round5PostMerge, ed è nel backlog delle chiavi inutilizzate;
  - `…result.proof.floatingUnfinished` `:4775`.
- Non esiste un `model.test.ts`. I test vitest della cartella (`StateNotice.test.ts`,
  `ResultCell.test.ts`) sono elencati a mano in `scripts/test_runner/_frontend_utility.py:256-257`.

### 3.7 Test, sonde e runner

- `test_services/test_pac_planner_solver.py` (435 righe):
  - `_run` `:68`, `_lexicographic_key` `:86`;
  - fixture d'accordo con l'oracolo `:199-218`, gate B1 `:226`;
  - `node_limit=1` `:328`;
  - `test_zero_time_budget…` `:344-364` deve restare com'è: `no_incumbent`, tutti gli stadi
    `unfinished` senza osservazioni;
  - stadio `infeasible` `:372-407`.
- `test_pac_planner_report.py`: spareggi filtrati, stop ed evidenza a `:501-587`.
- `test_pac_planner_proof.py`: varianti costruite con `dataclasses.replace` (`:141-149`).
- `test_pac_planner_planner.py:588-627`: il caso infeasible arriva al wire con un solo stadio, senza
  `not_reached`.
- Il cap dell'oracolo esaustivo è 200 000 candidati (`_pac_exhaustive_oracle.py:62`). Un caso piccolo
  che riproduca P-a non l'ho trovato io, e nemmeno la review: 12 configurazioni risolte entro il cap,
  col primo stadio al più 3e-9 sotto il valore esatto (§13.10).
- Leve deterministiche per i test, verificate dalla review (§13.10):
  - `node_limit=1` su M 5×2: 0,08 s; il primo stadio si ferma col limite inferiore a 75,07, contro un
    ottimo di 475;
  - una sottoclasse di `pyscipopt.Model` messa al posto di `compiler.Model` con `monkeypatch`, per
    iniettare un primal o un duale sbagliati. Il modello nasce a `compiler.py:165`: `solver.py:49` è
    solo un'annotazione di tipo, e sostituirlo lì non serve. In alternativa
    `dataclasses.replace(program, model=proxy)`, perché `CompiledProgram` è frozen
    (`compiler.py:103-116`). Assegnare il metodo sull'istanza non funziona: l'attributo è in sola
    lettura;
  - un `SolverRunResult` costruito a mano, per la prova, P-c, R10 e la causa dello stop;
  - per la guardia della §13.2, `monkeypatch.setattr(planner, "solve_policy_program", …)`: il planner
    lo importa a `planner.py:103` e lo chiama a `:191`.
- Runner: `services pac-planner-{core,evaluator,oracle,policies,solver,proof,wire-numbers,report,service}`
  (`service` è `test_pac_planner_planner.py`), `schemas pac-planner`, `api pac-planner-tool`.
  `check-orphans` guarda solo i `test_*.py` delle cartelle delle suite: `test_scripts/diagnostics/`
  ospita script su richiesta con nomi diversi (`ai_export_*`).
- Sonde: `/tmp/libreFolio_d_perf/`, con copia degli script in `files/d_perf_probes/` della sessione
  (macOS pulisce `/tmp`). Le sonde della review S1 sono in `files/review_S1/` della sessione
  (`review2_*`).
  - `probe_lib.py`: la griglia M;
  - `realistic.py`: `make(n, k)`;
  - `lexcheck*.py`, `polish*.py`, `proofcheck.py`, `lexcompare.py`, `plancheck.py`, `r10_demo.py`,
    `stage1*.py`.

## 4. Proposte e domande per la review (S1)

La review la fa l'agente `general-purpose`, prima di ogni codice. Risponde per iscritto a ogni
domanda, e l'esito va nella §13.

### 4.1 P-a — la regola del blocco

- **Proposta:**
  - per gli stadi continui (`fixed_l2`, `shortfall`, `explicit_cost`) il blocco è `m + |m|·1e-12`,
    con `m = max(primal di SCIP, valore esatto del candidato estratto)`;
  - gli stadi interi restano a `round`.
- **Il valore esatto** viene da `evaluate_exact_candidate(program.scenario, program.view, candidato)`,
  codice per codice attraverso `view.objectives`.
  - `CompiledProgram` (`compiler.py:104-116`) ha già `scenario` e `view`, e non nasce un ciclo di
    import.
  - Gli obiettivi esatti valgono anche con `feasible=False` (deficit di arrotondamento), purché
    `candidate_valid`.
- **Ripiego.** Con `candidate_valid=False` si usa il blocco di oggi più un'`anomaly`, quindi la prova
  scende a `not_proven`.
- **Domande:**
  1. massimo dei due, o solo il valore esatto?
  2. il margine di 1e-12 resta?
  3. il ripiego è giusto?
  4. come si scrive il limite residuo: «entro le tolleranze del solver», cioè un peggioramento
     possibile di circa un milionesimo su uno stadio già chiuso (con importi grandi è di più:
     §13.2).
  > **Decisi dalla review S1** (§13.3): il massimo dei due, anche per gli stadi interi; il margine di
  > 1e-12 resta; il ripiego è giusto.

### 4.2 P-c — il controllo finale

- **Criterio.** Per ogni stadio `finished` k, con `v` il valore esatto del candidato finale, c'è una
  contraddizione se:
  - `v < duale_k − tol_k`, oppure
  - `v > primal_k + tol_k`,

  con `tol_k = feastol · max(1, |limite|)`. La `feastol` è quella che SCIP riporta, oggi 1e-6.
- **Dove metterlo.**
  - (iii), raccomandato: alla fine di `_solve_stages`, che imposta `anomaly`. Nessuna firma cambia, e
    `conclude_with_solver` declassa già con un'anomaly.
  - (i): nel planner, con `dataclasses.replace` sul risultato del solver.
  - (ii): un argomento nuovo di `conclude_with_solver`. Cambierebbero le chiamate in
    `test_pac_planner_proof.py` e `test_pac_planner_report.py`.

  > L'analisi approvata metteva P-c in `planner.py`/`proof.py`. (iii) dà lo stesso comportamento con
  > meno superficie, e il solver valuta già il candidato per P-a. Lo decide la review, e lo segnalo al
  > coordinator.
- **Domande:**
  1. il criterio e la tolleranza, anche per gli stadi interi;
  2. il posto.
  > **Decisi dalla review S1** (§13.4): posto (iii). La tolleranza è relativa, `1e-6·max(1, |limite|)`,
  > più `n·1e-6` sulla distanza L2 (n = numero di Asset); gli stadi interi si confrontano in modo
  > esatto; gli spareggi si saltano.

### 4.3 A1 — la coda dopo uno stadio interrotto

- **Riserva sul primo stadio.** Il limite del primo stadio è `rimanente − R(B)`, con
  `R = min(R_max, ρ·B)`. Proposta: `ρ = 0,2`, `R_max = 6 s`. Con 30 s fa 6 s; con i 3,5 s dei test,
  0,7 s.
  > **Superata dalla review S1** (§13.5): `R = min(3 s; 0,1·B)`, cioè 3 s con 30 s e 0,35 s con
  > 3,5 s. Con 6 s, M 5×2 perdeva la prova col carico normale della macchina. In più, se il primo
  > stadio arriva al suo limite senza nessun piano, lo si riprende fino a B.
- **Finché gli stadi finiscono**, ognuno riceve tutto il tempo rimasto, come oggi.
- **Dopo il primo stadio i non finito, se c'è un candidato:**
  - si blocca i al valore esatto del candidato, con la regola di P-a;
  - gli stadi successivi girano dentro quel blocco;
  - ognuno è riportato `unfinished`, con `scope = incumbent_face` e le sue osservazioni;
  - la coda divide il tempo: gli stadi normali ricevono metà del rimanente, gli spareggi tutto il
    rimanente, sempre almeno 0,05 s.
- **Guardia g1, solo nella coda.** Un candidato nuovo sostituisce il migliore solo se il suo vettore
  esatto degli obiettivi, e poi gli spareggi canonici, è migliore o uguale in ordine lessicografico.
  Altrimenti resta il precedente.
- **Il blocco della coda** tiene conto anche del valore esatto del migliore, così il migliore resta
  ammissibile in tutte le facce successive.
- **Se uno stadio della coda non trova soluzioni**, resta il migliore.
- **Senza candidato al primo stadio**, tutto come oggi: `no_incumbent`, stadi senza osservazioni.
- **Domande:**
  1. `ρ` e `R_max`, e la divisione della coda;
  2. g1, confronto esatto stretto, oppure g2, uguaglianza entro la tolleranza sugli stadi già
     bloccati? g1 può scartare un candidato migliore sui criteri successivi solo perché peggiora di
     1e-7 lo stadio bloccato;
  3. dopo `freeTransform`, SCIP riparte dalle soluzioni già trovate? Si verifica con
     `getSols`/`getNSols` in una sonda. L'alternativa esplicita è `createSol`/`addSol`;
  4. gli stadi della coda riportati `unfinished` con le loro osservazioni: la rappresentazione è
     onesta?
  > **Decisi dalla review S1** (§13.5): riserva `min(3 s; 0,1·B)`; g1; SCIP riparte da solo dalle
  > ultime 10 soluzioni, quindi niente `createSol`/`addSol`. La rappresentazione è onesta, ma l'aiuto
  > delle colonne della prova va corretto (§13.8).

### 4.4 R10 — gli spareggi interrotti

- **α, obbligatoria.** In `build_solver_evidence`, se uno stadio di spareggio non è `finished`,
  l'ultimo stadio di obiettivo pubblicato va riportato `unfinished`.
  - Le sue osservazioni restano: lo schema ammette un gap 0 (`:980-1027`).
  - Stop (`time_limit`) ed evidenza concordano, e la prova è già `not_proven`.
- **β, facoltativa.** Ogni stadio di obiettivo lascia `min(0,5 s; 5 % di B)` agli spareggi. Con
  30 s la prova di M 5×2 resta: le servono al massimo 2,2 s di margine.
- **Domande:**
  1. solo α, oppure α più β?
  2. α è onesta? Lo stadio mostrato come non concluso è stato chiuso da SCIP: a non finire è stato
     lo spareggio dopo di lui. Una rappresentazione esplicita degli spareggi chiede il salto di
     versione, fuori da questa slice.
  > **Deciso dalla review S1** (§13.6): solo α, che è onesta. β non serve.

### 4.5 La causa dello stop

- **Oggi:** `node_limit` se uno qualunque degli stadi non finiti ha `nodelimit` (`:989`).
- **Con A1** gli stadi della coda possono essere `optimal` sulla loro faccia, o fermarsi per un'altra
  ragione.
- **Proposta:** la causa è quella del **primo** stadio non finito.
- La produzione non passa mai `node_limit`, quindi per l'utente non cambia niente.
- **Domanda:** d'accordo?
  > **Deciso dalla review S1** (§13.7): sì, contando anche gli spareggi.

### 4.6 Il testo d'aiuto per «completato ma non dimostrato»

- Dopo P-c esiste il caso nuovo: stop `completed`, prova `not_proven`.
- L'aiuto di oggi, «The solver stopped before closing every stage…», per quel caso è falso.
- **(i)** Riscrivere solo `floatingUnfinished` in modo neutro, valido per i due casi. Solo testo.
- **(ii), raccomandata.** Una condizione in `model.ts:104-107`:
  - con `result.stop_reason === 'completed'` si usa `proof.floatingFinished`, riscritta ×4 con
    `dev.py i18n update`. Per esempio: «The solver closed every stage, but its own figures do not
    match the exact check of the plan: the plan is valid, but not proven to be the best.»;
  - altrimenti resta `floatingUnfinished`;
  - si aggiorna il commento di `ProofPanel.svelte:172`.

  Non cambia la struttura, e riusa una chiave inutilizzata: il backlog delle chiavi scende di 1.
- **Decisione:** del coordinator, dopo la review. È una condizione nuova nella UI, quindi la chiedo
  prima di S4.
  > **La review S1 raccomanda (ii)** (§13.8), con testi nuovi. Chiesta al coordinator il 2026-10-06
  > alle 12:26 (vedi il Fuori pista di S1 nella §12). In attesa di risposta.

### 4.7 R3 — QX1-b e S17, in sola lettura

- **Da leggere:**
  - MathematicalCore §6.2 (nota QX1-b) e §13 (arrotondamento firmato);
  - `evaluator.py:2255-2300` (arrotondamento contabile e il suo limite), `:2700-2710` (la regola
    `ROUNDING_BOUND`) e `:3659-3730` (`rounding_top_ups`).
- **Domande:**
  1. il conteggio di `N` è giusto, crediti FX compresi?
  2. la soglia `N × unità minima` basta sempre, e non è più larga del necessario?
  3. i numeri di S17 tornano come nella §1.7?
- Se una correzione cambia il contratto, STOP.
  > **Esito della review S1** (§13.9): tutto giusto. Nessun difetto, contratto intatto.

## 5. Fuori scope

- **Rinviati:**
  - A2 (un'altra rappresentazione della coda);
  - P-b (stadi in denaro resi interi);
  - F (l'avviso nella UI sul dominio difficile);
  - G (`limits/nodes`);
  - il limite di memoria;
  - i candidati al salto di versione (`explanation_keys`, `fx_cost`, la rappresentazione degli
    spareggi, `node_limit`, uno stop per la memoria);
  - `min_fragmentation`.
- **Il Rebalancer.** La domanda (b) sul numero di Asset va nella sua analisi, con la sonda 4×2.
- **Altrove:**
  - R7 → punto 2, come ultimo commit `fix(pac)`;
  - R9 → analisi del Rebalancer;
  - `hypothesis` → backlog.
- **Già risolto:** il tetto delle route non ha più un valore predefinito.
- **Il benchmark** (griglia M e matrice realistica) resta una diagnostica da lanciare su richiesta,
  fuori dalla CI, perché dipende dall'hardware.

## 6. Squadra

| Chi | Cosa |
|---|---|
| D (questa sessione) | piano, codice (`solver.py`, `planner_report.py`, docstring di `planner.py`, commenti di `tool_plugins/pac_allocator.py`; se approvata, la guardia della §13.2 in `planner.py`), revisione dei test, misure, gate, handoff |
| agente `general-purpose` | review matematica S1, solo lettura: fatta il 2026-10-06. Sonde, log e rapporto sono in `files/review_S1/` della sessione (`review2_*`), perché le regole dell'agente non ammettevano `/tmp` |
| test-author | test rossi S2 e la diagnostica su richiesta |
| docs-writer | docs EN S4, solo `user/tools/pac-allocator/index.en.md`; nessuna traduzione, quindi niente stamp |

Fleet non serve: 2–3 file di codice e un solo scrittore per file.

## 7. Passi

**S0 — Il piano.** Questo file e la riga 12 del README dell'implementazione.

**S1 — La review matematica** (agente `general-purpose`, solo lettura). ✅ 2026-10-06
- Risponde alle domande della §4 e verifica R3.
- Ha lavorato in `files/review_S1/` della sessione, non in `/tmp`. Non tocca il repository, il DB,
  i server, le porte né git.
- L'esito va nella §13.
- Se serve un cambio di contratto → STOP e messaggio al coordinator. Non è servito.
- Poi chiedo al coordinator le 3 decisioni della §13.11.

**S2 — I test, prima rossi** (test-author). Solo test, un modulo di supporto e una diagnostica.
> Riscritto il 2026-10-06 due volte: con l'esito della review (§13), poi con le risposte del
> coordinator delle 12:35 (§13.11). La versione che vale è il brief in inglese
> `files/S2/S2_brief_2026-10-06.md` della sessione; qui sotto il riassunto. Le leve sono nella §13.10.

- **Nomi nuovi.** I test li importano dentro la funzione di test, dopo l'asserzione che oggi è
  rossa: così il resto del file resta verde finché S3 non li crea.
  - `stage_one_reserve_seconds(budget_seconds: float) -> float` in `solver.py`, che restituisce
    `min(3, 0,1·B)`;
  - `SolverInfeasibilityContradictedError(ExactEvaluatorError)` in `planner.py` (la guardia è
    approvata).
- **Dove vanno i test:** nei tre file di test che esistono già, così il runner non cambia.
  - `test_pac_planner_solver.py`: la leva, P-a, P-c, coerenza, A1, riserva (2 test), ripresa (2
    varianti);
  - `test_pac_planner_report.py`: R10 α come test di unità, e la causa dello stop (8 casi);
  - `test_pac_planner_planner.py`, nuova sezione «Item 12»: R10 α da capo a fondo, G1 e G2 (la
    guardia).
- **Due file nuovi, senza test dentro:**
  - `backend/test_scripts/test_services/_pac_synthetic_requests.py` costruisce le richieste delle
    sonde: la griglia M, la griglia realistica e gli importi ×10^k. Il trattino basso iniziale
    evita che pytest lo raccolga come test. Rispetto alle sonde, un cambio: nella griglia M il
    primo peso assorbe il resto, perché con tre asset 0,333333 × 3 non fa 1 e la richiesta non è
    pronta (`allocation.target_total_not_one`);
  - `backend/test_scripts/diagnostics/pac_solver_robustness_probe.py`, la diagnostica qui sotto.
- **Come leggere il blocco nei test:** `cons._rhs` vale il blocco solo per `pin:fixed_l2`.
  L'espressione di `shortfall` contiene una costante, che SCIP sposta a destra: su `two_asset_pac`
  `_rhs` è il blocco meno 100.
- **Le asserzioni esatte di ogni test** sono nel brief. Qui sotto la versione della review, che
  resta il ragionamento di partenza.
- **P-a.**
  - Leva: monkeypatch di `compiler.Model` con una sottoclasse di `pyscipopt.Model`. Su uno stadio
    continuo (per esempio `fixed_l2`, riconosciuto contando le chiamate a `setObjective`: dopo S3
    la ripresa aggiunge un secondo `optimize()` senza un nuovo `setObjective`),
    `getPrimalbound` e `getDualbound` scendono di un millesimo. Il duale resta ≤ del primal.
  - Il secondo membro dei vincoli `pin:{code}` si registra con un override di `addCons`
    (`cons._rhs`, oppure `getRhs`).
  - Atteso: blocco ≥ del valore esatto del candidato; nessuna anomalia «infeasible sulla faccia»;
    gli stadi dopo non sono né `infeasible` né `not_reached`; su una fixture piccola il piano è
    quello dell'oracolo.
  - Non si asserisce `optimal_proven`, perché scatta P-c.
  - Oggi: il blocco sta sotto il valore esatto, la faccia è infeasible e gli stadi dopo sono
    `not_reached`.
- **P-c.**
  - La stessa leva, sempre **verso il basso**: primal e duale −1 su `route_priority` (è intero: un
    millesimo verrebbe arrotondato via), oppure −1‰ su uno stadio continuo.
  - Atteso dopo S3: ogni stadio `finished`, stop `completed`, prova `not_proven` con un'anomalia.
  - Oggi è rosso. Dopo il solo P-a deve restare rosso, con `optimal_proven`: così si vede che è rosso
    per il motivo giusto.
  - Il duale **non** va alzato: con P-a, `max(round(primal), esatto)` alzerebbe il blocco e
    cambierebbe il piano.
- **Coerenza sulle 13 fixture dell'oracolo** (`test_pac_planner_solver.py:199-218`).
  - Per ogni stadio `finished` che non è uno spareggio: `ceil(duale − 1e-6) ≤ v ≤ round(primal)` per
    gli stadi interi; `v` dentro [duale − tol, primal + tol] per quelli continui.
  - `tol = 1e-6·max(1, |limite|)`, più `n·1e-6` per `fixed_l2`.
  - Verde già oggi. Dopo S3 anche `anomaly is None`.
- **A1.**
  - `node_limit=1` su M 5×2: la coda è `unfinished`/`incumbent_face`, con le sue osservazioni.
  - Il vettore pubblicato è ≤ (17425/4, 65/2, 13, 3187/400, 8), in ordine lessicografico.
  - Lo stop è `node_limit`.
- **Riserva.**
  - `stage_one_reserve_seconds(30) == 3` e `stage_one_reserve_seconds(3.5) == approx(0.35)`.
  - Il `limits/time` dello stadio 1 è il tempo rimasto meno R, registrato con un override di
    `setParam`.
- **Ripresa.**
  - `getStatus` e `getNSols` finti al primo `optimize` (limite di tempo, nessuna soluzione).
  - Atteso: un secondo `optimize()` senza `freeTransform`, con limite = primo limite + R.
  - Se trova una soluzione, quella diventa il candidato; se non la trova → `no_incumbent`.
- **R10 α.**
  - Si avvolge `planner.solve_policy_program`, come in `r10_demo.py`.
  - L'ultimo stadio `tie:` diventa `solver._unfinished_report(stage, ordinal, "incumbent_face",
    "budget_exhausted")`, e `finished_stage_count` scende di 1 (con `dataclasses.replace`).
  - Fixture: `two_asset_pac` nel test di unità, `_incumbent_payload()` (1 asset, 1 broker, 1 rotta)
    in quello da capo a fondo. Non più la realistica 3×2: vedi il Fuori pista di S2 nella §12.
  - Oggi: `ValidationError`. Atteso: `time_limit`, `not_proven`, l'ultimo stadio di obiettivo
    `unfinished` con le sue osservazioni.
- **La causa dello stop**, con `dataclasses.replace` su un risultato vero di `two_asset_pac` (8 casi):
  - decide il primo stadio non finito, spareggi compresi;
  - uno stadio della coda `unfinished` con stato `optimal` non decide;
  - stadio 1 `timelimit` e coda `nodelimit` → `time_limit` (oggi rosso);
  - `budget_exhausted` o un'anomalia → `time_limit`;
  - il test del report `:540-556` resta valido.
- **La guardia** (approvata il 2026-10-06 alle 12:35).
  - Monkeypatch di `planner.solve_policy_program` che restituisce `reported_infeasible` mentre il
    piano vuoto è ammissibile → errore.
  - 5×1 con gli importi ×10^8 → mai `ready_infeasible`: o un piano, o l'errore. Così il test non
    dipende dalla versione di SCIP.
  - `test_pac_planner_planner.py:588-627` resta verde, perché lì il piano vuoto non è ammissibile.
- **Restano verdi:**
  - budget zero `:344-364`; stadio `infeasible` `:372-407`; gate B1 `:226`;
  - `test_pac_planner_proof.py:179-195`;
  - `test_pac_planner_planner.py:536-561` e `:588-627`;
  - report `:540-584`.
- **Un caso piccolo che riproduca P-a:** la review non l'ha trovato (§13.10). Restano la leva e la
  diagnostica.
- **Diagnostica su richiesta** `backend/test_scripts/diagnostics/pac_solver_robustness_probe.py`:
  - stampa il carico della macchina;
  - M 5×2: (475, 25, 9, 239/40, 6) oppure `not_proven`;
  - le 15 varianti della §13.10, con `--record` prima di S3 e `--compare` dopo, su un file JSON;
  - M 10×2 ≤ (3100, 35, 15, 1593/200, 10); realistico 10×3 ≤ (11098593/2500, 333/10, 15, 1549/100,
    10).
- **Prova del rosso:** una volta per suite, prima di S3, con i comandi della §8. `check-orphans` solo
  se nasce un file di test.

**S3 — Il codice.** Le decisioni della §13, in questo ordine. Dopo ogni punto si rilancia
`services pac-planner-solver`.
1. P-a: `_pin_value` e il suo chiamante. Il valore esatto viene da
   `evaluate_exact_candidate(program.scenario, program.view, candidato)`. Se `candidate_valid` è
   falso, resta il blocco di oggi, più un'anomalia.
2. A1: la riserva, la coda, la guardia g1 e la ripresa, in `_solve_stages`.
3. P-c, alla fine di `_solve_stages`.
4. R10 α in `build_solver_evidence`. Niente β.
5. `build_stop_reason`.
6. La guardia in `_no_incumbent_result`, se approvata.

Docstring e commenti:
- `solver.py:1-41`, `:88-97` (il testo della §13.2 c), `:174-190`;
- `planner_report.py:915-985`, con la frase della §13.10 a `:929-931`;
- `planner.py:183-187`; con la guardia anche `:130-145`, `:237-249` e la docstring del modulo
  `:18-40`.

**C901 — `normalize.py:461`** (chiesto dal coordinator il 06/10 alle 15:50). `dev.py lint` è rosso
sul target per `validate_funding_routes` (complessità 11 su 10), arrivato con `ac18ce097`.
- La regola del coordinator: una scomposizione, se è semplice e coperta dai test esistenti;
  altrimenti `# noqa: C901` con il motivo sulla stessa riga, come nel resto del progetto.
- Un commit `chore(pac)` a sé, solo `normalize.py`, nel prossimo checkpoint. Il contratto non cambia.
- Gate: ruff e black sul file, poi `dev.py lint` su tutto `backend/`.

**S4 — I testi.** I testi proposti sono nella §13.8; le scelte del developer nella §13.11.
- docs EN (docs-writer), le righe della §1.5, più la frase della guardia (§13.8);
- `dev.py i18n update` ×4 su `badges.help.optimalProven` e su `proof.floatingFinished` (scelta (ii));
- i fallback EN di `model.ts`, la condizione (ii) (stop `completed` → `proof.floatingFinished`), il
  commento di `ProofPanel.svelte:172`;
- `dev.py i18n update` ×4 su `proof.help.status`, `proof.help.absoluteGap` e `proof.help.dual`, con i
  fallback di `ProofPanel.svelte:39-45` (approvati il 06/10);
- `proof.scopes.*` ×4 e i fallback di `scopeText` (`ProofPanel.svelte:78-80`) (approvate il 06/10);
- `strategy.tieBreak` ×4 e i due fallback (`StrategyStep.svelte:109`, `ProofPanel.svelte:213`): vedi
  la §1.5, approvata come parte di P-d (06/10).
- I testi delle 8 chiavi nelle 4 lingue sono pronti in `files/S4/i18n_update.py` della sessione:
  un `dev.py i18n update` per chiave, con le 4 lingue insieme. FR ed ES usano i termini che il
  catalogo usa già.

**S5 — Voce 13.**
- Sonde in-process su M 5×2, M 10×2 e realistico 10×3, con 30 s.
- M 5×2 deve tenere la prova con R = 3 s. Con R = 6 s il margine era di 0,49 s, a carico 6,48.
- Alla review lo sforamento del solver era al massimo +0,01 s. La fase dopo il motore, sul 10×3
  sotto carico, la review non l'ha cronometrata: la misura S5.
- Si misurano:
  - di quanto il solver sfora il suo budget;
  - il tempo dopo il solver: ricontrollo esatto, integrazioni, prova e report.
- Se 2 000 ms bastano con largo margine, il valore resta, e cambiano solo i commenti
  (`tool_plugins/pac_allocator.py:72-78`, `:168-185`) con i numeri nuovi.
- **Il carico della macchina.** Prima di ogni corsa a tempo si annota `sysctl -n vm.loadavg`, e il
  numero va nella tabella delle misure. Una corsa fatta durante un picco si ripete. Il 2026-10-06 il
  carico era fra 19 e 26, per servizi di sistema.

**S6 — I gate**, nella §8.

**S7 — L'handoff.**
- `git diff --check`;
- il commit `chore(pac)` del C901, a sé, solo `normalize.py`, accanto ai commit della slice;
- la frase di CHANGELOG allineata a P-d, proposta al coordinator: il CHANGELOG lo scrive lui;
- CHECKPOINT READY;
- FROZEN.

## 8. Selettori e gate

Tutti con questo prefisso, un comando per volta:
`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6151 --data-dir /tmp/librefolio-r2-d …`

1. **Prima di ogni gate che avvia il backend** (lezione R14.8):
   - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front build --debug`,
     dopo l'ultima modifica sotto `frontend/src`;
   - `… dev.py mkdocs build`, se è cambiato un `.md` di MkDocs.
2. **Backend:**
   - le 9 suite `services pac-planner-*`;
   - `schemas pac-planner`: i fingerprint fissati;
   - `api pac-planner-tool`.
3. **Frontend:** `front-utility component-unit`, se cambia `model.ts`.
4. **Statici:**
   - `check-orphans`, se nasce un file di test;
   - `i18n audit`;
   - `front check` a 0/0;
   - `mkdocs check-links`: il D28 (`#rolling-return` in it/fr/es) resta l'unico rosso accettato;
   - `pipenv run ruff check` e `pipenv run black --check`, solo sui file Python toccati;
   - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py lint`: ruff su tutto
     `backend/`, non solo sui file toccati. È la lezione del C901: gli statici della compattazione
     (`plan-phase00PacContractCompaction.prompt.md:363-367`) non avevano il lint del backend, e il
     rosso è arrivato sul target;
   - `git diff --check`.
5. **La diagnostica su richiesta**, una volta, a mano, in-process, annotando il carico della
   macchina (`sysctl -n vm.loadavg`). Se il carico era in un picco, si ripete.

## 9. Definition of done

- [x] La review è scritta nella §13, con una risposta per ogni domanda e l'esito di R3. Nessun cambio
  di contratto, oppure STOP già segnalato. (2026-10-06: nessun cambio di contratto.)
- [x] I test di S2 sono stati rossi per il motivo giusto, e ora sono verdi. (2026-10-06: 13 rossi
  alle 15:17, ognuno col suo motivo, nella voce S2 della §12; tutti verdi nelle suite di S6.)
- [x] M 5×2 pubblica (475, 25, 9, 239/40, 6) oppure `not_proven`. Le 15 varianti sono identiche.
  M 10×2 e realistico 10×3 non sono peggiori della §1.3. (2026-10-06, diagnostica delle 16:18 sul
  codice finale:
  - M 5×2 è dimostrato, con questo piano, in 26,33 s;
  - le 15 varianti della §13.10 sono identiche, 15 su 15, con stato, prova, stop e vettore
    (`/tmp/libreFolio_d_s6_dod15.log`);
  - M 10×2 dà (3100, 35, 15, 1593/200, 10) e il 10×3 dà (…, 15, 1549/100, 10): sono uguali alla
    §1.3, con 10 ordini e costi di 7,965 e 15,49.)
- [x] R10 dà un risultato valido, non più un `ValidationError`. (M 10×2 ora pubblica; test
  `test_an_unfinished_tie_stage_marks_the_last_objective_row_unfinished` e
  `test_unfinished_tie_stage_reaches_the_wire_as_an_unfinished_objective_row`.)
- [x] Una contraddizione fra evidenza e piano dà `not_proven`; sulle fixture dell'oracolo non scatta.
  (`test_an_integral_stage_scip_misreports_is_pinned_exactly_and_never_proven`;
  `test_finished_stage_bounds_bracket_the_exact_replay`, 13 casi su 13.)
- [x] La ripresa lascia `no_incumbent` e l'infeasibilità come oggi. (`test_stage_one_resume_that_finds_nothing_is_still_no_incumbent`,
  `test_stage_one_resumes_once_on_its_reserve_when_its_limit_left_no_solution`,
  `test_infeasible_scenario_reports_only_the_first_global_stage_as_infeasible`.)
- [x] Se la guardia è approvata: con un piano vuoto ammissibile, un «infeasible» del solver dà un
  errore, mai `ready_infeasible`. (Approvata il 06/10, 12:35.
  `test_solver_infeasibility_contradicted_by_the_exact_zero_plan_raises`;
  `test_huge_amounts_never_turn_a_feasible_zero_plan_into_proven_infeasibility`, con SCIP vero.)
- [x] Gli aiuti della prova dicono il vero anche per uno stadio non terminato con gap 0. (S4:
  `model.test.ts`, 8 casi, 2 rossi sul `model.ts` di HEAD e 8 verdi ora.)
- [x] `test_zero_time_budget…`, lo stadio `infeasible` e il gate B1 sono verdi. (B1
  `test_solver_incumbent_equals_exhaustive_oracle_optimum`: 13 parametri su 13.)
- [x] I fingerprint sono invariati, e `git diff` è vuoto sullo schema e sui file della §2.
  (`test_full_planner_schema_fingerprints_are_frozen[pac|rebalancer]` verdi;
  `tool-contract-map.generated.ts` ha ancora `4f061103…58bb`. Il diff sui file della §2 è vuoto,
  tranne il commento `# noqa: C901` su `normalize.py:461`, chiesto dal coordinator: una riga che non
  cambia il comportamento, e va nel commit `chore(pac)` a sé.)
- [x] La voce 13 è chiusa con numeri misurati. (S5: dopo il motore 6,4–12,9 ms contro una riserva
  di 2 000; la riserva resta.)
- [x] Docs EN, i18n ×4, fallback, commenti e docstring dicono il vero, anche per «completato ma non
  dimostrato». (S4.)
- [x] Il C901 di `normalize.py:461` è chiuso e `dev.py lint` è verde (2026-10-06). Il checkpoint lo
  propone come commit `chore(pac)` a sé.
- [x] I gate della §8 sono verdi, e la 6151 è libera (prova con `lsof`). (Voce S6 della §12; `lsof`
  vuoto su 6151 e 6161 alle 16:51:54.)
- [x] Il piano è aggiornato a ogni passo, con «Note implementazione» e «Fuori pista». (S0–S7 nella §12.)
- [x] La frase di CHANGELOG è proposta, poi CHECKPOINT READY e FROZEN. (S7, 2026-10-06: la frase è
  nella voce S7 della §12.)

## 10. Conflitti previsti

- **i18n.** L, F e Risk scrivono altri namespace negli stessi 4 cataloghi. Io tocco solo
  `tools.pacAllocator.*`, con `dev.py i18n`. Eventuali conflitti si risolvono al merge.
- **`_frontend_utility.py`** è condiviso. Lo tocco solo se nasce un test vitest di `model.ts`, e solo
  con una riga accanto a `:256-257`.
- **I file del solver, del report, del planner e la pagina utente PAC** sono solo di D.

## 11. Rischi

- **M 5×2 vive al limite.** Con la regola del massimo (P-a) ci mette 25,11 s, contro 30 s di budget;
  il solo stadio 1 dura 22,04–24,00 s. Su una macchina più lenta perde la prova, e A1 pubblica un
  piano rifinito con «non dimostrata». È onesto, ma diverso da qui. Anche un carico alto della
  macchina può farle perdere la prova: per questo i test usano leve che non dipendono dal tempo
  (`node_limit=1`, valori spostati).
- **La riserva sul primo stadio** costa la prova di un primo stadio che finirebbe fra `B − R` e `B`.
  Con 6 s, M 5×2 la perdeva già a carico normale; con 3 s no, ma S5 lo riconferma. Il prezzo: sul
  10×3 gli spareggi finiscono `budget_exhausted`, quindi non è più garantito che gli stessi dati
  diano sempre lo stesso piano.
- **La guardia della coda è g1** (§13.5). Ha tenuto il piano vecchio contro uno peggiore di
  (0, 0, +8, +149/50, +2). Il suo limite: può scartare un candidato che sarebbe migliore sugli stadi
  dopo, ma è peggiore di un soffio su uno stadio già bloccato.
- **La precisione cala quando gli importi crescono.** Sopra un obiettivo di circa 100 000 unità per
  Asset, gli errori di calcolo superano il milionesimo, in tutte e due le direzioni.
  - P-c fa da rete: nelle misure non è uscito nessun falso «ottimo».
  - Verso 1e10 unità compare una falsa infeasibilità. La guardia, se approvata, prende solo il caso
    in cui il piano vuoto è ammissibile.
  - Sono importi realistici in VND, IDR o IRR, valute da 10^4 a 10^6 unità per euro.
- **Falsi allarmi di P-c.** Quando l'obiettivo per Asset (c) supera circa 1e5, l'errore cresce come
  ~1e-16·c². Se compaiono allarmi falsi, si aggiunge quel termine alla tolleranza.
- **«Ottimo dimostrato» resta entro la precisione del solver**, non esatto. Una certificazione esatta
  renderebbe quasi tutto `not_proven` e riaprirebbe D-X1: non è proposta.
- **Le valutazioni esatte** costano circa 1 ms ciascuna, una per stadio: 35 sul 10×3. S5 misura il
  tempo dopo il motore.
- **SCIP riparte dalle soluzioni già trovate:** dopo `freeTransform` tiene le ultime 10. La guardia
  g1 tiene comunque la migliore.
- **Riproducibilità.** A1 cambia quello che pubblica un run fermato dal tempo. Un run completato
  cambia solo dove P-a corregge il blocco: è il caso di M 5×2, da 7 a 6 ordini.

---

## 12. Avanzamento

- ✅ **S0 — 2026-10-05.** Piano scritto e collegato alla riga 12 del README dell'implementazione.
  > **Note implementazione**: le righe della §3 sono state rilette sul codice alla baseline prima di
  > scrivere il piano, e corrette dove la memoria dell'analisi era spostata di qualche riga.
  > Gli script delle sonde sono copiati anche in `files/d_perf_probes/` della sessione, perché
  > macOS pulisce `/tmp`.
  > **⚠️ Fuori pista**: l'analisi approvata (§5.3) metteva il controllo P-c in
  > `planner.py`/`proof.py`. Qui la proposta raccomandata è nel solver (§4.2, opzione iii): stesso
  > comportamento, meno superficie. Lo decide la review e lo segnalo al coordinator.
- ✅ **S1 — la review matematica, 2026-10-06.** Rilanciata alla ripresa; l'esito è nella §13.
  > **⚠️ Fuori pista**: il primo lancio, la sera del 2026-10-05, si è interrotto con lo stop della
  > sessione. L'agente risulta annullato e non ha scritto nessun rapporto. Si è salvata una sola
  > sonda, `review_tol.py` con il suo log, copiata in `files/review_S1/` della sessione. Misura tre
  > cose su SCIP 10.0, con le impostazioni predefinite:
  > - **come SCIP controlla una soluzione.** Le righe lineari hanno una tolleranza relativa: un
  >   milionesimo del valore. I vincoli quadratici hanno una tolleranza assoluta: un milionesimo e
  >   basta. Per i valori interi vale lo stesso milionesimo;
  > - **i quadrati con valori grandi.** Il quadrato del residuo arriva a SCIP già sviluppato. Quando
  >   il valore costante supera 100 000, gli errori di calcolo del computer superano il milionesimo:
  >   SCIP scarta alcuni punti giusti e accetta alcuni punti sbagliati;
  > - **la ripartenza.** Dopo `freeTransform()`, SCIP tiene le ultime 10 soluzioni trovate, e allo
  >   stadio dopo riprova quelle che rispettano ancora il blocco.
  >
  > Il rilancio parte da queste misure, senza ripeterle. Il 2026-10-06 il carico della macchina era
  > fra 19 e 26, per servizi di sistema: ogni corsa a tempo annota il carico, e quelle fatte durante
  > un picco si ripetono.
  >
  > **⚠️ Fuori pista**: rileggendo il prototipo di A1 (`polish2.py`) prima del rilancio, ho visto che
  > non segue la regola della §4.3, per tre motivi:
  > - dopo il primo stadio, ogni stadio di obiettivo riceve metà del tempo rimasto, anche quando gli
  >   stadi stanno finendo;
  > - il blocco è quello di oggi, non quello di P-a;
  > - non c'è la guardia sul candidato migliore.
  >
  > Quindi le misure della §1.3 vengono da una regola diversa da quella proposta. La review le rimisura
  > con la regola esatta della §4.3.
  >
  > Il rilancio è dell'agente `general-purpose`, in background, alle 09:35. Il brief completo è in
  > `files/review_S1/S1_prompt_2026-10-06.md` della sessione. Il rapporto si è scritto man mano in
  > `files/review_S1/review2_S1_report.md` della sessione, così un'altra interruzione non lo perdeva.
  >
  > **Note implementazione**: la review ha preso 4 140 s, di cui circa 8,6 minuti di sonde, una alla
  > volta. Ho riletto il rapporto contro i log delle sonde. Il piano è corretto nelle §1, §1.1, §1.3,
  > §1.4, §1.5, §3.7, §4, §6, §7, §9 e §11. Nessun cambio di contratto; 3 domande al coordinator
  > (§13.11). Il budget del motore è 30 s (`tool_plugins/pac_allocator.py:90`). La sonda q0a a 30 s
  > è caduta in un picco di carico (~22): è stata ripetuta a carico 9–10, con 120 s, e ha dato
  > 31,27 s.
  >
  > **⚠️ Fuori pista**:
  > - (a) il rapporto sta nei file della sessione, perché le regole dell'agente vietano `/tmp`;
  > - (b) i piani della §1.3 sono stati rimisurati con la regola esatta: stessi piani, 26,7–30,0 s;
  > - (c) con importi verso 1e10 unità esce una falsa infeasibilità (§13.2). La guardia aspetta
  >   l'approvazione;
  > - (d) nessun caso piccolo riproduce P-a. In più una sonda si è fermata su una 3×2 non pronta: un
  >   difetto della sonda, non del motore;
  > - (e) le 15 varianti sono quelle di `lexcompare.py`;
  > - (f) anche l'aiuto `proof.help.dual` è falso sugli stadi dopo il primo (§13.8);
  > - (g) macOS può aver pulito `/tmp/libreFolio_d_perf`: le copie sono in `files/d_perf_probes/`
  >   della sessione.
  >
  > **⚠️ Fuori pista**: la §4.6 e la §13.11 dicevano che le tre domande erano già state inviate il
  > 2026-10-06. Non era vero: le due righe le avevo scritte prima dell'invio, e l'invio non era mai
  > partito. Se n'è accorto il coordinator verso le 12:20, perché non gli era arrivato niente. Le ho
  > inviate alle 12:26 (carico 17,32), con l'esito di S1, i due scostamenti (P-c nel solver; la
  > riserva di 3 s invece di 6 s) e le proposte per il backlog, e ho corretto le due righe.
  > Il testo di `absoluteGap` inviato è quello più semplice, ora anche nella §13.8.
  > Finché il coordinator non risponde:
  > - S2 parte solo sulle parti già approvate: P-a, P-c, A1, R10 α e la causa dello stop, senza i
  >   test della guardia;
  > - la guardia (punto 6 di S3) e tutto S4 (testi, condizione in `model.ts`, docs) aspettano.
  >
  > **Aggiornamento**: il coordinator ha risposto alle 12:35, con le scelte del developer (§13.11).
  > Le tre domande sono chiuse, quindi S2 copre anche la guardia, e S4 può partire dopo S3.

- ✅ **S2 — i test rossi, 2026-10-06** (avvio alle 14:39, carico 5,30; prova del rosso alle 15:17). Li scrive il
  test-author `pac-s2-red-tests`, in background. Il brief, in inglese e autosufficiente, è
  `files/S2/S2_brief_2026-10-06.md` della sessione: è incollato per intero nel prompt dell'agente.
  > **Note implementazione**: prima del lancio ho riletto sul codice ogni riferimento del brief:
  > righe, nomi dei moduli, campi di `SolverStageReport`, il messaggio d'errore di R10 di oggi
  > (`schemas/pac_allocator.py:2290`), le funzioni di supporto dei test esistenti. Ho anche
  > rieseguito, senza runner e senza server, le premesse numeriche: i valori di `two_asset_pac`,
  > lo stadio 1 di M 5×2 con `node_limit` = 1, la coda di A1 simulata a mano, il caso G2.
  >
  > **⚠️ Fuori pista**:
  > - **due file nuovi**, mentre la §7 diceva «solo file che esistono già»: il modulo di supporto
  >   `_pac_synthetic_requests.py` e la diagnostica. Nessuno dei due contiene test, quindi il runner
  >   non cambia;
  > - **R10 è diviso in due**: un test di unità nel report, su `two_asset_pac`, e un test da capo a
  >   fondo nel planner, sulla fixture minima con una sola rotta. La realistica 3×2 non serve:
  >   basta un caso con almeno uno stadio di spareggio;
  > - **la causa dello stop** si prova modificando con `dataclasses.replace` un risultato vero di
  >   `two_asset_pac`, invece di costruire i risultati a mano;
  > - **la riserva ha due test**: uno sulla funzione, uno sul limite di tempo dello stadio 1;
  > - **P-a**: che oggi uno stadio dopo diventi infeasible è una previsione. Il rosso sicuro è
  >   un altro: il blocco registrato sta sotto il valore esatto del candidato;
  > - **la scansione delle 13 fixture dell'oracolo** (carico 6,66) ha letto solo la struttura: gli
  >   stadi di ogni fixture, quanti spareggi, il piano migliore dell'oracolo. Tutte iniziano con
  >   `fixed_l2`. Che il test di coerenza sia verde già prima di S3 lo dice la sonda `pc_oracle` della
  >   review (§13.11: 0 allarmi su 13 fixture). Lo confermerà la prova del rosso;
  > - P-c nel solver e la riserva di 3 s: il coordinator non ha obiezioni (§13.11);
  > - `ExactRatio` si confronta solo con `ExactRatio` o con un intero; con un numero decimale dà
  >   errore. Il brief dice di portare i due lati a `Fraction`;
  > - il blocco si legge da `cons._rhs` solo per `pin:fixed_l2` (vedi la §7). La leva si arma dopo
  >   la compilazione, così non tocca il modello in costruzione;
  > - **la griglia M 3×2 delle sonde non era pronta**: i tre pesi 0,333333 non fanno 1. Nel modulo di
  >   supporto il primo peso prende il resto; le altre griglie non cambiano;
  > - nella simulazione di A1 ho controllato che ogni stadio della coda avesse un valore primale;
  > - l'app si è chiusa verso le 14:18, prima che il test-author partisse. Ripreso alle 14:21
  >   (carico 5,26): il worktree era intatto, nessun test era stato scritto;
  > - il test-author è partito solo dopo la rilettura dei riferimenti, alle 14:39.
  >
  > **Nel frattempo** (14:40–15:05, carico fra 22 e 30): ho scritto una bozza di S3 solo nei file
  > della sessione (`files/S3/`), mai in `backend/app/**`. Sono tre file: `solver.py.draft`,
  > `planner_report.py.draft` e `planner.py.draft`, con gli script che li costruiscono dagli
  > originali. Ruff e black li passano. La funzione più complessa è `_solve_stages`, a 6 (il limite
  > è 10). Ruff conta solo `if`, `elif`, `for`, `while` ed `except`, non le espressioni
  > condizionali. La bozza entra nel codice solo dopo la prova del rosso, un punto alla volta.
  >
  > **Note implementazione** (consegna del test-author e prova del rosso):
  > - **file toccati**, solo quelli previsti:
  >   - `test_pac_planner_solver.py`: la sezione nuova `:446-770` (la leva su SCIP, P-a, P-c, A1,
  >     la riserva, la ripartenza);
  >   - `test_pac_planner_report.py`: la sezione nuova `:958-1026` (R10 e la causa dello stop);
  >   - `test_pac_planner_planner.py`: la sezione «Item 12» `:1349-1468` (R10 sul filo e la guardia);
  >   - nuovi: `_pac_synthetic_requests.py` (196 righe, solo funzioni di supporto) e
  >     `diagnostics/pac_solver_robustness_probe.py` (194 righe, non registrata nel runner).
  > - **la mia rilettura**: ogni test controlla quello che chiede il brief, con le premesse
  >   scritte come `PREMISE`. Nessun `xfail`, `skip` o `sleep`. Ruff e black puliti sui 5 file.
  >   `git diff --check` pulito. Nulla in stage.
  > - **la prova del rosso**, una suite per volta sulla 6151, con
  >   `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6151 --data-dir /tmp/librefolio-r2-d services <suite>`.
  >   Log in `/tmp/libreFolio_d_s2_red_{solver,report,service,proof}.log`.
  >
  >   | Suite | Ora | Carico (1 min) | Esito |
  >   |---|---|---|---|
  >   | `pac-planner-solver` | 15:17 | 20,49 | 7 rossi, 33 verdi |
  >   | `pac-planner-report` | 15:17 | 17,03 | 3 rossi, 31 verdi |
  >   | `pac-planner-service` | 15:17 | 15,73 | 3 rossi, 41 verdi |
  >   | `pac-planner-proof` | 15:18 | 22,17 | 30 verdi |
  >
  >   Uguale al rapporto del test-author. I 116 test che c'erano già restano verdi.
  > - **perché ogni rosso è rosso**, e quale punto di S3 lo farà diventare verde:
  >   - 5.1: il blocco di `fixed_l2` è 499,4999999995005, sotto il valore esatto 500 → P-a;
  >   - 5.2: lo stadio `explicit_cost` esce infeasible, perché il blocco di `route_priority` è 2
  >     invece di 3 → P-a, poi P-c per l'allarme;
  >   - 5.4: dopo lo stadio 1 fermato dal limite sui nodi, `shortfall` resta `not_reached` → A1;
  >   - 5.5a: `stage_one_reserve_seconds` non esiste ancora (ImportError) → la riserva;
  >   - 5.5b: lo stadio 1 riceve 29,9999987 s invece di circa 27 → la riserva;
  >   - 5.6 (due test): lo stadio 1 non viene ripreso, `optimize()` è chiamato una volta sola → la
  >     ripresa;
  >   - 6.1: la riga di `active_order_rows` resta `finished` anche se lo spareggio dopo non è
  >     finito → R10 α;
  >   - 6.2, casi C3 e C4: lo stop dice `node_limit`, ma il primo stadio fermato era fermato dal
  >     tempo → la causa dello stop;
  >   - 7.1: il risultato non passa la validazione (ValidationError) → R10 α e la causa dello stop;
  >   - 7.2 e 7.3: un piano «non fare niente» valido viene pubblicato come
  >     `infeasibility_proven` → la guardia.
  > - **7.3 è rosso con SCIP vero**, senza nessuna sostituzione: la griglia 5×1 con tutti gli
  >   importi moltiplicati per 10⁸ (prezzi fra 2 e 5 miliardi, cassa 150 miliardi) esce oggi
  >   `ready_infeasible` / `infeasibility_proven` / `completed`. È il difetto della §13.2,
  >   riprodotto su un caso di test.
  > - 5.3 (13 casi, il controllo dei limiti di SCIP contro i valori esatti) è verde già oggi, come
  >   previsto: il controllo di P-c non scarterà dimostrazioni giuste.
  >
  > **⚠️ Fuori pista** (scostamenti del test-author dal brief, tutti accettati):
  > - i dizionari sono scritti con le graffe e non con `dict(...)`, perché ruff (C408) lo chiede;
  > - nelle griglie sintetiche il primo peso prende il resto, così i pesi fanno sempre 1;
  > - in 6.2 ogni caso rifà da capo la corsa vera di `two_asset_pac`, invece di condividerne una:
  >   più lento di poco, ma ogni caso è indipendente;
  > - il caso G2 è cronometrato dentro il processo: 0,007–0,020 s;
  > - la diagnostica ha una chiave in più, `error`, e chiude con codice 1 se un controllo fallisce;
  > - il brief prevedeva che il blocco di 5.1 fosse 499,5000000005. È 499,4999999995005, perché
  >   anche il valore che SCIP dà prima della leva sta un poco sotto 500. Il test non cambia: il
  >   blocco resta sotto 500.
  >
  > **La diagnostica prima di S3** (15:19–15:21, carico fra 12 e 14, budget 30 s): 23 varianti,
  > in-process, con
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python backend/test_scripts/diagnostics/pac_solver_robustness_probe.py --budget 30 --record <file>`.
  > Il registro è `files/S3/probe_before_2026-10-06.json` della sessione, con il log accanto.
  > - 20 varianti chiudono con la prova, fra 0,02 e 8,70 s;
  > - **M 5×2**: si ferma al limite di 30 s, prova `not_proven`, piano (475, 25, 12, 279/40, 8):
  >   8 ordini invece dei 6 del piano migliore;
  > - **M 10×2**: si ferma al limite e poi **non pubblica niente**: il risultato non passa la
  >   validazione (ValidationError). È il difetto R10, visto su una corsa vera;
  > - **realistico 10×3**: si ferma al limite, piano (…, 25, 1049/50, 13), peggiore del riferimento
  >   della review (…, 15, 1549/100, 10). Il controllo della diagnostica dà FAIL, come previsto
  >   prima di S3.

- ✅ **S3 — il codice, 2026-10-06, dalle 15:22 alle 16:21.** La bozza di `solver.py` entra in tre tagli,
  costruiti da `files/S3/stage_solver.py` della sessione: il taglio 1 ha solo P-a, il 2 aggiunge A1,
  il 3 aggiunge P-c ed è la bozza intera. Ogni taglio passa ruff e black prima di entrare. Dopo
  ogni taglio rilancio `services pac-planner-solver`.
  - ✅ **1. P-a, 15:23** (carico 23,36). Il blocco di uno stadio è il più alto fra il valore di
    SCIP e il valore esatto del piano migliore. Il valore esatto si ricalcola con
    `evaluate_exact_candidate` a ogni stadio che trova un piano. Se il piano non passa il
    ricalcolo, il blocco resta quello di oggi e si registra un'anomalia.
    > **Note implementazione**: `services pac-planner-solver` → 6 rossi, 34 verdi
    > (`/tmp/libreFolio_d_s3_cut1_solver.log`). 5.1 è verde. 5.2 ora supera il suo primo controllo
    > (tutti gli stadi finiti) e si ferma al secondo, l'anomalia, che arriva con P-c. I 13 casi di
    > 5.3 restano verdi. Gli altri rossi aspettano A1.
    > **⚠️ Fuori pista**: il ciclo degli stadi è già diviso in funzioni piccole (`_Cascade`,
    > `_take_candidate`, `_close_stage`…), come nella bozza intera: nel taglio 1 la funzione che
    > deciderà se andare avanti dopo un limite ferma sempre il ciclo, come oggi.
  - ✅ **2. A1, 15:23** (carico 16,55): la riserva, la coda, la guardia g1 e la ripresa, in
    `_solve_stages` e nelle funzioni piccole intorno.
    > **Note implementazione**: `services pac-planner-solver` → 1 rosso, 39 verdi
    > (`/tmp/libreFolio_d_s3_cut2_solver.log`). Resta rosso solo 5.2, che aspetta l'allarme di P-c.
    > **⚠️ Fuori pista** (scelte della bozza su punti che la review lasciava aperti):
    > - lo stadio 1 viene ripreso solo quando il tempo lo ferma senza nessun piano in mano. Con un
    >   piano, si va avanti nella coda;
    > - nella coda si entra solo con un piano migliore che ha passato il ricalcolo esatto. Senza, il
    >   ciclo si ferma come prima, con gli stadi dopo `not_reached`;
    > - il piano dello stadio che si ferma per primo su un limite sostituisce sempre il migliore,
    >   come prima: è stato trovato dentro tutti i blocchi già dimostrati. Negli stadi dopo, un piano
    >   lo sostituisce solo se i suoi valori esatti non sono peggiori, stadio per stadio;
    > - quando lo stadio 1 dice «infeasible», la risposta ha solo quella riga, come prima: lo schema
    >   non ne accetta altre.
  - ✅ **3. P-c, 15:23** (carico 13,88): il taglio 3, cioè la bozza intera. Alla fine del ciclo si
    controlla che il valore esatto del piano restituito stia dentro i limiti che SCIP ha dato per
    ogni stadio finito. Se non ci sta, si registra un'anomalia e la prova diventa `not_proven`.
    > **Note implementazione**: `services pac-planner-solver` → 40 verdi. Il `solver.py` del repo è
    > uguale alla bozza (`cmp`).
    > **⚠️ Fuori pista**: il controllo di P-c sta nel solver (`_flag_contradicted_bounds`), non nel
    > planner; la riserva dello stadio 1 è di 3 s su 30 (`stage_one_reserve_seconds`). Il
    > coordinator non ha obiezioni (2026-10-06, insieme alle risposte del developer delle 12:35).
  - ✅ **4. R10 α, 15:24** (carico 17,10; 20,88 per la suite del service): quando uno spareggio non
    è finito, anche l'ultima riga con un nome diventa `unfinished`, con i numeri di SCIP.
    > **Note implementazione**: `services pac-planner-report` → 2 rossi (C3, C4), 32 verdi; 6.1 è
    > verde. `services pac-planner-service` → 2 rossi (7.2, 7.3), 42 verdi.
    > **⚠️ Fuori pista**: 7.1 è già verde con R10 α da solo. La previsione diceva che serviva anche
    > la causa dello stop (punto 5).
  - ✅ **5. La causa dello stop, 15:25** (carico 32,69: un picco, quindi questa corsa non vale come
    misura di tempo): decide il primo stadio non finito che SCIP non ha chiuso.
    > **Note implementazione**: `services pac-planner-report` → 34 verdi.
  - ✅ **6. La guardia, 15:25** (carico 35,71, letto subito dopo): se il solver dice «infeasible»
    ma il piano vuoto rispetta tutte le regole, la risposta è un errore, mai `ready_infeasible`.
    > **Note implementazione**: `services pac-planner-service` → 44 verdi. `planner.py` e
    > `planner_report.py` sono uguali alle loro bozze.
    > **⚠️ Fuori pista**:
    > - il carico non è stato letto prima della corsa: la catena di comandi si è fermata al C901 di
    >   ruff su `normalize.py:461` (`validate_funding_routes`, complessità 11 su 10). Il C901 c'è già
    >   a HEAD, in un file che questa slice non toccava. Il coordinator l'ha poi chiesto dentro
    >   questa slice (06/10, 15:50): vedi la voce «C901» in fondo a questa sezione. I tre file
    >   cambiati passano ruff e black;
    > - la guardia controlla prima di costruire la parte comune della risposta;
    > - la classe d'errore `SolverInfeasibilityContradictedError` non è in `__all__`: il plugin la
    >   tratta come ogni `ExactEvaluatorError`, cioè `execution_failed`.
  - ✅ **7. Docstring e commenti**, prima dei gate delle 15:29.
    > **Note implementazione**:
    > - `solver.py`:
    >   - il commento sopra `STAGE_PIN_RELATIVE_SLACK` è il testo della §13.2 c, adattato: il caso
    >     474,9999988 contro 475 su 5 asset × 2 broker, e il blocco che è `max(SCIP, esatto)` più
    >     il margine (`_exact_pin_value`);
    >   - la docstring di `SolverRunResult`: il piano migliore, la ripresa dello stadio 1, i tipi di
    >     anomalia, e che `proof.py` non conclude mai `optimal_proven` con un'anomalia;
    >   - quella di `_pin_value`, che ora serve solo quando il piano migliore non passa il ricalcolo
    >     esatto;
    > - `planner_report.py`, `build_stop_reason`:
    >   - ogni stadio riceve tutto il tempo rimasto, e lo stadio 1 tiene da parte la riserva;
    >   - un paragrafo «Corrected 2026-10-06»: con più broker che vendono lo stesso asset il
    >     ginocchio scende molto sotto la griglia. 5 asset × 2 broker chiudono lo stadio 1 solo
    >     dopo 22–24 s su 30, 10 × 2 mai, 10 asset con un broker ciascuno in 85 ms (la sonda di M).
    >     La taglia si misura in asset × broker;
    > - `planner.py`, docstring di `_search`: il rimando a `build_stop_reason`.
    > **⚠️ Fuori pista**: le bozze non avevano questi testi, chiesti dalla §7, dalla §1.5 e dalla
    > §13.2 c. Li ho scritti direttamente nel repo, quindi ora i tre file del repo sono diversi dalle
    > bozze della sessione.
  - ✅ **8. I gate e la diagnostica**, chiusi alle 16:21, dopo il punto 9.
    > **Note implementazione**:
    > - le 9 suite e lo schema, 15:28:58–15:29:50 (carico 13,9–18,8), lanciati uno per volta da
    >   `/tmp/libreFolio_d_s3_gates.sh`. Tutti verdi:
    >
    >   | Suite | Verdi |
    >   |---|---|
    >   | core | 177 |
    >   | evaluator | 159 |
    >   | oracle | 21 |
    >   | policies | 40 |
    >   | solver | 40 |
    >   | proof | 30 |
    >   | wire-numbers | 39 |
    >   | report | 34 |
    >   | service | 44 |
    >   | `schemas pac-planner` | 543: i fingerprint tengono |
    >
    > - la diagnostica, 15:30–15:31:50 (carico da 13,04 a 26,98), con `--compare` sul registro di
    >   prima di S3 (`files/S3/probe_after_2026-10-06.{json,log}` della sessione, log in
    >   `/tmp/libreFolio_d_s3_probe_after.log`):
    >   - 19 varianti danno lo stesso piano di prima, con la prova;
    >   - M 5×2 ora è dimostrato: (475, 25, 9, 239/40, 6), PASS. Ci mette 28,05 s su 30: il tempo si
    >     guarda in S5;
    >   - `m-5x2_ratezero_fixed_both`: prima era «dimostrato» con (475, 25, 10, 7, 7), cioè 7
    >     ordini. Ora è dimostrato con (475, 25, 9, 6, 6), 6 ordini, in 7,71 s invece di 8,70. È il
    >     difetto del blocco a 474,9999988, che P-a corregge: la vecchia «prova» scartava piani
    >     migliori;
    >   - **M 10×2 e realistico 10×3 non pubblicano niente** (ValidationError). M 10×2 falliva già
    >     prima di S3, ma per R10; il 10×3 prima pubblicava un piano. Vedi il Fuori pista.
    > **⚠️ Fuori pista — la distanza fra i due numeri di ogni stadio.**
    > - Per ogni stadio la risposta mostra il valore del piano trovato (primal), il limite dimostrato
    >   (dual) e la distanza fra i due:
    >   - il solver calcola la distanza in virgola mobile (`solver.py:475`);
    >   - la risposta scrive ogni numero come il decimale più corto (`planner_report.py:1044`);
    >   - il validatore (`schemas/pac_allocator.py:1024`) rifà la differenza, esatta, sui decimali
    >     scritti, e vuole che la distanza scritta non sia più piccola.
    > - I tre arrotondamenti non vanno d'accordo. 7,965 − 7,770482487229448 = 0,194517512770552,
    >   ma la risposta scrive 0,19451751277055163, più piccolo di 3,7·10⁻¹⁶: è lo stadio
    >   `explicit_cost` di M 10×2. Sul 10×3 è `route_priority`: 18,000000000026 −
    >   11,817996292140588, con uno scarto di 10⁻¹⁵.
    > - Il difetto c'era già, ma prima solo lo stadio 1 scriveva una distanza, e su M 10×2 lo
    >   copriva R10. Con la coda di A1 la scrivono anche gli stadi dopo il limite, e il caso diventa
    >   frequente.
    > - La correzione: in `build_solver_evidence` la distanza si calcola esatta dai due decimali
    >   scritti, con `ExactRatio` e `ratio_to_fixed_decimal`. È la stessa definizione di
    >   `solver.py:475`. Schema, validatore e fingerprint non cambiano; quel numero lo mostra solo la
    >   tabella della prova.
    > - La prova a secco, con una sostituzione fuori dal repo (15:36–15:37, carico 31–40): M 10×2
    >   (3100, 35, 15, 1593/200, 10) e realistico 10×3 (11098593/2500, 333/10, 15, 1549/100, 10).
    >   Tutti e due escono `not_proven`/`time_limit`, uguali ai riferimenti della review: PASS.
    > - Il coordinator non ha obiezioni (2026-10-06). L'ordine: il test rosso (test-author), la
    >   correzione, poi la diagnostica intera a carico più basso, annotando il carico.
  - ✅ **9. La distanza esatta, 2026-10-06, 16:00–16:21.**
    > **Note implementazione**:
    > - **il test rosso** (test-author, agente `edbd3550…`), in
    >   `test_pac_planner_report.py`, sezione 6.3:
    >   - due prove sulle coppie vere: `explicit_cost` di M 10×2 e `route_priority` del 10×3;
    >   - una scansione deterministica di 1000 coppie;
    >   - un caso con una differenza lunga 30 cifre:
    >     `test_published_absolute_gap_keeps_every_digit_of_a_long_difference` (`:1140`), con
    >     l'aiuto `_fixed_point_text` (`:1079`);
    >   - il caso «nessun primal → nessuna distanza».
    >
    >   Prova del rosso a carico 22,89: 4 rossi, 35 verdi, ciascuno per il motivo giusto:
    >   - le due coppie: `ValidationError` a `planner_report.py:902`;
    >   - la scansione: 416 rifiutate, 429 inesatte;
    >   - il caso a 30 cifre: accettato ma inesatto, pubblicava `18.000000000024766` invece di
    >     `18.0000000000247654321098765433`.
    > - **tre scostamenti del test-author dalla mia richiesta**, che ho letto e accetto:
    >   - il caso a 30 cifre controlla `rounded < Decimal(gap_text)` invece di `!=`: prova che
    >     un contesto Decimal a 28 cifre farebbe scendere la distanza sotto quella vera, cioè
    >     proprio il rifiuto del validatore;
    >   - un `Context(prec=28, rounding=ROUND_HALF_EVEN)` esplicito, che non dipende dal
    >     contesto globale;
    >   - l'aiuto `_fixed_point_text`, che scrive i valori attesi senza notazione esponenziale.
    > - **la correzione**, in `planner_report.py`:
    >   - un aiuto nuovo, `_published_gap`, subito dopo `_float_text`. Se i due limiti sono
    >     pubblicati, la distanza è `ratio_to_fixed_decimal(abs(ExactRatio(primal) −
    >     ExactRatio(dual)))`, calcolata sui due testi scritti. Se ne manca uno resta il numero del
    >     solver: non c'è niente da sottrarre;
    >   - in `build_solver_evidence` il primal e il dual si scrivono una volta sola, e la distanza
    >     li riusa;
    >   - un paragrafo nella docstring di `build_solver_evidence`.
    >
    >   I limiti infiniti arrivano già come `None` (`solver._finite_or_none`), quindi `Decimal()`
    >   vede solo testi finiti. `ExactRatio` ha già `from_decimal`, la sottrazione e `abs()`
    >   (`numeric.py:78`, `:114`, `:130`), e gli import c'erano già.
    > - **il limite noto:** il testo della distanza ha al massimo 96 caratteri, come quello di
    >   primal e dual (`PlannerNonNegativeDecimal`, `schemas/pac_allocator.py:237-240`). Una
    >   distanza più lunga solleva `WireNumberTooLargeError` invece di essere arrotondata; ci
    >   vogliono due limiti lontani una ottantina di ordini di grandezza. Nessun ripiego, per
    >   YAGNI.
    > - **schema, validatore e fingerprint non cambiano** (PAC `4f061103…58bb`, Rebalancer
    >   `be2bb19d…2e62`).
    > - **gli statici:** ruff e black sul file e sul test, verdi.
    > - **le suite**, una per volta:
    >
    >   | Suite | Carico | Verdi |
    >   |---|---|---|
    >   | report | 51,60 | 39, compresi i 4 rossi |
    >   | service | 42,10 | 44 |
    >   | `schemas pac-planner` | 36,55 | 543; i due test dei fingerprint, PAC e Rebalancer, verdi |
    >   | solver | 31,69 | 40 |
    >   | proof | 27,50 | 30 |
    >
    >   I log sono `/tmp/libreFolio_d_s3_gap_{report,service,schemas,solver,proof}.log`.
    > - **la diagnostica intera**, 16:18–16:21, a carico da 24,18 a 19,57, in discesa. Comando con
    >   `--compare` sul registro di prima di S3; il registro nuovo è
    >   `files/S3/probe_after_gapfix_2026-10-06.json` della sessione, il log
    >   `/tmp/libreFolio_d_s3_probe_gapfix.log`. I tre CHECKS passano:
    >
    >   | Variante | Prima di S3 | Dopo S3, senza il punto 9 | Ora |
    >   |---|---|---|---|
    >   | M 5×2 | 30,03 s, non dimostrato, (475, 25, 12, 279/40, 8) | 28,05 s, dimostrato, (475, 25, 9, 239/40, 6) | 26,33 s, dimostrato, uguale: PASS `==` |
    >   | M 10×2 | nessun piano | nessun piano | 29,69 s, `not_proven`/`time_limit`, (3100, 35, 15, 1593/200, 10): PASS `<=` |
    >   | realistico 10×3 | 30,07 s, non dimostrato, (11098593/2500, 333/10, 25, 1049/50, 13) | nessun piano | 30,03 s, `not_proven`/`time_limit`, (11098593/2500, 333/10, 15, 1549/100, 10): PASS `<=` |
    >
    >   Delle altre 20 varianti, 19 danno lo stesso piano di prima di S3, con la prova;
    >   `m-5x2_ratezero_fixed_both` è «migliorata», come al punto 8.
    >
    >   Sul 10×3 il piano trovato ora è migliore: 10 ordini invece di 13, e commissioni di 15,49
    >   invece di 20,98.
    > **⚠️ Fuori pista**: M 5×2 chiude la prova in 26,33 s, con 3,7 s di margine sui 30. Il margine
    > si misura in S5, che decide anche la riserva.
- ✅ **C901 — `normalize.py:461`, 2026-10-06, 15:55** (chiesto dal coordinator alle 15:50, commit
  `chore(pac)` a sé).
  > **Note implementazione**:
  > - la causa: `ac18ce097` (la compattazione) ha reso facoltativo `transfer_cap`. Il blocco
  >   `if item.transfer_cap is not None:` porta `validate_funding_routes` da 10 a 11. Ruff sulla
  >   versione di prima passa;
  > - perché è arrivato sul target: gli statici della compattazione
  >   (`plan-phase00PacContractCompaction.prompt.md:363-367`) non avevano il lint del backend. Ora
  >   `dev.py lint` è nella §8;
  > - la scelta è il `# noqa: C901` con il motivo sulla stessa riga, non la scomposizione:
  >   - il blocco da spostare sarebbe il controllo della fonte (una cassa o un contributo), con
  >     quattro rami d'errore: `reference_not_found` ×2 e `currency_mismatch` ×2;
  >   - nessun test fa passare quei rami dal normalizzatore. I test lo attraversano solo con fonti
  >     valide: `test_pac_planner_normalize.py:664` e `:1647` (cassa), `:1666` e
  >     `test_pac_planner_planner.py:218`, `:772` (contributi);
  >   - i casi di `test_pac_planner_schemas.py:1111-1652` controllano solo che il messaggio
  >     d'errore passi dallo schema; evaluator, oracolo e policies costruiscono rotte già
  >     normalizzate;
  >   - quindi la scomposizione non è «coperta dai test esistenti», e per la regola del coordinator
  >     resta il `noqa`;
  > - il motivo scritto: «flat per-route field checks plus one source lookup per source kind», nello
  >   stile del progetto (161 `noqa: C901` in `backend/app`). Il codice non cambia;
  > - gate (carico 79,73): ruff e black sul file verdi; `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc
  >   pipenv run python dev.py lint` → «All checks passed!», exit 0 (log
  >   `/tmp/libreFolio_d_c901_devlint.log`). Nessuna suite: cambia solo un commento.
  > **⚠️ Fuori pista**: anche `funding_cap_negative` e `route_priority_negative` delle rotte di
  > finanziamento non hanno un test che passi dal normalizzatore. Per scomporre servono prima quei
  > test. Proposta per il backlog: farli scrivere al test-author dentro l'analisi del Rebalancer,
  > che riusa lo stesso normalizzatore.
- ✅ **S4 — i testi, 2026-10-06, chiuso alle 16:44.** Le docs EN sono partite in parallelo al
  test rosso del gap; chiavi, fallback e test frontend dopo S3 ✅.
  > **Note implementazione**:
  > - **i18n**, con `dev.py i18n update`, 8 chiavi × 4 lingue (log `/tmp/libreFolio_d_s4_i18n.log`):
  >   - `result.badges.help.optimalProven`: il testo P-d approvato;
  >   - `result.proof.floatingFinished`: il testo Q6, che finisce con «…è il migliore trovato, ma
  >     non è dimostrato che sia il migliore»;
  >   - `result.proof.help.status`, `.absoluteGap`, `.dual`: i tre aiuti approvati;
  >   - `result.proof.scopes.global` → «all plans», `.incumbent_face` → «only plans as good as the
  >     one found»;
  >   - `strategy.tieBreak`: una ricerca finita da sola dà sempre lo stesso piano, una fermata da
  >     un limite può darne un altro (§1.5).
  >
  >   Dopo l'update ogni lingua ha 4 498 chiavi foglia, e gli insiemi sono uguali.
  > - **Fallback EN:**
  >   - `model.ts`: il ramo Q6 sceglie `floatingFinished` solo con `stop_reason = completed`;
  >     con `time_limit` o `node_limit` resta `floatingUnfinished`;
  >   - `ProofPanel.svelte`: i tre aiuti, i due ambiti, `tieBreak` e il commento del ramo
  >     `not_proven`;
  >   - `StrategyStep.svelte`: `tieBreak`.
  >
  >   I 7 fallback dei due `.svelte` sono uguali a `en.json` (controllo con uno script, 0
  >   differenze). Quelli di `model.ts` li controlla il test nuovo.
  > - **Docs EN**, con il docs-writer: `user/tools/pac-allocator/index.en.md` (+7 −4).
  >   `mkdocs build` strict verde, 0 WARNING (`/tmp/libreFolio_d_s4_docs_build.log`).
  >   `check-links`: 81 link validi; l'unico rosso è D28, `#rolling-return` in it/fr/es
  >   (`/tmp/libreFolio_d_s4_docs_check-links.log`). Niente stamp: la pagina esiste solo in inglese.
  > - **Test**, scritto dal test-author: `planner/result/model.test.ts`, nuovo, 8 casi.
  >   - 6 casi sull'aiuto che apre il badge della prova, uno per combinazione di prova, esito e
  >     causa dello stop;
  >   - 1 caso di controllo sul risolutore delle chiavi;
  >   - 1 controllo sul catalogo: etichetta e aiuto di ogni badge prodotto dai casi devono essere
  >     uguali al testo di `en.json`.
  >
  >   Riga nel runner: `scripts/test_runner/_frontend_utility.py:258`, in `front-utility
  >   component-unit`.
  > - **Prova del rosso**, senza toccare file tracciati (`/tmp/libreFolio_d_s4_redproof.sh`):
  >   - il `model.ts` di HEAD copiato in un file temporaneo accanto all'originale, più una copia
  >     del test che importa quel file; `vitest run` con carico 60,36;
  >   - **2 rossi su 8**:
  >     - il caso 1 (`not_proven`, `incumbent_found`, `completed`): riceve `floatingUnfinished`,
  >       si aspetta `floatingFinished`. È il rosso vero di Q6;
  >     - il controllo sul catalogo: a HEAD il fallback di `optimalProven` è ancora il testo
  >       vecchio, diverso da `en.json`;
  >   - col `model.ts` del worktree: 8 su 8 verdi;
  >   - i due file temporanei sono stati cancellati. Log `/tmp/libreFolio_d_s4_redproof.log`.
  > - **Gate:**
  >   - Prettier verde su `model.ts` e `model.test.ts`;
  >   - `front-utility component-unit`, 16:41–16:44, carico 64,31: 98 file, 2 231 test, tutti
  >     verdi. La lista del runner ha 98 voci: le 97 di HEAD più `model.test.ts`, quindi il test
  >     nuovo ha girato (`/tmp/libreFolio_d_s6_front_component_unit.log`);
  >   - `check-orphans` verde: ogni test è registrato e raggiungibile
  >     (`/tmp/libreFolio_d_s6_check_orphans.log`).
  > **⚠️ Fuori pista**:
  > - il test frontend non era nel brief di S2. Il ramo Q6 è logica di `model.ts` e senza un test
  >   sarebbe rimasto scoperto, quindi l'ho chiesto al test-author in S4. La riga del runner è
  >   additiva, come chiede la §10 per `_frontend_utility.py`, che è condiviso;
  > - `ProofPanel.svelte` e `StrategyStep.svelte` non passano Prettier, ma già a HEAD. Ho
  >   confrontato la differenza fra file e file formattato, a HEAD e nel worktree: è identica
  >   (`ProofPanel :95-131`; `StrategyStep :50-58` e `:88-94`) e non tocca le mie righe. Non li
  >   riformatto, per non allargare il diff (`/tmp/libreFolio_d_s4_prettier_drift.log`);
  > - il badge del caso «nessun ordine» (`no_op`) non ha un caso nel test nuovo. Il test-author ne
  >   ha proposto un settimo: lo metto nel backlog del coordinator.
  > **⚠️ Fuori pista** (all'avvio delle docs): le docs EN partono prima della chiusura di S3. La pagina non dipende dalla
  > correzione del gap: dipende da P-c e dalla guardia, già nel worktree e verdi. Il docs-writer
  > tocca solo `user/tools/pac-allocator/index.en.md` (`:41`, `:83`, `:139-142`; la `:40` è di N),
  > in inglese e senza stamp, perché la pagina non ha traduzioni. Usa i testi della §13.8, con una
  > sola differenza: la `:83` finisce come l'aiuto scelto dal developer, «…it is the best plan
  > found, but it is not proven to be the best», non «…not a proven best». Le chiavi i18n, i
  > fallback e il commento di `ProofPanel.svelte` si fanno dopo S3 ✅.
- ✅ **S5 — voce 13, 2026-10-06, 16:24–16:30.** La riserva resta 2 000 ms; cambiano solo i commenti.
  > **Note implementazione**:
  > - **Come.** Una sonda in-process della sessione (`files/S5/timing_probe.py`, non nel repo)
  >   cronometra le fasi intorno al solver negli stessi punti del worker:
  >   - *prima*: normalizzazione, vista esatta e compilazione;
  >   - *SCIP*: la ricerca;
  >   - *dopo*: ricontrollo esatto, integrazioni, prova e report. È ciò che la riserva copre;
  >   - *ser* e *out*: la conversione in JSON e il controllo stretto dell'output. Il worker li
  >     fa dopo `compute`, quindi fuori dalla riserva.
  > - **Corsa 1**, 16:24–16:27: M 5×2, M 10×2 e realistico 10×3, budget 30 s, due ripetizioni.
  >   Log `/tmp/libreFolio_d_s5_timing_run1.log`; record di sessione `files/S5/timing_2026-10-06_run1.json`.
  >
  >   | Variante | Carico | Prima ms | SCIP ms | Sforo ms | Dopo ms | ser+out ms | Byte | Esito |
  >   |---|---|---|---|---|---|---|---|---|
  >   | M 5×2 | 27,65 | 16,1 | 24 811,7 | −5 188,3 | 7,1 | 1,4 | 18 914 | `optimal_proven`, `completed` |
  >   | M 10×2 | 25,98 | 9,4 | 29 579,8 | −420,2 | 10,2 | 1,9 | 27 739 | `not_proven`, `time_limit` |
  >   | realistico 10×3 | 25,80 | 12,4 | 30 007,8 | +7,8 | 12,9 | 2,8 | 28 545 | `not_proven`, `time_limit` |
  >   | M 5×2 | 21,19 | 6,0 | 28 949,1 | −1 050,9 | 6,5 | 1,7 | 18 914 | `optimal_proven`, `completed` |
  >   | M 10×2 | 20,01 | 9,3 | 29 704,5 | −295,5 | 11,0 | 2,2 | 27 784 | `not_proven`, `time_limit` |
  >   | realistico 10×3 | 16,51 | 12,9 | 30 007,2 | +7,2 | 12,9 | 1,9 | 28 548 | `not_proven`, `time_limit` |
  >
  > - **Corsa 2**, 16:28–16:30: solo M 5×2, quattro ripetizioni, con i secondi di ogni stadio (la
  >   sonda ora li legge dal risultato del solver). Log `/tmp/libreFolio_d_s5_timing_run2.log`;
  >   record `files/S5/timing_2026-10-06_run2_m5x2.json`.
  >
  >   | Carico prima → dopo | Stadio 1 (`fixed_l2`) | Stadio 2 (`shortfall`) | Resto | SCIP totale | Dopo ms | Esito |
  >   |---|---|---|---|---|---|---|
  >   | 10,70 → 8,68 | 21,57 s | 2,95 s | 0,18 s | 24,74 s | 7,3 | `optimal_proven` |
  >   | 8,68 → 8,02 | 21,49 s | 2,90 s | 0,17 s | 24,61 s | 6,4 | `optimal_proven` |
  >   | 8,02 → 6,79 | 21,19 s | 2,86 s | 0,17 s | 24,27 s | 6,7 | `optimal_proven` |
  >   | 6,79 → 6,44 | 22,12 s | 3,42 s | 0,21 s | 25,80 s | 6,8 | `optimal_proven` |
  >
  > - **Cosa dicono i numeri:**
  >   - il lavoro dopo il solver prende 6,4–12,9 ms, contro i 2 000 riservati: circa 150 volte meno;
  >   - SCIP sfora il suo budget al massimo di 7,8 ms;
  >   - conversione e controllo dell'output, fuori dalla riserva, prendono al massimo 2,8 ms. Il
  >     risultato più grosso pesa 28,5 KB, contro il tetto di 512 KB;
  >   - la riserva non toglie nulla al solver: si controlla una volta sola, quando la finestra viene
  >     chiesta. Basta che dei 44 000 ms della finestra «soft» ne restino 30 000 + 2 000. La finestra
  >     parte quando il lavoro ottiene il suo posto (`executor.py:446`), avvio del processo figlio
  >     compreso.
  > - **M 5×2 tiene la prova in tutte e 6 le corse.** Lo stadio 1 chiude in 21,2–22,1 s, contro il suo
  >   limite di 27 s (30 meno i 3 di riserva di S3). Il totale va da 24,3 a 28,9 s.
  > - **I commenti**, in `tool_plugins/pac_allocator.py`:
  >   - `:72-78`: i numeri nuovi e il rimando a questo piano, al posto di «provisional»;
  >   - `:172-187`: le misure, perché la riserva non costa nulla, e cosa resta fuori.
  > - **Il piano Step3**, voce 13: una nota datata, «fatto il 2026-10-06», con il link qui.
  > - **Gate:** ruff e black sul file, verdi. Nessuna suite: cambiano solo commenti. Le suite girano in S6.
  > **⚠️ Fuori pista**:
  > - con carico 21 il totale di M 5×2 è arrivato a 28,9 s, a un secondo dai 30. In quella corsa la
  >   sonda non leggeva ancora gli stadi: per questo c'è la corsa 2. Se il carico sale ancora, M 5×2
  >   può finire `not_proven`. È il comportamento voluto: un piano non dimostrato non si dichiara
  >   ottimo. Non è un difetto;
  > - per M 10×2 e per il 10×3 i byte cambiano fra una ripetizione e l'altra (27 739 e 27 784;
  >   28 545 e 28 548). Un piano fermato dal tempo può cambiare da una corsa all'altra. Il testo di
  >   `strategy.tieBreak` (§1.5) lo dice già.
- ✅ **S6 — i gate, 2026-10-06, 16:32–16:52.** Tutti verdi; l'unico rosso è il D28, che è accettato.
  Ogni comando ha il prefisso della §8, e ne gira uno per volta sulla 6151.
  > **Note implementazione**:
  > - **le build prima dei gate col backend** (R14.8):
  >   - `api sync` alle 16:32;
  >   - `front build --debug` dalle 16:33 alle 16:35;
  >   - `mkdocs build` dalle 16:35 alle 16:36, strict, verde.
  >
  >   I log sono `/tmp/libreFolio_d_s6_{api_sync,front_build,mkdocs_build}.log`.
  > - **le 11 suite del backend**, dalle 16:36 alle 16:40, col carico prima di ognuna
  >   (`/tmp/libreFolio_d_s6_suites_summary.log`, un log per suite accanto):
  >
  >   | Suite | Carico | Verdi |
  >   |---|---|---|
  >   | `services pac-planner-core` | 29,63 | 177 |
  >   | `services pac-planner-evaluator` | 29,18 | 159 |
  >   | `services pac-planner-oracle` | 27,81 | 21 |
  >   | `services pac-planner-policies` | 27,50 | 40 |
  >   | `services pac-planner-solver` | 27,22 | 40, con B1 a 13 parametri su 13 |
  >   | `services pac-planner-proof` | 27,01 | 30 |
  >   | `services pac-planner-wire-numbers` | 26,69 | 39 |
  >   | `services pac-planner-report` | 26,69 | 39 |
  >   | `services pac-planner-service` | 26,07 | 44 |
  >   | `schemas pac-planner` | 25,76 | 543, con i due fingerprint |
  >   | `api pac-planner-tool` | 25,76 | 7 |
  >
  >   Nessun rosso e nessun errore. Le 13 funzioni di test di S2 e le 4 del gap (S3) sono tutte fra
  >   i verdi.
  > - **`front-utility component-unit`**, dalle 16:41 alle 16:44, carico 64,31: 98 file, 2 231 test,
  >   tutti verdi. Il runner ne elenca 98: i 97 di HEAD più `model.test.ts`, quindi il test nuovo
  >   ha girato. Log `/tmp/libreFolio_d_s6_front_component_unit.log`.
  > - **gli statici:**
  >   - `check-orphans`, alle 16:44: verde;
  >   - `front check`, dalle 16:46 alle 16:48, carico 98,5: «svelte-check found 0 errors and 0
  >     warnings». Il client era quello generato alle 16:37:45 (vedi il Fuori pista);
  >   - `i18n audit`, alle 16:49:
  >     - 4 498 chiavi in ognuna delle 4 lingue, nessuna mancante;
  >     - le probabili inutilizzate restano 521, il numero già nel backlog;
  >     - `proof.help.absoluteGap` e `.dual` compaiono sotto «Not Verified», insieme a `primal` e
  >       `relativeGap` che non ho toccato. È una famiglia di chiavi lette per nome composto: non è
  >       la prova che non servano;
  >   - `mkdocs check-links`, alle 16:50: rosso solo per il D28 (`#rolling-return` in it/fr/es),
  >     quello accettato; 81 link validi;
  >   - `dev.py lint`, alle 16:50: «All checks passed!»;
  >   - ruff e black sugli 11 file Python toccati: verdi;
  >   - `git diff --check`: pulito. Sui 4 file nuovi, `git diff --no-index --check`: 0 problemi.
  >
  >   I log sono `/tmp/libreFolio_d_s6_{check_orphans,front_check,i18n_audit,mkdocs_check_links,devlint,ruff,black}.log`.
  > - **la diagnostica su richiesta (§8.5)**: vale la corsa delle 16:18–16:21 di S3 (voce del gap),
  >   col carico in discesa da 24,18 a 19,57, cioè il livello normale della giornata, non un picco.
  >   Gira già sul codice finale:
  >   - l'ultimo file del backend usato dalla sonda è `planner_report.py`, salvato alle 16:14:50;
  >   - dopo è cambiato soltanto `tool_plugins/pac_allocator.py` (S5), con zero righe che non siano
  >     commenti;
  >   - frontend, i18n e docs restano fuori dalla sonda.
  >
  >   Quindi non l'ho ripetuta: sotto i picchi di questa ora (64–98) i tempi non sarebbero
  >   confrontabili. Il confronto delle 15 varianti col registro di prima di S3 è in
  >   `/tmp/libreFolio_d_s6_dod15.log`: 15 su 15 identiche.
  > - **le porte**: `lsof -nP -iTCP:6151 -sTCP:LISTEN` e `…:6161…`, vuoti alle 16:51:54.
  >
  > **⚠️ Fuori pista**:
  > - **il runner ha rifatto la build del frontend all'avvio della suite API.** Il test-author ha
  >   creato `model.test.ts` alle 16:36:34, dopo la build di debug. Il runner
  >   (`check_frontend_needs_build`, `scripts/cli_base.py:537-582`) confronta ogni file sotto
  >   `frontend/src`, compresi i `.test.ts`, con `frontend/build/index.html`. Quindi all'avvio di
  >   `api pac-planner-tool` (16:37:32) ha rifatto la build, e prima ha rilanciato `api sync`:
  >   - il client è stato rigenerato alle 16:37:45 (`generated.ts`) e alle 16:37:47
  >     (`tool-contract-map.generated.ts`), dallo stesso codice backend;
  >   - la build è finita alle 16:40:26; il primo test è partito alle 16:40:37, dopo circa 3
  >     minuti di avvio;
  >   - la suite è passata 7 su 7, e il fingerprint PAC non è cambiato.
  >
  >   L'ordine R14.8 si è rotto per l'ora in cui è arrivato il file, non per una scelta.
  >   `frontend/build` ora contiene la build del runner, non quella di debug: è un artefatto
  >   ignorato. Il miglioramento possibile del runner, cioè ignorare i `*.test.ts` nel controllo,
  >   va nel backlog del coordinator;
  > - **la diagnostica §8.5 non è stata ripetuta**: le ragioni sono qui sopra.
- ✅ **S7 — l'handoff, 2026-10-06, 16:53–17:05.** CHECKPOINT READY inviato al coordinator, poi FROZEN.
  > **Note implementazione**:
  > - **la riga 12 del README** è ✅ «consegnato il 2026-10-06»; gli SHA arrivano all'integrazione.
  >   Lo stato in testa a questo piano è ✅;
  > - **tre commit proposti**, con messaggi in ASCII (righe ≤ 69 caratteri). I file sono in `/tmp` e
  >   nei file della sessione, in `files/S7/`:
  >   1. `chore(pac): waive C901 on funding-route checks`, solo `normalize.py`
  >      (`/tmp/libreFolio_commit_d_slice_1_chore.txt`);
  >   2. `fix(pac): harden the solver cascade and its proofs`: backend, test, frontend, i18n ×4, la
  >      pagina EN e la riga del runner (`/tmp/libreFolio_commit_d_slice_2_fix.txt`);
  >   3. `docs(journal): close the PAC solver robustness slice`: README, questo piano e la nota della
  >      voce 13 nello Step 3 (`/tmp/libreFolio_commit_d_slice_3_journal.txt`);
  > - **i18n**: cambiano 8 chiavi, le stesse nelle 4 lingue; nessuna aggiunta e nessuna tolta; 4 498
  >   chiavi per lingua. Sono `badges.help.optimalProven`, `proof.floatingFinished`,
  >   `proof.scopes.{global,incumbent_face}`, `proof.help.{status,dual,absoluteGap}` (sotto
  >   `tools.pacAllocator.planner.result`) e `tools.pacAllocator.planner.strategy.tieBreak`;
  > - **la frase di CHANGELOG** sostituisce due frasi del punto «PAC allocator» (riga 18, uguale in
  >   `d9aad0ec9` e in `dev_release2` `6addaba05`). Prima:
  >
  >   > Every answer says what it is worth: proven optimal, the best plan found when optimality could
  >   > not be proven, proven infeasible, or no plan within the calculation limits. These are never
  >   > presented as the same thing, and missing or invalid inputs are reported rather than guessed.
  >
  >   Dopo:
  >
  >   > Every answer says what it is worth: proven optimal, the best plan found, proven infeasible, or
  >   > no plan within the calculation limits. A plan is called optimal only when the solver has
  >   > closed every objective and an exact check of the plan confirms its numbers, within the
  >   > solver's small calculation margin; otherwise it is the best plan found, not proven to be the
  >   > best. These are never presented as the same thing, and missing or invalid inputs are reported
  >   > rather than guessed.
  >
  >   Facoltativa, dopo «calculation limits»: «When time runs out, the time held in reserve can still
  >   lower fees and the number of orders without worsening the main goal.» Nessuna riga 🐛: il PAC è ancora in
  >   `[Unreleased]`, quindi le correzioni entrano nel suo punto ✨. Il CHANGELOG lo scrive il
  >   coordinator;
  > - **proposte per il backlog**, nuove rispetto alla §13.11:
  >   1. i test del normalizzatore per le rotte di finanziamento (`funding_cap_negative`,
  >      `route_priority_negative`), prima di scomporre la funzione del C901 e togliere il `noqa`;
  >   2. `floatingFinished` ora si usa (`model.ts:113`) e l'audit di S6 non la elenca più: va tolta
  >      dal backlog delle chiavi inutilizzate;
  >   3. un settimo caso in `CASES` di `model.test.ts`, per il badge `no_op`;
  >   4. il runner: `check_frontend_needs_build` (`scripts/cli_base.py:537-582`) dovrebbe ignorare i
  >      `*.test.ts`;
  >   5. la deriva Prettier che c'era già a HEAD: `ProofPanel.svelte :95-131`,
  >      `StrategyStep.svelte :50-58` e `:88-94`;
  > - **i controlli, alle 17:01:29** (carico 7,57): `git diff --check` pulito; sui 4 file nuovi,
  >   `git diff --no-index --check`: 0 problemi; stage vuoto; `lsof -nP -iTCP:6151 -sTCP:LISTEN` e
  >   `…:6161…` vuoti. Ripetuti dopo questa voce;
  > - **l'unione con `dev_release2` `6addaba05`, simulata alle 17:05** con `git merge-file -p`, che
  >   scrive solo su stdout (`/tmp/libreFolio_d_s7_mergesim.sh`, log `.log` accanto). Dalla base
  >   comune `7038c2224` sono arrivati 26 commit e 64 file; 5 sono anche miei:
  >   - i18n ×4: 0 conflitti. Io cambio 8 chiavi, loro 13, nessuna in comune e nessuna sotto
  >     `tools.pacAllocator`. Il risultato è un JSON valido di 4 505 chiavi, senza chiavi perse;
  >   - `_frontend_utility.py`: 0 conflitti; il risultato è il loro file più la mia riga;
  > - **`core-unit` non l'ho lanciato:** i suoi test PAC (`allocationSource`, `decimal`, `format`)
  >   coprono file che non ho toccato, e nessun suo test importa `result/model`, `ProofPanel` o
  >   `StrategyStep`. L'unico test sui cataloghi (`HeaderToggles.i18n.test.ts`) è in
  >   `component-unit`, verde in S6;
  > - **pulizia di `/tmp`**: tolti 15 file miei di prova, non citati qui (gli script `s2_*` e `s3_*`,
  >   il diff `s3_solver.diff`, i tre `s4_*` intermedi di Prettier e la lista temporanea di S7). Restano i log citati,
  >   `libreFolio_d_s3_gates.sh`, `libreFolio_d_s4_redproof.sh`, `libreFolio_d_s4_prettier_drift.sh`,
  >   `libreFolio_d_s6_suites.sh` e `libreFolio_d_s6_dod15.py`, che hanno prodotto i log, e la
  >   cartella `libreFolio_d_s3_dbg/` con i log del difetto del gap.
  >
  > **⚠️ Fuori pista**: nessuno.

## 13. Esito della review (S1)

- **Chi e quando:** agente `general-purpose`, 2026-10-06, in sola lettura su `8c98a03c1`.
- **Rapporto:** `files/review_S1/review2_S1_report.md` della sessione, con accanto le sonde e i log
  `review2_*`.
- **STOP CONTRATTO: no.** Tutte le correzioni raccomandate passano i validatori di oggi. Lo prova la
  sonda `review2_wire`:
  - accettati: W1 (`completed` con `not_proven`, tutti gli stadi chiusi), W3 (R10 α), W4 e W5 (la
    coda di A1);
  - rifiutati, giustamente: W2 (il caso R10 di oggi) e i controlli W6 e W7.

### 13.1 Riepilogo

| Q | Decisione | Codice (S3) | Test (S2) |
|---|---|---|---|
| Q0 | la causa del 474,9999988; falsa infeasibilità verso 1e10 | commento `solver.py:88-97`; la guardia, se approvata | 5×1 con gli importi ×10^8 |
| Q1 | blocco al massimo, anche sugli stadi interi | `_pin_value`, `_solve_stages` | sottoclasse di `compiler.Model` |
| Q2 | tolleranza relativa più n·1e-6, posto (iii) | fine di `_solve_stages` | valori spostati; 13 fixture verdi |
| Q3 | R = min(3 s; 0,1·B), g1, ripresa | coda e ripresa | `node_limit=1`; infeasible e `no_incumbent` invariati |
| Q4 | solo α | `build_solver_evidence` | la leva di `r10_demo` |
| Q5 | decide il primo stadio non finito | `build_stop_reason` e docstring | `SolverRunResult` costruiti a mano |
| Q6 | (ii), con testi nuovi | `model.ts`, i18n ×4, `ProofPanel`, docs | vitest solo se nasce |
| Q7 | N·μ è giusto | nessuno | nessuno |
| Q8 | correzioni al piano, leve | docstring | le leve |

### 13.2 Q0 — da dove viene il 474,9999988

- **(a) La causa.** Su M 5×2, 2 delle 5 righe che misurano la distanza al quadrato (`fixed_l2`)
  stanno circa 6e-7 sotto il quadrato esatto.
  - Per SCIP sono righe non lineari, e le accetta con una tolleranza ASSOLUTA di 1e-6.
  - I quadrati esatti sono 400, 25, 25, 25 e 0. Gli scarti sono 0, +5,9e-13, −5,89e-7, −6,01e-7 e 0.
  - La somma fa 474,9999988102287, cioè 475 − 1,190e-6. Il rumore dei calcoli in virgola mobile è
    di circa 1e-13: lo scarto viene dalla tolleranza, non dal rumore.
- **(b) I piani si perdono nella ricerca, non nel controllo finale.** Con il piano da 6 ordini fissato
  e il blocco di oggi:
  - con il presolve predefinito esce `optimal` a 474,99999999592, perché le righe lineari si
    controllano in modo relativo (4,75e-4 su 475);
  - con presolve e propagazione spenti, cioè con la sola ricerca sul rilassamento lineare, è
    infeasible;
  - con il blocco esatto, 475·(1 + 1e-12), è `optimal`.

  Quindi lo stadio 3 «dimostra» 11, e oggi M 5×2 pubblica (475, 25, 10, 239/40, 7) con «Ottimo
  dimostrato», mentre il piano giusto è (475, 25, 9, 239/40, 6).
- **(c) Il commento per `solver.py:88-97`**, in inglese:
  ```text
  # Not an economic or policy epsilon. A stage pin must never fall below the
  # exact value of the candidate that produced it, and SCIP's primal is not safe
  # for that: each fixed_l2 epigraph row ``residual_sq >= residual**2`` is
  # nonlinear and accepted with an ABSOLUTE numerics/feastol (1e-6, unscaled),
  # so the stage value can sit up to that much per asset below the exact value
  # (M 5x2: 474.9999988 for an exact 475). A pin there cuts equally good plans in
  # a path-dependent way: the final solution check accepts them (linear rows are
  # compared relatively), while the LP relaxation (absolute tolerance) prunes
  # them. Hence the pin is max(SCIP primal, exact candidate value) plus this
  # relative slack, which only covers the float rounding of that exact value.
  # A later stage can still worsen a pinned stage within the solver's
  # tolerances. The relative slack is not applied to provably integral stages
  # (see ``_INTEGRAL_STAGE_CODES``).
  ```
- **(d) Gli importi grandi.**
  - Il wire accetta importi fino a circa 1e95: stringhe di 96 caratteri
    (`schemas/pac_allocator.py:228-249`), controllate solo sulle cifre (`normalize.py:86`, `:143`).
    È contro la §18 di MathematicalCore.
  - 5×1 con tutti gli importi moltiplicati per 10^k: con k = 0, 3, 5, 6 e 7 va tutto bene.
  - Con k = 8 (prezzi da 2e9 a 5e9, cassa 1,5e11, obiettivo 3e10 per Asset) esce un falso
    `ready_infeasible`, con `infeasibility_proven` e `completed`. Eppure il piano vuoto e le quantità
    di k = 6 sono esattamente ammissibili. Con k = 9 succede lo stesso.
  - L'infinito di SCIP è 1e20, e i quadrati passano da 9e18 a 9e20.
  - `review_tol`: i punti ammissibili sono accettati 40 su 40 fino a 1e4, 31–32 su 40 fra 1e5 e 1e6.
    I punti fuori di 2e-6 sono accettati 0 su 40 fino a 1e4, 5 su 40 a 1e5, 30–32 su 40 da 3e5.
  - Sono importi realistici in VND, IDR o IRR.
- **La guardia proposta.** In `_no_incumbent_result` il piano vuoto è già valutato
  (`_zero_candidate_evaluation`, `planner.py:250`). Se il solver dice «infeasible» e il piano vuoto è
  ammissibile, il motore solleva un errore di difetto, come `ExactReplayRejectedError`, invece di
  pubblicare una prova falsa.
- **Rinviati:** il modello in scala e un tetto agli importi.
- **Resta scoperto:** la guardia copre solo il caso del piano vuoto ammissibile.

### 13.3 Q1 — il blocco (P-a)

- **Regola:** `m = max(primal, valore esatto)`, blocco `m + |m|·1e-12`; l'1e-12 resta. Sugli stadi
  interi, `max(round(primal), valore esatto)`. Il big-M è a `constraints.py:562`.
- **Se il candidato non è valido** (`candidate_valid=False`): il blocco di oggi, più un'anomalia.
- **Perché il massimo e non il solo valore esatto:** su `explicit_cost` l'esatto è 5,975 e SCIP dà
  5,9750016. Col solo esatto il blocco potrebbe tagliare la soluzione che SCIP ha salvato.
- **Evidenza:**
  - blocco a 475,000000000475 → (475, 25, 9, 239/40, 6), 15 stadi su 15, 25,11 s. Il prototipo
    «solo esatto» ci metteva 27,80 s;
  - `shortfall` scende da 7,54 s a 2,88 s;
  - nella coda `getNSols` vale 10;
  - 12 casi piccoli danno lo stesso piano.
- **Resta:** uno scarto possibile di `1e-6·|m| + n·1e-6`.
- **Frase EN:** "Each criterion is optimal within the solver's numerical precision: a later
  criterion can pick a plan that is worse on an earlier one by less than that precision."

### 13.4 Q2 — il controllo fra piano ed evidenza (P-c)

- **Tolleranza:** `tol = 1e-6·max(1, |limite|)`, più `n·1e-6` per `fixed_l2`.
- **Stadi interi:** allarme se `v < ceil(duale − 1e-6)` oppure `v > round(primal)`.
- **Spareggi:** saltati (`objectives.py:231`, `planner_report.py:890`). Controllo facoltativo:
  quantità == `round(primal)`.
- **Posto (iii):** alla fine di `_solve_stages`, sul candidato finale, che è proprio quello pubblicato
  (`published=search.candidate`, `planner.py:162-168`). Se il candidato non è valido, il controllo
  tace.
- **M 5×2:** la regola relativa scatta solo su `route_priority` (10 contro un duale di 11). Quella
  assoluta scatterebbe anche su `fixed_l2` (+1,19e-6) e su `explicit_cost` (−1,58e-6).
- **13 fixture:** 0 allarmi; lo scarto peggiore è +7,4e-11. W1 accettato.
- **Chi legge `anomaly`:** `proof.py:195`, `:204`; i test `test_pac_planner_solver.py:356`, `:392` e
  `test_pac_planner_proof.py:167-190`, `:386-393`. La docstring dello schema a `:986` resta vera.
- **Resta:** un errore di circa 1e-16·c², quando l'obiettivo per Asset (c) supera 1e5.
- **Scostamento dall'analisi approvata:** la §5.3 metteva P-c in `planner.py`/`proof.py`; qui sta nel
  solver. Stesso comportamento, meno superficie.

### 13.5 Q3 — la coda dopo il limite (A1)

- **Regola:** R = min(3 s; 0,1·B); la coda divisa come nella §4.3; la guardia g1. Non serve dare a
  SCIP una soluzione di partenza.
- **Ripresa:** se lo stadio 1 arriva al limite senza nessuna soluzione, `limits/time` diventa il primo
  limite + R, con un nuovo `optimize()` senza `freeTransform`.
- **Perché 3 s:** con R = 6 s lo stadio 1 ha 24 s, contro corse da 22,04 a 24,00 s, e il resto vuole
  circa 3,2 s.
- **Il prezzo:** sul 10×3 gli spareggi finiscono `budget_exhausted`, quindi non è garantito che gli
  stessi dati diano sempre lo stesso piano.
- **Misure** (B = 30 s, la regola esatta della §4.3, nessun picco):

  | Caso | Carico | Stadio 1 | Piano | Prova | Wall |
  |---|---|---|---|---|---|
  | M 5×2, R = 6 | 6,48 | finito a 23,51 s (margine 0,49 s) | (475, 25, 9, 239/40, 6) | `optimal_proven` | 26,72 s |
  | M 10×2, R = 6 | 7,5 | limite a 24,00 s | (3100, 35, 15, 1593/200, 10) | `not_proven` | 28,05 s |
  | M 10×2, R = 3 | 9,5 | limite a 27 s | lo stesso, spareggi chiusi | `not_proven` | 29,59 s |
  | 10×3, R = 6 | 7,78 | limite a 24 s | (11098593/2500, 333/10, 15, 1549/100, 10) | `not_proven` | 29,23 s |
  | 10×3, R = 3 | 5,6 | limite a 27 s | lo stesso, spareggi `budget_exhausted` | `not_proven` | 30,01 s |

- **Sforamento:** ≤ +0,001 s per stadio; il wall meno B va da −3,28 a +0,01 s. Solo uno stadio può
  superare B, di 0,05 s (il minimo) più il tempo di Python.
- **g1:** ha tenuto il piano vecchio contro uno peggiore di (0, 0, +8, +149/50, +2), su `shortfall`.
- **SCIP tiene 10 soluzioni** (`limits/maxorigsol`); `createSol`/`addSol` servono solo come riserva.
- **Ripresa:** i nodi passano da 12 069 a 28 087, il tempo da 2 a 4 s. W4 e W5 accettati.

### 13.6 Q4 — gli spareggi interrotti (R10)

- **Solo α.** α è onesta: indebolisce un'affermazione, non ne inventa una.
- **β non serve:** i 30 spareggi del 10×3 costano 1,85 s, e la riserva R fa già il lavoro di β.
- **Meglio di così non si può senza cambiare il contratto:** il wire non mostra gli spareggi,
  `time_limit` vuole uno stadio non finito e `optimal_proven` vuole `tie_break_closed`.
- W3 accettato. W2 rifiutato con «Completed stops require no unfinished stage; limit stops require an
  unfinished stage».

### 13.7 Q5 — la causa dello stop

- Decide il primo stadio non finito di `SolverRunResult`, spareggi compresi. L'evidenza riscritta da
  α non si legge.
- Uno stadio della coda `unfinished` con stato `optimal` non decide.
- Con α decide lo spareggio (`timelimit`).
- `budget_exhausted`, un'anomalia o uno stato inatteso → `time_limit`.
- Nessun candidato → `no_incumbent`, con il limite dello stadio 1.
- Infeasible → `completed`.
- `node_limit` succede solo nei test.
- La regola di oggi è a `planner_report.py:986-989`.

### 13.8 Q6 — l'aiuto per «completato ma non dimostrato»

- **Raccomandata (ii).** Perché:
  - `proof.py:208` non si raggiunge (`planner.py:167`);
  - il motivo resta `allocation.exact_proof_not_established` (`proof.py:71`);
  - «circa un milionesimo» è falso con importi grandi;
  - «dice che non lo sa invece di tirare a indovinare» è vero solo con la guardia.
- **Trovati anche:**
  - gli aiuti `proof.help.status` e `proof.help.absoluteGap` sono falsi con A1: uno stadio non
    terminato può avere gap 0;
  - `proof.help.dual` è falso sugli stadi dopo il primo, che cercano solo fra i piani buoni quanto
    quello trovato (`solver.py:366`);
  - le etichette dell'ambito («global scope», «incumbent face») sono gergo.
- I testi EN della review sono nel rapporto (`:268-290`). Qui sotto ci sono quelli più semplici di D;
  sceglie il coordinator.

**Testi proposti** (EN e IT; FR ed ES seguono in S4):

| Chiave | EN | IT |
|---|---|---|
| `proof.floatingFinished` | The solver finished its search, but its own numbers do not match the exact check of this plan, so the proof does not hold. The plan respects every constraint: it is the best plan found, not a proven best. | Il solver ha finito la ricerca, ma i suoi numeri non tornano con il controllo esatto di questo piano, quindi la prova non regge. Il piano rispetta tutti i vincoli: è il migliore trovato, non un migliore dimostrato. |
| `badges.help.optimalProven` | The solver proved that no better plan exists, objective by objective in the order chosen in Strategy, and the exact check of the plan matches its numbers. The proof holds within the solver's small calculation margin, which grows with the amounts. | Il solver ha dimostrato che non esiste un piano migliore, obiettivo per obiettivo nell'ordine scelto in Strategia, e il controllo esatto del piano torna con i suoi numeri. La prova vale entro il piccolo margine di calcolo del solver, che cresce con gli importi. |
| `proof.help.status` | Whether the solver closed this stage. Finished: it proved the best value. Unfinished: it stopped at a limit. After a stage that stopped, the later ones only searched among plans as good as the one already found, so a gap of 0 there proves nothing. | Se il solver ha chiuso questo stadio. «Terminato»: ha dimostrato il valore migliore. «Non terminato»: si è fermato a un limite. Dopo uno stadio che si è fermato, i successivi hanno cercato solo fra i piani buoni quanto quello già trovato, quindi lì anche un gap 0 non dimostra niente. |
| `proof.help.absoluteGap` | Distance between the two values. A gap of 0 proves the best value only when the stage is finished. | Distanza fra i due valori. Un gap di 0 dimostra il valore migliore solo se lo stadio è terminato. |
| `proof.help.dual` | The bound the solver proved for this stage: none of the plans it searched can do better. From the second stage on, it searched only among plans as good as the chosen one on the stages above. | Il limite che il solver ha dimostrato per questo stadio: nessuno dei piani cercati può fare meglio. Dal secondo stadio in poi ha cercato solo fra i piani buoni quanto quello scelto negli stadi sopra. |
| `proof.scopes.global` (facoltativa) | all plans | tutti i piani |
| `proof.scopes.incumbent_face` (facoltativa) | only plans as good as the one found | solo piani buoni quanto quello trovato |

- **Commento di `ProofPanel.svelte:172`:** "Not proven: either a stage is still open, or every stage
  closed but the final exact check contradicted the solver's bounds; the badge help says which."
- **Docs EN** (`user/tools/pac-allocator/index.en.md`):
  - `:41`: "A fixed order of Assets and Brokers settles any final tie, so a search that completes
    always gives the same plan for the same data; a search stopped by a time or node limit can give a
    different plan on a slower or busier machine."
  - `:83`: "A plan that respects every constraint. It is marked **Proven optimal** when the solver
    proved, within its small calculation margin (which grows with the amounts), that no better plan
    exists, objective by objective in the order of the **Strategy** step. It is marked **Optimality
    not proven** when the solver reached its time or node limit, or when its own numbers do not match
    the exact check of the plan: it is then the best plan found, not a proven best."
  - `:139-142`: "**It never passes off an unproven plan as optimal.** A plan stopped by a time or
    node limit is shown as the best one found and marked **Optimality not proven**. So is a plan
    whose exact check does not match the solver's own numbers, even when the search ended by itself.
    When no plan is found, it says so instead of guessing."
- **Nota sull'ultima frase di `:139-142`.** «When no plan is found, it says so instead of guessing»
  regge solo con la guardia, e solo nel caso che la guardia copre. Se la guardia passa, propongo di
  aggiungere: "With amounts of around ten billion units of a currency or more, the solver's
  calculations can lose precision: the tool may then stop with an error, or mark the plan
  **Optimality not proven**." Il caso che resta scoperto va nel backlog, insieme al tetto agli
  importi.

### 13.9 Q7 — R3, il limite di arrotondamento N·μ

- **N·μ è giusto** (`evaluator.py:2272-2283`, `:2700-2706`).
- N·μ/2 respingerebbe S17. I crediti FX aggiungono solo margine, e il limite si ricontrolla dopo le
  integrazioni (`:3725-3729`).
- **S17 torna:** 3 × 33,335 = 100,005; addebito HALF_UP 100,01; saldo −0,01;
  `rounding_adjustment` +0,005; U = −0,005; l'identità di `:2285` dà −0,005 = −0,01 + 0,005;
  integrazione 0,01 ≤ 0,01; `ROUNDING_BOUND`: |0,005| ≤ 0,005 e −0,005 + 0,01 ≥ −0,005.
- **Resta:** la soglia è per cassa, mentre il margine è globale. Nel caso peggiore esce un errore di
  difetto, mai un piano sbagliato.

### 13.10 Q8 — correzioni al piano e leve per i test

- **Errori del piano, già corretti:**
  - il tetto delle route è 1000, non 10 (`probe_lib.py:43`); i €10 sono il tetto della fee variabile
    (`:34`); 29 quote su a00/b01;
  - b00 paga lo 0,1 %: 1,4925 dei 5,975 (0,595 + 0,2975 + 0,6);
  - «un milionesimo» è falso con importi grandi;
  - `solver.py:49` è solo un'annotazione di tipo (`compiler.py:165`);
  - R = 6 è troppo stretto;
  - la docstring di `build_stop_reason` (`:929-931`) dice il falso: ogni stadio riceve tutto il tempo
    rimasto. EN proposto: "each stage gets all of the remaining budget (stage 1 keeps a reserve for
    the tail, see ``solver.py``), and the cascade is what makes the answer unique."
- **Leve per i test:**
  - `node_limit=1` su M 5×2: 0,08 s; primal 4356,25, duale 75,07; candidato (17425/4, 65/2, 13,
    3187/400, 8);
  - la sottoclasse di `pyscipopt.Model` al posto di `compiler.Model`, oppure
    `dataclasses.replace(program, model=proxy)` (`CompiledProgram` è frozen, `compiler.py:103-116`).
    Assegnare il metodo sull'istanza non funziona: è in sola lettura;
  - un `SolverRunResult` costruito a mano.
- **Casi piccoli:** 12 configurazioni risolte (altre 6 non pronte o sopra il tetto dell'oracolo), tutte
  sotto 0,15 s, al massimo 3e-9 sotto l'esatto. Nessuna riproduce P-a.
- **Voce 13:** i 2 s sembrano bastare, ma la fase dopo il motore sul 10×3 non è cronometrata.
- **Le 15 varianti** (valori arrotondati; oggi danno lo stesso piano col blocco di produzione e col
  blocco esatto):
  - griglia M: 1x2 (1600, 40, 3, 3.96, 2); 2x2 (225, 15, 6, 4.985, 4); 5x2_samefee (75, 5, 9, 2.995,
    6); 5x2_fixedonly (75, 5, 9, 3, 6); 5x2_nofee (75, 5, 9, 0, 6); 5x2_disjoint (32150, 310, 7, 4.69,
    5); 5x1 (412.5, 20, 5, 1.48, 5); 10x1 (2518.75, 2.5, 10, 1.4975, 10);
  - realistica: 3x2 (2293.57, 24.77, 5, 5.49, 4); 5x2 (898.992, 17.43, 8, 7.98, 6); 8x2 (7249.56,
    14.28, 11, 10.47, 8); 12x2 (7802.8, 55.61, 12, 11.97, 9); 3x3 (381.034, 30.88, 11, 9.49, 6); 5x3
    (3689.11, 51.96, 11, 9.49, 6); 8x3 (3028.53, 42.39, 13, 12.49, 8).

### 13.11 Cosa ne segue

- **S3** segue l'ordine della §7.
- **Tre domande al coordinator** (inviate il 2026-10-06 alle 12:26; vedi il Fuori pista di S1 nella
  §12). **Risposte del developer**, raccolte dal coordinator e inviate alle 12:35, confermate alle
  14:21 dopo la chiusura dell'app:
  1. **Q6: scelta (ii), con un testo dedicato.** Vale solo quando lo stop è `completed`, con la
     chiave `proof.floatingFinished`. Il testo finisce così:
     - IT: «…Il piano rispetta tutti i vincoli: è il migliore trovato, ma non è dimostrato che sia il
       migliore.»
     - EN: "…The plan respects every constraint: it is the best plan found, but it is not proven to
       be the best."

     Il testo P-d di `badges.help.optimalProven` è approvato così com'è.
  2. **La guardia della §13.2: sì, in questa slice**, con una frase nella guida. È il punto 6 di S3:
     - prima il test rosso;
     - poi l'errore interno che esiste già, senza una chiave i18n nuova;
     - una frase nella pagina utente, solo in inglese.

     Il caso con acquisti obbligatori va nel backlog.
  3. **Gli aiuti: approvati i tre testi e anche le etichette dell'ambito.** Sono `status`,
     `absoluteGap`, `dual`, `proof.scopes.global` e `proof.scopes.incumbent_face`, nelle 4 lingue con
     `dev.py i18n update`, e con i fallback in inglese in `model.ts`.
- **Nessuna obiezione del coordinator** su P-c nel solver e sulla riserva di 3 s: sono annotati come
  Fuori pista nella §12.
- **Backlog:** le 4 voci qui sotto (il modello in scala, il tetto agli importi, il messaggio preciso,
  il margine per cassa) le ha registrate il coordinator. `hypothesis` era già nel backlog, con la sua
  risposta (d) al checkpoint del journal J1.
- **Scostamento:** P-c sta nel solver (posto iii), non in `planner.py`/`proof.py` come diceva la §5.3
  dell'analisi.
- **Proposte per il backlog:**
  - il modello in scala;
  - un tetto agli importi (§18 di MathematicalCore): un codice issue nuovo, quindi un salto di
    versione;
  - un messaggio preciso per la falsa infeasibilità: un codice nuovo, quindi un salto di versione;
  - un margine di arrotondamento per cassa;
  - `hypothesis`.
- **Sonde della review** (carico = `vm.loadavg` a 1 minuto, letto prima della corsa):

  | Sonda | Argomenti | Carico | Wall | Risultato |
  |---|---|---|---|---|
  | q0a | 5×2, B = 30 s | ~22 | 30,0 s | oggi: stadio 1 finito a 24,00 s, `shortfall` interrotto; 8 ordini, non dimostrati |
  | q0a | 5×2, B = 120 s | 9–10 | 31,27 s | 15 stadi su 15; stadio 3: 11, pubblicato 10 |
  | q0b | 5×2 | 9–10 | 25,11 s | catena al massimo → 6 ordini; `checkSol` accetta |
  | q0c | 5×2 | n.d. | < 2 s | solo LP → infeasible; blocco esatto → 475 |
  | scale | 5×1, k = 0–9 | n.d. | secondi | k ≤ 7 giusti; k = 8 e 9 falsa infeasibilità |
  | scale2 | 5×1 | n.d. | secondi | piano vuoto e piano di k = 6 ammissibili a k = 8 |
  | wire | 5×1 | 6,68 | ~2 s | W1, W3, W4, W5 accettati; W2, W6, W7 rifiutati |
  | a1 | M 5×2 / M 10×2 / 10×3, R = 6 | 6,48 / 7,5 / 7,78 | 26,72 / 28,05 / 29,23 s | tabella della §13.5 |
  | a1g | 10×3 / M 10×2, R = 3 | 5,6 / 9,5 | 30,01 / 29,59 s | tabella della §13.5 |
  | pc_oracle | 13 fixture | 6,35 | < 1 s | 0 allarmi di P-c |
  | small | leve, ripresa, 6 configurazioni | 10,25 | ~10 s | leve e ripresa OK; 4 risolte, 1 sopra il tetto, una 3×2 non pronta ferma la sonda; 0 riproduzioni |
  | small2 | 12 configurazioni | 18,01 | 2 s | 8 risolte, 4 non pronte; 0 riproduzioni, 0 allarmi |

  n.d.: il carico era stato letto, ma è andato perso. Sono sonde di correttezza, non di tempo.
