# 🎲 Modos de simulación

La simulación proyecta una cartera hacia el futuro generando un gran número de futuros posibles y leyendo la distribución de dónde llegan. Es el único lugar de esta sección donde **nada de lo que aparece en la salida ocurrió**: cada trayectoria está fabricada, y la forma en que se fabrica decide qué pueden contener los resultados y qué no.

Hay cinco formas de fabricarlas. El resultado nombra la que usó, con su configuración, en un bloque breve — *Lo que esta simulación asumió* — pero no lo que esa configuración implica. Esta página lo expone.

---

## 🧭 Los cinco modos {: #the-five-modes }

En la pestaña **Risk** del panel y de la página de un bróker, la simulación es la tercera herramienta de **What if…?**, después de la repetición histórica y del choque hipotético. Ofrece cinco modos, cada uno con su supuesto escrito bajo su nombre:

| Modo | Cómo se crean las trayectorias | Supuesto añadido al historial |
|---|---|---|
| **Historial remezclado** — *Recomendado*, el predeterminado | [Bootstrap conjunto por bloques](#block-bootstrap) | Ninguno: tus propios retornos, reordenados en bloques |
| **Mercado tranquilo** | Bootstrap conjunto por bloques con un [régimen](#prescribed-regimes) | Oscilaciones reducidas un 30% durante todo el horizonte |
| **Crisis prolongada** | Bootstrap conjunto por bloques con un régimen | Oscilaciones ×2,5 y un nivel que cae un 20% al año, durante 14 meses |
| **Shock y recuperación** | Bootstrap conjunto por bloques con un régimen | Una caída del 35% durante los dos primeros meses, luego el historial tal cual era |
| **Curva normal (MBG)** — *Avanzado* | [Movimiento browniano geométrico](#the-process) | Retornos gaussianos con deriva, volatilidad y correlación constantes |

Los cuatro primeros extraen retornos reales de la ventana analizada y difieren solo en el régimen que declaran sobre ellos; el último extrae de un modelo ajustado a esa ventana. Un régimen no puede combinarse con la curva normal, y la lista no ofrece tal par.

Junto al modo, el paso pide un **Horizonte (días)** — 365 por defecto, como máximo 3 650 — y un número de **Trayectorias de simulación** — 8 192 por defecto, de 256 a 100 000 — y, solo para la curva normal, una **Estrategia de muestreo**. Una **Semilla aleatoria** fija las extracciones — cuasi-Monte Carlo no necesita ninguna — de modo que las mismas entradas den siempre el mismo resultado. **Simular** la ejecuta. La respuesta da el **Retorno medio terminal**, la **Probabilidad de pérdida** — la proporción de trayectorias que terminan por debajo de donde empezaron — y el rango del percentil 5 al 95 en el último día, sobre un cono que dibuja los percentiles 5, 50 y 95 día a día.

La pestaña **Risk & Scenarios** de la página de detalle de un activo sigue ejecutando solo la curva normal, con muestreo Monte Carlo o cuasi-Monte Carlo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="whatif-simulation" alt="El cuadro de simulación What if…? del panel: el aviso de beta y la advertencia del modelo, los cinco modos con Historial remezclado recomendado, horizonte, trayectorias y semilla, y tras Simular las cifras terminales, el cono y Lo que esta simulación asumió" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🧪 Por qué la simulación sigue en beta {: #why-beta }

Todas las demás partes del análisis de riesgos han salido de beta. Solo el paso de simulación se abre con un aviso: *La simulación sigue en beta. Su resultado depende en gran medida de cuánto historial se solicite en relación con el horizonte: una ventana corta con un horizonte largo puede producir cifras inverosímiles.* Debajo, una segunda advertencia permanece para siempre, porque un modelo sigue siendo un modelo: *Este es el único peldaño que es un modelo en lugar de una medición. Léelo como un rango de posibilidades, no como una previsión.*

El defecto que hay detrás del primer aviso es la relación entre el horizonte $H$, contado en pasos, y las $n$ observaciones de la ventana. Una trayectoria remuestreada de $H$ pasos reutiliza cada observación $H/n$ veces en promedio: a partir de un cuarto de historial, un horizonte de un año es ese cuarto, remezclado y repetido unas cuatro veces, y lo que hizo ese cuarto — un repunte, una racha tranquila, un descenso — se convierte en el año. La curva normal no se libra de ello, porque su deriva y su volatilidad son las de la ventana, arrastradas sin cambios por largo que sea el horizonte. Pedir más historial tampoco lo cura siempre: una posición con un historial corto acorta la ventana compartida para todas ellas (véase [Calidad de datos](data-quality.md#alignment-what-missing-data-actually-costs)). Todavía no se aplica ninguna protección sobre esa relación, y hasta que la haya, el paso permanece en beta. La [incertidumbre de la deriva](#the-drift-is-an-estimate), mostrada junto a cada resultado, es esa relación en acción.

---

## 🔁 Historial remezclado: el bootstrap conjunto por bloques {: #block-bootstrap }

El modo predeterminado no estima nada. Toma los retornos simples de las posiciones durante la ventana analizada, alineados en un calendario compartido — una fila por fecha de observación, una columna por posición — los convierte en retornos logarítmicos $x_{s,i} = \ln(1 + r_{s,i})$, y construye cada futuro a partir de **bloques** de filas consecutivas de esa matriz.

Con $n$ observaciones en la ventana y bloques de $b$ observaciones, una trayectoria de $H$ pasos se ensambla a partir de $\lceil H/b \rceil$ bloques. Cada bloque comienza en una fila extraída uniformemente al azar entre las $n$ filas y toma las $b$ filas desde ahí, dando la vuelta desde la última fila a la primera; los bloques se colocan uno tras otro y se cortan en $H$ pasos. La posición $i$ crece a lo largo de la trayectoria por la suma compuesta de sus retornos logarítmicos extraídos, y la cartera es la composición de hoy mantenida sin rebalanceo, su parte en efectivo $c$ sin generar nada:

$$
G_i(s) = \exp\Big(\sum_{u=1}^{s} x_{u,i}\Big), \qquad R(s) = c + \sum_i w_i \, G_i(s) - 1
$$

donde $w_i$ son los pesos de hoy y $R(s)$ es el retorno de la cartera tras $s$ pasos. De la construcción se derivan tres propiedades:

- **Se extraen filas enteras.** El retorno de cada posición en una fecha viaja con el retorno de todas las demás posiciones en la misma fecha, así que su co-movimiento se arrastra por construcción: no se estima, ni se invierte, ni se comprueba ninguna covarianza, y ninguna puede fallar.
- **Los retornos consecutivos permanecen juntos dentro de un bloque.** La dependencia de corto alcance — una semana turbulenta, una racha de días tranquilos — sobrevive dentro de cada bloque, y solo se rompe en las uniones.
- **Sin un régimen, cada paso ocurrió.** Las colas son las de la propia ventana, no las de una campana de Gauss: un solo paso no puede moverse más que el mayor movimiento registrado en la ventana, y una trayectoria no contiene nada que la ventana no contuviera.

### 📏 Días de calendario y pasos {: #calendar-days-and-steps }

El horizonte se declara en días de calendario, pero el historial es una secuencia de observaciones: una serie cotizada en días bursátiles contiene unas 252 al año, no 365. Un horizonte de $D$ días de calendario se convierte por tanto a la frecuencia observada $f$ de la ventana, el número de observaciones que contiene por año (véase [Anualización observada](observed-annualization.md)):

$$
H = \max\Big(1,\ \operatorname{round}\Big(\frac{D \, f}{365}\Big)\Big)
$$

Los $H$ pasos se simulan y luego se leen de vuelta a un punto por día de calendario: el día $d$ muestra el paso $\lfloor d \, H / D \rfloor$, de modo que un día que cae entre dos pasos repite el anterior — sin cotización, sin movimiento.

### 🧱 La longitud del bloque {: #block-length }

Salvo que se solicite una longitud de bloque, sigue la regla práctica del bloque móvil, proporcional a la raíz cúbica de la muestra:

$$
b = \min\big(n,\ \max(2,\ \operatorname{round}(n^{1/3}))\big)
$$

Eso da 6 observaciones para un año de días bursátiles, y 9 para tres años: lo bastante larga para arrastrar el agrupamiento de volatilidad a lo largo de unos pocos días consecutivos, lo bastante corta para dejar muchos bloques distintos de los que extraer. El resultado informa la longitud que usó, convertida de vuelta a días de calendario, como *Longitud del bloque*.

El análisis también acepta una longitud solicitada, `block_length_days`, de 1 a 5 000 días de calendario, convertida a observaciones a la misma frecuencia $f$. El paso **What if…?** no la ofrece y siempre usa la regla anterior, así que solo una petición enviada directamente al análisis puede fijarla — y solo tal petición puede encontrarse con el rechazo descrito en [Límites](#limits).

---

## 🌦️ Regímenes prescritos {: #prescribed-regimes }

*Mercado tranquilo*, *Crisis prolongada* y *Shock y recuperación* remuestrean exactamente como arriba, y luego transforman cada retorno logarítmico extraído durante el lapso del régimen:

$$
\tilde{x}_{s,i} = \bar{x}_i + k_s \, (x_{s,i} - \bar{x}_i) + \delta_s
$$

donde $\bar{x}_i$ es el retorno logarítmico medio de la posición $i$ durante la ventana, $k_s$ escala las oscilaciones alrededor de él y $\delta_s$ desplaza su nivel. Fuera del lapso, $k_s = 1$ y $\delta_s = 0$: el historial se extrae tal cual era.

| Modo | Lapso | $k_s$ | $\delta_s$, por paso |
|---|---|---|---|
| Mercado tranquilo | todo el horizonte | $0.7$ | $0$ |
| Crisis prolongada | los primeros 426 días de calendario (14 meses) | $2.5$ | $\ln(0.8)/f$ |
| Shock y recuperación | los primeros 61 días de calendario (2 meses) | $1$ | $\ln(0.65)/m$ |

con $f$ la frecuencia observada de la ventana y $m$ el número de pasos que cubre el shock. A lo largo de un año de pasos, el desplazamiento de la crisis se capitaliza hasta un factor de $0.8$ — un nivel un 20% más bajo cada año que el que daría solo el historial — además de oscilaciones dos veces y media más amplias. El shock se capitaliza hasta $0.65$, una caída del 35% sobre el historial, durante su lapso, y siempre íntegramente: en un horizonte más corto que dos meses, toda la caída cae dentro del horizonte. Los lapsos se convierten a pasos del mismo modo que el horizonte.

Un régimen está **declarado, nunca estimado**: estos números son la hipótesis, puesta por escrito, no algo medido a partir de tus datos. Cada paso aplica el mismo $k_s$ y el mismo $\delta_s$ a todas las posiciones, lo que deja las correlaciones entre ellas como las del historial.

Cuando el horizonte es más corto que el lapso de un régimen, el régimen cubre solo el horizonte, y el resultado lo dice — para una crisis en un horizonte de un año: *Declarado para 426 días, aplicado sobre 365: el cono responde a la pregunta más corta.*

---

## 📈 La curva normal: movimiento browniano geométrico {: #the-process }

En el modo *Curva normal (MBG)*, cada trayectoria proviene de un **movimiento browniano geométrico**. Para un único activo, el valor $S_t$ evoluciona como

$$
dS_t = \mu S_t \, dt + \sigma S_t \, dW_t
$$

donde $\mu$ es la deriva, $\sigma$ la volatilidad y $W_t$ un movimiento browniano, que es por donde entra la aleatoriedad. Cada activo simulado parte de 1,0, así que su trayectoria es un factor de crecimiento más que un precio, y avanza un día a la vez hasta alcanzar el horizonte.

Los activos no se simulan por separado ni se suman después. Se ensamblan en un único proceso cuyos shocks están ligados por **una sola matriz de correlación**, de modo que un movimiento en un activo llega acompañado de los movimientos que implica su co-movimiento medido.

Integrar la ecuación da la trayectoria en forma cerrada:

$$
S_t = S_0 \exp\left(\left(\mu - \frac{\sigma^{2}}{2}\right) t + \sigma W_t\right)
$$

Dos propiedades de este modelo hacen la mayor parte del trabajo, y ambas son restricciones:

- **$\mu$ y $\sigma$ son constantes.** Cada una toma un valor y lo mantiene durante todo el horizonte, y lo mismo hace cada entrada de la matriz de correlación. Nada en la simulación cambia su propia volatilidad, ni sus propias correlaciones, mientras se ejecuta.
- **La aleatoriedad entra solo a través de $W_t$**, así que en cualquier intervalo el retorno logarítmico se distribuye normalmente. La forma de los retornos simulados queda fijada antes de extraer la primera trayectoria, y esa forma es la campana de Gauss.

La segunda propiedad es la que hay que llevar a todo lo que sigue: la distribución normal es **más delgada en las colas** que los retornos que los mercados producen realmente, y las colas son para lo que se lee una simulación de riesgo.

---

## 🎲 Dos formas de extraer el mismo modelo {: #sampling-strategies }

La **Estrategia de muestreo** que se ofrece con la curva normal — y solo con ella — es entre **Monte Carlo** y **cuasi-Monte Carlo**. Es una elección sobre cómo se producen los números aleatorios, y sobre nada más. El bootstrap no tiene tal elección: siempre extrae los inicios de sus bloques de un generador pseudoaleatorio con semilla.

!!! warning "Dos entradas no son dos modelos"

    Un menú con dos elementos invita a leer que hay dos modelos disponibles, y que uno de ellos podría convenir más a una cartera que el otro. No hay dos. Ambas entradas usan el mismo movimiento browniano geométrico, con la misma deriva, la misma volatilidad y la misma matriz de correlación, y ambas extraen números **gaussianos** para hacerlo.

    El cuasi-Monte Carlo compra **convergencia**, no realismo. Su secuencia de baja discrepancia cubre el espacio muestral de manera más uniforme que las extracciones pseudoaleatorias, así que la estimación se estabiliza con menos trayectorias. No simula un mercado distinto, y no repara ninguno de los supuestos de esta página.

Lo que sí difiere es lo que cada uno necesita para ser reproducible, y lo que cada uno exige del número de trayectorias:

| | Monte Carlo | Cuasi-Monte Carlo |
|---|---|---|
| Números extraídos de | un generador pseudoaleatorio | una secuencia de baja discrepancia de Sobol |
| Reproducido mediante | una semilla aleatoria | un índice de inicio en la secuencia |
| Número de trayectorias | sin requisito adicional | debe ser una **potencia de dos** |
| Límite adicional | — | posiciones × días de horizonte como máximo 21 201 — véase [Límites](#limits) |

Ambos son totalmente reproducibles: la misma semilla, o el mismo índice de inicio, regenera las mismas trayectorias. Ninguno acepta el parámetro del otro — una semilla y un índice de inicio de Sobol son mutuamente excluyentes. El panel no muestra ningún índice de inicio: siempre entra en la secuencia por 0. La pestaña **Risk & Scenarios** de la página del activo permite fijarlo.

---

## 📐 De dónde vienen los parámetros {: #parameters }

En la curva normal, el modelo lo suministra la medición más que la elección. Los retornos de la ventana analizada se convierten en retornos logarítmicos, y a partir de ellos:

- la **covarianza** es la covarianza muestral, simetrizada y escalada a términos anuales. Cada observación de la ventana lleva el mismo peso — un retorno del primer día cuenta exactamente igual que uno del último;
- las **volatilidades** son las raíces cuadradas de su diagonal, y la **matriz de correlación** es lo que queda una vez dividida esa escala;
- el escalado a términos anuales usa el factor de lapso observado medido descrito en [Anualización observada](observed-annualization.md), no una convención fija.

La deriva es el único parámetro que no es simplemente la media medida:

$$
\mu = \bar{r}_{\log} \cdot f + \frac{\sigma^{2}}{2}
$$

con $\bar{r}_{\log}$ el retorno logarítmico medio por observación, $f$ el factor de anualización y $\sigma^{2}$ la varianza anual. El término de media varianza es la corrección de convexidad de Itô. El parámetro de deriva del proceso es una tasa de crecimiento *simple* esperada, mientras que lo medido es un retorno *logarítmico* medio, y los dos difieren exactamente en la mitad de la varianza; sumarla de vuelta es lo que hace que el crecimiento logarítmico esperado de las trayectorias simuladas sea igual al retorno logarítmico medio de la ventana. Sin ella, las trayectorias crecerían más despacio que los datos de los que provienen.

El efectivo se trata de forma distinta a las posiciones, en todos los modos. Entra en la trayectoria de la cartera con su peso y ahí permanece: la porción de efectivo **gana exactamente cero** durante todo el horizonte y no aporta variación propia.

---

## 🧮 La deriva es una estimación {: #the-drift-is-an-estimate }

Sea cual sea el modo, el centro del cono descansa sobre el crecimiento medio de la ventana — el bootstrap extrae cada fila con la misma probabilidad, la curva normal fija su deriva a partir de la misma media — y esa media es una estimación muestral, con su propio error estándar. El cono no contiene ese error: es la dispersión de las trayectorias *dada* la deriva. Así que junto al resultado, una línea indica cuánto mueve solo ese error a la mediana.

Con $\hat{\sigma}$ la desviación estándar del retorno logarítmico de la cartera por observación sobre las $n$ observaciones de la ventana — el efectivo contado a su peso, sin generar nada — y $H$ el horizonte en pasos, el factor del 95% es

$$
\varphi = \exp\left(z_{0.975} \, \frac{H \, \hat{\sigma}}{\sqrt{n}}\right), \qquad z_{0.975} \approx 1.96
$$

y a la mediana $M$ del último día se le da el rango $\big[(1 + M)/\varphi - 1,\ (1 + M)\,\varphi - 1\big]$: *La deriva proviene de … observaciones: solo eso sitúa esta mediana entre … y ….* Cuando $\varphi$ supera la dispersión del propio cono, $(1 + P_{95})/(1 + P_{5})$, la línea se convierte en una advertencia ámbar: la incertidumbre sobre la deriva sola es entonces más amplia que la banda que dibujó la simulación.

El exponente crece con $H$ y solo se reduce con $\sqrt{n}$: duplicar el horizonte lo duplica, mientras que reducirlo a la mitad exige cuatro veces más historial. Esa es la [relación que hay detrás del aviso de beta](#why-beta), escrita como un número.

---

## 🚧 Límites {: #limits }

Una simulación se rechaza, en lugar de ejecutarse mal, en los casos siguientes. El rechazo es en sí mismo el resultado — la simulación vuelve como no disponible — y el banner de **What if…?** dice por qué:

| Rechazo | Cuándo | En pantalla | Qué cambiar |
|---|---|---|---|
| Muy poco historial | Menos de 30 observaciones en la ventana | *Historial insuficiente para este cálculo.* | Un rango de fechas más largo |
| Bloque más largo que el historial | Una longitud de bloque solicitada abarca más observaciones de las que contiene la ventana | *Parámetros de cálculo no válidos.* | Un bloque más corto, o una ventana más larga |
| Número de trayectorias | Cuasi-Monte Carlo con un número de trayectorias que no es una potencia de dos | *Parámetros de cálculo no válidos.* | Una potencia de dos: 4 096, 8 192, 16 384… |
| Presupuestos de trayectorias | Cualquier modo, cuando trayectorias × (días de horizonte + 1) supera 20 000 000, o trayectorias × días de horizonte × posiciones supera 200 000 000 | *Esta simulación es demasiado grande para ejecutarse. Usa menos trayectorias de simulación o un horizonte más corto.* | Menos trayectorias, o un horizonte más corto |
| Secuencia demasiado grande | Curva normal con cuasi-Monte Carlo, cuando posiciones × días de horizonte supera 21 201 | *Esta simulación de cuasi-Monte Carlo es demasiado grande para ejecutarse. Acorta el horizonte o elige muestreo Monte Carlo.* | Un horizonte más corto, o muestreo Monte Carlo |
| Historial demasiado largo | Historial remezclado o un régimen, cuando la ventana contiene más de 5 000 observaciones, o las observaciones de la ventana × posiciones supera 250 000 | *Esta simulación es demasiado grande para ejecutarse: el periodo contiene demasiado historial. Elige un periodo más corto.* | Un rango de fechas más corto |
| Demasiadas posiciones | Cualquier modo, cuando participan más de 100 posiciones | *Una simulación puede incluir como máximo 100 posiciones, y esta cartera tiene más. Simula un bróker con menos posiciones en su lugar.* | Ninguna configuración: un bróker con menos posiciones, simulado desde su propia página |

Cada límite de tamaño responde `resource_limit` — demasiado grande para ejecutarse, que no es ni un fallo ni un defecto en los parámetros. Sus detalles nombran el límite alcanzado, el valor alcanzado y el techo, y un `remedy` nombra lo que devuelve la petición al alcance. El remedio elige la frase en pantalla, así que cada una dice qué cambiar; un rechazo por tamaño que no nombre ningún remedio, o para el que el banner no tenga frase, se muestra con la general *Este cálculo es demasiado grande para ejecutarse.* El rechazo por longitud de bloque es más bien un rechazo de una configuración, y su código lo dice — parámetros inválidos más que historial insuficiente. Declara la longitud solicitada, las observaciones que abarca y las observaciones que contiene la ventana: el remedio es un bloque más corto, ya que a menudo no hay más historial disponible. El rechazo de Sobol declara el número de dimensiones de la secuencia que necesita — una por posición y por día del horizonte — y el límite. Con el horizonte predeterminado de 365 días, el límite admite 58 posiciones; con el más largo, 3 650 días, cae entre cinco y seis: cinco posiciones necesitan 18 250 dimensiones, seis necesitan 21 900. El número de trayectorias no interviene en ello, y el muestreo Monte Carlo no tiene tal límite.

Los límites de tamaño se imponen antes de lo que parecen. Con las 8 192 trayectorias predeterminadas, cualquier horizonte más allá de 2 440 días supera el primer presupuesto de trayectorias — a 2 441 días, 8 192 × 2 442 = 20 004 864. Con los 365 días y 8 192 trayectorias predeterminados, un alcance de 67 posiciones o más supera el segundo: 8 192 × 365 × 67 = 200 335 360. El presupuesto de historial se estrecha a medida que crece el alcance: la ventana puede contener como máximo 5 000 observaciones — casi veinte años de días bursátiles — y como máximo 250 000 dividido por el número de posiciones, así que el primer límite gobierna hasta 50 posiciones y el segundo más allá de ellas, hasta 2 500 observaciones, unos diez años, con 100. Más allá de 100 posiciones ninguna configuración ayuda: el alcance se rechaza antes de que se remuestree o estime nada, sea cual sea la configuración, y lo que queda es simular un único bróker con menos posiciones. En todos los recuentos, las posiciones son las que la simulación lee, así que una posición [excluida](data-quality.md#exclusions) no cuenta en ninguno de ellos. Una petición que supera varios límites se encuentra con ellos uno a la vez: cada rechazo nombra uno, y el siguiente aparece una vez subsanado el anterior.

---

## 💡 Interpretación {: #interpretation }

Lee la salida como lo que implica el modo, nunca como lo que se espera que ocurra:

- **Nada en ella es evidencia.** Una trayectoria remuestreada reordena lo que contenía la ventana; una trayectoria de modelo es una consecuencia de la deriva, la volatilidad y las correlaciones introducidas. Ninguna lleva información que la ventana no tuviera ya, y un régimen solo añade la hipótesis que declara.
- **Más trayectorias reducen el error de muestreo, no el error de modelo.** Elevar el número de trayectorias hace converger el resultado — hacia la respuesta que da *este modo*. Ningún número de trayectorias añade una caída que la ventana no contuviera, engorda una cola gaussiana ni hace que una correlación fija se mueva.
- **El centro de la distribución es una extrapolación.** Es el crecimiento medio de la ventana arrastrado sin cambios — desplazado, bajo una crisis o un shock, en la cantidad que declara el régimen. Una ventana que subió produce futuros que suben, durante todo el horizonte, y la precisión con que se conoce esa media es la [incertidumbre de la deriva](#the-drift-is-an-estimate).
- **La dispersión es tan amplia como fue la ventana, y no más** — salvo por el factor que declare un régimen. Un periodo de estimación tranquilo suministra oscilaciones tranquilas y un co-movimiento cómodo, y la simulación produce entonces un futuro tranquilo con toda buena fe.

Las cifras que leen lo que realmente ocurrió — [Valor en riesgo](value-at-risk.md), [Peor realización](worst-realization.md), [Caída máxima](max-drawdown.md) — están al menos acotadas por un historial que ocurrió. Una simulación solo está acotada por sus propios supuestos. La curva normal puede mostrar una pérdida peor que cualquier cosa registrada, cuya forma es la del modelo y no la del mercado; una trayectoria remuestreada larga puede encadenar bloques malos hasta formar una caída que el mercado nunca entregó de una sola vez.

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "La ventana es la única fuente"

    Todos los modos leen una sola ventana: el bootstrap reutiliza sus filas, la curva normal ajusta sus medias, y ambos ponderan todas las observaciones por igual, sin peso adicional sobre las recientes. Una ventana sin una caída no contiene ninguna que extraer, y una ventana que subió se proyecta hacia arriba, por largo que sea el horizonte. La ventana sobre la que se calculó cada resultado se publica con él — véase [Calidad de datos](data-quality.md).

!!! warning "La curva normal subestima las colas"

    Los retornos reales de mercado producen movimientos extremos con más frecuencia, y mayores, de lo que permite una distribución normal. El modo *Curva normal (MBG)*, construido sobre incrementos gaussianos, informa por tanto de resultados raros como más raros y más suaves de lo que han sido históricamente, y lo hace con mayor confianza en el extremo lejano de la distribución — la parte que una simulación de riesgo debe describir. [Valor en riesgo](value-at-risk.md) cubre el mismo fallo en su forma paramétrica. El bootstrap conserva las colas de la propia ventana: ni más delgadas, ni más gruesas.

!!! warning "La volatilidad se agrupa solo hasta donde llega un bloque"

    En la curva normal, la volatilidad es un único número para todo el horizonte, así que un mal día no hace que el día siguiente sea más probable que sea malo. El bootstrap conserva el agrupamiento de la ventana dentro de cada bloque, de unos pocos días, y lo pierde en las uniones: una racha turbulenta remuestreada dura más o menos lo que dura un bloque, no lo que duró aquella de la que provino, salvo que una *Crisis prolongada* declare una. Los mercados reales se comportan de otro modo: los periodos turbulentos llegan en rachas, y las crisis persisten. Una peor racha simulada no es el mismo objeto que una crisis histórica y no debería compararse con una.

!!! warning "Las correlaciones nunca se rompen"

    La curva normal aplica una única matriz de correlación a cada futuro; el bootstrap arrastra el co-movimiento de la propia ventana, y los regímenes lo dejan sin cambios por diseño. Ninguno puede producir, salvo que la ventana lo contenga, el evento que más daña a una cartera diversificada: correlaciones que suben hacia uno exactamente cuando los mercados caen, dejando que posiciones que se habían estado compensando mutuamente caigan juntas en su lugar. [Correlación](correlation.md) cubre la versión medida, y cuánto depende de la ventana de la que se tomó.

!!! warning "El efectivo se queda quieto, y no ocurre nada más"

    La porción de efectivo de la cartera ni crece ni varía a lo largo del horizonte, haga lo que haga en la realidad, y la composición se mantiene sin rebalanceo. Los costes, los flujos de efectivo y la inflación también quedan fuera: el resultado los enumera bajo *Fuera del cono*. Cuanto más largo sea el horizonte, más importan estas simplificaciones.

---

## 🔗 Relacionado {: #related }

- 📊 **[Volatilidad](volatility.md)** — la medida de dispersión que la curva normal toma como uno de sus dos parámetros
- 🔗 **[Correlación](correlation.md)** — la estructura de co-movimiento que la simulación mantiene fija en todas las trayectorias
- 📅 **[Anualización observada](observed-annualization.md)** — la frecuencia medida que convierte los días de calendario en pasos, y las estadísticas de la ventana en anuales
- 📉 **[Valor en riesgo](value-at-risk.md)** — la misma pregunta de colas respondida desde retornos observados en lugar de generados
- ⏮️ **[Repetición histórica](historical-replay.md)** — un episodio real aplicado a la cartera actual, donde no se genera nada
- 🧪 **[Calidad de datos](data-quality.md)** — la ventana y el recuento de observaciones a partir de los que se estimaron los parámetros
