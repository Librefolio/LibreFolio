# 📊 Precio Medio de Compra (PMC)

## 💡 ¿Qué es el PMC?

El **Precio Medio de Compra** (PMC) es el coste unitario promedio de un activo en una cartera, ponderado por la cantidad adquirida a cada precio.

Responde a la pregunta: _"En promedio, ¿cuánto pagué por unidad por este activo?"_

!!! info "Otros nombres"

    - **PMC** — Prezzo Medio di Carico (Italia)
    - **ACB** — Average Cost Basis (Canadá, EE. UU.)
    - **CMP** — Coût Moyen Pondéré (Francia)

## 🧮 Fórmula

El PMC se calcula **iterativamente** a medida que cada transacción se procesa cronológicamente:

$$
PMC_{new} = \frac{PMC_{current} \times Q_{pool} + Coste_{unit} \times Q_{tx}}{Q_{pool} + Q_{tx}}
$$

Donde:

- $PMC_{current}$ = precio medio de compra actual antes de esta transacción
- $Q_{pool}$ = cantidad total mantenida en el pool antes de esta transacción
- $Coste_{unit}$ = coste de adquisición por unidad de la nueva transacción — lo que realmente se pagó, en la moneda en que se mantiene el PMC, convertido al tipo de cambio de la fecha de la propia transacción (ver [Manejo de múltiples monedas](#multi-currency-handling))
- $Q_{tx}$ = cantidad añadida por la nueva transacción

De manera equivalente, LibreFolio mantiene el coste total del pool $C_{pool}$ junto a su cantidad, con $PMC = C_{pool} / Q_{pool}$: una adquisición suma su coste, una reducción de $q$ unidades elimina $C_{pool} \cdot q / Q_{pool}$.

## ⚙️ Cómo calcula LibreFolio el PMC

LibreFolio utiliza un **algoritmo iterativo que tiene en cuenta el inventario** que procesa todas las transacciones válidas para un par (bróker, activo) dado en orden cronológico. El mismo algoritmo sirve a todas las pantallas que muestran un coste promedio: el Panel, la tabla de Posiciones, el análisis de lotes y la vista previa de transacción.

### 🏷️ Efectos de las transacciones

Cada transacción contribuye al cálculo del PMC de una de estas maneras:

| Efecto | Condición | Impacto en el PMC |
|--------|-----------|-------------------|
| **Ponderado** | `qty > 0` con un coste conocido mayor que cero | El PMC se mueve hacia el nuevo coste de adquisición |
| **Cantidad reducida** | `qty < 0` | Sale al PMC actual — PMC sin cambios, el pool se reduce |
| **Dilución** | `qty > 0` a coste cero | El pool crece, numerador sin cambios → PMC **disminuye** |
| **Desdoblamiento** | Ajuste vinculado a un evento de desdoblamiento | Cantidad reescalada, coste total sin cambios → PMC dividido por la proporción del desdoblamiento |
| **Coste desconocido** | `qty > 0` sin coste conocido: una transferencia o ajuste sin anulación del coste base | El pool crece sin coste — el PMC está **incompleto** (ver [Anulación del coste base](#cost-basis-override)) |

### 📅 Ordenación en el mismo día

Cuando múltiples transacciones ocurren en la misma fecha:

1. **Primero las adiciones** (qty > 0) — procesadas antes que las reducciones
2. **Segundo las reducciones** (qty < 0) — asegura que el pool no se vuelva transitoriamente negativo

### 🔻 Agotamiento del pool

- Cuando la cantidad llega a 0, la última reducción toma el **total** del coste restante, por lo que el coste total se conserva exactamente; el pool se reinicia desde cero, y una compra posterior abre un nuevo pool completo
- Una reducción mayor que el pool se limita a la cantidad disponible

## 📝 Ejemplos prácticos

??? example "Ejemplo 1: Dos compras — el PMC sube"

    | Fecha | Tipo | Cant. | Coste unitario | Cant. en pool | PMC |
    |-------|------|-------|----------------|---------------|-----|
    | 1 abr | COMPRA | 10 | $150 | 10 | $150.00 |
    | 15 abr | COMPRA | 5 | $180 | 15 | $160.00 |

    $$
    PMC = \frac{150 \times 10 + 180 \times 5}{10 + 5} = \frac{2400}{15} = 160.00
    $$

    La segunda compra a un precio más alto **hace subir el PMC**.

??? example "Ejemplo 2: Compra y luego venta — el PMC no cambia"

    | Fecha | Tipo | Cant. | Coste unitario | Cant. en pool | PMC |
    |-------|------|-------|----------------|---------------|-----|
    | 1 abr | COMPRA | 10 | $150 | 10 | $150.00 |
    | 15 abr | VENTA | -5 | (al PMC) | 5 | $150.00 |

    La VENTA elimina unidades al PMC actual ($150). El PMC permanece **sin cambios** — solo se reduce el pool.

??? example "Ejemplo 3: Adquisición a coste cero — Dilución"

    | Fecha | Tipo | Cant. | Coste unitario | Cant. en pool | PMC |
    |-------|------|-------|----------------|---------------|-----|
    | 1 abr | COMPRA | 10 | $150 | 10 | $150.00 |
    | 1 may | AJUSTE | +5 | $0 | 15 | $100.00 |

    $$
    PMC = \frac{150 \times 10 + 0 \times 5}{10 + 5} = \frac{1500}{15} = 100.00
    $$

    El PMC se **diluye** porque 5 unidades entraron a coste cero — un ajuste cuya anulación del coste base es cero, como un airdrop. Un desdoblamiento 3 por 2 vinculado a su evento de desdoblamiento alcanza los mismos $100.00 sin ninguna adquisición: el pool mantiene sus $1,500 y los reparte entre 15 unidades.

## 🔄 Anulación del coste base {: #cost-basis-override }

Para transferencias y ajustes, LibreFolio admite una **anulación del coste base**: un coste unitario, en una moneda de su elección, que representa el coste histórico de las unidades que entran. Una transferencia o ajuste que añade cantidad necesita una: el formulario de transacción lo requiere.

**Cuando se establece (modo manual):**

- La transacción entra en el cálculo del PMC como una adquisición ponderada normal que cuesta $\text{anulación} \times Q_{tx}$, convertida en la fecha de la transacción como cualquier compra
- Esto preserva la continuidad del coste entre brókers (por ejemplo, al transferir del bróker A al bróker B)
- Una anulación de **cero** es una adquisición gratuita: la dilución del Ejemplo 3

**Cuando falta:**

- El coste de esas unidades es **desconocido**, no cero: entran al pool sin ningún coste, y el PMC permanece incompleto hasta que se cierra la posición
- El Panel muestra el coste promedio y el P&L no realizado de esa posición como no disponibles y advierte sobre el coste base faltante; la vista previa de la transacción cuenta las unidades a cero (dilución)

**En modo automático (`cost_basis_mode = "auto"`):**

- LibreFolio calcula el PMC de la posición de origen — para una transferencia, la posición del bróker emisor cuando las unidades salieron (la fecha de transferencia saliente), antes del tramo saliente; para un ajuste, la posición misma en la fecha de la transacción, sin esta transacción — y lo almacena como la anulación
- A partir de entonces, la transacción es una adquisición ponderada ordinaria a ese coste unitario. Para un ajuste en la misma posición, el PMC permanece algebraicamente sin cambios, en la moneda en que se calculó:

$$
PMC_{new} = \frac{PMC \times Q_{pool} + PMC \times Q_{tx}}{Q_{pool} + Q_{tx}} = PMC
$$

!!! tip "Modo automático en la interfaz"

    En el formulario de transacción, el interruptor **Auto** calcula el valor cuando usted valida: la vista previa muestra el PMC sugerido y las transacciones de las que proviene, cada una con su efecto.

??? example "Ejemplo 4: Transferencia en modo automático — el coste sigue a las unidades"

    El bróker A tiene el pool del Ejemplo 1 y envía 3 unidades al bróker B, que no tenía ninguna:

    | Bróker | Fecha | Tipo | Cant. | Coste unitario | Cant. en pool | PMC |
    |--------|-------|------|-------|----------------|---------------|-----|
    | A | 1 abr | COMPRA | 10 | $150 | 10 | $150.00 |
    | A | 15 abr | COMPRA | 5 | $180 | 15 | $160.00 |
    | A | 1 may | TRANSFERENCIA saliente | −3 | (al PMC) | 12 | $160.00 |
    | B | 1 may | TRANSFERENCIA entrante (auto) | +3 | $160 (PMC de A) | 3 | $160.00 |

    En **modo automático**, el lado receptor toma el PMC del emisor como su anulación del coste base: el bróker B comienza con el promedio del bróker A, y los $480 de coste se mueven con las 3 unidades.

## 🌍 Manejo de múltiples monedas {: #multi-currency-handling }

El PMC se mantiene en una única moneda, la **moneda objetivo** $T$, y cada adquisición entra en él a su **coste histórico**: el importe realmente pagado, convertido al tipo de cambio de la fecha de la propia adquisición $d_i$:

$$
c_i^{T} = P_i \cdot \mathrm{fx}\bigl(\mathrm{ccy}(P_i),\, T,\, d_i\bigr), \qquad \mathrm{fx}(T, T, d) = 1
$$

Aquí $P_i$ es el efectivo pagado por una COMPRA, en su moneda de efectivo, o $\text{anulación} \times Q_{tx}$ en la moneda de la anulación para una transferencia o ajuste. Un importe que ya está en $T$ no necesita ningún tipo de cambio; de lo contrario, cuando la fecha exacta no tiene tipo de cambio, se usa el último tipo anterior a ella.

El coste base de una posición es entonces

$$
\mathrm{CB}(a,b,t) = q(a,b,t) \times \mathrm{PMC}^{T}(a,b,t)
$$

sin **ningún tipo de cambio en $t$**: es lo que se pagó, y no se mueve cuando los tipos de cambio se mueven. Para un activo valorado en otra moneda, el efecto del tipo de cambio reside, por tanto, en el P&L no realizado — valor de mercado al tipo del día menos coste histórico — donde el Panel lo desglosa (ver [P&L período](portfolio-engine/period-pnl.md#unrealized-change-by-currency)).

La moneda objetivo depende de dónde se muestra el PMC:

| Dónde | Moneda objetivo $T$ |
|-------|---------------------|
| Panel, tabla de Posiciones, ventas realizadas, Rendimiento sobre coste | La moneda de visualización (informe) |
| Líneas de PMC del análisis de lotes | La moneda del análisis |
| Vista previa de transacción, coste base automático, series de PMC (`POST /portfolio/wac`) | La moneda seleccionada en la vista previa; de lo contrario, la moneda de la **última adquisición** |
| Planificador PAC | La moneda del planificador |

La moneda de la última adquisición es la moneda pagada por la transacción más reciente que añadió cantidad — una regla determinista; en caso de empate, gana la primera registrada. Un desdoblamiento, o una adquisición de coste desconocido, recurre a la moneda propia del activo.

??? example "Ejemplo 5: Un activo en dólares comprado con euros, moneda de visualización EUR"

    | Fecha | Tipo | Cant. | Pagado | Tipo de cambio USD→EUR | Coste en EUR |
    |-------|------|-------|--------|--------------------------|--------------|
    | 1 abr | COMPRA | 10 | €400 | — (pagado en EUR) | €400.00 |
    | 1 may | COMPRA | 5 | 300 USD | 0.90 | €270.00 |

    $$
    PMC^{EUR} = \frac{400 + 270}{10 + 5} = \frac{670}{15} \approx 44.67 \text{ EUR}
    $$

    La primera compra no necesita tipo de cambio: su coste es exactamente los €400 pagados. El coste base de la posición permanece en €670 sin importar lo que haga el dólar después; un dólar más débil reduce el valor de mercado en euros y se refleja como una pérdida no realizada.

!!! warning "Disponibilidad de tipos de cambio"

    Cuando no existe un tipo de cambio en la fecha de adquisición o antes, LibreFolio nunca cuenta ese coste como cero. Las unidades entran al pool sin su coste y el PMC se marca como incompleto: la vista previa de la transacción no muestra PMC y lista el par FX faltante con sus fechas, el Panel muestra el coste promedio y el P&L no realizado de la posición como no disponibles, y el análisis de lotes deja esos días fuera de sus líneas de PMC. La interfaz advierte sobre los pares FX faltantes y proporciona acciones rápidas para añadirlos o sincronizarlos.

## 🎯 Dónde se usa el PMC en LibreFolio

- **Coste base**: $\text{CB}(a,b,t) = q(a,b,t) \times \text{PMC}^{T}(a,b,t)$, histórico, sin conversión en $t$
- **P&L realizado en VENTA**: $\text{realizado} = P_{\text{venta}} - q_{\text{vendida}} \times \text{PMC}^{T}_{\text{pre-venta}}$, con los ingresos $P_{\text{venta}}$ convertidos en la fecha de venta y las unidades vendidas saliendo a su coste histórico
- **Descomposición del pool de efectivo**: la VENTA devuelve $C = q_{\text{vendida}} \times \text{PMC}^{T}_{\text{pre-venta}}$ a Capital Pool
- **Rendimiento sobre coste**: el precio de compra promedio del denominador de [Rendimiento sobre coste](portfolio-engine/yield-on-cost.md)
- **Formulario de transferencia**: sugiere automáticamente el cost_basis_override del lado receptor a partir del PMC de la posición emisora

!!! warning "El PMC nunca se usa para la valoración de activos"

    El PMC es una construcción contable para el coste base. El valor de mercado utiliza los niveles del resolutor unificado: `MARKET → TRADE_AVG → CARRIED → MISSING`, expuestos a las filas de cartera como `MARKET_PRICE`, `LAST_TRADE_PRICE` o `MISSING`. Ver [Resolución de precios](portfolio-engine/price-resolution.md).

## ⚙️ Implementación: alcance a nivel de posición

El PMC se mantiene **por posición** $(a, b)$ — es decir, por par (activo, bróker). El mismo activo mantenido en dos brókers tiene dos pools de PMC independientes.

$$
\text{PMC}(a, b_1, t) \neq \text{PMC}(a, b_2, t) \quad \text{en general}
$$

El coste promedio de cada posición en un informe se calcula **una vez, antes de la reproducción diaria**, con todas las conversiones que necesita agrupadas en una sola solicitud al servicio de FX; la reproducción diaria luego sigue el pool de cada posición paso a paso en lugar de recalcularlo, y nunca convierte un coste por sí misma.

### 📅 Ordenación de transacciones del mismo día

Dentro de la misma fecha, **las adiciones se procesan antes que las reducciones**:

$$
\text{COMPRA}_1, \text{COMPRA}_2, \ldots \quad \text{luego} \quad \text{VENTA}_1, \text{VENTA}_2, \ldots
$$

Esto evita cantidades negativas transitorias y asegura que la VENTA siempre lea el PMC correcto que incluye las COMPRAS del mismo día.

## 🔗 Relacionado

- 🔬 **[Análisis de lotes FIFO](fifo-engine/fifo-lot-analysis.md)** — Complemento por lote: rastrea cada lote de adquisición individualmente en lugar de fusionarlos en un promedio
- 🔁 **[Compra y venta](../../instruments/transaction-types/buy-sell.md)** — Transacciones que alimentan el pool del PMC
- 📈 **[NAV / Patrimonio neto](portfolio-engine/nav.md)** — Cómo el valor contable basado en PMC difiere del NAV a precio de mercado
- 📖 **[Valor contable](portfolio-engine/book-value.md)** — Coste base abierto: la suma de los costes históricos
- ⚖️ **[PMC y coste base (Manual del desarrollador)](../../../developer/backend/transactions/wac.md)** — La implementación única del coste promedio y sus invocadores
