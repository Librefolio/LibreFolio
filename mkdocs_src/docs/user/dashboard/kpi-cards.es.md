# 💰 Tarjetas KPI

*[⬅️ Volver a la Descripción General del Panel](index.md)*

Las tres tarjetas KPI en la parte superior del panel te brindan un diagnóstico rápido de tu cartera. Todos los valores respetan el **rango de tiempo y ámbito del bróker** seleccionados en la parte superior de la página.

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Vista general de las tarjetas KPI">
</div>

---

## 📉 Tarjeta 1 — Ganancias y Pérdidas del Período {: #card-1-period-pl }

<div class="kpi-card-crop-container card-period-pnl">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Tarjeta de Ganancias y Pérdidas del Período">
</div>

La tarjeta **Ganancias y Pérdidas del Período** muestra cuánto dinero *ganó* realmente tu cartera en la ventana seleccionada, después de eliminar el efecto de tus propios depósitos y retiros.

El número principal se calcula mediante la siguiente fórmula:

\[\text{Ganancias y Pérdidas del Período} = \text{VL}_{\text{final}} - \text{VL}_{\text{inicio}} - \text{Flujos Netos}_{\text{período}}\]

Un número positivo significa que ganaste dinero con la actividad de inversión. Un número negativo significa que perdiste dinero una vez descontados los movimientos de capital.

### Las filas de desglose

| Fila | Qué mide |
|-----|-----------------|
| **Cambio no realizado** | Cuánto cambió la [ganancia/pérdida no realizada](../../financial-theory/technical-analysis/performance-metrics/book-value.md) de tus posiciones abiertas durante el período |
| **Ventas** | Ganancia o pérdida realizada de posiciones cerradas durante el período (precio de venta − costo promedio) |
| **Dividendos e intereses** | Ingresos en efectivo por dividendos, cupones de bonos e intereses P2P |
| **Comisiones e impuestos** | Comisiones e impuestos registrados como transacciones |

!!! tip "Verificación de identidad"

    Las cuatro filas suman el número principal de Ganancias y Pérdidas del Período (± pequeños residuales por redondeo del tipo de cambio).

🔗 **Teoría**: [Ganancias y Pérdidas del Período](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md) · [Valor en Libros / PMP](../../financial-theory/technical-analysis/performance-metrics/book-value.md)

---

## 📈 Tarjeta 2 — Rendimientos {: #card-2-returns }

<div class="kpi-card-crop-container card-returns">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Tarjeta de Rendimientos">
</div>

La tarjeta **Rendimientos** muestra métricas de *tasa de rendimiento* — porcentajes que te permiten comparar el rendimiento independientemente del tamaño de la cartera.

### Efecto de Sincronización

El **Efecto de Sincronización** en la parte superior de la tarjeta mide si tus decisiones de depósito/retiro *añadieron* o *restaron* valor en comparación con una estrategia pasiva de comprar y mantener:

\[\text{Efecto de Sincronización} = \text{MWR}_{\text{acumulado}} - \text{TWR}_{\text{acumulado}}\]

- **Favorable (positivo)** ✅: tendiste a depositar cuando los precios eran bajos, aumentando tu rendimiento personal por encima de lo que ganaron los activos por sí solos.
- **Desfavorable (negativo)** ❌: tendiste a depositar en picos o te perdiste las caídas, reduciendo tu rendimiento por debajo del rendimiento puro de los activos.

### Las cuatro métricas de rendimiento

| Métrica | A qué pregunta responde |
|--------|---------------------|
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/roi.md)** | ¿Cuánto gané en relación con mi capital neto invertido? |
| **[TWR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** | ¿Cómo se desempeñaron mis elecciones de activos, independientemente de cuándo deposité? |
| **[MWR acumulado](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | ¿Cuál es el rendimiento ponderado por dinero acumulado para mis flujos de efectivo reales? |
| **[MWR anualizado](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | ¿A qué tasa compuesta anual creció realmente mi capital? |

!!! note "TWR vs. MWR"

    - **[TWR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** mide la **estrategia de activos** — igual que se evalúa a un gestor de fondos.
    - **[MWR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** mide **tu resultado personal** — incluyendo la sincronización de tus depósitos.
    - La brecha entre ellos es el [Efecto de Sincronización](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md).

---

## 💰 Tarjeta 3 — Patrimonio Neto {: #card-3-net-worth }

<div class="kpi-card-crop-container card-net-worth">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Tarjeta de Patrimonio Neto">
</div>

La tarjeta **Patrimonio Neto** muestra el valor absoluto de tu cartera al final del período seleccionado.

### Qué significan las filas

| Fila | Definición |
|-----|-----------|
| **[Valor de Mercado](../../financial-theory/technical-analysis/performance-metrics/nav.md)** | Precio de mercado actual × cantidad de todos los activos mantenidos |
| **[Valor en Libros](../../financial-theory/technical-analysis/performance-metrics/book-value.md)** | Lo que pagaste por tus posiciones abiertas (costo promedio × cantidad) |
| **Efectivo** | Saldo líquido mantenido en cuentas de bróker |
| **[Capital Depositado](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)** | Capital externo neto aportado a este ámbito |

### La barra de Capital Depositado

La barra horizontal debajo de las filas visualiza:

- 🟢 **Total depositado** — todos los depósitos en el período
- 🔴 **Total retirado** — todos los retiros en el período

El número principal muestra el saldo neto (depositado − retirado).

!!! info "Punto en el tiempo vs. período"

    El Valor de Mercado, el Valor en Libros y el Efectivo son **instantáneas** en la fecha final — son independientes de la fecha de inicio.
    El Capital Depositado tiene **alcance de período** — cuenta los depósitos y retiros entre el inicio y el final del rango seleccionado.

---

## 🔗 Relacionado

- 💼 **[VL / Patrimonio Neto](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- 📚 **[Valor en Libros](../../financial-theory/technical-analysis/performance-metrics/book-value.md)**
- 📊 **[Ganancias y Pérdidas del Período](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md)**
- 💸 **[Capital Depositado y Ganancias y Pérdidas Totales](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- 📈 **[TWR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)**
- 📈 **[MWR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)**
- ⏱️ **[Efecto de Sincronización](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md)**
