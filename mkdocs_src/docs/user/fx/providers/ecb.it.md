# <img src="https://www.ecb.europa.eu/favicon-32.png" alt=""> Banca Centrale Europea (BCE)

La **Banca Centrale Europea (BCE)** è il principale provider di tassi di riferimento per i portafogli europei. Pubblica quotidianamente i tassi di cambio dell'Euro rispetto a circa 45 valute principali ed emergenti.

## 📊 Funzionalità

- ✅ **Prezzo Attuale**: Tasso di riferimento aggiornato una volta al giorno
- ✅ **Storico**: Tassi storici disponibili a partire dal 1999
- ❌ **Ricerca**: Nessuna ricerca di asset (solo tassi di cambio)

## 🔧 Specifiche

- **Valuta di Base**: EUR 🇪🇺
- **Frequenza di Aggiornamento**: Da lunedì a venerdì (esclusi i giorni festivi della BCE), intorno alle 16:00 CET
- **API Key**: Non richiesta (endpoint pubblico)

## 💰 Valute Supportate

La BCE supporta un'ampia gamma di valute, tra cui:

- **Principali**: USD 🇺🇸, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿
- **Europee/Regionali**: SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, PLN 🇵🇱, CZK 🇨🇿, HUF 🇭🇺, RON 🇷🇴, BGN 🇧🇬, TRY 🇹🇷
- **Globali / Emergenti**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦

## 📝 Note Importanti

- **Formato delle quotazioni**: I tassi sono espressi come l'importo di valuta estera per 1 EUR (es. 1 EUR = 1.08 USD). LibreFolio normalizza automaticamente questo tasso in base alla valuta di base del tuo portafoglio.
- **Nessun dato nei fine settimana**: La BCE non pubblica tassi di sabato, domenica o nei giorni festivi ufficiali della BCE (es. Venerdì Santo, Lunedì di Pasqua, Natale). LibreFolio manterrà il tasso dell'ultimo giorno lavorativo disponibile per le valutazioni durante il fine settimana.
