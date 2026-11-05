# <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" alt=""> Yahoo Finance

Yahoo Finance abarca acciones, ETF, fondos, índices y criptomonedas de bolsas de todo el mundo, y puedes
buscarlos por nombre o por ticker.

## 🔍 Qué ofrece

- **Precio actual**: el último precio que Yahoo informa para el ticker — en algunas bolsas va con
  retraso.
- **Histórico**: apertura, máximo, mínimo, cierre y volumen diarios, hasta donde llega Yahoo. Los cierres se guardan tal como los
  da la bolsa, sin el ajuste por los dividendos pagados desde entonces (un desdoblamiento ya está incorporado en
  los cierres de Yahoo y se registra como evento).
- **Dividendos y desdoblamientos**: se registran como eventos del activo. Para un valor de Londres cotizado en peniques, el dividendo se
  guarda en libras (1,95 peniques son 0,0195 GBP).
- **Búsqueda**: por nombre o por ticker.
- **Detalles**: tipo, divisa, descripción, sector, ticker y, cuando Yahoo lo tiene, el ISIN.
- **Detalles del fondo**: para un ETF o un fondo, el desglose por sectores (una acción recibe su único sector), la
  descripción propia del fondo cuando Yahoo no tiene un resumen de actividad para él y, al final de la descripción,
  el ratio de gastos (`TER: 0.03%`) y el emisor (`Issuer: Vanguard`). Yahoo no proporciona el ratio de gastos a todos los fondos
  —Vanguard FTSE All-World (`VWCE.DE`) no lo tiene— y entonces esa parte se omite.
  El desglose por países procede únicamente de [justETF](justetf.md).

## ✏️ Cómo configurarlo

**Search Online** lo configura por ti. Si lo haces a mano, en **Provider Assignment**, elige
**Yahoo Finance**, pon **Identifier Type** en **TICKER** y escribe el ticker como **Identifier**.
No hay nada más que rellenar.

| Activo | Ticker |
|-------|--------|
| Apple Inc. | `AAPL` |
| Vanguard FTSE All-World (Xetra) | `VWCE.DE` |
| iShares Core S&P 500 (Milán) | `CSSPX.MI` |
| Bitcoin en dólares estadounidenses | `BTC-USD` |

Fuera de EE. UU., añade el sufijo de la bolsa al ticker: `.DE` para Xetra, `.MI` para Milán, `.AS` para
Ámsterdam.

Muchos valores de Londres (sufijo `.L`) cotizan en peniques, que Yahoo indica con la divisa `GBp`.
LibreFolio guarda la divisa como `GBP` y los precios tal como los da Yahoo, en peniques, así que un
activo de este tipo necesita **Units per single price** en 100, o su valor saldrá 100 veces demasiado alto. Cuando
Yahoo indica `GBp`, seleccionar el valor en **Search Online** pone 100, con una nota bajo el campo,
y **Ask Provider** lo propone si el campo dice otra cosa
([Comprobar los datos del proveedor](../create-edit.md#provider-data-comparison)).

## ⚠️ Limitaciones

- **ISIN** también funciona como **Identifier Type**, pero solo cuando Yahoo puede emparejarlo con un ticker: es preferible
  el ticker.
- **Los datos guardados antes de este comportamiento se quedan como estaban.** Si tienes un activo de Yahoo cuyos cierres se
  guardaron con anterioridad, siguen llevando el ajuste por dividendos del día en que se leyeron, y los dividendos
  de un valor en peniques siguen en peniques. Nada los reescribe por su cuenta: vuelve a ejecutar la **full Sync** del activo
  (el diálogo avisa antes de sobrescribir) y el histórico se lee de nuevo. Esto no cambia el
  comportamiento de los desdoblamientos que se describe abajo.
- **Limitación conocida: los desdoblamientos.** Tras un desdoblamiento de acciones, Yahoo reescribe los cierres pasados (y los dividendos) al
  nuevo número de acciones. Para el desdoblamiento 4:1 de Apple del 31 de agosto de 2020, el cierre del 28 de agosto de 2020 se da como
  124,81 en lugar de los 499 que realmente fue. Así, el valor de una posición en los días anteriores a un desdoblamiento puede salir
  dividido por el ratio del desdoblamiento (10 acciones × 124,81 = 1.248 en lugar de 4.990), y el rendimiento da un salto el
  día del desdoblamiento. Está prevista una corrección después de la 1.3.
- Yahoo puede limitar las peticiones frecuentes: LibreFolio entonces lo deja en pausa durante un rato y sigue mostrando los
  últimos precios guardados. A algunos tickers les faltan días.

## 🔗 Relacionado

- 🔌 **[Proveedores de activos](index.md)** — Compara los proveedores
- 🛠️ **Para desarrolladores: [Proveedor de Yahoo Finance](../../../developer/backend/assets/provider_yahoo_finance.md)** — Peticiones, almacenamiento en caché y eventos
