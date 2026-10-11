# 🔗 Correlazione

La correlazione misura **come due posizioni si muovono in relazione l'una all'altra**. È la metrica che stabilisce se un portafoglio è realmente diversificato o semplicemente una somma di posizioni lunghe: possedere molte cose non è diversificazione se queste salgono e scendono insieme.

---

## 🔢 Formula {: #formula }

Per due serie di rendimenti $r_i$ e $r_j$ osservate sugli stessi $N$ periodi, il coefficiente di correlazione di Pearson è la loro covarianza normalizzata per le loro deviazioni standard:

$$\rho_{i,j} = \frac{\mathrm{Cov}(r_i, r_j)}{\sigma_i \, \sigma_j}$$

con gli stimatori campionari non distorti ($N-1$):

$$\mathrm{Cov}(r_i, r_j) = \frac{1}{N-1} \sum_{t=1}^{N} (r_{i,t} - \bar{r_i})(r_{j,t} - \bar{r_j}) \qquad \sigma_i = \sqrt{\frac{1}{N-1} \sum_{t=1}^{N} (r_{i,t} - \bar{r_i})^2}$$

Dividere per le due deviazioni standard è ciò che rende il risultato comparabile: la covarianza è espressa in unità di rendimento al quadrato e cresce con la volatilità dei suoi input, mentre $\rho$ è un numero puro limitato tra $-1$ e $+1$, qualunque siano gli asset.

!!! info "La correlazione è calcolata dopo la conversione di valuta"

    I rendimenti entrano nel calcolo già convertiti nella valuta obiettivo richiesta per l'analisi — la stessa regola per un portafoglio e per un insieme di asset. La cifra descrive quindi ciò che ha sperimentato un detentore che misura in quella valuta, movimenti del tasso di cambio inclusi — non ciò che lo strumento ha fatto nella sua valuta di origine. Due asset quotati in valute diverse vengono confrontati sulla stessa base convertita.

---

## 💡 Interpretazione {: #interpretation }

Il coefficiente ha tre punti di riferimento, e solo tre che non richiedono alcuna convenzione:

| Valore | Significato |
|---|---|
| $\rho = +1$ | Le due serie si muovono in perfetto sincrono: una è una funzione lineare positiva esatta dell'altra |
| $\rho = 0$ | Nessuna relazione **lineare** tra le due serie nella finestra osservata |
| $\rho = -1$ | Opposizione perfetta: una serie è una funzione lineare negativa esatta dell'altra |

Tutto ciò che sta tra questi poli è una questione di grado. Per rendere leggibile la matrice, LibreFolio legge ogni coefficiente in una di quattro fasce, ovunque disegni una matrice di correlazione — nella scheda Rischio della dashboard e della pagina di un broker, e nella [scheda Correlazione](../../../user/assets/correlation.md#correlation) della pagina Asset — nel tooltip di ogni cella e nelle due liste di coppie accanto alla matrice:

| Fascia | Intervallo | Lettura mostrata |
|---|---|---|
| Alta | $\rho > 0.7$ | si muovono insieme |
| Moderata | $0.3 \le \rho \le 0.7$ | si muovono in parte insieme |
| Bassa | $-0.3 < \rho < 0.3$ | si muovono indipendentemente |
| Inversa | $\rho \le -0.3$ | si muovono in direzioni opposte |

Le soglie sono simmetriche rispetto allo zero, quindi un coefficiente debole viene letto come indipendenza qualunque sia il suo segno: $\rho = -0.01$ non è prova che due asset si compensino a vicenda. Le due liste mantengono solo i casi chiari — *i più simili* per la fascia alta, *quelli che si compensano* per la fascia inversa — e una coppia con $\rho \ge 0.9$ è inoltre contrassegnata come *quasi identica*: due strumenti che, in pratica, sono una singola esposizione. Una cella senza coefficiente non ricade in alcuna fascia: una correlazione sconosciuta non viene mai letta come bassa.

Le fasce sono ausili di lettura, non verdetti. Non esiste un livello al quale una coppia diventa "troppo correlata", perché la risposta dipende da quanto del portafoglio rappresentano quelle due posizioni — una domanda a cui la sola matrice di correlazione non può rispondere.

### 🧩 Perché la matrice risponde a "Sono diversificato?" {: #why-the-matrix-answers-am-i-diversified }

Il numero di posizioni è un conteggio; la diversificazione è un comportamento. Dieci posizioni che rispondono tutte allo stesso driver si comportano, in un mese negativo, come una sola posizione detenuta dieci volte. La matrice di correlazione è ciò che rende visibile questo: è la mappa delle relazioni, non un verdetto su di esse.

Leggila per la struttura più che per i singoli valori — i cluster di posizioni che si muovono insieme, le coppie che davvero non si muovono insieme, e se un presunto diversificatore si comporta davvero come tale. La diagonale non porta informazione: ovunque contenga un valore, quel valore è $+1$ per costruzione — ma la cella diagonale di una serie piatta è `undefined`, e una matrice sotto la soglia di osservazioni non contiene alcun valore (vedi [Come viene calcolata ogni cella](#how-each-cell-is-computed)).

L'ordine predefinito della matrice serve a questa lettura. Dispone gli asset tramite clustering agglomerativo con legame medio sulla distanza

$$d_{ij} = 1 - |\rho_{ij}|$$

così che le coppie fortemente legate — nella stessa direzione o in direzioni opposte — finiscano fianco a fianco, e i cluster appaiano come blocchi. Legame medio anziché singolo, perché il legame singolo concatena: due gruppi non correlati uniti tramite un asset intermedio verrebbero disegnati come un unico blocco. Una coppia senza coefficiente è posizionata alla distanza massima, $d_{ij} = 1$, così che un valore mancante non possa mai attirare due asset nello stesso blocco; i pareggi sono risolti per posizione, quindi la stessa matrice produce sempre lo stesso ordine.

La correlazione risponde a *come* le posizioni si muovono insieme. Non dice nulla su **quanto** del portafoglio ciascuna rappresenti, motivo per cui viene letta insieme a [Concentrazione](concentration.md) e [Contributo al rischio](risk-contribution.md): una correlazione forte tra due posizioni marginali conta molto meno di una moderata tra le due più grandi.

---

## 🧮 Come viene calcolata ogni cella {: #how-each-cell-is-computed }

Ogni cella della matrice restituisce uno di tre stati, e ogni cella riporta il numero di osservazioni su cui è stata valutata.

| Stato della cella | Quando | Cosa viene pubblicato |
|---|---|---|
| `ok` | Il calendario condiviso contiene osservazioni sufficienti e nessuna delle due serie è piatta | Il coefficiente, limitato a $[-1, +1]$ |
| `insufficient` | Il calendario condiviso contiene meno osservazioni del minimo richiesto — ogni cella della matrice è quindi in questo stato | Nessun valore — il conteggio è pubblicato senza un coefficiente |
| `undefined` | Almeno una delle due serie ha varianza (numericamente) zero | Nessun valore — una serie che non si muove mai non ha una direzione da condividere |

Il minimo è applicato alla **matrice nel suo complesso**, non coppia per coppia. Poiché ogni serie si trova sullo stesso calendario condiviso (vedi sotto), ogni coppia è calcolata esattamente sulle stesse date, quindi c'è un unico conteggio di osservazioni per l'intera matrice: o supera la soglia di osservazioni o no, e quando non la supera, ogni cella è segnalata come insufficiente. Una storia breve, quindi, non lascia mai alcune coppie calcolate e altre vuote — accorcia il calendario, e con esso il campione, per ogni coppia contemporaneamente. La soglia di osservazioni predefinita è di 20 osservazioni, ed è un parametro regolabile dell'analisi, non una regola codificata.

Ogni stato diverso da `ok` che si verifica almeno una volta genera anche un avviso sul risultato — rispettivamente `insufficient_pair_history` e `flat_series` — così una matrice totalmente o parzialmente inutilizzabile lo dice esplicitamente invece di lasciare celle vuote da interpretare. Nonostante il nome, `insufficient_pair_history` riguarda sempre l'intera matrice. Una serie piatta, al contrario, svuota solo la propria riga e colonna e lascia ogni altra correlazione invariata.

!!! info "Tutte le serie condividono un unico calendario"

    Prima che venga calcolata qualsiasi correlazione, ogni serie nell'ambito viene allineata su un unico calendario condiviso: una data entra nell'analisi solo se **ogni** posizione può essere valorizzata su di essa nella valuta obiettivo. Le coppie non vengono quindi mai calcolate su date non corrispondenti o interpolate — ma il costo è collettivo, perché una data che fallisce per una posizione viene eliminata per tutte. Una posizione con una storia breve — una che non può essere valorizzata prima della data di inizio richiesta — accorcia la finestra per l'intera matrice: il calendario inizia dalla prima data in cui ogni posizione può essere valorizzata, e il report di qualità dei dati nomina le posizioni interessate anziché elencare le date saltate. Un vuoto all'interno di una storia non rimuove date: un prezzo mancante, come un tasso di cambio mancante, è sostituito dall'ultimo noto, mantenuto senza limite di età, e il report conta come punti mantenuti solo quelli mantenuti oltre la [soglia di obsolescenza](data-quality.md#staleness-threshold). Una volta iniziato il calendario, una data viene eliminata solo se qualche posizione non ha ancora alcun valore nella valuta obiettivo su di essa, e tali date sono elencate nel report come incomplete. Vedi [Qualità dei dati](data-quality.md).

    Quando la matrice viene costruita su un insieme di asset scelti direttamente, senza alcun portafoglio dietro di essi, un asset **senza alcuna serie di prezzi** non è una storia breve ma una storia assente: viene escluso dall'ambito prima che il calendario venga costruito. Il risultato lo elenca come escluso — con motivo `no_price_source` quando non gli è assegnata alcuna fonte di prezzo e nessun prezzo è mai stato registrato per esso, `missing_price` altrimenti — genera un avviso `assets_excluded` ed è contrassegnato come `partial`. L'asset non appare come riga piatta, e non accorcia la finestra per gli altri asset. Vedi [Esclusioni](data-quality.md#exclusions).

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "La correlazione vede solo la parte lineare di una relazione"

    $\rho$ misura quanto bene la relazione tra due serie è descritta da una linea retta. Una dipendenza reale ma curva — per esempio, un asset che reagisce solo a grandi movimenti di un altro — può produrre un coefficiente vicino a zero. Una correlazione bassa significa "nessun legame lineare rilevato in questa finestra", mai "queste posizioni non sono correlate".

!!! warning "Un solo numero per l'intera finestra"

    Una correlazione è una media sul periodo richiesto. Una coppia che è stata non correlata per la maggior parte della finestra e si è mossa insieme nel momento peggiore produce una media rassicurante. Questa è l'asimmetria ben documentata della diversificazione: le correlazioni osservate in condizioni calme non sono una promessa sul comportamento sotto stress, quando posizioni che sembravano indipendenti spesso smettono di esserlo. La matrice descrive la finestra su cui è stata misurata, e nient'altro.

!!! warning "La correlazione non è causalità, né grandezza"

    Due asset possono essere fortemente correlati tramite un driver comune senza alcuna relazione tra loro. E la correlazione non dice nulla sulla dimensione: una coppia correlata a $+1$ in cui un asset si muove violentemente e l'altro a malapena condivide la direzione, non il rischio. La grandezza appartiene a [Volatilità](volatility.md), il peso appartiene a [Contributo al rischio](risk-contribution.md).

---

## 🔗 Correlati {: #related }

- 🧩 **[Concentrazione](concentration.md)** — quanto del portafoglio rappresenta effettivamente ciascuna posizione
- ⚖️ **[Contributo al rischio](risk-contribution.md)** — quali posizioni guidano il rischio di portafoglio una volta combinati correlazione e peso
- 📊 **[Volatilità](volatility.md)** — la grandezza che la correlazione normalizza deliberatamente fino ad annullarla
- 🧪 **[Qualità dei dati](data-quality.md)** — il calendario condiviso, e quanto una data mancante costa all'intera matrice
