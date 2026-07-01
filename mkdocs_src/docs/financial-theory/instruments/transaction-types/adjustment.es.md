# ![](../../../static/icons/transactions/adjustment.png){: width="32" style="vertical-align: middle;" } Ajuste

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-adjustment" alt="Transaction Form — Adjustment">
</div>

Los **Ajustes** son un tipo de transacción comodín para correcciones manuales de los saldos de efectivo o de activos. A diferencia de los tipos emparejados (Transferencia, Transferencia de Efectivo, Conversión de FX), los ajustes son **independientes**: cada ajuste es una fila única e independiente.

---

## 🔑 Propiedades Clave

| Propiedad | Valor |
|----------|-------|
| **Código** | `ADJUSTMENT` |
| **Efecto en efectivo** | Opcional (± cualquier cantidad) |
| **Efecto en activo** | Obligatorio (± cualquier cantidad) |
| **Evento fiscal** | No |

---

## 📊 Casos de Uso

Los ajustes se utilizan cuando ningún otro tipo de transacción encaja:

- **Corrección de errores de importación** — p. ej., una importación de un bróker omitió una acción corporativa
- **Divisiones / divisiones inversas de acciones** — ajustar la cantidad sin movimiento de efectivo
- **Regalos** — recibir o dar acciones
- **Configuración de saldo inicial** — arranque de una cartera a partir de una instantánea
- **Acciones corporativas** no cubiertas por otros tipos (spinoffs, fusiones, etc.)

!!! note "Promover a Transferencia"

    Dos filas de `ADJUSTMENT` con **cantidades opuestas**, **mismo activo** y **brókeres diferentes** pueden ser **promovidas** a un par de Transferencia de Activos. Esto es útil cuando inicialmente registró ajustes separados y posteriormente desea vincularlos como una transferencia.

---

## 📐 Impacto en la Base de Costo

Los ajustes con cantidad positiva **incrementan** el recuento de lotes (FIFO). La base de costo para los lotes creados mediante ajustes depende de si se proporciona una **Anulación de la Base de Costo (Cost Basis Override)**:

- **Con anulación**: el valor especificado se utiliza como el **costo de adquisición por unidad** (PMP — Precio Medio Ponderado)
- **Sin anulación**: el lote se crea con costo cero (adquisición gratuita — p. ej. regalos, airdrops)

!!! info "Valor por unidad"

    La Anulación de la Base de Costo es el costo promedio **por una sola unidad** del activo.
    Para obtener el costo total del bloque transferido, multiplique por la cantidad:

    $$\text{Costo total} = \text{PMP} \times \text{cantidad}$$

### 🏦 Base de Costo Automática en Transferencias

Al transferir activos entre brókeres, LibreFolio **calcula automáticamente** la Anulación de la Base de Costo en el lado receptor utilizando el **Precio Medio Ponderado (PMP)** de la posición del bróker de origen.

!!! tip "Más información"

    Para ver la fórmula completa, ejemplos y casos especiales, consulte la página dedicada:
    **[📊 Precio Medio Ponderado (PMP)](../../technical-analysis/performance-metrics/weighted-average-cost.md)**

??? note "✏️ Cuándo Anular Manualmente"

    La fórmula automática funciona para el caso estándar (mismo régimen fiscal, sin eventos fiscales en la transferencia). En los siguientes escenarios, el usuario debe establecer el valor manualmente:

    | Escenario | Qué establecer |
    |----------|------------|
    | **Transferencia normal** | Dejar vacío — calculado automáticamente |
    | **Impuesto de salida (Exit Tax)** | Valor de mercado en la fecha de transferencia (específico de la jurisdicción) |
    | **Herencia** | Valor justo de mercado en la fecha del fallecimiento (o base actualizada) |
    | **Regalo** | Base de costo original del donante (base transferida) |
    | **Acción corporativa** | Base ajustada según los términos de la acción corporativa |

    !!! warning "Responsabilidad del Usuario"

        Al anular manualmente la base de costo, el usuario es responsable de la exactitud del valor. LibreFolio no valida los montos de anulación frente a las reglas fiscales; consulte a un asesor fiscal para obtener orientación específica de su jurisdicción.

---

## 🔗 Relacionados

- 📊 **[Precio Medio Ponderado (PMP)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Cómo se calcula la base de costo automática
- 🔄 **[Transferencia de Activos](transfer.md)** — Dos ajustes vinculados pueden promoverse a una transferencia
- 🛒 **[Compra y Venta](buy-sell.md)** — Transacciones estándar de activos con efectivo
- 💰 **[Comisión e Impuesto](fee.md)** — Correcciones solo de efectivo (use Comisión/Impuesto en lugar de Ajuste)
