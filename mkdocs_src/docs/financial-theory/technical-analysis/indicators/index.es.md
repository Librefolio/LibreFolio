# 📉 Indicadores Técnicos

LibreFolio proporciona cuatro indicadores técnicos como indicadores superpuestos en el gráfico. Cada indicador se explica desde dos perspectivas complementarias: la interpretación **financiera** que los traders utilizan a diario y el equivalente de **procesamiento de señales** que los ingenieros reconocerán al instante.

!!! info "¿Por qué dos perspectivas?"

    Los mercados financieros **no** son sistemas LTI (Lineales e Invariantes en el Tiempo)
    estacionarios; son ruidosos, caóticos y su contenido espectral cambia con el tiempo.
    Sin embargo, las herramientas matemáticas que aplicamos para extraer la tendencia,
    el impulso o la volatilidad son *exactamente* los mismos filtros de tiempo discreto
    que se enseñan en cualquier curso de procesamiento de señales.

---

## 📋 Descripción General de los Indicadores

| Indicador | Qué mide | Uso clave | Detalles |
|-----------|-----------------|---------|---------|
| **EMA** | Dirección de la tendencia | Detección de cruces dorados/de la muerte | [📖](ema.md) |
| **MACD** | Impulso / aceleración de la tendencia | Cruces alcistas/bajistas | [📖](macd.md) |
| **RSI** | Sobrecompra / sobreventa | Configuraciones de reversión a la media | [📖](rsi.md) |
| **Bandas de Bollinger** | Envolvente de volatilidad | Detección de compresión $\rightarrow$ ruptura | [📖](bollinger-bands.md) |

---

## 🔗 Relacionados

- 🎯 **[Benchmarks Sintéticos](../synthetic-benchmarks/index.md)** — Curvas de benchmark matemáticas
- 📈 **[Gráfico Interactivo](../../../user/assets/detail/chart.md)** — Donde se muestran los indicadores
- 📊 **[Señales](../../../user/assets/detail/signals.md)** — Cómo configurar los indicadores superpuestos en LibreFolio
