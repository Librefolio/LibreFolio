# 🧮 ![](../../../static/icons/transactions/adjustment.png){: width="32" style="vertical-align: middle;" } Ajuste

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-adjustment" alt="Formulario de transacción — Ajuste">
</div>

Los **ajustes** son correcciones independientes de la cantidad de un activo. No implican efectivo en el esquema de transacciones incluido: la cantidad cambia, el efectivo no. A diferencia de los tipos emparejados (transferencia de activos, transferencia de fondos, conversión FX), cada ajuste es una fila única e independiente.

---

## 🔑 Propiedades clave

| Propiedad | Valor |
|----------|-------|
| **Código** | `ADJUSTMENT` |
| **Efecto en efectivo** | Ninguno — `ADJUSTMENT` no implica efectivo |
| **Efecto en el activo** | Obligatorio (± cualquier cantidad) |
| **Evento fiscal** | No |

---

## 📊 Casos de uso

Los ajustes se usan cuando ningún otro tipo de transacción encaja:

- **Corregir errores de importación** — p. ej., una importación del bróker omitió una acción corporativa
- **Desdoblamientos / desdoblamientos inversos de acciones** — ajustar la cantidad sin movimiento de efectivo
- **Regalos** — recibir o entregar acciones
- **Posiciones heredadas o por sucesión** — los valores llegan en especie, sin movimiento de efectivo del bróker
- **Configuración del saldo inicial** — iniciar una cartera a partir de una instantánea
- **Acciones corporativas** no cubiertas por otros tipos (escisiones, fusiones, etc.)

Ejemplos importados: las instantáneas `patrimonio` de Intesa Sanpaolo usan `ADJUSTMENT`s positivos para sembrar posiciones existentes con un `cost_basis_override` por unidad; las filas de sucesión de Crédit Agricole (`GIRO ALTRO DOSSIER`, `VERS.TITOLI`) también se modelan como `ADJUSTMENT`s positivos y sin efectivo, no como `TRANSFER`s emparejados, porque el dossier de origen está fuera de LibreFolio.

!!! note "Promover a transferencia de activos"

    Dos filas `ADJUSTMENT` con **cantidades opuestas**, el **mismo activo** y **brókers diferentes** se pueden **promover** a un par de transferencias de activos. Esto resulta útil cuando registró inicialmente ajustes separados y más tarde quiere vincularlos como una transferencia. Ninguna de las dos filas puede estar vinculada a un evento del activo, por ejemplo un desdoblamiento: una transferencia no puede llevar ese vínculo, por lo que LibreFolio ni sugiere ni acepta tal promoción.

---

## 📐 Impacto en el coste base

Los ajustes con cantidad positiva **aumentan** el número de lotes (FIFO). El coste base
de los lotes creados por un ajuste depende de si se proporciona una **Sobrescritura del coste base**:

- **Con sobrescritura**: el valor especificado se usa como **coste de adquisición por unidad** (PMC — precio medio de compra), en la moneda propia del coste base, que es también la moneda del lote FIFO que abre el ajuste (no la moneda propia de la fila, a menudo vacía ya que un ajuste no mueve efectivo); una sobrescritura de **cero** registra una adquisición gratuita, como un airdrop
- **Sin sobrescritura**: el lote FIFO se abre con coste cero, pero el precio medio de compra (PMC) trata el coste como **desconocido**, no como gratuito: las unidades se incorporan a la posición sin un coste, su PMC permanece incompleto hasta que se cierra la posición, el panel muestra su precio medio de compra y su P&L no realizado como no disponibles, y un aviso de calidad de datos señala el activo (véase [Sobrescritura del coste base](../../technical-analysis/performance-metrics/weighted-average-cost.md#cost-basis-override))

Un ajuste positivo no se puede guardar sin un coste base: introdúzcalo, o elija **Auto**, que almacena el precio medio de compra de la posición a la que se incorporan las unidades (cero si aún no tiene ninguna). Dos tipos de filas pueden seguir sin él: un ajuste vinculado a un **desdoblamiento**, que Auto guarda sin coste base porque el desdoblamiento conserva el coste ya mantenido y lo reparte sobre la nueva cantidad, y las filas guardadas antes de que el coste base fuera obligatorio.

!!! info "Valor por unidad"

    La Sobrescritura del coste base es el precio medio de compra **por unidad individual** del activo.
    Para obtener el coste total del bloque transferido, multiplique por la cantidad:

    $$\text{Coste total} = \text{PMC} \times \text{cantidad}$$

### 📤 Ajustes salientes {: #outgoing-adjustments }

Los ajustes con cantidad negativa **disminuyen** la posición: unidades regaladas, enviadas a una cuenta que LibreFolio no rastrea o eliminadas por una corrección. Un ajuste así **no tiene valor** — solo reduce la cantidad —, por lo que no admite **Sobrescritura del coste base**:

- **Capital y rentabilidades**: no sale capital, por lo que el ajuste no es un flujo para la [base de capital](../../technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#outgoing-adjustments), TWRR o MWRR: el valor de las unidades sale del NAV y las rentabilidades lo interpretan como una pérdida.
- **Precio medio de compra**: la posición cede el precio medio de compra de esas unidades, por lo que el precio medio de compra (PMC) de lo que queda no cambia.
- **Realizado**: las unidades salen a **cero**, por lo que el ajuste registra un P&L realizado igual al negativo de su precio medio de compra, $-q \times \text{PMC}$ en el panel. Los lotes FIFO consumen los lotes abiertos del bróker empezando por los más antiguos, como hace una venta, y los cierran a cero: $q$ unidades tomadas de un lote registran un P&L realizado de $-q \times \text{CosteUnitarioLote}$, sin ingresos.

Para registrar unidades que salieron a cambio de dinero, utilice una **Venta**. La API rechaza un coste base en un ajuste saliente (`costBasisNotAllowed`); uno almacenado en una fila así por una versión anterior permanece en la base de datos pero se ignora. Un ajuste vinculado a un **desdoblamiento** es la excepción: el desdoblamiento solo reparte el coste ya mantenido sobre la nueva cantidad y no realiza nada.

!!! example "Dos acciones regaladas"

    Todos los importes están en la moneda del informe. Compre 10 acciones a 50 (invertido 500); el precio sube a 80, así que la posición vale 800 y su P&L total es $800 - 500 = +300$. Un ajuste de −2 acciones regala dos:

    - quedan 8 acciones, por valor de $8 \times 80 = 640$; el capital invertido sigue siendo 500 y el precio medio de compra 50;
    - realizado: $0 - 2 \times 50 = -100$; no realizado: $8 \times (80 - 50) = +240$;
    - P&L total: $640 - 500 = +140$, es decir $-100 + 240$;
    - el TWRR del día: $640 / 800 - 1 = -20\%$, ya que ningún flujo compensa el valor que salió.

### 🏦 Coste base automático en transferencias y datos semilla

Al transferir activos entre brókers, LibreFolio **calcula automáticamente** la Sobrescritura del coste base en el lado receptor usando el **precio medio de compra (PMC)** de la posición del bróker de origen. Los datos semilla de importación del bróker pueden, en su lugar, establecerla directamente a partir del informe de origen. El valor es siempre **por unidad**, no el valor total de la posición; para una instantánea con valor fiscal total \(C\) y cantidad \(q\), los plugins almacenan:

$$\text{Sobrescritura del coste base} = \frac{C}{q}$$

Esto registra capital en especie, no P&L: el ajuste crea o modifica lotes pero no crea una aportación de efectivo ni una plusvalía realizada.

!!! tip "Más información"

    Para ver la fórmula completa, ejemplos y casos límite, consulte la página dedicada:
    **[📊 Precio medio de compra (PMC)](../../technical-analysis/performance-metrics/weighted-average-cost.md)**

??? note "✏️ Cuándo sobrescribir manualmente"

    La fórmula automática funciona para el caso estándar (mismo régimen fiscal, sin eventos fiscales
    en la transferencia). En los siguientes escenarios el usuario debe establecer el valor manualmente:

    | Escenario | Qué establecer |
    |----------|------------|
    | **Transferencia normal** | Mantenga el coste en **Auto** — calculado a partir de sus compras |
    | **Impuesto de salida** | Valor de mercado en la fecha de la transferencia (según la jurisdicción) |
    | **Herencia** | Valor razonable de mercado en la fecha del fallecimiento (o base incrementada) |
    | **Regalo** | Coste base original del donante (base de arrastre) |
    | **Acción corporativa** | Coste base ajustado según los términos de la acción corporativa |

    !!! warning "Responsabilidad del usuario"

        Al sobrescribir manualmente el coste base, el usuario es responsable de la
        exactitud del valor. LibreFolio no valida los importes sobrescritos
        frente a las normas fiscales; consulte a un asesor fiscal para obtener orientación específica de su jurisdicción.

---

## 🔗 Relacionado

- 📊 **[Precio medio de compra (PMC)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Cómo se calcula el coste base automático
- 🔄 **[Transferencia de activos](transfer.md)** — Dos ajustes vinculados se pueden promover a una transferencia de activos
- 🛒 **[Compra y venta](buy-sell.md)** — Transacciones estándar de activos con efectivo
- 💰 **[Comisión e impuesto](fee.md)** — Correcciones solo de efectivo (utilice Comisión/Impuesto en lugar de Ajuste)
