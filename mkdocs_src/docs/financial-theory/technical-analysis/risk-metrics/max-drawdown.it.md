# 📉 Max Drawdown

Il Max Drawdown (MDD) misura la **maggiore flessione dal picco al minimo** (peak-to-trough) nel valore del portafoglio prima che venga stabilito un nuovo picco. Risponde alla domanda: *"Qual è stata la perdita peggiore che un investitore avrebbe potuto subire?"*

---

## 🔢 Formula

$$
MDD = \frac{Trough - Peak}{Peak} = \min_{t} \left( \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau} \right)
$$

dove $V_t$ è il valore del portafoglio al tempo $t$.

Il drawdown in un qualsiasi punto $t$ è:

$$
DD_t = \frac{V_t - V_{peak}}{V_{peak}}
$$

Il max drawdown è il valore minimo (più negativo) di $DD_t$ nell'intero periodo di osservazione.

---

## 💡 Interpretazione

| Max Drawdown | Contesto Tipico |
|---|---|
| $-5\%$ a $-10\%$ | Correzione normale, portafoglio ben diversificato |
| $-10\%$ a $-20\%$ | Correzione significativa |
| $-20\%$ a $-30\%$ | Fase di mercato orso (bear market) |
| $-30\%$ a $-50\%$ | Bear market severo (2008, COVID-2020) |
| $> -50\%$ | Catastrofico (posizioni concentrate, crypto) |

!!! example "Esempio numerico"

    Sequenza del valore del portafoglio: 100 → 120 → 90 → 110 → 130

    - Picco: 120
    - Minimo: 90
    - MDD: $(90 - 120) / 120 = -25\%$
    - Recupero: il valore è risalito a 120, poi nuovo massimo a 130

---

## ⏱️ Tempo di Recupero

Una metrica altrettanto importante è il **tempo di recupero** — quanto tempo occorre per recuperare dal drawdown e raggiungere un nuovo picco:

$$
T_{recovery} = t_{new\_peak} - t_{trough}
$$

| Asset Class | Tempo di Recupero Tipico (dopo un drawdown significativo) |
|-------------|---------------------------------------------|
| Azioni USA (S&P 500) | 1-5 anni |
| Obbligazioni | Da mesi a 1-2 anni |
| Crypto | Altamente variabile (da mesi a anni) |

!!! warning "Asimmetria delle perdite"

    Una perdita del 50% richiede un **guadagno del 100%** per essere recuperata:

    $$
    \text{Guadagno richiesto} = \frac{1}{1 + MDD} - 1
    $$

    <div style="display: flex; justify-content: center;">

    | Perdita | Guadagno Richiesto |
    |:----:|:-------------:|
    | -10% | +11.1% |
    | -25% | +33.3% |
    | -50% | +100% |
    | -75% | +300% |

    </div>

---

## 📊 Grafico del Drawdown

Un grafico del drawdown mostra l'andamento di $DD_t$ nel tempo. È sempre zero o negativo, toccando lo zero a ogni nuovo picco. La valle più profonda rappresenta il max drawdown. Questa visualizzazione rende facile:

- Identificare il **timing** dei periodi peggiori
- Vedere con quale frequenza si verificano i drawdown
- Confrontare i pattern di recupero tra diverse strategie

---

## 🔗 Correlati

- 📊 **[Volatilità](volatility.md)** — La deviazione standard non cattura la severità del drawdown
- 📐 **[Indice di Sharpe](sharpe-ratio.md)** — Rendimento corretto per il rischio (utilizza la volatilità, non il drawdown)
- 🔀 **[Diversificazione](../diversification.md)** — Lo strumento principale per ridurre il max drawdown
