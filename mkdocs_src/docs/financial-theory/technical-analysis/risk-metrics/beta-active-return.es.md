# 📐 Beta y rendimiento activo

La beta mide con qué fuerza tiende una cartera a seguir a su índice de referencia, mientras que el rendimiento activo aísla la parte del resultado que el índice de referencia no explica. Ambas son cifras **relativas**: describen una cartera solo en compañía de la serie con la que se comparó, y cambian cuando esa serie cambia.

---

## 🔢 Fórmula {: #formula }

Se calculan cuatro cantidades a partir de las dos series de rendimientos alineadas: la cartera, $p$, y la serie de comparación, $b$.

**La beta** es la covarianza muestral de las dos series dividida por la varianza de la comparación:

$$
\beta = \frac{\mathrm{Cov}(r_p, r_b)}{\mathrm{Var}(r_b)}
$$

Ambos momentos usan los estimadores insesgados $(N-1)$, por lo que se requieren al menos dos observaciones comunes.

**El rendimiento activo** es la diferencia entre los dos rendimientos compuestos a lo largo de toda la ventana:

$$
AR = \left[\prod_{t=1}^{N} (1 + r_{p,t}) - 1\right] - \left[\prod_{t=1}^{N} (1 + r_{b,t}) - 1\right]
$$

**El error de seguimiento** es la dispersión de la diferencia por periodo $a_t = r_{p,t} - r_{b,t}$, anualizada con el factor medido:

$$
TE = \sigma_a \times \sqrt{f}
$$

**El ratio de información** relaciona el promedio de esa diferencia con su dispersión, anualizado sobre la misma base:

$$
IR = \frac{\bar{a}}{\sigma_a} \times \sqrt{f}
$$

El factor $f$ es el mismo factor de anualización observado que se usa en el resto del análisis — se cuenta a partir de los datos en lugar de suponerse. Véase [Anualización observada](observed-annualization.md).

!!! info "Las dos series deben estar alineadas"

    Ambas series se comparan punto por punto, por lo que deben cubrir las mismas observaciones: una comparación se calcula solo cuando las dos series tienen la misma longitud y al menos dos observaciones. La alineación se realiza antes de llegar a las métricas, y por eso un resultado que usó una ventana acortada lo indica mediante su recuento de observaciones en lugar de mediante una comparación desplazada silenciosamente.

---

## 🚫 Cuando la beta no tiene valor {: #when-beta-has-no-value }

La beta no siempre está definida y, cuando no lo está, no se publica ningún número.

**Una serie de comparación con varianza cero no produce beta.** La beta expresa cómo responde la cartera a los movimientos de la serie de comparación; una serie que no se mueve no ofrece nada a lo que responder. Matemáticamente, el denominador se anula, y cualquier valor devuelto en su lugar sería un artefacto de la aritmética en vez de una medición. En su lugar, el resultado informa de la ausencia.

La misma disciplina se aplica al ratio de información: si la diferencia por periodo entre las dos series nunca varía, su dispersión es cero y el ratio se deja sin publicar en lugar de forzarlo.

!!! info "Un valor ausente es un resultado"

    Una beta ausente no es un fallo del cálculo — es lo que los datos respaldan. Leerla como "ninguna relación" sería la conclusión equivocada: significa que la serie de comparación no proporcionó ninguna variación contra la cual pudiera medirse una relación en absoluto.

---

## ➗ El rendimiento activo es una diferencia de rendimientos compuestos {: #active-return-is-a-difference-of-compounded-returns }

El orden de las operaciones importa, y es la fuente de la mala interpretación más común de este número. El rendimiento activo compone cada serie a lo largo de la ventana **primero** y resta **después**. No es la composición de las diferencias por periodo.

Se derivan tres consecuencias.

**No se suma a lo largo del tiempo.** El rendimiento activo de un año no es la suma —ni la composición— de los rendimientos activos de sus meses. Cada cifra pertenece a la ventana sobre la que se calculó, y las ventanas no se pueden encadenar.

**No es el rendimiento de una estrategia.** No es lo que habría ganado un inversor manteniendo la cartera y vendiendo en corto el índice de referencia: esa posición compondría la diferencia y además conllevaría efectos de financiación y reequilibrio que ninguna resta de dos rendimientos compuestos puede representar.

**No se descompone en habilidad.** El rendimiento activo afirma que la cartera terminó la ventana por delante o por detrás de su comparación, en esa cantidad. No atribuye nada: la brecha puede provenir de exposiciones diferentes, de un timing diferente o de una comparación que nunca fue una vara de medir adecuada desde el principio.

---

## 💡 Interpretación {: #interpretation }

**La beta** describe sensibilidad, no calidad. Una beta de $1$ significa que la cartera ha tendido a moverse uno a uno con la serie de comparación; por debajo de $1$ se ha movido menos que la serie, por encima de $1$ más. El signo importa más que cualquier umbral: una beta negativa significa que la cartera ha tendido a moverse en la dirección opuesta.

Vale la pena separar la beta de la correlación, porque se confunden fácilmente. A partir de las definiciones anteriores, $\beta = \rho_{p,b} \times \dfrac{\sigma_p}{\sigma_b}$: la correlación captura solo la *dirección* de la relación, mientras que la beta también lleva el cociente de las dos volatilidades. Una cartera puede seguir de cerca su comparación y aun así tener una beta lejos de $1$ simplemente porque fluctúa más, o menos, que la serie que sigue. Véase [Correlación](correlation.md).

**El rendimiento activo** es la distancia entre las dos líneas de meta, medida a lo largo de la ventana.

**El error de seguimiento** es la consistencia con la que se recorrió esa distancia. Es la volatilidad de la diferencia, por lo que un valor alto indica que la cartera se apartó de su comparación con frecuencia o de forma violenta —en cualquier dirección, ya que es una dispersión y no lleva signo.

**El ratio de información** combina ambos: expresa la diferencia promedio por periodo en unidades de su propia dispersión, anualizada. Un ratio más alto significa que la diferencia fue más regular en relación con cuánto varió; un ratio cercano a cero significa que la diferencia, sea cual sea su signo, es pequeña en comparación con la variación que la rodea. Ningún valor es bueno o malo en sí mismo — la cifra depende de la longitud de la ventana y de la comparación elegida, y el mismo número medido sobre una ventana diferente no es la misma afirmación.

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "Cada cifra aquí hereda su índice de referencia"

    La beta, el rendimiento activo, el error de seguimiento y el ratio de información se miden todos *contra* una serie de comparación. Cambie la serie y todas ellas cambian, sin que nada de la cartera haya cambiado. Una cifra relativa citada sin nombrar contra qué se midió está incompleta. Véase [Selección de índice de referencia](benchmark-selection.md).

!!! warning "La beta ve una línea recta, sobre una sola ventana"

    La beta es la pendiente de una relación lineal estimada durante el periodo observado. Una cartera cuyo comportamiento difiere entre condiciones de calma y de estrés queda resumida por una única pendiente que no describe ninguna de las dos. Y, como se estima, una ventana corta produce una cifra que refleja la secuencia particular que resultó contener por casualidad.

!!! warning "La sensibilidad no es explicación"

    Una beta cercana a $1$ indica que la cartera se movió con la serie de comparación; no dice que la serie impulse a la cartera, ni que el resto sea habilidad. Dos series pueden moverse juntas por una causa común sin ninguna relación entre ellas — la misma precaución que se aplica a la correlación se aplica aquí, con el cociente de volatilidades añadido además.

---

## 🔗 Relacionado {: #related }

- 🎯 **[Selección de índice de referencia](benchmark-selection.md)** — la elección que hereda cada cifra de esta página
- 🔗 **[Correlación](correlation.md)** — dirección de la relación, con el cociente de volatilidades eliminado
- 📊 **[Volatilidad](volatility.md)** — la dispersión que convierte una correlación en una beta
- 📏 **[Anualización observada](observed-annualization.md)** — el factor medido que se usa para anualizar el error de seguimiento y el ratio de información
