# Rami, non righe — e file abbastanza piccoli da poterli testare

Storico precedente: `files/plan-storico-fase012.md`.

## Il problema, misurato

Il frontend non ha poca copertura: ha copertura **superficiale**.

| | statement | branch | forbice |
|---|---|---|---|
| Backend | 92,39% | 82,64% | 9,8 pp |
| **Frontend** | 69,84% | **53,75%** | **16,1 pp** |

**10 591 rami scoperti.** Ogni componente è attraversato dal percorso felice; i rami di
errore e di caso limite non sono percorsi. È anche il motivo per cui inseguire le *righe* ha
mosso il numero di un punto in una notte: una riga in più costa un test, un ramo in più costa
spesso **lo stesso test scritto meglio** — lo stesso montaggio con una prop diversa.

### Che tipo di rami sono

| tipo | scoperti | totali | |
|---|---|---|---|
| `IfStatement` | **5 282** | 10 548 | logica vera, il bersaglio |
| `LogicalExpression` | 3 253 | 7 852 | `&&`, `\|\|`, `??` — misti |
| `ConditionalExpression` | 1 887 | 4 043 | ternari, spesso stati di rendering |
| `SwitchStatement` | 143 | 285 | |
| `AssignmentPattern` | 26 | 169 | default di parametri |

**Buona notizia: `try/catch` non genera rami in istanbul.** Il problema che ci ha fatto perdere
tempo nel backend — inseguire `except` irraggiungibili — qui non si ripresenta.

**Cattiva: `LogicalExpression` sì.** Un `x ?? []` che non scatta mai è un ramo scoperto per
sempre, ed è esattamente il difensivo che non va inseguito. Regola operativa: **si insegue un
ramo solo se si sa descrivere lo stato dell'utente che lo percorre.** Se la frase non viene,
il ramo è difensivo e si lascia — annotandolo, non fingendo.

---

## Fase 1 — Fattorizzare gli helper duplicati. Da fare per prima, e da sola.

Tocca molti file in molte aree, quindi **non può girare in parallelo con le corsie**: si fa
prima, si verifica, e poi le corsie partono da un albero stabile.

| helper | copie | note |
|---|---|---|
| `formatDate` | **9** | |
| `handleClickOutside` | **9** | |
| `setupResizeObserver` | **8** | |
| `parseNumber` | 5 | |
| `formatPercent` | 5 | ⚠️ **due semantiche diverse** |
| `renderChart` | 12 | struttura comune, non corpo comune |

### L'avvertimento che vale tutta la fase

`formatPercent` **non è una funzione in cinque copie**:

```ts
// LotWacPriceChart, LotComparisonChart — riceve una PERCENTUALE (0-100)
return `${sign}${normalized.toFixed(2)}%`;

// LotCustodyModal, RiskAnalysisPanel — riceve una FRAZIONE (0-1)
return `${sign}${(parsed * 100).toFixed(2)}%`;
```

Unificarle alla cieca **moltiplica o divide per 100 i valori che l'utente legge**. È lo stesso
identico tranello di `safeNumber` contro `safeNum`, che in questa campagna ha già rischiato di
azzerare ogni importo di ogni grafico.

**Ma la differenza non è un motivo per tenere due funzioni: è un parametro mancante.** Chi
chiama sa in che scala è il proprio numero — è l'unico a saperlo — quindi lo dice:

```ts
/** @param scale moltiplicatore applicato prima di formattare: 1 se il valore è
 *  già una percentuale, 100 se è una frazione. */
export function formatPercent(value: X, {scale = 1} = {}): string
```

`formatPercent(v)` per i grafici dei lotti, `formatPercent(v, {scale: 100})` per il pannello
di rischio. Una funzione sola, nessuna ambiguità sul posto di chiamata, e riusabile per la
terza scala che prima o poi arriverà.

### Il principio, che vale oltre questo caso

> Quando due copie divergono per **una scelta che il chiamante conosce**, la differenza
> diventa un **parametro con un default sensato** — non due funzioni, e non un'unificazione
> che ne sacrifica una.

Quando invece divergono per **prudenza applicata in un posto solo** (una guardia in più, come
`Number.isFinite` in `safeDecimal`), la guardia si tiene per tutti. E quando divergono perché
fanno davvero **due cose diverse**, restano due funzioni con nomi che lo dicono.

Ogni corsia applica questa griglia prima di unificare qualsiasi cosa, leggendo i **corpi** e
non i nomi.

---

## Fase 2 — Scorporare i file grandi, e testarli mentre li si apre

24 file superano le 1 000 righe. I cinque che contano:

| file | righe | rami scoperti | copertura rami |
|---|---|---|---|
| `ImportWizardModal.svelte` | **4 927** | **752** | 34,3% |
| `TransactionBulkModal.svelte` | **3 349** | 263 | 67,2% |
| `DataTable.svelte` | **2 560** | 339 | 44,1% |
| `AssetModal.svelte` | **2 352** | 369 | 38,7% |
| `TransactionFormModal.svelte` | **2 260** | 165 | 66,8% |

**Lo scorporo non alza la copertura: rende raggiungibile ciò che oggi non lo è.** La prova è
già in casa — i quattro moduli estratti dal wizard stanno al **100%**, il `.svelte` residuo al
57,5%. Non perché siano stati testati meglio, ma perché prima vivevano dentro closure
raggiungibili solo attraversando sette passi in ordine.

Il criterio: **estrarre ciò che è funzione di input e produce output** (validazione,
riconciliazione, costruzione di payload, formattazione, aritmetica), lasciare nel `.svelte` il
markup e il collegamento agli eventi. Non spezzare per fare numero.

### Solo la logica, ma con l'inventario del markup

**Deciso: in questa campagna si scorpora solo la logica.** Spezzare il markup in
sotto-componenti toccherebbe il rendering, e ogni errore lì si vede a schermo — è un rischio
che non serve prendere mentre si insegue la copertura.

Però ogni corsia, mentre apre il suo file, **annota i blocchi di markup che vede ripetersi**
in `LibreFolio_developer_journal/Release_2/render-components-index.md`: che cos'è, in quali
file compare, cosa avrebbe in comune. Alla fine avremo una mappa costruita leggendo il codice
vero invece che immaginandola, e la fattorizzazione del rendering diventerà una decisione
informata invece di una scommessa.

L'indice sta nel repo, non nella sessione, perché deve sopravviverle.

### Le corsie, parallele per costruzione

Ognuna tocca la propria cartella e nient'altro. I component test girano in Vitest+jsdom:
niente database, niente porta 6041.

| corsia | area | rami scoperti | perché |
|---|---|---|---|
| **A** | `brokers/lots` | **710** | **mai toccata da nessuna corsia**; `LotWacPriceChart` 284, `LotComparisonChart` 269, `LotGanttChart` 157 |
| **B** | `transactions/modals` | **1 180** | i tre modali giganti: scorporo + rami |
| **C** | `assets` | **725** | `AssetModal` 369, `ScheduledInvestmentEditor` 203, `ProviderAssignmentSection` 153 |
| **D** | `table` | **545** | `DataTable` 339, `DataTableColumnFilter` 206 |
| **E** | rotte | **647** | `assets/[id]` 268, `fx/[pair]` 132, `assets` 129, `transactions` 118 — E2E |
| **F** | `charts` + `risk` | **323** | `PriceChartFull` 203, `RiskAnalysisPanel` 120 |

`brokers/lots` per prima: è l'unica area che nessuna corsia ha mai guardato, ha la copertura
di rami più bassa fra le grandi, e i suoi tre grafici condividono `formatPercent`,
`parseNumber` e `setupResizeObserver` — cioè è anche il posto dove la Fase 1 si verifica sul
campo.

---

## Fase 3 — I due spec distruttivi, in seriale

`files/+page.svelte` (115 righe, 125 rami) e `fx/[pair]/+page.svelte` (145 righe, 132 rami)
restano scoperti perché i percorsi residui **cancellano** file, coppie e tassi che ogni altro
test legge.

La soluzione è quella indicata: **uno spec dedicato, `mode: 'serial'` con la motivazione
scritta, che chiama `db populate --force --with-reports` come ultima operazione.** Il runner
ha già `_ensure_db_populated`, e la fixture `txHygiene` ripopola da sé quando rileva id
spariti — quindi il meccanismo esiste, va solo dichiarato.

Va in fondo perché è l'unico blocco che non può girare accanto agli altri.

---

## Cosa resta aperto e va chiuso qui

1. **Il residuo del difetto di misura.** Restano **1 403 righe fantasma** su 78 file: la doppia
   compilazione produce insiemi di righe eseguibili diversi, e la cura per riga ha ridotto il
   problema senza estinguerlo. Col denominatore giusto la copertura è **75,29%**, non 74,81%.
   Da valutare: prendere per ogni file la mappa più ricca invece dell'unione.
2. **`coverage-report --lang js` classifica per statement**, cioè la metrica che il difetto
   gonfia. Va portato a classificare per **rami scoperti**, che è la domanda vera.
3. **Il report HTML titola «83%»**, che è la metrica *Bytes* — la più generosa delle cinque che
   pubblica. Vale la pena rendere esplicito nel nostro strumento quale numero stiamo citando.

---

## Definizione di fatto

Per ogni corsia:

- copertura **di rami** prima e dopo, per file, stesso metodo;
- ogni ramo lasciato scoperto di proposito è **annotato con la ragione** (difensivo,
  irraggiungibile, appartiene a un altro componente);
- i blocchi di markup ripetuti che si incontrano finiscono **nell'indice**
  (`render-components-index.md`), anche quando non si tocca il rendering;
- nessuna asserzione su testo tradotto, classi CSS o geometria;
- `check-orphans` pulito, prettier pulito, `svelte-check` 0/0;
- nessun commit.

Alla fine, **una sola** corsa completa con coverage azzerata e ricatturata.

---

# Esecuzione — Fase 1

## `parseNumber` · 6 copie → 5 delegano a `safeDecimal`, 1 resta

La griglia ha dato tre esiti diversi sullo stesso nome:

| copia | esito |
|---|---|
| `LotWacPriceChart`, `LotCustodyModal`, `LotComparisonChart` | **erano già `safeDecimal`** riscritta a mano |
| `LotGanttChart`, `PerformanceChart` | idem, ma con `?? 0`: il fallback è una scelta del file, la logica no |
| `CsvEditor` | **caso (c)**: fa parsing localizzato (virgola contro punto). Resta. |

E c'era un difetto latente: due copie passavano da **`safeString`**, che risponde `null` per
un valore *già numerico*. Finché il backend serializza i decimali come stringhe non si vede;
il giorno che ne manda uno come numero, quel grafico legge zero. `safeDecimal` accetta
entrambi.

**Come**: non ho riscritto le 59 chiamate. Le funzioni locali ora **delegano** in una riga —
la duplicazione era nel corpo, non nel nome, e così il rischio di sostituzione è nullo.

## `formatPercent` · 5 copie → una funzione con `scale`

Le cinque differivano su **quattro** assi, e solo uno era pericoloso:

| asse | varianti | esito |
|---|---|---|
| **scala** | 2 ricevono percentuali (0-100), 3 frazioni (0-1) | **parametro `scale`**, default 1 |
| segno | 4 sempre, `RiskAnalysisPanel` opzionale | parametro `signed`, default `true` |
| valore mancante | 3 stampano `—`, 2 assumono un numero | parametro `empty` |
| `-0` | 2 lo normalizzavano, 3 no | **guardia tenuta per tutte** |

`formatPercent(v)` per i grafici dei lotti, `formatPercent(v, {scale: 100})` per rischio e
custodia. Chi chiama sa in che scala è il proprio numero: è l'unico a saperlo, quindi lo dice.

14 test nuovi, fra cui la proprietà che le cinque copie violavano — *la stessa quantità,
espressa nei due modi, deve stampare identica*:

```ts
expect(formatPercent(7.25)).toBe(formatPercent(0.0725, {scale: 100}));
```

E uno che pinna una stranezza del linguaggio: `(1.005).toFixed(2)` è `"1.00"`, non `"1.01"`,
perché 1.005 in binario sta appena sotto la metà. Documentato perché sembra un difetto del
formattatore e non lo è — e perché chi fosse tentato di «correggerlo» con un epsilon deve
trovare questo test per primo.

**Stato**: `svelte-check` 0/0, **1 387 unit verdi**, `check-orphans` pulito (98 unit).

## `setupResizeObserver` · 8 copie → `createResizeWatcher`, e una guardia che mancava a sette

Le otto erano le stesse tre righe — tranne una. **`GrowthChart`** controllava anche se stesse
osservando *quell'* elemento, e si ri-puntava se era cambiato:

```ts
if (resizeObserver && observedContainer === chartContainer) return;
resizeObserver?.disconnect();
```

Le altre sette guardavano solo «ho già un observer?». Quando Svelte sostituisce il nodo — cosa
che fa ogni volta che l'elemento sta in un blocco keyed che si ri-renderizza — restavano
attaccate a un nodo staccato e **smettevano di ridimensionarsi in silenzio**: il grafico
congelato alla vecchia misura fino a un ricaricamento.

Caso (2) della griglia: quella copia aveva ragione, e la sua guardia è ora di tutti.
`createResizeWatcher(onResize)` → `{observe(el), disconnect()}`, 8 test.

---

# Fase 4 — lo strumento ora guida per rami

`coverage_js` calcola i rami **per funzione** (`_branches_in_range`) e `coverage_analysis` li
mostra, **ordinando le righe per rami scoperti** invece che per statement:

```
  🖼️ SVELTE_UI     1628 funcs   4756 stmts   3678 branch
  🧭 JS_ROUTE       217 funcs    719 stmts    379 branch
  🔨 JS_UTILITY      34 funcs    231 stmts    200 branch
  📉 JS_CHART        23 funcs     85 stmts     89 branch   ← più rami che statement
```

`JS_CHART` è il caso che dà ragione al cambio di metrica: **89 rami scoperti contro 85
statement**. Ordinando per statement finiva a metà classifica; è logica densamente
condizionale, ed è invisibile a chi conta le righe.

Funziona anche per il backend senza modifiche: `coverage.py` fornisce già
`missing_branches` nel proprio summary, quindi i due linguaggi ora si leggono con lo stesso
metro. 10 test nuovi (26 in tutto sull'adattatore).

## `handleClickOutside` · 9 copie → una detection, e la guardia che ne salva sette

`isOutsideClick(target, isInside)`. Le nove divergevano su tre assi, e la griglia li separa:

- **cosa conta come «dentro»** — cinque `ref.contains`, quattro `closest(selettore)` perché la
  loro superficie è portalata fuori dal sottoalbero. Due *espressioni* di una domanda sola →
  **caso (1)**: il predicato lo passa il chiamante. Non due funzioni.
- **`isConnected`** — l'avevano **solo i due date-picker**, ed è **caso (2)**. Il commento nel
  loro codice spiega perché: un `SimpleSelect` annidato rimuove l'`<option>` cliccata su
  *mousedown*, **prima** che parta il `click`; a quel punto il bersaglio è staccato dal DOM e
  ogni `contains`/`closest` risponde «fuori» → **si chiude la superficie che l'utente sta
  usando**. Gli altri sette erano a un dropdown annidato di distanza dallo stesso difetto.
  Ora è di tutti.
- **`click` contro `mousedown`** — **lasciato a ogni chiamante di proposito**. `mousedown`
  chiude prima che il click raggiunga il bersaglio, `click` dopo: è una scelta di
  comportamento, e nasconderla dietro un default seppellirebbe una decisione vera.

## `formatDate` · 13 definizioni → 4 delegano, le altre sono famiglie diverse

Qui la griglia ha detto soprattutto **(3)**: ci sono almeno cinque semantiche — serializzatore
UTC interno, asse di grafico, data+ora, data lunga, multi-formato — e forzarle in una sola
avrebbe prodotto una funzione con sei parametri che nessuno legge.

Unificato solo ciò che era **byte-identico**: due copie che erano già `formatAxisDate`, e la
coppia data+ora di `FileGrid` e `routes/files` → `formatDateTime`.

---

# Il difetto che le copie nascondevano: un giorno intero, a ovest di Greenwich

`new Date('2024-03-15')` è mezzanotte **UTC** per specifica. Misurato:

```
A New York mostra:  Mar 14, 2024
A Roma mostra:      15 mar 2024
```

Ogni data che l'API manda per un'apertura, una chiusura o un confine di lotto è un
`YYYY-MM-DD` — **un giorno di calendario**, senza istante e senza fuso da convertire. Renderla
come istante mostra il giorno sbagliato a metà del pianeta. `LotCustodyModal` era l'unica copia
che la parsava in locale; le altre no.

**Corretto in `formatAxisDate`**, che è il punto per cui passano i grafici dei lotti.

Due cose imparate lungo la strada:

1. **La prima versione della correzione era sbagliata.** La regex riconosce la *forma*, non il
   calendario: `new Date(2024, 12, 45)` non fallisce, trabocca nell'anno dopo. L'ho scoperto
   perché il mio stesso test è diventato rosso. Aggiunto il **round-trip** sui componenti — la
   stessa tecnica che `dateOnly.parseUtc` già usa e documenta.
2. **Il test è scritto per essere indipendente dal fuso**: non nomina una stringa attesa, ma
   afferma che *il giorno reso è il giorno chiesto*. Verificato con `TZ=America/New_York`:
   **rosso senza la correzione, verde con**. A Roma sarebbe passato in entrambi i casi — cioè
   sarebbe stato inutile.

**A Roma nulla cambia a schermo**, quindi la gallery e gli E2E non si muovono: il rischio era
zero e il guadagno reale.

## Lasciato aperto di proposito

- **L'asimmetria touch di `Tooltip`**: `handleTouchOutside` guarda solo il trigger, non il
  corpo del tooltip, quindi un tap sul tooltip lo chiude. Su mobile «tocca per chiudere» è un
  modo di fare comune, quindi **potrebbe essere voluto** — e non ho prove che sia un difetto.
  Non toccato.
- **`toISOString().slice(0, 10)` in ~15 file fuori dai tre helper**: stessa famiglia del
  difetto sopra, già segnalata. Fuori dal perimetro della Fase 1.

**Stato Fase 1**: **1 414 unit verdi** su 101 file, `svelte-check` 0/0, `check-orphans` pulito,
lint 37.

---

# Fase 2 — la scoperta che cambia come si legge tutta la campagna

## I rami dei template Svelte **non sono misurati**

La corsia `assets` ha segnalato un ramo che un test verde asserisce e la copertura dà per
scoperto. L'ho verificato, prima sul caso reale e poi su un caso minimo costruito apposta.

**Caso reale** — `ProviderAssignmentSection` riga 402, `{#if idTypeAutoSet}`: il test asserisce
il lato vero (riga 171, elemento presente) *e* il lato falso (riga 181, assente). La misura
dice `arms=[0, 4]`: un lato mai eseguito.

**Caso minimo** — un componente con un solo `{#if}`, due test che rendono i due lati:

```
Toggle.svelte nel report: True
branchMap: {}          ← vuoto
hits b :   {}
```

**Il `branchMap` è vuoto.** Per un `{#if}` in un template Svelte, istanbul non registra alcun
ramo. Quelli che *compaiono* nei `.svelte` vengono dal blocco `<script>`, che è JavaScript
normale; il markup condizionale è invisibile alla misura, e quando compare è mal attribuito.

**Cosa significa:**

1. Il **53,75% di rami del frontend è sottostimato**, perché il denominatore ignora i
   condizionali dei template ma il numeratore risente delle attribuzioni sbagliate.
2. **La strategia del piano era giusta per la ragione sbagliata.** Estrarre la logica in `.ts`
   non serve solo a renderla testabile senza montare: è **l'unico modo di misurarla**. Un ramo
   che resta nel `.svelte` non si può né contare né dimostrare coperto.
3. Le percentuali di rami dei `.svelte` vanno lette come **indicative**, mai citate. Quelle
   dei `.ts` sono esatte.

Due corsie l'hanno incontrata per conto proprio: `table` parla di «rami dimostrabilmente
eseguiti eppure riportati scoperti», `assets` di «sotto-stima del 36% e del 58%». Tre
osservazioni indipendenti dello stesso fenomeno.

---

# Il difetto: una colonna che dichiara il proprio ordine, e nessuno lo legge

`ColumnDef.sortFn` è dichiarato in `types.ts:259`, impostato da `ImportWizardModal:1614` sulla
colonna **Status**, e **letto da nessuno**: `grep sortFn` in `DataTable.svelte` e in
`dataTableLogic.ts` dava zero.

L'intenzione del chiamante è esplicita — ordinare per **priorità di triage**:

```
before_opening → unresolved → pending_duplicate → pending_possible_duplicate
              → likely → possible → unique
```

L'ordine alfabetico che l'utente otteneva è invece:

```
before_opening, likely, pending_duplicate, pending_possible_duplicate,
possible, unique, unresolved
```

Cioè `unresolved` — una riga che **richiede un intervento** — finiva in fondo, dopo `unique`
che non ne richiede nessuno. Chi ordina per stato lo fa proprio per raggruppare ciò su cui
deve agire, e otteneva l'opposto.

**Corretto** onorando `sortFn` quando c'è, con l'inversione applicata al risultato per il
verso discendente. Quattro test, verificati **rossi prima** (3 su 4) e verdi dopo, fra cui uno
che dimostra che i due ordinamenti *divergono davvero* — altrimenti la correzione sarebbe
indistinguibile dal caso precedente.

## Il secondo difetto: due liste percorse a velocità diverse

`TransactionBulkModal`, percorso di **validazione** (non di commit).

- riga 1170 — `resolveOps({splitTxIds})`: **senza** `promoteTxIds`, quindi le righe-edit in coda
  di promote restano nella lista risolta;
- riga 1116 — `buildOpsIndexMap` deriva `promoteTxIds` **da sé** e quelle righe le **salta**,
  senza avanzare il proprio cursore.

Due funzioni percorrono la stessa lista a velocità diverse: da lì in avanti la mappa
`"operation:index" → tempId` è **sfasata di uno**. E quella mappa è ciò attraverso cui vengono
agganciati l'anteprima WAC e i messaggi di validazione — quindi l'utente che valida un bulk
con un promote in mezzo vede **l'anteprima appesa alla transazione sbagliata**.

Il percorso di **commit** (riga 1397) passa entrambi ed è coerente: è solo la validazione a
divergere. E validava anche righe che il commit non invia, il che è la domanda sbagliata —
un'anteprima deve simulare il commit, non qualcosa che gli somiglia.

È il **quinto** difetto trovato in questo stesso file in questa campagna, tutti della stessa
famiglia: due percorsi che dovrebbero dire la stessa cosa e non la dicono. Corretto allineando
la validazione al commit.

## Fase 2 — le corsie rientrate

| corsia | rami |
|---|---|
| `assets` | 40,7% → **63,4%** (`ProviderAssignmentSection` 0 → 86%) |
| `table` | 42,1% → **72,2%** (`DataTablePagination` 27 → 91,9%) |
| `charts` + `risk` | 146 rami spostati nei `.ts`, portati al **97-100%** |
| `transactions/modals` | 85 rami estratti al **100%**; superficie `.ts` complessiva **523/524** |

**Diciassette moduli di logica pura estratti**, tutti fra il 95% e il 100% di rami — contro
`.svelte` che stavano fra il 21% e il 67%. Non è che i moduli siano stati testati meglio: è
che nei `.svelte` quei rami **non erano nemmeno misurabili**.

Unit test: **1 414 → 2 185**.

## `brokers/lots` — l'area mai toccata, e la stessa data sbagliata in altri tre punti

**655/658 rami = 99,5%** su 9 moduli estratti, 392 test. Prima: 38-53% e mai in entrambi i
sensi, perché la logica viveva dentro le closure di `renderChart` — e in jsdom ECharts non
monta, quindi quei rami erano **strutturalmente irraggiungibili**.

I 3 rami scoperti sono tutti `??`/`default` difensivi, annotati **nel sorgente** con la
dimostrazione che non sono raggiungibili (es. `perDate.get(iso) ?? 1`, dove `perDate` è
riempita per ogni `iso` prima della lettura).

### Il difetto delle date era in quattro posti, non uno

Avevo corretto `formatAxisDate`. La corsia ne ha trovati altri **tre** che non ci passano:
`LotComparisonChart.formatShortDate` e `.formatLongDate`, `LotGanttChart.formatDate`.

Il difetto era nel **parse**, non nel formato — e i tre formati sono diversi, quindi non
potevano semplicemente chiamare `formatAxisDate`. Estratto `parseDisplayDate(value)`: il
*parse* è la conoscenza condivisa, il *formato* resta di chi chiama. È di nuovo la griglia —
divergono per una scelta che il chiamante conosce.

Verificato con `TZ=America/New_York`: 15 test verdi lì come qui.

### Due funzioni simili tenute separate, con la ragione

- `getBroker` (custody) contro `findBroker` (table): la prima ritorna un broker **sintetico**
  sul miss, la seconda `null`. **Post-condizione diversa** → unificarle mentirebbe a un
  chiamante.
- `eventMarkerKind` in due file: enum di ritorno **diversi** (`'open'|'transfer'|…` contro
  `'BUY'|'SELL'|…`). Restano due.

---

# Fase 2 — chiusura

| corsia | rami |
|---|---|
| `brokers/lots` | 38-53% → **99,5%** (655/658, 9 moduli) |
| `transactions/modals` | superficie `.ts` **523/524** (99,8%) |
| `table` | 42,1% → **72,2%** |
| `assets` | 40,7% → **63,4%** |
| `charts` + `risk` | 146 rami spostati, **97-100%** |

**Unit test: 1 414 → 2 324.** Trentacinque moduli di logica pura estratti in tutto.

## Due difetti di prodotto, entrambi corretti

1. **`ColumnDef.sortFn` dichiarato e mai letto** — chi ordinava per stato nel wizard otteneva
   l'ordine alfabetico, con le righe che *richiedono un intervento* in fondo.
2. **`validateFn` e `buildOpsIndexMap` percorrevano la stessa lista a velocità diverse** —
   l'anteprima WAC finiva appesa alla transazione sbagliata.

Più il difetto delle date in tre punti nuovi.

## L'indice del rendering

13 righe, tutte da codice **letto**. Il campo più utile si è rivelato «cosa diverge»: metà
delle voci sono **«no — sono diversi»**, e la ragione è quasi sempre la stessa — lo stesso
blocco appare una volta come markup Svelte e una volta come **stringa HTML** per una cella
`html:` di `DataTable`. Somiglianza ingannevole: non sono fattorizzabili come componente,
al massimo lo è la funzione che decide le classi.

---

# Risultato — `all --workers 8`: **15/15**

| | inizio | fine |
|---|---|---|
| JS **rami** | 53,75% | **58,47%** |
| JS righe | 74,81% | **76,66%** |
| Unit frontend | 1 414 | **2 324** |
| Backend righe / rami | 92,39 / 82,64% | 92,38 / **82,63%** |

**+4,7 punti di rami**, che era l'obiettivo del piano.

## Il numero che conta davvero

**I `.ts` sono al 75,95% di rami** (6 185 / 8 143), contro il 58,47% complessivo. La
differenza non è che i moduli siano testati meglio: è che **nei `.svelte` i rami dei template
non sono misurati affatto**, e quelli che compaiono sono mal attribuiti.

Quindi il 58,47% è un numero misto — parte misura vera, parte rumore. Il 75,95% dei `.ts` è
il solo dato su cui si possa ragionare, ed è anche la parte che questa campagna ha creato:
trentacinque moduli estratti, quasi tutti fra il 95% e il 100%.

## Cosa lascia questa fase

1. **Una regola sulle duplicazioni che ha retto cinque volte.** Divergono per una scelta che
   il chiamante conosce → parametro (`formatPercent({scale})`, `parseDisplayDate`); per una
   guardia in più → la guardia si tiene per tutti (`isConnected`, la re-punta del
   `ResizeObserver`); perché fanno due cose diverse → restano due (`getBroker` contro
   `findBroker`, i due `eventMarkerKind`).
2. **Tre difetti di prodotto** corretti: `sortFn` mai letto, le due liste percorse a velocità
   diverse, le date lette un giorno prima in quattro punti.
3. **Un fatto sulla misura** che nessuno sapeva: i rami dei template Svelte non esistono nel
   report. Da qui in avanti, ogni percentuale di rami su un `.svelte` va letta come indicativa.
4. **L'indice del rendering**, 13 righe da codice letto, per una decisione futura.

## Resta aperto

- **Fase 3**, i due spec distruttivi (`files/+page`, `fx/[pair]/+page`): `mode: 'serial'` con
  `db populate --force --with-reports` in coda, come indicato.
- I `.svelte` restano poco misurabili: l'unica leva è continuare a estrarre.

---

# Fase 3 — i due percorsi distruttivi

`files-destructive.spec.ts` (6 test) e `fx/fx-destructive.spec.ts` (10), entrambi
`mode: 'serial'` **con la ragione scritta**, entrambi auto-ripristinanti.

## La strategia si è rivelata migliore dell'istruzione

Avevo suggerito `db populate --force --with-reports` come rete. La corsia l'ha implementata
ma **condizionata a un solo worker** — e la ragione è ottima: `--force` sgancia l'intero
SQLite mentre gli altri worker sono a metà asserzione, quindi a `--workers 4` **si spegne per
costruzione**.

Il che significa che a quattro worker regge soltanto la pulizia precisa: righe usa-e-getta con
marcatore unico, cancellate dal test che le ha create, senza toccare le righe del mock. Il
ripopolamento resta come rete, non come strategia — che è l'ordine giusto.

## La prova del ripristino

| | corsa A | corsa B (sul database che A ha lasciato) |
|---|---|---|
| `front-utility` | 178 verdi | **178 verdi**, con `LF_SETUP_DONE=1`: *nessun* ripopolamento |
| `fx-destructive` | 10 verdi | **10 verdi**, stato dell'API identico: 15 rotte, 0 residui, 168 upload |

La corsa B di `front-utility` è la prova alla lettera: se A avesse eroso i dati del mock,
`files.spec.ts` — che li legge — sarebbe caduto. Non è successo.

## Rami

`fx/[pair]/+page.svelte` 71 → **79** su 206; `files/+page.svelte` 47 → **50** su 111.

Il delta è modesto, e la corsia ne dà la ragione onesta: **parte di `files/+page` non è
raggiungibile**. Vedi sotto.

## Codice morto trovato — non toccato

In `files/+page.svelte` i tre mutatori del filtro broker — `toggleBrokerFilter`,
`selectAllBrokers`, `clearBrokerFilter` — compaiono **una sola volta ciascuno**: la propria
definizione. Nessun controllo del template li invoca. Verificato di persona.

E `selectedBrokerIds` viene inizializzato con **tutti** i broker selezionati, quindi non
filtra nemmeno di fatto. Il filtro broker non è un difetto: è una funzionalità **inerte**, e
non è raggiungibile via E2E perché non ha interfaccia. Lasciata: rimuoverla o ricollegarla è
una decisione di prodotto.

## Nessun difetto nei percorsi di cancellazione

Conferma, annullamento della conferma, cancellazione singola e multipla, esito su file già
sparito, refresh di massa, cancellazione di coppie e di singoli tassi: tutti corretti. È il
primo blocco di questa campagna che non produce difetti — e i percorsi di cancellazione erano
il posto dove ne aspettavo di più.

## Segnalato: un flake preesistente

`tooltip-component.spec.ts:118` è caduto una volta su quattro nella sessione precedente, su
una rotta che non condivide nulla con i nuovi spec. Non introdotto da questa fase, da tenere
d'occhio.

---

# Chiusura della campagna — `all --workers 8`: **15/15**

| | inizio | fine |
|---|---|---|
| **JS rami** | 53,75% | **58,77%** |
| **JS rami, solo `.ts`** | — | **76,03%** ← la parte misurabile |
| JS righe | 74,81% | **77,07%** |
| Backend righe / rami | 92,33 / 82,56% | **92,40 / 82,67%** |
| Python del server E2E | 0,00% | **28,75%** |
| Unit frontend | 952 su 75 file | **2 324 su 128** |
| Spec E2E | 60 | **66** |

Lint 37 (invariato), `svelte-check` 0/0, `check-orphans` pulito.

## Cosa è cambiato davvero

Il **58,77%** è un numero misto: i rami dei template Svelte non esistono nel report, quindi
metà del denominatore è cieca. Il **76,03% dei `.ts`** è l'unico dato su cui si possa
ragionare — ed è anche quello che questa campagna ha costruito, estraendo **trentasette
moduli** di logica pura da componenti dove quei rami non erano né raggiungibili né misurabili.

## I difetti di prodotto

| # | difetto | chi lo vedeva |
|---|---|---|
| 1 | `sortFn` dichiarato e mai letto | chi ordinava per stato: righe da sistemare in fondo |
| 2 | `validateFn` e `buildOpsIndexMap` a velocità diverse | anteprima WAC sulla transazione sbagliata |
| 3 | date-only lette come UTC, **in quattro punti** | ogni utente a ovest di Greenwich, un giorno prima |
| 4 | `isConnected` mancante in sette copie su nove | chiusura della superficie che si sta usando |
| 5 | `ResizeObserver` non ri-puntato in sette copie su otto | grafico congelato dopo un cambio di nodo |

I primi tre corretti in questa fase, gli ultimi due dalla fattorizzazione: **erano difetti che
la duplicazione teneva in vita**, perché in ogni file la copia sbagliata sembrava corretta e
nessuno guardava le copie insieme.

## Codice morto segnalato, non toccato

Il filtro broker di `files/+page.svelte`: tre mutatori mai invocati e uno stato inizializzato
a «tutto selezionato». Non è un difetto, è una funzionalità inerte — rimuoverla o
ricollegarla è una decisione di prodotto.

## Le tre cose da ricordare

1. **I rami dei template Svelte non sono misurati.** Provato con un componente minimo:
   `branchMap` vuoto. Ogni percentuale di rami su un `.svelte` è indicativa; solo i `.ts`
   contano.
2. **La griglia sulle duplicazioni ha retto sei volte.** Parametro se la scelta è del
   chiamante; guardia tenuta per tutti se una copia era più prudente; due funzioni se fanno
   due cose. `formatPercent({scale})` e `parseDisplayDate` sono nate così.
3. **Un test che passa con e senza la correzione non prova nulla.** È capitato due volte a me
   in questa campagna, entrambe rimosse: la disciplina è verificare il rosso *prima*.
