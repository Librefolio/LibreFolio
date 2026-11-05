# <img src="https://www.justetf.com/android-chrome-144x144.png?v2" alt=""> justETF

justETF quota gli ETF europei tramite il loro ISIN, in euro, dollari statunitensi, franchi svizzeri o sterline britanniche.
Fornisce inoltre la descrizione di ciascun fondo e la sua distribuzione geografica e settoriale.

## 🔍 Cosa offre

- **Prezzo corrente**: in EUR, il prezzo live dalla borsa gettex; quando non è disponibile — e
  sempre in USD, CHF e GBP — l'ultimo prezzo giornaliero.
- **Storico**: i prezzi di chiusura giornalieri nella valuta che scegli.
- **Dividendi**: le distribuzioni mostrate nel grafico del fondo diventano eventi di dividendo.
- **Ricerca**: per nome, ticker, WKN o ISIN, tra gli ETF quotati su justETF.
- **Dettagli**: una descrizione con il TER e la politica di distribuzione, la distribuzione geografica e settoriale, l'ISIN e il ticker.

## ✏️ Configuralo

**Ricerca online** lo configura per te. Manualmente, in **Assegnazione provider**:

1. Scegli **JustETF** come **Provider**.
2. Digita l'**ISIN** del fondo, per esempio `IE00B4L5Y983` (iShares Core MSCI World).
3. In `currency`, scegli `EUR` (il valore predefinito), `USD`, `CHF` o `GBP`: ogni prezzo dell'asset è
   memorizzato in quella valuta.

### 💱 Scegli la valuta nella ricerca {: #search-currency }

Ogni ETF compare quattro volte nei risultati, una per valuta: 🇪🇺 EUR, 🇺🇸 USD, 🇨🇭 CHF e
🇬🇧 GBP — a meno che tu non abbia scelto una [valuta preferita](#preferred-currency). 👑 contrassegna la valuta
propria del fondo, quella in cui è calcolato il suo NAV — non necessariamente quella in cui fai trading. Una riga
in fondo ai risultati lo segnala ogni volta che un risultato mostra 👑.

justETF converte i prezzi in USD, CHF e GBP con i propri tassi di cambio. La tua valuta di
rendicontazione è un'altra? Scegli una qualsiasi delle quattro: LibreFolio converte con i propri
[tassi di cambio](../../fx/index.md).

### ⭐ La tua valuta preferita {: #preferred-currency }

Scegli sempre la stessa valuta? Impostala una volta come **Valuta preferita**, sotto **JustETF** in
**Impostazioni › Plugin**, oppure con **Configura** accanto al provider nella finestra di dialogo dell'asset. Le tue
ricerche mostreranno quindi ogni ETF una sola volta, in quella valuta, con 👑 solo sui fondi calcolati in quella valuta.
L'opzione **Tutte le valute**, quella predefinita, mostra tutte e quattro.

È un'impostazione personale: cambia solo le tue ricerche, mai un prezzo o un asset che già
possiedi. Vedi [Impostazioni plugin](../../settings/plugins.md#search-preferences).

## ⚠️ Limiti

- Solo ISIN: per un ticker, usa [Yahoo Finance](yahoo-finance.md).
- Solo il prezzo in EUR è live.
- LibreFolio legge il sito web di justETF: una modifica da parte loro può bloccare i prezzi finché LibreFolio
  non viene aggiornato.

## 🔗 Correlati

- 🔌 **[Provider asset](index.md)** — Confronta i provider
- 🧩 **[Impostazioni plugin](../../settings/plugins.md)** — La tua valuta preferita nella ricerca
- 🛠️ **Per gli sviluppatori: [JustETF Provider](../../../developer/backend/assets/provider_justetf.md)** — Quotazioni live, grafici e caching
