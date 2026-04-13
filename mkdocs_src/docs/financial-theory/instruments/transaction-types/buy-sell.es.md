# ![](../../../static/icons/transactions/buy.png){: width="32" style="vertical-align: middle;" } Compra y Venta

Los tipos de transacción más fundamentales: la **compra** aumenta sus posiciones y disminuye el efectivo; la **venta** hace lo contrario y materializa una plusvalía o pérdida.

---

## 🔑 Propiedades Clave

| Propiedad | Compra | Venta |
|----------|-----|------|
| **Código** | `BUY` | `SELL` |
| **Efecto en efectivo** | ⬇️ Disminuye | ⬆️ Aumenta |
| **Efecto en activo** | ⬆️ Aumenta las posiciones | ⬇️ Disminuye las posiciones |
| **Evento fiscal** | No | Sí (materializa plusvalía/pérdida) |

---

## 📊 Cómo Funciona

### 🛒 Compra

Cuando compra un activo, se crea un **lote** con:

- **Fecha**: Cuándo ocurrió la compra
- **Cantidad**: Número de acciones/unidades compradas
- **Precio unitario**: Precio por acción en el momento de la compra
- **Comisiones**: Cualquier tarifa de transacción (comisión, spread, etc.)
- **Costo total**: `quantity × unit_price + fees`

### 💰 Venta

Cuando vende, LibreFolio empareja la venta con los lotes existentes utilizando **FIFO** (First In, First Out) para determinar:

$$
\text{Plusvalía} = (P_{sell} \times Q) - (P_{buy} \times Q) - \text{Comisiones}
$$

!!! info "Emparejamiento FIFO"

    LibreFolio calcula el emparejamiento de lotes en **tiempo de ejecución** (runtime); no se persiste en la base de datos. Esto permite análisis de escenarios ("what-if") flexibles y el posible soporte futuro para otros métodos de emparejamiento (LIFO, identificación específica).

---

## 📐 Base de Costo

La base de costo de sus posiciones es el monto total que ha pagado, incluyendo las comisiones:

$$
\text{Base de Costo} = \sum_{i} (Q_i \times P_i + F_i)
$$

Esto se utiliza para calcular el P&L no realizado en cualquier momento:

$$
\text{P\&L no realizado} = \text{Valor Actual} - \text{Base de Costo}
$$

---

## 🔗 Relacionado

- 💰 **[Tributación](../../fundamentals/taxation.md)** — Plusvalías, métodos de emparejamiento, arrastre de pérdidas
- 📈 **[Rendimientos](../../fundamentals/returns.md)** — Medición del rendimiento de la inversión
