# 💰 Fiscalidad y Eficiencia Fiscal

Comprender la fiscalidad es esencial para maximizar los retornos de inversión a largo plazo. Esta página cubre los fundamentos teóricos — **no reglas específicas de una jurisdicción** — sobre cómo interactúan los impuestos con el crecimiento de la cartera.

!!! warning "No es asesoramiento financiero"

    LibreFolio no proporciona asesoramiento fiscal. Cada jurisdicción tiene reglas diferentes con respecto a las tasas impositivas, los periodos de tenencia, la compensación de pérdidas y los métodos de emparejamiento. Consulte a un profesional fiscal cualificado para su situación específica.

---

## 📊 Plusvalías y Pérdidas de Capital

Cuando vende un activo, la diferencia entre el precio de venta y el precio de compra determina su **plusvalía** o **pérdida de capital**:

$$
\text{Capital Gain} = P_{sell} - P_{buy} - \text{Fees}
$$

- **Plusvalía** ($> 0$): Vendió por más de lo que pagó → evento imponible en la mayoría de las jurisdicciones
- **Pérdida de Capital** ($< 0$): Vendió por menos de lo que pagó → puede compensar plusvalías futuras

### 🔄 Realizadas vs No Realizadas

| Tipo | Definición | Impacto Fiscal |
|------|-----------|------------|
| **No Realizadas** (ganancia/pérdida sobre el papel) | Activo aún mantenido; la ganancia/pérdida existe solo en el papel | No tributa (en la mayoría de las jurisdicciones) |
| **Realizadas** | Activo vendido; la ganancia/pérdida se materializa | Normalmente desencadena un evento fiscal |

Esta distinción es la base del **diferimiento fiscal**: al no vender, usted difiere el evento fiscal indefinidamente.

### 📋 Métodos de Emparejamiento

Cuando ha comprado el mismo activo varias veces a precios diferentes, ¿con qué compra se empareja una venta?

| Método | Regla | Efecto |
|--------|------|--------|
| **FIFO** (First In, First Out) | Las acciones más antiguas se venden primero | El valor predeterminado más común |
| **LIFO** (Last In, First Out) | Las acciones más recientes se venden primero | Puede minimizar/maximizar las plusvalías |
| **Identificación Específica** | Usted elige qué lote vender | Máxima optimización fiscal |

!!! info "LibreFolio utiliza FIFO"

    LibreFolio calcula las plusvalías utilizando el emparejamiento **FIFO** en tiempo de ejecución. El emparejamiento se calcula bajo demanda, no se almacena en la base de datos.

---

## 🔄 Compensación de Pérdidas (Loss Carry-Forward)

La mayoría de las jurisdicciones permiten **trasladar** las pérdidas de capital para compensar plusvalías futuras:

$$
\text{Taxable Gain}_t = \max(0, \text{Realized Gains}_t - \text{Carried Losses}_{t-1})
$$

Parámetros clave que varían según la jurisdicción:

- ⏳ **Duración**: Cuánto tiempo se pueden trasladar las pérdidas (ej., 4 años en Italia, ilimitado en Alemania, 7 años en EE. UU. para ciertos tipos)
- 📊 **Alcance**: Si las pérdidas de una clase de activo pueden compensar las plusvalías de otra
- 🚫 **Reglas de venta simulada (Wash sale)**: Restricciones sobre la recompra de un activo vendido en un plazo corto para reclamar la pérdida

---

## ⏳ Ventaja del Diferimiento Fiscal { #tax-deferral-advantage }

Uno de los conceptos más poderosos en la inversión fiscalmente eficiente es **diferir** el evento fiscal el mayor tiempo posible. Las matemáticas favorecen fuertemente el diferimiento:

### 📐 La Fórmula

Compare dos escenarios durante $n$ años con un retorno anual $r$ y una tasa impositiva $\tau$:

**Escenario A — Impuestos anuales** (ej., fondo de distribución):

$$
V_A = P \cdot (1 + r \cdot (1 - \tau))^n
$$

**Escenario B — Impuestos al final** (ej., fondo de acumulación):

$$
V_B = P \cdot (1 + r)^n - \tau \cdot [P \cdot (1 + r)^n - P] = P \cdot [(1 + r)^n \cdot (1 - \tau) + \tau]
$$

### 📊 Ejemplo Numérico

Con $P = 10{,}000$, $r = 7\%$, $\tau = 26\%$, $n = 20$ años:

| Escenario | Valor Final | Retorno Efectivo |
|----------|------------|-----------------|
| Impuestos anuales | €28,398 | 5.18% p.a. |
| Impuestos al final | €31,616 | 5.93% p.a. |
| **Ventaja del diferimiento** | **+€3,218** | **+0.75% p.a.** |

La ventaja crece exponencialmente con el tiempo; a lo largo de 30 años, la brecha se amplía a más de €8,000 sobre la misma inversión de €10,000.

---

## 📦 Instrumentos de Acumulación vs Distribución

Esta ventaja del diferimiento se manifiesta directamente en la elección entre vehículos de inversión de acumulación y de distribución:

### 📈 Acumulación (ej., Acc ETFs)

- Los dividendos son **reinvertidos internamente** por el fondo
- **No hay evento imponible** hasta que usted venda las participaciones del fondo
- Beneficio total del [crecimiento compuesto](../technical-analysis/synthetic-benchmarks/compound.md) sobre el importe bruto (antes de impuestos)
- Ideal para inversores a largo plazo que buscan el máximo crecimiento

### 💵 Distribución (ej., Dist ETFs)

- Los dividendos se le **pagan** periódicamente
- Cada distribución es un **evento imponible** (tributa inmediatamente)
- Usted recibe efectivo pero pierde el beneficio del interés compuesto sobre el importe impositivo
- Útil si necesita ingresos de sus inversiones

### 🔗 Conexión con los Modelos de Crecimiento

- El **[Crecimiento Lineal](../technical-analysis/synthetic-benchmarks/linear.md)** aproxima el comportamiento cuando los dividendos se reciben pero **no se reinvierten**; el crecimiento es aditivo.
- El **[Crecimiento Compuesto](../technical-analysis/synthetic-benchmarks/compound.md)** representa el caso ideal con reinversión total; el crecimiento es multiplicativo y es el que más se beneficia del diferimiento fiscal.

---

## ⚠️ Consideraciones Específicas por Jurisdicción

Cada país tiene su propio marco fiscal. Parámetros clave que varían:

| Parámetro | Ejemplos |
|-----------|---------|
| **Tasa impositiva sobre plusvalías** | 26% (Italia), 25% (Alemania), 0-20% (EE. UU., dependiendo del periodo de tenencia) |
| **Beneficios por periodo de tenencia** | Algunos países reducen las tasas para tenencias a largo plazo |
| **Duración de la compensación de pérdidas** | 4 años (Italia), ilimitado (Alemania), 7 años (EE. UU. para algunos tipos) |
| **Tratados de doble imposición** | Afectan a los dividendos de acciones extranjeras |
| **Mínimos exentos** | Umbrales anuales por debajo de los cuales las plusvalías no tributan |
| **Reglas específicas de Crypto** | En rápida evolución; a menudo se tratan de forma diferente a los activos tradicionales |

!!! abstract "El rol de LibreFolio"

    LibreFolio rastrea sus transacciones y calcula las plusvalías/pérdidas realizadas utilizando el emparejamiento FIFO. Proporciona la **base de datos** para la declaración de impuestos, pero no genera declaraciones fiscales ni aplica reglas específicas de cada jurisdicción. Exporte sus datos de transacciones y consulte a un profesional fiscal.

---

## 🔗 Relacionado

- 📈 **[Retornos y Tasas de Crecimiento](returns.md)** — Cómo medir y anualizar los retornos
- 🎯 **[Benchmarks Sintéticos](../technical-analysis/synthetic-benchmarks/index.md)** — Visualización de crecimiento lineal vs compuesto
- 📅 **[Convenciones de Recuento de Días](day-count.md)** — Cómo afectan los periodos de tiempo a los cálculos
