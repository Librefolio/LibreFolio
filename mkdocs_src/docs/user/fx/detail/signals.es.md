# 📈 Señales

El panel de Señales permite superponer **indicadores técnicos** en el gráfico de divisas. Estos se calculan en tiempo real a partir de los datos del tipo de cambio y ayudan a identificar tendencias, cambios en el **impulso** y patrones de volatilidad.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="Panel de Señales FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📊 Indicadores Disponibles

### 📉 [EMA — Media Móvil Exponencial](../../../financial-theory/technical-analysis/indicators/ema.md)

Suaviza el ruido de los tipos de cambio diarios para revelar la **tendencia subyacente**. En FX, una EMA que cruza por encima de la línea del tipo suele sugerir un debilitamiento de la moneda base (o fortalecimiento de la moneda cotizada). Período configurable: más corto = más reactivo, más largo = más suave.

### 📊 [MACD — Convergencia/Divergencia de Medias Móviles](../../../financial-theory/technical-analysis/indicators/macd.md)

Mide el **impulso** calculando la diferencia entre una EMA rápida y una lenta. Un MACD positivo significa que la EMA rápida está por encima de la EMA lenta (alcista), negativo significa lo contrario (bajista). Útil en FX para detectar reversiones de tendencia y cambios de impulso.

- 📈 **Línea MACD**: Diferencia entre la EMA rápida y la EMA lenta
- 〰️ **Línea de Señal**: EMA de la propia línea MACD (impulso suavizado)
- 📊 **Histograma**: Diferencia visual entre las líneas MACD y de Señal

### 💪 [RSI — Índice de Fuerza Relativa](../../../financial-theory/technical-analysis/indicators/rsi.md)

Un **oscilador** (0–100) que mide la velocidad y magnitud de los cambios de precio. Valores por encima de 70 sugieren condiciones de sobrecompra, por debajo de 30 sugieren sobreventa.

### 📏 [Bandas de Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md)

Un **canal de volatilidad** alrededor del precio. Las bandas se amplían durante períodos volátiles y se contraen durante períodos tranquilos.

- 〰️ **Banda Central**: Media Móvil Simple (SMA)
- 🔺 **Banda Superior**: SMA + 2 desviaciones estándar
- 🔻 **Banda Inferior**: SMA − 2 desviaciones estándar

---

## 🛠️ Cómo Usar

1. Haz clic en el botón de alternancia **Señales** (📈) en la barra de herramientas del gráfico
2. El panel de señales se abre debajo del gráfico
3. Agrega indicadores desde los menús desplegables categorizados (Indicadores Técnicos, Comparación de Datos, Benchmarks Sintéticos)
4. Los parámetros de cada indicador pueden ajustarse directamente en línea
5. Las señales se representan como superposiciones directamente en el gráfico

---

## 📚 Profundización: Teoría Financiera

Para un tratamiento matemático integral de cada indicador — incluyendo fórmulas, equivalentes en procesamiento de señales e interpretación práctica:

:material-book-open-variant: **[Indicadores Técnicos — Teoría Financiera](../../../financial-theory/technical-analysis/indicators/index.md)**

Esta página de referencia cubre:

- 🔢 Las **fórmulas matemáticas** detrás de cada indicador
- 🎛️ Equivalentes en **procesamiento de señales** (EMA = filtro IIR, SMA = filtro FIR, etc.)
- ⚡ La intuición de **"rápido vs lento"** en términos de frecuencias de corte de filtro
- 📈 **Ejemplos prácticos** de detección de cruces e identificación de tendencias
