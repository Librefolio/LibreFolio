# 📈 Crescita Lineare

Un benchmark di crescita lineare rappresenta l'**interesse semplice**: il valore aumenta di un importo assoluto fisso per ogni periodo.

---

## 💡 Significato Finanziario

Questo simula lo scenario in cui **non reinvestite** i guadagni (dividendi, interessi, cedole): i pagamenti in contanti vengono ricevuti ma tenuti a parte, quindi solo il capitale originale genera rendimenti.

Se invece **reinvestite** tali guadagni — manualmente o automaticamente attraverso strumenti ad accumulazione (ad esempio, ETF ad accumulazione, che reinvestono i dividendi internamente e beneficiano del [differimento fiscale](../../fundamentals/taxation.md#tax-deferral-advantage)) — dovreste aspettarvi una **[crescita composta](compound.md)**, dove i rendimenti generano ulteriori rendimenti.

In pratica, la differenza tra crescita lineare e composta si amplia drasticamente su orizzonti temporali lunghi. Ecco perché il benchmark Lineare appare come una linea retta, mentre il benchmark Composto curva verso l'alto esponenzialmente.

!!! abstract "Plusvalenze e minusvalenze"

    Quando si vende un asset a un prezzo superiore a quello di acquisto, la differenza è una **plusvalenza**;
    se inferiore, una **minusvalenza**. Ogni giurisdizione ha le proprie regole riguardanti le aliquote fiscali,
    le soglie del periodo di detenzione, la durata del riporto delle perdite e i metodi di
    computo (FIFO, LIFO, identificazione specifica). Per una panoramica teorica, vedere
    [Panoramica su tassazione ed efficienza fiscale](../../fundamentals/taxation.md).

---

## 🔢 Formula Matematica

$$
y(t) = y_0 \cdot (1 + r \cdot t)
$$

dove:

- $y_0$ è il valore iniziale (primo punto dati del grafico),
- $r$ è il tasso di crescita annuale (espresso come decimale, ad es. 0.07 per il 7%),
- $t$ è il tempo in anni dall'inizio.

Questo è equivalente alla formula dell'**interesse semplice** $A = P(1 + rt)$, dove $t$ è espresso in anni utilizzando la [Convenzione di Conteggio dei Giorni](../../fundamentals/day-count.md) applicabile.

---

## ⚙️ Parametri

| Parametro | Chiave | Predefinito | Descrizione |
|---|---|---|---|
| Tasso Annuale | `annualRate` | 5 | Tasso di crescita in percentuale annua. |
| Offset | `offset` | 0 | Spostamento verticale come % del valore di base. |

---

## 🔍 Interpretazione

La linea è perfettamente dritta su una scala lineare. Qualsiasi punto in cui il prezzo effettivo è *sopra* la linea significa che l'asset ha superato l'obiettivo; qualsiasi punto *sotto* significa una sottoperformance. Poiché la crescita è additiva, la linea curva verso il basso su una scala logaritmica, rendendola facile da distinguere visivamente dalla crescita composta.

:material-link: [Interesse Semplice su Wikipedia](https://en.wikipedia.org/wiki/Interest#Simple_interest){ target="_blank" }
