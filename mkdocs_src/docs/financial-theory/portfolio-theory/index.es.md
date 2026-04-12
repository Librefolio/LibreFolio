# 📈 Teoría de Carteras

La teoría de carteras proporciona el marco matemático para construir carteras de inversión que maximicen el rendimiento esperado para un nivel de riesgo dado — o equivalentemente, minimicen el riesgo para un rendimiento esperado determinado.

---

## 📖 Descripción General

### 🏛️ Teoría Moderna de Carteras (MPT)

Introducida por Harry Markowitz en 1952, la Teoría Moderna de Carteras revolucionó las inversiones al demostrar que **el riesgo de una cartera no es simplemente la suma de los riesgos individuales de los activos**. A través de la diversificación, un inversor puede reducir la volatilidad de la cartera sin sacrificar el rendimiento esperado.

La idea clave: lo que importa no es solo el riesgo y el rendimiento individual de cada activo, sino cómo se mueven los activos **en relación unos con otros** (correlación).

### 📐 La Frontera Eficiente

La frontera eficiente es el conjunto de carteras que ofrecen el **mayor rendimiento esperado para cada nivel de riesgo**:

$$
\max_{w} \quad E[R_p] = \sum_i w_i \cdot E[R_i]
$$

sujeto a:

$$
\sigma_p^2 = \sum_i \sum_j w_i w_j \sigma_i \sigma_j \rho_{ij} \leq \sigma_{target}^2
$$

donde $w_i$ son las ponderaciones de la cartera, $E[R_i]$ los rendimientos esperados, $\sigma_i$ las volatilidades y $\rho_{ij}$ las correlaciones.

Cualquier cartera **por debajo** de la frontera es suboptimal: se podría obtener un mayor rendimiento con el mismo riesgo, o un menor riesgo con el mismo rendimiento.

---

## 📖 Contenido

### 🔀 [Diversificación](diversification.md)

El fundamento matemático de "no poner todos los huevos en la misma cesta". Cómo la combinación de activos con una correlación imperfecta reduce la varianza de la cartera — y los límites de la diversificación frente al riesgo sistemático.

### ⚖️ [Asignación de Activos](asset-allocation.md)

Asignación estratégica frente a táctica, rutas de deslizamiento, estrategias de fecha objetivo y el arte del rebalanceo. Cómo decidir *cuánto* poseer de cada clase de activo.

### 📊 [Métricas de Riesgo](risk-metrics/index.md)

Medidas cuantitativas del riesgo de la cartera. Desde la desviación estándar hasta el ratio de Sharpe, cada métrica captura un aspecto diferente del riesgo:

- **[Ratio de Sharpe](risk-metrics/sharpe-ratio.md)** — Rendimiento ajustado al riesgo (volatilidad total)
- **[Ratio de Sortino](risk-metrics/sortino-ratio.md)** — Rendimiento ajustado al riesgo (solo riesgo de caída)
- **[Max Drawdown](risk-metrics/max-drawdown.md)** — La mayor caída desde el punto máximo al punto más bajo
- **[Volatilidad](risk-metrics/volatility.md)** — Desviación estándar de los rendimientos

---

## 🔑 Supuestos Clave y Limitaciones

!!! warning "MPT assumptions"

    La Teoría Moderna de Carteras asume:

    1. **Inversores racionales** que buscan maximizar la utilidad
    2. **Distribución normal** de los rendimientos (en la práctica, los rendimientos tienen colas pesadas)
    3. Rendimientos esperados, volatilidades y correlaciones **conocidos** (en la práctica, estos se estiman con error)
    4. **Mercados sin fricciones** — sin impuestos, sin costes de transacción (¡LibreFolio te ayuda a rastrearlos!)

A pesar de estas limitaciones, la MPT sigue siendo la base de la gestión de carteras institucional y proporciona el vocabulario utilizado por toda la industria de la inversión.

---

## 🔗 Secciones Relacionadas

- 🏦 **[Instrumentos](../instruments/index.md)** — Los bloques básicos de las carteras
- 📐 **[Fundamentos](../fundamentals/index.md)** — Rendimientos, convenciones de recuento de días, tributación
- 📊 **[Análisis Técnico](../technical-analysis/index.md)** — Herramientas de análisis de activos individuales
