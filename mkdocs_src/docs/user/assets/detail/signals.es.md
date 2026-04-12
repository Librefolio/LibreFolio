# 📊 Señales

El panel de Señales le permite superponer **indicadores técnicos** en el gráfico de precios. Estos se calculan en tiempo real a partir de los datos de precios del activo y ayudan a identificar tendencias, cambios de impulso y patrones de volatilidad.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-signals" alt="Asset Signals Panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📊 Indicadores Disponibles

### 📉 [EMA — Media Móvil Exponencial](../../../financial-theory/technical-analysis/indicators/ema.md)

Suaviza el ruido del precio diario para revelar la **tendencia subyacente**. Cuando una EMA se sitúa por encima de la línea de precio, a menudo señala una tendencia bajista. Período configurable: más corto = más reactivo, más largo = más suave.

### 📊 [MACD — Convergencia/Divergencia de Medias Móviles](../../../financial-theory/technical-analysis/indicators/macd.md)

Mide el **impulso** (momentum) calculando la diferencia entre una EMA rápida y una lenta. Útil para detectar reversiones de tendencia y cambios de impulso.

- 📈 **Línea MACD**: Diferencia entre la EMA rápida y la lenta
- 〰️ **Línea de Señal**: EMA de la propia línea MACD (impulso suavizado)
- 📊 **Histograma**: Diferencia visual entre las líneas MACD y de Señal

### 💪 [RSI — Índice de Fuerza Relativa](../../../financial-theory/technical-analysis/indicators/rsi.md)

Un **oscilador** (0–100) que mide la velocidad y la magnitud de los cambios de precio. Valores superiores a 70 pueden sugerir que el activo está sobrecomprado, valores inferiores a 30 sugieren que está sobrevendido.

### 📏 [Bandas de Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md)

Una **envoltura de volatilidad** alrededor del precio. Las bandas se ensanchan durante períodos volátiles y se contraen durante períodos de calma.

- 〰️ **Banda Media**: Media Móvil Simple (SMA)
- 🔺 **Banda Superior**: SMA + 2 desviaciones estándar
- 🔻 **Banda Inferior**: SMA − 2 desviaciones estándar

### 🔀 Comparación de Activos

Compare el rendimiento del activo actual frente a **otro activo**. El precio del activo de comparación se superpone en el gráfico, normalizado a la misma escala. Útil para el análisis de rendimiento relativo (por ejemplo, comparar una acción frente a su benchmark).

---

## 🛠️ Cómo usarlo

1. Haga clic en el interruptor de **Señales** (📈) en la barra de herramientas
2. El panel de señales se abre debajo de la barra de herramientas
3. Agregue indicadores desde los menús desplegables categorizados
4. Los parámetros de cada indicador se pueden ajustar en línea
5. Las señales se renderizan como superposiciones directamente en el gráfico

---

## 📚 Análisis Profundo: Teoría Financiera

Para un tratamiento matemático exhaustivo de cada indicador —incluyendo fórmulas, equivalentes de procesamiento de señales e interpretación práctica:

:material-book-open-variant: **[Indicadores Técnicos — Teoría Financiera](../../../financial-theory/technical-analysis/indicators/index.md)**

Esta página de referencia cubre:

- 🔢 Las **fórmulas matemáticas** detrás de cada indicador
- 🎛️ Equivalentes de **procesamiento de señales** (EMA = filtro IIR, SMA = filtro FIR, etc.)
- ⚡ La intuición de **"rápido vs lento"** en términos de frecuencias de corte de filtro
- 📈 **Ejemplos prácticos** de detección de cruces e identificación de tendencias
