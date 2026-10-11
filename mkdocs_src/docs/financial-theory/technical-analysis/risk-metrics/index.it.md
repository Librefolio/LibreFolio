# 📊 Metriche di rischio

Le metriche di rischio forniscono **misure quantitative** del rischio di portafoglio. Ogni metrica cattura un aspetto diverso dell'incertezza e nessuna singola metrica racconta l'intera storia. Usare più metriche insieme offre una visione completa del rischio di portafoglio.

---

## 🧭 Le quattro domande {: #the-four-questions }

Ogni pagina di questa sezione esiste per rispondere a una delle quattro domande. Una metrica si guadagna il suo posto rispondendo a una di esse; due pagine trasversali spiegano come vengono calcolate le risposte e quanto ci si può fidare di esse. Le due tabelle più avanti confrontano fianco a fianco le quattro più note di queste metriche e suggeriscono quando ricorrere a ciascuna.

### 📉 Quanto può fare male? {: #how-much-can-it-hurt }

| Metrica | A cosa risponde |
|--------|-----------------|
| **[Drawdown massimo](max-drawdown.md)** | Il maggiore calo da picco a minimo prima di un nuovo picco — la perdita peggiore che un investitore avrebbe effettivamente vissuto. |
| **[Drawdown attuale](current-drawdown.md)** | Quanto un portafoglio si trova attualmente al di sotto del proprio massimo storico, in contrapposizione al peggior calo mai subito. |
| **[Drawdown a rischio](drawdown-at-risk.md)** | Il drawdown a rischio applica l'idea del quantile ai drawdown anziché ai rendimenti: è la profondità di drawdown che non dovrebbe essere superata a un livello di confidenza scelto. |
| **[Drawdown a rischio condizionale](conditional-drawdown-at-risk.md)** | Il drawdown a rischio condizionale calcola la media dei drawdown che hanno effettivamente superato la soglia di drawdown a rischio, rispondendo a quanto profondo diventa il calo una volta superato quel punto. |
| **[Indice di Ulcer](ulcer-index.md)** | L'indice di Ulcer combina la profondità della caduta di un portafoglio con la durata della permanenza in ribasso, perciò un calo lieve ma persistente può ottenere un punteggio peggiore di uno brusco che si riprende rapidamente. |
| **[Value at Risk](value-at-risk.md)** | Una domanda deliberatamente ristretta: su un dato orizzonte e a un livello di confidenza scelto, qual è la perdita che non dovrebbe essere superata? |
| **[VaR condizionale](conditional-value-at-risk.md)** | Subentra esattamente dove si ferma il Value at Risk: la perdita media nei casi in cui la soglia del Value at Risk è stata effettivamente superata. |
| **[Peggior realizzazione](worst-realization.md)** | Il rendimento di singolo periodo meno favorevole effettivamente osservato nella storia disponibile — un fatto osservato anziché una stima. |

*Le prime cinque leggono il **percorso** che il portafoglio ha effettivamente seguito; le ultime tre leggono la **distribuzione** dei suoi rendimenti. Se si cambia l'ordine di quei rendimenti, le ultime tre restano invariate, mentre le prime cinque possono cambiare completamente.*

### 🧩 Sono diversificato? {: #am-i-diversified }

| Metrica | A cosa risponde |
|--------|-----------------|
| **[Correlazione](correlation.md)** | Come si muovono le posizioni l'una rispetto all'altra, ed è per questo che la diversificazione dipende da come le posizioni si comportano insieme, non da quante ce ne siano. |
| **[Contributo al rischio](risk-contribution.md)** | Come il rischio totale di portafoglio viene attribuito alle singole posizioni — quanto ciascuna posizione contribuisce non è generalmente la stessa cosa di quanto rappresenta nel portafoglio. |
| **[Concentrazione](concentration.md)** | Quanto il peso di un portafoglio è concentrato in poche posizioni, fornendo una lettura che un semplice conteggio delle posizioni non può dare. |

### ⚖️ Sono pagato per il rischio? {: #am-i-paid-for-the-risk }

| Metrica | A cosa risponde |
|--------|-----------------|
| **[Volatilità](volatility.md)** | La dispersione dei rendimenti — quanto oscilla il valore, e l'elemento costitutivo di quasi ogni altra metrica di rischio. |
| **[Indice di Sharpe](sharpe-ratio.md)** | Quanto rendimento in eccesso è stato guadagnato per unità di volatilità totale. |
| **[Indice di Sortino](sortino-ratio.md)** | Lo stesso confronto, con solo la volatilità al ribasso al denominatore. |
| **[Beta e rendimento attivo](beta-active-return.md)** | Quanto fortemente un portafoglio tende a seguire il suo benchmark, e quale parte del risultato il benchmark non spiega. |
| **[Selezione del benchmark](benchmark-selection.md)** | Ogni cifra relativa al benchmark eredita il benchmark rispetto al quale è stata misurata, quindi la scelta del confronto è essa stessa parte del verdetto. |

### 🎲 E se…? {: #what-if }

| Metrica | A cosa risponde |
|--------|-----------------|
| **[Replay storico](historical-replay.md)** | Cosa farebbero i movimenti di un reale episodio passato al portafoglio così come è composto oggi. |
| **[Shock ipotetico](hypothetical-shock.md)** | Sostituisce l'episodio storico con uno scelto, il che rende possibile testare uno scenario che la storia disponibile non ha mai contenuto. |
| **[Modalità di simulazione](simulation-modes.md)** | Ogni modalità si basa su assunzioni proprie, e tali assunzioni determinano tanto ciò che i suoi risultati non possono dire quanto ciò che possono dire. |

### 🔧 Metodo {: #method }

| Pagina | A cosa risponde |
|------|-----------------|
| **[Annualizzazione osservata](observed-annualization.md)** | Come una cifra per periodo diventa annuale, con il numero di periodi in un anno misurato dai dati invece che assunto in anticipo. |
| **[Qualità dei dati](data-quality.md)** | Una cifra di rischio è affidabile solo quanto le osservazioni che vi stanno dietro, quindi la quantità e la freschezza dei dati sottostanti fanno parte della lettura del risultato. |

---

## 📋 Panoramica comparativa {: #comparative-overview }

| Metrica | Cosa misura | Formula | Intervallo | Dettagli |
|--------|-----------------|---------|-------|---------|
| **[Indice di Sharpe](sharpe-ratio.md)** | Rendimento corretto per il rischio (volatilità totale) | $\frac{R_p - R_f}{\sigma_p}$ | $(-\infty, +\infty)$ | [📖](sharpe-ratio.md) |
| **[Indice di Sortino](sortino-ratio.md)** | Rendimento corretto per il rischio (solo ribasso) | $\frac{R_p - R_f}{\sigma_d}$ | $(-\infty, +\infty)$ | [📖](sortino-ratio.md) |
| **[Drawdown massimo](max-drawdown.md)** | Peggior calo da picco a minimo | $\frac{Trough - Peak}{Peak}$ | $[-100\%, 0\%]$ | [📖](max-drawdown.md) |
| **[Volatilità](volatility.md)** | Dispersione dei rendimenti | $\sigma = \sqrt{\text{Var}(R)}$ | $[0, +\infty)$ | [📖](volatility.md) |

---

## 🔑 Quando usare ciascuna metrica {: #when-to-use-each-metric }

| Scenario | Metrica migliore | Perché |
|----------|-------------|-----|
| Confrontare due fondi | **Indice di Sharpe** | Normalizza il rendimento per il rischio totale |
| Distribuzioni dei rendimenti asimmetriche | **Indice di Sortino** | Penalizza solo la volatilità al ribasso |
| Pianificazione dello scenario peggiore | **Drawdown massimo** | Mostra il punto di massimo dolore |
| Valutazione generale del rischio | **Volatilità** | Fondamento per tutte le altre metriche |
| Ottimizzazione del portafoglio | **Tutte e quattro** | Ciascuna cattura una dimensione diversa |

---

## ⚠️ Errori comuni {: #common-pitfalls }

!!! warning "Limitazioni"

    - **Le metriche storiche ≠ rischio futuro**: La volatilità passata potrebbe non predire quella futura
    - **Assunzione di distribuzione normale**: Sharpe e Sortino assumono che i rendimenti siano approssimativamente normali; i rendimenti finanziari hanno code spesse
    - **Sensibilità alla finestra di osservazione**: Le metriche cambiano in modo significativo a seconda dell'intervallo temporale
    - **Dipendenza dal benchmark**: Sharpe e Sortino dipendono dal tasso privo di rischio, che cambia nel tempo

---

## 🔗 Correlati {: #related }

- 🔀 **[Diversificazione](../../portfolio-theory/diversification.md)** — Come funziona matematicamente la riduzione del rischio
- ⚖️ **[Allocazione degli asset](../../portfolio-theory/asset-allocation.md)** — Usare le metriche di rischio per guidare l'allocazione
- 📈 **[Rendimenti e tassi di crescita](../../fundamentals/returns.md)** — Il lato "rendimento" del rischio-rendimento
