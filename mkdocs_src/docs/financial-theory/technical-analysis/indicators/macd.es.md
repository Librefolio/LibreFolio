# 📊 MACD — Moving Average Convergence Divergence

El MACD responde a: *"¿Se está acelerando la tendencia o está perdiendo impulso?"* Indica si la *tasa de cambio* de la tendencia es positiva o negativa.

---

## 💡 Significado Financiero

Los traders observan cuando la línea MACD cruza la línea de señal: un cruce alcista sugiere un aumento del impulso, mientras que uno bajista sugiere agotamiento. El MACD **no** indica que el precio esté subiendo (eso ya se puede observar); indica si el impulso está aumentando o disminuyendo.

---

## 🔢 Fórmulas Matemáticas

El sistema MACD produce tres series:

1. **Línea MACD** (la salida del filtro de banda pasante):

 $$
 MACD_t = EMA_{fast}(C_t) - EMA_{slow}(C_t)
 $$

2. **Línea de señal** (MACD suavizado):

 $$
 Signal_t = EMA_{signal}(MACD_t)
 $$

3. **Histograma** (delta de impulso):

 $$
 Histogram_t = MACD_t - Signal_t
 $$

---

## ⚙️ Parámetros

| Parámetro | Clave | Predeterminado | Descripción |
|---|---|---|---|
| Periodo Rápido | `fastPeriod` | 12 | Ventana EMA a corto plazo (días). |
| Periodo Lento | `slowPeriod` | 26 | Ventana EMA a largo plazo (días). |
| Periodo de Señal | `signalPeriod` | 9 | Suavizado EMA aplicado a la línea MACD. |

---

## 🎛️ Equivalente en Procesamiento de Señales — Filtro de Banda Pasante (Derivada Suavizada)

Restar dos filtros de paso bajo con diferentes frecuencias de corte produce un **filtro de banda pasante**. $EMA_{fast} - EMA_{slow}$ cancela la componente de corriente continua (la tendencia a largo plazo compartida por ambos) y suprime el ruido de alta frecuencia (ya filtrado por ambas EMA). Lo que queda es la banda de *frecuencia media*: la oscilación del impulso.

En el dominio $z$:

$$
H_{MACD}(z) = H_{fast}(z) - H_{slow}(z)
 = \frac{\alpha_f}{1-(1-\alpha_f)z^{-1}}
 - \frac{\alpha_s}{1-(1-\alpha_s)z^{-1}}
$$

La línea de señal es otro filtro de paso bajo aplicado a esta salida de banda pasante; actúa como un **filtro adaptado** (matched filter), retrasando ligeramente la señal para reducir los falsos positivos en la detección de cruces.

!!! note "Interpretación de la derivada"

    Para un $\alpha$ pequeño, $EMA_{fast} - EMA_{slow}$ se comporta como una primera
    derivada suavizada $\frac{d}{dt}[\text{tendencia}]$. Cuando el histograma cambia de signo, la
    "velocidad" de la tendencia cambia de dirección.

:material-link: [MACD en Wikipedia](https://en.wikipedia.org/wiki/MACD){ target="_blank" }
