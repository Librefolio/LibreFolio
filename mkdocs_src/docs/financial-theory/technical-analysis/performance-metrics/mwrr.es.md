# 💵 MWRR (Money-Weighted Rate of Return) / XIRR

*[⬅️ Volver a la Descripción General de Métricas de Rendimiento](index.md)*

## 💡 ¿Qué es?
El MWRR (también conocido como Tasa Interna de Retorno) mide *su rendimiento personal*. Pondera considerablemente los periodos en los que tuvo la mayor cantidad de dinero invertido.

## 🧮 Cómo funciona
Analiza las fechas exactas y los montos de todos sus flujos de caja (depósitos y retiros) y el valor final de la cartera, calculando la tasa de interés constante que un banco habría tenido que ofrecerle para alcanzar exactamente el mismo resultado final.

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{t_i}}
$$

Donde $CF_i$ es cada flujo de caja (depósitos positivos, retiros negativos, valor final de la cartera positivo).

## 🎯 Cuándo utilizarlo
- Para juzgar **su sincronización personal**.
- Para ver la realidad bruta y verdadera de qué tan eficientemente creció su dinero.

## 📈 Cómo se calcula la Serie Acumulada (Gráfico)
Para mostrar el MWRR como un gráfico histórico a lo largo del tiempo, el cálculo se realiza de forma **acumulativa** desde el inicio para cada día de la serie.

Para cada punto de datos trazado en el día $t_N$:

1. El cálculo considera toda la ventana de tiempo desde $t_0$ hasta $t_N$.
2. Establece la ecuación del Valor Actual Neto (NPV) donde el flujo de caja inicial en $t_0$ es el valor inicial de la cartera (representado como un flujo de caja negativo: una "inversión").
3. Todos los flujos de caja intermedios entre $t_0$ y $t_N$ se trazan en la línea de tiempo.
4. El flujo de caja final en $t_N$ representa la liquidación hipotética de la cartera, que es el NAV en $t_N$ (representado como un flujo de caja positivo).

**Caso límite matemático importante:**
Si ocurre un flujo de caja externo exactamente el último día $t_N$ del periodo evaluado, el NAV en $t_N$ ya incorpora ese flujo de caja. En la ecuación del NPV para ese día específico, el flujo de caja neto final debe contabilizar tanto el NAV final como el flujo de caja realizado ese mismo día.

**Ejemplo:**
Imagine que comienza en $t_0$ con una cartera de \$1,000.
- El flujo de caja en $t_0$ es -\$1,000.
- El día $t_{31}$, deposita \$100 adicionales.
- El NAV de su cartera salta inmediatamente a \$1,100 (asumiendo que no hay crecimiento del mercado).

Si el algoritmo utiliza el NAV final de +\$1,100 como el flujo de caja terminal sin compensar el depósito realizado ese mismo día, la matemática asume que una inversión de \$1,000 creció a \$1,100 puramente por el rendimiento del mercado (una ganancia falsa del 10%). Al incluir correctamente el depósito de -\$100 en $t_{31}$ junto con el NAV terminal, el flujo de caja neto final se convierte en +\$1,000 (\$1,100 - \$100), demostrando correctamente que el rendimiento real fue del 0%.

Esta lógica también asegura que el primer día ($t_0$), el NAV inicial y la inversión inicial se cancelen perfectamente entre sí, anclando el inicio del gráfico exactamente en 0%.
