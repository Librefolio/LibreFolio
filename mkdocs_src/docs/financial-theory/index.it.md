# 📚 Teoria Finanziaria

Questa sezione documenta i modelli finanziari, le convenzioni e le definizioni utilizzate in tutto LibreFolio.

## 📖 Panoramica

I calcoli finanziari accurati sono fondamentali per un tracker di portafoglio. LibreFolio implementa convenzioni finanziarie standard per garantire la coerenza con i report dei broker e i dati reali. Questa sezione è organizzata in quattro aree tematiche.

## 🗺️ Mappa Concettuale

### 🏦 [Strumenti](instruments/index.md)

I mattoni di ogni portafoglio:

- **[Tipi di Asset](instruments/asset-types/index.md)** — Azioni, ETF, Obbligazioni, Crypto, Immobiliare, Indici
- **[Tipi di Transazione](instruments/transaction-types/index.md)** — Acquisto/Vendita, Deposito/Prelievo, Dividendo, Commissione, Interesse, Trasferimento
- **[Eventi dell'Asset](instruments/asset-events/index.md)** — Dividendo, Interesse, Split, Aggiustamento del Prezzo, Liquidazione alla scadenza

### 📊 [Analisi Tecnica](technical-analysis/index.md)

Overlay di grafici basati sui dati e curve di riferimento matematiche:

- **[Indicatori](technical-analysis/indicators/index.md)** — EMA, MACD, RSI, Bollinger Bands
- **[Benchmark Sintetici](technical-analysis/synthetic-benchmarks/index.md)** — Crescita Lineare, Crescita Composta, Onda Sinusoidale

### 📐 [Fondamenti](fundamentals/index.md)

Concetti finanziari di base:

- **[Convenzioni di Conteggio dei Giorni](fundamentals/day-count.md)** — ACT/365, ACT/360, 30/360, ACT/ACT
- **[Rendimenti e Tassi di Crescita](fundamentals/returns.md)** — Rendimenti Semplici vs Logaritmici, CAGR, annualizzazione
- **[Tassazione](fundamentals/taxation.md)** — Plusvalenze, differimento fiscale, Acc vs Dist

### 📈 [Teoria di Portafoglio](portfolio-theory/index.md)

Teoria Moderna di Portafoglio e gestione del rischio:

- **[Diversificazione](portfolio-theory/diversification.md)** — Correlazione, rischio sistematico vs idiosincratico
- **[Allocazione degli Asset](portfolio-theory/asset-allocation.md)** — Strategica, tattica, glide path, ribilanciamento
- **[Metriche di Rischio](technical-analysis/risk-metrics/index.md)** — Sharpe, Sortino, Max Drawdown, Volatilità
