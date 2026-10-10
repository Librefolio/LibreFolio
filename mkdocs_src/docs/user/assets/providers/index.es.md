# 🔌 Proveedores

Un proveedor mantiene actualizados los precios de un activo por ti: el precio de hoy, su historial y, para algunos,
detalles como el tipo o el sector. Cada activo tiene como máximo un proveedor: elige un
resultado de **Buscar en línea** para conectarlo, o configúralo tú mismo en **Asignación de proveedor** — consulta
[Crear y editar](../create-edit.md).

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="yahoo-finance/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon de Yahoo Finance">
            <span class="card-title" style="margin: 0;">Yahoo Finance</span>
        </div>
        <span class="card-desc">Acciones, ETF, fondos y criptomonedas de bolsas de todo el mundo.</span>
    </a>
    <a href="justetf/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon de justETF">
            <span class="card-title" style="margin: 0;">justETF</span>
        </div>
        <span class="card-desc">Comparación de ETF europeos, precios y estructuras de activos.</span>
    </a>
    <a href="borsa-italiana/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon de Borsa Italiana">
            <span class="card-title" style="margin: 0;">Borsa Italiana</span>
        </div>
        <span class="card-desc">Acciones, bonos, ETF y fondos italianos, en italiano o inglés.</span>
    </a>
    <a href="css-scraper/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="../../../static/cssscraper.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Icono de CSS Scraper">
            <span class="card-title" style="margin: 0;">CSS Scraper</span>
        </div>
        <span class="card-desc">Scraper de páginas web mediante selectores para precios de bonos personalizados o instrumentos exóticos.</span>
    </a>
    <a href="scheduled-investment/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="../../../static/scheduled_investment.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Icono de Scheduled Investment">
            <span class="card-title" style="margin: 0;">Inversión programada</span>
        </div>
        <span class="card-desc">Activos de renta fija cuyo valor se calcula mediante calendarios de intereses.</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
     <div style="display: flex; align-items: center; gap: 0.75rem;">
     <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
     <span class="card-title" style="margin: 0;">Solicitar nuevo plugin</span>
     </div>
     <span class="card-desc">¿Falta tu proveedor de precios? ¡Solicita un nuevo plugin o contribuye con código!</span>
    </a>
    </div>

## 📊 Comparación de proveedores

| Proveedor | Precio actual | Historial | Búsqueda | Detalles | Identificador | Ideal para |
|----------|:---:|:---:|:---:|:---:|---|---|
| <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Yahoo Finance** | ✅ | ✅ | ✅ | ✅ | Ticker (`AAPL`, `VWCE.DE`) o ISIN | Acciones, ETF, fondos y criptomonedas en todo el mundo |
| <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **justETF** | ✅ | ✅ | ✅ | ✅ | ISIN (`IE00B4L5Y983`) | ETF europeos, valorados en EUR, USD, CHF o GBP |
| <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Borsa Italiana** | ✅ | ✅ | ✅ | ✅ | ISIN (`IT0003128367`) | Instrumentos cotizados en Milán, fondos de inversión italianos |
| <img src="../../../static/cssscraper.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **CSS Scraper** | ✅ | ❌ | ❌ | ❌ | URL de la página | Un precio mostrado en cualquier página web pública |
| <img src="../../../static/scheduled_investment.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Inversión programada** | ✅ | ✅ | ❌ | ❌ | Ninguno — creado para ti | Depósitos, préstamos y bonos valorados por sus intereses |

Los **detalles** son el tipo, la divisa, la descripción y datos similares que LibreFolio puede completar por ti. Algunos proveedores también registran [eventos de activos](../detail/events.md): dividendos (Yahoo Finance, justETF), desdoblamientos (Yahoo Finance), pagos de intereses y vencimiento (Inversión programada).

## 🎯 Elegir un proveedor

- **Acciones, ETF o criptomonedas en cualquier bolsa** → **Yahoo Finance**.
- **Un ETF europeo**, o precios de ETF en USD, CHF o GBP → **justETF**.
- **Acciones, bonos, ETF o fondos negociados en Milán**, y fondos de inversión italianos → **Borsa Italiana**.
- **Un precio que solo muestra una página web** → **CSS Scraper**.
- **Una cuenta de ahorros, depósito a plazo, préstamo P2P o bono cuyo valor se calcula a partir de sus intereses** →
  **Inversión programada**.
- **¿Nada encaja?** Marca **Sin proveedor** e introduce los precios tú mismo en el
  [Editor de datos](../detail/data-editor.md).

## 🔗 Enlaces relacionados

- 🛠️ **Para desarrolladores: [Proveedores de activos](../../../developer/backend/assets/system_providers.md)** — Cómo funciona internamente cada proveedor
