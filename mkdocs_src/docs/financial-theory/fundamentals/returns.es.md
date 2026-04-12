# 📈 Retornos y Tasas de Crecimiento

Esta página cubre los fundamentos matemáticos de los **retornos de inversión**: cómo medir, comparar y anualizar las tasas de crecimiento. Estos conceptos se utilizan en todas las herramientas de medición y análisis de cartera de LibreFolio.

---

## 📊 Retorno Simple (Discreto)

El **retorno simple** durante un período es el cambio porcentual:

$$
R_{simple} = \frac{P_{end} - P_{start}}{P_{start}} = \frac{P_{end}}{P_{start}} - 1
$$

!!! example

    Si el EUR/USD se mueve de 1.10 a 1.14:

    $$R = \frac{1.14 - 1.10}{1.10} = 0.0364 = 3.64\%$$

### 📊 Propiedades

- **Intuitivo**: representa directamente la ganancia o pérdida
- **No es aditivo**: no se pueden sumar simplemente los retornos simples de varios períodos para obtener el retorno total
- **Capitalización**: los retornos de múltiples períodos deben **multiplicarse**, no sumarse

$$
R_{total} = (1 + R_1)(1 + R_2) \cdots (1 + R_n) - 1
$$

---

## 📐 Retorno Logarítmico (Continuo)

El **retorno logarítmico** es el logaritmo natural de la relación de precios:

$$
r_{log} = \ln\left(\frac{P_{end}}{P_{start}}\right) = \ln(P_{end}) - \ln(P_{start})
$$

### 📊 Propiedades

- **Aditivo en el tiempo**: el retorno logarítmico total = la suma de los retornos logarítmicos de los subperíodos

$$
r_{total} = r_1 + r_2 + \cdots + r_n
$$

- **Simétrico**: un movimiento de +5% seguido de un movimiento de −5% regresa exactamente al punto de partida
- **Aproximadamente igual** al retorno simple para valores pequeños: $r_{log} \approx R_{simple}$ cuando $R_{simple}$ es pequeño

### 🔄 Conversión

$$
r_{log} = \ln(1 + R_{simple}) \qquad R_{simple} = e^{r_{log}} - 1
$$

---

## 📅 Retorno Anualizado

Para comparar retornos en diferentes períodos de tiempo, los **anualizamos**, proyectando la tasa de crecimiento observada a un año completo.

### 📈 Tasa de Crecimiento Anual Compuesta (CAGR)

El método de anualización más común. Dado un retorno total durante $d$ días naturales:

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

Esto es lo que muestra la [herramienta de Métricas](../../user/fx/detail/measures.md) de LibreFolio.

!!! example

    El EUR/USD se mueve de 1.10 a 1.14 en 90 días:

    $$R_{annual} = \left(\frac{1.14}{1.10}\right)^{365/90} - 1 = (1.0364)^{4.056} - 1 \approx 15.5\%$$

### 📐 Retorno Logarítmico Anualizado

Para los retornos logarítmicos, la anualización es simplemente un escalado:

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

Esta linealidad es una de las ventajas clave de los retornos logarítmicos en las finanzas cuantitativas.

---

## 🔄 Relación Entre Retornos Simples y Logarítmicos

| Propiedad | Retorno Simple $R$ | Retorno Logarítmico $r$ |
|----------|:---:|:---:|
| **Capitalización** | Multiplicativa: $(1+R_1)(1+R_2)$ | Aditiva: $r_1 + r_2$ |
| **Simetría** | Asimétrica: +10% luego −10% ≠ 0 | Simétrica: +10% luego −10% = 0 |
| **Anualización** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Retornos de cartera** | La suma ponderada funciona ✅ | La suma ponderada no funciona ❌ |
| **Series temporales** | No es aditiva ❌ | Aditiva ✅ |
| **Interpretación** | "Gané un 5%" | "La tasa de crecimiento logarítmico fue 0.0488" |

!!! tip "¿Cuándo usar cuál?"

    - **Retornos simples** para reportes a usuarios y para calcular retornos a nivel de cartera
    - **Retornos logarítmicos** para análisis estadísticos, estimación de volatilidad y modelos de series temporales

---

## 📏 Convenciones de Recuento de Días

El número de días $d$ puede calcularse de manera diferente según la convención:

- **Actual/365**: Días naturales (lo que utiliza LibreFolio)
- **Actual/360**: Días naturales sobre un año de 360 días (común en los mercados monetarios)
- **30/360**: Asume meses de 30 días y un año de 360 días

Para más detalles, consulte [Convenciones de Recuento de Días](day-count.md).

---

## ⚠️ Riesgos y errores comunes

1. **Períodos muy cortos**: Anualizar un retorno de 3 días puede producir cifras engañosas (por ejemplo, un movimiento de 0.1% en 3 días $\rightarrow$ 12.5% anualizado)
2. **Precios negativos**: Los retornos logarítmicos no están definidos para valores negativos; esto no es un problema para los tipos de cambio de FX
3. **Frecuencia de capitalización**: El CAGR asume una capitalización continua; los instrumentos del mundo real pueden capitalizar diaria, mensual o trimestralmente
