# <img src="https://data.snb.ch/favicon.ico" alt=""> Banca Nazionale Svizzera (SNB)

Il provider **Banca Nazionale Svizzera (SNB)** pubblica tassi di cambio **medi mensili** per il franco svizzero (CHF), recuperati dal portale dati pubblico della SNB. È una fonte stabile e autorevole per asset denominati in CHF.

!!! warning "Monthly data only — no daily rates"

    La SNB **non** offre un set di dati con tassi giornalieri: ogni valore è la **media di un mese di calendario**, registrato il **1° di quel mese**. Nelle catene di conversione un tasso viene calcolato solo nelle date in cui **tutti** i provider coinvolti hanno dati, quindi passando attraverso la SNB si ottiene un punto al mese. Se hai bisogno di tassi CHF giorno per giorno, usa un altro provider (es. ECB o FED) per la coppia.

## 📊 Funzionalità

- ✅ **Prezzo corrente**: ultima media mensile disponibile
- ✅ **Cronologia**: medie mensili storiche
- ❌ **Ricerca**: nessuna ricerca di asset (solo tassi FX)

## 🔧 Specifiche

- **Valuta base**: CHF 🇨🇭
- **Frequenza di aggiornamento**: mensile — le nuove medie vengono pubblicate intorno al 2° giorno lavorativo del mese successivo
- **Chiave API**: non richiesta (API pubblica del portale dati SNB)

## 💰 Valute supportate

La SNB copre circa **25 valute** contro CHF; LibreFolio carica dinamicamente l'elenco esatto dal portale dati SNB. Include:

- **Principali**: USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CNY 🇨🇳
- **Globali**: CAD 🇨🇦, AUD 🇦🇺 e altre valute mondiali

## 📝 Note importanti

- **Quotazione multi-unità delle valute**: La SNB quota alcune valute per **100 unità** invece di 1 unità (es. `100 JPY = x CHF`). **LibreFolio rileva e normalizza automaticamente questi tassi** in valori per unità, per garantire che le tue transazioni siano calcolate correttamente.
- **Un punto al mese**: i tassi sono datati il 1° di ogni mese. Le conversioni nelle date comprese tra due punti mensili usano il tasso disponibile più recente (backward-fill).
