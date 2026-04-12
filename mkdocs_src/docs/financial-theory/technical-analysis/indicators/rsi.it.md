# 💪 RSI — Relative Strength Index

L'RSI misura se i compratori o i venditori hanno dominato *recentemente*. Risponde alla domanda: *"Negli ultimi $N$ giorni, quanta parte del movimento totale del prezzo è stata verso l'alto rispetto a quella verso il basso?"*

---

## 💡 Significato Finanziario

Il risultato è compresso in un intervallo tra 0 e 100:

- **RSI > 70** → Ipercomprato — la molla è tesa, un ritracciamento è statisticamente probabile.
- **RSI < 30** → Ipervenduto — la molla è compressa, un rimbalzo è probabile.

---

## 🔢 Formule Matematiche

1. **Scomponi** le variazioni giornaliere in guadagni e perdite:

 $$
 U_t = \max(P_t - P_{t-1},\; 0), \qquad
 D_t = \max(P_{t-1} - P_t,\; 0)
 $$

2. **Liscia** ogni componente con una media mobile esponenziale (variante SMMA):

 $$
 \overline{U} = SMMA_N(U), \qquad
 \overline{D} = SMMA_N(D)
 $$

3. Rapporto di **Forza Relativa** e normalizzazione:

 $$
 RS = \frac{\overline{U}}{\overline{D}}, \qquad
 RSI = 100 - \frac{100}{1 + RS}
 $$

La normalizzazione $100 - 100/(1+RS)$ è una sigmoide monotonicamente crescente che mappa $RS \in [0, \infty)$ in $RSI \in [0, 100)$.

---

## ⚙️ Parametri

| Parametro | Chiave | Predefinito | Descrizione |
|---|---|---|---|
| Periodo ($N$) | `period` | 14 | Finestra di osservazione per la SMMA. |
| Ipercomprato | `overbought` | 70 | Soglia per la zona di ipercomprato. |
| Ipervenduto | `oversold` | 30 | Soglia per la zona di ipervenduto. |

---

## 🎛️ Equivalente nell'Elaborazione dei Segnali — Duty Cycle / Indicatore di Saturazione

Immaginate di dividere il segnale del delta di prezzo $\Delta P[n]$ nelle sue componenti raddrizzate a mezz'onda positiva e negativa, per poi applicare un filtro passa-basso a ciascuna. L'RSI è il **rapporto tra l'inviluppo positivo e l'inviluppo totale**, riscalato su $[0, 100]$.

In termini di sistemi di controllo, è un **rilevatore di saturazione**: quando l'uscita del sistema (prezzo) si è mossa in una sola direzione per troppo tempo, l'RSI segnala che l'attuatore (mercato) è vicino alla saturazione. Come ogni oscillatore in un anello di retroazione, più ci si allontana dall'equilibrio, più forte è la forza di richiamo — da qui la proprietà di ritorno alla media che i trader sfruttano.

!!! warning "Non-stazionarietà"

    Le soglie 70/30 presuppongono distribuzioni dei rendimenti approssimativamente simmetriche. In mercati con trend forti, l'RSI può rimanere sopra 70 per settimane — è un indicatore *probabilistico*, non deterministico.

:material-link: [RSI su Wikipedia](https://en.wikipedia.org/wiki/Relative_strength_index){ target="_blank" }
