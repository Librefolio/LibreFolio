# Analysis: DB Populate Mock Data

**Data**: 3 Febbraio 2026  
**Status**: ✅ COMPLETATO  
**File analizzato**: `backend/test_scripts/test_db/populate_mock_data.py`

---

## 📊 Riepilogo Dati Creati (Aggiornato)

| Entità           | Quantità | Note                                |
|------------------|----------|-------------------------------------|
| Brokers          | 6        | Con `brim_plugin_key` assegnato     |
| BrokerUserAccess | 6        | Admin = OWNER di tutti              |
| Assets           | 9        | Stocks, ETFs, Crypto, Loans         |
| Asset Providers  | 7        | yfinance per tutti i prezzabili     |
| Transactions     | 24       | Depositi, Buy, Sell, Dividendi, Fee |
| Price History    | ~154     | 30 giorni per 7 asset               |
| FX Rates         | 88       | 4 coppie x 22 giorni                |
| FX Pair Sources  | 6        | ECB come provider                   |

---

## ✅ Fix Completati

### 1. BrokerUserAccess ✅ NUOVO

Aggiunta funzione `populate_broker_user_access()` che:

- Associa tutti i broker all'utente `e2e_test_admin` come OWNER
- Se non esiste nessun utente, crea `e2e_test_admin` automaticamente
- Garantisce che la pagina brokers mostri i dati nella gallery

### 2. BRIM Plugin Keys ✅

Tutti i broker hanno ora `brim_plugin_key`:

| Broker              | Plugin               |
|---------------------|----------------------|
| Interactive Brokers | `broker_ibkr`        |
| DEGIRO              | `broker_degiro`      |
| Directa SIM         | `broker_directa`     |
| eToro               | `broker_etoro`       |
| Coinbase            | `broker_coinbase`    |
| Recrowd             | `broker_generic_csv` |

### 3. Nuovi Broker Aggiunti ✅

- Directa SIM (italiano)
- eToro (social trading)
- Coinbase (crypto)

### 4. Nuovi Asset Aggiunti ✅

- Bitcoin (BTC-USD)
- Ethereum (ETH-USD)
- Tesla, Inc. (TSLA)

### 5. Transazioni per Nuovi Broker ✅

Aggiunte transazioni di test per:

- Directa: Deposito + Buy Tesla
- eToro: Deposito + Buy Apple
- Coinbase: Deposito + Buy BTC + Buy ETH + Staking reward

### 6. Price History per Nuovi Asset ✅

- Tesla: 22 price points (skip weekends)
- Bitcoin: 30 price points (crypto trades 24/7)
- Ethereum: 30 price points (crypto trades 24/7)

---

## 🔗 BRIM Plugins Disponibili (Riferimento)

```json
[
  {"code": "broker_finpension", "name": "Finpension"},
  {"code": "broker_coinbase", "name": "Coinbase"},
  {"code": "broker_revolut", "name": "Revolut"},
  {"code": "broker_generic_csv", "name": "Generic CSV"},
  {"code": "broker_ibkr", "name": "Interactive Brokers"},
  {"code": "broker_freetrade", "name": "Freetrade"},
  {"code": "broker_schwab", "name": "Charles Schwab"},
  {"code": "broker_degiro", "name": "DEGIRO"},
  {"code": "broker_etoro", "name": "eToro"},
  {"code": "broker_directa", "name": "Directa SIM"},
  {"code": "broker_trading212", "name": "Trading212"}
]
```

---

## 🎯 Priorità Fix (Tutte Completate)

| Priorità | Fix                           | Status |
|----------|-------------------------------|--------|
| **P1**   | Aggiungere `BrokerUserAccess` | ✅      |
| **P1**   | Aggiungere `brim_plugin_key`  | ✅      |
| **P1**   | Aggiungere più broker         | ✅      |
| P2       | Aggiungere crypto assets      | ✅      |
| P2       | Fix price history crypto      | ✅      |

---

## 📝 Note Tecniche

- Il file usa `--force` per ricrearne il DB da zero
- I weekend sono esclusi da price history per stocks (non per crypto)
- I dati coprono gli ultimi 30 giorni
- Asset type `CROWDFUND_LOAN` non ha price fetching (corretto)
- Gallery usa `TEST_ADMIN` per vedere i broker

---

## 🔗 File Correlati

- `backend/test_scripts/test_db_config.py` - Setup test database
- `backend/app/db/models.py` - Definizione modelli
- `backend/app/services/brim_providers/` - Plugin BRIM disponibili
- `frontend/e2e/gallery.spec.ts` - Usa `TEST_ADMIN` dopo db populate
