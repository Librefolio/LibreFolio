# 📈 Señales

El panel de Señales permite superponer **indicadores técnicos** en el gráfico de FX. Estos se calculan en tiempo real a partir de los datos del tipo de cambio y ayudan a identificar tendencias, cambios de momentum y patrones de volatilidad.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="Panel de Señales de FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📊 Indicadores Disponibles

### 📉 [EMA — Media Móvil Exponencial](../../../financial-theory/technical-analysis/indicators/ema.md)

Suaviza el ruido de la tasa diaria para revelar la **tendencia subyacente**. En FX, que una EMA cruce por encima de la línea del tipo de cambio a menudo sugiere un debilitamiento de la moneda base (o un fortalecimiento de la moneda de cotización). Período configurable: más corto = más reactivo, más largo = más suave.

### 📊 [MACD — Convergencia/Divergencia de la Media Móvil](../../../financial-theory/technical-analysis/indicators/macd.md)

Mide el **momentum** calculando la diferencia entre una EMA rápida y una lenta. Un MACD positivo significa que la EMA rápida está por encima de la EMA lenta (alcista), un MACD negativo significa lo contrario (bajista). Útil en FX para detectar reversiones de tendencia y cambios de momentum.

- 📈 **Línea MACD**: Diferencia entre la EMA rápida y la lenta
- 〰️ **Línea de Señal**: EMA de la propia línea MACD (momentum suavizado)
- 📊 **Histograma**: Diferencia visual entre las líneas MACD y de Señal

### 💪 [RSI — Índice de Fuerza Relativa](../../../financial-theory/technical-analysis/indicators/rsi.md)

Un **oscilador** (0–100) que mide la velocidad y la magnitud de los cambios de precio. En FX, los valores por encima de 70 pueden sugerir que el par de divisas está sobrecomprado, y por debajo de 30 sugieren que está sobrevendido. Útil para detectar posibles reversiones.

### 📏 [Bandas de Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md)

Una **envolvente de volatilidad** alrededor del precio. Las bandas se ensanchan durante periodos volátiles y se contraen durante periodos de calma. En FX, que una tasa toque la banda superior puede señalar condiciones de sobrecompra, mientras que tocar la banda inferior puede señalar sobreventa.

- 〰️ **Banda Media**: Media Móvil Simple (SMA)
- 🔺 **Banda Superior**: SMA + 2 desviaciones estándar
- 🔻 **Banda Inferior**: SMA − 2 desviaciones estándar

---

## 🛠️ Cómo Usarlo

1. Haga clic en el **interruptor** de Señales (📈) en la barra de herramientas del gráfico
2. El panel de señales se abre debajo del gráfico
3. Añada indicadores desde los menús desplegables categorizados (Indicadores Técnicos, Comparación de Datos, benchmarks Sintéticos)
4. Los parámetros de cada indicador se pueden ajustar en línea
5. Las señales se renderizan como capas superpuestas directamente en el gráfico

---

## 📚 Profundización: Teoría Financiera

Para un tratamiento matemático exhaustivo de cada indicador — incluyendo fórmulas, equivalentes de procesamiento de señales e interpretación práctica:

:material-book-open-variant: **[Indicadores Técnicos — Teoría Financiera](../../../financial-theory/technical-analysis/indicators/index.md)**

Esta página de referencia cubre:

- 🔢 Las **fórmulas matemáticas** detrás de cada indicador
- 🎛️ Equivalentes de **procesamiento de señales** (EMA = filtro IIR, SMA = filtro FIR, etc.)
- ⚡ La intuición de **"rápido vs lento"** en términos de frecuencias de corte de filtro
- 📈 **Ejemplos prácticos** de detección de cruces e identificación de tendencias
