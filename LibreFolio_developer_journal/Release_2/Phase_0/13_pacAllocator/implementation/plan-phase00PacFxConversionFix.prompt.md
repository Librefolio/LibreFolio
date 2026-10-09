# Piano D — Conversioni FX del PAC: residuo esatto e cambi incrociati coerenti

**Stato:** 🔄 iniziato il 2026-10-08 alle 22:45; CHECKPOINT READY il 2026-10-09 alle 01:25. S9 (pagina
utente e record dei commit), chiesto dal coordinator alle 01:26, chiuso alle 02:01; FROZEN in attesa
degli SHA. Il via è del developer, inoltrato dal coordinator alle
22:17 (A + 2A e le 3 raccomandazioni). Il coordinator ha confermato il fast-forward e ha scritto «Puoi
scrivere».
**Baseline:** `4d09ac2ac` su `e-alfy-allocatore-pac`, cioè il treno 19 di `dev_release2` in
fast-forward. Il codice del PAC è identico a `70d02cd8e`, su cui è stata fatta l'analisi. Verificata
alle 22:38: albero pulito, stage vuoto, porta 6151 libera. Carico 20.33 / 20.85 / 22.78.
**Posizione:** `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacFxConversionFix.prompt.md`.
Il coordinator aveva scritto `13_pacAllocator/plan-…`, ma i piani d'esecuzione stanno in
`implementation/`, come quello della riga 13.
← Precedente: [`plan-phase00PacP1FinalRemoval.prompt.md`](plan-phase00PacP1FinalRemoval.prompt.md)
(riga 13 del README, con R7).
→ Seguente: analisi del Rebalancer (riga 14), nel backlog. Non parte senza il via del coordinator.
**Corsia:** suite `6151` + `/tmp/librefolio-r2-d`, un comando per volta. Prefisso:
`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6151 --data-dir /tmp/librefolio-r2-d …`.
- Niente E2E prima delle 23: sulla 6150 girano i gate del treno 19 e la gallery di M.
- `db populate` solo con una nuova concessione.
- Nessun server di review.
- Accanto a ogni tempo annoto il carico della macchina.

Le righe citate sono misurate alla baseline. Se il codice cambia, prevale il codice.

---

## 0. Perché

M, preparando gli scatti della gallery, ha trovato il difetto: il risultato del PAC mostra
«Calculation failed» (`tool_error`) appena una fonte di finanziamento, per esempio un conto esterno,
è in una valuta diversa da quella dello scenario. Nel frattempo M ha messo in EUR il conto esterno
della gallery (`galleryPac.ts`, `PAC_SCENARIO.externalAccount`). Dopo questa correzione torna a USD.

Il developer, il 2026-10-08, sull'analisi di D (inoltro del coordinator delle 22:17):

> su A + 2A: «si a tutto, solo una cosa non mi torna, se l'inverso è un numero periodico, arrotondare
> alla prima untà valida per quella valuta, in eccesso o difetto, non credo sia corretto dire che non è
> più l'ottimo, al massimo possiamo dire "ottimo arrotondato" se proprio serve distinguerlo, ma non ne
> sono così sicuro»
>
> sulle 3 raccomandazioni: «ok per le 3 raccomandazioni, riguardo al non autorevole intendevi il
> simbolo del circa al posto dell'uguale?»

Le decisioni del coordinator, nello stesso inoltro:
- **A + 2A**.
- `contract_version` resta `1.0.0`.
- Il messaggio di `allocation.fx_rate_inconsistent` contiene solo valute e coppia.
- `_log_engine_failure` registra 2–3 frame propri, senza il messaggio, in un commit piccolo a parte.
- Le 4 voci di `…fx_rate_inconsistent` nei cataloghi sono mie fino al checkpoint, e solo tramite
  `dev.py i18n add`.
- CHANGELOG: il tool non è mai uscito, quindi niente «Fixed»; al più una precisazione nella voce del
  PAC. Le righe le propongo io, il file lo scrive il coordinator.

Il coordinator ha chiarito il dubbio del developer. Questo lavoro deve garantire tre cose:
- **G1.** Il piano resta `optimal_proven`. L'unico arrotondamento economico è quello di oggi,
  `post_half_up` alla minor unit. Nessun testo dice «non ottimo». Il rosso R1 asserisce lo stato di
  ottimalità.
- **G2.** «Non autorevole» vale solo per il formato del residuo. In pagina diventa il «≈» che il
  formatter già usa (`exactMoneyDisplay` → `approx`), al posto di «=».
- **G3.** Mai «≈ −0.00» per un residuo sotto il centesimo. Vale la stessa regola scelta per il
  rischio (F2): precisione adattiva. Il residuo si mostra con le cifre che servono, per esempio
  «≈ −0.0022 EUR», e «0.00» solo per uno zero vero. Questo va nei rossi del formatter.

**Perché G1 regge.**
- Il modello accredita già oggi l'importo arrotondato alla minor unit: è quello che un broker
  registra. La prova di ottimalità riguarda proprio questo modello, arrotondamento compreso.
- `rounding_delta` è la differenza fra l'importo registrato e quello esatto. È una riga contabile, non
  uno scarto dall'ottimo.
- La correzione A non tocca né il calcolo né la prova. Cambia solo il modo in cui quella differenza
  viene pubblicata: oggi non si può pubblicare e il calcolo cade; domani si pubblica esatta.
- Per questo non serve un «ottimo arrotondato»: l'ottimo è già calcolato sugli importi arrotondati.

## 1. Il problema

### 1.1 Caso 1: conversione nel verso inverso della coppia salvata (correzione A)

La catena:
1. La coppia `"A/B"` con `A < B` salva quanti B vale 1 A. Il verso B→A usa `1/r`
   (`normalize.py:621`, `evaluator.py:196-206`; la riga `:206` è
   `rate if source < destination else _EXACT_ONE / rate`).
2. Con `r = 1.085`, `1/r = 200/217`. Il credito esatto è un decimale periodico.
3. `post_half_up` (`numeric.py:233-254`) arrotonda il credito al centesimo. Alla riga `:252` salva
   `rounding_delta = posted − exact`, che quindi è periodico anche lui.
4. `build_ledger_rows` (`planner_report.py:667`) lo pubblica con `ratio_to_fixed_decimal`. Questa
   funzione solleva `WireNumberTooLargeError` (`wire_numbers.py:142`): un periodico non si scrive come
   decimale fisso.

Riproduzione di servizio, alla baseline, su dati sintetici (log di sessione `05_repro.log`):

| Caso | Fonte → Asset | Coppia, spread | Esito |
|---|---|---|---|
| C1a2 | USD → EUR 10.01 | `EUR/USD` 1.085, s 0 | ❌ `WireNumberTooLargeError: -47/21700` |
| C1b | USD → EUR 10.00 | 1.085, s 0.01 | ❌ `-18/5425` |
| C1d | USD → EUR + USD | 1.085, s 0 | ❌ `-47/21700` |
| C3 | USD → CHF (incrocio coerente) | 3 coppie, s 0 | ❌ `2/287525` |
| C1a | USD → EUR 10.00 | 1.085, s 0 | ✅ (il credito esatto termina per caso) |
| C1c | USD → EUR | 1.25, s 0.01 | ✅ (`1/1.25 = 0.8` termina) |
| CTRL | EUR → USD (verso diretto) | 1.085, s 0 | ✅ `optimal_proven` |

Prova della correzione (`07_whatif_a.log`): pubblicando il residuo come `ExactNumber`, C1a2, C1b,
C1d e C3 diventano `ready_incumbent` + `optimal_proven`. L'unico punto che cambia è
`planner_report.py:667`.

### 1.2 Caso 2: cambi incrociati incoerenti (correzione 2A)

La catena:
1. `ExactFxEvaluation.__post_init__` (`models.py:1000-1016`) controlla `spread_loss` con
   `_require_nonnegative` (`models.py:127-129`) e solleva `ValueError: spread_loss must be nonnegative`.
2. `spread_loss` è calcolato in `evaluator.py:1799-1803`. Nella valuta di valutazione V vale
   `debit · [v(c) − r(c→q)·(1−s)·v(q)]`, dove:
   - c è la valuta di partenza e q quella d'arrivo;
   - v(x) è il tasso x→V;
   - s è lo spread.
3. Se c = V o q = V, l'espressione si riduce a `debit·s` (o `debit·v(c)·s`), che è ≥ 0: la mappa a
   coppie inverte lo stesso tasso in modo esatto. Può diventare negativa **solo un incrocio** (c ≠ V e
   q ≠ V), quando
   `r(c→q)·(1−s)·r(q→V) > r(c→V)`: convertire passando per la coppia diretta crea valore rispetto al
   passaggio per V.

Riproduzione (`05_repro.log` e `08_whatif_2a.log`). Con s = 0, CHF/EUR 1.06 e EUR/USD 1.085,
l'incrocio implicito è CHF/USD = 1.1501.

| Caso | CHF/USD | s | Esito | Predicato |
|---|---|---|---|---|
| C2b, C2e | 1.16 | 0 | ❌ `spread_loss must be nonnegative` | incoerente |
| C2b2 | 1.1502 | 0 | ❌ | incoerente |
| C3b | 1.14, verso USD→CHF | 0 | ❌ | incoerente |
| C2c | 1.1501 | 0 | ✅ | coerente |
| C2d | 1.14, verso CHF→USD | 0 | ✅ | coerente |
| C2f | 1.16 | 0.01 | ✅ | coerente: lo spread assorbe lo 0.86% |

Il predicato coincide con l'esito del planner in ogni caso: ogni crash ha il predicato vero, ogni
caso verde ce l'ha falso.

### 1.3 Perché succede con i dati veri

- La copia dei cambi (`_load_latest_planner_fx_rows`, `portfolio_allocation_source.py:892`) prende
  l'ultimo tasso di ogni coppia. Le coppie possono avere date e fonti diverse, quindi un triangolo può
  non tornare per qualche decimillesimo.
- Lo spread di default è 0 (`defaults.ts:13` `DEFAULT_FX_SPREAD_PERCENT = '0'`, usato da
  `draft.svelte.ts:267` e `request.ts:456`). Basta quindi un incrocio più alto anche di 10⁻⁴.

### 1.4 Un'affermazione del dossier da correggere

`review/PAC_ALLOCATOR_REVIEW_DOSSIER.md:60-66` (Fork 2) dice che la mappa canonica a coppie rende
l'arbitraggio «structurally impossible». È vero per i cicli **fra due valute**: un solo tasso per
coppia, invertito in modo esatto. Non è vero per i **triangoli fra tre valute**, che possono restare
incoerenti. La stessa idea si legge in:
- `drafts/pac-rebalancer-end-to-end-design.md:720-726`;
- `plan-phase00PacRebalancerMathematicalCore.prompt.md:559`;
- `implementation/plan-phase00Step2PacRebalancerExactCore.prompt.md:657-661`.

Si corregge solo il dossier, con una nota datata: è un documento di review vivo. I piani archiviati
restano come sono, perché sono storia; il rimando sta qui.

## 2. Decisioni di progetto

### 2.1 Correzione A: `rounding_delta` esatto

- `schemas/pac_allocator.py:1436`: `PlannerLedgerRow.rounding_delta` passa da
  `PlannerFixedDecimal` a `ExactNumber` (`:697`). La descrizione del campo resta.
  - `validate_ledger_identity` (`:1439-1476`) non usa `rounding_delta`: resta invariato.
  - `accounting.rounding_delta` (`:1552`) è già `ExactMoney`.
- `planner_report.py:667`: `ratio_to_exact_number(ledger.raw_rounding_delta)`.
  - Vanno corrette le docstring di `planner_report.py:639-650` e `wire_numbers.py:132-138`, che oggi
    dicono che ogni cifra del ledger termina.
- `_validate_no_op_common` (`:1760-1783`): `"rounding_delta"` esce da `flow_fields` (`:1767-1779`),
  che si leggono con `_fixed_fraction`, e si controlla a parte con
  `_exact_fraction(row.rounding_delta) != 0` (`:706`).
- `ratio_to_exact_number` ripiega su `exact_ratio`. Il `display_decimal` è HALF_UP, al massimo 18
  cifre, con `display_authority="non_authoritative"`. Il tetto di 192 caratteri sugli interi non è un
  problema: lo ha verificato il what-if.
- Un residuo che termina esce `{"kind": "finite_decimal", "value": …}`, uno periodico `exact_ratio`.
  **Il tipo del campo cambia per ogni riga**, non solo dove prima il calcolo cadeva: da stringa
  semplice a oggetto `ExactNumber`. Per questo cambiano fixture, letterali dei test e impronte, e il
  frontend non può più passare `row.rounding_delta` a `decimalSign` (oggi solleva su un oggetto: §2.4).
  - Letterali dei test da allineare, in S2: la riga dell'incumbent (`test_pac_planner_schemas.py:291`,
    `"rounding_delta": "0"`) e il ciclo del no-op del Rebalancer (`:360-374`), che mette a `"0"` i
    campi di flusso, residuo compreso.
  - Fixture di risultato: `pac_plan_result.min.v2.json:352`,
    `rebalancer_plan_result.medium.v2.json:1126,1144,1162`, `pac_plan_result.candidate-max.v2.json:129-132`,
    tutte a `{"kind": "finite_decimal", "value": "0"}`.
- **Versioni.**
  - `contract_version` e `implementation_version` restano `1.0.0`, per decisione del coordinator.
    Il tool non è mai uscito, come per le righe 11 e 12.
  - Cambiano le due impronte dello schema, perché `PlannerLedgerRow` è condiviso:
    - PAC `4f061103f96ac9f4…`, `test_pac_planner_schemas.py:3765`;
    - Rebalancer `be2bb19d144e07fb…`, `:3771`.
    Le aggiorno con il motivo scritto accanto.

### 2.2 Correzione 2A: coerenza dei cambi incrociati

Nuovo `validate_fx_coherence()` in `normalize.py`. Si chiama in `run()` subito dopo
`validate_fx_pair_closure()` (`:1135`). Scorre esattamente le conversioni che la chiusura ha richiesto
(`:649-660`):
- per ogni rotta **BUY** con un Asset quotato in q;
- per ogni valuta c ≠ q delle casse del suo broker, presa da `_cash_pool_currencies_by_broker()`
  (`:635-647`). Questa comprende cassa esistente, rotte di finanziamento e incassi delle rotte SELL.

Un controllo si salta quando:
- c = V oppure q = V: è sempre coerente (§1.2);
- `fx_rate()` (`:611-624`) restituisce `None` per (c, q), (c, V) o (q, V). In quel caso la coppia
  manca (`fx_rate_missing`) oppure il tasso non è positivo (`nonpositive_fx_rate`), e quel problema è
  già segnalato;
- lo spread non è in [0, 1). È già segnalato a `:603-605`; lo leggo con
  `ExactRatio.from_decimal(Decimal(…))` e `_rate_in_half_open_unit_interval`, senza riaggiungere
  issue.

**Violazione** se e solo se `fx_rate(c,q)·(1−s)·fx_rate(q,V) > fx_rate(c,V)`. L'uguaglianza è
ammessa.

Issue:
- codice `allocation.fx_rate_inconsistent`, tipo `invalid`;
- path `field_path("fx", "fx_rate", pair, "rate")`, con `pair = _fx_pair_key(c, q)`: lo stesso
  path di `fx_rate_missing`;
- parametri: solo valute e coppia, come deciso dal coordinator. `canonicalize` li ordina per nome:
  - `IdIssueParam(name="pair")`: `PlannerId` accetta «/», regex `_PLANNER_ID` `:50`;
  - `CurrencyIssueParam` per `source_currency`, `destination_currency` e `valuation_currency`.
- Una sola issue per coppia: un insieme `reported_fx_rate_inconsistent`, accanto a
  `reported_fx_rate_missing` (`:136`).

Vale per PAC e Rebalancer: il normalizer è lo stesso.

Registrazione del codice:
- il codice entra nel `Literal` `PlannerIssueCode` (`schemas :131-206`) in ordine alfabetico, quindi
  **prima** di `fx_rate_missing` (`:156`), fra `funding_cap_negative` e `fx_rate_missing`
  («fx_rate_i» < «fx_rate_m»). Il test del catalogo (`test_pac_planner_schemas.py:1215`) esige
  l'ordine;
- `issues.py`: `_normalizer_definition(…, "invalid")` nella mappa W1, nello stesso punto, prima di
  `fx_rate_missing` (`:72`);
- la guardia `issues.py:49-50` passa da 76 a 77, con il testo «77-value»;
- nei test:
  - `test_pac_planner_normalize.py:869-870`: da 76 a 77;
  - `test_pac_planner_schemas.py`: `EXPECTED_PLANNER_ISSUE_CODES` (~`:1112`), il conto a `:1214` e un
    caso in `DOWNSTREAM_NORMALIZER_ISSUE_CASES` (`:1631-1675`).
- Il frontend non ha mappe per codice: la chiave è `tools.pacAllocator.planner.issues.<code>`,
  `paramValues` passa id e valute come stringhe, e l'etichetta dell'entità `fx_rate` è la coppia.

**Impatto sui test esistenti: nessuno previsto.**
- Le 4 fixture di richiesta non hanno coppie incrociate (`09_scan_fixtures.log`).
- I test con tre valute costruiscono `ExactScenario` direttamente, senza passare dal normalizer
  (evaluator, oracle, policies, report).
- I due payload con `{"EUR/JPY", "EUR/KWD"}` non dichiarano la coppia incrociata, quindi il controllo
  si salta.

Lo confermano le suite.

### 2.3 Testi i18n

Una chiave, `tools.pacAllocator.planner.issues.allocation.fx_rate_inconsistent`, aggiunta con
`dev.py i18n add`. È la 67ª chiave `allocation.*`, e porta il totale da 4198 a 4199 chiavi per
lingua (base del treno 19; il 4356 → 4357 scritto qui prima veniva dal conto di prima del treno,
corretto in S5).

| Lingua | Testo |
|---|---|
| EN | This exchange rate does not match the {source_currency} and {destination_currency} rates against {valuation_currency}: converting {source_currency} into {destination_currency} would create value. Align the rates or set a conversion spread. |
| IT | Questo tasso di cambio non è coerente con i tassi di {source_currency} e {destination_currency} rispetto a {valuation_currency}: convertire {source_currency} in {destination_currency} creerebbe valore. Allinea i tassi o imposta uno spread di conversione. |
| FR | Ce taux de change ne concorde pas avec les taux de {source_currency} et {destination_currency} par rapport à {valuation_currency} : convertir {source_currency} en {destination_currency} créerait de la valeur. Alignez les taux ou définissez un spread de conversion. |
| ES | Esta tasa de cambio no es coherente con las tasas de {source_currency} y {destination_currency} frente a {valuation_currency}: convertir {source_currency} a {destination_currency} crearía valor. Alinea las tasas o define un spread de conversión. |

«Spread di conversione / de conversion / de conversión» è il nome del campo (`planner.fx.spread`).

### 2.4 Frontend: precisione adattiva (G2, G3)

Regola globale in `exactMoneyDisplay` (`format.ts:65-74`):
- Se il valore esatto è diverso da zero e alla scala `places` si arrotonda a `0`, si prendono **due
  cifre significative vere**: p0 è la posizione della prima cifra decimale non nulla di |v|, e si
  arrotonda half-away-from-zero a `min(p0+1, 20)` cifre.
- `approx` vale vero quando il testo mostrato è diverso dal valore esatto.
- Uno zero vero non entra in questo ramo e resta «0.00».
- La stessa regola vale nel ramo di ripiego su `display_decimal`, dove `approx` è sempre vero.
- `moneyArgs` (`:86-97`) allarga già `maxFraction` alla scala mostrata.
- La funzione di oggi, non adattiva, resta come `exactRoundedDisplay` interna: la usa L2
  (`formatPlannerL2`), che continua a mostrare «≈0» per un valore sotto la sua scala.
- `formatSolverNumber` non cambia.
- Il chip KPI (`KpiCards.svelte:70`, `formatExactMoneyPlain`) e ogni cella `exactMoney` ereditano la
  regola senza modifiche al codice: è un cambio di comportamento dichiarato.

Esempi:

| Valore | Oggi | Dopo |
|---|---|---|
| −47/21700 | (il calcolo cadeva) | «≈ −0.0022» |
| 0.00176 | «0.00176» (ledger) / «≈0.00» (KPI) | «≈ 0.0018» |
| −0.003365 | «−0.003365» (ledger) | «≈ −0.0034» |
| −0.0021 | «−0.0021» (ledger) | «−0.0021», senza ≈ |
| −0.004 (`finite_decimal`) | «0», approx | «−0.004», senza ≈ |
| 0.00095 | «≈0.00» (KPI) | «0.00095», senza ≈ |
| 0.000951 | «≈0.00» (KPI) | «≈ 0.00095» |
| 0.4 JPY (scala 0) | «≈0» | «0.4», senza ≈ |
| 0 | «0.00» | «0.00» |

Limite accettato: per |v| < 5·10⁻²¹ resta «≈0», perché le cifre si fermano a 20 (`MAX_DISPLAY_FRACTION`,
limite di Intl). Non si raggiunge con importi in minor unit.

Altri punti:
- `result/model.ts`, `ledgerFieldSpeaks` (`:350-353`): per `rounding_delta` si usa `exactSign`
  (`:162`). Oggi `decimalSign(row.rounding_delta)` riceverebbe un oggetto e solleverebbe
  (`parse` → `text.trim()`).
- `result/LedgerTable.svelte:91`: la cella del residuo passa da `type:'money'` (tutte le cifre,
  nessun ≈) a `type:'exactMoney'`, come il chip KPI (`KpiCards.svelte:70`). Dopo `api sync` il tipo
  generato rende `row[field]` un'unione, quindi senza questa modifica `front check` fallirebbe.

**Cambi di comportamento dichiarati.**
- `format.test.ts:184`: `−0.004` passa da `{text:'0', approx:true}` a `{text:'-0.004', approx:false}`.
- Nella tabella del ledger, un residuo con più di due decimali mostra ora «≈» con al massimo due cifre
  significative: «−0.012» diventa «≈ −0.01», «0.00176» diventa «≈ 0.0018». Prima mostrava ogni cifra.
- Il chip KPI non mostra più «≈0.00» per un totale non nullo sotto il centesimo.

### 2.5 Log degli errori del motore (commit a parte)

In `tool_plugins/pac_allocator.py`, `_log_engine_failure` (`:106-125`), chiamato dal ramo `except` di
`compute` (~`:199`), oggi registra solo il frame proprio più interno (`where`) e, se c'è, il frame di
libreria (`raised_in`). Nel caso CHF ha registrato `models.py:129:_require_nonnegative`, un helper
generico che non dice quale oggetto fallisce.

La modifica è additiva:
- `where` e `raised_in` restano;
- si aggiunge `callers`: i frame propri, al massimo due, che hanno chiamato `where`, dal più vicino;
- in tutto, quindi, al massimo tre frame propri;
- mai il messaggio, gli argomenti o le variabili locali.

Il test va in `test_pac_planner_tool_api.py` (corsia `api pac-planner-tool`). È il file del plugin, e
nessun altro commit di questo lavoro lo tocca, quindi i due commit si separano per percorso. È un test
puro: non chiede il fixture del server.

## 3. File e zone

| File | Zona | Passo |
|---|---|---|
| `backend/app/schemas/pac_allocator.py` | `Literal` `:131-206`; `PlannerLedgerRow.rounding_delta` `:1436`; `_validate_no_op_common` `:1760-1783` | S2, S3 |
| `backend/app/services/pac_allocator/planner_report.py` | `:639-650`, `:667` | S2 |
| `backend/app/services/pac_allocator/wire_numbers.py` | docstring `:132-138` | S2 |
| `backend/app/services/pac_allocator/normalize.py` | `__init__` `:136`; nuovo `validate_fx_coherence`; `run()` `:1135` | S3 |
| `backend/app/services/pac_allocator/issues.py` | `:49-50`, `:72` | S3 |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | una chiave, solo `dev.py i18n add` | S3 |
| `frontend/…/pac-allocator/planner/format.ts` | `exactMoneyDisplay` `:65-74` | S4 |
| `frontend/…/planner/result/model.ts` | `:350-353` | S4 |
| `frontend/…/planner/result/LedgerTable.svelte` | `:91` | S4 |
| `backend/test_scripts/test_services/test_pac_planner_planner.py` | R1, R2, R3, V1, V2 | S1 |
| `backend/test_scripts/test_services/test_pac_planner_normalize.py` | 2A, 76 → 77 | S1 |
| `backend/test_scripts/test_services/test_pac_planner_report.py` | residuo esatto o decimale | S1 |
| `backend/test_scripts/test_schemas/test_pac_planner_schemas.py` | riga del ledger, no-op, catalogo (S1); letterali `:291` e `:360-374`, impronte `:3762-3773` (S2) | S1, S2 |
| `backend/test_scripts/fixtures/pac_allocator/*result*.json` | `rounding_delta` in forma `ExactNumber` | S2 |
| `frontend/…/planner/format.test.ts` | precisione adattiva, `:184` | S1 |
| `frontend/…/planner/result/model.test.ts` | residuo `exact_ratio` | S1 |
| `frontend/…/planner/result/KpiCards.svelte` | nessuna modifica: eredita la regola di §2.4 | — |
| `backend/app/services/tool_plugins/pac_allocator.py` | `:99-125` | S7 |
| `backend/test_scripts/test_api/test_pac_planner_tool_api.py` | test del log | S7 |
| `review/PAC_ALLOCATOR_REVIEW_DOSSIER.md` | nota datata dopo `:66` | S6 |
| `implementation/README.md` | riga 13 (SHA di R7), riga 15 | S6 |
| `mkdocs_src/docs/user/tools/pac-allocator/index.en.md` | passo FX, un paragrafo nuovo dopo `:212`; niente vicino alla `:192` | S9 |

Esclusi dallo stage, perché generati e ignorati: i file prodotti da `api sync` (`openapi.json`,
`tool-contracts.openapi.json`, `tool-contract-map.generated.ts`, `generated-tools.ts`), log, build e
`.svelte-kit`.

## 4. Passi

### S0 — Piano ✅ 2026-10-08 22:45

> **Nota implementazione**: questo file. Le citazioni sono state riverificate alla baseline. Le
> fixture di richiesta sono state controllate in sola lettura con uno script di sessione
> (`09_scan_fixtures.log`): nessuna ha coppie incrociate.

### S1 — Test rossi (test-author) ✅ 2026-10-09 00:15

> **Nota implementazione**: test-author (sync) con brief autosufficiente: 7 file, +726/−16. Ha usato
> solo `py_compile` e controlli in processo, nessuna suite. Ho rivisto tutto il diff: è conforme al
> brief, la raccolta è sicura e le righe da non toccare sono intatte. Rossi verificati uno per volta
> sulla 6151, con il preambolo di corsia:
>
> | Comando | Ora, carico | Esito | Rossi e motivo | Log |
> |---|---|---|---|---|
> | `test services pac-planner-service` | 00:12, 5.5 | 6 F / 47 P | R1 manuale e automatico: `WireNumberTooLargeError` −47/21700; R1b: −18/5425; forma di V1: `'-0.0021' == {…}`; R2 e V2-invalid: `ValueError: spread_loss must be nonnegative` | `/tmp/libreFolio_pacfx_s1_service.log` |
> | `test services pac-planner-core` | 00:12, 5.4 | 5 F / 182 P | universo 76 invece di 77; oltre lo spread `ready` invece di `invalid`; una issue per coppia e Rebalancer incoerente: 0 issue; definizione W1: `KeyError` | `/tmp/libreFolio_pacfx_s1_core.log` |
> | `test services pac-planner-report` | 00:12, 4.9 | 3 F / 39 P | periodico: `WireNumberTooLargeError` −47/21700; che termina e zero: stringa invece di `FiniteDecimal` | `/tmp/libreFolio_pacfx_s1_report.log` |
> | `test schemas pac-planner` | 00:13, 4.6 | 10 F / 542 P | catalogo (indice 24); roundtrip e precedenza del codice nuovo: `literal_error`; riga con `ExactNumber`, zero e rapporto: `string_type`; testo nudo: non solleva; no-op con zero esatto, PAC e Rebalancer: `string_type`; no-op con residuo: messaggio diverso | `/tmp/libreFolio_pacfx_s1_schemas.log` |
> | `test front-utility core-unit` | 00:13, 4.3 | 4 F / 3448 P | `format.test.ts:194` (−0.004 → `'0'`); G3 (`'0'` invece di `'-0.0022'`); privacy spenta (`'≈0.00 €'`); privacy accesa (`'≈•••'`, senza segno) | `/tmp/libreFolio_pacfx_s1_coreunit.log` |
> | `test front-utility component-unit` | 00:13, 5.8 | 3 F / 2896 P | i tre `ledgerFields`: `TypeError: text.trim is not a function` | `/tmp/libreFolio_pacfx_s1_compunit.log` |
>
> Totale: 31 rossi, ognuno per il motivo previsto. Restano verdi tutti i controlli:
> - backend: V1 fatti, R3, V2-ready, i quattro casi `ready` del normalizer, la coppia mancante (solo
>   `fx_rate_missing`) e il Rebalancer coerente;
> - frontend: il controllo G3, le guardie del solver e di L2, lo zero vero mascherato.

> **⚠️ Fuori pista**:
> - Il test-author ha aggiunto, oltre al brief minimo, una fixture di modulo per V1
>   (`eur_funds_usd_wire`), le guardie del solver e di L2 e le parametrizzazioni PAC/Rebalancer. Le ho
>   accettate in revisione.
> - Il caso −0.004 ora è a `format.test.ts:194`, non a `:184`: il test-author ha aggiunto
>   l'intestazione G3.
> - Le impronte sono scese di 80 righe, ora a `test_pac_planner_schemas.py:3845` e `:3851`. I letterali
>   `"rounding_delta": "0"` del builder sono tre (`:241`, `:291`, `:351`), più la tupla a `:371`: li
>   allineo in S2.
> - Il primo lancio di `core-unit` usava la categoria `front`, che non esiste: argparse l'ha rifiutato
>   prima di toccare DB o server. La categoria giusta è `front-utility`; l'ho corretta in S5.
> - Prima della raccolta il runner ha eseguito `dev.py db upgrade` sulla data-dir di corsia. Il DB
>   esiste, quindi non serve `populate`.

Solo file già registrati, nessuna nuova voce nel runner. Ogni rosso deve fallire per il motivo
atteso, verificato un comando per volta.

Le specifiche sono state verificate prima del test-author con uno script di servizio, in processo,
senza DB né server (log di sessione `10_verify_specs.log`, 22:57, carico 8.57 / 12.46 / 15.56):
R1, R1b e R2 cadono oggi come previsto; V1, R3 e V2-ready sono verdi; il normalizer di oggi dà
`ready` su ogni caso incrociato e `fx_rate_missing` sulla coppia mancante.

`test_pac_planner_planner.py` (`services pac-planner-service`):
- **R1**, verso inverso, in entrambe le modalità di conversione. Il finanziamento è un conto esterno
  in USD; l'Asset è in EUR a 10.01; `EUR/USD` 1.085, s 0. Una variante: Asset a 10.00, s 0.01.
  - Si asserisce `ready_incumbent`, la rivalidazione stretta dell'output e `proof.kind ==
    "optimal_proven"` (G1).
  - Per ogni riga del ledger, `rounding_delta` esatto = Σ(credito registrato − credito esatto),
    ricalcolato con `Fraction` da debito, tasso e spread pubblicati, senza l'evaluator.
  - Il residuo EUR è un `exact_ratio` con `display_authority = "non_authoritative"`.
  - Oggi fallisce con `WireNumberTooLargeError`.
- **R2**, incrocio incoerente: CHF/EUR 1.06, EUR/USD 1.085, CHF/USD 1.1502, s 0, Asset in USD.
  - Si asserisce `invalid`, il codice nuovo al path `fx.fx_rate.CHF/USD.rate`, i suoi quattro
    parametri e nessuna soluzione.
  - Oggi fallisce con `ValueError: spread_loss must be nonnegative`.
- **R3**: con CHF/USD 1.1501 il piano è pronto.
- **V1**, verso diretto (EUR → USD): verde prima e dopo.
- **V2**:
  - restano verdi CHF/USD 1.1501, e 1.16 con s 0.01;
  - 1.16 con s 0.008 → `invalid`.

`test_pac_planner_normalize.py` (`services pac-planner-core`):
- l'uguaglianza esatta passa;
- lo spread minimo che pareggia passa;
- una coppia mancante dà solo `fx_rate_missing`;
- il lato della valuta di valutazione non si controlla mai;
- le valute senza rotta BUY non si controllano;
- una sola issue per coppia;
- l'universo passa a 77.

`test_pac_planner_report.py` (`services pac-planner-report`):
- un residuo periodico esce `exact_ratio`;
- un residuo che termina resta `finite_decimal`.

`test_pac_planner_schemas.py` (`schemas pac-planner`):
- la riga accetta un `ExactNumber`;
- un no-op con zero esatto passa, uno con residuo non nullo no;
- catalogo, precedenza e impronte (queste si aggiornano in S2/S3).

`format.test.ts` (`core-unit`):
- «≈-0.0022» per −47/21700;
- mai «≈0.00» né «≈-0.00» per un valore non nullo;
- uno zero vero resta «0.00»;
- `finite` −0.004 → «-0.004» senza ≈;
- il ripiego su `display_decimal`;
- il cambio di `:184`.

`result/model.test.ts` (`component-unit`): `ledgerFields` mostra un residuo `exact_ratio` non nullo.

### S2 — Correzione A (backend) ✅ 2026-10-09 00:25

§2.1, con l'aggiornamento delle fixture di risultato e delle due impronte.

> **Nota implementazione**: le modifiche di §2.1 sono tutte applicate.
> - `schemas/pac_allocator.py:1436`: il residuo ora è `ExactNumber`. In `_validate_no_op_common` è
>   uscito da `flow_fields` e ha un controllo a parte, `_exact_fraction(row.rounding_delta) != 0`, con
>   lo stesso messaggio.
> - `planner_report.py:669` usa `ratio_to_exact_number`, già importato.
> - Docstring corrette: `build_ledger_rows` e `ratio_to_fixed_decimal`.
> - Le fixture di risultato sono migrate con uno script che conserva il formato
>   (`/tmp/libreFolio_pacfx_migrate_fixtures.py`). Sostituzioni e byte:
>   - `min.v2`: 1 sostituzione, 13 722 → 13 789 byte;
>   - `medium.v2`: 3 sostituzioni, 37 762 → 37 963 byte;
>   - `candidate-max.v2`: 4 sostituzioni, 21 018 → 21 166 byte.
>   Tutte sono molto sotto il tetto di 262 144 byte, l'unica asserzione di `:767`.
> - Nessun altro consumatore backend: `rounding_delta` del ledger compare solo nello schema, nel
>   validatore no-op e nel report.
> - Nessuna fixture frontend o E2E costruisce righe del ledger.

> **⚠️ Fuori pista**:
> - Nel test degli schemi, solo `:291` (la riga dell'incumbent) e la tupla di `:371` (il no-op del
>   Rebalancer) sono righe del ledger. `:241` e `:351` sono campi di `accounting`, già `ExactMoney`
>   tramite `_money`.
> - La migrazione dei due letterali e delle impronte passa al test-author dopo S3: il `Literal` del
>   codice nuovo cambia di nuovo lo schema, quindi le impronte si calcolano una volta sola, a schema
>   finale.

### S3 — Correzione 2A e i18n ✅ 2026-10-09 00:30

§2.2 e §2.3.

> **Nota implementazione**: le modifiche di §2.2 e §2.3 sono tutte applicate.
> - **Schema**: il `Literal` `PlannerIssueCode` ha `"allocation.fx_rate_inconsistent"` in ordine
>   alfabetico, prima di `fx_rate_missing`.
> - **`issues.py`**: la guardia passa a 77 valori; la definizione W1 del codice è `invalid`.
> - **`normalize.py`**:
>   - l'import di `CurrencyIssueParam`;
>   - l'insieme `reported_fx_rate_inconsistent`, che emette l'issue una volta per coppia;
>   - `validate_fx_coherence()`, chiamata in `run()` subito dopo `validate_fx_pair_closure()`.
> - **Le conversioni controllate** sono le stesse che la chiusura richiede: per ogni rotta BUY
>   quotata in q, ogni valuta di cassa c del suo Broker.
>   - Si salta quando c = q, c = V o q = V.
>   - Si salta quando manca un tasso o non è positivo: `fx_rate()` restituisce `None`, e il problema
>     lo segnala già `validate_fx_rates` o la chiusura.
>   - Si salta quando lo spread è fuori da [0, 1): lo segnala già `validate_fx_rates`.
>   - Il confronto è stretto, su `ExactRatio`. La perdita da spread del valutatore usa il credito
>     esatto (`evaluator.py:1799`), quindi l'uguaglianza è davvero coerente.
> - **`fx_rate()` non solleva su testo malformato**: `fx_rates` e `fx_spread_rate` sono
>   `PlannerFixedDecimal`, validati dallo schema prima del normalizzatore.
> - **i18n**: `dev.py i18n add` della chiave
>   `tools.pacAllocator.planner.issues.allocation.fx_rate_inconsistent`, con i testi di §2.3.
>   - Diff: 4 file, +8/−4.
>   - Le foglie per lingua passano da 4198 a 4199 (il conteggio dell'audit è atteso a 4357), e le 4
>     lingue hanno lo stesso insieme di chiavi. *(S5: anche l'audit conta 4199. Il 4357 era il conto
>     di prima del treno 19.)*
>   - Lo strumento aggiunge la chiave in fondo al nodo `allocation`: è la sua forma canonica.
> - **Testi controllati sul vicinato**:
>   - nominano il campo come l'etichetta dell'editor («Conversion spread», «Spread di conversione»,
>     «Spread de conversion», «Spread de conversión»);
>   - usano il registro di ogni lingua (tu in IT e ES, vous in FR);
>   - in FR, uno spazio normale prima dei due punti, come le chiavi vicine.
> - **Migrazione del test-author** (`test_pac_planner_schemas.py`):
>   - `:291`: `_finite("0")`;
>   - `:369-375`: la tupla senza `rounding_delta`, più `ledger["rounding_delta"] = _finite("0")`;
>   - impronte con un commento sul motivo a `:3841`:
>     - PAC `a999932e…cbad` (era `4f061103…58bb`);
>     - Rebalancer `a1daf513…7822` (era `be2bb19d…8e62`).
>   - Lo script `/tmp/libreFolio_pacfx_fingerprints.py` annulla solo le due modifiche approvate e
>     ritrova i vecchi valori congelati: le impronte si sono mosse solo per queste due.
> - **Suite sulla 6151, una per volta, alle 00:29, carico 6.9–7.7**:
>
>   | Comando | Esito | In S1 |
>   |---|---|---|
>   | `services pac-planner-core` | 187 passati | 5 falliti, 182 passati |
>   | `services pac-planner-report` | 42 passati | 3 falliti, 39 passati |
>   | `services pac-planner-service` | 53 passati | 6 falliti, 47 passati |
>   | `schemas pac-planner` | 552 passati | 10 falliti, 542 passati |
>
>   Tutti e 24 i rossi backend di S1 sono verdi, e i controlli restano verdi.
>   I log sono `/tmp/libreFolio_pacfx_s3_{core,report,service,schemas}.log`.

> **⚠️ Fuori pista**:
> - Il test-author segnala che `frontend/src/lib/api/tool-contracts.openapi.json` ha ancora
>   l'impronta vecchia.
>   - È un file generato e ignorato da git (come `openapi.json`, `generated-tools.ts` e
>     `tool-contract-map.generated.ts`).
>   - Lo rigenera `api sync` in S5, e non entra nello stage.
> - `implementation_version` resta 1.0.0, come `contract_version`.
>   - Il tool non è mai uscito, e nessun registro blocca l'impronta: la calcola il registry a
>     runtime (`registry.py:121`).
>   - L'executor confronta l'impronta della richiesta con il descriptor (`executor.py:345`). Una
>     scheda aperta prima del deploy si ferma, e basta ricaricarla.

### S4 — Frontend ✅ 2026-10-09 00:37

§2.4.

> **Note implementazione**:
> - `format.ts`:
>   - la funzione di oggi resta, privata, come `exactRoundedDisplay`;
>   - `exactMoneyDisplay` la chiama alla minor unit. Se il testo è `0`, rilegge il valore arrotondato
>     a 20 cifre, trova l'indice `i` della prima cifra decimale non nulla e arrotonda a
>     `min(i+2, 20)` cifre (p0 + 1, con p0 = i + 1). Se a 20 cifre resta `0` (zero vero, o |v| sotto
>     5·10⁻²¹) restituisce il risultato alla minor unit, invariato.
>   - Cercare p0 sul valore già arrotondato a 20 cifre dà la stessa cifra del valore esatto, salvo
>     quando le cifre da p0 a 20 sono tutte 9 e il riporto la sposta di un posto. In quel caso
>     l'arrotondamento a p0 o a p0+1 dà la stessa potenza di dieci, quindi il testo mostrato non
>     cambia.
>   - `formatPlannerL2` usa `exactRoundedDisplay`; `formatSolverNumber` non cambia. Docstring del
>     modulo, di L2 e del solver aggiornate con G3.
> - `result/model.ts`: `ledgerFieldSpeaks` ha un ramo per `rounding_delta` con `exactSign`.
> - `result/LedgerTable.svelte`: la cella del residuo è `exactMoney`, senza segno come le altre celle
>   del ledger.
> - **Suite sulla 6151, una per volta**:
>
>   | Comando | Ora, carico | Esito | In S1 |
>   |---|---|---|---|
>   | `front-utility core-unit` | 00:35, 4.7–7.8 | 118 file, 3452 passati | 4 falliti |
>   | `front-utility component-unit` | 00:36–00:37, 7.4–13.2 | 111 file, 2899 passati | 3 falliti |
>
>   Tutti e 7 i rossi frontend di S1 sono verdi. I log sono
>   `/tmp/libreFolio_pacfx_s4_{core,component}.log`.

> **⚠️ Fuori pista**:
> - Ho valutato `signed: true` per la cella del residuo e l'ho tolto: nessuna cella del ledger mostra
>   il «+», e un negativo ha comunque il suo «−».
> - Rischio E2E: nessuna spec in `frontend/e2e` cita `rounding_delta`, «≈0.00» o «≈-0» (grep vuoto).
> - I tipi generati hanno ancora `rounding_delta` del ledger come stringa (`generated-tools.ts:843`)
>   fino ad `api sync`. Il restringimento di `row[field]` in `LedgerTable.svelte` e `model.ts` lo
>   verifica `front check` in S5. Vitest non controlla i tipi.

### S5 — `api sync` e gate sulla 6151 ✅ 2026-10-09 00:49

Un comando per volta, in quest'ordine:
1. `api sync`;
2. `front build --debug`;
3. `front check`;
4. `services pac-planner-core`, `pac-planner-report`, `pac-planner-service`,
   `pac-planner-evaluator`, `pac-planner-proof`, `pac-planner-wire-numbers`;
5. `schemas pac-planner`;
6. `api pac-planner-tool`;
7. `front-utility core-unit`, `front-utility component-unit`;
8. `i18n audit`, `check-orphans`, `lint`.

> **Note implementazione**:
> - Preambolo: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py`, più
>   `test --test-port 6151 --data-dir /tmp/librefolio-r2-d` per le suite. Base `4d09ac2ac`.
>
>   | Comando | Ora, carico | Esito |
>   |---|---|---|
>   | `api sync` | 00:37–00:38, 8.9–9.5 | exit 0; `generated-tools.ts:843` ora ha il residuo come `ExactNumber`, e il codice nuovo è nei contratti |
>   | `front build --debug` | 00:38–00:39, 8.2 | exit 0 |
>   | `front check` | 00:39–00:40, 9.7–8.4 | 0 errori, 0 avvisi |
>   | `services pac-planner-core` | 00:40, 7.4–8.0 | 187 passati |
>   | `services pac-planner-report` | 00:40, 8.0–7.9 | 42 passati |
>   | `services pac-planner-service` | 00:41, 7.9–7.5 | 53 passati |
>   | `services pac-planner-evaluator` | 00:41, 7.5–7.8 | 159 passati |
>   | `services pac-planner-proof` | 00:41, 7.8–7.1 | 30 passati |
>   | `services pac-planner-wire-numbers` | 00:41, 7.1–6.8 | 39 passati |
>   | `schemas pac-planner` | 00:41, 6.5–6.3 | 552 passati |
>   | `api pac-planner-tool` | 00:41–00:42, 6.1–13.2 | 7 passati; porta libera prima e dopo |
>   | `front-utility core-unit` | 00:42–00:43, 13.8–14.9 | 118 file, 3452 passati |
>   | `front-utility component-unit` | 00:43–00:44, 14.9–16.9 | 111 file, 2899 passati |
>   | `i18n audit` | 00:44, 14.9–13.5 | exit 0; 4199 chiavi, tutte complete; 0 inutilizzate; 0 chiavi backend mancanti |
>   | `check-orphans` | 00:45, 11.6 | tutti i file registrati e raggiungibili da un `all` |
>   | `lint` | 00:45, 10.7 | «All checks passed!» |
>   | `front check` (dopo la riforma della cella) | 00:47–00:48, 6.1–5.7 | 0 errori, 0 avvisi |
>   | `front-utility component-unit` (idem) | 00:48–00:49, 5.8–12.5 | 111 file, 2899 passati |
>
> - I log sono in `/tmp/libreFolio_pacfx_s5_*.log`.

> **⚠️ Fuori pista**:
> - **Chiavi i18n: 4199, non 4357.** Il treno 19 contiene già l'audit i18n generale: la base ha 4198
>   chiavi per lingua. Il conto foglia per foglia, HEAD contro worktree, dà in ognuna delle 4 lingue
>   una sola chiave aggiunta (`tools.pacAllocator.planner.issues.allocation.fx_rate_inconsistent`) e
>   nessuna tolta. Il 4357 del §7 era il conto di prima del treno; l'ho corretto.
> - **Vitest rilanciato dopo `api sync`.** In S4 le due suite giravano col client zod generato prima
>   della modifica; ora girano con quello nuovo. Esito identico.
> - **Prettier** (`front format --check`, sola lettura): 30 file segnalati, tutti già segnalati a
>   `HEAD`. È il debito `style(pac)` rimandato dal coordinator. L'unico mio,
>   `result/LedgerTable.svelte`, era già fuori formato a `HEAD` (il `$derived.by` esterno). Ho
>   riscritto la mia cella nella forma su una riga che Prettier produce. Ora l'uscita di Prettier su
>   `HEAD` e sul worktree differisce solo per la riga della cella, e il futuro commit di stile la
>   reindenta soltanto. Dopo la modifica (solo spazi) ho rilanciato `front check` e `component-unit`.
> - **black** (`black --check`, sola lettura, sui 10 file Python toccati): 9 a posto. Il decimo,
>   `test_pac_planner_schemas.py`, ha due blocchi fuori formato già a `HEAD` (`:2025`, `:3843`),
>   lontani dai nostri blocchi. È debito ereditato e non lo tocco.
> - **Osservazione, fuori scope.** `i18n audit` segnala la famiglia backend
>   `tools.allocation.constraints.` (da `evaluator.py:968`) senza chiavi di catalogo. È il campo
>   interno `ConstraintRef.explanation_key` (`models.py:664`). Non arriva in uscita:
>   `planner_report.py:628` pubblica `explanation_keys=[]`, e il frontend non lo legge. Era già così
>   prima di questo piano e il tool d'audit del treno ora lo vede. Lo passo al backlog dell'audit
>   i18n.
> - `check-orphans` scrive un'istantanea del DB di test in `.testLog/00_archive/`, ignorato da git.

### S6 — Journal

- Nota datata nel dossier (§1.4).
- README:
  - riga 13: gli SHA di R7, `dbedcc822` · `f374f1e5b`, merge `9f06df702`;
  - riga 15: questo piano.

> ✅ **2026-10-09 01:22.**
>
> **Note implementazione**:
> - Dossier: nota «Correction 2026-10-09» sotto il Fork 2 (dopo `:65`, «checking for it
>   afterwards.»), in inglese come il dossier. Dice dove vale «structurally impossible» (cicli fra
>   due valute) e dove no (triangoli), e rimanda a questo piano per la 2A e per l'elenco dei piani
>   archiviati che ripetono l'affermazione.
> - README, riga 13: ✅, con gli SHA di R7 (`dbedcc822` `fix(pac)`, `f374f1e5b` journal) e la merge
>   `9f06df702` con `c9a602f74`, rivalidata con 8 gate su 8 verdi.
> - README, riga 15: questo piano, eseguito prima della riga 14; stato «in attesa degli SHA».
>
> **⚠️ Fuori pista**: il §1.4 cita il Fork 2 a `:60-66`; il paragrafo è a `:59-65`. La nota sta
> comunque subito dopo, come previsto. La riga 14 del README resta com'è: non è nella zona di S6.

### S7 — Log del motore (commit a parte)

§2.5. Prima il rosso, poi la modifica, poi `api pac-planner-tool` e `lint`.

> ✅ **2026-10-09 01:18.**
>
> **Note implementazione**:
> - Rossi scritti dal test-author in `test_pac_planner_tool_api.py`: 5 test nuovi (sezione
>   `:443-671`), test puri senza il fixture del server. Cattura con `capture_logs` più
>   `add_logger_name`, come il precedente di `test_post_migration.py:1395-1440`, con una barriera
>   sull'evento, sul logger e sul livello `error`. La libreria finta è un `boom` compilato con un
>   percorso fuori dal repository, così il suo frame è di libreria.
> - Rosso confermato sulla 6151 (01:14–01:15, carico 11.9→9.3): 3 falliti per `callers` mancante,
>   2 guardie verdi (nessuna chiave `callers` senza chiamante proprio; né il messaggio né gli importi
>   nell'evento). Log: `/tmp/libreFolio_pacfx_s7_red.log`.
> - Cura in `_log_engine_failure` (`pac_allocator.py:124-128`): `callers` è
>   `reversed(own[-3:-1])`, quindi al massimo due frame propri sopra `where`, dal più vicino; la
>   chiave manca se non ce ne sono. `where` e `raised_in` invariati; docstring aggiornata.
> - `api pac-planner-tool`: 12 passati (01:16–01:17, carico 9.4→11.1), porta libera prima e dopo. Log:
>   `/tmp/libreFolio_pacfx_s7_green.log`.
> - `lint`: «All checks passed!». `black --check` sui due file: a posto.
> - L'impronta del contratto è dei soli schemi (`tools/registry.py:121`, `schema_fingerprint`): S7
>   non la cambia. `implementation_version` resta 1.0.0, perché il log non cambia le uscite.
>
> **⚠️ Fuori pista**: il test-author ha aggiunto un caso limite non chiesto, un solo chiamante
> (`test_pac_engine_failure_log_names_a_lone_caller_alone`). Lo tengo: fissa «al massimo due» anche
> come «uno», senza errore per il secondo mancante.

### S8 — Checkpoint

1. `git diff --check`.
2. Inventario dei file.
3. Porta 6151 libera (`lsof -nP -iTCP:6151 -sTCP:LISTEN` vuoto).
4. Messaggi di commit proposti e righe del CHANGELOG.
5. FROZEN.

> ✅ **2026-10-09 01:25.**
>
> **Note implementazione**:
> - `git diff --check` pulito; il piano, non tracciato, senza spazi finali né tab. Stage vuoto,
>   `HEAD` ancora `4d09ac2ac`.
> - Inventario: 26 file modificati (+1115/−62) e questo piano, non tracciato. Nessun
>   file generato fra i modificati: `openapi.json`, `tool-contracts.openapi.json`,
>   `generated-tools.ts`, `tool-contract-map.generated.ts`, `frontend/build/` e `.testLog/` sono
>   ignorati da git.
> - Suite in più, per provare il «Lo confermano le suite» del §2.2, che in S5 mancava per tre suite
>   del PAC. Tutte verdi sulla 6151, porta libera prima e dopo (01:21–01:23, carico 9.3→11.6):
>
>   | Suite | Esito |
>   |---|---|
>   | `services pac-planner-oracle` | 21 passati |
>   | `services pac-planner-policies` | 40 passati |
>   | `services pac-planner-solver` | 40 passati |
>   | `schemas tools` | 271 passati |
>   | `services tools-registry` | 93 passati |
>   | `services tools-lifecycle` | 91 passati |
>   | `utils tools-wire` | 196 passati |
>   | `api tools` | 7 passati |
>
>   Log: `/tmp/libreFolio_pacfx_s8_*.log`. Nessun test fissa più le impronte vecchie
>   (`4f061103`, `be2bb19d`).
> - Previsione dei conflitti: `dev_release2` è ora `3af9aac63` (treno 20), discendente di `HEAD`.
>   Tocca 21 file (Risk L1, pagine FX, journal), nessuno dei miei 27: nessuna sovrapposizione,
>   né di testo né di significato.
> - Ancora del CHANGELOG verificata: «…and every exchange appears in the plan.» è a
>   `CHANGELOG.md:18`, uguale nel treno 20.
>
> **⚠️ Fuori pista**:
> - La pagina utente del PAC (`mkdocs_src/docs/user/tools/pac-allocator/index.en.md`, solo EN) non
>   dice niente di sbagliato dopo questa correzione. Però il passo FX (`:196-221`) non dice che i
>   cambi devono essere coerenti fra loro. Non era nel §3: lo propongo al coordinator come aggiunta
>   piccola, via docs-writer, invece di allargare il perimetro da solo.
> - Soggetti dei commit accorciati a ≤50 caratteri (§5).

### S9 — Pagina utente e record dei commit

Chiesto dal coordinator alle 01:26, dopo il CHECKPOINT READY. Poi di nuovo FROZEN.

1. Docs-writer: 2–3 frasi in inglese nel passo FX della pagina utente del PAC, dopo il paragrafo
   che finisce con «…conversions use the rate with the spread, $x\,(1 - s)$.» (`:212`).
   - Contenuto: i cambi devono essere coerenti fra loro. Un cambio diretto che, al netto dello
     spread, rende più del giro attraverso la valuta di valutazione ferma il calcolo con
     **Input not valid**: si allineano i tassi o si imposta uno spread. In più, il residuo
     d'arrotondamento con «≈».
   - Niente vicino alla `:192`: lì M mette un'immagine nel lotto 5.
   - Commit a sé, `docs(pac)`. Il journal diventa il quarto commit.
2. Gate, uno per volta: `mkdocs build` (strict) e `mkdocs check-links`.
3. Record in `/tmp/libreFolio_commits/`, con una copia nella cartella di sessione:
   - `d-r15-C1.txt` … `d-r15-C4.txt`, solo ASCII, soggetto ≤ 50 caratteri, righe ≤ 72;
   - `d-r15-C1.paths` … `d-r15-C4.paths`, un percorso per riga;
   - `d-r15-blobs.txt`, `hash-object` e percorso, calcolato dopo l'ultima modifica.
4. FROZEN.

> ✅ **2026-10-09 02:01.**
>
> **Note implementazione**:
> - Pagina utente (`mkdocs_src/docs/user/tools/pac-allocator/index.en.md`), scritta dal docs-writer:
>   25 righe inserite dopo la `:215`, nessuna tolta (`@@ -215,0 +216,25 @@`), niente vicino alla `:192`.
>   Tre frasi in due paragrafi:
>   - i cambi devono essere coerenti. Esempio CHF → USD → EUR con la formula
>     $x_{\text{CHF} \to \text{USD}}\,(1 - s)\,x_{\text{USD} \to \text{EUR}} \le x_{\text{CHF} \to \text{EUR}}$.
>     L'esito è **Input not valid**, col link a `#reading-the-result`. La causa è un tasso Manual,
>     oppure tassi Auto di giorni o fonti diversi. Il rimedio: allineare i tassi o impostare uno spread;
>   - il residuo: come ordini e fee, l'importo ricevuto da una conversione si arrotonda half up alla
>     minor unit. La colonna **Rounding** mette «≈» quando la cifra mostrata è arrotondata. Sotto la
>     minor unit tiene le cifre che servono: «≈ −0.0022», non «≈ −0.00».
>   - Riscontri nel codice:
>     - `normalize.py:664-705`: solo le conversioni fra due valute diverse da quella di valutazione;
>       l'uguaglianza è ammessa, da qui `\le`;
>     - `ledger.py:35-52` e `:127`: `fx_debit` esatto, `fx_credit` HALF_UP;
>     - `format.ts:67-88` e `format.test.ts:29-35`;
>     - `portfolio_allocation_source.py:892-924` e `models.py:980`: Auto legge l'ultimo tasso di ogni
>       coppia, ciascuno con la sua fonte.
> - Gate, uno per volta:
>
>   | Gate | Esito | Ora e carico |
>   |---|---|---|
>   | `mkdocs build` (strict: `dev.py` passa `--strict`, `mkdocs.yml:22`) | exit 0 in 25.4 s, 0 righe WARNING/ERROR. Nell'HTML ci sono il paragrafo, la formula in un blocco `arithmatex`, il link e `id="reading-the-result"` | 01:56:03–01:56:34, carico 4.15 → 11.72 |
>   | `mkdocs check-links` | `user/tools/pac-allocator` ✅, 89 link validi; exit 1 per **un** link rotto non mio (Fuori pista) | 01:57:02–01:57:05, carico 13.69 |
>
>   Log: `/tmp/libreFolio_pacfx_s9_mkdocs_build.log` e `/tmp/libreFolio_pacfx_s9_check_links.log`.
>   `git status` è uguale prima e dopo: 28 voci, perché `mkdocs_src/site/` è ignorato. Stage vuoto,
>   porta 6151 libera.
> - Record in `/tmp/libreFolio_commits/`, scritti e verificati con
>   `/tmp/libreFolio_pacfx_s9_records.py` («VERIFY OK»):
>   - `d-r15-C1.txt` … `C4.txt`, solo ASCII: soggetti di 49, 44, 36 e 46 caratteri; righe al massimo
>     di 69, 63, 68 e 66;
>   - `d-r15-C1.paths` … `C4.paths`: 22 + 2 + 1 + 3 = 28 percorsi, disgiunti, uguali a `git status`;
>   - `d-r15-blobs.txt` calcolato per ultimo, dopo questa nota e il README. Copia nella cartella di
>     sessione.
>
> **⚠️ Fuori pista**:
> - La prima stesura del docs-writer era giusta nei fatti, ma usava `$c$`, `$q$` e `$V$`. Sulla
>   pagina `$q$` è già la quantità dell'ordine (`:63`, `:130-139`) e `$V_i$` il valore di un Asset
>   (`:257`, `:374`). Aveva anche una frase di circa 85 parole. Le righe che gli avevo dato erano
>   spostate di 2: il paragrafo d'ancora va da `:212` a `:214`. Nella seconda stesura c'è il mio
>   testo, con l'esempio in valute e la formula nello stile del blocco $D \cdot x\,(1 - s)$.
> - Terza stesura, su un'osservazione del docs-writer verificata nel codice. «A converted amount is
>   rounded» si poteva leggere come l'importo convertito, che invece resta esatto (`fx_debit`,
>   `ledger.py:35-42`); ora è «the amount received from a conversion». In più «≈ 0.00» → «≈ −0.00»:
>   −0.0022 a due cifre è −0.00, la forma che G3 vieta (`format.test.ts:30`).
> - `check-links` rosso, preesistente e fuori perimetro: `user/assets/detail/chart/#rolling-return`,
>   da `frontend/src/routes/(app)/assets/[id]/+page.svelte:3012`, commit `e3af27ff3` del 2026-10-01.
>   L'ancora c'è in `chart.en.md:22`, mentre `chart.{it,fr,es}.md` non hanno ancora la sezione
>   Rolling Return: è debito di traduzione. Né il mio diff né il treno 20 (`3af9aac63`) toccano questi
>   file. Lo segnalo al coordinator e non lo correggo.
> - Rischio residuo, misurato; non è una regressione.
>   - Lo spread predefinito è 0 (`frontend/src/lib/features/tools/pac-allocator/planner/defaults.ts:13`)
>     e i tassi si salvano a 10 decimali (`Numeric(24, 10)`, `backend/app/db/models.py:976`).
>   - Un cambio incrociato ricavato dalla catena attraverso la valuta di valutazione, e arrotondato
>     half up alla decima cifra, supera la catena esatta circa metà delle volte. Con s = 0 il
>     controllo stretto 2A lo segnala.
>   - Esempio: EUR/RON 4.97 ed EUR/USD 1.085 danno un eccesso relativo di +2.06e-10.
>   - Su 20 000 casi casuali, con EUR/c ed EUR/q a 4 decimali, ne segnala 10 011, il 50.1%
>     (`/tmp/libreFolio_pacfx_s9_chain.py`, log `/tmp/libreFolio_pacfx_s9_chain.log`). Un cambio
>     incrociato quotato a parte va di qua o di là in modo simile.
>   - Prima di 2A gli stessi casi facevano fallire il calcolo (`_require_nonnegative`).
>   - Una tolleranza non si può dare: l'evaluator vuole una perdita da spread non negativa, cioè
>     niente arbitraggio.
>   - Opzioni per il developer:
>     - (a) lasciare così, come documentato in pagina;
>     - (b) uno spread predefinito > 0 quando c'è una coppia incrociata;
>     - (c) l'issue riporta lo spread minimo che rende coerenti i tassi, e l'utente sceglie con un
>       numero davanti.
>   - Nessun codice cambiato.

## 5. Commit proposti (per percorso)

1. `fix(pac): exact FX residual, coherent cross rates`. Contiene tutto il §3 tranne i file di S6,
   S7 e S9.
2. `chore(pac): log callers of an engine failure`. Contiene `tool_plugins/pac_allocator.py` e
   `test_pac_planner_tool_api.py`.
3. `docs(pac): exchange rates must agree`. Contiene solo la pagina utente del PAC (S9).
4. `docs(journal): row 15 PAC FX fix, dossier note`. Contiene questo piano, il README e il dossier.

I soggetti sono stati accorciati in S8, perché stiano entro 50 caratteri. Prima erano
`fix(pac): publish exact FX rounding residual, reject incoherent cross rates`,
`chore(pac): log calling frames of an engine failure` e
`docs(journal): PAC FX conversion fix plan, dossier correction`.

In S9 il commit della pagina utente si è inserito al terzo posto e il journal è passato al quarto.
I messaggi completi, solo ASCII, sono nei record `d-r15-C1.txt` … `d-r15-C4.txt`. Il corpo di C1
scrive «approx (~)» al posto di «≈».

## 6. CHANGELOG (proposta, la scrive il coordinator)

Nessuna voce «Fixed». Due frasi nella voce del PAC (`CHANGELOG.md:18`), dopo «…and every exchange
appears in the plan.»:

> Exchange rates must agree with each other: when a direct rate between two currencies, after the
> spread, gives more than going through the valuation currency, the plan reports it as an invalid
> input — align the rates or set a conversion spread — instead of planning with it. The amount
> received from a conversion is rounded to the smallest unit of its currency, and the plan shows the
> rounding difference with the digits it needs, marked ≈ when the figure shown is rounded.

**⚠️ Fuori pista (S9)**: la seconda frase mandata col CHECKPOINT READY era troppo stretta. Diceva
«marked ≈ when it has no exact decimal form». Ma `exactRoundedDisplay` (`format.ts:67-76`) mette
«≈» ogni volta che la cifra mostrata è arrotondata. Quindi lo mette sempre a un rapporto periodico,
e anche a un decimale finito con più cifre di quelle mostrate: −0.012 diventa «≈ −0.01». Ho
corretto la frase e ho aggiunto «with the digits it needs» per G3. Poi «A converted amount is
credited» è diventato «The amount received from a conversion», come nella pagina: l'importo
convertito resta esatto (`ledger.py:35-42`). Al coordinator la mando come correzione.

## 7. Definition of done

- [x] R1 verde in entrambe le modalità: `ready_incumbent`, `optimal_proven`, residuo esatto uguale alla
      somma calcolata in modo indipendente, output rivalidato.
- [x] R2 `invalid` con codice, path e parametri; nessuna eccezione. R3, V1 e V2 come previsto.
- [x] Normalizer: i sette casi del §S1 verdi; universo a 77.
- [x] Report e schemi: `exact_ratio` e `finite_decimal`; no-op; impronte aggiornate con il motivo.
- [x] Frontend: precisione adattiva; «≈» solo quando il valore è inesatto; mai «≈0.00» per un valore
      non nullo; il residuo del ledger è `exactMoney`.
- [x] i18n: una chiave × 4 tramite `dev.py i18n add`; audit verde; 4199 chiavi per lingua (4198 della
      base del treno 19, più una; corretto in S5, prima era 4357).
- [x] Gate di S5 verdi sulla 6151, con il carico annotato.
- [x] S7 in un commit a sé: rosso, poi verde; nessun messaggio nel log.
- [x] Dossier e README aggiornati.
- [x] Porta libera, nessun file generato nello stage, CHECKPOINT READY.
- [x] Pagina utente: 3 frasi nel passo FX, lontano dalla `:192`. `mkdocs build` strict verde.
      `check-links` verde sulla pagina PAC; c'è un rosso preesistente fuori perimetro,
      `#rolling-return` (Fuori pista di S9).
- [x] Record dei 4 commit in `/tmp/libreFolio_commits/`: ASCII, soggetti ≤ 50, righe ≤ 72; percorsi
      disgiunti che coprono tutto `git status`; blob calcolati per ultimi (S9).

## 8. Avanzamento

| Passo | Stato | Data | Note |
|---|---|---|---|
| S0 Piano | ✅ | 2026-10-08 22:45 | |
| S1 Rossi | ✅ | 2026-10-09 00:15 | 31 rossi, motivi previsti; controlli verdi |
| S2 Correzione A | ✅ | 2026-10-09 00:25 | schema, validatore no-op, report, 3 fixture |
| S3 2A + i18n | ✅ | 2026-10-09 00:30 | normalizzatore, codice 77, chiave i18n; 4 suite backend verdi (834) |
| S4 Frontend | ✅ | 2026-10-09 00:37 | `exactMoneyDisplay` adattiva, L2 no; residuo `exactMoney`; core-unit 3452, component-unit 2899 verdi |
| S5 Gate | ✅ | 2026-10-09 00:49 | tutti verdi; chiavi 4199 (non 4357); cella del ledger su una riga; debito di formato ereditato |
| S6 Journal | ✅ | 2026-10-09 01:22 | nota nel dossier, README righe 13 e 15 |
| S7 Log del motore | ✅ | 2026-10-09 01:18 | rosso 3+2, cura `callers`, 12 passati, lint e black a posto |
| S8 Checkpoint | ✅ | 2026-10-09 01:25 | 8 suite in più verdi (oracle, policies, solver, piattaforma Tool); nessuna sovrapposizione col treno 20; CHECKPOINT READY, FROZEN |
| S9 Pagina utente e record | ✅ | 2026-10-09 02:01 | docs-writer, 25 righe dopo la `:215`; `mkdocs build` strict verde; `check-links`: PAC ✅, un rosso preesistente non mio (`#rolling-return`); record C1–C4 «VERIFY OK», 28 percorsi; rischio dello spread 0 misurato (50.1%) e passato al developer; FROZEN |
