# Riparare le misure, poi alzare la copertura JS

Storico precedente: `files/plan-storico-coverage-campaign-2.md`.

## Il problema

Due misure mentono, e finché mentono ogni decisione su dove scrivere test è presa
al buio. Una nasconde dati, l'altra **premia il comportamento sbagliato**.

Solo dopo averle riparate ha senso pianificare la copertura JS — e i dati raccolti
oggi dicono che la strada battuta finora (E2E per tutto) non è quella che rende.

---

## Fase 0 — Riparare le misure. Bloccante.

### 0.1 · La coverage Python del server E2E si perde sopra i 2 worker

`.coveragerc` dichiara `concurrency = thread,gevent` e **non** `multiprocessing`.
Sopra i due client `server_workers_for` = `ceil(client/2)` fa partire uvicorn con
più worker, uvicorn li **forka**, e `coverage run` misura solo il padre — che non
serve richieste.

| | file scritti | misurato |
|---|---|---|
| `--workers 8`, tutta la suite | 5 | **0,00%** |
| `--workers 2`, **una sola** spec | 1 | **35,01%** |

I file vengono scritti **vuoti**, quindi nulla avvisa: il numero scende e si legge
come codice non testato.

Portata reale: unita al backend quella misura vale **+0,36 punti** (90,10 → 90,46 in
scala mista). Non alza il totale — serve a sapere *quali percorsi backend toccano gli
E2E*, che è un'altra domanda e vale comunque la pena poterla porre.

**Cura decisa**: aggiungere `multiprocessing` alla `concurrency`.

Attenzione: uvicorn ha una propria supervisione dei worker, quindi la cura va
**provata**, non solo scritta. Il criterio di successo non è «gira», è che
`.coverage_data/frontend` a 8 worker dia una percentuale ≥ di quella a 2 worker.
Se `multiprocessing` non basta, il ripiego è forzare **un solo** worker uvicorn
quando la coverage è attiva.

### 0.2 · Il report JS combinato conta 2 163 statement fantasma

Trovato oggi, e più insidioso del primo. `mcr merge` unisce i raw di vitest e degli
E2E, ma le due build compilano lo stesso `.svelte` in modo diverso: gli statement
hanno offset diversi e **non si fondono**. Il denominatore combinato è la somma
parziale di due mappe dello stesso file.

```
DataTableColumnFilter.svelte
   vitest    coperti=389  totali=532
   e2e       coperti=107  totali=484
   combinato coperti=454  totali=791   ← 791 > 532, e 73,1% diventa 57,4%
```

**89 file su 134** misurati da entrambi i livelli ne soffrono, per **2 163 statement
fantasma** (~6% del denominatore).

| | |
|---|---|
| combinato dichiarato | **71,11%** (25 738 / 36 195) |
| togliendo i fantasma | **75,63%** (25 738 / 34 032) |

E qui sta il veleno: i file colpiti sono **esattamente quelli con un component
test** — `DataTable` +331, `DataTableColumnFilter` +259, `DateRangePicker` +232,
`ScheduledInvestmentEditor` +202. Cioè **aggiungere un component test a un file già
coperto dagli E2E ne peggiora il numero combinato.** La metrica punisce la cosa
giusta, ed è il motivo per cui questa fase viene prima di tutto il resto.

**Da decidere in corso d'opera, con la prova in mano**: far coincidere le due mappe
(stessa pipeline di build per entrambi i livelli), oppure — se non è praticabile —
smettere di fondere i due livelli sullo stesso file e prendere il **massimo per
file**, dichiarandolo nel report. Nessuna delle due è ovvia: prima si riproduce il
difetto su un file solo, poi si sceglie.

---

## Fase 1 — Component test dove rendono. Parallelizzabile.

### Il dato che cambia strategia

Confronto sui file grandi, stessa metrica:

| file | vitest | E2E |
|---|---|---|
| `DataTableColumnFilter` | **73,1%** | 22,1% |
| `ScheduledInvestmentEditor` | **61,5%** | 25,1% |
| `DateRangePicker` | **54,5%** | 45,9% |
| `DataTable` | 53,4% | 56,3% |
| `ImportWizardModal` | — | 65,3% |
| `AssetModal` | — | 53,0% |

Dove il componente ha **logica densa e propria** (un filtro con sette modalità, un
editor, un date picker), il component test arriva a **tre volte** quello che
raggiunge l'E2E. La ragione è scritta nel test che esiste già:

> *«Raggiungerlo con Playwright significa scegliere una pagina che esponga la
> modalità che vuoi esercitare — e tre delle sette vivono su pagine dove preparare
> i dati è la maggior parte del lavoro. Qui ogni modalità è una prop.»*

Dove invece il componente è **orchestrazione** (`DataTable`), i due si equivalgono.

### Perché è parallelizzabile davvero

I component test girano in **Vitest + jsdom**: niente database, niente porta 6041,
niente Playwright. Le corsie non condividono nulla, quindi possono girare tutte
insieme — a differenza degli E2E, dove il parallelismo sta *dentro* Playwright e
mai sopra.

L'infrastruttura c'è: `$test/component` (`render`, `screen`, `fireEvent`,
`setupI18n`, `waitFor`), 13 component test già scritti, due dei quali (559 e 764
righe) sono il modello da seguire.

### Le corsie

Ordinate per statement scoperti recuperabili. Ogni corsia è indipendente.

| corsia | bersaglio | scoperti | perché |
|---|---|---|---|
| **A** | `components/assets` (18 file) | **1 086** | l'area **meno coperta** in proporzione: 55,0% |
| **B** | `components/ui` (53 file) | **1 490** | tanti file piccoli e puri — il caso ideale per jsdom |
| **C** | `components/charts` (27 file) | **986** | 62,1%; la logica di serie/assi è testabile senza browser |
| **D** | `components/table` (6 file) | **796** | 58,7%, ma concentrati: `DataTable` + `ColumnFilter` |
| **E** | `ImportWizardModal` | **533** | il singolo file peggiore del frontend |

Regola per ogni corsia: **misurare prima, misurare dopo**, con lo stesso metodo, e
riportare il delta per file. Un numero aggregato non dice se il lavoro è servito.

### Cosa non fare

- Non inseguire `SVELTE_UI` come categoria: Svelte 5 compila i template in closure
  anonime, quindi quel dato dice *«raggiunto o no»*, non quanto. Serve a ordinare,
  non a citare percentuali.
- Non riscrivere in component test ciò che l'E2E copre già bene
  (`TransactionBulkModal` è all'82,7%): il margine è 175 statement e il costo è alto.
- Non asserire su testo tradotto, mai. L'interfaccia è EN/IT/FR/ES.

---

## Fase 2 — E2E solo per i flussi

Resta la corsia D3 mai avviata: `routes/fx` (188 scoperti), `routes/files`,
`FilePreviewModal`. Sono **rotte**, cioè attraversano più componenti e toccano il
backend: qui l'E2E è lo strumento giusto e il component test non arriverebbe.

Una sola invocazione Playwright per volta, sempre.

---

## Il potenziale, con i numeri

Denominatore corretto ~34 032 → **un punto percentuale costa ~340 statement**.

I primi dieci file fanno **2 980 statement scoperti**, il 34,2% di tutto lo scoperto
`.svelte`. Recuperarne il 60% vale **~5 punti**. Sommato ai ~4,5 che la Fase 0
restituisce correggendo la misura, l'ordine di grandezza è **71 → 80%**.

Va detto onestamente: 4,5 di quei punti non sono lavoro, sono **la fine di un
errore di conteggio**. È giusto separarli nel resoconto invece di intestarseli.

---

## I file grandi: una domanda aperta, non una fase

L'osservazione sullo spezzettare regge, e i numeri la sostengono:

| file | righe | scoperti |
|---|---|---|
| `ImportWizardModal.svelte` | **5 326** | 533 |
| `TransactionBulkModal.svelte` | **3 349** | 175 |
| `DataTable.svelte` | **2 560** | 414 |
| `DataTableColumnFilter.svelte` | 1 794 | 337 |
| `DateRangePicker.svelte` | 1 463 | 297 |
| `ScheduledInvestmentEditor.svelte` | 1 432 | 311 |

`ImportWizardModal` da solo è il **6%** di tutto lo scoperto del frontend, e i suoi
sette passi si raggiungono solo attraversandoli in ordine — che è precisamente ciò
che rende il test costoso.

Ma è un refactoring architetturale su codice appena corretto, non un lavoro di
copertura. **Deciso: fuori da questo piano.** Farlo insieme ai test significherebbe
cambiare il codice e la sua misura nello stesso momento, e se qualcosa peggiorasse
non si saprebbe quale dei due l'ha causato. Si valuta dopo, con la misura riparata e
i component test a fare da rete.

---

## Verifica finale

Una sola corsa completa alla fine, con coverage azzerata e ricatturata:

```
./dev.py test --coverage --cov-clean-backend --cov-clean-backend-e2e \
              --cov-clean-js --workers 8 all
```

Più: `check-orphans` pulito, lint ≤ 37, `svelte-check` 0/0, prettier pulito.

---

# Esecuzione — Fase 0 chiusa

## 0.1 · `multiprocessing`: curato e **provato**

`concurrency = multiprocessing,thread,gevent`. Il criterio non era «gira»: la stessa spec
(`tx-tooltips`) a 8 worker passa da **0,00% a 35,01%**, cioè esattamente quanto misurava a
2 worker. Quattro file scritti e non vuoti.

## 0.2 · Statement fantasma: causa provata, non dedotta

Il combinato è l'**unione** delle due mappe (791 posizioni), che ne condividono solo **225**
su 532/484. Le **righe** invece reggono la doppia compilazione (356 condivise su ~450), e
sono quindi l'unità stabile.

Cura in `coverage_js._statements_in_range`: conteggio per riga. Effetto sulla mappa che
guida le decisioni: **7 628 → 6 475** statement, `SVELTE_UI` 6 012 → 4 982.

**16 test nuovi** su quell'adattatore (`utils coverage-js-adapter`, isolamento `PURE`),
verificati **rossi prima** — 7 su 16 — e verdi dopo. Era codice non testato che decide dove
tutti gli altri vanno a scrivere test.

---

# Fase 1 — corsie

## D · `table` (fatta direttamente)

8 test sulle **celle tipizzate**: `badge`, `size`, `html`, `link`, `icon-text`, `date` e le
forme editabili si *mostrano* in un modo e si **ordinano** in un altro (`size` mostra
«1,5 kB» e ordina su 1536), e ogni forma andava raggiunta trovando una pagina che la usi.
Più il footer vuoto, che nessuno copriva.

Due cose imparate:

1. **Due dei miei test erano ridondanti.** Il footer era già coperto, e *meglio*: il test
   esistente verifica anche gli argomenti passati alla funzione. Rimossi.
2. **I numeri di riga della mappa vitest non si allineano al sorgente** — la riga 503
   risultava coperta e la 489 no, che è impossibile. Quindi la misura è il **delta**
   prima/dopo, rimuovendo temporaneamente i test: `DataTable` **49,0 → 51,2%**.

## E · `ImportWizardModal`

L'agente ha scelto l'**estrazione**, e la motivazione regge: ogni passo è sbloccato da stato
prodotto da chiamate API, quindi la logica densa dei passi 4-6 non ha alcun ingresso da
prop. Montare fin lì significherebbe doppiare l'intera catena — «montare a fatica e
verificare poco».

Quattro moduli estratti (`importTypes`, `importDedup`, `importMerge`, `importCompare`, 377
righe), il componente da **5 326 a 4 949**. Copertura dei moduli **86-100%** statement,
60 test. Nota: è un'estrazione *funzionale*, non lo spezzettamento architetturale che
abbiamo tenuto fuori dal piano.

Segnalato **dead code**: `buildDupTooltipHtml` (~30 righe) non ha chiamanti. Lasciato.

## A · `assets`

82 test nuovi, 124 verdi. `ProviderComparisonModal` 0 → **98,2%**,
`AssetCurrencyChangeModal` 0 → **98,7%**, `CellDateRange` 36,9 → **96,9%**,
`AssetSearchAutocomplete` 0 → **87,6%**, `AssetModal` 0 → **52,3%**.

L'agente sosteneva che monocart «scarta silenziosamente i file grandi». **Verificato: falso**
— `AssetModal` è nel report al 50,6%. Valeva la pena controllarlo invece di crederci: se
fosse stato vero, sarebbe stato un terzo difetto di misura.

---

# Il difetto trovato dall'orologio

`CalendarMonth.test.ts` è diventato rosso alle **00:02**, e non l'aveva toccato nessuno.
Il componente legge `todayIso()` (calendario **locale**), il test costruiva l'atteso con
`toISOString().slice(0, 10)` (**UTC**). Le due letture coincidono 22 ore su 24: il difetto
esiste solo fra mezzanotte e le 02:00 a Roma — ed erano le 00:02.

È lo **stesso difetto** che avevamo corretto in `todayIso` giorni fa, sopravvissuto in un
test che nessuno aveva motivo di guardare. Estratto `localIso(date)` in `dateOnly.ts` — la
formula «leggi i campi locali» esisteva in un posto solo e non era riusabile — e allineato
il test.

**Ma la prima versione del test di presidio era inutile.** Congelava l'orologio e poi
costruiva l'atteso con `localIso`, cioè con la funzione sotto test: iniettando la
regressione UTC restava **verde**. È esattamente l'errore dell'oracolo trovato nei preset di
`DateRangePicker`, ripetuto da me. Riscritto derivando l'atteso dalla **regola** («i campi
anno, mese e giorno della Date locale»), scritta per esteso nel test, più un'asserzione che
dichiara la premessa (`expected !== utcReading`). Verificato: **rosso** con il difetto,
verde senza.

## C · `charts`

179 test, 8 file nuovi, 212 verdi nella cartella. La logica interessante era **sepolta
dentro le closure di `renderChart`**, inseparabile dalla chiamata a `echarts.setOption`:
estratta in quattro moduli `.ts` fratelli, tutti al **100%**.

| modulo | copertura |
|---|---|
| `priceChartHelpers.ts` | 100% (33 test) |
| `candlestickChartHelpers.ts` | 100% (29) |
| `chartSignalsHelpers.ts` | 100% (20) |
| `geographyMapHelpers.ts` | 100% (23) |
| `echartsTooltipHelpers.ts` | 52,6 → **100%** (29) |
| `MeasurePanel.svelte` | 21,8 → **83,6%** (17) |

**Due funzioni byte-identiche** trovate lungo la strada: `formatMonthLabel` e `getBucketInfo`
esistevano in doppia copia in `PriceChartFull` e `CandlestickChart`. Verificato: ora entrambi
importano dall'unico modulo.

La traduzione resta fuori dallo strato puro per **iniezione**: `formatSignalProblem(problem,
translate, fieldLabel)` riceve la funzione, il componente le passa `$t`, i test un finto che
restituisce la chiave. Così le asserzioni sono su chiavi stabili, mai su testo tradotto.

E la locale è **fissata** dove conta: `formatMonthLabel` è testata con `en-US` e `de-DE`
espliciti, perché un test che si affida alla locale del processo passa qui e fallisce altrove.

## B · `ui`

| file | prima | dopo |
|---|---|---|
| `SearchSelect.svelte` | 0% | **83,5%** (22 test) |
| `AssetPickerModal.svelte` | 0% | **90,2%** |
| `ImageEditModal.svelte` | 0% | **85,0%** |
| `DataEditor.svelte` | 0% | **63,8%** |
| `DateRangePicker.svelte` | 64,5% | **76,7%** |
| `FxProviderSelect.svelte` | 91,5% | **93,5%** |

`SearchSelect` — il select che usa tutta l'app — ha ricevuto la cura maggiore: ogni ricerca
di opzione è **scoped con `within(dropdown())`**, che è la barriera contro il prefisso
condiviso `search-select-option-*` (due select aperti in sequenza hanno insiemi di opzioni
sovrapposti nel DOM finché il primo si chiude).

### Un difetto segnalato che non sono riuscito a confermare

L'agente ha riportato `selectOption` come difetto: `containerRef!` viene dereferenziato
dentro un `setTimeout` di 20 ms, mentre la guardia gira al momento dello *scheduling*. In
teoria un consumatore che chiude la propria modale sulla selezione smonta il componente in
quella finestra.

Il ragionamento regge, e `onchange` viene davvero chiamato **prima** del timer. Ma ho
provato a riprodurlo e **non ci sono riuscito**: né con fake timer né con timer reali, e una
sonda su `querySelector` mostra che in jsdom quella riga **non viene mai raggiunta**.

Quindi:

1. **Il test che avevo scritto passava con e senza la guardia** — cioè non provava nulla, ed
   è la definizione di test che mente. Rimosso.
2. **La guardia resta**, ma il commento dice la verità: una non-null assertion su un ref
   letto in modo asincrono è un'affermazione che nulla fa rispettare, e questo è il motivo
   per cui c'è — non un fallimento osservato.

Vale la pena distinguerlo dagli altri undici difetti di questa campagna, che avevano tutti
una prova riproducibile. Questo no.

---

# La notte ha trovato tre difetti che il giorno nascondeva

La corsa completa è finita all'01:00 con un rosso: `tx-clone`, due test su
`expect(rowText).toContain(today)`. Causa: la spec aveva la **propria copia** di `todayIso`,
scritta come `new Date().toISOString().slice(0, 10)` — cioè in UTC — mentre la UI rende il
calendario dell'utente.

È la **terza** occorrenza dello stesso difetto in questa sessione: prima `CalendarMonth.test`,
poi questa. Cercandolo ovunque, il pattern compare in **18 punti**, ma non sono tutti
difetti — e questa è la parte che conta.

| dove | «oggi dell'utente»? | esito |
|---|---|---|
| `dateRangeStore.defaultRange()` | **sì** | difetto di **prodotto**: la dashboard si apriva su un intervallo che finiva *ieri* |
| `dateRangeStore.resolveDateSentinel('max')` | **sì** | difetto di **prodotto** |
| `DataEditor.handleAddRow()` | **sì** | difetto di **prodotto**: rifiutava il giorno corrente come data di una riga nuova |
| `tx-clone.spec.ts` | sì | difetto di **test** (il rosso) |
| `dateOnly.formatUtc`, `DataEditor` `setUTCDate` | no | aritmetica UTC interna — **corretta**, non toccata |
| `asset-modal.spec.ts:400` | no | la data viene dal **backend**, che risponde in UTC |

Quell'ultima riga è il motivo per cui non ho corretto tutto d'un colpo: `asset-modal`
asserisce una data prodotta dal server, ed **è passata** in questa stessa corsa notturna.
Cambiarla per uniformità l'avrebbe rotta. Un'operazione «sostituisci ovunque» qui avrebbe
introdotto un difetto invece di toglierne uno.

**Cura**: creata `e2e/fixtures/dates.ts` (`localIso`, `todayIso`, `daysAgoIso`) — la regola
scritta **una volta** invece che in ogni spec, che è esattamente come il difetto è nato. Le
spec Playwright girano fuori dal build di SvelteKit e non risolvono l'alias `$lib`, quindi la
regola va ripetuta lì: ma una volta sola.

`tx-clone` verificato verde **all'01:00**, cioè nella finestra oraria che lo rompeva.

## Perché è successo adesso

Perché la corsa è finita dopo mezzanotte. Per 22 ore al giorno UTC e il calendario locale
coincidono, e la suite gira quasi sempre in quelle 22 ore. Non è fortuna: è la stessa ragione
per cui il difetto in `todayIso` era sopravvissuto per mesi, e per cui il test di presidio che
ho scritto **congela l'orologio** invece di fidarsi di quando gira.

---

# Risultato finale — `all --workers 8`: **15/15**

| | prima | dopo |
|---|---|---|
| Backend righe | 92,33% | **92,40%** |
| Backend branch | 82,56% | **82,64%** |
| **Python del server E2E** | **0,00%** | **28,75%** |
| JS/Svelte righe | 73,77% | **74,70%** |
| Unit frontend | 952 su 75 file | **1 354 su 96** |

**+1 366 righe JS coperte.** La percentuale sale meno del conteggio perché il denominatore è
cresciuto di 1 448 nello stesso momento: file che nessun unit test importava non erano
affatto nella mappa unit, e ora ci sono. Il numero onesto del lavoro è il **+1 366**.

| file | prima | dopo |
|---|---|---|
| `SearchSelect` | 65,3% | **90,7%** |
| `MeasurePanel` | 21,8% | **75,4%** |
| `DateRangePicker` | 64,5% | **80,2%** |
| `ScheduledInvestmentEditor` | 56,1% | **70,6%** |
| `AssetModal` | 52,9% | **56,2%** |
| `DataTable` | 60,4% | **62,0%** |

`ImportWizardModal` non è in questa tabella di proposito: l'estrazione ha spostato logica
*coperta* fuori dal `.svelte` verso moduli che ora sono al **100%**, quindi la percentuale
del file e quella di prima non misurano la stessa cosa. Insieme stanno al **61,6%**, e non ho
una baseline per riga precedente allo scorporo con cui confrontarmi. Dirlo è più utile che
esibire un delta che non reggerebbe.

## Cosa resta aperto

- **F2 · rotte `fx` e `files`** — non avviata. Sono rotte, quindi E2E: `routes/fx` è l'area
  con più righe scoperte fra quelle rimaste.
- **`buildDupTooltipHtml`** in `ImportWizardModal` — dead code, ~30 righe, zero chiamanti.
- **Lo spezzettamento dei file grandi** — tenuto fuori dal piano, come deciso. Ora però la
  misura è onesta e i component test fanno da rete, che erano le due condizioni.

---

# Fase 2 — avviata, più il dead code chiuso

## `buildDupTooltipHtml`: rimossa

Segnalata dalla corsia E come codice morto. Verificato: **un solo riferimento in tutto il
repo**, la dichiarazione stessa — nessun chiamante, nemmeno dinamico (cercato anche in `e2e/`
e nelle stringhe). 22 righe rimosse, `ImportWizardModal` da 4 949 a **4 927**.
`svelte-check` 0/0, 98 test verdi.

Nessuna decisione da chiedere: togliere codice che non viene mai eseguito non cambia nulla di
ciò che l'utente vede.

## I bersagli della Fase 2, misurati per riga

| file | scoperte / totali | |
|---|---|---|
| `routes/(app)/fx/+page.svelte` | **177 / 338** | 47,6% |
| `components/files/FilePreviewModal.svelte` | **155 / 331** | 53,2% |
| `routes/(app)/fx/[pair]/+page.svelte` | **145 / 389** | 62,7% |
| `routes/(app)/files/+page.svelte` | **115 / 313** | 63,3% |

**592 righe scoperte.** Le tre rotte vanno in E2E perché attraversano più componenti e
parlano col backend; `FilePreviewModal` è un **componente**, quindi la scelta dello strumento
è dell'agente — con l'obbligo di motivarla. Se monta a fatica in jsdom per via di `<canvas>`,
`<iframe>` o EmbedPDF, l'E2E è l'esito legittimo, com'è già successo col wizard.

## Fase 2 — consegnati due file su quattro, con la ragione scritta

| file | strumento | prima → dopo |
|---|---|---|
| `FilePreviewModal.svelte` | **component test** (19) | 168 → **187** righe coperte |
| `routes/(app)/fx/+page.svelte` | **E2E** `fx-bulk.spec.ts` (7) | 161 → **181** |

Gli altri due — `files/+page.svelte` (115 scoperte) e `fx/[pair]/+page.svelte` (145) — **non
toccati**, e la motivazione regge: le righe residue sono in larga parte **distruttive**
(`deleteFile`, `handleBulkDeleteFiles`, i delete confermati, `handleBulkRefreshFx`), cioè
scrivono su stato globale che ogni altro test legge. Coprirle richiede coppie usa-e-getta e
un ripristino per-test, non un'ora in coda a una sessione.

Preferisco due file solidi a quattro sfiorati, che è quello che avevo chiesto.

### La scelta dello strumento, motivata

`FilePreviewModal` → **component test**, e la ragione è precisa: `$app/environment` è
doppiato con `browser=false`, quindi in jsdom **tutti** i renderer asincroni (EmbedPDF,
cheetah-grid, marked+DOMPurify+KaTeX) vivono dentro `$effect` gated su `browser` e si
cortocircuitano. Resta la superficie sincrona — scelta del body per tipo, azioni per tipo,
aritmetica dello zoom, le quattro diramazioni di `formatDetectedEncoding`, gli stati
loading/error/noData — che è esattamente ciò che l'E2E raggiunge male.

Il contenuto reso in modo asincrono **resta all'E2E** (`files.spec.ts`, Chromium vero). È la
divisione giusta, non una rinuncia.

### Nessun attributo aggiunto, e va notato

L'agente ha verificato che ogni segnale servisse esistesse già: `fx-page` pubblica
`data-busy`, `selection-toolbar` pubblica `data-selected-count`, il combobox pubblica
`aria-expanded`. **Nessun `.svelte` toccato.** Dopo settimane in cui la regola 4 ci ha fatto
aggiungere attributi ovunque, è il segno che il prodotto ha smesso di essere muto.

### Un comportamento incontrato che **non** è un difetto

Riaprire un filtro valuta che ha già un valore richiede a volte un secondo clic:
`SearchSelect.openDropdown` ha una guardia di 200 ms dopo la chiusura, commentata nel codice
come prevenzione del double-tap su touch. L'agente l'ha gestita con un'apertura in **polling**
che clicca solo finché `aria-expanded !== 'true'`, invece di scambiarla per un difetto e
«correggerla». Distinguere una difesa voluta da un difetto è la parte difficile.

---

# Chiusura — `all --workers 8`: **15/15**

| | inizio | fine |
|---|---|---|
| Backend righe | 92,33% | **92,39%** |
| Backend branch | 82,56% | **82,64%** |
| **Python del server E2E** | **0,00%** | **28,75%** |
| JS/Svelte righe | 73,77% | **74,81%** |
| Unit frontend | 952 / 75 file | **1 373 / 97** |
| Spec E2E | 60 | **64** |

**+1 413 righe JS coperte.** `check-orphans` pulito, lint 37, `svelte-check` 0/0.

## Cosa resta, e perché non l'ho fatto

- **`files/+page.svelte`** (115 righe) e **`fx/[pair]/+page.svelte`** (145): i percorsi
  residui sono **distruttivi** — cancellano file, coppie e rate che ogni altro test legge.
  Servono coppie usa-e-getta e un ripristino per-test, cioè uno spec dedicato progettato per
  quello, non un'aggiunta a fine sessione.
- **Lo spezzettamento dei file grandi**: tenuto fuori come deciso. Ora però esistono entrambe
  le condizioni che mancavano — una misura onesta e i component test a fare da rete.

---

# Perché il numero si muove poco — l'analisi, con i dati

## Il sospetto «ci sono aree non testate» è infondato

| | |
|---|---|
| File sorgente in `src/` | 394 |
| File nel report | **393** — nessuna area nascosta |
| File **mai eseguiti** (0%) | 11, per **148 righe** |
| Righe scoperte in tutto | **8 099** |

Il codice mai eseguito è il **2%** dello scoperto. Non c'è un continente sommerso: le 8 099
righe sono **dentro file già coperti**, cioè sono i rami che il percorso felice non attraversa.

## È una coda lunga, ed è questo che rende il numero lento

| | righe scoperte | % del totale |
|---|---|---|
| primi 10 file | 2 438 | 30,1% |
| primi 20 | 3 640 | 44,9% |
| primi 50 | 5 444 | 67,2% |
| primi 100 | 6 988 | 86,3% |

**Un punto percentuale costa ~321 righe.** Le cinque corsie ne hanno coperte 1 413, cioè
+1 punto netto — perché nel frattempo il denominatore è cresciuto.

## Il numero vero è 75,29%, non 74,81%

Il difetto di misura è **ridotto ma non estinto**: restano **1 403 righe fantasma** su 78
file, e sono ancora i file con component test (`ImportWizardModal` +180, `DataTable` +115,
`AssetModal` +101). Ironia: il lavoro di ieri notte ha **aumentato** il gonfiaggio, perché ha
aggiunto una mappa vitest a file che prima avevano solo quella E2E.

Calcolato col denominatore giusto — una mappa **reale**, non l'unione di due, e le coperte
intersecate con essa — la copertura è **75,29%**.

*(Una mia stima intermedia diceva 78,22%: era sbagliata, toglieva le fantasma dal
denominatore ma teneva tutte le coperte, comprese quelle che vivono solo nella mappa
fantasma. Il metodo corretto dà mezzo punto, non tre e mezzo.)*

## Dove attaccare, in ordine di resa

| area | scoperte | copertura | file |
|---|---|---|---|
| `componenti/transactions` | **1 542** | 69,9% | 29 |
| **rotte (pagine)** | **1 074** | 67,8% | 21 |
| `componenti/ui` | 947 | 75,5% | 53 |
| `componenti/assets` | 720 | 69,3% | 18 |
| `componenti/brokers` | **672** | 75,5% | 17 — *mai toccata da una corsia* |
| `componenti/charts` | 618 | 74,6% | 31 |
| `componenti/table` | 440 | 67,2% | 7 |

Due osservazioni:

1. **`componenti/brokers` non è mai stata una corsia.** 672 righe scoperte, e `LotComparisonChart`
   da solo ne ha 194. È il buco più grosso fra le aree mai affrontate.
2. Le **rotte** sono 1 074 righe su 21 file al 67,8%: è E2E, ed è il secondo blocco.

## I file grandi: 24 sopra le 1 000 righe

| file | righe | scoperte |
|---|---|---|
| `ImportWizardModal.svelte` | **4 927** | 708 |
| `TransactionBulkModal.svelte` | **3 349** | 158 |
| `DataTable.svelte` | **2 560** | 262 |
| `AssetModal.svelte` | **2 352** | 316 |
| `TransactionFormModal.svelte` | **2 260** | 153 |
| `DataTableColumnFilter.svelte` | 1 794 | 135 |
| `DateRangePicker.svelte` | 1 464 | 98 |
| `ScheduledInvestmentEditor.svelte` | 1 432 | 138 |

**Lo spezzettamento non alza la copertura di per sé: rende testabile ciò che oggi non lo è.**
La prova è già in casa — i quattro moduli estratti dal wizard sono al **100%**, mentre il
`.svelte` residuo è al 57,5%. Non perché quei moduli siano stati testati meglio, ma perché
prima erano dentro closure raggiungibili solo attraversando sette passi.

---

# «Il report dice 83%, tu dici 74,8%» — non c'è un numero solo

Il report HTML di monocart ne pubblica **cinque**, e mostra come titolo il più generoso:

| metrica | valore | cosa conta |
|---|---|---|
| **Bytes** | **83,17%** | byte del file eseguiti — include markup statico, CSS, stringhe |
| **Lines** | 80,35% | 73 796 / **91 843** righe non vuote |
| Functions | 74,73% | 7 450 / 9 969 |
| Statements | 69,84% | 27 708 / 39 675 — **la metrica gonfiata dalla doppia mappa** |
| **Branches** | **53,75%** | 12 307 / 22 896 — i rami decisionali |

Il mio 74,81% è una sesta cosa ancora: **righe che contengono almeno uno statement istanbul**
(24 052 / 32 151). Più severo di *Lines* perché esclude import, dichiarazioni di tipo, markup
e CSS — 92 000 righe contro 32 000, e quelle 60 000 di differenza sono quasi tutte coperte
per il solo fatto che il file viene caricato.

## Qual è il numero onesto

**Branches, 53,75%.** È l'unico che risponde alla domanda *«questo comportamento è stato
verificato?»* invece di *«questa riga è stata attraversata?»*. Un `if (err) log(err)` in cui
`err` è sempre vero risulta coperto al 100% per riga e al 50% per ramo — la riga è verde, la
decisione non è mai stata presa in entrambi i sensi.

Il confronto col backend chiarisce quanto sia largo il divario:

| | statement | branch | forbice |
|---|---|---|---|
| Backend | 92,39% | 82,64% | **9,8 pp** |
| Frontend | 69,84% | 53,75% | **16,1 pp** |

Il frontend non ha solo meno copertura: ha copertura più **superficiale**. Ogni componente è
attraversato dal percorso felice, e i rami di errore e di caso limite non sono percorsi.

## Cosa cambia per il lavoro

Finora abbiamo inseguito le **righe**, che è la ragione per cui il numero si muove piano: una
riga in più costa un test, un ramo in più spesso costa lo stesso test scritto meglio (lo
stesso montaggio con una prop diversa).

E attenzione a un dettaglio operativo: `./dev.py test coverage-report --lang js` classifica per
**statement**, cioè la metrica che la doppia compilazione gonfia. Per scegliere dove andare
conviene guardare i **rami scoperti**, non gli statement.
