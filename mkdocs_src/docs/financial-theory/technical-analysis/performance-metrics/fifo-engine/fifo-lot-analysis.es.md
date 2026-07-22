# 🔬 Análisis de Lotes FIFO

El análisis de lotes FIFO constituye el complemento **por lote** del [Precio Medio Ponderado (PMP)](../weighted-average-cost.md).

El PMP responde: *"¿Cuál es mi precio medio ponderado para esta posición?"* El análisis de lotes FIFO responde una pregunta diferente: *"¿Cómo se comporta cada lote de compra individual a lo largo del tiempo?"*

En lugar de fusionar todas las adquisiciones en un solo grupo, LibreFolio rastrea cada lote a través de su propio ciclo de vida — **abierto**, **parcialmente cerrado**, **totalmente cerrado** — y empareja las ventas en orden **FIFO** (primero en entrar, primero en salir).

!!! info "Complemento, no reemplazo"

    El PMP es agregado y a nivel de posición. El análisis de lotes FIFO es granular y a nivel de lote. Ambas vistas son útiles: una para la base de costo combinada, otra para la atribución económica lote por lote.

---

## 💡 ¿Qué es el Análisis de Lotes FIFO?

Un **lote** es un lote de adquisición: por ejemplo, una COMPRA de 100 acciones, o una transferencia de entrada que conserva la base de costo histórica.

Cuando ocurre una VENTA, los lotes abiertos más antiguos se cierran primero. Esto crea un historial lote por lote:

- cuánto de cada lote sigue abierto
- cuánto se ha vendido ya
- cuánto producto de venta ha generado ese lote
- cuántos ingresos se obtuvieron mientras se mantuvo el lote
- cuánto rendimiento provino del cambio de precio versus los ingresos en efectivo

Esto hace que el análisis de lotes FIFO sea especialmente útil cuando dos posiciones en el mismo activo se compraron a precios o fechas muy diferentes.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-gantt-chart" alt="Cronograma de Vida y Custodia del Lote — cada barra es un lote, coloreado por el bróker custodio, el grosor es proporcional a la cantidad mantenida">
</div>

El cronograma de **Vida y Custodia del Lote** anterior hace visible el ciclo de vida: cada barra es un lote, coloreada por el bróker que lo posee actualmente, con un grosor proporcional a la cantidad aún mantenida en ese segmento. Una barra que termina en medio del gráfico es un lote totalmente cerrado; una barra que llega hasta "hoy" aún está abierta.

---

## 🧮 Rendimiento Abierto por Lote

El **Rendimiento Abierto** aísla el movimiento **solo de precio** de un lote en relación con su precio de referencia de apertura.

$$
\text{RendimientoRelativo} = \frac{\text{PrecioMercado}}{\text{PrecioUnitarioReferencia}} - 1
$$

En la práctica:

- si existe una cotización de mercado en la fecha de apertura del lote, esa cotización de apertura se convierte en `precio_unitario_referencia`
- si el lote se abrió antes de la primera cotización de mercado disponible, el sistema recurre al costo de apertura del propio lote, escalado a las unidades de cotización de mercado

Esta métrica excluye dividendos, intereses y productos de venta realizados. Responde: *"¿Cuánto se ha movido el precio de mercado desde que se abrió este lote?"*

!!! tip "Fallback del precio de referencia"

    Cuando no existe una cotización de mercado del día de apertura, LibreFolio utiliza el precio de adquisición del lote como base de referencia, escalado a la convención de cotización del activo. Esto evita porcentajes de rendimiento engañosos en instrumentos cotizados por cada 100 unidades nominales.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-wac-chart" alt="Gráfico PMP / Precio de Mercado — una burbuja por lote, coloreada por el bróker de apertura, dimensionada por el valor de apertura, trazada contra la línea de precio de mercado">
</div>

El gráfico **PMP / Precio de Mercado** traza cada lote como una burbuja contra la línea de precio de mercado: el color de la burbuja marca el bróker donde se abrió el lote, el tamaño de la burbuja escala con el valor de apertura del lote. Un lote valorado solo al costo (sin precio de mercado en vivo) se dibuja con un contorno discontinuo.

---

## 💰 Rendimiento Total por Lote

El **Rendimiento Total** es más amplio que el Rendimiento Abierto. Incluye el valor de mercado restante del lote, cualquier producto de venta ya realizado de ese lote y cualquier ingreso asignado recibido mientras se mantuvo el lote.

El cálculo matemático de lotes de LibreFolio utiliza estos componentes exactos:

$$
\text{ValorApertura} = \text{CostoOriginal}
$$

$$
\text{Producto}(t) = \sum \text{Productos de Cierre} \text{ hasta } t
$$

$$
\text{ValorTotal}(t) = \text{ValorAbierto}(t) + \text{Producto}(t)
$$

$$
\text{GyP}(t) = \text{ValorTotal}(t) - \text{CostoOriginal}
$$

$$
\text{GyPMercado} = \text{GyP} - \text{GyPRealizado}
$$

$$
\text{GyPRealizado} = \sum \text{GyP Realizado de Cierre}
$$

$$
\text{IngresoActivo} = \sum_t \text{Ingreso}_i(t)
$$

$$
\text{GyPTotal} = \text{GyPMercado} + \text{GyPRealizado} + \text{IngresoActivo}
$$

Para el resumen escalar del lote, el porcentaje de rendimiento es:

$$
\text{RendimientoTotal} = \frac{\text{GyPTotal}}{\text{ValorApertura}}
$$

Para el historial de rendimiento a lo largo del tiempo, LibreFolio utiliza:

$$
\text{RendimientoTotal}(t) = \frac{\text{ValorTotal}(t) + \text{Ingreso}(t)}{\text{CostoOriginal}} - 1
$$

Esto responde: *"¿Cuál es el rendimiento económico completo de este lote, incluyendo tanto el movimiento de precio como el rendimiento en efectivo?"*

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" alt="Gráfico de comparación Valor / Rendimiento en modo Rendimiento — porcentaje de rendimiento por lote desde la fecha de apertura de cada lote">
</div>

El gráfico de comparación **Valor / Rendimiento**, cambiado al modo **Rendimiento**, traza exactamente este porcentaje — una línea por lote, cada una medida desde su propia fecha de apertura, sobre el conjunto de lotes seleccionado actualmente.

---

## ⚙️ Escalado qbq

Algunos instrumentos se cotizan **por cantidad base**, no por unidad individual. LibreFolio llama a esta cantidad base `qbq` (`quote_base_quantity`).

- Para la mayoría de las acciones, `qbq = 1`
- Para muchos bonos, `qbq = 100`

La regla de valoración exacta es:

$$
\text{ValorPosición}(cantidad, precio, qbq) = \left(\frac{cantidad}{qbq}\right)\cdot precio
$$

$$
\text{ValorAbierto}(t) = \left(\frac{\text{CantidadAbierta}(t)}{qbq}\right)\cdot \text{PrecioMercado}(t)
$$

!!! warning "El escalado qbq importa"

    Supongamos que un bono tiene una cantidad nominal de 1,000 y se cotiza a **101.50 por cada 100 nominal**.

    - `qbq = 100`
    - cantidad del lote = `1,000`
    - valor de mercado = `(1,000 / 100) × 101.50 = 1,015.00`

    Si comparas `101.50` directamente con una base de costo por unidad individual como `0.992`, obtienes un sin sentido porque los dos números viven en escalas diferentes.

    La comparación correcta reescala el costo del lote al eje de cotización de mercado:

    $$
    0.992 \times 100 = 99.20
    $$

    Por lo tanto, la comparación de precios significativa es **101.50 vs 99.20**, no **101.50 vs 0.992**.

Sin este escalado, los rendimientos y valoraciones de los bonos pueden diferir por órdenes de magnitud.

---

## 🛟 Estimado al Costo

Si no hay un precio de mercado en vivo disponible para un activo, LibreFolio **no** falla el análisis. En su lugar, valora temporalmente la parte aún abierta del lote al costo:

$$
\text{ValorAbierto} = \text{ValorApertura}\cdot \frac{\text{CantidadAbierta}}{\text{CantidadOriginal}}
$$

$$
\text{GyPMercado} = 0
$$

Implicación práctica:

- el lote aún muestra valor residual
- los productos ya realizados siguen siendo visibles
- los dividendos o intereses asignados siguen siendo visibles
- **la volatilidad no realizada se subestima temporalmente**

!!! info "Interpretación"

    Estimado al costo es un fallback operativo conservador. Significa: *"Sabemos lo que pagaste, pero actualmente no sabemos qué pagaría el mercado."*

---

## 💸 Asignación de Ingresos entre Lotes {: #income-allocation-across-lots }

Los dividendos e intereses vinculados a un activo se asignan **de forma prorrateada entre los lotes LONG que son
elegibles el día anterior a la fecha del ingreso (D-1)**, y solo entre los lotes mantenidos **en el bróker pagador**.

Regla de asignación exacta:

$$
w_i(D) = \frac{\text{CantElegible}_i(D)}{\sum_j \text{CantElegible}_j(D)}, \qquad
\text{CantElegible}_i(D) = \text{CantAbierta}_i(D-1)
$$

$$
\text{Ingreso}_i = \text{Convertir}(I, ccy, D)\cdot w_i(D)
$$

Donde:

- $I$ = monto del ingreso recibido en la fecha $D$
- $\text{Convertir}(I, ccy, D)$ = ingreso convertido a la divisa de destino en la fecha $D$
- $\text{CantElegible}_i(D)$ = cantidad del lote $i$ abierta en el **bróker pagador** en $D-1$ (la cantidad en
  tránsito saliente de ese bróker sigue contando como originada allí)
- solo los lotes LONG participan en el denominador

La regla **D-1** mantiene limpia la fecha de registro: una compra realizada *en* la fecha del ingreso no genera
esa distribución, y un lote vendido el día anterior tampoco. Los lotes elegibles más grandes reciben una parte
mayor; los lotes mantenidos en otros brókeres, o aún no (o ya no) elegibles, no reciben nada.

!!! warning "Modificado en FIFO v5"

    Las versiones anteriores usaban la propia fecha del ingreso con **todos** los brókeres
    ($\text{CantAbierta}_i(t)$ sobre cada lote). El motor actual usa la elegibilidad D-1 limitada al bróker
    pagador. Si ningún lote es elegible, el ingreso se mantiene como **ingreso huérfano a nivel de activo**
    (nunca se pierde, nunca se asigna al lote equivocado).

!!! tip "Regla de conservación"

    Los montos de lote asignados suman exactamente al total del evento de ingreso convertido. El ingreso se distribuye, no se crea.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-custody-modal" alt="Modal de detalle del lote — la fila Ingreso del Activo muestra el dividendo/interés prorrateado asignado a este lote específico, junto con la insignia Estimado al Costo cuando no hay precio de mercado en vivo disponible">
</div>

La fila **Ingreso del Activo** del modal de detalle del lote es exactamente $\text{Ingreso}_i$ de la fórmula anterior — la porción prorrateada que recibió este lote específico. Cuando el lote no tiene precio de mercado en vivo, el mismo modal también muestra la insignia **Estimado al Costo** de la sección anterior.

---

## 💸 Costes y Métricas Netas {: #costs-and-net-metrics }

Las `FEE` y `TAX` vinculadas a un activo se asignan a los lotes mediante una **escalera determinista de
emparejamiento con operaciones**, y luego se restan para producir las cifras **netas** junto con las brutas.

### Asignación determinista de costes

Un grupo de costes (mismo bróker, mismo día, mismo tipo) se empareja con el primer objetivo no vacío en este orden:

| Coste | Orden de emparejamiento |
|------|----------------|
| `FEE` | operaciones del mismo día → operaciones del día anterior → posiciones abiertas → huérfano a nivel de activo |
| `TAX` | ingreso del mismo día → operaciones del mismo día → ingreso del día anterior → operaciones del día anterior → posiciones abiertas → huérfano a nivel de activo |

Dentro de una operación emparejada, el coste **pasa exactamente a los lotes que esa operación afectó** — el
coste de una COMPRA recae en el lote que abrió, el coste de una VENTA recae en los lotes consumidos en FIFO —
por lo que la atribución de costes nunca contradice el propio emparejamiento FIFO. Los importes se convierten a
la divisa de destino y se almacenan como magnitudes positivas.

!!! tip "Conservación"

    Por grupo, $\sum_i \text{Coste}_i + \text{Huérfano} = \text{Convertir}(\text{grupo}, ccy, D)$. Un coste que
    no encuentra ningún lote elegible (p. ej. una comisión registrada después de que la posición se haya cerrado
    por completo) se convierte en **coste huérfano a nivel de activo** en lugar de descartarse o forzarse sobre
    un lote no relacionado.

### Bruto vs neto

Con los costes atribuidos por lote, LibreFolio reporta tanto el rendimiento bruto como el neto:

$$
\text{GyPTotalNeto}_i = \text{GyPTotal}_i - \text{Comisiones}_i - \text{Impuestos}_i
$$

$$
\text{RendimientoTotalNeto}_i = \frac{\text{GyPTotalNeto}_i}{\text{ValorApertura}_i}
$$

donde $\text{GyPTotal}_i$ ya **incluye** el ingreso (GyP de mercado + GyP realizado + ingreso del activo). La
serie histórica de valor por lote reporta en cambio un GyP neto *solo de capital*,
$\text{gyp}_i - \text{Comisiones}_i - \text{Impuestos}_i$, que **excluye** el ingreso — cada línea neta refleja
su propia contraparte bruta menos los costes.

!!! example "Números canónicos"

    COMPRA 10×100, VENTA 4×120, precio actual 110, dividendo 50, comisiones 8, impuestos 5:
    GyP Total Bruto $= 60 + 80 + 50 = 190$; GyP Total Neto $= 190 - 13 = 177$; sobre un valor de apertura de
    1,000 eso equivale a un rendimiento total del **19%** bruto frente al **17.7%** neto.

Los costes con `asset_id = null` **no** forman parte de esta vista a nivel de lote — son a nivel de cartera y
los gestiona el [Portfolio Engine](../portfolio-engine/roi.md). Véase
[Comisiones e Impuestos](../../../instruments/transaction-types/fee.md) para la teoría a nivel de instrumento.

---

## 📝 Ejemplo Práctico

??? example "Ejemplo: dos lotes, un dividendo, un precio de mercado"

    Supongamos la misma acción, la misma moneda, `qbq = 1`.

    | Fecha | Evento | Cant. Abierta Lote A | Cant. Abierta Lote B | Notes |
    |------|-------|----------------|----------------|-------|
    | Ene 2 | COMPRA 100 @ $10 | 100 | 0 | El lote A se abre con costo original $1,000 |
    | Feb 10 | COMPRA 50 @ $14 | 100 | 50 | El lote B se abre con costo original $700 |
    | Mar 15 | DIVIDENDO $30 | 100 | 50 | Ambos lotes aún están abiertos |
    | Abr 1 | Precio de mercado = $16 | 100 | 50 | Evaluar ambos lotes |

    **Paso 1 — Asignar dividendo prorrateado**

    $$
    w_A = \frac{100}{100 + 50} = \frac{2}{3}
    \qquad
    w_B = \frac{50}{100 + 50} = \frac{1}{3}
    $$

    $$
    \text{Ingreso}_A = 30 \times \frac{2}{3} = 20
    \qquad
    \text{Ingreso}_B = 30 \times \frac{1}{3} = 10
    $$

    **Paso 2 — Rendimiento Abierto para cada lote**

    $$
    \text{RendimientoRelativo}_A = \frac{16}{10} - 1 = 60.00\%
    $$

    $$
    \text{RendimientoRelativo}_B = \frac{16}{14} - 1 \approx 14.29\%
    $$

    **Paso 3 — Valor de mercado y Rendimiento Total**

    $$
    \text{ValorAbierto}_A = 100 \times 16 = 1,600
    \qquad
    \text{ValorAbierto}_B = 50 \times 16 = 800
    $$

    Como aún no se han vendido acciones, los productos y GyP realizados son ambos cero.

    $$
    \text{GyPTotal}_A = (1,600 - 1,000) + 20 = 620
    $$

    $$
    \text{RendimientoTotal}_A = \frac{620}{1,000} = 62.00\%
    $$

    $$
    \text{GyPTotal}_B = (800 - 700) + 10 = 110
    $$

    $$
    \text{RendimientoTotal}_B = \frac{110}{700} \approx 15.71\%
    $$

    **Paso 4 — Rendimiento agregado entre los lotes mostrados**

    $$
    \text{RendimientoAgregado} = \frac{620 + 110}{1,000 + 700} = \frac{730}{1,700} \approx 42.94\%
    $$

    Aunque ambos lotes pertenecen al mismo activo, sus rendimientos difieren porque se abrieron a diferentes precios.

---

## 📚 De Lotes a Métricas Agregadas

Los rendimientos a nivel de lote se pueden agrupar en una serie de rendimiento agregado, pero **los porcentajes no deben sumarse directamente**.

LibreFolio utiliza esta regla agregada exacta entre los lotes mostrados:

$$
\text{GyPAgregado}(t) = \sum_i \left(\text{GyP}_i(t) + \text{Ingreso}_i(t)\right)
$$

$$
\text{ValorAperturaAgregado}(t) = \sum_i \text{CostoOriginal}_i
$$

$$
\text{RendimientoAgregado}(t) = \frac{\text{GyPAgregado}(t)}{\text{ValorAperturaAgregado}(t)}
$$

Esta vista a nivel de lote ayuda a explicar **de dónde** provino el rendimiento. Las métricas de nivel superior, como [ROI](../portfolio-engine/roi.md) y [TWRR](../portfolio-engine/twrr.md), responden preguntas de cartera más amplias:

- **ROI** se centra en la ganancia en relación con el capital invertido
- **TWRR** neutraliza el momento de los flujos de efectivo externos
- El análisis de lotes FIFO explica la contribución y la trayectoria **dentro** de una posición

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-table" alt="Tabla Unificada de Lotes — una fila por lote con fecha de apertura, rendimiento total, valor actual, custodia y estado, las filas exactas por lote que suman las fórmulas agregadas anteriores">
</div>

La **Tabla Unificada de Lotes** enumera exactamente las filas por lote $i$ que suman las fórmulas agregadas anteriores: fecha de apertura, rendimiento total, valor actual, custodia y estado, todo filtrable al mismo conjunto de lotes visibles utilizado por los gráficos.

---

## 🔗 Relacionado

- 📊 **[Precio Medio Ponderado (PMP)](../weighted-average-cost.md)** — vista de base de costo combinada
- 🔁 **[Compra y Venta](../../../instruments/transaction-types/buy-sell.md#fifo-matching)** — breve descripción del emparejamiento FIFO
- 💸 **[Dividendo e Interés](../../../instruments/transaction-types/dividend-interest.md)** — fuente de eventos de ingresos vinculados a activos
- 💰 **[Fiscalidad](../../../fundamentals/taxation.md)** — contexto de plusvalías y emparejamiento de lotes
- ⚙️ **[Servicio de Análisis de Lotes](../../../../developer/backend/transactions/lots_analysis_service.md)** — inmersión profunda en la implementación para desarrolladores
