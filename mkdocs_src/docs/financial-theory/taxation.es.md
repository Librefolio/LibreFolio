# 💰 Fiscalidad & Eficiencia Fiscal

Comprender la fiscalidad es esencial para maximizar los rendimientos de inversión a largo plazo. Esta página cubre los fundamentos teóricos — **no las reglas específicas de cada jurisdicción** — de cómo los impuestos interactúan con el crecimiento del portafolio.

!!! warning "No es asesoramiento financiero"

    LibreFolio no proporciona asesoramiento fiscal. Cada jurisdicción tiene reglas diferentes respecto a tipos impositivos, períodos de tenencia, compensación de pérdidas y métodos de asignación. Consulta a un profesional fiscal cualificado para tu situación específica.

---

## 📊 Ganancias y Pérdidas de Capital

Cuando vendes un activo, la diferencia entre el precio de venta y el precio de compra determina tu **ganancia** o **pérdida de capital**:

$$
\text{Ganancia de Capital} = P_{venta} - P_{compra} - \text{Comisiones}
$$

- **Ganancia de capital** ($> 0$): Vendiste por más de lo que pagaste → evento imponible en la mayoría de las jurisdicciones
- **Pérdida de capital** ($< 0$): Vendiste por menos de lo que pagaste → puede compensar ganancias futuras

### 🔄 Realizadas vs No Realizadas

| Tipo | Definición | Impacto Fiscal |
|------|-----------|---------------|
| **No realizadas** (ganancia/pérdida latente) | Activo aún mantenido; ganancia/pérdida existe solo en papel | No gravado (en la mayoría de las jurisdicciones) |
| **Realizadas** | Activo vendido; ganancia/pérdida se consolida | Típicamente desencadena un evento imponible |

Esta distinción es la base del **diferimiento fiscal** — al no vender, diferimos el evento imponible indefinidamente.

### 📋 Métodos de Asignación

Cuando has comprado el mismo activo varias veces a precios diferentes, ¿qué compra se asocia a una venta?

| Método | Regla | Efecto |
|--------|-------|--------|
| **FIFO** (First In, First Out) | Las participaciones más antiguas se venden primero | Valor predeterminado más común |
| **LIFO** (Last In, First Out) | Las participaciones más recientes se venden primero | Puede minimizar/maximizar ganancias |
| **Identificación Específica** | Tú eliges qué lote vender | Máxima optimización fiscal |

!!! info "LibreFolio usa FIFO"

    LibreFolio calcula las ganancias de capital utilizando la asignación **FIFO** en tiempo de ejecución. La asignación se calcula bajo demanda, no se almacena en la base de datos.

---

## 🔄 Compensación de Pérdidas

La mayoría de las jurisdicciones permiten **compensar** pérdidas de capital con ganancias futuras:

$$
\text{Ganancia Imponible}_t = \max(0, \text{Ganancias Realizadas}_t - \text{Pérdidas Compensables}_{t-1})
$$

Parámetros clave que varían según la jurisdicción:

- ⏳ **Duración**: Por cuánto tiempo las pérdidas pueden compensarse (ej. 4 años en Italia, ilimitado en Alemania, 7 años en EE.UU. para ciertos tipos)
- 📊 **Alcance**: Si las pérdidas de una clase de activo pueden compensar ganancias de otra
- 🚫 **Reglas de venta ficticia**: Restricciones sobre la recompra de un activo vendido en un plazo corto para reclamar la pérdida

---

## ⏳ Ventaja del Diferimiento Fiscal { #tax-deferral-advantage }

Uno de los conceptos más poderosos en la inversión fiscalmente eficiente es **diferir** el evento imponible el mayor tiempo posible. Las matemáticas favorecen fuertemente el diferimiento:

### 📐 La Fórmula

Compara dos escenarios a lo largo de $n$ años con rendimiento anual $r$ y tipo impositivo $\tau$:

**Escenario A — Impuesto anual** (ej. fondo de distribución):

$$
V_A = P \cdot (1 + r \cdot (1 - \tau))^n
$$

**Escenario B — Impuesto al final** (ej. fondo de acumulación):

$$
V_B = P \cdot (1 + r)^n - \tau \cdot [P \cdot (1 + r)^n - P] = P \cdot [(1 + r)^n \cdot (1 - \tau) + \tau]
$$

### 📊 Ejemplo Numérico

Con $P = 10.000$, $r = 7\%$, $\tau = 26\%$, $n = 20$ años:

| Escenario | Valor Final | Rendimiento Efectivo |
|-----------|------------|---------------------|
| Impuesto anual | 28.398 € | 5,18 % p.a. |
| Impuesto al final | 31.616 € | 5,93 % p.a. |
| **Ventaja del diferimiento** | **+3.218 €** | **+0,75 % p.a.** |

La ventaja crece exponencialmente con el tiempo — a lo largo de 30 años, la diferencia supera los 8.000 € sobre la misma inversión de 10.000 €.

---

## 📦 Instrumentos de Acumulación vs Distribución

Esta ventaja del diferimiento se manifiesta directamente en la elección entre vehículos de inversión de acumulación y distribución:

### 📈 Acumulación (ej. ETF Acc)

- Los dividendos se **reinvierten internamente** por el fondo
- **Ningún evento imponible** hasta que vendas las participaciones del fondo
- Pleno beneficio del [crecimiento compuesto](synthetic-benchmarks.md#compound-growth) sobre el importe bruto de impuestos
- Ideal para inversores a largo plazo que buscan máximo crecimiento

### 💵 Distribución (ej. ETF Dist)

- Los dividendos se **pagan** periódicamente
- Cada distribución es un **evento imponible** (gravado inmediatamente)
- Recibes efectivo pero pierdes el beneficio de la capitalización sobre la parte gravada
- Útil si necesitas ingresos de tus inversiones

### 🔗 Conexión con los Modelos de Crecimiento

- **[Crecimiento Lineal](synthetic-benchmarks.md#linear-growth)** aproxima el comportamiento cuando los dividendos se reciben pero **no se reinvierten** — el crecimiento es aditivo
- **[Crecimiento Compuesto](synthetic-benchmarks.md#compound-growth)** representa el caso ideal con reinversión completa — el crecimiento es multiplicativo y se beneficia más del diferimiento fiscal

---

## ⚠️ Consideraciones Específicas por Jurisdicción

Cada país tiene su propio marco fiscal. Parámetros clave que varían:

| Parámetro | Ejemplos |
|-----------|---------|
| **Tipo impositivo sobre ganancias de capital** | 26 % (Italia), 25 % (Alemania), 0-20 % (EE.UU., según período de tenencia) |
| **Beneficios por período de tenencia** | Algunos países reducen los tipos para tenencias a largo plazo |
| **Duración de la compensación de pérdidas** | 4 años (Italia), ilimitado (Alemania), 7 años (EE.UU. para algunos tipos) |
| **Tratados de doble imposición** | Afectan a los dividendos de acciones extranjeras |
| **Exenciones fiscales** | Umbrales anuales por debajo de los cuales las ganancias no tributan |
| **Reglas específicas para criptomonedas** | En rápida evolución; a menudo tratadas de forma diferente a los activos tradicionales |

!!! abstract "El papel de LibreFolio"

    LibreFolio rastrea tus transacciones y calcula las ganancias/pérdidas de capital realizadas usando la asignación FIFO. Proporciona la **base de datos** para la declaración fiscal, pero no genera declaraciones fiscales ni aplica reglas específicas de jurisdicción. Exporta los datos de tus transacciones y consulta a un profesional fiscal.

---

## 🔗 Relacionado

- 📈 **[Rendimientos y Tasas de Crecimiento](returns.md)** — Cómo medir y anualizar rendimientos
- 🎯 **[Benchmarks Sintéticos](synthetic-benchmarks.md)** — Visualización de crecimiento lineal vs compuesto
- 📅 **[Convenciones de Conteo de Días](day-count.md)** — Cómo los períodos temporales afectan los cálculos

