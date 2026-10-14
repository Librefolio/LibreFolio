# 💸 Capital depositado, P&L total y fondos de efectivo

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

- filas AJUSTE valoradas que llevan `cost_basis_override` (no vinculadas a un desdoblamiento), **a coste**: el coste que una fila entrante añade a la posición, o el coste medio que una fila saliente elimina;
- patas de TRANSFERENCIA cuya otra pata no está en el ámbito —está en un bróker fuera de la vista, falta o nunca se vinculó— **a valor de mercado** en su propia fecha: $+$ para valores recibidos, $-$ para valores enviados, nada si el valor no puede valorarse ese día.

Estas filas mueven valor sin efectivo: son capital, no ganancia ni pérdida.

---

## 🎯 Qué cuenta

| Transacción | Efecto sobre la base de capital |
|------------|-----------------|
| DEPÓSITO / RETIRO (no vinculados) | ✅ Sí |
| TRANSFERENCIA DE FONDOS / CONVERSIÓN FX cuya otra pata está fuera de la vista, falta o nunca se vinculó (huérfana) | ✅ Sí, por su importe, como un depósito o un retiro |
| TRANSFERENCIA DE FONDOS / CONVERSIÓN FX / TRANSFERENCIA con ambas patas en la vista (par interno) | ❌ No. Por bróker, un par entre dos brókeres mueve capital del emisor al receptor el día de llegada, sumando cero ([Transferencias internas](#internal-transfers-broker-lines)) |
| TRANSFERENCIA de valores cuya otra pata está fuera de la vista, falta o nunca se vinculó (huérfana) | ✅ Sí, capital en especie a valor de mercado en su fecha |
| AJUSTE con `cost_basis_override`, no vinculado a desdoblamiento | ✅ Sí, capital en especie a coste |
| AJUSTE vinculado a desdoblamiento | ❌ No, solo reescalado de cantidad |
| COMPRA, VENTA, DIVIDENDO, INTERÉS, COMISIÓN, IMPUESTO | ❌ No |
| Movimiento del tipo de cambio sobre el efectivo mantenido en otra divisa (sin transacción) | ❌ No: un resultado, parte del P&L total; los flujos de capital (depósitos, retiros, patas de efectivo huérfanas) entraron en la base al tipo de cambio de sus propias fechas |

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

La línea de un bróker es, por tanto, el P&L obtenido mientras el valor estuvo en ese bróker, o viajando desde él. No es la ganancia no realizada de las posiciones que mantiene el bróker.

### 📐 El flujo interno

Un **par interno** es una TRANSFERENCIA DE FONDOS, una CONVERSIÓN FX o una TRANSFERENCIA vinculada cuyas dos patas están ambas en $S$, en dos brókeres diferentes: el emisor $A$ (la pata que sale) y el receptor $B$ (la pata que entra). Produce un flujo, el **día de llegada** $t_{arr}$, la fecha de la pata posterior:

$$
\mathrm{Internal}_A(t_{arr}) = -X,
\qquad
\mathrm{Internal}_B(t_{arr}) = +X,
\qquad
X = s_A \cdot V(t_{arr})
$$

$s_A$ es la [cuota de propiedad](../../../../user/brokers/sharing.md) del emisor y $V(t_{arr})$ el valor total que la llegada aporta a $B$ ese día, valorado exactamente como lo valora el NAV:

| Par | $V(t_{arr})$ |
|------|--------------|
| TRANSFERENCIA DE FONDOS | El importe recibido, convertido al tipo $\mathrm{fx}(c, C^*, t_{arr})$ |
| CONVERSIÓN FX entre brókeres | La pata recibida, convertida de la misma forma: $-1.000$ USD en $A$ → $+900$ EUR en $B$ da $V = 900$ EUR, y el coste de conversión permanece en la línea de $A$ |
| TRANSFERENCIA de valores | $\mathrm{MV}$ de la cantidad recibida al [precio de valoración](index.md#2-valuation-price) de $t_{arr}$, el último precio conocido arrastrado si no hay ninguno ese día |

Con cuotas de propiedad iguales, $X$ es exactamente lo que la llegada añade a $\mathrm{NAV}_B$, así que ninguna línea salta. El $\mathrm{CapitalBaseline}$ del ámbito no se modifica, porque un movimiento interno no es capital externo: NAV, CapitalBaseline, P&L total y sus velas, ROI, TWRR, MWRR y efectivo son los mismos que sin el flujo. Solo cambia el reparto de la base entre los brókeres.

### ✈️ Valor en tránsito

Cuando las patas caen en días diferentes, el valor viaja desde el día de salida $t_{dep}$ hasta el día anterior a $t_{arr}$. Mientras tanto, forma parte de $\mathrm{InTransit}_A$, a la cuota $s_A$ del emisor, valorado cada día: el efectivo al tipo de cambio de ese día, los valores al precio de valoración de ese día (al coste registrado en la transferencia si el valor no tiene ningún precio). No ocurre ningún flujo mientras el valor viaja, así que sus movimientos de precio y tipo de cambio permanecen en la línea de $A$, incluido el propio movimiento del día de llegada; la línea de $B$ comienza desde el valor recibido.

Por ejemplo, $A$ recibe un depósito de 1.000 USD el día 0 a 0,90 EUR por USD ($C_A = 900$) y envía los dólares el día 1; $B$ los recibe el día 4. Con el tipo a 0,90, 0,91, 0,92, 0,93 en los días 1–4, la línea de $A$ marca 0, +10, +20, +30 y la de $B$ se mantiene en 0. El día 4, $X = 930$ y $C_A = 900 - 930 = -30$. Una vez llegados, los dólares son efectivo de $B$, revalorizado cada día, así que desde el día 5 la línea de $B$ se mueve con el tipo: a 0,94, marca +10.

### 🧩 Casos especiales

- **Cuotas de propiedad diferentes.** $X$ usa $s_A$, como el valor en tránsito, mientras que la llegada añade $s_B \cdot V(t_{arr})$ a $\mathrm{NAV}_B$. La línea de $B$ conserva un escalón residual de $(s_B - s_A)\,V(t_{arr})$ el día de llegada, y el P&L total muestra el mismo escalón, con o sin el flujo.
- **Valor desconocido el día de llegada.** Si $V(t_{arr})$ no puede calcularse —el instrumento no tiene observación en o antes de $t_{arr}$ ($\operatorname{mark} = \varnothing$), o falta un tipo de cambio—, entonces $X = 0$, que es lo que la llegada añade a $\mathrm{NAV}_B$. No se adivina nada: el salto permanece, y el valor de un instrumento aparece en la línea del bróker que lo mantiene desde su primer precio.
- **Comisiones.** No forman parte de $X$. Una fila COMISIÓN de 5 registrada en el emisor, o los mismos 5 como diferencia entre las patas ($-1.000$ enviados, $+995$ recibidos, por lo que $X = 995$), permanece en la línea de $A$ como una pérdida de 5.
- **Pares en el mismo bróker.** Dos patas en el mismo bróker, como una conversión de divisa dentro de una cuenta, no necesitan flujo: el valor nunca sale de la línea.
- **Pares de AJUSTE.** No son pares internos: cada pata permanece como capital en especie a coste (véase la tabla anterior). El capital del emisor disminuye en el coste medio eliminado y el del receptor aumenta en el coste añadido, por lo que la línea receptora asume la ganancia acumulada en el emisor. Con la configuración del ejemplo de abajo y ambas patas el día 2 a un coste de 10, las líneas marcan $A = 0$, $B = +20$; un par de TRANSFERENCIA da $A = +20$, $B = 0$.

### 🔍 Vistas filtradas

En una vista con solo algunos brókeres, una pata de TRANSFERENCIA cuya otra pata está fuera de $S$ —o falta, o nunca se vinculó— no puede formar un par interno. Es capital en especie a valor de mercado en su propia fecha: $+\mathrm{MV}$ para valores recibidos, $-\mathrm{MV}$ para valores enviados, a la cuota de ese bróker, y nada si el instrumento no puede valorarse ese día. A diferencia de un flujo interno, mueve el CapitalBaseline de la vista, por lo que el P&L total, ROI, TWRR y MWRR de la vista lo tratan como capital, igual que un AJUSTE en especie. Una pata de TRANSFERENCIA DE FONDOS o CONVERSIÓN FX en la misma posición es efectivo externo por su importe, como un depósito o un retiro.

Una pata pierde su vínculo cuando se elimina el bróker que mantiene la otra pata. Tal huérfana sigue las mismas reglas en todas las vistas, incluida la completa.

Comparación de la vista propia de un bróker con la vista combinada:

- **El receptor por sí solo coincide con su línea combinada.** En la vista propia de $B$, los valores recibidos son capital a su valor de mercado en $t_{arr}$, que es el $X$ de la vista combinada. Esto se cumple con cuotas de propiedad iguales y un precio que ambas vistas pueden ver: un precio que proviene solo de operaciones en $A$ no es visible en la vista propia de $B$.
- **El emisor por sí solo pierde los movimientos en tránsito.** En la vista propia de $A$, su capital cae el día de salida en $s_A \cdot V(t_{dep})$, mientras que en la vista combinada el valor permanece con $A$ hasta que llega.

Escribiendo $\mathrm{PnL}_A^{(S)}$ para la línea de $A$ en la vista del ámbito $S$, desde el día de salida en adelante:

$$
\mathrm{PnL}_A^{(A)}(t) = \mathrm{PnL}_A^{(A,B)}(t) - s_A\bigl[V(\min(t, t_{arr})) - V(t_{dep})\bigr]
$$

### 📦 Ejemplo — Valores en tránsito

Todos los importes en EUR, cuotas de propiedad 100%. $A$ recibe un depósito de 100 y compra 10 unidades a 10 el día 0. El precio es 10, 11, 12, 13, 14, 15 en los días 0–5. $A$ envía las 10 unidades el día 1, y $B$ las recibe el día 3.

**Vista combinada** (ambos brókeres en $S$):

| Día | Precio | $\mathrm{NAV}_A$ | $C_A$ | $\mathrm{PnL}_A$ | $\mathrm{NAV}_B$ | $C_B$ | $\mathrm{PnL}_B$ | P&L total |
|-----|-------|------------------|-------|------------------|------------------|-------|------------------|----------|
| 0 | 10 | 100 | 100 | 0 | 0 | 0 | 0 | 0 |
| 1 | 11 | 110 (en tránsito) | 100 | +10 | 0 | 0 | 0 | +10 |
| 2 | 12 | 120 (en tránsito) | 100 | +20 | 0 | 0 | 0 | +20 |
| 3 | 13 | 0 | −30 | +30 | 130 | 130 | 0 | +30 |
| 4 | 14 | 0 | −30 | +30 | 140 | 130 | +10 | +40 |
| 5 | 15 | 0 | −30 | +30 | 150 | 130 | +20 | +50 |

El día 3, el flujo $X = 10 \times 13 = 130$ mueve capital de $A$ a $B$. $A$ conserva los +30 obtenidos mientras las unidades estuvieron en $A$ o viajando (10 → 13), y $B$ gana desde 13 en adelante. $C_A$ se vuelve negativo porque $A$ transmitió más valor (130) que el capital que recibió (100): la diferencia es su ganancia. El P&L total es el mismo con o sin el flujo; sin él, el día 3 la línea de $A$ caería a $0 - 100 = -100$ y la de $B$ saltaría a $130 - 0 = +130$.

**Vistas de un solo bróker**:

| Día | $B$ por sí solo: $C_B$ | $B$ por sí solo: $\mathrm{PnL}_B$ | $A$ por sí solo: $C_A$ | $A$ por sí solo: $\mathrm{PnL}_A$ |
|-----|------------------|-----------------------------|------------------|-----------------------------|
| 0 | — | — | 100 | 0 |
| 1 | — | — | −10 | +10 |
| 2 | — | — | −10 | +10 |
| 3 | 130 | 0 | −10 | +10 |
| 4 | 130 | +10 | −10 | +10 |
| 5 | 130 | +20 | −10 | +10 |

La vista propia de $B$ comienza en su primera transacción y coincide con $B$ en la vista combinada. En la vista propia de $A$, las unidades salen el día 1 a $10 \times 11 = 110$, así que $C_A = 100 - 110 = -10$ y la línea se mantiene en +10: el movimiento de 11 a 13 durante el tránsito no está en ella, y $+30 - (130 - 110) = +10$. Contabilizada como ganancia o pérdida en lugar de capital, la misma transferencia situaría a $A$ por sí solo en −100 desde el día 1 y a $B$ por sí solo en +130 el día 3.

### 💶 Ejemplo — Efectivo entre dos brókeres

$A$ recibe un depósito de 5.000. Después, $A$ envía 1.000 a $B$, ambas patas el mismo día.

| Caso | $\mathrm{NAV}_A$ | $C_A$ | $\mathrm{PnL}_A$ | $\mathrm{NAV}_B$ | $C_B$ | $\mathrm{PnL}_B$ | P&L total |
|------|------------------|-------|------------------|------------------|-------|------------------|----------|
| Después del depósito | 5.000 | 5.000 | 0 | 0 | 0 | 0 | 0 |
| Después de la transferencia | 4.000 | 4.000 | 0 | 1.000 | 1.000 | 0 | 0 |
| $B$ recibe 995 (comisión 5) | 4.000 | 4.005 | −5 | 995 | 995 | 0 | −5 |
| $B$ con una cuota de propiedad del 50% | 4.000 | 4.000 | 0 | 500 | 1.000 | −500 | −500 |
| Sin el flujo | 4.000 | 5.000 | −1.000 | 1.000 | 0 | +1.000 | 0 |

La última fila es la misma transferencia leída sin el flujo interno: el movimiento parece una pérdida para $A$ y una ganancia para $B$. Con $B$ con una cuota de propiedad del 50%, el escalón de −500 es el residual $(s_B - s_A)\,V = (0{,}5 - 1) \times 1.000$, y el P&L total también lo muestra.

---

## 📊 Modelo de efectivo de tres fondos {: #three-pool-cash-model }

El gráfico de crecimiento descompone el efectivo actual en dos agregados visibles más un rastreador global oculto:

$$
\mathrm{Cash}(t) \approx \sum_b K_b(t) + \sum_b R_b(t)
$$

| Fondo | Ámbito | Significado |
|------|-------|---------|
| $K_b$ | Por bróker | Capital externo que aún está en el bróker $b$ |
| $R_b$ | Por bróker | Rendimientos generados que aún están en el bróker $b$ |
| $W$ | Global | Rendimientos que salieron del sistema (restaurables al volver a depositar) |

!!! info "Propiedades clave"

    - $\mathrm{CapitalBaseline}$ = suma histórica de flujos de efectivo y capital en especie. $\sum K_b$ = cuánto del efectivo actual es capital externo. Divergen después de COMPRA/VENTA.
    - Una COMPRA en el bróker $b_1$ solo consume $R_{b_1}$, nunca $R_{b_2}$.
    - Las transferencias de fondos entre brókeres mueven $R$ y $K$ desde el origen al destino sin tocar $W$.
    - Un resultado de cambio sobre el efectivo que un bróker mantiene en otra divisa va a $R_b$; una pérdida mayor que $R_b$ sale de $K_b$, como hace una COMISIÓN. $\mathrm{CapitalBaseline}$ no se mueve ([Motor de cartera — §6](index.md#exchange-result-on-foreign-cash)).

🔗 Reglas completas de actualización por bróker: **[Motor de cartera — §6 Modelo de tres fondos](index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w)**

---

## 📝 Ejemplos prácticos

### 🧾 A — Depósito → Compra → Venta con ganancia

| Paso | Tx | $K$ | $R$ | Efectivo |
|------|----|-----|-----|------|
| 1 | DEPÓSITO €1.000 | 1.000 | 0 | 1.000 |
| 2 | COMPRA €1.000 | 0 | 0 | 0 |
| 3 | VENTA P=€1.200, C=€1.000 | 1.000 | 200 | 1.200 |

P&L total = 1.200 − 1.000 = **+€200** ✓

### 💸 B — Dividendo y luego retiro

| Paso | Tx | $K$ | $R$ | $W$ | Efectivo |
|------|----|-----|-----|-----|------|
| 1 | DEPÓSITO €1.000 | 1.000 | 0 | 0 | 1.000 |
| 2 | DIVIDENDO €50 | 1.000 | 50 | 0 | 1.050 |
| 3 | RETIRO €100 (K primero) | 900 | 50 | 0 | 950 |
| 4 | RETIRO €950 (K=900→0, R=50→0, W+=50) | 0 | 0 | 50 | 0 |
| 5 | RE-DEPÓSITO €30 (restaurar min(30,W=50)=30) | 0 | 30 | 20 | 30 |

Después del paso 5: Efectivo=30, K=0, R=30 ✓ (rendimientos restaurados desde W)

### 🧪 C — Regresión de venta total

| Paso | Tx | $K$ | $R$ | Efectivo |
|------|----|-----|-----|------|
| 1 | DEPÓSITO €1.000, COMPRA 1@€1.000 | 0 | 0 | 0 |
| 2 | VENTA 1@€1.005 (C=1.000, G=5) | 1.000 | 5 | 1.005 |

El capital vuelve correctamente a $K$; solo €5 de ganancia a $R$. **No** los €1.005 completos a $R$.

### 💱 D — Dólares mantenidos mientras el tipo se mueve

Un solo bróker, divisa del informe EUR, tipos de cambio en EUR por USD; $\varepsilon$ es el [resultado de cambio sobre el efectivo](index.md#exchange-result-on-foreign-cash).

| Paso | Evento | $\varepsilon$ | $K$ | $R$ | Efectivo | P&L total |
|------|-------|---------------|-----|-----|------|----------|
| 1 | DEPÓSITO 1.000 USD a 0,90 | — | 900 | 0 | 900 | 0 |
| 2 | El tipo sube a 0,95 | +50 | 900 | 50 | 950 | +50 |
| 3 | El tipo baja a 0,85 ($R$ = 50 − 100, $K$ absorbe −50) | −100 | 850 | 0 | 850 | −50 |
| 4 | COMPRA por 1.000 USD a 0,85 (€850) | — | 0 | 0 | 0 | MV − 900 |

La CapitalBaseline se mantiene en €900 durante todo el ejemplo: los resultados de cambio son ganancias y pérdidas, no capital. Tras el paso 4, el P&L total es el valor de mercado MV del título menos los €900 depositados — −50 el día de la compra si MV es igual a los €850 pagados.

---

## ⚙️ Implementación

El modelo de tres fondos se ejecuta en un **único bucle por transacción** (dirigido por eventos, no por delta diario):

1. Toma la parte de la transacción correspondiente al fondo de coste medio de su posición, calculado antes de la reproducción —para una VENTA, el coste que elimina ($C$ = PMC previo a la venta × cantidad vendida, a tipos históricos)
2. Actualiza K/R/W según las reglas del tipo de transacción, con ese $C$ para una VENTA

Cada día en que cambia el tipo de cambio de una divisa extranjera mantenida como efectivo, el resultado de cambio de cada bróker sobre ese efectivo también se registra en sus fondos, después de los movimientos de efectivo del día y antes de las transacciones del día ([§6](index.md#exchange-result-on-foreign-cash)).

La serie de entrada de ROI/TWRR/MWRR se deriva de los cambios día a día en `cumulative_external_cash_flow`, la base de capital. No se deriva del campo `external_cash_flow` que solo contiene efectivo.

🔗 Véase **[Motor de cartera — §6](index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w)** para todas las reglas formales.

---

## 🔗 Relacionado

- 💼 [NAV](nav.md) — el otro término del P&L total
- 📊 [P&L período](period-pnl.md) — versión por ventana móvil
- ⚙️ [Motor de cartera](index.md) — modelo matemático completo
- 📈 [Resumen de métricas de rendimiento](../index.md) — todas las métricas de rendimiento de un vistazo
