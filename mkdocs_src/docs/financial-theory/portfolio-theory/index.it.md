# 📈 Teoria del Portafoglio

La teoria del portafoglio fornisce il quadro matematico per costruire portafogli di investimento che massimizzino il rendimento atteso per un dato livello di rischio — o equivalentemente, minimizzino il rischio per un dato rendimento atteso.

---

## 📖 Panoramica

### 🏛️ Modern Portfolio Theory (MPT)

Introdotta da Harry Markowitz nel 1952, la Modern Portfolio Theory ha rivoluzionato l'investimento dimostrando che **il rischio di portafoglio non è semplicemente la somma dei rischi dei singoli asset**. Attraverso la diversificazione, un investitore può ridurre la volatilità del portafoglio senza sacrificare il rendimento atteso.

L'intuizione chiave: ciò che conta non è solo il rischio e il rendimento individuale di ogni asset, ma come gli asset si muovono **relativamente l'uno all'altro** (correlazione).

### 📐 La Frontiera Efficiente

La frontiera efficiente è l'insieme di portafogli che offrono il **massimo rendimento atteso per ogni livello di rischio**:

$$
\max_{w} \quad E[R_p] = \sum_i w_i \cdot E[R_i]
$$

soggetto a:

$$
\sigma_p^2 = \sum_i \sum_j w_i w_j \sigma_i \sigma_j \rho_{ij} \leq \sigma_{target}^2
$$

dove $w_i$ sono i pesi del portafoglio, $E[R_i]$ i rendimenti attesi, $\sigma_i$ le volatilità e $\rho_{ij}$ le correlazioni.

Qualsiasi portafoglio **al di sotto** della frontiera è subottimale — è possibile ottenere un rendimento maggiore a parità di rischio, o un rischio minore a parità di rendimento.

---

## 📖 Cosa troverai

### 🔀 [Diversificazione](diversification.md)

Il fondamento matematico del principio "non mettere tutte le uova in un solo paniere". Come la combinazione di asset con correlazione imperfetta riduca la varianza del portafoglio — e i limiti della diversificazione contro il rischio sistematico.

### ⚖️ [Asset Allocation](asset-allocation.md)

Allocazione strategica vs tattica, glide path, strategie target-date e l'arte del ribilanciamento. Come decidere *quanto* di ogni asset class detenere.

### 📊 [Metriche di Rischio](../technical-analysis/risk-metrics/index.md)

Misure quantitative del rischio di portafoglio. Dalla deviazione standard all'indice di Sharpe, ogni metrica cattura un aspetto diverso del rischio:

- **[Indice di Sharpe](../technical-analysis/risk-metrics/sharpe-ratio.md)** — Rendimento aggiustato per il rischio (volatilità totale)
- **[Indice di Sortino](../technical-analysis/risk-metrics/sortino-ratio.md)** — Rendimento aggiustato per il rischio (solo il rischio di ribasso)
- **[Max Drawdown](../technical-analysis/risk-metrics/max-drawdown.md)** — Calo massimo da picco a minimo
- **[Volatilità](../technical-analysis/risk-metrics/volatility.md)** — Deviazione standard dei rendimenti

---

## 🔑 Assunzioni Chiave e Limitazioni

!!! warning "MPT assumptions"

    La Modern Portfolio Theory assume:

    1. **Investitori razionali** che cercano di massimizzare l'utilità
    2. **Distribuzione normale** dei rendimenti (nella pratica, i rendimenti presentano code grasse (fat tails))
    3. Rendimenti attesi, volatilità e correlazioni **conosciuti** (nella pratica, questi vengono stimati con un margine di errore)
    4. **Mercati senza attriti** — nessuna tassa, nessun costo di transazione (LibreFolio ti aiuta a monitorarli!)

Nonostante queste limitazioni, la MPT rimane il fondamento della gestione di portafoglio istituzionale e fornisce il vocabolario utilizzato da tutta l'industria degli investimenti.

---

## 🔗 Sezioni Correlate

- 🏦 **[Strumenti](../instruments/index.md)** — Gli elementi costitutivi dei portafogli
- 📐 **[Fondamentali](../fundamentals/index.md)** — Rendimenti, convenzioni di conteggio dei giorni, tassazione
- 📊 **[Analisi Tecnica](../technical-analysis/index.md)** — Strumenti di analisi per i singoli asset
