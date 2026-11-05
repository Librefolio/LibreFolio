# TODO FUTURI

Questo file documenta miglioramenti futuri, migrazioni pianificate, e note tecniche importanti per il progetto LibreFolio.
I TODO completati sono in `TODO_Completati.md`.

---

## ⏳ Investimento programmato con mora: la cedola di scadenza (J-39, 28/10/2026)

**Il difetto.** In un investimento programmato (provider Scheduled Investment) con **mora**, la cedola di scadenza è
contata due volte e la mora parte dal valore di prima della cedola. La liquidazione senza mora è già curata
(`5fcd7b738`).

**Cosa manca.** Decidere se, con la mora, la cedola di scadenza è pagata o no; poi correggere il calcolo (J, ~1 giorno).

**Decisione del developer (28/10/2026):** non è una priorità della 1.3, resta qui.

## 🧬 Profilo dei dati dell'asset — composizione, costi, obbligazioni, esposizione e nuove fonti

**Data aggiunta**: 18 Ottobre 2026 · **Status**: 📋 FUTURO — da progettare · **Priorità**: 🔼 Medio-alta
**Origine**: fusione di F16 (feedback Giuseppe + Alfy, 07/08/2026), F-MC-3 (feedback utente 08/09/2026), le voci
C-86 e C-87 del backlog (utente C, chat del 04/09), due note sciolte (extraETF, aziende) e le richieste GitHub
#50, #51 e #52 di @Xgialippo (17/10/2026). Skill di riferimento: `asset-plugin`.

### Perché un punto solo

Più utenti chiedono informazioni diverse sugli stessi asset: il TER, la composizione degli ETF per azienda, i dati
delle obbligazioni, la valuta base e l'esposizione valutaria. Aggiungerle una colonna alla volta non scala: serve
un'architettura unica, pensata bene prima di scrivere codice.

### Direzione (da progettare)

- **Un profilo per asset**, fatto di due cose:
  - **fatti tipizzati**, ciascuno con fonte, data di riferimento e data di lettura: TER, emittente, dimensione del
    fondo, replica, copertura valutaria, valuta del fondo, domicilio, indice replicato, data di lancio, frequenza di
    distribuzione; per le obbligazioni cedola, scadenza, rendimento a scadenza (YTM) e duration (ex C-87: cambiano
    nel tempo e vanno salvati con la loro data; da decidere se leggerli da un provider o calcolarli in
    `backend/app/services/financial_math/`);
  - **distribuzioni**: paesi, settori, valute, aziende, classi di attivo. Il modello esiste già per paesi e settori
    (`FAGeographicArea`, `FASectorArea`): va esteso, con la data e una quota «Sconosciuta».
- **Ogni plugin dichiara** quali fatti e distribuzioni sa fornire. Una **libreria interna di arricchimento** (l'idea
  di F16: usata dai plugin dei prezzi, invece di un plugin a parte) li unifica e ne conserva la provenienza.
- **Le aggregazioni sul portafoglio le calcola il backend**: TER medio pesato sul valore (#51), esposizione per
  azienda (#50), esposizione valutaria vera.
- **Identità delle aziende** (per l'esposizione per azienda): «Apple» e «Apple SRL» devono risultare la stessa
  azienda → identificatori univoci (ISIN per le quotate), normalizzazione dei nomi, regole di confronto e intervento
  manuale per i casi ambigui.
- **Valuta base ed esposizione valutaria** (ex F-MC-3):
  - valuta di quotazione, valuta base dello strumento ed esposizione economica sottostante non sono la stessa cosa.
    Un ETF sul Giappone non implica valuta base JPY né esposizione JPY pura: posizioni, classe di quote e coperture
    valutarie cambiano il risultato;
  - una colonna per la valuta base SOLO con semantica e fonte chiare; per l'esposizione effettiva serve una
    distribuzione valutaria look-through, con data, copertura e quota «Sconosciuta», non un codice dedotto dalla
    geografia;
  - grafico in Dashboard con metodo e denominatore dichiarati, cassa e posizioni trattate in modo coerente, dati
    incompleti visibili, nessuna falsa precisione. Prima un disegno ASCII e la decisione del developer, poi una
    revisione su esempi sintetici multi-valuta e coperti;
  - **la variazione non realizzata** (developer, 12/10/2026, voce 23): oggi il tooltip dei KPI della Dashboard
    (`period_unrealized_breakdown`, `KpiSection.svelte`) separa, valuta per valuta, l'effetto dell'asset da quello del
    cambio, ma ragiona solo sulla valuta di quotazione. Con la valuta base dovrà usare anche lei: con il cambio dalla
    valuta di quotazione a quella base, se la coppia è configurata, si vedrà quanta parte del movimento viene dal
    cambio e quanta dall'asset.
- **UI**: nella pagina dell'asset i fatti e le distribuzioni con fonte e data; nella Dashboard il TER del portafoglio
  e le esposizioni, con il metodo dichiarato.

### Prime idee d'uso dei dati in comune

- **TER del portafoglio** (GitHub #51, @Xgialippo, 17/10/2026): il TER di ogni ETF in tabella, e il **TER medio del
  portafoglio pesato sul valore delle posizioni**. È il primo esempio di come usare i dati del profilo: un fatto
  per asset, aggregato sul portafoglio dal backend. Risposta all'utente il 18/10: arriva dopo aver ragionato bene e
  creato l'ambiente centralizzato delle informazioni degli asset.
- **Portafoglio diviso per obiettivi** (GitHub #52, @Xgialippo, 17/10/2026; qui dal 22/10, decisione del developer):
  raggruppare gli asset per obiettivo («i pilastri di Coletti»: fondo emergenze, pensione…), con sottogruppi o tag, e
  filtrare la Dashboard per gruppo. Oggi la Dashboard si filtra solo per broker. Si lega all'idea dei «Portafogli»,
  gruppi di broker, di asset o di entrambi (più sotto, tra le idee sparse). Domande poste all'utente il 18/10, ancora
  senza risposta: un asset sta in un solo obiettivo o si divide (a quote o a lotti)? gruppi di broker, di asset o
  tutti e due? cosa vedere per ogni portafoglio (Dashboard filtrata, KPI e allocazione propri, allocazione obiettivo
  per il PAC)? Registro: `PROSSIMI_LAVORI.md`, #52.
- **Lo stesso principio, da applicare ad altre voci una volta identificate**: un fatto per asset, pesato sul valore
  delle posizioni (o raggruppato), con la quota dei dati mancanti dichiarata. Candidati da valutare quando si progetta:
  - per le obbligazioni, il rendimento a scadenza e la duration medi del portafoglio;
  - le esposizioni per emittente del fondo, per tipo di replica, per domicilio, per copertura valutaria, per politica
    di distribuzione;
  - le distribuzioni (paesi, settori, valute, aziende) già aggregate sul portafoglio, invece che asset per asset.
- **Gate**: fonte e aggiornamento dei metadati, normalizzazione, dati mancanti visibili, FX; colonne o tabelle nuove
  solo con migrazioni Alembic incrementali.

### Dati estraibili oggi (verificati il 18/10/2026)

- **justETF** (`justetf_scraping.get_etf_overview`, tipo `EtfOverview`): `isin`, `name`, `description`, `index`,
  `investment_focus`, `fund_size_eur`, `ter`, `replication`, `legal_structure`, `strategy_risk`, `sustainability`,
  `fund_currency`, `currency_hedged`, `volatility_1y`, `inception_date`, `distribution_policy`,
  `distribution_frequency`, `fund_domicile`, `fund_provider`, `top_holdings`, `holdings_date`, `countries`,
  `sectors`. Il plugin oggi usa solo `description`, `ter` (come testo nella descrizione), `distribution_policy`,
  `countries` e `sectors`.
- **Yahoo** (`yfinance` 1.7.0, `Ticker(...).funds_data`): `top_holdings` (prime 10 con peso), `sector_weightings`,
  `asset_classes`, `bond_holdings`, `bond_ratings`, `fund_operations` (con il TER, «Annual Report Expense Ratio»),
  `fund_overview` (emittente, categoria, tipo legale), `description`. Non dà la ripartizione per paese. Provato su
  VOO, SWDA.MI, VWCE.DE, CSPX.L, IWDA.AS, EUNL.DE: prime 10 e settori per tutti, TER per 5 su 6 (manca VWCE.DE).
  La parte che LibreFolio già supporta va subito nel plugin: vedi
  `LibreFolio_developer_journal/Release_2/Phase_1/PROSSIMI_LAVORI.md`, #50.
- **Borsa Italiana**: da verificare quali dati del profilo espone oltre al prezzo.
- **Cataloghi e identificativi** (idea F16): ESMA FIRDS
  (`https://registers.esma.europa.eu/publication/searchRegister?core=esma_registers_firds_files`, file «full»
  dell'ultima settimana) e OpenFIGI per arricchire gli ISIN. Twelve Data sarebbe ideale ma è a pagamento.

### Possibili prossime fonti

- **extraETF**: anche la distribuzione valutaria, che si sposa con la valuta base del fondo.
- **Investing.com** e **TradingView**: nessuna API ufficiale, e i termini vietano la lettura automatica anche agli
  abbonati. Un plugin a scraping è possibile ma fragile. **Bassa priorità**, salvo che portino titoli, o meglio classi
  di titoli, che Yahoo, justETF e Borsa Italiana non coprono.
- **Fornitori a pagamento con la chiave dell'utente**: EODHD Fundamentals, Financial Modeling Prep, Finnworlds;
  Morningstar o LSEG a livello aziendale. Danno TER e posizioni dei fondi per ISIN, con un contratto che lo permette.
  Le impostazioni dei plugin con segreti per utente o per istanza ci sono già (1.3, migrazione 007).
- **Interactive Brokers** (ex C-86): prezzo corrente e storico letti con le API e la chiave dell'utente; serve un
  account per le prove. Dettagli:
  `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/feedback-early-user-C-20261014.md`, voce 4.

### Licenze e uso commerciale

- justETF (AGB §3.1: niente «programmi per l'interrogazione automatica dei prezzi»), Borsa Italiana/Euronext e Yahoo
  limitano l'uso automatico dei loro dati.
- In self-hosted ogni istanza interroga per il suo utente, a basso volume e senza ridistribuire: rischio basso, tollerato
  nei fatti.

### Collegamenti

- Piano in pausa: `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00AssetIdentityAndIdentifiers.prompt.md`
  (identità asset, identificativi).
- `LibreFolio_developer_journal/Release_2/Phase_1/PROSSIMI_LAVORI.md` (#50, #51, #52).
- Backlog `BACKLOG_POST_1.2.md`: C-86, C-87, spostate qui.
- Qui sotto, «💱 Settlement multicurrency ed esposizione»: F-MC-1 e F-MC-2 restano lì.

---

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

---

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

---

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

## 🔒 Ripensare struttura di accesso ai broker Utente-SuperUtente per essere GDPR compliant

**Data aggiunta**: Gennaio 2026  
**Status**: 📋 PIANIFICATO → Architettura definita in `plan-phase05-to-08-upgrade.md` §10 (GDPR/Sharing)  
**Priorità**: Media

### Contesto

La visibilità dei dati di altri utenti da parte del superuser deve essere ripensata per essere GDPR compliant.

### Possibili Approcci

- Superuser non vede dati personali di altri utenti senza consenso esplicito
- Log di accesso ai dati di altri utenti
- Anonimizzazione dei dati visualizzati (solo statistiche aggregate)
- Meccanismo di "data request" invece di accesso diretto (utente concede accesso all'assistenza per x tempo)

---

## 🏦 Regime Fiscale — Metodo di Vendita (FIFO, LIFO, PMC, Select ID)

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Alta (architettura core)

> **Cross-link**: stesso motore FIFO (`fifo_utils.py`) del TODO "BRIM: FEE/TAX non collegati all'asset" qui sopra — entrambi toccano come i lotti calcolano il proprio cost basis. Da coordinare se pianificati insieme.

### Contesto

Diverse giurisdizioni usano metodi diversi per determinare quale lotto vendere in caso di vendita parziale:

- **Italia**: Prezzo Medio di Carico (PMC)
- **USA**: FIFO, LIFO, Select ID (scelta specifica dell'utente)
- **Altre**: HIFO (Highest In First Out), etc.

### Requisiti

1. **Impostazioni Broker**: Nella zona short/long del broker, selettore per il metodo di vendita supportato (FIFO, LIFO, PMC, Select ID)
2. **Preferenze Utente**: Impostazioni di default per metodo di vendita
3. **Impostazioni Admin**: Default globale per nuovi utenti
4. **Collegamento Transazioni**: Il sell deve essere collegato ai buy tramite `link_transactions_id`:
   - FIFO/LIFO: collegamento algoritmico
   - Select ID: scelto dall'utente
   - PMC: nessun collegamento (calcolo on-the-fly)

### Note Tecniche

- Analizzare le strade per lo split dei buy: slittare buy e connettere la parte residua, tabella di appoggio, lista di link
- Deve essere possibile identificare transazioni già importate per evitare doppio import
- Per PMC il problema del collegamento non sussiste, basta calcolare il valore on-the-fly
- I plugin BRIM in fase di vendita devono fornire un dizionario di remap con le transazioni linkate più probabili
- Il vincolo di over-sell va esteso nell'import

---

## 💸 PAC/Rebalancer — Profili Commissionali Avanzati per Broker e Mercato

**Data aggiunta**: 15 Settembre 2026
**Status**: 📋 FUTURO — estensione successiva al primo planner operativo
**Priorità**: Media

**Target v1 correlato:** [suite PAC/Rebalancer — piano maestro](LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerTargetDesign.prompt.md).

### Confine della Prima Versione

Il primo planner PAC/Rebalancer deve mantenere due profili indipendenti,
`fee_buy` e `fee_sell`. Ciascuno supporta:

- componente fissa;
- componente percentuale sul controvalore;
- minimo e massimo opzionali per la componente percentuale;
- valore `0` valido.

Questa separazione copre i PAC con acquisti gratuiti e vendite soggette alle normali
commissioni. Non implica ancora regole diverse per mercato o formule dipendenti dalla
sequenza giornaliera degli ordini.

### Estensioni Future

- Override dei profili per mercato, sede di negoziazione o classe di strumento.
- Profili dinamici/degressivi nei quali la fee dipende dal numero progressivo degli
  eseguiti nella giornata.
- Calendario, timezone, valuta, data di validità e provenance del tariffario.
- Regole esplicite per eseguiti parziali, ordini annullati e conteggi condivisi fra
  mercati/strumenti.
- Integrazione nel solver: una tariffa dipendente dal numero d'ordine rende il costo
  non separabile e richiede di ottimizzare anche sequenza e numero degli ordini.

Directa documenta, per alcuni mercati, un profilo dinamico giornaliero che parte da
8 EUR sul primo eseguito, scende progressivamente fino a 3 EUR dal 6° al 25°, passa a
2 EUR dal 26° al 50° e a 1,50 EUR dal 51°; disponibilità e valori dipendono dal mercato.
Questa famiglia di policy non rientra nella prima versione.

### Gate Futuri

- Nessuna tariffa implicita o scelta automaticamente senza conferma utente.
- Distinguere ordine pianificato da eseguito reale: il planner non deve fingere di
  conoscere il contatore giornaliero.
- Mostrare profilo, mercato, data e assunzioni usate nel costo stimato.
- Testare discontinuità delle soglie, min/max, BUY/SELL e pareggi fra Broker.

### Riferimenti

- [Directa — Commissioni](https://www.directa.it/commissioni), consultato il
  15 settembre 2026.

---

## 🧭 PAC/Rebalancer — Profili Persistenti e Strategie Estese

**Data aggiunta**: 15 Settembre 2026
**Status**: 📋 FUTURO — fuori dal primo planner operativo
**Priorità**: Media

**Target v1 correlato:** [suite PAC/Rebalancer — piano maestro](LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerTargetDesign.prompt.md).

### Confine della Prima Versione

La prima versione mantiene nello snapshot del singolo calcolo:

- parametri operativi dei Broker;
- fee BUY/SELL;
- supporto agli ordini frazionati e relativo step monetario;
- regime fiscale e minusvalenze pregresse;
- aliquota sulle plusvalenze per Asset, pre-popolata al `26%` e modificabile;
- route Asset×Broker e priorità;
- trasferimenti dichiarati, gratuiti e immediati;
- FX single-hop, con lo spread globale. ~~`fx_buffer_rate` esplicito (label UI “Margine di sicurezza FX”)~~ —
  ❌ **non più da fare**, decisione del developer del 02/10/2026: non esiste e non esisterà (vedi «Non più da
  fare» più sotto).

Questi dati non diventano automaticamente impostazioni persistenti. Il Tool resta
atomico e riceve sempre uno snapshot completo.

### Persistenza da Valutare

1. **Profilo operativo personale del Broker**
   - salvare per utente×Broker valute operative, FX mode, supporto frazioni,
     step monetario, min/max, fee BUY/SELL, regime e minus pregresse;
   - usare il profilo solo come prefill modificabile del singolo scenario;
   - non trasformarlo in un lookup del worker Tool;
   - mantenere i Broker manuali scenario-only salvo futura azione di salvataggio
     esplicita.
2. **Aliquota plusvalenze sull'Asset**
   - aggiungere un campo Asset configurabile e versionabile;
   - pre-popolare il planner dal dato persistito, con origine/data visibili;
   - mantenere override per-run;
   - definire default, permessi, provenienza e migrazione prima di aggiungere la
     colonna.

### Strategie Future

- Distribuzione proporzionale esplicita degli acquisti fra più Broker.
- Vendita proporzionale dello stesso Asset fra più custodie.
- Chiusura Broker: svuotamento controllato di una custodia.
- Consolidamento: trasferire il portafoglio verso uno o più Broker scelti.
- Minimizzazione delle plusvalenze realizzate.
- Compensazione di minusvalenze pregresse con plus compatibili.
- Tax-loss harvesting e minimizzazione del realizzo fiscale.
- Bucket di minusvalenze per categoria, compensabilità e scadenza.

#### PAC `min_fragmentation` — differita (decisione developer, 21/09/2026)

**Status**: 📋 DIFFERITA — non entra nella prima versione operativa.

Quarta policy dichiarata nel contratto (`PlannerPolicy`,
`backend/app/services/pac_allocator/models.py`) e **già specificata**: la sua
cascata obiettivo esiste ed è scorata in aritmetica esatta
(`evaluator.py`, ordine `fixed_l2 → shortfall → split_asset_count →
active_order_rows → route_priority → explicit_cost`). Oggi è risolvibile
**provatamente** dall'oracolo esaustivo sui domini piccoli; manca solo la
compilazione dello stage `split_asset_count` verso SCIP, quindi
`compiler._require_supported_scope` la rifiuta.

**Perché è differita e non "da progettare"**: la funzione obiettivo non è una
domanda aperta — è scritta e testata. Il rinvio è di priorità: la decisione
developer del 21/09 mette il **Rebalancer completo** davanti a tutto, perché il
PAC ne è il caso particolare a distribuzione iniziale nulla.

**Se si volesse ridiscutere l'obiettivo**: `split_asset_count` minimizza il
numero di Asset spezzati fra più route. Un'alternativa sensata sarebbe pesare la
frammentazione per valore anziché per conteggio, così che spezzare un Asset da
10 € non costi quanto spezzarne uno da 10 000 €. È una proposta, non una
raccomandazione: richiede una decisione di prodotto.

### Modello Operativo Futuro

- Fee, limiti e tempi di settlement dei trasferimenti.
- ~~Route FX multi-hop, solo con protezioni anti-ciclo e anti-arbitraggio.~~ ❌ non più da fare nel PAC (02/10/2026).
- ~~Buffer FX dinamico per Asset/volatilità invece del solo `fx_buffer_rate`
  esplicito.~~ ❌ non più da fare (02/10/2026).
- Persistenza opzionale delle fonti manuali.

### Salvare l'analisi — sul client, non sul server (richiesta del developer, 02/10/2026)

**Status**: 📋 FUTURO · **Priorità**: da stabilire

Il developer, testuale (riportato dal workstream D): *«salvare l'analisi: stampa PDF e condivisione/salvataggio sul
client, non sul server»*.

- **Cosa**: il risultato del planner (KPI, esposizioni, piano operativo, prova) diventa un documento che l'utente
  stampa in PDF, salva o condivide dal proprio dispositivo.
- **Vincolo**: niente salvataggio sul server. Il Tool resta atomico e senza stato (vedi «Confine della Prima
  Versione»): l'analisi vive solo sul client.
- **Da decidere alla ripresa**:
  - il formato: la stampa del browser con un foglio di stile dedicato, oppure un PDF generato nel client;
  - il contenuto: gli input dello scenario, il risultato, la data e la versione del contratto;
  - la condivisione: la Web Share API dove esiste, altrimenti il download;
  - la privacy: il documento contiene importi reali, quindi va deciso se la modalità privacy vale anche lì.

### Gate Futuri

- Nuova review matematica se cambiano input, vincoli, fiscalità, fee, FX o
  obiettivi.
- Nessuna compensazione fiscale senza categoria dello strumento, regole di
  compensabilità, scadenza, regime e perimetro Broker espliciti.
- Nessun profilo persistito può diventare un default silenzioso: provenance,
  data e override per-run restano visibili.
- Le strategie di chiusura/consolidamento non possono introdurre short, leverage,
  BUY+SELL dello stesso Asset o vendite oltre inventario.

### Riuso futuro del solver discreto — senza migrazione Riskfolio

PySCIPOpt/SCIP è il candidato additivo approvato per il planner fixed-L2
(primo tier MIQP, tier lessicografici successivi convex-MIQCP); la dipendenza non
è ancora installata e resta subordinata al freeze coordinato, all'update
developer-owned/autorizzato e ai gate packaging/capacità. Dopo l'adozione
effettiva, valutarne il riuso solo
per nuovi problemi realmente misto-interi: cardinalità, lotti minimi, turnover,
costi fissi, distribuzione proporzionale BUY/SELL fra Broker, chiusura o
consolidamento di custodie, strategie fiscali discrete, fee dipendenti dalla
sequenza e routing operativo di trasferimenti, settlement e FX.

Riskfolio-Lib resta il motore di dominio per covariance, risk parity, frontiera
efficiente e analisi rischio; SciPy resta disponibile per XIRR e calcolo numerico.
Non reimplementare queste funzioni per eliminare una dipendenza. Un eventuale
secondo backend richiede spike separato, parità completa degli output esistenti e
benchmark che dimostri un vantaggio misurabile di capacità, latenza o memoria.

---

## 🤖 QuarkAI — Assistente AI (MCP Server)

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Bassa (futuro)

### Contesto

Creare un assistente AI basato su MCP server chiamato "QuarkAI".

### Funzionalità Future

- Raccolta automatizzata notizie mercati azionari
- Notifiche su Telegram (o simili) quando rileva eventi che richiedono attenzione
- Recap giornaliero (es. alle 20:00) con sommario eventi rilevanti

---

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

## ⚖️ Asimmetria della piattaforma Tool sull'assenza

**Data aggiunta**: 21 Settembre 2026 · **Status**: 📋 OSSERVAZIONE · **Priorità**: Bassa

Il backend vieta un servizio senza operazioni (`ToolDescriptor.operations`, `min_length=1`): il tool sparisce dal catalogo. Il
frontend invece descrive un tool senza UI (`renderer_missing`), con un messaggio tradotto. Per questo due tool a metà hanno
due destini diversi. Nessuna delle due scelte è sbagliata: se un giorno si vuole uniformare, è qui che si guarda.

## 💰 Futura policy cedola (coupon_policy)

**Data aggiunta**: 3 Aprile 2026 (Round 12 Finale)
**Status**: 📋 IDEA FUTURA
**Priorità**: Bassa

### Concetto

Colonna `coupon_policy` su `FAInterestRatePeriod` con opzioni:

- **FULL_RESET** (attuale): torna a `initial_value` dopo coupon
- **CUSTOM_RATE**: tasso cedola diverso dal tasso di accumulo
- **PARTIAL**: percentuale del valore accumulato

Per ora solo FULL_RESET è implementato.

---

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

## ⚡ Migrazione a ORJSONResponse per performance JSON

**Data aggiunta**: 11 Giugno 2026
**Priority**: P4 (ottimizzazione, non urgente)
**Scope**: Backend (`app/main.py`, serializzazione)

### Contesto

`orjson` è un serializzatore JSON scritto in Rust, 5–10× più veloce di `json` stdlib per la serializzazione e 2–3× per la deserializzazione. FastAPI supporta nativamente `ORJSONResponse` come `default_response_class`.

### Problema attuale: incompatibilità con `SafeDecimal`

Il progetto usa `SafeDecimal = Annotated[Decimal, PlainSerializer(..., when_used="json")]` su tutti gli schemi di transazioni, FX e portafoglio. Questo `PlainSerializer` garantisce che i `Decimal` arrivino al frontend come stringhe senza notazione scientifica (es. `"0.00500000"` invece di `5e-3`).

**`orjson` bypassa i `PlainSerializer` di Pydantic** quando serializza direttamente, convertendo i `Decimal` in float nativi — con rischio di perdita di precisione e notazione scientifica silenziosa sul frontend.

### Come implementarlo correttamente

Non è sicuro usare `ORJSONResponse` come `default_response_class` senza prima risolvere questo punto. Le opzioni:

1. **Subclass `ORJSONResponse`** che chiama `model.model_dump(mode='json')` prima di passare a `orjson` → applica i `PlainSerializer` prima della serializzazione Rust.
2. **Custom `orjson` default function** che intercetta `Decimal` e lo serializza come stringa.
3. **Rendere `orjson` l'encoder di Pydantic v2** via `model_config = ConfigDict(json_encoders=...)` — ma deprecato in v2.

**Approccio consigliato**: opzione 1. Creare `SafeORJSONResponse(ORJSONResponse)` che fa `jsonable_encoder(content)` prima di `orjson.dumps()`, e usarla come `default_response_class`.

### Benefici attesi

Endpoint pesanti (bulk import, FIFO calc, portfolio summary) potrebbero guadagnare 20–50ms su payload grandi. Serializzazione nativa di `datetime`, `UUID`, `Enum` senza `jsonable_encoder`.

### Prerequisiti

- Test coverage sugli endpoint con campi `SafeDecimal` per verificare output identico
- Benchmark prima/dopo su `/api/v1/transactions` con dataset reale

---

Aree di miglioramento dopo aver visto compeditor:
Tra i provider di prezzo, oltre ai siti da aumentare, ha senso fare olgre al css selector (che potrebbe essere rinominato web page) anche json api, html table e csv
aggiungere i provider AI, olre a ollama e openrouter, anche tutti gli altri per l'installazione locale.
pensare un sistema di addon che permetta al forontend di aggiungere tab. Capendo come creare un market place.
aggiungere nella dashboard e nei broker dei tab che fanno anche altri tipi di analisi oltre quelli pensati. Altri tipi di analisi restano da definire (allocazione % con quadrettoni/treemap già fatta, vedi TODO_Completati.md).
La vecchia idea di target allocation per Broker è ora precisata nella sezione
“PAC/Rebalancer — Profili Persistenti e Strategie Estese”: la v1 usa target
globali per Asset e route/priorità; una distribuzione proporzionale esplicita per
Broker resta futura.
Aggiungere la possibilità di creare "Portafogli" che dovrebbero essere gruppi di broker o asset o entrambi, da approfondire.
Fare delle pagine di dettaglio per analizzare i trade, le fee 
Aggiungere un calcolatore FIRE non solo da oggi al futuro, ma anche fissando una data di inizio per aver modo di vedere la differenza tra andamento teorico e reale.

---

---

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

### F-MC-3 — Valuta base dell'asset ed esposizione valutaria economica

Spostata il 18/10/2026 nella voce «🧬 Profilo dei dati dell'asset», in cima al file.

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

## Il generatore di dati di prova non onora i bersagli `end_price`, e lo scarto è sistematico

**Misurato il 18/09/2026** · **Priorità**: Media, non blocca nulla.

`end_price` è un'attesa, non un bersaglio: `drift_per_day` centra il valore in media sulle realizzazioni, e ogni popolamento ne
pesca una sola. Apple doveva chiudere a 185 e chiude a 264,57 (+43 %), Bitcoin a 45 000 e chiude a 25 890 (−42,5 %), Microsoft
−17,4 %: i segni discordi escludono un bias, sono le ampiezze previste dalla volatilità configurata. Gli indici invece centrano
il bersaglio, perché `_populate_benchmark_indices` normalizza.

**Il lavoro.** Decidere se `end_price` è un contratto o un'attesa e renderlo esplicito, oppure normalizzare anche le serie non
indice. Cambia i numeri di tutte le superfici: va fatto come lavoro a sé, con il confronto prima e dopo.

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

## 🔴 La simulazione risponde alla finestra, non al portafoglio — e non si annuncia

**Misurato il 21/09/2026** · **Priorità**: Medio-alta. Non blocca il rilascio: L4 è dietro il banner beta, che cade quando si
chiude questa voce (`L4WhatIf.svelte`).

**Il fatto.** Stesso asset, stesso orizzonte (365 giorni), stesso motore: cambia solo la finestra.

| Finestra | Mediana | Probabilità di perdita |
|---|---:|---:|
| 95 giorni | +1 400,4 % | 0,01 % |
| 365 giorni | −39,1 % | 70,74 % |

**La causa.** La matematica è giusta: su sei finestre la mediana sta fra 1,009 e 1,016 volte l'estrapolazione ingenua. Il
bootstrap ripesca ogni osservazione `orizzonte / n_osservazioni` volte: con 93 osservazioni su 365 giorni assume che quel
trimestre duri quattro volte tanto. Non dipende dai dati finti: chi tiene crypto e sceglie «3M» riceve questo.

**⚠️ Il denominatore è gonfiato.** `series_preparation.py` riporta i prezzi in avanti, quindi `n_observations` conta giorni di
calendario, e 540 giorni restituiscono le stesse 360 osservazioni di 365. Chiedere più storia può ridare in silenzio la stessa
storia.

**Il lavoro.** Decidere cosa fare quando l'orizzonte supera la finestra: rifiutare, avvisare, o lasciar fare dichiarando
l'incertezza. Una soglia ovvia non esiste (a 1,00× Bitcoin dà comunque +100 %): la monotonia è il dato, la soglia è una scelta.
L'incertezza della deriva è già mostrata accanto alla banda; resta da decidere se serve anche la guardia.

**Stima**: circa un giorno per un avviso quando l'orizzonte supera la storia usata, 4 lingue comprese.

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

# Idea interessante presa da un utente:

3. L'effetto del cambio sul rendimento (FX Impact)
   "Related to my previous feature is how much FX rates change the balance, again not really that import but just interesting to see."

Gli piacerebbe vedere (anche solo per curiosità) quanto del suo guadagno/perdita dipende dal titolo in sé e quanto dalle fluttuazioni del tasso di cambio (il classico spacchettamento tra capital gain e impatto valutario). Ma ribadisce che non è prioritario.
Discorso originale qui: https://github.com/Librefolio/LibreFolio/discussions/24#discussioncomment-18584139

---

# Feedback del developer — idee e migliorie (lista 06–26/09, smistata il 30/09/2026)

Le voci qui sotto vengono da una lista di appunti del developer. I **difetti** della stessa lista
sono stati assegnati a un workstream di sviluppo (K, piano dei seguiti di review); qui restano solo
le migliorie e le funzioni nuove.

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

## 🏠 Funzioni in stile HomeBank, parser OFX e migrazione

**Data aggiunta**: 30 Settembre 2026 (appunto del 06/09) · **Status**: ⏳ IN ATTESA · **Priorità**: Bassa

### Contesto

Far evolvere LibreFolio verso le funzioni di HomeBank: categorie per versamenti e prelievi, i
grafici relativi e le funzioni accessorie, come il calcolatore per l'auto.

### Azione Futura

- Un plugin BRIM **OFX** generico, da usare quando manca un plugin specifico della banca.
- Uno **script di migrazione** da un file HomeBank a LibreFolio, una tabella alla volta.
- Categorie per le transazioni di cassa, con grafici dedicati.

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
non serve e i primi 3 sono sufficienti»). Si lega al task notturno qui sopra: potrebbero diventare la stessa cosa.

## 🔥 Strumenti — calcolatore FIRE e riuso del motore matematico

**Data aggiunta**: 30 Settembre 2026 (appunto del 22/09) · **Status**: ⏳ IN ATTESA · **Priorità**: Bassa

### Contesto

La pagina **Strumenti** esiste: è il posto naturale per un **calcolatore FIRE**. Se il motore
matematico dei tool (quello del PAC) si presta, può servire anche ad altri calcolatori.

### Azione Futura

Un plugin Tool nuovo (skill `tool-plugin`), con contratto Pydantic e UI compilata, come il PAC.

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

## 📈 Grafici da un video di analisi del portafoglio

**Data aggiunta**: 27 Luglio 2026 (era `idee_per_grafici.md` nella radice, spostato qui il 14/10/2026) · **Status**: ⏳ IN ATTESA · **Priorità**: Bassa

### Contesto

Usare come base i grafici mostrati in questo video: https://www.youtube.com/watch?v=B6mLq6UUTWw

### Azione Futura

Analizzarli, poi implementarne alcuni o tutti.

## 📈 Scala logaritmica nei grafici

**Data aggiunta**: 30 Settembre 2026 (appunto del 26/09) · **Status**: ⏳ IN ATTESA · **Priorità**: Bassa

### Contesto

Una modalità di visualizzazione **logaritmica**, soprattutto sulle percentuali.

### Azione Futura

Sulle percentuali il logaritmo non si applica ai rendimenti negativi: va applicato al fattore di
crescita (1 + r). Decidere su quali grafici offrirla (Crescita, prezzo dell'asset, confronto).

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

## ⚡ Motore del portafoglio — caricare solo i prezzi che servono

**Data aggiunta**: 1 Ottobre 2026 · **Status**: 📋 FUTURO — PR #30 (ex #28) entrata il 05/10/2026 ·
**Priorità**: Media (prima va misurata)

### Contesto

- La PR [#30](https://github.com/Librefolio/LibreFolio/pull/30) di Martin Sova (msov19), che sostituisce la
  [#28](https://github.com/Librefolio/LibreFolio/pull/28), corregge `convert_bulk`.
  La query dei cambi aveva solo il limite superiore e a ogni chiamata caricava tutta la storia della
  coppia. Ora carica la finestra [ultimo cambio ≤ prima data richiesta, ultima data richiesta] e
  cerca con `bisect`.
- Banco di prova del coordinatore (01/10, 10 anni di cambi, 3.650 conversioni giornaliere):
  - la ricerca passa da 120–200 ms a meno di 1 ms;
  - nel `convert_bulk` completo (~17 ms) il `bisect` pesa ~4%; il resto è la query e la creazione
    degli oggetti `Currency`.
  - **Valutato e scartato**: sostituire il `bisect` con una ricerca O(1) (dizionario per data con
    passo indietro, dizionario pre-riempito per ogni giorno, cursore). Risparmierebbe meno dell'1%;
    il cursore non aiuta perché `portfolio_engine` passa le date in ordine sparso (le raccoglie in
    un `set`).
- Lo stesso schema della query dei cambi c'è nel motore del portafoglio:
  - `backend/app/services/financial_math/portfolio/engine.py:312` precarica i prezzi con solo `date <= actual_to`,
    come oggetti ORM completi (`select(PriceHistory)`);
  - quindi legge tutta la storia di ogni asset posseduto, anche gli anni prima del primo acquisto o
    del periodo richiesto (`actual_from = date_from or first_tx_date`, `:246`).
- A cosa servono i prezzi caricati:
  - il calcolo dei giorni che cambiano (`daily_state.py:366`), che dei prezzi precedenti a `frame_start` usa solo
    l'ultimo;
  - il resolver `AssetPriceSeries` (`backend/app/services/financial_math/price_marks.py:146`), che con `bisect`
    trova l'ultima osservazione ≤ data.
- `get_prices_bulk` (`backend/app/services/assets/price_query.py:149`), il corrispettivo di
  `convert_bulk` per i prezzi, ha già la finestra con minimo e massimo.

### Azione Futura

- **Prima misurare**, su una copia dei dati reali: righe lette e tempo della query a `:312` rispetto
  al calcolo intero, con e senza `date_from`.
- Se conviene:
  - limitare la query a [ultimo prezzo ≤ `frame_start` per asset, `actual_to`], con la stessa
    sottoquery «ancora» della PR #30;
  - leggere solo le colonne usate (data, close, valuta; open/high/low solo con le candele), invece
    degli oggetti ORM.
- Da verificare prima: nessuno deve chiedere al resolver una data precedente a `frame_start`
  (periodo pre-frame, intervalli in transito, prezzi alle date dei BUY). Altrimenti l'ancora va
  presa dalla prima di quelle date.
- Test:
  - confronto differenziale del risultato del motore, prima e dopo, su più utenti e periodi, come
    quello fatto per la PR #28;
  - poi `services portfolio-engine`, `services roi-fifo-utils`, `api portfolio`.
- Minori, solo se la misura lo giustifica, in `get_prices_bulk`: la finestra è unica per tutte le
  richieste (minimo e massimo globali), e il prezzo «seme» si cerca con una query per asset. Si
  possono fare per asset, in una query sola, come nella PR #30.

## 💡 Traccia rischio/rendimento nel tempo («snail trail»)

**Data aggiunta**: 1 Ottobre 2026 · **Status**: 💡 IDEA — da approfondire prima di pianificarla ·
**Priorità**: Bassa

### Contesto

- Origine: la review del developer di L3° di Asset Global (scheda Correlazione), 01/10/2026. Il
  parere di F è nel suo diario di avanzamento di L3°
  (`LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/progress/F-L3-rischio-rendimento.md`,
  ancora sul ramo di F).
- Cambiando il periodo, i punti del grafico rischio/rendimento si spostano. Per mostrare
  quell'evoluzione il developer propone una traccia: con un periodo di 1A, un punto per ciascun
  trimestre, uniti da una linea. In letteratura esiste e si chiama *snail trail*: i punti
  rischio/rendimento di sotto-periodi successivi, uniti nel tempo.

### ⚠️ Perché non a trimestri dentro un anno

- **Asse orizzontale, la volatilità**: si stima bene già su ~63 sedute (errore relativo ≈ 1/√(2n),
  cioè 9–14% con le code grasse), e cambia davvero nel tempo, perché i mercati alternano fasi calme e
  agitate. Qui la traccia direbbe il vero.
- **Asse verticale, il rendimento medio annuo**: anche per un asset che non cambia affatto, la media
  annualizzata di un sotto-periodo lungo T anni si scosta per puro caso di σ/√T. Su un trimestre fa
  2σ: ±40 punti per un ETF azionario al 20% di volatilità, ±140 per una cripto al 70%. In più,
  annualizzare un trimestre lo moltiplica per quattro: un +10% nel trimestre diventa «+40% annuo».
- **Il risultato**: punti che saltano di decine di punti, e un'evoluzione che si vede ma non c'è. È
  il grafico «plausibile ma sbagliato» che il laboratorio evita.
- **La leggibilità**: N asset per 4 punti, più N linee che si incrociano.

### Azione Futura — la versione onesta, se un giorno la si vuole

- Solo per l'asset selezionato: la selezione collegata fra tabella e grafico di L3° c'è già.
- Segmenti di un anno solare: il rendimento davvero ottenuto in quell'anno, un fatto e non
  un'estrapolazione. Quindi solo per periodi di almeno 3 anni.
- Calcolata dal motore (Risk): un campo nuovo nell'uscita di `asset_set_risk_return`, con le regole
  di copertura per segmento.
- Prima di disegnarla, un prototipo sui dati veri, per vedere se la traccia dice qualcosa di più del
  rumore.
- Per «come cambia il rischio nel tempo» esistono già gli indicatori Rolling Volatility e Rolling
  Sharpe nel grafico dell'asset.

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

## Approfondire protocollo Enable Banking europeo

Ascoltando online ho trovato di https://enablebanking.com/ come protocollo open per accedere alle banche europee, sarebbe interessante approfondire e capire se si esce a usare per creare un importatore "automatico" delle transazioni nel sistema BRIM

Priorità: Esplorativa

Aggiunto: 26/10/26
