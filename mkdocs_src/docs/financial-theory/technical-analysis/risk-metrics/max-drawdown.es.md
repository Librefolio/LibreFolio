# 📉 Caída máxima

La caída máxima (MDD) mide la **mayor caída desde un máximo hasta un mínimo** en el valor de una cartera antes de que se establezca un nuevo máximo. Responde a la pregunta: *"¿Cuál fue la peor pérdida que podría haber experimentado un inversor?"*

---

## 🔢 Fórmula {: #formula }

$$
MDD = \frac{Trough - Peak}{Peak} = \min_{t} \left( \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau} \right)
$$

donde $V_t$ es el valor de la cartera en el momento $t$.

La caída en cualquier punto $t$ es:

$$
DD_t = \frac{V_t - V_{peak}}{V_{peak}}
$$

La caída máxima es el valor mínimo (más negativo) de $DD_t$ a lo largo de todo el período de observación.

---

## 💡 Interpretación {: #interpretation }

| Caída máxima | Contexto típico |
|---|---|
| $-5\%$ a $-10\%$ | Corrección normal, cartera bien diversificada |
| $-10\%$ a $-20\%$ | Corrección significativa |
| $-20\%$ a $-30\%$ | Territorio de mercado bajista |
| $-30\%$ a $-50\%$ | Mercado bajista severo (2008, COVID-2020) |
| $> -50\%$ | Catastrófico (posiciones concentradas, cripto) |

!!! example "Ejemplo numérico"

    Secuencia del valor de la cartera: 100 → 120 → 90 → 110 → 130

    - Máximo: 120
    - Mínimo: 90
    - MDD: $(90 - 120) / 120 = -25\%$
    - Recuperación: se alcanzó 120 de nuevo y luego un nuevo máximo en 130

---

## ⏱️ Tiempo de recuperación {: #recovery-time }

Una métrica igualmente importante es el **tiempo de recuperación**: cuánto tiempo permaneció la cartera por debajo de un máximo que ya había alcanzado. El cronómetro comienza en el **máximo**, no en el mínimo: empieza el día en que la cartera abandona su marca máxima y solo se detiene cuando esa marca se alcanza de nuevo.

$$
T_{recovery} = t_{recovery} - t_{peak}
$$

La caída forma parte, por tanto, del cómputo, y la duración se expresa en **días naturales** entre esas dos fechas. El peor episodio siempre se presenta junto con su estado, y el estado determina qué más se puede decir sobre él:

| Estado de recuperación | Qué significa | Qué lo acompaña |
|---|---|---|
| *recuperado* | Se alcanzó de nuevo el máximo anterior | Fechas de máximo, mínimo y recuperación; la duración es definitiva |
| *abierto* | El máximo no se ha vuelto a alcanzar dentro del período observado | Fechas de máximo y mínimo, y **ninguna fecha de recuperación**; la duración sigue en curso |
| *sin caída* | La cartera nunca cerró por debajo de un máximo previo | Ninguna fecha ni fracción recuperada; la profundidad y la duración son cero |

No se trata de convenciones de presentación: las combinaciones se imponen sobre el propio resultado, de modo que un episodio abierto no puede llevar una fecha de recuperación, y un episodio que nunca ocurrió no puede llevar una recuperación parcial.

!!! info "Cuando la caída sigue abierta"

    Si el máximo no se ha vuelto a alcanzar al final del período observado, no hay fecha de recuperación, y la duración se mide hasta la última observación:

    $$
    T_{open} = t_{last} - t_{peak}
    $$

    Esta cifra **crece con cada día que pasa** mientras la cartera permanezca por debajo del máximo: el número no se está desviando, simplemente el episodio aún no ha terminado.

    Un episodio abierto también lleva una **fracción recuperada** entre $0$ y $1$: cuánto de la caída, medida desde el mínimo, se ha remontado ya. Es una lectura de progreso más que un veredicto —la parte del descenso que se ha deshecho hasta ahora— y es la cifra que responde a la pregunta que realmente se hace un inversor que sigue bajo el pico.

!!! warning "Por qué el cómputo empieza en el máximo"

    Medir solo la remontada —desde el mínimo hasta un nuevo máximo— arroja siempre un número **menor**, porque descarta la caída en sí. Pero el inversor ya estaba por debajo de su marca máxima mientras la cartera caía: ese tramo no es un preludio de la pérdida, es la pérdida misma ocurriendo. Empezar el cómputo en el máximo registra todo el período pasado bajo el pico, que es el período que el inversor realmente tuvo que vivir.

Contexto histórico, por clase de activo:

| Clase de activo | Tiempo de recuperación típico (tras una gran caída) |
|-------------|---------------------------------------------|
| Acciones de EE. UU. (S&P 500) | 1-5 años |
| Bonos | De meses a 1-2 años |
| Cripto | Muy variable (de meses a años) |

Estas cifras son historia general del mercado, no una medición de LibreFolio, y no se indica la base sobre la que se contaron: los tiempos de recuperación publicados a veces se miden desde el mínimo y a veces desde el máximo. Por tanto, **no son directamente comparables** con la duración indicada más arriba, que siempre cuenta desde el máximo y, por ello, abarca un tramo más largo que una cifra basada en el mínimo para el mismo episodio.

!!! warning "Asimetría de las pérdidas"

    Una pérdida del 50% requiere una **ganancia del 100%** para recuperarse:

    $$
    \text{Ganancia requerida} = \frac{1}{1 + MDD} - 1
    $$

    <div style="display: flex; justify-content: center;">

    | Pérdida | Ganancia requerida |
    |:----:|:-------------:|
    | -10% | +11.1% |
    | -25% | +33.3% |
    | -50% | +100% |
    | -75% | +300% |

    </div>

La tabla anterior es la aritmética general de la asimetría, tabulada frente a la profundidad de la caída **máxima**. La cifra que calcula el sistema aplica esa misma fórmula a la caída **actual**: responde a cuánta ganancia se necesita para volver al máximo *desde donde se encuentra hoy la cartera*, que es la única versión de la pregunta sobre la que se puede actuar. Ambas lecturas coinciden solo cuando la cartera resulta estar situada en su punto más profundo de toda su historia; véase [Caída actual](current-drawdown.md).

---

## 📊 Gráfico de caída {: #drawdown-chart }

Un gráfico de caída representa $DD_t$ a lo largo del tiempo. Siempre es cero o negativo, y toca cero en cada nuevo máximo. El valle más profundo es la caída máxima. Esta visualización facilita:

- Identificar el **momento** de los períodos de peor caso
- Ver con qué frecuencia se producen las caídas
- Comparar patrones de recuperación entre distintas estrategias

---

## 🔗 Relacionado {: #related }

- 📊 **[Volatilidad](volatility.md)** — La desviación estándar no capta la severidad de la caída
- 📐 **[ratio de Sharpe](sharpe-ratio.md)** — Rentabilidad ajustada al riesgo (usa la volatilidad, no la caída)
- 🔀 **[Diversificación](../../portfolio-theory/diversification.md)** — La principal herramienta para reducir la caída máxima
