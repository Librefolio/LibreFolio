# 📈 Yahoo Finance Provider

Yahoo Finance is the default provider for stocks, ETFs, and mutual funds. It offers the widest coverage and supports asset search.

## 📊 Capabilities

- ✅ **Current Price**: Real-time or delayed quotes
- ✅ **History**: Full historical price data
- ✅ **Search**: Search assets by name or ticker

## 🔧 Configuration

- **Identifier**: Yahoo Finance ticker symbol (e.g., `AAPL`, `VWCE.DE`, `BTC-USD`)
- **Identifier Type**: `TICKER`
- **Parameters**: None required

## 💡 Examples

| Asset | Ticker |
|-------|--------|
| Apple Inc. | `AAPL` |
| Vanguard FTSE All-World (Xetra) | `VWCE.DE` |
| Bitcoin | `BTC-USD` |
| iShares Core S&P 500 (Milan) | `CSSPX.MI` |

## 📝 Notes

- For European-listed ETFs, append the exchange suffix (e.g., `.DE` for Xetra, `.MI` for Milan, `.AS` for Amsterdam)
- Yahoo Finance data may have a 15-minute delay for some exchanges
