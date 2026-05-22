# 📈 Rentabilidades y Tasas de Crecimiento

Esta página cubre los fundamentos matemáticos de los **rendimientos de inversión**: cómo medir, comparar y anualizar las tasas de crecimiento. Estos conceptos se utilizan en todas las herramientas de medición y análisis de cartera de LibreFolio.

---

## 📊 Rentabilidad Simple (Discreta)

La **rentabilidad simple** durante un periodo es el cambio porcentual:

$$
R_{simple} = \frac{P_{end} - P_{start}}{P_{start}} = \frac{P_{end}}{P_{start}} - 1
$$

!!! example

    Si el EUR/USD se mueve de 1.10 a 1.14:

    $$R = \frac{1.14 - 1.10}{1.10} = 0.0364 = 3.64\%$$

### 📊 Propiedades

- **Intuitiva**: representa directamente "cuánto ganaste/perdiste"
- **No es aditiva**: no se pueden sumar simplemente las rentabilidades simples de varios periodos para obtener la rentabilidad total
- **Capitalización**: las rentabilidades de múltiples periodos deben **multiplicarse**, no sumarse

$$
R_{total} = (1 + R_1)(1 + R_2) \cdots (1 + R_n) - 1
$$

---

## 📐 Rentabilidad Logarítmica (Continua)

La **rentabilidad logarítmica** es el logaritmo natural de la razón de precios:

$$
r_{log} = \ln\left(\frac{P_{end}}{P_{start}}\right) = \ln(P_{end}) - \ln(P_{start})
$$

### 📊 Propiedades

- **Aditiva en el tiempo**: la rentabilidad logarítmica total = suma de las rentabilidades logarítmicas de los subperiodos

$$
r_{total} = r_1 + r_2 + \cdots + r_n
$$

- **Simétrica**: un movimiento de +5% seguido de un movimiento de −5% regresa exactamente al punto de partida
- **Aproximadamente igual** a la rentabilidad simple para valores pequeños: $r_{log} \approx R_{simple}$ cuando $R_{simple}$ es pequeño

### 🔄 Conversión

$$
r_{log} = \ln(1 + R_{simple}) \qquad R_{simple} = e^{r_{log}} - 1
$$

---

## 📅 Rentabilidad Anualizada

Para comparar rentabilidades en diferentes periodos de tiempo, las **anualizamos**, proyectando la tasa de crecimiento observada a un año completo.

### 📈 Tasa de Crecimiento Anual Compuesto (CAGR)

El método de anualización más común. Dada una rentabilidad total durante $d$ días naturales:

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

Esto es lo que muestra la [herramienta de medida](../../user/fx/detail/measures.md) de LibreFolio.

!!! example

    El EUR/USD se mueve de 1.10 a 1.14 en 90 días:

    $$R_{annual} = \left(\frac{1.14}{1.10}\right)^{365/90} - 1 = (1.0364)^{4.056} - 1 \approx 15.5\%$$

### 📐 Rentabilidad Logarítmica Anualizada

Para las rentabilidades logarítmicas, la anualización es simplemente un escalado:

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

Esta linealidad es una de las ventajas clave de las rentabilidades logarítmicas en las finanzas cuantitativas.

---

## 🔄 Relación Entre Rentabilidades Simples y Logarítmicas

| Propiedad | Rentabilidad Simple $R$ | Rentabilidad Logarítmica $r$ |
|----------|:---:|:---:|
| **Capitalización** | Multiplicativa: $(1+R_1)(1+R_2)$ | Aditiva: $r_1 + r_2$ |
| **Simetría** | Asimétrica: +10% luego −10% ≠ 0 | Simétrica: +10% luego −10% = 0 |
| **Anualización** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Rentabilidades de cartera** | La suma ponderada funciona ✅ | La suma ponderada no funciona ❌ |
| **Series temporales** | No es aditiva ❌ | Aditiva ✅ |
| **Interpretación** | "Gané un 5%" | "La tasa de crecimiento logarítmico fue 0.0488" |

!!! tip "¿Cuándo usar cuál?"

    - **Rentabilidades simples** para informes a usuarios y para calcular rentabilidades a nivel de cartera
    - **Rentabilidades logarítmicas** para análisis estadísticos, estimación de volatilidad y modelos de series temporales

---

## 📏 Convenciones de Recuento de Días

El número de días $d$ puede calcularse de forma diferente según la convención:

- **Actual/365**: Días naturales (lo que utiliza LibreFolio)
- **Actual/360**: Días naturales sobre un año de 360 días (común en mercados monetarios)
- **30/360**: Asume meses de 30 días y un año de 360 días

Para más detalles, consulte [Convenciones de Recuento de Días](day-count.md).

---

## 💰 Métodos de Rentabilidad de Cartera

Cuando una cartera tiene **flujos de efectivo** (depósitos, retiros), una única fórmula de rentabilidad no es suficiente. Existen dos métodos para aislar el rendimiento de los efectos de los flujos de efectivo:

### ⏱️ Rentabilidad Ponderada en el Tiempo (TWR)

Elimina el efecto de los flujos de efectivo calculando rentabilidades de subperiodos entre cada evento de flujo y encadenándolas:

$$
R_{TWR} = \prod_{i=1}^{n} (1 + r_i) - 1
$$

- Mide el **rendimiento puro de la cartera** independientemente del momento de los depósitos/retiros
- Utilizada por gestores de fondos para benchmarking (conforme a GIPS)
- No se ve afectada por el comportamiento del inversor (añadir dinero en los picos, retirar en los mínimos)

### 💵 Rentabilidad Ponderada por el Dinero (MWR / IRR)

Toma en cuenta el **momento y el tamaño** de los flujos de efectivo: la tasa interna de retorno que establece el VAN de todos los flujos en cero:

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{t_i}}
$$

donde $CF_i$ es cada flujo de efectivo (depósitos positivos, retiros negativos, valor final de la cartera positivo).

- Mide la **experiencia específica del inversor** (su rentabilidad real dado el momento en que añadió/retiró efectivo)
- Penaliza el mal timing (depositar en máximos, retirar en mínimos)
- Utilizada para el rendimiento de carteras personales

!!! info "¿Cuál utiliza LibreFolio?"

    LibreFolio calculará tanto la TWR como la MWR en el panel de control de análisis de la cartera. TWR para la comparación con benchmarks, MWR para la evaluación del rendimiento personal.

---

## ⚠️ Errores Comunes

1. **Periodos muy cortos**: Anualizar la rentabilidad de 3 días puede producir cifras engañosas (por ejemplo, un movimiento de 0.1% en 3 días → 12.5% anualizado)
2. **Precios negativos**: Las rentabilidades logarítmicas no están definidas para valores negativos; esto no es un problema para los tipos de cambio
3. **Frecuencia de capitalización**: El CAGR asume una capitalización continua; los instrumentos del mundo real pueden capitalizar diaria, mensual o trimestralmente
