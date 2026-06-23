# ⏱️ Efecto Timing

*[⬅️ Volver a la Descripción General de las Métricas de Rendimiento](index.md)*

## 💡 ¿Qué es?

El **Efecto Timing** mide cuánto influyó el momento y el importe de sus depósitos y retiradas (flujos de efectivo) en el rendimiento personal del inversor en comparación con el rendimiento de la estrategia subyacente, neutralizando el efecto de los flujos de efectivo externos.

Se calcula como la diferencia entre la Tasa de Rendimiento Ponderada por el Dinero (MWRR) acumulada y la Tasa de Rendimiento Ponderada por el Tiempo (TWRR) acumulada:

$$
\text{Efecto Timing} = \text{MWRR}_{\text{acumulado}} - \text{TWRR}_{\text{acumulado}}
$$

Se expresa en **puntos porcentuales (pp)**.

---

## 🧮 Cómo Interpretar el Efecto Timing

Al comparar el [MWRR Acumulado](mwrr.md#cumulative-mwrr) (que incluye el momento de los flujos de efectivo) con el [TWRR Acumulado](twrr.md) (que neutraliza dicho efecto), el Efecto Timing destaca la diferencia entre el rendimiento personal del inversor y el rendimiento de la estrategia, atribuible al momento y dimensión de los flujos de efectivo:

- **Efecto Timing Positivo ($> 0$ pp):** Sus flujos de efectivo ocurrieron en momentos favorables (por ejemplo, comprando activos con descuento durante una caída del mercado). Su rendimiento personal (MWRR) es superior al rendimiento de la estrategia pura (TWRR).
- **Efecto Timing Negativo ($< 0$ pp):** Sus flujos de efectivo ocurrieron en momentos desfavorables (por ejemplo, depositando grandes sumas en el máximo del mercado justo antes de una corrección). Su rendimiento personal (MWRR) es inferior al rendimiento de la estrategia pura (TWRR).
- **Efecto Timing Cercano a Cero ($\approx 0$ pp):** Sus flujos de efectivo tuvieron poco o ningún impacto en el rendimiento (por ejemplo, si realizó depósitos muy pequeños o si el mercado permaneció plano durante sus transacciones).

---

## 🔢 Ejemplos Numéricos

### Ejemplo 1: Efecto Timing Positivo (Flujos Favorables)
* **TWRR Acumulado (Rendimiento de la Estrategia):** $+20\%$
* **MWRR Acumulado (Rendimiento del Inversor):** $+28\%$

$$
\text{Efecto Timing} = 28\% - 20\% = +8\text{ pp}
$$

* **Interpretación:** La estrategia de activos subyacentes generó un rendimiento del $+20\%$. Sin embargo, debido a que aportó una cantidad significativa de capital a la cartera antes de que el mercado subiera, su rendimiento personal ponderado por dinero aumentó al $+28\%$. El momento y el tamaño de sus aportaciones aportaron **$+8$ puntos porcentuales** de rendimiento adicional.

### Ejemplo 2: Efecto Timing Negativo (Flujos Desfavorables)
* **TWRR Acumulado (Rendimiento de la Estrategia):** $+20\%$
* **MWRR Acumulado (Rendimiento del Inversor):** $+12\%$

$$
\text{Efecto Timing} = 12\% - 20\% = -8\text{ pp}
$$

* **Interpretación:** La estrategia generó un rendimiento del $+20\%$. Sin embargo, aportó un capital significativo cerca del máximo del mercado justo antes de una caída. Esto concentró una mayor parte de su dinero durante un período de mal rendimiento, arrastrando su rendimiento personal ponderado por dinero al $+12\%$. Su sincronización redujo su rendimiento en **$-8$ puntos porcentuales**.

---

## ⚖️ Qué Captura y Qué No Captura

### Qué Captura
- **Impacto del momento de depósitos/retiros:** Si aportó capital durante los mínimos del mercado (comprando barato) o máximos (comprando caro).
- **Impacto del tamaño de los flujos:** Los flujos de efectivo más grandes tienen una mayor ponderación y un mayor impacto en el MWRR, lo que refleja el Efecto Timing.
- **La "Brecha del Inversor" (Investor Gap):** la distancia entre el rendimiento de la estrategia y el rendimiento realmente obtenido por el inversor, debido al momento y dimensión de los flujos de efectivo.

### Qué No Captura
- **Beneficio monetario absoluto:** Puede existir un Efecto Timing positivo de $+5$ pp incluso si la cartera está en pérdidas netas (por ejemplo, si el TWRR es del $-20\%$ y el MWRR del $-15\%$). Use el [P&L del Periodo](period-pnl.md) para evaluar las ganancias monetarias.
- **Riesgo y volatilidad:** No indica el perfil de riesgo ni la volatilidad de los activos.
- **Impacto desagregado de impuestos/costes:** el Efecto Timing no desglosa impuestos y costes; los posibles costes e impuestos pueden mostrarse por separado en el P&L del periodo.
- **Calidad intrínseca de los activos:** Se puede dar un Efecto Timing elevado en un activo deficiente si se compra justo antes de un rebote temporal. Compruebe siempre el [TWRR](twrr.md) para juzgar la calidad de los activos.

---

## 🖥️ Uso en el Panel de Control
LibreFolio muestra el Efecto Timing en la tarjeta de **Rendimientos** del panel de control. Esta tarjeta resume los indicadores clave de su rendimiento de inversión:

- **Efecto Timing:** Diferencia entre el MWRR acumulado y el TWRR acumulado, que muestra cómo afectaron los flujos de efectivo a sus rendimientos.
- **Simple ROI:** rendimiento porcentual intuitivo del periodo. Es útil para leer rápidamente el resultado, pero no considera el momento de los flujos con la misma precisión que el MWRR.
- **TWRR Acumulado:** Rendimiento de la estrategia subyacente, neutralizando los impactos de los flujos de efectivo.
- **MWRR Acumulado:** Rendimiento de su capital real, considerando los flujos de efectivo.
- **MWRR Anualizado:** La tasa anual compuesta de crecimiento de su dinero.

!!! note "Tooltip Informativo"

    Diferencia entre el MWRR acumulado y el TWRR acumulado. Muestra cuánto afectaron el momento y el importe de sus flujos de efectivo a su rendimiento general.


---

## 🔗 Relación con Otras Métricas

- **[Simple ROI](roi.md):** Mide la ganancia o pérdida porcentual absoluta en relación con el capital invertido.
- **[TWRR](twrr.md):** Mide el rendimiento de la estrategia o activos subyacentes, ignorando el momento de los flujos de efectivo del inversor.
- **[MWRR](mwrr.md):** Mide el rendimiento del capital del inversor, teniendo en cuenta tanto el rendimiento de los activos como el momento de los flujos de efectivo.
- **[P&L del Periodo](period-pnl.md):** Mide el beneficio o pérdida monetaria absoluta generada por la cartera dentro del periodo de tiempo seleccionado.
