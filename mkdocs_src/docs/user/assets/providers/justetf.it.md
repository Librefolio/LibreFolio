# <img src="https://www.justetf.com/android-chrome-144x144.png?v2" alt=""> justETF

justETF fornisce dati dettagliati per gli ETF europei, inclusi i prezzi attuali e i dati storici con supporto multi-valuta.

## 📊 Capacità

- ✅ **Prezzo Attuale**: quotazioni gettex in tempo reale (solo EUR)
- ✅ **Storico**: dati storici dei prezzi in EUR, USD, CHF o GBP
- ✅ **Eventi**: può emettere eventi `DIVIDEND` dai dati del grafico quando sono presenti serie di dividendi
- ✅ **Ricerca**: ricerca full-text tra oltre 3000 ETF europei

## 💱 Selezione della Valuta

justETF supporta il recupero dei prezzi in **4 valute**: EUR, USD, CHF, GBP.

Quando cerchi un ETF, i risultati appaiono con le bandiere delle valute:

| Bandiera | Significato |
|------|---------|
| 🇪🇺 | prezzi in Euro |
| 🇺🇸 | prezzi in Dollari USA |
| 🇨🇭 | prezzi in Franchi Svizzeri |
| 🇬🇧 | prezzi in Sterline Britanniche |
| 👑 | valuta NAV nativa del fondo (mostrata accanto alla bandiera) |

!!! note "Conversione Valutaria"

    JustETF esegue la conversione lato server utilizzando i propri tassi di cambio.
    Per le valute non presenti nell'elenco supportato (JPY, SEK, ecc.), utilizza il sistema di conversione valutaria integrato di LibreFolio.

## ⚠️ Limitazioni

!!! warning "Fallback del Prezzo Attuale"

    Il valore attuale prova prima la quotazione gettex in tempo reale in **EUR**.

    Se la quotazione live non è disponibile, LibreFolio ripiega sul `latestQuote` giornaliero dell'API del grafico di performance per **EUR, USD, CHF e GBP**.

    I dati storici restano disponibili per tutte le valute supportate.

## 🔧 Configurazione

- **Identifier**: codice ISIN (es. `IE00BK5BQT80`)
- **Identifier Type**: `ISIN`
- **Parameters**:
 - `currency`: valuta del prezzo — EUR (default), USD, CHF o GBP

## 💡 Esempi

| Asset | ISIN | Valuta Suggerita |
|-------|------|--------------------|
| Vanguard FTSE All-World | `IE00BK5BQT80` | EUR o USD 👑 |
| iShares Core MSCI World | `IE00B4L5Y983` | EUR o USD 👑 |
| Xtrackers MSCI Emerging Markets | `IE00BTJRMP35` | EUR o USD 👑 |

## 📝 Note

- Più indicato per gli ETF con domicilio europeo quotati su justETF
- Utilizza l'ISIN come identificatore primario
- La 👑 nei risultati di ricerca indica la denominazione NAV nativa del fondo — questa è la valuta che il gestore del fondo utilizza internamente, non necessariamente la valuta in cui effettui il trading
