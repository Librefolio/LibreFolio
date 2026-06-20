# 📊 Volatilità

La volatilità misura la **dispersione dei rendimenti** — ovvero quanto il prezzo di un asset fluttua nel tempo. È la misura del rischio più fondamentale in finanza e il mattone costruttivo per quasi tutte le altre metriche di rischio.

---

## 🔢 Formula

### 📐 Deviazione Standard dei Rendimenti

$$
\sigma = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (R_i - \bar{R})^2}
$$

dove $R_i$ sono i rendimenti dei singoli periodi e $\bar{R}$ è il rendimento medio.

### 📈 Annualizzazione

La volatilità giornaliera viene annualizzata moltiplicandola per la radice quadrata del numero di giorni di trading:

$$
\sigma_{annual} = \sigma_{daily} \times \sqrt{252}
$$

!!! info "Perché √252?"

    Si assume che i rendimenti siano indipendenti tra i vari giorni. La varianza di una somma di $N$ variabili indipendenti è $N$ volte la varianza individuale. Pertanto:

    $$\text{Var}_{annual} = 252 \times \text{Var}_{daily}$$
    $$\sigma_{annual} = \sqrt{252} \times \sigma_{daily}$$

---

## 💡 Interpretazione

| Volatilità Annualizzata | Asset Tipici |
|---|---|
| 1-5% | Mercato monetario, obbligazioni a breve termine |
| 5-15% | Obbligazioni governative, corporate investment-grade |
| 15-25% | Azioni large-cap, ETF azionari diversificati |
| 25-40% | Azioni small-cap, singole azioni |
| 40-80%+ | Crypto, meme stocks, prodotti a leva |

---

## 📊 Volatilità Realizzata vs Implicita

### 📈 Volatilità Realizzata (Storica)

Calcolata a partire dai dati di prezzo **passati**. Questo è ciò che calcola LibreFolio:

$$
\sigma_{realized} = \text{StdDev}(\text{historical returns})
$$

### 🔮 Volatilità Implicita

Estratta dai **prezzi delle opzioni** utilizzando il modello di Black-Scholes. Rappresenta l'**aspettativa** del mercato sulla volatilità futura:

$$
C = f(S, K, T, r, \sigma_{implied})
$$

La volatilità implicita è orientata al futuro ma è disponibile solo per gli asset con opzioni negoziabili.

---

## 🔄 Volatilità a Finestra Mobile (Rolling Window)

Invece di calcolare un unico valore di volatilità per l'intero periodo, la **volatilità a finestra mobile** calcola $\sigma$ su una finestra scorrevole (ad esempio, 30 giorni), producendo una serie temporale che mostra come evolve la volatilità:

$$
\sigma_t^{(w)} = \text{StdDev}(R_{t-w+1}, R_{t-w+2}, \ldots, R_t)
$$

Questo è utile per:

- Identificare i **regimi di volatilità** (periodi di calma rispetto a periodi turbolenti)
- Rilevare il **clustering della volatilità** (i giorni ad alta volatilità tendono a essere seguiti da altri giorni ad alta volatilità)
- Impostare dimensioni di posizione dinamiche (ridurre l'esposizione durante i periodi di alta volatilità)

---

## 📐 Volatilità e Teoria di Portafoglio

La volatilità svolge un ruolo centrale nella [Teoria Moderna di Portafoglio](../index.md):

- È il **denominatore** dello [Sharpe Ratio](sharpe-ratio.md)
- Determina l'**ampiezza** delle [Bollinger Bands](../../technical-analysis/indicators/bollinger-bands.md)
- È l'input chiave per l'ottimizzazione del portafoglio (minimizzazione di $\sigma_p$ per un target $R_p$)
- La [Diversificazione](../../portfolio-theory/diversification.md) riduce la volatilità del portafoglio quando le correlazioni tra gli asset sono inferiori a 1

---

## ⚠️ Limitazioni

!!! warning "Volatilità ≠ Rischio"

    La volatilità tratta i movimenti al rialzo e al ribasso allo stesso modo. Un asset che ha frequenti picchi verso l'alto presenta un'alta volatilità ma può essere molto attraente. Per una misura focalizzata solo sul ribasso, utilizzare il [Sortino Ratio](sortino-ratio.md) o il [Max Drawdown](max-drawdown.md).

!!! warning "Non-normalità"

    I rendimenti finanziari tipicamente presentano:

    - **Code pesanti** (eventi più estremi di quanto previsto da una distribuzione normale)
    - **Asimmetria negativa** (crolli significativi più comuni di guadagni significativi)
    - **Clustering della volatilità** (alternanza di periodi calmi e turbolenti)

    La sola deviazione standard non cattura queste caratteristiche.

---

## 🔗 Correlati

- 📐 **[Sharpe Ratio](sharpe-ratio.md)** — Utilizza la volatilità come denominatore del rischio
- 📊 **[Sortino Ratio](sortino-ratio.md)** — Variante della volatilità focalizzata esclusivamente sul rischio di ribasso
- 📏 **[Bollinger Bands](../../technical-analysis/indicators/bollinger-bands.md)** — Inviluppo di volatilità sui grafici
- 🔀 **[Diversificazione](../../portfolio-theory/diversification.md)** — Ridurre la volatilità del portafoglio
