# 📊 P&L período (ganancia y pérdida)

## 💡 ¿Qué es el P&L período?

La ganancia o pérdida monetaria absoluta generada por tu cartera dentro de $[t_0, t_1]$, ajustada por los flujos de efectivo externos.

---

## 🧮 Fórmula

$$
\boxed{\mathrm{PnL}_{\text{período}} = \mathrm{NAV}(t_1)-\mathrm{NAV}(t_0)-\Delta \mathrm{CapitalBaseline}_{[t_0,t_1]}}
$$

El delta de la línea base proviene de `cumulative_external_cash_flow`, por lo que incluye flujos de efectivo y capital en especie valorado de ADJUSTMENT/TRANSFER.

---

## 🧮 Descomposición

$$
\mathrm{PnL}_{\text{período}} = \Delta\mathrm{UGL} + \mathrm{Realized} + \mathrm{Income} - \mathrm{FeesTaxes} + \mathrm{Other}
$$

| Componente | Definición |
|-----------|-----------|
| $\Delta\mathrm{UGL}$ | Cambio en el P&L no realizado durante el período — para activos valorados en otra moneda, incluido el efecto del tipo de cambio sobre su coste histórico |
| Realized | Suma de (importe de venta − coste histórico de las unidades vendidas) para SELLs del período; el importe se convierte en la fecha de venta |
| Income | DIVIDEND + INTEREST en el período |
| FeesTaxes | FEE + TAX en el período |
| Other | Residuo que cierra la identidad |

El residuo se calcula como:

$$
\mathrm{Other} = \mathrm{PnL}_{\text{período}} - \Delta\mathrm{UGL} - \mathrm{Realized} - \mathrm{Income} + \mathrm{FeesTaxes}
$$

Como el coste base conserva sus tipos de cambio históricos (véase [Valor contable](book-value.md)), el efecto de los tipos de cambio sobre los activos extranjeros forma parte de $\Delta\mathrm{UGL}$, no de Other. Lo que Other aún contiene es lo que los cuatro componentes no pueden ver, por ejemplo el valor de activos que viajan entre dos brókers en un día límite, o una venta excluida de Realized porque su importe no pudo convertirse o el coste de su posición está incompleto.

---

## 💱 Cambio no realizado por moneda {: #unrealized-change-by-currency }

$\Delta\mathrm{UGL}$ se desglosa por la moneda $A$ en la que se valoran los activos. Para las posiciones en la moneda $A$ en el día $t$, sea

| Símbolo | Significado |
|--------|---------|
| $\mathrm{MV}_A(t)$ | Su valor de mercado en $C^*$, al precio y tipo del día |
| $\mathrm{Cost}^{A}_A(t)$ | Su coste histórico en $A$ |
| $\mathrm{Cost}^{*}_A(t)$ | Su coste histórico en $C^*$ |
| $r_A(t) = \mathrm{fx}(A, C^*, t)$ | El tipo de cambio del día |

El coste de cada adquisición en $A$ proviene de su coste en $C^*$ en la fecha de adquisición, $c^{A} = c^{*} \cdot \mathrm{fx}(C^*, A, d)$ (o del importe pagado, cuando se pagó en $A$). El P&L no realizado se divide entonces exactamente en un **efecto de activo** y un **efecto de tipo de cambio**:

$$
E^{\text{asset}}_A(t) = \mathrm{MV}_A(t) - \mathrm{Cost}^{A}_A(t)\, r_A(t)
$$

$$
E^{\text{fx}}_A(t) = \mathrm{Cost}^{A}_A(t)\, r_A(t) - \mathrm{Cost}^{*}_A(t)
$$

$$
E^{\text{asset}}_A(t) + E^{\text{fx}}_A(t) = \mathrm{MV}_A(t) - \mathrm{Cost}^{*}_A(t) = \mathrm{UGL}_A(t)
$$

Para una cotización expresada en $A$, $\mathrm{MV}_A(t) = \frac{q}{qbq} \cdot \mathrm{mark}_A(t) \cdot r_A(t)$, por lo que el efecto de activo es el cambio propio de los activos en su moneda, convertido al tipo de cambio del día: $E^{\text{asset}}_A(t) = \bigl(\frac{q}{qbq} \cdot \mathrm{mark}_A(t) - \mathrm{Cost}^{A}_A(t)\bigr)\, r_A(t)$. El efecto del tipo de cambio es cero el día de cada compra. Para $A = C^*$, $r = 1$ y $\mathrm{Cost}^{A} = \mathrm{Cost}^{*}$: el efecto del tipo de cambio desaparece, y los activos que ya están en la moneda del informe solo tienen efecto de activo.

Una posición en una moneda $A \neq C^*$ que no puede desglosarse en el día $t$ —sin valor de mercado, sin tipo $r_A(t)$, o con un coste incompleto en cualquiera de las dos monedas— suma todo su $\mathrm{MV} - \mathrm{Cost}^{*}$ (con $\mathrm{MV} = 0$ cuando no tiene valor de mercado) a una parte **no desglosada** $E^{\text{unsplit}}_A(t)$. Las posiciones en $C^*$ siempre cuentan en el efecto de activo.

Las filas del período son los cambios entre los dos estados límite del período —el último estado en o antes de $t_0$ (cero si no hay ninguno) y el estado en $t_1$—, los mismos dos estados que $\Delta\mathrm{UGL}$:

$$
\Delta E^{k}_A = E^{k}_A(t_1) - E^{k}_A(t_0), \qquad k \in \{\text{asset}, \text{fx}, \text{unsplit}\}
$$

$$
\sum_{A}\ \sum_{k} \Delta E^{k}_A = \Delta\mathrm{UGL} \quad \text{exactamente}
$$

??? example "Ejemplo: un ETF estadounidense en un panel en euros"

    10 unidades compradas por 400 € cuando valían 500 USD, por lo que $\mathrm{Cost}^{*} = 400$ EUR y $\mathrm{Cost}^{A} = 500$ USD.

    | Día | Valor en USD | $r_{USD}$ | MV en EUR | $E^{\text{asset}}$ | $E^{\text{fx}}$ | $\mathrm{UGL}$ |
    |-----|-------|-----------|---------------|--------------------|-----------------|----------------|
    | $t_0$ | 520 USD | 0.78 | 405.60 | $(520-500) \times 0.78 = 15.60$ | $500 \times 0.78 - 400 = -10.00$ | 5.60 |
    | $t_1$ | 550 USD | 0.75 | 412.50 | $(550-500) \times 0.75 = 37.50$ | $500 \times 0.75 - 400 = -25.00$ | 12.50 |

    $$
    \Delta E^{\text{asset}} = +21.90, \qquad \Delta E^{\text{fx}} = -15.00, \qquad \Delta\mathrm{UGL} = +6.90 \text{ EUR}
    $$

    El ETF ganó en dólares (+€21.90), el dólar perdió terreno frente al euro (−€15.00): juntos, los +€6.90 del P&L no realizado del período.

---

## 🎯 Contribución por activo

Para cada posición $(a,b)$:

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{FeesTaxes}(a,b)
$$

El conjunto de posiciones incluye **toda la actividad** del período:

$$
\mathcal{P} = \text{posiciones con actividad BUY/SELL/ADJUSTMENT/TRANSFER o cantidad límite}
$$

El rendimiento anualizado del período fija el inicio de su ventana en la fecha más tardía entre el inicio solicitado y la fecha del lote abierto más antiguo. Utiliza $|\mathrm{StartValue}|$ como base de anualización, y recurre al coste base final para las posiciones abiertas a mitad del período. Véase [Rendimiento neto anualizado](net-annualized-return.md).

🔗 Véase **[Motor de cartera — §7 Contribución del período](index.md#7-period-contribution)** para más detalles.

---

## 📝 Ejemplo

- NAV en $t_0$: €27,000
- Aumento de la línea base de capital en el período: €1,000
- NAV en $t_1$: €33,000

$$
\mathrm{PnL} = 33\,000 - 27\,000 - 1\,000 = +5\,000 \text{ EUR}
$$

---

## 🔗 Relacionado

- 💼 [NAV](nav.md) — punto final de cada fórmula de P&L
- 📖 [Valor contable](book-value.md) — coste base histórico detrás del P&L no realizado
- 💸 [Capital depositado](deposited-capital.md) — P&L total desde el inicio
- ⚙️ [Motor de cartera](index.md) — modelo matemático completo
- 📈 [Resumen de métricas de rendimiento](../index.md) — todas las métricas de rendimiento de un vistazo
