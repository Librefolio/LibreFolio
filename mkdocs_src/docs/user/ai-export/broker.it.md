# 🧠 Esportazione AI del Broker

L'esportazione AI del Broker prepara un'istantanea degli appunti o un prompt di analisi limitato a un
broker accessibile. LibreFolio non la invia mai a un servizio AI.

## 📍 Posizione

Aprire una pagina di dettaglio del Broker e selezionare **Esportazione AI** nella barra degli strumenti superiore. La bozza
rimane disponibile per 10 minuti nella sessione di accesso corrente e si azzera dopo
il logout o un nuovo accesso.

## 🎯 Analisi del Broker

| Attività | Focus |
| ------------------------------------------- | ------------------------------------------------------------------------- |
| **Revisione del Broker** | Posizioni, liquidità, attività, performance e copertura dei dati. |
| **Performance del Broker e Driver di Mercato** | Riconciliazione della performance più ricerca con datazione per ogni Asset detenuto tramite il Broker. |
| **Strategie di Compensazione delle Minusvalenze** | Modalità condizionali per utilizzare perdite fiscali disponibili o in scadenza contro plusvalenze potenzialmente ammissibili utilizzando evidenze FIFO economiche del Broker selezionato. |

## 🗂️ Ambito e Dati

L'esportazione è limitata al broker selezionato, all'intervallo di date corrente e alla valuta
di destinazione. A seconda della selezione, può includere saldi di cassa, posizioni,
transazioni, performance, costi, allocazione, concentrazione, redditi e riepiloghi
dei lotti FIFO. I controlli di accesso lato server impediscono l'esportazione di un broker che
l'utente corrente non può leggere.

!!! important "I costi allocati e non allocati rimangono distinti"

    Le righe FIFO contengono solo commissioni e imposte allocate deterministicamente ai lotti.
    I costi non allocati a livello di Broker rimangono nelle evidenze finanziarie generali e
    non vengono mai presentati come costi di lotto pari a zero.

## 📤 Esportazione Dati e Richiesta di Analisi

- **Esporta Dati** copia solo un dataset fattuale del Broker.
- **Richiedi Analisi** aggiunge istruzioni specifiche per il compito, un contratto di risposta e
 i dataset dichiarati per l'Analisi.
 La lingua della risposta richiesta segue la lingua corrente dell'interfaccia di
 LibreFolio.
- Le note facoltative sono incluse solo quando supportate dall'Analisi selezionata.

Sono disponibili due esportazioni di dati pubbliche:

- **Panoramica e Cronologia del Broker** — posizioni del Broker selezionato, liquidità, concentrazione,
 percorso di performance, flussi, costi, rapporti, riepilogo FIFO economico, cronologia compatta per Asset,
 Drawdown, copertura e provenienza;
- **Cronologia degli Asset del Broker** — bucket di prezzi di chiusura osservati nell'ambito del Broker,
 indicatori, stati, eventi, ampiezza e motivi espliciti per gli Asset correnti
 esclusi dall'ammissibilità tecnica.

## 🧾 Strategie di Compensazione delle Minusvalenze

Il prompt utilizza i lotti FIFO economici del Broker selezionato per identificare candidati condizionali di plusvalenze
e minusvalenze, ma non li tratta mai automaticamente come legalmente ammissibili. In
primo luogo richiede residenza fiscale, regime, tipo di conto, inventario ufficiale delle perdite fiscali,
importi per categoria legale, date di origine e scadenza, saldi già utilizzati, regole di
compensazione e se i saldi tra Broker/conti possono essere combinati.

Può quindi confrontare il non intervento, la realizzazione di plusvalenze ammissibili prima della scadenza, la realizzazione
scaglionata allineata al ribilanciamento e la raccolta delle perdite quando pertinente. Ogni
percorso mostra costi, variazioni dell'esposizione, liquidità, concentrazione, tempistica e incertezza
giuridica; nessuna operazione viene raccomandata esclusivamente per motivi fiscali.

## 📏 Dettaglio e Campionamento

| Dettaglio | Campionamento esatto |
| ------------ | -------------------------------------------------------------------------------- |
| **Compatto** | Stesso universo di dati con i bucket temporali supportati più radi (fino a 30 giorni). |
| **Standard** | Stesso universo di dati con bucket temporali fino a 14 giorni. |
| **Completo** | Stesso universo di dati con bucket temporali fino a 7 giorni. |

L'esportazione generale utilizza 8/16/30 punti del percorso del Broker e fino a 6/12/24 punti
di cronologia compatta per Asset ammissibile. L'esportazione dettagliata mantiene l'intera politica
di campionamento tecnico e può essere di grandi dimensioni.

Un dataset o un'Analisi può omettere sezioni facoltative non disponibili o non applicabili.
Il **periodo AI** termina alla data dell'istantanea. La cronologia parziale e la copertura rimangono
esplicite.

## 🔒 Applicabilità, Errori e Privacy

Le analisi possono non essere disponibili quando i fatti richiesti non esistono. Le scelte falliscono inoltre
bloccandosi in caso di mancata corrispondenza di catalogo o contratto. Gli errori tipizzati segnalano problemi di
accesso, applicabilità, origine o contratto.

Gli appunti possono contenere dati sensibili di conti e transazioni. Rivedere gli appunti
prima della condivisione. Vedere la [Panoramica dell'esportazione AI](index.md) per il
flusso di lavoro cross-domain e il modello di sicurezza.
