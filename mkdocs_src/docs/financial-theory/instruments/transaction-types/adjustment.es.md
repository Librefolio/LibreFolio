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

    Dos filas de `ADJUSTMENT` con **cantidades opuestas**, **mismo activo** y **brókeres diferentes** pueden ser **promovidas** a un par de Transferencia de Activos. Esto es útil cuando inicialmente registraste ajustes separados y posteriormente deseas vincularlos como una transferencia. Ninguna de las dos filas puede estar vinculada a un evento del activo, por ejemplo un desdoblamiento: una transferencia no puede llevar ese vínculo, así que LibreFolio no sugiere ni acepta esa promoción.

---

## 📐 Impacto en el coste base

Los ajustes con cantidad positiva **incrementan** el recuento de lotes (FIFO). El coste base de los lotes creados mediante ajustes depende de si se proporciona una **Anulación del coste base (Cost Basis Override)**:

- **Con anulación**: el valor especificado se utiliza como el **coste de adquisición por unidad** (PMC — Precio Medio de Compra); una anulación de **cero** registra una adquisición gratuita, como un airdrop
- **Sin anulación**: el lote FIFO se abre a coste cero, pero el coste medio (PMC) trata el coste como **desconocido**, no gratuito: las unidades se suman a la posición sin coste, su PMC queda incompleto hasta que se cierra la posición, el Panel muestra su coste medio y su P&L no realizado como no disponibles, y un aviso de calidad de datos nombra el activo (ver [Anulación del coste base](../../technical-analysis/performance-metrics/weighted-average-cost.md#cost-basis-override))

Un ajuste positivo no se puede guardar sin un coste base: introduce uno, o elige **Auto**, que guarda el coste medio de la posición a la que se suman las unidades (cero si todavía no tiene ninguna). Dos tipos de filas pueden seguir sin él: un ajuste vinculado a un **desdoblamiento**, que Auto guarda sin coste base porque el desdoblamiento conserva el coste ya mantenido y lo reparte sobre la nueva cantidad, y las filas guardadas antes de que el coste base fuera obligatorio.

!!! info "Valor por unidad"

    La Anulación del coste base es el costo promedio **por una sola unidad** del activo.
    Para obtener el costo total del bloque transferido, multiplica por la cantidad:

    $$\text{Costo total} = \text{PMP} \times \text{cantidad}$$

### 🏦 Coste base automático en transferencias y cargas iniciales

Al transferir activos entre brókeres, LibreFolio **calcula automáticamente** la Anulación del coste base en el lado receptor utilizando el **Precio Medio de Compra (PMC)** de la posición del bróker de origen. Las cargas iniciales de una importación de bróker pueden fijarla directamente a partir del informe de origen. El valor es siempre **por unidad**, no el valor total de la posición; para una instantánea con valor fiscal total \(C\) y cantidad \(q\), los plugins guardan:

$$\text{Cost Basis Override} = \frac{C}{q}$$

Esto registra capital en especie, no P&L: el ajuste crea o modifica lotes, pero no genera una aportación de efectivo ni una ganancia realizada.

!!! tip "Más información"

    Para ver la fórmula completa, ejemplos y casos especiales, consulta la página dedicada:
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

        Al anular manualmente el coste base, el usuario es responsable de la exactitud del valor. LibreFolio no valida los montos de anulación frente a las reglas fiscales; consulta a un asesor fiscal para obtener orientación específica de tu jurisdicción.

---

## 🔗 Relacionados

- 📊 **[Precio Medio de Compra (PMC)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Cómo se calcula el coste base automático
- 🔄 **[Transferencia de Activos](transfer.md)** — Dos ajustes vinculados pueden promoverse a una transferencia
- 🛒 **[Compra y Venta](buy-sell.md)** — Transacciones estándar de activos con efectivo
- 💰 **[Comisión e Impuesto](fee.md)** — Correcciones solo de efectivo (usa Comisión/Impuesto en lugar de Ajuste)
