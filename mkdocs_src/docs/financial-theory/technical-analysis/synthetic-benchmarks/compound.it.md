# 📊 Crescita Composta

Un benchmark di crescita composta rappresenta l'**interesse composto**: il valore cresce in modo esponenziale, il che significa che i rendimenti vengono reinvestiti.

---

## 💡 Significato Finanziario

Questo è il modello di crescita naturale per la maggior parte degli asset finanziari e l'ipotesi standard nelle analisi dei flussi di cassa attualizzati (DCF). La crescita composta produce una curva esponenziale che accelera nel tempo: il fondamento della costruzione della ricchezza a lungo termine.

---

## 🔢 Formula Matematica

$$
y(t) = y_0 \cdot (1 + r)^t
$$

dove:

- $y_0$ è il valore iniziale,
- $r$ è il tasso di crescita annuale (decimale),
- $t$ è il tempo in anni dall'inizio.

Questo è equivalente alla formula dell'**interesse composto** $A = P(1 + r)^t$ con capitalizzazione annuale. La formula generalizzata con $n$ periodi di capitalizzazione all'anno è:

$$
A = P \cdot \left(1 + \frac{r}{n}\right)^{n \cdot t}
$$

Il backend di LibreFolio supporta le seguenti frequenze di capitalizzazione: **Annuale** ($n=1$), **Semestrale** ($n=2$), **Trimestrale** ($n=4$), **Mensile** ($n=12$), **Giornaliera** ($n=365$) e **Continua** ($n \to \infty$).

Quando $n \to \infty$ (capitalizzazione continua):

$$
A = P \cdot e^{r \cdot t}
$$

---

## 🔄 Calcolo Iterativo (Passo Giornaliero)

In LibreFolio la curva composta viene calcolata **iterativamente** invece di chiamare `pow()` per ogni punto dati. Questo è sia più efficiente che istruttivo:

$$
\text{dailyFactor} = (1 + r)^{1/365}
$$

Quindi, per ogni giorno successivo:

$$
y_{i+1} = y_i \cdot \text{dailyFactor}
$$

Questo è matematicamente equivalente alla forma chiusa $y_0(1+r)^t$ ma sostituisce $N$ costose operazioni di potenza con $N$ semplici moltiplicazioni: lo stesso principio utilizzato dalle banche per il calcolo dell'interesse composto giornaliero.

!!! tip "Regola del 72"

    Una rapida scorciatoia mentale: un investimento che cresce al $r$% all'anno raddoppierà approssimativamente in $72 / r$ anni. Al 7% $\to$ ~10,3 anni.

---

## ⚙️ Parametri

| Parametro | Chiave | Predefinito | Descrizione |
|---|---|---|---|
| Tasso Annuale | `annualRate` | 7 | Tasso di crescita composta in percentuale all'anno. |
| Offset | `offset` | 0 | Spostamento verticale come % del valore di base. |

---

## 🔍 Interpretazione

La curva appare come una retta su una scala **logaritmica**: questo è il segno distintivo della crescita esponenziale. Sovrapporre un benchmark composto a un grafico in scala logaritmica è il modo più pulito per giudicare se un asset sta crescendo più velocemente o più lentamente di un tasso target.

:material-link: [Interesse Composto su Wikipedia](https://en.wikipedia.org/wiki/Compound_interest){ target="_blank" }
