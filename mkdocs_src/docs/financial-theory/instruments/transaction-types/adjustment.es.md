# 🧮 ![](../../../static/icons/transactions/adjustment.png){: width="32" style="vertical-align: middle;" } Ajuste

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-adjustment" alt="Formulario de transacción — Ajuste">
</div>

Los **Ajustes** son correcciones independientes de la cantidad de un activo. En el esquema de transacciones no mueven efectivo: cambia la cantidad, el efectivo no. A diferencia de los tipos emparejados (Transferencia, Transferencia de fondos, Conversión de FX), cada ajuste es una fila única e independiente.

---

## 🔑 Propiedades Clave

| Propiedad | Valor |
|----------|-------|
| **Código** | `ADJUSTMENT` |
| **Efecto en efectivo** | Ninguno — `ADJUSTMENT` no mueve efectivo |
| **Efecto en activo** | Obligatorio (± cualquier cantidad) |
| **Evento fiscal** | No |

---

## 📊 Casos de Uso

Los ajustes se utilizan cuando ningún otro tipo de transacción encaja:

- **Corrección de errores de importación** — p. ej., una importación de un bróker omitió una acción corporativa
- **Desdoblamientos / desdoblamientos inversos de acciones** — ajustar la cantidad sin movimiento de efectivo
- **Regalos** — recibir o dar acciones
- **Herencias o sucesiones** — los valores llegan en especie, sin movimiento de efectivo en el bróker
- **Configuración de saldo inicial** — arranque de una cartera a partir de una instantánea
- **Acciones corporativas** no cubiertas por otros tipos (spinoffs, fusiones, etc.)

Ejemplos de importación: las instantáneas `patrimonio` de Intesa Sanpaolo usan `ADJUSTMENT` positivos para cargar las posiciones existentes con un `cost_basis_override` por unidad; las filas de sucesión de Crédit Agricole (`GIRO ALTRO DOSSIER`, `VERS.TITOLI`) también se modelan como `ADJUSTMENT` positivos sin efectivo, no como pares de `TRANSFER`, porque el dossier de origen está fuera de LibreFolio.

!!! note "Promover a Transferencia"

    Dos filas de `ADJUSTMENT` con **cantidades opuestas**, **mismo activo** y **brókeres diferentes** pueden ser **promovidas** a un par de Transferencia de Activos. Esto es útil cuando inicialmente registró ajustes separados y posteriormente desea vincularlos como una transferencia.

---

## 📐 Impacto en el coste base

Los ajustes con cantidad positiva **incrementan** el recuento de lotes (FIFO). El coste base de los lotes creados mediante ajustes depende de si se proporciona una **Anulación del coste base (Cost Basis Override)**:

- **Con anulación**: el valor especificado se utiliza como el **costo de adquisición por unidad** (PMC — Precio Medio de Compra)
- **Sin anulación**: el lote se crea con costo cero (adquisición gratuita — p. ej. regalos, airdrops)

!!! info "Valor por unidad"

    La Anulación del coste base es el costo promedio **por una sola unidad** del activo.
    Para obtener el costo total del bloque transferido, multiplique por la cantidad:

    $$\text{Costo total} = \text{PMP} \times \text{cantidad}$$

### 🏦 Coste base automático en transferencias y cargas iniciales

Al transferir activos entre brókeres, LibreFolio **calcula automáticamente** la Anulación del coste base en el lado receptor utilizando el **Precio Medio de Compra (PMC)** de la posición del bróker de origen. Las cargas iniciales de una importación de bróker pueden fijarla directamente a partir del informe de origen. El valor es siempre **por unidad**, no el valor total de la posición; para una instantánea con valor fiscal total \(C\) y cantidad \(q\), los plugins guardan:

$$\text{Cost Basis Override} = \frac{C}{q}$$

Esto registra capital en especie, no P&L: el ajuste crea o modifica lotes, pero no genera una aportación de efectivo ni una ganancia realizada.

!!! tip "Más información"

    Para ver la fórmula completa, ejemplos y casos especiales, consulte la página dedicada:
    **[📊 Precio Medio de Compra (PMC)](../../technical-analysis/performance-metrics/weighted-average-cost.md)**

??? note "✏️ Cuándo Anular Manualmente"

    La fórmula automática funciona para el caso estándar (mismo régimen fiscal, sin eventos fiscales en la transferencia). En los siguientes escenarios, el usuario debe establecer el valor manualmente:

    | Escenario | Qué establecer |
    |----------|------------|
    | **Transferencia normal** | Dejar vacío — calculado automáticamente |
    | **Impuesto de salida (Exit Tax)** | Valor de mercado en la fecha de transferencia (específico de la jurisdicción) |
    | **Herencia** | Valor justo de mercado en la fecha del fallecimiento (o base actualizada) |
    | **Regalo** | Coste base original del donante (base transferida) |
    | **Acción corporativa** | Base ajustada según los términos de la acción corporativa |

    !!! warning "Responsabilidad del Usuario"

        Al anular manualmente el coste base, el usuario es responsable de la exactitud del valor. LibreFolio no valida los montos de anulación frente a las reglas fiscales; consulte a un asesor fiscal para obtener orientación específica de su jurisdicción.

---

## 🔗 Relacionados

- 📊 **[Precio Medio de Compra (PMC)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Cómo se calcula el coste base automático
- 🔄 **[Transferencia de Activos](transfer.md)** — Dos ajustes vinculados pueden promoverse a una transferencia
- 🛒 **[Compra y Venta](buy-sell.md)** — Transacciones estándar de activos con efectivo
- 💰 **[Comisión e Impuesto](fee.md)** — Correcciones solo de efectivo (use Comisión/Impuesto en lugar de Ajuste)
