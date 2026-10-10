# 📈 Rentabilidades y tasas de crecimiento

Esta página cubre los fundamentos matemáticos de las **rentabilidades de las inversiones** — cómo medir, comparar y anualizar las tasas de crecimiento. Estos conceptos se utilizan en todas las herramientas de medición y el análisis de carteras de LibreFolio.

---

## 📊 Rentabilidad simple (discreta)

La **rentabilidad simple** durante un período es el cambio porcentual:

$$
R_{simple} = \frac{P_{end} - P_{start}}{P_{start}} = \frac{P_{end}}{P_{start}} - 1
$$

!!! example

    Si el EUR/USD pasa de 1.10 a 1.14:

    $$R = \frac{1.14 - 1.10}{1.10} = 0.0364 = 3.64\%$$

### 📊 Propiedades

- **Intuitiva**: representa directamente “cuánto has ganado/perdido”
- **No aditiva**: no puedes simplemente sumar rentabilidades simples entre períodos para obtener la rentabilidad total
- **Composición**: las rentabilidades de múltiples períodos deben **multiplicarse**, no sumarse

$$
R_{total} = (1 + R_1)(1 + R_2) \cdots (1 + R_n) - 1
$$

---

## 📐 Rentabilidad logarítmica (continua)

La **rentabilidad logarítmica** es el logaritmo natural del cociente de precios:

$$
r_{log} = \ln\left(\frac{P_{end}}{P_{start}}\right) = \ln(P_{end}) - \ln(P_{start})
$$

### 📊 Propiedades

- **Aditiva a lo largo del tiempo**: rentabilidad logarítmica total = suma de las rentabilidades logarítmicas de los subperíodos

$$
r_{total} = r_1 + r_2 + \cdots + r_n
$$

- **Simétrica**: un movimiento de +5% seguido de un movimiento de −5% vuelve exactamente al punto de partida
- **Aproximadamente igual** a la rentabilidad simple para valores pequeños: $r_{log} \approx R_{simple}$ cuando $R_{simple}$ es pequeño

### 🔄 Conversión

$$
r_{log} = \ln(1 + R_{simple}) \qquad R_{simple} = e^{r_{log}} - 1
$$

---

## 📅 Rentabilidad anualizada

Para comparar rentabilidades entre diferentes períodos de tiempo, las **anualizamos** — proyectando la tasa de crecimiento observada a un año completo.

### 📈 Tasa de crecimiento anual compuesta (CAGR)

El método de anualización más común. Dada una rentabilidad total durante $d$ días naturales:

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

Esto es lo que muestra la [herramienta Medidas](../../user/fx/detail/measures.md) de LibreFolio.

!!! example

    El EUR/USD pasa de 1.10 a 1.14 en 90 días:

    $$R_{annual} = \left(\frac{1.14}{1.10}\right)^{365/90} - 1 = (1.0364)^{4.056} - 1 \approx 15.5\%$$

### 📐 Rentabilidad logarítmica anualizada

Para las rentabilidades logarítmicas, la anualización es simplemente un escalado:

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

Esta linealidad es una de las ventajas clave de las rentabilidades logarítmicas en finanzas cuantitativas.

---

## 🔄 Relación entre rentabilidades simples y logarítmicas

| Propiedad | Rentabilidad simple $R$ | Rentabilidad logarítmica $r$ |
|----------|:---:|:---:|
| **Composición** | Multiplicativa: $(1+R_1)(1+R_2)$ | Aditiva: $r_1 + r_2$ |
| **Simetría** | Asimétrica: +10% luego −10% ≠ 0 | Simétrica: +10% luego −10% = 0 |
| **Anualización** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Rentabilidades de cartera** | La suma ponderada funciona ✅ | La suma ponderada no funciona ❌ |
| **Series temporales** | No aditiva ❌ | Aditiva ✅ |
| **Interpretación** | “Gané un 5%” | “La tasa de crecimiento logarítmica fue 0,0488” |

!!! tip "¿Cuándo usar cada una?"

    - **Rentabilidades simples** para informar a los usuarios y calcular rentabilidades a nivel de cartera
    - **Rentabilidades logarítmicas** para análisis estadístico, estimación de volatilidad y modelos de series temporales

---

## 🔁 Rentabilidad móvil {: #rolling-return }

Una **rentabilidad móvil** es la rentabilidad simple de las secciones anteriores, medida en una ventana que se desplaza a lo largo de la serie: un valor por fecha, cada uno mirando hacia atrás durante el mismo intervalo. Dos funciones de la página de un activo la calculan, y difieren en cómo se cuenta el intervalo — en sesiones o en días naturales. El botón de guía 📖 en la tarjeta de la señal **Rentabilidad móvil** abre esta página.

### 📊 Sobre una ventana de sesiones {: #rolling-return-sessions }

La señal **Rentabilidad móvil** del panel de Señales, en la familia de riesgo, lee la serie de rentabilidades preparada del activo, en la moneda del gráfico: una rentabilidad simple por **sesión**, un día en el que el activo tiene una cotización propia. Un precio almacenado en un fin de semana o un día festivo del mercado que solo repite el cierre anterior no es una sesión. Con $V_t$ el valor en la sesión $t$ y $r_t = V_t / V_{t-1} - 1$, la rentabilidad móvil en una ventana de $w$ sesiones es

$$
R_t^{(w)} = \prod_{k=0}^{w-1} \left(1 + r_{t-k}\right) - 1 = \frac{V_t}{V_{t-w}} - 1
$$

calculada mediante logaritmos, $R_t^{(w)} = \exp\left(\sum_{k=0}^{w-1} \ln(1 + r_{t-k})\right) - 1$, para que la ventana pueda desplazarse paso a paso. La ventana $w$ — 30 por defecto, de 1 a 500 — cuenta observaciones de rentabilidad, no días naturales: 30 sesiones de un instrumento cotizado en días laborables abarcan unas seis semanas, 30 sesiones de uno cotizado todos los días abarcan 30 días. El primer valor aparece una vez que hay $w + 1$ valoraciones disponibles.

### 🗓️ Sobre una ventana de días naturales {: #rolling-return-calendar }

El modo **Rentabilidad móvil** del gráfico mide cada fecha contra el cierre exactamente $N$ días naturales antes. Con $\hat{P}(d)$ el cierre resuelto del día natural $d$ — el último cierre disponible en o antes de $d$, convertido a la moneda del gráfico, de modo que un fin de semana o un día festivo lee la sesión anterior — la rentabilidad del día $d$ es

$$
R^{[N]}(d) = \frac{\hat{P}(d)}{\hat{P}(d - N)} - 1
$$

Los preajustes **1W**, **1M**, **3M** y **1Y** establecen $N$ en 7, 30, 90 y 365 días; una ventana personalizada cuenta 7 días por semana, 30 por mes y 365 por año. Un punto se deja vacío, nunca se estima, cuando cualquiera de los extremos no tiene un cierre resuelto o tiene un cierre que no es positivo; cuando no se puede calcular ningún punto del rango, el resultado no está disponible. Cada punto informa la fecha de referencia que solicitó y las fechas del precio y del tipo de cambio realmente utilizados — véase el [Gráfico interactivo](../../user/assets/detail/chart.md#rolling-return).

### ⚖️ Sesiones o días naturales {: #sessions-or-calendar-days }

Ambas medidas son rentabilidades simples basadas únicamente en el precio: ninguna añade dividendos, cupones o flujos de caja, y ninguna está anualizada. Responden a preguntas ligeramente diferentes:

| | Ventana de sesiones | Ventana de días naturales |
|---|---|---|
| Intervalo | $w$ cotizaciones, cualquiera que sea el tiempo que cubran | exactamente $N$ días, cualquiera que sea el ritmo de cotización |
| Definida en | las sesiones del activo | cada fecha del gráfico |
| Comparación de dos activos | un $w$ igual puede significar intervalos diferentes | un $N$ igual siempre significa el mismo intervalo |
| Un día cerrado en cualquiera de los extremos | no puede ocurrir: solo se usan las sesiones | se resuelve al último cierre anterior |

Para comparar una rentabilidad móvil con otra en un intervalo diferente, anualízala con la fórmula CAGR anterior, siendo $d$ el intervalo en días naturales — teniendo en cuenta el error común sobre períodos muy cortos que figura a continuación.

---

## 📏 Convenciones de recuento de días

El número de días $d$ puede calcularse de forma diferente según la convención:

- **Actual/365**: días naturales (lo que usa LibreFolio)
- **Actual/360**: días naturales sobre un año de 360 días (común en mercados monetarios)
- **30/360**: asume meses de 30 días y un año de 360 días

Para más detalles, véase [Convenciones de recuento de días](day-count.md).

---

## 💰 Métodos de rentabilidad de cartera

Cuando una cartera tiene **flujos de caja** (depósitos, retiros), una única fórmula de rentabilidad no es suficiente, porque las aportaciones o retiros de capital diluirían o inflarían artificialmente la rentabilidad porcentual.

Para resolver esto, se utilizan métricas de rendimiento avanzadas:
- **TWRR (tasa de rentabilidad ponderada por tiempo):** aísla el rendimiento de los activos, ignorando el momento de los flujos de caja del inversor.
- **MWRR (tasa de rentabilidad ponderada por dinero):** mide el rendimiento personal del inversor, teniendo en cuenta el momento de los flujos de caja.

Para profundizar en cómo funcionan estas métricas, por qué difieren y cómo las utiliza LibreFolio, véase el capítulo dedicado de [Métricas de rendimiento](../technical-analysis/performance-metrics/index.md).

---

## ⚠️ Errores comunes

1. **Períodos muy cortos**: anualizar una rentabilidad de 3 días puede producir cifras engañosas (p. ej., un movimiento del 0,1 % en 3 días → 12,5 % anualizado)
2. **Precios negativos**: las rentabilidades logarítmicas no están definidas para valores negativos — no es un problema para los tipos de cambio
3. **Frecuencia de capitalización**: la CAGR asume capitalización continua; los instrumentos del mundo real pueden tener capitalización diaria, mensual o trimestral
