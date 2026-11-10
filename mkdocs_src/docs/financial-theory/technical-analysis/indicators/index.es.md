# 📉 Indicadores técnicos

LibreFolio expone **22 indicadores técnicos calculados por el backend**, agrupados por la propiedad de mercado que miden. Los mismos contratos matemáticos alimentan los gráficos de activos, los gráficos FX compatibles, las anotaciones y los consumidores analíticos como la exportación IA.

Los indicadores cuentan **sesiones**, no días naturales: una sesión es un día en el que la serie tiene una cotización propia — un precio para un activo, un tipo de cambio publicado para un par FX. Un día que la serie rellena con el último valor conocido — un fin de semana, un día festivo de mercado, cualquier día sin cotización — no es una sesión, y tampoco lo es un precio almacenado con fecha en fin de semana o día festivo de mercado que solo repite el cierre anterior (un [arrastre almacenado](../risk-metrics/data-quality.md#stored-carries)). Los períodos, el período de calentamiento y el historial mínimo se cuentan en sesiones, así que la SMA 200 promedia las últimas 200 sesiones, unos 290 días naturales. El gráfico conserva sus fechas de calendario: un indicador tiene valores solo en sesiones, y su línea une los días cerrados intermedios. La familia de Riesgo cuenta sus ventanas de otra manera. La volatilidad móvil, el ratio de Sharpe móvil y la beta móvil cuentan **observaciones de retorno** de la serie de retornos preparada del activo: un retorno por sesión, medido desde la sesión anterior — para la beta móvil, para cada fecha del [calendario conjunto](../risk-metrics/data-quality.md#alignment-what-missing-data-actually-costs) de ambos activos —, así que una ventana de $w$ toma $w$ retornos de $w + 1$ precios. El **retorno móvil** cuenta **días naturales**: compara cada fecha con el cierre resuelto exactamente $N$ días naturales antes ([Retorno móvil](../../fundamentals/returns.md#rolling-return-calendar)), el mismo cálculo que el [modo Retorno móvil](../../../user/assets/detail/chart.md#primary-modes) del gráfico.

!!! info "Los campos de precio importan"

    No todos los indicadores pueden ejecutarse en todas las series. **9 de los 22** son
    indicadores basados únicamente en el cierre y funcionan tanto en activos como en tipos de cambio FX
    (EMA, SMA, KAMA, MACD, RSI, ROC, PPO, RSI estocástico, Bandas de Bollinger). Los
    indicadores que requieren máximo, mínimo o volumen son exclusivos de activos y se
    marcan como no disponibles cuando esos campos no existen. La familia **Riesgo**
    también es exclusiva de activos: las lecturas de riesgo móvil no se generan para
    pares FX.

---

## 📈 Tendencia

Los indicadores de tendencia suavizan el precio o miden si se ha establecido un movimiento direccional.

| Indicador | Pregunta principal | Datos | Detalles |
|---|---|---|---|
| **EMA** | ¿Dónde está la tendencia ponderada reciente? | Cierre | [📖](ema.md) |
| **SMA** | ¿Cuál es el precio medio de igual ponderación? | Cierre | [📖](sma.md) |
| **KAMA** | ¿Cómo debería adaptarse el suavizado al ruido? | Cierre | [📖](kama.md) |
| **ADX** | ¿Qué tan fuerte es la tendencia? | Máximo, Mínimo, Cierre | [📖](adx.md) |
| **Aroon** | ¿Hace cuánto se produjeron nuevos extremos? | Máximo, Mínimo | [📖](aroon.md) |

➡️ [Resumen del grupo de tendencia](trend.md)

---

## ⚡ Impulso

Los indicadores de impulso miden velocidad, presión direccional y aceleración.

| Indicador | Pregunta principal | Datos | Detalles |
|---|---|---|---|
| **RSI** | ¿Están dominando los compradores o los vendedores? | Cierre | [📖](rsi.md) |
| **MACD** | ¿Está acelerándose el impulso de la tendencia? | Cierre | [📖](macd.md) |
| **ROC** | ¿A qué velocidad ha cambiado el precio? | Cierre | [📖](roc.md) |
| **RSI estocástico** | ¿Dónde está el RSI dentro de su rango reciente? | Cierre | [📖](stochastic-rsi.md) |
| **PPO** | ¿Cuál es el impulso de la media móvil en términos porcentuales? | Cierre | [📖](ppo.md) |
| **CCI** | ¿A qué distancia está el precio de su media estadística reciente? | Máximo, Mínimo, Cierre | [📖](cci.md) |

➡️ [Resumen del grupo de impulso](momentum.md)

---

## 🌊 Volatilidad

Los indicadores de volatilidad miden rango, dispersión y amplitud de canal en lugar de dirección.

| Indicador | Pregunta principal | Datos | Detalles |
|---|---|---|---|
| **Bandas de Bollinger** | ¿Qué tan amplia es la envolvente estadística del precio? | Cierre | [📖](bollinger-bands.md) |
| **ATR** | ¿Qué tan grande es el rango verdadero típico? | Máximo, Mínimo, Cierre | [📖](atr.md) |
| **NATR** | ¿Qué tan grande es la volatilidad en relación con el precio? | Máximo, Mínimo, Cierre | [📖](natr.md) |
| **Canales de Donchian** | ¿Cuáles son el máximo más alto y el mínimo más bajo del período? | Máximo, Mínimo | [📖](donchian-channels.md) |

➡️ [Resumen del grupo de volatilidad](volatility.md)

---

## 📊 Volumen

Los indicadores de volumen combinan la dirección del precio con la actividad de negociación.

| Indicador | Pregunta principal | Datos | Detalles |
|---|---|---|---|
| **OBV** | ¿El volumen con signo se está acumulando o distribuyendo? | Cierre, Volumen | [📖](obv.md) |
| **MFI** | ¿El flujo de dinero es presión de compra o de venta? | Máximo, Mínimo, Cierre, Volumen | [📖](mfi.md) |

➡️ [Resumen del grupo de volumen](volume.md)

---

## ⚠️ Riesgo

Los indicadores de riesgo convierten la propia serie de precios en una lectura de riesgo móvil. Son **exclusivos de activos** — los pares FX no los generan.

| Indicador | Pregunta principal | Datos | Detalles |
|---|---|---|---|
| **Caída bajo el pico** | ¿Cuánto está el precio por debajo del pico acumulado? | Cierre | [📖](../risk-metrics/current-drawdown.md) |
| **Retorno móvil** | ¿Cuánto se movió el precio durante los últimos $N$ días naturales? | Cierre | [📖](../../fundamentals/returns.md#rolling-return) |
| **Volatilidad móvil** | ¿Qué tan dispersos son los retornos recientes? | Cierre | [📖](../risk-metrics/volatility.md) |
| **Ratio de Sharpe móvil** | ¿El exceso de retorno compensa su riesgo? | Cierre | [📖](../risk-metrics/sharpe-ratio.md) |
| **Beta móvil** | ¿Qué tan sensible es el activo a un activo de comparación? | Cierre + activo de comparación | [📖](../risk-metrics/beta-active-return.md) |

➡️ [Resumen de métricas de riesgo](../risk-metrics/index.md)

---

## 🔗 Relacionados

- 🎯 **[Benchmarks sintéticos](../synthetic-benchmarks/index.md)** — Curvas de referencia matemáticas
- 📈 **[Gráfico interactivo](../../../user/assets/detail/chart.md)** — Donde se muestran los indicadores
- 📊 **[Señales](../../../user/assets/detail/signals.md)** — Cómo configurar superposiciones en LibreFolio
