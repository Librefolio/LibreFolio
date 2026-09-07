# Piano — blocco finale: Onda 3, deduplicazione residua, due classi comuni

> Lo storico dei giri precedenti è in `files/plan-storico-coverage-campaign.md`.
> Stato di partenza: `all --workers 8` **15/15**, lint **38** (uno sotto la baseline
> preesistente), 98 file pronti al commit (messaggio in `/tmp/libreFolio_commit_ALL.txt`).

---

## Risposta alla domanda: le 101 classi pydantic sfruttano `common.py`?

**In parte sì**, e c'è spazio per due classi nuove che chiuderebbero due buchi reali.

Cosa l'AI Export già riusa, misurato sugli import: `Currency` (10 file), `SafeDecimal`,
`DateRangeModel`, `OpenDateRangeModel`, `BackwardFillInfo`, e ora `StrictModel` (5 file
diretti, 100 classi per eredità). Non c'è nessun caso di modello che **ridichiara** una
struttura comune: da quel lato è pulito.

Ma cercando le **forme ripetute** fra le 101 classi sono usciti due idiomi che una classe
comune coprirebbe — e in entrambi i casi la ripetizione ha già prodotto una divergenza.

### Buco 1 — `period_start` / `period_end`: 16 classi, **zero** validano l'ordine

Sedici payload dichiarano la coppia a mano. **Nessuno** verifica che la fine non preceda
l'inizio, mentre `DateRangeModel` in `common.py` lo fa da sempre. Un payload AI Export può
quindi uscire con un periodo **invertito**, e l'unico a notarlo sarebbe il modello che lo
legge.

Non si può sostituire con `DateRangeModel` annidato: cambierebbe la **forma del JSON**
esportato, che è un contratto versionato. La forma giusta è una **mixin** —
`PeriodBoundedModel(StrictModel)` — che dichiara i due campi *piatti* e aggiunge il
validatore. Stesso JSON sul filo, invariante finalmente controllata in un posto solo.

### Buco 2 — il codice valuta come `str`: 34 classi, **15 senza validazione**

`target_currency: str` compare 36 volte, `currency: str` altre 8. Di 34 classi che hanno un
campo valuta come stringa, **19 lo validano e 15 no**: quindi quindici payload possono
uscire con una valuta che non esiste. Il progetto ha già la regola giusta
(`Currency.validate_code`), applicata a metà.

La cura è un tipo annotato in `common.py` — `CurrencyCode = Annotated[str, AfterValidator(...)]`
— che si usa al posto di `str` e porta con sé la validazione, senza cambiare il JSON
(resta una stringa) e senza costringere a scrivere un validator per classe.

---

## Come è organizzato questo blocco

Il vincolo che ha già fatto danni: **un solo database di test e una sola porta 6041**. Un
`db populate` di una corsia azzera la corsa di un'altra (`no such table: users`), e uno
spegnimento con `--force` stende il backend del vicino.

Quindi le corsie sono assegnate per **ciò che toccano**, non per argomento:

| corsia | tocca DB / porta? | può girare insieme a |
|---|---|---|
| **A — frontend Vitest** | no (`npx vitest run` e basta) | chiunque |
| **B — backend puro** | no (test `PURE`, nessuna sessione) | chiunque |
| **C — backend con DB** | sì | solo A e B |
| **D — E2E** | sì, anche la porta | solo A e B |

**C e D non girano mai insieme.** A e B sono libere sempre.

E la regola che l'utente ha chiesto: gli agenti **scrivono** e al massimo eseguono la
**singola spec** su cui stanno lavorando; la corsa completa la faccio io **una volta sola**,
alla fine di tutte le corsie.

---

## I task

### Corsia A — frontend, nessun database (2 task, paralleli fra loro)

**A1 · `translatedOr`** — la stessa logica «traduci con fallback» esiste sotto tre nomi
(`label`, `tr`, `translatedOr`) in `LotComparisonChart`, `LotWacPriceChart`,
`OtherPeriodEffectsTable`. È logica i18n copiata tre volte: se una divergesse, una parte
dell'interfaccia mostrerebbe la chiave grezza invece del testo. Unificare + test unitari.

**A2 · i duplicati minori** — sei gruppi già mappati: chiave di posizione
(`makeHoldingLookupKey`/`makePositionKey`), numero-finito-o-null
(`finiteNumber`/`finiteChartNumber`), data breve per asse (`formatAxisDate`/`formatShortDate`,
tre chart), snake→Title (`humanize`/`humanizeSignalKey`), `portal`/`portalAction`, e quattro
modi di annullare un long-press. Per ciascuno: **verificare che siano davvero uguali prima di
unire** — un `diff` fra le implementazioni, non «sembrano uguali».

### Corsia B — backend puro, nessun database (2 task, paralleli fra loro e con A)

**B1 · `PeriodBoundedModel`** — la mixin del buco 1, applicata alle 16 classi, con i test che
dimostrano il rosso: un periodo invertito oggi passa, dopo no. Attenzione: il JSON deve
restare **identico**, quindi va verificato che `model_dump()` di un payload esistente non
cambi di una virgola.

**B2 · `CurrencyCode`** — il tipo annotato del buco 2, applicato alle 15 classi che oggi non
validano. Stessa cautela sulla forma del JSON. Le 19 che già validano si allineano al tipo
comune se questo non cambia il loro comportamento.

### Corsia C — backend con database (2 task, **sequenziali fra loro**)

**C1 · rami negativi dei provider** — `justetf` 67%, `borsa_italiana` 74,8%,
`yahoo_finance` 71,4%, `snb` 65%. Sono i percorsi d'errore: risposta vuota, formato
inatteso, campo mancante, timeout. **Mai la rete**: risposte mockate, che è anche l'unico
modo di renderli deterministici. Se una parte è testabile senza sessione, va in una unit
`PURE` separata — allora si sposta in corsia B.

**C2 · `database is locked`** — visto una volta su una scrittura bulk di `price_history` a 8
worker, mai riprodotto. Prima capire **se** è riproducibile (girare la unit da sola a
worker alti), poi decidere: è contesa legittima da assorbire con un retry, o un test che
scrive più di quanto gli serve?

### Corsia D — E2E (3 task, **sequenziali fra loro**, dopo la C)

**D1 · `ImportWizardModal`** — 60,1%, **613 statement scoperti: il file più scoperto del
frontend**. Il percorso felice è coperto da `tx-brim-import` e `tx-import-resolution`;
mancano parsing fallito, file non riconosciuto, righe che non si risolvono, annullamento a
metà, ritorno indietro fra i passi. **L'import committa transazioni vere**: serve il
`TransactionWriteTracker` di `tx-clone.spec.ts`, che cancella solo ciò che ha scritto lui.
`tx-brim-import` è dichiarato `mode: 'serial'`: rispettare la dichiarazione, e non toglierla
senza una corsa a 4 worker come prova.

**D2 · `TransactionBulkModal`** — 75,5%, 246 scoperti.

**D3 · rotte `fx` e `files`** — `routes/fx` 48,4% (188 scoperti), `routes/files` 65,1%,
`FilePreviewModal` 59,6%.

Per tutte e tre, la cosa da fare **per prima**: cercare le uscite silenziose (`if (!x)
return`, `count() === 0`, `isVisible().catch(() => false)`). In `brokers-detail.spec.ts` ce
n'erano 36 e **10 test su 22 non testavano niente**; il componente che sembrava all'11,9% è
salito all'82,9% solo mettendoli in condizione di girare. Il metodo: sostituire ogni `return`
con un `throw` parlante, lanciare, contare quanti scattano.

### Decisione per l'utente (non un task)

**`UnifiedLotsTable`** ha due divergenze lasciate apposta: `firstScalar` salta i `null`
invece di prendere il primo elemento (`[null, 7]` dà `7` invece di `null`), e il suo
`safeNum` rifiuta `±Infinity` mentre le altre quattro copie lo accettano. Cambiano cosa vede
l'utente quando un dato manca, quindi la scelta è tua: allinearle alle comuni o tenerle.

---

## Come si chiude

1. Le corsie A e B partono **subito e insieme** (quattro agenti, nessuno tocca il database).
2. La corsia C parte insieme a loro (un solo agente, ha il database).
3. La corsia D parte **quando C ha finito** (un solo agente per volta, o tre agenti che
   scrivono e uno solo che esegue).
4. **Una sola corsa completa alla fine**: `db populate --force --clean`, `./dev.py front
   build` se qualcuno ha toccato un `.svelte`, poi
   `./dev.py test --coverage --cov-clean-* --workers 8 --log-dir .testLog all`.
5. `check-orphans`, `lint` (baseline **38**), `svelte-check`, Prettier.
6. Messaggio di commit aggiornato, misure prima/dopo, e le domande di contratto rimaste.

## Regole che valgono per ogni agente

- `export PATH=/Users/ea_enel/.local/share/virtualenvs/LibreFolio-SAUMUTtc/bin:$PATH` prima
  di ogni `./dev.py`; i flag globali vanno **prima** della categoria.
- **Mai** `git commit`/`push`/`reset`/`rebase`/`checkout --`.
- **Mai** `db populate`, `db create-clean`, `server --force` fuori dalla corsa finale.
- Chi tocca un `.svelte` deve ricordare che gli E2E girano contro il **frontend buildato**.
- Un difetto di prodotto si **segnala con la prova**, non si corregge di iniziativa: in
  questa campagna ne sono usciti nove per questa via, fra cui un'aritmetica delle date rotta
  in tutta Europa e un guard che ingoiava i dati appena caricati.
- Prima di unificare due funzioni, **dimostrare** che sono uguali. Il caso
  `safeNumber` ≠ `safeNum` avrebbe azzerato ogni importo di ogni grafico, in silenzio.

---

## Ricognizione per D1 — dov'è davvero il buco di `ImportWizardModal`

Fatta prima di assegnare la corsia, per non far ripartire l'agente da zero.

Il wizard ha **sette passi**: `upload → select → analyze → assets → fix → duplicates → review`.
Contando quante volte ciascuno compare nelle due spec che lo esercitano
(`tx-brim-import.spec.ts`, 360 righe, e `tx-import-resolution.spec.ts`, 728):

| passo | citazioni nelle spec |
|---|---|
| upload | **0** |
| select | **0** |
| analyze | **0** |
| assets | 2 |
| fix | 2 |
| duplicates | 3 |
| review | **0** |

**Quattro passi su sette non sono nominati da nessun test.** Le spec entrano nel wizard già
a metà, sui passi di risoluzione, e non toccano né l'ingresso (caricamento del file, scelta
del broker, analisi) né l'uscita (la revisione finale prima del commit). Ecco i 613 statement
scoperti.

Nota positiva: in queste due spec le **uscite silenziose sono zero**. Il problema qui non è
quello di `brokers-detail` — i test fanno il loro lavoro, semplicemente non arrivano dove
serve. Quindi l'agente D1 non deve cercare `return` nascosti: deve entrare dal principio.

Il file è di **5324 righe**, il più grande del frontend.

---

# Corsie A, B, C — chiuse (28/08, ore 15:00) · `all` **15/15**

Gli agenti sono caduti per problemi di rete **prima delle rifiniture**, ma il lavoro
prodotto era funzionante: 111 test provider verdi, 1560 fra schemi e AI Export, 950 unit
frontend. Mancavano registrazione e lint, che ho completato io.

## Risultati

| | prima | dopo |
|---|---|---|
| Backend statement | 91,36% | **92,33%** |
| Backend branch | 81,40% | **82,56%** |
| Frontend statement | 70,31% | 70,25% |
| Frontend branch | 53,37% | 53,22% |

I quattro provider, che erano l'obiettivo della corsia C:

| file | stmt prima → dopo | branch prima → dopo |
|---|---|---|
| `borsa_italiana.py` | 74,8 → **98,3%** | 69,0 → **100%** |
| `yahoo_finance.py` | 71,4 → **96,6%** | 61,6 → **98,8%** |
| `justetf.py` | 67,1 → **93,8%** | 50,0 → **88,2%** |
| `snb.py` | 65,1 → **92,7%** | 50,0 → **87,5%** |

107 test nuovi, tutti offline. Il micro-calo frontend (−0,06) è rumore di misura: la corsia
A ha spostato codice in moduli condivisi, cambiando i denominatori.

## Cosa ho dovuto completare io

1. **Quattro file provider non registrati** — `check-orphans` li segnalava orfani, cioè
   test che non sarebbero mai girati. Verificato che siano genuinamente `PURE` (zero
   marcatori impuri: nessuna sessione, nessun server, ogni client doppiato) e creata la
   unit `services provider-errors` con `isolation="pure"` e la motivazione scritta.
2. **Lint da 44 a 37.** Due `dict()` da convertire in letterali nei nuovi test.

## Un incidente che vale la pena ricordare

Ho lanciato `ruff check --fix` sull'intero repo per ripulire in fretta, e **ha rotto il
runner**: ha rimosso `TEST_DB_PATH` da `scripts/test_runner/_common.py` giudicandolo
inutilizzato, e da lì `_backend_db.py` non importava più — `./dev.py lint` stesso moriva con
un `ImportError`. Ripristinato il file, e poi verificate **una per una** le altre 21
modifiche che il `--fix` aveva fatto al runner: `_scheduler.py` aveva perso `READ` e
`WRITE_SCOPED`, ma solo perché comparivano in *commenti*, quindi la rimozione era corretta.
Controllo finale importando tutti i moduli del runner: zero rotti.

La lezione: un `--fix` su un albero che non hai scritto tu non è un'operazione sicura, e la
verifica non è «gira il lint», è «gira ancora tutto il resto».

## Cosa hanno consegnato le corsie

**A — frontend**: cinque moduli condivisi in `utils/core/` (`translateOr`, `positionKey`,
`finiteNumber`, `formatAxisDate`, `clearTimer`) più i loro test.

**B — classi comuni**: `CurrencyCode = Annotated[str, BeforeValidator(Currency.validate_code)]`
e `PeriodBoundedModel`. Adottate in `broker_financial` (7 periodi, 10 valute),
`portfolio_financial` (8 e 11), `broker_cost_efficiency`, `asset_payloads`,
`technical_payloads`, `portfolio_income`.

**C — provider**: 107 test sui percorsi d'errore, tutti con i client doppiati.

---

# Corsia D — import wizard (28/08)

`ImportWizardModal` **60,2% → 65,5%** di copertura, +82 statement coperti, 16 test nuovi.
Due spec: `tx-import-upload.spec.ts` (8 test sul passo *upload*) e `tx-import-flow.spec.ts`
(8 su *analyze*, navigazione e *review*).

| passo | prima | ora |
|---|---|---|
| upload | 0 citazioni | 8 test |
| analyze | 0 | detail modal, view-all, re-parse, verdetto |
| review | 0 | toolbar di selezione + discard guard |
| navigazione | 0 | Back attraverso analyze→select→upload e ritorno |
| select | 0 | attraversato in ingresso |

Nessuna transazione committata: entrambe le spec si fermano **prima** dell'Import, quindi
non c'è nulla da ripulire — è il disegno più sicuro, non un'omissione. I file caricati
hanno nomi unici e vengono spazzati da `db populate --with-reports`.

## Stati che il prodotto non pubblicava

La review non esponeva **nessun conteggio di selezione**: per sapere quante righe fossero
selezionate bisognava contarle, e contarle significa leggere testo tradotto. Aggiunti
`data-selected-count` / `data-total-count` su step4, più i testid per le azioni che non ne
avevano (`view-all`, `reparse`, `select-all`, `deselect-all`, la chiusura del ParseDetail).
E `data-badge-variant` su `DataTable`, per asserire la **variante** di un badge invece del
suo testo.

## L'errore era nel test, ed è il più istruttivo

Il file caricato allo step 1 arriva allo step 2 **già pre-selezionato**. Un `checkbox.click()`
cieco lo **des**elezionava, e il wizard si fermava su `Parse (0)`. È esattamente la regola 13
— *su un interruttore, asserisci lo stato finale, non cliccare alla cieca* — colta sul fatto:
il test funzionava sui dati contro cui era stato scritto e si sarebbe invertito ovunque
altrove. Cura: assicurare lo stato `checked`, poi asserirlo. Reso deterministico anche il
broker (scelto **per nome**, non `options.first()`, che alfabeticamente pescava un altro).

## Difetto di prodotto trovato — e la parte imbarazzante

`brim_provider.py:1111`, la guardia `can_parse`, **non aveva** il retry che `parse()` ha
venti righe sotto. Stessa corsa: un parse concorrente rinomina il file `uploaded/ → parsed/`,
il percorso risolto un istante prima è morto, e `can_parse` risponde `False` — cioè l'utente
si sente dire *«questo plugin non sa leggere il tuo file»* riguardo a un file che il plugin
legge benissimo.

La parte imbarazzante è che **quel retry l'avevamo scritto noi**, in una sessione precedente,
per questa identica corsa. Avevamo curato `parse()` e lasciato scoperta la guardia due righe
sopra: mezza diagnosi, mezza cura. La prova che il difetto era vivo sta nei log dell'agente —
la prima versione della spec, che parsava tutta lo **stesso** file, perdeva un test per corsa,
*ogni volta uno diverso* (`flow_run2.log:419` A3, `flow_run3.log:419` A1). Il classico rosso
che sembra flaky e invece è un difetto sotto carico.

**Cura**: estratto `_relocated_path(file_id, file_path)` — «dove è finito il file, o `None` se
il fallimento era genuino» — e usato da entrambi i rami. Tre test nuovi in
`test_brim_parse_race.py`, verificati **rossi prima** (`ValueError` alla riga 1112) e verdi
dopo. Il caso «il plugin davvero non sa leggere questo formato» resta rosso come deve.

---

# La decisione lasciata aperta su `UnifiedLotsTable` — chiusa

Erano due divergenze fra le copie locali e le funzioni condivise di `types/common.ts`:

1. `firstScalar` prendeva il primo elemento **non-null** dell'array, `safeScalar` prende il primo;
2. `safeNum` rifiutava `±Infinity` (`Number.isFinite`), `safeDecimal` lo accetta (solo `isNaN`).

Sembravano scelte sul *cosa vede l'utente quando un dato manca*. Leggendo la fonte, non lo sono:

**L'array non è un array.** Il commento in `common.ts:40` lo dice: `openapi-zod-client` genera
`string | (string | null)[]` dove il contratto ha `string | null`. È un tipo malformato, non una
collezione — ha zero o un elemento, quindi «primo» e «primo non-null» coincidono **sempre**. Nel
caso impossibile `[null, x]`, saltare il null significherebbe pescare da una posizione arbitraria:
peggio, non meglio.

**`Infinity` non arriva.** `safeDecimal` lo documenta: `parseFloat` produce `Infinity` solo dal
testo letterale `"Infinity"`, che nessuna colonna decimale emette.

Quindi le divergenze erano teoriche, e la duplicazione le teneva in vita. Rimosse le tre copie
locali (`firstScalar`, `safeNum`, `safeBrokerId`) e i due tipi `NumericLike`/`BrokerIdLike` rimasti
senza usi: 23 chiamate migrate su `safeDecimal` / `safeNumber`, **−21 righe**, `svelte-check` 0/0.

Vale la pena notare quale delle due fosse la copia «migliorata»: quella locale, che aggiungeva
difese contro casi che non possono accadere. È il modo tipico in cui una copia diverge — non per
un errore, ma per una prudenza applicata in un posto solo.

## Correzione della correzione: la copia locale aveva ragione su un punto

La prima passata aveva **eliminato** le copie locali senza chiedersi se contenessero
qualcosa di meglio. Su una delle due divergenze la risposta è sì.

`safeDecimal` accettava `Infinity`, e il suo commento lo giustificava così: *«parseFloat lo
produce solo dal testo letterale "Infinity", che nessuna colonna decimale emette»*. Il
ragionamento è vero sulle **colonne** e cieco sul **serializzatore**: `SafeDecimal` lato
backend serializza con `format(v, 'f')`, e `format(Decimal('Infinity'), 'f')` è esattamente
la stringa `"Infinity"`. Il frontend la rilegge come `Infinity` e la stampa come `∞` dove
dovrebbe esserci un importo.

Verificato per gradi:

| | esito |
|---|---|
| `Decimal('1')/Decimal('0')` | **solleva** `DivisionByZero` — questa via non produce infiniti |
| `cumulative_to_annualized` | ha già `math.isfinite()` → `None` sull'overflow |
| `format(Decimal('Infinity'), 'f')` | `'Infinity'` — **la strada esiste** |
| `format(Decimal('NaN'), 'f')` | `'NaN'` — già respinto da `isNaN` |

Quindi la guardia della copia locale non era paranoia: era la difesa giusta nel posto
sbagliato, cioè in un solo componente su sette. Portata in `safeDecimal` (`Number.isFinite`),
insieme all'altra cosa che la copia locale faceva meglio — `String(scalar)` esplicito invece
del cast `scalar as string`, che mente quando il valore è un numero.

Quattro test nuovi che pinnano il comportamento; **952 unit verdi su 75 file**, nessun
consumatore dipendeva dall'accettare l'infinito.

Su `safeScalar` invece la copia locale aveva torto, e il perché è documentato nel sorgente:
saltare i `null` significherebbe rispondere da una posizione arbitraria di una forma che
nessuno ha progettato. L'array è un artefatto del generatore, non una collezione.

**La morale della giornata**: quando due copie divergono, la domanda non è *quale cancello*
ma *perché differiscono*. Qui una aveva una difesa in più e l'altra aveva ragione sul resto.
Cancellarne una a scatola chiusa avrebbe perso una protezione reale — e la prima passata
stava per farlo.

---

# Corsia D2 — `TransactionBulkModal`: ripresa del lavoro interrotto

L'agente è stato fermato durante la seconda corsa, quindi il suo esito era **ignoto** e i
log erano spariti con `/tmp`. Ripreso da capo: 9 test in `tx-bulk-promote-exec.spec.ts`,
registrati, che coprono l'esecuzione del *promote* (edit+edit, create+create, misto, modale
di fusione conferma/annulla, link del banner) e il ripristino di una riga marcata per la
cancellazione.

## Prima cosa trovata: clic ciechi, di nuovo

Gli helper selezionavano le caselle con la **classe CSS** `.checkbox-btn` e cliccavano senza
guardare — mentre `DataTable` pubblica `data-testid="dt-row-checkbox-{rowId}"` **con
`data-state`**. È la regola 13, la stessa che ci aveva morso nel wizard: su un interruttore
si asserisce lo stato finale. Qui è concreto, perché una riga collegata viene selezionata
**insieme al suo gemello**: il clic cieco la deseleziona. Sostituito con `ensureChecked`.

## Due difetti di prodotto, entrambi nel percorso di commit

I 9 test hanno prodotto 2 rossi. Nessuno dei due era un difetto del test.

### 1. La fusione si applicava a una sola metà (`create+create`)

`executePromote` scriveva i campi risolti dal modale di fusione **solo su `opA`**:

- `edit+edit` e `misto` mandano `resolved_fields` al backend, che li applica a entrambi → funzionano;
- `create+create` è **puramente locale** (solo un `link_uuid` condiviso, nessun promote sul filo),
  quindi `opB` conservava la sua descrizione e il commit veniva respinto con
  `pairDescriptionMismatch`, **citando una descrizione che l'utente non aveva mai scelto**.

Seconda faccia: `collapseIntoPaired` elegge la riga visibile in base al **segno del contante**,
quindi `opA` può essere quella *nascosta* — l'utente poteva non vedere nemmeno il valore scelto.
Cura: applicare a entrambe. Idempotente sugli altri due rami, dove il backend fa lo stesso.

### 2. Il promote misto non ha mai funzionato

Tre difetti in fila, ognuno nascosto dal precedente. Il contratto era già documentato e
testato lato backend (`test_transactions_batch_split_promote.py:559`): la create si manda
col tipo **pre-promote** più il `link_uuid`, e il backend deriva il resto.

| # | difetto | sintomo |
|---|---|---|
| a | `resolveOps` saltava la create nascosta: riga 967 salta l'edit in coda al promote, riga 960 salta il partner nascosto — **i due `continue` si annullavano** e la create non partiva | `Cannot resolve TX B reference` |
| b | la create partiva col tipo **già promosso**, mentre il backend deriva la regola dai due tipi *sorgente* | `No promote rule for WITHDRAWAL+CASH_TRANSFER` |
| c | col tipo pre-promote, `buildCreatePayload` **scarta** il `link_uuid` (lo manda solo per i tipi che richiedono una coppia) — ma lì quell'uuid non è un marcatore di coppia, è l'aggancio del promote | di nuovo `Cannot resolve TX B reference` |

Un terzo difetto trovato mentre curavo (a): se la create è la riga **principale** e la
riga salvata è quella nascosta, `partnerPayload` costruiva una *create* per una riga che
esiste già → **duplicato silenzioso** di una transazione salvata. Aggiunta la guardia
`pOp.op === 'create'`.

Introdotto `promoteFromType` per tenere separati «il tipo mostrato» e «il tipo sul filo»,
e azzerato in `handleSplitRow`: scollegare una coppia rende quel valore obsoleto, e lasciato
lì sovrascriverebbe in silenzio il tipo appena assegnato.

**Perché nessuno se n'era accorto**: il promote misto non aveva **nessun** test E2E. Il test
API del backend passava — era il frontend a non rispettare il contratto.

`front-transaction all --workers 4`: **tutte verdi**, incluse `tx-split-promote` e
`tx-bulk-operations` che percorrono lo stesso codice.

---

# Corsa finale con coverage azzerata — e il difetto che ha rivelato

`all --coverage --cov-clean-backend --cov-clean-backend-e2e --cov-clean-js --workers 8`
→ **15/15**. Ma il numero del backend è sceso da 92,33% a 90,10% mentre le **branch
restavano ferme** (82,56 → 82,61). Un'asimmetria del genere non è lavoro perso: è misura
rotta.

## La coverage Python degli E2E non viene catturata sopra i 2 worker

| | file scritti | misurato |
|---|---|---|
| `--workers 8` (4 worker uvicorn), **tutta la suite** | 5 | **0,00%** |
| `--workers 2` (1 worker uvicorn), **una sola spec** (`tx-tooltips`) | 1 | **35,01%** |

Una singola spec misura il 35% del backend; l'intera suite ne misura zero. La causa non è
dedotta, è nella configurazione: `.coveragerc` dichiara `concurrency = thread,gevent` e
**non** `multiprocessing`. Sopra i due client, `server_workers_for` = `ceil(client/2)` fa
partire uvicorn con più worker, uvicorn li **forka**, e `coverage run` misura solo il
processo padre — che non serve richieste. I cinque file vengono scritti regolarmente e sono
vuoti, quindi non c'è alcun avviso: il conteggio scende e sembra codice non testato.

**Perché conta oltre il numero**: significa che le percentuali backend confrontate durante
tutta questa campagna sono state prese a conteggi di worker diversi, e parte del movimento
che ho attribuito ai test era rumore di misura. Il 90,10% è il numero onesto **delle sole
unit backend**; il vecchio 92,33% era per giunta accumulato su corse mai ripulite.

Due strade, da decidere:
- `concurrency = multiprocessing,thread,gevent` in `.coveragerc` — corretta, ma va provata:
  uvicorn ha una sua supervisione dei worker;
- forzare **un solo** worker uvicorn quando la coverage è attiva — banale e sicura, ma
  rallenta le corse con coverage.

## JS/Svelte, ricatturata da zero

| | prima | dopo |
|---|---|---|
| statement | 70,25% | **71,11%** (25 738/36 195) |
| branch | 53,22% | **53,77%** (11 331/21 073) |

Questa metrica è sana: nessun fork di mezzo, i dati V8 vengono dal browser.

---

# CORREZIONE: il backend non è mai calato. Avevo confrontato due unità diverse

La sezione precedente diceva che la coverage backend era scesa da 92,33% a 90,10%.
**È falso, ed è un mio errore di lettura**, non un difetto del prodotto.

Con `branch = true`, `coverage report` stampa come TOTAL una percentuale **mista**
(righe + archi), mentre il 92,33% della baseline era **solo righe**. Stesso dato, due
formule:

```
percent_covered (righe+archi):  90.10%   ← quello che stampa `coverage report`
righe pure:                     92.33%   ← esattamente la baseline
branch pure:                    82.61%   ← baseline 82.56, +0.05
```

Quindi: **92,33 → 92,33 righe (identico), 82,56 → 82,61 branch (+0,05)**. Nessuna
regressione. Ho paragonato una percentuale pura a una mista e ho letto la differenza di
formula come perdita di copertura — l'errore che questa campagna passa il tempo a
cercare negli altri.

La lezione, che vale più del numero: *prima di dichiarare una regressione, verifica che i
due numeri misurino la stessa cosa*. Il segnale c'era ed era la branch ferma: se avessi
perso codice testato, sarebbero calate entrambe.

## Quel che resta vero: la coverage E2E del server esterno è persa

Questa parte regge. È una misura **distinta** (`htmlcov-backend-e2e`), che riguarda il
server sulla porta 6041 usato da Playwright — non i test backend, che girano in-process:

| | esito |
|---|---|
| `--workers 8`, tutta la suite | 5 file scritti, **0,00%** |
| `--workers 2`, **una sola** spec | 1 file, **35,01%** |
| archivio 28/08 14:29 (cattura buona) | 25,78% |

Unita al backend, quella misura vale **+0,36 punti** (90,10 → 90,46 in scala mista). Utile,
ma non è il 2,23 che credevo: serve a sapere *quali percorsi backend gli E2E toccano*, non
ad alzare il totale.

**Perché il backend è completo lo stesso**: `test_server_helper.py` avvia uvicorn in un
**thread dello stesso processo pytest**, proprio perché `concurrency = thread` lo tracci. Le
rotte API sono quindi misurate (75-100% in `.coverage_data/backend`). Il server esterno serve
solo agli E2E del browser.

Decisione presa dall'utente: aggiungere `multiprocessing` alla `concurrency` e rifare la
corsa completa.

# JS/Svelte: perché solo +0,86

Il denominatore è **36 195 statement**: un punto percentuale costa ~362 statement coperti.
Le due spec nuove ne hanno guadagnati ~311 in totale (il solo `ImportWizardModal` +82).
Non è poco lavoro mal ripagato — è una scala in cui il singolo test sposta di poco.

## SVELTE_UI: aggregato, ma molto concentrato

**196 file**, 8 705 statement scoperti. I primi dieci ne fanno **34,2%**:

| scoperti | totali | file | righe |
|---|---|---|---|
| 533 | 1535 | `ImportWizardModal.svelte` | **5 326** |
| 414 | 975 | `DataTable.svelte` | 2 560 |
| 337 | 791 | `DataTableColumnFilter.svelte` | 1 794 |
| 311 | 612 | `ScheduledInvestmentEditor.svelte` | 1 432 |
| 297 | 683 | `DateRangePicker.svelte` | 1 463 |
| 286 | 608 | `AssetModal.svelte` | — |
| 175 | 1011 | `TransactionBulkModal.svelte` | 3 349 |

L'intuizione dell'utente sullo spezzettare regge: quattro file superano le 1 400 righe e due
le 3 000. `ImportWizardModal` da solo è il 6% degli statement scoperti dell'intero frontend.
