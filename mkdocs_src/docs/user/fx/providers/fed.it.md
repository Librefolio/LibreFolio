# <img src="https://fred.stlouisfed.org/favicon.ico" alt=""> Federal Reserve (FED)

Il provider **Federal Reserve (FRED)** recupera i dati dei tassi di cambio dal database Federal Reserve Economic Data (FRED). È la fonte primaria o fallback ideale per i portafogli incentrati sul Dollaro statunitense.

## 📊 Funzionalità

- ✅ **Prezzo Corrente**: tasso di riferimento aggiornato giornalmente
- ✅ **Storico**: tassi storici estesi (dipende dalla serie della valuta)
- ❌ **Ricerca**: nessuna ricerca asset (solo tassi FX)

## 🔧 Specifiche

- **Valuta di Base**: USD 🇺🇸
- **Frequenza di Aggiornamento**: un tasso per giorno lavorativo statunitense, pubblicato una volta alla settimana (vedi sotto)
- **API Key**: non richiesta (recuperata tramite download pubblico di file CSV)

## 💰 Valute Supportate

FRED fornisce tassi per 23 valute:

- **Valute G10**: EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CAD 🇨🇦, CHF 🇨🇭, AUD 🇦🇺, NZD 🇳🇿, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰
- **Emergenti e Regionali**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦, TWD 🇹🇼, THB 🇹🇭, MYR 🇲🇾, LKR 🇱🇰, VES 🇻🇪

## 📝 Note Importanti

- **Formato delle quotazioni**: FRED quota alcune valute come "USD per unità di valuta estera" (es. EUR, GBP) e altre come "valuta estera per USD" (es. JPY, CAD). LibreFolio legge ogni serie nella sua direzione e la normalizza per garantire la coerenza nel tuo database.
- **Pubblicazione settimanale**: i tassi FED sono giornalieri, un valore per ogni giorno lavorativo statunitense, ma la Federal Reserve li pubblica una volta alla settimana, il lunedì, con i giorni della settimana precedente. L'ultimo tasso FED può quindi avere fino a circa 10 giorni, e una catena di conversione con una gamba FED non ha tasso per i giorni più recenti fino alla pubblicazione successiva. Le route che usano FED lo segnalano con una nota ℹ️.
- **VES (bolívar venezuelano)**: disponibile dal 4 ottobre 2021, giorno dell'ultima ridenominazione. I valori FRED precedenti sono in unità di bolívar più vecchie e non vengono usati.
- **Festività**: nessun tasso viene pubblicato durante le festività federali statunitensi (come il Giorno del Ringraziamento, il Giorno dell'Indipendenza, ecc.) o nei fine settimana.
