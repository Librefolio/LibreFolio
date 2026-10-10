# 📊 Señales

Las señales son líneas dibujadas sobre el gráfico de precios: **indicadores técnicos** que LibreFolio calcula a partir de los precios almacenados, **otro activo o un par de divisas** con el que comparar, y **curvas de referencia** como un crecimiento constante. Úsalas para leer tendencia, momentum, volatilidad y riesgo de un vistazo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals" alt="Panel de señales del activo" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Añadir una señal

1. Abre el panel **Señales** encima del gráfico.
2. Elige una señal de uno de sus tres menús: **Indicadores técnicos**, **Comparación de datos** o **Benchmarks sintéticos**. En el menú de indicadores, escribe para buscar por nombre, descripción o los datos que usa un indicador.
3. Configura sus parámetros en la tarjeta que aparece; el gráfico se actualiza.
4. Arrastra una tarjeta por su tirador (flechas en un teléfono) para cambiar el orden, o elimínala con 🗑️.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals-tree" alt="Búsqueda agrupada de indicadores en el panel de señales del activo">
</div>

Cada línea de una tarjeta, y cada zona de indicadores como el RSI, tiene su propio color y estilo de línea. Tus señales se recuerdan para este activo, en este navegador.

---

## 📉 Indicadores técnicos {: #technical-indicators }

**22 indicadores**, agrupados por lo que miden. Cada nombre enlaza a su página de teoría; el **?** de una tarjeta abre la misma página.

### 📈 Tendencia

- [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) — media simple de los precios de cierre
- [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) — media que pondera más los precios recientes
- [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) — media que se adapta al ruido del mercado
- [ADX](../../../financial-theory/technical-analysis/indicators/adx.md) — fuerza de la tendencia, con +DI y −DI para su dirección
- [Aroon](../../../financial-theory/technical-analysis/indicators/aroon.md) — cuán recientes son los últimos máximos y mínimos

### ⚡ Momentum

- [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) — presión de compra y de venta, con zonas de sobrecompra y sobreventa
- [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) — momentum entre dos medias móviles, con una línea de señal y un histograma
- [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) — el mismo momentum, en porcentaje
- [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) — velocidad del cambio de precio
- [RSI estocástico](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) — dónde se sitúa el RSI dentro de su rango reciente
- [CCI](../../../financial-theory/technical-analysis/indicators/cci.md) — distancia respecto al precio medio

### 🌊 Volatilidad

- [Bandas de Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) — una banda alrededor de una media móvil que se ensancha con la volatilidad
- [ATR](../../../financial-theory/technical-analysis/indicators/atr.md) — volatilidad en unidades de precio
- [NATR](../../../financial-theory/technical-analysis/indicators/natr.md) — volatilidad en porcentaje del precio
- [Canales de Donchian](../../../financial-theory/technical-analysis/indicators/donchian-channels.md) — el máximo más alto y el mínimo más bajo del periodo

### 📊 Volumen

- [OBV](../../../financial-theory/technical-analysis/indicators/obv.md) — presión del volumen detrás de los movimientos de precio
- [MFI](../../../financial-theory/technical-analysis/indicators/mfi.md) — momentum ponderado por volumen

### ⚠️ Riesgo

- [Caída bajo el pico](../../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md) — cuánto está el precio por debajo de su pico acumulado ([histórico completo](#drawdown-full-history))
- [Rentabilidad móvil](../../../financial-theory/fundamentals/returns.md#rolling-return-sessions) — rentabilidad solo de precio sobre una ventana móvil
- [Volatilidad móvil](../../../financial-theory/technical-analysis/risk-metrics/volatility.md) — volatilidad anualizada sobre una ventana móvil
- [Ratio de Sharpe móvil](../../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md) — exceso de rentabilidad por unidad de volatilidad sobre una ventana móvil
- [Beta móvil](../../../financial-theory/technical-analysis/risk-metrics/beta-active-return.md) — con qué fuerza sigue el activo a un activo de comparación que elijas

Los periodos se cuentan en **sesiones**, los días en que el activo cotizó: una SMA 200 cubre 200 sesiones, unos 290 días naturales ([por qué](../../../financial-theory/technical-analysis/indicators/index.md)). La **Ventana** de las cuatro señales de riesgo móviles también cuenta días con cotización; para la Beta móvil, días en los que ambos activos cotizaron.

!!! info "No todos los indicadores pueden ejecutarse en todos los activos"

    ADX, Aroon, ATR, NATR, CCI, canales de Donchian y MFI necesitan precios **máximos** y **mínimos**; OBV y MFI necesitan el **volumen**. Sin esos datos, la tarjeta te dice qué datos faltan.

### 📉 Caída sobre el histórico completo {: #drawdown-full-history }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals-drawdown" alt="Tarjeta de señal de caída con la casilla de histórico completo">
</div>

La tarjeta **Caída bajo el pico** tiene una casilla **Histórico completo**, activada por defecto: la caída se mide desde el precio más alto de todo el histórico del activo, incluso años antes de las fechas en pantalla. Desmárcala para una vista más rápida, medida desde el precio más alto dentro de las fechas en pantalla.

---

## 💱 Comparar con un activo o un par de divisas {: #data-comparison }

El menú **Comparación de datos** añade:

- **Comparación de activos** — otro activo en el mismo gráfico, como una acción frente a su ETF de índice. En la vista **%** ambas líneas empiezan en 0 %.
- **Par FX** — el tipo de cambio de uno de tus pares de divisas.

**Sync** (🔄) en una tarjeta de Comparación de activos descarga los precios de ese activo para las fechas del gráfico, junto con los tipos de cambio que lo convierten, para los pares que existan. Cuando el par falta, un ⚠️ ámbar en la tarjeta lo crea; cuando faltan sus tipos, un 🔄 ámbar los sincroniza.

En el modo [Rentabilidad móvil](chart.md#rolling-return) solo permanece la Comparación de activos: cada activo comparado se convierte en una rentabilidad móvil, con la misma ventana y divisa. Las demás señales se ocultan, no se eliminan, y vuelven en el modo **Precios**.

---

## 📐 Benchmarks sintéticos

Curvas de referencia dibujadas solo a partir de sus parámetros, sin datos de mercado:

- [Crecimiento lineal](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md) — $y(t) = y_0\,(1 + r\,t)$
- [Crecimiento compuesto](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) — $y(t) = y_0\,(1 + r)^t$
- [Onda senoidal](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md) — $y(t) = A \sin(2\pi t / T) + y_0$

---

## 🩺 Leer una tarjeta de señal

- Un **spinner** gira mientras se calcula la señal.
- **📈 N** es el número de puntos de precio cargados.
- Un **ℹ** gris — calculada, con una advertencia menor: un pequeño hueco o un periodo de calentamiento casi completo. Pasa el cursor sobre el icono para ver los detalles.
- Un **⚠** ámbar — calculada, con una advertencia que merece un vistazo: huecos mayores, un periodo de calentamiento incompleto, o datos que empiezan después de la primera fecha en pantalla. La tarjeta también se vuelve ámbar.
- Un **⚠** rojo — no calculada: falta un campo de precio, hay poco histórico para los parámetros, no hay datos en absoluto, o hay un error de cálculo. La tarjeta se vuelve roja.

??? note "🧩 Histórico de precios irregular — cuando una señal es parcial"

    ADX, Aroon, ATR, NATR, CCI, canales de Donchian, MFI y OBV pueden ejecutarse sobre un histórico irregular: usan el tramo más reciente sin huecos que sea lo bastante largo, y la información emergente nombra ese tramo y cuántos puntos se omitieron. Los demás indicadores necesitan un histórico sin huecos, y explican por qué no pueden ejecutarse en lugar de dibujar una línea engañosa. Un fin de semana o un festivo de mercado no es un hueco.

---

## 🔗 Relacionado

- 📚 **[Indicadores técnicos](../../../financial-theory/technical-analysis/indicators/index.md)** — La fórmula de cada indicador y cómo leerlo
- ⚠️ **[Métricas de riesgo](../../../financial-theory/technical-analysis/risk-metrics/index.md)** — Las métricas detrás de las señales de riesgo
- 🧠 **[Exportación IA de activos](../../ai-export/asset.md)** — Indicadores técnicos calculados por el mismo backend, exportados para un asistente de IA
- 🛠️ **[Guía de plugins de señales](../../../developer/architecture/patterns/signal_plugin_guide.md)** — Para desarrolladores: cómo se calculan, se verifican y se añaden los indicadores
