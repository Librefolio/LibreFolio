# 🎯 Benchmark Sintetici

LibreFolio può sovrapporre **curve di benchmark sintetici**[^1] su qualsiasi grafico Forex. A differenza degli indicatori tecnici (che vengono calcolati *dai* dati di mercato), i benchmark sintetici sono generati matematicamente e fungono da **linee di riferimento visive** — "e se il prezzo avesse seguito questa traiettoria ideale?".

Sono strumenti preziosi per:

* Confrontare i rendimenti effettivi con un tasso di crescita obiettivo.
* Visualizzare come apparirebbe un piano di investimento disciplinato.
* Aggiungere riferimenti oscillatori o ciclici per l'analisi della stagionalità.

---

## 📈 Crescita Lineare { #linear-growth }

### 💡 Significato Finanziario

Un benchmark di crescita lineare rappresenta **interesse semplice** — il valore aumenta di un importo fisso assoluto ogni periodo. È la "linea obiettivo" più semplice che si possa disegnare: se ci si aspetta che un asset renda $r$% annui, il benchmark lineare mostra dove il prezzo *dovrebbe* essere in qualsiasi momento sotto questa ipotesi.

### 🔢 Formula Matematica

$$
y(t) = y_0 \cdot (1 + r \cdot t)
$$

dove:

- $y_0$ è il valore iniziale (primo punto dati del grafico),
- $r$ è il tasso di crescita annuo (espresso come decimale, es. 0,07 per il 7%),
- $t$ è il tempo in anni dall'inizio.

Questo è equivalente alla formula dell'**interesse semplice** $A = P(1 + rt)$, dove $t$ è espresso in anni usando la convenzione di [Conteggio dei Giorni](day-count.md)[^2] applicabile.

### ⚙️ Parametri

| Parametro | Chiave | Predefinito | Descrizione |
|---|---|---|---|
| Tasso Annuo | `annualRate` | 5 | Tasso di crescita in percentuale annua. |
| Scostamento | `offset` | 0 | Spostamento verticale come % del valore base[^3]. |

### 🔍 Interpretazione

La linea è perfettamente dritta su scala lineare. Qualsiasi punto in cui il prezzo effettivo è *sopra* la linea significa che l'asset ha superato il target; qualsiasi punto *sotto* indica underperformance. Poiché la crescita è additiva, la linea tende a curvarsi verso il basso su scala logaritmica[^4] — rendendola facilmente distinguibile visivamente dalla crescita composta.

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
**Mensile** ($n=12$), **Giornaliera** ($n=365$), e **Continua** ($n \to \infty$)[^5].

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

Questo è matematicamente equivalente alla forma chiusa $y_0(1+r)^t$ ma sostituisce $N$ costose operazioni di potenza con $N$ semplici moltiplicazioni — lo stesso principio dietro come le banche effettivamente **maturano**[^6] gli interessi composti giornalieri.

!!! tip "Regola del 72"[^7]
 Una scorciatoia mentale rapida: un investimento che cresce al $r$% annuo raddoppierà approssimativamente in $72 / r$ anni. Al 7% → ~10,3 anni.

### ⚙️ Parametri

| Parametro | Chiave | Predefinito | Descrizione |
|---|---|---|---|
| Tasso di Crescita | `annualRate` | 7 | Tasso di crescita in percentuale annua. |
| Scostamento | `offset` | 0 | Spostamento verticale come % del valore base[^3]. |

### 🔍 Interpretazione

La curva è dritta su scala **logaritmica**[^4] — questo è il segno distintivo della crescita esponenziale. Sovrapporre un benchmark composto su un grafico in scala log è il modo più pulito per valutare se un asset sta crescendo più o meno velocemente di un tasso obiettivo.

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
| Scostamento | `offset` | 0 | Spostamento verticale come % del valore base[^3]. |

### 🔍 Interpretazione

Se il prezzo effettivo segue approssimativamente il riferimento sinusoidale, il mercato mostra una **componente ciclica**[^8] rilevabile a quella frequenza. Le deviazioni dalla sinusoide suggeriscono shock non periodici o deriva della tendenza. Regolare il parametro del periodo permette di **analizzare**[^9] diverse lunghezze di ciclo — effettivamente eseguendo una versione manuale dell'analisi spettrale.

:material-link: [Onda Sinusoidale su Wikipedia](https://en.wikipedia.org/wiki/Sine_wave){ target="_blank" }

---
[^1]: Nel gergo finanziario italiano, "benchmark" è generalmente considerato un sostantivo maschile. Pertanto, "benchmark sintetici" è la forma grammaticalmente corretta con accordo al maschile. In alternativa, si potrebbe usare "curve di riferimento sintetiche" per evitare il prestito.
[^2]: La **Convenzione di Conteggio dei Giorni** (Day Count Convention) è lo standard utilizzato nel settore finanziario per determinare il numero di giorni tra due date ai fini del calcolo degli interessi. Le convenzioni più comuni includono Actual/365, 30/360 e Actual/360.
[^3]: Il parametro `offset` (scostamento) non indica un errore, ma uno spostamento verticale calibrato in percentuale del valore iniziale (`y_0`). Serve per adattare la curva di benchmark a diversi livelli di prezzo di partenza.
[^4]: Su una **scala logaritmica**, una crescita esponenziale (composta) si presenta come una linea retta, mentre una crescita lineare (semplice) assume una forma curva verso il basso. Questo principio permette un confronto visivo immediato tra il benchmark e il prezzo.
[^5]: La **capitalizzazione continua** rappresenta il limite matematico in cui gli interessi sono calcolati e aggiunti al capitale in modo istantaneo e infinitamente frequente. La costante `e` (~2.71828) è il numero di Nepero, base dei logaritmi naturali.
[^6]: Il verbo corretto per "accrue" in questo contesto finanziario è "maturano" (gli interessi maturano nel tempo). "Accantonare" si riferisce invece alla creazione di un fondo per far fronte a un futuro Omanento o rischio.
[^7]: La **Regola del 72** è una formula approssimativa per stimare il tempo di raddoppio di un investimento. Si calcola dividendo 72 per il tasso di rendimento percentuale annuo. Fornisce una stima rapida per tassi comuni (es. 72/6 = 12 anni).
[^8]: "Ciclabile" (adatto a essere percorso in bicicletta) era un errore di traduzione di "cyclic". Il termine corretto è "**componente ciclica**", che indica una parte o un elemento che si ripete a intervalli regolari.
[^9]: "Scansire" è un calco dall'inglese "to scan" poco idiomatico in questo contesto. Alternative più fluide sono "**analizzare**", "**sperimentare con**" o "**esplorare**" diverse lunghezze di ciclo.
