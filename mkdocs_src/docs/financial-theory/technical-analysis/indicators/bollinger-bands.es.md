# 📏 Bandas de Bollinger

Las Bandas de Bollinger miden dinámicamente la **volatilidad** y dibujan una "valla de normalidad" adaptativa alrededor del precio.

---

## 💡 Significado Financiero

Cuando las bandas se ensanchan, el mercado es volátil; cuando se comprimen, una ruptura es inminente. Un precio que toca la banda superior señala exuberancia estadística; tocar la banda inferior señala una caída anormal.

---

## 🔢 Fórmulas Matemáticas

1. **Banda Media** (valor esperado):

 $$
 MB_t = SMA_N(C_t)
 $$

2. **Desviación estándar** de los precios durante la ventana:

 $$
 \sigma_t = \sqrt{\frac{1}{N} \sum_{i=0}^{N-1} (C_{t-i} - MB_t)^2}
 $$

3. **Bandas Superior e Inferior**:

 $$
 Upper_t = MB_t + k \cdot \sigma_t, \qquad
 Lower_t = MB_t - k \cdot \sigma_t
 $$

Con $k = 2$, si los rendimientos estuvieran distribuidos normalmente, el precio se mantendría dentro de las bandas aproximadamente el 95.4% del tiempo. En la práctica, los rendimientos financieros tienen *colas pesadas* (leptocurtosis), por lo que las rupturas son más frecuentes, aunque siguen siendo estadísticamente significativas.

---

## ⚙️ Parámetros

| Parámetro | Clave | Predeterminado | Descripción |
|---|---|---|---|
| Periodo ($N$) | `period` | 20 | Ventana de SMA para el valor esperado. |
| Multiplicador ($k$) | `multiplier` | 2 | Número de desviaciones estándar. |

---

## 🎛️ Equivalente en Procesamiento de Señales — Rastreador de Intervalo de Confianza Adaptativo

La Banda Media es un **filtro de media móvil FIR (Finite Impulse Response)** — el filtro paso bajo más simple con una ventana rectangular de longitud $N$. Las bandas añaden una **envolvente variable en el tiempo** en $\pm k\sigma$, que es esencialmente una estimación móvil de la varianza instantánea de la señal.

En el lenguaje de los filtros adaptativos, se trata de un **rastreador de valor esperado con un intervalo de confianza adaptativo**. Cuando la varianza $\sigma^2$ cae (el *Bollinger Squeeze*), el sistema se encuentra en un estado de baja entropía. En sistemas caóticos como los mercados financieros, los periodos de baja entropía son seguidos fiablemente por explosiones de alta entropía (alta volatilidad), lo que convierte al *Bollinger Squeeze* en una de las configuraciones más vigiladas en el análisis técnico.

!!! info "FIR vs IIR"

    A diferencia de la EMA (IIR, un polo), la SMA es un **filtro FIR** con un retardo
    de grupo completamente plano de $(N-1)/2$ muestras. Sacrifica una banda de
    transición más ancha a cambio de una distorsión de fase nula, lo cual es ideal
    para centrar la envolvente de confianza.

:material-link: [Bandas de Bollinger en Wikipedia](https://en.wikipedia.org/wiki/Bollinger_Bands){ target="_blank" }
