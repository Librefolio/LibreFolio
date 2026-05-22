# ![](../../../static/icons/transactions/buy.png){: width="32" style="vertical-align: middle;" } Compra y Venta

Los tipos de transacción más fundamentales: **comprar** aumenta las posiciones y disminuye el efectivo; **vender** hace lo contrario y materializa una plusvalía o pérdida.

---

## 🔑 Propiedades Clave

| Propiedad | Compra | Venta |
|----------|-----|------|
| **Código** | `BUY` | `SELL` |
| **Efecto en efectivo** | ⬇️ Disminuye | ⬆️ Aumenta |
| **Efecto en activo** | ⬆️ Aumenta posiciones | ⬇️ Disminuye posiciones |
| **Evento fiscal** | No | Sí (materializa plusvalía/pérdida) |

---

## 📊 Cómo Funciona

### 🛒 Compra

Al comprar un activo, se crea un **lote** con:

- **Fecha**: Cuándo ocurrió la compra
- **Cantidad**: Número de acciones/unidades compradas
- **Precio unitario**: Precio por acción al momento de la compra
- **Comisiones**: Cualquier tarifa de transacción (comisión, spread, etc.)
- **Costo total**: `quantity × unit_price + fees`

### 💰 Venta

Al vender, LibreFolio empareja la venta con los lotes existentes utilizando **FIFO** (First In, First Out) para determinar:

$$
\text{Plusvalía} = (P_{sell} \times Q) - (P_{buy} \times Q) - \text{Fees}
$$

!!! info "Emparejamiento FIFO"

    LibreFolio calcula el emparejamiento de lotes en **tiempo de ejecución** — no se persiste en la base de datos. Esto permite realizar análisis hipotéticos flexibles y un posible soporte futuro para otros métodos de emparejamiento (LIFO, identificación específica).

---

## 🔗 Relacionado

- 📊 **[Costo Promedio Ponderado (WAC)](../../portfolio-theory/weighted-average-cost.md)** — Costo promedio por unidad a través de múltiples compras
- 💰 **[Tributación](../../fundamentals/taxation.md)** — Plusvalías, métodos de emparejamiento, compensación de pérdidas
- 📈 **[Rendimientos](../../fundamentals/returns.md)** — Medición del rendimiento de la inversión
