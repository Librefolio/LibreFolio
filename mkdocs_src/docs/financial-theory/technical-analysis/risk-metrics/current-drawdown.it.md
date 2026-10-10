# 📍 Drawdown attuale

Il drawdown attuale misura quanto un portafoglio si trova **attualmente** al di sotto del proprio picco storico, al contrario della peggior caduta mai subita. Il [Drawdown massimo](max-drawdown.md) riporta un fatto del passato; questo valore riporta una posizione nel presente, ed è quello che cambia ad ogni nuova osservazione.

---

## 🔢 Formula {: #formula }

Entrambe le cifre di drawdown vengono lette dalla stessa serie sotto il picco. Un indice di ricchezza viene costruito dai rendimenti analizzati, un picco corrente viene mantenuto, e il drawdown in ogni punto è la distanza tra i due:

$$
DD_t = \frac{W_t}{\displaystyle\max_{\tau \le t} W_\tau} - 1
$$

Il drawdown attuale è il valore di quella serie all'**ultima** osservazione, mai superiore a zero:

$$
DD_{current} = \min\left(0,\; DD_{last}\right)
$$

In corrispondenza di un nuovo high-water mark l'ultimo valore di ricchezza *è* il picco corrente, quindi il rapporto è $1$ e il drawdown è esattamente $0$.

!!! info "Lo stato sotto il picco è deciso con una tolleranza"

    Un portafoglio è considerato sotto il picco solo quando il drawdown attuale è negativo **oltre una tolleranza numerica**, non ad ogni frazione di centesimo al di sotto del picco. La tolleranza esiste per assorbire il rumore in virgola mobile, in modo che un valore indistinguibile dal picco venga trattato come se fosse al picco. È una protezione contro artefatti aritmetici, non una soglia visibile all'utente al di sotto della quale un calo smette di avere importanza.

---

## 📅 Cosa Viene Pubblicato {: #what-is-published }

Quattro grandezze descrivono la posizione attuale. Il loro comportamento quando il portafoglio **non** è sotto il picco fa parte del contratto, non è un caso.

| Grandezza | Significato | In corrispondenza di un high-water mark |
|---|---|---|
| Drawdown attuale | Distanza al di sotto del picco corrente, come rapporto decimale, mai positiva | Esattamente $0$ |
| Data del picco corrente | La data del picco **corrente** dal quale il drawdown è misurato | La data dell'ultima osservazione |
| Durata del drawdown attuale | Giorni di calendario trascorsi **da quel picco** | Esattamente $0$ |
| Mancante al picco | Il guadagno ancora necessario, sul valore corrente, per tornare al picco | Esattamente $0$ |

Due di queste meritano una lettura attenta.

**La durata è contata dal picco, non dal punto minimo.** È la stessa convenzione che il drawdown massimo usa per la sua durata: il cronometro parte quando il portafoglio lascia il suo high-water mark, non quando smette di scendere. Il calo non è un preludio alla perdita — è la perdita che si sta verificando — quindi il conteggio copre l'intero tratto trascorso al di sotto del picco. Vedi [Tempo di recupero](max-drawdown.md#recovery-time) per lo stesso ragionamento applicato al peggior episodio.

**La data del picco corrente non è il picco del peggior episodio.** È l'high-water mark più recente: il picco corrente avanza ogni volta che il portafoglio ne stabilisce uno nuovo. Un portafoglio ai massimi storici riporta quindi la data odierna e un drawdown di durata zero; il picco che ha preceduto il calo storico più profondo appartiene al [Drawdown massimo](max-drawdown.md) ed è pubblicato separatamente.

---

## 🧗 Cosa Serve per Recuperare {: #what-it-takes-to-get-back }

Il guadagno necessario per tornare al picco non è l'immagine speculare del calo, perché il guadagno si applica a una base più piccola. Scritto dal drawdown attuale $DD$:

$$
\text{Guadagno richiesto} = \frac{1}{1 + DD} - 1 = \frac{-DD}{1 + DD}
$$

Le due forme sono la stessa espressione — la seconda è la prima con la frazione combinata — e il [Drawdown massimo](max-drawdown.md) spiega l'asimmetria che questo crea, con i valori calcolati.

!!! warning "La stessa formula, applicata a una domanda diversa"

    Quell'asimmetria è una lezione generale, ed è insegnata nella pagina del drawdown massimo. La grandezza calcolata qui la applica invece al drawdown **attuale**, e la differenza non è cosmetica:

    - applicata al **massimo**, è un'affermazione storica — *quanto sarebbe servito per recuperare, nel punto peggiore mai raggiunto*;
    - applicata al drawdown **attuale**, è un'affermazione presente — *quanto serve per recuperare da dove si trova oggi il portafoglio*.

    Solo la seconda può essere messa in pratica. Un portafoglio che è caduto bruscamente anni fa e da allora si è ripreso porta contemporaneamente un massimo elevato e una cifra attuale quasi nulla: non sono due numeri in disaccordo, sono risposte a due domande diverse, ed entrambe sono vere.

---

## 💡 Interpretazione {: #interpretation }

Il drawdown attuale risponde a *dove sono, rispetto al mio miglior risultato?* — una domanda a cui nessuna cifra di rendimento risponde, perché un rendimento misura un percorso tra due date scelte, mentre questo misura una distanza da un picco che il portafoglio stesso ha stabilito.

Lette insieme, le quattro grandezze descrivono una posizione piuttosto che un punteggio: **quanto in basso** rispetto al picco, **da quando**, e **quanto** manca ancora. La durata è spesso la più rivelatrice delle due: un calo modesto che si protrae a lungo è un'esperienza diversa da uno più profondo apertosi la settimana scorsa, e la sola profondità non riesce a distinguerli. Quella combinazione di profondità e persistenza è ciò che l'[Indice di Ulcer](ulcer-index.md) si propone di riassumere in un unico numero.

Poiché è misurato rispetto al picco corrente, il valore ha una sua asimmetria intrinseca: migliora man mano che il portafoglio sale e si azzera nel momento in cui viene stabilito un nuovo picco, per quanto poco quel picco venga superato.

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "È una posizione, non una previsione"

    Il drawdown attuale dice quanto il portafoglio è al di sotto del picco, e nulla su ciò che accadrà dopo. Non indica se il calo sta terminando, proseguendo o sta per approfondirsi, e la cifra mancante al picco è aritmetica — il guadagno necessario per colmare il divario — non un'aspettativa che il guadagno arrivi.

!!! warning "Un nuovo picco cancella la memoria"

    Il picco corrente si muove solo verso l'alto, quindi superare il massimo precedente di qualsiasi margine azzera il drawdown attuale e fa ripartire la durata da quella data. Il calo che lo ha preceduto non scompare dall'analisi, ma smette di essere descritto da *questa* cifra: appartiene al drawdown massimo e alla storia degli episodi.

!!! warning "Eredita la serie su cui è stato calcolato"

    La serie sotto il picco è costruita dagli stessi rendimenti del resto dell'analisi, sulla stessa finestra di osservazione. Una finestra più corta può contenere solo i picchi che ha visto: un portafoglio analizzato su una finestra recente può apparire vicino al suo massimo semplicemente perché il picco più alto si trova prima della data di inizio. Ogni risultato pubblica la finestra utilizzata, il suo numero di osservazioni e la base su cui sono stati calcolati i rendimenti. Vedi [Qualità dei dati](data-quality.md).

---

## 🔗 Correlati {: #related }

- 📉 **[Drawdown massimo](max-drawdown.md)** — la peggior caduta registrata, la sua durata e il suo stato di recupero
- 🩹 **[Indice di Ulcer](ulcer-index.md)** — profondità e persistenza combinate in un'unica cifra
- 📊 **[Volatilità](volatility.md)** — quanto oscilla il portafoglio, indipendentemente da qualsiasi picco
- 🧪 **[Qualità dei dati](data-quality.md)** — la finestra e le osservazioni da cui è stato letto il drawdown
