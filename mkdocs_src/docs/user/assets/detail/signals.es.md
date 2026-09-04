# 📊 Señales

El panel de Señales te permite superponer **indicadores técnicos**, **series de comparación** y **curvas benchmark** sobre el gráfico de precios. Los indicadores se calculan en el servidor mediante la **plataforma de plugins de señales** del backend de LibreFolio a partir del historial de precios almacenado del activo — el navegador solo renderiza los resultados, por lo que el gráfico, los diagnósticos y las instantáneas de AI Export muestran los mismos números.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-signals" alt="Panel de señales del activo" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🧮 Señales disponibles

Las señales se organizan en **tres categorías**, cada una con su propio menú desplegable en la parte superior del panel.

### 📉 Indicadores técnicos — 22 plugins de backend

Los gráficos de activos pueden ejecutar **22 plugins de indicadores**, agrupados por la propiedad de mercado que miden. Las matemáticas de cada indicador se encuentran en la sección de Teoría Financiera — sigue los enlaces a continuación o haz clic en el icono 📖 de cualquier tarjeta de señal para ir directamente a su página de teoría.

| Familia | Indicadores |
|---|---|
| 📈 **Tendencia** (5) | [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) · [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) · [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) · [ADX](../../../financial-theory/technical-analysis/indicators/adx.md) · [Aroon](../../../financial-theory/technical-analysis/indicators/aroon.md) |
| ⚡ **Momentum** (6) | [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) · [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) · [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) · [RSI Estocástico](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) · [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) · [CCI](../../../financial-theory/technical-analysis/indicators/cci.md) |
| 🌊 **Volatilidad** (4) | [Bandas de Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) · [ATR](../../../financial-theory/technical-analysis/indicators/atr.md) · [NATR](../../../financial-theory/technical-analysis/indicators/natr.md) · [Canales de Donchian](../../../financial-theory/technical-analysis/indicators/donchian-channels.md) |
| 📊 **Volumen** (2) | [OBV](../../../financial-theory/technical-analysis/indicators/obv.md) · [MFI](../../../financial-theory/technical-analysis/indicators/mfi.md) |
| ⚠️ **Riesgo** (5) | Drawdown bajo el agua · Rentabilidad móvil · Volatilidad móvil · Ratio de Sharpe móvil · Beta móvil |

Para los conceptos de la familia de riesgo, consulta las páginas de teoría de [Métricas de riesgo](../../../financial-theory/technical-analysis/risk-metrics/index.md) ([Drawdown máximo](../../../financial-theory/technical-analysis/risk-metrics/max-drawdown.md), [Volatilidad](../../../financial-theory/technical-analysis/risk-metrics/volatility.md), [Ratio de Sharpe](../../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md)).

!!! info "No todos los indicadores pueden ejecutarse en todos los activos"

    Los indicadores que necesitan precios **máximos/mínimos** (ADX, Aroon, ATR, NATR, CCI, Canales de Donchian)
    o **volumen** (OBV, MFI) solo están disponibles cuando tu historial de precios
    incluye esos campos — la tarjeta de señal te indica qué campo falta.
    **Beta móvil** además te pide elegir un activo de comparación.

### 💱 Comparación de datos

Superposiciones calculadas en el navegador que normalizan otra serie en el mismo gráfico:

- ↔️ **Comparación de activos** — superpone el rendimiento de otro activo, normalizado a la misma escala (p. ej., una acción frente a su índice benchmark)
- 💱 **Par FX** — superpone el tipo de cambio de un par de divisas configurado

### 📐 Benchmarks sintéticos

**Curvas matemáticas de referencia** calculadas en el navegador, generadas puramente a partir de parámetros — no se necesitan datos de mercado: [Crecimiento lineal](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md), [Crecimiento compuesto](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) y [Onda senoidal](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

---

## 🔍 Cómo encontrar un indicador

El menú desplegable de indicadores es un **árbol plegable agrupado por familia** (tendencia, momentum, volatilidad, volumen, riesgo), con un cuadro de búsqueda en la parte superior:

- ⌨️ Escribe para filtrar entre todas las familias — la búsqueda encuentra coincidencias en nombres, descripciones e incluso en los campos de datos que utiliza un indicador
- 📁 Cada familia muestra una insignia con el recuento y se expande/contrae de forma independiente
- 🖱️ Soporte completo de teclado: las flechas mueven el cursor, `→`/`←` expanden y contraen una familia, `Enter` selecciona

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-signals-tree" alt="Búsqueda agrupada de indicadores en el panel de señales del activo">
</div>

---

## 🎛️ Tarjetas de señal

Cada señal añadida se convierte en una tarjeta que muestra:

- 📖 Un **icono de documentación** que enlaza a la página de Teoría Financiera del indicador
- 🎚️ **Parámetros en línea** (números, menús desplegables, casillas de verificación) — algunas informaciones emergentes contienen fórmulas LaTeX renderizadas con KaTeX
- 🏷️ Una **insignia de datos** con el número de puntos de precio (📈) cargados
- 🗑️ Botón de eliminar; arrastra las tarjetas para reordenar las superposiciones

### ⏳ Mientras el backend calcula

Aparece un pequeño **spinner** en cada tarjeta mientras la solicitud al backend está en curso. El estado transitorio es deliberado: las tarjetas nunca muestran un error rojo de "sin datos" solo porque la respuesta aún no ha llegado.

### 🩺 Diagnósticos por señal

Después de la carga, un icono de color informa de cómo fue el cálculo — pasa el cursor por encima para ver la explicación completa:

- ℹ️ **Aviso** (gris) / ⚠️ **Advertencia** (ámbar) — la señal se calculó, pero con salvedades: huecos en los datos, un período de calentamiento incompleto o un rango que comienza antes que tus datos
- 🔴 **Error** (rojo) — la señal no se pudo calcular: faltan campos OHLCV, no hay suficiente historial para los parámetros elegidos o se produjo un error de cálculo

---

## 🧩 Datos incompletos: segmentos parciales

Los indicadores que toleran huecos (ADX, Aroon, ATR, NATR, CCI, Donchian, MFI, OBV) no fallan ante un historial de precios irregular: el backend selecciona el **segmento contiguo completo** más reciente, calcula el indicador allí e informa del resultado como *parcial* — la información emergente te indica qué segmento se usó y cuántos puntos se excluyeron. Todos los demás indicadores requieren una entrada sin huecos y explican por qué no pueden ejecutarse en lugar de dibujar una línea engañosa.

---

## 📉 Drawdown: interruptor de historial completo

La tarjeta **Drawdown bajo el agua** incluye una casilla **Historial completo** (activada por defecto): la caída se mide con respecto al máximo acumulado de *todo* el historial disponible y luego se recorta a la ventana visible — un pico de hace años sigue contando. Desactívala para obtener una vista más rápida y relativa a la ventana. Las instantáneas de AI Export siempre utilizan el comportamiento de historial completo, independientemente de esta configuración del gráfico.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-signals-drawdown" alt="Tarjeta de señal de drawdown con el interruptor de historial completo">
</div>

---

## 🛠️ Cómo usarlo

1. Haz clic en el **interruptor Señales** (📈) de la barra de herramientas
2. El panel de señales se abre debajo de la barra de herramientas
3. Añade señales desde los tres menús desplegables de categorías (**Indicadores técnicos**, **Comparación de datos**, **Benchmarks sintéticos**)
4. Ajusta los parámetros de cada señal directamente en su tarjeta
5. Las señales se renderizan como superposiciones directamente en el gráfico

---

## 🧠 AI Export

El botón **AI Export** (:material-brain:) de la barra de herramientas de la página ofrece dos tareas de activo:

- **Revisión de posición**
- **Análisis de mercado del activo**

El backend construye la instantánea a partir de la identidad y valoración del activo, el historial de precios normalizado, el contexto de la posición en la cartera y los resultados técnicos del servicio de señales compartido. El navegador no recalcula los indicadores. Las tareas solo aparecen cuando son aplicables al activo y a los datos disponibles; por ejemplo, Revisión de posición requiere una posición abierta. Consulta [AI Export de activos](../../ai-export/asset.md) o la [descripción general de AI Export](../../ai-export/index.md).

---

## 📚 Análisis en profundidad: teoría financiera

Para un tratamiento matemático integral de cada indicador — incluyendo fórmulas, equivalentes de procesamiento de señales e interpretación práctica:

:material-book-open-variant: **[Indicadores técnicos — teoría financiera](../../../financial-theory/technical-analysis/indicators/index.md)**

Esta página de referencia incluye:

- 🔢 Las **fórmulas matemáticas** detrás de cada indicador
- 🎛️ Equivalentes de **procesamiento de señales** (EMA = filtro IIR, SMA = filtro FIR, etc.)
- ⚡ La intuición de **"rápido vs lento"** en términos de frecuencias de corte del filtro
- 📈 **Ejemplos prácticos** de detección de cruces e identificación de tendencias
