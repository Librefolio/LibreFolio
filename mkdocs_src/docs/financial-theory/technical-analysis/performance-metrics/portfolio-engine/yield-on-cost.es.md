# 💸 Rendimiento sobre coste (YOC)

El rendimiento sobre coste (YOC) mide el **ingreso bruto registrado generado por unidad actual durante los últimos 365 días calendario**, en relación con el precio medio de compra por unidad de la posición abierta ([Precio medio de compra, o PMC](../weighted-average-cost.md)). Cada importe de ingreso cuenta con su signo, de modo que una corrección registrada reduce el ingreso en lugar de sumarse a él.

LibreFolio lo calcula por separado para cada par $(a,b)$:

$$
(a,b) = (\text{activo},\ \text{bróker})
$$

Por lo tanto, el mismo activo mantenido en dos brókers tiene dos valores de YOC independientes.

!!! warning "Ingreso bruto registrado — no es un rendimiento neto de impuestos"

    YOC utiliza únicamente los importes en efectivo de las transacciones `DIVIDEND` e `INTEREST` vinculadas a activos, cada una con su signo. Se rechaza un nuevo importe negativo, pero las filas antiguas aún pueden contener uno: esa corrección reduce el ingreso, como ocurre en el panel. Las transacciones `TAX` y `FEE` separadas no se restan, por lo que el resultado no debe interpretarse como rendimiento después de impuestos ni como rendimiento neto.

---

## 🧭 Alcance y ventana móvil

Sea $T$ la fecha de fin del informe seleccionada. YOC siempre utiliza la ventana inclusiva:

$$
\boxed{[T-364,\ T]}
$$

Esta ventana contiene 365 días calendario y es **independiente de la fecha de inicio del informe**. Mover el inicio de un informe del panel no cambia YOC cuando $T$ permanece sin cambios.

Solo califican las entradas vinculadas a activos del libro de transacciones personales:

| Incluido | Excluido |
|---|---|
| Filas de `Transaction` vinculadas a activos de tipo `DIVIDEND` o `INTEREST`, sea cual sea el signo de su importe en efectivo | Transacciones `TAX`, `FEE` y `ADJUSTMENT` separadas |
| El importe en efectivo con signo, la divisa, la fecha, el activo y el bróker pagador | Ingresos de `AssetEvent` del proveedor o manuales |
| Ingreso asignado al par $(a,b)$ exacto | Ingreso sin un activo |

El esquema de transacciones acepta un importe en efectivo de `DIVIDEND` o `INTEREST` exactamente cero, pero rechaza uno nuevo negativo. Una fila negativa guardada anteriormente sigue calificando y cuenta con su signo. Un `ADJUSTMENT` puede afectar la cantidad de la repetición, el PMC o las entradas de desdoblamientos vinculados, pero nunca entra en el numerador de ingresos de YOC.

El cálculo no tiene una lista de clases de activos permitidas. Se aplica a todos los tipos de posición larga abierta representados por el motor de cartera, incluidos criptoactivos y activos manuales, siempre que las entradas requeridas del libro de transacciones, PMC, desdoblamiento y FX sean válidas.

---

## 🧮 Definición matemática

Para cada transacción de ingreso $j$ que califique:

| Símbolo | Significado |
|---|---|
| $D_j$ | Fecha de la transacción |
| $I_j$ | Importe en efectivo bruto de la transacción en la divisa $c_j$, con su signo: $I_j<0$ para una corrección negativa anterior |
| $C^*$ | Divisa del informe seleccionada |
| $q_j$ | Cantidad larga elegible en el bróker pagador al final del día $D_j-1$ |
| $s_j$ | Producto de los ratios de desdoblamientos vinculados con fecha desde $D_j$ hasta $T$, inclusive |
| $w_{a,b,T}$ | Precio medio de compra por unidad (PMC) del par $(a,b)$ en $T$, mantenido en $C^*$ a tipos de cambio históricos |

### 💱 Conversión de ingresos

Cada importe de ingreso se convierte a la divisa del informe en su propia fecha de transacción:

$$
I_j^* =
I_j \cdot \mathrm{fx}(c_j,C^*,D_j)
$$

### 🧬 Normalización a unidades actuales

El ingreso por unidad se asigna primero sobre la cantidad elegible del día anterior y luego se normaliza para cada desdoblamiento vinculado válido en la fecha del ingreso o posterior:

$$
g_{a,b,T}
=
\sum_{\substack{j \in (a,b)\\T-364 \leq D_j \leq T}}
\frac{I_j^*}{q_j \cdot s_j}
$$

Para un desdoblamiento 2 por 1, $s_j=2$: el ingreso histórico por unidad antigua se divide entre dos para que sea comparable con las unidades actuales. También se incluye un desdoblamiento vinculado con fecha en $D_j$.

### 📊 Denominador del precio medio de compra

El denominador es el precio medio de compra por unidad de la posición, **ya expresado en la divisa del informe**: cuando se construyó el promedio, cada adquisición entró en él al tipo de cambio de su propia fecha (véase la sección de múltiples divisas de [Precio medio de compra](../weighted-average-cost.md)):

$$
w_{a,b,T}^*
=
\frac{C^{*}_{a,b,T}}{Q_{a,b,T}}
$$

donde $Q_{a,b,T}$ es la cantidad del grupo de coste medio del par en $T$ y $C^{*}_{a,b,T}$ su coste histórico en $C^*$: cada adquisición $i$ añadió $P_i \cdot \mathrm{fx}(\mathrm{ccy}(P_i), C^*, d_i)$ por el importe $P_i$ pagado en la fecha $d_i$, y cada reducción eliminó su parte proporcional.

No se aplica ninguna conversión en la fecha de fin del informe $T$: el denominador es lo que se pagó y no varía con el tipo de cambio actual.

LibreFolio informa entonces:

$$
\boxed{
\mathrm{YOC}_{a,b,T}
=
\frac{g_{a,b,T}}{w_{a,b,T}^*}
}
$$

El valor de la API es una fracción y la tabla de posiciones lo muestra como porcentaje. Un valor disponible puede ser positivo o exactamente cero. Cuando $g_{a,b,T}<0$ —las correcciones de la ventana superan sus ingresos—, LibreFolio no muestra ningún YOC (véanse las reglas de disponibilidad a continuación).

---

## 🔁 Reglas de cantidad, custodia, transferencia y desdoblamiento

La cantidad elegible $q_j$ se evalúa deliberadamente al **final del día anterior al pago**:

- solo cuenta la cantidad `LONG`;
- una **compra (BUY) del mismo día se excluye**;
- una **venta (SELL) del mismo día se incluye**, porque esas unidades existían al final del día $D_j-1$;
- la custodia del bróker se respeta a lo largo de la repetición de transferencias;
- un fragmento en tránsito sigue contando para su bróker de origen, nunca para el destino antes de su llegada;
- las unidades que llegan de un bróker que no puede ver —por ejemplo, como copropietario del bróker receptor— cuentan desde su llegada: el otro bróker nunca entra en la repetición, y su coste es el coste base de la propia transferencia entrante, parte del precio medio de compra (sin él, YOC no está disponible).

El ingreso permanece vinculado al bróker que lo registró. Mover unidades del bróker A al bróker B **no** traslada automáticamente el ingreso histórico de A al YOC de B. Los ingresos posteriores registrados en B utilizan la cantidad elegible del día anterior de B y el precio medio de compra de B.

Los desdoblamientos vinculados posteriores y del mismo día reescalan el ingreso por unidad anterior a las unidades que existen en $T$. LibreFolio utiliza filas explícitas de desdoblamientos vinculados; no infiere un reajuste para todo el activo a partir de un desdoblamiento registrado solo en otro bróker. Si una repetición conectada entre brókers contiene un desdoblamiento pero carece de una fila de desdoblamiento correspondiente para el bróker del ingreso o el bróker actual, la normalización es ambigua y YOC falla de forma segura. Un desdoblamiento vinculado inválido, duplicado, no coincidente o no positivo también hace que el par afectado no esté disponible en lugar de producir un resultado aproximado.

Las transacciones `ADJUSTMENT` siguen siendo únicamente entradas de repetición: pueden cambiar la cantidad o el PMC y pueden llevar un desdoblamiento vinculado, pero sus importes nunca cuentan como ingreso.

??? example "Operaciones del mismo día y un desdoblamiento posterior"

    Suponga que se registra un dividendo de 20 € el 30 de junio. El bróker pagador tenía 100 unidades largas elegibles al final del día 29 de junio. Una compra o venta el 30 de junio no cambia ese denominador.

    Se produce un desdoblamiento vinculado 2 por 1 entre el 30 de junio y $T$, por lo que:

    $$
    g = \frac{20}{100 \times 2} = 0.10\ \mathrm{EUR}
    $$

    Si el precio medio de compra (PMC) en $T$ es de 4,00 € por unidad actual:

    $$
    \mathrm{YOC} =
    \frac{0.10\ \mathrm{EUR}}{4.00\ \mathrm{EUR}}
    = 2.50\%
    $$

---

## 🌍 Resolución de FX y procedencia

YOC utiliza la política actual de FX históricos de la cartera:

- los ingresos solicitan FX para $D_j$;
- el precio medio de compra (PMC) no necesita FX en $T$: cada una de sus adquisiciones se convirtió en su propia fecha cuando se construyó el promedio;
- cuando la fecha exacta no está disponible, se utiliza el último tipo de cambio almacenado en esa fecha o anterior;
- no se sustituye por un tipo de cambio a plazo.

La procedencia conserva tanto la **fecha solicitada** como la **fecha real del tipo de cambio** de cada conversión de ingreso, además del par de divisas y los días retrocedidos. Por lo tanto, la información emergente de la tabla de posiciones puede mostrar, por ejemplo, que una conversión de ingreso del 30 de junio utilizó el tipo de cambio más reciente del 28 de junio.

Si no se puede resolver alguna conversión de ingreso requerida, todo el par no está disponible. Si el coste de una adquisición no se puede convertir —o una transferencia o un ajuste no tiene coste base—, el propio precio medio de compra no está disponible, y tampoco YOC. LibreFolio no omite silenciosamente la transacción afectada ni reutiliza un valor no relacionado.

---

## 🚦 Disponibilidad y comportamiento de fallo seguro

YOC distingue una ausencia válida de ingresos de un cálculo en el que no se puede confiar.

| Estado | Significado | Celda de la tabla de posiciones |
|---|---|---|
| **Disponible** | Existe al menos una transacción de ingreso que califica, todas las entradas requeridas son válidas y el ingreso por unidad con signo $g_{a,b,T}$ es cero o más. El resultado es positivo cuando $g_{a,b,T}>0$; es exactamente cero cuando $g_{a,b,T}=0$ —por ejemplo, cuando todas las filas que califican están registradas con importe cero, o una corrección compensa exactamente el ingreso. La procedencia marca ese caso de cero exacto con `net_zero=true`. No se aplica una antigüedad mínima del par. | Porcentaje con dos decimales: por ejemplo, `2.50%` o `0.00%`. |
| **Sin ingresos** | No existe ninguna fila de ingreso que califique en la ventana y el par tiene un historial completo de 365 fechas en el libro de transacciones. El valor de la API es cero, pero este estado es distinto de un cero disponible. | `-` con información emergente explicativa y sin icono de advertencia. |
| **No disponible** | El par sin ingresos es demasiado joven, una entrada requerida del libro de transacciones o del cálculo no superó la validación, o las correcciones dejan el ingreso por unidad por debajo de cero. Su valor es `null` y su motivo identifica la causa. | `-` con un icono de información y una información emergente con el motivo personalizado. |

El campo externo `yield_on_cost` es obligatorio y no nulo para cada posición. Por lo tanto, un resultado no disponible se representa mediante el estado `unavailable` del objeto de resultado y un `value` nulo, no mediante un campo externo ausente o nulo.

Sea $F_{a,b}$ la primera fecha de transacción vinculada a un activo para el par. Un resultado sin ingresos solo se vuelve válido cuando:

$$
(T-F_{a,b})+1 \geq 365
$$

De forma equivalente, $F_{a,b} \leq T-364$. Cerrar y luego reabrir la posición **no** restablece esta antigüedad: la primera transacción original del par sigue siendo el ancla.

Esta condición de un año se evalúa **solo cuando la ventana móvil no contiene transacciones de ingreso que califiquen**. No es una regla de anualización: un par más joven con ingresos registrados válidos puede tener un YOC disponible porque la métrica simplemente suma los ingresos observados dentro de $[T-364,T]$.

El cálculo falla de forma segura ante cualquiera de estas condiciones:

- el ingreso no tiene cantidad larga elegible al final del día $D_j-1$;
- la repetición de transacciones o transferencias es inconsistente;
- los datos de desdoblamientos vinculados son inválidos o inconsistentes;
- faltan los FX históricos requeridos;
- el precio medio de compra (PMC) falta o no es positivo —la falta incluye una adquisición cuyo coste no pudo convertirse o que no tiene coste base.

Una entrada requerida incorrecta hace que todo el par no esté disponible. No hay suma parcial, sustitución por evento de activo, fallback de ingresos del proveedor ni aproximación con la cantidad actual.

Un ingreso negativo no es una entrada incorrecta, pero no deja rendimiento que mostrar. Cuando todas las entradas son válidas y $g_{a,b,T}<0$ —las correcciones registradas en la ventana superan sus ingresos—, el par no está disponible con el motivo `negative_net_income`, y la información emergente de la tabla de posiciones dice *Las correcciones superan los ingresos del último año.* Su procedencia conserva el ingreso negativo por unidad (`gross_income_per_unit`). Una suma exactamente cero no es este caso: permanece disponible en `0.00%`, con `net_zero=true`.

---

## 🖥️ Cómo leer YOC en LibreFolio

YOC aparece en la tabla compartida **Posiciones**, utilizada tanto por la pestaña Posiciones del panel como por la pestaña Posiciones de cada bróker:

- visible de forma predeterminada justo al lado de **Anualizado**;
- los valores disponibles, incluido el cero exacto, se fijan a dos decimales;
- los valores positivos no llevan un `+` inicial;
- un cero disponible aparece como `0.00%` y tiene `net_zero=true` en su procedencia;
- un guion normal de ausencia de ingresos no tiene icono de advertencia;
- un guion de no disponible tiene un icono de información cuya información emergente explica el motivo específico y la procedencia disponible;
- las opciones de mostrar/ocultar se comparten entre las vistas del panel y del bróker y persisten entre sesiones.

Cada fila sigue siendo específica de un bróker. Por lo tanto, en el ámbito de múltiples brókers del panel, dos filas para el mismo activo pueden mostrar valores diferentes. Consulte [Posiciones y análisis](../../../../user/dashboard/positions.md) para ver la guía de la tabla orientada al usuario.

---

## ⚖️ Qué no es YOC

| Métrica | Denominador y horizonte | Por qué difiere del YOC de LibreFolio |
|---|---|---|
| [**Rendimiento por dividendo de mercado**](../../../instruments/asset-events/dividend.md) | Dividendo anual por acción dividido por el precio de mercado actual | Medida de mercado/proveedor; YOC utiliza solo ingresos personales registrados y el precio medio de compra (PMC). |
| **Rendimiento acumulado en efectivo** | Ingreso total histórico dividido por el coste base total actual | YOC utiliza solo $[T-364,T]$, reconstruye el ingreso por unidad histórica elegible y no divide el efectivo total histórico por el coste base agregado actual. |
| [**Rendimiento neto anualizado / CAGR**](net-annualized-return.md) | Rendimiento total neto compuesto durante la ventana de tenencia | Incluye rendimiento de mercado, ingresos, comisiones e impuestos; YOC aísla el ingreso bruto registrado y no se anualiza a partir de un rendimiento acumulado. |
| [**Rendimiento actual del bono**](../../../instruments/asset-events/interest.md) | Cupón anual dividido por el precio actual del bono | Medida de cupón/precio a nivel del título; YOC utiliza el libro de transacciones del bróker registrado por el inversor y el PMC. |
| [**Rendimiento hasta el vencimiento (YTM)**](../../../instruments/asset-events/interest.md) | Tasa de descuento que iguala los cupones futuros y el valor de reembolso de un bono con su precio | TIR prospectiva del bono; YOC es retrospectivo, basado en transacciones y se aplica a todos los tipos de posición. |

---

## 🔗 Relacionado

- 📊 [Precio medio de compra](../weighted-average-cost.md) — denominador del precio medio de compra
- 🖥️ [Posiciones del panel](../../../../user/dashboard/positions.md) — estados de columna, formato y preferencia compartida
- 💰 [Transacciones de dividendos e intereses](../../../instruments/transaction-types/dividend-interest.md) — entradas del libro de transacciones personal que califican
- ⚙️ [Motor de cartera](index.md) — estado de la posición y capa de métricas
