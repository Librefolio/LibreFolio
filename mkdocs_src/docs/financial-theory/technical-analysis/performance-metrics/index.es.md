# 📈 Métricas de Rendimiento

Al evaluar el éxito de una cartera de inversión, mirar únicamente el saldo total o el beneficio absoluto no es suficiente. Para entender realmente el rendimiento, necesita métricas estandarizadas que respondan a diferentes preguntas: "¿Cómo se comportaron mis activos?", "¿Qué tan buena fue mi sincronización (timing)?" y "¿Cuál es el retorno de esta operación específica?".

---

## 🎭 Los dos actores de su cartera

Para comprender por qué existen varias métricas, imagine que hay dos "actores" diferentes que gestionan su patrimonio:

1. **El Mercado (Los Activos):** Provoca que los precios de las cosas que posee suban o bajen.
2. **Usted (El Inversor):** Decide *cuándo* depositar o retirar efectivo de la cartera.

Estos dos actores pueden tener rendimientos muy diferentes. Puede elegir una acción excelente (el Mercado se comporta bien), pero comprarla justo en el punto más alto antes de una caída (su rendimiento personal es malo). LibreFolio utiliza diferentes métricas para aislar estos dos comportamientos.

---

## 📚 Temas de este capítulo

| Métrica / Concepto | Descripción |
|--------------------|-------------|
| **[Net Asset Value (NAV)](nav.md)** | Net Worth / Net Asset Value. La valoración de mercado total de la cartera (activos + efectivo) al final de la ventana de tiempo. |
| **[Book Value](book-value.md)** | El coste contable histórico de las posiciones abiertas más el efectivo. Se utiliza para comparar el coste de adquisición con el valor de mercado. |
| **[P&L del Periodo](period-pnl.md)** | La ganancia o pérdida monetaria absoluta de la cartera en la ventana seleccionada, descontando los flujos de efectivo. |
| **[Capital Depositado & P&L Total](deposited-capital.md)** | Capital externo neto aportado desde el origen; el ancla para calcular el P&L Total y el algoritmo de descomposición de efectivo. |
| **[Efecto Timing](timing-effect.md)** | Diferencia entre el MWRR acumulado y el TWRR acumulado. Muestra cuánto afectaron el momento y el importe de sus flujos de efectivo a su rendimiento general. |
| **[ROI Simple](roi.md)** | Porcentaje de retorno absoluto generado por una inversión en relación con su costo. Ideal para evaluar posiciones individuales. |
| **[TWRR](twrr.md)** | Tasa de Retorno Ponderada por el Tiempo (Time-Weighted Rate of Return). Mide el rendimiento puro de los activos subyacentes, ignorando la temporalidad de los flujos de caja. |
| **[MWRR (XIRR)](mwrr.md)** | Tasa de Retorno Ponderada por el Dinero (Money-Weighted Rate of Return). Mide su rendimiento personal como inversor, teniendo en cuenta la temporalidad de los flujos de caja. Abarca tanto la forma **Anualizada** como la **Acumulada**. |
| **[Coste Medio Ponderado](weighted-average-cost.md)** | El coste unitario medio de un activo en una cartera, ponderado por las cantidades adquiridas. |

---

## ⚖️ Guía de Comparación de Métricas

Para ayudarle a elegir la métrica adecuada para su análisis, utilice esta guía comparativa:

### 1. [Net Asset Value (NAV) / Valor Neto](nav.md)
* **Pregunta clave:** "¿Cuánto vale la cartera dentro del alcance seleccionado en este momento preciso?"
* **Concepto de la fórmula:** $\text{Valor de Mercado} + \text{Efectivo} + \text{Activos en Tránsito}$ al final del periodo.
* **Mejor caso de uso:** Instantánea del patrimonio absoluto en la fecha de finalización seleccionada (`date_to`).

### 2. [Valor Contable (Book Value)](book-value.md)
* **Pregunta clave:** "¿Cuánto costó construir mi cartera actual?"
* **Concepto de la fórmula:** $\text{Coste Posiciones Abiertas} + \text{Efectivo} + \text{Coste en Tránsito}$ utilizando el Precio Medio Ponderado (PMP).
* **Mejor caso de uso:** Evaluar el capital comprometido y compararlo con el valor actual de mercado (NAV) para determinar las ganancias latentes.

### 3. [P&L del Periodo](period-pnl.md)
* **Pregunta clave:** "¿Cuánto dinero he ganado o perdido realmente durante este periodo?"
* **Concepto de la fórmula:** $\text{NAV}_{\text{end}} - \text{NAV}_{\text{start}} - \text{Flujos Externos Netos}$.
* **Mejor caso de uso:** Medir las ganancias absolutas del periodo en moneda real, independientemente de los depósitos y retiros del inversor.

### 4. [Efecto Timing](timing-effect.md)
* **Pregunta clave:** "¿Cómo afectaron el momento y la dimensión de mis flujos de efectivo a mi rendimiento general en comparación con una estrategia de comprar y mantener?"
* **Concepto de la fórmula:** $\text{MWRR}_{\text{acumulado}} - \text{TWRR}_{\text{acumulado}}$.
* **Mejor caso de uso:** Diagnosticar si las aportaciones y retiros añadieron valor ($>0$ pp) o redujeron el rendimiento ($<0$ pp).

### 5. [ROI Simple](roi.md)
* **Pregunta clave:** "¿Cuánto he ganado en relación con el capital neto que he invertido?"
* **Denominador de la fórmula:** Precio de Compra Medio (PCM).
* **Limitaciones:** No tiene en cuenta *cuándo* se produjeron los flujos de caja, lo que provoca la diluición del ROI al realizar compras posteriores del mismo activo.

### 6. [TWRR (Tasa de Retorno Ponderada por el Tiempo)](twrr.md)
* **Pregunta clave:** "¿Cómo se comportó mi estrategia o distribución de activos, ignorando la temporalidad de mis ahorros?"
* **Concepto de la fórmula:** Divide la línea de tiempo en cada flujo de caja, calcula los retornos de los subperíodos y los multiplica.
* **Mejor caso de uso:** Comparar su rendimiento con índices de referencia externos (como el S&P 500) o evaluar el rendimiento puro de los activos seleccionados en sí.

### 6. [MWRR Anualizado (Tasa de Retorno Ponderada por el Dinero)](mwrr.md#annualized-mwrr)
* **Pregunta clave:** "¿A qué tasa compuesta anual creció mi capital real, teniendo en cuenta mis depósitos y retiros?"
* **Concepto de la fórmula:** Resuelve la tasa interna de retorno ($r$) que hace que el valor presente neto de todos los flujos de caja sea igual a cero.
* **Mejor caso de uso:** Comparar su rendimiento personal con las tasas de interés a largo plazo o evaluar el crecimiento compuesto en horizontes temporales largos. Puede ser muy volátil en ventanas de tiempo cortas.

### 7. [MWRR Acumulado](mwrr.md#cumulative-mwrr)
* **Pregunta clave:** "¿Cuál es el retorno acumulado equivalente ponderado por el dinero para la ventana de tiempo seleccionada?"
* **Concepto de la fórmula:** Capitaliza el MWRR anualizado por el número real de días transcurridos.
* **Mejor caso de uso:** Gráficos históricos seriales y widgets del panel para comparar visualmente las tendencias de rendimiento lado a lado con TWRR y ROI.

---

## 💡 El ejemplo práctico (TWRR vs MWRR vs ROI)

Veamos un ejemplo extremo para entender cómo el TWRR, el MWRR y el ROI Simple cuentan historias diferentes, pero matemáticamente correctas.

* **Mes 1:** Compra **1.000 €** de una acción. El mes siguiente, la acción se duplica (+100%). Ahora tiene **2.000 €**.
* **Mes 2:** Deposita otros **100.000 €** en la misma acción. Ahora tiene 102.000 € invertidos.
* **Mes 3:** La acción baja un **-10%**. Su capital total cae a **91.800 €**.

Esto es lo que LibreFolio calculará para este escenario:

### TWRR Acumulado: +80,00%
Los activos que eligió subieron un +100% y luego bajaron un -10%. Matemáticamente:

$$
(1 + 1,00) \times (1 - 0,10) - 1 = +80,00\%
$$

Esto aísla el comportamiento puro de la acción. Su selección de activos (*asset picking*) fue excelente. Si hubiera invertido todo su dinero el primer día, habría obtenido un retorno del 80%.

### ROI Simple: -9,11%
Ha depositado un total de 101.000 € de su bolsillo (1.000 € + 100.000 €), pero actualmente tiene 91.800 €:

$$
ROI = \frac{91.800 - 101.000}{101.000} = -9,11\%
$$

Esto representa la ganancia o pérdida real de su cartera en relación con su capital neto invertido.

### MWRR Acumulado: -16,99%
Debido a que depositó 100.000 € justo en el pico antes de una caída, su sincronización (timing) penalizó considerablemente sus retornos:

$$
\text{MWRR}_{\text{acumulado}} \approx -16,99\%
$$

Este retorno acumulado ponderado por el dinero representa el rendimiento de un "euro teórico" sujeto a la sincronización de sus flujos de caja reales.

### MWRR Anualizado: -67,19%
Dado que la caída sustancial ocurrió en una ventana de tiempo muy corta (31 días) sobre una base de capital enorme (100.000 €), la tasa compuesta anualizada de pérdida es extremadamente alta:

$$
\text{MWRR}_{\text{anualizado}} \approx -67,19\%
$$

Esto representa la velocidad anualizada de pérdida de capital durante esta ventana específica.

---

## ⚖️ Por qué LibreFolio muestra ambos lado a lado

Al colocar el TWRR y el MWRR uno al lado del otro en su panel de control, LibreFolio le proporciona un diagnóstico conductual inmediato:

* **TWRR > MWRR:** *"Está eligiendo buenas inversiones, pero su timing es malo. Es probable que esté comprando en el punto más alto (FOMO) y arrastrando sus retornos personales a la baja".*
* **MWRR > TWRR:** *"¡Tiene un timing excelente! Está comprando activos con descuento cuando el mercado cae, impulsando sus retornos personales por encima del promedio del mercado".*

---

## 🔗 Integración en la UI y enlaces de ayuda en el panel de control

Para facilitar la navegación, el panel de control de LibreFolio presenta iconos y enlaces de ayuda junto a cada métrica. Al hacer clic en estos enlaces, se le redirige directamente al capítulo correspondiente de la teoría financiera:

* Los widgets de **Valor Neto (NAV)** enlazan directamente con la [Página del NAV / Net Worth](nav.md).
* Los campos de **Valor Contable** enlazan directamente con la [Página del Valor Contable](book-value.md).
* Los widgets de **P&L del Periodo** enlazan directamente con la [Página del P&L del Periodo](period-pnl.md).
* Los widgets de **Efecto Timing** enlazan directamente con la [Página del Efecto Timing](timing-effect.md).
* Los widgets de **ROI** enlazan directamente con la [Página del ROI Simple](roi.md).
* Los widgets de **TWRR** enlazan directamente con la [Página del TWRR](twrr.md).
* Los widgets de **MWRR** enlazan directamente con la [Página del MWRR](mwrr.md).
