# <img src="https://www.justetf.com/android-chrome-144x144.png?v2" alt=""> justETF

justETF fornisce i prezzi degli ETF europei tramite il loro ISIN, in euro, dollari statunitensi, franchi svizzeri o sterline britanniche.
Include anche la descrizione di ciascun fondo e le sue distribuzioni geografiche e settoriali.

## 🔍 Cosa offre

- **Prezzo attuale**: in EUR, il prezzo live dalla borsa gettex; quando non è disponibile — e
  sempre in USD, CHF e GBP — l'ultimo prezzo giornaliero.
- **Storico**: prezzi di chiusura giornalieri nella valuta scelta.
- **Dividendi**: le distribuzioni mostrate nel grafico del fondo diventano eventi di dividendo.
- **Ricerca**: per nome, ticker, WKN o ISIN, tra gli ETF elencati su justETF.
- **Dettagli**: una descrizione con il TER e la politica di distribuzione, le distribuzioni geografiche e settoriali,
  l'ISIN e il ticker.

## ✏️ Configuralo

**Ricerca online** lo configura per te. Manualmente, in **Assegnazione provider**:

1. Scegli **JustETF** come **Provider**.
2. Digita l'**ISIN** del fondo, per esempio `IE00B4L5Y983` (iShares Core MSCI World).
3. In `currency`, scegli `EUR` (predefinita), `USD`, `CHF` o `GBP`: ogni prezzo dell'asset viene
   memorizzato in quella valuta.

### 💱 Scegli la valuta nella ricerca

Ogni ETF compare quattro volte nei risultati, una per valuta: 🇪🇺 EUR, 🇺🇸 USD, 🇨🇭 CHF e
🇬🇧 GBP. 👑 contrassegna la valuta propria del fondo, quella in cui viene calcolato il suo NAV — non necessariamente quella
in cui fai trading.

justETF converte i prezzi in USD, CHF e GBP con i propri tassi di cambio. La tua valuta di
rendicontazione è un'altra? Scegli una qualsiasi delle quattro: LibreFolio converte con i propri
[tassi di cambio](../../fx/index.md).

## ⚠️ Limiti

- Solo ISIN: per un ticker, usa [Yahoo Finance](yahoo-finance.md).
- Solo il prezzo in EUR è live.
- LibreFolio legge il sito web di justETF: una modifica da parte loro può interrompere i prezzi finché LibreFolio
  non viene aggiornato.

## 🔗 Correlati

- 🔌 **[Provider asset](index.md)** — Confronta i provider
- 🛠️ **Per sviluppatori: [Provider JustETF](../../../developer/backend/assets/provider_justetf.md)** — Quotazioni live, grafici e caching
