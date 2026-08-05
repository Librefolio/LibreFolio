# 📊 PnL del Período (Ganancias y Pérdidas)

*[⬅️ Volver a la Descripción General de Métricas de Rendimiento](../index.md)*

## 💡 ¿Qué es el PnL del Período?

La ganancia o pérdida monetaria absoluta generada por tu cartera dentro de $[t_0, t_1]$, ajustada por flujos de efectivo externos.

---

## 🧮 Fórmula

$$
\boxed{\mathrm{PnL}_{\text{period}} = \mathrm{NAV}(t_1)-\mathrm{NAV}(t_0)-\Delta \mathrm{CapitalBaseline}_{[t_0,t_1]}}
$$

El delta de la línea base proviene de `cumulative_external_cash_flow`, por lo que incluye flujos de efectivo y capital valorado en especie por ADJUSTMENT/TRANSFER.

---

## 🧮 Descomposición

$$
\mathrm{PnL}_{\text{period}} = \Delta\mathrm{UGL} + \mathrm{Realized} + \mathrm{Income} - \mathrm{FeesTaxes} + \mathrm{Other}
$$

| Componente | Definición |
|-----------|-----------|
| $\Delta\mathrm{UGL}$ | Cambio en la ganancia/pérdida no realizada durante el período |
| Realized | Suma de (ingresos por venta − base de costo) para SELLs en el período |
| Income | DIVIDEND + INTEREST en el período |
| FeesTaxes | FEE + TAX en el período |
| Other | Residual que completa la identidad |

El residual se calcula como:

$$
\mathrm{Other} = \mathrm{PnL}_{\text{period}} - \Delta\mathrm{UGL} - \mathrm{Realized} - \mathrm{Income} + \mathrm{FeesTaxes}
$$

---

## 🎯 Contribución por Activo

Para cada posición $(a,b)$:

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{FeesTaxes}(a,b)
$$

El conjunto de posiciones incluye **toda la actividad** en el período:

$$
\mathcal{P} = \text{posiciones con actividad BUY/SELL/ADJUSTMENT/TRANSFER o cantidad en los límites del período}
$$

El retorno anualizado del período limita el inicio de su ventana al más tardío entre el inicio solicitado y la fecha de lote abierto más antigua. Utiliza $|\mathrm{StartValue}|$ como base de anualización, recurriendo a la base de costo final para posiciones abiertas a mitad del período. Ver [Retorno Neto Anualizado](net-annualized-return.md).

🔗 Ver **[Portfolio Engine — §7 Contribución del Período](index.md#7-period-contribution)** para más detalles.

---

## 📝 Ejemplo

- NAV en $t_0$: €27,000
- Aumento de la línea base de capital en el período: €1,000
- NAV en $t_1$: €33,000

$$
\mathrm{PnL} = 33\,000 - 27\,000 - 1\,000 = +5\,000 \text{ EUR}
$$

---

## 🔗 Relacionados

- 💼 [NAV](nav.md) — punto extremo de toda fórmula de PnL
- 💸 [Capital Depositado](deposited-capital.md) — PnL Total desde el inicio hasta la fecha
- ⚙️ [Portfolio Engine](index.md) — modelo matemático completo
