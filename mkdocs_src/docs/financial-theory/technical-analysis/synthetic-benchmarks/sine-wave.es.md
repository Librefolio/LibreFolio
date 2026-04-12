# 🌊 Onda Sinusoidal

Un benchmark de onda sinusoidal representa una **oscilación periódica**. Es el único benchmark que no es de crecimiento en LibreFolio.

---

## 💡 Significado Financiero

Útil para:

- Modelar la **estacionalidad** (por ejemplo, materias primas agrícolas, monedas vinculadas al turismo).
- Proporcionar una referencia visual de **patrones cíclicos** que los traders intuyen en los datos.
- Probar el flujo de renderizado con una forma de onda analítica conocida.

---

## 🔢 Fórmula Matemática

$$
y(t) = A \cdot \sin\!\left(\frac{2\pi t}{T}\right) + y_0 + \text{offset}
$$

donde:

- $A$ es la amplitud (rango pico a pico como % del valor base),
- $T$ es el periodo en días,
- $y_0$ es el valor base (primer punto de datos),
- $\text{offset}$ es un desplazamiento vertical.

---

## ⚙️ Parámetros

| Parámetro | Clave | Predeterminado | Descripción |
|---|---|---|---|
| Amplitud | `amplitude` | 10 | Rango de oscilación pico a pico como % del valor base. |
| Periodo | `period` | 365 | Longitud del ciclo completo en días. |
| Desplazamiento | `offset` | 0 | Desplazamiento vertical como % del valor base. |

---

## 🔍 Interpretación

Si el precio real sigue aproximadamente la referencia sinusoidal, el mercado exhibe un componente cíclico detectable a esa frecuencia. Las desviaciones de la sinusoide sugieren perturbaciones no periódicas o una deriva tendencial. Ajustar el parámetro del periodo permite escanear diferentes longitudes de ciclo, realizando efectivamente una versión manual del análisis espectral.

:material-link: [Onda Sinusoidal en Wikipedia](https://en.wikipedia.org/wiki/Sine_wave){ target="_blank" }
