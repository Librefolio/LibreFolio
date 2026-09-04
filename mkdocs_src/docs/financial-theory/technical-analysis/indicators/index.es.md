# 📉 Indicadores Técnicos

LibreFolio expone **17 indicadores técnicos calculados en el backend**, agrupados por la propiedad del mercado que miden. Los mismos contratos matemáticos alimentan los gráficos de Activos, gráficos FX compatibles, anotaciones y futuros consumidores analíticos.

!!! info "Price fields matter"

    No todos los indicadores pueden ejecutarse en todas las series. Los indicadores que solo usan cierre funcionan en Activos y tasas FX; los indicadores que requieren máximo, mínimo o volumen son solo para Activos y se reportan como no disponibles cuando esos campos no existen.

---

## 📈 Tendencia

Los indicadores de tendencia suavizan el precio o miden si un movimiento direccional está establecido.

| Indicador | Pregunta principal | Datos | Detalles |
|---|---|---|---|
| **EMA** | ¿Dónde está la tendencia ponderada reciente? | Cierre | [📖](ema.md) |
| **SMA** | ¿Cuál es el precio promedio de igual ponderación? | Cierre | [📖](sma.md) |
| **KAMA** | ¿Cómo debería adaptarse el suavizado al ruido? | Cierre | [📖](kama.md) |
| **ADX** | ¿Qué tan fuerte es la tendencia? | Máximo, Mínimo, Cierre | [📖](adx.md) |
| **Aroon** | ¿Qué tan recientes fueron los nuevos extremos? | Máximo, Mínimo | [📖](aroon.md) |

➡️ [Descripción general del grupo de Tendencia](trend.md)

---

## ⚡ Momentum

Los indicadores de momentum miden la velocidad, la presión direccional y la aceleración.

| Indicador | Pregunta principal | Datos | Detalles |
|---|---|---|---|
| **RSI** | ¿Dominan los compradores o los vendedores? | Cierre | [📖](rsi.md) |
| **MACD** | ¿Se está acelerando el momentum de la tendencia? | Cierre | [📖](macd.md) |
| **ROC** | ¿Qué tan rápido ha cambiado el precio? | Cierre | [📖](roc.md) |
| **Stochastic RSI** | ¿Dónde está el RSI dentro de su rango reciente? | Cierre | [📖](stochastic-rsi.md) |
| **PPO** | ¿Cuál es el momentum de la media móvil en términos porcentuales? | Cierre | [📖](ppo.md) |
| **CCI** | ¿Qué tan lejos está el precio de su media estadística reciente? | Máximo, Mínimo, Cierre | [📖](cci.md) |

➡️ [Descripción general del grupo de Momentum](momentum.md)

---

## 🌊 Volatilidad

Los indicadores de volatilidad miden el rango, la dispersión y la amplitud del canal, más que la dirección.

| Indicador | Pregunta principal | Datos | Detalles |
|---|---|---|---|
| **Bandas de Bollinger** | ¿Qué tan amplia es la envolvente estadística del precio? | Cierre | [📖](bollinger-bands.md) |
| **ATR** | ¿Qué tan grande es el rango verdadero típico? | Máximo, Mínimo, Cierre | [📖](atr.md) |
| **NATR** | ¿Qué tan grande es la volatilidad en relación con el precio? | Máximo, Mínimo, Cierre | [📖](natr.md) |
| **Canales de Donchian** | ¿Cuáles son el máximo más alto y el mínimo más bajo del período? | Máximo, Mínimo | [📖](donchian-channels.md) |

➡️ [Descripción general del grupo de Volatilidad](volatility.md)

---

## 📊 Volumen

Los indicadores de volumen combinan la dirección del precio con la actividad de negociación.

| Indicador | Pregunta principal | Datos | Detalles |
|---|---|---|---|
| **OBV** | ¿Está el volumen firmado acumulando o distribuyendo? | Cierre, Volumen | [📖](obv.md) |
| **MFI** | ¿El flujo de dinero es presión de compra o de venta? | Máximo, Mínimo, Cierre, Volumen | [📖](mfi.md) |

➡️ [Descripción general del grupo de Volumen](volume.md)

---

## 🔗 Relacionados

- 🎯 **[Benchmarks Sintéticos](../synthetic-benchmarks/index.md)** — Curvas matemáticas de referencia
- 📈 **[Gráfico Interactivo](../../../user/assets/detail/chart.md)** — Donde se muestran los indicadores
- 📊 **[Señales](../../../user/assets/detail/signals.md)** — Cómo configurar superposiciones en LibreFolio
