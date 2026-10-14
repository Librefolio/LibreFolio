# 📐 Ratio de Sharpe

El ratio de Sharpe es la métrica de **rentabilidad ajustada al riesgo** más ampliamente utilizada. Mide cuánto exceso de rentabilidad se recibe por unidad de volatilidad total.

---

## 🔢 Fórmula {: #formula }

$$
S = \frac{R_p - R_f}{\sigma_p}
$$

donde:

- $R_p$ = rentabilidad de la cartera (anualizada)
- $R_f$ = tasa libre de riesgo (p. ej., la tasa de las letras del Tesoro)
- $\sigma_p$ = desviación estándar de la cartera (anualizada)

!!! info "Cómo entra la tasa en el cálculo"

    La tasa libre de riesgo se proporciona como una tasa **anual efectiva** y se convierte a una tasa **efectiva por período** antes de usarla:

    $$
    r_{period} = (1 + r_{annual})^{1/f} - 1
    $$

    donde $f$ es el mismo factor de anualización que escala la volatilidad, medido a partir de los datos observados — véase [Anualización](#annualization). Esa tasa por período se resta de la rentabilidad de cada período, y el exceso de rentabilidad resultante es la base sobre la que se construye el ratio. Compartir $f$ con la volatilidad mantiene el numerador y el denominador en el mismo período: aplicar una tasa de días naturales contra rentabilidades de días bursátiles subestimaría el cargo y, cuando la tasa es positiva, favorecería el ratio. La conversión tiene en cuenta la capitalización: un simple $r_{annual}/f$ trataría la tasa como si no se capitalizara a lo largo del año.

---

## 💡 Interpretación {: #interpretation }

| Ratio de Sharpe | Qué significa el valor |
|---|---|
| $< 0$ | La cartera rindió menos que la tasa libre de riesgo durante la ventana: el exceso de rentabilidad del numerador es negativo, por lo que ningún nivel de volatilidad puede hacer que el ratio sea positivo |
| $0 - 0.5$ | Menos de media unidad de exceso de rentabilidad por unidad de volatilidad: la cartera se movió mucho en relación con lo que ese movimiento generó |
| $0.5 - 1.0$ | Entre media unidad y una unidad de exceso de rentabilidad por unidad de volatilidad |
| $1.0 - 2.0$ | De una a dos unidades de exceso de rentabilidad por unidad de volatilidad: el exceso de rentabilidad fue mayor que la volatilidad que lo produjo |
| $> 2.0$ | Más de dos unidades de exceso de rentabilidad por unidad de volatilidad — poco frecuente en períodos largos, y bastante más frecuente en períodos cortos y favorables |

!!! warning "El mismo número no es la misma afirmación"

    Un ratio no significa nada si se desvincula de la ventana y de la clase de activo sobre la que se midió. Un tramo corto y favorable produce valores que un ciclo de mercado completo no sostendría, y las clases de activo con distintos ritmos de rentabilidad ocupan por construcción partes diferentes de la escala. Dos ratios solo son comparables cuando cubren el mismo período y se anualizaron con el mismo factor observado — véase [Anualización observada](observed-annualization.md). La tabla dice lo que el número *es*, no si el resultado fue bueno: ese juicio requiere el objetivo para el que se construyó la cartera.

!!! example "Ejemplo numérico"

    Rentabilidad de la cartera: 12 %, Tasa libre de riesgo: 3 %, Volatilidad: 15 %

    $$S = \frac{0.12 - 0.03}{0.15} = 0.60$$

    Por cada 1 % de volatilidad, la cartera obtuvo un 0,60 % de exceso de rentabilidad.

---

## ⚙️ Anualización {: #annualization }

Un ratio de Sharpe calculado sobre rentabilidades por período se escala a una cifra anual mediante la raíz cuadrada del número de períodos que contiene un año:

$$
S_{annual} = S_{period} \times \sqrt{f}
$$

El factor $f$ se **mide a partir de los datos observados** — el número de rentabilidades realmente utilizadas, reescalado a un año natural completo a lo largo del intervalo que abarcan:

$$
f = \frac{N \times 365}{D}
$$

donde $N$ es el número de rentabilidades por período y $D$ los días naturales que abarcan. La raíz cuadrada proviene de que la varianza se suma entre períodos independientes, por lo que el escalado asume que las rentabilidades son IID (independientes e idénticamente distribuidas) — una aproximación que deja de ser válida para rentabilidades autocorrelacionadas.

!!! info "√252 es un resultado, no una constante"

    Una acción con precio diario aporta aproximadamente 252 rentabilidades a lo largo de un año natural completo, de modo que $f \approx 252$ y el conocido $\sqrt{252}$ se recupera como resultado de la medición en lugar de estar escrito en ella. Un instrumento con precio cada día natural da $f \approx 365$, y un fondo con precio semanal, $f \approx 52$.

    → Véase **[Anualización observada](observed-annualization.md)** para la derivación y ejemplos resueltos.

---

## ⚠️ Limitaciones {: #limitations }

### 📊 Penalización simétrica {: #symmetric-penalty }

El ratio de Sharpe penaliza la **volatilidad al alza** tanto como la volatilidad a la baja. Un activo que repunta con frecuencia al alza (¡muy deseable!) tendrá un ratio de Sharpe más bajo que otro con la misma rentabilidad y menos movimiento al alza.

→ Para distribuciones de rentabilidad asimétricas, es preferible el **[ratio de Sortino](sortino-ratio.md)**.

### 📈 Sensibilidad a los valores atípicos {: #sensitivity-to-outliers }

Unas pocas rentabilidades extremas pueden distorsionar significativamente la desviación estándar, lo que hace que el ratio de Sharpe sea inestable para períodos de tiempo cortos.

### 🔄 Dependencia del período temporal {: #time-period-dependency }

El ratio de Sharpe puede variar drásticamente según la ventana de observación. Una estrategia con un excelente Sharpe a 5 años puede tener un pobre Sharpe a 1 año (o viceversa).

---

## 🔗 Relacionado {: #related }

- 📊 **[Ratio de Sortino](sortino-ratio.md)** — Variante únicamente a la baja
- 📊 **[Volatilidad](volatility.md)** — El denominador del ratio de Sharpe
- 📈 **[Rentabilidades](../../fundamentals/returns.md)** — El numerador del ratio de Sharpe
