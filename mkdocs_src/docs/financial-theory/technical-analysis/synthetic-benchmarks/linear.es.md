# 📈 Crecimiento Lineal

Un benchmark de crecimiento lineal representa el **interés simple**: el valor aumenta en una cantidad absoluta fija en cada período.

---

## 💡 Significado Financiero

Este modelo representa el escenario en el que **no reinvierte** las ganancias (dividendos, intereses, cupones): los pagos en efectivo se reciben pero se mantienen reservados, por lo que solo el capital original genera rendimientos.

Si, por el contrario, **reinvierte** esas ganancias —ya sea manualmente o automáticamente a través de instrumentos de acumulación (por ejemplo, ETFs de acumulación, que reinvierten los dividendos internamente y se benefician del [aplazamiento fiscal](../../fundamentals/taxation.md#tax-deferral-advantage))— debe esperar un **[crecimiento compuesto](compound.md)**, donde los rendimientos generan nuevos rendimientos.

En la práctica, la diferencia entre el crecimiento lineal y el compuesto se amplía drásticamente en horizontes temporales largos. Es por esto que el benchmark Lineal aparece como una línea recta, mientras que el benchmark Compuesto se curva hacia arriba exponencialmente.

!!! abstract "Plusvalías y pérdidas de capital"

    Cuando se vende un activo por encima de su precio de compra, la diferencia es una **plusvalía**;
    si es por debajo, una **pérdida de capital**. Cada jurisdicción tiene sus propias reglas respecto a las tasas impositivas,
    los umbrales del período de tenencia, la duración del arrastre de pérdidas y los métodos de emparejamiento
    (FIFO, LIFO, identificación específica). Para una descripción general teórica, consulte
    [Tributación y Eficiencia Fiscal](../../fundamentals/taxation.md).

---

## 🔢 Fórmula Matemática

$$
y(t) = y_0 \cdot (1 + r \cdot t)
$$

donde:

- $y_0$ es el valor inicial (primer punto de datos del gráfico),
- $r$ es la tasa de crecimiento anual (expresada como decimal, p. ej., 0.07 para el 7%),
- $t$ es el tiempo en años desde el inicio.

Esto es equivalente a la fórmula de **interés simple** $A = P(1 + rt)$, donde $t$ se expresa en años utilizando la [Convención de Conteo de Días](../../fundamentals/day-count.md) aplicable.

---

## ⚙️ Parámetros

| Parámetro | Clave | Predeterminado | Descripción |
|---|---|---|---|
| Tasa Anual | `annualRate` | 5 | Tasa de crecimiento en porcentaje por año. |
| Desplazamiento | `offset` | 0 | Desplazamiento vertical como % del valor base. |

---

## 🔍 Interpretación

La línea es perfectamente recta en una escala lineal. Cualquier punto donde el precio actual esté *por encima* de la línea significa que el activo ha superado el objetivo; cualquier punto *por debajo* significa que el rendimiento ha sido inferior. Debido a que el crecimiento es aditivo, la línea se curva hacia abajo en una escala logarítmica, lo que facilita distinguirla visualmente del crecimiento compuesto.

:material-link: [Interés Simple en Wikipedia](https://en.wikipedia.org/wiki/Interest#Simple_interest){ target="_blank" }
