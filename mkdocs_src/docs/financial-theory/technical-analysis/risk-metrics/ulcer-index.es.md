# 🩹 Índice de Ulcer

El índice de Ulcer combina cuánto cae una cartera con cuánto tiempo permanece por debajo, por lo que una caída leve que persiste puede obtener una puntuación peor que una fuerte que se recupera rápido.

Todas las demás cifras de caída de las páginas vecinas de esta informan de un **momento** —el peor, o el actual—. Este índice informa de un **periodo de tiempo**: examina la caída en cada observación y pregunta cuánto del historial se pasó por debajo de un pico, y por cuánto.

---

## 🔢 Fórmula {: #formula }

La caída en la observación $t$ es la distancia desde el valor más alto alcanzado hasta el momento:

$$
DD_t = \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau} \leq 0
$$

El índice de Ulcer es la **media cuadrática** de esa serie a lo largo de las $T$ observaciones:

$$
UI = \sqrt{\frac{1}{T} \sum_{t=1}^{T} DD_t^{2}}
$$

Tres propiedades se derivan directamente de esa expresión, antes de añadir cualquier interpretación:

- Es **positivo**. Es una dispersión construida a partir de una raíz cuadrada, y una raíz cuadrada no puede devolver un número negativo. Es el único miembro de la familia de las caídas que no se reporta como un descenso.
- **Cada observación cuenta**, incluidas las que están exactamente en un pico. Esas contribuyen con $0$ a la suma, pero siguen ocupando un lugar en el divisor, que es lo que hace que un largo periodo de calma reduzca la cifra.
- **Elevar al cuadrado no es neutral.** Una caída el doble de profunda contribuye cuatro veces más, por lo que la medida está dominada por los tramos profundos y no por los que simplemente están por debajo del pico.

---

## 📐 El divisor que parece la corrección de Bessel {: #the-divisor }

Este es el detalle que hace tropezar a cualquiera que recalcule la cifra a mano, y merece la pena enunciarlo con precisión porque el error que produce es lo bastante pequeño como para pasar una comprobación informal.

!!! info "La serie lleva un punto más que el historial"

    Una serie de caídas se deriva de un índice de riqueza que comienza en una línea base unitaria, por lo que contiene $T + 1$ puntos: los $T$ observados, más esa línea base. La caída de la línea base es **siempre exactamente cero** — un punto de partida no puede estar por debajo de un pico que aún no ha dejado atrás.

    La implementación de referencia estándar divide la suma de cuadrados entre $n - 1$, donde el contador $n$ recorre toda la serie y, por lo tanto, **incluye** esa línea base. Dado que $n = T + 1$:

    $$
    \frac{1}{n - 1} = \frac{1}{(T + 1) - 1} = \frac{1}{T}
    $$

    El $-1$ cancela el punto fantasma, no aplica una corrección muestral.

!!! warning "Leerlo como una desviación estándar muestral sobreestima el resultado"

    La línea base contribuye con $0$ a la suma de cuadrados y con $+1$ al recuento, y esos dos se cancelan exactamente — por lo que la expresión se reduce a una media genuina sobre las $T$ observaciones reales. Confundir el $n - 1$ con la corrección de Bessel y dividir entre $T - 1$ en su lugar infla la cifra en

    $$
    \sqrt{\frac{T}{T - 1}}
    $$

    Con $T = 750$, eso es **+0.0667%**: demasiado pequeño para parecer incorrecto, y aun así incorrecto. El índice de Ulcer es una media cuadrática, no una desviación estándar muestral, y no tiene ninguna media que estimar.

---

## 🆚 Frente a la caída máxima {: #against-the-maximum-drawdown }

La [Caída máxima](max-drawdown.md) informa del peor momento. El índice de Ulcer informa de cuánto tiempo se pasó bajo el pico, y cuán profundo. Se construyen a partir de la misma serie y clasifican las carteras de forma diferente, que es precisamente la razón para publicar ambos.

| Dos historiales con la **misma** caída máxima | Índice de Ulcer |
|---|---|
| Una caída brusca, recuperada en pocos días | **pequeño** — las observaciones profundas son pocas, y el resto están en un pico |
| Una erosión lenta que permanece bajo el pico durante meses | **grande** — la mayoría de las observaciones están bajo el pico, y cada una cuenta |

La relación entre ambos no es meramente cualitativa. Dado que $DD_t^{2} \leq MDD^{2}$ para cada $t$, la media de los cuadrados no puede superar al mayor de ellos:

$$
UI \leq |MDD|
$$

La igualdad requeriría que la cartera permaneciera en su punto más profundo durante toda la ventana. Por lo tanto, el cociente $UI / |MDD|$ se lee como **cuánto del historial se pareció a lo peor de él** — cerca de $0$ para un único episodio agudo en un historial por lo demás sin problemas, y acercándose a $1$ para una cartera que bajó y se quedó ahí.

---

## 💡 Interpretación {: #interpretation }

Lee la cifra como una profundidad *típica* más que como la peor — ponderada por duración, y expresada en las mismas unidades que las caídas a partir de las que se construye.

- **Cero significa que nunca se estuvo por debajo de un pico.** Una cartera que solo alcanzó nuevos máximos no tiene una serie de caídas digna de mención, y el índice se reduce a $0$. Cualquier historial que contenga una caída produce una cifra estrictamente positiva.
- **Un valor más bajo es mejor**, lo que invierte el hábito de lectura del resto de la familia de las caídas. Aquí un número mayor es una peor experiencia, sin ningún signo menos que lo indique.
- **Lee la secuencia, no la distribución.** Reordenar los rendimientos observados deja [Valor en riesgo](value-at-risk.md) y [VaR condicional](conditional-value-at-risk.md) intactos, pero reconstruye la serie de caídas desde cero y puede mover esta cifra una gran distancia. Pertenece a la mitad dependiente de la trayectoria de la sección, junto con [Caída máxima](max-drawdown.md) y [Caída actual](current-drawdown.md).

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "Una ventana de calma más larga lo reduce"

    El divisor es el recuento de observaciones, por lo que extender un historial con periodos transcurridos en un pico añade ceros al numerador y posiciones al denominador. La cifra baja sin que haya cambiado nada de los episodios malos de la cartera. Dos índices de Ulcer solo son comparables cuando se calcularon sobre ventanas de longitud y frecuencia de observación comparables.

!!! warning "No es la fracción de tiempo pasado bajo el pico"

    Elevar al cuadrado da a los tramos profundos un peso desproporcionado, por lo que el índice no es una estadística de duración disfrazada con un signo de porcentaje. Una cartera que pasó la mitad de la ventana un $2\%$ por debajo de su pico y otra que pasó un octavo de ella un $4\%$ por debajo puntúan igual, y ninguna de las dos cifras te dice qué forma lo produjo.

!!! warning "No contiene fechas"

    La medida resume toda la ventana en un único número y no dice nada sobre **cuándo** ocurrieron los periodos bajo el pico, ni sobre si la cartera está bajo el pico ahora. La [Caída actual](current-drawdown.md) responde a la segunda pregunta y la [Caída máxima](max-drawdown.md) fecha la primera.

---

## 🔗 Relacionados {: #related }

- 📉 **[Caída máxima](max-drawdown.md)** — el peor momento, frente al cual este índice mide todo el periodo
- 📍 **[Caída actual](current-drawdown.md)** — dónde se sitúa la cartera frente a su pico hoy
- 📉 **[Caída en riesgo](drawdown-at-risk.md)** — un cuantil de la misma serie de caídas, en lugar de su media cuadrática
- 🌊 **[Caída en riesgo condicional](conditional-drawdown-at-risk.md)** — la severidad de la cola de caídas más allá de ese cuantil
- 📊 **[Volatilidad](volatility.md)** — dispersión de los rendimientos, que no tiene memoria del pico
- 🧪 **[Calidad de datos](data-quality.md)** — la ventana y el recuento de observaciones sobre los que se construyó la serie
