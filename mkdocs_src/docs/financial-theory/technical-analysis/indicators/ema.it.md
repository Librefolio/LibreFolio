# 📉 EMA — Exponential Moving Average

L'EMA traccia il **trend** attenuando il rumore dei prezzi giornalieri, assegnando un peso maggiore alle osservazioni recenti rispetto a quelle più vecchie.

---

## 💡 Significato Finanziario

I trader sovrappongono EMA di diversi periodi su un grafico dei prezzi: quando un'EMA a breve periodo incrocia *verso l'alto* un'EMA a lungo periodo, segnala un momentum rialzista (una "golden cross"); l'incrocio opposto segnala un rallentamento ("death cross").

---

## 🔢 Formula Matematica

L'EMA è definita dalla ricorrenza del primo ordine:

$$
EMA_t = \alpha \cdot P_t + (1 - \alpha) \cdot EMA_{t-1}
$$

dove $P_t$ è il prezzo di chiusura al tempo $t$ e $\alpha$ è il **coefficiente di livellamento**.

**Mappatura $N$ → $\alpha$.**
I trader specificano un "periodo" $N$ (in giorni). Il coefficiente è derivato eguagliando l' *età media* dei dati tra un'EMA e una Simple Moving Average (SMA) della stessa finestra:

$$
\text{Age}_{SMA} = \frac{N-1}{2}, \qquad
\text{Age}_{EMA} = \frac{1-\alpha}{\alpha}
$$

Uguagliandole:

$$
\alpha = \frac{2}{N+1}
$$

Per esempio, $N = 14 \implies \alpha = 2/15 \approx 0.133$.

---

## ⚙️ Parametri

| Parametro | Chiave | Default | Descrizione |
|---|---|---|---|
| Periodo ($N$) | `period` | 14 | Finestra di lookback in giorni. Più alto → più liscia, più lenta. |
| Offset | `offset` | 0 | Spostamento verticale come % del valore base. |

---

## 🎛️ Equivalente nell'Elaborazione dei Segnali — Filtro Passa-Basso IIR del Primo Ordine

La ricorrenza $y[n] = \alpha\,x[n] + (1-\alpha)\,y[n-1]$ è precisamente un **filtro passa-basso IIR (Infinite Impulse Response) del primo ordine**. La sua funzione di trasferimento nel dominio $z$ è:

$$
H(z) = \frac{\alpha}{1 - (1-\alpha)\,z^{-1}}
$$

La frequenza di taglio a $-3\,\text{dB}$ (normalizzata) è:

$$
\omega_c = \cos^{-1}\!\left(1 - \frac{\alpha^2}{2(1-\alpha)}\right)
$$

Quando $\alpha$ è piccolo ($N$ grande), la banda passante si restringe drasticamente, attenuando tutto tranne la componente DC (il trend a lungo termine).

!!! tip "Posizione del polo"

    L'unico polo si trova in $z = 1-\alpha$. Per $N = 200$, $\alpha \approx 0.01$, quindi
    il polo è in $z = 0.99$ — estremamente vicino alla circonferenza unitaria, il che spiega l'
    accentuato livellamento e l'elevato ritardo di gruppo.

:material-link: [EMA su Wikipedia](https://en.wikipedia.org/wiki/Exponential_smoothing){ target="_blank" }
