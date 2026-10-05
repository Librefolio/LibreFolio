# Piano D — Round 5 post-merge: UI PAC v2 nella build, poi review di dettaglio

**Stato:** APPROVATO dal developer il 24/09/2026 (uscita dal plan mode in autopilot); in esecuzione. I gate umani (delta ASCII, test list, runbook, STOP) restano fermate esplicite anche in autopilot.
**Baseline:** `f1047f766` (`dev_release2`), albero pulito, branch `e-alfy-allocatore-pac` — verificati il 23/09 e di nuovo il 24/09, prima del Passo 0.
**Posizione:** `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacRound5PostMerge.prompt.md`
(copia del piano di sessione approvato).
→ Delta C0: [`plan-phase00PacRound5-C0UiDelta.prompt.md`](plan-phase00PacRound5-C0UiDelta.prompt.md).
→ Successivo: [`plan-phase00PacContractCompaction.prompt.md`](plan-phase00PacContractCompaction.prompt.md) (compattazione del contratto 1.0.0, dopo R14.8).
← Precedente: [`plan-phase00PacSolverBudget.prompt.md`](plan-phase00PacSolverBudget.prompt.md).
**Lane:** copia di prod `6161` + `/tmp/librefolio-r2-d-prodcopy`, ricavata dalla snapshot `/tmp/librefolio-r2-prod-snapshot` (server e review) · suite `6151` + `/tmp/librefolio-r2-d` (solo `dev.py test`).

Ordine imposto dal developer: **(A) i documenti prima**, poi **la UI torna nella build**, poi **STOP**
per la review di dettaglio di UI e matematica, fatta in questa chat.

---

## 0. Regole operative (valgono per ogni passo)

- Preambolo: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …`
- Mai `dev.py test` sulla copia di prod. Mai le porte 6040/6041/6042/5173. Un solo comando di test
  alla volta nella lane. A ogni `FROZEN`: server spento e `lsof -nP -iTCP:<porta> -sTCP:LISTEN`
  vuoto sia per 6151 sia per 6161.
- Copia di prod: **solo dalla snapshot** `/tmp/librefolio-r2-prod-snapshot`, con la procedura
  del coordinator nella seconda versione, ricevuta il 24/09:
  1. `test -f` sull'`app.db` e controllo che il marcatore sia assente;
  2. `mv` della copia precedente in `.prev-<data>`;
  3. `cp -R`, poi `chmod -R u+w` (la snapshot è in sola lettura);
  4. deve stampare `004_release_1_2_0_schema`.

  La prima procedura leggeva `backend/data/prod` del main checkout ed è **ritirata**, perché
  violava il divieto di leggere il main checkout. Se la snapshot manca (reboot), la chiedo al
  coordinator. Va rinfrescata prima di ogni review.
- Credenziali della copia: utente `alfy`. La password l'ha data il coordinator e **non è
  trascritta qui**, perché questo piano finisce nel repo.
  - Non va mai in log, in un `tee` o in un comando salvato su file.
  - Se il login dà 401:
    1. `LIBREFOLIO_TEST_DATA_DIR=/tmp/librefolio-r2-d-prodcopy … dev.py user --test-db list`, sempre **prima**;
    2. poi `reset` allo stesso valore, solo sulla copia.

    `dev.py user` non ha `--data-dir`, e senza `--test-db` mira al prod del checkout.
- **Nessuna migrazione Alembic.** Lo scope di D non tocca modelli DB: il tool è stateless.
  Se emergesse un bisogno di schema → fermarsi e chiedere al coordinator.
- Il client generato è ignorato da git. Prima di ogni `front check` va lanciato `api sync`
  (in-process, nessuna porta). Ogni conteggio `svelte-check` va riportato **con l'ora di
  generazione del client**. Il pavimento noto è 3 errori, 41 warning, 4 file.
- i18n solo via `dev.py i18n add|update`, sintassi ICU `{x}`, in modo additivo. Nessuna
  cancellazione di chiavi (decisione a, §4 di `09_…`).
- `CHANGELOG.md` non si tocca: le voci si propongono nell'handoff.
- `ToolsHub.svelte` è di D **in questo round** (coordinator, 24/09). Si conserva
  `use:guideAnchor={'tools.hub'}` (`:146`). Il toast per un `renderer_missing` atteso si decide al STOP (R9).
- UI: la test list va al developer. Niente test-author per l'analisi UI. I test backend vanno a
  test-author, suite 6151.
- Mai `git commit/push/merge/rebase`. Il piano si aggiorna dopo **ogni** passo, con data,
  `Note implementazione` e `Fuori pista`.
- Nota storica: i miei piani precedenti citano le lane 6152/6153. Sono superate: vale
  6151/6161, come assegnato.
- Il grafo graphify è assente nel worktree fresco, come atteso. Le pagine wiki sono state lette
  direttamente: `problems/front-check-does-not-check-what-you-think.md` e
  `problems/openapi-zod-discriminator-type-erasure.md`.

---

## 1. Stato reale misurato

### 1.1 Difetti round 5 di competenza D

| # | Difetto | Evidenza | Lettura |
|---|---|---|---|
| D1 | «Interfacce non disponibili: 1» + toast warning | `registry.ts:240-251` array vuoto. `resolve()` → `renderer_missing` (`registry.ts:234`). Toast in `ToolsHub.svelte:88-101` (J). | Stato modellato e vero: la UI v2 non esiste. `pac_allocator` è l'unico tool backend, quindi registrare il renderer elimina l'unica occorrenza. La policy «un `renderer_missing` atteso deve generare warning?» resta a J/coordinator. |
| D2 | Card con la descrizione del prototipo P1 | `tools.pacAllocator.description` a `{en,it,fr,es}.json:3635`. `presentation.ts:28` `metadataText`: vince l'i18n. | Decisione (e) chiusa dal coordinator: tocca a D. |
| D2b | Anche il testo backend è impreciso | `tool_plugins/pac_allocator.py:98` dice «whole-unit purchases». Ma `monetary_amount` è supportato: `normalize.py:553-568`, `constraints.py:167-172`, `planner_report.py:764` (`MonetaryAmountInstruction`). | La descrizione **non** entra nel fingerprint (`tools/schema.py:227`: solo schemi input/output più operazioni), quindi nessun bump di contratto. |
| D3 | Contratto PAC «disatteso» (§9.5) | `16_toolPlatform/handoff-pac-D.md` (304 righe) promette `1.0.0`, `analyze`, `PacAnalyzeInput`, timeout 5 s, `compute(parameters, context)`, `uiContractVersion: 1`, lane 6153, selector `pac-analyze`/`pac-tool`. | La realtà: `2.0.0`, `plan`, `ToolService` con `compute(tool_code, parameters, context)`. Timeout: coda 5000, engine 30000, job 45000, soft 44000, cleanup 5000, request 59000, client 65000; riserva post-engine 2000. Registrazione: `defineToolRenderer(code, version, {componentKey, uiVersion, load})` (`registry.ts:25-29,126`). Selector reali: `services pac-planner-{core,evaluator,oracle,policies,solver,proof,wire-numbers,report,service}`, `schemas pac-planner`, `api tools`, `front-utility core-unit`/`component-unit`. |
| D3b | Stessi documenti D ancora non allineati | UiTarget §20.20 `:2336` «Privacy oscura importi, quantità, costi, **percentuali** e valori grafici». Step 5 §10 `:408-409` idem. Step 5 header `:3`, §12 `:437-439` (lane 6153, fixture sintetica). Step 6 header e selector `:109-120` (`pac-tool`, `pac-planner-capacity`, selector inesistenti). `implementation/README.md` header «READY FOR PLANNING CHECKPOINT», baseline `b0a410b8`. | La decisione (c) del 22/09 dice che percentuali e prezzi **non** sono patrimonio. Le stringhe `1.0.0` negli ASCII (`UiTarget:209,230,277,390,1285,1355,1753,1781`) sono illustrative. |
| D3c | Puntatori nei record del coordinator | `05_…:22`, `06_…:637`, `manifest-integrazione-C.md:233`, `plan-phase00ToolPlatform.prompt.md:16,173` | Sono **solo link** a handoff-pac-D. Correggendo la radice restano validi. Unica parte datata: il diagramma di `plan-phase00ToolPlatform.prompt.md:161-171` (`:162` «PacAnalyzeInput reale», `:168` «componente P1 D») → lo **propongo** al coordinator, non lo edito. |
| D4 | Pagina utente MkDocs | `user/tools/pac-allocator/index.en.md` `:3`, `:14-21`, `:104` «No interface yet»; `:61` «whole units» | Esiste solo EN: nessun debito di traduzione. Quando la UI entra va fatto un ritocco puntuale; la riscrittura completa dopo la review. |

### 1.2 Reperti nuovi, non presenti in 08/09

| # | Reperto | Evidenza | Conseguenza |
|---|---|---|---|
| N1 | **`min_fragmentation` raggiungibile via API** | `schemas/pac_allocator.py:758` accetta la policy. `evaluator.py:1468` ne implementa la cascata. `planner.py:210-224`: fino a 200 000 candidati (`oracle.py:61`) l'oracolo dà un risultato **dimostrato**; oltre, `compiler.py:117-122` solleva `PolicyProgramScopeError` → `worker.py:178` → `execution_failed` non ritentabile. I codici issue sono un `Literal` del wire (`:246`, 80 codici). | Stessa policy: successo sui domini piccoli, errore generico sui grandi. È una decisione per la review (R2), e non blocca la UI, che mostra solo `proportional`. **Deciso il 24/09 (Q-C0-4): esce dal wire, C0b.2.** |
| N2 | **Nessun test API del plugin reale** | `test_tools_api.py`: 0 riferimenti a `pac_allocator`. `test_pac_tool_api.py` è sparito col P1 (resta solo un `.pyc`). | Serve un test API di `/api/v1/tools/compute` con `pac_allocator`/`plan`, via test-author. |
| N3 | **Nessun test API di `POST /portfolio/allocation-source`** | Esiste solo il test di servizio `test_portfolio_allocation_source.py`. `test_portfolio_api.py:593` copre l'`allocation_source` **P1** di `/portfolio/report`. | Serve un test API: auth, 403 per broker non OWNER, 404 per asset mancante, forma della risposta. |
| N4 | **Due sorgenti di copia** | La v2 è `portfolio_api.py:188-219` → `PortfolioPlannerSourceResponse` (`portfolio.py:1205-1612`), con 0 consumer frontend. `pac-allocator/allocationSource.ts` (P1, su `/portfolio/report`) ha 0 consumer ed è ancora nel runner `core-unit` (`_frontend_utility.py:103`). | La UI v2 usa l'endpoint v2 tramite un client nuovo. Il ritiro del P1 va a fine round, coerente con la decisione (a). |
| N5 | **80 codici issue, 0 messaggi i18n** | `issues.py:137` `message_key = code`. Nessuno degli 80 codici è coperto in `tools.allocation.issues` (38 chiavi P1). | Servono 80 × 4 = 320 voci, più il fallback per un codice sconosciuto. È il blocco i18n più grosso. **Dopo C0b: 82 chiavi (79 del planner + 3 della sola copia), vedi C8.** |
| N6 | **Tensione sulla privacy delle quantità** | `maskable.ts:29-31`: la classe «strutturale» (quantità, date, conteggi) non passa dal formatter valuta (D5). La decisione (c) però parla di «quantità possedute» come patrimonio. | Nel PAC si ha `quantità × prezzo pubblico = importo mascherato`: mostrare la quantità vanifica la maschera. Default prudente: mascherare con `maskable(…, 'personal')` di J (non una maschera mia), poi confermare in review (R7). |
| N7 | **Gate privacy di J non registrato nel runner** | `moneyRenderSites.test.ts` e `maskable.test.ts`: 0 occorrenze in `scripts/test_runner/*.py`. | Non gira via `dev.py test`. Lo segnalo al coordinator (è perimetro J). Il gate copre comunque tutto `src/` (`:64`) e ammette `maskable(` come chiamata sicura (`:81`). |
| N8 | **Stati producibili in 2.0.0** | Si producono solo: `optimal_proven` via oracolo, `not_proven` via SCIP, `infeasibility_proven` via oracolo. Deployment sempre omesso (`planner.py:108-112`), `buffer` sempre zero (`planner_report.py:569`). `describe_conclusion` è usato solo nei test (`proof.py:265`). `age_days` esiste solo in input (`schemas:427-430`) e il report non lo riporta. | La UI deve rendere **tutti** gli stati del codec da fixture; il runbook può raggiungere solo quelli producibili. |
| N9 | **Test da invertire** | `registry.test.ts:135-146` asserisce `renderer_missing` per `pac_allocator`. | Va portato a `ready`. `renderer_missing` resta coperto via `createToolRendererRegistry([])`. |
| N10–N23 | **Reperti del confronto col wire** (Passo C0) | Evidenza `file:riga` in [`…-C0UiDelta` §9](plan-phase00PacRound5-C0UiDelta.prompt.md) | N10 tariffa monovaluta = valuta del prezzo · N11 tipo di tetto/minimo errato → `reference_not_found` · N12 `asset_class` maiuscolo dalla copia → `invalid_parameters` · N13 priorità bassa = preferita · N14 nessuna modalità «solo nativa» · N15 FX senza freschezza sul wire · N16 tetto obbligatorio · N17 `ToolErrorCode` tradotti solo in `risk.errors.*` · N18 copia con ≥ 1 Broker `OWNER`, `minor_unit` solo da copia · N19 selezionata = raggiungibile + intrappolata · N20 chiave FX malformata → `invalid_parameters` · N21 valuta del passo monetario ignorata · N22 esposizioni > 100% non rifiutate (non provato) · N23 `fx_cost`/`buffer`/`explanation_keys` costanti. |

### 1.3 Riuso disponibile, in sola lettura

- Input esatti: `ExactQuantityInput.svelte`, `ExactDecimalInput.svelte`.
- Formatter: `formatDecimalForDisplay` (`formatDecimal.ts:37`), `formatPercent` (`formatPercent.ts:63`),
  `formatCurrencyAmountPlain/Html` (`currencyFormat.ts:33,55`; prendono `amount: number`, con
  `min/maxFraction` e `sensitivity`).
- Client della piattaforma: `runTool` (`client.ts:300`).
  `toolContractMap.pac_allocator["2.0.0"]` = fingerprint `e2b70735…`, `componentKey 'pac-allocator'`, `uiVersion '2.0.0'`.
- Grafici: non esiste un bar chart condiviso. `AllocationPieChart` è bersaglio di Risk (R12).
  → grafici PAC-local con ECharts diretto, come fanno gli altri componenti.
- Il request PAC prende la cassa **per broker × valuta** (`PlannerExistingCashInput`, schemi `:579`),
  quindi la copia è 1:1. L'aggregazione per valuta la fa il planner: **zero somme nel frontend**.
- **La UI P1 è intatta nella storia**, a `b82e59ffa^`.
  - **Storia:** cinque commit, dal 10 al 14/09: `1fd395a10` → `8273335ff` → `8504f0528` → `afca689dd` → `d66f8e58e`.
  - **Cosa è stato cancellato in `b82e59ffa`:**
    - 16 file UI, ≈ 3 665 righe;
    - 2 file Vitest, ≈ 1 982 righe;
    - 2 spec E2E, ≈ 1 083 righe.
  - **Non è andata persa nel merge.** L'ho tolta io, su decisione del developer del 21/09 («togli p1 e poi lavora su v2»).
  - **Perché non basta sistemare gli import:** è tipizzata sul contratto `1.0.0`/`analyze`,
    `ToolInput<'pac_allocator','1.0.0'>` (`editorTypes.ts:4`, a `b82e59ffa^`), che non esiste più.
    Il registro rifiuta un renderer senza contratto corrispondente (`registry.ts:162`).
  - **Cosa si riusa lo decide la UiTarget approvata:** §2 `:70-84` e §20.22 `:2426-2440`.
    - *Riusa pattern:*
      - le guardie request/draft/account e il ciclo `runTool`/annulla/`ToolExecutionMetrics` di `PacAllocatorTool`;
      - `importedValue`/`stale` di `draftFactories.ts`;
      - `OwnedAssetGallery` → `AssetPicker`;
      - `AllocationTargetEditor` e le sue celle → `PlannerTargetStep`;
      - `AllocationDiagnostics` → `OutcomeSummary`.
    - *Ridisegna:* `PacMoneySection` → `FundingSourcesStep`.
    - *Sostituisce:*
      - la shell monolitica con una progressiva;
      - `PacAssetEditor` (il `buy_grid` passa al broker);
      - `AllocationFxSection` (FX operativo con spread);
      - `PacResultPanel`, che mostrava importi teorici e non un piano con prova.
  - **Privacy:** nei 10 file PAC controllati nessuno importa `currencyFormat.ts`. Gli importi
    passavano da `formatDecimalForDisplay` (`PacMoneySection.svelte:64`), quindi anche i pezzi
    riusati vanno ricablati sull'adapter privacy.

---

## 2. Decisioni

**Chiuse, da non ridiscutere:**
- l'ordine docs → UI → STOP;
- la descrizione tocca a D;
- privacy: patrimonio sono gli importi (liquidità, importi per ETF, fee, residui, scostamenti in
  valuta); pesi, percentuali, prezzi di mercato e tassi FX sono pubblici;
- nessuna cancellazione di chiavi;
- nessuna `005`;
- `ToolsHub.svelte` passa a D per questo round (coordinator, 24/09), con `guideAnchor` `:146` conservato;
- **risposte di J via coordinator (23-24/09):**
  - D5′: le quantità accanto a un prezzo si mascherano, e le righe del piano PAC rientrano. D usa
    `maskable(…, 'personal')` dietro l'adapter unico; quando J aggiunge `maskableQuantity`, lo scambio
    lo fa il coordinator all'integrazione;
  - N7 lo assorbe J;
  - nessuna variante del formatter per stringhe decimali: `formatCurrencyAmountPlain/Html(Number(s), code)`;
    vuoto o non finito → `—` non mascherato; oltre 15 cifre significative si chiede a J;
  - `sensitivity: 'public'` esiste (`currencyFormat.ts:24`), con `minFraction`/`maxFraction`;
  - ramo `exact_ratio` di un valore personale: `≈` fuori dalla maschera come il segno, cifre `•••` (`≈•••`);
  - `maskable(…, 'public')` solo per tassi e percentuali: il gate salta quelle righe;
  - gate `moneyRenderSites`: le primitive D8 e `maskable(` sono `SAFE_CALL`; se diventa rosso, D scrive la
    voce del registro e J la rivede;
  - J chiede il test di comportamento sulle quantità: T7b;
- toast per `renderer_missing` (`notify.svelte.ts:53-55`): niente toast, conteggio in `detail`. Se
  correggerlo in questo round si decide al STOP (R9), altrimenti va in backlog;
- UiTarget approvata (Review A–D);
- `min_fragmentation` rinviata (TODO_FUTURI `:597-619`);
- copia di prod ricavata solo dalla snapshot condivisa (decisione del developer, riferita dal coordinator il 24/09:
  «snapshot per tutti e sette»);
- gli importi passano solo da `formatCurrencyAmountPlain/Html`, mai dall'helper di Risk;
- il riuso della UI P1 segue la classificazione della UiTarget approvata (§20.22), non il
  ripristino in blocco;
- **Q1 (24/09, developer): UI completa per il PAC 2.0.0 prima dello STOP.**
  - Entrano tutti gli step (manuale e copie), tutti gli stati, le tabelle complete e un grafico
    prima/target/dopo in %, riusando i pezzi P1 recuperabili.
  - Il Sankey e la rifinitura mobile fine si fanno **dopo** la review.
  - Il layout mobile di base (D4, a pila) entra comunque, perché è nel delta ASCII.
- **Domande del delta C0 (developer, 24/09).** Tre giri: `ask_user` dopo il recap, poi la chat, poi
  `ask_user` sul dettaglio di Q-C0-6. Queste decisioni sostituiscono i default provvisori che avevo
  scritto la mattina, quando il developer non era disponibile. Q-C0-1 e Q-C0-2 le ha risolte con una
  strada che non era fra le opzioni proposte. Dettaglio e citazioni: [delta §8.1.1](plan-phase00PacRound5-C0UiDelta.prompt.md).
  - **Q-C0-1 — il quantum lo ricava il backend da babel.** «cambiamo la api semplicemente, tanto le
    valute sono standard e vincolate ad essere quelle di babel». `minor_unit` = `10^-cifre`, con le
    cifre CLDR di `get_currency_precision`. `currency_specs` esce dall'input dei tre planner
    (`_PlannerRequestBase`) e dalla risposta di `allocation-source`. Nessuna API nuova e nessun
    passaggio dalla UI. Chiude la parte quantum di N18: uno scenario tutto manuale non ha più
    bisogno della copia. Era già l'intenzione di Step 1 («l'assembly di dominio risolve il codice
    tramite … Babel CLDR `get_currency_precision`»), ora senza il giro nella request.
  - **Q-C0-2 — nella UI solo percentuali di controllo.** «se si tratta di fare percentuali,
    ovviamente li può fare anche la ui, ma devono essere di controllo/informativi, quelli dei
    risultati stanno nel backend».
    - Ammessi: totale e restante del target; il confronto nella stessa unità «selezionato ≤
      disponibile» su una riga di cassa.
    - Esclusi: le somme di importi (il riepilogo della liquidità conta le fonti, non le somma) e
      ogni numero del risultato, che arriva dal backend.
    - Questa lettura, prudente, la confermo al STOP (R1).
  - **Q-C0-3 — si mostra l'età, senza conferme.** «vale giusto la pena mostrare se è del giorno
    precedente di quanti giorni è, ma in ogni caso la scelta finale è dell'utente».
    - L'età dei prezzi copiati viene da `days_before_requested` (`schemas/portfolio.py`). Per un
      prezzo manuale la UI conta i giorni fra la data scritta e `as_of`.
    - I valori restano modificabili e non c'è nessun pulsante «Conferma».
    - All'invio un prezzo con età > 0 viaggia come `stale{age_days, accepted: true}`, uno del giorno
      come `fresh`.
    - L'età di un tasso FX resta solo in UI (N15).
  - **Q-C0-4 — `min_fragmentation` esce dal wire.** «semplicemente non mettiamola, la ui in questo
    deve essere dinamica». `policy` diventa `Literal["proportional"]` nella request PAC e nel suo
    `scenario_basis`. Il Passo 8 costruisce le card dalle opzioni del contratto generato. Il ramo
    interno resta spento (TODO_FUTURI). **Chiude R2 (N1).**
  - **Q-C0-5 — tetto obbligatorio, default alto.** «per ora se ti devi predisporre metti un numero
    alto e un todo che dice che andrà ridotto quando si saranno fatte le simulazioni sui tempi di
    esecuzione».
    - Il wire resta com'è (N16).
    - La UI precompila `1000000000` nell'unità della modalità (quote o valuta del prezzo). Il valore
      è visibile e modificabile.
    - Il TODO sta nel codice (`planner/defaults.ts`), e il numero entra nella lista di Step 3 punto 13.
    - Un fatto utile per la misura: il tetto non allarga il dominio. Il bound di ogni ordine è il
      minimo fra tetto e risorse (`evaluator.py:784-845`), e `compiler.py:146` lo passa a SCIP come
      `ub`. Un tetto sopra le risorse non cambia quindi né l'oracolo né il solver.
  - **Q-C0-6 — «Copia distribuzione corrente» si fa.** «è un ottima idea facciamola». Fonte scelta:
    «Motore del portafoglio (numeri della pagina Allocazione)». Nuova sezione `current_distribution`
    di `POST /portfolio/allocation-source` (Passo C0b.4).
  - **Q-C0-7 — issue nuovo di tipo `invalid`.** «il codice invalid è la scelta giusta».
    `allocation.exposure_total_exceeds_one` nel normalizer (Passo C0b.3).
  - **Q-C0-F — delta approvato.** «ho letto il piano e guardato le ascii mi paiono coerenti, quello
    che avevamo pianificato in origine, hai il mio via libera, ovviamente poi faremo la review».
- **Domande a J:** chiuse (vedi sopra).
- **D-X1 (24/09, developer) — in produzione gira solo SCIP, e il suo esito fa fede.**
  - Parole sue: «scip come libreria dovrebbe già ritornare gli ottimi rispetto a vincoli e
    funzione obiettivo, avere un oracolo può essere utile in fase di test, su set piccoli, per
    testare funzione obiettivo e vincoli, ma in produzione oracolo non deve MAI essere usato e si
    assume che la matematica di scip sia corretta» … «in prod deve girare solo l'ottimizzatore con
    l'assunzione che l'output che dà sarà corretto o andrà in timeout».
  - Conseguenze:
    - SCIP `optimal` su tutti gli stage vale «ottimo»;
    - SCIP `infeasible` sul primo stage vale «impossibile»;
    - un limite vale «tempo scaduto», con il miglior piano trovato o senza piano;
    - l'enumeratore esaustivo esce dal codice di produzione e resta solo nei test (gate di accordo
      su casi piccoli).
  - Sostituisce la regola «status floating mai promosso, prova solo da oracolo», registrata come
    scelta del developer in `09_feedbackJobs/05_pac_allocation_tool.md:242-244` e in
    `06_piano_sprint.md:742-748`. Esecuzione: Passo F.

**Aperte:**
- **R7 — la classificazione privacy campo per campo**, quantità incluse. Va in review; nel
  frattempo vale il default prudente.
- **QX1-a — il tetto massimo delle commissioni nel modello SCIP. ✅ Deciso il 24/09 dal developer:
  «sì, modelliamolo subito».** Si modella in modo esatto dentro il Passo F, con una binaria per
  ogni route BUY che ha un tetto.
  - Con D-X1, «ottimo di SCIP» vuol dire ottimo solo se il modello compilato coincide con le regole
    esatte. Oggi il modello non conosce `maximum_fee`: `constraints.py:42-55` e `:613-642` lo
    dichiarano un limite noto dal passo 3; `test_pac_planner_policies.py:543` lo blocca come
    regressione voluta.
  - Esempio: 50 050 €, ETF a 100 €, commissione 0,19% con massimo 18 €.
    - La regola esatta permette 500 quote: 50 000 + 18 = 50 018 €.
    - SCIP calcola 95 € di commissione e si ferma a 499.
    - Con un minimo d'ordine obbligatorio, lo stesso scarto può produrre un falso «impossibile».
- **QX1-b — tolleranza di SCIP e piano che il controllo esatto non accetta.** ✅ **Deciso il 25/09
  dal developer** (sotto la domanda, la risposta e la regola). La proposta del 24/09, un messaggio
  esplicito «piano di SCIP scartato dal controllo esatto», è **respinta**.
  - SCIP giudica i vincoli lineari con una tolleranza **relativa**: `feastol` 1e-6 per il valore
    in gioco. Verificato nel sorgente di SCIP (`cons_linear.c:7236-7237`, `set.c:7300-7322`,
    `misc.c:11162-11176`); installato: SCIP 10.0 / PySCIPOpt 6.2.1.
  - Su una cassa da 20 000 € può accettare uno sforamento fino a 2 centesimi.
  - Il replay Decimal lo scarta, e oggi lo scarto diventa `ready_no_incumbent`, «nessun piano»
    (`planner.py:152-160`).
  - Il commento di `solver.py:91` chiama «absolute» quella tolleranza: da correggere.
  - **25/09, domanda del developer:** «se i vincoli sul numero di decimali della valuta sono messi
    correttamente, e come abbiamo detto li prendi da babel, non capisco quando mai potrebbe
    realizzarsi un simile scenario».
    - **Risposta:** il quantum di babel c'è, e ogni importo del modello è un numero intero di
      centesimi. Lo scarto nasce da altre due strade.
      - **Arrotondamento a metà centesimo.** Acquisto e commissione si registrano HALF_UP; a un
        pareggio esatto la coppia non stretta di `_posted_units_term` ammette anche il centesimo
        sotto. È voluto per i debiti (`constraints.py:397-401`), che il codice considera «permissive».
      - **Tolleranza relativa di SCIP.** Vale sui grandi importi; nelle prove non è mai successo.
    - **🔴 X3, riprodotto sul modello compilato** (`files/x1-probes/tie_probe.py`, sola lettura,
      nessun DB o server):
      - caso: 3 quote a 33,335 € su una cassa di 100,00 €;
      - SCIP chiude tutti gli stage con 3 quote: conta 100,00 € al posto dei 100,01 € della regola
        esatta (3 × 33,335 = 100,005);
      - il replay lo scarta (`feasible=False`), mentre il piano giusto è 2 quote (66,67 €,
        `feasible=True`);
      - controlli: a 33,336 € SCIP sceglie 2 quote; con una cassa di 100,01 € sceglie 3 quote, e il
        replay le accetta.
    - Oggi su questo dominio decide l'oracolo, quindi il difetto non si vede. Con D-X1 diventa
      «nessun piano» anche su 100 €.
    - Il modello sui debiti resta comunque un **rilassamento** delle regole esatte: un piano di SCIP
      che passa il replay è davvero ottimo, e uno scartato vuol dire solo che non c'è una risposta.
    - Cura proposta (X3):
      - per acquisti e commissioni, arrotondare in su i pareggi esatti come fa la regola, con il
        margine esatto del reticolo dei prezzi;
      - il margine è la metà della distanza minima dal pareggio: `quantum/(2b)`, con
        `coefficiente/quantum = a/b`;
      - il margine si applica solo dove sta ben sopra la tolleranza di SCIP; altrove il modello resta
        permissivo e decide il replay.
    - **❌ X3 respinta dal developer (25/09)**, scelta «No, niente X3: nell'esempio 3 quote e la nota
      "servono 1 unità minima in più"». Il modello resta permissivo ai pareggi
      (`constraints.py:397-401`), e SCIP può usare il centesimo del pareggio quando gli conviene.
  - **La decisione del developer (25/09), parole sue:**
    - «non credo che qui ci sia da fare messaggi espliciti o altro, serve un altra strategia,
      potremmo anche fare che semplicemente la sol viene arrotondata all'half_up e se alla fine i
      soldi richiesti superano il budget si specifica all'utente che servono altri soldi per via
      degli arrotondamenti ai centesimi, oltretutto mi aspetto che per 1 che supera di pochissimo,
      c'è un altro che sta sotto di intere unità, quindi alla fine le cose si compensano»;
    - «riguardo la soglia dei centesimi, potresti trovarti ad avere 1 centesimo extra per ogni
      asset, quindi la soglia è N centesimi, e nota bene, per centesimi, intendo l'unità minima in
      quella valuta».
  - **La regola che ne segue** (Passo F, F2c):
    - Il replay Decimal con HALF_UP resta la contabilità del piano pubblicato: i numeri mostrati
      sono i suoi.
    - Il piano esce anche se, dopo gli arrotondamenti, costa più della cassa.
      - Condizione: l'unica violazione è un saldo finale negativo in una o più casse (broker ×
        valuta).
      - Soglia: il deficit di ogni cassa non supera `N × unità minima` della sua valuta, con l'unità
        minima presa da babel (1 yen per JPY, 0,001 per BHD).
      - `N` conta gli importi arrotondati registrati in quella cassa: 1 unità minima per ciascuno.
        Per un piano di soli acquisti vuol dire l'acquisto di ogni ordine attivo, più la sua
        commissione quando c'è: con una commissione percentuale sono 2 per asset (detto al
        developer il 25/09).
      - Si contano anche i crediti FX arrotondati che entrano nella cassa: stessa regola, 1 per
        importo.
    - Per ogni cassa in deficit il risultato dice quanto aggiungere, per esempio «per eseguire il
      piano servono 0,01 € in più su Broker X (EUR), per gli arrotondamenti all'unità minima».
      Niente messaggio di scarto, niente «nessun piano».
    - Oltre la soglia, o con qualunque altra violazione delle regole esatte, non si tratta di un
      arrotondamento: è un errore del modello, e **resta un errore**. Non diventa «nessun piano».
      Lo stato esatto si sceglie in F2c fra i percorsi d'errore esistenti; uno stato nuovo sul wire
      solo se serve, e in quel caso lo si dichiara.
    - Con D-X1, «ottimo» vuol dire ottimo per il modello compilato. Il modello resta permissivo solo
      ai pareggi esatti, e quello che ne esce è coperto dalla nota.
    - L'esempio `3 × 33,335` con una cassa di 100,00 € diventa: 3 quote, e la nota «servono 0,01 € in
      più». È anche il test rosso naturale di F2c.
    - Rischio residuo, dichiarato: uno sforamento dovuto alla tolleranza relativa di SCIP oltre la
      soglia darebbe un errore su un input legittimo. Nelle prove (`files/x1-probes/`) non è mai
      successo.

---

## 3. Passi

### Passo 0 — Piano nel journal ✅ 2026-09-24
Copiare questo piano nella destinazione. Aggiungere i link reciproci con `SolverBudget` e una riga nel
`README.md` di `implementation/`. *Gate:* `git diff --check`.

> **Note implementazione** (2026-09-24): HEAD verificato `f1047f766`, albero pulito prima di
> iniziare. Piano di sessione copiato qui con lo stato passato ad APPROVATO. Link avanti aggiunto
> in testa a `plan-phase00PacSolverBudget.prompt.md` (`> **Successor**`), link indietro qui.
> Nel `README.md` di `implementation/` c'è una nuova tabella «Piani successivi
> all'integrazione» con quattro righe: Remediation `c7e25da93`, P1ResidueRemoval
> `b82e59ffa`…`154182295`, SolverBudget `a7cd01b07`/`3e513fea2`, Round5. Gli SHA sono stati
> verificati con `git log`. `git diff --check` è pulito sui tracciati; sul file nuovo è stato
> controllato con `git diff --no-index --check`, che non segnala errori di spazi.
>
> **⚠️ Fuori pista**: nessuno. L'header del README («READY FOR PLANNING CHECKPOINT», baseline
> `b0a410b8…`) è rimasto com'era, perché è nel perimetro di A2.

### Passo A — Allineamento documenti (PRIMA; zero codice prodotto) ✅ 2026-09-24

- **A1 `handoff-pac-D.md`** (assegnato dal coordinator per §9.5):
  - banner datato «contratto superato: vale §0»;
  - nuova **§0 «Contratto effettivo al `f1047f766`»**, con i valori reali di D3: simboli, versioni,
    operazione, firma di `compute`, timeout, registrazione del renderer, codegen, selector, lane, DoD;
  - marcatore `⚠️ superato → §0` su §1–§7. Il testo storico **non si cancella**.
- **A2 documenti D in `13_pacAllocator/`:**
  - UiTarget: erratum in testa («le versioni negli ASCII sono illustrative; il wire vivo è 2.0.0;
    delta 2.0.0 → piano Round5») e riga §20.20 riallineata alla decisione (c), con data;
  - Step 5: header, §10 privacy, §12 runbook (la copia di prod sostituisce 6153 e la fixture sintetica);
  - Step 6: header e §selector (nomi reali; `pac-tool` e `pac-planner-capacity` non esistono);
  - `implementation/README.md`: header e tabella, aggiungendo Remediation, P1ResidueRemoval,
    SolverBudget e Round5.
  - I file `drafts/*` restano intatti, perché storici.
- **A3 record del coordinator:** nessuna modifica; propongo al coordinator il testo per il
  diagramma di `plan-phase00ToolPlatform.prompt.md:161-171`.
  - Le righe datate sono due: `:162` «PacAnalyzeInput reale» e `:168` «componente P1 D».
    Proposta: `PacPlannerRequest reale (2.0.0, plan)` … `host C + renderer PAC v2 D (Round 5)`,
    con una nota datata sulla rimozione del P1 in `b82e59ffa`.
  - `:173` («Nessuna registry vuota … può chiudere questo passo») resta vera: quel passo di C si
    chiude soltanto quando D registra il renderer v2.

*Gate:* un grep su «PacAnalyzeInput|analyze_initial_state|uiContractVersion|6153|pac-analyze|pac-tool»
nei doc live di D restituisce solo occorrenze dentro blocchi marcati «superato/storico». Poi `git diff --check`.

> ✅ **2026-09-24 — Note implementazione.**
>
> **A1.** `handoff-pac-D.md` ha:
> - un banner datato;
> - la nuova **§0**, con sei sottosezioni: backend, codegen, renderer, selector, lane, DoD.
>   Ogni valore è letto dal codice al `f1047f766` con `file:riga`, e le righe citate sono
>   state ricontrollate una per una (sei intervalli corretti prima della consegna);
> - un marcatore `⚠️ Superato → §0.x` in testa a ciascuna delle §1–§7. Il testo storico è intatto.
>
> **A2.**
> - UiTarget: erratum in testa, che rimanda alle sezioni e non alle righe (le righe si
>   sposterebbero), e §20.20 riscritta sulla decisione (c), con il testo del 16/09 conservato
>   in citazione.
> - Step 5: nota di stato nell'header; §10 privacy riallineata, con il testo originale
>   citato; §12 marcata superata a favore della copia di prod 6161.
> - Step 6: nota di stato nell'header, che copre 6153 in §12/§14/§15, e nota selector in §6.
> - README: nota di stato sotto l'header storico.
>
> **A3.** Il testo per il diagramma di `plan-phase00ToolPlatform.prompt.md:161-171` è già
> stato proposto al coordinator nel messaggio di piano pronto. Il file non è stato toccato.
>
> **Gate.**
> - Il grep sui doc di D (`13_pacAllocator/**` esclusi `drafts/`, `handoff-pac-D.md`,
>   `mkdocs_src/docs`) trova 107 occorrenze. Classificate tutte:
>   - dentro note datate `>`: evidenza storica;
>   - sotto un banner di file o un marcatore di sezione;
>   - negazioni esplicite nella §0 dell'handoff;
>   - descrizione del problema in questo piano;
>   - registro della rimozione in `P1ResidueRemoval`.
>   Log in `/tmp/libreFolio_d_r5_gateA_grep2.log`.
> - Link relativi dei 13 file toccati: 0 rotti (script `/tmp/libreFolio_d_r5_linkcheck.py`).
> - `git diff --check` pulito; sul file nuovo, `git diff --no-index --check` non stampa errori.
>
> **⚠️ Fuori pista.**
> 1. Il grep ha trovato righe non citate che il piano non prevedeva: header e comandi
>    canonici con `6153`, liste selector con `pac-tool`. Stanno nel master implementativo,
>    negli Step 1–4 e nello Step 1 Round 1. Ho aggiunto a ciascuno **lo stesso banner datato**
>    (6 file), con uno script (`/tmp/libreFolio_d_r5_banner.py`) e non a mano. Il banner non
>    afferma nulla sullo stato di avanzamento, perché quello non è stato rimisurato: dice solo
>    che lane, selector e simboli sono superati e dove si trova lo stato corrente. Gli
>    `**Stato:** IN PROGRESS` di quegli header restano come sono.
> 2. Ho lanciato `api sync` subito, invece che nel Passo B, per misurare il fingerprint della
>    §0 su un client fresco:
>    - il client del worktree era del 2026-09-22 12:33, rigenerato il 2026-09-24 alle 09:58;
>    - fingerprint `e2b70735…` invariato, `generation 4e906f9e…`;
>    - `git status` senza file generati, perché sono ignorati.
>    Log: `/tmp/libreFolio_d_r5_api_sync_1.log`.

### Passo B — Descrizione della card ✅ 2026-09-24

- **B1:** `dev.py i18n update "tools.pacAllocator.description"` nelle 4 lingue, con questa proposta
  (da approvare insieme al piano):
  - EN: *Plan the purchases that bring a new investment as close as possible to its target allocation, in whole units or amounts, without placing orders.*
  - IT: *Pianifica gli acquisti che portano un nuovo investimento il più vicino possibile all'allocazione obiettivo, in quote intere o importi, senza inviare ordini.*
  - FR: *Planifie les achats qui rapprochent au mieux un nouvel investissement de son allocation cible, en parts entières ou en montants, sans passer d'ordres.*
  - ES: *Planifica las compras que acercan al máximo una nueva inversión a su asignación objetivo, en participaciones enteras o importes, sin enviar órdenes.*
- **B2:** `pac_allocator.py:98` prende il testo EN.
- *Gate:*
  - dopo `api sync`, il fingerprint in `tool-contract-map.generated.ts` resta `e2b70735…`
    (prova che il contratto non è cambiato);
  - `i18n audit` pulito;
  - `services tools-registry` verde in 6151.

> ✅ **2026-09-24 — Note implementazione.**
>
> **B1.** `dev.py i18n update "tools.pacAllocator.description" --en … --it … --fr … --es …`
> (script `/tmp/libreFolio_d_r5_i18n_desc.sh`). Il diff è di **una riga per locale** (4 file,
> +4/−4), senza riordini né riformattazioni. Nessuna chiave cancellata.
>
> **B2.** Il fallback EN a `backend/app/services/tool_plugins/pac_allocator.py:98` è sullo
> stesso testo; `ruff check` e `black --check` sono puliti. Il testo «in quote intere o
> importi» è verificato sul contratto: le capability broker sono `whole_quantity` e
> `monetary_amount` (`schemas/pac_allocator.py:519-535`).
>
> **Gate.**
> - `api sync` dopo la modifica (client rigenerato il 2026-09-24 alle 10:07): fingerprint
>   `e2b70735f589…` **invariato**, contract generation `4e906f9e…` invariata. È la prova che
>   la descrizione non entra nel contratto (`schema_fingerprint` hasha solo gli schemi e le
>   operazioni, `backend/app/services/tools/schema.py:227-229`).
> - `i18n audit`: 3403 chiavi, 3403 complete, 0 incomplete, 0 chiavi backend mancanti.
>   `tools.pacAllocator.name` e `.description` **non** sono tra le inutilizzate; le 422
>   inutilizzate sono le note (168 `tools.pacAllocator.*` del P1), invariate.
> - `services tools-registry` in 6151 + `/tmp/librefolio-r2-d`: **92 passed** in 0,98 s.
>   Dopo il run la porta 6151 è libera.
> - Log in `/tmp/libreFolio_d_r5_{api_sync_2,i18n_audit_B,B_tools_registry}.log`.
>
> **⚠️ Fuori pista.** Il runner ha scritto uno snapshot del DB di test in
> `.testLog/00_archive/test-db_20260924_100736.tar.xz`, dentro il worktree ma ignorato da
> git (`.gitignore:119`). Da non stageare. Restano altrove due testi che descrivono il tool,
> che **non** ho toccato. Diventano falsi solo quando la UI torna nella build (Passo C), quindi
> si correggono dopo:
> - `CHANGELOG.md:18` («whole-unit purchase plans», «Its interactive interface is not ready
>   yet»): la nuova voce si propone nell'handoff;
> - la guida utente: `mkdocs_src/docs/user/tools/index.en.md:49` («This is the PAC
>   allocator's current state») e `user/tools/pac-allocator/index.en.md:3,14-21,33-37`
>   («No interface yet»). Vanno a docs-writer nel passo `r5-user-doc-punctual`.
>   → ✅ 2026-10-05: fatto nel passo S11 di
>   [plan-phase00PacContractCompaction.prompt.md](plan-phase00PacContractCompaction.prompt.md).

### Passo C — UI PAC v2.0.0 nella build ✅ 2026-09-24 (verificato sulla copia di prod, vedi Passo E)

**Base di partenza: la UI P1 nella storia, non il foglio bianco.** Ogni componente che la
UiTarget §20.22 classifica «riusa» riparte da `git show b82e59ffa^:<path>`. I tipi vengono
riscritti sul contratto 2.0.0 e gli importi passano dall'adapter privacy (C7). Nessun ripristino
in blocco: un file P1 torna solo se la UiTarget lo classifica riusabile. Tutto ciò che la v2 ha e
il P1 non aveva è nuovo:
- capability e fee del broker;
- route di funding e d'ordine;
- 7 stati del risultato;
- prova;
- piano funding → FX → ordini;
- esposizioni;
- mapping degli issue per `path`.

- **C0 — Delta ASCII → approvazione del developer (gate), prima di qualsiasi vista.** È un
  documento di delta rispetto alla UiTarget approvata. Contenuto:
  - B14 con la sola `proportional`: nascosta o con nota, da scegliere;
  - C1 senza la tab «variante margine»;
  - niente C3/C15/D6, perché il backend non ha variante né confronto;
  - deployment «non calcolato in 2.0.0»;
  - C14 con i proof kind reali;
  - le versioni 2.0.0;
  - le varianti privacy on/off, desktop e mobile, per i casi manuale, copie, vincoli, risultati,
    invalid, infeasible, busy e stale.

  Anteprima:
  ```text
  +--------------------------------------------------------------------------------+
  | <- Strumenti                                                         [Docs]    |
  | Allocatore PAC · Piano calcolato                                               |
  | Snapshot 23/09/2026 14:35 · Valuta di riferimento EUR · Backend/API 2.0.0      |
  +--------------------------------------------------------------------------------+
  | [v] Piano disponibile  [Ottimo dimostrato · oracolo esaustivo]  [Completato]   |
  | L2 fixed ••• EUR² · U ••• EUR · 0 vincoli violati · nessun issue bloccante     |
  | [ Modifica configurazione ]                            [ Calcola nuovo piano ] |
  +--------------------------------------------------------------------------------+
  | ORDINI                                                    privacy: ON          |
  | Asset   Broker    Quantità  Prezzo        Importo     Fee      Target  Dopo    |
  | VWCE    Directa   •••       110,52 € EUR  ••• € EUR   ••• €    60 %    60,1 %  |
  | AGGH    Directa   •••       5,43 € EUR    ••• € EUR   ••• €    40 %    39,9 %  |
  +--------------------------------------------------------------------------------+
  | [Fattibile · non dimostrato ottimo]  ← badge per not_proven: mai «ottimo»      |
  +--------------------------------------------------------------------------------+

  mobile (D4)                      +------------------------------+
                                   | Allocatore PAC · Piano       |
                                   | [v] Ottimo dimostrato        |
                                   | U ••• EUR · 0 vincoli        |
                                   |------------------------------|
                                   | VWCE · Directa               |
                                   |  Q ••• · 110,52 € · 60,1 %   |
                                   |  Importo ••• € · Fee ••• €   |
                                   +------------------------------+
  ```

  > **28/09 (D-X1, commit 4):** l'anteprima resta com'era stata approvata. Nella UI la fonte della
  > prova sta nel pannello della prova (C14), e oggi è «stato del solver», non «oracolo esaustivo».

  > ✅ **2026-09-24 — C0 approvato dal developer** (Q-C0-F: «hai il mio via libera, ovviamente poi
  > faremo la review»). Le decisioni Q-C0-1…7 sono in §2 e nel delta §8.1.1; il delta è stato
  > riallineato a quelle decisioni (registro delle modifiche in testa al delta).
  > [`plan-phase00PacRound5-C0UiDelta.prompt.md`](plan-phase00PacRound5-C0UiDelta.prompt.md) sostituisce
  > l'anteprima qui sopra (circa 1.390 righe, 49 blocchi ASCII: 29 desktop fra wizard, dialogo di copia
  > e risultato, varianti privacy comprese, 12 di stato, 8 mobile a 34 colonne). Contiene: fatti del
  > wire W1–W23 con `file:riga`; delta per voce della UiTarget (A/B/C/D); scenario testimone verificato
  > con frazioni esatte (non un golden del solver); matrice degli stati; privacy; domande Q-C0-1…7 e
  > decisioni; reperti N10–N23; delta della test list.
  >
  > **Note implementazione**: gli ASCII sono generati da script in `/tmp` (fuori dal repo) che
  > controllano la larghezza di ogni riga: desktop 110 colonne, mobile 34. Tabelle markdown
  > verificate per numero di colonne; `git diff --no-index --check` pulito. Prima del riallineamento
  > il generatore riproduceva il file byte per byte (`diff -q` vuoto); ne tengo una copia nella
  > memoria di sessione, perché `/tmp` si svuota al riavvio.
  >
  > **⚠️ Fuori pista**:
  > - la mattina del 24/09 il developer non era disponibile (alla Q-C0-1: «non disponibile, lavora in
  >   autonomia») e avevo scritto dei default provvisori; il pomeriggio ha risposto, e le sue decisioni
  >   li hanno sostituiti tutti;
  > - un primo tentativo di scrivere il documento in un colpo solo è fallito per il limite di
  >   scrittura; si è passati a parti separate più generatore;
  > - il controllo di larghezza ha trovato righe sforanti nei blocchi del wizard, poi accorciate;
  > - l'esposizione geografica di EMER è stata riallineata fra editor e risultato (Asia 100%);
  > - dopo le risposte di J (24/09) il ramo `≈` dei valori personali è passato da «sparisce con le
  >   cifre» a `≈•••`, e tetti e minimi delle route sono diventati mascherati per default (J: mai
  >   `public` per ciò che deriva da quanto l'utente possiede);
  > - avviso del coordinator su `tee | head` (log troncato in silenzio): la sola conclusione di
  >   assenza che ne dipendeva, N5, è stata ricontata sul file completo: 80 codici, 0 coperti,
  >   38 chiavi `tools.allocation.issues`. Confermata.
  >
  > ✅ **2026-09-24 (pomeriggio) — Documenti allineati alle decisioni, prima del codice.**
  >
  > **Note implementazione**:
  > - Delta C0: il generatore è stato corretto da `/tmp/libreFolio_d_r5_c0_patch.py`, che applica 74
  >   sostituzioni più la §8.1.1 intera e si ferma prima di scrivere se una sola non trova esattamente
  >   un'occorrenza. Ricostruzione: `blocks=50 used=49 unused=['r13_on'] lines=1394`, nessuno sforo.
  >   Cambiano i riepiloghi della liquidità (conteggi, Q-C0-2), il conto manuale (niente quantum,
  >   Q-C0-1), prezzi e FX (età, niente conferma, Q-C0-3), tetto (Q-C0-5), strategia (Q-C0-4), editor
  >   delle esposizioni (Q-C0-7). Nuovo il dialogo «Copia distribuzione corrente» (`s6_copy`, Q-C0-6).
  >   In testa al delta c'è il registro delle modifiche; §8.1.1 è la tabella delle decisioni con le
  >   citazioni; la tabella §8.1 resta com'era quando le domande sono state poste.
  > - Controllo residui sul file ricostruito: `Q-C0-n` compare solo come riferimento a una decisione;
  >   `` `?` `` solo nella legenda; «stale» solo per il risultato non aggiornato (D15, un altro
  >   concetto), nei nomi del wire e nella tabella delle domande.
  > - Note datate negli altri documenti vivi:
  >   - Step 1 (`currency_specs` superato da Q-C0-1);
  >   - Step 3 (punto 6 per Q-C0-4; punto 13: il tetto `1000000000` è il terzo numero da rimisurare);
  >   - Step 5, master implementativo, Policies §7, TargetDesign §3.2, Remediation Fase 3 e
  >     domanda 4 (Q-C0-4);
  >   - UiTarget: voce 4 dell'erratum e riga «Round 5 · delta C0» nel review log §22.
  > - Il generatore aggiornato è copiato anche nella memoria di sessione.
  >
  > **⚠️ Fuori pista**:
  > - la prima nota nella UiTarget era un blocco di 10 righe nell'erratum in testa. Avrebbe spostato
  >   ogni citazione `UiTarget:NNN` del delta (B11 `:1154` → `:1164`, B13 `:1199` → `:1209`…) e
  >   reso false le evidenze. L'ho tolto; ora la nota sta nel §22 in fondo, più una riga al posto di
  >   una riga vuota, e le citazioni tornano a valere (B11 `:1154`, B13 `:1199`, verificato).
  >   Regola da qui in poi: in un documento citato per riga le note si aggiungono in fondo;
  > - controllando le altre citazioni per riga, due in `plan-phase00PacSolverBudget.prompt.md` erano
  >   già scadute prima di oggi: i banner del Passo A avevano spostato Step 3 `:313` → `:324` e Step 6
  >   `:279` → `:305`. Con la nota del punto 6, Step 3 è ora a `:328`. Ho aggiornato i due localizzatori
  >   (testo citato identico); `Remediation:105` era ancora valido;
  > - `TODO_FUTURI.md:597-623` («`min_fragmentation` differita», decisione del 21/09) non riporta
  >   ancora Q-C0-4. Non l'ho toccato: è un file globale, lo chiedo al coordinator;
  > - `review/PAC_ALLOCATOR_REVIEW_DOSSIER.md` e le `drafts/` non li ho toccati: sono fotografie
  >   datate, non documenti vivi.

- **C0b — Contratto backend, prima della UI.** Ordine: C0b.1 → C0b.2 → C0b.3 → C0b.4, uno per
  commit proposto. La versione del tool resta `2.0.0`, perché non è mai stata rilasciata; cambia il
  fingerprint del contratto. Lo stesso vale per `_PLANNER_SOURCE_REVISION` `2.0.0` della copia.
  - **C0b.1 — Q-C0-1, quantum da babel.**
    - Request (`schemas/pac_allocator.py`): `currency_specs` esce da `_PlannerRequestBase`
      (`:727-755`), cioè dalla request PAC e dalle due del ribilanciatore. `CurrencySpec` (`:394`)
      resta, perché serve ai cataloghi del risultato.
    - Normalizer (`normalize.py`): via `validate_currency_specs` (`:208-220`) e la sua chiamata
      (`:1069`). `build_scenario` deriva la spec per ogni valuta di `currency_references`, che
      comprende la valuta di valutazione richiesta da `models.py:603`, con
      `Decimal(1).scaleb(-get_currency_precision(code))`.
    - Il wire valida già `CurrencyCode` contro ISO 4217 (`schemas/common.py:74-98`, pycountry).
      Per un codice che CLDR non elenca, babel applica la regola `DEFAULT` di CLDR (2 cifre):
      è la regola dello standard, non un nostro default. Per il quantum non esiste quindi più un
      caso `needs_input`/`unsupported`.
    - Escono i codici `allocation.currency_minor_unit_nonpositive` e
      `allocation.currency_spec_missing`: dal Literal dei planner (`:246-327`), da
      `W1_NORMALIZER_ISSUE_DEFINITIONS` e dal controllo a 80 di `issues.py:49` (commento
      compreso).
    - Copia (`portfolio_allocation_source.py`):
      - vanno via `_build_currency_specs` (`:1501-1548`, e con lui il suo `precision is None → 2`
        locale), l'accumulo delle valute (`:1680-1708`) e `currency_specs=` (`:1721`);
      - l'issue di valuta non valida del PMC (`:1229`) passa a `section="wac_contexts"`,
        `entity_kind="wac_context"`, `entity_id=_wac_key(…)`, `field="unit_cost"`.
    - Schema della copia (`schemas/portfolio.py`):
      - escono `PortfolioPlannerSourceCurrencySpec` (`:1322-1326`), la sezione `"currency_specs"`
        (`:1217`), l'entity kind `"currency_spec"` (`:1238`) e il campo di risposta (`:1602`);
      - `allocation.currency_spec_missing` **resta** fra i codici della copia (`:1561`), con il
        significato «valuta non valida nel DB».
    - ✅ **C0b.1 eseguito (2026-09-24).**
      > **Note implementazione**: `normalize.py` ha `currency_minor_unit(code)` =
      > `ExactRatio(1, 10**get_currency_precision(code))`; `build_scenario` costruisce una spec per
      > ogni valuta di `currency_references`. Ho verificato che l'insieme copre tutto ciò che
      > l'evaluator esige (`_referenced_currencies`, `evaluator.py:236-251`): valutazione `:206`,
      > quote `:250`, cassa `:436`, contributi `:447`, route di funding `:467`, commissioni `:358`,
      > vendite `:661/:682/:696`. Babel 2.18.0: `get_currency_precision` non solleva e non torna mai
      > `None` (JPY 1, BHD 1/1000, CLF 1/10000, XAU/XXX e codici fuori CLDR 1/100). Codici issue
      > 80 → 78 (`issues.py:49`). Copia: via `_build_currency_specs`, l'import di babel, gli accumuli
      > di valute nei due helper (ora tornano solo le righe), `currency_specs` dalla risposta, la
      > sezione `currency_specs` e l'entity kind `currency_spec`; l'issue PMC con valuta asset non
      > valida sta ora in `wac_contexts`/`wac_context`/`_wac_key(…)`/`unit_cost`. Import di prova
      > dei moduli: 78 codici, `currency_specs` assente dalla request.
      > **⚠️ Fuori pista**: le chiavi di `fx_rates` erano validate solo con la regex
      > `^[A-Z]{3}/[A-Z]{3}$` (`schemas/pac_allocator.py:170`), non contro ISO 4217 — la frase
      > «il wire valida già `CurrencyCode`» valeva per i campi, non per le chiavi FX. Finora un
      > codice non ISO in una chiave finiva in `currency_spec_missing` (una spec per lui non si
      > poteva nemmeno scrivere, `CurrencySpec.currency` è ISO); senza quel controllo avrebbe
      > ricevuto il `DEFAULT` di CLDR in silenzio. `_validate_fx_rate_pair_keys` ora passa
      > entrambi i codici da `Currency.validate_code`: è solo runtime, lo schema JSON non cambia.
      > Resta nel Literal `PlannerIssueEntityKind` il valore `"currency"` (`:930`), che nessun
      > produttore usa più: non lo tolgo, lo annoto per R2.
  - **C0b.2 — Q-C0-4, `min_fragmentation` esce dal wire.**
    - `PacPlannerRequest.policy` (`:758`) e `PacScenarioBasis.policy` (`:2346`) diventano
      `Literal["proportional"]`.
    - La base `PlannerScenarioBasis.policy` (`:1342`) si restringe solo se si verifica che non
      viene mai istanziata direttamente.
    - Le policy del ribilanciatore (`:767`, `:772`, `:2350`) restano come sono.
    - `ExactPlannerScenario`, evaluator e oracolo non cambiano: il ramo resta scritto e spento
      (TODO_FUTURI, «differita»).
    - Una request con `min_fragmentation` diventa wire-invalid (test `test_pac_planner_schemas.py:1695`).
    - Effetto sul client generato: il codec passa da `z.enum(["proportional","min_fragmentation"])`
      (`generated-tools.ts:564,936`, client del 24/09 alle 10:07) a `z.literal("proportional")`.
      Il Passo 8 legge quindi le opzioni con un helper che accetta sia `ZodEnum.options` sia
      `ZodLiteral.value` (zod 3.24.1).
    - ✅ **C0b.2 eseguito (2026-09-24).**
      > **Note implementazione**: `PacPlannerRequest.policy` e `PacScenarioBasis.policy` ora sono
      > `Literal["proportional"]`, con un commento che rimanda a TODO_FUTURI. La base
      > `PlannerScenarioBasis` non viene mai istanziata direttamente: l'unica costruzione è
      > `PacScenarioBasis(…)` in `planner_report.py:187`, e i tre usi a `:2180/:2207/:2225` sono
      > annotazioni di parametro. L'ho quindi ristretta a `["proportional", "invest_only",
      > "invest_and_sell"]`; non compare nello schema JSON. `models.py:72/578/871`,
      > `evaluator.py:1460-1468` e `compiler.py:119` restano come sono: il ramo è scritto e spento.
  - **C0b.3 — Q-C0-7, esposizioni oltre il 100%.**
    - In `validate_asset_exposures` (`normalize.py:258-274`): somma esatta dei pesi per Asset e
      dimensione. Oltre 1 nasce l'issue `allocation.exposure_total_exceeds_one`, kind `invalid`,
      a `field_path("assets","asset",id,"exposures.weight")`, con la dimensione come parametro
      testuale. Una somma sotto 1 resta ammessa.
    - Il codice va nel Literal, in `W1_NORMALIZER_ISSUE_DEFINITIONS`, nel controllo di
      `issues.py:49` (**80 − 2 + 1 = 79**) e nell'i18n di C8.
    - Oggi lo stesso input produce `execution_failed` (N22, provato):
      `planner.py:171 > 250 > 333` → `planner_report.py:291 > 370 > 404` → `ValidationError` in
      `PacExposurePlanRow`. TB4 fissa prima l'esito attuale, poi il nuovo.
    - ✅ **C0b.3 eseguito (2026-09-24).**
      > **Note implementazione**: `validate_asset_exposures` somma in modo esatto i pesi per
      > dimensione (`defaultdict` di `ExactRatio`) e, per ogni dimensione sopra 1, emette
      > `allocation.exposure_total_exceeds_one` (`invalid`) a `assets/asset/<id>/exposures.weight`
      > con il parametro testuale `dimension`. Codice nel Literal (in ordine alfabetico, prima di
      > `exposure_weight_out_of_range`) e in `W1_NORMALIZER_ISSUE_DEFINITIONS`; controllo
      > `issues.py:49` a **79**. Docstring di `planner_report._declared_weight` aggiornata: ora
      > il residuo è garantito non negativo dal normalizer.
      > **⚠️ Fuori pista**: il piano non diceva come convivono i due codici. Scelta: se una
      > dimensione ha già un peso fuori da [0, 1] non emetto anche il totale, perché la causa è
      > quel peso e la somma non ha senso; le chiavi duplicate invece restano nella somma (la
      > duplicazione è segnalata a parte, col suo parametro). Da confermare in review R2.
      > Sonda in-process `/tmp/libreFolio_d_c0b_probe.py` (nessun DB, nessuna porta), log
      > `/tmp/libreFolio_d_c0b_probe.log`: fixture minima PAC senza `currency_specs` → `ready`,
      > spec derivata `EUR 1/100`; la stessa con `currency_specs` → `extra_forbidden`;
      > `min_fragmentation` → `literal_error`; chiave FX `EUR/ZZZ` → rifiutata; un secondo
      > `asset_type` a 0,5 sopra un 1 → `invalid` con il solo nuovo codice e `dimension=asset_type`.
  - **C0b.4 — Q-C0-6, sezione `current_distribution` della copia.**
    - Request: `PlannerSourceSection.CURRENT_DISTRIBUTION` in `requested_sections`. Richiede
      almeno un broker OWNER selezionato, come le altre copie.
    - Motore: `PortfolioCalculationEngine(session).calculate(user_id, broker_ids=sorted(OWNER
      selezionati), date_from=None, date_to=as_of, target_currency=target_currency)`. È la stessa
      chiamata di `get_summary` (`portfolio_service.py:676-715`): stessi numeri della pagina
      Allocazione e, se `as_of` è oggi, lo stesso blob in cache. Il controllo di equivalenza con
      `date_from=as_of` non serve più.
    - Posizioni: `position_states_end`. Un asset è «posseduto» se `quantity >
      _QUANTITY_DUST_THRESHOLD` (`Decimal("0.00001")`, `portfolio_service.py:438`, import pigro
      per evitare il ciclo fra moduli). Il `market_value` si somma per asset sui broker
      selezionati; la quota OWNER l'ha già applicata il motore.
    - Denominatore: gli asset dello scenario (`asset_ids`). La cassa è esclusa; un asset
      selezionato ma non posseduto vale 0.
    - Un asset posseduto con `market_value` assente o negativo porta lo stato `incomplete`, senza
      pesi. Gli issue riusano `allocation.price_missing` (sorgente MISSING) e
      `allocation.saved_fx_missing` (coppia come parametro, da `missing_fx_pair`). Un totale nullo
      porta lo stato `no_holdings`.
    - Pesi: frazione esatta, troncata a 0,0001 e completata col metodo dei resti maggiori.
      A parità di resto vince l'`asset_id` più basso. La somma è esattamente 1.
    - Risposta: `current_distribution`, assente se la sezione non è richiesta.
      - Campi: `status`, `method: "portfolio_engine_market_value"`, `rounding:
        "largest_remainder"`, `weight_quantum: "0.0001"`, `as_of`, `provenance_id` (nuova sorgente
        `source:portfolio-engine`, dominio `portfolio`).
      - Righe: `weight_id` (`current:asset:{id}`), `asset_id`, `held`, `weight` (assente se
        `incomplete`), `valuation_source`, `valuation_reference_date`, `valuation_stale`.
      - Nuova sezione `"current_distribution"` in `PlannerSourceResponseSection` e nuovo entity
        kind `"current_weight"`.
      - **Nessun importo sul wire**: i pesi sono pubblici (decisione c).
    - Differenza voluta rispetto alla dashboard (`portfolio_service.py:1079-1083`). Là il
      denominatore sono tutti gli holding con valore, la precisione è 0,01 senza garanzia sulla
      somma, e un holding senza valore sparisce in silenzio. Qui il denominatore è lo scenario e un
      valore mancante dà `incomplete`. Il dialogo della copia lo dice (delta §3.6, `s6_copy`).
    - ✅ **C0b.4 eseguito (2026-09-24).**
      > **Note implementazione**: schema (`schemas/portfolio.py`, solo blocco planner-source):
      > `PlannerSourceSection.CURRENT_DISTRIBUTION`, sezione di risposta `current_distribution`,
      > entity kind `current_weight`, costante `PLANNER_CURRENT_WEIGHT_QUANTUM`, modelli
      > `PortfolioPlannerCurrentWeight` e `PortfolioPlannerCurrentDistribution`, campo di risposta
      > `current_distribution` opzionale (default `null`, quindi i costruttori esistenti restano
      > validi). Il modello si autoverifica: `complete` ⇒ ogni riga pesata e somma esattamente 1;
      > altrimenti nessun peso; ogni peso multiplo di 0,0001; asset distinti. Servizio
      > (`portfolio_allocation_source.py`): `_build_planner_current_distribution` con import pigri
      > (`portfolio_service` importa questo modulo al caricamento), la stessa chiamata al motore di
      > `get_summary`, posizioni oltre `_QUANTITY_DUST_THRESHOLD`, somma per asset sui broker;
      > `_largest_remainder_weights` lavora in `Fraction` esatte. Nuova provenance
      > `source:portfolio-engine` (dominio `portfolio`, `portfolio_engine.PortfolioCalculationEngine`).
      > Issue a `current_distribution/current_weight/current:asset:<id>/weight`.
      > Sonda in-process `/tmp/libreFolio_d_c0b4_probe.py` → `/tmp/libreFolio_d_c0b4_probe.log`
      > (nessun DB, nessuna porta): 1/3 ciascuno → `0.3334` all'`asset_id` più basso; 7 asset
      > uguali → quattro `0.1429` e tre `0.1428`, somma `1.0000`; un valore minuscolo → `0.0000`;
      > i validator rifiutano somma ≠ 1, pesi con `incomplete`, pesi fuori quanto, asset duplicati.
      > Il percorso col DB lo prova TB6 (test-author, lane 6151) e S16 sulla copia di prod.
      > **⚠️ Fuori pista** (quattro scelte non scritte nel piano, da confermare in review R2):
      > 1. `asset_ids` **obbligatorio** quando si chiede `current_distribution` (validator della
      >    request → 422): senza scenario il denominatore non esiste. `asset_ids: []` è ammesso e
      >    dà `no_holdings` senza righe.
      > 2. Campo in più `valuation_days_before_requested` sulle righe, come `days_before_requested`
      >    dei prezzi: il dialogo mostra «1 giorno prima» senza aritmetica di date nel frontend,
      >    che su `YYYY-MM-DD` sbaglia di un giorno con i fusi.
      > 3. Valore negativo → `allocation.nonpositive_price` (`invalid`). Il codice esiste già fra i
      >    79 del planner, quindi l'unione i18n resta 82; l'ho aggiunto solo al Literal della copia.
      >    Un valore **zero** con quantità positiva resta valido (peso 0).
      > 4. La coppia di `saved_fx_missing` va in forma canonica ascendente (`EUR/USD`), come nella
      >    sezione `fx_quotes`; il motore la dà come `nativa/target`.
      > Stato con totale nullo e asset posseduti a valore zero → `no_holdings`; `incomplete` ha
      > la precedenza. Una posizione negativa (short) il motore non la emette: non posseduto.
  - **Gate di C0b** — ✅ 2026-09-24 (parte backend; i test sono il Passo D):
    - `ruff check` sui 7 file toccati → «All checks passed!» (due UP037 corretti a mano);
      `black --check` → invariati 6 file. **⚠️ Fuori pista**: `schemas/pac_allocator.py` non è
      black-pulito **già a `HEAD`** (solo righe vuote in eccesso, nessuna riga di codice): non
      riformattato, per non gonfiare il diff e i conflitti; i miei hunk sono conformi.
    - `git diff --check` → pulito.
    - `api sync` alle **13:41 del 24/09** (`/tmp/libreFolio_d_api_sync_c0b.log`): client e
      `openapi.json` rigenerati, ignorati da git. Fingerprint dei contratti tool
      `9e8930fff51397d66adaefc763550c888429477d12ca0629dbf77bfdc57c7efb`.
    - Nuovi fingerprint dello schema completo (`test_pac_planner_schemas.py:2603,2609`,
      `/tmp/libreFolio_d_fingerprint_probe.log`): PAC
      `a4f499864b74cdea63a8411ff26b80877055a8b8fd297524d2a5197a8fc41923`, ribilanciatore
      `c4451b184aa0fd9f670a27f8be53fc1aa4e11c852cb3dc631199b3fd1d805446`.
  - **Gate di C0b** (testo originale):
    - `ruff`/`black` (skill lint-format);
    - `pipenv run python dev.py api sync`, che non apre porte. Registro il nuovo fingerprint
      (`test_pac_planner_schemas.py:2603`) e l'ora del client;
    - test backend via test-author nella lane di suite 6151 (TB1–TB5 del Passo D);
    - `git diff --check`.

- **C1 — Dati:** `features/tools/pac-allocator/planner/source.ts`.
  - Client di `POST /portfolio/allocation-source` con `requested_sections`, `broker_ids`,
    `asset_ids`, `as_of` e `target_currency`.
  - Mapper 1:1 snapshot → frammenti di draft: provenance, `captured_at`, freshness (con
    `days_before_requested` per l'età), `quote_base_quantity`. Il `minor_unit` non viaggia più
    (C0b.1).
  - Sezione `current_distribution` (C0b.4) → proposta di target, applicata solo dal dialogo.
  - Nessuna somma e nessuna conversione.
  - Un 403 o un 404 arriva esplicito all'utente, mai come broker o asset omessi in silenzio.
  - Niente `/assets/prices/current`, che può scrivere OHLC.
- **C2 — Draft:** `planner/draft.svelte.ts`, con le runes; il pattern `importedValue`/`stale`
  viene da `draftFactories.ts` P1.
  - Sezioni per step e `draft_revision` monotona.
  - Pulsanti di copia indipendenti (liquidità, prezzi, classificazioni, FX, distribuzione
    corrente), che non sovrascrivono mai in silenzio un campo modificato: conflitto B4.
  - La distribuzione corrente riempie i pesi target solo con «Usa come target»; gli asset manuali
    ricevono 0 con nota esplicita. Con `incomplete` il pulsante è disabilitato e nessun target
    cambia.
  - Età dei prezzi (Q-C0-3): si mostra quanti giorni ha il dato, non c'è conferma. All'invio
    `stale{age_days, accepted:true}` per età > 0, `fresh` altrimenti.
  - Tetto delle route (Q-C0-5): default `'1000000000'` da `planner/defaults.ts`, con il TODO
    «ridurre dopo le simulazioni sui tempi».
  - Guardia sulle risposte vecchie (token di richiesta più `accountGeneration`). Nessun binding live.
- **C3 — Shell a 9 step, ristretta alla 2.0.0:**
  - Scenario: solo PAC puro;
  - Liquidità: cassa per broker × valuta, contributi separati;
  - Broker: capability quantità intera con passo o importo, fee;
  - Asset: da DB o manuali;
  - Routing;
  - Target: pesi in %;
  - FX: tassi e spread;
  - Strategia: `proportional`. Le card nascono dalle opzioni del contratto generato
    (`toolContractMap.pac_allocator['2.0.0']`), nessuna lista scritta a mano (Q-C0-4);
  - Review.

  Gli issue del backend vengono mappati su step e campo tramite `path`. **Nessun calcolo economico nel
  frontend.** Per Q-C0-2 la UI calcola solo percentuali di controllo, a titolo informativo: totale
  e restante del target, più il confronto nella stessa unità «selezionato ≤ disponibile» su una
  riga di cassa. Non somma importi: il riepilogo della liquidità conta le fonti. I numeri del
  risultato arrivano tutti dal backend. I controlli che decidono restano al backend:
  `allocation.target_total_not_one` (`normalize.py:303`) e `allocation.cash_selection_invalid`
  (`:443`).
- **C4 — Esecuzione:** `runTool('pac_allocator','2.0.0',{descriptor, correlationId, parameters, signal})`.
  Il ciclo run/annulla/metriche e le guardie account vengono da `PacAllocatorTool.svelte` P1.
  - `data-busy` e annulla (D7).
  - Un risultato su una revisione vecchia è marcato stale (D15).
  - Cambio account → teardown (D16), già garantito dal mount del registro.
- **C5 — Risultati:**
  - C1 header e KPI, C2 matrice target/dopo, C4 esposizioni (`exposure_rows` backend),
    C5 riepilogo asset;
  - C10–C12 piano operativo in tabelle (funding → FX → ordini per broker), C13 dettaglio ordine,
    C14 proof e diagnostica;
  - D8–D16 stati;
  - un grafico prima/target/dopo **in %**, PAC-local;
  - l'`OutcomeSummary` riparte da `AllocationDiagnostics` P1, con gli stati ampliati;
  - **fuori da questa fetta (Q1):** il Sankey/ribbon dei flussi e la rifinitura mobile fine
    della serie D, che vengono dopo la review.
- **C6 — Registrazione in `registry.ts:240-251`:**
  `defineToolRenderer('pac_allocator','2.0.0',{componentKey:'pac-allocator', uiVersion:'2.0.0', load: () => import('./pac-allocator/planner/PacPlannerTool.svelte')})`
  al posto del blocco di commento.
- **C7 — Privacy:** un solo adapter, `planner/format.ts`, così un cambio di API di J tocca un file solo.
  - Importi → `formatCurrencyAmountPlain/Html`, sensibilità di default (personal). Le cifre
    decimali:
    - nel risultato vengono da `catalogs.currencies[].minor_unit`, cioè dal backend;
    - nel draft, dove il catalogo non esiste ancora, sono le cifre CLDR lette con
      `new Intl.NumberFormat('en',{style:'currency',currency}).resolvedOptions().maximumFractionDigits`,
      solo dentro `planner/format.ts`. È lo stesso schema di
      `features/ai-export/templates/snapshotDataRenderer.ts:226`, e per lui il gate di J ha una
      voce di falso positivo noto in `utils/privacy/moneyRenderSites.test.ts:174-176`. D aggiunge
      una voce gemella per `planner/format.ts`, attraverso il coordinator, perché il file è di J.
      Formatta cifre, non calcola: non tocca Q-C0-2.
  - Prezzi e tassi FX → `sensitivity:'public'`. Percentuali → `formatPercent`.
  - Quantità → `maskable(formatDecimalForDisplay(q), 'personal')` (D5′). L2 → `≈••• EUR²`, unità fuori
    dalla maschera.
  - Ramo `exact_ratio` di un valore personale: `≈` e segno fuori, cifre `•••` (J, 24/09).
  - `maskable(…, 'public')` solo per tassi e percentuali. Tetti e minimi delle route: mascherati in
    sola lettura fino a R7.
  - Export previsti: `formatPlannerMoneyPlain/Html`, `formatPlannerPricePlain/Html`,
    `formatPlannerQuantity`, `formatPlannerFxRate`, `formatPlannerPercent`, `formatPlannerL2`.
  - Grafici solo in % e tooltip passati dai formatter. **Nessuna maschera propria.**
  - **Mai** `formatCurrencyAmount` di `components/risk/riskAnalysisHelpers.ts:155`: a L160
    restituisce il segnaposto al posto dell'intera stringa, valuta compresa, contro la decisione
    (c). J lo sta riparando; il PAC non lo importa in ogni caso.
  - I valori esatti restano stringhe; `Number()` si usa solo al confine di visualizzazione, mai in
    aritmetica.
- **C8 — i18n:**
  - `tools.pacAllocator.planner.*` via `dev.py i18n add` nelle 4 lingue;
  - messaggi issue sotto `tools.pacAllocator.planner.issues.<code>`, con parametri ICU. Planner e
    copia usano entrambi `message_key = code` (`issues.py:137`,
    `portfolio_allocation_source.py:466`). Dopo C0b le chiavi sono **82**:
    - i 79 codici del planner;
    - i 3 codici della sola copia (`allocation.saved_fx_missing`, `allocation.wac_fx_missing`,
      `allocation.currency_spec_missing`).

    Dei 19 codici della copia (riconteggio del 24/09: erano stati dati come 18), 16 coincidono con
    codici del planner; l'unione resta 82. Per questi il messaggio deve
    reggere i parametri di entrambe le fonti: li confronto in C8, e dove divergono il messaggio
    non li usa. Conteggio misurato sui due Literal (`PlannerIssueCode`, `PortfolioPlannerSourceIssueCode`);
    i parametri money passano dal formatter personal;
  - fallback per codice sconosciuto;
  - 16 messaggi PAC-locali per i `ToolErrorCode` sotto `tools.pacAllocator.planner.toolErrors.<code>`
    (N17), finché non esiste un namespace comune;
  - le chiavi P1 restano (decisione a).

> ✅ **2026-09-24 — C1–C8 eseguiti (codice).** La verifica sulla copia di prod (card `ready`, nessun
> toast dovuto al PAC) è il Passo E: fino ad allora il Passo C resta aperto.
> ✅ **Chiuso lo stesso giorno (17:40):** card `ready` e nessun banner o toast degradato sulla copia
> di prod. Prova nella nota del Passo E.
>
> **Note implementazione.** Albero nuovo, non tracciato:
> `frontend/src/lib/features/tools/pac-allocator/planner/`, 62 file e circa 7 900 righe:
> - 18 moduli alla radice;
> - `shared/` 9, `steps/` 15, `shell/` 2, `result/` 18.
>
> Nessun file P1 riusato per import: i pattern (draft, ciclo di run) sono stati ripresi, non importati.
> - **C1** — `source.ts`:
>   - `fetchPlannerSource(query, accountGeneration, signal)` chiama `POST /portfolio/allocation-source`;
>     i mapper sono 1:1, senza somme né conversioni;
>   - 403 e 404 diventano `PlannerSourceError` (`broker_forbidden` / `asset_not_found`) e arrivano
>     all'utente;
>   - `/assets/prices/current` non viene mai chiamato (`source.ts:6`, `copies.ts:7`);
>   - `scope.ts` carica i broker selezionabili (OWNER); `sourceLoad.svelte.ts` guida il caricamento
>     con il suo errore.
> - **C2** — `draft.svelte.ts` (`PlannerDraft`, runes):
>   - `draft_revision` monotona; `FactOrigin` `copied|manual`; 6 `CopyKind`;
>   - le copie e i loro conflitti sono in `copies.ts` (`apply*Copy`, `CopyConflict` →
>     `shared/ConflictDialog.svelte` → `resolveConflicts`);
>   - distribuzione corrente: `distributionProposal`/`applyDistribution`, applicata solo da
>     `steps/DistributionDialog.svelte`;
>   - `DEFAULT_ROUTE_CAP = '1000000000'` con il TODO di Q-C0-5 (`defaults.ts:8-11`).
> - **C3** — i 9 step in `steps/*Step.svelte`, più 6 dialoghi; `shell/StepNav.svelte` e
>   `SummaryPanel.svelte`:
>   - `request.ts` espone `buildRequest`, `localProblems` e `stepOfWirePath`;
>   - le policy vengono dal contratto compilato (`policies.ts`, `contractPolicies()`);
>   - i problemi di build si vedono nella Review, non in un toast;
>   - il footer usa `common.back` / `common.continue`.
> - **C4** — `run.svelte.ts` (`PlannerRun`):
>   - `start(built, accountGeneration)` → `runTool`, con `stop()`, `discard()` e `dispose()`;
>   - lo stale si decide confrontando `draft_revision` con la revisione del risultato;
>   - le metriche riusano `ToolExecutionMetrics`; `result/BusyPanel.svelte` ha l'h2 focalizzabile.
>
>   A8 (lasciare con un draft sporco chiede conferma) è in `PacPlannerTool.svelte:165-197`. Un
>   cambio di sessione non chiede nulla: il registro smonta il renderer.
> - **C5** — `result/` (18 file):
>   - OutcomeHeader, KpiCards, WeightBars (grafico in %, PAC-local), ExposureSection, AssetTable,
>     OperationalPlan, OrderDetail, LedgerTable, ProofPanel;
>   - gli stati: StateNotice, FailurePanel, ToolErrorPanel, StaleBanner;
>   - `model.ts` e `text.ts` solo formattano, senza aritmetica economica;
>   - il Sankey resta fuori (Q1).
> - **C6** — `registry.ts:241-244`: `defineToolRenderer('pac_allocator','2.0.0', …PacPlannerTool.svelte)`.
>   `registry.test.ts:135-157` attende `ready` sul contratto compilato e `renderer_missing` con un
>   registro vuoto.
> - **C7** — `format.ts` è l'unico adapter:
>   - importi → `formatCurrencyAmountPlain/Html`;
>   - prezzi, FX e % → `'public'`; quantità e L2 → `maskable(…,'personal')`;
>   - nessuna maschera propria, 0 import da `riskAnalysisHelpers`;
>   - l'unico `Intl.NumberFormat` è `format.ts:27` (cifre CLDR); l'unico `toFixed` è
>     `result/model.ts:74`, una larghezza CSS in %.
> - **C8** — 692 chiavi per lingua (511 statiche e 181 dinamiche, di cui 82 issue e 16 `toolErrors`):
>   - 692 `dev.py i18n add`, fail=0 (10 min 21 s);
>   - diff per catalogo +868/−2: le due righe sono la descrizione del Passo B e la virgola di
>     `valuationSettingsInfo`;
>   - parità a 4095 chiavi per lingua, nessuna rimossa né cambiata;
>   - ICU: 2076 controlli con il parser formatjs, 0 difformi.
>
> **Evidenze** (client TS generato il 24/09 alle 14:19):
> - `pipenv run python dev.py front check` → **3 errors / 41 warnings / 4 files = pavimento**, 0
>   diagnostiche nel planner (`/tmp/libreFolio_d/front_check_c8.log`);
> - `npx vitest run src/lib/utils/privacy/moneyRenderSites.test.ts src/lib/features/tools/registry.test.ts`
>   → 2 file, 14/14;
> - `dev.py i18n audit` → planner **DEAD 0**, UNVERIFIED 3 (`origin.copied`,
>   `result.sections.exposures`, `result.sections.ledger`: chiavi dinamiche risolte a runtime).
>   Il totale «Likely Unused» torna a 422, pari al baseline;
> - `npx prettier --check` sul planner → pulito.
>
> **⚠️ Fuori pista.**
> - `copies.ts` — un difetto trovato scrivendo i dialoghi. Una copia con **tutte** le righe in
>   conflitto veniva potata all'applicazione; «Aggiorna» timbrava poi righe che puntavano a una
>   copia inesistente, e la provenance si perdeva. Correzione: `CopyOutcome.copy`, e
>   `resolveConflicts` ri-registra la copia su `'update'` (`copies.ts:21,36,382-384`).
> - `run.svelte.ts` — il warning `state_referenced_locally` è stato risolto con `$state.raw`
>   (`:24,26`) più un getter del descriptor.
> - `store_rune_conflict`: variabili rinominate `stepState` (`shell/StepNav.svelte:23`) e
>   `resultState` (`result/ResultView.svelte:58`).
> - Gate di J — una voce `not-money` aggiunta in coda a `utils/privacy/moneyRenderSites.test.ts:215-218`
>   per `format.ts:27`. È la gemella di `snapshotDataRenderer`. **File di J**: va nell'handoff come
>   file condiviso.
> - Visibilità all'audit (non prevista dal piano). `scripts/i18n_usage.py` risolve solo const
>   quotate dello stesso file e teste letterali di template. Il primo audit dava quindi **297 chiavi
>   del planner DEAD**, pur usate.
>
>   In 23 file:
>   - namespace locale quotato per modulo (`const PLANNER_KEY = 'tools.pacAllocator.planner'`), con
>     il motivo commentato in `labels.ts:6-9`;
>   - const di template diventate letterali;
>   - teste letterali per i codici puntati (`issues.ts:138`, le `reasons` di OperationalPlan e
>     ProofPanel);
>   - rimosso l'export inutilizzato `ISSUE_KEY_PREFIX`.
>
>   Nessun cambio di comportamento: stesse chiavi, stessa risoluzione.
> - Prettier: i 24 file nuovi non erano formattati. Ho eseguito `--write` sul solo albero
>   `planner/`; i file condivisi erano già puliti e sono rimasti intatti.
> - Etichetta breve EN di «dopo»: `D` → `A` (`result/WeightBars.svelte`). IT O/D, FR C/A, ES O/D.
> - Da portare in review (R7, non corretti):
>   - `result.text.units` = «{quantity} units» non ha il plurale, quindi può scrivere «1 units»;
>   - L2 si formatta con `toLocaleString`, cioè nella locale del browser (`format.ts:185`), mentre
>     quantità e tassi usano `formatDecimalForDisplay`, non localizzato (punto decimale).

### Passo D — Test

**Frontend** — test list sottoposta al developer; Vitest, jsdom per i componenti; registrazione in
`front-utility core-unit`/`component-unit`:

| # | Caso | Asserzione |
|---|---|---|
| T1 | mapper sorgente | Cassa per broker × valuta non sommata. Prezzo con `quote_base_quantity`, data, fonte e staleness. Prezzo assente = assenza esplicita. 403/404 visibili. |
| T2 | draft | Copie indipendenti. Nessuna sovrascrittura silenziosa. `draft_revision` monotona. Risposta vecchia scartata. `accountGeneration` cambiata → scarto. |
| T3 | request builder | Stringhe decimali intatte (nessun passaggio da `Number`). Unità esplicite. ~~Draft vuoto → request valida che dà `needs_input`~~ **Corretto il 24/09:** un draft vuoto dà `{ok:false, problems}`, cioè problemi locali per step (D8, `request.ts:217-219`), e nessuna request. `needs_input` si prova con le fixture (T5) e via API (TB1). Nessun `currency_specs` nella request (C0b.1). `policy` letta dal contratto: con una sola opzione è `proportional` (C0b.2). Prezzo con età > 0 → `stale{age_days, accepted:true}`, del giorno → `fresh` (Q-C0-3). Tetto della route precompilato `1000000000` nell'unità della modalità (Q-C0-5). |
| T4 | lifecycle | `data-busy`, annulla, stale (D15), cambio account (D16). |
| T5 | stati da fixture | `needs_input`, `invalid`, `unsupported`, `ready_no_op`. ~~`ready_incumbent` × {`optimal_proven` oracolo, `optimal_proven` lattice, `gap_bounded`, `not_proven`}. `ready_infeasible` × {oracolo, conflitto deterministico}.~~ **Corretto il 28/09 (D-X1, commit 4):** `ready_incumbent` × {`optimal_proven` da `solver_status`, `not_proven`}; `ready_infeasible` × {`infeasibility_proven` da `solver_status`}; le altre forme non esistono più sul wire. `ready_no_incumbent`, per limite e, fino al commit 5, per replay respinto. Per ognuno `data-state`; badge «ottimo» **solo** con `optimal_proven`. |
| T6 | issue | Ogni codice del wire ha un messaggio in 4 lingue (confronto con la lista generata). Fallback. Parametri ICU. `path` → step. |
| T7 | privacy | Privacy ON: importi, fee, residui, L2 e quantità → `•••`, con il **codice valuta visibile** (decisione c); prezzi, FX e % in chiaro; segno fuori dalla maschera (D8); tooltip e label mascherati. Privacy OFF: tutto in chiaro. Il gate di J resta verde sui file nuovi. Nessun import da `riskAnalysisHelpers`. |
| T7b | quantità (J) | Privacy ON: istruzione e quantità economica `•••` via `maskable(…, 'personal')`; OFF in chiaro. Nessuna cella con quantità in chiaro accanto a un prezzo pubblico. Caso `≈`: un valore personale `exact_ratio` rende `≈•••`, senza cifre. Delta C0 §10.1. |
| T8 | registro | `registry.test.ts:135-146` → `ready`; `renderer_missing` coperto con un registro vuoto. |
| T9 | build | `api sync` → `front check` al pavimento (con l'ora del client) → `front build`. |
| T10 | copia della distribuzione corrente (Q-C0-6) | Il dialogo mostra fonte, data, broker OWNER e le righe con età del prezzo. «Usa come target» riempie i pesi solo alla conferma. Un target già modificato non si sovrascrive in silenzio (B4). Asset manuale → 0 con nota. `incomplete` → pulsante disabilitato, nessun target cambiato. `no_holdings` → messaggio, nessun target cambiato. Pesi in chiaro, nessun importo. |

In tutti i test le select (`AssetSelect`, `BrokerSearchSelect`, `CurrencySearchSelect`) si
pilotano per `data-testid` e valore, **mai per posizione**. L'R13 di K cambierà l'ordine di
`filterOptions` (`optionFilter.ts:37`): prima il nome, poi la descrizione.

E2E Playwright: **dopo** l'approvazione umana, come da hard gate di Step 5 (Step 6).

**Backend** — via test-author, suite 6151:
- **TB1:** nuovo `test_api/test_pac_planner_tool_api.py`, selector nuovo `api pac-planner-tool`.
  Copre compute autenticato bulk con `pac_allocator`/`plan`:
  - scenario piccolo → `ready_incumbent` + `optimal_proven`;
  - `needs_input`;
  - 401;
  - versione o fingerprint errati;
  - item ripetuti con correlation ID diversi;
  - `policy: "min_fragmentation"` rifiutata dal codec (C0b.2; chiude N1).
- **TB2:** `POST /portfolio/allocation-source` a livello API: auth, 403 broker, 404 asset, forma della risposta.
- **TB3:** `services tools-registry` sulla descrizione.
- **TB4 (N22, Q-C0-7):** esposizioni > 100% per Asset e dimensione.
  - Prima fissa l'esito attuale, provato: `execution_failed` per `ValidationError` in
    `PacExposurePlanRow`.
  - Dopo C0b.3 attende l'issue `allocation.exposure_total_exceeds_one` (`invalid`) al suo `path`,
    con la dimensione come parametro. Somma esattamente 1 e somma sotto 1 restano ammesse.
  - Conteggio dei codici 79 (`issues.py:49`) e fingerprint aggiornato.
- **TB5 (Q-C0-1):** quantum da babel.
  - Una request con `currency_specs` è wire-invalid.
  - I cataloghi del risultato portano il `minor_unit` CLDR: JPY `1`, EUR `0.01`, KWD `0.001`.
    EUR non è elencato nella tabella CLDR: vale la regola `DEFAULT` (verificato con babel il
    24/09).
  - La copia non ha più la sezione `currency_specs`; l'issue di valuta non valida del PMC punta a
    `wac_contexts`.
  - Uno scenario tutto manuale arriva a `ready_*` senza alcuna copia (chiude la parte quantum di
    N18).
- **TB6 (Q-C0-6):** sezione `current_distribution`.
  - Stessi pesi della dashboard quando lo scenario comprende tutti gli holding: confronto con
    `get_summary` sullo stesso DB di test, a meno dell'arrotondamento.
  - Denominatore = scenario; asset selezionato non posseduto → 0; la cassa non entra.
  - Resti maggiori con parità risolta per `asset_id`; somma esattamente 1.
  - Posseduto senza prezzo o senza FX → `incomplete`, nessun peso, issue con `path`.
  - Nessun posseduto → `no_holdings`.
  - Broker non OWNER → 403; sezione non richiesta → campo assente.
  - Nessun importo nella risposta.
- Le aggiunte a T3, T5, T6 e T7 sono nel delta C0 §10.1.

> ✅ **2026-09-24 — Passo D backend eseguito da test-author** (agente `tb-c0b-tests`, lane di suite
> 6151 + `/tmp/librefolio-r2-d`, un comando alla volta, log `/tmp/libreFolio_d_tb_<nome>.log`).
> **Note implementazione.**
> - 12 file modificati + 1 nuovo, tutti in `backend/test_scripts/` e nel catalogo del runner:
>   - fixture `pac_allocator/` (4 JSON: via `currency_specs`, `policy` → `proportional`);
>   - `test_schemas/test_pac_planner_schemas.py` (79 codici, fingerprint `a4f49986…`/`c4451b18…`,
>     `currency_specs` rifiutato per PAC e per le due policy del ribilanciatore);
>   - `test_services/`: `test_pac_planner_normalize.py`, `test_pac_planner_evaluator.py`,
>     `test_pac_planner_planner.py`, `test_portfolio_allocation_source.py`, `test_tools_registry.py`;
>   - `test_api/test_portfolio_api.py` (TB2, TB6b live) e **nuovo** `test_api/test_pac_planner_tool_api.py` (TB1);
>   - `scripts/test_runner/_backend_api.py`: solo aggiunte, `api_pac_planner_tool()` e
>     `add_test(api, "pac-planner-tool", …)` (**file condiviso**, da elencare nell'handoff).
> - TB1–TB6 coperti come da elenco sopra; il 401 di TB1 resta a `test_tools_api.py` (nessun doppione).
> - Gate: `--workers 4 --fresh-run schemas all` 1560 passed; `--workers 4 --fresh-run services all`
>   4545 + 178 passed, 0 failed; `--fresh-run api all` 730 passed / **1 failed** / 3 skipped;
>   `check-orphans` backend pulito. Mirati: `api pac-planner-tool` 5, `services portfolio-allocation-source`
>   89, `services tools-registry` 93, `schemas pac-planner` 450. `ruff` pulito; `black` pulito sui file
>   nuovi. Porta 6151 libera a fine lavoro.
> - **Nessun difetto di prodotto** nel contratto C0b.
>
> **⚠️ Fuori pista.**
> - Il rosso `test_portfolio_api.py::TestPortfolioReportEndpoint::test_report_allocation_source_authenticated_contract`
>   (`:767`) **non è di D e non nasce da C0b**. Il test fissa le chiavi di `/portfolio/report`, che a
>   `HEAD` ha sei campi in più (`acquisition_funding`, `broker_pnl_history`, `cost_history`,
>   `deposit_history`, `income_history`, `pnl_candles`, `schemas/portfolio.py:1694`): perimetro dei
>   grafici (I). Non corretto; segnalato al coordinator.
> - 11 test esistenti di `test_portfolio_allocation_source.py` oltre al punto 5 erano rotti da C0b
>   (builder FX/PMC che ora rendono solo righe, `get_currency_precision` rimosso, la nuova lettura
>   `current_distribution` nell'ordine di autorizzazione): riparati solo lato test.
> - `check-orphans` elenca 5 Vitest del frontend non registrati, tutti già a `HEAD` e di J
>   (`privacyStore*.test.ts`, `currencyFormat.test.ts`, `maskable.test.ts`, `moneyRenderSites.test.ts`).
> - Domande aperte per la review di dettaglio (non bloccanti): (1) il 422 di `asset_ids: null`
>   nasce in FastAPI prima dell'handler, quindi probabilmente senza `no-store`; (2) con
>   `asset_ids: []` il builder chiama comunque il motore del portafoglio; (3) l'ordine delle righe
>   è quello di lettura (nome, poi id), non quello di `asset_ids`: la UI mappa per id, quindi
>   l'ordine non le serve.

### Passo E — Runbook sulla copia di prod (6161)

1. Rinfrescare la copia dalla snapshot (§0) → `004_release_1_2_0_schema`.
2. `api sync` → `front build` → `server --test --port 6161 --data-dir /tmp/librefolio-r2-d-prodcopy`.
   - Prima del developer faccio le mie verifiche sulla copia: login `alfy` via API, con il cookie
     jar in `/tmp` e senza stampare la password.
   - Ogni esperimento lo dichiaro. Poi rinfresco la copia, salvo che l'esperimento sia proprio ciò
     che il developer deve vedere.
3. Il developer entra come `alfy` (§0), poi sidebar → Strumenti. Atteso: nessun banner
   «Interfacce non disponibili», nessun toast degradato, la descrizione nuova.
4. Scenari, ciascuno con lo stato atteso:

   | # | Scenario | Atteso |
   |---|---|---|
   | S1 | draft vuoto | ~~`needs_input`~~ **corretto il 24/09:** «Continua» si ferma su Liquidità con l'avviso «1 problema da correggere» (gating locale D8), senza chiamate al backend. `needs_input` non si raggiunge dalla UI: si prova in T5 e TB1 |
   | S2 | solo manuale, senza asset DB | ~~proven oracolo~~ ~~**corretto il 24/09:** `ready_incumbent` + `not_proven` quando il contributo passa da una route di funding di taglia reale. Il trasferimento si enumera al centesimo (`evaluator.py:694-716`), per cui 1000 € su due ETF a 100 e 50 dà 100 001 × 11 × 21 ≈ 2,3·10⁷ candidati, sopra il tetto di 200 000: decide SCIP.~~ **Corretto il 28/09 (D-X1):** la taglia del dominio non conta più. SCIP chiude ogni stadio → `ready_incumbent` + `optimal_proven`, fonte «stato del solver», `completed`. Nessuna copia necessaria (quantum da babel, C0b.1). **Visto il 29/09 (F6, smoke):** 1000 € su ETF a 100 e 50, target 60/40 → 6 + 8 unità, L2 = 0, U = 0; testimone «5 obiettivi della cascata chiusi all'ottimo dal solver»; risposta in 0,7 s (compute 20 ms) |
   | S2b | come S2, dominio minuscolo (5 € su ETF a 1 e 2) | ~~`ready_incumbent` + `optimal_proven` dall'oracolo; il testimone riporta 501 × 6 × 3 = 9 018 candidati~~ **Corretto il 28/09 (D-X1):** `ready_incumbent` + `optimal_proven` dal solver; il testimone dice quanti obiettivi della cascata il solver ha chiuso all'ottimo, non più quanti candidati. **Visto il 29/09 (F6, mobile 430×932):** 3 + 1 unità (3 € + 2 €), `optimal_proven`, 0,66 s (il 24/09 l'oracolo impiegava 29,5 s) |
   | S2c | PAC comune (100 € su ETF a 50 e 100) | **difetto 🔴 X1** (nota del Passo E): ~~oggi `tool_error` `execution_limit`.~~ Curato dal commit 4 (D-X1). Atteso: `ready_incumbent` + `optimal_proven` in pochi istanti, mai errore. **Visto il 29/09 (F6):** target 60/40 → 1 unità dell'ETF a 50 €, L2 = 1 700 EUR², U = 50 €, `optimal_proven`, 0,7 s |
   | S3 | copie da broker OWNER | provenance e date visibili; età in giorni dei dati non del giorno, nessuna conferma (Q-C0-3) |
   | S4 | broker non OWNER | errore esplicito. **Nota del 29/09:** le finestre di copia elencano solo i Broker di cui l'utente è proprietario, e sulla copia c'è un solo utente: dalla UI si controlla solo il testo; l'errore esplicito lo provano i test API |
   | S5 | budget sotto la quota minima più le fee | `ready_no_op` |
   | S6 | vincolo impossibile | `infeasibility_proven` (esempio del 29/09: ETF a 100 €, 100 €, «Minimo obbligatorio» 2 nella route) |
   | S7 | pesi non validi | ~~`invalid`, campo evidenziato~~ **corretto il 29/09:** «Continua» si ferma su Obiettivi con «Il totale degli obiettivi è X%, deve essere 100% (controllo)» (gating locale D8, `request.ts:197-199`). Come per S1, `invalid` non si raggiunge dalla UI: lo provano i test |
   | S8 | broker inattivo o altro caso unsupported | `unsupported`. **Nota del 29/09:** dalla UI solo con un Broker inattivo dell'utente, copiato (badge «Inattivo») e usato per un ordine (`normalize.py:342-343`); senza, lo provano i test |
   | S9 | ~~dominio oltre 200 000 candidati~~ **corretto il 28/09 (D-X1):** ricerca troncata da un limite | ~~`not_proven`, tempi in C14; scenario testimone del delta C0 §0.1~~ `ready_incumbent` o `ready_no_incumbent` + `not_proven`, stop `time_limit`. Con 30 s di budget non si raggiunge con dati piccoli: lo provano i test (budget zero) |
   | S10 | EUR + USD con FX e spread | righe FX nel piano |
   | S11 | busy e annulla | D7 |
   | S12 | modifica dopo il risultato | stale |
   | S13 | logout | draft distrutto |
   | S14 | privacy ON/OFF | come T7 |
   | S15 | viewport mobile | D4 |
   | S16 | «Copia distribuzione corrente» sui dati del developer | pesi uguali a quelli della pagina Allocazione quando lo scenario comprende tutti gli holding; asset manuale a 0 con nota; target applicato solo con «Usa come target» |
   | S17 | **(29/09, QX1-b)** arrotondamento con integrazione: un ETF a 33,335 €, contributo 100,00 €, fee a zero | `ready_incumbent` + `optimal_proven`, 3 unità, addebito 100,01 €; riga «Per eseguire il piano servono 0,01 € in più su <broker> (EUR), per gli arrotondamenti all'unità minima»; saldo finale −0,01 €; U = −0,005 €. Visto nello smoke F6. Qui si fa la review matematica di R3 |
   | S18 | **(29/09, X2)** fee col minimo: ETF a 10 €, 100 €, fee 0,19 % con minimo 1,50 € | 9 unità, addebito 90 € più fee 1,50 €, funding 91,50 €; U = 10 € (8,50 di cassa libera più 1,50 di fee); `optimal_proven`. Visto nello smoke F6 |

5. Feedback nel piano; correzioni; server spento; porte libere.

> 🟡 **2026-09-24 — Pre-verifica dell'agente sulla copia di prod eseguita. Resta aperto il runbook del
> developer (DoD E).**
>
> **Note implementazione.**
> - `front build` OK in 1 min 12 s (log `/tmp/libreFolio_d/front_build.log`). Il build ha rigenerato
>   il client, ora del **24/09 17:23**. Il suo svelte-check è al pavimento 3/41/4 e nessun warning
>   viene dal planner.
> - Copia dalla snapshot con la procedura v2 → `004_release_1_2_0_schema`. Server `--test` su 6161.
>   Health `ok`; `/tools/catalog` senza auth → 401.
> - Smoke Playwright usa-e-getta (`/tmp/libreFolio_d/smoke_pac.mjs`, chromium headless; non è un test
>   del repo). Esiti:
>   - **Hub:** `tools-hub[data-state=ready]`, `tools-catalog-degraded` 0, `tool-interface-unavailable`
>     0, card PAC con la descrizione nuova e «Backend/API 2.0.0 · UI 2.0.0». **Il difetto visto per
>     primo dal developer è chiuso.**
>   - **S1:** gating D8 (vedi tabella corretta).
>   - **S2 desktop:** 1000 € su ETF a 100 e 50, target 60/40 → `ready_incumbent`, `not_proven`,
>     `solver=reported_floating` (SCIP 10.0). Piano 6 + 8 unità, L2 = 0, U = 0; compute 26 ms.
>   - **Privacy ON sul risultato S2:** mascherati importi, quantità, fee, L2 e i valori degli stage
>     del solver. Restano in chiaro prezzi di mercato, pesi, priorità e numero di ordini.
>   - **S2b mobile** (430×932, `isMobile`): 5 € su ETF a 1 e 2 → `ready_incumbent`, `optimal_proven`,
>     `solver=not_run`. Testimone «9,018 candidates enumerated · 2212 feasible · 5 objectives».
>     **Compute 29 537 ms.** Sezioni a fisarmonica e barra di navigazione fissa corrette.
>   - **S2c desktop:** 100 € su ETF a 50 e 100 → `tool_error` **`execution_limit`**. Il pannello
>     d'errore è corretto (Riprova, Modifica, «bozza intatta»); l'esito no (X1 sotto).
>   - In tutti i flussi: **0 errori di console e 0 page error**.
> - Copia rinfrescata di nuovo dopo lo smoke: la vecchia è in
>   `/tmp/librefolio-r2-d-prodcopy.prev-20260924-174629`. Utenti = 1 (solo quello del developer).
>   Server riavviato su 6161 per la review.
>
> **⚠️ Fuori pista.**
> - **Esperimento dichiarato.** La password del developer non era più nel mio contesto. Ho creato
>   sulla copia un superuser usa-e-getta `pac_smoke` (`dev.py user --test-db create`, dopo un `list`
>   che mostrava solo l'ID 1). Il refresh lo ha eliminato.
>   - Conseguenza: S3, S4 e S16 (dati reali) non li ho pre-verificati io; li copre il runbook del
>     developer.
> - **Attesi del runbook sbagliati.** S1 e S2 promettevano stati che la UI non produce; T3 lo stesso.
>   Corretti sopra, barrati.
> - 🔴 **X1 — `execution_limit` su PAC comuni (critico, motore; scoperto dallo smoke).**
>   - Meccanismo:
>     - `planner.py:210-216` prova l'oracolo **prima** di SCIP su ogni dominio fino a 200 000
>       candidati (`oracle.py:61`). Quel tetto è una «costante interna di sicurezza»
>       (Step3 §16.8), mai tarata sul tempo.
>     - L'oracolo non ha un sotto-budget: lo ferma solo `checkpoint()`, alla soft deadline di 44 s
>       (`tools/base.py:46-50`), con `execution_limit` sull'intero job. Non c'è fallback a SCIP.
>     - Il costo misurato è ≈ 3,3 ms per candidato (S2b: 9 018 in 29,5 s), quindi il pareggio con
>       44 s cade a circa 13 000 candidati.
>     - **Ogni dominio fra circa 13 000 e 200 000 candidati fallisce.**
>     - I domini crescono in fretta per due ragioni: il funding si enumera al centesimo (100 € =
>       10 001 valori); le quantità crescono con budget/prezzo.
>   - Casi colpiti: 100 € su 2 ETF (60 006 candidati, provato); 1000 € già sul broker su 4 ETF da
>     30–100 € (≈ 1,2·10⁵, stima).
>   - ~~Non corretto: serve una decisione (vedi R5 e la domanda al developer).~~
>     **Deciso il 24/09: D-X1 (§2).** In produzione gira solo SCIP; l'oracolo resta solo nei test.
>     Esecuzione: Passo F.
>   - **⚠️ Fuori pista — l'origine del difetto è mia.**
>     - Il brief del developer metteva l'«oracle esaustivo completo di casi piccoli» fra le
>       **prove da pianificare**, cioè nei test.
>     - Lo Step 3 (§16.3, §16.5 punto 4) l'ha portato in produzione come unica fonte di prova.
>       Poi il fix 5b (Difetto A) ha tolto SCIP dal percorso quando decide l'oracolo.
>     - I documenti master hanno registrato la politica conservativa come scelta del developer:
>       `09_feedbackJobs/05_pac_allocation_tool.md:242-244`, `06_piano_sprint.md:742-748` e
>       `guida_allocazione_pac_multi_etf.md:1195-1199`.
>     - D-X1 li sostituisce. La correzione è proposta al coordinatore: sono file condivisi.
> - 🔴 **X2 — la commissione minima rende il modello SCIP infeasible (critico con D-X1; trovato il
>   24/09 verificando la fedeltà del modello compilato).**
>   - Prova: `/tmp/libreFolio_d/fee_floor_probe.py`, codice attuale, SCIP 10.0. Scenario: prezzo
>     10 €, budget 100 €, commissione 0,19% con minimo 1,50 €.
>     - Replay esatto: 9 quote fattibili (90 + 1,50 = 91,50 €).
>     - SCIP: `reported_infeasible`, stage tutti `unfinished`.
>     - Controllo: con minimo 1 € e 10%, SCIP trova 9 quote e il replay le accetta.
>   - Meccanismo, in `constraints.py:635-641`:
>     - `fee_upper = rate * notional_upper` ignora il minimo, e `big_m = fixed + fee_upper`.
>     - Se `floor > rate * notional_upper`, la riga `fee_floor` impone `fee ≥ floor − fee_upper > 0`
>       anche a ordine spento, mentre `fee_active_upper` impone `fee ≤ 0`.
>     - Il modello è quindi impossibile con l'ordine acceso e anche con l'ordine spento.
>     - Stesso difetto in `_fee_variable_upper` (`:417-423`).
>   - Quando capita: basta **una** route con minimo il cui controvalore massimo stia sotto
>     minimo/percentuale (789 € a 0,19% con minimo 1,50 €), e salta l'intero modello, perché è
>     impossibile anche a ordine spento. Due casi tipici:
>     - un PAC mensile piccolo, dove il controvalore massimo è il budget;
>     - un tetto per titolo piccolo dichiarato dall'utente, anche con un budget grande. Provato
>       (`fee_floor_probe3.py`): budget 10 000 €, tetto 20 quote da 10 € → `reported_infeasible`.
>   - Finora lo nascondeva l'oracolo sui domini piccoli. Oltre quei domini diventava «nessun piano».
>     Con D-X1 diventerebbe un «impossibile» dimostrato e sbagliato.
>   - Correzione (Passo F): limite superiore `max(floor, min(rate · notional_upper, cap))`.
>   - Il test di accordo SCIP↔oracolo non l'ha visto: nessuna fixture ha un minimo sopra
>     `rate · notional_upper`.
> - **Prova dell'esempio di QX1-a** (stesso script): 50 050 €, prezzo 100 €, 0,19% con massimo
>   18 €.
>   - SCIP: 499 quote, stage tutti `finished`, quindi con D-X1 sarebbe «ottimo».
>   - Replay esatto: anche 500 quote sono fattibili.
> - **Prova su QX1-b** (`/tmp/libreFolio_d/scip_tol_probe.py`): su un modello minimo con cassa
>   1 000, 20 000 e 200 000 SCIP non ha sfruttato la tolleranza relativa. Il rischio resta teorico:
>   non è stato osservato.
> - **Voci UI nuove per R7:**
>   - (a) il testimone raggruppa le migliaia per `#` ma non per `{feasible}` («9,018» contro
>     «2212»): basta `{feasible, number}` nelle 4 lingue;
>   - (b) i valori floating degli stage si stampano con tutte le cifre
>     («≈-0.0000000000017705302566 € EUR» per U).
> - Artefatti dello smoke: gli screenshot a pagina intera catturano l'header e la barra fissi a metà
>   pagina, e un resize desktop→mobile fotografa la transizione della sidebar. Non sono difetti; il
>   flusso mobile ora parte già con il viewport mobile.

### Passo F — SCIP unico motore in produzione (D-X1, X2, QX1-a, QX1-b) ⏳ in esecuzione

> Stato al 24/09 sera: la decisione, i difetti e le prove sono registrati; **nessun file di codice
> è stato toccato**. Il developer ha chiesto di fermarsi.
>
> Stato al 25/09 mattina:
> - ✅ checkpoint committato, HEAD `0210f9848` (§8);
> - ✅ testo di correzione dei tre master inviato al coordinator. Nel 05 il passaggio superato va
>   da `:242` a `:246`: anche «SCIP è candidato additivo approvato, non ancora installato o
>   provato» non vale più;
> - ✅ il developer conferma F0 → F6 e l'ordine dei commit (scelta «Confermo F0 → F6 in
>   quest'ordine»);
> - ✅ QX1-b deciso: il piano esce con la nota di quanto aggiungere per gli arrotondamenti, entro
>   `N` unità minime per cassa (§2). X3 respinta. Il lavoro diventa il passo **F2c**, ed è un
>   commit in più.
> - ✅ commit 1 (F0) e 2 (X2) committati alle 11:25: `856c2193f` → `f92e5560b` (§8). Si prosegue
>   con QX1-a.
> - ✅ commit 3 (QX1-a) committato alle 11:58: `6061affd7`, 5 file, +315/−69, sopra `f92e5560b`
>   (§8).
> - ⏸️ **Pausa alle 12:59**: il developer spegne la macchina. **Il commit 4 (X1/D-X1) non è
>   iniziato**: nessun file di codice o di test toccato, nessun test-author al lavoro. Porte 6151 e
>   6161 libere. L'unico file sporco è questo piano.
>
>   Alla ripartenza:
>   1. verificare HEAD `6061affd7`, che l'unico file sporco sia questo piano, lo stage vuoto e le
>      porte libere (`lsof`). `/tmp` si svuota al riavvio; la cartella della lane
>      `/tmp/librefolio-r2-d` la ricrea il runner;
>   2. inventario in sola lettura di ciò che D-X1 rende obsoleto, con la test-triage prima di
>      togliere (principio del developer, sotto):
>      - i test del percorso «prima l'oracolo» del planner;
>      - `ExhaustiveOracleWitness` e `SolverNotRunEvidence` nelle unioni di produzione;
>      - i rami dell'oracolo nel report e in `ProofPanel`, e le loro chiavi i18n;
>   3. misurare quante volte SCIP e il replay chiamano il `Checkpoint` (condizione del
>      coordinator, sotto);
>   4. test-author, test rossi:
>      - il caso X1, 100 € su 2 ETF (60 006 candidati, `:1171`): il conteggio deterministico delle
>        chiamate al `Checkpoint` prova che il planner di produzione non enumera;
>      - SCIP infeasible → `ready_infeasible` + `completed`;
>   5. poi F1 → F2 → F3 → F5.
> - ▶️ **Ripresa il 28/09** (coordinator), dopo il riavvio del Mac:
>   1. ✅ verifica (10:20): HEAD `6061affd7`, unico file sporco questo piano (+39/−3), stage vuoto,
>      `git diff --check` pulito, porte 6151 e 6161 libere;
>   2. ✅ inventario in sola lettura, con la test-triage: la tabella è in F4, «Inventario D-X1»;
>   3. ✅ misura del `Checkpoint`: la tabella è in F4, «Misura del Checkpoint»;
>   4. ✅ domanda al developer (10:58) sulle quattro forme di prova senza uso già prima di D-X1
>      (`deterministic_conflict`, `gap_bounded`, `score_lattice_closure`, `describe_conclusion`).
>      Risposta: «se non sono più nei piani e sono stati prodotti per un piano precedente e ormai
>      superato è inutile lasciarli, eliminali». La condizione è verificata: le citano solo i
>      design di prima di D-X1 (MathematicalCore §19, UiTarget, Policies, le bozze, il dossier
>      DBT-4/6/7), e D-X1 ha tre sole regole di esito, tutte da SCIP. Quindi si tolgono nel
>      commit 4, con UI, i18n e test;
>   5. ✅ test rossi (test-author, 28/09), tutti in `test_pac_planner_planner.py`, ciascuno rosso
>      per la ragione giusta sul codice di oggi (`services pac-planner-service <nome>`, «1 failed,
>      34 deselected»):
>      - `test_x1_planner_does_not_enumerate_a_large_domain`: prima verifica che il dominio
>        (60 006) superi il budget di 2 000 chiamate, poi il `Checkpoint` che conta scatta a 2 001
>        dentro `oracle.py:195 run_exhaustive_oracle` (log `/tmp/libreFolio_d_x1_red_1.log`);
>      - `test_forced_infeasible_returns_ready_infeasible_not_raise`, riscritto sul posto: stato,
>        esito e `completed` passano già; rosso su `proof_source` `exhaustive_oracle` ≠
>        `solver_status` e sul testimone (`red_2.log`);
>      - `test_exhaustive_oracle_is_test_only`, nuovo, strutturale: rosso con tre righe, il modulo
>        risolve ancora, `planner.py:88` e `proof.py:53` lo importano (`red_3.log`).
>
>      Ruff e black puliti.
>      > **⚠️ Fuori pista**: test-author, forzando la via SCIP con uno script usa e getta fuori
>      > dal repo, ha visto che oggi l'infeasible esce `ready_no_incumbent` + `time_limit`: in
>      > `planner_report.py:908-911` ogni stadio non finito diventa `time_limit`. È il difetto che
>      > F1/F2 curano, dando allo stadio lo stato `infeasible`, che non è «non finito». Sulla stessa
>      > via forzata, il caso X1 ha già tutto il resto giusto (5 stadi pubblicati finiti, una quota
>      > per ETF, 189 chiamate). Gli stadi `tie:*` non sono nell'evidence pubblicata, quindi «ogni
>      > stadio finito» sul filo copre i 5 obiettivi. Il test infeasible usa
>      > `_forced_min_scenario_view()` del blocco «Item 7»: resta anche quando quel blocco si pulisce.
>   6. ✅ F1 → F2 → F3 → F5 (28/09, note nei passi), con il lotto di test di F4 e i gate: in F4,
>      «Lotto del commit 4». F6 viene dopo il commit.
>   7. ✅ commit 4 committato dal developer alle 12:51: `b48b3cec9`, 31 file, sopra `6061affd7`
>      (§8).
>   8. ✅ allineamento a `dev_release2`, deciso dal developer per subito dopo il commit 4 e prima
>      del commit 5. Merge `d32f27c24` alle 13:51, genitori `b48b3cec9` e `7c61dd924` (J, A, K e
>      il CHANGELOG di K), albero `b5f2dda8`.
>      - Nessun conflitto. In comune ci sono solo i 4 cataloghi (unione esatta, 4102 chiavi) e
>        `moneyRenderSites.test.ts`.
>      - Nessuna migrazione e nessuna dipendenza nuova; i file Python di D sono identici a
>        `b48b3cec9`.
>      - Dal target entra `AssetType.CROWDFUND_REAL_ESTATE`. Per il PAC è un codice come gli altri:
>        `plannerAssetClass` abbassa solo le maiuscole, `PlannerCode` lo accetta, e nessun ramo
>        del PAC elenca i tipi.
>
>      Gate sulla nuova base (13:58-14:04), lane 6151, un comando alla volta. Script
>      `/tmp/libreFolio_d_gate_merge.sh`, riepilogo in `.summary`, log in
>      `/tmp/libreFolio_d_merge_*.log`:
>      - `api sync`: nessun file tracciato cambiato;
>      - `front check`: 3 errori e 41 avvisi, negli stessi 4 file di prima; nessuno nel PAC;
>      - Vitest `front-utility core-unit` (98 file, 2647 test) e `component-unit` (85 file, 2113
>        test), verdi. Dentro ci sono `moneyRenderSites`, `allocationSource`, `ToolsHub` e
>        `ToolHost`;
>      - services: core 152, evaluator 139, oracle 20, policies 40, solver 19, proof 30,
>        wire-numbers 39, report 17, service 25, tools-registry 93;
>      - schemas: pac-planner 450, tools 271;
>      - api: pac-planner-tool 5, tools 7. Conteggi uguali a prima del merge. La build del
>        frontend, vecchia dopo il merge, l'ha rifatta l'avvio del backend di `api pac-planner-tool`
>        (`frontend/build` delle 14:03:13), dentro i 120 s del runner;
>      - `i18n audit`: 4102 chiavi, tutte complete. Le voci PAC fra le inutilizzate sono le stesse
>        di prima: 3 «not verified» per prefisso dinamico e 168 del P1 (decisione a);
>      - ruff pulito sui 31 file Python di D.
>
>      > **⚠️ Fuori pista**: due rossi, entrambi precedenti al merge e presenti anche su
>      > `dev_release2`. Nessuno viene dal commit 4.
>      > - `api portfolio`: 51 passed e 1 failed,
>      >   `test_report_allocation_source_authenticated_contract` (`test_portfolio_api.py:593`,
>      >   assert a `:767`). Il pin sulle chiavi di primo livello di `/report`, scritto l'11/09 da
>      >   `8273335ff`, non conta le 6 sezioni opzionali che il P&L (`8ed7a0f0d`, 18/09) ha aggiunto
>      >   a `PortfolioReportResponse`, serializzate a `null`. Test, schema e rotta sono identici
>      >   fra `f1047f766` e `7c61dd924`, quindi il rosso c'è anche lì. Una sonda pura
>      >   (`/tmp/libreFolio_d_legacy_pins_probe.py`) mostra che i pin annidati su sorgente, asset e
>      >   quote coincidono con lo schema di oggi. È il test che la S10 di I sistema («riattiva i
>      >   pin annidati di `:593`»): D non lo tocca.
>      > - black su `test_portfolio_api.py`: 8 blocchi da riformattare (`:1675-2314`), gli stessi 8
>      >   a `f1047f766`. Vengono dal PAC v1 (per esempio `0088748a8`, 18/09), non dal checkpoint.
>      >   Il file è condiviso con I, quindi non lo riformatto ora. Gli altri 28 file sono puliti.
>   9. ✅ il coordinator accetta il gate (28/09). Le sue risposte:
>      - **le 168 chiavi del P1 restano**, per decisione (a) del developer: «Le chiavi verranno
>        decretate morte solo alla vera fine del round di sviluppo». Il principio del 25/09 vale
>        per test e codice, non per le chiavi i18n. Vanno nella lista di fine round, con le 22
>        chiavi del tour di J. Lo stesso vale per le 2 chiavi che il commit 5 lascia senza uso
>        (F2c, passo 6);
>      - `:593` e il black di `test_portfolio_api.py` sono voci d'integrazione del coordinator. Se
>        la S10 di I entra prima, D non fa niente;
>      - via al commit 5 (QX1-b): prima i test rossi del test-author, poi `CHECKPOINT READY` e
>        `FROZEN`.
>   10. ✅ 2026-09-28 commit 5 (QX1-b, F2c): cura e gate verdi. Il disegno e i passi sono in F2c,
>       i test e gli esiti in F4 («cura del commit 5»). `CHECKPOINT READY` al coordinator, poi
>       `FROZEN` fino al commit del developer.
  11. ✅ risposte del coordinator (28/09) a ciò che gli ho mandato sul commit 5:
      - `contract_version` resta `2.0.0`;
      - le 2 chiavi che restano senza uso vanno nella lista di fine round;
      - la chiave nuova passa da `dev.py i18n`, e il totale sale a 4103;
      - il test di componente di `StateNotice` lo registro io, ma solo con la riga del percorso
        in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`). La riga va
        vicino a `ToolsHub` e `ToolHost`, non in fondo: Risk ha aggiunto la sua intorno a
        `:211`. Il `desc` di `component-unit` **non si tocca**, perché anche Risk l'ha
        riscritto: la frase la mette il coordinator nella lista d'integrazione;
      - nel handoff vanno i due fingerprint nuovi dello schema completo. Il coordinator ha già
        in lista l'`api sync` dopo l'integrazione.
>
> **Principio del developer** (25/09 alle 11:54, per tutte le lane, via coordinator):
> - il prodotto, per ora, va bene così com'è;
> - i test provano il prodotto di oggi, non i passi intermedi da cui è passato;
> - un test vecchio, che prova un comportamento non più nel prodotto, si toglie. Si toglie anche il
>   codice di prodotto rimasto senza uso, dentro il perimetro della lane, con il suo test di
>   regressione quando serve. Prima di togliere si attribuisce con la test-triage: un test vecchio
>   non va confuso con un difetto;
> - le domande al developer si fanno in italiano.
>
> **Condizioni del coordinator** (24/09 alle 18:35, ribadite il 25/09 alle 09:09):
> - X1 e X2 sono **gate d'integrazione**: la UI v2 li espone, quindi il ramo non entra in
>   `dev_release2` finché restano aperti. X1 non è in nessuna release (`v1.1.0` non contiene
>   `pac_allocator`), quindi niente hotfix.
> - Prima si fa il **checkpoint** dei 106 file (handoff del 25/09, §8). Il Passo F entra sopra, in
>   commit separati.
> - Ogni cura ha il suo commit e un test **rosso prima della cura**, scritto da test-author.
> - Il test di X1 è deterministico, senza misurare il tempo. Con D-X1 deve provare che il planner di
>   produzione non enumera. Proposta: un `Checkpoint` iniettato che conta le chiamate (l'oracolo lo
>   chiama per ogni candidato) e un dominio come S2c (60 006 candidati) che SCIP risolve sotto la
>   soglia, più il test strutturale di F3. Prima va misurato quante volte SCIP e il replay chiamano il
>   checkpoint.
> - Il testo di correzione dei master condivisi (05:242-244, 06:742-748, guida:1195-1199) va al
>   coordinator, che lo applica.
> - Prima di eseguire, il developer conferma F0 → F6 e risponde a QX1-b.
>
> Ordine dei commit, perché ogni commit intermedio resti corretto:
> 1. `docs(pac)`: D-X1 e QX1-b nei normativi (F0);
> 2. X2, limite superiore della fee con il minimo (F2b, prima parte), con il suo test rosso;
> 3. QX1-a, tetto esatto (F2b, seconda parte); `test_fee_epigraph_cap_oblivious_regression` si inverte;
> 4. X1/D-X1: SCIP unico, prova del solver, oracolo nei test, testimone UI (F1-F3, F5), con il test
>    deterministico;
> 5. QX1-b (F2c, aggiunto il 25/09): la nota di quanto aggiungere per gli arrotondamenti. Il test
>    rosso è `3 × 33,335` su 100,00 €: dopo il commit 4 dà «nessun piano», dopo il 5 dà 3 quote e
>    «servono 0,01 € in più».

Ordine, con i documenti prima del codice (regola del developer):

- **F0 — documenti.** ✅ 2026-09-25
  - I normativi di `13_pacAllocator` ricevono una nota datata che li sostituisce: MathematicalCore,
    TargetDesign, Architecture, Policies, UiTarget, `review/PAC_ALLOCATOR_REVIEW_DOSSIER.md`,
    `implementation/README.md`.
  - I piani storici (Step3 §16.3 e 5b) ricevono una nota in avanti di una riga.
  - Per i master condivisi (05:242-244, 06:742-748, guida:1195-1199) si manda la proposta al
    coordinatore.

  > **Note implementazione** (2026-09-25):
  > - **Note in testa.** Ognuno dei cinque design autorevoli ha una nota «Aggiornamento del
  >   2026-09-25», che prevale sul testo dove i due sono in conflitto. Dice tre cose:
  >   - D-X1 e le tre regole di esito;
  >   - l'oracolo solo nei test;
  >   - QX1-b, con la soglia `N`.
  >
  >   Elenca anche le sezioni toccate.
  > - **Note in linea**, dove un lettore arriva da un link:
  >   - MathematicalCore §6.2 (ledger, QX1-b), §19, §20, §22 (la review matematica di QX1-b va
  >     in R3);
  >   - TargetDesign §2 (dopo il mermaid) e §9.3;
  >   - Policies §12.7 e §12.8;
  >   - Architecture §2, §12 e §14;
  >   - UiTarget §20.18. La UiTarget ha un secondo blocco di erratum in testa, accanto a quello
  >     del 24/09, e dice anche che l'importo da aggiungere va mascherato con la privacy.
  > - **Dossier** (in inglese): nota in testa, più una riga in §5.5 e in §6.4.
  >   - §6.4 sosteneva «mai falsa infeasibility»: X2 lo smentisce.
  >   - DBT-5 si chiude col Passo F.
  > - **README di `implementation/`:** blocco del 25/09 (`0210f9848`).
  > - **Step3:** una nota in avanti in §16.3 e in «Difetto A». Il «5b» del piano è quella cura:
  >   SCIP fuori dal percorso quando decide l'oracolo.
  > - **Nome della fonte di prova nuova: `solver_status`.** È scelto qui per coerenza fra i
  >   documenti, e lo schema lo userà al passo F1.
  > - **Errore oltre la soglia di QX1-b:** errore Tool, non un risultato. È scritto nella nota
  >   dell'Architecture, coerente con la sua §14 («Tool error, non result success-shaped»).
  > - **Master condivisi:** il testo del mattino e l'aggiunta su QX1-b sono al coordinator, che
  >   li applica.
  >   - I tre testi su D-X1 sono applicati e committati su `dev_release2`. Verificato in sola
  >     lettura, con `git show`, a `3aa33ff78`: 05:249, 06:750, guida:1201. Il link del 05 a
  >     questo piano resta sospeso finché il ramo non è integrato: sta nel journal, che MkDocs non
  >     costruisce, e il coordinator lo accetta.
  >   - Le aggiunte su QX1-b per gli stessi tre punti sono committate dal coordinator su
  >     `dev_release2`: `268fe835d` «docs(journal): record the QX1-b rounding rule», 25/09 alle
  >     11:31; 3 file, +11/−5. Verificato in sola lettura con `git show --stat`.
  > - Evidenza: `git diff --check` pulito; 9 file di documenti, nessun file di codice.
  >
  > **⚠️ Fuori pista**:
  > - Nel 05 il passaggio superato va da `:242` a `:246`, non fino a `:244` (detto al coordinator).
  > - Rileggendo Difetto A: uno stage SCIP infeasible è per forza `unfinished`, mentre
  >   `ready_infeasible` richiede `completed`. È il vincolo che F1 deve sciogliere.
- **F1 — schema.** ✅ 2026-09-28
  - Prova di ottimo e di impossibilità con una fonte «solver».
  - Lo stage infeasible diventa uno stato completato, così `ready_infeasible` è raggiungibile da
    SCIP.
  - Si rimuovono `ExhaustiveOracleWitness` e `SolverNotRunEvidence` dalle union di produzione.

  > **Note implementazione** (2026-09-28, `backend/app/schemas/pac_allocator.py`):
  > - Fonte unica `solver_status`, col testimone `SolverStatusWitness(kind="solver_status",
  >   objective_codes)`: almeno un codice, senza doppioni. `OptimalProvenProof` lo porta con
  >   `tie_break_closed: True`; `InfeasibilityProvenProof` lo porta con un solo codice, il primo
  >   obiettivo. `ReadyPlanProof` è `OptimalProvenProof | NotProvenProof`.
  > - `SolverStageEvidence.status` accetta `infeasible`, solo con ordinale 1, scope `global` e
  >   nessuna osservazione (primal, duale e gap `None`, come misurato in F4). In
  >   `ReportedFloatingSolverEvidence` uno stage infeasible è l'unico stage.
  > - `_validate_solver_status_proof`, chiamato dalle due basi dei risultati pronti:
  >   - un ottimo richiede ogni stage pubblicato `finished` e i codici uguali a quelli del
  >     testimone;
  >   - un'impossibilità richiede lo stage `infeasible` e il suo codice nel testimone;
  >   - uno stage `infeasible` con qualunque altra prova è un errore.
  > - Tolti: `SolverNotRunReasonCode`, `SolverNotRunEvidence`, l'alias `PlannerSolverEvidence`,
  >   `ExhaustiveOracleWitness`, `ScoreLatticeClosureWitness`, `DeterministicConflictWitness`, gli
  >   alias `OptimalityWitness` e `InfeasibilityWitness`, `BoundedObjectiveStage`,
  >   `GapBoundedProof` e `_validate_gap_proof`.
  > - `_validate_stop_evidence` ha un messaggio nuovo («Completed stops require no unfinished
  >   stage; limit stops require an unfinished stage»). Nessun test confronta quel testo.
  > - `SellIrreducibilityCheck.closure_kind` resta com'è, per R8 (inventario in F4).
  >
  > **⚠️ Fuori pista**: black sull'intero file ha tolto 117 righe vuote che c'erano già in HEAD,
  > avanzate dalla rimozione di P1 (`ef321160f`). Sono solo spazi. Lo stesso in `models.py`, dove
  > cambiava un commento: 46 righe vuote.
- **F2 — motore.** ✅ 2026-09-28
  - `planner.py` usa solo SCIP.
  - `proof.py` promuove gli esiti di SCIP.
  - Si corregge la mappa di stato in `solver.py` e il suo commento «absolute» (`:91`).
  - Si aggiorna la proiezione in `planner_report.py`.

  > **Note implementazione** (2026-09-28):
  > - `solver.py`: se il primo stage torna `infeasible`, lo stage è `infeasible`, l'esito
  >   `reported_infeasible` e la cascata si ferma, senza righe `not_reached`. Uno stage successivo
  >   che torna infeasible resta un'anomalia, non terminato, come prima. Corretti il commento di
  >   `STAGE_PIN_RELATIVE_SLACK` (la `feastol` di SCIP è relativa: sorgenti di SCIP 10 e
  >   `files/x1-probes/scip_tol_probe*.log`), quello di `DEFAULT_SOLVER_TIME_BUDGET_SECONDS` e i
  >   docstring.
  > - `planner.py`: una sola via, compile → SCIP, senza soglia. `_Search(candidate, solver)`.
  >   `_conclude` chiama `proof.conclude_with_solver`; `ready_infeasible` nasce solo da una
  >   conclusione d'impossibilità, tutto il resto senza piano è `ready_no_incumbent` con
  >   `not_proven`. `stop_reason` ed evidenza vengono sempre dal solver. Il docstring del modulo è
  >   riscritto, ed è sparito il testo P1 superato che c'era ancora.
  > - `proof.py` riscritto, senza import dell'oracolo:
  >   - tre conclusioni, con il testimone sigillato `SolverStatusWitnessFacts`;
  >   - `conclude_with_solver` dà l'ottimo solo se ogni stage, spareggi compresi, ha chiuso
  >     `optimal` senza anomalia e il piano pubblicato è quello di SCIP;
  >   - dà l'impossibilità solo con un unico stage: ordinale 1, globale, `infeasible`, niente
  >     pubblicato;
  >   - negli altri casi dà `not_proven`;
  >   - alza `ProofForgeryError` se una prova nominerebbe obiettivi diversi da quelli eseguiti;
  >   - tolti `ExhaustiveOracleWitnessFacts`, `DeterministicConflictWitnessFacts`,
  >     `conclude_with_oracle`, `conclude_without_proof`, `conclude_infeasible_from_conflicts`,
  >     `describe_conclusion` e `_witness_from_oracle`.
  > - `planner_report.py`: solo docstring. `build_stop_reason` dice che uno stage infeasible
  >   chiude una ricerca `completed`, e la misura del 22/09 è datata rispetto a D-X1.
  > - Docstring riallineati in `tool_plugins/pac_allocator.py`, `evaluator.py`, `models.py` e
  >   `objectives.py`.
  > - Evidenza: ruff e black puliti sui 10 file backend. L'import di `proof`, `planner` e del
  >   plugin passa; `find_spec` del vecchio percorso dell'oracolo dà `None`.
  >
  > **⚠️ Fuori pista**:
  > - **Il rifiuto del replay resta raggiungibile fino al commit 5.** Se SCIP chiude ogni stage
  >   `optimal` e il replay Decimal rifiuta il piano (`3 × 33,335` su 100,00 €), il risultato è
  >   `ready_no_incumbent`, `not_proven`, `completed`, con gli stage finiti. La UI non deve
  >   contraddirlo: F5 aggiorna `proof.floatingFinished` e aggiunge `states.noIncumbent.rejected`.
  > - **Difetto latente, già presente prima di D-X1: proposto come R10, non curato qui.**
  >   L'evidenza pubblicata toglie gli stage `tie:*`, ma `build_stop_reason` legge gli stage
  >   interni. Se il budget finisce durante gli spareggi, dopo che i 5 obiettivi sono finiti, lo
  >   stop è `time_limit` ma l'evidenza non ha stage non finiti. `_validate_stop_evidence` allora
  >   alza, e il Tool va in errore. Serve molto tempo sugli obiettivi (ben oltre 80 decisioni,
  >   che oggi chiudono in 7-8 s su 30), quindi la finestra è stretta. Curarlo vuol dire decidere
  >   come mostrare sul filo uno spareggio troncato: è una scelta di design, non un fix.
  > - Con la via unica, `_Search.candidate` ripete `solver.candidate`. L'ho lasciato per
  >   leggibilità dei punti di chiamata.
- **F2b — fedeltà delle commissioni.**
  - X2 (commit 2): limite superiore `max(floor, rate · notional_upper)` nel fee epigraph e in
    `_fee_variable_upper`. Il tetto resta fuori fino al commit 3 (vedi il fuori pista sotto).
    ✅ 2026-09-25
  - QX1-a (commit 3): il tetto esatto con una binaria `capped` per ogni route che ha un tetto, con
    Big-M derivato dai limiti della route. Solo allora il limite diventa
    `max(floor, min(rate · notional_upper, cap))`. ✅ 2026-09-25
  - `test_fee_epigraph_cap_oblivious_regression` si inverte al commit 3. ✅ 2026-09-25 (ora
    `test_fee_epigraph_cap_exact`)

  > **Note implementazione** (2026-09-25, QX1-a):
  > - **Cura** (`constraints.py`):
  >   - un solo predicato, `_fee_cap_excess`, restituisce `rate · notional_upper − cap` se il
  >     tetto può mordere dentro la route, altrimenti `None`;
  >   - lo usano entrambe le metà, così non possono divergere:
  >     - `add_fee_epigraph_constraints` aggiunge la binaria `fee_capped` e le righe
  >       `fee_capped_active` (`capped ≤ active`) e `fee_cap` (`fee ≥ (fixed + cap) · capped`);
  >       inoltre, sulla riga `fee_linear`, toglie `cap_excess · capped`;
  >     - `_fee_clamp_upper` abbassa il limite al tetto, e `_fee_variable_upper` lo segue.
  > - **Perché è esatta.**
  >   - Con `capped = 0` la fee sta in `[fixed + max(floor, rate · N), fixed + cap]`: l'intervallo
  >     non è vuoto solo se `rate · N ≤ cap`.
  >   - Con `capped = 1` la fee vale esattamente `fixed + cap`.
  >   - A ordine spento tutte le righe basse sono ≤ 0.
  >   - Il minimo fra i due rami è `calculate_fee` per ogni nozionale.
  >   - Gli stadi prima di `explicit_cost` (`fixed_l2`, `shortfall`, `route_priority`) non
  >     guadagnano mai da una fee più alta, quindi il margine sopra il minimo è innocuo.
  > - **Docstring riscritti:** il modulo `constraints.py` (paragrafi Fee e Fee bound, con X2 e
  >   QX1-a), `_fee_clamp_upper`, `add_fee_epigraph_constraints` (le righe e la dimostrazione) e
  >   il `compiler.py` (da «limitazione nota» a «fedeltà della fee», con i tre test che la
  >   bloccano; l'ultima frase sull'escalation resta).
  > - **Test rossi** (test-author), provati rossi sul codice di prima per il motivo giusto:
  >   - `test_fee_epigraph_cap_boundary`, in `test_pac_planner_policies.py`, 3 forme: tetto
  >     1,50 €; minimo 1,20 € + tetto; 0,50 € fisso + tetto. Rosso a `:666`, il pin di 9 quote a
  >     `fixed + cap`: `'infeasible' == 'optimal'`;
  >   - `test_fee_epigraph_cap_exact`, che sostituisce la vecchia regressione: rosso a `:692`,
  >     `10.0 == 2.0`;
  >   - quattro fixture nel gate SCIP↔oracolo (`test_pac_planner_solver.py`), tutte in centesimi
  >     interi, quindi senza pareggi:
  >     - `fee_cap_binds`, rosso 8 contro 9;
  >     - `fee_fixed_floor_cap`, rosso 8 contro 9;
  >     - `fee_cap_binds_qx1a_example` (50 050 €), rosso 499 contro 500;
  >     - il controllo `fee_cap_never_binds`, verde anche prima.
  >   - I docstring del modulo di test del solver e di `_proportional_fee_no_cap_scenario` non
  >     escludono più dal gate i tetti che mordono.
  > - **Verde dopo la cura** (lane 6151, `/tmp/librefolio-r2-d`), un comando alla volta:
  >   - `pac-planner-policies` 40, `-solver` 19;
  >   - `-core` 152, `-evaluator` 139, `-oracle` 20, `-proof` 33, `-wire-numbers` 39,
  >     `-report` 16, `-service` 33: tutti passed, 491 in tutto.
  > - **Sonda di mutazione** (usa-e-getta, `files/qx1a-probes/cure_mutations.py`, nella cartella
  >   di sessione). Si rompe un pezzo alla volta:
  >   - M1, senza la riga `fee_cap`: il ramo del tetto diventa ottimista, e il test di confine è
  >     rosso a `:662` e `:668`;
  >   - M2, senza lo sgravio sulla riga lineare: è la lezione di X2. Il confine è rosso a `:666`,
  >     `cap_exact` a `:689`, e il gate compra 1 quota contro 9, e 94 contro 500;
  >   - M3, limite senza tetto, e M4, senza `capped ≤ active`: tutto verde, come previsto.
  >     Stringono il modello, ma non cambiano il comportamento:
  >     - M3 rafforza il rilassamento e restringe il limite delle unità della fee registrata;
  >     - M4 è già implicata quando `fixed + cap > 0`.
  > - `ruff check` e `black --check` sui 4 file: puliti. `git diff --check`: pulito.
  >
  > **⚠️ Fuori pista**:
  > - **La binaria solo dove il tetto può mordere, non su ogni route che ha un tetto** (il piano
  >   diceva «per ogni route che ha un tetto»). Dove `rate · notional_upper ≤ cap`, la riga lineare
  >   è già esatta: una binaria in più non cambierebbe niente, e costerebbe un ramo al solver.
  > - **La binaria vive solo nel modello**, come le unità di `_posted_units_term`, e non entra in
  >   `CompiledVariables`: nessun obiettivo, nessuna soluzione iniettata e nessun test la legge.

  > **Note implementazione** (2026-09-25, X2):
  > - **Cura.** Un solo helper, `_fee_clamp_upper` (`constraints.py`), calcola
  >   `max(floor, rate · notional_upper)`. Lo usano i due siti:
  >   - il Big-M del fee epigraph;
  >   - `_fee_variable_upper`, che limita le unità della fee registrata nel ledger.
  > - **Docstring.** Il modulo `constraints.py` e il `compiler.py` dicevano «mai falsa
  >   infeasibility». Adesso dicono:
  >   - il minimo sta nel limite (X2);
  >   - il tetto no, e dove morde può escludere piani che il replay accetta (QX1-a, aperto,
  >     con l'esempio 50 050 € → 500 quote contro 499).
  > - **Test rossi** (test-author), provati rossi sul codice di prima, per il motivo giusto:
  >   - `test_fee_epigraph_floor_above_linear_upper_boundary`, in `test_pac_planner_policies.py`.
  >     Tre forme: 0,19 % con minimo 1,50 €; minimo fisso di 2 € a tasso zero; 0,19 % con minimo
  >     1,50 € più 1 € fisso. Rosso: `assert 'infeasible' == 'optimal'` a ordine spento (`:582`).
  >   - tre fixture nel gate d'accordo SCIP↔oracolo (`test_pac_planner_solver.py`):
  >     `fee_floor_above_linear_upper`, `small_route_cap_fee_floor`, `flat_minimum_fee`. Tutte in
  >     centesimi interi, quindi senza pareggi. Rosso: `assert 'reported_infeasible' ==
  >     'incumbent'` (`:180`).
  > - **Verde dopo la cura** (lane 6151, `/tmp/librefolio-r2-d`), un comando alla volta:
  >   - `…dev.py test --test-port 6151 --data-dir /tmp/librefolio-r2-d services
  >     pac-planner-policies` → 37 passed;
  >   - `… services pac-planner-solver` → 15 passed;
  >   - `pac-planner-core` 152, `-evaluator` 139, `-oracle` 20, `-proof` 33, `-wire-numbers` 39,
  >     `-report` 16, `-service` 33: tutti passed.
  > - **Secondo sito coperto.** Una sonda usa-e-getta (`files/x2-probes/second_site_mutation.py`,
  >   nella cartella di sessione) rimette il vecchio limite solo in `_fee_variable_upper`. Le tre
  >   forme tornano rosse a `:585`, cioè al pin di 9 quote. Quindi il test copre entrambi i siti.
  > - `ruff check` e `black --check` sui 4 file: puliti. `git diff --check`: pulito.
  >
  > **⚠️ Fuori pista**:
  > - **La formula del piano andava divisa in due commit.** `max(floor, min(rate · N_up, cap))`
  >   è giusta solo insieme alla binaria `capped` di QX1-a. Il motivo:
  >   - finché resta la riga lineare `fee ≥ fixed + rate · N − big_m (1 − active)`, mettere il tetto
  >     nel limite superiore rende infeasible ogni `N` con `rate · N > cap`;
  >   - nell'esempio di QX1-a (0,19 % di 100 €/quota, tetto 18 €) il modello arriverebbe al
  >     massimo a 94 quote, molto peggio delle 499 di oggi.
  >
  >   Quindi il commit 2 mette solo il minimo, e il tetto entra al commit 3 con la sua binaria.
  > - Il docstring di `test_fee_epigraph_cap_oblivious_regression` dice ancora «can never cause
  >   false infeasibility». È falso già oggi, per QX1-a. Non l'ho toccato: il test è del
  >   test-author, e al commit 3 si inverte e si riscrive comunque.
- **F2c — arrotondamenti oltre la cassa (QX1-b, deciso il 25/09).** ✅ 2026-09-28 (commit 5;
  esiti in F4, «cura del commit 5»)
  - Il replay classifica il rifiuto. Se l'unica violazione è un deficit di cassa entro
    `N × unità minima` per cassa, il piano esce con l'importo da aggiungere per ogni cassa.
    Altrimenti è un errore (§2).
  - Schema: un campo nel risultato pronto con le casse da integrare (broker, valuta, importo, `N`,
    e il suo valore nella valuta di valutazione: passo 3).
  - Report e UI: la nota per cassa; i18n via `dev.py i18n` nelle 4 lingue.
  - Il deficit è un dato personale, quindi passa dalla maschera della privacy.
  - Dal commit 4 (28/09): il commit 5 rende irraggiungibile il rifiuto del replay per un solo
    deficit di cassa entro `N`, quindi toglie anche il ramo che la UI gli dedica al commit 4
    (`proof.floatingFinished` riscritto e `states.noIncumbent.rejected`), se non resta un altro
    rifiuto che lo usi.

  **Disegno del commit 5** (28/09, analisi in sola lettura sul codice di `d32f27c24`), in ordine:
  1. **Classificatore** (`evaluator.py`, tipo in `models.py`):
     `rounding_top_ups(scenario, evaluation)` restituisce una tupla di
     `ExactRoundingTopUp(broker_id, currency, amount, rounded_postings, valuation_amount)`,
     nell'ordine dei ledger.
     - Piano esatto → tupla vuota.
     - Candidato fuori contratto (`candidate_valid=False`) → `ExactReplayRejectedError`, sottoclasse
       di `ExactEvaluatorError`.
     - Violazioni ammesse: solo `SPENDABLE_CASH_NONNEGATIVE`, `FX_SOURCE_CASH`,
       `NO_SHORT_OR_LEVERAGE` e `ROUNDING_BOUND`, con almeno una `SPENDABLE_CASH_NONNEGATIVE`.
       Qualunque altra → errore.
     - Per ogni cassa con saldo finale negativo: `D = −saldo`. `N` conta le registrazioni della
       cassa con un `quantum`: l'acquisto di ogni ordine, la commissione quando non è zero, il
       credito FX. Sono le stesse che formano `rounding_bound` (`evaluator.py:2268-2279`); una
       commissione esatta a zero non si registra (`_append_rounded_posting`, `:1563`). Errore se
       `N = 0` o `D > N × unità minima`.
     - Una quantità finale negativa → errore: `NO_SHORT_OR_LEVERAGE` (`:2711-2720`) si spiega solo
       con le casse.
     - `FX_SOURCE_CASH` vale il saldo della cassa sorgente (`:2463`): se è violato, quella cassa è
       già fra le integrazioni.
     - `ROUNDING_BOUND` violato: accettato solo se `|arrotondamento| ≤ limite` e
       `shortfall + ΣV ≥ −limite`, con `V` = valore di `D` nella valuta di valutazione. È il
       vincolo come sarebbe con le integrazioni: l'integrazione è liquidità raggiungibile, quindi
       alza `fixed_reference` e `shortfall` di `V`, e lascia uguali arrotondamento e limite. Serve
       perché il rischio residuo di §2 dice che uno sforamento entro la soglia esce.
  2. **Planner** (`planner.py:150-160`): dopo il replay, `rounding_top_ups`. L'errore propaga: il
     worker lo rende `execution_failed`, senza dettagli (`tools/worker.py:178-180`), e la UI lo
     mostra con il pannello d'errore che c'è già. Il rifiuto del replay non dà più
     `ready_no_incumbent`. Docstring aggiornati: modulo (`:19-23`), `plan_pac_allocation` («never
     raises…») e `_no_incumbent_result`.
  3. **Schema** (`schemas/pac_allocator.py`):
     - `PlannerRoundingTopUp(broker_id, currency, amount, rounded_postings, valuation_amount)`;
       `PacPlanSolution.rounding_top_ups` obbligatorio, senza default; `PacNoOpSolution` lo vuole
       vuoto;
     - `PlannerLedgerRow` (`:1409-1425`) non vieta più il saldo finale negativo, e tiene le due
       identità. Lo vieta `RebalancerPlanSolution`, come oggi. `PacPlanSolution` lo ammette solo con
       l'integrazione della stessa cassa e `amount = −saldo`, e ogni integrazione ha la sua riga
       negativa;
     - `rounded_postings ≤ 2 × ordini della cassa + FX che entrano nella cassa`. È solo un tetto:
       una commissione che si arrotonda a zero conta in `N` ma sul filo vale 0;
       `amount ≤ rounded_postings × unità minima` del catalogo;
     - `valuation_amount` nella valuta di valutazione, positivo, uguale ad `amount` quando la cassa
       è in quella valuta;
     - contabilità (`_validate_accounting_summary`, `:1794`): `free_cash + ΣV ≥ 0` e
       `shortfall + ΣV ≥ −limite`. Le identità restano uguali; il Rebalancer passa `ΣV = 0`;
     - `ready_no_incumbent`: `stop_reason` solo `time_limit`/`node_limit`, per PAC e Rebalancer,
       come l'infeasible al commit 4. Dopo il commit 5 «nessun piano» nasce solo da SCIP senza
       soluzione al primo stadio, e quello stadio è non finito (`solver.py:397-437`): anche
       un'anomalia lo segna `unfinished`.
  4. **Report** (`planner_report.py`): `build_rounding_top_ups`, con `ratio_to_fixed_decimal` e
     `_money` nella valuta di valutazione.
  5. **UI**: in `StateNotice`, dopo la catena degli stati, una nota `NOTICE.warning` con
     `role="status"`, una riga per cassa (`pac-planner-top-up`, `pac-planner-top-up-row` con
     `data-broker` e `data-currency`). L'importo passa da `formatPlannerMoneyPlain`, quindi è
     mascherato. Via il ramo `ready_no_incumbent` + `completed` di `StateNotice` (`:85-91`) e il
     ramo `floatingFinished` di `ProofPanel` (`:77-81`), con il suo `unfinished`.
  6. **i18n**, via `dev.py i18n add`: una chiave nuova nelle 4 lingue,
     `tools.pacAllocator.planner.result.states.topUp.row`. Testo IT: «Per eseguire il piano servono
     {amount} in più su {broker} ({currency}), per gli arrotondamenti all'unità minima.» Le due
     chiavi che restano senza uso, `result.proof.floatingFinished` e
     `result.states.noIncumbent.rejected`, **restano**, per decisione (a): vanno nella lista di
     fine round.
  7. `api sync`, poi i gate.

  - **Perché `valuation_amount`.** Lo schema non ha i cambi: senza il valore nella valuta di
    valutazione non potrebbe verificare la contabilità con le integrazioni, e dovrebbe solo
    allentarla.
  - **Versione.** `contract_version` resta `2.0.0`: il Tool non è rilasciato, come al commit 4.
  - **Rebalancer.** Il classificatore non lo copre: non ha un planner. È un residuo dichiarato.
  - **Prova in sola lettura** (28/09, sonda pura senza DB né server:
    `files/qx1b-probes/tie_currency_probe.py` e `.log`, nella cartella di sessione). Sui tre
    pareggi (`3 × 33,335` € su 100,00; `3 × 333,5` JPY su 1 000; `3 × 33,3335` BHD su 100,000):
    - SCIP chiude tutti gli stadi con 3 quote;
    - il replay vede solo `SPENDABLE_CASH_NONNEGATIVE` e `NO_SHORT_OR_LEVERAGE`;
    - deficit di 1 unità minima, `N = 1`;
    - `ROUNDING_BOUND` rispettato, perché `shortfall = −limite`;
    - il planner di oggi dà `ready_no_incumbent` + `completed`: è il rosso.
    Controllo: a 33,336 € SCIP sceglie 2 quote e il replay le accetta.
- **F3 — oracolo solo nei test.** ✅ 2026-09-28
  - `oracle.py` passa nell'albero dei test.
  - Un test strutturale verifica che nessun modulo di produzione lo importi.

  > **Note implementazione** (2026-09-28):
  > - Spostato con il filesystem, non con `git mv`: ora è
  >   `backend/test_scripts/test_services/_pac_exhaustive_oracle.py`. Il trattino basso lo tiene
  >   fuori dalla raccolta di pytest (`pytest.ini`: `python_files = test_*.py`). Docstring: è uno
  >   strumento di test, non costruisce più un testimone sul filo, e il tetto di sicurezza serve
  >   solo a non bloccare un test.
  > - Il test strutturale è `test_exhaustive_oracle_is_test_only` (passo 5 della ripresa).
  > - Runner, file condiviso `scripts/test_runner/_backend_services.py`: cambiano solo 6 testi
  >   delle voci PAC (docstring e `desc` di `pac-planner-oracle`, `-solver`, `-proof`,
  >   `-service`). Chiavi e percorsi restano uguali. Lo segnalo al coordinator nell'handoff.
  > - Gli import dei moduli di test si ricablano nel lotto del test-author (F4).
- **F4 — test backend** (test-author, lane 6151).
  - Accordo SCIP↔oracolo allargato alle forme di commissione: fissa, minimo sopra
    `rate · notional_upper`, tetto che morde, tetto piccolo per titolo. ✅ 2026-09-25, con le
    fixture del gate nei commit 2 (X2: tre) e 3 (QX1-a: tre, più un controllo).
  - Regressione X1 (100 € su due ETF: veloce) e X2 (minimo 1,50 €: 9 quote); 5 € contro minimo
    d'ordine 10 € → `ready_infeasible` da SCIP.
  - F2c (QX1-b):
    - `3 × 33,335` su 100,00 € → 3 quote, e 0,01 € da aggiungere. Condizione del coordinator
      (25/09 alle 11:05): l'esito si verifica **sul risultato pubblicato**, cioè 3 quote e la nota
      di 0,01 € per la cassa broker/EUR, non sulla strada interna (incumbent SCIP o replay);
    - un deficit oltre `N` unità minime → errore;
    - un'altra violazione delle regole esatte → errore, anche se il deficit sta sotto la soglia;
    - una valuta a 0 decimali (JPY) e una a 3 (BHD), per l'unità minima.

    Lotto del commit 5 (28/09), rosso prima della cura:
    - **servizio, SCIP vero**, sul risultato pubblicato e rivalidato: EUR, JPY e BHD come nella
      sonda di F2c; stato `ready_incumbent`, 3 quote, una sola integrazione (broker, valuta, 1
      unità minima, `N = 1`) e il saldo finale a −1 unità minima. La stessa proposta con 1 unità
      minima di cassa in più passa il replay: l'importo detto basta;
    - **classificatore**, su candidati costruiti a mano con `evaluate_exact_candidate`:
      - deficit oltre `N × unità minima` → errore;
      - commissione presente, `N = 2`: 0,02 accettato, 0,03 errore;
      - un'altra violazione più un piccolo deficit → errore;
      - due casse: la soglia vale per cassa, non sommata;
      - il credito FX conta in `N`;
      - candidato fuori contratto → errore;
    - **planner**: un candidato oltre la soglia fa sollevare `plan_pac_allocation`, e non dà mai
      `ready_no_incumbent`. Sostituisce `test_replay_failure_suppresses_the_plan`, che prova il
      comportamento rovesciato il 25/09 (attribuzione con la test-triage);
    - **schema**: riga negativa solo con la sua integrazione; importo diverso, integrazione senza
      riga negativa, oltre `N × unità minima`, `rounded_postings` sopra il tetto, no-op con
      un'integrazione, saldo negativo nel Rebalancer, `valuation_amount` fuori valuta o diverso
      dall'importo nella stessa valuta → invalidi; contabilità allentata solo di `ΣV`;
      `ready_no_incumbent` + `completed` → invalido. La fixture `_ready_no_incumbent_result` passa a
      uno stop per limite con uno stadio non finito;
    - **API**: il pareggio EUR da `/tools/compute`, con l'integrazione sul risultato;
    - **UI**: la nota per cassa, se c'è un banco di prova per componenti adatto.

    ✅ 2026-09-28 — **rossi scritti dal test-author** (brief nella cartella di sessione,
    `files/commit5/test_author_red_prompt.md`), lanciati una volta ciascuno sulla 6151, uno alla
    volta; log in `/tmp/libreFolio_d_c5_*.log`.

    > **Note implementazione**:
    > - Rossi, tutti per l'assenza del bersaglio e dopo che i fatti di partenza passano:
    >   - classificatore, 20 (`test_pac_planner_evaluator.py:4643-5068`): `rounding_top_ups`,
    >     `ExactReplayRejectedError` o `ExactRoundingTopUp` assenti. Chiave intera: 20 failed,
    >     139 passed;
    >   - servizio, 7 (`test_pac_planner_planner.py:337-516`): i tre pareggi danno
    >     `ready_no_incumbent` invece di `ready_incumbent`; i tre controfattuali non hanno
    >     `rounding_top_ups`; il rifiuto oltre soglia risponde invece di sollevare. Chiave
    >     intera: 7 failed, 24 passed;
    >   - report, 1 (`test_pac_planner_report.py:589-622`). Chiave intera: 1 failed, 17 passed;
    >   - schema, 17 (`test_pac_planner_schemas.py:2280-2312`, `:2554-2804`): `extra_forbidden`
    >     su `rounding_top_ups`, «Published ledger amounts cannot be negative» al posto dei
    >     messaggi nuovi, `DID NOT RAISE` sul `completed` senza piano. Chiave intera: 17 failed,
    >     450 passed;
    >   - API, 1 (`test_pac_planner_tool_api.py:239-269`): `ready_no_incumbent` al posto di
    >     `ready_incumbent`;
    >   - componente, 4 (`StateNotice.test.ts`, nuovo): `pac-planner-top-up` assente. I 2 casi
    >     «nessun blocco» sono verdi prima e dopo, con la loro barriera di presenza.
    > - Nessun test esistente cambia stato. `_ready_no_incumbent_result` diventa uno stop per
    >   limite con uno stadio non finito; il caso `no-incumbent-over-infeasible-stage` ora
    >   aspetta il messaggio della regola sullo stop, che scatta prima: verde prima e dopo.
    > - **Attribuzione con la test-triage** di `test_replay_failure_suppresses_the_plan` e del suo
    >   `_InfeasibleReplay`: test vecchio per scelta. Provava il comportamento che il developer ha
    >   rovesciato il 25/09 (il rifiuto del replay dava `ready_no_incumbent` + `completed`). Non è
    >   un flake e non è un difetto del prodotto: sostituito da
    >   `test_replay_rejection_beyond_the_rounding_threshold_raises`. Tolto anche
    >   `_ZERO_CANDIDATE_ID`, rimasto senza uso.
    > - Porta 6151 libera dopo l'API (`lsof` vuoto, uscita 1). Nessun file di prodotto, runner,
    >   i18n, fixture JSON o fingerprint toccato.

    > **⚠️ Fuori pista** (scelte del test-author, verificate sui test):
    > - Il rifiuto oltre soglia non può usare il pareggio a commissione zero: la vista limita la
    >   rotta a 3 quote, quindi la quarta è fuori contratto e non oltre soglia. Usa il pareggio
    >   EUR con 1 € di commissione fissa: SCIP compra 2 quote, la sonda ne fa 3, la cassa resta
    >   a −1,01 € con `N = 2`.
    > - Per la stessa ragione (limite della vista): 0,03 € con `N = 2` viene da 0,02 € di
    >   commissione su 100 € di cassa; «una quota che la cassa non paga» è una quota da 10 € con
    >   1 € di commissione su 10 €; l'«altra violazione» è un minimo d'ordine di 4 quote
    >   (`ORDER_MIN_IF_ACTIVE`), non un tetto di rotta.
    > - Credito FX: 84,16 € lasciano la cassa USD a −0,02 (accettata), 84,15 € a −0,03 (errore),
    >   valori letti dall'evaluator.
    > - Schema: USD entra nel catalogo, così il messaggio sulla valuta di valutazione è quello
    >   inchiodato. Secondo caso positivo: 0,02 € con 2 registrazioni.
    > - **Ordine dei validatori che la cura deve rispettare**: unicità delle casse prima della
    >   copertura; positività del valore prima dell'uguaglianza con l'importo; valuta di
    >   valutazione prima dell'uguaglianza; controllo dello shortfall prima della decomposizione,
    >   come oggi.

    ✅ 2026-09-28 — **cura del commit 5** (prodotto, fixture e gate): tutti i gate verdi sulla
    6151.

    > **Note implementazione**:
    > - `models.py`: `ExactRoundingTopUp` (frozen, slots). Controlla testo, valuta, importo
    >   positivo, `rounded_postings` intero ≥ 1 e non bool, valore positivo.
    > - `evaluator.py`: `ExactReplayRejectedError(ExactEvaluatorError)` e
    >   `rounding_top_ups(scenario, evaluation)`. Legge solo `evaluation.accounting` e i codici dei
    >   conflitti, perché i test fabbricano valutazioni con `replace`. I messaggi nominano regole e
    >   casse, mai importi.
    > - `planner.py`: dopo il replay chiama `rounding_top_ups`, e l'errore propaga. Tolto il ramo
    >   `ready_no_incumbent` del rifiuto.
    > - `planner_report.py`: `build_rounding_top_ups`, una proiezione senza ricalcolo,
    >   nell'ordine del classificatore.
    > - Schema:
    >   - `PlannerRoundingTopUp`; `PacPlanSolution.rounding_top_ups` obbligatorio;
    >     `PacNoOpSolution` con `max_length=0`;
    >   - `PlannerLedgerRow` non vieta più il saldo negativo: lo vieta `RebalancerPlanSolution`;
    >   - `_validate_pac_rounding_top_ups`, nell'ordine unicità → copertura → tetto;
    >   - l'unità minima del catalogo in `_validate_ready_solution`;
    >   - la valuta di valutazione e l'uguaglianza in `_validate_solution_financials`;
    >   - `_validate_accounting_summary(…, top_up_value)` allenta solo free cash e shortfall;
    >   - lo `stop_reason` dei due `ReadyNoIncumbent` ammette solo i limiti.
    > - UI:
    >   - `StateNotice`: il blocco `pac-planner-top-up` dopo la catena degli stati, una riga per
    >     cassa nell'ordine del filo. Tolto il ramo `ready_no_incumbent` + `completed`;
    >   - `ProofPanel`: tolti `unfinished` e il ramo `floatingFinished`;
    >   - `types.ts`: `PacRoundingTopUp`, che tipizza la lista in `StateNotice`.
    > - i18n con `dev.py i18n add` (`/tmp/libreFolio_d_i18n_c5.sh`): da 4102 a 4103 chiavi per
    >   lingua, stesso insieme nelle 4 lingue, +3 righe per file.
    > - `api sync` alle 16:23 (`/tmp/libreFolio_d_c5_api_sync.log`):
    >   - fingerprint PAC da `bd52b93a…` a `502e8c48dbbf3cc5…`;
    >   - generazione del contratto dei tool `2f30f6ce92e3b7fe…`, versione `2.0.0`;
    >   - Rebalancer da `fff1f966…` a `17d5625e8bf24e20…`, con una sonda di solo import sulle
    >     funzioni del test.
    > - Chiavi sulla 6151, una alla volta:
    >   - evaluator 159/159;
    >   - servizio 31/31;
    >   - report 16 passed, 2 failed;
    >   - schema 443 passed, 24 failed;
    >   - API 6/6, con la porta libera dopo.
    > - Attribuzione dei rossi residui:
    >   - 22 dello schema e 2 del report: manca `rounding_top_ups` nelle due fixture JSON PAC e
    >     in `_build_primary_solution` del report;
    >   - 2 sono i fingerprint;
    >   - i 17 casi nuovi dello schema e il test di proiezione del report sono verdi.
    >   Lotto al test-author (`c5-fixture-followup`): solo modifiche, senza lanciare suite.
    > - Il lotto del test-author:
    >   - `"rounding_top_ups": []` nelle due fixture JSON PAC (`pac_plan_result.min.v2.json` e
    >     `pac_plan_result.candidate-max.v2.json`), e `rounding_top_ups=[]` in
    >     `_build_primary_solution` del test del report;
    >   - i due fingerprint del test dello schema, calcolati con le sue funzioni:
    >     PAC `502e8c48dbbf3cc55fbe02f2a2c43b186d5970ff3f1fe5130d35748641c8e374`,
    >     Rebalancer `17d5625e8bf24e20090ef3c58e7cd98178eaadb74884aee92cbc1753d5591cc3`;
    >   - una ricerca in tutto l'albero dei test: nessun'altra soluzione PAC costruita senza il campo;
    >   - su mia richiesta, due docstring vecchie in `test_pac_planner_schemas.py`
    >     (`_pac_top_up_result` e il caso che lo segue).
    > - Lint: ruff dava 2 C901 nuovi, miei (a HEAD era pulito). Ho estratto
    >   `_require_rounding_only_rejection` (evaluator) e `_validate_pac_top_up_minor_units` (schema),
    >   senza cambiare l'ordine dei controlli. ruff e black puliti.
    > - Gate sulla 6151, in serie (`/tmp/libreFolio_d_c5_gates.sh`, riepilogo in
    >   `/tmp/libreFolio_d_c5_gates_summary.log`):
    >   - services: core 152, evaluator 159, oracle 20, policies 40, solver 19, proof 30,
    >     wire-numbers 39, report 18, service 31, tools-registry 93;
    >   - schemas: pac-planner 467, tools 271;
    >   - api: pac-planner-tool 6, tools 7;
    >   - Vitest `core-unit` (98 file, 2647 test) e `component-unit` (86 file, 2119 test);
    >     `StateNotice.test.ts` da solo: 6;
    >   - rispetto al gate dopo il merge: evaluator +20, servizio +6 netti, report +1, schema +17,
    >     API +1, componenti +1 file e +6 test. Sono i rossi del lotto, ora verdi;
    >   - 6151 libera dopo (`lsof` esce con 1).
    > - Controlli statici:
    >   - `front check`: 3 errori e 41 avvisi, negli stessi 4 file non PAC di prima;
    >   - Prettier pulito sui file frontend toccati e sui 4 cataloghi;
    >   - ruff e black puliti sui file Python toccati, test e runner compresi;
    >   - `git diff --check` pulito;
    >   - `i18n audit`: 4103 chiavi per lingua, tutte complete, e `topUp.row` risulta usata. Fra le
    >     «Likely Unused» le PAC sono 170: le 168 del P1 e le 2 tenute per decisione (a).

    > **⚠️ Fuori pista**:
    > - `ProofPanel`: prima di togliere `floatingFinished` ho verificato che sia irraggiungibile.
    >   Lo schema da solo ammette `not_proven` con tutti gli stadi finiti, il prodotto no:
    >   - `solver.py:396-405` segna `finished` solo con stato `optimal` e una soluzione;
    >   - un'anomalia (`:429-434`) cade sempre su uno stadio non finito;
    >   - quindi `proof.py:204-213` dà `optimal_proven` quando tutti gli stadi sono finiti e il
    >     piano pubblicato è quello di SCIP.
    >   Un piano `not_proven` ha sempre uno stadio aperto.
    > - Il contesto del test-author dei rossi non c'era più: il brief nuovo è autosufficiente.
    > - Finché le fixture PAC non avevano il campo, un caso negativo dello schema partiva da una
    >   base già invalida, e poteva essere verde per la ragione sbagliata. Ora la base è valida (i
    >   casi positivi che la caricano sono verdi), quindi ogni caso negativo verde respinge la sua
    >   mutazione, non la fixture.
    > - L'audit sposta 2 chiavi PAC da «usate» a «not verified»: `result.ledger.fields.final_spendable`
    >   e `.final_physical`. In `backend/app` comparivano come testo solo nella tupla
    >   `nonnegative_fields` di `PlannerLedgerRow`, e il commit 5 le toglie da lì, perché il saldo
    >   finale ora può essere negativo. Il vocabolario dell'audit legge solo `backend/app`
    >   (`frontend/scripts/i18n-audit.py:51`, `scripts/i18n_usage.py:242-260`). Le chiavi restano
    >   usate: `LedgerTable.svelte:56` le compone da `LEDGER_FIELDS` (`model.ts:174`). Nessuna
    >   azione. Le PAC «not verified» passano da 3 a 5; le «Likely Unused» sono solo le 2 attese in
    >   più.
  - Il gate d'accordo SCIP↔oracolo tiene conto di X3 respinta. Dove è raggiungibile il pareggio di
    un addebito (acquisto o commissione), SCIP può fare meglio dell'oracolo esatto usando il
    centesimo del pareggio. Quindi (riscritto il 02/10, R13.6):
    - sui domini senza pareggi degli addebiti gli ottimi coincidono, anche quando l'accredito FX
      cade su un pareggio (fixture `credit_tie_fx`). L'accredito entra solo con `+` nelle righe
      `≥ 0` e in nessun obiettivo, quindi il modello può sempre usare il valore più alto, che è
      quello vero: l'insieme ammissibile non cambia;
    - dove è raggiungibile il pareggio di un addebito, SCIP non è mai peggiore dell'oracolo.
    - Il guard sui pareggi degli accrediti, con `_half_up_tie_reachable`, non c'è più: opzione A
      del developer, 02/10.
  - Schema e API.
  - Le prove usa-e-getta del 24/09 sono copiate nella cartella di sessione (`files/x1-probes/`),
    perché `/tmp` si svuota al riavvio.

  > **Misura del Checkpoint** (2026-09-28, commit 4). Sonda pura, senza DB né server:
  > `files/x1-probes/checkpoint_count_probe.py` e il suo `.log`, nella cartella di sessione. Il
  > `Checkpoint` è un contatore iniettato; il tempo è solo informativo.
  >
  > | Caso | Dominio | SCIP | Replay | Planner, via SCIP | Planner di oggi (oracolo) |
  > |---|---|---|---|---|---|
  > | no-op (5 € contro minimo 10 €) | 1 | 6 | 88 | 97 | 181 |
  > | incumbent (50 €) | 6 | 6 | 96 | 105 | 674 |
  > | minimo forzato impossibile | 1 | 1 | — | 3 | 92 |
  > | **X1**: 100 € su 2 ETF a 40/60 € | 60 006 | 8 | 178 | 189 | oltre 1 000: sonda interrotta |
  >
  > - SCIP chiama il `Checkpoint` una volta per stage. Il replay lo chiama 88-178 volte: cresce
  >   con le decisioni e i vincoli, non con il dominio.
  > - L'oracolo lo chiama 89-96 volte per candidato. Su X1 sarebbero circa 5,7 milioni di chiamate.
  > - Quindi il test di X1 è deterministico con un `Checkpoint` che conta e alza un errore oltre
  >   una soglia fissa, ben sopra 189 e molto sotto l'enumerazione. Oggi è rosso subito; dopo D-X1
  >   il planner risponde con un piano pronto, senza alzare niente.
  > - Via SCIP, il minimo impossibile dà oggi `ready_no_incumbent` con `stop=time_limit`: è il
  >   difetto che F1 scioglie (lo stage infeasible conta come non terminato).
  > - Una seconda sonda, `infeasible_stage_fields_probe.py`, conferma che uno stage 1 infeasible
  >   non ha primal, duale né gap (tutti `None`). Lo schema F1 può quindi richiederli assenti.
  >
  > **Inventario D-X1** (2026-09-28, sola lettura, con la test-triage). Criterio: è obsoleto ciò
  > che prova il percorso «prima l'oracolo», l'oracolo come prova di produzione o la regola «una
  > soluzione floating non si promuove mai». D-X1 rovescia quella regola: è una decisione del
  > developer, non un difetto.
  >
  > Codice di produzione che D-X1 rende obsoleto:
  > - `planner.py`: il ramo dell'oracolo in `_search`, `_Search.oracle_*`, lo stop forzato a
  >   `completed` e l'evidenza `not_run` in `_common_ready_fields`, `_wire_oracle_witness`;
  > - `proof.py`: `ExhaustiveOracleWitnessFacts`, `conclude_with_oracle`,
  >   `conclude_without_proof`, `_witness_from_oracle`, l'import di `OracleResult`;
  > - schema: `ExhaustiveOracleWitness`, `SolverNotRunEvidence`, `SolverNotRunReasonCode`
  >   (`allocation.solver_not_required`);
  > - `oracle.py` in produzione (va nei test, F3);
  > - UI: i rami `exhaustive_oracle` e `not_run` di `ProofPanel.svelte`, `notCertified`, e le
  >   chiavi `oracleWitness`, `oracleInfeasibleWitness`, `sources.exhaustive_oracle`,
  >   `solverNotRun`, `reasons.allocation.solver_not_required`.
  >
  > Test, con l'attribuzione:
  >
  > | Modulo | Obsoleti (si tolgono) | Da riscrivere | Restano |
  > |---|---|---|---|
  > | `test_pac_planner_planner.py` | `:370` fallback oltre il tetto, `:409` fonti e non promozione, `:529` minimo forzato → `not_proven`, `:660` e `:678` evidenza `not_run`, `:702` percorso SCIP (diventa quello di default) | `:234` fonte della prova, `:450` stati di `ready_infeasible`, `:465` infeasible da SCIP, `:493` nessun `deterministic_conflict`, `:620` evidenza, docstring e import `:118-135` | `:259`, `:278`, `:295`, `:307`, `:340`, `:560`, `:585`, `:738`, `:756`, `:768` |
  > | `test_pac_planner_proof.py` | `:127`, `:153`, `:199`, i parametri di falsificazione del testimone dell'oracolo, `:256`, `:265`, `:272`, `:294`, `:313`, `:336`, `:356`, `:422`, `:442`, `:465`, `:481` | — | i parametri del conflitto, `:105`, `:110`, `:179`, `:192`, `:281`, `:377`, `:398`, `:460`, `:495` (da adattare al testimone nuovo) |
  > | `test_pac_planner_solver.py` | — | `:354` infeasible: un solo stage terminale `infeasible`; import `:48` e docstring dopo lo spostamento dell'oracolo | il gate d'accordo `:209` |
  > | `test_pac_planner_schemas.py` | `:1233-1238` catalogo `SolverNotRunReasonCode`, `:1246` voce `REASON_ONLY_CODES`, `:2360` «solver finito non diventa prova» | `:395-411`, `:459-464`, `:2172`, `:2188`, `:2230`, `:2326`, `:2380-2407` | il resto |
  > | `test_pac_planner_report.py` | — | `:58` e `:610` (`conclude_without_proof`) | il resto |
  > | fixture `*.v2.json` | — | `pac_plan_result.min` `:93-101`, `pac_plan_result.candidate-max` `:79-80`, `rebalancer_plan_result.medium` `:141-142`: `not_run` → stage `reported_floating` terminati | `:894`, `:902` (`closure_kind`) |
  >
  > `test_api/test_pac_planner_tool_api.py` non cita né l'oracolo né `not_run`: il suo
  > `optimal_proven` (`:191`) resta vero anche con SCIP.
  >
  > Tolte anche per decisione del developer (28/09 alle 10:58, sopra): le forme di prova mai
  > prodotte, pensate per i design di prima di D-X1.
  > - `deterministic_conflict`: mancava un ponte fra i due vocabolari di codici (`planner.py:272`).
  >   Schema `DeterministicConflictWitness`; `proof.py` `DeterministicConflictWitnessFacts` e
  >   `conclude_infeasible_from_conflicts`;
  > - `gap_bounded`: serviva un duale sicuro. Schema `GapBoundedProof`, `BoundedObjectiveStage` e
  >   `_validate_gap_proof`;
  > - `score_lattice_closure`: schema `ScoreLatticeClosureWitness`;
  > - `describe_conclusion` (`proof.py`), usato solo nei test (N8);
  > - UI: i rami `gap_bounded`, `latticeWitness` e `conflictWitness` di `ProofPanel.svelte`, il
  >   badge `gap_bounded` di `model.ts`, e le chiavi `gapBounded`, `latticeWitness`,
  >   `conflictWitness`, `sources.deterministic_conflict`, `sources.score_lattice_closure`,
  >   `badges.gapBounded`;
  > - i loro test in `test_pac_planner_proof.py` (i parametri del conflitto, `:105`, `:110`),
  >   `test_pac_planner_planner.py` (`:493`) e `test_pac_planner_schemas.py`.
  >
  > Restano fuori dal commit 4, da portare alla review:
  > - il Rebalancer rinviato: `SellIrreducibilityCheck.closure_kind` `"deterministic_conflict" |
  >   "exhaustive_oracle"` (schema `:1571`), `ProofRequirement.allowed_sources` (`models.py:785`)
  >   ed `evaluator.py:3124`. La verifica di irriducibilità delle vendite è ancora nei piani, quindi
  >   la condizione del developer non vale. Ma con D-X1 l'oracolo non è più una fonte di
  >   produzione: le fonti vanno riprogettate col Rebalancer, in R8;
  > - uno stage successivo al primo che torna infeasible resta un'anomalia (non terminato), e
  >   `build_stop_reason` lo chiama `time_limit`. Era già così: va in R5.

  > **Lotto del commit 4** ✅ 2026-09-28 (test-author, lane 6151, un comando alla volta). Coperti la
  > regressione X1, l'infeasible da SCIP, lo schema e l'API; F2c resta al commit 5. I tre test rossi
  > del punto 5 della ripresa sono verdi (3 passed, 22 deselected). L'attribuzione è quella
  > dell'«Inventario D-X1» qui sopra.
  >
  > | Modulo | Esito | Cosa cambia |
  > |---|---|---|
  > | `test_pac_planner_planner.py` | 25 passed | Tolti i 5 obsoleti dell'inventario (`:370`, `:409`, `:529`, `:660`, `:678`) e `:493` (decisione del developer). `:702` riscritto sul posto: ogni risultato pronto porta l'evidenza `reported_floating`. Riscritti docstring, import, `:234`, `:450`, `:465` e `:620`. Nuovi: i tre rossi e `test_exhausted_solver_budget_degrades_to_honest_not_proven` (budget zero → `not_proven`, `time_limit`) |
  > | `test_pac_planner_proof.py` | 30 passed | Riscritto su tre esecuzioni reali di SCIP: superficie pubblica (`__all__`, una sola funzione), tabella degli esiti, falsificazioni, ogni stadio aperto (tie-break compresi), infeasible solo dal primo stadio globale, limite e anomalia, nessun trasferimento della prova, codici discordi = falsificazione. 20 test tolti, 9 nuovi, 4 restano |
  > | `test_pac_planner_solver.py` | 19 passed | L'infeasible riporta un solo stadio, il primo, globale |
  > | `test_pac_planner_oracle.py` | 20 passed | Solo import e docstring: l'oracolo ora è `test_services/_pac_exhaustive_oracle.py` |
  > | `test_pac_planner_report.py` | 17 passed | L'e2e usa `conclude_with_solver`; nuovo `test_infeasible_first_stage_is_a_verdict_that_completes_the_search` |
  > | `test_pac_planner_schemas.py` | 450 passed | Tolti conflitto, gap (2), reticolo e `:2360` (inventario); 8 nuovi su `solver_status` e sullo stadio infeasible; pin dei fingerprint aggiornati (PAC `bd52b93a…`, ribilanciatore `fff1f966…`) |
  > | fixture `*.v2.json` (3) | — | `not_run` → stadi `reported_floating` terminati; restano `not_proven` e `completed`. Byte del sorgente (emessi): candidate-max 20 967 (18 329), min 13 671 (8 421), ribilanciatore 36 615 (21 333), sotto il tetto di 262 144 |
  > | `test_api/test_pac_planner_tool_api.py` | 5 passed | Vedi il primo fuori pista |
  >
  > - Gate su 6151 dalle 12:30 alle 12:33 (`/tmp/libreFolio_d_gate_x1.sh`, riepilogo in
  >   `/tmp/libreFolio_d_gate_x1.summary`):
  >   - `services`: `pac-planner-core` 152, `-evaluator` 139, `-oracle` 20, `-policies` 40,
  >     `-solver` 19, `-proof` 30, `-wire-numbers` 39, `-report` 17, `-service` 25, `tools-registry` 93;
  >   - `schemas`: `pac-planner` 450, `tools` 271;
  >   - `api`: `tools` 7; `pac-planner-tool` 4 passed e 1 failed, poi 5 passed dopo la correzione
  >     (`/tmp/libreFolio_d_ta_api_pac.log`).
  > - Statici:
  >   - ruff e black puliti sui 18 file Python toccati; `git diff --check` pulito;
  >   - `i18n audit`: 4088 chiavi, tutte complete, 0 chiavi backend mancanti. Le 3 chiavi PAC
  >     «unused» (`origin.copied`, `result.sections.exposures`, `result.sections.ledger`) si leggono
  >     per prefisso dinamico, in file che il commit 4 non tocca.
  > - Porta 6151 libera dopo ogni comando.
  >
  > **⚠️ Fuori pista**:
  > - `api pac-planner-tool` rosso su `test_pac_compute_plans_a_buying_scenario_to_a_proven_optimum`
  >   (`:198`), che l'inventario aveva mancato.
  >   - Attribuzione con una sonda pura (`/tmp/libreFolio_d_api_eq_probe.py`): l'unica differenza è
  >     il setting `time_budget` di ogni stadio, 3,5 s in processo e 30 s nel worker. Due
  >     esecuzioni a 30 s sono identiche.
  >   - Prima di D-X1 non si vedeva, perché l'oracolo non pubblicava setting.
  >   - Il prodotto è giusto. Il test-author fa leggere al test l'`engine_timeout_ms` dal catalogo e
  >     lo passa alla chiamata in processo, come fa il plugin; poi verifica il `time_budget`
  >     pubblicato. L'uguaglianza completa resta.
  > - Il test di schema a `:2360` era già fra gli obsoleti dell'inventario: toglierlo non chiede
  >   altre conferme.
  > - Le 3 fixture restano `not_proven` + `completed`: sono forme del wire, e nemmeno prima erano
  >   esiti del planner (alla baseline: `not_proven` con `not_run`). Il test-author nota che oggi,
  >   con stadi terminati e `completed`, il planner pubblicherebbe `optimal_proven`. Portarle a
  >   `solver_status` è un seguito possibile, da decidere.
  > - Tolto il bytecode `pac_allocator/__pycache__/oracle.cpython-313.pyc`, ignorato da git.
  > - Riallineati a D-X1, con note datate: il runbook (S2, S2b, S2c, S9), T5 e l'anteprima di C.
  >   §4 punto 5 (`score_lattice_closure`) è barrato: era stato scritto prima di D-X1.
  > - Il reperto R10 (stadi di tie-break e stop) è aggiunto alla tabella dello STOP.
- **F5 — frontend.** ✅ 2026-09-28
  - Testimone del solver al posto di quello dell'oracolo in `ProofPanel.svelte`; tipi e
    `StateNotice`.
  - i18n via `dev.py i18n`, poi `api sync`, dichiarando l'ora del client accanto a `front check`.

  > **Note implementazione** (2026-09-28):
  > - i18n: 18 comandi `dev.py i18n` da `/tmp/libreFolio_d_i18n_x1.sh`, tutti ✅. Per ogni lingua
  >   4095 → 4088 chiavi: 5 aggiunte, 12 tolte, 1 cambiata, stesso insieme nelle quattro lingue;
  >   diff di 4 file, +40/−68. Tutte sotto `tools.pacAllocator.planner.result.`:
  >   - aggiunte `proof.sources.solver_status`, `proof.statuses.infeasible`, `proof.solverWitness`,
  >     `proof.solverInfeasibleWitness`, `states.noIncumbent.rejected`;
  >   - cambiata `proof.floatingFinished`: ora dice che il solver ha chiuso ogni stadio ma il
  >     replay Decimal ha respinto il piano;
  >   - tolte `proof.oracleWitness`, `proof.oracleInfeasibleWitness`,
  >     `proof.sources.{exhaustive_oracle,deterministic_conflict,score_lattice_closure}`,
  >     `proof.solverNotRun`, `proof.reasons.allocation.solver_not_required`, `proof.notCertified`,
  >     `proof.gapBounded`, `proof.latticeWitness`, `proof.conflictWitness`, `badges.gapBounded`.
  > - `ProofPanel.svelte`: gli stadi vengono da `solver.stages`; con `optimal_proven` e con
  >   `infeasibility_proven` la fonte è `sources.solver_status`, con il testimone del solver
  >   (numero di obiettivi chiusi, oppure primo stadio infeasible). Resta
  >   `data-testid="pac-planner-proof-witness"`. Il suggerimento di `not_proven` è
  >   `floatingFinished` se nessuno stadio è aperto, altrimenti `floatingUnfinished`. Tolti i rami
  >   `gap_bounded` (con la tabella dei limiti), `not_run` e i testimoni oracolo, reticolo e
  >   conflitto. La colonna di stato legge `STATUS_FALLBACKS` (finished, unfinished, infeasible).
  > - `StateNotice.svelte`: gli stadi vengono da `result.solver_evidence.stages`. Un ramo nuovo,
  >   prima di quello generico: `ready_no_incumbent` con `stop_reason = completed` (SCIP ha chiuso
  >   tutto, il replay ha respinto) → avviso `data-state="no_incumbent"`, corpo
  >   `states.noIncumbent.rejected`, senza consigli, col pulsante di modifica.
  > - `model.ts`: tolto il badge `gap_bounded`. `types.ts:47`:
  >   `PacSolverStage = PacSolverEvidence['stages'][number]`.
  > - `api sync` alle 11:36:48, exit 0 (`/tmp/libreFolio_d_api_sync_x1.log`). Fingerprint PAC
  >   `a4f499864b74cdea…` (client del 24/09 alle 17:25) → `bd52b93a79b6560c…`; digest del contratto
  >   dei tool `a8033018917dc9a2…`. La versione del Tool resta `2.0.0`. I file generati sono
  >   ignorati da git. Una sonda di solo import (`/tmp/libreFolio_d_fp_probe.py`) conferma PAC
  >   `bd52b93a…` e dà il ribilanciatore `c4451b184aa0fd9f…` → `fff1f966c63a9d9b…`.
  > - `front check` dopo il sync (`/tmp/libreFolio_d_front_check_x1.log`): 3 errori e 41 warning
  >   in 4 file, il pavimento; nessuno nel PAC (`BrokerSharingPanel`, `GlobalSettingsTab`,
  >   `TransactionFormModal.test`, `ToolExecutionMetrics`). `prettier --check` pulito sui 4 file
  >   e sui 4 JSON.
  > - Nessun test Vitest o E2E tocca il pannello della prova o gli avvisi di stato; in
  >   `frontend/src` ed `e2e` non resta alcun riferimento alle forme tolte.
  >
  > **⚠️ Fuori pista**:
  > - Il pin `test_full_planner_schema_fingerprints_are_frozen`
  >   (`test_pac_planner_schemas.py:2630-2643`) va aggiornato ai due fingerprint nuovi: è voluto,
  >   lo schema della prova è cambiato. Va nel lotto del test-author.
  > - Due testi da portare in R7, non corretti qui:
  >   - con un limite, il suggerimento `floatingUnfinished` dice «miglior piano trovato» anche per
  >     `ready_no_incumbent`, dove nessun piano è pubblicato;
  >   - l'avviso di limite di `StateNotice` per `no_incumbent` dice «nessun piano trovato» anche
  >     quando SCIP ne aveva uno e il replay lo ha respinto.
- **F6 — verifica.** ✅ 2026-09-29
  - Suite su 6151, `front check` e build.
  - Smoke S2, S2b e S2c più un caso X2 sulla copia 6161.
  - Copia rinfrescata prima della review.

  > **Note implementazione** (2026-09-29):
  > - Identità: a HEAD `f6d7a955d` i 22 blob coincidono con `/tmp/libreFolio_commits/d-f5-qx1b.sha8`
  >   (`/tmp/libreFolio_d_f6_head_sha8.log`).
  > - `front build --debug`: rc 0 in 1 min 12 s, 10:15:47 → 10:17:00
  >   (`/tmp/libreFolio_d_f6_front_build.log`). Il build ha rigenerato il client: `openapi.json`
  >   alle 10:15:54, `generated.ts` alle 10:15:57, i contratti dei tool alle 10:15:59. Il suo
  >   svelte-check è al pavimento 3/41/4, nessun file PAC.
  > - `front check` (client delle 10:15:57): rc 1 allo stesso pavimento, 3 errori e 41 warning in
  >   `BrokerSharingPanel`, `GlobalSettingsTab`, `TransactionFormModal.test`, `ToolExecutionMetrics`
  >   (`/tmp/libreFolio_d_f6_front_check.log`).
  > - Stile, tutto pulito:
  >   - `prettier --check` sui 65 file PAC del frontend e sui 4 cataloghi;
  >   - `dev.py lint` (ruff, tutto il backend);
  >   - `black --check` sui 30 file Python del PAC.
  > - Suite su 6151 (`/tmp/libreFolio_d_f6_gates.sh`, 10:18:32 → 10:21:08), tutte rc 0 e con i
  >   conteggi del gate del commit 5 (`/tmp/libreFolio_d_f6_gates_summary.log`):
  >
  >   | Categoria | Suite | Passati |
  >   |---|---|---|
  >   | services | pac-planner-core / -evaluator / -oracle / -policies / -solver | 152 / 159 / 20 / 40 / 19 |
  >   | services | pac-planner-proof / -wire-numbers / -report / -service | 30 / 39 / 18 / 31 |
  >   | services | tools-registry | 93 |
  >   | schemas | pac-planner / tools | 467 / 271 |
  >   | api | pac-planner-tool / tools | 6 / 7 |
  >   | front-utility | core-unit / component-unit | 2647 (98 file) / 2119 (86 file) |
  >
  > - Smoke Playwright usa-e-getta sulla copia 6161 (`/tmp/libreFolio_d_f6/smoke_pac.mjs`, esito
  >   in `/tmp/libreFolio_d_f6/smoke/report.json`, con request, response e screenshot di ogni
  >   scenario): **5/5**, 0 errori di console, 0 page error, 0 risposte 4xx/5xx.
  >   - Hub `ready`, 0 degradati, 0 interfacce mancanti, «Backend/API 2.0.0 · UI 2.0.0».
  >   - Ogni scenario: `ready_incumbent`, `optimal_proven`, stop `completed`, replay Decimal
  >     verificato, i 5 stadi SCIP `finished`. Risposte fra 0,62 e 0,70 s, compute 14–20 ms.
  >   - S2, S2b (mobile) e S2c: esiti nella tabella del runbook (Passo E). S2c non va più in
  >     errore: X1 è curato anche sulla UI.
  >   - X2 (fee col minimo) e il caso del top-up QX1-b sono le righe nuove S18 e S17 del runbook.
  >     Sul top-up la condizione del coordinator è verificata sul risultato pubblicato: 3 unità e
  >     0,01 € da aggiungere (`rounding_top_ups`, `rounded_postings` 1), non sulla strada interna.
  >   - Privacy ON su S2: le istruzioni diventano «buy ••• units», gli importi dei KPI sono
  >     mascherati, «Ordini 2» resta in chiaro (voce già in R7); OFF ripristina.
  > - Copia rinfrescata dopo lo smoke: la vecchia, `/tmp/librefolio-r2-d-prodcopy.prev-20260929-102854`,
  >   è cancellata alle 10:38 su richiesta del coordinator (dati reali, non servono più); utenti = 1,
  >   solo quello del developer.
  > - Server di review su 6161, PID 70702, avviato alle 10:30:40: health 200, `/tools/catalog`
  >   senza auth → 401 (`/tmp/libreFolio_d_f6/server_review.log`). Serve dal disco il build di HEAD
  >   delle 10:39:27 (vedi F7).
  >
  > **⚠️ Fuori pista**:
  > - **Esperimento dichiarato**, come il 24/09: superuser usa-e-getta `pac_smoke` (ID 2), creato
  >   dopo un `list` che mostrava solo l'ID 1, con una password casuale tenuta solo nell'ambiente del
  >   processo e mai scritta. Il refresh lo ha tolto. S3, S4 e S16, che richiedono i dati reali,
  >   restano al runbook del developer.
  > - **Flag dei server della copia**, diversi dal comando del Passo E:
  >   - `--host 127.0.0.1`, perché la copia contiene dati personali;
  >   - `--no-scheduler`, anche per la review, così prezzi e date restano fermi: S3 mostra l'età
  >     vera dei dati e S16 si confronta con la pagina Allocazione a parità di prezzi;
  >   - `--no-reload`.
  >
  >   Se il developer vuole lo scheduler, o la review da un telefono sulla LAN, riavvio a richiesta.
  > - All'avvio c'è un warning dal download di MathJax dal CDN (errore SSL): ambientale, fuori dal PAC.
  > - Il repo non ha E2E del PAC (arriva dopo lo STOP, §4 punto 7): la verifica UI è lo smoke.
  > - Nuovo per la review R3, sulla schermata S17: U = −0,005 € (investiti 100,005 € contro 100,00),
  >   mentre il saldo finale è −0,01 € (addebito 100,01 arrotondato HALF_UP) e la riga «Rounding» del
  >   ledger vale 0,005 €.
- **F7 — nessun titolo della scheda nelle pagine Tools** — ~~a D~~ **riassegnato a K il 29/09**
  (coordinator). Il motivo: il cambiamento è uno solo, cioè nessuna pagina imposta più un titolo.
  Tocca File, le pagine Tools, il reset di `+layout.svelte` (che diventa codice morto),
  `document-title.spec.ts` e `layout.gate.test.ts`. Diviso fra due rami sarebbe un conflitto
  certo sullo stesso spec e sulla sua intestazione, e il comportamento arriverebbe spezzato in due
  integrazioni. Il ramo di D non ha mai toccato le pagine Tools, quindi la modifica di K non
  entra in conflitto con D.
  - ~~`tools/+page.svelte:6-8` e `tools/[tool_code]/+page.svelte:9-11` tolgono il blocco
    `<svelte:head><title>` («Tools · LibreFolio»), e con lui l'import di `t`, che resta senza uso.~~
  - ~~La chiave `tools.title` resta: la usano `Sidebar.svelte:41`, `ToolsHub.svelte:151`,
    `ToolHost.svelte:240-249` e `ToolAboutPanel.svelte:242`. Nessuna modifica i18n.~~ (Dato
    passato a K col messaggio al coordinator.)
  - ~~Test: il caso 3 di `e2e/layout/document-title.spec.ts` («una pagina col proprio titolo lo
    rimette dopo Files», `:139-158`) ha per premessa il titolo di Tools. Diventa obsoleto per
    decisione di prodotto, non per un difetto. Il test-author lo toglie, riallinea l'intestazione e
    aggiunge la regressione: le pagine Tools lasciano il titolo di default. Il nuovo caso non passa
    da Files, così regge anche quando K toglie il titolo di Files.~~ Anche la descrizione del
    runner (`_frontend_utility.py:527`, «Tools still sets its own») è di K.
  - ~~`+layout.svelte:57-64` (il reset) resta, finché non sono entrati sia D sia K. Il commento di
    `layout.gate.test.ts:19` («Only Files and Tools set a title») diventa inesatto: lo lascio a chi
    toglierà il reset, perché anche K lo rende inesatto.~~
  - ~~Gate: `front check` al pavimento; prettier sui file toccati; `front build --debug`, poi l'E2E
    `document-title.spec.ts` su 6151. Il build riscrive `frontend/build`, servito dalla 6161 della
    review: si fa quando il developer non la sta usando.~~

  > **⚠️ Fuori pista** (2026-09-29):
  > - Prima del cambio di assegnazione avevo già tolto i due blocchi `<title>` e lanciato
  >   `front build --debug` (10:36:33 → 10:37:48, rc 0, `/tmp/libreFolio_d_f7_front_build.log`).
  >   Nessun test lanciato e nessun test-author coinvolto.
  > - Ripristino con l'edit tool, non con `git checkout`: `git diff --quiet HEAD --` sui due file
  >   → 0, blob uguali a HEAD (`5b86893a`, `4d51cfb5`).
  > - `front build --debug` rilanciato (10:38:14 → 10:39:27, rc 0,
  >   `/tmp/libreFolio_d_f7_front_build_restore.log`). La 6161 (stesso PID 70702) serve di nuovo
  >   HEAD: i chunk delle pagine Tools (`nodes/13`, `nodes/14`) contengono di nuovo
  >   «· LibreFolio» e rispondono 200.

### ⛔ STOP — review di dettaglio col developer

Ogni tema matematico si guarda **sulla schermata della UI che lo espone**, sui dati del developer:

| # | Tema | Contenuto |
|---|---|---|
| R1 | Modello di input e unità | Liquidità, broker, asset, routing: cassa per valuta, contributi separati, passo di quantità, importo, fee, provenance e staleness. Reperti N10, N13, N14, N16, N21. **Da confermare:** la lettura prudente di Q-C0-2 (nessuna somma di importi in UI) e il default del tetto delle route (`1000000000`). |
| R2 | Normalizzazione e issue | 79 codici; `needs_input` / `invalid` / `unsupported`. N1 chiuso da Q-C0-4 (C0b.2); esposizioni oltre il 100% → `invalid` (C0b.3). Reperti N11, N12, N17, N20. |
| R3 | Evaluator esatto e ledger | Decimal/ExactRatio; arrotondamenti (storia del difetto HALF_UP); spread FX applicato una volta sola; le fee non sono investimento; niente doppio conteggio della cassa. **QX1-b (25/09)** cambia il ledger: un piano può chiudere una cassa sotto zero di al più `N` unità minime, con l'importo da aggiungere. MathematicalCore §22 chiede per questo una review matematica: si fa qui, sulla schermata della nota, insieme al conteggio di `N` (crediti FX inclusi). |
| R4 | Cascata obiettivi | L2 fixed → U → priorità → fee → righe → tie-break; cosa significano L2 (EUR²) e U. |
| R5 | Ricerca e prova | ~~Oracolo fino a 200 000 = dimostrato; SCIP oltre = `not_proven`; infeasible solo dall'oracolo;~~ **D-X1 (24/09):** SCIP unico; `optimal` su tutti gli stage = ottimo, `infeasible` sul primo = impossibile, limite = tempo scaduto; l'oracolo resta nei test. Determinismo = `completed`; budget di 30 s; **domanda aperta sul numero di asset** (ginocchio ≈ 18 asset multi-valuta). Le soglie crescenti per il tetto delle route (Q-C0-5) entrano nella stessa misura. **🔴 X1 (24/09):** la premessa «fino a 200 000 = dimostrato» valeva solo fino a circa 13 000 candidati (≈ 3,3 ms ciascuno contro la soft deadline di 44 s); fra 13 000 e 200 000 il job moriva con `execution_limit`. ~~Opzioni: sotto-budget dell'oracolo con fallback a SCIP; tetto tarato sul tempo; funding e FX dedotti invece che enumerati; evaluator più veloce.~~ Chiuso da D-X1, Passo F. |
| R6 | Report e spiegazioni | `buffer = 0`, deployment omesso, ~~`describe_conclusion` non usato~~ (tolto nel commit 4, decisione del developer del 28/09), freshness non riportata: cosa mostrare. Reperti N19, N23. |
| R7 | UI risultati e privacy | Tabella campo per campo personal/public/strutturale, **quantità incluse**; tetti e minimi delle route (default mascherati); input in chiaro durante la scrittura. Voci nuove dello smoke: «1 units» senza plurale; L2 nella locale del browser (`format.ts:185`); titolo del contributo con etichetta vuota; testimone «9,018» contro «2212»; valori floating degli stage con tutte le cifre; numero di ordini in chiaro con privacy ON (da confermare). **Voce nuova del 29/09**, trovata preparando la lista per il developer: la copia della distribuzione rimanda a «i valori della pagina Allocazione» e «i pesi differiscono dalla pagina», in tutte e 4 le lingue (`tools.pacAllocator.planner.distribution.source` / `.differs`, `DistributionDialog.svelte:98,118`). Quella pagina non esiste: è il pannello «Allocazione Patrimoniale» della Dashboard (`AllocationPanel.svelte:68`). Nessuna correzione prima della review. |
| R8 | Registro decisioni | E la prossima fetta (§4). |
| R9 | Toast di `ToolsHub` | Un `renderer_missing` atteso non merita un toast (`notify.svelte.ts:53-55`): correggerlo ora o metterlo in backlog. |
| R10 | Stadi di tie-break e stop (latente, da prima di D-X1) | L'evidenza sul filo toglie gli stadi `tie:*` (`planner_report.py:814`), ma `build_stop_reason` li legge (`planner_report.py:910-913`). Se il budget finisce durante un tie-break, lo stop è `time_limit` mentre il filo non mostra alcuno stadio non terminato: `_validate_stop_evidence` (`schemas/pac_allocator.py:2125-2127`) alza un errore e il piano diventa un errore del tool, invece di un `not_proven` onesto. La finestra è stretta, ma con D-X1 ogni piano passa da SCIP. Opzioni: (a) un campo sul filo che dica che il tie-break è stato troncato; (b) contare lo stop solo sugli stadi pubblicati, ma allora `completed` non vorrebbe più dire «riproducibile»; (c) pubblicare anche gli stadi di tie-break, allargando `ObjectiveCode`. Da decidere; nessuna correzione nel commit 4. |

### Iterazione UI col developer — passi 1 (Scenario) e 2 (Liquidità) ⏳ 2026-09-29, in attesa del suo feedback

Il developer guarda la 6161 e scrive direttamente a D. Chiede di migliorare la UI dei passi 1 e 2, **senza test automatici**, e di fargliela vedere subito.

**Cosa ha segnalato:**
- in Strumenti c'è solo il PAC;
- Scenario: la data è più bassa del selettore di valuta, e non è chiaro a cosa serva; il banner «Nessun valore finanziario in questo passo.» non ha senso;
- Liquidità:
  - vuole l'icona del Broker nella copia;
  - un clic in qualsiasi punto della riga deve selezionarla e colorarla tutta;
  - i due avvisi della copia non sono chiari, e ne compare uno su Recrowd, che non aveva selezionato;
  - non si capisce la differenza fra «Contributo» e «Conto manuale».

- ✅ 2026-09-29 — **modifiche fatte; la build è sulla 6161.**

  > **Note implementazione** (2026-09-29). Tutti i file sono sotto `frontend/src/lib/features/tools/pac-allocator/planner/`.
  >
  > **Scenario** (`steps/ScenarioStep.svelte`):
  > - tolto il banner (`scenario.noValues` rimossa);
  > - la valuta usa `CurrencySearchSelect compact`, alta quanto un input, e la data non ripete l'etichetta interna;
  > - due spiegazioni: `scenario.asOfHint` (a cosa serve la data) e `scenario.currencyHint`;
  > - nuova introduzione `scenario.intro`, che spiega il PAC puro e dice che è una simulazione.
  >
  > **Liquidità** (`steps/LiquidityStep.svelte`, `ui.ts`: `CHOICE_CARD`, `ICON_BUBBLE`):
  > - un'introduzione e tre schede-fonte al posto dei tre pulsanti, testid invariati:
  >   - «Dai tuoi Broker»;
  >   - «Nuovo versamento»;
  >   - «Conto esterno»;
  > - ogni scheda porta un'icona e una frase che la distingue dalle altre;
  > - le card della liquidità mostrano l'icona del Broker (`BrokerIcon`, con i campi letti da `getBrokerInfo`); la card del versamento mostra un salvadanaio.
  >
  > **Finestra di copia** (`steps/BrokerScopeCopyDialog.svelte`, `scope.ts` con `iconUrl`/`portalUrl`/`pluginCode`):
  > - ogni riga selezionabile è un'unica `<label>`, quindi un clic ovunque la seleziona;
  > - la riga selezionata è verde per intero (`data-selected`);
  > - le righe bloccate hanno un bordo tratteggiato e l'icona grigia.
  >
  > **Avvisi della copia** (`shared/CopyNotice.svelte`, `format.ts` con `formatPlannerClock`):
  > - il riepilogo usa il plurale ICU;
  > - «copiati alle HH:mm» se la copia è di oggi, altrimenti data e ora;
  > - l'issue del profilo di esecuzione diventa **una sola frase informativa** con i nomi dei Broker, senza tono di avviso.
  >
  > **Terminologia**, solo i valori e non i nomi delle chiavi:
  > - «contributo» → «versamento» (FR «versement», ES «aportación»);
  > - «conto manuale» → «conto esterno» (FR «compte externe», ES «cuenta externa»);
  > - allineate anche 6 chiavi degli altri passi che usavano i vecchi termini (`brokerEditor.noFunding`, `issues.allocation.negative_contribution`, `problems.*` ×3, `summary.contributions`).
  >
  > **i18n**, solo con `dev.py i18n`, da `/tmp/libreFolio_d_ui12/i18n_apply.py` (log `i18n_apply.log`):
  > - 7 chiavi aggiunte, 29 aggiornate, 1 rimossa; da 4103 a 4109 chiavi per lingua, insiemi identici;
  > - valori riletti uguali al copione (0 differenze);
  > - le stringhe ICU nuove sono formattate con `intl-messageformat` nelle 4 lingue (log `icu_check.log`).
  >
  > **Build**:
  > - `front build --debug`, dalle 13:21:19 alle 13:22:35, rc 0, log `/tmp/libreFolio_d_ui12/build.log`;
  > - la 6161 (PID 70702, invariato) serve il chunk con i testid nuovi; health 200.
  >
  > **Nessun test eseguito** e nessun test-author coinvolto, su richiesta del developer.

  > **⚠️ Fuori pista** (2026-09-29):
  > - **Recrowd non selezionato.** `BrokerScopeCopyDialog` legge la fonte per tutti i Broker posseduti, e `outcome()` copiava tutte le `source.issues`. Ora `selectedBrokerIssues` (`copies.ts:35`) tiene solo le issue senza entità o di un Broker selezionato. La usano `applyBrokerCopy` e `applyLiquidityCopy` (`copies.ts:152,170`).
  > - **Profilo di esecuzione.** Il backend imposta `execution_profile_status="not_available"` per ogni Broker (`portfolio_allocation_source.py:727`) ed emette `allocation.broker_execution_profile_unsupported` con severità `error` (`:743-752`): il DB non ha né fee né modalità d'ordine. Il backend non è stato toccato; la UI la presenta come informazione (`CopyNotice.svelte:32-44`).
  > - **Un solo tool.** In `backend/app/services/tool_plugins/` c'è solo `pac_allocator.py`: non è un difetto.
  > - **`svelte-check`**, lanciato dalla build `--debug`: 3 errori e 41 warning in 4 file, **nessuno nel planner**. Gli errori sono in `features/tools/components/ToolExecutionMetrics.svelte:44` (piattaforma C) e `TransactionFormModal.test.ts:787,819`. Sono preesistenti (file non toccati) e fuori perimetro; segnalati al coordinatore.
  >
  > **Debito di test**, per il test-author, dopo il feedback:
  > - le issue filtrate sui Broker selezionati;
  > - la frase del profilo e il plurale in `CopyNotice` (~~`sameDay`~~: tolto nel round 2);
  > - il clic sulla riga e `data-selected`;
  > - ~~`formatPlannerClock`~~: rimossa nel round 2, sostituita da `formatCopyStamp`.
  >
  > **Follow-up** per coerenza, non fatti:
  > - `DistributionDialog` mostra ancora l'issue grezza del profilo;
  > - `OwnerBrokerPicker` ha ancora le righe vecchie;
  > - le chiavi legacy `tools.pacAllocator.*` fuori da `planner.` sembrano morte: verificarle con l'audit i18n.

#### Round 2 — secondo feedback del developer ⏳ 2026-09-29, in attesa del suo feedback

**Cosa ha chiesto:**
- Scenario: le spiegazioni non a schermo, ma in un `Tooltip` dietro un'icona «?»;
- avviso della copia: togliere «Non si aggiornano da soli…»; solo un badge con data e ora, **solo la data** se i dati sono di un giorno prima di oggi;
- una domanda: la data di riferimento ha senso? La sua idea era rileggere i prezzi correnti subito prima del calcolo e lasciare i manuali come sono (vedi «Decisione aperta» sotto);
- un pulsante «Tutto» accanto a «Importo da usare»;
- versamento: l'etichetta nel titolo, modificabile, numerata «Nuovo versamento 1, 2, …»;
- conto esterno: la valuta nel titolo a 3 lettere, con `currencyFormat.ts` e le regole di design del progetto;
- le card nell'ordine dei clic, riordinabili con `OrderableList`.

- ✅ 2026-09-29 — **modifiche fatte; la build è sulla 6161.**

  > **Note implementazione** (2026-09-29). Tutti i file sono sotto `frontend/src/lib/features/tools/pac-allocator/planner/`.
  >
  > **Scenario** (`steps/ScenarioStep.svelte`, `ui.ts` con `HELP_BUTTON`):
  > - le due spiegazioni sono in un `Tooltip` (`components/ui/feedback/Tooltip.svelte`) dietro un pulsante «?» (`CircleHelp`) accanto all'etichetta;
  > - testid `pac-planner-scenario-date-help` e `-currency-help`; i vecchi `-hint` non esistono più;
  > - l'`aria-label` del pulsante contiene etichetta e spiegazione;
  > - l'introduzione resta a schermo.
  >
  > **Badge della copia** (`shared/CopyNotice.svelte`, `format.ts` con `formatCopyStamp`):
  > - la frase `copyNotice.when` è tolta;
  > - accanto al riepilogo c'è un badge (`BADGE.neutral`, icona `Clock`, testid `…-stamp`):
  >   - dati di oggi: data e ora della copia;
  >   - dati di un giorno precedente, o ora illeggibile: solo la data;
  >   - «oggi» è `defaultAsOf(now)`;
  > - il `title` del badge usa `copyNotice.stamp`;
  > - lo stesso testo compare nell'`OriginBadge` della card di cassa copiata;
  > - `formatPlannerClock` è rimossa: il suo unico uso era `CopyNotice`.
  >
  > **`defaultAsOf`** passa da `draft.svelte.ts` a `defaults.ts`: serve a `format.ts` senza creare un ciclo. Non ha altri importatori.
  >
  > **«Tutto»** (`steps/LiquidityStep.svelte`, testid `pac-planner-cash-use-all`):
  > - un `BUTTON_SECONDARY` accanto a «Importo da usare» copia `available` in forma canonica;
  > - disabilitato se il disponibile non è un numero positivo;
  > - vale sia per la cassa copiata sia per il conto esterno;
  > - per un Broker in quota parziale «Tutto» è l'intera custodia, cioè il massimo che il backend accetta (`normalize.py:443-449`).
  >
  > **Versamento**:
  > - il titolo si modifica sul posto: un input dentro l'`<h3>` (`ui.ts` con `TITLE_INPUT`), con una matita `PenLine` che si accende al passaggio; testid invariato `pac-planner-contribution-label`;
  > - il campo «Etichetta» esce dalla griglia, che resta con 2 colonne (importo e valuta);
  > - l'importo non ha più il suffisso di valuta, perché il selettore della valuta è accanto;
  > - nome predefinito da `contribution.defaultLabel`, «Nuovo versamento {n}», con n = numero di versamenti + 1; i nomi già presenti vengono saltati.
  >
  > **Valuta nel titolo** (`shared/CurrencyCode.svelte`, nuovo):
  > - rende `formatCurrencyCodeHtml`: simbolo, bandiera e codice ISO a 3 lettere, la regola di progetto già usata da WAC e dal Bulk modal;
  > - si ridisegna con `currencyStoreVersion` e carica il catalogo con `ensureCurrenciesLoaded($currentLanguage)`;
  > - è usata nei titoli di cassa e di conto esterno e come unità in «Liquidità dichiarata» e «Importo da usare»;
  > - `cash.title` e `cash.manualTitle` non contengono più `{currency}`.
  >
  > **Ordine** (`draft.svelte.ts`: `LiquidityEntry`, `liquidityEntryKey`, `liquidityOrder`, `liquidityEntries`, `reorderLiquidity`, `forgetLiquidityEntry`):
  > - cassa e versamenti sono un'unica `OrderableList`: si trascina su desktop, si usano le frecce su mobile;
  > - prima l'ordine scelto dall'utente, poi le card restanti per `enteredAt`, cioè nell'ordine dei clic;
  > - l'ordine sta **fuori da `data`**: riordinare non cambia l'impronta della richiesta e non rende vecchio un risultato;
  > - `reset` lo svuota; una card rimossa perde il suo posto.
  >
  > **i18n**, solo con `dev.py i18n`, da `/tmp/libreFolio_d_ui12/i18n_round2.py` (log `i18n_round2.log`):
  > - 4 aggiunte: `cash.useAll`, `cash.useAllHint`, `contribution.defaultLabel`, `copyNotice.stamp`;
  > - 2 aggiornate: `cash.title`, `cash.manualTitle`;
  > - 1 rimossa: `copyNotice.when`;
  > - da 4109 a 4112 chiavi per lingua, insiemi identici, 0 differenze dal copione (`verify_round2.log`);
  > - ICU formattato nelle 4 lingue (`icu_check_r2.log`).
  >
  > **Build**:
  > - `front build --debug`, rc 0, log `/tmp/libreFolio_d_ui12/build2.log`;
  > - svelte-check dà gli stessi 3 errori preesistenti fuori dal planner, e nessun warning nel planner;
  > - la 6161 (PID 70702) risponde 200 su health e sulla pagina del tool; il chunk contiene i testid nuovi e nessun riferimento ai vecchi.
  >
  > **Nessun test eseguito**, su richiesta del developer.

  > **⚠️ Fuori pista** (2026-09-29):
  > - **`LiquidityStep.svelte` riscritto per intero** invece che con modifiche mirate, e il sorgente del round 1 non era salvato. L'ho recuperato dalla sourcemap della build di debug (`sourcesContent` di `build/_app/immutable/chunks/O4vLtp2c.js.map`) e l'ho confrontato con la riscrittura: le differenze sono solo quelle volute.
  > - **Scheduler e prezzi correnti**, per la domanda sulla data:
  >   - lo scheduler è attivo per default e aggiorna i prezzi correnti ogni 10 minuti, per gli asset attivi con un provider;
  >   - il percorso è `services/scheduler/jobs.py:38` `run_current_price_refresh` → `get_current_prices_bulk`, che scrive OHLC; le impostazioni sono in `schemas/settings.py:300-309`;
  >   - quindi una lettura del DB dà già l'ultimo prezzo corrente, senza che il planner chiami un provider o scriva.
  > - **`OrderableList` e input.** L'intera riga è `draggable`: in Firefox trascinare il mouse dentro un input di una riga trascinabile può non selezionare il testo. `ChartSignalsSection` usa già lo stesso schema con degli input. Da osservare nel feedback.
  >
  > **Debito di test**, in aggiunta:
  > - `formatCopyStamp`: dati di oggi → data e ora; giorno precedente → solo data; ora illeggibile → solo data;
  > - «Tutto»: valore canonico; disabilitato se il disponibile è vuoto o non positivo;
  > - titolo modificabile e numerazione predefinita, che salta i nomi presi;
  > - `CurrencyCode`, con catalogo caricato e non caricato;
  > - `liquidityEntries`: ordine dei clic, riordino, rimozione, `reset`, e riordino che non cambia l'impronta.
  >
  > **Follow-up**, non fatti:
  > - `BrokerEditor` mostra ancora «etichetta · versamento» (`contribution.kind`);
  > - gli `OriginBadge` degli altri passi usano ancora `formatPlannerTimestamp`;
  > - i titoli delle frecce di `OrderableList` sono fissi in inglese: componente condiviso, fuori perimetro.

  > **Decisione — la data di riferimento ✅ 2026-09-29: opzione 2**, scelta dal developer (`ask_user`: «Opzione 2: tolgo la data e rileggo i dati copiati prima di Calcola»). L'esecuzione è il Round 3, sotto. Le opzioni restano qui come traccia.
  >
  > Con lo scheduler attivo, «rileggere l'ultimo prezzo corrente» è una lettura del DB. Le opzioni:
  > 1. **Minima**, circa mezza giornata, solo frontend:
  >    - il campo data sparisce, e «oggi» è fissato in automatico alla copia e al calcolo;
  >    - i prezzi manuali perdono la data;
  >    - quelli copiati tengono la loro, con l'etichetta di età;
  >    - backend e contratto restano invariati.
  > 2. **Consigliata**, circa una giornata più i test: l'opzione 1, più una rilettura subito prima di «Calcola»:
  >    - si rileggono da LibreFolio (`POST /portfolio/allocation-source`, una lettura del DB senza provider e senza scritture) prezzi, FX e cassa copiati e non modificati, e si aggiornano;
  >    - i valori modificati e quelli manuali restano, senza finestra di conflitto;
  >    - servono una fase «occupato» e una politica per gli errori;
  >    - backend e contratto restano invariati;
  >    - resta coerente col «draft protetto da sovrascritture»: non è un legame live, è un aggiornamento su un'azione dell'utente.
  > 3. **Chiamata live ai provider** (`POST /assets/prices/current`) prima del calcolo, circa 2 giorni:
  >    - scrive OHLC di oggi durante una simulazione, contro la decisione chiusa «/assets/prices/current … non innocente auto-prefill»;
  >    - la risposta non ha `quote_base_quantity`, quindi servono una modifica al backend e un `api sync`;
  >    - aggiunge latenza e guasti dei provider;
  >    - rispetto alla 2 guadagna poco, visto lo scheduler.
  > 4. **Lasciare com'è.**
  >
  > Qualunque cambio va al coordinatore, perché 05, 06 e la guida lo registrino.

#### Round 3 — data automatica e rilettura prima di «Calcola» ⏳ 2026-09-29, in attesa del feedback del developer

Decisione del developer: opzione 2 (sopra). Solo frontend del planner: backend, contratto `2.0.0` e client generato restano invariati.

**Passi:**
- R3.1 ✅ 2026-09-29 — `as_of` automatico:
  - `draft.refreshAsOf()` fissa `data.asOf = defaultAsOf()`; si chiama prima di ogni lettura di copia e all'inizio di «Calcola»;
  - il campo data esce dallo Scenario, e la data esce dal riepilogo e dal passo Revisione;
  - i testi che citano la data della copia la perdono; le chiavi rimaste senza uso si tolgono con `dev.py i18n`.
- R3.2 ✅ 2026-09-29 — prezzi dell'utente senza data:
  - `AssetEditor` perde il campo data;
  - un prezzo manuale, o copiato e poi modificato, parte con `reference_date = as_of` e `fresh`;
  - i controlli sulla data del prezzo valgono solo per i prezzi copiati e non modificati;
  - l'etichetta di età sparisce per prezzi e cambi modificati; i conteggi «non del giorno» contano solo i fatti copiati e non modificati (`review.ts`, `draft.svelte.ts`).
- R3.3 ✅ 2026-09-29 — `refreshCopiedFacts` in `copies.ts`:
  - una sola `POST /portfolio/allocation-source` per prezzi (`assets`, `prices`), saldi (`brokers`, `cash_balances`) e cambi (`fx_quotes`), solo per i fatti copiati e non modificati;
  - `broker_ids`: i Broker di proprietà (`loadCopyScope`) più quelli delle casse copiate. Un Broker non più tuo dà 403, mai un taglio silenzioso;
  - aggiorna valore, base copiata, timbro e fonte. Non aggiunge righe e non tocca «Importo da usare», classificazioni, distribuzione né Broker;
  - una riga assente lascia il valore di prima e viene contata come «non trovata».
- R3.4 ✅ 2026-09-29 — fase di rilettura prima del calcolo:
  - la vista del risultato mostra la rilettura in corso, con «Interrompi attesa», che riporta alla Revisione;
  - se la rilettura fallisce, un pannello offre «Riprova», «Calcola con i dati copiati» (consenso esplicito) e «Modifica configurazione»;
  - dopo la rilettura, una riga sopra il risultato dice quanti prezzi, cambi e saldi sono cambiati e quanti non sono stati trovati;
  - se la rilettura porta «Importo da usare» sopra il disponibile, il calcolo si ferma col problema locale che già esiste.
- R3.5 ✅ 2026-09-29 — i18n, `front build --debug`, verifica sulla 6161. Nessun test automatico.
- R3.6 ⏳ — feedback del developer su round 2 e round 3.

  > **Note implementazione** (2026-09-29):
  >
  > **Data** (R3.1, R3.2):
  > - `draft.refreshAsOf()` fissa `data.asOf = defaultAsOf()`, cioè il minimo fra data locale e data UTC, perché `normalize.py:215` rifiuta un `as_of` dopo la data UTC dello snapshot. Si chiama in `SourceCopyDialog.copy()`, `BrokerScopeCopyDialog` (`onMount`), `DistributionDialog.read()` e all'inizio di `calculate`;
  > - `priceIsCopied` e `rateIsCopied` (`draft.svelte.ts`) dicono se un fatto è ancora uguale alla sua copia. Solo questi fatti portano la data della fonte, l'etichetta di età e i conteggi «non del giorno» (`review.ts`, `AssetsStep`, `AssetEditor`, `FxStep`);
  > - `request.ts`: un prezzo copiato e non modificato manda la sua data; uno manuale o modificato manda `data.asOf`. I tre problemi sulla data sono tolti;
  > - tolti il campo data da `ScenarioStep` (resta solo la valuta, col suo `?`), la riga data dal riepilogo e dalla Revisione, il campo data da `AssetEditor` (griglia prezzo a 3 colonne).
  >
  > **Rilettura** (R3.3, `copies.ts`, sezione «Re-read before «Calcola»»):
  > - `refreshPlan` raccoglie gli id degli asset con prezzo copiato e non modificato, i Broker delle casse copiate e le coppie FX copiate e non modificate; `null` se non resta nulla, e allora non si legge niente;
  > - `refreshQuery` fa una sola lettura: le sezioni servono solo per i tipi presenti; `broker_ids` = Broker di proprietà ∪ Broker delle casse copiate, quindi un Broker non più tuo dà 403 e mai un taglio silenzioso; `asset_ids` esplicito, anche vuoto (lo schema accetta `[]`);
  > - `refreshCopiedFacts` ricontrolla la condizione «non modificato» al momento di applicare, così una modifica fatta durante la lettura non viene sovrascritta. Crea al più un `CopyRecord` per tipo, e chiude con `pruneCopies`;
  > - «cambiato» ignora la data per i prezzi (`sameQuote`) e guarda solo il tasso per l'FX: un fatto con la sola data nuova conta come invariato, ma prende timbro e data nuovi;
  > - cassa: si abbina per `source_broker_id` e valuta; aggiorna disponibile, quota e importo economico, e confronta anche la quota. Il disponibile di una cassa copiata non è modificabile dall'utente (`LiquidityStep.svelte:166-175`), quindi la rilettura non può sovrascrivere una sua modifica;
  > - non tocca mai «Importo da usare» e non aggiunge righe. Una riga assente lascia il valore copiato e finisce in `missing`, col nome dell'asset, la coppia o «Broker · valuta»;
  > - distribuzione e classificazioni non si rileggono: sono basi dell'utente.
  >
  > **Fase di rilettura** (R3.4, `PacPlannerTool.svelte`):
  > - `calculate`: `refreshAsOf` → problemi locali (se ci sono, alla Revisione) → rilettura → `buildRequest`, che riesegue i problemi locali. Così un saldo sceso sotto «Importo da usare» ferma il calcolo alla Revisione, con la riga della rilettura sopra;
  > - `refreshCopies` usa un contatore di sequenza: «Interrompi attesa», un nuovo «Calcola» o lo smontaggio la superano. Proprietari da `loadCopyScope`; errori con le chiavi esistenti `copy.scopeError` e `copy.noOwner`, oppure con quello della lettura;
  > - `BusyPanel` ha `phase` (`refresh` | `compute`, `data-phase`) e il riepilogo della richiesta solo in fase di calcolo;
  > - nuovo `result/RefreshFailedPanel.svelte`: «Riprova», «Calcola con i dati copiati» (`calculate({refresh: false})`), «Modifica configurazione»;
  > - nuovo `result/RefreshNotice.svelte`: quanti prezzi, cambi e saldi sono cambiati, oppure «nessun valore è cambiato», più i non trovati, che la rendono un avviso. Sta sopra il risultato se l'impronta coincide con quella della richiesta, e nella Revisione solo se il calcolo si è fermato lì;
  > - `runState` aggiunge `refreshing` e `refresh_failed`; `data-busy` e `aria-busy` valgono anche durante la rilettura;
  > - `retry()` dopo un errore della piattaforma rimanda la stessa richiesta senza rileggere;
  > - `CopyNotice`: il `title` del badge dice, per prezzi, cambi e liquidità, che i valori non modificati si rileggono prima del calcolo.
  >
  > **i18n**, solo con `dev.py i18n`, da `/tmp/libreFolio_d_ui12/i18n_round3.py` (log `i18n_round3.log`, 24 operazioni con rc 0):
  > - 11 aggiunte: `busy.refreshing`, `refresh.failed.{title,body,retry,proceed}`, `refresh.notice.{summary,prices,fx,cash,unchanged,missing}`;
  > - 6 aggiornate: `copy.sourcePortfolio`, `pricesCopy.source`, `fxCopy.source`, `distribution.source` (senza `{date}`), `age.after`, `copyNotice.stamp` (ICU `select` su `kind`);
  > - 7 rimosse: `scenario.asOf`, `scenario.asOfHint`, `summary.date`, `problems.asOfMissing`, `problems.priceDateMissing`, `problems.priceDateAfterReference`, `assetEditor.priceDate`;
  > - da 4112 a 4116 chiavi per lingua, insiemi identici, 0 differenze dal copione (`verify_round3.log`); ICU formattato nelle 4 lingue, plurali 1/n compresi (`icu_check_r3.log`);
  > - nessun riferimento rimasto alle chiavi rimosse, né import senza uso nel planner.
  >
  > **Build**:
  > - `front build --debug`, rc 0, log `/tmp/libreFolio_d_ui12/build3.log`;
  > - svelte-check: gli stessi 3 errori e 41 warning preesistenti, in 4 file fuori dal planner;
  > - la 6161 (PID 70702) risponde 200 su `/api/v1/system/health` e sulla pagina del tool; i chunk contengono i testid nuovi (`pac-planner-refresh-notice`, `-refresh-failed`, `-refresh-retry`, `-refresh-proceed`, `data-phase`) e nessuno di quelli tolti.
  >
  > **Nessun test eseguito**, su richiesta del developer.

  > **⚠️ Fuori pista** (2026-09-29):
  > - **Tre politiche scelte senza chiedere**, da confermare col feedback: un errore di rilettura blocca e offre le tre scelte; «Importo da usare» non si adegua da solo a un saldo cambiato; un fatto non trovato tiene il valore copiato ed è elencato.
  > - **«Cambiato» senza la data.** `samePrice` confronta anche la data, che per un prezzo copiato cambia ogni giorno: contarla avrebbe dato «1 prezzo aggiornato» a valore identico. Per il conteggio ho aggiunto `sameQuote`, che la ignora.
  > - **Nessuno spec E2E del planner** nel ramo: `e2e/tools/allocation-tool-fixtures.ts` viene dal prototipo del Round 4 (`d66f8e58e`) e nessuno spec la importa. La lettura in più non rompe quindi nessuno spec esistente; la fixture orfana va attribuita con la test-triage nel debito di test.
  >
  > **Debito di test**, in aggiunta:
  > - `refreshPlan`: solo fatti copiati e non modificati; `null` senza niente da leggere;
  > - `refreshQuery`: sezioni per tipo, proprietari ∪ Broker delle casse, `asset_ids` esplicito anche vuoto;
  > - `refreshCopiedFacts`: invariato, aggiornato, non trovato, fatto modificato durante la lettura lasciato stare, «Importo da usare» intatto, nessuna riga aggiunta, sola data nuova contata come invariata;
  > - `request.ts`: data dei prezzi dell'utente (`as_of`) contro quella dei prezzi copiati;
  > - `refreshAsOf` e i conteggi «non del giorno»;
  > - componenti: pannello d'errore (riprova, calcola senza rileggere, modifica), «Interrompi attesa» durante la rilettura, posizione della riga della rilettura;
  > - E2E: copia → «Calcola» con la lettura in più e gli stati `refreshing`/`refresh_failed`.

#### Round 4 — feedback sui passi 3 (Broker) e 4 (Asset) ✅ 2026-09-30 (R4.1–R4.8); R4.9 ⏳ dopo i giri UI

**Feedback del developer** (30/09), in sostanza:
- **Broker, card**:
  - ogni Broker, ovunque compaia, con la sua icona;
  - la card è poco chiara («EUR: Numero di unità · passo 1 unità · Commissione BUY 0 / Conversioni: tasso globale + spread (passo FX) / Funding: cassa locale EUR»): alla valuta manca la bandiera, e «passo» e «numero di unità» non sono spiegati;
  - servono tooltip e info accanto ai parametri.
- **Broker, «Modifica»**:
  - pulsanti, etichette e larghezze disallineati;
  - l'EUR non modificabile va bene, e piace che l'incremento cambi col tipo;
  - la commissione va su una riga a sé, con «BUY» tradotto, info e tooltip;
  - «Aggiungi» va in cima, la scelta della valuta dentro il blocco nuovo, e i blocchi in una `OrderableList`.
- **Funding consentito**: di default tutto spuntato; è l'utente che toglie.
- **Conversione**: manca un selettore «il Broker converte da solo all'acquisto, oppure serve liquidità già in quella valuta».
- **Asset (passo 4)**: ci sono solo «Cerca Asset» e «Asset manuale». Serve una selezione con un clic di tutti gli asset posseduti, filtrati per Broker, come «I tuoi asset» in asset-correlation.
- **Baseline**: «sentiti col coordinatore se serve portare avanti la baseline».
  - Valutazione: non serve. Bastano i componenti di HEAD: `BrokerIcon`, `OrderableList`, `Tooltip`, `CurrencyCode` e le holdings di `POST /portfolio/allocation-source`.
  - Il `LabAssetPicker` del risk-lab non è nella baseline, e non serve.

**R3.6, esito**: il developer non ha commentato i passi 1–2 né le tre politiche del Round 3. Le considero accettate in silenzio e le ricordo nella richiesta di feedback.

**Passi:**
- R4.1 ✅ 2026-09-30 — `shared/PlannerBrokerIcon.svelte`, estratto da `LiquidityStep`. Icona nelle card Broker, nell'editor (titolo e righe di funding), nel routing, in `OwnerBrokerPicker` e nel dialog «I tuoi asset». Le viste del risultato vengono al giro dei risultati.
- R4.2 ✅ 2026-09-30 — card Broker:
  - una riga per valuta, con `CurrencyCode`, «per numero di quote / per importo» e «a multipli di N», ciascuno col suo `?`;
  - commissione di acquisto su una riga a sé, col suo `?`;
  - riga della conversione, col suo `?`;
  - liquidità utilizzabile con le icone.
- R4.3 ✅ 2026-09-30 — editor:
  - «Aggiungi valuta» in cima; il blocco nuovo porta la scelta della valuta;
  - modalità in una `OrderableList`;
  - griglia uniforme: intestazione (`CurrencyCode` e rimuovi), riga tipo + incremento, riga commissione (fissa, %, minimo, massimo), con tooltip.
- R4.4 ✅ 2026-09-30 — funding abilitato di default (`syncFunding`). Una voce tolta dall'utente non torna mai attiva da sola.
- R4.5 ✅ 2026-09-30 — selettore di conversione: deciso dal developer, come passo a sé dopo questo giro (**R4.9**).
  > **Note implementazione**: la prima domanda era impostata male: diceva «solo liquidità già in quella valuta» invece delle due modalità del piano alto. Il developer l'ha corretta: il piano alto aveva due modalità per Broker (`fx_mode`), in `plan-phase00PacRebalancerUiTarget.prompt.md:976-978` e `drafts/pac-rebalancer-end-to-end-design.md:203`, `:375`:
  > - `auto_convert_on_buy`: il Broker converte all'acquisto;
  > - `native_currency_required`: conversione preventiva proposta dal piano.
  >
  > Il 17/09 la **regola 10** del ridisegno FX a 15 regole le ha tolte: nessun campo modalità, conversione sempre esplicita prima del BUY e mai per il SELL (`plan-phase00Step1PacRebalancerContractsCapacity.prompt.md:911-918`; il «retract» di `conversion_mode` e di `PlannerFxAction.handling` sta nel delta-plan di sessione `w1-fx-redesign-final-delta-plan.md:70` e `:74`). Oggi la lista finale tratta quindi ogni conversione come manuale: un passo «FX» prima degli ordini, uno per route d'ordine × valuta sorgente (`OperationalPlan.svelte:31-75`, `PlannerFxAction` in `schemas/pac_allocator.py:1194`).
  >
  > **Decisione del developer (30/09)**: riaprire la regola 10 **come passo a sé subito dopo questo giro UI, con i test**. In questo giro la card dice solo cosa succede oggi.
- R4.6 ✅ 2026-09-30 — «I tuoi asset»:
  - mapping `holdings` in `source.ts`;
  - `steps/OwnedAssetsDialog.svelte`;
  - pulsante in `AssetsStep`.
- R4.7 ✅ 2026-09-30 — i18n con `dev.py i18n`, `front build --debug`, verifica sulla 6161. Nessun test automatico.
- R4.7b ✅ 2026-09-30 — rimesse nei cataloghi le 8 chiavi tolte nei round 1–3, contro la regola (a). Eseguito dopo il RESUME del venv condiviso: vedi il Fuori pista sotto.
  > **Note implementazione**: `/tmp/libreFolio_d_ui12/i18n_restore_r4.py`, 8 × `dev.py i18n add` con rc 0 e i testi di HEAD nelle 4 lingue (log `i18n_restore_r4.log`, 12:44; sha di prima in `i18n_before_r47b.sha`). Confronto con HEAD (`keydiff_r47b.log`): 4103 → 4157 chiavi per lingua, +54, **0 rimosse**, 0 differenze fuori dal planner. ICU di nuovo verde nelle 4 lingue (`icu_check_r47b.log`). Le 8 chiavi vanno nella lista di fine round.
- R4.8 ✅ 2026-09-30 — feedback del developer sui passi 2–4, sulla 6161. Diventa l'ingresso del **Round 5** (sotto).
- R4.9 ⏳ — **dopo questo giro UI**: riapertura della regola 10, cioè la modalità di conversione per Broker. Proposta approvata dal developer il 30/09:
  - **Passo 3**: una scelta per Broker, «il Broker converte da solo quando compri» oppure «la fai tu prima di comprare». Il default è il comportamento di oggi, cioè la conversione manuale.
  - **Calcolo invariato**: stessi importi, stesso tasso, stesso spread; motore, oracolo e prova non si toccano.
  - **Lista finale**:
    - automatica: la conversione compare dentro la riga dell'ordine;
    - manuale: un passo «prima converti» per Broker × coppia di valute, col totale.
  - **Il totale lo calcola il backend**, perché la UI non somma importi (lettura prudente di Q-C0-2). Quindi il contratto cambia:
    - campo nella richiesta, modalità e totali nel risultato;
    - fingerprint, `api sync`;
    - test di schema e report tramite test-author.
  - **Limite dichiarato**: un ordine può essere pagato in parte con cassa nella valuta dell'asset e in parte convertendo. In modalità automatica si assume che il Broker lo sappia fare; se non lo fa, serve un cambio del calcolo, da portare alla review R1/R3.
  - Il coordinatore è stato avvisato il 30/09 (contratto, `api sync` in lista d'integrazione).

  > **Note implementazione** (2026-09-30), R4.1–R4.7:
  >
  > **Icone** (R4.1):
  > - `shared/PlannerBrokerIcon.svelte` (nuovo) mette `BrokerIcon` su un Broker del draft, col fallback all'icona del catalogo. La usano `BrokersStep`, `BrokerEditor` (titolo e righe di funding), `RoutingStep` e `LiquidityStep`;
  > - `OwnerBrokerPicker` e `OwnedAssetsDialog` usano direttamente `BrokerIcon`, e il dialog anche `AssetIcon`, perché mostrano righe della fonte e non del draft.
  >
  > **Card Broker** (R4.2, `BrokersStep.svelte`):
  > - una riga per valuta, con `CurrencyCode` (bandiera e codice di 3 lettere), il tipo d'ordine e l'incremento, ciascuno col suo `HelpTip`;
  > - la commissione di acquisto sta su una riga a sé;
  > - la riga della conversione descrive il comportamento di oggi, cioè un passo «FX» esplicito prima degli ordini, in attesa di R4.9;
  > - la liquidità utilizzabile è mostrata con le icone;
  > - i testi di tipo, unità, incremento e commissione vengono da `modeText.ts` (nuovo: `modeKindText`, `modeUnitText`, `modeIncrementText`, `modeFeeText`), condiviso con `RoutingStep`.
  >
  > **Editor** (R4.3, `BrokerEditor.svelte`):
  > - «Aggiungi valuta» sta in cima; il blocco nuovo porta la scelta della valuta, e le valute già presenti non ricompaiono;
  > - i blocchi stanno in una `OrderableList`;
  > - la griglia è uniforme grazie a `LABEL_ROW`, `INPUT_SUFFIX`, `BUTTON_DANGER_SMALL` e `BUTTON_PILL` (`ui.ts`): intestazione con valuta e «rimuovi», riga tipo + incremento, riga commissione (fissa, %, minimo, massimo), tutte coi loro `?`;
  > - «BUY» diventa «Commissione di acquisto».
  >
  > **Funding** (R4.4):
  > - `syncFunding()` (`draft.svelte.ts:464-470`) aggiunge già abilitata ogni voce Broker × fonte mancante. Si chiama dopo le copie e le aggiunte di Broker e casse (`:381`, `:424`, `:585`), e `BrokerEditor.svelte:40` fa lo stesso sulla copia di lavoro;
  > - una voce già presente non viene mai toccata: se l'utente toglie la spunta, resta tolta;
  > - `newFunding()` (`:473-474`) resta `enabled: false` come fabbrica, ma tutti e tre i chiamanti lo sovrascrivono.
  >
  > **«I tuoi Asset»** (R4.6):
  > - `source.ts` legge la sezione `holdings`;
  > - `copies.ts`:
  >   - `ownedAssets(source)` unisce holdings, asset e Broker con le chiavi della fonte, senza leggere quantità;
  >   - una holding non risolta si conta in `unresolved` e si mostra, mai scartata in silenzio;
  >   - `applyOwnedAssets` aggiunge solo l'identità (`draftAssetFromSource`), e un asset già nel piano resta com'è.
  > - `steps/OwnedAssetsDialog.svelte` (nuovo):
  >   - una sola `POST /portfolio/allocation-source` con `assets`, `brokers` e `holdings`, `broker_ids` uguale ai Broker di proprietà e `asset_ids: null`;
  >   - filtro per Broker con `OwnerBrokerPicker`. La preselezione sono i Broker del piano, o tutti quelli di proprietà se il piano non ne ha (`:43-46`);
  >   - tutti gli asset visibili partono spuntati, con «Seleziona tutto» e «Deseleziona tutto»; quelli già nel piano non si selezionano.
  > - `AssetsStep.svelte:67-68`: pulsante «I tuoi Asset» accanto a «Cerca Asset» e «Asset manuale».
  >
  > **i18n** (R4.7), solo con `dev.py i18n`, da `/tmp/libreFolio_d_ui12/i18n_round4.py` (log `i18n_round4.log`, 50 operazioni con rc 0):
  > - 33 aggiunte, 17 aggiornate, 0 rimosse (regola (a)). I cataloghi passano da 4116 a 4149 chiavi per lingua, con insiemi identici e 0 differenze dal copione (`verify_round4.log`);
  > - ogni default EN coincide col testo EN del catalogo (`extract_r4c.log`: 0 mancanti, 0 diversi);
  > - l'ICU si formatta nelle 4 lingue, plurali 1 e n compresi (`icu_check_r4.log`); gli sha256 di prima sono in `i18n_before_r4.sha`;
  > - terminologia:
  >   - quote, titres e títulos per le unità;
  >   - «Seleziona tutto / Deseleziona tutto» presi da `risk.assetSet.bulk.*`;
  >   - «I tuoi Asset» preso da `assets.panels.own`;
  >   - FR con lo spazio prima di «:», e ’ tipografico in IT e FR.
  > - Rispetto a HEAD (`keydiff_r4.log`, fatto con node): +54, −8, e 39 cambiate in EN e 48 nelle altre lingue. Tutte le differenze stanno sotto `tools.pacAllocator.planner.*`: 0 fuori dal planner.
  > - **10 chiavi rimaste senza uso in questo giro**, per la lista di fine round; non le ho tolte, per la regola (a):
  >   - `brokerEditor.{feeRule,localCash,origin,stepRule}`;
  >   - `brokers.{conversions,localCash,stepAmount,fee,funding}`;
  >   - `route.fee`.
  >
  >   Tutte erano usate a HEAD, oggi hanno 0 riferimenti (grep esatto della chiave con la virgoletta) e stanno ancora nei cataloghi.
  >
  > **Build**:
  > - `front build --debug`, rc 0, log `/tmp/libreFolio_d_ui12/build4.log`;
  > - svelte-check: gli stessi 3 errori e 41 warning di prima, in 4 file fuori dal planner (`ToolExecutionMetrics.svelte:44`, `TransactionFormModal.test.ts:787` e `:819`);
  > - la 6161 risponde `{"status":"ok"}` e serve la build nuova: `start.BnRn4MPL.js` è lo stesso di `build/index.html`, delle 11:50:49.
  >
  > **Nessun test eseguito**, su richiesta del developer.

  > **⚠️ Fuori pista** (2026-09-30):
  > - **Regola (a) violata nei round 1–3.** Il confronto con HEAD mostra 8 chiavi **tolte** dai cataloghi durante i giri UI. La regola del developer dice: «Le chiavi verranno decretate morte solo alla vera fine del round di sviluppo». Le chiavi sono:
  >   - `scenario.noValues` (round 1);
  >   - `copyNotice.when` (round 2);
  >   - `scenario.asOf`, `summary.date`, `problems.asOfMissing`, `problems.priceDateMissing`, `problems.priceDateAfterReference` e `assetEditor.priceDate` (round 3).
  >
  >   `scenario.asOfHint` non conta: è nata e morta dentro i giri, e a HEAD non c'era.
  >
  >   **Correzione (R4.7b)**: rimetterle con `dev.py i18n add`, coi testi di HEAD nelle 4 lingue. Lo script è `/tmp/libreFolio_d_ui12/i18n_restore_r4.py`, coi valori in `restore_r4_values.json` estratti da `restore_r4_extract.mjs`. Poi vanno nella lista di fine round, e i cataloghi arrivano a 4157 chiavi per lingua. Lo si esegue solo dopo il RESUME del coordinatore (pausa del venv condiviso per `pipenv update` nel worktree di K, 30/09).
  > - **Default EN riallineati al catalogo e al codice**: `age.after`, `brokerEditor.fundingCap`, `brokerEditor.modesHelp` («an Asset priced») e `ownedAssets.brokersHelp`. A quest'ultimo si aggiunge «, or all of them if the plan has none yet», come fa il codice a `OwnedAssetsDialog.svelte:45-46`.
  > - **`ownedAssets.count`**: in EN resta semplice («{selected} of {total} selected»); IT, FR ed ES usano il plurale ICU su `selected`, perché lì il participio concorda.
  > - **Funding spuntato di default**: lo ha chiesto il developer. Le conseguenze vanno ricordate nel feedback R4.8:
  >   - più coppie FX richieste;
  >   - trasferimenti fra Broker proposti più spesso;
  >   - la preferenza implicita diventa «tutto consentito», e non più «nessuna».
  >
  > **Debito di test**, in aggiunta:
  > - `HelpTip`: apertura, testo e accessibilità;
  > - `modeText.ts`: tipo, unità, incremento, e commissione zero, fissa + %, minimo e massimo;
  > - `syncFunding`: voci nuove abilitate, una voce tolta dall'utente mai riattivata, la copia di lavoro di `BrokerEditor`;
  > - `source.ts`: il mapping di `holdings`;
  > - `ownedAssets`: join, `unresolved`, ordinamento, Broker non duplicati. `applyOwnedAssets`: solo identità, asset già nel piano intatto, conteggio;
  > - `OwnedAssetsDialog`: preselezione dei Broker, filtro, spunte di default, «Seleziona tutto / Deseleziona tutto», asset già nel piano, errore dello scope, `accountGeneration`;
  > - `BrokerEditor`: «Aggiungi valuta» in cima, valuta nel blocco nuovo, `OrderableList`, commissione su riga a sé. `BrokersStep` e `RoutingStep`: testi da `modeText` e icone;
  > - E2E: passi 3 e 4 con «I tuoi Asset».

#### Round 5 — feedback sui passi 2 (Liquidità), 3 (Broker) e 4 (Asset) ✅ 2026-09-30

**Feedback del developer** (R4.8, 30/09), in sostanza:
- **Passo 2, liquidità copiata da un Broker**:
  - via il banner verde «Copia eseguita…» e la nota sulle commissioni;
  - «Importo da usare» parte da tutto il disponibile.
- **Passo 3, card Broker**:
  - più larga: i testi vanno a capo;
  - «Modifica» e «Rimuovi» in alto a destra;
  - via il badge «Copiato»;
  - il chip «già qui» non si capisce.
- **Passo 3, editor**:
  - la valuta di un blocco già presente si deve poter cambiare;
  - un clic in un punto qualsiasi del rettangolo del funding lo seleziona e lo colora;
  - «massimo utilizzabile qui» con simbolo e bandiera della valuta;
  - tooltip della commissione con più esempi;
  - campi della commissione nell'ordine minimo, percentuale, massimo, e la fissa per ultima.
- **Dialog «Aggiungi Broker»**: nasconde i Broker già aggiunti. Via il concetto «ricopiare aggiorna»: i dati automatici si rileggono a «Calcola».
- **«I tuoi Asset»**: il filtro per Broker diventa una tendina come quella di Risk in asset-correlation.
- **«Prezzo mancante»**: dopo aver aggiunto i propri asset non ha senso, perché il prezzo si può ricavare subito.

**Perché oggi compare «Prezzo mancante»** (lettura del codice, 30/09):
- tutte le vie di aggiunta copiano solo l'identità, con `price: null`: `draftAssetFromInfo` (`copies.ts:91-111`), `applyOwnedAssets` (`:157-166`) e «Cerca Asset» (`AssetsStep.svelte:36-41`);
- il prezzo arriva solo con «Copia prezzi» (`SourceCopyDialog`, sezioni `assets` + `prices`, poi `applyPriceCopy` a `copies.ts:293`);
- la rilettura prima di «Calcola» (`refreshPlan`, `:462`) rilegge solo i prezzi già copiati. Un asset senza prezzo non viene mai riletto.

**Baseline**: non serve spostarla. La tendina di Risk (`components/risk/AssetSetRiskPanel.svelte:275-282`, `SimpleSelect`) è già a HEAD.

**Passi:**
- R5.1 ✅ 2026-09-30 — liquidità:
  - dopo la copia della liquidità e dei Broker, nessun banner se tutto è andato bene. Restano gli avvisi veri (mancanti, conflitti, problemi) e il dialog dei conflitti;
  - «Importo da usare» parte dal disponibile. Alla rilettura segue il disponibile nuovo finché l'utente non lo cambia: nessun campo nuovo nel draft.
  > **Note implementazione**:
  > - `copies.ts`: `wholeAvailable` (disponibile canonico, zero compreso; vuoto se negativo) e `usesAllAvailable` («Importo da usare» = disponibile). La riga nuova parte da `wholeAvailable`. Una riga esistente segue il saldo nuovo se è vuota o se usa «tutto», sia in `applyLiquidityCopy` sia in `refreshCopiedFacts`; altrimenti resta il conflitto di prima.
  > - `CopyNotice` e `CopyFlowView`: prop `quiet`. Con `quiet` il banner compare solo con mancanti, conflitti o problemi, e la nota sulle commissioni non c'è più. `LiquidityStep` e `BrokersStep` lo passano.
  > - `LiquidityStep`: le righe copiate hanno il testo nuovo `cash.selectedAll`; le righe manuali tengono `cash.noPrefill`.
  > - Il badge con data e ora sulla riga copiata resta: lo aveva chiesto il developer nel giro 2.
  > **⚠️ Fuori pista**: debito di test. Gli E2E che aspettano `pac-planner-liquidity-notice` o `pac-planner-brokers-notice` dopo una copia riuscita ora non li trovano più: da cercare in `frontend/e2e` al giro dei test. Da coprire anche la regola «tutto» in `copies` (saldo zero e negativo).
- R5.2 ✅ 2026-09-30 — card Broker: modalità a tutta larghezza, «Modifica» e «Rimuovi» in alto a destra, niente badge «Copiato», il chip «già qui» diventa il Broker stesso (icona, nome, valuta) con un tooltip.
  > **Note implementazione**: `BrokersStep.svelte`. Le modalità sono una colonna (`space-y-3`), non più `sm:grid-cols-2`. «Modifica» e «Rimuovi» stanno nell'intestazione, a destra; «Inattivo» segue il nome. Il chip della cassa locale mostra icona, nome e valuta del Broker. Ogni chip del funding ha un tooltip, chiave nuova `brokers.fundingChipHelp` (ICU `select`: `local`, `account`, `contribution`). Tolti `copyStamp`, `formatCopyStamp` e `locale`. `OriginBadge` resta solo sulle card dei conti esterni.
- R5.3 ✅ 2026-09-30 — editor Broker:
  - valuta modificabile anche nei blocchi già presenti (le valute usate da altri blocchi restano escluse);
  - il rettangolo del funding si seleziona con un clic ovunque e si colora;
  - `CurrencyCode` su tutti i suffissi di valuta;
  - ordine della commissione: minimo, %, massimo, fissa; tooltip con gli esempi della formula del backend (`constraints.py:43`: `fissa + clamp(% × importo, minimo, massimo)`, 0 se non si compra).
  > **Note implementazione**:
  > - `BrokerEditor.svelte`, intestazione del blocco: `CurrencySearchSelect compact` (testid nuovo `pac-planner-mode-currency`), che esclude le valute degli altri blocchi. `setCurrency` accetta solo un codice di 3 lettere non usato; con l'ordine «per importo» il passo segue la valuta nuova (`cldrCurrencyStep`), con «per unità» resta. Le cifre della commissione restano quelle scritte: il suffisso mostra la valuta nuova, quindi il cambio è visibile. Il draft cerca le modalità per valuta (`draft.modeFor`, `request.ts:48`) e le rotte sono per Asset e Broker, quindi il cambio non rompe niente.
  > - Commissione: ordine minimo, percentuale, massimo, fissa; griglia `sm:grid-cols-2 lg:grid-cols-4`; ogni campo ha il suo tooltip (nuovi `brokerEditor.feeRateHelp` e `feeFixedHelp`). `brokers.feeHelp`, usato anche dalla card, ha ora quattro esempi calcolati con `calculate_fee` (`numeric.py:265-290`): 0,19% con minimo 1,50 e massimo 18 su 500, 2.000 e 20.000 → 1,50, 3,80, 18; solo fissa 2,95; fissa 1 + 0,10% su 1.000 → 2; tutto 0. Le cifre sono testo del catalogo, scritte nel formato di ogni lingua, e non passano dai formatter del denaro: il mascheramento della privacy nasconderebbe gli esempi.
  > - Suffissi di valuta con `CurrencyCode` (passo «per importo», commissioni, «massimo utilizzabile qui»). `INPUT_SUFFIX` passa da `w-12` a `w-20`, così «€ 🇪🇺 EUR» ci sta e tutti i campi restano larghi uguale.
  > - Funding: la cassa locale è colorata come selezionata e bloccata, senza il badge «già qui» (`brokers.localHere` resta senza uso: lista di fine round); ha il tooltip di `fundingSourceHelp`, che adesso vive in `modeText.ts` ed è usato anche da `BrokersStep`. Ogni sorgente candidata è una card: verde se attiva, grigia se no; tutta la riga in alto è la `<label>` della casella, quindi un clic ovunque la seleziona; i campi priorità e massimo stanno sotto, fuori dalla label (nessuna label annidata).
  > **⚠️ Fuori pista**: debito di test per il giro dei test: `pac-planner-mode-currency` (cambio valuta, esclusione, passo che segue), ordine dei campi della commissione, clic sulla card del funding, `fundingSourceHelp` (tre rami ICU).
- R5.4 ✅ 2026-09-30 — dialog di copia di Broker e liquidità: nascondono ciò che è già nel piano, con un messaggio se non resta niente; valute con `CurrencyCode`.
  > **Note implementazione**: `BrokerScopeCopyDialog.svelte`.
  > - «Aggiungi Broker» nasconde i Broker già nel piano e legge solo gli altri; se sono tutti nel piano non legge niente.
  > - «Copia liquidità» mostra, per ogni Broker, solo le valute che il piano non ha ancora (`newCash`, per chiave `domainCashKey`), e nasconde un Broker già nel piano che non ha più niente da aggiungere. Senza la sua snapshot (lettura fallita) un Broker non viene dato per completo. La copia passa a `applyLiquidityCopy` una sorgente filtrata: le righe già nel piano non vengono toccate, e le rilegge «Calcola». Così dal dialog non nasce più il conflitto «ricopiare aggiorna».
  > - Se non resta niente da copiare: messaggio nuovo `copy.allInPlan` (ICU `select` su `kind`), testid `…-all-in-plan`. Tolto il badge `copy.alreadyInDraft` (chiave senza uso: lista di fine round).
  > - Valute con `CurrencyCode`: righe della liquidità e valute viste del Broker. Per metterle in fila serve l'etichetta da sola: chiave nuova `brokerCopy.currenciesSeen`; `brokerCopy.currencies` resta senza uso (lista di fine round).
  > - Aggiornato il testo `liquidityCopy.rule`: l'importo da usare ora parte da tutto il disponibile (R5.1).
  > **⚠️ Fuori pista**: debito di test: filtro per Broker e per valuta, sorgente filtrata (nessuna riga esistente modificata), messaggio `…-all-in-plan`, nessuna lettura quando tutti i Broker sono già nel piano.
- R5.5 ✅ 2026-09-30 — «I tuoi Asset»: tendina `SimpleSelect` come Risk; dopo ogni aggiunta (tuoi Asset e «Cerca Asset») una sola `POST /portfolio/allocation-source` con `assets` + `prices` per gli asset nuovi. I prezzi diventano copiati, quindi si rileggono a «Calcola».
  > **Note implementazione**:
  > - `copies.ts`: nuova `applyAddedAssetPrices(draft, source, copy, assetIds)`. Riempie solo gli asset elencati con il prezzo ancora vuoto (`price`, `copiedPrice`, `priceStamp`, `priceSource`), mette gli altri in `missing` e chiude con `pruneCopies`. Non produce conflitti: un prezzo scritto a mano durante la lettura non si tocca. `applyPriceCopy` e `refreshCopiedFacts` restano invariati.
  > - `priceRead.svelte.ts` (nuovo), classe `AddedAssetPrices`: una lettura `assets` + `prices` con i Broker OWNER, niente provider. Ha una sua sequenza; una chiamata nuova sostituisce la vecchia e ne eredita gli id, presi solo dopo lo scope, quindi nessun id si perde. Stato pubblico: `waiting`, `missed` (asset letti senza un prezzo utilizzabile), `busy`, `error`; `stop()` in `onDestroy`.
  > - `AssetsStep.svelte`: «Cerca Asset» e «I tuoi Asset» (`onadded`) chiamano la lettura. Sulla card: «Lettura del prezzo…» con spinner mentre legge (niente «!»), poi il prezzo copiato, oppure il testo nuovo `assets.priceNotStored` se LibreFolio non ha un prezzo utilizzabile. Nessun banner di copia: lo stato sta sulle card. Errore di rete o di scope: avviso chiudibile `pac-planner-assets-price-error`. Il contenitore pubblica `aria-busy`/`data-busy`, la card `data-price-read` (`reading`, `not-stored`, `idle`). Il suggerimento `assets.noAutoPrice` diventa `assets.priceAuto`.
  > - `OwnedAssetsDialog.svelte`: il filtro è una tendina `SimpleSelect` come Risk, con «Tutti i Broker» (chiave nuova `ownedAssets.allBrokers`) e icone dei Broker (`item`/`selectedItem`). I Broker con un ruolo inferiore restano nella tendina, disabilitati, con il motivo (N18). Default: il Broker del piano se il piano ne ha uno solo, altrimenti tutti. `ownedAssets.noBroker` resta senza uso (lista di fine round); aggiornati `brokers`, `brokersHelp` e `noneInBrokers`.
  > **⚠️ Fuori pista**: rispetto alla riga del piano, al posto di `applyPriceCopy` una funzione nuova che riempie solo i prezzi vuoti: così la lettura automatica non apre mai il dialog dei conflitti. Debito di test: lettura dopo «Cerca Asset» e dopo «I tuoi Asset», gara fra due letture, prezzo scritto a mano durante la lettura non sovrascritto, `not-stored`, errore di scope, rilettura a «Calcola» dei prezzi letti così; tendina (default, «Tutti», Broker disabilitati, filtro); E2E del passo 4.
- R5.6 ✅ 2026-09-30 — i18n solo con `dev.py i18n`: solo aggiunte e aggiornamenti, nessuna rimozione (regola (a)); chiavi rimaste senza uso nella lista di fine round.
  > **Note implementazione**: `/tmp/libreFolio_d_ui12/i18n_round5.py`, 10 `add` + 5 `update`, tutti rc=0; sha dei 4 cataloghi presi prima in `i18n_before_r5.sha`.
  > - Nuove: `assets.priceAuto`, `assets.priceNotStored`, `assets.priceReading`, `brokerCopy.currenciesSeen`, `brokerEditor.feeFixedHelp`, `brokerEditor.feeRateHelp`, `brokers.fundingChipHelp` (ICU `select` su `local`/`account`/altro), `cash.selectedAll`, `copy.allInPlan` (ICU `select` su `liquidity`/altro), `ownedAssets.allBrokers`.
  > - Aggiornate: `brokers.feeHelp` (regola + 4 esempi verificati a mano: 0,19% di 500 = 0,95 → minimo 1,50; di 2.000 = 3,80; di 20.000 = 38 → massimo 18; 1 + 0,10% di 1.000 = 2; numeri scritti nel formato di ogni lingua, FR con lo spazio fine U+202F), `liquidityCopy.rule`, `ownedAssets.brokers`, `ownedAssets.brokersHelp`, `ownedAssets.noneInBrokers`.
  > - Verifiche: `verify_round5.py` 0 differenze, 4167 chiavi per lingua, stessi insiemi; `keydiff` contro HEAD (4103): +64, 0 rimosse, 0 fuori dal planner in tutte e 4 le lingue; ICU (`icu_check_r5.mjs`) 0 errori, nessuna graffa residua; estrattore: 0 chiavi mancanti, l’unica «differenza» di `feeHelp` è il `\n` letterale del sorgente contro l’a capo reale del catalogo.
  > - Lista di fine round (regola (a)), 20 chiavi senza uso: 18 usate a HEAD e non più (`assetEditor.priceDate`, `assets.noAutoPrice`, `brokerCopy.currencies`, `brokerEditor.feeRule`, `brokerEditor.localCash`, `brokerEditor.origin`, `brokerEditor.stepRule`, `brokers.conversions`, `brokers.fee`, `brokers.funding`, `brokers.localCash`, `brokers.stepAmount`, `copy.alreadyInDraft`, `copyNotice.when`, `route.fee`, `scenario.asOf`, `scenario.noValues`, `summary.date`) + 2 aggiunte in questi round e già senza uso (`brokers.localHere`, `ownedAssets.noBroker`). Controllate a mano le omonime per suffisso (`${KEY}.fee`, `.funding`, `.priceDate`, `.stepAmount`): sono di altri namespace (`result.*`).
  > **⚠️ Fuori pista**: lo scanner letterale segnava come senza uso anche `refresh.failed.*` e `refresh.notice.*`: sono usate tramite la costante `KEY` in `RefreshFailedPanel`/`RefreshNotice`, quindi restano fuori dalla lista.
- R5.7 ✅ 2026-09-30 — `front build --debug`, verifica della 6161, feedback del developer. Nessun test automatico, su sua richiesta.
  > **Note implementazione** (2026-09-30): `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front build --debug` rc=0 (log `/tmp/libreFolio_d_ui12/build5.log`); svelte-check 3 errori e 41 warning in 4 file, come la baseline, nessuno nel planner. La 6161 (`srv6161review`, PID 70702) serve la build nuova: `start.BspabasX.js` uguale in `frontend/build/index.html` e in `curl localhost:6161/`. 6151 libera.
  > **Esito**: il developer approva i passi 1–3 («fino allo step 3 ora è tutto perfetto»). Il feedback sul passo 4 diventa il **Round 6** (sotto).

#### Round 6 — feedback sul passo 4 (Asset) ✅ 2026-09-30 (R6.1–R6.5); il feedback apre il Round 7

**Feedback del developer** (R5.7, 30/09), in sostanza:
- **(a) Card dell'asset**: perché due badge «Copiato»? Che cosa vuol dire «8 giorni prima del 30/09/2026»?
- **(b) Nota**: che cosa vogliono dire, su questa pagina, «Nessuna esposizione: il backend la conta come Non classificato» e «classificazione»?
- **(c) Editor «Modifica asset»**: i componenti hanno altezze diverse, i badge non si capiscono, lo scopo di «Esposizioni (facoltative)» non è chiaro.
- **(d) Import**: le classificazioni devono arrivare da sole, come i prezzi.

**Decisione del developer sui pulsanti della barra** (30/09, `ask_user`): «Toglili: tutto automatico. Nella modifica resta «Ripristina», e se la lettura fallisce compare un «Riprova»». Quindi via «Copia prezzi» e «Copia classificazioni»; il dialog di copia esplicita resta solo per l'FX (`FxStep`).

**Lettura del codice** (30/09):
- I due «Copiato»: uno è l'`OriginBadge` dell'identità, nell'intestazione (`AssetsStep.svelte:112-121`); l'altro è quello del prezzo (`:122-147`). «8 giorni prima» è `AgeLabel`: la distanza fra la data del prezzo e la data di riferimento dello scenario.
- Le esposizioni servono solo al report del risultato (`result/ExposureSection.svelte`): il motore non le usa per decidere gli ordini. Le categorie arrivano dal dominio (`portfolio_allocation_source.py:983-1105`, `_build_planner_classifications`): per `asset_type` il valore dell'enum («ETF»), per `sector` la chiave `FinancialSector`, per `geography` l'ISO alpha-3. Una dimensione che LibreFolio non ha arriva come riga segnaposto con `category_id`/`label`/`weight` nulli, più un avviso.
- Oggi le classificazioni arrivano solo con «Copia classificazioni» (`SourceCopyDialog`, poi `applyClassificationCopy`, `copies.ts:388-425`). La lettura automatica di R5.5 (`priceRead.svelte.ts`) chiede solo `assets` + `prices`.
- Nell'editor (`AssetEditor.svelte:207-243`) le righe delle esposizioni hanno `SimpleSelect compact` (più basso) accanto a campi da 38px, e chiedono a mano «ID categoria» ed «Etichetta».
- Nessun E2E o test unitario usa `pac-planner-prices-copy-open`, `pac-planner-classifications-copy-open` o importa `copies.ts`. L'unico test del planner è `result/StateNotice.test.ts`.

**Passi:**
- R6.1 ✅ 2026-09-30 — card dell'asset (`AssetsStep.svelte`):
  - via i pulsanti «Copia prezzi» e «Copia classificazioni», il loro stato e il render di `SourceCopyDialog`. Il suggerimento sul prezzo automatico passa in un `HelpTip` e dice che prezzo e composizione arrivano da soli;
  - intestazione: `AssetIcon`, nome, tipo tradotto (`assets.types.*`); niente badge «Copiato» dell'identità, «Manuale» solo per gli asset manuali; «Modifica» e «Rimuovi» in alto a destra, come le card dei Broker;
  - prezzo: un solo badge, con data e ora se il prezzo è di oggi, altrimenti solo la data; il tooltip spiega che è l'ultimo prezzo salvato in LibreFolio, riletto prima del calcolo, e che un valore scritto a mano resta. Via `AgeLabel` dalla card e dall'editor;
  - riga «Composizione», con un `HelpTip` che dice che serve solo al report del risultato: una riga per dimensione con le etichette leggibili (tipo tradotto, settore con emoji, paese con bandiera), le prime categorie e «+N»; se LibreFolio non ha il dato lo dice, e lo distingue da «non indicata» per gli asset manuali;
  - «Riprova» sull'avviso di errore della lettura.
  > **Note implementazione** (✅ 2026-09-30): `AssetsStep.svelte` riscritto.
  > - Barra: ricerca, «I tuoi Asset», «Asset manuale» e un `HelpTip` (`assets.autoLabel` + `assets.priceAuto`, testid `pac-planner-assets-auto-help`). Via i due pulsanti di copia, il loro stato e `SourceCopyDialog`, che resta solo in `FxStep` (`kind="fx"`).
  > - Intestazione: `AssetIcon`, ticker + nome, tipo tradotto (`pac-planner-asset-type`); `OriginBadge` solo per «Manuale»; «Inattivo»; «!» se manca il prezzo e non sta leggendo; «Modifica» e «Rimuovi» in alto a destra.
  > - Prezzo: un solo `OriginBadge` copiato, con `formatCopyStamp` (data e ora se di oggi, altrimenti la data) oppure «Modificato». Il tooltip è `assets.priceCopiedHelp` (ICU con data e fonte) o `assets.priceModifiedHelp`. Via `AgeLabel` dalla card; resta in `ReviewStep`, `DistributionDialog` e `FxStep`.
  > - Composizione: `dt` con `HelpTip` (`assets.compositionHelp`); una riga per dimensione (`pac-planner-asset-dimension`, `data-dimension`, `data-state` = `set`/`not-stored`/`missing`), categorie per peso decrescente, le prime `VISIBLE_CATEGORIES` e «+N» con tooltip. La riga del tipo non compare quando ripete l'intestazione (una sola categoria al 100% uguale al tipo). «nessun dato in LibreFolio» (`assets.dimensionNotStored`) si distingue da «non indicato/a» (`assets.dimensionNone`, ICU con il genere di «area geografica»). Badge «Modificato» con `assets.compositionModifiedHelp`.
  > - Errore di lettura: «Riprova» (`pac-planner-assets-read-retry`) quando restano id falliti, più «Chiudi». Al mount si leggono una volta gli asset ripristinati col draft o lasciati a metà lettura (`reader.pending`).
- R6.2 ✅ 2026-09-30 — classificazioni automatiche: la lettura dopo un'aggiunta chiede anche `classifications` e riempie solo le composizioni vuote e mai copiate (nuova `applyAddedAssetClassifications` in `copies.ts`, nessun conflitto); ricorda per asset e dimensione che cosa LibreFolio non ha; tiene gli id dell'ultima lettura fallita per «Riprova». Le classificazioni non si rileggono a «Calcola» (decisione del Round 3).
  > **Note implementazione**:
  > - `assetRead.svelte.ts` (nuovo) sostituisce `priceRead.svelte.ts` di R5.5. Quel file non era tracciato, quindi la cancellazione non lascia traccia in git. Classe `AddedAssetFacts`: una `POST /portfolio/allocation-source` con `assets` + `prices` + `classifications` per gli asset aggiunti, Broker OWNER, niente provider. API: `needsRead`, `pending`, `isReading`, `notStored`, `lackingOf`, `read`, `retry` (id dell'ultima lettura fallita), `canRetry`, `dismiss`, `stop`.
  > - `copies.ts`: `applyAddedAssetClassifications` (`:411`) e `lackingDimensions` (`:440`), che raccoglie le righe segnaposto con cui il dominio dice che non ha il dato. `applyAddedAssetPrices` (`:370`) invariata.
- R6.3 ✅ 2026-09-30 — editor (`AssetEditor.svelte`): controlli tutti alti 38px; suggerimenti in `HelpTip`; identità copiata con icona, nome e tipo tradotto; tipo manuale con `AssetTypeSelect`; composizione raggruppata per dimensione, con la scelta della categoria (tipo, settore, paese) e la percentuale, più «Aggiungi» per ogni dimensione; via «ID categoria» ed «Etichetta» (l'etichetta prende l'id, come fa il backend). Restano «Modificato» e «Ripristina».
  > **Note implementazione**:
  > - Identità. Asset manuale: griglia a 2 colonne con ID (`HelpTip` `neverByName`), nome, ticker e tipo. Asset copiato: icona, nome e tipo tradotto in sola lettura (`pac-planner-asset-editor-type-text`). Il tipo di un asset copiato resta modificabile solo se la sua classe non è fra gli `ASSET_TYPES`.
  > - Tipo: `AssetTypeSelect` (testid `pac-planner-asset-editor-type`, trigger `…-type-button`) con `HelpTip` `assetEditor.typeHelp`. Un asset manuale nuovo parte con la composizione `asset_type` = ETF al 100%; se l'unica riga del tipo è al 100% e uguale al tipo, segue il tipo scelto (`setType`).
  > - Prezzo: importo, `CurrencySearchSelect compact` e base con `HelpTip`; badge «Modificato» con tooltip `assetEditor.priceModifiedHelp` e «Ripristina» (`planner.restore`); tooltip del prezzo copiato come sulla card.
  > - Composizione: un blocco per dimensione (`pac-planner-exposure-block`, `data-dimension`). Ogni riga ha: la categoria (`AssetTypeSelect`, `SectorSearchSelect` o `CountrySearchSelect`); `ExactDecimalInput` del peso (`w-28`, `%`); rimuovi, solo icona. «Aggiungi un tipo/settore/paese» (ICU). Settori e paesi già usati nel blocco sono esclusi dalla scelta. Un valore che i riferimenti non conoscono (testo libero di un draft vecchio) si mostra in sola lettura. `HelpTip` = `assets.compositionHelp` + `assetEditor.weightsHelp`; badge «Modificato» + «Ripristina».
  > - Via `SimpleSelect`, il datalist `CLASS_SUGGESTIONS`, i campi «ID categoria», «Etichetta» e «Dimensione», `AgeLabel`, `OriginBadge` e i paragrafi statici `unclassified`/`overHundred`. Il loro testo è ora nel `HelpTip`: a HEAD `overHundred` era solo un suggerimento statico, quindi nessun controllo è andato perso.
  > **⚠️ Fuori pista**: `AssetTypeSelect` non ha una prop per escludere i tipi già usati, quindi una seconda riga dello stesso tipo resta possibile e la respinge il normalizer (coppia dimensione/categoria duplicata). Domanda aperta al developer.
- R6.4 ✅ 2026-09-30 — etichette leggibili delle categorie in un helper unico, usato dalla card, dall'editor e da `result/ExposureSection.svelte`.
  > **Note implementazione**: `categoryLabels.svelte.ts` (nuovo). `exposureCategoryLabel` produce: il tipo tradotto (`assets.types.*`); il settore con emoji e nome (`sectors.*`); il paese con bandiera e nome (`countryStore`). Un codice sconosciuto resta il codice. `CategoryLabels` carica paesi e settori una volta per lingua (`load`), poi offre `text` e `known`. `ExposureSection.label()` lo usa per le dimensioni note, e mantiene la mappatura di «Non classificato».
- R6.5 ✅ 2026-09-30 — i18n solo con `dev.py i18n` (aggiunte e aggiornamenti), `keydiff` e ICU, `front build --debug`, verifica della 6161, feedback del developer. Nessun test automatico, su sua richiesta.
  > **Note implementazione**:
  > - `/tmp/libreFolio_d_ui12/i18n_round6.py`: 16 `add` + 2 `update` (`assets.priceAuto`, `assets.priceReading`), tutti rc=0, nessuna rimozione. Nuove: `restore`; `assets.autoLabel`, `priceCopiedHelp` (ICU), `priceModifiedHelp`, `composition`, `compositionHelp`, `dimensionNotStored`, `dimensionNone` (ICU con il genere), `compositionModifiedHelp`; `assetEditor.typeHelp`, `pickCategory` (ICU), `addCategory` (ICU), `weightsHelp`, `weight`, `priceModifiedHelp`, `compositionModifiedHelp`.
  > - Verifiche:
  >   - estrattore `keys_r6.py`: `missing=0`, 57 coppie chiave/default distinte confrontate col catalogo EN, 0 differenze dopo aver allineato 6 default;
  >   - 4183 chiavi per lingua;
  >   - `keydiff` contro HEAD (4103): +80, 0 rimosse, 0 fuori dal planner nelle 4 lingue;
  >   - ICU (`icu_check_r6.mjs`): 0 errori;
  >   - sha8 dei cataloghi dopo il round in `i18n_sha_after_r6.txt`: en `1c694fc0`, it `17cfbca1`, fr `dca8e3a7`, es `f1178040`.
  > - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front build --debug`: rc=0 (`build6.log`). svelte-check dà 3 errori e 41 warning in 4 file, come la baseline dei round 1–5; nessuno nel planner.
  > - La 6161 (`srv6161review`, PID 70702) serve `start.DOSki1CW.js`. La 6151 è libera.
  > - Lista di fine round, regola (a). Scanner `unused_r6.py`, che adesso espande anche le costanti `${KEY}.x`. Risultato: 32 chiavi, cioè le 20 del R5.6 più 12 nuove: `assetEditor.categoryId`, `categoryLabel`, `class`, `classHint`, `dimension`, `exposureAdd`, `exposures`, `overHundred`, `unclassified`; `assets.copyClassifications`, `copyPrices`, `noExposures`. `pricesCopy.*` e `classificationsCopy.*` risultano ancora usate solo perché i rami morti di `SourceCopyDialog` le citano; si liberano con la cascata qui sotto.
  > **⚠️ Fuori pista**:
  > - Lo scanner letterale di R5 dava 45 chiavi «nuove senza uso»: 15 erano falsi positivi dovuti alle costanti `KEY`. Da qui la versione r6.
  > - **Codice morto** (solo inventario; si toglie dopo la test-triage): in `SourceCopyDialog`, i tipi `prices` e `classifications`; `applyPriceCopy` (`copies.ts:305`) e `applyClassificationCopy` (`:453`), citate solo da quei rami; le varianti di conflitto dei prezzi e delle classificazioni (`copies.ts:15-16`, `resolveConflicts`, `ConflictDialog.svelte`). `AgeLabel`, `OriginBadge` e `restoreCopiedRate`/`planner.restoreCopied` restano usati e non si toccano.
  > - **Debito di test**, per il giro dei test:
  >   - testid cambiati: `pac-planner-asset-editor-class` ora è un contenitore; `pac-planner-exposure-dimension` e `-label` non esistono più; `-category` è un contenitore. Tipo: `pac-planner-asset-editor-type`, `-type-button`, `-type-text`. Via `price-origin`, `price-age` ed `exposures-origin` nell'editor;
  >   - le spec della barra di copia;
  >   - lettura automatica con le classificazioni: riempie solo le composizioni vuote, `not-stored`, «Riprova»;
  >   - lettura al mount;
  >   - `CategoryLabels`: tipo, settore, paese, codice sconosciuto;
  >   - la riga del tipo nascosta sulla card;
  >   - il tipo che segue la scelta.
  > **Esito** (30/09): passi 1–3 approvati, con due ritocchi; il resto del feedback diventa il **Round 7** (sotto).

#### Round 7 — ritocchi ai passi 2–3, card ed editor dell'Asset, passo Instradamento ✅ 2026-09-30 (R7.0–R7.7); in attesa del feedback del developer

**Feedback del developer** (R6.5, 30/09), in sostanza:
- **Passo 2 (Liquidità)**: via il badge «Copiato · data/ora», è una svista.
- **Editor del Broker**: «tutto perfetto», tranne la spunta in «Liquidità utilizzabile da»: basta lo sfondo colorato.
- **Card dell'Asset**:
  - più larghe, perché i parametri lunghi vanno a capo;
  - ordinabili con `OrderableList`;
  - i nomi lunghi scorrono;
  - la composizione dice «nessun dato in LibreFolio» anche quando i dati ci sono;
  - via il badge «Copiato · data».
- **Editor dell'Asset**:
  - deve caricare i dati che LibreFolio ha già;
  - per la composizione riusa il componente del modale «Aggiungi Asset» (`DistributionEditor`);
  - il tipo è un valore solo, senza percentuale.
- **Passo Instradamento**: via il selettore in alto, una zona per ogni Asset; campi chiari (Priorità «0 = preferita», Minimo se operi, Minimo obbligatorio, Tetto 1000000000 «Default alto», Margine di esecuzione %, Commissione di acquisto: nessuna); spiegare il «Tetto». Migliorarlo ora: il feedback preciso arriva al giro dopo.

**Lettura del codice** (30/09):
- **Causa della composizione vuota** (difetto del backend, codice di D):
  - chi scrive le classificazioni salva il JSON di Pydantic, con i pesi come **stringhe**: `crud.py:104` (`model_dump_json`) e il PATCH `crud.py:468`/`:600` (`model_dump(mode="json")`); `BaseDistribution` (`schemas/assets.py:335-431`) li quantizza a 4 decimali HALF_EVEN e porta la somma a 1 esatto;
  - `_parse_saved_distribution` (`portfolio_allocation_source.py:952-980`) accetta solo `Decimal`, quindi restituisce `None`: il dominio manda il segnaposto e l'avviso `allocation.classification_invalid`, e la card dice «nessun dato»;
  - la geografia rifiuta anche la chiave `"Other"`, che chi scrive lascia passare (`geo_utils.py:185-187`) e che l'API dei paesi elenca (`utilities.py:147-149`, `iso3="Other"`).
  - Riproduzione: `/tmp/libreFolio_d_ui12/classif_roundtrip.py` (log accanto) → `sector parse: None`, `geo parse: None`, anche senza `"Other"`.
  - I test esistenti (`test_portfolio_allocation_source.py:186-203`, `:1200-1316`) scrivono pesi numerici: per questo non l'hanno visto. I rifiuti che verificano (somma, settore inventato, `"US"`) restano validi con la correzione.
- `CategoryLabels` cerca il paese in maiuscolo (`categoryLabels.svelte.ts:25`), quindi `"Other"` diventa `OTHER` e non si trova.
- Il draft non è persistito (`draft.svelte.ts:4`): dopo il riavvio della 6161 il developer riaggiunge gli Asset e la lettura porta la composizione nuova.
- Nomi che scorrono: l'azione `use:scrollOnOverflow` (`$lib/actions/scrollOnOverflow.ts`) con `overflowScrollTextClass` (`$lib/utils/overflowScroll.ts`), come in `AssetCard.svelte:183`.
- L'ordine degli Asset non conta per il motore: il normalizer li ordina per `asset_id` (`normalize.py:833`). Come per la Liquidità (`draft.svelte.ts:303-316`, `liquidityOrder` fuori da `data`), l'ordine è solo presentazione e non cambia il fingerprint.
- Badge con la data di copia: `LiquidityStep.svelte:152`, il prezzo in `AssetsStep.svelte` (`:200-208`), il timbro di `CopyNotice.svelte:79-81`, il `when` di `FxStep.svelte:71`. `BrokerEditor.svelte:147` resta (il developer lo approva); restano anche `AgeLabel` in `ReviewStep` e `DistributionDialog`.
- **Significato dei campi della rotta** (contratto `schemas/pac_allocator.py:502-553`):
  - **Priorità**: gara a pari merito dopo `fixed_l2` e `shortfall` (`objectives.py:9`, `:150-164`), `sum(priorità × attiva)`: vince il numero più basso; tutto a 0 = nessuna preferenza;
  - **Minimo se operi**: un acquisto è 0 oppure almeno `max(passo, minimo)` (`constraints.py:617-643`);
  - **Minimo obbligatorio**: pavimento senza condizioni (`constraints.py:600-614`); può rendere il piano impossibile;
  - **Tetto**: limite superiore in unità o importo, secondo la modalità; `OrderCap` non ha un tipo «nessuno» (`:523-537`), quindi è obbligatorio. Il default 1 000 000 000 (`defaults.ts`) non allarga la ricerca: conta `min(tetto, risorse)`;
  - **Margine**: prezzo di esecuzione `medio × (1 + margine)` (`constraints.py:170-178`), in [0, 1) (`normalize.py:529-531`): è una riserva di costo, non investimento;
  - il normalizer rifiuta minimo > tetto (`normalize.py:566-569`).
- `DistributionEditor` (`$lib/components/ui/input/DistributionEditor.svelte`): `kind` `sector`/`geographic`, `value` legabile in 0..1, `onchange`, emette `Number((w/100).toFixed(4))`; tabella con ricerca del settore o del paese, barra, «Bilancia», import CSV. Uso di riferimento: `AssetModal.svelte:2079-2082`.
- Nessun E2E o test unitario usa i testid che cambiano (funding-toggle, route-enabled, routing prev/next/asset/title, cash-origin, asset-price-origin, stamp).

**Passi:**
- R7.0 ✅ 2026-09-30 — questa sezione.
- R7.1 ✅ 2026-09-30 — via i badge con la data di copia: Liquidità (card della cassa copiata), prezzo sulla card dell'Asset (resta «Modificato»), timbro di `CopyNotice` per prezzi, FX e liquidità (valori riletti prima di «Calcola»); in `FxStep` via solo l'ora dal badge, restano badge e `AgeLabel`, perché lì la data del tasso serve.
  > **Note implementazione**:
  > - `CopyNotice.svelte`: `showStamp` è falso per `prices`, `fx` e `liquidity`; il timbro resta per le copie dei Broker e delle classificazioni, dove l'ora di copia è l'unica data che il dato ha.
  > - Card dell'Asset: resta l'`OriginBadge` («Copiato»/«Modificato»); la data del prezzo passa nel `?` accanto al prezzo (`assets.priceCopiedHelp`, con la fonte quando c'è).
  > - `FxStep.svelte:70-81`: badge d'origine e `AgeLabel` della data del tasso, senza l'ora di copia.
- R7.2 ✅ 2026-09-30 — `BrokerEditor`, «Liquidità utilizzabile da»: niente checkbox; la cassa locale è una chip colorata, le altre sono pulsanti `aria-pressed` con lo stesso colore acceso/spento.
  > **Note implementazione**:
  > - `BrokerEditor.svelte:312` (cassa locale, sempre `TOGGLE_ON`) e `:323` (fonti, `TOGGLE_ON`/`TOGGLE_OFF`); le classi vivono in `ui.ts:50-52`, condivise con l'Instradamento (R7.6).
  > - **⚠️ Fuori pista**: i testi d'aiuto parlavano ancora di spunte. `brokerEditor.fundingHelp` e `brokers.fundingHelp` ora dicono «in verde / clicca per escludere»; commento di `request.ts:328` allineato («excludes»).
- R7.3 ✅ 2026-09-30 — card dell'Asset a tutta larghezza, in `OrderableList`; nome che scorre; `assetOrder`/`orderedAssets`/`reorderAssets` nel draft (fuori da `data`, come la Liquidità), usati anche dall'Instradamento; via la riga del tipo dalla composizione (il tipo è già nell'intestazione).
  > **Note implementazione**:
  > - `draft.svelte.ts:332-357` (`assetOrder`, `orderedAssets`: prima l'ordine scelto, poi gli Asset nuovi in coda), `:579` (rimozione), `:583` (`reorderAssets`).
  > - Lettori dell'ordine: `AssetsStep.svelte:149-150` (`OrderableList`), `TargetsStep.svelte:52`, `RoutingStep.svelte:70-75`. Il fingerprint e la richiesta non cambiano: l'ordine non entra in `data`.
  > - Nome che scorre con `use:scrollOnOverflow` e `overflowScrollTextClass`, come `AssetCard`.
- R7.4 ✅ 2026-09-30 — backend: `_parse_saved_distribution` accetta anche il testo decimale che scrive Pydantic (`^[0-9]+(\.[0-9]+)?$`) e la chiave geografica `"Other"`; restano i rifiuti (non finito, negativo, somma ≠ 1, settore sconosciuto, paese non ISO alpha-3). Verifica con lo script di riproduzione; il test di regressione (con lo scrittore vero) va al test-author nel giro dei test. `CategoryLabels` trova `"Other"`.
  > **Note implementazione**:
  > - `portfolio_allocation_source.py`: `import re`; costanti `_SAVED_WEIGHT_TEXT` (`fullmatch`) e `_GEOGRAPHY_OTHER` accanto a `_KNOWN_SECTORS`; nel ciclo, un peso `Decimal` resta com'è, un testo che combacia diventa `Decimal(testo)`, tutto il resto → `None`.
  > - Il peso conserva la scala salvata (`"0.4000"` esce `"0.4000"`: `SafeDecimal` scrive `format(v, "f")`, `schemas/common.py:38-47`); il frontend lo legge esatto (`decimal.ts` `render` toglie gli zeri). Nessuna canonicalizzazione: la funzione dichiara di non modificare il dato salvato.
  > - Verifica: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python /tmp/libreFolio_d_ui12/classif_roundtrip_r7.py` → 21/21 OK (`classif_roundtrip_r7.log`): creazione (`crud.py:104`) e PATCH (`crud.py:600`) con `"Other"`, JSON numerico dei mock, 12 rifiuti (negativo, esponente, parola, `NaN`, booleano, vuoto, spazio, somma, settore inventato, `US`, `other`, `OTHER`), costruttore intero senza avvisi né segnaposto.
  > - Nessuna suite lanciata, su richiesta del developer: il test di regressione e `api portfolio`/servizi vanno nel giro dei test.
- R7.5 ✅ 2026-09-30 — editor dell'Asset: composizione con due `DistributionEditor` (settore e area geografica), agganciati alle esposizioni del draft con conversione esatta percentuale ↔ frazione; «Ripristina» li riallinea. Il tipo è un valore solo: la scelta scrive una sola riga `asset_type` al 100%; niente blocco del tipo nella composizione.
  > **Note implementazione**:
  > - `AssetEditor.svelte`: `distributionOf` (esposizioni → `Record` in frazione) e `writeDimension` (ritorno dell'editor → righe del draft; una categoria già presente conserva chiave, etichetta e provenienza); `withTypeRow` tiene una sola riga `asset_type` al 100%; `restoreExposures` rimette la composizione di LibreFolio e riallinea i due editor.
  > - `compositionModified` (`draft.svelte.ts:254`) è una funzione sola, usata dall'editor e dalla card: prima c'erano due confronti diversi.
  > - **⚠️ Fuori pista**:
  >   - `DistributionEditor` emette `Number((w/100).toFixed(4))`: una quota ha al massimo 2 decimali in percentuale. Il ritorno nel draft usa `toFixed(6)` e `fractionToPercent`, quindi non perde nulla di ciò che l'editor mostra.
  >   - `DistributionEditor` lascia passare totali oltre il 100%. `apply()` ora li blocca per dimensione con `assetEditor.totalOver` (`sumControlPercentages` + `compareDecimal`), prima che il normalizer li rifiuti al «Calcola».
  >   - Una composizione copiata poteva avere la riga del tipo diversa dal tipo mostrato: `apply()` la normalizza con `withTypeRow`.
  >   - Via `CategoryLabels.known()` (`categoryLabels.svelte.ts`, nato nel Round 6, mai in HEAD): serviva al vecchio editor a righe per decidere se una categoria era modificabile; con `DistributionEditor` non ha più lettori. `compositionRows` e `compositionModified` sono ora condivisi in `draft.svelte.ts`.
- R7.6 ✅ 2026-09-30 — Instradamento: una zona per Asset (nell'ordine del passo Asset), una riga per Broker operativo con interruttore colorato (icona, nome, valuta con emoji, modalità, commissione); campi con etichette chiare e `HelpTip`, layout di `BrokerEditor`. Il tetto resta un numero visibile (nasconderlo come «nessun limite» sarebbe una politica nascosta per gli Asset molto economici).
  > **Note implementazione**:
  > - `RoutingStep.svelte` riscritto: niente selettore né «precedente/successivo»; per ogni Asset di `orderedAssets` una card `TOGGLE_*` per Broker operativo (clic = consenti/escludi); i Broker di sola liquidità in una riga `routing.fundingOnly`.
  > - La riga della modalità è `route.modeLine` (tipo · incremento · commissione di acquisto, via `modeText.ts`).
  > - Campi: «Acquisto minimo», «Acquisto obbligatorio», «Acquisto massimo», «Priorità», «Margine sul prezzo», ognuno con il suo `HelpTip`. Il segnaposto dei campi vuoti è «nessun minimo»/«nessun obbligo».
  > - I testi d'aiuto dicono ciò che il motore fa (`solver.py:4`, ordine `fixed_l2 → shortfall → route_priority → explicit_cost → active_order_rows`): la priorità pesa più delle commissioni; il margine è un costo esplicito, non investimento; il tetto iniziale `1000000000` è mostrato nel suo aiuto (`route.capHelp`, `{cap}`), per la regola «nessun coefficiente nascosto» del brief.
  > - **⚠️ Fuori pista**:
  >   - La riga rossa «nessuna modalità» era sbagliata: `draft.modeFor` ricade su una modalità qualsiasi quando l'Asset non ha prezzo, quindi `null` vuol dire che il Broker non ha modalità. Ora mostra `problems.brokerNoMode` se `broker.modes.length === 0`, altrimenti `problems.routeNoMode` (le stesse chiavi di `request.ts:121`/`:174`); `route.noPrice` non serve più.
  >   - Il genere di «Nessuna» non andava bene per tutti i campi: segnaposto separati `route.minimumNone`/`route.requiredNone`.
  >   - Le costanti `TOGGLE_*` sono passate da `BrokerEditor` a `ui.ts`, per averne una sola copia.
- R7.7 ✅ 2026-09-30 — i18n solo con `dev.py i18n` (aggiunte e aggiornamenti), `keydiff` e ICU, `front build --debug`, riavvio di `srv6161review` per il backend, verifica della 6161, feedback del developer. Nessun test automatico, su sua richiesta.
  > **Note implementazione**:
  > - i18n: `python3 /tmp/libreFolio_d_ui12/i18n_round7.py` (log `i18n_round7.log`), 11 aggiunte e 8 aggiornamenti con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py i18n add|update`, tutti rc=0; nessuna rimozione (decisione (a)).
  >   - Aggiunte: `route.modeLine`, `route.minimumNone`, `route.requiredNone`, `route.minimumHelp`, `route.requiredHelp`, `route.capHelp`, `route.priorityHelp`, `route.marginHelp`, `routing.intro`, `routing.introHelp`, `assetEditor.totalOver`.
  >   - Aggiornate: `route.minimumIfActive`, `route.requiredMinimum`, `route.cap`, `route.margin`, `routing.fundingOnly`, `assets.compositionHelp` (via «tipo»), `brokerEditor.fundingHelp`, `brokers.fundingHelp`.
  >   - Cataloghi: **4194** chiavi per lingua, stesso insieme nelle 4; sha8 en `5f211180`, it `359d08ed`, fr `a19c3c10`, es `48c95675`.
  > - Verifiche: `keys_r7b.py` → manca solo l'artefatto `problems.` (prefisso dinamico di `request.ts`); `defaults_vs_en_r7.py` → solo il falso positivo `brokers.feeHelp` (la regex legge `\n` alla lettera); `icu_check_r7.mjs` → 21 chiavi × 4 lingue, **0 errori**, nessuna graffa residua.
  > - Build: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front build --debug` → rc=0 (`build7.log`), `start.STTnJeXF.js`.
  > - Riavvio della 6161 (serve per R7.4): stesso comando di F6, `server --test --host 127.0.0.1 --port 6161 --data-dir /tmp/librefolio-r2-d-prodcopy --no-scheduler --no-reload`, shellId `srv6161r7`, log `/tmp/libreFolio_d_f6/server_review_r7.log`. Health 200, catalogo senza auth 401, scheduler spento, la pagina serve `start.STTnJeXF.js`; 6151 libera.
  > - **⚠️ Fuori pista**: `stop_bash srv6161review` ha risposto «stopped», ma il processo restava in ascolto: lo strumento non tracciava più quella shell. Ho verificato che il padre (PID 70682) fosse proprio `dev.py server --test … --port 6161 --data-dir /tmp/librefolio-r2-d-prodcopy`, cioè il mio server di review, poi ho mandato un SIGTERM al figlio uvicorn (PID 70702): arresto pulito, 6161 libera prima del riavvio. Nessun processo di altre corsie toccato.
  > - Chiavi del planner senza uso (lista di fine round, decisione (a)): 39 usate in HEAD e ora non più (fra cui `route.ready`, `route.capHint`, `route.priorityHint`, `route.none`, `route.fee`, `route.noPrice`, `routing.unitRule`, `routing.capRule`, `routing.previous`, `routing.next`), più 4 nate nei giri UI e già superate (`assetEditor.addCategory`, `assetEditor.weight`, `brokers.localHere`, `ownedAssets.noBroker`, quest'ultima della vecchia versione a spunte del dialogo). Elenco completo in `/tmp/libreFolio_d_ui12/unused_r7.log`. `routing.asset` resta in uso (`TargetsStep`, `DistributionDialog`).
  > - Nessun test automatico, su richiesta del developer. Debito per il giro dei test: regressione R7.4 con lo scrittore vero, guardia `totalOver`, ordine degli Asset, `brokerNoMode`/`routeNoMode` nell'Instradamento.

#### Round 8 — Broker, Asset di LibreFolio in sola lettura, Instradamento per Broker, tetto facoltativo, distribuzione ✅ 2026-09-30

**Feedback del developer** (R7.7, 30/09), in sostanza («stiamo migliorando ma devi continuare a lavorarci»):
1. Editor del Broker (passo 3): via il badge «Copiato · data/ora».
2. Instradamento: al contrario. Per ogni Broker si sceglie quali Asset può comprare, non i Broker per ogni Asset.
3. Gli Asset presi da LibreFolio non si modificano, composizione inclusa. Si modificano solo quelli manuali.
4. Asset manuale: solo nome e tipo, più al massimo un campo ticker che accetti anche un ISIN o un altro codice.
5. «Acquisto massimo *» non obbligatorio: vuoto = nessun limite (oggi mostra 1000000000).
6. Obiettivi → «Copia la distribuzione attuale»: il modale resta vuoto prima che compaia il testo; deve usare la DataTable del progetto; il badge «8 giorni prima del 30/09/2026» continua a non essere chiaro.

**Lettura del codice** (30/09):
- **Tetto** (`schemas/pac_allocator.py:523-537`): `OrderCap` ha solo `quantity`/`notional`, quindi oggi è obbligatorio e il frontend manda `1000000000` (`defaults.ts:8-11`, `TODO(Q-C0-5)`). Il limite vero è già calcolato altrove: `_order_upper_bounds` (`evaluator.py:791-823`) usa `min(tetto, risorse)` per un acquisto e `min(tetto, posizione)` per una vendita, e il compilatore passa a SCIP `ub=access.upper_quanta` (`compiler.py:147`). Senza tetto il limite resta finito (risorse o posizione). Siti del tetto: normalizer `:507-511`, `:549-569`, `:940-943`, `:1032`; evaluator `:318-321`, `:546`, `:802`, `:2530-2535`; il fatto di vincolo accetta già `upper_bound=None` (`models.py:1278`). L'oracolo esaustivo non legge il tetto.
- **Asset di LibreFolio**: `models.py:640` dà sempre un tipo (`AssetType.OTHER` di default). Un Asset senza prezzo salvato viene rifiutato dal normalizer (`allocation.price_missing`, `normalize.py:239-244`). Il ricarico prima di «Calcola» (`refreshPlan`, `copies.ts:568`) rilegge solo i prezzi copiati (`priceIsCopied`, `draft.svelte.ts:225`): un Asset rimasto senza prezzo non verrebbe mai riletto.
- **Asset manuale**: l'identità sul wire è `name`, `ticker` (1–128 caratteri), `asset_class` (`schemas:335`). Il codice interno si genera con `draft.nextId('manual-asset')`: il contatore (`draft.svelte.ts:294`, `:348`) è monotono e non collide con `asset:N` (`copies.ts:78`).
- **Instradamento**: `DraftRoute` (`draft.svelte.ts:139-151`) è già una coppia Asset × Broker (`routeKey`); cambia solo la presentazione. L'ordine sul wire (`request.ts:353-376`) resta.
- **Distribuzione**: `DistributionDialog.svelte:111-133` è una `<table>` scritta a mano; la tabella compare solo quando la lettura è finita. `DataTable` (`$lib/components/table/DataTable.svelte`) ha `isLoading` (riga con spinner), celle personalizzate e `align`.
- Nessun E2E e nessun test unitario usa i testid che cambiano (l'unico test del planner è `result/StateNotice.test.ts`).

**Decisioni:**
- **Tetto facoltativo, contratto**: nuovo `NoOrderCap` (`kind: "none"`, come `NoOrderMinimum`) nell'unione `OrderCap`; `ExactOrderRoute.cap: ExactOrderCap | None`. Senza tetto il normalizer salta i controlli sul tetto (positività, unità, valuta, minimo oltre il tetto); l'evaluator usa solo il limite delle risorse o della posizione, e il fatto `ORDER_CAP` ha `upper_bound=None`, sempre soddisfatto. `contract_version` resta `2.0.0` (contratto non ancora uscito). Dopo l'integrazione serve `api sync`.
  - **Inversione di una nota del Round 7**: la R7.6 diceva che il tetto «resta un numero visibile (nasconderlo come "nessun limite" sarebbe una politica nascosta)». Ora il «nessun limite» è vero: non c'è più un 1e9 nascosto, il limite è quello delle risorse, che il motore calcolava già.
- **Asset di LibreFolio in sola lettura**: «Modifica» solo per gli Asset manuali. Via i badge «Modificato» e il ripristino di prezzo e composizione (codice morto per il principio del 25/09; le chiavi restano, decisione (a)).
  - Un Asset di LibreFolio senza prezzo salvato: l'aiuto lo dice e porta alla pagina dell'Asset (nuova scheda: il draft vive solo in memoria); prima di «Calcola» il prezzo si rilegge anche per questi Asset. Se ancora manca, il backend lo segnala come oggi.
  - Conseguenza da dire al developer: con la sola lettura stretta non si può scrivere a mano il prezzo di un Asset di LibreFolio.

**Passi:**
- R8.0 ✅ 2026-09-30 — questa sezione.
- R8.1 ✅ 2026-09-30 — `BrokerEditor.svelte`: via `formatCopyStamp`, `copyStamp` e il suo `OriginBadge`. Resta il badge sulle card (`BrokersStep.svelte:183`).
  > **Note implementazione**: tolto l'`OriginBadge` dell'intestazione per entrambe le origini: un Broker copiato ha già «Ripristina i valori copiati», uno manuale ha il nome modificabile. Via anche gli import `locale`, `formatCopyStamp` e `OriginBadge`, rimasti senza uso. Il testid `pac-planner-broker-editor-origin` non ha lettori.
- R8.2 ✅ 2026-09-30 — Instradamento per Broker: una zona per Broker operativo (icona, nome, valute); dentro, un interruttore per ogni Asset nell'ordine del passo Asset, con i campi della rotta. Helper del draft per le rotte di un Broker.
  > **Note implementazione**: `draft.routesOfBroker(brokerKey)` sostituisce `routesOf(assetKey)` (unico chiamante era il passo; nessun test). `RoutingStep.svelte` riscritto: una `section` per Broker operativo nell'ordine dei Broker (`pac-planner-routing-broker`, `data-broker-key`), con icona 28 px, nome che scorre, e una riga per modalità (`CurrencyCode` + tipo · passo · commissione). Un Broker senza modalità lo dice una volta nell'intestazione, non su ogni Asset; la riga rossa per Asset (`routeNoMode`) resta solo se il Broker ha modalità ma nessuna nella valuta del prezzo. Ogni Asset è una `TOGGLE_CARD` (`pac-planner-route` con `data-asset-key` e `data-broker-key`): icona, ticker + nome che scorre, tipo, valuta della modalità usata. Pillole «Consenti tutti» / «Escludi tutti» e conteggio per Broker, come nel dialogo degli Asset posseduti. I campi della rotta sono quelli di prima, rientrati sotto il titolo (`sm:pl-10`). Il testid `pac-planner-routing-asset` sparisce: nessun lettore.
  > **⚠️ Fuori pista**: le pillole «Consenti tutti» / «Escludi tutti» non erano nel feedback; aggiunte perché con la vista per Broker l'unico modo di escludere un Broker da tutto sarebbe un clic per Asset. Da confermare col developer.
- R8.3 ✅ 2026-09-30 — Asset di LibreFolio in sola lettura; aiuto e collegamento per il prezzo mancante; rilettura del prezzo mancante prima di «Calcola».
  > **Note implementazione**: `AssetsStep.svelte` — «Modifica» solo per `origin === 'manual'`; via i badge «Modificato» di prezzo e composizione (`samePrice`/`compositionModified` non servono più al passo); l'aiuto del prezzo copiato non ha più il ramo «modificato». Prezzo non memorizzato: testo nuovo (`priceNotStored`) e link «Apri la pagina dell'Asset» (`/assets/{id}`, nuova scheda, `pac-planner-asset-open-page`, icona `ExternalLink`). `priceAuto` riscritto: i dati dell'Asset sono quelli di LibreFolio, solo un Asset manuale si modifica. `copies.ts` — `refreshPlan` include anche gli Asset di LibreFolio in attesa del primo prezzo (`priceAwaitsRead`); `refreshCopiedFacts` li riempie se il prezzo ora c'è (conta in «prezzi aggiornati»), altrimenti non li elenca fra i mancanti: il prezzo resta vuoto e lo segnala il calcolo. `AssetEditor.svelte` ridotto al solo Asset manuale: via ramo d'identità copiata, `typeEditable`, `CategoryLabels`, aiuto del prezzo copiato, «Ripristina» di prezzo e composizione. Codice morto rimosso (principio del 25/09): `restoreCopiedPrice`/`restoreCopiedExposures` (`copies.ts`), `compositionRows`/`compositionModified` (`draft.svelte.ts`); nessun test li nominava (grep su `src` e `e2e`).
- R8.4 ✅ 2026-09-30 — Asset manuale: Nome*, Tipo*, «Ticker / ISIN» facoltativo; codice interno automatico; via `manualId`.
  > **Note implementazione**: il modulo ha Nome*, Tipo* e «Ticker / ISIN» (stesso campo `ticker`, 128 caratteri, con aiuto: non collega l'Asset a LibreFolio e non unisce per nome o codice). Il codice interno è `draft.nextId('manual-asset')` (`manual-asset:N`, valido per `PLANNER_ID`, contatore monotono anche dopo `reset`): due Asset manuali con lo stesso nome restano distinti. Via `manualId` da `DraftAsset`, da `draftAssetFromInfo` e dall'editor, con i controlli ID mancante/troppo lungo/duplicato. Titolo del dialogo sempre «Asset manuale». Testid `pac-planner-asset-editor-id` e `-identity`/`-type-text`/`-price-restore`/`-exposures-restore`/`-price-modified`/`-exposures-modified` spariscono: nessun lettore.
- R8.5 ✅ 2026-09-30 — Tetto facoltativo: `NoOrderCap` nel backend, `api sync`, frontend (vuoto = nessun limite, nessun `*`).
  > **Note implementazione**: backend — `NoOrderCap` (`kind: "none"`) nell'unione `OrderCap` (`schemas/pac_allocator.py:531-543`); `ExactOrderRoute.cap: ExactOrderCap | None` (`models.py:439-440`); il normalizer salta positività, unità, valuta e «minimo oltre il tetto» quando il tetto manca, senza cambiare l'ordine dei problemi quando c'è (`normalize.py:508-514`, `:552-575`, `:945-950`); l'evaluator applica `min(massimo, tetto)` solo se il tetto esiste (`evaluator.py:791-821`): il massimo resta il limite delle risorse per un acquisto e la posizione (o 0) per una vendita, quindi SCIP riceve sempre un `ub` finito. Il fatto `ORDER_CAP` resta emesso per ogni rotta, con `upper_bound=None` e `satisfied=True` senza tetto. Controllo d'import senza suite: `TypeAdapter(OrderCap).validate_python({'kind':'none'})` → `kind='none'`. `api sync` (exit 0, log `/tmp/libreFolio_d_r8_apisync.log`): fingerprint dello schema PAC `4d8978e958829b2e912fbeb8b8f3e1d83190dc3a296230bdb20b8741c2617aa2` (era `502e8c48…`); generazione del contratto dei tool `61303d560a1ef3d3dc6861c527c7fa8a8df773e382fe0fac5fd10b0942c253c9` (era `2f30f6ce…`); l'unione generata `OrderCap` ha tre membri. Frontend — via `DEFAULT_ROUTE_CAP` e il suo `TODO(Q-C0-5)` (`defaults.ts`); `syncRoutes` crea rotte con tetto vuoto; `request.ts` manda `{kind: 'none'}` per un tetto vuoto e segnala solo un tetto non numerico (`routeCapMissing` non si usa più); nel passo il campo non ha `*`, ha il segnaposto «nessun limite» e un aiuto nuovo senza `{cap}`. Il draft vive solo in memoria: nessun draft vecchio conserva il 1e9.
  > **⚠️ Fuori pista**: debito di test, da affidare al test-author dopo la review — il test del fingerprint congelato (`test_scripts/test_schemas/test_pac_planner_schemas.py:2999`, atteso `502e8c48…`) va portato a `4d8978e9…`; il fingerprint del ribilanciatore (`17d5625e…`) va riverificato; servono casi `NoOrderCap` per normalizer, evaluator e oracolo.
- R8.6 ✅ 2026-09-30 — `DistributionDialog` su `DataTable`, subito visibile con lo spinner, icona dell'Asset, senza il badge dell'età.
  > **Note implementazione**: la `<table>` scritta a mano diventa la `DataTable` del progetto (`storageKey="pac-planner-distribution"`, senza selezione, azioni, paginazione, filtri, menu contestuale e visibilità delle colonne; `tableLayout="auto"`), dentro `pac-planner-distribution-table` con `data-loading`. Tre colonne: Asset (cella nuova `shared/AssetNameCell.svelte`: `AssetIcon` + nome), Peso (numerica, a destra, ordinabile; `—` senza peso) con denominatore, differenze dalla pagina e quanto nel tooltip dell'intestazione, e Valutazione (prezzo di mercato o ultimo prezzo di transazione con la data, manuale, non posseduto, prezzo o cambio mancante). Il modale è subito pieno: mentre il perimetro o i dati si leggono, la `DataTable` mostra la sua riga con lo spinner (`isLoading`), non un modale vuoto. Via il badge dell'età (`AgeLabel` resta per Rivedi e Cambi) e i testi di fonte e denominatore sullo schermo: la fonte sta nel tooltip accanto a «Broker (solo OWNER)». Corretto un difetto latente: togliendo tutti i Broker restava applicabile la proposta vecchia; ora senza Broker non c'è proposta e la tabella dice «Seleziona almeno un Broker». Codice morto rimosso da `copies.ts`: `daysBefore`, `stale` (`DistributionRow`) e `asOf` (`DistributionProposal`), senza lettori. Testid `-loading`, `-reading`, `-row`, `-age` spariti: nessun lettore (grep su `src` ed `e2e`).
  > **⚠️ Fuori pista**: svelte-check ha trovato 2 errori in `result/text.ts:54`, conseguenza di R8.5: `routeCapText` non conosceva `{kind: 'none'}`. Ora restituisce «nessun limite» (`route.capNone`), e il dettaglio dell'ordine dice «priorità N · nessun tetto» con una chiave sua (`result.detail.routeFactsNoCap`), invece di «tetto nessun limite». Dopo la correzione svelte-check (`/tmp/libreFolio_d_ui12/svelte_check_r8b.log`) dà solo i 3 errori noti fuori scope (`ToolExecutionMetrics.svelte:44`, `TransactionFormModal.test.ts:787`, `:819`) e nessun warning nel PAC.
- R8.7 ✅ 2026-09-30 — i18n solo con `dev.py i18n`, `api sync`, `front build --debug`, riavvio della 6161 (cambia il backend), verifica, feedback del developer. Nessun test automatico, su sua richiesta.
  > **Note implementazione**:
  > - i18n: `python3 /tmp/libreFolio_d_ui12/i18n_round8.py` (log `i18n_round8.log`), 7 aggiunte e 6 aggiornamenti con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py i18n add|update`, tutti rc=0; nessuna rimozione (decisione (a)).
  >   - Aggiunte: `result.detail.routeFactsNoCap`, `route.capNone`, `assetEditor.tickerHelp`, `assets.openAssetPage`, `routing.allowAll`, `routing.excludeAll`, `routing.allowedCount` (plurale ICU in it/fr/es, come `ownedAssets.count`).
  >   - Aggiornate: `assetEditor.ticker` («Ticker / ISIN»), `assets.priceAuto`, `assets.priceNotStored`, `routing.intro`, `routing.introHelp`, `route.capHelp` (via `{cap}`).
  >   - Cataloghi: **4201** chiavi per lingua, stesso insieme nelle 4; sha8 en `6ea4036c`, it `67f88414`, fr `d8a99fe6`, es `94e63abe`.
  > - Verifiche: `keys_r8.py` → manca solo l'artefatto `problems.`; `defaults_vs_en_r8.py` → solo il falso positivo `brokers.feeHelp`; `icu_check_r8.mjs` → 15 casi × 4 lingue (con `allowedCount` a 0, 1 e 2), **0 errori**, nessuna graffa residua. svelte-check: solo i 3 errori noti fuori scope.
  > - `api sync` già fatto in R8.5; nessun cambio del backend dopo.
  > - Build: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front build --debug` → rc=0 (`build8.log`), `start.DMvtZW7F.js`.
  > - Riavvio della 6161: `stop_bash srv6161r7`, questa volta il processo si è fermato davvero (6161 libera, PID 68321 sparito); poi lo stesso comando di F6, shellId `srv6161r8`, log `/tmp/libreFolio_d_f6/server_review_r8.log`. Health 200, `/api/v1/tools/catalog` senza auth 401, scheduler spento, la pagina serve `start.DMvtZW7F.js`; 6151 libera. `git diff --check` pulito.
  > - Chiavi del planner senza uso (lista di fine round, decisione (a); log `/tmp/libreFolio_d_ui12/unused_r8.log`): **47** usate in HEAD e ora non più (le 39 del Round 7 più `assetEditor.manualId`, `manualIdPlaceholder`, `neverByName`, `idMissing`, `idTooLong`, `idDuplicate`, `assetEditor.title`, `origin.modified`), più **8** nate nei giri UI e già superate (`assetEditor.addCategory`, `assetEditor.weight`, `brokers.localHere`, `assetEditor.priceModifiedHelp`, `assetEditor.compositionModifiedHelp`, `assets.priceModifiedHelp`, `assets.compositionModifiedHelp`, `restore`), più `problems.routeCapMissing` (prefisso dinamico, verificato a mano: nessun riferimento) e le 2 già note del commit 5 (`result.proof.floatingFinished`, `result.states.noIncumbent.rejected`). `ownedAssets.noBroker` torna in uso (messaggio della tabella vuota nel dialogo della distribuzione).
  > - Debito di test per il giro dei test (oltre a quello di R8.5): Instradamento per Broker e pillole, Asset di LibreFolio in sola lettura, rilettura del prezzo mancante, codice interno dell'Asset manuale, dialogo della distribuzione su `DataTable` (spinner, nessuna proposta senza Broker), `routeCapText` senza tetto.

#### Round 9 — prezzo auto/manuale, riepilogo sotto i passi, Instradamento essenziale, Cambi per coppia, DataTable, Strategia spiegata, Rivedi, Risultato ✅ 2026-09-30 (R9.0–R9.9); feedback ricevuto il 01/10 → Round 10

**Feedback del developer** (risposta all'`ask_user` del Round 8, 30/09), in sostanza:
1. Asset: di un Asset di LibreFolio si modifica solo il prezzo, con un interruttore auto/manuale. In auto il prezzo si rilegge al «Calcola»; in manuale si usa quello scritto. Il modulo dell'Asset manuale va bene. «Asset manuale» va a destra, nella riga di «Cerca asset» e «Tuoi asset».
2. Layout desktop: il riepilogo spreca una colonna intera; va sotto i passi, come su mobile.
3. Instradamento: la priorità solo se ci sono più Broker. Regola generale: un campo compare solo quando ha senso. Via la valuta dopo i campi: è già all'inizio della card.
4. Cambi: il passo si nasconde o si salta se acquisti e Broker usano tutti la stessa valuta. Altrimenti un blocco per ogni conversione mancante, riempito in automatico quando si può e a mano altrimenti, con un interruttore auto/manuale come quello del PMC dell'ADJUSTMENT in «aggiungi transazione».
5. Obiettivi, «Copia distribuzione»: prende i rapporti attuali del portafoglio fra gli Asset scelti, portati a 100? Se sì va benissimo, ma l'interfaccia deve renderlo certo. Eventualmente con l'estetica del `DistributionEditor`.
6. `DataTable` per tutte le tabelle, negli Obiettivi e altrove.
7. Strategia: descrivere cosa fa e la catena di fallback; spiegare «distanza L2» a parole o con un link.
8. Rivedi: i 2 pulsanti e le 2 tabelle su `DataTable`, e una spiegazione al developer; hanno molti badge ed errori di design già corretti altrove.
9. Risultato:
   - prima la tabella dell'allocazione, poi quella del «riuso dei margini»; aperte solo queste due, le altre chiuse;
   - nazionalità: 2 mappe (prima/dopo) con la stessa scala di colori; passando su un paese di una delle due, l'infobox mostra la variazione;
   - tipo e settori: barre ECharts, prima e dopo affiancate.
10. Altre deviazioni di stile: libero di correggerle, il developer darà feedback.

**Lettura del codice** (30/09):
- **Distribuzione attuale** (`backend/app/services/portfolio_allocation_source.py:1542-1655`): valori di mercato del motore di portafoglio (lo stesso della pagina Allocazione) solo per gli Asset dello scenario, liquidità esclusa; pesi `_largest_remainder_weights(values)` sul totale degli Asset scelti (somma esatta 1, quanto 0.0001). Un Asset posseduto senza valutazione blocca tutti i pesi (`incomplete`). Quindi **sì**: sono i rapporti attuali fra gli Asset scelti, portati a 100%. Un Asset manuale riceve 0 (`copies.ts`, `distributionProposal`).
- **Risultato PAC**: `PacExposurePlanRow` (`schemas/pac_allocator.py:1479`) ha solo `target_weight` e `final_weight`, senza «prima» né scarto. In un PAC puro il «prima» è 0 per costruzione: il calcolo non legge le posizioni (pagina utente, «How its target is meant to be read»). Mappe e barre confrontano quindi **Obiettivo** e **Dopo**, con la stessa scala. La variazione nell'infobox è «obiettivo → dopo» con la freccia di `compareDecimal`, senza sottrazioni nell'interfaccia. Alternativa, da chiedere: un `residual_weight` calcolato dal backend (cambio di contratto).
- **«Riuso dei margini»**: nessun pannello ha questo nome. Dalle richieste precedenti del developer («tabelle che dicono cosa impostare sui broker», poi «una seconda soluzione che raccoglie i margini di liquidità e li spalma per investire tutto») la lettura più probabile è il Piano operativo (ordini e movimenti di liquidità). Scelta: Allocazione e Piano operativo aperti, gli altri chiusi; domanda al developer.
- **Strategia** (`backend/app/services/pac_allocator/objectives.py:234-246`), cascata `proportional`:
  1. `fixed_l2` = Σ(valore dopo − valore obiettivo)². Il valore obiettivo è peso × riferimento fisso; il riferimento fisso (`evaluator.py:2221`) è investito attuale + liquidità raggiungibile, cioè 0 + liquidità nel PAC.
  2. `shortfall`.
  3. `route_priority` = Σ priorità delle rotte usate: vince il numero più basso.
  4. `explicit_cost` = commissioni + spread FX + margine di esecuzione.
  5. `active_order_rows`.
  6. Spareggio canonico.
  Ogni obiettivo decide solo fra i piani a pari merito sul precedente. La pagina utente (`mkdocs_src/docs/user/tools/pac-allocator/index.en.md`) non spiega la cascata: un link non basta, la spiegazione va nel passo. Debito docs per il docs-writer.
- **Tabelle da portare su `DataTable`**: `TargetsStep.svelte:43`, `ReviewStep.svelte:123`, `result/AssetTable.svelte:22`, `result/LedgerTable.svelte:42`, `result/OperationalPlan.svelte:96`, `result/ProofPanel.svelte:99`.

**Decisioni:**
- **Prezzo auto/manuale**: un flag esplicito `priceManual` su `DraftAsset`.
  - In auto il prezzo è quello letto da LibreFolio, riletto prima di «Calcola».
  - In manuale il valore scritto non si tocca mai e va sul wire con provenienza manuale, anche se è uguale alla copia.
  - Rovescia in parte R8.3 (sola lettura): tutto il resto (nome, tipo, composizione) resta non modificabile.
- **Cambi**: stesso schema, con un flag `manual` su `DraftFx`. Le coppie sono quelle di `requiredPairs`, senza aggiunta libera. Il passo sparisce dalla navigazione quando non serve nessuna coppia.
- **Mappe e barre**: Obiettivo contro Dopo (vedi sopra).

**Passi:**
- R9.0 ✅ 2026-09-30 — questa sezione.
- R9.1 ✅ 2026-09-30 — Asset: prezzo auto/manuale per gli Asset di LibreFolio; «Asset manuale» a destra.
  > **Note implementazione**: `DraftAsset.priceManual` (in memoria, nessuna migrazione del draft). `priceIsCopied` è falso in manuale, quindi il prezzo va sul wire con provenienza manuale anche se è uguale alla copia (`request.ts:255`), e `refreshPlan`/`refreshCopiedFacts` non lo rileggono. `priceAwaitsRead` esclude il manuale. `applyPriceCopy` in manuale sposta solo il riferimento (`copiedPrice`/`priceStamp`/`priceSource`) e conta «invariato». Nuovo `setPriceManual` (`copies.ts`): verso manuale parte dal prezzo a schermo, o da un importo vuoto nella valuta del prezzo copiato o, in mancanza, in quella dell'Asset (`getAssetInfo`); verso auto rimette il prezzo copiato, o lo svuota e il passo rilancia subito la lettura. Nuovo `shared/AutoManualToggle.svelte` (le pillole del PMC di `WacPreviewSection.svelte:363-380`, `aria-pressed`, `data-mode`), riusato in R9.4. `AssetsStep.svelte`: l'interruttore sta a destra della riga del prezzo, solo per gli Asset di LibreFolio; in manuale `ExactDecimalInput` + `CurrencyCode` + «/ N unità» + aiuto che mostra il prezzo di LibreFolio che «Auto» ripristina; «Asset manuale» a destra (`ml-auto`), l'aiuto «Dati da LibreFolio» accanto a «Tuoi Asset»; il «!» e `data-price` contano anche un prezzo manuale vuoto; nuovo `data-price-mode`. `review.ts`: in manuale l'origine è manuale e, se esisteva una copia, «modificato» (coerente con `factCounts`). i18n raccolte in `/tmp/libreFolio_d_ui12/i18n_round9.py`, applicate in R9.9.
- R9.2 ✅ 2026-09-30 — Layout: riepilogo sotto i passi anche su desktop.
  > **Note implementazione**: `PacPlannerTool.svelte` — la griglia desktop passa da tre colonne (passi · passo · riepilogo) a due (`minmax(11rem,13rem)` · passo). A ogni larghezza c'è un solo blocco: una card con `StepNav` (verticale su desktop, orizzontale o compatta sotto) e, sotto, «Riepilogo» apribile a richiesta, come già su mobile; su desktop la card resta `sticky top-4`. Il passo guadagna la colonna del riepilogo (~15rem). Nessun lettore dei testid del riepilogo fuori dal componente (grep su `e2e`).
- R9.3 ✅ 2026-09-30 — Instradamento: priorità solo con più Broker per l'Asset; via i suffissi di valuta.
  > **Note implementazione**: `RoutingStep.svelte` — la «Priorità» compare solo se l'Asset è ammesso su più di un Broker operativo (conteggio `$derived` sulle rotte abilitate), oppure se contiene già un valore diverso da 0 o non valido: un valore nascosto agirebbe senza che l'utente lo veda (`objectives.py:150-164`, la priorità somma anche le rotte singole). Via le colonne `INPUT_SUFFIX` dopo i campi: in modalità importo la valuta è già nella card e nella riga; in modalità unità «unità» e il «%» del margine stanno dentro il campo (`INPUT_ADORNMENT` nuovo in `ui.ts`, il campo si riserva lo spazio con `pr-*`, come `PasswordInput`), così i campi di una riga hanno la stessa larghezza. Ordine: minimo, obbligatorio, massimo, poi margine e (se serve) priorità. svelte-check: solo i 3 errori noti fuori perimetro.
- R9.4 ✅ 2026-09-30 — Cambi: passo dinamico, un blocco per coppia con interruttore auto/manuale e lettura automatica.
  > **Note implementazione**:
  > - **Coppie necessarie** (`draft.svelte.ts:636-694`): chiusura in due parti, calcolata come il backend (`normalize.py:639-650`). `valuationPairs`: ogni valuta citata (prezzi, liquidità, contributi) contro la valuta di valutazione. `conversionPairs`: ogni cassa di un Broker contro la valuta del prezzo di ogni Asset che quel Broker può comprare. `requiredPairs` è l'unione; `fxPurpose(pair)` dice valutazione, conversione o entrambe; `fxNeeded`; `visibleSteps` toglie `fx` da `PLANNER_STEPS` quando non serve nessuna coppia. `PacPlannerTool.svelte:100` mostra comunque tutti i passi mentre si è su «Cambi» o c'è un problema dei Cambi, così il passo non sparisce sotto l'utente. `DraftFx.manual` nuovo (`:168`, in memoria, nessuna migrazione del draft).
  > - **`copies.ts`**: `rateAwaitsRead` (auto, tasso vuoto, mai letto), `setRateManual` (verso manuale parte dal tasso a schermo; verso auto rimette `copiedRate`, o svuota e il passo rilegge), `applyAwaitingFxRates` (riempie solo le coppie ancora in attesa, mai un tasso scritto a mano). `refreshPlan` include le coppie in attesa, quindi una coppia auto mai visitata si legge prima di «Calcola».
  > - **`fxRead.svelte.ts`** nuovo, `FxRateReader`: legge le coppie in attesa all'apertura del passo (`pending`), una lettura nuova assorbe le coppie della precedente; memoria per draft (`WeakMap`: `attempted`, `missed`, `ownerless`) che sopravvive all'uscita dal passo, così non rilegge a ogni visita una coppia che LibreFolio non ha. Errore con «Riprova» solo per le coppie fallite.
  > - **`request.ts:193-198`, `:386-402`**: sul wire vanno solo le `requiredPairs`; lo spread si valida solo se ci sono conversioni (senza conversioni un valore non valido va come 0, il backend lo applica solo alle conversioni: `objectives.py:205`, `constraints.py:421/576`).
  > - **Rivedi/Riepilogo**: righe dei cambi solo con coppie necessarie (`review.fxRated`, `summary.rates`); `ReviewStep`, `SummaryPanel`, `review.ts`.
  > - **`steps/FxStep.svelte` riscritto** (backup `/tmp/libreFolio_d_ui12/FxStep.r8.svelte`): una card per coppia (`pac-planner-fx-pair`, con `data-pair`, `data-purpose`, `data-mode`, `data-rate`, `data-read`), titolo «BASE → QUOTE» con `CurrencyCode`, `AutoManualToggle` (`pac-planner-fx-mode`), badge dello scopo con aiuto (valutazione in `{valuta}`, conversione fra casse). Manuale: «1 BASE =» + `ExactDecimalInput` + QUOTE e aiuto col tasso che «Auto» ripristina. Auto: il tasso letto con la sua data nell'aiuto; durante la lettura uno spinner; senza Broker posseduto un avviso; coppia che LibreFolio non ha un avviso e il link alla pagina Cambi (`/fx`, nuova scheda); altrimenti «si legge prima del calcolo». Lo spread compare solo con conversioni, col «%» dentro il campo (`INPUT_ADORNMENT`). Via l'aggiunta libera di coppie, «Copia», il dialogo, la rimozione e il ripristino. Radice con `aria-busy`/`data-busy`.
  > - svelte-check (`/tmp/libreFolio_d_ui12/check9_4.log`): solo i 3 errori noti fuori perimetro. Nessun test o E2E usa i testid tolti (grep su `e2e` e `src`).
  > - **Codice senza più uso** (inventario, da togliere solo dopo test-triage; `/tmp/libreFolio_d_ui12/dead_r94.log`): `steps/SourceCopyDialog.svelte` (nessun import; il suo unico utente era `FxStep`), e con lui `applyFxCopy`, `applyPriceCopy`, `applyClassificationCopy` (`copies.ts:305/490/559`; gli ultimi due senza uso reale dal R6), le varianti `fx`/`price`/`exposures` di `CopyConflict` e i loro rami in `resolveConflicts` (`copies.ts:786-818`, oggi solo `cash` è raggiungibile), `restoreCopiedRate` (`copies.ts:823`), `draft.fxPairs` (`:697`, letto solo dal codice morto) e `draft.removeFx` (`:707`). Restano vivi `CopyFlow`/`CopyFlowView` (Liquidità, Broker), `AgeLabel` (Rivedi, da rivedere in R9.7), `OriginBadge`.
  > - **Chiavi senza più uso** (lista di fine round, decisione (a); `/tmp/libreFolio_d_ui12/unused_r94.log`): 10 in più rispetto al Round 8, `add`, `fx.addFrom`, `fx.addTo`, `fx.copy`, `fx.pairsHint`, `fx.remove`, `restoreCopied`, `review.fx`, `review.noFx`, `summary.pairs`. Le chiavi nuove del passo sono in `i18n_round9.py`, applicate in R9.9.
  > **⚠️ Fuori pista**: `PortfolioPlannerSourceRequest.broker_ids` ha `min_length=1` (`backend/app/schemas/portfolio.py:1264-1272`): senza un Broker posseduto non si può leggere nessun tasso. Il lettore lo ricorda come «nessun Broker» invece di chiamare l'API. Lo stesso limite toccava «Calcola»: con coppie o prezzi in attesa e nessun Broker, `refreshCopies` chiedeva una lettura impossibile e si fermava con errore. Ora `copiedOnly` (`copies.ts:659`) toglie dal piano le prime letture, così il calcolo parte e segnala come mancante ciò che manca; un fatto già copiato si rilegge ancora. Nessun cambio del backend.
- R9.5 ✅ 2026-09-30 — Obiettivi su `DataTable` (stile `DistributionEditor`) e dialogo della distribuzione esplicito.
  > **Note implementazione**: `steps/TargetsStep.svelte` riscritto (copia in `/tmp/libreFolio_d_ui12/TargetsStep.r8.svelte`). In alto intro breve e, a destra, «Copia la distribuzione attuale» con icona `PieChart` e aiuto `targets.copyHelp` (stessa regola di abilitazione). La tabella è una `DataTable` senza ordinamento, paginazione, selezione, filtri né resize: colonne Asset (`AssetNameCell` con icona), barra e Obiettivo %. La barra è quella del `DistributionEditor` (`:137`, `:367`): lunga rispetto al peso più alto, verde a 100%, rossa sopra, ambra sotto. L'obiettivo è la nuova `shared/TargetInputCell.svelte`: `ExactDecimalInput` con suffisso `%`; legge e scrive `draft.data.targets[key]` da sé, quindi l'istanza resta e il fuoco non si perde. Ogni riga ha nel menu ⋮ «Bilancia al 100%»: aggiunge all'obiettivo il mancante, o toglie l'eccesso, con `sumControlPercentages` e limiti 0–100 via `compareDecimal`; nessun `Number` per i valori. Sotto, il totale nello stile del badge `DistributionEditor` (`:523-535`), con `data-state` `balanced|excess|missing|unknown` e aiuto `targets.totalHelp`. Via dallo schermo «(controllo informativo)», che era falso: `request.ts:189-191` blocca il calcolo con totale ≠ 100. `DistributionDialog.svelte`: sottotitolo visibile `distribution.subtitle` («insieme fanno il 100%»), con la vecchia regola in un aiuto; colonna barra; riga di totale nel `footerCells` solo con stato `complete`, dove il backend garantisce somma esatta 1 (`schemas/portfolio.py:1522-1526`, largest remainder). svelte-check: solo i 3 errori noti fuori scope, 0 avvisi del planner.
  > - **Test da riallineare** (debito per il test-author): i testid `pac-planner-target` e `data-asset-key` passano dalla riga `<tr>` al contenitore dell'input nella cella; nuovi `pac-planner-target-bar`, `pac-planner-targets-total`, `pac-planner-target-balance` (menu ⋮, `row-actions-{key}`), `pac-planner-distribution-subtitle`/`-rule`/`-bar`. Nessuna E2E o unit li usa oggi (verificato con grep).
  > - **Chiavi**: 5 nuove (`targets.copyHelp`, `targets.excess`, `targets.balance`, `targets.totalHelp`, `distribution.subtitle`), 4 aggiornate (`targets.intro`, `targets.total` senza segnaposto, `targets.remaining` «{value} mancante», `targets.wire` come aiuto della colonna). Senza più uso: `targets.control`. Tutto in `i18n_round9.py` (ADD=25, UPDATE=8, dry run verde).
- R9.6 ✅ 2026-09-30 — Strategia: descrizione, catena, L2 a parole.
  > **Note implementazione**: `steps/StrategyStep.svelte` riscritto (copia in `/tmp/libreFolio_d_ui12/StrategyStep.r8.svelte`), con la catena del backend come fonte: `objectives.py:1-9` e `:234-246` (`build_objective_cascade`: `fixed_l2` → `shortfall` → `route_priority` → `explicit_cost` → `active_order_rows`), stadi `:109-221`, spareggio canonico `:224-231` e `evaluator.py:3089` (`canonical_key`); solo acquisti da `constraints.py:5`. In alto un'intro in una frase (`strategy.intro`): la strategia sceglie il migliore fra i piani che rispettano i passi precedenti. Ogni strategia è una card: radio (`accent-libre-green`) con nome e, sotto, cosa cerca a parole (`policyHelp.{policy}`, testid `pac-planner-policy-help`). Nella card la sezione «Come sceglie il piano, in ordine» con la regola della catena (`strategy.cascadeRule`, testid `pac-planner-policy-rule`: ogni criterio decide solo fra i piani ancora alla pari su quelli sopra) e la lista numerata (`ol` `pac-planner-policy-objectives`, `li[data-objective]`, bolla `ICON_BUBBLE`): nome del criterio più una riga che dice cosa preferisce (`objectiveHelp.{code}`). Un «?» solo dove la riga non basta: la distanza L2 spiegata a parole (differenza fra valore comprato e quota del denaro, al quadrato, sommata; il quadrato pesa di più gli scarti grandi; valore al prezzo dell'Asset, senza commissioni né margine) e dove si scelgono i numeri di priorità (passo Route per gli Asset comprabili su più Broker, passo Broker per le fonti; vince il più basso, tutti a 0 = nessuna preferenza), testid `pac-planner-objective-help`. In fondo lo spareggio finale (icona `Equal`, testid `pac-planner-policy-tie-break`): ordine fisso di Asset e Broker, stesso input → stesso piano. Via dallo schermo «Le strategie vengono dal contratto del backend» e «Parametri aggiuntivi: nessuno». Nomi dei criteri resi leggibili: «Vicinanza agli obiettivi (distanza L2)», «Liquidità non investita» (senza «(U)»), «Priorità di Broker e fonti»; allineati i fallback EN di `policies.ts` (`OBJECTIVE_FALLBACKS`, copia in `/tmp/libreFolio_d_ui12/policies.r8.ts`). svelte-check: solo i 3 errori noti fuori scope, 0 avvisi del planner (`/tmp/libreFolio_d_ui12/svelte_check_r96.log`).
  > - **Riuso**: le etichette `objectives.*` compaiono anche in `result/ProofPanel.svelte:33`/`:141`, che quindi prende i nomi nuovi. Lo spareggio grezzo (`ProofPanel.svelte:148`, «canonical_key») si sistema in R9.8.
  > - **Test da riallineare** (debito per il test-author): nuovi testid `pac-planner-policy-help`, `pac-planner-policy-rule`, `pac-planner-policy-objectives`, `pac-planner-objective-help`, `pac-planner-policy-tie-break`; `pac-planner-policy` resta sulla card con `data-policy`. Nessuna E2E o unit usa i testid della Strategia (verificato con grep).
  > - **Debito docs** (docs-writer, EN): la catena con le stesse parole, e dove si impostano le priorità.
  > - **Chiavi**: 11 nuove (`policyHelp.proportional`, `objectiveHelp.{fixed_l2,shortfall,route_priority,explicit_cost,active_order_rows}`, `strategy.{cascadeRule,l2Help,priorityHelp,tieBreakTitle,tieBreak}`), 5 aggiornate (`strategy.intro`, `strategy.cascade` senza due punti, `objectives.{fixed_l2,shortfall,route_priority}`). Senza più uso: `strategy.fromContract`, `strategy.noParameters`. `i18n_round9.py`: ADD=36, UPDATE=13, dry run verde, nessuna chiave ADD già presente.
- R9.7 ✅ 2026-09-30 — Rivedi: due `DataTable`, filtri standard al posto dei 2 pulsanti.
  > **Note implementazione**:
  > - **Cosa c'era** (per la spiegazione al developer): i 2 pulsanti «Snapshot completo» / «Solo modificati / non del giorno» erano due viste della **stessa** tabella dei fatti, cioè un filtro. Sopra, un elenco dei passi con «Modifica», e un banner fisso sugli ordini.
  > - **`steps/ReviewStep.svelte` riscritto** (copia in `/tmp/libreFolio_d_ui12/ReviewStep.r8.svelte`):
  >   1. In alto una frase (`review.lead`) con un «?» (`review.help`, testid `pac-planner-review-help`): il calcolo usa solo questi dati, e subito prima rilegge ciò che è preso da LibreFolio e non modificato (`copies.ts:611-720`).
  >   2. **Tabella dei passi** (`DataTable`, testid `pac-planner-review-sections`): colonne Passo (icona verde/ambra e nome, `data-step`, `data-blocked`) e Riepilogo (testo e chip di valuta). Clic sulla riga o ⋮ «Modifica» (`pac-planner-review-goto`) → il passo. Riepiloghi riscritti a parole: «2 Broker · 1 conto esterno», «5 Asset · 1 senza prezzo · 2 prezzi non di oggi», «4 di 5 Asset acquistabili», «5 di 5 Asset con un obiettivo», «3 cambi · 1 senza tasso». Riga dei Cambi solo se servono coppie o c'è un problema lì (come R9.4).
  >   3. I problemi (`pac-planner-review-problems`, `IssueList`) sotto la tabella.
  >   4. **Tabella dei dati** («Dati del calcolo (N)», chiusa di default, `pac-planner-review-facts-toggle`, `aria-expanded`): `DataTable` con ordinamento e filtri di colonna (testid `pac-planner-review-facts`). Colonne Dato (icona del Broker, del versamento o dell'Asset, come nei passi; il filtro di testo cerca anche i codici valuta), Tipo (filtro enum: Broker, Liquidità, Versamento, Prezzo, Composizione, Cambio), Valore, Origine (filtro enum: LibreFolio, Manuale, Modificato). ⋮ «Modifica» (`pac-planner-review-fact-goto`). I 2 pulsanti diventano il filtro Origine, multiplo: «Manuale» + «Modificato» è la vecchia vista «solo modificati».
  >   5. Origine senza badge per LibreFolio: testo grigio e, se il valore non è di oggi, la data in ambra con un aiuto (`review.staleTitle`, testid `pac-planner-review-fact-stale`). Badge solo per Manuale e Modificato (`OriginBadge`).
  >   6. Pulsanti centrati; il banner «nessun ordine» diventa una riga di nota sotto (`review.noOrdersHint`).
  > - **`shared/ReviewCell.svelte`** nuovo: renderer delle celle delle due tabelle (`step`, `summary`, `entity`, `value`, `origin`). `review.ts`: `SectionCounts.assets.missing`/`fx.missing`, `FactSubject`, `FactOriginState`, `factOriginState`, valore `modes` (valute degli ordini o «Conto esterno»).
  > - Solo conteggi nell'interfaccia; nessun importo sommato o convertito. svelte-check (`/tmp/libreFolio_d_ui12/svelte_check_r97.log`): solo i 3 errori noti fuori perimetro, 0 avvisi del planner.
  > - **Codice senza più uso** (inventario, da togliere solo dopo test-triage): `shared/AgeLabel.svelte` (nessun import).
  > - **Chiavi**: 16 nuove (`review.lead`, `help`, `colSummary`, `colKind`, `kind.{broker,cash,contribution,price,exposures,fx}`, `origin.librefolio`, `staleTitle`, `ordersIn`, `externalAccount`, `noOrdersHint`, `factsToggle`; `review.fxRated` riscritta in `i18n_round9.py` prima di applicarla), 6 aggiornate (`factEntity` «Dato», `factsEmpty` come messaggio dei filtri, `brokers`, `assets`, `routes`, `targets`). Senza più uso (lista di fine round, decisione (a); `/tmp/libreFolio_d_ui12/unused_r97.log`): `review.factsAll`, `factsChanged`, `factsLabel`, `intro`, `noOrders` (più `review.fx`, `review.noFx` già in R9.4). `i18n_round9.py`: ADD=52, UPDATE=19, dry run verde, verifica catalogo pulita (`r9_batchcheck.py`).
  > - **Test da riallineare** (debito per il test-author): nessun test usa oggi i testid del Rivedi (grep su `e2e` e `src`); nuovi `pac-planner-review-sections`, `-section` (`data-step`, `data-blocked`), `-facts-toggle`, `-facts`, `-fact` (`data-kind`, `data-origin`, `data-stale`), `-fact-stale`, `-fact-goto`, `-help`.
- R9.8 ✅ 2026-09-30 — Risultato: ordine e apertura dei pannelli; tabelle su `DataTable`; mappe Obiettivo/Dopo; barre ECharts.
  > **Note implementazione**:
  > - **`result/ResultView.svelte` riscritto**. Ordine: esito (`OutcomeHeader`), avviso di stato (`StateNotice`), note, `KpiCards`, poi i pannelli **Allocazione per Asset**, **Piano operativo** (solo se ci sono passi, con il conteggio), **Esposizioni**, **Contabilità per cassa**, **Prova**. Aperti di default solo Allocazione e Piano operativo (`OPEN_BY_DEFAULT`); senza soluzione resta la sola Prova, aperta. «Chiudi/Apri tutti» (`pac-planner-result-toggle-all`) quando i pannelli sono più di uno. Il pannello «Asset» separato confluisce nell'Allocazione; tolti `wide` (anche da `PacPlannerTool.svelte`) e l'`allocationHint`.
  > - **Tutte le tabelle su `DataTable`**, con l'aiuto di ogni colonna in `headerTooltip` e un renderer comune, **`result/ResultCell.svelte`** nuovo (tipi `broker`, `asset` con icona e numero del passo `STEP_NUMBER` di `ui.ts`, `contribution`, `weight`, `bars`, `money`, `exactMoney`, `price`, `instruction`, `label`, `objective`, `solver`).
  >   1. **Allocazione** (`AssetTable.svelte`): Asset fisso a sinistra, obiettivo, dopo, barre (grigio obiettivo, verde dopo, scala sulla barra più larga), valore obiettivo, valore dopo, scarto con segno, acquisto al prezzo mid (commissioni escluse); legenda (`pac-planner-assets-legend`) e piè con base degli obiettivi e investito dopo. Il testid `pac-planner-assets-row` resta, con `data-asset`.
  >   2. **Piano operativo** (`OperationalPlan.svelte`): in alto i passi numerati del finanziamento, con un badge per tipo: liquidità dello stesso Broker, trasferimento, versamento, cambio. La priorità di finanziamento compare solo se per quel Broker e quella valuta le scelte sono almeno 2 (`PlanLookup.fundingChoices`). Poi una tabella di ordini per Broker, con icona: Asset con il numero del passo, istruzione, prezzo mid, addebito in cassa (commissione esclusa, `evaluator.py:1908-1943`), commissione. Un clic sulla riga o l'occhio apre il dettaglio dell'ordine. Tolti l'intestazione «Seq» e l'avviso di privacy.
  >   3. **Contabilità** (`LedgerTable.svelte`): una riga per Broker+valuta, i campi come colonne (`model.ts` `LEDGER_FIELDS`/`ledgerFields`). Si vedono sempre saldo iniziale e saldo finale spendibile; le altre colonne solo se non valgono zero su qualche riga, e il saldo fisico solo se diverso da quello spendibile (`ledgerFields`, `model.ts:262-273`). In un PAC i 4 campi di vendita e imposte (ricavo lordo, commissioni di vendita, imposta trattenuta, imposta accantonata) valgono sempre zero, quindi restano nascosti, e hanno un aiuto comune (`LEDGER_PAC_ZERO_FIELDS` → `ledger.help.alwaysZero`). «Mostra altre N colonne» rivela quelle nascoste. La liquidità dello stesso Broker compare con importi uguali in entrata e in uscita sulla stessa cassa, e l'aiuto lo spiega.
  >   4. **KPI** (`KpiCards.svelte`): 5 voci con un «?» ciascuna: Base degli obiettivi, Investito dopo, Non investito, Costi, Ordini. La riga del finanziamento cambia secondo i dati: se c'è liquidità intrappolata la nomina (`kpi.funding`), altrimenti dice solo quanta è raggiungibile (`kpi.fundingReachable`, `data-trapped`). La scomposizione del non investito omette l'arrotondamento quando è zero (`kpi.shortfallPartsNoRounding`).
  >   5. **Prova** (`ProofPanel.svelte`): i valori esatti degli obiettivi in tabella (`proof.exactValue`); lo spareggio finale a parole (`strategy.tieBreakTitle` + `strategy.tieBreak`, testid `pac-planner-proof-tie-break`) al posto del codice; gli stadi del solver con un badge di stato e l'aiuto su primale, duale e gap. La colonna «Ord» è tolta; la colonna dell'ambito compare solo se gli ambiti sono più di uno.
  > - **Esposizioni** (`ExposureSection.svelte` sostituito): prima i Paesi, su tutta la larghezza; sotto, affiancati su desktop, tipo e settore.
  >   1. **Mappe** (`ExposureMaps.svelte`, nuovo): due mappe ECharts, Obiettivo e Dopo, su **una sola scala di colore** (massimo comune fra i due lati, indicato sotto). Puntando o toccando un Paese lo si evidenzia in entrambe le mappe; zoom e spostamento sono sincronizzati. Il riquadro del tooltip (`exposureTooltip.ts`) mostra i due pesi e la direzione ▲▼= (sopra/sotto/in linea con l'obiettivo), decisa con `compareExact` sui pesi esatti del backend. Le categorie che la mappa non sa collocare («Altro», la quota non classificata, un codice sconosciuto) sono elencate sotto (`pac-planner-exposures-off-map`), così nessun peso manca. Se la mappa non si carica, i pesi restano in elenco (`exposures.mapUnavailable`, `data-state="failed"`). Il componente condiviso `GeographyMap` non è toccato: la mappa registrata è la stessa.
  >   2. **Barre** (`ExposureBars.svelte`, nuovo): barre orizzontali ECharts, Obiettivo in grigio e Dopo in verde come nell'Allocazione, con lo stesso tooltip.
  >   3. Sotto ogni grafico, un elenco `sr-only` con gli stessi numeri (`pac-planner-exposures-values`). Tolto l'avviso `exposures.public`.
  >   4. **Scelta di merito**: il confronto è Obiettivo contro Dopo, perché il risultato del PAC non pubblica un peso «prima». Un peso di partenza chiederebbe un campo nuovo nel contratto del backend: domanda aperta al developer.
  > - **Nessun calcolo economico nell'interfaccia.** `chartPercent`/`weightFraction` convertono un peso pubblicato in numero solo per disegnare (colore, lunghezza della barra), mai per sommare o per mostrare una cifra; segno e confronti passano da `exactSign`/`compareExact` sui valori esatti. Gli importi passano solo dai formattatori mascherabili di `planner/format.ts`.
  > - svelte-check (`/tmp/libreFolio_d_ui12/svelte_check_r98b.log`): solo i 3 errori noti fuori perimetro (`TransactionFormModal.test.ts` ×2, `ToolExecutionMetrics.svelte` ×1), 41 avvisi come prima, 0 avvisi del planner.
  > - **Chiavi**: nel blocco R9.8 di `i18n_round9.py` (da `:393`) ci sono 40 chiavi nuove (`result.assets.bars`/`buyMidHelp`, `exposures.above`/`below`/`equal`/`scale`/`offMap`/`scaleHelp`/`mapUnavailable`, `kpi.fundingReachable`/`shortfallPartsNoRounding`/`help.*` ×5, `plan.*Help` ×4, `plan.kind.cash`/`transfer`/`deposit`, `proof.exactValue`/`help.*` ×5, `ledger.help.*` ×11) e 31 aggiornate. Totale del batch: ADD=92, UPDATE=50. Il dry run e `r9_batchcheck.py` sono verdi. `r98_postcheck.py` confronta i fallback con il catalogo en dopo il batch: 237 coppie, 219 chiavi, 0 differenze.
  > - **Chiavi senza più uso** (lista di fine round, decisione (a); `/tmp/libreFolio_d_ui12/unused_r98b.log`): `result.allocationHint`, `exposures.public`, `plan.funding`, `plan.privacyHint`, `plan.sequence`, `proof.floatingFinished`, `proof.ordinal`, `proof.tieBreak`, `states.noIncumbent.rejected`. Nascoste da una famiglia dinamica ma senza uso: `result.kpi.source`, `result.sections.assets`. Usate solo dal codice morto `WeightBars.svelte`: `result.weights.targetShort`/`finalShort`.
  > - **Codice senza più uso** (inventario, da togliere solo dopo test-triage; `/tmp/libreFolio_d_ui12/dead_r98.log`): `result/WeightBars.svelte` (nessun import); in `result/model.ts` gli export `BadgeTone`, `ResultBadge`, `availableNumber`, `PlanStep`, `RESULT_DIMENSIONS`, `ExposureGroup`, e `weightFraction`, che è usato solo all'interno; in `exposureTooltip.ts` il tipo `ExposureTooltipText`.
  > - **Test da riallineare** (debito per il test-author). Nessun test usa oggi i testid del Risultato: grep su `e2e` e `src`; l'unico test del risultato, `StateNotice.test.ts`, non cambia. Testid tolti o cambiati: `pac-planner-assets-totals`, `pac-planner-solver-stage` (ora sulla cella dell'obiettivo, `data-status`), le righe del ledger (ora `pac-planner-ledger-row` + `pac-planner-ledger-<campo>`), `pac-planner-exposures-bars` (ora il contenitore ECharts, `data-dimension`). Nuovi: `pac-planner-result-toggle-all`, `-assets-legend`, `-plan-fx-amounts`, `data-funding`, `data-trapped`, `-proof-tie-break`, `-kpi-help`, `-exposures-values`/`-row`/`-maps` (`data-state`)/`-map` (`data-side`)/`-off-map`/`-scale`/`-scale-help`.
  > **⚠️ Fuori pista**:
  > - 4 fallback allineati alla terminologia dell'interfaccia prima di scrivere il blocco: `ExposureMaps` `scaleHelp` («Point at a country, or tap it, …»), `OperationalPlan` `midPriceHelp` («…before the price margin.»), `cashDebitHelp` (margine sul prezzo del passo Instradamento, commissioni escluse), `feeHelp` («…set in the Brokers step.»).
  > - Il 30/09 verso le 23:33 il turno si è interrotto per un errore del servizio, non del lavoro. Alla ripresa nessuna modifica è stata rifatta. Le ultime scritture sono state verificate: `ExposureSection.svelte` identico (`cmp`) alla bozza in `/tmp`; `ExposureMaps.svelte` diverso solo nel fallback voluto di `:272`; `OperationalPlan.svelte` completo. svelte-check è verde come prima.
  > - Il primo `unused_r98.log` segnava come inutilizzata anche `proof.reasons.portfolio_rebalancer.sell_irreducibility_unresolved`, ma la chiave è raggiunta dinamicamente da `ProofPanel.svelte:173`, perché il codice è nell'enum di `generated-tools.ts:971`. Il controllo rifatto dopo la ripresa, senza i prefissi dinamici troppo larghi `planner` e `planner.result`, dà le 9 chiavi sopra.
- R9.9 ✅ 2026-09-30 — i18n, svelte-check, build, verifica, feedback. Nessun test automatico, su richiesta del developer.
  > **Note implementazione**:
  > - i18n: `python3 /tmp/libreFolio_d_ui12/i18n_round9.py` (log `i18n_round9.log`) con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py i18n add|update`: **92** aggiunte e **50** aggiornamenti, 0 falliti, nessuna rimozione (decisione (a)). Copia dei cataloghi di prima in `/tmp/libreFolio_d_ui12/pre_apply_r9/`: lo sha8 di en è `6ea4036c`, lo stesso di R8.7, quindi nessuna chiave è cambiata fuori dal batch.
  >   - Cataloghi: **4293** chiavi per lingua (4201 + 92), stesso insieme nelle 4, 0 valori vuoti; sha8 en `2e791937`, it `8157c51b`, fr `3745c50b`, es `2fff98b0`.
  > - Verifiche, tutte a 0 differenze: `r9_applied_check.py` (le 142 chiavi × 4 lingue identiche al batch); `icu_check_r9.mjs` (142 chiavi: sintassi ICU, stessi argomenti nelle 4 lingue, formattazione due volte, nessuna graffa residua); `r98_postcheck.py` (fallback del codice contro il catalogo en: 237 coppie, 219 chiavi). `dev.py i18n audit` → rc=0, «All translations complete» (`i18n_audit_r9.log`).
  > - **Chiavi del planner senza uso, lista unica di fine round** (decisione (a); `unused_r99.py` → `unused_r99.log`, lista in `final_unused_r99.sorted`): **86**. Il controllo copre tutto il namespace: costanti `*KEY*`, famiglie dinamiche tranne le due troppo larghe, chiavi relative al planner a più segmenti. Dà 81 chiavi; le 5 in più sono state verificate a mano: `result.kpi.source` e `result.sections.assets` (nascoste da una famiglia dinamica), `result.weights.{finalShort,targetShort}` (solo il codice morto `WeightBars.svelte`), `problems.routeCapMissing` (Round 8). Il conto torna con le note: Round 8 58 + R9.4 10 + R9.5 1 + R9.6 2 + R9.7 5 + R9.8 11 − `origin.modified`, che è di nuovo in uso (`OriginBadge.svelte:20` produce `'modified'` per `origin.${…}`). Elenco: `add`, `restore`, `restoreCopied`, `assetEditor.{addCategory,categoryId,categoryLabel,class,classHint,compositionModifiedHelp,dimension,exposureAdd,exposures,idDuplicate,idMissing,idTooLong,manualId,manualIdPlaceholder,neverByName,overHundred,priceDate,priceModifiedHelp,title,unclassified,weight}`, `assets.{compositionModifiedHelp,copyClassifications,copyPrices,noAutoPrice,noExposures,priceModifiedHelp}`, `brokerCopy.currencies`, `brokerEditor.{feeRule,localCash,origin,stepRule}`, `brokers.{conversions,fee,funding,localCash,localHere,stepAmount}`, `copy.alreadyInDraft`, `copyNotice.when`, `fx.{addFrom,addTo,copy,pairsHint,remove}`, `problems.routeCapMissing`, `result.allocationHint`, `result.exposures.public`, `result.kpi.source`, `result.plan.{funding,privacyHint,sequence}`, `result.proof.{floatingFinished,ordinal,tieBreak}`, `result.sections.assets`, `result.states.noIncumbent.rejected`, `result.weights.{finalShort,targetShort}`, `review.{factsAll,factsChanged,factsLabel,fx,intro,noFx,noOrders}`, `route.{capHint,fee,noPrice,none,priorityHint,ready}`, `routing.{capRule,next,previous,unitRule}`, `scenario.{asOf,noValues}`, `strategy.{fromContract,noParameters}`, `summary.{date,pairs}`, `targets.control`. Tutte sotto `tools.pacAllocator.planner.`; le 168 chiavi P1 sono una lista a parte.
  > - svelte-check (`svelte_check_r99.log`): 5477 file, solo i 3 errori noti fuori perimetro (`TransactionFormModal.test.ts` ×2, `ToolExecutionMetrics.svelte` ×1), 41 avvisi come prima, 0 avvisi del planner.
  > - Build: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front build --debug` → rc=0 (`build9.log`), `start.CbSeCkiu.js`, `app.-gH496nM.js`. La sincronizzazione dei tipi API della build non cambia file tracciati.
  > - 6161, senza riavvio (serve `frontend/build` dal disco; il backend non cambia in questo giro): PID 16131 in ascolto, `/api/v1/system/health` 200, `/api/v1/tools/catalog` senza auth 401, `/tools/pac_allocator` 200 con `start.CbSeCkiu.js`. Nei chunk ci sono i testid nuovi (`pac-planner-exposures-maps`, `-result-toggle-all`, `-exposures-scale`, `-ledger-row`, `-proof-tie-break`). 6151 libera.
  > - Stato: HEAD `f6d7a955d`, 72 percorsi modificati, stage vuoto, `git diff --check` pulito. Resta il feedback del developer sul Round 9, chiesto dopo questa nota.
  > **⚠️ Fuori pista**:
  > - `dev.py i18n audit` segna morte 86 chiavi del planner, ma 8 sono **falsi positivi**: `brokers.{feeMax,feeMin,feeZero,fundingChipHelp,stepUnits}` e `units.shares`, scritte per intero in `modeText.ts` dentro `tr(…)` (una funzione passata come parametro, che l'audit non riconosce); `strategy.{l2Help,priorityHelp}`, chiavi relative nei campi `key:` di `StrategyStep.svelte:38/43`. Tutte e 8 sono vive: da non togliere a fine round. Al contrario, `restore` e `restoreCopied` stanno fra le «non verificate» dell'audit (famiglia larga `${PLANNER_KEY}.${…}`), ma sono davvero senza uso. Lo strumento è condiviso e fuori perimetro: lo segnalo al coordinatore nel handoff, senza toccarlo.
  > - Il primo giro di `unused_r99.py` dava 80: la corrispondenza relativa tra apici considerava usate anche le chiavi di un solo segmento (`'add'` compare ovunque come letterale). Ora vale solo per i percorsi con almeno un punto: 81, più le 5 a mano.
  > - 01/10 verso le 11:13: il developer ha riavviato l'app per un aggiornamento, e la 6161 si è fermata con lei, perché la shell era collegata alla sessione. L'`ask_user` del Round 9 si è interrotto. Ho riavviato il server con lo stesso comando di F6, questa volta **staccato** (`detach`), così sopravvive a un altro riavvio dell'app:
  >   - comando: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py server --test --host 127.0.0.1 --port 6161 --data-dir /tmp/librefolio-r2-d-prodcopy --no-scheduler --no-reload`;
  >   - shellId `srv6161r9`, log `/tmp/libreFolio_d_f6/server_review_r9.log`;
  >   - PID 58751 (`dev.py server`), 58844 (uvicorn in ascolto).
  >   Verifiche: health 200 dopo ~4 s, `/api/v1/tools/catalog` senza auth 401, scheduler spento, la pagina serve `start.CbSeCkiu.js`/`app.-gH496nM.js` (il build di R9.9), 6151 libera. HEAD `f6d7a955d`, 72 percorsi, stage vuoto: nulla perso. Il server di F sulla 6164 non l'ho toccato. Poiché è staccato, al handoff va fermato in modo esplicito: `stop_bash srv6161r9`, poi `lsof`. Se resta in ascolto, SIGTERM a 58844, dopo aver verificato che il padre sia il mio `dev.py server`.

#### Round 10 — Obiettivi bilanciabili, Strategia in due righe, L2 con formula, colonne dell'Allocazione, KPI e riquadro del calcolo, colonne ridimensionabili, «≈» delle percentuali, Composizione nel Rivedi, salto alla Prova, barra dei tempi ⏳ 2026-10-01

> Nota sugli ID: i finding `R1`…`R10` della tabella di `:2243-2252` non sono i passi di questo giro, che si chiamano `R10.x`.

**Feedback del developer** (risposta all'`ask_user` del Round 9, 01/10), in sostanza:
1. Broker: il riepilogo dice «Conversione di valuta — Converti prima di comprare, al tasso del passo FX meno lo spread», ma l'editor non permette di cambiarla. In R5 aveva chiesto un selettore: il Broker converte da solo all'acquisto, o serve già la liquidità in quella valuta?
2. Asset: il prezzo auto/manuale è «Ottimo».
3. Obiettivi: bene il riuso del `DistributionEditor`, ma mancano i pulsanti globali, soprattutto «bilancia», che rinormalizza tutte le righe o quelle selezionate.
4. Strategia: la descrizione su due righe, «Compra in modo che il denaro investito si divida fra gli Asset il più vicino possibile ai tuoi obiettivi.» / «Solo acquisti: non vende nulla.»
5. Tooltip L2: chiaro ma prolisso. Più corto, con una o due formule LaTeX al posto delle operazioni descritte a parole.
6. Rivedi, «Dati del calcolo»: le righe «Composizione · N esposizioni» non sono chiare; chiede una spiegazione.
7. Risultato, «Allocazione per Asset»: «Dopo» non è chiaro, serve un nome che dica come cambia il rapporto fra gli Asset. Anche «Valore obiettivo», «Valore dopo», «Residuo» e «Acquisto (mid)» vanno resi chiari, con tooltip visibili.
8. Prima sezione del Risultato (KPI): più badge, voci più separate, e un piccolo riquadro con il tempo di calcolo e le opzioni analizzate dall'ottimizzatore.
9. Tabelle: le colonne non si possono allargare, soprattutto nel Riepilogo.
10. Mappe delle esposizioni: l'elenco fuori mappa mostra sempre «≈» (es. «Taiwan 16,72% → ≈16,72%»). Numeri piccoli (1500 €) o un bug? L'infobox dice sopra/sotto l'obiettivo: in un PAC (non ribilanciamento) come si definisce l'obiettivo? Le mappe mostrano il portafoglio prima e dopo l'acquisto, o la forma teorica del PAC contro quella reale?
11. In cima al Risultato, un pulsante che apre l'ultimo pannello (la Prova, con i tempi del backend) e ci scorre.
12. (In corsa, 01/10) «Tempi del backend»: oltre ai tempi, una barra a colori con un segmento per ogni fase, per vedere a colpo d'occhio come si distribuisce il tempo.

La domanda «riuso dei margini = Piano operativo?» resta accettata (la risposta si apriva con «meglio»): non si richiede.

**Lettura del codice** (01/10):
- **Punto 1** = R4.9 in attesa (`:2573-2586`): è un cambio di contratto (campo della richiesta, modalità e totali nel risultato, fingerprint, `api sync`, test via test-author). Non entra in un giro UI: domanda separata al developer sul momento.
- **Punto 3**: `steps/TargetsStep.svelte` ha solo il «Bilancia al 100%» di riga (`:61-68`) e una `DataTable` senza selezione (`:137-154`). Il `DistributionEditor` (`:251-280`, `:430-450`) ha la selezione e il `DataTableToolbar` con «Bilancia selezionati» (proporzionale ai pesi, in parti uguali se sono tutti 0), ma in virgola mobile con `toFixed(2)`. Nel planner le percentuali sono solo controllo (Q-C0-2, `:180-187`) e restano decimali esatti: serve un helper in `decimal.ts`, che oggi non ha divisioni.
- **Punto 5**: `strategy.l2Help` passa da `shared/HelpTip.svelte`, che non inoltra `math` a `Tooltip` (supportato: `Tooltip.svelte:44`, `:57`, `:332-339`, KaTeX inline `$…$`, `throwOnError: false`). L'`aria-label` di `HelpTip` è «{label}: {help}»: con una formula serve un testo semplice a parte. Vincolo ICU: niente graffe nella stringa (sono segnaposto).
- **Punto 6**: `review.ts:168-180` produce, per ogni Asset con una composizione, una riga «Composizione» con il numero di righe di esposizione (`review.exposureRows`). Le esposizioni compaiono solo in `normalize.py`, `planner_report.py`, `issues.py`, `models.py` e `planner.py`: sono assenti da solver, obiettivi, evaluator e vincoli, quindi **non cambiano il piano** e alimentano solo mappe e barre del Risultato.
- **Punto 7**: colonne in `result/AssetTable.svelte:27-108`. Semantica (`evaluator.py:2053-2105`, `planner_report.build_asset_rows` `:446-470`):
  - valore obiettivo \(T_i = w_i R\), con \(R\) la base degli obiettivi (`evaluator.py:2221`: investito attuale + liquidità raggiungibile);
  - valore dopo \(F_i\) = quantità finale × prezzo ÷ `quote_base_quantity`, al cambio ufficiale;
  - residuo \(F_i - T_i\);
  - acquisto mid = Σ quantità economica × prezzo mid, senza commissioni né margine (`:1880-1907`, `mid_native` `:477`);
  - quota dopo = \(F_i\) ÷ investito dopo.
  In un PAC puro valore dopo = acquisto mid. `assets.target`/`assets.final` servono anche ai tooltip delle esposizioni e alla legenda (`AssetTable.svelte:120-121`): le intestazioni nuove vogliono chiavi nuove.
- **Punto 8**: `result/KpiCards.svelte` mette 5 voci in una griglia senza bordi. Dati disponibili: `ToolItemMetrics` (`backend/app/schemas/tools.py:250-262`) e `solver_evidence` (`backend/app/schemas/pac_allocator.py:979-1080`: stadi con stato, motore, versione e impostazioni, cioè `time_budget` sempre e `limits/nodes` se impostati, `solver.py:288-300`). **Il backend non pubblica il numero di nodi o di candidati esplorati**: `wall_seconds` e `finished_stage_count` sono interni (`solver.py:330-340`). Il riquadro mostra quindi stadi conclusi su totali, motore e versione, tempo concesso e tipo di prova; i nodi richiederebbero un cambio di contratto, da proporre insieme a R4.9.
- **Punto 9**: `DataTable` ha `enableColumnResize` vero di default (`components/table/DataTable.svelte:138`, solo mouse, `:702-733`, larghezze salvate per `storageKey`), ma il planner lo spegne: `AssetTable.svelte:136`, `LedgerTable.svelte:104`, `OperationalPlan.svelte:209`, `ReviewStep.svelte` (2 tabelle), `TargetsStep.svelte`, `ProofPanel.svelte` (`TABLE_PROPS`, `:131-142`).
- **Punto 10**: il «≈» viene da `formatExactPercent` (`format.ts`, `exactDisplay` `:60-63`). Un peso pubblicato come frazione esatta periodica (es. 1/3) si mostra arrotondato e quindi è marcato «≈» (regola di C0, `plan-phase00PacRound5-C0UiDelta.prompt.md:48`). Non è un errore di calcolo né dipende dalla cifra: sulle percentuali a 2 decimali il simbolo non dice niente di utile e confonde. Nella mappa, l'obiettivo di una categoria è Σ quota obiettivo × quota di esposizione dichiarata; il Dopo è Σ quota dopo il piano × esposizione (`planner_report.py:300-385`, `_require_unit_closure`). In un PAC puro «Dopo» è solo ciò che si compra: né il portafoglio intero né lo stato prima.
- **Punto 11**: sezioni e `open` in `result/ResultView.svelte:53-84`; `OutcomeHeader.svelte`; `ResultSection.svelte` (toggle con `aria-expanded`).
- **Punto 12**: `features/tools/components/ToolExecutionMetrics.svelte` è della piattaforma (C) e in questa base la usa solo `ProofPanel.svelte:215`. Le misure (`backend/app/services/tools/executor.py`, `worker.py:131-162`):
  - `queue_wait_ms`: ammissione → assegnazione dello slot;
  - `startup_ms`: assegnazione → worker pronto;
  - `input_validation_ms`, `compute_ms`, `serialization_ms`, `output_validation_ms`: in sequenza nel worker;
  - `execution_ms`: assegnazione → fine, quindi **contiene** l'avvio e le fasi del worker;
  - `cleanup_ms`: dopo l'esecuzione;
  - `total_ms`: ammissione → fine della pulizia.
  Le fasi si sovrappongono solo per annidamento. Una barra corretta usa le fasi foglia nell'ordine reale più un resto «non attribuito» = totale − somma delle foglie (caricamento della definizione, costruzione del plugin, passaggio del risultato). Una fase `null` non è osservata: non diventa 0.

**Decisioni:**
- R4.9 non entra nel Round 10; dopo il feedback, domanda separata sul momento (consigliato: subito dopo questo giro).
- Il bilanciamento è aritmetica decimale esatta in `decimal.ts`, senza `Number`.
- Il «≈» esce dalle percentuali (`formatExactPercent`) e resta su importi e quantità. È un emendamento della regola C0, annotato qui. Se due percentuali mostrate sono uguali ma i valori esatti no, il tooltip lo dice.
- La barra dei tempi è locale al PAC (`planner/result/`), accanto al riquadro «Tempi del backend», senza toccare `ToolExecutionMetrics.svelte` (piattaforma C). Nel handoff propongo al coordinatore di portarla nel componente condiviso, con un solo writer, se la vuole per tutti gli strumenti.

**Passi:**
- R10.0 ✅ 2026-10-01 — questa sezione.
- R10.1 ✅ 2026-10-01 — Obiettivi: selezione multipla, «Bilancia selezionati» e «Bilancia tutto», helper esatto.
  > **Note implementazione**: `decimal.ts` ha `rebalanceControlPercentages(values, selected, of='100')`: righe non selezionate ferme; \(R\) = `of` − somma delle altre; quote \(R \cdot W_i / S\) in unità di \(10^{-P}\), \(P=\max(2,\text{scala degli input})\), con `bigint`: floor e cifre avanzate ai resti più grandi, a pari resto vince l'ordine di riga; tutte a 0 → parti uguali; `null` se un valore non è un numero o è negativo, se la selezione è vuota o se le altre righe superano già `of`. Controllo a mano con uno script usa e getta (esbuild del solo `decimal.ts`, non una suite): `10/20/30` → `16.67/33.33/50`; tre zeri → `33.34/33.33/33.33`; `33.333/0/10` con le ultime due selezionate → `33.333/0/66.667`; `60/50/5` con la sola terza → `null`; somma sempre 100 (`/tmp/libreFolio_d_ui12/r10_rebalance_check.log`). `TargetsStep`: `DataTable` con `enableSelection`, `selectionMode="multi"`, `onSelectionChange` e `bind:this`; in testata `DataTableToolbar` con l'azione «Bilancia le righe selezionate al 100%» (`toolbar-action-balance-selected`, poi `clearSelection()`), il pulsante «Bilancia tutto» (`pac-planner-targets-balance-all`) e «Copia distribuzione attuale». Un campo vuoto vale 0; un testo che non è un numero disattiva i due pulsanti. Il «Bilancia al 100%» di riga resta. `totalHelp` spiega i tre modi.
- R10.2 ✅ 2026-10-01 — Strategia: descrizione in due righe.
  > **Note implementazione**: `policyHelp.proportional` si ferma alla prima frase; la seconda è la chiave nuova `policyScope.proportional` («Solo acquisti: non vende nulla.»), su una riga sua (`pac-planner-policy-scope`), con lo stesso stile.
- R10.3 ✅ 2026-10-01 — L2: tooltip corto con formula.
  > **Note implementazione**: `HelpTip` ha due prop nuove: `math` (passa a `Tooltip` un `html` già escapato con `escapeHtml` di `$lib/utils/inlineMath`, che tiene gli apostrofi per KaTeX, e con gli a capo resi `<br>`, perché il ramo `math` di `Tooltip` usa `{@html}` e perderebbe il `pre-line`) e `spoken`, il testo a parole per l'`aria-label`. In `StrategyStep` il tooltip di L2 mostra la chiave nuova `strategy.l2Formula`: «Distanza dagli obiettivi:», la formula \(D=\sum_i (V_i - p_i R)^2\) su una riga, poi \(V_i\), \(p_i\), \(R\) e «vince il \(D\) più basso; il quadrato pesa di più gli scarti grandi; prezzo di quotazione, senza commissioni né margine». Senza graffe (ICU). `strategy.l2Help` resta il testo per lo screen reader, riscritto per dire la stessa cosa della formula.
  > **⚠️ Fuori pista**: il vecchio `l2Help` parlava di «valore comprato»; la formula usa il valore dell'Asset **dopo** il piano (`evaluator.py:2053-2105`), che in un PAC puro coincide ma col pregresso no. Il testo a parole ora dice «dopo il piano».
- R10.4 ✅ 2026-10-01 — Allocazione: nomi delle colonne e tooltip.
  > **Note implementazione**: intestazioni nuove, ognuna col suo tooltip: «Quota obiettivo» (`targetShare`, nuova), «Quota dopo il piano» (`finalShare`, nuova), «Valore ideale» (`targetValue`), «Valore dopo il piano» (`finalValue`), «Scarto dall’ideale» (`residual`), «Valore comprato» (`buyMid`). I tooltip spiegano la quota scelta nel passo Obiettivi, la quota sul valore di questi Asset dopo il piano, il valore ideale (quota obiettivo × base degli obiettivi), il valore dopo il piano (quote tenute più comprate, prezzo di quotazione, cambio del passo FX), lo scarto (dopo − ideale, segno) e il valore comprato (senza commissioni né margine; l’uscita di cassa è nel Piano operativo). Chiavi nuove: `targetShare`, `finalShare`, `targetShareHelp`, `finalShareHelp`, `targetValueHelp`, `finalValueHelp`; aggiornate: `targetValue`, `finalValue`, `residual`, `residualHint`, `buyMid`, `buyMidHelp`. La legenda delle barre passa a `targetShare`/`finalShare`; `assets.target`/`assets.final` restano, li usa `exposureTooltip.ts:29-30`. Il «Valore comprato» non dice più «a prezzo di quotazione» nel titolo: l’intestazione di `DataTable` non va a capo (`white-space: nowrap`) e allargherebbe la colonna.
  > Il segnale «?» visibile: `DataTable` mostra l’icona dei tooltip d’intestazione solo con `headerTooltipUrl` (`DataTable.svelte:1043-1085`); senza URL il tooltip c’è ma non si vede. Nuovo `planner/shared/columnHelp.ts` con `withHelpCues(columns)`: alle colonne con `headerTooltip`, etichetta non vuota, senza `headerHtml` né URL, aggiunge `headerHtml` = etichetta escapata (`$lib/utils/core/escapeHtml`) + l’SVG di lucide `circle-question-mark` a 12 px, `aria-hidden`, grigio. `DataTable.svelte` non si tocca (componente condiviso). Applicato a tutte le tabelle del planner con tooltip d’intestazione, per coerenza: `AssetTable`, `LedgerTable`, `OperationalPlan`, `ProofPanel` (stadi), `TargetsStep`, `DistributionDialog`. `ReviewStep` non ha tooltip d’intestazione.
- R10.5 ✅ 2026-10-01 — Colonne ridimensionabili.
  > **Note implementazione**: `enableColumnResize` acceso in `AssetTable`, `LedgerTable`, `OperationalPlan`, `ReviewStep` (sezioni e dati del calcolo), `TargetsStep` e `ProofPanel` (`TABLE_PROPS`, vale per obiettivi e stadi). `DistributionDialog` non lo spegneva: lo era già. Le larghezze si salvano per `storageKey`, come nel resto dell’app. Il trascinamento è solo col mouse (`DataTable.svelte:702-733`): su mobile non c’è.
  > **⚠️ Fuori pista**: con `tableLayout="auto"` il trascinamento parte da `column.width` o 150 px (`DataTable.svelte:708`), non dalla larghezza disegnata: se la colonna è più larga per il suo contenuto, i primi pixel del trascinamento non si vedono. È lo stesso comportamento delle altre tabelle `auto` con resize (`MeasurePanel`, `ImportWizardModal`, `FilesTable`); correggerlo vuol dire toccare `DataTable`, componente condiviso: lo segnalo nel handoff, non lo cambio qui.
- R10.6 ✅ 2026-10-01 — KPI a riquadri con badge; riquadro «Calcolo».
  > **Note implementazione**: `result/KpiCards.svelte` riscritto. Con un piano: titolo «Cifre chiave» (`h3`) col suo «?» (`kpi.source`), poi due colonne da `lg` (riquadri | «Calcolo», 16rem), una sola sotto. Sei riquadri con bordo (`pac-planner-kpi-item`, `data-kpi`), ognuno col valore grande e, sotto, le sue parti come badge (`pac-planner-kpi-chip`, `data-chip`, `data-tone`); una parte esattamente 0 non compare, una illeggibile sì (`exactSign` → `null`):
  > - «Base degli obiettivi»: «Già investito» + «Liquidità raggiungibile», solo se c’è un investito attuale (in un PAC puro la base è tutta liquidità e i badge ripeterebbero il valore);
  > - «Investito dopo»: «in N Asset su M» (righe con valore dopo ≠ 0 su righe totali; è un conteggio, non un calcolo economico);
  > - «Non investito»: liquidità libera, costi (`economic_losses`), imposte accantonate (`physical_reserves`), arrotondamento; se è 0, badge verde «Tutto investito»;
  > - «Liquidità scelta» (nuovo, prima era una frase sotto la griglia): badge verde «Tutta raggiungibile», oppure raggiungibile + «Non raggiungibile» in giallo; `data-trapped` resta sul riquadro;
  > - «Costi»: le voci non nulle di `solution.costs` con le etichette già usate dal Saldo e dal dettaglio ordine; se sono tutte 0, badge verde «Nessun costo»;
  > - «Ordini»: «su N Broker» e, se ci sono, «N cambi valuta». Niente badge acquisti/vendite: il contratto PAC 2.0.0 ha solo righe d’acquisto.
  > Le due frasi sotto la griglia (`kpi-shortfall-parts`, `kpi-funding`) escono: il loro contenuto è nei badge. Riquadro «Calcolo» (`pac-planner-kpi-compute`, sfondo grigio), con «?» per riga: tempo di calcolo (`compute_ms`, in ms sotto il secondo, in s sopra, `Intl` con unità, «—» se non misurato) e il totale; tempo concesso (impostazione `time_budget` dello stadio, sempre presente); obiettivi chiusi «N su M» (stadi `finished` su stadi totali; nascosto se il problema è impossibile, perché lì lo stadio è uno solo e dice altro); limite di nodi solo se impostato; motore e versione. Nessun badge della prova: è già nell’intestazione (`OutcomeHeader`). Senza piano (impossibile, nessun piano entro i limiti) il componente mostra solo il riquadro «Calcolo»: `ResultView` lo rende per ogni risultato pronto, non più solo con una soluzione.
  > **⚠️ Fuori pista**: il developer chiedeva anche «le opzioni analizzate dall’ottimizzatore». Il backend non pubblica nodi né candidati esplorati (`solver.py:330-340`, interni): il riquadro dice obiettivi chiusi, tempo e limiti. Pubblicarli è un cambio di contratto, da proporre con R4.9.
- R10.7 ✅ 2026-10-01 — Pulsante per la Prova in cima al Risultato.
  > **Note implementazione**: `OutcomeHeader` ha la prop `ongotoproof` e, a destra del titolo, un pulsante-link «Prova e tempi» con la freccia in giù (`pac-planner-goto-proof`, chiave nuova `result.gotoProof`). `ResultView.gotoProof()`: apre la sezione `proof` nel `SvelteSet`, aspetta il `tick()`, la porta in vista (`scrollIntoView`, `smooth`, `auto` con «riduci movimento») e sposta il focus sul suo interruttore senza un secondo scorrimento (`preventScroll`), così anche la tastiera arriva lì. La sezione si cerca dentro il contenitore del Risultato (`bind:this`), non in tutto il documento. `ResultSection` ha `scroll-mt-20`: l’intestazione dell’app è `sticky` (`Header.svelte:213`) e coprirebbe il titolo della sezione. Un solo pulsante, nell’intestazione: il riquadro «Calcolo» non ne ha un secondo.
- R10.8 ✅ 2026-10-01 — «≈» delle percentuali (a) e Composizione nel Rivedi (b).
  > **Note implementazione (a)**: `format.ts` `formatExactPercent(value, digits)` passa a `formatPlannerPercent` il testo esatto senza `approx`: nessun «≈» sui pesi, ovunque li si mostri (barre, mappe, elenco fuori mappa, tooltip, Allocazione). Importi, quantità e cambi lo tengono. **Emendamento della regola C0** (`plan-phase00PacRound5-C0UiDelta.prompt.md:48`): il «≈» resta il segno di un importo, di una quantità o di un cambio esatto mostrato arrotondato; sulle percentuali a 2 decimali non lo è più, perché un peso esatto periodico (1/3) lo portava quasi sempre e diceva solo che 2 decimali sono un arrotondamento. Il caso che il simbolo copriva davvero, due pesi uguali a 2 decimali ma diversi nei valori esatti, ora lo dice il tooltip dell'esposizione: `exposureTooltip.ts` aggiunge a «Sopra/Sotto l'obiettivo» la coda «di meno di 0,01 punti» (chiave nuova `result.exposures.hairline`) quando il confronto esatto (`compareExact`) non è 0 ma i due testi mostrati coincidono. Il confronto resta esatto, il testo è solo un confronto fra due stringhe già formattate.
  > «Dopo» → «Dopo il piano»: `assets.final` è ormai solo l'etichetta delle esposizioni (lato della mappa `ExposureMaps:259`, legenda e serie delle barre, riga del tooltip, elenco per lo screen reader); il valore si aggiorna (chiave invariata) per allinearsi a «Quota dopo il piano» e «Valore dopo il piano» di R10.4. La sezione «Esposizioni» del Risultato ha un «?» accanto al titolo (prop nuova `help` di `ResultSection`, fuori dal pulsante che apre e chiude; chiave nuova `result.exposures.help`), che risponde alla domanda del punto 10: ogni grafico confronta due forme degli stessi Asset (l'obiettivo distribuito sulle esposizioni dichiarate, e le quote dopo il piano distribuite allo stesso modo), non il portafoglio prima del piano; in un PAC puro «Dopo il piano» è solo ciò che si compra, con Asset già posseduti li comprende; le esposizioni alimentano solo questi grafici.
  > **Note implementazione (b)**: `review.ts`: il valore del fatto «Composizione» passa da `{kind:'rows', count}` a `{kind:'exposures', dimensions}`, il conteggio delle righe per dimensione nell'ordine fisso `EXPOSURE_DIMENSIONS`, senza le dimensioni vuote (un conteggio, non un calcolo economico). `ReviewCell` lo mostra come «Area geografica: 12 voci · Settore: 11 voci · Tipo di Asset: 1 voce» (chiave nuova `review.exposureDimension`, con i nomi delle dimensioni già tradotti `dimensions.*`); tipo nuovo di cella `kind`, etichetta più «?» opzionale. Nel Rivedi la colonna «Tipo» usa quella cella: per la composizione l'etichetta diventa «Composizione per le mappe» (`review.kind.exposures` aggiornata) e il «?» (chiave nuova `review.exposuresHelp`) spiega che viene dalla pagina Asset o è scritta a mano, e che serve solo a mappe e barre delle esposizioni: non entra nel calcolo e non cambia il piano. Il filtro della colonna resta per `fact.kind`. La tabella non ha clic di riga, quindi il «?» non apre la modifica. `review.exposureRows` non ha più usi: va nella lista di fine round (decisione (a)).
- R10.9 ✅ 2026-10-01 — Barra dei tempi del backend.
  > **Note implementazione**: nuovo `result/BackendTimingBar.svelte`, in `ProofPanel` sotto il riquadro condiviso «Tempi del backend» (stesso blocco, `space-y-3`); `ToolExecutionMetrics.svelte` non si tocca. Riquadro con lo stesso bordo, titolo `h4` «Come si distribuisce il tempo» (icona `ChartBarStacked`), una riga di spiegazione col totale dell'elemento, poi la barra (`aria-hidden`, alta 16 px, arrotondata) e la legenda in lista (colore, nome, ms, quota). Segmenti: le fasi foglia nell'ordine in cui avvengono (attesa in coda, avvio del worker, validazione degli input, calcolo, serializzazione dell'output, validazione dell'output, pulizia), con le etichette già tradotte `tools.metrics.*`; `execution_ms` non è un segmento perché contiene l'avvio e le fasi del worker. In coda «Non attribuito» = max(0, totale − somma delle foglie), con un «?» che dice cosa contiene (caricamento e preparazione dello strumento, consegna del risultato). Scala = max(totale, somma delle foglie), perché millisecondi interi misurati a parte possono superare il totale di poco. Una fase `null` (non osservata) o a 0 ms non compare: mai uno 0 inventato. Senza un totale > 0 il componente non si mostra. Ogni segmento ha almeno 3 px, per non sparire. Colori Tailwind con la variante scura. Sono durate, non importi: nessuna maschera della privacy. Chiavi nuove `result.timing.title`, `hint`, `unattributed`, `unattributedHelp`. Testid: `pac-planner-timing`, `-timing-bar`, `-timing-segment` (`data-phase`), `-timing-legend`, `-timing-item` (`data-phase`), `-timing-help`.
- R10.10 ✅ 2026-10-01 — i18n, svelte-check, build. Nessun test automatico, su richiesta del developer.
  > **Note implementazione**: batch `/tmp/libreFolio_d_ui12/i18n_round10.py`, solo `dev.py i18n add|update`: 43 chiavi nuove e 11 aggiornate, 4 lingue ciascuna, nessuna rimozione (decisione (a)). Prima di scrivere, lo script confronta il valore inglese di ogni chiave con il default del sorgente (chiavi `${KEY}.…`, chiavi letterali, `text()`/`tile()` di `KpiCards`, fallback di `StrategyStep`, `KIND_FALLBACKS` del Rivedi): 54 su 54 uguali (`r10_guard_probe.log`). Esito: 54 su 54 rc=0 (`i18n_round10.log`); 4336 chiavi per catalogo (4293 + 43); sha8 en `5be9096d`, it `7ac1707e`, fr `df9c478c`, es `1ebcd709`. ICU (`icu_check_r10.mjs` sulle 54 chiavi, 4 lingue): 0 problemi. `strategy.l2Formula` conserva i due a capo e il `\sum` in tutte e 4 le lingue. `r10_keys_probe.py`: 54 presenti. `r10_scan_diff.py`: restano solo le 3 differenze di `review.*` (`routes`, `targets`, `fxRated`), anteriori al Round 10, dove il catalogo ha la forma plurale migliore del default: non toccate.
  > `targets.totalHelp`: il default inglese ora cita «Balance the selected rows to 100%», l'etichetta esatta dell'azione della barra (prima «Balance the selected rows»); le traduzioni citano le etichette tradotte.
  > Chiavi rimaste senza uso, tutte ancora nel catalogo (lista di fine round, decisione (a)): `result.kpi.funding`, `result.kpi.fundingReachable`, `result.kpi.shortfallParts`, `result.kpi.shortfallPartsNoRounding` (R10.6), `review.exposureRows` (R10.8); da prima `result.proof.floatingFinished`, `result.states.noIncumbent.rejected`.
  > svelte-check: 3 errori e 41 warning in 4 file, la baseline; nessuno nel planner (`r10_svelte_check2.log`). Build: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front build --debug` → rc=0 (14:06:34 → 14:08:11, `build10.log`), `start.DSziYD8x.js`, `app.DZ6MhyI-.js`; la 6161 (pid 58844) li serve senza riavvio, perché il backend non cambia. `git diff --check` rc=0.
- R10.11 ✅ 2026-10-01 — feedback (`ask_user`) con le spiegazioni.
  > **Note implementazione**: il developer ha risposto con 11 punti, che diventano il Round 11. Sul punto 1 conferma che vuole R4.9 adesso: «Broker: Manca ancora il modo di specificare come il broker gestisce le conversioni».

#### Round 11 — R4.9 (conversione per Broker), titolo della Route, L2 con min ed elenco, Rivedi senza Composizione, badge nell'intestazione, ordine dei valori, marquee, esposizioni «ideale vs reale», colonne spostabili e nascondibili, barra dei tempi interattiva, Prova a card ⏳ 2026-10-01

**Feedback del developer** (risposta all'`ask_user` del Round 10, 01/10), in sostanza:
1. Broker: manca ancora il modo di dire come il Broker gestisce le conversioni. Il riepilogo dice solo «Conversione di valuta — Converti prima di comprare, al tasso del passo FX meno lo spread». È R4.9, e lo vuole adesso.
2. Route: il titolo su una riga, «Route - Cosa può comprare ogni Broker».
3. Tooltip L2: nella prima formula serve il **min**; i parametri in un elenco puntato, uno per riga. Il resto è «ottimo». La formula doppia del testo incollato è il MathML più l'HTML di KaTeX copiati insieme, non un difetto.
4. Rivedi: togliere del tutto le righe «Composizione per le mappe». La riga del prezzo invece conta.
5. Intestazione del Risultato: la riga «Distanza L2 … · Non investito … · nessuna nota» va resa con badge e tooltip.
6. «Allocazione per Asset»: «Valore comprato» e «Valore dopo il piano» possono essere diversi? Il ribilanciamento non lo vede ancora come strumento. Ordine dei valori: Valore dopo il piano → Valore ideale → Scarto.
7. Nomi degli Asset che non entrano nelle tabelle: marquee, come altrove nel progetto.
8. Esposizioni: spiegazione da sviluppatore, va resa concisa; «ideale vs reale» nel titolo; tooltip molto più semplice; legende «Distribuzione ideale» e «Distribuzione reale». Nota sua: «quando facciamo il pac invece prima vs dopo».
9. Tabelle: un pulsante per spostare e nascondere le colonne, nella tabella di ogni sezione.
10. Barra dei tempi: passando su un segmento si evidenzia la sua voce di legenda, e viceversa.
11. Prima parte della Prova (Esito, Prova, Arresto): da migliorare. «Valori esatti degli obiettivi» diventa a card: una tabella qui è dispersiva.

**Lettura del codice** (01/10):
- **Punto 1** = R4.9 (`:2573-2586`), con la sua riga di testa: «Decisione del developer (30/09): riaprire la regola 10 come passo a sé subito dopo questo giro UI, con i test». Contratto attuale: `PlannerFxAction` (`backend/app/schemas/pac_allocator.py:1200-1229`), una per rotta d'ordine × valuta di origine; `PlannerBuyOrderRow` `:1280-1322`; `fx_actions` `:1617`, `:1647`; UI `result/OperationalPlan.svelte:31-75`. La regola 10 del 17/09 aveva ritirato `conversion_mode` e `PlannerFxAction.handling` (`plan-phase00Step1PacRebalancerContractsCapacity.prompt.md:911-918`; `w1-fx-redesign-final-delta-plan.md:70,74`).
- **Punto 2**: il titolo del passo è l'`h2` di `PacPlannerTool.svelte:349-350`; `steps/RoutingStep.svelte:82-91` aggiunge un `h3` (`routing.intro`) col suo «?» (`routing.introHelp`, `pac-planner-routing-help`).
- **Punto 3**: i fallback del tooltip sono in `steps/StrategyStep.svelte:49-62` (`OBJECTIVE_TIPS.fixed_l2`); `shared/HelpTip.svelte` passa `math` a `Tooltip` e trasforma gli a capo in `<br>`. Niente graffe nel testo (ICU): `\min` senza pedice.
- **Punto 4**: `review.ts:169-185` aggiunge un fatto `exposures` per Asset; `steps/ReviewStep.svelte:38-39` (`KIND_ORDER`, `KIND_FALLBACKS`) e `:176-187` (il «?» del tipo); `shared/ReviewCell.svelte:101-110`. `withExposures` (`review.ts:14`) resta: lo usa `shell/SummaryPanel.svelte:58`.
- **Punto 5**: `result/OutcomeHeader.svelte:54-61`, un `<p>` con le parti unite da « · ».
- **Punto 6**: `final_value = current_value + buy_mid_value − sell_mid_value` (`backend/app/services/pac_allocator/models.py:1205`, `evaluator.py:2685`). Il PAC esige un investito attuale nullo (`schemas/pac_allocator.py:2085-2086`): `PacPlannerRequest` (`:645-650`) non ha posizioni, le ha solo `_RebalancerPlannerRequestBase.holdings` (`:654`). Quindi in un PAC comprato = dopo, sempre; si separano solo nel ribilanciatore (§4). Colonne in `result/AssetTable.svelte:28-128`.
- **Punto 7**: lo schema è `use:scrollOnOverflow` + `overflowScrollTextClass` (`$lib/actions/scrollOnOverflow`, `$lib/utils/overflowScroll`), già in `AssetsStep.svelte:201` e `RoutingStep.svelte:107,152`. Nelle tabelle il nome passa da `shared/AssetNameCell.svelte` (`truncate`; lo usano `ResultCell`, `ReviewCell`, `TargetsStep`, `DistributionDialog`) e da `result/ResultCell.svelte` (`NAME`, Broker e versamenti).
- **Punto 8**: titolo e «?» in `result/ResultView.svelte:139-149`; etichette del tooltip in `result/exposureTooltip.ts:31-35` (`assets.target`/`assets.final`, usate solo lì e nelle mappe/barre); `result/ExposureMaps.svelte:253-279` (scala, `scaleHelp`); `result/ExposureSection.svelte:40-93`.
- **Punto 9**: `components/table/ColumnVisibilityToggle.svelte` (condiviso, si usa e basta): legge `getColumnsForVisibility()` e chiama `toggleColumnVisibilityById`/`setColumnOrder`/`resetColumnLayout` di `DataTable.svelte:883-908`; esclude le colonne senza intestazione né `displayName`. Visibilità (solo le scelte esplicite) e ordine si salvano per utente e `storageKey` (`DataTable.svelte:193-199`, `:744-751`); `hiddenByDefault` è `components/table/types.ts:289`. `enableColumnVisibility` è solo dichiarato (`DataTable.svelte:54`, `:140`). Il planner lo spegne in `AssetTable.svelte:154`, `LedgerTable.svelte:103`, `OperationalPlan.svelte:208`, `ProofPanel.svelte:140` (`TABLE_PROPS`), `ReviewStep.svelte:239`, `:282`, `TargetsStep.svelte:202`, `DistributionDialog.svelte:224`. Il pulsante ha un `data-testid` fisso (`column-visibility-toggle`): nel planner lo avvolge un contenitore col suo.
- **Punto 10**: `result/BackendTimingBar.svelte`, segmenti `:96-100`, legenda `:101-111`.
- **Punto 11**: `result/ProofPanel.svelte`: `<dl>` `:149-198` (esito, prova, arresto), obiettivi `:200-209` (`DataTable`, `pac-planner-result-objectives`, con la nota sul pareggio), stadi `:211-219`.

**Decisioni:**
- R4.9 entra in questo giro come passo a sé, dopo i punti UI, **con i test** (decisione del developer del 30/09, che qui prevale sul «niente test» dei giri UI). Disegno approvato il 30/09 (`:2573-2586`): calcolo invariato; il backend fa i totali; contratto, fingerprint e `api sync` (lista del coordinatore); test di contratto via test-author, corsia 6151.
- «Valore comprato» resta, nascosto di default (`hiddenByDefault`): si riaccende dall'occhio. In un PAC è uguale al valore dopo il piano; nel ribilanciatore (§4) no.
- Esposizioni: «ideale vs reale» adesso; «prima vs dopo» arriva col ribilanciatore (§4), perché in un PAC puro «prima» è vuoto.
- Colonne: il `ColumnVisibilityToggle` condiviso sopra ogni tabella del planner, a destra; niente componenti condivisi modificati.
- Le chiavi che restano senza uso vanno nella lista di fine round (decisione (a)).

**Passi:**
- R11.0 ✅ 2026-10-01 — questa sezione.
- R11.1 ✅ 2026-10-01 — Route: titolo su una riga, «?» accanto.
  > **Note implementazione**: `PacPlannerTool.svelte`: il titolo del passo sta in una riga flessibile; sul passo `routing` l'`h2` aggiunge « – Cosa può comprare ogni Broker» (`routing.intro`, `pac-planner-routing-intro`) e accanto, fuori dall'`h2`, il «?» con `routing.introHelp` (`pac-planner-routing-help`, testid invariato). `RoutingStep.svelte` perde l'`h3` e il suo «?», e l'import `SECTION_TITLE` rimasto senza uso. Il trattino è punteggiatura, non testo da tradurre: le due parti restano le chiavi già tradotte. Nessuna chiave nuova; nessun test cita il testid.
- R11.2 ✅ 2026-10-01 — L2: `\min` ed elenco puntato.
  > **Note implementazione**: `strategy.l2Formula` (fallback in `StrategyStep.svelte:51`): la formula diventa `$D = \min \sum_i (V_i - p_i R)^2$` e i parametri tre righe «• $V_i$: …», «• $p_i$: …», «• $R$: …»; la frase finale dice «vince il piano con la somma più bassa», perché $D$ ora è il minimo. `shared/HelpTip.svelte`: con `math`, `mathHtml()` trasforma una serie di righe che iniziano con «• » in un solo `<ul class="my-1 list-disc space-y-0.5 pl-4">`; le altre righe restano unite da `<br>`. L'escape avviene prima, come prima: il markup aggiunto è solo `ul`/`li`. `strategy.l2Help` (la versione a parole per lo screen reader) non cambia: dice già «vince il piano con la somma più bassa». Valori delle 4 lingue nel batch di R11.13.
- R11.3 ✅ 2026-10-01 — Rivedi senza «Composizione per le mappe».
  > **Note implementazione**: `review.ts` non produce più il fatto `exposures` (blocco per Asset tolto, variante `FactValue` e voce di `FactKind` tolte; import `EXPOSURE_DIMENSIONS`/`sameExposures`/`ExposureDimension` rimasti senza uso tolti). Resta `assets.withExposures` di `sectionCounts`, letto dal pannello Riepilogo (`SummaryPanel.svelte:58`). `ReviewStep.svelte`: `KIND_ORDER`/`KIND_FALLBACKS` senza `exposures`; la cella del tipo è solo `{type:'kind', label}`. `ReviewCell.svelte`: tolti il ramo che contava le righe per dimensione, il «?» del tipo (`pac-planner-review-kind-help`, serviva solo alla composizione) e gli import/costanti rimasti senza uso (`HelpTip`, `DIMENSION_FALLBACKS`, `PLANNER_KEY`). La composizione resta nel passo Asset e nella richiesta (`request.ts:80`), quindi la mappa del risultato non cambia. Nessun test citava i testid tolti. Chiavi rimaste senza uso, per la lista della decisione (a): `review.kind.exposures`, `review.exposureDimension`, `review.exposuresHelp`.
- R11.4 ✅ 2026-10-01 — Badge e tooltip nell'intestazione del Risultato.
  > **Note implementazione**: `result/model.ts`: ogni `ResultBadge` porta `help` (`BadgeHelp`, chiave letterale + fallback). Riusate le frasi già tradotte che dicono la stessa cosa: «Nessuna operazione» → `result.states.noOp.empty`; «Infattibile» → `result.states.infeasible.body`; «Nessun piano entro i limiti» → `result.states.noIncumbent.body`; «Infattibilità dimostrata» → `result.proof.solverInfeasibleWitness`; «Ottimalità non dimostrata» → `result.proof.floatingUnfinished`, ma con esito `no_incumbent` la stessa `noIncumbent.body`, perché «il miglior piano trovato» lì sarebbe falso. Chiavi nuove (`result.badges.help.*`): `planAvailable`, `decimalVerified`, `optimalProven`, e per l'arresto `completed`, `timeLimit`, `nodeLimit` (mappa `STOP_HELP`); `completed` dice solo che il solver ha chiuso la ricerca da sé, senza promettere l'ottimo, che resta compito del badge di prova.
  > `result/OutcomeHeader.svelte`: ogni badge è un `Tooltip` (hover, tap, focus) attorno allo `span` colorato; `li` con `data-badge`/`data-tone` invariati. La riga «Distanza L2 · Non investito · note» diventa badge (`pac-planner-outcome-objective`, `data-objective`): L2 con la formula di Strategia (`strategy.l2Formula`, stessa chiave e stesso fallback, ora `L2_FORMULA_FALLBACK` in `policies.ts`, usato anche da `StrategyStep`); Non investito con `result.kpi.help.shortfall`; note (`pac-planner-outcome-notes`) arancione se c'è un avviso, blu se ci sono solo informazioni, neutro se zero, con la chiave nuova `result.header.notesHelp`. Un risultato pronto non porta errori: il tono non li prevede.
  > `shared/tipHtml.ts` (nuovo): la trasformazione di R11.2 (escape, poi «• » → `ul`/`li`, il resto `<br>`) esce da `HelpTip.svelte`, che ora la importa; la usa anche il badge L2. Nessun test cita i testid toccati (`grep` su `frontend/`).
  > **⚠️ Fuori pista**: le date «2026-10-02» di R10.6–R11.3 (e «02/10» nel feedback e nella lettura del codice del Round 11) erano sbagliate: il giorno è il 01/10 (`date`; `build10.log` di R10.10 ha mtime 01/10 14:08:11). Corrette nel piano; `plan_note.py` ora scrive 2026-10-01.
- R11.5 ✅ 2026-10-01 — Allocazione: ordine dei valori, «Valore comprato» nascosto.
  > **Note implementazione**: `result/AssetTable.svelte`: ordine Asset, Obiettivo, Quota dopo il piano, barre, **Valore dopo il piano → Valore ideale → Scarto dall’ideale**, poi «Valore comprato» con `hiddenByDefault: true` (lo onora `DataTable.svelte:199` anche senza menu; da R11.8 si riaccende dall’occhio delle colonne). I totali del piede sono per id di colonna, quindi seguono lo spostamento da soli. `result.assets.buyMidHelp` aggiunge «In un PAC, che parte da zero, coincide con il valore dopo il piano» (UPDATE nel batch, 4 lingue). Risposta alla domanda del developer, da riportare nell’`ask_user`: `final_value = current_value + buy_mid_value − sell_mid_value`; il PAC parte da investito nullo e non vende, quindi comprato = dopo; si separano solo nel ribilanciatore (§4). Batch del giro avviato: `/tmp/libreFolio_d_ui13/i18n_round11.py` (R11.2, R11.4, R11.5; `--dry` → ADD=7 UPDATE=2, guard 0).
- R11.6 ✅ 2026-10-01 — Marquee nei nomi delle tabelle.
  > **Note implementazione**: `shared/MarqueeName.svelte` (nuovo): il nome in una cella è `<span use:scrollOnOverflow class="{overflowScrollTextClass} font-medium …" title={text}>`, lo schema di `AssetsStep.svelte:201` e `BrokerCard.svelte:107`. Sostituisce il `truncate` in `shared/AssetNameCell.svelte` (quindi `TargetsStep`, `DistributionDialog`, `ReviewCell` e `ResultCell` per gli Asset), in `result/ResultCell.svelte` (Broker, versamento, etichetta: obiettivi e stadi della Prova) e in `shared/ReviewCell.svelte` (Broker, cassa, versamento); le due costanti `NAME` spariscono. Il nome che entra non cambia (niente animazione né listener); quello che non entra scorre da solo e ha il testo intero nel `title`. Nessuna chiave nuova; nessun componente condiviso toccato.
- R11.7 ✅ 2026-10-01 — Esposizioni «ideale vs reale».
  > **Note implementazione**: titolo «Esposizioni – ideale vs reale» (`result.sections.exposures`, fallback in `result/ResultView.svelte`); il «?» passa da cinque frasi a due: come si distribuiscono gli Asset per paese, tipo e settore, la distribuzione ideale segue le quote obiettivo e quella reale le quote dopo il piano, i grafici non cambiano il piano. Le due serie si chiamano «Distribuzione ideale» e «Distribuzione reale» (chiavi nuove `result.exposures.ideal`/`actual`, in `result/exposureTooltip.ts`): da lì le prendono le didascalie delle mappe, la legenda delle barre, le righe del tooltip e l’elenco accessibile. La direzione nel tooltip dice «Sopra/Sotto l’ideale», «In linea con l’ideale», come le colonne «Valore ideale» e «Scarto dall’ideale» dell’Allocazione. `scaleHelp` più corto. Batch: ADD 2, UPDATE 6 (titolo, help, scaleHelp, above/below/equal); la guardia ora legge anche i fallback di `title('<id>', …)` in `ResultView`. `--dry` → ADD=9 UPDATE=8, guardia 0. Senza uso da qui (decisione (a), lista di fine round): `result.assets.target`, `result.assets.final`. «Prima vs dopo» resta per il ribilanciatore (§4), come deciso.
- R11.8 ✅ 2026-10-01 — Colonne spostabili e nascondibili.
  > **Note implementazione**: nuovo `shared/TableColumns.svelte`, un contenitore `ml-auto` col suo `data-testid` attorno al `ColumnVisibilityToggle` condiviso (usato così com'è, con `showLabel`: l'occhio più «Colonne», così il pulsante ha anche un nome accessibile, che senza etichetta non avrebbe). Messo a destra sopra ogni tabella: Allocazione per Asset (sulla riga della legenda, `pac-planner-assets-columns`), Saldi (`pac-planner-ledger-columns`), ordini per Broker (nella riga del titolo di ogni Broker, `pac-planner-plan-orders-columns`: le tabelle condividono la `storageKey`, quindi ogni pulsante le cambia tutte insieme via `additionalTableRefs`), fasi del solver (`pac-planner-solver-stages-columns`), Rivedi (sezioni sulla riga d'apertura, dati del calcolo sopra la loro tabella), Obiettivi (in fondo alla riga dei pulsanti) e «Copia la distribuzione attuale» (`{testid}-columns`). Ogni `DataTable` ha `bind:this`; `enableColumnVisibility={false}` (solo dichiarato, mai letto da `DataTable`) passa a vero dove c'è il pulsante. Gli obiettivi della Prova non lo hanno: diventano card in R11.10.
  > **⚠️ Fuori pista**: Saldi. Prima le colonne «mute» uscivano dall'elenco `columns`, e `DataTable` scarta le scelte salvate delle colonne che spariscono: una colonna nascosta a mano sarebbe ricomparsa al piano dopo. Ora `columns` le contiene tutte e le mute hanno `hiddenByDefault: !showAll && !speaking.has(field)`. «Mostra altre colonne» cambia solo il default; una scelta fatta col pulsante vince, e «Reset layout» torna al default. Il conteggio del link resta quello delle colonne mute.
- R11.9 ✅ 2026-10-01 — Barra dei tempi interattiva.
  > **Note implementazione**: `result/BackendTimingBar.svelte`. Un solo stato `pointed` (la fase sotto il puntatore), e `active` lo tiene solo se la fase è ancora disegnata, così un nuovo risultato che la toglie non lascia un'evidenza appesa. Segmento e voce di legenda hanno `onpointerenter`/`onpointerleave` sullo stesso stato: quello attivo resta pieno, gli altri si attenuano (segmenti `opacity-30`, voci `opacity-50`), e la voce attiva prende uno sfondo grigio (`bg-gray-100`/`dark:bg-gray-700`), con una transizione breve. Eventi pointer, quindi un tocco su touch screen fa lo stesso. La voce reagisce anche al focus al suo interno (`onfocusin`/`onfocusout`: il «?» di «Non attribuito»), così da tastiera il legame resta. `data-active` su segmento e voce per i test futuri. La barra resta `aria-hidden`: la legenda dice già tutto a parole. Nessuna chiave nuova.
- R11.10 ✅ 2026-10-01 — Prova: esito a badge, obiettivi a card.
  > **Note implementazione**: `result/ProofPanel.svelte`. Esito, Prova e Arresto non sono più un `<dl>` di testo ma tre riquadri affiancati (`pac-planner-proof-facts`, una colonna su mobile), ognuno col titolo piccolo e gli stessi badge dell'intestazione, con la loro spiegazione al passaggio, al tocco o al focus. Esito (`pac-planner-proof-outcome`): «Piano disponibile» (o nessuna operazione, impossibile, nessun piano) più «Verificato in Decimal» quando c'è. Prova (`pac-planner-proof-kind`): il badge della prova, e sotto una riga solo quando aggiunge qualcosa: con l'ottimo il numero di obiettivi chiusi (`proof.solverWitness`), senza prova il motivo (`pac-planner-proof-reason`). Arresto (`pac-planner-proof-stop`): il badge dell'arresto. I valori esatti degli obiettivi non sono più una `DataTable` ma card in ordine di cascata (`pac-planner-objective`, `data-objective`), una griglia da 1 a 3 colonne: il numero d'ordine nel cerchio verde della Strategia, il nome con lo stesso «?» della Strategia (la formula L2 col suo testo a voce, la priorità, altrimenti la riga breve `objectiveHelp.*`) e il valore grande (`pac-planner-objective-value`, `formatObjectiveValue`, quindi mascherabile). La nota sullo spareggio finale resta sotto le card; fasi del solver, metriche e barra dei tempi restano come sono.
  > Nuovo `result/ResultBadgeTip.svelte` (il badge con il suo `Tooltip`), usato anche da `OutcomeHeader`, così intestazione e Prova non possono divergere. In `ui.ts` le classi `TILE` e `TILE_LABEL`. Le spiegazioni degli obiettivi (`OBJECTIVE_HELP_FALLBACKS`, `OBJECTIVE_TIPS`, tipo `ObjectiveTip`) passano da `StrategyStep.svelte` a `policies.ts`, con chiavi assolute, così la Strategia e la Prova leggono lo stesso testo; l'audit ora vede `strategy.l2Help` e `strategy.priorityHelp`, prima falsi positivi. In `ResultCell.svelte` esce il tipo di cella `objective`, che aveva come unico uso la vecchia tabella. Nessuna chiave nuova. Guardia del batch i18n aggiornata (le spiegazioni si leggono da `policies.ts`); `--dry`: ADD=9, UPDATE=8, problemi 0.
  > Chiavi rimaste senza uso (verificate con grep sulla chiave intera e sulla forma `${KEY}.*`), da aggiungere alla lista di fine round (decisione (a)): `result.proof.optimal`, `result.proof.notProven`, `result.proof.infeasible`, `result.proof.sources.solver_status`, `result.proof.tieBreakClosed`, `result.proof.decimalVerified`, `result.proof.exactValue`, `result.outcomes.incumbent_found`, `result.outcomes.no_op`, `result.outcomes.infeasible_proven`, `result.outcomes.no_incumbent`.
  > **⚠️ Fuori pista**: con l'infattibilità dimostrata il riquadro Prova mostra solo il badge, senza la riga `solverInfeasibleWitness`: è la spiegazione del badge stesso (R11.4) e l'avviso di stato sopra la dice per intero, quindi sarebbe stata la stessa frase due volte.
- R11.11 ✅ 2026-10-01 — svelte-check.
  > **Note implementazione**: `svelte-kit sync`, poi `svelte-check --tsconfig ./tsconfig.json --output machine` in `frontend/` (log `/tmp/libreFolio_d_ui13/check_r11.log`): 5483 file, **3 errori e 41 avvisi, gli stessi della baseline** (`TransactionFormModal.test.ts` ×2, `ToolExecutionMetrics.svelte` ×1, tutti fuori dal planner). Nessun avviso nel planner: né sui gestori pointer/focus della barra dei tempi (R11.9) né sui riquadri e sulle card della Prova (R11.10).
- R11.12 ⏳ — R4.9: contratto, UI, test, riavvio della 6161.
  > **Analisi (2026-10-01), prima del codice: la conversione non appartiene a un ordine.**
  > - **Cosa decide il motore.** Una conversione è una decisione `fx_debit` per rotta d'acquisto × valuta di origine (`evaluator.py:1738-1821`). Il suo accredito però entra nella cassa del Broker nella valuta dell'Asset, la cella `(broker, valuta)` che tutti gli ordini di quel Broker in quella valuta usano insieme (`constraints.py:503-597`). Nessun vincolo lega la conversione all'acquisto della sua rotta: il catalogo dei vincoli (`models.py:53-87`) non ha una regola FX↔BUY, e `_validate_ready_solution` non controlla che `order_route_id` abbia una riga d'ordine.
  > - **Chi sceglie la rotta.** Nessun obiettivo distingue la rotta: lo spread dipende solo dalla coppia (`objectives.py:167-201`). Decide lo spareggio canonico, che minimizza i quanti in ordine (`objectives.py:224-231`), con la chiave `("", broker, origine, "fx", destinazione, route_id)` (`evaluator.py:3007-3077`). La conversione finisce quindi sull'ultima rotta in ordine di ID fra quelle dello stesso Broker e della stessa valuta, anche su un Asset che il piano non compra.
  > - **Conseguenze.**
  >   1. «Dentro la riga dell'ordine» (disegno del 30/09) non ha un importo per ordine definito dal calcolo.
  >   2. Già oggi la riga «per comprare {asset}» del passo FX (`OperationalPlan.svelte:175`) e le conversioni nel dettaglio d'ordine (`OrderDetail.svelte:29`, filtro su `order_route_id`) possono nominare l'Asset sbagliato, o nessuno.
  >   3. Il rollup di `fx_cost` per rotta del 17/09 (`w1-fx-redesign-final-delta-plan.md:60-74`, mai implementato) metterebbe il costo sulla rotta sbagliata: non lo implemento. Lo spread resta sul totale per Broker × coppia; il frontend non legge `fx_cost`.
  > - **Il totale per Broker × coppia invece è ben definito**: debito, accredito registrato e spread si sommano sulle azioni della coppia, e tasso e spread sono globali per coppia, quindi identici in ogni azione.
  > - Prima di scrivere il contratto, domanda al developer (`ask_user`) su come mostrare la modalità automatica.
  > **Decisione del developer (2026-10-01, `ask_user`, opzione raccomandata).**
  > - **Automatica**: nel gruppo «Ordini su {Broker}» un riquadro con il totale per coppia («il Broker converte circa X EUR → Y USD quando compri»); sugli ordini in quella valuta un badge «conversione automatica», senza importo. Nessun passo numerato.
  > - **Manuale**: resta il passo numerato «prima converti», uno per Broker × coppia, con il totale; la frase diventa «per gli ordini in USD su {Broker}».
  > - Il calcolo non cambia e non nasce nessuna regola nuova: la modalità decide solo come il piano presenta la conversione.
  > **Contratto finale di R4.9.**
  > - Richiesta: `PlannerBrokerInput.conversion_mode: "manual" | "automatic"`, obbligatorio come ogni campo della richiesta. Il normalizzatore lo porta in `ExactBroker.conversion_mode`, quindi l'impronta dello scenario cambia con la modalità: un risultato calcolato con l'altra modalità non passa per fresco.
  > - `PlannerFxAction`: perde `sequence` e guadagna `conversion_id`. `order_route_id` resta, documentato come chiave della decisione del motore, non come «l'acquisto che la paga».
  > - Nuovo `PlannerConversion`, uno per Broker × origine × destinazione: `conversion_id`, `mode`, `sequence` (intero se manuale, `None` se automatica), `broker_id`, `source_debit` (Σ esatta delle azioni), `destination_credit` (Σ degli accrediti registrati), `spot_rate` ed `effective_rate` (identici in tutta la coppia), `spread_loss` (Σ esatta, nella valuta di valutazione), `fx_action_ids`, `provenance_ids` (unione di quelli delle azioni).
  > - Soluzioni PAC e Rebalancer: nuova lista `conversions`; nei no-op `max_length=0`.
  > - Sequenze: un solo contatore, funding 1..F, poi le conversioni manuali ordinate per Broker, origine e destinazione, poi gli ordini. Uniche fra le tre sezioni e crescenti dentro ognuna, come prima.
  > - `fx_cost` della riga d'ordine resta 0 e la descrizione del campo lo dice: lo spread vive sulla conversione. Niente rollup per rotta; debito da riportare al coordinatore.
  > **Note implementazione (backend, 2026-10-01)**: contratto R4.9 scritto.
  > - Schema: `PlannerBrokerInput.conversion_mode` obbligatorio (`manual`/`automatic`, solo presentazione); `PlannerFxAction` perde `sequence` e guadagna `conversion_id`; nuova `PlannerConversion` (Broker × coppia, `sequence` presente solo se manuale, somme esatte, tassi della coppia, `fx_action_ids`, provenance unione); `conversions` nelle due soluzioni (vuota nei no-op); `fx_cost` del BUY ora deve essere 0.
  > - Validatori: `_validate_action_ids_and_sequences` (ID unici su funding/fx/conversioni/ordini, sequenze uniche su funding/conversioni manuali/ordini) e `_validate_conversions` (aggregato puro: coppia, tassi, somme Fraction, provenance, un modo per Broker).
  > - Motore: `ExactBroker.conversion_mode` (normalizer lo passa, `ValueError` su modo ignoto); `build_fx_actions` senza sequenza; nuova `build_conversions` raggruppa per (Broker, src, dst), sequenza solo alle manuali; `_build_solution_parts` chiama funding → fx → conversioni → ordini. Calcolo invariato: tassi e spread sono globali per coppia (`evaluator.py:1765-1772`), quindi l’invariante «stessi tassi nel gruppo» regge.
  > - Verifica: import dei moduli OK; `api sync` exit 0 (contratti tool `ebf753ba…dde77`). Nuovi fingerprint schema: pac `bd84ef14dc43bc6185c8c4e009a336f924a3fee6cdff03a04b1263ab0246cc29`, rebalancer `0b43bd19dc8716ea6cffc4158764594a5f16fb06adcc43185f1bb54cfa91a1e0` (erano `502e8c48…8e374` e `17d5625e…591cc3`).
  > - Restano: test e fixture (test-author), frontend, i18n, build, riavvio 6161.
  > **Note implementazione (frontend, 2026-10-01)**: R4.9 nell'interfaccia.
  > - **Dati**: `types.ts` `PacConversion`; `draft.svelte.ts:64` `ConversionMode`, `:80` `DraftBroker.conversionMode`, `'manual'` nei due costruttori (`:439`, `:536`) e nella copia del Broker (`copies.ts:198`); `request.ts:295` invia `conversion_mode`. Il draft vive solo in memoria (`draft.svelte.ts:4`), quindi nessun draft salvato può arrivare senza il campo, che ora è obbligatorio.
  > - **Risultato**: `result/model.ts`: `PlanStep` (funding o conversione manuale), `planSteps(funding, conversions)` (solo le manuali, che hanno la sequenza), `automaticConversions(conversions, brokerId)`, `conversionsFor(conversions, order)` (stesso Broker, accredito nella valuta dell'ordine; più origini possono accreditare la stessa destinazione, quindi è un elenco).
  >   - `OperationalPlan.svelte`: i passi numerati vengono da `solution.conversions`. La manuale dice «{debito} → circa {accredito}» e «per gli ordini in {valuta}», col «?» `fxEstimateHelp` (`pac-planner-plan-fx-estimate-help`). L'automatica è un riquadro nel gruppo «Ordini su {Broker}» (`pac-planner-plan-auto-conversion`, `data-conversion`), con gli importi «circa {debito} → {accredito}» (`pac-planner-plan-auto-conversion-amounts`) e il «?» `autoConversionHelp` (`pac-planner-plan-auto-conversion-help`). `orphanAutomatic` mostra in fondo le automatiche di un Broker senza ordini, così nulla si perde. Tolto `routeAsset`, che poteva nominare l'Asset sbagliato.
  >   - `ResultCell.svelte`: badge «Conversione automatica» sugli ordini in quella valuta (`pac-planner-plan-order-auto-conversion`), senza importo.
  >   - `OrderDetail.svelte`: la prop `conversions` sostituisce `fxActions`; la manuale resta `conversionAction`, l'automatica è `detail.conversionAuto` (`pac-planner-order-detail-conversion`, `data-mode`); lo spread è `detail.spreadLossConversion`.
  >   - `KpiCards.svelte`: il chip `fx` conta le manuali; nuovo chip `fx_auto` (`kpi.autoConversions`). `ResultView.svelte`: `hasPlan` conta anche `solution.conversions`, e `OrderDetail` riceve `conversions`.
  > - **Input**: `BrokerEditor.svelte`, sezione «Conversione di valuta» prima del funding (`:299-309`): un `fieldset` con due card radio, «Converti tu prima di comprare» e «Converte il Broker quando compri» (`pac-planner-conversion-modes`, `pac-planner-conversion-mode` con `data-mode`/`data-selected`, `pac-planner-conversion-mode-radio`). `notIn200` aggiornata. `BrokersStep.svelte:127-133`: la riga della card dice la modalità (`pac-planner-broker-conversion`, `data-mode`; `conversionValue` o `conversionValueAuto`), e `conversionHelp` spiega le due.
  > - **i18n R4.9** (nel batch di R11.13): ADD 11, cioè `brokerEditor.{conversionManual,conversionAutomatic}`, `brokers.conversionValueAuto`, `result.plan.{conversionFor,fxEstimateHelp,autoConversion,autoConversionAmounts,autoConversionHelp}`, `result.detail.{conversionAuto,spreadLossConversion}`, `result.kpi.autoConversions`; UPDATE 3, cioè `brokers.conversionHelp`, `brokerEditor.notIn200`, `result.plan.fxAmounts`.
  > - **Verifica**: svelte-check dopo R4.9 (`/tmp/libreFolio_d_ui13/svcheck_r49.log`): 3 errori e 41 avvisi, la baseline, nessuno nel planner. `front build --debug` ok (`front_build_r49.log`). 6161 riavviata alle 17:13:05 (shell `srv6161r11`, log `/tmp/libreFolio_d_f6/server_review_r11.log`), dopo l'ultima modifica al backend (16:47:47): serve il backend R4.9, e nel log non ci sono errori dell'app.
  > **⚠️ Fuori pista**:
  > - `result.detail.spreadLoss` è condivisa col chip dei costi di `KpiCards`: non la cambio, la conversione ha la chiave nuova `spreadLossConversion`.
  > - `result.plan.fxTitle` resta senza uso: va nella lista di fine round (decisione (a)).
  > - `orphanAutomatic` è difensivo: non c'è un vincolo FX↔BUY (vedi l'analisi sopra), quindi non posso escludere un'automatica su un Broker senza ordini.
  > - `FxStep.svelte` non cambia: il suo testo non dipende dalla modalità.
  > - Nell'editor ho usato card radio (`fieldset`, `label` + `input type=radio`) e non i bottoni `aria-pressed` di `TOGGLE_CARD` (`ui.ts:62-64`) previsti nel disegno: la scelta è esclusiva fra due, e un gruppo radio lo comunica da solo a tastiera e screen reader.
  > - Restano: test e fixture (test-author, in corso) e `api pac-planner-tool` nella corsia 6151.
- R11.13 ✅ 2026-10-01 — i18n, build, feedback (`ask_user`).
  > **Note implementazione (2026-10-01)**: il developer ha risposto all'`ask_user` del Round 11 con «ottimo». Subito dopo ha segnalato il blocco della Route su un Asset quotato in una valuta senza modalità d'ordine: è il Round 12.
  > **Note implementazione (2026-10-01)**: batch del giro `/tmp/libreFolio_d_ui13/i18n_round11.py` (R11.2, R11.4, R11.5, R11.7, R11.12), applicato con `dev.py i18n`.
  > - `--dry` finale (`i18n_r11_dry2.log`): ADD=20 (9 dei punti UI + 11 di R4.9), UPDATE=11 (8 + 3), guardia EN 0 problemi. Applicato alle 17:15:30 (`i18n_r11_apply.log`), tutti rc=0. Controllo ICU (`icu_check_r11.log`): 31 chiavi × 4 lingue, 0 problemi.
  > - Cataloghi: 4356 chiavi per lingua (erano 4336). sha8 en `cc406707`, it `acfe7d6d`, fr `03d87f38`, es `54eae373` (erano `5be9096d`, `7ac1707e`, `df9c478c`, `1ebcd709`).
  > - svelte-check (`svcheck_r49.log`, 17:10:11, dopo l'ultima modifica al codice): 3 errori e 41 avvisi, la baseline. `front build --debug` alle 17:17:20 (`front_build_r11.log`; `start.DkwlLmm2.js`, `app.B3xjPxE-.js`), servito dalla 6161 senza riavvio. Il build rifà da sé la sync del client prima di compilare: i generati, ignorati da git, hanno mtime 17:16 e lo stesso hash dei contratti tool `ebf753ba…dde77`.
  > - **Chiavi del planner senza uso, lista unica di fine round** (decisione (a); `unused_r99.py` → `/tmp/libreFolio_d_ui13/unused_r11.log`; lista in `files/i18n/unused_planner_keys_r11.txt` e `.grouped.txt` della sessione): **107**, tutte verificate come foglie del catalogo EN. Composizione:
  >   - le 86 del Round 9, meno `result.kpi.source`, di nuovo in uso come «?» del titolo delle cifre chiave (`KpiCards.svelte:152`);
  >   - 17 nuove trovate dallo script: `result.assets.{final,target}` (R11.7), `result.outcomes.{incumbent_found,infeasible_proven,no_incumbent,no_op}` e `result.proof.{decimalVerified,exactValue,infeasible,notProven,optimal,tieBreakClosed}`, `result.proof.sources.solver_status` (R11.10), `result.plan.fxTitle` (R11.12), `review.{exposureDimension,exposuresHelp}` (R11.3), `review.exposureRows` (R10.8);
  >   - 5 aggiunte a mano, che lo script non vede perché stanno sotto famiglie dinamiche: `review.kind.exposures` (`${KEY}.kind.${kind}`, `ReviewStep.svelte:122`; R11.3) e `result.kpi.{funding,fundingReachable,shortfallParts,shortfallPartsNoRounding}` (helper `text()`, `KpiCards.svelte:45`; R10.6).
  > - Dei 5 aggiunti a mano nel Round 9, 4 restano senza uso: `problems.routeCapMissing` (non più in `request.ts`), `result.sections.assets` (non fra le sezioni di `ResultView.svelte:53`), `result.weights.{finalShort,targetShort}` (solo in `result/WeightBars.svelte`, che nessuno importa).

#### Round 12 — Route: Asset quotato in una valuta in cui il Broker non ha una modalità d'ordine ⏳ 2026-10-01

**Feedback del developer** (01/10, dopo l'«ottimo» sul Round 11): Broker directa con conversione manuale, poi un Asset «test» (ETF) aggiunto a mano e quotato in una valuta diversa da EUR. Al passo Route la card dell'Asset dice «Il Broker non ha alcuna modalità d'ordine nella valuta del prezzo di questo Asset», e il banner blocca Continua («1 problema da correggere prima di continuare: Route · test · directa · …»). Non capisce l'errore, «visto che semplicemente tra i passi da fare mi verrà detto di convertire».

**Lettura del codice** (01/10):
- `draft.syncRoutes()` (`draft.svelte.ts:597-624`) crea **abilitata** ogni rotta Asset × Broker operativo.
- `draft.modeFor()` (`draft.svelte.ts:397-405`) cerca la modalità nella valuta del prezzo (N10), e dà `null` se il Broker non ne ha una in quella valuta. Senza prezzo ripiega sulla modalità della valuta di valutazione, o sulla prima.
- `request.ts:174` aggiunge `routeNoMode` per ogni rotta abilitata senza modalità. Passa `{currency}`, ma il testo non lo usa.
- `RoutingStep.svelte:144-148`: lo span rosso sta dentro il bottone che abilita o esclude la rotta. Sotto, i campi dei limiti compaiono anche senza modalità, con un'unità che non si conosce.
- Il contratto resta com'è. La modalità d'ordine (unità o importo, incremento, commissioni nella sua valuta) è per Broker × valuta, e la rotta usa quella nella valuta del prezzo. La conversione è una decisione FX a parte (R4.9: manuale = passo numerato, automatica = riquadro con gli ordini del Broker). Il piano non può dimensionare un ordine in USD con le regole e le commissioni in EUR.
- `BrokerEditor.svelte` è un dialogo autonomo (`{draft, brokerKey, onclose}`): lavora su una copia e scrive nella bozza solo con «Applica alla bozza». Si può aprire anche dalla Route.

**Decisione**, dentro i principi già fissati (nessuna modalità creata in silenzio con commissioni inventate, nessuna rotta esclusa in silenzio):
- Il requisito resta, ma la card lo spiega e offre le due uscite a un clic.
- Card di una rotta abilitata senza modalità: al posto dei campi dei limiti, un riquadro ambra fuori dal bottone, con:
  - la riga «{broker} non ha ancora una modalità d'ordine in {currency}» e un «?» che spiega a cosa serve e perché non è la conversione;
  - il pulsante «Aggiungi modalità {currency}», che apre l'editor del Broker con il blocco già aggiunto, i valori di partenza in vista, e scrive solo con «Applica»;
  - il link «Escludi su {broker}».
- `routeNoMode` vale solo se il Broker ha già delle modalità (a zero c'è `brokerNoMode`), e il suo testo dice cosa fare.
- Alternativa da proporre al developer, non implementata: creare da sola la modalità mancante, copiando tipo e incremento, con commissioni 0. Va contro «niente coefficienti nascosti»: la commissione in USD varrebbe 0 senza che nessuno l'abbia scritta.

**Passi:**
- R12.1 ✅ 2026-10-01 — Route: riquadro «modalità mancante» con «?», «Aggiungi modalità {currency}» ed «Escludi su {broker}»; campi solo con la modalità; editor del Broker con il blocco preaggiunto (`addCurrency`, `addFor`); `routeNoMode` solo con modalità presenti, con il testo nuovo.
  > **Note implementazione (2026-10-01)**: `RoutingStep.svelte` — tolto lo span rosso `pac-planner-route-no-mode` dal pulsante della route; con route attiva e senza modalità, al posto dei campi c'è il riquadro ambra `pac-planner-route-mode-missing` (`data-currency`), con «?» (`route.modeMissingHelp`: cos'è la modalità d’ordine, perché serve nella valuta del prezzo, che non è la conversione), «Aggiungi modalità {currency}» (`pac-planner-route-add-mode`, apre `BrokerEditor` montato fuori dalla radice come in `BrokersStep`) ed «Escludi su {broker}» (`pac-planner-route-exclude`, mette `route.enabled = false`, reversibile col toggle). I campi della route compaiono solo con la modalità. Helper `missingCurrency(asset, mode)`: valuta del prezzo se manca la modalità e il codice è valido, altrimenti `''`.
  > `BrokerEditor.svelte` — prop opzionali `addCurrency`/`addFor` (default `''`); all'apertura, se il Broker non ha già un blocco in quella valuta, ne aggiunge uno in cima alla copia di lavoro con `defaultMode(draft.nextId('mode'), addCurrency)`, marcato `data-added="true"` e con l'avviso ambra `pac-planner-mode-added-for` (`brokerEditor.addedFor`: controlla tipo di ordine, incremento e commissioni, poi applica). Come ogni modifica dell'editor, arriva alla bozza solo con «Applica alla bozza»: chiudere senza applicare non crea niente. Nessun valore inventato oltre ai default già usati da «Aggiungi valuta».
  > `request.ts:174` — `routeNoMode` solo se il Broker ha già modalità (a zero vale `brokerNoMode`, `request.ts:121`: prima i due avvisi si sommavano); testo nuovo con `{currency}` e le due vie d'uscita. Verificato su `draft.svelte.ts:397-404`: con modalità presenti, `modeFor` è null solo se la valuta del prezzo è impostata e manca il blocco; senza prezzo restituisce comunque una modalità.
  > Nessun altro riferimento a `route-no-mode` o al vecchio testo in `frontend/src`, `frontend/e2e`, `backend/test_scripts`, `mkdocs_src/docs`.
- R12.2 ✅ 2026-10-01 — i18n (`i18n_round12.py`), svelte-check, `front build --debug`, feedback (`ask_user`).
  > **Note implementazione (2026-10-01)**: `/tmp/libreFolio_d_ui14/i18n_round12.py` — 5 ADD (`route.modeMissing`, `route.modeMissingHelp`, `route.addMode`, `route.excludeHere`, `brokerEditor.addedFor`) e 1 UPDATE (`problems.routeNoMode`, ora con `{currency}` in tutte e 4 le lingue), solo via `dev.py i18n`, tutti rc=0. Guard EN = default del sorgente: 0 problemi; il guard ora legge anche `$t` su più righe (`\{\s*default:`) e i fallback di `problems.add(step, key, fallback)`, e controlla che le ADD siano assenti e l'UPDATE presente. Check ICU (`icu_check_r12.mjs`): 6 chiavi × 4 lingue, 0 problemi. Cataloghi 4361 chiavi per lingua (+5); sha8 en `fdb4e5f9`, it `9ccc83e6`, fr `97747c96`, es `2b555e85`. Termini: «modalità d’ordine», «Broker», «Asset» (IT); «mode d’ordre», «courtier», «actif» (FR); «modo de orden», «bróker», «activo» (ES); «Tipo di ordine», «Incremento», «Applica» come nell'editor.
  > svelte-check: 3 errori e 41 warning, identici alla baseline, nessuno nel planner (`/tmp/libreFolio_d_ui14/svelte_check_r12.log`). `dev.py front build --debug` rc=0 (`/tmp/libreFolio_d_ui14/front_build_r12.log`); 6161 serve il nuovo bundle senza riavvio (pid 23056, `/tools` 200). Nessun test automatico, per la regola del developer. Feedback chiesto con `ask_user`.
  > **⚠️ Fuori pista**: il guard di Round 11 non avrebbe visto le due chiavi con `$t` su più righe (riportava `NO SOURCE DEFAULT`), né i fallback di `problems.add`: allargato il guard prima di scrivere.

#### Round 13 — Obiettivi: conferma a tabella; FX: coppia aggiunta sul posto, tasso con simbolo e bandiera, «Non in 2.0.0» nel «?»; «Calcolo non riuscito»: causa nel motore ed errori più chiari; 02/10: motore A, via i limiti FX, errore più corto ✅ 2026-10-02 (R13.0–R13.12); il feedback apre il Round 14

**Feedback del developer** (01/10, con la risposta al Round 12):
1. Obiettivi, ribilanciamento: un avviso dice «3 items» in inglese; il pannello «Questi obiettivi cambiano:» elenca righe `nome: vecchio% → nuovo%` illeggibili, perché i nomi hanno lunghezze molto diverse. Vuole una tabella a 2 colonne, con i nomi lunghi che scorrono.
2. FX: al posto del link «Apri la pagina FX», un pulsante che aggiunge la coppia sul posto, con il flusso di aggiunta della pagina FX. Chiede cosa succede se la coppia esiste ma non ha punti, o se è manuale.
3. Non capisce «Non in 2.0.0: FX per Broker, margine di sicurezza, commissione di conversione, conversioni a più passi.»: va spiegato e rifatto (un «?» o toglierlo).
4. «1 EUR = 1.1298 USD», in automatico e in manuale, non ha bandiere né simboli: usare `currencyFormat.ts` e `CurrencyCode`.
5. «Calcolo non riuscito · errore della piattaforma strumenti — execution_failed · Il calcolo non è riuscito all’interno dello strumento.», e niente in console né nei log: vuole errori più chiari.

**Lettura del codice** (01/10):
- (1) `DistributionDialog.svelte:254-265` usa la `ConfirmModal` condivisa (`components/ui/modals/ConfirmModal.svelte`). Senza `itemsLabel` la modale ripiega su `` `${items.length} items` ``, in inglese e fisso (`:118`), e mostra solo una lista di stringhe (`changeItems`, `DistributionDialog.svelte:185`). Gli altri due usi nel planner (`RemovalConfirm.svelte:47`, `PacPlannerTool.svelte:421`) passano l'etichetta o non hanno elementi. La modale è condivisa: non la tocco.
- (2) `FxStep.svelte:189-195`: messaggio e `<a href="/fx">`. Il lettore (`fxRead.svelte.ts`) chiede la sezione `fx_quotes`; il backend prende l'ultimo `FxRate` della coppia con data ≤ `as_of`, **qualunque sia il provider** (`portfolio_allocation_source.py:1133-1166`, `:1447-1520`), altrimenti `allocation.saved_fx_missing`. Quindi «non memorizzato» copre due casi: coppia non configurata, e coppia configurata senza punti. Le coppie configurate sono in `fxRoutesStore.getConfiguredPairSlugs()` (slug alfabetico). La modale `FxPairAddModal` (`components/fx/FxPairAddModal.svelte`) è già riusata da dashboard (`dashboard/+page.svelte:858-863`) e dettaglio Asset; con un provider reale scarica da sola i tassi dopo la creazione (`finishFxPairCreation`, `services/fxCreationSync.ts:82`) e poi chiama `onsynced`. Permessi: `POST /fx/providers/routes` e `POST /fx/currencies/sync` chiedono solo l'utente autenticato (`api/v1/fx.py:762-766`, `:173-177`).
  - Risposte al developer: coppia configurata senza punti → «Scarica i tassi» (chiama i provider, ma solo con il clic dell'utente; la lettura del passo resta senza provider). Coppia con provider manuale: se ha punti, «Auto» legge l'ultimo punto come ogni altro tasso memorizzato; se non ne ha, resta «non memorizzata», e il tasso si scrive nella pagina FX o qui in «Manuale».
- (3) `FxStep.svelte:224`: elenca ciò che il contratto 2.0.0 non modella: un tasso diverso per Broker, un margine di sicurezza sul tasso, una commissione di conversione separata dallo spread, le conversioni a più passi (EUR→USD→CHF). È un testo da sviluppatore, non da utente.
- (4) `FxStep.svelte:173-187`: `1 {base} =` e `{quote}` sono testo semplice. `CurrencyCode` (`planner/shared/CurrencyCode.svelte`) rende `simbolo bandiera codice` con `formatCurrencyCodeHtml` (`utils/currency/currencyFormat.ts:80`).
- (5) **Causa**, riprodotta con dati sintetici (`/tmp/libreFolio_d_r13/repro_tie.py`, nessun dato personale): `_require_credit_tie_free` (`constraints.py:399-427`, chiamata a `:578-585`) solleva `LedgerPostingScopeError` quando un accredito FX può cadere esattamente a metà dell'unità minima (pareggio HALF_UP). Tasso 1,1298 e spread 0: €20 → `ready`; €30 → eccezione. Ogni tasso a 4 decimali con denominatore ridotto pari la fa scattare entro €50: la conversione manuale è di fatto inutilizzabile. L'eccezione esce dal plugin (`tool_plugins/pac_allocator.py:118-151`, nessun `except`); la piattaforma di C (`services/tools/worker.py`) la trasforma in `execution_failed` senza log, per scelta (nessun messaggio né input esposto). Il processo figlio (*spawn*) non chiama `configure_logging` (solo `main.py:74`): un `get_logger(...).error` nel figlio finisce sullo stderr del server (console, `docker logs`), non in `librefolio.log` (`/tmp/libreFolio_d_r13/probe_child_log.py`).
  - **Perché il guard non serve.** L'unità accreditata `u` è una variabile nuova per (rotta, cassa), con limiti `[0, floor(upper/q + 0,5) + 1]` che includono il valore HALF_UP vero (`_posted_units_term`, `:468-500`). L'epigrafe `q·u − q/2 ≤ E ≤ q·u + q/2` ammette due valori {k, k+1} solo a un pareggio esatto, e il valore vero è k+1. `u` compare solo con segno `+` nelle righe `≥ 0` del ledger (`:576-597`) e in nessun obiettivo (`objectives.py`). Quindi una decisione è ammissibile se e solo se lo è con l'accredito massimo, che è quello vero: il guard non evita nessuna potatura dell'ottimo (il solver «può» scegliere k, non «deve»). I quasi-pareggi in virgola mobile restano coperti dal replay esatto e dai `rounding_top_ups` (`evaluator.py:3684`), come per gli addebiti. È coerente con la decisione del 25/09 (X3 respinta, modello permissivo, «servono N unità minime in più»).

**Decisione** (UI, dentro i principi già fissati):
- (1) Conferma propria del planner (`PlannerDialog`), con una tabella Asset | Obiettivo (`prima → dopo`), nome con icona e scorrimento (`AssetNameCell`). La `ConfirmModal` condivisa resta com'è; il suo «N items» fisso va segnalato al coordinatore.
- (2) «Aggiungi la coppia» se la coppia non è configurata: apre `FxPairAddModal` con base e quote già scelte; a creazione o download finiti, il passo rilegge la coppia. «Scarica i tassi» se è configurata ma senza punti. Resta «Manuale». Nessun provider chiamato senza un clic.
- (3) «Non in 2.0.0» diventa un «?» accanto all'introduzione, con un testo per l'utente.
- (4) Riga del tasso: `1 <CurrencyCode base> = tasso <CurrencyCode quote>`, anche in manuale.
- (5) Motore: tre opzioni da far scegliere al developer. **A** (consigliata): togliere il guard e il codice che resta morto, con i loro test. **B**: tenerlo, ma marcare la prova `not_proven` invece di sollevare. **C**: righe intere esatte per l'HALF_UP degli accrediti. Errori: nel plugin un log ERROR con solo classe e posizione (file:riga:funzione), niente messaggi, importi o variabili locali, poi il rilancio, così il codice resta `execution_failed`. Testo UI: «errore interno del calcolo», non dovuto ai dati inseriti, nessun piano pubblicato, dettagli nel log del server per l'amministratore. Al coordinatore: proposta a C di un log di piattaforma per tutti i plugin.

**Passi:**
- R13.0 ✅ 2026-10-01 — questa sezione.
- R13.1 ✅ 2026-10-01 — Obiettivi: conferma a tabella.
  > **Note implementazione (2026-10-01)**: `DistributionDialog.svelte` non usa più la `ConfirmModal` condivisa. La conferma è un `PlannerDialog` (`testid` `pac-planner-distribution-confirm`, `zIndex` 70, `maxWidth` `lg`) con il messaggio e una tabella `table-fixed` a 2 colonne in un riquadro `max-h-80` che scorre, con l'intestazione fissa. Colonna Asset: `AssetNameCell` (icona e nome che scorre se non ci sta); colonna Obiettivo (`w-48`, a destra, `tabular-nums`): prima in grigio → dopo in grassetto. Righe `…-confirm-change` con `data-asset-key`. Piede: Annulla e «Sostituisci» ambra (`BUTTON_WARNING`, nuovo in `ui.ts`, stessi colori del `btn-warning` della modale condivisa). Tolto il derivato `changeItems`.
  > Chiavi nuove: `distribution.changeColumn`, `distribution.confirmApply`. Resta senza uso `distribution.change` (lista di fine round, decisione (a)).
  > **⚠️ Fuori pista**: l'«N items» in inglese viene dalla `ConfirmModal` condivisa (`ConfirmModal.svelte:118`, ripiego fisso quando manca `itemsLabel`). Non è un file di D: va segnalato al coordinatore.
- R13.2 ✅ 2026-10-01 — FX: «Aggiungi la coppia» e «Scarica i tassi» sul posto.
  > **Note implementazione (2026-10-01)**: nuovo `planner/fxSetup.ts`. `loadPairSetups()` legge `GET /fx/providers/routes` e classifica ogni coppia (slug alfabetico di `createPairSlug`): `provider` se almeno una rotta usa un provider diverso da MANUAL (catene comprese), `manual` se tutte le rotte sono solo MANUAL; `pairSetup()` ricade su `absent` se la coppia non ha rotte. In `FxStep.svelte` il ramo «non memorizzato» (`pac-planner-fx-no-rate`, con `data-setup`) mostra un testo ambra con «?» e un'azione per caso: `absent` → «Aggiungi la coppia» (`pac-planner-fx-add-pair`): apre `FxPairAddModal` con base e quote già scelte; `provider` → «Scarica i tassi» (`pac-planner-fx-sync`): apre `FxSyncModal` sulla sola coppia, e il download parte solo col clic dentro la finestra; `manual` → link «Apri la coppia» a `/fx/{slug}` in una nuova scheda (`pac-planner-fx-open-pair`). Finché le rotte non sono lette: solo il testo, senza pulsante.
  > Le rotte si leggono solo se almeno una coppia è «non memorizzata», e di nuovo a ogni `invalidateFxRoutes()` (`fxRoutesVersion`), quindi anche dopo una creazione fatta qui. Una lettura fallita ricade su «Aggiungi la coppia»: se la coppia esiste già, lo dice la finestra stessa (`fx.addPair.alreadyExists`).
  > Date: gli ultimi `SYNC_WINDOW_DAYS = 7` giorni fino a `defaultAsOf()`, la stessa data che il lettore usa con `refreshAsOf`. Sette giorni coprono un ponte o una festività della fonte; le due finestre mostrano le date e il «?» dice il numero (`{days}`): non è un coefficiente nascosto.
  > Rilettura: `reader.read(draft, [pair], …)` dopo una creazione senza download (solo MANUAL, `autoSyncStarted` falso) e a download finito (`onsynced`, anche parziale o fallito). Le callback tengono la propria coppia, perché `finishFxPairCreation` chiama `onsynced` dopo aver chiuso la finestra. La rilettura riempie solo un tasso ancora in attesa (`rateAwaitsRead`): un «Manuale» scritto nel frattempo resta com'è.
  > Chiavi nuove: `fx.pairMissing`, `fx.pairAbsent`, `fx.pairAbsentHelp`, `fx.pairNoRates`, `fx.pairNoRatesHelp`, `fx.pairManualOnly`, `fx.pairManualOnlyHelp`, `fx.addPair`, `fx.syncRates`, `fx.openPair`. Restano senza uso `fx.notStored` e `fx.openFxPage` (lista di fine round, decisione (a)).
  > **⚠️ Fuori pista**: la sezione prevedeva le coppie configurate da `fxRoutesStore.getConfiguredPairSlugs()`. Lo store condiviso tiene solo gli slug, senza i provider, e non distingue «configurata con un provider» da «solo manuale». Per non toccare uno store fuori scope, `fxSetup.ts` legge le rotte dentro il planner. Da proporre al coordinatore: i provider per coppia nello store condiviso.
- R13.3 ✅ 2026-10-01 — FX: «Non in 2.0.0» nel «?».
  > **Note implementazione (2026-10-01)**: tolta la riga `fx.notInVersion` in fondo al passo. Il testo nuovo (`fx.limitsHelp`, elenco a punti: tasso o spread diverso per Broker, margine di sicurezza sul tasso, commissione di conversione oltre lo spread, conversioni in più passi EUR → USD → CHF) va in coda al «?» dello spread, dopo una riga vuota; il `Tooltip` rende il testo semplice con `white-space: pre-line` (`Tooltip.svelte:425`), quindi gli a capo restano. Resta senza uso `fx.notInVersion` (lista di fine round, decisione (a)).
  > **⚠️ Fuori pista**: la decisione diceva «un "?" accanto all'introduzione». I quattro limiti riguardano tutti le conversioni, e il campo dello spread compare solo quando una conversione è possibile: lì il testo è vicino a ciò che descrive, e non appare in un piano che converte niente.
- R13.4 ✅ 2026-10-01 — FX: riga del tasso con simbolo e bandiera.
  > **Note implementazione (2026-10-01)**: in «Manuale» l'etichetta è `1 <CurrencyCode base> =` e il suffisso del campo `<CurrencyCode quote>`; in «Auto» `1 <CurrencyCode base> = tasso <CurrencyCode quote>`, con il tasso in grassetto. `CurrencyCode` rende `simbolo bandiera codice` da `formatCurrencyCodeHtml`, come il titolo della card. Nuovi `testid` `pac-planner-fx-rate-base` e `pac-planner-fx-rate-quote`. Solo markup, nessun template literal con valuta e numero: il gate `moneyRenderSites.test.ts` non cambia (un tasso non è un importo).
- R13.5 ✅ 2026-10-01 — Errori più chiari: log nel plugin, testo della UI.
  > **Note implementazione (2026-10-01)**: `tool_plugins/pac_allocator.py` ha `logger = get_logger(__name__)` e la chiamata a `plan_pac_allocation` dentro un `try`. Una `ToolExecutionError` (limite di tempo o annullamento della piattaforma, `execution_limit`) passa senza log: è un codice della piattaforma, non un guasto del motore. Ogni altra eccezione passa da `_log_engine_failure`, che scrive un ERROR «PAC planner engine failure» con `error_type` (la classe), `execution_id`, `where` (il frame più interno del codice LibreFolio, `file:riga:funzione`, con il percorso dalla radice del repo) e `raised_in` (il frame di libreria più sotto, solo se c'è). Non scrive il messaggio, gli argomenti né le variabili locali, che possono contenere importi. Poi `raise` nudo: il worker di C la trasforma comunque in `execution_failed`. Il processo figlio (*spawn*) non chiama `configure_logging`, quindi la riga va sullo stderr del server (console, `docker logs`), non in `librefolio.log`.
  > Prova sintetica, senza DB né server (`/tmp/libreFolio_d_r13/probe_plugin_log.py`, `probe_plugin_log2.py`): pareggio a €30 → `LedgerPostingScopeError` rilanciata, con il log `where=backend/app/services/pac_allocator/constraints.py:424:_require_credit_tie_free` e nient'altro; €20 → piano, nessun log; scadenza già passata, e `ToolExecutionError` sollevata dal motore → nessun log; errore dentro una libreria → `where` più `raised_in=decoder.py:361:raw_decode`. `ruff check` e `black --check` puliti.
  > UI: il titolo diventa «Calcolo non riuscito». Tolto «· errore della piattaforma strumenti», sbagliato per gli errori del motore e per quelli di rete. Il testo di `execution_failed` dice: errore interno dello strumento, nessun piano pubblicato, il difetto è nello strumento e non nei dati inseriti, il log del server registra dove, per l'amministratore. Il codice resta visibile. `execution_failed` copre anche `ExactReplayRejectedError`, cioè il replay esatto che rifiuta il candidato di SCIP oltre la soglia dei top-up (QX1-b): anche lì i dati sono validi e il limite è dello strumento. La riga di log distingue i due casi per classe.
  > Chiavi: aggiornate `result.platform.title` e `toolErrors.execution_failed`; nuova `result.platform.reference`.
  > **⚠️ Fuori pista**: `RunOutcome` di tipo `tool_error` ora tiene `executionId`, che la risposta porta già (`ToolResultIdentity.execution_id`, lo stesso id del contesto del worker: `executor.py:449-450`, `worker.py:122`). `ToolErrorPanel` mostra «Riferimento nel log del server: <id>» (`pac-planner-platform-reference`) solo per `execution_failed`, l'unico codice che lascia una riga di log: la piattaforma non ne scrive (`services/tools/executor.py` e `worker.py` non hanno un logger). La riga di log porta lo stesso id, così l'amministratore la trova dal riferimento che l'utente gli riporta. Da proporre al coordinatore, per C: un log di piattaforma per ogni eccezione non dichiarata di qualunque plugin, con lo stesso criterio (classe e posizione, niente messaggio).
- R13.6 ✅ 2026-10-02 — Motore: opzione A (developer, 02/10): via il guard dei pareggi degli accrediti FX e il codice rimasto senza uso, nel prodotto e nei test; regressioni via test-author.
  > **Note implementazione (2026-10-02)**: prodotto, `constraints.py` (13 righe in più, 89 in meno): via il guard `_require_credit_tie_free`, con la sua chiamata, e i tre helper rimasti senza uso, `_half_up_tie_reachable`, `_exact_currency_quantum` e `_exact_fx_rate`. La docstring di `_posted_units_term` ora dice perché il pareggio di un accredito è sicuro: l'accredito entra solo con `+` nelle righe `≥ 0` e in nessun obiettivo. ruff e black puliti; nessun `.py` nomina più le quattro funzioni.
  > Il caso del developer, `/tmp/libreFolio_d_r13/repro_tie.py` (log `repro_tie_after.log`): €20 e €30 a 1,1298 senza spread, e 1,25 con spread 4% e €50, danno tutti `PacPlannerReadyIncumbentResult`, `availability=ready`. Prima della correzione €30 andava in errore.
  > La sonda contro l'oracolo, `probe_credit_tie_oracle.py`:
  > - prezzo 2, cap 4: SCIP uguale all'oracolo (buy 4, funding 5, fx 5; dominio 240, 46 ammissibili);
  > - prezzo 1, cap 10: SCIP uguale all'oracolo su buy 8 (dominio 528);
  > - con le decisioni fissate, buy 7 e buy 8 sono ottimi; buy 9 non è ammissibile né per SCIP né per l'oracolo. Accredito esatto 15/2, registrato 8.
  > Test di test-author (`r13-credit-tie-tests`, lane 6151):
  > - policies: tolti l'import e il vecchio test A2 dell'helper; nuovo A2, `test_exact_fx_credit_tie_admits_the_true_round_up_and_not_one_quantum_more`. Con prezzo 1 e cap 10, buy 8 è ammissibile e `optimal` con saldo USD 0; buy 9 no, è `infeasible` con saldo −1.
  > - oracle: fixture `_credit_tie_fx_scenario(*, price, cap)` e Item 3b, `test_exact_fx_credit_tie_optimum_matches_the_hand_derived_one`. L'ottimo è derivato a mano: {buy 4, funding 5, fx 5}, `fixed_l2` = 1/9. 240 candidati, 46 ammissibili (1+3+5+8+12+17).
  > - solver: `credit_tie_fx` nel gate d'accordo, con uguaglianza esatta dei quanti e della chiave lessicografica.
  > - planner: `test_manual_conversion_reaching_an_exact_credit_tie_still_plans`, il caso €30 a 1,1298. Verifica prima le premesse (25,00 × 1,1298 = 28,245, con il pareggio dentro il box FX), poi l'esito `ready_incumbent`/`optimal_proven`/`completed`. Ogni accredito pubblicato deve essere l'HALF_UP del suo addebito × 1,1298.
  > Esiti con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6151 --data-dir /tmp/librefolio-r2-d services <azione>`: `pac-planner-policies` 40 passed, `pac-planner-oracle` 21, `pac-planner-solver` 20 (con `[credit_tie_fx]`), `pac-planner-service` 36, `pac-planner-proof` 30. Totale 147 passed, 0 failed, 0 skipped. ruff e black puliti sui 4 file. Log in `/tmp/libreFolio_d_r13/r136_*.log`. Alla fine la 6151 è libera (`lsof` rc=1).
  > Ho riletto i 4 diff e la derivazione a mano: residui 25, 121/9, 49/9, 1, 1/9 e conteggio 46, tutto corretto. Il gate d'accordo SCIP↔oracolo è riscritto (~:1946).
  > **⚠️ Fuori pista**: test-author ha notato che la frase «The tie never decides feasibility for a credit» era falsa. È proprio l'arrotondamento a 8 che rende possibile il buy 4; quello che non cambia l'insieme ammissibile è la scelta fra i due vicini. Ho corretto la frase nella docstring di `_posted_units_term`: è solo un commento, ruff e black restano puliti, e la 6161 non va riavviata perché il comportamento è lo stesso.
  > **⚠️ Fuori pista**: il test del planner usa la finestra `_TOOL_ENGINE_WINDOW_SECONDS` (30 s), non 5 s, perché verifica `optimal_proven`/`completed`. SCIP si ferma appena prova l'ottimo, e il file gira in 1,98 s. Due `__pycache__/*.pyc` contengono ancora i nomi rimossi: git li ignora e Python li ricompila da solo.
- R13.7 ✅ 2026-10-01 — i18n, svelte-check, `front build --debug`, riavvio della 6161, feedback (`ask_user`).
  > **Note implementazione (2026-10-01)**: `/tmp/libreFolio_d_ui15/i18n_round13.py` — 14 ADD (`distribution.changeColumn`, `distribution.confirmApply`, `fx.pairMissing`, `fx.pairAbsent`, `fx.pairAbsentHelp`, `fx.pairNoRates`, `fx.pairNoRatesHelp`, `fx.pairManualOnly`, `fx.pairManualOnlyHelp`, `fx.addPair`, `fx.syncRates`, `fx.openPair`, `fx.limitsHelp`, `result.platform.reference`) e 2 UPDATE (`result.platform.title`, `toolErrors.execution_failed`), solo via `dev.py i18n add|update`, tutti rc=0, nessuna rimozione (decisione (a)). Guard EN = default del sorgente: 0 problemi; rilettura dei 16 valori nei 4 cataloghi: 0 differenze (gli a capo di `fx.limitsHelp` compresi). Check ICU (`icu_check_r13.mjs`): 16 chiavi × 4 lingue, 0 problemi (`{days}` in tutte). Cataloghi 4375 chiavi per lingua (+14); sha8 en `b62bb24e`, it `a22680d0`, fr `11c86b19`, es `b4de7428`. Scansione finale (`scan_keys_r13.py`): 584 chiavi del planner nel sorgente, 0 mancanti, 0 diverse dal catalogo inglese. Termini: «coppia», «tasso», «provider», «Manuale» (IT); «paire», «taux», «fournisseur», « Manuel » (FR, spazi normali come nel resto del catalogo); «par», «tipo», «proveedor», «Manual», «bróker» (ES).
  > Lista di fine round (decisione (a)), nel file di sessione `files/i18n/unused_planner_keys_r11.txt`, ordinata: +4 senza più uso, verificate con grep anche nella forma `${KEY}` (`distribution.change`, `fx.notStored`, `fx.openFxPage`, `fx.notInVersion`), 111 in tutto.
  > svelte-check: 3 errori e 41 warning, identici alla baseline, nessuno nel planner (`/tmp/libreFolio_d_ui15/svelte_check_r13.log`). `dev.py front build --debug` rc=0 (`/tmp/libreFolio_d_ui15/front_build_r13.log`). 6161 riavviata perché il plugin è cambiato (R13.5): fermata la mia shell `srv6161r11` (pid 23056), porta libera, poi `srv6161r13` (pid 64653, log `/tmp/libreFolio_d_f6/server_review_r13.log`, stessi argomenti: `--test`, `--data-dir /tmp/librefolio-r2-d-prodcopy`, `--no-scheduler`, `--no-reload`); `/tools` e `/tools/pac_allocator` 200. Nessun test automatico, per la regola del developer. Feedback e scelta del motore (R13.6) chiesti con `ask_user`.
  > **⚠️ Fuori pista**: il guard ora legge anche le chiavi scritte come `` `${KEY}.x` `` (con `const KEY = 'tools.pacAllocator.planner…'` nello stesso file) e il blocco `TOOL_ERROR_FALLBACKS` di `issues.ts` (`toolErrors.<codice>`). Così ha trovato 3 differenze di Round 9 (R9.7) che il guard di allora non vedeva: `review.fxRated`, `review.routes`, `review.targets` avevano nel catalogo il testo voluto (plurali corretti, «1 of 1 Asset», «exchange rates»), ma nel sorgente un ripiego più vecchio. Allineati i 3 `default` di `ReviewStep.svelte` al catalogo; nessun cambiamento visibile, perché le chiavi esistono.
  > **⚠️ Fuori pista (2026-10-02)**: l'`ask_user` del 01/10 è stato interrotto prima di arrivare al developer, e il riavvio dell'app nella notte ha chiuso la 6161. Rimessa online con gli stessi argomenti (`srv6161r13b`, pid 7935, log `/tmp/libreFolio_d_f6/server_review_r13b.log`; `/tools` e `/tools/pac_allocator` 200), sullo stesso build. Domanda riproposta.

**Feedback del developer** (02/10, risposta al Round 13):
1. Motore: opzione **A**, «togli quello che non serve, sia dal prodotto che dai test».
2. Punti 1–4: «tutto fantastico».
3. Nel «?» dello spread va tolto l'elenco «Non in questa versione:». È un testo da sviluppatore, e nessuna di quelle voci si farà. Tasso o spread per Broker, margine di sicurezza e commissione di conversione non hanno senso: lo spread è già il parametro di margine che somma tutti gli attori della conversione. Le conversioni in più passi sono compito della parte FX, e qui ogni conversione è diretta. Se le voci sono in un backlog o altrove, vanno cancellate o segnate come non più da fare.
4. Testo di `execution_failed`: via la parte lunga («Il difetto è nello strumento…»); finisce a «…e nessun piano è stato pubblicato.»

**Lettura del codice** (02/10):
- (1) In `constraints.py` il guard è la chiamata `:578-585` più `_require_credit_tie_free` (`:399-427`). Restano senza uso `_half_up_tie_reachable` (`:358-375`), `_exact_currency_quantum` (`:378-382`) e `_exact_fx_rate` (`:385-396`): le chiama solo il guard (`:419-423`). Il guard è citato nella docstring di `LedgerPostingScopeError` (`:296-304`) e in quella di `_posted_units_term` (`:483-484`). `LedgerPostingScopeError` resta: serve a `_require_modelled_rounded_families` (`:351`, `:355`), che non riguarda i pareggi. Gli import `ExactRatio`, `ExactOrderRoute`, `_fx_pair_key` e `math` restano usati nel modulo. Nei test, `_half_up_tie_reachable` compare solo nell'import (`test_pac_planner_policies.py:79`) e nel test A2 (`:928-977`). L'arrotondamento HALF_UP dei pareggi resta provato in `test_pac_planner_exact.py:289-290` (`positive-tie`, `negative-tie`).
- Il gate d'accordo SCIP↔oracolo di questo piano (`:1946-1949`) usa `_half_up_tie_reachable` per definire i «domini senza pareggi». I pareggi che allargano il modello sono solo quelli degli addebiti (acquisto e commissione), dove il modello resta permissivo (X3 respinta). Un pareggio dell'accredito FX non cambia l'insieme ammissibile: il modello può sempre usare l'accredito più alto, che è quello vero.
- (3) Nel prodotto l'elenco compare solo in `FxStep.svelte:341-343`, in coda all'aiuto dello spread. Nel backlog: `TODO_FUTURI.md:565` (confine della prima versione: «FX single-hop e `fx_buffer_rate` esplicito», etichetta «Margine di sicurezza FX»), `:624` (route FX multi-hop) e `:625-626` (buffer FX dinamico). `TODO_FUTURI.md` è un file condiviso, non di D. `06_piano_sprint.md` non ha queste voci: le sue 2 «Conversion Fee» sono il campione eToro di BRIM (`:126`, `:597`). Nei piani di D le voci compaiono in tre modi: elenchi di cose rinviate o «non in 2.0.0», parti del disegno mai consegnate (margine di sicurezza, commissione di conversione, buffer FX), e cronaca delle decisioni.
- `fx_cost` della riga d'ordine: sempre 0 per descrizione (`schemas/pac_allocator.py:1334`), validatore `:1357`, costruito in `planner_report.py:626`. Con la decisione (3) non avrà mai un altro valore. Togliere il campo cambia il contratto: fuori da questo round.
- (4) Il ripiego è in `issues.ts:211` (`TOOL_ERROR_FALLBACKS.execution_failed`), la chiave è `toolErrors.execution_failed`.

**Decisione**:
- (1) Opzione A. Tolgo la chiamata, le 4 funzioni e i riferimenti nelle docstring; ruff e black. Test, via test-author: tolti l'import e il test A2. Aggiunti: la regressione del caso del developer (tasso 1,1298, spread 0, €30 → piano `ready`, con il pareggio raggiunto); una prova a decisione fissata sul pareggio esatto (passa un acquisto che consuma l'accredito arrotondato in su, non uno che consuma un'unità minima in più); un accordo SCIP↔oracolo su un dominio piccolo con pareggio dell'accredito e senza pareggi degli addebiti, dove gli ottimi devono coincidere. Selettori sulla corsia 6151, uno alla volta: `services pac-planner-policies`, `services pac-planner-service`, `services pac-planner-oracle`, poi `services pac-planner-solver` e `services pac-planner-proof`. Riscrivo il gate `:1946-1949`.
- (3) Tolgo la coda dell'aiuto. `fx.limitsHelp` va nella lista di fine round (decisione (a): nessun `i18n remove` durante i round). Nei piani di D, accanto a ogni voce rinviata o mai consegnata, aggiungo «❌ non più da fare (developer, 02/10/2026)» senza riscrivere il testo; la cronaca resta com'è. `TODO_FUTURI.md` e il campo `fx_cost` vanno al coordinatore, come decisione del developer.
- (4) Testo nuovo: EN «An internal error of the tool stopped the calculation, and no plan was published.» · IT «Un errore interno dello strumento ha fermato il calcolo, e nessun piano è stato pubblicato.» · FR «Une erreur interne de l’outil a interrompu le calcul, et aucun plan n’a été publié.» · ES «Un error interno de la herramienta detuvo el cálculo, y no se publicó ningún plan.» Il riferimento nel log (`result.platform.reference`) resta: è ciò che l'utente riporta all'amministratore.

**Passi:**
- R13.8 ✅ 2026-10-02 — questa sezione.
- R13.9 ✅ 2026-10-02 — FX: via l'elenco dei limiti dal «?» dello spread.
  > **Note implementazione (2026-10-02)**: in `FxStep.svelte` l'aiuto dello spread torna al solo
  > `fx.spreadHint`: via la coda `\n\n` + `fx.limitsHelp` aggiunta in R13.3. Nessun altro uso di
  > `limitsHelp` in `frontend/src`. La chiave resta nei cataloghi e va nella lista di fine round
  > (`files/i18n/unused_planner_keys_r11.txt`, ora 112 chiavi), accanto a `fx.notInVersion`.
- R13.10 ✅ 2026-10-02 — `execution_failed` più corto.
  > **Note implementazione (2026-10-02)**: `issues.ts:211` (`TOOL_ERROR_FALLBACKS.execution_failed`)
  > si ferma a «…and no plan was published.». i18n con `/tmp/libreFolio_d_ui15/i18n_round13b.py`
  > (copia del modello `i18n_round13.py`, solo UPDATE, guard EN = sorgente): `--dry` pulito, poi
  > `i18n update tools.pacAllocator.planner.toolErrors.execution_failed` rc=0 nelle 4 lingue, con i
  > testi della decisione (4). Cataloghi a 4375 chiavi ciascuno, invariati. Verifiche: ICU
  > (`icu_check_r13b.mjs`, letta su `r13b_keys.json`) 1 chiave, 4 lingue, 0 problemi;
  > `scan_keys_r13.py` 583 chiavi della sorgente, 0 mancanti, 0 diverse. La riga
  > `result.platform.reference` resta.
- R13.11 ✅ 2026-10-02 — Voci «mai» segnate nei piani di D; `TODO_FUTURI.md` e `fx_cost` al coordinatore.
  > **Note implementazione (2026-10-02)**: script one-shot `/tmp/libreFolio_d_r13/annotate_never.py`
  > (assert sul contenuto di ogni riga e sulle fence, scrittura solo a fine controlli): 24 marcature
  > «❌ non più da fare (developer, 02/10/2026)» e 3 note `>` dopo i blocchi ASCII/codice, in 9 file.
  > Suite target: master `:125`, `:482`, `:559` + nota dopo `:521` (`fx_fees`, `fx_buffer_amount`);
  > nucleo matematico `:854`, `:911`, `:912`, `:1335`; policy `:739`, `:747`, `:994`; architettura
  > `:364`; UI target `:896`, `:991`, `:1252`, `:1253`, `:1255`, `:1721` + nota dopo `:1244` (card FX per
  > Broker con spread, margine e fee propri). C0UiDelta `:147` + nota dopo `:527` (voci «Non in
  > 2.0.0»). Bozze, solo le tabelle dei rinvii: cronaca `:527`, `:541`; Round5 `:2126-2127`; Round7
  > `:2576-2577`. Il testo resta com'è: il segno si aggiunge accanto alla voce, o dopo il blocco.
  > `git diff --check` pulito.
  > **⚠️ Fuori pista**: la ricerca completa (109 righe) ha trovato più voci della lettura del 02/10
  > (policy `:739`, `:747`; master `:482`, `:559`; nucleo `:911`, `:1335`; UI `:991`, `:1252`). Segnate
  > anche quelle: sono parti del target mai consegnate. **Non** segnati `fx_mode` (UI target `:976`,
  > C0UiDelta `:140`): il modo in cui un Broker converte non è nella lista del developer ed è arrivato
  > dopo come `conversion_mode` (`schemas/pac_allocator.py:448`). Restano come storia: policy `:195` e
  > `:943` (multi-hop `unsupported`, comportamento attuale), le note di `ExactCore` e
  > `ContractsCapacity`, il dossier di review, `pac-rebalancer-end-to-end-design.md` e il resto delle
  > bozze Round5/Round7. `TODO_FUTURI.md` (`:565`, `:624`, `:625-626`) e il debito `fx_cost` vanno al
  > coordinatore, come decisione del developer.
  > Il coordinatore li ha registrati su `dev_release2` (02/10): `TODO_FUTURI.md` `:565`, `:624`,
  > `:625-626` barrati e segnati, nuova sottosezione «❌ Non più da fare — FX nel PAC»; `fx_cost` è il
  > terzo caso del gate «campi di contratto senza consumatore», da togliere con un cambio di versione
  > del Tool, non in questo round.
- R13.12 ✅ 2026-10-02 — i18n, svelte-check, `front build --debug`, riavvio della 6161 (cambia il motore), feedback (`ask_user`).
  > **Avanzamento (2026-10-02)**: svelte-check 3 errori e 41 avvisi, come la baseline
  > (`/tmp/libreFolio_d_ui15/svelte_check_r13b.log`); `front build --debug` ok
  > (`front_build_r13b.log`); 6161 riavviata come `srv6161r13c` (pid 25576), `/tools` e
  > `/tools/pac_allocator` 200 dopo 7 s. Gate `:1946` riscritto (R13.6). Mancano gli esiti di
  > test-author per R13.6, poi la richiesta di feedback.
  > **Note implementazione (2026-10-02)**: test-author per R13.6: 147 test verdi nella lane 6151
  > (`/tmp/libreFolio_d_r13/r136_*.log`). Feedback chiesto con `ask_user`; il developer ha risposto
  > il 02/10 con sei punti: (a) la versione «Backend/API 2.0.0 · UI 2.0.0» deve essere 1.0.0, perché
  > non è stato rilasciato nulla; (b) un testo nuovo per il «?» dello spread; (c) troppi decimali in
  > «Cifre chiave» e in «Prova e solver», da arrotondare all'unità minima della valuta; (d)
  > «esteticamente non mi pare di avere molto altro da dire, ben fatto!!!»; (e) «quando faremo il
  > ribilanciamento?»; (f) dopo le correzioni, integrare in `dev_release2` e aggiornare la baseline.
  > I punti (a)–(c) aprono il Round 14; (e) ha risposta nel Round 14; (f) passa al coordinatore.

#### Round 14 — versione 1.0.0, testo dello spread, importi all'unità minima della valuta ✅ 2026-10-02 (R14.8, gate sulla revisione unita: ✅ 2026-10-05)

**Feedback del developer** (02/10, con la risposta al Round 13):
1. «Backend/API 2.0.0 · UI 2.0.0» deve diventare 1.0.0: non è stato rilasciato nulla.
2. Il «?» dello spread va riscritto in modo generico e diretto: «un sovrapprezzo di margine per
   coprire eventuali variazioni del tasso ufficiale o commissioni del broker».
3. Troppi decimali, da arrotondare all'unità minima della valuta. I suoi esempi:
   - «Cifre chiave»: Investito dopo ≈2989,751460435475 €; Non investito ≈10,248539564524695 €;
     Costi e Perdita da spread 10,0581 €; Arrotondamento ≈0,000439564524694636 €;
   - «Prova e solver»: valori degli obiettivi ≈10,248539564524695 € e 10,0581 €; primale e duale
     dei passi del solver ≈10,248539564524435 € e ≈10,058100000000113 €.
4. «Quando faremo il ribilanciamento?»
5. Dopo le correzioni: integrazione in `dev_release2` e baseline aggiornata.

**Lettura del codice (02/10):**
- *Decimali.* `format.ts` `moneyArgs` (`:73-83`) fissa `maxFraction = min(20, max(minFraction,
  decimalScale(valore)))`: mostra tutte le cifre del valore. I risultati esatti del backend
  (`exact_ratio` con `display_decimal`, `finite_decimal`) arrivano con molte cifre, e
  `formatExactMoneyPlain/Html` (`:102/:107`) le passano intatte. Il solver: `formatSolverNumber`
  (`:203`) mostra il float di SCIP (`planner_report.py:1003`, `Decimal(str(float))`) con tutte le
  cifre e sempre con «≈». La colonna «Gap ass.» (`ProofPanel.svelte:126`) passa da
  `formatPlannerPlainDecimal`, pubblica e senza unità, anche quando il passo è in valuta.
- *Quote personali.* `economic_amount = custody_amount × share_percentage`
  (`portfolio_allocation_source.py:838`) non è arrotondato: lo mostrano `LiquidityStep.svelte:154`
  e `BrokerScopeCopyDialog.svelte:174`.
- *Versione.* I siti di D: `tool_plugins/pac_allocator.py:132-133,147,151`; `schemas/portfolio.py:1320`
  (`source_revision`); `portfolio_allocation_source.py:385`; frontend `tools/registry.ts:241-243`,
  `planner/defaults.ts:32`, `planner/types.ts:2,10,11`, `planner/request.ts:416`, il commento di
  `PacPlannerTool.svelte:3`, e la chiave `brokerEditor.notIn200` (`BrokerEditor.svelte:409`, con
  «SELL» non tradotto). I test: `test_tools_registry.py:1205-1206`,
  `test_portfolio_allocation_source.py:2096`, `test_api/test_portfolio_api.py:1741`,
  `tools/registry.test.ts`. Restano a 2.0.0 le fixture sintetiche di C (`test_tools_executor.py:82`,
  `test_tools_registry.py:537`) e i test di altri domini. Nessuna persistenza legge la versione.
- *Spread.* Chiave `tools.pacAllocator.planner.fx.spreadHint`, `FxStep.svelte` ~`:337`.

**Decisione (02/10, D, da confermare col developer nella richiesta di feedback):**
- I risultati esatti in valuta si arrotondano **sempre** all'unità minima, dentro
  `formatExactMoneyPlain/Html`: `exact_ratio` dal rapporto esatto (numeratore/denominatore in
  BigInt), `finite_decimal` dal decimale; metà lontano da zero; `Number()` solo sul testo già
  arrotondato. Coprono «Cifre chiave», tabella Asset, dettaglio ordine, avvisi di stato, cassa
  libera, perdite da spread e i valori degli obiettivi.
- Opzione `minorUnit` per i testi grezzi: le quote personali dei passi Liquidità e copia, e il
  primale e il duale del solver. I numeri di conteggio del solver: al più 2 decimali.
- **Non** si arrotondano: i prezzi di mercato, i valori digitati, i parametri degli issue, gli
  importi già all'unità minima (addebiti, commissioni, importi FX) e il gap relativo, che non ha unità.
- «≈» con la regola A: compare solo quando il valore arrotondato differisce da quello esatto
  («Arrotondamento ≈0,00 €», «Costi ≈10,06 €»). In alternativa, la regola C toglie «≈» dagli
  importi, come per i pesi (R10.8): la scelta va al developer.
- «Gap ass.» diventa una cella del solver con l'unità del passo: in valuta è arrotondato e
  mascherato con la privacy.

**Passi:**
- R14.0 ✅ 2026-10-02 — Questa sezione.
- R14.1 ✅ 2026-10-02 — Versione 1.0.0: siti di D, `api sync`, chiave nuova al posto di `notIn200`; test via test-author.
  > **Note implementazione**: 1.0.0 nei siti di D. Backend: `tool_plugins/pac_allocator.py`
  > (`contract_version`, `implementation_version`, `ToolUIDescriptor.version`,
  > `ToolDocumentation.version`), `schemas/portfolio.py:1320` (`source_revision`) e
  > `portfolio_allocation_source.py:385`. Frontend: `registry.ts:241-243`, `defaults.ts:32-34`,
  > `types.ts:2,10-11`, `request.ts:416` e il commento di `PacPlannerTool.svelte:3`.
  > La nota di `BrokerEditor.svelte:409` usa una chiave nuova, senza versione e con «vendita» tradotto:
  > `brokerEditor.notYetSupported`, aggiunta nelle 4 lingue con `dev.py i18n add`. `notIn200` non si
  > cancella (decisione a): va nella lista delle chiavi inutilizzate, che sale a 113.
  > Nessun controllo di `source_revision` nel frontend, fuori dal codice generato.
  > `api sync` rc=0: la mappa generata ha `pac_allocator["1.0.0"]`, `uiVersion` 1.0.0, fingerprint
  > `bd84ef14…`, generazione `bb77549b…`. ruff e black puliti sui 3 file backend.
  > Restano a 2.0.0, come previsto, le fixture sintetiche di C e i test di altri domini.
  > I 4 test di versione (`test_tools_registry.py:1205-1206`, `test_portfolio_allocation_source.py:2096`,
  > `test_api/test_portfolio_api.py:1741`, `registry.test.ts`) passano a R14.4, con test-author.
- R14.2 ✅ 2026-10-02 — Testo dello spread nelle 4 lingue.
  > **Note implementazione**: `fx.spreadHint` aggiornata nelle 4 lingue con `dev.py i18n update`, con il
  > testo del developer. IT: «Un sovrapprezzo di margine, in percentuale dell'importo convertito, per
  > coprire eventuali variazioni del tasso ufficiale o commissioni del Broker.» Il `default` di
  > `FxStep.svelte:340` coincide con l'EN, verificato dalla guardia dello script prima della scrittura.
  > Controllo ICU: 2 chiavi × 4 lingue, 0 problemi. Scansione sorgente/catalogo: 583 chiavi, nessuna
  > mancante, nessuna diversa.
- R14.3 ✅ 2026-10-02 — Importi all'unità minima (`decimal.ts`, `format.ts`, `ResultCell`, `ProofPanel`, le due quote personali).
  > **Note implementazione**: `decimal.ts` ha `roundDecimal`, `roundRatio` e `decimalEqualsRatio`
  > (BigInt, metà lontano da zero, nessun `-0`). In `format.ts`, `exactMoneyDisplay(value, places)`
  > arrotonda `finite_decimal` dal decimale e `exact_ratio` dal rapporto; `formatExactMoneyPlain/Html`
  > la usano con le cifre del catalogo o, in mancanza, quelle CLDR. `MoneyOptions.minorUnit` arrotonda i
  > testi grezzi: le quote personali di `LiquidityStep.svelte:154` e `BrokerScopeCopyDialog.svelte:174`,
  > e il primale, il duale e il gap assoluto del solver (`formatSolverNumber`, con `digits` passato da
  > `ResultCell.svelte:21,98` e `ProofPanel.svelte:127-129`). Il gap assoluto è ora una cella del solver,
  > quindi è mascherato con la privacy quando è in valuta. I numeri di conteggio del solver hanno al più
  > 2 decimali. Regola A: «≈» solo se l'arrotondamento cambia il valore. `isExactProjection` usa
  > `decimalEqualsRatio`.
  > **Non arrotondati**, come deciso: prezzi, valori digitati, parametri degli issue, flussi già
  > all'unità minima (addebiti, commissioni, importi FX), importi di custodia (`ReviewCell`) e gap relativo.
  > `StateNotice.test.ts` resta valido: le sue integrazioni sono flussi già all'unità minima.
  > svelte-check (client generato il 02/10 alle 11:55): 5 errori, 41 warning. I 3 errori sono quelli di
  > sempre; i 2 nuovi sono in `registry.test.ts:100,198`, che dice ancora `2.0.0` e va in R14.4.
- R14.4 ✅ 2026-10-02 — Test del formatter e dei componenti toccati, via test-author.
  > **Note implementazione (2026-10-02)**: test-author (`r14-tests`), lane 6151, un comando alla volta. Log in `/tmp/libreFolio_d_r14/r14_4_*.log`.
  > - Versione 1.0.0 nei test: `test_tools_registry.py:1205-1206`, `test_portfolio_allocation_source.py:2096`, `test_api/test_portfolio_api.py:1732` e `registry.test.ts`. In `registry.test.ts` il `fixtureArtifactVersion` sintetico passa da `1.0.0` a `9.4.2`, così resta diverso dalla versione vera del contratto.
  > - Test nuovi: `planner/decimal.test.ts` e `planner/format.test.ts` in `core-unit`, `planner/result/ResultCell.test.ts` in `component-unit` (`_frontend_utility.py`, 3 righe in più).
  > - Prodotto, durante il passo:
  >   - `decimal.ts` legge numeratore e denominatore solo come interi semplici (`INTEGER`, `parseInteger`). `BigInt` da solo accetterebbe anche `''`, `0x10` e testo con spazi.
  >   - `ResultCell.svelte` ha un `data-testid` per il test di componente.
  > - Esiti:
  >   - `services tools-registry` 93/0; `services portfolio-allocation-source` 89/0;
  >   - `api portfolio` 51/1, poi 52/0 dopo la correzione del Fuori pista 1; `api pac-planner-tool` 6/0;
  >   - `front-utility core-unit`: 100 file e 2833 test, poi 2840 con i casi L2; `front-utility component-unit`: 87 file e 2126 test;
  >   - prettier e ruff puliti; per black vedi il Fuori pista 3.
  > **⚠️ Fuori pista 1**: `test_report_allocation_source_authenticated_contract` (`test_portfolio_api.py:767`) era già rosso sulla baseline. Contava 7 sezioni del report, che dal 18/09 sono 13 (`d5e834de4` e `8ed7a0f0d`, di un altro workstream). Ora confronta le chiavi con `PortfolioReportResponse.model_fields` e chiede `None` per le sezioni non richieste. Il file è condiviso: se un altro ramo l'ha già corretto, all'integrazione va tenuta una versione sola. Segnalato nell'handoff.
  > **⚠️ Fuori pista 2**: test-author ha trovato che in L2 il «≈» valeva solo per i rapporti inesatti, perché `formatPlannerL2` usava `exactDisplay`. Ora usa `exactMoneyDisplay(value, SOLVER_COUNT_DIGITS)` (`format.ts:202-208`): 2 decimali e regola A anche per `finite_decimal`. I casi, in `format.test.ts:390-440`:
  >   - 12.345 → ≈12,35; 12.5 → senza «≈»;
  >   - 1/4 → senza «≈»; 1/3 → ≈0,33;
  >   - `0.124999999999999999999` → ≈0,12: come numero JavaScript varrebbe 0,125, che darebbe 0,13;
  >   - `formatSolverNumber` in EUR² → «≈»;
  >   - privacy ON → `≈••• EUR²`.
  > **⚠️ Fuori pista 3**: `black --check` fallisce su `test_portfolio_api.py` già a HEAD. Sono 8 blocchi (righe ≈1666–2305) del commit D `0088748a8` del 18/09, lontani dalle righe toccate. Non l'ho riformattato perché il file è condiviso: è debito D, da chiudere dopo l'integrazione. Segnalato nell'handoff.
- R14.5 ✅ 2026-10-02 — i18n, svelte-check, `front build --debug`, riavvio della 6161, feedback (`ask_user`) con la risposta sul ribilanciamento.
  > **Note implementazione (2026-10-02)**:
  > - i18n: nessuna chiave nuova dopo R14.1 (`brokerEditor.notYetSupported`) e R14.2 (`fx.spreadHint`).
  > - Build R14, poi 6161 riavviata (shell `srv6161r14`). Il feedback l'ho chiesto con `ask_user`, insieme a:
  >   - le modifiche;
  >   - la scelta del «≈», regola A o C;
  >   - la risposta sul ribilanciamento. È la prossima fetta dopo l'integrazione (§4): prima `invest_only`, con fixture e oracolo e poi SCIP; poi `invest_and_sell`, col verifier SELL. L'ordine lo decidono developer e coordinator.
  > - **Risposta del developer (02/10):** «è tutto perfetto… procedi con l'integrazione e poi rispondimi». Regola A confermata. Ha fatto tre domande nuove, a cui rispondo dopo l'handoff:
  >   - perché «Calcola» fa due chiamate;
  >   - una revisione critica di ogni parametro del pacchetto di calcolo;
  >   - dove sta la nota del Broker.
  > - Gate finali, sul codice con l'hardening di `decimal.ts` e la correzione L2:
  >   - svelte-check alle 12:48, con il client generato alle 12:27:47: 3 errori, 41 warning, 4 file. È il pavimento, e nessuno è in un file PAC. I 2 errori di `registry.test.ts:100,198` visti in R14.3 sono spariti. Log `/tmp/libreFolio_d_r14/svelte_check_r14_final.log`.
  >   - `front build --debug` dalle 12:51 alle 12:52, rc=0. Rigenera il client alle 12:51:23, con lo stesso fingerprint `bd84ef14…` e la stessa generazione `bb77549b…`. Il suo svelte-check dà di nuovo 3 errori, 41 warning, 4 file. Log `/tmp/libreFolio_d_r14/front_build_r14_final.log`.
- R14.6 ✅ 2026-10-02 — Chiusura della review: 6161 spenta, copia di prod cancellata, handoff d'integrazione al coordinator.
  > **Note implementazione** (02/10, 12:53):
  > - Il developer ha approvato il Round 14 («è tutto perfetto… procedi con l'integrazione») e la review sulla 6161 è chiusa.
  > - Igiene dati, su richiesta del coordinator, per la copia di prod `/tmp/librefolio-r2-d-prodcopy` (dati reali del developer):
  >   1. `chmod -R go-rwx` subito: directory `drwx------`, 0 file leggibili da gruppo o altri, 31 MB;
  >   2. server della review fermato (shell `srv6161r14`, pid 52786). Poi `lsof -nP -iTCP:6161 -sTCP:LISTEN` → rc=1 e `lsof -nP -iTCP:6151 -sTCP:LISTEN` → rc=1, mentre `ps -p 52786` → rc=1;
  >   3. `lsof +D /tmp/librefolio-r2-d-prodcopy` → vuoto (rc=1), e non esistono copie `.prev-*`;
  >   4. `rm -rf` alle 12:53:31, rc=0. Prova: `ls -ld /tmp/librefolio-r2-d-prodcopy` → «No such file or directory».
  > - Una copia futura si fa solo con l'OK esplicito del developer.
  > - Log della review in `/tmp/libreFolio_d_f6/server_review*.log`: nessun traceback. Le sole 2 righe d'errore dell'engine stanno in `server_review_r13b.log` (il caso R13 prima dell'opzione A) e riportano solo tipo d'errore, `execution_id` e posizione nel codice, senza importi.
  > - Handoff d'integrazione (CHECKPOINT READY) inviato al coordinator `c8328a01-…`, poi `FROZEN`.
- R14.7 ✅ 2026-10-02 — Preparazione al merge di `dev_release2`, unica modifica sbloccata dal coordinator: tolto il mio pezzo del test sulle sezioni del report.
  > **⚠️ Fuori pista**: doppia correzione in `test_portfolio_api.py`; vale quella di `dev_release2`.
  > - Il coordinator ha simulato il merge con `merge-tree`, senza toccare l'indice. Ha trovato un solo conflitto: il test sulle sezioni di `/portfolio/report` (`:767-780`), che avevo reso dinamico con `PortfolioReportResponse.model_fields`.
  > - `dev_release2` ha già `1b3a20fb0` (28/09, «pin all 13 report top-level keys»), con le 13 chiavi fissate a mano di proposito. Vale quella, che arriva col merge.
  > - Ho riportato le righe al testo di HEAD con l'edit tool. Prova:
  >   - `diff` fra HEAD e il file sulle righe 1–1737 → vuoto;
  >   - l'unico hunk rimasto è `:1741`: `source_revision="1.0.0"` in `_empty_planner_source_response`, che resta;
  >   - `ast.parse` OK; stesse 2542 righe di HEAD.
  > - Fino al merge il test torna allo stato del commit 5. `api portfolio` si rilancia dopo il merge, nella lane 6151, contro la versione di `dev_release2`.
- R14.8 ✅ 2026-10-05 (aperto 2026-10-02) — Gate sulla revisione unita (punto 3 del coordinator) e §0 di `handoff-pac-D.md`.
  > **Base**: il developer ha fatto i commit `6f29ec1cf` feat(pac) e `30d235b4d` docs(journal), poi il merge
  > `111b0bbd0` (genitori `30d235b4d` + `dd538d650`, albero `ea9479db`, uguale alla simulazione del coordinator).
  > Worktree pulito, stage vuoto, 6151 e 6161 libere.
  > **Sovrapposizioni semantiche controllate prima dei gate** (diff `30d235b4d..111b0bbd0`, log
  > `/tmp/libreFolio_d_r14/merge_shared_helpers.diff`):
  > - motore PAC, `schemas/pac_allocator.py` e piattaforma Tool: nessun file toccato dal merge;
  > - `portfolio_engine.py` e `portfolio_service.py` cambiano: alimentano `allocation-source`, quindi i gate
  >   chiave sono `services portfolio-allocation-source` e `api portfolio`;
  > - `echartsTooltipHelpers.ts`: ora fa l'escape dei nomi in `buildTooltipTopN/ByThreshold`; `buildTooltipRow` è
  >   invariato e `exposureTooltip.ts:44-54` fa già l'escape di tutto quello che gli passa;
  > - `Tooltip.svelte`: `{@html sanitizeHtml(...)}` (DOMPurify, config di default). I tooltip PAC con `html`/`math`
  >   (`HelpTip`, `OutcomeHeader` via `tipHtml`) usano `<br>`, `<ul class>`, `<li>` e KaTeX, che restano;
  > - route `/tools` e `/tools/[tool_code]`: tolto solo il `<title>` (lavoro del document-title).
  > **Fatto**:
  > - `api sync` rc=0 (`/tmp/libreFolio_d_r14m/01_api_sync.log`): fingerprint `bd84ef14…` e generazione
  >   `bb77549b…` invariati; i file generati sono ignorati, `git status` mostra solo il piano.
  > - `handoff-pac-D.md` §0 riscritta come misura al `111b0bbd0`: versione `1.0.0`, righe citate rimisurate,
  >   fingerprint `bd84ef14…`. Corretti anche i fatti superati: il renderer è registrato e restituisce `ready`;
  >   `api pac-planner-tool` esiste; `component-unit` ha 4 test PAC; aggiunto `document-title`. La nota in testa
  >   spiega «stesso numero, contratto diverso» (P1 `1.0.0`/`analyze` contro planner `1.0.0`/`plan`).
  > - Gate (script `/tmp/libreFolio_d_r14m/gates_backend.sh`, sequenziale, log `gate_<cat>_<action>.log`):
  >   `services tools-registry` 93/0, `services portfolio-allocation-source` 89/0.
  >
  > **⚠️ Fuori pista — backend condiviso che non parte (rosso infrastrutturale, prima di pytest)**: `api portfolio`
  > e `api pac-planner-tool` rc=1, entrambi con «Shared backend did not answer within 120s» → «shared test backend
  > failed to start». Nessun test raccolto. `/tmp/librefolio-r2-d/logs/librefolio.log` si ferma alle 10:32 UTC
  > (giro R14 di stamattina), quindi l'app non è nemmeno arrivata al log d'avvio. L'output del server non è
  > nell'archivio `.testLog/00_archive/logs_20261002_1326*.tar.xz`. Ipotesi da verificare, in ordine:
  > (1) import lento o bloccato sulla revisione unita, perché il merge tocca `borsa_italiana.py`,
  > `asset_sources/core.py` e il venv ha borsa 0.3.2; (2) carico della macchina, con tre altre lane attive
  > (6150, 6154, 6155). DB e file della lane non toccati oltre alla creazione del runner (`sqlite/` 13:24).
  >
  > **⚠️ Fuori pista — PAUSE del coordinator (2026-10-02, ~13:27)**: ho fermato la catena uccidendo solo lo script
  > padre (pid 12749), mentre `api pac-planner-tool` era già partito. Quel gate è finito da solo (rosso, sopra).
  > 6151 e 6161 libere (`lsof` vuoto). Nessun server mio acceso.
  >
  > **Non eseguiti**: `api tools`, `schemas pac-planner`, `schemas tools`, `services tools-lifecycle`,
  > `utils tools-wire`, `services pac-planner-*` (9 suite), `check-orphans`, `i18n audit`, `front check`,
  > `front build`, `front-utility core-unit`/`component-unit`, E2E `front-utility document-title`.
  > Da fare in §0: le note puntatore di §2 (`:175`) e §3 (`:253`) dicono ancora `2.0.0`.
  >
  > **Prossimo passo esatto, dopo «riprendi»**: (a) diagnosi dell'avvio, un comando per volta nella 6151, con
  > lo skill `test-triage`: rilanciare `api tools` da solo; se scade di nuovo, misurare il tempo di
  > `import backend.app.main` col venv condiviso e cercare dove il runner scrive l'output del backend condiviso.
  > (b) Poi riprendere lo script da `api portfolio` in giù, aggiungendo `front-utility core-unit` e
  > `component-unit`, poi `check-orphans`, `i18n audit`, `front check`, `front build` e `document-title`.
  > (c) Correggere le due note di §2/§3, `git diff --check`, `lsof`, e mandare il CHECKPOINT READY.
  >
  > **Ripresa 2026-10-05 («riprendi» del coordinator) — diagnosi chiusa, causa = build prima del bind**:
  > - Codice: in test mode `cmd_server` forza `debug_mode=True` (`dev.py:185`). Poi, **prima** di aprire
  >   la porta, chiama `auto_build_frontend(debug=True)` e `auto_build_mkdocs()` (`dev.py:214-221`). Il runner
  >   lancia `dev.py server --test --no-reload --no-scheduler` con stdout/stderr su DEVNULL se non è verbose
  >   (`scripts/test_runner/_server.py:207-232,269-270`) e aspetta `STARTUP_TIMEOUT = 120` (`:43`).
  > - Stato misurato prima di ricostruire: 95 sorgenti in `frontend/src` più recenti di `frontend/build/index.html`
  >   (build delle 12:52, prima del merge delle 13:18) e 8 `.md` più recenti di `mkdocs_src/site/index.html`
  >   (28/09). Quindi tutte e due le build erano vecchie.
  > - Misure, lane 6151, un comando per volta: `front build --debug` rc=0 in 88 s
  >   (`/tmp/libreFolio_d_r14m/10_front_build_debug.log`); `mkdocs build` (strict) rc=0 in 42 s
  >   (`11_mkdocs_build.log`, l'unico «Warning» è il banner del team Material). 88 + 42 = 130 s, cioè più dei
  >   120 s anche senza carico; il 02/10 c'erano in più altre tre lane attive. Poi `api tools` da solo:
  >   backend pronto in pochi secondi, **7 passed**, 21 s in tutto. L'ipotesi «import» è scartata: anche
  >   `api sync`, che importa l'app, era passato.
  > - **Lezione per la corsia** (resta valida per la slice e per l'integrazione): dopo un merge o una modifica a
  >   sorgenti frontend o `.md`, prima di un gate con server conviene lanciare `front build --debug` e, se
  >   servono, `mkdocs build`. E il `front build` di produzione va **dopo** l'ultimo gate con server: il
  >   server di test, quando trova il marcatore `.build-debug=0`, ricostruisce in debug prima del bind
  >   (`dev.py:2026-2031`). L'E2E invece no (`_frontend_common.py:92-96`, `debug=False` senza controllo del modo).
  > - Note puntatore di §2 (`:175`) e §3 (`:253`) di `handoff-pac-D.md` corrette a `1.0.0`. Verificate su
  >   `pac_allocator.py:132,147` e su `tool-contract-map.generated.ts:10,15,18`. Le righe `:12` e `:28` restano,
  >   perché sono storia.
  > - Gate ripresi con `/tmp/libreFolio_d_r14m/gates_resume.sh` (riassunto in `gates_resume.summary`), da
  >   `api portfolio` in giù; `front build` di produzione per ultimo.
  > - **Esiti 2026-10-05, revisione unita `111b0bbd0`, corsia 6151, un comando per volta** (log `gate_*.log`
  >   nella stessa cartella):
  >
  >   | Gate | Esito |
  >   |---|---|
  >   | `api portfolio` (con il test a 13 chiavi di `dev_release2`) | 58 passed |
  >   | `api pac-planner-tool` | 6 passed |
  >   | `schemas pac-planner` / `schemas tools` | 522 / 271 passed |
  >   | `services tools-lifecycle` / `utils tools-wire` | 91 / 196 passed |
  >   | `services pac-planner-*` (core, evaluator, oracle, policies, solver, proof, wire-numbers, report, service) | 164 / 159 / 21 / 40 / 20 / 30 / 39 / 25 / 36 passed |
  >   | `front-utility core-unit` | **2 failed** / 2876 passed — vedi sotto |
  >   | `front-utility component-unit` | 2216 passed |
  >   | `front-utility document-title` (E2E, unica spec sulla pagina Tools) | 22 passed |
  >   | `test check-orphans` | ✅ tutto raggiungibile |
  >   | `i18n audit` | rc=0, nessuna traduzione mancante; 521 potenzialmente inutilizzate (avviso) |
  >   | `front check` | 3 errori / 41 warning in 4 file = pavimento vecchio; **nessun file PAC**. `ToolExecutionMetrics.svelte` è di C ed è identico su `dev_release2` |
  >   | `front build` (produzione, per ultimo) | ✅ |
  >
  >   Porte 6151/6161 libere a fine catena (`lsof` vuoto).
  >
  >   > **⚠️ Fuori pista — conflitto semantico senza conflitto Git.** I 2 rossi di `core-unit` vengono dai gate
  >   > nuovi di K, «K step 13, item 0» (`53219bc00 fix(security): escape user text in HTML sinks`, arrivati col
  >   > merge; prima del merge non c'erano sul nostro lato). Scandiscono tutto `src` e colpiscono due file PAC:
  >   > - `htmlInterpolation.gate.test.ts`: `TargetsStep.svelte:62`, `${BAR_CLASS[totalState]}` dentro l'HTML
  >   >   costruito a mano. È una lettura per chiave calcolata, che il gate vuole «escaped or reported»; la sua
  >   >   lista di eccezioni è vuota («NONE yet»).
  >   > - `htmlSink.gate.test.ts`: `CurrencyCode.svelte:28`, `{@html html}`. Ogni sink deve essere
  >   >   `sanitizeHtml(…)` per intero, o una voce di `REVIEWED_SINKS` (nel file del gate, di K).
  >   >
  >   > Correzione proposta, solo nei file PAC: `${escapeHtml(BAR_CLASS[totalState])}` (output identico: le
  >   > classi sono statiche) e `{@html sanitizeHtml(html)}`. DOMPurify tiene span, classi ed emoji, e
  >   > `formatCurrencyCodeHtml` resta la chiamata riconosciuta dal gate privacy. In attesa del via del
  >   > coordinator. Dopo la correzione: `core-unit`, `component-unit` e di nuovo `front build`.
  >
  > **✅ Chiuso 2026-10-05 — correzione dei due sink, via del coordinator** (la proposta così com'è; niente voce
  > in `REVIEWED_SINKS`, perché il file del gate è di K ed è condiviso, e la chiave `html` sarebbe fragile):
  > - `TargetsStep.svelte:62` → `${escapeHtml(BAR_CLASS[totalState])}`. `escapeHtml` era già importato.
  > - `CurrencyCode.svelte`: import di `sanitizeHtml` da `$lib/utils/core/sanitizeHtml` e `:29` →
  >   `{@html sanitizeHtml(html)}`. `formatCurrencyCodeHtml` resta dentro il `$derived`.
  > - Rilanci (script `/tmp/libreFolio_d_r14m/gates_htmlfix.sh`, riassunto `gates_htmlfix.summary`, log
  >   `gate2_*.log`), corsia 6151, un comando per volta:
  >
  >   | Gate | Esito |
  >   |---|---|
  >   | `front-utility core-unit` | ✅ **2878 passed** (104 file); prima 2 failed / 2876 passed |
  >   | `front-utility component-unit` | ✅ 2216 passed |
  >   | `front check` | 3 errori / 41 warning negli stessi 4 file (BrokerSharingPanel, GlobalSettingsTab, TransactionFormModal.test.ts, ToolExecutionMetrics). Pavimento vecchio, **nessun file PAC** |
  >   | `front build` (produzione, per ultimo; marcatore `.build-debug=0`) | ✅ |
  >
  >   6151 libera a fine catena (`lsof` vuoto). Il pavimento passa a 0/0 con il prossimo merge di `dev_release2`.
  >
  > **→ Seguito (2026-10-05):** checkpoint `0900f11fa` fix(pac) + `946095d58` docs(journal). La slice di
  > compattazione del contratto 1.0.0 (decisione a del coordinator) prosegue in
  > [`plan-phase00PacContractCompaction.prompt.md`](plan-phase00PacContractCompaction.prompt.md).

---

## 4. Prosecuzione concordata (dopo lo STOP; ordine da confermare in R8)

1. **Rebalancer-first:**
   - prima una fixture `invest_only` valida, da far risolvere a view e oracolo;
   - poi la cascata SCIP `invest_only`;
   - poi `invest_and_sell` col verifier SELL (rischio più alto: inventario, cost basis, fisco,
     irriducibilità).
2. Allentare `_require_supported_scope` una policy alla volta.
3. Variante margine e `g` (il `buffer` smette di essere zero).
4. `limits/nodes` e il gate di capacità dopo la risposta sul numero di asset.
5. ~~`score_lattice_closure`.~~ Superato da D-X1: la prova è lo stato di SCIP. La forma è stata tolta
   nel commit 4 per decisione del developer (28/09 alle 10:58, F4 «Inventario D-X1»). Questa voce
   era stata scritta prima di D-X1.
6. `min_fragmentation` resta rinviata (TODO_FUTURI). Da C0b.2 non è più accettata sul wire:
   riattivarla vuol dire riallargare il Literal, e con lui il contratto.
7. Riscrittura completa della pagina MkDocs PAC (docs-writer) e `ToolDocumentation.version`.
   Poi E2E (Step 6).
8. Residui P1 a fine round: `allocationSource.ts`, l'`allocation_source` P1 di `/portfolio/report`
   e le 680 chiavi `tools.pacAllocator.*` P1.
9. Sankey/ribbon dei flussi e rifinitura mobile fine della serie D (rinviati da Q1).

---

## 5. Previsione conflitti

| WS | Superficie | Rischio | Mitigazione |
|---|---|---|---|
| **J** | `maskable.ts`, `currencyFormat.ts`, `moneyRenderSites.test.ts`, maschera dell'asse Y; `maskableQuantity` in arrivo | medio: se J cambia l'API dei formatter, rompe il PAC | Adapter unico `planner/format.ts`. Nessuna modifica ai file J. Lo scambio verso `maskableQuantity` lo fa il coordinator all'integrazione. `ToolsHub.svelte` è di D in questo round: si conserva `guideAnchor` `:146`, e il delta del layout delle card passa dal coordinator. |
| **K** | `utils/assetTypes.ts`, icone composite, `optionFilter.ts` (R13) | basso: il PAC usa `AssetSelect` (icone da `assetTypes.ts`), `BrokerSearchSelect` e `CurrencySearchSelect`, tutti basati su `SearchSelect` → `filterOptions` (`optionFilter.ts:37`) | Il PAC li consuma soltanto, senza modificarli. Il nuovo ordine di R13 è atteso e non è un difetto PAC. Test per `data-testid`/valore, mai per posizione. |
| **Risk** | `AllocationPieChart` (R12), `RiskExecutionContext`, `riskAnalysisHelpers.ts` (la valuta mascherata la ripara J), `risk.errors.*` (N17) | nullo | Grafici PAC-local. Nessun import da `riskAnalysisHelpers`. Messaggi dei `ToolError` PAC-locali; un namespace comune `tools.errors.*` lo propongo al coordinator, senza toccare `risk.errors.*`. |
| **I** | Grafici di dashboard | nullo | Nessun import dei loro componenti. |
| **A** | Livelli per-asset di Asset Global | nullo | Il PAC sceglie gli asset esistenti con `AssetSelect`; `AssetSearchAutocomplete` (ricerca sui provider) non gli serve. |
| **F** | Laboratorio | nessuno | — |
| **I / Risk** | `schemas/portfolio.py` (C0b.1 e C0b.4 toccano solo il blocco planner-source `:1205-1612`); `portfolio_allocation_source.py` (di D); `portfolio_service.py` e `portfolio_engine.py` in sola lettura (un import pigro di `_QUANTITY_DUST_THRESHOLD`, nessuna modifica) | basso: I ha aggiunto campi a `schemas/portfolio.py` in altri blocchi (`cost_history`, `pnl_candles`) | Modifiche solo nel blocco planner-source, niente riordino. Il client generato è ignorato da git: dopo ogni salto di baseline serve un `api sync` prima di misurare. **25/09 (coordinator):** in `test_portfolio_api.py` gli hunk di D e quelli di S10 di I stanno in zone diverse, ma dopo I + D va rilanciato `api portfolio` sulla revisione combinata: D toglie `currency_specs` e I riattiva i pin annidati di `:593`. |
| **Condivisi** | `registry.ts` (piattaforma: solo l'array L240-251); cataloghi i18n (additivi); `_frontend_utility.py` (liste `core-unit`/`component-unit`); `_backend_api.py` (`pac-planner-tool`); `moneyRenderSites.test.ts` (una voce `not-money` per `planner/format.ts`, attraverso il coordinator); `handoff-pac-D.md` (cartella C, su assegnazione); `CHANGELOG` (solo proposte) | medio sugli i18n per volume (≈ 400 voci) | Solo `dev.py i18n`, niente riordino. Elenco completo nell'handoff. |

---

## 6. Esecuzione

- **Writer unico**, cioè io: registro, i18n, runner e UI, per coerenza. Una Fleet non serve per
  questa fetta.
- **test-author:** TB1–TB6, con file esclusivi e lane 6151. Il prompt include il preambolo e i
  divieti della lane. Prima di TB5/TB6 aggiorna le fixture che C0b cambia: fingerprint
  (`test_pac_planner_schemas.py:2603`), `currency_specs` nelle request di test, il conteggio dei
  codici, la request con `min_fragmentation` (`:1695`).
- **docs-writer:** il ritocco puntuale della pagina PAC quando entra la UI («No interface yet» →
  disponibile); la riscrittura dopo la review.
- **Fuori pista / errori:** si registrano nel piano; niente workaround senza il coordinator.

## 7. Definition of Done (fino allo STOP)

- A: il grep dei termini superati è pulito fuori dai blocchi storici.
- B: descrizione nelle 4 lingue e nel backend; fingerprint invariato, con prova.
- C:
  - delta ASCII approvato ✅ (24/09) e riallineato alle decisioni;
  - C0b: contratto backend cambiato (Q-C0-1, Q-C0-4, Q-C0-7, Q-C0-6), `api sync` eseguito,
    fingerprint nuovo registrato con l'ora del client;
  - renderer registrato;
  - la card PAC è `ready` e non c'è toast degradato dovuto al PAC, verificato sulla copia di prod.
- D:
  - T1–T10 (con T7b) verdi via runner;
  - TB1–TB6 verdi in 6151, più le suite PAC esistenti toccate da C0b (`schemas pac-planner`,
    `services pac-planner-core`, `pac-planner-evaluator`, `portfolio-allocation-source`,
    `api portfolio`, `api tools`);
  - `front check` al pavimento, con l'ora del client;
  - `i18n audit` pulito;
  - gate J verde.
- E: runbook eseguito dal developer e feedback registrato.
- Handoff:
  - file condivisi toccati;
  - proposte CHANGELOG e commit;
  - elenco esplicito di **cosa non è stato eseguito**;
  - porte 6151 e 6161 libere; `FROZEN`.

## 8. Proposte (non eseguite)

- Commit, uno per passo:
  - `docs(pac): align tool contract docs with planner v2`
  - `fix(pac): describe planner v2 on the tool card`
  - `docs(pac): record C0 delta decisions`
  - `refactor(pac): derive currency quantum from babel` (C0b.1)
  - `refactor(pac): drop min_fragmentation from the wire` (C0b.2)
  - `fix(pac): reject asset exposures above 100%` (C0b.3)
  - `feat(portfolio): current distribution in allocation-source` (C0b.4)
  - `feat(pac): planner v2 tool UI`
  - `test(pac): cover planner tool and allocation-source APIs`

  > **25/09 — checkpoint.** Uno per passo non si può fare per file, e il coordinator mette in stage
  > per percorso:
  > - C0b.1, C0b.2 e C0b.3 condividono `schemas/pac_allocator.py`, `normalize.py` e `issues.py`;
  > - C0b.1 e C0b.4 condividono `schemas/portfolio.py` e `portfolio_allocation_source.py`;
  > - B e C8 condividono i quattro cataloghi i18n.
  >
  > Proposti invece **5 commit per file**, disgiunti e completi (106 file, verificato con `comm`):
  > 1. `docs(pac): record round-5 plan and realign docs` — 17 file del journal;
  > 2. `fix(pac): describe planner v2 on the tool card` — fallback EN e test del registro (2 file);
  > 3. `feat(pac): planner contract for the v2 UI` — C0b.1-C0b.4 con fixture e test (16 file);
  > 4. `test(pac): cover the planner tool API` — TB1 e la voce del runner (2 file);
  > 5. `feat(pac): planner v2 tool UI` — `planner/`, registro, i18n, voce del gate J (69 file).
  >
  > **25/09 alle 09:33 — committati** dal developer con lo script guardato del coordinator, in fila
  > su `f1047f766`:
  > - `4cd2cda56` (17 file) → `93704e3da` (2) → `f401f5e1b` (16) → `a6e2926f3` (2) → `0210f9848` (69);
  > - 106 file, +16363/−261, albero pulito;
  > - il coordinator ha verificato che ogni commit contiene esattamente la sua lista e che i
  >   messaggi sono identici ai file.
  >
  > **25/09 — Passo F, commit 1 e 2** (handoff al coordinator; messaggi e liste in
  > `/tmp/libreFolio_commits/d-f1-*` e `d-f2-*`, copia in `files/passo-f-commits/` della sessione):
  > 1. `docs(pac): record D-X1 and QX1-b in the designs` — F0, 8 file del journal (i cinque
  >    design, il dossier, il README di `implementation/` e lo Step3);
  > 2. `fix(pac): bound the solver fee by its minimum` — X2: `constraints.py`, `compiler.py`, i due
  >    file di test e questo piano (5 file).
  >
  > Vanno committati in quest'ordine, e il commit 2 prima che cominci QX1-a: i due toccano entrambi
  > `constraints.py`, e il coordinator mette in stage per percorso.
  >
  > **25/09 alle 11:25 — committati** dal developer con lo script guardato del coordinator
  > (`/tmp/libreFolio_commit_d_f12.sh`), in fila su `0210f9848`:
  > - `856c2193f` (8 file) → `f92e5560b` (5);
  > - 13 file, +570/−45, albero pulito;
  > - il coordinator ha verificato liste e messaggi, come per il checkpoint.
  >
  > **25/09 — Passo F, commit 3** (handoff al coordinator; messaggio e lista in
  > `/tmp/libreFolio_commits/d-f3-*`, copia in `files/passo-f-commits/` della sessione):
  > 3. `fix(pac): model the solver fee cap exactly` — QX1-a: `constraints.py`, `compiler.py`, i
  >    due file di test e questo piano (5 file), sopra `f92e5560b`.
  >
  > **25/09 alle 11:58 — committato** dal developer con lo script guardato del coordinator
  > (`/tmp/libreFolio_commit_d_f3.sh`): `6061affd7`, 5 file, +315/−69. Lo SHA l'ho letto con
  > `git log`. Dopo il commit l'albero è pulito, e gli sha256 dei 5 file sono quelli verificati dal
  > coordinator.
  >
  > **28/09 — Passo F, commit 4** (handoff al coordinator; messaggio e lista in
  > `/tmp/libreFolio_commits/d-f4-*`, copia in `files/passo-f-commits/` della sessione):
  > 4. `fix(pac): make SCIP status the only proof` — D-X1, sopra `6061affd7`: 31 file, cioè 29
  >    modificati (questo piano compreso), 1 cancellato (`oracle.py`) e 1 nuovo
  >    (`_pac_exhaustive_oracle.py`). Backend, test e fixture, voce condivisa del runner (6 testi),
  >    UI e i18n.
  >    Un solo commit: schema, planner, UI, i18n e test cambiano insieme, perché lo schema della
  >    prova è cambiato e il fingerprint lega il client.
  >
  > **28/09 alle 12:51 — committato** dal developer con lo script guardato del coordinator
  > (`/tmp/libreFolio_commit_d_f4.sh`): `b48b3cec9`, 31 file, sopra `6061affd7`. Il coordinator ha
  > verificato la lista e il messaggio. Git legge `oracle.py` → `_pac_exhaustive_oracle.py` come
  > una rinomina, quindi il suo script conta i file con `--no-renames`. Dopo il commit l'albero è
  > pulito.
  >
  > **28/09 alle 13:51 — merge di allineamento** `dev_release2` → D, lanciato dal developer con lo
  > script del coordinator: `d32f27c24`, genitori `b48b3cec9` e `7c61dd924`, nessun conflitto. Il
  > gate sulla nuova base è nel Passo F, punto 8 della ripresa del 28/09.
- CHANGELOG `[Unreleased]` (**superato il 25/09**, vedi la nota sotto):
  - `✨ Added` — «PAC allocator: interactive planner in Tools»;
  - `✨ Added` — «PAC allocator: copy the current portfolio distribution as the starting target»;
  - `🐛 Fixed` — «Tools page no longer reports the PAC allocator interface as missing; card
    describes the current tool»;
  - `🐛 Fixed` — «PAC allocator: asset exposures summing above 100% are reported as invalid input
    instead of failing the run».

  > **25/09 — proposta corretta.** Nessuna parte del PAC è rilasciata (`v1.1.0` non contiene
  > `pac_allocator`). Le due voci `🐛 Fixed` descriverebbero quindi difetti che nessun utente ha
  > mai visto. Resta **una sola modifica**: la voce PAC esistente in `### ✨ Added`
  > (`CHANGELOG.md:18`), da applicare all'integrazione, **dopo il Passo F**:
  > - «whole-unit purchase plans» → «purchase plans, in whole units or amounts,»;
  > - «**Its interactive interface is not ready yet**: the catalogue card says so explicitly and
  >   starts no calculation.» → «**Its interactive planner** walks through liquidity, brokers,
  >   assets, targets and routing, can copy current prices, cash and the current portfolio
  >   distribution with their source and date, and shows each plan with its proof.»
  >
  > Il resto della voce resta vero anche con D-X1, compresa la frase sulle tre risposte.
