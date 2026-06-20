# 📉 Máximo Drawdown

El Máximo Drawdown (MDD) mide la **mayor caída desde el pico hasta el valle** en el valor de la cartera antes de que se establezca un nuevo pico. Responde a la pregunta: *"¿Cuál fue la peor pérdida que podría haber experimentado un inversor?"*

---

## 🔢 Fórmula

$$
MDD = \frac{Trough - Peak}{Peak} = \min_{t} \left( \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau} \right)
$$

donde $V_t$ es el valor de la cartera en el momento $t$.

El drawdown en cualquier punto $t$ es:

$$
DD_t = \frac{V_t - V_{peak}}{V_{peak}}
$$

El máximo drawdown es el valor mínimo (el más negativo) de $DD_t$ durante todo el periodo de observación.

---

## 💡 Interpretación

| Máximo Drawdown | Contexto típico |
|---|---|
| $-5\%$ a $-10\%$ | Corrección normal, cartera bien diversificada |
| $-10\%$ a $-20\%$ | Corrección significativa |
| $-20\%$ a $-30\%$ | Mercado bajista |
| $-30\%$ a $-50\%$ | Mercado bajista severo (2008, COVID-2020) |
| $> -50\%$ | Catastrófico (posiciones concentradas, crypto) |

!!! example "Ejemplo numérico"

    Secuencia de valor de la cartera: 100 → 120 → 90 → 110 → 130

    - Pico: 120
    - Valle: 90
    - MDD: $(90 - 120) / 120 = -25\%$
    - Recuperación: alcanzó 120 nuevamente, luego un nuevo máximo en 130

---

## ⏱️ Tiempo de recuperación

Una métrica igualmente importante es el **tiempo de recuperación** — cuánto tiempo se tarda en recuperarse del drawdown y alcanzar un nuevo pico:

$$
T_{recovery} = t_{new\_peak} - t_{trough}
$$

| Clase de activo | Tiempo de recuperación típico (tras un drawdown importante) |
|-------------|---------------------------------------------|
| Acciones EE. UU. (S&P 500) | 1-5 años |
| Bonos | Meses a 1-2 años |
| Crypto | Muy variable (meses a años) |

!!! warning "Asimetría de las pérdidas"

    Una pérdida del 50% requiere una **ganancia del 100%** para recuperarse:

    $$
    \text{Ganancia requerida} = \frac{1}{1 + MDD} - 1
    $$

    <div style="display: flex; justify-content: center;">

    | Pérdida | Ganancia requerida |
    |:----:|:-------------:|
    | -10% | +11.1% |
    | -25% | +33.3% |
    | -50% | +100% |
    | -75% | +300% |

    </div>

---

## 📊 Gráfico de Drawdown

Un gráfico de drawdown representa $DD_t$ a lo largo del tiempo. Siempre es cero o negativo, tocando el cero en cada nuevo pico. El valle más profundo es el máximo drawdown. Esta visualización facilita:

- Identificar el **momento** de los periodos más críticos
- Ver con qué frecuencia ocurren los drawdowns
- Comparar los patrones de recuperación entre diferentes estrategias

---

## 🔗 Relacionado

- 📊 **[Volatilidad](volatility.md)** — La desviación estándar no captura la severidad del drawdown
- 📐 **[Sharpe Ratio](sharpe-ratio.md)** — Rentabilidad ajustada al riesgo (utiliza la volatilidad, no el drawdown)
- 🔀 **[Diversificación](../../portfolio-theory/diversification.md)** — La herramienta principal para reducir el máximo drawdown
