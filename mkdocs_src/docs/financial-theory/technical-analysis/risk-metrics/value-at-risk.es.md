# 📉 Valor en Riesgo

El Valor en Riesgo responde a una pregunta deliberadamente estrecha: en un horizonte dado y con un nivel de confianza elegido, ¿cuál es la pérdida que no debería superarse?

Lo estrecho es el punto, y también es la trampa. El VaR marca **dónde comienza la cola** — es un umbral, no un máximo, y guarda silencio sobre todo lo que queda más allá.

---

## 🔢 Fórmula {: #formula }

Con un nivel de confianza $c$, el Valor en Riesgo es el cuantil de la distribución de pérdidas:

$$
VaR_c = \inf\left\{\, \ell : P(L \le \ell) \ge c \,\right\}
$$

En la práctica, eso es un ejercicio de ordenación: las pérdidas observadas durante la ventana analizada se ordenan, y la cifra se lee en la posición que indica el nivel de confianza.

El resultado es una **declaración de frecuencia**. Con un 95%, dice que en 19 de cada 20 períodos la pérdida no es peor que la cifra reportada — y que en el restante es peor, en una cuantía que esta medida no indica.

---

## 📜 Medido, no modelado {: #measured-not-modelled }

El Valor en Riesgo de LibreFolio es **histórico**: es el cuantil empírico de las pérdidas que realmente experimentó la cartera. No hay ninguna distribución asumida en él.

Esa es una elección deliberada frente a la alternativa más común, en la que se asume que los rendimientos se distribuyen normalmente y el cuantil se lee de esa curva.

!!! warning "El supuesto gaussiano falla exactamente cuando el número importa"

    Los rendimientos reales del mercado tienen **colas más gruesas** que una distribución normal: los movimientos extremos ocurren con más frecuencia, y son mayores, de lo que permite la curva de campana. Por tanto, un VaR gaussiano paramétrico promete que los peores días son más raros de lo que son — y hace esa promesa con mayor seguridad en los niveles de confianza altos, que son precisamente los que se usan para pensar en crisis.

    Es una medida de riesgo que resulta reconfortante en proporción a lo equivocada que está. El enfoque empírico no puede cometer ese error, porque nunca afirma una forma: cuenta lo que ocurrió.

La ventaja se gana, no es gratuita, y el precio está en la misma página que el beneficio:

!!! warning "No puede mostrarle una pérdida que nunca ha vivido"

    Un cuantil empírico está acotado por la muestra de la que se extrae. Un historial corto, o uno tranquilo, produce un Valor en Riesgo tranquilo — no porque la cartera sea segura, sino porque aún no se ha observado nada peor. La medida describe la ventana que se le dio, y una ventana que no contiene ninguna crisis no contiene pérdidas del tamaño de una crisis.

---

## 💡 Interpretación {: #interpretation }

Lea la cifra como *con qué frecuencia*, nunca como *cuánto en el peor caso*:

- **Es un umbral, no una cota.** Las pérdidas más allá de él no están excluidas — por construcción, se espera que ocurran a la tasa indicada.
- **No dice nada sobre la profundidad más allá.** Dos carteras pueden reportar el mismo VaR mientras una lo supera moderadamente y la otra catastróficamente. Esa diferencia es para lo que sirve el [VaR condicional](conditional-value-at-risk.md), y es la razón por la que esta sección comienza con esa cifra en lugar de esta.
- **Es una tasa, no un calendario.** "Un período de cada veinte" no significa un período malo cada veinte. Los períodos malos llegan en grupos, y un cuantil no tiene memoria del orden.

Esa última propiedad merece enunciarse con precisión, porque separa esta medida de la mitad de la sección: **reordene aleatoriamente los rendimientos observados y el Valor en Riesgo no se mueve en absoluto.** Lee la distribución, no la secuencia. Las cifras que leen la secuencia — [Caída máxima](max-drawdown.md) y [Caída actual](current-drawdown.md) — pueden cambiar por completo con la misma reordenación. Ninguna de las dos visiones es completa por sí sola, y por eso se publican ambas.

La observación única menos favorable de la ventana se reporta como su propia cifra, [Peor realización](worst-realization.md): donde el Valor en Riesgo dice *un período de cada veinte va peor que esto*, esa dice *y el peor fue este, en esta fecha*.

---

## 🔄 Qué cambia aquí la corrección del estimador de cola {: #what-the-correction-changes }

El promedio de cola utilizado por el [VaR condicional](conditional-value-at-risk.md) se ha corregido, y la pregunta natural es si la cifra del Valor en Riesgo se mueve con él.

Lo hace para algunas configuraciones y no para otras, y la frontera entre ambas es exacta. De qué lado cae una cifra dada lo decide la aritmética, no la inspección, así que puede comprobarse en lugar de asumirse.

!!! info "La condición, en su totalidad"

    El Valor en Riesgo reportado cambia **exactamente cuando $(1-c) \cdot T$ es un número entero**, donde $c$ es el nivel de confianza y $T$ es el número de observaciones que entran en el cálculo de la cola.

    Cuando ese producto no es un número entero, ambas convenciones seleccionan la misma observación y la cifra no es solo cercana, sino idéntica.

### 🎚️ Por qué el cambio es todo o nada {: #why-the-change-is-all-or-nothing }

Un estudio de medición sobre 24 combinaciones de nivel de confianza y longitud de historial, con 300 muestras cada una — 7.200 pruebas — encontró que cada combinación era una en la que **o todas las muestras se movían o ninguna lo hacía**. Ninguna combinación produjo una proporción intermedia.

Eso se deriva de lo que es la cifra. El Valor en Riesgo aquí es un **estadístico de orden**: el cálculo ordena las pérdidas observadas y lee la que está en la posición que indica el nivel de confianza, por lo que el número reportado es siempre una pérdida que la cartera realmente experimentó. Es una función escalonada de un índice, no una función continua de los datos.

Cuando se cumple la condición anterior, el índice se desplaza una posición — y un índice que se desplaza no se desplaza un poco. Selecciona una **observación diferente**. Por tanto, la cifra salta en un estadístico de orden completo, y el mayor salto de este tipo medido fue **+4,587%**. Entre números enteros, ambas convenciones redondean al mismo índice y la salida es idéntica bit a bit.

!!! info "Donde la cifra se mueve, se mueve hacia arriba"

    Esta cifra y el [VaR condicional](conditional-value-at-risk.md) se mueven en la misma dirección: hacia arriba. No se encontró ninguna configuración en la que cualquiera de los dos números se moviera hacia una lectura más optimista. Donde un Valor en Riesgo cambió, el riesgo reportado previamente era **demasiado bajo**.

### 📅 Qué historiales se ven afectados {: #which-histories-are-affected }

$(1-c) \cdot T$ es un número entero cuando $T$ es divisible por 10 con un 90% de confianza, por 20 con un 95%, y por 100 con un 99%:

| Observaciones $T$ | 90% | 95% | 99% |
|---|---|---|---|
| 250 | se mueve | — | — |
| 500 | se mueve | se mueve | se mueve |
| 750 | se mueve | — | — |
| 1000 | se mueve | se mueve | se mueve |
| 1003 | — | — | — |
| 2000 | se mueve | se mueve | se mueve |

El patrón de esa tabla merece ser nombrado, porque es lo opuesto a un caso límite raro: **los historiales afectados son los redondos**. Un año, dos años, tres años, mil días — los números redondos son precisamente los números divisibles, y los números redondos son lo que una interfaz te invita a escribir. Un historial de 1.003 observaciones, en cambio, no se ve afectado en ningún nivel de confianza.

Este es el hecho que responde a la pregunta que la corrección suele provocar — **por qué un análisis cambió y el de un colega no**. Dos análisis de la misma cartera con el mismo nivel de confianza pueden discrepar sobre si ocurrió algo, porque uno se ejecutó sobre una ventana redonda y el otro no. Ninguno está equivocado, y la diferencia entre ellos no es una cuestión de grado: es la divisibilidad de un único número entero.

### ⏳ El número de observaciones no es la longitud del historial {: #the-observation-count-is-not-the-history-length }

$T$ no es el número de días de la ventana. La cola se calcula a partir de rendimientos **compuestos por horizonte** — cada serie de $n$ rendimientos consecutivos compuesta en uno — por lo que el número de valores que entran en el cálculo es

$$
T = N - n + 1
$$

donde $N$ es el número de rendimientos en la ventana y $n$ es el horizonte contado en observaciones. El parámetro **Horizonte (días)** $h$ está en **días calendario**, y se convierte en observaciones a la tasa a la que la serie se observó realmente — su [factor de anualización observado](observed-annualization.md) $f$:

$$
n = \max\left(1,\ \operatorname{round}\left(\frac{h \cdot f}{365}\right)\right)
$$

Por tanto, un horizonte abarca el mismo tramo de calendario en todas las series, a la observación más cercana. Treinta días — el mes malo que la aplicación reporta junto al día malo — son $n = 21$ observaciones de una serie cotizada en días hábiles ($f \approx 252$) y $n = 30$ de una cotizada cada día calendario ($f = 365$).

El módulo de análisis calcula exactamente estas cantidades y publica ambas con el resultado: $n$ como su horizonte en observaciones, $T$ como su recuento de observaciones. Ese recuento publicado, no la longitud de la ventana, es el $T$ al que se aplica la regla. También es el recuento con el que se verifica el mínimo de 20 observaciones: con menos de 20 ventanas compuestas, la cifra no se calcula, y el resultado vuelve como no disponible por historial insuficiente. Un mes malo, por tanto, necesita $N \ge 40$ rendimientos con $f \approx 252$, donde $n = 21$, y $N \ge 49$ con $f = 365$.

El horizonte es un campo de formulario del análisis, cuyo valor predeterminado es $h = 1$ y que acepta valores de 1 a 365. Con el valor predeterminado, $n = 1$ en todas las series — ninguna se observa más de una vez por día calendario, por lo que $f \le 365$ — y $T = N$, que es por lo que los historiales redondos son los afectados.

Auméntelo y la tabla anterior se invierte. Con $h = 10$, una serie cotizada en días hábiles compone $n = 7$ observaciones, por lo que un $N$ redondo produce $T = N - 6$, un número que termina en 4; una serie cotizada cada día calendario compone $n = 10$, y $T = N - 9$ termina en 1. Ninguno es nunca divisible por 10, 20 o 100, y lo mismo ocurre en cualquier serie observada al menos 54,75 veces al año ($f \ge 54.75$): diez días entonces contienen entre 2 y 10 observaciones, por lo que un $N$ redondo pierde entre 1 y 9 de ellas. En las mismas longitudes de historial, con $h = 10$ **250, 500, 750, 1000, 1250 y 2000 observaciones no se ven afectadas en ninguno de los tres niveles de confianza**, en cualquiera de los dos tipos de serie. El horizonte predeterminado de 1 es precisamente la configuración bajo la cual los historiales redondos se mueven; un horizonte de 10 deja esos mismos historiales intactos — excepto en una serie observada con menos frecuencia, como un fondo semanal ($f \approx 52$), donde diez días aún redondean a una única observación y $T = N$. Esto es una consecuencia de la aritmética más que un defecto en ella, pero sí significa que una comparación entre dos análisis tiene que coincidir en el horizonte, así como en la ventana y el nivel — y, dado que el mismo horizonte contiene un $n$ diferente con un $f$ diferente, también en la frecuencia observada de la serie.

!!! info "Cómo comprobar un caso particular"

    Tome el recuento de observaciones que el Valor en Riesgo publica con sus cifras — `observations`, ya neto del horizonte y publicado junto a `horizon_observations` — y multiplíquelo por $1 - c$. Un número entero significa que la cifra se movió por una observación; cualquier otra cosa significa que no cambió. El recuento de observaciones en los metadatos del resultado (`n_observations`, véase [Calidad de datos](data-quality.md)) es $N$, contado antes de la composición: es igual a $T$ solo cuando $n = 1$.

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "Silencioso más allá del umbral"

    La medida se detiene en el límite de la cola. Si las pérdidas más allá son ligeramente peores o muchas veces peores es información que no aporta, y ningún nivel de confianza la recupera. Use el [VaR condicional](conditional-value-at-risk.md) para la profundidad.

!!! warning "El nivel de confianza cambia la pregunta, no la precisión"

    Pasar del 95% al 99% no produce una respuesta más precisa; plantea una pregunta sobre un evento más raro. También pregunta sobre uno estimado a partir de menos observaciones, por lo que el nivel más alto se lee de una porción más delgada del mismo historial.

!!! warning "Hereda su ventana"

    La cifra se calcula a partir de los rendimientos del período analizado, sobre el calendario de observación que comparten esas series. La ventana, el recuento de observaciones y la base utilizada se publican con el resultado — véase [Calidad de datos](data-quality.md).

---

## 🔗 Relacionado {: #related }

- 🌊 **[VaR condicional](conditional-value-at-risk.md)** — cuán profunda es la cola una vez superado el umbral
- 📉 **[Caída máxima](max-drawdown.md)** — la peor caída a lo largo del camino, que un cuantil no puede ver
- 📊 **[Volatilidad](volatility.md)** — la dispersión en su conjunto, en lugar de un punto de la distribución
- ⏮️ **[Repetición histórica](historical-replay.md)** — un episodio específico en lugar de un estadístico resumen
- 🔻 **[Peor realización](worst-realization.md)** — la observación única más profunda, como un hecho fechado en lugar de una tasa
- 🧪 **[Calidad de datos](data-quality.md)** — la ventana y las observaciones de las que se leyó el cuantil
