# 🔀 Diversificazione

La diversificazione è la strategia di gestione del rischio più fondamentale: combinando asset che non si muovono in perfetta sincronia, un investitore può **ridurre la volatilità del portafoglio** senza necessariamente ridurre il rendimento atteso.

---

## 📐 La Matematica

### 📊 Varianza di un Portafoglio a Due Asset

Per un portafoglio composto da due asset con pesi $w_1$ e $w_2 = 1 - w_1$:

$$
\sigma_p^2 = w_1^2 \sigma_1^2 + w_2^2 \sigma_2^2 + 2 w_1 w_2 \sigma_1 \sigma_2 \rho_{12}
$$

dove:

- $\sigma_1, \sigma_2$ sono le volatilità dei singoli asset
- $\rho_{12}$ è il **coefficiente di correlazione** ($-1 \leq \rho \leq +1$)

La magia della diversificazione risiede nel **termine incrociato**: quando $\rho_{12} < 1$, la varianza del portafoglio è **inferiore** alla media ponderata delle varianze individuali.

### 🔑 Effetti della Correlazione

| Correlazione $\rho$ | Effetto | Esempio |
|---|---|---|
| $+1$ | Nessun beneficio di diversificazione — gli asset si muovono identicamente | Due ETF S&P 500 |
| $0$ | Riduzione significativa della varianza | Azioni vs Oro |
| $-1$ | Copertura perfetta — la varianza può raggiungere lo zero | Posizione long su azione + opzione put |

### 📈 Generalizzazione a N-Asset

Per $N$ asset:

$$
\sigma_p^2 = \sum_{i=1}^{N} \sum_{j=1}^{N} w_i w_j \sigma_i \sigma_j \rho_{ij}
$$

All'aumentare di $N$, il contributo delle varianze individuali diminuisce (proporzionalmente a $1/N$), ma il contributo delle covarianze rimane. Questo porta al concetto di **rischio sistematico**.

---

## 🎯 Rischio Sistematico vs Rischio Idiosincratico

### 📊 Rischio Idiosincratico (Diversificabile)

Rischio specifico di una singola azienda o asset. Esempi:

- Dimissioni del CEO
- Richiamo di un prodotto
- Scadenza di un brevetto

Questo rischio **può essere annullato tramite la diversificazione** mantenendo molte posizioni. Con circa 30 azioni non correlate, il rischio idiosincratico tende a zero.

### 🌍 Rischio Sistematico (Non Diversificabile)

Rischio che colpisce l'intero mercato. Esempi:

- Variazioni dei tassi di interesse
- Recessioni
- Pandemie
- Eventi geopolitici

Questo rischio **non può essere eliminato** attraverso la diversificazione. È il rischio per il quale gli investitori sono remunerati — la base del Capital Asset Pricing Model (CAPM).

$$
\sigma_{portfolio}^2 = \underbrace{\sigma_{systematic}^2}_{\text{non eliminabile}} + \underbrace{\sigma_{idiosyncratic}^2}_{\xrightarrow{N \to \infty} 0}
$$

---

## ⚠️ Insidie della Diversificazione

!!! warning "Instabilità della correlazione"

    Le correlazioni **non sono costanti** — tendono ad aumentare durante le crisi di mercato (proprio quando la diversificazione è più necessaria). Questo fenomeno, chiamato **collasso della correlazione**, significa che la diversificazione offre meno protezione durante eventi estremi rispetto a quanto suggerito dai dati storici.

!!! info "Sovra-diversificazione"

    Oltre un certo punto, aggiungere altri asset aumenta la complessità e i costi (commissioni di transazione, complessità fiscale) senza ridurre significativamente il rischio. Il punto di equilibrio per la maggior parte degli investitori è tra le 20 e le 40 posizioni distribuite tra diverse classi di asset e aree geografiche.

---

## 🔗 Correlati

- ⚖️ **[Asset Allocation](asset-allocation.md)** — Come scegliere l'allocazione del portafoglio
- 📊 **[Volatilità](risk-metrics/volatility.md)** — Misurare il rischio che la diversificazione riduce
- 📈 **[Max Drawdown](risk-metrics/max-drawdown.md)** — La metrica dello scenario peggiore
