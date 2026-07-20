# 📈 Métricas de Rendimiento

Al evaluar el éxito de una cartera de inversiones, no basta con mirar solo el saldo total o la ganancia absoluta. Para comprender realmente el rendimiento, necesitas métricas estandarizadas que respondan diferentes preguntas: "¿Cómo se desempeñaron mis activos?", "¿Qué tan buena fue mi elección del momento?" y "¿Cuál es el rendimiento de esta operación específica?".

---

## 🎭 Los Dos Actores en Tu Cartera

Para entender por qué existen múltiples métricas, imagina que hay dos "actores" diferentes gestionando tu patrimonio:

1. **El Mercado (Los Activos):** Hace que los precios de las cosas que posees suban o bajen.
2. **Tú (El Inversor):** Decides *cuándo* depositar o retirar efectivo de la cartera.

Estos dos actores pueden tener rendimientos muy diferentes. Podrías elegir una excelente acción (El Mercado se desempeña bien), pero podrías comprarla en el pico justo antes de una caída (Tú te desempeñas mal). LibreFolio utiliza diferentes métricas para aislar estos dos comportamientos.

---

## 📚 Temas en este Capítulo

Las métricas de rendimiento de LibreFolio están organizadas en torno a tres motores de cálculo. Cada uno tiene su propia página de descripción general con el modelo matemático completo.

### ⚙️ Motor de Cartera (Portfolio Engine)

Contabilidad agregada basada en PMP para toda la cartera (o cualquier ámbito de bróker/activo).

| Métrica / Concepto | Descripción |
|------------------|-------------|
| **[Descripción General del Motor de Cartera](portfolio-engine/index.md)** | Modelo matemático completo: cadena de valoración, PMP, agregación, modelo de 3 fondos, contribución, arquitectura pre-frame/frame. |
| **[Valor Liquidativo (NAV)](portfolio-engine/nav.md)** | Valoración de mercado total de la cartera (activos + efectivo + en tránsito). Utiliza la cadena de valoración: Precio de Mercado → Último Precio de Compra → Falta. |
| **[Valor Contable (Book Value)](portfolio-engine/book-value.md)** | Coste contable histórico de las posiciones abiertas (PMP × cantidad) más efectivo. La diferencia con el NAV = P&L no realizado. |
| **[P&L del Período](portfolio-engine/period-pnl.md)** | Ganancia/pérdida monetaria ajustada por flujo de caja en una ventana. Se descompone en: delta no realizado + realizado + ingresos − comisiones. Incluye atribución de contribución por activo. |
| **[Capital Depositado y P&L Total](portfolio-engine/deposited-capital.md)** | Capital externo neto desde el inicio. Documenta el modelo de descomposición de efectivo basado en eventos de **3 fondos** (K, R, W) con reglas formales de actualización a nivel de transacción. |
| **[Efecto del Momento (Timing Effect)](portfolio-engine/timing-effect.md)** | Diferencia entre MWRR Acumulado y TWRR Acumulado — cuantifica el impacto del momento del flujo de caja en los rendimientos. |
| **[ROI Simple](portfolio-engine/roi.md)** | Rendimiento porcentual relativo al capital neto invertido. Simple pero sujeto a la dilución del flujo de caja. |
| **[TWRR](portfolio-engine/twrr.md)** | Tasa de Rendimiento Ponderada por Tiempo. Rendimiento puro del activo/estrategia, neutralizando el momento de depósitos/retiros. |
| **[MWRR (XIRR)](portfolio-engine/mwrr.md)** | Tasa de Rendimiento Ponderada por Dinero. Rendimiento personal del inversor que considera el momento del flujo de caja. Formas anualizada y acumulada. |

### 🔬 Motor FIFO

Contabilidad por lote: rastrea cada lote de adquisición a través de su propio ciclo de vida en lugar de combinarlo en un promedio.

| Métrica / Concepto | Descripción |
|------------------|-------------|
| **[Descripción General del Motor FIFO](fifo-engine/index.md)** | Estados del ciclo de vida del lote, procesamiento cronológico de eventos, emparejamiento FIFO, divisiones y transferencias entre brókers. |
| **[Análisis de Lotes FIFO](fifo-engine/fifo-lot-analysis.md)** | Complemento por lote al PMP: rastrea cada lote de adquisición a través de su propio ciclo de vida, empareja las ventas en orden FIFO y calcula el rendimiento abierto/total por lote. |

### Precio Medio Ponderado (Weighted Average Cost)

| Métrica / Concepto | Descripción |
|------------------|-------------|
| **[Precio Medio Ponderado](weighted-average-cost.md)** | PMP iterativo consciente del inventario por posición (bróker, activo). Calculado en línea durante el bucle diario del motor. |

---

## ⚖️ Guía de Comparación de Métricas

Para ayudarte a elegir la métrica adecuada para tu análisis, utiliza esta guía de comparación:

### 1. [Valor Liquidativo (NAV) / Patrimonio Neto](portfolio-engine/nav.md)
* **Pregunta Clave:** "¿Cuánto vale la cartera en el ámbito seleccionado en este momento?"
* **Concepto de Fórmula:** $\text{Valor de Mercado} + \text{Efectivo} + \text{Activos en Tránsito}$ al final del período.
* **Mejor Caso de Uso:** Instantánea de la riqueza absoluta en la fecha de fin seleccionada (`date_to`).

### 2. [Valor Contable (Book Value)](portfolio-engine/book-value.md)
* **Pregunta Clave:** "¿Cuánto costó construir mi cartera actual?"
* **Concepto de Fórmula:** $\text{Base de Coste Abierta} + \text{Efectivo} + \text{Valor Contable en Tránsito}$ utilizando el Precio Medio Ponderado (PMP).
* **Mejor Caso de Uso:** Evaluar los costes de adquisición y compararlos con el valor de mercado actual (NAV) para encontrar ganancias latentes.

### 3. [P&L del Período](portfolio-engine/period-pnl.md)
* **Pregunta Clave:** "¿Cuánto dinero gané o perdí realmente durante este período?"
* **Concepto de Fórmula:** $\text{NAV}_{\text{final}} - \text{NAV}_{\text{inicio}} - \text{Flujos Externos Netos}$.
* **Mejor Caso de Uso:** Medir las ganancias del período en moneda absoluta, independientemente de las inyecciones/retiros de efectivo del inversor.

### 4. [Efecto del Momento (Timing Effect)](portfolio-engine/timing-effect.md)
* **Pregunta Clave:** "¿Cómo afectaron el momento y el tamaño de mis flujos de efectivo a mi rendimiento general en comparación con una estrategia de comprar y mantener?"
* **Concepto de Fórmula:** $\text{MWRR}_{\text{acumulado}} - \text{TWRR}_{\text{acumulado}}$.
* **Mejor Caso de Uso:** Diagnosticar si los depósitos y retiros añadieron valor ($>0$ pp) o lastraron el rendimiento ($<0$ pp).

### 5. [ROI Simple](portfolio-engine/roi.md)
* **Pregunta Clave:** "¿Cuánto gané en relación con el capital neto que invertí?"
* **Denominador de la Fórmula:** Precio Medio Ponderado (PMP).
* **Limitaciones:** No tiene en cuenta *cuándo* ocurrieron los flujos de efectivo, lo que provoca una dilución del flujo de efectivo al comprar más de un activo posteriormente.

### 6. [TWRR (Tasa de Rendimiento Ponderada por Tiempo)](portfolio-engine/twrr.md)
* **Pregunta Clave:** "¿Cómo se desempeñó mi asignación/estrategia de activos elegida, ignorando el momento de mis flujos de efectivo?"
* **Concepto de Fórmula:** Divide la línea de tiempo en cada flujo de efectivo, calcula los rendimientos de los subperíodos y los multiplica.
* **Mejor Caso de Uso:** Comparar tu rendimiento con índices de referencia externos (como el S&P 500) o evaluar el rendimiento puro de los activos.

### 7. [MWRR Anualizada (Tasa de Rendimiento Ponderada por Dinero)](portfolio-engine/mwrr.md#annualized-mwrr)
* **Pregunta Clave:** "¿A qué tasa anual compuesta creció mi capital real, considerando mis depósitos y retiros?"
* **Concepto de Fórmula:** Resuelve la tasa interna de rendimiento ($r$) que iguala el valor presente neto de todos los flujos de efectivo a cero.
* **Mejor Caso de Uso:** Comparar tu rendimiento personal con las tasas de interés a largo plazo o evaluar el crecimiento compuesto en horizontes largos. Puede ser muy volátil en ventanas cortas.

### 8. [MWRR Acumulada](portfolio-engine/mwrr.md#cumulative-mwrr)
* **Pregunta Clave:** "¿Cuál es el rendimiento acumulado equivalente ponderado por dinero durante esta ventana de tiempo seleccionada?"
* **Concepto de Fórmula:** Compone la MWRR anualizada para el número real de días transcurridos.
* **Mejor Caso de Uso:** Gráficos en serie y widgets de panel de control para comparar visualmente las tendencias de rendimiento junto con TWRR y ROI.

---

## 💡 El Ejemplo Práctico (TWRR vs MWRR vs ROI)

Veamos un ejemplo extremo para ver cómo TWRR, MWRR y ROI Simple cuentan historias diferentes, pero matemáticamente correctas.

* **Mes 1:** Compras **€1.000** de una acción. Al mes siguiente, la acción se duplica (+100%). Ahora tienes **€2.000**.
* **Mes 2:** Depositas otros **€100.000** en la misma acción. Ahora tienes €102.000 invertidos.
* **Mes 3:** La acción cae un **-10%**. Tu capital total se reduce a **€91.800**.

Esto es lo que LibreFolio calculará para este escenario:

### TWRR Acumulada: +80.00%
Los activos que elegiste subieron un +100% y luego cayeron un -10%. Matemáticamente:

$$
(1 + 1.00) \times (1 - 0.10) - 1 = +80.00\%
$$

Esto aísla el rendimiento puro de la acción. Tu *selección de activos* fue excelente. Si hubieras invertido todo tu dinero el día 1, habrías obtenido un rendimiento del 80%.

### ROI Simple: -9.11%
Depositaste un total de €101.000 de tu propio bolsillo (€1.000 + €100.000), pero actualmente posees €91.800:

$$
ROI = \frac{91.800 - 101.000}{101.000} = -9.11\%
$$

Esto representa tu ganancia/pérdida real y bruta en la cartera en relación con tu capital neto invertido.

### MWRR Acumulada: -16.99%
Debido a que depositaste €100.000 justo en el pico antes de una caída, tu elección del momento perjudicó tu rendimiento significativamente:

$$
\text{MWRR}_{\text{acumulada}} \approx -16.99\%
$$

Este rendimiento acumulado ponderado por dinero representa el rendimiento de un "euro teórico" bajo el momento real de tus flujos de efectivo.

### MWRR Anualizada: -67.19%
Dado que la caída sustancial ocurrió en una ventana de tiempo muy corta (31 días) sobre una base de capital masiva (€100.000), la tasa compuesta anualizada de pérdida es muy alta:

$$
\text{MWRR}_{\text{anualizada}} \approx -67.19\%
$$

Esto representa la velocidad anualizada de pérdida de capital durante esta ventana específica.

---

## ⚖️ Por Qué LibreFolio Muestra Ambos Uno al Lado del Otro

Al colocar TWRR y MWRR uno al lado del otro en tu panel de control, LibreFolio te brinda un diagnóstico conductual inmediato:

* **TWRR > MWRR:** *"Estás eligiendo buenas inversiones, pero tu elección del momento es mala. Probablemente estés comprando en el pico (FOMO) y reduciendo tus rendimientos personales."*
* **MWRR > TWRR:** *"¡Tienes un excelente sentido del momento! Estás comprando activos con descuento cuando el mercado cae, impulsando tus rendimientos personales por encima del promedio del mercado."*

---

## 🔗 Integración UI y Enlaces de Ayuda del Panel de Control

Para facilitar la navegación, el panel de control de LibreFolio presenta iconos de ayuda y enlaces adyacentes a cada métrica. Al hacer clic en estos enlaces, se te redirige directamente al capítulo de teoría financiera relevante:

* Los widgets de **Patrimonio Neto (NAV)** enlazan directamente a la [Página de NAV / Patrimonio Neto](portfolio-engine/nav.md).
* Los campos de **Valor Contable (Book Value)** enlazan directamente a la [Página de Valor Contable](portfolio-engine/book-value.md).
* Los widgets de **P&L del Período** enlazan directamente a la [Página de P&L del Período](portfolio-engine/period-pnl.md).
* Los widgets de **Efecto del Momento (Timing Effect)** enlazan directamente a la [Página de Efecto del Momento](portfolio-engine/timing-effect.md).
* Los widgets de **ROI** enlazan directamente a la [Página de ROI Simple](portfolio-engine/roi.md).
* Los widgets de **TWRR** enlazan directamente a la [Página de TWRR](portfolio-engine/twrr.md).
* Los widgets de **MWRR** enlazan directamente a la [Página de MWRR](portfolio-engine/mwrr.md).
* **Capital Depositado / P&L Total** (información emergente del gráfico de crecimiento) enlaza a la [Página de Capital Depositado y P&L Total](portfolio-engine/deposited-capital.md).
