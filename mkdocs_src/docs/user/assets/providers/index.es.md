# 🔌 Proveedores

LibreFolio es compatible con múltiples proveedores de precios para obtener automáticamente los precios actuales y los datos históricos de sus activos.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
 <a href="yahoo-finance/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Yahoo Finance favicon">
 <span class="card-title" style="margin: 0;">Yahoo Finance</span>
 </div>
 <span class="card-desc">Proveedor predeterminado para acciones globales, ETF y fondos mutuos.</span>
 </a>
 <a href="justetf/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="justETF favicon">
 <span class="card-title" style="margin: 0;">justETF</span>
 </div>
 <span class="card-desc">Comparación de ETF europeos, precios y estructuras de activos.</span>
 </a>
 <a href="borsa-italiana/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Borsa Italiana favicon">
 <span class="card-title" style="margin: 0;">Borsa Italiana</span>
 </div>
 <span class="card-desc">Integración con la bolsa italiana para instrumentos de Euronext.</span>
 </a>
 <a href="css-scraper/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="../../../../static/cssscraper.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="CSS Scraper icon">
 <span class="card-title" style="margin: 0;">CSS Scraper</span>
 </div>
 <span class="card-desc">Scraper de selector de páginas web para precios de bonos personalizados o exóticos.</span>
 </a>
 <a href="scheduled-investment/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="../../../../static/scheduled_investment.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="icono de inversión programada">
 <span class="card-title" style="margin: 0;">Inversión programada</span>
 </div>
 <span class="card-desc">Activos de renta fija cuyo valor se calcula mediante calendarios de tipos de interés.</span>
 </a>
 <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
  <div style="display: flex; align-items: center; gap: 0.75rem;">
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
  <span class="card-title" style="margin: 0;">Solicitar Nuevo Plugin</span>
  </div>
  <span class="card-desc">¿Falta tu proveedor? ¡Solicita un nuevo plugin o contribuye!</span>
 </a>
 </div>

## 📊 Comparativa de Proveedores

| Proveedor | Precio Actual | Historial | Búsqueda | Identificador | Notas |
|----------|:---:|:---:|:---:|---|---|
| <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Yahoo Finance** | ✅ | ✅ | ✅ | Ticker (ej. `AAPL`, `VWCE.DE`) | El mejor para acciones, ETF, fondos mutuos |
| <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **justETF** | ✅ (EUR) | ✅ | ✅ | ISIN (ej. `IE00BK5BQT80`) | ETF europeos, multidivisa |
| <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Borsa Italiana** | ✅ | ✅ | ✅ | ISIN o código alfa | Acciones, bonos y ETF italianos |
| <img src="../../../../static/cssscraper.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **CSS Scraper** | ✅ | ❌ | ❌ | URL | Extrae datos de precio de cualquier página web |
| <img src="../../../../static/scheduled_investment.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Inversión programada** | ✅ | ✅ | ❌ | Auto-generado | Instrumentos de renta fija con calendarios de intereses |

## 🎯 Elegir un Proveedor

- **Acciones y ETF**: Use **Yahoo Finance** — mayor cobertura, soporta búsqueda
- **ETF Europeos**: Use **justETF** para obtener datos más detallados de ETF europeos
- **Borsa Italiana**: Use Borsa Italiana directamente para cotizaciones de Euronext Milano
- **Bonos en Borsa Italiana**: Use **CSS Scraper** para extraer precios directamente de la web
- **Cuentas de ahorro / Depósitos fijos**: Use **Inversión programada** con calendarios de tipos de interés
