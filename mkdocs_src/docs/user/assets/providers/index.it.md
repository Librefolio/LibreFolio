# 🔌 Provider di Prezzo

LibreFolio supporta più provider di prezzo per recuperare automaticamente i prezzi correnti e i dati storici dei tuoi asset.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="yahoo-finance/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Yahoo Finance favicon">
            <span class="card-title" style="margin: 0;">Yahoo Finance</span>
        </div>
        <span class="card-desc">Provider predefinito per azioni globali, ETF e fondi comuni.</span>
    </a>
    <a href="justetf/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="justETF favicon">
            <span class="card-title" style="margin: 0;">justETF</span>
        </div>
        <span class="card-desc">Confronto di ETF europei, prezzi e strutture degli asset.</span>
    </a>
    <a href="borsa-italiana/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Borsa Italiana favicon">
            <span class="card-title" style="margin: 0;">Borsa Italiana</span>
        </div>
        <span class="card-desc">Azioni italiane, obbligazioni, ETF e fondi con ricerca URL intelligente.</span>
    </a>
    <a href="css-scraper/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="../../../static/cssscraper.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="CSS Scraper icon">
            <span class="card-title" style="margin: 0;">CSS Scraper</span>
        </div>
        <span class="card-desc">Scraper di pagine web per prezzi di obbligazioni personalizzate o esotici.</span>
    </a>
    <a href="scheduled-investment/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="../../../static/scheduled_investment.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Scheduled Investment icon">
            <span class="card-title" style="margin: 0;">Investimento programmato</span>
        </div>
        <span class="card-desc">Asset a reddito fisso che calcolano il valore tramite calendari di interesse.</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
     <div style="display: flex; align-items: center; gap: 0.75rem;">
     <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
     <span class="card-title" style="margin: 0;">Richiedi Nuovo Plugin</span>
     </div>
     <span class="card-desc">Il tuo provider di prezzo manca? Richiedi un nuovo plugin o contribuisci!</span>
    </a>
</div>

## 📊 Confronto tra Provider

| Provider | Prezzo Corrente | Storico | Ricerca | Identificatore | Note |
|----------|:---:|:---:|:---:|---|---|
| <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Yahoo Finance** | ✅ | ✅ | ✅ | Ticker (es. `AAPL`, `VWCE.DE`) | Il migliore per azioni, ETF, fondi comuni |
| <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **justETF** | ✅ (EUR) | ✅ | ✅ | ISIN (es. `IE00BK5BQT80`) | ETF europei, multivaluta |
| <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Borsa Italiana** | ✅ | ✅ | ✅ | ISIN; fondi usano codice interno | Azioni italiane, obbligazioni, ETF e fondi. NAV dei fondi corrente solo se datato oggi; lo storico è un punto NAV alla data reale. |
| <img src="../../../static/cssscraper.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **CSS Scraper** | ✅ | ❌ | ❌ | URL | Estrae dati di prezzo da qualsiasi pagina web |
| <img src="../../../static/scheduled_investment.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Investimento programmato** | ✅ | ✅ | ❌ | Auto-generato | Strumenti a reddito fisso con calendari di interesse |

## 🎯 Scegliere un Provider

- **Azioni & ETF**: Usa **Yahoo Finance** — copertura più ampia, supporta la ricerca
- **ETF Europei**: Usa **justETF** per dati più dettagliati sugli ETF europei
- **Borsa Italiana**: Usa Borsa Italiana direttamente per azioni, obbligazioni, ETF e fondi Euronext Milano. La Ricerca Intelligente può anche risolvere gli URL dei provider Borsa supportati e acquisire automaticamente i parametri dei fondi.
- **Conti deposito / Depositi vincolati**: Usa **Investimento programmato** con calendari di interesse
