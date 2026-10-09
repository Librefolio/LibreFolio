# <img src="https://www.ecb.europa.eu/favicon-32.png" alt=""> Banca Centrale Europea (BCE)

La **Banca Centrale Europea (BCE)** è il principale provider di tassi di riferimento per i portafogli europei. Pubblica ogni giorno i tassi di riferimento dell'euro rispetto a circa 30 valute.

## 📊 Funzionalità

- ✅ **Prezzo Attuale**: Tasso di riferimento aggiornato una volta al giorno
- ✅ **Storico**: Tassi storici disponibili a partire dal 1999
- ❌ **Ricerca**: Nessuna ricerca di asset (solo tassi di cambio)

## 🔧 Specifiche

- **Valuta di Base**: EUR 🇪🇺
- **Frequenza di Aggiornamento**: Da lunedì a venerdì (esclusi i giorni festivi della BCE), intorno alle 16:00 CET
- **API Key**: Non richiesta (endpoint pubblico)

## 💰 Valute Supportate

La BCE pubblica un tasso ogni giorno lavorativo per circa 30 valute, tra cui:

- **Principali**: USD 🇺🇸, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿
- **Europee/Regionali**: SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, ISK 🇮🇸, PLN 🇵🇱, CZK 🇨🇿, HUF 🇭🇺, RON 🇷🇴, TRY 🇹🇷
- **Globali / Emergenti**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦

Le valute che la BCE non pubblica più, come il lev bulgaro (BGN, sostituito dall'euro nel 2026), la kuna croata (HRK) o il rublo russo (RUB), conservano i tassi passati: una sincronizzazione ne scarica ancora lo storico, e non arrivano nuovi tassi.

## 📝 Note Importanti

- **Formato delle quotazioni**: I tassi sono espressi come l'importo di valuta estera per 1 EUR (es. 1 EUR = 1.08 USD). LibreFolio normalizza automaticamente questo tasso in base alla valuta di base del tuo portafoglio.
- **Nessun dato nei fine settimana**: La BCE non pubblica tassi di sabato, domenica o nei giorni festivi ufficiali della BCE (es. Venerdì Santo, Lunedì di Pasqua, Natale). LibreFolio manterrà il tasso dell'ultimo giorno lavorativo disponibile per le valutazioni durante il fine settimana.
