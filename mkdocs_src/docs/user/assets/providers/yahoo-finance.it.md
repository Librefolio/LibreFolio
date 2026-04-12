# 📈 Yahoo Finance Provider

Yahoo Finance è il provider predefinito per azioni, ETF e fondi comuni. Offre la copertura più ampia e supporta la ricerca di asset.

## 📊 Funzionalità

- ✅ **Prezzo Corrente**: Quotazioni in tempo reale o ritardate
- ✅ **Storico**: Dati storici completi dei prezzi
- ✅ **Ricerca**: Ricerca di asset per nome o ticker

## 🔧 Configurazione

- **Identificatore**: Simbolo ticker di Yahoo Finance (es. `AAPL`, `VWCE.DE`, `BTC-USD`)
- **Tipo di identificatore**: `TICKER`
- **Parametri**: Nessuno richiesto

## 💡 Esempi

| Asset | Ticker |
|-------|--------|
| Apple Inc. | `AAPL` |
| Vanguard FTSE All-World (Xetra) | `VWCE.DE` |
| Bitcoin | `BTC-USD` |
| iShares Core S&P 500 (Milan) | `CSSPX.MI` |

## 📝 Note

- Per gli ETF quotati in Europa, aggiungere il suffisso della borsa valori (es. `.DE` per Xetra, `.MI` per Milano, `.AS` per Amsterdam)
- I dati di Yahoo Finance potrebbero avere un ritardo di 15 minuti per alcune borse valori
