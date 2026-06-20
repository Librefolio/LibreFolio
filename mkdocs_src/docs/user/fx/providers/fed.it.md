# <img src="https://fred.stlouisfed.org/favicon.ico" alt=""> Federal Reserve (FED)

Il provider **Federal Reserve (FRED)** recupera i dati dei tassi di cambio dal database Federal Reserve Economic Data (FRED). È la fonte primaria o fallback ideale per i portafogli incentrati sul Dollaro statunitense.

## 📊 Funzionalità

- ✅ **Prezzo Corrente**: tasso di riferimento aggiornato giornalmente
- ✅ **Storico**: tassi storici estesi (dipende dalla serie della valuta)
- ❌ **Ricerca**: nessuna ricerca asset (solo tassi FX)

## 🔧 Specifiche

- **Valuta di Base**: USD 🇺🇸
- **Frequenza di Aggiornamento**: giornaliera nei giorni lavorativi statunitensi
- **API Key**: non richiesta (recuperata tramite download pubblico di file CSV)

## 💰 Valute Supportate

FRED fornisce tassi per circa 20 valute principali, tra cui:

- **Valute G10**: EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CAD 🇨🇦, CHF 🇨🇭, AUD 🇦🇺, NZD 🇳🇿, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰
- **Emergenti e Regionali**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦, TWD 🇹🇼, THB 🇹🇭

## 📝 Note Importanti

- **Formato delle quotazioni**: FRED quota alcune valute come "USD per unità di valuta estera" (es. EUR, GBP) e altre come "valuta estera per USD" (es. JPY, CAD). LibreFolio inverte e normalizza automaticamente questi tassi per garantire la coerenza nel tuo database.
- **Festività**: nessun tasso viene pubblicato durante le festività federali statunitensi (come il Giorno del Ringraziamento, il Giorno dell'Indipendenza, ecc.) o nei fine settimana.
