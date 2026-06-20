# 📊 Ratio de Sortino

El ratio de Sortino es una modificación del ratio de Sharpe que solo penaliza la **volatilidad a la baja**. Reconoce que los inversores están preocupados primordialmente por las pérdidas, no por las sorpresas al alza.

---

## 🔢 Fórmula

$$
So = \frac{R_p - R_f}{\sigma_d}
$$

donde:

- $R_p$ = retorno de la cartera (anualizado)
- $R_f$ = tasa libre de riesgo (o retorno mínimo aceptable)
- $\sigma_d$ = **desviación a la baja** (anualizada)

### 📐 Desviación a la baja

$$
\sigma_d = \sqrt{\frac{1}{N} \sum_{i=1}^{N} \min(R_i - R_f, 0)^2}
$$

Solo los retornos **por debajo** del umbral contribuyen a la desviación a la baja. Los retornos por encima del umbral contribuyen con cero.

---

## 💡 Interpretación

| Ratio de Sortino | Calidad |
|---|---|
| $< 0$ | Retornos por debajo del umbral |
| $0 - 1.0$ | Retorno moderado ajustado al riesgo a la baja |
| $1.0 - 2.0$ | Bueno |
| $> 2.0$ | Excelente gestión del riesgo a la baja |

!!! example "Ejemplo numérico"

    Retorno de la cartera: 12%, Tasa libre de riesgo: 3%, Desviación a la baja: 10%

    $$So = \frac{0.12 - 0.03}{0.10} = 0.90$$

    Comparar con Sharpe (si total σ = 15%): $S = 0.60$. El Sortino es más alto porque se excluye la volatilidad al alza.

---

## 📊 Sharpe vs Sortino

| Aspecto | Sharpe | Sortino |
|--------|--------|---------|
| **Medida de riesgo** | Desviación estándar total | Solo desviación a la baja |
| **¿Penaliza el alza?** | Sí ❌ | No ✅ |
| **Ideal para** | Distribuciones de retorno simétricas | Retornos asimétricos / sesgados |
| **Ejemplo** | Índice de mercado amplio | Estrategias de opciones, carteras concentradas |

### 🔑 Cuándo preferir Sortino

- **Distribuciones sesgadas**: Estrategias que tienen ganancias ocasionales grandes pero pérdidas controladas
- **Carteras basadas en opciones**: Pagos inherentemente asimétricos
- **Acciones de crecimiento**: Tienden a tener distribuciones de retorno sesgadas positivamente
- **Cualquier inversor** que se preocupe más por el riesgo a la baja que por el riesgo total

---

## ⚠️ Limitaciones

!!! warning "Sesgo de muestra pequeña"

    La desviación a la baja requiere suficientes puntos de datos por debajo del umbral. Con pocos retornos negativos (por ejemplo, períodos cortos de mercado alcista), la estimación se vuelve poco fiable y el ratio de Sortino puede ser engañosamente alto.

---

## 🔗 Relacionado

- 📐 **[Ratio de Sharpe](sharpe-ratio.md)** — Variante de volatilidad total
- 📊 **[Volatilidad](volatility.md)** — Entendiendo la desviación estándar
- 📈 **[Máximo Drawdown](max-drawdown.md)** — Otra métrica enfocada en la baja
