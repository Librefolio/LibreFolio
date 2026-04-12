# 📚 Teoría Financiera

Esta sección documenta los modelos financieros, convenciones y definiciones utilizados en todo LibreFolio.

## 📖 Descripción general

Los cálculos financieros precisos son fundamentales para un rastreador de carteras. LibreFolio implementa convenciones financieras estándar para garantizar la coherencia con los informes de los brókers y los datos del mundo real. Esta sección está organizada en cuatro áreas temáticas.

## 🗺️ Mapa Conceptual

### 🏦 [Instrumentos](instruments/index.md)

Los bloques básicos de cualquier cartera:

- **[Tipos de Activos](instruments/asset-types/index.md)** — Acciones, ETF, Bonos, Cripto, Bienes raíces, Índices
- **[Tipos de Transacciones](instruments/transaction-types/index.md)** — Compra/Venta, Depósito/Retiro, Dividendo, Comisión, Interés, Transferencia
- **[Eventos de Activos](instruments/asset-events/index.md)** — Dividendo, Interés, Split (Desdoblamiento), Ajuste de Precio, Liquidación al Vencimiento

### 📊 [Análisis Técnico](technical-analysis/index.md)

Capas de gráficos basadas en datos y curvas de referencia matemáticas:

- **[Indicadores](technical-analysis/indicators/index.md)** — EMA, MACD, RSI, Bandas de Bollinger
- **[Benchmarks Sintéticos](technical-analysis/synthetic-benchmarks/index.md)** — Crecimiento Lineal, Crecimiento Compuesto, Onda Sinusoidal

### 📐 [Fundamentos](fundamentals/index.md)

Conceptos financieros básicos:

- **[Convenciones de Conteo de Días](fundamentals/day-count.md)** — ACT/365, ACT/360, 30/360, ACT/ACT
- **[Retornos y Tasas de Crecimiento](fundamentals/returns.md)** — Retornos Simples vs Logarítmicos, CAGR, anualización
- **[Fiscalidad](fundamentals/taxation.md)** — Plusvalías, aplazamiento fiscal, Acumulación vs Distribución (Acc vs Dist)

### 📈 [Teoría de Carteras](portfolio-theory/index.md)

Teoría Moderna de Carteras y gestión de riesgos:

- **[Diversificación](portfolio-theory/diversification.md)** — Correlación, riesgo sistemático vs idiosincrásico
- **[Asignación de Activos](portfolio-theory/asset-allocation.md)** — Estratégica, táctica, trayectorias de deslizamiento (glide paths), rebalanceo
- **[Métricas de Riesgo](portfolio-theory/risk-metrics/index.md)** — Sharpe, Sortino, Máxima Caída (Max Drawdown), Volatilidad
