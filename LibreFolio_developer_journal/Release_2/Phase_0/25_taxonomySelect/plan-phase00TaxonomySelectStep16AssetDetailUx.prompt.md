# Piano — K / step 16: tre ritocchi di UX (tooltip su mobile, avanti/indietro fra asset, testi social)

> Perimetro nuovo chiesto dal developer il 06/10, assegnato dal coordinator. Questo file è per ora **l'analisi**
> (sola lettura, nessun codice): l'implementazione parte solo dopo l'autorizzazione del developer. Viene dopo lo
> step 15 ([`plan-phase00TaxonomySelectStep15ToolbarSweepGutter.prompt.md`](plan-phase00TaxonomySelectStep15ToolbarSweepGutter.prompt.md)).

| | |
|---|---|
| **Baseline** | `385238e85` (fast-forward confermato dal coordinator; `dev_release2` = `ace3fd8ac`, solo `TODO_FUTURI.md` in più) |
| **Lane suite** | `--test-port 6155 --data-dir /tmp/librefolio-r2-k`, preambolo `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc` |
| **Copia di prod** | **non autorizzata**: va chiesta ogni volta (coordinator, 06/10). Di default dati sintetici, per esempio un asset di test con un nome di 58 caratteri. Quella dell'analisi è stata fatta senza permesso, poi cancellata (vedi 16.0) |
| **Vincolo** | in `assets/[id]/+page.svelte` modifiche minime; il nuovo in componenti a parte (la famiglia Risk lavora sui componenti di rischio del dettaglio) |

## Analisi (06/10, sola lettura; sonde in `/tmp/libreFolio_k16_*.mjs`)

### 1. Il riquadro che esce dallo schermo è il tooltip del grafico prezzi

Misurato sulla **copia di prod**, cioè sui dati del developer. Presi i 6 asset con il nome più lungo (50–58
caratteri), in emulazione telefono a 390 e 360 px:

- **pagina**: nessuna scatola oltre il bordo. Testate la Panoramica a pannelli chiusi e aperti (segnali, misure,
  metadati) e il tab Rischio; `scrollWidth` è sempre uguale alla larghezza;
- **tooltip del grafico in modalità linea** (`PriceChartFull.svelte:908-1010`): largo **362–386 px**, con
  `white-space:nowrap` (default di ECharts, `TooltipHTMLContent.js:55`). Il contenitore del grafico è largo 309 px a
  390 e 279 px a 360, quindi il tooltip esce dallo schermo di **20–44 px a 390** e **50–74 px a 360**. Lo screenshot
  mostra il valore tagliato al bordo. Un tooltip non si scorre: è «l'infobox» della nota;
- **candele** (`CandlestickChart`) e **Rendimento mobile**: tooltip larghi 187–275 px, sempre dentro.

La causa sta nella riga della serie principale: `👑` + icona + nome (già troncato a 30 caratteri da `truncateName`,
`utils/text.ts:1`) + valuta + `: valore` a 4 decimali, tutto su una riga che non può andare a capo. Il
posizionamento (`tooltipPositionSide`, `echartsTooltipHelpers.ts:186`) tiene il tooltip nel grafico solo se è più
stretto del grafico.

Sui dati di test le sonde di pagina non trovano niente: i nomi lunghi dei mock non hanno prezzi, e lo stesso vale con
l'asset 2 rinominato temporaneamente e poi ripristinato. Il tooltip lì non si apre col tap emulato; sulla copia si apre
passandoci sopra col mouse.

**Proposta**: troncare, non andare a capo. Si è già sulla pagina dell'asset, quindi il nome nel tooltip è ridondante,
e andare a capo allungherebbe il tooltip coprendo il grafico.
- Il tooltip si limita alla larghezza del grafico (`chartInstance.getWidth() − 16`, letta nel formatter a ogni
  apertura, quindi vale anche dopo un ridimensionamento).
- Ogni riga diventa una linea flessibile: l'etichetta si accorcia con i puntini, mentre valore, valuta e nota d'asse
  restano sempre interi.
- Vale per tutte le righe, quindi anche per i segnali e gli asset di confronto.
- `PriceChartFull` è usato anche dal dettaglio FX, dove le etichette sono corte: lì il comportamento non cambia.

### 2. Avanti e indietro fra gli asset

Stato attuale:
- la lista (`assets/+page.svelte`) tiene i filtri **solo in memoria** (`:152-163`: ricerca, tipi, valute,
  attivi/inattivi); tornando dal dettaglio si azzerano;
- l'ordinamento della vista tabella è interno a `DataTable` (`sortState`, `:180`, non salvato); `localStorage` tiene solo
  la vista griglia/tabella (`assetsViewMode`) e le colonne;
- nella griglia l'ordine è quello di `orderAssetsByLifecycle` (`:283`), diviso in tre pannelli (miei, di altri, in
  analisi); nella tabella c'è un `AssetTable` per pannello, ognuno col suo ordinamento;
- il dettaglio si apre con `goto('/assets/{id}?start&end')` (`AssetCard.svelte:153`, `AssetTable.svelte:305`).
- Il dettaglio **ricarica già tutto** quando cambia l'id sulla stessa route (`:1439-1447`, con le guardie
  `current()`), quindi prev/next può restare sulla stessa route.
- «Indietro» usa `goBack('/assets')`, una pila esplicita (`navigationStore.ts:72`).
- Nessun gestore di tastiera globale nella pagina né nel grafico; `TabBar` non usa le frecce.

**Proposta**:
- **Elenco seguito**: quello che l'utente ha lasciato, cioè l'ordine visibile con filtri, pannelli, vista e
  ordinamento.
  - La lista lo pubblica a ogni cambiamento in un piccolo store di sessione (`sessionStorage` per utente, azzerato al
    logout), quindi vale qualunque sia il modo di aprire il dettaglio (clic, link, nuova scheda).
  - Nella vista tabella serve l'ordine delle righe filtrate e ordinate, su tutte le pagine: una callback opzionale
    nuova di `DataTable` (`onRowOrderChange`), passata da `AssetTable`. È solo un'aggiunta.
- **Nel dettaglio**, un componente nuovo `AssetBrowseNav` nella riga dell'intestazione: `‹ 3/12 ›`. Nella pagina
  cambiano solo l'import e una riga.
- **Ai bordi**: niente giro circolare; il pulsante si disattiva al primo e all'ultimo, e il contatore dice dove si è.
- **Senza elenco** (link diretto, apertura dalla dashboard o dalle transazioni, asset non più nell'elenco): i pulsanti
  non compaiono. Alternativa: usare l'ordine predefinito della lista, senza filtri. → *Il developer ha scelto
  l'alternativa (vedi Decisioni).*
- **Cronologia**: prev/next **sostituisce** la voce corrente (`replaceState`), così «Indietro» riporta alla lista e non
  all'asset precedente. Serve un'aggiunta in `navigationStore.ts`: la pila non distingue un `goto` che sostituisce da
  uno che aggiunge.
- **Tastiera**: ← e → fanno lo stesso, solo se (→ *scartata dal developer: solo i pulsanti*):
  - nessun modificatore (Alt+← è il «indietro» del browser);
  - il focus non è in un campo, una lista, un menu, uno slider, una griglia o un tablist;
  - nessuna modale aperta;
  - l'evento non è già stato gestito.
- **Facoltativo (2b)**: tornando alla lista, ripristinare i filtri (snapshot di SvelteKit). Oggi «uscire e rientrare»
  li perde.

### 3. Testi di condivisione

Oggi:
- i 5 testi (`support.share.{x,reddit,facebook,instagram,tiktok}.message`, più `reddit.title`) stanno nei cataloghi;
- `supportLinks.ts` aggiunge solo il link (`buildSocialShareCopy`, `:76`);
- il «server» compare in: `reddit.title` («on my own server»), `reddit.message` («install on your own server»),
  `facebook.message` («run on your own server»), `instagram.message` («host on your own server»), `tiktok.message`
  («on my own server»); X no;
- gli hashtag ci sono solo in X, Instagram e TikTok, e in parte tradotti (`#Investimenti`, `#AutoHebergement`,
  `#CodigoAbierto`…): non si tracciano da una lingua all'altra.

**Proposta**:
- **Hashtag fuori dai cataloghi**: una costante `SHARE_HASHTAGS` in `supportLinks.ts`, aggiunta in coda al messaggio
  per **tutti e 5** i social.
  - Uguale in ogni lingua per costruzione, ed è un solo punto da cambiare.
  - Il testo mostrato nella modale coincide con quello copiato e con quello inviato a X e Reddit.
  - Su Reddit gli hashtag vanno nel corpo, non nel titolo: non sono attivi, ma restano cercabili.
- **Insieme raccomandato** (inglese, la lingua dei tag): `#LibreFolio #OpenSource #SelfHosted #PersonalFinance`.
  - `#SelfHosted` descrive la categoria del prodotto ed è una comunità grande. Togliere la frase «sul mio server» non lo
    rende sbagliato.
  - Alternativa senza il tema server: `#LibreFolio #OpenSource #PortfolioTracker #PersonalFinance`.
  - → *Il developer li vuole tutti e 5: `#LibreFolio #OpenSource #SelfHosted #PortfolioTracker #PersonalFinance`.*
- **Testi nuovi** (EN/IT qui; FR e ES li seguono fedelmente). Si toglie il «server» in prima persona, si toglie anche la
  descrizione «da installare sul tuo server», si tengono il controllo dei dati e l'open source:
  - `reddit.title`: «Trying LibreFolio, an open-source portfolio tracker» / «Sto provando LibreFolio, un gestore di
    portafoglio open source».
  - `reddit.message`, secondo paragrafo: «It's an open-source portfolio tracker to organize your holdings and explore
    their performance, while keeping your data under your control. If that sounds useful, take a look!» / «È un
    programma open source per organizzare il portafoglio e analizzarne l'andamento, mantenendo i dati sotto il tuo
    controllo. Se cerchi qualcosa di simile, dagli un'occhiata!».
  - `facebook.message`, secondo paragrafo: «If you're looking for an open-source portfolio tracker that keeps your data
    under your control, give it a look!» / «Se cercate un gestore di portafoglio open source che lasci i dati sotto il
    vostro controllo, dateci un'occhiata!».
  - `instagram.message`: «A little more order in my investments, without leaving my data elsewhere. I'm trying
    LibreFolio, an open-source portfolio tracker.» / «Un po' più di ordine nei miei investimenti, senza lasciare i miei
    dati altrove. Sto provando LibreFolio, un gestore di portafoglio open source.».
  - `tiktok.message`: «My new sidekick for tracking my portfolio: LibreFolio. Open source, with my data under my control.
    If you like tinkering, check it out!» / «Il mio nuovo alleato per tenere d'occhio il portafoglio: LibreFolio. Open
    source, con i miei dati sotto controllo. Se ti piace smanettare, dagli un'occhiata!».
  - `x.message`: stesso testo di oggi, senza gli hashtag, che arrivano dal codice.
- Le chiavi si cambiano solo con `dev.py i18n update`, nessuna chiave nuova.

## Decisioni del developer (06/10, nella chat di K, risposte testuali)

1. **Voce 1**: «Troncare con i puntini, valore sempre intero».
2. **Voce 2**:
   - elenco seguito: «L'elenco che ho lasciato nella lista: filtri, vista e ordinamento»;
   - senza elenco (link diretto, Dashboard, Transazioni, asset non più nel filtro): «Usare tutti gli asset, nell'ordine
     predefinito della lista». Interpretazione di K: la lista come appare senza filtri, cioè gli attivi nell'ordine della
     griglia (miei → di altri → in analisi, ognuno in ordine di ciclo di vita). Se l'asset aperto è inattivo, entrano
     anche gli inattivi, come con l'interruttore «inattivi». Da correggere se il developer la intende diversamente;
   - «Indietro»: «"Indietro" riporta alla lista»;
   - tastiera: «No, solo i pulsanti» → **niente ← →**;
   - 2b: «Sì, ma dopo che Risk ha integrato la sua lista: per ora va nel backlog».
3. **Voce 3**:
   - hashtag: «in realtà vorrei tenere entrambi i temi, quindi mettiamoli tutti e 5» → **`#LibreFolio #OpenSource
     #SelfHosted #PortfolioTracker #PersonalFinance`**;
   - testi: «Approvo i testi proposti».
4. **Autorizzazione**: «Sì, parti», sul riepilogo delle decisioni, l'ordine 1 → 3 → 2, un commit per voce, rosso prima,
   solo dati sintetici.
5. **Coordinator (06/10, 11:07)**: «Confermato, parti». Checkpoint diviso:
   - il primo dopo le voci 1 e 3, piccole e indipendenti, così entrano subito in `dev_release2`;
   - la voce 2 col suo checkpoint, compreso il `merge-file` contro `f6b7273f8`;
   - il test che protegge la copia di `assetScope` deve nominare nel messaggio d'errore il file da allineare;
   - 2b nel backlog di fine round.

### Progetto aggiornato della voce 2 (dopo le decisioni e i vincoli del coordinator)

- **Pubblicazione dell'ordine**, con al massimo tre righe in `assets/+page.svelte`:
  - un componente senza markup, `AssetBrowseOrder`, riceve i pannelli e la vista (import più una riga);
  - nella vista tabella ogni `AssetTable` pubblica il segmento del suo pannello: riceve `browseSegment={panel.id}` (una
    riga) e passa la callback nuova `onRowOrderChange` di `DataTable`;
  - lo store compone i segmenti nell'ordine dei pannelli.
- **Ordine predefinito** (quando manca l'elenco): `AssetBrowseNav` lo calcola da solo, leggendo `/assets/query`. Usa
  `orderAssetsByLifecycle` (già condivisa) e una funzione di pannello che deve restare uguale a `assetScope` della
  lista (`:333-337`): non si può importare dalla pagina, quindi la copia va protetta da un test.
- **Cronologia**: prev/next con `goto(..., {replaceState: true})` più un'aggiunta in `navigationStore.ts`, perché la
  pila sostituisca la voce in cima invece di aggiungerne una. Si conservano `start` ed `end` della query.
- **Niente tastiera**: niente guardie da scrivere, niente test di tastiera.

### Backlog

- **2b**: ritrovare i filtri della lista al ritorno (snapshot di SvelteKit), dopo l'integrazione della lista di Risk.

## Superfici e conflitti

| Voce | File | Note |
|---|---|---|
| 1 | `components/charts/PriceChartFull.svelte` (formatter `:914-1010`), `echartsTooltipHelpers.ts` (helper della riga) | condiviso col dettaglio FX; nessun altro ramo li tocca (coordinator, 06/10) |
| 1 | `src/htmlInterpolation.gate.test.ts` | il gate XSS dello step 13 deve conoscere il nuovo helper, se riceve HTML d'etichetta |
| 2 | nuovi `components/assets/AssetBrowseNav.svelte`, `components/assets/AssetBrowseOrder.svelte`, `lib/stores/assets/assetBrowseContext.svelte.ts` | nuovi |
| 2 | `assets/[id]/+page.svelte` | solo import e una riga nell'intestazione (`:2681-2685`) |
| 2 | `assets/+page.svelte` | **la riscrive la famiglia Risk**: al massimo tre righe (import, `AssetBrowseOrder`, `browseSegment`), fuori dalle zone di Risk (`:205-487`, `:1258-1480`); `git merge-file` contro `f6b7273f8` prima del checkpoint, codice d'uscita salvato |
| 2 | `AssetTable.svelte`, `table/DataTable.svelte`, `stores/app/navigationStore.ts` | condivisi, solo aggiunte; nessun altro ramo li tocca oggi. Su `DataTable` più avanti F aggiunge le opzioni di `navigateToRowId`: i test di K stanno in `DataTable.rowOrder.test.ts` |
| 2 | i18n: `assetDetail.browse.{previous,next,position}` ×4 con `dev.py i18n add` | in aggiunta |
| 2 | doc utente `mkdocs_src/docs/user/assets/detail/` (EN, docs-writer) | debito di traduzione dichiarato |
| 3 | `components/support/supportLinks.ts`, `SocialShareModal.svelte`, 6 chiavi `support.share.*` ×4 | nessun altro le tocca (coordinator) |

## Test (red-first, test-author)

- **Voce 1**:
  - Vitest dell'helper della riga: etichetta con i puntini, valore intero, larghezza massima applicata, escape intatto;
  - E2E in `assets/asset-mobile-layout.spec.ts`, che è già di K: un asset del test con un nome lungo e prezzi
    (`mockprov`, come lo sweep), a 390 e 360 px. Si passa sul grafico e il tooltip (`z-index: 9999999` dentro
    `asset-detail-chart`) deve stare dentro `<html>`, col valore visibile; controllo positivo per l'assenza. Rosso
    prima: 20–74 px fuori.
- **Voce 2**:
  - Vitest dello store (`assetBrowseContext`): pubblica, compone i segmenti nell'ordine dei pannelli, calcola i vicini
    e i bordi, gestisce l'id assente, si azzera al logout;
  - Vitest dell'ordine predefinito: la funzione di pannello copiata deve dare gli stessi gruppi di `assetScope` della
    lista, sugli stessi casi;
  - Vitest di `DataTable` in **`DataTable.rowOrder.test.ts`**: `onRowOrderChange` riceve gli id filtrati e ordinati, su
    tutte le pagine, e cambia con l'ordinamento e coi filtri di colonna;
  - Vitest di `AssetBrowseNav`: contatore, disattivo ai bordi, ordine predefinito senza elenco, `goto` con
    `replaceState` e la query conservata;
  - E2E nuovo, `assets/asset-browse.spec.ts`. Sulla griglia filtrata, e sulla tabella ordinata per una colonna, l'ordine
    atteso si legge dal DOM della lista, non da posizioni fisse. Poi si verificano:
    - avanti e indietro seguono quell'ordine;
    - i pulsanti si disattivano ai bordi;
    - aperto senza passare dalla lista (URL diretto), segue l'ordine predefinito;
    - «Indietro» riporta alla lista anche dopo più passi;
    - a 390 e 360 px la pagina non scorre di lato.
- **Voce 3** (insieme: `#LibreFolio #OpenSource #SelfHosted #PortfolioTracker #PersonalFinance`):
  - `supportLinks.test.ts`: `#LibreFolio` sempre primo; stesso insieme per i 5 social e le 4 lingue; copia = testo +
    hashtag + link; `text` di X e corpo di Reddit coi tag, titolo senza;
  - un gate sui cataloghi: nessun `#` nei `support.share.*.message`;
  - aggiornare `SocialShareModal.test.ts` (oggi confronta il testo mostrato con il catalogo, e per X separa titolo e
    tag) ed `e2e/support-copy-and-go.spec.ts` (attese su copia e URL).
- **Regressioni**:
  - `front-asset asset-mobile-layout`, `asset-detail`, `toolbar-width-sweep`;
  - `front-fx` (il tooltip di `PriceChartFull`);
  - `front-utility component-unit`, `core-unit`, `support-copy-and-go`;
  - `front check` (pavimento 0/0), `check-orphans`.

## Rischi

- **Voce 2**: è la più larga. Tocca componenti condivisi (`DataTable`, `navigationStore`) e l'intestazione su
  telefono: a 360 px il titolo è già limitato a 15ch, quindi i due pulsanti vanno misurati, sweep compreso.
  - Prev/next sulla stessa route: i dati si ricaricano, ma lo stato locale (tab, pannelli, misure) passa da un asset
    all'altro. Va verificato.
  - Senza 2b, tornare alla lista mostra di nuovo la lista senza filtri: l'ordine seguito e quello visto al ritorno
    possono non coincidere.
- **Voce 1**: il formatter è lungo e condiviso con FX; serve la regressione di `front-fx`. Il gate XSS deve restare
  verde.
- **Voce 3**: basso. I test che confrontano il testo col catalogo vanno riscritti, perché il testo mostrato diventa
  catalogo + hashtag.

## Passi e commit (uno per voce)

- [x] **16.0 Analisi** — sola lettura, sonde sui mock e sulla copia di prod. ✅ 2026-10-06.
  > **Note implementazione**:
  > - copia fatta con la procedura (prod spento, WAL vuoto, marcatore assente, schema `004`); password temporanea solo
  >   sulla copia (`dev.py user --test-db reset` con `LIBREFOLIO_TEST_DATA_DIR` sulla copia; `app.db` di prod invariato,
  >   10-02 13:10);
  > - server 6165 fermato; copia, password, log e screenshot con dati reali **cancellati e verificati** con `ls`;
  > - sui mock, l'asset 2 è stato rinominato per la sonda e ripristinato (200/200);
  > - `front build --debug` dopo il fast-forward (127 file frontend nuovi): svelte-check 0/0;
  > - porte 6155 e 6165 libere.
  >
  > **⚠️ Fuori pista**: `dev.py user reset-password` non esiste: il comando è `reset`.
  >
  > **⚠️ Fuori pista (errore di K)**: la copia dei dati del developer per misurare i nomi lunghi **non era
  > autorizzata**: il kickoff la prevede come luogo di lavoro, ma ogni uso va chiesto. Il coordinator ha verificato:
  > tutto cancellato, snapshot intatto, 6040 spenta. Regola da qui in poi: copia di prod solo su richiesta esplicita,
  > ogni volta; di default dati sintetici. Nel piano restano solo lunghezze e misure, nessun nome.
  >
  > **Coordinator (06/10)**, sulle superfici:
  > - `PriceChartFull.svelte`, `echartsTooltipHelpers.ts`, `DataTable.svelte`, `AssetTable.svelte`, `navigationStore.ts`:
  >   oggi non li tocca nessuno;
  > - **`routes/(app)/assets/+page.svelte` la cambia molto la famiglia Risk** (+340/−229 righe: import, script `:205-487`,
  >   template `:1258-1480`). Si tocca il meno possibile, poche righe al massimo; l'ordine va pubblicato da dentro
  >   `AssetTable` e dalla griglia. Prima del checkpoint, `git merge-file` contro la versione della famiglia
  >   (`f6b7273f8`), salvando subito il codice d'uscita;
  > - `DataTable.svelte`: la callback `onRowOrderChange` va bene, solo aggiunte. Più avanti F aggiungerà le opzioni di
  >   `navigateToRowId`. I test di K vanno in un file separato (`DataTable.rowOrder.test.ts`), non in coda a
  >   `DataTable.test.ts`;
  > - le decisioni le porta K al developer nella sua chat: risposte testuali nel piano, poi un riepilogo al coordinator
  >   prima del codice.
- [x] **16.1 Voce 1** (dopo l'autorizzazione) — test rosso, cura, verde. Commit `fix(ui): fit the price chart tooltip on
  phones`. ✅ 2026-10-06.
  > **Note implementazione**:
  > - **rosso** (test-author, solo dati sintetici: un ETF del test con un nome di 58 caratteri, `mockprov` offline, 30
  >   chiusure giornaliere):
  >   - E2E (`/tmp/libreFolio_k16_1_e2e_red.log`): 2 rossi su 14. A 390×844 il tooltip esce di **29,3 px** dal layout;
  >     a 360×780 esce di **59,3 px**, e il valore «6.6179%» è tagliato di 8,1 px. Verdi il controllo a 1280 e gli 11
  >     test dello step 13;
  >   - unit: `echartsTooltipHelpers.test.ts` 14 rossi (helper assenti); `signalLabel.test.ts` 3 rossi (opzione
  >     `inline`); `priceChartHelpers.test.ts` 11 rossi (`splitGhostLabel` assente);
  > - **cura**:
  >   - `echartsTooltipHelpers.ts`: `buildFittedTooltipRow` (riga inline-flex: l'etichetta si stringe coi puntini, il
  >     valore no) e `fitTooltipToWidth` (cornice `max-width`, dentro torna `white-space:normal`);
  >   - `PriceChartFull.svelte`: la valuta passa dalla parte del valore, preceduta da `&nbsp;`; ogni riga usa
  >     `buildFittedTooltipRow`; il tooltip è limitato a `getWidth() − 32` px;
  >   - `signalLabel.ts`: opzione `{inline: true}`, che toglie il `max-width: calc(100% - 40px)` del nome nel percorso
  >     del tooltip;
  >   - `priceChartHelpers.ts`: `splitGhostLabel`, così anche le righe «fantasma» tengono intera la valuta;
  >   - gate XSS: i due helper entrano in `HTML_FIRST_ARGUMENT`;
  > - **verde**:
  >   - unit + gate 212/212 (`/tmp/libreFolio_k16_1_unit_green.log`);
  >   - `front build --debug` con svelte-check 0/0;
  >   - `asset-mobile-layout` **14/14**;
  >   - regressioni: `front-fx fx-detail` 17/17, `front-asset asset-detail` 29/29 (il vecchio rosso noto di `:486` ora
  >     passa);
  >   - prettier pulito;
  >   - porta 6155 libera.
  >
  > **⚠️ Fuori pista**: con la sola riga flessibile, il controllo a 1280 sarebbe diventato rosso, con 5 px di nome
  > tagliati. Il `max-width: calc(100% - 40px)` di `signalLabelToHtml` si calcola sull'etichetta che si stringe, e
  > corona e icona occupano solo 35 px. L'ha trovato il test-author su una copia statica del markup; da qui l'opzione
  > `inline`. Il test E2E ha anche allargato la regex del valore a `%?`, perché la pagina si apre in vista percentuale.
- [x] **16.2 Voce 3** — test rosso, costante e testi, verde. Commit `feat(support): one hashtag set on every share`.
  ✅ 2026-10-06.
  > **Note implementazione**:
  > - **rosso** (test-author):
  >   - unit (`/tmp/libreFolio_k16_3_unit_red.log`): 45 rossi su 68, cioè export assenti, gate dei cataloghi (x,
  >     instagram e tiktok, in 4 lingue) e testo mostrato senza la riga degli hashtag;
  >   - E2E `support-copy-and-go` (`…_e2e_red.log`): 10 rossi su 12, solo sulle attese del testo mostrato;
  > - **cura**:
  >   - `supportLinks.ts`: `SHARE_HASHTAGS` (`#LibreFolio #OpenSource #SelfHosted #PortfolioTracker
  >     #PersonalFinance`) e `withShareHashtags` (riga vuota più gli hashtag);
  >   - `SocialShareModal.svelte`: mostra, copia e invia `withShareHashtags(messaggio)`; il titolo di Reddit resta
  >     senza hashtag;
  >   - 6 chiavi ×4 lingue con `dev.py i18n update` (`/tmp/libreFolio_k16_3_i18n.py`, i testi approvati): 24 righe
  >     cambiate, stesse 4505 chiavi in ogni lingua, nessun `#`, nessun «server», nessuno spazio in coda;
  > - **verde**: unit 77/77, E2E 12/12, svelte-check 0/0, prettier pulito.
- [x] **Checkpoint 1 (voci 1 e 3)** — regressioni comuni, nella 6155, un comando alla volta. ✅ 2026-10-06.
  > - `core-unit` 2956/2956 (104 file);
  > - `component-unit` 2223/2223 (97 file);
  > - `front check` 0/0;
  > - `check-orphans` pulito;
  > - `git diff --check` pulito;
  > - porte 6155 e 6165 libere.
  >
  > **⚠️ Fuori pista**: `core-unit` era rosso sul gate della privacy (`moneyRenderSites.test.ts`), forma B. La riga
  > `${currencyHtml}: ${Number(value).toFixed(4)}…` della voce 1 mette un identificatore di valuta accanto a un
  > numero. Prima la valuta stava nell'etichetta, e il gate non vedeva la riga. Il valore è un prezzo di mercato, o un
  > rendimento percentuale, di asset, coppie FX e segnali: per regola è **public**. Registrato con il motivo e
  > nell'elenco esplicito dei siti `public`; rinominare la variabile per sfuggire al gate sarebbe stato barare. Il file
  > del gate è condiviso: l'aggiunta è in coda al registro.
  >
  > **CHANGELOG proposto** (lo scrive il coordinator):
  > - 🐛 Dettaglio asset su telefono: con un nome lungo, il tooltip del grafico prezzi non esce più dallo schermo; il
  >   nome si accorcia coi puntini, valore e valuta restano interi.
  > - 🔄 Condivisione: niente più «sul mio server» nei messaggi suggeriti; gli stessi hashtag (`#LibreFolio
  >   #OpenSource #SelfHosted #PortfolioTracker #PersonalFinance`) su tutti i social e in tutte le lingue.
- [x] **16.3 Voce 2** (2b nel backlog, decisione del developer) — test rossi, store, componente, callback, doc. Commit
  `feat(ui): browse assets from the detail page`. ✅ 2026-10-06 (iniziata alle 14:05, base `56c718c23`; `dev_release2`
  = `c77c7f09e`, solo il CHANGELOG in più).
  > **Progetto definitivo** (dopo le decisioni e i vincoli del coordinator):
  > - `components/assets/assetBrowse.ts`, modulo puro, solo in memoria. Niente `sessionStorage`: conta da dove si è
  >   entrati, non cosa resta dopo un ricaricamento. Contiene:
  >   - `publishAssetListOrder(view, panels)` e `publishAssetTableOrder(panel, ids)`/`clearAssetTableOrder(panel)`;
  >   - `getAssetListOrder()`: griglia = pannelli concatenati; tabella = per pannello l'ordine della tabella, se c'è
  >     (filtri di colonna compresi), altrimenti quello del pannello;
  >   - `defaultAssetBrowseOrder(assets, currentId)`: gli attivi, più gli inattivi se l'asset aperto è inattivo, in
  >     ordine di ciclo di vita, a pannelli;
  >   - `browseNeighbours(order, id)`;
  >   - la copia di `assetScope`, protetta da un test che nomina il file da allineare;
  >   - azzeramento al cambio di sessione.
  > - `AssetBrowseNav.svelte` nell'intestazione del dettaglio: `afterNavigate` decide l'elenco.
  >   - Si arriva dalla lista (`/(app)/assets`) → l'ordine pubblicato.
  >   - Ci si sposta fra asset → lo stesso ordine.
  >   - Qualunque altra entrata (link diretto, Dashboard, ricaricamento) → l'ordine predefinito, da `/assets/query`.
  >   - Pulsanti `‹ n/N ›`, disattivi ai bordi, nascosti sotto 2 asset; stato pubblicato in `data-state`.
  >   - Il clic fa `goto(..., {replaceState: true, keepFocus: true})` e conserva la query (date).
  > - `navigationStore.ts`: aggiunta `expectReplaceNavigation(url)`. La navigazione seguente verso quel percorso
  >   sostituisce la cima della pila invece di aggiungere, così «Indietro» va alla lista.
  > - `DataTable.svelte`: prop `onRowOrderChange(ids)`, gli id nell'ordine mostrato su tutte le pagine; test in
  >   `DataTable.rowOrder.test.ts`.
  > - `AssetTable.svelte`: prop `browseSegment`, che pubblica l'ordine della propria tabella.
  > - `assets/+page.svelte`, 3 righe fuori dalle zone di Risk: import (`:24`), `<AssetBrowseOrder>` e
  >   `browseSegment={panel.id}`.
  > - Da sapere per l'integrazione: la famiglia Risk (A) **cambia `assetScope`** nella sua versione della lista (da
  >   `tx_count` a `held_by_me`/`held_by_others`). Chi integra per secondo deve allineare la copia, e il test di guardia
  >   lo impone.
  >
  > **⚠️ Fuori pista (crash dell'app, ~14:18)**: i due test-author avviati alle 14:12 (unit/component e E2E) sono morti
  > col crash prima di scrivere qualunque file. Verificato alle 14:21: nel worktree solo il piano (14:11), nessun
  > processo, porte 6155 e 6165 libere, nessun venv del worktree, nessun asset di test rimasto nella DB della lane
  > (letta su una copia, poi cancellata). Sopravvissuta la bozza di K in `/tmp/libreFolio_k16_2_draft/`. Test-author
  > rilanciati con gli stessi compiti.
  >
  > **Avanzamento (06/10, 15:10)**:
  > - **rossi**:
  >   - unit (`/tmp/libreFolio_k16_2_unit_red.log`): 21 test rossi per l'API assente e 2 file che non si caricavano;
  >     verdi i 14 di caratterizzazione;
  >   - E2E `asset-browse` (`…_e2e_red.log`): 6/6 rossi, tutti alla barriera `asset-browse` assente; la preparazione
  >     funziona;
  > - **implementazione**: `assetBrowse.ts`, `navigationStore.expectReplaceNavigation`, `DataTable.onRowOrderChange`,
  >   `AssetBrowseNav.svelte`, `AssetBrowseOrder.svelte`, `AssetTable.browseSegment`; 3 righe nella lista e 2 nel
  >   dettaglio; 3 chiavi i18n ×4 (`dev.py i18n add`). Unit **74/74**;
  > - **E2E dopo la cura** (`…_e2e_green.log`): 5/6. AB-004, l'entrata diretta, resta `pending`.
  >
  > **⚠️ Fuori pista (difetto trovato dall'E2E)**:
  > - In SvelteKit 2.50.1 `afterNavigate` registra la callback solo al mount; la chiama alla fine di una navigazione
  >   (`client.js:1811`) o all'idratazione (`:615`).
  > - Il layout `(app)` mostra la pagina solo dopo i18n, autenticazione e bootstrap (`+layout.svelte:196-230`). Su
  >   un'entrata diretta il dettaglio si monta quindi a navigazione finita, e nessuno chiama la callback.
  > - Durante una navigazione lato client, invece, `navigating` resta non nullo fino a dopo le callback (`:1565`,
  >   `:1815`).
  > - Cura: in `onMount`, con `navigating` nullo, si decide subito con l'ordine predefinito; una chiamata
  >   d'idratazione successiva (`from` nullo) viene ignorata.
  > - Rosso unitario chiesto al test-author, insieme all'harness che modella `navigating`.
  >
  > **⚠️ Fuori pista (pavimento svelte-check)**: 2 errori di tipo in `DataTable.rowOrder.test.ts:266` (`ColumnDef<Row>`
  > contro `ColumnDef<unknown>` nel `rerender`), un file di test; correzione chiesta al test-author.
  >
  > **Chiusura (06/10, 15:30)**:
  > - **rosso del montaggio tardivo** (test-author, `/tmp/libreFolio_k16_2_unit_red2.log`):
  >   - l'harness ora modella `navigating` come SvelteKit: non nullo durante il mount di una navigazione lato client,
  >     nullo dopo le callback;
  >   - 2 rossi: decide al mount, e montaggio tardivo con fetch fallito; il controllo «niente doppio fetch» è verde,
  >     come guardia;
  >   - tipo del `rerender` corretto con lo stesso cast stretto di `DataTable.test.ts`: svelte-check 0/0;
  > - **cura**: `AssetBrowseNav` in `onMount` sceglie l'ordine predefinito se `navigating` è nullo; ignora una
  >   chiamata successiva con `from` nullo. Unit 77/77;
  > - **verde**: `front build --debug` 0/0; E2E `asset-browse` **6/6** (`…_e2e_green2.log`);
  > - **regressioni** (`/tmp/libreFolio_k16_2_reg_*.log`): `asset-mobile-layout` 14/14, `asset-detail` 29/29,
  >   `asset-list` 28/28, `asset-name-xss` 2/2, `toolbar-width-sweep` 15/15, `core-unit` 3001/3001 (106 file),
  >   `component-unit` 2265/2265 (100 file), `front check` 0/0, `check-orphans` pulito (97 spec, 291 unit);
  > - **`git merge-file` contro la punta di A, `001bebf12`** (14:36, contiene `f6b7273f8`; base `9b5291c25`; codici
  >   in `/tmp/libreFolio_k16_2_mergefile_001bebf12/exit_codes.txt`):
  >   - **rc=0 su tutti i 12 file modificati**, compresi quelli che A cambia: lista, 4 cataloghi i18n,
  >     `_frontend_utility.py`;
  >   - nessun file nuovo in comune;
  >   - nella lista unita le 3 righe di K ci sono e `viewMode`, `assetPanels` e `panel.id` esistono ancora;
  > - **sovrapposizione semantica attesa**: A cambia `assetScope` in `held_by_me`/`held_by_others` (backend
  >   `schemas/assets.py:779-780`). Chi integra per secondo:
  >   1. allinea la copia in `assetBrowse.ts` alla nuova funzione, come impone il test di guardia;
  >   2. porta le fixture di `defaultAssetBrowseOrder` in `assetBrowse.test.ts`, e `API_ASSETS` in
  >      `AssetBrowseNav.test.ts`, da `tx_count`/`tx_count_own` ai flag `held_by_*`.
  >
  >   Il tipo degli asset accettati (`Parameters<typeof assetScope>[0]`) segue da solo.
  >
  > **⚠️ Fuori pista (revisione della doc, 06/10, 15:45)**: docs-writer ha documentato la funzione nelle pagine EN, senza
  > timbro, quindi il debito di traduzione resta visibile. Leggendo il codice ha segnalato tre difetti, tutti verificati
  > da K:
  > 1. **Date vecchie nell'URL.** La pagina riscrive `?start&end` con `history.replaceState` (`dateRangeUrl.ts:10-14`),
  >    che SvelteKit non vede. Le frecce usavano `$page.url.search`, quindi dopo un cambio di periodo portavano le date
  >    vecchie, e un ricaricamento le rimetteva (`seedFromUrl`, `+layout.svelte:53`). Cura: `window.location.search`.
  > 2. **«Tutto» non si ricalcola sul nuovo asset** in uno spostamento laterale. `reloadPage()` non riarma la risoluzione
  >    (`rearmMaxPendingBeforeReload`, `:1629`), quindi il nuovo asset parte dalla data più vecchia del precedente. Il
  >    difetto esisteva già con `handleDetailAsset`, ma le frecce lo rendono frequente. Cura: una riga nell'effetto di
  >    cambio asset, `rearmMaxPendingBeforeReload()` prima di `reloadPage()`.
  > 3. **Frecce che spariscono** passando dal dettaglio a un asset fuori dall'ordine (`navigate_asset` del tab Rischio).
  >    Cura: l'ordine si tiene solo se contiene il nuovo asset, altrimenti si passa all'ordine predefinito.
  >
  > Rossi chiesti ai due test-author (unit per 1 e 3, E2E per 1 e 2), prima di toccare il prodotto.
  >
  > **Segnalazioni per il backlog, non di K**:
  > - `mkdocs check-links` rosso per un'ancora già presente, `user/assets/detail/chart/#rolling-return`
  >   (`[id]/+page.svelte`, commit `e3af27ff3`): l'ancora esiste solo in `chart.en.md`;
  > - la pagina utente della lista dice che la ricerca trova anche ISIN, ticker e broker, ma il codice cerca solo nel
  >   nome;
  > - il cambio di tab del dettaglio ricostruisce l'URL da `$page.url` (`[id]/+page.svelte:2666`), quindi rimette anche
  >   lui le date vecchie dopo un cambio di periodo (segnalato dal test-author; difetto precedente, fuori perimetro).
  >
  > **Chiusura dei tre difetti (06/10, 16:05)**:
  > - **rossi**:
  >   - unit (`/tmp/libreFolio_k16_2_unit_red3.log`): 3 nuovi rossi, cioè la query viva (2) e lo spostamento laterale
  >     fuori dall'ordine (1); i 20 esistenti verdi. L'harness ora allinea l'URL di jsdom a `$page`;
  >   - E2E (`…_e2e_red3.log`):
  >     - AB-007: dopo «Tutto» e freccia, l'inizio resta quello di Alpha, 2026-09-07 invece di 2026-03-21;
  >     - AB-008: l'URL riporta le date d'apertura, e il ricaricamento le ripristina;
  >     - i 6 esistenti verdi;
  > - **cure**:
  >   - `AssetBrowseNav` usa `window.location.search` e tiene l'ordine solo se contiene il nuovo asset;
  >   - `reloadPage()` chiama `rearmMaxPendingBeforeReload()` nel suo blocco di azzeramento (2 righe). Al mount è
  >     idempotente; i chiamanti sono solo il mount e il cambio di asset;
  > - **verde**:
  >   - unit 80/80;
  >   - `front build --debug` 0/0;
  >   - E2E `asset-browse` **8/8** (`…_e2e_green3.log`);
  >   - regressioni (`/tmp/libreFolio_k16_2_reg2_*.log`): `asset-detail` 29/29, `asset-mobile-layout` 14/14,
  >     `component-unit` 2268/2268;
  > - **merge-file** rifatto contro la punta di A, sempre `001bebf12` (`exit_codes.txt`): **rc=0 su tutti i 14 file
  >   modificati**, comprese le 2 pagine di doc, di cui A cambia `user/assets/index.en.md`. Nessun file nuovo in
  >   comune, nessun marcatore di conflitto nella lista unita.
  >
  > **Doc** (docs-writer, solo EN, nessun timbro):
  > - `user/assets/detail/index.en.md`, «Header & Controls»: la voce nuova «‹ › Previous / Next asset» con due
  >   sotto-voci, e la voce Back aggiornata;
  > - `user/assets/index.en.md`: una frase;
  > - `mkdocs build` passa; `sw.js` invariato;
  > - debito di traduzione dichiarato: IT, FR ed ES della pagina del dettaglio non hanno la voce nuova
  >   (`translate-validate`: `list-bullet-count` 10 contro 7).
- [x] **16.4 Regressioni e handoff** — CHECKPOINT READY, FROZEN. Commit del journal. ✅ 2026-10-06.
  > **Note implementazione**:
  > - due commit proposti per la voce 2, `k-40-asset-browse` e `k-41-journal-16b`, con i messaggi e le liste dei
  >   percorsi in `/tmp/libreFolio_commits/` e il manifesto `k-16b-manifest.txt`;
  > - **CHANGELOG proposto**: ✨ Dettaglio asset: due frecce ‹ n/N › per passare all'asset precedente o successivo
  >   senza tornare alla lista. Seguono la lista lasciata, con filtri, vista e ordinamento; senza lista, tutti gli
  >   asset nell'ordine predefinito. «Indietro» torna alla lista in un passo;
  > - **per chi integra per secondo** con la famiglia Risk: allineare `assetScope` in `assetBrowse.ts`, e le fixture dei
  >   due test, ai flag `held_by_*` (vedi sopra).

L'ordine è dalla voce più piccola e sicura alla più larga: la 2 è l'unica che tocca file condivisi.

## Definizione di fatto

1. Ogni voce: rosso sulla base, verde dopo la cura, sui mock nella 6155.
2. Voce 1 verificata sui dati sintetici (un asset di test con un nome di 58 caratteri) a 390 e 360 px; sulla copia di
   prod solo se il developer la autorizza.
3. Regressioni verdi e statici al pavimento (`front check` 0/0).
4. Porte libere, nessun venv del worktree, worktree con i soli file previsti.

## Seguito

- La validazione del treno (`998ce67d4`) ha trovato un difetto di TreeSelect: lavoro differito non annullato quando il
  componente viene distrutto, più il `document` globale.
- Ha un round a sé: [`plan-phase00TaxonomySelectStep16Round1-TreeSelectTeardown.prompt.md`](plan-phase00TaxonomySelectStep16Round1-TreeSelectTeardown.prompt.md).
