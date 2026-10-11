# <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" alt=""> Yahoo Finance

Yahoo Finance cubre acciones, ETFs, fondos, índices y criptomonedas de bolsas de todo el mundo, y puedes buscarlos por nombre o ticker.

## 🔍 Qué ofrece

- **Precio actual**: el último precio que Yahoo reporta para el ticker — en algunas bolsas está retrasado.
- **Historial**: apertura, máximo, mínimo, cierre y volumen diarios, hasta donde se remonta Yahoo.
- **Dividendos y desdoblamientos**: registrados como eventos del activo.
- **Búsqueda**: por nombre o ticker.
- **Detalles**: tipo, divisa, descripción, sector, ticker y, cuando Yahoo lo tiene, el ISIN.

## ✏️ Configúralo

**Buscar en línea** te lo configura. De forma manual, en **Asignación de proveedor**, elige **Yahoo Finance**, establece **Tipo de identificador** en **TICKER** y escribe el ticker como **Identificador**. No hay nada más que rellenar.

| Activo | Ticker |
|-------|--------|
| Apple Inc. | `AAPL` |
| Vanguard FTSE All-World (Xetra) | `VWCE.DE` |
| iShares Core S&P 500 (Milán) | `CSSPX.MI` |
| Bitcoin en dólares estadounidenses | `BTC-USD` |

Fuera de EE. UU., añade el sufijo de la bolsa al ticker: `.DE` para Xetra, `.MI` para Milán, `.AS` para Ámsterdam.

## ⚠️ Límites

- **ISIN** también funciona como **Tipo de identificador**, pero solo cuando Yahoo puede emparejarlo con un ticker: es preferible el ticker.
- Yahoo puede limitar la frecuencia de las solicitudes, y algunos tickers tienen días sin datos.

## 🔗 Relacionado

- 🔌 **[Proveedores de activos](index.md)** — Compara los proveedores
- 🛠️ **Para desarrolladores: [Proveedor de Yahoo Finance](../../../developer/backend/assets/provider_yahoo_finance.md)** — Solicitudes, almacenamiento en caché y eventos
