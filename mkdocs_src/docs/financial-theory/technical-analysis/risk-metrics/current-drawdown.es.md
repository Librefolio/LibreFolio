# 📍 Caída actual

La caída actual mide a qué distancia por debajo de su propio máximo histórico se encuentra una cartera **en este momento**, en contraposición a la peor caída que haya sufrido. [Caída máxima](max-drawdown.md) informa un hecho sobre el pasado; esta cifra informa una posición en el presente, y es la que cambia con cada nueva observación.

---

## 🔢 Fórmula {: #formula }

Ambas cifras de caída se leen de la misma serie bajo el pico. Se construye un índice de riqueza a partir de los rendimientos analizados, se arrastra un máximo acumulado y la caída en cada punto es la distancia entre ambos:

$$
DD_t = \frac{W_t}{\displaystyle\max_{\tau \le t} W_\tau} - 1
$$

La caída actual es el valor de esa serie en la **última** observación, nunca por encima de cero:

$$
DD_{current} = \min\left(0,\; DD_{last}\right)
$$

En un nuevo máximo histórico, el último valor de riqueza *es* el máximo acumulado, por lo que el cociente es $1$ y la caída es exactamente $0$.

!!! info "Estar bajo el pico se decide con una tolerancia"

    Una cartera se considera bajo el pico solo cuando la caída actual es negativa **más allá de una tolerancia numérica**, no en cada fracción de céntimo por debajo del máximo. La tolerancia existe para absorber el ruido de punto flotante, de modo que un valor indistinguible del máximo se trata como si estuviera en el máximo. Es una protección contra artefactos aritméticos, no un umbral orientado al usuario por debajo del cual una caída deja de importar.

---

## 📅 Qué se publica {: #what-is-published }

Cuatro cantidades describen la posición presente. Su comportamiento cuando la cartera **no** está bajo el pico es parte del contrato, no un accidente.

| Cantidad | Significado | En un máximo histórico |
|---|---|---|
| Caída actual | Distancia por debajo del máximo acumulado, como ratio decimal, nunca positiva | Exactamente $0$ |
| Fecha del máximo actual | La fecha del máximo **acumulado** desde el que se mide la caída | La fecha de la última observación |
| Duración de la caída actual | Días naturales transcurridos **desde ese máximo** | Exactamente $0$ |
| Restante para el máximo | La ganancia aún necesaria, sobre el valor actual, para volver al máximo | Exactamente $0$ |

Dos de estas merecen leerse con atención.

**La duración se cuenta desde el máximo, no desde el punto mínimo.** Esta es la misma convención que la caída máxima usa para su duración: el reloj empieza cuando la cartera abandona su máximo histórico, no cuando deja de caer. La caída no es un preludio de la pérdida — es la pérdida ocurriendo —, por lo que la cuenta cubre todo el tramo pasado por debajo del máximo. Véase [Tiempo de recuperación](max-drawdown.md#recovery-time) para el mismo razonamiento aplicado al peor episodio.

**La fecha del máximo actual no es el máximo del peor episodio.** Es el máximo histórico más reciente, que el máximo acumulado avanza cada vez que la cartera establece uno nuevo. Una cartera en un máximo de todos los tiempos, por tanto, informa la fecha de hoy y una caída de duración cero; el máximo que precedió a la caída histórica más profunda pertenece a la [Caída máxima](max-drawdown.md) y se publica por separado.

---

## 🧗 Qué se necesita para recuperarse {: #what-it-takes-to-get-back }

La ganancia requerida para volver al máximo no es la imagen especular de la caída, porque la ganancia se aplica a una base menor. Expresada a partir de la caída actual $DD$:

$$
\text{Ganancia requerida} = \frac{1}{1 + DD} - 1 = \frac{-DD}{1 + DD}
$$

Las dos formas son la misma expresión — la segunda es la primera con la fracción combinada — y [Caída máxima](max-drawdown.md) explica la asimetría que esto crea, con los valores desarrollados.

!!! warning "La misma fórmula, aplicada a una pregunta diferente"

    Esa asimetría es una lección general, y se enseña en la página de caída máxima. La cantidad calculada aquí la aplica a la caída **actual** en su lugar, y la diferencia no es cosmética:

    - aplicada al **máximo**, es una afirmación histórica — *cuánto habría hecho falta para recuperarse, en el peor punto jamás alcanzado*;
    - aplicada a la caída **actual**, es una afirmación presente — *cuánto hace falta para recuperarse desde donde se encuentra la cartera hoy*.

    Solo sobre la segunda se puede actuar. Una cartera que cayó abruptamente hace años y desde entonces se ha recuperado carga un máximo grande y una cifra actual cercana a cero al mismo tiempo: no son dos números en desacuerdo, son respuestas a dos preguntas diferentes, y ambas son verdaderas.

---

## 💡 Interpretación {: #interpretation }

La caída actual responde *¿dónde estoy, en relación con mi propio mejor resultado?* — una pregunta que ninguna cifra de rentabilidad responde, porque una rentabilidad mide un trayecto entre dos fechas elegidas, mientras que esta mide una distancia desde un máximo que la propia cartera estableció.

Leídas en conjunto, las cuatro cantidades describen una posición en lugar de una puntuación: **a qué distancia** por debajo del máximo, **desde cuándo**, y **cuánto** falta todavía. La duración suele ser la más reveladora de las dos: una caída modesta que se ha prolongado durante mucho tiempo es una experiencia diferente de una más profunda que comenzó la semana pasada, y la profundidad por sí sola no puede distinguirlas. Esa combinación de profundidad y persistencia es lo que el [índice de Ulcer](ulcer-index.md) se propone resumir en un solo número.

Debido a que se mide con respecto al máximo acumulado, la cifra tiene una asimetría propia incorporada: mejora a medida que la cartera sube y se restablece a cero en el momento en que se establece un nuevo máximo, por poco que se supere ese máximo.

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "Es una posición, no una previsión"

    La caída actual dice a qué distancia por debajo del máximo está la cartera, y nada sobre lo que sucederá después. No indica si la caída está terminando, continuando o a punto de profundizarse, y la cifra restante para el máximo es aritmética — la ganancia requerida para cerrar la brecha —, no una expectativa de que la ganancia vaya a llegar.

!!! warning "Un nuevo máximo borra la memoria"

    El máximo acumulado solo se mueve hacia arriba, por lo que superar el máximo anterior por cualquier margen restablece la caída actual a cero y reinicia la duración desde esa fecha. La caída que lo precedió no desaparece del análisis, pero deja de ser descrita por *esta* cifra: pertenece a la caída máxima y al historial de episodios.

!!! warning "Hereda la serie sobre la que se calculó"

    La serie bajo el pico se construye a partir de los mismos rendimientos que el resto del análisis, sobre la misma ventana de observación. Una ventana más corta solo puede contener los máximos que vio: una cartera analizada durante una ventana reciente puede parecer cerca de su máximo simplemente porque el máximo más alto se encuentra antes de la fecha de inicio. Cada resultado publica la ventana que utilizó, su número de observaciones y la base sobre la que se calcularon los rendimientos. Véase [Calidad de datos](data-quality.md).

---

## 🔗 Relacionado {: #related }

- 📉 **[Caída máxima](max-drawdown.md)** — la peor caída registrada, su duración y su estado de recuperación
- 🩹 **[Índice de Ulcer](ulcer-index.md)** — profundidad y persistencia combinadas en una sola cifra
- 📊 **[Volatilidad](volatility.md)** — cuánto fluctúa la cartera, independientemente de cualquier máximo
- 🧪 **[Calidad de datos](data-quality.md)** — la ventana y las observaciones a partir de las cuales se leyó la caída
