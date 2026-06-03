# 🔌 Proveedores

LibreFolio es compatible con múltiples proveedores de precios para obtener automáticamente los precios actuales y los datos históricos de sus activos.

## 📊 Comparación de Proveedores

| Proveedor | Precio Actual | Historial | Búsqueda | Identificador | Notas |
|----------|:---:|:---:|:---:|---|---|
| **Yahoo Finance** | ✅ | ✅ | ✅ | Ticker (ej. `AAPL`, `VWCE.DE`) | Ideal para acciones, ETFs, fondos mutuos |
| **justETF** | ✅ (EUR) | ✅ | ✅ | ISIN (ej. `IE00BK5BQT80`) | ETF europeos, multidivisa (EUR/USD/CHF/GBP) |
| **CSS Scraper** | ✅ | ❌ | ❌ | URL | Extrae datos de precios de cualquier página web |
| **Inversión programada** | ✅ | ✅ | ❌ | Autogenerado | Instrumentos de renta fija con calendarios de intereses |

## 🎯 Elección de un Proveedor

- **Acciones y ETF**: Use **Yahoo Finance** — mayor cobertura, permite la búsqueda
- **ETF Europeos**: Use **justETF** para datos más detallados de ETF europeos
- **Bonos en Borsa Italiana**: Use **CSS Scraper** para extraer precios directamente
- **Cuentas de ahorro / Depósitos fijos**: Use **Inversión programada** con calendarios de tipos de interés

## 📚 Detalles de los Proveedores

- [📈 Yahoo Finance](yahoo-finance.md)
- [📊 justETF](justetf.md)
- [🔍 CSS Scraper](css-scraper.md) — guía detallada para web scraping
- [🧮 Inversión programada](scheduled-investment.md)
