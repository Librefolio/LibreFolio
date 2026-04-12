# 📅 Eventos de Activos

Los eventos de activos representan sucesos que afectan al activo **globalmente**, no a nivel de cartera. Son distintos de las [transacciones](../../../financial-theory/instruments/transaction-types/index.md), que rastrean lo que sucede en la cartera de un usuario.

Para un análisis profundo de cada tipo de evento —incluyendo el impacto en el mercado, fórmulas y ejemplos prácticos— consulte la sección **[Eventos de Activos (Teoría Financiera)](../../../financial-theory/instruments/asset-events/index.md)**.

---

## 📊 Tipos de Eventos

| Tipo | Icono | Efecto en el Precio | Descripción | Más Información |
|------|------|----------------|-------------|-----------|
| **Dividendo** | 💰 | El precio disminuye en el valor del evento (ex-date) | Distribución de efectivo de acciones o ETF | [📖](../../../financial-theory/instruments/asset-events/dividend.md) |
| **Interés** | 📈 | El precio disminuye en el valor del evento | Pago de intereses de un instrumento de deuda o préstamo | [📖](../../../financial-theory/instruments/asset-events/interest.md) |
| **Desdoblamiento** | ✂️ | Cambia la cantidad, no el valor total | División de acciones o unidades | [📖](../../../financial-theory/instruments/asset-events/split.md) |
| **Ajuste de Precio** | 📊 | Cambio algebraico (+/-) | Cambio de valor no monetario: deterioro de valor, haircut, re-rating | [📖](../../../financial-theory/instruments/asset-events/price-adjustment.md) |
| **Liquidación al Vencimiento** | 🏁 | Retorno final de capital | El activo alcanza su vencimiento — no hay más cálculos de precio | [📖](../../../financial-theory/instruments/asset-events/maturity-settlement.md) |

## 📈 Marcadores de Eventos en el Gráfico

Los eventos aparecen como **marcadores de colores** en el [gráfico de precios](chart.md). Cada tipo de evento tiene un color e icono distintos. Pase el cursor sobre un marcador para ver los detalles del evento (fecha, tipo, valor, moneda).

## ⚙️ Origen de los Eventos

Los eventos pueden generarse de dos maneras:

### 1. Generados por el proveedor (automático)

Algunos proveedores producen eventos durante la sincronización:

- **[Scheduled Investment](../providers/scheduled-investment.md)**: genera eventos `INTEREST` y `PRICE_ADJUSTMENT` a partir de la configuración del calendario de intereses.
- **[Yahoo Finance](../providers/yahoo-finance.md)**: puede producir eventos `DIVIDEND` a partir de datos históricos.

Los eventos generados por el proveedor tienen un `provider_assignment_id` y se actualizan automáticamente durante la sincronización (deduplicación DELETE + INSERT basada en `asset_id, date, type`).

### 2. Creados por el usuario (manual)

Los eventos también pueden añadirse manualmente a través del modal de edición del activo. Los eventos manuales no tienen `provider_assignment_id` y nunca se eliminan automáticamente durante la sincronización.

---

## 🧮 Cómo Afectan los Eventos al Cálculo del Precio

Para el proveedor **Scheduled Investment**, los eventos son integrales para el cálculo del precio:

```
price(d) = initial_value + accrued_interest − Σ(INTEREST events) + Σ(PRICE_ADJUSTMENT events)
```

Para activos con precio de mercado (Yahoo Finance, justETF), los eventos son informativos: explican caídas repentinas de precio (fechas ex-dividendo) pero no modifican directamente el precio obtenido.

---

## 🔗 Relacionado

- 📈 **[Gráfico Interactivo](chart.md)** — Marcadores de eventos en el gráfico
- ✏️ **[Editor de Datos](data-editor.md)** — Gestión manual de eventos con importación CSV
- 🧮 **[Scheduled Investment](../providers/scheduled-investment.md)** — Proveedor que genera eventos a partir de calendarios de intereses
- 📚 **[Eventos de Activos (Teoría Financiera)](../../../financial-theory/instruments/asset-events/index.md)** — Análisis detallado de cada tipo de evento
- 💸 **[Tipos de Transacciones (Teoría Financiera)](../../../financial-theory/instruments/transaction-types/index.md)** — Transacciones vs eventos
