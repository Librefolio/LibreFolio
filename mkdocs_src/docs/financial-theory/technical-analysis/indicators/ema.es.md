# 📉 EMA — Media Móvil Exponencial

La EMA rastrea la **tendencia** suavizando el ruido de los precios diarios, otorgando más peso a las observaciones recientes que a las más antiguas.

---

## 💡 Significado Financiero

Los traders superponen EMAs de diferentes periodos en un gráfico de precios: cuando una EMA de periodo corto cruza *por encima* de una EMA de periodo largo, indica un impulso alcista (un "cruce dorado"); el cruce opuesto indica una desaceleración ("cruce de la muerte").

---

## 🔢 Fórmula Matemática

La EMA se define mediante la recurrencia de primer orden:

$$
EMA_t = \alpha \cdot P_t + (1 - \alpha) \cdot EMA_{t-1}
$$

donde $P_t$ es el precio de cierre en el tiempo $t$ y $\alpha$ es el **coeficiente de suavizado**.

**Relación entre $N$ y $\alpha$.**
Los traders especifican un "periodo" $N$ (en días). El coeficiente se deriva igualando la *edad promedio* de los datos entre una EMA y una Media Móvil Simple (SMA) de la misma ventana:

$$
\text{Age}_{SMA} = \frac{N-1}{2}, \qquad
\text{Age}_{EMA} = \frac{1-\alpha}{\alpha}
$$

Igualándolos:

$$
\alpha = \frac{2}{N+1}
$$

Por ejemplo, $N = 14 \implies \alpha = 2/15 \approx 0.133$.

---

## ⚙️ Parámetros

| Parámetro | Clave | Predeterminado | Descripción |
|---|---|---|---|
| Periodo ($N$) | `period` | 14 | Ventana de observación en días. Mayor $\to$ más suave, más lento. |
| Desplazamiento | `offset` | 0 | Desplazamiento vertical como % del valor base. |

---

## 🎛️ Equivalente en Procesamiento de Señales — Filtro Pasa-Bajos IIR de Primer Orden

La recurrencia $y[n] = \alpha\,x[n] + (1-\alpha)\,y[n-1]$ es precisamente un **filtro pasa-bajos IIR (Infinite Impulse Response) de primer orden**. Su función de transferencia en el dominio $z$ es:

$$
H(z) = \frac{\alpha}{1 - (1-\alpha)\,z^{-1}}
$$

La frecuencia de corte de $-3\,\text{dB}$ (normalizada) es:

$$
\omega_c = \cos^{-1}\!\left(1 - \frac{\alpha^2}{2(1-\alpha)}\right)
$$

Cuando $\alpha$ es pequeño ($N$ grande), la banda de paso se estrecha drásticamente, atenuando todo excepto la componente DC (la tendencia a largo plazo).

!!! tip "Ubicación del polo"

    El polo único se sitúa en $z = 1-\alpha$. Para $N = 200$, $\alpha \approx 0.01$, por lo que
    el polo está en $z = 0.99$ — extremadamente cerca del círculo unitario, lo que explica el
    alto nivel de suavizado y el gran retardo de grupo.

:material-link: [EMA en Wikipedia](https://en.wikipedia.org/wiki/Exponential_smoothing){ target="_blank" }
