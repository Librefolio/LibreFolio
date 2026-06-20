# 📊 Métricas de Riesgo

Las métricas de riesgo proporcionan **medidas cuantitativas** del riesgo de la cartera. Cada métrica captura un aspecto diferente de la incertidumbre, y ninguna métrica por sí sola cuenta la historia completa. El uso de múltiples métricas en conjunto ofrece una visión integral del riesgo de la cartera.

---

## 📋 Descripción General Comparativa

| Métrica | Qué mide | Fórmula | Rango | Detalles |
|--------|-----------------|---------|-------|---------|
| **[Ratio de Sharpe](sharpe-ratio.md)** | Rendimiento ajustado al riesgo (volatilidad total) | $\frac{R_p - R_f}{\sigma_p}$ | $(-\infty, +\infty)$ | [📖](sharpe-ratio.md) |
| **[Ratio de Sortino](sortino-ratio.md)** | Rendimiento ajustado al riesgo (solo bajista) | $\frac{R_p - R_f}{\sigma_d}$ | $(-\infty, +\infty)$ | [📖](sortino-ratio.md) |
| **[Máximo Drawdown](max-drawdown.md)** | Mayor caída desde el pico hasta el valle | $\frac{Trough - Peak}{Peak}$ | $[-100\%, 0\%]$ | [📖](max-drawdown.md) |
| **[Volatilidad](volatility.md)** | Dispersión de los rendimientos | $\sigma = \sqrt{\text{Var}(R)}$ | $[0, +\infty)$ | [📖](volatility.md) |

---

## 🔑 Cuándo utilizar cada métrica

| Escenario | Mejor métrica | Por qué |
|----------|-------------|-----|
| Comparar dos fondos | **Ratio de Sharpe** | Normaliza el rendimiento según el riesgo total |
| Distribuciones de rendimiento asimétricas | **Ratio de Sortino** | Solo penaliza la volatilidad bajista |
| Planificación del peor escenario | **Máximo Drawdown** | Muestra el punto de máxima pérdida |
| Evaluación general del riesgo | **Volatilidad** | Base para todas las demás métricas |
| Optimización de la cartera | **Las cuatro** | Cada una captura una dimensión diferente |

---

## ⚠️ Errores Comunes

!!! warning "Limitations"

    - **Métricas históricas ≠ riesgo futuro**: La volatilidad pasada puede no predecir la volatilidad futura
    - **Supuesto de distribución normal**: Sharpe y Sortino asumen que los rendimientos son aproximadamente normales; los rendimientos financieros tienen colas pesadas
    - **Sensibilidad al periodo de observación**: Las métricas cambian significativamente dependiendo de la ventana de tiempo
    - **Dependencia del benchmark**: Sharpe y Sortino dependen de la tasa libre de riesgo, la cual cambia con el tiempo

---

## 🔗 Relacionado

- 🔀 **[Diversificación](../../portfolio-theory/diversification.md)** — Cómo funciona matemáticamente la reducción del riesgo
- ⚖️ **[Asignación de Activos](../../portfolio-theory/asset-allocation.md)** — Uso de métricas de riesgo para guiar la asignación
- 📈 **[Rendimientos y Tasas de Crecimiento](../../fundamentals/returns.md)** — La vertiente del "rendimiento" en la relación riesgo-rendimiento
