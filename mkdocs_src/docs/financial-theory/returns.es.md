# 📈 Rendimientos y Tasas de Crecimiento

Esta página cubre los fundamentos matemáticos de los **rendimientos de inversión** — cómo medirlos, compararlos y anualizar las tasas de crecimiento. Estos conceptos se utilizan en todas las herramientas de medición FX y el análisis de carteras de LibreFolio.

---

## 📊 Rendimiento Simple (Discreto)

El **rendimiento simple** durante un período es el cambio porcentual:

$$
R_{simple} = \frac{P_{final} - P_{inicial}}{P_{inicial}} = \frac{P_{final}}{P_{inicial}} - 1
$$

!!! example

    Si EUR/USD pasa de 1.10 a 1.14:

    $$R = \frac{1.14 - 1.10}{1.10} = 0.0364 = 3.64\%$$

### 📊 Propiedades

- **Intuitivo**: representa directamente "cuánto ganó/perdió"
- **No es aditivo**: no se pueden sumar simplemente los rendimientos simples de varios períodos para obtener el rendimiento total
- **Capitalización**: los rendimientos de múltiples períodos deben **multiplicarse**, no sumarse

$$
R_{total} = (1 + R_1)(1 + R_2) \cdots (1 + R_n) - 1
$$

---

## 📐 Rendimiento Logarítmico (Continuo)

El **rendimiento logarítmico** es el logaritmo natural del ratio de precios:

$$
r_{log} = \ln\left(\frac{P_{final}}{P_{inicial}}\right) = \ln(P_{final}) - \ln(P_{inicial})
$$

### 📊 Propiedades

- **Aditivo en el tiempo**: el rendimiento logarítmico total = suma de los rendimientos logarítmicos de subperíodos

$$
r_{total} = r_1 + r_2 + \cdots + r_n
$$

- **Simétrico**: un movimiento de +5% seguido de −5% regresa exactamente al punto de partida
- **Aproximadamente igual** al rendimiento simple para valores pequeños: $r_{log} \approx R_{simple}$ cuando $R_{simple}$ es pequeño

### 🔄 Conversión

$$
r_{log} = \ln(1 + R_{simple}) \qquad R_{simple} = e^{r_{log}} - 1
$$

---

## 📅 Rendimiento Anualizado

Para comparar rendimientos de diferentes períodos, los **anualizamos** — proyectando la tasa de crecimiento observada a un año completo.

### 📈 Tasa de Crecimiento Anual Compuesta (CAGR)

El método de annualización más común. Dado un rendimiento total durante $d$ días naturales:

$$
R_{annual} = \left(\frac{P_{final}}{P_{inicial}}\right)^{365/d} - 1
$$

Esto es lo que muestra la herramienta [Medidas](../user/fx/detail/measures.md) de LibreFolio.

!!! example

    EUR/USD pasa de 1.10 a 1.14 en 90 días:

    $$R_{annual} = \left(\frac{1.14}{1.10}\right)^{365/90} - 1 = (1.0364)^{4.056} - 1 \approx 15.5\%$$

### 📐 Rendimiento Logarítmico Anualizado

Para rendimientos logarítmicos, la anualización es simplemente un escalado:

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

Esta linealidad es una de las ventajas clave de los rendimientos logarítmicos en finanzas cuantitativas.

---

## 🔄 Relación entre Rendimiento Simple y Logarítmico

| Propiedad | Rendimiento Simple $R$ | Rendimiento Logarítmico $r$ |
|----------|:---:|:---:|
| **Capitalización** | Multiplicativo: $(1+R_1)(1+R_2)$ | Aditivo: $r_1 + r_2$ |
| **Simetría** | Asimétrico: +10% luego −10% ≠ 0 | Simétrico: +10% luego −10% = 0 |
| **Anualización** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Rendimientos de cartera** | La suma ponderada funciona ✅ | La suma ponderada no funciona ❌ |
| **Series temporales** | No aditivo ❌ | Aditivo ✅ |
| **Interpretación** | "Gané un 5%" | "La tasa de crecimiento logarítmica fue 0.0488" |

!!! tip "¿Qué rendimiento usar en cada caso?"

    - **Rendimientos simples** para informar a usuarios y calcular rendimientos a nivel de cartera
    - **Rendimientos logarítmicos** para análisis estadístico, estimación de volatilidad y modelos de series temporales

---

## 📏 Convenciones de Conteo de Días

El número de días $d$ puede calcularse de forma diferente según la convención:

- **Actual/365**: días naturales (lo que usa LibreFolio)
- **Actual/360**: días naturales sobre un año de 360 días (común en mercados monetarios)
- **30/360**: asume meses de 30 días y año de 360 días

Para más detalles, ver [Convenciones de Conteo de Días](day-count.md).

---

## ⚠️ Advertencias

1. **Períodos muy cortos**: Anualizar un rendimiento de 3 días puede producir cifras engañosas (ej. un movimiento de 0.1% en 3 días → 12.5% anualizado)
2. **Precios negativos**: los rendimientos logarítmicos no están definidos para valores negativos — no es un problema para tipos de cambio FX
3. **Frecuencia de capitalización**: CAGR asume capitalización continua; los instrumentos reales pueden capitalizar diaria, mensual o trimestralmente
