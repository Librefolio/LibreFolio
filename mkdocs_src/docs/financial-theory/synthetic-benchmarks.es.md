# 🎯 Referencias Sintéticas

LibreFolio puede superponer **curvas de referencia sintéticas** en cualquier gráfico de divisas. A diferencia de los indicadores técnicos (que se calculan *a partir* de los datos del mercado), las referencias sintéticas se generan matemáticamente y sirven como **líneas de referencia visuales** — ¿y si el precio hubiera seguido esta trayectoria ideal?

Son herramientas muy útiles para:

- Comparar los rendimientos reales **con** una tasa de crecimiento objetivo.
- Visualizar cómo se vería un plan de inversión disciplinado.
- Añadir referencias oscilatorias o cíclicas para el análisis de estacionalidad.

---

## 📈 Crecimiento Lineal { #linear-growth }

### 💡 Significado Financiero

Una referencia de crecimiento lineal representa **interés simple** — el valor aumenta en una cantidad absoluta fija cada período. Es la 'línea objetivo' más simple que **se puede** trazar: si esperas que un activo rinda $r$% anual, la referencia lineal muestra dónde *debería* estar el precio en cualquier momento bajo ese supuesto.

### 🔢 Fórmula Matemática

$$
y(t) = y_0 \cdot (1 + r \cdot t)
$$

donde:

- $y_0$ es el valor inicial (primer punto de datos del gráfico),
- $r$ es la tasa de crecimiento anual (expresada como decimal, por ejemplo 0.07 para 7%),
- $t$ es el tiempo en años desde el inicio.

Esto es equivalente a la fórmula de **interés simple** $A = P(1 + rt)$, donde $t$ se expresa en años usando la [convención de conteo de días](day-count.md) aplicable.

### ⚙️ Parámetros

| Parámetro | Clave | Valor por defecto | Descripción |
|---|---|---|---|
| Tasa Anual | `annualRate` | 5 | Tasa de crecimiento en porcentaje anual. |
| Desplazamiento | `offset` | 0 | Desplazamiento vertical como % del valor base. |

### 🔍 Interpretación

La línea es perfectamente recta en escala lineal. Cualquier punto donde el precio real esté *por encima* de la línea significa que el activo ha superado el objetivo; cualquier punto *por debajo* significa bajo rendimiento. Debido a que el crecimiento es aditivo, la línea se curva hacia abajo en escala logarítmica, lo que facilita distinguirla visualmente del crecimiento compuesto.

:material-link: [Interés Simple en Wikipedia](https://en.wikipedia.org/wiki/Interest#Simple_interest){ target="_blank" }

---

## 📊 Crecimiento Compuesto { #compound-growth }

### 💡 Significado Financiero

Una referencia de crecimiento compuesto representa **interés compuesto** — el valor crece exponencialmente, lo que significa que los rendimientos se reinvierten. Este es el modelo de crecimiento natural para la mayoría de los activos financieros y la suposición estándar en el análisis de flujo de caja descontado (DCF).

### 🔢 Fórmula Matemática

$$
y(t) = y_0 \cdot (1 + r)^t
$$

donde:

- $y_0$ es el valor inicial,
- $r$ es la tasa de crecimiento anual (decimal),
- $t$ es el tiempo en años desde el inicio.

Esto es equivalente a la fórmula de **interés compuesto** $A = P(1 + r)^t$ con capitalización anual. La fórmula generalizada con $n$ períodos de capitalización por año es:

$$
A = P \cdot \left(1 + \frac{r}{n}\right)^{n \cdot t}
$$

El backend de LibreFolio admite las siguientes frecuencias de capitalización:
**Anual** ($n=1$), **Semestral** ($n=2$), **Trimestral** ($n=4$),
**Mensual** ($n=12$), **Diaria** ($n=365$) y **Continua** ($n \to \infty$).

Cuando $n \to \infty$ (capitalización continua):

$$
A = P \cdot e^{r \cdot t}
$$

### 🔄 Cálculo Iterativo (Paso Diario)

En LibreFolio, la curva compuesta se calcula **iterativamente** en lugar de llamar a `pow()` para cada punto de datos. Esto es **a la vez más eficiente e instructivo**:

$$
\text{factorDiario} = (1 + r)^{1/365}
$$

Luego, para cada día sucesivo:

$$
y_{i+1} = y_i \cdot \text{factorDiario}
$$

Esto es matemáticamente equivalente a la forma cerrada $y_0(1+r)^t$ pero reemplaza $N$ operaciones de potencia costosas por $N$ multiplicaciones simples — el mismo principio **que utilizan** los bancos para devengar intereses compuestos diarios.

!!! tip "Regla del 72"
 Un atajo mental rápido: una inversión que crece al $r$% anual se duplicará aproximadamente en $72 / r$ años. Al 7% → ~10.3 años.

### ⚙️ Parámetros

| Parámetro | Clave | Valor por defecto | Descripción |
|---|---|---|---|
| Tasa Anual | `annualRate` | 7 | Tasa de crecimiento compuesto en porcentaje anual. |
| Desplazamiento | `offset` | 0 | Desplazamiento vertical como % del valor base. |

### 🔍 Interpretación

La curva es recta en escala **logarítmica** — esta es la señal reveladora del crecimiento exponencial. Superponer una referencia compuesta en un gráfico de escala logarítmica es la forma más clara de juzgar si un activo está creciendo más rápido o más lento que una tasa objetivo.

:material-link: [Interés Compuesto en Wikipedia](https://en.wikipedia.org/wiki/Compound_interest){ target="_blank" }

---

## 🌊 Onda Senoidal { #sine-wave }

### 💡 Significado Financiero

Una referencia de onda senoidal representa **oscilación periódica**. Es útil para:

- Modelar **estacionalidad** (por ejemplo, materias primas agrícolas, divisas vinculadas al turismo).
- Proporcionar una referencia visual para **patrones cíclicos** que los **operadores** sospechan en los datos.
- Probar el **pipeline de renderizado** con una forma de onda analítica conocida.

### 🔢 Fórmula Matemática

$$
y(t) = A \cdot \sin\!\left(\frac{2\pi t}{T}\right) + y_0 + \text{desplazamiento}
$$

donde:

- $A$ es la amplitud (rango pico a pico como % del valor base),
- $T$ es el período en días,
- $y_0$ es el valor base (primer punto de datos),
- $\text{desplazamiento}$ es un desplazamiento vertical.

### ⚙️ Parámetros

| Parámetro | Clave | Valor por defecto | Descripción |
|---|---|---|---|
| Amplitud | `amplitude` | 10 | Rango de oscilación pico a pico como % del valor base. |
| Período | `period` | 365 | Longitud del ciclo completo en días. |
| Desplazamiento | `offset` | 0 | Desplazamiento vertical como % del valor base. |

### 🔍 Interpretación

Si el precio real sigue aproximadamente la referencia senoidal, el mercado **presenta** un componente cíclico detectable en esa frecuencia. Las desviaciones de la senoide sugieren **choques no periódicos** o deriva de tendencia. Ajustar el parámetro de período permite examinar diferentes longitudes de ciclo, **lo que equivale a realizar** una versión manual del **análisis espectral**.

:material-link: [Onda Senoidal en Wikipedia](https://en.wikipedia.org/wiki/Sine_wave){ target="_blank" }

---
**Notas del Traductor**
