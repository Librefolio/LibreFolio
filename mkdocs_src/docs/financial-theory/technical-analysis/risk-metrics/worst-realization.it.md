# 🔻 Peggior realizzazione

La peggior realizzazione è semplicemente il rendimento su singolo periodo meno favorevole effettivamente osservato nella storia disponibile — un fatto osservato, non una stima.

Ogni altra cifra in questa sezione è calcolata *dalle* osservazioni. Questa **è** una di esse.

---

## 🔢 Che cos'è {: #what-it-is }

Dati i rendimenti della finestra analizzata, la peggior realizzazione è il loro minimo:

$$
WR = \min_t \; r_t
$$

Non c'è alcun livello di confidenza da scegliere, alcuna distribuzione da ipotizzare, alcuna media da calcolare. La cifra è un rendimento che si è verificato, e arriva con **la data in cui si è verificato** — ed è questo che la separa da ogni parametro nelle pagine circostanti. Una data può essere cercata. Fissa il numero a un evento che il portafoglio ha effettivamente attraversato, invece che a una costruzione statistica.

---

## 🆚 A confronto con Value at Risk {: #against-value-at-risk }

Il compagno naturale è il [Value at Risk](value-at-risk.md), e la coppia funziona per **contrasto** anziché per ripetizione:

| | Dice | Natura |
|---|---|---|
| Value at Risk | *Un periodo su venti va peggio di questo* | Una soglia, stimata |
| Peggior realizzazione | *E la peggiore è stata questa, in questa data* | Un singolo punto, osservato |

Il Value at Risk descrive una **frequenza** e tace sull'ampiezza oltre la soglia. La peggior realizzazione descrive un'**ampiezza** e tace sulla frequenza — si è verificata una volta, e la cifra non dice nulla sulla probabilità che si ripeta. Il [VaR condizionale](conditional-value-at-risk.md) si colloca tra i due, facendo la media dell'intera coda anziché leggerne il confine o l'estremo.

Insieme delimitano la coda: dove inizia, quanto è profonda in media e il passo singolo più profondo registrato.

---

## 🧭 Distribuzione o percorso {: #distribution-or-path }

Le metriche etichettate come *rischio* rientrano in due famiglie che rispondono a domande diverse, e nulla in una riga di otto numeri segnala quale sia quale.

!!! info "Mescola i rendimenti e osserva cosa si muove"

    **Mescola l'ordine dei rendimenti di un portafoglio e il Value at Risk non cambia di una virgola — mentre il drawdown massimo può raddoppiare.**

    Il Value at Risk, il VaR condizionale e la peggior realizzazione leggono la **distribuzione**: quali rendimenti si sono verificati, in qualsiasi ordine. Il [drawdown massimo](max-drawdown.md), il [drawdown attuale](current-drawdown.md) e le durate a essi associate leggono il **percorso**: l'ordine in cui sono arrivati.

La peggior realizzazione appartiene saldamente alla famiglia della distribuzione, e la distinzione non è accademica. Risponde a *quanto può essere brutto un singolo periodo?* — mentre un portafoglio non viene distrutto da un singolo giorno negativo, ma da una **sequenza** di essi. Tre perdite consecutive del 5% fanno più danni di una singola perdita isolata del 12%, e solo la famiglia che legge il percorso può distinguerle.

Leggere una cifra distribuzionale come se descrivesse la peggiore esperienza disponibile è l'errore che questa sezione è organizzata per prevenire.

---

## 💡 Interpretazione {: #interpretation }

Usala come verifica di realtà sulle cifre stimate. Un Value at Risk molto più blando della peggior realizzazione non è una contraddizione — il quantile è pensato per essere superato a volte, e questo è ciò che ha significato superarlo nel suo caso più estremo.

La data conta quanto il valore. Una peggior realizzazione proveniente da un evento di mercato ben noto si legge diversamente da una relativa a un giorno qualsiasi, che spesso indica qualcosa di specifico del portafoglio: una singola posizione, un'operazione societaria o un artefatto di prezzo che vale la pena controllare in [qualità dei dati](data-quality.md).

---

## ⚠️ Limiti {: #limitations }

!!! warning "È un estremo, quindi la finestra può solo peggiorarlo"

    Allungare il periodo analizzato non può mai migliorare questa cifra e può solo peggiorarla: una finestra più lunga contiene ogni osservazione contenuta in quella più breve, più ulteriori occasioni di trovare qualcosa di peggio. Confrontare le peggiori realizzazioni tra portafogli è quindi privo di senso, a meno che non siano state misurate sulla stessa finestra — una storia più lunga di solito sembrerà peggiore solo per questo motivo.

!!! warning "Una singola osservazione non porta con sé alcuna frequenza"

    La cifra si basa su un singolo periodo. Non dice nulla sulla frequenza con cui un tale periodo si verifica, se qualcosa di simile sia accaduto più di una volta, o su come si sia comportato il resto della coda. Per la forma della coda anziché per il suo estremo, usa il [VaR condizionale](conditional-value-at-risk.md).

!!! warning "Dipende dalla lunghezza di un periodo"

    Un giorno peggiore, una settimana peggiore e un mese peggiore sono quantità diverse, e non si convertono l'una nell'altra. La cifra è legata alla frequenza di osservazione della serie da cui è stata letta — vedi [Annualizzazione osservata](observed-annualization.md) per come viene stabilita tale frequenza.

---

## 🔗 Correlati {: #related }

- 📉 **[Value at Risk](value-at-risk.md)** — dove inizia la coda, come frequenza anziché come fatto
- 🌊 **[VaR condizionale](conditional-value-at-risk.md)** — la profondità media della coda alla cui estremità si trova questa cifra
- 📉 **[drawdown massimo](max-drawdown.md)** — la peggiore caduta cumulativa, che legge il percorso anziché la distribuzione
- 📊 **[Volatilità](volatility.md)** — dispersione tipica, rispetto alla quale un estremo può essere giudicato
- 🧪 **[qualità dei dati](data-quality.md)** — la finestra e la serie su cui è stato calcolato il minimo
