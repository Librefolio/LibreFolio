# 📊 Métricas de Riesgo

Las métricas de riesgo proporcionan **medidas cuantitativas** del riesgo de la cartera. Cada métrica captura un aspecto diferente de la incertidumbre, y ninguna métrica por sí sola cuenta la historia completa. El uso de múltiples métricas en conjunto ofrece una visión integral del riesgo de la cartera.

---

## 📋 Descripción General Comparativa

| Métrica | Qué Mide | Fórmula | Rango | Detalles |
|--------|-----------------|---------|-------|---------|
| **[Ratio de Sharpe](sharpe-ratio.md)** | Rentabilidad ajustada al riesgo (volatilidad total) | $\frac{R_p - R_f}{\sigma_p}$ | $(-\infty, +\infty)$ | [📖](sharpe-ratio.md) |
| **[Ratio de Sortino](sortino-ratio.md)** | Rentabilidad ajustada al riesgo (solo volatilidad a la baja) | $\frac{R_p - R_f}{\sigma_d}$ | $(-\infty, +\infty)$ | [📖](sortino-ratio.md) |
| **[Max Drawdown](max-drawdown.md)** | Mayor caída desde el pico al valle | $\frac{Trough - Peak}{Peak}$ | $[-100\%, 0\%]$ | [📖](max-drawdown.md) |
| **[Volatilidad](volatility.md)** | Dispersión de las rentabilidades | $\sigma = \sqrt{\text{Var}(R)}$ | $[0, +\infty)$ | [📖](volatility.md) |

---

## 🔑 Cuándo Utilizar Cada Métrica

| Escenario | Mejor Métrica | Por qué |
|----------|-------------|-----|
| Comparar dos fondos | **Ratio de Sharpe** | Normaliza la rentabilidad mediante el riesgo total |
| Distribuciones de rentabilidad asimétricas | **Ratio de Sortino** | Solo penaliza la volatilidad a la baja |
| Planificación del peor escenario | **Max Drawdown** | Muestra el punto de máxima pérdida |
| Evaluación general del riesgo | **Volatilidad** | Base para todas las demás métricas |
| Optimización de la cartera | **Las cuatro** | Cada una captura una dimensión diferente |

---

## ⚠️ Errores Comunes

!!! warning "Limitations"

    - **Métricas históricas ≠ riesgo futuro**: La volatilidad pasada no necesariamente predice la volatilidad futura
    - **Supuesto de distribución normal**: Sharpe y Sortino asumen que las rentabilidades son aproximadamente normales; las rentabilidades financieras tienen colas pesadas (fat tails)
    - **Sensibilidad al periodo de análisis**: Las métricas cambian significativamente dependiendo de la ventana de tiempo
    - **Dependencia del benchmark**: Sharpe y Sortino dependen de la tasa libre de riesgo, la cual cambia con el tiempo

---

## 🔗 Relacionado

- 🔀 **[Diversificación](../diversification.md)** — Cómo funciona matemáticamente la reducción del riesgo
- ⚖️ **[Asignación de Activos](../asset-allocation.md)** — Uso de métricas de riesgo para guiar la asignación
- 📈 **[Rendimientos y Tasas de Crecimiento](../../fundamentals/returns.md)** — El lado de la "rentabilidad" de la relación riesgo-rentabilidad
