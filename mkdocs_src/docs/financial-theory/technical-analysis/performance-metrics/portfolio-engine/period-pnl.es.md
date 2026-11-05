# 📊 P&L período (ganancias y pérdidas)

## 💡 ¿Qué es el P&L período?

La ganancia o pérdida monetaria absoluta generada por su cartera dentro de $[t_0, t_1]$, ajustada por los flujos de efectivo externos.

---

## 🧮 Fórmula

$$
\boxed{\mathrm{PnL}_{\text{period}} = \mathrm{NAV}(t_1)-\mathrm{NAV}(t_0)-\Delta \mathrm{CapitalBaseline}_{[t_0,t_1]}}
$$

El delta de la línea base proviene de `cumulative_external_cash_flow`, por lo que incluye los flujos de efectivo y el capital en especie valorado procedente de ADJUSTMENT/TRANSFER. Un ADJUSTMENT saliente no tiene valor y no saca nada ([Capital depositado — Ajustes salientes](deposited-capital.md#outgoing-adjustments)).

---

## 🧮 Descomposición

$$
\mathrm{PnL}_{\text{period}} = \Delta\mathrm{UGL} + \mathrm{Realized} + \mathrm{Income} - \mathrm{FeesTaxes} + \mathrm{Other}
$$

| Componente | Definición |
|-----------|-----------|
| $\Delta\mathrm{UGL}$ | Variación de la ganancia/pérdida no realizada durante el período: valor de mercado − coste base abierto de las posiciones mantenidas en cada límite, excluidos los valores en tránsito ([el P&L no realizado del período](index.md#two-unrealized-figures)) — para activos valorados en otra divisa, incluido el efecto del tipo de cambio sobre su coste histórico |
| Realized | Suma de (importe recibido − coste histórico de las unidades entregadas) para las SELL del período y los ADJUSTMENT salientes no vinculados a un desdoblamiento, cuyo importe recibido es cero; los importes recibidos se convierten a la fecha de la transacción ([Motor de cartera — §8](index.md#8-realized-gain-loss)) |
| Income | DIVIDEND + INTEREST en el período |
| FeesTaxes | FEE + TAX en el período |
| Other | Lo que cierra la identidad: el resultado de cambio sobre el efectivo mantenido en otra divisa (efecto del tipo de cambio sobre el efectivo), la ganancia que los valores acumularon fuera de la vista antes de cruzar su límite (transferencias a valor de mercado), más un residual |

Other se calcula como:

$$
\mathrm{Other} = \mathrm{PnL}_{\text{period}} - \Delta\mathrm{UGL} - \mathrm{Realized} - \mathrm{Income} + \mathrm{FeesTaxes}
$$

Debido a que el coste base conserva sus tipos de cambio históricos (véase [Valor contable](book-value.md)), el efecto de los tipos de cambio sobre los activos extranjeros forma parte de $\Delta\mathrm{UGL}$, no de Other. El efectivo mantenido en otra divisa es diferente: NAV y el valor contable lo valoran ambos al tipo de cambio de cada día, por lo que su efecto cambiario se cancela en la ganancia/pérdida no realizada y no está en $\Delta\mathrm{UGL}$. Es la primera parte de Other, el [efecto del tipo de cambio sobre el efectivo](#fx-on-cash) de cada bróker $b$, que la vista de Período muestra por bróker. La segunda parte, las [transferencias a valor de mercado](#transfers-at-market-value), también se muestran por bróker:

$$
\mathrm{Other} = \sum_{b \in S} \mathrm{FXonCash}_b + \sum_{b \in S} \mathrm{TMV}_b + \mathrm{Residual}
$$

El residual contiene lo que ni los cuatro componentes, ni el resultado de cambio sobre el efectivo, ni las transferencias a valor de mercado pueden ver:

- el movimiento del tipo de cambio del efectivo mientras viaja entre dos brókeres: en tránsito, no pertenece al saldo de ningún bróker;
- el coste de un cambio de divisas, en un bróker o entre dos: −1.000 USD que valen €920 al tipo de cambio del día, cambiados por +€900, dan −€20, que no es ni una comisión ni una venta;
- el valor de activos que viajan entre dos brókeres en un día límite;
- una venta excluida de Realized porque su importe recibido no pudo convertirse, o una venta o un ADJUSTMENT saliente excluidos porque el coste de su posición está incompleto.
- el coste del dust: una venta que deja $10^{-5}$ unidades o menos en una posición saca lo que queda del coste base abierto sin venderlo, así que su coste no está ni en $\Delta\mathrm{UGL}$ ni en Realized — 0,00001 unidades compradas a 100.000 dejan −1,00 aquí ([§7](index.md#7-period-contribution)).

### 💵 Efecto del tipo de cambio sobre el efectivo {: #fx-on-cash }

Para cada bróker $b$ que mantiene efectivo en una divisa distinta de $C^*$, durante el período $(t_0, t_1]$, siendo $t_0$ el estado de apertura:

$$
\mathrm{FXonCash}_b = \sum_{c \neq C^*} \Bigl[N_{b,c}(t_1)\,\mathrm{fx}(c, C^*, t_1) - N_{b,c}(t_0)\,\mathrm{fx}(c, C^*, t_0)\Bigr] - \sum_{\substack{m \in (t_0, t_1] \\ \mathrm{ccy}(m) \neq C^*}} s_m \cdot \mathrm{amount}_m \cdot \mathrm{fx}(\mathrm{ccy}(m), C^*, d_m)
$$

$N_{b,c}(t)$ es el saldo que $b$ mantiene en la divisa $c$ en $t$, escalado por la participación del bróker, y $\mathrm{fx}$ el último tipo de cambio en o antes del día. La segunda suma recorre los movimientos de $b$ en una divisa extranjera fechados en el período: cada importe, escalado por la participación $s_m$, al tipo de cambio de su propia fecha $d_m$. El primer término es el cambio de valor del efectivo extranjero, el segundo lo que los movimientos aportaron o retiraron: la diferencia es lo que los tipos de cambio hicieron con el efectivo que mantenía el bróker. Es igual a los resultados de cambio sobre el efectivo que el motor registra en los días de cambio de tipo del período ([Motor de cartera — §6](index.md#exchange-result-on-foreign-cash)). El efectivo en $C^*$ no tiene ninguno.

??? example "Ejemplo: dólares en un bróker con un panel en euros"

    Un bróker mantiene 1.000 USD durante todo el período mientras el tipo de cambio pasa de 0,90 a 0,92 EUR por USD:

    $$
    \mathrm{FXonCash} = 1\,000 \times 0{,}92 - 1\,000 \times 0{,}90 = +20 \text{ EUR}
    $$

    Con un depósito de 500 USD a mitad del período a 0,91, y 0,92 al final:

    $$
    \mathrm{FXonCash} = 1\,500 \times 0{,}92 - 1\,000 \times 0{,}90 - 500 \times 0{,}91 = 1\,380 - 900 - 455 = +25 \text{ EUR}
    $$

    El depósito entró en el capital a €455; los +€25 son lo que ganaron los dólares frente al euro mientras el bróker los mantenía.

### 🔀 Transferencias a valor de mercado {: #transfers-at-market-value }

En una vista que selecciona solo algunos brókeres, un tramo TRANSFER cuya otra parte está fuera de la vista — valores enviados a un bróker no seleccionado, recibidos de uno, o una transferencia sin contraparte — es capital en especie a su valor de mercado en su fecha, mientras el coste de la posición se mueve con él ([Capital depositado](deposited-capital.md)). Por tanto, la ganancia que las unidades acumularon en el otro bróker no está ni en $\Delta\mathrm{UGL}$ ni en Realized, y solía terminar en el residual. Es la segunda parte de Other. Para cada bróker $b$ de la vista, sobre los tramos $\ell$ fechados en $(t_0, t_1]$:

$$
\mathrm{TMV}_b = \sum_{\ell \in (t_0, t_1]} \bigl(\mathrm{Cost}_\ell - \mathrm{Capital}_\ell\bigr)
$$

$\mathrm{Capital}_\ell$ es el valor de mercado que el tramo añade al capital (positivo cuando se recibe, negativo cuando se envía) y $\mathrm{Cost}_\ell$ el coste que mueve en la posición (mismo signo), ambos en $C^*$ según la participación del bróker. Para unidades con valor de mercado $\mathrm{MV}$ y coste $C$:

| Tramo | $\mathrm{Capital}$ | $\mathrm{Cost}$ | Contribución |
|-----|---------|------|--------------|
| Enviado fuera de la vista | $-\mathrm{MV}$ | $-C$ | $+(\mathrm{MV} - C)$ |
| Recibido desde fuera de la vista | $+\mathrm{MV}$ | $+C$ | $-(\mathrm{MV} - C)$ |

La vista del emisor toma como resultado propio la ganancia que las unidades obtuvieron mientras las mantuvo; la vista del receptor parte del valor con el que llegan, así que lo que ganaron antes no es su resultado y se excluye. Una cifra por debajo del umbral de redondeo no se muestra, y el residual disminuye en el importe mostrado. Con ambos brókeres seleccionados no cambia nada: el par es interno, y las unidades solo reparten el resultado entre las dos filas (véase la transferencia interna en Contribución por activo más abajo).

??? example "Ejemplo: unidades compradas en un bróker y enviadas a otro"

    10 unidades compradas a 50 cada una (coste €500) en el bróker A se envían al bróker B cuando valen €800.

    - **Vista solo en A:** las unidades salen con €800 de capital y se llevan €500 de coste: $\mathrm{TMV}_A = -500 + 800 = +300$ EUR.
    - **Vista solo en B:** las unidades llegan con €800 de capital y €500 de coste: $\mathrm{TMV}_B = 500 - 800 = -300$ EUR.
    - **Vista en A y B:** no hay tal fila.

---

## 💱 Variación no realizada por divisa {: #unrealized-change-by-currency }

$\Delta\mathrm{UGL}$ se divide por la divisa $A$ en la que están valorados los activos. Para las posiciones en la divisa $A$ en el día $t$, sea

| Símbolo | Significado |
|--------|---------|
| $\mathrm{MV}_A(t)$ | Su valor de mercado en $C^*$, al precio y tipo de cambio del día |
| $\mathrm{Cost}^{A}_A(t)$ | Su coste histórico en $A$ |
| $\mathrm{Cost}^{*}_A(t)$ | Su coste histórico en $C^*$ |
| $r_A(t) = \mathrm{fx}(A, C^*, t)$ | El tipo de cambio del día |

El coste de cada adquisición en $A$ proviene de su coste en $C^*$ en la fecha de adquisición, $c^{A} = c^{*} \cdot \mathrm{fx}(C^*, A, d)$ (o del importe pagado, cuando se paga en $A$). La ganancia/pérdida no realizada se descompone entonces exactamente en un **efecto del activo** y un **efecto del tipo de cambio**:

$$
E^{\text{asset}}_A(t) = \mathrm{MV}_A(t) - \mathrm{Cost}^{A}_A(t)\, r_A(t)
$$

$$
E^{\text{fx}}_A(t) = \mathrm{Cost}^{A}_A(t)\, r_A(t) - \mathrm{Cost}^{*}_A(t)
$$

$$
E^{\text{asset}}_A(t) + E^{\text{fx}}_A(t) = \mathrm{MV}_A(t) - \mathrm{Cost}^{*}_A(t) = \mathrm{UGL}_A(t)
$$

Para una cotización expresada en $A$, $\mathrm{MV}_A(t) = \frac{q}{qbq} \cdot \mathrm{mark}_A(t) \cdot r_A(t)$, por lo que el efecto del activo es el cambio propio de los activos en su divisa, traducido al tipo de cambio del día: $E^{\text{asset}}_A(t) = \bigl(\frac{q}{qbq} \cdot \mathrm{mark}_A(t) - \mathrm{Cost}^{A}_A(t)\bigr)\, r_A(t)$. El efecto del tipo de cambio es cero el día de cada compra. Para $A = C^*$, $r = 1$ y $\mathrm{Cost}^{A} = \mathrm{Cost}^{*}$: el efecto del tipo de cambio desaparece, y los activos que ya están en la divisa del informe tienen solo un efecto del activo.

Una posición en una divisa $A \neq C^*$ que no puede dividirse el día $t$ — sin valor de mercado, sin tipo de cambio $r_A(t)$, o con un coste incompleto en cualquiera de las dos divisas — suma todo su $\mathrm{MV} - \mathrm{Cost}^{*}$ (con $\mathrm{MV} = 0$ cuando no tiene valor de mercado) a una parte **sin dividir** $E^{\text{unsplit}}_A(t)$. Las posiciones en $C^*$ siempre cuentan en el efecto del activo. Una posición valorada a su coste porque su activo no tiene ningún precio de referencia ([Motor de cartera — §3](index.md#3-position-state)) tiene $\mathrm{MV} = \mathrm{Cost}^{*}$ y no se suma a ninguna parte: dividirla inventaría un efecto del activo y un efecto del tipo de cambio de signo opuesto.

Las filas del período son los cambios entre los dos estados límite del período — el último estado en o antes de $t_0$ (cero si no hay ninguno) y el estado en $t_1$ —, los mismos dos estados que $\Delta\mathrm{UGL}$:

$$
\Delta E^{k}_A = E^{k}_A(t_1) - E^{k}_A(t_0), \qquad k \in \{\text{asset}, \text{fx}, \text{unsplit}\}
$$

$$
\sum_{A}\ \sum_{k} \Delta E^{k}_A = \Delta\mathrm{UGL} \quad \text{exactamente}
$$

??? example "Ejemplo: un ETF estadounidense en un panel en euros"

    10 unidades compradas por €400 cuando valían 500 USD, así que $\mathrm{Cost}^{*} = 400$ EUR y $\mathrm{Cost}^{A} = 500$ USD.

    | Día | Valor en USD | $r_{USD}$ | MV en EUR | $E^{\text{asset}}$ | $E^{\text{fx}}$ | $\mathrm{UGL}$ |
    |-----|-------|-----------|---------------|--------------------|-----------------|----------------|
    | $t_0$ | 520 USD | 0,78 | 405,60 | $(520-500) \times 0{,}78 = 15{,}60$ | $500 \times 0{,}78 - 400 = -10{,}00$ | 5,60 |
    | $t_1$ | 550 USD | 0,75 | 412,50 | $(550-500) \times 0{,}75 = 37{,}50$ | $500 \times 0{,}75 - 400 = -25{,}00$ | 12,50 |

    $$
    \Delta E^{\text{asset}} = +21{,}90, \qquad \Delta E^{\text{fx}} = -15{,}00, \qquad \Delta\mathrm{UGL} = +6{,}90 \text{ EUR}
    $$

    El ETF ganó en dólares (+€21,90), el dólar perdió terreno frente al euro (−€15,00): juntos, los +€6,90 de la variación no realizada del período.

---

## 🎯 Contribución por activo

Para cada posición $(a,b)$:

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{FeesTaxes}(a,b)
$$

El conjunto de posiciones incluye **toda la actividad** del período:

$$
\mathcal{P} = \text{posiciones con actividad BUY/SELL/ADJUSTMENT/TRANSFER o cantidad en el límite}
$$

Los valores inicial y final de una posición son la valoración propia de la cartera en el cierre de $t_0$ y de $t_1$, los dos estados de $\Delta\mathrm{UGL}$ ([Motor de cartera — §3](index.md#3-position-state)):

- su precio de referencia ([§2](index.md#2-valuation-price)): una cotización de mercado o, en su defecto, un precio de BUY/SELL — o, para un activo sin nada más todavía, el coste de una transferencia entrante como estimación —, reexpresándose un precio de operación tras cualquier desdoblamiento posterior;
- su coste base, para una posición cuyo activo no tiene ningún precio de referencia (`ESTIMATED_AT_COST`);
- convertidos al tipo de cambio del propio día límite.

Las filas, por tanto, cuadran con la cartera: cuando se conoce cada fila, $\sum_{(a,b)} \Delta\mathrm{UGL}(a,b) = \Delta\mathrm{UGL}$, y las filas más los demás efectos del período — ingresos y costes no asignados, efecto del tipo de cambio sobre el efectivo, transferencias a valor de mercado, el residual — cierran $\mathrm{PnL}_{\text{period}}$. Other no contiene ninguna diferencia de valoración. Una posición que queda con $10^{-5}$ unidades o menos — dust — no la mantiene ni una fila ni la cartera, así que no cambia nada en la identidad ([§3](index.md#3-position-state)); su coste está en el residual (arriba).

- **Transferencia interna.** Un valor movido entre dos de sus brókeres dentro del período divide su resultado: la fila del bróker emisor responde por las unidades hasta que llegan, la del bróker receptor desde su llegada, y el total no cambia. Una transferencia que ya está en tránsito en $t_0$, o que sigue en tránsito en $t_1$, conserva los valores límite simples ([§7](index.md#7-period-contribution)).
- **Valores desconocidos.** Una posición mantenida en un límite cuyo P&L no realizado es desconocido allí — un tipo de cambio faltante, un coste incompleto — tiene un $\Delta\mathrm{UGL}(a,b)$ desconocido, nunca el lado conocido menos cero.

El rendimiento anualizado del período limita el inicio de su ventana al más tardío entre el inicio solicitado y la fecha del lote abierto más antiguo. Usa $|\mathrm{StartValue}|$ como base de anualización, recurriendo al coste base final para las posiciones abiertas a mitad del período. Véase [Rendimiento neto anualizado](net-annualized-return.md).

Una posición cerrada en el período — sin nada restante en $t_1$ — se anualiza de forma diferente: sobre el coste histórico de las unidades que la abandonaron en el período — vendidas o movidas a otro bróker del ámbito — durante el tiempo que se mantuvo dentro de ella, desde el más tardío entre $t_0$ y su primera apertura hasta el día en que salieron sus últimas unidades. Su porcentaje del período mantiene $|\mathrm{StartValue}|$ como base. Véase [Rendimiento neto anualizado — Posiciones cerradas en el período](net-annualized-return.md#closed-in-period).

🔗 Véase **[Motor de cartera — §7 Contribución del período](index.md#7-period-contribution)** para más detalles.

---

## 📝 Ejemplo

- NAV en $t_0$: €27.000
- Aumento de la línea base de capital en el período: €1.000
- NAV en $t_1$: €33.000

$$
\mathrm{PnL} = 33\,000 - 27\,000 - 1\,000 = +5\,000 \text{ EUR}
$$

---

## 🔗 Relacionado

- 💼 [NAV](nav.md) — punto final de toda fórmula de P&L
- 📖 [Valor contable](book-value.md) — coste base histórico detrás de la ganancia/pérdida no realizada
- 💸 [Capital depositado](deposited-capital.md) — P&L total desde el inicio hasta la fecha
- ⚙️ [Motor de cartera](index.md) — modelo matemático completo
- 📈 [Resumen de métricas de rendimiento](../index.md) — todas las métricas de rendimiento de un vistazo
