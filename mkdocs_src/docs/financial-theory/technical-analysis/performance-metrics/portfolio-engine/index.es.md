# ⚙️ Motor de cartera — Modelo matemático

## 💡 Resumen

Esta página define formalmente el modelo matemático que subyace al motor de cálculo de carteras de LibreFolio. Todas las demás páginas de métricas ([NAV](nav.md), [Valor contable](book-value.md), [P&L período](period-pnl.md), [Rendimiento sobre coste](yield-on-cost.md), [PMC](../weighted-average-cost.md), [Capital depositado](deposited-capital.md)) remiten a esta página para sus reglas precisas de cálculo.

---

## 📐 1. Notación y conjuntos

| Símbolo | Significado |
|--------|---------|
| $V(u)$ | Todos los brókers visibles para el usuario $u$ |
| $S \subseteq V(u)$ | Ámbito de brókers seleccionado (filtrado) |
| $A$ | Conjunto de activos con posiciones |
| $C^*$ | Divisa objetivo |
| $[t_0, t_1]$ | Marco de evaluación solicitado |
| $q(a,b,t)$ | Cantidad del activo $a$ en el bróker $b$ en la fecha $t$ |
| $p(a,t)$ | Precio de valoración del activo $a$ en la fecha $t$ |
| $\mathrm{fx}(c_1, c_2, t)$ | Tipo de cambio de la divisa $c_1$ a $c_2$ en la fecha $t$ |

---

## 📐 2. Precio de valoración {: #2-valuation-price }

$$
\operatorname{mark}(a,t)=
\begin{cases}
\text{MARKET}(a,t) & \text{cotización del sistema de activos del mismo día}\\
\operatorname{avg}(\text{TRADE}(a,t)) & \text{observaciones de BUY/SELL del mismo día, o estimaciones de coste de transferencia}\\
\text{última observación anterior a }t & \text{arrastrado (LOCF)}\\
\varnothing & \text{ninguna observación en o antes de }t
\end{cases}
$$

- El resolutor unificado es el único cerebro de valoración: `MARKET → TRADE_AVG → CARRIED → MISSING`.
- Las cotizaciones de mercado y las operaciones de COMPRA/VENTA son observaciones. Un AJUSTE nunca lo es, entrante o saliente, con o sin coste base: su coste base es un coste, no lo que el activo valía ese día.
- El coste de una TRANSFERENCIA entrante (su coste base por unidad, en la divisa del coste base) es una observación de operación, estimada, solo mientras el activo no tenga, en ese día o antes, ninguna cotización de mercado ni ninguna otra operación —ni COMPRA ni VENTA, ni AJUSTE, ni transferencia saliente; otras transferencias entrantes no lo impiden—. Se arrastra hasta que una cotización u operación real lo reemplace, y nunca se impone a una observación real: un valor cotizado movido entre brókers conserva su cotización arrastrada ([Coste de transferencia como estimación](price-resolution.md#transfer-cost-estimate)).
- `CARRIED` es arrastre de la última observación (last-observation-carried-forward). Lleva metadatos de obsolescencia `days_back`.
- `estimated=True` significa de origen TRADE. Una cotización MARKET arrastrada que está obsoleta sigue obsoleta, no es estimada.
- Los precios de valoración permanecen en su divisa nativa; cada consumidor convierte a $C^*$ en la fecha de valoración $t$.
- El FX del coste base permanece fijado a la fecha de la transacción.
- El efectivo permanece en la divisa en la que se registró, bróker por bróker, y se valora al tipo de cambio de $t$ (§5); cada movimiento de efectivo se sigue registrando, y cada flujo de efectivo externo entra en el capital, al tipo de cambio de su propia fecha.
- El PMC **nunca** se usa como precio de valoración. Una posición cuyo activo no tiene ningún precio de valoración ($\varnothing$) se cuenta en su lugar a su coste base, como una estimación declarada, no como un precio (§3).

Véase [Resolución de precios](price-resolution.md) para el contrato del resolutor y la semántica de calidad de datos.

---

## 📐 3. Estado de la posición {: #3-position-state }

Una posición $(a,b)$ se considera **mantenida** en $t$ cuando su cantidad supera el umbral de residuo $\varepsilon = 10^{-5}$ unidades: $q(a,b,t) > \varepsilon$. Para cada posición mantenida:

$$
\mathrm{MV}(a,b,t) =
\begin{cases}
\dfrac{q(a,b,t)}{qbq(a)}\cdot \operatorname{mark}(a,t)\cdot \mathrm{fx}\bigl(\mathrm{ccy}_{mark}, C^*, t\bigr) & \operatorname{mark}(a,t) \neq \varnothing\\
\mathrm{CB}(a,b,t) & \operatorname{mark}(a,t) = \varnothing \text{ y el coste de } (a,b) \text{ es completo}
\end{cases}
$$

$$
\mathrm{CB}(a,b,t) = q(a,b,t) \cdot w(a,b,t)
$$

$$
\mathrm{UGL}(a,b,t) = \mathrm{MV}(a,b,t) - \mathrm{CB}(a,b,t)
$$

Donde $w(a,b,t)$ es el [Precio medio de compra (PMC)](../weighted-average-cost.md) de la posición $(a,b)$ en la fecha $t$, mantenido en $C^*$ a tipos históricos (§4): el coste base no toma ningún tipo de cambio en $t$, así que para un activo extranjero el efecto del tipo de cambio forma parte de $\mathrm{UGL}$.

El segundo caso cubre un activo sin ninguna observación todavía —sin cotización, sin COMPRA o VENTA y sin estimación de coste de transferencia en $t$ o antes, como una posición recibida mediante ajustes o mediante transferencias sin coste base—. La posición se valora a su coste base, fuente de valoración `ESTIMATED_AT_COST`: una estimación declarada, no un precio. No informa de ningún precio unitario, no se mueve con los tipos de cambio y su $\mathrm{UGL}$ es cero, sin efecto de precio ni efecto de tipo de cambio. La elección se hace día a día, sin mirar hacia delante: desde la primera observación en adelante, gana el precio de valoración, incluso uno antiguo arrastrado. Una posición cuyo coste es incompleto (§4) no tiene valor de mercado en tal día (`MISSING`) y queda fuera de $\mathrm{MV}(t)$. Por tanto, las fuentes de valoración se ordenan `MARKET_PRICE` > `LAST_TRADE_PRICE` > `ESTIMATED_AT_COST` > `MISSING` ([Resolución de precios](price-resolution.md)).

Una cantidad de $\varepsilon$ unidades o menos —el residuo que puede dejar una venta de casi todas las unidades— no se mantiene: no tiene estado de posición, por lo que no tiene valor de mercado, ni coste base, ni porción de asignación, ni instantánea, y un residuo sin precio de valoración no hace que el día sea incompleto. El mismo umbral decide qué posiciones mantienen las filas de rendimiento (§7), así que la cartera y sus filas cuentan las mismas posiciones; a dónde va el coste del residuo se explica en la §7.

---

## 📐 4. Actualización iterativa del PMC

Se mantiene por posición $(a,b)$ con un estado de pool $(\hat{q}, \hat{c})$, con el coste $\hat{c}$ en $C^*$:

**Adquisición** (cantidad $> 0$, importe $P$ pagado en la divisa $c$ en la fecha $d$):

$$
\hat{q}_{\text{new}} = \hat{q} + q_{\text{tx}}, \quad
\hat{c}_{\text{new}} = \hat{c} + P \cdot \mathrm{fx}(c, C^*, d), \quad
w = \frac{\hat{c}_{\text{new}}}{\hat{q}_{\text{new}}}
$$

$P$ es el efectivo pagado por una COMPRA, o el coste base por unidad sobrescrito multiplicado por $q_{\text{tx}}$ para una TRANSFERENCIA o un AJUSTE; $\mathrm{fx}(C^*, C^*, d) = 1$. Cuando no existe ningún tipo de cambio en $d$ o antes, o la adquisición no tiene coste base, la cantidad entra y el coste no: el coste de la posición se marca como incompleto en lugar de contar cero.

**Reducción** (cantidad $< 0$):

$$
w_{\text{pre}} = \frac{\hat{c}}{\hat{q}}, \quad
\hat{q}_{\text{new}} = \hat{q} - |q_{\text{tx}}|, \quad
\hat{c}_{\text{new}} = \hat{q}_{\text{new}} \cdot w_{\text{pre}}
$$

**Desdoblamiento** (vinculado a un evento de desdoblamiento): $\hat{q}$ cambia, $\hat{c}$ no.

!!! info "Orden"

    Dentro de la misma fecha: las adiciones se procesan antes que las reducciones. Garantiza que una VENTA lea el PMC correcto incluyendo las compras del mismo día.

---

## 📐 5. Agregación de la cartera {: #5-portfolio-aggregation }

$$
\mathrm{MV}(t) = \sum_{(a,b) \in S} \mathrm{MV}(a,b,t)
$$

$$
\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)
$$

$$
\mathrm{Book}(t) = \mathrm{OCB}(t) + \mathrm{Cash}(t) + \mathrm{InTransitBook}(t)
$$

$$
\mathrm{UGL}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)
$$

$\mathrm{MV}(t)$ y $\mathrm{OCB}(t)$ recorren las posiciones mantenidas en $t$ (§3): el residuo, en el umbral o por debajo de él, no está en ninguno, así que no está ni en el NAV ni en el valor contable.

$\mathrm{Cash}(t)$ es el efectivo de cada bróker, mantenido en las divisas en que se registró y valorado al tipo de cambio de $t$:

$$
\mathrm{Cash}(t) = \sum_{b \in S} \sum_{c} N_{b,c}(t) \cdot \mathrm{fx}(c, C^*, t)
$$

donde $N_{b,c}(t)$ es el saldo del bróker $b$ en la divisa $c$ después de sus movimientos fechados en $t$ o antes, escalado por la [participación de propiedad](../../../../user/brokers/sharing.md) del bróker, y $\mathrm{fx}(c, C^*, t)$ es el último tipo de cambio en $t$ o antes ($1$ para $c = C^*$). El mismo término está en el NAV y en el valor contable, así que el efecto del tipo de cambio sobre el efectivo se cancela en UGL: se registra como un resultado de cambio (§6) y pertenece al P&L total.

### 🔀 Dos cifras no realizadas {: #two-unrealized-figures }

$\mathrm{InTransit}(t)$ y $\mathrm{InTransitBook}(t)$ contienen el mismo efectivo en tránsito y los valores que viajan entre dos brókers de $S$ a valor de mercado, $\mathrm{MV}^{\mathrm{tr}}(t)$, en el primero y a coste histórico, $\mathrm{CB}^{\mathrm{tr}}(t)$, en el segundo. El efectivo se cancela, así que con $\mathrm{OCB}(t)$ el coste base de las posiciones mantenidas (§3):

$$
\mathrm{UGL}(t) = \bigl[\mathrm{MV}(t) - \mathrm{OCB}(t)\bigr] + \bigl[\mathrm{MV}^{\mathrm{tr}}(t) - \mathrm{CB}^{\mathrm{tr}}(t)\bigr]
$$

El motor informa de dos cifras no realizadas:

| Cifra | Definición | Dónde aparece |
|--------|-----------|----------------|
| No realizado de la cartera | $\mathrm{UGL}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)$, valores en tránsito incluidos | `unrealized_gain_loss` del resumen y de los puntos de historial del informe de cartera (`POST /portfolio/report`) y de los resúmenes de cartera y de bróker de la exportación IA; [Valor contable — No realizado](book-value.md) |
| No realizado del periodo | $\mathrm{MV}(t) - \mathrm{OCB}(t)$ en cada frontera del periodo, solo posiciones mantenidas | `period_unrealized_gain_loss_start`, `_end`, `_delta` y su reparto por divisa; la **variación no realizada** del panel; el $\Delta\mathrm{UGL}$ de [P&L período](period-pnl.md) y las filas por posición de la §7 |

Difieren solo por los valores en tránsito: en un día en el que no viaja ninguno, son iguales. Un valor en tránsito en una frontera del periodo está en el NAV, por tanto en el P&L período, pero no en el estado de ninguna posición: su parte del resultado está en el residual de la §7, no en $\Delta\mathrm{UGL}$.

### 🏦 El bróker completo {: #whole-broker }

Cada importe del bróker $b$ —sus cantidades, efectivo y flujos— cuenta según la [participación de propiedad](../../../../user/brokers/sharing.md) del bróker $s_b$: la participación de un propietario, $1$ para un editor o un lector. La vista de **bróker completo**, pensada para la página del bróker, fija $s_b = 1$ para cada bróker, como lo ve un editor, cualquiera que sea la participación del usuario; el panel mantiene la participación del propietario. Un bróker valorado en 10 000 € con una participación del 30 % equivale a 3 000 € en el panel y 10 000 € en la vista completa; con una participación del 0 %, 0 € y 10 000 €.

Para un solo bróker, los ratios son los mismos en ambas vistas: cada flujo y cada valor se multiplica por la misma constante $s_b$, que se cancela en TWRR, MWRR, ROI simple, los pesos y los porcentajes del periodo. Solo cambian los importes.

---

## 📐 6. Modelo de efectivo de tres pools — Por bróker $(K_b, R_b, W)$ {: #6-three-pool-cash-model-per-broker-k_b-r_b-w }

Tres pools acumuladores rastrean la procedencia del efectivo. $K$ y $R$ se mantienen **por bróker** $b$; $W$ es global (sale del sistema por completo).

| Pool | Ámbito | Significado |
|------|-------|---------|
| $K_b$ | Por bróker | Capital externo que sigue en el bróker $b$ como efectivo |
| $R_b$ | Por bróker | Rendimientos generados que siguen en el bróker $b$ como efectivo |
| $W$ | Global | Rendimientos que salieron del sistema (ocultos, restaurables al volver a depositar) |

!!! info "Propiedad clave"

    Una COMPRA en el bróker $b_1$ solo puede consumir $R_{b_1}$, nunca $R_{b_2}$. El efectivo no se teletransporta entre brókers: solo las transferencias explícitas mueven los saldos de los pools.

### 🔁 Reglas de actualización (por transacción en el bróker $b$, en orden cronológico)

| Icono y tipo | Fórmulas de actualización | Lógica y descripción |
|:---:|---|---|
| ![](../../../../static/icons/transactions/deposit.png){: width="24" }<br>**DEPÓSITO**<br>$D > 0$ | $r = \min(D,\, W)$<br>$R_b \mathrel{+}= r$<br>$W \mathrel{-}= r$<br>$K_b \mathrel{+}= D - r$ | Restaura primero los rendimientos retirados previamente desde el rastreador global $W$, y luego añade el resto al capital $K_b$. |
| ![](../../../../static/icons/transactions/withdrawal.png){: width="24" }<br>**RETIRO**<br>$X > 0$ | $k = \min(X,\, K_b)$<br>$K_b \mathrel{-}= k$<br>$\rho = \min(X - k,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$W \mathrel{+}= \rho$ | Consume primero el capital $K_b$ y luego mueve los rendimientos restantes $\rho$ al rastreador global $W$. |
| ![](../../../../static/icons/transactions/dividend.png){: width="24" } ![](../../../../static/icons/transactions/interest.png){: width="24" }<br>**DIVIDENDO / INTERÉS**<br>$I > 0$ | $R_b \mathrel{+}= I$ | Los rendimientos incrementan directamente el pool de rendimientos $R_b$. |
| ![](../../../../static/icons/transactions/fee.png){: width="24" } ![](../../../../static/icons/transactions/tax.png){: width="24" }<br>**COMISIÓN / IMPUESTO**<br>$F > 0$ | $R_b \mathrel{-}= F$<br>$\text{si } R_b < 0\text{: } K_b \mathrel{+}= R_b,\; R_b = 0$ | Consume primero los rendimientos $R_b$; si $R_b$ se vuelve negativo, se drena del capital $K_b$. |
| ![](../../../../static/icons/transactions/buy.png){: width="24" }<br>**COMPRA**<br>$B > 0$ | $\rho = \min(B,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$K_b \mathrel{-}= (B - \rho)$ | Consume primero los rendimientos $R_b$ y luego drena el resto del capital $K_b$. |
| ![](../../../../static/icons/transactions/sell.png){: width="24" }<br>**VENTA** | $G = P - C$<br>$K_b \mathrel{+}= C$<br>$R_b \mathrel{+}= G$<br>$\text{si } R_b < 0\text{: } K_b \mathrel{+}= R_b, \quad R_b = 0$ | El coste base $C = |q_s| \cdot w_{\text{pre}}$ vuelve al capital $K_b$; la ganancia $G$ va a los rendimientos $R_b$ (si $G < 0$, se comporta como una comisión).<br><br>!!! warning "Orden crítico"<br><br> $C$ debe calcularse **antes** de que se reduzca el pool del PMC (una venta total daría $C = 0$ de lo contrario). |
| ![](../../../../static/icons/transactions/cash-transfer.png){: width="24" } ![](../../../../static/icons/transactions/fx-conversion.png){: width="24" }<br>**TRANSFERENCIA DE FONDOS / CONVERSIÓN FX**<br>(Interno, $s \to d$, $X > 0$ sale, $Y > 0$ llega) | **Tramo de salida ($s$):**<br>$\rho = \min(X,\, R_s)$<br>$R_s \mathrel{-}= \rho$<br>$\kappa = X - \rho$<br>$K_s \mathrel{-}= \kappa$<br><br>**Tramo de llegada ($d$):**<br>$K_d \mathrel{+}= \kappa$<br>$R_d \mathrel{+}= \rho + (Y - X)$<br>$\text{si } R_d < 0\text{: } K_d \mathrel{+}= R_d,\; R_d = 0$ | El tramo de salida toma primero los rendimientos $R_s$ y luego el capital $K_s$. La llegada devuelve lo que la salida tomó de cada pool. $X$ e $Y$ están en $C^*$ al tipo de cambio de la fecha de cada tramo, cada uno ponderado por la participación de propiedad de su bróker, por lo que pueden diferir: el spread de conversión frente al tipo de referencia, el movimiento del tipo de cambio mientras viaja el efectivo, dos brókers con participaciones de propiedad distintas. Ningún tramo es un flujo externo, así que la base de capital no se mueve y el P&L total ya cuenta la brecha $Y - X$: es un **resultado**, registrado como el [resultado de cambio sobre el efectivo en reposo](#exchange-result-on-foreign-cash) —una ganancia para los rendimientos, una pérdida con cargo primero a los rendimientos y luego al capital, como una COMISIÓN. Con $Y = X$: $K_d \mathrel{+}= \kappa$, $R_d \mathrel{+}= \rho$.<br>Una CONVERSIÓN FX tiene ambos tramos en el mismo bróker ($s = d$), en dos divisas.<br>El rastreador global $W$ **nunca** se toca (el capital permanece dentro del sistema). |
| ![](../../../../static/icons/transactions/cash-transfer.png){: width="24" } ![](../../../../static/icons/transactions/fx-conversion.png){: width="24" }<br>**TRANSFERENCIA DE FONDOS / CONVERSIÓN FX**<br>(Tramo externo o huérfano en $b$: $Y > 0$ llega, o $X > 0$ sale) | **Entrante ($Y$), como un DEPÓSITO:**<br>$r = \min(Y,\, W)$<br>$R_b \mathrel{+}= r$<br>$W \mathrel{-}= r$<br>$K_b \mathrel{+}= Y - r$<br><br>**Saliente ($X$), como un RETIRO:**<br>$k = \min(X,\, K_b)$<br>$K_b \mathrel{-}= k$<br>$\rho = \min(X - k,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$W \mathrel{+}= \rho$ | Un tramo cuyo otro tramo está en un bróker fuera de $S$, o que ha perdido su pareja —el enlace se borró o la fila emparejada desapareció—, es un flujo externo: la base de capital lo cuenta por su importe, como un depósito o un retiro. Sus pools se mueven como lo harían ese depósito o ese retiro: una llegada primero restaura los rendimientos retirados $W$ en $R_b$ y el resto es capital $K_b$; una salida toma primero el capital $K_b$ y luego los rendimientos $R_b$, que van a $W$. A diferencia de un par interno, este tramo **sí** toca $W$, y no registra ni recoge ningún reparto. |

Por ejemplo, con $C^* = \mathrm{EUR}$, un bróker con $K = 1000$, $R = 300$ convierte 650 EUR en 715 USD a un tipo de referencia de 0.92 EUR por USD ($Y = 657.80$): después $K = 1000$ y $R = 307.80$ —el capital sigue siendo igual a lo depositado, y el spread de 7.80 es un resultado—. Entre brókers con participaciones de propiedad distintas, $A$ al 100 % enviando 400 a $B$ al 50 % da $X = 400$, $Y = 200$: una pérdida de 200, con cargo primero a los rendimientos.

Cada salida registra su reparto $(\rho, X)$ hasta que su llegada lo recoge, una sola vez. Una llegada cuya salida es desconocida —sin reparto registrado, o $X = 0$— va íntegramente a $K_d$. Cuando ambos tramos caen el mismo día, la llegada se aplica después de los demás movimientos de ese día, cualesquiera que sean sus IDs de transacción, de modo que siempre encuentra el reparto de su salida. Una transferencia o conversión cuyo otro tramo está fuera de $S$, o que ha perdido su pareja, no es interna y no sigue esta regla: mueve los pools como un DEPÓSITO o un RETIRO (la fila anterior). En una vista solo del bróker $B$, $650$ que llegan de un bróker $A$ fuera de la vista hacen que un $B$ vacío mantenga $K_B = 650$, $R_B = 0$; un $B$ que mantiene $K_B = 100$, $R_B = 100$ termina en $K_B = 750$, $R_B = 100$. Si el $B$ que mantiene $K_B = 100$, $R_B = 100$ envía $150$ fuera de la vista en su lugar, conserva $K_B = 0$, $R_B = 50$ y $W = 50$: la siguiente entrada —un depósito u otro tramo desde fuera— restaura esos $50$ en $R_B$ primero, y una COMPRA posterior gasta $R_B$ primero, como de costumbre. En la vista de $A$ y $B$ juntos, el mismo par es interno y sigue la regla anterior.

Si las fechas de salida y llegada difieren, la transferencia está en tránsito: se resta de $s$ el día de salida y se suma a $d$ el día de llegada. Entre esas fechas, $\sum K_b + \sum R_b < \mathrm{Cash}_{\text{like}}$ por el importe en tránsito; la conciliación de más abajo interpreta ese efectivo con la mezcla actual de los pools hasta que la llegada devuelve el reparto de la salida.

### 💱 Resultado de cambio sobre el efectivo extranjero {: #exchange-result-on-foreign-cash }

Cada movimiento de efectivo entra en el efectivo del bróker, y en sus pools, al tipo de cambio de su propia fecha; el saldo mantenido después sigue el tipo de cambio (§5). En cada día $t$ en el que cambia el tipo de cambio de una divisa extranjera mantenida como efectivo en $S$ —incluido su primer tipo de cambio conocido—, después de los movimientos de efectivo de ese día y antes de que las transacciones de ese día actualicen los pools, cada bróker $b$ que mantiene efectivo extranjero se revalúa:

$$
\varepsilon_b(t) = \sum_{c} N_{b,c}(t) \cdot \mathrm{fx}(c, C^*, t) - \mathrm{Cash}^{\text{replay}}_b(t)
$$

$$
\mathrm{Cash}^{\text{replay}}_b \mathrel{+}= \varepsilon_b, \qquad
R_b \mathrel{+}= \varepsilon_b, \qquad
\text{si } R_b < 0\text{: } K_b \mathrel{+}= R_b,\; R_b = 0
$$

$\mathrm{Cash}^{\text{replay}}_b(t)$ es el efectivo que la repetición arrastra para $b$: su valor en la revaluación anterior más cada movimiento posterior al tipo de cambio de su propia fecha. Una ganancia va a los rendimientos; una pérdida los consume primero y luego el capital, exactamente como una COMISIÓN. La base de capital no se mueve: un resultado de cambio es un resultado, no una aportación, así que está en el NAV, el P&L total, el ROI, el TWRR y el MWRR, nunca en el capital depositado.

### 🧮 Agregación para la salida

$$
\mathrm{CashFromCapital}(t) = \sum_{b \in S} K_b(t)
$$

$$
\mathrm{CashFromReturns}(t) = \sum_{b \in S} R_b(t)
$$

### ⚖️ Invariante de conciliación

$$
\mathrm{Cash}_{\text{like}}(t) \approx \sum_{b \in S} K_b(t) + \sum_{b \in S} R_b(t)
$$

Ambos pools se limitan primero a cero por bróker. Si los pools no están vacíos y la desviación aún supera $0.01$, los pools **sumados** se escalan a $\mathrm{Cash}_{\text{like}}$, el efectivo más el efectivo en tránsito —un escalado agregado, no por bróker, aplicando un mínimo de cero a cada resultado—:

$$
\mathrm{CashFromCapital}(t) = \sum_{b \in S} K_b(t) \cdot \frac{\mathrm{Cash}_{\text{like}}(t)}{\sum_{b \in S} K_b(t) + \sum_{b \in S} R_b(t)}, \qquad
\mathrm{CashFromReturns}(t) = \mathrm{Cash}_{\text{like}}(t) - \mathrm{CashFromCapital}(t)
$$

En caso contrario, $\mathrm{CashFromCapital}(t) = \min\bigl(\sum_b K_b(t),\, \mathrm{Cash}_{\text{like}}(t)\bigr)$ y $\mathrm{CashFromReturns}$ es el resto, con un mínimo de cero. Los resultados de cambio sobre el efectivo en reposo se registran en los pools (arriba); el escalado absorbe dos desviaciones:

- **Efectivo en tránsito.** La salida ya ha dejado los pools, mientras que $\mathrm{Cash}_{\text{like}}$ sigue contando el efectivo en tránsito —y el movimiento de su tipo de cambio mientras viaja—, así que $\sum K_b + \sum R_b < \mathrm{Cash}_{\text{like}}$. Hasta la llegada, la escala interpreta ese efectivo con la mezcla actual de los pools. Un bróker con $K = 1000$, $R = 300$ envía $650$ en $C^*$ a un bróker vacío de $S$: conserva $K = 650$, $R = 0$, la escala es $1300 / 650 = 2$, así que $\mathrm{CashFromCapital} = 1300$ y $\mathrm{CashFromReturns} = 0$ durante el tránsito. A la llegada, el reparto vuelve: $1000$ y $300$.
- **Efectivo negativo (descubierto).** Ambos pools se limitan a cero por bróker, así que un bróker cuyo efectivo cae por debajo de cero deja pools que ya no suman su efectivo —también en los días siguientes, ya que los valores limitados se conservan—.

---

## 📐 7. Contribución del periodo {: #7-period-contribution }

Para el periodo $[t_0, t_1]$, por posición $(a,b)$:

$$
\Delta\mathrm{UGL}(a,b) = \mathrm{UGL}(a,b,t_1) - \mathrm{UGL}(a,b,t_0) + T(a,b)
$$

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{FeesTaxes}(a,b)
$$

Conjunto de posiciones de la contribución:

$$
\mathcal{P} = \text{posiciones con actividad de BUY/SELL/ADJUSTMENT/TRANSFER o cantidad en frontera}
$$

$\mathrm{UGL}(a,b,t)$ es el estado de la posición de la §3 al final del día $t$, el que agrega la cartera (§5): el precio de valoración de la §2 —un precio derivado de una operación, reexpresado a través de cualquier desdoblamiento posterior—, el coste base cuando el activo no tiene ningún precio de valoración, el tipo de cambio de $t$ mismo. Una posición no mantenida en $t$ cuenta 0. Una posición mantenida en $t$ cuyo $\mathrm{UGL}(a,b,t)$ es desconocido —sin tipo de cambio, un coste incompleto— hace que $\Delta\mathrm{UGL}(a,b)$ sea desconocido, nunca el lado conocido menos cero. Cuando todas las filas son conocidas, las filas suman el cambio de la cartera, el de las posiciones mantenidas —el no realizado del periodo de la [§5](#two-unrealized-figures), excluidos los valores en tránsito—:

$$
\sum_{(a,b) \in \mathcal{P}} \Delta\mathrm{UGL}(a,b) = \Delta\mathrm{UGL} = \bigl[\mathrm{MV}(t_1) - \mathrm{OCB}(t_1)\bigr] - \bigl[\mathrm{MV}(t_0) - \mathrm{OCB}(t_0)\bigr]
$$

La identidad también se cumple con el residuo: una fila y el estado de cartera de la §3 usan el mismo umbral, así que una posición que queda con $10^{-5}$ unidades o menos no se mantiene en ninguno de los dos lados: sin valor, sin no realizado, en ninguna fila y no en $\Delta\mathrm{UGL}$. Su coste sale del coste base abierto sin venderse, así que no está ni en $\Delta\mathrm{UGL}$ ni en el Realizado: termina en el residual del periodo (más abajo).

**Transferencias internas.** $T(a,b)$ reparte el resultado de un valor movido entre dos brókers de $S$: cada bróker responde por su propio tramo. Para cada TRANSFERENCIA vinculada de $a$ del bróker $s$ al bróker $d$ que sale después de $t_0$ y llega en $t_1$ o antes, con $V$ el valor de las unidades movidas el día de llegada (§3) y $C$ el coste histórico que el pool del emisor cedió por ellas (§4):

$$
T(a,s) \mathrel{+}= V - C, \qquad T(a,d) \mathrel{-}= V - C
$$

El emisor responde por las unidades hasta que llegan, incluido el tránsito, y el receptor desde su llegada; los términos se cancelan, por lo que el total no cambia. Una transferencia que ya está en tránsito en $t_0$, que sigue en tránsito en $t_1$, o cuyo $V$ o $C$ es desconocido, no añade nada: los valores de frontera se mantienen.

??? example "Ejemplo: 10 unidades movidas del bróker A al bróker B"

    A tiene 10 unidades compradas a 80 ($C = 800$). El precio es 100 en $t_0$, 120 el día en que se mueven a B ($V = 1{,}200$) y 150 en $t_1$:

    $$
    \Delta\mathrm{UGL}(a,A) = 0 - (1{,}000 - 800) + (1{,}200 - 800) = +200
    $$

    $$
    \Delta\mathrm{UGL}(a,B) = (1{,}500 - 800) - 0 - (1{,}200 - 800) = +300
    $$

    A responde por 100 → 120 y B por 120 → 150: +500 en total, el $\Delta\mathrm{UGL}$ de la cartera ($700 - 200$). Sin $T$, A mostraría −200 y B +700.

El P&L período a nivel de cartera también expone un residual:

$$
\mathrm{Other} =
\mathrm{PnL}_{period} - \Delta\mathrm{UGL} - \mathrm{Realized} - \mathrm{Income} + \mathrm{FeesTaxes}
$$

Dado que UGL no puede contener el resultado de cambio sobre el efectivo (§5), Other se divide en el resultado de cambio de cada bróker durante el periodo y lo que queda:

$$
\mathrm{Other} = \sum_{b \in S} \mathrm{FXonCash}_b + \mathrm{Residual}
$$

Las comisiones/ingresos no asignados sin `asset_id` se agrupan por bróker como otros efectos del periodo, y lo mismo ocurre con $\mathrm{FXonCash}_b$: una fila por bróker que mantiene efectivo extranjero, que se muestra cuando su resultado no es cero. Véase [P&L período — efecto del tipo de cambio sobre el efectivo](period-pnl.md#fx-on-cash).

Cuando todas las filas son conocidas, las filas y los demás efectos del periodo cierran juntos $\mathrm{PnL}_{period}$. Dado que las filas se valoran igual que la cartera, el residual no contiene diferencias de valoración entre ellas, solo lo que ninguna posición contiene: lo que viaja entre dos brókers, el coste de un cambio de divisas, una enajenación excluida del Realizado y el coste del residuo.

??? example "Ejemplo: una venta que deja 0.00001 unidades"

    10 unidades se compran a 100,000 antes del periodo, y el precio es 100,000 en $t_0$: el NAV es 1,000,000 y el no realizado 0. Dentro del periodo, se venden 9.99999 unidades a 120,000 por 1,199,998.80: el Realizado es $9.99999 \times 20{,}000 = 199{,}999.80$, y quedan 0.00001 unidades; el precio también es 120,000 en $t_1$, así que valen 1.20 con un coste de 1.00. Son residuo: no están en ninguna fila ni en el NAV, así que el $\Delta\mathrm{UGL}$ de la fila y el de la cartera son ambos 0, y el NAV en $t_1$ es el efectivo de la venta. $\mathrm{PnL}_{period} = 1{,}199{,}998.80 - 1{,}000{,}000 = 199{,}998.80$, y

    $$
    \mathrm{Other} = 199{,}998.80 - 0 - 199{,}999.80 = -1.00
    $$

    el coste del residuo. Valorado en el NAV, el residuo habría puesto $1.20 - 1.00 = 0.20$ en el $\Delta\mathrm{UGL}$ de la cartera que ninguna fila tenía.

---

## 📐 8. Ganancia/pérdida realizada {: #8-realized-gain-loss }

En una enajenación de $|q_s|$ unidades de la posición $(a,b)$ en la fecha $t$ —una VENTA, o un AJUSTE saliente no vinculado a un desdoblamiento:

$$
C = |q_s| \cdot w_{\text{pre}}(a,b)
$$

$$
\mathrm{Realized} = P \cdot \mathrm{fx}(c_P, C^*, t) - C
$$

$P$ es aquello por lo que salen las unidades, en su divisa $c_P$: el producto de una VENTA, en la divisa de su efectivo; $0$ para un AJUSTE saliente, que no tiene valor sea cual sea el coste base que tenga la fila ([Ajustes salientes](../../../instruments/transaction-types/adjustment.md#outgoing-adjustments)), por lo que realiza $-C$. $w_{\text{pre}}$ es el PMC en $C^*$ **antes** de la reducción del pool (el mismo valor que usa la regla de VENTA de los 3 pools anterior): las unidades salen a su coste histórico, sin conversión en $t$, mientras que $P$ se convierte en $t$. Una enajenación cuyo $P$ no puede convertirse, o que se extrae de una posición cuyo coste es incompleto, queda excluida del Realizado.

Un AJUSTE saliente no mueve efectivo, por lo que ningún pool de la §6 cambia, ni tampoco el capital: la base de capital no se mueve ([Capital depositado — Ajustes salientes](deposited-capital.md#outgoing-adjustments)).

---

## 📐 9. Una repetición diaria

| Rango | Intervalo de fechas | Función |
|-------|-----------|------|
| Repetición | $[\min(t_{\mathrm{first}},\ t_0),\ t_1]$ | Cada día, con las mismas reglas: efectivo, cantidad, PMC, pools, precios, FX, estados de posición y de cartera |
| Marco | $[t_0,\ t_1]$ | Los días cuyos estados se devuelven |

Hay una sola repetición, desde el primer movimiento $t_{\mathrm{first}}$ (o $t_0$, si es anterior) hasta $t_1$. Un movimiento fechado antes de $t_0$ sigue las mismas reglas que cualquier otro: se convierte al tipo de cambio de su propia fecha y mueve los pools del PMC y los K/R/W de los 3 pools, y cada día en que cambia el tipo de cambio de una divisa extranjera mantenida, el efectivo se revalúa y el resultado de cambio entra en los pools (§6). Los estados se devuelven desde $t_0$, de modo que el estado de un día no depende del marco en el que se lee. Un día en el que no cambia ningún término del modelo conserva el estado del día anterior. Un día lo cambia cuando aporta un movimiento, un cambio en un tipo de cambio que el día lee, una cotización, un desdoblamiento, una frontera de tránsito, un precio que pasa a estar obsoleto o un tipo de cambio que pasa a estar obsoleto; el primer día de la repetición y el inicio del marco siempre se calculan.

**Cuándo un precio pasa a estar obsoleto.** Un precio arrastrado está obsoleto una vez que su última observación $o$ (una cotización o una operación de COMPRA/VENTA) tiene más de $\theta = 7$ días de antigüedad. El indicador de cada día se calcula como antes, pero el motor inicia un nuevo estado el primer día obsoleto, $o+\theta+1$, solo cuando el precio aún se arrastra entonces:

$$
\text{cambio a obsoleto en } o+\theta+1 \iff \text{ninguna observación del activo cae en } (o,\ o+\theta+1]
$$

Una observación más reciente dentro de ese tramo es un cambio por sí misma y renueva la antigüedad del precio: con una cotización del viernes seguida de una del lunes, viernes + 8 días no es un cambio a obsoleto, porque el precio en uso entonces es el del lunes y no está obsoleto.

**Cuándo un tipo de cambio pasa a estar obsoleto.** Un tipo de cambio leído para valorar los valores mantenidos (la divisa del activo y de sus cotizaciones frente a $C^*$) pasa a estar obsoleto de la misma manera: cuando la fila almacenada de la que proviene, fechada en $r$, tiene más de $\theta$ días de antigüedad, el día $r+\theta+1$ inicia un nuevo estado, a menos que una fila más reciente lo reemplace antes. El estado lleva entonces el par `CCY/C*` con la fecha $r$ de su fila, y el informe lo lista en `data_quality.stale_fx_pairs` como `{pair, last_rate_date, stale_days}` para el día de valoración. El tipo de cambio sigue siendo el último conocido: la obsolescencia es un indicador, no un valor distinto.

### 🪜 Estados diarios como pasos {: #daily-states-as-steps }

Entre dos días que cambian el estado, todos los valores del informe son idénticos. Por tanto, el informe de cartera no devuelve un punto por día natural: devuelve **un punto por tramo sin novedades**, que abarca desde su `date` hasta su `through`, ambos incluidos. La respuesta lleva `range {start, end}`, la ventana tras recortarla a los días que tienen estado.

```json
{
  "range": {"start": "2026-10-23", "end": "2026-10-26"},
  "history": [
    {"date": "2026-10-23", "through": "2026-10-25", "nav_value": {"code": "EUR", "amount": "10450.00"}, "twrr": "0", "roi": "0.045000"},
    {"date": "2026-10-26", "through": "2026-10-26", "nav_value": {"code": "EUR", "amount": "10462.50"}, "twrr": "0.001196", "roi": "0.046250"}
  ],
  "mwrr_line": [
    {"date": "2026-10-23", "annualized": "0", "cumulative": "0"},
    {"date": "2026-10-25", "annualized": "0", "cumulative": "0"},
    {"date": "2026-10-26", "annualized": "0.156557", "cumulative": "0.001196"}
  ]
}
```

Un fondo mantenido el viernes 23, sábado 24, domingo 25 y lunes 26 de octubre, cotizado el viernes y el lunes (las cifras son ilustrativas y los demás campos de un punto se omiten). El NAV del sábado es el NAV del paso que lo contiene: $\mathrm{NAV}(t)$ se lee del punto con `date` $\le t \le$ `through`, con una búsqueda por fecha y sin cálculo.

- **Qué series.** `history`, `allocation_history.*`, `broker_pnl_history[].points` y `pnl_candles.points`. Las series de eventos (ingresos, coste, depósito, financiación de adquisiciones) no cambian: un punto por evento.
- **Pasos maximales.** Dos pasos adyacentes nunca llevan valores idénticos; los pasos de un bróker son maximales para su propio P&L, no para el de la cartera.
- **Huecos.** Un día que ningún paso cubre no tiene valor: un bróker que empieza a mitad de la ventana, o un día sin una vela de P&L (un activo mantenido no pudo valorarse).
- **TWRR y ROI** permanecen dentro de los pasos. En un día tranquilo, el factor TWRR es exactamente 1 y el ROI no cambia. El primer punto del TWRR está fijado a 0, por ser relativo al periodo. Un paso en el que el NAV es cero o negativo no lleva TWRR (`null`), bajo la misma regla que la tarjeta ([Cuándo no se muestra TWRR](twrr.md#when-no-twrr)); la cadena sigue componiendo a través de él, así que el TWRR vuelve una vez que el NAV es positivo de nuevo. El capital del ROI es el de la tarjeta ([El ROI de un periodo](roi.md#dashboard-period-roi)).
- **MWRR** se mueve cada día, porque el tiempo pasa, y con varios flujos no tiene forma cerrada: no está en los pasos sino en `mwrr_line`, una serie de **valores reales**, cada uno igual al [MWRR](mwrr.md) del periodo que termina ese día, bajo la misma regla que la tarjeta (sin tasa cuando el valor de la cartera o el capital neto invertido no es positivo). La línea tiene un punto en el `date` y en el `through` de cada paso; dentro de un paso de más de 62 días añade el último día de cada mes natural estrictamente dentro de él, como máximo 24 por paso, repartidos uniformemente. Su primer punto está fijado a 0.
- **Calidad de datos** sigue la misma idea: `incomplete_nav_ranges`, `incomplete_book_value_ranges`, `incomplete_allocation_ranges` e `incomplete_valuation_ranges` son listas de `{start, end}` con días consecutivos fusionados. `missing_fx_pairs[].dates` contiene solo las fechas de los movimientos, y `missing_fx_pairs[].ranges`, los días de valoración, fusionados. Las listas `incomplete_*_dates` más antiguas son transitorias.

---

## 📐 10. Métricas de rendimiento (Capa 2)

Se calculan **después** de los estados diarios, en una pasada separada:

| Métrica | Fórmula | Referencia |
|--------|---------|-----------|
| P&L total | $\mathrm{NAV}(t) - \text{CapitalBaseline}(t)$ | [Capital depositado](deposited-capital.md) |
| P&L período | $\mathrm{NAV}(t_1) - \mathrm{NAV}(t_0) - \text{ECF}_{[t_0,t_1]}$ | [P&L período](period-pnl.md) |
| TWRR | $\prod_i (1 + r_i) - 1$ (cadena de subperiodos) | [TWRR](twrr.md) |
| MWRR | XIRR que resuelve $\sum \frac{CF_i}{(1+r)^{d_i/365}} = 0$ | [MWRR](mwrr.md) |
| ROI simple | $(\mathrm{NAV} - \text{NetInvested}) / \text{NetInvested}$ | [ROI](roi.md) |
| Rentabilidad anualizada neta | $(1+r_{\mathrm{net}})^{365/d}-1$, suprimida por debajo de 30 días | [Rentabilidad anualizada neta](net-annualized-return.md) |
| Rendimiento sobre coste | Ingresos brutos por transacción de los últimos 365 días por unidad histórica elegible, divididos por el PMC residual por unidad en $t_1$ | [Rendimiento sobre coste](yield-on-cost.md) |
| Efecto timing | $\text{MWRR}_{\text{cum}} - \text{TWRR}_{\text{cum}}$ | [Efecto timing](timing-effect.md) |

---

## 🔗 Relacionado

- 💼 [NAV](nav.md) — valoración puntual
- 🧭 [Resolución de precios](price-resolution.md) — resolutor de valoración unificado
- 📈 [Rentabilidad anualizada neta](net-annualized-return.md) — definiciones de CAGR de posiciones, periodo y FIFO
- 💸 [Rendimiento sobre coste](yield-on-cost.md) — ingresos brutos registrados acumulados en relación con el PMC residual por unidad
- 📖 [Valor contable](book-value.md) — agregado del coste base
- 📊 [P&L período](period-pnl.md) — ganancia/pérdida por ventana con contribución
- 💸 [Capital depositado](deposited-capital.md) — detalles de los 3 pools y ejemplos resueltos
- 📈 [PMC](../weighted-average-cost.md) — método de coste iterativo
- 📈 [Resumen de métricas de rendimiento](../index.md) — todas las métricas de rendimiento de un vistazo
