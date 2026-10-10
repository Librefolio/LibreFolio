# 📊 Volatilidad

La volatilidad mide la **dispersión de los rendimientos** — cuánto fluctúa el precio de un activo a lo largo del tiempo. Es la medida de riesgo más fundamental en finanzas y el componente básico de casi todas las demás métricas de riesgo.

---

## 🔢 Fórmula {: #formula }

### 📐 Desviación estándar de los rendimientos {: #standard-deviation-of-returns }

$$
\sigma = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (R_i - \bar{R})^2}
$$

donde $R_i$ son los rendimientos de cada periodo y $\bar{R}$ es el rendimiento medio.

### 📈 Anualización {: #annualization }

La volatilidad por periodo se anualiza multiplicándola por la raíz cuadrada del número de periodos que contiene un año:

$$
\sigma_{annual} = \sigma_{period} \times \sqrt{f}
$$

El factor $f$ se **mide a partir de los datos observados**, no se fija de antemano: es el número de rendimientos realmente utilizados, reescalado a un año calendario completo en función del intervalo que abarcan.

$$
f = \frac{N \times 365}{D}
$$

donde $N$ es el número de rendimientos del periodo y $D$ los días calendario que abarcan.

!!! info "¿Por qué una raíz cuadrada?"

    Se supone que los rendimientos son independientes entre periodos. La varianza de una suma de $f$ variables independientes es $f$ veces la varianza individual. Por lo tanto:

    $$\text{Var}_{annual} = f \times \text{Var}_{period}$$

    $$\sigma_{annual} = \sqrt{f} \times \sigma_{period}$$

!!! info "√252 es un resultado, no una constante"

    Una acción con precio diario aporta aproximadamente 252 rendimientos a lo largo de un año calendario completo, por lo que $f = 252 \times 365 / 365 = 252$ y se recupera la conocida $\sqrt{252}$ — como resultado de la medición, no como una suposición incorporada en ella. Un instrumento que cotiza todos los días calendario, como las criptomonedas, da $f \approx 365$ y, por lo tanto, $\approx \sqrt{365}$: un $\sqrt{252}$ codificado de forma fija **subestimaría** su volatilidad anualizada. Un fondo con precio semanal da $f \approx 52$.

    → Véase **[Anualización observada](observed-annualization.md)** para la derivación, los ejemplos resueltos y qué aporta la cobertura de datos a dichos ejemplos.

---

## 💡 Interpretación {: #interpretation }

| Volatilidad anualizada | Activos típicos |
|---|---|
| 1-5% | Mercado monetario, bonos a corto plazo |
| 5-15% | Bonos gubernamentales, corporativos con grado de inversión |
| 15-25% | Acciones de gran capitalización, ETFs de renta variable diversificados |
| 25-40% | Acciones de pequeña capitalización, acciones individuales |
| 40-80%+ | Criptomonedas, acciones meme, productos apalancados |

---

## 📊 Volatilidad realizada vs implícita {: #realized-vs-implied-volatility }

### 📈 Volatilidad realizada (histórica) {: #realized-historical-volatility }

Calculada a partir de datos de precios **pasados**. Esto es lo que calcula LibreFolio:

$$
\sigma_{realized} = \text{StdDev}(\text{historical returns})
$$

### 🔮 Volatilidad implícita {: #implied-volatility }

Extraída de los **precios de opciones** utilizando el modelo Black-Scholes. Representa la **expectativa** del mercado sobre la volatilidad futura:

$$
C = f(S, K, T, r, \sigma_{implied})
$$

La volatilidad implícita mira hacia el futuro, pero solo está disponible para activos con opciones.

---

## 🔄 Volatilidad de ventana móvil {: #rolling-window-volatility }

En lugar de calcular un único número de volatilidad para todo el periodo, la **volatilidad de ventana móvil** calcula $\sigma$ en una ventana deslizante (p. ej., 30 días), produciendo una serie temporal que muestra cómo evoluciona la volatilidad:

$$
\sigma_t^{(w)} = \text{StdDev}(R_{t-w+1}, R_{t-w+2}, \ldots, R_t)
$$

Esto es útil para:

- Identificar **regímenes de volatilidad** (periodos tranquilos vs turbulentos)
- Detectar **agrupamiento de volatilidad** (los días de alta volatilidad tienden a seguir a días de alta volatilidad)
- Establecer tamaños de posición dinámicos (reducir la exposición durante periodos de alta volatilidad)

---

## 📐 Volatilidad y teoría de carteras {: #volatility-and-portfolio-theory }

La volatilidad desempeña un papel central en la [Teoría Moderna de Carteras](../index.md):

- Es el **denominador** del [ratio de Sharpe](sharpe-ratio.md)
- Determina la **amplitud** de las [Bandas de Bollinger](../../technical-analysis/indicators/bollinger-bands.md)
- Es la entrada clave para la optimización de carteras (minimizar $\sigma_p$ para un $R_p$ objetivo)
- La [Diversificación](../../portfolio-theory/diversification.md) reduce la volatilidad de la cartera cuando las correlaciones entre activos son menores que 1

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "Volatilidad ≠ Riesgo"

    La volatilidad trata por igual los movimientos al alza y a la baja. Un activo que con frecuencia tiene picos al alza tiene alta volatilidad, pero puede ser muy atractivo. Para una medida centrada en las caídas, utilice el [ratio de Sortino](sortino-ratio.md) o la [caída máxima](max-drawdown.md).

!!! warning "No normalidad"

    Los rendimientos financieros suelen tener:

    - **Colas gruesas** (más eventos extremos de los que predice una distribución normal)
    - **Asimetría negativa** (las caídas grandes son más comunes que las ganancias grandes)
    - **Agrupamiento de volatilidad** (periodos tranquilos y turbulentos)

    La desviación estándar por sí sola no captura estas características.

---

## 🔗 Relacionado {: #related }

- 📐 **[ratio de Sharpe](sharpe-ratio.md)** — Utiliza la volatilidad como denominador de riesgo
- 📊 **[ratio de Sortino](sortino-ratio.md)** — Variante de volatilidad solo a la baja
- 📏 **[Bandas de Bollinger](../../technical-analysis/indicators/bollinger-bands.md)** — Envolvente de volatilidad en los gráficos
- 🔀 **[Diversificación](../../portfolio-theory/diversification.md)** — Reducir la volatilidad de la cartera
