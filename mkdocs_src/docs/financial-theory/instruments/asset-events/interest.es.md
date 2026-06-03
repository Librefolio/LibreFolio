# 📈 Interés

Un evento de **interés** representa un pago de intereses periódico de un instrumento de deuda, un valor de renta fija o un acuerdo de préstamo.

---

## 📖 Definición

El interés es el coste de pedir dinero prestado, pagado por el emisor (prestatario) al tenedor (prestamista). Para los inversores, los pagos de intereses representan los ingresos obtenidos por mantener bonos, pagarés, depósitos a plazo o préstamos peer-to-peer.

A diferencia de los dividendos (que dependen de los beneficios de la empresa), los pagos de intereses **son una obligación contractual**: el emisor debe pagar la tasa acordada independientemente del rendimiento financiero.

**Calendarios de intereses comunes:**

| Frecuencia | Instrumentos típicos |
|-----------|-------------------|
| Mensual | Cuentas de ahorro, préstamos P2P |
| Trimestral | Bonos corporativos, algunos bonos gubernamentales |
| Semestral | Bonos del Tesoro de EE. UU., muchos bonos gubernamentales europeos |
| Anual | Algunos bonos corporativos, depósitos a plazo |
| Al vencimiento | Bonos cupón cero, certificados de depósito |

---

## 🧮 Fórmulas de Interés

??? example "📏 Interés Simple"

    Interés calculado únicamente sobre el capital original, sin capitalización:

    $$
    I = P \times r \times t
    $$

    Donde:

    - $P$ = capital (inversión inicial)
    - $r$ = tasa de interés anual (p. ej., 0.04 para el 4%)
    - $t$ = tiempo en años

    Utilizado para: préstamos a corto plazo, algunas cuentas de ahorro, letras del tesoro.

??? example "📈 Interés Compuesto"

    Interés calculado sobre el capital **más** los intereses acumulados previamente:

    $$
    A = P \times \left(1 + \frac{r}{n}\right)^{n \times t}
    $$

    Donde:

    - $A$ = valor final (capital + interés)
    - $P$ = capital
    - $r$ = tasa de interés anual
    - $n$ = frecuencia de capitalización por año (12 = mensual, 4 = trimestral, 1 = anual)
    - $t$ = tiempo en años

    El interés ganado es: $I = A - P$

    Utilizado para: la mayoría de los bonos, cuentas de ahorro con reinversión, plataformas P2P.

---

## 📉 Impacto en el Precio de Mercado

Para los **bonos con cupón**, los pagos de intereses provocan un reinicio periódico del componente de **interés devengado**:

1. Entre las fechas de cupón, el "precio sucio" del bono (precio limpio + interés devengado) aumenta gradualmente
2. En la fecha de pago del cupón, el interés devengado se restablece a cero
3. El precio limpio puede bajar ligeramente alrededor de la fecha ex-cupón

??? example "Ciclo de cupón de bono"

    Un bono con un valor nominal de 1.000 € paga un cupón anual del 4% semestralmente (20 € cada 6 meses).

    - **Día anterior al cupón**: Precio limpio 980 €, Interés devengado 20 € → Precio sucio 1.000 €
    - **Fecha del cupón**: El interés devengado se restablece a 0 €, el inversor recibe 20 € en efectivo
    - **Día posterior al cupón**: Precio limpio 980 €, Interés devengado ≈ 0,11 € → Precio sucio 980,11 €

Para los activos de **inversión programada** en LibreFolio, los eventos de interés modifican directamente el precio calculado:

$$
\text{price}(d) = V_0 + I_{accrued}(d) - \sum_{k} C_k
$$

Donde:

- $V_0$ = valor de la inversión inicial
- $I_{accrued}(d)$ = interés devengado hasta la fecha $d$
- $\sum_k C_k$ = suma de todos los pagos de intereses (cupones) ya distribuidos

---

## 📊 Métricas de Rendimiento

??? example "📐 Rendimiento Actual"

    La medida de rendimiento más sencilla: los ingresos anuales en relación con el precio actual:

    $$
    \text{Rendimiento Actual} = \frac{\text{Cupón Anual}}{\text{Precio de Mercado Actual}} \times 100
    $$

    Donde:

    - **Cupón Anual** = total de pagos de cupones por año (p. ej., 40 € para un bono del 4% con un valor nominal de 1.000 €)
    - **Precio de Mercado Actual** = lo que pagaría por comprar el bono hoy

    Limitación: ignora la plusvalía o pérdida de capital si se mantiene hasta el vencimiento.

??? example "📐 Rendimiento al Vencimiento (YTM)"

    El rendimiento total previsto si el bono se mantiene hasta el vencimiento, contabilizando **todos** los flujos de caja: pagos de cupones, reembolso del valor nominal y la diferencia entre el precio de compra y el valor a la par.

    YTM es la tasa $y$ que satisface:

    $$
    P = \sum_{t=1}^{T} \frac{C}{(1+y)^t} + \frac{F}{(1+y)^T}
    $$

    Donde:

    - $P$ = precio de mercado actual
    - $C$ = pago de cupón por período
    - $F$ = valor nominal (devuelto al vencimiento)
    - $T$ = número de períodos hasta el vencimiento
    - $y$ = rendimiento al vencimiento (por período)

    YTM debe resolverse numéricamente (no tiene una solución de forma cerrada).

---

## 🧮 Cómo gestiona LibreFolio los intereses

En LibreFolio, un evento `INTEREST` se registra con:

- **Date**: La fecha del pago de intereses
- **Amount**: El monto en efectivo recibido
- **Currency**: La moneda del pago

Para los activos de proveedor de **inversión programada**, los eventos de interés se generan automáticamente a partir del calendario de intereses configurado y afectan directamente al cálculo del precio. Para los bonos con precio de mercado, sirven como marcadores informativos.

---

## 🔗 Relacionado

- 📅 **[Descripción general de eventos de activos](index.md)** — Todos los tipos de eventos
- 📆 **[Convenciones de recuento de días](../../fundamentals/day-count.md)** — Cómo se calculan los períodos de devengo de intereses
- 🏁 **[Liquidación al vencimiento](maturity-settlement.md)** — Retorno final del capital al vencimiento del bono
- 📈 **[Tasas de retorno y crecimiento](../../fundamentals/returns.md)** — Medición del rendimiento total
