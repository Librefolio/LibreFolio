# 📊 Rapporto di Sortino

Il rapporto di Sortino è una modifica del rapporto di Sharpe che penalizza esclusivamente la **volatilità al ribasso**. Riconosce che gli investitori sono primariamente preoccupati dalle perdite, non dalle sorprese positive.

---

## 🔢 Formula

$$
So = \frac{R_p - R_f}{\sigma_d}
$$

dove:

- $R_p$ = rendimento del portafoglio (annualizzato)
- $R_f$ = tasso risk-free (o rendimento minimo accettabile)
- $\sigma_d$ = **deviazione al ribasso** (annualizzata)

### 📐 Deviazione al ribasso

$$
\sigma_d = \sqrt{\frac{1}{N} \sum_{i=1}^{N} \min(R_i - R_f, 0)^2}
$$

Solo i rendimenti **al di sotto** della soglia contribuiscono alla deviazione al ribasso. I rendimenti superiori alla soglia contribuiscono con zero.

---

## 💡 Interpretazione

| Rapporto di Sortino | Qualità |
|---|---|
| $< 0$ | Rendimenti al di sotto della soglia |
| $0 - 1.0$ | Rendimento moderato aggiustato per il rischio di ribasso |
| $1.0 - 2.0$ | Buono |
| $> 2.0$ | Eccellente gestione del rischio di ribasso |

!!! example "Esempio numerico"

    Rendimento del portafoglio: 12%, Tasso risk-free: 3%, Deviazione al ribasso: 10%

    $$So = \frac{0.12 - 0.03}{0.10} = 0.90$$

    Confronto con Sharpe (se σ totale = 15%): $S = 0.60$. Il Sortino è più alto perché la volatilità positiva è esclusa.

---

## 📊 Sharpe vs Sortino

| Aspetto | Sharpe | Sortino |
|--------|--------|---------|
| **Misura del rischio** | Deviazione standard totale | Solo deviazione al ribasso |
| **Penalizza il rialzo?** | Sì ❌ | No ✅ |
| **Ideale per** | Distribuzioni di rendimento simmetriche | Rendimenti asimmetrici / sbilanciati |
| **Esempio** | Indice di mercato ampio | Strategie con opzioni, portafogli concentrati |

### 🔑 Quando preferire il Sortino

- **Distribuzioni asimmetriche**: Strategie che presentano occasionalmente grandi guadagni ma perdite controllate
- **Portafogli basati su opzioni**: Payoff intrinsecamente asimmetrici
- **Growth stocks**: Tendono ad avere distribuzioni di rendimento con asimmetria positiva
- **Qualsiasi investitore** che si preoccupi più del rischio di ribasso che del rischio totale

---

## ⚠️ Limitazioni

!!! warning "Bias da campione ridotto"

    La deviazione al ribasso richiede un numero sufficiente di punti dati al di sotto della soglia. Con pochi rendimenti negativi (ad esempio, durante brevi periodi di bull market), la stima diventa inaffidabile e il rapporto di Sortino può risultare ingannevolmente alto.

---

## 🔗 Correlati

- 📐 **[Rapporto di Sharpe](sharpe-ratio.md)** — Variante basata sulla volatilità totale
- 📊 **[Volatilità](volatility.md)** — Comprendere la deviazione standard
- 📈 **[Max Drawdown](max-drawdown.md)** — Un'altra metrica focalizzata sul rischio di ribasso
