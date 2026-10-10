# ⚡ Choque hipotético

Un choque hipotético reemplaza el episodio histórico por uno elegido, lo que permite probar un escenario que el historial disponible nunca contuvo.

[Repetición histórica](historical-replay.md) pregunta *¿qué me haría ese episodio?* — los movimientos son reales y solo eliges las fechas. Un choque hipotético pregunta *¿qué pasaría si yo decidiera esto?* — tú eliges los movimientos. Ninguno es un pronóstico, y la diferencia entre ellos está en de dónde vienen los números.

---

## 🔢 Cómo se calcula el choque {: #how-the-shock-is-computed }

Eliges una **dimensión** a lo largo de la cual aplicar el choque — clase de activo, sector o geografía — y asignas un rendimiento a sus grupos: *tecnología cae un 30 %, energía sube un 5 %*. El análisis entonces procede en dos pasos.

Primero, el choque de cada posición se arma a partir de sus exposiciones a esos grupos:

$$
s_i = \sum_b e_{ib} \cdot \text{shock}_b
$$

donde $e_{ib}$ es la exposición de la posición $i$ al grupo $b$. Esto importa más de lo que parece: una posición rara vez está *en* un solo grupo. Un fondo diversificado repartido entre varios sectores recibe una **mezcla ponderada por exposición** de los choques que configuraste, no uno de ellos. La cifra por posición que lees ya es una mezcla.

Segundo, el impacto en la cartera es la suma ponderada de esos choques por posición, y la contribución de cada posición es su propio término:

$$
r_{shock} = \sum_i w_i \, s_i, \qquad \text{contribution}_i = w_i \, s_i
$$

No hay historial de rendimientos en este cálculo. A diferencia de todos los demás análisis de la sección, un choque hipotético no lee una sola observación pasada: necesita los pesos de hoy y las clasificaciones de hoy, y nada más. El resultado informa cero observaciones exactamente por esa razón.

---

## 🧾 Qué ocurre con lo que no configuraste {: #what-you-did-not-configure }

Un escenario nunca está completo. Aplicas un choque a tecnología, y la cartera también mantiene bonos, oro y un fondo en el que nunca pensaste. Lo que el análisis hace con el resto es lo más importante de esta página — y **no es lo mismo para cada dimensión**.

| Dimensión | Qué ocurre con lo que no configuraste |
|---|---|
| **Sector**, **geografía** | No puedes dejarlo sin definir. El escenario se **rechaza** a menos que incluya un grupo `Other`, así que el resto se mueve por una cantidad **que tú elegiste** |
| **Clase de activo** | Un grupo no configurado recibe un choque de **cero**, y el resultado etiqueta esa fila como *Sin configurar → choque cero* |

El rechazo en la primera fila ocurre en la puerta: un escenario de sector o geografía sin un grupo `Other` se rechaza **antes de que se calcule nada**, así que nunca hay un resultado parcial construido sobre un residual no declarado.

!!! warning "Un choque de cero no es neutralidad — es una predicción"

    Dejar una posición sin choque no la elimina del escenario. Afirma que, mientras las acciones caen un 30 %, esa posición **no se mueve**. Eso es una afirmación sobre el mundo y, en una venta masiva generalizada, suele ser generosa.

    Lo que hace defendible el diseño no es que sea cauteloso — es que la afirmación está **registrada por escrito**. El escenario no asume silenciosamente que el resto de la cartera se queda quieto; registra, para cada posición y cada grupo, que se aplicó un cero porque no se configuró nada. La suposición sigue siendo una suposición. Solo que no está oculta.

La asimetría entre las dimensiones vale la pena conocerla en lugar de juzgarla: en sector y geografía estás **obligado** a declarar el residual; en clase de activo, no. En cuál estés trabajando decide qué tienes que comprobar — y si estás aplicando choque por clase de activo, lo que hay que comprobar es si algo volvió como no configurado.

---

## 🖥️ Qué muestra el resultado {: #what-the-result-shows }

Un choque hipotético se ofrece en la pestaña **Riesgo** del Panel y de la página de un bróker, como la segunda herramienta de **¿Y si…?**, y en la pestaña **Riesgo y escenarios** de la página de detalle de un activo. La [pestaña Correlación](../../../user/assets/correlation.md#what-if) de la página de Activos no lo ofrece: una selección no tiene pesos a los que aplicar choque.

En el Panel y en la página de un bróker, un escenario es un clic. Cada escenario con nombre — *Aversión global al riesgo*, *Crac bursátil*, *Crisis bancaria*, *Choque de la Unión Europea* — se ejecuta tan pronto como se elige, según la dimensión para la que está escrito. **Mostrar el choque por grupo** abre sus grupos, cada uno con su choque en porcentaje entero; cambiar uno deja de lado el escenario con nombre, ya que lo que está en pantalla ya no es ese escenario, y **Ejecutar escenario** ejecuta el editado. El resultado dice:

- el total, $r_{shock}$, como *Este escenario movería el ámbito en …*, con la cantidad que representa;
- una tabla con **una fila por grupo del escenario**, no una por posición, de peor a mejor: el choque aplicado al grupo (**Rendimiento**), lo que las posiciones que cayeron en él hicieron al total (**Contribución**: el peso de cada posición multiplicado por la parte de su choque que aportó este grupo, sumado sobre las posiciones, de modo que las filas suman el total), y una barra de esa contribución (**Efecto**), en una escala compartida por todas las filas;
- cuando no todas las posiciones pudieron clasificarse, una nota que da la proporción que sí pudo clasificarse — véase [Cuando falta la clasificación](#when-the-classification-is-missing).

La vista posición por posición, con la regla detrás de cada choque aplicado, es la auditoría de abajo. Aparece en la pestaña **Riesgo y escenarios** del activo, donde la dimensión y el choque de cada grupo también se pueden establecer a mano.

---

## 🔍 Lectura de la auditoría {: #reading-the-audit }

En la pestaña **Riesgo y escenarios** del activo, el impacto viene con una auditoría por grupo, que es donde un escenario deja de ser algo que crees y se convierte en algo que verificas. Cada fila informa:

| Columna | Qué te dice |
|---|---|
| Grupo de exposición | De qué grupo de la dimensión elegida trata esta fila |
| Exposición | Cuánto de la posición está en ese grupo |
| Grupo aplicado | Qué choque de grupo se usó realmente — a menudo, pero no siempre, el mismo |
| Choque | El rendimiento aplicado |
| Contribución | Ese choque escalado por la exposición |
| Regla | **Cómo** se eligió el grupo aplicado |

La última columna es la primera que hay que leer, porque dos posiciones pueden mostrar el mismo choque por razones completamente diferentes y solo la regla las distingue. Existen seis reglas y, en la dimensión de geografía, forman una cascada que se prueba en orden:

| Regla | Cuándo la lleva una fila |
|---|---|
| **Directa** | El propio grupo de la posición es uno que configuraste — el caso ordinario en clase de activo y sector |
| **País** | Geografía, primer paso: configuraste **ese país** en sí |
| **Grupo geográfico** | Geografía, segundo paso: no el país, sino un **grupo que lo contiene**, como un grupo regional |
| **Other** | Geografía, último paso — y el equivalente en sector: nada de lo anterior coincidió, así que se aplicó el grupo residual obligatorio |
| **Metadatos faltantes → Other** | La clasificación de la posición no estaba disponible, así que se trató como `Other` al 100 % |
| **Sin configurar → choque cero** | Solo clase de activo: el grupo nunca se configuró y se aplicó cero |

Leer esa lista hacia abajo te dice cuán lejos de tu intención viajó un choque antes de aterrizar. Una fila *País* es el escenario que escribiste; una fila *Other* es el grupo residual que atrapa algo que no nombraste; una fila *Metadatos faltantes* es un problema de clasificación con la misma ropa.

!!! info "La ambigüedad se rechaza, no se resuelve"

    Un país puede pertenecer a más de un grupo que configuraste — una posición en un país cubierto por dos grupos regionales superpuestos no tiene un único choque correcto. En lugar de elegir uno e informar un número, el análisis **se detiene e informa el conflicto**, nombrando el país y los grupos que colisionaron. Es el mismo principio que el grupo residual, aplicado a un caso que la mayoría de los usuarios nunca anticiparía: cuando el escenario es genuinamente indeterminado, la respuesta no es un valor.

---

## 🏷️ Cuando falta la clasificación {: #when-the-classification-is-missing }

Los choques de sector y geografía dependen de saber a qué está expuesta cada posición. Cuando esos metadatos no están disponibles, la posición no se descarta ni se adivina: se trata como **`Other` al 100 %**, que es por lo que esas dos dimensiones requieren el grupo `Other` en primer lugar. La posición se marca, de modo que el fallback es visible donde ocurrió.

!!! info "La cifra de cobertura en este análisis no trata sobre la densidad de datos"

    En otras partes de la sección, la cobertura describe con qué densidad se muestreó un período — véase [Calidad de datos](data-quality.md). Un choque hipotético no lee ningún historial, así que en este análisis la cifra de cobertura lleva algo diferente: la proporción del ámbito que se clasificó a partir de **metadatos reales** en lugar de recurrir al fallback `Other`. Una cifra baja no significa precios escasos; significa que gran parte del escenario aterrizó en el grupo residual en lugar de en los grupos que configuraste.

---

## 💡 Interpretación {: #interpretation }

El resultado es una afirmación lineal de un solo período: *si estos movimientos ocurrieran, a la vez, en una cartera compuesta como está hoy, el impacto sería este.*

Cada palabra de esa frase tiene peso.

- **Un solo período.** No hay camino. La aritmética da un punto final, no una secuencia, así que nada sobre el trayecto hasta él puede leerse del resultado — ni caída en el camino, ni [tiempo de recuperación](max-drawdown.md#recovery-time), ni orden de los eventos.
- **Lineal.** El impacto es exactamente la suma ponderada de lo que especificaste. No hay efectos de segundo orden, ni retroalimentación, ni contagio de un grupo a otro.
- **Sin correlaciones.** Esta es la diferencia más marcada con el resto de la sección. [Correlación](correlation.md) y [Contribución al riesgo](risk-contribution.md) derivan cómo se mueven juntas las posiciones a partir del historial; un choque hipotético no consulta eso en absoluto. Si configuras tecnología cayendo y bonos planos, hacen exactamente eso, sin importar cómo se hayan comportado juntos en el pasado. Los co-movimientos en el escenario son los que **tú** afirmaste.

La proporción en efectivo no recibe choque: no aporta nada al impacto, así que una cartera que mantiene efectivo ve el resultado escalado solo por la fracción invertida. Para el efectivo esa es una suposición mucho menor que para una posición sin configurar — pero es el mismo mecanismo.

Bien usado, esta es la herramienta para una pregunta que el historial no puede responder, porque el escenario que quieres probar nunca ocurrió. Usado descuidadamente, es una forma de obtener cualquier número: la salida solo puede ser tan disciplinada como los choques introducidos, y nada en la aritmética te dirá que un escenario es inverosímil.

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "No puede contradecirte"

    Todas las demás métricas de esta sección están limitadas por los datos. Esta solo está limitada por tu juicio: calculará fielmente el impacto de un escenario internamente inconsistente — uno donde activos correlacionados se mueven en direcciones opuestas, o donde un choque está muy fuera de cualquier cosa que haya ocurrido — sin ninguna señal de que algo va mal.

!!! warning "No dice nada sobre la probabilidad"

    El impacto está condicionado a que el escenario ocurra exactamente como se especifica. El análisis no le asigna ninguna probabilidad, y un impacto mayor de un escenario más extremo no es evidencia de que el escenario sea más probable. Comparar dos choques compara dos suposiciones, no dos riesgos.

!!! warning "La composición es la de hoy"

    Al igual que [Repetición histórica](historical-replay.md), el choque se aplica a la cartera tal como está ahora. Es una afirmación sobre la exposición actual, no sobre nada que se hubiera mantenido antes.

---

## 🔗 Relacionado {: #related }

- ⏮️ **[Repetición histórica](historical-replay.md)** — la misma estructura con un episodio real en lugar de uno elegido
- 🧩 **[Contribución al riesgo](risk-contribution.md)** — qué posiciones cargan el riesgo, derivado del historial en lugar de afirmado
- 🔗 **[Correlación](correlation.md)** — los co-movimientos que un choque hipotético deliberadamente no usa
- 📉 **[Caída máxima](max-drawdown.md)** — la vista que tiene en cuenta la trayectoria que un choque de un solo período no puede producir
- 🧪 **[Calidad de datos](data-quality.md)** — qué significa cobertura en los análisis que sí leen el historial
