# 📊 Volatilidad

La volatilidad mide la **dispersión de los rendimientos**: cuánto fluctúa el precio de un activo a lo largo del tiempo. Es la medida de riesgo más fundamental en las finanzas y la base de casi todas las demás métricas de riesgo.

---

## 🔢 Fórmula

### 📐 Desviación Estándar de los Rendimientos

$$
\sigma = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (R_i - \bar{R})^2}
$$

donde $R_i$ son los rendimientos de periodos individuales y $\bar{R}$ es el rendimiento medio.

### 📈 Anualización

La volatilidad diaria se anualiza multiplicándola por la raíz cuadrada del número de días bursátiles:

$$
\sigma_{annual} = \sigma_{daily} \times \sqrt{252}
$$

!!! info "¿Por qué √252?"

    Se asume que los rendimientos son independientes entre días. La varianza de una suma de $N$ variables independientes es $N$ veces la varianza individual. Por lo tanto:

    $$\text{Var}_{annual} = 252 \times \text{Var}_{daily}$$
    $$\sigma_{annual} = \sqrt{252} \times \sigma_{daily}$$

---

## 💡 Interpretación

| Volatilidad Anualizada | Activos Típicos |
|---|---|
| 1-5% | Mercado monetario, bonos a corto plazo |
| 5-15% | Bonos gubernamentales, bonos corporativos grado de inversión |
| 15-25% | Acciones de gran capitalización, ETF de renta variable diversificados |
| 25-40% | Acciones de pequeña capitalización, acciones individuales |
| 40-80%+ | Cripto, acciones meme, productos apalancados |

---

## 📊 Volatilidad Realizada vs. Implícita

### 📈 Volatilidad Realizada (Histórica)

Calculada a partir de datos de precios **pasados**. Esto es lo que calcula LibreFolio:

$$
\sigma_{realized} = \text{StdDev}(\text{rendimientos históricos})
$$

### 🔮 Volatilidad Implícita

Extraída de los **precios de las opciones** utilizando el modelo Black-Scholes. Representa la **expectativa** del mercado sobre la volatilidad futura:

$$
C = f(S, K, T, r, \sigma_{implied})
$$

La volatilidad implícita mira hacia adelante, pero solo está disponible para activos que admiten opciones.

---

## 🔄 Volatilidad de Ventana Móvil

En lugar de calcular un único número de volatilidad para todo el periodo, la **volatilidad de ventana móvil** calcula $\sigma$ sobre una ventana deslizante (por ejemplo, 30 días), produciendo una serie temporal que muestra cómo evoluciona la volatilidad:

$$
\sigma_t^{(w)} = \text{StdDev}(R_{t-w+1}, R_{t-w+2}, \ldots, R_t)
$$

Esto es útil para:

- Identificar **regímenes de volatilidad** (periodos de calma frente a periodos turbulentos)
- Detectar el **agrupamiento de volatilidad** (los días de alta volatilidad tienden a seguir a otros días de alta volatilidad)
- Establecer tamaños de posición dinámicos (reducir la exposición durante periodos de alta volatilidad)

---

## 📐 Volatilidad y Teoría de Carteras

La volatilidad juega un papel central en la [Teoría Moderna de Carteras](../index.md):

- Es el **denominador** del [Ratio de Sharpe](sharpe-ratio.md)
- Determina el **ancho** de las [Bandas de Bollinger](../../technical-analysis/indicators/bollinger-bands.md)
- Es la entrada clave para la optimización de carteras (minimizar $\sigma_p$ para un $R_p$ objetivo)
- La [Diversificación](../diversification.md) reduce la volatilidad de la cartera cuando las correlaciones de los activos son menores que 1

---

## ⚠️ Limitaciones

!!! warning "Volatilidad ≠ Riesgo"

    La volatilidad trata los movimientos al alza y a la baja por igual. Un activo que presenta picos alcistas frecuentes tiene una volatilidad alta, pero puede ser muy atractivo. Para una medida centrada en el riesgo a la baja, utilice el [Ratio de Sortino](sortino-ratio.md) o el [Max Drawdown](max-drawdown.md).

!!! warning "No-normalidad"

    Los rendimientos financieros suelen presentar:

    - **Colas pesadas** (más eventos extremos de los que predice una distribución normal)
    - **Asimetría negativa** (caídas grandes más comunes que ganancias grandes)
    - **Agrupamiento de volatilidad** (periodos de calma y turbulencia)

    La desviación estándar por sí sola no captura estas características.

---

## 🔗 Relacionado

- 📐 **[Ratio de Sharpe](sharpe-ratio.md)** — Utiliza la volatilidad como denominador de riesgo
- 📊 **[Ratio de Sortino](sortino-ratio.md)** — Variante de la volatilidad centrada únicamente en el riesgo a la baja
- 📏 **[Bandas de Bollinger](../../technical-analysis/indicators/bollinger-bands.md)** — Envolvente de volatilidad en gráficos
- 🔀 **[Diversificación](../diversification.md)** — Reducción de la volatilidad de la cartera
