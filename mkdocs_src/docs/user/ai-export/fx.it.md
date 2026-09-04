# 🧠 FX AI Export

FX Detail AI Export prepara un'istantanea per gli appunti o un prompt di analisi
mirata per la coppia di valute canonica attualmente aperta. LibreFolio non invia
mai questi dati a un servizio di intelligenza artificiale.

## 📍 Posizione

Apri una pagina di dettaglio FX. Nell'intestazione **Signals**, seleziona
**AI Export**. La bozza rimane disponibile per 10 minuti nella sessione di
accesso corrente e viene azzerata dopo il logout o un nuovo accesso.

## 🎯 Analisi FX

| Attività | Focus |
| --- | --- |
| **FX Pair Analysis** | Direzione della coppia, rendimenti, volatilità, evidenze tecniche, copertura e contesto macro con data. |
| **FX Exposure Impact** | Collegamenti diretti alla coppia da cassa, valuta di negoziazione e valuta di valutazione. |

## 🗂️ Ambito e dati

L'esportazione utilizza la coppia canonica della pagina, l'intervallo di date
selezionato, la valuta di destinazione, la cronologia dei tassi, il contesto del
provider e i risultati tecnici calcolati dal backend.

## 📤 Export Data e Request Analysis

- **Export Data** copia solo un set di dati FX fattuale.
- **Request Analysis** aggiunge istruzioni specifiche per l'attività, un contratto
 di risposta e i set di dati dichiarati per l'Analisi.
 La lingua della risposta richiesta segue la lingua corrente dell'interfaccia di
 LibreFolio.
- Le note opzionali sono incluse solo quando supportate dall'Analisi selezionata.

Sono disponibili due esportazioni pubbliche di dati:

- **FX Market & Exposure** — tasso corrente quote-per-base, 8/16/30 punti
 osservati del percorso, trend/momentum/volatilità mirati, rendimenti a 30 e 91
 giorni, posizione nel range, copertura delle fonti, input utente mancanti ed
 esposizione diretta;
- **FX Market History** — bucket di tassi più fitti, rendimenti, indicatori,
 stati, eventi e copertura.

## 📉 Cronologia parziale

Quando il periodo AI richiesto inizia prima della cronologia dei tassi
memorizzata, LibreFolio esporta la cronologia effettiva che può utilizzare e
riporta:

- date richieste e disponibili;
- copertura;
- conteggi osservati e riempiti a ritroso;
- segnale parziale;
- segnale omesso e relative motivazioni;
- avvisi di cronologia insufficiente.

Non viene utilizzato alcun tasso futuro. Un segnale parziale non viene presentato
come equivalente a una cronologia completa.

## 📏 Dettaglio e campionamento

| Dettaglio | Campionamento esatto |
| --- | --- |
| **Compatto** | Esportazione generale: fino a 8 punti di tasso osservati in modo uniforme. Esportazione dettagliata: fino a 5 righe di indicatori non vuote per segnale. |
| **Standard** | Esportazione generale: fino a 16 punti. Esportazione dettagliata: fino a 10 righe di indicatori. |
| **Completo** | Esportazione generale: fino a 30 punti. Esportazione dettagliata: include ogni bucket di indicatori non vuoto e può essere di grandi dimensioni. |

Un set di dati o un'Analisi può omettere sezioni opzionali non disponibili o non
applicabili. Il **periodo AI** termina alla data dell'istantanea.

## 🔒 Applicabilità, errori e privacy

Le Analisi o le scelte di dettaglio possono essere disabilitate quando i dati
richiesti sono assenti. Le discrepanze tra catalogo e contratto di risposta
falliscono in modalità chiusa. Gli errori tipizzati segnalano problemi di
applicabilità, origine, entità o contratto.

Gli appunti possono contenere dati sensibili relativi all'esposizione valutaria
e di portafoglio. Rivedili prima di condividerli. Consulta la [panoramica di AI
Export](index.md) per il flusso di lavoro cross-domain e il modello di sicurezza.
