# 📊 Análisis Técnico

El análisis técnico estudia los **patrones de precios y la dinámica del mercado** para identificar tendencias, momentum y volatilidad. A diferencia del análisis fundamental (que evalúa el valor intrínseco de una empresa), el análisis técnico se centra puramente en los datos históricos de precio y volumen.

---

## 📖 Contenido

### 📉 [Indicadores](indicators/index.md)

Superposiciones de gráficos que extraen información de tendencia, momentum o volatilidad a partir de los datos de precios. LibreFolio implementa cuatro indicadores principales, cada uno explicado desde una perspectiva **financiera** y de **procesamiento de señales**:

- **[EMA](indicators/ema.md)** — Media Móvil Exponencial (seguimiento de tendencia)
- **[MACD](indicators/macd.md)** — Convergencia/Divergencia de la Media Móvil (momentum)
- **[RSI](indicators/rsi.md)** — Índice de Fuerza Relativa (sobrecompra/sobreventa)
- **[Bandas de Bollinger](indicators/bollinger-bands.md)** — Envolvente de volatilidad adaptativa

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
