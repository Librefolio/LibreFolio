# 🔗 Correlación

La correlación mide **cómo se mueven dos posiciones en relación entre sí**. Es la métrica que decide si una cartera está realmente diversificada o simplemente es larga: poseer muchas cosas no es diversificación si esas cosas suben y bajan juntas.

---

## 🔢 Fórmula {: #formula }

Para dos series de rendimientos $r_i$ y $r_j$ observadas durante los mismos $N$ periodos, el coeficiente de correlación de Pearson es su covarianza normalizada por sus desviaciones estándar:

$$\rho_{i,j} = \frac{\mathrm{Cov}(r_i, r_j)}{\sigma_i \, \sigma_j}$$

con los estimadores muestrales insesgados ($N-1$):

$$\mathrm{Cov}(r_i, r_j) = \frac{1}{N-1} \sum_{t=1}^{N} (r_{i,t} - \bar{r_i})(r_{j,t} - \bar{r_j}) \qquad \sigma_i = \sqrt{\frac{1}{N-1} \sum_{t=1}^{N} (r_{i,t} - \bar{r_i})^2}$$

Dividir por las dos desviaciones estándar es lo que hace que el resultado sea comparable: la covarianza se expresa en unidades de rendimiento al cuadrado y crece con la volatilidad de sus entradas, mientras que $\rho$ es un número puro acotado entre $-1$ y $+1$, sean cuales sean los activos.

!!! info "La correlación se calcula después de la conversión de divisa"

    Los rendimientos entran en el cálculo ya convertidos a la divisa objetivo solicitada para el análisis — la misma regla para una cartera y para un conjunto de activos. Por lo tanto, la cifra describe lo que experimentó un titular que mide en esa divisa, incluidos los movimientos del tipo de cambio — no lo que hizo el instrumento en su divisa de origen. Dos activos cotizados en divisas diferentes se comparan sobre la misma base convertida.

---

## 💡 Interpretación {: #interpretation }

El coeficiente tiene tres puntos de referencia, y solo tres que no requieren convención:

| Valor | Significado |
|---|---|
| $\rho = +1$ | Las dos series se mueven en perfecta sincronía: una es una función lineal positiva exacta de la otra |
| $\rho = 0$ | Ninguna relación **lineal** entre las dos series en la ventana observada |
| $\rho = -1$ | Oposición perfecta: una serie es una función lineal negativa exacta de la otra |

Todo lo que está entre esos polos es una cuestión de grado. Para que la matriz sea legible, LibreFolio lee cada coeficiente en una de cuatro bandas, dondequiera que dibuje una matriz de correlación — en la pestaña Riesgo del panel y de la página de un bróker, y en la [pestaña Correlación](../../../user/assets/correlation.md#correlation) de la página de Activos — en la información emergente de cada celda y en las dos listas de pares junto a la matriz:

| Banda | Rango | Lectura mostrada |
|---|---|---|
| Alta | $\rho > 0.7$ | se mueven juntas |
| Moderada | $0.3 \le \rho \le 0.7$ | se mueven juntas en parte |
| Baja | $-0.3 < \rho < 0.3$ | se mueven de forma independiente |
| Inversa | $\rho \le -0.3$ | se mueven en direcciones opuestas |

Los umbrales son simétricos respecto a cero, por lo que un coeficiente débil se lee como independencia, sea cual sea su signo: $\rho = -0.01$ no es evidencia de que dos activos se compensen entre sí. Las dos listas conservan solo los casos claros — *los más similares* de la banda alta, *los que se compensan* de la banda inversa — y un par con $\rho \ge 0.9$ se marca además como *casi idéntico*: dos instrumentos que son, a efectos prácticos, una única exposición. Una celda sin coeficiente no cae en ninguna banda: una correlación desconocida nunca se lee como baja.

Las bandas son ayudas de lectura, no veredictos. No hay un nivel en el que un par se vuelva «demasiado correlacionado», porque la respuesta depende de cuánto de la cartera representan esas dos posiciones — una pregunta que la matriz de correlación por sí sola no puede responder.

### 🧩 Por qué la matriz responde a «¿Estoy diversificado?» {: #why-the-matrix-answers-am-i-diversified }

El número de posiciones es un recuento; la diversificación es un comportamiento. Diez posiciones que responden todas al mismo impulsor se comportan, en un mal mes, como una sola posición mantenida diez veces. La matriz de correlación es lo que hace visible eso: es el mapa de las relaciones, no un veredicto sobre ellas.

Léala por su estructura más que por sus valores individuales — los grupos de posiciones que se mueven juntas, los pares que realmente no lo hacen, y si un supuesto diversificador se comporta de verdad como tal. La diagonal no aporta información: donde tenga un valor, ese valor es $+1$ por construcción — pero la propia celda diagonal de una serie plana es `undefined`, y una matriz por debajo del umbral de observaciones no contiene ningún valor (véase [Cómo se calcula cada celda](#how-each-cell-is-computed)).

El orden predeterminado de la matriz sirve a esa lectura. Ordena los activos mediante agrupamiento aglomerativo con enlace promedio sobre la distancia

$$d_{ij} = 1 - |\rho_{ij}|$$

de modo que los pares fuertemente vinculados — en la misma dirección o en direcciones opuestas — queden uno al lado del otro, y los grupos se muestren como bloques. Enlace promedio en lugar de enlace simple, porque el enlace simple encadena: dos grupos no relacionados unidos a través de un activo intermedio se dibujarían como un único bloque. Un par sin coeficiente se coloca en la distancia máxima, $d_{ij} = 1$, para que un valor faltante nunca pueda arrastrar dos activos al mismo bloque; los empates se resuelven por posición, de modo que la misma matriz siempre produce el mismo orden.

La correlación responde a *cómo* se mueven juntas las posiciones. No dice nada sobre **cuánto** de la cartera representa cada una, por lo que se lee junto con [Concentración](concentration.md) y [Contribución al riesgo](risk-contribution.md): una correlación fuerte entre dos posiciones marginales importa mucho menos que una moderada entre las dos más grandes.

---

## 🧮 Cómo se calcula cada celda {: #how-each-cell-is-computed }

Cada celda de la matriz se devuelve en uno de tres estados, y cada celda lleva el recuento de observaciones sobre el que se juzgó.

| Estado de la celda | Cuándo | Qué se publica |
|---|---|---|
| `ok` | El calendario compartido contiene suficientes observaciones y ninguna de las series es plana | El coeficiente, recortado a $[-1, +1]$ |
| `insufficient` | El calendario compartido contiene menos observaciones que el mínimo requerido — todas las celdas de la matriz están entonces en este estado | Ningún valor — el recuento se publica sin coeficiente |
| `undefined` | Al menos una de las dos series tiene varianza (numéricamente) cero | Ningún valor — una serie que nunca se mueve no tiene dirección que compartir |

El mínimo se aplica a la **matriz en su conjunto**, no par por par. Dado que todas las series se sitúan en el mismo calendario compartido (véase más abajo), cada par se calcula exactamente en las mismas fechas, por lo que hay un único recuento de observaciones para toda la matriz: o supera el umbral o no lo supera, y cuando no lo supera, todas las celdas se informan como insuficientes. Por lo tanto, un historial corto nunca deja unos pares calculados y otros en blanco — acorta el calendario, y con él la muestra, para todos los pares a la vez. El umbral predeterminado es de 20 observaciones, y es un parámetro ajustable del análisis en lugar de una regla codificada de forma fija.

Cada estado distinto de `ok` que se produce al menos una vez también genera una advertencia en el resultado — `insufficient_pair_history` y `flat_series` respectivamente —, de modo que una matriz total o parcialmente inutilizable lo indica explícitamente en lugar de dejar celdas en blanco a interpretación. A pesar de su nombre, `insufficient_pair_history` siempre concierne a toda la matriz. Una serie plana, en cambio, deja en blanco solo su propia fila y columna y no afecta a ninguna otra correlación.

!!! info "Todas las series comparten un único calendario"

    Antes de calcular cualquier correlación, todas las series en el ámbito se alinean en un único calendario compartido: una fecha entra en el análisis solo si **cada** posición puede valorarse en ella en la divisa objetivo. Por lo tanto, los pares nunca se calculan sobre fechas desajustadas o interpoladas — pero el coste es colectivo, porque una fecha que falla para una posición se descarta para todas ellas. Una posición con un historial corto — una que no puede valorarse antes del inicio solicitado — acorta la ventana para toda la matriz: el calendario comienza en la primera fecha en la que puede valorarse cada posición, y el informe de calidad de datos nombra las posiciones afectadas en lugar de enumerar las fechas omitidas. Un hueco dentro de un historial no elimina ninguna fecha: un precio faltante, como un tipo de cambio faltante, se reemplaza por el último conocido, arrastrado sin límite de antigüedad, y el informe cuenta como puntos arrastrados solo aquellos mantenidos más allá del [umbral de obsolescencia](data-quality.md#staleness-threshold). Una vez que el calendario ha comenzado, solo se descarta una fecha si alguna posición todavía no tiene valor en la divisa objetivo en ella, y esas fechas se enumeran en el informe como incompletas. Véase [Calidad de datos](data-quality.md).

    Cuando la matriz se construye sobre un conjunto de activos elegidos directamente, sin ninguna cartera detrás, un activo con **ninguna serie de precios en absoluto** no es un historial corto sino uno ausente: se excluye del ámbito antes de construir el calendario. El resultado lo lista como excluido — con el motivo `no_price_source` cuando no se le asigna ninguna fuente de precios y nunca se ha registrado ningún precio para él, `missing_price` en caso contrario — genera una advertencia `assets_excluded` y se marca como `partial`. El activo no aparece como una fila plana, y no acorta la ventana para los demás activos. Véase [Exclusiones](data-quality.md#exclusions).

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "La correlación solo ve la parte lineal de una relación"

    $\rho$ mide cómo de bien se describe la relación entre dos series mediante una línea recta. Una dependencia que es real pero curva — por ejemplo, un activo que reacciona solo a los grandes movimientos de otro — puede producir un coeficiente cercano a cero. Una correlación baja significa «no se detectó ningún vínculo lineal en esta ventana», nunca «estas posiciones no están relacionadas».

!!! warning "Un único número para toda la ventana"

    Una correlación es un promedio durante el periodo solicitado. Un par que no estuvo relacionado durante la mayor parte de la ventana y se movió junto en el peor momento produce un promedio tranquilizador. Esta es la asimetría bien documentada de la diversificación: las correlaciones observadas en condiciones de calma no son una promesa sobre el comportamiento bajo estrés, cuando las posiciones que parecían independientes con frecuencia dejan de serlo. La matriz describe la ventana sobre la que se midió, y nada más.

!!! warning "La correlación no es causalidad, ni magnitud"

    Dos activos pueden estar fuertemente correlacionados a través de un impulsor común sin ninguna relación entre sí. Y la correlación no dice nada sobre el tamaño: un par correlacionado en $+1$ donde un activo se mueve violentamente y el otro apenas se mueve comparte dirección, no riesgo. La magnitud pertenece a [Volatilidad](volatility.md), el peso pertenece a [Contribución al riesgo](risk-contribution.md).

---

## 🔗 Relacionado {: #related }

- 🧩 **[Concentración](concentration.md)** — cuánto de la cartera representa realmente cada posición
- ⚖️ **[Contribución al riesgo](risk-contribution.md)** — qué posiciones impulsan el riesgo de la cartera una vez que se combinan la correlación y el peso
- 📊 **[Volatilidad](volatility.md)** — la magnitud que la correlación normaliza deliberadamente
- 🧪 **[Calidad de datos](data-quality.md)** — el calendario compartido, y lo que una fecha faltante le cuesta a toda la matriz
