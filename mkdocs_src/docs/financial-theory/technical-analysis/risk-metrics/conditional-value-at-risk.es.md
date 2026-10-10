# 🌊 VaR condicional

El VaR condicional retoma exactamente donde se detiene el Valor en Riesgo: mide la pérdida promedio en los casos en que el umbral del Valor en Riesgo fue de hecho superado.

[Valor en Riesgo](value-at-risk.md) dice **dónde comienza la cola**. Este dice **cuán profunda es**. Esa es toda la diferencia, y por eso esta es la cifra con la que abre la sección.

---

## 🔢 Fórmula {: #formula }

Con un nivel de confianza $c$, el VaR condicional es la pérdida esperada **dado** que la pérdida superó el Valor en Riesgo:

$$
CVaR_c = E\left[\, L \mid L \ge VaR_c \,\right]
$$

Empíricamente, es el promedio de las pérdidas en la cola más allá del umbral: la media de los casos malos, en lugar del límite de los casos malos.

Como promedia una región en lugar de leer un punto, lleva información que el cuantil no puede aportar: dos carteras con el **mismo** Valor en Riesgo pueden tener valores de VaR condicional muy diferentes, una superando el umbral por poco y la otra por mucho. Nada en la primera cifra las distingue; esta sí.

!!! tip "También recompensa la diversificación de forma consistente"

    Hay una segunda razón, más técnica, por la que la práctica de riesgo se ha orientado hacia los promedios de cola. Un cuantil puede comportarse de forma perversa cuando se combinan carteras: es posible que el Valor en Riesgo de una cartera combinada supere la suma de los Valores en Riesgo de sus partes, lo que diría que diversificar aumentó el riesgo. Un promedio sobre la cola no tiene ese defecto, lo que lo convierte en la cifra de mejor comportamiento cuando se compara el riesgo entre composiciones.

---

## 🔬 Cómo se toma el promedio de la cola {: #how-the-tail-average-is-taken }

La cola rara vez contiene un número entero de observaciones. Con un 95% de confianza a lo largo de unos cientos de periodos, el límite de la cola cae **entre** dos pérdidas observadas, y la observación que se sitúa en ese límite pertenece a la cola solo en parte.

Por tanto, el promedio pondera esa observación límite por la fracción de ella que realmente queda más allá del umbral, en lugar de contar por igual cada observación de la cola. Tratar una observación parcialmente incluida como totalmente incluida arrastra el promedio hacia el límite —es decir, hacia la pérdida menos severa de la cola— y, por tanto, informa de una cola menos profunda de lo que es.

---

## 📐 La corrección y qué le hace a su cifra {: #the-correction }

Este es un cambio en una cifra que quizá ya haya visto. El estimador anterior tomaba un **promedio uniforme** sobre la cola; el actual aplica la ponderación fraccionaria descrita arriba.

!!! warning "La nueva cifra no es solo distinta: es menos optimista"

    La corrección mueve el VaR condicional **hacia arriba en todos los niveles de confianza**, en cada muestra de un estudio de medición de 2.000 series simuladas de 750 observaciones cada una: 2.000 de 2.000, sin una sola excepción en ninguno de los dos sentidos.

    Esa dirección es lo importante. La cifra anterior **subestimaba la cola**: informaba del caso malo promedio como más leve de lo que decían los datos. Un usuario que ve subir este número no está viendo que una nueva metodología produzca una diferencia arbitraria: está viendo una estimación optimista reemplazada por una precisa.

| Confianza | Cambio medido (mediana) | Cambio mayor observado | Muestras que subieron |
|---|---|---|---|
| 90% | +0,364% | +0,476% | 2.000 / 2.000 |
| 95% | +0,267% | +0,404% | 2.000 / 2.000 |
| 99% | +0,727% | +1,748% | 2.000 / 2.000 |

**El desplazamiento crece con el nivel de confianza**, y la razón se desprende del mecanismo: cuanto mayor es el nivel, menos observaciones hay en la cola, por lo que la única parcialmente incluida soporta una mayor proporción del promedio. Al 99%, un puñado de observaciones decide la cifra, y ponderar mal una de ellas mueve el resultado más de lo que lo haría al 90%.

!!! info "La cifra corregida coincide con la implementación de referencia"

    Medida frente a la implementación de referencia estándar del mismo estimador, la diferencia restante es $-4.27 \times 10^{-18}$: ruido de redondeo en coma flotante, no una brecha metodológica. Ahora ambos calculan la misma cantidad.

La cifra del umbral también se mueve, aunque bajo una condición mucho más estrecha: el [Valor en Riesgo](value-at-risk.md) que se informa junto a este cambia solo cuando el recuento de observaciones es divisible de la forma que requiere el nivel de confianza, y donde cambia, salta una observación entera en lugar de desplazarse ligeramente. La regla, y cómo comprobar un caso concreto, se expone en [qué cambia la corrección](value-at-risk.md#what-the-correction-changes). Son dos cambios distintos que coinciden en el tiempo: este afecta a cómo se promedia la cola, no a dónde comienza la cola.

---

## 💡 Interpretación {: #interpretation }

Lea esta cifra como *cuán mal se pone cuando se pone mal*: el resultado promedio entre los peores casos de la ventana, no el peor de ellos.

- Siempre es al menos tan severa como el Valor en Riesgo del mismo nivel, porque promedia valores que están todos más allá de ese umbral.
- La brecha entre ambas es informativa en sí misma: un VaR condicional muy por encima de su Valor en Riesgo describe una cartera cuyos casos malos, cuando llegan, son mucho peores de lo que sugiere el umbral.
- Al igual que el cuantil que extiende, lee la **distribución** y no la secuencia: reordenar el orden de los rendimientos observados la deja sin cambios. La visión dependiente de la trayectoria corresponde a la [Caída Máxima](max-drawdown.md) y la [Caída Actual](current-drawdown.md), y una imagen completa necesita ambas.

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "La cola se estima a partir de pocas observaciones"

    Por definición, solo una pequeña fracción de la ventana queda más allá del umbral, y al 99% esa fracción es muy pequeña. Por tanto, la cifra es la menos estable de las medidas distribucionales: puede desplazarse notablemente a medida que llegan nuevas observaciones, y dos ventanas adyacentes pueden discrepar más de lo que sugiere la diferencia de longitud.

!!! warning "Sigue estando limitada por el historial que se le dio"

    Promediar la cola no hace aparecer pérdidas que la cartera nunca experimentó. Si la ventana no contiene ningún episodio severo, la cola que promedia es leve: la medida informará con honestidad sobre un historial que sencillamente no ha sido puesto a prueba. Una [Repetición Histórica](historical-replay.md) o un [Choque Hipotético](hypothetical-shock.md) es la forma en que un escenario fuera de la ventana entra en el análisis.

!!! warning "Describe gravedad, no probabilidad"

    La cifra es condicional a que se alcance la cola. No dice nada sobre cuán probable es eso más allá del nivel de confianza que la definió, ni nada sobre cuándo: los periodos malos se agrupan, y ningún resumen de distribución recoge eso.

---

## 🔗 Relacionado {: #related }

- 📉 **[Valor en Riesgo](value-at-risk.md)** — el umbral más allá del cual promedia esta cifra
- 📉 **[Caída Máxima](max-drawdown.md)** — la peor caída acumulada a lo largo de la trayectoria
- 📊 **[Volatilidad](volatility.md)** — dispersión en ambas direcciones, en lugar de solo la cola de pérdidas
- ⚡ **[Choque Hipotético](hypothetical-shock.md)** — un escenario que el historial observado nunca contuvo
- 🧪 **[Calidad de Datos](data-quality.md)** — la ventana de la que se extrajo la cola
