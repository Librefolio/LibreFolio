# 📉 Indicadores Técnicos

LibreFolio ofrece **22 indicadores técnicos calculados por el backend**, agrupados según la propiedad del mercado que miden. Los mismos contratos matemáticos alimentan los gráficos de activos, los gráficos FX compatibles, las anotaciones y los consumidores analíticos, como AI Export.

!!! info "Los campos de precio importan"

    No todos los indicadores pueden ejecutarse en todas las series. **9 de los 22**
    son indicadores de solo cierre y funcionan tanto en activos como en tipos de cambio FX (EMA, SMA, KAMA, MACD, RSI, ROC, PPO, RSI Estocástico y Bandas de Bollinger).
    Los indicadores que requieren máximo, mínimo o volumen son exclusivos de activos
    y se declaran como no disponibles cuando esos campos no existen. La familia
    **Risk** también es exclusiva de activos: no se generan lecturas de riesgo móvil
    para pares de divisas.

---

## 📈 Tendencia

Los indicadores de tendencia suavizan el precio o miden si se ha establecido un movimiento direccional.

| Indicador | Pregunta principal | Datos | Detalles |
|---|---|---|---|
| **EMA** | ¿Dónde se sitúa la tendencia ponderada reciente? | Cierre | [📖](ema.md) |
| **SMA** | ¿Cuál es el precio medio de igual ponderación? | Cierre | [📖](sma.md) |
| **KAMA** | ¿Cómo debe adaptarse el suavizado al ruido? | Cierre | [📖](kama.md) |
| **ADX** | ¿Qué intensidad tiene la tendencia? | Máximo, Mínimo, Cierre | [📖](adx.md) |
| **Aroon** | ¿Hace cuánto se produjeron los nuevos extremos? | Máximo, Mínimo | [📖](aroon.md) |

➡️ [Descripción general del grupo de Tendencia](trend.md)

---

## ⚡ Momentum

Los indicadores de momentum miden la velocidad, la presión direccional y la aceleración.

| Indicador | Pregunta principal | Datos | Detalles |
|---|---|---|---|
| **RSI** | ¿Están dominando los compradores o los vendedores? | Cierre | [📖](rsi.md) |
| **MACD** | ¿Se está acelerando el impulso de la tendencia? | Cierre | [📖](macd.md) |
| **ROC** | ¿Con qué rapidez ha cambiado el precio? | Cierre | [📖](roc.md) |
| **RSI Estocástico** | ¿Dónde se encuentra el RSI dentro de su rango reciente? | Cierre | [📖](stochastic-rsi.md) |
| **PPO** | ¿Cuál es el impulso de la media móvil en términos porcentuales? | Cierre | [📖](ppo.md) |
| **CCI** | ¿Cuánto se aleja el precio de su media estadística reciente? | Máximo, Mínimo, Cierre | [📖](cci.md) |

➡️ [Descripción general del grupo de Momentum](momentum.md)

---

## 🌊 Volatilidad

Los indicadores de volatilidad miden el rango, la dispersión y la anchura del canal, no la dirección.

| Indicador | Pregunta principal | Datos | Detalles |
|---|---|---|---|
| **Bandas de Bollinger** | ¿Qué anchura tiene la envolvente estadística del precio? | Cierre | [📖](bollinger-bands.md) |
| **ATR** | ¿Cuál es la magnitud del rango real típico? | Máximo, Mínimo, Cierre | [📖](atr.md) |
| **NATR** | ¿Qué magnitud tiene la volatilidad en relación con el precio? | Máximo, Mínimo, Cierre | [📖](natr.md) |
| **Canales de Donchian** | ¿Cuáles son el máximo más alto y el mínimo más bajo del período? | Máximo, Mínimo | [📖](donchian-channels.md) |

➡️ [Descripción general del grupo de Volatilidad](volatility.md)

---

## 📊 Volumen

Los indicadores de volumen combinan la dirección del precio con la actividad de negociación.

| Indicador | Pregunta principal | Datos | Detalles |
|---|---|---|---|
| **OBV** | ¿El volumen con signo se está acumulando o distribuyendo? | Cierre, Volumen | [📖](obv.md) |
| **MFI** | ¿El flujo de dinero es presión de compra o de venta? | Máximo, Mínimo, Cierre, Volumen | [📖](mfi.md) |

➡️ [Descripción general del grupo de Volumen](volume.md)

---

## ⚠️ Riesgo

Los indicadores de riesgo convierten la propia serie de precios en una lectura de riesgo móvil. Son **exclusivos de activos** — los pares de divisas no los generan.

| Indicador | Pregunta principal | Datos | Detalles |
|---|---|---|---|
| **Drawdown bajo el máximo** | ¿Cuánto está el precio por debajo del máximo acumulado? | Cierre | [📖](../risk-metrics/max-drawdown.md) |
| **Rentabilidad móvil** | ¿Qué rentabilidad compuesta ha generado la última ventana? | Cierre | [📖](../../fundamentals/returns.md) |
| **Volatilidad móvil** | ¿Cuán dispersas están las rentabilidades recientes? | Cierre | [📖](../risk-metrics/volatility.md) |
| **Ratio de Sharpe móvil** | ¿Está el exceso de rentabilidad compensando su riesgo? | Cierre | [📖](../risk-metrics/sharpe-ratio.md) |
| **Beta móvil** | ¿Qué sensibilidad tiene el activo frente a un activo de comparación? | Cierre + activo de comparación | — |

➡️ [Descripción general de las métricas de riesgo](../risk-metrics/index.md)

---

## 🔗 Relacionados

- 🎯 **[Benchmarks sintéticos](../synthetic-benchmarks/index.md)** — Curvas matemáticas de referencia
- 📈 **[Gráfico interactivo](../../../user/assets/detail/chart.md)** — Donde se muestran los indicadores
- 📊 **[Señales](../../../user/assets/detail/signals.md)** — Cómo configurar superposiciones en LibreFolio
