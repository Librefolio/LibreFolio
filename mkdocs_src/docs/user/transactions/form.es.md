# 📝 Formulario de Transacción

El Formulario de Transacción se abre cada vez que **creas** o **editas** una transacción. Se adapta dinámicamente al tipo de transacción seleccionado, mostrando únicamente los campos relevantes para esa operación.

---

## 🏷️ Tipos de Transacción

Para obtener una definición conceptual detallada de cada operación, consulta la [guía de Teoría Financiera](../../financial-theory/instruments/transaction-types/index.md).

<div class="lf-screenshot-carousel" data-carousel="transactions" data-carousel-interval="3000" data-show-titles="true">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> COMPRA' alt="Compra">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VENTA' alt="Venta">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-dividend" data-title='<img src="/LibreFolio/static/icons/transactions/dividend.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DIVIDENDO' alt="Dividendo">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-deposit" data-title='<img src="/LibreFolio/static/icons/transactions/deposit.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DEPÓSITO' alt="Depósito">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-adjustment" data-title='<img src="/LibreFolio/static/icons/transactions/adjustment.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> AJUSTE' alt="Ajuste">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRANSFERENCIA' alt="Transferencia de Activos">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-fxconversion" data-title='<img src="/LibreFolio/static/icons/transactions/fx-conversion.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> CONVERSIÓN FX' alt="Conversión FX">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-cash-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/cash-transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRANSFERENCIA DE EFECTIVO' alt="Transferencia de Efectivo">
</div>

### Transacciones Simples

Estas operan de forma independiente en una sola cuenta de bróker.

| Tipo | Descripción | Guía Teórica |
|------|-------------|--------------|
| ![](../../static/icons/transactions/buy.png){: width="24" style="vertical-align: middle;" } **COMPRA / VENTA** ![](../../static/icons/transactions/sell.png){: width="24" style="vertical-align: middle;" } | Compra o venta de un activo | [📖 Leer](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/deposit.png){: width="24" style="vertical-align: middle;" } **DEPÓSITO / RETIRO** ![](../../static/icons/transactions/withdrawal.png){: width="24" style="vertical-align: middle;" } | Añadir o retirar efectivo de una cuenta de bróker | [📖 Leer](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/dividend.png){: width="24" style="vertical-align: middle;" } **DIVIDENDO / INTERÉS** ![](../../static/icons/transactions/interest.png){: width="24" style="vertical-align: middle;" } | Rendimiento de activos de renta variable o renta fija | [📖 Leer](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/fee.png){: width="24" style="vertical-align: middle;" } **COMISIÓN / IMPUESTO** ![](../../static/icons/transactions/tax.png){: width="24" style="vertical-align: middle;" } | Costos como comisiones de bróker o impuestos | [📖 Leer](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/adjustment.png){: width="24" style="vertical-align: middle;" } **AJUSTE** | Corrección manual de saldos | [📖 Leer](../../financial-theory/instruments/transaction-types/adjustment.md) |

### Transacciones Compuestas

Estas representan movimientos **entre** cuentas o monedas. Generan dos asientos vinculados que se equilibran entre sí.

| Tipo | Descripción | Guía Teórica |
|------|-------------|--------------|
| ![](../../static/icons/transactions/transfer.png){: width="24" style="vertical-align: middle;" } **TRANSFERENCIA** | Movimiento de activos entre dos brókers | [📖 Leer](../../financial-theory/instruments/transaction-types/transfer.md) |
| ![](../../static/icons/transactions/cash-transfer.png){: width="24" style="vertical-align: middle;" } **TRANSFERENCIA DE EFECTIVO** | Transferencia bancaria entre brókers | [📖 Leer](../../financial-theory/instruments/transaction-types/cash-transfer.md) |
| ![](../../static/icons/transactions/fx-conversion.png){: width="24" style="vertical-align: middle;" } **CONVERSIÓN FX** | Conversión de divisa dentro de un bróker | [📖 Leer](../../financial-theory/instruments/transaction-types/fx-conversion.md) |

---

## 📋 La Interfaz del Formulario

El formulario está diseñado para ser intuitivo y dinámico. Cuando selecciona un **Tipo de Transacción**, el formulario se ajusta automáticamente para mostrar solo los campos relevantes. 

- **Detalles Básicos:** Fecha, Tipo, Moneda y Monto.
- **Especificaciones del Activo:** Si la transacción involucra un activo (como COMPRA o VENTA), aparecerán campos para seleccionar el activo, ingresar la cantidad y establecer el precio unitario.
- **Panel de Previsualización (WAC):** Para las operaciones que afectan su cartera, aparece una previsualización en tiempo real en la parte inferior. Muestra su base de costo actual, la nueva base de costo proyectada y cualquier ganancia/pérdida realizada.

> **💡 Note:** El sistema gestiona automáticamente los cálculos estándar por usted (como multiplicar la cantidad por el precio unitario) para que no tenga que hacer las cuentas manualmente.

---

## 🔄 Transacciones Compuestas

**TRANSFERENCIA** y **CONVERSIÓN FX** son *compuestas* — vinculan dos asientos:

- **TRANSFERENCIA**: especifica un **bróker de origen** y un **bróker de destino**, además del activo y la cantidad. LibreFolio registra ambos asientos de forma atómica.
- **CONVERSIÓN FX**: especifica el **monto de la moneda de origen** y el **monto de la moneda de destino** dentro del mismo bróker.

Para dividir una transacción compuesta nuevamente en dos transacciones independientes, utilice la operación [División](index.md) en la tabla de transacciones.

---

## 🔗 Relacionado

- 📋 **[Tabla de Transacciones](index.md)** — Vista de lista, filtrado, operaciones masivas
- 📥 **[Importar desde Bróker](import/index.md)** — Evite la entrada manual con la importación BRIM
