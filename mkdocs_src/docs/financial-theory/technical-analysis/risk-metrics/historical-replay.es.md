# ⏮️ Repetición histórica

La repetición histórica aplica los movimientos de un episodio pasado real a la cartera tal como está compuesta hoy, preguntando qué haría ese mismo episodio ahora.

Es la pregunta *¿qué me haría 2008?* respondida aritméticamente en lugar de recurriendo al recuerdo — y el valor de la respuesta depende enteramente de entender de quién es la cartera que se está sometiendo a ese episodio.

---

## 🔢 Cómo se calcula la repetición {: #how-the-replay-is-computed }

Eliges un episodio — un rango de fechas — y el análisis toma los rendimientos reales de cada posición durante ese rango. A cada activo se le da una unidad de riqueza al inicio y capitaliza por su cuenta:

$$
W_i(t) = W_i(t-1) \cdot \left(1 + r_i(t)\right), \qquad W_i(0) = 1
$$

La riqueza de la cartera en cada paso es la suma ponderada de esos índices de riqueza de los activos, más la parte en efectivo:

$$
W_p(t) = c + \sum_i w_i \, W_i(t)
$$

y el rendimiento de la cartera para el periodo es el cambio en esa riqueza:

$$
r_p(t) = \frac{W_p(t)}{W_p(t-1)} - 1
$$

La parte en efectivo $c$ toma por defecto lo que dejen los pesos de los activos, $c = 1 - \sum_i w_i$, y se exige que los pesos más el efectivo sumen $1$. Todas las series deben ejecutarse en un mismo calendario común; se rechazan los rendimientos por debajo de $-100\%$ y los pesos negativos.

---

## 🧭 Nada se rebalancea {: #nothing-is-rebalanced }

Los pesos $w_i$ multiplican índices de riqueza de activos que crecen por separado. Solo se imponen los pesos **iniciales**: a partir del segundo periodo, la composición efectiva es la que ha creado la capitalización.

Eso es deliberado, y es el significado de *comprar y mantener*. Durante una caída, los activos que más caen se encogen como proporción de la cartera por sí solos — ninguna regla los vende, y ninguna regla los vuelve a completar. Una repetición rebalanceada sería un ejercicio distinto, porque el rebalanceo compra lo que ha caído y reportaría un resultado diferente para el mismo episodio.

!!! info "El efectivo rinde exactamente cero"

    La parte en efectivo contribuye una constante a la riqueza de la cartera en cada periodo. Esa no es una elección neutral, es una elección específica con consecuencias en ambas direcciones: durante una caída, el efectivo es la parte de la cartera que mantiene su valor, y hará que la pérdida repetida sea más superficial de lo que sugerirían solo las posiciones invertidas. Durante un tramo largo o inflacionario, un rendimiento nominal cero es una pérdida real que la repetición no muestra, porque la repetición se expresa en términos nominales.

---

## ❓ De quién es la cartera que se repite {: #whose-portfolio-is-being-replayed }

Este es el punto en el que el resultado se malinterpreta con más frecuencia.

!!! warning "Así no se comportó tu cartera"

    La repetición proyecta **las posiciones de hoy** hacia atrás. Responde *¿cómo le habría ido a la cartera que tengo ahora en ese episodio?* — no *¿cómo me fue a mí?* Las dos coinciden solo si la composición nunca cambió, y divergen cada vez que se compró, vendió o cambió de tamaño una posición. El rendimiento pasado real consta en los registros y se informa en otro lugar; esta cifra es una hipótesis sobre una composición que, en muchos casos, no existía en esas fechas.

Hay una segunda consecuencia, más silenciosa. La cartera que se tiene hoy es la que **sobrevivió** a cada decisión tomada desde entonces: las posiciones que se vendieron, incluidas las que se vendieron porque salieron mal, no están en ella. Proyectarla hacia atrás arrastra esa selección consigo, así que una repetición de un episodio malo puede parecer más cómoda de lo que realmente fue — no porque la aritmética esté mal, sino porque la aritmética se está aplicando a un conjunto de posiciones elegidas con la ventaja de todo lo que ocurrió después.

---

## 🧩 Posiciones sin suficiente historial {: #holdings-without-enough-history }

Un episodio de 2008 no se puede repetir en un fondo lanzado en 2019: no hay rendimientos que aplicar. El análisis ni rellena el hueco con una suposición ni se detiene: **deja fuera la posición** y repite las demás.

Cada posición se juzga por sus propias cotizaciones, no por el calendario compartido. Solo participa si tiene precio en ambos extremos de la ventana, con un margen de siete días naturales del [umbral de obsolescencia](data-quality.md#staleness-threshold): al inicio, una cotización en los siete días anteriores a que comience la ventana — o, para un historial que comienza dentro de la ventana, una primera cotización no más de siete días después de que comience la ventana; al final, una última cotización no más de siete días antes de que termine la ventana. La prueba se ejecuta antes de preparar las series de rendimientos, y el orden importa. Las series repetidas comparten un calendario (consulta [Limitaciones](#limitations)): una posición que empieza tarde, si se mantuviera, movería el inicio de ese calendario y acortaría la repetición de todas las demás posiciones para ajustarse a la suya.

### 🏷️ Por qué se deja fuera una posición {: #why-a-holding-is-left-out }

Cada posición excluida lleva exactamente un motivo:

| Motivo | Qué muestran las cotizaciones de la posición |
|---|---|
| Sin precios en el periodo | Ninguna cotización dentro de la ventana, y ninguna en los siete días anteriores a su inicio. |
| Primera cotización después de que comenzó el periodo | Su historial comienza dentro de la ventana, más de siete días después del inicio. |
| Sin precio reciente cuando comenzó el periodo | Se cotizó antes de la ventana, pero no en los siete días anteriores a su inicio — un hueco en un historial más antiguo, o un ritmo disperso como un NAV mensual. |
| Sin precio reciente al final del periodo | Ningún precio en los últimos siete días de la ventana. Las cotizaciones se leen solo hasta el final de la ventana, así que un hueco y una exclusión de cotización se ven igual allí y comparten este motivo. |
| Sin tipo de cambio a tu moneda | Ningún tipo de cambio desde su moneda a la moneda en la que se expresa el análisis. |
| Excluida por ti | El lector la excluyó manualmente, donde eso sea posible — consulta [Proxies](#proxies). |

### ⚖️ Qué ocupa su lugar {: #what-takes-its-place }

Lo que ocurre con una posición excluida depende de si la repetición tiene pesos.

**En una cartera** — la pestaña Riesgo del panel o de la página de un bróker — la posición sale de la repetición, pero su peso no. El peso excluido se suma a la parte en efectivo $c$, lo que significa que se repite como **ganando exactamente cero** durante todo el episodio. Ese cero pertenece al total, no a la posición: la posición no obtiene un rendimiento propio, y la lista de rendimientos por posición solo incluye las posiciones que se repitieron — un cero entre ellas declararía un rendimiento que nadie midió.

Ese tratamiento merece un momento, porque no es neutral. Excluir una posición no hace que la cartera sea más pequeña; hace que esa fracción de la cartera quede plana. En un episodio en el que todo cayó, una posición del 10% mantenida plana es una afirmación implícita de que habría sido lo mejor que poseías. Nadie hace esa afirmación a propósito — el motor la aplica por su cuenta —, por lo que el resultado nombra cada posición que excluyó, con su motivo y su parte del valor.

**En una selección de activos sin pesos** — la [pestaña Correlación](../../../user/assets/correlation.md) de la página de Activos — no hay parte en efectivo que mantenga nada. El activo simplemente se omite: no obtiene ningún rendimiento, no un rendimiento de cero, y las cifras hablan de los activos que se repitieron. Una selección no tiene una composición que sumar, así que esos rendimientos por activo son toda la respuesta.

### 🔎 Qué muestra el resultado {: #what-the-result-shows }

En esas tres pestañas, la repetición dice qué excluyó antes de las cifras que reporta:

- una advertencia **por encima de todo lo demás** cuando más de la mitad del valor de la cartera queda excluido, indicando la parte que el resultado aún cubre: pasado ese punto, el total habla de una minoría de la cartera, con el resto mantenido plano al lado;
- tan pronto como se excluye una posición, un cuadro **por encima del total, donde lo haya, y la tabla** enumera las posiciones excluidas, **agrupadas por motivo**, cada una como una insignia con su icono y su nombre — en una cartera, también con su parte del valor, bajo una línea que indica cuánto del valor cuenta como efectivo a rendimiento cero. El [periodo común](#the-common-period), cuando lo haya, se ofrece en el mismo cuadro;
- la tabla enumera solo las posiciones que se **repitieron**, las peores primero — un clic en el título de una columna ordena por esa columna — cada una en una fila: su **Peso**; su **Rendimiento**, el propio durante el periodo; su **Contribución**, el peso por ese rendimiento, de modo que las contribuciones sumen el total; su **Impacto**, la cantidad ganada o perdida; y su **Efecto**, una barra en una columna que puedes ensanchar arrastrando el borde de su título. La barra muestra la contribución en una cartera y el rendimiento en una selección. Crece desde una línea cero en el centro de la columna — pérdidas a la izquierda en rojo, ganancias a la derecha en verde — en una escala compartida por todas las filas, con la mayor magnitud llegando al borde. Una posición excluida [no tiene rendimiento propio](#what-takes-its-place), así que no recibe fila, no una fila en cero;
- una columna sin nada que mostrar se omite, no se rellena con guiones: una selección de activos no tiene pesos, ni contribuciones, ni dinero, así que su tabla muestra solo el **Rendimiento** y el **Efecto**;
- cuando todas las posiciones quedan excluidas, ninguna cifra: el resultado dice que **no hay nada que repetir** y enumera los motivos.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-replay" alt="¿Qué pasaría si…? en la pestaña Correlación después de Ejecutar repetición: el cuadro de activos excluidos, como insignias agrupadas por motivo, con el botón de periodo común, encima de la tabla de los activos repetidos, con Rendimiento y Efecto" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📆 El periodo común {: #the-common-period }

Cuando los bordes de la ventana son lo que dejó fuera a las posiciones — un inicio tardío, un hueco antes de la ventana, ningún precio reciente al final — el análisis propone la parte de la ventana en la que también están cotizadas. Esa parte comienza el día después de la primera cotización más tardía, dentro de la ventana, de una posición sin precio al inicio, de modo que esta cotización se convierte en su precio inicial; termina en la última cotización más temprana de una posición sin precio reciente al final. Antes de ofrecerse, una segunda lectura de las cotizaciones en esa ventana más corta lo confirma: toda posición que recupera, y toda posición que la ventana ya cubría, debe estar cotizada en ambos extremos, o no se propone nada. Una posición excluida por no tener precios en la ventana, o por no tener tipo de cambio, nunca forma parte de él: ninguna ventana más corta la recuperaría.

En esas pestañas, la propuesta es un botón dentro del cuadro que enumera lo que se excluyó: muestra sus fechas y cuántas posiciones recupera, y con un clic se repite — también cuando no se pudo repetir nada en absoluto en la ventana original. Cuando la repetición se ejecutó sobre una de las crisis integradas — todavía elegida en el menú, en las fechas propias de la crisis — y la propuesta es más corta, se marca como que cubre solo parte de la crisis. Esa es la contrapartida: recuperas las posiciones, pero repites un tramo más corto que el episodio, y lo que el mercado hiciera fuera de ese tramo ya no está en la respuesta. Elegir **Sin preajuste**, un rango rápido o una fecha propia deja de lado la crisis: la siguiente repetición es de un periodo, ya no de la crisis, y no lleva tal marca.

### 🎭 Proxies {: #proxies }

Un proxy permite que la serie de rendimientos de otro activo sustituya a una posición sin el historial. Existe en un solo lugar: la pestaña **Riesgo y escenarios** de la página de detalle de un activo, solo para ese activo, donde el lector puede elegir un proxy para él o excluirlo en su lugar. Una posición con proxy se repite con los rendimientos de su proxy en lugar de quedar excluida, y un proxy sin rendimientos utilizables en la ventana se rechaza como elección inválida, nunca se descarta en silencio. La repetición en las tres pestañas anteriores no ofrece ni proxy ni exclusión manual.

!!! warning "Un proxy es una elección, no un hecho"

    Sustituir una posición por un proxy cambia lo que significa el resultado. Ya no dice qué le habría pasado a esa posición; dice qué habría pasado **si esa posición se hubiera comportado como su sustituto** durante ese episodio. Esa condición es parte de la respuesta, no una nota al pie — un índice amplio usado como proxy de una posición concentrada subestimará cómo se habría movido esa posición, y ninguna parte de la aritmética puede detectar la discrepancia. El resultado registra qué posiciones se usaron con proxy.

---

## 💡 Interpretación {: #interpretation }

La repetición produce un rendimiento compuesto para el episodio y, debajo, un rendimiento para cada posición que repitió. Léelos como una **afirmación condicional**: *esta composición, a través de esas fechas específicas, sin rebalanceo, efectivo plano — y plano con él cada posición que el motor excluyó — y un proxy solo donde se eligió uno*. En una selección de activos no hay composición que capitalizar y nada se mantiene plano: los rendimientos por activo se sostienen por sí solos, para los activos que pudieron repetirse.

Su fortaleza es que cada número en ella ocurrió. La secuencia de rendimientos es la que entregó el mercado — la trayectoria de la caída, la agrupación de días malos, la velocidad de la recuperación son reales, que es exactamente lo que un resumen distribucional no puede reproducir. Su debilidad es la imagen especular: es **un** episodio. Ocurrió una vez, y el próximo estrés no será una copia de él.

Una repetición, por tanto, no es una previsión ni una probabilidad. Es una medición de exposición frente a un evento conocido — útil porque el evento es conocido, y limitada por la misma razón.

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "Un episodio es una muestra"

    Repetir un único tramo histórico dice qué haría ese tramo. No acota lo que podría hacer un tramo futuro, y elegir el peor episodio del registro no convierte el resultado en un peor caso — lo convierte en el peor caso *del registro*.

!!! warning "La composición está fijada a la de hoy"

    Las posiciones abiertas después del episodio, las posiciones cerradas desde entonces y cada cambio de tamaño intermedio están ausentes por construcción. Cuanto más lejos de hoy esté el rango de repetición, más será la cartera repetida una construcción en lugar de un historial.

!!! warning "Los rendimientos se toman tal como se miden"

    La repetición prepara sus series de rendimientos como lo hace el resto del análisis, pero durante la ventana de su episodio y para los activos que repite, cada proxy en lugar de la posición a la que representa. Esas series comparten un calendario, construido como se describe en [Calidad de datos](data-quality.md#alignment-what-missing-data-actually-costs): cada fecha de la ventana en la que al menos uno de esos activos tiene una cotización propia, conservada siempre que todos ellos puedan valorarse, si hace falta a un precio arrastrado desde una fecha anterior. Los huecos, los precios arrastrados y la conversión de divisa llegan a la repetición a través de esas series. Consulta [Calidad de datos](data-quality.md) para lo que el análisis informa sobre las series que utilizó.

---

## 🔗 Relacionado {: #related }

- ⚡ **[Choque hipotético](hypothetical-shock.md)** — la misma pregunta con un escenario elegido en lugar de uno histórico
- 📉 **[Caída máxima](max-drawdown.md)** — la peor caída a lo largo de una trayectoria, y [cuánto tardó la recuperación](max-drawdown.md#recovery-time)
- 📍 **[Caída actual](current-drawdown.md)** — dónde está la cartera hoy, antes de aplicar ningún escenario
- 🧩 **[Contribución al riesgo](risk-contribution.md)** — qué posiciones cargan el riesgo sobre el que actuaría un episodio
- 🧪 **[Calidad de datos](data-quality.md)** — las series sobre las que se ejecutó la repetición
