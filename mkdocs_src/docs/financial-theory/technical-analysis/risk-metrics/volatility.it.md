# 📊 Volatilità

La volatilità misura la **dispersione dei rendimenti** — quanto il prezzo di un asset fluttua nel tempo. È la misura di rischio più fondamentale in finanza e la base di quasi tutte le altre metriche di rischio.

---

## 🔢 Formula {: #formula }

### 📐 Deviazione Standard dei Rendimenti {: #standard-deviation-of-returns }

$$
\sigma = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (R_i - \bar{R})^2}
$$

dove $R_i$ sono i rendimenti dei singoli periodi e $\bar{R}$ è il rendimento medio.

### 📈 Annualizzazione {: #annualization }

La volatilità per periodo viene annualizzata moltiplicandola per la radice quadrata del numero di periodi contenuti in un anno:

$$
\sigma_{annual} = \sigma_{period} \times \sqrt{f}
$$

Il fattore $f$ è **misurato dai dati osservati**, non fissato in anticipo: è il numero di rendimenti effettivamente utilizzati, riscalato a un anno solare completo in base all'intervallo temporale che coprono.

$$
f = \frac{N \times 365}{D}
$$

dove $N$ è il numero di rendimenti di periodo e $D$ i giorni di calendario che essi coprono.

!!! info "Perché una radice quadrata?"

    Si assume che i rendimenti siano indipendenti tra i periodi. La varianza di una somma di $f$ variabili indipendenti è $f$ volte la varianza individuale. Pertanto:

    $$\text{Var}_{annual} = f \times \text{Var}_{period}$$

    $$\sigma_{annual} = \sqrt{f} \times \sigma_{period}$$

!!! info "√252 è un risultato, non una costante"

    Un titolo con prezzo giornaliero contribuisce con circa 252 rendimenti nell'arco di un anno solare completo, quindi $f = 252 \times 365 / 365 = 252$ e si ritrova il familiare $\sqrt{252}$ — come esito della misurazione, non come assunzione scritta al suo interno. Uno strumento che viene scambiato ogni giorno di calendario, come le criptovalute, dà $f \approx 365$ e quindi $\approx \sqrt{365}$: un $\sqrt{252}$ codificato in modo fisso **sottostimerebbe** la sua volatilità annualizzata. Un fondo con prezzo settimanale dà $f \approx 52$.

    → Vedi **[Annualizzazione Osservata](observed-annualization.md)** per la derivazione, gli esempi svolti e cosa aggiunge la copertura a questi elementi.

---

## 💡 Interpretazione {: #interpretation }

| Volatilità Annualizzata | Asset Tipici |
|---|---|
| 1-5% | Mercato monetario, obbligazioni a breve termine |
| 5-15% | Titoli di Stato, obbligazioni societarie investment-grade |
| 15-25% | Azioni large-cap, ETF azionari diversificati |
| 25-40% | Azioni small-cap, singoli titoli azionari |
| 40-80%+ | Criptovalute, azioni meme, prodotti a leva |

---

## 📊 Volatilità Realizzata vs Implicita {: #realized-vs-implied-volatility }

### 📈 Volatilità Realizzata (Storica) {: #realized-historical-volatility }

Calcolata dai dati di prezzo **passati**. È quella che calcola LibreFolio:

$$
\sigma_{realized} = \text{StdDev}(\text{rendimenti storici})
$$

### 🔮 Volatilità Implicita {: #implied-volatility }

Estratta dai **prezzi delle opzioni** utilizzando il modello di Black-Scholes. Rappresenta l'**aspettativa** del mercato sulla volatilità futura:

$$
C = f(S, K, T, r, \sigma_{implied})
$$

La volatilità implicita è prospettica ma disponibile solo per asset su cui esistono opzioni.

---

## 🔄 Volatilità a Finestra Mobile {: #rolling-window-volatility }

Invece di calcolare un singolo valore di volatilità per l'intero periodo, la **volatilità a finestra mobile** calcola $\sigma$ su una finestra scorrevole (ad esempio, 30 giorni), producendo una serie temporale che mostra come la volatilità evolve:

$$
\sigma_t^{(w)} = \text{StdDev}(R_{t-w+1}, R_{t-w+2}, \ldots, R_t)
$$

Questo è utile per:

- Identificare i **regimi di volatilità** (periodi calmi vs turbolenti)
- Rilevare il **clustering della volatilità** (i giorni ad alta volatilità tendono a seguire giorni ad alta volatilità)
- Impostare dimensioni di posizione dinamiche (ridurre l'esposizione durante i periodi ad alta volatilità)

---

## 📐 Volatilità e Teoria del Portafoglio {: #volatility-and-portfolio-theory }

La volatilità gioca un ruolo centrale nella [Teoria Moderna del Portafoglio](../index.md):

- È il **denominatore** dell'[indice di Sharpe](sharpe-ratio.md)
- Determina l'**ampiezza** delle [Bande di Bollinger](../../technical-analysis/indicators/bollinger-bands.md)
- È l'input chiave per l'ottimizzazione del portafoglio (minimizzare $\sigma_p$ per un $R_p$ obiettivo)
- La [Diversificazione](../../portfolio-theory/diversification.md) riduce la volatilità del portafoglio quando le correlazioni tra asset sono inferiori a 1

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "Volatilità ≠ Rischio"

    La volatilità tratta allo stesso modo i movimenti al rialzo e al ribasso. Un asset che registra frequentemente picchi verso l'alto ha un'elevata volatilità ma può essere molto attraente. Per una misura focalizzata sul ribasso, usa l'[indice di Sortino](sortino-ratio.md) o il [drawdown massimo](max-drawdown.md).

!!! warning "Non normalità"

    I rendimenti finanziari tipicamente presentano:

    - **Code spesse** (eventi più estremi di quanto preveda una distribuzione normale)
    - **Asimmetria negativa** (grandi cali più frequenti dei grandi guadagni)
    - **Clustering della volatilità** (periodi calmi e turbolenti)

    La sola deviazione standard non cattura queste caratteristiche.

---

## 🔗 Correlati {: #related }

- 📐 **[indice di Sharpe](sharpe-ratio.md)** — Usa la volatilità come denominatore del rischio
- 📊 **[indice di Sortino](sortino-ratio.md)** — Variante della volatilità solo al ribasso
- 📏 **[Bande di Bollinger](../../technical-analysis/indicators/bollinger-bands.md)** — Inviluppo di volatilità sui grafici
- 🔀 **[Diversificazione](../../portfolio-theory/diversification.md)** — Ridurre la volatilità del portafoglio
