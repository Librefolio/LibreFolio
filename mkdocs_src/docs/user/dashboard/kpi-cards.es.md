# 💰 Tarjetas de KPI

*[⬅️ Volver a la Descripción general del panel de control](index.md)*

Las tres tarjetas de KPI en la parte superior del panel de control proporcionan un diagnóstico rápido de su cartera. Todos los valores respetan el **rango de tiempo y el alcance del bróker** seleccionados en la parte superior de la página.

---

## 💰 Tarjeta 1 — Patrimonio Neto

La tarjeta de **Patrimonio Neto** muestra el valor absoluto de su cartera al final del periodo seleccionado.

### Qué significan las filas

| Fila | Definición |
|-----|-----------|
| **[Valor de Mercado](../../financial-theory/technical-analysis/performance-metrics/nav.md)** | Precio de mercado actual × cantidad para todos los activos mantenidos |
| **[Valor Contable](../../financial-theory/technical-analysis/performance-metrics/book-value.md)** | Lo que pagó por sus posiciones abiertas (coste medio × cantidad) |
| **Efectivo** | Saldo líquido mantenido en cuentas de bróker |
| **[Capital Depositado](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)** | Capital externo neto aportado a este alcance |

### La barra de Capital Depositado

La barra horizontal debajo de las filas visualiza:

- 🟢 **Total depositado** — todos los depósitos en el periodo
- 🔴 **Total retirado** — todos los retiros en el periodo

El número principal muestra el saldo neto (depositado − retirado).

!!! info "Punto en el tiempo vs. periodo"

    Valor de Mercado, Valor Contable y Efectivo son **instantáneas** a la fecha de finalización — son independientes de la fecha de inicio.
    Capital Depositado tiene un **alcance de periodo** — contabiliza los depósitos y retiros entre el inicio y el final del rango seleccionado.

---

## 📉 Tarjeta 2 — P&L del Periodo

La tarjeta de **P&L del Periodo** muestra cuánto dinero *ganó* realmente su cartera en la ventana seleccionada, tras eliminar el efecto de sus propios depósitos y retiros.

El número principal utiliza la fórmula:

> **NAV final** − **NAV inicial** − **Flujos Externos Netos en el periodo**

Un número positivo significa que ganó dinero gracias a la actividad de inversión. Un número negativo significa que perdió dinero neto de los movimientos de capital.

### Las filas de desglose

| Fila | Qué mide |
|-----|-----------------|
| **Cambio no realizado** | Cuánto cambió la [ganancia/pérdida no realizada](../../financial-theory/technical-analysis/performance-metrics/book-value.md) de sus posiciones abiertas durante el periodo |
| **Ventas** | Ganancia o pérdida realizada de las posiciones cerradas durante el periodo (precio de venta − coste medio) |
| **Dividendos e intereses** | Ingresos en efectivo provenientes de dividendos, cupones de bonos e intereses P2P |
| **Comisiones e impuestos** | Comisiones e impuestos registrados como transacciones |

!!! tip "Verificación de coherencia"

    Las cuatro filas suman el número principal del P&L del Periodo (± pequeños residuos por redondeo de FX).

🔗 **Teoría**: [P&L del Periodo](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md) · [Valor Contable / PMP](../../financial-theory/technical-analysis/performance-metrics/book-value.md)

---

## 📈 Tarjeta 3 — Retornos

La tarjeta de **Retornos** muestra métricas de *tasa de retorno* — porcentajes que le permiten comparar el rendimiento independientemente del tamaño de la cartera.

### Efecto de Temporización (Timing Effect)

El **Timing Effect** en la parte superior de la tarjeta mide si sus decisiones de depósito/retiro *añadieron* o *restaron* valor en comparación con una estrategia pasiva de comprar y mantener (buy-and-hold).

> **Timing Effect** = MWRR acumulado − TWRR acumulado

- **Favorable (positivo)** ✅: tendió a depositar cuando los precios estaban bajos, impulsando su retorno personal por encima de lo que los activos ganaron por sí solos.
- **Desfavorable (negativo)** ❌: tendió a depositar en los picos o no aprovechó las caídas, arrastrando su retorno por debajo del rendimiento puro de los activos.

### Las cuatro métricas de retorno

| Métrica | Pregunta a la que responde |
|--------|---------------------|
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/roi.md)** | ¿Cuánto gané en relación con mi capital neto invertido? |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** | ¿Cómo se comportaron mis elecciones de activos, independientemente de cuándo deposité? |
| **[MWRR acumulado](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | ¿Cuál es el retorno acumulativo ponderado por dinero para mis flujos de caja reales? |
| **[MWRR anualizado](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | ¿A qué tasa anual compuesta creció realmente mi capital? |

!!! note "TWRR vs. MWRR"

    - **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** mide la **estrategia de activos** — igual que se evalúa a un gestor de fondos.
    - **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** mide **su resultado personal** — incluyendo la temporización de sus depósitos.
    - La brecha entre ambos es el [Timing Effect](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md).

---

## 🔗 Relacionado

- 💼 **[NAV / Patrimonio Neto](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- 📚 **[Valor Contable](../../financial-theory/technical-analysis/performance-metrics/book-value.md)**
- 📊 **[P&L del Periodo](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md)**
- 💸 **[Capital Depositado & P&L Total](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)**
- 📈 **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)**
- ⏱️ **[Timing Effect](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md)**
