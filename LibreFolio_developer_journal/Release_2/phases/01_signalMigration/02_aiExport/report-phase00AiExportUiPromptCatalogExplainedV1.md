# AI Export — guida ragionata a ogni scelta UI

**Data**: 4 agosto 2026  
**Catalogo corrente**: 32 Export Data, 17 Request Analysis, 65 componenti  
**Scopo**: spiegare, pagina per pagina e scelta per scelta, cosa viene copiato,
cosa viene chiesto all'AI e perché il prompt contiene quei dati ma non altri.

## Indice

1. [Risposta breve ai dubbi principali](#1-risposta-breve-ai-dubbi-principali)
2. [Come funziona la UI](#2-come-funziona-la-ui)
3. [Guida rapida](#3-guida-rapida-quale-scelta-usare)
4. [Dashboard / Portfolio](#4-dashboard--portfolio)
5. [Dettaglio Broker](#5-dettaglio-broker)
6. [Dettaglio Asset](#6-dettaglio-asset)
7. [Dettaglio FX](#7-dettaglio-fx)
8. [Valutazione della frammentazione](#8-valutazione-della-frammentazione)
9. [Fonti e prova reale](#9-fonti-e-prova-reale)

## 1. Risposta breve ai dubbi principali

### I dati Portfolio non sono tutti aggregati

La percezione è comprensibile perché molte scelte hanno nomi simili e alcune sono
effettivamente solo aggregate. Però:

- **Panoramica portafoglio** contiene una riga per ogni posizione aperta con:
  Asset, Broker, quantità, prezzo unitario corrente, fonte di valorizzazione,
  valore corrente, WAC, P&L e peso;
- **Sintesi Asset del portafoglio** contiene una riga uniforme per ogni Asset
  tecnico idoneo con prezzo corrente osservato, rendimento 1M/3M/periodo,
  minimo/massimo con date, EMA, KAMA, RSI, volatilità disponibile, stato e ultimi
  eventi; aggiunge anche Drawdown corrente/massimo per Asset;
- **Confronto Asset del portafoglio** contiene lo stesso contesto di mercato
  individuale, più breadth aggregata ed eventi strutturali selezionati;
- **Dati tecnici portafoglio** contiene la history prezzi/rendimenti e tutti i
  Signal per ogni Asset coperto;
- **Tutti i dati portafoglio** include sia prezzi correnti delle posizioni sia
  history tecnica con la densità del detail scelto, oltre a performance e FIFO.

Le scelte realmente aggregate sono soprattutto:

- **Sintesi tecnica portafoglio**;
- **Contesto di Drawdown del Portafoglio**;
- i riepiloghi generali dentro Performance/Flussi.

| Export Portfolio | Righe per Asset | Prezzo corrente | History prezzo | Dati economici posizione |
|---|:---:|:---:|:---:|:---:|
| Panoramica | sì, per posizione | sì | no | sì |
| Performance e flussi | sì, contributor | no | no | P&L/flussi |
| Sintesi tecnica | no | no | no | no |
| Sintesi Asset | sì | sì | no | solo peso |
| Confronto Asset | sì | sì | no | solo peso |
| Drawdown Portfolio | no | no | no | TWRR aggregato |
| Prove reddito | sì, eventi reddito | no | no | reddito |
| Dati tecnici | sì | sì | sì, bucketizzata | no |
| FIFO | sì, per lotto | valuation | no | costo/risultati |
| Tutti i dati | sì | sì | sì, secondo detail | sì |

### PAC: riceve dati dei singoli Asset

Il prompt **Pianificazione PAC** corrente non riceve soltanto allocazioni generali.
Compone automaticamente:

1. `portfolio.overview`;
2. `portfolio.performance_flows`;
3. `portfolio.asset_snapshot`, opzionale ma normalmente incluso quando disponibile;
4. `portfolio.drawdown_context`, opzionale ma normalmente incluso quando disponibile.

Quindi l'AI riceve:

- ogni posizione con prezzo unitario, valore, costo medio, P&L e peso;
- contributo P&L di periodo per Asset/Broker;
- prezzo corrente osservato e rendimenti recenti per Asset;
- minimi/massimi, trend, momentum, volatilità e ultimi eventi per Asset;
- Drawdown sintetico per Asset;
- Drawdown TWRR dell'intero portafoglio;
- liquidità, flussi, redditi, commissioni e tasse.

Non riceve la history completa di tutti i Signal né tutti i lotti FIFO: sarebbero
molto più pesanti e non servono per costruire scenari PAC neutrali. Il prompt
consiglia **Dati tecnici portafoglio** come export aggiuntivo quando quella history
serve davvero.

### Ribilanciamento: riceve dati dei singoli Asset

Il prompt **Ribilanciamento portafoglio** compone:

1. `portfolio.overview`, richiesto;
2. `portfolio.performance_flows`, opzionale;
3. `portfolio.asset_comparison`, opzionale;
4. `portfolio.drawdown_context`, opzionale.

Quindi riceve:

- posizioni individuali, prezzi correnti, valori, P&L e pesi;
- allocazioni per tipo, settore e geografia;
- contributori individuali della performance;
- confronto per Asset su prezzo corrente, rendimenti recenti, min/max, trend,
  momentum, volatilità e ultimi eventi;
- breadth tecnica aggregata;
- Drawdown del portafoglio.

Non riceve automaticamente:

- target allocation, perché deve fornirla l'utente;
- history tecnica completa;
- lotti FIFO;
- costi fiscali futuri o ipotesi di esecuzione.

Questi ultimi dati sono suggeriti separatamente solo se cambiano materialmente la
decisione.

## 2. Come funziona la UI

### Export Data

**Export Data** copia fatti senza chiedere interpretazione. Il testo contiene:

1. metadata e manifest;
2. Snapshot Data.

Non contiene obiettivo di analisi, response contract, note utente o lingua di
risposta.

### Request Analysis

**Request Analysis** aggiunge:

1. obiettivo;
2. istruzioni di verifica;
3. struttura obbligatoria della risposta;
4. dataset richiesti;
5. dataset opzionali disponibili;
6. suggerimenti per altri export;
7. note di dominio;
8. eventuali note utente;
9. lingua di risposta.

### “Richiesto”, “opzionale” e “Additional Data”

- **Dataset richiesto**: se non può essere costruito, l'Analysis fallisce.
- **Dataset opzionale**: il backend prova comunque a includerlo; viene omesso solo
  se non applicabile o se una sua sorgente fallisce.
- **Additional Data**: non è già nel prompt. È un secondo export suggerito
  all'utente per approfondire.

Per leggere le Analysis in questo report:

- **sempre** = dataset richiesto;
- **se disponibile** = dataset opzionale, normalmente incluso ma non garantito;
- **mai automaticamente** = non fa parte della composizione;
- **input utente** = informazione che LibreFolio non può dedurre, per esempio target,
  budget, orizzonte o tolleranza al rischio.

### Tre significati diversi di “prezzo”

1. **Prezzo unitario della posizione**: prezzo usato per valorizzare una posizione,
   normalmente nella valuta target; appare in Overview.
2. **Prezzo di mercato osservato dell'Asset**: ultimo punto della serie prezzo,
   con data, valuta e contesto tecnico; appare negli snapshot/confronti Asset.
3. **History prezzi**: serie bucketizzata nel tempo; appare nei Technical Export.

Confondere questi tre livelli è una delle cause principali della scarsa
leggibilità attuale della UI.

### Cosa cambia con Compact / Standard / Full

Il detail non sceglie quali Asset includere. Cambia la densità:

- Technical Export:
  - history indicatori: 5 / 10 / tutte le righe non vuote;
  - eventi: 7g-min3 / 21g-min10 / 30g-min20;
- Asset Position Context: 3 / 6 / 12 righe recenti;
- FX Market Context: 0 / 4 / 8 righe recenti;
- alcune evidence timeline possono passare da aggregati a righe più dettagliate.

Latest value, period summary, universo e coverage restano deterministici e non
vengono scelti dal frontend.

### Periodo, note, lingua e privacy

- **Periodo**: determina la finestra di performance, prezzi, eventi, redditi,
  Drawdown e FIFO chiuso; Overview resta una fotografia alla data finale.
- **Note utente**: vengono aggiunte soltanto ai Request Analysis; sono dati non
  affidabili e non possono sovrascrivere le istruzioni del prompt.
- **Lingua**: la risposta richiesta segue la lingua corrente della UI.
- **Privacy**: LibreFolio non invia nulla a un servizio AI. Copia il prompt negli
  appunti; è l'utente a decidere dove incollarlo.
- **Web research**: LibreFolio non scarica notizie. Quando un'Analysis richiede
  fonti esterne, è lo strumento AI ricevente a dover cercare e citare le fonti.

## 3. Guida rapida: quale scelta usare

| Domanda | Scelta consigliata |
|---|---|
| Voglio posizioni, prezzi correnti, valori, P&L e allocazioni | Panoramica portafoglio / broker |
| Voglio capire chi ha contribuito al risultato nel periodo | Performance e flussi |
| Voglio una riga comparabile per ogni Asset | Sintesi Asset o Confronto Asset |
| Voglio history prezzi e Signal | Dati tecnici; Full per massima densità |
| Voglio lotti, costi residui e chiusure | Lotti FIFO |
| Voglio redditi datati | Prove di reddito portafoglio |
| Voglio costi/turnover/ratio Broker | Prove di efficienza costi broker |
| Voglio concentrazione per dimensione | Prove di concentrazione broker |
| Voglio tutto il set canonico senza duplicare proiezioni | Tutti i dati |

**Eccezione Broker**: `broker.technical` contiene history indicatori/eventi, ma non
una tabella raw OHLC/prezzi. Il prezzo corrente è in Broker Overview/Asset
Comparison.

## 3.1 Guida rapida alle Request Analysis

| Obiettivo | Analysis | Dati individuali principali |
|---|---|---|
| Pianificare nuovi versamenti | PAC | posizioni/prezzi/pesi + snapshot e Drawdown Asset se disponibili |
| Avvicinare il portafoglio a target | Ribilanciamento | posizioni/prezzi/pesi + confronto Asset se disponibile |
| Spiegare P&L | Attribuzione performance | contributor Asset/Broker, flussi, costi, redditi |
| Collegare movimenti a notizie | Notizie e driver | movimenti/eventi Asset; news cercate dall'AI esterna |
| Analizzare redditi | Revisione redditi | timeline redditi + posizioni e costi |
| Analizzare lotti | Revisione FIFO | posizioni + lotti |
| Leggere breadth | Ampiezza tecnica | posizioni/prezzi correnti + tecnica aggregata |
| Descrivere il portafoglio | Descrizione | posizioni/prezzi/pesi + performance/sintesi se disponibili |

---

# 4. Dashboard / Portfolio

La Dashboard offre **10 Export Data** e **8 Request Analysis**.

## 4.1 Export Data Portfolio

### 4.1.1 Panoramica portafoglio

- **ID**: `portfolio.overview`
- **Perché esiste**: fotografia finanziaria leggibile del portafoglio alla data
  finale, senza history.
- **Contiene**:
  - totali di patrimonio, investito, liquidità, costo aperto, P&L e rendimenti;
  - tutte le posizioni aperte;
  - per ogni posizione: Asset, Broker, quantità, prezzo unitario, valore corrente,
    WAC, P&L, allocation e peso NAV;
  - allocazioni per tipo, settore e geografia;
  - liquidità per valuta;
  - provenienza e semantica dei calcoli.
- **Granularità**: totale + una riga per posizione `(Broker, Asset)`.
- **Prezzi**: sì, prezzo corrente per posizione; no history prezzi.
- **Non contiene**: contributori di periodo, history performance, Signal, eventi,
  Drawdown o FIFO.
- **Perché solo questi dati**: serve come base comune compatta per quasi tutte le
  Analysis Portfolio. Mescolare history e lotti renderebbe ogni prompt
  inutilmente grande.
- **Componenti**: `portfolio.summary`, `portfolio.positions`,
  `portfolio.allocations_cash`, `portfolio.provenance`.

### 4.1.2 Performance e flussi portafoglio

- **ID**: `portfolio.performance_flows`
- **Perché esiste**: spiegare cosa è successo durante il periodo, non descrivere
  solo lo stato finale.
- **Contiene**:
  - TWRR, MWRR, ROI, P&L, guadagni e perdite;
  - bucket temporali di NAV, flussi esterni, rendimento e P&L;
  - una riga contributore per Asset/Broker con valore iniziale/finale,
    realizzato, variazione non realizzata, redditi, costi e P&L;
  - depositi, prelievi, redditi, commissioni, tasse e riconciliazione.
- **Granularità**: portafoglio per bucket + Asset/Broker per contributore.
- **Prezzi**: no prezzo unitario esplicito; usa valori iniziali/finali e
  contributi economici.
- **Non contiene**: allocazione corrente completa, history del prezzo del singolo
  titolo, Signal o FIFO.
- **Perché solo questi dati**: performance e prezzi sono problemi diversi. Qui
  servono contributi economici riconciliabili, non ogni quotazione.
- **Componenti**: `portfolio.performance`, `portfolio.flows_income`,
  `portfolio.fees_taxes`, `portfolio.reconciliation`.

### 4.1.3 Sintesi tecnica portafoglio

- **ID**: `portfolio.technical_summary`
- **Perché esiste**: dare una lettura tecnica aggregata economica in token.
- **Contiene**:
  - universo eligible/covered e copertura Signal;
  - breadth pesata e non pesata per stati tecnici;
  - digest degli eventi recenti.
- **Granularità**: aggregata per Signal/stato/event type.
- **Prezzi individuali**: no.
- **Non contiene**: righe per Asset, prezzi, history indicatori o tutti gli eventi.
- **Perché solo questi dati**: è una proiezione per Analysis descrittive o breadth;
  evita di allegare un Technical Export enorme.
- **Componenti**: `portfolio.technical_coverage`,
  `portfolio.technical_breadth`, `portfolio.event_digest`.

### 4.1.4 Sintesi Asset del portafoglio

- **ID**: `portfolio.asset_snapshot`
- **Perché esiste**: offrire una riga decisionale uniforme per ogni Asset senza
  esportare tutta la history.
- **Contiene per Asset**:
  - prezzo corrente osservato e data;
  - peso nel portafoglio;
  - rendimento 1M, 3M e periodo;
  - minimo/massimo e date;
  - EMA 50/200, KAMA, RSI, NATR/volatilità quando disponibili;
  - stato sopra/sotto medie;
  - ultimi eventi per categoria;
  - Drawdown corrente/massimo, recovery status e distanza dal picco.
- **Granularità**: una riga per Asset + ultimi eventi + una riga Drawdown per Asset.
- **Prezzi**: sì, prezzo corrente osservato; no history completa.
- **Non contiene**: quantità, WAC, P&L posizione, flussi, FIFO o tutti i Signal.
- **Perché solo questi dati**: è il mattoncino pensato per PAC: confronto
  orizzontale piccolo, non analisi tecnica completa.
- **Componenti**: `portfolio.technical_coverage`,
  `portfolio.asset_market_context`, `portfolio.asset_drawdown_snapshot`.

### 4.1.5 Confronto Asset del portafoglio

- **ID**: `portfolio.asset_comparison`
- **Perché esiste**: confrontare tutti gli Asset con le stesse colonne di mercato e
  tecnica.
- **Contiene per Asset**:
  - prezzo corrente, rendimenti, min/max, trend, momentum e volatilità;
  - coverage;
  - ultimi eventi per categoria.
- **Aggiunge**:
  - breadth tecnica aggregata;
  - eventi strutturali selezionati per Asset.
- **Granularità**: una riga per Asset + eventi.
- **Prezzi**: sì, prezzo corrente; no history completa.
- **Non contiene**: Drawdown per Asset, quantità/WAC/P&L, FIFO.
- **Perché differisce da Asset Snapshot**: Snapshot privilegia Drawdown e
  compattezza PAC; Comparison privilegia confronto tecnico/eventi per
  ribilanciamento e news.
- **Componenti**: `portfolio.technical_coverage`,
  `portfolio.asset_market_context`, `portfolio.technical_breadth`,
  `portfolio.context_events`.

### 4.1.6 Contesto di Drawdown del Portafoglio

- **ID**: `portfolio.drawdown_context`
- **Perché esiste**: fornire Drawdown deterministico del portafoglio come percorso
  di ricchezza, non come somma di Drawdown dei titoli.
- **Contiene**: Drawdown corrente/massimo, peak/trough/recovery, durata, recupero,
  copertura, qualità e base `historical_twrr`.
- **Granularità**: un solo portafoglio.
- **Prezzi individuali**: no.
- **Non contiene**: episodi per Asset o history completa.
- **Perché solo questi dati**: il Drawdown del portafoglio deve usare TWRR
  flow-adjusted; aggiungere prezzi Asset cambierebbe domanda e base matematica.
- **Componente**: `portfolio.drawdown_summary`.

### 4.1.7 Prove di reddito portafoglio

- **ID**: `portfolio.income_evidence`
- **Perché esiste**: distinguere redditi realizzati e datati da previsioni.
- **Contiene**: DIVIDEND/INTEREST registrati, data, Asset, tipo, importo nativo,
  importo convertito, valuta, fonte e coverage FX.
- **Granularità**: una riga per evento di reddito o aggregazione dichiarata dal
  detail.
- **Prezzi**: no.
- **Non contiene**: cedole future, ratei, yield stimato o prezzo.
- **Perché solo questi dati**: l'Analysis redditi deve restare ledger-based e non
  inventare cash flow futuri.
- **Componente**: `portfolio.income_timeline`.

### 4.1.8 Dati tecnici portafoglio

- **ID**: `portfolio.technical`
- **Perché esiste**: export tecnico completo multi-Asset.
- **Contiene**:
  - coverage per Asset e Signal;
  - prezzi/rendimenti bucketizzati per ogni Asset idoneo;
  - tutti i Signal e output disponibili;
  - latest e period summary completi;
  - history indicatore 5/10/all righe non vuote per Compact/Standard/Full;
  - eventi 7g/min3, 21g/min10, 30g/min20;
  - breadth aggregata.
- **Granularità**: Asset × Signal × bucket/evento.
- **Prezzi**: sì, current + history bucketizzata secondo il detail scelto.
- **Non contiene**: costi posizione, flussi, allocazioni finanziarie o FIFO.
- **Perché solo questi dati**: separazione netta tra mercato/tecnica e contabilità
  di portafoglio.
- **Componenti**: `portfolio.technical_coverage`,
  `portfolio.technical_prices`, `portfolio.technical_indicators`,
  `portfolio.technical_events`, `portfolio.technical_breadth`.

### 4.1.9 Lotti FIFO portafoglio

- **ID**: `portfolio.fifo`
- **Perché esiste**: audit di costo e risultati per lotto.
- **Contiene**:
  - riepilogo FIFO;
  - lotti aperti/parziali;
  - lotti chiusi nel periodo;
  - quantità, costo residuo, valore corrente, realizzato/non realizzato,
    redditi, fee/tax, età, custody e stato.
- **Granularità**: lotto.
- **Prezzi**: valore/valutazione del lotto; non history prezzi.
- **Non contiene**: allocazioni generali, performance TWRR o Signal.
- **Perché solo questi dati**: FIFO è una metodologia di matching del costo, non
  una lettura di mercato.
- **Componenti**: `portfolio.fifo_summary`, `portfolio.fifo_lots`.

### 4.1.10 Tutti i dati portafoglio

- **ID**: `portfolio.all_data`
- **Perché esiste**: export canonico “kitchen sink” senza duplicazioni interne.
- **Contiene**: unione deduplicata di Overview, Performance/Flows, Technical e FIFO.
- **Prezzi**: sì, prezzi correnti e history tecnica secondo il detail scelto.
- **Non contiene come sezioni separate**:
  - Technical Summary;
  - Asset Snapshot;
  - Asset Comparison;
  - Drawdown Context;
  - Income Evidence.
- **Perché mancano**: sono proiezioni degli stessi fatti o evidence task-specific.
  Inserirle insieme ai dati completi duplicherebbe righe e semantica.
- **Nota importante**: “Tutti i dati” significa tutti i dataset canonici completi,
  non ogni scelta visibile della UI.

## 4.2 Request Analysis Portfolio

### 4.2.1 Pianificazione PAC

- **ID**: `portfolio.pac_planning`
- **Cosa fa fare all'AI**:
  - valuta struttura, liquidità, flussi, concentrazione e vincoli;
  - individua solo le preferenze utente mancanti;
  - separa domande indispensabili da affinamenti;
  - propone 2-3 scenari PAC condizionali;
  - non inventa budget, target o rischio.
- **Dataset**:
  - sempre: Overview, Performance/Flows;
  - se disponibili: Asset Snapshot, Portfolio Drawdown;
  - mai automaticamente: FIFO e Technical completo;
  - suggerito dopo: Technical completo 3M Standard.
- **Dati individuali Asset**: sì. Posizioni/prezzi/WAC/P&L/pesi + snapshot prezzi,
  rendimenti, trend, eventi e Drawdown per Asset.
- **Perché non include full technical/FIFO**: non servono per decidere cadenza e
  scenari di contribuzione; sono approfondimenti subordinati.
- **Input utente**: budget, cadenza, target, orizzonte, liquidità minima,
  tolleranza a volatilità/Drawdown e vincoli operativi.

### 4.2.2 Ribilanciamento portafoglio

- **ID**: `portfolio.rebalancing`
- **Cosa fa fare all'AI**:
  - confronta composizione corrente con target/tolleranze forniti;
  - quantifica gap solo se esistono target;
  - confronta flussi futuri, operazione una tantum e approccio misto;
  - separa costi misurati da ipotesi fiscali/esecutive.
- **Dataset**:
  - sempre: Overview;
  - se disponibili: Performance/Flows, Asset Comparison, Portfolio Drawdown;
  - mai automaticamente: FIFO e Technical completo;
  - suggeriti dopo: Technical completo e FIFO.
- **Dati individuali Asset**: sì. Posizione, prezzo, valore, P&L, peso, contributo
  di periodo, rendimento, min/max, trend, momentum, volatilità ed eventi.
- **Cosa manca intenzionalmente**:
  - target allocation: deve arrivare dall'utente;
  - full history e tutti i Signal;
  - lotti e impatto fiscale puntuale.
- **Input utente**: target allocation/tolleranze, vendite consentite, budget,
  vincoli fiscali ed esecutivi.

### 4.2.3 Attribuzione della performance

- **ID**: `portfolio.performance_attribution`
- **Cosa fa fare all'AI**: spiega risultato del periodo, contributori positivi e
  negativi, realizzato/non realizzato, redditi, costi, tasse, flussi e residuo.
- **Dataset**: Overview + Performance/Flows.
- **Dati individuali Asset**: sì, contributor rows per Asset/Broker e posizioni
  correnti con prezzo; no history prezzo.
- **Perché niente tecnica/FIFO**: la domanda è riconciliare risultato economico,
  non spiegare trend o matching fiscale. FIFO è suggerito se serve.

### 4.2.4 Notizie e driver di prezzo del portafoglio

- **ID**: `portfolio.market_events_review`
- **Cosa fa fare all'AI**:
  - identifica movimenti Asset rilevanti e finestre temporali;
  - cerca fonti web datate;
  - separa driver emittente, settore e macro;
  - classifica legami come supportati, inferiti o speculativi;
  - elenca movimenti non spiegati.
- **Confine dati/news**: Snapshot Data contiene movimenti, date, prezzi, rendimenti
  ed eventi tecnici. Non contiene articoli. L'AI esterna deve effettuare la ricerca
  web e produrre URL, publisher, data pubblicazione e data accesso.
- **Dataset**:
  - richiesti: Overview + Asset Comparison;
  - opzionale: Performance/Flows;
  - suggerito: Technical completo 3M Standard.
- **Dati individuali Asset**: sì, inclusi prezzo corrente, rendimenti, min/max,
  trend e eventi.
- **Perché non full history**: per cercare notizie servono date/movimenti/eventi
  materiali; la history completa è un follow-up se la correlazione richiede più
  dettaglio.

### 4.2.5 Revisione redditi portafoglio

- **ID**: `portfolio.income_review`
- **Cosa fa fare all'AI**: analizza redditi registrati, contributori,
  concentrazione, fee/tax e contesto netto; non prevede redditi futuri.
- **Dataset**: Overview + Performance/Flows + Income Evidence.
- **Dati individuali Asset**: sì, posizioni/prezzi correnti e righe di reddito
  datate per Asset.
- **Perché niente tecnica**: non serve per dimostrare redditi realizzati.

### 4.2.6 Revisione FIFO portafoglio

- **ID**: `portfolio.fifo_review`
- **Cosa fa fare all'AI**: separa lotti aperti/parziali da chiusure del periodo,
  analizza costi, risultati, redditi, fee/tax, età e custody.
- **Dataset**: Overview + FIFO.
- **Dati individuali Asset**: sì, posizioni correnti e lotti.
- **Perché niente performance aggregata**: il focus è la composizione dei lotti;
  Performance/Flows è suggerito come secondo export.

### 4.2.7 Ampiezza tecnica

- **ID**: `portfolio.technical_breadth`
- **Cosa fa fare all'AI**: descrive quanti Asset/pesi sono in stati trend,
  momentum, volatilità ed evento; distingue copertura e assenze.
- **Dataset**: Overview + Technical Summary.
- **Dati individuali Asset**:
  - sì per le posizioni e prezzi correnti dell'Overview;
  - no per la tecnica per Asset: la tecnica è aggregata.
- **Perché niente full technical**: breadth significa distribuzione degli stati,
  non lettura delle singole serie. Il Technical completo è Additional Data.

### 4.2.8 Descrizione portafoglio

- **ID**: `portfolio.description`
- **Cosa fa fare all'AI**: produce descrizione neutrale di composizione,
  liquidità, capitale, performance, concentrazione e contesto tecnico generale.
- **Dataset**:
  - richiesto: Overview;
  - opzionali: Performance/Flows e Technical Summary.
- **Dati individuali Asset**: sì per posizioni/prezzi/pesi; tecnica solo aggregata.
- **Perché non Asset Comparison/FIFO**: una descrizione generale deve restare
  concisa. Technical e FIFO completi sono suggeriti solo se la domanda li richiede.

---

# 5. Dettaglio Broker

La pagina Broker offre **10 Export Data** e **4 Request Analysis**. Tutti i dati
sono limitati al Broker selezionato e alla quota/accesso dell'utente.

## 5.1 Export Data Broker

### 5.1.1 Panoramica broker

- **ID**: `broker.overview`
- **Perché esiste**: fotografia finanziaria completa del Broker alla data finale.
- **Contiene**:
  - riepilogo Broker;
  - tutte le posizioni;
  - quantità, prezzo unitario, valore, WAC, P&L e peso;
  - allocazioni e concentrazione;
  - liquidità e provenienza.
- **Granularità**: totale + riga per posizione.
- **Prezzi**: sì, prezzo corrente per posizione; no history.
- **Non contiene**: performance di periodo, technical history o FIFO.
- **Componenti**: `broker.summary`, `broker.positions`,
  `broker.allocation_concentration`, `broker.provenance`.

### 5.1.2 Performance e flussi broker

- **ID**: `broker.performance_flows`
- **Perché esiste**: spiegare risultato e movimenti economici del Broker nel periodo.
- **Contiene**: performance, contributori per Asset, flussi, redditi, costi e
  riconciliazione.
- **Granularità**: bucket Broker + contributori Asset.
- **Prezzi**: no prezzo unitario/history; usa valori e contributi economici.
- **Non contiene**: allocazione completa, Signal o FIFO.
- **Componenti**: `broker.performance`, `broker.flows_income_costs`,
  `broker.reconciliation`.

### 5.1.3 Sintesi tecnica Broker

- **ID**: `broker.technical_summary`
- **Perché esiste**: breadth tecnica aggregata nello scope Broker.
- **Contiene**: coverage e distribuzione degli stati tecnici.
- **Granularità**: aggregata.
- **Prezzi individuali**: no.
- **Non contiene**: righe Asset, history o eventi dettagliati.
- **Componenti**: `broker.technical_coverage`,
  `broker.technical_breadth`.

### 5.1.4 Confronto Asset del Broker

- **ID**: `broker.asset_comparison`
- **Perché esiste**: confronto uniforme degli Asset detenuti nel Broker.
- **Contiene per Asset**: prezzo corrente osservato, rendimenti, min/max, trend,
  momentum, volatilità, coverage e ultimi eventi.
- **Aggiunge**: breadth Broker ed eventi strutturali selezionati.
- **Granularità**: Asset + eventi.
- **Prezzi**: sì, current snapshot; no full history.
- **Non contiene**: costi, lotti, Drawdown per Asset o performance contabile.
- **Componenti**: `broker.technical_coverage`,
  `broker.asset_market_context`, `broker.technical_breadth`,
  `broker.context_events`.

### 5.1.5 Contesto di Drawdown del Broker

- **ID**: `broker.drawdown_context`
- **Perché esiste**: Drawdown TWRR del solo Broker.
- **Contiene**: episodio corrente/massimo, date, durata, recovery, coverage e base.
- **Granularità**: Broker aggregato.
- **Prezzi individuali**: no.
- **Perché**: il Drawdown del Broker deve usare il percorso TWRR filtrato sullo
  scope, non i prezzi dei singoli titoli.
- **Componente**: `broker.drawdown_summary`.

### 5.1.6 Prove di concentrazione broker

- **ID**: `broker.concentration_evidence`
- **Perché esiste**: rendere deterministica l'analisi di concentrazione.
- **Contiene**:
  - largest position e HHI;
  - concentrazione per posizione, tipo, settore, geografia e valuta;
  - coverage e bucket unknown;
  - confronto opzionale Broker vs intero portafoglio.
- **Granularità**: dimensione/categoria, con alcune metriche posizione.
- **Prezzi**: non come campo primario; usa valori correnti delle posizioni.
- **Non contiene**: technical history o FIFO.
- **Componenti**: richiesto `broker.concentration_context`, opzionale
  `broker.concentration_comparison`.

### 5.1.7 Prove di efficienza costi broker

- **ID**: `broker.cost_efficiency_evidence`
- **Perché esiste**: distinguere costi registrati, dati mancanti e ratio validi.
- **Contiene**:
  - transaction/trade/buy/sell count;
  - turnover share-adjusted;
  - fee, tasse, costi totali e contributor categories;
  - average NAV, investito, reddito e trade count come denominatori;
  - formule, operandi, unità, coverage e status dei ratio;
  - distinzione `recorded`, `unavailable`, `not_applicable`.
- **Granularità**: Broker/periodo + categorie costo + ratio.
- **Prezzi**: no.
- **Non contiene**: inferenze su costi FX/trading se la sorgente non li classifica.
- **Componente**: `broker.cost_efficiency`.

### 5.1.8 Dati tecnici broker

- **ID**: `broker.technical`
- **Perché esiste**: history indicatori ed eventi per gli Asset nello scope Broker.
- **Contiene**:
  - coverage;
  - tutti gli indicatori disponibili per Asset;
  - period summary/latest;
  - history 5/10/all;
  - eventi 7g/min3, 21g/min10, 30g/min20;
  - breadth.
- **Granularità**: Asset × Signal × bucket/evento.
- **Prezzi**:
  - non contiene una sezione raw OHLC/prezzi equivalente a
    `portfolio.technical_prices`;
  - il prezzo corrente resta disponibile in Broker Overview o Asset Comparison.
- **Non contiene**: performance, costi, FIFO o raw price history.
- **Nota architetturale**: questa asimmetria rispetto a Portfolio/Asset/FX è una
  possibile lacuna da rivalutare.
- **Componenti**: `broker.technical_coverage`,
  `broker.technical_indicators`, `broker.technical_events`,
  `broker.technical_breadth`.

### 5.1.9 Lotti FIFO broker

- **ID**: `broker.fifo`
- **Perché esiste**: audit dei lotti limitato al Broker.
- **Contiene**: lotti aperti/parziali e chiusure applicabili, costi, valori,
  risultati, età, custody e trasferimenti.
- **Granularità**: lotto.
- **Prezzi**: valore/valuation source, non price history.
- **Non contiene**: performance TWRR o Signal.
- **Componente**: `broker.fifo_lots`.

### 5.1.10 Tutti i dati broker

- **ID**: `broker.all_data`
- **Contiene**: Overview + Performance/Flows + Technical + FIFO, deduplicati.
- **Prezzi**: prezzo corrente tramite Overview; non raw price history.
- **Esclude come sezioni separate**: Technical Summary, Asset Comparison,
  Drawdown, Concentration Evidence, Cost Efficiency Evidence.
- **Perché**: sono proiezioni/evidence focalizzate e duplicheranno dati canonici.
- **Possibile sorpresa**: “Tutti i dati” non include tutti i dataset visibili e
  non include una history raw prezzi Broker.

## 5.2 Request Analysis Broker

### 5.2.1 Revisione broker

- **ID**: `broker.review`
- **Cosa fa fare all'AI**: revisione neutrale di holdings, liquidità, performance,
  flussi, redditi, costi, FIFO, concentrazione e limiti di scope.
- **Dataset**:
  - sempre: Overview + Performance/Flows;
  - se disponibili: Asset Comparison, FIFO, Drawdown, Concentration Evidence;
  - mai automaticamente: Technical completo;
  - suggerito: Technical completo.
- **Dati Asset**: posizioni/prezzi correnti sempre; confronto di mercato per Asset,
  FIFO, Drawdown e concentrazione soltanto se i dataset opzionali vengono costruiti.
- **Perché niente full technical**: deve restare una review finanziaria; tecnica è
  evidenza secondaria.

### 5.2.2 Efficienza costi broker

- **ID**: `broker.cost_efficiency`
- **Cosa fa fare all'AI**: valuta fee/tax/costi rispetto a turnover, NAV, investito,
  redditi e trade count, senza inventare dati mancanti.
- **Dataset**: Overview + Performance/Flows + Cost Efficiency Evidence.
- **Dati Asset**: posizioni correnti e contributor economici; il nucleo è Broker.
- **Perché niente tecnica**: trend e prezzi non determinano se un costo registrato
  è efficiente.
- **Additional Data**: FIFO quando custody/lot/realizzato incidono.

### 5.2.3 Concentrazione broker

- **ID**: `broker.concentration_context`
- **Cosa fa fare all'AI**: descrive concentrazione per dimensione e distingue
  Broker da portafoglio totale.
- **Dataset**:
  - richiesti: Overview + Concentration Evidence;
  - opzionale: Technical Summary;
  - suggerito: Asset Comparison.
- **Dati Asset**: posizioni/prezzi/pesi individuali da Overview; tecnica aggregata.
- **Perché Asset Comparison non è già incluso**: il focus primario è la
  concentrazione finanziaria. Il confronto di mercato è un approfondimento.

### 5.2.4 Revisione FIFO broker

- **ID**: `broker.fifo_review`
- **Cosa fa fare all'AI**: analizza lotti, chiusure, risultati, età,
  concentrazione e limiti di trasferimento/custody.
- **Dataset**: Overview + FIFO.
- **Dati Asset**: sì, posizioni e lotti.
- **Perché niente performance**: è suggerita separatamente quando serve contesto
  temporale.

---

# 6. Dettaglio Asset

La pagina Asset offre **6 Export Data** e **2 Request Analysis**.

## 6.1 Export Data Asset

### 6.1.1 Panoramica asset

- **ID**: `asset.overview`
- **Perché esiste**: identità e fotografia di mercato/posizione di un solo Asset.
- **Contiene**:
  - nome, ticker, identificatori, tipo, valuta e quote base;
  - ultimo prezzo osservato con data;
  - prezzo convertito e provenienza FX;
  - Broker che detengono l'Asset e quantità;
  - quantità totale e peso fattuale nel portafoglio;
  - provider/provenienza.
- **Granularità**: Asset + una riga per Broker detentore.
- **Prezzi**: sì, observed current market price; no history.
- **Non contiene**: WAC/P&L dettagliato, history tecnica o lotti.
- **Componenti**: `asset.identity`, `asset.market_snapshot`,
  `asset.position_scope`, `asset.provenance`.

### 6.1.2 Performance posizione asset

- **ID**: `asset.position_performance`
- **Perché esiste**: analizzare la posizione reale, non il titolo astratto.
- **Contiene**:
  - posizioni per Broker;
  - quantità, costo, valore, P&L;
  - performance di periodo;
  - dettaglio lotti opzionale.
- **Granularità**: Asset aggregato + Broker + eventuali lotti.
- **Prezzi**: valore corrente; per prezzo osservato/provenienza si usa Overview.
- **Non contiene**: technical history.
- **Componenti**: `asset.positions_by_broker`, `asset.cost_value_pl`,
  `asset.performance`; opzionale `asset.lot_detail`.

### 6.1.3 Contesto posizione Asset

- **ID**: `asset.position_context`
- **Perché esiste**: contesto tecnico piccolo per una review della posizione.
- **Contiene**: coverage, prezzo/rendimento/trend/volatilità, history limitata ed
  eventi recenti.
- **Granularità**: singolo Asset, history focalizzata.
- **Applicabilità**: richiede una posizione nello scope accessibile.
- **Non contiene**: tutti i Signal o history completa.
- **Componenti**: `asset.technical_coverage`,
  `asset.position_market_context`.

### 6.1.4 Contesto di Drawdown dello Strumento

- **ID**: `asset.drawdown_context`
- **Perché esiste**: Drawdown deterministico price-only dell'Asset.
- **Contiene**: current/max drawdown, peak/trough/recovery, durata, coverage e
  valuta prezzo nativa.
- **Granularità**: un Asset.
- **Non contiene**: volatility, VaR, Sharpe o forecast.
- **Componente**: `asset.drawdown_summary`.

### 6.1.5 Dati di mercato e tecnici asset

- **ID**: `asset.market_technical`
- **Perché esiste**: export completo della serie di mercato e dei Signal.
- **Contiene**:
  - coverage;
  - OHLC/rendimenti bucketizzati;
  - tutti gli indicatori disponibili;
  - latest e period summary;
  - history 5/10/all;
  - eventi 7g/min3, 21g/min10, 30g/min20.
- **Granularità**: Signal × bucket/evento.
- **Prezzi**: sì, current + history secondo il detail scelto.
- **Non contiene**: costo posizione, P&L o FIFO.
- **Componenti**: `asset.technical_coverage`, `asset.ohlc_returns`,
  `asset.indicators`, `asset.states_events`.

### 6.1.6 Tutti i dati asset

- **ID**: `asset.all_data`
- **Contiene**: Overview + Position Performance + Market Technical.
- **Prezzi**: sì, current + history secondo il detail scelto.
- **Esclude**: Position Context e Drawdown Context come sezioni dedicate.
- **Perché**: sono proiezioni focalizzate; i dati completi sottostanti sono già
  presenti, salvo la sintesi Drawdown che resta opt-in.

## 6.2 Request Analysis Asset

### 6.2.1 Analisi trend asset

- **ID**: `asset.trend_analysis`
- **Cosa fa fare all'AI**: separa trend lungo/medio/breve, momentum, volatilità ed
  eventi; usa extrema/date; non produce forecast deterministici.
- **Dataset**: Overview + Market Technical.
- **Dati posizione**: solo scope/ruolo generale; costo/P&L non sono richiesti.
- **Perché**: è analisi del titolo, non della posizione dell'utente.
- **Additional Data**: Position Performance se costo/valore/P&L diventano rilevanti.
- **Incoerenza UI corrente**: la descrizione italiana cita il Drawdown, ma
  l'Analysis non include `asset.drawdown_context` e il response contract non ha una
  sezione Drawdown deterministica. Questo testo UI va chiarito o la composizione va
  rivalutata.

### 6.2.2 Revisione posizione

- **ID**: `asset.position_review`
- **Cosa fa fare all'AI**: esamina quantità, costo, valore, P&L, Broker, FIFO,
  peso nel portafoglio, contesto tecnico focalizzato e Drawdown.
- **Dataset**:
  - sempre: Overview + Position Performance;
  - se disponibili: Position Context + Drawdown Context;
  - mai automaticamente: Market Technical completo;
  - suggerito: Market Technical completo.
- **Prezzi**: current price sempre da Overview; history limitata soltanto se
  Position Context è disponibile.
- **Perché non full technical**: review della posizione, non analisi tecnica
  esaustiva.

---

# 7. Dettaglio FX

La pagina FX offre **6 Export Data** e **3 Request Analysis**.

## 7.1 Regola base di lettura

Il tasso è sempre:

```text
unità di valuta quote per 1 unità di valuta base
```

Esempio: EUR/USD = USD per 1 EUR. Ogni Analysis deve mantenere questa direzione.

## 7.2 Export Data FX

### 7.2.1 Panoramica coppia FX

- **ID**: `fx.overview`
- **Perché esiste**: identità e tasso corrente.
- **Contiene**: base/quote, tasso, data effettiva, staleness/backfill, provider,
  direzione e provenienza conversione.
- **Granularità**: as-of.
- **History**: no.
- **Componenti**: `fx.pair_identity`, `fx.current_rate`,
  `fx.conversion_provenance`.

### 7.2.2 Contesto di mercato FX

- **ID**: `fx.market_context`
- **Perché esiste**: piccola sintesi di mercato per Analysis non tecniche.
- **Contiene**: coverage, tasso/rendimenti/volatilità/trend/eventi focalizzati e
  history sorgente.
- **Granularità**: coppia + poche righe context.
- **Non contiene**: OHLC e tutti i Signal.
- **Componenti**: `fx.technical_coverage`, `fx.market_summary`.

### 7.2.3 Contesto tempistica conversione FX

- **ID**: `fx.conversion_timing_context`
- **Perché esiste**: evidence non predittiva per decidere come distribuire una
  conversione nel tempo.
- **Contiene**:
  - tasso/data/staleness/provider;
  - minimo/massimo osservato;
  - posizione nel range;
  - distanza dagli estremi;
  - rendimenti osservati;
  - volatilità realizzata;
  - coverage/partial history;
  - input utente mancanti.
- **Non contiene**: importo, scadenza, spread, fee o forecast.
- **Componente**: `fx.timing_context`.

### 7.2.4 Dati di mercato e tecnici FX

- **ID**: `fx.market_technical`
- **Perché esiste**: export completo della serie tasso e dei Signal FX.
- **Contiene**: coverage, OHLC tasso, rendimenti, volatilità, indicatori,
  latest/summary, history 5/10/all ed eventi 7g/min3, 21g/min10, 30g/min20.
- **Granularità**: coppia × Signal × bucket/evento.
- **Componenti**: `fx.technical_coverage`, `fx.rate_ohlc`,
  `fx.returns_volatility`, `fx.indicators`, `fx.states_events`.

### 7.2.5 Esposizione FX diretta

- **ID**: `fx.direct_exposure`
- **Perché esiste**: mostrare solo collegamenti valutari direttamente osservabili.
- **Contiene**:
  - saldi cash in base/quote;
  - posizioni con trading o valuation currency base/quote;
  - importi nativi/target e provenienza conversione;
  - riepiloghi base/quote e zero-state.
- **Granularità**: una riga per cash balance o posizione.
- **Non contiene**: esposizione economica look-through di ETF/aziende.
- **Perché**: inferire look-through sarebbe semanticamente rischioso.
- **Componenti**: `fx.exposure_base_quote`, `fx.exposure_provenance`.

### 7.2.6 Tutti i dati FX

- **ID**: `fx.all_data`
- **Contiene**: Overview + Market Technical + Direct Exposure.
- **Esclude**: Market Context e Conversion Timing Context.
- **Perché**: sono proiezioni focalizzate degli stessi tassi/history.

## 7.3 Request Analysis FX

### 7.3.1 Revisione trend FX

- **ID**: `fx.trend_review`
- **Cosa fa fare all'AI**: spiega direzione quote-per-base, movimento, extrema,
  trend, momentum, volatilità ed eventi.
- **Dataset**: Overview + Market Technical.
- **Non contiene**: esposizione dell'utente, salvo Additional Data separato.

### 7.3.2 Tempistica conversione FX

- **ID**: `fx.conversion_timing`
- **Cosa fa fare all'AI**: presenta scenari neutrali di conversione, senza point
  forecast, usando range osservato, trend, volatilità e coverage.
- **Dataset**:
  - richiesti: Overview + Market Technical + Timing Context;
  - opzionale: Direct Exposure.
- **Dati mancanti intenzionali**: importo, deadline, spread e fee devono essere
  forniti dall'utente.
- **Perché**: senza questi input non esiste un piano esecutivo corretto.

### 7.3.3 Impatto esposizione FX

- **ID**: `fx.exposure_impact`
- **Cosa fa fare all'AI**: descrive come movimenti base/quote si collegano a cash e
  posizioni dirette.
- **Dataset**:
  - richiesti: Overview + Direct Exposure;
  - opzionale: Market Context;
  - suggerito: Market Technical completo.
- **Limite**: nessun look-through e nessun forecast.

---

# 8. Valutazione della frammentazione

## 8.1 Perché il catalogo è stato diviso

La divisione nasce da quattro obiettivi corretti:

1. evitare prompt enormi;
2. fornire all'AI solo dati materialmente utili;
3. evitare duplicazione tra serie complete e proiezioni;
4. permettere ad Analysis diverse di riusare componenti deterministici.

Dal punto di vista backend è una buona architettura plugin/composition.

Nessuna Request Analysis usa `*.all_data`: ogni Analysis compone il minimo set
task-specific. `all_data` resta una scelta manuale per chi vuole consegnare
all'AI il bundle completo del dominio.

## 8.2 Perché la UI risulta confusa

La UI espone quasi direttamente mattoncini architetturali:

- Summary vs Snapshot vs Comparison;
- Context data vs Analysis con nome simile;
- Technical Summary vs Technical;
- evidence task-specific;
- All Data che non significa letteralmente ogni voce visibile.

Quindi la separazione tecnica corretta diventa carico cognitivo per l'utente.

## 8.3 Le tre famiglie più confuse

### Technical Summary / Asset Snapshot / Asset Comparison

| Scelta | Livello | Prezzo per Asset | Drawdown per Asset | Breadth/eventi |
|---|---|:---:|:---:|:---:|
| Technical Summary | aggregato | no | no | digest aggregato |
| Asset Snapshot | per Asset | sì | sì | ultimi eventi |
| Asset Comparison | per Asset | sì | no | breadth + eventi strutturali |
| Technical | per Asset/Signal/bucket | sì + history | no | completo secondo detail |

### Overview / Performance

- Overview = stato corrente, inclusi prezzi unitari.
- Performance = variazione economica nel periodo, inclusi contributor Asset.

### Context / Analysis

- `*.context` = dati.
- Analysis omonima = istruzioni + dati + struttura risposta.

## 8.4 “Tutti i dati” è tecnicamente corretto ma semanticamente ambiguo

Ogni `all_data` unisce soltanto questi dataset sorgente:

- Portfolio: Overview + Performance + Technical + FIFO;
- Broker: Overview + Performance + Technical + FIFO;
- Asset: Overview + Position Performance + Market Technical;
- FX: Overview + Market Technical + Direct Exposure.

Le altre scelte visibili sono escluse per non duplicare proiezioni/evidence.
Sarebbe utile dirlo nella UI invece di usare soltanto “Tutti i dati”.

## 8.5 Lacune o possibili miglioramenti da discutere

Nessuna modifica è stata applicata in questa attività, ma emergono questi punti:

1. aggiungere badge UI:
   - `Aggregato`;
   - `Per Asset`;
   - `Prezzo corrente`;
   - `History prezzi`;
   - `Lotti`;
2. raggruppare Export Data in:
   - Base;
   - Confronto Asset;
   - Evidenze specifiche;
   - Completo/avanzato;
3. rinominare o descrivere meglio:
   - Sintesi tecnica → “Breadth tecnica aggregata”;
   - Sintesi Asset → “Prezzi, rendimenti e Drawdown per Asset”;
   - Confronto Asset → “Prezzi, rendimenti, tecnica ed eventi per Asset”;
   - Tutti i dati → “Tutti i dati canonici completi”;
4. chiarire sulle card Analysis quali dataset individuali Asset vengono inclusi;
5. rivalutare Broker Technical: contiene history indicatori ma non una raw price
   history dedicata.
6. correggere la promessa Drawdown di **Analisi trend asset**, oggi non supportata
   dal dataset composto.

## 8.6 Conclusione

Il problema principale non è che PAC e ribilanciamento ricevano solo aggregati:
**ricevono già dati individuali Asset e prezzi correnti**.

Il problema reale è che:

- la UI non mostra la granularità;
- “current price”, “position value” e “price history” non sono distinti;
- dataset interni molto focalizzati sono esposti tutti allo stesso livello;
- `all_data` ha una semantica tecnica non evidente.

Il catalogo backend può restare modulare; la UI potrebbe diventare molto più
comprensibile raggruppando e descrivendo le stesse scelte.

## 9. Fonti e prova reale

Fonti di verità:

- `backend/app/services/ai_export/datasets/catalog.py`;
- `backend/app/services/ai_export/components/catalog.py`;
- `backend/app/services/ai_export/analyses/catalog.py`;
- `frontend/src/lib/features/ai-export/templates/sharedInstructions.ts`;
- `frontend/src/lib/features/ai-export/templates/responseContracts.ts`;
- `frontend/src/lib/i18n/it.json`;
- `mkdocs_src/docs/developer/architecture/patterns/ai_export_composition.md`.

Probe mirato usato per verificare i dubbi Portfolio:

`real_prompt_probe/20260804T085052.052297Z`

Risultati:

- 5/5 prompt;
- 0 failure;
- 0 violazioni public output;
- UI/probe equivalence;
- secret scan passed;
- source e production DB invariati.

Prompt letti:

- Portfolio Overview;
- Portfolio Asset Snapshot;
- Portfolio Asset Comparison;
- Pianificazione PAC;
- Ribilanciamento portafoglio.

### Copertura della verifica

I cinque prompt sopra sono stati generati e letti integralmente sul runtime
corrente. Le altre 44 scelte sono state verificate sul catalogo/runtime corrente,
sui modelli payload, sulle istruzioni e sui response contract; non è stato
rieseguito un probe reale da 49 prompt perché non era necessario per descrivere la
composizione dichiarativa.

### Drift documentale rilevato

La tabella iniziale nel docstring di `analyses/catalog.py` conserva alcuni mapping
storici, mentre le definizioni `_PORTFOLIO_ANALYSES`, `_BROKER_ANALYSES`,
`_ASSET_ANALYSES` e `_FX_ANALYSES` più in basso rappresentano il runtime corrente.
Questo report usa le definizioni runtime, non il riepilogo storico del docstring.
