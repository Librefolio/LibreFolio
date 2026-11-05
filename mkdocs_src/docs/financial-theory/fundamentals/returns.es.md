# 📈 Rendimientos y tasas de crecimiento

Esta página abarca los fundamentos matemáticos de los **rendimientos de las inversiones**: cómo medir, comparar y anualizar las tasas de crecimiento. Estos conceptos se utilizan en las herramientas de medición y en los análisis de cartera de LibreFolio.

---

## 📊 Rendimiento simple (discreto)

El **rendimiento simple** durante un periodo es la variación porcentual:

$$
R_{simple} = \frac{P_{end} - P_{start}}{P_{start}} = \frac{P_{end}}{P_{start}} - 1
$$

!!! example

    Si EUR/USD pasa de 1.10 a 1.14:

    $$R = \frac{1.14 - 1.10}{1.10} = 0.0364 = 3.64\%$$

### 📊 Propiedades

- **Intuitivo**: representa directamente «cuánto ha ganado o perdido»
- **No aditivo**: no basta con sumar los rendimientos simples de distintos periodos para obtener el rendimiento total
- **Capitalización compuesta**: los rendimientos de varios periodos deben **multiplicarse**, no sumarse

$$
R_{total} = (1 + R_1)(1 + R_2) \cdots (1 + R_n) - 1
$$

---

## 📐 Rendimiento logarítmico (continuo)

El **rendimiento logarítmico** es el logaritmo natural de la relación de precios:

$$
r_{log} = \ln\left(\frac{P_{end}}{P_{start}}\right) = \ln(P_{end}) - \ln(P_{start})
$$

### 📊 Propiedades

- **Aditivo a lo largo del tiempo**: el rendimiento logarítmico total = suma de los rendimientos logarítmicos de los subperiodos

$$
r_{total} = r_1 + r_2 + \cdots + r_n
$$

- **Simétrico**: un movimiento de +5 % seguido de un movimiento de −5 % vuelve exactamente al punto de partida
- **Aproximadamente igual** al rendimiento simple para valores pequeños: $r_{log} \approx R_{simple}$ cuando $R_{simple}$ es pequeño

### 🔄 Conversión

$$
r_{log} = \ln(1 + R_{simple}) \qquad R_{simple} = e^{r_{log}} - 1
$$

---

## 📅 Rendimiento anualizado

Para comparar rendimientos entre distintos periodos de tiempo, los **anualizamos**: proyectamos la tasa de crecimiento observada a un año completo.

### 📈 Tasa de crecimiento anual compuesta (CAGR)

El método de anualización más común. Dado un rendimiento total en $d$ días naturales:

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

Esto es lo que muestra la [herramienta Medidas](../../user/fx/detail/measures.md) de LibreFolio.

!!! example

    EUR/USD pasa de 1.10 a 1.14 en 90 días:

    $$R_{annual} = \left(\frac{1.14}{1.10}\right)^{365/90} - 1 = (1.0364)^{4.056} - 1 \approx 15.5\%$$

### 📐 Rendimiento logarítmico anualizado

Para los rendimientos logarítmicos, la anualización consiste simplemente en escalar:

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

Esta linealidad es una de las ventajas clave de los rendimientos logarítmicos en las finanzas cuantitativas.

---

## 🔄 Relación entre rendimientos simples y logarítmicos

| Propiedad | Rendimiento simple $R$ | Rendimiento logarítmico $r$ |
|----------|:---:|:---:|
| **Capitalización compuesta** | Multiplicativa: $(1+R_1)(1+R_2)$ | Aditiva: $r_1 + r_2$ |
| **Simetría** | Asimétrica: +10 % y luego −10 % ≠ 0 | Simétrica: +10 % y luego −10 % = 0 |
| **Anualización** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Rendimientos de cartera** | La suma ponderada funciona ✅ | La suma ponderada no funciona ❌ |
| **Series temporales** | No aditivas ❌ | Aditivas ✅ |
| **Interpretación** | «Gané un 5 %» | «La tasa de crecimiento logarítmica fue 0,0488» |

!!! tip "¿Cuándo usar cada uno?"

    - **Rendimientos simples** para informar a los usuarios y calcular rendimientos a nivel de cartera
    - **Rendimientos logarítmicos** para análisis estadístico, estimación de volatilidad y modelos de series temporales

---

## 🔁 Rendimiento móvil {: #rolling-return }

Un **rendimiento móvil** es el rendimiento simple de las secciones anteriores, medido sobre una ventana que se desplaza a lo largo de la serie: un valor por fecha, cada uno de ellos retrocediendo el mismo intervalo. LibreFolio cuenta ese intervalo en **días naturales**, y un mismo cálculo sirve a dos funciones de la página de un activo: el modo **Rendimiento móvil** del gráfico y la señal **Rendimiento móvil** del panel de Señales, en la familia de riesgo, que dibuja la misma serie sobre los precios. El botón de guía 📖 de la tarjeta de la señal **Rendimiento móvil** abre esta página.

### 🗓️ Sobre una ventana de días naturales {: #rolling-return-calendar }

Cada fecha se mide con respecto al cierre exactamente $N$ días naturales antes. Si $\hat{P}(d)$ es el cierre resuelto del día natural $d$ —el último cierre disponible en o antes de $d$, convertido a la moneda del gráfico, de modo que un fin de semana o un día festivo toma la sesión anterior—, el rendimiento del día $d$ es

$$
R^{[N]}(d) = \frac{\hat{P}(d)}{\hat{P}(d - N)} - 1
$$

En el modo del gráfico, los preajustes **1W**, **1M**, **3M** y **1Y** fijan $N$ en 7, 30, 90 y 365 días, y una ventana personalizada cuenta 7 días por semana, 30 por mes y 365 por año; en la tarjeta de la señal, $N$ es la **Ventana**, un número entero de días —30 por defecto, como mínimo 1—. Un punto se deja vacío, nunca se estima, cuando alguno de los extremos no tiene un cierre resuelto o tiene un cierre que no es positivo; cuando no se puede calcular ningún punto del rango, el resultado no está disponible. El modo del gráfico también muestra, para cada punto, la fecha de referencia solicitada y las fechas del precio y del tipo de cambio realmente utilizados; consulte el [Gráfico interactivo](../../user/assets/detail/chart.md#rolling-return).

### ⚖️ Días naturales, no sesiones {: #sessions-or-calendar-days }

La ventana es un intervalo de tiempo, no un número de cotizaciones. Los demás indicadores del panel de Señales cuentan cotizaciones: los [indicadores técnicos](../technical-analysis/indicators/index.md) cuentan sesiones, los días con una cotización propia, y la volatilidad móvil, el ratio de Sharpe y la beta cuentan observaciones de rendimiento. Un mismo recuento puede entonces significar intervalos distintos —30 sesiones de un instrumento cotizado en días laborables abarcan unas seis semanas, 30 sesiones de uno cotizado todos los días abarcan 30 días—, mientras que una ventana de $N$ días naturales abarca exactamente $N$ días en todos los activos, sea cual sea su ritmo de cotización: dos rendimientos móviles con el mismo $N$ siempre comparan el mismo intervalo. El rendimiento se define en cada fecha del gráfico, y un día cerrado en cualquiera de los extremos se resuelve con el último cierre anterior a él.

El rendimiento móvil es un rendimiento simple basado únicamente en el precio: no añade dividendos, cupones ni flujos de caja, y no está anualizado. Para compararlo con un rendimiento de un intervalo distinto, anualícelo con la fórmula de la CAGR anterior, siendo $d$ igual a $N$, y tenga en cuenta la advertencia sobre periodos muy cortos que aparece más abajo.

---

## 📏 Convenciones de recuento de días

El número de días $d$ puede calcularse de distinta forma según la convención:

- **Actual/365**: días naturales (lo que utiliza LibreFolio)
- **Actual/360**: días naturales sobre un año de 360 días (habitual en los mercados monetarios)
- **30/360**: asume meses de 30 días y un año de 360 días

Para más detalles, consulte [Convenciones de recuento de días](day-count.md).

---

## 💰 Métodos de rendimiento de cartera

Cuando una cartera tiene **flujos de caja** (depósitos, retiros), una única fórmula de rendimiento no basta, porque las inyecciones o retiros de capital diluirían o inflarían artificialmente el rendimiento porcentual.

Para resolverlo, se utilizan métricas de rendimiento avanzadas:
- **TWRR (tasa de rendimiento ponderada por tiempo):** aísla el rendimiento de los activos, ignorando el momento en que se producen los flujos de caja del inversor.
- **MWRR (tasa de rendimiento ponderada por dinero):** mide el rendimiento personal del inversor, teniendo en cuenta el momento de los flujos de caja.

Para profundizar en cómo funcionan estas métricas, por qué difieren y cómo las utiliza LibreFolio, consulte el capítulo dedicado a [Métricas de rendimiento](../technical-analysis/performance-metrics/index.md).

---

## ⚠️ Advertencias

1. **Periodos muy cortos**: anualizar un rendimiento de 3 días puede producir cifras engañosas (p. ej., un movimiento del 0,1 % en 3 días → un 12,5 % anualizado)
2. **Precios negativos**: los rendimientos logarítmicos no están definidos para valores negativos; no es un problema para los tipos de cambio
3. **Frecuencia de capitalización**: la CAGR supone capitalización continua; los instrumentos del mundo real pueden capitalizar diariamente, mensualmente o trimestralmente
