# 📅 Annualizzazione osservata

Annualizzare una cifra di rischio richiede di sapere quanti periodi contiene un anno, e quel numero può essere misurato dai dati osservati invece di essere assunto in anticipo. LibreFolio lo misura: il fattore usato per rapportare una cifra per periodo a una cifra annuale è **contato dalla serie che è stata effettivamente analizzata**, mai preso da una convenzione di mercato fissata in anticipo.

---

## 🔢 Formula {: #formula }

Due quantità vengono lette dalla serie prima che qualsiasi cifra venga annualizzata — l'intervallo di calendario che copre, e il numero di rendimenti osservati all'interno di tale intervallo:

$$
D = d_{last} - d_{baseline}
$$

$$
f = \frac{N \times 365}{D}
$$

dove:

- $N$ = numero di rendimenti di periodo effettivamente utilizzati
- $d_{baseline}$ = data della prima valutazione (apre la serie e quindi non produce un rendimento proprio)
- $d_{last}$ = data dell'ultimo rendimento
- $D$ = giorni di calendario coperti, weekend e chiusure inclusi

Il fattore $f$ viene quindi applicato ovunque una cifra per periodo debba essere espressa su base annuale. Per la volatilità:

$$
\sigma_{annual} = \sigma_{period} \times \sqrt{f}
$$

!!! info "È un conteggio, non una convenzione"

    $f$ ha una lettura letterale: **osservazioni all'anno, contate**. Una serie con $N$ rendimenti distribuiti su $D$ giorni di calendario è stata osservata a un tasso di $N/D$ al giorno, quindi $365N/D$ all'anno. Non viene fatta alcuna ipotesi sullo strumento, sul suo calendario di mercato o sulla sua classe di attività — il tasso è quello che i dati risultano essere. L'unico elemento di conoscenza del calendario che entra in gioco decide cosa conta come osservazione, mai quante dovrebbero essercene: un prezzo memorizzato che ripete solo la chiusura precedente in un weekend o in un giorno festivo di mercato è un riporto, non una quotazione (vedi [sotto](#252-is-recovered-not-imposed)).

Se l'intervallo collassa — una singola data di valutazione, quindi $D \leq 0$ — non esiste alcun fattore e non viene prodotta alcuna cifra annualizzata. L'alternativa sarebbe inventarne una.

---

## 💡 Interpretazione {: #interpretation }

La tabella seguente sviluppa la formula per alcune forme di serie. È aritmetica, non l'output di un'esecuzione di LibreFolio:

| Serie | Rendimenti $N$ | Giorni di calendario $D$ | $f = 365N/D$ | $\sqrt{f}$ |
|---|---|---|---|---|
| Strumento quotato solo nei giorni di negoziazione, anno completo | 252 | 365 | 252.0 | 15.87 |
| Strumento negoziato ogni giorno (cripto), anno completo | 365 | 365 | 365.0 | 19.10 |
| Fondo con prezzo settimanale, anno completo | 52 | 365 | 52.0 | 7.21 |
| Strumento quotato nei giorni di negoziazione, iniziato a metà periodo | 126 | 183 | 251.3 | 15.85 |
| Serie giornaliera con lacune | 180 | 365 | 180.0 | 13.42 |

Da quelle righe seguono quattro letture.

### 📈 √252 viene ritrovato, non imposto {: #252-is-recovered-not-imposed }

Uno strumento quotato solo mentre il suo mercato è aperto contribuisce con circa 252 rendimenti in un anno solare completo, quindi $f = 252 \times 365 / 365 = 252$ e il familiare $\sqrt{252}$ emerge dalla misurazione. Il numero convenzionale è **un risultato** qui, non un input — ed è proprio per questo che non si perde nulla rifiutandosi di codificarlo in modo fisso.

Viene fuori anche quando la fonte dei prezzi fornisce una riga per ogni giorno di calendario. Alcune fonti ripetono l'ultima chiusura nei giorni in cui il mercato è chiuso — justETF, per esempio, ripete la chiusura del venerdì il sabato e la domenica. Contate come quotazioni, quelle righe aggiungerebbero un rendimento nullo che nessun mercato ha prodotto per ogni giorno di chiusura, e spingerebbero $f$ verso 365. Non vengono contate: un prezzo memorizzato datato di sabato, domenica o in un giorno festivo infrasettimanale di mercato la cui chiusura ripete **esattamente** la chiusura della riga precedente è un **riporto** — l'ultima quotazione rimasta valida, non una nuova — e la sua data non aggiunge alcuna osservazione alla serie. Un prezzo che si è mosso in un giorno di chiusura resta una quotazione, come fanno i prezzi del fine settimana di un cripto-asset, e così fa un prezzo invariato in un normale giorno feriale, come un giorno piatto di un'obbligazione. Lo strumento mantiene i suoi giorni di negoziazione, e $f$ resta vicino a 252. La regola completa, con le borse i cui giorni festivi contano, è in [Qualità dei dati](data-quality.md#stored-carries).

!!! info "Una serie di portafoglio viene letta nei giorni di quotazione delle sue posizioni"

    Quella riga descrive i prezzi quotati di uno strumento; la serie dei rendimenti di un **portafoglio** vi arriva per un'altra via. Il [rendimento ponderato per il tempo](../performance-metrics/portfolio-engine/twrr.md) del portafoglio è calcolato un giorno di calendario alla volta, weekend e festivi inclusi, mantenendo l'ultimo prezzo noto dove nulla è stato quotato. L'analisi del rischio la legge solo nei suoi **giorni di osservazione** — i giorni in cui almeno una delle posizioni detenute alla fine del periodo analizzato aveva una quotazione propria — e concatena il rendimento di ogni altro giorno nel successivo giorno di osservazione, così il rendimento cumulato è esattamente quello che era: cambia solo il campionamento. Un portafoglio di azioni e fondi quotati nei giorni di negoziazione contribuisce quindi con circa 252 rendimenti all'anno, come la prima riga, sebbene la sua storia abbia un punto per ogni giorno di calendario; uno che detiene uno strumento quotato ogni giorno di calendario, come un cripto-asset, viene osservato ogni giorno, come la seconda. Il fattore segue la serie su cui è calcolata la metrica, ed è esattamente per questo che viene misurato anziché assunto.

### 🪙 Uno strumento 24/7 dà ≈ √365 {: #a-247-instrument-gives-365 }

Uno strumento che viene negoziato ogni giorno di calendario è osservato 365 volte all'anno, quindi $f \approx 365$. Un $\sqrt{252}$ codificato in modo fisso applicato ad esso **sottostimerebbe** la sua volatilità annualizzata di un fattore di:

$$
\frac{\sqrt{365}}{\sqrt{252}} \approx 1.20
$$

L'errore non è un dettaglio di arrotondamento: è sistematico, e punta sempre nella direzione rassicurante.

### 📐 Il fattore misura un tasso, non una lunghezza {: #the-factor-measures-a-rate-not-a-length }

La quarta riga è un'azione con prezzo giornaliero osservata per circa mezzo anno: $f$ si attesta ancora vicino a 252, perché numeratore e denominatore si riducono insieme. Una finestra più breve non riduce il fattore — lo rende solo più rumoroso (vedi le limitazioni sotto).

### 🕳️ Le lacune lo abbassano, onestamente {: #gaps-lower-it-honestly }

Festivi, prezzi mancanti, un asset iniziato a metà periodo: ciò che è stato osservato è ciò che viene contato. Una serie con lacune viene annualizzata come la serie sparsa che è, anziché come la serie densa che si presumeva fosse.

---

## 📏 Copertura {: #coverage }

Insieme al fattore, una seconda quantità viene pubblicata con il risultato: dei giorni in cui la serie avrebbe potuto essere osservata, la quota in cui lo è stata.

$$
c = \frac{N}{Q}
$$

dove $Q$ è il numero di quei giorni. La copertura dice quanto **densamente** la serie è stata campionata, come frazione tra 0 e 1. Non è un secondo fattore di annualizzazione: $f$ dice a quale tasso la serie è stata osservata, $c$ dice quante delle sue possibili osservazioni ha mantenuto. Quali giorni contano in $Q$ dipende da come è costruita la serie:

- Una serie di **strumento** — e qualsiasi serie costruita dai prezzi di più asset — scorre su un calendario congiunto. Ogni data nella finestra richiesta in cui almeno uno degli asset ha una quotazione propria è una candidata, e una candidata diventa un'osservazione solo se ogni asset può essere valutato in essa, incluso un prezzo mantenuto da una data precedente. $Q$ conta le candidate, a parte la baseline. Per uno strumento quotato solo mentre il suo mercato è aperto, le candidate sono il calendario del mercato stesso, quindi i suoi giorni di chiusura non costano nulla: un riporto non è una quotazione, e non aggiunge alcuna candidata.
- Una serie di **portafoglio** è il suo rendimento ponderato per il tempo letto nei suoi giorni di osservazione (vedi [sopra](#252-is-recovered-not-imposed)), con il suo primo punto mantenuto come baseline. $Q$ conta i giorni di osservazione dopo la baseline, fino all'ultimo rendimento. La storia del portafoglio ha un punto per ogni giorno di calendario, quindi per un portafoglio detenuto senza interruzioni ogni giorno di osservazione ne porta uno, e la copertura si colloca in cima al suo intervallo per costruzione. Solo se nessuna delle posizioni detenute ha una quotazione propria nella finestra viene mantenuto ogni giorno di calendario, e $Q$ è allora l'intervallo $D$.

Ciò che la copertura **non** dice è se i prezzi dietro quelle osservazioni fossero reali. Su un calendario congiunto, una data in cui solo alcuni degli asset erano quotati è comunque un'osservazione, gli altri entrano con un prezzo mantenuto; nel giorno di osservazione di un portafoglio, ogni posizione non quotata quel giorno entra al suo ultimo valore noto. Quindi una copertura alta non è un certificato e una bassa non è un difetto: entrambe descrivono *quante delle possibili osservazioni la serie ha mantenuto*, non la qualità di ciò che contengono. Quella seconda domanda — questi prezzi erano quotati, o mantenuti? — è compito di [Qualità dei dati](data-quality.md).

!!! info "Entrambe le cifre viaggiano con il risultato"

    Ogni risultato di rischio porta con sé gli input della propria annualizzazione nei suoi metadati — il numero di osservazioni, i giorni di calendario coperti, il fattore e la copertura. Una cifra annuale pubblicata può quindi essere ricalcolata a mano dagli stessi input che l'hanno prodotta.

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "Un intervallo breve rende il fattore instabile"

    Il denominatore è l'intervallo di calendario osservato. Su poche settimane $D$ è piccolo, quindi un'osservazione mancante o una in più muove $f$ in modo apprezzabile, e $\sqrt{f}$ con essa. La cifra annualizzata eredita quell'instabilità: viene estrapolata da una finestra molto più breve dell'anno che pretende di descrivere.

!!! warning "Misurare il fattore non ripara l'ipotesi"

    Rapportare tramite $\sqrt{f}$ deriva dal fatto che la varianza si somma attraverso periodi **indipendenti** (vedi [Volatilità](volatility.md)). Se i rendimenti sono autocorrelati — trend, clustering della volatilità, ritorno alla media — la cifra riscalata è distorta indipendentemente da quanto accuratamente è stato contato $f$. Misurare il fattore rimuove una costante sbagliata; non rimuove l'ipotesi di indipendenza sottostante.

Due cifre annualizzate con fattori diversi sono anche comparabili solo se il campionamento alla loro base è comparabile. Un fondo con prezzo settimanale e uno strumento 24/7 sono entrambi annualizzati correttamente, e vengono comunque osservati in modi molto diversi — ed è ciò che il conteggio delle osservazioni e la copertura servono a rendere visibile.

---

## 🔗 Correlati {: #related }

- 📊 **[Volatilità](volatility.md)** — la cifra più spesso espressa su base annuale
- 🧪 **[Qualità dei dati](data-quality.md)** — cosa significa una copertura bassa per l'affidabilità di un risultato
- 📐 **[Indice di Sharpe](sharpe-ratio.md)** — un indice corretto per il rischio che porta anch'esso una scala annuale
- 📊 **[Indice di Sortino](sortino-ratio.md)** — la variante solo al ribasso, stessa questione di scala
