# Classifica delle 325 voci aperte — 22/10/2026, sera

Fonte: `BACKLOG-aperte-20261022.md` (le 325 voci ancora valide, con le prove) e le «Decisioni del developer sulle
10 voci (22/10 sera)», che qui sono rispettate. Ondate già pianificate: `PIANO-ondata4.md` («Dopo l'ondata 4»),
`PROSSIMI_LAVORI.md` («Esito 22/10»), `ATTIVITA_INIZIO_1.4.md`. Codice letto in sola lettura su `dev_release2`.

**I principi applicati** (vincolanti, dal developer):
- **proteggere l'ingresso** (validazione, rifiuto, avviso) dove un errore può succedere davvero; **niente bonifiche**
  né correzioni in silenzio per casi mai visti. Le voci che «tamponano» nei calcoli un errore d'inserimento sono
  scartate, o trasformate in protezione in ingresso;
- **una casa sola per la matematica** (`financial_math/`): togliere copie = buona idea; aggiungere calcoli fuori casa = no;
- **niente bonifica hardcoded nell'app**: se serve, script esterno;
- **traduzioni it/fr/es solo su richiesta**: una riga sola, «giro di traduzione unico prima del tag»;
- la 1.3 non esce prima di novembre: c'è tempo per le buone idee, non per la lana caprina.

Taglie: p = piccola, m = media, g = grande (dal backlog). Giorni: stima grezza mia.

---

## Riassunto in numeri

| Gruppo | Voci |
|---|---|
| **1. Buona idea** | **110** — 7 già in ondata 4, 20 in ondata 5, **83 in ondata 6** |
| **2. Da raffinare** | **26** |
| **3. Lana caprina** (si scarta) | **125** |
| **4. Aspettano altro** (designer, utente, misura, decisione «dopo la 1.3») | **48** |
| Debito di traduzione → **giro unico prima del tag** (una riga, non classificate) | 15 |
| Chiusa dal developer il 22/10 (A-1: comportamento voluto) | 1 |
| **Totale** | **325** |

Controllo: 110 + 26 + 125 + 48 + 15 + 1 = 325.

### Le buone idee per ondata e proprietario

| Proprietario | Ondata 5 (voci) | Giorni ond. 5 | Ondata 6 (voci) | Giorni ond. 6 |
|---|---|---|---|---|
| **W** | 5 (B2, V-37b, W-B87, W-B88, J-58→protezione) | 7–8,5 | 21 (in 15 lotti) | ~6 |
| **X** | 5 (C-65a + W-B2 + X-R69, Z-35 + Z-32) | 3,5–4,5 | 9 (in 6 lotti) | ~3 |
| **Y** | 2 (Z-14b + Z-15) | 1–1,5 | 8 | ~2 |
| **J** | — | — | 4 (in 3 lotti) | ~1,5 |
| **MF** | 2 (B5, MF-FV P4 + pavimenti) | 4–6 | 2 | ~2 |
| **A** | — | — | 9 (in 8 lotti) | ~2 |
| **H** | 2 (H-18, X-R84) | 1 | 6 (in 5 lotti) | ~2,5 |
| **E** | 3 (C-70b, E-21 + W-B80) | 2,5–3 | — | — |
| **B** | 1 (M-1 arm64) | 0,5–1 (+ CI) | 1 (B-56) | 0,25 |
| **Z** | — | — | 1 (V-18) | 0,25 |
| **C** (coordinatore, con docs-writer e test-author) | — | — | 11 (in 8 lotti) | ~4,5 (di cui C-99: 2–3) |
| **G** (galleria) | — | — | 6 | ~1 |
| **M** (pipeline doc) | — | — | 2 | ~0,75 |
| **L** (Designer Lab) | — | — | 2 (un lotto) | 0,25 |
| **DV** | — | — | 1 (BK-5) | 0,1 |
| **Totale** | **20** | **~20–25** | **83** | **~26** |

Nota: i giorni dell'ondata 5 contano solo le voci del backlog. I lotti già nell'ondata 5 che non hanno un ID nel
backlog (#47, #48, CP12, Crédit Agricole analisi, MF-P1c, X-Q1…Q3/S1, R1 di J) valgono altri ~10–12 giorni.
L'ondata 6 è nuova: nasce da questa classifica. W è il più carico nelle due ondate (~14 giorni): se serve, V-15 e
l'igiene dei test di W vanno al test-author in parallelo.

---

## 1. Buone idee (110)

Per prime le voci con effetto visibile per l'utente. «Ondata 4» = già assegnata nel piano del 22/10.

### W · Import e transazioni (27 voci: 5 in ondata 5, 21 in ondata 6 in 15 lotti, 1 in ondata 4)

| ID | Cosa fa per l'utente | Ondata | Peso | Nota |
|---|---|---|---|---|
| **W-B88** | I plugin registrano la data dell'operazione, non la data valuta: numeri per periodo e lotti al posto giusto | 5 | m | già in ondata 5; nessuna bonifica dei dati salvati |
| **W-B87** | Le righe con effetto economico (tasse, commissioni, rettifiche) dei sei plugin in beta entrano davvero | 5 | g | decisione 22/10; i plugin restano in beta; BRIM non crea eventi |
| **V-37** (V-37b) | «⚡ Validate now» controlla campi obbligatori e formato prima di chiamare il server | 5 | p | già in ondata 5; poi #47 nello stesso form |
| **B2** | Una coppia di trasferimento con l'arrivo prima della partenza viene **segnalata** al salvataggio | 5 | p | decisione 22/10: solo segnalazione, nessuna correzione; la cura sta in `transactions/validation.py` (W), MF legge |
| **J-58 → protezione** | L'API rifiuta una coppia di rettifiche collegate con un codice chiaro che indica il TRANSFER | 5 | p | decisione 22/10; dopo W-BS; niente bonifica dei dati vecchi |
| **P-2** | Nell'anteprima del costo medio una riga di split non si chiama più «Diluizione» | 6 | p | il backend manda `split_rescale`; `add_at_wac` è morto |
| **V-24** | La cella del costo in Auto non mostra più per un attimo «💡 0.00» come già calcolato | 6 | p | |
| **W-B47** | La barra di stato dell'editor CSV («N righe valide», «errori», «duplicati») parla la lingua dell'app | 6 | p | chiavi ICU nelle 4 lingue; avvisare il coordinatore (file area T) |
| **W-B49** | Svuotare il costo manuale è rifiutato subito, non a «Salva tutto»; i tre testi non dicono più «vuoto = Auto» | 6 | p | prima il rosso Vitest su `diffDualItem` |
| **J-64** | Il CSV generico accetta un costo 0 scritto nel file senza chiederlo di nuovo | 6 | p | un costo 0 è un costo vero (Q-J57-3) |
| **W-B79** | «Promuovi coppia» non apre più una modale d'unione vuota quando differiscono solo data o costo | 6 | p | rosso prima |
| **C-42 + W-B46** | L'API rifiuta una coppia di cassa con valuta o importo incoerenti (CASH_TRANSFER, FX_CONVERSION) | 6 | p | protezione in ingresso; **conferma del developer**: cambia cosa accetta l'API; nessun controllo sulle coppie già salvate |
| **C-57** | Se la prima lista dei plugin fallisce, le icone arrivano al tentativo dopo, senza ricaricare | 6 | p | rosso prima; cura di una riga (`brokerHelpers.ts:65`) |
| **C-45** | Il 💡 del Bulk non conta candidati che poi il picker non mostra | 6 | p | rosso prima; se non si riproduce, si chiude |
| **W-B19** | Il controllo dei saldi del batch usa la casa unica invece di sommare la cassa da sé | 6 | p | regola 10; MF rivede; misurare sui set BRIM |
| **U-B9** | I broker mock usano l'icona del loro plugin (galleria e DB di test) | 6 | p | una chiave (`default_import_plugin`); prima del giro finale della galleria |
| **W-B91** | La guida dell'import, passo 3, indica un bottone che esiste | 6 | p | crea debito di traduzione → giro unico |
| **V-15** | Gli spec che creano e cancellano broker di `TEST_USER` passano ad account usa-e-getta | 6 | p | 11 spec; test-author; regola «DB condiviso» |
| **V-21 + W-B50 + IW-8 + AF-12** | Gli spec dell'import, del WAC e di image-crop non saltano più asserzioni con guardie `isVisible().catch` | 6 | p | igiene test: un lotto solo di W, test-author |
| **M-15 + TC-17 + W-B57** | `tx-picker-pagination.spec.ts` senza budget brevi: non cade sotto carico | 6 | p | togliere i timeout espliciti |
| **W-B86** | Regola dei plugin in beta nella skill e nella guida; Fineco su `RowSkips` | 4 | — | già assegnata |

### X · Plugin, asset e ricerca (17 voci: 5 in ondata 5, 9 in ondata 6 in 6 lotti, 3 in ondata 4)

| ID | Cosa fa per l'utente | Ondata | Peso | Nota |
|---|---|---|---|---|
| **Z-35 + Z-32 (a/b)** | Le chiusure Yahoo si salvano senza la rettifica del giorno di lettura (`auto_adjust=False`); i dividendi in pence (`GBp`) sono divisi per 100 | 5 | m | decisione 22/10, con MF; le righe già salvate in pence **non** si bonificano (l'utente corregge col Manual); «rendimento totale» in TODO_FUTURI |
| **C-65 (C-65a) + W-B2 + X-R69** | Cambiando provider o piano, una modale avvisa prima di scollegare le transazioni dagli eventi; «togli» e «cambia» seguono la stessa regola | 5 | m | decisione 22/10 (C-65a: ondata 5, X); X-R69 è la stessa domanda di prodotto |
| **X-R61 + X-R29** | Il Sync di una sola card o riga avvisa prima di sovrascrivere i prezzi salvati, come fa la lista; l'avviso dice quante righe sono manuali, se costa poco | 6 | p | protezione dei dati inseriti a mano; X-R29 solo la parte «quante manuali» |
| **X-R78** | Un prezzo manuale con Low o High dal lato sbagliato della chiusura è **rifiutato** (`ohlc_inconsistent`) | 6 | p | protezione in ingresso; **conferma**: oggi un test fissa «si salva com'è» |
| **W-B16** | Importando un backup di eventi, le righe `PROVIDER` si saltano con avviso se l'asset ha un fornitore (opzione per importarle) | 6 | p | protezione in ingresso contro il raddoppio al sync; file di X (editor eventi), l'export è di B |
| **X-R70** | Il conteggio dei prezzi dopo un refresh non include le date rifiutate dal controllo OHLC | 6 | p | |
| **X-R63 + W-B27** | Le date nel messaggio di errore dell'editor sono leggibili (`dateLabel`); la tabella degli eventi del piano programmato ha Maturity Settlement | 6 | p | X-R63 crea debito di traduzione → giro unico |
| **X-R33 + V-32** | Spec degli asset senza scelte per posizione (`firstCard`) e senza l'header `content-encoding` nelle risposte finte | 6 | p | igiene test |
| **X-N64b, X-N64c, X-N64d** | Confronti e segnali in cache per periodo e per segnale; nota sullo spec | 4 | — | già assegnate |

### Y · Cruscotto e grafici (11 voci: 2 in ondata 5, 8 in ondata 6, 1 in ondata 4)

| ID | Cosa fa per l'utente | Ondata | Peso | Nota |
|---|---|---|---|---|
| **Z-14b + Z-15** | Dopo un recupero dei prezzi, le pagine di asset e cambi e i pannelli di rischio e lotti già aperti si ricaricano da soli | 5 | p | decisione 22/10; piano 06 pronto |
| **Y-32** | Nella lista degli asset il Δ della card segue il prezzo live | 6 | p | domanda di prodotto: consiglio sì (`range_start` nel poll); allargare le glob degli spec |
| **W-B76** | La riga aperta con `?highlight=<id>` resta segnata: si capisce quale si è aperta | 6 | p | ruolo esistente (`bg-lf-selected`), niente palette |
| **T-ST** | «day(s)» / «giorno/i» diventa un plurale vero; la «d» del badge è tradotta | 6 | p | |
| **P-15** | «Reset layout» e «max» tradotti | 6 | p | due chiavi, 4 lingue |
| **Y-15** | Il pulsante «Refresh» dei broker parla la lingua dell'app | 6 | p | scegliere la chiave (consiglio: `dashboard.syncData`, come la pagina del broker) |
| **Y-18** | Passando alle Candele si vede che stanno caricando | 6 | p | passare `pnlCandlesLoading` a `GrowthChart` |
| **32-2** | La frase d'apertura del banner nella guida della Dashboard dice tutto quello che il banner segnala | 6 | p | docs-writer + `translate-stamp` |
| **V-14** | `data-quality-banners.spec.ts` senza sonde che annotano invece di fallire | 6 | p | igiene test |
| **Y-41** | La lista dei cambi disegna il confronto con un asset | 4 | — | già assegnata |

### J · Numeri e analisi (6 voci: 4 in ondata 6 in 3 lotti, 2 in ondata 4)

| ID | Cosa fa per l'utente | Ondata | Peso | Nota |
|---|---|---|---|---|
| **T-DI** | I due campi data della riproduzione storica (Rischio) seguono la lingua dell'app | 6 | p | partire da `DateRangePicker.svelte` (M-17) |
| **T-GRP** | Un gruppo geografico definito dall'host ha un nome nella tabella dello shock, non un id grezzo | 6 | p | `geography_groups` porta già gli id; i nomi per lingua dall'host |
| **T-U4 + J-62** | Il validatore «fattore di annualizzazione finito e positivo» in una copia sola (`financial_math/returns.py`) | 6 | p | regola 10; la parità esiste già (`test_risk_metrics_oracle.py`) |
| **J-68, J-71** | Un trasferimento in un giorno solo nomina l'origine; una sola `buildSyncTargets` | 4 | — | già assegnate |

### MF · Matematica finanziaria (4 voci)

| ID | Cosa fa per l'utente | Ondata | Peso | Nota |
|---|---|---|---|---|
| **MF-FV** (P4 + pavimenti all'indietro) | Grafici e viste più veloci, parità al bit | 5 | g | corretto dal developer il 22/10 sera: «tutto nella 1.3»; P4 collide con CP-8 di J solo nella 1.4 |
| **B5** | Il guadagno maturato di un titolo che esce dalla selezione ha una riga sua nel waterfall, non finisce in «Other» | 5 | p | decisione 22/10; rosso prima |
| **T-U5** | Il prezzo «del giorno» in una copia sola: via le copie di `portfolio_service.py:495` e `brokers/summary.py:245` | 6 | m | regola 10; farlo **prima** di CP-8 (1.4); V4 (PAC) e V10 fuori |
| **MF-A6** | La polvere sotto 1e-5 vale uguale per il motore giornaliero e per le righe (identità del §7) | 6 | p | usare `QUANTITY_DUST_THRESHOLD` in `daily_state.py` |

### A · Account e accessi (9 voci, 8 lotti)

| ID | Cosa fa per l'utente | Ondata | Peso | Nota |
|---|---|---|---|---|
| **A-28 + A-36** | Cambiando l'email nel Profilo, il campo «password attuale» compare quando il server lo chiede; la riga si assesta dopo il salvataggio | 6 | p | oggi l'utente resta bloccato con spazi o forme Unicode |
| **A-19** | Su un'istanza solo su invito, «Register here» non lampeggia al caricamento del login | 6 | p | uno stato `data-*` da aspettare |
| **A-17** | KeePassXC riempie Username, non Email, nella registrazione e nell'invito | 6 | p | Email prima di Username; controllare gli scatti |
| **TC-1** | Chi usa un lettore di schermo sente quali requisiti della password sono soddisfatti | 6 | p | due chiavi i18n, 4 lingue, `sr-only` |
| **H-8** | Il comando «password dimenticata» non gira come root nel container | 6 | p | `gosu` nella frase di `ForgotPasswordCard.svelte` |
| **A-61** | Dopo logout e login nella stessa scheda, i controlli di sicurezza non mostrano per un attimo quelli di prima | 6 | p | una chiamata a `registerClientSessionReset` |
| **A-38** | Regola scritta e test: un 422 non rimette parti del valore nel messaggio per i campi segreti | 6 | p | sicurezza; `security.md` + un test per campo |
| **21-2** | Un test tiene allineati il catalogo TS delle guide e il registro Python dei flussi | 6 | p | evita guide che non partono mai |

### H · Piattaforma (8 voci, 7 lotti)

| ID | Cosa fa per l'utente | Ondata | Peso | Nota |
|---|---|---|---|---|
| **H-18** | I toast sono annunciati ai lettori di schermo (`aria-live`) | 5 | p | decisione 22/10: «sì, H»; componente condiviso |
| **X-R84** | Se un pezzo dell'app non si carica dopo un aggiornamento, la pagina si ricarica da sola una volta invece di «500 Internal Error» | 5 | p | decisione 22/10; `hooks.client.ts` + `vite:preloadError` |
| **W-B26** | Una tendina aperta verso l'alto in una tabella non finisce sotto l'intestazione fissa | 6 | p | lista nel `body`; file condivisi UI e tabella |
| **H-44** | Il ripiego dell'anteprima PDF mostra il file invece di scaricarlo | 6 | p | prima la prova nel browser (o un test sull'header `Content-Disposition`) |
| **M-22** | I diagrammi Mermaid della doc si disegnano anche offline e senza chiamare jsDelivr da ogni pagina | 6 | m | con M; coerente con la politica H-55; scegliere il formato da copiare in `vendor/` |
| **R-7** | L'anteprima a tabella dei file segue il cambio di tema dal vivo | 6 | p | `FilePreviewModal.svelte`, un osservatore; DV può farla |
| **H-7 + Z-36** | `tzdata` nelle dipendenze: scheduler e date Yahoo giuste anche su un sistema senza database dei fusi | 6 | p | `pipenv install tzdata --keep-outdated`; insieme alla domanda 16 (dipendenze) |

### E · Email e testi (3 voci, 2 lotti)

| ID | Cosa fa per l'utente | Ondata | Peso | Nota |
|---|---|---|---|---|
| **C-70 (C-70b)** | Il 400 del parse e gli errori dell'anteprima dell'import arrivano tradotti | 5 | p | già in ondata 5; patch parcheggiata; W rivede |
| **E-21 + W-B80** | I motivi di un file non leggibile (93 `BRIMParseError`) e il rifiuto `ledger_unreadable` del gap-fix arrivano tradotti | 5 | m | già in ondata 5, dopo C-70b; W-B80 è lo stesso lavoro |

### B · Backup e Docker (2 voci)

| ID | Cosa fa per l'utente | Ondata | Peso | Nota |
|---|---|---|---|---|
| **M-1** | Immagine Docker **arm64**: Raspberry Pi e Mac Apple Silicon | 5 | p | decisione 22/10; arm 32 bit solo se un utente la chiede; CI più lunga |
| **B-56** | `dev.py db check --integrity`: un controllo in sola lettura del DB vivo dopo un ripristino a mano o un disco rovinato | 6 | p | `PRAGMA integrity_check` + testo non UTF-8 |

### Z (1 voce)

| ID | Cosa fa per l'utente | Ondata | Peso | Nota |
|---|---|---|---|---|
| **V-18** | Il pulsante che toglie un orario nello scheduler ha un nome accessibile tradotto (oggi «Remove 08:00» fisso); lo spec usa testid | 6 | p | |

### C · Coordinatore (11 voci, 8 lotti)

| ID | Cosa fa per l'utente | Ondata | Peso | Nota |
|---|---|---|---|---|
| **C-99** | Manuale admin con le variabili d'ambiente divise per categoria e un controllo che ogni `LIBREFOLIO_*` stia in una pagina | 6 | m | decisa «nella 1.3» dal developer (16/10); docs-writer; **dopo** il treno 10 (H-62, B) |
| **C-67 + J-7 + L-12** | Una sola build del frontend per il server di test: via la doppia build (5–7 min per run di coverage) e il rischio di ricostruire in release a metà giro | 6 | p | scelta tecnica: build debug strumentata per i test; il coordinatore decide |
| **C-68** | Gli artefatti Playwright di una categoria non spariscono quando parte la successiva | 6 | p | `outputDir` per categoria nel runner |
| **J-8** | Il runner non chiama più `npx`: un errore chiaro se manca `node_modules`, invece di un download dal registro | 6 | p | `dev.require_frontend_dependencies` in un punto comune |
| **I-07** | `tsc -p tsconfig.e2e.json` nel gate: gli E2E non riprendono errori di tipo | 6 | p | rimisurare i 3 TS2769 di C-66 prima |
| **C-51** | I 5 asset sintetici scrivono la forma nuova di `classification_params`: l'AI Export sui dati di prova non dà più 503 | 6 | p | serve agli scatti dell'AI Export (C-41) e alle sonde |
| **V-17** | La chiave `settings` del runner non prende anche `fx-chart-settings.spec.ts` | 6 | p | un filtro esatto |
| **H-20 + J-15** | L'output del runner e della galleria rediretto su file arriva riga per riga (`PYTHONUNBUFFERED`, `flush`) | 6 | p | serve a chi legge i log in `/tmp` durante un run |

### G · Galleria deterministica (6 voci, un lotto)

| ID | Cosa fa per l'utente | Ondata | Peso | Nota |
|---|---|---|---|---|
| **G-19** | «Asset detail rolling return» aspetta `data-busy="false"` prima di leggere il selettore | 6 | p | prima del giro finale della galleria |
| **G-23** | `settings/cache-panel` da una fixture, non dallo stato vero del server | 6 | p | |
| **G-25** | `onboarding/welcome-setup` mobile fr/es sta nell'inquadratura (`extendScreenToBlock`) | 6 | p | A conferma la scelta (A9) |
| **G-26** | `settings/password-modal` mobile: fermare lo scorrimento prima dello scatto | 6 | p | |
| **G-17** | Il nome dell'account usa-e-getta negli scatti è fisso, non casuale | 6 | p | |
| **G-14** | Gli orari degli scatti non dipendono dal fuso della macchina (`timezoneId`) | 6 | p | consiglio: `Europe/Rome` |

### M · Pipeline delle traduzioni (2 voci)

| ID | Cosa fa per l'utente | Ondata | Peso | Nota |
|---|---|---|---|---|
| **M-3** | L'audit degli stamp come opzione di `translate-validate`: il giro di traduzione non ritraduce pagine già buone | 6 | p | **prima del giro unico**; porta nel repo i tre script che stanno fuori |
| **M-11** | Regola di registro («tu», mai «usted») nei prompt della pipeline | 6 | p | prima del giro unico |

### L · Designer Lab (2 voci, un lotto)

| ID | Cosa fa per l'utente | Ondata | Peso | Nota |
|---|---|---|---|---|
| **L-22 + L-14** | Il catalogo del Lab non elenca i colori scritti nei commenti (≈170 voci false su 1450): la designer vede solo colori veri | 6 | p | saltare i commenti nello scanner JS e nell'inventario Python |

### DV (1 voce)

| ID | Cosa fa per l'utente | Ondata | Peso | Nota |
|---|---|---|---|---|
| **BK-5** | Nel grafico di confronto dei lotti il trattino della legenda «stimato al costo» ha lo stesso grigio della linea | 6 | p | una riga: `border-lf-cat-other` |

---

## 2. Da raffinare (26)

| ID | Cosa va chiarito o diviso | Domanda al developer (con consiglio) |
|---|---|---|
| **W-B63** | Mescola tre cose: (1) `volume` e `rate` ancora `Numeric` → `RealDecimal` (rifiuta `inf` in ingresso); (2) la query degli eventi su `None`; (3) la «correzione post-migrazione» degli `inf` già salvati | (1) e (2) sì, piccole, W ondata 6. (3) è bonifica: **consiglio: togliere**; se un DB reale ha un `inf`, script esterno |
| **X-R39** | Quattro residui dell'editor dati: uno utile (il salvataggio in tre richieste non dice la scrittura parziale), tre di riordino | Fare solo il messaggio di scrittura parziale (X, 0,25 g, ondata 6); gli altri tre in lana caprina. **Consiglio: sì** |
| **A-21b** | Username unici senza maiuscole: oggi «Bob» e «bob» convivono. Serve una migrazione e una regola per i doppioni già esistenti | Rifiuto **solo in ingresso** (nome nuovo che collide), nessuna migrazione dei doppioni esistenti (bonifica). Consiglio: sì, A, 0,5 g, ondata 6. Il testo cita una «010» che non esiste: riscrivere |
| **TC-5** | Due cose insieme: (a) i testi inglesi della shell (Sidebar, «Loading…», «Checking authentication…») — chiara, H, 0,25 g; (b) il tema scelto dall'header che non sopravvive al login | (b): il toggle dell'header salva sull'account? **Consiglio: sì** (A, 0,5 g): oggi la scelta si perde a ogni accesso |
| **H-3** (opzione A) | Chiave d'istanza persa = primo uso. La B (avviso con il conteggio dei segreti illeggibili) è in dev. La A fermerebbe l'avvio con un valore di controllo nel DB | Fermare l'avvio o solo avvisare? **Consiglio: B basta per la 1.3; A dopo**, come dice il piano H §14 (P24) |
| **A-30 + B-10** | Un nuovo link di setup/reset dall'API, dalla scheda Utenti e dal pannello dell'hosting. Due voci per lo stesso bisogno (dopo un ripristino) | Serve al coordinatore cloud nella 1.3? **Consiglio: solo se lo chiede lui** (allora B/A, 1 g, ondata 6); altrimenti 1.4. Oggi c'è `dev.py user setup-link` |
| **B-33** | Stato del ripristino illeggibile all'avvio: oggi si va avanti con i dati come sono | Fermarsi o servire? **Consiglio: fermarsi** con un messaggio chiaro quando lo stato esiste ma non si legge; decidere **dentro il lotto H-62/B** (ondata 4), senza un lotto a parte |
| **X-R48b** | La modale del cambio di valuta non avvisa degli SPLIT bloccanti. Cade se entra **N68** (decisione del 19/10: niente blocco, gli split sopravvivono, bottone «Ricollega eventi»). **N68 non è in nessuna ondata e non ha commit** | Mettere N68 in ondata 5 (X, 1,5–2 g)? **Consiglio: sì**; allora X-R48b si chiude come superata |
| **X-R56** | Uno SPLIT di un provider con rapporto non valido, salvato prima di X-R47, non si corregge né si cancella. È un caso «legacy» | Prima contare sui dati reali (`real-data-copy`) se esistono split con rapporto non valido. Se zero: chiudere. Se ce ne sono: aprire la via del Manual (correggere/cancellare), non una bonifica |
| **J-61 + J-59** | L'avviso «troppe lacune, la linea le unisce» non arriva mai all'utente; `MAX_LINE_RUNS = 30` resta un tetto provvisorio | Togliere l'avviso (consiglio di Y) o mostrarlo? **Consiglio: toglierlo** e ritoccare CHANGELOG e guida (Y, 0,25 g, ondata 6). J-59 (una serie sola per uscita) resta fuori: prestazioni senza misura |
| **W-B94** | «La metà che entra di un trasferimento come stima del prezzo»: idea del developer (22/10), non definita (quale fonte vince, come segnarla) | **Consiglio: TODO_FUTURI**, da analizzare con J e MF quando serve |
| **B3 + MF-J3** | Stessa cosa vista da I e da MF: nelle viste filtrate un trasferimento di cassa che attraversa il perimetro sposta la cassa ma non i pool versato/generato (K/R) | Le gambe esterne muovono K/R? **Consiglio: sì**, come un versamento/prelievo dall'esterno del perimetro (MF, 1 g, ondata 6) |
| **B6** | Una coppia ADJUSTMENT su più giorni conta come contante a valore 0 in viaggio. Q-N78-1k (ondata 4) cambia la regola delle coppie collegate | Verificare **dopo** Q-N78-1k se resta. Se sì: trattarla come asset in transito (MF, 0,5 g, ondata 6) |
| **T-U1** | «Un piano dei cambi unico» è troppo largo: cinque chiamanti di `convert_bulk`, ognuno a modo suo | Spezzare in MF-A13 (tasso per divisione) e l'avviso `STALE_FX`; dichiarare chiuso il resto. **Consiglio: sì** |
| **T-U9** | Due cose: le due percentuali scritte a mano (`percent_of`, casa unica, 0,1 g) e il `reason_code` sbagliato per il broker senza posizioni, che cambia il contratto (v2 del componente) | Percentuali subito (MF, ondata 6). Il codice motivo solo se nella 1.3 c'è già un bump v2 dell'AI Export (regola «un bump per release»): **c'è?** |
| **MF-L** | `BRSummary.holdings`: togliere (rottura API) o valutare col motore. D-MF1 senza risposta | **Consiglio: (a) togliere**, con ⚠️ nel CHANGELOG e `api sync`: nessuna pagina lo legge (W scrive, 0,25 g) |
| **MF-K3** | Due casi limite: portafoglio svuotato (card «—», linea piatta) e ROI semplice 0 se il periodo comincia prima del primo giorno | **Consiglio**: card e linea coerenti («—» entrambe); ROI semplice dal primo giorno con capitale. MF, 0,5 g, ondata 6 |
| **MF-C2** | Fette d'allocazione con somma ≤ 0: escono 50000 % / −50000 %. Cambia grafico, schema (`AllocationItem.value` null) e dataset AI Export | Fette `null` e grafico vuoto con avviso? **Consiglio: sì**; se tocca il dataset, nello stesso bump v2 di T-U9 |
| **MF-A3 + MF-A11** | Una posizione chiusa presto annualizza sull'anno intero; J propone una base unica per le righe aperte nel periodo. Stessa area, due voci | **Consiglio**: sotto 30 giorni «—» (b), come già per le posizioni chiuse; la base unica di A11 solo se MF la conferma coi numeri. MF, 1 g, ondata 6 |
| **MF-A13** | Il tasso del punto di prezzo ricavato per divisione in tre posti: copia di calcolo (regola 10) o mancanza di provenienza? Cambia l'ultima cifra | Misura su una copia dei dati reali: se le differenze sono < 1e-6, chiudere; se no, portare il tasso sul punto (MF con X, 1 g). Aspetta PL4 di X |
| **Y-9** | Il layout del PAC da telefono: la tabella dei target può superare la larghezza. Serve il giudizio del developer sugli scatti mobile | Guardare `pac-step-targets` e `pac-step-review` mobile: va bene così? Se no, colonne fluide (Y, 0,5 g) |
| **21-7** | La sezione Tools non ha una guida (`tools.hub`) | Serve una guida con un solo Tool (il PAC)? **Consiglio: una guida corta** (A, 0,5 g, ondata 6), oppure aspettare il secondo Tool |

---

## 3. Lana caprina (125) — si scartano

Una riga di motivo. Le sigle: *cosmesi* = pulizia senza effetto; *commento* = testo superato senza conseguenze;
*mai visto* = difesa contro un caso che nessuno ha incontrato; *senza misura* = ottimizzazione non misurata;
*stile* = preferenza; *bonifica* = contro il principio del developer; *test senza difetto* = copertura senza un difetto noto.

| ID | Motivo |
|---|---|
| C-44 | cosmesi: tre copie di `renderedFrames` nelle fixture della galleria |
| C-52 | strumento di sviluppo senza una necessità misurata (si fa quando serve una sonda su un asset) |
| C-56 | mai visto: nessun chiamante passa a `BrokerIcon` le props vuote |
| C-61 | mai visto: la barra del Bulk dopo un import «potrebbe» non comparire; se un utente lo vede, issue |
| C-69 | test senza difetto: i lotti di coverage del planner del PAC sono grandi e non curano nulla |
| C-72 | commento: runner e coverage |
| C-77 | test senza difetto: i test del PAC sono verdi, dichiarano più di quanto verificano, nulla sotto è rotto |
| C-78 | cosmesi: `toFixed(6)`, un fingerprint, un «-0» senza effetto visibile |
| C-92 | capitolo 1.2.0 già rilasciato: due righe in 4 lingue; se proprio, nel giro di traduzione unico |
| C-95 | documento per gli agenti: si aggiorna in una passata a fine riordino (1.4) |
| D-T1 | diagnostica dei Tool: la modalità di memoria non l'ha chiesta nessuno |
| D-T3 | senza misura: nessun benchmark né host delegato |
| B7 | mai visto: uno split mentre il titolo è in viaggio fra due broker |
| B12 | mai visto: l'unico chiamante passa sempre la data di fine |
| B17 | limite documentato: il cambio sulla cassa in viaggio resta in «Other», caso raro |
| B18 | una riga nuova nel waterfall per uno spread che «Other» contiene già; nessuno l'ha chiesta |
| B19 | l'ordine degli interi in un `set` è stabile in pratica: nessuno vede righe che cambiano posto |
| 49-1 | stile: lint del runner (149 errori ruff in 17 file, fuori dal gate) |
| P-8 | commento |
| P-9 | un comando di format su un file di test: al primo tocco |
| T-TS1 | opzione, non lavoro: «solo se lo si vuole» (D-P5), costo alto, valore basso → togliere dal backlog |
| T-TP | una riga di `pyproject.toml` che non rompe nulla (vince `pytest.ini`) |
| T-ICU | limite noto: i numeri dentro i messaggi del catalogo con una regione rara (es-MX) |
| T-COL | la collazione del browser ordina bene i nomi; nessuno se n'è accorto |
| T-DEAD | codice morto (`relative`, `formatDate`) |
| T-CAT | due rese delle etichette di categoria: non è matematica, nessun effetto |
| M-2 | già deciso: «solo se il caso si ripete», e non si è ripetuto |
| M-6 | mai visto: nessuna pagina usa `srcset`/`poster` con `../` |
| M-7 | latente: diventa vero solo con un'icona locale (W5-W6, 1.4) |
| M-9 | un controllo automatico per un difetto che si vede a occhio nel giro di traduzione |
| M-21 | solo build locali; la CI parte da zero; `dev.py mkdocs build` basta |
| M-24 | solo con `--headed`/`--ui`; il `resolvedOptions().locale` c'è già |
| 21-3 | mai visto: nessun flusso ha mai cambiato versione; il test si scrive al primo bump |
| 21-4 | nessun utente tablet ha segnalato nulla; un terzo progetto Playwright costa a ogni run |
| 21-6 | telemetria su un prodotto self-hosted: mai richiesta → togliere |
| 32-4 | commento di stato nelle pagine developer |
| 32-5 | docstring |
| V-2 | hook di test (`data-busy`) che nessun test chiede |
| V-8 | caso raro (broker cancellato in un'altra scheda): basta ricaricare; decisione del 13/10 |
| V-12 | titolo di una pagina developer |
| V-13 | commento («valued at cost») |
| V-30 | misura della coverage un po' bassa: non cambia nessuna decisione |
| V-31 | tollerato, nessun rosso da 10 giorni |
| V-34 | pulizia di test che controlla solo `res.ok()`: mai un rosso |
| P4-7 | senza misura: la cache dei prezzi «cresce» ma nessuno ha misurato quanto; torna con una misura |
| P4-9 | stile: 44 `readFileSync` in un test fragile ma verde |
| SP15 | `SensitiveValue` senza un consumatore dal 21/09 → TODO_FUTURI |
| U-B6 | comodità di sviluppo: `npm run i18n:build` basta |
| U-B7 | il gate `gate-plugin-i18n-ownership` lo segnala già dopo |
| L-2, TC-3 | cosmesi: uno scanner dei colori solo; si fa solo se conviene mentre si tocca lo scanner per L-22 |
| L-4 | l'export del Lab si scarica: basta |
| L-6 | indice «visto dal vivo»: nessuno lo usa |
| L-8 | comodità del picker |
| L-9 | limiti noti e documentati → chiudere come «accettati» |
| L-11 | valore in calo: la baseline dei colori si svuota con i lotti |
| L-15 | riordino di `CONTRAST_PAIRS`; la designer non l'ha chiesto |
| L-17 | il picker non nomina la fetta di un grafico: nessuno l'ha chiesto |
| L-19 | commento: due numeri di riga in una pagina developer |
| R-5 | mai visto: nessun chiamante passa `hsl()` con spazi |
| G-7 | il coordinatore ha già detto «senza correzione» |
| G-27 | etichetta fissa «prima (v1.2)» in uno script: si cambia quando si prepara il giro 4 |
| TC-9 | lo splash della PWA beige invece di grigio-verde: differenza minima, costa icone ridipinte |
| TC-11 | mai visto: una tendina aperta che diventa disabilitata sotto il mouse |
| DV-4 | `hexToHsl` usato solo dai test |
| IW-6 | stile: classe per prop contro `variant` |
| H-11 | mai chiesto: build locale dietro un proxy che ri-firma il TLS |
| H-31 | facoltativa: E l'ha già risolta coi suoi 401 |
| H-48 | la barra finale di un link di pagina: `env_url` la toglie da sempre, nessuno se n'è lamentato; con H-47 se mai |
| H-50 | senza misura: una lettura per voce solo con plugin che hanno impostazioni SYSTEM (oggi solo `mockprov`) |
| H-56 | mai visto: spegnimento nei primi secondi dopo l'avvio; la piattaforma uccide comunque al `kill_timeout` |
| H-58 | due righe di doc developer: al prossimo tocco di `alembic.md` |
| A-4 | prosa della devWiki: lavoro dello storico fuori dalle ondate |
| A-18, E-6 | stesso tema: il registro delle schede importa i corpi; un `vi.mock` in più per scheda non è un difetto |
| A-29 | solo `vite dev`: una riga in `PUBLIC_ROUTES` quando serve a chi sviluppa |
| A-31 | mai visto: ripristino con l'admin iniziale mai attivato; `dev.py user setup-link` rimedia |
| A-37 | cosmesi: togliere `NoInputEchoRoute` non cambia nulla, può solo rompere |
| A-41 | lo dice la voce stessa: «solo se compare un motivo nuovo» → chiudere |
| A-48 | il link del caffè sulla pagina offline di un'istanza gestita: innocuo |
| A-49 | «non verificabile» basta: l'avvio avvisa già della chiave inutilizzabile |
| A-59 | ramo irraggiungibile |
| A-60 | riordino di due cerchi d'avatar; il colore lo decide il programma colori |
| X-R4 | un riquadro Mermaid sbagliato nella guida FX: al prossimo tocco |
| X-R26 | latente: la pagina non cambia asset senza smontarsi |
| X-R36 | nota, non difetto (MD5 a 32 bit senza proprietari degli asset) |
| X-R42 | tollerato: righe FX lasciate da un test, nessun rosso |
| X-R44b | mai visto: codici di fornitore orfani esistono solo con plugin esterni che non ci sono |
| X-R80 | corsa rara sulle gambe di una catena; c'è `replace` |
| X-R49b | corsa rara prima del `BEGIN` differito |
| X-R67 | mai visto: 32 766 eventi su un asset (cedole giornaliere per 90 anni) |
| X-R68 | due funzioni senza chiamanti |
| X-R76 | troncare la 7ª cifra decimale di un importo non cambia nulla di visibile |
| X-R77 | un test che accetta un numero come nome: al prossimo tocco |
| X-R81 | raro: la conferma già aperta non vede una cancellazione fatta altrove; ricaricare basta |
| X-R82 | docstring |
| X-R83 | ramo morto, ipotesi di difetto ritirata |
| W-B7 | testo di `TODO_FUTURI` superato: si aggiorna con K3 |
| W-B18 | docstring di test |
| W-B78 | una costante `10` ripetuta: non è matematica, nessun difetto |
| W-B90 | mai visto: nessun chiamante passa `columns: []` |
| J-1 | chiudere: resta solo il punto 3, che è MF-A13 |
| J-4 | prosa della devWiki: storico |
| J-55 | chiarezza marginale nel prompt dell'AI Export (`null`): il modello capisce |
| J-56 | un gradino nel secchio del taglio, settimanale/mensile: minimo e raro |
| J-70 | **bonifica**: il rifiuto in ingresso di un costo negativo esiste già (`costBasisNegative`, `transaction_batch_stages.py:196`); le righe salvate prima le corregge l'utente col Manual |
| Z-23 | riordino di 6 `flock` in file di tre sessioni, nessun difetto |
| Z-31 | nessun effetto: la query dei prezzi non limita l'inizio, ma nessuno lo chiede sotto il 1900 |
| Z-38 | copia di una regola di campionamento dell'AI Export: non è matematica finanziaria, nessun effetto |
| Z-40 | differenze volute, nel contratto: chiudere come «accettato» |
| B-2 | commento |
| B-6 | il polling del backup funziona; l'aiuto comune mette in pausa a scheda nascosta, forse non voluto |
| B-12 | mai visto: salto d'orologio fra worker al primo avvio dopo un ripristino; nessun rischio per i dati |
| B-46 | lo stderr di Alembic in un log d'upgrade contiene nomi di tabelle, non dati: utile al triage |
| E-2 | tipi larghi nel client generato, nessun effetto a runtime; quando si tocca il generatore |
| E-3 | `ApiError` è un'astrazione morta: i lettori controllano `isAxiosError` prima; togliere quando si tocca |
| E-19 (D1/D2) | **bonifica**: la correzione automatica dei codici di valuta salvati; l'avviso e il suggerimento ci sono già (E-19a/b), l'utente corregge; se serve, script esterno |
| E-22 | senza misura di un problema: 0,6 s a un milione di righe a ogni risveglio |
| Y-10 | la maniglia funziona col dito; mostrarla cambia gli scatti mobile e nessuno l'ha chiesta |
| Y-26 | un prezzo esattamente 0 all'inizio della serie: caso che in pratica non esiste |
| Y-35 | tenere `PRICE_HISTORY` non costa nulla; toglierlo rompe l'API |
| Y-36 | latente: il filtro delle transazioni resta nel browser |
| Y-37 | due righe in una pagina developer |
| MF-SEC9d | senza misura: tetto globale per fornitore, «solo informazione» |
| MF-SEC9f | nota informativa, «nessuna azione» → togliere |

---

## 4. Aspettano altro (48) — lasciare stare, ma dirlo

### La designer (programma colori, giro 4): 20

| ID | Cosa aspetta |
|---|---|
| TC-8 | la risposta della designer al pacchetto del 19/10 (domande 39–42): i ruoli provvisori |
| TC-10, IW-7 | la rilettura del developer **e** della designer delle scelte «più vicine» delle ondate notturne (D-T27, D-T21) |
| DV-7, DV-10 | i ruoli categoriali e la revisione delle mappe «voce → ruolo» |
| IW-5, TR-4 | il ruolo categoriale «coppia/cambio», split, promuovi (69 classi) |
| AF-1 | un colore unico per lo strumento misura (Q12 «niente arcobaleno») |
| AF-3 | domanda aperta 7: un accento per pagina o il verde dell'app |
| AF-10 | un neutro «sopra panel» con il suo hover (domanda 3) |
| AF-11, AF-14 | i ruoli categoriali per tipo di file; il tema chiaro del foglio di calcolo (punto 35) |
| BK-2, IM-3, IM-6 | il ruolo categoriale viola (lotti, segnali) e quello dei provider |
| R-6 | il ruolo per la linea di anteprima degli editor |
| L-7 | l'accettazione dal vivo nel Lab (`designer_live.sh`) |
| L-3 | il campionario dei componenti: solo se la designer lo chiede |
| L-21 | il censimento a runtime dei colori ECharts: un giro del Lab con il server, alla chiusura del programma colori |
| DV-5 | la passata sui documenti a fine programma colori (decisione del 14/10) |

### Il giro finale della galleria (dopo la designer e dopo il treno 10): 9

| ID | Cosa aspetta |
|---|---|
| C-41 | gli scatti dell'AI Export (5 pagine, desktop e mobile); prima C-51 |
| G-20 | gli scatti del ripristino: l'interfaccia cambia con H-62 e B (treno 10) |
| G-21, X-R32 | uno scatto della ricerca con le sezioni premium (stessa cosa) |
| G-22 | la scheda Security con controlli da guardare, e la riga di connessione |
| G-24 | la modale «What's new» |
| M-12 | una nuova cattura dai dati del developer con liquidità in un'altra valuta (`normalize-dashboard-fixture`) |
| M-33 | uno scatto con la colonna YOC |
| G-11 | una run con osservatore di `data-scroll-state` su mobile es (header che resta) |

### Un utente, un report, una misura reale: 10

| ID | Cosa aspetta |
|---|---|
| C-43 | schermate vere dei portali di 8 broker (la galleria non le fa) |
| C-91 | un report vero di Interactive Brokers |
| C-80, C-81 | la run di coverage dei cancelli finali |
| C-82 | una run a 4 worker con un'altra corsia attiva, prima del rilascio |
| H-38, H-40 | una prova su un Docker vero / un host Linux con Docker (Tailscale Serve, IPv6) |
| V-35 | un nuovo rosso con `[fx-panel-log]`: mai visto a mano |
| J-19 | la prossima caduta `worker_crashed`: la strumentazione c'è |
| D-T2 | il secondo Tool |

### Già decise «dopo la 1.3» dal developer, o fuori dal nostro controllo: 9

| ID | Cosa aspetta |
|---|---|
| C-60 | una versione di Python con un vantaggio misurabile (resta 3.13) |
| C-98 | CoinGecko: risposta data all'utente (#43), «dopo la 1.3» |
| Z-4 | la politica D-19 (un campo per asset, migrazione): piano 06, dopo la 1.3 |
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
| U-B1 | un plugin esterno vero montato a runtime (D-X11: facoltativa) |
| W-B24 | un'istanza multiutente che chieda chi può modificare i dati condivisi → TODO_FUTURI |
| U-B2, X-R23, Y-7 | il blocco del riordino all'inizio della 1.4 (FE4/FE5a, Y4a). **Da aggiungere a `ATTIVITA_INIZIO_1.4.md`**: non ci sono |

---

## Debito di traduzione → una riga sola: «giro di traduzione unico prima del tag»

Non classificate una per una. Partono solo su richiesta del developer, con la pipeline Aphra, quando l'inglese è fermo
(le pagine EN del motore cambiano ancora: N78-1 del 22/10). Prima del giro: M-3 (audit degli stamp) e M-11 (registro).

- **Pagine admin**: H-5 (hosting_providers, filesystem, docker_advanced, connection_checks), A-10 (users, email,
  configuration#accounts…; dentro anche W-B21 e `orphan_pair_halves`), B-7 + B-11 (cli_tools#backup, backup_restore).
  Ordine delle ancore: cli_tools#backup prima di filesystem/docker_advanced; connection_checks#client-address prima di
  configuration/docker_advanced.
- **Pagine utente e teoria**: W-B28 (events#new-event, form), J-22, J-25, J-29, J-31, J-32, J-34 (returns, signals,
  fifo-lot-analysis, portfolio-engine, deposited-capital, max-drawdown: un giro solo, stesse pagine).
- **Qualità delle traduzioni esistenti**: P-14 (es «bróker», ~22 chiavi UI), M-5 (virgola o punto nelle formule:
  **serve la regola, consiglio: punto**), M-8 (etichette UI nelle pagine di teoria col nome del catalogo), M-10
  (nomi dei provider: **consiglio: la forma dell'app, in inglese**).
- **Debito nuovo creato dall'ondata 6**: 32-2, W-B91, X-R63, #49 (già tradotto in ondata 4 per eccezione).

Totale: 15 voci + le 3 nuove.

---

## Raggruppamenti: stessa cosa vista da due workstream, da fondere in un lotto

| Lotto unico | Voci | Chi | Ondata |
|---|---|---|---|
| Modale al cambio di provider/piano: una regola sola | C-65 (C-65a), W-B2, X-R69 | X | 5 |
| Yahoo senza rettifica e GBp | Z-35, Z-32 (a/b) | X con MF | 5 |
| Rifiuti dell'import tradotti | C-70b, E-21, W-B80 | E, W rivede | 5 |
| Coppie di cassa coerenti (protezione in ingresso) | C-42, W-B46 | W | 6 |
| Sync che sovrascrive i prezzi salvati: avviso coerente | X-R61, X-R29 | X | 6 |
| Una sola build per il server di test | C-67, J-7, L-12 | C | 6 |
| Output del runner riga per riga | H-20, J-15 | C | 6 |
| `tzdata` nelle dipendenze | H-7, Z-36 | H | 6 |
| `tx-picker-pagination` senza budget brevi | M-15, TC-17, W-B57 | W | 6 |
| Igiene degli spec di W | V-21, W-B50, IW-8, AF-12 | W (test-author) | 6 |
| Igiene degli spec di X | X-R33, V-32 | X | 6 |
| Editor dati dell'asset: piccole | X-R63, W-B27 (+ il messaggio di X-R39 se sì) | X | 6 |
| Validatore dell'annualizzazione in casa | T-U4 (R11), J-62 | J | 6 |
| Profilo: email e password attuale | A-28, A-36 | A | 6 |
| Scanner dei colori senza i commenti | L-22, L-14 (+ L-2/TC-3 solo se conviene) | L | 6 |
| Cassa che attraversa il perimetro e i pool K/R | B3, MF-J3 | MF | da raffinare |
| Annualizzazione delle righe aperte nel periodo | MF-A3, MF-A11 | MF | da raffinare |
| Link di setup/reset dall'API e dal pannello | A-30, B-10 | A/B | da raffinare |
| `inf` nelle colonne `Numeric` | W-B63 (parti 1-2) | W | da raffinare |
| Avviso «lacune unite» | J-61, J-59 | Y | da raffinare |
| Scatto premium della ricerca | G-21, X-R32 | G | galleria finale |
| Registro delle schede di Impostazioni | A-18, E-6 | — | lana caprina |
| Giro di traduzione unico | 15 voci sopra | coordinatore | prima del tag |

---

## Dubbi rimasti

1. **N68** (19/10: niente blocco, split che sopravvivono, bottone «Ricollega eventi») è deciso ma **non è in nessuna
   ondata e non ha commit**. Va in ondata 5 (X)? X-R48b dipende da questo.
2. **Bump v2 dell'AI Export nella 1.3**: T-U9 (codice motivo) e MF-C2 (fette null nel dataset) cambiano un contratto.
   Se nella 1.3 non c'è già un bump, conviene lasciarle alla 1.4 (regola «un bump per release»).
3. **C-42/W-B46 e X-R78** sono protezioni in ingresso che **cambiano ciò che l'API accetta** (coppie di cassa
   incoerenti; prezzo manuale incoerente con la chiusura). Le ho messe fra le buone idee perché seguono il principio;
   serve comunque il «sì».
4. **C-99** (manuale admin per categoria) è deciso «nella 1.3» dal developer ma non è in nessuna ondata: l'ho messo in
   ondata 6, dopo il treno 10.
5. **U-B2, X-R23, Y-7** dipendono dal blocco del riordino (FE4/FE5a, Y4a) ma non stanno in `ATTIVITA_INIZIO_1.4.md`:
   da aggiungere, altrimenti si perdono. Stesso per E-2/E-3 («rimandate alla 1.4» nel testo), che ho messo in lana
   caprina.
6. **Carico di W**: ~14 giorni fra ondata 5 e 6, più #47 e Crédit Agricole. V-15 e l'igiene degli spec possono andare
   al test-author in parallelo; W-B16 l'ho dato a X.
7. **H-44** e **C-45/C-57** li ho messi fra le buone idee «con un rosso prima»: se il rosso non si scrive, la voce si
   chiude senza altro lavoro.
8. Non ho verificato su dati reali: X-R56 (split con rapporto non valido) e MF-A13 (differenze dell'ultima cifra)
   restano «da raffinare» proprio per quella misura.
