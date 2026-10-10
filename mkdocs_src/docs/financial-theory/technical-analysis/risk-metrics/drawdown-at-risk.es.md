# 📉 Caída en Riesgo

La caída en riesgo aplica la idea de cuantil a las caídas en lugar de a los rendimientos: es la profundidad de caída que no debería superarse a un nivel de confianza elegido.

Todo lo que es el [valor en riesgo](value-at-risk.md), esto también lo es — con una sustitución. Donde esa cifra ordena las **pérdidas** que sufrió la cartera, esta ordena las **distancias por debajo de un pico** que atravesó. La estrechez es idéntica, y también la trampa: marca dónde comienza la cola de caídas y calla sobre todo lo que está más allá.

---

## 🔢 Fórmula {: #formula }

La caída en la observación $t$ es la distancia desde el valor más alto alcanzado hasta ese momento:

$$
DD_t = \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau} \leq 0
$$

Con un nivel de confianza $c$, escribiendo $\alpha = 1 - c$ para la fracción de cola, la caída en riesgo es el cuantil $\alpha$ de esa serie:

$$
DaR_c = \inf\left\{\, d : P(DD_t \leq d) \geq \alpha \,\right\}
$$

En la práctica, eso es un ejercicio de ordenación, exactamente como lo es para el valor en riesgo: las caídas observadas durante la ventana analizada se ordenan de la más profunda a la menos profunda, y la cifra se lee en la posición a la que apunta $\alpha T$.

!!! info "Signo y lectura"

    La caída en riesgo es **no positiva** — cero o negativa. Una caída es un descenso desde un pico, por lo que no puede salir por encima de cero, y una cifra *más profunda* es una *más negativa*. Con un 95% de confianza, la afirmación es: en 19 de cada 20 observaciones la cartera no estuvo más por debajo de su pico que esto, y en la restante estuvo más abajo — en una cuantía que esta medida no indica.

    La $T$ aquí cuenta solo los puntos observados. La línea base desde la que parte un índice de riqueza tiene una caída de exactamente cero por construcción, y la familia de cuantiles la descarta antes de ordenar, por lo que ni entra en la ordenación ni infla el denominador. El [índice de Ulcer](ulcer-index.md) la conserva, de forma inofensiva, por una razón expuesta [en su propia página](ulcer-index.md#the-divisor).

---

## 🎯 Es un estadístico de orden {: #it-is-an-order-statistic }

La cifra se lee de una lista ordenada, lo que fija de antemano dos de sus propiedades.

- **Solo puede reportar una profundidad que la cartera realmente visitó.** No hay interpolación ni distribución supuesta; el número es una de las observaciones, seleccionada por posición. No puede describir una caída que el historial nunca contuvo.
- **Es una función escalonada de un índice.** Entre una posición y la siguiente no se mueve en absoluto, y cuando la posición cambia, salta una observación entera. Este es el mismo mecanismo que hace que el valor en riesgo cambie de forma todo o nada, descrito en [qué cambia la corrección](value-at-risk.md#what-the-correction-changes).

---

## 🔁 El mismo paso que da el VaR hacia el CVaR {: #the-same-step-that-var-takes-to-cvar }

Un cuantil se detiene en el límite. Dos carteras pueden reportar la misma caída en riesgo mientras una lo supera por un pelo y la otra se desploma mucho más allá, y nada en esta cifra las distingue. Ese silencio es exactamente lo que cubre la [caída en riesgo condicional](conditional-drawdown-at-risk.md).

| Lee la serie de **pérdidas** | Lee la serie de **caídas** | Qué responde |
|---|---|---|
| [valor en riesgo](value-at-risk.md) | **caída en riesgo** | ¿Dónde comienza la cola? |
| [VaR condicional](conditional-value-at-risk.md) | [caída en riesgo condicional](conditional-drawdown-at-risk.md) | ¿Hasta qué profundidad llega una vez que comienza? |

Leer las columnas hacia abajo da los dos pares de umbral y severidad; leer las filas horizontalmente da la misma pregunta planteada a una distribución y a una trayectoria. Una imagen completa necesita los cuatro, y el par de la derecha es el que sabe que la cartera tenía un pico desde el que caer.

---

## 💡 Interpretación {: #interpretation }

Interprétela como *cuánto por debajo del pico lo suele encontrar un mal día*, nunca como un suelo.

- **Es un umbral, no un límite.** Las caídas más profundas no están excluidas — por construcción, se esperan a la tasa indicada.
- **El nivel de confianza cambia la pregunta, no la precisión.** Pasar del 95% al 99% pregunta por un tramo más raro, estimado a partir de menos observaciones, no por el mismo tramo medido mejor.
- **No es la caída máxima.** La [caída máxima](max-drawdown.md) es el único punto más profundo de la ventana; este es el nivel que una fracción elegida de la ventana superó. Las dos coinciden solo en el límite en que la cola contiene una observación.

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "Silenciosa más allá del umbral"

    La medida se detiene en el límite de la cola de caídas. Si las caídas más allá de él son ligeramente más profundas o catastróficamente más profundas es información que no lleva, y ningún nivel de confianza la recupera. Use la [caída en riesgo condicional](conditional-drawdown-at-risk.md) para la profundidad.

!!! warning "Las observaciones de caída no son independientes entre sí"

    Las observaciones consecutivas dentro del mismo episodio son casi el mismo número: una cartera que está bajo el pico el martes casi con certeza está bajo el pico el miércoles. Por lo tanto, la cola de una serie de caídas rara vez consta de $\alpha T$ eventos separados — más a menudo es un puñado de episodios, o uno largo, contado día a día.

    Esto hace que la cifra sea menos estable de lo que sugiere su número de observaciones, y significa que una única caída prolongada puede proporcionar toda la cola por sí sola.

!!! warning "Hereda su ventana"

    Un cuantil empírico está acotado por el historial del que se extrae. Una ventana sin episodios severos produce una caída en riesgo poco profunda — no porque la cartera sea segura, sino porque todavía no se ha observado nada peor. Una [repetición histórica](historical-replay.md) o un [choque hipotético](hypothetical-shock.md) es la forma en que un escenario fuera de la ventana entra en el análisis.

---

## 🔗 Relacionados {: #related }

- 🌊 **[caída en riesgo condicional](conditional-drawdown-at-risk.md)** — hasta qué profundidad llega la cola de caídas más allá de este umbral
- 📉 **[valor en riesgo](value-at-risk.md)** — la misma construcción de cuantil, aplicada a pérdidas en lugar de caídas
- 🌊 **[VaR condicional](conditional-value-at-risk.md)** — la contraparte de severidad en la serie de pérdidas
- 📉 **[caída máxima](max-drawdown.md)** — la caída más profunda, en lugar de una tasa
- 🩹 **[índice de Ulcer](ulcer-index.md)** — toda la serie de caídas en un solo número, sin un nivel de confianza
- 🧪 **[calidad de datos](data-quality.md)** — la ventana y el número de observaciones a partir de los que se leyó el cuantil
