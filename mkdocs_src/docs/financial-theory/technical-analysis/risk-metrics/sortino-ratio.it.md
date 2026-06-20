# 📊 Indice di Sortino

L'indice di Sortino è una modifica dell'indice di Sharpe che penalizza esclusivamente la **volatilità negativa** (downside volatility). Riconosce che gli investitori sono primariamente preoccupati dalle perdite, non dalle sorprese positive.

---

## 🔢 Formula

$$
So = \frac{R_p - R_f}{\sigma_d}
$$

dove:

- $R_p$ = rendimento del portafoglio (annualizzato)
- $R_f$ = tasso risk-free (o rendimento minimo accettabile)
- $\sigma_d$ = **deviazione negativa** (downside deviation, annualizzata)

### 📐 Deviazione Negativa (Downside Deviation)

$$
\sigma_d = \sqrt{\frac{1}{N} \sum_{i=1}^{N} \min(R_i - R_f, 0)^2}
$$

Solo i rendimenti **inferiori** alla soglia contribuiscono alla deviazione negativa. I rendimenti superiori alla soglia contribuiscono con zero.

---

## 💡 Interpretazione

| Indice di Sortino | Qualità |
|---|---|
| $< 0$ | Rendimento inferiore alla soglia |
| $0 - 1.0$ | Rendimento moderato rettificato per il rischio negativo |
| $1.0 - 2.0$ | Buono |
| $> 2.0$ | Eccellente gestione del rischio negativo |

!!! example "Esempio numerico"

    Rendimento del portafoglio: 12%, Tasso risk-free: 3%, Deviazione negativa: 10%

    $$So = \frac{0.12 - 0.03}{0.10} = 0.90$$

    Confronto con Sharpe (se total σ = 15%): $S = 0.60$. Il Sortino è più alto perché la volatilità positiva è esclusa.

---

## 📊 Sharpe vs Sortino

| Aspetto | Sharpe | Sortino |
|--------|--------|---------|
| **Misura del rischio** | Deviazione standard totale | Solo deviazione negativa |
| **Penalizza il rialzo?** | Sì ❌ | No ✅ |
| **Ideale per** | Distribuzioni di rendimento simmetriche | Rendimenti asimmetrici / con skewness |
| **Esempio** | Indice di mercato ampio | Strategie con opzioni, portafogli concentrati |

### 🔑 Quando preferire il Sortino

- **Distribuzioni asimmetriche**: Strategie che hanno occasionali grandi guadagni ma perdite controllate
- **Portafogli basati su opzioni**: Payoff intrinsecamente asimmetrici
- **Growth stocks**: Tendono ad avere distribuzioni di rendimento asimmetriche positive
- **Qualsiasi investitore** che sia più preoccupato del rischio di ribasso che del rischio totale

---

## ⚠️ Limitazioni

!!! warning "Small sample bias"

    La deviazione negativa richiede un numero sufficiente di punti dati al di sotto della soglia. Con pochi rendimenti negativi (ad esempio, in brevi periodi di mercato toro), la stima diventa inaffidabile e l'indice di Sortino può risultare ingannevolmente alto.

---

## 🔗 Correlati

- 📐 **[Indice di Sharpe](sharpe-ratio.md)** — Variante basata sulla volatilità totale
- 📊 **[Volatilità](volatility.md)** — Comprendere la deviazione standard
- 📈 **[Max Drawdown](max-drawdown.md)** — Altra metrica focalizzata sul rischio di ribasso
