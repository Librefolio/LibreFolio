# Piano — N: cambi FX nella Dashboard (sync dal banner, storia completa alla creazione, valute del menu) + V2 segno KPI

> **Seguito**: [step 2 — cache del frontend tra le pagine](plan-phase00FxDashboardSyncStep2PageCache.prompt.md)
> (06/10, analisi).

> Workstream **N** di Release 2. Coordinator: «Release 2 backlog analysis» (`c8328a01-f208-4ade-a352-0486d1f14de2`).
> Questo file è per ora **l'analisi** (sola lettura, nessun codice): l'implementazione parte solo dopo
> l'autorizzazione esplicita del developer, inoltrata dal coordinator.
>
> **Percorso di destinazione**: `LibreFolio_developer_journal/Release_2/Phase_0/28_fxDashboardSync/plan-phase00FxDashboardSync.prompt.md`.
> La sessione è in *plan mode*, che blocca ogni scrittura fuori dalla cartella di sessione (il `mkdir` è stato
> rifiutato), quindi per ora il testo vive in `plan.md` della sessione; il passo 0 lo copia identico nel journal.

| | |
|---|---|
| **Worktree** | `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-symmetrical-spoon` |
| **Branch** | `e-alfy-fx-dashboard-sync` (rinominato via app da `e-alfy-symmetrical-spoon`, 06/10) |
| **Baseline** | HEAD `c77c7f09e168004b4f50740d7736abe56327fe2b` = target `dev_release2`. La worktree era nata su `d9aad0ec9` (`origin/dev_release2`); fast-forward fatto dal developer e confermato dal coordinator il 06/10. Fra i due commit nessun file di questo perimetro cambia (diffstat: solo `SearchSelect.svelte` e i18n fra i file vicini), quindi le righe citate valgono sul target |
| **Lane** | `--test-port 6159 --data-dir /tmp/librefolio-r2-n`; server di review, se approvato, `127.0.0.1:6169`. Preambolo: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py` |
| **Dati** | solo sintetici. Mai porta 6040, mai `--force` sul server, mai copie di prod |
| **Bootstrap** | `frontend/node_modules` **assente** (verificato) → `npm ci` (pre-approvato) al passo 0. `.env` assente: atteso, non si copia. `graphify-out/graph.json` e `.graphify_python` assenti: atteso, wiki letto pagina per pagina |
| **Da non toccare** | `backend/app/services/provider_registry.py` (L ci sta lavorando) |

---

## Riepilogo per il developer (IT)

**Cosa non va (verificato sul codice):**

1. **Il «Sincronizza» del banner scarica il periodo della pagina** (3M), non le date che mancano. Le date mancanti
   (2022-11-03…2023-06-27) sono tutte *prima del primo tasso salvato* della coppia: un tasso «manca» solo se non ce
   n'è nessuno prima di quella data, perché la conversione usa l'ultimo tasso disponibile senza limiti. I 38 punti
   del toast erano tassi dei 3 mesi visibili, che non c'entravano.
2. **Il buco nasce alla creazione**: il modal «Aggiungi coppia» scarica solo il periodo della pagina che lo apre
   (dalla PAC gli ultimi 7 giorni; se il periodo è vuoto, niente).
3. **GBP nel menu**: lo store mette nel menu anche le valute *di mezzo* delle catene. La catena salva solo il tasso
   della coppia finale, quindi GBP non è convertibile.
4. **V2 «+91,31 € (+-16.36%)»**: il «+» segue l'importo, il numero ha già il suo segno. Con un P&L totale negativo
   esce il doppio segno, o un segno sbagliato. Lo stesso difetto c'è nella card Rendimenti.

**Precedenti asset trovati:** creazione = `start: 'resume'`, che per un asset nuovo vuol dire tutta la storia del
provider (`AssetModal.svelte:1449-1461`); margine di una settimana prima e dopo = `buildComparisonSyncRange`
(`loadComparisonData.ts:40`, `:52-73`), usato dal Sincronizza del dettaglio asset anche per le coppie FX.

**Decisioni da prendere (in grassetto la mia raccomandazione):**

- **D1, «tutta la storia»**: **`start: 'min'` fino a oggi**, cioè tutto quello che il provider pubblica (come un
  asset nuovo). Nessuna modifica al backend.
- **D2, chiamanti**: **la regola sta nel servizio di creazione e il modal perde `dateStart/dateEnd`**. Vanno
  aggiornati i 5 chiamanti, fra cui la PAC (area D), che oggi promette «gli ultimi {days} giorni» nel testo d'aiuto.
- **D3, margine**: **nel frontend, dalle date che l'issue porta già, con la stessa regola dell'asset estratta in un
  helper comune**. Un solo intervallo, dalla prima data meno 7 giorni all'ultima più 7, con tetto a oggi.
- **D4, weekend e festivi**: con la settimana prima si risolvono da soli. Il banner resta solo per date anteriori
  alla storia del provider: **toast di avviso se, dopo il sync, l'issue è ancora lì** (1 chiave i18n nuova).
- **D6, rischio**: dopo il sync col margine, i giorni fra «ultima data + 7» e il primo tasso già salvato usano in
  silenzio un tasso vecchio, perché nessun banner lo segnala. **Accettarlo**: le coppie nuove non avranno più buchi,
  quelle vecchie si riparano una volta con FX → MAX → Sincronizza tutto. Alternativa: il Sincronizza del banner
  arriva fino a oggi.
- **D7, V2, percentuale su base negativa**:
  - **A, rispetto al valore assoluto del P&L di ieri**: il segno segue sempre l'importo. «+91,31 € (+16,36%)»
    vuol dire che la perdita si è ridotta del 16%.
  - B: nasconderla se la base è ≤ 0.
  - C: base = capitale versato.
  - Card Rendimenti: **stesso segno dal valore, nascosta se il NAV di ieri è ≤ 0**.

**Permessi da chiedere al coordinator:**

- `FxStep.svelte` + chiave i18n PAC (area D);
- `fx/+page.svelte`, `fx/[pair]/+page.svelte`, `assets/[id]/+page.svelte` (lì lavora K, step 16);
- `fxCreationSync.ts`, `loadComparisonData.ts`;
- il catalogo test, per i nuovi file.

---

## Decisioni prese e permessi (06/10, inoltrati dal coordinator)

- **D1–D5 e D8**: si applicano le raccomandazioni («Approvo le raccomandazioni (Consigliato)»). Il menu valute
  mostra solo i capi delle rotte.
- **D6 = A**: solo ±7 giorni. «per sincronizzazioni monche pre fix, saranno gli utenti a fare in sinc max». La nota
  nel CHANGELOG la scrive il coordinator: io propongo il testo.
- **D7, su tutte e due le card**:
  - percentuale = variazione / |valore precedente| × 100;
  - segno e colore dalla direzione: + e verde se sale, − e rosso se scende;
  - mai «+-»;
  - nascosta solo se il valore precedente è esattamente 0.
  - La card 2 **non** si nasconde con un NAV negativo: qui la mia raccomandazione è stata superata. Le parole del
    developer: «deve dire quanto è variata in percentuale day-by-day, se è aumentata è + e verde, se è diminuita - e
    rossa».
- **Permessi concessi**:
  - file: `fxCreationSync.ts`, `loadComparisonData.ts` (delega all'helper), il nuovo `utils/sync/syncRange.ts`,
    `dashboard/+page.svelte`, `fxRoutesStore.ts`, `FxPairAddModal.svelte`, `KpiSection.svelte` e i loro test;
  - chiamanti: `fx/+page.svelte:1221`, `fx/[pair]/+page.svelte:1635`, `assets/[id]/+page.svelte:3565` (**una
    riga sola**: K ha modifiche in sospeso a `:37` e `:2735`), `FxStep.svelte:197-200` e `:354-363` (D è
    informato);
  - runner `_frontend_utility.py`: **solo le 2 righe nuove**, ad almeno 4 righe da quelle in sospeso di K (`:27`,
    `:87`, `:191`, `:203`) e della famiglia Risk (`:72`, `:77-81`, `:179`, `:224`). Scelgo `:40-41`, subito dopo
    `syncToastHelpers.test.ts`;
  - i18n: 1 chiave nuova con `dev.py i18n add`; `tools.pacAllocator.planner.fx.pairAbsentHelp` con
    `dev.py i18n update`;
  - doc solo in inglese, con docs-writer, nessuno stamp.
- `CurrencySearchSelect.svelte` non è fra i permessi, quindi il commento del prop resta com'è. «Reachable via a
  configured FX route» rimane vero anche con i soli capi.

---

## 1. Stato attuale verificato (HEAD `c77c7f09e`)

### 1.1 Il «Sincronizza» del banner usa il periodo della pagina

- `frontend/src/routes/(app)/dashboard/+page.svelte:334-361`: ramo `sync_fx_pair` di `handleBannerAction` (`:324`).
  Fa `POST /fx/currencies/sync` con `start: dateRangeCtl.start, end: dateRangeCtl.end` (`:342-346`). L'analisi del
  coordinator è confermata.
- L'issue ha già il suo intervallo: `backend/app/services/portfolio_engine.py:2099-2121`.
  - `MISSING_FX_RATES` per le coppie configurate con un provider reale.
  - `message_params = {count, date_from, date_to, dates_count}`, dove `date_from` e `date_to` sono il minimo e il
    massimo sull'unione delle date di tutte le coppie dell'issue.
  - `cta_action="sync_fx_pair"`, `affected_fx_pairs`.
  - Il contratto è già testato: `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_data_quality_report.py:233-237`.
  - Le coppie MANUAL hanno un'issue a parte, senza date (`:2123-2136`, CTA `navigate_fx`): resta com'è.
- Da dove vengono le date.
  - `backend/app/services/portfolio_service.py:738-802` scorre **tutte** le transazioni fino a `date_to`:
    `_get_transactions(broker_id, date_to=date_to)`, senza `date_from`. Per ogni conversione fallita registra
    `WACMissingPairInfo(pair, [tx.date])` e salta l'importo (`continue`).
  - Poi le conversioni alla data di valutazione: `:935-941`, `:958-965`, `:1045-1052`.
  - Tutto viene fuso a `:1263` e passato a `build_data_quality_report(…)` (`:1264-1274`).
  - Solo `NAV_INCOMPLETE` è ritagliato sul periodo (`portfolio_engine.py:1995-2003`, motivato nel docstring
    `:1983-1994`). `MISSING_FX_RATES` no, ed è corretto: quelle conversioni mancanti tolgono importi dai totali
    cumulativi (capitale investito, P&L totale), che la dashboard mostra anche su 3M («…per completare i totali»).
- Cosa vuol dire «data mancante».
  - `convert_bulk` fa backward-fill **illimitato** (`backend/app/services/fx.py:1240-1247`): una conversione fallisce
    solo se non c'è **nessun** tasso con data ≤ quella richiesta.
  - Le 9 date del developer sono quindi tutte **prima del primo tasso salvato** di EUR-USD.
  - Un sync sui 3M visibili scrive solo dentro quel periodo (i «38» del toast) e non può toccarle: il banner resta.
- Feedback fuorviante.
  - `:347-352`: il toast somma `points_changed ?? points_fetched` di tutte le coppie («38 pts» in verde) anche se
    nessuna data mancante è stata coperta.
  - `:357`: l'errore è un testo inglese fisso, «FX sync failed:».
- Timeout: quello di default è 30 s (`frontend/src/lib/api/zodios-client.ts:30`). `FxSyncModal.svelte:39-46` e
  `PageSyncModal.svelte:120` usano 120 s per lo stesso endpoint.
- Il backend rifiuta `end` nel futuro con un 400 (`backend/app/api/v1/fx.py:201-204`, `date.today()` del server).

### 1.2 Il buco nasce alla creazione della coppia

- `frontend/src/lib/components/fx/FxPairAddModal.svelte`:
  - props `dateStart/dateEnd` a `:44-47` («Current date range for auto-sync after creation»), letti a `:71`,
    catturati a `:237-238`;
  - contesto a `:312-325`: `autoSyncStarted: !editing && hasRealProvider && !!start && !!end` (`:314`), con
    `pairs` = coppia + intermedie create (`:315`);
  - poi `finishFxPairCreation` (`:341`, `:360`).
- `frontend/src/lib/services/fxCreationSync.ts:82-201`:
  - nessun sync in modifica, con solo MANUAL **o con il periodo vuoto** (`:84`, `:115-133`);
  - altrimenti `POST /fx/currencies/sync {pairs, start, end}` (`:138`, timeout di default);
  - `start/end` finiscono nel dettaglio di completamento (`:162`) e nell'evento `fx.pair.creation-sync-completed`
    (`:196-200`);
  - l'unico listener di produzione, `fx/[pair]/+page.svelte:616`, non legge `start/end`.
- I 5 chiamanti:

| Chiamante | Riga | Periodo passato |
|---|---|---|
| Dashboard | `dashboard/+page.svelte:894` | `dateRangeCtl.start/end` (es. 3M) — il caso del developer |
| Lista FX | `fx/+page.svelte:1221` | periodo della pagina |
| Dettaglio FX | `fx/[pair]/+page.svelte:1635` | `editMode` → **nessun** sync. È una scelta: R6/C2R2, «user controls sync timing». Non cambia |
| Dettaglio asset | `assets/[id]/+page.svelte:3565` | periodo della pagina |
| PAC | `features/tools/pac-allocator/planner/steps/FxStep.svelte:354-363` | ultimi 7 giorni (`SYNC_WINDOW_DAYS = 7`, `:118`, `:154-158`) |

- La PAC lo promette all'utente: `tools.pacAllocator.planner.fx.pairAbsentHelp` (`en.json:4299`, `it.json:4299`),
  «…LibreFolio scarica poi i tassi degli ultimi {days} giorni…»; testo di default in `FxStep.svelte:197-200`.
- Test che fissano il vecchio contratto:
  - `FxPairAddModal.test.ts:82, 270, 297, 344, 349-350, 408, 424, 446, 507, 513`;
  - `fxCreationSync.test.ts:40, 470-482` (caso «missing date»), `:486-514`;
  - E2E `fx/fx-add-pair.spec.ts:25, 91-95, 233-234`.
- Doc utente: `mkdocs_src/docs/user/fx/add-pair.en.md:10-15` («…and the FX page has a valid date range
  selected… no date range is set, no sync runs»).

### 1.3 GBP nel menu valute

- `frontend/src/lib/stores/reference/fxRoutesStore.ts:67-75`: per ogni rotta aggiunge `base`, `quote` **e** i
  `from/to` di ogni `chain_steps` (`:71-74`). Il commento del modulo (`:4-8`, `:15-17`) chiama tutto questo
  «raggiungibile».
- Consumo:
  - `CurrencySearchSelect.svelte:96-100`: con `configuredOnly` tiene `getConfiguredCurrencySet()` + `value` +
    `defaultCurrency` (doc del prop a `:50-53`);
  - lo usano la dashboard (`dashboard/+page.svelte:675-690`) e `AssetPriceSummary.svelte:134`, il menu
    «Converti in» del dettaglio asset. Lì la valuta nativa resta raggiungibile con la scorciatoia `originalCurrency`.
- La valuta di mezzo non si può convertire. Il sync di una catena salva **solo** il tasso composto della coppia
  (`fx.py:1102-1148`: insert `FxRate` su `route.base/route.quote`); i tassi delle tratte restano in memoria.
- GBP diventa convertibile solo se esiste una coppia GBP configurata, per esempio con l'opzione «crea anche le coppie
  intermedie» del modal (`FxPairAddModal.svelte:88`, `:286-309`). In quel caso GBP è un capo di quella rotta e resta
  nel menu: è la condizione posta dal developer.
- Doc sviluppatore: `mkdocs_src/docs/developer/frontend/components/core-ui/select.md:233-234` («reachable through a
  configured FX route»).
- `configuredCurrencies` (`:28`, `:78`) viene scritto e mai letto: è stato morto, fuori perimetro, lo lascio.

### 1.4 V2 — «+91,31 € (+-16.36%)»

- `frontend/src/lib/components/dashboard/KpiSection.svelte`:
  - `:75-80`: `pnlDeltaDay` = P&L totale dell'ultimo punto della history meno quello del penultimo;
  - `:114-119`: `pnlDeltaDayVsPrevTotalPct` = `pnlDeltaDay / prevTotalPnl × 100`, come **stringa** `toFixed(2)`;
    nascosta se |base| < 0,01;
  - `:256-262`: resa `({pnlDeltaDay >= 0 ? '+' : ''}{pct}%)`.
  - Con base −558,10 € e delta +91,31 € la percentuale vale −16,36 e la resa è «(+-16.36%)».
  - Con base negativa e delta negativo esce «(16.36%)», positiva senza segno accanto a un importo rosso: segno
    sbagliato anche senza doppio segno.
- Card 2 «Rendimenti», `:81-86`: `pnlDeltaDayPct` = delta / NAV di ieri; resa a `:309-311` con lo stesso prefisso.
  Doppio segno se il NAV di ieri è negativo, caso raro (cassa negativa).
- `KpiSection` è usato anche dal dettaglio broker (`brokers/[id]/+page.svelte:592`): la correzione vale anche lì.
- Il formattatore giusto esiste già: `formatPercent()` (`frontend/src/lib/utils/core/formatPercent.ts:63`). Prende il
  segno dal valore e ha la guardia sul −0.
- Doc: `mkdocs_src/docs/user/dashboard/kpi-cards.en.md:29-38` («a share of yesterday's Total P&L»); card 2 a `:74-80`.
- Test: `KpiSection.test.ts` (componente, jsdom) copre solo F5.
- Fuori perimetro, solo segnalato: le percentuali delle KPI hanno sempre il punto decimale (`toFixed`), mentre gli
  importi seguono la lingua («91,31 €» accanto a «16.36%»).

---

## 2. Precedenti asset (richiesti dal developer, «come per asset»)

| Regola | Precedente | Dettaglio |
|---|---|---|
| **Creazione = tutta la storia** | `frontend/src/lib/components/assets/AssetModal.svelte:1449-1461` | Dopo la creazione con un provider reale parte un sync «fire-and-forget» `date_range {start: 'resume', end: oggi}`. `'resume'` vuol dire «dal giorno dopo l'ultimo prezzo salvato, o tutta la storia del provider (`'min'`) se non ce n'è» (schema `backend/app/schemas/refresh.py:65-76`, risoluzione `backend/app/services/asset_sources/refresh.py:81-84`). Per un asset nuovo equivale a `'min'`. Al cambio provider vale la stessa regola: `AssetModal.svelte:1626-1642` |
| FX accetta già «tutta la storia» | `backend/app/schemas/refresh.py:63`, `:167` | `SyncStartDate = date \| 'min'`; il sync FX volutamente non ha `'resume'` (`:73-74`). I provider traducono `'min'` in `FX_HISTORY_MIN_FALLBACK = 1900-01-01` (`fx.py:37`; `ecb.py:176`, `fed.py:169`, `boe.py:148`, `snb.py:235`) e restituiscono quello che hanno. Le pagine FX lo mandano già col preset MAX (`fx/+page.svelte:95`, `fx/[pair]/+page.svelte:155`) |
| **Margine di una settimana prima e dopo** | `frontend/src/lib/charts/loadComparisonData.ts:40` e `:52-73` | `COMPARISON_SYNC_PADDING_DAYS = 7`. `buildComparisonSyncRange`: inizio − 7 giorni (o `'min'`); fine + 7 giorni con tetto a oggi; inizio mai oltre la fine. La usa il Sincronizza del dettaglio asset (`assets/[id]/+page.svelte:2344`) sia per i prezzi dell'asset sia per le coppie FX che gli servono (`:2365-2376`). Test: `src/lib/charts/__tests__/loadComparisonData.test.ts:46-…` |
| FX nelle transazioni (stessa idea) | `TransactionBulkModal.svelte:1391-1423` | Sync FX del WAC sulle date mancanti ± 7 giorni (`:1408-1410`). `TransactionFormModal.svelte:1237-1266` fa lo stesso **senza** margine: incoerenza preesistente, fuori perimetro, segnalata |

---

## 3. Difetti, derive, mancanze

| # | Tipo | Cosa | Dove |
|---|---|---|---|
| F1 | difetto | Il CTA `sync_fx_pair` ignora l'intervallo dell'issue e scarica il periodo della pagina | `dashboard/+page.svelte:342-346` |
| F2 | difetto | Il toast dice «N pts» anche quando le date mancanti restano; l'errore è un testo inglese fisso | `:347-352`, `:357` |
| F3 | difetto (origine) | La creazione scarica solo il periodo della pagina che apre il modal (7 giorni dalla PAC; niente se il periodo è vuoto) → buco storico | `FxPairAddModal.svelte:237-238,314`; `fxCreationSync.ts:84,115-138` |
| F4 | deriva | Il menu `configuredOnly` include le valute di mezzo delle catene, che non si possono convertire | `fxRoutesStore.ts:71-74` |
| F5 | difetto | Doppio segno o segno incoerente nella percentuale giornaliera (card 1 e card 2) | `KpiSection.svelte:114-119,256-262,81-86,309-311` |
| F6 | mancanza | Timeout di 30 s sui due sync toccati, 120 s negli altri punti | `zodios-client.ts:30` |
| F7 | doc | Quattro pagine descrivono il comportamento di oggi | §5 |

---

## 4. Decisioni aperte — opzioni e raccomandazione

### D1 — Che cosa vuol dire «tutta la storia» per una coppia FX
- **A (raccomandata)**: `start: 'min'`, `end: todayIso()`.
  - È la storia che il provider pubblica: ECB dal 1999, BOE dal 1975… Per una catena, dove tutte le tratte hanno
    dati.
  - Equivale al `'resume'` di un asset nuovo. Nessuna modifica a backend, schema o API.
- B: dalla prima transazione dell'utente meno 7 giorni. Non è «tutto», e i tassi sono globali: servono anche agli
  altri utenti.
- C: aggiungere `'resume'` al sync FX (backend + schema + `api sync`). Su una coppia ricreata lascerebbe il buco
  iniziale; non serve.

### D2 — Dove vive la regola; i props `dateStart/dateEnd`
- **A (raccomandata)**: la regola sta in `fxCreationSync.ts`, l'unico punto che lancia i sync di creazione.
  - `autoSyncStarted` diventa `!editing && hasRealProvider`.
  - Il modal perde `dateStart/dateEnd` e i 5 chiamanti vengono aggiornati. Con le firme di Svelte 5, un prop rimosso
    ma ancora passato è un errore di `svelte-check`.
  - Il testo d'aiuto PAC `pairAbsentHelp` diventa «…scarica la storia dei tassi…», nelle 4 lingue.
  - Servono i permessi per `FxStep.svelte` (area D), `fx/+page.svelte`, `fx/[pair]/+page.svelte` e
    `assets/[id]/+page.svelte`.
- B: i props restano ma in creazione vengono ignorati. Nessun chiamante da toccare, ma l'API dice una cosa falsa.
- C: la PAC resta un'eccezione con i suoi 7 giorni. Le coppie create dalla PAC avrebbero di nuovo il buco:
  sconsigliata.

### D3 — Dove si applica il margine
- **A (raccomandata)**: nel frontend, nel gestore del banner, partendo da `message_params.date_from/date_to`
  dell'issue (contratto backend già testato, §1.1).
  - La regola dell'asset viene estratta in un helper neutro, `frontend/src/lib/utils/sync/syncRange.ts`:
    `SYNC_MARGIN_DAYS = 7` e `padSyncRange()`.
  - Lo stesso file contiene una funzione pura `buildMissingFxRatesSyncRequest(issue, today)`.
  - `buildComparisonSyncRange` si appoggia a `padSyncRange` senza cambiare comportamento: lo garantiscono i suoi
    test.
  - Serve il permesso per `loadComparisonData.ts`.
- A′ (se il permesso non arriva): la dashboard chiama direttamente
  `buildComparisonSyncRange({start: date_from, end: date_to})`. Stessa regola, nome meno chiaro, nessun altro file
  toccato.
- B: il backend calcola i campi strutturati `sync_start/sync_end` e li espone in `DataQualityIssue`. Il contratto è
  più esplicito, ma cambia schema e API (serve `api sync`) su uno schema condiviso con lots e risk.
- Forma (raccomandata): **un solo intervallo sull'unione** (min − 7, max + 7, tetto a oggi), con un solo sync per
  tutte le coppie dell'issue. Copre anche i buchi fra una data e l'altra, mentre una finestra per data (più
  richieste) lascerebbe scoperti gli intervalli in mezzo.

### D4 — Weekend, festivi e banner che resta
- Il fatto: il backward-fill è illimitato. Con la settimana prima, un sabato o un festivo prende il tasso dell'ultimo
  giorno lavorativo e il banner **sparisce**. Resta solo per date **anteriori all'inizio della storia del provider**
  (es. ECB prima del 04/01/1999) o se il provider va in errore.
- **A (raccomandata)**:
  - dopo il sync e il ricaricamento, se la stessa issue è ancora lì, toast di avviso «il provider non ha tassi
    per … tra … e …: inseriscili a mano nella pagina della coppia» (chiave nuova, 4 lingue) e evento
    `fx.rates.synced` con `{origin: 'dashboard-banner', pairs, start, end, stillMissing}`;
  - un toast per coppia con `buildFxSyncToast` (come le pagine FX) al posto della somma «pts»;
  - errore con la chiave esistente `fx.sync.toastFailed`;
  - timeout 120 s.
- B: solo i toast per coppia, nessun controllo dopo il ricaricamento.

### D5 — Un'issue senza date (caso difensivo: oggi il backend le mette sempre)
- **A (raccomandata)**: tutta la storia, da `'min'` a oggi, la stessa regola della creazione.
- B: il periodo della pagina, cioè il comportamento di oggi, che è proprio il bug.

### D6 — Rischio: buco interno dopo il sync col margine
- Il backward-fill è illimitato, quindi i giorni fra `date_to + 7` e il primo tasso già salvato prendono in silenzio
  l'ultimo tasso scaricato, che può essere vecchio di anni.
- Prima del sync quei giorni risultavano «NAV incompleto», ma solo fuori dal periodo visibile. Dopo il sync nessun
  banner lo dice più.
- **A (raccomandata, come deciso dal developer)**: ±7 giorni, e basta.
  - Con D1 le coppie nuove non avranno più buchi.
  - Le coppie create prima si riparano una volta con FX → MAX → Sincronizza tutto: una nota nel CHANGELOG,
    proposta al coordinator.
- B: il Sincronizza del banner arriva fino a oggi invece che a `date_to + 7`. Chiude anche il buco interno in un
  colpo, ma riscarica e riscrive tutta la serie da `date_from − 7`: il provider è considerato la fonte autorevole
  (`mkdocs_src/docs/user/fx/sync.en.md:34`, `:42`).
- C: riconoscere i tassi FX «stantii» come STALE_PRICE fa per i prezzi. È lavoro backend a parte (TODO_FUTURI, del
  coordinator).

### D7 — V2: che cosa mostra la percentuale su una base negativa (card 1)
- **A (raccomandata)**: rispetto a **|P&L totale di ieri|**, così il segno segue sempre l'importo.
  - «+91,31 € (+16,36%)» = la perdita accumulata si è ridotta del 16,36%; con un delta negativo la percentuale è
    negativa.
  - Cambiano una riga di calcolo e una frase di doc. Il significato resta quello di oggi.
- B: la percentuale sparisce quando la base è ≤ 0 e resta solo l'importo. Nessuna ambiguità, ma sparisce proprio nei
  periodi in perdita.
- C: base = capitale versato di ieri (`capital_baseline`, già nei punti della history).
  - «Oggi hai mosso lo 0,9% del capitale»: ben definita e stabile anche quando il P&L è vicino a zero.
  - Cambia però il significato che la percentuale ha dalla v1.1.0, e si avvicina al dato della card 2.
- **Card 2** (delta / NAV di ieri): stesso doppio segno con un NAV negativo. Raccomandazione: segno preso dal valore,
  e percentuale nascosta se il NAV di ieri è ≤ 0, perché un rendimento su un patrimonio ≤ 0 non ha senso.
- In tutti i casi la percentuale diventa un numero (non più una stringa), resa con `formatPercent()`, con
  `data-testid="kpi-pnl-delta-day-pct"` sullo span come appiglio stabile per i test.

### D8 — Appiglio per l'E2E del menu valute
- **A (raccomandata)**: `testId="dashboard-target-currency"` sul `CurrencySearchSelect` della dashboard (è solo un
  attributo), più un E2E con le rotte stubbate.
- B: solo il test unitario dello store.

---

## 5. Superfici esatte

| File | Modifica | Stato |
|---|---|---|
| `frontend/src/routes/(app)/dashboard/+page.svelte` | `:334-361`: intervallo dall'issue ± 7 con fallback, timeout 120 s, toast per coppia, controllo del residuo + evento. `:675-690`: `testId` (D8). `:894`: tolti `dateStart/dateEnd` | nella lista |
| `frontend/src/lib/stores/reference/fxRoutesStore.ts` | `:67-75`: solo `base/quote`; doc `:4-8`, `:15-17` | nella lista |
| `frontend/src/lib/components/ui/select/CurrencySearchSelect.svelte` | solo il commento del prop, `:50-53` | nella lista |
| `frontend/src/lib/components/fx/FxPairAddModal.svelte` | via i props `:44-47`/`:71`; `:237-238`; contesto `:312-325`; intestazione | nella lista |
| `frontend/src/lib/services/fxCreationSync.ts` | regola «tutta la storia» + timeout; `autoSyncStarted` senza periodo | **da confermare** (è il servizio chiamato dal modal) |
| `frontend/src/lib/components/dashboard/KpiSection.svelte` | `:81-86`, `:114-119`, `:256-262`, `:309-311` | assegnato (V2) |
| `frontend/src/lib/utils/sync/syncRange.ts` (nuovo) | `SYNC_MARGIN_DAYS`, `padSyncRange()`, `buildMissingFxRatesSyncRequest()` | nuovo |
| `frontend/src/lib/charts/loadComparisonData.ts` | `buildComparisonSyncRange` delega a `padSyncRange` (D3-A) | **serve permesso** |
| `fx/+page.svelte:1221`, `fx/[pair]/+page.svelte:1635`, `assets/[id]/+page.svelte:3565` | tolti `{dateStart} {dateEnd}` (D2-A) | **serve permesso** |
| `features/tools/pac-allocator/planner/steps/FxStep.svelte:354-363`, `:197-200` | tolti i props; testo di default «scarica la storia» | **serve permesso** (area D) |
| i18n `en/it/fr/es.json` | 1 chiave nuova (D4-A) con `dev.py i18n add`; `tools.pacAllocator.planner.fx.pairAbsentHelp` con `dev.py i18n update` (D2-A) | condiviso, dichiarato qui |
| `scripts/test_runner/_frontend_utility.py` | registrare `fxRoutesStore.test.ts` e `utils/sync/__tests__/syncRange.test.ts` in `core-unit` | condiviso, serve grant |
| Test esistenti: `fxCreationSync.test.ts`, `FxPairAddModal.test.ts`, `KpiSection.test.ts`, `e2e/portfolio/data-quality-banners.spec.ts`, `e2e/fx/fx-add-pair.spec.ts`, `e2e/portfolio/dashboard.spec.ts` | aggiornamenti ed estensioni (§10) | test-author |
| Doc EN | `user/fx/add-pair.en.md:10-15`; `user/dashboard/index.en.md:46` e `:66-74`; `user/dashboard/kpi-cards.en.md:29-38` e `:74-80`; `developer/frontend/components/core-ui/select.md:233-234` | docs-writer |
| Backend | **nessuna modifica prevista** (con D3-B servirebbe). `provider_registry.py` non si tocca | — |
| API | nessun cambiamento → niente `api sync` | — |

---

## 6. Previsione conflitti

- `assets/[id]/+page.svelte`: K, step 16, aggiunge `AssetBrowseNav` nell'intestazione. Io tocco solo la riga 3565:
  un conflitto testuale è improbabile, ma il file ha due writer.
- `FxStep.svelte` e la chiave i18n della PAC: area D. Se D sta toccando lo stesso blocco, conviene integrare N prima
  o dopo D, non in parallelo.
- Cataloghi i18n: writer condiviso, ma su chiavi diverse da quelle degli altri rami.
- `select.md`: L l'ha appena toccato (`e09ec9b47`, già nel target). Io cambio solo `:233-234`.
- `_frontend_utility.py`: catalogo condiviso, solo righe nuove nelle liste.
- `loadComparisonData.ts`: nessun ramo noto, da confermare.
- Sovrapposizioni semantiche: `FxPairSyncCompleteDetail.start/end` lo leggono solo i test. Chi aggiunge un nuovo
  chiamante di `FxPairAddModal` su un altro ramo passerà ancora `dateStart`, e `svelte-check` lo segnalerà dopo il
  merge.
- `CHANGELOG.md` è del coordinator: proporrò la voce (3 fix FX + V2 + la nota di riparazione per le coppie vecchie).

---

## 7. Complessità e rischi

**Complessità: medio-bassa.**

- 6 file di produzione nel perimetro + 1 helper nuovo; 4 chiamanti con una riga ciascuno; nessuna modifica backend.
- 3 file di test aggiornati, 2 test unitari nuovi, 3 spec E2E estese.
- 4 pagine di doc in inglese; 1 chiave i18n nuova e 1 aggiornata.

| # | Rischio | Mitigazione |
|---|---|---|
| R1 | Un sync completo, soprattutto di una catena con BOE (lenta, con protezione anti-bot), può superare i 30 s: l'utente vede un errore di trasporto mentre il backend completa | timeout 120 s, come `FxSyncModal`; la creazione resta in background col toast finale |
| R2 | Volume: 7–14 mila righe per coppia con i provider reali. MOCKFX su `'min'` genera un punto per ogni giorno dal 1900 (~46 mila righe, `mockfx.py:76-84`) | Gli E2E intercettano il sync (`fx-add-pair.spec.ts:91`); nessuno spec crea oggi coppie MOCKFX dal modal con il sync reale. La review manuale usa solo il DB della lane |
| R3 | Il sync completo riscrive l'intera serie della coppia (il provider è la fonte autorevole), quindi anche eventuali modifiche manuali di una coppia ricreata | Comportamento documentato (`sync.en.md:42`); su una coppia nuova di solito non c'è niente da riscrivere |
| R4 | Buco interno dopo il sync col margine (D6) | Decisione D6 |
| R5 | `end = todayIso()` (data del browser) contro `date.today()` del server: un utente a est del server, a cavallo della mezzanotte, prende un 400 | Rischio preesistente per tutti i chiamanti che usano `todayIso()`, fuori perimetro, segnalato |
| R6 | Conflitti fra file (§6) | Permessi espliciti; modifiche di una riga |
| R7 | V2 cambia un dato visibile e la doc in 4 lingue (debito di traduzione) | Decisione D7; nessuno stamp senza l'ok del coordinator |

---

## 8. Passi ordinati (dopo l'autorizzazione)

0. ✅ (06/10) **Avvio.**
   - Copiare questo piano nel percorso del journal.
   - Verificare che `frontend/node_modules` manchi ancora, poi `cd frontend && npm ci` (pre-approvato).
   - Ricontrollare HEAD = baseline.

   > **Note implementazione**:
   > - piano approvato nell'app (uscita dal plan mode) il 06/10; si applicano le raccomandazioni D1–D8;
   > - HEAD `c77c7f09e` riverificato; `node_modules` assente, quindi `npm ci`: 433 pacchetti, log in
   >   `/tmp/libreFolio_n_npmci.log`;
   > - copiato questo piano nel journal.
   >
   > **⚠️ Fuori pista**:
   > - il plan mode aveva rifiutato la scrittura nel journal, per cui il piano è nato in `plan.md` della sessione;
   > - i permessi chiesti al coordinator (`fxCreationSync.ts`, `loadComparisonData.ts`, gli altri 4 chiamanti
   >   compresa la PAC, il catalogo dei test) sono ancora in attesa: quelle parti restano ferme finché non arrivano.
1. ✅ (06/10) **Test rossi** (test-author, §10).
   - Prima i test unitari e di componente, poi gli E2E.
   - Registrare i file nuovi nel catalogo (con grant).
   - Eseguirli e verificare che falliscano per il motivo giusto.

   > **Note implementazione**: test-author, sotto-agente `n-red-tests`; nessun codice di produzione toccato.
   >
   > Nuovi file:
   > - `fxRoutesStore.test.ts`: 1 rosso (la catena dà {EUR,USD,GBP}), 4 verdi di regressione;
   > - `syncRange.test.ts`: 26 test, rossi per «Cannot find module».
   >
   > File aggiornati:
   > - `fxCreationSync.test.ts`: 34 rossi, 3 verdi;
   > - `FxPairAddModal.test.ts`: 8 rossi, 10 verdi;
   > - `KpiSection.test.ts`: 9 rossi, 3 verdi (F5);
   > - `fx-add-pair.spec.ts`: 5 rossi, cioè le varianti provider (il corpo del sync è il periodo della pagina);
   > - `data-quality-banners.spec.ts`: 3 rossi, 15 verdi;
   > - `dashboard.spec.ts`: 2 rossi (testid assente), 24 verdi.
   >
   > `loadComparisonData.test.ts` non è toccato (33 verdi). Catalogo: 2 righe a `_frontend_utility.py:40-41`. Log in
   > `/tmp/libreFolio_n_red_*.log`.
   >
   > **⚠️ Fuori pista**:
   > - `frontend/src/lib/api/generated.ts` (gitignored) mancava nella worktree, e i test di componente non si
   >   caricavano nemmeno prima delle modifiche. L'ha generato la build del frontend fatta dal runner E2E.
   > - Il CTA del banner ha un `data-testid` legato al solo codice: due righe `MISSING_FX_RATES` (gruppi reale e
   >   manuale) condividono `data-quality-cta-MISSING_FX_RATES` e `busyCode`. È un difetto preesistente di
   >   `DataQualityBanner.svelte`, fuori dai permessi: lo segnalo, non lo correggo.
   > - Caso «giorno piatto» aggiunto da test-author: `0.00%` con `data-direction="flat"`, coerente con «nascosta
   >   solo se la base è 0».
2. ✅ (06/10) **F4**: `fxRoutesStore.ts` prende solo i capi (base/quote); aggiornare i commenti dello store e del prop di
   `CurrencySearchSelect`; aggiungere il `testId` in dashboard (D8).

   > **Note implementazione**: tolto il ciclo su `chain_steps`; commenti del modulo e di `getConfiguredCurrencySet`
   > aggiornati. `vitest fxRoutesStore.test.ts`: 5/5. Il `testId` della dashboard è nel passo 4.
   >
   > **⚠️ Fuori pista**: `CurrencySearchSelect.svelte` non è fra i permessi, quindi il suo commento resta com'è. È
   > ancora vero: «reachable via a configured FX route».
3. ✅ (06/10) **Helper margine** (D3): `utils/sync/syncRange.ts`; `buildComparisonSyncRange` vi delega (A) oppure si usa A′.

   > **Note implementazione**: D3-A.
   > - `syncRange.ts` contiene `SYNC_MARGIN_DAYS`, `subtractCalendarDaysOrMin` (spostata qui da
   >   `loadComparisonData`), `padSyncRange` e `buildMissingFxRatesSyncRequest`.
   > - La validità delle date si controlla con `addDays(v, 0) === v`, quindi senza nuovi export da `dateOnly.ts`.
   > - `buildComparisonSyncRange` mantiene il controllo sul lookback e delega a `padSyncRange`.
   > - Evidenza: `vitest syncRange + loadComparisonData + fxRoutesStore` → 64/64; log
   >   `/tmp/libreFolio_n_step2_unit.log`.
4. ✅ (06/10) **F1, F2, F6**: gestore del banner in dashboard. Intervallo dall'issue, fallback D5, timeout, toast per coppia,
   controllo del residuo ed evento (D4), chiave i18n nuova.

   > **Note implementazione**:
   > - `dashboard/+page.svelte`: il ramo `sync_fx_pair` chiama la nuova `syncMissingFxRates(issue)`.
   >   - Richiesta = `buildMissingFxRatesSyncRequest(issue)`, timeout 120 s.
   >   - Dopo la risposta: `invalidate()` + `loadAll(true, true)`, poi si guarda se un'issue `sync_fx_pair` copre
   >     ancora le stesse coppie.
   >   - Una sola notifica `fx.rates.synced` con `{origin:'dashboard-banner', pairs, start, end, outcome,
   >     stillMissing}`. Il toast ha una riga per coppia (`formatFxSyncResult`). Con esito ok/partial e date ancora
   >     scoperte si aggiunge la frase `dataQuality.missingFxRatesAfterSync` e la variante sale a warning.
   >   - Errore di trasporto: righe tradotte (`prices.sync.failedDefault`), nessun ricaricamento,
   >     `stillMissing: null`.
   > - Tolta la funzione locale `normalizeToSlug`, rimasta senza usi. Aggiunto
   >   `testId="dashboard-target-currency"` (D8).
   > - `fxCreationSync.ts` ora esporta `formatFxSyncResult` (era `formatResult`), `classifyFxSyncOutcome` (la
   >   regola dell'esito estratta senza cambiarla), `FX_SYNC_TIMEOUT_MS`, `FxSyncResponse` e `FxSyncOutcome`: banner e
   >   creazione condividono escaping ed esito.
   > - i18n con `dev.py i18n add`: `dataQuality.missingFxRatesAfterSync` (EN/IT/FR/ES), 5 righe per file; script
   >   `/tmp/libreFolio_n_i18n.sh`, log `/tmp/libreFolio_n_i18n.log`.
   >
   > **⚠️ Fuori pista**: il toast di esito arriva dopo il ricaricamento del report, non subito dopo il sync: solo a
   > quel punto si sa se le date sono coperte. Resta il toast informativo «Sincronizzazione tassi FX…» alla partenza.
5. ✅ (06/10) **F3**: regola «tutta la storia» in `fxCreationSync.ts`, via i props dal modal e dai 5 chiamanti, testo d'aiuto
   PAC (D2).

   > **Note implementazione**:
   > - `finishFxPairCreation` sincronizza `{pairs, start:'min', end: todayIso()}` con `{timeout: 120000}`.
   >   - `FxPairCreationContext` perde `start/end`.
   >   - `autoSyncStarted` = né modifica né solo MANUAL, senza condizione sul periodo.
   >   - Il completamento riporta `start:'min'` e `end` = oggi.
   > - `FxPairAddModal.svelte` perde i props `dateStart/dateEnd`.
   > - Chiamanti aggiornati, una riga ciascuno: dashboard, `fx/+page.svelte`, `fx/[pair]/+page.svelte`,
   >   `assets/[id]/+page.svelte`, `FxStep.svelte`.
   > - PAC: testo di default di `pairAbsentHelp` senza `{days}` né `values`; chiave aggiornata con `dev.py i18n
   >   update` nelle 4 lingue.
   >
   > **⚠️ Fuori pista**:
   > - Ho riscritto anche il commento di `SYNC_WINDOW_DAYS` (`FxStep.svelte:114-118`), fuori dalle righe concesse:
   >   diceva che anche «Aggiungi la coppia» usava i 7 giorni, quindi sarebbe diventato falso. D non tocca il file.
   > - `FxStep.svelte` non era già formattato con Prettier: il blocco `<section>` a `:248` e il modal a `:354`.
   >   Prettier l'aveva riformattato; ho annullato il riflusso estraneo, così il diff resta nelle righe concesse.
6. ✅ (06/10) **F5 / V2**: `KpiSection.svelte` per la card 1 (D7) e la card 2.

   > **Note implementazione**: regola del developer su tutte e due le card.
   > - `dayChangePct(change, base)` = change / |base| × 100; null solo con base 0 o illeggibile.
   > - Resa con `formatPercent()`, cioè il segno del valore e mai «+-».
   > - `data-direction` up/down/flat su `kpi-pnl-delta-day` e su `kpi-returns-delta-pct`; nuovo span
   >   `kpi-pnl-delta-day-pct`.
   > - Card 2: la condizione è passata da «stringa vera» a `!= null`, altrimenti un giorno piatto (0) l'avrebbe
   >   nascosta. Colore invariato (verde se ≥ 0).
7. ✅ (06/10) **Verde**: suite della lane (§10), `front check`, `front format --check`, `i18n audit`.

   > **Note implementazione** (lane 6159, `/tmp/librefolio-r2-n`, un comando alla volta):
   > - `vitest` diretto sui 6 file toccati: 131/131 (`/tmp/libreFolio_n_green_unit.log`);
   > - `dev.py front check`: 0 errori, 0 warning (`/tmp/libreFolio_n_front_check.log`);
   > - `front-utility core-unit`: 106 file, 2988 test (`/tmp/libreFolio_n_core_unit.log`);
   > - `front-utility component-unit`: 98 file, 2241 test;
   > - `front-utility onboarding-component-unit`: 14 file, 408 test;
   > - `front-portfolio banners`: 18/18 (`/tmp/libreFolio_n_green_banners.log`);
   > - `front-fx fx-add-pair`: 11/11;
   > - `front-portfolio dashboard`: 26/26.
   >
   > Regressioni sulle superfici vicine, nella stessa lane:
   > - `front-fx all`: 102/102 (`/tmp/libreFolio_n_regr_fx_all.log`), che copre i chiamanti di lista e dettaglio
   >   FX;
   > - `front-portfolio stale-price-banner`: 1/1;
   > - `front-portfolio privacy-masking`: 18/18;
   > - `front-asset all`: 123/123 (`/tmp/libreFolio_n_regr_asset_all.log`; comprende i 29 test di `asset-detail` e
   >   `asset-unit`).
   >
   > Controlli statici:
   > - `prettier --check` sui file toccati: verde tranne `FxStep.svelte` (vedi sotto);
   > - `git diff --check` pulito;
   > - `dev.py i18n audit`: nessuna traduzione mancante, le mie chiavi non risultano inutilizzate;
   > - `dev.py test check-orphans`: tutti i test raggiungibili;
   > - `dev.py lint --dead-code --scope frontend`: nessuno dei miei file nell'elenco (exit 1 per reperti
   >   preesistenti).
   >
   > **⚠️ Fuori pista**:
   > - `FxStep.svelte` resta con il disallineamento Prettier che aveva già alla baseline (`<section>` a `:249` e
   >   modal a `:355`): non lo tocco, perché sta fuori dalle righe concesse.
   > - La chiave `fx.sync.noNewData` è diventata orfana: il suo unico uso era il vecchio toast del banner. Toglierla
   >   (`dev.py i18n remove`) è fuori dal permesso i18n: la chiedo al coordinator.
   > - In `KpiSection.svelte` un commento diceva che `data-direction` guida il colore, ma il colore segue ancora
   >   `>= 0`: commento corretto, test 12/12.
8. ✅ (06/10) **Doc** (docs-writer): `mkdocs build` (strict), `check-links`, `translate-validate` sulle pagine tradotte.

   > **Note implementazione**: docs-writer (`n-docs`), solo pagine EN, nessuno stamp.
   >
   > Pagine aggiornate:
   > - `user/fx/add-pair.en.md:10-16`;
   > - `user/dashboard/index.en.md`: `:47` per la valuta di destinazione, `:76-87` per il banner (date ±1
   >   settimana, avviso se mancano ancora, suggerimento MAX + Sync All);
   > - `user/dashboard/kpi-cards.en.md`: `:31-42` e `:80-84`, con formule a denominatore `|…|`;
   > - `developer/.../core-ui/select.md:235-237`, solo la riga di `configuredOnly`;
   > - `developer/frontend/data-quality-banner.md`: righe `sync_fx_pair` e `MISSING_FX_RATES` (×2), più la
   >   limitazione di `busyCode`.
   >
   > Evidenza:
   > - `mkdocs build` strict pulito (`/tmp/libreFolio_n_mkdocs_build.log`);
   > - `check-links`: 81 validi, 1 rotto preesistente fuori perimetro (`user/assets/detail/chart/#rolling-return`,
   >   ancora presente solo in EN);
   > - `translate-validate`: debito atteso sulle pagine tradotte `dashboard/index` e `kpi-cards`; `add-pair`
   >   cambia solo nel significato (`/tmp/libreFolio_n_mkdocs_tv.log`).
   >
   > **⚠️ Fuori pista**: docs-writer ha corretto anche la riga `navigate_fx` della tabella CTA. La dashboard fa
   > `goto('/fx/' + target)` senza periodo, solo il dettaglio asset aggiunge `?start&end`. È documentazione per
   > sviluppatori, solo EN, e la correzione è vera; si annulla facilmente. Restano altre derive preesistenti in
   > `data-quality-banner.md`, segnalate e non toccate: modalità grouped «prime 3 issue», `MWRR_SERIES_UNRELIABLE`
   > assente, sezione test datata.
9. ✅ (06/10) **Revisione finale** (`git diff --check`), server spento, porta libera, consegna al coordinator → `FROZEN`.

   > **Note implementazione**:
   > - `git diff --check` pulito;
   > - `lsof -nP -iTCP:6159 -sTCP:LISTEN` e `:6169` vuoti;
   > - gli artefatti ignorati (`generated.ts`, `frontend/build`, `.testLog`, `test-results`, `mkdocs_src/site`)
   >   restano fuori;
   > - messaggio di commit proposto in `/tmp/libreFolio_commit_n_fxDashboardSync.txt`; voce CHANGELOG proposta
   >   al coordinator.
   >
   > **Aggiunta (06/10, permesso del coordinator)**: rimossa la chiave orfana `fx.sync.noNewData` con
   > `dev.py i18n remove fx.sync.noNewData -f`, preceduto da `--dry-run`. Il comando è quello concesso, più `-f` per
   > non bloccarsi sulla conferma interattiva.
   > - `i18n audit`: 4505 chiavi per lingua, nessuna mancante, nessuna delle mie chiavi segnalata
   >   (`/tmp/libreFolio_n_i18n_audit2.log`).
   > - Cataloghi: 8 righe per file (aggiunta `dataQuality.missingFxRatesAfterSync`, rimozione
   >   `fx.sync.noNewData`, aggiornamento `pairAbsentHelp`).
   > - `git diff --check` pulito. Si torna `FROZEN`.

Dopo ogni passo il piano va aggiornato con ✅, data, «Note implementazione» e «Fuori pista».

---

## 9. Definition of done

- **Creazione**: da qualunque punto venga creata, una coppia con almeno un provider reale (comprese le intermedie
  create insieme) manda **un solo** sync `{pairs, start: 'min', end: <oggi>}` con timeout 120 s. Modifica e MANUAL
  restano senza sync. Nessun chiamante passa più `dateStart/dateEnd`, e `svelte-check` è verde.
- **Banner**: il CTA `MISSING_FX_RATES` manda `{pairs, start: date_from − 7 g, end: min(date_to + 7 g, oggi)}`.
  - Mentre gira, il CTA è disabilitato e la pagina ha `data-busy="true"`.
  - Alla risposta il report si ricarica.
  - Il toast è per coppia e onesto; se la stessa issue resta c'è l'avviso (D4-A) e l'evento `fx.rates.synced`.
  - Senza date: tutta la storia (D5).
- **Menu valute** (dashboard e «Converti in» dell'asset): solo i capi delle rotte configurate, più la valuta
  corrente e quella di default. GBP compare solo se GBP è capo di una coppia configurata.
- **KPI**: mai «+-»; il segno della percentuale segue la regola scelta in D7; la card 2 è corretta.
- **Test**: rossi prima, verdi dopo, nella lane N. Nessun `waitForTimeout`, nessun testo tradotto nelle asserzioni,
  nessuna posizione fissa.
- **Qualità e doc**: format, check e `i18n audit` puliti; doc EN aggiornata, build strict e link verdi.
- **Chiusura**: piano aggiornato a ogni passo; nessun server attivo e `lsof -nP -iTCP:6159 -sTCP:LISTEN` vuoto.

---

## 10. Strategia di test (red-first, scritti da test-author)

| Livello | File | Casi | Runner (lane N) |
|---|---|---|---|
| Unità | `src/lib/stores/reference/fxRoutesStore.test.ts` (**nuovo**) | catena EUR→GBP→USD → set {EUR, USD}; con anche la coppia GBP-JPY → GBP presente; capi delle rotte MANUAL presenti; reset dello stato di modulo fra un caso e l'altro (`vi.resetModules`) | `front-utility core-unit` |
| Unità | `src/lib/utils/sync/__tests__/syncRange.test.ts` (**nuovo**) | `padSyncRange({2022-11-03, 2023-06-27}, today 2026-10-06)` → `{2022-10-27, 2023-07-04}`; tetto a oggi; inizio mai oltre la fine; `'min'` passa invariato; `buildMissingFxRatesSyncRequest`: unione delle coppie, slug normalizzati e deduplicati, fallback `'min'` con date assenti o non valide | `front-utility core-unit` |
| Unità | `src/lib/services/fxCreationSync.test.ts` (aggiornato) | corpo `{pairs, start: 'min', end: <oggi>}` con orologio finto; opzione `timeout: 120_000`; il caso «missing date» diventa «la creazione con un provider reale sincronizza sempre»; modifica e MANUAL restano senza sync | `front-utility core-unit` |
| Unità (regressione) | `src/lib/charts/__tests__/loadComparisonData.test.ts` | invariato, deve restare verde dopo la delega (D3-A) | `front-utility core-unit` |
| Componente | `src/lib/components/fx/FxPairAddModal.test.ts` (aggiornato) | montato senza `dateStart/dateEnd`; corpo `start: 'min'`; i casi `:349-350` («nessuna data → nessun sync») vengono rovesciati | `front-utility component-unit` e `onboarding-component-unit` |
| Componente | `src/lib/components/dashboard/KpiSection.test.ts` (esteso) | base −558,10 e delta +91,31 → `kpi-pnl-delta-day-pct` = `+16.36%` (D7-A) e mai `+-`; delta −91,31 → `-16.36%`; base positiva invariata; card 2 con NAV di ieri ≤ 0 → `kpi-returns-delta-pct` assente | `front-utility component-unit` |
| E2E | `e2e/portfolio/data-quality-banners.spec.ts` (esteso) | Con `injectDashboardIssues` + stub di `/fx/currencies/sync`. (1) issue `MISSING_FX_RATES` con 2022-11-03…2023-06-27 → aprire `data-quality-toggle`, cliccare `data-quality-cta-MISSING_FX_RATES` → il corpo è `{pairs: ['EUR-USD'], start: '2022-10-27', end: '2023-07-04'}`, CTA disabilitato mentre il sync è trattenuto, report richiesto di nuovo dopo la risposta. (2) `date_to` = oggi − 2 → `end` = oggi. (3) issue ancora presente al ricaricamento → evento `fx.rates.synced` con `stillMissing: true` e toast di avviso (variante, non testo). (4) issue iniettata solo alla prima richiesta → `stillMissing: false` | `front-portfolio banners` |
| E2E | `e2e/fx/fx-add-pair.spec.ts` (aggiornato) | corpo del sync e dettaglio di `fx.pair.creation-sync-completed`: `start: 'min'`, `end` = `todayIso()` dal fixture `../fixtures/dates` | `front-fx fx-add-pair` |
| E2E | `e2e/portfolio/dashboard.spec.ts` (nuovo test, D8-A) | stub di `/fx/providers/routes*` con la catena via GBP → `dashboard-target-currency-trigger`, `search-select-option-USD` visibile, `search-select-option-GBP` assente; con la coppia GBP-JPY GBP compare | `front-portfolio dashboard` |
| Backend (controllo del contratto, opzionale) | `test_data_quality_report.py` | `message_params` di `MISSING_FX_RATES`; nessuna modifica backend | `services roi-fifo-utils test_data_quality_report` |

Comandi (uno alla volta; sempre preambolo + `test --test-port 6159 --data-dir /tmp/librefolio-r2-n`):

```bash
P="PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py"
L="--test-port 6159 --data-dir /tmp/librefolio-r2-n"
$P test $L front-utility core-unit
$P test $L front-utility component-unit
$P test $L front-utility onboarding-component-unit
$P test $L db populate --force --clean          # solo per gli E2E: DB nuovo nella mia data-dir
$P test $L front-portfolio banners
$P test $L front-fx fx-add-pair
$P test $L front-portfolio dashboard
$P front check ; $P front format --check ; $P i18n audit
$P mkdocs build ; $P mkdocs check-links ; $P mkdocs translate-validate
```

---

## 11. Wiki context (pagine lette a mano; grafo assente nella worktree)

- [[decisions/fx-sync-pair-based]]: `POST /fx/currencies/sync {pairs, start, end}`, risultati per coppia.
- [[problems/fx-multi-route-no-fallback]]: le rotte si provano in ordine di priorità, con il dettaglio per tratta.
- [[sources/phase07-part4-round6-planc2r2-regressions-mockfx]]: tolto l'auto-sync in modifica nel dettaglio FX
  («user controls sync timing»). Per questo D2 lascia la modifica senza sync.
- [[decisions/fxsyncmodal-parent-ownership]], [[features/F-097]]: il sync FX del WAC parte da coppie + date mancanti.
  È il parente transazionale del precedente.
- [[domains/dashboard]], [[features/F-054]]: `DataQualityBanner` legge il campo unificato `data_quality`.
- [[concepts/fx-range-helper-pattern]]: `ensureFxRangeLoaded`, la cache della pagina; non viene toccata.
- Dopo il lavoro: `wiki-file` per «il backward-fill FX illimitato trasforma i buchi interni in tassi stantii
  silenziosi» (D6).
