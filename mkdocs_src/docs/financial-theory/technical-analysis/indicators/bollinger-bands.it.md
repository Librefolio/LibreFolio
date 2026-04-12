# 📏 Bande di Bollinger

Le Bande di Bollinger misurano dinamicamente la **volatilità** e tracciano una "recinzione di normalità" adattiva attorno al prezzo.

---

## 💡 Significato Finanziario

Quando le bande sono ampie, il mercato è volatile; quando si stringono (squeeze), un breakout è imminente. Un prezzo che tocca la banda superiore segnala un'esuberanza statistica; il contatto con la banda inferiore segnala un calo anomalo.

---

## 🔢 Formule Matematiche

1. **Banda Centrale** (valore atteso):

 $$
 MB_t = SMA_N(C_t)
 $$

2. **Deviazione standard** dei prezzi nell'intervallo:

 $$
 \sigma_t = \sqrt{\frac{1}{N} \sum_{i=0}^{N-1} (C_{t-i} - MB_t)^2}
 $$

3. **Bande Superiore e Inferiore**:

 $$
 Upper_t = MB_t + k \cdot \sigma_t, \qquad
 Lower_t = MB_t - k \cdot \sigma_t
 $$

Con $k = 2$, se i rendimenti fossero distribuiti normalmente, il prezzo rimarrebbe all'interno delle bande per circa il 95,4% del tempo. In pratica, i rendimenti finanziari presentano *code grasse* (leptocurtosi), quindi le violazioni sono più frequenti — ma comunque statisticamente significative.

---

## ⚙️ Parametri

| Parametro | Chiave | Default | Descrizione |
|---|---|---|---|
| Periodo ($N$) | `period` | 20 | Finestra SMA per il valore atteso. |
| Moltiplicatore ($k$) | `multiplier` | 2 | Numero di deviazioni standard. |

---

## 🎛️ Equivalente nell'Elaborazione dei Segnali — Tracker di Intervallo di Confidenza Adattivo

La Banda Centrale è un **filtro a media mobile FIR (Finite Impulse Response)** — il più semplice filtro passa-basso con una finestra rettangolare di lunghezza $N$. Le bande aggiungono un **inviluppo variabile nel tempo** a $\pm k\sigma$, che è essenzialmente una stima mobile della varianza istantanea del segnale.

Nel linguaggio dei filtri adattivi, si tratta di un **inseguitore del valore atteso con un intervallo di confidenza adattivo**. Quando la varianza $\sigma^2$ diminuisce (il "Bollinger Squeeze"), il sistema si trova in uno stato di bassa entropia. Nei sistemi caotici come i mercati finanziari, i periodi di bassa entropia sono costantemente seguiti da esplosioni di alta entropia (alta volatilità) — rendendo lo squeeze uno dei setup più osservati nell'analisi tecnica.

!!! info "FIR vs IIR"

    A differenza dell'EMA (IIR, un polo), la SMA è un **filtro FIR** con un ritardo
    di gruppo perfettamente piatto di $(N-1)/2$ campioni. Sacrifica una banda di
    transizione più ampia per una distorsione di fase zero — ideale per centrare
    l'inviluppo di confidenza.

:material-link: [Bande di Bollinger su Wikipedia](https://en.wikipedia.org/wiki/Bollinger_Bands){ target="_blank" }
