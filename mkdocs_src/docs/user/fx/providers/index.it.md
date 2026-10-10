# 🔌 Provider FX

LibreFolio scarica i tassi di cambio dalle banche centrali — gratuitamente e senza API key. Una coppia
di valute può avere più fonti in ordine di priorità: se la prima fallisce durante una sincronizzazione, subentra
la successiva.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="ecb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.ecb.europa.eu/favicon-32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon della BCE">
            <span class="card-title" style="margin: 0;">Banca Centrale Europea (BCE)</span>
        </div>
        <span class="card-desc">Tassi di cambio di riferimento giornalieri della BCE, valuta base EUR.</span>
    </a>
    <a href="fed/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://fred.stlouisfed.org/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon della FED">
            <span class="card-title" style="margin: 0;">Federal Reserve (FED)</span>
        </div>
        <span class="card-desc">Tassi di cambio del database FRED, valuta base USD.</span>
    </a>
    <a href="boe/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon della BOE">
            <span class="card-title" style="margin: 0;">Bank of England (BOE)</span>
        </div>
        <span class="card-desc">Tassi di riferimento giornalieri della BOE, valuta base GBP.</span>
    </a>
    <a href="snb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://data.snb.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon della BNS">
            <span class="card-title" style="margin: 0;">Banca Nazionale Svizzera (SNB)</span>
        </div>
        <span class="card-desc">Tassi medi mensili stabili del franco svizzero dalla SNB, valuta base CHF.</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
     <div style="display: flex; align-items: center; gap: 0.75rem;">
     <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
     <span class="card-title" style="margin: 0;">Richiedi un nuovo plugin</span>
     </div>
     <span class="card-desc">Manca la tua fonte di tassi di cambio? Richiedi un nuovo plugin o contribuisci al codice!</span>
    </a>
    </div>

## 📊 Confronto tra i provider

Ogni banca centrale quota le altre valute rispetto alla propria, la **valuta base**.

| <span style="min-width: 320px;">Provider</span> | Valuta base | <span style="min-width: 220px;">Frequenza di aggiornamento</span> | Adatto per |
|:---|:---:|:---|:---|
| <img src="https://www.ecb.europa.eu/favicon-32.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BCE** (Banca Centrale Europea) | EUR 🇪🇺 | Giornaliera, intorno alle 16:00 CET nei giorni lavorativi della BCE | Le coppie con l'euro e le principali valute mondiali |
| <img src="https://fred.stlouisfed.org/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **FED** (Federal Reserve FRED) | USD 🇺🇸 | Giornaliera, nei giorni lavorativi statunitensi | Le coppie con il dollaro statunitense |
| <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BOE** (Bank of England) | GBP 🇬🇧 | Giornaliera, nei giorni lavorativi britannici | Le coppie con la sterlina |
| <img src="https://data.snb.ch/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **SNB** (Banca Nazionale Svizzera) | CHF 🇨🇭 | Medie mensili, un valore al mese | Le coppie con il franco svizzero, quando basta un tasso mensile |

## 🎯 Come funzionano routing e fallback

1. 🛤️ **Rotta diretta**: una banca centrale quota la coppia — ad es. EUR/USD dalla BCE.
2. 🔀 **Rotta a catena**: nessuna banca quota la coppia, quindi LibreFolio combina più passaggi — ad es. RON/USD come
   RON → EUR → USD, entrambi i passaggi dalla BCE. Una catena ottiene un tasso solo nei giorni in cui ogni passaggio
   ne ha uno.
3. 🔄 **Fallback**: con più rotte, una sincronizzazione le prova in ordine di priorità e usa la prima
   che funziona.
4. ✍️ **Manuale**: nessuna rotta per la tua coppia? Salvala senza un provider e inserisci i tassi manualmente
   nell'[Editor dati](../detail/data-editor.md).

Scegli le rotte quando [aggiungi una coppia](../add-pair.md) e le modifichi in seguito con il
pulsante [Provider](../detail/provider.md) della coppia.

!!! warning "SNB: un tasso al mese"

    La SNB pubblica medie mensili, datate il 1º di ogni mese. Una coppia che la usa ottiene un
    tasso al mese, e una catena che passa per la SNB ha tassi solo in quei giorni.

## 🔗 Correlati

- 🛠️ **Per gli sviluppatori: [Provider FX](../../../developer/backend/fx/providers/index.md)** — API, serie e formati di quotazione
