# <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" alt=""> Yahoo Finance

Yahoo Finance copre azioni, ETF, fondi, indici e criptovalute dalle borse di tutto il mondo e puoi
cercarlo per nome o ticker.

## 🔍 Cosa offre

- **Prezzo attuale**: il prezzo più recente riportato da Yahoo per il ticker — su alcune borse è
  ritardato.
- **Storico**: dati giornalieri di apertura, massimo, minimo, chiusura e volume, fino a dove arriva Yahoo.
- **Dividendi e split**: registrati come eventi dell'asset.
- **Ricerca**: per nome o ticker.
- **Dettagli**: tipo, valuta, descrizione, settore, ticker e, quando Yahoo lo ha, l'ISIN.

## ✏️ Configurazione

**Ricerca online** lo configura per te. Manualmente, in **Assegnazione provider**, scegli
**Yahoo Finance**, imposta **Tipo di identificatore** su **TICKER** e digita il ticker come **Identificatore**.
Non c'è altro da compilare.

| Asset | Ticker |
|-------|--------|
| Apple Inc. | `AAPL` |
| Vanguard FTSE All-World (Xetra) | `VWCE.DE` |
| iShares Core S&P 500 (Milano) | `CSSPX.MI` |
| Bitcoin in dollari statunitensi | `BTC-USD` |

Fuori dagli Stati Uniti, aggiungi il suffisso della borsa al ticker: `.DE` per Xetra, `.MI` per Milano, `.AS` per
Amsterdam.

## ⚠️ Limiti

- **ISIN** funziona anche come **Tipo di identificatore**, ma solo quando Yahoo riesce ad associarlo a un ticker: preferisci
  il ticker.
- Yahoo può limitare la frequenza delle richieste e alcuni ticker presentano giorni senza dati.

## 🔗 Correlati

- 🔌 **[Provider asset](index.md)** — Confronta i provider
- 🛠️ **Per sviluppatori: [Yahoo Finance Provider](../../../developer/backend/assets/provider_yahoo_finance.md)** — Richieste, caching ed eventi
