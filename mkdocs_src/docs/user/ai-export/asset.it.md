# 🧠 Esportazione AI degli Asset

L'Esportazione AI dei Dettagli dell'Asset prepara un'istantanea negli appunti o un prompt di analisi mirato
per l'asset attualmente aperto. LibreFolio non invia mai tali contenuti a un servizio AI.

## 📍 Posizione

Apri una pagina di dettaglio dell'Asset. Nella **barra degli strumenti della pagina**, seleziona **AI Export**. La bozza
rimane disponibile per 10 minuti nella sessione di accesso corrente e si azzera
dopo il logout o un nuovo accesso.

## 🎯 Analisi degli Asset

| Attività | Focus |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Revisione della Posizione** | Dimensioni della posizione, base di costo, performance, reddito e concentrazione. |
| **Analisi di Mercato dell'Asset** | Cronologia dei prezzi di chiusura osservati, rendimenti, trend, momentum, volatilità, Drawdown, stati, eventi e copertura. |

## 🗂️ Ambito e Dati

L'esportazione utilizza l'asset corrente, l'intervallo di date selezionato, la valuta di visualizzazione/obiettivo,
e l'ambito del broker accessibile all'utente quando è richiesto il contesto del portafoglio.
A seconda della selezione, può includere identificativi, prezzi, rendimenti, valutazione,
dati di posizione e FIFO, reddito, eventi societari e risultati tecnici calcolati dal backend.
Il browser non ricalcola gli indicatori.

## 📤 Dati Esportati e Richiesta di Analisi

- **Export Data** copia un dataset fattuale selezionato dell'Asset senza istruzioni
 di analisi o interpretazione.
- **Request Analysis** utilizza i dati rilevanti e aggiunge istruzioni specifiche
 per l'attività, oltre a un contratto di risposta, così che l'AI ricevente possa interpretarli.
 La lingua della risposta richiesta segue la lingua corrente dell'interfaccia LibreFolio.
- Le note opzionali sono incluse solo quando supportate dall'Analisi selezionata.

Sono disponibili due esportazioni pubbliche di dati:

- **Posizione e Cronologia di Mercato (completa)** — posizioni per Broker, costo, valore, P&L,
 semantica dei periodi a zero registrato, lotti economici con commissioni/imposte allocate,
 cronologia di mercato compatta, Drawdown e provenienza;
- **Solo Cronologia di Mercato (senza posizioni)** — bucket di chiusura osservati, rendimenti, indicatori, stati,
 eventi, Drawdown e copertura.

## 📏 Dettaglio e Campionamento

| Dettaglio | Campionamento esatto |
| ------------ | --------------------------------------------------------------------------------------------------------------------------- |
| **Compatto** | Esportazione posizione: fino a 8 punti uniformi di cronologia osservata. Esportazione mercato: fino a 5 righe di indicatori non vuote per segnale. |
| **Standard** | Esportazione posizione: fino a 16 punti. Esportazione mercato: fino a 10 righe di indicatori. |
| **Completo** | Esportazione posizione: fino a 30 punti. Esportazione mercato: include ogni bucket di indicatori non vuoto e può quindi risultare di grandi dimensioni. |

Un dataset o un'Analisi può omettere sezioni opzionali non disponibili o non applicabili.
Il **periodo AI** termina alla data dell'istantanea. Le date disponibili, la copertura, il segnale
parziale e i motivi delle omissioni rimangono espliciti.

## 🔒 Applicabilità, Errori e Privacy

La Revisione della Posizione richiede il contesto della posizione. Altre attività possono essere
disabilitate quando i dati richiesti sono assenti. Le discrepanze tra catalogo e contratto di
risposta attivano la modalità fail-closed. Gli errori tipizzati segnalano applicabilità,
entità mancanti, errori di origine o problemi contrattuali.

Gli appunti possono contenere dati sensibili su posizioni e performance. Rivedili
prima di condividerli. Consulta la [panoramica AI Export](index.md) per
il flusso di lavoro cross-domain e il modello di sicurezza.
