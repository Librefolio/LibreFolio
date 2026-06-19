# 📊 Metriche di Rischio

Le metriche di rischio forniscono **misure quantitative** del rischio di portafoglio. Ogni metrica cattura un aspetto diverso dell'incertezza e nessuna metrica da sola fornisce un quadro completo. L'utilizzo di più metriche insieme offre una visione completa del rischio del portafoglio.

---

## 📋 Panoramica Comparativa

| Metrica | Cosa Misura | Formula | Intervallo | Dettagli |
|--------|-----------------|---------|-------|---------|
| **[Indice di Sharpe](sharpe-ratio.md)** | Rendimento corretto per il rischio (volatilità totale) | $\frac{R_p - R_f}{\sigma_p}$ | $(-\infty, +\infty)$ | [📖](sharpe-ratio.md) |
| **[Indice di Sortino](sortino-ratio.md)** | Rendimento corretto per il rischio (solo volatilità negativa) | $\frac{R_p - R_f}{\sigma_d}$ | $(-\infty, +\infty)$ | [📖](sortino-ratio.md) |
| **[Max Drawdown](max-drawdown.md)** | Il massimo calo da picco a minimo | $\frac{Trough - Peak}{Peak}$ | $[-100\%, 0\%]$ | [📖](max-drawdown.md) |
| **[Volatilità](volatility.md)** | Dispersione dei rendimenti | $\sigma = \sqrt{\text{Var}(R)}$ | $[0, +\infty)$ | [📖](volatility.md) |

---

## 🔑 Quando Usare Ogni Metrica

| Scenario | Metrica Migliore | Perché |
|----------|-------------|-----|
| Confrontare due fondi | **Indice di Sharpe** | Normalizza il rendimento rispetto al rischio totale |
| Distribuzioni di rendimento asimmetriche | **Indice di Sortino** | Penalizza solo la volatilità negativa |
| Pianificazione dello scenario peggiore | **Max Drawdown** | Mostra il punto di massimo ribasso |
| Valutazione generale del rischio | **Volatilità** | Fondamento per tutte le altre metriche |
| Ottimizzazione del portafoglio | **Tutte e quattro** | Ognuna cattura una dimensione diversa |

---

## ⚠️ Errori Comuni

!!! warning "Limitations"

    - **Metriche storiche ≠ rischio futuro**: La volatilità passata potrebbe non prevedere la volatilità futura
    - **Assunzione di distribuzione normale**: Sharpe e Sortino assumono che i rendimenti siano approssimativamente normali; i rendimenti finanziari hanno "code grasse" (fat tails)
    - **Sensibilità al periodo di analisi**: Le metriche cambiano significativamente a seconda della finestra temporale considerata
    - **Dipendenza dal benchmark**: Sharpe e Sortino dipendono dal tasso privo di rischio, che cambia nel tempo

---

## 🔗 Correlati

- 🔀 **[Diversificazione](../diversification.md)** — Come funziona matematicamente la riduzione del rischio
- ⚖️ **[Asset Allocation](../asset-allocation.md)** — Utilizzo delle metriche di rischio per guidare l'allocazione
- 📈 **[Rendimenti e Tassi di Crescita](../../fundamentals/returns.md)** — Il lato "rendimento" del binomio rischio-rendimento
