# 📉 Indicadores Técnicos

Esta página documenta los indicadores de análisis técnico disponibles como superposiciones de gráficos en el módulo FX de LibreFolio. Cada indicador se explica desde dos perspectivas complementarias: la interpretación **financiera** que los traders usan a diario, y el equivalente en **procesamiento de señales** que los ingenieros de sistemas de control o con formación en DSP reconocerán al instante.

!!! info "¿Por qué dos perspectivas?"
    Los mercados financieros **no** son sistemas LTI (Lineales e Invariantes en el Tiempo) estacionarios — son ruidosos, caóticos y su contenido espectral cambia con el tiempo. Sin embargo, las herramientas matemáticas que aplicamos para extraer tendencia, momento o volatilidad son *exactamente* los mismos filtros de tiempo discreto que se enseñan en cualquier curso de procesamiento de señales. Si alguna vez has diseñado un pasa-bajos Butterworth o calculado una varianza móvil, ya entiendes estos indicadores — solo con nombres diferentes.

---

## ⚡ La Intuición "Rápido" vs "Lento"

En finanzas, rápido y lento se refieren a la **constante de tiempo** ($\tau$) del filtro subyacente.

| Propiedad | Rápido (N pequeño) | Lento (N grande) |
|---|---|---|
| Frecuencia de corte $f_c$ | Más alta | Más baja |
| Rechazo de ruido | Pobre — deja pasar HF | Bueno — fuerte suavizado |
| Retardo de fase | Pequeño — reacciona rápido | Grande — retraso significativo |
| $N$ típico | 9, 12, 14 | 26, 50, 200 |

---

## 📉 EMA — Media Móvil Exponencial { #ema }

### 💡 Significado Financiero

La EMA rastrea la **tendencia** suavizando el ruido diario del precio, dando más peso a las observaciones recientes que a las antiguas. Los traders superponen EMAs de diferentes períodos en un gráfico de precios: cuando una EMA de período corto cruza *por encima* de una EMA de largo período, señala un impulso alcista (una "cruz dorada"); el cruce opuesto señala una desaceleración ("cruz de la muerte").

### 🔢 Fórmula Matemática

La EMA está definida por la recurrencia de primer orden:

$$
EMA_t = \alpha \cdot P_t + (1 - \alpha) \cdot EMA_{t-1}
$$

donde $P_t$ es el precio de cierre en el tiempo $t$ y $\alpha$ es el **coeficiente de suavizado**.

**Mapeo $N$ → $\alpha$.**
Los traders especifican un "período" $N$ (en días). El coeficiente se deriva igualando la *edad promedio* de los datos entre una EMA y una Media Móvil Simple (SMA) de la misma ventana:

$$
\text{Edad}_{SMA} = \frac{N-1}{2}, \qquad
\text{Edad}_{EMA} = \frac{1-\alpha}{\alpha}
$$

Igualándolas:

$$
\alpha = \frac{2}{N+1}
$$

Por ejemplo, $N = 14 \implies \alpha = 2/15 \approx 0.133$.

### ⚙️ Parámetros

| Parámetro | Clave | Predeterminado | Descripción |
|---|---|---|---|
| Período ($N$) | `period` | 14 | Ventana de retrospectiva en días. Más alto → más suave, más lenta. |
| Desplazamiento | `offset` | 0 | Desplazamiento vertical como % del valor base. |

### 🎛️ Equivalente en Procesamiento de Señales — Filtro Pasa-Bajos IIR de Primer Orden

La recurrencia $y[n] = \alpha\,x[n] + (1-\alpha)\,y[n-1]$ es precisamente un **filtro pasa-bajos IIR (Infinite Impulse Response) de primer orden**. Su función de transferencia en el dominio $z$ es:

$$
H(z) = \frac{\alpha}{1 - (1-\alpha)\,z^{-1}}
$$

La frecuencia de corte $-3\,\text{dB}$ (normalizada) es:

$$
\omega_c = \cos^{-1}\!\left(1 - \frac{\alpha^2}{2(1-\alpha)}\right)
$$

Cuando $\alpha$ es pequeño ($N$ grande) la banda de paso se estrecha dramáticamente, atenuando todo excepto el componente DC (la tendencia a largo plazo).

!!! tip "Ubicación del polo"
    El único polo está en $z = 1-\alpha$. Para $N = 200$, $\alpha \approx 0.01$, entonces el polo está en $z = 0.99$ — extremadamente cerca del círculo unitario, lo que explica el fuerte suavizado y el gran retraso de grupo.

:material-link: [EMA en Wikipedia](https://en.wikipedia.org/wiki/Exponential_smoothing){ target="_blank" }

---

## 📊 MACD — Convergencia/Divergencia de Medias Móviles { #macd }

### 💡 Significado Financiero

El MACD responde: *"¿La tendencia se está acelerando o perdiendo fuerza?"* No te dice que el precio está subiendo (ya puedes ver eso); te dice si la **tasa de cambio** de la tendencia es positiva o negativa. Los traders vigilan el cruce de la línea MACD con la línea de Señal — un cruce alcista sugiere un impulso creciente, uno bajista sugiere agotamiento.

### 🔢 Fórmulas Matemáticas

El sistema MACD produce tres series:

1. **Línea MACD** (la salida pasa-banda):

 $$
 MACD_t = EMA_{fast}(C_t) - EMA_{slow}(C_t)
 $$

2. **Línea de Señal** (MACD suavizado):

 $$
 Signal_t = EMA_{signal}(MACD_t)
 $$

3. **Histograma** (delta de momento):

 $$
 Histogram_t = MACD_t - Signal_t
 $$

### ⚙️ Parámetros

| Parámetro | Clave | Predeterminado | Descripción |
|---|---|---|---|
| Período Rápido | `fastPeriod` | 12 | Ventana EMA a corto plazo (días). |
| Período Lento | `slowPeriod` | 26 | Ventana EMA a largo plazo (días). |
| Período de Señal | `signalPeriod` | 9 | Suavizado EMA aplicado a la línea MACD. |

### 🎛️ Equivalente en Procesamiento de Señales — Filtro Pasa-Banda (Derivada Suavizada)

Restar dos filtros pasa-bajos con diferentes frecuencias de corte produce un **filtro pasa-banda**. $EMA_{fast} - EMA_{slow}$ cancela el componente DC (la tendencia a largo plazo compartida por ambas) y suprime el ruido de alta frecuencia (ya filtrado por ambas EMAs). Lo que queda es la banda de *frecuencias medias*: la oscilación del momento.

En el dominio $z$:

$$
H_{MACD}(z) = H_{fast}(z) - H_{slow}(z)
 = \frac{\alpha_f}{1-(1-\alpha_f)z^{-1}}
 - \frac{\alpha_s}{1-(1-\alpha_s)z^{-1}}
$$

La Línea de Señal es otro pasa-bajos aplicado a esta salida pasa-banda — actúa como un **filtro adaptado**, retrasando ligeramente la señal para reducir detecciones de cruce falsos positivos.

!!! note "Interpretación como derivada"
    Para $\alpha$ pequeño, $EMA_{fast} - EMA_{slow}$ se comporta como una primera derivada suavizada $\frac{d}{dt}[\text{tendencia}]$. Cuando el histograma cambia de signo, la "velocidad" de la tendencia cambia de dirección.

:material-link: [MACD en Wikipedia](https://en.wikipedia.org/wiki/MACD){ target="_blank" }

---

## 💪 RSI — Índice de Fuerza Relativa { #rsi }

### 💡 Significado Financiero

El RSI mide si los compradores o vendedores han dominado *recientemente*. Responde: *"En los últimos $N$ días, ¿cuánto del movimiento total del precio fue al alza vs a la baja?"* El resultado se comprime en un rango de 0–100:

- **RSI > 70** → Sobrecomprado — el resorte está tensado al máximo, un retroceso es estadísticamente probable.
- **RSI < 30** → Sobreventa — el resorte está comprimido, un rebote es probable.

### 🔢 Fórmulas Matemáticas

1. **Descomponer** los cambios diarios en ganancias y pérdidas:

 $$
 U_t = \max(P_t - P_{t-1},\; 0), \qquad
 D_t = \max(P_{t-1} - P_t,\; 0)
 $$

2. **Suavizar** cada componente con una media móvil exponencial (variante SMMA):

 $$
 \overline{U} = SMMA_N(U), \qquad
 \overline{D} = SMMA_N(D)
 $$

3. **Relación de Fuerza** y normalización:

 $$
 RS = \frac{\overline{U}}{\overline{D}}, \qquad
 RSI = 100 - \frac{100}{1 + RS}
 $$

La normalización $100 - 100/(1+RS)$ es una sigmoide monótonamente creciente que mapea $RS \in [0, \infty)$ a $RSI \in [0, 100)$.

### ⚙️ Parámetros

| Parámetro | Clave | Predeterminado | Descripción |
|---|---|---|---|
| Período ($N$) | `period` | 14 | Ventana de retrospectiva para SMMA. |
| Sobrecomprado | `overbought` | 70 | Umbral para la zona de sobrecompra. |
| Sobreventa | `oversold` | 30 | Umbral para la zona de sobreventa. |

### 🎛️ Equivalente en Procesamiento de Señales — Detector de Ciclo de Trabajo / Indicador de Saturación

Imagina dividir la señal de delta de precio $\Delta P[n]$ en sus componentes rectificados de media onda positiva y negativa, y luego aplicar un filtro pasa-bajos a cada uno. El RSI es la **relación de la envolvente positiva a la envolvente total**, reescalado a $[0, 100]$.

En términos de sistemas de control, es un **detector de saturación**: cuando la salida del sistema (precio) ha estado moviéndose en una dirección por demasiado tiempo, el RSI señaliza que el actuador (mercado) está cerca de su riel. Como cualquier oscilador en un bucle de retroalimentación, cuanto más lejos del equilibrio, más fuerte es la fuerza restauradora — de ahí la propiedad de reversión a la media que los traders explotan.

!!! warning "No estacionariedad"
    Los umbrales 70/30 asumen distribuciones de retorno aproximadamente simétricas. En mercados con tendencias fuertes, el RSI puede permanecer por encima de 70 durante semanas — es un indicador *probabilístico*, no determinista.

:material-link: [RSI en Wikipedia](https://en.wikipedia.org/wiki/Relative_strength_index){ target="_blank" }

---

## 📏 Bandas de Bollinger { #bollinger-bands }

### 💡 Significado Financiero

Las Bandas de Bollinger miden dinámicamente la **volatilidad** y dibujan una "cerca de normalidad" adaptativa alrededor del precio. Cuando las bandas son anchas, el mercado es volátil; cuando se aprietan, una ruptura es inminente. Un precio que toca la banda superior señala exuberancia estadística; tocar la banda inferior señala una caída anormal.

### 🔢 Fórmulas Matemáticas

1. **Banda Media** (valor esperado):

 $$
 MB_t = SMA_N(C_t)
 $$

2. **Desviación estándar** de precios sobre la ventana:

 $$
 \sigma_t = \sqrt{\frac{1}{N} \sum_{i=0}^{N-1} (C_{t-i} - MB_t)^2}
 $$

3. **Bandas Superior e Inferior**:

 $$
 Upper_t = MB_t + k \cdot \sigma_t, \qquad
 Lower_t = MB_t - k \cdot \sigma_t
 $$

Con $k = 2$, si los retornos estuvieran distribuidos normalmente, el precio se mantendría dentro de las bandas ~95.4% del tiempo. En la práctica, los retornos financieros tienen colas gruesas (leptocurtosis), por lo que las violaciones son más frecuentes — pero aún así estadísticamente significativas.

### ⚙️ Parámetros

| Parámetro | Clave | Predeterminado | Descripción |
|---|---|---|---|
| Período ($N$) | `period` | 20 | Ventana SMA para el valor esperado. |
| Multiplicador ($k$) | `multiplier` | 2 | Número de desviaciones estándar. |

### 🎛️ Equivalente en Procesamiento de Señales — Rastreador de Intervalo de Confianza Adaptativo

La Banda Media es un filtro de media móvil **FIR (Finite Impulse Response)** — el pasa-bajos más simple con una ventana rectangular de longitud $N$. Las bandas añaden una **envolvente que varía en el tiempo** en $\pm k\sigma$, que es esencialmente una estimación móvil de la varianza instantánea de la señal.

En el lenguaje de filtros adaptativos, esto es un **rastreador de valor esperado con un intervalo de confianza adaptativo**. Cuando la varianza $\sigma^2$ cae (la "contracción de Bollinger" o *squeeze*), el sistema está en un estado de baja entropía. En sistemas caóticos como los mercados financieros, los períodos de baja entropía son seguidos de manera confiable por explosiones de alta entropía (alta volatilidad) — haciendo de la contracción una de las configuraciones más vigiladas en el análisis técnico.

!!! info "FIR vs IIR"
    A diferencia de la EMA (IIR, un polo), la SMA es un filtro **FIR** con un retraso de grupo perfectamente plano de $(N-1)/2$ muestras. Compensa una banda de transición más ancha por distorsión de fase cero — ideal para centrar la envolvente de confianza.

:material-link: [Bandas de Bollinger en Wikipedia](https://en.wikipedia.org/wiki/Bollinger_Bands){ target="_blank" }
