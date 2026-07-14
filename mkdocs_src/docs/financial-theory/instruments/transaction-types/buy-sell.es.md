# ![](../../../static/icons/transactions/buy.png){: width="32" style="vertical-align: middle;" } Compra y Venta ![](../../../static/icons/transactions/sell.png){: width="32" style="vertical-align: middle;" }

<div class="lf-screenshot-carousel" data-carousel="buy-sell" data-carousel-interval="4000" data-show-titles="true">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> COMPRA' alt="Compra">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VENTA' alt="Venta">
</div>

Los tipos de transacciones más fundamentales: la **compra** aumenta sus posiciones y disminuye el efectivo; la **venta** hace lo inverso y materializa una plusvalía o pérdida.

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

Cuando compra un activo, se crea un **lote** con:

- **Fecha**: Cuándo ocurrió la compra
- **Cantidad**: Número de acciones/unidades compradas
- **Precio unitario**: Precio por acción en el momento de la compra
- **Comisiones**: Cualquier comisión de transacción (comisión, spread, etc.)
- **Coste total**: `quantity × unit_price + fees`

### 💰 Venta

Cuando vende, LibreFolio empareja la venta con los lotes existentes utilizando **FIFO** (First In, First Out) para determinar:

$$
\text{Capital Gain} = (P_{sell} \times Q) - (P_{buy} \times Q) - \text{Fees}
$$

<div id="fifo-matching"></div>

!!! info "Emparejamiento FIFO"

    LibreFolio calcula el emparejamiento de lotes en **tiempo de ejecución** — no se persiste en la base de datos. Esto permite realizar análisis hipotéticos flexibles y el posible soporte futuro de otros métodos de emparejamiento (LIFO, identificación específica).

---

## 🔗 Relacionado

- 📊 **[Precio Medio Ponderado (PMP)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Coste medio por unidad a través de múltiples compras
- 💰 **[Tributación](../../fundamentals/taxation.md)** — Plusvalías, métodos de emparejamiento, compensación de pérdidas
- 📈 **[Rentabilidades](../../fundamentals/returns.md)** — Medición del rendimiento de la inversión
