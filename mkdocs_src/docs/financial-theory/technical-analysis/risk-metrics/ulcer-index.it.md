# 🩹 Indice di Ulcer

L'indice di Ulcer combina quanto in profondità cade un portafoglio con quanto a lungo rimane giù, per cui un calo contenuto che persiste può ottenere un punteggio peggiore di uno brusco che si riprende rapidamente.

Ogni altra cifra di drawdown nelle pagine vicine riporta un **momento** — il peggiore, o quello attuale. Questa riporta un **arco di tempo**: esamina il drawdown in ogni singola osservazione e chiede quanto della storia è stato trascorso sotto un picco, e di quanto.

---

## 🔢 Formula {: #formula }

Il drawdown all'osservazione $t$ è la distanza dal valore più alto raggiunto fino a quel momento:

$$
DD_t = \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau} \leq 0
$$

L'indice di Ulcer è la **radice della media dei quadrati** di quella serie sulle $T$ osservazioni:

$$
UI = \sqrt{\frac{1}{T} \sum_{t=1}^{T} DD_t^{2}}
$$

Tre proprietà seguono direttamente da quell'espressione, prima che vi si sovrapponga qualsiasi interpretazione:

- È **positivo**. È una dispersione costruita da una radice quadrata, e una radice quadrata non può restituire un numero negativo. È l'unico membro della famiglia dei drawdown che non viene riportato come una caduta.
- **Ogni osservazione conta**, comprese quelle che si trovano esattamente su un picco. Queste contribuiscono con $0$ alla somma ma occupano comunque una posizione nel divisore, ed è questo che fa sì che un lungo periodo tranquillo abbassi la cifra.
- **Elevare al quadrato non è neutro.** Un drawdown due volte più profondo contribuisce quattro volte tanto, per cui la misura è dominata dai tratti profondi piuttosto che da quelli semplicemente sotto il picco.

---

## 📐 Il divisore che sembra la correzione di Bessel {: #the-divisor }

Questo è il dettaglio che mette in difficoltà chiunque ricalcoli la cifra a mano, e vale la pena enunciarlo con precisione perché l'errore che produce è abbastanza piccolo da sopravvivere a un controllo superficiale.

!!! info "La serie porta un punto in più rispetto alla storia"

    Una serie di drawdown deriva da un indice di ricchezza che parte da una base unitaria, quindi contiene $T + 1$ punti: i $T$ osservati, più quella base. Il drawdown della base è **sempre esattamente zero** — un punto di partenza non può essere sotto un picco che non ha ancora lasciato.

    L'implementazione di riferimento standard divide la somma dei quadrati per $n - 1$, dove il contatore $n$ scorre sull'intera serie e quindi **include** quella base. Poiché $n = T + 1$:

    $$
    \frac{1}{n - 1} = \frac{1}{(T + 1) - 1} = \frac{1}{T}
    $$

    Il $-1$ sta cancellando il punto fantasma, non applicando una correzione campionaria.

!!! warning "Leggerlo come una deviazione standard campionaria sovrastima il risultato"

    La base contribuisce con $0$ alla somma dei quadrati e con $+1$ al conteggio, e queste due cose si annullano esattamente — ed è per questo che l'espressione si riduce a una media genuina sulle $T$ osservazioni reali. Scambiare il $n - 1$ per la correzione di Bessel e dividere invece per $T - 1$ gonfia la cifra di

    $$
    \sqrt{\frac{T}{T - 1}}
    $$

    Con $T = 750$ ciò equivale a **+0,0667%**: troppo piccolo per sembrare sbagliato, e comunque sbagliato. L'indice di Ulcer è una radice della media dei quadrati, non una deviazione standard campionaria, e non ha alcuna media da stimare.

---

## 🆚 A confronto con il Drawdown massimo {: #against-the-maximum-drawdown }

Il [Drawdown massimo](max-drawdown.md) riporta il momento peggiore. L'indice di Ulcer riporta quanto tempo è stato trascorso sotto il picco, e quanto in profondità. Sono costruiti dalla stessa serie e ordinano i portafogli in modo diverso, il che è l'intera ragione per pubblicarli entrambi.

| Due storie con lo **stesso** Drawdown massimo | Indice di Ulcer |
|---|---|
| Una caduta brusca, recuperata in pochi giorni | **piccolo** — le osservazioni profonde sono poche, e il resto sta su un picco |
| Una lenta erosione che rimane sotto il picco per mesi | **grande** — la maggior parte delle osservazioni è sotto il picco, e ognuna conta |

La relazione tra i due non è soltanto qualitativa. Poiché $DD_t^{2} \leq MDD^{2}$ per ogni $t$, la media dei quadrati non può superare il più grande di essi:

$$
UI \leq |MDD|
$$

L'uguaglianza richiederebbe che il portafoglio restasse nel suo punto più profondo per l'intera finestra. Il rapporto $UI / |MDD|$ si legge quindi come **quanto della storia assomigliava al suo punto peggiore** — vicino a $0$ per un singolo picco in un percorso altrimenti privo di turbamenti, tendente a $1$ per un portafoglio che è sceso e vi è rimasto.

---

## 💡 Interpretazione {: #interpretation }

Si legga la cifra come una profondità *tipica* piuttosto che come la peggiore — ponderata per la durata, ed espressa nelle stesse unità dei drawdown da cui è costruita.

- **Zero significa non essere mai sotto un picco.** Un portafoglio che ha sempre e solo fatto nuovi massimi non ha alcuna serie di drawdown di cui parlare, e l'indice si riduce a $0$. Qualsiasi storia contenente un calo produce una cifra strettamente positiva.
- **Più basso è meglio**, il che inverte l'abitudine di lettura del resto della famiglia dei drawdown. Qui un numero più grande è un'esperienza peggiore, senza alcun segno meno a segnalarlo.
- **Legge la sequenza, non la distribuzione.** Rimescolare i rendimenti osservati lascia intatti il [Value at Risk](value-at-risk.md) e il [VaR condizionale](conditional-value-at-risk.md), ma ricostruisce da zero la serie dei drawdown e può spostare questa cifra di molto. Appartiene alla metà dipendente dal percorso della sezione, insieme al [Drawdown massimo](max-drawdown.md) e al [Drawdown attuale](current-drawdown.md).

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "Una finestra tranquilla più lunga lo abbassa"

    Il divisore è il numero di osservazioni, quindi estendere una storia con periodi trascorsi su un picco aggiunge zeri al numeratore e posizioni al denominatore. La cifra scende senza che nulla degli episodi negativi del portafoglio sia cambiato. Due indici di Ulcer sono confrontabili solo quando sono stati calcolati su finestre di lunghezza comparabile e con la stessa frequenza di osservazione.

!!! warning "Non è la frazione di tempo trascorsa sotto il picco"

    Elevare al quadrato attribuisce ai tratti profondi un peso sproporzionato, quindi l'indice non è una statistica di durata travestita da percentuale. Un portafoglio che ha trascorso metà della finestra al $2\%$ sotto il suo picco e uno che ne ha trascorso un ottavo al $4\%$ sotto ottengono lo stesso punteggio, e nessuna delle due cifre ti dice quale forma lo abbia prodotto.

!!! warning "Non porta con sé date"

    La misura riassume l'intera finestra in un solo numero e non dice nulla su **quando** si siano verificati i periodi sotto il picco, né se il portafoglio sia sotto il picco adesso. Il [Drawdown attuale](current-drawdown.md) risponde alla seconda domanda e il [Drawdown massimo](max-drawdown.md) data la prima.

---

## 🔗 Correlati {: #related }

- 📉 **[Drawdown massimo](max-drawdown.md)** — il momento peggiore, rispetto al quale questa ne misura l'intero arco
- 📍 **[Drawdown attuale](current-drawdown.md)** — dove si trova oggi il portafoglio rispetto al suo picco
- 📉 **[Drawdown a rischio](drawdown-at-risk.md)** — un quantile della stessa serie di drawdown, invece della sua radice della media dei quadrati
- 🌊 **[Drawdown a rischio condizionale](conditional-drawdown-at-risk.md)** — la severità della coda dei drawdown oltre quel quantile
- 📊 **[Volatilità](volatility.md)** — dispersione dei rendimenti, che non ha memoria del picco
- 🧪 **[Qualità dei dati](data-quality.md)** — la finestra e il numero di osservazioni su cui è stata costruita la serie
