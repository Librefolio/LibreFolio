# 📊 Ratio de Sortino

El ratio de Sortino es una modificación del ratio de Sharpe que solo penaliza la **volatilidad a la baja**. Reconoce que a los inversores les preocupan principalmente las pérdidas, no las sorpresas al alza.

---

## 🔢 Fórmula {: #formula }

$$
So = \frac{R_p - R_f}{\sigma_d}
$$

donde:

- $R_p$ = rendimiento de la cartera (anualizado)
- $R_f$ = tasa libre de riesgo (o rendimiento mínimo aceptable)
- $\sigma_d$ = **desviación a la baja** (anualizada)

!!! info "Cómo entra el umbral en el cálculo"

    El umbral —el rendimiento mínimo aceptable— se proporciona como una tasa **anual efectiva** y se convierte en una tasa **efectiva por periodo** mediante la misma conversión que utiliza el ratio de Sharpe:

    $$
    r_{period} = (1 + r_{annual})^{1/f} - 1
    $$

    donde $f$ es el mismo factor de anualización que escala la desviación a la baja, medido a partir de los datos observados — véase [Anualización observada](observed-annualization.md). Ese umbral por periodo se resta luego a cada rendimiento del periodo, tanto en los rendimientos en exceso como en la desviación a la baja que figura a continuación, de modo que una única definición de "aceptable" gobierna por igual el numerador y el denominador.

### 📐 Desviación a la baja {: #downside-deviation }

$$
\sigma_d = \sqrt{\frac{1}{N} \sum_{i=1}^{N} \min(R_i - R_f, 0)^2}
$$

Solo los rendimientos **por debajo** del umbral contribuyen a la desviación a la baja. Los rendimientos por encima del umbral contribuyen cero.

---

## ⚖️ Dos convenciones de desviación a la baja {: #two-downside-conventions }

Dos cantidades diferentes se denominan comúnmente "desviación a la baja", y difieren en dos aspectos: uno insignificante y otro decisivo.

| | Punto de referencia | Divisor |
|---|---|---|
| **Convención del umbral** (usada aquí) | Un umbral **elegido** — el rendimiento mínimo aceptable | $N$, cada observación |
| **Convención de la media** | La **media muestral de la propia serie** | $N - 1$, las observaciones menos uno |

**El divisor es la diferencia insignificante.** Cuando el umbral coincide con la media muestral, los dos resultados difieren solo por el factor $\sqrt{N/(N-1)}$ — a lo largo de un año de observaciones diarias, aproximadamente dos partes por mil. Es una elección contable, no un cambio de significado.

**El punto de referencia es el decisivo**, y la brecha que abre no tiene límite superior. Los siguientes valores se derivan directamente de las dos definiciones aplicadas a series construidas — son aritmética que un lector puede reproducir, no la salida de una ejecución de LibreFolio:

| Serie de 250 observaciones | Convención de la media | Convención del umbral (umbral $= 0$) |
|---|---|---|
| **Pierde exactamente 0,5 % cada día** | **0,000000** | **0,005000** |
| Alterna $+1\%$ y $-1\%$ en torno a cero | 0,007085 | 0,007071 |
| Gana exactamente 0,5 % cada día | 0,000000 | 0,000000 |

La primera fila es todo el argumento. Una cartera que pierde medio punto porcentual **cada día durante un año** nunca se desvía de su propia media, porque su media *es* esa pérdida diaria — así que la convención de la media mide su riesgo a la baja como exactamente cero. La convención del umbral, cuando se le pregunta a qué distancia cayó la serie por debajo de cero, responde que cayó por debajo en cada uno de los 250 días.

!!! warning "No son dos estimaciones de la misma cantidad"

    Las dos convenciones responden a preguntas diferentes. Medir contra la media de la propia serie pregunta *cuán inconsistente soy respecto a mí mismo*; medir contra un umbral elegido pregunta *cuánto caigo por debajo de lo que pedí*. Solo la segunda puede informar que perder de forma constante es un riesgo; la primera, por construcción, no puede ver una pérdida que nunca varía.

    Ninguna es incorrecta en general. La convención de la media pertenece de forma natural a la optimización de carteras, donde la cantidad que se minimiza es la dispersión en torno a la media que logre la asignación. La pregunta de la que trata esta página es la otra: el umbral es algo que el inversor declara de antemano, y el ratio informa del resultado frente a él.

LibreFolio utiliza la **convención del umbral con el divisor $N$** — la fórmula indicada arriba. El umbral es un parámetro explícito del análisis y es cero a menos que se establezca en otro valor, así que, por defecto, la pregunta planteada es *cuánto cayó la cartera por debajo del punto de equilibrio y si su resultado estuvo por encima de él*.

---

## 💡 Interpretación {: #interpretation }

| Ratio de Sortino | Qué significa el valor |
|---|---|
| $< 0$ | El rendimiento quedó por debajo del umbral: el numerador es negativo sea cual sea la desviación a la baja resultante |
| $0 - 1.0$ | Menos de una unidad de rendimiento en exceso por unidad de desviación a la baja |
| $1.0 - 2.0$ | De una a dos unidades de rendimiento en exceso por unidad de desviación a la baja |
| $> 2.0$ | Más de dos unidades de rendimiento en exceso por unidad de desviación a la baja — poco común a lo largo de periodos largos, y mucho menos infrecuente en periodos cortos y favorables |

!!! warning "Lea la escala antes de leer el número"

    Estos rangos se expresan en unidades de desviación **a la baja**, por lo que un Sortino y un Sharpe con el mismo valor numérico no son la misma afirmación sobre una cartera. Y como con cualquier ratio de esta familia, el valor depende de la ventana y de la clase de activo en que se midió: un tramo corto favorable y un ciclo de mercado completo no producen cifras comparables, incluso para la misma cartera. La tabla dice qué *es* el número, no si es bueno.

!!! example "Ejemplo numérico"

    Rendimiento de la cartera: 12 %, Tasa libre de riesgo: 3 %, Desviación a la baja: 10 %

    $$So = \frac{0.12 - 0.03}{0.10} = 0.90$$

    Compárelo con Sharpe (si σ total = 15 %): $S = 0.60$. El Sortino es más alto porque se excluye la volatilidad al alza.

---

## 📊 Sharpe vs Sortino {: #sharpe-vs-sortino }

| Aspecto | Sharpe | Sortino |
|--------|--------|---------|
| **Medida de riesgo** | Desviación estándar total | Solo desviación a la baja |
| **¿Penaliza el alza?** | Sí ❌ | No ✅ |
| **Mejor para** | Distribuciones de rendimiento simétricas | Rendimientos asimétricos / sesgados |
| **Ejemplo** | Índice de mercado amplio | Estrategias con opciones, carteras concentradas |

### 🔑 Cuándo preferir Sortino {: #when-to-prefer-sortino }

- **Distribuciones sesgadas**: Estrategias que tienen ganancias grandes ocasionales pero pérdidas controladas
- **Carteras basadas en opciones**: Pagos intrínsecamente asimétricos
- **Acciones de crecimiento**: Tienden a tener distribuciones de rendimiento con sesgo positivo
- **Cualquier inversor** que se preocupe más por el riesgo a la baja que por el riesgo total

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "Sesgo de muestra pequeña"

    La desviación a la baja requiere suficientes puntos de datos por debajo del umbral. Con pocos rendimientos negativos (p. ej., periodos cortos de mercado alcista), la estimación se vuelve poco fiable y el ratio de Sortino puede ser engañosamente alto.

---

## 🔗 Relacionado {: #related }

- 📐 **[Ratio de Sharpe](sharpe-ratio.md)** — Variante de volatilidad total
- 📊 **[Volatilidad](volatility.md)** — Entender la desviación estándar
- 📈 **[Caída máxima](max-drawdown.md)** — Otra métrica centrada en el riesgo a la baja
