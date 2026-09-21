# Analisi preliminare — U2 / SP15: privacy globale («nascondi valori»)

> **Cos'è questo documento.** Un'**analisi**, non un piano: non ha step, non ha `**Stato:**`, non si
> esegue. Il prefisso `analysis-` è deliberato — un audit che lo contasse fra i piani lo
> classificherebbe come «non completato» per sempre.
>
> **Cosa non è.** Non contiene codice di prodotto, test, migrazioni, chiavi i18n né viste ASCII del
> gate UX. Il piano d'implementazione sarà `plan-phase00PrivacyGlobalRound1-….prompt.md` in questa
> stessa cartella, con cross-link in entrambe le direzioni.

| | |
|---|---|
| **Sprint** | SP15 — task **U2** |
| **Fonte** | [`09_feedbackJobs/06_piano_sprint.md` §5 U2](../09_feedbackJobs/06_piano_sprint.md) (riga 311) |
| **Workstream** | J — lane 6158, worktree `e-alfy-literate-lamp` |
| **Revisione di osservazione** | **`1982c254b`** salvo dove diversamente attribuito |
| **Redatto** | 2026-09-01 |

> ⚠️ **Nota sul path.** Il piano di lavoro proponeva `22_privacy/`, ma `22_assetPricingRefactor/` e
> `23_transactionBatchRefactor/` esistono già. `06_piano_sprint.md:1077` prescrive di *«scegliere il
> prossimo `<NN_area>` libero in `Phase_0/`»*: il primo libero è **24**. Deviazione dal path
> approvato, con la ragione scritta.

---

## §0 — Decisioni già prese, e da chi

| # | Decisione | Chi | Stato |
|---|---|---|---|
| D1 | La preferenza è **locale al dispositivo**, non una proprietà dell'account | developer | ✅ fissata |
| D2 | La chiave è **nuda** (`librefolio-privacy`), non `lf_{userId}_privacy` | J, §4.2 | ✅ proposta con ragione |
| D3 | Nessun «mascherato di default»: il valore iniziale è quello persistito | conseguenza di §5.3 | ✅ chiusa |
| D4 | Nessuna protezione promessa contro DevTools, API, log, export grezzi | piano sprint | ✅ confine dichiarato §8 |
| D5 | **Le quantità restano VISIBILI**: si maschera solo il denaro. **Tre classi**, non due | developer, chiude Q3 | ✅ fissata |
| D6 | **Le percentuali restano visibili**, tutte, incluso il P&L percentuale | J, §1.6 | ✅ scelta dichiarata |
| D7 | I **campi di input** con importi sono **fuori scope**, esclusione motivata | coordinator, chiude Q4 | ✅ fissata |

**D1, la ragione del developer**, conservata perché è ciò che decide tutto il resto: alla domanda
*«attiva "nascondi valori", chiude il browser, rientra domani — cosa trova?»* la risposta è **ancora
nascosto, ma solo su quel dispositivo**. Il caso d'uso è **contestuale** — ufficio, bar, proiettore
collegato — non una proprietà dell'utente.

### D5 — Tre classi, non due. E la classe segue il formattatore

Il piano di sprint elencava le quantità fra i valori sensibili. **Il piano ha perso**, e la ragione
è la stessa che questa analisi aveva sollevato come Q3: `UnifiedLotsTable.svelte:162` usa la
quantità come **chiave di lettura della riga** (`open / original`, `PARTIALLY_CLOSED`). Mascherarla
rende la tabella illeggibile **a chi ha acceso la privacy apposta** — cioè fa fallire la funzione
esattamente nel momento in cui viene usata.

Parole del developer: *«chi guarda lo schermo non deve capire quanto vale, ma io devo continuare a
lavorare»*.

| classe | esempi | sotto privacy |
|---|---|---|
| **monetario** | prezzo, controvalore, P&L assoluto, dividendo, totale, costo medio (WAC) | **mascherato** |
| **strutturale** | quantità, numero di lotti, ticker, data, broker, valuta | **visibile** |
| **pubblico** | codice valuta, etichette, percentuali (→ D6) | **visibile** |

> **Il guadagno non è di copertura, è di metodo.** Il criterio smette di essere *«questo valore è
> sensibile?»* — giudizio da rifare a ogni sito — e diventa *«da quale formattatore esce?»*, che è
> meccanico:
>
> - esce da `formatCurrencyAmountPlain` / `…AmountHtml` ⇒ **monetario** ⇒ mascherato di default;
> - esce da `formatCurrencyCodeHtml` / `formatCurrencyForTooltip` ⇒ non è un importo ⇒ **mai**;
> - non passa da un formattatore di valuta ⇒ **strutturale** ⇒ visibile salvo dichiarazione.
>
> `maskable()` a livello formattatore smette così di essere un espediente per coprire le stringhe e
> diventa **il punto in cui la classificazione è decisa una volta sola**. I 61 siti di chiamata non
> devono sapere nulla.

**⚠️ La regola meccanica ha un buco, e §1.8 lo misura invece di ereditarlo.** Se esistono importi in
denaro che **non** passano da quei due formattatori, sono falsi negativi: la regola li dichiara
strutturali e li lascia in chiaro **in silenzio**. Ne ho trovati, e sono elencati in §1.8.

### Ramo scartato: preferenza come colonna `UserSettings`

Scritto come **scartato con la ragione**, non omesso: il silenzio su una strada scartata è
indistinguibile dal silenzio su una strada mai considerata, e «mettiamola nel profilo utente» verrà
riproposto.

| | locale (adottata) | colonna server (scartata) |
|---|---|---|
| idratazione | sincrona, all'init del modulo | dentro `appBootstrap.load()` (`appBootstrap.svelte.ts:70`) |
| segue l'utente fra dispositivi | ❌ | ✅ |
| costo | nessuno | migrazione Alembic incrementale + `api sync` + schema + client |
| modo di guasto | nessuno | su `state === 'blocked'` la preferenza resta ignota |

**Motivo dello scarto**: la portabilità fra dispositivi è *contraria* al requisito, non solo
superflua. Una preferenza che segue l'utente riattiva il mascheramento sul portatile di casa, dove
non serve, e non lo riattiva sul portatile dell'ufficio se l'ultima modifica è avvenuta altrove.

---

## §1 — Inventario delle superfici

> **Regola di lettura.** Un inventario è una misura e vale **con la data attaccata**. Ogni voce
> riporta la revisione in cui è stata osservata. Un elenco che dice «N superfici» senza dire *a quale
> revisione* afferma qualcosa che nessuno ha mai misurato.

### 1.1 — Correzione preliminare: il perimetro reale dei formattatori monetari

Una prima stima interna diceva *«`formatCurrency` in 26 file»*. **È falsa come lettura**: il simbolo
`formatCurrency` **non esiste**. Il conteggio era un match di **prefisso** su quattro funzioni
diverse con responsabilità diverse — e due di esse non rendono affatto un valore.

**Metodo di conteggio, dichiarato perché senza di esso i numeri non sono confrontabili.**
Perimetro `frontend/src`, **tutte le estensioni**. **Esclusi**: i file di test
(`.test.` · `.spec.` · `__tests__/`), perché non sono superfici viste da un utente e un inventario
di lavoro non deve prescriverne su di essi; e la **riga di definizione**, perché una definizione non
è un sito di chiamata. «Siti» = righe che contengono il simbolo **meno** le righe di `import`.
Controllo negativo eseguito sul metodo (simbolo inesistente → 0).

Misurato a `1982c254b` con quel metodo:

| simbolo | file | righe | import | **siti** | rende un **importo**? |
|---|---|---|---|---|---|
| `formatCurrencyAmountPlain` `:30` | **19** | 65 | 18 | **47** | ✅ sì, come **stringa** |
| `formatCurrencyAmountHtml` `:51` | **7** | 21 | 7 | **14** | ✅ sì, come **stringa HTML** |
| `formatCurrencyCodeHtml` `:75` | 4 | 16 | 4 | **12** | ❌ **no** — solo l'identità della valuta |
| `formatCurrencyForTooltip` | 2 | 5 | 1 | **4** | ❌ **no** — vedi sotto |

`table/DataTableColumnFilter.svelte` usa **solo** `formatCurrencyCodeHtml`: entra nell'unione dei
file ma **non ha nulla da mascherare**.

#### Due correzioni a una revisione precedente di questa stessa tabella

**(a) `formatCurrencyForTooltip` era nella colonna sbagliata.** L'avevo classificata fra i
formattatori di importo. La firma la smentisce, e l'output dei test la smentisce più della firma:

```
providerProbe.ts:72   export function formatCurrencyForTooltip(code: string | undefined): string
providerProbe.test.ts:110   formatCurrencyForTooltip('USD')  →  '🇺🇸 USD $'
providerProbe.test.ts:114   formatCurrencyForTooltip('GBP')  →  'GBP £'
```

**Prende un codice valuta, non un importo**: appartiene alla riga di `…CodeHtml`. Ed era anche
descritta come *«locale»*: è **esportata**, con consumatori in `ProviderAssignmentSection.svelte`
`:329,:350` e due usi interni a `providerProbe.ts` `:111,:122`.

> La direzione dell'errore è quella che nessuno controlla: **un helper che non mostra nulla di
> sensibile era stato incluso nel perimetro da mascherare.** È la forma speculare dell'errore di
> prefisso che questa stessa §1.1 corregge — là un numero gonfiato prescriveva lavoro inutile, qui
> una riga gonfiata prescriveva **mascheramento** inutile.
>
> Il controllo che avevo eseguito verificava che ogni simbolo **esistesse**, non che **facesse** ciò
> che la colonna affermava. **L'esistenza di un simbolo non è la prova della sua responsabilità**, e
> in tre casi su quattro la responsabilità era a un `grep` di distanza — nella firma.

**(b) La causa dei conteggi sbagliati era il perimetro: `grep -r` su `*.svelte` soltanto.**

**Escludeva i `.ts`** — cioè **proprio i `formatter` dei tooltip ECharts**, che sono l'evidenza
principale della tesi di §1.2 (*una stringa non si avvolge con un componente*). La conclusione era
giusta; **la misura che la sosteneva ne aveva escluso la prova più forte.**

> **Un perimetro che esclude l'evidenza principale produce un numero che nessuno contesta**, perché
> resta dello stesso ordine di grandezza di quello vero. Non avevo misurato poco: avevo misurato
> **in un posto dove la mia stessa conclusione non poteva apparire.**

Non era un problema di file di test, né di revisione — le due cause che sembravano ovvie. Contare i
test è la lezione sbagliata da portare via: **la lezione è controllare il perimetro.**

Conseguenza secondaria, comunque grave: i numeri (17/61 · 7/21 · 3/12 · 1/3) erano **non
riproducibili**. Ricostruiti a posteriori, **una riga sola su tre** combacia con un perimetro
dichiarabile. Righe che non condividono una definizione **non sono confrontabili fra loro** — il
difetto peggiore in una tabella, perché la tabella stessa invita a confrontarle.

> **Conseguenza metodologica**: il conteggio per prefisso sovrastima il lavoro e **nasconde la
> classificazione dentro il numero**. Le due funzioni `…AmountPlain` / `…AmountHtml` sono il vero
> perimetro — **61 siti di chiamata**; `…CodeHtml` e `…ForTooltip` (**16 siti**) sono la prova che
> una parte di ciò che *sembra* denaro è identità di valuta, che il piano classifica esplicitamente
> come **non sensibile**.

### 1.2 — Il formato dell'output decide la primitiva, e la misura lo dimostra

Letto `lib/utils/currency/currencyFormat.ts` per intero:

- **`formatCurrencyAmountHtml:51-73`** produce già un markup **separato per ruolo**:

  ```html
  <span class="currency-amount">1.000,00</span>
  <span class="currency-symbol">$</span> <span class="emoji-flag">🇺🇸</span>
  <span class="currency-code">USD</span>
  ```

  Il numero è già isolato in `.currency-amount`, distinto da simbolo, bandiera e codice.
  **Esiste quindi un punto di innesto preciso**, ed è più fine di «il campo».

- **`formatCurrencyAmountPlain:30-44`** restituisce una **stringa piatta**. Il suo docstring dice
  *«Suitable for tooltips, title attributes, plain-text contexts»* — cioè esattamente la classe che
  §1.4 chiama «fuori dal DOM renderizzato».

**Ma il docstring descrive l'intenzione, non l'uso.** Misurati i 61 siti di chiamata, la
destinazione prevalente è un'altra: l'output viene **concatenato dentro stringhe HTML costruite a
mano**, riconoscibili dal `</span>` che segue la chiamata. Esempi a `1982c254b`:

| sito | forma |
|---|---|
| `dashboard/ExposureTable.svelte` | `` …${formatCurrencyAmountPlain(value, …)}</span>` `` dentro una cella `HtmlCell` |
| `dashboard/PerformanceChart.svelte` | dentro il `formatter` del tooltip ECharts |
| `dashboard/ExposureTreemap.svelte` | idem |
| `brokers/lots/LotComparisonChart.svelte` | idem, 7 occorrenze |
| `transactions/wac/WacPreviewSection.svelte` | direttamente in un nodo di testo `</td>` |

> **Questa è la scoperta che governa il design delle primitive.** **47 dei 61 siti** che rendono un
> importo producono una **stringa piatta**, non un nodo. Una stringa non si avvolge in un componente
> Svelte. Quindi `SensitiveValue` **non può essere solo un componente**: deve esistere a livello di
> **formattatore**, altrimenti copre la minoranza dei siti e lascia scoperta la maggioranza —
> **senza segnalarlo**, perché i siti scoperti continuano a renderizzare correttamente il valore
> vero.

Consumatori del ramo HTML: `HtmlCell` (**6** file), `{@html}` (**21** file).

### 1.3 — Componenti di valore dedicati

| componente | file | nota |
|---|---|---|
| `TweenedValue` | 3 | animazione numerica: una transizione **verso** un valore mascherato va definita, non ereditata |
| `CompactCashCell` | 3 | cella cash compatta |

Il rapporto `3 + 3` contro `17 + 7` è il dato: **la superficie monetaria non è concentrata in
componenti riusabili**, è diffusa in chiamate dirette dentro il markup e dentro i formatter dei
grafici. È questa la ragione della taglia XL, e non «ci sono molte pagine».

### 1.4 — 🆕 Classe a sé: superfici che riproducono il valore **fuori dal DOM renderizzato**

Misurato `document.body` in `frontend/src`, esclusi test ed E2E: **41 occorrenze** a `1982c254b`.
Il coordinator ha misurato le stesse **41** su **`c75cf9150`**: il numero coincide, ma le due misure
restano attribuite ciascuna alla propria revisione.

| sotto-classe | siti (`path:riga`) | perché è una superficie |
|---|---|---|
| **clipboard** | `features/ai-export/aiExportClipboard.ts:169` · `utils/clipboard.ts:25` · `components/files/FilesTable.svelte:456` · `components/files/FileGrid.svelte:107` | un `textarea` con il **testo reale** viene inserito nel body per copiare |
| **download / export** | `components/files/FilesTable.svelte:508,541` · `api/backupDownload.ts:53` | un `<a download>` nel body porta fuori il file |
| **cross-document** | `components/support/shareNavigation.ts:34` | `tab.document.body.append(link)` — scrive nel `document` di **un'altra scheda** |
| **clone di misura** | `utils/layout/labelShrink.ts:59,61` | clona un nodo nel body per **misurare la larghezza del testo** |
| **portali** | §1.5 | il nodo **esce dall'albero del componente** |
| **attributi** | da inventariare campo per campo | `title`, `aria-label`, `data-*`, testo per screen reader |

Due casi meritano di essere nominati perché **non sono difetti evidenti**:

- **Clipboard** — schermo mascherato, appunti con i numeri veri. È **esfiltrazione per funzione
  legittima**: non è ovvio che sia sbagliato, un utente con privacy attiva potrebbe *volere* copiare
  i dati reali. È ovvio invece che debba essere una **scelta scritta** e non un effetto collaterale.
  → domanda aperta **Q1** (§6).
- **Clone di misura** — `labelShrink` misura la larghezza del testo per decidere il troncamento.
  Maschera e valore reale hanno larghezze diverse: o si misura il testo **reale** (e il valore reale
  transita per il body) o si misura la **maschera** (e il layout viene deciso su una stringa che
  l'utente non vedrà mai quando riattiva la privacy). → **Q2** (§6).

### 1.5 — Portali e grafici: il caso peggiore della feature

**Due meccanismi di portale con nomi diversi**, quindi un inventario per grep su un nome solo è
incompleto **per costruzione**:

| meccanismo | definizione | consumatori |
|---|---|---|
| azione generica | `lib/actions/portal.ts:14` | `ui/date/DateRangePicker.svelte:1367` · `assets/CellDateRange.svelte:129` |
| funzione locale | `features/ai-export/AiExportMenu.svelte:81` (`portalToBody`) | stesso file, `:308` |
| portale ad hoc | `ui/feedback/Tooltip.svelte:232-240` | interno |
| lock di scroll | `ui/modals/ModalBase.svelte:168,195` · `layout/Header.svelte:155,166` | non spostano valore, ma toccano il body |

**Grafici ECharts in produzione: 14** (escluso lo stub di test `__tests__/harness/`). Il
comportamento del tooltip è **per-grafico, non globale** — e in questo repo è già cambiato in
entrambe le direzioni:

| grafico | riga | configurazione | tooltip nel body? |
|---|---|---|---|
| `brokers/lots/LotGanttChart.svelte` | `:976` | `appendTo: 'body'` | ✅ sì |
| `charts/CandlestickChart.svelte` | `:495` | `appendToBody: true` | ✅ sì |
| `charts/LineChart.svelte` | `:661` | `appendToBody: true` | ✅ sì |
| `dashboard/PerformanceChart.svelte` | `:961` | `appendTo: () => document.body` | ✅ sì |
| `dashboard/AllocationHistoryChart.svelte` | `:555-561` | **rimosso** con bugfix documentato | ❌ no |
| `dashboard/GrowthChart.svelte` | `:700-706` | **rimosso** con bugfix documentato | ❌ no |
| `dashboard/ExposureTreemap.svelte` | `:606-618` | **rimosso**, cita `fcdd89e8` «Fix mobile tooltip scroll offset» | ❌ no |
| gli altri 7 | — | non configurato | ❌ no (default) |

> **Perché è il caso peggiore.** Un nodo portato su `document.body` **esce dall'albero del
> componente**. Qualunque `SensitiveRegion` basata sulla **discendenza DOM** non lo contiene — e
> **fallisce senza segnalarlo**: la maschera è presente, il tooltip la scavalca. Peggio: quattro
> grafici stanno in questo stato *oggi*, e i tre che ne sono usciti possono rientrarci con il
> prossimo bugfix di z-index, come è già successo.
>
> **Un inventario di «quali grafici» è quindi inutile da solo**: serve la configurazione di
> ciascuno, e serve che la primitiva non dipenda dalla discendenza.

Meccanismo di invalidazione disponibile per i tooltip già aperti: `dispatchAction` (**64** siti).

### 1.6 — Il lato **non** sensibile, misurato

Il piano classifica come non sensibili: quotazioni pubbliche, tassi FX, percentuali, rapporti, date,
conteggi. Misurato a `1982c254b` **con il metodo canonico di §1.1** (non con il perimetro `*.svelte`
ritirato, che affliggeva anche questa tabella):

| simbolo | file | siti | classificazione |
|---|---|---|---|
| `formatPercent` (`utils/core/formatPercent.ts:35`) | 5 | 37 | **non sensibile** → **D6** |
| `formatDate` | 13 | 54 | **non sensibile** |
| `formatCurrencyCodeHtml` | 4 | 12 | **non sensibile** — identità della valuta |
| `formatQuantity` (`brokers/lots/lotGanttChartHelpers.ts:104`) | 5 | 24 | **non sensibile** → **D5**, risolto |

#### Le quantità: contestate, e risolte contro il piano di sprint (D5)

Il piano le dichiarava sensibili, e la ragione era buona: quantità × quotazione pubblica
**ricostruisce il controvalore**, quindi mascherare il controvalore e mostrare la quantità è una
protezione che si annulla da sola.

Ma in `brokers/lots/UnifiedLotsTable.svelte:162-171` la quantità è la **chiave di lettura della
riga**: `quantityCell` rende `aperta / originale` e distingue un lotto `PARTIALLY_CLOSED` da uno
intero. Mascherandola, la tabella diventa illeggibile *anche per chi ha attivato la privacy
volontariamente* — cioè la funzione **fallisce nello scenario che la giustifica**.

**Decisione del developer: quantità VISIBILI.** Il rischio di ricostruzione è accettato e
dichiarato: chi guarda lo schermo non deve capire *quanto vale*, ma il proprietario deve poter
continuare a lavorare. Il confine di §8 copre anche questo — non si promette segretezza
crittografica, si toglie la leggibilità a colpo d'occhio.

#### D6 — Le percentuali restano visibili, **tutte**. E la ragione è che la distinzione non è esprimibile

L'obiezione da battere era buona: una percentuale di allocazione non rivela un patrimonio, ma un
**P&L percentuale rivela quanto stai guadagnando**. Stessa unità, sensibilità diversa.

Misurato — e la misura chiude la questione nella direzione opposta:

```
utils/core/formatPercent.ts:35
  formatPercent(value, {scale = 1, signed = true, empty = '—', digits = 2})
                        ↑ nessun parametro semantico: la firma non sa cosa sta formattando
```

Il proxy ovvio — *«il P&L è `signed`, l'allocazione no»* — **non tiene**, e la controprova è a un
`grep` di distanza:

```
fx/FxTable.svelte:127   formatDeltaPct → `${sign}${val.toFixed(2)}%`     signed  ✅
                        ma è un delta di tasso FX, cioè un dato PUBBLICO
```

> **La distinzione che servirebbe non è esprimibile nel punto in cui andrebbe applicata.**
> Applicarla richiederebbe un giudizio su ciascuno dei 37 siti — reintroducendo esattamente il costo
> che la regola di D5 elimina — e sbagliarlo sarebbe silenzioso.

**Decisione**: percentuali visibili. Un `+12%` non rivela un patrimonio, e la percentuale di un
numero mascherato non moltiplica nulla.

**Rischio residuo, dichiarato e non risolto qui**: una percentuale accanto a un **importo visibile**
diventa un moltiplicatore su un numero leggibile. È un rischio di **composizione**, non di
formattatore — non catturabile dove si decide la classe. Va nella checklist per-sito di §7.2.

### 1.7 — Voci aperte attribuite (superfici che **non esistono ancora** in questo albero)

> Entrano come **voci aperte**, mai come assenze. *Un'assenza si legge «non c'è nulla da
> proteggere»; una voce aperta «qui arriverà qualcosa da proteggere».*

| workstream | superficie attesa | stato a `1982c254b` | azione |
|---|---|---|---|
| **I** (SP07) | candele sintetiche, nuove viste P&L | non presente in questo albero | da inventariare **dopo** il freeze di I |
| **D** (SP14) | report Broker, tabelle allocatore/PAC | non presente in questo albero | da inventariare **dopo** il freeze di D |

I relativi file si **leggono** per inventariarli e **non si scrivono**. L'inventario va rifatto —
non integrato a memoria — sulla revisione in cui quelle superfici esistono.

### 1.8 — 🔴 Falsi negativi: denaro che **non** passa dai due formattatori

La regola meccanica di D5 — *«da quale formattatore esce?»* — ha un presupposto che va misurato e
non ereditato: **sapere quanti formattatori esistono**. Misurato a `1982c254b`, non sono quattro.

| # | sito | cosa rende | perché sfugge |
|---|---|---|---|
| 1 | 🔴 `risk/riskAnalysisHelpers.ts:130` | `formatCurrencyAmount(value, currency, locale)`, **esportata** → `Intl.NumberFormat({style:'currency'})` | **è un quinto formattatore di importi**, e non vive in `currencyFormat.ts` |
| 2 | `risk/RiskAnalysisPanel.svelte:737` | `formatAmount` → delega a #1 | eredita il buco di #1 |
| 3 | `dashboard/GrowthChart.svelte:692` | `fmtCurrency` locale: `` `${baseCurrency} ${v.toLocaleString(…)}` `` | template literal, nessuna delega |
| 4 | `brokers/lots/LotComparisonChart.svelte:245` | `formatAxisCurrency` → `Intl.NumberFormat({style:'currency', notation:'compact'})` | il file **delega altrove**, ma non qui: un'etichetta d'asse `€12K` rivela l'ordine di grandezza |
| 5 | `charts/MeasurePanel.svelte:257` | `fmtValue` → `toFixed(4)`, **senza valuta**, su un grafico di prezzo | ⚠️ **sito di giudizio, non meccanico** — vedi sotto |
| 6 | `transactions/events/EventCreateMiniModal.svelte:73` | `formatAmount()` scrive `eventAmount`, cioè un **`value` di input** | non è un rendering: conferma che l'esclusione **D7** è reale, non teorica |

Controprova sul verso opposto, perché un elenco di falsi negativi ha bisogno del suo controllo
positivo: `ai-export/templates/snapshotDataRenderer.ts:226` usa `Intl.NumberFormat({style:'currency'})`
**senza rendere nulla** — ne legge solo `resolvedOptions().maximumFractionDigits`. Non è un falso
negativo, ed è esattamente il tipo di riga che un elenco costruito sul nome dell'API avrebbe incluso
per sbaglio.

> **La direzione dell'errore è la peggiore possibile.** Un importo che esce da `risk/` sarebbe stato
> classificato **strutturale** dalla regola di D5, cioè **lasciato in chiaro, in silenzio** — il
> guasto esatto che il default `personal` esiste per impedire.
>
> **Una regola meccanica sbagliata è più pericolosa di un giudizio sito per sito**, perché il
> giudizio lascia il dubbio e la regola lo toglie.

#### La riparazione non è allungare l'elenco: è un gate

Aggiungere `formatCurrencyAmount` all'insieme registrato ripara i cinque di oggi e **non ripara il
sesto**, che nascerà e verrà classificato strutturale in silenzio, sotto un documento che nel
frattempo dichiara completezza.

L'àncora non può essere il nome di un file né la cartella — §1.1(b) e questa stessa sezione sono due
istanze dello stesso errore. Deve essere **l'API che rende il denaro**, che è osservabile
indipendentemente da dove vive il codice. Nei sei siti misurati i modi sono due:

```
A)  Intl.NumberFormat(..., {style: 'currency'})      #1, #4, e currencyFormat.ts stesso
B)  template literal con una valuta interpolata       #3
```

**Proposta (non lavoro autorizzato — l'autorizzazione è del developer)**: un test che enumera i siti
corrispondenti ad A e B e **fallisce quando ne compare uno fuori dall'insieme registrato**.

- **Valore**: non è trovare i cinque di oggi — quelli sono già qui. È **fallire il giorno del sesto**.
- **Costo**: S — un test di sorgente, nessuna dipendenza, nessuna lane; più la manutenzione
  dell'insieme registrato a ogni aggiunta legittima.
- **Confine esplicito**: `MeasurePanel:257` (#5) **resta fuori dal gate** e dentro l'elenco come sito
  di giudizio. Non ha valuta: catturarlo richiederebbe di inseguire `toFixed` su numeri qualsiasi.
  > *Un gate che sbaglia in modo fastidioso viene spento, e allora non protegge più nemmeno i casi
  > che prendeva bene.* Un gate rumoroso è un gate futuro assente.

---

## §2 — Contratto di mascheramento

> **La parte negativa viene per prima**, perché è quella che un'implementazione plausibile viola
> senza accorgersene.

### 2.1 — Cosa «mascherato» **non** significa (parte negativa, vincolante)

Quando la privacy è attiva, il valore reale **non deve esistere**:

1. ❌ **sotto un blur CSS** — `filter: blur()` è cosmetico: il testo resta nel DOM, si seleziona, si
   copia, si legge in DevTools e lo legge uno screen reader;
2. ❌ **in un attributo `title`** — è il caso documentato di `formatCurrencyAmountPlain`, il cui
   docstring lo indica come destinazione naturale;
3. ❌ **in `aria-label`, `aria-valuetext` o in qualunque testo per tecnologie assistive** — una
   maschera che protegge lo schermo e non l'uscita audio protegge la persona sbagliata;
4. ❌ **in un attributo `data-*`** — inclusi gli attributi usati dai test;
5. ❌ **in un nodo nascosto** con `display:none`, `visibility:hidden`, `opacity:0`, `clip-path` o
   fuori viewport;
6. ❌ **in un tooltip, in un portale o in un canvas** che al momento del paint non discende dal
   componente mascherato (§1.5);
7. ❌ **nel testo che il clipboard copia**, salvo decisione esplicita contraria (**Q1**).

### 2.2 — Cosa «mascherato» significa (parte positiva)

1. ✅ il valore reale **non viene renderizzato**: viene **sostituito prima** di entrare nel markup,
   non coperto dopo;
2. ✅ il segnaposto ha **forma stabile** — per esempio `••••` — e **non** dipende dal valore reale:
   nessuna randomizzazione di cifre reali, nessuna lunghezza proporzionale all'importo. *Un
   segnaposto la cui larghezza varia col valore è un canale laterale a bassa risoluzione, ed è
   peggio di un segnaposto onesto perché sembra sicuro;*
3. ✅ **l'identità della valuta resta visibile** — `$ 🇺🇸 USD` non è un valore sensibile
   (§1.1), ed è ciò che rende la tabella ancora leggibile;
4. ✅ **la struttura del layout non cambia**: righe, colonne e altezze restano, per non segnalare
   quali celle contenessero un valore;
5. ✅ **è reversibile senza ricaricare**: il toggle agisce sul rendering corrente, inclusi tooltip
   già aperti (`dispatchAction`, §1.5) e portali già montati;
6. ✅ **si applica prima del primo paint utile**, garanzia già fornita dal gate esistente (§5.3).

### 2.3 — Verificabilità del contratto

Un contratto la cui violazione non è osservabile non è un contratto. Forme di verifica proposte (il
piano d'implementazione le trasformerà in test, tramite `test-author`):

| clausola | come si osserva una violazione |
|---|---|
| 2.1.1 – 2.1.5 | il testo reale non compare in `container.innerHTML` né in `outerHTML` del documento |
| 2.1.3 | il nome accessibile calcolato non contiene il valore |
| 2.1.6 | asserzione sul `document.body`, non sul sottoalbero del componente |
| 2.2.2 | due valori di ordini di grandezza diversi producono **lo stesso** segnaposto |
| 2.2.5 | toggle con un tooltip aperto: il contenuto cambia senza rimontare il grafico |

> ⚠️ **Attenzione alle asserzioni negative.** «Il valore non compare» è vera quando il mascheramento
> funziona **e** quando il test non sta misurando nulla — per esempio se il componente non ha
> ricevuto il prop. Ogni test negativo deve essere accompagnato da un **controllo positivo** sullo
> stesso oggetto (con privacy spenta, il valore *compare*), altrimenti resta verde per la ragione
> sbagliata. Lezione già pagata in questo workstream.

---

## §3 — Primitive proposte (design, non implementazione)

### 3.1 — Il vincolo che le determina

Da §1.2: **47 dei 61 siti producono una stringa piatta**, non un nodo; da §1.5: **4 grafici su 14**
rendono il valore in un nodo che non discende dal componente. Ne segue che:

> Una primitiva **solo a componente** copre la minoranza dei siti e fallisce in silenzio sul resto.
> Una primitiva **solo a formattatore** non sa distinguere una quotazione pubblica da un
> controvalore personale, perché **è la stessa funzione a rendere entrambi**.

Servono quindi **tre** livelli, non due, e il terzo è quello che il piano non nominava.

### 3.2 — `maskable(...)` — livello formattatore (il livello portante)

**Responsabilità**: decidere, *prima* di produrre la stringa, se restituire il valore o il
segnaposto.

**Forma proposta**: estendere `CurrencyAmountFormatOptions`
(`lib/utils/currency/currencyFormat.ts:15`) con un campo di classificazione **esplicito**:

```ts
interface CurrencyAmountFormatOptions {
    showSign?: boolean;
    minFraction?: number;
    maxFraction?: number;
    /** Omesso ⇒ trattato come denaro personale ⇒ mascherato. */
    sensitivity?: 'personal' | 'public';
}
```

#### ⚠️ Divergenza dichiarata: la tassonomia ha **tre** classi, questa enum ne ha **due**

D5 stabilisce tre classi — monetario, strutturale, pubblico. Qui ne compaiono due, e **non è una
svista**: a livello di formattatore di valuta la classe *strutturale* è **irraggiungibile per
costruzione**. Una quantità, una data, un conteggio non passano da `formatCurrencyAmount*`; se ci
passassero, il difetto da correggere sarebbe il sito, non l'enum.

Aggiungere `'structural'` creerebbe uno stato che non può essere raggiunto correttamente e che
**qualcuno userebbe comunque** per silenziare il mascheramento di un valore monetario — cioè
esattamente il modo di guasto silenzioso che il default `personal` esiste per impedire.

**Cosa resta binario e perché**: dentro il formattatore la sola domanda sensata è *«questo importo è
di chi guarda o è pubblico?»*. Il caso `public` non è teorico — una **quotazione di mercato** è
formattata come valuta ed è un dato pubblico. È per quello che serve l'uscita esplicita.

| classe D5 | arriva a `maskable()`? | valore di `sensitivity` |
|---|---|---|
| monetario personale | sì | omesso, o `'personal'` |
| monetario pubblico (quotazione, tasso) | sì | `'public'`, **esplicito** |
| strutturale (quantità, data, conteggio) | **no, per costruzione** | *nessuno* — non passa di qui |

**Regola di default: omesso ⇒ `personal` ⇒ mascherato.** La ragione è un'asimmetria di modo di
guasto, la stessa che governa §4.2:

| errore | esito |
|---|---|
| dimentico di classificare un valore **pubblico** | viene mascherato ⇒ **visibile**, l'utente lo nota e lo segnala |
| dimentico di classificare un valore **personale** (se il default fosse `public`) | resta in chiaro ⇒ **silenzioso**, e l'utente crede di essere protetto |

> Un default sicuro converte una dimenticanza in un difetto **visibile**. Per una feature di privacy
> questa è l'unica direzione accettabile.

**Copertura**: `formatCurrencyAmountPlain` (**47 siti**) e `formatCurrencyAmountHtml` (**14 siti**)
— incluse **tutte** le stringhe che finiscono nei `formatter` dei
tooltip ECharts, quindi **anche i 4 grafici portati nel body**, perché il mascheramento avviene
*prima* che la stringa esista, e la posizione del nodo diventa irrilevante.

**Non copre** `formatCurrencyCodeHtml` né `formatCurrencyForTooltip` (§1.1: **nessuna delle due
rende un importo**). Includerle sarebbe mascherare l'identità della valuta, che il piano classifica
come non sensibile — ed è l'errore che §1.1(a) corregge.

⚠️ **E non copre i sei siti di §1.8**, che rendono denaro senza passare di qui. Il livello
portante copre 61 siti su 61 *di quelli che lo attraversano*: è una copertura completa **del
canale**, non della superficie. La differenza è tutta §1.8, ed è il motivo per cui quella sezione
propone un gate invece di un elenco.

### 3.3 — `SensitiveValue` — livello componente

**Responsabilità**: rendere un valore che **non** passa da un formattatore monetario — quantità
(`formatQuantity`, 5 file, subordinato a **Q3**), campi di input, celle costruite a mano.

**Firma proposta** (design):

```
SensitiveValue
  value          il valore reale, mai renderizzato quando mascherato
  sensitivity    'personal' | 'public'      default: 'personal'
  format         (v) => string              formattatore applicato SOLO se visibile
  placeholder    stringa a forma stabile    default: '••••'
```

**Responsabilità che non ha**: non applica blur, non nasconde, non copre. **Sceglie cosa
renderizzare**, e il valore reale non entra mai nel markup quando la privacy è attiva.

**Caso duro dichiarato**: un `<input value={…}>` con un importo reale. Il valore è nell'attributo, e
la DoD vieta di renderizzarlo «sotto patina». Va progettato nel piano d'implementazione, non
elencato qui: probabile soluzione è un input in modalità segnaposto che espone il valore reale solo
al focus esplicito — ma è **Q4** (§6), perché tocca l'usabilità dei form di modifica.

### 3.4 — `SensitiveRegion` — **non** è un valore più grande

**L'errore da evitare è trattarla come un contenitore.** Una regione che maschera per discendenza
DOM:

- ❌ non copre un canvas, perché il canvas **disegna** il valore: non c'è un nodo da sostituire;
- ❌ non copre un tooltip portato su `document.body`, perché al paint non discende più da lei
  (§1.5);
- ❌ e in entrambi i casi **fallisce senza segnalare**.

**Contratto proposto**: `SensitiveRegion` non è un wrapper DOM ma un **contesto** che dichiara una
politica per i discendenti *logici* — inclusi quelli che al paint non sono discendenti *fisici*.
Due responsabilità concrete:

1. **Per i grafici**: la regione non copre, **propaga la classificazione al `formatter`**, che già
   costruisce la stringa (§3.2). La sostituzione avviene a monte del rendering, quindi funziona
   identicamente per i 4 grafici nel body e per i 10 che non ci sono.
2. **Per i canvas che disegnano numeri fuori dal formatter** — etichette di assi, `dataLabel` —
   serve **sostituzione a livello di serie**, cioè un'opzione ECharts rigenerata, non una patina.

**Invalidazione**: al cambio di stato, i tooltip già aperti vanno chiusi/ricalcolati
(`dispatchAction`, 64 siti) e i portali già montati vanno rivalutati. Senza questo, il toggle
protegge il prossimo hover e non quello in corso — cioè fallisce esattamente nell'istante in cui
l'utente lo preme perché qualcuno è entrato nella stanza.

---

## §4 — Design dello store

### 4.1 — Idratazione: **non** su `appBootstrap.ready`

Verificato contro il codice, perché la domanda è stata posta esplicitamente. La risposta si
**sdoppia**, e le due domande erano state fuse:

| domanda | risposta |
|---|---|
| *quando è sicuro dipingere?* | `appBootstrap.ready` — **e il gate esiste già**, non c'è nulla da aggiungere (§5.3) |
| *quando idratare la preferenza?* | **non lì** |

Tre ragioni misurate a `1982c254b`:

1. **`load()` è I/O di rete** — `appBootstrap.svelte.ts:70` esegue
   `Promise.allSettled([userSettings.load(), onboarding.load(), globalSettings.load()])`.
   Una lettura `localStorage` è **sincrona**: non ha motivo di attendere un I/O che può fallire.
2. **`ready` può restare falso per sempre** — `:135-136` è
   `get ready() { return state === 'ready' || state === 'degraded'; }`;
   su `blocked` (`:77`) resta falso, **ma `OnboardingBootstrapBlock` viene renderizzato comunque**
   (`routes/(app)/+layout.svelte:194`, `routes/+page.svelte:110`). Una preferenza che non si idrata
   sul cammino d'errore è un buco latente dal momento in cui una superficie fuori dal gate mostra
   un valore.
3. **`appBootstrap` è un consumatore pari grado, non la sorgente** — non *aspetta* di conoscere
   l'identità: la **chiede**, con `getClientSessionUserId()` a `:55`, la fissa a `:66`
   (`loadedUserId = userId`) e si difende dal cambio account a `:71`. Appendere la privacy a
   `appBootstrap.ready` la farebbe dipendere da un **fratello** invece che dalla **sorgente**,
   ereditandone i modi di guasto.

**Design adottato**: lettura sincrona **all'inizializzazione del modulo**, senza sottoscrizione,
senza resetter, senza attesa — conseguenza diretta di §4.2. Il valore è idratato prima di qualunque
render, perché il modulo dello store è importato dai formattatori e inizializza al caricamento del
grafo dei moduli, cioè **prima della prima chiamata di formattazione**.

> ⚠️ **Correzione: `themeStore` non è il precedente di questo.** Una revisione precedente scriveva
> *«come fa già `themeStore`»*. Misurato: `themeStore.ts` **non ha nessuna lettura a livello di
> modulo** — l'unica riga di modulo è `:11` (`STORAGE_KEY`), e ogni lettura è **pigra**, dentro
> `getStoredThemePreference()`, chiamata dai 3 consumatori (`ThemeToggle:29`, `AboutTab:123`,
> `PreferencesTab:105`).
>
> **Il vero precedente di lettura anticipata è altrove, e dice la cosa opposta di quella che
> serviva.** Il tema evita il flash con uno **script inline in `app.html:14-27`**, eseguito *prima
> del primo paint* e del caricamento dei moduli — con il suo `try { … } catch (e) {}` attorno a
> `getItem`, a differenza dello store.
>
> **La privacy non ha bisogno di quello script**, e la ragione è §5.3: nessun importo è dipinto prima
> di `appBootstrap.ready`, mentre la classe `dark` sull'`<html>` è nel primo paint per definizione.
> È la stessa misura di §5.3 vista dall'altro lato — *il tema ha bisogno del pre-paint perché* **è**
> *il paint; il denaro no, perché arriva dopo il gate.*

### 4.2 — Forma della chiave: **nuda**, `librefolio-privacy`

D1 dice «locale al dispositivo» ma non dice se la chiave sia per-utente. Le due letture sono
entrambe difendibili; questa analisi sceglie la chiave nuda e ne scrive il perché, **perché una
chiave lasciata implicita si legge come dimenticanza**.

**Precedente misurato.** Il repo ha già tre chiavi **non** scoped per utente:

| chiave | file | categoria |
|---|---|---|
| `librefolio-theme` | `stores/app/themeStore.ts:11` | preferenza di **presentazione sullo schermo** |
| `librefolio-locale` | `stores/app/language.ts:16` | lingua dell'interfaccia |
| `global_settings` | `stores/app/globalSettings.ts:49` | cache di impostazioni globali |

e un pattern per-utente `lf_{userId}_{base}` (`utils/storage.ts:23`) con **9** consumatori.
**Verificato: `librefolio-theme` non è resettato da nessuno dei 22 resetter di sessione** —
sopravvive al logout e al cambio account, esattamente come deve fare la privacy.

**Tre argomenti a favore della chiave nuda, in ordine di forza.**

1. **Comportamentale — è l'unico che soddisfa il caso d'uso dichiarato.** Con una chiave per-utente,
   al cambio di account la privacy assume il valore dell'*altro* account, che può essere «spenta».
   Cioè: i valori ricompaiono **durante un cambio di account fatto davanti al proiettore**, che è
   letteralmente la situazione per cui la feature esiste. La chiave nuda sopravvive alla
   transizione, come il tema.
2. **Asimmetria del modo di guasto.** Chiave nuda: l'utente B sullo stesso dispositivo eredita
   privacy **attiva** ⇒ **sovra-protezione**, visibile, un clic per annullarla. Chiave per-utente
   scritta con l'helper sbagliato (§5.2): A eredita la preferenza di B, che può essere **spenta**
   ⇒ **sotto-protezione silenziosa**, e l'utente crede di essere protetto. Per una feature di
   privacy l'asimmetria decide.
3. **Categoria.** La privacy contestuale descrive **lo schermo che si sta guardando**, non chi è
   loggato — la stessa categoria del tema, che è già nudo per questa ragione.

**Costi, dichiarati.**

- **Esce dal perimetro di `getUserStorage`**, quindi §5.2 non si applica più a U2. È una perdita di
  coerenza con il pattern dominante, ma **elimina un intero modo di guasto** invece di doverlo
  evitare a ogni chiamata.
- **Rivela**, a un secondo utente sullo stesso browser, che *qualcuno* su questo dispositivo usa la
  modalità privacy. `librefolio-theme` già rivela la stessa classe di informazione; l'impatto è
  giudicato trascurabile, ma è **scritto**, non taciuto.
- Non esiste una preferenza per-utente da mostrare nel profilo: il controllo nelle impostazioni è un
  **controllo locale**, coerente con D1.

### 4.3 — Superficie dello store

| elemento | forma |
|---|---|
| stato | `boolean` — privacy attiva / spenta |
| persistenza | `localStorage['librefolio-privacy']`, scrittura a ogni toggle |
| idratazione | sincrona all'init del modulo, guardia `typeof` **+** `try/catch` come `storage.ts:33-34,47-48` |
| reset di sessione | **nessuno** — la preferenza deve sopravvivere a logout e cambio account (§4.2.1) |
| effetti collaterali al toggle | invalidazione tooltip/portali (§3.4) |

> ⚠️ **Correzione: il precedente è `storage.ts`, non `themeStore`.** Una revisione precedente di
> questa riga citava `themeStore:29` come esempio di `try/catch`. È **falso**: `themeStore` ha la
> sola guardia `typeof`, in lettura (`:29`) e in scrittura (`:51`). Il solo `try/catch` su
> `localStorage` in `utils/` sta in `storage.ts` (`:34` lettura, `:48` scrittura), con la ragione già
> scritta nel codice — *«quota exceeded in private browsing»*.
>
> La differenza non è di stile. `typeof` risponde a **«esiste `localStorage`?»**, `try/catch` a
> **«la chiamata può fallire?»** — e in Safari privato, a quota superata o con lo storage negato,
> la prima passa e `setItem` **lancia**.
>
> **Modo di guasto che ne segue, e che vincola il passo 1.** Un `setItem` che lancia durante il
> toggle lascia lo stato **acceso in memoria e spento su disco**: la sessione corrente maschera, il
> reload no. La privacy fallisce nella direzione in cui non si vede — la stessa asimmetria che
> governa il default di §3.2. Quindi la scrittura va protetta **e** il suo esito va considerato:
> fallire in silenzio qui significa promettere una protezione che al reload non c'è.
>
> *(`themeStore:51` ha lo stesso buco latente. Non è nel perimetro di U2 e non viene toccato —
> §8 vale anche verso il basso. È annotato perché citarlo senza annotarlo lo trasformerebbe di nuovo
> in un precedente da copiare.)*

---

## §5 — Verifica delle tre trappole nominate dal piano di sprint

> Il piano ha settimane; i file no. Ogni trappola è stata **verificata contro il codice**, non
> citata.

### 5.1 — «Il primo `ClientSessionState.transition` non esegue i resetter» → ✅ **VERA**

`stores/app/clientSession.ts:43-50`: al primo ingresso il metodo imposta id e generazione e
**ritorna senza iterare i resetter**. Confermata alla lettera.

**Ma il piano si ferma un passo prima del rimedio.** A `:48` il primo ramo chiama comunque
`userIdStore.set(normalizedNext)`: l'identità iniziale **è già osservabile**, ed è esportata come
`clientSessionUserId` (`:88`). Una preferenza per-utente deve quindi **sottoscrivere** quel canale,
non registrare un resetter — la sottoscrizione copre identità iniziale *e* cambi con un solo
meccanismo.

**Perché nessuno l'aveva notato**: i **22** resetter registrati in produzione sono tutti
**invalidatori di cache**, e per un invalidatore il no-op al primo ingresso è **corretto** — non c'è
nulla da invalidare. Una preferenza da **idratare** ha il requisito opposto.

> **Il comportamento non è un difetto**: è giusto per ogni consumatore esistente e sbagliato per il
> primo che arriva. Scrivere «il primo `transition` è rotto» perde esattamente questa distinzione.

⚠️ **Non applicabile a U2** dopo §4.2: con una chiave di dispositivo non c'è identità da
sottoscrivere. La voce resta perché è **vera** e perché la prossima preferenza per-utente ci
inciamperà.

### 5.2 — «`getUserStorage` legge lo store auth, che può essere ancora l'account precedente» → ✅ **VERA E RAGGIUNGIBILE**

`utils/storage.ts:23` fa `get(currentUser)`. La domanda che decide è l'**ordine**. Misurato su
**tutti e quattro** i rami di `stores/app/auth.ts`:

| ramo | righe | ordine osservato |
|---|---|---|
| login | `:63` → `:65` | `transitionClientSession(id)` **prima** di `update({user})` |
| logout | `:149` → `:150` | `transitionClientSession(null)` **prima** di `set({user:null})` |
| `checkAuth` ok | `:176` → `:177` | transizione **prima** dell'`update` |
| `checkAuth` ko | `:188` → `:190` | transizione **prima** dell'`update` |

**Nessuna eccezione**: dentro un resetter, `get(currentUser)` è **sempre** l'account precedente. Il
fallback aggrava — `userId ?? 'anon'` fa leggere `lf_anon_…` invece di fallire.

**Il rimedio esiste già ed è in produzione**: `stores/chartSettingsStore.svelte.ts:72` costruisce la
chiave con `getClientSessionUserId()`. `this.userId` è assegnato **prima** del corrispondente `set`
su entrambi i rami — `:46` prima di `:48`, `:54` prima di `:69` — e `getUserId()` lo restituisce a
`:74`: la correttezza è **per costruzione dell'ordine interno**, non per convenzione.

> **La trappola vera**: esistono due helper che producono la **stessa identica forma di chiave**
> `lf_{id}_{base}` e differiscono **solo nel momento in cui leggono l'identità**. Sono
> intercambiabili all'occhio e non nel comportamento, e l'errore **non solleva un'eccezione**:
> produce la preferenza dell'**account sbagliato**.

**Domanda aperta, non asserzione**: i 9 consumatori attuali di `getUserStorage` (`ViewModeToggle`,
`Sidebar`, `PositionsPanel`, `WacPreviewSection`, `TransactionBulkModal`, `DataTable`,
`files/+page`, `(app)/+layout`) leggono **a mount**, non dentro una transizione, quindi
probabilmente non raggiungono il difetto. **Da verificare, non da dichiarare.**

⚠️ **Non applicabile a U2** dopo §4.2 — vedi il costo dichiarato.

### 5.3 — «Nessun flash iniziale del dato con privacy persistita» → 🔒 **DOMANDA CHIUSA: il flash non è possibile**

**Registrata come chiusa con la ragione, non omessa**, perché la deduzione che porta a riaprirla è
plausibile e qualcuno la rifarà.

**La deduzione plausibile.** `app.html:14-23` applica il tema **prima del primo paint**;
`themeStore.ts:11` conferma che `'librefolio-theme'` è globale. Se la preferenza privacy fosse
per-utente, sarebbe illeggibile prima che `checkAuth()` si risolva ⇒ sembrerebbe necessario
«mascherare di default» in attesa dell'identità, con un flash di **maschere** per chi ha la privacy
spenta.

**Perché è falsa.**

> **Un'analogia trasporta la soluzione e lascia indietro la premessa.** L'anti-FOUC esiste perché il
> contenuto **si dipinge comunque**: senza la classe si dipinge del colore sbagliato. Qui la
> premessa non vale — il ramo che produce i valori monetari non è ancora stato scelto, quindi quei
> valori **non sono nel DOM**.

**Prova** — `routes/(app)/+layout.svelte:191-237`, ogni ramo che renderizza contenuto è guardato da
`$isAuthenticated`:

```
{#if $i18nLoading}                                    → loader
{:else if $isAuthenticated && state === 'blocked'}    → OnboardingBootstrapBlock
{:else if $isAuthenticated && !appBootstrap.ready}    → loader
{:else if $isAuthenticated && !onboardingRouteReady}  → loader
{:else if $isAuthenticated && isWelcomeRoute}         → welcome shell
{:else if $isAuthenticated}                           → i dati vivono QUI
{:else}                                               → "Checking authentication..."
```

più la guardia reattiva a `:131`
(`if (browser && $isAuthInitialized && !$isAuthenticated) goto('/')`).

**Dominio della tesi, chiuso esplicitamente** — «non c'è flash» vale solo se quel layout è l'unico
posto in cui si dipingono valori:

| controllo | risultato a `1982c254b` |
|---|---|
| layout totali in `routes/` | **2** — root e `(app)` |
| pagine fuori dal gruppo `(app)` | **1** — `routes/+page.svelte` (login/landing) |
| file di `routes/` che usano un formattatore monetario | **3**, tutti sotto `(app)/` |
| root `+layout.svelte` | 49 righe, rende `<slot />` a `:47`, nessun valore |
| `routes/+page.svelte` | rende `OnboardingBootstrapBlock` a `:110`, nessun formattatore monetario |

⚠️ **Limite dichiarato**: la misura è sui file di `routes/`. Un componente raggiunto dal root layout
potrebbe rendere denaro senza passare di lì; il root layout non ne importa, ma la verifica
esaustiva per-componente è lavoro dell'inventario di §1, non di questa voce.

**Anche il cambio di account è coperto**, e dal medesimo meccanismo:
`appBootstrap.svelte.ts:146` registra `registerClientSessionReset('appBootstrap', …)`, e `reset()`
(`:118-123`) riporta `state = 'idle'` ⇒ `ready` torna falso ⇒ si rientra nel ramo loader. Nessun
paint con i dati dell'account precedente.

> **L'inversione da non perdere.** Lo stesso ordine che rende `getUserStorage` stantio in §5.2 — la
> transizione precede **sempre** la scrittura dello store auth — è ciò che rende il flash
> impossibile qui: quando `$isAuthenticated` diventa vero (`auth.ts:225`, derivato da `$auth.user`),
> `clientSession.userId` **è già assegnato**. **Una misura, due conclusioni opposte.** Chi legge le
> due voci separatamente penserà che una delle due sia sbagliata.

**Seconda metà della trappola — tooltip e portali**: ✅ **vera**, ed è il problema architetturale
della feature. Vedi §1.5 e §3.4.

---

## §6 — Domande aperte (decisioni di prodotto, non tecniche)

Ciascuna con due opzioni e l'argomento a favore di entrambe. **Nessuna è decisa in questo
documento.**

### Q1 — Il clipboard copia il valore reale o il segnaposto?

| opzione | argomento |
|---|---|
| **valore reale** | copiare è un'azione deliberata dell'utente, non una visualizzazione passiva; la privacy protegge dagli sguardi, non dall'utente stesso; un incolla con `••••` è inutilizzabile e l'utente disattiverebbe la privacy per copiare, cioè farebbe apparire *tutto* |
| **segnaposto** | coerenza letterale: se lo schermo è mascherato, nulla di reale esce; evita il caso «copio un IBAN/importo mentre proietto e lo incollo in una chat condivisa» |

Siti coinvolti: `aiExportClipboard.ts:169`, `utils/clipboard.ts:25`, `FilesTable.svelte:456`,
`FileGrid.svelte:107`. Stesso discorso per i **download/export** (`FilesTable:508,541`,
`backupDownload.ts:53`), dove l'argomento «azione deliberata» è ancora più forte.

### Q2 — `labelShrink` misura il testo reale o la maschera?

| opzione | argomento |
|---|---|
| **testo reale** | il layout resta identico fra privacy attiva e spenta, nessun salto al toggle |
| **maschera** | nessun valore reale transita per `document.body`, coerente con §2.1.5 |

Nota: il valore reale in `labelShrink` è **transitorio e non dipinto** — il clone serve solo a
misurare. Se si adotta la prima opzione va scritto **perché è considerata accettabile**, altrimenti
contraddice §2.1 alla lettera.

### Q3 — Le quantità sono sensibili? → 🔒 **CHIUSA: no, visibili** (D5)

| opzione | argomento | esito |
|---|---|---|
| **sì** (posizione del piano di sprint) | quantità × quotazione pubblica **ricostruisce il controvalore**: mascherare l'uno e mostrare l'altra annulla la protezione | ❌ **respinta** |
| **no** | in `UnifiedLotsTable.svelte:162-171` la quantità è la **chiave di lettura della riga** (`aperta / originale`, stato `PARTIALLY_CLOSED`): mascherarla rende la tabella illeggibile **anche a chi ha attivato la privacy di proposito** | ✅ **adottata dal developer** |

**Anche la terza via è stata scartata**, ed è bene che resti scritta: *mascherare la quantità solo
dove compare accanto a un controvalore*. Costo: una regola **non uniforme**, cioè una regola che
qualcuno applicherà male — e in questa feature applicarla male è silenzioso.

> La posizione del piano non era sbagliata nel merito: era sbagliata nel **modo di guasto**. È vero
> che la quantità permette di ricostruire il controvalore; è anche vero che mascherarla fa fallire
> la funzione **nello scenario che la giustifica**. Fra una protezione aggirabile da chi ha tempo e
> una funzione inutilizzabile da chi l'ha accesa, si accetta la prima — e la si dichiara in §8.

### Q4 — Campi di input con importi → 🔒 **CHIUSA: fuori scope** (D7)

Un `<input value={…}>` contiene il valore nell'attributo, quindi §2.1 lo vieterebbe. **Esclusione
motivata, non omissione**: un campo di modifica serve a modificare; mascherarlo lo rende
inutilizzabile, che è lo **stesso errore di Q3 un livello più in basso**.

Confermato che il caso è reale e non teorico: `transactions/events/EventCreateMiniModal.svelte:73`
scrive `eventAmount` con `toFixed(2)` — §1.8 #6.

> *Il silenzio su una strada scartata è indistinguibile dal silenzio su una strada mai considerata.*
> Per questo l'esclusione sta qui e in §8, non nell'assenza di una riga.

### Q5 — Il toggle è raggiungibile da tastiera e da mobile?

Non è una domanda di prodotto marginale: se serve a coprire lo schermo *mentre qualcuno si avvicina*,
la latenza d'uso è il requisito. Un'opzione sepolta in Impostazioni non serve il caso d'uso
dichiarato; una scorciatoia globale sì. → richiede il **gate UX**, fuori dallo scope di questa
analisi.

---

## §7 — Stima raffinata e ordine di implementazione

### 7.1 — Perché XL, e dove sta davvero il costo

Confermata la taglia **XL** del piano di sprint, ma per una ragione diversa da «ci sono molte
pagine»:

| voce | dimensione misurata | costo |
|---|---|---|
| le primitive | 3 livelli, ~2 file nuovi + 1 esteso | **S** — il codice è poco |
| innesto nei formattatori | 2 funzioni | **S** |
| **classificazione dei siti** | **61 chiamate che rendono importi**, 25 file | **L** — un giudizio per sito, non automatizzabile |
| grafici | 14 componenti, `formatter` da classificare + 4 con nodo nel body | **M** |
| classe fuori-DOM | 4 clipboard + 3 export + 1 cross-doc + 1 clone di misura | **M**, ma **bloccata da Q1/Q2** |
| 🔴 **falsi negativi §1.8** | **6 siti**, di cui **un quinto formattatore** fuori da `currencyFormat.ts` | **S** di codice, ma **cambia la regola**: vedi sotto |
| gate anti-regressione §1.8 | 1 test di sorgente, insieme registrato | **S** — *proposta, non autorizzata* |
| quantità | 5 file, 24 siti | **✅ nessuno** — D5: restano visibili |
| input con importi | — | **✅ nessuno** — D7: fuori scope |
| test | contratto §2.3, con controllo positivo obbligatorio | **M** |

> **Il costo dominante è la classificazione, non il rendering.** Le primitive si scrivono in poche
> ore; decidere 61 siti uno per uno è il lavoro. E un giudizio sbagliato costa in due direzioni
> opposte: in un verso si perde la protezione **in silenzio**, nell'altro si rende illeggibile un
> dato pubblico **in modo visibile**. §3.2 sceglie il default che rende visibile l'errore.

**D5 e D7 hanno tolto lavoro, §1.8 ne ha aggiunto di un tipo diverso.** Le quantità e gli input
escono dal perimetro — due voci a zero. Ma §1.8 non aggiunge sei siti da sistemare: aggiunge il
fatto che **l'insieme dei formattatori non è noto per enumerazione**. La taglia resta **XL**, e la
ragione si sposta: non «ci sono molte pagine», ma **«il canale portante non è l'unico canale, e il
secondo non ha un nome che lo renda cercabile»**.

### 7.2 — Ordine proposto

1. **Store + chiave** (§4) — nessuna dipendenza, nessuna superficie condivisa.
2. **`maskable` nei formattatori** (§3.2) con default sicuro — copre subito **61 siti** senza
   ancora classificarli, perché il default è «mascherato». Da qui in poi il sistema
   **sovra-maschera**: stato sicuro e visibile.
3. 🔴 **Falsi negativi §1.8** — i **4 siti che rendono denaro con una valuta** (#1–#4). `#5`
   (`MeasurePanel`, senza valuta) è un sito di giudizio e segue la classificazione del passo 4;
   `#6` è un input, **fuori scope per D7**. **Va prima della
   classificazione**, non dopo: finché restano fuori, il sistema sovra-maschera dove passa dal
   canale e **lascia in chiaro dove non ci passa** — cioè la proprietà di sicurezza del passo 2 è
   falsa, e lo è in modo non visibile.
4. **Classificazione dei siti pubblici** (`sensitivity: 'public'`) — è il lavoro L, e procede per
   viste, riducendo la sovra-mascheratura a partire da quelle più usate. La **checklist per-sito**
   include il rischio di composizione di D6: una percentuale accanto a un importo visibile.
5. **`SensitiveValue`** (§3.3) per i siti fuori formattatore.
6. **Grafici** (§3.4) — `formatter` e invalidazione `dispatchAction`.
7. **Classe fuori-DOM** — **dopo Q1/Q2**.
8. **Gate anti-regressione** (§1.8) — **solo se il developer lo autorizza**. Va **dopo** il passo 3,
   perché il gate registra un insieme e quell'insieme deve essere già corretto.
9. **Gate UX** — approvazione developer separata, include Q5.
10. **Voci aperte I e D** (§1.7) — **dopo** il freeze dei rispettivi workstream, con inventario
    rifatto sulla revisione in cui quelle superfici esistono.

**Proprietà di questo ordine**: dopo i passi 2 **e 3** il sistema è conforme al contratto, e i passi
successivi riducono un eccesso di protezione invece di colmare un difetto. Un rilascio parziale è
sicuro in ogni punto **a partire dal 3** — non dal 2, ed è la correzione che §1.8 impone a questa
sezione.

### 7.3 — Superficie condivisa con gli altri workstream

Dopo D1, **U2 non tocca il backend**: nessuno schema, nessuna migrazione, nessun `api sync`, nessun
client rigenerato.

| workstream | sovrapposizione |
|---|---|
| **D** (SP14, Tool/PAC) | ❌ nessuna a livello backend; da verificare sui file frontend delle tabelle allocatore al suo freeze |
| **I** (SP07) | ❌ nessuna a livello backend; voci aperte §1.7 sulle nuove viste P&L |
| coordinator | i18n delle etichette del toggle (chiavi nuove), da richiedere al momento del piano |

---

## §8 — Confine dichiarato

La feature protegge **ciò che si vede sullo schermo**. Non protegge, e non deve promettere di
proteggere:

- **DevTools** e il sorgente della pagina;
- le **risposte API**, che contengono i valori reali indipendentemente dallo stato della privacy;
- gli **allegati** e i report broker scaricati;
- i **log** applicativi e di console;
- gli **export** grezzi e i backup (salvo decisione contraria in **Q1**);
- la **cronologia** del browser e le estensioni installate.

> Il confine va **dichiarato**, non aggirato. Una feature di privacy che lascia credere di proteggere
> da un attaccante con accesso al dispositivo è **peggio** di nessuna feature, perché cambia il
> comportamento di chi si fida.

L'interfaccia deve dire questo confine, e il piano d'implementazione deve indicare **dove** lo dice.

---

## §9 — Cross-link

- Fonte del task: [`09_feedbackJobs/06_piano_sprint.md` §5 U2](../09_feedbackJobs/06_piano_sprint.md)
- Backlog strutturale: [`09_feedbackJobs/00_backlog_strutturale_P4.md`](../09_feedbackJobs/00_backlog_strutturale_P4.md)
- UX dashboard (origine di U2): [`09_feedbackJobs/01_ux_dashboard.md`](../09_feedbackJobs/01_ux_dashboard.md)
- Workstream J, lavoro precedente (SP11/U8): [`21_onboarding/`](../21_onboarding/)
- Piano d'implementazione: **da creare**, `plan-phase00PrivacyGlobalRound1-….prompt.md` in questa
  cartella — dovrà cross-linkare questo documento.

---

## Appendice A — Tutte le misure, con la loro revisione

| misura | valore | revisione | comando |
|---|---|---|---|
| `formatCurrencyAmountPlain` | 19 file / **47 siti** | `1982c254b` | `grep -rn` su `frontend/src`, esclusi test e riga di definizione; siti = righe − import |
| `formatCurrencyAmountHtml` | 7 file / **14 siti** | `1982c254b` | idem |
| `formatCurrencyCodeHtml` | 4 file / **12 siti** | `1982c254b` | idem |
| `formatCurrencyForTooltip` | 2 file / **4 siti** | `1982c254b` | idem |
| file che rendono **importi** (`…Plain` ∪ `…Html`) | **25 file / 61 siti** | `1982c254b` | idem |
| unione dei 4 simboli | **27 file** | `1982c254b` | idem |
| ⚠️ *misura precedente, ritirata* | 17/61 · 7/21 · 3/12 · 1/3 | `1982c254b` | `grep -r` su **`*.svelte`** soltanto — perimetro che **escludeva i `.ts`**, cioè i `formatter` ECharts. Non riproducibile: vedi §1.1(b) |
| `TweenedValue` / `CompactCashCell` | 3 / 3 file | `1982c254b` | idem |
| `HtmlCell` / `{@html}` | 6 / 21 file | `1982c254b` | idem |
| `formatPercent` / `formatQuantity` / `formatDate` | 5 / 5 / 13 file — **37 / 24 / 54 siti** | `1982c254b` | idem |
| 🔴 **quinto formattatore di importi** | `risk/riskAnalysisHelpers.ts:130`, 1 consumatore | `1982c254b` | `Intl.NumberFormat({style:'currency'})`, **fuori** da `currencyFormat.ts` |
| falsi negativi §1.8 (denaro fuori dal canale) | **6 siti**, di cui 1 input e 1 di giudizio | `1982c254b` | `style:'currency'` ∪ template literal con valuta ∪ formattatori locali non deleganti |
| formattatori locali di valuta che **delegano** | 8 su 13 | `1982c254b` | presenza di `formatCurrencyAmountPlain\|Html` nel file |
| controprova negativa §1.8 | `snapshotDataRenderer.ts:226` | `1982c254b` | usa `Intl…style:'currency'` ma **legge solo** `maximumFractionDigits` |
| `formatPercent` ha un parametro semantico? | **no** — `{scale, signed, digits}` | `1982c254b` | firma a `formatPercent.ts:35`; proxy `signed` smentito da `FxTable:127` |
| `document.body` (esclusi test ed E2E) | **41** | `1982c254b` | J |
| `document.body` (esclusi test) | **41** | `c75cf9150` | coordinator |
| componenti ECharts in produzione | **14** | `1982c254b` | esclusi `__tests__/harness/` |
| grafici con tooltip nel body | **4** | `1982c254b` | `appendTo` / `appendToBody` |
| grafici che l'hanno rimosso | **3** | `1982c254b` | bugfix documentati nel codice |
| `dispatchAction` | 64 siti | `1982c254b` | invalidazione tooltip |
| resetter di sessione in produzione | **22** | `1982c254b` | `registerClientSessionReset(`, esclusi test e definizione |
| consumatori di `getUserStorage` | 9 file | `1982c254b` | — |
| chiavi `localStorage` non per-utente | 3 | `1982c254b` | `librefolio-theme`, `librefolio-locale`, `global_settings` |
| layout in `routes/` | 2 | `1982c254b` | root + `(app)` |
| pagine fuori dal gruppo `(app)` | 1 | `1982c254b` | `routes/+page.svelte` |

> **Nota sulle misure con perimetro.** Ogni riga di questa tabella vale **nel perimetro del comando
> che l'ha prodotta**. Durante questa analisi una misura corretta su un perimetro sbagliato —
> `lib/charts/`, che **non contiene alcun grafico** — ha prodotto la conclusione falsa «ECharts non
> porta i tooltip fuori dal contenitore», smentita in §1.5 da quattro configurazioni attive.
>
> **Un perimetro stretto si allarga; un perimetro sbagliato si rifà.** E un limite dichiarato sul
> perimetro sbagliato è più ingannevole di uno taciuto, perché dice al lettore *«so dove non ho
> guardato»* e lo convince che chi scrive sappia dove **ha** guardato.

### Il difetto ricorrente di questa analisi, nominato

Lo stesso errore è comparso **cinque volte**, sempre nella stessa forma: un contenitore dal nome
giusto che non contiene gli oggetti che il nome promette.

| # | contenitore | promessa del nome | contenuto reale |
|---|---|---|---|
| 1 | `lib/charts/` | i grafici | **nessun grafico** — stanno in `components/` |
| 2 | `utils/shareNavigation` | un util | vive in `components/support/` |
| 3 | `22_privacy/` | cartella libera | **occupata**, regola a `06_piano_sprint.md:1077` |
| 4 | `grep --include=*.svelte` | le superfici | **esclude i `.ts`**, dove sta la prova (§1.1b) |
| 5 | `currencyFormat.ts` | i formattatori di valuta | **non tutti** — il quinto è in `risk/` (§1.8) |

> **Il nome di un contenitore è un'ipotesi sul contenuto, non una misura di esso.** In questo
> repository l'ipotesi è risultata falsa una volta su due, e ogni volta ha prodotto un numero
> *plausibile* — mai uno assurdo, che sarebbe stato contestato.
>
> Da cui la regola operativa che §1.8 traduce in proposta di gate: **àncorare una verifica a ciò che
> un oggetto fa (l'API che chiama) e non a dove vive o come si chiama.** La prima proprietà è
> osservabile, la seconda è una convenzione che il codice può violare in silenzio.
