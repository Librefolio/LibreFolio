# 🎯 Concentración

La concentración mide hasta qué punto el peso de una cartera se agrupa en unas pocas posiciones, lo que ofrece una lectura que un simple recuento de posiciones no puede proporcionar.

Aquí se trata como **dos** cifras en lugar de una, y eso es deliberado: la primera cuenta cómo se reparte el dinero, la segunda comprueba si repartirlo logró algo. Leída por sí sola, la primera llamará diversificada a una cartera cuando no lo es.

---

## 🔢 La cifra basada en el recuento {: #the-count-based-figure }

El punto de partida es el índice de Herfindahl — la suma de las ponderaciones al cuadrado:

$$
H = \sum_i w_i^{2}
$$

Elevar al cuadrado es lo que la convierte en una medida de concentración: una ponderación del 50% contribuye veinticinco veces más que una del 10%, así que las posiciones grandes dominan el total de una forma que un simple recuento nunca refleja.

El recíproco lo convierte en algo legible, el **número de activos efectivos**:

$$
N_{eff} = \frac{1}{H}
$$

Responde: *¿cuántas posiciones de igual tamaño producirían la concentración que realmente tengo?* Diez posiciones del 10% cada una dan $H = 10 \times 0.1^2 = 0.1$ y, por tanto, exactamente 10. Una posición del 50% junto a diez del 5% da bastante menos que once — el número cae hacia el recuento de posiciones que realmente importan.

La cifra es intuitiva precisamente porque se expresa en la escala de un recuento aunque no se comporte en absoluto como uno. Esa lectura depende de que las ponderaciones sumen uno: en cuanto se mantiene algo de efectivo, no lo hacen, y el resultado puede superar directamente el número de posiciones — [Dónde se sitúa el efectivo](#where-cash-sits) cubre qué ocurre entonces.

---

## 🙈 Lo que un recuento no puede ver {: #what-a-count-cannot-see }

El número de activos efectivos lee **solo las ponderaciones**. Nunca mira cómo se comportan las posiciones, y este es su punto ciego, y lo es por completo.

Consideremos tres carteras, cada una con diez activos equiponderados, que difieren solo en cuán correlacionados están esos activos. Junto a la cifra basada en el recuento, la tabla muestra el **ratio de diversificación**, que compara la volatilidad que habrían tenido las posiciones por separado con la volatilidad de la cartera que forman:

$$
DR = \frac{\sum_i w_i \sigma_i}{\sigma_p}
$$

| Correlación entre posiciones | Número de activos efectivos | Ratio de diversificación |
|---|---|---|
| 0 | **10,00** | 3,15 |
| 0,5 | **10,00** | 1,35 |
| 0,95 | **10,00** | **1,02** |

La cifra basada en el recuento no se mueve ni una centésima. El ratio de diversificación se desploma.

!!! warning "Diez posiciones que se mueven juntas no son diez apuestas"

    Con una correlación de 0,95, la cartera se comporta casi exactamente como una sola posición: el ratio de 1,02 dice que repartir el dinero entre diez activos aportó una reducción del 2% en volatilidad frente a mantener uno de ellos. La cifra basada en el recuento reporta 10,00 en los tres casos, y un lector que solo mirara ese número concluiría que las tres carteras estaban igual de bien diversificadas.

    Por eso las dos cifras pertenecen a la misma página y deben leerse de un vistazo. Una mide cómo se **reparte** el dinero; la otra, si el reparto **funcionó**.

Los valores medidos anteriores son consistentes con el caso idealizado: para $n$ posiciones equiponderadas de igual volatilidad y correlación por pares constante $\rho$, el ratio es $\sqrt{n / (1 + (n-1)\rho)}$, que da aproximadamente 3,16, 1,35 y 1,02 para las tres filas.

---

## 🏦 La misma palabra en dos granularidades {: #two-granularities }

Una cartera puede reportar dos cifras de concentración diferentes en el mismo momento, y ninguna es incorrecta. Lo que cambia es **qué cuenta como una posición**.

Supongamos que el mismo instrumento se mantiene en dos brókers, con un 6% y un 4% de la cartera.

- Si se cuenta **por posición**, contribuye con $0.06^2 + 0.04^2 = 0.0052$.
- Si se cuentan **por instrumento**, las posiciones primero se suman para dar un 10%, lo que contribuye con $0.10^2 = 0.0100$.

La diferencia es exactamente $2 w_1 w_2$, que siempre es positiva. Así que el enfoque por instrumento **siempre** reporta la concentración más alta — y, como la cifra de activos efectivos es el recíproco, el enfoque por posición **siempre** reporta el número más cómodo.

!!! info "Dos preguntas, no dos respuestas"

    *¿Cuán concentrado estoy por posición?* y *¿cuán concentrado estoy por instrumento?* son preguntas diferentes, y una cartera repartida entre brókers las responde de forma distinta por construcción. El enfoque por instrumento es el que coincide con la exposición de mercado: el mismo fondo mantenido en dos cuentas es una sola apuesta, sin importar en cuántas filas aparezca.

    Cuando dos cifras no coinciden, lo que hay que establecer es qué granularidad contó cada una — no cuál es la correcta.

Una cifra calculada sobre posiciones es verificable en este punto: los informes de cartera y del bróker de LibreFolio construyen su índice de Herfindahl a partir de ponderaciones por posición, y una posición allí se identifica por **ambos**: su instrumento y su bróker.

---

## 🪙 Dónde se sitúa el efectivo {: #where-cash-sits }

El efectivo debe tratarse de alguna manera, y la elección cambia el resultado. En los informes de cartera y del bróker, la regla se declara en el propio código: las ponderaciones son el valor de la posición sobre el **NAV total**, y el efectivo está *incluido en el denominador pero no es en sí mismo un término del índice*.

Vale la pena detallar la consecuencia, porque va en una dirección que la mayoría de los lectores no adivinaría. El efectivo diluye cada ponderación sin aportar un cuadrado propio, así que mantener más efectivo **baja** el índice y, por lo tanto, **sube** el recuento de activos efectivos. Una cartera que mantiene la mitad de su valor en efectivo parece mejor diversificada que las mismas posiciones sin él.

Bajo esa regla, el efecto es mayor de lo que sugiere la idea de que *parece mejor*. Escribamos $s$ para la proporción invertida de la cartera, de modo que $s = 1 - \text{cash fraction}$ y las ponderaciones sumen $s$ en lugar de uno. Añadir efectivo a un conjunto fijo de posiciones multiplica el índice por $s^{2}$ y el recuento de activos efectivos por $1/s^{2}$; para $n$ posiciones equiponderadas, eso es exactamente

$$
N_{eff} = \frac{n}{s^{2}}
$$

Dos posiciones sin efectivo dan 2,00. Las mismas dos posiciones dan 8,00 con la mitad del valor en efectivo, aproximadamente **11,4** con algo más de la mitad en efectivo, y 200 con el noventa por ciento en efectivo. Por lo tanto, una cartera de dos posiciones puede reportar una cifra muchas veces mayor que dos, y no hay límite superior en absoluto: a medida que el efectivo se acerca a toda la cartera, el recuento diverge.

Las ponderaciones desiguales tiran en la otra dirección, así que una cartera desequilibrada que mantiene poco efectivo todavía puede reportar menos activos efectivos que posiciones tiene. No obstante, la inflación en sí siempre está presente — y la lectura habitual, un valor entre uno y el número de posiciones, describe solo el caso sin efectivo.

Eso es defendible — el efectivo es genuinamente una posición no concentrada, y genuinamente reduce la exposición a cualquier instrumento individual — pero es una suposición, no un hecho neutral, y leer una cifra de concentración sin conocerla invita a la conclusión equivocada. Dos carteras con posiciones idénticas y saldos de efectivo diferentes no están igualmente diversificadas en su capital invertido.

---

## 💡 Interpretación {: #interpretation }

Lea las dos cifras como un par, en este orden:

1. **Activos efectivos frente al número real de posiciones.** La dirección de la diferencia determina su significado: **por debajo** del recuento, las ponderaciones están desequilibradas y unas pocas posiciones sostienen la cartera sin importar cuántas filas tenga; **por encima**, el exceso es efectivo, y no dice nada sobre cómo se reparten las ponderaciones.
2. **Ratio de diversificación.** Un valor cercano a 1 significa que las posiciones se mueven como una sola, y que el reparto aportó poco. Cuanto más por encima de 1, más se compensan unas posiciones con otras.

La segunda cifra es la que puede contradecir a la primera, y es la contradicción la que aporta la información. Una cartera puede estar perfectamente equilibrada por ponderación y no estar diversificada en esencia — es el resultado ordinario de mantener varios fondos que siguen mercados solapados.

Ninguna de las dos cifras dice nada sobre **qué** posiciones impulsan el riesgo. Esa atribución es [Contribución al riesgo](risk-contribution.md), y el comportamiento por pares que subyace a ambas es [Correlación](correlation.md).

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "Las ponderaciones por sí solas pueden tranquilizar"

    La cifra basada en el recuento es una función de las ponderaciones y nada más. No puede distinguir una cartera genuinamente variada de un conjunto de posiciones casi idénticas, y no es evidencia de diversificación por sí sola.

!!! warning "Tener en cuenta la correlación no significa mirar hacia adelante"

    El ratio de diversificación depende de volatilidades y correlaciones estimadas sobre una ventana, y estas cambian — normalmente en la dirección menos conveniente, ya que las correlaciones tienden a subir en mercados de estrés. Un ratio cómodo medido durante un período tranquilo es una medición de ese período. Consulte [Calidad de datos](data-quality.md) para conocer la ventana sobre la que se calculó cada resultado.

!!! warning "La concentración no es automáticamente un defecto"

    Ninguna de las dos cifras es una puntuación. Una cartera deliberadamente concentrada es una elección, y un recuento alto de activos efectivos no es un logro en sí mismo — como muestra la tabla anterior, puede ser reportado por una cartera que mantiene diez versiones de la misma apuesta.

---

## 🔗 Relacionado {: #related }

- 🔗 **[Correlación](correlation.md)** — el comportamiento por pares que resume el ratio de diversificación
- 🧩 **[Contribución al riesgo](risk-contribution.md)** — qué posiciones soportan el riesgo, una vez combinadas las ponderaciones y los movimientos conjuntos
- 📊 **[Volatilidad](volatility.md)** — la magnitud con la que se compara el ratio de diversificación
- 🧪 **[Calidad de datos](data-quality.md)** — la ventana sobre la que se estimaron las volatilidades y correlaciones
