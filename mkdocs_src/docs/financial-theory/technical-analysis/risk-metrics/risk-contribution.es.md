# 🧩 Contribución al riesgo

La contribución al riesgo atribuye el riesgo total de la cartera a las posiciones individuales, y lo que aporta cada posición generalmente no es lo mismo que la parte de la cartera que representa.

Conocer los pesos no te dice nada nuevo: son visibles en la propia cartera. Saber de dónde viene el **riesgo** normalmente sí, porque la contribución de una posición depende de cuán volátil es y de cómo se mueve junto con todo lo demás que se mantiene junto a ella.

---

## 🔢 Fórmula {: #formula }

La descomposición parte de la varianza de la cartera escrita a través de la matriz de covarianzas $\Sigma$ de los rendimientos de los activos y el vector de pesos $w$:

$$
\sigma_p = \sqrt{w^{\top} \Sigma\, w}
$$

De ella se derivan tres cantidades, en este orden:

$$
MCTR_i = \frac{(\Sigma w)_i}{\sigma_p}, \qquad
CCTR_i = w_i \cdot MCTR_i, \qquad
PCTR_i = \frac{CCTR_i}{\sigma_p}
$$

| Cantidad | Se lee como | Responde |
|---|---|---|
| $MCTR_i$ — marginal | Sensibilidad de la volatilidad de la cartera al peso de $i$ | *Si añado un poco de esta posición, ¿cuánto se mueve el riesgo total?* |
| $CCTR_i$ — componente | Esa sensibilidad multiplicada por el peso realmente mantenido | *¿Cuánto del riesgo total aporta esta posición, en unidades de volatilidad?* |
| $PCTR_i$ — porcentaje | El componente como proporción de la volatilidad total | *¿Qué fracción del riesgo de la cartera representa esta posición?* |

La cifra marginal es la derivada $\partial \sigma_p / \partial w_i$: describe la **siguiente** unidad de la posición, no la que se mantiene. La cifra de componente es la que describe la posición tal como está.

!!! info "La anualización se aplica a la matriz de covarianzas"

    Cada entrada de $\Sigma$ se multiplica por el factor de anualización observado $f$ antes de que se ejecute la descomposición, por lo que la volatilidad de la cartera y las tres cifras de contribución salen en base anual. Escalar una covarianza por $f$ es la forma matricial de multiplicar una desviación estándar por $\sqrt{f}$: la misma operación, y el mismo factor medido, que utiliza [Volatilidad](volatility.md). Consulta [Anualización observada](observed-annualization.md) para saber de dónde viene $f$.

---

## ➗ Por qué las partes suman {: #why-the-parts-add-up }

Las contribuciones por componente suman la volatilidad de la cartera **exactamente**, y las contribuciones porcentuales, por lo tanto, suman $1$:

$$
\sum_i CCTR_i = \sum_i w_i \frac{(\Sigma w)_i}{\sigma_p} = \frac{w^{\top} \Sigma\, w}{\sigma_p} = \frac{\sigma_p^{2}}{\sigma_p} = \sigma_p
\qquad\Longrightarrow\qquad
\sum_i PCTR_i = 1
$$

Esto no es una aproximación que da la casualidad de ser cercana, ni una normalización aplicada después para forzar los números a un total redondo. Es la descomposición de Euler, y se cumple porque $\sigma_p$ es **homogénea de grado 1** en los pesos: duplicar cada peso duplica la volatilidad de la cartera. Cualquier función de este tipo se recupera exactamente mediante la suma de sus argumentos multiplicados por sus propias derivadas parciales, que es precisamente la suma anterior.

La consecuencia práctica es la razón por la que la métrica se publica: como las partes son exactas y suman uno, **una contribución porcentual puede compararse directamente con un peso**. Una posición que representa el 10% de la cartera y soporta el 30% del riesgo es una afirmación en la que no hay ningún escalado oculto.

---

## ⚖️ La contribución no es el peso {: #contribution-is-not-weight }

Los dos números responden a preguntas diferentes, y se separan por dos razones que se combinan:

- **Volatilidad.** Una posición que se mueve el doble que el resto aporta más riesgo por unidad de capital.
- **Correlación.** Una posición que se mueve *con* las demás añade su volatilidad a la de ellas; una que se mueve en contra cancela en parte lo que hacen las otras. La misma posición, con el mismo peso, contribuye de forma diferente según con qué otras posiciones se acompañe.

Esa segunda razón es por la que la contribución no puede leerse de una única posición de forma aislada: $(\Sigma w)_i$ contiene todas las covarianzas entre el activo $i$ y el resto de la cartera, por lo que cambiar una posición *no relacionada* cambia la contribución de esta.

!!! tip "Dónde la métrica se gana su lugar"

    Una posición pequeña en algo volátil y estrechamente ligado al resto de la cartera puede soportar una parte del riesgo varias veces mayor que su parte del capital, y la vista de la cartera nunca lo mostrará, porque la vista de la cartera muestra pesos. A la inversa, una posición grande que se mueve al margen de todo lo demás puede contribuir con mucho menos riesgo de lo que su tamaño sugiere. La diversificación es visible aquí de una forma en la que no lo es en [Correlación](correlation.md) por sí sola: la correlación dice qué pares se mueven juntos; esto dice cuánto cuesta eso una vez que se tienen en cuenta los importes mantenidos.

---

## 🧾 Qué deben cumplir las entradas {: #what-the-inputs-must-satisfy }

La descomposición rechaza las entradas que no puede descomponer honestamente. Estos son **límites declarados de la primera etapa**, no vacíos dejados por omisión:

| Requisito | Comportamiento cuando se incumple |
|---|---|
| Los pesos deben ser no negativos | Rechazado — las posiciones cortas están fuera del contrato de la primera etapa |
| La composición no debe estar apalancada | Rechazado en una fase anterior — los pesos de los activos por encima del 100% del valor del alcance están fuera del contrato |
| La matriz de covarianzas debe ser simétrica | Rechazado, dentro de una tolerancia numérica para el ruido de punto flotante |
| Las dimensiones de la matriz deben coincidir con los pesos | Rechazado |
| Todas las series de rendimiento deben compartir un calendario común | Rechazado — la matriz de covarianzas se construye sobre un único calendario de observación |

Una posición corta rompería la aritmética anterior de una manera concreta: con pesos negativos, una contribución por componente puede ser negativa, y una parte del “riesgo total” que está por debajo de cero no puede leerse como una parte de nada. Rechazar la entrada es la respuesta honesta hasta que el contrato de presentación cubra ese caso.

El efectivo se gestiona sin aparecer en la matriz en absoluto. Los pesos de los activos suman uno menos la proporción de efectivo, por lo que la volatilidad calculada ya es la de **toda** la cartera, efectivo incluido, y el efectivo nunca aparece como contribuyente, porque una posición que no se mueve tiene una contribución marginal de cero. La proporción de efectivo se publica junto con las contribuciones para que el lector pueda ver cuál es el resto.

---

## 💡 Interpretación {: #interpretation }

Lee la contribución porcentual **en relación con el peso**, no por sí sola:

- contribución ≈ peso — la posición carga con su propia parte, ni más
- contribución > peso — es una fuente concentrada de riesgo en relación con el capital comprometido en ella
- contribución < peso — está diluyendo el riesgo de la cartera, ya sea porque es tranquila o porque se mueve de forma diferente al resto

La cifra marginal responde a una pregunta diferente y es la que hay que usar cuando se piensa en un cambio: dice qué le hace a la volatilidad total el **siguiente** euro que entra en esa posición. Una posición puede tener una gran contribución por componente simplemente porque es grande, mientras que su contribución marginal no tiene nada de especial.

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "Descompone la volatilidad, no la pérdida"

    Todas las cifras de esta página son una parte de la **volatilidad de la cartera**. La volatilidad cuenta movimientos en ambas direcciones, por lo que una posición que contribuye con el 30% del riesgo no por ello se espera que produzca el 30% de ninguna pérdida. Las contribuciones a una cifra a la baja son una descomposición diferente, y esto no es eso. Para saber qué captura y qué no captura la fluctuación, consulta [Volatilidad](volatility.md).

!!! warning "Es una instantánea de la composición actual"

    Los pesos son los que se tienen ahora, y la matriz de covarianzas se estima sobre la ventana analizada. El resultado describe la cartera de hoy medida frente a ese historial: no es una afirmación sobre cómo se distribuyó el riesgo en el pasado, cuando la composición era diferente.

!!! warning "La matriz es una estimación y hereda su ventana"

    Las covarianzas se estiman a partir de una muestra finita sobre un único calendario común. Una ventana corta, un tramo turbulento o un activo con un historial de precios escaso producen una estimación que otra ventana no reproduciría, y cada contribución deriva de esa estimación. Se sabe, en particular, que las correlaciones se mueven cuando los mercados están bajo tensión. Cada resultado publica el recuento de observaciones y la ventana que utilizó; consulta [Calidad de datos](data-quality.md).

!!! warning "La volatilidad cero devuelve ceros, no un resultado ausente"

    Si la volatilidad de la cartera es indistinguible de cero, las tres cifras de contribución se devuelven como exactamente cero. Esa es la respuesta, no un marcador de posición: si no hay riesgo que atribuir, cada parte de él es genuinamente nada. Vale la pena contrastarlo con la página [Beta y rendimiento activo](beta-active-return.md), donde un índice de referencia sin varianza produce **ningún valor en absoluto** — allí la cantidad sería una división por cero, así que no hay nada que informar; aquí la cantidad existe y es igual a cero.

---

## 🔗 Relacionado {: #related }

- 🔗 **[Correlación](correlation.md)** — qué posiciones se mueven juntas, antes de tener en cuenta los importes
- 📊 **[Volatilidad](volatility.md)** — el total que se descompone
- 🎯 **[Concentración](concentration.md)** — cuánto de la cartera se concentra en cuán pocas posiciones
- 🗓️ **[Anualización observada](observed-annualization.md)** — el factor aplicado a la matriz de covarianzas
- 🧪 **[Calidad de datos](data-quality.md)** — la ventana y las observaciones sobre las que se estimó la matriz
