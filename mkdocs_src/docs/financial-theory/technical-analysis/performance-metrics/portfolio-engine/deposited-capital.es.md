# 💸 Capital depositado, P&L total y pools de efectivo

## 💡 Resumen del concepto

**Base de capital** = capital económico acumulado aportado desde el inicio:

$$
\mathrm{CapitalBaseline}(t)=
\sum_{\tau \leq t}\mathrm{ExternalCashFlow}(\tau)
+ \sum_{\tau \leq t}\mathrm{InKindCapital}(\tau)
$$

**P&L total** = todo el valor generado por encima de las aportaciones externas:

$$
\boxed{\mathrm{TotalPnL}(t) = \mathrm{NAV}(t) - \mathrm{CapitalBaseline}(t)}
$$

`InKindCapital` cubre los valores que entran o salen del ámbito sin efectivo:

- filas ADJUSTMENT entrantes que llevan un coste base (`cost_basis_override`, no vinculado a un desdoblamiento), **a coste**: el coste que añaden a la posición; una fila saliente nunca cuenta: no tiene valor ([Ajustes salientes](#outgoing-adjustments));
- patas de TRANSFER cuya otra pata no está en el ámbito —está en un bróker fuera de la vista, falta o nunca se vinculó— **a valor de mercado** en su propia fecha: $+$ para los valores recibidos, $-$ para los valores enviados. Una pata recibida con un coste base, para un título sin cotización y sin otra operación en o antes de su fecha, da al título su precio: su propio coste, como una [estimación](price-resolution.md#transfer-cost-estimate), así que en su fecha su valor de mercado es ese coste y la pata es neutra. Un título sin ningún precio en esa fecha —sin cotización, sin BUY ni SELL y sin tal estimación en o antes de ella— cuenta **a coste** en su lugar: el coste que la pata mueve en su posición, el coste que añade una pata recibida o el precio medio de compra que elimina una pata enviada. Un coste desconocido cuenta como cero, igual que en el coste propio de la posición. Mientras el coste de la posición esté completo, el NAV valora la posición a ese mismo coste y la pata es neutra; con parte del coste desconocida, la posición no tiene valor en el NAV, pero la pata aún mueve su coste conocido, así que no queda nada en el capital una vez que las unidades desaparecen. No cuenta nada si el título no se puede valorar ese día: tiene un precio, pero falta el tipo de cambio.

Estas filas mueven valor sin efectivo: son capital, no ganancias ni pérdidas. Un ADJUSTMENT saliente no es capital: realiza como pérdida el precio medio de compra al que renuncia su posición.

---

## 🎯 Qué cuenta

| Transacción | Efecto sobre la base de capital |
|------------|-----------------|
| DEPOSIT / WITHDRAWAL (sin vincular) | ✅ Sí |
| CASH\_TRANSFER / FX\_CONVERSION cuya otra pata está fuera de la vista, falta o nunca se vinculó (huérfana) | ✅ Sí, por su importe, como un depósito o un retiro |
| CASH\_TRANSFER / FX\_CONVERSION / TRANSFER con ambas patas en la vista (pareja interna) | ❌ No. Por bróker, una pareja entre dos brókeres mueve capital del remitente al receptor el día de llegada, sumando cero ([Transferencias internas](#internal-transfers-broker-lines)) |
| TRANSFER de valores cuya otra pata está fuera de la vista, falta o nunca se vinculó (huérfana) | ✅ Sí, capital en especie a valor de mercado en su fecha, o a coste para un título sin ningún precio |
| ADJUSTMENT entrante con `cost_basis_override`, no vinculado a un desdoblamiento | ✅ Sí, capital en especie a coste |
| ADJUSTMENT saliente | ❌ No: no tiene valor, y realiza el coste de sus unidades como pérdida ([más abajo](#outgoing-adjustments)) |
| ADJUSTMENT vinculado a un desdoblamiento | ❌ No, solo reescala la cantidad |
| BUY, SELL, DIVIDEND, INTEREST, FEE, TAX | ❌ No |
| Variación del tipo de cambio en efectivo mantenido en otra divisa (sin transacción) | ❌ No: un resultado, parte de TotalPnL; los flujos de capital (depósitos, retiros, patas de efectivo huérfanas) entraron en la base de capital al tipo de sus propias fechas |

---

## 📤 Ajustes salientes {: #outgoing-adjustments }

Un ADJUSTMENT que elimina $|q|$ unidades del activo $a$ del bróker $b$ en la fecha $d$ —unidades cedidas, enviadas a una cuenta que LibreFolio no rastrea o eliminadas por una corrección— **no tiene valor**, sea cual sea el coste base que tenga la fila: solo reduce la cantidad. La posición cede el coste histórico de esas unidades, a su [precio medio de compra (PMC)](../weighted-average-cost.md) antes del ajuste, cada compra al tipo de su propia fecha, y no vuelve nada:

$$
C = s_b \cdot |q| \cdot w_{\text{pre}}(a,b)
$$

$$
\Delta\mathrm{CapitalBaseline}(d) = 0, \qquad \mathrm{Realized} = -C
$$

$s_b$ es la [participación](../../../../user/brokers/sharing.md) del bróker.

- **Capital.** No sale nada de la base de capital, ni del capital de la línea del bróker $b$. No se mueve efectivo, así que los [pools de efectivo](#three-pool-cash-model) no cambian.
- **Realizado.** $-C$ cuenta en la ganancia o pérdida realizada del período y en la contribución de la posición ([P&L período](period-pnl.md)), y se deja fuera, como una venta, cuando el coste de la posición está incompleto. El precio medio de compra de las unidades restantes no cambia.
- **Rendimientos.** TWRR y MWRR toman sus flujos de los cambios de la base de capital, así que el ajuste no es un flujo: el valor de las unidades sale del NAV, y la rentabilidad del día lo lee como una pérdida.

Un ADJUSTMENT vinculado a un desdoblamiento es la excepción (tabla anterior): solo reescala la cantidad. Las unidades que salen por dinero son una SELL.

!!! example "Dos acciones cedidas"

    Divisa de informe EUR, participación del 100 %. Un depósito de 500 € compra 10 acciones a 50 €; el precio sube a 80 €. Un ADJUSTMENT de −2 acciones cede dos, con el precio sin cambios ese día: $C = 2 \times 50 = 100$.

    | Momento | NAV | CapitalBaseline | TotalPnL | Realizado |
    |--------|-----|-----------------|----------|----------|
    | Antes del ajuste | 800 | 500 | +300 | 0 |
    | Después del ajuste | 640 | 500 | +140 | −100 |

    Las 8 acciones restantes mantienen un precio medio de compra de 50 €, por lo que su ganancia no realizada es $8 \times (80 - 50) = 240$, y $-100 + 240 = +140$. El flujo del día es 0, por lo que la TWRR lee $640 / 800 - 1 = -20\%$ ese día.

---

## 🔀 Transferencias internas en las líneas de bróker {: #internal-transfers-broker-lines }

Con dos o más brókeres en el ámbito, el [gráfico de P&L](../../../../user/dashboard/charts.md#pnl-line) dibuja una línea por bróker. Cada bróker $b \in S$ tiene su propio NAV, capital y P&L:

$$
\mathrm{PnL}_b(t) = \mathrm{NAV}_b(t) - C_b(t)
$$

$$
\mathrm{NAV}_b(t) = \mathrm{MV}_b(t) + \mathrm{Cash}_b(t) + \mathrm{InTransit}_b(t)
$$

$$
C_b(t) = \sum_{\tau \leq t}\mathrm{ExternalCashFlow}_b(\tau) + \sum_{\tau \leq t}\mathrm{InKindCapital}_b(\tau) + \sum_{\tau \leq t}\mathrm{Internal}_b(\tau)
$$

$\mathrm{InTransit}_b$ es el valor en tránsito que salió de $b$, y $\mathrm{Internal}_b$ es el lado de $b$ de las transferencias internas descritas abajo. Dado que $\sum_b \mathrm{NAV}_b = \mathrm{NAV}$ y los flujos internos se cancelan cada día, las líneas suman las cifras del ámbito:

$$
\sum_{b \in S}\mathrm{Internal}_b(t) = 0
\quad\Rightarrow\quad
\sum_{b \in S} C_b(t) = \mathrm{CapitalBaseline}(t),
\qquad
\sum_{b \in S}\mathrm{PnL}_b(t) = \mathrm{TotalPnL}(t)
$$

La línea de un bróker es, por tanto, el P&L obtenido mientras el valor estaba en ese bróker, o viajando desde él. No es la ganancia no realizada de las posiciones que mantiene el bróker.

### 📐 El flujo interno

Una **pareja interna** es un CASH\_TRANSFER, FX\_CONVERSION o TRANSFER vinculado cuyas dos patas están ambas en $S$, en dos brókeres diferentes: el remitente $A$ (la pata que sale) y el receptor $B$ (la pata que entra). Produce un flujo, en el **día de llegada** $t_{arr}$, la fecha de la pata posterior:

$$
\mathrm{Internal}_A(t_{arr}) = -X,
\qquad
\mathrm{Internal}_B(t_{arr}) = +X,
\qquad
X = s_A \cdot V(t_{arr})
$$

$s_A$ es la [participación](../../../../user/brokers/sharing.md) del remitente y $V(t_{arr})$ el valor completo que la llegada aporta a $B$ ese día, valorado exactamente como lo valora el NAV:

| Pareja | $V(t_{arr})$ |
|------|--------------|
| CASH\_TRANSFER | El importe recibido, convertido al tipo $\mathrm{fx}(c, C^*, t_{arr})$ |
| FX\_CONVERSION entre brókeres | La pata recibida, convertida de la misma forma: $-1{,}000$ USD en $A$ → $+900$ EUR en $B$ da $V = 900$ EUR, y el coste de la conversión permanece en la línea de $A$ |
| TRANSFER de valores | $\mathrm{MV}$ de la cantidad recibida al [precio de valoración](index.md#2-valuation-price) de $t_{arr}$, el último precio conocido arrastrado si no hay ninguno ese día. Sin ningún precio en o antes de $t_{arr}$, el coste base que las unidades añaden a la posición de $B$ —el coste registrado en la pata de $B$, convertido en la fecha de esa pata—, ya que el NAV valora a coste una posición sin precio ([§3](index.md#3-position-state)) |

Con participaciones iguales, $X$ es exactamente lo que la llegada añade a $\mathrm{NAV}_B$, así que ninguna línea salta. El $\mathrm{CapitalBaseline}$ del ámbito no se toca, porque un movimiento interno no es capital externo: NAV, CapitalBaseline, TotalPnL y sus velas, ROI, TWRR, MWRR y efectivo son los mismos que sin el flujo. Solo cambia el reparto de la base entre los brókeres.

### ✈️ Valor en tránsito

Cuando las patas caen en días distintos, el valor viaja desde el día de salida $t_{dep}$ hasta el día anterior a $t_{arr}$. Mientras tanto, forma parte de $\mathrm{InTransit}_A$, con la participación del remitente $s_A$, valorado cada día: el efectivo al tipo de cambio de ese día, los valores al precio de valoración de ese día (al coste registrado en la transferencia si el título no tiene ningún precio). No ocurre ningún flujo mientras el valor viaja, así que sus variaciones de precio y tipo de cambio permanecen en la línea de $A$, incluida la variación del propio día de llegada; la línea de $B$ parte del valor recibido.

Por ejemplo, $A$ recibe un depósito de 1.000 USD el día 0 a 0,90 EUR por USD ($C_A = 900$) y envía los dólares el día 1; $B$ los recibe el día 4. Con el tipo a 0,90, 0,91, 0,92, 0,93 en los días 1–4, la línea de $A$ marca 0, +10, +20, +30 y la de $B$ se mantiene en 0. El día 4, $X = 930$ y $C_A = 900 - 930 = -30$. Una vez llegados, los dólares son efectivo de $B$, revalorizado cada día, así que desde el día 5 la línea de $B$ se mueve con el tipo: a 0,94, marca +10.

### 🧩 Casos especiales

- **Participaciones diferentes.** $X$ usa $s_A$, como el valor en tránsito, mientras que la llegada añade $s_B \cdot V(t_{arr})$ a $\mathrm{NAV}_B$. La línea de $B$ conserva un escalón residual de $(s_B - s_A)\,V(t_{arr})$ el día de llegada, y TotalPnL muestra el mismo escalón, con o sin el flujo.
- **Valor desconocido el día de llegada.** Si $V(t_{arr})$ no se puede calcular —falta un tipo de cambio, o el título no tiene observación en o antes de $t_{arr}$ ($\operatorname{mark} = \varnothing$) y el coste en la pata de $B$ es desconocido (sin coste base, o con uno sin tipo de cambio), de modo que la llegada no añade nada al coste de la posición de $B$—, entonces $X = 0$. No se adivina nada: el salto permanece, y el valor del título aparece en la línea del bróker que lo mantiene desde su primer precio.
- **Ningún precio en absoluto.** Un título sin observación en o antes de $t_{arr}$ se mueve al coste que su llegada añade a la posición de $B$ —el coste registrado en la pata de $B$, el precio medio de compra del remitente cuando la transferencia se guarda con un coste base automático—, tanto si el coste de $B$ está completo como si no. Con el coste de $B$ completo, ese es el valor al que $\mathrm{NAV}_B$ toma las unidades, así que con participaciones iguales la línea de $B$ no salta. El coste no tiene por qué igualar el valor que las unidades tenían en $A$ antes de salir, el propio coste base de $A$ o nada cuando ese coste estaba incompleto; la diferencia acaba en la línea de $A$, y TotalPnL también la muestra. Con el coste de $B$ incompleto —$B$ ya mantenía unidades de coste desconocido—, la posición de $B$ no tiene valor en el NAV, que está incompleto: la línea de $B$ absorbe la brecha, su propio coste desconocido, y la línea de $A$ es la misma que con un coste completo en $B$.
- **Comisiones.** No forman parte de $X$. Una fila FEE de 5 registrada en el remitente, o los mismos 5 como brecha entre las patas ($-1{,}000$ enviados, $+995$ recibidos, así que $X = 995$), permanece en la línea de $A$ como una pérdida de 5.
- **Parejas en el mismo bróker.** Dos patas en el mismo bróker, como una conversión de divisa dentro de una cuenta, no necesitan flujo: el valor nunca sale de la línea.
- **Parejas de ADJUSTMENT.** No son parejas internas: cada pata sigue su propia regla (véase la tabla anterior). El capital del receptor aumenta por el coste que añade su pata; la pata del remitente no tiene valor, así que su capital no se mueve y realiza su precio medio de compra como pérdida ([Ajustes salientes](#outgoing-adjustments)). Con la configuración del ejemplo de abajo y ambas patas el día 2, la pata receptora con un coste de 10: la línea de $A$ cae a $-100$ y la de $B$ marca $+20$, así que TotalPnL baja de $+20$ a $-80$. Para mover unidades entre dos brókeres sin esa pérdida, vincule los dos ajustes como una pareja TRANSFER.

### 🔍 Vistas filtradas

En una vista con solo algunos brókeres, una pata de TRANSFER cuya otra pata está fuera de $S$ —o falta, o nunca se vinculó— no puede formar una pareja interna. Es capital en especie a valor de mercado en su propia fecha: $+\mathrm{MV}$ para los valores recibidos, $-\mathrm{MV}$ para los valores enviados, con la participación de ese bróker —a coste para un título sin ningún precio, como arriba— y nada si el título no se puede valorar ese día. A diferencia de un flujo interno, mueve el CapitalBaseline de la vista, así que el TotalPnL, ROI, TWRR y MWRR de la vista lo tratan como capital, igual que un ADJUSTMENT en especie. Una pata de CASH\_TRANSFER o FX\_CONVERSION en la misma posición es efectivo externo por su importe, como un depósito o un retiro, y mueve los [pools de efectivo](#three-pool-cash-model) como lo haría ese depósito o retiro: el reparto del efectivo de la vista entre capital aportado y rendimientos generados, y la financiación de sus compras posteriores, lo siguen.

Cuando se elimina el bróker que mantiene la otra pata, la pata restante pasa a ser lo que deja una separación de la pareja, y las patas que las versiones anteriores dejaron atrás se convierten de la misma forma al inicio: los valores se convierten en un ADJUSTMENT —una pata recibida es capital en especie a coste cuando tiene un coste base (tabla anterior), ya no a valor de mercado; una pata enviada es un ADJUSTMENT saliente sin valor, que realiza el coste de sus unidades como pérdida ([Ajustes salientes](#outgoing-adjustments))— y el efectivo en un DEPOSIT o un WITHDRAWAL. Las filas convertidas siguen las mismas reglas en todas las vistas, incluida la completa.

Comparación de la vista propia de un bróker con la vista combinada:

- **El receptor por sí solo coincide con su línea combinada.** En la vista propia de $B$, los valores recibidos son capital a su valor de mercado en $t_{arr}$, que es el $X$ de la vista combinada. Esto se cumple con participaciones iguales y un precio que ambas vistas pueden ver: un precio que proviene solo de operaciones en $A$ no es visible en la vista propia de $B$.
- **El remitente por sí solo pierde las variaciones en tránsito.** En la vista propia de $A$, su capital cae el día de salida en $s_A \cdot V(t_{dep})$, mientras que en la vista combinada el valor permanece con $A$ hasta que llega.

Escribiendo $\mathrm{PnL}_A^{(S)}$ para la línea de $A$ en la vista del ámbito $S$, desde el día de salida en adelante:

$$
\mathrm{PnL}_A^{(A)}(t) = \mathrm{PnL}_A^{(A,B)}(t) - s_A\bigl[V(\min(t, t_{arr})) - V(t_{dep})\bigr]
$$

### 📦 Ejemplo — Valores en tránsito

Todos los importes en EUR, participaciones del 100 %. $A$ recibe un depósito de 100 y compra 10 unidades a 10 el día 0. El precio es 10, 11, 12, 13, 14, 15 en los días 0–5. $A$ envía las 10 unidades el día 1, y $B$ las recibe el día 3.

**Vista combinada** (ambos brókeres en $S$):

| Día | Precio | $\mathrm{NAV}_A$ | $C_A$ | $\mathrm{PnL}_A$ | $\mathrm{NAV}_B$ | $C_B$ | $\mathrm{PnL}_B$ | TotalPnL |
|-----|-------|------------------|-------|------------------|------------------|-------|------------------|----------|
| 0 | 10 | 100 | 100 | 0 | 0 | 0 | 0 | 0 |
| 1 | 11 | 110 (en tránsito) | 100 | +10 | 0 | 0 | 0 | +10 |
| 2 | 12 | 120 (en tránsito) | 100 | +20 | 0 | 0 | 0 | +20 |
| 3 | 13 | 0 | −30 | +30 | 130 | 130 | 0 | +30 |
| 4 | 14 | 0 | −30 | +30 | 140 | 130 | +10 | +40 |
| 5 | 15 | 0 | −30 | +30 | 150 | 130 | +20 | +50 |

El día 3 el flujo $X = 10 \times 13 = 130$ mueve capital de $A$ a $B$. $A$ conserva los +30 obtenidos mientras las unidades estaban en $A$ o viajando (10 → 13), y $B$ gana desde 13 en adelante. $C_A$ se vuelve negativo porque $A$ transmitió más valor (130) que el capital que recibió (100): la diferencia es su ganancia. TotalPnL es el mismo con o sin el flujo; sin él, el día 3 la línea de $A$ caería a $0 - 100 = -100$ y la de $B$ saltaría a $130 - 0 = +130$.

**Vistas de un solo bróker**:

| Día | $B$ solo: $C_B$ | $B$ solo: $\mathrm{PnL}_B$ | $A$ solo: $C_A$ | $A$ solo: $\mathrm{PnL}_A$ |
|-----|------------------|-----------------------------|------------------|-----------------------------|
| 0 | — | — | 100 | 0 |
| 1 | — | — | −10 | +10 |
| 2 | — | — | −10 | +10 |
| 3 | 130 | 0 | −10 | +10 |
| 4 | 130 | +10 | −10 | +10 |
| 5 | 130 | +20 | −10 | +10 |

La vista propia de $B$ comienza en su primera transacción y coincide con $B$ en la vista combinada. En la vista propia de $A$, las unidades salen el día 1 a $10 \times 11 = 110$, así que $C_A = 100 - 110 = -10$ y la línea se mantiene en +10: el movimiento de 11 a 13 mientras viajaban no está incluido, y $+30 - (130 - 110) = +10$. Contada como ganancia o pérdida en lugar de capital, la misma transferencia pondría a $A$ solo en −100 desde el día 1 y a $B$ solo en +130 el día 3.

### 💶 Ejemplo — Efectivo entre dos brókeres

$A$ recibe un depósito de 5.000. Más tarde, $A$ envía 1.000 a $B$, ambas patas el mismo día.

| Caso | $\mathrm{NAV}_A$ | $C_A$ | $\mathrm{PnL}_A$ | $\mathrm{NAV}_B$ | $C_B$ | $\mathrm{PnL}_B$ | TotalPnL |
|------|------------------|-------|------------------|------------------|-------|------------------|----------|
| Tras el depósito | 5.000 | 5.000 | 0 | 0 | 0 | 0 | 0 |
| Tras la transferencia | 4.000 | 4.000 | 0 | 1.000 | 1.000 | 0 | 0 |
| $B$ recibe 995 (comisión 5) | 4.000 | 4.005 | −5 | 995 | 995 | 0 | −5 |
| $B$ participado al 50 % | 4.000 | 4.000 | 0 | 500 | 1.000 | −500 | −500 |
| Sin el flujo | 4.000 | 5.000 | −1.000 | 1.000 | 0 | +1.000 | 0 |

La última fila es la misma transferencia leída sin el flujo interno: el movimiento parece una pérdida para $A$ y una ganancia para $B$. Con $B$ participado al 50 %, el escalón de −500 es el residual $(s_B - s_A)\,V = (0.5 - 1) \times 1{,}000$, y TotalPnL también lo muestra.

---

## 📊 Modelo de efectivo de tres pools {: #three-pool-cash-model }

El gráfico de crecimiento descompone el efectivo actual en dos agregados visibles más un rastreador global oculto:

$$
\mathrm{Cash}(t) \approx \sum_b K_b(t) + \sum_b R_b(t)
$$

| Pool | Ámbito | Significado |
|------|-------|---------|
| $K_b$ | Por bróker | Capital externo que aún está en el bróker $b$ |
| $R_b$ | Por bróker | Rendimientos generados que aún están en el bróker $b$ |
| $W$ | Global | Rendimientos que salieron del sistema (restaurables al volver a depositar) |

!!! info "Propiedades clave"

    - $\mathrm{CapitalBaseline}$ = suma histórica de flujos de efectivo y capital en especie. $\sum K_b$ = cuánto del efectivo actual es capital externo. Difieren tras BUY/SELL.
    - Una BUY en el bróker $b_1$ solo consume $R_{b_1}$, nunca $R_{b_2}$.
    - Las transferencias de fondos entre brókeres y las conversiones de divisa con ambas patas en el ámbito mueven $R$ y $K$ del origen al destino sin tocar $W$: la salida deja primero los rendimientos, y la llegada devuelve lo que tomó del capital y de los rendimientos; cualquier brecha entre las dos patas —otra divisa, el tipo de otro día, otra participación— es un resultado.
    - Una pata de transferencia de fondos o de conversión cuya otra pata está fuera del ámbito, o que ha perdido su pareja, mueve los pools como un DEPOSIT o un WITHDRAWAL por su importe: al llegar, primero restaura los rendimientos retirados de $W$ en $R_b$ y el resto es $K_b$; al salir, toma primero $K_b$, luego $R_b$, que va a $W$ ([ejemplo E](#e-cash-from-outside-the-view)).
    - Un resultado de cambio sobre el efectivo que un bróker mantiene en otra divisa va a $R_b$; una pérdida mayor que $R_b$ sale de $K_b$, como lo hace una FEE. $\mathrm{CapitalBaseline}$ no se mueve ([Motor de cartera — §6](index.md#exchange-result-on-foreign-cash)).

🔗 Reglas completas de actualización por bróker: **[Motor de cartera — §6 Modelo de tres pools](index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w)**

---

## 📝 Ejemplos resueltos

### 🧾 A — Depósito → Compra → Venta con ganancia

| Paso | Tx | $K$ | $R$ | Efectivo |
|------|----|-----|-----|------|
| 1 | DEPOSIT 1.000 € | 1.000 | 0 | 1.000 |
| 2 | BUY 1.000 € | 0 | 0 | 0 |
| 3 | SELL P=1.200 €, C=1.000 € | 1.000 | 200 | 1.200 |

TotalPnL = 1.200 − 1.000 = **+200 €** ✓

### 💸 B — Dividendo y luego retiro

| Paso | Tx | $K$ | $R$ | $W$ | Efectivo |
|------|----|-----|-----|-----|------|
| 1 | DEPOSIT 1.000 € | 1.000 | 0 | 0 | 1.000 |
| 2 | DIVIDEND 50 € | 1.000 | 50 | 0 | 1.050 |
| 3 | WITHDRAWAL 100 € (K primero) | 900 | 50 | 0 | 950 |
| 4 | WITHDRAWAL 950 € (K=900→0, R=50→0, W+=50) | 0 | 0 | 50 | 0 |
| 5 | RE-DEPOSIT 30 € (restaura min(30,W=50)=30) | 0 | 30 | 20 | 30 |

Tras el paso 5: Efectivo=30, K=0, R=30 ✓ (rendimientos restaurados desde W)

### 🧪 C — Regresión de venta completa

| Paso | Tx | $K$ | $R$ | Efectivo |
|------|----|-----|-----|------|
| 1 | DEPOSIT 1.000 €, BUY 1@1.000 € | 0 | 0 | 0 |
| 2 | SELL 1@1.005 € (C=1000, G=5) | 1.000 | 5 | 1.005 |

El capital vuelve correctamente a $K$; solo 5 € de ganancia a $R$. **No** los 1.005 € completos a $R$.

### 💱 D — Dólares mantenidos mientras se mueve el tipo

Un bróker, divisa de informe EUR, tipos en EUR por USD; $\varepsilon$ es el [resultado de cambio sobre el efectivo](index.md#exchange-result-on-foreign-cash).

| Paso | Evento | $\varepsilon$ | $K$ | $R$ | Efectivo | TotalPnL |
|------|-------|---------------|-----|-----|------|----------|
| 1 | DEPOSIT 1.000 USD a 0,90 | — | 900 | 0 | 900 | 0 |
| 2 | El tipo sube a 0,95 | +50 | 900 | 50 | 950 | +50 |
| 3 | El tipo cae a 0,85 ($R$ = 50 − 100, $K$ absorbe −50) | −100 | 850 | 0 | 850 | −50 |
| 4 | BUY por 1.000 USD a 0,85 (850 €) | — | 0 | 0 | 0 | MV − 900 |

El CapitalBaseline se mantiene en 900 € durante todo el proceso: los resultados de cambio son ganancias y pérdidas, no capital. Tras el paso 4, TotalPnL es el valor de mercado MV del título menos los 900 € depositados —−50 el día de la compra si MV es igual a los 850 € pagados.

### 🔀 E — Efectivo desde fuera de la vista {: #e-cash-from-outside-the-view }

La vista del bróker $B$ por sí solo; el bróker $A$ está fuera de ella, así que cada transferencia de fondos entre ellos es un flujo externo de la vista, como en Vistas filtradas arriba.

| Paso | Tx en $B$ | $K$ | $R$ | $W$ | Efectivo |
|------|-----------|-----|-----|-----|------|
| 1 | DEPOSIT 100 €, INTEREST 100 € | 100 | 100 | 0 | 200 |
| 2 | CASH\_TRANSFER 150 € a $A$, como un WITHDRAWAL (K=100→0, R=100→50, W+=50) | 0 | 50 | 50 | 50 |
| 3 | CASH\_TRANSFER 100 € desde $A$, como un DEPOSIT (restaura min(100,W=50)=50, los otros 50 a K) | 50 | 100 | 0 | 150 |
| 4 | BUY 100 € (R primero) | 50 | 0 | 0 | 50 |

La compra del paso 4 son todos rendimientos reinvertidos, nada de capital nuevo. Lo mismo vale para una pata de transferencia que ha perdido su pareja, en todas las vistas. En la vista de $A$ y $B$ juntos, ambas transferencias son parejas internas y mueven los pools de un bróker al otro, sin tocar $W$.

---

## ⚙️ Implementación

El modelo de 3 pools se ejecuta en un **único bucle por transacción** (dirigido por eventos, no por delta diario):

1. Tome el paso de la transacción en el pool de PMC de su posición, calculado antes de la repetición histórica —para una SELL, el coste que elimina ($C$ = PMC previo a la venta × cantidad vendida, a tipos históricos)
2. Actualice K/R/W según las reglas del tipo de transacción, con ese $C$ para una SELL

Cada día que cambia el tipo de cambio de una divisa extranjera mantenida como efectivo, el resultado de cambio de cada bróker sobre ese efectivo también se contabiliza en sus pools, después de los movimientos de efectivo del día y antes de las transacciones del día ([§6](index.md#exchange-result-on-foreign-cash)).

La serie de entrada de ROI/TWRR/MWRR se deriva de los cambios día a día en `cumulative_external_cash_flow`, la base de capital. No se deriva del campo `external_cash_flow`, que solo contiene efectivo.

🔗 Consulte **[Motor de cartera — §6](index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w)** para todas las reglas formales.

---

## 🔗 Relacionados

- 💼 [NAV](nav.md) — el otro término del P&L total
- 📊 [P&L período](period-pnl.md) — versión por ventana
- ⚙️ [Motor de cartera](index.md) — modelo matemático completo
- 📈 [Resumen de métricas de rendimiento](../index.md) — todas las métricas de rendimiento de un vistazo
