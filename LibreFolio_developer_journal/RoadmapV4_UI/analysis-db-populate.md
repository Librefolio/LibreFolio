# Analisi: Database Populate Mock Data

**Data**: 2 Febbraio 2026  
**File analizzato**: `backend/test_scripts/test_db/populate_mock_data.py`  
**Linee**: 759

---

## 📊 Riepilogo Dati Creati

| Entità          | Quantità | Note                                             |
|-----------------|----------|--------------------------------------------------|
| Brokers         | 3        | Interactive Brokers, Degiro, Recrowd             |
| Assets          | 7        | 3 stocks, 2 ETFs, 2 crowdfund loans              |
| Asset Providers | 5        | Solo per asset con prezzi (yfinance)             |
| Transactions    | ~15      | Deposits, buys, sells, dividends, interest, fees |
| Price History   | ~80      | Ultimi 30 giorni (esclusi weekend) per 4 asset   |
| FX Rates        | ~80      | Ultimi 30 giorni per 4 coppie                    |
| FX Pair Sources | 6        | Configurazioni ECB                               |

---

## 🏦 Brokers Creati

1. **Interactive Brokers**
    - URL: https://www.interactivebrokers.com
    - Multi-currency (EUR, USD)

2. **Degiro**
    - URL: https://www.degiro.com
    - Solo EUR

3. **Recrowd**
    - URL: https://www.recrowd.com
    - P2P lending, solo EUR

### ❌ Problemi Broker

- **Nessun `brim_plugin_key`**: I broker non hanno associato un plugin BRIM, quindi nella UI non compare l'icona del plugin
- **Nessun `icon_url`**: I broker non hanno favicon configurato

---

## 🔌 BRIM Plugins Disponibili

| Code                 | Name                | Description                                 |
|----------------------|---------------------|---------------------------------------------|
| `broker_ibkr`        | Interactive Brokers | Stocks, ETFs, FX trades                     |
| `broker_degiro`      | DEGIRO              | Multi-language, multi-currency              |
| `broker_directa`     | Directa SIM         | Italian broker, ETF dividends, bond coupons |
| `broker_etoro`       | eToro               | Stocks, CFDs, dividends                     |
| `broker_schwab`      | Charles Schwab      | Stocks, ETFs, dividends                     |
| `broker_coinbase`    | Coinbase            | Crypto buys, sells, staking                 |
| `broker_revolut`     | Revolut             | Stocks, dividends, cash movements           |
| `broker_trading212`  | Trading212          | Stocks, ETFs, dividends                     |
| `broker_freetrade`   | Freetrade           | UK stocks, ETFs                             |
| `broker_finpension`  | Finpension          | Swiss pension fund                          |
| `broker_generic_csv` | Generic CSV         | Auto-detects columns                        |

### Mapping Broker → Plugin

Per i broker esistenti nel populate:

| Broker              | Plugin Consigliato                        |
|---------------------|-------------------------------------------|
| Interactive Brokers | `broker_ibkr`                             |
| Degiro              | `broker_degiro`                           |
| Recrowd             | `broker_generic_csv` (no plugin dedicato) |

---

## 📈 Assets Creati

### Stocks (USD)

1. Apple Inc. (`AAPL`)
2. Microsoft Corporation (`MSFT`)
3. Tesla, Inc. (`TSLA`) - ⚠️ Non ha provider assignment!

### ETFs (EUR)

4. Vanguard FTSE All-World UCITS ETF (`VWCE.DE`)
5. iShares Core S&P 500 UCITS ETF (`SXR8.DE`)

### Crowdfund Loans (EUR)

6. Real Estate Loan - Milano Centro
7. Real Estate Loan - Roma Parioli

### ❌ Problemi Assets

- **Tesla non ha provider**: L'asset TSLA è creato ma non ha `AssetProviderAssignment`
- **Loans non hanno provider**: I crowdfund loans non hanno price history (OK per questo tipo)
- **Mancano ISIN/ticker**: Gli asset non hanno identificatori standardizzati (`isin`, `ticker`)

---

## 📊 Transactions Create

| Tipo     | Quantità | Broker              | Note                   |
|----------|----------|---------------------|------------------------|
| DEPOSIT  | 4        | IB, Degiro, Recrowd | Funding iniziale       |
| BUY      | 6        | Tutti               | Acquisti vari          |
| SELL     | 1        | IB                  | Profit taking AAPL     |
| DIVIDEND | 1        | IB                  | AAPL Q4 dividend       |
| INTEREST | 1        | Recrowd             | Pagamento mensile loan |
| FEE      | 1        | IB                  | Platform fee           |

### ✅ Buona copertura di transaction types

---

## 💱 FX Rates Create

Coppie coperte:

- EUR/USD
- EUR/GBP
- CHF/EUR
- EUR/JPY

**Provider**: ECB

### ❌ Mancanze

- USD/GBP (cross rate)
- AUD, CAD (solo in pair_sources, non in rates)

---

## 🔧 Raccomandazioni di Fix

### 1. Aggiungere `brim_plugin_key` ai Broker (PRIORITÀ ALTA)

```python
brokers = [
    {
        "name": "Interactive Brokers",
        ...
            "brim_plugin_key": "broker_ibkr",
},
{
    "name": "Degiro",
    ...
        "brim_plugin_key": "broker_degiro",
},
{
    "name": "Recrowd",
    ...
        "brim_plugin_key": "broker_generic_csv",
},
]
```

### 2. Aggiungere più Broker per test UI diversificati

Suggerimento: aggiungere broker con diversi plugin BRIM per testare la UI con più varietà:

```python
# Broker aggiuntivi suggeriti
additional_brokers = [
    {
        "name": "Directa SIM",
        "description": "Italian online broker",
        "portal_url": "https://www.directa.it",
        "brim_plugin_key": "broker_directa",
        },
    {
        "name": "eToro",
        "description": "Social trading platform",
        "portal_url": "https://www.etoro.com",
        "brim_plugin_key": "broker_etoro",
        },
    {
        "name": "Coinbase",
        "description": "Cryptocurrency exchange",
        "portal_url": "https://www.coinbase.com",
        "brim_plugin_key": "broker_coinbase",
        },
    ]
```

### 3. Aggiungere ISIN/Ticker agli Assets

```python
assets = [
    {
        "display_name": "Apple Inc.",
        "isin": "US0378331005",
        "ticker": "AAPL",
        ...
        },
    ]
```

### 4. Fix Tesla Provider Assignment

```python
# In populate_asset_provider_assignments - verificare che Tesla sia incluso
provider_configs = [
    ...
    ("Tesla, Inc.", "yfinance", "TSLA", IdentifierType.TICKER, None),
    ]
```

### 5. Verificare che icon_url sia popolato

Il broker dovrebbe avere un `icon_url` popolato automaticamente dal favicon del `portal_url`. Verificare che il meccanismo funzioni.

---

## 🎯 Priorità Fix

| Priorità | Fix                          | Impatto                     |
|----------|------------------------------|-----------------------------|
| **P1**   | Aggiungere `brim_plugin_key` | Gallery mostra icone broker |
| **P1**   | Aggiungere più broker        | Test UI più realistici      |
| P2       | Aggiungere ISIN/ticker       | Ricerca asset funziona      |
| P3       | Fix Tesla provider           | Price history completa      |

---

## 📝 Note Tecniche

- Il file usa `--force` per ricrearne il DB da zero
- I weekend sono esclusi da price history e FX rates
- I dati coprono gli ultimi 30 giorni
- Asset type `CROWDFUND_LOAN` non ha price fetching (corretto)

---

## 🔗 File Correlati

- `backend/test_scripts/test_db_config.py` - Setup test database
- `backend/app/db/models.py` - Definizione modelli
- `backend/app/services/brim_providers/` - Plugin BRIM disponibili
