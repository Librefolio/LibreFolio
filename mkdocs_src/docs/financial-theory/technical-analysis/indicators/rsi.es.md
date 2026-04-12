# 💪 RSI — Índice de Fuerza Relativa

El RSI mide si los compradores o los vendedores han dominado *recientemente*. Responde a: *"En los últimos $N$ días, ¿qué proporción del movimiento total del precio fue ascendente frente a descendente?"*

---

## 💡 Significado Financiero

El resultado se comprime en un rango de 0 a 100:

- **RSI > 70** → Sobrecompra — el muelle está estirado, un retroceso es estadísticamente probable.
- **RSI < 30** → Sobreventa — el muelle está comprimido, un rebote es probable.

---

## 🔢 Fórmulas Matemáticas

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

3. Relación de **Fuerza Relativa** (Relative Strength) y normalización:

 $$
 RS = \frac{\overline{U}}{\overline{D}}, \qquad
 RSI = 100 - \frac{100}{1 + RS}
 $$

La normalización $100 - 100/(1+RS)$ es una sigmoide monótonamente creciente que mapea $RS \in [0, \infty)$ a $RSI \in [0, 100)$.

---

## ⚙️ Parámetros

| Parámetro | Clave | Por defecto | Descripción |
|---|---|---|---|
| Periodo ($N$) | `period` | 14 | Ventana de retroceso para SMMA. |
| Sobrecompra | `overbought` | 70 | Umbral para la zona de sobrecompra. |
| Sobreventa | `oversold` | 30 | Umbral para la zona de sobreventa. |

---

## 🎛️ Equivalente en Procesamiento de Señales — Ciclo de Trabajo / Indicador de Saturación

Imagine dividir la señal de variación de precio $\Delta P[n]$ en sus componentes rectificados de media onda positiva y negativa, y luego aplicar un filtro de paso bajo a cada una. El RSI es la **relación entre la envolvente positiva y la envolvente total**, reescalada a $[0, 100]$.

En términos de sistemas de control, es un **detector de saturación**: cuando la salida del sistema (precio) se ha movido en una dirección durante demasiado tiempo, el RSI indica que el actuador (mercado) ha alcanzado su límite de saturación. Como cualquier oscilador en un bucle de retroalimentación, cuanto más lejos esté del equilibrio, más fuerte será la fuerza restauradora; lo que explica la propiedad de reversión a la media que explotan los traders.

!!! warning "Non-stationarity"

    Los umbrales 70/30 asumen distribuciones de retorno aproximadamente simétricas. En mercados con tendencias fuertes, el RSI puede permanecer por encima de 70 durante semanas; es un indicador *probabilístico*, no determinista.

:material-link: [RSI en Wikipedia](https://en.wikipedia.org/wiki/Relative_strength_index){ target="_blank" }
