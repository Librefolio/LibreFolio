# Richieste degli utenti

Registro tecnico delle richieste arrivate dagli utenti (issue, discussioni, chat), con lo stato reale nel codice,
la decisione del developer e i task che ne derivano. Una sezione per richiesta, la più recente in alto.

Convenzioni:
- **Stato**: 💬 in discussione con l'utente · 📋 deciso, da pianificare · 🚧 in lavorazione · ✅ fatto · ⛔ non lo faremo.
- Il task, quando entra in un rilascio, prende un codice del backlog (`BACKLOG_POST_1.2.md`) e qui si scrive il link.
- Su GitHub (18/10): etichette `priority: …` / `effort: …` / `blocked`, milestone `1.3.0` e `1.4.0`.
- **Le issue sono degli utenti** (decisione del developer, 19/10): noi non apriamo issue nostre, né ombrelli né task. I
  task che nascono da una richiesta si tengono qui (e nel backlog quando entrano in un rilascio). Le issue #54, #55 e
  #56, aperte da noi il 18/10, sono state cancellate il 19/10; il loro testo è nei file della sessione del
  coordinatore.

---

## Utente @Xgialippo (GitHub, 17/10/2026) — usa Fineco

### #48 · Grafico delle singole posizioni sovrapposte — 💬 (direzione decisa dal developer, 18/10)

**Richiesta.** Un grafico come «Crescita del Portafoglio», ma con una linea per ogni posizione più il portafoglio
intero, «base 100», con la possibilità di escludere una posizione dal grafico (come la legenda del grafico Abs).

**Stato nel codice (18/10).**
- Esiste per i **lotti**: `features/brokers/lots/LotComparisonChart.svelte` (`lotComparisonChartHelpers.ts`),
  sezione «Confronto Valore / Rendimento» (`user/dashboard/positions.*.md` §4). Modo **Rendimento**: un
  «Rendimento aggregato» più una linea per ogni lotto **selezionato** nella tabella dei lotti, in **Abs** o **%**,
  con «Auto / Da 0». Modo **Valore**: aree impilate (valore residuo + incassi + proventi).
- Esiste in parte per gli **asset**: l'indicatore «Confronto Asset» nella pagina dell'asset sovrappone il prezzo di
  **un** altro asset; in modalità % le due curve partono da 0 %.
- Nella Dashboard, scheda «Le tue posizioni» (`PositionsPanel`, sottoschede «Portafoglio» e «Periodo»), il dettaglio
  lotti (`LotsAnalysisPanel`) si apre **sotto** il pannello delle posizioni con `?asset=<id>`
  (`routes/(app)/dashboard/+page.svelte`, `openAssetPanel` / `closeAssetPanel`).

**Decisione del developer (18/10).**
- Si fa la **soluzione 2: il rendimento della posizione**, non l'andamento del prezzo dell'asset. Include acquisti,
  vendite e proventi, come il grafico dei lotti.
- Due viste: **Abs** (P&L in denaro) e **%**, dove **la % è proprio il «base 100»** richiesto dall'utente.
- **Linee, non aree impilate**: un rendimento o un P&L può essere negativo (e una posizione corta ha valore
  negativo), quindi un grafico impilato non regge. Il valore per asset nel tempo c'è già nello storico
  dell'allocazione.
- **Dove**: un grafico sotto «Le tue posizioni» → «Portafoglio».
  - La tabella «Portafoglio» si evolve con i **selettori di riga come la tabella dei lotti**: senza selezione il
    grafico mostra la linea del portafoglio; le righe selezionate aggiungono le loro linee; la legenda le accende e
    le spegne. Così il grafico resta leggibile anche con molti asset.
  - **«Dettaglio lotto» sostituisce il portafoglio**: chiedendo il dettaglio lotti di una posizione, al posto della
    tabella «Portafoglio» (e del suo grafico) compare il dettaglio lotti richiesto, non più sotto.
  - Serve **un modo per tornare al portafoglio** uscendo dal dettaglio lotti (un comando «← Portafoglio» ben
    visibile; anche il «indietro» del browser, visto che il dettaglio è già guidato da `?asset=`).

**Note tecniche per la pianificazione.**
- Riuso: la logica e i gesti di `LotComparisonChart` (selezione → linee, Abs/%, legenda). Va generalizzata a
  «serie per posizione» invece di «serie per lotto», o affiancata da un componente gemello.
- Backend: serve una **serie giornaliera per posizione** (P&L e base per la %) sul periodo. Il motore la conosce già
  (`daily_state`), ma va esposta **solo per le posizioni selezionate**, su richiesta, per non appesantire il report.
- % «base 100»: per una posizione aperta a metà periodo serve la stessa regola del grafico dei lotti
  («Auto / Da 0»: da dove parte la linea). La linea del portafoglio usa il rendimento già calcolato della Dashboard.
- Posizioni corte o con valore negativo: la % va calcolata su una base in valore assoluto, come le altre % del
  periodo (`period_pnl / |start_value|`); da fissare con un test.
- Matematica nella casa (`financial_math/`), regola 10.

**Prossimo passo.** Risposta pubblicata dal developer il 18/10 (in attesa della replica dell'utente); poi analisi
tecnica e codice del backlog quando entra in un rilascio.

### #52 · Portafoglio diviso in sezioni / obiettivi — 💬 chiesto all'utente come raffinare l'idea (18/10)

**Richiesta.** Raggruppare gli asset per obiettivo («i pilastri di Coletti»: fondo emergenze, pensione…), con
sottogruppi o tag, e filtrare la Dashboard per gruppo.

**Stato nel codice.** La Dashboard si filtra solo per broker. Ripiego oggi: più «broker» separati, scomodo con un
solo conto reale.

**Idea già appuntata dal developer** (`TODO_FUTURI.md`, tra le idee sparse): creare dei **«Portafogli»**, cioè
gruppi di broker, di asset o di entrambi, da approfondire. Collegamenti nello stesso file: la distribuzione
proporzionale esplicita per broker del PAC/Rebalancer (futura, «PAC/Rebalancer — Profili Persistenti e Strategie
Estese») e il benchmark persistente per portafoglio/broker (Risk Analysis).

**Domande poste all'utente (18/10)**, per arricchire il task prima di farlo:
- lo stesso asset appartiene sempre a un solo obiettivo, o va diviso fra più obiettivi (a quote o a lotti)?
- gruppi di broker, di asset, o tutti e due?
- cosa si aspetta di vedere per ogni portafoglio: Dashboard filtrata, KPI e allocazione propri, un'allocazione
  obiettivo per il PAC?

### #51 · TER degli ETF e del portafoglio — 📋 nel TODO (18/10), dopo l'ambiente centralizzato degli asset

**Richiesta.** Vedere il TER di ogni ETF e il TER complessivo del portafoglio.

**Stato nel codice.** Il TER arriva solo dal plugin justETF, e solo come testo nella descrizione dell'asset
(`asset_source_providers/justetf/plugin.py`, «TER: x%»); con il potenziamento di Yahoo (#50) arriverà nello stesso
modo anche per gli ETF seguiti con Yahoo. Non è un campo.

**Decisione del developer (18/10).** L'idea è buona ma arriva solo dopo aver ragionato bene e creato un ambiente
centralizzato per le informazioni degli asset. Annotata in `TODO_FUTURI.md`, «🧬 Profilo dei dati dell'asset»,
sottosezione «Prime idee d'uso dei dati in comune»: il TER medio pesato è il primo esempio di un fatto per asset
aggregato sul portafoglio, da estendere ad altre voci una volta identificate.

### #50 · Investing.com / TradingView e composizione degli ETF — 📋 potenziamento Yahoo deciso (18/10); il resto in `TODO_FUTURI.md`

**Richiesta.** (1) La composizione degli ETF arriva solo da justETF, da Yahoo solo il prezzo; (2) aggiungere
Investing.com o TradingView come provider; (3) esposizione per singola azienda e per emittente del fondo.

**Stato nel codice.** justETF dà paesi e settori (`FAGeographicArea`, `FASectorArea`) e il TER come testo; Yahoo dà
prezzi, dividendi e split.

**Verifiche (18/10).**
- **Yahoo espone i dati dei fondi, LibreFolio non li legge.** `yfinance` 1.7.0, `Ticker(...).funds_data`:
  `top_holdings` (prime 10 con peso), `sector_weightings` (11 settori), `asset_classes`, `bond_holdings`,
  `bond_ratings`, `fund_operations` (TER, «Annual Report Expense Ratio»), `fund_overview` (emittente, tipo legale).
  Prova dal vivo su VOO, SWDA.MI, VWCE.DE, CSPX.L, IWDA.AS, EUNL.DE: tutti con top 10 e settori; TER su 5 su 6
  (manca per VWCE.DE). Manca la ripartizione per **paese**, che dà solo justETF. Nessuna verifica precedente
  trovata (wiki, giornale, sessioni): l'idea «Yahoo non li espone» non era verificata, ed è sbagliata.
- **Anche justETF dà più di quanto usiamo.** `justetf_scraping.get_etf_overview` (`EtfOverview`): `ter`,
  `top_holdings`, `holdings_date`, `fund_provider`, `fund_size_eur`, `replication`, `currency_hedged`,
  `fund_currency`, `fund_domicile`, `index`, `inception_date`, `distribution_frequency`, `countries`, `sectors`.
  Il plugin oggi usa solo `description`, `ter` (come testo), `distribution_policy`, `countries`, `sectors`.
- **Condizioni d'uso delle fonti** (non è un parere legale):
  - justETF, AGB §3.1 (letto nel PDF): l'utente deve astenersi da «Einsatz von Programmen zur automatisierten
    Kursabfrage»;
  - Borsa Italiana / Euronext: dati riservati, il download automatico e il riuso richiedono licenza (dai termini
    pubblicati, non letti clausola per clausola);
  - Yahoo: i termini limitano l'accesso automatico e la ridistribuzione; l'uso personale con yfinance è tollerato
    nei fatti, non autorizzato.
  - In self-hosted (ogni istanza interroga per il suo utente, a basso volume, senza ridistribuire) il rischio è
    basso. **In un servizio ospitato a pagamento diventa uso commerciale** (lo interroghiamo noi per clienti paganti):
    rischio molto più chiaro → servono dati con licenza (fornitore a pagamento, F06) o la chiave dell'utente.
- **Investing.com e TradingView**: niente API ufficiali; i termini vietano la lettura automatica anche agli abbonati
  → niente provider, nemmeno a pagamento.
- **Strada standard a pagamento**: API di data vendor con chiave personale (EODHD Fundamentals, Financial Modeling
  Prep, Finnworlds; Morningstar/LSEG a livello enterprise), con TER e posizioni dei fondi per ISIN. LibreFolio 1.3
  ha già le impostazioni dei plugin con segreti per utente o per istanza (migrazione 007): un plugin a pagamento
  con la chiave dell'utente è la via pulita.

**Decisione del developer (18/10).**
- **Subito: potenziare il plugin Yahoo con i dati che Yahoo dà e che LibreFolio già sa tenere** (per la 1.3.0). Task:
  - per ETF e fondi (`quoteType` `etf` / `mutualfund`), la **distribuzione per settore** da
    `funds_data.sector_weightings` in `classification_params.sector_area` (`FASectorArea`), con la mappatura dei settori
    di Yahoo sui nostri (`validate_sector`), come fa già justETF; oggi Yahoo dà un settore solo per le azioni
    (`info["sector"]`);
  - nella **descrizione** (`short_description`), quando manca `longBusinessSummary`, la descrizione del fondo
    (`funds_data.description`); e, come fa già justETF, **TER ed emittente in coda alla descrizione**
    («TER: x%», da `fund_operations` e `fund_overview.family`);
  - tutto in `fetch_asset_metadata` (`asset_source_providers/yahoo_finance/plugin.py`), con la stessa politica
    d'errore (un dato del fondo che manca non fa fallire i metadati), dentro il thread del core;
  - test: rossi prima, su un `funds_data` finto (settori, TER mancante come per VWCE.DE, fondo senza dati);
    documentazione `user/assets/providers` di Yahoo (cosa offre) e dev `provider_yahoo_finance.md`.
- **Dopo, da studiare bene**: le posizioni dei fondi, le classi di attivo, le obbligazioni, il TER come campo e
  tutto ciò che justETF dà in più → `TODO_FUTURI.md`, «🧬 Profilo dei dati dell'asset» (priorità medio-alta).
- **Investing.com e TradingView** → `TODO_FUTURI.md`, stessa voce, «Possibili prossime fonti», insieme a extraETF:
  priorità bassa-media, da alzare se portano titoli o classi di titoli che Yahoo, justETF e Borsa Italiana non
  coprono. Il provider CSS Scraper permette già di provare a leggere un prezzo da una loro pagina.
- **Risposta pubblicata dal developer (18/10)**: ha invitato l'utente a scrivere lui i plugin e a proporre una PR
  («il sistema è modulare apposta»).

### #49 (discussione) · «Valore Iniziale» e «Valore Finale» — ✅ risposto (17/10), task aperti

**Risposta data.** Valore della posizione a inizio e a fine periodo, come la colonna «Valore» del Portafoglio; 0 se
la posizione non c'era all'inizio o era chiusa alla fine; il Valore Iniziale è la base delle % del periodo.

**Task promessi all'utente** (per la 1.3.0).
- La frase che spiega le due colonne c'è solo in `user/dashboard/positions.en.md` (riga ~96): portarla in
  `positions.it.md` (e fr/es).
- Un tooltip sulle colonne «Valore Iniziale» e «Valore Finale» (`dashboard.startValue` / `endValue`, oggi senza
  tooltip; le colonne sono nascoste di default).

**Domanda aperta all'utente.** Fineco funziona bene con i suoi report? Se sì, togliere l'etichetta Beta (collegata a
C-91 del backlog: collaudare gli import di Interactive Brokers e Fineco su report veri).

### #47 · Inserire il prezzo unitario invece dell'importo — 📋 risposto (18/10)

**Richiesta.** Nel modulo «Nuova transazione», poter scrivere il prezzo medio unitario invece dell'importo totale.

**Risposta data.** Si aggiunge la scelta «Importo totale / Prezzo unitario», con l'altro valore calcolato; l'importo
risultante resta visibile e modificabile, perché `prezzo × quantità` può differire dall'addebito reale per gli
arrotondamenti. Spiegato anche che il valore di mercato usa il prezzo dell'asset, e solo senza prezzi l'ultimo
acquisto o l'ultima vendita.

**Task.** Il selettore nel modulo (`TransactionFormModal`, sezioni singola e coppia), con la quantità e la regola dei
decimali già in uso (W-B64, N63); valutare lo stesso selettore nella modifica multipla.
