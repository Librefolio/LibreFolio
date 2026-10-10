# 🌊 Caída en Riesgo Condicional

La Caída en Riesgo Condicional promedia las caídas que sí superaron el umbral de Caída en Riesgo, respondiendo a cuán profunda es la caída una vez que pasa ese punto.

[Caída en Riesgo](drawdown-at-risk.md) dice **dónde comienza la cola de la caída**. Esta dice **cuán profunda llega** — el mismo paso que da [VaR condicional](conditional-value-at-risk.md) más allá de [valor en riesgo](value-at-risk.md), tomado sobre la serie de caídas en lugar de la serie de pérdidas.

La palabra *promedia* en esa frase inicial hace más trabajo de lo que parece. Es un promedio **ponderado**, y el peso está fijado por el nivel de confianza en lugar de por cuántas observaciones caen en la cola. Esa distinción es el tema de la mayor parte de esta página, porque el atajo que descarta es uno plausible.

---

## 🔢 Fórmula {: #formula }

En el nivel de confianza $c$, escribiendo $\alpha = 1 - c$ para la fracción de cola, la medida toma la forma **Rockafellar–Uryasev**:

$$
CDaR_c = DaR_c - \frac{1}{\alpha T} \sum_{t=1}^{T} \left( DaR_c - DD_t \right)^{+}
$$

donde $(x)^{+} = \max(x, 0)$, $DD_t$ es la caída en la observación $t$, y $T$ es el número de puntos observados en la serie.

La suma recoge la **severidad en exceso**: por cada observación más profunda que el umbral, cuánto más profunda. Toda observación menos profunda que el umbral no contribuye en nada. Ese total se reparte luego entre $\alpha T$ y se resta del umbral, lo que lleva el resultado más por debajo de cero que la Caída en Riesgo de la que parte.

Al igual que el umbral que extiende, la Caída en Riesgo Condicional es **no positiva** — una caída es un descenso desde un pico, y promediar caídas no produce una subida. Siempre es al menos tan severa como la Caída en Riesgo en el mismo nivel de confianza, porque cada cantidad que añade a ese umbral es una caída más allá de él.

---

## 🔬 No Es el Promedio de las Peores Observaciones {: #it-is-not-the-average-of-the-worst-observations }

La receta intuitiva — tomar las $k$ caídas más profundas y promediarlas — no es esta fórmula, y la diferencia está en el denominador.

La normalización anterior es $\alpha T$: una cantidad **fija** determinada por el nivel de confianza y la longitud del historial. El recuento de la cola $k$ es una cantidad diferente — el número de observaciones que realmente cayeron más allá del umbral, que solo puede ser un número entero. Cuando $\alpha T$ no es entero, la cola contiene necesariamente **más** observaciones que $\alpha T$, y dividir la misma severidad total entre ese recuento mayor produce una cifra menos profunda.

!!! warning "El atajo subestima la cola"

    Promediar sobre el recuento de la cola en lugar de sobre $\alpha T$ reporta el caso malo promedio como **más leve** de lo que dicen los datos. Las dos formas coinciden **exactamente** cuando $\alpha T$ es un número entero, y el atajo es demasiado optimista siempre que no lo sea.

    | Observaciones $T$ | $\alpha T$ al 95% | ¿Número entero? | Diferencia relativa |
    |---|---|---|---|
    | 740 | 37.00 | sí | **0.00000%** |
    | 745 | 37.25 | no | $-0.03817\%$ |
    | 750 | 37.50 | no | $-0.02528\%$ |
    | 760 | 38.00 | sí | **0.00000%** |
    | 800 | 40.00 | sí | **0.00000%** |
    | 1000 | 50.00 | sí | **0.00000%** |

    Las diferencias son fracciones de un porcentaje. Eso es precisamente lo que hace que el atajo sea duradero: una cifra equivocada por tres centésimas de un porcentaje parece un redondeo, no una fórmula diferente.

---

## 🪤 La Misma Trampa, en el Sentido Opuesto {: #the-same-trap-in-the-opposite-sense }

Esta es la misma forma de error que la página de [VaR condicional](conditional-value-at-risk.md) describe para la cola de pérdidas: un promedio simple plausible, equivocado por una fracción de un porcentaje, en la misma dirección — subestimar la cola. Y está gobernada por la **misma cantidad aritmética**, $(1 - c) \cdot T$, que la página de [valor en riesgo](value-at-risk.md#what-the-correction-changes) ya expone.

!!! warning "La misma cantidad, el significado opuesto — no traslades una regla de una a la otra"

    Que $(1 - c) \cdot T$ sea un número entero significa cosas opuestas en las dos páginas, y es fácil que ambas afirmaciones se fundan en una sola.

    | Medida | Cuando $(1 - c) \cdot T$ es un número entero |
    |---|---|
    | [valor en riesgo](value-at-risk.md#what-the-correction-changes) | las dos convenciones **divergen** — la cifra cambia en una observación completa |
    | **Caída en Riesgo Condicional** | el atajo **resulta ser correcto** — las dos formas coinciden exactamente |

    La divisibilidad es la condición en ambos casos; simplemente selecciona desacuerdo en uno y acuerdo en el otro.

---

## 🔍 Comprobar la cifra por ti mismo {: #checking-the-figure-yourself }

Dado que un $\alpha T$ entero es exactamente donde el atajo es indistinguible de la forma correcta, la elección de la longitud del historial decide si una comprobación manual puede detectar la diferencia.

!!! warning "Una longitud de historial redonda no puede distinguir las dos formas"

    | Observaciones $T$ | 90% | 95% | 99% |
    |---|---|---|---|
    | 250 | ciega | ve | ve |
    | 500 | **ciega** | **ciega** | **ciega** |
    | 750 | ciega | ve | ve |
    | 1000 | **ciega** | **ciega** | **ciega** |
    | 1003 | ve | ve | ve |
    | 2000 | **ciega** | **ciega** | **ciega** |

    **500, 1000 y 2000 observaciones son ciegas en todos los niveles de confianza; 1003 detecta en todos los niveles.**

    El patrón no es un caso límite raro — es lo contrario. $\alpha T$ es entero cuando $T$ es divisible por 10 al 90% de confianza, por 20 al 95%, y por 100 al 99%, y los números redondos son precisamente los divisibles. Dos años, mil días, quinientas sesiones: las longitudes de ventana que cualquiera elige primero son aquellas donde las dos formas devuelven el mismo número.

!!! tip "Así que elige una ventana poco redonda"

    Si quieres verificar la cifra recalculándola, elige una longitud de historial que **no** sea un múltiplo redondo de 10, 20 o 100 — 1003 observaciones en lugar de 1000. En una longitud divisible, las dos fórmulas candidatas coinciden hasta el último dígito, así que una coincidencia no te dice nada sobre cuál la produjo.

---

## 💡 Interpretación {: #interpretation }

Léela como *cuán por debajo del pico llegan las cosas una vez que superan el umbral* — la severidad de la cola de la caída, no su límite.

- **La distancia desde el umbral es informativa.** Una Caída en Riesgo Condicional muy por debajo de su Caída en Riesgo describe una cartera cuyos tramos malos, una vez que empiezan, se vuelven mucho más profundos de lo que sugiere el umbral.
- **Es una profundidad, no una duración.** Dice cuán profunda es la cola de la distribución de caídas, y nada sobre cuánto tiempo permaneció allí la cartera. El [índice de Ulcer](ulcer-index.md) es la cifra que incorpora la duración.
- **Se calcula sobre una serie dependiente de la trayectoria.** A diferencia del par basado en pérdidas, esta medida y su umbral se calculan a partir de caídas, que dependen del orden en que llegaron los rendimientos. Reordenar el historial reconstruye ambas.

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "La cola se estima a partir de pocas observaciones"

    Solo una pequeña fracción de la ventana queda más allá del umbral, y al 99% esa fracción es muy pequeña. La cifra es correspondientemente inestable: puede cambiar notablemente a medida que llegan observaciones, y dos ventanas adyacentes pueden discrepar más de lo que sugiere su diferencia de longitud.

!!! warning "Esas pocas observaciones no son independientes"

    Las caídas dentro de un mismo episodio son casi el mismo número día tras día, así que la cola suele ser una única caída prolongada contada muchas veces en lugar de $\alpha T$ eventos separados. La medida promedia observaciones, no episodios, y un historial con un año malo puede poner ese año en la cola por sí solo.

!!! warning "Está acotada por el historial que se le dio"

    Promediar la cola de la caída no hace aparecer caídas que la cartera nunca vivió. Una ventana que no contiene ningún episodio severo produce una cola leve, reportada honestamente. Una [Repetición Histórica](historical-replay.md) o un [Choque Hipotético](hypothetical-shock.md) es la forma en que un escenario fuera de la ventana entra en el análisis.

---

## 🔗 Relacionado {: #related }

- 📉 **[Caída en Riesgo](drawdown-at-risk.md)** — el umbral más allá del cual promedia esta cifra
- 🌊 **[VaR condicional](conditional-value-at-risk.md)** — el mismo paso de severidad, tomado sobre la serie de pérdidas
- 📉 **[valor en riesgo](value-at-risk.md)** — donde se expone completa la regla de divisibilidad
- 📉 **[Caída máxima](max-drawdown.md)** — la caída más profunda individual, en lugar de un promedio sobre la cola
- 🩹 **[índice de Ulcer](ulcer-index.md)** — profundidad y duración juntas, sin un nivel de confianza
- 🧪 **[Calidad de datos](data-quality.md)** — la ventana y el recuento de observaciones a partir de los cuales se calculó la cola
