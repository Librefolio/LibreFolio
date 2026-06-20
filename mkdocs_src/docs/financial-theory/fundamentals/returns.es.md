# 📈 Rendimientos y Tasas de Crecimiento

Esta página cubre los fundamentos matemáticos de los **rendimientos de inversión**: cómo medir, comparar y anualizar las tasas de crecimiento. Estos conceptos se utilizan en todas las herramientas de medición y analítica de cartera de LibreFolio.

---

## 📊 Rendimiento Simple (Discreto)

El **rendimiento simple** durante un periodo es el cambio porcentual:

$$
R_{simple} = \frac{P_{end} - P_{start}}{P_{start}} = \frac{P_{end}}{P_{start}} - 1
$$

!!! example

    Si el EUR/USD se mueve de 1.10 a 1.14:

    $$R = \frac{1.14 - 1.10}{1.10} = 0.0364 = 3.64\%$$

### 📊 Propiedades

- **Intuitivo**: representa directamente "cuánto se ganó/perdió"
- **No es aditivo en el tiempo**: no se pueden sumar simplemente los rendimientos simples de varios periodos para obtener el rendimiento total
- **Capitalización**: los rendimientos de periodos múltiples deben **multiplicarse**, no sumarse

$$
R_{total} = (1 + R_1)(1 + R_2) \cdots (1 + R_n) - 1
$$

---

## 📐 Rendimiento Logarítmico (Continuo)

El **rendimiento logarítmico** es el logaritmo natural de la relación de precios:

$$
r_{log} = \ln\left(\frac{P_{end}}{P_{start}}\right) = \ln(P_{end}) - \ln(P_{start})
$$

### 📊 Propiedades

- **Aditivo en el tiempo**: el rendimiento logarítmico total = la suma de los rendimientos logarítmicos de los subperiodos

$$
r_{total} = r_1 + r_2 + \cdots + r_n
$$

- **Simétrico**: un movimiento del +5% seguido de un movimiento del −5% regresa exactamente al punto de partida
- **Aproximadamente igual** al rendimiento simple para valores pequeños: $r_{log} \approx R_{simple}$ cuando $R_{simple}$ es pequeño

### 🔄 Conversión

$$
r_{log} = \ln(1 + R_{simple}) \qquad R_{simple} = e^{r_{log}} - 1
$$

---

## 📅 Rendimiento Anualizado

Para comparar rendimientos entre diferentes periodos de tiempo, los **anualizamos**, proyectando la tasa de crecimiento observada a un año completo.

### 📈 Tasa de Crecimiento Anual Compuesta (CAGR)

El método de anualización más común. Dado un rendimiento total durante $d$ días naturales:

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

Esto es lo que muestra la [herramienta de medida](../../user/fx/detail/measures.md) de LibreFolio.

!!! example

    El EUR/USD se mueve de 1.10 a 1.14 en 90 días:

    $$R_{annual} = \left(\frac{1.14}{1.10}\right)^{365/90} - 1 = (1.0364)^{4.056} - 1 \approx 15.5\%$$

### 📐 Rendimiento Logarítmico Anualizado

Para los rendimientos logarítmicos, la anualización es simplemente un escalado:

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

Esta linealidad es una de las ventajas clave de los rendimientos logarítmicos en las finanzas cuantitativas.

---

## 🔄 Relación Entre Rendimientos Simples y Logarítmicos

| Propiedad | Rendimiento Simple $R$ | Rendimiento Log $r$ |
|----------|:---:|:---:|
| **Capitalización** | Multiplicativa: $(1+R_1)(1+R_2)$ | Aditiva: $r_1 + r_2$ |
| **Simetría** | Asimétrica: +10% luego −10% ≠ 0 | Simétrica: +10% luego −10% = 0 |
| **Anualización** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Rendimientos de cartera** | La suma ponderada funciona ✅ | La suma ponderada no funciona ❌ |
| **Series temporales** | No es aditiva ❌ | Aditiva ✅ |
| **Interpretación** | "Gané el 5%" | "La tasa de crecimiento logarítmico fue 0.0488" |

!!! tip " ¿Cuándo usar cuál?"

    - **Rendimientos simples** para reportar a los usuarios y calcular rendimientos a nivel de cartera
    - **Rendimientos logarítmicos** para análisis estadísticos, estimación de volatilidad y modelos de series temporales

---

## 📏 Convenciones de Recuento de Días

El número de días $d$ puede computarse de manera diferente según la convención:

- **Actual/365**: Días naturales (lo que utiliza LibreFolio)
- **Actual/360**: Días naturales sobre un año de 360 días (común en mercados monetarios)
- **30/360**: Asume meses de 30 días y un año de 360 días

Para más detalles, consulte [Convenciones de Recuento de Días](day-count.md).

---

## 💰 Métodos de Rendimiento de Cartera

Cuando una cartera tiene **flujos de caja** (depósitos, retiros), una sola fórmula de rendimiento no es suficiente, ya que las inyecciones o retiros de capital diluirían o inflarían artificialmente el rendimiento porcentual.

Para solucionar esto, se utilizan métricas de rendimiento avanzadas:
- **TWRR (Time-Weighted Rate of Return):** Aísla el rendimiento de los activos, ignorando el momento de los flujos de caja del inversor.
- **MWRR (Money-Weighted Rate of Return):** Mide el rendimiento personal del inversor, teniendo en cuenta el momento de los flujos de caja.

Para profundizar en cómo funcionan estas métricas, por qué difieren y cómo las utiliza LibreFolio, consulte el capítulo dedicado a [Métricas de Rendimiento](../technical-analysis/performance-metrics/index.md).

---

## ⚠️ Errores Comunes

1. **Periodos muy cortos**: Anualizar un rendimiento de 3 días puede producir cifras engañosas (por ejemplo, un movimiento del 0.1% en 3 días → 12.5% anualizado)
2. **Precios negativos**: Los rendimientos logarítmicos no están definidos para valores negativos, aunque esto no es un problema para los tipos de cambio
3. **Frecuencia de capitalización**: El CAGR asume una capitalización continua; los instrumentos del mundo real pueden capitalizar diaria, mensual o trimestralmente
