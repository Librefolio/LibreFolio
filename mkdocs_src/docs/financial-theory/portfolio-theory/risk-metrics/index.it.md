# 📊 Metriche di Rischio

Le metriche di rischio forniscono **misure quantitative** del rischio di portafoglio. Ogni metrica cattura un aspetto diverso dell'incertezza, e nessuna singola metrica racconta l'intera storia. L'utilizzo di più metriche insieme offre una visione completa del rischio di portafoglio.

---

## 📋 Panoramica Comparativa

| Metrica | Cosa Misura | Formula | Range | Dettagli |
|--------|-----------------|---------|-------|---------|
| **[Indice di Sharpe](sharpe-ratio.md)** | Rendimento corretto per il rischio (volatilità totale) | $\frac{R_p - R_f}{\sigma_p}$ | $(-\infty, +\infty)$ | [📖](sharpe-ratio.md) |
| **[Indice di Sortino](sortino-ratio.md)** | Rendimento corretto per il rischio (solo downside) | $\frac{R_p - R_f}{\sigma_d}$ | $(-\infty, +\infty)$ | [📖](sortino-ratio.md) |
| **[Max Drawdown](max-drawdown.md)** | Peggior calo da picco a minimo | $\frac{Trough - Peak}{Peak}$ | $[-100\%, 0\%]$ | [📖](max-drawdown.md) |
| **[Volatilità](volatility.md)** | Dispersione dei rendimenti | $\sigma = \sqrt{\text{Var}(R)}$ | $[0, +\infty)$ | [📖](volatility.md) |

---

## 🔑 Quando Utilizzare Ogni Metrica

| Scenario | Metrica Migliore | Perché |
|----------|-------------|-----|
| Confronto tra due fondi | **Indice di Sharpe** | Normalizza il rendimento rispetto al rischio totale |
| Distribuzioni di rendimento asimmetriche | **Indice di Sortino** | Penalizza solo la volatilità negativa (downside) |
| Pianificazione dello scenario peggiore | **Max Drawdown** | Mostra il punto di massimo drawdown |
| Valutazione generale del rischio | **Volatilità** | Fondamento per tutte le altre metriche |
| Ottimizzazione del portafoglio | **Tutte e quattro** | Ognuna cattura una dimensione differente |

---

## ⚠️ Errori Comuni

!!! warning "Limitations"

    - **Metriche storiche ≠ rischio futuro**: La volatilità passata potrebbe non prevedere la volatilità futura
    - **Ipotesi di distribuzione normale**: Sharpe e Sortino presumono che i rendimenti siano approssimativamente normali; i rendimenti finanziari presentano invece code grasse
    - **Sensibilità al periodo di analisi**: Le metriche cambiano significativamente a seconda della finestra temporale considerata
    - **Dipendenza dal benchmark**: Sharpe e Sortino dipendono dal tasso privo di rischio, che varia nel tempo

---

## 🔗 Correlati

- 🔀 **[Diversificazione](../diversification.md)** — Come funziona matematicamente la riduzione del rischio
- ⚖️ **[Asset Allocation](../asset-allocation.md)** — Utilizzo delle metriche di rischio per guidare l'allocazione
- 📈 **[Rendimenti e Tassi di Crescita](../../fundamentals/returns.md)** — Il lato "rendimento" del binomio rischio-rendimento
