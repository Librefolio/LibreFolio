# ⏱️ TWRR (Tasa de Retorno Ponderada por el Tiempo)

*[⬅️ Volver a la Descripción General de Métricas de Rendimiento](index.md)*

## 💡 ¿Qué es?
El TWRR (por sus siglas en inglés, *Time-Weighted Rate of Return*) mide el **rendimiento "puro"** de sus activos y su estrategia de inversión (El Mercado), ignorando por completo la temporalidad (timing) y el volumen de sus depósitos o retiros.

Es la métrica estándar utilizada por los fondos de inversión y los ETF debido a que los gestores no tienen control sobre cuándo deciden los clientes depositar o retirar capital; por lo tanto, deben ser evaluados únicamente en función de las ganancias generadas por las inversiones subyacentes.

---

## 🧩 ¿Qué es un subperíodo?
Para aislar el rendimiento de los activos de la influencia de la temporalidad de los flujos de caja, el TWRR divide la línea de tiempo de evaluación en intervalos más pequeños llamados **subperíodos**.

Un **subperíodo** es un intervalo de tiempo continuo entre dos flujos de caja externos consecutivos (depósitos o retiros).

Per definición:
* Un nuevo subperíodo comienza inmediatamente después de cualquier flujo de caja externo.
* Durante un subperíodo determinado, **no se añade ni se retira capital externo** de la cartera.
* En consecuencia, cualquier variación en el valor de la cartera durante un subperíodo se debe exclusivamente al rendimiento de los activos (fluctuaciones de precios, dividendos, intereses).

---

## 🧮 Cómo funciona
El TWRR calcula la tasa de retorno de cada subperíodo individualmente y luego los vincula (multiplica) entre sí.

$$
R_{\text{TWRR}} = \prod_{i=1}^{n} (1 + r_i) - 1 = (1 + r_1) \times (1 + r_2) \times \dots \times (1 + r_n) - 1
$$

**Descripción de las Variables:**

* $r_i$ = La tasa de retorno del subperíodo $i$.
* $n$ = El número total de subperíodos.

---

??? note "Ejemplo de despliegue de TWRR"

    ### 1. El escenario

    * **Día 0:** Inicia su cartera con un depósito inicial de **1.000 €**.
    * **Día 10:** El mercado sube. Su cartera vale ahora **1.100 €**. Ese mismo día, realiza otro depósito de **500 €**.
    * **Día 20:** El mercado baja. Su cartera termina con un valor final de **1.440 €**.
    
    ### 2. Desglose de los subperíodos
    La línea de tiempo se divide en dos subperíodos debido al flujo de caja del Día 10:
    
    **Subperíodo 1 (del Día 0 al Día 10):**

    * Valor Inicial (\(V_{\text{start}}\)): **1.000 €**
    * Valor Final (\(V_{\text{end}}\) antes del flujo de caja): **1.100 €**
    * Retorno del subperíodo (\(r_1\)):

    \[
    r_1 = \frac{V_{\text{end}}}{V_{\text{start}}} - 1 = \frac{1.100}{1.000} - 1 = +10\%
    \]
    
    **Subperíodo 2 (del Día 10 al Día 20):**

    * Valor Inicial (\(V_{\text{start}}\) después del flujo de caja): 1.100 € + 500 € (depósito) = **1.600 €**
    * Valor Final (\(V_{\text{end}}\)): **1.440 €**
    * Retorno del subperíodo (\(r_2\)):

    \[
    r_2 = \frac{V_{\text{end}}}{V_{\text{start}}} - 1 = \frac{1.440}{1.600} - 1 = -10\%
    \]
    
    ### 3. Despliegue del cálculo de TWRR
    Multiplicamos los retornos de los subperíodos entre sí:
    
    \[
    \begin{aligned}
    R_{\text{TWRR}} &= (1 + r_1) \times (1 + r_2) - 1 \\
    &= (1 + 0.10) \times (1 - 0.10) - 1 \\
    &= 1.10 \times 0.90 - 1 \\
    &= 0.99 - 1 \\
    &= -1\%
    \end{aligned}
    \]
    
    Los activos que eligió subieron un 10% y luego bajaron un 10%, lo que da como resultado un retorno neto de la estrategia de **-1%**.
    
    ### 4. TWRR vs. ROI Simple
    Calculemos el **ROI Simple** para el mismo escenario para ver el contraste:

    * Capital neto total invertido = 1.000 € + 500 € = **1.500 €**
    * Valor final de la cartera = **1.440 €**
    * ROI Simple:

    \[
    ROI = \frac{1.440 - 1.500}{1.500} = -4\%
    \]
    
    **¿Por qué son diferentes?**

    * **El ROI Simple (-4%)** muestra el rendimiento real de su cartera. Se ve perjudicado porque depositó 500 € justo antes de una caída del -10%, lo que hizo que su pérdida fuera mayor en términos absolutos.
    * **El TWRR (-1%)** aísla el rendimiento de la estrategia de los activos. Muestra lo que habría sucedido si simplemente hubiera invertido una suma única al principio y no la hubiera vuelto a tocar.

---

## 🎯 Cuándo utilizarlo
* Para evaluar la calidad de los **activos y la estrategia que ha elegido**, independientemente de su ritmo de ahorro o de la temporalidad de sus depósitos.
* Para comparar directamente el rendimiento de su cartera con índices de referencia externos (como el S&P 500 o un ETF de índice).
