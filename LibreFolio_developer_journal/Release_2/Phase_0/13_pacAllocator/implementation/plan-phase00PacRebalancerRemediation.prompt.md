# Piano di rimedio — PAC & Rebalancer

**Stato:** PIANO CONSEGNATO 2026-09-21 — nessun codice di prodotto scritto.
**Baseline verificata:** `09c6171bc` (il codice a quel commit è **identico** al
worktree `e-alfy-allocatore-pac`; `git diff HEAD 09c6171bc` tocca solo docs).
**Autorizzazione:** scrivere questo piano è autorizzato dal coordinator.
**L'implementazione no**: resta dietro il sign-off del developer.
**Tipo:** piano **trasversale**, non un settimo Step. Sta accanto al
[master implementativo](plan-phase00PacRebalancerImplementation.prompt.md).

> Questo documento non ridefinisce il prodotto. In caso di conflitto prevalgono
> i cinque design autorevoli e il lavoro si ferma per una decisione esplicita
> (`README.md` §Autorità, regola 6).

---

## 1. Perché esiste questo piano

Fra il 16 e il 19 settembre sono state consegnate ~9.100 righe di planner v2
(commit `9229085e9` e `c25c1e874`, poi `3913fe217` in `dev_release2`). Il
codice è testato — 907 test verdi — ma **tre cose non tornano**:

1. **Niente di quel lavoro è raggiungibile dall'applicazione.**
   `plan_pac_allocation` ha zero chiamanti di produzione; il Tool plugin
   registra solo l'operazione P1 `analyze`.
2. **I piani non riflettono ciò che è stato consegnato.** 23 caselle spuntate
   su 80 nei sette piani, e Step 3 è a 0/14 con sei Stage documentati sotto.
3. **Alcune promesse dei design autorevoli non sono coperte**: variante
   margine, margine prudenziale `g`, policy diverse da `proportional`,
   determinismo del solver.

Questo piano parte dalla verifica del punto in cui siamo e costruisce il
percorso per realizzare **pienamente** la suite `13_pacAllocator/`.

---

## 2. Verifica indipendente dello stato

Tutto ciò che segue è stato verificato **eseguendo** sul target, non dedotto.

### 2.1 Il collo di bottiglia è uno solo, ed è nominabile

Gli step 6/7/8/9 della sequenza §13 di Step 3 **non sono quattro buchi
sparsi**: condividono un unico punto di blocco.

Cosa **esiste** già:

- `models.py:264-278` — `PlannerPolicy` dichiara tutte e quattro le policy;
  `ExactPolicyPurpose` dichiara `primary`, `invest_only_baseline`,
  `sell_extension`, `deployment`.
- `models.py:771,775,777,1057,1064,1066` — validazioni coerenti già attive
  (`invest_and_sell` esige la baseline invest-only, `invest_only` rifiuta un
  `sell_context`, il purpose `primary` è incompatibile con `invest_and_sell`).
- `evaluator.py:1660` — ramo `min_fragmentation` reale.
- `evaluator.py:1647-1674` — l'evaluator valuta **tutte e nove** le
  `ExactObjectiveCode` e conosce **tutte e quattro** le cascate.

Cosa **non** esiste:

- `objectives.py` costruisce **una sola** cascata (`proportional`);
- `compiler._require_supported_scope` (`compiler.py:118-122`) è **una funzione
  con due condizioni** che rifiuta tutto il resto:

```python
def _require_supported_scope(scenario, view) -> None:
    if scenario.product != "pac" or scenario.policy != "proportional":
        raise PolicyProgramScopeError(...)
    if view.purpose != "primary":
        raise PolicyProgramScopeError(...)
```

**Contratti e validazioni esistono; la compilazione verso il solver no.**

**Corollario verificato eseguendo**: l'oracolo è agnostico rispetto alla
policy, quindi `min_fragmentation` è **già risolvibile provatamente oggi**:

```
POLICY: min_fragmentation
  view OK    | cascade = ['fixed_l2','shortfall','split_asset_count',
                          'active_order_rows','route_priority','explicit_cost']
  ORACLE OK  | domain=16 feasible=16 best=(3,3)
  COMPILER REFUSES: PolicyProgramScopeError
```

Il lavoro mancante non è «implementare la matematica» ma «costruire le cascate
SCIP e rimuovere il guard, una policy alla volta»: molto meno rischioso, perché
la semantica esatta esiste ed è già testata.

### 2.2 Stato reale dei 14 punti di §13

| # | Punto | Stato verificato |
|---|---|---|
| 1 | `ConstraintSpec` / `ObjectiveStage` | **fatto** (`constraints.py`, `objectives.py`) |
| 2 | variabili/bound comuni | **fatto** (`compiler.py`) |
| 3 | MIQP `L2_fixed` | **fatto** (`build_fixed_l2_stage`) |
| 4 | cascade MIQCP e tie | **fatto** (`build_objective_cascade`) |
| 5 | PAC `proportional` | **fatto** |
| 6 | PAC `min_fragmentation` | **non compilabile** — core fatto, oracolo lo prova, manca cascata SCIP |
| 7 | Rebalancer `invest_only` | **non compilabile** — purpose e validazioni presenti, manca cascata |
| 8 | estensione `invest_and_sell` | **non compilabile** — come sopra, più SELL verifier |
| 9 | variante BUY-only e promotion | **mancante** — stesso guard |
| 10 | proof mapping e lattice closure | **metà** — proof sì; `score_lattice_closure` **no** |
| 11 | SELL verifier | **mancante** |
| 12 | cancel/cleanup | **peggio di parziale** — vedi 2.3 |
| 13 | confronto oracle e benchmark | **metà** — gate oracolo permanente sì; **benchmark capacity no** |
| 14 | review matematica e lifecycle | **non fatto** |

### 2.3 Difetto di prima grandezza: il percorso solver non è riproducibile

`solver.py` effettua esattamente **due** `setParam`: `limits/nodes` (:280) e
`limits/time` (:360). Contro §11 di Step 3 («Adapter SCIP») mancano:

- `randomization/randomseedshift` → **nessun seed deterministico**;
- `lp/threads` / `parallel/maxnthreads` → **nessuna thread policy**;
- nessun cleanup esplicito in success/error/timeout/cancel (nessun `finally`,
  nessuna `free()`);
- nessun coefficient scaling.

**La cascata lessicografica e il tie-break canonico rendono deterministico il
report _dato un incumbent_, ma nulla garantisce che SCIP restituisca lo stesso
incumbent fra due esecuzioni.** Il percorso oracolo è deterministico per
costruzione; il percorso solver no.

Per uno strumento che produce numeri su cui un utente muove denaro, questo è un
difetto di prima grandezza: va in cima al percorso, non in fondo.

### 2.4 Margine prudenziale `g` — promesso e non implementato

`planner_report.py:569` scrive `buffer=_nonnegative_money(_EXACT_ZERO, …)`.
`buffer` ha **zero occorrenze** in
`constraints/objectives/solver/compiler/evaluator/models`: è un campo di
contratto costante, non una grandezza calcolata.

`UiTarget` lo mostra nello step 7 del wizard («spread, **buffer** e fee») e
`Policies §10` specifica la variante margine in dettaglio. Due promesse dei
design autorevoli, oggi scoperte.

### 2.5 Tracciabilità — il difetto è la forma, non l'assenza

Tre affermazioni, verificate separatamente:

**(a) I piani Stage _sono_ versionati.** I due file standalone di Stage 4 e
Stage 5 sono stati **ripiegati** nel piano Step 3 come §16.13 e §16.14 e sono
committati nel target (`git show 09c6171bc:…` → §16.10-§16.14 presenti). I file
standalone esistono solo in commit interni `copilot checkpoint`, che non
appartengono ad alcun branch.

**(b) La checklist §13 esiste ed è a zero.** Verbatim dal target:

```
## 13. Sequenza

- [ ] 1. Definire `ConstraintSpec` e `ObjectiveStage`.
...
- [ ] 14. Review matematica e resource lifecycle.
```

Conteggio: `- [ ]` → 14, `- [x]` → 0.

**(c) L'header sintetico è falso.** Riga 3 del piano Step 3:

```
**Stato:** ANALISI CONSEGNATA 2026-09-18 (nessun codice) — …
```

`(nessun codice)` è smentito dal documento stesso, che sotto elenca sei Stage
di codice consegnato.

> **Il difetto reale**: nello stesso documento convivono due tracciati che non
> si indicizzano a vicenda — la checklist §13 (14 voci, 0 spuntate) e la
> narrativa §16.8-§16.14 (sei Stage documentati e datati). Non manca il
> racconto: manca il **ponte**. E chi apre il file senza scorrerlo legge
> l'header, che dice l'opposto del corpo.

### 2.6 Il sotto-registro è sistemico: 23 caselle su 80

Misurato su tutti e sette i piani:

| Piano | Caselle | Header riga 3 |
|---|---|---|
| Step 1 Contracts/Capacity | 6/10 | `IN PROGRESS — G2/G4 COMPLETE…` |
| Step 1 Round1 ToolPlatform | 6/6 | `FROZEN — backend handoff pronto` |
| Step 2 ExactCore | 6/13 | `IN PROGRESS — W1 CHECKPOINT…` |
| **Step 3 SolverPolicies** | **0/14** | **`ANALISI CONSEGNATA (nessun codice)`** ← falso |
| Step 4 DomainCopies | 5/10 | `IN PROGRESS — OWNERSHIP FROZEN…` |
| Step 5 FrontendReview | 0/13 | `PENDING CONTRACT…` |
| Step 6 Integration | 0/14 | `PENDING SOLVER…` |

Due disallineamenti specifici già identificati:

- **`oracle.py` appartiene a Step 2** (compare nella sua lista file, riga 35) ma
  è stato costruito in Step 3 Stage 1: il record §16.8 è nel piano sbagliato.
  Anche i punti 2.2/2.4/2.5/2.6 risultano consegnati (`numeric.py`, `ledger.py`).
- **Step 4 punto 6 è fatto**: `test_portfolio_allocation_source.py` esiste, 35
  test, selector `portfolio-allocation-source` registrato — ma la casella è
  vuota e riporta «⏳ test-author».

Step 5 (0/13) e Step 6 (0/14) sono invece **genuinamente** non fatti.

### 2.7 `monetary_step` — verificato, e il perimetro è diverso da come è posto

**`monetary_step` non esiste nel contratto v2.**

```
monetary_step in v2 PLAN contract   : False
monetary_step in P1 ANALYZE contract: True
```

Vive in `AllocationContributionInput` (`schemas/pac_allocator.py:112`) e
`NormalizedContribution` (:406), **entrambi P1**. Zero occorrenze in
`constraints/objectives/solver/compiler/evaluator/planner_report`; in
`models.py:87` viene perfino **scartato** nell'unpack
(`for currency, amount, _monetary_step in self.entries`). Le uniche superfici
UI che lo usano appartengono al prototipo Round 4 (`d66f8e58e`).

**Risposta alla domanda posta** — «se la rimozione cambia un risultato
calcolato, fermati»: **non cambia alcun risultato calcolato**, né in v2 (dove è
assente) né in P1 (dove la matematica non lo legge mai). **Ma cambia una
validazione**: `contribution_not_multiple_of_monetary_step`
(`normalize.py:486`) oggi rifiuta contributi non multipli dello step dichiarato;
derivando lo step da Babel, quella regola cambia riferimento. Non è un calcolo,
è un contratto di accettazione: va detto, non nascosto.

**Osservazione di prodotto** (decisione non nostra, vedi §5): il campo è
**editabile dall'utente** — label «Amount increment», hint «Smallest accepted
increment for this contribution, for example 0.01 for cents». L'hint descrive
esattamente la minor unit, quindi la derivazione Babel **coincide con l'intento
documentato**; ma per un utente che lo usasse come passo più grossolano (es.
incrementi da €50) è una **rimozione di capacità**, non un refactoring. Babel è
già dipendenza (`Pipfile:38`): EUR/USD → 0.01, JPY → 1, BHD → 0.001.

**Conseguenza di sequenziamento**: essendo P1-only, `monetary_step` **muore da
solo** quando si cancella il servizio P1 PAC. Rimuoverlo prima è lavoro
indipendente che ha senso solo se P1 PAC sopravvive a lungo.

---

## 3. Il Rebalancer nell'intervallo — proposta

`analyze_rebalancing` alimenta il `ToolService` `portfolio_rebalancer`
(`tool_plugins/pac_allocator.py`), reso da `PortfolioRebalancerTool.svelte`.

Il punto che scioglie il dilemma: **P1 e v2 non fanno la stessa cosa.** P1
restituisce scostamenti corrente/target e, per sua docstring, «never buy or sell
instructions»; v2 restituirebbe ordini eseguibili. Non è un rimpiazzo
like-for-like: è un'altra funzione.

**Proposta: cancellazione per-tool, non in blocco.** Il plugin passa da 2
servizi → 1 → 0:

1. **PAC v2 cablato** ⇒ cancellare **solo** il `ToolService` P1 `pac_allocator`,
   e con esso `monetary_step`, `PacMoneySection.svelte` e il renderer PAC.
2. **Rebalancer resta su P1** per tutto l'intervallo, dichiarato tool di
   *analisi* e non di *pianificazione*.
3. **Rebalancer v2 cablato** (dopo gli step 7-8-11) ⇒ cancellare il secondo
   servizio e l'intero `analyze_*`.

Motivazione: togliere il Rebalancer dal catalogo nell'intervallo rimuove una
capacità che oggi esiste, in cambio di nulla; tenerlo su P1 non viola il master
§1.2, che dichiara non-obiettivo la **compatibilità** col prototipo, non la sua
sopravvivenza temporanea.

> Questa è una **proposta**, non una decisione presa: vedi §5 punto 3.

---

## 4. Fasi e gate

Ordinate dal più sicuro al più rischioso. Nessuna fase parte senza il gate
della precedente. Ogni gate dice **cosa è verificabile e come**.

### Fase 0 — Riallineamento della tracciabilità (zero codice di prodotto)

**Primo atto, una riga**: correggere l'header `**Stato:**` del piano Step 3.

Poi:

- costruire il **ponte §13 ↔ §16**: spuntare i punti 1, 2, 3, 4, 5, 10
  (parziale), 13 (parziale) con l'evidenza richiesta dal `README.md` regola 2
  (comando, selector, pass count, data);
- spostare il record di `oracle.py` da Step 3 §16.8 a Step 2 punto 9;
- spuntare Step 4 punto 6 con l'evidenza esistente;
- riconciliare **anche** Step 1 e Step 2, non solo Step 3;
- registrare nei piani i debiti del dossier (DBT-1…DBT-7) e i difetti §2.3 e
  §2.4 di questo documento.

**Estensione (richiesta dal coordinator)**: verificare **header e checklist di
tutti e sette i piani**. Il difetto «narrativa giusta / indicatore sintetico
falso» è già comparso **due volte su due workstream diversi**: è un modo di
sbagliare, non un caso isolato.

*Gate*: ogni spunta è riverificata dal coordinator contro un comando eseguito, e
nessun header contraddice il corpo del proprio documento.

### Fase 1 — Determinismo e lifecycle del solver (§13 punto 12, parte del 14)

Seed fisso, thread policy esplicita, cleanup in success/error/timeout/cancel,
coefficient scaling sicuro.

**Rinforzo dal dossier piattaforma** (§2.7.3 trappola 4), che conferma dal lato
opposto ciò che questo workstream aveva già misurato: *«se il motore è una
libreria nativa che non torna al Python per decine di secondi,
`context.checkpoint()` non verrà mai chiamato e il budget soft non avrà
effetto: resterà solo il kill duro a 45 s, che è un **errore di piattaforma**,
non una terminazione ordinata e **non** un'infattibilità finanziaria»*.

SCIP è esattamente quel motore. Conseguenze operative:

- il limite di tempo va impostato **dentro SCIP** (`limits/time`), non affidato
  al soft budget della piattaforma — cosa che `solver.py` già fa, ed è quindi
  una scelta giusta che ora ha una motivazione scritta anche dall'altro lato;
- `engine_timeout_ms` della policy e il `limits/time` di SCIP devono essere
  **lo stesso numero**, altrimenti uno dei due è decorativo;
- un superamento non deve mai presentarsi all'utente come «nessun piano
  possibile»: è un limite di risorsa, non un'infattibilità.

*Gate*: stesso input → risultato **identico** su N esecuzioni ripetute, provato
da un test che **fallisce se si rimuove il seed** (mutation-checked, secondo la
regola già adottata in questo workstream: un test di regressione che non può
fallire è decorazione). In più: un superamento di budget produce un esito di
**limite**, mai un risultato vuoto travestito da risposta.

### Fase 2 — Campagna capacity G5 (metà mancante del §13 punto 13)

Campionamento su 7 assi: Asset canonici, route/Asset e totali, Broker, valute e
casse, route FX, buy-only vs invest-and-sell, densità fee/limiti/attivazioni.

*Gate*: numeri **misurati**, non estrapolati. È l'input obbligatorio
dell'envelope timeout: senza questa fase, la Fase 5 non può partire onestamente.
Oggi l'unica misura esistente è su fixture giocattolo (3-8 ms) ed è priva di
valore predittivo.

### Fase 3 — Sbloccare il compilatore: `min_fragmentation` (§13 punto 6)

Cascata `split_asset_count` in `objectives.py`; rilassare
`_require_supported_scope` **in modo mirato**.

> **Vincolo non negoziabile**: una policy alla volta, mai un guard permissivo.
> Oggi quel guard è l'unica barriera che impedisce di compilare in silenzio un
> modello sbagliato per una policy la cui cascata SCIP non esiste ancora.
> Rimuoverlo in blocco trasformerebbe un rifiuto rumoroso in un risultato
> plausibile e falso.

*Gate*: oracle-agreement su fixture `min_fragmentation` (stesse quanta e stessa
chiave lessicografica dell'ottimo esaustivo) + nessuna regressione sulle 907.

### Fase 4 — Variante margine e margine prudenziale `g` (§13 punto 9, §8)

Freeze hard di funding, trasferimenti, FX, SELL, BUY primari e attivazioni;
solo BUY addizionali finanziabili dai saldi risultanti. Pipeline:

```
min U → min L2_fixed risultante → min incremental cost
      → min incremental rows → canonical tie
```

`buffer` smette di essere costante zero. I delta `L2_fixed` sono sempre visibili
nel report.

*Gate*: **promotion provata** — se la variante domina il `L2_fixed` di un
primario non provato, diventa incumbent primaria e la cascata riparte; mai
etichettata come semplice variante di una base dominata.

### Fase 5 — Cablaggio `operation="plan"` per PAC + cancellazione P1 PAC

> **Sequenziamento contestato**: il developer ha chiesto di cablare **prima**
> delle prove. Questa fase è scritta come «dopo la Fase 2», ma la decisione è
> aperta e documentata in **§5 punto 7**, con controproposta e raccomandazione.

`ToolService` + `ToolOperationPolicy` con envelope **derivato dalla Fase 2**.
Cancellazione del servizio P1 PAC, di `monetary_step` da API e UI, e delle
chiavi i18n nelle 4 lingue via `dev.py i18n`.

**Vincoli di piattaforma da rispettare** — non deducibili dal codice PAC, presi
da [`16_toolPlatform/dossier-piattaforma-tool.md`](../../16_toolPlatform/dossier-piattaforma-tool.md)
§2.7, letto e verificato. Quel dossier è l'unico residuo di una sessione
archiviata: va trattato come fonte, non come promemoria.

1. **Una policy d'operazione invalida spegne l'intero tool, non l'operazione**
   (§2.7.3 trappola 1). `effective_descriptor` valuta **tutte** le operazioni di
   un descrittore in una sola comprehension: un `plan` mal dimensionato su
   `pac_allocator` **fa sparire anche il suo `analyze`**. La quarantena del
   registro isola i **servizi** fratelli; la validazione delle policy **non**
   isola le **operazioni** sorelle.
   → **Conferma per la §3**: `pac_allocator` e `portfolio_rebalancer` sono due
   `ToolService` **distinti** (`tool_plugins/pac_allocator.py:49,70`), quindi il
   Rebalancer su P1 **è protetto** anche se la policy `plan` di PAC è mal
   dimensionata. La proposta di cancellazione per-tool regge, e ora si sa perché.
2. **I numeri si derivano, non si indovinano** (§2.7.2). Una sola decisione di
   prodotto — `engine_timeout_ms`, il budget del solver — e tutto il resto
   discende da identità imposte dai validatori:
   `soft ≥ engine + riserva` · `hard = soft + output_reserve` ·
   `request ≥ 9 000 + hard` · `client > request`.
   A budget pieno (`engine` 30 000) l'envelope risultante è
   `44 000 / 45 000 / 5 000 / 5 000 / 59 000 / 65 000`, e **`server_bound` vale
   esattamente 59 000 contro un `request` di 59 000**: margine zero. Non si alza
   `queue`, `cleanup` o `job` di un millisecondo senza far fallire la
   validazione; se serve più cleanup, va tolto al job.
3. **La larghezza del batch è limitata dai worker** (§2.7.3 trappola 2).
   `admitted_at` è calcolato **una volta per batch** (`executor.py:474`) e la
   scadenza di coda è ancorata a quello (`executor.py:401`), mai rinnovata per
   ondata. Con 2 corsie e un job da 45 s, **gli item dal terzo in poi muoiono di
   `queue_timeout` a 5 s**. Non è un timeout da alzare — la trappola 1 lo
   impedisce comunque a budget pieno — è un'aritmetica da rispettare: **al più
   `workers` item di un'operazione lunga per batch**.
4. **Dispatch su `tool_code` *e* `parameters.operation`** (§2.7.1 punto 3): mai
   dedurre l'operazione dalla forma dei parametri.
5. **`implementation_version` sale sempre**; `contract_version` sale se cambiano
   gli schemi pubblicati — e sale **anche per i servizi fratelli** della stessa
   classe (§3.4e). Cioè toccare PAC tocca la versione dichiarata del Rebalancer.

*Gate*: PAC v2 raggiungibile dall'applicazione; **il tool compare ancora nel
catalogo** dopo l'aggiunta (trappola 1); un batch di ampiezza `workers` riesce e
uno più largo fallisce **pulito** con `queue_timeout` (trappola 2); un
superamento di budget produce `execution_timeout`/`execution_limit` e **mai** un
risultato a zero; `check-orphans` verde; nessuna chiave i18n orfana; **il
Rebalancer resta funzionante su P1**.

### Fase 6 — Rebalancer `invest_only` (§13 punto 7)

> **Gate d'ingresso obbligatorio**: costruire una fixture v2 rebalancer
> **valida**. Quella esistente
> (`fixtures/pac_allocator/rebalancer_plan_request.medium.v2.json`) è
> deliberatamente **invalida** — normalizza con 4 issue
> (`broker_inactive`, `economic_share_out_of_range`, `currency_mismatch`,
> `tax_rate_out_of_range`) perché è una fixture di rilevamento errori.
> Finché view + oracolo non risolvono una fixture valida, **non si scrive la
> cascata SCIP**: si starebbe compilando contro un input che nessuno ha mai
> visto funzionare.

*Gate*: oracle-agreement su `invest_only`.

### Fase 7 — `invest_and_sell` e SELL verifier (§13 punti 8 e 11)

La fase più rischiosa: tocca inventario, cost basis, tasse e irreducibilità.

*Gate*: verifier che dimostra l'irreducibilità del SELL; counterfactual; nessuna
vendita oltre l'inventario; nessun buy+sell sullo stesso titolo per gonfiare
l'obiettivo.

### Fase 8 — `score_lattice_closure` (resto del §13 punto 10)

Solo dopo che solver e oracolo sono incrociati su un corpus ampio.

*Gate*: witness di chiusura accettato dal proof layer **senza** allentare
l'irrappresentabilità già garantita (nessuna scorciatoia che permetta a uno
status floating di promuoversi).

### Fase 9 — Rebalancer v2 cablato e P1 eliminato del tutto

*Gate*: catalogo Tool senza più alcun servizio P1; `analyze_*` rimosso.

### Fase 10 — Step 5 (frontend v2 e doppia review umana) e Step 6 (integrazione, E2E, docs)

*Gate*: doppio `APPROVED` umano prima degli E2E completi, come da `README.md`
regola 4.

---

## 5. Decisioni che non sono nostre

Raccolte qui perché il developer possa rispondere in blocco.

1. **Envelope timeout della `ToolOperationPolicy`** per `operation="plan"` —
   lease del coordinator; richiede i numeri della Fase 2. Non va indovinato.
2. **`monetary_step`**: rimozione anticipata (lavoro indipendente) oppure
   assorbita dalla cancellazione del servizio P1 PAC (gratis)? E: si accetta la
   perdita di capacità per chi lo usava come passo più grossolano della minor
   unit di valuta?
3. **Destino del Rebalancer nell'intervallo** — la proposta §3 è «resta su P1»,
   ma è una scelta di prodotto.
4. **`min_fragmentation` può uscire solo per via oracolo?** Domini piccoli
   risolti provatamente, `not_proven` oltre il cap, prima che la cascata SCIP
   esista. È onesto, ma è una promessa di prodotto asimmetrica.
5. **DBT-5** (`stop_reason="time_limit"` non veritiero sul percorso solver
   infeasible): richiede un cambio al contratto congelato oppure una nota UI
   permanente che vieti di mostrare «time limit» all'utente su quel percorso.
6. **Ordine fra Fase 4 e Fase 6**: la variante margine è promessa dalla UI
   target; il Rebalancer è un tool già visibile nel catalogo. È una priorità di
   prodotto.

7. **Quando cablare `operation="plan"`** — la decisione più importante di questa
   sezione, perché il piano come scritto **contraddice un'istruzione esplicita
   del developer**.

   Il developer ha detto: *«possiamo cancellare il vecchio p1 che non era manco
   ben testato e non funzionava e collegarlo **prima di metterci a fare le
   prove**»*. Questo piano mette il cablaggio in **Fase 5**, a valle di
   determinismo, capacity, `min_fragmentation` e variante margine. La ragione
   tecnica è reale — l'envelope si deriva dai numeri della Fase 2 — ma il
   risultato è che **non si vede nulla di v2 nell'applicazione finché non sono
   chiuse quattro fasi**, una delle quali è una campagna di misura.

   **Controproposta: spezzare la Fase 5.**

   - **5a — cablaggio anticipato**, subito dopo la Fase 1: **solo
     `proportional`**, envelope **provvisorio e generoso**, marcato come tale
     nel codice e nel piano, con la nota che va rivisto. PAC v2 diventa
     raggiungibile e provabile a mano. La cancellazione di P1 PAC può stare
     qui o in 5b: è parte della stessa decisione.
   - **5b — raffinamento dell'envelope** con i numeri misurati della Fase 2.

   **Il contro, che è serio e va detto**: la **Fase 1 resta prerequisito non
   negoziabile**. Cablare un solver che può restituire incumbent diversi fra due
   esecuzioni significa mostrare a un utente numeri che cambiano da soli su cui
   muove denaro. Quello non si anticipa, in nessuna forma. Ma
   `min_fragmentation` e variante margine **non** sono prerequisiti del
   cablaggio della sola `proportional`: presentarli come tali allunga la catena
   oltre ciò che la fisica richiede.

   **Raccomandazione: 5a/5b, cioè cablare dopo la Fase 1.** Tre ragioni.

   1. **La Fase 2 non è un prerequisito di correttezza, è di dimensionamento.**
      Un envelope provvisorio e generoso non produce risultati sbagliati: al
      peggio consuma più budget del necessario, e la trappola 1 del dossier
      garantisce che uno sbaglio si manifesti in modo **rumoroso** — il tool
      sparisce dal catalogo — non silenzioso. È il tipo di errore che si vede
      subito.
   2. **Il contatto con l'app anticipa scoperte che la misura non produce.**
      Questo workstream ha collezionato sei difetti invisibili ai gate statici e
      trovati solo eseguendo; l'ultimo — il crash su input infeasible — è emerso
      alla **prima esecuzione end-to-end vera**. Il cablaggio è il prossimo
      «prima esecuzione vera» disponibile, e rimandarlo di quattro fasi rimanda
      anche quella classe di scoperte.
   3. **La campagna G5 si progetta meglio con il percorso reale acceso.** La
      Fase 2 deve campionare scenari rappresentativi: averli osservabili
      attraverso l'applicazione, invece che solo da fixture, rende il
      campionamento più fedele.

   **Condizione che rende la raccomandazione accettabile**: 5a va spedita con
   l'envelope marcato provvisorio **nel codice**, non solo nel piano — un
   commento che dica *da rivedere dopo G5, non misurato a scala
   rappresentativa* — altrimenti il provvisorio diventa definitivo per inerzia,
   che è esattamente il meccanismo per cui `buffer` è ancora una costante zero.

---

## 6. Note operative

- **Server di review 6152** (PID 66314) acceso e rappresentativo del target: il
  codice a `09c6171bc` è identico al worktree, differiscono solo le docs. È
  l'unico modo di rivedere l'applicazione merged. Da non fermare finché il
  developer non chiude la review.
- Pianificato contro `09c6171bc`; l'allineamento del worktree è del
  coordinator, prima di qualunque implementazione.
- Nessun commit, merge, rebase, push o staging in questa assegnazione.
- Nessun file di prodotto è stato modificato per scrivere questo piano.

---

## 7. Definition of Done del rimedio

1. I sette piani riflettono ciò che è stato consegnato: header veri, checklist
   riconciliate, evidenza per ogni spunta.
2. Il percorso solver è riproducibile e il determinismo è provato da un test
   che fallisce se la garanzia viene rimossa.
3. L'envelope timeout è derivato da numeri misurati a scala rappresentativa.
4. Tutte e quattro le policy sono compilabili, ciascuna sbloccata singolarmente
   e coperta da oracle-agreement.
5. La variante margine esiste e `buffer` non è più una costante zero.
6. `operation="plan"` è raggiungibile dall'applicazione per PAC e Rebalancer, e
   nessun servizio P1 sopravvive.
7. Doppia review umana `APPROVED` su PAC e Rebalancer, E2E chiusi, docs e i18n
   allineati.

→ Torna a [README del bundle](README.md) ·
[Master implementativo](plan-phase00PacRebalancerImplementation.prompt.md) ·
[Step 3 — Solver e policy](plan-phase00Step3PacRebalancerSolverPolicies.prompt.md)
