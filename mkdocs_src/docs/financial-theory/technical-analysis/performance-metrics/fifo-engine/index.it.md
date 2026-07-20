# 🧬 Motore FIFO — Ciclo di Vita dei Lotti e Modello di Abbinamento

*[⬅️ Torna alla Panoramica delle Metriche di Performance](../index.md)*

## 💡 Panoramica

Mentre il [Prezzo Medio di Carico (PMC)](../weighted-average-cost.md) fonde ogni acquisizione di una posizione in un'unica media mobile, il motore FIFO di LibreFolio tiene traccia dei **lotti individuali** — uno per lotto di acquisizione — attraverso il loro intero ciclo di vita: apertura, chiusure parziali, trasferimenti tra broker, frazionamenti ed eventuale chiusura totale.

Questa pagina descrive il **funzionamento** di quel motore: come i lotti vengono creati, abbinati e chiusi. Per le **metriche** derivate da questo motore (Rendimento Aperto/Totale, ridimensionamento qbq, allocazione del reddito, un esempio pratico), consulta [Analisi dei Lotti FIFO](fifo-lot-analysis.md).

!!! info "Due motori, due domande"

    [Motore di Portafoglio](../index.md) (basato sul PMC) risponde: _"Qual è il mio prezzo medio di carico per questa posizione?"_

    Il motore FIFO risponde a una domanda strutturalmente diversa: _"Quale specifico lotto di unità sto vendendo e come si è comportato esattamente quel lotto?"_

---

## 🧱 Cos'è un Lotto?

Un **lotto** è un singolo lotto di acquisizione economica per un asset: un singolo ACQUISTO, il residuo aperto di una rettifica di inventario, o un trasferimento in entrata che preserva la sua base di costo originale. Un lotto mantiene la propria identità per tutta la sua vita, anche quando si sposta tra broker o si divide in pezzi.

| Proprietà | Significato |
|----------|-------------|
| Direzione | `LONG` (acquistato prima) o `SHORT` (venduto prima, solo dove il broker consente lo short) |
| Data e broker di apertura | Dove e quando il lotto è stato creato |
| Quantità e costo originali | Fissati all'apertura, successivamente ridimensionati solo da frazionamenti — mai da trasferimenti |
| Quantità aperta | Quanto del lotto **non** è stato ancora abbinato da una transazione opposta |
| Custodia | Quale broker (o broker, nel tempo) detiene attualmente la quantità aperta |

---

## 🔁 Stati del Ciclo di Vita del Lotto

| Stato | Significato |
|-------|-------------|
| **APERTO** | Nulla è stato ancora abbinato — l'intera quantità originale è ancora detenuta |
| **PARZIALMENTE_CHIUSO** | Una parte, ma non tutta, del lotto è stata abbinata da successive transazioni opposte |
| **CHIUSO** | L'intero lotto è stato abbinato — non rimane nulla di aperto |

Un lotto procede APERTO → PARZIALMENTE_CHIUSO → CHIUSO rigorosamente in avanti nel tempo man mano che l'abbinamento lo consuma; non si riapre mai. Indipendentemente da questo ciclo di vita, un lotto può anche essere etichettato:

- **IN_TRANSITO** — parte della sua quantità aperta è attualmente in fase di trasferimento tra broker
- **DISTRIBUITO** — la sua quantità aperta è attualmente suddivisa in più di una sede di custodia contemporaneamente
- **DEGRADATO** — un problema di qualità dei dati è stato registrato contro questo specifico lotto (vedi [Qualità dei Dati](#data-quality-best-effort-not-all-or-nothing) di seguito)

---

## 📅 Elaborazione Cronologica degli Eventi

LibreFolio riproduce ogni transazione per un asset **in ordine cronologico**, classificando ciascuna in un tipo di evento:

| Evento | Effetto |
|-------|--------|
| ACQUISTO | Prima chiude eventuali lotti SHORT aperti su quel broker; eventuale residuo apre un nuovo lotto LONG |
| VENDITA | Chiude i lotti LONG aperti in ordine FIFO su quel broker; eventuale residuo apre un nuovo lotto SHORT solo dove il broker consente lo short |
| Rettifica in / out | Stessa logica di abbinamento di ACQUISTO/VENDITA, a costo zero |
| FRAZIONAMENTO | Ridimensiona quantità e costo unitario per ogni lotto aperto dell'asset |
| Trasferimento (partenza / arrivo) | Sposta la custodia della quantità aperta di un lotto da un broker all'altro |

!!! info "Ordinamento dello stesso giorno"

    Quando più eventi cadono nella stessa data, LibreFolio li elabora sempre in un ordine fisso — partenze di trasferimenti, poi arrivi di trasferimenti, poi frazionamenti, poi acquisti/vendite/rettifiche ordinarie — in modo che i trasferimenti e i frazionamenti dello stesso giorno vedano sempre uno stato di custodia coerente.

---

## ⛏️ Abbinamento FIFO

Quando un evento di chiusura (una VENDITA, o la gamba di direzione opposta di una rettifica) deve consumare una quantità $Q$, LibreFolio si abbina sempre al **lotto aperto più vecchio per primo**, sullo stesso broker:

$$
\text{OrdineAbbinamento} = \text{ordina per } (\text{DataApertura}, \text{IdLotto})
$$

Scorre questo elenco ordinato, chiudendo la quantità dal lotto più vecchio fino a quando $Q$ non è completamente abbinata, passando al lotto successivo più vecchio solo quando quello corrente è esaurito. Il profitto o la perdita realizzati vengono calcolati **per pezzo abbinato**, utilizzando il prezzo trasportato dall'esatto frammento di lotto consumato:

$$
\text{PnLRealizzato}_{\text{LONG}} = \text{QuantitàAbbinata} \times (\text{PrezzoChiusura} - \text{CostoUnitarioLotto})
$$

$$
\text{PnLRealizzato}_{\text{SHORT}} = \text{QuantitàAbbinata} \times (\text{CostoUnitarioLotto} - \text{PrezzoChiusura})
$$

Ecco perché due lotti dello stesso asset, acquistati a tempi e prezzi diversi, possono mostrare risultati realizzati molto diversi anche se successivamente vengono abbinati lo stesso giorno allo stesso prezzo — vedi l'esempio pratico in [Analisi dei Lotti FIFO](fifo-lot-analysis.md).

---

## ✂️ Frazionamenti — Ridimensionamento Quantità/Prezzo

Un frazionamento azionario (o raggruppamento) con rapporto $r$ ridimensiona ogni **frammento attualmente aperto** di ogni lotto interessato:

$$
\text{NuovaQuantità} = \text{Quantità} \times r
\qquad
\text{NuovoCostoUnitario} = \frac{\text{CostoUnitario}}{r}
$$

Il costo economico della posizione è invariante attraverso un frazionamento — solo la quantità e il costo per unità si muovono, in direzioni opposte, quindi $\text{Quantità} \times \text{CostoUnitario}$ rimane costante per ogni lotto.

---

## 🚚 Trasferimenti — Movimento di Custodia, Non una Vendita

Un trasferimento tra broker è modellato come una **variazione di custodia**, mai come una dismissione:

- **Partenza** — LibreFolio estrae la quantità trasferita dal broker di origine in ordine FIFO. Se il trasferimento richiede più di un giorno per essere regolato, apre temporaneamente un frammento di custodia **in transito** nel frattempo.
- **Arrivo** — All'arrivo, il frammento in transito si chiude e un frammento equivalente si riapre presso il broker di destinazione, mantenendo la **stessa quantità e costo unitario**.

L'identità del lotto, la data di apertura e il costo originale non cambiano mai a causa di un trasferimento — solo *dove* è attualmente detenuto. Nessun profitto o perdita viene mai realizzato da un trasferimento.

Questa cronologia di custodia — quale broker (o in transito) ha detenuto la quantità aperta di un lotto, e quanta, in ogni momento — è esattamente ciò che alimenta la timeline **Vita del Lotto e Custodia** nel pannello [Analisi dei Lotti FIFO](../../../../user/dashboard/positions.md#fifo-lots-analysis): ogni segmento della barra è colorato dal broker di custodia che lo detiene, e il suo spessore riflette la quantità detenuta durante quel segmento.

---

## ⚠️ Qualità dei Dati: Al Meglio delle Possibilità, Non Tutto o Nulla {: #data-quality-best-effort-not-all-or-nothing }

Se la cronologia delle transazioni contiene qualcosa che il motore non può risolvere completamente — ad esempio una transazione di chiusura senza un lotto aperto corrispondente su quel broker, o un trasferimento la cui gamba abbinata è mancante — LibreFolio **non** interrompe l'intero calcolo. Registra il problema specifico, contrassegna il/i lotto/i interessato/i come degradato e continua a elaborare il resto della cronologia con i migliori dati disponibili.

Il risultato complessivo viene quindi contrassegnato come **completo** o **degradato** nel suo insieme, ma i grafici e le tabelle basati su un risultato degradato vengono comunque visualizzati normalmente per ogni lotto che **non** è stato interessato. Potresti vederlo riflesso come un banner di qualità dei dati nel pannello [Analisi dei Lotti FIFO](../../../../user/dashboard/positions.md#fifo-lots-analysis).

---

## 🔗 Correlati

- 🔬 **[Analisi dei Lotti FIFO](fifo-lot-analysis.md)** — Metriche derivate da questo motore: Rendimento Aperto/Totale per lotto, ridimensionamento qbq, allocazione del reddito, esempio pratico
- ⚙️ **[Motore di Portafoglio](../index.md)** — Il motore complementare aggregato/basato su PMC e come i due si relazionano
- 📊 **[Prezzo Medio di Carico (PMC)](../weighted-average-cost.md)** — Base di costo mista a livello di posizione
- 🧬 **[Motore Lotti FIFO (Manuale dello Sviluppatore)](../../../../developer/backend/transactions/fifo_lot_engine.md)** — Approfondimento implementativo: classi, dispatch degli eventi, vincoli a livello di codice
