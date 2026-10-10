# 💸 Rendimiento sobre coste (YOC)

El rendimiento sobre coste (YOC) mide los **ingresos brutos registrados no negativos producidos por unidad actual durante las últimas 365 fechas de calendario**, en relación con el precio medio de compra por unidad de la posición abierta ([precio medio de compra, o PMC](../weighted-average-cost.md)).

LibreFolio lo calcula por separado para cada par $(a,b)$:

$$
(a,b) = (\text{asset},\ \text{broker})
$$

Por lo tanto, el mismo activo mantenido en dos brókeres tiene dos valores YOC independientes.

!!! warning "Ingresos brutos registrados — no un rendimiento neto de impuestos"

    El YOC usa únicamente importes de efectivo no negativos de transacciones `DIVIDEND` e `INTEREST` vinculadas a activos. Se acepta el cero exacto; no se admiten importes de ingresos negativos. Las transacciones `TAX` y `FEE` separadas no se restan, por lo que el resultado no debe interpretarse como rendimiento de ingresos después de impuestos o neto.

---

## 🧭 Alcance y ventana retrospectiva

Sea $T$ la fecha de fin del informe seleccionada. El YOC siempre usa la ventana inclusiva:

$$
\boxed{[T-364,\ T]}
$$

Esta ventana contiene 365 fechas de calendario y es **independiente de la fecha de inicio del informe**. Mover el inicio de un informe del panel no cambia el YOC cuando $T$ permanece sin cambios.

Solo califican las entradas no negativas vinculadas a activos del libro de transacciones personal:

| Incluidas | Excluidas |
|---|---|
| Filas de `Transaction` vinculadas a activos de tipo `DIVIDEND` o `INTEREST`, con importe de efectivo igual o mayor que cero | Transacciones `TAX`, `FEE` y `ADJUSTMENT` separadas |
| El importe de efectivo no negativo, la divisa, la fecha, el activo y el bróker pagador | Ingresos por `AssetEvent` de proveedor o manuales |
| Ingresos asignados al par exacto $(a,b)$ | Ingresos sin un activo |

El esquema de transacciones acepta un importe de efectivo `DIVIDEND` o `INTEREST` exactamente cero, pero rechaza uno negativo. Un `ADJUSTMENT` puede afectar la cantidad de la repetición, el PMC o las entradas de desdoblamiento vinculado, pero nunca entra en el numerador de ingresos del YOC.

El cálculo no tiene lista de permitidos de clases de activos. Se aplica a todo tipo de posición larga abierta representada por el motor de cartera, incluidos criptoactivos y activos manuales, siempre que las entradas requeridas de libro, PMC, desdoblamiento y FX sean válidas.

---

## 🧮 Definición matemática

Para cada transacción de ingresos que califica $j$:

| Símbolo | Significado |
|---|---|
| $D_j$ | Fecha de la transacción |
| $I_j$ | Importe bruto de efectivo de la transacción no negativo en la divisa $c_j$, con $I_j\geq0$ |
| $C^*$ | Divisa de informe seleccionada |
| $q_j$ | Cantidad larga elegible en el bróker pagador al final del día $D_j-1$ |
| $s_j$ | Producto de los ratios de desdoblamiento vinculados con fecha desde $D_j$ hasta $T$, inclusive |
| $w_{a,b,T}$ | Precio medio de compra por unidad (PMC) del par $(a,b)$ en $T$, mantenido en $C^*$ a tipos de cambio históricos |

### 💱 Conversión de ingresos

Cada importe de ingresos se convierte a la divisa de informe en su propia fecha de transacción:

$$
I_j^* =
I_j \cdot \mathrm{fx}(c_j,C^*,D_j)
$$

### 🧬 Normalización a unidades actuales

Los ingresos por unidad se asignan primero sobre la cantidad elegible del día anterior y luego se normalizan para cada desdoblamiento vinculado válido en la fecha de ingresos o posterior:

$$
g_{a,b,T}
=
\sum_{\substack{j \in (a,b)\\T-364 \leq D_j \leq T}}
\frac{I_j^*}{q_j \cdot s_j}
$$

Para un desdoblamiento 2 por 1, $s_j=2$: los ingresos históricos por unidad antigua se dividen por dos para que sean comparables con las unidades actuales. También se incluye un desdoblamiento vinculado con fecha en $D_j$.

### 📊 Denominador del precio medio de compra

El denominador es el precio medio de compra por unidad de la posición, **ya expresado en la divisa de informe**: cuando se construyó la media, cada adquisición se incorporó a ella al tipo de cambio de su propia fecha (véase la sección de múltiples divisas de [precio medio de compra](../weighted-average-cost.md)):

$$
w_{a,b,T}^*
=
\frac{C^{*}_{a,b,T}}{Q_{a,b,T}}
$$

donde $Q_{a,b,T}$ es la cantidad del fondo de coste medio del par en $T$ y $C^{*}_{a,b,T}$ su coste histórico en $C^*$: cada adquisición $i$ añadió $P_i \cdot \mathrm{fx}(\mathrm{ccy}(P_i), C^*, d_i)$ por el importe $P_i$ pagado en la fecha $d_i$, y cada reducción eliminó su parte proporcional.

No se aplica conversión en la fecha de fin del informe $T$: el denominador es lo que se pagó y no se mueve con el tipo de cambio de hoy.

LibreFolio entonces informa:

$$
\boxed{
\mathrm{YOC}_{a,b,T}
=
\frac{g_{a,b,T}}{w_{a,b,T}^*}
}
$$

El valor de la API es una fracción, y la tabla Posiciones lo muestra como porcentaje. Un valor disponible puede ser positivo o exactamente cero.

---

## 🔁 Reglas de cantidad, custodia, transferencia y desdoblamiento

La cantidad elegible $q_j$ se evalúa deliberadamente al **final del día anterior al pago**:

- solo cuenta la cantidad `LONG`;
- una **compra (BUY) del mismo día se excluye**;
- una **venta (SELL) del mismo día se incluye**, porque esas unidades existían al final del día $D_j-1$;
- la custodia del bróker se respeta durante toda la repetición de transferencias;
- un fragmento en tránsito todavía cuenta para su bróker de origen, nunca para el de destino antes de la llegada.

Los ingresos permanecen vinculados al bróker que los registró. Mover unidades del bróker A al bróker B **no** traslada automáticamente los ingresos históricos de A al YOC de B. Los ingresos posteriores registrados en B usan la cantidad elegible del día anterior de B y el precio medio de compra de B.

Los desdoblamientos vinculados posteriores y del mismo día reescalan los ingresos por unidad anteriores a las unidades que existen en $T$. LibreFolio usa filas explícitas de desdoblamiento vinculado; no infiere una reexpresión para todo el activo a partir de un desdoblamiento registrado solo en otro bróker. Si una repetición conectada entre brókeres contiene un desdoblamiento pero carece de una fila de desdoblamiento coincidente para el bróker de ingresos/actual, la normalización es ambigua y el YOC falla cerrado. Un desdoblamiento vinculado inválido, duplicado, no coincidente o no positivo también hace que el par afectado no esté disponible en lugar de producir un resultado aproximado.

Las transacciones `ADJUSTMENT` siguen siendo solo entradas de repetición: pueden cambiar la cantidad o el PMC y pueden conllevar un desdoblamiento vinculado, pero sus importes nunca cuentan como ingresos.

??? example "Operaciones del mismo día y un desdoblamiento posterior"

    Supón que se registra un dividendo de 20 € el 30 de junio. El bróker pagador tenía 100 unidades largas elegibles al final del día 29 de junio. Una compra o venta el 30 de junio no cambia ese denominador.

    Entre el 30 de junio y $T$ ocurre un desdoblamiento vinculado 2 por 1, así que:

    $$
    g = \frac{20}{100 \times 2} = 0.10\ \mathrm{EUR}
    $$

    Si el precio medio de compra (PMC) en $T$ es 4,00 € por unidad actual:

    $$
    \mathrm{YOC} =
    \frac{0.10\ \mathrm{EUR}}{4.00\ \mathrm{EUR}}
    = 2.50\%
    $$

---

## 🌍 Resolución de FX y procedencia

El YOC usa la política de FX histórica actual de la cartera:

- los ingresos solicitan FX para $D_j$;
- el precio medio de compra (PMC) no necesita FX en $T$: cada una de sus adquisiciones se convirtió en su propia fecha cuando se construyó la media;
- cuando falta la fecha exacta, se usa el último tipo de cambio almacenado en esa fecha o antes;
- no se sustituye por un tipo de cambio futuro.

La procedencia conserva tanto la **fecha solicitada** como la **fecha real del tipo de cambio** de cada conversión de ingresos, además del par de divisas y los días retrocedidos. Por lo tanto, la información emergente de Posiciones puede mostrar, por ejemplo, que una conversión de ingresos del 30 de junio usó el tipo de cambio más reciente del 28 de junio.

Si no se puede resolver alguna conversión de ingresos requerida, el par completo no está disponible. Si el coste de una adquisición no se puede convertir —o una transferencia o ajuste no tiene coste base—, el precio medio de compra en sí no está disponible, y el YOC tampoco. LibreFolio no omite silenciosamente la transacción afectada ni reutiliza un valor no relacionado.

---

## 🚦 Disponibilidad y comportamiento de fallo cerrado

El YOC distingue una ausencia válida de ingresos de un cálculo en el que no se puede confiar.

| Estado | Significado | Celda de Posiciones |
|---|---|---|
| **Disponible** | Existe al menos una transacción de ingresos que califica y toda entrada requerida es válida. El resultado es positivo cuando algún importe que califica es positivo; es exactamente cero cuando una o más filas que califican se registran con importe cero y ninguna tiene un importe positivo. La procedencia marca ese caso de cero exacto con `net_zero=true`. No se aplica ninguna antigüedad mínima del par. | Porcentaje con dos decimales: por ejemplo, `2.50%` o `0.00%`. |
| **Sin ingresos** | No existe ninguna fila de ingresos que califique en la ventana, y el par tiene un historial de libro completo de 365 fechas. El valor de la API es cero, pero este estado es distinto de un cero disponible. | `-` con información emergente explicativa y sin icono de advertencia. |
| **No disponible** | El par sin ingresos es demasiado joven, o una entrada requerida de libro/cálculo no superó la validación. Su valor es `null` y su motivo identifica el fallo. | `-` con un icono de información y información emergente con el motivo personalizado. |

El campo externo `yield_on_cost` es obligatorio y no nulo para cada posición. Por lo tanto, un resultado no disponible se representa mediante el estado `unavailable` del objeto de resultado y el `value` nulo, no mediante un campo externo ausente o nulo.

Sea $F_{a,b}$ la primera fecha de transacción vinculada a activos del par. Un resultado sin ingresos solo se vuelve válido cuando:

$$
(T-F_{a,b})+1 \geq 365
$$

De forma equivalente, $F_{a,b} \leq T-364$. Cerrar y luego reabrir la posición **no** restablece esta antigüedad: la transacción original del primer par sigue siendo el ancla.

Esta condición de un año se evalúa **solo cuando la ventana retrospectiva no contiene transacciones de ingresos que califiquen**. No es una regla de anualización: un par más joven con ingresos registrados válidos puede tener un YOC disponible porque la métrica simplemente suma los ingresos observados dentro de $[T-364,T]$.

El cálculo falla cerrado para cualquiera de estas condiciones:

- los ingresos no tienen cantidad larga elegible al final del día $D_j-1$;
- la repetición de transacciones o transferencias es inconsistente;
- los datos de desdoblamiento vinculado son inválidos o inconsistentes;
- falta el FX histórico requerido;
- el precio medio de compra (PMC) falta o no es positivo —falta incluye una adquisición cuyo coste no se pudo convertir o no tiene coste base.

Una entrada requerida incorrecta hace que todo el par no esté disponible. No hay suma parcial, sustituto de evento de activo, fallback de ingresos de proveedor ni aproximación por cantidad actual.

---

## 🖥️ Cómo leer el YOC en LibreFolio

El YOC aparece en la tabla compartida **Posiciones** que usan tanto la pestaña Posiciones del panel como la pestaña Posiciones de cada bróker:

- visible de forma predeterminada justo al lado de **Anualizado**;
- los valores disponibles, incluido el cero exacto, se fijan a dos decimales;
- los valores positivos no llevan `+` inicial;
- un cero disponible aparece como `0.00%` y tiene `net_zero=true` en su procedencia;
- un guion normal de sin ingresos no tiene icono de advertencia;
- un guion de no disponible tiene un icono de información cuya información emergente explica el motivo específico y la procedencia disponible;
- las elecciones de mostrar/ocultar se comparten entre las vistas del panel y del bróker y persisten entre sesiones.

Cada fila sigue siendo específica del bróker. En el alcance multi-bróker del panel, dos filas para el mismo activo pueden por lo tanto mostrar valores diferentes. Consulta [Posiciones y análisis](../../../../user/dashboard/positions.md) para la guía de la tabla orientada al usuario.

---

## ⚖️ Lo que el YOC no es

| Métrica | Denominador y horizonte | Por qué difiere del YOC de LibreFolio |
|---|---|---|
| [**Rendimiento por dividendo de mercado**](../../../instruments/asset-events/dividend.md) | Dividendo anual por acción dividido por el precio de mercado actual | Medida de mercado/proveedor; el YOC usa solo ingresos personales registrados y el precio medio de compra (PMC). |
| **Rendimiento de efectivo acumulado** | Ingresos totales de por vida divididos por el coste base total actual | El YOC usa solo $[T-364,T]$, reconstruye los ingresos por unidad histórica elegible y no divide el efectivo de por vida por el coste base agregado de hoy. |
| [**Rendimiento anualizado neto / CAGR**](net-annualized-return.md) | Rendimiento total neto compuesto durante la ventana de tenencia | Incluye rendimiento de mercado, ingresos, comisiones e impuestos; el YOC aísla los ingresos brutos registrados y no se anualiza a partir de un rendimiento acumulado. |
| [**Rendimiento actual de bonos**](../../../instruments/asset-events/interest.md) | Cupón anual dividido por el precio actual del bono | Medida de cupón/precio a nivel de valor; el YOC usa el libro del bróker registrado por el inversor y el PMC. |
| [**Rendimiento al vencimiento (YTM)**](../../../instruments/asset-events/interest.md) | Tasa de descuento que iguala los cupones futuros y el valor de reembolso de un bono con el precio | TIR prospectiva del bono; el YOC es retrospectivo, basado en transacciones y se aplica a todo tipo de posición. |

---

## 🔗 Relacionado

- 📊 [Precio medio de compra](../weighted-average-cost.md) — denominador del precio medio de compra
- 🖥️ [Posiciones del panel](../../../../user/dashboard/positions.md) — estados de columna, formato y preferencia compartida
- 💰 [Transacciones de dividendos e intereses](../../../instruments/transaction-types/dividend-interest.md) — entradas elegibles del libro personal
- ⚙️ [Motor de cartera](index.md) — estado de posición y capa de métricas
