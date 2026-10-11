# 🧩 Contributo al Rischio

Il contributo al rischio attribuisce il rischio totale di portafoglio alle singole posizioni detenute, e ciò che ciascuna posizione contribuisce generalmente non coincide con la quota di portafoglio che essa rappresenta.

Conoscere i pesi non ti dice nulla di nuovo — sono visibili nel portafoglio stesso. Sapere da dove proviene il **rischio** di solito sì, perché il contributo di una posizione dipende da quanto è volatile e da come si muove insieme a tutto ciò con cui è detenuta.

---

## 🔢 Formula {: #formula }

La scomposizione parte dalla varianza di portafoglio scritta tramite la matrice di covarianza $\Sigma$ dei rendimenti degli asset e il vettore dei pesi $w$:

$$
\sigma_p = \sqrt{w^{\top} \Sigma\, w}
$$

Da essa si derivano tre grandezze, in questo ordine:

$$
MCTR_i = \frac{(\Sigma w)_i}{\sigma_p}, \qquad
CCTR_i = w_i \cdot MCTR_i, \qquad
PCTR_i = \frac{CCTR_i}{\sigma_p}
$$

| Grandezza | Si legge come | Risponde a |
|---|---|---|
| $MCTR_i$ — marginale | Sensibilità della volatilità di portafoglio al peso di $i$ | *Se aggiungo un po' di questa posizione, quanto si muove il rischio totale?* |
| $CCTR_i$ — componente | Quella sensibilità moltiplicata per il peso effettivamente detenuto | *Quanto del rischio totale porta questa posizione, in unità di volatilità?* |
| $PCTR_i$ — percentuale | La componente come quota della volatilità totale | *Quale frazione del rischio del portafoglio è questa posizione?* |

La grandezza marginale è la derivata $\partial \sigma_p / \partial w_i$: descrive la **prossima** unità della posizione, non quella detenuta. La grandezza di componente è quella che descrive la posizione così com'è.

!!! info "L'annualizzazione è applicata alla matrice di covarianza"

    Ogni elemento di $\Sigma$ è moltiplicato per il fattore di annualizzazione osservato $f$ prima che la scomposizione venga eseguita, così la volatilità di portafoglio e tutte e tre le grandezze di contributo risultano su base annuale. Scalare una covarianza per $f$ è la forma matriciale della moltiplicazione di una deviazione standard per $\sqrt{f}$ — la stessa operazione, e lo stesso fattore misurato, usati da [Volatilità](volatility.md). Vedi [Annualizzazione Osservata](observed-annualization.md) per capire da dove proviene $f$.

---

## ➗ Perché le Parti si Sommano {: #why-the-parts-add-up }

I contributi di componente si sommano alla volatilità di portafoglio **esattamente**, e i contributi percentuali quindi si sommano a $1$:

$$
\sum_i CCTR_i = \sum_i w_i \frac{(\Sigma w)_i}{\sigma_p} = \frac{w^{\top} \Sigma\, w}{\sigma_p} = \frac{\sigma_p^{2}}{\sigma_p} = \sigma_p
\qquad\Longrightarrow\qquad
\sum_i PCTR_i = 1
$$

Non è un'approssimazione che risulta vicina, né una normalizzazione applicata a posteriori per forzare i numeri verso un totale tondo. È la scomposizione di Eulero, e vale perché $\sigma_p$ è **omogenea di grado 1** nei pesi: raddoppiando ogni peso raddoppia la volatilità di portafoglio. Qualsiasi funzione di questo tipo è recuperata esattamente dalla somma dei suoi argomenti moltiplicati per le sue derivate parziali, che è precisamente la somma qui sopra.

La conseguenza pratica è il motivo per cui la metrica viene pubblicata: poiché le quote sono esatte e sommano a uno, **un contributo percentuale può essere confrontato direttamente con un peso**. Una posizione pari al 10% del portafoglio che porta il 30% del rischio è un'affermazione che non contiene alcuna scalatura nascosta.

---

## ⚖️ Il Contributo Non È il Peso {: #contribution-is-not-weight }

I due numeri rispondono a domande diverse, e si separano per due ragioni che si compongono:

- **Volatilità.** Una posizione che si muove il doppio rispetto al resto porta più rischio per unità di capitale.
- **Correlazione.** Una posizione che si muove *insieme* alle altre aggiunge la propria volatilità a quella delle altre; una che si muove contro di esse in parte annulla ciò che fanno le altre. La stessa posizione, allo stesso peso, contribuisce in modo diverso a seconda delle altre posizioni con cui è detenuta.

Questa seconda ragione è il motivo per cui il contributo non può essere letto da una singola posizione in isolamento: $(\Sigma w)_i$ contiene ogni covarianza tra l'asset $i$ e il resto del portafoglio, quindi cambiare una posizione *non collegata* cambia il contributo di questa.

!!! tip "Dove la metrica si guadagna il suo posto"

    Una piccola posizione in qualcosa di volatile e strettamente legato al resto del portafoglio può portare una quota di rischio parecchie volte superiore alla sua quota di capitale — e la vista di portafoglio non lo mostrerà mai, perché la vista di portafoglio mostra i pesi. Al contrario, una grande posizione che si muove fuori passo rispetto a tutto il resto può contribuire a molto meno rischio di quanto la sua dimensione suggerisca. La diversificazione è visibile qui in un modo che non lo è nella sola [Correlazione](correlation.md): la correlazione dice quali coppie si muovono insieme, questa dice quanto ciò costa una volta tenuti in conto gli importi detenuti.

---

## 🧾 Cosa Devono Soddisfare gli Input {: #what-the-inputs-must-satisfy }

La scomposizione rifiuta gli input che non può onestamente scomporre. Questi sono **confini dichiarati della prima ondata**, non lacune lasciate per omissione:

| Requisito | Comportamento quando violato |
|---|---|
| I pesi devono essere non negativi | Rifiutato — le posizioni corte sono fuori dal contratto della prima ondata |
| La composizione non deve essere a leva | Rifiutato a monte — pesi degli asset superiori al 100% del valore dello scope sono fuori dal contratto |
| La matrice di covarianza deve essere simmetrica | Rifiutato, entro una tolleranza numerica per il rumore in virgola mobile |
| Le dimensioni della matrice devono corrispondere ai pesi | Rifiutato |
| Tutte le serie di rendimenti devono condividere un unico calendario comune | Rifiutato — la matrice di covarianza è costruita su un singolo calendario di osservazione |

Una posizione corta romperebbe l'aritmetica qui sopra in modo specifico: con pesi negativi, un contributo di componente può essere negativo, e una quota di "rischio totale" inferiore a zero non può essere letta come quota di alcunché. Rifiutare l'input è la risposta onesta finché il contratto di presentazione non copre quel caso.

La liquidità è gestita senza comparire affatto nella matrice. I pesi degli asset sommano a uno meno la quota di liquidità, quindi la volatilità calcolata è già quella dell'**intero** portafoglio, liquidità inclusa — e la liquidità non compare mai come contributore, perché una posizione che non si muove ha un contributo marginale pari a zero. La quota di liquidità è pubblicata accanto ai contributi così che il lettore possa vedere qual è il resto.

---

## 💡 Interpretazione {: #interpretation }

Leggi il contributo percentuale **rispetto al peso**, non da solo:

- contributo ≈ peso — la posizione porta la propria quota, niente di più
- contributo > peso — è una fonte concentrata di rischio rispetto al capitale impegnato su di essa
- contributo < peso — sta diluendo il rischio di portafoglio, o perché è calma o perché si muove diversamente dal resto

La grandezza marginale risponde a una domanda diversa ed è quella da usare quando si pensa a un cambiamento: dice cosa fa il **prossimo** euro in quella posizione alla volatilità totale. Una posizione può portare un grande contributo di componente semplicemente perché è grande, mentre il suo contributo marginale è insignificante.

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "Decompone la volatilità, non la perdita"

    Ogni grandezza in questa pagina è una quota della **volatilità di portafoglio**. La volatilità conta i movimenti in entrambe le direzioni, quindi una posizione che contribuisce al 30% del rischio non produce per ciò stesso il 30% di una qualsiasi perdita. I contributi a una misura di ribasso sono una scomposizione diversa, e questa non è quella. Per sapere cosa la fluttuazione cattura e cosa no, vedi [Volatilità](volatility.md).

!!! warning "È un'istantanea della composizione attuale"

    I pesi sono quelli detenuti ora, e la matrice di covarianza è stimata sulla finestra analizzata. Il risultato descrive il portafoglio di oggi misurato rispetto a quella storia — non è un'affermazione su come il rischio fosse distribuito in passato, quando la composizione era diversa.

!!! warning "La matrice è una stima, e eredita la sua finestra"

    Le covarianze sono stimate da un campione finito su un unico calendario comune. Una finestra corta, un periodo turbolento, o un asset con una storia dei prezzi limitata produce una stima che un'altra finestra non riprodurrebbe, e ogni contributo deriva da quella stima. Le correlazioni in particolare sono note per muoversi quando i mercati sono sotto stress. Ogni risultato pubblica il numero di osservazioni e la finestra utilizzata — vedi [Qualità dei Dati](data-quality.md).

!!! warning "Volatilità zero restituisce zeri, non un risultato assente"

    Se la volatilità di portafoglio è indistinguibile da zero, tutte e tre le grandezze di contributo vengono restituite esattamente come zero. Questa è la risposta, non un segnaposto: non essendoci rischio da attribuire, ogni sua quota è genuinamente nulla. Vale la pena contrastarla con la pagina [Beta e Rendimento Attivo](beta-active-return.md), dove un benchmark privo di varianza non produce **alcun valore** — lì la grandezza sarebbe una divisione per zero, quindi non c'è nulla da riportare; qui la grandezza esiste ed è pari a zero.

---

## 🔗 Correlati {: #related }

- 🔗 **[Correlazione](correlation.md)** — quali posizioni si muovono insieme, prima di tenere in conto gli importi
- 📊 **[Volatilità](volatility.md)** — il totale che viene decomposto
- 🎯 **[Concentrazione](concentration.md)** — quanto del portafoglio risiede in quante poche posizioni
- 🗓️ **[Annualizzazione Osservata](observed-annualization.md)** — il fattore applicato alla matrice di covarianza
- 🧪 **[Qualità dei Dati](data-quality.md)** — la finestra e le osservazioni su cui la matrice è stata stimata
