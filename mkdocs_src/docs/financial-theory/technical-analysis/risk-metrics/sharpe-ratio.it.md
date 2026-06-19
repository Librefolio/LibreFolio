# 📐 Indice di Sharpe

L'indice di Sharpe è la metrica di **rendimento corretto per il rischio** più ampiamente utilizzata. Misura quanto rendimento in eccesso si riceve per ogni unità di volatilità totale.

---

## 🔢 Formula

$$
S = \frac{R_p - R_f}{\sigma_p}
$$

dove:

- $R_p$ = rendimento del portafoglio (annualizzato)
- $R_f$ = tasso risk-free (es. tasso dei titoli del Tesoro)
- $\sigma_p$ = deviazione standard del portafoglio (annualizzata)

---

## 💡 Interpretazione

| Indice di Sharpe | Qualità |
|---|---|
| $< 0$ | Il portafoglio ha sottoperformato il tasso risk-free |
| $0 - 0.5$ | Rendimento corretto per il rischio subottimale |
| $0.5 - 1.0$ | Accettabile |
| $1.0 - 2.0$ | Buono |
| $> 2.0$ | Eccellente (raro per periodi prolungati) |

!!! example "Esempio numerico"

    Rendimento del portafoglio: 12%, Tasso risk-free: 3%, Volatilità: 15%

    $$S = \frac{0.12 - 0.03}{0.15} = 0.60$$

    Per ogni 1% di volatilità, il portafoglio ha guadagnato lo 0,60% di rendimento in eccesso.

---

## ⚙️ Annualizzazione

Quando calcolato dai rendimenti giornalieri:

$$
S_{annual} = S_{daily} \times \sqrt{252}
$$

dove 252 è il numero tipico di giorni di trading per anno. Questo presuppone che i rendimenti siano IID (indipendenti e identicamente distribuiti) — un'approssimazione che non è più valida in caso di rendimenti autocorrelati.

---

## ⚠️ Limitazioni

### 📊 Penalità Simmetrica

L'indice di Sharpe penalizza la **volatilità al rialzo** tanto quanto quella negativa. Un asset che presenta frequenti picchi verso l'alto (estremamente desiderabile!) avrà un indice di Sharpe più basso rispetto a uno con lo stesso rendimento ma con meno movimenti al rialzo.

→ Per distribuzioni di rendimento asimmetriche, preferire l'**[Indice di Sortino](sortino-ratio.md)**.

### 📈 Sensibilità agli Outlier

Alcuni rendimenti estremi possono distorcere significativamente la deviazione standard, rendendo l'indice di Sharpe instabile per periodi di tempo brevi.

### 🔄 Dipendenza dal Periodo Temporale

L'indice di Sharpe può variare drasticamente a seconda della finestra temporale considerata (lookback window). Una strategia con un eccellente indice di Sharpe a 5 anni potrebbe avere un indice di Sharpe a 1 anno scarso (o viceversa).

---

## 🔗 Correlati

- 📊 **[Indice di Sortino](sortino-ratio.md)** — Variante basata solo sulla volatilità al ribasso
- 📊 **[Volatilità](volatility.md)** — Il denominatore dell'indice di Sharpe
- 📈 **[Rendimenti](../../fundamentals/returns.md)** — Il numeratore dell'indice di Sharpe
