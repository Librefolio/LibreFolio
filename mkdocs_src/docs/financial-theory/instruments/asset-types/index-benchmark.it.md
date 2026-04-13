# ![](../../../static/icons/asset-types/other.png){: width="32" style="vertical-align: middle;" } Indice & Benchmark

Un **indice** è una misura statistica di una sezione del mercato finanziario. Traccia l'andamento di un gruppo di asset e funge da **benchmark** rispetto al quale gli investitori misurano la performance del proprio portafoglio.

---

## 🔑 Caratteristiche Principali

| Proprietà | Dettaglio |
|----------|--------|
| **Scambiabile?** | Non direttamente — ma ETF e futures tracciano gli indici |
| **Esempi** | S&P 500, MSCI World, FTSE 100, DAX, Nikkei 225 |
| **Uso in LibreFolio** | Riferimento per il segnale [Confronto Asset](../../../user/assets/detail/signals.md) |
| **Prezzo** | Calcolato in base ai pesi dei componenti, non scambiato in borsa |

---

## 📊 Come Vengono Costruiti gli Indici

### 📈 Metodi di Ponderazione

| Metodo | Formula | Esempio |
|--------|---------|---------|
| **Ponderazione per capitalizzazione** | Peso ∝ capitalizzazione di mercato dell'azienda | S&P 500, MSCI World |
| **Ponderazione per prezzo** | Peso ∝ prezzo dell'azione | Dow Jones, Nikkei 225 |
| **Equiponderato** | Tutti i componenti hanno lo stesso peso | S&P 500 Equal Weight |

### 🔄 Ribilanciamento

Gli indici vengono ribilanciati periodicamente: i componenti vengono aggiunti, rimossi o riponderati. Ciò avviene tipicamente su base trimestrale. Gli ETF che tracciano l'indice devono adeguare le proprie posizioni di conseguenza.

---

## 📐 Utilizzo dei Benchmark in LibreFolio

LibreFolio offre due tipi di benchmark:

### 📊 Benchmark Reali (Confronto Asset)

Confronta il grafico del tuo asset con un altro asset reale (ad es., confronta la tua azione con un ETF S&P 500). Questo utilizza l'overlay del segnale **Confronto Asset**.

### 🎯 Benchmark Sintetici

Curve di riferimento matematiche che rispondono alla domanda "cosa succederebbe se il mio asset crescesse del X% all'anno?":

- **[Crescita Lineare](../../technical-analysis/synthetic-benchmarks/linear.md)** — Modello a interesse semplice
- **[Crescita Composta](../../technical-analysis/synthetic-benchmarks/compound.md)** — Modello a interesse composto
- **[Onda Sinusoidale](../../technical-analysis/synthetic-benchmarks/sine-wave.md)** — Riferimento ciclico per la stagionalità

---

## 🔗 Correlati

- 📊 **[ETF](etfs.md)** — Strumenti che tracciano gli indici
- 🎯 **[Benchmark Sintetici](../../technical-analysis/synthetic-benchmarks/index.md)** — Curve di riferimento matematiche
- 📈 **[Rendimenti e Tassi di Crescita](../../fundamentals/returns.md)** — Misurazione della performance rispetto al benchmark
