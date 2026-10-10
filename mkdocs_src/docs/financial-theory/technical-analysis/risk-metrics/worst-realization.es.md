# 🔻 Peor realización

La peor realización es simplemente el rendimiento de un solo período menos favorable realmente observado en el historial disponible: un hecho observado, no una estimación.

Todas las demás cifras de esta sección se calculan *a partir de* las observaciones. Esta **es** una de ellas.

---

## 🔢 Qué es {: #what-it-is }

Dados los rendimientos de la ventana analizada, la peor realización es su mínimo:

$$
WR = \min_t \; r_t
$$

No hay un nivel de confianza que elegir, ni una distribución que asumir, ni un promedio. La cifra es un rendimiento que ocurrió, y viene con **la fecha en que ocurrió**, que es lo que la separa de todos los parámetros de las páginas circundantes. Una fecha se puede consultar. Ancla el número a un evento que la cartera realmente atravesó, en lugar de a una construcción estadística.

---

## 🆚 Frente al valor en riesgo {: #against-value-at-risk }

El compañero natural es el [valor en riesgo](value-at-risk.md), y el par funciona por **contraste** en lugar de por repetición:

| | Dice | Naturaleza |
|---|---|---|
| Valor en riesgo | *Uno de cada veinte períodos va peor que esto* | Un umbral, estimado |
| Peor realización | *Y el peor fue este, en esta fecha* | Un único punto, observado |

El valor en riesgo describe una **tasa** y no dice nada sobre la magnitud más allá del umbral. La peor realización describe una **magnitud** y no dice nada sobre la tasa: ocurrió una vez, y la cifra no dice nada sobre qué probabilidad hay de que se repita. El [VaR condicional](conditional-value-at-risk.md) se sitúa entre ellos, promediando toda la cola en lugar de leer su frontera o su extremo.

Juntos delimitan la cola: dónde comienza, cuán profunda es en promedio y el paso único más profundo registrado.

---

## 🧭 Distribución o trayectoria {: #distribution-or-path }

Las métricas etiquetadas como *riesgo* se dividen en dos familias que responden a preguntas distintas, y nada en una fila de ocho números indica cuál es cuál.

!!! info "Reordena los rendimientos y observa qué se mueve"

    **Reordena los rendimientos de una cartera y el valor en riesgo no cambia ni una coma — mientras que la caída máxima puede duplicarse.**

    El valor en riesgo, el VaR condicional y la peor realización leen la **distribución**: qué rendimientos ocurrieron, en cualquier orden. La [caída máxima](max-drawdown.md), la [caída actual](current-drawdown.md) y las duraciones asociadas a ellas leen la **trayectoria**: el orden en que llegaron.

La peor realización pertenece firmemente a la familia de la distribución, y la distinción no es académica. Responde a *¿qué tan malo puede ser un solo período?*, mientras que una cartera no queda destruida por un mal día, sino por una **secuencia** de ellos. Tres pérdidas consecutivas del 5% hacen más daño que una pérdida aislada del 12%, y solo la familia que lee la trayectoria puede distinguirlas.

Leer una cifra distribucional como si describiera la peor experiencia disponible es el error que esta sección está organizada para prevenir.

---

## 💡 Interpretación {: #interpretation }

Úsala como una comprobación de la realidad sobre las cifras estimadas. Un valor en riesgo mucho menos severo que la peor realización no es una contradicción: se supone que el cuantil se supera a veces, y así es como se veía superarlo en su forma más extrema.

La fecha importa tanto como el valor. Una peor realización de un evento de mercado bien conocido se lee de forma distinta a una en un día sin particularidades, lo que a menudo apunta a algo específico de la cartera: una única posición, una acción corporativa o un artefacto de precios que vale la pena revisar en [calidad de datos](data-quality.md).

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "Es un valor extremo, por lo que la ventana solo puede empeorarlo"

    Alargar el período analizado nunca puede mejorar esta cifra y solo puede empeorarla: una ventana más larga contiene todas las observaciones que contenía la más corta, y además más oportunidades de encontrar algo peor. Por lo tanto, comparar peores realizaciones entre carteras carece de sentido a menos que se hayan medido en la misma ventana — un historial más largo normalmente parecerá peor solo por esa razón.

!!! warning "Una observación no conlleva frecuencia"

    La cifra se basa en un único período. No dice nada sobre con qué frecuencia ocurre un período así, si algo cercano a él ocurrió más de una vez, ni cómo se comportó el resto de la cola. Para la forma de la cola en lugar de su extremo, usa el [VaR condicional](conditional-value-at-risk.md).

!!! warning "Depende de la duración de un período"

    El peor día, la peor semana y el peor mes son cantidades distintas, y no se convierten entre sí. La cifra está ligada a la frecuencia de observación de la serie de la que se leyó; consulta [Anualización observada](observed-annualization.md) para ver cómo se establece esa frecuencia.

---

## 🔗 Relacionado {: #related }

- 📉 **[Valor en riesgo](value-at-risk.md)** — dónde comienza la cola, como una tasa en lugar de un hecho
- 🌊 **[VaR condicional](conditional-value-at-risk.md)** — la profundidad media de la cola al final de la cual se sitúa esta cifra
- 📉 **[Caída máxima](max-drawdown.md)** — la peor caída acumulada, que lee la trayectoria en lugar de la distribución
- 📊 **[Volatilidad](volatility.md)** — dispersión típica, con la que se puede juzgar un extremo
- 🧪 **[Calidad de datos](data-quality.md)** — la ventana y la serie sobre las que se tomó el mínimo
