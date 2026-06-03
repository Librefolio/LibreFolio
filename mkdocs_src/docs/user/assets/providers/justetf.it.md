# 📊 Provider justETF

justETF fornisce dati dettagliati per gli ETF europei, inclusi i prezzi attuali e i dati storici con supporto multi-valuta.

## 📊 Capacità

- ✅ **Prezzo Attuale**: Quote gettex in tempo reale (solo EUR)
- ✅ **Storico**: Dati storici dei prezzi in EUR, USD, CHF o GBP
- ✅ **Ricerca**: Ricerca full-text tra più di 3000 ETF europei

## 💱 Selezione della Valuta

justETF supporta il recupero dei prezzi in **4 valute**: EUR, USD, CHF, GBP.

Quando cerchi un ETF, i risultati appaiono con le bandiere della valuta:

| Bandiera | Significato |
|------|---------|
| 🇪🇺 | Prezzi in Euro |
| 🇺🇸 | Prezzi in Dollari USA |
| 🇨🇭 | Prezzi in Franchi Svizzeri |
| 🇬🇧 | Prezzi in Sterline Britanniche |
| 👑 | Valuta NAV nativa del fondo (mostrata accanto alla bandiera) |

!!! note "Conversione Valutaria"

    JustETF esegue la conversione valutaria lato server utilizzando i propri tassi di cambio.
    Per le valute non presenti nell'elenco supportato (JPY, SEK, ecc.), utilizza il sistema di conversione valutaria integrato di LibreFolio.

## ⚠️ Limitazioni

!!! warning "Prezzo Attuale: Solo EUR"

    I prezzi in tempo reale (valore attuale) sono disponibili solo in **EUR** perché provengono dal WebSocket dell'exchange **gettex**, che è un exchange europeo che quota in EUR.

    Per le valute diverse dall'EUR (USD, CHF, GBP):

    - ✅ I dati storici sono disponibili (convertiti da JustETF)
    - ❌ Il prezzo in tempo reale **non** è disponibile — la sincronizzazione dell'asset mostrerà "current value unavailable"

    **Raccomandazione**: Se hai bisogno di prezzi in tempo reale, usa EUR. Per il tracciamento del portafoglio dove i prezzi di chiusura giornalieri sono sufficienti, qualsiasi valuta va bene.

## 🔧 Configurazione

- **Identificatore**: codice ISIN (es. `IE00BK5BQT80`)
- **Tipo Identificatore**: `ISIN`
- **Parametri**:
 - `currency`: Valuta del prezzo — EUR (default), USD, CHF o GBP

## 💡 Esempi

| Asset | ISIN | Valuta Suggerita |
|-------|------|--------------------|
| Vanguard FTSE All-World | `IE00BK5BQT80` | EUR o USD 👑 |
| iShares Core MSCI World | `IE00B4L5Y983` | EUR o USD 👑 |
| Xtrackers MSCI Emerging Markets | `IE00BTJRMP35` | EUR o USD 👑 |

## 📝 Note

- Ideale per ETF domiciliati in Europa quotati su justETF
- Utilizza l'ISIN come identificatore primario
- La 👑 nei risultati di ricerca indica la valuta NAV nativa del fondo — questa è la valuta che il gestore del fondo utilizza internamente, non necessariamente la valuta in cui effettui il trading
