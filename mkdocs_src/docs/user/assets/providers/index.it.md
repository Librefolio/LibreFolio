# 🔌 Provider

LibreFolio supporta molteplici provider di quotazioni per recuperare automaticamente i prezzi attuali e i dati storici dei tuoi asset.

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
 <span class="card-desc">Integrazione con Borsa Italiana per strumenti Euronext.</span>
 </a>
 <a href="css-scraper/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="../../static/cssscraper.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="CSS Scraper icon">
 <span class="card-title" style="margin: 0;">CSS Scraper</span>
 </div>
 <span class="card-desc">Scraper con selettore di pagine web per prezzi di obbligazioni personalizzate o asset esotici.</span>
 </a>
 <a href="scheduled-investment/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="../../static/scheduled_investment.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Scheduled Investment icon">
 <span class="card-title" style="margin: 0;">Investimento programmato</span>
 </div>
 <span class="card-desc">Asset a reddito fisso che calcolano il valore tramite calendari di interesse.</span>
 </a>
</div>

## 📊 Confronto Provider

| Provider | Prezzo Attuale | Storico | Ricerca | Identificatore | Note |
|----------|:---:|:---:|:---:|---|---|
| <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Yahoo Finance** | ✅ | ✅ | ✅ | Ticker (es. `AAPL`, `VWCE.DE`) | Ideale per azioni, ETF, fondi comuni |
| <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **justETF** | ✅ (EUR) | ✅ | ✅ | ISIN (es. `IE00BK5BQT80`) | ETF europei, multi-valuta |
| <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Borsa Italiana** | ✅ | ✅ | ✅ | ISIN o codice alpha | Azioni, obbligazioni ed ETF italiani |
| <img src="../../static/cssscraper.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **CSS Scraper** | ✅ | ❌ | ❌ | URL | Estrae dati di prezzo da qualsiasi pagina web |
| <img src="../../static/scheduled_investment.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Investimento programmato** | ✅ | ✅ | ❌ | Generato automaticamente | Strumenti a reddito fisso con calendari di interesse |

## 🎯 Scegliere un Provider

- **Azioni & ETF**: Usa **Yahoo Finance** — copertura più ampia, supporta la ricerca.
- **ETF Europei**: Usa **justETF** per dati più dettagliati sugli ETF europei.
- **Borsa Italiana**: Usa Borsa Italiana direttamente per i titoli quotati su Euronext Milano.
- **Obbligazioni su Borsa Italiana**: Usa **CSS Scraper** per estrarre i prezzi direttamente dal web.
- **Conti deposito / Depositi vincolati**: Usa **Investimento programmato** con calendari di interesse.
