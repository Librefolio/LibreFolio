# 🔀 Diversificación

La diversificación es la estrategia de gestión de riesgos más fundamental: al combinar activos que no se mueven en perfecta sincronía, un inversor puede **reducir la volatilidad de la cartera** sin reducir necesariamente el rendimiento esperado.

---

## 📐 Las Matemáticas

### 📊 Varianza de una Cartera de Dos Activos

Para una cartera de dos activos con pesos $w_1$ y $w_2 = 1 - w_1$:

$$
\sigma_p^2 = w_1^2 \sigma_1^2 + w_2^2 \sigma_2^2 + 2 w_1 w_2 \sigma_1 \sigma_2 \rho_{12}
$$

donde:

- $\sigma_1, \sigma_2$ son las volatilidades individuales de los activos
- $\rho_{12}$ es el **coeficiente de correlación** ($-1 \leq \rho \leq +1$)

La magia de la diversificación reside en el **término cruzado**: cuando $\rho_{12} < 1$, la varianza de la cartera es **menor** que el promedio ponderado de las varianzas individuales.

### 🔑 Efectos de la Correlación

| Correlación $\rho$ | Efecto | Ejemplo |
|---|---|---|
| $+1$ | Sin beneficio de diversificación — los activos se mueven idénticamente | Dos ETF del S&P 500 |
| $0$ | Reducción significativa de la varianza | Acciones vs Oro |
| $-1$ | Cobertura perfecta — la varianza puede llegar a cero | Posición larga en acciones + opción put |

### 📈 Generalización para N Activos

Para $N$ activos:

$$
\sigma_p^2 = \sum_{i=1}^{N} \sum_{j=1}^{N} w_i w_j \sigma_i \sigma_j \rho_{ij}
$$

A medida que $N$ aumenta, la contribución de las varianzas individuales disminuye (proporcional a $1/N$), pero la contribución de las covarianzas permanece. Esto conduce al concepto de **riesgo sistemático**.

---

## 🎯 Riesgo Sistemático vs Idiosincrásico

### 📊 Riesgo Idiosincrásico (Diversificable)

Riesgo específico de una sola empresa o activo. Ejemplos:

- Salida del CEO
- Retirada de un producto
- Expiración de una patente

Este riesgo **puede eliminarse mediante la diversificación** manteniendo muchos activos. Con aproximadamente 30 acciones no correlacionadas, el riesgo idiosincrásico se aproxima a cero.

### 🌍 Riesgo Sistemático (No Diversificable)

Riesgo que afecta a todo el mercado. Ejemplos:

- Cambios en las tasas de interés
- Recesiones
- Pandemias
- Eventos geopolíticos

Este riesgo **no puede eliminarse** a través de la diversificación. Es el riesgo por el cual los inversores son compensados — la base del Capital Asset Pricing Model (CAPM).

$$
\sigma_{portfolio}^2 = \underbrace{\sigma_{systematic}^2}_{\text{no se puede eliminar}} + \underbrace{\sigma_{idiosyncratic}^2}_{\xrightarrow{N \to \infty} 0}
$$

---

## ⚠️ Trampas de la Diversificación

!!! warning "Correlation instability"

    Las correlaciones **no son constantes** — tienden a aumentar durante las crisis de mercado (precisamente cuando más se necesita la diversificación). Este fenómeno, llamado **ruptura de la correlación**, significa que la diversificación proporciona menos protección durante eventos extremos de lo que sugieren los datos históricos.

!!! info "Over-diversification"

    A partir de cierto punto, añadir más activos aumenta la complejidad y el coste (comisiones de transacción, complejidad fiscal) sin reducir el riesgo de manera significativa. El punto óptimo para la mayoría de los inversores es poseer entre 20 y 40 posiciones distribuidas en diferentes clases de activos y geografías.

---

## 🔗 Relacionado

- ⚖️ **[Asignación de Activos](asset-allocation.md)** — Cómo elegir los pesos de la cartera
- 📊 **[Volatilidad](../technical-analysis/risk-metrics/volatility.md)** — Medir el riesgo que la diversificación reduce
- 📈 **[Máximo Drawdown](../technical-analysis/risk-metrics/max-drawdown.md)** — La métrica del peor escenario posible
