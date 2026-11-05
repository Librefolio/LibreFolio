# ⏱️ TWRR (tasa de rendimiento ponderada por tiempo)

## 💡 ¿Qué es?
TWRR mide el **rendimiento "puro"** de los activos y la estrategia que elijas (el mercado), ignorando por completo el momento y el tamaño de tus depósitos o retiros.

LibreFolio detecta cortes de subperiodo provocados por flujos externos a partir de las variaciones de la base de capital. Esto incluye el capital de AJUSTE/TRANSFERENCIA en especie valorado, por lo que los activos aportados inicialmente se tratan como capital del inversor que entra en la cartera, no como rendimiento del mercado. Un AJUSTE de salida no tiene valor y no constituye un flujo ([Capital depositado — Ajustes de salida](deposited-capital.md#outgoing-adjustments)): el valor de sus unidades sale del NAV, y el rendimiento del día lo interpreta como una pérdida.

Es la métrica estándar que utilizan los fondos de inversión y los ETF porque los gestores de fondos no tienen control sobre cuándo los clientes depositan o retiran capital; deben evaluarse únicamente por los rendimientos de las inversiones subyacentes.

---

## 🧩 ¿Qué es un subperiodo?
Para aislar el rendimiento de los activos del momento en que se producen los flujos de efectivo, TWRR divide la línea temporal de evaluación en intervalos más pequeños llamados **subperiodos**.

Un **subperiodo** es un intervalo continuo de tiempo entre dos flujos de efectivo externos consecutivos (depósitos o retiros).

Por definición:
* Un nuevo subperiodo comienza inmediatamente después de cualquier flujo de efectivo externo.
* Durante cualquier subperiodo dado, **no se añade ni se retira capital externo** de la cartera.
* En consecuencia, cualquier cambio en el valor de la cartera durante un subperiodo se debe enteramente al rendimiento de los activos (fluctuaciones de precios, dividendos e intereses).

---

## 🧮 Cómo funciona
TWRR calcula la tasa de rendimiento de cada subperiodo de forma individual y luego las enlaza (multiplica) entre sí.

$$
R_{\text{TWRR}} = \prod_{i=1}^{n} (1 + r_i) - 1 = (1 + r_1) \times (1 + r_2) \times \dots \times (1 + r_n) - 1
$$

**Descripción de las variables:**

* $r_i$ = La tasa de rendimiento del subperiodo $i$.
* $n$ = El número total de subperiodos.

---

??? note "Ejemplo de desarrollo del TWRR"

    ### 🧾 1. El escenario

    * **Día 0:** Comienzas tu cartera con un depósito inicial de **1.000 €**.
    * **Día 10:** El mercado sube. Tu cartera ahora vale **1.100 €**. Ese mismo día, depositas otros **500 €** en efectivo.
    * **Día 20:** El mercado cae. Tu cartera termina con un valor final de **1.440 €**.
    
    ### 🧩 2. Desglose de los subperiodos
    La línea temporal se divide en dos subperiodos debido al flujo de efectivo del día 10:
    
    **Subperiodo 1 (del día 0 al día 10):**

    * Valor inicial (\(V_{\text{start}}\)): **1.000 €**
    * Valor final (\(V_{\text{end}}\) antes del flujo de efectivo): **1.100 €**
    * Rendimiento del subperiodo (\(r_1\)):

    \[
    r_1 = \frac{V_{\text{end}}}{V_{\text{start}}} - 1 = \frac{1.100}{1.000} - 1 = +10\,\%
    \]
    
    **Subperiodo 2 (del día 10 al día 20):**

    * Valor inicial (\(V_{\text{start}}\) después del flujo de efectivo): 1.100 € + depósito de 500 € = **1.600 €**
    * Valor final (\(V_{\text{end}}\)): **1.440 €**
    * Rendimiento del subperiodo (\(r_2\)):

    \[
    r_2 = \frac{V_{\text{end}}}{V_{\text{start}}} - 1 = \frac{1.440}{1.600} - 1 = -10\,\%
    \]
    
    ### 🧮 3. Desarrollo del cálculo del TWRR
    Encadenamos los rendimientos de los subperiodos:
    
    \[
    \begin{aligned}
    R_{\text{TWRR}} &= (1 + r_1) \times (1 + r_2) - 1 \\
    &= (1 + 0{,}10) \times (1 - 0{,}10) - 1 \\
    &= 1{,}10 \times 0{,}90 - 1 \\
    &= 0{,}99 - 1 \\
    &= -1\,\%
    \end{aligned}
    \]
    
    Los activos que elegiste subieron un 10 % y luego bajaron un 10 %, lo que dio como resultado un rendimiento neto a nivel de activos del **-1 %**.
    
    ### ⚖️ 4. TWRR frente a ROI simple
    Calculemos el **ROI simple** para el mismo escenario exacto para ver el contraste:

    * Efectivo neto total invertido = 1.000 € + 500 € = **1.500 €**
    * Valor final de la cartera = **1.440 €**
    * ROI simple:

    \[
    ROI = \frac{1.440 - 1.500}{1.500} = -4\,\%
    \]
    
    **¿Por qué son diferentes?**

    * **ROI simple (-4 %)** muestra el rendimiento real y bruto de tu cartera. Se ve lastrado porque depositaste 500 € justo antes de una caída del 10 %, lo que hace que tu pérdida sea mayor en términos absolutos.
    * **TWRR (-1 %)** aísla el rendimiento de la estrategia de los activos. Muestra qué habría ocurrido si hubieras invertido una única suma al principio y no la hubieras tocado nunca más.

---

## 🎯 Cuándo usarlo
* Para juzgar la calidad de los **activos y la estrategia que elegiste**, independientemente de tu tasa de ahorro personal o del momento de tus aportaciones.
* Para comparar el rendimiento de tu cartera directamente con índices de referencia externos (como el S&P 500 o un ETF de índice).

---

## 🚫 Cuándo no se muestra el TWRR {: #when-no-twrr }

La tarjeta KPI y la línea de TWRR del gráfico del panel siguen la misma regla en todos los días del periodo: un día tiene TWRR solo cuando el valor de la cartera en ese día es mayor que cero. Una cartera que hayas vaciado —todo vendido y el efectivo retirado— o una cuyas deudas superen lo que posee no tiene un rendimiento ponderado por tiempo que mostrar.

En un día así, la tarjeta muestra `—` y la línea tiene un hueco. La tarjeta siempre muestra el último punto de la línea, por lo que una tarjeta sin TWRR va acompañada de una línea que termina en un hueco, y el [Efecto timing](timing-effect.md), que necesita el TWRR, también muestra `—`. Cuando nuevos depósitos hacen que el valor vuelva a estar por encima de cero, la línea se reanuda desde el rendimiento que había alcanzado antes del hueco: los días a cero no aportan ganancia ni pérdida, y la cadena de subperiodos sigue capitalizando desde ahí.

El primer punto de la línea es la excepción: siempre es 0, el punto desde el que parte todo rendimiento del periodo.

---

!!! tip "Análisis de la diferencia de rendimiento"

    Para entender cómo tus flujos de efectivo personales hicieron que tus rendimientos reales se desviaran del rendimiento puro de la estrategia (TWRR), consulta la página [Efecto timing](timing-effect.md).
