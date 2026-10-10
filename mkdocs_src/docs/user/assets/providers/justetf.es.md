# <img src="https://www.justetf.com/android-chrome-144x144.png?v2" alt=""> justETF

justETF proporciona los precios de los ETF europeos por su ISIN, en euros, dólares estadounidenses, francos suizos o libras británicas.
También incluye la descripción de cada fondo y su distribución geográfica y sectorial.

## 🔍 Qué ofrece

- **Precio actual**: en EUR, el precio en vivo de la bolsa gettex; cuando no haya precio en vivo — y
  siempre en USD, CHF y GBP — el último precio diario.
- **Histórico**: precios de cierre diarios en la moneda que elijas.
- **Dividendos**: las distribuciones que se muestran en el gráfico del fondo se convierten en eventos de dividendo.
- **Búsqueda**: por nombre, ticker, WKN o ISIN, entre los ETF listados en justETF.
- **Detalles**: una descripción con la TER y la política de distribución, la distribución geográfica y
  sectorial, el ISIN y el ticker.

## ✏️ Configúralo

**Buscar en línea** lo configura por ti. Manualmente, en **Asignación de proveedor**:

1. Elige **JustETF** como **Proveedor**.
2. Escribe el **ISIN** del fondo, por ejemplo `IE00B4L5Y983` (iShares Core MSCI World).
3. En `currency`, elige `EUR` (el valor predeterminado), `USD`, `CHF` o `GBP`: todos los precios del activo se
   almacenan en esa moneda.

### 💱 Elige la moneda en la búsqueda

Cada ETF aparece cuatro veces en los resultados, una por moneda: 🇪🇺 EUR, 🇺🇸 USD, 🇨🇭 CHF y
🇬🇧 GBP. 👑 marca la moneda propia del fondo, en la que se calcula su NAV — no necesariamente la que
usas para operar.

justETF convierte los precios en USD, CHF y GBP con sus propios tipos de cambio. ¿Tu divisa de referencia es otra? Elige cualquiera de las cuatro: LibreFolio convierte con sus propios
[tipos de cambio](../../fx/index.md).

## ⚠️ Límites

- Solo ISIN: para un ticker, usa [Yahoo Finance](yahoo-finance.md).
- Solo el precio en EUR es en vivo.
- LibreFolio lee el sitio web de justETF: un cambio por su parte puede interrumpir la actualización de los precios hasta que se
  actualice LibreFolio.

## 🔗 Relacionado

- 🔌 **[Proveedores de activos](index.md)** — Compara los proveedores
- 🛠️ **Para desarrolladores: [Proveedor JustETF](../../../developer/backend/assets/provider_justetf.md)** — Cotizaciones en vivo, gráficos y almacenamiento en caché
