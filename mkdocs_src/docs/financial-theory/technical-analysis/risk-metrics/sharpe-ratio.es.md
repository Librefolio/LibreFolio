# 📐 Ratio de Sharpe

El ratio de Sharpe es la métrica de **rendimiento ajustado al riesgo** más utilizada. Mide cuánto rendimiento excedente recibe por cada unidad de volatilidad total.

---

## 🔢 Fórmula

$$
S = \frac{R_p - R_f}{\sigma_p}
$$

donde:

- $R_p$ = rendimiento de la cartera (anualizado)
- $R_f$ = tasa libre de riesgo (por ejemplo, la tasa de las letras del Tesoro)
- $\sigma_p$ = desviación estándar de la cartera (anualizada)

---

## 💡 Interpretación

| Ratio de Sharpe | Calidad |
|---|---|
| $< 0$ | La cartera tuvo un rendimiento inferior a la tasa libre de riesgo |
| $0 - 0.5$ | Rendimiento ajustado al riesgo subóptimo |
| $0.5 - 1.0$ | Aceptable |
| $1.0 - 2.0$ | Bueno |
| $> 2.0$ | Excelente (raro durante periodos prolongados) |

!!! example "Ejemplo numérico"

    Rendimiento de la cartera: 12%, Tasa libre de riesgo: 3%, Volatilidad: 15%

    $$S = \frac{0.12 - 0.03}{0.15} = 0.60$$

    Por cada 1% de volatilidad, la cartera obtuvo un 0.60% de rendimiento excedente.

---

## ⚙️ Anualización

Cuando se calcula a partir de rendimientos diarios:

$$
S_{annual} = S_{daily} \times \sqrt{252}
$$

donde 252 es el número típico de días bursátiles por año. Esto asume que los rendimientos son IID (independientes e idénticamente distribuidos), una aproximación que deja de ser válida en el caso de rendimientos autocorrelacionados.

---

## ⚠️ Limitaciones

### 📊 Penalización Simétrica

El ratio de Sharpe penaliza la **volatilidad alcista** tanto como la volatilidad bajista. Un activo que presenta picos alcistas frecuentes (¡lo cual es muy deseable!) tendrá un ratio de Sharpe menor que uno con el mismo rendimiento y menos movimiento alcista.

→ Para distribuciones de rendimiento asimétricas, prefiera el **[Ratio de Sortino](sortino-ratio.md)**.

### 📈 Sensibilidad a Valores Atípicos

Algunos rendimientos extremos pueden distorsionar significativamente la desviación estándar, haciendo que el ratio de Sharpe sea inestable en periodos de tiempo cortos.

### 🔄 Dependencia del Periodo de Tiempo

El ratio de Sharpe puede variar drásticamente dependiendo de la ventana de análisis. Una estrategia con un ratio de Sharpe excelente a 5 años puede tener un ratio de Sharpe deficiente a 1 año (o viceversa).

---

## 🔗 Relacionado

- 📊 **[Ratio de Sortino](sortino-ratio.md)** — Variante enfocada solo en la volatilidad bajista
- 📊 **[Volatilidad](volatility.md)** — El denominador del ratio de Sharpe
- 📈 **[Rendimientos](../../fundamentals/returns.md)** — El numerador del ratio de Sharpe
