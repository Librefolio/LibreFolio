# 🔌 Proveedores

LibreFolio admite múltiples proveedores de precios para obtener automáticamente los precios actuales y los datos históricos de sus activos.

## 📊 Comparación de Proveedores

| Proveedor | Precio Actual | Historial | Búsqueda | Identificador | Notas |
|----------|:---:|:---:|:---:|---|---|
| **Yahoo Finance** | ✅ | ✅ | ✅ | Ticker (ej., `AAPL`, `VWCE.DE`) | Ideal para acciones, ETF, fondos mutuos |
| **justETF** | ✅ | ✅ | ❌ | ISIN (ej., `IE00BK5BQT80`) | ETF europeos con datos detallados |
| **CSS Scraper** | ✅ | ❌ | ❌ | URL | Extrae datos de precios de cualquier página web |
| **Scheduled Investment** | ✅ | ✅ | ❌ | Generado automáticamente | Instrumentos de renta fija con cronogramas de intereses |

## 🎯 Elección de un Proveedor

- **Acciones y ETF**: Use **Yahoo Finance** — mayor cobertura, admite búsqueda
- **ETF Europeos**: Use **justETF** para obtener datos más detallados de ETF europeos
- **Bonos en Borsa Italiana**: Use **CSS Scraper** para extraer los precios directamente
- **Cuentas de ahorro / Depósitos fijos**: Use **Scheduled Investment** con cronogramas de tipos de interés

## 📚 Detalles de los Proveedores

- [📈 Yahoo Finance](yahoo-finance.md)
- [📊 justETF](justetf.md)
- [🔍 CSS Scraper](css-scraper.md) — guía detallada para web scraping
- [🧮 Scheduled Investment](scheduled-investment.md)
