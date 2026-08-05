# 🧠 Esportazione AI del portafoglio

L'Esportazione AI del portafoglio prepara un'istantanea negli appunti limitata alla dashboard
o un prompt di analisi mirato. LibreFolio non invia mai l'esportazione a un servizio AI.

## 📍 Posizione

Apri **Dashboard** e seleziona **AI Export** nella barra degli strumenti superiore,
accanto a **Update/Sync**. La bozza rimane disponibile per 10 minuti nella sessione
di accesso corrente e viene azzerata dopo il logout o un nuovo accesso.

## 🎯 Analisi del portafoglio

| Attività | Focus |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Piano di investimento ricorrente** | Struttura del portafoglio, flussi di cassa, vincoli e contesto dell'investimento ricorrente. |
| **Ribilanciamento del portafoglio** | Allocazione attuale, concentrazione, diversificazione e contesto dell'allocazione obiettivo. |
| **Performance del portafoglio e driver di mercato** | Riconciliazione della performance unitamente a ricerca datata a orizzonte breve e lungo per ogni asset detenuto. |
| **Strategie di compensazione delle minusvalenze** | Modalità condizionali per utilizzare perdite fiscali disponibili o in scadenza contro plusvalenze potenzialmente idonee, utilizzando evidenze FIFO economiche e l'inventario ufficiale delle perdite fiscali dell'utente. |

## 🗂️ Ambito e dati

L'esportazione segue il filtro broker attivo, l'intervallo di date e la valuta obiettivo.
A seconda della selezione, può includere totali del portafoglio, contante, posizioni,
allocazioni, performance, contributi, redditi, contesto di qualità dei dati e
risultati tecnici calcolati dal backend.

Il prompt distingue:

- broker inclusi nell'ambito di calcolo;
- broker con posizioni aperte correnti;
- broker rappresentati da contributori di performance nel periodo AI.

Un broker incluso nell'ambito di calcolo può non avere posizioni correnti. I riferimenti B# restano coerenti con
l'Entity Directory.

!!! note "Il FIFO economico non è un trattamento fiscale legale"

    L'esportazione generale contiene un riepilogo FIFO economico compatto per asset.
    **Strategie di compensazione delle minusvalenze** riceve inoltre ogni lotto applicabile.
    Prima di confrontare i percorsi di non azione, realizzazione di plusvalenze, scaglionamento o raccolta di perdite,
    il prompt chiede residenza fiscale, regime, tipo di conto, inventario ufficiale delle perdite fiscali
    (ad esempio il `cassetto fiscale` italiano), categoria legale,
    importi rimanenti e utilizzati, date di origine/scadenza, regole di compensazione e vincoli.

## 📤 Export Data e Request Analysis

- **Export Data** copia un dataset fattuale del portafoglio senza istruzioni di analisi
 o contratto di risposta.
- **Request Analysis** aggiunge istruzioni specifiche per l'attività, un contratto di risposta e
 i dataset dichiarati per l'Analisi selezionata.
 La lingua della risposta richiesta segue sempre la lingua corrente dell'interfaccia
 LibreFolio.
- Le note opzionali sono incluse solo per le analisi che le supportano.

Sono disponibili due esportazioni di dati pubbliche:

- **Portfolio Overview & History** — posizioni, contante, allocazioni, concentrazione,
 percorso di performance, flussi, redditi, costi, riconciliazione, riepilogo FIFO economico,
 storia compatta per asset, Drawdown, copertura e provenienza;
- **Portfolio Asset History** — bucket più densi di prezzi di chiusura osservati, indicatori,
 stati, eventi, copertura e ampiezza per l'universo di asset idonei.

## 📅 Piano di investimento ricorrente

L'Analisi utilizza prima i fatti forniti e chiede solo le preferenze mancanti che
modificano sostanzialmente il piano. Le domande sono raggruppate in:

- capitale e frequenza dei contributi;
- obiettivi e orizzonte;
- preferenze di rischio, inclusa la volatilità accettabile o il Drawdown temporaneo;
- vincoli operativi come liquidità, broker, ordini minimi, esclusioni
 o se le vendite sono consentite.

Il prompt distingue le risposte indispensabili dai perfezionamenti opzionali e può
comunque offrire scenari condizionali. Non inventa mai budget, obiettivi o tolleranza
al rischio.

Confronta il dispiegamento immediato e quello scaglionato. L'attesa condizionale appare solo
quando esistono evidenze di declino ampie e persistenti nell'intero portafoglio, mai
da un singolo asset o un singolo indicatore.

Il Drawdown del portafoglio e un confronto compatto del Drawdown per asset sono solo contesto
storico. Non sono previsioni né segnali d'acquisto a sé stanti e non viene aggiunta alcuna
storia di Drawdown per asset.

## 📰 Performance e driver di mercato

All'AI ricevente viene richiesto di coprire ogni asset detenuto, citare fonti datate,
valutare la qualità delle fonti, fornire tesi a orizzonte breve e lungo, distinguere
cronologia/correlazione dalla causalità ed etichettare i collegamenti come supportati,
plausibili, inferiti, speculativi o inspiegati.

## 📏 Dettaglio e campionamento

| Dettaglio | Campionamento esatto |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Compatto** | Esportazione generale: 8 punti del percorso del portafoglio e fino a 6 punti per asset idoneo. Esportazione dettagliata: fino a 5 righe di indicatori non vuote per asset/segnale. |
| **Standard** | Esportazione generale: 16 punti del percorso del portafoglio e fino a 12 punti per asset idoneo. Esportazione dettagliata: fino a 10 righe di indicatori. |
| **Completo** | Esportazione generale: 30 punti del percorso del portafoglio e fino a 24 punti per asset idoneo. Esportazione dettagliata: ogni bucket non vuoto di indicatori; può essere molto grande. |

Un dataset o un'Analisi può omettere sezioni opzionali non disponibili o non applicabili.
Il **periodo AI** utilizza 3M, 6M, 1Y o Personalizzato quando offerto e termina sempre alla
data dell'istantanea. Le righe temporali completamente vuote vengono omesse, mentre i metadati
di periodo/copertura e i valori zero osservati rimangono.

## 🔒 Applicabilità, errori e privacy

Le attività o le scelte di dettaglio non disponibili restano disabilitate. AI Export adotta
inoltre un comportamento fail-closed quando i cataloghi del browser e del server o i contratti
di risposta non corrispondono. Gli errori tipizzati spiegano l'applicabilità mancante, le entità
inaccessibili, i fallimenti delle fonti o i problemi di contratto senza esporre dettagli interni.

Gli appunti possono contenere dati finanziari sensibili. Rivedili prima di incollarli
in un servizio di terze parti. Consulta la [panoramica AI Export](index.md)
per il flusso di lavoro cross-domain e il modello di sicurezza.
