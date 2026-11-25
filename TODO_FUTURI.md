# TODO FUTURI

Idee e miglioramenti ancora da ponderare, per tema. Le voci completate o scartate stanno in `TODO_Completati.md`; i
lavori già decisi per la 1.4 stanno nel journal, `Release_2/Phase_2/ATTIVITA_INIZIO_1.4.md`.

---

# Asset e dati di mercato

## 🧬 Profilo dei dati dell'asset — quello che resta dopo la 1.4

**Data aggiunta**: 18 Ottobre 2026, ridotta il 20 Novembre 2026 · **Status**: 📋 FUTURO — da progettare ·
**Priorità**: 🔼 Medio-alta
**Origine**: fusione di F16 (feedback Giuseppe + Alfy, 07/08/2026), F-MC-3 (feedback utente 08/09/2026), le voci
C-86 e C-87 del backlog (utente C, chat del 04/09), due note sciolte (extraETF, aziende) e le richieste GitHub
#50, #51 e #52 di @Xgialippo (17/10/2026). Ridotta alla chiusura della corsia 68 (journal,
`Release_2/Phase_2/68_assetProfile/plan-phase02AssetProfile.prompt.md`, §11 «Fuori dal piano», r.778–792, e r.766).
Skill di riferimento: `enricher-plugin`, `asset-plugin`.

### Cosa c'è già (1.4, corsia 68)

Il profilo dell'asset: un elenco chiuso di voci (costi, il fondo, la società, l'obbligazione, paesi e settori), ognuna
con la sua fonte, la sua data e la sua storia. Le leggono ogni settimana gli arricchitori (justETF, Borsa Italiana,
Yahoo, il registro ESMA), e la pagina dell'asset le mostra nella scheda «Profilo». Il TER di ogni ETF c'è (#51); il
**TER medio del portafoglio è scartato** (giro 28 del piano), non rinviato.

### Cosa resta

- **Esposizione per azienda sul portafoglio** (#50) e le **prime posizioni dei fondi**, che oggi non si salvano (I2
  del piano). Serve l'**identità delle aziende**: «Apple» e «Apple SRL» devono risultare la stessa azienda →
  identificatori univoci (ISIN per le quotate), normalizzazione dei nomi, regole di confronto e intervento manuale per
  i casi ambigui.
- **Valuta base ed esposizione valutaria** (ex F-MC-3). La valuta del fondo ora è una voce del profilo
  (`fund_currency`), ma:
  - valuta di quotazione, valuta base dello strumento ed esposizione economica sottostante non sono la stessa cosa.
    Un ETF sul Giappone non implica valuta base JPY né esposizione JPY pura: posizioni, classe di quote e coperture
    valutarie cambiano il risultato;
  - per l'esposizione effettiva serve una distribuzione valutaria look-through, con data, copertura e quota
    «Sconosciuta», non un codice dedotto dalla geografia;
  - grafico in Dashboard con metodo e denominatore dichiarati, cassa e posizioni trattate in modo coerente, dati
    incompleti visibili, nessuna falsa precisione. Prima un disegno ASCII e la decisione del developer, poi una
    revisione su esempi sintetici multi-valuta e coperti;
  - **la variazione non realizzata** (developer, 12/10/2026, voce 23): oggi il tooltip dei KPI della Dashboard
    (`period_unrealized_breakdown`, `KpiSection.svelte`) separa, valuta per valuta, l'effetto dell'asset da quello del
    cambio, ma ragiona solo sulla valuta di quotazione. Con la valuta base dovrà usare anche lei.
- **Altre aggregazioni sul portafoglio**, con lo stesso principio: un fatto per asset, pesato sul valore delle
  posizioni (o raggruppato), con la quota dei dati mancanti dichiarata. Candidati: rendimento a scadenza e duration
  medi delle obbligazioni; esposizioni per emittente del fondo, per tipo di replica, per domicilio, per copertura
  valutaria, per politica di distribuzione. Le calcola il backend.
- **Rendimento e duration calcolati da noi** invece che letti dalle fonti (ex C-87), in
  `backend/app/services/financial_math/`.
- **Il calendario di cedole e dividendi attesi** (journal, `68_assetProfile/calendario-cedole-PROF.md`).
- **Portafoglio diviso per obiettivi** (GitHub #52, @Xgialippo, 17/10/2026; qui dal 22/10, decisione del developer):
  raggruppare gli asset per obiettivo («i pilastri di Coletti»: fondo emergenze, pensione…), con sottogruppi o tag, e
  filtrare la Dashboard per gruppo. Oggi la Dashboard si filtra solo per broker. Si lega all'idea dei «Portafogli»,
  gruppi di broker, di asset o di entrambi (vedi «Idee sparse»). Domande poste all'utente il 18/10, ancora
  senza risposta: un asset sta in un solo obiettivo o si divide (a quote o a lotti)? gruppi di broker, di asset o
  tutti e due? cosa vedere per ogni portafoglio (Dashboard filtrata, KPI e allocazione propri, allocazione obiettivo
  per il PAC)? Registro: `PROSSIMI_LAVORI.md`, #52.
- **Documenti attaccati all'asset** (il KID) e **note personali**.
- **Nuove fonti e aiuti**:
  - **GLEIF**: nome e paese dell'emittente, dal LEI che il profilo già salva (`issuer_lei`);
  - **FinanceDatabase** e **OpenFIGI**, come aiuto alla ricerca dell'identificativo;
  - **i file degli emittenti caricati dall'utente**;
  - **extraETF**: anche la distribuzione valutaria, che si sposa con la valuta base del fondo;
  - **Investing.com** e **TradingView**: nessuna API ufficiale, e i termini vietano la lettura automatica anche agli
    abbonati. **Bassa priorità**, salvo che portino titoli, o meglio classi di titoli, che le fonti di oggi non coprono;
  - **fornitori a pagamento con la chiave dell'utente**: EODHD Fundamentals, Financial Modeling Prep, Finnworlds;
    Morningstar o LSEG a livello aziendale;
  - **Interactive Brokers** (ex C-86): prezzo corrente e storico letti con le API e la chiave dell'utente; serve un
    account per le prove. Dettagli: `Release_2/Phase_0/38_postReleaseBacklog/feedback-early-user-C-20261014.md`,
    voce 4.
  - L'arricchitore **CoinGecko** non è qui: è in `PENDING_IDEA_JOBS_1.4.md` (J-2), da decidere per la fine della 1.4.
- **Le tre correzioni alla nostra libreria justETF** («se serviranno le faremo»): la voce «coperto dal cambio», le
  righe «UCITS compliance» e «Fund Structure», il caso «ISIN sconosciuto» (`68_assetProfile/prove/prove-arricchitori-PROF.md`,
  r.714). Quando si faranno, si fanno nella libreria (sub-repo), non nel plugin.

### Licenze

justETF (AGB §3.1), Borsa Italiana/Euronext e Yahoo limitano l'uso automatico dei loro dati. In self-hosted ogni istanza
interroga per il suo utente, a basso volume e senza ridistribuire: rischio basso, tollerato nei fatti. Per il cloud a
pagamento vedi `RESIDUO_CLOUD.md`.

### Collegamenti

- Piano della 1.4: `Release_2/Phase_2/68_assetProfile/plan-phase02AssetProfile.prompt.md`.
- Piano in pausa: `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00AssetIdentityAndIdentifiers.prompt.md`
  (identità asset, identificativi).
- `LibreFolio_developer_journal/Release_2/Phase_1/PROSSIMI_LAVORI.md` (#50, #51, #52).
- «💱 Settlement multicurrency ed esposizione»: F-MC-1 e F-MC-2 restano lì.

## 🔀 Split e prezzi rettificati dai fornitori (MF-SPL1, 23/10/2026)

**Il problema.** Dopo uno split, Yahoo **riscrive all'indietro** le chiusure (e i dividendi) nelle unità di oggi, anche
con `auto_adjust=False`: il `Close` è sempre rettificato per gli split (solo `Adj Close` toglie in più i dividendi).
Yahoo non dà una chiusura «grezza». Il motore invece cambia la quantità solo nel giorno dello split (la rettifica
collegata all'evento SPLIT) e prima usa il prezzo così com'è.

Esempio, AAPL split 4:1 del 31/08/2020: il 28/08 abbiamo 10 azioni, Yahoo dà 124,81 (il vero era circa 499) →
10 × 124,81 = **1 248** invece di 4 990; il 31/08 40 × 129 = 5 160. Il TWRR salta del +313 % senza flusso e prima dello
split compare una perdita finta. Stessa cosa per i dividendi: Yahoo dà 0,205 invece di 0,82 per i dividendi del 2020,
quindi con le 10 azioni di allora l'importo esce diviso per 4. Verificato dal vivo da X (yfinance 1.7.0) il 23/10.
Non l'ha introdotto Z-35; il «Sync completo» però estende le chiusure rettificate a tutta la storia prima di ogni split.

**Decisione 1.3**: opzione C — solo documentazione («Known limitation» nella pagina di Yahoo, nota nella metodologia di
MF) e la voce MF-SPL1 del backlog. Niente codice.

**Idea di soluzione (da riparlarne)**: nel database i prezzi si salvano **veri**, nelle unità del loro giorno; la vista
rettificata si calcola in lettura.

- **Gli split sono eventi dell'asset** (fornitore o manuali), con data e rapporto: l'unica fonte.
- **All'ingresso, un solo normalizzatore** in `financial_math/` (non nel plugin): ogni plugin dichiara nel contratto se
  consegna prezzi `raw` o `split_adjusted`; se rettificati, il nucleo li riporta al vero moltiplicando per i rapporti
  degli split **successivi alla data della riga**, letti dagli eventi dell'asset.
- **Non serve riscaricare la storia intera**: la lista degli split (`ticker.splits`, già letta dal plugin,
  `plugin.py:370`) è piccola e si legge a ogni aggiornamento; le righe già salvate «vere» restano giuste anche dopo uno
  split nuovo; si convertono solo le righe appena scaricate, con gli split conosciuti in quel momento.
- **In lettura, due viste da una funzione sola** `split_factor(asset, da, a)`: la valutazione (Dashboard, lotti, P&L,
  TWRR) usa prezzo vero × quantità vera; grafici, segnali e rischio usano la serie rettificata (prezzo vero × fattore fino
  alla data di riferimento), così il grafico resta liscio. Dividendi con la stessa regola.
- **Dati già salvati**: niente bonifiche; dopo il cambio, il Sync completo scelto dall'utente rilegge la storia.
- **Prove**: AAPL 4:1 con il valore della posizione continuo attraverso il giorno dello split; uno split inverso; un
  fornitore che dà già prezzi veri non cambia nulla.
- **Ordine**: tutto in un treno (normalizzatore + lettori), altrimenti i grafici mostrano il −75 % nel giorno dello split.
  Stima 4-6 giorni (MF il fattore e il motore; X/Z il contratto dei plugin e l'ingresso; Z/J `price_query` e
  `market_series`; X dividendi e doc).

## 📐 Chiusura «rendimento totale» calcolata da noi (idea remota, 22/10/2026)

**Origine**: Z-35 (decisione del developer del 22/10): i prezzi Yahoo si chiedono senza la correzione per i dividendi
(`auto_adjust=False`) e la storia salvata si riscrive, perché la correzione di Yahoo riscala **tutte le chiusure
precedenti** a ogni nuovo dividendo e farebbe contare il dividendo due volte (nel prezzo e nella transazione).

**Idea, solo se un giorno serve** (per esempio un grafico «rendimento totale» o un confronto con un indice total return):
la chiusura corretta si calcola da sé, con il metodo standard (lo stesso di CRSP e di Yahoo). Per ogni dividendo `D` con
data di stacco `t`, fattore `f = 1 − D / P(t−1)` (`P(t−1)` = chiusura del giorno prima dello stacco); la chiusura corretta
di un giorno è la chiusura vera per il prodotto dei fattori di tutti i dividendi successivi (gli split allo stesso modo,
con fattore `1/rapporto`). Dati che servono: le chiusure vere (dopo Z-35) e i dividendi salvati come eventi dell'asset.
Il calcolo andrebbe nella casa della matematica finanziaria (`backend/app/services/financial_math/`).

**Uso nel rischio** (corsia 70, 16/11/2026). Il rischio oggi lavora «solo prezzi» (`RiskReturnBasis.PRICE_ONLY`): lo
stacco di un dividendo o di una cedola è un giorno di perdita che non c'è, e il rendimento sul periodo perde i dividendi.
La serie rettificata di questa voce lo risolve: il rischio la leggerebbe al posto delle chiusure vere, dichiarando la base
(«rendimento totale» o «solo prezzi») per asset. Il caso dei prestiti a piano (il prezzo torna al capitale a ogni cedola)
è limite e non ha un trattamento suo. Rimandato dal developer il 16/11/2026.

## ⏳ Investimento programmato con mora: la cedola di scadenza (J-39, 28/10/2026)

**Il difetto.** In un investimento programmato (provider Scheduled Investment) con **mora**, la cedola di scadenza è
contata due volte e la mora parte dal valore di prima della cedola. La liquidazione senza mora è già curata
(`5fcd7b738`).

**Cosa manca.** Decidere se, con la mora, la cedola di scadenza è pagata o no; poi correggere il calcolo (J, ~1 giorno).

**Decisione del developer (28/10/2026):** non è una priorità della 1.3, resta qui.

## 📅 Scheduled Investment — Frequenze disaccoppiate (prezzi vs cedola) + anchor day

**Data aggiunta**: 24 Aprile 2026 · **Status**: ⏳ IDEA · **Priorità**: Media (UX, non bloccante)

**Il limite.** Nel provider `scheduled_investment` la frequenza dei prezzi coincide con quella della cedola
(`maturation_frequency`), e la data della cedola dipende dalla `start_date` del periodo. Quindi un BTP con cedola semestrale
ha due punti l'anno sul grafico, e una cedola il 15 marzo e il 15 settembre non si può modellare se l'asset parte in
un'altra data.

**Cosa serve.**
- `FAInterestRatePeriod`: `price_frequency` (default DAILY), `coupon_frequency` (solo con `generate_interest=True`),
  `coupon_anchor` (`SCHEDULE_START`, `FIRST_OF_MONTH`, `LAST_OF_MONTH`, giorno del mese, giorno della settimana, data
  fissa), con la coerenza fra frequenza e anchor validata.
- Motore (`_generate_schedule_values`): due insiemi di date, `price_emission_dates` e `coupon_dates`, che possono
  sovrapporsi.
- `ScheduledInvestmentEditor.svelte`: i tre campi, con il selettore che dipende dalla frequenza.
- Nessuna migrazione Alembic: i campi stanno nel JSON `provider_params`; se `price_frequency` manca vale
  `maturation_frequency`.

**⚠️ Il valore di oggi (#R6-3).** Il ramo «dentro il ciclo» di `get_current_value` presume che cedola e punto di prezzo
coincidano: con le frequenze separate il valore sulle card può divergere dalla schedule. `get_current_value` e
`_compute_value_at` vanno ripensati insieme, applicando gli eventi in ordine cronologico.

**Test** (`test_synthetic_yield_integration.py`): parametrici su frequenze e anchor, con `current_price` in date scomode: il
giorno dopo una cedola, a metà ciclo, fra due date di prezzo, e il caso BTP (prezzi DAILY, cedola ANNUAL).

**Stima**: circa un giorno, più i test.

## 💱 Provider FX della Banca di Russia (CBR, lotto L9 sospeso)

**Data aggiunta**: 20 Novembre 2026 · **Status**: ⏸️ SOSPESO (decisione D4 del developer, 16/11/2026) · **Priorità**: ⏬ Bassa
**Origine**: corsia 75, ondata 1 (journal, `Release_2/Phase_2/75_fxCentralBanks/plan-phase02FxCentralBanks.prompt.md`,
sezione «In attesa», lotto L9, r.273). Finora parcheggiato solo nel piano.

«Niente Russia per ora»: il plugin CBR (`cbr.ru`, storia dal 01/01/1998, ~1,5 giorni) è descritto nel piano, pronto se la
decisione cambia. Intanto il RUB arriva da altre banche che lo pubblicano ancora, senza contattare `cbr.ru`: BNR, RBI e
SARB, entrati con la Q3 (b) dell'ondata 2 (19/11/2026). ECB, Norges Bank, Bank of Canada e Banca d'Italia l'hanno sospeso.

## 🏦 Borsa Italiana: la capitalizzazione delle azioni nel profilo (P-33 b, 24/11/2026)

**Data aggiunta**: 24 Novembre 2026 · **Status**: 📋 FUTURO — da ricontrollare · **Priorità**: 🔽 Bassa
**Origine**: P-33 (b) della 1.4, corsia 83 (BI-PROF). Il developer: «se non si può fare, amen, mettilo in todo_futuri
come una cosa da ricontrollare in seguito».

- **Cosa si voleva**: riempire `market_cap` del profilo di un'azione dalla capitalizzazione che la scheda di Borsa
  Italiana dovrebbe già dare, senza richieste in più.
- **Perché non c'è**: nelle registrazioni vere delle schede azioni (Enel, ASML, Apple, 10/11/2026) il campo
  `capitalizzazione` della libreria `borsa-italiana-scraping` è sempre vuoto. La libreria cerca le etichette «Market Cap
  / Capitalizzazione / Market Capitalization / Cap. di Mercato», ma la pagina azioni non le mostra, o le mostra con
  un'altra etichetta. Senza un valore mai visto non si conosce l'unità (unità o milioni): scriverlo alla cieca rischia
  un errore di un fattore un milione.
- **Da ricontrollare**: trovare su una pagina azioni vera dove sta la capitalizzazione e con quale etichetta; correggere
  la libreria (`LibreFolio_subRepo/borsaItaliana-scraping`, `scheda.py`) con un test su una pagina salvata; poi
  l'arricchitore la usa (`enricher_providers/borsa_italiana/plugin.py`, voce `market_cap`).
- Dettagli: journal, `Release_2/Phase_2/83_xtbExcel/analisi-BI-PROF.md`.


# Transazioni e import

## 🔗 Suggerimento eventi collegabili nella bulk modal (da P2-6)

**Status**: 📋 FUTURO — prima va capito se serve ancora.

**L'idea.** Nella bulk modal, una riga di notifica come quella di «promote»: se una transazione può collegarsi a un evento
dell'asset entro la tolleranza dello slider delta-days, l'utente vede i candidati e conferma.

**Cosa c'è oggi.** La rotta `POST /transactions/suggest-events` non esiste più. Il bottone «Ricollega eventi» in Transazioni
(`GET /transactions/event-reconciliation`, `EventReconciliationModal.svelte`) copre una parte del bisogno, ma cerca solo
eventi **dello stesso giorno**. Il motore sta in `backend/app/services/transactions/event_suggestions.py`
(`suggest_events_bulk`).

**Cosa resta.**
- La riga di notifica nella bulk modal, con una tolleranza in giorni.
- `AssetEventPicker.svelte` usa ancora `query_events_bulk`, senza la mappa tipo transazione → tipo evento e senza
  l'ordinamento per distanza: va portato sullo stesso motore.

## 🌙 Task notturno — dividendi e interessi senza evento collegato

**Data aggiunta**: 30 Settembre 2026 (appunto dell'11/09) · **Status**: ⏳ IN ATTESA · **Priorità**: Media

### Contesto

Insieme alla sincronizzazione notturna, un task cerca le transazioni di tipo dividendo o interesse,
più vecchie del periodo sincronizzato, **senza evento collegato**. Per ognuna cerca nell'asset un
evento compatibile in un intervallo di date configurabile (7 giorni per default).

### Azione Futura

- Se l'evento non c'è: crearlo (manuale o auto-assegnato, da decidere) e collegarlo, **oppure**
  produrre un report o una notifica che elenca le transazioni trovate con il suggerimento di
  correzione.
- Studiare se dai soli dati di una transazione si può riconoscere uno split (dubbio).
- Studiare cosa succede se l'asset cambia provider: uno nuovo che espone l'evento alla sync, o uno
  che smette di esporlo.
- Riusare il backend già pronto della sezione «🔗 Suggerimento eventi collegabili nella bulk modal
  (da P2-6)».

### Ricollegamento automatico dopo il sync (19/10/2026, decisione N68, punto 4) — 🔍 da analizzare

Nella 1.3 arrivano i primi tre punti di N68:

- il cambio di valuta di un asset non è più bloccato dagli split;
- gli split sopravvivono al cambio di valuta;
- un bottone **«Ricollega eventi»** in Transazioni elenca le transazioni senza evento, con l'evento candidato.

Il quarto resta qui, **da analizzare in un momento futuro**: dopo un sync, ricollegare **da soli** i casi certi (stesso
asset, tipo e data, un solo candidato), con un riepilogo per l'utente. La regola deve stare nel backend, non in dati
tenuti dal frontend, che si perderebbero a una ricarica o con un sync notturno.

Prima di farlo va verificato che serva davvero (developer, 19/10: «prima facciamolo funzionare, magari scopriamo che
non serve e i primi 3 sono sufficienti»). Si lega al task notturno: potrebbero diventare la stessa cosa.

## 📸 Guide d'import — schermate dei portali dei broker (C-43, parcheggiata l'11/11/2026)

Le pagine d'import di DEGIRO, Schwab, Revolut, Trading 212, eToro, Finpension, Freetrade e Coinbase hanno un segnaposto
invisibile al posto della schermata del portale. Si fanno quando un utente manda il materiale, come per Crédit Agricole,
Fineco e Trade Republic. Danske Bank ha le schermate di LibreFolio ma non quelle del portale: in attesa dell'utente.

## 📥 BRIM — riconoscere all'import una posizione chiusa (Directa, CSV generico)

**Data aggiunta**: 30 Settembre 2026 (appunto del 22/09) · **Status**: ⏳ IN ATTESA — da approfondire se ne vale la pena · **Priorità**: Bassa

### Contesto

Il flag che fa comparire nel frontend il banner «posizione importata già chiusa: la ricerca potrebbe
non dare risultati» esiste, ma oggi lo usa solo Crédit Agricole.

### Azione Futura

- **Directa**: con ETF venduti completamente, verificare se dal solo messaggio si capisce che la
  posizione si è estinta, e in quel caso alzare il flag.
- **CSV generico** (per esempio Recrowd importato in blocco): tenere traccia della quantità per
  capire quando la posizione si annulla.

## 💱 Settlement multicurrency ed esposizione — feedback 2026-09-08

**Status**: FUTURO — progettazione separata, non autorizzata come hotfix del parser.
**Origine**: nuovo feedback utente del 2026-09-08; correzioni urgenti import/asset/FX
affidate alla corsia E in un worktree separato. Qui si tracciano soltanto i tre temi
architetturali rinviati; le altre voci di questo file restano invariate.

### F-MC-1 — Acquisti multicurrency con conversione del broker “on-the-fly”

**Problema riportato:** alcuni broker convertono liquidità al momento dell'acquisto
senza una riga FX separata nel ledger. Una rappresentazione incompleta o una valuta cash
attribuita male può portare il consistency checker a rilevare cassa negativa.

**Target:** rappresentare correttamente il settlement multicurrency e, se necessario,
una policy esplicita per i broker interessati, senza perdere conservazione e audit dei saldi.

**Prima del design:** distinguere valuta della quotazione dell'asset, valuta del cash
effettivamente addebitato e valuta di regolamento. Verificare quanto il modello corrente
già supporta e quanto invece manca nel report/parser; non assumere che ogni acquisto
di un asset quotato in USD debba addebitare una cassa USD.

**Gate e rischi:** scegliere fonti e struttura delle eventuali gambe di settlement,
date, arrotondamenti e costi; mantenere quantità/importi originali e tracciabilità.
Credito/margine o permesso di saldo negativo non sono sinonimi di conversione implicita.
Niente disabilitazione del checker o deposito inventato per nascondere un deficit.

**Superfici candidate:** schemi transazione, normalizzazione BRIM/core, paired-leg
workflow, validazione saldi e wizard. Piano dedicato dopo esempi reali anonimizzati;
nessuna nuova conversione dentro il parser in questa tornata.

### F-MC-2 — Proposte FX automatiche opt-in per import Generic CSV

**Idea:** offrire un toggle che proponga transazioni collegate di cambio valuta per
deficit di liquidità spiegabili da conversioni non esplicitate nel file.

**Confine:** generazione in uno strato di preparazione/core o nel workflow di review,
DOPO la trascrizione del CSV. **BRIM resta un parser verbatim: niente FX o ricalcolo
monetario nel plugin.** Le proposte entrano nel draft normale della bulk, non in un
nuovo percorso di commit nascosto.

**Dati:** riusare il motore FX e i tassi storici disponibili (BCE quando pertinente,
con fonti/fallback già supportati), indicando data, provenance e staleness. Un tasso
stimato non va presentato come quello realmente applicato dal broker.

**Gate:** scelta esplicita di valuta/conto di finanziamento, fondi disponibili, date,
fee e rounding; preview modificabile/rifiutabile prima del salvataggio. Mancanza dati
o fondi resta un problema visibile. Reparse/riprova non deve duplicare gambe già presenti
o approvate; conservare collegamento alla motivazione e alla riga originaria.

**Dipendenza:** chiarire il modello F-MC-1 e la distinzione fra ricostruzione documentata
e simulazione assistita. Nessuna generazione FX automatica autorizzata dai bug E1-E4.

## 🏠 Funzioni in stile HomeBank, parser OFX e migrazione

**Data aggiunta**: 30 Settembre 2026 (appunto del 06/09) · **Status**: ⏳ IN ATTESA · **Priorità**: Bassa

### Contesto

Far evolvere LibreFolio verso le funzioni di HomeBank: categorie per versamenti e prelievi, i
grafici relativi e le funzioni accessorie, come il calcolatore per l'auto.

### Azione Futura

- Un plugin BRIM **OFX** generico, da usare quando manca un plugin specifico della banca.
- Uno **script di migrazione** da un file HomeBank a LibreFolio, una tabella alla volta.
- Categorie per le transazioni di cassa, con grafici dedicati.

## Approfondire protocollo Enable Banking europeo

Ascoltando online ho trovato di https://enablebanking.com/ come protocollo open per accedere alle banche europee, sarebbe interessante approfondire e capire se si esce a usare per creare un importatore "automatico" delle transazioni nel sistema BRIM

Priorità: Esplorativa

Aggiunto: 26/10/26

---

# Portafoglio e grafici

## 🏦 Regime Fiscale — Metodo di Vendita (FIFO, LIFO, PMC, Select ID)

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 🟡 IN PARTE FATTO — FIFO e LIFO nell'analisi dei lotti (1.4, progetto 69); il resto è backlog  
**Priorità**: Alta (architettura core)

> Tocca il motore dei lotti (`backend/app/services/financial_math/fifo/`): da coordinare con ogni lavoro sul cost basis.

### Cosa c'è (1.4, progetto 69)

- L'analisi dei lotti calcola **FIFO e LIFO in una richiesta** (`matching_methods`); il pannello sceglie con un selettore,
  vista iniziale FIFO, non salvata. La selezione dei lotti resta al cambio di metodo (i lotti sono gli stessi).
- Coda **per broker**; nel giorno **prima le entrate, poi le uscite**, nei due metodi; con tutti i broker nello scope il
  lotto trasferito tiene la data d'acquisto, visto da un broker solo nasce all'arrivo.
- Nessun dato salvato sui lotti, nessuna migrazione. L'AI Export resta FIFO (D7), la finestra di detenzione della
  Dashboard resta FIFO (D6), la Dashboard realizza sul costo medio.

### Contesto (la norma)

- **Italia, regime dichiarativo**: **LIFO** — art. 67, comma 1-bis, TUIR; dal 2027 art. 76, comma 2, del nuovo TUIR
  (d.lgs. 117/2026). Il FIFO non è il metodo di nessun regime italiano.
- **Italia, regime amministrato**: **costo medio ponderato** — art. 6, comma 4, d.lgs. 461/1997; dal 2027 art. 306,
  comma 5. Non è un metodo di abbinamento: le linee del costo medio esistono già.
- **USA**: FIFO, LIFO, Select ID (scelta specifica dell'utente). **Altre**: HIFO (Highest In First Out), etc.
- Punti incerti (più conti: per conto o sul contribuente; ETF e fondi; cripto) e fonti: pagina di teoria
  `mkdocs_src/docs/financial-theory/fundamentals/taxation.en.md`, sezione «Italy».

### Ancora da fare

1. **Preferenza dell'utente, impostazione per broker, default dell'admin** (D1: «poi vedremo»): legata a quale metodo
   è il default.
2. **Il LIFO nell'AI Export** (D7): legato alla stessa decisione sul default.
3. **Select ID**: il sell collegato ai buy tramite `link_transactions_id`, scelto dall'utente (vedi le note qui sotto).
4. **Rinomino** di `fifo/` e delle classi `Fifo*` (D5), in una finestra quieta, senza toccare il codice di errore.
5. **Una gamba d'arrivo che porti le date d'acquisto** (D10): oggi, visto da un broker solo, il lotto trasferito nasce
   all'arrivo.
6. **Una coda LIFO unica su tutti i broker** (D3): solo se la norma la chiede.

### Note Tecniche

- Analizzare le strade per lo split dei buy: slittare buy e connettere la parte residua, tabella di appoggio, lista di link
- Deve essere possibile identificare transazioni già importate per evitare doppio import
- Per PMC il problema del collegamento non sussiste, basta calcolare il valore on-the-fly
- I plugin BRIM in fase di vendita devono fornire un dizionario di remap con le transazioni linkate più probabili
- Il vincolo di over-sell va esteso nell'import

## 💱 L'effetto del cambio sul rendimento (FX Impact)

**Origine**: [discussione #24](https://github.com/Librefolio/LibreFolio/discussions/24#discussioncomment-18584139), un utente
curioso di vedere quanto del guadagno dipende dal titolo e quanto dal cambio. Non prioritario.

**Cosa c'è già**: il tooltip dei KPI della Dashboard separa la variazione non realizzata in effetto dell'asset ed effetto del
cambio, valuta per valuta (`period_unrealized_breakdown`), e la cassa ha la riga `fx_on_cash`.

**Cosa resta**: il realizzato, e una vista dedicata invece del solo tooltip.

## ⚡ Motore del portafoglio — caricare solo i prezzi che servono

**Data aggiunta**: 1 Ottobre 2026 · **Status**: 📋 FUTURO · **Priorità**: Media, prima va misurata

La PR [#30](https://github.com/Librefolio/LibreFolio/pull/30) ha corretto `convert_bulk` (finestra [ultimo cambio ≤ prima data,
ultima data] e `bisect`: la ricerca passa da 120–200 ms a meno di 1 ms). Una ricerca O(1) è stata valutata e scartata: meno
dell'1 %.

Lo stesso schema c'è in `backend/app/services/financial_math/portfolio/engine.py`: precarica i prezzi con solo `date <= actual_to`,
come oggetti ORM, quindi legge tutta la storia di ogni asset. `get_prices_bulk` ha già la finestra.

**Azione.**
1. Misurare su una copia dei dati reali: righe e tempo di quella query rispetto al calcolo intero, con e senza `date_from`.
2. Se conviene: limitarla a [ultimo prezzo ≤ `frame_start`, `actual_to`] con la sottoquery «ancora» della PR #30, e leggere solo
   le colonne usate.
3. Prima, verificare che nessuno chieda al resolver una data precedente a `frame_start`.
4. Test: confronto differenziale del motore prima e dopo, su più utenti e periodi; poi `services portfolio-engine`,
   `services roi-fifo-utils`, `api portfolio`.

## 📈 Grafici da un video di analisi del portafoglio

**Data aggiunta**: 27 Luglio 2026 (era `idee_per_grafici.md` nella radice, spostato qui il 14/10/2026) · **Status**: ⏳ IN ATTESA · **Priorità**: Bassa

### Contesto

Usare come base i grafici mostrati in questo video: https://www.youtube.com/watch?v=B6mLq6UUTWw

### Azione Futura

Analizzarli, poi implementarne alcuni o tutti.

## 🔍 Da approfondire: roboquants

**Data aggiunta**: 18 Ottobre 2026 (appunto del developer) · **Status**: ⏳ IN ATTESA · **Priorità**: Bassa

### Azione Futura

Capire cos'è roboquants e se può servire a LibreFolio.

## 🔍 Da approfondire: vikunja

**Data aggiunta**: 19 Ottobre 2026 (appunto del developer) · **Status**: ⏳ IN ATTESA · **Priorità**: Bassa

### Azione Futura

Valutare vikunja per tracciare le attività e i task del progetto.

## 📈 Scala logaritmica nei grafici

**Data aggiunta**: 30 Settembre 2026 (appunto del 26/09) · **Status**: ⏳ IN ATTESA · **Priorità**: Bassa

### Contesto

Una modalità di visualizzazione **logaritmica**, soprattutto sulle percentuali.

### Azione Futura

Sulle percentuali il logaritmo non si applica ai rendimenti negativi: va applicato al fattore di
crescita (1 + r). Decidere su quali grafici offrirla (Crescita, prezzo dell'asset, confronto).

**Un caso in più: l'Omega mobile** (corsia 70, 17/11/2026; journal, `Release_2/Phase_2/70_riskNext/plan-phase02RiskNext.prompt.md`,
r.343–348). Il rapporto vive intorno a 1, ma con la finestra di 30 giorni e molti giorni a rendimento zero fa picchi
veri e rari (fino a 32 e 56 nelle prove). Il consulente non li taglia: oggi la pagina utente dice di fissare la scala
dell'asse per guardare la zona vicina a 1. Un asse logaritmico renderebbe leggibili insieme la zona intorno a 1 e i picchi.

---

# Analisi del rischio

## ✅ La simulazione risponde alla finestra, non al portafoglio — superata (1.4, RN-06/RN-16)

**Misurata il 21/09/2026, superata il 20/11/2026.** Nella 1.4 (corsia 70) la simulazione legge la sua storia, non il
periodo della pagina, e la dichiara (RN-16, RN-16b); il banner beta è tolto (RN-06); il «denominatore gonfiato» non c'è più,
perché il calendario conta le quotazioni vere (journal, `Release_2/Phase_2/70_riskNext/plan-phase02RiskNext.prompt.md`, r.20–21).

## Avanzamento della simulazione Monte Carlo — si può fare, e si sa già dove è difficile

**Status**: 📋 FUTURO · **Priorità**: Medio-bassa

**Il worker sa a che punto è** su tutti e tre i rami: `resampling.py` (block bootstrap, a chunk) e `quantlib_worker.py` (GBM,
MC e QMC, per cammino). Una callback sul confine del chunk costa una chiamata per chunk e riusa una garanzia già difesa: la
riproducibilità non dipende da come il lavoro è affettato.

**Il criterio di accettazione.** Il sorteggio degli inizi di blocco e la preparazione stanno fuori dal ciclo: una barra guidata
dal contatore resterebbe a 0 % per tutta quella fase, e una barra ferma è peggio di nessuna barra. Il payload misura già i tempi
(`rng_seconds`, `process_evolution_seconds`, `generation_evolution_seconds`, `path_aggregation_seconds`): vanno letti da un
caso reale prima di scegliere la forma. Se le fasi fuori ciclo pesano, serve un avanzamento a fasi.

**Il costo vero non è il worker.**
- `SpawnWorkerPool` ha due utenti, simulazione e ottimizzazione: cambiare il protocollo le tocca entrambe.
- `query_risk` è sincrona e bulk e non ha un id di lavoro: non c'è nulla da seguire, e «la simulazione» è una delle analitiche di
  un lotto. Il lavoro vero è invertire l'API in «invia → segui», o trasmettere dentro la stessa risposta HTTP.

## 🎲 Risk Analysis — Monte Carlo avanzato: regimi calibrati e volatilità stocastica

**Data aggiunta**: 16 Settembre 2026 · **Status**: 📋 FUTURO · **Priorità**: 🔽 Bassa

La simulazione fa il livello 1 (block bootstrap) e il livello 3 (preset di regime dichiarati). Questi sono i livelli rinviati.

### Livello 2 — GJR-GARCH

Non si calibra con QuantLib (misurato su 1.43, D88): `GJRGARCHModel.calibrate()` vuole quotazioni di opzioni, `ql.Garch11` non è
esposto in Python, e `GJRGARCHProcess` ha due fattori e non entra in `StochasticProcessArray`.

**La strada**: la libreria `arch` stima un GJR-GARCH(1,1,1) su 1 250 osservazioni in 22 ms, ma oggi è solo una dipendenza
transitiva di `riskfolio-lib`. Precondizione: dichiararla nel `Pipfile`, con il lock rigenerato dal developer a corsie ferme.
Poi il lavoro è contenuto: univariato sull'aggregato del portafoglio, sul campionatore esistente.

### Preset di crisi — la forma preferita per il seguito

Il preset «crisi prolungata» usa numeri prescritti (oscillazioni ×2,5, deriva −20 % annuo). La forma preferita è il
**ricampionamento condizionato**: blocchi estratti solo dal decile peggiore della storia del portafoglio. L'ipotesi a schermo
non conterrebbe numeri dichiarati e la correlazione salirebbe perché è salita davvero.

Condizione vincolante: se la storia non contiene un periodo abbastanza severo, il risultato **lo dichiara**. Un decile peggiore
su tre anni di mercato toro non è una crisi.

### Livello 4 — Markov-switching calibrato

Regimi (calma, stress, crisi) con transizioni stimate dai dati. Rinviato perché con 3-5 anni di storia la stima EM overfitta, e
richiede `hmmlearn` o `statsmodels`. Precondizioni: storia lunga, diagnostica di stabilità dei regimi fra finestre diverse,
incertezza dichiarata.

### Livello 5 — Heston / Bates / Merton

QuantLib li supporta, ma la calibrazione vuole una superficie di volatilità implicita da opzioni, dato che LibreFolio non ha. Con
parametri inventati è sofisticazione senza contenuto: fuori scope, salvo una futura fonte di dati sulle opzioni.

## 📊 Risk Analysis — evoluzioni scenario catalog e replay

**Data aggiunta**: 29 Luglio 2026 · **Status**: 📋 FUTURO · **Priorità**: Bassa

### Catalogo scenari dinamico

Oggi il catalogo è statico, tipizzato e letto all'avvio, senza CRUD, database o watcher. Evoluzioni possibili: rilevamento
dei file senza riavvio, reload manuale, CRUD di scenari personali, modifiche dalla UI, import/export YAML, override
espliciti dei preset e diagnostica per l'admin. Da riprendere quando il catalogo statico è stabile e gli utenti chiedono di
gestire gli scenari.

### Sostituti (proxy) nel replay storico

**Decisione D372 (02/10/2026)**: «teniamoli fuori, ma segnalo in todo_futuri con tutta la spiegazione annessa». Nessun utente
l'ha chiesto.

**Cos'è.** Un asset senza storia nella finestra di una crisi (un ETF del 2015 davanti al 2008) oggi è escluso dal replay con
il suo motivo. Un sostituto è un altro asset con quella storia: il replay ne usa i rendimenti giornalieri, con il peso
dell'originale.

**Il motore è pronto**: `StressParams.proxy_assets` (fino a 100 coppie), `prepare_historical_replay_context`, l'audit e
l'avviso `historical_replay_proxies_used`. Un sostituto senza storia dà `invalid_parameters`, mai un'esclusione silenziosa.

**Cosa manca, in quest'ordine.**
1. Una regola su quale sostituto sia sensato (valuta, classe, correlazione minima): senza, un sostituto sbagliato dà un
   numero falso che sembra preciso.
2. Una diagnostica prima della scelta: quanto copre la finestra e quanto i due si sono mossi insieme.
3. ⚠️ Il buco da verificare con un test: la copertura del sostituto non passa per `replay_coverage`, quindi un sostituto
   quotato dopo l'inizio della finestra accorcerebbe il replay per tutti. Va rifiutato con il suo motivo.
4. L'interfaccia: L4 non manda mai `proxy_assets`. Un modello c'è per l'asset singolo, in `RiskAnalysisPanel.svelte`.
5. La persistenza delle associazioni per utente, sempre con una conferma esplicita.

**Quando riprenderlo**: quando un utente chiede di rigiocare una crisi con asset più giovani della crisi.

### RQMC

Priorità bassa. Da rivalutare solo se il binding Python di QuantLib espone lo scrambling. Il contratto deve tenere il seme
dello scrambling separato da `sobol_start_index`, con un oracolo di convergenza, il processo `spawn` e nessun ripiego su SciPy
in produzione.

## 💰 Rischio — rendimento totale con cedole e dividendi

**Data aggiunta**: 6 Ottobre 2026 · **Status**: ⏳ IN ATTESA · **Priorità**: Media

### Contesto

- Review del developer del 06/10/2026 con A (Dashboard, livello L3 rischio/rendimento). Testuale: «mettiamolo nei todo
  futuri e anche in un todo nel codice per non dimenticarlo».
- Oggi i rendimenti dell'analisi del rischio vengono dalle sole serie di prezzo: cedole e dividendi non entrano. Un asset
  che paga gran parte del suo rendimento come reddito sta più in basso di dove lo metterebbe il rendimento totale, e
  quando succede al benchmark la retta rischio/rendimento si inclina verso il basso.
- Il manuale lo dichiara nell'avviso «Prices only, for now»
  (`mkdocs_src/docs/financial-theory/technical-analysis/risk-metrics/benchmark-selection.en.md`, sezione
  `#the-risk-return-line`, sul ramo della famiglia Risk fino alla sua integrazione).
- Un TODO nel codice segna il punto, aggiunto dalla famiglia Risk nel giro in corso.

### Azione Futura

- Backend (Risk): una serie di rendimento totale per asset, che aggiunga ai prezzi i flussi di cedole e dividendi.
  Prima di scriverla va deciso se i flussi si reinvestono nell'asset o si sommano come cassa.
- Usarla nei calcoli di rischio/rendimento: livelli della Dashboard, pagina del broker, laboratorio di Asset Global.
- Quando arriva: togliere la riga «solo prezzi» dall'interfaccia, l'avviso dal manuale e il TODO dal codice.

## 💡 Traccia rischio/rendimento nel tempo («snail trail»)

**Data aggiunta**: 1 Ottobre 2026 · **Status**: 💡 IDEA · **Priorità**: Bassa

La proposta: con un periodo di 1A, un punto per trimestre uniti da una linea. A trimestri non regge: su un asset che non cambia, la
media annualizzata di un trimestre si scosta per puro caso di 2σ (±40 punti per un ETF azionario, ±140 per una cripto), quindi si
vedrebbe un'evoluzione che non c'è.

**La versione onesta**: solo per l'asset selezionato, a segmenti di un anno solare (il rendimento davvero ottenuto), per periodi
di almeno 3 anni, calcolata dal motore in `asset_set_risk_return`. Prima un prototipo sui dati veri. Per il rischio nel tempo
esistono già Rolling Volatility e Rolling Sharpe.

## 📉 Risk Analysis — Tracking Error / Information Ratio con benchmark selezionabile

**Data aggiunta**: 16 Settembre 2026 · **Status**: 📋 FUTURO · **Priorità**: 🔽 Bassa

`ComparisonAnalytic` li calcola già, ma sono stati tolti dalla UI: nascono per giudicare un gestore contro un mandato, e un
privato non ne ha uno. Si riabilitano solo con un benchmark vero: scelto fra gli asset del DB, persistente per portafoglio o
broker, con un avviso se valuta o storia non sono allineate, e un testo che dica che misurano lo scostamento, non la qualità.

## 🧮 Risk Analysis — Portfolio optimization / frontiera efficiente (Riskfolio)

**Data aggiunta**: 16 Settembre 2026 · **Status**: 📋 FUTURO LONTANO · **Priorità**: 🔽 Molto bassa

`PortfolioOptimizationAnalytic` è fatto e testato, ma non ha UI: si raggiunge solo via API.

**Perché è rinviato.** Non per la potenza di calcolo (0,016 s). L'ottimizzatore dà un output prescrittivo che lo strumento non
sa giustificare: preferisce gli asset con il rendimento sovrastimato, i pesi cambiano con la finestra, più asset vuol dire più
errore. LibreFolio è un tracker, non un consulente.

**Precondizioni.** Un provider con universo ampio e storia lunga; un risultato mostrato come confronto con l'allocazione
attuale, mai come «consigliata»; niente max-Sharpe in-sample, solo min-variance ed ERC; una guida su instabilità e limiti.

**Decisione aperta sulle dipendenze.** Finché non è esposto, va deciso se togliere Riskfolio-Lib, CVXPY, CLARABEL, SCS e il
pool `optimization` dall'immagine, misurando prima quanto pesano.

**Variante a basso costo.** L'ERC come diagnostica («con lo stesso rischio per asset i pesi sarebbero questi, i tuoi sono
questi»): affianca `risk_contribution`, si fa in poche righe di NumPy e non richiede Riskfolio.

## Stimatori robusti di covarianza per la matrice di correlazione (Riskfolio)

**Priorità**: 🔽 Bassa, dopo che la pagina correlazioni avrà una direzione chiara.

`riskfolio.src.ParamsEstimation.covar_matrix` offre quindici stimatori oltre a quello storico (`ledoit`, `oas`, `gerber1/2`,
`ewma1/2`, denoising…), utili con molti asset e poche osservazioni. Migliorano la qualità della stima, non il tempo
(Ledoit-Wolf 25 ms contro 0,2 ms). Se la pagina resta descrittiva, lo stimatore storico è quello onesto; se diventa
prescrittiva, uno stimatore ristretto è obbligatorio e va dichiarato nella UI.

## 🔄 Rivalutare le otto misure reimplementate da N contro riskfolio-lib

**Priorità**: Media, non blocca il rilascio.

Il developer, 18/09/2026: «Anche se è un wrapper di NumPy, è meglio usare una libreria collaudata, anche perché nel tempo, se
arrivano migliorie, le abbiamo for free».

`backend/app/services/risk/acquired.py` reimplementa misure che esistono in riskfolio (`maximum_drawdown`, `ulcer_index`,
`drawdown_at_risk`…), perché riskfolio si importa solo nel worker e le analitiche sono sincrone.

**Le domande vere.**
1. Il confine processo/worker è ancora quello giusto?
2. Quanto costa l'import (~340 MB nativi) in un processo che già carica NumPy e SciPy?
3. Le due convenzioni nostre (il segno e la baseline della serie underwater) stanno in un adattatore sottile?

La rete c'è già: `test_risk_metrics_oracle.py` confronta le due implementazioni.

🔴 **Divieto che resta** (D130/D244): `riskfolio.SemiDeviation` non è la nostra deviazione di ribasso, perché misura lo scarto
dalla propria media e non da un MAR fisso.

## 🔴 I 110 `raise ValueError` del motore di rischio — il metodo per separarli, non il risultato

**Aperto il 21/09/2026** · **Priorità**: Bassa. Il conteggio è di quella data: il 05/11 i `raise ValueError(` in `services/risk` e
`services/risk_plugins` sono 161 (allora 172). Va rimisurato alla ripresa.

**Il perimetro.** Dei 172, 62 avevano un confine chiaro (registrazione plugin, YAML, pool worker, `validate_params`, motore,
sottoprocesso); 110 finiscono nel catch-all di `service.py`. Attenzione: il grep non vede i 41 siti già instradati a un codice,
perché `RiskUnavailableError` e `RiskScopeNotFoundError` sono sottoclassi di `ValueError`.

**Il criterio è strutturale.** Leggere `Field(...)` non basta: il contratto esterno è `validate_params()` per intero, che è
funzione pura dei parametri.

| Classe | Predicato | Verdetto |
|---|---|---|
| C1 | soli parametri | va eseguito: se accetta, l'utente può causarlo |
| C2 | parametro × dato di runtime | causabile per costruzione |
| C3 | soli argomenti interni | invariante, deve esplodere |

**Il banco.** Chiamare `validate_params` ai bordi dichiarati sotto `sys.settrace` (evento `exception`, filtro su
`app/services/risk`) e correlare ogni riga colpita al `RiskErrorCode`. Riga colpita = causabile. Riga mai colpita = «non provata
raggiungibile», mai «irraggiungibile». I 110 siti ora loggano: conviene partire dalle occorrenze reali.

**Ogni guardia C2 va con il suo controllo**: una prova di rifiuto senza una prova di accettazione non dimostra la causa.

**Da non «riparare» per sbaglio.**
1. `risk.errors.undefined_metric` non ha un emettitore di produzione, ma la chiave resta nelle 4 lingue: toglierla riaprirebbe il
   ripiego silenzioso che B1(b) ha chiuso.
2. `except ValueError` in `portfolio_optimization/plugin.py` ha ancora il difetto latente corretto in `simulation/plugin.py`:
   avvolge tutta la costruzione della richiesta, quindi anche un errore del motore diventa «parametri non validi».

---

# PAC e strumenti

## 💾 Scenari salvati degli Strumenti (idea del developer, 11/11/2026)

Salvare la configurazione di un piano (PAC, Ribilanciatore) e riprenderla: un bottone alla fine, la scelta all'inizio,
anche più di uno scenario. Il calcolo resta senza stato: lo scenario è un documento dell'utente che la pagina rimanda per
intero. Tre strade (file esportato, memoria del browser, tabella sul server) e i punti aperti (dati copiati che
invecchiano, versione del contratto) in `LibreFolio_developer_journal/Release_2/Phase_2/67_rebalancer/idea-scenari-salvati-REB.md`.
Non è nel giro della 1.4.

## 💸 PAC/Rebalancer — Profili Commissionali Avanzati per Broker e Mercato

**Data aggiunta**: 15 Settembre 2026 · **Status**: 📋 FUTURO · **Priorità**: Media

Oggi il planner ha due profili indipendenti, `fee_buy` e `fee_sell`, con parte fissa, parte percentuale e minimo e massimo
facoltativi.

**Estensioni.**
- Profili per mercato, sede o classe di strumento.
- Profili degressivi che dipendono dal numero di eseguiti del giorno. Esempio Directa, per alcuni mercati: 8 € il primo, a
  scendere fino a 3 € dal 6° al 25°, 2 € dal 26° al 50°, 1,50 € dal 51°
  ([commissioni](https://www.directa.it/commissioni), 15/09/2026).
- Calendario, fuso, valuta, validità e provenienza del tariffario; regole per eseguiti parziali e ordini annullati.
- Nel solver: una tariffa legata al numero d'ordine rende il costo non separabile, quindi vanno ottimizzati anche sequenza e
  numero degli ordini.

**Gate.** Nessuna tariffa scelta senza conferma; il planner non finge di conoscere il contatore giornaliero; profilo, mercato,
data e assunzioni restano visibili; test su soglie, min/max, BUY/SELL e pareggi fra broker.

## 🧭 PAC/Rebalancer — Profili Persistenti e Strategie Estese

**Data aggiunta**: 15 Settembre 2026 · **Status**: 📋 FUTURO · **Priorità**: Media

Il Tool resta atomico: riceve sempre uno snapshot completo e non legge impostazioni salvate.

### Persistenza da valutare

- **Profilo operativo del broker**, per utente×broker (valute, modo FX, frazioni, step, min/max, fee, regime, minus pregresse):
  solo come precompilazione modificabile, mai come lookup del worker. I broker manuali restano per scenario.
- **Aliquota plusvalenze sull'asset**: un campo configurabile e versionabile, con origine e data visibili e override per calcolo.
  Default, permessi e migrazione vanno definiti prima della colonna.

### Strategie future

- Distribuzione proporzionale degli acquisti fra broker (oggi: target globali per asset e priorità delle route) e vendita
  proporzionale fra custodie.
- Chiusura di un broker e consolidamento verso uno o più broker.
- Minimizzazione delle plusvalenze, compensazione delle minus, tax-loss harvesting, bucket di minus per categoria e scadenza.
- Fee, limiti e tempi di settlement dei trasferimenti; persistenza facoltativa delle fonti manuali.

### PAC `min_fragmentation` — differita (21/09/2026)

Quarta policy di `PlannerPolicy`: la cascata obiettivo è scritta e testata in aritmetica esatta, e l'oracolo la risolve sui domini
piccoli. Manca la compilazione dello stage `split_asset_count` verso SCIP. Il rinvio è di priorità, non di disegno. Alternativa da
decidere: pesare la frammentazione per valore invece che per conteggio.

### Salvare l'analisi — sul client, non sul server (02/10/2026)

Il risultato del planner diventa un documento che l'utente stampa, salva o condivide dal suo dispositivo, senza nulla sul
server. Da decidere: stampa del browser o PDF generato nel client, contenuto (input, risultato, data, versione del contratto),
Web Share API o download, e se la modalità privacy vale anche lì.

### Gate futuri

- Nuova review matematica se cambiano input, vincoli, fiscalità, fee, FX o obiettivi.
- Nessuna compensazione fiscale senza categoria, compensabilità, scadenza, regime e perimetro broker espliciti.
- Nessun profilo salvato diventa un default silenzioso.
- Chiusura e consolidamento non introducono short, leva, BUY+SELL dello stesso asset o vendite oltre l'inventario.

### Riuso del solver discreto

PySCIPOpt/SCIP serve il planner: valutarne il riuso solo per problemi davvero misto-interi (cardinalità, lotti minimi, costi
fissi, chiusura di custodie, fee legate alla sequenza). Riskfolio-Lib resta il motore per covarianza, risk parity e frontiera;
SciPy per XIRR. Un secondo backend richiede uno spike e un vantaggio misurato.

## 🔥 Strumenti — calcolatore FIRE e riuso del motore matematico

**Data aggiunta**: 30 Settembre 2026 · **Status**: ⏳ IN ATTESA · **Priorità**: Bassa

Un plugin Tool nuovo nella pagina Strumenti (skill `tool-plugin`), con contratto Pydantic e UI compilata, come il PAC. Non solo
da oggi al futuro: anche con una data di inizio fissata, per vedere la differenza fra andamento teorico e reale. Se il motore
matematico del PAC si presta, può servire ad altri calcolatori.

---

# Piattaforma

## 🔐 Accesso con un provider OIDC esterno (SSO)

**Data aggiunta**: 30 Settembre 2026 · **Status**: ⏳ IN ATTESA — dopo Release 2 · **Priorità**: Media ·
**Issue**: [#27](https://github.com/Librefolio/LibreFolio/issues/27)

### Contesto

- Richiesta (Johan3F, 29/09): entrare in LibreFolio con il provider di identità del proprio homelab
  (Authelia, Authentik, Keycloak, Pocket ID…), senza un'altra password.
- Oggi c'è solo il login locale: username o email e password. Il login emette un JWT senza stato nel
  cookie `session`, con la durata presa dalle impostazioni globali; a ogni richiesta
  `get_current_user` ricarica l'utente e controlla `is_active` (`backend/app/api/v1/auth.py:55`).
  La registrazione è aperta solo se abilitata nelle impostazioni globali, e il primo utente diventa
  admin (`auth.py:177`).
- `hashed_password` è obbligatoria (`models.py:370`), ma la password serve solo al login: nessun dato
  è cifrato con una chiave derivata da lei.
- **Più utenti**: i permessi stanno tutti in LibreFolio (ruoli OWNER/EDITOR/VIEWER sui broker in
  `BrokerUserAccess`, `is_superuser`, impostazioni per utente) e sono legati all'id dell'utente, non
  al modo in cui entra. OIDC sostituisce solo il passo «chi sei», quindi funziona anche con più
  utenti.
- **Le risposte del richiedente** (Johan3F, 01/10, nell'issue; esperienza personale da homelab):
  - usa **Rauthy**, un provider piccolo, già funzionante con quasi tutte le sue app; si offre per i test;
  - i permessi dovrebbero venire dal provider, con claim di gruppo configurabili e default sensati: il
    provider resta la fonte di verità. Attenzione: in LibreFolio OWNER/EDITOR/VIEWER sono ruoli di
    condivisione **per broker**, non globali. Dal provider si possono prendere solo il permesso di entrare
    (un gruppo) e l'admin (`is_superuser`);
  - creazione automatica al primo accesso, configurabile; lui la sceglie sempre;
  - admin dal provider: il primo utente che entra, oppure chi ha un certo claim o gruppo;
  - il login locale di riserva per lui non serve («se il provider è giù, il problema è altrove»): resta
    un'opzione, spenta o accesa dall'admin.

### Azione Futura

- Configurazione da variabili d'ambiente: indirizzo del provider, client id e secret, scope, testo
  del pulsante. Un solo provider, ma l'identità salvata come coppia (issuer, `sub`), per non
  escluderne altri.
- Flusso Authorization Code con PKCE, `state` e `nonce`; verifica del token (firma via JWKS, issuer,
  audience, scadenza); poi lo stesso JWT di oggi, così il resto dell'app non cambia.
- DB, con una migrazione Alembic incrementale: `oidc_issuer` e `oidc_subject` unici insieme;
  `hashed_password` facoltativa per chi entra solo con OIDC.
- Frontend: pulsante «Accedi con …» nella pagina di login; cambio password nascosto a chi non ha
  una password.
- Decisioni da prendere, per il caso con più utenti:
  - creazione automatica al primo accesso, alle stesse condizioni della registrazione, ed
    eventualmente solo per i membri di un gruppo del provider;
  - collegamento a un utente locale già esistente: per email solo se il provider la dà per
    verificata, oppure dal profilo, dopo il login locale;
  - admin: gestito in LibreFolio, oppure da un gruppo del provider, riletto a ogni accesso;
  - username ed email presi da `preferred_username` ed `email`; cosa fare se sono già usati (nel DB
    sono unici);
  - login locale: tenerlo accanto, oppure spegnerlo lasciando un admin di riserva per quando il
    provider è giù;
  - un utente disattivato nel provider non entra più, ma la sessione aperta dura fino alla scadenza
    del JWT, a meno di disattivarlo anche in LibreFolio.
- Test con un provider finto; guida per l'admin con esempi (Authelia, Authentik, Keycloak, Rauthy).
- Alternativa scartata per ora: l'autenticazione fatta dal reverse proxy con un header («forward
  auth»), rischiosa se il backend è raggiungibile senza passare dal proxy.
- Stima: qualche giorno, ben delimitato; non tocca i calcoli.

## 🔒 Ripensare struttura di accesso ai broker Utente-SuperUtente per essere GDPR compliant

**Data aggiunta**: Gennaio 2026 · **Status**: 📋 PIANIFICATO · **Priorità**: Media

La visibilità dei dati degli altri utenti da parte del superuser va ripensata. Strade possibili: niente dati personali senza
consenso esplicito, log degli accessi, solo statistiche aggregate, oppure una «data request» con cui l'utente concede
l'accesso per un tempo limitato.

## 🤝 Condivisione dei broker — la stessa fetta per più utenti

**Data aggiunta**: 30 Settembre 2026 (appunto del 06/09) · **Status**: ⏳ IN ATTESA · **Priorità**: Bassa

### Contesto

Oggi ogni utente ha una sua quota di possesso sul broker. L'idea è introdurre la **fetta
condivisa**: due utenti possiedono al 100% lo stesso broker perché è la stessa fetta. Apre anche a
scenari, rari, in cui la stessa quota n% appartiene a due utenti: la vedono entrambi con la stessa
percentuale nella dashboard, e se la quota cambia la subiscono entrambi.

### Azione Futura

Modellare la fetta come entità a sé (quota → insieme di utenti), con migrazione incrementale e
compatibilità con le quote attuali. Da incrociare con la sezione GDPR sull'accesso ai broker.

## 🔄 Self-update in-app (da F14)

**Data aggiunta**: 1 Settembre 2026
**Status**: 📋 FUTURO — F14 è stato rilasciato in scope 1 (modale + guida); il self-update richiede un piano dedicato
**Origine**: discussione F14 del 01/09/2026

### Obiettivo

Pulsante nel frontend (modale "nuova versione") che fa aggiornare e riavviare il backend.

### Fattibilità analizzata

- **Docker**: un container non può aggiornare la propria immagine da solo, ma può farlo se
  `/var/run/docker.sock` è montato (opt-in in compose): Docker API → pull nuova immagine →
  ricreazione del container. È ciò che fa **Watchtower** (documentato nella guida come alternativa).
  Attenzione: docker.sock montato = root sull'host → montaggio opt-in esplicito, endpoint admin-only,
  script fisso senza input utente. LibreFolio è single-image → caso semplice.
- **Git clone**: script guardato — `git fetch`, `git pull` solo se work-tree pulito
  (`git status --porcelain` vuoto), rebuild, restart. Il restart richiede un supervisore
  (systemd o Docker restart policy). Candidato: `scripts/self_update.sh` documentato.
- Distinguere le varianti di immagine full/light se necessario (F13).

## 🗄️ Cache Server Centralizzato per Multi-Worker Uvicorn

**Data aggiunta**: 14 Aprile 2026 · **Status**: 📋 Quando si passerà a più worker · **Priorità**: Bassa

**Il problema.** Le cache in memoria (theine) sono per processo: con `--workers 1`, il default, vanno bene; con più worker
ognuno ha la sua, compresa `web_link_finder._cache`.

**Prima, o insieme: l'audit delle cache.** Il pannello «Server Caches» mostra le 16 cache con dimensione, TTL e hit: va
capito quali servono davvero, prima di investire nella condivisione. Questa voce chiede l'analisi, non la soluzione.

**Soluzione proposta (~100 righe).** Un processo cache lanciato da `lifespan()` in `main.py`, con theine dentro e un socket
Unix per i worker (`multiprocessing.managers.BaseManager`, nuovo `utils/cache_server.py`). `NamedCache` in
`utils/runtime/cache.py` delega al server solo con più worker, e i chiamanti non cambiano.

**Costi.** 200–500 μs per operazione contro ~1 μs, irrilevanti per cache di chiamate da secondi. I valori devono essere
serializzabili. Se il processo cade si perde solo la cache. Alternativa: `diskcache`, ~50 μs, ma persistente.

**Prerequisiti**: PostgreSQL e un bisogno reale di più worker (oltre 50 utenti concorrenti).

**Nota**: la Fase B di SearXNG resta archiviata, finché `ddgs` regge.

## 🧮 Gestore dei calcoli degli Strumenti come processo unico (idea del developer, 21/11/2026)

**Data aggiunta**: 25 Novembre 2026 · **Status**: 📋 In attesa, nessun lotto aperto · **Priorità**: non detta

**Il problema.** Ogni processo del server ha il suo esecutore dei calcoli (`backend/app/services/tools/executor.py`,
`ToolExecutor`): la sua coda, i suoi posti, la sua regola «un piano alla volta» per utente. Con un processo solo, come
nell'immagine Docker, va tutto bene. Con più processi (`dev.py server --workers N`) no:

- **«Continua» può arrivare al processo sbagliato.** Con «pausa e riprendi» (lotti PAUSA, non cominciati il 25/11) un
  piano resta in pausa dentro il processo che lo ha calcolato. La risposta dell'utente è una seconda richiesta, e il
  sistema operativo sceglie a quale processo darla.
- **I conti sono per processo.** Con tre processi i posti sono tre volte tanti, e «un piano alla volta» vale solo
  dentro ciascuno.
- **Ogni processo del server carica il risolutore.** Sono circa 24 MB l'uno: 81 MB col plugin, contro 57 MB col solo
  modulo dell'anteprima, misurati dal consulente su una copia del codice del 20/11. Che il server carichi il plugin
  all'avvio (`registry.auto_discover`) è letto sul codice, non misurato sul server vero.

**L'idea, con le parole del developer.**

- 21/11/2026, nella chat del consulente: «e se facessimo il calcolo come un processo singleton a parte? che viene
  istanziato quando serve dal primo a cui serve, e se qualcunaltro arriva si mette in coda? così quando tutta la coda
  si svuota il processo si auto termina e risparmia memoria, ed è compito del processo ricordare i vari calcoli
  pendenti dei vari richiedenti, anzi evitiamo di caricare le librerie pesanti ed essendo un processo diverso, se
  crasha il sistema operativo protegge il processo di libre, cosa ne pensi? è complicato da fare il motore così»
- 21/11/2026, poco dopo: «[…] per altro potremmo comunque fare che il manager è un singleton processo unico a parte,
  e i worker si collegano a lui, ma che dentro il processo unico continuiamo a usare multiprocesing per farlo in
  reale parallelismo ed evitare che se uno dei processi crasha, si perdono gli altri, cosa ne pensi?»
- 25/11/2026, riferite dal coordinatore: «per ora B, in attesa che realizziamo il processo singleton che avevo
  pianificato, credo sia già in todo_futuri, se così non fosse fallo aggiungere all'agente progettista, ne avevo
  parlato con lui»

**Cosa c'è già oggi.** Ogni calcolo gira in un processo suo, che finisce col calcolo. Se quel processo muore il
server resta in piedi e l'utente vede un errore (`worker_crashed`). Ogni calcolo ha il suo tetto di memoria
(`process_tree.py`, `OwnedProcessTree`). Manca solo il padrone unico: coda e posti (`_admit`, `_batches`) vivono
dentro ogni processo del server.

**La forma giudicata** (del consulente, sulla seconda frase del developer). Un gestore leggero, in un processo a
parte, che non calcola:

- lo avvia il primo processo del server che ne ha bisogno, e gli altri si collegano a lui;
- per ogni calcolo avvia un processo figlio, come oggi: parallelismo vero, e un calcolo che muore non porta via gli
  altri;
- si spegne da solo quando non ha più calcoli.

Un processo unico che calcola dentro di sé perderebbe il tetto di memoria per calcolo e l'isolamento dai crash.

**Cosa sostituirebbe.**

- **Il passaggio fra processi di «continua» e «va bene così»** (la strada B, sotto): ogni processo del server parla
  con lo stesso gestore, quindi il comando arriva sempre.
- **I conti per processo:** una coda, i posti e «un piano alla volta» contati una volta sola per tutta la macchina.
- **Il risolutore nei processi del server.** Questo si toglie anche senza il gestore, caricando il plugin più tardi.

**Costi e punti aperti** (del consulente). Non cambia il motore: cambia la piattaforma degli Strumenti, perché il
supervisore esce dal server e diventa un processo.

- **L'avvio:** chi lo fa partire quando due processi arrivano insieme, e come gli altri lo trovano.
- **Lo spegnimento da solo,** mentre arriva una richiesta nuova.
- **Il crash del gestore:** si perdono i calcoli in corso di tutti gli utenti. Oggi si perdono solo quelli di un
  processo.
- **Le righe d'avanzamento:** ogni processo del server deve fare da tramite fra il gestore e la pagina.
- **Tocca gli stessi file** che il lotto PAUSA-2 riscrive.
- **A chi serve:** solo a chi avvia più processi. L'immagine Docker ne avvia uno.
- **Nessuna stima.**

**Fino ad allora.** Vale la strada B, decisa dal developer il 25/11: «continua» resta una seconda richiesta; il
processo che la riceve e non ha quel calcolo la passa a quello che lo ha, sulla stessa macchina; se non ci riesce,
rifiuta, e la pagina tiene il piano mostrato. I conti restano per processo: è un limite noto, e questa è una lettura
del consulente, non una frase del developer.

**Rapporto con «Cache Server Centralizzato per Multi-Worker Uvicorn»** (osservazione del consulente). Le due voci
nascono dallo stesso fatto, più di un processo del server, e hanno la stessa forma: un processo per tutta la
macchina, a cui gli altri si collegano. Hanno anche lo stesso punto delicato, cosa succede quando quel processo cade:
lì si perde la cache, qui i calcoli in corso. Non sono un disegno solo: il cache server parte col server e resta
acceso, il gestore parte quando serve e si spegne. Conviene guardarle insieme, almeno per scegliere un modo solo di
avviare e trovare un servizio locale.

**Prerequisiti** (del consulente): «pausa e riprendi» costruita, così il gestore si disegna sul protocollo
definitivo; e un bisogno reale di più processi.

**Dove sta il dettaglio**: `LibreFolio_developer_journal/Release_2/Phase_2/67_rebalancer/plan-phase02Step7SearchTime.prompt.md`,
§3 punto 2 (le due risposte del developer e la strada B) e lotto PAUSA-2.

## ⚡ Migrazione a ORJSONResponse per performance JSON

**Data aggiunta**: 11 Giugno 2026 · **Priorità**: P4

`orjson` guadagnerebbe 20–50 ms sui payload grandi, ma scavalca il `PlainSerializer` di `SafeDecimal` e trasforma i `Decimal` in
float. Se mai si fa: una `SafeORJSONResponse` che passa da `jsonable_encoder` prima di `orjson.dumps()`, con test di output
identico sugli endpoint `SafeDecimal` e un benchmark su dati reali.

# Qualità del codice e dei test

## 🔎 Gate sui campi di contratto senza consumatore

**Data aggiunta**: 21 Settembre 2026 · **Status**: 📋 DIFFERITO · **Priorità**: Media

**Il buco.** Un campo aggiunto al contratto backend e mai letto dal frontend non dà nessun errore, né in compilazione né in
esecuzione: il contratto cresce e nulla lo dice.

**Perché differito.** Decisione del developer del 21/09: «buona idea, ma da fare solo alla fine, quando il sistema è
funzionante e si passa alla fase di condensazione e potenziamento». Oggi darebbe rumore su campi legittimamente non ancora
consumati.

**Cosa insegnano i casi trovati.** Il difetto è non controllare l'estremo, in tutte e due le direzioni:

| Caso | Forma | Esito |
|---|---|---|
| `memory` in `ToolItemMetrics` | dichiarato, mai letto | trovato per caso, da un helper tipizzato in modo generico |
| `monetary_step` | compilato dall'utente, mai letto dalla matematica | tolto con P1 |
| `ToolDocumentation.path` | letto, mai verificato | ora coperto da `check-links` |
| `RebalancerPolicy` | superato da `PlannerPolicy` | tolto |
| `pac-analyze` nel runner | registrato su file cancellati, con `check-orphans` verde | tolto |

Due di questi passavano un gate esistente: non basta chiedersi se un controllo c'è, ma da che parte guarda.

## 📏 Coverage E2E: i conteggi persi alle navigazioni piene (corsia 71, 20/11/2026)

**Data aggiunta**: 20 Novembre 2026 · **Status**: 📋 FUTURO — la prima cosa da fare per l'85 % del frontend ·
**Priorità**: 🔽 Bassa finché la percentuale del frontend non diventa un obiettivo
**Origine**: corsia 71, passo 3, «Rischi e punti aperti» punto 1 (journal,
`Release_2/Phase_2/71_openDecisions/plan-phase02Step3Coverage.prompt.md`, r.473–481); decisione D11 (b) dell'11/11.

`window.__coverage__` vive nel documento: una navigazione piena (`page.goto`, anche quella di `login()`) riparte da zero,
e la fixture legge i contatori una volta sola, alla fine. Così i colpi di una pagina prima della sua ultima navigazione
piena non si contano: il numero E2E è un po' più basso del vero, di quanto non è misurato. Il limite è già scritto nella
pagina developer `mkdocs_src/docs/developer/test-walkthrough/coverage-model.md` (riquadro «Counts before a full
navigation are lost»), che dice anche «the first thing to fix the day the frontend's percentage becomes a target».

Il disegno, per allora: `context.addInitScript` + `context.exposeBinding` (lo schema di `cspViolations` in
`frontend/e2e/fixtures/playwright.ts`) che a `pagehide` manda i contatori del documento che se ne va, con «leggi e
azzera» contro il doppio conteggio; test `JCS-10` (due documenti di fila, conteggi di entrambi). Circa 3 ore. Da provare
prima: che una chiamata di binding fatta a `pagehide` arrivi sempre a Node.

## Il generatore di dati di prova non onora i bersagli `end_price`, e lo scarto è sistematico

**Misurato il 18/09/2026** · **Priorità**: Media, non blocca nulla.

`end_price` è un'attesa, non un bersaglio: `drift_per_day` centra il valore in media sulle realizzazioni, e ogni popolamento ne
pesca una sola. Apple doveva chiudere a 185 e chiude a 264,57 (+43 %), Bitcoin a 45 000 e chiude a 25 890 (−42,5 %), Microsoft
−17,4 %: i segni discordi escludono un bias, sono le ampiezze previste dalla volatilità configurata. Gli indici invece centrano
il bersaglio, perché `_populate_benchmark_indices` normalizza.

**Il lavoro.** Decidere se `end_price` è un contratto o un'attesa e renderlo esplicito, oppure normalizzare anche le serie non
indice. Cambia i numeri di tutte le superfici: va fatto come lavoro a sé, con il confronto prima e dopo.

## 🍰 Il rischio di una parte del portafoglio (D58, D59; corsia 70, 16/11/2026)

Idea, da vedere come evolve: guardare il rischio di una sola parte del portafoglio (per esempio la parte azionaria) contro
un indice scelto per quella parte (un azionario mondiale). Posto: il laboratorio o la Dashboard, non l'Asset Detail. Il
backend c'è già: `PortfolioRiskScope.asset_ids` e `sliced_asset_ids`, pesi rinormalizzati al 100 % della fetta (D59);
manca l'interfaccia e la scelta dell'indice di confronto. In modo storico una fetta non può leggere il TWRR e usa la
composizione di oggi: va detto nella pagina.

## 📉 Tassi in salita o in discesa sul portafoglio e sul broker (corsia 70, RN-25, 18/11/2026)

**Data aggiunta**: 19 Novembre 2026 · **Status**: 📋 FUTURO — da riparlarne · **Priorità**: 🔽 Bassa
**Origine**: proposta della corsia 70 dopo RN-25; il developer: «non credo di aver capito l'idea ma appuntala, in futuro
ne riparliamo».

RN-25 porta lo scenario «tassi in salita» su un asset solo, dalla duration modificata del profilo (variazione del prezzo
≈ −D_mod × Δy, al primo ordine, tassi su o giù). La versione per portafoglio e broker è la somma pesata sulle
obbligazioni possedute. Servono una regola per le posizioni senza duration (lasciate fuori e nominate, come nel
replay) e l'indicazione di quanta parte del portafoglio la cifra copre. La convessità resta fuori finché una fonte non
la dà.

## 🪙 Prezzi piccolissimi delle cripto (corsia 76, P2c, 18/11/2026)

**Data aggiunta**: 19 Novembre 2026 · **Status**: 📋 FUTURO — da analizzare · **Priorità**: ⏬ Bassissima
**Origine**: domanda 8 del recap del 17/11; il developer: «per ora appuntiamocelo e mettiamolo in todo_futuro come una
cosa da analizzare a bassissima priorità».

Il database tiene i prezzi a 12 decimali. PEPE (3,5e-6) resta con 7 cifre significative, con un errore sotto 0,001 € su
un miliardo di monete; una moneta sotto 1e-12 diventerebbe 0 e sarebbe scartata, sotto ~1e-9 perde precisione. Idea
(P2c, ~0,5 giorni): un parametro «prezzo per N unità», come i pence di Yahoo, solo per le monete sotto ~1e-9.

**Aggiornamento del 20/11/2026.** Il developer: «si ok prevediamolo e documentiamolo per quando servirà ma attendiamo a
farlo». Il lotto è deciso nella forma, non nei tempi:

- **Quando parte**: appena qualcuno tiene una moneta sotto ~1e-9 € (oggi salvata con 4 cifre o meno; sotto 1e-12 € come 0).
- **Cosa fa**: un parametro `price_per` del plugin CoinGecko (1, 1 000, 1 000 000, 1 000 000 000; predefinito 1). Il plugin
  moltiplica prezzo corrente e storia per quel numero, e `suggest_quote_base()` restituisce lo stesso numero, così la
  finestra dell'asset propone la quote base giusta: il meccanismo che c'è già per i GBp di Yahoo. Esempio: «prezzo per
  1 000 000» salva 3,514249 invece di 0,000003514249, e il valore resta quantità ÷ 1 000 000 × prezzo.
- **Dettagli**: il lotto P2c nel piano della corsia 76 (journal, `Release_2/Phase_2/76_cryptoPrices/`).

## 🖼️ Le icone dei provider servite da LibreFolio (corsia 76, 20/11/2026)

**Data aggiunta**: 20 Novembre 2026 · **Status**: 📋 FUTURO · **Priorità**: 🔽 Medio-bassa
**Origine**: domanda 4 delle decisioni aperte della corsia 76; il developer: «non è un idea da scartare, ma ogni tanto
dovrebbe aggiornare le icone, o meglio verificare se sono cambiate, ma non la farei ora».

Oggi le icone dei provider (i favicon di Yahoo, justETF, CoinGecko, delle banche centrali) e i loghi delle monete sono
indirizzi dei siti delle fonti: ogni browser che li mostra chiede a quei siti. Idea: LibreFolio le scarica, ne tiene una
copia e le serve lui, dallo stesso indirizzo dell'istanza.

- **Cosa risolverebbe**: la privacy verso i siti delle fonti; i siti che vietano di mostrare le loro icone altrove
  (`Cross-Origin-Resource-Policy: same-origin`, come Banca d'Italia, oggi servita da una copia fissa); e la copia di
  Banca d'Italia stessa, che non si aggiorna mai.
- **Il punto del developer**: ogni tanto verificare se un'icona è cambiata (per esempio confrontandone l'impronta), e
  sostituire la copia solo allora.
- **Cosa costa**: lo scaricamento, una cache, i limiti di dimensione e di formato, e una protezione dagli indirizzi
  malevoli (SSRF: l'indirizzo di un'icona lo dà un plugin).
- **Dettagli**: il piano della corsia 76 (journal, `Release_2/Phase_2/76_cryptoPrices/`, le decisioni del 20/11) e il
  triage delle icone a puzzle (journal, `76_cryptoPrices/notes/icons-triage/`).

## 🔍 Da approfondire: XERJ, ricerca locale per gli agenti

**Data aggiunta**: 16 Novembre 2026 (decisione del developer) · **Status**: ⏳ IN ATTESA che diventi stabile ·
**Priorità**: Bassa

**Cos'è.** [xerj-org/xerj](https://github.com/xerj-org/xerj) (Apache-2.0, Rust, un solo binario): indicizza cartelle (codice
con tree-sitter, Markdown, log, CSV/JSON, PDF) e restituisce brani con `file:riga` (BM25, vettoriale, ibrida); server MCP
(`xerj mcp`) e API compatibile Elasticsearch su `localhost:9200`. Corpus Hub (hub.xerj.org) con raccolte pronte. Ci hanno
chiesto di usare commit di LibreFolio come esempi (il developer ha detto sì; LibreFolio è AGPL-3.0: la raccolta deve citarla).

**Perché aspettare.** Al 16/11/2026 è ancora `v1.0.0-rc.102` (≈250 issue aperte, benchmark solo loro); dalla rc.101 i binari
contengono crate proprietari (Query-1, opzionale), per restare solo Apache va compilato dai sorgenti.

**Dove servirebbe.** Sul nostro codice si sovrappone a graphify e grep. Il guadagno è altrove: cercare in progetti di
riferimento (Ghostfolio, Portfolio Performance, librerie FX e cripto) prima di scrivere codice, e cercare nel journal, che
graphify non copre. Costo: zero soldi in locale (niente Jev, che manda i risultati a un servizio esterno), un processo in
più, qualche centinaio di MB di indici.

**Quando ripreso.** Prova breve su una copia: indicizzare repository e journal, cinque domande vere confrontate con
graphify/grep (tempi e token), poi decidere se registrarlo come MCP del progetto.

---

# Idee

## 💡 Idee sparse (dopo aver visto i concorrenti)

- Provider di prezzo: oltre al CSS selector (da rinominare «web page»), anche JSON API, tabella HTML e CSV.
- Provider AI: oltre a Ollama e OpenRouter, gli altri per l'installazione locale.
- Addon che aggiungono tab al frontend, con un marketplace.
- Nuovi tab di analisi in Dashboard e broker, da definire.
- «Portafogli»: gruppi di broker, di asset o di entrambi. Si lega a #52, nel «Profilo dei dati dell'asset».
- Pagine di dettaglio per analizzare trade e fee.

# Residui della 1.3 (10/11/2026)

Voci trovate aperte nella verifica di chiusura della 1.3 e rimandate a quando servono (decisione del developer, 10/11).
Dettagli nel journal, `Release_2/Phase_2/DA-DECIDERE-residui-1.3.md`.

- **Prova vera della connessione** (H-38, H-40): Docker Desktop, Tailscale Serve e IPv6 su una macchina vera. La guida c'è.
- **PAC `worker_crashed` sotto carico** (J-19): la strumentazione è pronta (`tools/executor.py`), la causa non si è mai
  vista. Se ricapita, si guarda il log.
- **Variazione del giorno in euro per posizione**: nella tabella delle posizioni, accanto a quella in percentuale.
- **Colori degli indicatori per tema** (S9): `SIGNAL_DEFAULT_PALETTE` è uguale nel tema chiaro e in quello scuro.
- **Base media nel tempo** al posto di MF-A11, per i rendimenti sul capitale (MF, seguito 1).
- **Lotti e report sulla quota dell'Owner** (MF, seguito 3): oggi l'analisi dei lotti non legge la quota.
- **Selettore dell'icona del broker** (C-40).
- **`SearchSelect` che sceglie la voce sbagliata dopo una ricerca**: sospeso finché non ricapita.
- **Traduzioni dei plugin montati a runtime** (U-B1): facoltativo, oggi c'è il ripiego in inglese.
- **Crédit Agricole, ruolo `portfolio`** (W5-7 gradino 7): le verifiche di posizione e liquidità dal file «Andamento
  Portafoglio». Si fa quando arriva un file d'esempio; il resto del plugin 2.0.0 è nella 1.3.
- **Immagine d'avvio su iPhone** (K-6): `app.html` non ha `apple-touch-startup-image`; serve un'immagine per formato.
- **Quadrato nero sull'icona Android** (K-7): prima una prova sul telefono.
- **I filtri della lista asset persi al ritorno** (K-19): decisione del 06/10, dopo la lista del Rischio.
- **Catene FX e provider** (O-19): `leg_rates` ha la chiave `(base, quote, data)` senza provider (`fx/sync.py:75`), quindi
  due provider della stessa coppia nella stessa sync si sovrascrivono. Mai visto: prima un test di caratterizzazione.
- **Valuta dei dividendi eToro** (C-6): presa dal ticker (`broker_etoro/plugin.py:256`); serve un export vero con `KER/EUR`.

## 🧵 Python con thread davvero paralleli (C-60, 10/11/2026)

Non interessa una versione di Python in sé, ma **la prima che abilita davvero, di default, l'esecuzione parallela dei
thread**, cioè senza il global interpreter lock attivo. Finché il lock resta acceso di default, aggiornare il codice non
porta niente: si resta sulla 3.13. Quando arriverà, si misura il guadagno sui lavori pesanti (sync, report, rischio)
prima di migrare. La ricerca del 12/10 su Python 3.15 è nel journal, `phases/38_postReleaseBacklog/`.
