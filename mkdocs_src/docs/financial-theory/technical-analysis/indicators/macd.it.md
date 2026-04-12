# 📊 MACD — Moving Average Convergence Divergence

Il MACD risponde alla domanda: *"Il trend sta accelerando o sta perdendo forza?"* Indica se il *tasso di variazione* del trend è positivo o negativo.

---

## 💡 Significato Finanziario

I trader monitorano l'incrocio tra la linea MACD e la linea del segnale: un crossover rialzista suggerisce un aumento del momentum, uno ribassista suggerisce un esaurimento del movimento. Il MACD **non** indica che il prezzo stia salendo (questo è già visibile); indica se il momentum sta aumentando o diminuendo.

---

## 🔢 Formule Matematiche

Il sistema MACD produce tre serie:

1. **Linea MACD** (l'output passa-banda):

 $$
 MACD_t = EMA_{fast}(C_t) - EMA_{slow}(C_t)
 $$

2. **Linea del segnale** (MACD levigato):

 $$
 Signal_t = EMA_{signal}(MACD_t)
 $$

3. **Istogramma** (delta del momentum):

 $$
 Histogram_t = MACD_t - Signal_t
 $$

---

## ⚙️ Parametri

| Parametro | Chiave | Default | Descrizione |
|---|---|---|---|
| Periodo Veloce | `fastPeriod` | 12 | Finestra EMA a breve termine (giorni). |
| Periodo Lento | `slowPeriod` | 26 | Finestra EMA a lungo termine (giorni). |
| Periodo del segnale | `signalPeriod` | 9 | Smoothing EMA applicato alla linea MACD. |

---

## 🎛️ Equivalente nell'Elaborazione dei Segnali — Filtro Passa-Banda (Derivata Levigata)

Sottrarre due filtri passa-basso con diverse frequenze di taglio produce un **filtro passa-banda**. $EMA_{fast} - EMA_{slow}$ annulla la componente DC (il trend a lungo termine condiviso da entrambi) e sopprime il rumore ad alta frequenza (già filtrato da entrambi gli EMA). Ciò che rimane è la banda a *media frequenza*: l'oscillazione del momentum.

Nel dominio $z$:

$$
H_{MACD}(z) = H_{fast}(z) - H_{slow}(z)
 = \frac{\alpha_f}{1-(1-\alpha_f)z^{-1}}
 - \frac{\alpha_s}{1-(1-\alpha_s)z^{-1}}
$$

La Linea del segnale è un ulteriore passa-basso applicato a questo output passa-banda — agisce come un **filtro adattato** (matched filter), ritardando leggermente il segnale per ridurre i falsi positivi nel rilevamento dei crossover.

!!! note "Interpretazione come derivata"

    Per valori piccoli di $\alpha$, $EMA_{fast} - EMA_{slow}$ si comporta come una
    derivata prima levigata $\frac{d}{dt}[\text{trend}]$. Quando l'istogramma inverte il segno, la
    "velocità" del trend cambia direzione.

:material-link: [MACD su Wikipedia](https://en.wikipedia.org/wiki/MACD){ target="_blank" }
