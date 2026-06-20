# 📈 Interés

Un evento de **interés** representa un pago de intereses periódico de un instrumento de deuda, un valor de renta fija o un acuerdo de préstamo.

---

## 📖 Definición

El interés es el coste del préstamo de dinero, pagado por el emisor (prestatario) al tenedor (prestamista). Para los inversores, los pagos de intereses representan los ingresos obtenidos por mantener bonos, pagarés, depósitos a plazo o préstamos entre pares (P2P).

A diferencia de los dividendos (que dependen de los beneficios de la empresa), los pagos de intereses son una **obligación contractual**: el emisor debe pagar la tasa acordada independientemente del rendimiento financiero.

**Calendarios de intereses comunes:**

| Frecuencia | Instrumentos típicos |
|-----------|-------------------|
| Mensual | Cuentas de ahorro, préstamos P2P |
| Trimestral | Bonos corporativos, algunos bonos gubernamentales |
| Semestral | Bonos del Tesoro de EE. UU., muchos bonos gubernamentales europeos |
| Anual | Algunos bonos corporativos, depósitos a plazo |
| Al vencimiento | Bonos de cupón cero, certificados de depósito |

---

## 🧮 Fórmulas de Interés

??? example "📏 Interés Simple"

    Interés calculado únicamente sobre el principal original; sin capitalización:

    $$
    I = P \times r \times t
    $$

    Donde:

    - $P$ = principal (inversión inicial)
    - $r$ = tasa de interés anual (ej. 0.04 para el 4%)
    - $t$ = tiempo en años

    Utilizado para: préstamos a corto plazo, algunas cuentas de ahorro, letras del tesoro.

??? example "📈 Interés Compuesto"

    Interés calculado sobre el principal **más** el interés acumulado previamente:

    $$
    A = P \times \left(1 + \frac{r}{n}\right)^{n \times t}
    $$

    Donde:

    - $A$ = monto final (principal + interés)
    - $P$ = principal
    - $r$ = tasa de interés anual
    - $n$ = frecuencia de capitalización por año (12 = mensual, 4 = trimestral, 1 = anual)
    - $t$ = tiempo en años

    El interés ganado es: $I = A - P$

    Utilizado para: la mayoría de los bonos, cuentas de ahorro con reinversión, plataformas P2P.

---

## 📉 Impacto en el Precio de Mercado

Para los **bonos con cupón**, los pagos de intereses provocan un restablecimiento periódico del componente de **interés acumulado**:

1. Entre las fechas de cupón, el "precio sucio" del bono (precio limpio + interés acumulado) aumenta gradualmente
2. En la fecha de pago del cupón, el interés acumulado se restablece a cero
3. El precio limpio puede caer ligeramente alrededor de la fecha ex-cupón

??? example "Ciclo de cupón de un bono"

    Un bono con valor nominal de 1.000 € paga un cupón anual del 4% semestralmente (20 € cada 6 meses).

    - **Día antes del cupón**: Precio limpio 980 €, Interés acumulado 20 € → Precio sucio 1.000 €
    - **Fecha del cupón**: El interés acumulado se restablece a 0 €, el inversor recibe 20 € en efectivo
    - **Día después del cupón**: Precio limpio 980 €, Interés acumulado ≈ 0,11 € → Precio sucio 980,11 €

Para los activos de **inversión programada** en LibreFolio, los eventos de interés modifican directamente el precio calculado:

$$
\text{price}(d) = V_0 + I_{accrued}(d) - \sum_{k} C_k
$$

Donde:

- $V_0$ = valor de la inversión inicial
- $I_{accrued}(d)$ = interés acumulado hasta la fecha $d$
- $\sum_k C_k$ = suma de todos los pagos de intereses (cupones) ya distribuidos

---

## 📊 Métricas de Rendimiento

??? example "📐 Rendimiento Actual (Current Yield)"

    La medida de rendimiento más simple: los ingresos anuales en relación con el precio actual:

    $$
    \text{Current Yield} = \frac{\text{Annual Coupon}}{\text{Current Market Price}} \times 100
    $$

    Donde:

    - **Annual Coupon** = pagos totales de cupones por año (ej. 40 € para un bono del 4% con valor nominal de 1.000 €)
    - **Current Market Price** = lo que pagaría por comprar el bono hoy

    Limitación: ignora la plusvalía o pérdida de capital si se mantiene hasta el vencimiento.

??? example "📐 Rendimiento al Vencimiento (YTM)"

    El retorno total anticipado si el bono se mantiene hasta el vencimiento, contabilizando **todos** los flujos de caja: pagos de cupones, reembolso del valor nominal y la diferencia entre el precio de compra y el valor a la par.

    El YTM es la tasa $y$ que satisface:

    $$
    P = \sum_{t=1}^{T} \frac{C}{(1+y)^t} + \frac{F}{(1+y)^T}
    $$

    Donde:

    - $P$ = precio de mercado actual
    - $C$ = pago de cupón por período
    - $F$ = valor nominal (devuelto al vencimiento)
    - $T$ = número de períodos hasta el vencimiento
    - $y$ = rendimiento al vencimiento (por período)

    El YTM debe resolverse numéricamente (no tiene una solución analítica).

---

## 🧮 Cómo gestiona LibreFolio los Intereses

En LibreFolio, un evento `INTEREST` (y la transacción de cartera correspondiente) se registra con:

- **Date**: La fecha del pago de intereses
- **Amount**: El monto en efectivo recibido
- **Currency**: La moneda del pago

### La diferencia contable: Interés vs. Dividendo
Es fundamental distinguir entre una transacción de **Interés** y una de **Dividendo** a nivel de base de datos:

1. **Interés (Basado en Deuda/Rendimiento)**: Un pago de intereses representa el rendimiento de una deuda o depósitos en efectivo (ej. cuentas de ahorro bancarias, préstamos P2P o cupones de bonos). En el seguimiento de cartera de partida doble, estos representan entradas de efectivo (`cash.amount > 0`) donde el activo subyacente es opcional. La transacción de la base de datos requiere `quantity = 0` porque no se transaccionan unidades del activo durante un pago de intereses en efectivo.
2. **Dividendo (Basado en capital)**: Un dividendo es una distribución de utilidades pagada a los accionistas. Requiere estrictamente que exista un activo de capital subyacente (el activo es obligatorio), y el pago depende directamente del número de acciones poseídas en la fecha ex. Al igual que los intereses, los dividendos son movimientos puros de efectivo (`quantity = 0`).

Para los activos de proveedores de **inversión programada**, los eventos de interés se generan automáticamente a partir del calendario de intereses configurado y afectan directamente al cálculo del precio. Para los bonos con precio de mercado, sirven como marcadores informativos.

---

## 🔗 Relacionado

- 📅 **[Descripción general de eventos de activos](index.md)** — Todos los tipos de eventos
- 📆 **[Convenciones de conteo de días](../../fundamentals/day-count.md)** — Cómo se calculan los períodos de devengo de intereses
- 🏁 **[Liquidación al Vencimiento](maturity-settlement.md)** — Retorno final del principal al vencimiento del bono
- 📈 **[Tasas de Retorno y Crecimiento](../../fundamentals/returns.md)** — Medición del retorno total
