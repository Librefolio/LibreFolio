# Reperti del round di analisi statica — 22/09/2026

**Baseline**: `e4a46e9e0`. Sei worktree + main, tutti puliti, tutti fermi.
**Vincolo del round**: nessuna modifica di codice, nemmeno ai piani.

> **Cos'è questo documento.** Il round del 22/09 è stato un'analisi **puramente statica**:
> sette workstream hanno riletto il codice integrato senza eseguirlo e senza toccarlo. Questo
> file raccoglie ciò che ne è uscito — difetti, debito, e soprattutto i **reperti di metodo**
> (§3), cioè i modi in cui una misura può essere corretta e dire il falso.
>
> **Come si legge insieme a [08](08_review_visiva_20260922.md).** Il foglio 08 è la review
> **d'uso** che il developer ha fatto lo stesso giorno sul server di produzione. I due si
> controllano a vicenda: 08 ha **confermato** alcune voci di qui, e ne ha **smentita una**
> (§1.2). Le rettifiche sono registrate in **§9**, e le voci corrette portano un richiamo in
> testa — **senza cancellare il testo originale**, per la ragione scritta in §2.7.
>
> ⚠️ **Nato come scratch di sessione**, materializzato nel repo su richiesta del developer il
> 22/09 alle 16:28. Fino a quel momento questi reperti vivevano solo nei messaggi
> cross-session: erano a un colpo di compattazione dallo sparire.

---

## 1. Difetti di prodotto verificati (non ancora riparati)

### 1.1 🔴 La card del tool PAC mostra la descrizione del prototipo cancellato

- i18n `tools.pacAllocator.description` = testo del **P1**, rimosso in `b82e59ffa`
- backend `pac_allocator.py:98` = testo del **v2**, vivo
- `frontend/src/lib/features/tools/presentation.ts` → `metadataText()` ritorna il
  fallback backend **solo se la chiave i18n manca** → **l'i18n vince**
- × 4 lingue
- Nessun gate può vederlo: una chiave referenziata da `description_i18n_key` è
  **viva per definizione, qualunque cosa dica**

### 1.2 ~~🔴 Toggle «Abs / %» morto sul tab correlazione~~ → ❌ **SMENTITO dalla review (§9.1)**

> 🔴 **Non riparare questa voce.** La review d'uso del 22/09 ha dimostrato che il toggle
> **funziona**: premuto nel tab correlazione e poi osservato tornando su Asset, **l'effetto
> è vivo**. L'analisi qui sotto è tecnicamente esatta su ciò che ha misurato, e sbagliata
> sulla conclusione. Il perché è in **§9.1** — è il reperto di metodo più forte del round.
>
> Resta vera una sola cosa, ed è una nota d'uso: il toggle **compare solo in modalità
> griglia**, dettaglio che non era documentato da nessuna parte.

*Testo originale, conservato per la ragione in §2.7:*

`frontend/src/routes/(app)/assets/+page.svelte`

```
:1439  {#snippet actions(…)}  …  :1496 {/snippet}   ← la barra, FUORI da ogni guardia
:1450 / :1459   globalViewMode = 'absolute' / 'percentage'   ← le due scritture
:1500  {#if activeTab === 'correlation'}
:1544  {:else if viewMode === 'grid'}     ← RAMO MUTUAMENTE ESCLUSIVO
:1575         {globalViewMode}             ← l'UNICA lettura, qui dentro
```

`:1500` e `:1544` sono rami della stessa catena `if/else-if`. Con il tab correlazione
attivo il solo consumatore **non è montato**: zero lettori, non «un lettore che ignora».
Stesso difetto per `ColumnVisibilityToggle` (`:1441`) e per Settings, che apre le
impostazioni grafico senza grafici montati.

> Su una pagina la cui tesi è «qui è sempre percentuale», un bottone `Abs` cliccabile
> non è inerte: è un'affermazione contraria alla regola della pagina. (F)

### 1.3 🔴 Dual View asimmetrica

`AssetTable.svelte` 2 chiamate mascherate · `AssetCard.svelte` **0**.
Stessa pagina, stesso dato, un `localStorage` decide se la privacy esiste.
Nessun test lo dichiara.

### 1.4 🔴 Tre popolazioni senza masking

| superficie | misura |
|---|---|
| `features/ai-export/` | 0 file su 29 nel canale mascherato |
| `features/tools/` | 0 file su 15 |
| FX (`displayFxRate`) | 21 siti su 7 file |

`snapshotDataRenderer.ts` fa passare ogni numero per `scalar()` → `formatPromptNumber()`:
l'anteprima del prompt è **l'intero portafoglio in chiaro**.

### 1.5 🔴 I 9 render di denaro scoperti — composizione, non totale

```
4 patrimonio · 3 quotazioni · 2 fallback condizionali
```

- patrimonio: `CompactCashCell:76,101` · `AssetEventPicker:451` · `TransactionBulkModal:1871`
- quotazioni: `AssetCard:223` · `AssetPriceSummary:96` · `providerProbe:115`
- fallback: `WacPreviewSection:565,586`

⚠️ Il totale `9` è passato da `9` a `9` attraverso **due correzioni opposte**
(−2 guardia di blur, +2 fallback). Vedi §3.3.

### 1.6 ~~🔴 Gate che passa misurando nulla (Asset Global)~~ → ⚠️ **RIDIMENSIONATO (§9.2)**

> ⚠️ **L'affermazione qui sotto è falsa per due terzi.** La maschera avvolge **solo il
> numero**: simbolo, bandiera e codice valuta sono concatenati **dopo**
> (`currencyFormat.ts:41-47`), quindi sotto privacy l'output è `••• € 🇪🇺 EUR`, non `•••`.
> Delle tre asserzioni, **una sola** è cieca:
>
> | # | asserzione | sotto privacy |
> |---|---|---|
> | 1 | `:1356` `.not.toMatch(MONEY_PATTERN)` — cerca il **valore** | 🔴 cieca |
> | 2 | `:1357` `.not.toContain('€')` — cerca il **canale** | ✅ regge |
> | 3 | `:1359` `.currency-symbol` count 0 — cerca il **canale** | ✅ regge |
>
> 🔑 **La maschera nasconde il valore, non il canale.** Un gate che cerca il canale
> sopravvive alla privacy; uno che cerca il valore no. E l'autore **lo sapeva già**: il
> commento a `risk-lab.spec.ts:55-66` anticipa il problema, e le tre barriere di presenza a
> `:1312-1317` sono la sua risposta.
>
> **Resta vero e da riparare**: l'asserzione 1. **Resta falso**: che il gate «misuri nulla».

*Testo originale, conservato per la ragione in §2.7:*

Il controllo «niente euro» asserisce assenza di `12.345,67`, `€`, `.currency-symbol`.
Con privacy attiva `maskable` restituisce `'•••'` (`maskable.ts:24`) — **nessuno dei tre**.
Condizione di successo e condizione di fallimento producono **lo stesso output osservabile**.
Oggi salvo solo per **D3** (`privacyStore.svelte.ts:59`, «chiave assente = off») e perché
nessun test di `risk-lab` nomina la privacy.
Riparazione: due righe che pinnano il flag a `off`. **Owner: Risk/A.**

### 1.7 🔴 4 chiavi i18n vive dichiarate morte

`risk.betaBanner.{title,description,simulation.title,simulation.description}`

```
RiskBetaBanner.svelte:31  keyPrefix = $derived(scope === 'simulation' ? … : …)
                     :36/:37  $t(`${keyPrefix}.title`)
```

**Causa corretta**: prefisso `$derived` con ternario (due prefissi possibili, irriducibili),
NON «il template comincia con `${`».
**Controllo che falsifica la causa larga**: `SimulationProvenance.svelte:22` usa
`const NS = 'risk.levels.l4.provenance'`, ha **10 siti** con la stessa sintassi e
**31 chiavi, 0 condannate**.

⚠️ Nelle **422** chiavi morte ce ne sono almeno **4 false**: non cancellare in blocco.

---

## 2. Debito strutturale

### 2.1 `front-portfolio risk-lab` mai eseguito

Passato da **bloccato** (due nodi `risk-correlation-heatmap` ambigui) a **eseguibile**
quando A ha smontato il legacy. Cresciuto **817 → 2057 righe**, con le asserzioni di
**due mandati**. **Nessuno l'ha mai eseguito**: richiede una lane, e il round la vietava.

### 2.2 P4-11 — terza rettifica, il nono canale

`GrowthChart.svelte`
```
:1815  yAxisFormatter   (ternario viewMode === 'pct' GIÀ presente)
:1834  fmtCurrency      (1 def + 8 consumi = gli 8 tooltip)
:2051  axisLabel.formatter = yAxisFormatter     ← L'ASSE Y, nono canale
```
Mascherare solo `:1834` lascia in chiaro il canale **leggibile senza mouse**.
Rimedio corretto = **due punti**, e il secondo è più piccolo (basta il ramo `else`).

### 2.3 Due riparazioni in coda, owner Risk/A

1. pin del flag privacy sul cancello euro (§1.6)
2. `risk.assetSet.panelTitle` orfano (4 righe)

### 2.4 Guardiano — il ritiro era troppo largo

| difetto | riparazione |
|---|---|
| 46 rossi: artefatto **generato** più vecchio della fixture | `api sync` — riga di procedura |
| deriva fra catalogo **finto scritto a mano** e registro vero | **guardiano** — debito vero |

Discrimine: **se esiste qualcosa che rigenera**. Sul secondo no, quindi `api sync`
**non fallisce: passa senza toccarla**. Costo misurato: 4 occorrenze in 2 giorni,
la quarta **viva**. Pezzo riusabile: `risk-lab.spec.ts` + marchio `algorithm_version`
che impedisce al guardiano di diventare vacuo se qualcuno reinstalla i mock in un
`beforeEach`.

### 2.5 🔴 Un default che trasforma un'omissione in un consenso

`frontend/src/routes/(app)/assets/[id]/+page.svelte:2174`

```js
async function handlePageSyncComplete({accepted}: {accepted: boolean} = {accepted: true}) {
    if (accepted && primaryMode === 'calendar-return') { … }
```

Catena completa (I): `PageSyncModal:27,40` emette `{accepted}` → `RiskAnalysisPanel`
(`:50` firma, `:524-526` propagazione) → `AssetRiskScenariosView:21` → `+page:2174`.

Oggi innocuo: la sola chiamata porta sempre il detail, perché `handleSynced` invoca
`controller.handleSynced()` **senza** hook e chiama il genitore **una volta sola**
(commento a `:519-522`, che documenta il doppio invio già evitato una volta).

🔴 **Ma qualunque futura chiamata senza argomento viene letta come accettazione**, in
silenzio, senza errore di tipo. Il commento protegge il contratto; **niente protegge il
default se il contratto cade.**

Rimedio proposto: **non** togliere il default, ma renderlo `{accepted: false}` —
un'omissione dovrebbe valere come annullamento, non come conferma. **Owner naturale: I**,
unica che conosce la catena.

✅ **Costo dell'inversione: zero oggi** (misurato da I `12:51`, riverificato dal
coordinator). Due call site, **entrambi come prop che passano il detail**:
```
assets/[id]/+page.svelte:3533   onsynced={handlePageSyncComplete}
                        :3558   onsynced={handlePageSyncComplete}
invocazioni nude                NESSUNA
```
> Nessun percorso attuale esercita il default. È una decisione **puramente su cosa debba
> succedere domani** — il che la rende più facile da prendere, non più difficile: non c'è
> un comportamento da preservare, solo **una polarità da scegliere**. (I)

⚠️ **Omonimia — trappola per chi cercherà dopo.** Esiste una **seconda**
`handlePageSyncComplete` in `fx/[pair]/+page.svelte:1030`, **senza parametri**, funzione
diversa. E la sonda naturale peggiora la cosa:
```
grep -rn "handlePageSyncComplete()"  ->  1 risultato:
     fx/[pair]/+page.svelte:1030:    async function handlePageSyncComplete() {
```
**L'unico risultato è una *definizione* di un'*altra* funzione in un'*altra* pagina**, e
si presenta come «ecco il chiamante senza argomento che temevi». La sonda per *«esiste un
chiamante nudo?»* risponde **sì** con un artefatto che non è né un chiamante né quella
funzione. Stessa famiglia del `buildBucketInfos` omonimo — segnalata **prima** che
costasse, non dopo.

📌 Direzione dell'errore: **verso il rosso** → si autodenuncia (cfr. §3.6). È il motivo
per cui questa la stiamo contando e altre no.

📌 Forma prospettica dei quattro registri verdi e falsi: non un registro che sopravvive al
codice, ma **un default che sopravviverà al contratto che lo rende sicuro**.

### 2.6 Deriva di commenti

`L4Replay:47` e `L4Shock:46` citano `formatScopedCurrencyAmount:163`; la funzione è a
**:177** (spostata dalle `+18 −3` di J). Rimedio strutturale: **citare il simbolo, non
la riga**.

### 2.7 Debito di storia — non riscrivere

Il commit `0a1d98eaf` dice «workstream D renamed those files out of existence».
D li aveva **cancellati** (`b82e59ffa`). Catena del verbo:
`drop` (D) → `masked` (J) → `renamed` (coordinator, nel commit) → `masked` + **agente
invertito** (coordinator, nel messaggio). È un fatto datato: si registra, non si corregge.

---

## 3. Reperti di metodo — la parte che vale più dei difetti

### 3.1 L'artefatto derivato scaduto scambiato per regressione

`frontend/.gitignore:12-13` → `generated.ts` e `openapi.json` **ignorati**: il client
TypeScript **non partecipa al merge**. Dopo un salto di baseline il codice è nuovo e
l'artefatto è vecchio → `svelte-check` dava **72 errors in 18 files** invece di **3 in 4**.

> L'errore ha la forma esatta di una regressione: nomina una proprietà che davvero non
> esiste, su un tipo che davvero esiste. Chi verifica apre il tipo, non trova il campo, e
> **conferma**. La verifica corretta produce la conclusione sbagliata.

**L'età è una proprietà del checkout, non del repo** (I): stesso HEAD, **liste di errori
disgiunte**. I tre alberi Risk avevano client del 22, del 21 e del 18 settembre.

✅ **Prova migliore del `mtime`** (F): confrontare l'**hash** di `generated.ts` prima e
dopo il sync — byte-identico mentre `openapi.json` cambia. *Identità di contenuto invece
di una data.* Una data si legge male su un checkout copiato; un hash no.

✅ `api sync` **non apre porte**: `scripts/list_api_endpoints.py:69` → `app.openapi()`
in-process. La skill `devpy-server` che lo descrive come «starts a temporary server
instance» è **obsoleta**.

🔑 **Il verso conta più della causa** (Risk/A): la stessa causa **gonfia** gli errori di
`svelte-check` e **spegne** 46 rossi E2E. La formulazione che sopravvive a entrambe non
nomina il meccanismo:

> **«Il colore non è una proprietà della revisione: è una proprietà dell'albero di chi guarda.»**

### 3.2 La sonda che sbaglia verso il verde

A ha confermato l'orfano `risk.assetSet.panelTitle` **al terzo tentativo**; le prime due
sonde dicevano «zero».

```python
re.search(r'`' + re.escape('risk.assetSet') + r'\.', src)
# combacia su  $t(`risk.assetSet.bulk.${key}`)
# -> OGNI figlia finisce nel secchio "raggiunta dinamicamente", orfano compreso
```

> **Una sonda che sbaglia verso il verde non si vede: si vede solo cercando ciò che si è
> già deciso di non stampare.** (A)

A aveva **il difetto e la prova che non c'era** — una misura sincera a sostegno di
«segnalazione infondata». L'ha trovato solo perché **ha creduto alla contraddizione
invece che alla propria sonda**. *Quella è la mossa; la regex no.*

### 3.3 Il totale che non si muove

```
9  − 2 (guardia di blur)  + 2 (:565, :586)  =  9
```

Due correzioni **indipendenti, in direzioni opposte**, totale invariato. Senza le classi
tracciate sarebbe sembrato «niente è cambiato», mentre sono cambiate 2 voci su 9 e si è
aperta la classe peggiore.

> Peggiore della spiegazione che riproduce il numero: lì c'è **un'affermazione** da
> sospettare, qui c'è **solo un numero che non si muove**. Un totale stabile non afferma
> niente — è la forma in cui una misura **smette di poter essere contraddetta**.

### 3.4 La cecità causata dalla correttezza

```js
{qtx.unit_cost && qtx.currency ? formatCurrencyAmountPlain(…) : parseFloat(…).toFixed(2)}
//                               ^^^ fa scattare SAFE_CALL → la riga INTERA viene saltata
//                                                            ^^^ esce con lei
```

`moneyRenderSites.test.ts:81` ha `formatCurrencyAmountPlain` come **prima alternativa
esplicita**; `:136` fa `if (SAFE_CALL.test(line)) return;` — **granularità di riga**.

> **La cecità del gate è causata dalla correttezza che vede per prima. Più la riga sembra
> giusta, meno il gate la guarda.** (J)

Stessa regola, **entrambe le direzioni**: 3 falsi positivi nella rete larga, 2 falsi
negativi qui.

✅ **Criterio eseguibile che sostituisce il campionamento** (J):
> Una riga che contiene **sia** una chiamata mascherata **sia** una formattazione grezza è,
> per costruzione, un candidato a ramo dimenticato — ed è **esattamente l'insieme che il
> gate non guarda**.

### 3.5 Il ragionamento corretto sul pezzo che non decide

`/formatCurrencyAmount\b/.test("formatCurrencyAmountPlain(")` = **`false`** — vero, fra `t`
e `P` non c'è word boundary. Ma `SAFE_CALL` ha `formatCurrencyAmountPlain` come alternativa
**esplicita**, quindi la deduzione è vera **e irrilevante**.

> Le altre forme partono da una misura sbagliata o da un soggetto sbagliato. Questa parte
> da una deduzione **vera**, che resta vera anche dopo. Non c'è niente da correggere nel
> ragionamento: c'è da **sostituirlo con un'esecuzione**.

> Le altre dodici forme lasciano un residuo: un numero che non torna, un albero diverso,
> una riga che non c'è. **Questa no.** La `\b` non matcha davvero `…Plain`, prima e dopo.
> Un ragionamento corretto su un frammento **non è distinguibile, dall'interno**, da un
> ragionamento corretto sul tutto. L'unica differenza osservabile è **quanto hai letto** —
> e non è un fatto sul codice, è un fatto su di te, che nessuna verifica sul codice può
> restituirti. (J)

### 3.6 Il campione selezionato dal fenomeno

Quattro misure cadute oggi, **tutte** sbagliavano verso la risposta attesa:

| chi | misura | come sbagliava |
|---|---|---|
| coordinator | `awk` sull'audit i18n | due sezioni contate come una (`463 = 422 + 41`) |
| Risk | `−41` sulle chiavi morte | applicato a **entrambi** gli estremi → **il delta restava giusto** |
| Risk | `pac_allocator` in `generated.ts` | interrogava un file dove quel simbolo non vive (sta in `generated-tools.ts` 3, `tool-contract-map.generated.ts` 2) |
| A | sonda sugli orfani i18n | il backtick assorbiva l'orfano nel secchio sicuro |

> Le misure sbagliate che tendono al **rosso si autodenunciano** — qualcuno va a guardare.
> Quelle che tendono al **verde chiudono la pratica**. Non sbagliamo più spesso verso
> l'atteso: **solo quelle sopravvivono abbastanza da essere contate.** Quindi `4` è un
> minimo, e il campione è selezionato dal fenomeno.

### 3.7 Un errore sistematico si cancella in una sottrazione

```
ieri   dead misurate 237  →  riportate 196   (237 − 41)
oggi   dead misurate 422  →  riportate 381   (422 − 41)
delta  +185               →  +185            ✅ CORRETTO
```

I due livelli erano sbagliati e la loro **differenza era giusta**. Chi avesse controllato
il delta avrebbe trovato tutto in ordine. **Preso confrontando un livello, non una
variazione.**

### 3.8 La catena di riscrittura del verbo

`drop → masked → renamed → masked` + agente invertito.

> **Una correzione può aumentare la precisione apparente e lasciare intatto l'errore.**
> Al terzo passo *stavo correggendo*, e ho scelto un verbo altrettanto falso ma più
> circostanziato — quindi più credibile. **Una correzione aumenta la credibilità di ciò
> che non corregge.** (D)

### 3.9 `FROZEN` è due affermazioni, non una

I aveva lasciato acceso `dev.py server --test --port 6157 --data-dir /tmp/librefolio-r2-i-charts`
per 2h15, con `watchfiles` reload **sul proprio albero congelato**.

> Non l'ho dimenticato: l'ho **riclassificato**. Da «server che ho avviato» a «lane che non
> sto usando» — e la seconda descrizione è vera e **non copre la prima**. (I)

**Un processo che hai avviato non smette di essere tuo quando smetti di usarlo.**
`FROZEN` sull'albero e `FROZEN` sui processi sono due affermazioni diverse.

### 3.10 Registri che sopravvivono al codice che descrivono

Quattro nello stesso round, **tutti verdi, tutti falsi**:
1. due migrazioni `003_*` con lo stesso genitore
2. il registro privacy che nominava file cancellati
3. la chiave i18n che descrive un prototipo rimosso (§1.1)
4. il cancello che passa perché ciò che doveva impedire è stato **nascosto da un
   meccanismo che non conosce** (§1.6)

### 3.11 Due regole che si somigliano, tenute da cose diverse

> Il cancello di J protegge il **canale**; quello di Risk protegge lo **scope**. Un euro
> reso con `formatCurrencyAmount` su `asset_set` sarebbe **mascherato correttamente** e
> **invisibile al cancello di J**, e violerebbe comunque la regola del rischio.

E le due nature di sicurezza (F):
- `L4Replay:147,213` → **chiama** il formattatore, soppresso da `showMoney` = *denaro che
  esiste e tace*
- `assetSetLevels.ts` → **nessun parametro valuta** = *denaro che non esiste*

> Il primo è sicuro finché regge una bandiera; **il secondo non ha una bandiera da far cadere.**

### 3.12 🔑 Indipendenza e non-duplicazione sono in conflitto diretto

La «rete larga» che J ha usato per triare i 19 candidati aveva **copiato verbatim dal gate**
la costante `SAFE_CALL` e la riga `if (SAFE_CALL.test(line)) return;`.

Non per pigrizia: **di proposito**. Una rete larga che riportasse anche i siti già coperti
dal canale mascherato avrebbe prodotto decine di falsi allarmi su righe corrette.

> **Era una regola di de-duplicazione.** Serviva a non ripetere ciò che il primo strumento
> già gestiva — e per farlo ha dovuto adottare **la definizione di «già gestito» del primo
> strumento**. Non ha ereditato un bug: ha ereditato un **giudizio**, insieme al confine
> sbagliato su cui poggiava.

**Forma generale (J):**
> Un secondo strumento costruito per **escludere ciò che il primo copre** non può essere il
> controllo del primo, perché **ha accettato la sua mappa**. L'unico modo di avere il
> controllo è accettare il rumore — e il rumore è esattamente ciò che si stava cercando di
> evitare.

Quindi «il verificatore aveva il difetto che cercava» va corretto in: **non l'aveva per
caso, l'aveva per progetto** — e ogni verificatore costruito così lo condividerà sempre.

⚠️ Qualità della prova dichiarata da J: `/tmp/lfj/wide.mjs` è stata **rimossa** a fine
analisi, quindi questa è la sua testimonianza sul comando eseguito, non una rilettura.
Ricostruibile in un minuto se serve.

### 3.13 Una misura su una coppia riportata come proprietà di uno

«Zero conflitti attesi» (Risk, pre-merge) **non è una previsione che scade**: è una
**relazione fra due alberi** presentata come attributo di uno solo.

> Non serve che nessuno sbagli e non serve che passi tempo: basta che si muova **l'altro
> termine**, che chi misura non controlla e spesso non guarda. (I)

Stessa forma del server acceso di I (§3.9): *lo stato che descrivi non è quello che
controlli*. Lì il mondo era un processo proprio; qui è il target di qualcun altro.

### 3.14 Un'istruzione porta uno stato implicito che scade

I ha **rifiutato** un comando di commit del coordinator perché `22b82e3fb` era già
antenato di `e4a46e9e0` (entrato via `7fd660846`).

> **Il messaggio non è sbagliato: è stantio.** Descrive correttamente un momento che è
> passato **mentre era in coda**. Il ritardo era del **canale**, non della rilettura: il
> messaggio era vero quando è partito. (I)

Il costo dell'esecuzione sarebbe stato zero (`nothing to commit`). **Il danno non è
l'effetto: è la convinzione di aver fatto qualcosa.**

Difesa: **misurare lo stato che l'istruzione presuppone, prima di eseguirla.**
Contromisura adottata: mandare sempre **lo stato atteso accanto al comando**.

🧹 Conseguenza operativa: rimossi **8** file `/tmp/libreFolio_commit_*.txt` del round
(09:36 → 12:20). Con ogni albero `dirty=0`, **nessuno aveva più oggetto per costruzione**.

### 3.15 ✅ L'unica conferma del round che non sia una rimisura

Risk aveva risolto il conflitto `onsynced` (*«controller creato senza `onsynced`, chiamata
singola, verificato da A»*). I, **senza averlo letto**, ha descritto la stessa
configurazione partendo dal **perché** (`PageSyncModal:27,40` → … → `+page:2174`, e il
commento a `RiskAnalysisPanel:519-522` sul doppio invio già evitato una volta).

> **Due agenti che non si sono parlati convergono sulla stessa risoluzione da direzioni
> opposte.** Tutte le altre verifiche del round erano *qualcuno che rifà il conto di
> qualcun altro*; questa è **una causa e un effetto che combaciano senza essersi
> coordinati**.

### 3.16 Una richiesta senza misura non si può contraddire

> Le tre correzioni sono arrivate perché mi hai mandato ogni volta **il dato accanto
> all'affermazione**. Il verde-che-diventa-rosso l'ho trovato perché avevi scritto
> «registro a 10 contro 10» invece di «il gate resterebbe verde»: **il numero mi ha dato
> dove guardare**. Con la misura, la contraddizione la trova chiunque legga. (J)

---

## 4. Decisioni del developer — ✅ **risolte il 22/09**

| | cosa | esito |
|---|---|---|
| a | Le 422 chiavi morte **non** vanno cancellate in blocco (≥4 false) | ✅ *«Le chiavi verranno decretate morte solo alla vera fine del round di sviluppo»* → **nessuna cancellazione ora** |
| b | P4-11: **due** punti, non uno (il nono canale è l'asse Y) | ✅ *«andrà revisionato e toccherà anche gli assi Y dei grafici che mostrano il patrimonio (non percentuali o indicatori)»* → e la review l'ha poi **visto a schermo** ([08](08_review_visiva_20260922.md) R5/R6) |
| c | **Un prezzo di mercato è patrimonio?** 3 dei 9 render scoperti sono quotazioni | ✅ **NO.** *«Il patrimonio entra in gioco quando da quel numero si riesce a risalire a quanto possiede l'utente, e generalmente quindi ha a che fare con le transazioni e le quantità possedute»* |
| d | I 21 siti FX — stessa domanda, superficie diversa | ✅ **Niente da nascondere.** Verificato nel codice: `fx/[pair]/+page.svelte:795` chiede sempre `from_amount: {amount: '1'}` — la pagina espone **tassi**, non importi dell'utente |
| e | La descrizione i18n del tool PAC: coordinator o workstream? | ⏳ **aperta.** La review ha confermato che la card mostra ancora la descrizione del prototipo ([08](08_review_visiva_20260922.md) §3.1) |
| f | Voce di backlog sulle sonde che sbagliano verso il verde (§3.2, §3.6)? | ✅ *«Non importa, quando faremo i test di non regressione sono certo che i problemi salteranno fuori»* → **niente controlli positivi dedicati** |

**Corollari applicati** (dal criterio di `c`):

- **prezzo unitario WAC** → si mostra: *«al massimo si potrebbe risalire, con molto sforzo,
  ai momenti di acquisto, non necessariamente alle quantità»*. `WacPreviewSection:565,586`
  **non vanno riparati**.
- **numero di movimenti in Asset** → si mostra. È una **cardinalità**, non una quantità: dice
  quanto *spesso* hai agito, non quanto *hai*, e non è moltiplicabile per un prezzo.
- **la maschera copre il numero, non la valuta** → *«il privacy deve nascondere il numero,
  non la valuta, quindi se lo fa è un errore»*. Già il comportamento del codice (§9.2).
- **Tools** → oggi niente da nascondere, perché l'unico strumento non ha UI. ⚠️ **Ma il PAC
  prende `quanta liquidità investibile ho` e produce `quanto metto su ciascun ETF`: entrambi
  patrimonio puro.** Se il perimetro si chiude adesso, la sua UI nascerà fuori.

## 5. 🟡 Non sono difetti — dichiararli o qualcuno li «ripara»

- **`−•••`**: decisione **D8** del product owner, obiezione respinta.
  `maskable.ts:56-57` **vieta esplicitamente** di spostare il segno dentro la maschera.
  Costo accettato e dichiarato: la cella mascherata rivela `sign(amount)` — tre valori
  invece di due — e sei siti passano `showSign: value !== 0`, così una colonna mascherata
  mostra ancora **quali periodi hanno avuto attività**.
- **Il tour di onboarding** sopra il pannello: `+page.svelte:391` chiama
  `maybeStartContextual` in `onMount` incondizionatamente. Atteso.
  🔴 *Ma un tour che punta al comando morto della barra, no.*
- **Tre giorni vuoti in coda**: lane non ripopolata, non codice rotto.
- **`backend/data/test/*.db`** (file chiamato letteralmente così, 0 byte, 12 agosto):
  `touch` con le virgolette sbagliate, antico, innocuo. Accanto `librefolio.db` 0 byte
  del 13 agosto → **quel data-dir non è usato da un mese**.

## 6. Contromisure di misura adottate nel round

1. `N path in ⇒ Test Files deve dire N` (vitest nasconde i path inesistenti)
2. `git check-ignore -v`, non la lettura del `.gitignore` ovvio
3. `git merge-tree --write-tree` + confronto **blob**; cieco sui path in conflitto →
   confrontare i **simboli**
4. BRE: `$` è ancora solo in coda alla RE intera
5. `grep -c` che trova zero **esce con 1** → spezza `A && B && C`; usare `;`
6. `git log --no-pager` non esiste (è `git --no-pager log`)
7. **Hash** del client, non `mtime`, accanto a ogni numero `svelte-check`
8. Un output che non capisco **non è un dato** (D: quattro `?` hanno la forma di un risultato)
9. **Eseguire la regex, non dedurla** — anche quando è elementare (§3.5)
10. **Riportare la composizione, non il totale** (§3.3)
11. Dichiarare `FROZEN` **provando la porta**, non affermandola (§3.9)

## 7. Quirk ambientali

- invocare vitest da `frontend/` (`--prefix` sposta npm, non la cwd)
- `--reporter=basic` non esiste
- `git status --porcelain` default collassa una dir nuova → `-uall`
- `/tmp` viene ripulito
- `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …` obbligatorio
  nei worktree
- cataloghi i18n in `frontend/src/lib/i18n/{en,it,fr,es}.json`
- `i18n audit`, `mkdocs check-links` e `api sync` sono **statici**: non aprono porte
- struttura del log `i18n audit`: riga 39 `## Potentially Unused (422)` · riga 68
  `### 🔵 Not Verified (41)` · riga 138 `### ❌ Likely Unused (422)` → **463 righe elencate**,
  e l'intestazione padre dichiara il figlio invece della somma

## 8. Lane

```
coordinator 6150 + /tmp/librefolio-r2-main
I           6157 + /tmp/librefolio-r2-i-charts     (spenta e provata 12:47)
J           6158
```

Alle **12:47** verificate libere: `6040 6041 6042 · 6150–6159 · 5173`. Nessun processo
`dev.py`/`uvicorn` residuo.

---

## 9. Rettifiche dalla review d'uso — 22/09/2026, pomeriggio

Il round di §1–§8 è stato **solo statico**: nessuno ha eseguito l'applicazione. Nel pomeriggio
il developer l'ha usata davvero, su un giro pulito in produzione
([08](08_review_visiva_20260922.md)). Questa sezione registra **dove l'analisi statica ha
sbagliato**, perché è la parte che insegna di più.

### 9.1 🔑 §1.2 smentito — «morto» era «differito»

**L'analisi diceva**: il toggle Abs/% è morto sul tab correlazione. Prova: `:1500` e `:1544`
sono rami mutuamente esclusivi della stessa catena `if/else-if`, e l'unica lettura di
`globalViewMode` (`:1575`) vive dentro il ramo `grid`. Quindi, con correlazione attiva,
**zero lettori montati**.

**L'uso dice**: premi il toggle in correlazione, torni su Asset, **l'effetto è vivo**.

**Chi aveva ragione: entrambi, su domande diverse.** La misura era esatta su *chi legge
adesso*. Ma `globalViewMode` **non è locale al render**: è stato che sopravvive al cambio di
tab. Il lettore non era assente — era **in un altro momento**.

> 🔑 **La forma, perché si ripeterà.** L'analisi statica vede la *struttura del montaggio*;
> non vede il *ciclo di vita dello stato*. Un consumatore che si monta dopo è indistinguibile,
> per un lettore del solo sorgente, da un consumatore che non esiste. Per separarli serve
> qualcuno che prema il bottone e **poi cambi pagina** — cioè esattamente ciò che nessuna
> rilettura può fare.
>
> È la stessa famiglia del §3.5 («il ragionamento corretto sul pezzo che non decide»), ma con
> una differenza che vale la pena isolare: lì il frammento era *testuale*, qui è **temporale**.
> Il pezzo mancante non era altrove nel file: era **più tardi**.

**Resta vero, come nota d'uso**: il toggle compare **solo in modalità griglia**, e questo non
era scritto da nessuna parte. Chi documenta la pagina lo aggiunga.

### 9.2 §1.6 ridimensionato — la maschera copre il valore, non il canale

Vedi il richiamo in testa a §1.6. In sintesi: delle tre asserzioni del gate, **una** è cieca
sotto privacy (quella che cerca il valore), **due reggono** (quelle che cercano il canale),
perché `maskable()` avvolge solo l'importo e la valuta resta fuori.

**Errore a carico del coordinator**: ho accettato e propagato l'affermazione «il gate
passerebbe misurando nulla» senza eseguirla sull'output del formatter. È il §3.5 del mio
stesso registro, commesso dopo averlo scritto.

### 9.3 I «61 file orfani» in `custom-uploads` — rovesciato

Avevo segnalato 61 file sopravvissuti al `create-clean`. Sono gli **avatar di default**,
creati **dal** `create-clean`:

```
.avatars_seeded  →  "Seeded 30 avatars at 2026-09-22T11:11:03Z"   (13:11 locali)
un .json         →  "description": "Default avatar: men_04",  "uploaded_by_user_id": 0
                     30 png + 30 json + 1 sentinella = 61
```

La frase *«il reset azzera il DB, non il disco»* era esatta **al contrario**: il reset
**popola** il disco. Avevo dedotto l'orfanità dalla **sequenza degli eventi** senza aprire un
file.

### 9.4 `mkdocs gallery` senza `--data-dir` — non è un difetto

Decisione del developer: *«non è un difetto, è che all'epoca non avevamo porte e db diversi.
Tanto è una cosa che gira alla fine, e abbiamo modo di spostare noi db e porta per non
pestargli i piedi: meglio che lui sta fisso.»*

⚠️ **Ma il piano `15_parallelRuntimeIsolation` lo dichiara isolato**, e non lo è. Il documento
va corretto: è la differenza fra **un limite noto** e **una bugia**.

### 9.5 Il contratto PAC disatteso — documento invecchiato, non regressione

`handoff-pac-D.md` promette `1.0.0`/`analyze`/timeout 5s/`compute(parameters, context)`; il
codice consegna `2.0.0`/`plan`/30-65s/`compute(tool_code, parameters, context)`. Una sonda
l'aveva etichettato **regressione**.

**Il fatto è vero, l'etichetta no**: è il documento rimasto indietro. Istruzione del
developer: *«per casi come il suo, aggiorniamo i documenti prima di ripetere l'errore.»*

> 🔑 Una discrepanza documento↔codice ha **due letture opposte** — il codice è regredito,
> oppure il documento è invecchiato — e **il documento da solo non può dirti quale**. Serve la
> storia.

### 9.6 ✅ Misura nuova: gli argomenti ICU delle quattro lingue sono allineati

La review ha usato **una sola lingua** (italiano), e §R1 di [08](08_review_visiva_20260922.md)
ha rivelato una chiave ICU malformata che `i18n audit` dà per completa. Domanda naturale:
esistono chiavi rotte **solo** in francese o spagnolo, che nessuno ha mai visto?

Misurato su tutti e quattro i cataloghi:

```
chiavi confrontate: 3403   lingue: it, fr, es
argomenti ICU divergenti: 0        chiavi assenti in una lingua: 0
controllo positivo (en={days} vs it={giorni}) -> rilevata: True
sintassi non-ICU {{doppia}}: 1 chiave (risk.assetSet.levels.l1.lastedDays) × 4 lingue
```

⚠️ **Il primo tentativo di questa misura ha prodotto 21 falsi positivi**: il regex estraeva i
**rami interni delle forme plurali** (`{count, plural, one {…} other {…}}`), tradotti per
definizione, scambiandoli per nomi di argomento. Corretto restringendo l'estrazione a
`{identificatore` seguito da `,` o `}`.

📌 **Il controllo positivo è la riga che rende leggibile lo zero.** Senza, «0 divergenze» è
indistinguibile da uno strumento che non matcha nulla — che è precisamente il difetto
diagnosticato in §3.2 e §3.6. Qui costava una riga, e va notato che il developer aveva
ragione a non volerli in generale (§4.f): il loro valore dipende da quanto è fragile
l'estrazione, e questa lo era.

### 9.7 Ciò che la review ha **confermato**

| voce | esito |
|---|---|
| §1.1 card PAC con la descrizione del prototipo | ✅ vista a schermo |
| §2.1 `risk-lab` mai eseguito | ✅ *«alla fine della review va aggiornato per essere coerente col nuovo sistema»* → task per `test-author` |
| §2.2 P4-11, il nono canale (asse Y) | ✅ visto in Abs e in P&L |
| §1.7 chiavi vive dichiarate morte | ✅ nessuna cancellazione fino a fine round |

**Bilancio del confronto**: su ~7 voci verificabili a mano, l'analisi statica ne ha prese 4
giuste, una ridimensionata e **una sbagliata in pieno** — quella che richiedeva di premere un
bottone e cambiare pagina. Non è un buon tasso né un cattivo tasso: è la **firma del metodo**.
La rilettura trova ciò che è scritto; l'uso trova ciò che accade.
