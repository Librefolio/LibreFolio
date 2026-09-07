# 📈 Métricas de rendimiento

Al evaluar el éxito de una cartera de inversiones, no basta con mirar únicamente el saldo total o el beneficio absoluto. Para comprender realmente el rendimiento, necesitas métricas estandarizadas que respondan a diferentes preguntas: «¿Cómo han rendido mis activos?», «¿Fue buena mi sincronización?» y «¿Cuál es la rentabilidad de esta operación concreta?».

---

## 🎭 Los dos actores de tu cartera

Para entender por qué existen múltiples métricas, imagina que hay dos «actores» diferentes gestionando tu patrimonio:

1. **El mercado (los activos):** Hace que los precios de las cosas que posees suban o bajen.
2. **Tú (el inversor):** Decides *cuándo* depositar o retirar efectivo de la cartera.

Estos dos actores pueden tener rendimientos muy diferentes. Puede que elijas una acción excelente (el mercado se comporta bien), pero puedes comprarla justo en el máximo, momentos antes de un desplome (tú te comportas mal). LibreFolio utiliza diferentes métricas para aislar estos dos comportamientos.

---

## 📚 Temas de este capítulo

Las métricas de rendimiento de LibreFolio se organizan en torno a tres motores de cálculo. Cada uno tiene su propia página de descripción general con el modelo matemático completo.

### ⚙️ Motor de cartera

Contabilidad agregada basada en PMP para toda la cartera (o cualquier ámbito de bróker/activo).

| Métrica / Concepto | Descripción |
|------------------|-------------|
| **[Descripción general del motor de cartera](portfolio-engine/index.md)** | Modelo matemático completo: resolvedor de precios unificado, PMP, agregación, modelo de 3 grupos, contribución, arquitectura pre-frame/frame. |
| **[Resolución de precios](portfolio-engine/price-resolution.md)** | Niveles del resolvedor unificado: MARKET → TRADE_AVG → CARRIED → MISSING, con marcas nativas y FX por fecha. |
| **[Valor liquidativo (NAV)](portfolio-engine/nav.md)** | Valoración total de mercado de la cartera (activos + efectivo + en tránsito), utilizando el resolvedor unificado. |
| **[Valor contable](portfolio-engine/book-value.md)** | Coste contable histórico de las posiciones abiertas (PMP × cantidad) más el efectivo. La diferencia con el NAV = P&L no realizado. |
| **[P&L del período](portfolio-engine/period-pnl.md)** | Beneficio/pérdida monetarios ajustados por flujo de caja en un período. Se descompone en: delta no realizada + realizada + ingresos − comisiones. Incluye la atribución de la contribución por activo. |
| **[Capital depositado y P&L total](portfolio-engine/deposited-capital.md)** | Capital externo neto desde el inicio. Documenta el modelo de descomposición del efectivo **de 3 grupos dirigido por eventos** (K, R, W) con reglas formales de actualización a nivel de transacción. |
| **[Efecto de sincronización](portfolio-engine/timing-effect.md)** | Diferencia entre la MWRR acumulada y la TWRR acumulada — cuantifica el impacto de la sincronización de los flujos de caja en las rentabilidades. |
| **[ROI simple](portfolio-engine/roi.md)** | Rentabilidad porcentual en relación con el capital neto invertido. Sencillo, pero sujeto a la dilución por los flujos de caja. |
| **[Rentabilidad neta anualizada](portfolio-engine/net-annualized-return.md)** | Definiciones de CAGR neto para posiciones, contribución del período y lotes FIFO, con una ventana mínima de 30 días. |
| **[TWRR](portfolio-engine/twrr.md)** | Tasa de rentabilidad ponderada en el tiempo. Rendimiento puro de activos/estrategia, neutralizando la sincronización de depósitos/retiros. |
| **[MWRR (XIRR)](portfolio-engine/mwrr.md)** | Tasa de rentabilidad ponderada por dinero. Rendimiento personal del inversor que tiene en cuenta la sincronización de los flujos de caja. Formas anualizada y acumulada. |

### 🔬 Motor FIFO

Contabilidad por lote: realiza un seguimiento de cada lote de adquisición a lo largo de su propio ciclo de vida, en lugar de combinarlo en un único promedio.

| Métrica / Concepto | Descripción |
|------------------|-------------|
| **[Descripción general del motor FIFO](fifo-engine/index.md)** | Estados del ciclo de vida del lote, procesamiento cronológico de eventos, emparejamiento FIFO, divisiones y transferencias entre brókers. |
| **[Análisis de lotes FIFO](fifo-engine/fifo-lot-analysis.md)** | Complemento por lote del PMP: realiza un seguimiento de cada lote de adquisición a lo largo de su propio ciclo de vida, empareja las ventas en orden FIFO y calcula la rentabilidad abierta/total por lote. |

### 📊 Precio medio ponderado (PMP)

| Métrica / Concepto | Descripción |
|------------------|-------------|
| **[Precio medio ponderado (PMP)](weighted-average-cost.md)** | PMP iterativo que tiene en cuenta el inventario por posición (bróker, activo). Se calcula directamente durante el bucle diario del motor. |

---

## ⚖️ Guía de comparación de métricas

Para ayudarte a elegir la métrica adecuada para tu análisis, utiliza esta guía de comparación:

### 💼 1. [Valor liquidativo (NAV) / Patrimonio neto](portfolio-engine/nav.md)
* **Pregunta clave:** «¿Cuánto vale ahora mismo la cartera del ámbito seleccionado?»
* **Concepto de la fórmula:** $\text{Market Value} + \text{Cash} + \text{In Transit Assets}$ al final del período.
* **Mejor caso de uso:** Instantánea de la riqueza absoluta en la fecha final seleccionada (`date_to`).

### 📖 2. [Valor contable](portfolio-engine/book-value.md)
* **Pregunta clave:** «¿Cuánto me costó construir mi cartera actual?»
* **Concepto de la fórmula:** $\text{Open Cost Basis} + \text{Cash} + \text{In Transit Book Value}$ utilizando el precio medio ponderado (PMP).
* **Mejor caso de uso:** Evaluar los costes de adquisición y compararlos con el valor de mercado actual (NAV) para encontrar ganancias latentes.

### 📊 3. [P&L del período](portfolio-engine/period-pnl.md)
* **Pregunta clave:** «¿Cuánto dinero gané o perdí realmente durante este período?»
* **Concepto de la fórmula:** $\text{NAV}_{\text{end}} - \text{NAV}_{\text{start}} - \Delta\text{CapitalBaseline}$.
* **Mejor caso de uso:** Medir las ganancias del período en términos monetarios absolutos, con independencia de las aportaciones/retiros de efectivo del inversor.

### ⏱️ 4. [Efecto de sincronización](portfolio-engine/timing-effect.md)
* **Pregunta clave:** «¿Cómo afectaron la sincronización y el tamaño de mis flujos de caja a mi rentabilidad general en comparación con una estrategia de comprar y mantener?»
* **Concepto de la fórmula:** $\text{MWRR}_{\text{cumulative}} - \text{TWRR}_{\text{cumulative}}$.
* **Mejor caso de uso:** Diagnosticar si los depósitos y los retiros aportaron valor ($>0$ pp) o lastraron el rendimiento ($<0$ pp).

### 📉 5. [ROI simple](portfolio-engine/roi.md)
* **Pregunta clave:** «¿Cuánto gané en relación con el capital neto que invertí?»
* **Denominador de la fórmula:** Línea base de capital, incluido el capital en especie valorado.
* **Limitaciones:** No tiene en cuenta *cuándo* se produjeron los flujos de caja, lo que provoca una dilución por los flujos de caja al comprar posteriormente más de un activo.

### ⏱️ 6. [TWRR (Tasa de rentabilidad ponderada en el tiempo)](portfolio-engine/twrr.md)
* **Pregunta clave:** «¿Cómo se comportó la asignación de activos/estrategia que elegí, ignorando la sincronización de mi efectivo?»
* **Concepto de la fórmula:** Divide la línea temporal en cada flujo de caja, calcula las rentabilidades de los subperíodos y las multiplica.
* **Mejor caso de uso:** Comparar tu rendimiento con benchmarks externos (como el S&P 500) o evaluar el rendimiento puro de los activos.

### 📈 7. [MWRR anualizada (Tasa de rentabilidad ponderada por dinero)](portfolio-engine/mwrr.md#annualized-mwrr)
* **Pregunta clave:** «¿A qué tasa anual compuesta creció mi capital real, considerando mis depósitos y retiros?»
* **Concepto de la fórmula:** Resuelve la tasa interna de rendimiento ($r$) que hace que el valor actual neto de todos los flujos de caja sea cero.
* **Mejor caso de uso:** Comparar tu rendimiento personal con los tipos de interés a largo plazo o evaluar el crecimiento compuesto en horizontes largos. Puede ser muy volátil en ventanas cortas.

### 📊 8. [MWRR acumulada](portfolio-engine/mwrr.md#cumulative-mwrr)
* **Pregunta clave:** «¿Cuál es la rentabilidad acumulada equivalente ponderada por dinero en esta ventana de tiempo seleccionada?»
* **Concepto de la fórmula:** Compone la MWRR anualizada durante el número real de días transcurridos.
* **Mejor caso de uso:** Gráficos de series temporales y widgets del panel de control para comparar visualmente las tendencias de rendimiento en paralelo con TWRR y ROI.

---

## 💡 El ejemplo práctico (TWRR vs MWRR vs ROI)

Veamos un ejemplo extremo para comprobar cómo TWRR, MWRR y el ROI simple cuentan historias diferentes, aunque matemáticamente correctas.

* **Mes 1:** Compras **1.000 €** de una acción. Al mes siguiente, la acción se duplica (+100 %). Ahora tienes **2.000 €**.
* **Mes 2:** Depositas otros **100.000 €** en exactamente la misma acción. Ahora tienes 102.000 € invertidos.
* **Mes 3:** La acción cae un **-10 %**. Tu capital total se reduce a **91.800 €**.

Esto es lo que LibreFolio calculará para este escenario:

### 📊 TWRR acumulada: +80,00 %

Los activos que elegiste subieron un +100 % y luego cayeron un -10 %. Matemáticamente:

$$
(1 + 1.00) \times (1 - 0.10) - 1 = +80.00\%
$$

Esto aísla el rendimiento puro de la acción. Tu *selección de activos* fue excelente. Si hubieras invertido todo tu dinero el día 1, habrías obtenido una rentabilidad del 80 %.

### 📉 ROI simple: -9,11 %

Depositaste un total de 101.000 € de tu propio bolsillo (1.000 € + 100.000 €), pero actualmente tienes 91.800 €:

$$
ROI = \frac{91,800 - 101,000}{101,000} = -9.11\%
$$

Esto representa la ganancia/pérdida real y sin ajustar de tu dinero en relación con tu capital neto invertido.

### 💵 MWRR acumulada: -16,99 %

Debido a que depositaste 100.000 € justo en el máximo antes de una caída, tu sincronización lastró significativamente tu rentabilidad:

$$
\text{MWRR}_{\text{cumulative}} \approx -16.99\%
$$

Esta rentabilidad acumulada ponderada por dinero representa el rendimiento de un «euro teórico» bajo tu sincronización real de los flujos de caja.

### 📈 MWRR anualizada: -67,19 %

Dado que la caída sustancial se produjo en una ventana de tiempo muy corta (31 días) sobre una base de capital masiva (100.000 €), la tasa compuesta anualizada de pérdida es muy alta:

$$
\text{MWRR}_{\text{annualized}} \approx -67.19\%
$$

Esto representa la velocidad anualizada de pérdida de capital en esta ventana específica.

---

## ⚖️ Por qué LibreFolio muestra ambas una al lado de la otra

Al colocar TWRR y MWRR una al lado de la otra en tu panel de control, LibreFolio te ofrece un diagnóstico de comportamiento inmediato:

* **TWRR > MWRR:** *«Estás eligiendo buenas inversiones, pero tu sincronización es mala. Es probable que estés comprando en los máximos (FOMO) y lastrando tus rentabilidades personales.»*
* **MWRR > TWRR:** *«¡Tienes una sincronización excelente! Estás comprando activos con descuento cuando el mercado cae, impulsando tus rentabilidades personales por encima de la media del mercado.»*

---

## 🔗 Integración de UI y enlaces de ayuda del panel de control

Para facilitar la navegación, las tres tarjetas KPI del panel de control de LibreFolio — **P&L del período**, **Rentabilidad** y **Patrimonio neto** — tienen cada una un icono de ayuda. El camino hacia estos capítulos de teoría consta de dos pasos:

1. El icono de ayuda abre la sección correspondiente de la página [Tarjetas KPI](../../../user/dashboard/kpi-cards.md) de la guía de usuario ([Tarjeta 1](../../../user/dashboard/kpi-cards.md#card-1-period-pl), [Tarjeta 2](../../../user/dashboard/kpi-cards.md#card-2-returns), [Tarjeta 3](../../../user/dashboard/kpi-cards.md#card-3-net-worth)).
2. Desde allí, cada métrica enlaza con su capítulo de teoría financiera: [P&L del período](portfolio-engine/period-pnl.md), [Valor contable](portfolio-engine/book-value.md), [ROI](portfolio-engine/roi.md), [TWRR](portfolio-engine/twrr.md), [MWRR](portfolio-engine/mwrr.md), [Efecto de sincronización](portfolio-engine/timing-effect.md), [NAV / Patrimonio neto](portfolio-engine/nav.md), [Capital depositado y P&L total](portfolio-engine/deposited-capital.md).

En el resto de la aplicación, la vista previa del PMP en el formulario de transacciones enlaza directamente con el capítulo [Precio medio ponderado (PMP)](weighted-average-cost.md), y cada señal/indicador de los gráficos enlaza con su propia página de teoría.
