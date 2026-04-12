# 📈 Interés

Un evento de **interés** representa un pago de intereses periódico de un instrumento de deuda, un valor de renta fija o un acuerdo de préstamo.

---

## 📖 Definición

El interés es el costo de pedir dinero prestado, pagado por el emisor (prestatario) al tenedor (prestamista). Para los inversores, los pagos de intereses representan los ingresos obtenidos por mantener bonos, pagarés, depósitos a plazo o préstamos entre pares (P2P).

A diferencia de los dividendos (que dependen de los beneficios de la empresa), los pagos de intereses son **obligaciones contractuales**: el emisor debe pagar la tasa acordada independientemente del desempeño financiero.

**Calendarios de intereses comunes:**

| Frecuencia | Instrumentos típicos |
|-----------|-------------------|
| Mensual | Cuentas de ahorro, préstamos P2P |
| Trimestral | Bonos corporativos, algunos bonos gubernamentales |
| Semestral | Bonos del Tesoro de EE. UU., muchos bonos gubernamentales europeos |
| Anual | Algunos bonos corporativos, depósitos a plazo |
| Al vencimiento | Bonos cupón cero, certificados de depósito |

---

## 📉 Impacto en el Precio de Mercado

Para los **bonos con cupón**, los pagos de intereses provocan un reinicio periódico del componente de **interés devengado**:

1. Entre las fechas de cupón, el "precio sucio" del bono (precio limpio + interés devengado) aumenta gradualmente
2. En la fecha de pago del cupón, el interés devengado se reinicia a cero
3. El precio limpio puede descender ligeramente alrededor de la fecha ex-cupón

!!! example "Example"

    Un bono con un valor nominal de 1.000 € paga un cupón anual del 4% semestralmente (20 € cada 6 meses).

    - **Día anterior al cupón**: Precio limpio 980 €, Interés devengado 20 € $\to$ Precio sucio 1.000 €
    - **Fecha del cupón**: El interés devengado se reinicia a 0 €, el inversor recibe 20 € en efectivo
    - **Día posterior al cupón**: Precio limpio 980 €, Interés devengado $\approx$ 0,11 € $\to$ Precio sucio 980,11 €

Para los activos de **Scheduled Investment** en LibreFolio, los eventos de interés modifican directamente el precio calculado:

$$
\text{price}(d) = \text{initial{\_}value} + \text{accrued{\_}interest}(d) - \sum \text{INTEREST events}
$$

---

## 📊 Métricas de Rendimiento

### Rendimiento Actual (Current Yield)

$$
\text{Current Yield} = \frac{\text{Annual Coupon}}{\text{Current Market Price}} \times 100\%
$$

### Rendimiento al Vencimiento (YTM)

El rendimiento total anticipado si el bono se mantiene hasta su vencimiento, teniendo en cuenta los pagos de cupones, el reembolso del valor nominal y el precio de mercado actual.

---

## 🧮 Cómo gestiona LibreFolio el Interés

En LibreFolio, un evento `INTEREST` se registra con:

- **Date**: La fecha del pago de intereses
- **Amount**: El monto en efectivo recibido
- **Currency**: La moneda del pago

Para los activos de proveedor de **Scheduled Investment**, los eventos de interés se generan automáticamente a partir del calendario de intereses configurado y afectan directamente al cálculo del precio. Para los bonos con precio de mercado, sirven como marcadores informativos.

---

## 🔗 Relacionados

- 📅 **[Descripción general de eventos de activos](index.md)** — Todos los tipos de eventos
- 📆 **[Convenciones de conteo de días](../../fundamentals/day-count.md)** — Cómo se calculan los períodos de devengo de intereses
- 🏁 **[Liquidación al Vencimiento](maturity-settlement.md)** — Retorno final del principal al vencimiento del bono
