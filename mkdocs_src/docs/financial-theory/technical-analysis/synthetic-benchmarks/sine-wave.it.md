# 🌊 Onda Sinusoidale

Un benchmark a onda sinusoidale rappresenta un'**oscillazione periodica**. È l'unico benchmark non orientato alla crescita in LibreFolio.

---

## 💡 Significato Finanziario

Utile per:

- Modellare la **stagionalità** (es. materie prime agricole, valute legate al turismo).
- Fornire un riferimento visivo per **pattern ciclici** che i trader sospettano nei dati.
- Testare la pipeline di rendering con una forma d'onda analitica nota.

---

## 🔢 Formula Matematica

$$
y(t) = A \cdot \sin\!\left(\frac{2\pi t}{T}\right) + y_0 + \text{offset}
$$

dove:

- $A$ è l'ampiezza (intervallo picco-picco come % del valore base),
- $T$ è il periodo in giorni,
- $y_0$ è il valore base (primo punto dati),
- $\text{offset}$ è uno spostamento verticale.

---

## ⚙️ Parametri

| Parametro | Chiave | Default | Descrizione |
|---|---|---|---|
| Ampiezza | `amplitude` | 10 | Intervallo di oscillazione picco-picco come % del valore base. |
| Periodo | `period` | 365 | Lunghezza del ciclo completo in giorni. |
| Offset | `offset` | 0 | Spostamento verticale come % del valore base. |

---

## 🔍 Interpretazione

Se il prezzo effettivo segue approssimativamente il riferimento sinusoidale, il mercato presenta una componente ciclica rilevabile a quella frequenza. Le deviazioni dalla sinusoide suggeriscono shock non periodici o deriva del trend. Regolando il parametro del periodo è possibile scansionare diverse lunghezze di ciclo, eseguendo di fatto una versione manuale dell'analisi spettrale.

:material-link: [Onda Sinusoidale su Wikipedia](https://en.wikipedia.org/wiki/Sine_wave){ target="_blank" }
