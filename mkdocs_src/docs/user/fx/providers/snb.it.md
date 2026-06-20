# <img src="https://data.snb.ch/favicon.ico" alt=""> Banca Nazionale Svizzera (SNB)

Il provider **Banca Nazionale Svizzera (SNB)** pubblica i tassi di cambio giornalieri per il Franco Svizzero (CHF). È estremamente stabile e preciso, il che lo rende una fonte preziosa per gli asset basati su CHF.

## 📊 Funzionalità

- ✅ **Prezzo Attuale**: Tasso di riferimento aggiornato giornalmente
- ✅ **Storico**: Tassi giornalieri storici
- ❌ **Ricerca**: Ricerca asset non disponibile (solo tassi FX)

## 🔧 Specifiche

- **Valuta di Base**: CHF 🇨🇭
- **Frequenza di Aggiornamento**: Giornaliera nei giorni lavorativi svizzeri
- **API Key**: Non richiesta (API pubblica del Portale Dati SNB)

## 💰 Valute Supportate

La SNB fornisce tassi di cambio per un elenco selezionato di valute principali:

- **Valute Supportate**: USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CAD 🇨🇦, AUD 🇦🇺, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, CNY 🇨🇳

## 📝 Note Importanti

- **Quotazione valutaria a unità multiple**: La SNB esprime il tasso di alcune valute per **100 unità** (ad es. Yen giapponese, Corona svedese, Corona norvegese, Corona danese) invece di 1 unità. Per esempio, il tasso viene mostrato come `100 JPY = 0.58 CHF`. **LibreFolio rileva e normalizza automaticamente questi tassi** in valori per singola unità per garantire che le transazioni siano calcolate correttamente.
- **Festività**: I tassi non vengono pubblicati nei giorni festivi bancari svizzeri o nei fine settimana.
