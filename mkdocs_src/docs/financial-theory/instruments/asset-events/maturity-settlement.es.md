# 🏁 Liquidación al Vencimiento

Un evento de **liquidación al vencimiento** marca el final de un instrumento financiero a plazo fijo: el emisor devuelve el principal (valor nominal) al inversor y no se realizan más cálculos de precio.

---

## 📖 Definición

El vencimiento es la fecha en la que un instrumento de deuda (bono, letra, certificado de depósito, préstamo a plazo) llega a su fin contractual. En esta fecha:

1. El **principal** (valor nominal / valor par) se devuelve al inversor
2. Se realiza cualquier **pago de interés final** (si corresponde)
3. El instrumento **deja de existir**: no hay más valoraciones ni negociaciones

### Instrumentos con Fechas de Vencimiento

| Instrumento | Vencimiento Típico | Liquidación |
|------------|-----------------|------------|
| **Letras del Tesoro** | 4 semanas – 1 año | Valor par al vencimiento |
| **Bonos del Estado** | 2 – 30 años | Valor par + cupón final |
| **Bonos Corporativos** | 1 – 30 años | Valor par + cupón final |
| **Certificados de Depósito** | 1 mes – 5 años | Principal + intereses devengados |
| **Depósitos a Plazo** | 1 mes – 5 años | Principal + intereses |
| **Préstamos P2P** | 1 – 5 años | Principal restante |

---

## 📉 Impacto en el Precio de Mercado

A medida que un bono se acerca al vencimiento, su precio de mercado converge hacia el **valor nominal** (par), independientemente de si cotizaba con prima o con descuento:

$$
\lim_{d \to \text{vencimiento}} P(d) = \text{Valor Nominal}
$$

Este fenómeno se denomina **pull to par**:

- **Bonos con prima** (precio > par): El precio disminuye gradualmente hacia el valor par
- **Bonos con descuento** (precio < par): El precio aumenta gradualmente hacia el valor par

!!! example "Ejemplo: Vencimiento de Bono del Estado"

    Un bono del Estado a 10 años con valor nominal de 1.000 € y un cupón anual del 3%:

    - **En la emisión** (2015): Precio = 1.000 € (par)
    - **A mitad de vida** (2020): Precio = 1.050 € (prima, porque las tasas de mercado bajaron)
    - **Cerca del vencimiento** (2024): Precio = 1.005 € (convergiendo al par)
    - **Al vencimiento** (2025-01-15): El inversor recibe:
    - 1.000 € (devolución del valor nominal)
    - 30 € (cupón anual final)
    - Total: 1.030 €

!!! example "Ejemplo: Bono Cupón Cero"

    Un bono cupón cero con valor nominal de $1,000 adquirido por $850:

    - **En la compra**: Precio = $850 (descuento)
    - **Al vencimiento**: El inversor recibe $1,000
    - **Rendimiento implícito**: $150 ($1,000 − $850)
    - Sin pagos de intereses intermedios; todo el retorno proviene de la liquidación al vencimiento

---

## 📊 Después del Vencimiento

Una vez que se registra un evento de liquidación al vencimiento en LibreFolio:

- La **serie de precios** del activo finaliza en la fecha de vencimiento
- El importe de la liquidación representa el **punto de datos final**
- El activo puede permanecer en el sistema para análisis históricos, pero no recibirá nuevos datos de precios

---

## 🧮 Cómo gestiona LibreFolio la Liquidación al Vencimiento

En LibreFolio, se registra un evento `MATURITY_SETTLEMENT` con:

- **Date**: La fecha de vencimiento
- **Amount**: El valor nominal / importe del principal devuelto
- **Currency**: La moneda de la liquidación
- **Notes**: Descripción opcional (ej., "Bono del Tesoro a 10 años vencido")

Para el proveedor **Scheduled Investment**, la fecha de vencimiento se configura en la configuración del proveedor. La fórmula de cálculo de precios reconoce que no ocurre más devengo después del vencimiento:

$$
\text{price}(d) = \begin{cases}
\text{initial\\_value} + \text{accrued}(d) - \Sigma\text{INT} + \Sigma\text{ADJ} & \text{if } d < \text{maturity} \\
\text{settlement\\_amount} & \text{if } d \geq \text{maturity}
\end{cases}
$$

---

## 🔗 Relacionado

- 📅 **[Descripción General de Eventos de Activos](index.md)** — Todos los tipos de eventos
- 📈 **[Intereses](interest.md)** — Pagos de cupones periódicos antes del vencimiento
- 📆 **[Convenciones de Recuento de Días](../../fundamentals/day-count.md)** — Cómo se calcula el devengo entre fechas de cupón
- 📊 **[Ajuste de Precio](price-adjustment.md)** — Cambios de valor no monetarios antes del vencimiento
