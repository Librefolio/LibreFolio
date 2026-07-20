# 💰 Tarjetas KPI

*[⬅️ Volver a la Descripción General del Panel de Control](index.md)*

Las tres tarjetas KPI en la parte superior del panel de control te brindan un diagnóstico rápido de tu cartera. Todos los valores respetan el **rango de tiempo y el ámbito del bróker** seleccionados en la parte superior de la página.

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Vista general de las tarjetas KPI">
</div>

---

## 📉 Tarjeta 1 — P&L del Período {: #card-1-period-pl }

<div class="kpi-card-crop-container card-period-pnl">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Tarjeta de P&L del Período">
</div>

La tarjeta **P&L del Período** muestra cuánto dinero *ganó* realmente tu cartera en la ventana seleccionada — después de eliminar el efecto de tus propios depósitos y retiros.

El número principal se calcula utilizando la siguiente fórmula:

\[\text{P&L del Período} = \text{VNA}_{\text{final}} - \text{VNA}_{\text{inicio}} - \text{Flujos Netos}_{\text{período}}\]

Un número positivo significa que ganaste dinero gracias a la actividad de inversión. Un número negativo significa que perdiste dinero, neto de los movimientos de capital.

### El número debajo del valor principal

Justo debajo del valor de P&L del Período, una línea más pequeña muestra algo como `+45.20 (+3.10%)`.

- La cantidad es el cambio **día a día** (hoy vs. ayer) en tu **P&L Total** — tu ganancia/pérdida acumulada de todos los tiempos, no solo del período seleccionado.
- El porcentaje lo expresa como una proporción del P&L del Período de **ayer** — te indica cuánto "pesó" el movimiento de hoy en el resultado del período que estás viendo actualmente.

\[\text{Cambio diario} = \text{P&L Total}_{\text{hoy}} - \text{P&L Total}_{\text{ayer}}\]

Esta línea solo aparece una vez que el historial tiene al menos dos puntos diarios.

### Las filas de desglose

| Fila | Qué mide |
|-----|-----------------|
| **Cambio no realizado** | Cuánto cambió la [ganancia/pérdida no realizada](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md) de tus posiciones abiertas durante el período |
| **Ventas** | Ganancia o pérdida realizada de posiciones cerradas durante el período (precio de venta − costo promedio) |
| **Dividendos e intereses** | Ingresos en efectivo por dividendos, cupones de bonos e intereses P2P |
| **Comisiones e impuestos** | Comisiones e impuestos registrados como transacciones |

!!! tip "Verificación de identidad"

    Las cuatro filas suman el número principal de P&L del Período (± pequeños residuales por redondeo de FX).

🔗 **Teoría**: [P&L del Período](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md) · [Valor en Libros / PMP](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)

---

## 📈 Tarjeta 2 — Rendimientos {: #card-2-returns }

<div class="kpi-card-crop-container card-returns">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Tarjeta de Rendimientos">
</div>

La tarjeta **Rendimientos** muestra métricas de *tasa de rendimiento* — porcentajes que te permiten comparar el rendimiento independientemente del tamaño de la cartera.

### Efecto de la Oportunidad

El **Efecto de la Oportunidad** en la parte superior de la tarjeta mide si tus decisiones de depósito/retiro *añadieron* o *restaron* valor en comparación con una estrategia pasiva de comprar y mantener:

\[\text{Efecto de la Oportunidad} = \text{MWRR}_{\text{acumulado}} - \text{TWRR}_{\text{acumulado}}\]

- **Favorable (positivo)** ✅: tendiste a depositar cuando los precios estaban bajos, aumentando tu rendimiento personal por encima de lo que ganaron los activos por sí solos.
- **Desfavorable (negativo)** ❌: tendiste a depositar en picos o te perdiste las caídas, reduciendo tu rendimiento por debajo del rendimiento puro de los activos.

### El número debajo del Efecto de la Oportunidad

Debajo del Efecto de la Oportunidad verás un pequeño porcentaje (ej. `+0.35%`) — es el cambio en tu **P&L Total** de **ayer a hoy**, expresado como una proporción del patrimonio neto de ayer:

\[\text{%Cambio diario} = \frac{\text{P&L Total}_{\text{hoy}} - \text{P&L Total}_{\text{ayer}}}{\text{Patrimonio Neto}_{\text{ayer}}} \times 100\]

Es una estimación aproximada del rendimiento de **hoy** — una comprobación rápida del estado. No es el ROI, TWRR o MWRR que se muestran en las filas siguientes, que permanecen ancladas al período completo seleccionado.

### Las cuatro métricas de rendimiento

| Métrica | Pregunta que responde |
|--------|---------------------|
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)** | ¿Cuánto gané en relación con mi capital neto invertido? |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** | ¿Cómo se desempeñaron mis selecciones de activos, independientemente de cuándo deposité? |
| **[MWRR acumulado](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | ¿Cuál es el rendimiento ponderado por dinero acumulado para mis flujos de efectivo reales? |
| **[MWRR anualizado](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | ¿A qué tasa compuesta anual creció realmente mi capital? |

!!! note "TWRR vs. MWRR"

    - **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** mide la **estrategia de activos** — igual que como se evalúa a un gestor de fondos.
    - **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** mide **tu resultado personal** — incluyendo el momento de tus depósitos.
    - La brecha entre ellos es el [Efecto de la Oportunidad](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md).

---

## 💰 Tarjeta 3 — Patrimonio Neto {: #card-3-net-worth }

<div class="kpi-card-crop-container card-net-worth">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Tarjeta de Patrimonio Neto">
</div>

La tarjeta **Patrimonio Neto** muestra el valor absoluto de tu cartera al final del período seleccionado.

### El número debajo del Patrimonio Neto

Debajo del valor del Patrimonio Neto encontrarás tu **P&L Total**, con su cambio porcentual entre paréntesis — ej. `+12,450.30 (+0.35%)`.

- La cantidad es tu **P&L Total** — la ganancia o pérdida acumulada desde el inicio, en todo el historial de este ámbito (no solo el período actual).
- El porcentaje entre paréntesis expresa el cambio **día a día** (hoy vs. ayer) de este P&L Total, como una proporción del P&L Total de **ayer**.

\[\text{P&L Total} = \text{Patrimonio Neto} - \text{Capital Neto Invertido Desde el Inicio}\]

Nota: "Capital Neto Invertido Desde el Inicio" aquí es la suma de **todos** los depósitos menos **todos** los retiros desde que empezaste a usar este ámbito — una cifra diferente y más grande que la fila "Capital Depositado" a continuación, que solo cuenta los movimientos dentro del período seleccionado.

🔗 **Teoría**: [Capital Depositado, P&L Total y Fondos de Efectivo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)

### Qué significan las filas

| Fila | Definición |
|-----|-----------|
| **[Valor de Mercado](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)** | Precio de mercado actual × cantidad de todos los activos mantenidos |
| **[Valor en Libros](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)** | Lo que pagaste por tus posiciones abiertas (costo promedio × cantidad) |
| **Efectivo** | Saldo líquido mantenido en cuentas de bróker |
| **[Capital Depositado](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)** | Capital externo neto aportado a este ámbito |

### La barra de Capital Depositado

La barra horizontal debajo de las filas visualiza:

- 🟢 **Total depositado** — todos los depósitos en el período
- 🔴 **Total retirado** — todos los retiros en el período

El número principal muestra el saldo neto (depositado − retirado).

!!! info "Punto en el tiempo vs. período"

    El Valor de Mercado, el Valor en Libros y el Efectivo son **instantáneas** al final — son independientes de la fecha de inicio.
    El Capital Depositado tiene **ámbito de período** — cuenta los depósitos y retiros entre el inicio y el final del rango seleccionado.

---

## 🔗 Relacionado

- 💼 **[VNA / Patrimonio Neto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- 📚 **[Valor en Libros](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)**
- 📊 **[P&L del Período](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)**
- 💸 **[Capital Depositado y P&L Total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)**
- 📈 **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)**
- ⏱️ **[Efecto de la Oportunidad](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)**
