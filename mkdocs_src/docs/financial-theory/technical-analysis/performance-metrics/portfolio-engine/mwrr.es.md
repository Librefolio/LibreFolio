# 💵 MWRR (Tasa de Rentabilidad Ponderada por el Dinero) / XIRR

## 💡 ¿Qué es?
La MWRR (también conocida como Tasa Interna de Rentabilidad) mide **tu rendimiento personal** como inversor. A diferencia de las métricas basadas únicamente en los activos, tiene en cuenta tanto el rendimiento de los activos subyacentes como el **momento y el tamaño** de tus depósitos y retiros.

Para ofrecer una visibilidad completa, LibreFolio distingue entre dos formas de esta métrica: **MWRR anualizada** y **MWRR acumulada**.

---

## 📈 MWRR anualizada frente a MWRR acumulada

### 📈 MWRR anualizada {: #annualized-mwrr }
La MWRR anualizada es la tasa de rentabilidad anual compuesta que hace que el Valor Presente Neto (NPV) de todos los flujos de efectivo sea igual a cero.

Esta tasa compuesta es matemáticamente equivalente al **CAGR** (Tasa de Crecimiento Anual Compuesta) de tu dinero realmente invertido, y representa la tasa de crecimiento anual suavizada necesaria para que el capital crezca hasta el saldo final, teniendo en cuenta todos los movimientos intermedios.

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{\frac{t_i}{365}}}
$$

??? note "🧮 Cómo se desarrolla la ecuación del NPV"

    #### 1. Forma intuitiva del valor final
    Imagina que intentas proyectar tu valor neto (NAV) final haciendo crecer cada flujo de efectivo a una tasa compuesta \(r\):
    
    \[
    NAV_{final} = CF_0 \times (1 + r)^{\frac{d_0}{365}} + CF_1 \times (1 + r)^{\frac{d_1}{365}} + \dots + CF_n \times (1 + r)^{\frac{d_n}{365}}
    \]
    
    Donde \(d_i\) representa el número de días que cada flujo de efectivo estuvo invertido durante el período.
    
    #### 2. Descuento al Valor Presente Neto (NPV = 0)
    Al dividir ambos lados de la ecuación entre \((1 + r)^{\frac{\text{días totales}}{365}}\), desplazamos todos los flujos de efectivo al inicio del período (\(t_0\)). Esto nos da la ecuación estándar del Valor Presente Neto, donde la suma de los flujos de efectivo descontados es igual a cero:
    
    \[
    0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{\frac{t_i}{365}}}
    \]
    
    Donde \(t_i\) es el número de días desde el inicio del período hasta la fecha del flujo de efectivo \(i\).
    
    #### 3. Ejemplo de despliegue de los flujos de efectivo
    Veamos cómo se completan los flujos de efectivo de una cartera durante un período de 31 días:
    
    * **Día 0:** El valor inicial de la cartera es de 1.000 € (representado como un depósito/inversión).
    * **Día 15:** Depositas 100 €.
    * **Día 31:** El valor neto (NAV) final de la cartera es de 1.150 €.
    
    Primero, construimos la tabla de transacciones desde la perspectiva del inversor (el dinero que entra en la cartera es negativo, el dinero que regresa es positivo):
    
    | Paso (\(i\)) | Día (\(t_i\)) | Evento | Flujo de efectivo de la billetera (\(CF_i\)) |
    |------------|-------------|-------|---------------------------|
    | 0 | 0 | Saldo inicial | **-1.000 €** (Salida) |
    | 1 | 15 | Depósito | **-100 €** (Salida) |
    | 2 | 31 | Liquidación hipotética (NAV) | **+1.150 €** (Entrada) |
    
    Ahora, desplegamos estas transacciones en la suma del NPV:
    
    \[
    0 = -1.000 + \frac{-100}{(1+r)^{\frac{15}{365}}} + \frac{1.150}{(1+r)^{\frac{31}{365}}}
    \]
    
    El solucionador matemático busca iterativamente el valor de \(r\) (MWRR anualizada) que hace que el lado derecho de esta ecuación sea igual a 0.

    #### 4. Anclaje del gráfico acumulado
    Esta convención de signos garantiza que, en el primer día (\(t_0\)), el depósito inicial (\(CF_0 = -1.000\)) y la liquidación hipotética (\(CF_1 = +1.000\)) se anulen mutuamente:
    
    \[
    0 = -1.000 + 1.000 = 0\,\%
    \]
    
    Esto ancla el inicio del gráfico de MWRR acumulada exactamente en **0 %**.

**Descripción de las variables:**

* $r$ = MWRR anualizada (representa el CAGR de tu dinero real).
* $CF_i$ = Flujo de efectivo desde la perspectiva del inversor:
    * **Flujos de efectivo negativos ($CF_i < 0$):** Capital comprometido en la cartera (depósitos, inversiones). Esto representa dinero que sale de la billetera del inversor.
    * **Flujos de efectivo positivos ($CF_i > 0$):** Capital devuelto al inversor (retiros, dividendos). Esto representa dinero que regresa a la billetera.
    * **Valoración final ($CF_n > 0$):** El valor neto (NAV) final de la cartera al final del período, tratado como una entrada positiva (una liquidación hipotética en la que toda la cartera se convierte de nuevo en efectivo que regresa a la billetera).
* $t_i$ = Días transcurridos desde el inicio del período ($t_0 = 0$).

**Conceptos clave:**

* Representa una **velocidad/tasa anual** de crecimiento.
* Es ideal para comparaciones a largo plazo (por ejemplo, comparar tu rendimiento con una tasa de interés bancaria anual o con el CAGR).
* **Advertencia de volatilidad:** En períodos cortos (por ejemplo, unos pocos días o semanas), la rentabilidad anualizada puede ser muy volátil y mostrar porcentajes extremos porque las matemáticas extrapolan la rentabilidad de una ventana pequeña a un año completo de 365 días.

LibreFolio construye los flujos de efectivo de la MWRR a partir de las variaciones de la línea base de capital, no de filas de depósitos exclusivamente en efectivo. Por lo tanto, el capital de AJUSTE/TRANSFERENCIA valorado en especie se trata como capital aportado en lugar de como un rendimiento de inversión repentino. Un ajuste saliente no tiene valor: no devuelve nada al inversor y no constituye un flujo de efectivo ([Capital depositado — Ajustes salientes](deposited-capital.md#outgoing-adjustments)).

### 📊 MWRR acumulada {: #cumulative-mwrr }
La MWRR acumulada representa la rentabilidad total equivalente durante el período seleccionado, obtenida al capitalizar la tasa anualizada durante la duración real de esa ventana.

**Fórmula directa (sin raíces, usa $r$ directamente):**

$$
\text{MWRR}_{\text{acumulada}} = (1 + r)^{\frac{\text{días}}{365}} - 1
$$

**Fórmula de la tasa diaria (con raíz):**

$$
\text{MWRR}_{\text{acumulada}} = (1 + r_d)^{\text{días}} - 1 \quad \text{donde} \quad r_d = \sqrt{1 + r} - 1
$$

Ambas fórmulas son matemáticamente equivalentes. Sin embargo, desde el punto de vista computacional, se prefiere la fórmula directa que usa $r$ (sin raíces) una vez encontrada la tasa anualizada $r$, ya que la exponenciación directa es más simple y eficiente de calcular para el software.

**Descripción de las variables:**

* $\text{días}$ = El número real de días calendario en la ventana de tiempo seleccionada.

**Conceptos clave:**

* Representa la **distancia total recorrida** durante el período.
* Comienza en 0 % y crece a lo largo de la línea temporal, lo que la convierte en la métrica correcta para la visualización de gráficos de series.
* **No es un HPR simple:** Aunque representa una rentabilidad acumulada, se trata de una rentabilidad acumulada ponderada por el dinero. No debe confundirse con la simple Rentabilidad del Período de Tenencia (ROI), que ignora el momento de los flujos de efectivo.

---

## 🔢 Ejemplo numérico a 10 años

Veamos un escenario a 10 años para ver cómo el momento de las aportaciones afecta el rendimiento y cómo se convierten estas métricas:

* **Año 0:** Depositas **10.000 €**.
* **Año 5:** Depositas otros **90.000 €**.
* **Año 10:** Tu valor neto (NAV) final es **200.000 €**.

### 📉 Comparación con el ROI simple
El ROI simple se calcula únicamente sobre las contribuciones netas totales:

$$
ROI = \frac{200.000 - 100.000}{100.000} = +100\,\%
$$

### ⏱️ Efecto timing de la MWRR
Si la mayor parte de tu capital (90.000 €) se depositó en el Año 5, justo antes de una enorme recuperación del mercado que duró varios años, tu dinero trabajó de manera muy eficiente. Como la cantidad mayor estuvo expuesta a los años de alto crecimiento, tu **MWRR anualizada** sería mucho más alta que la TWRR del mercado.

Usando un solucionador matemático de NPV para este escenario específico:
* La **MWRR anualizada ($r$)** es exactamente **13,02 %**.

### 🔁 Conversión a MWRR acumulada
Al capitalizar esta rentabilidad anualizada del 13,02 % durante el período de 10 años:

$$
\text{MWRR}_{\text{acumulada}} = (1 + 0{,}130227)^{10} - 1 \approx +240{,}14\,\%
$$

### 💡 ¿Qué significa +240,14 %?
* **No** significa que tus contribuciones totales de 100.000 € hayan crecido hasta 340.140 €.
* Significa que un **euro teórico**, invertido justo al comienzo del período de 10 años y dejado intacto, habría crecido hasta 3,40 €, logrando una rentabilidad total del 240,14 % al crecer a la misma velocidad compuesta promedio que tus flujos de efectivo reales.

---

## 🖥️ Integración en la interfaz y uso en el panel

LibreFolio muestra estas métricas de rendimiento en el panel:

### 📊 Gráfico de porcentajes (`%`)
Las series representadas usan la **MWRR acumulada**, la **TWRR acumulada** y el **ROI simple**. Esto permite una comparación visual directa y en paralelo, ya que las tres series comienzan en 0 % y representan el progreso total durante el período seleccionado.

### 📐 La línea de MWRR está formada por puntos reales {: #mwrr-line }

A diferencia de la TWRR y el ROI, la MWRR cambia incluso en un día en el que no ocurre nada: el tiempo pasa y, con varios flujos, no existe una forma cerrada que la extienda de un día al siguiente. Por lo tanto, en el informe de la cartera no se almacena en los [pasos diarios](index.md#daily-states-as-steps) del historial, sino en su propia serie, `mwrr_line`, cuyos puntos son **valores reales**: cada uno es la MWRR del período que termina en su día, resuelta en ese día, anualizada y acumulada, con la misma regla que las tarjetas (ver más abajo). La línea tiene un punto al inicio y al final de cada paso del historial, más uno al final de cada mes calendario dentro de los pasos de más de 62 días (como máximo 24 por paso); su primer punto es 0. Nada entre dos puntos se estima ni se almacena: el gráfico los une.

### 🧾 Tarjetas de KPI
* **ROI simple** (Métrica principal para la rentabilidad absoluta).
* **TWRR acumulada** (Indicador de rendimiento de la estrategia/asignación).
* **MWRR acumulada** (Indicador principal del timing personal).
* **MWRR anualizada** (Se muestra como métrica secundaria/comparativa para entender la tasa anual compuesta).

### 🚫 Cuándo no se muestra la MWRR

Las tarjetas de KPI y la línea de MWRR del gráfico siguen la misma regla en cada día del período. Un día tiene MWRR solo cuando:

* el valor de la cartera en ese día es mayor que cero, y
* el período aún mantiene **capital invertido neto** en ese día: el valor con el que abrió, más los depósitos, menos los retiros realizados hasta ese día (los flujos de capital descritos anteriormente), es mayor que cero.

De lo contrario, no hay tasa: la tarjeta muestra `—` y la línea tiene un hueco (un punto sin valor). Después de retiros netos, el hueco comienza el día en que llevan el capital invertido neto a cero o por debajo de cero, y dura hasta que nuevos depósitos lo vuelvan a situar por encima de cero. Las tarjetas siempre muestran el último punto de la línea, por lo que una tarjeta sin MWRR se corresponde con una línea que termina en un hueco. Un día tampoco tiene MWRR cuando ninguna tasa resuelve la ecuación de flujos de efectivo: LibreFolio nunca muestra una tasa que no la resuelva.

!!! tip "Cómo analizar la diferencia de rendimiento"

    Para interpretar la diferencia entre la MWRR acumulada y la TWRR acumulada, consulta la página [Efecto timing](timing-effect.md).
