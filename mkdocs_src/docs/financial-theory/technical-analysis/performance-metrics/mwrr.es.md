# 💵 MWRR (Tasa de Retorno Ponderada por el Dinero) / XIRR

*[⬅️ Volver a la Descripción General de Métricas de Rendimiento](index.md)*

## 💡 ¿Qué es?
El MWRR (también conocido como Tasa Interna de Retorno) mide **su rendimiento personal** como inversor. A diferencia de las métricas que solo consideran los activos, el MWRR tiene en cuenta tanto el rendimiento de los activos subyacentes como la **temporalidad (timing) y el volumen** de sus depósitos y retiros.

Para proporcionar una visibilidad completa, LibreFolio distingue entre dos formas de esta métrica: **MWRR Anualizado** y **MWRR Acumulado**.

---

## 📈 MWRR Anualizado vs. MWRR Acumulado

### MWRR Anualizado {: #annualized-mwrr }
El MWRR Anualizado es la tasa compuesta anual de retorno que iguala el valor presente neto (NPV) de todos los flujos de caja con cero.

Esta tasa compuesta es matemáticamente equivalente al **CAGR** (Compound Annual Growth Rate - tasa de crecimiento anual compuesta) de su capital realmente invertido, representando la tasa de crecimiento anual constante necesaria para que el capital inicial alcance el saldo final, teniendo en cuenta todos los movimientos intermedios.

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{\frac{t_i}{365}}}
$$

??? note "🧮 Cómo se desglosa la ecuación NPV"

    #### 1. Forma intuitiva del valor final
    Imagine proyectar el valor neto final de su cartera (NAV) haciendo crecer cada flujo de caja a una tasa compuesta \(r\) :
    
    \[
    NAV_{final} = CF_0 \times (1 + r)^{\frac{d_0}{365}} + CF_1 \times (1 + r)^{\frac{d_1}{365}} + \dots + CF_n \times (1 + r)^{\frac{d_n}{365}}
    \]
    
    Donde \(d_i\) representa el número de días que cada flujo de caja estuvo invertido durante el período.
    
    #### 2. Descontar al Valor Presente Neto (NPV = 0)
    Al dividir ambos lados de la ecuación por \((1 + r)^{\frac{\text{días totales}}{365}}\), trasladamos todos los flujos de caja al inicio del período (\(t_0\)). Esto nos da la ecuación estándar del Valor Presente Neto (NPV) donde la suma de los flujos de caja descontados es igual a cero:
    
    \[
    0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{\frac{t_i}{365}}}
    \]
    
    Donde \(t_i\) es el número de días transcurridos desde el inicio del período hasta la fecha del flujo de caja \(i\).
    
    #### 3. Ejemplo de despliegue de flujos de caja
    Veamos cómo se distribuyen los flujos de caja para una cartera durante un período de 31 días:
    
    * **Día 0:** El valor inicial de la cartera es de 1.000 € (representado como un depósito/inversión).
    * **Día 15:** Deposita 100 €.
    * **Día 31:** El NAV final de la cartera es de 1.150 €.
    
    Primero, construimos la tabla de transacciones desde la perspectiva de la cartera (el dinero que entra en la cartera invertida es negativo, el dinero que se retira es positivo):
    
    | Paso (\(i\)) | Día (\(t_i\)) | Evento | Flujo de caja de la cartera (\(CF_i\)) |
    |------------|-------------|--------|--------------------------------------|
    | 0 | 0 | Saldo Inicial | **-1.000 €** (Salida) |
    | 1 | 15 | Depósito | **-100 €** (Salida) |
    | 2 | 31 | Liquidación Hipotética (NAV) | **+1.150 €** (Entrada) |
    
    Ora desplegamos estas transacciones en la sumatoria del NPV:
    
    \[
    0 = -1000 + \frac{-100}{(1+r)^{\frac{15}{365}}} + \frac{1150}{(1+r)^{\frac{31}{365}}}
    \]
    
    El solver matemático busca de manera iterativa el valor de \(r\) (MWRR Anualizado) que hace que el lado derecho de esta ecuación sea igual a 0.

    #### 4. Anclaje del gráfico acumulado
    Esta convención de signos asegura que el primer día (\(t_0\)), el depósito inicial (\(CF_0 = -1000\)) y la liquidación hipotética (\(CF_1 = +1000\)) se cancelen perfectamente entre sí:
    
    \[
    0 = -1000 + 1000 = 0\%
    \]
    
    Esto ancla el inicio del gráfico del MWRR Acumulado exactamente en el **0%**.

**Descripción de las Variables:**

* $r$ = MWRR Anualizado (que representa el CAGR de su dinero real).
* $CF_i$ = Flujo de caja desde la perspectiva del inversor:
    * **Flujos de caja negativos ($CF_i < 0$):** Capital comprometido con la cartera (depósitos, compras). Esto representa dinero que sale del monedero personal del inversor para ser invertido.
    * **Flujos de caja positivos ($CF_i > 0$):** Capital devuelto al inversor (retiros, dividendos). Esto representa dinero que regresa al monedero del inversor.
    * **Valuación final ($CF_n > 0$):** El Net Asset Value (NAV) o valor neto final de la cartera al final del período, tratado como una entrada positiva (una liquidación hipotética donde toda la cartera se convierte de nuevo en efectivo que regresa al inversor).
* $t_i$ = Días transcurridos desde el inicio del período ($t_0 = 0$).

**Conceptos clave:**

* Representa una **velocidad o tasa compuesta anual** de crecimiento.
* Es ideal para comparaciones a largo plazo (por ejemplo, comparar su rendimiento con la tasa de interés anual de un banco o con el CAGR).
* **Advertencia de volatilidad:** En períodos cortos (por ejemplo, unos pocos días o semanas), el retorno anualizado puede ser muy volátil y mostrar porcentajes extremos porque la matemática extrapola el retorno de un período pequeño a un año completo de 365 días.

### MWRR Acumulado {: #cumulative-mwrr }
El MWRR Acumulado representa el retorno total equivalente durante el período seleccionado, obtenido al capitalizar la tasa anualizada por la duración real de ese período.

**Fórmula Directa (sin raíces, usa directamente $r$):**

$$
\text{MWRR}_{\text{acumulado}} = (1 + r)^{\frac{\text{días}}{365}} - 1
$$

**Fórmula por Tasa Diaria (con raíz):**

$$
\text{MWRR}_{\text{acumulado}} = (1 + r_d)^{\text{días}} - 1 \quad \text{donde} \quad r_d = \sqrt[365]{1 + r} - 1
$$

Ambas fórmulas son matemáticamente equivalentes. Sin embargo, a nivel computacional, se prefiere la fórmula directa con $r$ (sin raíces) una vez encontrada la tasa anualizada $r$, ya que la potenciación directa es más simple y eficiente de calcular para el software.

**Descripción de las Variables:**

* $\text{días}$ = El número real de días naturales en el período seleccionado.

**Conceptos clave:**

* Representa la **distancia total recorrida** durante el período.
* Comienza en 0% y crece a lo largo de la línea de tiempo, lo que la convierte en la métrica adecuada para representarse en el gráfico serial.
* **No es un ROI simple:** Aunque representa un retorno acumulado, se trata de un retorno acumulado ponderado por el dinero (money-weighted). No debe confundirse con el retorno simple del período (ROI), que ignora la temporalidad de los flujos de caja.

---

## 🔢 Ejemplo numérico de 10 años

Veamos un escenario de 10 años para entender cómo la temporalidad afecta al rendimiento y cómo se convierten estas métricas:

* **Día 0:** Deposita **10.000 €**.
* **Día 5:** Deposita otros **90.000 €**.
* **Día 10:** Su valor neto final (NAV) es de **200.000 €**.

### Comparación con el ROI Simple
El ROI simple se calcula únicamente sobre las contribuciones netas totales:

$$
ROI = \frac{200.000 - 100.000}{100.000} = +100\%
$$

### Efecto de la sincronización en el MWRR
Si la mayor parte de su capital (90.000 €) se depositó en el Año 5, justo antes de una fuerte recuperación del mercado de varios años, su dinero trabajó de manera muy eficiente. Debido a que la suma más grande estuvo expuesta a los años de alto crecimiento, su **MWRR Anualizado** será significativamente mayor que el TWRR del mercado.

Utilizando un solver matemático NPV para este escenario específico:
* El **MWRR Anualizado ($r$)** es exactamente del **13,02%**.

### Conversión a MWRR Acumulado
Capitalizando este retorno anualizado del 13,02% durante el período de 10 años:

$$
\text{MWRR}_{\text{acumulado}} = (1 + 0.130227)^{10} - 1 \approx +240.14\%
$$

### ¿Qué significa +240.14%?
* **No** significa que sus 100.000 € de contribuciones totales se hayan convertido en 340.140 €.
* Significa que un **euro teórico**, invertido al principio del período de 10 años y no vuelto a tocar, se habría convertido en 3,40 €, logrando un retorno total del 240.14% al crecer a la misma velocidad compuesta promedio generada por sus flujos de caja reales.

---

## 🖥️ Integración en la UI y uso en el panel de control

LibreFolio muestra estas métricas de rendimiento en el panel de control:

### Gráfico de porcentaje (`%`)
Las series trazadas utilizan el **MWRR Acumulado**, el **TWRR Acumulado** y el **ROI Simple**. Esto permite una comparación visual directa, ya que las tres series comienzan en 0% y representan el progreso total a lo largo del período seleccionado.

### Tarjetas de KPI
* **ROI Simple** (Métrica principal para el rendimiento absoluto).
* **TWRR Acumulado** (Indicador de rendimiento de la estrategia o distribución de activos).
* **MWRR Acumulado** (Indicador principal de la sincronización personal).
* **MWRR Anualizado** (Se muestra como métrica secundaria/comparativa para comprender la tasa compuesta anual).

!!! tip "Analizar la Diferencia de Rendimiento"

    Para interpretar la diferencia entre el MWRR acumulado y el TWRR acumulado, consulte la página del [Efecto Timing](timing-effect.md).

