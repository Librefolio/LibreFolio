# Performance charts — voce 10: le traduzioni nell'HTML dei tooltip si leggono come testo

**Stato:** ✅ **COMPLETATO E INTEGRATO**. Lotto chiuso il 2026-10-09 alle 12:25 (FROZEN). Commit del developer il
2026-10-09 alle 12:52: `48e736855` (il gate) e `2ee77d04e` (questo giornale). In `dev_release2` col treno 23, merge
`2c382824d`, punta `1ead733f2`. I residui 1–4 sono limiti accettati con la scelta (c) e dichiarati nell'intestazione
del gate («Completeness, stated honestly»): nessuna voce di backlog. Verificato e archiviato il 2026-10-09 in
`Release_2/phases/20_performanceCharts/`. La voce 10 del riepilogo del 06/10 è stata affidata a I dal developer
(«Sì: la 10 a I subito»). Dopo l'analisi, il 2026-10-09 il developer ha scelto la cura (c): «(c) Controllo dei
cataloghi nel gate, nessun sito toccato» (via coordinator, 11:48).
*Storia dello stato:* IN CORSO (2026-10-09), «Il lavoro entra nel treno 23».
**Workstream:** I (grafici performance) · ramo `e-alfy-performance-charts-plan` · coordinatore
`c8328a01-f208-4ade-a352-0486d1f14de2`.
**Baseline:** HEAD = `dev_release2` = `da8d7a10b`. Albero pulito, rimisurato alle 11:57.
**Lane:** suite `6157` + `/tmp/librefolio-r2-i`, solo `dev.py test …`, un comando alla volta. La `6167` qui non
serve. Preambolo: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …`.
**File concessi:** solo `frontend/src/htmlInterpolation.gate.test.ts`, più questo piano. Il gate l'ha scritto K, che
oggi non lo tocca. I cataloghi `frontend/src/lib/i18n/*.json` sono di L: li leggo soltanto.

Precedenti e collegati:

- Il gate di K (step 13, voce 0): `frontend/src/htmlInterpolation.gate.test.ts`, registrato in
  `front-utility core-unit` (`scripts/test_runner/_frontend_utility.py:106`).
- Voce indipendente: non nasce da un piano precedente di I, quindi niente collegamenti incrociati.
- *Verifica d'archivio, 2026-10-09:* il piano madre la elenca fra i seguiti (§6.0.20):
  [plan-phase00PerformanceCharts.prompt.md](plan-phase00PerformanceCharts.prompt.md).
- CHANGELOG: nessuna riga proposta. È un gate interno e l'utente non vede nulla; decide il coordinator.

## Stato di esecuzione

| Step | Contenuto | Stato |
|---|---|---|
| T0 | Baseline, analisi in sola lettura, prova del disegno sui cataloghi veri, questo piano | ✅ 2026-10-09 12:05 |
| T1 | I rossi (test-author): il `describe` nuovo, con gli stub | ✅ 2026-10-09 12:15: 6 rossi all'asserzione, come atteso |
| T2 | La cura: `translationMarkup` col parser di jsdom, e la visita dei cataloghi | ✅ 2026-10-09 12:17: `core-unit` verde, 3479/3479 |
| T3 | L'intestazione del gate: l'esenzione delle traduzioni si regge sul controllo | ✅ 2026-10-09 12:20 |
| T4 | Gate: `core-unit`, `front check`, Prettier, `git diff --check` | ✅ 2026-10-09 12:24: verdi; `front check` rosso fuori dal delta (client generato vecchio) |
| T5 | Pulizia di `/tmp/libreFolio_i_esc/`, CHECKPOINT READY, FROZEN | ✅ 2026-10-09 12:25 |

## Il problema

- Alcune traduzioni entrano nell'HTML dei tooltip dei grafici senza `escapeHtml`. Gli esempi della voce sono in
  `GrowthChart.svelte`: `eurLabels.nav` (`:2221`), `pnlLabels.total` (`:2243`), le righe OHLC (`:2253`) e
  `pnlLabels.bookValue` (`:2299`).
- Il gate le lascia passare di proposito: «Translations stay allowed there as everywhere» (`:63-66`). Lo fa con
  `I18N_CALLS` (`:198`) e `LABEL_BUNDLE` (`:177`).
- Il rischio è basso, perché i testi sono nostri. Ma una traduzione con `<` o `&` rompe il tooltip, e il gate non lo
  vede.

## L'analisi (2026-10-09, sola lettura, su `da8d7a10b`)

Una sonda con gli stessi parser del gate (TypeScript e il compilatore di Svelte) ha contato i siti che un gate stretto
segnalerebbe.

**Livello A** (`$_`/`$t`, e le proprietà dei bundle `labels`/`*Labels`, in contesto HTML senza `escapeHtml`):
**94 siti in 19 file**. Diventano 104 se si aggiungono a `HTML_FIRST_ARGUMENT` gli helper locali di GrowthChart
`signedRow` e `ohlcRow`.

- Grafici: 55 siti in 9 file, 65 con gli helper.
  - GrowthChart, 15 più 10 dagli helper:
    - testata `:1392 :1395 :1398 :1401`;
    - righe NAV/EUR `:2221 :2222 :2225 :2227 :2229 :2230 :2231`;
    - righe P&L `:2243 :2260 :2288 :2299`;
    - dagli helper: OHLC `:2255–:2258`, proventi `:2285 :2286 :2294 :2295 :2300 :2301`.
  - PerformanceChart, 8: `:517 :518 :519 :539 :540 :546 :547 :548`.
  - PriceChartFull, 6: `:347 :350×2 :858 :1018 :1027`.
  - CandlestickChart, 5: `:196 :199×2 :519 :522`.
  - LineChart, 5: `:760 :768×2 :776 :779`.
  - ExposureTreemap, 5: `:588–:591 :595`.
  - CorrelationHeatmap, 5: `:487×2 :488 :489×2`.
  - AllocationHistoryChart, 4: `:557×2 :561×2`.
  - ScatterChart, 2: `:151×2`.
- Fuori dai grafici: 39 siti in 10 file.
  - ImportWizardModal 15.
  - I toast delle impostazioni: ProfileTab 6, PreferencesTab 4, GlobalSettingsTab 1.
  - TransactionBulkModal 4.
  - `providerProbe.ts` 3, WacPreviewSection 2, `pairCellHtml.ts` 2, FxTable 1, TransactionPickerModal 1.

**Livello B** (l'alias `t(…)`): 5 siti, tutti in `utils/currency/fxConversionHelper.ts`
(`:116 :118 :120 :126 :129`).

**Livello C** (nomi neutri come `label`, `text`, `title`; è il punto cieco del gate, e qui sono solo contati):
33 siti in 18 file.

**Il markup voluto nei cataloghi** (4203 stringhe per lingua):

- Ci sono solo 3 chiavi, tutte errori delle transazioni: `transactions.errors.balanceAssetNegative`,
  `balanceCashNegative` e `costBasisRequired`. Usano `<strong>` e `<b>`, in tutte e 4 le lingue.
- Le produce solo `resolveValidationMessage.ts:222` (`transactions.errors.${code}`). Ogni chiamata di
  `resolveIssueMessage` passa da `{@html sanitizeHtml(…)}`: TransactionFormModal, TransactionBulkModal,
  ParseDetailModal. Non finiscono mai in un tooltip.
- I loro parametri passano già da `escapeHtml` (`:148`, e i nomi a `:167` e `:178`).
- Nessun altro valore contiene `<`.
- `&` compare in 49 valori inglesi e in 25 per IT, FR ed ES, quasi tutti «P&L». Il parser non ne decodifica nessuno.
- **Il difetto è latente**: oggi non si rompe niente.

**Le tre cure proposte:**

- (a) l'escape di ogni sito, circa 109 in 20 file, con il gate stretto;
- (b) solo i grafici (65 siti), con il gate stretto e i 44 restanti come debito che può solo scendere;
- (c) controllare i cataloghi invece dei siti.

Il developer ha scelto la (c).

## La cura (c): il controllo dei cataloghi

**Perché basta.**

- Il gate di K controlla già i *parametri* delle traduzioni: gli argomenti dopo la chiave arrivano
  all'interpolazione. Resta esente solo il *testo* della traduzione.
- Se ogni testo dei cataloghi, letto come HTML, dà sé stesso, l'escape non cambierebbe nulla: interpolarlo crudo è
  equivalente.
- In contesto di testo, `escapeHtml` cambia la resa solo per `<` e `&`. `>`, `"` e `'` si vedono uguali, crudi o
  escapati.
- Il controllo guarda la fonte e non i siti. Per questo copre anche le traduzioni che passano dall'alias `t(…)`
  (livello B) o da nomi neutri (livello C).

**Il contratto.** Tutto sta in `htmlInterpolation.gate.test.ts`, in una sezione nuova in fondo al file.

- `translationMarkup(value: string): string | null`
  - Restituisce `'contains "<"'` se il valore contiene `<`, in qualunque punto. È più severo del parser: `a < b` si
    vedrebbe giusto, ma è vietato lo stesso, e così la regola resta semplice.
  - Altrimenti restituisce `null` se non c'è `&`.
  - Altrimenti legge il valore col parser HTML di jsdom (`div.innerHTML = value`). Se `textContent` è diverso dal
    valore, restituisce `` `renders as «${text}»` ``; se no, `null`.
- `catalogMarkupFindings(catalogs, reviewed): {offenders: string[]; stale: string[]}`
  - `catalogs` è un record per nome di file (`'en.json'`). `reviewed` è un `ReadonlySet<string>` di chiavi puntate.
  - Visita ogni foglia stringa, a qualunque profondità, con la chiave puntata (gli array per indice). Le foglie che
    non sono stringhe le ignora.
  - `offenders`: ogni foglia segnalata da `translationMarkup` la cui chiave non è in `reviewed`, nel formato
    `` `${file}  ${key}  ${reason}` ``. L'ordine è quello dei cataloghi, poi quello del documento.
  - `stale`: le chiavi di `reviewed` che nessun catalogo segnala, nell'ordine del set. Una chiave revisionata resta
    necessaria finché almeno una lingua ha del markup lì.
- `SANITIZED_MARKUP_KEYS: readonly ReviewedMarkup[]`, con `ReviewedMarkup = {key: string; why: string}`.
  - È il gemello di `REVIEWED_EXCEPTIONS`: ogni voce porta un perché verificabile di almeno 20 caratteri.
  - Contiene le 3 chiavi d'errore, con il percorso del consumatore unico.
- I cataloghi si leggono dentro gli `it`, con una funzione, e non al caricamento del modulo. Così un catalogo
  illeggibile fa fallire solo questi test, non la raccolta dei test di K.
- jsdom si carica al primo uso, con `createRequire(import.meta.url)('jsdom')`.
  - Il pacchetto non ha dichiarazioni di tipo e `@types/jsdom` non è una dipendenza. Un `import` normale farebbe
    fallire `front check` con TS7016, perché `svelte-check` controlla anche i file di test.
  - Un cast locale tipa l'unico costruttore usato.
  - Il file resta nell'ambiente `node`, come il resto del gate.

**Perché jsdom e non una regex.** È il parser del browser.

- Ha la regola esatta dei nomi legacy senza `;`: `&notes` diventa `¬es`, `P&LT` diventa `P<`.
- Ha la tabella completa delle entità.
- Lascia stare `P&L;` e `S&P500`.
- Una regex dovrebbe portarsi i 106 nomi legacy, e la regola generica `&nome;` segnalerebbe `P&L;` per niente.

**Le autoverifiche** (il `describe` nuovo, scritto dal test-author):

1. Segnala ogni `<`, anche dove il parser lo mostrerebbe come testo: `Totale <b>P&L</b>`, `a < b`.
2. Segnala ogni riferimento che il parser decodifica, con o senza `;`:

   | Valore | Esito |
   |---|---|
   | `1 &lt; 2` | `renders as «1 < 2»` |
   | `&#60;b&#62;` | `renders as «<b>»` |
   | `&#x3C;` | `renders as «<»` |
   | `Profit &amp; loss` | `renders as «Profit & loss»` |
   | `&eacute;t&eacute;` | `renders as «été»` |
   | `&copy 2026` | `renders as «© 2026»` |
   | `R&notes` | `renders as «R¬es»` |
   | `P&LT` | `renders as «P<»` |

3. Lascia passare la `&` isolata: `P&L`, `P&L, R&D, M&A, AT&T`, `S&P500`, `P&L; Q&A`, `&#`, `&;`, `a > b`, le
   virgolette, il testo semplice e la stringa vuota danno `null`.
4. Visita i cataloghi annidati, array compresi, per chiave puntata, nell'ordine dei cataloghi e poi del documento.
5. Una chiave revisionata resta necessaria se il markup c'è in una lingua sola. Una revisionata senza markup, o
   assente, è `stale`.
6. Legge ogni catalogo della UI: `en`, `it`, `fr`, `es`.
7. Il verdetto: nei cataloghi veri nessun valore ha markup, fuori dalle chiavi revisionate. Il messaggio spiega la
   regola.
8. Le chiavi revisionate sono attuali e spiegate: nessuna `stale`, e ogni `why` ha almeno 20 caratteri.

**Le richieste del coordinator, una per una:**

- (1) «un `<` e un `&lt;` sintetici devono far fallire il controllo, «P&L» deve passare»: sono le autoverifiche 1–5.
- (2) «il controllo sui 4 cataloghi, con l'elenco esplicito delle 3 chiavi»: i test 6–8 e
  `SANITIZED_MARKUP_KEYS`, scritti in T1 dal test-author, diventano reali con la cura di T2.

**Gli stub di T1:**

- `translationMarkup` restituisce sempre una sentinella `RED STUB …`, cioè segnala tutto.
- `catalogMarkupFindings` non trova niente: `{offenders: [], stale: [...reviewed]}`.

**Il rosso atteso:** 1, 2, 3, 4, 5 e 8 falliscono all'asserzione.

- Il 6 è il controllo del caricamento, codice vero, e passa già.
- Il 7 passa a vuoto sotto gli stub.
  - Che sia vivo lo provano il 4, sui cataloghi sintetici, e l'8, sui cataloghi veri: la visita deve vedere le 3
    chiavi revisionate.
  - Un rosso del 7 servirebbe markup nei cataloghi, che non sono miei.

## I residui dichiarati

1. **I 2 siti in attributo.** Lì conta anche `"`, che il controllo in contesto di testo non vieta:
   - `ImportWizardModal.svelte:2310`, `title="${$t('importWizard.status.editBrokerDate')}"`;
   - `TransactionBulkModal.svelte:1783`, `title="${$t('transactions.bulk.partnerInaccessible')}"`.

   Oggi nessuna delle due chiavi contiene `"`, in nessuna lingua. Se una traduzione futura lo introducesse,
   l'escape tocca ai proprietari di quei file.
2. **`translateOr`** (`frontend/src/lib/utils/core/translateOr.ts`).
   - Se la chiave manca o la traduzione è vuota, restituisce un `fallback` letterale scritto nel codice.
   - Quei letterali non stanno in nessun catalogo, quindi il controllo non li vede.
   - Si usa in LotGanttChart, LotComparisonChart, LotWacPriceChart, OtherPeriodEffectsTable, PerformanceChart e
     ReportSetCard.
3. **I bundle di etichette** (`LABEL_BUNDLE`).
   - L'esenzione si regge sul nome: un bundle deve contenere solo traduzioni.
   - Rivisti: `eurLabels` e `pnlLabels` di GrowthChart (`:603`, `:614`) e `labels` di PerformanceChart (`:302`).
     Sono tutti `$_` senza parametri.
4. **I nomi neutri** (`label`, `title`, `text`): 33 siti di livello C.
   - Per le traduzioni ora li copre il controllo dei cataloghi.
   - Per il testo dell'utente restano il punto cieco del gate di K, già dichiarato nella sua intestazione: non è la
     voce 10.

## Gate (T4)

- `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir
  /tmp/librefolio-r2-i front-utility core-unit`
- `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front check`: `svelte-check`, che controlla
  anche il tipo del `createRequire`.
- Prettier sul file, lanciato da `frontend/`: `node_modules/.bin/prettier --check src/htmlInterpolation.gate.test.ts`.
- `git diff --check`.

## Definition of done

- I test nuovi sono rossi sugli stub, come atteso, e verdi con la cura.
- `core-unit` è verde per intero, compresi i test di K, che restano invariati.
- `front check` dà 0 errori, Prettier è pulito, `git diff --check` è vuoto.
- L'intestazione del gate dice su cosa si regge l'esenzione delle traduzioni, e dichiara i residui.
- Nessun sito toccato e nessun catalogo toccato. Il delta è di 2 percorsi: il gate e questo piano.
- `/tmp/libreFolio_i_esc/` è cancellata, le porte sono libere, e lo stato è FROZEN.

## Registro

### T0 — baseline, analisi, prova del disegno, piano (2026-10-09 12:05)

> **Note implementazione**:
>
> - Baseline verificata alle 11:57: HEAD = `dev_release2` = `da8d7a10b`, 0 voci in `git status`, porte
>   `6157`/`6167` libere.
> - Il disegno è stato provato fuori dal repo, con lo stesso jsdom del frontend, sui 4 cataloghi veri
>   (`/tmp/libreFolio_i_esc/contract_check.mjs`): 25 controlli su 25 tornano.
>   - Le autoverifiche 1–5 danno gli esiti della tabella.
>   - Il verdetto sui cataloghi veri è vuoto con le 3 chiavi revisionate. Senza revisione dà 12 righe: 3 chiavi per
>     4 lingue.
>   - I file JSON in `src/lib/i18n` sono solo `en`, `es`, `fr`, `it`.
>   - 4203 stringhe per lingua, nessun array, nessuna foglia che non sia una stringa, nessun CR o NUL.
> - Il consumatore unico delle 3 chiavi è stato riverificato: `resolveValidationMessage.ts:222`, e tutte le chiamate
>   di `resolveIssueMessage` sono avvolte in `sanitizeHtml`.

> **⚠️ Fuori pista — jsdom non ha i tipi.**
>
> - jsdom 30.0.1 non pubblica dichiarazioni di tipo, e `@types/jsdom` non è nel `package.json`.
> - `svelte-check` controlla anche i file di test: `tsconfig.json` esclude solo `e2e/**` e `playwright.config.ts`, in
>   modalità `strict`. Un `import {JSDOM} from 'jsdom'` fallirebbe con TS7016.
> - La scelta: `createRequire` con un cast locale, senza toccare dipendenze né la configurazione di vitest. Nel
>   frontend non c'è un precedente di `createRequire`.

> **⚠️ Fuori pista — Prettier va lanciato da `frontend/`.** Dalla radice del repo,
> `frontend/node_modules/.bin/prettier --check …` non trova `prettier-plugin-svelte`. Da `frontend/` il file di K è
> pulito.

### T1 — i rossi (2026-10-09 12:15)

> **Note implementazione — il test-author.**
>
> - Ha aggiunto la sezione in coda al gate, righe 874–1012: `ReviewedMarkup`, `SANITIZED_MARKUP_KEYS` con le 3 chiavi
>   e i loro `why`, `CATALOG_DIR`, `readCatalogs()`, i due stub e il `describe` con gli 8 `it` del contratto.
> - Le righe 1–873 di K sono identiche byte per byte: stesso SHA-256 di `git show HEAD:…` e di `head -n 873`. Il diff
>   è un solo blocco, `@@ -873,0 +874,139 @@`, senza righe tolte.
> - Non ha eseguito suite. Prettier `--check` pulito, lanciato da `frontend/`.
> - Nessuno scostamento dal contratto. Ha aggiunto solo testo: il commento di sezione e commenti brevi negli `it`.

> **Note implementazione — il rosso.** Comando:
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir
> /tmp/librefolio-r2-i front-utility core-unit` (log `/tmp/libreFolio_i_esc/red_core_unit.log`, 12:15).
>
> - Esito: `Test Files 1 failed | 118 passed (119)`, `Tests 6 failed | 3473 passed (3479)`.
> - Il file del gate ha 26 test: 6 rossi, gli altri 20 verdi (i 18 di K più il 6 e il 7).
> - I 6 rossi sono quelli attesi, tutti `AssertionError`:
>   - 1, 2 e 3: la sentinella `RED STUB …` al posto di `contains "<"`, di `renders as «1 < 2»` e di `null`;
>   - 4: `offenders` vuoto al posto delle 4 righe;
>   - 5: `stale: ['e.r']` al posto di `[]`;
>   - 8: le 3 chiavi revisionate, lette come `stale`.
> - Nessun errore di raccolta o di import.

### T2 — la cura (2026-10-09 12:17)

> **Note implementazione.** Ho cambiato solo il gate, con il disegno provato in T0. Gli 8 test del test-author non
> li ho toccati.
>
> - Ho aggiunto l'import `createRequire` da `node:module`.
> - `textOfHtml(html)`: un `div` di jsdom creato al primo uso, così i test di K non lo pagano. Gli dà `innerHTML` e ne
>   legge `textContent`. jsdom è caricato con `createRequire` e il suo costruttore è tipato a mano: jsdom non ha
>   dichiarazioni di tipo, e `@types/jsdom` non è tra le dipendenze.
> - `translationMarkup(value)`:
>   - qualunque `<` dà `contains "<"`;
>   - senza `&` dà `null`, perché nel contenuto di testo l'escape cambia la resa solo per `<` e `&`;
>   - altrimenti confronta il testo che il parser ne ricava con il valore: diverso dà `renders as «…»`, uguale dà
>     `null`.
> - `catalogMarkupFindings`: visita ricorsiva per chiave puntata, array compresi, in ordine di catalogo e di
>   documento. Divide i reperti tra `offenders`, fuori dall'elenco, e chiavi revisionate trovate; le revisionate mai
>   trovate sono `stale`.
> - Ho tolto le righe «RED STUB» dai commenti e il prefisso `_` dai parametri.
>
> **Prova.** Stesso comando di T1, log `/tmp/libreFolio_i_esc/green_core_unit.log`, 12:16:50:
> `Test Files 119 passed (119)`, `Tests 3479 passed (3479)`.
>
> - Il numero dei test è quello del rosso: nessun test perso o aggiunto.
> - Il test 8, il controllo positivo sui cataloghi veri, è verde. Quindi la visita trova davvero le 3 chiavi
>   revisionate in tutte e 4 le lingue: il verde del test 7 non è vuoto.
> - Prettier `--check` pulito, lanciato da `frontend/`.

### T3 — l'intestazione del gate (2026-10-09 12:20)

> **Note implementazione.** Ho aggiunto testo all'intestazione di K, in quattro punti, senza togliere niente:
>
> - **«What it reads»:** il gate legge anche i cataloghi della UI, `src/lib/i18n/*.json`. Il testo di una
>   traduzione si controlla dove è scritto, non dove è usato.
> - **La frase dell'esenzione** («Translations stay allowed there as everywhere…»): ora dice che l'esenzione si regge
>   su un controllo dei cataloghi, non sulla fiducia nei loro testi, e rimanda alla sezione nuova.
> - **La sezione nuova «Translations»,** tra «The allow-list» e «Completeness». Dice:
>   - perché si controllano i cataloghi e non i siti: il testo viene dai cataloghi, per qualunque strada passi (`$t`,
>     un alias, un bundle, un nome qualunque);
>   - la regola: nessun `<`, nessuna `&` che il parser decodifica, la `&` isolata ammessa;
>   - il parser, che è quello di jsdom;
>   - `SANITIZED_MARKUP_KEYS` e `sanitizeHtml`, e la voce `stale`;
>   - che gli argomenti di un messaggio non sono dei cataloghi: li controlla la regola di K, nei limiti dichiarati.
> - **«Completeness, stated honestly»:** tre punti nuovi, che sono i residui 1–3 qui sotto. Il residuo 4 (i nomi
>   neutri) era già il primo punto di K, e non l'ho ripetuto.
>   - la traduzione dentro un attributo (`title="${$t(…)}"`), dove conta anche `"`;
>   - il `fallback` di `translateOr`, un letterale del codice;
>   - il bundle riconosciuto dal nome e non dal contenuto.
>
> Le costanti `LABEL_BUNDLE` e `I18N_CALLS`, e i loro commenti, non le ho toccate.

> **⚠️ Fuori pista — la frase sulle virgolette.** Prima di scriverla ho controllato due fatti.
>
> - Con la ricerca di `attributo="${traduzione…` sui sorgenti, i siti in attributo sono esattamente i 2 già noti.
> - I cataloghi contengono `"`: 27 valori in `en`, 26 in `it`, 17 in `fr`, 23 in `es`. Nessuno però sta nelle 2 chiavi
>   dei `title`.
>
> Quindi l'intestazione non dice «nessuna traduzione contiene `"`», che sarebbe falso. Dice: nessuna delle due
> traduzioni interpolate oggi in un `title`.

### T4 — gate (2026-10-09 12:21–12:24)

> **Note implementazione — gli esiti, sul file finale, intestazione compresa.**
>
> - `core-unit` (comando di T1, log `final_core_unit.log`, 12:21): `Test Files 119 passed (119)`,
>   `Tests 3479 passed (3479)`. Il conteggio è uguale a quello del rosso e del verde di T2.
> - Prettier `--check`, lanciato da `frontend/`: pulito.
> - `git diff --check`: vuoto. Il diff del gate è 199 righe aggiunte e 2 tolte.
>   - Le 2 tolte sono le due righe dell'intestazione che ho allungato: la frase dell'esenzione, e l'ultimo punto di
>     «Completeness», chiuso ora con `;`.
>   - Il codice di K è invariato.
> - Il piano: niente spazi in coda, niente tabulazioni, niente percorsi personali.

> **⚠️ Fuori pista — `front check` rosso, ma fuori dal delta.**
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front check` esce con 1:
> `svelte-check found 2 errors and 0 warnings in 2 files`. Nessuno dei due errori è nel gate.
>
> - **Dove sono:** `pac-allocator/planner/result/model.ts:352` e `LedgerTable.svelte:92`. In tutti e due,
>   `rounding_delta` è tipato `string`, ma il codice si aspetta l'unione esatta `{value, kind: "finite_decimal"} | …`.
> - **La causa: il client API generato della mia worktree è vecchio.** Il client è ignorato da Git.
>   - `generated.ts` e `generated-tools.ts` sono dell'8/10 alle 20:28, l'ultimo `api sync` del lotto eventi.
>   - `bffc634b0` (`fix(pac): exact FX residual, coherent cross rates`) è del 9/10 alle 07:51. Ha cambiato
>     `rounding_delta: PlannerFixedDecimal` in `ExactNumber` in `backend/app/schemas/pac_allocator.py`, insieme a
>     `model.ts` e `LedgerTable.svelte`.
>   - `generated-tools.ts:843` ha ancora `z.string()` per quel campo.
> - **Verdetto `test-triage`: ambiente.** Non è un difetto del prodotto né del mio delta.
> - **Cosa non ho fatto:** non ho rigenerato il client. `api sync` è una generazione API, che spetta al coordinatore, e
>   in questo lotto non è concessa. Basta lanciarla nella corsia per azzerare i due errori; il codice non cambia.
>
> **La prova che il gate è pulito**, senza toccare la worktree. Ho lanciato `tsc` 5.9.3, quello del lock
> (`frontend/node_modules/.bin/tsc`), con un `tsconfig` temporaneo in `/tmp`. Quel file estende
> `frontend/tsconfig.json` (`strict`), con `noEmit`, `include: []` e un solo file radice.
>
> | File radice | Esito |
> |---|---|
> | il gate | uscita 0, nessun `error TS`; il file è nella lista di `--listFiles` |
> | `model.ts` (taratura) | riproduce lo stesso `model.ts(352,73): error TS2345` di `svelte-check` |
> | un controllo negativo (`const x: number = "…"`) | preso, `TS2322` |
>
> - Nella taratura compaiono anche 4 errori di tipi ambientali (`$app/*`, `import.meta.env`). Sono attesi con
>   `include: []`, che esclude `ambient.d.ts`.
> - Il gate non importa nessuno di quei moduli, quindi nel suo caso non contano.
> - Lo stesso controllo conferma anche il punto aperto di T0: `new Set()` nei test 4 e 5 compila.
>
> Il criterio «`front check` dà 0 errori» della Definition of done è quindi soddisfatto per il delta. Sull'intero
> progetto serve prima l'`api sync`.

### T5 — chiusura (2026-10-09 12:25)

> **Note implementazione.**
>
> - Ho cancellato `/tmp/libreFolio_i_esc/`, come chiesto dal coordinatore: `ls` risponde «No such file or
>   directory».
>   - La cartella conteneva i log del rosso, del verde e del finale, il diff dell'intestazione, le prove del
>     contratto di T0, i `tsconfig` temporanei e il controllo negativo di T4.
>   - Gli esiti sono citati qui sopra, con i numeri.
> - Porte libere: `lsof -nP -iTCP:6157 -sTCP:LISTEN` e `lsof -nP -iTCP:6167 -sTCP:LISTEN` escono con 1, senza
>   righe. Non ho avviato server.
> - Il delta è di 2 percorsi:
>   - `frontend/src/htmlInterpolation.gate.test.ts`, modificato;
>   - questo piano, nuovo.
> - Nessun sito, nessun catalogo, nessun file condiviso toccato. Niente in stage.
> - Fuori dal delta, ignorati da Git: i log per unità del runner in `.testLog/`, e l'istantanea del DB di test della
>   mia corsia.
> - Stato: CHECKPOINT READY inviato al coordinatore, poi FROZEN.
