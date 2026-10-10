# 🌊 VaR condizionale

Il VaR condizionale subentra esattamente dove si ferma il Value at Risk: misura la perdita media nei casi in cui la soglia del Value at Risk è stata effettivamente superata.

[Value at Risk](value-at-risk.md) dice **dove inizia la coda**. Questo dice **quanto è profonda**. Questa è tutta la differenza, ed è per questo che è il valore con cui la sezione si apre.

---

## 🔢 Formula {: #formula }

A un livello di confidenza $c$, il VaR condizionale è la perdita attesa **condizionata al fatto che** la perdita abbia superato il Value at Risk:

$$
CVaR_c = E\left[\, L \mid L \ge VaR_c \,\right]
$$

Empiricamente, è la media delle perdite nella coda oltre la soglia — la media dei casi negativi, anziché il confine dei casi negativi.

Poiché calcola la media su una regione invece di leggere un punto, porta con sé informazioni che il quantile non può fornire: due portafogli con lo **stesso** Value at Risk possono avere VaR condizionali molto diversi, uno supera la soglia di poco e l'altro di molto. Nulla nel primo valore li distingue; questo sì.

!!! tip "Premia anche la diversificazione in modo coerente"

    C'è una seconda ragione, più tecnica, per cui la pratica del rischio si è spostata verso le medie della coda. Un quantile può comportarsi in modo perverso quando si combinano portafogli: è possibile che il Value at Risk di un portafoglio combinato superi la somma dei Value at Risk delle sue parti, il che significherebbe che diversificare ha aumentato il rischio. Una media sulla coda non ha questo difetto, il che la rende la misura più affidabile quando si confronta il rischio tra composizioni.

---

## 🔬 Come viene calcolata la media della coda {: #how-the-tail-average-is-taken }

La coda raramente contiene un numero intero di osservazioni. Al 95% di confidenza su qualche centinaio di periodi, il confine della coda cade **tra** due perdite osservate, e l'osservazione che si trova su quel confine appartiene alla coda solo in parte.

La media quindi pondera quell'osservazione di confine in base alla frazione di essa che cade effettivamente oltre la soglia, invece di contare ogni osservazione della coda allo stesso modo. Trattare un'osservazione parzialmente inclusa come se fosse inclusa per intero trascina la media verso il confine — cioè verso la perdita meno grave della coda — e quindi riporta una coda meno profonda di quanto sia.

---

## 📐 La correzione, e ciò che fa al tuo numero {: #the-correction }

Questa è una modifica a un numero che potresti aver già visto. Lo stimatore precedente calcolava una media **uniforme** sulla coda; quello attuale applica la ponderazione frazionaria descritta sopra.

!!! warning "Il nuovo valore non è soltanto diverso — è meno ottimistico"

    La correzione sposta il VaR condizionale **verso l'alto a ogni livello di confidenza**, in ogni campione di uno studio di misurazione di 2.000 serie simulate di 750 osservazioni ciascuna: 2.000 su 2.000, senza una singola eccezione in nessuna delle due direzioni.

    Questa direzione è il punto. Il valore precedente **sottostimava la coda**: riportava il caso negativo medio come più mite di quanto dicessero i dati. Un utente che vede questo numero salire non sta vedendo una nuova metodologia produrre una differenza arbitraria — sta vedendo una stima ottimistica sostituita da una stima accurata.

| Confidenza | Variazione misurata (mediana) | Variazione massima osservata | Campioni che si sono mossi verso l'alto |
|---|---|---|---|
| 90% | +0,364% | +0,476% | 2.000 / 2.000 |
| 95% | +0,267% | +0,404% | 2.000 / 2.000 |
| 99% | +0,727% | +1,748% | 2.000 / 2.000 |

**Lo spostamento cresce con il livello di confidenza**, e la ragione deriva dal meccanismo: più alto è il livello, meno osservazioni cadono nella coda, quindi l'unica osservazione parzialmente inclusa porta una quota maggiore della media. Al 99% una manciata di osservazioni decide il valore, e ponderare male una di esse sposta il risultato più di quanto farebbe al 90%.

!!! info "Il valore corretto corrisponde all'implementazione di riferimento"

    Misurata rispetto all'implementazione di riferimento standard dello stesso stimatore, la differenza rimanente è $-4.27 \times 10^{-18}$ — rumore di arrotondamento in virgola mobile, non un divario metodologico. I due ora calcolano la stessa quantità.

Anche il valore della soglia si muove, anche se in una condizione molto più stretta: il [Value at Risk](value-at-risk.md) riportato accanto a questo cambia solo quando il numero di osservazioni è divisibile nel modo richiesto dal livello di confidenza, e dove cambia salta di un'intera osservazione invece di spostarsi leggermente. La regola, e come verificare un caso particolare, è esposta in [cosa cambia la correzione](value-at-risk.md#what-the-correction-changes). Le due sono modifiche distinte che capita arrivino insieme: questa riguarda come viene calcolata la media della coda, non dove inizia la coda.

---

## 💡 Interpretazione {: #interpretation }

Leggi questo valore come *quanto diventa grave quando va male* — il risultato medio nei casi peggiori nella finestra, non il peggiore tra essi.

- È sempre almeno tanto grave quanto il Value at Risk allo stesso livello, perché calcola la media di valori che sono tutti oltre quella soglia.
- Il divario tra i due è di per sé informativo: un VaR condizionale molto sopra il suo Value at Risk descrive un portafoglio i cui casi negativi, quando arrivano, sono molto peggiori di quanto suggerisca la soglia.
- Come il quantile che estende, legge la **distribuzione** e non la sequenza: rimescolare l'ordine dei rendimenti osservati lo lascia invariato. La visione dipendente dal percorso appartiene a [drawdown massimo](max-drawdown.md) e [drawdown attuale](current-drawdown.md), e un quadro completo richiede entrambi.

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "La coda è stimata da poche osservazioni"

    Per definizione, solo una piccola frazione della finestra cade oltre la soglia, e al 99% quella frazione è molto piccola. Il valore è quindi la misura meno stabile tra le misure distributive: può spostarsi in modo evidente all'arrivo di nuove osservazioni, e due finestre adiacenti possono discordare più di quanto suggerisca la differenza di lunghezza.

!!! warning "Rimane comunque limitato dalla storia che gli è stata fornita"

    Calcolare la media della coda non evoca perdite che il portafoglio non ha mai subito. Se la finestra non contiene nessun episodio severo, la coda di cui calcola la media è lieve — la misura riporterà onestamente una storia che semplicemente non è stata messa alla prova. Un [replay storico](historical-replay.md) o uno [shock ipotetico](hypothetical-shock.md) sono il modo in cui uno scenario esterno alla finestra entra nell'analisi.

!!! warning "Descrive la gravità, non la probabilità"

    Il valore è condizionato al raggiungimento della coda. Non dice nulla su quanto sia probabile oltre il livello di confidenza che l'ha definito, e nulla su quando — i periodi negativi si raggruppano, e nessun riepilogo distributivo lo cattura.

---

## 🔗 Correlati {: #related }

- 📉 **[Value at Risk](value-at-risk.md)** — la soglia oltre la quale questa misura calcola la media
- 📉 **[drawdown massimo](max-drawdown.md)** — la peggiore caduta cumulativa lungo il percorso
- 📊 **[Volatilità](volatility.md)** — dispersione in entrambe le direzioni, anziché solo la coda delle perdite
- ⚡ **[shock ipotetico](hypothetical-shock.md)** — uno scenario che la storia osservata non ha mai contenuto
- 🧪 **[qualità dei dati](data-quality.md)** — la finestra da cui è stata tratta la coda
