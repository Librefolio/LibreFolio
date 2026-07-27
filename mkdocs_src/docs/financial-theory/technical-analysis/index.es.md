# 📊 Análisis Técnico

El análisis técnico estudia los **patrones de precios y la dinámica del mercado** para identificar tendencias, momentum y volatilidad. A diferencia del análisis fundamental (que evalúa el valor intrínseco de una empresa), el análisis técnico se centra puramente en los datos históricos de precio y volumen.

---

## 📖 Contenido

### 📉 [Indicadores](indicators/index.md)

Superposiciones de gráficos que extraen información de tendencia, momentum, volatilidad o volumen a partir de los datos del mercado. LibreFolio implementa **17 indicadores backend**, cada uno explicado desde una perspectiva **financiera** y de **procesamiento de señales**:

- 📈 **[Tendencia](indicators/trend.md)** — EMA, SMA, KAMA, ADX, Aroon
- ⚡ **[Momentum](indicators/momentum.md)** — RSI, MACD, ROC, Stochastic RSI, PPO, CCI
- 🌊 **[Volatilidad](indicators/volatility.md)** — Bandas de Bollinger, ATR, NATR, Canales de Donchian
- 📊 **[Volumen](indicators/volume.md)** — OBV, MFI

### 🎯 [Benchmarks Sintéticos](synthetic-benchmarks/index.md)

Benchmarks matemáticos superpuestos en los gráficos para su comparación. A diferencia de los indicadores (calculados *a partir de* los datos del mercado), los benchmarks se generan puramente a partir de parámetros:

- **[Crecimiento Lineal](synthetic-benchmarks/linear.md)** — Modelo de interés simple
- **[Crecimiento Compuesto](synthetic-benchmarks/compound.md)** — Modelo de interés compuesto
- **[Onda Senoidal](synthetic-benchmarks/sine-wave.md)** — Referencia cíclica para estacionalidad

---

## ⚡ La Intuición de "Rápido" vs "Lento"

En finanzas, *rápido* y *lento* se refieren a la **constante de tiempo** ($\tau$) del filtro subyacente.

| Propiedad | Rápido ($N$ pequeño) | Lento ($N$ grande) |
|---|---|---|
| Frecuencia de corte $f_c$ | Más alta | Más baja |
| Rechazo de ruido | Pobre — deja pasar HF | Bueno — suavizado fuerte |
| Desfase | Pequeño — reacciona rápido | Grande — retraso significativo |
| $N$ típico | 9, 12, 14 | 26, 50, 200 |

---

## 🔗 Secciones Relacionadas

- 🏦 **[Instrumentos](../instruments/index.md)** — Los activos que estos indicadores analizan
- 📐 **[Fundamentos](../fundamentals/index.md)** — Rendimientos, convenciones de conteo de días
- 📈 **[Teoría de Carteras](../portfolio-theory/index.md)** — Métricas de riesgo y asignación
