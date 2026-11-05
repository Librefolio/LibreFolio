# <img src="https://www.justetf.com/android-chrome-144x144.png?v2" alt=""> justETF

justETF proporciona precios de los ETF europeos a partir de su ISIN, en euros, dólares estadounidenses, francos suizos o libras esterlinas.
También incluye la descripción de cada fondo y su desglose por países y sectores.

## 🔍 Qué ofrece

- **Precio actual**: en EUR, el precio en vivo de la bolsa gettex; cuando no lo hay —y
  siempre en USD, CHF y GBP—, el último precio diario.
- **Historial**: precios de cierre diarios en la moneda que elijas.
- **Dividendos**: las distribuciones que se muestran en el gráfico del fondo se convierten en eventos de dividendo.
- **Búsqueda**: por nombre, ticker, WKN o ISIN, entre los ETF listados en justETF.
- **Detalles**: una descripción con el TER y la política de distribución, el desglose por países y sectores,
  el ISIN y el ticker.

## ✏️ Configúralo

**Buscar en línea** te lo configura. Manualmente, en **Asignación de proveedor**:

1. Elige **JustETF** como **Proveedor**.
2. Escribe el **ISIN** del fondo, por ejemplo `IE00B4L5Y983` (iShares Core MSCI World).
3. En `currency`, elige `EUR` (la opción predeterminada), `USD`, `CHF` o `GBP`: todos los precios del activo
   se almacenan en esa moneda.

### 💱 Elige la moneda en la búsqueda {: #search-currency }

Cada ETF aparece cuatro veces en los resultados, una por moneda: 🇪🇺 EUR, 🇺🇸 USD, 🇨🇭 CHF y
🇬🇧 GBP, a menos que hayas elegido una [moneda preferida](#preferred-currency). 👑 marca la moneda
propia del fondo, aquella en la que se calcula su NAV —no necesariamente aquella en la que operas—. Una
línea al pie de los resultados lo indica siempre que un resultado muestra 👑.

justETF convierte los precios en USD, CHF y GBP con sus propios tipos de cambio. ¿Tu moneda de
informe es otra? Elige cualquiera de las cuatro: LibreFolio convierte con sus propios
[tipos de cambio](../../fx/index.md).

### ⭐ Tu moneda preferida {: #preferred-currency }

¿Siempre eliges la misma moneda? Elígela una vez como **Moneda preferida**, en **JustETF**, dentro de
**Configuración › Plugins**, o con **Configurar** junto al proveedor en el diálogo del activo. Tus
búsquedas mostrarán entonces cada ETF una sola vez, en esa moneda, con 👑 solo en los fondos cuyo NAV se calcula en ella.
La opción **Todas las monedas**, que es la predeterminada, muestra las cuatro.

Es una configuración personal: cambia solo tus propias búsquedas, nunca un precio ni un activo que ya
tengas. Consulta [Configuración de plugins](../../settings/plugins.md#search-preferences).

## ⚠️ Limitaciones

- Solo ISIN: para un ticker, usa [Yahoo Finance](yahoo-finance.md).
- Solo el precio en EUR está disponible en vivo.
- LibreFolio lee el sitio web de justETF: un cambio en su sitio puede impedir que se obtengan los precios hasta que se actualice LibreFolio.

## 🔗 Relacionado

- 🔌 **[Proveedores de activos](index.md)** — Compara los proveedores
- 🧩 **[Configuración de plugins](../../settings/plugins.md)** — Tu moneda preferida en la búsqueda
- 🛠️ **Para desarrolladores: [Proveedor JustETF](../../../developer/backend/assets/provider_justetf.md)** — Cotizaciones en vivo, gráficos y almacenamiento en caché
