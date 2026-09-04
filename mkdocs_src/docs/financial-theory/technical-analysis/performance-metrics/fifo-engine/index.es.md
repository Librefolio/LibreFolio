# 🧬 Motor FIFO — Ciclo de Vida de Lotes y Modelo de Emparejamiento

## 💡 Descripción General

Mientras que el [Precio Medio Ponderado (PMP)](../weighted-average-cost.md) fusiona cada adquisición de una posición en un promedio continuo, el motor FIFO de LibreFolio realiza un seguimiento de **lotes individuales** — uno por lote de adquisición — a lo largo de todo su ciclo de vida: apertura, cierres parciales, transferencias entre brókeres, divisiones y cierre total final.

Esta página describe la **mecánica** de ese motor: cómo se crean, emparejan y cierran los lotes. El motor FIFO es independiente del feed de precios. Reproduce cantidades, lotes, fragmentos, transferencias y cierres realizados. Los niveles de valoración actuales residen fuera de él: [Resolución de Precios](../portfolio-engine/price-resolution.md) y `LotsAnalysisService` suministran las marcas de referencia/actuales y el comportamiento al coste estimado. Para las **métricas** derivadas de este motor (Retorno Abierto/Total, escalado qbq, asignación de ingresos, un ejemplo práctico), consulte [Análisis de Lotes FIFO](fifo-lot-analysis.md).

!!! info "Dos motores, dos preguntas"

    [Motor de Cartera](../index.md) (basado en PMP) responde: _"¿Cuál es mi precio medio ponderado para esta posición?"_

    El motor FIFO responde una pregunta estructuralmente diferente: _"¿Qué lote específico de unidades estoy vendiendo y cómo se desempeñó exactamente ese lote?"_

---

## 🧱 ¿Qué es un Lote?

Un **lote** es un lote de adquisición económica para un activo: una sola COMPRA, el remanente abierto de un ajuste de inventario, o una transferencia de entrada que conserva su costo base original. Un lote mantiene su propia identidad durante toda su vida, incluso cuando se mueve entre brókeres o se divide en partes.

| Propiedad | Significado |
|-----------|-------------|
| Dirección | `LONG` (comprado primero) o `SHORT` (vendido primero, solo donde el bróker permita ventas en corto) |
| Fecha y bróker de apertura | Dónde y cuándo se creó el lote |
| Cantidad y costo originales | Fijados en la apertura, posteriormente reescalados solo por divisiones — nunca por transferencias |
| Cantidad abierta | Cuánto del lote **no** ha sido emparejado aún por una transacción opuesta |
| Custodia | Qué bróker (o brókeres, a lo largo del tiempo) posee actualmente la cantidad abierta |
| Precio de referencia | `reference_unit_price` más `reference_price_source` (`exact`, `fallback`, `none`) |

---

## 🔁 Estados del Ciclo de Vida del Lote

| Estado | Significado |
|--------|-------------|
| **ABIERTO** | Nada ha sido emparejado aún — la cantidad original completa aún se mantiene |
| **PARCIALMENTE_CERRADO** | Parte, pero no toda, del lote ha sido emparejada por transacciones opuestas posteriores |
| **CERRADO** | Todo el lote ha sido emparejado — no queda nada abierto |

Un lote avanza ABIERTO → PARCIALMENTE_CERRADO → CERRADO estrictamente hacia adelante en el tiempo a medida que el emparejamiento lo consume; nunca se reabre. Independientemente de este ciclo de vida, un lote también puede ser etiquetado:

- **EN_TRÁNSITO** — parte de su cantidad abierta está actualmente en medio de una transferencia entre brókeres
- **DISTRIBUIDO** — su cantidad abierta está actualmente dividida en más de una ubicación de custodia a la vez
- **DEGRADADO** — se registró un problema de calidad de datos contra este lote específico (consulte [Calidad de Datos](#data-quality-best-effort-not-all-or-nothing) a continuación)

---

## 📅 Procesamiento Cronológico de Eventos

LibreFolio reproduce cada transacción de un activo **en orden cronológico**, clasificando cada una en un tipo de evento:

| Evento | Efecto |
|--------|--------|
| COMPRA | Primero cierra cualquier lote SHORT abierto en ese bróker; cualquier remanente abre un nuevo lote LONG |
| VENTA | Cierra lotes LONG abiertos en orden FIFO en ese bróker; cualquier remanente abre un nuevo lote SHORT solo donde el bróker permita ventas en corto |
| Ajuste de entrada/salida | Misma lógica de emparejamiento que COMPRA/VENTA, a costo cero |
| DIVISIÓN | Reescala la cantidad y el costo unitario de cada lote abierto del activo |
| Transferencia (salida/llegada) | Mueve la custodia de la cantidad abierta de un lote de un bróker a otro |

!!! info "Orden del mismo día"

    Cuando varios eventos ocurren en la misma fecha, LibreFolio siempre los procesa en un orden fijo — salidas de transferencia, luego llegadas de transferencia, luego divisiones, luego compras/ventas/ajustes ordinarios — para que las transferencias y divisiones del mismo día siempre vean un estado de custodia consistente.

---

## ⛏️ Emparejamiento FIFO

Cuando un evento de cierre (una VENTA, o la etapa de dirección opuesta de un ajuste) necesita consumir una cantidad $Q$, LibreFolio siempre empareja contra el **lote abierto más antiguo primero**, en ese mismo bróker:

$$
\text{OrdenDeEmparejamiento} = \text{ordenar por } (\text{FechaDeApertura}, \text{IdDelLote})
$$

Recorre esta lista ordenada, cerrando cantidad del lote más antiguo hasta que $Q$ esté completamente emparejada, pasando al siguiente lote más antiguo solo cuando el actual se agota. La ganancia o pérdida realizada se calcula **por pieza emparejada**, utilizando el precio transportado por el fragmento de lote exacto consumido:

$$
\text{GananciaPérdidaRealizada}_{\text{LONG}} = \text{CantidadEmparejada} \times (\text{PrecioCierre} - \text{CostoUnitarioDelLote})
$$

$$
\text{GananciaPérdidaRealizada}_{\text{SHORT}} = \text{CantidadEmparejada} \times (\text{CostoUnitarioDelLote} - \text{PrecioCierre})
$$

Esta es la razón por la que dos lotes del mismo activo, comprados en diferentes momentos y precios, pueden mostrar resultados realizados muy diferentes aunque luego se emparejen el mismo día al mismo precio — consulte el ejemplo práctico en [Análisis de Lotes FIFO](fifo-lot-analysis.md).

---

## ✂️ Divisiones — Reescalado de Cantidad/Precio

Una división de acciones (o contra-división) con proporción $r$ reescala cada **fragmento actualmente abierto** de cada lote afectado:

$$
\text{NuevaCantidad} = \text{Cantidad} \times r
\qquad
\text{NuevoCostoUnitario} = \frac{\text{CostoUnitario}}{r}
$$

El costo económico de la posición es invariante a través de una división — solo la cantidad y el costo por unidad se mueven, en direcciones opuestas, por lo que $\text{Cantidad} \times \text{CostoUnitario}$ permanece constante para cada lote.

---

## 🚚 Transferencias — Movimiento de Custodia, No una Venta

Una transferencia entre brókeres se modela como un **cambio de custodia**, nunca como una disposición:

- **Salida** — LibreFolio extrae la cantidad transferida del bróker de origen en orden FIFO. Si la transferencia tarda más de un día en liquidarse, abre un fragmento de custodia temporal **en tránsito** mientras tanto.
- **Llegada** — Al llegar, el fragmento en tránsito se cierra y un fragmento equivalente se reabre en el bróker de destino, trasladando la **misma cantidad y costo unitario**.

La identidad del lote, la fecha de apertura y el costo original nunca cambian debido a una transferencia — solo *dónde* se mantiene actualmente. Nunca se realiza ninguna ganancia o pérdida por una transferencia.

Este historial de custodia — qué bróker (o en tránsito) mantuvo la cantidad abierta de un lote, y cuánto, en cada punto en el tiempo — es exactamente lo que alimenta la línea de tiempo de **Vida y Custodia del Lote** en el panel [Análisis de Lotes FIFO](../../../../user/dashboard/positions.md#fifo-lots-analysis): cada segmento de barra está coloreado por el bróker de custodia que lo mantiene, y su grosor refleja la cantidad mantenida durante ese segmento.

---

## ⚠️ Calidad de Datos: El Mejor Esfuerzo, No Todo o Nada {: #data-quality-best-effort-not-all-or-nothing }

Si el historial de transacciones contiene algo que el motor no puede resolver completamente — por ejemplo, una transacción de cierre sin un lote abierto correspondiente en ese bróker, o una transferencia cuya etapa emparejada falta — LibreFolio **no** aborta todo el cálculo. Registra el problema específico, marca el(los) lote(s) afectado(s) como degradados y continúa procesando el resto del historial con los mejores datos disponibles.

El resultado general se marca entonces como **completo** o **degradado** en su conjunto, pero los gráficos y tablas construidos sobre un resultado degradado aún se renderizan normalmente para cada lote que **no** fue afectado. Puede ver esto reflejado como un banner de calidad de datos en el panel [Análisis de Lotes FIFO](../../../../user/dashboard/positions.md#fifo-lots-analysis).

---


## 🔗 Relacionados

- 🔬 **[Análisis de Lotes FIFO](fifo-lot-analysis.md)** — Métricas derivadas de este motor: Retorno Abierto/Total por lote, escalado qbq, asignación de ingresos, ejemplo práctico
- 🧭 **[Resolución de Precios](../portfolio-engine/price-resolution.md)** — Niveles de valoración usados por el servicio de lotes
- ⚙️ **[Motor de Cartera](../index.md)** — El motor agregado/complementario basado en PMP, y cómo se relacionan ambos
- 📊 **[Precio Medio Ponderado (PMP)](../weighted-average-cost.md)** — Costo base combinado a nivel de posición
- 🧬 **[Motor de Lotes FIFO (Manual del Desarrollador)](../../../../developer/backend/transactions/fifo_lot_engine.md)** — Inmersión profunda en la implementación: clases, despacho de eventos, restricciones a nivel de código
- 📈 **[Descripción General de Métricas de Rendimiento](../index.md)** — Todas las métricas de rendimiento de un vistazo
