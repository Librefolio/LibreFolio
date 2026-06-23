# 🔌 Provider FX

LibreFolio sincronizza automaticamente i tassi di cambio utilizzando i feed ufficiali delle banche centrali. Ogni coppia di valute configurata può avere un elenco prioritario di sorgenti, creando un robusto sistema di fallback nel caso in cui un servizio diventi indisponibile.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
 <a href="ecb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.ecb.europa.eu/favicon-32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="ECB favicon">
 <span class="card-title" style="margin: 0;">Banca Centrale Europea (ECB)</span>
 </div>
 <span class="card-desc">Tassi di cambio di riferimento giornalieri dell'ECB, valuta base EUR.</span>
 </a>
 <a href="fed/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://fred.stlouisfed.org/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="FED favicon">
 <span class="card-title" style="margin: 0;">Federal Reserve (FED)</span>
 </div>
 <span class="card-desc">Tassi di cambio del database FRED, valuta base USD.</span>
 </a>
 <a href="boe/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="BOE favicon">
 <span class="card-title" style="margin: 0;">Bank of England (BOE)</span>
 </div>
 <span class="card-desc">Tassi di riferimento giornalieri della BOE, valuta base GBP.</span>
 </a>
 <a href="snb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://data.snb.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="SNB favicon">
 <span class="card-title" style="margin: 0;">Banca Nazionale Svizzera (SNB)</span>
 </div>
 <span class="card-desc">Tassi giornalieri stabili del franco svizzero dalla SNB, valuta base CHF.</span>
 </a>
 <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
  <div style="display: flex; align-items: center; gap: 0.75rem;">
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
  <span class="card-title" style="margin: 0;">Richiedi Nuovo Plugin</span>
  </div>
  <span class="card-desc">Il tuo provider di tassi di cambio non è presente? Richiedi un nuovo plugin o contribuisci!</span>
 </a>
 </div>

## 📊 Confronto Provider

| <span style="min-width: 320px;">Provider</span> | Valuta Base | Valute Supportate | <span style="min-width: 220px;">Frequenza di aggiornamento</span> | API Key | Note |
|:---|:---:|:---:|:---:|:---:|:---|
| <img src="https://www.ecb.europa.eu/favicon-32.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **ECB** (Banca Centrale Europea) | EUR 🇪🇺 | ~45 | Giornaliero, ~16:00 CET | Non richiesta | Provider primario per coppie basate sull'euro e principali valute mondiali. |
| <img src="https://fred.stlouisfed.org/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **FED** (Federal Reserve FRED) | USD 🇺🇸 | ~20 | Giornaliero, giorni lavorativi US | Non richiesta | Miglior fallback per coppie basate sul dollaro USA. |
| <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BOE** (Bank of England) | GBP 🇬🇧 | ~15 | Giornaliero, giorni lavorativi UK | Non richiesta | Buona copertura per coppie basate sulla sterlina. |
| <img src="https://data.snb.ch/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **SNB** (Banca Nazionale Svizzera) | CHF 🇨🇭 | ~10 | Giornaliero, giorni lavorativi svizzeri | Non richiesta | Quotazioni altamente stabili per coppie in franco svizzero. |

## 🎯 Come Funzionano Routing e Fallback

LibreFolio non ti limita a un'unica sorgente. Quando gestisce i tassi di cambio:

1. 🛤️ **Rotte Dirette**: Se esiste un tasso diretto (es. EUR/USD tramite ECB), LibreFolio lo recupera.
2. 🔀 **Rotte a Catena**: Se nessun provider diretto supporta la tua coppia (es. EUR/RON), LibreFolio può convertirla automaticamente attraverso una catena (es. EUR → USD → RON).
3. 🔄 **Auto Fallback**: Se il provider primario fallisce durante la sincronizzazione (es. timeout di rete), LibreFolio prova automaticamente il provider successivo configurato.
4. ✍️ **Sentinel Manuale**: Per le coppie di valute che non sono supportate da alcuna banca centrale, puoi impostare il provider su `MANUAL` per inserire i tassi manualmente.
