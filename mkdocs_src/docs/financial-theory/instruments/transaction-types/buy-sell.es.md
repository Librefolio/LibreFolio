# ![](../../../static/icons/transactions/buy.png){: width="32" style="vertical-align: middle;" } Compra & Venta ![](../../../static/icons/transactions/sell.png){: width="32" style="vertical-align: middle;" }

<div class="lf-screenshot-carousel" data-carousel="buy-sell" data-carousel-interval="4000" data-show-titles="true">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> COMPRA' alt="Compra">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VENTA' alt="Venta">
</div>

Los tipos de transacciones más fundamentales: **comprar** aumenta tus posiciones y disminuye el efectivo; **vender** hace lo contrario y realiza una plusvalía o minusvalía.

---

## 🔑 Propiedades Clave

| Propiedad | Compra | Venta |
|-----------|--------|-------|
| **Código** | `BUY` | `SELL` |
| **Efecto en efectivo** | ⬇️ Disminuye | ⬆️ Aumenta |
| **Efecto en activos** | ⬆️ Aumenta posiciones | ⬇️ Disminuye posiciones |
| **Evento fiscal** | No | Sí (realiza plusvalía/minusvalía) |

---

## 📊 Cómo Funciona

### 🛒 Compra

Cuando compras un activo, se crea un **lote** con:

- **Fecha**: Cuándo ocurrió la compra
- **Cantidad**: Número de acciones/unidades compradas
- **Precio unitario**: Precio por acción en el momento de la compra
- **Comisiones**: Cualquier comisión de transacción (corretaje, diferencial, etc.)
- **Costo total**: `cantidad × precio_unitario + comisiones`

### 💰 Venta

Cuando vendes, LibreFolio empareja la venta con los lotes existentes usando **FIFO** (Primero en Entrar, Primero en Salir) para determinar:

$$
\text{Plusvalía} = (P_{venta} \times Q) - (P_{compra} \times Q) - \text{Comisiones}
$$

<div id="fifo-matching"></div>

!!! info "Emparejamiento FIFO"

    LibreFolio calcula el emparejamiento de lotes en **tiempo de ejecución** — no se persiste en la base de datos. Esto permite un análisis flexible de escenarios hipotéticos y posible soporte futuro para otros métodos de emparejamiento (LIFO, identificación específica).

---

## 🔗 Relacionados

- 📊 **[Precio Medio Ponderado (PMP)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Costo promedio por unidad a través de múltiples compras
- 💰 **[Impuestos](../../fundamentals/taxation.md)** — Plusvalías, métodos de emparejamiento, arrastre de pérdidas
- 📈 **[Rendimientos](../../fundamentals/returns.md)** — Medición del rendimiento de inversiones
