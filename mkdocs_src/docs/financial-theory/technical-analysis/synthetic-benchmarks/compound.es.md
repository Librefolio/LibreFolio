# 📊 Crecimiento Compuesto

Un benchmark de crecimiento compuesto representa el **interés compuesto**: el valor crece exponencialmente, lo que significa que los rendimientos se reinvierten.

---

## 💡 Significado Financiero

Este es el modelo de crecimiento natural para la mayoría de los activos financieros y la suposición estándar en el análisis de flujos de caja descontados (DCF). El crecimiento compuesto produce una curva exponencial que se acelera con el tiempo, siendo la base de la creación de riqueza a largo plazo.

---

## 🔢 Fórmula Matemática

$$
y(t) = y_0 \cdot (1 + r)^t
$$

donde:

- $y_0$ es el valor inicial,
- $r$ es la tasa de crecimiento anual (decimal),
- $t$ es el tiempo en años desde el inicio.

Esto es equivalente a la fórmula de **interés compuesto** $A = P(1 + r)^t$ con capitalización anual. La fórmula generalizada con $n$ periodos de capitalización por año es:

$$
A = P \cdot \left(1 + \frac{r}{n}\right)^{n \cdot t}
$$

El backend de LibreFolio soporta las siguientes frecuencias de capitalización: **Anual** ($n=1$), **Semestral** ($n=2$), **Trimestral** ($n=4$), **Mensual** ($n=12$), **Diaria** ($n=365$) y **Continua** ($n \to \infty$).

Cuando $n \to \infty$ (capitalización continua):

$$
A = P \cdot e^{r \cdot t}
$$

---

## 🔄 Computación Iterativa (Pasos Diarios)

En LibreFolio, la curva compuesta se calcula de forma **iterativa** en lugar de llamar a `pow()` para cada punto de datos. Esto es más eficiente e instructivo:

$$
\text{dailyFactor} = (1 + r)^{1/365}
$$

Luego, para cada día sucesivo:

$$
y_{i+1} = y_i \cdot \text{dailyFactor}
$$

Esto es matemáticamente equivalente a la forma cerrada $y_0(1+r)^t$, pero reemplaza $N$ operaciones de potencia costosas por $N$ multiplicaciones simples; el mismo principio que utilizan los bancos para calcular el interés compuesto diario.

!!! tip "Regla del 72"

    Un atajo mental rápido: una inversión que crece al $r$% por año aproximadamente
    se duplicará en $72 / r$ años. Al 7% $\to$ ~10.3 años.

---

## ⚙️ Parámetros

| Parámetro | Clave | Valor predeterminado | Descripción |
|---|---|---|---|
| Tasa Anual | `annualRate` | 7 | Tasa de crecimiento compuesto en porcentaje por año. |
| Desplazamiento | `offset` | 0 | Desplazamiento vertical como % del valor base. |

---

## 🔍 Interpretación

La curva es recta en una escala **logarítmica**; este es el signo inequívoco del crecimiento exponencial. Superponer un benchmark compuesto en un gráfico de escala logarítmica es la forma más clara de juzgar si un activo está creciendo más rápido o más lento que una tasa objetivo.

:material-link: [Interés Compuesto en Wikipedia](https://en.wikipedia.org/wiki/Compound_interest){ target="_blank" }
