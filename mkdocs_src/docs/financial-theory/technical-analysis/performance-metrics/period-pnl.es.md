# 📊 PnL del Periodo (Ganancias y Pérdidas)

*[⬅️ Volver a la Descripción General de Métricas de Rendimiento](index.md)*

## 💡 ¿Qué es el PnL del Periodo?

La ganancia o pérdida monetaria absoluta generada por su cartera dentro de $[t_0, t_1]$, ajustada por flujos de efectivo externos.

---

## 🧮 Fórmula

$$
\boxed{\mathrm{PnL}_{\text{period}} = \mathrm{NAV}(t_1) - \mathrm{NAV}(t_0) - \mathrm{ECF}_{[t_0, t_1]}}
$$

Donde $\mathrm{ECF}$ = Flujos Netos de Efectivo Externos (depósitos − retiradas en el periodo).

---

## 🧮 Descomposición

$$
\mathrm{PnL}_{\text{period}} = \Delta\mathrm{UGL} + \mathrm{Realized} + \mathrm{Income} - \mathrm{Fees} + \mathrm{Other}
$$

| Componente | Definición |
|-----------|-----------|
| $\Delta\mathrm{UGL}$ | Cambio en las ganancias/pérdidas no realizadas durante el periodo |
| Realized | Suma de (producto de la venta − base de costo) para las VENTAS en el periodo |
| Income | DIVIDENDOS + INTERÉS en el periodo |
| Fees | COMISIONES + IMPUESTOS en el periodo |
| Other | Residual (efectos de FX, redondeos) |

---

## 🎯 Contribución por Activo

Para cada posición $(a,b)$:

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{Fees}(a,b)
$$

El conjunto de posiciones incluye **toda la actividad** en el periodo:

$$
\mathcal{P} = \mathcal{P}(t_0) \cup \mathcal{P}(t_1) \cup \text{keys(Realized)} \cup \text{keys(Income)} \cup \text{keys(Fees)}
$$

🔗 Consulte **[Portfolio Engine — §7 Contribución del Periodo](portfolio-engine.md#7-contribucion-del-periodo)** para más detalles.

---

## 📝 Ejemplo

- NAV en $t_0$: €27,000
- Depósitos en el periodo: €1,000
- NAV en $t_1$: €33,000

$$
\mathrm{PnL} = 33\,000 - 27\,000 - 1\,000 = +5\,000 \text{ EUR}
$$

---

## 🔗 Relacionados

- 💼 [NAV](nav.md) — valor terminal de cada fórmula de PnL
- 💸 [Capital Depositado](deposited-capital.md) — PnL Total desde el inicio hasta la fecha
- ⚙️ [Portfolio Engine](portfolio-engine.md) — modelo matemático completo
