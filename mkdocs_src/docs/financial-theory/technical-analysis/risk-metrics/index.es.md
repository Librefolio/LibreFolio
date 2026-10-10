# 📊 Métricas de riesgo

Las métricas de riesgo proporcionan **medidas cuantitativas** del riesgo de una cartera. Cada métrica captura un aspecto diferente de la incertidumbre, y ninguna métrica por sí sola cuenta la historia completa. Usar varias métricas en conjunto ofrece una visión integral del riesgo de la cartera.

---

## 🧭 Las cuatro preguntas {: #the-four-questions }

Cada página de esta sección existe para responder a una de cuatro preguntas. Una métrica se gana su lugar respondiendo a una de ellas; dos páginas transversales explican cómo se calculan las respuestas y hasta qué punto se puede confiar en ellas. Las dos tablas que aparecen más abajo comparan, en paralelo, las cuatro métricas más conocidas de estas y sugieren cuándo recurrir a cada una.

### 📉 ¿Cuánto puede doler? {: #how-much-can-it-hurt }

| Métrica | Qué responde |
|--------|-----------------|
| **[Caída máxima](max-drawdown.md)** | La mayor caída de pico a valle antes de un nuevo pico — la peor pérdida que un inversor habría vivido realmente. |
| **[Caída actual](current-drawdown.md)** | A qué distancia por debajo de su propio pico histórico se encuentra una cartera justo ahora, en contraposición a la peor caída que haya sufrido. |
| **[Caída en riesgo](drawdown-at-risk.md)** | La caída en riesgo aplica la idea de cuantil a las caídas en lugar de a los rendimientos: es la profundidad de caída que no debería superarse en un nivel de confianza elegido. |
| **[Caída en riesgo condicional](conditional-drawdown-at-risk.md)** | La caída en riesgo condicional promedia las caídas que sí superaron el umbral de la caída en riesgo, respondiendo a cuán profunda llega la caída una vez que se pasa de ese punto. |
| **[Índice de Ulcer](ulcer-index.md)** | El índice de Ulcer combina la profundidad con que cae una cartera y el tiempo que permanece a la baja, de modo que una caída poco pronunciada pero persistente puede puntuar peor que una brusca que se recupera con rapidez. |
| **[Valor en riesgo](value-at-risk.md)** | Una pregunta deliberadamente acotada: en un horizonte dado y con un nivel de confianza elegido, ¿cuál es la pérdida que no debería superarse? |
| **[VaR condicional](conditional-value-at-risk.md)** | Toma el relevo justo donde se detiene el valor en riesgo: la pérdida promedio en los casos en que el umbral del valor en riesgo sí fue superado. |
| **[Peor realización](worst-realization.md)** | El rendimiento de un solo período menos favorable realmente observado en el historial disponible — un hecho observado y no una estimación. |

*Las primeras cinco leen la **trayectoria** que realmente siguió la cartera; las últimas tres leen la **distribución** de sus rendimientos. Si se altera el orden de esos rendimientos, las últimas tres no cambian, mientras que las primeras cinco pueden cambiar por completo.*

### 🧩 ¿Estoy diversificado? {: #am-i-diversified }

| Métrica | Qué responde |
|--------|-----------------|
| **[Correlación](correlation.md)** | Cómo se mueven las posiciones entre sí, que es la razón por la que la diversificación depende de cómo se comportan las posiciones en conjunto y no de cuántas haya. |
| **[Contribución al riesgo](risk-contribution.md)** | Cómo se atribuye el riesgo total de la cartera a cada una de las posiciones — lo que aporta cada posición generalmente no coincide con la proporción de la cartera que representa. |
| **[Concentración](concentration.md)** | Hasta qué punto el peso de una cartera se concentra en unas pocas posiciones, ofreciendo una lectura que un simple recuento de posiciones no puede dar. |

### ⚖️ ¿Me pagan por el riesgo? {: #am-i-paid-for-the-risk }

| Métrica | Qué responde |
|--------|-----------------|
| **[Volatilidad](volatility.md)** | La dispersión de los rendimientos — cuánto fluctúa el valor, y el componente básico de casi todas las demás métricas de riesgo. |
| **[Ratio de Sharpe](sharpe-ratio.md)** | Cuánto rendimiento excedente se obtuvo por unidad de volatilidad total. |
| **[Ratio de Sortino](sortino-ratio.md)** | La misma comparación, con solo la volatilidad a la baja en el denominador. |
| **[Beta y rendimiento activo](beta-active-return.md)** | Con qué fuerza tiende una cartera a seguir a su índice de referencia, y qué parte del resultado no explica el índice de referencia. |
| **[Selección de índice de referencia](benchmark-selection.md)** | Toda cifra relativa a un índice de referencia hereda el índice de referencia con el que se midió, por lo que la elección de la comparación forma parte en sí misma del veredicto. |

### 🎲 ¿Y si…? {: #what-if }

| Métrica | Qué responde |
|--------|-----------------|
| **[Repetición histórica](historical-replay.md)** | Qué le harían a la cartera, tal como está compuesta hoy, los movimientos de un episodio real del pasado. |
| **[Choque hipotético](hypothetical-shock.md)** | Sustituye el episodio histórico por uno elegido, lo que permite poner a prueba un escenario que el historial disponible nunca contuvo. |
| **[Modos de simulación](simulation-modes.md)** | Cada modo se apoya en sus propios supuestos, y esos supuestos determinan tanto lo que sus resultados no pueden decir como lo que sí pueden. |

### 🔧 Método {: #method }

| Página | Qué responde |
|------|-----------------|
| **[Anualización observada](observed-annualization.md)** | Cómo una cifra por período se convierte en anual, con el número de períodos de un año medido a partir de los datos en lugar de supuesto de antemano. |
| **[Calidad de datos](data-quality.md)** | Una cifra de riesgo es tan fiable como las observaciones que la respaldan, por lo que la cantidad y la actualidad de los datos subyacentes forman parte de la lectura del resultado. |

---

## 📋 Resumen comparativo {: #comparative-overview }

| Métrica | Qué mide | Fórmula | Rango | Detalles |
|--------|-----------------|---------|-------|---------|
| **[Ratio de Sharpe](sharpe-ratio.md)** | Rendimiento ajustado al riesgo (vol. total) | $\frac{R_p - R_f}{\sigma_p}$ | $(-\infty, +\infty)$ | [📖](sharpe-ratio.md) |
| **[Ratio de Sortino](sortino-ratio.md)** | Rendimiento ajustado al riesgo (solo a la baja) | $\frac{R_p - R_f}{\sigma_d}$ | $(-\infty, +\infty)$ | [📖](sortino-ratio.md) |
| **[Caída máxima](max-drawdown.md)** | Peor caída de pico a valle | $\frac{Trough - Peak}{Peak}$ | $[-100\%, 0\%]$ | [📖](max-drawdown.md) |
| **[Volatilidad](volatility.md)** | Dispersión de los rendimientos | $\sigma = \sqrt{\text{Var}(R)}$ | $[0, +\infty)$ | [📖](volatility.md) |

---

## 🔑 Cuándo usar cada métrica {: #when-to-use-each-metric }

| Escenario | Mejor métrica | Por qué |
|----------|-------------|-----|
| Comparar dos fondos | **Ratio de Sharpe** | Normaliza el rendimiento por el riesgo total |
| Distribuciones de rendimiento asimétricas | **Ratio de Sortino** | Solo penaliza la volatilidad a la baja |
| Planificación del peor escenario | **Caída máxima** | Muestra el punto máximo de dolor |
| Evaluación general del riesgo | **Volatilidad** | Base de todas las demás métricas |
| Optimización de cartera | **Las cuatro** | Cada una captura una dimensión diferente |

---

## ⚠️ Errores comunes {: #common-pitfalls }

!!! warning "Limitaciones"

    - **Las métricas históricas ≠ el riesgo futuro**: la volatilidad pasada puede no predecir la volatilidad futura
    - **Supuesto de distribución normal**: Sharpe y Sortino suponen que los rendimientos son aproximadamente normales; los rendimientos financieros tienen colas gruesas
    - **Sensibilidad a la ventana de observación**: las métricas cambian de forma significativa según la ventana temporal
    - **Dependencia del índice de referencia**: Sharpe y Sortino dependen de la tasa libre de riesgo, que cambia con el tiempo

---

## 🔗 Relacionado {: #related }

- 🔀 **[Diversificación](../../portfolio-theory/diversification.md)** — Cómo funciona matemáticamente la reducción del riesgo
- ⚖️ **[Asignación de activos](../../portfolio-theory/asset-allocation.md)** — Usar las métricas de riesgo para guiar la asignación
- 📈 **[Rendimientos y tasas de crecimiento](../../fundamentals/returns.md)** — El lado del "rendimiento" en la relación riesgo-rendimiento
