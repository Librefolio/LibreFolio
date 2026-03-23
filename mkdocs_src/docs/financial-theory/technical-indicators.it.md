# 📉 Indicatori Tecnici

Questa pagina documenta gli indicatori di analisi tecnica disponibili come overlay sui grafici nel modulo FX di LibreFolio. Ogni indicatore viene spiegato da due prospettive complementari:
l'interpretazione **finanziaria** che i trader usano quotidianamente, e l'equivalente in **elaborazione del segnale** che ingegneri con background in sistemi di controllo o DSP riconosceranno all'istante.

!!! info "Perché due prospettive?"

    I mercati finanziari **NON** sono sistemi LTI (Lineari Tempo-Invarianti) stazionari — sono
    rumorosi, caotici e il loro contenuto spettrale cambia nel tempo. Eppure gli strumenti
    matematici che usiamo per estrarre trend, momentum o volatilità sono *esattamente* gli
    stessi filtri a tempo discreto insegnati in qualsiasi corso di elaborazione del segnale.
    Se avete mai progettato un filtro Butterworth passa-basso o calcolato una varianza mobile,
    già comprendete questi indicatori — solo con nomi diversi.

---

## ⚡ L'intuizione "Veloce" vs "Lento"

In finanza, *veloce* e *lento* si riferiscono alla **costante di tempo** ($\tau$) del filtro sottostante.

| Proprietà | Veloce (piccolo $N$) | Lento (grande $N$) |
|---|---|---|
| Frequenza di taglio $f_c$ | Più alta | Più bassa |
| Rigetto del rumore | Scarso — lascia passare le HF | Buono — forte smorzamento |
| Sfasamento | Piccolo — reagisce rapidamente | Grande — ritardo significativo |
| $N$ tipico | 9, 12, 14 | 26, 50, 200 |

---

## 📉 EMA — Media Mobile Esponenziale { #ema }

### 💡 Significato Finanziario

L'EMA traccia il **trend** smorzando il rumore quotidiano dei prezzi, dando più peso alle
osservazioni recenti rispetto a quelle più vecchie. I trader sovrappongono EMA con periodi
diversi su un grafico dei prezzi: quando un EMA a periodo breve incrocia *sopra* un EMA a
periodo lungo, segnala momentum rialzista (una "croce dell'oro"); l'incrocio opposto segnala
un rallentamento ("croce della morte").

### 🔢 Formula Matematica

L'EMA è definita dalla ricorrenza del primo ordine:

$$
EMA_t = \alpha \cdot P_t + (1 - \alpha) \cdot EMA_{t-1}
$$

dove $P_t$ è il prezzo di chiusura al tempo $t$ e $\alpha$ è il **coefficiente di livellamento**.

**Mappatura $N$ → $\alpha$.**
I trader specificano un "periodo" $N$ (in giorni). Il coefficiente si ricorda eguagliando
l'*età media* dei dati tra un'EMA e una Media Mobile Semplice (SMA) della stessa finestra:

$$
\text{Età}_{SMA} = \frac{N-1}{2}, \qquad
\text{Età}_{EMA} = \frac{1-\alpha}{\alpha}
$$

Uguagliandole:

$$
\alpha = \frac{2}{N+1}
$$

Ad esempio, $N = 14 \implies \alpha = 2/15 \approx 0.133$.

### ⚙️ Parametri

| Parametro | Chiave | Default | Descrizione |
|---|---|---|---|
| Periodo ($N$) | `period` | 14 | Periodo di osservazione in giorni. Maggiore → più smorzato, più lento. |
| Offset | `offset` | 0 | Spostamento verticale come % del valore base. |

### 🎛️ Equivalente in Elaborazione del Segnale — Filtro passa-basso IIR del primo ordine

La ricorrenza $y[n] = \alpha\,x[n] + (1-\alpha)\,y[n-1]$ è esattamente un **filtro passa-basso
IIR (Infinite Impulse Response) del primo ordine**. La sua funzione di trasferimento nel
dominio $z$ è:

$$
H(z) = \frac{\alpha}{1 - (1-\alpha)\,z^{-1}}
$$

La frequenza di taglio a $-3\,\text{dB}$ (normalizzata) è:

$$
\omega_c = \cos^{-1}\!\left(1 - \frac{\alpha^2}{2(1-\alpha)}\right)
$$

Quando $\alpha$ è piccola ($N$ grande) la banda passante si restringe drasticamente, attenuando
tutto tranne la componente DC (il trend di lungo periodo).

!!! tip "Posizione del polo"

    Il singolo polo si trova in $z = 1-\alpha$. Per $N = 200$, $\alpha \approx 0.01$, quindi
    il polo è in $z = 0.99$ — estremamente vicino al cerchio unitario, il che spiega il forte
    smorzamento e il large ritardo di gruppo.

:material-link: [EMA su Wikipedia](https://en.wikipedia.org/wiki/Exponential_smoothing){ target="_blank" }

---

## 📊 MACD — Moving Average Convergence Divergence { #macd }

### 💡 Significato Finanziario

**Non** ti dice che il prezzo sta salendo (lo vedi già); ti dice se la *velocità di variazione*
del trend è positiva o negativa. I trader osservano l'incrocio della linea MACD con la linea di
segnale — un incrocio rialzista suggerisce momentum crescente, uno ribassista suggerisce
esaurimento.

### 🔢 Formule Matematiche

Il sistema MACD produce tre serie:

1. **Linea MACD** (l'output passa-banda):

 $$
 MACD_t = EMA_{fast}(C_t) - EMA_{slow}(C_t)
 $$

2. **Linea di Segnale** (MACD smorzato):

 $$
 Signal_t = EMA_{signal}(MACD_t)
 $$

3. **Istogramma** (delta momentum):

 $$
 Histogram_t = MACD_t - Signal_t
 $$

### ⚙️ Parametri

| Parametro | Chiave | Default | Descrizione |
|---|---|---|---|
| Periodo Veloce | `fastPeriod` | 12 | Periodo di osservazione EMA a breve termine (giorni). |
| Periodo Lento | `slowPeriod` | 26 | Periodo di osservazione EMA a lungo termine (giorni). |
| Periodo Segnale | `signalPeriod` | 9 | Periodo di osservazione EMA applicato alla linea MACD. |

### 🎛️ Equivalente in Elaborazione del Segnale — Filtro passa-banda (Derivata Smorzata)

Sottrarre due filtri passa-basso con diverse frequenze di taglio produce un **filtro passa-banda**.
$EMA_{fast} - EMA_{slow}$ annulla la componente DC (il trend di lungo periodo condiviso da
entrambi) sopprime il rumore ad alta frequenza (già filtrato da entrambe le EMA). Ciò che
rimane è la banda *a frequenza media*: l'oscillazione del momentum.

Nel dominio $z$:

$$
H_{MACD}(z) = H_{fast}(z) - H_{slow}(z)
 = \frac{\alpha_f}{1-(1-\alpha_f)z^{-1}}
 - \frac{\alpha_s}{1-(1-\alpha_s)z^{-1}}
$$

La Linea di Segnale è un altro passa-basso applicato a questo output passa-banda — agisce come
un **filtro adattato**, ritardando leggermente il segnale per ridurre i falsi positivi nel
rilevamento degli incroci.

!!! note "Interpretazione derivata"

    Per piccoli $\alpha$, $EMA_{fast} - EMA_{slow}$ si comporta come una derivata smorzata del
    primo ordine $\frac{d}{dt}[\text{trend}]$. Quando l'istogramma cambia segno, la "velocità"
    del trend cambia direzione.

:material-link: [MACD su Wikipedia](https://en.wikipedia.org/wiki/MACD){ target="_blank" }

---

## 💪 RSI — Relative Strength Index { #rsi }

### 💡 Significato Finanziario

L'RSI misura se acquirenti o venditori hanno dominato *di recente*. Risponde a: *"Negli
ultimi $N$ giorni, quanta parte del movimento totale del prezzo è stata rialzista vs
ribassista?"* Il risultato viene compresso in un intervallo 0-100:

- **RSI > 70** → Ipercomprato — la molla è tesa, un ritracciamento è statisticamente probabile.
- **RSI < 30** → Ipervenduto — la molla è compressa, un rimbalzo è probabile.

### 🔢 Formule Matematiche

1. **Scomposizione** delle variazioni giornaliere in guadagni e perdite:

 $$
 U_t = \max(P_t - P_{t-1},\; 0), \qquad
 D_t = \max(P_{t-1} - P_t,\; 0)
 $$

2. **Smorzamento** di ciascun componente con una media mobile esponenziale (variante SMMA):

 $$
 \overline{U} = SMMA_N(U), \qquad
 \overline{D} = SMMA_N(D)
 $$

3. **Rapporto di Forza Relativa** e normalizzazione:

 $$
 RS = \frac{\overline{U}}{\overline{D}}, \qquad
 RSI = 100 - \frac{100}{1 + RS}
 $$

La normalizzazione $100 - 100/(1+RS)$ è una sigmoide monotonicamente crescente che mappa
$RS \in [0, \infty)$ in $RSI \in [0, 100)$.

### ⚙️ Parametri

| Parametro | Chiave | Default | Descrizione |
|---|---|---|---|
| Periodo ($N$) | `period` | 14 | Periodo di osservazione per la SMMA. |
| Ipercomprato | `overbought` | 70 | Soglia per la zona ipercomprata. |
| Ipervenduto | `oversold` | 30 | Soglia per la zona ipervenduta. |

### 🎛️ Equivalente in Elaborazione del Segnale — Indicatore di Duty Cycle / Saturazione

Immaginate di dividere il segnale di delta prezzo $\Delta P[n]$ nelle sue componenti positive
e negative a semionda rettificata, poi filtrando ciascuna con un passa-basso. L'RSI è il
**rapporto dell'inviluppo positivo sull'inviluppo totale**, riscalato a $[0, 100]$.

In termini di sistemi di controllo, è un **rilevatore di saturazione**: quando l'uscita del
sistema (prezzo) si è mossa in una direzione per troppo tempo, l'RSI segnala che l'attuatore
(mercato) è vicino al suo limite. Come qualsiasi oscillatore in un loop di feedback, più ci si
allontana dall'equilibrio, più forte è la forza di ripristino — da qui la proprietà di reversione
verso la media che i trader sfruttano.

!!! warning "Non-stazionarietà"

    Le soglie 70/30 assumono distribuzioni di rendimento approssimativamente simmetriche. In
    forti trend di mercato l'RSI può rimanere sopra 70 per settimane — è un indicatore
    *probabilistico*, non deterministico.

:material-link: [RSI su Wikipedia](https://en.wikipedia.org/wiki/Relative_strength_index){ target="_blank" }

---

## 📏 Bollinger Bands { #bollinger-bands }

### 💡 Significato Finanziario

Le Bollinger Bands misurano dinamicamente la **volatilità** e tracciano un "confine di
normalità" adattivo intorno al prezzo. Quando le bande sono larghe, il mercato è volatile;
quando si stringono insieme, una rottura è imminente. Un prezzo che tocca la banda superiore
segnala euforia statistica; toccare la banda inferiore segnala un anomalo calo.

### 🔢 Formule Matematiche

1. **Banda Mediana** (valore atteso):

 $$
 MB_t = SMA_N(C_t)
 $$

2. **Deviazione standard** dei prezzi nella finestra:

 $$
 \sigma_t = \sqrt{\frac{1}{N} \sum_{i=0}^{N-1} (C_{t-i} - MB_t)^2}
 $$

3. **Bande Superiore e Inferiore**:

 $$
 Upper_t = MB_t + k \cdot \sigma_t, \qquad
 Lower_t = MB_t - k \cdot \sigma_t
 $$

Con $k = 2$, se i rendimenti fossero normalmente distribuiti il prezzo rimarrebbe dentro le
bande ~95.4% del tempo. In pratica, i rendimenti finanziari hanno *code grasse* (leptocurtici),
quindi le violazioni sono più frequenti — ma comunque statisticamente significative.

### ⚙️ Parametri

| Parametro | Chiave | Default | Descrizione |
|---|---|---|---|
| Periodo ($N$) | `period` | 20 | Periodo di osservazione SMA per il valore atteso. |
| Moltiplicatore ($k$) | `multiplier` | 2 | Numero di deviazioni standard. |

### 🎛️ Equivalente in Elaborazione del Segnale — Tracker di Intervallo di Confidenza Adattativo

La Banda Mediana è un filtro **FIR (Finite Impulse Response) moving average** — il più
semplice passa-basso con una finestra rettangolare di lunghezza $N$. Le bande aggiungono un
**inviluppo variabile nel tempo** a $\pm k\sigma$, che è essenzialmente una stima mobile
della varianza istantanea del segnale.

Nel linguaggio dei filtri adattativi, questo è un **tracciatore del valore atteso con intervallo
di confidenza adattativo**. Quando la varianza $\sigma^2$ cala (lo "Squeeze di Bollinger"), il
sistema è in uno stato a bassa entropia. Nei sistemi caotici come i mercati finanziari, i periodi
a bassa entropia sono seguiti in modo affidabile da esplosioni ad alta entropia (alta volatilità)
— rendendo lo squeeze uno dei setup più osservati nell'analisi tecnica.

!!! info "FIR vs IIR"

    A differenza dell'EMA (IIR, un polo), la SMA è un **filtro FIR** con un ritardo di gruppo
    perfettamente piatto di $(N-1)/2$ campioni. Compromette una banda di transizione più ampia
    per zero distorsione di fase — ideale per centrare l'inviluppo di confidenza.

:material-link: [Bollinger Bands su Wikipedia](https://en.wikipedia.org/wiki/Bollinger_Bands){ target="_blank" }
