# Piano D — Round 5 post-merge: UI PAC v2 nella build, poi review di dettaglio

**Stato:** APPROVATO dal developer il 24/09/2026 (uscita dal plan mode in autopilot); in esecuzione. I gate umani (delta ASCII, test list, runbook, STOP) restano fermate esplicite anche in autopilot.
**Baseline:** `f1047f766` (`dev_release2`), albero pulito, branch `e-alfy-allocatore-pac` — verificati il 23/09 e di nuovo il 24/09, prima del Passo 0.
**Posizione:** `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacRound5PostMerge.prompt.md`
(copia del piano di sessione approvato).
→ Delta C0: [`plan-phase00PacRound5-C0UiDelta.prompt.md`](plan-phase00PacRound5-C0UiDelta.prompt.md).
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
| T5 | stati da fixture | `needs_input`, `invalid`, `unsupported`, `ready_no_op`. `ready_incumbent` × {`optimal_proven` oracolo, `optimal_proven` lattice, `gap_bounded`, `not_proven`}. `ready_infeasible` × {oracolo, conflitto deterministico}. `ready_no_incumbent`. Per ognuno `data-state`; badge «ottimo» **solo** con `optimal_proven`. |
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
   | S2 | solo manuale, senza asset DB | ~~proven oracolo~~ **corretto il 24/09:** `ready_incumbent` + `not_proven` quando il contributo passa da una route di funding di taglia reale. Il trasferimento si enumera al centesimo (`evaluator.py:694-716`), per cui 1000 € su due ETF a 100 e 50 dà 100 001 × 11 × 21 ≈ 2,3·10⁷ candidati, sopra il tetto di 200 000: decide SCIP. Nessuna copia necessaria (quantum da babel, C0b.1) |
   | S2b | come S2, dominio minuscolo (5 € su ETF a 1 e 2) | `ready_incumbent` + `optimal_proven` dall'oracolo; il testimone riporta 501 × 6 × 3 = 9 018 candidati |
   | S2c | PAC comune (100 € su ETF a 50 e 100) | **difetto 🔴 X1** (nota del Passo E): oggi `tool_error` `execution_limit`. Atteso dopo la correzione: `ready_incumbent`, con prova o senza, mai errore |
   | S3 | copie da broker OWNER | provenance e date visibili; età in giorni dei dati non del giorno, nessuna conferma (Q-C0-3) |
   | S4 | broker non OWNER | errore esplicito |
   | S5 | budget sotto la quota minima più le fee | `ready_no_op` |
   | S6 | vincolo impossibile | `infeasibility_proven` |
   | S7 | pesi non validi | `invalid`, campo evidenziato |
   | S8 | broker inattivo o altro caso unsupported | `unsupported` |
   | S9 | dominio oltre 200 000 candidati | `not_proven`, tempi in C14; scenario testimone del delta C0 §0.1 |
   | S10 | EUR + USD con FX e spread | righe FX nel piano |
   | S11 | busy e annulla | D7 |
   | S12 | modifica dopo il risultato | stale |
   | S13 | logout | draft distrutto |
   | S14 | privacy ON/OFF | come T7 |
   | S15 | viewport mobile | D4 |
   | S16 | «Copia distribuzione corrente» sui dati del developer | pesi uguali a quelli della pagina Allocazione quando lo scenario comprende tutti gli holding; asset manuale a 0 con nota; target applicato solo con «Usa come target» |

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
  > - Evidenza: `git diff --check` pulito; 9 file di documenti, nessun file di codice.
  >
  > **⚠️ Fuori pista**:
  > - Nel 05 il passaggio superato va da `:242` a `:246`, non fino a `:244` (detto al coordinator).
  > - Rileggendo Difetto A: uno stage SCIP infeasible è per forza `unfinished`, mentre
  >   `ready_infeasible` richiede `completed`. È il vincolo che F1 deve sciogliere.
- **F1 — schema.**
  - Prova di ottimo e di impossibilità con una fonte «solver».
  - Lo stage infeasible diventa uno stato completato, così `ready_infeasible` è raggiungibile da
    SCIP.
  - Si rimuovono `ExhaustiveOracleWitness` e `SolverNotRunEvidence` dalle union di produzione.
- **F2 — motore.**
  - `planner.py` usa solo SCIP.
  - `proof.py` promuove gli esiti di SCIP.
  - Si corregge la mappa di stato in `solver.py` e il suo commento «absolute» (`:91`).
  - Si aggiorna la proiezione in `planner_report.py`.
- **F2b — fedeltà delle commissioni.**
  - X2 (commit 2): limite superiore `max(floor, rate · notional_upper)` nel fee epigraph e in
    `_fee_variable_upper`. Il tetto resta fuori fino al commit 3 (vedi il fuori pista sotto).
    ✅ 2026-09-25
  - QX1-a (commit 3): il tetto esatto con una binaria `capped` per ogni route che ha un tetto, con
    Big-M derivato dai limiti della route. Solo allora il limite diventa
    `max(floor, min(rate · notional_upper, cap))`.
  - `test_fee_epigraph_cap_oblivious_regression` si inverte al commit 3.

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
- **F2c — arrotondamenti oltre la cassa (QX1-b, deciso il 25/09).**
  - Il replay classifica il rifiuto. Se l'unica violazione è un deficit di cassa entro
    `N × unità minima` per cassa, il piano esce con l'importo da aggiungere per ogni cassa.
    Altrimenti è un errore (§2).
  - Schema: un campo nel risultato pronto con le casse da integrare (broker, valuta, importo, `N`).
  - Report e UI: la nota per cassa; i18n via `dev.py i18n` nelle 4 lingue.
  - Il deficit è un dato personale, quindi passa dalla maschera della privacy.
- **F3 — oracolo solo nei test.**
  - `oracle.py` passa nell'albero dei test.
  - Un test strutturale verifica che nessun modulo di produzione lo importi.
- **F4 — test backend** (test-author, lane 6151).
  - Accordo SCIP↔oracolo allargato alle forme di commissione: fissa, minimo sopra
    `rate · notional_upper`, tetto che morde, tetto piccolo per titolo.
  - Regressione X1 (100 € su due ETF: veloce) e X2 (minimo 1,50 €: 9 quote); 5 € contro minimo
    d'ordine 10 € → `ready_infeasible` da SCIP.
  - F2c (QX1-b):
    - `3 × 33,335` su 100,00 € → 3 quote, e 0,01 € da aggiungere;
    - un deficit oltre `N` unità minime → errore;
    - un'altra violazione delle regole esatte → errore, anche se il deficit sta sotto la soglia;
    - una valuta a 0 decimali (JPY) e una a 3 (BHD), per l'unità minima.
  - Il gate d'accordo SCIP↔oracolo tiene conto di X3 respinta. Dove un pareggio è raggiungibile,
    SCIP può fare meglio dell'oracolo esatto usando il centesimo del pareggio. Quindi:
    - sui domini senza pareggi (`_half_up_tie_reachable` falso) gli ottimi coincidono;
    - altrove SCIP non è mai peggiore dell'oracolo.
  - Schema e API.
  - Le prove usa-e-getta del 24/09 sono copiate nella cartella di sessione (`files/x1-probes/`),
    perché `/tmp` si svuota al riavvio.
- **F5 — frontend.**
  - Testimone del solver al posto di quello dell'oracolo in `ProofPanel.svelte`; tipi e
    `StateNotice`.
  - i18n via `dev.py i18n`, poi `api sync`, dichiarando l'ora del client accanto a `front check`.
- **F6 — verifica.**
  - Suite su 6151, `front check` e build.
  - Smoke S2, S2b e S2c più un caso X2 sulla copia 6161.
  - Copia rinfrescata prima della review.

### ⛔ STOP — review di dettaglio col developer

Ogni tema matematico si guarda **sulla schermata della UI che lo espone**, sui dati del developer:

| # | Tema | Contenuto |
|---|---|---|
| R1 | Modello di input e unità | Liquidità, broker, asset, routing: cassa per valuta, contributi separati, passo di quantità, importo, fee, provenance e staleness. Reperti N10, N13, N14, N16, N21. **Da confermare:** la lettura prudente di Q-C0-2 (nessuna somma di importi in UI) e il default del tetto delle route (`1000000000`). |
| R2 | Normalizzazione e issue | 79 codici; `needs_input` / `invalid` / `unsupported`. N1 chiuso da Q-C0-4 (C0b.2); esposizioni oltre il 100% → `invalid` (C0b.3). Reperti N11, N12, N17, N20. |
| R3 | Evaluator esatto e ledger | Decimal/ExactRatio; arrotondamenti (storia del difetto HALF_UP); spread FX applicato una volta sola; le fee non sono investimento; niente doppio conteggio della cassa. **QX1-b (25/09)** cambia il ledger: un piano può chiudere una cassa sotto zero di al più `N` unità minime, con l'importo da aggiungere. MathematicalCore §22 chiede per questo una review matematica: si fa qui, sulla schermata della nota, insieme al conteggio di `N` (crediti FX inclusi). |
| R4 | Cascata obiettivi | L2 fixed → U → priorità → fee → righe → tie-break; cosa significano L2 (EUR²) e U. |
| R5 | Ricerca e prova | ~~Oracolo fino a 200 000 = dimostrato; SCIP oltre = `not_proven`; infeasible solo dall'oracolo;~~ **D-X1 (24/09):** SCIP unico; `optimal` su tutti gli stage = ottimo, `infeasible` sul primo = impossibile, limite = tempo scaduto; l'oracolo resta nei test. Determinismo = `completed`; budget di 30 s; **domanda aperta sul numero di asset** (ginocchio ≈ 18 asset multi-valuta). Le soglie crescenti per il tetto delle route (Q-C0-5) entrano nella stessa misura. **🔴 X1 (24/09):** la premessa «fino a 200 000 = dimostrato» valeva solo fino a circa 13 000 candidati (≈ 3,3 ms ciascuno contro la soft deadline di 44 s); fra 13 000 e 200 000 il job moriva con `execution_limit`. ~~Opzioni: sotto-budget dell'oracolo con fallback a SCIP; tetto tarato sul tempo; funding e FX dedotti invece che enumerati; evaluator più veloce.~~ Chiuso da D-X1, Passo F. |
| R6 | Report e spiegazioni | `buffer = 0`, deployment omesso, `describe_conclusion` non usato, freshness non riportata: cosa mostrare. Reperti N19, N23. |
| R7 | UI risultati e privacy | Tabella campo per campo personal/public/strutturale, **quantità incluse**; tetti e minimi delle route (default mascherati); input in chiaro durante la scrittura. Voci nuove dello smoke: «1 units» senza plurale; L2 nella locale del browser (`format.ts:185`); titolo del contributo con etichetta vuota; testimone «9,018» contro «2212»; valori floating degli stage con tutte le cifre; numero di ordini in chiaro con privacy ON (da confermare). |
| R8 | Registro decisioni | E la prossima fetta (§4). |
| R9 | Toast di `ToolsHub` | Un `renderer_missing` atteso non merita un toast (`notify.svelte.ts:53-55`): correggerlo ora o metterlo in backlog. |

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
5. `score_lattice_closure`.
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
