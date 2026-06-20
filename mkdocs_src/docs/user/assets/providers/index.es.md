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
 <img src="../../static/cssscraper.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="CSS Scraper icon">
 <span class="card-title" style="margin: 0;">CSS Scraper</span>
 </div>
 <span class="card-desc">Scraper de selector de páginas web para precios de bonos personalizados o exóticos.</span>
 </a>
 <a href="scheduled-investment/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="../../static/scheduled_investment.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="icono de inversión programada">
 <span class="card-title" style="margin: 0;">Inversión programada</span>
 </div>
 <span class="card-desc">Activos de renta fija cuyo valor se calcula mediante calendarios de tipos de interés.</span>
 </a>
</div>

## 📊 Comparativa de Proveedores

| Proveedor | Precio Actual | Historial | Búsqueda | Identificador | Notas |
|----------|:---:|:---:|:---:|---|---|
| <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Yahoo Finance** | ✅ | ✅ | ✅ | Ticker (ej. `AAPL`, `VWCE.DE`) | El mejor para acciones, ETF, fondos mutuos |
| <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **justETF** | ✅ (EUR) | ✅ | ✅ | ISIN (ej. `IE00BK5BQT80`) | ETF europeos, multidivisa |
| <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Borsa Italiana** | ✅ | ✅ | ✅ | ISIN o código alfa | Acciones, bonos y ETF italianos |
| <img src="../../static/cssscraper.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **CSS Scraper** | ✅ | ❌ | ❌ | URL | Extrae datos de precio de cualquier página web |
| <img src="../../static/scheduled_investment.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Inversión programada** | ✅ | ✅ | ❌ | Auto-generado | Instrumentos de renta fija con calendarios de intereses |

## 🎯 Elegir un Proveedor

- **Acciones y ETF**: Use **Yahoo Finance** — mayor cobertura, soporta búsqueda
- **ETF Europeos**: Use **justETF** para obtener datos más detallados de ETF europeos
- **Borsa Italiana**: Use Borsa Italiana directamente para cotizaciones de Euronext Milano
- **Bonos en Borsa Italiana**: Use **CSS Scraper** para extraer precios directamente de la web
- **Cuentas de ahorro / Depósitos fijos**: Use **Inversión programada** con calendarios de tipos de interés
