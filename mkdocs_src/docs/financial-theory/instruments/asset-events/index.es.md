# 📅 Eventos de Activos

Los eventos de activos representan **acciones corporativas o sucesos financieros programados** que afectan a un activo de manera global, independientemente de la cartera de cualquier inversor individual. Son distintos de las [transacciones](../transaction-types/index.md), que rastrean lo que sucede a nivel de cartera (por ejemplo, cuando un usuario compra o vende acciones).

Comprender los eventos de activos es esencial para un análisis de precios preciso, el cálculo del rendimiento total y la interpretación de los gráficos históricos.

---

## 📊 Descripción General de Tipos de Eventos

| Tipo | Emoji | Impacto en el Precio | Activos Típicos | Detalles |
|------|-------|----------------|----------------|---------|
| **Dividendo** | 💰 | El precio cae según el monto del dividendo (ex-date) | Acciones, ETF | [📖](dividend.md) |
| **Interés** | 📈 | El devengo reduce el rendimiento restante | Bonos, Préstamos, Renta fija | [📖](interest.md) |
| **Split** | ✂️ | El precio se divide, la cantidad se multiplica | Acciones, ETF | [📖](split.md) |
| **Ajuste de Precio** | 📊 | Cambio algebraico (+/−) al valor razonable | Bonos, Activos ilíquidos | [📖](price-adjustment.md) |
| **Liquidación por Vencimiento** | 🏁 | Retorno final de capital, sin valoraciones posteriores | Bonos, Depósitos a plazo | [📖](maturity-settlement.md) |

---

## 🔄 Eventos vs Transacciones

| Concepto | Eventos | Transacciones |
|---------|--------|-------------|
| **Alcance** | Global — afecta al activo | Personal — afecta a la cartera de un usuario |
| **Ejemplo** | "Apple declaró un dividendo de $0.25 el 2024-05-10" | "Recibí $12.50 de mis 50 acciones de AAPL" |
| **Efecto en el gráfico** | Marcador en el gráfico de precios | No visible en el gráfico de precios |
| **Quién los crea** | Proveedor (automático) o usuario (manual) | Importación desde reportes del bróker (BRIM) |

---

## ⚙️ Fuentes de Eventos

### 🤖 Generados por el proveedor (automático)

Algunos proveedores generan eventos durante la sincronización de datos:

- **Scheduled Investment**: genera eventos `INTEREST` y `PRICE_ADJUSTMENT` a partir del calendario de intereses configurado
- **Yahoo Finance**: puede generar eventos `DIVIDEND` a partir de datos históricos

Los eventos generados por el proveedor tienen un `provider_assignment_id` y se actualizan automáticamente durante la sincronización (deduplicación basada en `asset_id + date + type`).

### ✏️ Creados por el usuario (manual)

Los eventos pueden añadirse manualmente a través del **Editor de Datos** o mediante **Importación de CSV**. Los eventos manuales no tienen `provider_assignment_id` y nunca se eliminan automáticamente durante la sincronización.

---

## 📈 Marcadores de Eventos en el Gráfico

Los eventos aparecen como **marcadores en forma de diamante de colores** (◆) en el gráfico de precios interactivo. Cada tipo de evento tiene un color distinto. Pase el cursor sobre un marcador para ver los detalles completos (fecha, tipo, valor, moneda, notas).

Hacer doble clic en un marcador de evento mientras el Editor de Datos está abierto **desplazará la vista directamente a la fila de ese evento** en la pestaña de Eventos.

---

## 🔗 Relacionado

- 📈 **[Gráfico Interactivo](../../../user/assets/detail/chart.md)** — Marcadores de eventos en el gráfico
- ✏️ **[Editor de Datos](../../../user/assets/detail/data-editor.md)** — Gestión manual de eventos
- 💸 **[Tipos de Transacciones](../transaction-types/index.md)** — Operaciones a nivel de cartera
