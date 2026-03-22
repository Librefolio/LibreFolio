# 🎯 Benchmark Sintetici

LibreFolio può sovrapporre **curve di benchmark sintetici** su qualsiasi grafico Forex. A differenza degli indicatori tecnici (che vengono calcolati *dai* dati di mercato), i benchmark sintetici sono generati matematicamente e fungono da **linee di riferimento visive** — "e se il prezzo avesse seguito questa traiettoria ideale?".

Sono strumenti preziosi per:

* Confrontare i rendimenti effettivi con un tasso di crescita obiettivo.
* Visualizzare come apparirebbe un piano di investimento disciplinato.
* Aggiungere riferimenti oscillatori o ciclici per l'analisi della stagionalità.

---

## 📈 Crescita Lineare { #linear-growth }

### 💡 Significato Finanziario

Un benchmark di crescita lineare rappresenta **interesse semplice** — il valore aumenta di un importo fisso assoluto ogni periodo. Questo modella lo scenario in cui **non reinvesti** i guadagni (dividendi, interessi, cedole): i pagamenti in contanti vengono ricevuti ma messi da parte, quindi solo il capitale originale genera rendimenti.

Se invece **reinvesti** quei guadagni — manualmente o automaticamente attraverso strumenti ad accumulazione (es. ETF ad accumulazione, che reinvestono i dividendi internamente e beneficiano del [differimento fiscale](taxation.md#tax-deferral-advantage)) — dovresti aspettarti una **[crescita composta](#compound-growth)**, dove i rendimenti generano ulteriori rendimenti.

In pratica, la differenza tra crescita lineare e composta si allarga drasticamente su orizzonti lunghi. Ecco perché il benchmark Lineare appare come una linea retta mentre il benchmark Composto curva verso l'alto esponenzialmente.

!!! abstract "Plusvalenze e minusvalenze"
    Quando si vende un asset al di sopra del prezzo di acquisto, la differenza è una **plusvalenza**; al di sotto, una **minusvalenza**. Ogni giurisdizione ha le proprie regole riguardo aliquote fiscali, soglie per periodo di detenzione, durata del riporto delle perdite e metodi di abbinamento (FIFO, LIFO, identificazione specifica). Per una panoramica teorica, vedi [Tassazione & Efficienza Fiscale](taxation.md).

### 🔢 Formula Matematica

$$
y(t) = y_0 \cdot (1 + r \cdot t)
$$

dove:

- $y_0$ è il valore iniziale (primo punto dati del grafico),
- $r$ è il tasso di crescita annuo (espresso come decimale, es. 0,07 per il 7%),
- $t$ è il tempo in anni dall'inizio.

Questo è equivalente alla formula dell'**interesse semplice** $A = P(1 + rt)$, dove $t$ è espresso in anni usando la convenzione di [Conteggio dei Giorni](day-count.md) applicabile.

### ⚙️ Parametri

| Parametro | Chiave | Predefinito | Descrizione |
|---|---|---|---|
| Tasso Annuo | `annualRate` | 5 | Tasso di crescita in percentuale annua. |
| Scostamento | `offset` | 0 | Spostamento verticale come % del valore base. |

### 🔍 Interpretazione

La linea è perfettamente dritta su scala lineare. Qualsiasi punto in cui il prezzo effettivo è *sopra* la linea significa che l'asset ha superato il target; qualsiasi punto *sotto* indica underperformance. Poiché la crescita è additiva, la linea tende a curvarsi verso il basso su scala logaritmica — rendendola facilmente distinguibile visivamente dalla crescita composta.

:material-link: [Interesse Semplice su Wikipedia](https://en.wikipedia.org/wiki/Interest#Simple_interest){ target="_blank" }

---

## 📊 Crescita Composta { #compound-growth }

### 💡 Significato Finanziario

Un benchmark di crescita composta rappresenta **interesse composto** — il valore cresce esponenzialmente, il che significa che i rendimenti sono reinvestiti. Questo è il modello di crescita naturale per la maggior parte degli asset finanziari e l'assunzione standard nell'analisi del discounted cash flow (DCF).

### 🔢 Formula Matematica

$$
y(t) = y_0 \cdot (1 + r)^t
$$

dove:

- $y_0$ è il valore iniziale,
- $r$ è il tasso di crescita annuo (decimale),
- $t$ è il tempo in anni dall'inizio.

Questa equivale alla formula dell'**interesse composto** $A = P(1 + r)^t$ con capitalizzazione annuale. La formula generalizzata con $n$ periodi di capitalizzazione all'anno è:

$$
A = P \cdot \left(1 + \frac{r}{n}\right)^{n \cdot t}
$$

Il backend di LibreFolio supporta le seguenti frequenze di capitalizzazione:
**Annuale** ($n=1$), **Semestrale** ($n=2$), **Trimestrale** ($n=4$),
**Mensile** ($n=12$), **Giornaliera** ($n=365$), e **Continua** ($n \to \infty$).

Quando $n \to \infty$ (capitalizzazione continua):

$$
A = P \cdot e^{r \cdot t}
$$

### 🔄 Calcolo Iterativo (Passo Giornaliero)

In LibreFolio la curva composta viene calcolata **iterativamente** invece di chiamare `pow()` per ogni punto dati. Questo è sia più efficiente che istruttivo:

$$
\text{fattoreGiornaliero} = (1 + r)^{1/365}
$$

Quindi, per ogni giorno successivo:

$$
y_{i+1} = y_i \cdot \text{fattoreGiornaliero}
$$

Questo è matematicamente equivalente alla forma chiusa $y_0(1+r)^t$ ma sostituisce $N$ costose operazioni di potenza con $N$ semplici moltiplicazioni — lo stesso principio dietro come le banche effettivamente **maturano** gli interessi composti giornalieri.

!!! tip "Regola del 72"
    Una scorciatoia mentale rapida: un investimento che cresce al $r$% annuo raddoppierà approssimativamente in $72 / r$ anni. Al 7% → ~10,3 anni.

### ⚙️ Parametri

| Parametro | Chiave | Predefinito | Descrizione |
|---|---|---|---|
| Tasso di Crescita | `annualRate` | 7 | Tasso di crescita in percentuale annua. |
| Scostamento | `offset` | 0 | Spostamento verticale come % del valore base. |

### 🔍 Interpretazione

La curva è dritta su scala **logaritmica** — questo è il segno distintivo della crescita esponenziale. Sovrapporre un benchmark composto su un grafico in scala log è il modo più pulito per valutare se un asset sta crescendo più o meno velocemente di un tasso obiettivo.

:material-link: [Interesse Composto su Wikipedia](https://en.wikipedia.org/wiki/Compound_interest){ target="_blank" }

---

## 🌊 Onda Sinusoidale { #sine-wave }

### 💡 Significato Finanziario

Un benchmark a onda sinusoidale rappresenta **oscillazione periodica**. È utile per:

- Modellare la **stagionalità** (es. materie prime agricole, valute legate al turismo).
- Fornire un riferimento visivo per **pattern ciclici** che i trader sospettano nei dati.
- Testare la pipeline di rendering con un'onda analitica nota.

### 🔢 Formula Matematica

$$
y(t) = A \cdot \sin\!\left(\frac{2\pi t}{T}\right) + y_0 + \text{scostamento}
$$

dove:

- $A$ è l'ampiezza (intervallo picco-picco come % del valore base),
- $T$ è il periodo in giorni,
- $y_0$ è il valore base (primo punto dati),
- $\text{scostamento}$ è uno spostamento verticale.

### ⚙️ Parametri

| Parametro | Chiave | Predefinito | Descrizione |
|---|---|---|---|
| Ampiezza | `amplitude` | 10 | Intervallo di oscillazione di picco come % del valore base. |
| Periodo | `period` | 365 | Lunghezza del ciclo completo in giorni. |
| Scostamento | `offset` | 0 | Spostamento verticale come % del valore base. |

### 🔍 Interpretazione

Se il prezzo effettivo segue approssimativamente il riferimento sinusoidale, il mercato mostra una **componente ciclica** rilevabile a quella frequenza. Le deviazioni dalla sinusoide suggeriscono shock non periodici o deriva della tendenza. Regolare il parametro del periodo permette di **analizzare** diverse lunghezze di ciclo — effettivamente eseguendo una versione manuale dell'analisi spettrale.

:material-link: [Onda Sinusoidale su Wikipedia](https://en.wikipedia.org/wiki/Sine_wave){ target="_blank" }

